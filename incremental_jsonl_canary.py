"""One-shot production-canary boundary for incremental Kiro JSONL.

This module is canary-only: it is not registered in the normal CLI or watcher.
P1 uses synthetic sources and temporary roots; P2 requires a separate grant.
"""

# pylint: disable=too-many-lines,too-many-locals,too-many-branches,too-many-statements
# pylint: disable=too-many-instance-attributes,duplicate-code

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import signal
import socket
import stat
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, TypeVar

from incremental_jsonl import (
    DURABLE_TRANSITIONS,
    CallCounters,
    IncrementalJsonlCoordinator,
    frontier_start,
)
from incremental_jsonl_isolation import (
    IsolationBoundary,
    IsolationViolation,
    SourceAdvisoryLock,
    create_fresh_root,
    install_network_denial,
    install_service_denial,
    known_production_roots,
    terminate_process_group,
)

CANARY_SCHEMA_VERSION = 1
CANARY_MODE = "jsonl-production-canary-v1"
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

    def to_payload(self) -> dict[str, Any]:
        return {
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
    unknown = set(payload) - _GRANT_REQUIRED_TOP
    if unknown:
        raise CanaryRefused(
            "canary_grant_unknown_field",
            f"unknown grant fields: {sorted(unknown)}",
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
    )


def validate_grant(
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    code_revision: str,
    forbidden_roots: tuple[Path, ...] | None = None,
) -> None:
    """Fail-closed grant validation before any writer construction."""
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
        for role, path in role_map.items():
            _ = role
            if not path.is_absolute():
                raise CanaryRefused("canary_boundary_path", f"resource must be absolute: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
        evidence = Path(grant.evidence_dir)
        evidence.mkdir(parents=True, exist_ok=True)
        os.chmod(evidence, 0o700)
        return cls(root=root_path, token=token, grant=grant, forbidden_roots=forbidden)

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
        allowed = {Path(item.path).resolve(strict=False) for item in self.grant.resources}
        allowed.add(self.root.resolve(strict=False))
        if not any(_is_relative_to(resolved, base) or resolved == base for base in allowed):
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


def gate0_preflight(
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
        "watcher": watcher,
        "grant_digest": expected_sha256,
        "nonce": grant.nonce,
        "overlay_digest": grant.config_overlay_digest,
    }


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
    )

    def summarize(text, **_kwargs):
        guard.record("summarize")
        return original[0](text, **_kwargs)

    def distill(text, **_kwargs):
        guard.record("distill")
        return original[1](text, **_kwargs)

    def embed(text, **_kwargs):
        kind = "summary_embed" if len(text) < 400 else "unit_embed"
        guard.record(kind)
        return original[2](text, **_kwargs)

    ingest.summarize = summarize
    ingest.distill = distill
    ingest.ollama_embed = embed
    try:
        yield guard
    finally:
        ingest.summarize = original[0]
        ingest.distill = original[1]
        ingest.ollama_embed = original[2]


def capture_rollback_capsule(
    coordinator: IncrementalJsonlCoordinator,
    *,
    unrelated_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Capture a source-scoped rollback capsule with optional unrelated census."""
    rollback = coordinator._snapshot_before_images()  # noqa: SLF001
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
    coordinator._restore_before_images(dict(capsule["rollback"]))  # noqa: SLF001


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
            summaries = self.repo._legacy_store.ids_for_source(SUMMARIES, self.source_path)  # noqa: SLF001
            units = self.repo._legacy_store.ids_for_source(UNITS, self.source_path)  # noqa: SLF001
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
    "capture_rollback_capsule",
    "chunk_starts_for_count",
    "consume_nonce",
    "decode_grant",
    "fault_point_for_selector",
    "gate0_preflight",
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
]
