"""Bounded retry state for wedged incremental transactions (issue #286 stage 2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SOURCE_HOLD_THRESHOLD = 3


def _state_path(paths: dict | None) -> Path | None:
    if not paths:
        return None
    transaction = paths.get("transaction")
    if not transaction:
        return None
    return Path(str(transaction)).parent / "retry_state.json"


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _read_or_raise_unavailable(path: Path) -> dict[str, Any] | None:
    import incremental_jsonl as inc

    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise inc.IncrementalJsonlError(
            "retry_state_unavailable",
            "incremental retry state could not be read or written",
        ) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise inc.IncrementalJsonlError(
            "retry_state_unavailable",
            "incremental retry state could not be read or written",
        ) from exc
    if not isinstance(payload, dict):
        raise inc.IncrementalJsonlError(
            "retry_state_unavailable",
            "incremental retry state could not be read or written",
        )
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def clear_incremental_retry_state(paths: dict | None) -> None:
    path = _state_path(paths)
    if path is not None:
        path.unlink(missing_ok=True)


def _retry_state_path_for_source(cfg: dict, canonical_path: str) -> Path | None:
    from config import incremental_jsonl_settings
    from incremental_jsonl import (
        ELIGIBLE_FORMAT,
        detect_format,
        get_format_spec,
        source_state_id,
    )

    settings = incremental_jsonl_settings(cfg)
    if not settings.enabled:
        return None
    state_root = Path(settings.state_dir).expanduser()
    if not state_root.is_dir():
        return None
    resolved = str(Path(canonical_path).expanduser().resolve())
    detected = detect_format(resolved)
    spec = get_format_spec(detected) or get_format_spec(ELIGIBLE_FORMAT)
    assert spec is not None
    state_id = source_state_id(resolved, format_id=spec.format_id)
    return state_root / state_id / "retry_state.json"


def clear_incremental_retry_states_for_source(cfg: dict, canonical_path: str) -> int:
    """Remove retry-state holds for one source path (issue #286 Q2(d) release)."""
    root = _incremental_state_root(cfg)
    if root is None:
        return 0
    resolved = str(Path(canonical_path).expanduser().resolve())
    cleared = 0
    computed = _retry_state_path_for_source(cfg, canonical_path)
    if computed is not None and computed.is_file():
        computed.unlink(missing_ok=True)
        cleared += 1
    for path in sorted(root.glob("**/retry_state.json")):
        if computed is not None and path == computed:
            continue
        payload = _read(path)
        if not payload:
            continue
        stored = str(payload.get("source_path") or "")
        if stored == resolved or stored == canonical_path:
            path.unlink(missing_ok=True)
            cleared += 1
    return cleared


def clear_all_incremental_retry_states(cfg: dict) -> int:
    root = _incremental_state_root(cfg)
    if root is None:
        return 0
    cleared = 0
    for path in sorted(root.glob("**/retry_state.json")):
        path.unlink(missing_ok=True)
        cleared += 1
    return cleared


def classify_incremental_escape(exc: BaseException) -> str:
    from ingest import ProviderUnavailableError

    if isinstance(exc, ProviderUnavailableError):
        return "provider_unavailable"
    if isinstance(exc, OSError):
        return "artifact_write_failed"
    return f"unexpected_{type(exc).__name__}"


def load_incremental_retry_state(paths: dict | None) -> dict[str, Any] | None:
    state_path = _state_path(paths)
    if state_path is None:
        return None
    return _read(state_path)


def _ensure_retry_state_available(state_path: Path) -> None:
    import incremental_jsonl as inc

    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if state_path.is_file():
            state_path.read_text(encoding="utf-8")
        else:
            state_path.write_text("{}\n", encoding="utf-8")
            state_path.unlink(missing_ok=True)
    except OSError as exc:
        raise inc.IncrementalJsonlError(
            "retry_state_unavailable",
            "incremental retry state could not be read or written",
        ) from exc


def enforce_incremental_retry_gates(
    paths: dict | None,
    *,
    path_key: str,
    prefix_digest: str,
) -> None:
    """Refuse before paid transform work when retry state demands it."""
    import incremental_jsonl as inc

    state_path = _state_path(paths)
    if state_path is None:
        return
    _ensure_retry_state_available(state_path)
    prior = _read_or_raise_unavailable(state_path)
    if not prior:
        return
    error_code = str(prior.get("error_code") or "")
    stored_prefix = str(prior.get("prefix_digest") or "")
    consecutive = int(prior.get("consecutive") or 0)
    source_consecutive = int(prior.get("source_consecutive") or 0)
    if source_consecutive >= SOURCE_HOLD_THRESHOLD and error_code:
        outcome = inc.wedged_incremental_outcome(error_code)
        head = f"{outcome}:{prefix_digest}" if prefix_digest else outcome
        diagnostic = inc.wedged_incremental_diagnostic(
            str(prior.get("transaction_id") or ""), path_key
        )
        raise inc.IncrementalJsonlError("live_route_refused", f"{head}\n{diagnostic}")
    if (
        consecutive >= 2
        and error_code
        and stored_prefix == prefix_digest
        and prefix_digest
    ):
        outcome = inc.wedged_incremental_outcome(error_code)
        head = f"{outcome}:{prefix_digest}"
        diagnostic = inc.wedged_incremental_diagnostic(
            str(prior.get("transaction_id") or ""), path_key
        )
        raise inc.IncrementalJsonlError("live_route_refused", f"{head}\n{diagnostic}")


def record_incremental_retry_failure(
    paths: dict | None,
    *,
    path_key: str,
    prefix_digest: str,
    error_code: str,
    transaction_id: str,
) -> bool:
    """Return True when the same error repeats on an unchanged prefix (refuse)."""
    state_path = _state_path(paths)
    if state_path is None:
        return False
    try:
        prior = _read(state_path) or {}
        repeat = (
            prior.get("error_code") == error_code
            and prior.get("prefix_digest") == prefix_digest
            and bool(prefix_digest)
        )
        source_repeat = prior.get("error_code") == error_code and bool(error_code)
        payload = {
            "source_path": path_key,
            "transaction_id": transaction_id,
            "error_code": error_code,
            "prefix_digest": prefix_digest,
            "consecutive": int(prior.get("consecutive") or 0) + 1 if repeat else 1,
            "source_consecutive": int(prior.get("source_consecutive") or 0) + 1
            if source_repeat
            else 1,
        }
        _write(state_path, payload)
    except OSError:
        return False
    return repeat


def _incremental_state_root(cfg: dict) -> Path | None:
    from config import incremental_jsonl_settings

    settings = incremental_jsonl_settings(cfg)
    if not settings.enabled:
        return None
    root = Path(settings.state_dir).expanduser()
    return root if root.is_dir() else None


def iter_wedged_incremental_states(cfg: dict) -> list[dict[str, Any]]:
    root = _incremental_state_root(cfg)
    if root is None:
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("**/retry_state.json")):
        payload = _read(path)
        if not payload:
            continue
        consecutive = int(payload.get("consecutive") or 0)
        source_consecutive = int(payload.get("source_consecutive") or 0)
        if consecutive >= 2 or source_consecutive >= SOURCE_HOLD_THRESHOLD:
            rows.append(payload)
    return rows


def iter_retry_state_unavailable(cfg: dict) -> list[dict[str, Any]]:
    """Directories where retry_state.json exists but is unreadable."""
    root = _incremental_state_root(cfg)
    if root is None:
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("**/retry_state.json")):
        try:
            raw = path.read_text(encoding="utf-8")
            json.loads(raw)
        except (OSError, json.JSONDecodeError):
            rows.append({"path": str(path.parent), "retry_state": str(path)})
    return rows


def iter_stale_incremental_transactions(
    cfg: dict, *, max_age_seconds: int = 900
) -> list[dict[str, Any]]:
    """Transactions stuck in PREPARING or APPLYING longer than max_age_seconds."""
    import time

    root = _incremental_state_root(cfg)
    if root is None:
        return []
    now = time.time()
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("**/transaction.json")):
        payload = _read(path)
        if not payload:
            continue
        phase = str(payload.get("phase") or "")
        if phase not in {"PREPARING", "APPLYING"}:
            continue
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age < max_age_seconds:
            continue
        rows.append(
            {
                "source_path": payload.get("source_path"),
                "transaction_id": payload.get("transaction_id"),
                "phase": phase,
                "age_seconds": int(age),
            }
        )
    return rows
