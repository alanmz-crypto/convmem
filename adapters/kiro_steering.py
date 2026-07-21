"""Adapter for Kiro steering markdown under .kiro/steering/*.md.

One knowledge-unit message per file (no LLM distill). Content leads with an
existence/path claim so retrieval can counter stale "file does not exist"
chat distillations (ksweep-deploy incident / P1.0a).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

_BODY_LEAD_CHARS = 2000


def is_kiro_steering_doc(path: Path | str) -> bool:
    """True for Markdown under ``.kiro/steering/`` (any repo depth)."""
    p = Path(path).expanduser().resolve()
    if p.suffix != ".md":
        return False
    parts = p.parts
    for i, part in enumerate(parts):
        if part == ".kiro" and i + 1 < len(parts) and parts[i + 1] == "steering":
            return True
    return False


def _file_date(path: Path) -> str:
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return ""


def _doc_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            return stripped.lstrip("# ").strip()
    return fallback


def parse(filepath: str) -> list[dict]:
    """Parse one steering file into a single document message for direct index."""
    path = Path(filepath).expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    title = _doc_title(text, path.stem.replace("-", " "))
    body = text.strip()
    if len(body) > _BODY_LEAD_CHARS:
        body = body[: _BODY_LEAD_CHARS - 1] + "…"
    content = (
        f"Kiro steering file {path.name} exists on disk at {path}.\n\n"
        f"{title}\n\n{body}"
    )
    return [
        {
            "role": "document",
            "content": content,
            "timestamp": _file_date(path) or None,
            "section_title": title,
            "section_index": 0,
            "source_type": "kiro_steering",
        }
    ]
