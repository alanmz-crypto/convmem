"""Owner claim-lock context for Codex bootstrap v2 (T2)."""

from __future__ import annotations

import contextvars
import os
from contextlib import contextmanager
from typing import Iterator

_OWNER_DEPTH = contextvars.ContextVar("bootstrap_v2_owner_depth", default=0)
ENFORCE_ENV = "CONVMEM_BOOTSTRAP_V2_ENFORCE_OWNER_LOCK"


class OwnerLockRequired(RuntimeError):
    """Authority mutation requires the owner claim lock."""


def owner_lock_held() -> bool:
    return _OWNER_DEPTH.get() > 0


def require_owner_lock() -> None:
    if os.environ.get(ENFORCE_ENV, "").strip() == "1" and not owner_lock_held():
        raise OwnerLockRequired("owner_claim_lock_required")


@contextmanager
def owner_claim_lock(state_dir) -> Iterator[None]:
    from bootstrap_codex_v2_authority import claim_lock

    with claim_lock(state_dir):
        token = _OWNER_DEPTH.set(_OWNER_DEPTH.get() + 1)
        try:
            yield
        finally:
            _OWNER_DEPTH.reset(token)
