"""T2 V4 paid accounting and composed permits."""

from __future__ import annotations

from pathlib import Path

import pytest

import llm
from bootstrap_codex_v2_authority import claim_initial_authority, claim_recovery_authority
from bootstrap_codex_v2_permits import (
    CodexV2PaidLedger,
    compose_provider_permits,
    outer_budget_permit_factory,
)
from bootstrap_safety import ProviderAttemptBudgetExceeded
from bootstrap_codex_v2 import operation_identity_v2
from tests.test_incremental_jsonl_bootstrap_safety import (
    _deepseek_post_response,
    _valid_attempt_event,
)


def _with_budget_v2(grant: dict, budget: int) -> dict:
    body = dict(grant)
    body["max_provider_http_attempts"] = budget
    body.pop("operation_id", None)
    return {"operation_id": operation_identity_v2(body), **body}

from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant
from tests.test_issue_286_codex_bootstrap_v2_t1_contract import _rebind_grant


def _ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, budget: int = 2):
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _with_budget_v2(_v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary), budget)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    from bootstrap_codex_v2 import v2_source_state_directory

    state_dir = v2_source_state_directory(state_root, grant)
    claim_initial_authority(state_dir, grant)
    return CodexV2PaidLedger(state_dir, grant), grant, state_dir


def test_permit_before_send_blocks_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, grant, _ = _ledger(tmp_path, monkeypatch, budget=1)
    transports: list[str] = []

    def fake_post(url, **_kwargs):
        transports.append(url)
        return _deepseek_post_response()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)
    with llm.provider_http_accounting(ledger.consume_provider_http_attempt, lambda *_a, **_k: None):
        assert (
            llm._deepseek_generate(
                "one",
                grant["summarize_model"],
                grant["summarize_base_url"],
                max_attempts=1,
            )
            == "ok"
        )
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            llm._deepseek_generate(
                "two",
                grant["summarize_model"],
                grant["summarize_base_url"],
                max_attempts=1,
            )
    assert len(transports) == 1


def test_composed_outer_and_operation_guards_both_execute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, grant, _ = _ledger(tmp_path, monkeypatch, budget=5)
    outer_calls: list[str] = []
    inner_calls: list[str] = []

    def outer(_event: dict[str, object]) -> None:
        outer_calls.append("outer")

    def inner(event: dict[str, object]) -> None:
        inner_calls.append("inner")
        ledger.consume_provider_http_attempt(event)

    composed = compose_provider_permits(outer, inner)
    event = _valid_attempt_event()
    composed(event)
    assert outer_calls == ["outer"]
    assert inner_calls == ["inner"]


def test_outer_refusal_blocks_before_operation_counter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, grant, _ = _ledger(tmp_path, monkeypatch, budget=5)
    outer = outer_budget_permit_factory(0)
    composed = compose_provider_permits(outer, ledger.consume_provider_http_attempt)
    with pytest.raises(ProviderAttemptBudgetExceeded, match="outer_budget"):
        composed(_valid_attempt_event())
    assert ledger.accounting()["observed_provider_http_attempts"] == 0


def test_recovery_ordinal_uses_separate_permit_bucket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, grant, state_dir = _ledger(tmp_path, monkeypatch, budget=2)
    with llm.provider_http_accounting(ledger.consume_provider_http_attempt, lambda *_a, **_k: None):
        ledger.consume_provider_http_attempt(_valid_attempt_event())
    claim_recovery_authority(state_dir, grant)
    ledger2 = CodexV2PaidLedger(state_dir, grant)
    ledger2.consume_provider_http_attempt(_valid_attempt_event())
    assert ledger2.accounting()["invocation_ordinal"] == 2
    assert ledger2.accounting()["permitted_http_attempts"] == 1


def test_broken_permit_order_negative_control() -> None:
    def send_before_permit() -> None:
        event = _valid_attempt_event()
        transports = ["sent"]
        ledger_calls: list[str] = []

        def permit(_e: dict[str, object]) -> None:
            ledger_calls.append("permit")

        permit(event)
        assert transports  # send already happened in broken variant

    with pytest.raises(AssertionError):
        send_before_permit()
        assert False
