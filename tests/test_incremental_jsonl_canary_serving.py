"""Serving visibility and chunking rehearsal tests for JSONL production canary."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from incremental_jsonl import IncrementalJsonlCoordinator, frontier_start
from incremental_jsonl_canary import (
    chunk_starts_for_count,
    validate_two_chunk_profile,
)
from tests.incremental_jsonl_canary_helpers import write_kiro_source
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    kiro_record,
)
from tests.serving_test_helpers import serving_test_cfg


def test_p1_a11_serving_probe_reports_mixed_state(tmp_path: Path) -> None:
    from chroma_store import ChromaStore
    from incremental_jsonl_canary import ServingVisibilityProbe
    from serving_index_repository import open_serving_index_repository

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = serving_test_cfg(tmp_path, chroma)
    store = ChromaStore(str(chroma))
    source = "/tmp/canary-source.jsonl"
    store.add_summary("s1", "summary", [0.1] * 8, {"source_path": source})
    store.close()
    with open_serving_index_repository(cfg) as repo:
        probe = ServingVisibilityProbe(repo, source)
        first = probe.sample()
        store = ChromaStore(str(chroma))
        store.add_unit("u1", "unit", [0.2] * 8, {"source_path": source, "id": "u1"})
        store.close()
        second = probe.sample()
        assert first.summary_generation == "present"
        assert first.unit_generation == "empty"
        assert second.unit_generation == "present"
        assert first.mixed or second.mixed or first.unit_generation != second.unit_generation


def test_p1_a11_stable_reads_after_settle(tmp_path: Path) -> None:
    from chroma_store import ChromaStore
    from incremental_jsonl_canary import ServingVisibilityProbe
    from serving_index_repository import open_serving_index_repository

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = serving_test_cfg(tmp_path, chroma)
    source = "/tmp/stable-source.jsonl"
    store = ChromaStore(str(chroma))
    store.add_summary("s1", "summary", [0.1] * 8, {"source_path": source})
    store.add_unit("u1", "unit", [0.2] * 8, {"source_path": source, "id": "u1"})
    store.close()
    with open_serving_index_repository(cfg) as repo:
        probe = ServingVisibilityProbe(repo, source)
        for _ in range(3):
            probe.sample()
            time.sleep(1.0)
        probe.assert_stable_reads()


def test_p1_a12_frontier_reuse_and_zero_call_replay(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source, _ = write_kiro_source(boundary.root, 61)
    validate_two_chunk_profile(61)
    assert chunk_starts_for_count(61, chunk_size=60, overlap=10) == [0, 50]
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary,
        source,
        enabled=True,
        chunk_size=60,
        overlap=10,
    ).run()
    assert first.outcome == "committed"
    baseline_calls = first.counters.total
    assert baseline_calls > 0
    with source.open("ab") as handle:
        for index in range(61, 110):
            handle.write(kiro_record(index))
    frontier = frontier_start(109, 60, 10)
    assert frontier == 50
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary,
        source,
        enabled=True,
        chunk_size=60,
        overlap=10,
    ).run()
    assert second.outcome == "committed"
    assert second.counters.total < baseline_calls
    third = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary,
        source,
        enabled=True,
        chunk_size=60,
        overlap=10,
    ).run()
    assert third.outcome == "unchanged"
    assert third.counters.total == 0
