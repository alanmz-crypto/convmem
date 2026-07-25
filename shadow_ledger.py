"""Phase 0 shadow ledger: config resolution and activation baseline (no Chroma import).

Sink injection and append I/O land in later Execute tasks. This module must not
import chroma_store or open production Chroma.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SHADOW_SCHEMA_VERSION = 1
MANIFEST_VERSION = 1
HASH_RULES_VERSION = 1
COLLECTION_KNOWLEDGE_UNITS = "knowledge_units"

DEFAULT_LEDGER_PATH = "~/.local/share/convmem/shadow_ledger.jsonl"
DEFAULT_MANIFEST_PATH = "~/.local/share/convmem/shadow_activation.json"
DEFAULT_HEALTH_PATH = "~/.local/share/convmem/shadow_health.json"


def canonical_json_bytes(obj: Any) -> bytes:
    """UTF-8 canonical JSON: sorted keys, compact separators, reject NaN."""
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_canonical(obj: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def projection_state_hash(
    *,
    stable_entity_id: str,
    deleted: bool,
    document: str | None,
    metadata: Mapping[str, Any] | None,
) -> str:
    """Architecture state_hash over identity, delete flag, document, metadata."""
    payload = {
        "stable_entity_id": stable_entity_id,
        "deleted": bool(deleted),
        "document": document if not deleted else None,
        "metadata": dict(metadata or {}) if not deleted else None,
    }
    return sha256_canonical(payload)


def resolve_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


@dataclass(frozen=True)
class ShadowLedgerSettings:
    """Resolved optional [shadow_ledger] table (paths expanded)."""

    enabled: bool
    ledger_path: Path
    activation_manifest_path: Path
    health_path: Path
    table_present: bool

    @property
    def injection_eligible_config(self) -> bool:
        """True only when enabled=true; manifest still required separately."""
        return self.enabled is True


def shadow_ledger_section(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    if not cfg:
        return {}
    section = cfg.get("shadow_ledger")
    return dict(section) if isinstance(section, dict) else {}


def resolve_shadow_settings(cfg: Mapping[str, Any] | None) -> ShadowLedgerSettings:
    """Absent table and enabled=false are equivalent (no sink)."""
    section = shadow_ledger_section(cfg)
    present = bool(section)
    enabled = bool(section.get("enabled", False)) if present else False
    ledger = resolve_path(section.get("ledger_path", DEFAULT_LEDGER_PATH))
    manifest = resolve_path(
        section.get("activation_manifest_path", DEFAULT_MANIFEST_PATH)
    )
    health = resolve_path(section.get("health_path", DEFAULT_HEALTH_PATH))
    return ShadowLedgerSettings(
        enabled=enabled,
        ledger_path=ledger,
        activation_manifest_path=manifest,
        health_path=health,
        table_present=present,
    )


def ensure_private_file_mode(path: Path) -> None:
    """Best-effort chmod 0600 for shadow artifacts."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def atomic_write_json_private(path: Path, obj: Any) -> None:
    """Temp → fsync → replace → parent dir fsync; mode 0600."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    if not payload.endswith("\n"):
        payload += "\n"
    data = payload.encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        ensure_private_file_mode(path)
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def new_incomplete_manifest(
    *,
    code_commit: str,
    chroma_root: Path,
    configured_embed_model: str | None,
) -> dict[str, Any]:
    """Start a baseline build; completion_status incomplete cannot enable sink."""
    return {
        "manifest_version": MANIFEST_VERSION,
        "baseline_id": str(uuid.uuid4()),
        "completion_status": "incomplete",
        "activation_timestamp_utc": None,
        "code_commit": code_commit,
        "chroma_root": str(resolve_path(chroma_root)),
        "collection": COLLECTION_KNOWLEDGE_UNITS,
        "active_unit_count": None,
        "total_unit_count": None,
        "entity_baselines": {},
        "configured_embed_model": configured_embed_model,
        "observed_embed_model": "unknown",
        "observed_embed_dimensions": None,
        "shadow_ledger_identity": None,
        "starting_sequence": 0,
        "hash_rules_version": HASH_RULES_VERSION,
        "shadow_schema_version": SHADOW_SCHEMA_VERSION,
    }


def finalize_manifest(
    manifest: dict[str, Any],
    *,
    entity_baselines: Mapping[str, Mapping[str, Any]],
    active_unit_count: int,
    total_unit_count: int,
    observed_embed_model: str,
    observed_embed_dimensions: int | None,
    shadow_ledger_identity: str,
    activation_timestamp_utc: str | None = None,
) -> dict[str, Any]:
    out = dict(manifest)
    out["entity_baselines"] = {
        eid: dict(payload) for eid, payload in entity_baselines.items()
    }
    out["active_unit_count"] = int(active_unit_count)
    out["total_unit_count"] = int(total_unit_count)
    out["observed_embed_model"] = observed_embed_model or "unknown"
    out["observed_embed_dimensions"] = observed_embed_dimensions
    out["shadow_ledger_identity"] = shadow_ledger_identity
    out["activation_timestamp_utc"] = (
        activation_timestamp_utc
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    out["completion_status"] = "complete"
    return out


def load_manifest(path: Path) -> dict[str, Any] | None:
    path = Path(path)
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("activation manifest must be a JSON object")
    return data


def manifest_is_complete(manifest: Mapping[str, Any] | None) -> bool:
    if not manifest:
        return False
    if manifest.get("completion_status") != "complete":
        return False
    required = (
        "baseline_id",
        "activation_timestamp_utc",
        "code_commit",
        "chroma_root",
        "collection",
        "active_unit_count",
        "total_unit_count",
        "entity_baselines",
        "shadow_ledger_identity",
        "hash_rules_version",
        "shadow_schema_version",
    )
    return all(manifest.get(key) is not None for key in required)


@dataclass(frozen=True)
class SinkInjectionDecision:
    """Whether a production write factory may attach a sink (T2+)."""

    inject: bool
    reason: str


def decide_sink_injection(
    cfg: Mapping[str, Any] | None,
    *,
    chroma_dir: str | Path,
) -> SinkInjectionDecision:
    """Gate for write-store factory. T1/T2: inject only when fully validated.

    Phase 0 Execute never sets inject=True until T2 provides a sink and Ryan
    activation has produced a complete matching manifest. This function still
    encodes the refusal reasons required by T1 gates.
    """
    settings = resolve_shadow_settings(cfg)
    if not settings.injection_eligible_config:
        return SinkInjectionDecision(
            False,
            "shadow_ledger absent or enabled=false (no sink)",
        )

    root = resolve_path(chroma_dir)
    configured_root = None
    index = (cfg or {}).get("index") if cfg else None
    if isinstance(index, dict) and index.get("chroma_dir"):
        configured_root = resolve_path(index["chroma_dir"])
    if configured_root is not None and root != configured_root:
        return SinkInjectionDecision(
            False,
            f"chroma root mismatch: store={root} config={configured_root}",
        )

    try:
        manifest = load_manifest(settings.activation_manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return SinkInjectionDecision(
            False, f"activation manifest unreadable: {exc}"
        )
    if not manifest_is_complete(manifest):
        return SinkInjectionDecision(
            False,
            "enabled=true but activation manifest missing or incomplete",
        )
    assert manifest is not None
    manifest_root = resolve_path(manifest["chroma_root"])
    if manifest_root != root:
        return SinkInjectionDecision(
            False,
            f"manifest chroma_root mismatch: store={root} manifest={manifest_root}",
        )
    # Complete matching manifest: injection *eligible* for T2 sink wiring.
    # T1 has no sink implementation — callers must still pass mutation_sink=None
    # until T2 attaches one. Report eligibility without claiming a live sink.
    return SinkInjectionDecision(
        True,
        "activation contract satisfied (sink object provided by T2 factory)",
    )


def runtime_stamp(
    *,
    code_commit: str,
    chroma_root: str | Path | None,
    active_count: int | None,
    total_count: int | None,
) -> dict[str, Any]:
    """Fresh stamp for evidence; never hardcodes audit snapshot counts."""
    return {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": code_commit,
        "chroma_root": str(resolve_path(chroma_root)) if chroma_root else None,
        "active_unit_count": active_count,
        "total_unit_count": total_count,
    }
