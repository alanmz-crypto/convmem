#!/usr/bin/env python3
"""Advisory locks and path-candidate helpers for exclude --purge.

Import-light module (no ingest/chroma) so ingest/inter_model can lock without cycles.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import stat
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TextIO

_tls = threading.local()


def _export_depth() -> int:
    return int(getattr(_tls, "export_depth", 0) or 0)


def source_lock_depth() -> int:
    """Current thread's source-flock nesting depth (tests/instrumentation)."""
    return _source_depth()


def export_lock_depth() -> int:
    """Current thread's export-flock nesting depth (tests/instrumentation)."""
    return _export_depth()


def index_write_lock_depth() -> int:
    """Current thread's store-wide index write lock nesting depth."""
    return int(getattr(_tls, "index_write_depth", 0) or 0)


def _source_depth() -> int:
    return int(getattr(_tls, "source_depth", 0) or 0)


def _index_write_depth() -> int:
    return int(getattr(_tls, "index_write_depth", 0) or 0)


def data_root_from_cfg(cfg: dict) -> Path:
    idx = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    for key in ("processed_log", "chroma_dir", "units_export"):
        raw = idx.get(key)
        if raw:
            return Path(str(raw)).expanduser().resolve().parent
    raise KeyError("cfg[index] lacks processed_log, chroma_dir, or units_export")


def index_write_lock_path(cfg: dict) -> Path:
    return data_root_from_cfg(cfg) / "locks" / "index_write.lock"


def index_write_lock_path_for_export(export_path: Path | str) -> Path:
    return index_write_lock_path({"index": {"units_export": str(export_path)}})


def assert_lock_ordering_ok(*, acquiring: str) -> None:
    if acquiring == "source" and _export_depth() > 0:
        raise RuntimeError(
            "lock ordering violation: cannot acquire source lock while holding export lock"
        )
    if acquiring == "source" and _index_write_depth() > 0:
        raise RuntimeError(
            "lock ordering violation: cannot acquire source lock while holding index write lock"
        )
    if acquiring == "index_write" and _export_depth() > 0:
        raise RuntimeError(
            "lock ordering violation: cannot acquire index write lock while holding export lock"
        )
    if acquiring == "index_write":
        from chroma_write_store import production_write_session_depth

        if production_write_session_depth() > 0:
            raise RuntimeError(
                "lock ordering violation: cannot acquire index write lock "
                "while holding a Chroma writer session"
            )
    if acquiring == "export" and _index_write_depth() == 0:
        raise RuntimeError(
            "lock ordering violation: cannot acquire export lock without index write lock"
        )


def require_index_write_lock_held() -> None:
    if index_write_lock_depth() == 0:
        raise RuntimeError(
            "production Chroma mutation requires the store-wide index write lock"
        )


def source_lock_dir(cfg: dict) -> Path:
    return data_root_from_cfg(cfg) / "locks" / "source"


def source_lock_path(cfg: dict, canonical_path: str) -> Path:
    path_hash = hashlib.sha256(canonical_path.encode()).hexdigest()
    return source_lock_dir(cfg) / f"{path_hash}.lock"


def export_lock_path_for_file(export_path: Path | str) -> Path:
    p = Path(export_path).expanduser().resolve()
    return p.with_suffix(p.suffix + ".lock")


def export_lock_path(cfg: dict) -> Path:
    return export_lock_path_for_file(cfg["index"]["units_export"])


def _open_private_lock(path: Path) -> TextIO:
    """Create or reopen a regular lock file with private permissions."""
    flags = os.O_RDWR | os.O_CREAT | os.O_APPEND | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise RuntimeError(f"lock path is not a regular file: {path}")
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, "a+", encoding="utf-8")
        descriptor = -1
        return handle
    finally:
        if descriptor >= 0:
            os.close(descriptor)


@contextmanager
def source_flock(cfg: dict, canonical_path: str) -> Iterator[Path]:
    assert_lock_ordering_ok(acquiring="source")
    lock = source_lock_path(cfg, canonical_path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with _open_private_lock(lock) as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        _tls.source_depth = _source_depth() + 1
        try:
            yield lock
        finally:
            _tls.source_depth = max(0, _source_depth() - 1)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _export_flock_path_inner(export_path: Path | str) -> Iterator[Path]:
    assert_lock_ordering_ok(acquiring="export")
    lock = export_lock_path_for_file(export_path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with _open_private_lock(lock) as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        _tls.export_depth = _export_depth() + 1
        try:
            yield lock
        finally:
            _tls.export_depth = max(0, _export_depth() - 1)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def index_write_flock(cfg: dict) -> Iterator[Path]:
    if _index_write_depth() == 0:
        assert_lock_ordering_ok(acquiring="index_write")
    lock = index_write_lock_path(cfg)
    lock.parent.mkdir(parents=True, exist_ok=True)
    depth_before = _index_write_depth()
    handle: TextIO | None = None
    if depth_before == 0:
        handle = _open_private_lock(lock)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    _tls.index_write_depth = depth_before + 1
    try:
        yield lock
    finally:
        _tls.index_write_depth = max(0, _index_write_depth() - 1)
        if depth_before == 0 and handle is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


@contextmanager
def index_write_flock_for_export(export_path: Path | str) -> Iterator[Path]:
    with index_write_flock({"index": {"units_export": str(export_path)}}) as lock:
        yield lock


@contextmanager
def export_flock_path(export_path: Path | str) -> Iterator[Path]:
    if _index_write_depth() == 0:
        with index_write_flock_for_export(export_path):
            with _export_flock_path_inner(export_path) as lock:
                yield lock
        return
    with _export_flock_path_inner(export_path) as lock:
        yield lock


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
