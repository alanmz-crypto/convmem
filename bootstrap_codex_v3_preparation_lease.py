"""Source preparation lease for Codex bootstrap v3 (Arc #286 T3)."""

from __future__ import annotations

import contextvars
import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from bootstrap_codex_v2_owner import require_owner_lock
from bootstrap_safety import BootstrapGrantError

SOURCE_WRITER_BUSY_CODE = "source_writer_busy"
_PREP_LEASE_NAME = ".bootstrap_v3_source_prep.flock"
_LEGACY_PREP_DEPTH = contextvars.ContextVar("bootstrap_v3_legacy_prep_depth", default=0)


class BootstrapPreparationLeaseError(BootstrapGrantError):
    """Preparation lease busy or ordering violation."""


def preparation_lease_path(state_dir: Path) -> Path:
    return state_dir / _PREP_LEASE_NAME


@contextmanager
def bootstrap_exclusive_preparation_lease(state_dir: Path) -> Iterator[None]:
    require_owner_lock()
    state_dir.mkdir(parents=True, exist_ok=True)
    path = preparation_lease_path(state_dir)
    handle = path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BootstrapPreparationLeaseError(SOURCE_WRITER_BUSY_CODE) from exc
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


@contextmanager
def legacy_shared_preparation_lease(state_dir: Path) -> Iterator[None]:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = preparation_lease_path(state_dir)
    handle = path.open("a+", encoding="utf-8")
    depth_token = _LEGACY_PREP_DEPTH.set(_LEGACY_PREP_DEPTH.get() + 1)
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        _LEGACY_PREP_DEPTH.reset(depth_token)
        handle.close()


def legacy_preparation_held() -> bool:
    return _LEGACY_PREP_DEPTH.get() > 0
