"""Structure-safe escaping for verbatim evidence rendering."""

from __future__ import annotations

import re
import unicodedata

_LINE_BREAK_RE = re.compile(r"[\r\n\u0085\u2028\u2029]+")


def _escape_isolated_char(ch: str) -> str:
    cat = unicodedata.category(ch)
    if cat in ("Cc", "Cf", "Zl", "Zp"):
        return "\\u{:04x}".format(ord(ch))
    return ch


def escape_metadata(value: object) -> str:
    """Escape attacker-influenced single-line metadata for prompt headers."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return "".join(_escape_isolated_char(ch) for ch in value)


def _split_quote_lines(text: str) -> list[str]:
    """Split on every visual line-break class, including Unicode separators."""
    if not text:
        return [""]
    return _LINE_BREAK_RE.split(text)


def _escape_quote_line(line: str) -> str:
    """Escape control/format characters that could break quote isolation."""
    return "".join(_escape_isolated_char(ch) for ch in line)


def quote_block(text: str) -> str:
    """Prefix every visual line with the excerpt quote marker.

    Splits on LF/CR and Unicode line/paragraph separators (U+0085, U+2028,
    U+2029) before quoting so attacker text cannot synthesize unquoted prompt
    lines or fake item headers. Control and format characters within each line
    are escaped to ``\\uXXXX`` literals.
    """
    lines = _split_quote_lines(text)
    if not lines:
        return "│"
    return "\n".join(f"│ {_escape_quote_line(line)}" for line in lines)
