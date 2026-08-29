"""Session read-scope default for retrieval (read-only; does not affect writes)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from domains import normalize_domain

_SCOPE_ENV = "CONVMEM_READ_SCOPE_DOMAIN"
_SCOPE_FILE = Path("~/.local/share/convmem/read_scope.json").expanduser()


def _scope_file_path() -> Path | None:
    raw = (os.environ.get("CONVMEM_READ_SCOPE_FILE") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return _SCOPE_FILE


def get_read_scope() -> str | None:
    """Return the active session read-scope domain, if any."""
    env = (os.environ.get(_SCOPE_ENV) or "").strip()
    if env:
        return normalize_domain(env)
    path = _scope_file_path()
    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = (payload.get("domain") or "").strip()
    return normalize_domain(raw) if raw else None


def set_read_scope(domain: str) -> str:
    """Persist session read-scope default; returns normalized domain."""
    normalized = normalize_domain(domain)
    path = _scope_file_path()
    if path is None:
        raise RuntimeError("read scope file path is not configured")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"domain": normalized}, indent=2) + "\n",
        encoding="utf-8",
    )
    return normalized


def clear_read_scope() -> None:
    """Remove persisted session read-scope default."""
    path = _scope_file_path()
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def resolve_retrieval_domain(
    explicit: str | None = None,
    *,
    cross_domain: bool = False,
) -> tuple[str | None, dict]:
    """Resolve effective retrieval domain and observability metadata.

    Precedence: cross_domain (widens for one call) > explicit per-call domain >
    session read-scope default > unscoped.
    """
    session = get_read_scope()
    meta: dict = {
        "cross_domain": cross_domain,
        "session_read_scope": session,
        "explicit_domain": normalize_domain(explicit) if explicit else None,
    }
    if cross_domain:
        meta.update(effective_domain=None, scope_source="cross_domain")
        return None, meta
    if explicit:
        effective = normalize_domain(explicit)
        meta.update(effective_domain=effective, scope_source="explicit")
        return effective, meta
    if session:
        meta.update(effective_domain=session, scope_source="session_default")
        return session, meta
    meta.update(effective_domain=None, scope_source="none")
    return None, meta
