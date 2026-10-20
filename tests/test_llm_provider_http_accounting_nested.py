"""Hermetic nested provider_http_accounting composition (issue #286)."""

# pylint: disable=protected-access,duplicate-code

from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

import llm
from bootstrap_safety import BootstrapOperationJournal
from tests.test_incremental_jsonl_bootstrap_command import _binding, _grant
from tests.test_incremental_jsonl_bootstrap_safety import _deepseek_post_response, _with_budget
from tests.test_issue_286_kiro_incremental_budget import (
    _coordinator,
    _frontier,
    _response,
    _run_frontier,
)


def _counter_cap(cap: int, *, label: str) -> tuple[list[str], llm.ProviderAttemptPermit]:
    seen: list[str] = []

    def permit(_event: dict[str, object]) -> None:
        if len(seen) >= cap:
            raise llm.ProviderAttemptBudgetExceeded(f"{label}_exhausted")
        seen.append(label)

    return seen, permit


def _reservation_cap(
    cap: int,
    *,
    label: str,
) -> tuple[list[tuple[str, bool | None]], llm.ProviderAttemptPermit, llm.ProviderAttemptFinished]:
    ledger: list[tuple[str, bool | None]] = []

    def permit(_event: dict[str, object]) -> None:
        reserved = sum(1 for item in ledger if item[1] is None)
        if reserved:
            raise RuntimeError(f"{label}_reservation_in_flight")
        if sum(1 for item in ledger if item[1] is True) >= cap:
            raise llm.ProviderAttemptBudgetExceeded(f"{label}_exhausted")
        ledger.append((label, None))

    def finished(_event: dict[str, object], success: bool) -> None:
        if not ledger or ledger[-1][1] is not None:
            return
        entry = ledger.pop()
        ledger.append((entry[0], success))

    return ledger, permit, finished


def _deepseek_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", lambda *_a, **_k: _deepseek_post_response())


def test_nested_outer_cap_tighter_blocks_before_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outer_seen, outer_permit = _counter_cap(1, label="outer")
    inner_seen, inner_permit = _counter_cap(5, label="inner")
    _deepseek_once(monkeypatch)
    with llm.provider_http_accounting(outer_permit, lambda *_a, **_k: None):
        with llm.provider_http_accounting(inner_permit, lambda *_a, **_k: None):
            assert (
                llm._deepseek_generate(
                    "one",
                    "deepseek-v4-test",
                    "https://provider.invalid",
                    max_attempts=1,
                )
                == "ok"
            )
            with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="outer_exhausted"):
                llm._deepseek_generate(
                    "two",
                    "deepseek-v4-test",
                    "https://provider.invalid",
                    max_attempts=1,
                )
    assert outer_seen == ["outer"]
    assert inner_seen == ["inner", "inner"]


def test_nested_inner_cap_tighter_blocks_before_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outer_seen, outer_permit = _counter_cap(5, label="outer")
    inner_seen, inner_permit = _counter_cap(1, label="inner")
    _deepseek_once(monkeypatch)
    with llm.provider_http_accounting(outer_permit, lambda *_a, **_k: None):
        with llm.provider_http_accounting(inner_permit, lambda *_a, **_k: None):
            assert (
                llm._deepseek_generate(
                    "one",
                    "deepseek-v4-test",
                    "https://provider.invalid",
                    max_attempts=1,
                )
                == "ok"
            )
            with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="inner_exhausted"):
                llm._deepseek_generate(
                    "two",
                    "deepseek-v4-test",
                    "https://provider.invalid",
                    max_attempts=1,
                )
    assert outer_seen == ["outer"]
    assert inner_seen == ["inner"]


def test_nested_outer_refusal_unwinds_inner_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inner_ledger, inner_permit, inner_finished = _reservation_cap(5, label="inner")

    def outer_refuse(_event: dict[str, object]) -> None:
        raise llm.ProviderAttemptBudgetExceeded("outer_refused")

    _deepseek_once(monkeypatch)
    with llm.provider_http_accounting(outer_refuse, lambda *_a, **_k: None):
        with llm.provider_http_accounting(
            inner_permit,
            lambda *_a, **_k: None,
            attempt_finished=inner_finished,
        ):
            with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="outer_refused"):
                llm._deepseek_generate(
                    "blocked",
                    "deepseek-v4-test",
                    "https://provider.invalid",
                    max_attempts=1,
                )
    assert inner_ledger == [("inner", False)]


def test_nested_inner_refusal_never_reaches_outer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outer_seen: list[str] = []

    def outer_permit(_event: dict[str, object]) -> None:
        outer_seen.append("outer")

    def inner_refuse(_event: dict[str, object]) -> None:
        raise llm.ProviderAttemptBudgetExceeded("inner_refused")

    _deepseek_once(monkeypatch)
    with llm.provider_http_accounting(outer_permit, lambda *_a, **_k: None):
        with llm.provider_http_accounting(inner_refuse, lambda *_a, **_k: None):
            with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="inner_refused"):
                llm._deepseek_generate(
                    "blocked",
                    "deepseek-v4-test",
                    "https://provider.invalid",
                    max_attempts=1,
                )
    assert not outer_seen


def test_nested_context_restores_outer_hooks_on_exception() -> None:
    outer_seen: list[str] = []

    def outer_permit(_event: dict[str, object]) -> None:
        outer_seen.append("outer")

    with llm.provider_http_accounting(outer_permit, lambda *_a, **_k: None):
        with pytest.raises(RuntimeError, match="boom"):
            with llm.provider_http_accounting(lambda *_e: None, lambda *_a, **_k: None):
                raise RuntimeError("boom")
        llm._permit_provider_http_attempt(
            provider="deepseek",
            operation="generate",
            model="m",
            base_url="https://provider.invalid",
        )
    assert outer_seen == ["outer"]


def test_nested_retry_settles_both_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inner_ledger, inner_permit, inner_finished = _reservation_cap(5, label="inner")
    outer_ledger, outer_permit, outer_finished = _reservation_cap(5, label="outer")
    attempts = {"count": 0}

    def flaky_post(*_args, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise requests.ConnectionError("transient")
        return _deepseek_post_response()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", flaky_post)
    with llm.provider_http_accounting(
        outer_permit,
        lambda *_a, **_k: None,
        attempt_finished=outer_finished,
    ):
        with llm.provider_http_accounting(
            inner_permit,
            lambda *_a, **_k: None,
            attempt_finished=inner_finished,
        ):
            assert (
                llm._deepseek_generate(
                    "retry",
                    "deepseek-v4-test",
                    "https://provider.invalid",
                    max_attempts=2,
                    retry_backoff=0,
                )
                == "ok"
            )
    assert inner_ledger == [("inner", False), ("inner", True)]
    assert outer_ledger == [("outer", False), ("outer", True)]


def test_bootstrap_and_kiro_coordinator_both_enforce_caps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = _coordinator(tmp_path, name="sess_nested_bootstrap", cap=1)
    grant = _with_budget(_grant(coordinator.source), 2)
    state = tmp_path / "bootstrap_state"
    journal = BootstrapOperationJournal(state, grant, _binding(grant))
    assert journal.begin_invocation(recoverable_transaction=False).authorized

    posts: list[str] = []

    def fake_post(url, **_kwargs):
        posts.append(url)
        return _response()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(coordinator, "_build_frontier", _frontier)

    with llm.provider_http_accounting(
        journal.consume_provider_http_attempt,
        journal.report_provider_usage,
    ):
        _run_frontier(coordinator, monkeypatch)
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="cohort"):
            _run_frontier(coordinator, monkeypatch)

    assert len(posts) == 1
    bootstrap_paid = journal.accounting()["cumulative_paid_provider_http_attempts"]
    cohort_payload = json.loads(
        coordinator._cohort_ledger.settings.ledger_path.read_text(encoding="utf-8")
    )
    assert bootstrap_paid == 1
    assert cohort_payload["consumed"] == 1
