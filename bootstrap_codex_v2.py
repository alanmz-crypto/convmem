"""Codex rollout bootstrap grant v2 validation and read-only preflight (Arc #286 T1)."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from adapters.detect import detect_format
from bootstrap_safety import (
    GRANT_FIELDS,
    BootstrapGrantError,
    canonical_json,
    sha256_bytes,
    validate_grant_common_fields,
)
from bootstrap_supersession import SUPERSESSION_DOCUMENT_KEY, guard_ordinary_bootstrap_admission
from incremental_jsonl import decide_eligibility, source_state_id as incremental_source_state_id
from incremental_jsonl_codex_admission import (
    CodexRolloutAdmissionSettings,
    admits_path_checks_1_4,
    parse_rollout_basename,
    verify_session_meta_identity,
)
from incremental_jsonl_formats import get_format_spec
from incremental_jsonl_isolation import open_source_readonly, validate_regular_source
from incremental_transform_contract import (
    RECOVERY_PROTOCOL_VERSION,
    recovery_protocol_supported,
    validate_descriptor_digest,
)
from ingest import chunk_messages, load_processed

CODEX_ROLLOUT_FORMAT = "jsonl_codex_rollout"
COORDINATION_PROTOCOL_VERSION = 1


def coordinator_source_state_id_for_path(canonical_path: str) -> str:
    """Match IncrementalJsonlCoordinator source_id derivation for a detected format."""
    detected = detect_format(Path(canonical_path))
    spec = get_format_spec(detected)
    format_id = spec.format_id if spec is not None else CODEX_ROLLOUT_FORMAT
    return incremental_source_state_id(canonical_path, format_id=format_id)


def v2_source_state_directory(state_root: Path, grant: dict[str, Any]) -> Path:
    path_key = str(Path(grant["source"]))
    state_id = incremental_source_state_id(path_key, format_id=CODEX_ROLLOUT_FORMAT)
    return state_root / state_id

MAX_LOCK_WAIT_SECONDS = 3600

_GRANT_V2_EXTENSION_FIELDS = frozenset(
    {
        "grant_version",
        "adapter_format",
        "adapter_contract_version",
        "coordination_protocol_version",
        "source_state_id",
        "session_id",
        "source_device",
        "source_inode",
        "max_source_bytes",
        "lock_wait_seconds",
        "transform_descriptor",
        "recovery_protocol_version",
        "outer_budget_authority_sha256",
    }
)
GRANT_FIELDS_V2 = GRANT_FIELDS | _GRANT_V2_EXTENSION_FIELDS


def operation_identity_v2(grant_without_operation_id: dict[str, Any]) -> str:
    body = dict(grant_without_operation_id)
    body.pop("operation_id", None)
    return sha256_bytes("convmem-bootstrap-operation-v2:" + canonical_json(body))


def grant_fingerprint_v2(grant: dict[str, Any]) -> str:
    return sha256_bytes("convmem-bootstrap-grant-v2:" + canonical_json(grant))


def _require_uuid(value: str, field: str) -> uuid.UUID:
    if not isinstance(value, str) or not value.strip():
        raise BootstrapGrantError(f"grant {field} must be a non-empty UUID string")
    try:
        parsed = uuid.UUID(value.strip())
    except ValueError as exc:
        raise BootstrapGrantError(f"grant {field} must be a UUID") from exc
    return parsed


def _validate_v2_extensions(grant: dict[str, Any], source: Path) -> None:
    if type(grant["grant_version"]) is not int or grant["grant_version"] != 2:
        raise BootstrapGrantError("grant grant_version must equal 2")
    if grant["adapter_format"] != CODEX_ROLLOUT_FORMAT:
        raise BootstrapGrantError("grant adapter_format must be jsonl_codex_rollout")
    spec = get_format_spec(CODEX_ROLLOUT_FORMAT)
    if spec is None:
        raise BootstrapGrantError("codex rollout format spec is unavailable")
    if grant["adapter_contract_version"] != spec.adapter_contract_version:
        raise BootstrapGrantError("grant adapter_contract_version mismatch")
    if (
        type(grant["coordination_protocol_version"]) is not int
        or grant["coordination_protocol_version"] != COORDINATION_PROTOCOL_VERSION
    ):
        raise BootstrapGrantError("grant coordination_protocol_version must equal 1")
    path_key = str(source)
    expected_state = incremental_source_state_id(path_key, format_id=CODEX_ROLLOUT_FORMAT)
    if grant["source_state_id"] != expected_state:
        raise BootstrapGrantError("grant source_state_id does not match format-bound identity")
    session = _require_uuid(grant["session_id"], "session_id")
    try:
        rollout_uid, _ = parse_rollout_basename(source)
    except ValueError as exc:
        raise BootstrapGrantError("grant source basename is not a valid rollout") from exc
    if session != rollout_uid:
        raise BootstrapGrantError("grant session_id does not match rollout basename")
    if type(grant["source_device"]) is not int or grant["source_device"] < 0:
        raise BootstrapGrantError("grant source_device must be a non-negative integer")
    if type(grant["source_inode"]) is not int or grant["source_inode"] < 1:
        raise BootstrapGrantError("grant source_inode must be a positive integer")
    if type(grant["max_source_bytes"]) is not int or grant["max_source_bytes"] < 1:
        raise BootstrapGrantError("grant max_source_bytes must be a positive integer")
    lock_wait = grant["lock_wait_seconds"]
    if (
        type(lock_wait) is not int
        or lock_wait < 1
        or lock_wait > MAX_LOCK_WAIT_SECONDS
    ):
        raise BootstrapGrantError("grant lock_wait_seconds is out of bounds")
    descriptor = grant["transform_descriptor"]
    if not isinstance(descriptor, dict):
        raise BootstrapGrantError("grant transform_descriptor must be a JSON object")
    try:
        validate_descriptor_digest(descriptor, grant["transform_fingerprint"])
    except ValueError as exc:
        raise BootstrapGrantError(str(exc)) from exc
    protocol = grant["recovery_protocol_version"]
    if type(protocol) is not int or not recovery_protocol_supported(protocol):
        raise BootstrapGrantError("grant recovery_protocol_version is unsupported")
    if protocol != RECOVERY_PROTOCOL_VERSION:
        raise BootstrapGrantError("grant recovery_protocol_version must match supported protocol")
    digest = grant["outer_budget_authority_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or digest.lower() != digest
    ):
        raise BootstrapGrantError(
            "grant outer_budget_authority_sha256 must be a lowercase SHA-256"
        )
    try:
        int(digest, 16)
    except ValueError as exc:
        raise BootstrapGrantError(
            "grant outer_budget_authority_sha256 must be hexadecimal"
        ) from exc


def validate_grant_v2(grant: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(grant, dict):
        raise BootstrapGrantError("grant must be a JSON object")
    if set(grant) != GRANT_FIELDS_V2:
        raise BootstrapGrantError(
            "grant must contain exactly " + ", ".join(sorted(GRANT_FIELDS_V2))
        )
    source = Path(grant["source"])
    _validate_v2_extensions(grant, source)
    if detect_format(source) != CODEX_ROLLOUT_FORMAT:
        raise BootstrapGrantError("grant source detection is not jsonl_codex_rollout")
    fd = open_source_readonly(source)
    try:
        info = validate_regular_source(fd)
    finally:
        os.close(fd)
    if grant["source_device"] != info.st_dev or grant["source_inode"] != info.st_ino:
        raise BootstrapGrantError("grant source device/inode mismatch")
    if info.st_size > grant["max_source_bytes"]:
        raise BootstrapGrantError("grant source exceeds max_source_bytes")
    expected_operation = operation_identity_v2(grant)
    if grant["operation_id"] != expected_operation:
        raise BootstrapGrantError("grant operation_id does not match its immutable body")
    validate_grant_common_fields(grant)
    return dict(grant)


def parse_v2_grant_document(document: dict[str, Any]) -> tuple[dict[str, Any], None]:
    if not isinstance(document, dict):
        raise BootstrapGrantError("grant must be a JSON object")
    if SUPERSESSION_DOCUMENT_KEY in document:
        raise BootstrapGrantError("v2 bootstrap does not support supersession authority")
    if document.get("grant_version") != 2:
        raise BootstrapGrantError("grant grant_version must equal 2")
    return validate_grant_v2(document), None


def _read_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _read_transaction(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _retry_outcome(state_dir: Path) -> str | None:
    retry_path = state_dir / "retry_state.json"
    if not retry_path.is_file():
        return None
    try:
        payload = json.loads(retry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "retry_state_unavailable"
    if not isinstance(payload, dict):
        return "retry_state_unavailable"
    return str(payload.get("outcome") or payload.get("error_code") or "") or None


def _codex_admission_settings(cfg: dict) -> CodexRolloutAdmissionSettings | None:
    from config import incremental_jsonl_settings

    settings = incremental_jsonl_settings(cfg)
    return settings.codex_rollout_admission


def _dry_run_preflight_impl(
    grant: dict[str, Any],
    *,
    cfg: dict,
    state_root: Path,
    chroma_row_count: int = 0,
) -> dict[str, Any]:
    grant = validate_grant_v2(grant)
    source = Path(grant["source"])
    path_key = str(source)
    blockers: list[str] = []
    spec = get_format_spec(CODEX_ROLLOUT_FORMAT)
    assert spec is not None
    view = spec.parse_complete_prefix(path_key)
    if (
        view.prefix_sha256 != grant["prefix_sha256"]
        or view.complete_boundary != grant["complete_boundary"]
    ):
        blockers.append("prefix_mismatch")
    chunks = len(chunk_messages(view.messages, grant["chunk_size"], grant["chunk_overlap"]))
    if chunks > grant["max_chunks"]:
        blockers.append("chunk_cap_exceeded")
    identity_refusal = verify_session_meta_identity(source, view.raw_prefix or b"")
    if identity_refusal:
        blockers.append(identity_refusal)
    admission = _codex_admission_settings(cfg)
    if admission is None:
        blockers.append("codex_admission_unconfigured")
    elif not admits_path_checks_1_4(admission, path_key, CODEX_ROLLOUT_FORMAT):
        blockers.append("codex_admission_rejected")
    elif len(view.raw_prefix or b"") > admission.max_source_bytes:
        blockers.append("source_too_large")
    computed_state_id = incremental_source_state_id(path_key, format_id=CODEX_ROLLOUT_FORMAT)
    source_state = state_root / computed_state_id
    try:
        guard_ordinary_bootstrap_admission(source_state)
    except BootstrapGrantError:
        blockers.append("supersession_evidence_present")
    checkpoint = _read_checkpoint(source_state / "checkpoint.json")
    if checkpoint is not None:
        blockers.append("checkpoint_present")
    transaction = _read_transaction(source_state / "transaction.json")
    if transaction is not None:
        blockers.append("transaction_present")
    processed = load_processed(str(cfg["index"]["processed_log"]))
    eligibility = decide_eligibility(
        enabled=True,
        detected_format=CODEX_ROLLOUT_FORMAT,
        path_key=path_key,
        processed=processed,
        chroma_row_count=chroma_row_count,
        checkpoint=checkpoint,
        eligible_formats=frozenset({CODEX_ROLLOUT_FORMAT}),
    )
    if eligibility not in {"bootstrap_required", "eligible_new_source"}:
        blockers.append(f"ineligible:{eligibility}")
    retry_outcome = _retry_outcome(source_state)
    if retry_outcome and retry_outcome not in {"", "bootstrap_required"}:
        blockers.append(f"retry_state:{retry_outcome}")
    kiro_state_id = incremental_source_state_id(path_key)
    coordinator_state_dir = str(source_state)
    return {
        "grant_version": 2,
        "operation_id": grant["operation_id"],
        "grant_fingerprint_v2": grant_fingerprint_v2(grant),
        "source_state_id": computed_state_id,
        "kiro_default_state_id": kiro_state_id,
        "coordinator_state_dir": coordinator_state_dir,
        "proposed_chunk_count": chunks,
        "complete_boundary": grant["complete_boundary"],
        "prefix_sha256": grant["prefix_sha256"],
        "blockers": blockers,
        "ready": not blockers,
    }


def dry_run_preflight(
    grant: dict[str, Any],
    *,
    cfg: dict,
    state_root: Path,
    chroma_row_count: int = 0,
) -> dict[str, Any]:
    def _run() -> dict[str, Any]:
        return _dry_run_preflight_impl(
            grant,
            cfg=cfg,
            state_root=state_root,
            chroma_row_count=chroma_row_count,
        )

    from bootstrap_codex_v2_dry_run_audit import audit_active, run_audited

    if audit_active():
        return run_audited(_run, cfg=cfg, state_root=state_root)
    return _run()

