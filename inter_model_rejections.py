# pylint: disable=duplicate-code
"""Terminal rejection records for inter-model provenance guard failures.

Operator clear when supersession is resolved without byte changes:
``clear_inter_model_rejection_for_path(load_config()['index']['processed_log'], path)``
"""

from __future__ import annotations

import fcntl
import json
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from atomic_files import atomic_write_text

REJECTION_KIND_PROVENANCE_SUPERSESSION = "provenance_supersession_required"
_FAIL_OPEN_EMITTED: list[bool] = []


def rejections_path(processed_log: str) -> Path:
    p = Path(processed_log).expanduser().resolve()
    return p.with_name("inter_model_rejections.json")


def rejections_lock_path(processed_log: str) -> Path:
    p = Path(processed_log).expanduser().resolve()
    return p.with_name(p.name + ".lock")


@contextmanager
def _rejections_lock(processed_log: str):
    lock = rejections_lock_path(processed_log)
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def clear_fail_open_diagnostic_emitted() -> None:
    """Reset one-shot stderr guard (for tests and recovery after corrupt read)."""
    _FAIL_OPEN_EMITTED.clear()


def _fail_open_once(message: str) -> None:
    if _FAIL_OPEN_EMITTED:
        return
    _FAIL_OPEN_EMITTED.append(True)
    print(message, file=sys.stderr)


def load_inter_model_rejections(processed_log: str) -> dict[str, Any]:
    """Load rejection sidecar; corrupt/unreadable data fails open (empty dict)."""
    path = rejections_path(processed_log)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        _fail_open_once(
            f"[convmem] inter_model_rejections.json unreadable, failing open: {exc}"
        )
        return {}
    if not isinstance(data, dict):
        _fail_open_once(
            "[convmem] inter_model_rejections.json invalid (not an object), failing open"
        )
        return {}
    return data


def save_inter_model_rejections(processed_log: str, data: dict[str, Any]) -> None:
    path = rejections_path(processed_log)
    try:
        atomic_write_text(path, json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        _fail_open_once(
            f"[convmem] inter_model_rejections.json unreadable, failing open: {exc}"
        )


def mutate_inter_model_rejections(
    processed_log: str,
    mutator: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    with _rejections_lock(processed_log):
        data = load_inter_model_rejections(processed_log)
        mutator(data)
        save_inter_model_rejections(processed_log, data)
        return data


def _canonical_path_key(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def record_provenance_supersession_rejection(
    processed_log: str,
    *,
    path_key: str,
    file_hash: str,
    section_id: str | int,
) -> None:
    key = _canonical_path_key(path_key)

    def mutator(data: dict[str, Any]) -> None:
        data[key] = {
            "path": key,
            "file_hash": file_hash,
            "kind": REJECTION_KIND_PROVENANCE_SUPERSESSION,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "section_id": str(section_id),
        }

    mutate_inter_model_rejections(processed_log, mutator)


def clear_inter_model_rejection_for_path(processed_log: str, path: str | Path) -> bool:
    """Remove rejection record for canonical path (operator undo). Returns True if removed."""
    key = _canonical_path_key(path)
    found = {"ok": False}

    def mutator(data: dict[str, Any]) -> None:
        if key in data:
            del data[key]
            found["ok"] = True

    mutate_inter_model_rejections(processed_log, mutator)
    return found["ok"]


def inter_model_rejection_matches(
    processed_log: str,
    path: str | Path,
    file_hash: str,
) -> bool:
    data = load_inter_model_rejections(processed_log)
    key = _canonical_path_key(path)
    entry = data.get(key)
    if not isinstance(entry, dict):
        return False
    return entry.get("file_hash") == file_hash and entry.get("kind") == (
        REJECTION_KIND_PROVENANCE_SUPERSESSION
    )


def prune_stale_inter_model_rejections(
    processed_log: str,
    *,
    path_key: str,
    current_hash: str,
) -> None:
    """Drop a path record when on-disk content no longer matches the rejection hash."""

    key = _canonical_path_key(path_key)

    def mutator(data: dict[str, Any]) -> None:
        entry = data.get(key)
        if not isinstance(entry, dict):
            return
        if entry.get("file_hash") != current_hash:
            data.pop(key, None)

    mutate_inter_model_rejections(processed_log, mutator)
