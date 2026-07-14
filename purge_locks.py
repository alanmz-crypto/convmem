#!/usr/bin/env python3
"""Advisory locks and path-candidate helpers for exclude --purge.

Import-light module (no ingest/chroma) so ingest/inter_model can lock without cycles.
"""

from __future__ import annotations

import fcntl
import hashlib
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

_tls = threading.local()


def _export_depth() -> int:
    return int(getattr(_tls, "export_depth", 0) or 0)


def _source_depth() -> int:
    return int(getattr(_tls, "source_depth", 0) or 0)


def assert_lock_ordering_ok(*, acquiring: str) -> None:
    if acquiring == "source" and _export_depth() > 0:
        raise RuntimeError(
            "lock ordering violation: cannot acquire source lock while holding export lock"
        )


def source_lock_dir(cfg: dict) -> Path:
    data_root = Path(cfg["index"]["processed_log"]).expanduser().resolve().parent
    return data_root / "locks" / "source"


def source_lock_path(cfg: dict, canonical_path: str) -> Path:
    path_hash = hashlib.sha256(canonical_path.encode()).hexdigest()
    return source_lock_dir(cfg) / f"{path_hash}.lock"


def export_lock_path_for_file(export_path: Path | str) -> Path:
    p = Path(export_path).expanduser().resolve()
    return p.with_suffix(p.suffix + ".lock")


def export_lock_path(cfg: dict) -> Path:
    return export_lock_path_for_file(cfg["index"]["units_export"])


@contextmanager
def source_flock(cfg: dict, canonical_path: str) -> Iterator[Path]:
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
    with export_flock_path(cfg["index"]["units_export"]) as lock:
        yield lock


def build_path_candidates(target: str) -> list[str]:
    if not target or not str(target).strip():
        return []
    s = str(target).strip()
    if not s.startswith(("/", "~")):
        return []
    raw = str(Path(s).expanduser())
    try:
        canonical = str(Path(s).expanduser().resolve())
    except OSError:
        canonical = raw
    return list(dict.fromkeys([canonical, raw]))


def line_matches_purge(rec: dict[str, Any], candidates: list[str]) -> bool:
    sp = rec.get("source_path", "")
    if not isinstance(sp, str) or not sp or not sp.startswith("/"):
        return False
    return sp in candidates


def purged_exclusion_key(canonical_path: str) -> str:
    digest = hashlib.sha256(canonical_path.encode()).hexdigest()
    return f"purged:{digest}"
