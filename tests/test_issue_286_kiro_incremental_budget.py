"""Issue #286 cohort budget ledger (C-KI4, C-KI6)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from incremental_jsonl_cohort_budget import CohortBudgetError, CohortBudgetLedger, CohortBudgetSettings
from llm import ProviderAttemptBudgetExceeded


def test_cohort_budget_refuses_when_cap_exhausted(tmp_path: Path) -> None:
    ledger_path = tmp_path / "cohort-ledger.json"
    settings = CohortBudgetSettings(
        ledger_path=ledger_path,
        max_paid_http_attempts=1,
        operation_id="canary-op-1",
    )
    ledger = CohortBudgetLedger(settings)
    ledger.reserve_paid_http_attempt({"provider": "deepseek", "operation": "summarize"})
    ledger.finalize_reservation("00000001", success=True)
    with pytest.raises(ProviderAttemptBudgetExceeded):
        ledger.reserve_paid_http_attempt({"provider": "deepseek", "operation": "distill"})


def test_concurrent_reservations_do_not_double_pay(tmp_path: Path) -> None:
    ledger_path = tmp_path / "cohort-ledger.json"
    settings = CohortBudgetSettings(
        ledger_path=ledger_path,
        max_paid_http_attempts=2,
        operation_id="op-concurrent",
    )
    ledger = CohortBudgetLedger(settings)
    errors: list[Exception] = []

    def worker() -> None:
        try:
            ledger.consume_provider_http_attempt(
                {
                    "provider": "deepseek",
                    "operation": "summarize",
                    "model": "m",
                    "base_url": "https://api.deepseek.com",
                }
            )
            ledger.report_provider_usage({}, {})
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert int(payload["consumed"]) == 2


def test_unfinalized_reservation_blocks_next_permit(tmp_path: Path) -> None:
    ledger_path = tmp_path / "cohort-ledger.json"
    settings = CohortBudgetSettings(
        ledger_path=ledger_path,
        max_paid_http_attempts=3,
        operation_id="op-crash",
    )
    ledger = CohortBudgetLedger(settings)
    ledger.consume_provider_http_attempt(
        {
            "provider": "deepseek",
            "operation": "summarize",
            "model": "m",
            "base_url": "https://api.deepseek.com",
        }
    )
    with pytest.raises(CohortBudgetError, match="cohort_reservation_in_flight"):
        ledger.consume_provider_http_attempt(
            {
                "provider": "deepseek",
                "operation": "distill",
                "model": "m",
                "base_url": "https://api.deepseek.com",
            }
        )
    ledger.report_provider_usage({}, {})
    ledger.consume_provider_http_attempt(
        {
            "provider": "deepseek",
            "operation": "distill",
            "model": "m",
            "base_url": "https://api.deepseek.com",
        }
    )


def test_coordinator_wires_cohort_ledger_for_admitted_kiro(tmp_path: Path) -> None:
    from tests.incremental_jsonl_helpers import write_source
    import incremental_jsonl
    from incremental_jsonl_production import ProductionBoundary

    source = write_source(tmp_path, 2)
    data = tmp_path / "data"
    ledger_path = data / "cohort-ledger.json"
    cfg = {
        "index": {
            "chroma_dir": str(data / "chroma"),
            "processed_log": str(data / "processed.json"),
            "units_export": str(data / "knowledge_units.jsonl"),
            "incremental_jsonl": {
                "enabled": True,
                "state_dir": str(data / "incremental-jsonl"),
                "live_sources": [str(source.resolve())],
                "embed_dimension": 8,
                "kiro_session": {
                    "max_source_bytes": 268435456,
                    "max_transform_chunks_per_run": 20,
                    "allow_full_rebuild": False,
                    "cohort_ledger_path": str(ledger_path),
                    "cohort_max_paid_http_attempts": 5,
                    "cohort_operation_id": "canary-op-1",
                },
            },
        }
    }
    prod = ProductionBoundary(cfg, source, config_path=tmp_path / "config.toml")
    coord = incremental_jsonl.IncrementalJsonlCoordinator(prod, source, cfg=cfg, enabled=True)
    assert coord.kiro_admitted_live is True
    assert coord.cohort_budget_enabled is True
