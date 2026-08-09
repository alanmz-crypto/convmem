"""Hermetic tests for export-to-Chroma projection completeness accounting."""

from projection_parity import build_projection_parity_report, entity_key


def test_ledger_identity_uses_ledger_id_instead_of_chroma_uuid():
    exported = {"id": "old-uuid", "ledger_id": "obs_1"}
    active = {"id": "new-uuid", "ledger_id": "obs_1"}
    assert entity_key(exported) == entity_key(active) == "ledger:obs_1"


def test_report_separates_active_claims_history_and_locked_ledger_gap():
    export_rows = [
        {"id": "active", "source_path": "/tmp/active.jsonl"},
        {"id": "old", "source_path": "/tmp/active.jsonl"},
        {"id": "lost", "source_path": "/tmp/lost.jsonl"},
        {"id": "empty", "source_path": "/tmp/empty.jsonl"},
        {
            "id": "ledger-old-uuid",
            "ledger_id": "obs_required",
            "source_path": "site:example.test",
        },
        {"id": "relative", "source_path": "legacy/transcript.md"},
    ]
    active_rows = [{"id": "active", "source_path": "/tmp/active.jsonl"}]
    processed = {
        "hash-active": {"path": "/tmp/active.jsonl", "units": 1, "chunks": 1},
        "hash-lost": {"path": "/tmp/lost.jsonl", "units": 3, "chunks": 1},
        "hash-empty": {"path": "/tmp/empty.jsonl", "units": 0, "chunks": 1},
    }

    report = build_projection_parity_report(
        export_rows,
        active_rows,
        processed,
        required_ledger_ids=["obs_required"],
        path_exists=lambda _path: False,
    )

    metrics = report["metrics"]
    assert metrics["export_only_path_count"] == 5
    assert metrics["export_only_paths_without_active_units_count"] == 4
    assert metrics["processed_nonzero_paths_without_active_units_count"] == 1
    assert metrics["processed_nonzero_expected_units_without_active_units_count"] == 3
    assert metrics["required_ledger_ids_missing_count"] == 1
    assert metrics["unclassified_export_only_paths_count"] == 0
    assert report["gates"]["pass"] is False
    dispositions = {
        row["source_path"]: row["disposition"]
        for row in report["paths_without_active_units"]
    }
    assert dispositions["/tmp/lost.jsonl"] == "processed_nonzero_missing_active_projection"
    assert dispositions["/tmp/empty.jsonl"] == "processed_zero_units"
    assert dispositions["site:example.test"] == "required_ledger_projection_gap"
    assert dispositions["legacy/transcript.md"] == "historical_relative_source_without_processed_claim"


def test_all_zero_gates_pass():
    report = build_projection_parity_report(
        [{"id": "same", "source_path": "/tmp/source"}],
        [{"id": "same", "source_path": "/tmp/source"}],
        {},
    )
    assert report["gates"] == {
        "processed_nonzero_paths_without_active_units_count": 0,
        "processed_nonzero_expected_units_without_active_units_count": 0,
        "required_ledger_ids_missing_count": 0,
        "unclassified_export_only_paths_count": 0,
        "pass": True,
    }
