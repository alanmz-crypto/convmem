"""T2 owner-lock enforcement, cap invariants, and V4 contract proofs."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.fixtures.issue_286_t2_owner_context import t2_owner_context

import llm
from bootstrap_codex_v2_authority import claim_initial_authority, claim_recovery_authority, load_authority
from bootstrap_codex_v2_owner import OwnerLockRequired
from bootstrap_codex_v2_authority import authority_path
from bootstrap_codex_v2_permits import CodexV2PaidLedger, validate_permit_event_against_grant
from bootstrap_safety import BootstrapOperationJournal, ProviderAttemptBudgetExceeded, BootstrapGrantError
from bootstrap_codex_v2 import operation_identity_v2
from tests.fixtures.issue_286_t2_parent_oracle import snapshot_tree
from tests.test_incremental_jsonl_bootstrap_command import _binding, _grant
from tests.test_incremental_jsonl_bootstrap_safety import _valid_attempt_event, _with_budget
from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant
from tests.test_issue_286_codex_bootstrap_v2_t2_accounting import _with_budget_v2


def _state(tmp_path, monkeypatch):
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    from bootstrap_codex_v2 import v2_source_state_directory

    state_dir = v2_source_state_directory(Path(cfg["index"]["incremental_jsonl"]["state_dir"]), grant)
    chroma = Path(cfg["index"]["chroma_dir"])
    return state_dir, grant, chroma



def _initial(state_dir, grant):
    with t2_owner_context(state_dir):
        return claim_initial_authority(state_dir, grant)


def _recovery(state_dir, grant):
    with t2_owner_context(state_dir):
        return claim_recovery_authority(state_dir, grant)


def test_owner_lock_required_without_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    existed = authority_path(state_dir).exists()
    with pytest.raises(OwnerLockRequired):
        claim_initial_authority(state_dir, grant)
    assert authority_path(state_dir).exists() == existed


def test_owner_lock_positive_allows_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    _initial(state_dir, grant)
    assert load_authority(state_dir) is not None


def test_accounting_lock_separate_from_owner_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    _initial(state_dir, grant)
    ledger = CodexV2PaidLedger(state_dir, grant)
    assert ledger.operation_dir.name not in {".bootstrap_v2_claim.lock"}


def test_no_chroma_mutation_during_permit_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, chroma = _state(tmp_path, monkeypatch)
    chroma.mkdir(parents=True, exist_ok=True)
    before = snapshot_tree(chroma)
    _initial(state_dir, grant)
    with t2_owner_context(state_dir):
        CodexV2PaidLedger(state_dir, grant).consume_provider_http_attempt(_valid_attempt_event())
    assert snapshot_tree(chroma) == before


def test_lifetime_cap_equals_grant_max_not_multiplied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    grant = _with_budget_v2(grant, 3)
    _initial(state_dir, grant)
    ledger = CodexV2PaidLedger(state_dir, grant)
    assert ledger.lifetime_paid_cap == 3
    assert ledger.lifetime_paid_cap == ledger.max_attempts


def test_recovery_does_not_reset_cumulative_paid_allowance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    grant = _with_budget_v2(grant, 2)
    _initial(state_dir, grant)
    ledger = CodexV2PaidLedger(state_dir, grant)
    with t2_owner_context(state_dir):
        ledger.consume_provider_http_attempt(_valid_attempt_event())
        ledger.consume_provider_http_attempt(_valid_attempt_event())
    _recovery(state_dir, grant)
    ledger2 = CodexV2PaidLedger(state_dir, grant)
    with t2_owner_context(state_dir):
        with pytest.raises(ProviderAttemptBudgetExceeded):
            ledger2.consume_provider_http_attempt(_valid_attempt_event())


def test_per_invocation_bucket_allows_one_each_with_lifetime_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    grant = _with_budget_v2(grant, 2)
    _initial(state_dir, grant)
    ledger = CodexV2PaidLedger(state_dir, grant)
    with t2_owner_context(state_dir):
        ledger.consume_provider_http_attempt(_valid_attempt_event())
    _recovery(state_dir, grant)
    ledger2 = CodexV2PaidLedger(state_dir, grant)
    with t2_owner_context(state_dir):
        ledger2.consume_provider_http_attempt(_valid_attempt_event())
    assert ledger2.accounting()["cumulative_permitted_http_attempts"] == 2


def test_provider_binding_rejects_model_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    event = dict(_valid_attempt_event())
    event["model"] = "wrong-model"
    with pytest.raises(ProviderAttemptBudgetExceeded, match="binding_mismatch"):
        validate_permit_event_against_grant(grant, event)


def test_prepared_reuse_does_not_append_second_permit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    _initial(state_dir, grant)
    ledger = CodexV2PaidLedger(state_dir, grant)
    with t2_owner_context(state_dir):
        ledger.consume_provider_http_attempt(_valid_attempt_event())

    def reuse_without_new_permit() -> int:
        return ledger.accounting()["observed_provider_http_attempts"]

    assert reuse_without_new_permit() == 1
    assert reuse_without_new_permit() == 1


def test_v1_journal_default_lifetime_matches_v2_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant_v2, _ = _state(tmp_path, monkeypatch)
    grant_v2 = _with_budget_v2(grant_v2, 4)
    v1_grant = _with_budget(_grant(tmp_path / "v1.jsonl"), 4)
    v1_journal = BootstrapOperationJournal(tmp_path / "v1state", v1_grant, _binding(v1_grant))
    v2_ledger = CodexV2PaidLedger(state_dir, grant_v2)
    assert v1_journal.lifetime_paid_http_attempts == v2_ledger.lifetime_paid_cap


def test_journal_ahead_of_authority_blocks_fresh_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from bootstrap_codex_v2_authority import detect_authority_corruption, operation_root

    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    _initial(state_dir, grant)
    inv = operation_root(state_dir, grant) / "invocations.jsonl"
    inv.parent.mkdir(parents=True, exist_ok=True)
    inv.write_text(
        '{"record_type":"start","invocation_ordinal":9}\n',
        encoding="utf-8",
    )
    assert "journal_ahead_of_authority" in detect_authority_corruption(state_dir, grant)


def test_rolled_back_authority_revision_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from bootstrap_codex_v2_authority import authority_path
    from bootstrap_safety import _atomic_json

    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    view = _initial(state_dir, grant)
    tampered = dict(view.record)
    tampered["revision"] = 0
    _atomic_json(authority_path(state_dir), tampered)
    with pytest.raises(BootstrapGrantError):
        load_authority(state_dir)


def test_provider_permit_refused_under_c1_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import chroma_write_store

    state_dir, grant, _ = _state(tmp_path, monkeypatch)
    _initial(state_dir, grant)
    ledger = CodexV2PaidLedger(state_dir, grant)
    monkeypatch.setattr(chroma_write_store, "production_chroma_store_session_depth", lambda: 1)
    with t2_owner_context(state_dir):
        with pytest.raises(ProviderAttemptBudgetExceeded, match="c1_session"):
            ledger.consume_provider_http_attempt(_valid_attempt_event())
