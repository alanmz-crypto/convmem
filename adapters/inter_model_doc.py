"""Adapter for repo coordination markdown under docs/inter-model/*.md.

Each ## / ### section becomes one canonical message for the ingest fast path
(no chat distill — see inter_model_index.index_inter_model_messages).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

_SECTION_RE = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)

_EXCLUDE_PATH_TOKENS = frozenset({".kiro", "snapshots"})


def is_inter_model_doc(path: Path | str) -> bool:
    """True for active Markdown under docs/inter-model/ at any depth.

    Excludes archive paths and Kiro session snapshot copies (path components
    ``.kiro`` / ``snapshots``). Nested debate folders are included.
    """
    p = Path(path).expanduser().resolve()
    if p.suffix != ".md":
        return False
    if "archive" in p.parts:
        return False
    if _EXCLUDE_PATH_TOKENS & set(p.parts):
        return False
    parts = p.parts
    for i, part in enumerate(parts):
        if part == "inter-model" and i > 0 and parts[i - 1] == "docs":
            return True
    return False


def _file_date(path: Path) -> str:
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return ""


def _doc_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            return stripped.lstrip("# ").strip()
    return ""


def _split_sections(text: str, path: Path) -> list[dict]:
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        title = _doc_title(text) or path.stem.replace("-", " ")
        body = text.strip()
        return [{"title": title, "content": body}]

    doc_title = _doc_title(text)
    sections: list[dict] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = match.group(2).strip()
        body = text[match.end() : end].strip()
        prefix = f"[{doc_title}]\n\n" if doc_title else ""
        if body:
            content = f"{prefix}## {heading}\n\n{body}"
        else:
            content = f"{prefix}## {heading}"
        sections.append({"title": heading, "content": content})
    return sections


def parse(filepath: str) -> list[dict]:
    """Parse an inter-model markdown file into section messages."""
    path = Path(filepath).expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    ts = _file_date(path)
    sections = _split_sections(text, path)

    messages: list[dict] = []
    for idx, section in enumerate(sections):
        content = section["content"].strip()
        if not content:
            continue
        messages.append(
            {
                "role": "document",
                "content": content,
                "timestamp": ts or None,
                "section_title": section["title"],
                "section_index": idx,
                "source_type": "inter_model_doc",
            }
        )
    return messages
