# pylint: disable=duplicate-code,too-many-locals
"""C3 writer gate: shared/exclusive lease, attestation, fresh-config boundary."""

from __future__ import annotations

import inspect
import json
import multiprocessing as mp
import os
import re
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _write_minimal_config(path: Path, chroma_dir: Path) -> None:
    path.write_text(
        "[index]\n"
        f'chroma_dir = "{chroma_dir}"\n'
        'collection = "knowledge_units"\n'
        "[models]\n"
        'embed_model = "nomic-embed-text"\n'
        'ollama_host = "http://127.0.0.1:11434"\n'
        "[shadow_ledger]\n"
        "enabled = false\n",
        encoding="utf-8",
    )


def test_production_apis_accept_no_caller_cfg() -> None:
    from chroma_write_store import (
        open_production_write_store,
        production_chroma_write_session,
    )

    for fn in (production_chroma_write_session, open_production_write_store):
        params = inspect.signature(fn).parameters
        assert "cfg" not in params
        assert "chroma_dir" not in params
        assert "config_path" in params


def test_static_scan_zero_legacy_production_factory_calls() -> None:
    factory = re.compile(r"\bopen_chroma_for_write\s*\(")
    old_session = re.compile(r"(?<![a-zA-Z_])chroma_write_session\s*\(")
    hits: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if rel.startswith("tests/") or "docs/" in rel:
            continue
        if rel == "chroma_write_store.py":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if factory.search(line) and "def open_chroma_for_write" not in line:
                hits.append(f"{rel}:{i}:factory")
            if (
                old_session.search(line)
                and "def chroma_write_session" not in line
                and "production_chroma_write_session" not in line
            ):
                hits.append(f"{rel}:{i}:old_session")
    assert not hits, f"legacy production write opens remain: {hits}"


def test_fourteen_production_writer_sites_migrated() -> None:
    inv = json.loads(
        (ROOT / "docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json").read_text(
            encoding="utf-8"
        )
    )
    total = len(inv["production_chroma_write_session_call_sites"]) + len(
        inv["open_production_write_store_call_sites"]
    )
    assert total == 14
    assert inv["must_use_factory_count"] == 0


def test_shared_lease_writes_and_clears_attestation(tmp_path: Path) -> None:
    from chroma_write_store import (
        WRITER_GATE_PROTOCOL_VERSION,
        load_attestation,
        shared_writer_lease,
    )

    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    with shared_writer_lease(
        lock_path=lock, attest_dir=attest, entrypoint="test.shared"
    ) as att:
        assert att.protocol_version == WRITER_GATE_PROTOCOL_VERSION
        loaded = load_attestation(att.pid, attest_dir=attest)
        assert loaded is not None
        assert loaded["entrypoint"] == "test.shared"
        assert (attest / f"{att.pid}.json").is_file()
        mode = (attest / f"{att.pid}.json").stat().st_mode & 0o777
        assert mode == 0o600
    assert load_attestation(os.getpid(), attest_dir=attest) is None


def test_concurrent_same_process_shared_leases_keep_attestation(tmp_path: Path) -> None:
    """Overlapping same-PID leases must not unlink attestation early."""
    from chroma_write_store import (
        _process_writer_leases,
        load_attestation,
        production_writer_boundary,
    )

    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    pid = os.getpid()
    attestation_path = attest / f"{pid}.json"
    iterations = 40
    errors: list[BaseException] = []
    both_inside = threading.Barrier(2)
    release = threading.Barrier(2)

    def hold_one(tag: str) -> None:
        try:
            with production_writer_boundary(
                lock_path=lock,
                attest_dir=attest,
                entrypoint=f"test.concurrent.{tag}",
            ):
                both_inside.wait(timeout=5)
                assert attestation_path.is_file(), f"{tag}: attestation missing while leased"
                loaded = load_attestation(pid, attest_dir=attest)
                assert loaded is not None
                assert loaded["pid"] == pid
                release.wait(timeout=5)
        except BaseException as exc:  # noqa: BLE001 — collect for main thread
            errors.append(exc)

    for _ in range(iterations):
        t1 = threading.Thread(target=hold_one, args=("a",))
        t2 = threading.Thread(target=hold_one, args=("b",))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)
        assert not t1.is_alive() and not t2.is_alive(), "threads hung"
        assert errors == [], errors

    assert load_attestation(pid, attest_dir=attest) is None
    assert not attestation_path.exists()
    with _process_writer_leases.lock:
        assert _process_writer_leases.active_count == 0
        assert _process_writer_leases.attestation is None


def test_intermediate_shared_lease_exit_preserves_attestation(tmp_path: Path) -> None:
    from chroma_write_store import load_attestation, shared_writer_lease

    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    pid = os.getpid()
    attestation_path = attest / f"{pid}.json"
    inner_ready = threading.Event()
    inner_may_exit = threading.Event()
    errors: list[BaseException] = []

    def inner() -> None:
        try:
            with shared_writer_lease(
                lock_path=lock,
                attest_dir=attest,
                entrypoint="test.intermediate.inner",
            ):
                inner_ready.set()
                assert attestation_path.is_file()
                inner_may_exit.wait(timeout=5)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    with shared_writer_lease(
        lock_path=lock,
        attest_dir=attest,
        entrypoint="test.intermediate.outer",
    ):
        assert attestation_path.is_file()
        t = threading.Thread(target=inner)
        t.start()
        assert inner_ready.wait(timeout=5)
        assert load_attestation(pid, attest_dir=attest) is not None
        inner_may_exit.set()
        t.join(timeout=5)
        assert errors == []
        assert not t.is_alive()
        assert load_attestation(pid, attest_dir=attest) is not None
        assert attestation_path.is_file()
    assert load_attestation(pid, attest_dir=attest) is None


def test_nested_shared_lease_process_count_and_attestation_lifecycle(
    tmp_path: Path,
) -> None:
    from chroma_write_store import (
        _held_writer_lease,
        _process_writer_leases,
        load_attestation,
        production_writer_boundary,
        require_writer_attestation,
    )

    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    pid = os.getpid()
    attestation_path = attest / f"{pid}.json"

    with production_writer_boundary(
        lock_path=lock,
        attest_dir=attest,
        entrypoint="test.nested.outer",
    ):
        outer = _held_writer_lease()
        assert outer is not None
        with _process_writer_leases.lock:
            assert _process_writer_leases.active_count == 1
        assert attestation_path.is_file()
        with production_writer_boundary(entrypoint="test.nested.inner"):
            inner = _held_writer_lease()
            assert inner is outer
            with _process_writer_leases.lock:
                assert _process_writer_leases.active_count == 2
            assert require_writer_attestation() is outer.attestation
            assert load_attestation(pid, attest_dir=attest) is not None
        with _process_writer_leases.lock:
            assert _process_writer_leases.active_count == 1
        assert load_attestation(pid, attest_dir=attest) is not None
    assert load_attestation(pid, attest_dir=attest) is None
    with _process_writer_leases.lock:
        assert _process_writer_leases.active_count == 0


def test_shared_lease_exception_unwind_does_not_leak_process_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from chroma_write_store import (
        _process_writer_leases,
        load_attestation,
        shared_writer_lease,
    )
    import writer_census

    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    pid = os.getpid()

    def boom(*_a, **_k):  # type: ignore[no-untyped-def]
        raise RuntimeError("census open failed")

    monkeypatch.setattr(writer_census, "record_writer_open", boom)
    with pytest.raises(RuntimeError, match="census open failed"):
        with shared_writer_lease(
            lock_path=lock,
            attest_dir=attest,
            entrypoint="test.unwind",
        ):
            pass
    assert load_attestation(pid, attest_dir=attest) is None
    with _process_writer_leases.lock:
        assert _process_writer_leases.active_count == 0
        assert _process_writer_leases.attestation is None


def test_first_acquire_write_attestation_failure_rolls_back_process_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import chroma_write_store
    from chroma_write_store import (
        _process_writer_leases,
        load_attestation,
        shared_writer_lease,
    )

    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    pid = os.getpid()
    fail_once = {"pending": True}
    real_write_attestation = chroma_write_store.write_attestation

    def boom_once(attestation, *, attest_dir=None):  # type: ignore[no-untyped-def]
        if fail_once["pending"]:
            fail_once["pending"] = False
            raise RuntimeError("write attestation failed")
        return real_write_attestation(attestation, attest_dir=attest_dir)

    monkeypatch.setattr(chroma_write_store, "write_attestation", boom_once)
    with pytest.raises(RuntimeError, match="write attestation failed"):
        with shared_writer_lease(
            lock_path=lock,
            attest_dir=attest,
            entrypoint="test.write_attestation_failure",
        ):
            pass
    assert load_attestation(pid, attest_dir=attest) is None
    with _process_writer_leases.lock:
        assert _process_writer_leases.active_count == 0
        assert _process_writer_leases.attestation is None

    with shared_writer_lease(
        lock_path=lock,
        attest_dir=attest,
        entrypoint="test.write_attestation_recovery",
    ) as recovered:
        assert load_attestation(pid, attest_dir=attest) is not None
        assert recovered.entrypoint == "test.write_attestation_recovery"

    assert load_attestation(pid, attest_dir=attest) is None
    with _process_writer_leases.lock:
        assert _process_writer_leases.active_count == 0
        assert _process_writer_leases.attestation is None


def _child_hold_exclusive(lock_path: str, ready_path: str, release_path: str) -> None:
    import fcntl

    path = Path(lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    Path(ready_path).write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if Path(release_path).exists():
            break
        time.sleep(0.01)
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def test_shared_lease_blocks_behind_exclusive(tmp_path: Path) -> None:
    from chroma_write_store import shared_writer_lease

    lock = tmp_path / "gate.lock"
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    proc = mp.Process(
        target=_child_hold_exclusive,
        args=(str(lock), str(ready), str(release)),
    )
    proc.start()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not ready.exists():
        time.sleep(0.01)
    assert ready.exists(), "child exclusive holder never signaled ready"
    with pytest.raises(TimeoutError, match="writer_quiesce_timeout"):
        with shared_writer_lease(
            lock_path=lock,
            attest_dir=tmp_path / "attest",
            timeout_ms=200,
        ):
            pass
    release.write_text("go", encoding="utf-8")
    proc.join(timeout=5)
    assert proc.exitcode == 0


def test_exclusive_blocks_while_shared_held(tmp_path: Path) -> None:
    from chroma_write_store import exclusive_writer_lease, shared_writer_lease

    lock = tmp_path / "gate.lock"
    with shared_writer_lease(
        lock_path=lock, attest_dir=tmp_path / "attest", timeout_ms=1000
    ):
        with pytest.raises(TimeoutError, match="writer_quiesce_timeout"):
            with exclusive_writer_lease(lock_path=lock, timeout_ms=200):
                pass


def _child_hold_shared(lock_path: str, attest_dir: str, ready_path: str, release_path: str) -> None:
    from chroma_write_store import shared_writer_lease

    with shared_writer_lease(
        lock_path=Path(lock_path),
        attest_dir=Path(attest_dir),
        entrypoint="ingest.write",
    ):
        Path(ready_path).write_text("ready", encoding="utf-8")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not Path(release_path).exists():
            time.sleep(0.01)


def _wait_for(path: Path) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not path.exists():
        time.sleep(0.01)
    assert path.exists(), f"child did not signal: {path}"


def test_capture_generation_is_exclusive_and_unique(tmp_path: Path) -> None:
    import fcntl

    from chroma_write_store import capture_generation

    lock = tmp_path / "gate.lock"
    with capture_generation(lock_path=lock) as first:
        assert first.generation_id.startswith("capture-")
        fd = os.open(lock, os.O_RDWR | os.O_CLOEXEC)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        finally:
            os.close(fd)
    with capture_generation(lock_path=lock) as second:
        assert second.generation_id.startswith("capture-")
        assert second.generation_id != first.generation_id


def test_capture_generation_rejects_overlapping_writer(tmp_path: Path) -> None:
    from chroma_write_store import capture_generation

    lock = tmp_path / "gate.lock"
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    proc = mp.Process(
        target=_child_hold_shared,
        args=(str(lock), str(tmp_path / "attest"), str(ready), str(release)),
    )
    proc.start()
    _wait_for(ready)
    with pytest.raises(TimeoutError, match="writer_quiesce_timeout"):
        with capture_generation(lock_path=lock, timeout_ms=200):
            pass
    release.write_text("release", encoding="utf-8")
    proc.join(timeout=5)
    assert proc.exitcode == 0


def test_nested_composite_writer_reuses_one_custom_boundary(tmp_path: Path) -> None:
    from chroma_write_store import _held_writer_lease, production_writer_boundary

    lock = tmp_path / "gate.lock"
    with production_writer_boundary(
        lock_path=lock,
        attest_dir=tmp_path / "attest",
        entrypoint="propose_decision.write",
    ):
        outer = _held_writer_lease()
        assert outer is not None
        with production_writer_boundary(entrypoint="propose_decision.governed"):
            inner = _held_writer_lease()
            assert inner is outer
            assert inner.lock_path == lock


def test_nested_shared_lease_rejects_different_lock_and_keeps_outer_usable(
    tmp_path: Path,
) -> None:
    from chroma_write_store import (
        WriterBoundaryError,
        _held_writer_lease,
        require_writer_attestation,
        shared_writer_lease,
    )

    outer_lock = tmp_path / "outer.lock"
    inner_lock = tmp_path / "inner.lock"
    with shared_writer_lease(lock_path=outer_lock, attest_dir=tmp_path / "attest"):
        outer = _held_writer_lease()
        assert outer is not None
        with pytest.raises(WriterBoundaryError, match="outer lock path"):
            with shared_writer_lease(
                lock_path=inner_lock, attest_dir=tmp_path / "attest"
            ):
                pass
        assert _held_writer_lease() is outer
        assert require_writer_attestation() is outer.attestation


def test_code_derived_writer_routes_use_universal_or_existing_gate() -> None:
    expected_routes = {
        "ingest.py": ("production_writer_boundary", "production_chroma_write_session"),
        "observe.py": ("open_production_write_store",),
        "inter_model_index.py": ("production_chroma_write_session",),
        "propose_decision.py": ("production_writer_boundary", "open_production_write_store"),
        "refine.py": ("production_writer_boundary", "open_production_write_store"),
        "source_purge.py": ("production_writer_boundary", "open_production_write_store"),
        "convmem.py": ("production_chroma_write_session",),
    }
    for filename, markers in expected_routes.items():
        source = (ROOT / filename).read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in source]
        assert not missing, f"{filename} lacks writer boundary markers: {missing}"


def test_all_new_writer_entrypoints_are_census_allowlisted() -> None:
    from writer_census import KNOWN_ENTRYPOINTS

    assert {
        "ingest.processed",
        "ingest.export",
        "propose_decision.governed",
        "production.writer",
        "refine.write",
        "source_purge.execute",
    } <= KNOWN_ENTRYPOINTS


def test_classify_legacy_writer_pids(tmp_path: Path) -> None:
    from chroma_write_store import (
        WRITER_GATE_PROTOCOL_VERSION,
        WriterAttestation,
        classify_legacy_writer_pids,
        write_attestation,
    )

    attest = tmp_path / "attest"
    # unattested
    refusals = classify_legacy_writer_pids(
        [os.getpid() + 10_000],
        attest_dir=attest,
        expected_revision="abc",
    )
    assert refusals and refusals[0]["code"] == "legacy_writer_process"
    assert "unattested" in refusals[0]["detail"]

    # protocol mismatch
    write_attestation(
        WriterAttestation(
            pid=424242,
            start_time="1",
            code_revision="abc",
            executable="/bin/true",
            entrypoint="x",
            protocol_version=WRITER_GATE_PROTOCOL_VERSION + 1,
            recorded_at_utc="2026-01-01T00:00:00Z",
        ),
        attest_dir=attest,
    )
    refusals = classify_legacy_writer_pids(
        [424242], attest_dir=attest, expected_revision="abc"
    )
    assert any(r["detail"] == "protocol version mismatch" for r in refusals)

    # revision mismatch
    write_attestation(
        WriterAttestation(
            pid=424243,
            start_time="1",
            code_revision="oldrev",
            executable="/bin/true",
            entrypoint="x",
            protocol_version=WRITER_GATE_PROTOCOL_VERSION,
            recorded_at_utc="2026-01-01T00:00:00Z",
        ),
        attest_dir=attest,
    )
    refusals = classify_legacy_writer_pids(
        [424243], attest_dir=attest, expected_revision="newrev"
    )
    assert any(r["detail"] == "code revision mismatch" for r in refusals)



def test_production_session_loads_config_after_lease(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    import config as config_mod
    from unittest import mock

    from chroma_write_store import production_chroma_write_session

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg_path = tmp_path / "config.toml"
    _write_minimal_config(cfg_path, chroma)
    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    order: list[str] = []

    def tracked_load(path=None):  # type: ignore[no-untyped-def]
        pid = os.getpid()
        assert (attest / f"{pid}.json").is_file(), "config loaded before lease/attest"
        order.append("load_config")
        import tomllib

        target = Path(path or cfg_path)
        data = tomllib.loads(target.read_text(encoding="utf-8"))
        data["index"]["chroma_dir"] = str(
            Path(data["index"]["chroma_dir"]).expanduser()
        )
        return data

    with mock.patch.object(config_mod, "load_config", side_effect=tracked_load):
        with production_chroma_write_session(
            cfg_path,
            lock_path=lock,
            attest_dir=attest,
            entrypoint="test.reload",
        ) as session:
            order.append("in_session")
            assert session.live_cfg["index"]["chroma_dir"] == str(chroma)
            assert session.decision.inject is False
            assert session.store.mutation_sink is None
    assert order == ["load_config", "in_session"]
    assert not (attest / f"{os.getpid()}.json").exists()


def test_open_production_store_releases_lease_on_close(
    tmp_path: Path,
) -> None:
    pytest.importorskip("chromadb")
    from chroma_write_store import (
        exclusive_writer_lease,
        open_production_write_store,
    )

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg_path = tmp_path / "config.toml"
    _write_minimal_config(cfg_path, chroma)
    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    session = open_production_write_store(
        cfg_path,
        lock_path=lock,
        attest_dir=attest,
        entrypoint="test.open",
    )
    assert (attest / f"{os.getpid()}.json").is_file()
    # exclusive must block while shared held
    with pytest.raises(TimeoutError):
        with exclusive_writer_lease(lock_path=lock, timeout_ms=150):
            pass
    session.store.close()
    assert not (attest / f"{os.getpid()}.json").exists()
    # after close, exclusive succeeds
    with exclusive_writer_lease(lock_path=lock, timeout_ms=1000):
        pass


def test_production_session_exception_still_releases_lease(
    tmp_path: Path,
) -> None:
    pytest.importorskip("chromadb")
    from chroma_write_store import (
        exclusive_writer_lease,
        production_chroma_write_session,
    )

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg_path = tmp_path / "config.toml"
    _write_minimal_config(cfg_path, chroma)
    lock = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    with pytest.raises(RuntimeError, match="boom"):
        with production_chroma_write_session(
            cfg_path,
            lock_path=lock,
            attest_dir=attest,
        ) as session:
            assert session.store is not None
            raise RuntimeError("boom")
    assert not (attest / f"{os.getpid()}.json").exists()
    with exclusive_writer_lease(lock_path=lock, timeout_ms=1000):
        pass


def test_census_document_present_and_shaped() -> None:
    census_path = ROOT / "docs/plans/SHADOW-WRITER-CENSUS.json"
    assert census_path.is_file()
    census = json.loads(census_path.read_text(encoding="utf-8"))
    assert census["protocol_version"] == 1
    assert "code_revision" in census
    assert "systemd_units" in census
    assert "cmdline_signatures" in census
    assert "open_fd_writer_pids" in census


def test_store_close_invokes_on_close(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    from chroma_store import ChromaStore

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    called = {"n": 0}

    def _cb() -> None:
        called["n"] += 1

    store = ChromaStore(str(chroma), on_close=_cb)
    store.close()
    store.close()  # idempotent
    assert called["n"] == 1
