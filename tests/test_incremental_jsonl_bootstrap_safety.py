"""Hermetic bootstrap budget, recovery, dedupe, and export safety evidence."""

# Tests intentionally exercise private transport and recovery seams.
# pylint: disable=protected-access

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import llm
from bootstrap_safety import (
    BootstrapGrantError,
    BootstrapOperationJournal,
    operation_identity,
)
from incremental_jsonl import IncrementalJsonlCoordinator
from ingest_dedupe import IngestDedupeResult, persist_ingest_dedupe
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    isolated_env,
    write_source,
)
from tests.test_incremental_jsonl_bootstrap_command import _binding, _grant


def _with_budget(grant: dict, budget: int) -> dict:
    body = dict(grant)
    body["max_provider_http_attempts"] = budget
    body.pop("operation_id")
    return {"operation_id": operation_identity(body), **body}


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def _deepseek_post_response() -> _Response:
    return _Response(
        {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
    )


def _ollama_embed_post_response() -> _Response:
    return _Response(
        {
            "embedding": [0.1, 0.2, 0.3],
            "prompt_eval_count": 3,
            "eval_count": 2,
        }
    )


def _valid_attempt_event(provider: str = "deepseek") -> dict[str, object]:
    if provider == "deepseek":
        return {
            "provider": "deepseek",
            "operation": "generate",
            "model": "deepseek-v4-test",
            "base_url": "https://provider.invalid",
        }
    return {
        "provider": "ollama",
        "operation": "embed",
        "model": "model",
        "base_url": "http://fake.invalid",
    }


def test_paid_transport_disables_automatic_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict] = []

    def fake_post(_url, **kwargs):
        seen.append(kwargs)
        return _Response(
            {"choices": [{"message": {"content": "ok"}}], "usage": {}}
        )

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)
    assert (
        llm._deepseek_generate(
            "prompt",
            "deepseek-v4-test",
            "https://provider.invalid",
            max_attempts=1,
        )
        == "ok"
    )
    assert len(seen) == 1
    assert seen[0]["allow_redirects"] is False


def test_deepseek_paid_cap_blocks_transport_and_survives_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant = _with_budget(_grant(tmp_path / "source.jsonl"), 2)
    state = tmp_path / "state"
    journal = BootstrapOperationJournal(state, grant, _binding(grant))
    assert journal.begin_invocation(recoverable_transaction=False).authorized
    transports: list[str] = []

    def fake_post(url, **_kwargs):
        transports.append(url)
        return _deepseek_post_response()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)
    with llm.provider_http_accounting(
        journal.consume_provider_http_attempt,
        journal.report_provider_usage,
    ):
        assert (
            llm._deepseek_generate(
                "one",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
            == "ok"
        )
        assert (
            llm._deepseek_generate(
                "two",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
            == "ok"
        )
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            llm._deepseek_generate(
                "three",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
    assert len(transports) == 2
    accounting = journal.accounting()
    assert accounting["cumulative_paid_provider_http_attempts"] == 2
    assert accounting["cumulative_observed_provider_http_attempts"] == 2
    journal.finish({"outcome": "failed", "failure_code": "interrupted"})

    restarted = BootstrapOperationJournal(state, grant, _binding(grant))
    recovery = restarted.begin_invocation(recoverable_transaction=True)
    assert recovery.authorized and recovery.recovery
    with llm.provider_http_accounting(
        restarted.consume_provider_http_attempt,
        restarted.report_provider_usage,
    ):
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            llm._deepseek_generate(
                "recovery",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
    assert len(transports) == 2
    assert restarted.accounting()["cumulative_paid_provider_http_attempts"] == 2


def test_ollama_observed_cap_exempt_beyond_paid_ceiling_and_survives_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant = _with_budget(_grant(tmp_path / "source.jsonl"), 1)
    state = tmp_path / "state"
    journal = BootstrapOperationJournal(state, grant, _binding(grant))
    assert journal.begin_invocation(recoverable_transaction=False).authorized
    transports: list[str] = []

    def fake_post(url, **_kwargs):
        transports.append(url)
        if "/v1/chat/completions" in url:
            return _deepseek_post_response()
        return _ollama_embed_post_response()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)
    with llm.provider_http_accounting(
        journal.consume_provider_http_attempt,
        journal.report_provider_usage,
    ):
        assert (
            llm._deepseek_generate(
                "paid",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
            == "ok"
        )
        for label in ("embed-one", "embed-two", "embed-three"):
            assert llm.ollama_embed(label, "model", "http://fake.invalid") == [
                0.1,
                0.2,
                0.3,
            ]
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            llm._deepseek_generate(
                "paid-blocked",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
    assert len(transports) == 4
    accounting = journal.accounting()
    assert accounting["paid_provider_http_attempts"] == 1
    assert accounting["observed_provider_http_attempts"] == 4
    assert accounting["cumulative_paid_provider_http_attempts"] == 1
    assert accounting["cumulative_observed_provider_http_attempts"] == 4
    journal.finish({"outcome": "failed", "failure_code": "interrupted"})

    restarted = BootstrapOperationJournal(state, grant, _binding(grant))
    recovery = restarted.begin_invocation(recoverable_transaction=True)
    assert recovery.authorized and recovery.recovery
    with llm.provider_http_accounting(
        restarted.consume_provider_http_attempt,
        restarted.report_provider_usage,
    ):
        assert llm.ollama_embed("after-restart", "model", "http://fake.invalid") == [
            0.1,
            0.2,
            0.3,
        ]
    assert len(transports) == 5
    restarted_accounting = restarted.accounting()
    assert restarted_accounting["cumulative_paid_provider_http_attempts"] == 1
    assert restarted_accounting["cumulative_observed_provider_http_attempts"] == 5


def test_mixed_providers_receipt_counters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant = _with_budget(_grant(tmp_path / "source.jsonl"), 3)
    state = tmp_path / "state"
    journal = BootstrapOperationJournal(state, grant, _binding(grant))
    assert journal.begin_invocation(recoverable_transaction=False).authorized

    def fake_post(url, **_kwargs):
        if "/v1/chat/completions" in url:
            return _deepseek_post_response()
        return _ollama_embed_post_response()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)
    with llm.provider_http_accounting(
        journal.consume_provider_http_attempt,
        journal.report_provider_usage,
    ):
        assert (
            llm._deepseek_generate(
                "d1",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
            == "ok"
        )
        assert llm.ollama_embed("o1", "model", "http://fake.invalid") == [0.1, 0.2, 0.3]
        assert (
            llm._deepseek_generate(
                "d2",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
            == "ok"
        )
        assert llm.ollama_embed("o2", "model", "http://fake.invalid") == [0.1, 0.2, 0.3]
        assert (
            llm._deepseek_generate(
                "d3",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
            == "ok"
        )
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            llm._deepseek_generate(
                "d4",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )

    accounting = journal.accounting()
    assert accounting["paid_provider_http_attempts"] == 3
    assert accounting["observed_provider_http_attempts"] == 5
    assert accounting["cumulative_paid_provider_http_attempts"] == 3
    assert accounting["cumulative_observed_provider_http_attempts"] == 5
    assert accounting["permitted_http_attempts"] == 3


def test_legacy_malformed_ledger_rows_cannot_create_paid_exemptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant = _with_budget(_grant(tmp_path / "source.jsonl"), 4)
    state = tmp_path / "state"
    journal = BootstrapOperationJournal(state, grant, _binding(grant))
    assert journal.begin_invocation(recoverable_transaction=False).authorized
    base = {
        "operation_id": journal.operation_id,
        "grant_fingerprint": journal.fingerprint,
        "invocation_ordinal": 1,
        "recorded_at": "2026-10-10T00:00:00.000Z",
    }
    legacy_rows = [
        {
            **base,
            "record_type": "permit_consumed",
            "attempt_ordinal": 1,
            "provider": "ollama",
            "operation": "embed",
            "model": "m",
            "base_url": "http://fake.invalid",
        },
        {
            **base,
            "record_type": "permit_consumed",
            "attempt_ordinal": 2,
            "provider": "ollama",
            "operation": "embed",
            "model": "m",
            "base_url": "http://provider.invalid",
            "paid_cap_consumed": True,
        },
        {
            **base,
            "record_type": "permit_consumed",
            "attempt_ordinal": 3,
            "provider": "deepseek",
            "operation": "generate",
            "model": "deepseek-v4-test",
            "base_url": "https://provider.invalid",
            "paid_cap_consumed": False,
        },
        {
            **base,
            "record_type": "legacy_unknown",
            "attempt_ordinal": 4,
            "provider": "unknown",
            "operation": "embed",
            "model": "m",
            "base_url": "http://fake.invalid",
            "paid_cap_consumed": False,
        },
    ]
    journal.attempts_path.parent.mkdir(parents=True, exist_ok=True)
    with journal.attempts_path.open("w", encoding="utf-8") as handle:
        for row in legacy_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    transports: list[str] = []

    def fake_post(url, **_kwargs):
        transports.append(url)
        return _deepseek_post_response()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)
    with llm.provider_http_accounting(
        journal.consume_provider_http_attempt,
        journal.report_provider_usage,
    ):
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            llm._deepseek_generate(
                "blocked",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
    assert transports == []


def test_malformed_provider_attempt_events_fail_before_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant = _with_budget(_grant(tmp_path / "source.jsonl"), 4)
    journal = BootstrapOperationJournal(tmp_path / "state", grant, _binding(grant))
    assert journal.begin_invocation(recoverable_transaction=False).authorized
    transports: list[str] = []

    def fake_post(url, **_kwargs):
        transports.append(url)
        return _deepseek_post_response()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)
    with llm.provider_http_accounting(
        journal.consume_provider_http_attempt,
        journal.report_provider_usage,
    ):
        event = _valid_attempt_event()
        with pytest.raises(BootstrapGrantError, match="exactly"):
            journal.consume_provider_http_attempt({**event, "operation_id": "forged-operation"})
        with pytest.raises(BootstrapGrantError, match="missing provider"):
            journal.consume_provider_http_attempt({**event, "provider": ""})
        with pytest.raises(BootstrapGrantError, match="unsupported provider"):
            journal.consume_provider_http_attempt(
                {
                    "provider": "openai",
                    "operation": "generate",
                    "model": "m",
                    "base_url": "https://provider.invalid",
                }
            )
        assert (
            llm._deepseek_generate(
                "ok",
                "deepseek-v4-test",
                "https://provider.invalid",
                max_attempts=1,
            )
            == "ok"
        )
    assert len(transports) == 1
    attempts = json.loads(journal.attempts_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert attempts["operation_id"] == journal.operation_id
    assert attempts["operation_id"] != "forged-operation"


def test_invocation_journal_allows_exactly_one_recovery(tmp_path: Path) -> None:
    grant = _grant(tmp_path / "source.jsonl")
    journal = BootstrapOperationJournal(tmp_path / "state", grant, _binding(grant))
    first = journal.begin_invocation(recoverable_transaction=False)
    assert first.authorized and not first.recovery
    journal.finish({"outcome": "failed", "failure_code": "transform_failed"})

    second = BootstrapOperationJournal(tmp_path / "state", grant, _binding(grant))
    recovery = second.begin_invocation(recoverable_transaction=True)
    assert recovery.authorized and recovery.recovery
    second.finish({"outcome": "failed", "failure_code": "provider_fatal_refusal"})

    third = BootstrapOperationJournal(tmp_path / "state", grant, _binding(grant))
    exhausted = third.begin_invocation(recoverable_transaction=True)
    assert not exhausted.authorized
    assert exhausted.refusal_code == "recovery_exhausted"


def test_transaction_bound_dedupe_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    cfg = {"index": {"chroma_dir": str(tmp_path / "data" / "chroma")}, "refine": {}}
    event = {
        "suppressed_id": "new",
        "matched_id": "old",
        "content_hash": "a" * 64,
        "source_path": "/source",
        "transaction_id": "tx-1",
        "transaction_sequence": 1,
        "event_id": "e" * 64,
    }
    result = IngestDedupeResult(exact_suppressions=[event])
    first = persist_ingest_dedupe(cfg, result)
    path = tmp_path / "data" / "ingest_duplicate_suppressions.jsonl"
    before = path.read_bytes()
    second = persist_ingest_dedupe(cfg, result)
    assert first["exact_suppressed"] == 1
    assert second["exact_suppressed"] == 0
    assert path.read_bytes() == before


def test_export_rollback_streams_foreign_bytes_and_restores_exact_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    )
    export = Path(coordinator.cfg["index"]["units_export"])
    export.parent.mkdir(parents=True, exist_ok=True)
    foreign_a = json.dumps({"id": "foreign-a", "source_path": "/other"}).encode() + b"\n"
    owned_a = json.dumps({"id": "owned-a", "source_path": str(source)}).encode() + b"\n"
    foreign_b = b"not-json-but-preserved\n"
    owned_b = json.dumps({"id": "owned-b", "source_path": str(source)}).encode() + b"\n"
    original = foreign_a + owned_a + foreign_b + owned_b
    export.write_bytes(original)
    preimage = coordinator._snapshot_export_before_image()  # pylint: disable=protected-access
    assert len(preimage["source_lines"]) == 2
    assert b"foreign-a" not in json.dumps(preimage).encode()

    export.write_bytes(foreign_a + foreign_b + json.dumps({"id": "new", "source_path": str(source)}).encode() + b"\n")
    coordinator._restore_export(preimage)  # pylint: disable=protected-access
    assert export.read_bytes() == original

    for method in (
        coordinator._snapshot_export_before_image,  # pylint: disable=protected-access
        coordinator._restore_export,  # pylint: disable=protected-access
        coordinator._reconcile_export,  # pylint: disable=protected-access
    ):
        source_text = inspect.getsource(method)
        assert ".read_text(" not in source_text
        assert ".read_bytes(" not in source_text
