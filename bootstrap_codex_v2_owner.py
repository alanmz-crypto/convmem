"""Owner claim-lock context for Codex bootstrap v2 (T2)."""

from __future__ import annotations

import contextvars
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from incremental_jsonl_isolation import IsolationBoundary, IsolationViolation, SourceAdvisoryLock

_OWNER_DEPTH = contextvars.ContextVar("bootstrap_v2_owner_depth", default=0)
_SOURCE_LOCK_HELD = contextvars.ContextVar("bootstrap_v2_source_lock_held", default=False)
_WORKER_BOUNDARY = contextvars.ContextVar("bootstrap_v2_worker_boundary", default=None)

INCREMENTAL_OWNER_LOCK_NAME = "lock.flock"


class OwnerLockRequired(RuntimeError):
    """Authority mutation requires the incremental owner lock context."""


def owner_lock_held() -> bool:
    return _OWNER_DEPTH.get() > 0


def source_lock_held() -> bool:
    return _SOURCE_LOCK_HELD.get()


def require_owner_lock() -> None:
    if not owner_lock_held():
        raise OwnerLockRequired("owner_claim_lock_required")
    if not source_lock_held():
        raise OwnerLockRequired("incremental_source_lock_required")


def incremental_owner_lock_path(state_dir: Path) -> Path:
    return state_dir / INCREMENTAL_OWNER_LOCK_NAME


def set_worker_isolation_boundary(boundary: IsolationBoundary) -> None:
    _WORKER_BOUNDARY.set(boundary)


def resolve_isolation_boundary() -> IsolationBoundary:
    cached = _WORKER_BOUNDARY.get()
    if cached is not None:
        return cached
    raw_root = os.environ.get("CONVMEM_INCREMENTAL_ROOT", "").strip()
    token = os.environ.get("CONVMEM_INCREMENTAL_TOKEN", "").strip()
    if raw_root and token:
        return IsolationBoundary(root=Path(raw_root).resolve(), token=token)
    return IsolationBoundary.from_environment()


@contextmanager
def owner_claim_lock(state_dir: Path, *, boundary: IsolationBoundary | None = None) -> Iterator[None]:
    """Acquire incremental source lock, then mark owner context for authority mutations."""
    if boundary is None:
        try:
            boundary = resolve_isolation_boundary()
        except IsolationViolation as exc:
            raise OwnerLockRequired("incremental_isolation_boundary_required") from exc
    lock = SourceAdvisoryLock(boundary, incremental_owner_lock_path(state_dir))
    lock.acquire()
    source_token = _SOURCE_LOCK_HELD.set(True)
    depth_token = _OWNER_DEPTH.set(_OWNER_DEPTH.get() + 1)
    try:
        yield
    finally:
        _OWNER_DEPTH.reset(depth_token)
        _SOURCE_LOCK_HELD.reset(source_token)
        lock.release()
