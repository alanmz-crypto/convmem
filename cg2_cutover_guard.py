"""Low-level first-canary-open guard substrate for CG-2 Design A.

Non-serving evidence that blocks ordinary forward promotion while a first-canary
window is open.  D3 owns orchestration; this module provides immutable
publication, validation, and path binding only.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from atomic_files import atomic_write_json
from file_generation_contract import (
    canonical_hash,
    owner_digest,
    validate_payload_hash,
)

GUARD_SCHEMA = "convmem/cg2-first-canary-open-guard-v1"


class CutoverGuardError(RuntimeError):
    """First-canary guard publication or validation refused."""


def canary_guard_path(generation_root: str | Path, owner_digest_value: str) -> Path:
    return Path(generation_root) / "active" / f"{owner_digest_value}.canary_guard.json"


def build_canary_open_guard(
    *,
    owner_key: str,
    canary_generation_id: str,
    rollback_baseline_generation_id: str,
    published_at: str,
) -> dict[str, Any]:
    if not str(canary_generation_id or "").strip():
        raise CutoverGuardError("canary generation id is required")
    if not str(rollback_baseline_generation_id or "").strip():
        raise CutoverGuardError("rollback baseline generation id is required")
    guard = {
        "schema": GUARD_SCHEMA,
        "owner_key": owner_key,
        "owner_digest": owner_digest(str(owner_key)),
        "canary_generation_id": str(canary_generation_id),
        "rollback_baseline_generation_id": str(rollback_baseline_generation_id),
        "published_at": published_at,
    }
    guard["guard_payload_hash"] = canonical_hash(
        {key: guard[key] for key in sorted(guard) if key != "guard_payload_hash"}
    )
    validate_canary_open_guard(guard)
    return guard


def validate_canary_open_guard(guard: Mapping[str, Any]) -> None:
    if guard.get("schema") != GUARD_SCHEMA:
        raise CutoverGuardError("unsupported first-canary guard schema")
    if guard.get("owner_digest") != owner_digest(str(guard.get("owner_key", ""))):
        raise CutoverGuardError("guard owner digest mismatch")
    for field in (
        "canary_generation_id",
        "rollback_baseline_generation_id",
        "published_at",
    ):
        if not isinstance(guard.get(field), str) or not str(guard[field]).strip():
            raise CutoverGuardError(f"guard missing {field}")
    validate_payload_hash(dict(guard), "guard_payload_hash")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CutoverGuardError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CutoverGuardError(f"{path} is not a JSON object")
    return value


def publish_canary_open_guard(
    generation_root: str | Path,
    *,
    owner_key: str,
    canary_generation_id: str,
    rollback_baseline_generation_id: str,
    published_at: str,
) -> Path:
    """Durably publish an open first-canary guard; idempotent for identical bytes."""

    digest = owner_digest(owner_key)
    path = canary_guard_path(generation_root, digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_canary_open_guard(
        owner_key=owner_key,
        canary_generation_id=canary_generation_id,
        rollback_baseline_generation_id=rollback_baseline_generation_id,
        published_at=published_at,
    )
    if path.exists():
        current = _read_json(path)
        if current != payload:
            raise CutoverGuardError(f"immutable first-canary guard collision at {path}")
        return path
    atomic_write_json(path, payload)
    reread = _read_json(path)
    if reread != payload:
        raise CutoverGuardError("published first-canary guard reread mismatch")
    return path


def read_canary_open_guard(
    generation_root: str | Path, owner_digest_value: str
) -> dict[str, Any] | None:
    path = canary_guard_path(generation_root, owner_digest_value)
    if not path.exists():
        return None
    guard = _read_json(path)
    validate_canary_open_guard(guard)
    if str(guard["owner_digest"]) != owner_digest_value:
        raise CutoverGuardError("guard stored under wrong owner digest")
    return guard
