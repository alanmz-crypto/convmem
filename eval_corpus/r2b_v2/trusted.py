"""Process-local authority consumption tracking for R2b v2."""

from __future__ import annotations

import os

from eval_corpus.r2b_v2._authority_capability import reset_capabilities_for_tests
from eval_corpus.r2b_v2.authority_registry import invalidate_all_authority


_CONSUMED_AUTHORITY_KEYS: set[tuple[str, str, str]] = set()
_ACTIVE_AUTHORITY_KEYS: set[tuple[str, str, str]] = set()


def authority_key(run_id: str, grant_digest: str, authority_digest: str) -> tuple[str, str, str]:
    return (run_id, grant_digest, authority_digest)


def register_active_authority(key: tuple[str, str, str]) -> None:
    if key in _CONSUMED_AUTHORITY_KEYS:
        raise RuntimeError("authority chain already consumed — cannot reacquire continuity")
    if key in _ACTIVE_AUTHORITY_KEYS:
        raise RuntimeError("authority chain already active")
    _ACTIVE_AUTHORITY_KEYS.add(key)


def consume_authority(key: tuple[str, str, str]) -> None:
    _ACTIVE_AUTHORITY_KEYS.discard(key)
    _CONSUMED_AUTHORITY_KEYS.add(key)


def is_authority_consumed(key: tuple[str, str, str]) -> bool:
    return key in _CONSUMED_AUTHORITY_KEYS


def _invalidate_trusted_state_after_fork() -> None:
    invalidate_all_authority()
    _ACTIVE_AUTHORITY_KEYS.clear()
    _CONSUMED_AUTHORITY_KEYS.clear()


os.register_at_fork(after_in_child=_invalidate_trusted_state_after_fork)


def _reset_for_tests() -> None:
    invalidate_all_authority()
    reset_capabilities_for_tests()
    _ACTIVE_AUTHORITY_KEYS.clear()
    _CONSUMED_AUTHORITY_KEYS.clear()
