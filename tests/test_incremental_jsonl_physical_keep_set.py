"""S2 — checkpoint keep sets must use physical Chroma IDs after apply."""

from __future__ import annotations

from pathlib import Path

import pytest

from chroma_store import SUMMARIES, UNITS
from incremental_jsonl import IncrementalJsonlCoordinator
from tests.incremental_jsonl_helpers import (
    enable_incremental,
    install_fakes,
    isolated_env,
    kiro_record,
    write_source,
)


def _physical_ids(coordinator: IncrementalJsonlCoordinator) -> tuple[set[str], set[str]]:
    with coordinator._session() as session:  # pylint: disable=protected-access
        summaries = set(session.store.ids_for_source(SUMMARIES, coordinator.path_key))
        units = set(session.store.ids_for_source(UNITS, coordinator.path_key))
    return summaries, units


def test_checkpoint_manifest_matches_physical_chroma_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    from tests.incremental_jsonl_helpers import apply_env

    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 4)
    coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    )
    result = coordinator.run()
    assert result.outcome == "committed"
    checkpoint = coordinator.checkpoint()
    assert checkpoint is not None
    physical_summaries, physical_units = _physical_ids(coordinator)
    assert set(checkpoint["summary_ids"]) == physical_summaries
    assert set(checkpoint["unit_ids"]) == physical_units
    assert checkpoint["unit_ids"]
    prepared_logical = {
        row["id"] for item in coordinator.paths["prepared"].iterdir() for row in []
    }
    del prepared_logical
    for path in coordinator.paths["prepared"].glob("*.json"):
        payload = __import__("json").loads(path.read_text(encoding="utf-8"))
        logical = {row["id"] for row in payload.get("units", [])}
        if logical and physical_units != logical:
            # Physical IDs may diverge after projection or dedupe; checkpoint must
            # follow Chroma, not prepared logical IDs.
            assert set(checkpoint["unit_ids"]) == physical_units


def test_exact_dedupe_matched_id_retained_in_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    from tests.incremental_jsonl_helpers import apply_env

    apply_env(monkeypatch, env)

    def duplicate_distill(_text, **_kwargs):
        return [
            {
                "type": "explanation",
                "title": "dup",
                "summary": "same canonical body for dedupe",
                "keywords": ["dup"],
                "confidence": 0.95,
                "domain": "general",
            }
        ]

    import ingest

    install_fakes(monkeypatch)
    monkeypatch.setattr(ingest, "distill", duplicate_distill)
    enable_incremental(boundary)
    source = write_source(boundary.root, 4)
    coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    )
    first = coordinator.run()
    assert first.outcome == "committed"
    first_units = set(coordinator.checkpoint()["unit_ids"])
    with source.open("ab") as handle:
        handle.write(kiro_record(4, content="different surface text"))
        handle.write(kiro_record(5, content="another line"))
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    ).run()
    assert second.outcome == "committed"
    checkpoint = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    ).checkpoint()
    _physical_summaries, physical_units = _physical_ids(
        IncrementalJsonlCoordinator.from_isolated_boundary(
            boundary, source, enabled=True, chunk_size=2, overlap=0
        )
    )
    assert set(checkpoint["unit_ids"]) == physical_units
    assert first_units.issubset(physical_units)
