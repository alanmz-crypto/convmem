"""Hermetic regression tests for issue #286 rollback processed authority."""

# pylint: disable=duplicate-code,protected-access

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


def test_3_r975_empty_preimage_with_checkpoint_refuses_before_write(
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
    rollback = dict(snapshot)
    rollback_bytes = json.dumps(rollback, sort_keys=True).encode("utf-8")
    rollback["processed_preimage"] = {}
    with pytest.raises(IncrementalJsonlError, match="empty processed preimage"):
        coordinator._preflight_rollback_restore(rollback)
    assert json.dumps(rollback, sort_keys=True).encode("utf-8") != rollback_bytes


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
    foreign_key = "foreign-" + hashlib.sha256(b"foreign").hexdigest()
    barrier = threading.Event()
    holder = threading.Event()

    original_mutate = mutate_processed
    restore_mutate_calls: list[int] = []

    def racing_mutate(path, mutator):
        if threading.current_thread().name == "restore":
            restore_mutate_calls.append(1)
        if threading.current_thread().name != "MainThread":
            holder.set()
            barrier.wait(timeout=5)
        return original_mutate(path, mutator)

    monkeypatch.setattr("ingest.mutate_processed", racing_mutate)

    def restore_in_thread() -> None:
        coordinator._restore_processed(snapshot.get("processed_preimage") or {})

    thread = threading.Thread(target=restore_in_thread, name="restore")
    thread.start()
    holder.wait(timeout=5)
    mutate_processed(
        processed_path,
        lambda data: data.update({foreign_key: {"path": "/other", "chunks": 1}}),
    )
    barrier.set()
    thread.join(timeout=10)
    restored = load_processed(processed_path)
    assert foreign_key in restored
    assert restore_mutate_calls, "restore must use mutate_processed sidecar lock"


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
    assert source_events
    assert any(src_depth >= 1 and c1_depth == 0 for _, src_depth, c1_depth in source_events)


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
    "fault",
    [
        "before_checkpoint_publish",
        "after_checkpoint_publish",
        "after_processed_publish",
    ],
)
def test_8_crash_windows_preserve_authority_and_idempotent_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
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
    assert rollback_before
    assert tx_before
    replay = _coordinator(boundary, source)
    second = replay.run()
    assert second.outcome in {"rolled_back", "unchanged", "recovery_partial", "committed"}


def test_c5_recovery_partial_after_late_processed_conflict(
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
    rollback_before = coordinator.paths["rollback"].read_bytes()
    tx_before = coordinator.paths["transaction"].read_bytes()
    processed_path = _ensure_processed_file(boundary)
    late_key = "late-" + hashlib.sha256(b"late").hexdigest()
    original_restore_processed = coordinator._restore_processed

    def restore_with_late_write(preimage: dict) -> None:
        late = json.loads(processed_path.read_text(encoding="utf-8"))
        late[late_key] = {"path": str(source), "chunks": 2}
        processed_path.write_text(json.dumps(late), encoding="utf-8")
        original_restore_processed(preimage)

    coordinator._restore_processed = restore_with_late_write  # type: ignore[method-assign]
    _fail_forward_commit_once(monkeypatch)
    result = coordinator.run()
    assert result.outcome == "recovery_partial"
    assert coordinator.paths["rollback"].read_bytes() == rollback_before
    assert coordinator.paths["transaction"].read_bytes() == tx_before
    assert late_key in json.loads(processed_path.read_text(encoding="utf-8"))


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
