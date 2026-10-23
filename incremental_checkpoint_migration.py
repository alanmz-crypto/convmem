"""Hermetic-only checkpoint/cache migration to transform contract v2."""

# pylint: disable=duplicate-code  # plan fields mirror coordinator transform inputs

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from incremental_jsonl import _atomic_json, _read_json
from incremental_transform_contract import (
    CHECKPOINT_VERSION_V1,
    CHECKPOINT_VERSION_V2,
    TransformDescriptor,
    build_transform_descriptor,
    compute_legacy_v1_transform_fingerprint,
    descriptor_to_checkpoint_fields,
    prepared_cache_key,
    validate_descriptor_digest,
)

MIGRATION_RECEIPT_VERSION = 1
STAGED_PREPARED_DIRNAME = "prepared_staged"

MIGRATION_PUBLISH_FAULT_POINTS = (
    "before_staged_prepare",
    "before_staged_artifact_write",
    "after_staged_artifact_write",
    "before_receipt_publish",
    "after_receipt_publish",
    "before_checkpoint_publish",
    "after_checkpoint_publish",
)


class MigrationError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class MigrationPlan:  # pylint: disable=too-many-instance-attributes
    state_dir: Path
    source_path: str
    source_identity: str
    chunk_size: int
    overlap: int
    min_confidence: float
    models: dict[str, Any]
    embed_dimension: int
    adapter_format: str
    adapter_contract_version: str
    legacy_producer_implementation_revision: str
    converter_revision: str = "incremental_checkpoint_migration-v1"


@dataclass(frozen=True)
class MigrationPublishContext:
    plan: MigrationPlan
    cfg: dict
    path_key: str
    coordinator_implementation_revision: str
    dry_run_report: dict[str, Any] | None = None


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def require_hermetic_migration_context() -> None:
    if not os.environ.get("CONVMEM_INCREMENTAL_ROOT"):
        raise MigrationError("migration_requires_hermetic_root")


def assert_quiescent_for_migration(
    *,
    checkpoint_path: Path,
    transaction_path: Path,
    rollback_path: Path,
) -> None:
    """C4: refuse when any journal or rollback authority is present."""
    if transaction_path.is_file():
        raise MigrationError("migration_blocked_pending_transaction")
    if rollback_path.is_file():
        raise MigrationError("migration_blocked_pending_rollback")
    checkpoint = _read_json(checkpoint_path)
    if checkpoint is None:
        raise MigrationError("migration_checkpoint_missing")
    if int(checkpoint.get("version") or 0) != CHECKPOINT_VERSION_V1:
        raise MigrationError("migration_checkpoint_not_v1")


def _publish_guards_from_checkpoint(checkpoint: dict[str, Any], checkpoint_bytes: bytes) -> dict[str, Any]:
    return {
        "checkpoint_digest": _sha(checkpoint_bytes),
        "source_identity": str(checkpoint.get("source_identity") or ""),
        "prefix_sha256": str(checkpoint.get("prefix_sha256") or ""),
        "complete_boundary": int(checkpoint.get("complete_boundary") or 0),
    }


def _assert_publish_preconditions(
    *,
    checkpoint_path: Path,
    transaction_path: Path,
    rollback_path: Path,
    guards: dict[str, Any],
) -> dict[str, Any]:
    assert_quiescent_for_migration(
        checkpoint_path=checkpoint_path,
        transaction_path=transaction_path,
        rollback_path=rollback_path,
    )
    current_bytes = checkpoint_path.read_bytes()
    if _sha(current_bytes) != guards["checkpoint_digest"]:
        raise MigrationError("migration_checkpoint_changed")
    checkpoint = _read_json(checkpoint_path)
    if checkpoint is None:
        raise MigrationError("migration_checkpoint_missing")
    if str(checkpoint.get("source_identity") or "") != guards["source_identity"]:
        raise MigrationError("migration_source_identity_changed")
    if str(checkpoint.get("prefix_sha256") or "") != guards["prefix_sha256"]:
        raise MigrationError("migration_prefix_hash_changed")
    if int(checkpoint.get("complete_boundary") or 0) != int(guards["complete_boundary"]):
        raise MigrationError("migration_boundary_changed")
    return checkpoint


def _v2_publication_if_complete(state_dir: Path, checkpoint_path: Path) -> dict[str, Any] | None:
    checkpoint = _read_json(checkpoint_path)
    if checkpoint is None:
        return None
    if int(checkpoint.get("version") or 0) != CHECKPOINT_VERSION_V2:
        return None
    receipt_digest = str(checkpoint.get("migration_receipt_digest") or "")
    if len(receipt_digest) != 64:
        raise MigrationError("migration_checkpoint_incomplete_v2")
    receipt_path = state_dir / f"migration_receipt_{receipt_digest}.json"
    if not receipt_path.is_file():
        raise MigrationError("migration_checkpoint_incomplete_v2")
    staged_root = state_dir / str(checkpoint.get("prepared_namespace") or "")
    if not staged_root.is_dir():
        raise MigrationError("migration_checkpoint_incomplete_v2")
    return checkpoint


@dataclass
class MigrationReceipt:
    receipt_digest: str
    body: dict[str, Any]


def _receipt_digest(body: dict[str, Any]) -> str:
    return _sha(_canonical_json(body))


def build_migration_receipt(
    *,
    source_path: str,
    source_identity: str,
    old_checkpoint_digest: str,
    old_transform_fingerprint: str,
    legacy_producer_implementation_revision: str,
    target_descriptor: TransformDescriptor,
    artifact_mappings: list[dict[str, str]],
    converter_revision: str,
) -> MigrationReceipt:
    body = {
        "version": MIGRATION_RECEIPT_VERSION,
        "source_path": source_path,
        "source_identity": source_identity,
        "old_checkpoint_digest": old_checkpoint_digest,
        "old_transform_fingerprint": old_transform_fingerprint,
        "legacy_producer_implementation_revision": legacy_producer_implementation_revision,
        "target_descriptor": target_descriptor.body,
        "target_transform_fingerprint": target_descriptor.digest,
        "artifact_mappings": artifact_mappings,
        "converter_revision": converter_revision,
    }
    return MigrationReceipt(receipt_digest=_receipt_digest(body), body=body)


def verify_legacy_preimage(checkpoint: dict[str, Any], plan: MigrationPlan) -> None:
    stored = str(checkpoint.get("transform_fingerprint") or "")
    recomputed = compute_legacy_v1_transform_fingerprint(
        chunk_size=plan.chunk_size,
        overlap=plan.overlap,
        min_confidence=plan.min_confidence,
        models=plan.models,
        embed_dimension=plan.embed_dimension,
        implementation_revision=plan.legacy_producer_implementation_revision,
        adapter_format=plan.adapter_format,
        adapter_contract_version=plan.adapter_contract_version,
    )
    if stored != recomputed:
        raise MigrationError("migration_compatibility_unproven", "legacy preimage mismatch")


def _target_descriptor_for_plan(plan: MigrationPlan) -> TransformDescriptor:
    return build_transform_descriptor(
        chunk_size=plan.chunk_size,
        overlap=plan.overlap,
        min_confidence=plan.min_confidence,
        models=plan.models,
        embed_dimension=plan.embed_dimension,
        adapter_format=plan.adapter_format,
        adapter_contract_version=plan.adapter_contract_version,
    )


def _migration_paths(plan: MigrationPlan) -> tuple[Path, Path, Path]:
    state_dir = plan.state_dir
    return (
        state_dir / "checkpoint.json",
        state_dir / "transaction.json",
        state_dir / "rollback.json",
    )


def dry_run_migration(plan: MigrationPlan) -> dict[str, Any]:
    require_hermetic_migration_context()
    checkpoint_path, transaction_path, rollback_path = _migration_paths(plan)
    assert_quiescent_for_migration(
        checkpoint_path=checkpoint_path,
        transaction_path=transaction_path,
        rollback_path=rollback_path,
    )
    checkpoint_bytes = checkpoint_path.read_bytes()
    checkpoint = _read_json(checkpoint_path)
    if checkpoint is None:
        raise MigrationError("migration_checkpoint_missing")
    verify_legacy_preimage(checkpoint, plan)
    target = _target_descriptor_for_plan(plan)
    old_fp = str(checkpoint.get("transform_fingerprint") or "")
    prepared_dir = plan.state_dir / "prepared"
    mappings: list[dict[str, str]] = []
    if prepared_dir.is_dir():
        for path in sorted(prepared_dir.glob("*.json")):
            payload = _read_json(path)
            if payload is None:
                raise MigrationError("migration_prepared_corrupt", path.name)
            chunk_start = int(payload["chunk_start"])
            input_digest = str(payload["input_digest"])
            new_key = prepared_cache_key(
                source_id=plan.source_identity,
                input_digest=input_digest,
                transform_fingerprint=target.digest,
                chunk_start=chunk_start,
            )
            mappings.append(
                {
                    "old_cache_key": str(payload.get("cache_key") or path.stem),
                    "new_cache_key": new_key,
                    "old_artifact_digest": str(payload.get("digest") or ""),
                }
            )
    receipt = build_migration_receipt(
        source_path=plan.source_path,
        source_identity=plan.source_identity,
        old_checkpoint_digest=_sha(checkpoint_bytes),
        old_transform_fingerprint=old_fp,
        legacy_producer_implementation_revision=plan.legacy_producer_implementation_revision,
        target_descriptor=target,
        artifact_mappings=mappings,
        converter_revision=plan.converter_revision,
    )
    publish_guards = _publish_guards_from_checkpoint(checkpoint, checkpoint_bytes)
    return {
        "dry_run": True,
        "receipt_digest": receipt.receipt_digest,
        "receipt": receipt.body,
        "artifact_count": len(mappings),
        "target_transform_fingerprint": target.digest,
        "publish_guards": publish_guards,
    }


def _write_staged_prepared_artifacts(
    plan: MigrationPlan,
    *,
    receipt_body: dict[str, Any],
    receipt_digest: str,
    target: TransformDescriptor,
    fault: Callable[[str], None],
) -> Path:
    state_dir = plan.state_dir
    staged_root = state_dir / STAGED_PREPARED_DIRNAME / receipt_digest
    fault("before_staged_prepare")
    if staged_root.exists():
        shutil.rmtree(staged_root)
    staged_root.mkdir(parents=True, exist_ok=True)
    os.chmod(staged_root, 0o700)
    prepared_dir = state_dir / "prepared"
    for mapping in receipt_body["artifact_mappings"]:
        old_key = mapping["old_cache_key"]
        old_path = prepared_dir / f"{old_key}.json"
        payload = _read_json(old_path)
        if payload is None:
            raise MigrationError("migration_prepared_missing", old_key)
        new_key = mapping["new_cache_key"]
        migrated = dict(payload)
        migrated["cache_key"] = new_key
        migrated["transform_fingerprint"] = target.digest
        migrated["migration_receipt_digest"] = receipt_digest
        migrated["migrated_from_artifact_digest"] = mapping["old_artifact_digest"]
        body = {name: value for name, value in migrated.items() if name != "digest"}
        migrated["digest"] = _sha(_canonical_json(body))
        fault("before_staged_artifact_write")
        _atomic_json(staged_root / f"{new_key}.json", migrated)
        fault("after_staged_artifact_write")
    return staged_root


def publish_migration(
    ctx: MigrationPublishContext,
    *,
    fault: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    require_hermetic_migration_context()
    fault = fault or (lambda _point: None)
    from purge_locks import index_write_flock, source_flock

    plan = ctx.plan
    checkpoint_path, transaction_path, rollback_path = _migration_paths(plan)
    state_dir = plan.state_dir

    with source_flock(ctx.cfg, ctx.path_key):
        with index_write_flock(ctx.cfg):
            complete = _v2_publication_if_complete(state_dir, checkpoint_path)
            if complete is not None:
                receipt_digest = str(complete.get("migration_receipt_digest") or "")
                if ctx.dry_run_report and ctx.dry_run_report.get("receipt_digest") != receipt_digest:
                    raise MigrationError("migration_already_published_different_receipt")
                return {
                    "published": True,
                    "idempotent": True,
                    "receipt_digest": receipt_digest,
                    "prepared_namespace": str(complete.get("prepared_namespace") or ""),
                    "checkpoint_version": CHECKPOINT_VERSION_V2,
                }

            report = ctx.dry_run_report or dry_run_migration(plan)
            receipt_body = report["receipt"]
            receipt_digest = report["receipt_digest"]
            guards = report["publish_guards"]
            target = _target_descriptor_for_plan(plan)
            _write_staged_prepared_artifacts(
                plan,
                receipt_body=receipt_body,
                receipt_digest=receipt_digest,
                target=target,
                fault=fault,
            )
            receipt_path = state_dir / f"migration_receipt_{receipt_digest}.json"
            fault("before_receipt_publish")
            _atomic_json(receipt_path, receipt_body)
            fault("after_receipt_publish")
            checkpoint = _assert_publish_preconditions(
                checkpoint_path=checkpoint_path,
                transaction_path=transaction_path,
                rollback_path=rollback_path,
                guards=guards,
            )
            new_checkpoint = dict(checkpoint)
            new_checkpoint.update(descriptor_to_checkpoint_fields(target))
            new_checkpoint["version"] = CHECKPOINT_VERSION_V2
            new_checkpoint["prepared_namespace"] = f"{STAGED_PREPARED_DIRNAME}/{receipt_digest}"
            new_checkpoint["migration_receipt_digest"] = receipt_digest
            new_checkpoint["coordinator_implementation_revision"] = ctx.coordinator_implementation_revision
            new_checkpoint["generation_scheme"] = "legacy-v1-generation-preserved"
            validate_descriptor_digest(
                new_checkpoint["transform_descriptor"],
                str(new_checkpoint["transform_fingerprint"]),
            )
            fault("before_checkpoint_publish")
            _atomic_json(checkpoint_path, new_checkpoint)
            fault("after_checkpoint_publish")
            return {
                "published": True,
                "receipt_digest": receipt_digest,
                "prepared_namespace": new_checkpoint["prepared_namespace"],
                "checkpoint_version": CHECKPOINT_VERSION_V2,
            }
