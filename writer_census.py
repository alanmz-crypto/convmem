"""Payload-free C7 writer-session census.

This module owns the operational writer-census journal.  It deliberately has
no Shadow dependency: it records only session timing and approved route labels
while the C3 shared writer lease is already held.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


ARTIFACT_MODE = 0o600
DIRECTORY_MODE = 0o700
DEFAULT_CENSUS_DIR = Path("~/.local/share/convmem/writer-census")
HEADER_NAME = "census-header.json"
EVENTS_NAME = "session-events.jsonl"
STATUS_NAME = "census-status.json"
REPORT_NAME = "census-report.json"
KNOWN_ENTRYPOINTS = frozenset(
    {
        "convmem.add", "convmem.verify", "convmem.monitor", "convmem.forget",
        "ingest.write", "refine.write", "observe.repair_empty_ledger_documents",
        "ingest.processed", "ingest.export",
        "propose_decision.write", "propose_decision.governed",
        "source_purge.execute", "inter_model_index", "production.writer",
    }
)


class WriterCensusRefused(RuntimeError):
    """Fail-closed C7 refusal with a stable operator-facing code."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CensusSession:
    """Opaque open record carried by C3 until the lease exits."""

    census_dir: Path
    nonce: str
    opened_in_window: bool


def _utc(value: datetime | None = None) -> datetime:
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _stamp(value: datetime | None = None) -> str:
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_stamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _identity(path: Path) -> str:
    resolved = path.expanduser().resolve()
    # The C3 lock can legitimately be created after the armed header.  Bind
    # its canonical, symlink-refusing location rather than a transient inode.
    return hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()


def _writer_contract() -> tuple[str, int]:
    """Avoid importing C3 while it is importing the census hook."""
    from chroma_write_store import (
        WRITER_GATE_PROTOCOL_VERSION,
        current_implementation_revision,
    )

    return current_implementation_revision(), WRITER_GATE_PROTOCOL_VERSION


def _private_dir(path: Path, *, create: bool) -> Path:
    target = path.expanduser().absolute()
    if create:
        target.mkdir(mode=DIRECTORY_MODE, parents=True, exist_ok=True)
    try:
        st = os.lstat(target)
    except OSError as exc:
        raise WriterCensusRefused("census_missing", "census directory is missing") from exc
    if stat.S_ISLNK(st.st_mode):
        raise WriterCensusRefused("census_symlink_refused", "census directory is symlinked")
    if not stat.S_ISDIR(st.st_mode):
        raise WriterCensusRefused("census_path_unsafe", "census path is not a directory")
    if st.st_uid != os.geteuid():
        raise WriterCensusRefused("census_owner_invalid", "census directory owner differs")
    if stat.S_IMODE(st.st_mode) != DIRECTORY_MODE:
        if create:
            os.chmod(target, DIRECTORY_MODE)
            st = os.lstat(target)
        if stat.S_IMODE(st.st_mode) != DIRECTORY_MODE:
            raise WriterCensusRefused("census_permission_invalid", "census directory mode is not 0700")
    return target


def _path(directory: Path, name: str) -> Path:
    return directory / name


def _read_private_json(directory: Path, name: str) -> dict[str, Any]:
    path = _path(directory, name)
    try:
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode):
            raise WriterCensusRefused("census_symlink_refused", f"{name} is symlinked")
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise WriterCensusRefused("census_path_unsafe", f"{name} is not a private regular file")
        if st.st_uid != os.geteuid():
            raise WriterCensusRefused("census_owner_invalid", f"{name} owner differs")
        if stat.S_IMODE(st.st_mode) != ARTIFACT_MODE:
            raise WriterCensusRefused("census_permission_invalid", f"{name} mode is not 0600")
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WriterCensusRefused("census_missing", f"{name} is missing") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise WriterCensusRefused("census_corrupt", f"{name} cannot be read") from exc
    if not isinstance(data, dict):
        raise WriterCensusRefused("census_corrupt", f"{name} is not an object")
    return data


def _write_new_json(directory: Path, name: str, value: Mapping[str, Any]) -> None:
    fd = -1
    dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(name, flags, ARTIFACT_MODE, dir_fd=dir_fd)
        os.fchmod(fd, ARTIFACT_MODE)
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        _write_all(fd, payload)
        os.fsync(fd)
        os.fsync(dir_fd)
    except FileExistsError as exc:
        raise WriterCensusRefused("census_path_unsafe", f"{name} already exists") from exc
    except OSError as exc:
        raise WriterCensusRefused("census_telemetry_write_failed", f"cannot create {name}") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(dir_fd)


def _write_all(fd: int, payload: bytes) -> None:
    sent = 0
    while sent < len(payload):
        written = os.write(fd, payload[sent:])
        if written <= 0:
            raise OSError("short census write")
        sent += written


def _read_events(directory: Path) -> list[dict[str, Any]]:
    path = _path(directory, EVENTS_NAME)
    try:
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode):
            raise WriterCensusRefused("census_symlink_refused", "event journal is symlinked")
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise WriterCensusRefused("census_path_unsafe", "event journal is unsafe")
        if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != ARTIFACT_MODE:
            raise WriterCensusRefused("census_permission_invalid", "event journal must be owned 0600")
        lines = path.read_text(encoding="utf-8").splitlines()
        events = [json.loads(line) for line in lines if line]
    except (OSError, json.JSONDecodeError) as exc:
        raise WriterCensusRefused("census_corrupt", "event journal is corrupt") from exc
    if not all(isinstance(event, dict) for event in events):
        raise WriterCensusRefused("census_corrupt", "journal event is not an object")
    return events


def _append_event(directory: Path, event: Mapping[str, Any]) -> None:
    lock_fd = os.open(directory / EVENTS_NAME, os.O_RDWR | os.O_CLOEXEC)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        events = _read_events(directory)
        event = dict(event)
        event["sequence"] = len(events) + 1
        payload = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
        os.lseek(lock_fd, 0, os.SEEK_END)
        _write_all(lock_fd, payload)
        os.fsync(lock_fd)
    except OSError as exc:
        raise WriterCensusRefused("census_telemetry_write_failed", "event durability failed") from exc
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def _validate_header(header: Mapping[str, Any], *, gate_path: Path | None = None) -> None:
    revision, protocol = _writer_contract()
    if header.get("schema_version") != 1:
        raise WriterCensusRefused("census_corrupt", "unsupported census schema")
    if header.get("code_revision") != revision:
        raise WriterCensusRefused("census_revision_mismatch", "runtime revision differs from census")
    if header.get("writer_gate_protocol") != protocol:
        raise WriterCensusRefused("census_protocol_mismatch", "writer gate protocol differs")
    if gate_path is not None and header.get("writer_gate_identity") != _identity(gate_path):
        raise WriterCensusRefused("census_gate_mismatch", "writer gate differs from census")


def start_writer_census(
    *,
    chroma_root: Path,
    writer_gate_path: Path,
    census_dir: Path | None = None,
    now: datetime | None = None,
    window_days: int = 7,
) -> dict[str, Any]:
    """Create one armed seven-complete-UTC-day census, with no payload data."""
    revision, protocol = _writer_contract()
    if revision == "unknown":
        raise WriterCensusRefused("census_revision_mismatch", "runtime revision is unavailable")
    directory = _private_dir(census_dir or DEFAULT_CENSUS_DIR, create=True)
    start = _utc(now).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    end = start + timedelta(days=window_days)
    header = {
        "schema_version": 1,
        "census_id": uuid.uuid4().hex,
        "created_at_utc": _stamp(now),
        "window_start_utc": _stamp(start),
        "window_end_utc": _stamp(end),
        "code_revision": revision,
        "writer_gate_protocol": protocol,
        "chroma_root_identity": _identity(chroma_root),
        "writer_gate_identity": _identity(writer_gate_path),
    }
    _write_new_json(directory, HEADER_NAME, header)
    _create_events(directory)
    _write_new_json(directory, STATUS_NAME, {"state": "armed", "census_id": header["census_id"]})
    return header


def _create_events(directory: Path) -> None:
    fd = -1
    dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(EVENTS_NAME, flags, ARTIFACT_MODE, dir_fd=dir_fd)
        os.fchmod(fd, ARTIFACT_MODE)
        os.fsync(fd)
        os.fsync(dir_fd)
    except FileExistsError as exc:
        raise WriterCensusRefused("census_path_unsafe", "event journal already exists") from exc
    except OSError as exc:
        raise WriterCensusRefused("census_telemetry_write_failed", "cannot create event journal") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(dir_fd)


def record_writer_open(
    *, census_dir: Path | None = None, entrypoint: str, writer_gate_path: Path, now: datetime | None = None
) -> CensusSession | None:
    """Durably record an open while C3's shared flock is held, or no-op when absent."""
    directory = (census_dir or DEFAULT_CENSUS_DIR).expanduser()
    if not directory.exists():
        return None
    directory = _private_dir(directory, create=False)
    header = _read_private_json(directory, HEADER_NAME)
    _validate_header(header, gate_path=writer_gate_path)
    if entrypoint not in KNOWN_ENTRYPOINTS:
        raise WriterCensusRefused("census_path_unsafe", "writer entrypoint is not allowlisted")
    instant = _utc(now)
    start, end = _parse_stamp(header["window_start_utc"]), _parse_stamp(header["window_end_utc"])
    if instant >= end:
        return None
    nonce = uuid.uuid4().hex
    in_window = instant >= start
    revision, protocol = _writer_contract()
    _append_event(directory, {
        "event": "open", "census_id": header["census_id"], "nonce": nonce,
        "at_utc": _stamp(instant), "monotonic_ns": time.monotonic_ns(),
        "entrypoint": entrypoint, "in_window": in_window,
        "code_revision": revision, "writer_gate_protocol": protocol,
    })
    return CensusSession(directory, nonce, in_window)


def record_writer_close(session: CensusSession | None, *, now: datetime | None = None) -> None:
    """Durably record close before C3 unlocks; caller decides close-error suppression."""
    if session is None:
        return
    header = _read_private_json(session.census_dir, HEADER_NAME)
    _validate_header(header)
    _append_event(session.census_dir, {
        "event": "close", "census_id": header["census_id"], "nonce": session.nonce,
        "at_utc": _stamp(now), "monotonic_ns": time.monotonic_ns(),
    })


def census_status(*, census_dir: Path | None = None, now: datetime | None = None) -> dict[str, Any]:
    directory = _private_dir(census_dir or DEFAULT_CENSUS_DIR, create=False)
    header = _read_private_json(directory, HEADER_NAME)
    events = _read_events(directory)
    return {"header": header, "event_count": len(events), "now_utc": _stamp(now)}


def build_writer_census_report(*, census_dir: Path | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Validate the immutable journal and write the one final C6-bindable report."""
    directory = _private_dir(census_dir or DEFAULT_CENSUS_DIR, create=False)
    header = _read_private_json(directory, HEADER_NAME)
    _validate_header(header)
    end = _parse_stamp(header["window_end_utc"])
    if _utc(now) < end:
        raise WriterCensusRefused("census_window_incomplete", "seven complete UTC days have not elapsed")
    events = _read_events(directory)
    active: dict[str, dict[str, Any]] = {}
    per_day: dict[str, int] = {}
    peak = 0
    for expected, event in enumerate(events, 1):
        if event.get("sequence") != expected:
            raise WriterCensusRefused("census_event_sequence_invalid", "event sequence is not contiguous")
        nonce, kind = event.get("nonce"), event.get("event")
        if not isinstance(nonce, str) or kind not in {"open", "close"}:
            raise WriterCensusRefused("census_event_pair_invalid", "event is malformed")
        if kind == "open":
            if nonce in active:
                raise WriterCensusRefused("census_event_pair_invalid", "duplicate open nonce")
            active[nonce] = event
            if event.get("in_window") is True:
                day = str(event.get("at_utc", ""))[:10]
                per_day[day] = per_day.get(day, 0) + 1
        else:
            if nonce not in active:
                raise WriterCensusRefused("census_event_pair_invalid", "close has no open")
            del active[nonce]
        peak = max(peak, len(active))
    if active:
        raise WriterCensusRefused("census_incomplete", "open sessions have no durable close")
    start = _parse_stamp(header["window_start_utc"])
    complete_days = {
        (start + timedelta(days=index)).strftime("%Y-%m-%d"): per_day.get(
            (start + timedelta(days=index)).strftime("%Y-%m-%d"), 0
        )
        for index in range(7)
    }
    report = {
        "schema_version": 1, "census_id": header["census_id"],
        "window_start_utc": header["window_start_utc"], "window_end_utc": header["window_end_utc"],
        "code_revision": header["code_revision"], "writer_gate_protocol": header["writer_gate_protocol"],
        "chroma_root_identity": header["chroma_root_identity"], "writer_gate_identity": header["writer_gate_identity"],
        "max_concurrent_writer_sessions": peak,
        "total_writer_session_opens": sum(complete_days.values()),
        "opens_per_day": complete_days,
        "conservative_short_lived_opens_per_day": max(complete_days.values(), default=0),
        "payloads": "none",
    }
    _write_new_json(directory, REPORT_NAME, report)
    return report


def load_writer_census_report(
    path: Path, *, chroma_root: Path, writer_gate_path: Path
) -> tuple[dict[str, Any], str]:
    """Strictly load report for C6 and return its canonical SHA-256 binding."""
    directory = _private_dir(path.expanduser().absolute().parent, create=False)
    if path.name != REPORT_NAME:
        raise WriterCensusRefused("census_path_unsafe", "report must be the final census report")
    report = _read_private_json(directory, REPORT_NAME)
    revision, protocol = _writer_contract()
    if report.get("code_revision") != revision:
        raise WriterCensusRefused("census_revision_mismatch", "report revision differs")
    if report.get("writer_gate_protocol") != protocol:
        raise WriterCensusRefused("census_protocol_mismatch", "report protocol differs")
    if report.get("chroma_root_identity") != _identity(chroma_root):
        raise WriterCensusRefused("census_chroma_mismatch", "report Chroma root differs")
    if report.get("writer_gate_identity") != _identity(writer_gate_path):
        raise WriterCensusRefused("census_gate_mismatch", "report writer gate differs")
    if not isinstance(report.get("max_concurrent_writer_sessions"), int) or not isinstance(
        report.get("conservative_short_lived_opens_per_day"), int
    ):
        raise WriterCensusRefused("census_corrupt", "report metrics are invalid")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return report, digest
