#!/usr/bin/env python3
"""Exclude --purge sinks and orchestrator (preview/execute).

Locks and path-candidate matching live in ``purge_locks`` (import-light).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from purge_locks import (
    build_path_candidates,
    export_flock,
    line_matches_purge,
    purged_exclusion_key,
    source_flock,
)

# Re-exports for stable public API / tests.
import purge_locks as _purge_locks

assert_lock_ordering_ok = _purge_locks.assert_lock_ordering_ok
export_flock_path = _purge_locks.export_flock_path
export_lock_path = _purge_locks.export_lock_path
source_lock_dir = _purge_locks.source_lock_dir
source_lock_path = _purge_locks.source_lock_path

class MalformedJsonlError(ValueError):
    """JSONL contains a malformed line — fail closed, do not rewrite."""


def count_jsonl_lines_for_source(export_path: Path | str, candidates: list[str]) -> int:
    """Count JSONL records whose source_path is in candidates (read-only)."""
    path = Path(export_path)
    if not path.is_file():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rec = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise MalformedJsonlError(f"malformed JSONL line: {exc}") from exc
        if not isinstance(rec, dict):
            raise MalformedJsonlError("malformed JSONL line: not an object")
        if line_matches_purge(rec, candidates):
            n += 1
    return n


def purge_source_from_jsonl(
    cfg: dict,
    export_path: Path | str,
    candidates: list[str],
    *,
    already_locked: bool = False,
    _hooks: dict | None = None,
) -> int:
    """Rewrite JSONL removing matching source lines. Returns lines removed.

    Acquires export lock unless ``already_locked`` (caller holds export_flock).
    Fail-closed on malformed lines (original file unchanged).
    """
    path = Path(export_path)
    hooks = _hooks or {}

    def _hook(name: str) -> None:
        fn = hooks.get(name)
        if callable(fn):
            fn()

    def _rewrite() -> int:
        if not path.is_file():
            return 0
        kept: list[str] = []
        removed = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise MalformedJsonlError(f"malformed JSONL line: {exc}") from exc
            if not isinstance(rec, dict):
                raise MalformedJsonlError("malformed JSONL line: not an object")
            if line_matches_purge(rec, candidates):
                removed += 1
            else:
                kept.append(stripped)
        if removed == 0:
            return 0
        tmp = path.with_suffix(path.suffix + ".purge.tmp")
        tmp.write_text(("\n".join(kept) + ("\n" if kept else "")), encoding="utf-8")
        _hook("after_jsonl_tmp_write")  # F6: tmp written, rename not reached
        tmp.replace(path)
        _hook("after_jsonl_rename")  # F7
        return removed

    if already_locked:
        return _rewrite()
    with export_flock(cfg):
        return _rewrite()


def count_chroma_for_source(store: Any, candidates: list[str]) -> dict[str, int]:
    """Count units and summaries matching any candidate source_path."""
    from chroma_store import SUMMARIES, UNITS

    units = 0
    summaries = 0
    for candidate in candidates:
        units += int(store.count_for_source_path(UNITS, candidate))
        summaries += int(store.count_for_source_path(SUMMARIES, candidate))
    return {"units": units, "summaries": summaries}


def purge_source_from_chroma(store: Any, candidates: list[str]) -> dict[str, int]:
    """Hard-delete units and summaries for each path candidate.

    Calls invalidate_superseded_cache after unit deletions.
    """
    from chroma_store import invalidate_superseded_cache

    units_deleted = 0
    summaries_deleted = 0
    for candidate in candidates:
        units_deleted += int(store.delete_units_for_source(candidate))
        summaries_deleted += int(store.delete_summaries_for_source(candidate))
    if units_deleted:
        invalidate_superseded_cache(store.chroma_dir)
    return {
        "units_deleted": units_deleted,
        "summaries_deleted": summaries_deleted,
    }




@dataclass
class PurgePreview:
    canonical_path: str
    candidates: list[str]
    units: int
    summaries: int
    jsonl_lines: int


@dataclass
class PurgeResult:  # pylint: disable=too-many-instance-attributes
    exit_code: int
    canonical_path: str
    candidates: list[str]
    units_deleted: int = 0
    summaries_deleted: int = 0
    jsonl_removed: int = 0
    message: str = ""
    exclusion_key: str = ""


def _count_chroma_readonly(chroma_dir: Path | str, candidates: list[str]) -> dict[str, int]:
    """Count matching units/summaries via readonly sqlite (no PersistentClient)."""
    from chroma_readonly import collection_metadata_rows
    from chroma_store import SUMMARIES, UNITS

    db = Path(chroma_dir).expanduser() / "chroma.sqlite3"
    if not db.is_file():
        return {"units": 0, "summaries": 0}
    cand = set(candidates)
    units = 0
    summaries = 0
    try:
        for meta in collection_metadata_rows(chroma_dir, UNITS):
            sp = meta.get("source_path") or ""
            if isinstance(sp, str) and sp in cand:
                units += 1
        for meta in collection_metadata_rows(chroma_dir, SUMMARIES):
            sp = meta.get("source_path") or ""
            if isinstance(sp, str) and sp in cand:
                summaries += 1
    except FileNotFoundError:
        return {"units": 0, "summaries": 0}
    return {"units": units, "summaries": summaries}


def preview_purge(cfg: dict, target: str) -> PurgePreview:
    """Mechanically read-only purge preview (no locks, no mutations).

    Rejects empty/relative/non-filesystem targets (no candidate rebuild).
    """
    candidates = build_path_candidates(target)
    if not candidates:
        raise ValueError(
            "purge target must be an absolute or home-qualified filesystem path"
        )
    canonical = candidates[0]
    chroma_dir = cfg["index"]["chroma_dir"]
    export = Path(cfg["index"]["units_export"]).expanduser()
    counts = _count_chroma_readonly(chroma_dir, candidates)
    jsonl_n = 0
    if export.is_file():
        # Read-only scan; skip malformed lines for preview counts.
        for line in export.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and line_matches_purge(rec, candidates):
                jsonl_n += 1
    return PurgePreview(
        canonical_path=canonical,
        candidates=candidates,
        units=counts["units"],
        summaries=counts["summaries"],
        jsonl_lines=jsonl_n,
    )



def undo_exclude_source(cfg: dict, target: str) -> bool:
    """Clear exclusion for target under the same per-source flock as purge.

    Serializes with ``execute_purge`` so undo cannot remove the fence while a
    purge for that source is still in progress. ``target`` must already be
    absolute or home-qualified (CLI resolves existing relative paths).
    """
    from ingest import undo_exclude_processed_path

    candidates = build_path_candidates(target)
    if not candidates:
        return False
    canonical = candidates[0]
    processed_path = cfg["index"]["processed_log"]
    with source_flock(cfg, canonical):
        return undo_exclude_processed_path(processed_path, canonical)


def mark_purge_exclusion(cfg: dict, canonical_path: str, reason: str) -> str:
    """Write exclusion marker (processed flock). Returns exclusion key used.

    Clears prior same-path markers and stamps ``purged_at`` atomically via
    ``exclude_processed_path`` (content-hash or synthetic ``purged:<sha>`` key).
    """
    from datetime import datetime, timezone

    from ingest import exclude_processed_path, sha256_file

    processed_path = cfg["index"]["processed_log"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if Path(canonical_path).is_file():
        key = sha256_file(canonical_path)
    else:
        key = purged_exclusion_key(canonical_path)
    if reason:
        reason_text = reason if reason.startswith("purge") else f"purge: {reason}"
    else:
        reason_text = "purge"
    # Pass explicit reason_text so marker always has a purge reason; carry is
    # unused when reason_text is non-empty (same as soft-exclude with reason).
    exclude_processed_path(
        processed_path,
        canonical_path,
        key,
        reason=reason_text,
        purged_at=now,
    )
    return key


def execute_purge(
    cfg: dict,
    target: str,
    reason: str = "",
    *,
    _hooks: dict | None = None,
) -> PurgeResult:
    """Mutating purge orchestrator under source lock.

    ``_hooks`` is for failure injection in tests (optional callables keyed by
    F1–F10 stage names that raise to simulate crash).
    """
    from chroma_store import ChromaStore

    hooks = _hooks or {}
    candidates = build_path_candidates(target)
    if not candidates:
        return PurgeResult(
            exit_code=1,
            canonical_path=str(target or ""),
            candidates=[],
            message=(
                "purge target must be an absolute or home-qualified filesystem path"
            ),
        )
    canonical = candidates[0]
    export = Path(cfg["index"]["units_export"]).expanduser()
    chroma_dir = str(Path(cfg["index"]["chroma_dir"]).expanduser())

    def _hook(name: str) -> None:
        fn = hooks.get(name)
        if callable(fn):
            fn()

    with source_flock(cfg, canonical):
        _hook("before_exclusion")  # F1
        exclusion_key = mark_purge_exclusion(cfg, canonical, reason)
        _hook("after_exclusion")  # F2

        store = ChromaStore(chroma_dir)
        try:
            units_deleted = 0
            summaries_deleted = 0
            if hooks.get("force_chroma_locked"):
                return PurgeResult(
                    exit_code=1,
                    canonical_path=canonical,
                    candidates=candidates,
                    units_deleted=units_deleted,
                    summaries_deleted=summaries_deleted,
                    jsonl_removed=0,
                    message="Chroma locked: injected",
                    exclusion_key=exclusion_key,
                )
            try:
                for candidate in candidates:
                    units_deleted += int(store.delete_units_for_source(candidate))
                _hook("after_units")  # F3
                for candidate in candidates:
                    summaries_deleted += int(
                        store.delete_summaries_for_source(candidate)
                    )
                _hook("after_summaries")  # F4
            except Exception as exc:  # noqa: BLE001 — surface locked/IO for retry
                if "database is locked" in str(exc).lower():
                    return PurgeResult(
                        exit_code=1,
                        canonical_path=canonical,
                        candidates=candidates,
                        units_deleted=units_deleted,
                        summaries_deleted=summaries_deleted,
                        jsonl_removed=0,
                        message=f"Chroma locked: {exc}",
                        exclusion_key=exclusion_key,
                    )
                raise
            if units_deleted:
                from chroma_store import invalidate_superseded_cache

                invalidate_superseded_cache(store.chroma_dir)

            jsonl_removed = 0
            remaining_jsonl = 0
            _hook("before_export_lock")
            try:
                with export_flock(cfg):
                    _hook("after_export_lock")  # F5
                    jsonl_removed = purge_source_from_jsonl(
                        cfg,
                        export,
                        candidates,
                        already_locked=True,
                        _hooks=hooks,
                    )
                    _hook("after_jsonl_rewrite")  # alias after rename
                    remaining_jsonl = count_jsonl_lines_for_source(export, candidates)
            except MalformedJsonlError as exc:
                return PurgeResult(
                    exit_code=1,
                    canonical_path=canonical,
                    candidates=candidates,
                    units_deleted=units_deleted,
                    summaries_deleted=summaries_deleted,
                    jsonl_removed=0,
                    message=f"JSONL purge aborted: {exc}",
                    exclusion_key=exclusion_key,
                )

            _hook("before_postcondition")
            remaining = count_chroma_for_source(store, candidates)
            # F8 inject residual
            if hooks.get("inject_residual"):
                remaining = {"units": 1, "summaries": 0}

            total = remaining["units"] + remaining["summaries"] + remaining_jsonl
            if total > 0:
                return PurgeResult(
                    exit_code=1,
                    canonical_path=canonical,
                    candidates=candidates,
                    units_deleted=units_deleted,
                    summaries_deleted=summaries_deleted,
                    jsonl_removed=jsonl_removed,
                    message=(
                        "postcondition failed: residual rows "
                        f"units={remaining['units']} summaries={remaining['summaries']} "
                        f"jsonl={remaining_jsonl}"
                    ),
                    exclusion_key=exclusion_key,
                )
            return PurgeResult(
                exit_code=0,
                canonical_path=canonical,
                candidates=candidates,
                units_deleted=units_deleted,
                summaries_deleted=summaries_deleted,
                jsonl_removed=jsonl_removed,
                message="purge ok",
                exclusion_key=exclusion_key,
            )
        finally:
            store.close()
