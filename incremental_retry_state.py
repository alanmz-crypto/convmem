"""Bounded retry state for wedged incremental transactions (issue #286 stage 2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def clear_incremental_retry_state(paths: dict | None) -> None:
    path = _state_path(paths)
    if path is not None:
        path.unlink(missing_ok=True)


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
    state_path.parent.mkdir(parents=True, exist_ok=True)
    prior = _read(state_path) or {}
    repeat = (
        prior.get("error_code") == error_code
        and prior.get("prefix_digest") == prefix_digest
    )
    payload = {
        "source_path": path_key,
        "transaction_id": transaction_id,
        "error_code": error_code,
        "prefix_digest": prefix_digest,
        "consecutive": int(prior.get("consecutive") or 0) + 1 if repeat else 1,
    }
    state_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return repeat


def iter_wedged_incremental_states(cfg: dict) -> list[dict[str, Any]]:
    state_dir = (cfg.get("index") or {}).get("incremental_jsonl", {}).get("state_dir")
    if not state_dir:
        return []
    root = Path(str(state_dir)).expanduser()
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("**/retry_state.json")):
        payload = _read(path)
        if not payload:
            continue
        if int(payload.get("consecutive") or 0) >= 2:
            rows.append(payload)
    return rows
