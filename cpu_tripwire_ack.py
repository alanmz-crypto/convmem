"""Strict acknowledgment storage, exact matching, and atomic operator writes."""

from __future__ import annotations

# Exact JSON integer types deliberately reject booleans.
# pylint: disable=unidiomatic-typecheck
import errno
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from cpu_tripwire_events import (
    EventKey,
    Fault,
    ackable,
    classify_message,
    message_bytes,
    valid_cursor,
)

ACK_SCHEMA = "convmem.cpu_tripwire.acknowledgments"
ACK_VERSION = 1
DEFAULT_ACK_PATH = Path(".config/convmem/cpu-tripwire-acknowledgments.json")
MAX_FILE_BYTES = 1024 * 1024
_RECORD_FIELDS = {
    "ack_id",
    "event",
    "evidence",
    "acknowledged_by",
    "acknowledged_at",
    "reason",
    "authority_ref",
    "operator_tty",
    "revoked_at",
    "revoked_by",
    "revocation_reason",
}
_KEY_FIELDS = {
    "boot_id",
    "realtime_us",
    "source_monotonic_us",
    "message_sha256",
    "cursor",
}
_CLASS_FIELDS = {"kind", "cpu", "process", "pid"}
_HARDWARE_SIGNALS = {4, 7, 8, 11}


class AckError(ValueError):
    """A refused operation; no inferred or broader acknowledgment is allowed."""


class TtyRequired(AckError):
    """Interactive input and output are required for acknowledgment."""


class DurabilityUnconfirmed(AckError):
    """The visible document is valid, but crash durability was not confirmed."""


@dataclass(frozen=True)
class Operator:
    by: str
    reason: str
    authority_ref: str | None = None


@dataclass
class AckContext:
    faults: list[Fault]
    current_boot_id: str | None
    known_bad: set[int]
    dumps: list[dict[str, Any]] = field(default_factory=list)
    problem: str | None = None


@dataclass
class Selection:
    applied: list[tuple[Fault, dict[str, Any]]] = field(default_factory=list)
    states: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    degraded: bool = False


@dataclass
class AckSet:
    records: tuple[dict[str, Any], ...] = ()
    problem: str | None = None
    present: bool = False

    def select(self, context: AckContext) -> Selection:
        result = Selection()
        problem = self.problem or context.problem
        if problem:
            result.notes.append(problem + "; no acknowledgments applied")
            result.degraded = True
        counts = Counter(f.key for f in context.faults if f.key is not None)
        by_key = {f.key: f for f in context.faults if f.key is not None}
        for record in self.records:
            key = record_key(record)
            if record["revoked_at"] is not None:
                state = "revoked"
            elif problem:
                state = "inert (acknowledgments disabled)"
            elif key.boot_id != context.current_boot_id:
                state = "inert (previous boot)"
            elif counts[key] == 0:
                state = "inert (entry not present)"
            elif counts[key] > 1:
                state = "inert (ambiguous key)"
            elif not ackable(by_key[key], context.known_bad):
                state = "inert (not needed: no longer a FAIL contributor)"
            else:
                state = "applied"
                result.applied.append((by_key[key], record))
            result.states.append({"record": record, "state": state})
        inert = [row["state"] for row in result.states if row["state"] != "applied"]
        if inert:
            reasons = ", ".join(sorted(set(inert)))
            result.notes.append(
                f"{len(inert)} inert acknowledgment(s) ({reasons}) -- see: convmem tripwire show"
            )
        return result


def default_ack_path() -> Path:
    return Path.home() / DEFAULT_ACK_PATH


def record_key(record: dict[str, Any]) -> EventKey:
    return EventKey(**{name: record["event"][name] for name in _KEY_FIELDS})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AckError(message)


def _keys(value: Any, expected: set[str], label: str) -> None:
    _require(
        isinstance(value, dict) and set(value) == expected, f"wrong {label} fields"
    )


def _text(value: Any, label: str, limit: int | None = None) -> None:
    _require(
        isinstance(value, str) and bool(value.strip()) and value.isprintable(),
        f"invalid {label}",
    )
    _require(limit is None or len(value) <= limit, f"{label} too long")


def _utc(value: Any, label: str) -> None:
    _require(isinstance(value, str) and value.endswith("Z"), f"invalid {label}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AckError(f"invalid {label}") from exc
    _require(parsed.utcoffset() == UTC.utcoffset(parsed), f"invalid {label}")


def _authority(value: Any) -> None:
    if value is None:
        return
    _text(value, "authority_ref")
    path = PurePosixPath(value)
    _require(
        not path.is_absolute()
        and ".." not in path.parts
        and ":" not in value
        and "\\" not in value
        and not value.startswith("~"),
        "authority_ref must be repo-relative",
    )


def _validate_key(key: EventKey) -> None:
    for value, width, name in (
        (key.boot_id, 32, "boot_id"),
        (key.message_sha256, 64, "message_sha256"),
    ):
        _require(
            isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{" + str(width) + "}", value) is not None,
            f"invalid {name}",
        )
    for value in (key.realtime_us, key.source_monotonic_us):
        _require(
            type(value) is int and value > 0, "timestamps must be positive integers"
        )
    _require(valid_cursor(key.cursor), "invalid cursor")


def _validate_record(record: Any) -> None:
    _keys(record, _RECORD_FIELDS, "record")
    event, evidence = record["event"], record["evidence"]
    _keys(event, _KEY_FIELDS | _CLASS_FIELDS, "event")
    _keys(evidence, {"message", "hostname", "coredump"}, "evidence")
    key = record_key(record)
    _validate_key(key)
    _require(record["ack_id"] == key.ack_id, "ack_id does not match the five-field key")
    raw = message_bytes(evidence["message"])
    _require(
        hashlib.sha256(raw).hexdigest() == key.message_sha256, "message hash mismatch"
    )
    fault = classify_message(raw.decode("utf-8", errors="replace"))
    _require(
        fault is not None
        and all(event[name] == getattr(fault, name) for name in _CLASS_FIELDS),
        "message classifier mismatch",
    )
    _require(
        type(event["cpu"]) is int
        and event["cpu"] >= 0
        and type(event["pid"]) is int
        and event["pid"] > 0
        and event["kind"] not in ("machine_check", "kernel_oops"),
        "event cannot be acknowledged",
    )
    _text(evidence["hostname"], "hostname")
    dump = evidence["coredump"]
    if dump is not None:
        _keys(dump, {"time_us", "pid", "sig", "exe"}, "coredump")
        _require(
            type(dump["time_us"]) is int
            and key.realtime_us <= dump["time_us"] <= key.realtime_us + 5_000_000
            and type(dump["pid"]) is int
            and dump["pid"] == event["pid"]
            and type(dump["sig"]) is int
            and dump["sig"] in _HARDWARE_SIGNALS,
            "invalid coredump evidence",
        )
        _text(dump["exe"], "coredump executable")
    _text(record["acknowledged_by"], "acknowledged_by")
    _text(record["reason"], "reason", 500)
    _text(record["operator_tty"], "operator_tty")
    _authority(record["authority_ref"])
    _utc(record["acknowledged_at"], "acknowledged_at")
    revoked = [
        record[name] for name in ("revoked_at", "revoked_by", "revocation_reason")
    ]
    if any(value is not None for value in revoked):
        _utc(revoked[0], "revoked_at")
        _text(revoked[1], "revoked_by")
        _text(revoked[2], "revocation_reason", 500)


def _validate_document(document: Any) -> tuple[dict[str, Any], ...]:
    _keys(document, {"schema", "version", "acknowledgments"}, "document")
    _require(
        document["schema"] == ACK_SCHEMA
        and type(document["version"]) is int
        and document["version"] == ACK_VERSION,
        "unsupported schema or version",
    )
    _require(
        isinstance(document["acknowledgments"], list), "acknowledgments must be a list"
    )
    seen = set()
    for record in document["acknowledgments"]:
        _validate_record(record)
        _require(record["ack_id"] not in seen, "duplicate ack_id")
        seen.add(record["ack_id"])
    return tuple(document["acknowledgments"])


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def load_acks(path: Path | None = None) -> AckSet:
    path = default_ack_path() if path is None else path
    try:
        info = path.lstat()
    except FileNotFoundError:
        return AckSet()
    except OSError as exc:
        return AckSet(
            problem=f"acknowledgment file unreadable: {errno.errorcode.get(exc.errno, 'I/O error')}",
            present=True,
        )
    try:
        _require(
            stat.S_ISREG(info.st_mode), "acknowledgment path is not a regular file"
        )
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            _require(
                stat.S_ISREG(os.fstat(stream.fileno()).st_mode),
                "acknowledgment path is not a regular file",
            )
            content = stream.read(MAX_FILE_BYTES + 1)
        _require(len(content) <= MAX_FILE_BYTES, "acknowledgment file exceeds 1 MiB")
        document = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
        return AckSet(_validate_document(document), present=True)
    except OSError as exc:
        problem = f"acknowledgment file unreadable: {errno.errorcode.get(exc.errno, 'I/O error')}"
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        problem = f"acknowledgment file invalid: {exc}"
    return AckSet(problem=problem, present=True)


@contextmanager
def _writer_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(".cpu-tripwire-acknowledgments.lock")
    fd = os.open(
        lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600
    )
    try:
        _require(stat.S_ISREG(os.fstat(fd).st_mode), "lock is not a regular file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AckError("acknowledgment writer lock is busy") from exc
        yield
    finally:
        os.close(fd)


def _save(path: Path, records: list[dict[str, Any]]) -> None:
    document = {
        "schema": ACK_SCHEMA,
        "version": ACK_VERSION,
        "acknowledgments": records,
    }
    _validate_document(document)
    data = (json.dumps(document, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
    _require(len(data) <= MAX_FILE_BYTES, "acknowledgment file would exceed 1 MiB")
    fd, name = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=path.parent)
    temp_path = Path(name)
    replaced = False
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        replaced = True
        _sync_directory(path.parent)
    except OSError as exc:
        if replaced:
            raise DurabilityUnconfirmed(
                "document replaced but directory durability is unconfirmed; "
                "inspect with tripwire show and retry the same command"
            ) from exc
        raise
    finally:
        temp_path.unlink(missing_ok=True)


def _sync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _sync_existing(path: Path) -> None:
    """Under the writer lock, finish durability without rewriting attribution."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            _require(
                stat.S_ISREG(os.fstat(fd).st_mode), "not a regular acknowledgment file"
            )
            os.fsync(fd)
        finally:
            os.close(fd)
        _sync_directory(path.parent)
    except OSError as exc:
        raise DurabilityUnconfirmed(
            "existing document is visible but durability is unconfirmed; "
            "inspect with tripwire show and retry the same command"
        ) from exc


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def interactive_tty() -> str | None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return None
    try:
        return os.ttyname(sys.stdin.fileno())
    except (OSError, ValueError):
        return None


def confirm_ack(fault: Fault, short_id: str) -> str:
    print(fault.describe())
    return input(
        f"Type {short_id} to acknowledge this fault (hardware health remains unproven): "
    )


def _dump_evidence(context: AckContext, fault: Fault) -> dict[str, Any] | None:
    for dump in context.dumps:
        timestamp = dump.get("time")
        valid_time = (
            type(timestamp) is int
            and fault.realtime_us <= timestamp <= fault.realtime_us + 5_000_000
        )
        valid_identity = (
            type(dump.get("pid")) is int
            and dump["pid"] == fault.pid
            and type(dump.get("sig")) is int
            and dump["sig"] in _HARDWARE_SIGNALS
        )
        if (
            valid_time
            and valid_identity
            and isinstance(dump.get("exe"), str)
            and dump["exe"]
            and dump["exe"].isprintable()
        ):
            return {
                "time_us": timestamp,
                "pid": dump["pid"],
                "sig": dump["sig"],
                "exe": dump["exe"],
            }
    return None


def _make_record(
    fault: Fault, context: AckContext, operator: Operator, tty: str, now: str
) -> dict[str, Any]:
    try:
        message = fault.message.decode("utf-8")
    except UnicodeError:
        message = list(fault.message)
    return {
        "ack_id": fault.key.ack_id,
        "event": {
            **asdict(fault.key),
            **{name: getattr(fault, name) for name in _CLASS_FIELDS},
        },
        "evidence": {
            "message": message,
            "hostname": fault.hostname or "unknown",
            "coredump": _dump_evidence(context, fault),
        },
        "acknowledged_by": operator.by,
        "acknowledged_at": now,
        "reason": operator.reason,
        "authority_ref": operator.authority_ref,
        "operator_tty": tty,
        "revoked_at": None,
        "revoked_by": None,
        "revocation_reason": None,
    }


def _validate_operator(operator: Operator) -> None:
    _text(operator.by, "by")
    _text(operator.reason, "reason", 500)
    _authority(operator.authority_ref)


def write_ack(
    key: EventKey,
    operator: Operator,
    read_context: Callable[[], AckContext],
    *,
    path: Path | None = None,
    confirm: Callable[[Fault, str], str] | None = None,
    tty_check: Callable[[], str | None] | None = None,
    now: Callable[[], str] | None = None,
) -> tuple[str, bool]:
    """Acknowledge one freshly observed entry; a revoked key cannot be reactivated."""
    confirm = confirm or confirm_ack
    now = now or _utc_now
    tty = (tty_check or interactive_tty)()
    if tty is None:
        raise TtyRequired("ack requires stdin and stdout to be interactive terminals")
    _validate_key(key)
    _validate_operator(operator)
    path = default_ack_path() if path is None else path
    with _writer_lock(path):
        acks = load_acks(path)
        _require(acks.problem is None, acks.problem or "invalid acknowledgment file")
        context = read_context()
        _require(
            context.problem is None and context.current_boot_id == key.boot_id,
            context.problem or "boot identity mismatch",
        )
        matches = [fault for fault in context.faults if fault.key == key]
        _require(len(matches) == 1, "key must match exactly one current journal entry")
        fault = matches[0]
        _require(
            ackable(fault, context.known_bad),
            "entry is not an acknowledgeable FAIL contributor",
        )
        for record in acks.records:
            if record_key(record) == key:
                _require(
                    record["revoked_at"] is None,
                    "this key was revoked; re-acknowledgment is refused",
                )
                _sync_existing(path)
                return key.ack_id, False
        _require(
            confirm(fault, key.ack_id[:12]) == key.ack_id[:12],
            "confirmation did not match; nothing written",
        )
        record = _make_record(fault, context, operator, tty, now())
        _save(path, [*acks.records, record])
    return key.ack_id, True


def revoke_ack(
    prefix: str,
    operator: Operator,
    *,
    path: Path | None = None,
    now: Callable[[], str] | None = None,
) -> tuple[str, bool]:
    now = now or _utc_now
    _require(
        isinstance(prefix, str)
        and re.fullmatch(r"[0-9a-f]{12,64}", prefix) is not None,
        "ack ID must be 12 to 64 lowercase hexadecimal characters",
    )
    _validate_operator(operator)
    path = default_ack_path() if path is None else path
    with _writer_lock(path):
        acks = load_acks(path)
        _require(acks.problem is None, acks.problem or "invalid acknowledgment file")
        matches = [
            record for record in acks.records if record["ack_id"].startswith(prefix)
        ]
        _require(len(matches) == 1, "ID must match exactly one stored acknowledgment")
        record = matches[0]
        if record["revoked_at"] is not None:
            _sync_existing(path)
            return record["ack_id"], False
        updated = {
            **record,
            "revoked_at": now(),
            "revoked_by": operator.by,
            "revocation_reason": operator.reason,
        }
        _save(
            path,
            [
                updated if row["ack_id"] == record["ack_id"] else row
                for row in acks.records
            ],
        )
    return record["ack_id"], True


# ref: ./cpu_tripwire_events.py, ./cpu_tripwire.py, ./cpu_tripwire_cli.py — identity and operator boundaries
# src: ./docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md — strict storage and retained revocations
