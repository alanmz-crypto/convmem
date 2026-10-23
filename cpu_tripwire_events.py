"""Kernel fault classification and exact, boot-bound journal identities."""

from __future__ import annotations

# JSON booleans must never pass integer validation.
# pylint: disable=unidiomatic-typecheck
import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

_PROCESS = re.compile(r"(?P<process>[^\s\[\]:]+)\[(?P<pid>\d+)\]")
_LIKELY_CPU = re.compile(r"likely on CPU (?P<cpu>\d+)")
_MCE_CPU = re.compile(r"\[Hardware Error\]: CPU (?P<cpu>\d+): Machine Check")
_TRAP = re.compile(r"\btrap (?P<trap>[a-z][a-z ]*?) ip[: ]")
_KINDS = (
    ("segfault at ", "segfault"),
    ("general protection fault", "general_protection"),
    ("Machine check events logged", "machine_check"),
    ("Oops:", "kernel_oops"),
)


@dataclass(frozen=True)
class EventKey:
    boot_id: str
    realtime_us: int
    source_monotonic_us: int
    message_sha256: str
    cursor: str

    @property
    def ack_id(self) -> str:
        fields = (
            self.boot_id,
            str(self.realtime_us),
            str(self.source_monotonic_us),
            self.message_sha256,
            self.cursor,
        )
        return hashlib.sha256(
            ("cpu_tripwire_ack_v1|" + "|".join(fields)).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class Fault:  # pylint: disable=too-many-instance-attributes
    """Classification survives even when the entry cannot be acknowledged."""

    when: str
    kind: str
    cpu: int | None
    process: str
    pid: int | None
    boot_id: str | None = None
    realtime_us: int | None = None
    source_monotonic_us: int | None = None
    message_sha256: str | None = None
    message: bytes | None = None
    cursor: str | None = None
    hostname: str = "unknown"

    def describe(self) -> str:
        where = f"CPU {self.cpu}" if self.cpu is not None else "unknown CPU"
        who = f"{self.process}[{self.pid}]" if self.pid is not None else self.process
        return f"{who} {self.kind} on {where} at {self.when}"

    @property
    def key(self) -> EventKey | None:
        fields = (
            self.boot_id,
            self.realtime_us,
            self.source_monotonic_us,
            self.message_sha256,
            self.cursor,
        )
        return None if any(value is None for value in fields) else EventKey(*fields)


@dataclass
class JournalRead:
    faults: list[Fault] = field(default_factory=list)
    boot_ids: set[str] = field(default_factory=set)
    problems: list[str] = field(default_factory=list)


def normalize_boot_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().replace("-", "").lower()
    return value if re.fullmatch(r"[0-9a-f]{32}", value) else None


def valid_cursor(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= 256
        and all(32 <= ord(c) <= 126 for c in value)
    )


def message_bytes(value: Any) -> bytes:
    """Decode a single journal MESSAGE without losing its original bytes."""
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, list) and all(type(b) is int and 0 <= b <= 255 for b in value):
        return bytes(value)
    raise ValueError("MESSAGE must be a string or an array of bytes")


def _fault_number(value: str, problems: list[str] | None) -> int | None:
    try:
        return int(value)
    except ValueError:
        if problems is not None:
            problems.append("unclassifiable numeric fault field")
        return None


def classify_message(
    message: str, when: str = "unknown time", *, problems: list[str] | None = None
) -> Fault | None:
    if _MCE_CPU.search(message):
        kind = "machine_check"
    elif (trap := _TRAP.search(message)) and "traps:" in message:
        kind = trap.group("trap").replace(" ", "_")
    else:
        kind = next((kind for needle, kind in _KINDS if needle in message), None)
    if kind is None:
        return None
    cpu = _LIKELY_CPU.search(message) or _MCE_CPU.search(message)
    proc = (
        _PROCESS.search(message)
        if kind not in ("machine_check", "kernel_oops")
        else None
    )
    return Fault(
        when,
        kind,
        _fault_number(cpu.group("cpu"), problems) if cpu else None,
        proc.group("process") if proc else "kernel",
        _fault_number(proc.group("pid"), problems) if proc else None,
    )


def parse_kernel_faults(lines: Iterable[str]) -> list[Fault]:
    """Retain the original short-iso parser for policy regression comparisons."""
    faults = []
    for line in lines:
        head, sep, message = line.partition(" kernel: ")
        if sep and (fault := classify_message(message, head.split(" ", 1)[0])):
            faults.append(fault)
    return faults


def _timestamp(value: Any) -> int | None:
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,20}", value):
        value = int(value)
    return value if type(value) is int and value > 0 else None


def _messages(value: Any) -> tuple[list[bytes], bool]:
    try:
        return [message_bytes(value)], True
    except (ValueError, UnicodeError):
        # Repeated MESSAGE fields are arrays of values. Preserve every decodable
        # fault, but never assign one identity to an ambiguous entry.
        decoded = []
        for item in value if isinstance(value, list) else []:
            try:
                decoded.append(message_bytes(item))
            except (ValueError, UnicodeError):
                pass
        return decoded, False


class _JournalObject(dict):
    """Keep repeated MESSAGE values instead of silently accepting the last one."""

    def __init__(self, pairs):
        super().__init__(pairs)
        self.duplicate_fields = len(self) != len(pairs)
        self.messages = [value for key, value in pairs if key == "MESSAGE"]


def parse_kernel_journal(lines: Iterable[str]) -> JournalRead:
    """Retain positive fault evidence across malformed or incomplete entries."""
    result = JournalRead()
    for line in lines:
        try:
            row = json.loads(line, object_pairs_hook=_JournalObject)
        except (ValueError, RecursionError):
            result.problems.append("malformed JSON line")
            continue
        if not isinstance(row, dict):
            result.problems.append("journal entry is not an object")
            continue
        if row.duplicate_fields:
            result.problems.append("duplicate JSON field")
        boot = normalize_boot_id(row.get("_BOOT_ID"))
        if boot:
            result.boot_ids.add(boot)
        else:
            result.problems.append("journal entry has no valid boot ID")
        realtime = _timestamp(row.get("__REALTIME_TIMESTAMP"))
        when = "unknown time"
        if realtime:
            try:
                when = (
                    datetime.fromtimestamp(realtime // 1_000_000)
                    .astimezone()
                    .isoformat(timespec="seconds")
                )
            except (ValueError, OverflowError, OSError):
                realtime = None
        raw_messages = []
        unambiguous = len(row.messages) == 1 and not row.duplicate_fields
        for value in row.messages:
            decoded, unique = _messages(value)
            raw_messages.extend(decoded)
            unambiguous = unambiguous and unique
        if not unambiguous:
            result.problems.append("missing, null, invalid or repeated MESSAGE")
        for raw in raw_messages:
            fault = classify_message(
                raw.decode("utf-8", errors="replace"), when, problems=result.problems
            )
            if fault is None:
                continue
            cursor = row.get("__CURSOR")
            result.faults.append(
                replace(
                    fault,
                    boot_id=boot,
                    realtime_us=realtime,
                    source_monotonic_us=_timestamp(
                        row.get("_SOURCE_MONOTONIC_TIMESTAMP")
                    ),
                    message_sha256=hashlib.sha256(raw).hexdigest(),
                    message=raw,
                    cursor=cursor if unambiguous and valid_cursor(cursor) else None,
                    hostname=row.get("_HOSTNAME")
                    if isinstance(row.get("_HOSTNAME"), str)
                    else "unknown",
                )
            )
    return result


def ackable(fault: Fault, known_bad: set[int]) -> bool:
    return (
        fault.key is not None
        and fault.cpu is not None
        and fault.cpu not in known_bad
        and fault.pid is not None
        and fault.kind not in ("machine_check", "kernel_oops")
    )


# ref: ./cpu_tripwire.py, ./cpu_tripwire_ack.py — shared classification and exact identity
# src: ./docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md — five-field event key and decoding contract
