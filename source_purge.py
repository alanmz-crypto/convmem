#!/usr/bin/env python3
"""Exclude --purge: per-source + export locks and path-candidate matching.

Design A (ARCHITECTURE-exclude-source-purge.md): source flock serializes
purge vs same-source ingest; export flock serializes all knowledge_units.jsonl
mutations. Never hold either lock across parse/LLM/embed/network work.
"""

from __future__ import annotations

import fcntl
import hashlib
import threading
from contextlib import contextmanager
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


def export_lock_path(cfg: dict) -> Path:
    """Export lock sidecar of configured units_export."""
    export_path = Path(cfg["index"]["units_export"]).expanduser().resolve()
    return export_path.with_suffix(export_path.suffix + ".lock")


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
def export_flock(cfg: dict) -> Iterator[Path]:
    """Exclusive advisory lock for knowledge_units.jsonl mutations (Lock 2)."""
    lock = export_lock_path(cfg)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        _tls.export_depth = _export_depth() + 1
        try:
            yield lock
        finally:
            _tls.export_depth = max(0, _export_depth() - 1)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
