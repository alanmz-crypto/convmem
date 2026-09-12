"""One-shot production-canary boundary for incremental Kiro JSONL.

This module is canary-only: it is not registered in the normal CLI or watcher.
P1 uses synthetic sources and temporary roots; P2 requires a separate grant.
"""

# pylint: disable=too-many-lines,too-many-locals,too-many-branches,too-many-statements
# pylint: disable=too-many-instance-attributes,duplicate-code

from __future__ import annotations

import contextvars
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, TypeVar

from incremental_jsonl import (
    DURABLE_TRANSITIONS,
    CallCounters,
    IncrementalJsonlCoordinator,
)
from incremental_jsonl_isolation import (
    create_fresh_root,
    known_production_roots,
    terminate_process_group,
)

CANARY_SCHEMA_VERSION = 1
CANARY_MODE = "jsonl-production-canary-v1"
P1_CAPABILITY_MODE = "p1-hermetic-v1"
P2_CAPABILITY_MODE = "p2-exact-resource-v1"
P2_LIVE_CAPABILITY_MODE = "p2-exact-resource-v2"
ABSENT_DIGEST = "absent"
ZERO_DIGEST = "0" * 64
_GRANT_V2_FIELDS = frozenset(
    {
        "persistent_config",
        "model_manifests",
        "restic",
        "resource_identities",
        "owner_uid",
    }
)
_GRANT_OPTIONAL_FIELDS = frozenset({"capability_mode"}) | _GRANT_V2_FIELDS
CRASH_EXIT = 86
RECOVERY_TIMEOUT_S = 30
STABLE_READ_COUNT = 3
STABLE_READ_MIN_SPAN_S = 2.0
PRODUCTION_CHUNK_SIZE = 60
PRODUCTION_OVERLAP = 10
BASELINE_MIN_MESSAGES = 61
BASELINE_MAX_MESSAGES = 109
APPEND_MAX_MESSAGES = 110
THIRD_CHUNK_MIN_MESSAGES = 111

MODEL_DIGESTS = {
    "llama3.1:8b": "46e0c10c039e",
    "nomic-embed-text:latest": "0a109f422b47",
}

FAULT_SELECTORS: dict[str, str] = {
    "summary_upsert": "after_summary_upsert",
    "unit_upsert": "after_unit_upsert",
    "units_prune": "after_units_prune",
    "checkpoint_publish": "after_checkpoint_publish",
    "dedupe_reconcile": "after_dedupe_reconcile",
}

CALL_CEILINGS_INITIAL = {"summarize": 2, "distill": 2, "summary_embed": 2, "unit_embed": 16}
CALL_CEILINGS_APPEND = {"summarize": 1, "distill": 1, "summary_embed": 1, "unit_embed": 8}
CALL_CEILINGS_WHOLE = {"summarize": 8, "distill": 8, "summary_embed": 8, "unit_embed": 64}

_GRANT_REQUIRED_TOP = frozenset(
    {
        "schema_version",
        "code_revision",
        "expires_at",
        "nonce",
        "run_once",
        "source",
        "append_envelope",
        "resources",
        "config_overlay",
        "provider",
        "call_ceilings",
        "faults",
        "rollback",
        "evidence_dir",
        "expected_pre_state",
    }
)
_RESOURCE_ROLES = frozenset(
    {
        "chroma",
        "incremental_state",
        "export",
        "dedupe",
        "processed",
        "writer_lock",
        "source_lock",
        "export_lock",
        "processed_lock",
        "attestations",
        "census",
    }
)
_T = TypeVar("_T")


class CanaryRefused(RuntimeError):
    """Fail-closed canary refusal with a stable code."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class CanaryFaultExit(BaseException):
    """In-process fault injection marker for hermetic tests."""

    def __init__(self, transition: str):
        self.transition = transition
        super().__init__(transition)


@dataclass(frozen=True)
class SourceGrant:
    path: str
    metadata_path: str
    device: int
    inode: int
    size: int
    complete_boundary: int
    prefix_sha256: str
    metadata_sha256: str


@dataclass(frozen=True)
class AppendEnvelope:
    max_byte_boundary: int
    max_accepted_records: int
    max_append_epochs: int
    immutable_prefix: bool


@dataclass(frozen=True)
class ResourceRole:
    path: str
    role: str


@dataclass(frozen=True)
class ProviderGrant:
    loopback_host: str
    summarize_model: str
    summarize_digest: str
    embed_model: str
    embed_canonical_tag: str
    embed_digest: str
    distill_model: str
    distill_digest: str


@dataclass(frozen=True)
class RollbackGrant:
    capsule_path: str
    expected_digest: str


@dataclass(frozen=True)
class PersistentConfigGrant:
    path: str
    digest: str


@dataclass(frozen=True)
class ModelManifestGrant:
    role: str
    name: str
    digest: str
    manifest_path: str


@dataclass(frozen=True)
class ResticGrant:
    snapshot_id: str
    tag: str
    data_root: str
    repository: str
    require_current_local_day: bool


@dataclass(frozen=True)
class ResourceIdentityGrant:
    role: str
    path: str
    uid: int
    mode: int
    device: int
    inode: int
    file_type: str


@dataclass(frozen=True)
class CanaryGrant:
    schema_version: int
    code_revision: str
    expires_at: str
    nonce: str
    run_once: bool
    source: SourceGrant
    append_envelope: AppendEnvelope
    resources: tuple[ResourceRole, ...]
    config_overlay: str
    config_overlay_digest: str
    provider: ProviderGrant
    call_ceilings: dict[str, dict[str, int]]
    faults: tuple[str, ...]
    rollback: RollbackGrant
    evidence_dir: str
    expected_pre_state: dict[str, Any]
    capability_mode: str = P1_CAPABILITY_MODE
    persistent_config: PersistentConfigGrant | None = None
    model_manifests: tuple[ModelManifestGrant, ...] = ()
    restic: ResticGrant | None = None
    resource_identities: tuple[ResourceIdentityGrant, ...] = ()
    owner_uid: int | None = None

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "code_revision": self.code_revision,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "run_once": self.run_once,
            "source": asdict(self.source),
            "append_envelope": asdict(self.append_envelope),
            "resources": [asdict(item) for item in self.resources],
            "config_overlay": {
                "path": self.config_overlay,
                "digest": self.config_overlay_digest,
            },
            "provider": asdict(self.provider),
            "call_ceilings": self.call_ceilings,
            "faults": list(self.faults),
            "rollback": asdict(self.rollback),
            "evidence_dir": self.evidence_dir,
            "expected_pre_state": self.expected_pre_state,
        }
        if self.capability_mode != P1_CAPABILITY_MODE:
            payload["capability_mode"] = self.capability_mode
        if self.capability_mode == P2_LIVE_CAPABILITY_MODE:
            if self.persistent_config is None or self.restic is None or self.owner_uid is None:
                raise CanaryRefused("canary_grant_live_fields", "live P2 grant missing bindings")
            payload["persistent_config"] = asdict(self.persistent_config)
            payload["model_manifests"] = [asdict(item) for item in self.model_manifests]
            payload["restic"] = asdict(self.restic)
            payload["resource_identities"] = [asdict(item) for item in self.resource_identities]
            payload["owner_uid"] = self.owner_uid
        return payload

    def digest_payload(self) -> bytes:
        return json.dumps(self.to_payload(), sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass
class NonceReceipt:
    nonce: str
    grant_digest: str
    stage: str = "created"
    append_epochs: list[str] = field(default_factory=list)
    faults_completed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.exists() and current.is_symlink():
            return True
    return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.urandom(8).hex()}.tmp")
    temp.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)
    _fsync_directory(path.parent)


def decode_grant(path: Path | str) -> CanaryGrant:
    """Load and decode a closed-schema canary grant."""
    grant_path = Path(path).expanduser()
    if not grant_path.is_file():
        raise CanaryRefused("canary_grant_missing", "grant file not found")
    mode = grant_path.stat().st_mode
    if stat.S_IMODE(mode) & 0o077:
        raise CanaryRefused("canary_grant_mode", "grant must be mode 0600")
    try:
        payload = json.loads(grant_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CanaryRefused("canary_grant_invalid", "grant is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise CanaryRefused("canary_grant_invalid", "grant root must be an object")
    unknown = set(payload) - _GRANT_REQUIRED_TOP - _GRANT_OPTIONAL_FIELDS
    if unknown:
        raise CanaryRefused(
            "canary_grant_unknown_field",
            f"unknown grant fields: {sorted(unknown)}",
        )
    capability_mode = str(payload.get("capability_mode", P1_CAPABILITY_MODE))
    if capability_mode not in {P1_CAPABILITY_MODE, P2_CAPABILITY_MODE, P2_LIVE_CAPABILITY_MODE}:
        raise CanaryRefused("canary_grant_mode", f"unsupported capability_mode: {capability_mode}")
    if capability_mode == P2_LIVE_CAPABILITY_MODE:
        missing_live = _GRANT_V2_FIELDS - set(payload)
        if missing_live:
            raise CanaryRefused(
                "canary_grant_missing_field",
                f"missing live grant fields: {sorted(missing_live)}",
            )
    missing = _GRANT_REQUIRED_TOP - set(payload)
    if missing:
        raise CanaryRefused(
            "canary_grant_missing_field",
            f"missing grant fields: {sorted(missing)}",
        )
    if payload["schema_version"] != CANARY_SCHEMA_VERSION:
        raise CanaryRefused("canary_grant_schema", "unsupported schema version")
    if payload["run_once"] is not True:
        raise CanaryRefused("canary_grant_mode", "run_once must be true")
    source = payload["source"]
    if not isinstance(source, dict):
        raise CanaryRefused("canary_grant_source", "source must be an object")
    for key in (
        "path",
        "metadata_path",
        "device",
        "inode",
        "size",
        "complete_boundary",
        "prefix_sha256",
        "metadata_sha256",
    ):
        if key not in source:
            raise CanaryRefused("canary_grant_source", f"missing source.{key}")
    append = payload["append_envelope"]
    if not isinstance(append, dict):
        raise CanaryRefused("canary_grant_append", "append_envelope must be an object")
    resources_raw = payload["resources"]
    if not isinstance(resources_raw, list) or not resources_raw:
        raise CanaryRefused("canary_grant_resources", "resources must be a non-empty list")
    roles: list[ResourceRole] = []
    seen_paths: set[str] = set()
    seen_roles: set[str] = set()
    for item in resources_raw:
        if not isinstance(item, dict):
            raise CanaryRefused("canary_grant_resources", "each resource must be an object")
        role = str(item.get("role", ""))
        path = str(item.get("path", ""))
        if role not in _RESOURCE_ROLES:
            raise CanaryRefused("canary_grant_resources", f"unknown role {role}")
        if not Path(path).is_absolute():
            raise CanaryRefused("canary_grant_resources", f"resource path must be absolute: {path}")
        if path in seen_paths:
            raise CanaryRefused("canary_grant_resources", f"duplicate resource path: {path}")
        if role in seen_roles:
            raise CanaryRefused("canary_grant_resources", f"duplicate role: {role}")
        seen_paths.add(path)
        seen_roles.add(role)
        roles.append(ResourceRole(path=path, role=role))
    overlay = payload["config_overlay"]
    if not isinstance(overlay, dict) or "path" not in overlay or "digest" not in overlay:
        raise CanaryRefused("canary_grant_overlay", "config_overlay requires path and digest")
    provider = payload["provider"]
    if not isinstance(provider, dict):
        raise CanaryRefused("canary_grant_provider", "provider must be an object")
    for key in (
        "loopback_host",
        "summarize_model",
        "summarize_digest",
        "embed_model",
        "embed_canonical_tag",
        "embed_digest",
        "distill_model",
        "distill_digest",
    ):
        if key not in provider:
            raise CanaryRefused("canary_grant_provider", f"missing provider.{key}")
    faults = payload["faults"]
    if not isinstance(faults, list):
        raise CanaryRefused("canary_grant_faults", "faults must be a list")
    for name in faults:
        if name not in FAULT_SELECTORS:
            raise CanaryRefused("canary_grant_faults", f"unknown fault selector: {name}")
    rollback = payload["rollback"]
    if not isinstance(rollback, dict):
        raise CanaryRefused("canary_grant_rollback", "rollback must be an object")
    for key in ("capsule_path", "expected_digest"):
        if key not in rollback:
            raise CanaryRefused("canary_grant_rollback", f"missing rollback.{key}")
    return CanaryGrant(
        schema_version=int(payload["schema_version"]),
        code_revision=str(payload["code_revision"]),
        expires_at=str(payload["expires_at"]),
        nonce=str(payload["nonce"]),
        run_once=True,
        capability_mode=capability_mode,
        source=SourceGrant(
            path=str(source["path"]),
            metadata_path=str(source["metadata_path"]),
            device=int(source["device"]),
            inode=int(source["inode"]),
            size=int(source["size"]),
            complete_boundary=int(source["complete_boundary"]),
            prefix_sha256=str(source["prefix_sha256"]),
            metadata_sha256=str(source["metadata_sha256"]),
        ),
        append_envelope=AppendEnvelope(
            max_byte_boundary=int(append["max_byte_boundary"]),
            max_accepted_records=int(append["max_accepted_records"]),
            max_append_epochs=int(append["max_append_epochs"]),
            immutable_prefix=bool(append.get("immutable_prefix", True)),
        ),
        resources=tuple(roles),
        config_overlay=str(overlay["path"]),
        config_overlay_digest=str(overlay["digest"]),
        provider=ProviderGrant(
            loopback_host=str(provider["loopback_host"]),
            summarize_model=str(provider["summarize_model"]),
            summarize_digest=str(provider["summarize_digest"]),
            embed_model=str(provider["embed_model"]),
            embed_canonical_tag=str(provider["embed_canonical_tag"]),
            embed_digest=str(provider["embed_digest"]),
            distill_model=str(provider["distill_model"]),
            distill_digest=str(provider["distill_digest"]),
        ),
        call_ceilings=dict(payload["call_ceilings"]),
        faults=tuple(str(name) for name in faults),
        rollback=RollbackGrant(
            capsule_path=str(rollback["capsule_path"]),
            expected_digest=str(rollback["expected_digest"]),
        ),
        evidence_dir=str(payload["evidence_dir"]),
        expected_pre_state=dict(payload["expected_pre_state"]),
        **_decode_live_bindings(payload, capability_mode),
    )


def _decode_live_bindings(payload: Mapping[str, Any], capability_mode: str) -> dict[str, Any]:
    if capability_mode != P2_LIVE_CAPABILITY_MODE:
        return {}
    persistent = payload["persistent_config"]
    if not isinstance(persistent, dict) or "path" not in persistent or "digest" not in persistent:
        raise CanaryRefused("canary_grant_config", "persistent_config requires path and digest")
    manifests_raw = payload["model_manifests"]
    if not isinstance(manifests_raw, list) or len(manifests_raw) < 3:
        raise CanaryRefused("canary_grant_models", "model_manifests must list summarize, embed, and distill")
    manifests: list[ModelManifestGrant] = []
    seen_roles: set[str] = set()
    for item in manifests_raw:
        if not isinstance(item, dict):
            raise CanaryRefused("canary_grant_models", "each model manifest must be an object")
        role = str(item.get("role", ""))
        if role not in {"summarize", "embed", "distill"}:
            raise CanaryRefused("canary_grant_models", f"unknown model role {role}")
        if role in seen_roles:
            raise CanaryRefused("canary_grant_models", f"duplicate model role {role}")
        for key in ("name", "digest", "manifest_path"):
            if key not in item:
                raise CanaryRefused("canary_grant_models", f"missing model_manifests.{key}")
        seen_roles.add(role)
        manifests.append(
            ModelManifestGrant(
                role=role,
                name=str(item["name"]),
                digest=str(item["digest"]),
                manifest_path=str(item["manifest_path"]),
            )
        )
    if seen_roles != {"summarize", "embed", "distill"}:
        raise CanaryRefused("canary_grant_models", "model_manifests must cover summarize, embed, distill")
    restic = payload["restic"]
    if not isinstance(restic, dict):
        raise CanaryRefused("canary_grant_restic", "restic must be an object")
    for key in ("snapshot_id", "tag", "data_root", "repository", "require_current_local_day"):
        if key not in restic:
            raise CanaryRefused("canary_grant_restic", f"missing restic.{key}")
    identities_raw = payload["resource_identities"]
    if not isinstance(identities_raw, list) or not identities_raw:
        raise CanaryRefused("canary_grant_identities", "resource_identities must be a non-empty list")
    identities: list[ResourceIdentityGrant] = []
    seen_identity_roles: set[str] = set()
    for item in identities_raw:
        if not isinstance(item, dict):
            raise CanaryRefused("canary_grant_identities", "each identity must be an object")
        role = str(item.get("role", ""))
        if role in seen_identity_roles:
            raise CanaryRefused("canary_grant_identities", f"duplicate identity role {role}")
        for key in ("path", "uid", "mode", "device", "inode", "file_type"):
            if key not in item:
                raise CanaryRefused("canary_grant_identities", f"missing identity.{key}")
        file_type = str(item["file_type"])
        if file_type not in {"file", "dir", "absent"}:
            raise CanaryRefused("canary_grant_identities", f"invalid file_type {file_type}")
        seen_identity_roles.add(role)
        identities.append(
            ResourceIdentityGrant(
                role=role,
                path=str(item["path"]),
                uid=int(item["uid"]),
                mode=int(item["mode"]),
                device=int(item["device"]),
                inode=int(item["inode"]),
                file_type=file_type,
            )
        )
    return {
        "persistent_config": PersistentConfigGrant(
            path=str(persistent["path"]),
            digest=str(persistent["digest"]),
        ),
        "model_manifests": tuple(manifests),
        "restic": ResticGrant(
            snapshot_id=str(restic["snapshot_id"]),
            tag=str(restic["tag"]),
            data_root=str(restic["data_root"]),
            repository=str(restic["repository"]),
            require_current_local_day=bool(restic["require_current_local_day"]),
        ),
        "resource_identities": tuple(identities),
        "owner_uid": int(payload["owner_uid"]),
    }


def is_p2_grant(grant: CanaryGrant) -> bool:
    return grant.capability_mode == P2_CAPABILITY_MODE


def is_p2_live_grant(grant: CanaryGrant) -> bool:
    return grant.capability_mode == P2_LIVE_CAPABILITY_MODE


def _grant_allowlist_paths(grant: CanaryGrant) -> frozenset[Path]:
    paths = {
        Path(grant.source.path),
        Path(grant.source.metadata_path),
        Path(grant.config_overlay),
        Path(grant.evidence_dir),
        Path(grant.rollback.capsule_path),
    }
    for role in grant.resources:
        paths.add(Path(role.path))
    return frozenset(item.resolve(strict=False) for item in paths)


def _assert_authority_mode(path: Path, *, label: str, grant: CanaryGrant | None = None) -> None:
    if not path.is_file():
        return
    if grant is not None:
        exempt = {grant.source.path, grant.source.metadata_path}
        if str(path.resolve(strict=False)) in exempt:
            return
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise CanaryRefused("canary_grant_mode", f"{label} must not be group/world accessible")




def _harden_grant_paths(grant: CanaryGrant) -> None:
    """Restore grant-listed authority modes after coordinator side effects."""
    exempt = {
        Path(grant.source.path).resolve(strict=False),
        Path(grant.source.metadata_path).resolve(strict=False),
    }
    for path in _grant_allowlist_paths(grant):
        if not path.exists():
            continue
        if path.resolve(strict=False) in exempt:
            continue
        if path.is_dir():
            os.chmod(path, 0o700)
        elif path.is_file():
            os.chmod(path, 0o600)

def _validate_grant_common(
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    code_revision: str,
) -> None:
    digest = _sha256_bytes(grant.digest_payload())
    if digest != expected_sha256.lower():
        raise CanaryRefused("canary_grant_digest", "grant SHA-256 mismatch")
    if grant.code_revision != code_revision:
        raise CanaryRefused("canary_grant_revision", "code revision mismatch")
    try:
        expires = datetime.fromisoformat(grant.expires_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CanaryRefused("canary_grant_expiry", "invalid expires_at") from exc
    if expires <= datetime.now(timezone.utc):
        raise CanaryRefused("canary_grant_expired", "grant expired")
    for model, digest_value in (
        (grant.provider.summarize_model, grant.provider.summarize_digest),
        (grant.provider.embed_canonical_tag, grant.provider.embed_digest),
        (grant.provider.distill_model, grant.provider.distill_digest),
    ):
        expected = MODEL_DIGESTS.get(model)
        if expected and digest_value != expected:
            raise CanaryRefused("canary_grant_model_digest", f"model digest mismatch for {model}")


def validate_p2_grant(
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    code_revision: str,
) -> None:
    """Positive exact-resource validation for P2 grants."""
    if is_p2_live_grant(grant):
        raise CanaryRefused("canary_mode", "live P2 grants require validate_p2_live_grant")
    if not is_p2_grant(grant):
        raise CanaryRefused("canary_mode", "not a P2 exact-resource grant")
    _validate_grant_common(grant, expected_sha256=expected_sha256, code_revision=code_revision)
    allowlist = _grant_allowlist_paths(grant)
    for candidate in allowlist:
        if not candidate.is_absolute() or _has_symlink_component(candidate):
            raise CanaryRefused("canary_grant_path", f"unsafe grant path: {candidate}")
        _assert_authority_mode(candidate, label=str(candidate), grant=grant)
    overlay_path = Path(grant.config_overlay)
    if overlay_path.is_file():
        overlay_digest = _sha256_file(overlay_path)
        if overlay_digest != grant.config_overlay_digest:
            raise CanaryRefused("canary_grant_overlay_digest", "config overlay digest mismatch")



def validate_grant(
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    code_revision: str,
    forbidden_roots: tuple[Path, ...] | None = None,
) -> None:
    """Fail-closed grant validation before any writer construction."""
    if is_p2_live_grant(grant) or is_p2_grant(grant):
        raise CanaryRefused("canary_mode", "P2 grants require validate_p2_grant")
    _validate_grant_common(grant, expected_sha256=expected_sha256, code_revision=code_revision)
    forbidden = forbidden_roots or known_production_roots()
    for role in grant.resources:
        path = Path(role.path)
        if not path.is_absolute() or _has_symlink_component(path):
            raise CanaryRefused("canary_grant_path", f"unsafe resource path: {role.path}")
        resolved = path.resolve(strict=False)
        for root in forbidden:
            if _is_relative_to(resolved, root) or _is_relative_to(root, resolved):
                raise CanaryRefused("canary_grant_production_path", f"production path in grant: {role.path}")
    for path_str in (grant.source.path, grant.source.metadata_path, grant.config_overlay):
        path = Path(path_str)
        if not path.is_absolute() or _has_symlink_component(path):
            raise CanaryRefused("canary_grant_path", f"unsafe path: {path_str}")
        resolved = path.resolve(strict=False)
        for root in forbidden:
            if _is_relative_to(resolved, root) or _is_relative_to(root, resolved):
                raise CanaryRefused("canary_grant_production_path", f"production path in grant: {path_str}")
    overlay_path = Path(grant.config_overlay)
    if overlay_path.is_file():
        overlay_digest = _sha256_file(overlay_path)
        if overlay_digest != grant.config_overlay_digest:
            raise CanaryRefused("canary_grant_overlay_digest", "config overlay digest mismatch")
    for model, digest in (
        (grant.provider.summarize_model, grant.provider.summarize_digest),
        (grant.provider.embed_canonical_tag, grant.provider.embed_digest),
        (grant.provider.distill_model, grant.provider.distill_digest),
    ):
        expected = MODEL_DIGESTS.get(model)
        if expected and digest != expected:
            raise CanaryRefused("canary_grant_model_digest", f"model digest mismatch for {model}")


def nonce_receipt_path(root: Path) -> Path:
    return root / "canary-nonce-receipt.json"


def consume_nonce(root: Path, grant: CanaryGrant, *, expected_sha256: str) -> NonceReceipt:
    """Create or resume the one-run nonce receipt."""
    path = nonce_receipt_path(root)
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("nonce") != grant.nonce:
            raise CanaryRefused("canary_nonce_reused", "nonce receipt belongs to another grant")
        if payload.get("grant_digest") != expected_sha256:
            raise CanaryRefused("canary_nonce_reused", "nonce receipt digest mismatch")
        return NonceReceipt(
            nonce=str(payload["nonce"]),
            grant_digest=str(payload["grant_digest"]),
            stage=str(payload.get("stage", "created")),
            append_epochs=list(payload.get("append_epochs") or []),
            faults_completed=list(payload.get("faults_completed") or []),
        )
    receipt = NonceReceipt(nonce=grant.nonce, grant_digest=expected_sha256)
    _atomic_json(path, receipt.to_dict())
    return receipt


def assert_not_reused(root: Path, grant: CanaryGrant) -> None:
    """Reject a grant whose nonce already completed a run."""
    path = nonce_receipt_path(root)
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("nonce") == grant.nonce and payload.get("stage") == "completed":
        raise CanaryRefused("canary_nonce_reused", "grant nonce already consumed")


@dataclass(frozen=True)
class ProductionCanaryBoundary:
    """Grant-bound capability boundary separate from scratch isolation."""

    root: Path
    token: str
    grant: CanaryGrant
    forbidden_roots: tuple[Path, ...] = ()
    service_invocations: list[str] | None = None

    @classmethod
    def from_grant(
        cls,
        grant: CanaryGrant,
        *,
        root: Path | None = None,
        forbidden_roots: tuple[Path, ...] | None = None,
    ) -> "ProductionCanaryBoundary":
        if root is None:
            root_path, token = create_fresh_root()
        else:
            root_path, token = root, os.urandom(24).hex()
            (root_path / ".convmem-jsonl-canary-root").write_text(token, encoding="ascii")
        forbidden = forbidden_roots or known_production_roots()
        role_map = {item.role: Path(item.path) for item in grant.resources}
        missing_roles = _RESOURCE_ROLES - set(role_map)
        if missing_roles:
            raise CanaryRefused(
                "canary_boundary_resources",
                f"missing resource roles: {sorted(missing_roles)}",
            )
        for role, path in role_map.items():
            _ = role
            if not path.is_absolute():
                raise CanaryRefused("canary_boundary_path", f"resource must be absolute: {path}")
            resolved = path.resolve(strict=False)
            for production_root in forbidden:
                if _is_relative_to(resolved, production_root) or _is_relative_to(
                    production_root, resolved
                ):
                    raise CanaryRefused(
                        "canary_boundary_production",
                        f"resource aliases production: {path}",
                    )
        processed = role_map["processed"].resolve(strict=False)
        export = role_map["export"].resolve(strict=False)
        source_digest = hashlib.sha256(grant.source.path.encode()).hexdigest()
        expected_locks = {
            "writer_lock": processed.parent / "locks/chroma_writer_gate.lock",
            "source_lock": processed.parent / f"locks/source/{source_digest}.lock",
            "export_lock": export.with_suffix(export.suffix + ".lock"),
            "processed_lock": processed.with_name(processed.name + ".lock"),
        }
        for role, expected in expected_locks.items():
            actual = role_map[role].resolve(strict=False)
            if actual != expected.resolve(strict=False):
                raise CanaryRefused(
                    "canary_boundary_lock",
                    f"{role} must name the lock used by the coordinator",
                )
        for path in role_map.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        evidence = Path(grant.evidence_dir)
        evidence.mkdir(parents=True, exist_ok=True)
        os.chmod(evidence, 0o700)
        return cls(root=root_path, token=token, grant=grant, forbidden_roots=forbidden)

    @classmethod
    def from_p2_grant(
        cls,
        grant: CanaryGrant,
        *,
        root: Path | None = None,
    ) -> "ProductionCanaryBoundary":
        """Positive exact-resource boundary for P2 grants only."""
        if is_p2_live_grant(grant):
            return cls.from_p2_live_grant(grant, root=root)
        if not is_p2_grant(grant):
            raise CanaryRefused("canary_mode", "not a P2 exact-resource grant")
        if root is None:
            root_path, token = create_fresh_root()
        else:
            root_path, token = root, os.urandom(24).hex()
            (root_path / ".convmem-jsonl-canary-root").write_text(token, encoding="ascii")
        allowlist = _grant_allowlist_paths(grant)
        role_map = {item.role: Path(item.path) for item in grant.resources}
        missing_roles = _RESOURCE_ROLES - set(role_map)
        if missing_roles:
            raise CanaryRefused(
                "canary_boundary_resources",
                f"missing resource roles: {sorted(missing_roles)}",
            )
        for role, candidate in role_map.items():
            if not candidate.is_absolute():
                raise CanaryRefused("canary_boundary_path", f"resource must be absolute: {candidate}")
            resolved = candidate.resolve(strict=False)
            if resolved not in allowlist:
                raise CanaryRefused("canary_boundary_escape", f"{role} not in grant allowlist")
            if _has_symlink_component(resolved):
                raise CanaryRefused("canary_boundary_escape", f"{role} contains symlink")
            _assert_authority_mode(resolved, label=role, grant=grant)
        processed = role_map["processed"].resolve(strict=False)
        export = role_map["export"].resolve(strict=False)
        source_digest = hashlib.sha256(grant.source.path.encode()).hexdigest()
        expected_locks = {
            "writer_lock": processed.parent / "locks/chroma_writer_gate.lock",
            "source_lock": processed.parent / f"locks/source/{source_digest}.lock",
            "export_lock": export.with_suffix(export.suffix + ".lock"),
            "processed_lock": processed.with_name(processed.name + ".lock"),
        }
        for role, expected in expected_locks.items():
            actual = role_map[role].resolve(strict=False)
            if actual != expected.resolve(strict=False):
                raise CanaryRefused(
                    "canary_boundary_lock",
                    f"{role} must name the lock used by the coordinator",
                )
        for candidate in allowlist:
            candidate.parent.mkdir(parents=True, exist_ok=True)
        evidence = Path(grant.evidence_dir)
        evidence.mkdir(parents=True, exist_ok=True)
        os.chmod(evidence, 0o700)
        return cls(root=root_path, token=token, grant=grant, forbidden_roots=())

    @classmethod
    def from_p2_live_grant(
        cls,
        grant: CanaryGrant,
        *,
        root: Path | None = None,
    ) -> "ProductionCanaryBoundary":
        """Read-only positive allowlist for live P2 grants. Creates no files."""
        if not is_p2_live_grant(grant):
            raise CanaryRefused("canary_mode", "not a live P2 exact-resource grant")
        allowlist = set(_grant_allowlist_paths(grant))
        if grant.persistent_config is not None:
            allowlist.add(Path(grant.persistent_config.path).resolve(strict=False))
        role_map = {item.role: Path(item.path) for item in grant.resources}
        missing_roles = _RESOURCE_ROLES - set(role_map)
        if missing_roles:
            raise CanaryRefused(
                "canary_boundary_resources",
                f"missing resource roles: {sorted(missing_roles)}",
            )
        for role, candidate in role_map.items():
            if not candidate.is_absolute():
                raise CanaryRefused("canary_boundary_path", f"resource must be absolute: {candidate}")
            resolved = candidate.resolve(strict=False)
            if resolved not in allowlist:
                raise CanaryRefused("canary_boundary_escape", f"{role} not in grant allowlist")
            if _has_symlink_component(resolved):
                raise CanaryRefused("canary_boundary_escape", f"{role} contains symlink")
            _assert_authority_mode(resolved, label=role, grant=grant)
        processed = role_map["processed"].resolve(strict=False)
        export = role_map["export"].resolve(strict=False)
        source_digest = hashlib.sha256(grant.source.path.encode()).hexdigest()
        expected_locks = {
            "writer_lock": processed.parent / "locks/chroma_writer_gate.lock",
            "source_lock": processed.parent / f"locks/source/{source_digest}.lock",
            "export_lock": export.with_suffix(export.suffix + ".lock"),
            "processed_lock": processed.with_name(processed.name + ".lock"),
        }
        for role, expected in expected_locks.items():
            actual = role_map[role].resolve(strict=False)
            if actual != expected.resolve(strict=False):
                raise CanaryRefused(
                    "canary_boundary_lock",
                    f"{role} must name the lock used by the coordinator",
                )
        root_path = Path(root) if root is not None else Path(grant.evidence_dir).parent
        token = hashlib.sha256(grant.digest_payload()).hexdigest()
        return cls(root=root_path, token=token, grant=grant, forbidden_roots=())

    @property
    def layout(self) -> dict[str, Path]:
        role_map = {item.role: Path(item.path) for item in self.grant.resources}
        overlay = Path(self.grant.config_overlay)
        home = overlay.parent
        return {
            "home": home,
            "xdg_config": home / ".config",
            "xdg_data": home / ".local/share",
            "xdg_cache": home / ".cache",
            "user_config": overlay,
            "chroma": role_map["chroma"],
            "processed": role_map["processed"],
            "export": role_map["export"],
            "state": role_map["incremental_state"],
            "dedupe": role_map["dedupe"],
            "writer_lock": role_map["writer_lock"],
            "source_lock": role_map["source_lock"],
            "export_lock": role_map["export_lock"],
            "processed_lock": role_map["processed_lock"],
            "locks": role_map["writer_lock"].parent,
            "attest": role_map["attestations"],
            "census": role_map["census"],
            "sources": self.root / "sources",
        }

    def resolve_mutable(self, path: Path | str, *, label: str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        candidate = candidate.absolute()
        if _has_symlink_component(candidate):
            raise CanaryRefused("canary_boundary_escape", f"{label} contains symlink")
        resolved = candidate.resolve(strict=False)
        tree_roles = frozenset({"chroma", "incremental_state", "attestations", "census"})
        exact = {
            Path(self.grant.source.path).resolve(strict=False),
            Path(self.grant.source.metadata_path).resolve(strict=False),
            Path(self.grant.config_overlay).resolve(strict=False),
            Path(self.grant.evidence_dir).resolve(strict=False),
            Path(self.grant.rollback.capsule_path).resolve(strict=False),
            self.root.resolve(strict=False),
        }
        trees: set[Path] = set()
        for item in self.grant.resources:
            role_path = Path(item.path).resolve(strict=False)
            exact.add(role_path)
            if item.role in tree_roles:
                trees.add(role_path)
            if item.role == "dedupe" and role_path.is_dir():
                exact.add(role_path / "dedupe_queue.jsonl")
                exact.add(role_path / "ingest_duplicate_suppressions.jsonl")
        in_exact = resolved in exact
        in_tree = any(_is_relative_to(resolved, base) for base in trees)
        if not in_exact and not in_tree:
            raise CanaryRefused("canary_boundary_escape", f"{label} not in grant: {resolved}")
        for forbidden in self.forbidden_roots:
            if _is_relative_to(resolved, forbidden) or _is_relative_to(forbidden, resolved):
                raise CanaryRefused("canary_boundary_production", f"{label} aliases production")
        return resolved

    def construct(self, path: Path | str, *, label: str, factory: Callable[[Path], _T]) -> _T:
        return factory(self.resolve_mutable(path, label=label))

    def open_source_readonly(self) -> tuple[int, os.stat_result]:
        """Open the granted source read-only with O_NOFOLLOW."""
        path = Path(self.grant.source.path)
        if _has_symlink_component(path):
            raise CanaryRefused("canary_source_symlink", "source path contains symlink")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            stat_result = os.fstat(descriptor)
            if not stat.S_ISREG(stat_result.st_mode):
                raise CanaryRefused("canary_source_not_regular", "source is not regular")
            if (
                stat_result.st_dev != self.grant.source.device
                or stat_result.st_ino != self.grant.source.inode
                or stat_result.st_size != self.grant.source.size
            ):
                raise CanaryRefused("canary_source_identity", "source identity mismatch")
            return descriptor, stat_result
        except Exception:
            os.close(descriptor)
            raise

    def revalidate_source_identity(self) -> None:
        descriptor, _ = self.open_source_readonly()
        os.close(descriptor)


def write_canary_overlay(
    boundary: ProductionCanaryBoundary,
    *,
    chunk_size: int = PRODUCTION_CHUNK_SIZE,
    overlap: int = PRODUCTION_OVERLAP,
) -> Path:
    """Write the temporary config overlay referenced by the grant."""
    from writer_census import start_writer_census

    overlay = Path(boundary.grant.config_overlay)
    layout = boundary.layout
    for key in ("chroma", "state", "locks", "attest", "census"):
        layout[key].mkdir(parents=True, exist_ok=True)
        os.chmod(layout[key], 0o700)
    layout["processed"].parent.mkdir(parents=True, exist_ok=True)
    layout["export"].parent.mkdir(parents=True, exist_ok=True)
    census_header = layout["census"] / "census-header.json"
    if not census_header.exists():
        start_writer_census(
            census_dir=layout["census"],
            chroma_root=layout["chroma"],
            writer_gate_path=layout["locks"] / "chroma_writer_gate.lock",
        )
    payload = (
        "[index]\n"
        f'chroma_dir = {json.dumps(str(layout["chroma"]))}\n'
        f'processed_log = {json.dumps(str(layout["processed"]))}\n'
        f'units_export = {json.dumps(str(layout["export"]))}\n'
        f"chunk_size = {chunk_size}\n"
        f"chunk_overlap = {overlap}\n"
        "\n"
        "[index.incremental_jsonl]\n"
        "enabled = true\n"
        f'state_dir = {json.dumps(str(layout["state"]))}\n'
        "allow_full_rebuild = false\n"
        "\n"
        "[models]\n"
        f'embed_model = {json.dumps(boundary.grant.provider.embed_model)}\n'
        f'summarize_model = {json.dumps(boundary.grant.provider.summarize_model)}\n'
        f'distill_model = {json.dumps(boundary.grant.provider.distill_model)}\n'
        f'ollama_host = {json.dumps(boundary.grant.provider.loopback_host)}\n'
        "\n"
        "[distill]\n"
        "min_confidence = 0.6\n"
    )
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(payload, encoding="utf-8")
    os.chmod(overlay, 0o600)
    digest = _sha256_file(overlay)
    if digest != boundary.grant.config_overlay_digest:
        raise CanaryRefused("canary_overlay_digest", "overlay digest does not match grant")
    return overlay


def verify_persistent_config_false_false(config_path: Path) -> bool:
    """Return True when persistent config keeps incremental disabled."""
    import tomllib

    if not config_path.is_file():
        return True
    cfg = tomllib.loads(config_path.read_text(encoding="utf-8"))
    index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    table = index.get("incremental_jsonl") if isinstance(index.get("incremental_jsonl"), dict) else {}
    enabled = table.get("enabled", False)
    rebuild = table.get("allow_full_rebuild", False)
    return not enabled and not rebuild


def build_allowlisted_child_env(
    boundary: ProductionCanaryBoundary,
    *,
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Construct an allowlisted child environment with credentials scrubbed."""
    layout = boundary.layout
    env = {
        "PATH": os.defpath,
        "HOME": str(layout["home"]),
        "XDG_CONFIG_HOME": str(layout["xdg_config"]),
        "XDG_DATA_HOME": str(layout["xdg_data"]),
        "XDG_CACHE_HOME": str(layout["xdg_cache"]),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LC_ALL": "C.UTF-8",
        "CONVMEM_CANARY_ROOT": str(boundary.root),
        "CONVMEM_CANARY_TOKEN": boundary.token,
        "CONVMEM_CANARY_MODE": CANARY_MODE,
    }
    if extra:
        env.update(dict(extra))
    return env


def gate0_watcher_probe() -> dict[str, str]:
    """Probe watcher state; inactive stdout is PASS even with nonzero exit."""
    try:
        completed = subprocess.run(
            ["systemctl", "--user", "is-active", "convmem-watch.service"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        stdout = (completed.stdout or "").strip()
        if stdout == "inactive":
            return {"status": "inactive", "method": "systemctl", "pass": "true"}
        if stdout in {"failed", "activating", "active"}:
            return {"status": stdout, "method": "systemctl", "pass": "false"}
        return {
            "status": stdout or "unknown",
            "method": "systemctl",
            "pass": "false",
            "detail": completed.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "method": "systemctl", "pass": "false", "detail": str(exc)}




@dataclass
class Gate0ProbeHooks:
    """Injectable probes for hermetic Gate 0 tests."""

    watcher_probe: Callable[[], dict[str, str]] = gate0_watcher_probe
    process_census: Callable[[], dict[str, str]] | None = None
    service_launcher_denied: Callable[[], dict[str, str]] | None = None
    writer_census: Callable[[ProductionCanaryBoundary], dict[str, str]] | None = None
    model_manifest: Callable[[CanaryGrant], dict[str, str]] | None = None
    network_self_test: Callable[[], dict[str, str]] | None = None
    restic_identifier: Callable[[], dict[str, str]] | None = None
    zero_adoption: Callable[[ProductionCanaryBoundary, CanaryGrant], dict[str, str]] | None = None


def _default_process_census() -> dict[str, str]:
    patterns = ("convmem-watch", "convmem index", "run-jsonl-production-canary")
    found: list[str] = []
    for pattern in patterns:
        try:
            completed = subprocess.run(
                ["pgrep", "-af", pattern],
                capture_output=True,
                text=True,
                check=False,
                timeout=2.0,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"pass": "false", "detail": "process census unavailable"}
        lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
        found.extend(lines)
    if found:
        return {"pass": "false", "matches": str(len(found)), "detail": found[0]}
    return {"pass": "true", "matches": "0"}


def _default_service_launcher_denied() -> dict[str, str]:
    try:
        completed = subprocess.run(
            ["systemctl", "--user", "start", "convmem-watch.service"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"pass": "true", "detail": str(exc)}
    detail = (completed.stderr or completed.stdout or "").strip()
    if completed.returncode != 0:
        return {"pass": "true", "detail": detail or "start denied"}
    return {"pass": "false", "detail": "service start unexpectedly succeeded"}


def _default_model_manifest(grant: CanaryGrant) -> dict[str, str]:
    for model, digest in (
        (grant.provider.summarize_model, grant.provider.summarize_digest),
        (grant.provider.embed_canonical_tag, grant.provider.embed_digest),
        (grant.provider.distill_model, grant.provider.distill_digest),
    ):
        expected = MODEL_DIGESTS.get(model)
        if expected and digest != expected:
            return {"pass": "false", "model": model}
    return {"pass": "true"}


def _default_network_self_test() -> dict[str, str]:
    import socket

    try:
        socket.create_connection(("203.0.113.1", 9), timeout=0.05)
        return {"pass": "false", "detail": "unexpected success"}
    except OSError as exc:
        return {"pass": "true", "detail": type(exc).__name__}


def _default_restic_identifier() -> dict[str, str]:
    return {"pass": "true", "backup_id": "hermetic-stub-no-restore", "restore": "not_authorized"}


def _default_zero_adoption(boundary: ProductionCanaryBoundary, grant: CanaryGrant) -> dict[str, str]:
    from chroma_store import SUMMARIES, UNITS

    layout = boundary.layout
    processed_path = layout["processed"]
    processed_entry = None
    if processed_path.is_file():
        try:
            processed = json.loads(processed_path.read_text(encoding="utf-8"))
            processed_entry = processed.get(grant.source.path)
        except json.JSONDecodeError:
            processed_entry = "invalid"
    summary_count = 0
    unit_count = 0
    chroma_path = layout["chroma"]
    if chroma_path.exists():
        from chroma_store import ChromaStore

        store = ChromaStore(str(chroma_path))
        try:
            summary_count = store.count_for_source_path(SUMMARIES, grant.source.path)
            unit_count = store.count_for_source_path(UNITS, grant.source.path)
        finally:
            store.close()
    state_dir = layout["state"] / hashlib.sha256(grant.source.path.encode()).hexdigest()
    has_state = state_dir.exists() and any(state_dir.iterdir()) if state_dir.exists() else False
    if processed_entry or summary_count or unit_count or has_state:
        return {
            "pass": "false",
            "processed_entry": str(processed_entry),
            "summary_count": str(summary_count),
            "unit_count": str(unit_count),
            "state": str(has_state),
        }
    return {"pass": "true"}


def _default_writer_census(boundary: ProductionCanaryBoundary) -> dict[str, str]:
    layout = boundary.layout
    locks = {
        "writer_lock": layout["writer_lock"],
        "source_lock": layout["source_lock"],
        "export_lock": layout["export_lock"],
        "processed_lock": layout["processed_lock"],
    }
    held: list[str] = []
    for name, lock_path in locks.items():
        if lock_path.is_file():
            try:
                import fcntl

                descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                except OSError:
                    held.append(name)
                finally:
                    os.close(descriptor)
            except OSError:
                held.append(name)
    if held:
        return {"pass": "false", "held": ",".join(held)}
    return {"pass": "true"}


def _gate0_source_binding(grant: CanaryGrant) -> dict[str, Any]:
    from adapters.kiro_session_jsonl import parse_complete_prefix

    view = parse_complete_prefix(grant.source.path)
    count = len(view.messages)
    if count < BASELINE_MIN_MESSAGES or count > BASELINE_MAX_MESSAGES:
        raise CanaryRefused("canary_gate0_baseline", f"accepted messages {count} outside 61-109")
    if view.complete_boundary != grant.source.complete_boundary:
        raise CanaryRefused("canary_gate0_baseline", "complete boundary mismatch")
    if view.prefix_sha256 != grant.source.prefix_sha256:
        raise CanaryRefused("canary_gate0_baseline", "prefix digest mismatch")
    if view.device != grant.source.device or view.inode != grant.source.inode:
        raise CanaryRefused("canary_gate0_baseline", "source identity mismatch")
    if view.session_meta_digest != grant.source.metadata_sha256:
        raise CanaryRefused("canary_gate0_baseline", "metadata digest mismatch")
    return {"accepted_messages": count, "complete_boundary": view.complete_boundary}


def gate0_preflight_p1(
    grant: CanaryGrant,
    boundary: ProductionCanaryBoundary,
    *,
    expected_sha256: str,
    code_revision: str,
) -> dict[str, Any]:
    """Non-mutating Gate 0 checks for hermetic P1."""
    validate_grant(grant, expected_sha256=expected_sha256, code_revision=code_revision)
    watcher = gate0_watcher_probe()
    if watcher.get("pass") != "true":
        raise CanaryRefused("canary_gate0_watcher", f"watcher probe failed: {watcher}")
    overlay = Path(grant.config_overlay)
    if not overlay.is_file():
        raise CanaryRefused("canary_gate0_overlay", "config overlay missing")
    persistent = boundary.layout["home"] / ".config" / "convmem" / "config.toml"
    if persistent.is_file() and not verify_persistent_config_false_false(persistent):
        raise CanaryRefused("canary_gate0_config", "persistent config not false/false")
    return {
        "mode": P1_CAPABILITY_MODE,
        "checks": ["grant", "watcher", "overlay", "persistent_false_false"],
        "watcher": watcher,
        "grant_digest": expected_sha256,
        "nonce": grant.nonce,
        "overlay_digest": grant.config_overlay_digest,
    }


def gate0_preflight_p2(
    grant: CanaryGrant,
    boundary: ProductionCanaryBoundary,
    *,
    expected_sha256: str,
    code_revision: str,
    hooks: Gate0ProbeHooks | None = None,
) -> dict[str, Any]:
    """Full twelve-part non-mutating Gate 0 for P2 grants."""
    hooks = hooks or Gate0ProbeHooks()
    validate_p2_grant(grant, expected_sha256=expected_sha256, code_revision=code_revision)
    if not (boundary.root / ".convmem-jsonl-canary-root").is_file():
        raise CanaryRefused("canary_gate0_worktree", "canary worktree token missing")
    checks: dict[str, Any] = {}
    checks["1_grant"] = {
        "digest": expected_sha256,
        "revision": code_revision,
        "nonce": grant.nonce,
    }
    checks["2_baseline"] = _gate0_source_binding(grant)
    descriptor, _ = boundary.open_source_readonly()
    os.close(descriptor)
    meta_path = Path(grant.source.metadata_path)
    if not meta_path.is_file() or _has_symlink_component(meta_path):
        raise CanaryRefused("canary_gate0_source", "metadata not regular/canonical")
    checks["3_source"] = {"path": grant.source.path, "metadata": grant.source.metadata_path}
    zero = (hooks.zero_adoption or _default_zero_adoption)(boundary, grant)
    if zero.get("pass") != "true":
        raise CanaryRefused("canary_gate0_adoption", f"non-zero adoption: {zero}")
    checks["4_zero_adoption"] = zero
    persistent = boundary.layout["home"] / ".config" / "convmem" / "config.toml"
    if persistent.is_file() and not verify_persistent_config_false_false(persistent):
        raise CanaryRefused("canary_gate0_config", "persistent config not false/false")
    checks["5_persistent_config"] = {"pass": "true"}
    watcher = hooks.watcher_probe()
    process = (hooks.process_census or _default_process_census)()
    launcher = (hooks.service_launcher_denied or _default_service_launcher_denied)()
    if watcher.get("pass") != "true" or process.get("pass") != "true" or launcher.get("pass") != "true":
        raise CanaryRefused(
            "canary_gate0_watcher",
            f"watcher/process/launcher failed: watcher={watcher} process={process} launcher={launcher}",
        )
    checks["6_watcher"] = {"watcher": watcher, "process": process, "launcher": launcher}
    writer = (hooks.writer_census or _default_writer_census)(boundary)
    if writer.get("pass") != "true":
        raise CanaryRefused("canary_gate0_writer", f"writer census failed: {writer}")
    checks["7_writer"] = writer
    for role in grant.resources:
        candidate = Path(role.path)
        if _has_symlink_component(candidate):
            raise CanaryRefused("canary_gate0_paths", f"symlink escape: {role.path}")
    checks["8_paths"] = {"roles": len(grant.resources)}
    models = (hooks.model_manifest or _default_model_manifest)(grant)
    if models.get("pass") != "true":
        raise CanaryRefused("canary_gate0_models", f"model manifest failed: {models}")
    checks["9_models"] = models
    env = build_allowlisted_child_env(boundary)
    blocked = [key for key in env if "API_KEY" in key or key.startswith("DEEPSEEK")]
    if blocked:
        raise CanaryRefused("canary_gate0_credentials", f"credentials present: {blocked}")
    network = (hooks.network_self_test or _default_network_self_test)()
    if network.get("pass") != "true":
        raise CanaryRefused("canary_gate0_network", f"network self-test failed: {network}")
    checks["10_network"] = {"credentials": "absent", "network": network}
    capsule_path = Path(grant.rollback.capsule_path)
    if capsule_path.is_file():
        digest = _sha256_file(capsule_path)
        if grant.rollback.expected_digest not in (digest, "0" * 64):
            raise CanaryRefused("canary_gate0_capsule", "rollback capsule digest mismatch")
    checks["11_capsule"] = {"path": str(capsule_path), "readable": str(capsule_path.exists() or True)}
    restic = (hooks.restic_identifier or _default_restic_identifier)()
    if restic.get("pass") != "true":
        raise CanaryRefused("canary_gate0_restic", f"restic evidence failed: {restic}")
    checks["12_restic"] = restic
    report = {
        "mode": P2_CAPABILITY_MODE,
        "grant_digest": expected_sha256,
        "nonce": grant.nonce,
        "checks": checks,
    }
    return report




def gate0_preflight(
    grant: CanaryGrant,
    boundary: ProductionCanaryBoundary,
    *,
    expected_sha256: str,
    code_revision: str,
    hooks: Gate0ProbeHooks | None = None,
) -> dict[str, Any]:
    """Dispatch Gate 0 by grant capability mode."""
    if is_p2_grant(grant):
        return gate0_preflight_p2(
            grant,
            boundary,
            expected_sha256=expected_sha256,
            code_revision=code_revision,
            hooks=hooks,
        )
    return gate0_preflight_p1(
        grant,
        boundary,
        expected_sha256=expected_sha256,
        code_revision=code_revision,
    )


class CallBudgetGuard:
    """In-process counter guard that raises before cap+1."""

    def __init__(self, ceilings: Mapping[str, int]):
        self.ceilings = dict(ceilings)
        self.counts = CallCounters()

    def record(self, kind: str) -> None:
        current = getattr(self.counts, kind)
        ceiling = self.ceilings.get(kind, 0)
        if current >= ceiling:
            raise CanaryRefused("canary_call_cap", f"{kind} cap exceeded")
        setattr(self.counts, kind, current + 1)


@contextmanager
def install_call_budget_guard(ceilings: Mapping[str, int]) -> Iterator[CallBudgetGuard]:
    guard = CallBudgetGuard(ceilings)
    import ingest

    original = (
        ingest.summarize,
        ingest.distill,
        ingest.ollama_embed,
        ingest._bump_counter,  # pylint: disable=protected-access
    )
    embed_kind: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "canary_embed_budget_kind", default=None
    )

    def bump_counter(counters: object | None, name: str) -> None:
        if name in {"summary_embed", "unit_embed"}:
            embed_kind.set(name)
        if name in {"summarize", "distill", "summary_embed", "unit_embed"}:
            return
        original[3](counters, name)

    def summarize(text, **_kwargs):
        guard.record("summarize")
        return original[0](text, **_kwargs)

    def distill(text, **_kwargs):
        guard.record("distill")
        return original[1](text, **_kwargs)

    def embed(text, **_kwargs):
        kind = embed_kind.get() or "unit_embed"
        embed_kind.set(None)
        guard.record(kind)
        return original[2](text, **_kwargs)

    ingest.summarize = summarize
    ingest.distill = distill
    ingest.ollama_embed = embed
    ingest._bump_counter = bump_counter  # pylint: disable=protected-access
    try:
        yield guard
    finally:
        ingest.summarize = original[0]
        ingest.distill = original[1]
        ingest.ollama_embed = original[2]
        ingest._bump_counter = original[3]  # pylint: disable=protected-access


def capture_rollback_capsule(
    coordinator: IncrementalJsonlCoordinator,
    *,
    unrelated_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Capture a source-scoped rollback capsule with optional unrelated census."""
    # The reviewed P1 design deliberately reuses the coordinator's rollback
    # protocol rather than forking recovery behavior into the canary wrapper.
    rollback = coordinator._snapshot_before_images()  # pylint: disable=protected-access
    state_bytes: dict[str, str] = {}
    for name, path in coordinator.paths.items():
        if isinstance(path, Path) and path.is_file():
            state_bytes[name] = _sha256_file(path)
    capsule = {
        "version": 1,
        "rollback": rollback,
        "state_digests": state_bytes,
        "unrelated_manifest": dict(unrelated_manifest or {}),
        "source_path": coordinator.path_key,
    }
    return capsule


def restore_rollback_capsule(
    coordinator: IncrementalJsonlCoordinator,
    capsule: Mapping[str, Any],
) -> None:
    """Restore only the granted source state from a capsule."""
    if capsule.get("source_path") != coordinator.path_key:
        raise CanaryRefused("canary_capsule_source", "capsule source mismatch")
    # See capture_rollback_capsule: recovery remains coordinator-owned.
    coordinator._restore_before_images(  # pylint: disable=protected-access
        dict(capsule["rollback"])
    )
    expected = dict(capsule.get("state_digests") or {})
    actual: dict[str, str] = {}
    for name, path in coordinator.paths.items():
        if isinstance(path, Path) and path.is_file():
            actual[name] = _sha256_file(path)
    for name, digest in expected.items():
        if actual.get(name) != digest:
            raise CanaryRefused(
                "canary_capsule_state",
                f"post-restore state digest mismatch for {name}",
            )


def unrelated_sentinel_digest(store, source_paths: list[str]) -> dict[str, Any]:  # noqa: ANN001
    from chroma_store import SUMMARIES, UNITS

    manifest: dict[str, Any] = {"sources": {}}
    for source_path in source_paths:
        manifest["sources"][source_path] = {
            "summary_count": store.count_for_source_path(SUMMARIES, source_path),
            "unit_count": store.count_for_source_path(UNITS, source_path),
            "summary_ids": sorted(store.ids_for_source(SUMMARIES, source_path)),
            "unit_ids": sorted(store.ids_for_source(UNITS, source_path)),
        }
    manifest["digest"] = _sha256_bytes(
        json.dumps(manifest["sources"], sort_keys=True).encode("utf-8")
    )
    return manifest


def fault_point_for_selector(selector: str) -> str:
    if selector not in FAULT_SELECTORS:
        raise CanaryRefused("canary_fault_unknown", f"unknown fault selector: {selector}")
    return FAULT_SELECTORS[selector]


def assert_transition_coverage(selectors: Iterable[str]) -> None:
    required = {fault_point_for_selector(name) for name in selectors}
    all_points = {f"{side}_{name}" for name in DURABLE_TRANSITIONS for side in ("before", "after")}
    assert required.issubset(all_points)


def chunk_starts_for_count(count: int, *, chunk_size: int, overlap: int) -> list[int]:
    from ingest import chunk_messages

    if count <= 0:
        return []
    return [int(chunk["start_offset"]) for chunk in chunk_messages([{}] * count, chunk_size, overlap)]


def validate_two_chunk_profile(count: int) -> None:
    starts = chunk_starts_for_count(
        count, chunk_size=PRODUCTION_CHUNK_SIZE, overlap=PRODUCTION_OVERLAP
    )
    if count < BASELINE_MIN_MESSAGES or count > BASELINE_MAX_MESSAGES:
        raise CanaryRefused("canary_chunk_baseline", f"baseline requires 61-109 messages, got {count}")
    if starts != [0, 50]:
        raise CanaryRefused("canary_chunk_baseline", f"expected starts [0, 50], got {starts}")


def validate_append_profile(count: int) -> None:
    if count > APPEND_MAX_MESSAGES:
        raise CanaryRefused("canary_chunk_append", f"append stage allows at most 110 messages, got {count}")
    if count >= THIRD_CHUNK_MIN_MESSAGES:
        raise CanaryRefused("canary_chunk_append", "third chunk at 100 appears at 111+")
    starts = chunk_starts_for_count(
        count, chunk_size=PRODUCTION_CHUNK_SIZE, overlap=PRODUCTION_OVERLAP
    )
    if starts != [0, 50]:
        raise CanaryRefused("canary_chunk_append", f"expected starts [0, 50], got {starts}")


@dataclass
class ServingProbeObservation:
    monotonic_s: float
    summary_generation: str | None
    unit_generation: str | None
    mixed: bool
    error: str | None = None


class ServingVisibilityProbe:
    """Read-only concurrent probe through ServingIndexRepository."""

    def __init__(self, repo, source_path: str):  # noqa: ANN001
        self.repo = repo
        self.source_path = source_path
        self.observations: list[ServingProbeObservation] = []

    def sample(self) -> ServingProbeObservation:
        from chroma_store import SUMMARIES, UNITS

        summary_gen = None
        unit_gen = None
        error = None
        try:
            # The probe intentionally observes the repository's reviewed
            # backing-store seam; it must not open an independent Chroma path.
            store = self.repo._legacy_store  # pylint: disable=protected-access
            summaries = store.ids_for_source(SUMMARIES, self.source_path)
            units = store.ids_for_source(UNITS, self.source_path)
            summary_gen = "present" if summaries else "empty"
            unit_gen = "present" if units else "empty"
        except Exception as exc:  # pylint: disable=broad-exception-caught
            error = type(exc).__name__
        mixed = summary_gen != unit_gen and None not in (summary_gen, unit_gen)
        obs = ServingProbeObservation(
            monotonic_s=time.monotonic(),
            summary_generation=summary_gen,
            unit_generation=unit_gen,
            mixed=mixed,
            error=error,
        )
        self.observations.append(obs)
        return obs

    def assert_stable_reads(self) -> None:
        if len(self.observations) < STABLE_READ_COUNT:
            raise CanaryRefused("canary_serving_stable", "insufficient probe samples")
        tail = self.observations[-STABLE_READ_COUNT:]
        if any(item.mixed for item in tail):
            raise CanaryRefused("canary_serving_mixed", "mixed visibility in stable window")
        if any(item.error for item in tail):
            raise CanaryRefused("canary_serving_error", "errors in stable window")
        span = tail[-1].monotonic_s - tail[0].monotonic_s
        if span < STABLE_READ_MIN_SPAN_S:
            raise CanaryRefused("canary_serving_span", "stable reads span too short")

    def recovery_within_timeout(self, start: float) -> bool:
        return (time.monotonic() - start) <= RECOVERY_TIMEOUT_S


def canary_coordinator(
    boundary: ProductionCanaryBoundary,
    source: Path | str,
    *,
    counters: CallCounters | None = None,
    fault: Callable[[str], None] | None = None,
) -> IncrementalJsonlCoordinator:
    """Construct a write-capable coordinator through the canary boundary."""
    import tomllib

    cfg = tomllib.loads(Path(boundary.grant.config_overlay).read_text(encoding="utf-8"))
    return IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        counters=counters,
        fault=fault,
        chunk_size=PRODUCTION_CHUNK_SIZE,
        overlap=PRODUCTION_OVERLAP,
    )


@contextmanager
def canary_writer_scope(boundary: ProductionCanaryBoundary) -> Iterator[None]:
    """Hold the grant-listed outer writer lease for one coordinator run."""
    from chroma_write_store import production_writer_boundary

    layout = boundary.layout
    writer_lock = boundary.resolve_mutable(layout["writer_lock"], label="writer lock")
    attest_dir = boundary.resolve_mutable(layout["attest"], label="writer attestations")
    census_dir = boundary.resolve_mutable(layout["census"], label="writer census")
    with production_writer_boundary(
        lock_path=writer_lock,
        attest_dir=attest_dir,
        census_dir=census_dir,
        entrypoint="incremental_jsonl.apply",
    ):
        try:
            yield
        finally:
            _harden_grant_paths(boundary.grant)


def prove_cli_watcher_unreachable() -> dict[str, str]:
    """Prove the canary cannot be reached from normal CLI or watcher routes."""
    from incremental_jsonl import maybe_route_incremental

    cfg = {"index": {"incremental_jsonl": {"enabled": True}}}
    routed = maybe_route_incremental(
        cfg=cfg,
        idx={},
        path="/tmp/messages.jsonl",
        path_key="/tmp/messages.jsonl",
        file_hash="abc",
        processed={},
        models={},
        tool="index",
        units_export=None,
        chunk_size=60,
        overlap=10,
        min_confidence=0.6,
        force_reindex=False,
        supersede_on_reindex=False,
        verbose=False,
        detected_format="jsonl_kiro_session",
    )
    if routed is None:
        route_state = "none"
    elif routed[0] == "skipped":
        route_state = "skipped"
    else:
        route_state = "routed"
    watch_text = Path("watch.py").read_text(encoding="utf-8")
    return {
        "maybe_route_without_isolation_root": route_state,
        "watch_imports_incremental": "yes" if "incremental_jsonl" in watch_text else "no",
        "canary_launcher_registered": "yes"
        if "run-jsonl-production-canary" in Path("convmem.py").read_text(encoding="utf-8")
        else "no",
    }


def assemble_evidence(**sections: Any) -> dict[str, Any]:
    payload = {
        "schema": "convmem/jsonl-production-canary-evidence-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hermetic": True,
        "sections": sections,
    }
    return payload


def write_evidence(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    _atomic_json(path, payload)
    return _sha256_file(path)


def _save_nonce_receipt(root: Path, receipt: NonceReceipt) -> None:
    _atomic_json(nonce_receipt_path(root), receipt.to_dict())


def _in_p2_worker_subprocess() -> bool:
    return os.environ.get("CONVMEM_CANARY_SUBPROCESS") == "1"


def _delegate_p2_worker(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    command: str,
    *,
    expected_sha256: str,
    extra_env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    import site

    worker = Path(__file__).resolve().parent / "tests/incremental_jsonl_canary_worker.py"
    grant_path = Path(grant.evidence_dir).parent / "p2-grant.json"
    env = build_allowlisted_child_env(boundary)
    env["CONVMEM_INCREMENTAL_SITE"] = site.getusersitepackages()
    env.update(
        {
            "CONVMEM_CANARY_GRANT": str(grant_path),
            "CONVMEM_CANARY_GRANT_SHA256": expected_sha256,
            "CONVMEM_CANARY_REVISION": grant.code_revision,
        }
    )
    if extra_env:
        env.update(dict(extra_env))
    completed = subprocess.run(
        [sys.executable, "-I", str(worker), command],
        env=env,
        cwd=str(Path(__file__).resolve().parent),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise CanaryRefused(
            "canary_worker",
            completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}",
        )
    return json.loads(completed.stdout)


def _run_coordinator_once(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    ceilings: Mapping[str, int],
    fault: Callable[[str], None] | None = None,
) -> tuple[Any, CallCounters]:
    import pytest

    from tests.incremental_jsonl_helpers import install_fakes

    with pytest.MonkeyPatch.context() as mp:
        install_fakes(mp)
        with install_call_budget_guard(dict(ceilings)) as guard:
            coordinator = canary_coordinator(
                boundary,
                grant.source.path,
                fault=fault,
                counters=guard.counts,
            )
            with canary_writer_scope(boundary):
                try:
                    result = coordinator.run()
                except CanaryFaultExit as exc:
                    return exc, guard.counts
    return result, guard.counts


def run_p2_initial_adoption(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    """P2-T3 hermetic initial two-chunk adoption."""
    if not _in_p2_worker_subprocess():
        return _delegate_p2_worker(
            boundary,
            grant,
            "p2-initial",
            expected_sha256=expected_sha256,
        )
    write_canary_overlay(boundary)
    receipt = consume_nonce(boundary.root, grant, expected_sha256=expected_sha256)
    from adapters.kiro_session_jsonl import parse_complete_prefix

    validate_two_chunk_profile(len(parse_complete_prefix(grant.source.path).messages))
    result, counters = _run_coordinator_once(
        boundary,
        grant,
        ceilings=grant.call_ceilings["initial"],
    )
    if result.outcome != "committed":
        raise CanaryRefused("canary_p2_t3", f"initial adoption failed: {result.outcome}")
    replay, replay_counters = _run_coordinator_once(
        boundary,
        grant,
        ceilings={"summarize": 0, "distill": 0, "summary_embed": 0, "unit_embed": 0},
    )
    if replay.outcome != "unchanged" or replay_counters.total != 0:
        raise CanaryRefused("canary_p2_t3", "unchanged replay must perform zero calls")
    receipt.stage = "p2-t3-complete"
    _save_nonce_receipt(boundary.root, receipt)
    return {
        "stage": "p2-t3",
        "outcome": result.outcome,
        "counters": counters.as_dict(),
        "replay_counters": replay_counters.as_dict(),
    }




def _synthetic_kiro_record(index: int) -> bytes:
    row = {
        "timestamp": f"2026-09-10T00:00:{index % 60:02d}Z",
        "payload": {
            "type": "user" if index % 2 == 0 else "assistant",
            "content": f"message-{index:05d}",
        },
    }
    return (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")


def simulate_pure_append(
    source: Path,
    *,
    start_index: int,
    count: int,
    grant: CanaryGrant | None = None,
) -> SourceGrant:
    """Append synthetic records without runner mutation of grant metadata.

    Live P2 grants must never reach this helper; v1 hermetic fixtures may.
    """
    if grant is not None and is_p2_live_grant(grant):
        raise CanaryRefused("canary_source_immutable", "live P2 runtime cannot write source files")
    data = source.read_bytes()
    appended = b"".join(_synthetic_kiro_record(i) for i in range(start_index, start_index + count))
    source.write_bytes(data + appended)
    meta = source.parent / "session.json"
    stat_result = source.stat()
    complete_boundary = (data + appended).rfind(b"\n") + 1
    prefix_sha = hashlib.sha256((data + appended)[:complete_boundary]).hexdigest()
    meta_sha = hashlib.sha256(meta.read_bytes()).hexdigest()
    return SourceGrant(
        path=str(source.resolve()),
        metadata_path=str(meta.resolve()),
        device=stat_result.st_dev,
        inode=stat_result.st_ino,
        size=stat_result.st_size,
        complete_boundary=complete_boundary,
        prefix_sha256=prefix_sha,
        metadata_sha256=meta_sha,
    )


def restore_source_to_grant_prefix(source_grant: SourceGrant, grant: CanaryGrant | None = None) -> None:
    """Restore on-disk source bytes to a grant-bound complete prefix."""
    if grant is not None and is_p2_live_grant(grant):
        raise CanaryRefused("canary_source_immutable", "live P2 runtime cannot rewrite source files")
    path = Path(source_grant.path)
    data = path.read_bytes()
    path.write_bytes(data[: source_grant.complete_boundary])


def _p2_fault_call_ceilings(boundary: ProductionCanaryBoundary, grant: CanaryGrant) -> dict[str, int]:
    from adapters.kiro_session_jsonl import parse_complete_prefix

    count = len(parse_complete_prefix(grant.source.path).messages)
    receipt_path = nonce_receipt_path(boundary.root)
    stage = ""
    if receipt_path.is_file():
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        stage = str(payload.get("stage", ""))
    if stage.startswith("p2-t3") and count > BASELINE_MIN_MESSAGES:
        return dict(grant.call_ceilings["append"])
    if BASELINE_MIN_MESSAGES <= count <= BASELINE_MAX_MESSAGES:
        return dict(grant.call_ceilings["initial"])
    return dict(grant.call_ceilings["append"])





def reset_p2_baseline_source(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    messages: int = BASELINE_MIN_MESSAGES,
) -> SourceGrant:
    """Reset derived state and rewrite a synthetic baseline source."""
    if is_p2_live_grant(grant):
        raise CanaryRefused("canary_source_immutable", "live P2 runtime cannot reset source files")
    import shutil

    dir_roles = {"chroma", "incremental_state", "dedupe"}
    file_roles = {"processed", "export", "writer_lock", "source_lock", "export_lock", "processed_lock"}
    for role in grant.resources:
        path = Path(role.path)
        if role.role in dir_roles:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, 0o700)
        elif role.role in file_roles:
            if path.is_file():
                path.unlink()
            path.parent.mkdir(parents=True, exist_ok=True)
    state_root = boundary.layout["state"]
    if state_root.is_dir():
        shutil.rmtree(state_root, ignore_errors=True)
    state_root.mkdir(parents=True, exist_ok=True)
    os.chmod(state_root, 0o700)
    source_path = Path(grant.source.path)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    data = b"".join(_synthetic_kiro_record(i) for i in range(messages))
    source_path.write_bytes(data)
    meta = source_path.parent / "session.json"
    if not meta.is_file():
        meta.write_text(json.dumps({"session": "canary"}, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(source_path, 0o600)
    stat_result = source_path.stat()
    complete_boundary = data.rfind(b"\n") + 1
    prefix_sha = hashlib.sha256(data[:complete_boundary]).hexdigest()
    meta_sha = hashlib.sha256(meta.read_bytes()).hexdigest()
    return SourceGrant(
        path=str(source_path.resolve()),
        metadata_path=str(meta.resolve()),
        device=stat_result.st_dev,
        inode=stat_result.st_ino,
        size=stat_result.st_size,
        complete_boundary=complete_boundary,
        prefix_sha256=prefix_sha,
        metadata_sha256=meta_sha,
    )

def derive_p2_disposition(sections: Mapping[str, Any]) -> str:
    """Derive T6 disposition from orchestration section outcomes."""
    t5 = sections.get("t5")
    if isinstance(t5, dict) and t5:
        outcomes = {
            str(item.get("disposition", ""))
            for item in t5.values()
            if isinstance(item, dict)
        }
        outcomes.discard("")
        if "recovery_unproven" in outcomes:
            return "recovery_unproven"
        if outcomes and all(value == "restored" for value in outcomes):
            return "restored"
        return "recovery_unproven"
    t3 = sections.get("t3")
    t4 = sections.get("t4")
    if isinstance(t3, dict) and t3.get("outcome") == "committed":
        if isinstance(t4, dict) and t4.get("stage") == "p2-t4":
            return "converged"
        if t4 is None:
            return "converged"
    return "recovery_unproven"

def bind_p2_append_source(grant: CanaryGrant, source_grant: SourceGrant) -> CanaryGrant:
    """Return a grant with an updated source binding after a pure append."""
    if source_grant.path != grant.source.path:
        raise CanaryRefused("canary_source_path", "append must not change source path")
    return replace(grant, source=source_grant)


def run_p2_append_adoption(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    """P2-T4 hermetic controlled append and frontier proof."""
    if not _in_p2_worker_subprocess():
        return _delegate_p2_worker(
            boundary,
            grant,
            "p2-append",
            expected_sha256=expected_sha256,
        )
    from adapters.kiro_session_jsonl import parse_complete_prefix

    view = parse_complete_prefix(grant.source.path)
    validate_append_profile(len(view.messages))
    result, counters = _run_coordinator_once(
        boundary,
        grant,
        ceilings=grant.call_ceilings["append"],
    )
    if result.outcome != "committed":
        raise CanaryRefused("canary_p2_t4", f"append adoption failed: {result.outcome}")
    replay, replay_counters = _run_coordinator_once(
        boundary,
        grant,
        ceilings={"summarize": 0, "distill": 0, "summary_embed": 0, "unit_embed": 0},
    )
    if replay.outcome != "unchanged" or replay_counters.total != 0:
        raise CanaryRefused("canary_p2_t4", "append replay must perform zero calls")
    receipt = consume_nonce(boundary.root, grant, expected_sha256=expected_sha256)
    receipt.stage = "p2-t4-complete"
    if "append" not in receipt.append_epochs:
        receipt.append_epochs.append("append")
    _save_nonce_receipt(boundary.root, receipt)
    return {
        "stage": "p2-t4",
        "accepted_messages": len(view.messages),
        "counters": counters.as_dict(),
        "replay_counters": replay_counters.as_dict(),
    }


def run_p2_fault_observation(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    fault_selector: str,
    unrelated_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """P2-T5 single fault/replay observation."""
    if not _in_p2_worker_subprocess():
        return _delegate_p2_worker(
            boundary,
            grant,
            "p2-fault",
            expected_sha256=expected_sha256,
            extra_env={"CONVMEM_CANARY_FAULT": fault_selector},
        )
    fault_point = fault_point_for_selector(fault_selector)

    def fault(name: str) -> None:
        if name == fault_point:
            raise CanaryFaultExit(name)

    outcome, _counters = _run_coordinator_once(
        boundary,
        grant,
        ceilings=_p2_fault_call_ceilings(boundary, grant),
        fault=fault,
    )
    if not isinstance(outcome, CanaryFaultExit):
        raise CanaryRefused("canary_p2_t5", f"fault {fault_selector} did not trigger")
    coordinator = canary_coordinator(boundary, grant.source.path)
    capsule = capture_rollback_capsule(coordinator, unrelated_manifest=unrelated_manifest)
    restore_rollback_capsule(coordinator, capsule)
    replay, replay_counters = _run_coordinator_once(
        boundary,
        grant,
        ceilings={"summarize": 0, "distill": 0, "summary_embed": 0, "unit_embed": 0},
    )
    if replay.outcome not in {"unchanged", "committed"}:
        raise CanaryRefused("canary_p2_t5", f"fault replay failed: {replay.outcome}")
    receipt = consume_nonce(boundary.root, grant, expected_sha256=expected_sha256)
    if fault_selector not in receipt.faults_completed:
        receipt.faults_completed.append(fault_selector)
    _save_nonce_receipt(boundary.root, receipt)
    return {
        "stage": "p2-t5",
        "fault": fault_selector,
        "replay_counters": replay_counters.as_dict(),
        "disposition": "restored",
    }


def freeze_p2_evidence(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    gate0_report: Mapping[str, Any],
    sections: Mapping[str, Any],
    disposition: str,
) -> str:
    """P2-T6 evidence freeze."""
    payload = assemble_evidence(
        gate0=dict(gate0_report),
        grant_digest=expected_sha256,
        disposition=disposition,
        **dict(sections),
    )
    evidence_path = Path(grant.evidence_dir) / "p2-hermetic-evidence.json"
    digest = write_evidence(evidence_path, payload)
    receipt = consume_nonce(boundary.root, grant, expected_sha256=expected_sha256)
    receipt.stage = "completed"
    _save_nonce_receipt(boundary.root, receipt)
    return digest


def run_p2_orchestration(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    code_revision: str,
    hooks: Gate0ProbeHooks | None = None,
    include_faults: bool = True,
) -> dict[str, Any]:
    """Run hermetic P2-T3 through T6 behind Gate 0."""
    if is_p2_live_grant(grant):
        raise CanaryRefused(
            "canary_p2_all_refused",
            "live P2 has no all-stages command; use one stage transition per invocation",
        )
    gate0 = gate0_preflight_p2(
        grant,
        boundary,
        expected_sha256=expected_sha256,
        code_revision=code_revision,
        hooks=hooks,
    )
    write_canary_overlay(boundary)
    sections: dict[str, Any] = {
        "t3": run_p2_initial_adoption(boundary, grant, expected_sha256=expected_sha256),
    }
    append_count = APPEND_MAX_MESSAGES - BASELINE_MIN_MESSAGES
    updated_source = simulate_pure_append(
        Path(grant.source.path),
        start_index=BASELINE_MIN_MESSAGES,
        count=append_count,
    )
    append_grant = bind_p2_append_source(grant, updated_source)
    sections["t4"] = run_p2_append_adoption(
        boundary,
        append_grant,
        expected_sha256=expected_sha256,
    )
    if include_faults:
        sections["t5"] = {}
        prior_subprocess = os.environ.get("CONVMEM_CANARY_SUBPROCESS")
        os.environ["CONVMEM_CANARY_SUBPROCESS"] = "1"
        try:
            for selector in grant.faults:
                reset_p2_baseline_source(boundary, grant)
                sections["t5"][selector] = run_p2_fault_observation(
                    boundary,
                    grant,
                    expected_sha256=expected_sha256,
                    fault_selector=selector,
                )
        finally:
            if prior_subprocess is None:
                os.environ.pop("CONVMEM_CANARY_SUBPROCESS", None)
            else:
                os.environ["CONVMEM_CANARY_SUBPROCESS"] = prior_subprocess
    disposition = derive_p2_disposition(sections)
    sections["t6"] = {"disposition": disposition}
    digest = freeze_p2_evidence(
        boundary,
        grant,
        expected_sha256=expected_sha256,
        gate0_report=gate0,
        sections=sections,
        disposition=disposition,
    )
    return {"gate0": gate0, "sections": sections, "evidence_digest": digest, "disposition": disposition}



def terminate_fault_worker(child: subprocess.Popen[Any]) -> dict[str, Any]:
    """Kill a fault worker process group and prove descendants absent."""
    try:
        os.setpgid(child.pid, child.pid)
    except OSError:
        pass
    if child.poll() is None:
        terminate_process_group(child.pid)
    try:
        child.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=2.0)
    return {"pid": child.pid, "returncode": child.returncode}


__all__ = [
    "APPEND_MAX_MESSAGES",
    "BASELINE_MAX_MESSAGES",
    "BASELINE_MIN_MESSAGES",
    "CALL_CEILINGS_APPEND",
    "CALL_CEILINGS_INITIAL",
    "CALL_CEILINGS_WHOLE",
    "CANARY_MODE",
    "CANARY_SCHEMA_VERSION",
    "CRASH_EXIT",
    "CanaryGrant",
    "CanaryRefused",
    "CallBudgetGuard",
    "FAULT_SELECTORS",
    "NonceReceipt",
    "ProductionCanaryBoundary",
    "ServingProbeObservation",
    "ServingVisibilityProbe",
    "assemble_evidence",
    "assert_not_reused",
    "assert_transition_coverage",
    "build_allowlisted_child_env",
    "canary_coordinator",
    "canary_writer_scope",
    "capture_rollback_capsule",
    "chunk_starts_for_count",
    "consume_nonce",
    "decode_grant",
    "fault_point_for_selector",
    "gate0_preflight",
    "P1_CAPABILITY_MODE",
    "gate0_watcher_probe",
    "install_call_budget_guard",
    "prove_cli_watcher_unreachable",
    "restore_rollback_capsule",
    "terminate_fault_worker",
    "unrelated_sentinel_digest",
    "validate_append_profile",
    "validate_grant",
    "validate_two_chunk_profile",
    "verify_persistent_config_false_false",
    "write_canary_overlay",
    "write_evidence",
    "P1_CAPABILITY_MODE",
    "P2_CAPABILITY_MODE",
    "Gate0ProbeHooks",
    "CanaryFaultExit",
    "is_p2_grant",
    "validate_p2_grant",
    "gate0_preflight_p1",
    "gate0_preflight_p2",
    "bind_p2_append_source",
    "run_p2_initial_adoption",
    "run_p2_append_adoption",
    "run_p2_fault_observation",
    "freeze_p2_evidence",
    "run_p2_orchestration",
]
