"""Tests for CG-2 namespaced logical accounting."""

from __future__ import annotations

from logical_accounting import (
    NamespacedLogicalKey,
    PhysicalRowClass,
    build_membership_metrics,
    build_owner_logical_projection_report,
    classify_physical_row,
    logical_id_from_metadata,
    manifest_namespaced_keys,
    membership_ratio,
    namespaced_logical_key,
    projection_key_index,
    STABLE_OWNER_SENTINEL,
)


def test_ledger_id_precedes_logical_id():
    meta = {"ledger_id": "obs_1", "logical_id": "other", "id": "phys"}
    assert logical_id_from_metadata(meta) == "obs_1"
    key = namespaced_logical_key(meta, "knowledge_units")
    assert key == NamespacedLogicalKey(STABLE_OWNER_SENTINEL, "knowledge_units", "obs_1")


def test_empty_set_membership_convention():
    metrics = build_membership_metrics(set(), set())
    assert metrics["completeness"] is None
    assert metrics["purity"] is None
    assert metrics["missing_count"] == 0
    assert metrics["unexpected_count"] == 0
    assert membership_ratio(0, 0) is None


def test_missing_and_unexpected_active_rows():
    expected = {
        NamespacedLogicalKey("owner-a", "knowledge_units", "L1"),
        NamespacedLogicalKey("owner-a", "knowledge_units", "L2"),
    }
    observed = {
        NamespacedLogicalKey("owner-a", "knowledge_units", "L2"),
        NamespacedLogicalKey("owner-a", "knowledge_units", "L3"),
    }
    metrics = build_membership_metrics(expected, observed)
    assert metrics["missing_count"] == 1
    assert metrics["unexpected_count"] == 1
    assert metrics["completeness"] == 0.5
    assert metrics["purity"] == 0.5


def test_duplicate_logical_keys_detected_in_projection_index():
    metas = [
        {"id": "fg1_a", "logical_id": "L1", "generation_scope": "file", "owner_digest": "o"},
        {"id": "fg1_b", "logical_id": "L1", "generation_scope": "file", "owner_digest": "o"},
    ]
    index = projection_key_index(metas, "knowledge_units")
    assert len(index[NamespacedLogicalKey("o", "knowledge_units", "L1")]) == 2


def test_retained_inactive_is_not_wrong_generation():
    meta = {
        "generation_scope": "file",
        "owner_digest": "owner-a",
        "generation_id": "gen-prev",
    }
    classification = classify_physical_row(
        meta,
        collection_kind="knowledge_units",
        active_generations={"owner-a": "gen-active"},
        previous_generations={"owner-a": "gen-prev"},
        known_generations_by_owner={"owner-a": {"gen-active", "gen-prev"}},
    )
    assert classification == PhysicalRowClass.RETAINED_INACTIVE


def test_abandoned_generation_classified():
    meta = {
        "generation_scope": "file",
        "owner_digest": "owner-a",
        "generation_id": "gen-abandoned",
    }
    classification = classify_physical_row(
        meta,
        collection_kind="knowledge_units",
        active_generations={"owner-a": "gen-active"},
        previous_generations={},
        known_generations_by_owner={"owner-a": {"gen-active", "gen-abandoned"}},
    )
    assert classification == PhysicalRowClass.ABANDONED


def test_wrong_generation_classified():
    meta = {
        "generation_scope": "file",
        "owner_digest": "owner-a",
        "generation_id": "gen-stale",
    }
    classification = classify_physical_row(
        meta,
        collection_kind="knowledge_units",
        active_generations={"owner-a": "gen-active"},
        previous_generations={},
        known_generations_by_owner={"owner-a": {"gen-active"}},
    )
    assert classification == PhysicalRowClass.WRONG_GENERATION


def test_legacy_rows_without_generation_scope_count_as_serving():
    meta = {"id": "dec_1", "tool": "cursor"}
    classification = classify_physical_row(
        meta,
        collection_kind="knowledge_units",
        active_generations={},
        previous_generations={},
        known_generations_by_owner={},
    )
    assert classification == PhysicalRowClass.SERVING_STABLE


def test_manifest_projection_report_flags_mismatch():
    manifest = {
        "owner_digest": "owner-a",
        "generation_id": "gen-1",
        "collections": {
            "knowledge_units": {
                "rows": {
                    "fg1_1": {"logical_id": "L1"},
                    "fg1_2": {"logical_id": "L2"},
                }
            }
        },
    }
    expected_keys = manifest_namespaced_keys(manifest)
    assert len(expected_keys) == 2
    chroma_rows = [
        {
            "id": "fg1_1",
            "logical_id": "L1",
            "generation_scope": "file",
            "owner_digest": "owner-a",
            "generation_id": "gen-1",
        },
        {
            "id": "fg1_3",
            "logical_id": "L3",
            "generation_scope": "file",
            "owner_digest": "owner-a",
            "generation_id": "gen-1",
        },
    ]

    class _Rows:
        @staticmethod
        def metadata_rows(_chroma_dir, collection_name):
            if collection_name == "knowledge_units":
                return chroma_rows
            return []

    import logical_accounting as module

    original = module.collection_metadata_rows
    module.collection_metadata_rows = _Rows.metadata_rows
    try:
        report = build_owner_logical_projection_report(manifest, "/tmp/chroma")
    finally:
        module.collection_metadata_rows = original

    assert report["membership"]["missing_count"] == 1
    assert report["membership"]["unexpected_count"] == 1
    assert not report["gate_pass"]


def test_ci_kryptonite_negative_control():
    assert False, "CI gate negative control"
