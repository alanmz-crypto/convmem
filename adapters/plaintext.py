"""Adapter for ordinary UTF-8 documents in user-configured watch folders."""

from __future__ import annotations

from pathlib import Path

MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
NATURAL_LANGUAGE_SUFFIXES = frozenset(
    {
        ".md",
        ".txt",
        ".text",
        ".rst",
        ".adoc",
        ".asciidoc",
        ".org",
        ".tex",
        ".wiki",
        ".textile",
    }
)


def _read_utf8(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) > MAX_DOCUMENT_BYTES or b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def is_plaintext(path: Path | str) -> bool:
    """Return whether *path* is a bounded, readable UTF-8 document."""
    candidate = Path(path)
    if not candidate.is_file():
        return False
    return _read_utf8(candidate) is not None


def parse(filepath: str) -> list[dict]:
    """Read one ordinary document as a canonical documentary message."""
    path = Path(filepath)
    text = _read_utf8(path)
    if text is None or not text.strip():
        return []
    return [
        {
            "role": "document",
            "content": text,
            "source_type": "plaintext_document",
            "title": path.name,
        }
    ]
