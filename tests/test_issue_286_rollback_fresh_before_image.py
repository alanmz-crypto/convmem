"""Hermetic regression tests for issue #286 rollback processed authority."""

# pylint: disable=duplicate-code,protected-access,too-many-lines

from __future__ import annotations

import hashlib
import tomllib
import json
import threading
from pathlib import Path

import socket

import pytest

import incremental_jsonl
from incremental_jsonl import (
    IncrementalJsonlCoordinator,
    IncrementalJsonlError,
)
from incremental_jsonl_isolation import IsolationViolation
from ingest import load_processed, mutate_processed
from purge_locks import index_write_lock_depth, source_lock_depth
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    kiro_record,
    write_source,
    worker_run,
)


@pytest.fixture(autouse=True)
def _deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(*_args, **_kwargs):
        raise IsolationViolation("outbound network denied in production-integration tests")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)

    # Patch the socket class, not unbound socket.socket.connect descriptors, so
    # pytest teardown cannot leave process-global connect hooks for later modules.
    _base_socket = socket.socket

    class _DeniedSocket(_base_socket):  # type: ignore[misc,valid-type]
        def connect(self, *_args, **_kwargs):
            denied()

        def connect_ex(self, *_args, **_kwargs):
            denied()
            return 1

    monkeypatch.setattr(socket, "socket", _DeniedSocket)

# Kiro C5 ruling: set to "ACCEPT-SUPERSEDE" or "REFUSE" before merging behavior change.
C5_SECOND_RUN_RULING: str | None = "REFUSE"


def _coordinator(boundary, source, *, processed=None, fault=None):
    return IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary,
        source,
        enabled=True,
        processed=processed,
        fault=fault,
    )


def test_1_stale_empty_processed_override_captures_disk_via_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 4)
    _coordinator(boundary, source).run()
    disk_entry = None
    processed_path = Path(boundary.layout["processed"])
    processed_on_disk = json.loads(processed_path.read_text(encoding="utf-8"))
    for entry in processed_on_disk.values():
        if isinstance(entry, dict) and entry.get("path") == str(source):
            disk_entry = entry
            break
    assert disk_entry is not None
    source.write_bytes(
        source.read_bytes()
        + kiro_record(4)
    )
    captured: dict = {}
    cfg = tomllib.loads(
        Path(boundary.layout["user_config"]).read_text(encoding="utf-8")
    )

    def fault(point: str) -> None:
        if point == "after_rollback_publish":
            rollback_path = next(Path(boundary.layout["state"]).rglob("rollback.json"))
            rollback = json.loads(rollback_path.read_text(encoding="utf-8"))
            captured["processed_preimage"] = rollback.get("processed_preimage")
            raise incremental_jsonl.IncrementalJsonlError("synthetic_abort", "stop")

    real_init = IncrementalJsonlCoordinator.__init__

    def routed_init(self, *args, **kwargs):
        kwargs["fault"] = fault
        return real_init(self, *args, **kwargs)

    monkeypatch.setattr(IncrementalJsonlCoordinator, "__init__", routed_init)
    with pytest.raises(IncrementalJsonlError, match="synthetic_abort"):
        incremental_jsonl.maybe_route_incremental(
            cfg=cfg,
            idx=cfg["index"],
            path=str(source),
            path_key=str(source),
            file_hash="stale-caller",
            processed={},
            models=cfg.get("models"),
            tool="kiro",
            units_export=Path(cfg["index"]["units_export"]),
            chunk_size=int(cfg.get("index", {}).get("chunk_size", 2)),
            overlap=int(cfg.get("index", {}).get("chunk_overlap", 0)),
            min_confidence=0.6,
            force_reindex=False,
            supersede_on_reindex=False,
            verbose=False,
            detected_format="jsonl_kiro_session",
        )
    monkeypatch.setattr(IncrementalJsonlCoordinator, "__init__", real_init)
    preimage = captured.get("processed_preimage") or {}
    assert preimage
    assert any(v == disk_entry for v in preimage.values())


def test_2_stale_nonempty_processed_override_captures_latest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    first = _coordinator(boundary, source)
    first.run()
    processed_path = Path(boundary.layout["processed"])
    stale_snapshot = json.loads(processed_path.read_text(encoding="utf-8"))
    source.write_bytes(source.read_bytes() + b'{"payload":{"type":"user","content":"extra"}}\n')
    first.run()
    expected_slice = {
        k: v
        for k, v in load_processed(str(processed_path)).items()
        if isinstance(v, dict) and v.get("path") == str(source)
    }
    source.write_bytes(source.read_bytes() + b'{"payload":{"type":"user","content":"more"}}\n')
    captured: dict = {}
    holder: dict = {}

    def fault(point: str) -> None:
        if point == "after_rollback_publish":
            coord = holder["coordinator"]
            rollback = json.loads(
                coord.paths["rollback"].read_text(encoding="utf-8")
            )
            captured["processed_preimage"] = rollback.get("processed_preimage")
            raise incremental_jsonl.IncrementalJsonlError("synthetic_abort", "stop")

    stale = _coordinator(boundary, source, processed=stale_snapshot, fault=fault)
    holder["coordinator"] = stale
    with pytest.raises(IncrementalJsonlError, match="synthetic_abort"):
        stale.run()
    preimage = captured.get("processed_preimage") or {}
    assert preimage == expected_slice
    assert preimage != {
        k: v
        for k, v in stale_snapshot.items()
        if isinstance(v, dict) and v.get("path") == str(source)
    }


def _pending_apply_coordinator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, records: int = 2
):
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, records)
    _coordinator(boundary, source).run()
    source.write_bytes(source.read_bytes() + kiro_record(records))
    crashed = worker_run(boundary, env, source, fault="after_unit_upsert")
    assert crashed.returncode == 86
    return boundary, source, _coordinator(boundary, source)


def _byte_artifacts(boundary, coordinator) -> dict[str, bytes | dict[str, bytes]]:
    tx_path = coordinator.paths["transaction"]
    rb_path = coordinator.paths["rollback"]
    tx = json.loads(tx_path.read_text(encoding="utf-8"))
    snap_dir = coordinator.paths["snapshots"] / tx["transaction_id"]
    snapshot = {
        str(item.relative_to(snap_dir)): item.read_bytes()
        for item in snap_dir.rglob("*")
        if item.is_file()
    }
    processed_path = Path(boundary.layout["processed"])
    export_path = Path(boundary.layout["export"])
    return {
        "transaction": tx_path.read_bytes(),
        "rollback": rb_path.read_bytes(),
        "snapshot": snapshot,
        "processed": processed_path.read_bytes() if processed_path.is_file() else b"",
        "export": export_path.read_bytes() if export_path.is_file() else b"",
    }


def _publish_tampered_rollback(coordinator, mutator) -> None:
    rollback = json.loads(coordinator.paths["rollback"].read_text(encoding="utf-8"))
    mutator(rollback)
    raw = json.dumps(rollback, sort_keys=True, separators=(",", ":")).encode("utf-8")
    coordinator.paths["rollback"].write_bytes(raw)
    tx = json.loads(coordinator.paths["transaction"].read_text(encoding="utf-8"))
    tx["rollback_authority_sha256"] = hashlib.sha256(raw).hexdigest()
    coordinator.paths["transaction"].write_text(
        json.dumps(tx, sort_keys=True), encoding="utf-8"
    )


def _assert_artifacts_unchanged(before, after) -> None:
    assert after["transaction"] == before["transaction"]
    assert after["rollback"] == before["rollback"]
    assert after["snapshot"] == before["snapshot"]
    assert after["processed"] == before["processed"]
    assert after["export"] == before["export"]


def _mutate_lineage_mismatch(rollback: dict) -> None:
    embedded = incremental_jsonl._embedded_rollback_checkpoint(rollback.get("state_files"))
    preimage = rollback.get("processed_preimage") or {}
    if not embedded or not preimage:
        return
    key = str(embedded.get("processed_hash") or "")
    if key in preimage and isinstance(preimage[key], dict):
        preimage[key]["incremental_jsonl_lineage"] = "deadbeef"


@pytest.mark.parametrize(
    "case,match",
    [
        ("empty_checkpoint", "empty processed preimage with prior checkpoint"),
        ("wrong_key", "processed preimage checkpoint key mismatch"),
        ("wrong_lineage", "processed preimage lineage mismatch"),
        ("foreign_path", "processed preimage foreign path"),
        ("wrong_type", "processed_preimage invalid"),
    ],
)
def test_3_real_recovery_path_refuses_tampered_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    match: str,
) -> None:
    boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)

    def mutator(rollback: dict) -> None:
        if case == "empty_checkpoint":
            rollback["processed_preimage"] = {}
        elif case == "wrong_key":
            preimage = dict(rollback.get("processed_preimage") or {})
            if preimage:
                value = next(iter(preimage.values()))
                rollback["processed_preimage"] = {"wrong-key": dict(value)}
        elif case == "wrong_lineage":
            _mutate_lineage_mismatch(rollback)
        elif case == "foreign_path":
            preimage = rollback.get("processed_preimage") or {}
            if preimage:
                next(iter(preimage.values()))["path"] = "/foreign-path"
        elif case == "wrong_type":
            rollback["processed_preimage"] = []

    _publish_tampered_rollback(coordinator, mutator)
    before = _byte_artifacts(boundary, coordinator)
    _fail_forward_commit_once(monkeypatch)
    with pytest.raises(IncrementalJsonlError, match=match):
        coordinator.run()
    after = _byte_artifacts(boundary, coordinator)
    _assert_artifacts_unchanged(before, after)


def test_4_legitimate_empty_preimage_for_new_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    rollback = {
        "version": 2,
        "summaries": [],
        "units": [],
        "export_preimage": {"version": 2, "source_lines": []},
        "processed_preimage": {},
        "source_path": str(source),
        "state_files": {"checkpoint": None, "transaction": None, "rollback": None},
    }
    coordinator._preflight_rollback_restore(rollback)


def test_6_concurrent_foreign_processed_writer_survives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    snapshot = coordinator._snapshot_before_images()
    processed_path = str(boundary.layout["processed"])
    lock_path = Path(processed_path).with_suffix(".json.lock")
    foreign_key = "foreign-" + hashlib.sha256(b"foreign").hexdigest()
    unrelated_key = "unrelated-" + hashlib.sha256(b"unrelated").hexdigest()
    before_unrelated = {
        k: v
        for k, v in load_processed(processed_path).items()
        if k != foreign_key
    }
    before_unrelated[unrelated_key] = {"path": "/other-source", "chunks": 1}
    mutate_processed(
        processed_path,
        lambda data: data.update({unrelated_key: before_unrelated[unrelated_key]}),
    )

    import ingest

    original_mutate = ingest.mutate_processed
    restore_pause = threading.Event()
    restore_release = threading.Event()
    foreign_attempting = threading.Event()
    foreign_first_mutated = threading.Event()
    thread_errors: list[BaseException] = []

    def _mutate_with_restore_pause(path, mutator):
        if threading.current_thread().name.startswith("restore"):
            def paused(data: dict) -> None:
                restore_pause.set()
                restore_release.wait(timeout=5)
                mutator(data)

            return original_mutate(path, paused)
        return original_mutate(path, mutator)

    monkeypatch.setattr(ingest, "mutate_processed", _mutate_with_restore_pause)

    def _foreign_iud() -> None:
        try:
            foreign_attempting.set()

            def first_mut(data: dict) -> None:
                data.update({foreign_key: {"path": "/other", "chunks": 1}})
                foreign_first_mutated.set()

            mutate_processed(processed_path, first_mut)
            mutate_processed(
                processed_path,
                lambda data: data.update({foreign_key: {"path": "/other", "chunks": 2}}),
            )
            mutate_processed(processed_path, lambda data: data.pop(foreign_key, None))
        except Exception as exc:  # pragma: no cover - surfaced below  # pylint: disable=broad-exception-caught
            thread_errors.append(exc)

    restore_thread = threading.Thread(
        target=lambda: coordinator._restore_processed(
            snapshot.get("processed_preimage") or {}
        ),
        name="restore-first",
    )
    restore_thread.start()
    restore_pause.wait(timeout=5)
    foreign_thread = threading.Thread(target=_foreign_iud, name="foreign")
    foreign_thread.start()
    foreign_attempting.wait(timeout=5)
    assert not foreign_first_mutated.wait(timeout=0.3)
    restore_release.set()
    restore_thread.join(timeout=10)
    foreign_thread.join(timeout=10)
    assert not restore_thread.is_alive()
    assert not foreign_thread.is_alive()
    assert not thread_errors
    after_unrelated = {
        k: v
        for k, v in load_processed(processed_path).items()
        if k != foreign_key
    }
    assert after_unrelated == before_unrelated
    assert lock_path.is_file()

    holder_ready = threading.Event()
    holder_release = threading.Event()
    thread_errors.clear()

    def _hold_and_mutate() -> None:
        try:

            def block(data: dict) -> None:
                holder_ready.set()
                data.update({foreign_key: {"path": "/other", "chunks": 1}})
                data.update({foreign_key: {"path": "/other", "chunks": 2}})
                data.pop(foreign_key, None)
                holder_release.wait(timeout=5)

            original_mutate(processed_path, block)
        except Exception as exc:  # pragma: no cover - surfaced below  # pylint: disable=broad-exception-caught
            thread_errors.append(exc)

    hold_thread = threading.Thread(target=_hold_and_mutate, name="holder")
    hold_thread.start()
    holder_ready.wait(timeout=5)
    restore_thread2 = threading.Thread(
        target=lambda: coordinator._restore_processed(
            snapshot.get("processed_preimage") or {}
        ),
        name="restore-second",
    )
    restore_thread2.start()
    restore_thread2.join(timeout=0.2)
    assert restore_thread2.is_alive()
    holder_release.set()
    hold_thread.join(timeout=10)
    restore_thread2.join(timeout=10)
    assert not hold_thread.is_alive()
    assert not restore_thread2.is_alive()
    assert not thread_errors
    after_unrelated2 = {
        k: v
        for k, v in load_processed(processed_path).items()
        if k != foreign_key
    }
    assert after_unrelated2 == before_unrelated
    assert lock_path.is_file()



def test_7_later_same_source_processed_refused_at_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    snapshot = coordinator._snapshot_before_images()
    processed_path = Path(boundary.layout["processed"])
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    processed["later"] = {"path": str(source), "chunks": 3}
    processed_path.write_text(json.dumps(processed), encoding="utf-8")
    with pytest.raises(IncrementalJsonlError, match="not transaction-owned"):
        coordinator._preflight_rollback_restore(snapshot)


def test_9_unowned_export_line_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    snapshot = coordinator._snapshot_before_images()
    export_path = Path(boundary.layout["export"])
    line = json.dumps({"id": "extra-unit", "source_path": str(source)}) + "\n"
    with export_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
    with pytest.raises(IncrementalJsonlError, match="unowned export"):
        coordinator._preflight_rollback_restore(snapshot)


def test_10_recovery_lock_order_source_before_c1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    _coordinator(boundary, source).run()
    source.write_bytes(source.read_bytes() + kiro_record(2))
    crashed = worker_run(boundary, env, source, fault="after_unit_upsert")
    assert crashed.returncode == 86
    coordinator = _coordinator(boundary, source)
    depths: list[tuple[str, int, int]] = []
    import contextlib
    import purge_locks

    original_source = purge_locks.source_flock
    original_c1 = purge_locks.index_write_flock

    @contextlib.contextmanager
    def _wrap_source(cfg, path_key):
        with original_source(cfg, path_key):
            depths.append(("source", source_lock_depth(), index_write_lock_depth()))
            yield

    @contextlib.contextmanager
    def _wrap_c1(cfg):
        with original_c1(cfg):
            depths.append(("c1", source_lock_depth(), index_write_lock_depth()))
            yield

    monkeypatch.setattr(purge_locks, "source_flock", _wrap_source)
    monkeypatch.setattr(purge_locks, "index_write_flock", _wrap_c1)
    _fail_forward_commit_once(monkeypatch)
    result = coordinator.run()
    assert result.outcome == "rolled_back"
    source_events = [entry for entry in depths if entry[0] == "source"]
    assert len(source_events) == 1
    assert source_events[0][2] == 0
    assert all(c1_depth == 0 for _, _, c1_depth in source_events)



def test_source_flock_not_nested_on_recovery_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    crashed = worker_run(boundary, env, source, fault="after_unit_upsert")
    assert crashed.returncode != 0
    coordinator = _coordinator(boundary, source)
    rollback = json.loads(coordinator.paths["rollback"].read_text(encoding="utf-8"))
    rollback_sha = hashlib.sha256(coordinator.paths["rollback"].read_bytes()).hexdigest()
    snapshot_dir = coordinator.paths["snapshots"] / json.loads(
        coordinator.paths["transaction"].read_text(encoding="utf-8")
    )["transaction_id"]
    depths: list[int] = []
    import contextlib
    import purge_locks

    original_source = purge_locks.source_flock

    @contextlib.contextmanager
    def _wrap(cfg, path_key):
        depths.append(purge_locks.source_lock_depth())
        with original_source(cfg, path_key):
            yield

    monkeypatch.setattr(purge_locks, "source_flock", _wrap)
    coordinator._preflight_rollback_restore = (  # type: ignore[method-assign]
        lambda *args, **kwargs: None
    )
    coordinator._restore_replay_before_images(
        rollback, rollback_sha, snapshot_dir, transaction={}
    )
    assert max(depths) <= 1


def test_foreign_key_collision_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    snapshot = coordinator._snapshot_before_images()
    key = next(iter(snapshot["processed_preimage"]))
    processed_path = Path(boundary.layout["processed"])
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    processed[key] = {"path": "/other-source", "chunks": 1}
    processed_path.write_text(json.dumps(processed), encoding="utf-8")
    with pytest.raises(IncrementalJsonlError, match="foreign key collision"):
        coordinator._preflight_rollback_restore(snapshot)


def _artifact_bytes(boundary) -> dict[str, bytes]:
    root = Path(boundary.layout["state"])
    artifacts: dict[str, bytes] = {}
    if root.is_dir():
        for path in root.rglob("*"):
            if path.is_file():
                artifacts[str(path.relative_to(root))] = path.read_bytes()
    for label in ("processed", "export"):
        path = Path(boundary.layout[label])
        artifacts[label] = path.read_bytes() if path.is_file() else b""
    return artifacts


def _ensure_processed_file(boundary) -> Path:
    path = Path(boundary.layout["processed"])
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    return path




def _fail_forward_commit_once(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[int] = []
    original = IncrementalJsonlCoordinator._commit_generation

    def _fail(self, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise IncrementalJsonlError("synthetic_forward_fail", "stop")
        return original(self, **kwargs)

    monkeypatch.setattr(IncrementalJsonlCoordinator, "_commit_generation", _fail)

def test_5_foreign_owner_unrelated_map_equality_on_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    snapshot = coordinator._snapshot_before_images()
    key = next(iter(snapshot["processed_preimage"]))
    processed_path = _ensure_processed_file(boundary)
    before = json.loads(processed_path.read_text(encoding="utf-8"))
    unrelated_key = "unrelated-" + hashlib.sha256(b"unrelated").hexdigest()
    before[unrelated_key] = {"path": "/other-source", "chunks": 1}
    unrelated_before = {k: v for k, v in before.items() if k != key}
    before[key] = {"path": "/foreign-owner", "chunks": 1}
    processed_path.write_text(json.dumps(before), encoding="utf-8")
    with pytest.raises(IncrementalJsonlError, match="foreign key collision"):
        coordinator._preflight_rollback_restore(snapshot)
    after = json.loads(processed_path.read_text(encoding="utf-8"))
    unrelated_after = {k: v for k, v in after.items() if k != key}
    assert unrelated_after == unrelated_before


@pytest.mark.parametrize(
    "fault,replay_outcome",
    [
        ("before_checkpoint_publish", "committed"),
        ("after_checkpoint_publish", "committed"),
        ("after_processed_publish", "committed"),
    ],
)
def test_8_crash_windows_preserve_authority_and_idempotent_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    replay_outcome: str,
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 4)
    _coordinator(boundary, source).run()
    source.write_bytes(source.read_bytes() + kiro_record(4))
    crashed = worker_run(boundary, env, source, fault=fault)
    assert crashed.returncode == 86
    coordinator = _coordinator(boundary, source)
    assert coordinator.paths["rollback"].is_file()
    assert coordinator.paths["transaction"].is_file()
    rollback_before = coordinator.paths["rollback"].read_bytes()
    tx_before = coordinator.paths["transaction"].read_bytes()
    _fail_forward_commit_once(monkeypatch)
    first = coordinator.run()
    assert first.outcome == "rolled_back"
    assert rollback_before and tx_before
    replay = _coordinator(boundary, source)
    second = replay.run()
    assert second.outcome == replay_outcome
    assert second.counters.total == 0



def test_8_corrupt_prepared_artifact_preserves_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    tx = json.loads(coordinator.paths["transaction"].read_text(encoding="utf-8"))
    prepared_key = next(iter(tx.get("prepared_keys") or []), None)
    assert prepared_key
    prepared_path = coordinator._prepared_path(prepared_key)
    rollback = json.loads(coordinator.paths["rollback"].read_text(encoding="utf-8"))
    journal_key = (
        prepared_key
        if prepared_key.endswith(".json")
        else f"{prepared_key}.json"
    )
    expected_prepared = rollback["prepared_files"][journal_key]
    prepared_path.write_text('{"corrupt": true}', encoding="utf-8")
    _fail_forward_commit_once(monkeypatch)
    result = coordinator.run()
    assert result.outcome == "rolled_back"
    assert prepared_path.read_text(encoding="utf-8") == expected_prepared

def test_non_conflict_processed_restore_propagates_after_partial_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    rollback_before = coordinator.paths["rollback"].read_bytes()
    tx_before = coordinator.paths["transaction"].read_bytes()

    def _raise_non_conflict(_preimage: dict) -> None:
        raise IncrementalJsonlError(
            "recovery_unproven",
            "synthetic non-conflict after partial surface restore",
        )

    coordinator._restore_processed = _raise_non_conflict  # type: ignore[method-assign]
    _fail_forward_commit_once(monkeypatch)
    with pytest.raises(
        IncrementalJsonlError,
        match="synthetic non-conflict after partial surface restore",
    ) as excinfo:
        coordinator.run()
    assert excinfo.value.code == "recovery_unproven"
    assert coordinator.paths["rollback"].read_bytes() == rollback_before
    assert coordinator.paths["transaction"].read_bytes() == tx_before
    assert coordinator.counters.total == 0


def test_c5_recovery_partial_after_late_processed_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    rollback_before = coordinator.paths["rollback"].read_bytes()
    tx_before = coordinator.paths["transaction"].read_bytes()
    processed_path = _ensure_processed_file(boundary)
    late_key = "late-" + hashlib.sha256(b"late").hexdigest()
    original_restore_processed = coordinator._restore_processed

    def restore_with_late_write(preimage: dict) -> None:
        late = json.loads(processed_path.read_text(encoding="utf-8"))
        late[late_key] = {"path": str(_source), "chunks": 2}
        processed_path.write_text(json.dumps(late), encoding="utf-8")
        original_restore_processed(preimage)

    coordinator._restore_processed = restore_with_late_write  # type: ignore[method-assign]
    _fail_forward_commit_once(monkeypatch)
    result = coordinator.run()
    assert result.outcome == "recovery_partial"
    assert coordinator.paths["rollback"].read_bytes() == rollback_before
    assert coordinator.paths["transaction"].read_bytes() == tx_before
    assert late_key in json.loads(processed_path.read_text(encoding="utf-8"))
    replay = _coordinator(boundary, _source)
    second = replay.run()
    assert second.counters.total == 0
    if C5_SECOND_RUN_RULING == "ACCEPT-SUPERSEDE":
        assert second.outcome == "committed"
        assert not replay.paths["rollback"].exists()
        assert not replay.paths["transaction"].exists()
        processed_after = json.loads(processed_path.read_text(encoding="utf-8"))
        assert late_key not in processed_after
    elif C5_SECOND_RUN_RULING == "REFUSE":
        assert second.outcome == "recovery_partial"
        assert replay.paths["rollback"].read_bytes() == rollback_before
        assert replay.paths["transaction"].read_bytes() == tx_before
        assert late_key in json.loads(processed_path.read_text(encoding="utf-8"))
    else:
        pytest.skip("awaiting Kiro C5 ruling (ACCEPT-SUPERSEDE vs REFUSE)")

    third = _coordinator(boundary, _source)
    third_result = third.run()
    assert third_result.outcome == "recovery_partial"
    assert third_result.counters.total == 0
    assert third.paths["rollback"].read_bytes() == rollback_before
    assert third.paths["transaction"].read_bytes() == tx_before
    assert late_key in json.loads(processed_path.read_text(encoding="utf-8"))







def test_refuse_tampered_rollback_semantics_with_late_same_source_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    processed_path = _ensure_processed_file(boundary)
    late_key = "late-" + hashlib.sha256(b"late-tamper").hexdigest()
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    processed[late_key] = {"path": str(_source), "chunks": 2}
    processed_path.write_text(json.dumps(processed), encoding="utf-8")

    def _mutate(rb: dict) -> None:
        rb["processed_preimage"] = {}
        rb["state_files"] = {
            "checkpoint": None,
            "transaction": None,
            "rollback": None,
        }

    _publish_tampered_rollback(coordinator, _mutate)
    before = _byte_artifacts(boundary, coordinator)
    _fail_forward_commit_once(monkeypatch)
    with pytest.raises(
        IncrementalJsonlError, match="empty processed preimage with prior rows"
    ):
        coordinator.run()
    assert coordinator.counters.total == 0
    after = _byte_artifacts(boundary, coordinator)
    _assert_artifacts_unchanged(before, after)
    assert late_key in json.loads(processed_path.read_text(encoding="utf-8"))


def test_normal_commit_supersedes_stale_same_source_processed_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    processed_path = _ensure_processed_file(boundary)
    stale_key = "stale-" + hashlib.sha256(b"stale").hexdigest()
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    processed[stale_key] = {"path": str(source), "chunks": 1}
    processed_path.write_text(json.dumps(processed), encoding="utf-8")
    source.write_bytes(source.read_bytes() + kiro_record(2))
    replay = _coordinator(boundary, source)
    result = replay.run()
    assert result.outcome == "committed"
    after = json.loads(processed_path.read_text(encoding="utf-8"))
    assert stale_key not in after


def test_roll_forward_source_fence_covers_final_processed_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later same-source writer cannot publish during roll-forward finalization."""
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    source.write_bytes(source.read_bytes() + kiro_record(2))

    import ingest
    import purge_locks

    real_commit = ingest.commit_processed_index_entry
    writer_started = threading.Event()
    writer_acquired = threading.Event()
    writer_publish = threading.Event()
    writer_errors: list[BaseException] = []
    writer_threads: list[threading.Thread] = []
    late_key = "late-writer-" + hashlib.sha256(b"late-writer").hexdigest()
    path_key = str(source.expanduser().resolve())
    processed_path = str(coordinator.cfg["index"]["processed_log"])

    def late_writer() -> None:
        try:
            writer_started.set()
            with purge_locks.source_flock(coordinator.cfg, path_key):
                writer_acquired.set()
                if not writer_publish.wait(timeout=5):
                    raise AssertionError("late writer was not released")
                assert real_commit(
                    processed_path,
                    file_hash=late_key,
                    path_key=path_key,
                    chunks=99,
                    units=99,
                )
        except BaseException as exc:  # noqa: BLE001 - report thread failures below
            writer_errors.append(exc)

    def intercepted_commit(*args, **kwargs):
        thread = threading.Thread(target=late_writer, name="late-writer")
        writer_threads.append(thread)
        thread.start()
        assert writer_started.wait(timeout=5)
        # The source lock must still be held while the recovery writer publishes
        # processed.json. On the old path this event becomes set immediately.
        assert not writer_acquired.wait(timeout=0.5)
        return real_commit(*args, **kwargs)

    monkeypatch.setattr(ingest, "commit_processed_index_entry", intercepted_commit)
    try:
        result = coordinator.run()
    finally:
        writer_publish.set()
        for thread in writer_threads:
            thread.join(timeout=5)

    assert not any(thread.is_alive() for thread in writer_threads)
    assert writer_errors == []
    assert result.outcome == "committed"
    assert late_key in load_processed(processed_path)


def test_roll_forward_commits_with_transaction_owned_processed_keys_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    tx = json.loads(coordinator.paths["transaction"].read_text(encoding="utf-8"))
    owned_key = tx.get("prefix_sha256")
    assert owned_key
    processed_path = _ensure_processed_file(boundary)
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    processed[owned_key] = {"path": str(source), "chunks": 1}
    processed_path.write_text(json.dumps(processed), encoding="utf-8")
    _fail_forward_commit_once(monkeypatch)
    first = coordinator.run()
    assert first.outcome == "rolled_back"
    replay = _coordinator(boundary, source)
    second = replay.run()
    assert second.outcome == "committed"
    assert second.counters.total == 0


def test_refuse_empty_processed_preimage_with_prior_rows_c2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    rollback = json.loads(coordinator.paths["rollback"].read_text(encoding="utf-8"))
    rollback["processed_preimage"] = {}
    rollback["state_files"] = {
        "checkpoint": None,
        "transaction": None,
        "rollback": None,
    }
    def _mutate(rb: dict) -> None:
        rb["processed_preimage"] = {}
        rb["state_files"] = {
            "checkpoint": None,
            "transaction": None,
            "rollback": None,
        }

    _publish_tampered_rollback(coordinator, _mutate)
    _fail_forward_commit_once(monkeypatch)
    with pytest.raises(
        IncrementalJsonlError, match="empty processed preimage with prior rows"
    ):
        coordinator.run()


def test_refuse_processed_capture_missing_checkpoint_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    checkpoint = coordinator.checkpoint()
    assert checkpoint is not None
    key = str(checkpoint.get("processed_hash") or "")
    assert key
    processed_path = Path(boundary.layout["processed"])
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    processed.pop(key, None)
    processed_path.write_text(json.dumps(processed), encoding="utf-8")
    source.write_bytes(source.read_bytes() + kiro_record(2))
    with pytest.raises(
        IncrementalJsonlError, match="processed capture missing checkpoint entry"
    ):
        coordinator.run()


def test_refuse_processed_capture_stale_vs_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    checkpoint = coordinator.checkpoint()
    key = str(checkpoint.get("processed_hash") or "")
    disk_entry = {"path": str(source), "chunks": 1}
    stale_preimage = {key: {"path": str(source), "chunks": 99}}
    monkeypatch.setattr(
        incremental_jsonl,
        "load_processed",
        lambda _path: {key: disk_entry},
    )
    monkeypatch.setattr(
        incremental_jsonl,
        "_source_processed_entries",
        lambda _processed, _path_key: stale_preimage,
    )
    monkeypatch.setattr(
        coordinator,
        "checkpoint",
        lambda: checkpoint,
    )
    with pytest.raises(
        IncrementalJsonlError, match="processed capture stale vs checkpoint"
    ):
        coordinator._capture_processed_preimage_locked()


def test_refuse_processed_exclusion_blocks_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    processed_path = Path(_boundary.layout["processed"])
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    for entry in processed.values():
        if isinstance(entry, dict) and entry.get("path") == str(_source):
            entry["excluded"] = True
            break
    processed_path.write_text(json.dumps(processed), encoding="utf-8")
    _fail_forward_commit_once(monkeypatch)
    with pytest.raises(
        IncrementalJsonlError, match="processed exclusion blocks restore"
    ):
        coordinator.run()


def test_refuse_unowned_chroma_rows_block_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    with coordinator._session() as session:
        session.store.add_unit(
            "intruder-unit",
            "intruder",
            [0.1] * 8,
            {"source_path": str(_source)},
        )
    _fail_forward_commit_once(monkeypatch)
    with pytest.raises(
        IncrementalJsonlError, match="unowned chroma rows block restore"
    ):
        coordinator.run()


def test_refuse_processed_exclusion_present_during_final_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    import ingest

    original_mutate = ingest.mutate_processed
    rollback = json.loads(coordinator.paths["rollback"].read_text(encoding="utf-8"))
    preimage = rollback.get("processed_preimage") or {}

    def intercept(path, mutator):
        def wrapped(data):
            for key, entry in list(data.items()):
                if isinstance(entry, dict) and entry.get("path") == str(_source):
                    entry = dict(entry)
                    entry["excluded"] = True
                    data[key] = entry
            return mutator(data)

        return original_mutate(path, wrapped)

    monkeypatch.setattr(ingest, "mutate_processed", intercept)
    with pytest.raises(IncrementalJsonlError, match="processed exclusion present"):
        coordinator._restore_processed(preimage)



def test_refuse_foreign_processed_key_owner_during_final_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _boundary, _source, coordinator = _pending_apply_coordinator(tmp_path, monkeypatch)
    import ingest

    original_mutate = ingest.mutate_processed
    rollback = json.loads(coordinator.paths["rollback"].read_text(encoding="utf-8"))
    preimage = rollback.get("processed_preimage") or {}

    def intercept(path, mutator):
        def wrapped(data):
            for key in preimage:
                data[key] = {"path": "/other-source", "chunks": 1}
            return mutator(data)

        return original_mutate(path, wrapped)

    monkeypatch.setattr(ingest, "mutate_processed", intercept)
    with pytest.raises(IncrementalJsonlError, match="foreign processed key owner"):
        coordinator._restore_processed(preimage)

def test_transaction_owned_processed_restore_after_partial_apply_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    _coordinator(boundary, source).run()
    source.write_bytes(source.read_bytes() + kiro_record(2))
    crashed = worker_run(boundary, env, source, fault="after_summary_upsert")
    assert crashed.returncode == 86
    coordinator = _coordinator(boundary, source)
    tx = json.loads(coordinator.paths["transaction"].read_text(encoding="utf-8"))
    owned_key = tx.get("prefix_sha256")
    assert owned_key
    processed_path = _ensure_processed_file(boundary)
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    processed[owned_key] = {"path": str(source), "chunks": 1}
    processed_path.write_text(json.dumps(processed), encoding="utf-8")
    _fail_forward_commit_once(monkeypatch)
    result = coordinator.run()
    assert result.outcome == "rolled_back"
    restored = json.loads(processed_path.read_text(encoding="utf-8"))
    assert owned_key not in restored


# ref: ../incremental_jsonl.py — forward roll-forward publication fence under test
# ref: ../ingest.py — legacy and incremental processed publication helpers
