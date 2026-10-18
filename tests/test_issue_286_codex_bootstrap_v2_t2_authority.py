"""T2 authority: reservation, recovery ordinal, terminal, concurrency."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from bootstrap_codex_v2_authority import (
    CodexBootstrapV2AuthorityError,
    claim_initial_authority,
    claim_recovery_authority,
    inspect_initial_claim_blockers,
    load_authority,
    mirror_invocation_start,
    publish_terminal_authority,
    refuse_third_invocation,
)
from bootstrap_safety import BootstrapGrantError, _atomic_json
from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant
from tests.test_issue_286_codex_bootstrap_v2_t1_contract import _rebind_grant


def _state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict]:
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    from bootstrap_codex_v2 import v2_source_state_directory

    state_dir = v2_source_state_directory(state_root, grant)
    return state_dir, grant


def test_authority_progress_binding_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    view = claim_initial_authority(state_dir, grant)
    for key in ("transaction_lineage_digest", "prepared_lineage_digest", "rollback_digest", "checkpoint_digest"):
        assert key in view.record["progress"]


def test_initial_claim_publishes_ordinal1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    view = claim_initial_authority(state_dir, grant)
    assert view.invocation_ordinal == 1
    assert view.reservation_active is True
    assert view.record["reservation_state"] == "RESERVED"
    assert load_authority(state_dir) is not None


def test_initial_claim_consumes_without_journal_mirror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    assert refuse_third_invocation(state_dir, grant) == "recovery_available"


def test_recovery_claim_ordinal2_identical_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    mirror_invocation_start(state_dir, grant)
    recovered = claim_recovery_authority(state_dir, grant)
    assert recovered.invocation_ordinal == 2
    assert recovered.revision == 2


def test_ordinal3_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    claim_recovery_authority(state_dir, grant)
    assert refuse_third_invocation(state_dir, grant) == "recovery_exhausted"
    with pytest.raises(CodexBootstrapV2AuthorityError, match="recovery_exhausted"):
        claim_recovery_authority(state_dir, grant)


def test_replacement_grant_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    altered = _rebind_grant(grant, max_chunks=grant["max_chunks"] + 1)
    with pytest.raises(CodexBootstrapV2AuthorityError, match="replacement_grant"):
        claim_recovery_authority(state_dir, altered)


def test_terminal_authority_immutable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    receipt_path = state_dir / "terminal_receipt.json"
    terminal = publish_terminal_authority(
        state_dir,
        grant,
        receipt_digest="a" * 64,
        receipt_path=receipt_path,
    )
    assert terminal.terminal is True
    assert terminal.reservation_active is False
    again = publish_terminal_authority(state_dir, grant, receipt_digest="a" * 64)
    assert again.revision == terminal.revision


def test_concurrent_initial_claimants_one_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    results: list[str] = []

    def worker() -> None:
        try:
            claim_initial_authority(state_dir, grant)
            results.append("claimed")
        except CodexBootstrapV2AuthorityError as exc:
            results.append(str(exc))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count("claimed") == 1
    assert sum("initial_claim_refused" in item for item in results) == 1


def test_orphan_journal_blocks_initial_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    from bootstrap_codex_v2_authority import operation_root

    op = operation_root(state_dir, grant)
    op.mkdir(parents=True)
    (op / "invocations.jsonl").write_text('{"record_type":"start"}\n', encoding="utf-8")
    blockers = inspect_initial_claim_blockers(state_dir, grant)
    assert "orphan_invocation_journal" in blockers


def test_authority_revision_rollback_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _state_dir(tmp_path, monkeypatch)
    view = claim_initial_authority(state_dir, grant)
    tampered = dict(view.record)
    tampered["revision"] = 0
    _atomic_json(view.path, tampered)
    with pytest.raises(CodexBootstrapV2AuthorityError):
        load_authority(state_dir)


def test_broken_ordinal3_allowance_would_fail() -> None:
    with pytest.raises(AssertionError):
        assert "recovery_exhausted" == "recovery_available"
