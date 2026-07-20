"""Shared helpers for agent-protocol slice fitness tests.

Used by ``test_bounded_autonomy_protocol`` and ``test_team_charter_protocol``
so marker extraction and surface-parity checks are not duplicated (R0801).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SSOT = REPO_ROOT / "config" / "agent-protocol.md"

EXECUTION_SURFACES = (
    REPO_ROOT / "config" / "agent-protocol-mcp.txt",
    REPO_ROOT / "config" / "cursor-rules-convmem.mdc.example",
    REPO_ROOT / "config" / "codex-agents-convmem.example.md",
    REPO_ROOT / "config" / "kiro-steering-convmem.example.md",
    REPO_ROOT / "config" / "crush-rules-convmem.example.md",
)
CHATGPT_PACK = REPO_ROOT / "docs" / "chatgpt-pack" / "custom-instructions.txt"


def slice_marker_re(section: str) -> re.Pattern[str]:
    """Compile START/END markers for an ``agent-protocol.md`` section name."""
    return re.compile(
        rf"<!-- {section}_START -->\n?(.*?)\n?<!-- {section}_END -->",
        re.DOTALL,
    )


def canonical_slice_body(section: str) -> str:
    """Extract a marked section body the way ``generate-agent-protocol.sh`` does.

    Leading whitespace on each line is stripped to match generator normalization.
    """
    text = SSOT.read_text(encoding="utf-8")
    match = slice_marker_re(section).search(text)
    if not match:
        raise AssertionError(
            f"{section} markers missing from config/agent-protocol.md"
        )
    raw = match.group(1)
    return "\n".join(line.lstrip() for line in raw.splitlines()).strip()


def assert_exact_body_once_on_surfaces(
    test_case: unittest.TestCase,
    body: str,
    *,
    label: str,
    extra_once_phrases: tuple[str, ...] = (),
) -> None:
    """Require ``body`` (and optional phrases) exactly once on each execution surface."""
    test_case.assertTrue(body, f"canonical {label} body is empty")
    for path in EXECUTION_SURFACES:
        with test_case.subTest(surface=path.name):
            text = path.read_text(encoding="utf-8")
            count = text.count(body)
            test_case.assertEqual(
                count,
                1,
                f"{path.name}: expected exact canonical {label} body "
                f"exactly once, found {count}",
            )
            for phrase in extra_once_phrases:
                test_case.assertEqual(
                    text.count(phrase),
                    1,
                    f"{path.name}: expected {phrase!r} once",
                )


def assert_absent_from_chatgpt_pack(
    test_case: unittest.TestCase,
    body: str,
    *,
    forbidden_phrases: tuple[str, ...] = (),
) -> None:
    """Require slice body (and optional phrases) absent from ChatGPT pack."""
    text = CHATGPT_PACK.read_text(encoding="utf-8")
    test_case.assertEqual(
        text.count(body),
        0,
        "slice body must not appear in ChatGPT strategy pack",
    )
    for phrase in forbidden_phrases:
        test_case.assertNotIn(
            phrase,
            text,
            f"{phrase!r} must not appear in ChatGPT strategy pack",
        )
