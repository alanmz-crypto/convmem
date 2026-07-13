"""Gate 5 — schema-deploy timestamp and hashless warn→block graduation."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from conflict_events import append_event, new_event
from hash_schema_gate import (
    GRADUATION_DAYS,
    deploy_path,
    enforce_hashless_on_approve,
    ensure_schema_deploy_recorded,
    graduation_state,
    hashless_targeted_unresolved,
    is_hashless_targeted,
    load_schema_deploy,
    migration_report_path,
)


def _cfg(td: str) -> dict:
    return {"index": {"chroma_dir": str(Path(td) / "chroma")}}


def test_is_hashless_targeted_only_for_updates_missing_hashes():
    assert not is_hashless_targeted({"target_ledger_id": None})
    assert not is_hashless_targeted(
        {
            "target_ledger_id": "dec_a",
            "base_content_hash": "aa",
            "proposed_content_hash": "bb",
        }
    )
    assert is_hashless_targeted({"target_ledger_id": "dec_a", "base_content_hash": None})
    assert is_hashless_targeted(
        {"target_ledger_id": "dec_a", "base_content_hash": "aa", "proposed_content_hash": ""}
    )


def test_schema_deploy_recorded_once_and_migration_report():
    with tempfile.TemporaryDirectory() as td:
        cfg = _cfg(td)
        first = ensure_schema_deploy_recorded(cfg)
        second = ensure_schema_deploy_recorded(cfg)
        assert first["deployed_at"] == second["deployed_at"]
        assert first["hash_schema_version"] == 1
        assert deploy_path(cfg).is_file()
        report = json.loads(migration_report_path(cfg).read_text(encoding="utf-8"))
        assert report["hashless_targeted_count"] == 0
        assert "warn until" in report["policy"]


def test_warn_then_block_after_14_days():
    with tempfile.TemporaryDirectory() as td:
        cfg = _cfg(td)
        ensure_schema_deploy_recorded(cfg)
        # Seed a hashless targeted unresolved PROPOSED event.
        append_event(
            cfg,
            new_event(
                "PROPOSED",
                "dec_prop_hashless",
                proposal={
                    "target_ledger_id": "dec_shared",
                    "base_content_hash": None,
                    "proposed_content_hash": None,
                    "hash_schema_version": None,
                },
            ),
        )
        assert len(hashless_targeted_unresolved(cfg)) == 1
        state = graduation_state(cfg)
        assert state["mode"] == "warn"
        warn = enforce_hashless_on_approve(
            cfg,
            {
                "id": "dec_prop_hashless",
                "target_ledger_id": "dec_shared",
                "base_content_hash": None,
                "proposed_content_hash": None,
            },
        )
        assert warn and "Gate 5 mode=warn" in warn

        # Age the deploy past graduation window.
        deploy = load_schema_deploy(cfg)
        old = (_now := datetime.now(timezone.utc) - timedelta(days=GRADUATION_DAYS + 1))
        deploy["deployed_at"] = old.strftime("%Y-%m-%dT%H:%M:%SZ")
        deploy_path(cfg).write_text(json.dumps(deploy) + "\n", encoding="utf-8")
        state = graduation_state(cfg)
        assert state["mode"] == "block"
        assert state["reason"] == "schema_deploy_age"
        with pytest.raises(ValueError, match="Gate 5 graduated"):
            enforce_hashless_on_approve(
                cfg,
                {
                    "id": "dec_prop_hashless",
                    "target_ledger_id": "dec_shared",
                    "base_content_hash": None,
                    "proposed_content_hash": None,
                },
            )


def test_zero_hashless_graduates_to_block_for_new_hashless():
    with tempfile.TemporaryDirectory() as td:
        cfg = _cfg(td)
        ensure_schema_deploy_recorded(cfg)
        state = graduation_state(cfg)
        assert state["mode"] == "block"
        assert state["reason"] == "zero_hashless_targeted"
        with pytest.raises(ValueError, match="zero_hashless_targeted"):
            enforce_hashless_on_approve(
                cfg,
                {
                    "id": "dec_prop_new_hashless",
                    "target_ledger_id": "dec_x",
                    "base_content_hash": "",
                    "proposed_content_hash": "",
                },
            )


def test_hashed_targeted_never_blocked():
    with tempfile.TemporaryDirectory() as td:
        cfg = _cfg(td)
        ensure_schema_deploy_recorded(cfg)
        assert (
            enforce_hashless_on_approve(
                cfg,
                {
                    "id": "dec_prop_ok",
                    "target_ledger_id": "dec_x",
                    "base_content_hash": "aa",
                    "proposed_content_hash": "bb",
                },
            )
            is None
        )
