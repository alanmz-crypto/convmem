"""Issue #286 cohort budget ledger (C-KI4, C-KI6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from incremental_jsonl_cohort_budget import CohortBudgetLedger, CohortBudgetSettings
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
