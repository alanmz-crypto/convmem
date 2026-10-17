"""Hermetic-only checkpoint/cache migration to transform contract v2."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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


class MigrationError(RuntimeError):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _read_json(path: Path) -> dict | None:
    if not path.is_file() or path.is_symlink():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def require_hermetic_migration_context() -> None:
    if not os.environ.get("CONVMEM_INCREMENTAL_ROOT"):
        raise MigrationError("migration_requires_hermetic_root")


def assert_quiescent_for_migration(
    state_dir: Path,
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


def verify_legacy_preimage(
    *,
    checkpoint: dict[str, Any],
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    models: dict[str, Any],
    embed_dimension: int,
    adapter_format: str,
    adapter_contract_version: str,
    legacy_producer_implementation_revision: str,
) -> None:
    stored = str(checkpoint.get("transform_fingerprint") or "")
    recomputed = compute_legacy_v1_transform_fingerprint(
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=min_confidence,
        models=models,
        embed_dimension=embed_dimension,
        implementation_revision=legacy_producer_implementation_revision,
        adapter_format=adapter_format,
        adapter_contract_version=adapter_contract_version,
    )
    if stored != recomputed:
        raise MigrationError("migration_compatibility_unproven", "legacy preimage mismatch")


def dry_run_migration(
    *,
    state_dir: Path,
    source_path: str,
    source_identity: str,
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    models: dict[str, Any],
    embed_dimension: int,
    adapter_format: str,
    adapter_contract_version: str,
    legacy_producer_implementation_revision: str,
    converter_revision: str = "incremental_checkpoint_migration-v1",
) -> dict[str, Any]:
    require_hermetic_migration_context()
    checkpoint_path = state_dir / "checkpoint.json"
    transaction_path = state_dir / "transaction.json"
    rollback_path = state_dir / "rollback.json"
    assert_quiescent_for_migration(
        state_dir,
        checkpoint_path=checkpoint_path,
        transaction_path=transaction_path,
        rollback_path=rollback_path,
    )
    checkpoint = _read_json(checkpoint_path)
    if checkpoint is None:
        raise MigrationError("migration_checkpoint_missing")
    verify_legacy_preimage(
        checkpoint=checkpoint,
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=min_confidence,
        models=models,
        embed_dimension=embed_dimension,
        adapter_format=adapter_format,
        adapter_contract_version=adapter_contract_version,
        legacy_producer_implementation_revision=legacy_producer_implementation_revision,
    )
    target = build_transform_descriptor(
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=min_confidence,
        models=models,
        embed_dimension=embed_dimension,
        adapter_format=adapter_format,
        adapter_contract_version=adapter_contract_version,
    )
    old_fp = str(checkpoint.get("transform_fingerprint") or "")
    prepared_dir = state_dir / "prepared"
    mappings: list[dict[str, str]] = []
    if prepared_dir.is_dir():
        for path in sorted(prepared_dir.glob("*.json")):
            payload = _read_json(path)
            if payload is None:
                raise MigrationError("migration_prepared_corrupt", path.name)
            chunk_start = int(payload["chunk_start"])
            input_digest = str(payload["input_digest"])
            new_key = prepared_cache_key(
                source_id=source_identity,
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
        source_path=source_path,
        source_identity=source_identity,
        old_checkpoint_digest=_sha(checkpoint_path.read_bytes()),
        old_transform_fingerprint=old_fp,
        legacy_producer_implementation_revision=legacy_producer_implementation_revision,
        target_descriptor=target,
        artifact_mappings=mappings,
        converter_revision=converter_revision,
    )
    return {
        "dry_run": True,
        "receipt_digest": receipt.receipt_digest,
        "receipt": receipt.body,
        "artifact_count": len(mappings),
        "target_transform_fingerprint": target.digest,
    }


def publish_migration(
    *,
    state_dir: Path,
    source_path: str,
    source_identity: str,
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    models: dict[str, Any],
    embed_dimension: int,
    adapter_format: str,
    adapter_contract_version: str,
    legacy_producer_implementation_revision: str,
    coordinator_implementation_revision: str,
    converter_revision: str = "incremental_checkpoint_migration-v1",
    fault: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    require_hermetic_migration_context()
    fault = fault or (lambda _point: None)
    report = dry_run_migration(
        state_dir=state_dir,
        source_path=source_path,
        source_identity=source_identity,
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=min_confidence,
        models=models,
        embed_dimension=embed_dimension,
        adapter_format=adapter_format,
        adapter_contract_version=adapter_contract_version,
        legacy_producer_implementation_revision=legacy_producer_implementation_revision,
        converter_revision=converter_revision,
    )
    receipt_body = report["receipt"]
    receipt_digest = report["receipt_digest"]
    checkpoint_path = state_dir / "checkpoint.json"
    checkpoint = _read_json(checkpoint_path)
    if checkpoint is None:
        raise MigrationError("migration_checkpoint_missing")
    target = build_transform_descriptor(
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=min_confidence,
        models=models,
        embed_dimension=embed_dimension,
        adapter_format=adapter_format,
        adapter_contract_version=adapter_contract_version,
    )
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
    receipt_path = state_dir / f"migration_receipt_{receipt_digest}.json"
    fault("before_receipt_publish")
    _atomic_json(receipt_path, receipt_body)
    fault("after_receipt_publish")
    new_checkpoint = dict(checkpoint)
    new_checkpoint.update(descriptor_to_checkpoint_fields(target))
    new_checkpoint["version"] = CHECKPOINT_VERSION_V2
    new_checkpoint["prepared_namespace"] = f"{STAGED_PREPARED_DIRNAME}/{receipt_digest}"
    new_checkpoint["migration_receipt_digest"] = receipt_digest
    new_checkpoint["coordinator_implementation_revision"] = coordinator_implementation_revision
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
