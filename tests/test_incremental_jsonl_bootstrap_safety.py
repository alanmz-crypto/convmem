"""Hermetic bootstrap budget, recovery, dedupe, and export safety evidence."""

# Tests intentionally exercise private transport and recovery seams.
# pylint: disable=protected-access

from __future__ import annotations

import inspect
import json
import stat
from pathlib import Path

import pytest

import llm
from bootstrap_safety import BootstrapOperationJournal, operation_identity
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


def test_http_attempt_cap_is_consumed_before_transport_and_survives_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    grant = _with_budget(_grant(tmp_path / "source.jsonl"), 2)
    state = tmp_path / "state"
    journal = BootstrapOperationJournal(state, grant, _binding(grant))
    assert journal.begin_invocation(recoverable_transaction=False).authorized
    transports: list[str] = []

    def fake_post(url, **_kwargs):
        transports.append(url)
        return _Response(
            {
                "response": "ok",
                "prompt_eval_count": 3,
                "eval_count": 2,
            }
        )

    monkeypatch.setattr(llm.requests, "post", fake_post)
    with llm.provider_http_accounting(
        journal.consume_provider_http_attempt,
        journal.report_provider_usage,
    ):
        assert llm._ollama_generate("one", "model", "http://fake.invalid") == "ok"
        assert llm._ollama_generate("two", "model", "http://fake.invalid") == "ok"
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            llm._ollama_generate("three", "model", "http://fake.invalid")
    assert len(transports) == 2
    assert journal.accounting()["cumulative_permitted_http_attempts"] == 2
    assert len(journal.accounting()["provider_usage"]) == 2
    journal.finish({"outcome": "failed", "failure_code": "interrupted"})

    restarted = BootstrapOperationJournal(state, grant, _binding(grant))
    recovery = restarted.begin_invocation(recoverable_transaction=True)
    assert recovery.authorized and recovery.recovery
    with llm.provider_http_accounting(
        restarted.consume_provider_http_attempt,
        restarted.report_provider_usage,
    ):
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            llm._ollama_generate("recovery", "model", "http://fake.invalid")
    assert len(transports) == 2
    assert restarted.accounting()["cumulative_permitted_http_attempts"] == 2


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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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
    lock = export.with_suffix(export.suffix + ".lock")
    assert stat.S_IMODE(lock.stat().st_mode) == 0o600

    for method in (
        coordinator._snapshot_export_before_image,  # pylint: disable=protected-access
        coordinator._restore_export,  # pylint: disable=protected-access
        coordinator._reconcile_export,  # pylint: disable=protected-access
    ):
        source_text = inspect.getsource(method)
        assert ".read_text(" not in source_text
        assert ".read_bytes(" not in source_text
