"""Kiro watch path expansion without pulling coordinator imports into watch.py."""

from __future__ import annotations

from pathlib import Path


def expand_selected_kiro_session_meta_paths(cfg: dict, paths: list[str]) -> list[str]:
    """Map session.json watch events to sibling messages.jsonl for selected Kiro."""
    from config import incremental_jsonl_settings
    from incremental_jsonl_kiro_admission import selected_kiro_path

    try:
        settings = incremental_jsonl_settings(cfg)
    except Exception:  # pylint: disable=broad-exception-caught
        return paths
    expanded: list[str] = []
    for raw in paths:
        expanded.append(raw)
        candidate = Path(raw)
        if candidate.name != "session.json":
            continue
        sibling = candidate.parent / "messages.jsonl"
        if not sibling.is_file():
            continue
        sibling_key = str(sibling.expanduser().resolve())
        if selected_kiro_path(
            path_key=sibling_key,
            live_sources=settings.live_sources,
            detected_format="jsonl_kiro_session",
        ):
            expanded.append(sibling_key)
    return expanded
