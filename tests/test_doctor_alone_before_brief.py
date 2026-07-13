"""Fitness: doctor runs alone before brief/ask/search on shell-capable surfaces.

Protects the promotion fix for parallel tool batching (doctor + MCP brief in one
batch). The consolidated Tier A step-1 rule must appear once on every shell-
capable execution surface; the removed Cursor-specific duplicate must stay gone.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SSOT = REPO_ROOT / "config" / "agent-protocol.md"

# Distinctive consolidated step-1 fragment (must match SSoT exactly once per surface).
CONSOLIDATED_RULE = (
    "run alone first. Must exit 0 before any brief/ask/search."
)
REMOVED_DUPLICATE = "**Cursor with shell:**"

SHELL_CAPABLE_SURFACES = (
    REPO_ROOT / "config" / "agent-protocol-mcp.txt",
    REPO_ROOT / "config" / "cursor-rules-convmem.mdc.example",
    REPO_ROOT / "config" / "codex-agents-convmem.example.md",
    REPO_ROOT / "config" / "kiro-steering-convmem.example.md",
    REPO_ROOT / "config" / "crush-rules-convmem.example.md",
)

_MARKER_RE = re.compile(
    r"<!-- TIER_A_START -->\n?(.*?)\n?<!-- TIER_A_END -->",
    re.DOTALL,
)


def _tier_a_body(text: str) -> str:
    match = _MARKER_RE.search(text)
    if not match:
        raise AssertionError("TIER_A markers missing")
    return "\n".join(line.lstrip() for line in match.group(1).splitlines()).strip()


class DoctorAloneBeforeBriefTests(unittest.TestCase):
    def test_ssot_has_consolidated_rule_once_and_no_cursor_duplicate(self):
        text = SSOT.read_text(encoding="utf-8")
        body = _tier_a_body(text)
        self.assertEqual(body.count(CONSOLIDATED_RULE), 1)
        self.assertNotIn(REMOVED_DUPLICATE, body)
        self.assertNotIn(REMOVED_DUPLICATE, text)

    def test_consolidated_rule_once_on_shell_capable_surfaces(self):
        for path in SHELL_CAPABLE_SURFACES:
            with self.subTest(surface=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(
                    text.count(CONSOLIDATED_RULE),
                    1,
                    f"{path.name}: expected consolidated doctor-alone rule once",
                )
                self.assertNotIn(
                    REMOVED_DUPLICATE,
                    text,
                    f"{path.name}: Cursor-specific doctor-before-MCP duplicate must be absent",
                )


if __name__ == "__main__":
    unittest.main()
