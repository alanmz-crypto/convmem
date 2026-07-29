# pylint: disable=too-many-lines
"""C2: secure header create, bounded-tail append, complete-path timing."""

from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path

import pytest

from shadow_ledger import (
    ARTIFACT_FILE_MODE,
    SHADOW_DIR_MODE,
    SecureIOHooks,
    SecureLedgerRefused,
    create_shadow_ledger_header,
    open_existing_shadow_ledger_fd,
    read_ledger_header_and_tail,
)
from shadow_replay import run_disposable_replay
from shadow_sink import (
    FSYNC_DEGRADED_LATENCY_MS,
    JsonlUnitMutationSink,
)


def _shadow(tmp_path: Path) -> Path:
    shadow = tmp_path / "shadow"
    shadow.mkdir(parents=True, exist_ok=True)
    os.chmod(shadow, SHADOW_DIR_MODE)
    return shadow


def _header_ledger(tmp_path: Path, **kwargs):
    shadow = _shadow(tmp_path)
    ledger = shadow / "ledger.jsonl"
    health = shadow / "health.json"
    header = create_shadow_ledger_header(
        ledger,
        activation_id=kwargs.get("activation_id", "act-1"),
        ledger_identity=kwargs.get("ledger_identity", "ledger-1"),
        starting_sequence=kwargs.get("starting_sequence", 0),
        hooks=kwargs.get("hooks"),
    )
    return shadow, ledger, health, header


def _events(ledger: Path) -> list[dict]:
    out = []
    for line in ledger.read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("record_type") == "ledger_header":
            continue
        out.append(obj)
    return out


@pytest.mark.parametrize("umask_value", [0o000, 0o022, 0o077])
def test_umask_matrix_header_is_0600(tmp_path: Path, umask_value: int) -> None:
    old = os.umask(umask_value)
    try:
        shadow = _shadow(tmp_path)
        ledger = shadow / f"ledger-{umask_value:03o}.jsonl"
        create_shadow_ledger_header(
            ledger, activation_id="act", ledger_identity="id"
        )
        mode = stat.S_IMODE(ledger.stat().st_mode)
        assert mode == ARTIFACT_FILE_MODE
        text = ledger.read_text()
        assert "record_type" in text
        assert "stable_entity_id" not in text  # no mutation payload
    finally:
        os.umask(old)


def test_fchmod_before_first_byte(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shadow = _shadow(tmp_path)
    ledger = shadow / "ledger.jsonl"
    seen = {"fchmod_before_write": False, "wrote": False}
    real_fchmod = os.fchmod
    real_write = os.write

    def fchmod(fd, mode):
        assert not seen["wrote"]
        seen["fchmod_before_write"] = True
        st = os.fstat(fd)
        assert st.st_size == 0
        return real_fchmod(fd, mode)

    def write(fd, data):
        assert seen["fchmod_before_write"]
        seen["wrote"] = True
        return real_write(fd, data)

    monkeypatch.setattr(os, "fchmod", fchmod)
    monkeypatch.setattr(os, "write", write)
    create_shadow_ledger_header(ledger, activation_id="a", ledger_identity="l")
    assert seen["fchmod_before_write"] and seen["wrote"]


def test_injected_fchmod_failure(tmp_path: Path) -> None:
    shadow = _shadow(tmp_path)
    ledger = shadow / "ledger.jsonl"

    def boom_fchmod(fd, mode):
        raise OSError("fchmod denied")

    hooks = SecureIOHooks(fchmod=boom_fchmod)
    with pytest.raises(SecureLedgerRefused):
        create_shadow_ledger_header(
            ledger, activation_id="a", ledger_identity="l", hooks=hooks
        )


def test_injected_fstat_mismatch(tmp_path: Path) -> None:
    shadow = _shadow(tmp_path)
    ledger = shadow / "ledger.jsonl"
    real_fstat = os.fstat

    def bad_fstat(fd):
        st = real_fstat(fd)
        # wrong mode bits via synthetic result
        return os.stat_result(
            (
                (st.st_mode & ~0o777) | 0o644,
                st.st_ino,
                st.st_dev,
                st.st_nlink,
                st.st_uid,
                st.st_gid,
                st.st_size,
                st.st_atime,
                st.st_mtime,
                st.st_ctime,
            )
        )

    hooks = SecureIOHooks(fstat=bad_fstat)
    with pytest.raises(SecureLedgerRefused):
        create_shadow_ledger_header(
            ledger, activation_id="a", ledger_identity="l", hooks=hooks
        )


def test_wrong_owner_seam(tmp_path: Path) -> None:
    shadow = _shadow(tmp_path)
    ledger = shadow / "ledger.jsonl"
    with pytest.raises(SecureLedgerRefused):
        create_shadow_ledger_header(
            ledger,
            activation_id="a",
            ledger_identity="l",
            euid=os.geteuid() + 1,
        )


def test_symlink_leaf_refused(tmp_path: Path) -> None:
    shadow = _shadow(tmp_path)
    real = shadow / "real.jsonl"
    real.write_text("x\n")
    os.chmod(real, 0o600)
    link = shadow / "ledger.jsonl"
    link.symlink_to(real)
    with pytest.raises(SecureLedgerRefused):
        open_existing_shadow_ledger_fd(link)


def test_symlinked_parent_refused(tmp_path: Path) -> None:
    real = tmp_path / "real-shadow"
    real.mkdir()
    os.chmod(real, SHADOW_DIR_MODE)
    link = tmp_path / "shadow"
    link.symlink_to(real)
    ledger = link / "ledger.jsonl"
    with pytest.raises(SecureLedgerRefused):
        create_shadow_ledger_header(ledger, activation_id="a", ledger_identity="l")


def test_existing_regular_file_create_refused(tmp_path: Path) -> None:
    shadow = _shadow(tmp_path)
    ledger = shadow / "ledger.jsonl"
    create_shadow_ledger_header(ledger, activation_id="a", ledger_identity="l")
    with pytest.raises(SecureLedgerRefused):
        create_shadow_ledger_header(ledger, activation_id="a", ledger_identity="l")


def test_zero_byte_and_headerless_refused(tmp_path: Path) -> None:
    shadow = _shadow(tmp_path)
    zero = shadow / "zero.jsonl"
    zero.write_bytes(b"")
    os.chmod(zero, 0o600)
    with pytest.raises(SecureLedgerRefused):
        open_existing_shadow_ledger_fd(zero)
    headerless = shadow / "headerless.jsonl"
    headerless.write_text('{"sequence":1,"event_id":"e"}\n')
    os.chmod(headerless, 0o600)
    fd, dfd, _ = open_existing_shadow_ledger_fd(headerless)
    try:
        with pytest.raises(SecureLedgerRefused):
            read_ledger_header_and_tail(fd)
    finally:
        os.close(fd)
        os.close(dfd)


def test_fifo_refused(tmp_path: Path) -> None:
    shadow = _shadow(tmp_path)
    fifo = shadow / "fifo.jsonl"
    os.mkfifo(fifo)
    try:
        os.chmod(fifo, 0o600)
    except OSError:
        pass
    with pytest.raises(SecureLedgerRefused):
        open_existing_shadow_ledger_fd(fifo)


def test_missing_ledger_append_refuses(tmp_path: Path) -> None:
    shadow = _shadow(tmp_path)
    ledger = shadow / "missing.jsonl"
    health = shadow / "health.json"
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    sink.observe(
        event_id="e",
        operation="create",
        stable_entity_id="u",
        document="x",
        metadata={},
        deleted=False,
    )
    assert not ledger.exists()


def test_first_fsync_failure_no_0644_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Umask 022 + first fsync failure cannot leave payload at 0644."""
    old = os.umask(0o022)
    try:
        shadow, ledger, health, _ = _header_ledger(tmp_path)
        assert (ledger.stat().st_mode & 0o777) == 0o600
        sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
        calls = {"n": 0}
        real = os.fsync

        def boom(fd):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("fsync failed")
            return real(fd)

        monkeypatch.setattr(os, "fsync", boom)
        sink.observe(
            event_id="e1",
            operation="create",
            stable_entity_id="u1",
            document="SECRET_PAYLOAD",
            metadata={},
            deleted=False,
        )
        mode = stat.S_IMODE(ledger.stat().st_mode)
        assert mode == 0o600
        assert mode != 0o644
        # Header still present; even if event bytes landed, file is private.
        raw = ledger.read_text()
        assert '"record_type":"ledger_header"' in raw.replace(" ", "") or (
            '"record_type": "ledger_header"' in raw
        )
    finally:
        os.umask(old)


def test_short_event_write_leaves_refusing_tail(tmp_path: Path) -> None:
    shadow, ledger, health, _ = _header_ledger(tmp_path)
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    real_write = os.write
    state = {"once": False}

    def short_write(fd, data):
        if not state["once"] and len(data) > 8:
            state["once"] = True
            return real_write(fd, data[:8])
        return real_write(fd, data)

    # Use hooks on sink
    sink._hooks = SecureIOHooks(write=short_write)  # pylint: disable=protected-access
    # write_all_fd loops until complete — simulate hard short by raising after partial
    def partial_then_fail(fd, data):
        if not state["once"]:
            state["once"] = True
            real_write(fd, data[:8])
            raise OSError("disk full")
        return real_write(fd, data)

    sink._hooks = SecureIOHooks(write=partial_then_fail)  # pylint: disable=protected-access
    sink.observe(
        event_id="e",
        operation="create",
        stable_entity_id="u",
        document="x",
        metadata={},
        deleted=False,
    )
    # Later append refuses truncated/invalid tail
    sink2 = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    sink2.observe(
        event_id="e2",
        operation="create",
        stable_entity_id="u2",
        document="y",
        metadata={},
        deleted=False,
    )
    health_obj = json.loads(health.read_text())
    assert health_obj.get("last_failure_class") in {
        "truncated_tail",
        "invalid_tail",
        "OSError",
        "secure_refused",
    }


def test_header_only_sequence_and_bounded_bytes(tmp_path: Path) -> None:
    shadow, ledger, health, _ = _header_ledger(tmp_path)
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    sink.observe(
        event_id="e1",
        operation="create",
        stable_entity_id="u1",
        document="x",
        metadata={},
        deleted=False,
    )
    assert _events(ledger)[0]["sequence"] == 1
    assert sink.last_timing.bytes_read_for_sequence > 0

    # Large events so N and 2N both exceed the 64KiB tail window.
    payload = "x" * 4000
    for i in range(2, 30):
        sink.observe(
            event_id=f"e{i}",
            operation="create",
            stable_entity_id=f"u{i}",
            document=payload,
            metadata={},
            deleted=False,
        )
    n_bytes = sink.last_timing.bytes_read_for_sequence
    assert ledger.stat().st_size > 65_536
    for i in range(30, 58):
        sink.observe(
            event_id=f"e{i}",
            operation="create",
            stable_entity_id=f"u{i}",
            document=payload,
            metadata={},
            deleted=False,
        )
    n2_bytes = sink.last_timing.bytes_read_for_sequence
    assert ledger.stat().st_size > 130_000
    # Bounded: header + one tail chunk (not linear in ledger length).
    assert n_bytes < 70_000
    assert n2_bytes < 70_000
    assert abs(n2_bytes - n_bytes) < 256


def test_duplicate_event_id_distinct_sequences_and_replay(tmp_path: Path) -> None:
    shadow, ledger, health, _ = _header_ledger(tmp_path)
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    for _ in range(2):
        sink.observe(
            event_id="same",
            operation="create",
            stable_entity_id="u1",
            document="x",
            metadata={"source_path": "/t"},
            deleted=False,
        )
    events = _events(ledger)
    assert len(events) == 2
    assert events[0]["sequence"] == 1
    assert events[1]["sequence"] == 2
    prod = tmp_path / "prod"
    prod.mkdir()
    result = run_disposable_replay(
        ledger_path=ledger,
        replay_root=tmp_path / "replay",
        production_chroma_root=prod,
        mode="stub",
        production_units={},
        touched_ids={"u1"},
    )
    # Replay should not fail; duplicates counted in findings/report if exposed.
    assert result.corrupt_at_line is None


def test_complete_timing_includes_health(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shadow, ledger, health, _ = _header_ledger(tmp_path)
    sink = JsonlUnitMutationSink(
        ledger_path=ledger,
        health_path=health,
        degraded_latency_ms=FSYNC_DEGRADED_LATENCY_MS,
    )
    real_fsync = os.fsync
    state = {"health_fsyncs": 0}

    def slow_fsync(fd):
        # Detect health temp fsync by path via /proc is hard; delay every fsync
        # after the ledger one by counting.
        state["health_fsyncs"] += 1
        if state["health_fsyncs"] >= 2:
            time.sleep(0.55)
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", slow_fsync)
    sink.observe(
        event_id="e1",
        operation="create",
        stable_entity_id="u1",
        document="x",
        metadata={},
        deleted=False,
    )
    assert sink.last_timing.health_persist_ms >= 500
    assert sink.last_timing.complete_append_ms >= sink.last_timing.health_persist_ms
    health_obj = json.loads(health.read_text())
    assert health_obj.get("append_degraded") is True
    assert health_obj.get("complete_append_ms", 0) >= 500


def test_hardlink_nlink_refused(tmp_path: Path) -> None:
    shadow, ledger, health, _ = _header_ledger(tmp_path)
    alt = shadow / "alt.jsonl"
    os.link(ledger, alt)
    with pytest.raises(SecureLedgerRefused):
        open_existing_shadow_ledger_fd(ledger)
