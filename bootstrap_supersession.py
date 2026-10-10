"""Hermetic failed-bootstrap supersession for exact transform_failed predecessors."""

# pylint: disable=unidiomatic-typecheck,too-many-lines,duplicate-code
# Exact ``type(x) is int`` rejects bool; single bounded authority module — no split yet.
# Shared atomic JSON/fsync helpers intentionally mirror bootstrap_safety / bootstrap script.

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bootstrap_safety import (
    BootstrapGrantError,
    GRANT_FIELDS,
    canonical_json,
    grant_fingerprint,
    sha256_bytes,
    sha256_file,
    validate_grant,
    _read_jsonl,
)
from chroma_readonly import collection_metadata_rows
from chroma_store import is_superseded
from purge_locks import source_flock

SUPERSESSION_DOCUMENT_KEY = "supersede_failed_bootstrap"

SUPERSESSION_AUTHORITY_FIELDS = frozenset(
    {
        "predecessor_operation_id",
        "predecessor_grant_fingerprint",
        "predecessor_transaction_id",
        "predecessor_transaction_sha256",
        "predecessor_source_path",
        "predecessor_source_identity",
        "predecessor_prefix_sha256",
        "predecessor_complete_boundary",
        "predecessor_config_sha256",
        "predecessor_transform_fingerprint",
        "predecessor_runtime_revision",
        "predecessor_binding_fingerprint",
        "predecessor_generation_identity_digest",
        "lifetime_max_paid_http_attempts",
        "predecessor_paid_http_attempts",
        "predecessor_provider_attempts_sha256",
        "predecessor_provider_usage_sha256",
        "predecessor_invocations_sha256",
        "predecessor_terminal_receipt_sha256",
        "predecessor_manifest_sha256",
        "predecessor_source_snapshot_sha256",
        "predecessor_mutation_inventory_sha256",
    }
)

_LINEAGE_RECORD_FIELDS = frozenset(
    {
        "record_type",
        "authority_fingerprint",
        "predecessor_transaction_id",
        "predecessor_transaction_sha256",
        "predecessor_operation_id",
        "predecessor_grant_fingerprint",
        "successor_operation_id",
        "successor_grant_fingerprint",
        "predecessor_paid_http_attempts",
        "lifetime_max_paid_http_attempts",
        "mutation_inventory_digest",
        "archive_relpath",
    }
)

_ALLOWED_SUPERSESSION_PHASES = frozenset({"transform_failed"})
_FORBIDDEN_SUPERSESSION_PHASES = frozenset(
    {
        "APPLYING",
        "applied",
        "complete",
        "COMMITTED",
        "PREPARING",
        "checkpoint",
        "rollback",
        "unknown",
    }
)
_LEGACY_ATTEMPT_ROW_FIELDS = frozenset(
    {
        "record_type",
        "recorded_at",
        "operation_id",
        "grant_fingerprint",
        "invocation_ordinal",
        "attempt_ordinal",
        "provider",
        "operation",
        "model",
        "base_url",
    }
)
_EXPECTED_LEGACY_ATTEMPT_ROWS = 8
_EXPECTED_LEGACY_DEEPSEEK_GENERATE = 2
_EXPECTED_LEGACY_OLLAMA_EMBED = 6
_EXPECTED_LEGACY_DEEPSEEK_USAGE = 2
_ARCHIVE_ROOT_NAME = "superseded_bootstrap_transactions"
_LINEAGE_DIR_NAME = "bootstrap_supersession_lineage"
_CHROMA_COLLECTIONS = ("conversation_summaries", "knowledge_units")
_MUTATION_PROOF_ROLES = (
    "checkpoint",
    "rollback",
    "processed",
    "export",
    "dedupe_queue",
    "duplicate_suppressions",
    "synthesis_failures",
    "prepared_cache",
)


def transaction_file_digest(transaction_path: Path) -> str:
    """SHA-256 of the exact on-disk transaction.json bytes."""

    return sha256_file(transaction_path)


def supersession_authority_fingerprint(authority: dict[str, Any]) -> str:
    return sha256_bytes(
        "convmem-bootstrap-supersession-authority-v1:" + canonical_json(authority)
    )


def generation_identity_digest(generation_identity: dict[str, Any]) -> str:
    device = generation_identity.get("device")
    inode = generation_identity.get("inode")
    if type(device) is not int or type(inode) is not int:
        raise BootstrapGrantError("generation identity requires integer device and inode")
    payload = {"device": device, "inode": inode}
    return sha256_bytes(
        "convmem-bootstrap-generation-identity-v1:" + canonical_json(payload)
    )


def parse_grant_document(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Split a grant file into the immutable grant body and optional supersession authority."""

    if not isinstance(document, dict):
        raise BootstrapGrantError("grant must be a JSON object")
    extra = set(document) - GRANT_FIELDS
    if not extra:
        return validate_grant(document), None
    if extra != {SUPERSESSION_DOCUMENT_KEY}:
        raise BootstrapGrantError(
            "grant must contain exactly grant fields or grant fields plus "
            f"{SUPERSESSION_DOCUMENT_KEY}"
        )
    grant = validate_grant({key: document[key] for key in GRANT_FIELDS})
    authority = document[SUPERSESSION_DOCUMENT_KEY]
    return grant, validate_supersession_authority(authority, grant)


def validate_supersession_authority(
    authority: dict[str, Any], grant: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(authority, dict):
        raise BootstrapGrantError("supersession authority must be a JSON object")
    if set(authority) != SUPERSESSION_AUTHORITY_FIELDS:
        raise BootstrapGrantError(
            "supersession authority must contain exactly "
            + ", ".join(sorted(SUPERSESSION_AUTHORITY_FIELDS))
        )
    digest_fields = (
        "predecessor_operation_id",
        "predecessor_grant_fingerprint",
        "predecessor_transaction_sha256",
        "predecessor_source_identity",
        "predecessor_prefix_sha256",
        "predecessor_config_sha256",
        "predecessor_transform_fingerprint",
        "predecessor_binding_fingerprint",
        "predecessor_generation_identity_digest",
        "predecessor_provider_attempts_sha256",
        "predecessor_provider_usage_sha256",
        "predecessor_invocations_sha256",
        "predecessor_terminal_receipt_sha256",
        "predecessor_manifest_sha256",
        "predecessor_source_snapshot_sha256",
        "predecessor_mutation_inventory_sha256",
    )
    for field in digest_fields:
        value = authority[field]
        if (
            not isinstance(value, str)
            or len(value) != 64
            or value.lower() != value
        ):
            raise BootstrapGrantError(
                f"supersession {field} must be a lowercase SHA-256 digest"
            )
        try:
            int(value, 16)
        except ValueError as exc:
            raise BootstrapGrantError(
                f"supersession {field} must be hexadecimal"
            ) from exc
    tx_id = authority["predecessor_transaction_id"]
    if (
        not isinstance(tx_id, str)
        or len(tx_id) != 32
        or tx_id.lower() != tx_id
        or any(char not in "0123456789abcdef" for char in tx_id)
    ):
        raise BootstrapGrantError(
            "supersession predecessor_transaction_id must be a lowercase 32-hex id"
        )
    source_path = authority["predecessor_source_path"]
    if not isinstance(source_path, str) or not source_path.strip():
        raise BootstrapGrantError("supersession predecessor_source_path must be canonical")
    runtime = authority["predecessor_runtime_revision"]
    if (
        not isinstance(runtime, str)
        or len(runtime) != 40
        or runtime.lower() != runtime
        or any(char not in "0123456789abcdef" for char in runtime)
    ):
        raise BootstrapGrantError(
            "supersession predecessor_runtime_revision must be a canonical Git SHA"
        )
    boundary = authority["predecessor_complete_boundary"]
    lifetime = authority["lifetime_max_paid_http_attempts"]
    carried_paid = authority["predecessor_paid_http_attempts"]
    if type(boundary) is not int or boundary < 1:
        raise BootstrapGrantError(
            "supersession predecessor_complete_boundary must be a positive integer"
        )
    if type(lifetime) is not int or lifetime < 1:
        raise BootstrapGrantError(
            "supersession lifetime_max_paid_http_attempts must be a positive integer"
        )
    if type(carried_paid) is not int or carried_paid < 0:
        raise BootstrapGrantError(
            "supersession predecessor_paid_http_attempts must be a non-negative integer"
        )
    if carried_paid > lifetime:
        raise BootstrapGrantError(
            "supersession predecessor paid attempts exceed lifetime ceiling"
        )
    if carried_paid + int(grant["max_provider_http_attempts"]) > lifetime:
        raise BootstrapGrantError(
            "successor grant would exceed lifetime paid HTTP attempt ceiling"
        )
    if authority["predecessor_source_path"] != grant["source"]:
        raise BootstrapGrantError("supersession source path must match grant source")
    if authority["predecessor_prefix_sha256"] != grant["prefix_sha256"]:
        raise BootstrapGrantError("supersession prefix must match grant prefix")
    if boundary != grant["complete_boundary"]:
        raise BootstrapGrantError("supersession boundary must match grant boundary")
    if grant_fingerprint(grant) == authority["predecessor_grant_fingerprint"]:
        raise BootstrapGrantError(
            "successor grant fingerprint must differ from predecessor grant fingerprint"
        )
    if grant["operation_id"] == authority["predecessor_operation_id"]:
        raise BootstrapGrantError(
            "successor operation id must differ from predecessor operation id"
        )
    return dict(authority)


def _path_inventory(path: Path) -> dict[str, Any]:
    if path.is_file():
        return {"kind": "file", "size": path.stat().st_size, "sha256": sha256_file(path)}
    if not path.is_dir():
        return {"kind": "absent"}
    files = []
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        files.append(
            {
                "path": str(child.relative_to(path)),
                "size": child.stat().st_size,
                "sha256": sha256_file(child),
            }
        )
    return {"kind": "directory", "files": files}


def _directory_inventory_digest(path: Path, label: str) -> str:
    return sha256_bytes(f"{label}:" + canonical_json(_path_inventory(path)))


def snapshot_directory_inventory_digest(snapshot_dir: Path) -> str:
    """Return the bound digest for a predecessor snapshot directory inventory."""

    return _directory_inventory_digest(snapshot_dir, "convmem-bootstrap-snapshot-dir-v1")


def _fsync_directory(path: Path) -> None:
    directory = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    _fsync_directory(path.parent)


def _row_active_for_source(row: dict[str, Any], source_path: str) -> bool:
    if row.get("source_path") != source_path:
        return False
    if is_superseded(row) or bool(row.get("deleted")):
        return False
    return True


def _chroma_row_content_digest(row: dict[str, Any]) -> str:
    payload = {str(key): row[key] for key in sorted(row)}
    return sha256_bytes(
        "convmem-bootstrap-chroma-row-v1:" + canonical_json(payload)
    )


def bootstrap_source_chroma_inventory(
    chroma_dir: Path, source_path: str
) -> dict[str, Any]:
    """Read-only source-scoped Chroma projection inventory for bootstrap proofs."""

    db = Path(chroma_dir).expanduser() / "chroma.sqlite3"
    if not db.is_file():
        return {name: {"count": 0, "entries": []} for name in _CHROMA_COLLECTIONS}
    collections: dict[str, Any] = {}
    for name in _CHROMA_COLLECTIONS:
        rows = [
            row
            for row in collection_metadata_rows(chroma_dir, name)
            if _row_active_for_source(row, source_path)
        ]
        entries = [
            {
                "id": str(row.get("id")),
                "content_digest": _chroma_row_content_digest(row),
            }
            for row in sorted(rows, key=lambda item: str(item.get("id")))
        ]
        collections[name] = {"count": len(entries), "entries": entries}
    return collections


def bootstrap_mutation_inventory(
    source_state: Path,
    data_root: Path,
    cfg: dict,
    *,
    chroma_dir: Path,
    source_path: str,
) -> dict[str, Any]:
    index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    roles = {
        "checkpoint": source_state / "checkpoint.json",
        "rollback": source_state / "rollback.json",
        "processed": Path(index.get("processed_log", data_root / "processed.json")),
        "export": Path(index.get("units_export", data_root / "units.jsonl")),
        "dedupe_queue": data_root / "dedupe_queue.jsonl",
        "duplicate_suppressions": data_root / "ingest_duplicate_suppressions.jsonl",
        "synthesis_failures": data_root / "synthesis_failures.jsonl",
        "prepared_cache": source_state / "prepared",
    }
    inventory = {name: _path_inventory(path) for name, path in roles.items()}
    inventory["chroma_source"] = bootstrap_source_chroma_inventory(
        chroma_dir, source_path
    )
    return inventory


def mutation_inventory_digest(inventory: dict[str, Any]) -> str:
    proof = {role: inventory[role] for role in _MUTATION_PROOF_ROLES}
    proof["chroma_source"] = inventory["chroma_source"]
    return sha256_bytes(
        "convmem-bootstrap-mutation-proof-v1:" + canonical_json(proof)
    )


def _ledger_file_digest(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)
    return sha256_bytes("convmem-bootstrap-absent-ledger-v1:" + path.name)


def _predecessor_operation_root(source_state: Path, predecessor_grant_fingerprint: str) -> Path:
    return source_state / "operations" / predecessor_grant_fingerprint


def _predecessor_snapshot_dir(source_state: Path, transaction_id: str) -> Path:
    return source_state / "snapshots" / transaction_id


def _binding_fingerprint_from_manifest(binding: dict[str, Any]) -> str:
    return sha256_bytes("convmem-bootstrap-binding-v1:" + canonical_json(binding))


def _terminal_receipt_digest(invocations_path: Path) -> tuple[dict[str, Any], str]:
    rows = _read_jsonl(invocations_path)
    terminals = [row for row in rows if row.get("record_type") == "terminal"]
    if len(terminals) != 1:
        raise BootstrapGrantError(
            "predecessor invocation journal must contain exactly one terminal receipt"
        )
    terminal = terminals[0]
    if str(terminal.get("transaction_phase") or "") != "transform_failed":
        raise BootstrapGrantError(
            "predecessor terminal receipt must record transform_failed phase"
        )
    outcome = str(terminal.get("outcome") or "")
    if outcome != "failed":
        raise BootstrapGrantError(
            "predecessor terminal receipt must record failed outcome"
        )
    failure = str(terminal.get("failure_code") or "")
    if failure != "provider_http_budget_exhausted":
        raise BootstrapGrantError(
            "predecessor terminal receipt must record provider budget exhaustion"
        )
    digest = sha256_bytes(
        "convmem-bootstrap-terminal-receipt-v1:" + canonical_json(terminal)
    )
    return terminal, digest


def _authorized_predecessor_provider_bindings(
    manifest: dict[str, Any], provider: str, operation: str
) -> frozenset[tuple[str, str]]:
    binding = manifest.get("binding")
    if not isinstance(binding, dict):
        raise BootstrapGrantError("predecessor manifest must bind grant and binding")
    if provider == "deepseek" and operation == "generate":
        matches: set[tuple[str, str]] = set()
        for role in ("summarize", "distill"):
            section = binding.get(role)
            if not isinstance(section, dict):
                continue
            if section.get("provider") == "deepseek":
                model = section.get("model")
                base_url = section.get("base_url")
                if isinstance(model, str) and isinstance(base_url, str):
                    matches.add((model, base_url))
        if not matches:
            raise BootstrapGrantError(
                "predecessor manifest lacks an authorized DeepSeek generate binding"
            )
        return frozenset(matches)
    if provider == "ollama" and operation == "embed":
        section = binding.get("embedding")
        if not isinstance(section, dict) or section.get("provider") != "ollama":
            raise BootstrapGrantError(
                "predecessor manifest lacks an authorized Ollama embed binding"
            )
        model = section.get("model")
        base_url = section.get("base_url")
        if not isinstance(model, str) or not isinstance(base_url, str):
            raise BootstrapGrantError(
                "predecessor manifest embedding binding is incomplete"
            )
        return frozenset({(model, base_url)})
    raise BootstrapGrantError(
        "predecessor provider attempt row has unsupported provider operation"
    )


def _validate_predecessor_terminal_receipt(
    terminal: dict[str, Any],
    authority: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    grant = manifest.get("grant")
    if not isinstance(grant, dict):
        raise BootstrapGrantError("predecessor manifest must bind grant and binding")
    if str(terminal.get("binding_fingerprint") or "") != authority[
        "predecessor_binding_fingerprint"
    ]:
        raise BootstrapGrantError("predecessor terminal binding fingerprint mismatch")
    if str(terminal.get("source") or "") != authority["predecessor_source_path"]:
        raise BootstrapGrantError("predecessor terminal source path mismatch")
    if str(terminal.get("prefix_sha256") or "") != authority["predecessor_prefix_sha256"]:
        raise BootstrapGrantError("predecessor terminal prefix digest mismatch")
    if str(terminal.get("backup_snapshot") or "") != str(grant.get("backup_snapshot") or ""):
        raise BootstrapGrantError("predecessor terminal backup snapshot mismatch")


def _validate_invocations_ledger(
    invocations_path: Path,
    authority: dict[str, Any],
    terminal: dict[str, Any],
) -> None:
    if not invocations_path.is_file():
        raise BootstrapGrantError("predecessor invocation journal is missing")
    bound_digest = sha256_file(invocations_path)
    if bound_digest != authority["predecessor_invocations_sha256"]:
        raise BootstrapGrantError("predecessor invocation journal digest mismatch")
    if str(terminal.get("operation_id") or "") != authority["predecessor_operation_id"]:
        raise BootstrapGrantError("predecessor terminal operation id mismatch")
    if str(terminal.get("grant_fingerprint") or "") != authority[
        "predecessor_grant_fingerprint"
    ]:
        raise BootstrapGrantError("predecessor terminal grant fingerprint mismatch")
    if int(terminal.get("invocation_ordinal") or 0) != 1:
        raise BootstrapGrantError("predecessor terminal invocation ordinal must be 1")


def _validate_provider_usage_ledger(
    usage_path: Path, authority: dict[str, Any], manifest: dict[str, Any]
) -> None:
    usage_digest = _ledger_file_digest(usage_path)
    if usage_digest != authority["predecessor_provider_usage_sha256"]:
        raise BootstrapGrantError("predecessor provider usage ledger digest mismatch")
    if not usage_path.is_file():
        raise BootstrapGrantError("predecessor provider usage ledger is missing")
    rows = _read_jsonl(usage_path)
    if len(rows) != _EXPECTED_LEGACY_DEEPSEEK_USAGE:
        raise BootstrapGrantError(
            "predecessor provider usage ledger must contain exactly two rows"
        )
    authorized_bindings = _authorized_predecessor_provider_bindings(
        manifest, "deepseek", "generate"
    )
    authorized_models = {model for model, _base in authorized_bindings}
    for row in rows:
        if row.get("record_type") != "provider_usage":
            raise BootstrapGrantError(
                "predecessor provider usage ledger must contain only provider_usage rows"
            )
        if not isinstance(row.get("recorded_at"), str) or not row["recorded_at"].strip():
            raise BootstrapGrantError("predecessor provider usage row missing recorded_at")
        if row.get("provider") != "deepseek" or row.get("operation") != "generate":
            raise BootstrapGrantError(
                "predecessor provider usage row must be DeepSeek generate"
            )
        if row.get("operation_id") != authority["predecessor_operation_id"]:
            raise BootstrapGrantError("predecessor provider usage operation mismatch")
        if row.get("grant_fingerprint") != authority["predecessor_grant_fingerprint"]:
            raise BootstrapGrantError(
                "predecessor provider usage grant fingerprint mismatch"
            )
        if int(row.get("invocation_ordinal") or 0) != 1:
            raise BootstrapGrantError(
                "predecessor provider usage invocation ordinal must be 1"
            )
        model = row.get("model")
        if not isinstance(model, str) or model not in authorized_models:
            raise BootstrapGrantError(
                "predecessor provider usage model does not match manifest binding"
            )


def _validate_predecessor_manifest(
    manifest_path: Path, authority: dict[str, Any]
) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise BootstrapGrantError("predecessor operation manifest is missing")
    manifest_digest = sha256_file(manifest_path)
    if manifest_digest != authority["predecessor_manifest_sha256"]:
        raise BootstrapGrantError("predecessor operation manifest digest mismatch")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapGrantError("predecessor operation manifest is unreadable") from exc
    if not isinstance(manifest, dict):
        raise BootstrapGrantError("predecessor operation manifest must be a JSON object")
    grant = manifest.get("grant")
    binding = manifest.get("binding")
    if not isinstance(grant, dict) or not isinstance(binding, dict):
        raise BootstrapGrantError("predecessor manifest must bind grant and binding")
    if str(manifest.get("operation_id") or "") != authority["predecessor_operation_id"]:
        raise BootstrapGrantError("predecessor manifest operation id mismatch")
    if str(manifest.get("grant_fingerprint") or "") != authority[
        "predecessor_grant_fingerprint"
    ]:
        raise BootstrapGrantError("predecessor manifest grant fingerprint mismatch")
    if str(grant.get("source") or "") != authority["predecessor_source_path"]:
        raise BootstrapGrantError("predecessor manifest source path mismatch")
    if str(grant.get("config_sha256") or "") != authority["predecessor_config_sha256"]:
        raise BootstrapGrantError("predecessor manifest config digest mismatch")
    if str(grant.get("transform_fingerprint") or "") != authority[
        "predecessor_transform_fingerprint"
    ]:
        raise BootstrapGrantError("predecessor manifest transform fingerprint mismatch")
    if str(grant.get("runtime_revision") or "") != authority["predecessor_runtime_revision"]:
        raise BootstrapGrantError("predecessor manifest runtime revision mismatch")
    if _binding_fingerprint_from_manifest(binding) != authority[
        "predecessor_binding_fingerprint"
    ]:
        raise BootstrapGrantError("predecessor manifest binding fingerprint mismatch")
    return manifest


def classify_legacy_predecessor_attempts(
    attempts_path: Path,
    *,
    operation_id: str,
    grant_fingerprint_value: str,
    manifest: dict[str, Any],
) -> tuple[int, str]:
    """Validate eight legacy rows and return carried paid count."""

    if not attempts_path.is_file():
        raise BootstrapGrantError("predecessor provider attempt ledger is missing")
    bound_digest = sha256_file(attempts_path)
    rows = _read_jsonl(attempts_path)
    if len(rows) != _EXPECTED_LEGACY_ATTEMPT_ROWS:
        raise BootstrapGrantError(
            "predecessor provider attempt ledger must contain exactly eight rows"
        )
    deepseek_generate = 0
    ollama_embed = 0
    for expected_ordinal, row in enumerate(rows, start=1):
        if set(row.keys()) != _LEGACY_ATTEMPT_ROW_FIELDS:
            raise BootstrapGrantError(
                "predecessor provider attempt row has unexpected legacy shape"
            )
        if not isinstance(row.get("recorded_at"), str) or not row["recorded_at"].strip():
            raise BootstrapGrantError(
                "predecessor provider attempt row missing recorded_at"
            )
        if row.get("record_type") != "permit_consumed":
            raise BootstrapGrantError(
                "predecessor provider attempt row must be permit_consumed"
            )
        if row.get("operation_id") != operation_id:
            raise BootstrapGrantError("predecessor provider attempt operation mismatch")
        if row.get("grant_fingerprint") != grant_fingerprint_value:
            raise BootstrapGrantError(
                "predecessor provider attempt grant fingerprint mismatch"
            )
        if int(row.get("invocation_ordinal") or 0) != 1:
            raise BootstrapGrantError(
                "predecessor provider attempt invocation ordinal must be 1"
            )
        if int(row.get("attempt_ordinal") or 0) != expected_ordinal:
            raise BootstrapGrantError(
                "predecessor provider attempt ordinals must be sequential 1..8"
            )
        provider = row.get("provider")
        operation = row.get("operation")
        authorized_bindings = _authorized_predecessor_provider_bindings(
            manifest, str(provider), str(operation)
        )
        model = row.get("model")
        base_url = row.get("base_url")
        if (
            not isinstance(model, str)
            or not isinstance(base_url, str)
            or (model, base_url) not in authorized_bindings
        ):
            raise BootstrapGrantError(
                "predecessor provider attempt row does not match manifest binding"
            )
        if provider == "deepseek" and operation == "generate":
            deepseek_generate += 1
        elif provider == "ollama" and operation == "embed":
            ollama_embed += 1
        else:
            raise BootstrapGrantError(
                "predecessor provider attempt row has unsupported provider operation"
            )
    if deepseek_generate != _EXPECTED_LEGACY_DEEPSEEK_GENERATE:
        raise BootstrapGrantError(
            "predecessor provider attempt ledger must contain exactly two "
            "DeepSeek generate rows"
        )
    if ollama_embed != _EXPECTED_LEGACY_OLLAMA_EMBED:
        raise BootstrapGrantError(
            "predecessor provider attempt ledger must contain exactly six "
            "Ollama embed rows"
        )
    return _EXPECTED_LEGACY_DEEPSEEK_GENERATE, bound_digest


def _prepared_cache_admissible(prepared_inventory: dict[str, Any]) -> bool:
    kind = prepared_inventory.get("kind")
    if kind == "absent":
        return True
    if kind == "directory" and not prepared_inventory.get("files"):
        return True
    return False


def prove_predecessor_mutation_inventory(
    transaction: dict[str, Any],
    mutation_inventory: dict[str, Any],
    authority: dict[str, Any],
) -> None:
    phase = str(transaction.get("phase") or "")
    if phase in _FORBIDDEN_SUPERSESSION_PHASES or phase not in _ALLOWED_SUPERSESSION_PHASES:
        raise BootstrapGrantError(
            f"supersession refused for transaction phase {phase or 'unknown'}"
        )
    if transaction.get("rollback_authority_sha256"):
        raise BootstrapGrantError("supersession refused: rollback authority is bound")
    if mutation_inventory["checkpoint"]["kind"] != "absent":
        raise BootstrapGrantError("supersession refused: checkpoint exists")
    if mutation_inventory["rollback"]["kind"] != "absent":
        raise BootstrapGrantError("supersession refused: rollback journal exists")
    if not _prepared_cache_admissible(mutation_inventory["prepared_cache"]):
        raise BootstrapGrantError("supersession refused: prepared cache is not empty")
    digest = mutation_inventory_digest(mutation_inventory)
    if digest != authority["predecessor_mutation_inventory_sha256"]:
        raise BootstrapGrantError("predecessor mutation inventory proof mismatch")


def _validate_predecessor_operation_evidence(
    source_state: Path,
    authority: dict[str, Any],
    *,
    transaction: dict[str, Any] | None = None,
    mutation_inventory: dict[str, Any] | None = None,
) -> int:
    root = _predecessor_operation_root(
        source_state, authority["predecessor_grant_fingerprint"]
    )
    attempts_path = root / "provider_attempts.jsonl"
    usage_path = root / "provider_usage.jsonl"
    invocations_path = root / "invocations.jsonl"
    manifest_path = root / "manifest.json"
    snapshot_dir = _predecessor_snapshot_dir(
        source_state, authority["predecessor_transaction_id"]
    )
    manifest = _validate_predecessor_manifest(manifest_path, authority)
    carried_paid, attempts_digest = classify_legacy_predecessor_attempts(
        attempts_path,
        operation_id=authority["predecessor_operation_id"],
        grant_fingerprint_value=authority["predecessor_grant_fingerprint"],
        manifest=manifest,
    )
    if attempts_digest != authority["predecessor_provider_attempts_sha256"]:
        raise BootstrapGrantError("predecessor provider attempt ledger digest mismatch")
    _validate_provider_usage_ledger(usage_path, authority, manifest)
    if not snapshot_dir.is_dir():
        raise BootstrapGrantError("predecessor source snapshot directory is missing")
    snapshot_digest = _directory_inventory_digest(
        snapshot_dir, "convmem-bootstrap-snapshot-dir-v1"
    )
    if snapshot_digest != authority["predecessor_source_snapshot_sha256"]:
        raise BootstrapGrantError("predecessor source snapshot inventory mismatch")
    terminal, terminal_digest = _terminal_receipt_digest(invocations_path)
    _validate_predecessor_terminal_receipt(terminal, authority, manifest)
    _validate_invocations_ledger(invocations_path, authority, terminal)
    if terminal_digest != authority["predecessor_terminal_receipt_sha256"]:
        raise BootstrapGrantError("predecessor terminal receipt digest mismatch")
    if carried_paid != authority["predecessor_paid_http_attempts"]:
        raise BootstrapGrantError("predecessor paid attempt carry-forward mismatch")
    if transaction is not None and mutation_inventory is not None:
        prove_predecessor_mutation_inventory(transaction, mutation_inventory, authority)
        generation = transaction.get("generation_identity")
        if not isinstance(generation, dict):
            raise BootstrapGrantError("predecessor transaction generation identity missing")
        if generation_identity_digest(generation) != authority[
            "predecessor_generation_identity_digest"
        ]:
            raise BootstrapGrantError("predecessor generation identity mismatch")
    return carried_paid


def _read_transaction(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _validate_lineage_evidence_file(path: Path) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BootstrapGrantError("supersession lineage record is unreadable") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BootstrapGrantError("supersession lineage record is invalid JSON") from exc
    if not isinstance(value, dict):
        raise BootstrapGrantError("supersession lineage record must be a JSON object")
    if set(value) != _LINEAGE_RECORD_FIELDS:
        raise BootstrapGrantError("supersession lineage record has unexpected shape")


def _classify_supersession_evidence_root(path: Path, *, kind: str) -> bool:
    """Return True when a real directory is present; fail closed on unsafe shapes."""

    if path.is_symlink():
        raise BootstrapGrantError(f"supersession {kind} evidence is ambiguous")
    if not path.exists():
        return False
    if not path.is_dir():
        raise BootstrapGrantError(f"supersession {kind} evidence is ambiguous")
    return True


def _iter_supersession_evidence_entries(root: Path, *, kind: str) -> list[Path]:
    try:
        return sorted(root.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise BootstrapGrantError(f"supersession {kind} evidence is unreadable") from exc


def _scan_durable_bootstrap_supersession_evidence(source_state: Path) -> bool:
    """Return True when durable supersession artifacts require explicit authority."""

    evidence = False
    lineage_root = source_state / _LINEAGE_DIR_NAME
    if _classify_supersession_evidence_root(lineage_root, kind="lineage"):
        for entry in _iter_supersession_evidence_entries(lineage_root, kind="lineage"):
            if entry.is_symlink():
                raise BootstrapGrantError("supersession lineage evidence is ambiguous")
            if not entry.is_file():
                raise BootstrapGrantError("supersession lineage evidence is ambiguous")
            if entry.suffix != ".json":
                raise BootstrapGrantError("supersession lineage evidence is ambiguous")
            _validate_lineage_evidence_file(entry)
            evidence = True

    archive_root = source_state / _ARCHIVE_ROOT_NAME
    if _classify_supersession_evidence_root(archive_root, kind="archive"):
        for entry in _iter_supersession_evidence_entries(archive_root, kind="archive"):
            if entry.is_symlink():
                raise BootstrapGrantError("supersession archive evidence is ambiguous")
            if entry.is_file():
                raise BootstrapGrantError("supersession archive evidence is ambiguous")
            if not entry.is_dir():
                raise BootstrapGrantError("supersession archive evidence is ambiguous")
            archived_tx = entry / "transaction.json"
            if archived_tx.is_symlink():
                raise BootstrapGrantError("supersession archive evidence is ambiguous")
            if archived_tx.is_file():
                evidence = True
                continue
            try:
                nonempty = any(entry.iterdir())
            except OSError as exc:
                raise BootstrapGrantError("supersession archive evidence is unreadable") from exc
            if nonempty:
                raise BootstrapGrantError("supersession archive evidence is ambiguous")
            raise BootstrapGrantError("supersession archive evidence is ambiguous")
    return evidence


def guard_ordinary_bootstrap_admission(source_state: Path) -> None:
    """Refuse ordinary bootstrap when durable supersession evidence is present."""

    if _scan_durable_bootstrap_supersession_evidence(source_state):
        raise BootstrapGrantError(
            "durable bootstrap supersession evidence requires supersession authority"
        )


def _lineage_path(source_state: Path, predecessor_transaction_id: str) -> Path:
    return (
        source_state
        / _LINEAGE_DIR_NAME
        / f"{predecessor_transaction_id}.json"
    )


def _read_lineage_record(
    source_state: Path, predecessor_transaction_id: str
) -> dict[str, Any] | None:
    path = _lineage_path(source_state, predecessor_transaction_id)
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BootstrapGrantError("supersession lineage record is unreadable") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BootstrapGrantError("supersession lineage record is invalid JSON") from exc
    if not isinstance(value, dict):
        raise BootstrapGrantError("supersession lineage record must be a JSON object")
    if set(value) != _LINEAGE_RECORD_FIELDS:
        raise BootstrapGrantError("supersession lineage record has unexpected shape")
    return value


def _archive_dir_for(
    source_state: Path,
    authority: dict[str, Any],
    successor_operation_id: str,
) -> Path:
    return (
        source_state
        / _ARCHIVE_ROOT_NAME
        / f"{authority['predecessor_transaction_id']}__{successor_operation_id}"
    )


def _conflicting_predecessor_archive(
    source_state: Path,
    authority: dict[str, Any],
    archive_dir: Path,
) -> None:
    root = source_state / _ARCHIVE_ROOT_NAME
    if not root.is_dir():
        return
    prefix = f"{authority['predecessor_transaction_id']}__"
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith(prefix) and entry != archive_dir:
            raise BootstrapGrantError(
                "predecessor transaction already superseded by another successor"
            )


def _validate_archived_transaction(
    archive_dir: Path, authority: dict[str, Any]
) -> None:
    archived = archive_dir / "transaction.json"
    if not archived.is_file():
        raise BootstrapGrantError("supersession archive is missing predecessor transaction")
    digest = sha256_file(archived)
    if digest != authority["predecessor_transaction_sha256"]:
        raise BootstrapGrantError("archived predecessor transaction digest mismatch")


def _validate_transaction_fields(
    transaction: dict[str, Any], authority: dict[str, Any]
) -> None:
    if transaction.get("bootstrap_existing") is not True:
        raise BootstrapGrantError("supersession requires bootstrap_existing predecessor")
    if str(transaction.get("transaction_id") or "") != authority["predecessor_transaction_id"]:
        raise BootstrapGrantError("predecessor transaction id mismatch")
    if str(transaction.get("operation_id") or "") != authority["predecessor_operation_id"]:
        raise BootstrapGrantError("predecessor operation id mismatch")
    if str(transaction.get("grant_fingerprint") or "") != authority["predecessor_grant_fingerprint"]:
        raise BootstrapGrantError("predecessor grant fingerprint mismatch")
    if str(transaction.get("binding_fingerprint") or "") != authority["predecessor_binding_fingerprint"]:
        raise BootstrapGrantError("predecessor binding fingerprint mismatch")
    if str(transaction.get("source_path") or "") != authority["predecessor_source_path"]:
        raise BootstrapGrantError("predecessor source path mismatch")
    if str(transaction.get("source_identity") or "") != authority["predecessor_source_identity"]:
        raise BootstrapGrantError("predecessor source identity mismatch")
    if str(transaction.get("prefix_sha256") or "") != authority["predecessor_prefix_sha256"]:
        raise BootstrapGrantError("predecessor prefix digest mismatch")
    if int(transaction.get("complete_boundary") or 0) != authority["predecessor_complete_boundary"]:
        raise BootstrapGrantError("predecessor complete boundary mismatch")
    generation = transaction.get("generation_identity")
    if not isinstance(generation, dict):
        raise BootstrapGrantError("predecessor transaction generation identity missing")
    if generation_identity_digest(generation) != authority[
        "predecessor_generation_identity_digest"
    ]:
        raise BootstrapGrantError("predecessor generation identity mismatch")


def _validate_lineage_record(
    record: dict[str, Any],
    *,
    authority: dict[str, Any],
    grant: dict[str, Any],
    carried_paid: int,
    archive_dir: Path,
    source_state: Path,
) -> None:
    if record.get("record_type") != "supersession":
        raise BootstrapGrantError("supersession lineage record type mismatch")
    if record.get("authority_fingerprint") != supersession_authority_fingerprint(authority):
        raise BootstrapGrantError("supersession lineage authority fingerprint mismatch")
    successor_fp = grant_fingerprint(grant)
    if record.get("successor_operation_id") != grant["operation_id"]:
        raise BootstrapGrantError("supersession lineage successor operation mismatch")
    if record.get("successor_grant_fingerprint") != successor_fp:
        raise BootstrapGrantError("supersession lineage successor grant mismatch")
    if record.get("predecessor_transaction_id") != authority["predecessor_transaction_id"]:
        raise BootstrapGrantError("supersession lineage predecessor transaction mismatch")
    if record.get("predecessor_transaction_sha256") != authority[
        "predecessor_transaction_sha256"
    ]:
        raise BootstrapGrantError("supersession lineage predecessor digest mismatch")
    if record.get("predecessor_operation_id") != authority["predecessor_operation_id"]:
        raise BootstrapGrantError("supersession lineage predecessor operation mismatch")
    if record.get("predecessor_grant_fingerprint") != authority[
        "predecessor_grant_fingerprint"
    ]:
        raise BootstrapGrantError("supersession lineage predecessor grant mismatch")
    if int(record.get("predecessor_paid_http_attempts") or -1) != carried_paid:
        raise BootstrapGrantError("supersession lineage accounting mismatch")
    if int(record.get("lifetime_max_paid_http_attempts") or -1) != int(
        authority["lifetime_max_paid_http_attempts"]
    ):
        raise BootstrapGrantError("supersession lineage lifetime ceiling mismatch")
    if record.get("mutation_inventory_digest") != authority[
        "predecessor_mutation_inventory_sha256"
    ]:
        raise BootstrapGrantError("supersession lineage mutation inventory mismatch")
    if record.get("archive_relpath") != str(archive_dir.relative_to(source_state)):
        raise BootstrapGrantError("supersession lineage archive path mismatch")


def _lineage_payload(
    *,
    authority: dict[str, Any],
    grant: dict[str, Any],
    carried_paid: int,
    mutation_inventory: dict[str, Any],
    archive_dir: Path,
    source_state: Path,
) -> dict[str, Any]:
    return {
        "record_type": "supersession",
        "authority_fingerprint": supersession_authority_fingerprint(authority),
        "predecessor_transaction_id": authority["predecessor_transaction_id"],
        "predecessor_transaction_sha256": authority["predecessor_transaction_sha256"],
        "predecessor_operation_id": authority["predecessor_operation_id"],
        "predecessor_grant_fingerprint": authority["predecessor_grant_fingerprint"],
        "successor_operation_id": grant["operation_id"],
        "successor_grant_fingerprint": grant_fingerprint(grant),
        "predecessor_paid_http_attempts": carried_paid,
        "lifetime_max_paid_http_attempts": int(
            authority["lifetime_max_paid_http_attempts"]
        ),
        "mutation_inventory_digest": mutation_inventory_digest(mutation_inventory),
        "archive_relpath": str(archive_dir.relative_to(source_state)),
    }


def successor_invocation_allows_lineage_recovery(
    source_state: Path, grant: dict[str, Any]
) -> bool:
    """True when a successor start exists without any terminal receipt."""

    root = source_state / "operations" / grant_fingerprint(grant)
    invocations_path = root / "invocations.jsonl"
    rows = _read_jsonl(invocations_path)
    starts = [row for row in rows if row.get("record_type") == "start"]
    terminals = [row for row in rows if row.get("record_type") == "terminal"]
    if terminals:
        return False
    return bool(starts)


def successor_invocation_terminal_committed(source_state: Path, grant: dict[str, Any]) -> bool:
    root = source_state / "operations" / grant_fingerprint(grant)
    invocations_path = root / "invocations.jsonl"
    for row in _read_jsonl(invocations_path):
        if row.get("record_type") != "terminal":
            continue
        outcome = str(row.get("outcome") or "")
        phase = str(row.get("transaction_phase") or "")
        if outcome == "committed" or phase in {"complete", "COMMITTED", "applied"}:
            return True
    return False


@dataclass(frozen=True)
class SupersessionAdmission:
    predecessor_paid_http_attempts: int
    lifetime_max_paid_http_attempts: int
    archive_dir: Path | None
    recovery_mode: bool
    finish_lineage_only: bool = False
    successor_recovery_without_transaction: bool = False


def supersession_accounting_from_authority(
    authority: dict[str, Any],
) -> dict[str, Any]:
    return {
        "predecessor_paid_http_attempts": int(authority["predecessor_paid_http_attempts"]),
        "lifetime_max_paid_http_attempts": int(
            authority["lifetime_max_paid_http_attempts"]
        ),
        "predecessor_operation_id": str(authority["predecessor_operation_id"]),
        "predecessor_grant_fingerprint": str(authority["predecessor_grant_fingerprint"]),
        "authority_fingerprint": supersession_authority_fingerprint(authority),
    }


def _recapture_mutation_inventory(
    *,
    cfg: dict,
    source_state: Path,
    data_root: Path,
    chroma_dir: Path,
    source_path: str,
) -> dict[str, Any]:
    return bootstrap_mutation_inventory(
        source_state,
        data_root,
        cfg,
        chroma_dir=chroma_dir,
        source_path=source_path,
    )


def inspect_bootstrap_supersession(
    *,
    source_state: Path,
    grant: dict[str, Any],
    authority: dict[str, Any],
    mutation_inventory: dict[str, Any],
) -> SupersessionAdmission:
    """Validate supersession preconditions without mutating source state."""

    successor_fp = grant_fingerprint(grant)
    predecessor_tx = authority["predecessor_transaction_id"]
    lineage = _read_lineage_record(source_state, predecessor_tx)
    archive_dir = _archive_dir_for(source_state, authority, str(grant["operation_id"]))
    lifetime = int(authority["lifetime_max_paid_http_attempts"])
    transaction_path = source_state / "transaction.json"

    if lineage is not None:
        if (
            lineage.get("successor_operation_id") != grant["operation_id"]
            or lineage.get("successor_grant_fingerprint") != successor_fp
        ):
            raise BootstrapGrantError(
                "predecessor transaction already superseded by another successor"
            )
        _validate_archived_transaction(archive_dir, authority)
        carried_paid = _validate_predecessor_operation_evidence(
            source_state, authority
        )
        _validate_lineage_record(
            lineage,
            authority=authority,
            grant=grant,
            carried_paid=carried_paid,
            archive_dir=archive_dir,
            source_state=source_state,
        )
        active = _read_transaction(transaction_path)
        successor_recovery_without_transaction = False
        if active is None:
            if successor_invocation_terminal_committed(source_state, grant):
                raise BootstrapGrantError(
                    "successor bootstrap already committed and cannot be replayed"
                )
            if successor_invocation_allows_lineage_recovery(source_state, grant):
                successor_recovery_without_transaction = True
        else:
            if active.get("grant_fingerprint") != successor_fp:
                raise BootstrapGrantError(
                    "active transaction does not match authorized successor grant"
                )
            phase = str(active.get("phase") or "")
            if phase not in _ALLOWED_SUPERSESSION_PHASES | {"PREPARING", "APPLYING"}:
                raise BootstrapGrantError(
                    f"successor recovery refused for transaction phase {phase or 'unknown'}"
                )
        return SupersessionAdmission(
            predecessor_paid_http_attempts=carried_paid,
            lifetime_max_paid_http_attempts=lifetime,
            archive_dir=archive_dir,
            recovery_mode=True,
            successor_recovery_without_transaction=successor_recovery_without_transaction,
        )

    staged_archive = archive_dir.is_dir() and (archive_dir / "transaction.json").is_file()
    if staged_archive:
        if _read_transaction(transaction_path) is not None:
            raise BootstrapGrantError(
                "supersession staged archive conflicts with active predecessor transaction"
            )
        _validate_archived_transaction(archive_dir, authority)
        archived_tx = _read_transaction(archive_dir / "transaction.json")
        carried_paid = _validate_predecessor_operation_evidence(
            source_state,
            authority,
            transaction=archived_tx,
            mutation_inventory=mutation_inventory,
        )
        return SupersessionAdmission(
            predecessor_paid_http_attempts=carried_paid,
            lifetime_max_paid_http_attempts=lifetime,
            archive_dir=archive_dir,
            recovery_mode=True,
            finish_lineage_only=True,
        )

    _conflicting_predecessor_archive(source_state, authority, archive_dir)

    transaction = _read_transaction(transaction_path)
    if transaction is None:
        raise BootstrapGrantError("supersession requires an existing bootstrap transaction")
    digest = transaction_file_digest(transaction_path)
    if digest != authority["predecessor_transaction_sha256"]:
        raise BootstrapGrantError("predecessor transaction digest mismatch")
    _validate_transaction_fields(transaction, authority)
    prove_predecessor_mutation_inventory(transaction, mutation_inventory, authority)
    carried_paid = _validate_predecessor_operation_evidence(
        source_state,
        authority,
        transaction=transaction,
        mutation_inventory=mutation_inventory,
    )
    if carried_paid >= lifetime:
        raise BootstrapGrantError("predecessor paid attempt budget already exhausted")
    return SupersessionAdmission(
        predecessor_paid_http_attempts=carried_paid,
        lifetime_max_paid_http_attempts=lifetime,
        archive_dir=None,
        recovery_mode=False,
    )


def activate_bootstrap_supersession(
    *,
    cfg: dict,
    source_state: Path,
    data_root: Path,
    chroma_dir: Path,
    grant: dict[str, Any],
    authority: dict[str, Any],
    admission: SupersessionAdmission,
) -> SupersessionAdmission:
    """Archive the exact predecessor transaction and publish durable lineage."""

    source_path = str(grant["source"])
    archive_dir = _archive_dir_for(source_state, authority, str(grant["operation_id"]))

    def _publish_lineage(
        carried_paid: int, mutation_inventory: dict[str, Any]
    ) -> None:
        payload = _lineage_payload(
            authority=authority,
            grant=grant,
            carried_paid=carried_paid,
            mutation_inventory=mutation_inventory,
            archive_dir=archive_dir,
            source_state=source_state,
        )
        _atomic_json(
            _lineage_path(source_state, authority["predecessor_transaction_id"]),
            payload,
        )

    with source_flock(cfg, source_path):
        mutation_inventory = _recapture_mutation_inventory(
            cfg=cfg,
            source_state=source_state,
            data_root=data_root,
            chroma_dir=chroma_dir,
            source_path=source_path,
        )
        if admission.finish_lineage_only:
            if admission.archive_dir is None:
                raise BootstrapGrantError("supersession lineage finish lacks archive")
            carried_paid = _validate_predecessor_operation_evidence(
                source_state,
                authority,
                transaction=_read_transaction(archive_dir / "transaction.json"),
                mutation_inventory=mutation_inventory,
            )
            _publish_lineage(carried_paid, mutation_inventory)
            return SupersessionAdmission(
                predecessor_paid_http_attempts=carried_paid,
                lifetime_max_paid_http_attempts=admission.lifetime_max_paid_http_attempts,
                archive_dir=archive_dir,
                recovery_mode=True,
            )

        if admission.recovery_mode and not admission.finish_lineage_only:
            inspect_bootstrap_supersession(
                source_state=source_state,
                grant=grant,
                authority=authority,
                mutation_inventory=mutation_inventory,
            )
            return admission

        inspect_bootstrap_supersession(
            source_state=source_state,
            grant=grant,
            authority=authority,
            mutation_inventory=mutation_inventory,
        )
        transaction_path = source_state / "transaction.json"
        if archive_dir.exists():
            raise BootstrapGrantError("supersession archive path already exists")
        archive_dir.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(archive_dir.parent, 0o700)
        archive_dir.mkdir(parents=False, exist_ok=False)
        os.chmod(archive_dir, 0o700)
        archived_tx = archive_dir / "transaction.json"
        os.replace(transaction_path, archived_tx)
        _fsync_directory(archive_dir)
        _fsync_directory(source_state)
        _validate_archived_transaction(archive_dir, authority)
        carried_paid = _validate_predecessor_operation_evidence(
            source_state,
            authority,
            transaction=_read_transaction(archived_tx),
            mutation_inventory=mutation_inventory,
        )
        _publish_lineage(carried_paid, mutation_inventory)
        return SupersessionAdmission(
            predecessor_paid_http_attempts=carried_paid,
            lifetime_max_paid_http_attempts=admission.lifetime_max_paid_http_attempts,
            archive_dir=archive_dir,
            recovery_mode=False,
        )
