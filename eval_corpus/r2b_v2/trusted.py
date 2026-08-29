"""Process-local unforgeable tokens for R2b v2 trusted authority objects."""

from __future__ import annotations

import os
import secrets

_LEASE_TOKEN: bytes = secrets.token_bytes(32)
_COVERAGE_TOKEN: bytes = secrets.token_bytes(32)
_AUTHORITY_TOKEN: bytes = secrets.token_bytes(32)

_CONSUMED_AUTHORITY_KEYS: set[tuple[str, str, str]] = set()
_ACTIVE_AUTHORITY_KEYS: set[tuple[str, str, str]] = set()


def lease_token() -> bytes:
    return _LEASE_TOKEN


def coverage_token() -> bytes:
    return _COVERAGE_TOKEN


def authority_token() -> bytes:
    return _AUTHORITY_TOKEN


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
    global _LEASE_TOKEN, _COVERAGE_TOKEN, _AUTHORITY_TOKEN
    _LEASE_TOKEN = secrets.token_bytes(32)
    _COVERAGE_TOKEN = secrets.token_bytes(32)
    _AUTHORITY_TOKEN = secrets.token_bytes(32)
    _ACTIVE_AUTHORITY_KEYS.clear()
    _CONSUMED_AUTHORITY_KEYS.clear()


os.register_at_fork(after_in_child=_invalidate_trusted_state_after_fork)


def _reset_for_tests() -> None:
    global _LEASE_TOKEN, _COVERAGE_TOKEN, _AUTHORITY_TOKEN
    _LEASE_TOKEN = secrets.token_bytes(32)
    _COVERAGE_TOKEN = secrets.token_bytes(32)
    _AUTHORITY_TOKEN = secrets.token_bytes(32)
    _ACTIVE_AUTHORITY_KEYS.clear()
    _CONSUMED_AUTHORITY_KEYS.clear()
