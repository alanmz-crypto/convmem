"""Fitness: shell+MCP surfaces use MCP_AFTER_TIER_A; MCP-only keeps brief-first.

Protects the Stage 3 promotion blocker fix where Cursor/Kiro/Crush were given
full Tier B (brief-first) beside Tier A, causing agents to batch MCP brief with
shell doctor. After Tier A, search tools are allowed; MCP brief must not repeat.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SSOT = REPO_ROOT / "config" / "agent-protocol.md"

POST_TIER_A_RULE = "Do **not** repeat MCP `brief()`"
TIER_B_BRIEF_FIRST = "**`brief()` first** every session"
MCP_PATH_LABELS = (
    "## Path: shell (Tier A)",
    "## Path: post-shell MCP (after Tier A)",
    "## Path: MCP-only (Tier B — no shell; brief-first)",
)

SHELL_MCP_SURFACES = (
    REPO_ROOT / "config" / "cursor-rules-convmem.mdc.example",
    REPO_ROOT / "config" / "kiro-steering-convmem.example.md",
    REPO_ROOT / "config" / "crush-rules-convmem.example.md",
)
MCP_ONLY_INSTRUCTIONS = REPO_ROOT / "config" / "agent-protocol-mcp.txt"

_MARKER_RE = re.compile(
    r"<!-- MCP_AFTER_TIER_A_START -->\n?(.*?)\n?<!-- MCP_AFTER_TIER_A_END -->",
    re.DOTALL,
)


def _canonical_body() -> str:
    text = SSOT.read_text(encoding="utf-8")
    match = _MARKER_RE.search(text)
    if not match:
        raise AssertionError("MCP_AFTER_TIER_A markers missing from config/agent-protocol.md")
    raw = match.group(1)
    return "\n".join(line.lstrip() for line in raw.splitlines()).strip()


class McpAfterTierATests(unittest.TestCase):
    def test_ssot_has_post_tier_a_rule(self):
        body = _canonical_body()
        self.assertIn(POST_TIER_A_RULE, body)
        self.assertIn("`search_fast()`", body)
        self.assertIn("`ask()`", body)
        self.assertIn("`related()`", body)
        self.assertIn("`stats()`", body)

    def test_shell_mcp_surfaces_have_post_tier_a_once_and_omit_tier_b_brief_first(self):
        body = _canonical_body()
        self.assertTrue(body, "canonical MCP_AFTER_TIER_A body is empty")
        for path in SHELL_MCP_SURFACES:
            with self.subTest(surface=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(
                    text.count(body),
                    1,
                    f"{path.name}: expected exact MCP_AFTER_TIER_A body once",
                )
                self.assertEqual(
                    text.count(POST_TIER_A_RULE),
                    1,
                    f"{path.name}: expected post-Tier-A no-repeat-brief rule once",
                )
                self.assertNotIn(
                    TIER_B_BRIEF_FIRST,
                    text,
                    f"{path.name}: Tier B brief-first must be omitted on shell+MCP surfaces",
                )
                self.assertNotIn(
                    "Prefer **`brief()` tool** for session start",
                    text,
                    f"{path.name}: Tier B brief-first preference must be omitted",
                )

    def test_mcp_only_instructions_retain_brief_first_and_labeled_paths(self):
        text = MCP_ONLY_INSTRUCTIONS.read_text(encoding="utf-8")
        body = _canonical_body()
        self.assertEqual(text.count(body), 1)
        self.assertIn(TIER_B_BRIEF_FIRST, text)
        self.assertIn("Prefer **`brief()` tool** for session start", text)
        for label in MCP_PATH_LABELS:
            with self.subTest(label=label):
                self.assertIn(label, text)


if __name__ == "__main__":
    unittest.main()
