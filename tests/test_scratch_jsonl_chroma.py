"""Focused real-Chroma evidence for the isolated JSONL projection seam."""

from __future__ import annotations

import json
from pathlib import Path

from scratch_jsonl_prototype.chroma_projection import ScratchChromaProjection
from scratch_jsonl_prototype.engine import ScratchIncrementalJsonl
from scratch_jsonl_prototype.isolation import ScratchBoundary, create_fresh_root


def _record(index: int) -> bytes:
    return (
        json.dumps(
            {"payload": {"type": "user", "content": f"message-{index}"}},
            sort_keys=True,
        )
        + "\n"
    ).encode()


def test_incremental_engine_projects_real_chroma_and_prunes_source_scope(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    boundary = ScratchBoundary(root, token)
    source = root / "sources" / "sess_scratch" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_bytes(_record(0) + _record(1))
    projection = ScratchChromaProjection(boundary, source_path=source)

    first = ScratchIncrementalJsonl(boundary, source, projection=projection).run()
    assert first.transform_calls == 1
    assert len(projection.rows()) == 1
    assert projection.authority()["chroma_dir"].startswith(str(root))

    with source.open("ab") as handle:
        handle.write(_record(2))
    second = ScratchIncrementalJsonl(boundary, source, projection=projection).run()
    assert second.transform_calls == 1
    rows = projection.rows()
    assert len(rows) == 2
    assert {row["metadata"]["source_identity"] for row in rows} == {
        projection.source_identity
    }
    assert projection.prune(generation=second.active_generation, keep_ids={rows[0]["id"]}) == 1
    assert len(projection.rows()) == 1
