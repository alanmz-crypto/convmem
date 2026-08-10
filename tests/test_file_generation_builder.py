from __future__ import annotations

import pytest

from distill import make_unit_id
from file_generation_builder import CandidateBuildError, build_candidate_generation


class FakeCommittedStore:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def query_units(self, _embedding, top_k):
        return self.rows[:top_k]

    def get_unit(self, unit_id):
        return next((row for row in self.rows if row.get("id") == unit_id), None)


def _parse(_source):
    return [
        {"start_offset": 0, "end_offset": 1, "text": "a"},
        {"start_offset": 2, "end_offset": 3, "text": "b"},
    ]


def _extract(chunk):
    return f"summary-{chunk['start_offset']}", [
        {"document": f"unit-{chunk['start_offset']}", "metadata": {"title": "T"}}
    ]


def _embed(text):
    return [float(len(text)), 1.0]


def _build(**overrides):
    kwargs = {
        "source_path": "/tmp/cg1/source.jsonl",
        "source_bytes": b"source-v1",
        "parse": _parse,
        "extract_chunk": _extract,
        "embed": _embed,
        "committed_store": FakeCommittedStore(),
        "dedupe_cfg": {"ingest_dedup": {"candidate_k": 10}},
        "pipeline_fingerprint": {"parser": "p1", "model": "m1"},
        "embedding_model": "test-embed-v1",
    }
    kwargs.update(overrides)
    return build_candidate_generation(**kwargs)


def test_candidate_build_is_inert_and_assigns_physical_after_generation():
    candidate = _build()
    assert len(candidate.unit_rows) == 2
    assert len(candidate.summary_rows) == 2
    for row in candidate.all_rows:
        assert row.physical_id.startswith("fg1_")
        assert row.metadata["id"] == row.physical_id
        assert row.metadata["logical_id"] == row.logical_id
        assert row.metadata["generation_id"] == candidate.generation_id
    unit = candidate.unit_rows[0]
    assert unit.logical_id == make_unit_id(
        candidate.canonical_source_path,
        0,
        "T",
        0,
    )


def test_different_nondeterministic_output_changes_generation_id():
    first = _build()

    def changed(chunk):
        return f"summary-{chunk['start_offset']}", [
            {"document": f"changed-{chunk['start_offset']}", "metadata": {}}
        ]

    second = _build(extract_chunk=changed)
    assert first.source_hash == second.source_hash
    assert first.generation_id != second.generation_id


def test_parse_and_embedding_failure_aborts_whole_candidate():
    with pytest.raises(CandidateBuildError, match="parse failed"):
        _build(parse=lambda _raw: (_ for _ in ()).throw(ValueError("bad parse")))

    def bad_embed(text):
        if text.startswith("unit"):
            raise TimeoutError("embed")
        return [1.0, 0.0]

    with pytest.raises(CandidateBuildError, match="embedding failed"):
        _build(embed=bad_embed)

    with pytest.raises(CandidateBuildError, match="extraction failed"):
        _build(extract_chunk=lambda _chunk: ("not-json", {"not": "a list"}))


def test_valid_empty_extraction_builds_intentional_empty_generation():
    candidate = _build(
        parse=lambda _raw: [{"start_offset": 0, "end_offset": 0}],
        extract_chunk=lambda _chunk: ("no facts", []),
    )
    assert not candidate.unit_rows
    assert candidate.summary_rows[0].metadata["distill_status"] == "empty"


def test_persisted_dedupe_ids_are_physical_with_logical_companions():
    existing = {
        "id": "stable-physical",
        "document": "unit-0",
        "distance": 0.01,
        "metadata": {
            "id": "stable-physical",
            "physical_id": "stable-physical",
            "logical_id": "stable-logical",
            "source_path": "/other/source",
        },
    }
    candidate = _build(committed_store=FakeCommittedStore([existing]))
    suppression = candidate.exact_suppressions[0]
    assert suppression["suppressed_id"].startswith("fg1_")
    assert suppression["matched_id"] == "stable-physical"
    assert suppression["suppressed_logical_id"]
    assert suppression["matched_logical_id"] == "stable-logical"


def test_same_logical_id_replacement_is_self_excluded_by_logical_identity():
    probe = _build(parse=lambda _raw: [{"start_offset": 0, "end_offset": 0}])
    row = probe.unit_rows[0]
    existing = {
        "id": "old-physical",
        "document": row.document,
        "distance": 0.0,
        "metadata": {
            "logical_id": row.logical_id,
            "source_path": probe.canonical_source_path,
            "content_hash": row.metadata["content_hash"],
        },
    }
    rebuilt = _build(
        parse=lambda _raw: [{"start_offset": 0, "end_offset": 0}],
        committed_store=FakeCommittedStore([existing]),
    )
    assert len(rebuilt.unit_rows) == 1
    assert not rebuilt.exact_suppressions


def test_same_chunk_and_earlier_chunk_duplicates_preserve_processing_order():
    same_chunk = _build(
        parse=lambda _raw: [{"start_offset": 0, "end_offset": 0}],
        extract_chunk=lambda _chunk: (
            "summary",
            [
                {"document": "duplicate", "metadata": {}},
                {"document": "duplicate", "metadata": {}},
            ],
        ),
    )
    assert len(same_chunk.unit_rows) == 1
    assert len(same_chunk.exact_suppressions) == 1

    earlier_chunk = _build(
        extract_chunk=lambda _chunk: (
            "summary",
            [{"document": "duplicate", "metadata": {}}],
        )
    )
    assert len(earlier_chunk.unit_rows) == 1
    assert len(earlier_chunk.exact_suppressions) == 1


def test_self_source_cross_logical_suppression_is_named_as_projection_loss():
    probe = _build(parse=lambda _raw: [{"start_offset": 0, "end_offset": 0}])
    existing = {
        "id": "old-physical",
        "document": probe.unit_rows[0].document,
        "distance": 0.0,
        "metadata": {
            "logical_id": "different-old-logical",
            "source_path": probe.canonical_source_path,
            "content_hash": probe.unit_rows[0].metadata["content_hash"],
        },
    }
    lossy = _build(
        parse=lambda _raw: [{"start_offset": 0, "end_offset": 0}],
        committed_store=FakeCommittedStore([existing]),
    )
    assert not lossy.unit_rows
    assert lossy.self_source_cross_logical_suppression_count == 1
    assert lossy.known_projection_loss_risks == [
        "self_source_cross_logical_exact_suppression"
    ]
