from __future__ import annotations

import json
from pathlib import Path

from chroma_store import UNITS
from file_generation_store import STABLE_SCOPE, FileGenerationStore, StagedRow
from ingest_dedupe import (
    IngestDedupeResult,
    evaluate_ingest_batch,
    persist_ingest_dedupe,
)
from refine import apply_dedupe_queue_record


def _row(physical: str, logical: str, embedding: list[float], *, owner="owner"):
    return StagedRow(
        UNITS,
        physical,
        logical,
        f"document-{logical}",
        embedding,
        {
            "source_path": "/tmp/source.jsonl",
            "title": logical,
            "embedding_model": "test",
            "embedding_dimension": len(embedding),
        },
        "file",
        owner,
        "N",
    )


def test_persisted_semantic_record_resolves_real_approval_path(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "ingest_dedup": {
            "semantic_similarity": 0.9,
            "candidate_k": 10,
            "max_semantic_candidates_per_unit": 3,
        },
        "refine": {"queue_max_depth": 100},
    }
    active = {"owner": "N"}
    canonical = _row("fg1_canonical", "L-canonical", [1.0, 0.0])
    tombstone = _row("fg1_tombstone", "L-tombstone", [0.99, 0.01])
    with FileGenerationStore(chroma, active_generations=lambda: active) as store:
        store.stage_rows([canonical, tombstone])
        unit = {
            "id": tombstone.physical_id,
            "physical_id": tombstone.physical_id,
            "logical_id": tombstone.logical_id,
        }
        meta = dict(tombstone.metadata)
        meta.update(
            {
                "id": tombstone.physical_id,
                "physical_id": tombstone.physical_id,
                "logical_id": tombstone.logical_id,
            }
        )
        outcome = evaluate_ingest_batch(
            store,
            cfg,
            [(unit, tombstone.document, tombstone.embedding, meta)],
            generation_identity_fields=True,
        )
        assert outcome.semantic_candidates
        record = outcome.semantic_candidates[0]
        assert {record["id_a"], record["id_b"]} == {
            canonical.physical_id,
            tombstone.physical_id,
        }
        assert {record["logical_id_a"], record["logical_id_b"]} == {
            canonical.logical_id,
            tombstone.logical_id,
        }

        stats = persist_ingest_dedupe(cfg, outcome)
        assert stats["semantic_candidates_queued"] == 1
        persisted = json.loads(
            (tmp_path / "dedupe_queue.jsonl").read_text(encoding="utf-8").strip()
        )
        assert persisted["id_a"] == record["id_a"]
        assert persisted["logical_id_a"] == record["logical_id_a"]

        persisted.update(
            {
                "status": "approved_merge_b_canonical",
                "tombstone_id": tombstone.physical_id,
                "canonical_id": canonical.physical_id,
            }
        )
        applied = apply_dedupe_queue_record(
            store.raw_store, cfg, persisted, verbose=False
        )
        assert applied == {"tombstoned": 1, "skipped": 0, "errors": 0}
        changed = store.raw_store.get_unit(tombstone.physical_id)
        assert changed is not None
        assert changed["metadata"]["superseded"] is True
        assert changed["metadata"]["superseded_by"] == canonical.physical_id

        negative = dict(persisted)
        negative["tombstone_id"] = tombstone.logical_id
        negative["chroma_applied"] = False
        silent = apply_dedupe_queue_record(
            store.raw_store, cfg, negative, verbose=False
        )
        assert silent == {"tombstoned": 0, "skipped": 1, "errors": 0}


def test_physical_pair_uniqueness_grows_per_generation_and_hits_global_cap(
    tmp_path: Path,
) -> None:
    cfg = {
        "index": {"chroma_dir": str(tmp_path / "chroma")},
        "refine": {"queue_max_depth": 4},
    }
    for generation in range(4):
        result = IngestDedupeResult(
            semantic_candidates=[
                {
                    "id_a": f"fg1_{generation}_a",
                    "id_b": f"fg1_{generation}_b",
                    "logical_id_a": "L-a",
                    "logical_id_b": "L-b",
                    "similarity": 0.95,
                    "status": "pending",
                }
            ]
        )
        assert persist_ingest_dedupe(cfg, result)["semantic_candidates_queued"] == 1

    paused = persist_ingest_dedupe(
        cfg,
        IngestDedupeResult(
            semantic_candidates=[{"id_a": "fg1_4_a", "id_b": "fg1_4_b"}]
        ),
    )
    assert paused["semantic_queue_paused"] is True
    assert paused["semantic_queue_depth"] == 4
    rows = [
        json.loads(line)
        for line in (tmp_path / "dedupe_queue.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 4
    assert len({tuple(sorted((row["id_a"], row["id_b"]))) for row in rows}) == 4
    assert {(row["logical_id_a"], row["logical_id_b"]) for row in rows} == {
        ("L-a", "L-b")
    }


def test_generation_equivalence_does_not_normalize_identifier_fields() -> None:
    physical = {
        "id_a": "fg1_a",
        "id_b": "fg1_b",
        "logical_id_a": "L-a",
        "logical_id_b": "L-b",
    }
    logical_substitution = dict(physical, id_a="L-a", id_b="L-b")
    assert physical != logical_substitution


def test_inactive_duplicate_does_not_influence_dedupe_but_stable_row_does(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    active = {"owner": "N"}
    with FileGenerationStore(chroma, active_generations=lambda: active) as store:
        store.stage_rows(
            [
                _row("fg1_active", "L-active", [0.0, 1.0]),
                StagedRow(
                    UNITS,
                    "stable-decision",
                    "stable-decision",
                    "stable duplicate",
                    [1.0, 0.0],
                    {"content_hash": "not-used"},
                    STABLE_SCOPE,
                ),
            ]
        )
        store.stage_rows(
            [
                StagedRow(
                    UNITS,
                    "fg1_abandoned",
                    "L-abandoned",
                    "abandoned exact",
                    [1.0, 0.0],
                    {"source_path": "/tmp/source.jsonl"},
                    "file",
                    "owner",
                    "A",
                )
            ]
        )
        cfg = {
            "ingest_dedup": {
                "candidate_k": 10,
                "semantic_similarity": 0.9,
                "max_semantic_candidates_per_unit": 3,
            }
        }
        abandoned_candidate = (
            {"id": "fg1_new", "physical_id": "fg1_new", "logical_id": "L-new"},
            "abandoned exact",
            [1.0, 0.0],
            {"logical_id": "L-new", "source_path": "/tmp/new"},
        )
        visible = evaluate_ingest_batch(
            store,
            cfg,
            [abandoned_candidate],
            generation_identity_fields=True,
        )
        assert len(visible.accepted) == 1

        stable_candidate = (
            {"id": "fg1_new2", "physical_id": "fg1_new2", "logical_id": "L-new2"},
            "stable duplicate",
            [1.0, 0.0],
            {"logical_id": "L-new2", "source_path": "/tmp/new"},
        )
        suppressed = evaluate_ingest_batch(
            store,
            cfg,
            [stable_candidate],
            generation_identity_fields=True,
        )
        assert suppressed.accepted == []
        assert suppressed.exact_suppressions[0]["matched_id"] == "stable-decision"


def test_semantic_threshold_and_candidate_k_are_not_changed() -> None:
    class NeighborStore:
        def __init__(self, distance):
            self.distance = distance

        def query_units(self, _embedding, top_k):
            assert top_k == 1
            return [
                {
                    "id": "physical-existing",
                    "document": "different",
                    "distance": self.distance,
                    "metadata": {"logical_id": "logical-existing"},
                }
            ]

    cfg = {
        "ingest_dedup": {
            "candidate_k": 1,
            "semantic_similarity": 0.92,
            "max_semantic_candidates_per_unit": 3,
        }
    }
    batch = [
        (
            {"id": "physical-new", "logical_id": "logical-new"},
            "new",
            [1.0, 0.0],
            {"logical_id": "logical-new"},
        )
    ]
    above = evaluate_ingest_batch(
        NeighborStore(0.079), cfg, batch, generation_identity_fields=True
    )
    below = evaluate_ingest_batch(
        NeighborStore(0.081), cfg, batch, generation_identity_fields=True
    )
    assert len(above.semantic_candidates) == 1
    assert below.semantic_candidates == []
