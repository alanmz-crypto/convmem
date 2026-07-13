"""Fitness checks for the Stage 2 opt-in BOUNDED_AUTONOMY protocol slice.

Protects against standing-token bloat (word ceiling), surface drift (exact body
once on execution surfaces), and accidental default activation (phrase + ChatGPT
absence).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SSOT = REPO_ROOT / "config" / "agent-protocol.md"
ACTIVATION_PHRASE = "Mode: bounded autonomy"
WORD_CEILING = 130

EXECUTION_SURFACES = (
    REPO_ROOT / "config" / "agent-protocol-mcp.txt",
    REPO_ROOT / "config" / "cursor-rules-convmem.mdc.example",
    REPO_ROOT / "config" / "codex-agents-convmem.example.md",
    REPO_ROOT / "config" / "kiro-steering-convmem.example.md",
    REPO_ROOT / "config" / "crush-rules-convmem.example.md",
)
CHATGPT_PACK = REPO_ROOT / "docs" / "chatgpt-pack" / "custom-instructions.txt"

_MARKER_RE = re.compile(
    r"<!-- BOUNDED_AUTONOMY_START -->\n?(.*?)\n?<!-- BOUNDED_AUTONOMY_END -->",
    re.DOTALL,
)


def _canonical_body() -> str:
    """Extract body the same way generate-agent-protocol.sh does (strip leading ws)."""
    text = SSOT.read_text(encoding="utf-8")
    match = _MARKER_RE.search(text)
    if not match:
        raise AssertionError("BOUNDED_AUTONOMY markers missing from config/agent-protocol.md")
    raw = match.group(1)
    return "\n".join(line.lstrip() for line in raw.splitlines()).strip()


class BoundedAutonomyProtocolTests(unittest.TestCase):
    def test_canonical_body_word_ceiling_and_activation(self):
        body = _canonical_body()
        words = body.split()
        self.assertLessEqual(
            len(words),
            WORD_CEILING,
            f"BOUNDED_AUTONOMY body is {len(words)} words (ceiling {WORD_CEILING})",
        )
        self.assertIn(ACTIVATION_PHRASE, body)

    def test_exact_body_once_on_execution_surfaces(self):
        body = _canonical_body()
        self.assertTrue(body, "canonical BOUNDED_AUTONOMY body is empty")
        for path in EXECUTION_SURFACES:
            with self.subTest(surface=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(
                    text.count(body),
                    1,
                    f"{path.name}: expected exact canonical body once",
                )
                self.assertEqual(
                    text.count(ACTIVATION_PHRASE),
                    1,
                    f"{path.name}: expected activation phrase once",
                )

    def test_absent_from_chatgpt_strategy_pack(self):
        body = _canonical_body()
        text = CHATGPT_PACK.read_text(encoding="utf-8")
        self.assertEqual(text.count(body), 0)
        self.assertNotIn(ACTIVATION_PHRASE, text)


if __name__ == "__main__":
    unittest.main()
