"""Doctor checks for CG-2 logical projection and reconciliation freshness."""

from __future__ import annotations

from unittest.mock import patch

from doctor import _check_logical_projection, _check_source_reconciliation_freshness


def test_logical_projection_passes_for_legacy_global_snapshot():
    report = {
        "view": {"serving_units": 10, "physical_units": 12},
        "physical_inventory": {
            "duplicate_logical_count": 0,
            "counts_by_class": {"retained_inactive": 2},
        },
        "authority": {"owners": []},
        "authority_failures": [],
        "logical_projection_gate_pass": True,
    }
    with patch(
        "logical_accounting.build_corpus_view_stats", return_value=report
    ):
        check = _check_logical_projection({"index": {"chroma_dir": "/tmp/chroma"}})
    assert check.ok
    assert "serving_units=10" in check.detail


def test_logical_projection_fails_on_authority_failure():
    report = {
        "view": {"serving_units": 1, "physical_units": 1},
        "physical_inventory": {"duplicate_logical_count": 0, "counts_by_class": {}},
        "authority": {"owners": []},
        "authority_failures": ["owner: manifest missing"],
        "logical_projection_gate_pass": False,
    }
    with patch(
        "logical_accounting.build_corpus_view_stats", return_value=report
    ):
        check = _check_logical_projection({"index": {"chroma_dir": "/tmp/chroma"}})
    assert not check.ok
    assert "authority" in check.detail


def test_source_reconciliation_warn_when_stale():
    diag = {
        "pending_owner_count": 0,
        "dirty_scope_count": 0,
        "staleness_seconds": 999.0,
        "fresh": False,
    }
    with patch(
        "logical_accounting.build_reconciliation_diagnostics", return_value=diag
    ):
        check = _check_source_reconciliation_freshness(
            {"index": {"processed_log": "/tmp/processed.json"}}
        )
    assert check.ok
    assert check.effective_status() == "warn"
