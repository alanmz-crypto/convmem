"""Structure-safe escaping for verbatim evidence rendering."""

from __future__ import annotations

import json
import unicodedata


def escape_metadata(value: object) -> str:
    """Escape attacker-influenced single-line metadata for prompt headers."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    out: list[str] = []
    for ch in value:
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf", "Zl", "Zp"):
            out.append("\\u{:04x}".format(ord(ch)))
            continue
        out.append(ch)
    return "".join(out)


def quote_block(text: str) -> str:
    """Prefix every line with the excerpt quote marker."""
    if not text:
        return "│"
    return "\n".join(f"│ {line}" for line in text.split("\n"))
