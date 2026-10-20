"""Hermetic regression tests for issue #286 rollback processed authority."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import pytest

import incremental_jsonl
from incremental_jsonl import (
    IncrementalJsonlCoordinator,
    IncrementalJsonlError,
)
from incremental_jsonl_isolation import install_network_denial
from ingest import load_processed, mutate_processed
from purge_locks import index_write_lock_depth, source_lock_depth
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    write_source,
    worker_run,
)


@pytest.fixture(autouse=True)
def _deny_network(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ARG001
    install_network_denial()


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
    first = _coordinator(boundary, source)
    first.run()
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
        + b'{"payload":{"type":"user","content":"more"}}\n'
    )
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

    stale = _coordinator(boundary, source, processed={}, fault=fault)
    holder["coordinator"] = stale
    with pytest.raises(IncrementalJsonlError, match="synthetic_abort"):
        stale.run()
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

    def racing_mutate(path, mutator):
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
    coordinator = _coordinator(boundary, source)
    coordinator.run()
    snapshot = coordinator._snapshot_before_images()
    depths: list[tuple[int, int]] = []

    from purge_locks import index_write_flock, source_flock

    original = coordinator._restore_before_images

    def traced_restore(rollback, **kwargs):
        depths.append((source_lock_depth(), index_write_lock_depth()))
        return original(rollback, **kwargs)

    coordinator._restore_before_images = traced_restore  # type: ignore[method-assign]
    coordinator._preflight_rollback_restore(snapshot)
    with source_flock(coordinator.cfg, coordinator.path_key):
        with index_write_flock(coordinator.cfg):
            coordinator._restore_before_images(snapshot, preserve_recovery_authority=True)
    assert depths
    assert all(src >= 1 and c1 >= 1 for src, c1 in depths)


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


def test_transaction_owned_processed_restore_succeeds(
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
    tx = json.loads(snapshot["state_files"]["transaction"] or "{}")
    processed_path = Path(boundary.layout["processed"])
    processed = json.loads(processed_path.read_text(encoding="utf-8"))
    owned_key = tx.get("prefix_sha256") or tx.get("generation", {}).get("prefix_sha256")
    if owned_key:
        processed[owned_key] = {"path": str(source), "chunks": 9, "units": 9}
        processed_path.write_text(json.dumps(processed), encoding="utf-8")
    coordinator._preflight_rollback_restore(snapshot, transaction=tx)
    coordinator._restore_processed(snapshot.get("processed_preimage") or {})
    restored = json.loads(processed_path.read_text(encoding="utf-8"))
    assert snapshot["processed_preimage"].keys() <= restored.keys()
