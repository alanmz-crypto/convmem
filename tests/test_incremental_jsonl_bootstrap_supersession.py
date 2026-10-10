"""Hermetic regression tests for transform_failed bootstrap supersession."""

# pylint: disable=too-many-lines,too-many-positional-arguments,unused-argument,unnecessary-lambda

from __future__ import annotations

import json
import os
import runpy
import shutil
from pathlib import Path

import pytest

from bootstrap_safety import (
    BootstrapGrantError,
    BootstrapOperationJournal,
    canonical_json,
    grant_fingerprint,
    operation_identity,
    sha256_bytes,
    sha256_file,
)
from bootstrap_supersession import (
    snapshot_directory_inventory_digest,
    _ledger_file_digest,
    _lineage_path,
    _terminal_receipt_digest,
    activate_bootstrap_supersession,
    bootstrap_mutation_inventory,
    guard_ordinary_bootstrap_admission,
    bootstrap_source_chroma_inventory,
    classify_legacy_predecessor_attempts,
    generation_identity_digest,
    inspect_bootstrap_supersession,
    mutation_inventory_digest,
    parse_grant_document,
    successor_invocation_terminal_committed,
    supersession_accounting_from_authority,
    transaction_file_digest,
    validate_supersession_authority,
)
from incremental_jsonl import IncrementalJsonlError, source_state_id
import llm

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-incremental-jsonl.py"
_RECORDED_AT = "2026-10-10T12:00:00.000Z"
_GENERATION = {"device": 9, "inode": 42}


def _grant_body(source: Path, *, max_attempts: int = 6, runtime: str = "b" * 40) -> dict:
    return {
        "source": str(source),
        "prefix_sha256": "a" * 64,
        "complete_boundary": 42,
        "max_chunks": 2,
        "embed_dimension": 8,
        "backup_snapshot": "e" * 64,
        "runtime_revision": runtime,
        "config_sha256": "c" * 64,
        "transform_fingerprint": "d" * 64,
        "chunk_size": 2,
        "chunk_overlap": 0,
        "min_confidence": 0.6,
        "summarize_provider": "ollama",
        "summarize_model": "summary-model",
        "summarize_base_url": "http://provider.invalid",
        "distill_provider": "deepseek",
        "distill_model": "deepseek-v4-test",
        "distill_base_url": "https://provider.invalid",
        "embedding_provider": "ollama",
        "embedding_model": "embed-model",
        "embedding_base_url": "http://provider.invalid",
        "max_provider_http_attempts": max_attempts,
        "max_recovery_invocations": 1,
    }


def _grant(source: Path, **kwargs) -> dict:
    body = _grant_body(source, **kwargs)
    return {"operation_id": operation_identity(body), **body}


def _binding(grant: dict) -> dict:
    return {
        "runtime_revision": grant["runtime_revision"],
        "config_sha256": grant["config_sha256"],
        "chunk_size": grant["chunk_size"],
        "chunk_overlap": grant["chunk_overlap"],
        "min_confidence": grant["min_confidence"],
        "summarize": {
            "provider": grant["summarize_provider"],
            "model": grant["summarize_model"],
            "base_url": grant["summarize_base_url"],
            "fallback": "false",
        },
        "distill": {
            "provider": grant["distill_provider"],
            "model": grant["distill_model"],
            "base_url": grant["distill_base_url"],
            "fallback": "false",
        },
        "embedding": {
            "provider": grant["embedding_provider"],
            "model": grant["embedding_model"],
            "base_url": grant["embedding_base_url"],
            "fallback": "false",
        },
        "transform_fingerprint": grant["transform_fingerprint"],
    }


def _binding_fp(grant: dict) -> str:
    return sha256_bytes("convmem-bootstrap-binding-v1:" + canonical_json(_binding(grant)))


def _transaction(grant: dict, binding_fp: str, *, tx_id: str = "18d83bf3246c4c19b823e2cd950fe8c0") -> dict:
    return {
        "version": 1,
        "transaction_id": tx_id,
        "phase": "transform_failed",
        "bootstrap_existing": True,
        "grant_fingerprint": grant_fingerprint(grant),
        "operation_id": grant["operation_id"],
        "binding_fingerprint": binding_fp,
        "source_path": grant["source"],
        "source_identity": source_state_id(grant["source"]),
        "complete_boundary": grant["complete_boundary"],
        "prefix_sha256": grant["prefix_sha256"],
        "generation_identity": dict(_GENERATION),
        "failure_code": "provider_http_budget_exhausted",
    }


def _write_exact_transaction(state: Path, transaction: dict, *, raw: str | None = None) -> Path:
    path = state / "transaction.json"
    if raw is None:
        raw = json.dumps(transaction, sort_keys=True)
    path.write_text(raw, encoding="utf-8")
    return path


def _write_predecessor_ledger(
    state: Path, predecessor: dict, *, deepseek: int = 2, ollama: int = 6
) -> Path:
    root = state / "operations" / grant_fingerprint(predecessor)
    root.mkdir(parents=True, exist_ok=True)
    attempts = root / "provider_attempts.jsonl"
    rows = []
    ordinal = 0
    for _ in range(deepseek):
        ordinal += 1
        rows.append(
            {
                "record_type": "permit_consumed",
                "recorded_at": _RECORDED_AT,
                "operation_id": predecessor["operation_id"],
                "grant_fingerprint": grant_fingerprint(predecessor),
                "invocation_ordinal": 1,
                "attempt_ordinal": ordinal,
                "provider": "deepseek",
                "operation": "generate",
                "model": "deepseek-v4-test",
                "base_url": "https://provider.invalid",
            }
        )
    for _ in range(ollama):
        ordinal += 1
        rows.append(
            {
                "record_type": "permit_consumed",
                "recorded_at": _RECORDED_AT,
                "operation_id": predecessor["operation_id"],
                "grant_fingerprint": grant_fingerprint(predecessor),
                "invocation_ordinal": 1,
                "attempt_ordinal": ordinal,
                "provider": "ollama",
                "operation": "embed",
                "model": "embed-model",
                "base_url": "http://provider.invalid",
            }
        )
    attempts.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n")
    usage = root / "provider_usage.jsonl"
    usage_rows = []
    for _ in range(2):
        usage_rows.append(
            {
                "record_type": "provider_usage",
                "recorded_at": _RECORDED_AT,
                "operation_id": predecessor["operation_id"],
                "grant_fingerprint": grant_fingerprint(predecessor),
                "invocation_ordinal": 1,
                "provider": "deepseek",
                "operation": "generate",
                "model": "deepseek-v4-test",
                "usage": {"total_tokens": 1},
            }
        )
    usage.write_text("\n".join(json.dumps(row, sort_keys=True) for row in usage_rows) + "\n")
    invocations = root / "invocations.jsonl"
    binding_fp = _binding_fp(predecessor)
    terminal = {
        "record_type": "terminal",
        "recorded_at": _RECORDED_AT,
        "operation_id": predecessor["operation_id"],
        "grant_fingerprint": grant_fingerprint(predecessor),
        "invocation_ordinal": 1,
        "outcome": "failed",
        "transaction_phase": "transform_failed",
        "failure_code": "provider_http_budget_exhausted",
        "binding_fingerprint": binding_fp,
        "source": predecessor["source"],
        "prefix_sha256": predecessor["prefix_sha256"],
        "backup_snapshot": predecessor["backup_snapshot"],
    }
    invocations.write_text(
        json.dumps(
            {"record_type": "start", "invocation_ordinal": 1, "recorded_at": _RECORDED_AT},
            sort_keys=True,
        )
        + "\n"
        + json.dumps(terminal, sort_keys=True)
        + "\n"
    )
    manifest = {
        "version": 1,
        "operation_id": predecessor["operation_id"],
        "grant_fingerprint": grant_fingerprint(predecessor),
        "grant": predecessor,
        "binding": _binding(predecessor),
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )
    return attempts


def _write_snapshot(state: Path, transaction: dict, content: bytes = b"{}\n") -> Path:
    snap_dir = state / "snapshots" / transaction["transaction_id"]
    snap_dir.mkdir(parents=True, exist_ok=True)
    path = snap_dir / "messages.jsonl"
    path.write_bytes(content)
    session = snap_dir / "session.json"
    session.write_text("{}", encoding="utf-8")
    return snap_dir


def _cfg(tmp_path: Path) -> dict:
    return {
        "index": {
            "processed_log": str(tmp_path / "processed.json"),
            "units_export": str(tmp_path / "units.jsonl"),
            "chroma_dir": str(tmp_path / "chroma"),
        }
    }


def _inventory(state: Path, tmp_path: Path, cfg: dict, source: str) -> dict:
    return bootstrap_mutation_inventory(
        state,
        tmp_path,
        cfg,
        chroma_dir=Path(cfg["index"]["chroma_dir"]),
        source_path=source,
    )


def _authority(
    state: Path,
    predecessor: dict,
    successor: dict,
    transaction_path: Path,
    cfg: dict,
    tmp_path: Path,
) -> dict:
    inventory = _inventory(state, tmp_path, cfg, predecessor["source"])
    tx_id = json.loads(transaction_path.read_text(encoding="utf-8"))["transaction_id"]
    root = state / "operations" / grant_fingerprint(predecessor)
    _, terminal_digest = _terminal_receipt_digest(root / "invocations.jsonl")
    snap_dir = state / "snapshots" / tx_id
    return {
        "predecessor_operation_id": predecessor["operation_id"],
        "predecessor_grant_fingerprint": grant_fingerprint(predecessor),
        "predecessor_transaction_id": tx_id,
        "predecessor_transaction_sha256": transaction_file_digest(transaction_path),
        "predecessor_source_path": predecessor["source"],
        "predecessor_source_identity": source_state_id(predecessor["source"]),
        "predecessor_prefix_sha256": predecessor["prefix_sha256"],
        "predecessor_complete_boundary": predecessor["complete_boundary"],
        "predecessor_config_sha256": predecessor["config_sha256"],
        "predecessor_transform_fingerprint": predecessor["transform_fingerprint"],
        "predecessor_runtime_revision": predecessor["runtime_revision"],
        "predecessor_binding_fingerprint": _binding_fp(predecessor),
        "predecessor_generation_identity_digest": generation_identity_digest(_GENERATION),
        "lifetime_max_paid_http_attempts": 8,
        "predecessor_paid_http_attempts": 2,
        "predecessor_provider_attempts_sha256": sha256_file(root / "provider_attempts.jsonl"),
        "predecessor_provider_usage_sha256": _ledger_file_digest(root / "provider_usage.jsonl"),
        "predecessor_invocations_sha256": sha256_file(root / "invocations.jsonl"),
        "predecessor_terminal_receipt_sha256": terminal_digest,
        "predecessor_manifest_sha256": sha256_file(root / "manifest.json"),
        "predecessor_source_snapshot_sha256": snapshot_directory_inventory_digest(snap_dir),
        "predecessor_mutation_inventory_sha256": mutation_inventory_digest(inventory),
    }



def _accounting_from_authority(authority: dict) -> dict:
    return supersession_accounting_from_authority(authority)


def _setup_state(
    tmp_path: Path,
    predecessor: dict,
    transaction: dict,
    *,
    raw_tx: str | None = None,
    prepared_nonempty: bool = False,
) -> Path:
    source = Path(predecessor["source"])
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("{}\n", encoding="utf-8")
    os.stat(source)  # ensure generation identity stable for tests using _GENERATION
    state = tmp_path / "state" / source_state_id(str(source))
    state.mkdir(parents=True, exist_ok=True)
    _write_exact_transaction(state, transaction, raw=raw_tx)
    prepared = state / "prepared"
    if prepared_nonempty:
        prepared.mkdir()
        (prepared / "chunk-0.json").write_text("{}", encoding="utf-8")
    elif prepared.exists():
        prepared.rmdir()
    _write_predecessor_ledger(state, predecessor)
    _write_snapshot(state, transaction)
    return state


def _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path):
    chroma_dir = Path(cfg["index"]["chroma_dir"])
    inventory = _inventory(state, tmp_path, cfg, predecessor["source"])
    admission = inspect_bootstrap_supersession(
        source_state=state,
        grant=successor,
        authority=authority,
        mutation_inventory=inventory,
    )
    return activate_bootstrap_supersession(
        cfg=cfg,
        source_state=state,
        data_root=tmp_path,
        chroma_dir=chroma_dir,
        grant=successor,
        authority=authority,
        admission=admission,
    )


def _cfg_for_script_state(tmp_path: Path) -> dict:
    cfg = _cfg(tmp_path)
    cfg["index"]["incremental_jsonl"] = {
        "enabled": False,
        "state_dir": str(tmp_path / "incremental"),
        "allow_full_rebuild": False,
    }
    return cfg


def _relocate_state_for_script(tmp_path: Path, state: Path, source: Path) -> Path:
    state_root = tmp_path / "incremental" / source_state_id(str(source))
    state_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(state), str(state_root))
    return state_root


def _chroma_files(chroma_dir: Path) -> set[str]:
    if not chroma_dir.exists():
        return set()
    return {str(item.relative_to(chroma_dir)) for item in chroma_dir.rglob("*") if item.is_file()}


def _forbidden_provider_path(*_args, **_kwargs):
    raise RuntimeError("bootstrap reached provider or network path")


def _install_script_bootstrap_harness(
    monkeypatch: pytest.MonkeyPatch, cfg: dict, tmp_path: Path
) -> tuple:
    namespace = runpy.run_path(str(SCRIPT), run_name="bootstrap_test")
    bootstrap = namespace["bootstrap"]
    globals_ = bootstrap.__globals__
    monkeypatch.setitem(globals_, "load_config", lambda: cfg)
    monkeypatch.setitem(globals_, "CONFIG_PATH", tmp_path / "config.toml")
    (tmp_path / "config.toml").write_text("# test\n", encoding="utf-8")
    monkeypatch.setitem(globals_, "_require_watcher_disabled", lambda: None)
    monkeypatch.setitem(
        globals_,
        "ProductionBoundary",
        lambda *_a, **_k: type(
            "B",
            (),
            {"resolve_mutable": staticmethod(lambda p, *, label: Path(p))},
        )(),
    )
    monkeypatch.setitem(globals_, "_effective_binding", _forbidden_provider_path)
    monkeypatch.setitem(globals_, "detect_format", _forbidden_provider_path)
    monkeypatch.setitem(globals_, "parse_complete_prefix", _forbidden_provider_path)
    monkeypatch.setitem(globals_, "chunk_messages", _forbidden_provider_path)
    monkeypatch.setitem(globals_, "IncrementalJsonlCoordinator", _forbidden_provider_path)
    return bootstrap, globals_


def _assert_no_successor_bootstrap_mutation(
    state: Path, chroma_dir: Path, *, grant: dict, chroma_before: set[str]
) -> None:
    assert not (state / "operations" / grant_fingerprint(grant) / "manifest.json").is_file()
    assert _chroma_files(chroma_dir) == chroma_before


def test_parse_grant_document_rejects_unknown_wrapper_keys(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    grant = _grant(source)
    document = {**grant, "unexpected": True}
    with pytest.raises(BootstrapGrantError, match="exactly grant fields"):
        parse_grant_document(document)


def test_transaction_digest_uses_exact_file_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source)
    binding_fp = _binding_fp(predecessor)
    transaction = _transaction(predecessor, binding_fp)
    state = _setup_state(tmp_path, predecessor, transaction)
    tx_path = state / "transaction.json"
    assert transaction_file_digest(tx_path) == sha256_file(tx_path)
    unsorted = json.dumps(transaction)
    _write_exact_transaction(state, transaction, raw=unsorted)
    assert transaction_file_digest(tx_path) != sha256_bytes(
        "convmem-bootstrap-transaction-v1:" + canonical_json(transaction)
    )


def test_legacy_attempt_classification_counts_two_deepseek_six_ollama(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source)
    state = tmp_path / "state"
    attempts = _write_predecessor_ledger(state, predecessor)
    paid, digest = classify_legacy_predecessor_attempts(
        attempts,
        operation_id=predecessor["operation_id"],
        grant_fingerprint_value=grant_fingerprint(predecessor),
        manifest=json.loads(
            (state / "operations" / grant_fingerprint(predecessor) / "manifest.json").read_text()
        ),
    )
    assert paid == 2
    assert digest == sha256_file(attempts)


def test_supersession_refuses_nonempty_prepared_cache(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source)
    successor = _grant(source, runtime="9" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction, prepared_nonempty=True)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    with pytest.raises(BootstrapGrantError, match="prepared cache is not empty"):
        inspect_bootstrap_supersession(
            source_state=state,
            grant=successor,
            authority=authority,
            mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
        )


def test_admissible_supersession_archives_exact_bytes_and_preserves_evidence(
    tmp_path: Path,
) -> None:
    source = tmp_path / "session" / "messages.jsonl"
    predecessor = _grant(source, max_attempts=8, runtime="3" * 40)
    successor = _grant(source, max_attempts=6, runtime="b" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    raw_tx = json.dumps(transaction, sort_keys=True, indent=2) + "\n"
    state = _setup_state(tmp_path, predecessor, transaction, raw_tx=raw_tx)
    cfg = _cfg(tmp_path)
    tx_path = state / "transaction.json"
    authority = _authority(state, predecessor, successor, tx_path, cfg, tmp_path)
    validate_supersession_authority(authority, successor)
    original_bytes = tx_path.read_bytes()
    snapshot_before = (
        state / "snapshots" / transaction["transaction_id"] / "messages.jsonl"
    ).read_bytes()
    attempts_before = (
        state / "operations" / grant_fingerprint(predecessor) / "provider_attempts.jsonl"
    ).read_bytes()
    admission = _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    assert admission.predecessor_paid_http_attempts == 2
    assert not tx_path.exists()
    archive = (
        state
        / "superseded_bootstrap_transactions"
        / f"{transaction['transaction_id']}__{successor['operation_id']}"
    )
    assert (archive / "transaction.json").read_bytes() == original_bytes
    assert _lineage_path(state, transaction["transaction_id"]).is_file()
    assert (
        state / "snapshots" / transaction["transaction_id"] / "messages.jsonl"
    ).read_bytes() == snapshot_before
    assert (
        state / "operations" / grant_fingerprint(predecessor) / "provider_attempts.jsonl"
    ).read_bytes() == attempts_before


def test_staged_archive_resumes_lineage_publication(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    tx_path = state / "transaction.json"
    archive = (
        state
        / "superseded_bootstrap_transactions"
        / f"{transaction['transaction_id']}__{successor['operation_id']}"
    )
    archive.mkdir(parents=True)
    os.replace(tx_path, archive / "transaction.json")
    assert not _lineage_path(state, transaction["transaction_id"]).exists()
    admission = inspect_bootstrap_supersession(
        source_state=state,
        grant=successor,
        authority=authority,
        mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
    )
    assert admission.finish_lineage_only is True
    finished = activate_bootstrap_supersession(
        cfg=cfg,
        source_state=state,
        data_root=tmp_path,
        chroma_dir=Path(cfg["index"]["chroma_dir"]),
        grant=successor,
        authority=authority,
        admission=admission,
    )
    assert finished.recovery_mode is True
    assert _lineage_path(state, transaction["transaction_id"]).is_file()


def test_supersession_refuses_applying_phase(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source)
    successor = _grant(source, runtime="9" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    transaction["phase"] = "APPLYING"
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    with pytest.raises(BootstrapGrantError, match="phase APPLYING"):
        inspect_bootstrap_supersession(
            source_state=state,
            grant=successor,
            authority=authority,
            mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
        )


def test_supersession_refuses_checkpoint_or_rollback(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source)
    successor = _grant(source, runtime="9" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    (state / "checkpoint.json").write_text("{}", encoding="utf-8")
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    with pytest.raises(BootstrapGrantError, match="checkpoint exists"):
        inspect_bootstrap_supersession(
            source_state=state,
            grant=successor,
            authority=authority,
            mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
        )
    (state / "checkpoint.json").unlink()
    (state / "rollback.json").write_text("{}", encoding="utf-8")
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    with pytest.raises(BootstrapGrantError, match="rollback journal exists"):
        inspect_bootstrap_supersession(
            source_state=state,
            grant=successor,
            authority=authority,
            mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
        )


def test_mutation_inventory_tamper_refuses_before_activation(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source)
    successor = _grant(source, runtime="9" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    inventory = _inventory(state, tmp_path, cfg, predecessor["source"])
    admission = inspect_bootstrap_supersession(
        source_state=state,
        grant=successor,
        authority=authority,
        mutation_inventory=inventory,
    )
    (tmp_path / "processed.json").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(BootstrapGrantError, match="mutation inventory proof mismatch"):
        activate_bootstrap_supersession(
            cfg=cfg,
            source_state=state,
            data_root=tmp_path,
            chroma_dir=Path(cfg["index"]["chroma_dir"]),
            grant=successor,
            authority=authority,
            admission=admission,
        )
    assert (state / "transaction.json").is_file()
    assert not _lineage_path(state, transaction["transaction_id"]).exists()


def test_same_grant_recovery_reuses_lineage_without_re_admitting_predecessor(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    successor_tx = _transaction(successor, _binding_fp(successor), tx_id="aa" * 16)
    successor_tx["phase"] = "transform_failed"
    _write_exact_transaction(state, successor_tx)
    recovery = inspect_bootstrap_supersession(
        source_state=state,
        grant=successor,
        authority=authority,
        mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
    )
    assert recovery.recovery_mode is True
    assert recovery.predecessor_paid_http_attempts == 2


def test_second_different_successor_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    other = _grant(source, runtime="3" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    with pytest.raises(BootstrapGrantError, match="already superseded by another successor"):
        inspect_bootstrap_supersession(
            source_state=state,
            grant=other,
            authority=authority,
            mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
        )


def test_committed_successor_terminal_refuses_replay(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    journal = BootstrapOperationJournal(
        state,
        successor,
        _binding(successor),
        predecessor_paid_http_attempts=2,
        lifetime_paid_http_attempts=8,
        supersession_accounting=_accounting_from_authority(authority),
    )
    journal.begin_invocation(recoverable_transaction=False)
    journal.finish(
        {
            "outcome": "committed",
            "transaction_phase": "COMMITTED",
            "failure_code": None,
        }
    )
    assert successor_invocation_terminal_committed(state, successor)
    with pytest.raises(BootstrapGrantError, match="already committed"):
        inspect_bootstrap_supersession(
            source_state=state,
            grant=successor,
            authority=authority,
            mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
        )


def test_lineage_recovery_without_active_transaction_after_start(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    journal = BootstrapOperationJournal(
        state,
        successor,
        _binding(successor),
        predecessor_paid_http_attempts=2,
        lifetime_paid_http_attempts=8,
        supersession_accounting=_accounting_from_authority(authority),
    )
    journal.begin_invocation(recoverable_transaction=False)
    recovery = inspect_bootstrap_supersession(
        source_state=state,
        grant=successor,
        authority=authority,
        mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
    )
    assert recovery.successor_recovery_without_transaction is True
    second = journal.begin_invocation(recoverable_transaction=True)
    assert second.authorized is True


def test_manifest_accounting_mismatch_refuses_journal(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    successor = _grant(source, max_attempts=6)
    state = tmp_path / "state"
    authority_fp = "a" * 64
    accounting = {
        "predecessor_paid_http_attempts": 3,
        "lifetime_max_paid_http_attempts": 8,
        "predecessor_operation_id": "0" * 64,
        "predecessor_grant_fingerprint": "f" * 64,
        "authority_fingerprint": authority_fp,
    }
    with pytest.raises(BootstrapGrantError, match="predecessor paid mismatch"):
        BootstrapOperationJournal(
            state,
            successor,
            _binding(successor),
            predecessor_paid_http_attempts=2,
            lifetime_paid_http_attempts=8,
            supersession_accounting=accounting,
        )
    matching = {
        **accounting,
        "predecessor_paid_http_attempts": 2,
    }
    journal = BootstrapOperationJournal(
        state,
        successor,
        _binding(successor),
        predecessor_paid_http_attempts=2,
        lifetime_paid_http_attempts=8,
        supersession_accounting=matching,
    )
    BootstrapOperationJournal(
        state,
        successor,
        _binding(successor),
        predecessor_paid_http_attempts=2,
        lifetime_paid_http_attempts=8,
        supersession_accounting=matching,
    )
    assert journal.manifest_path.is_file()


def test_successor_journal_enforces_lifetime_paid_cap_with_carryforward(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    successor = _grant(source, max_attempts=6)
    state = tmp_path / "state"
    accounting = {
        "predecessor_paid_http_attempts": 2,
        "lifetime_max_paid_http_attempts": 8,
        "predecessor_operation_id": "1" * 64,
        "predecessor_grant_fingerprint": "f" * 64,
        "authority_fingerprint": "a" * 64,
    }
    journal = BootstrapOperationJournal(
        state,
        successor,
        _binding(successor),
        predecessor_paid_http_attempts=2,
        lifetime_paid_http_attempts=8,
        supersession_accounting=accounting,
    )
    assert journal.begin_invocation(recoverable_transaction=False).authorized
    event = {
        "provider": "deepseek",
        "operation": "generate",
        "model": "deepseek-v4-test",
        "base_url": "https://provider.invalid",
    }
    with llm.provider_http_accounting(
        journal.consume_provider_http_attempt,
        journal.report_provider_usage,
    ):
        for _ in range(6):
            journal.consume_provider_http_attempt(event)
        with pytest.raises(llm.ProviderAttemptBudgetExceeded, match="exhausted"):
            journal.consume_provider_http_attempt(event)
    assert journal.lifetime_paid_http_attempts == 8
    assert journal.max_attempts == 6
    accounting = journal.accounting()
    assert accounting["predecessor_paid_provider_http_attempts"] == 2
    assert accounting["cumulative_lifetime_paid_provider_http_attempts"] == 8


def test_unbound_carried_accounting_refuses_journal(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    successor = _grant(source, max_attempts=6)
    state = tmp_path / "state"
    with pytest.raises(
        BootstrapGrantError,
        match="supersession_accounting required for carried paid HTTP accounting",
    ):
        BootstrapOperationJournal(
            state,
            successor,
            _binding(successor),
            predecessor_paid_http_attempts=2,
            lifetime_paid_http_attempts=8,
        )
    ordinary = _grant(source, max_attempts=6, runtime="9" * 40)
    journal = BootstrapOperationJournal(state, ordinary, _binding(ordinary))
    assert journal.manifest_path.is_file()
    assert not journal.manifest_path.read_text(encoding="utf-8").count(
        "supersession_accounting"
    )



def test_legacy_malformed_attempt_row_refuses(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source)
    attempts = _write_predecessor_ledger(state := tmp_path / "state", predecessor, deepseek=3, ollama=5)
    with pytest.raises(BootstrapGrantError, match="exactly two"):
        classify_legacy_predecessor_attempts(
            attempts,
            operation_id=predecessor["operation_id"],
            grant_fingerprint_value=grant_fingerprint(predecessor),
            manifest=json.loads(
                (state / "operations" / grant_fingerprint(predecessor) / "manifest.json").read_text()
            ),
        )




def test_lineage_recovery_allows_successor_nonempty_prepared_cache(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    successor_tx = _transaction(successor, _binding_fp(successor), tx_id="aa" * 16)
    successor_tx["phase"] = "transform_failed"
    _write_exact_transaction(state, successor_tx)
    prepared = state / "prepared"
    prepared.mkdir(exist_ok=True)
    (prepared / "chunk-0.json").write_text("{}", encoding="utf-8")
    recovery = inspect_bootstrap_supersession(
        source_state=state,
        grant=successor,
        authority=authority,
        mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
    )
    assert recovery.recovery_mode is True


def test_corrupt_lineage_record_refuses_recovery(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    lineage_path = _lineage_path(state, transaction["transaction_id"])
    lineage_path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(BootstrapGrantError, match="invalid JSON"):
        inspect_bootstrap_supersession(
            source_state=state,
            grant=successor,
            authority=authority,
            mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
        )

def test_bootstrap_source_chroma_inventory_is_read_only_empty(tmp_path: Path) -> None:
    source = str(tmp_path / "source.jsonl")
    inventory = bootstrap_source_chroma_inventory(tmp_path / "chroma", source)
    assert inventory["conversation_summaries"]["count"] == 0
    assert inventory["knowledge_units"]["count"] == 0


def test_script_preflight_binding_failure_leaves_predecessor_unarchived(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    namespace = runpy.run_path(str(SCRIPT), run_name="bootstrap_test")
    bootstrap = namespace["bootstrap"]
    globals_ = bootstrap.__globals__
    source = tmp_path / "source.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    cfg = _cfg(tmp_path)
    cfg["index"]["incremental_jsonl"] = {
        "enabled": False,
        "state_dir": str(tmp_path / "incremental"),
        "allow_full_rebuild": False,
    }
    state_root = tmp_path / "incremental" / source_state_id(str(source))
    state = _setup_state(tmp_path, predecessor, transaction)
    shutil.move(str(state), str(state_root))
    state = state_root
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    monkeypatch.setitem(globals_, "load_config", lambda: cfg)
    monkeypatch.setitem(globals_, "CONFIG_PATH", tmp_path / "config.toml")
    (tmp_path / "config.toml").write_text("# test\n", encoding="utf-8")
    monkeypatch.setitem(globals_, "_require_watcher_disabled", lambda: None)
    monkeypatch.setitem(globals_, "_effective_binding", lambda *_a, **_k: {"mismatch": True})
    monkeypatch.setitem(
        globals_,
        "ProductionBoundary",
        lambda *_a, **_k: type("B", (), {"resolve_mutable": staticmethod(lambda p, *, label: Path(p))})(),
    )
    with pytest.raises(BootstrapGrantError, match="binding mismatch"):
        bootstrap(successor, supersession_authority=authority)
    assert (state / "transaction.json").is_file()
    assert not _lineage_path(state, transaction["transaction_id"]).exists()


def test_script_preflight_dimension_failure_leaves_predecessor_unarchived(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    namespace = runpy.run_path(str(SCRIPT), run_name="bootstrap_test")
    bootstrap = namespace["bootstrap"]
    globals_ = bootstrap.__globals__
    source = tmp_path / "source.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    cfg = _cfg(tmp_path)
    cfg["index"]["incremental_jsonl"] = {
        "enabled": False,
        "state_dir": str(tmp_path / "incremental"),
        "allow_full_rebuild": False,
    }
    state = _setup_state(tmp_path, predecessor, transaction)
    state_root = tmp_path / "incremental" / source_state_id(str(source))
    state_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(state), str(state_root))
    state = state_root
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)

    class FakeCoordinator:
        def __init__(self, *_args, **_kwargs):
            self.cfg = cfg

        def require_existing_embedding_dimension(self, _expected):
            raise globals_["IncrementalJsonlError"]("embedding_dimension_mismatch", "bad")

    monkeypatch.setitem(globals_, "load_config", lambda: cfg)
    monkeypatch.setitem(globals_, "CONFIG_PATH", tmp_path / "config.toml")
    (tmp_path / "config.toml").write_text("# test\n", encoding="utf-8")
    monkeypatch.setitem(globals_, "_require_watcher_disabled", lambda: None)
    monkeypatch.setitem(globals_, "_effective_binding", lambda *_a, **_k: _binding(successor))
    monkeypatch.setitem(globals_, "IncrementalJsonlCoordinator", FakeCoordinator)
    monkeypatch.setitem(
        globals_,
        "ProductionBoundary",
        lambda *_a, **_k: type("B", (), {"resolve_mutable": staticmethod(lambda p, *, label: Path(p))})(),
    )
    monkeypatch.setitem(globals_, "detect_format", lambda *_a: "jsonl_kiro_session")
    monkeypatch.setitem(
        globals_,
        "parse_complete_prefix",
        lambda *_a: type(
            "V",
            (),
            {
                "prefix_sha256": successor["prefix_sha256"],
                "complete_boundary": successor["complete_boundary"],
                "messages": [],
            },
        )(),
    )
    monkeypatch.setitem(globals_, "chunk_messages", lambda *_a, **_k: [1, 2])
    with pytest.raises(IncrementalJsonlError):
        bootstrap(successor, supersession_authority=authority)
    assert (state / "transaction.json").is_file()
    assert not _lineage_path(state, transaction["transaction_id"]).exists()

def test_crash_window_ordinary_omission_refuses_same_successor_after_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg_for_script_state(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    state = _relocate_state_for_script(tmp_path, state, source)
    chroma_dir = Path(cfg["index"]["chroma_dir"])
    chroma_before = _chroma_files(chroma_dir)
    bootstrap, _globals = _install_script_bootstrap_harness(monkeypatch, cfg, tmp_path)
    with pytest.raises(
        BootstrapGrantError,
        match="durable bootstrap supersession evidence requires supersession authority",
    ):
        bootstrap(successor)
    _assert_no_successor_bootstrap_mutation(
        state, chroma_dir, grant=successor, chroma_before=chroma_before
    )


def test_crash_window_ordinary_omission_refuses_different_grant_after_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    ordinary = _grant(source, runtime="3" * 40)
    assert grant_fingerprint(ordinary) != grant_fingerprint(successor)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg_for_script_state(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    state = _relocate_state_for_script(tmp_path, state, source)
    chroma_dir = Path(cfg["index"]["chroma_dir"])
    chroma_before = _chroma_files(chroma_dir)
    bootstrap, _globals = _install_script_bootstrap_harness(monkeypatch, cfg, tmp_path)
    with pytest.raises(
        BootstrapGrantError,
        match="durable bootstrap supersession evidence requires supersession authority",
    ):
        bootstrap(ordinary)
    _assert_no_successor_bootstrap_mutation(
        state, chroma_dir, grant=ordinary, chroma_before=chroma_before
    )
    _assert_no_successor_bootstrap_mutation(
        state, chroma_dir, grant=successor, chroma_before=chroma_before
    )


def test_crash_window_authority_bearing_successor_resumes_lifetime_accounting(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40, max_attempts=6)
    successor = _grant(source, runtime="2" * 40, max_attempts=6)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    _inspect_activate(state, predecessor, successor, authority, cfg, tmp_path)
    assert not (
        state / "operations" / grant_fingerprint(successor) / "manifest.json"
    ).is_file()
    admission = inspect_bootstrap_supersession(
        source_state=state,
        grant=successor,
        authority=authority,
        mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
    )
    assert admission.predecessor_paid_http_attempts == 2
    assert admission.lifetime_max_paid_http_attempts == 8
    journal = BootstrapOperationJournal(
        state,
        successor,
        _binding(successor),
        predecessor_paid_http_attempts=admission.predecessor_paid_http_attempts,
        lifetime_paid_http_attempts=admission.lifetime_max_paid_http_attempts,
        supersession_accounting=_accounting_from_authority(authority),
    )
    assert journal.lifetime_paid_http_attempts == 8
    assert journal.max_attempts == 6
    accounting = journal.accounting()
    assert accounting["predecessor_paid_provider_http_attempts"] == 2


def test_crash_window_staged_archive_and_corrupt_lineage_fail_closed_without_authority(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jsonl"
    predecessor = _grant(source, runtime="1" * 40)
    successor = _grant(source, runtime="2" * 40)
    transaction = _transaction(predecessor, _binding_fp(predecessor))
    state = _setup_state(tmp_path, predecessor, transaction)
    cfg = _cfg(tmp_path)
    authority = _authority(state, predecessor, successor, state / "transaction.json", cfg, tmp_path)
    tx_path = state / "transaction.json"
    archive = (
        state
        / "superseded_bootstrap_transactions"
        / f"{transaction['transaction_id']}__{successor['operation_id']}"
    )
    archive.mkdir(parents=True)
    os.replace(tx_path, archive / "transaction.json")
    with pytest.raises(
        BootstrapGrantError,
        match="durable bootstrap supersession evidence requires supersession authority",
    ):
        guard_ordinary_bootstrap_admission(state)
    admission = inspect_bootstrap_supersession(
        source_state=state,
        grant=successor,
        authority=authority,
        mutation_inventory=_inventory(state, tmp_path, cfg, predecessor["source"]),
    )
    activate_bootstrap_supersession(
        cfg=cfg,
        source_state=state,
        data_root=tmp_path,
        chroma_dir=Path(cfg["index"]["chroma_dir"]),
        grant=successor,
        authority=authority,
        admission=admission,
    )
    lineage_path = _lineage_path(state, transaction["transaction_id"])
    lineage_path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(BootstrapGrantError, match="invalid JSON"):
        guard_ordinary_bootstrap_admission(state)

    lineage_root = state / "bootstrap_supersession_lineage"
    shutil.rmtree(lineage_root)
    lineage_root.write_text("not-a-directory", encoding="utf-8")
    with pytest.raises(BootstrapGrantError, match="lineage evidence is ambiguous"):
        guard_ordinary_bootstrap_admission(state)
    lineage_root.unlink()
    lineage_root.mkdir()
    outside_lineage = tmp_path / "outside-lineage.json"
    outside_lineage.write_text("{}", encoding="utf-8")
    symlink_lineage = lineage_root / "linked.json"
    symlink_lineage.symlink_to(outside_lineage)
    with pytest.raises(BootstrapGrantError, match="lineage evidence is ambiguous"):
        guard_ordinary_bootstrap_admission(state)
    shutil.rmtree(lineage_root)

    archive_root = state / "superseded_bootstrap_transactions"
    shutil.rmtree(archive_root)
    archive_root.symlink_to(".")
    with pytest.raises(BootstrapGrantError, match="archive evidence is ambiguous"):
        guard_ordinary_bootstrap_admission(state)
    archive_root.unlink()
    archive_root.mkdir()
    archive_entry = archive_root / f"{transaction['transaction_id']}__{successor['operation_id']}"
    archive_entry.mkdir()
    real_tx = archive_entry / "transaction.json"
    real_tx.write_text("{}", encoding="utf-8")
    (archive_entry / "transaction.json").unlink()
    (archive_entry / "transaction.json").symlink_to(real_tx.name)
    with pytest.raises(BootstrapGrantError, match="archive evidence is ambiguous"):
        guard_ordinary_bootstrap_admission(state)


def test_ordinary_bootstrap_admits_when_no_supersession_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    grant = _grant(source, runtime="1" * 40)
    state = tmp_path / "state" / source_state_id(str(source))
    state.mkdir(parents=True)
    guard_ordinary_bootstrap_admission(state)
    journal = BootstrapOperationJournal(state, grant, _binding(grant))
    assert journal.accounting()["predecessor_paid_provider_http_attempts"] == 0
