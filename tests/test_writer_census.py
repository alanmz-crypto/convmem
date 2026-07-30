"""C7 payload-free writer-census contract tests."""

from __future__ import annotations

import json
import os
import fcntl
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from writer_census import (
    ARTIFACT_MODE,
    DIRECTORY_MODE,
    EVENTS_NAME,
    HEADER_NAME,
    REPORT_NAME,
    STATUS_NAME,
    WriterCensusRefused,
    build_writer_census_report,
    record_writer_close,
    record_writer_open,
    start_writer_census,
)


def _at(day: int, hour: int = 12) -> datetime:
    return datetime(2030, 1, day, hour, tzinfo=timezone.utc)


def _start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    monkeypatch.setattr("chroma_write_store.current_code_revision", lambda: "revision")
    directory, chroma, gate = tmp_path / "census", tmp_path / "chroma", tmp_path / "gate.lock"
    chroma.mkdir()
    start_writer_census(
        census_dir=directory, chroma_root=chroma, writer_gate_path=gate, now=_at(1)
    )
    return directory, chroma, gate


def test_private_artifacts_and_report_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory, _chroma, gate = _start(tmp_path, monkeypatch)
    one = record_writer_open(census_dir=directory, entrypoint="convmem.add", writer_gate_path=gate, now=_at(2))
    two = record_writer_open(census_dir=directory, entrypoint="ingest.write", writer_gate_path=gate, now=_at(2, 13))
    assert one and two
    record_writer_close(one, now=_at(2, 14))
    record_writer_close(two, now=_at(2, 15))
    report = build_writer_census_report(census_dir=directory, now=_at(9))
    assert report["max_concurrent_writer_sessions"] == 2
    assert report["total_writer_session_opens"] == 2
    assert report["conservative_short_lived_opens_per_day"] == 2
    assert report["payloads"] == "none"
    assert not {"payload", "document", "metadata", "pid"} & set(report)
    assert (directory.stat().st_mode & 0o777) == DIRECTORY_MODE
    for name in (HEADER_NAME, EVENTS_NAME, STATUS_NAME, REPORT_NAME):
        assert (directory / name).stat().st_mode & 0o777 == ARTIFACT_MODE


def test_armed_open_is_not_counted_but_must_close(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory, _chroma, gate = _start(tmp_path, monkeypatch)
    armed = record_writer_open(census_dir=directory, entrypoint="convmem.add", writer_gate_path=gate, now=_at(1, 13))
    assert armed is not None and armed.opened_in_window is False
    record_writer_close(armed, now=_at(2, 1))
    report = build_writer_census_report(census_dir=directory, now=_at(9))
    assert report["total_writer_session_opens"] == 0


def test_tail_close_is_required_after_window(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory, _chroma, gate = _start(tmp_path, monkeypatch)
    session = record_writer_open(census_dir=directory, entrypoint="convmem.add", writer_gate_path=gate, now=_at(8, 23))
    assert session
    with pytest.raises(WriterCensusRefused, match="census_incomplete"):
        build_writer_census_report(census_dir=directory, now=_at(9))
    record_writer_close(session, now=_at(9, 1))
    assert build_writer_census_report(census_dir=directory, now=_at(9))["total_writer_session_opens"] == 1


def test_report_refuses_early_or_corrupt_sequence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory, _chroma, gate = _start(tmp_path, monkeypatch)
    session = record_writer_open(census_dir=directory, entrypoint="convmem.add", writer_gate_path=gate, now=_at(2))
    assert session
    record_writer_close(session, now=_at(2, 1))
    with pytest.raises(WriterCensusRefused, match="census_window_incomplete"):
        build_writer_census_report(census_dir=directory, now=_at(8))
    events = directory / EVENTS_NAME
    data = json.loads(events.read_text().splitlines()[0])
    data["sequence"] = 9
    events.write_text(json.dumps(data) + "\n", encoding="utf-8")
    with pytest.raises(WriterCensusRefused, match="census_event_sequence_invalid"):
        build_writer_census_report(census_dir=directory, now=_at(9))


def test_symlink_and_mode_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory, _chroma, gate = _start(tmp_path, monkeypatch)
    (directory / EVENTS_NAME).chmod(0o644)
    with pytest.raises(WriterCensusRefused, match="census_permission_invalid"):
        record_writer_open(census_dir=directory, entrypoint="convmem.add", writer_gate_path=gate, now=_at(2))
    (directory / EVENTS_NAME).chmod(0o600)
    target = directory / "target"
    target.write_text("{}", encoding="utf-8")
    (directory / HEADER_NAME).unlink()
    (directory / HEADER_NAME).symlink_to(target)
    with pytest.raises(WriterCensusRefused, match="census_symlink_refused"):
        record_writer_open(census_dir=directory, entrypoint="convmem.add", writer_gate_path=gate, now=_at(2))


def test_close_record_is_durable_before_shared_gate_releases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The external flock oracle fails while C3 is paused in close persistence."""
    import writer_census

    directory, _chroma, gate = _start(tmp_path, monkeypatch)
    entered, release = threading.Event(), threading.Event()
    original = writer_census.record_writer_close

    def paused_close(session, **kwargs):  # type: ignore[no-untyped-def]
        entered.set()
        assert release.wait(2)
        return original(session, **kwargs)

    monkeypatch.setattr(writer_census, "record_writer_close", paused_close)
    worker = threading.Thread(
        target=lambda: _run_lease(gate, directory), daemon=True
    )
    worker.start()
    assert entered.wait(2)
    fd = os.open(gate, os.O_RDWR | os.O_CLOEXEC)
    try:
        with pytest.raises(BlockingIOError):
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(fd)
    release.set()
    worker.join(2)
    assert not worker.is_alive()


def test_negative_control_unlock_before_close_allows_exclusive(tmp_path: Path) -> None:
    """The same external oracle catches the deliberately broken ordering."""
    gate = tmp_path / "gate.lock"
    entered, release = threading.Event(), threading.Event()

    def broken_adapter() -> None:
        fd = os.open(gate, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH)
            fcntl.flock(fd, fcntl.LOCK_UN)  # Deliberately wrong: publish after unlock.
            entered.set()
            assert release.wait(2)
        finally:
            os.close(fd)

    worker = threading.Thread(target=broken_adapter, daemon=True)
    worker.start()
    assert entered.wait(2)
    fd = os.open(gate, os.O_RDWR | os.O_CLOEXEC)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
    release.set()
    worker.join(2)
    assert not worker.is_alive()


def _run_lease(gate: Path, directory: Path) -> None:
    from chroma_write_store import shared_writer_lease

    with shared_writer_lease(
        lock_path=gate, attest_dir=directory / "attest", census_dir=directory,
        entrypoint="convmem.add",
    ):
        pass
