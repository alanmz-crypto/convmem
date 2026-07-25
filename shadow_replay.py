"""Disposable Phase 0 shadow replay into a marked temporary Chroma root."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

from shadow_ledger import projection_state_hash, resolve_path

REPLAY_MARKER_NAME = ".convmem_shadow_replay_ok"


class ReplayTargetError(ValueError):
    """Raised when the disposable root is unsafe."""


def iter_shadow_events(ledger_path: Path) -> Iterator[dict[str, Any]]:
    path = Path(ledger_path)
    if not path.is_file():
        return
    with open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"corrupt shadow record at line {lineno}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"non-object shadow record at line {lineno}")
            yield obj


def reduce_final_states(
    events: Iterator[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int]:
    """Apply first valid event_id; count later duplicates; keep last state per entity."""
    seen_ids: set[str] = set()
    final: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for event in events:
        eid = str(event.get("event_id") or "")
        if eid and eid in seen_ids:
            duplicates += 1
            continue
        if eid:
            seen_ids.add(eid)
        entity = str(event.get("stable_entity_id") or "")
        if not entity:
            continue
        final[entity] = event
    return final, duplicates


def assert_safe_replay_root(
    target: Path,
    *,
    production_chroma_root: Path,
) -> Path:
    """Refuse production root, parent, child, symlink alias, nonempty unmarked."""
    target = Path(target)
    prod = resolve_path(production_chroma_root)
    # Resolve without requiring target to exist yet.
    try:
        resolved = target.resolve()
    except OSError as exc:
        raise ReplayTargetError(str(exc)) from exc
    if resolved == prod:
        raise ReplayTargetError("refuse production chroma root")
    if resolved in prod.parents:
        raise ReplayTargetError("refuse parent of production chroma root")
    try:
        resolved.relative_to(prod)
        raise ReplayTargetError("refuse child of production chroma root")
    except ValueError:
        pass
    if target.exists() or resolved.exists():
        check = resolved if resolved.exists() else target
        if check.is_symlink():
            raise ReplayTargetError("refuse symlink replay target")
        if any(check.iterdir()):
            marker = check / REPLAY_MARKER_NAME
            if not marker.is_file():
                raise ReplayTargetError("refuse nonempty unmarked replay target")
    return resolved


def prepare_replay_root(
    target: Path, *, production_chroma_root: Path
) -> Path:
    root = assert_safe_replay_root(
        target, production_chroma_root=production_chroma_root
    )
    root.mkdir(parents=True, exist_ok=True)
    marker = root / REPLAY_MARKER_NAME
    if not marker.exists():
        marker.write_text("convmem shadow replay disposable root\n", encoding="utf-8")
        os.chmod(marker, 0o600)
    return root


def compare_touched(
    *,
    shadow_final: dict[str, dict[str, Any]],
    chroma_units: dict[str, dict[str, Any]],
    touched_ids: set[str],
) -> list[dict[str, Any]]:
    """Two-level comparison categories for touched IDs."""
    findings: list[dict[str, Any]] = []
    for eid in sorted(touched_ids):
        s = shadow_final.get(eid)
        c = chroma_units.get(eid)
        if s is None and c is not None:
            findings.append({"category": "missing-in-shadow", "id": eid})
            continue
        if s is not None and c is None:
            post = s.get("post_state") or {}
            if post.get("deleted"):
                continue
            findings.append({"category": "missing-in-Chroma", "id": eid})
            continue
        if s is None and c is None:
            continue
        assert s is not None and c is not None
        post = s.get("post_state") or {}
        deleted = bool(post.get("deleted"))
        c_doc = c.get("document")
        c_meta = c.get("metadata") or {}
        c_hash = projection_state_hash(
            stable_entity_id=eid,
            deleted=False,
            document=c_doc,
            metadata=c_meta,
        )
        if deleted:
            findings.append({"category": "extra final state", "id": eid})
            continue
        if s.get("state_hash") != c_hash:
            findings.append({"category": "state-hash mismatch", "id": eid})
        if s.get("document_hash") and s.get("document_hash") != __import__(
            "shadow_ledger"
        ).sha256_canonical(c_doc):
            findings.append({"category": "projection mismatch", "id": eid})
        s_model = s.get("embed_model") or "unknown"
        c_model = c_meta.get("embed_model") or "unknown"
        if s_model == "unknown" or c_model == "unknown":
            if s_model != c_model:
                findings.append({"category": "UNVERIFIABLE", "id": eid})
    return findings
