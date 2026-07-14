#!/usr/bin/env python3
"""Exclude --purge: per-source + export locks and path-candidate matching.

Design A (ARCHITECTURE-exclude-source-purge.md): source flock serializes
purge vs same-source ingest; export flock serializes all knowledge_units.jsonl
mutations. Never hold either lock across parse/LLM/embed/network work.
"""

from __future__ import annotations

import json
import fcntl
import hashlib
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


# Thread-local lock depth for ordering assertions (N9).
_tls = threading.local()


def _export_depth() -> int:
    return int(getattr(_tls, "export_depth", 0) or 0)


def _source_depth() -> int:
    return int(getattr(_tls, "source_depth", 0) or 0)


def assert_lock_ordering_ok(*, acquiring: str) -> None:
    """Raise if acquiring would violate source-then-export ordering.

    Allowed: source alone, export alone, source then export.
    Forbidden: export then source (hold export while acquiring source).
    """
    if acquiring == "source" and _export_depth() > 0:
        raise RuntimeError(
            "lock ordering violation: cannot acquire source lock while holding export lock"
        )


def source_lock_dir(cfg: dict) -> Path:
    """Lock directory derived from configured data root (parent of processed_log)."""
    data_root = Path(cfg["index"]["processed_log"]).expanduser().resolve().parent
    return data_root / "locks" / "source"


def source_lock_path(cfg: dict, canonical_path: str) -> Path:
    """Per-source lock file. Identity = SHA-256 of canonical path."""
    path_hash = hashlib.sha256(canonical_path.encode()).hexdigest()
    return source_lock_dir(cfg) / f"{path_hash}.lock"


def export_lock_path_for_file(export_path: Path | str) -> Path:
    """Export lock sidecar for a knowledge_units.jsonl path."""
    p = Path(export_path).expanduser().resolve()
    return p.with_suffix(p.suffix + ".lock")


def export_lock_path(cfg: dict) -> Path:
    """Export lock sidecar of configured units_export."""
    return export_lock_path_for_file(cfg["index"]["units_export"])


@contextmanager
def source_flock(cfg: dict, canonical_path: str) -> Iterator[Path]:
    """Exclusive advisory lock for one source path (Lock 1)."""
    assert_lock_ordering_ok(acquiring="source")
    lock = source_lock_path(cfg, canonical_path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        _tls.source_depth = _source_depth() + 1
        try:
            yield lock
        finally:
            _tls.source_depth = max(0, _source_depth() - 1)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def export_flock_path(export_path: Path | str) -> Iterator[Path]:
    """Exclusive advisory lock for a JSONL export path (Lock 2)."""
    lock = export_lock_path_for_file(export_path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        _tls.export_depth = _export_depth() + 1
        try:
            yield lock
        finally:
            _tls.export_depth = max(0, _export_depth() - 1)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def export_flock(cfg: dict) -> Iterator[Path]:
    """Exclusive advisory lock for configured units_export (Lock 2)."""
    with export_flock_path(cfg["index"]["units_export"]) as lock:
        yield lock


def build_path_candidates(target: str) -> list[str]:
    """Exact path candidates for all sink queries (canonical + expanduser-only).

    Does NOT canonicalize empty, relative, or non-filesystem prefixes into cwd.
    """
    if not target or not str(target).strip():
        return []
    s = str(target).strip()
    # Non-filesystem / relative markers are never purge targets as CLI input
    # for matching stored values — but we still build candidates for absolute paths.
    if not s.startswith(("/", "~")):
        return []
    raw = str(Path(s).expanduser())
    try:
        canonical = str(Path(s).expanduser().resolve())
    except OSError:
        canonical = raw
    return list(dict.fromkeys([canonical, raw]))


def line_matches_purge(rec: dict[str, Any], candidates: list[str]) -> bool:
    """Exact-string match of stored source_path against candidates."""
    sp = rec.get("source_path", "")
    if not isinstance(sp, str) or not sp or not sp.startswith("/"):
        return False
    return sp in candidates


def purged_exclusion_key(canonical_path: str) -> str:
    """Synthetic processed.json key when the source file is missing."""
    digest = hashlib.sha256(canonical_path.encode()).hexdigest()
    return f"purged:{digest}"



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
) -> int:
    """Rewrite JSONL removing matching source lines. Returns lines removed.

    Acquires export lock unless ``already_locked`` (caller holds export_flock).
    Fail-closed on malformed lines (original file unchanged).
    """
    path = Path(export_path)

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
        tmp.replace(path)
        return removed

    if already_locked:
        return _rewrite()
    with export_flock(cfg):
        return _rewrite()


def count_chroma_for_source(store: Any, candidates: list[str]) -> dict[str, int]:
    """Count units and summaries matching any candidate source_path."""
    units = 0
    summaries = 0
    for candidate in candidates:
        ures = store._collection("knowledge_units").get(  # noqa: SLF001
            where={"source_path": candidate}, include=[]
        )
        units += len(ures.get("ids") or [])
        sres = store._collection("conversation_summaries").get(  # noqa: SLF001
            where={"source_path": candidate}, include=[]
        )
        summaries += len(sres.get("ids") or [])
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
class PurgeResult:
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
    """Mechanically read-only purge preview (no locks, no mutations)."""
    candidates = build_path_candidates(target)
    if not candidates and target:
        # Absolute missing path: still form candidates from expanduser/resolve
        raw = str(Path(target).expanduser())
        try:
            canonical = str(Path(target).expanduser().resolve())
        except OSError:
            canonical = raw
        candidates = list(dict.fromkeys([canonical, raw]))
    canonical = candidates[0] if candidates else str(Path(target).expanduser())
    chroma_dir = cfg["index"]["chroma_dir"]
    export = Path(cfg["index"]["units_export"]).expanduser()
    counts = _count_chroma_readonly(chroma_dir, candidates)
    jsonl_n = 0
    if export.is_file():
        # Read-only scan; treat malformed as count-abort? Preview should not mutate;
        # skip malformed lines for preview counts (count only valid objects).
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


def mark_purge_exclusion(cfg: dict, canonical_path: str, reason: str) -> str:
    """Write exclusion marker (processed flock). Returns exclusion key used."""
    from datetime import datetime, timezone

    from ingest import exclude_processed_path, mutate_processed, sha256_file

    processed_path = cfg["index"]["processed_log"]
    reason_text = reason or "purge"
    if not reason_text.startswith("purge"):
        reason_text = f"purge: {reason_text}"
    path_obj = Path(canonical_path)
    if path_obj.is_file():
        file_hash = sha256_file(canonical_path)
        exclude_processed_path(
            processed_path, canonical_path, file_hash, reason=reason_text
        )
        # Stamp purged_at
        def stamp(data: dict) -> None:
            entry = data.get(file_hash)
            if isinstance(entry, dict):
                entry["purged_at"] = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )

        mutate_processed(processed_path, stamp)
        return file_hash

    key = purged_exclusion_key(canonical_path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def mutator(data: dict) -> None:
        data[key] = {
            "path": canonical_path,
            "excluded": True,
            "exclude_reason": reason_text,
            "purged_at": now,
        }

    mutate_processed(processed_path, mutator)
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
        raw = str(Path(target).expanduser())
        try:
            canonical = str(Path(target).expanduser().resolve())
        except OSError:
            canonical = raw
        candidates = list(dict.fromkeys([canonical, raw]))
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
            for candidate in candidates:
                units_deleted += int(store.delete_units_for_source(candidate))
            _hook("after_units")  # F3
            for candidate in candidates:
                summaries_deleted += int(store.delete_summaries_for_source(candidate))
            _hook("after_summaries")  # F4
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
                        cfg, export, candidates, already_locked=True
                    )
                    _hook("after_jsonl_rewrite")  # F7 (rename done)
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
