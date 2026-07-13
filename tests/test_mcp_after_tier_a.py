"""Fitness: shell+MCP surfaces use MCP_AFTER_TIER_A; MCP-only keeps brief-first.

Protects the Stage 3 promotion blocker fix where Cursor/Kiro/Crush were given
full Tier B (brief-first) beside Tier A, causing agents to batch MCP brief with
shell doctor. After Tier A in a project repo, search tools are allowed; MCP brief
must not repeat. Non-project modes keep MCP brief gates.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SSOT = REPO_ROOT / "config" / "agent-protocol.md"
MCP_SERVER = REPO_ROOT / "mcp_server.py"

POST_TIER_A_RULE = "Do **not** repeat `brief()`"
POST_TIER_A_SCOPE = "After Tier A in a project repo"
NON_PROJECT_GATES = "Non-project modes follow MCP gates"
TIER_B_BRIEF_FIRST = "**`brief()` first** every session"
REMOVED_TIER_A_MCP_BRIEF = "When also calling MCP"
FORBIDDEN_UNCONDITIONAL = "MANDATORY first MCP tool every session"
MCP_PATH_LABELS = (
    "## Shell (Tier A)",
    "## MCP after Tier A",
    "## MCP-only (Tier B)",
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
_TIER_A_RE = re.compile(
    r"<!-- TIER_A_START -->\n?(.*?)\n?<!-- TIER_A_END -->",
    re.DOTALL,
)


def _canonical_body() -> str:
    text = SSOT.read_text(encoding="utf-8")
    match = _MARKER_RE.search(text)
    if not match:
        raise AssertionError("MCP_AFTER_TIER_A markers missing from config/agent-protocol.md")
    raw = match.group(1)
    return "\n".join(line.lstrip() for line in raw.splitlines()).strip()


def _tier_a_body() -> str:
    text = SSOT.read_text(encoding="utf-8")
    match = _TIER_A_RE.search(text)
    if not match:
        raise AssertionError("TIER_A markers missing from config/agent-protocol.md")
    raw = match.group(1)
    return "\n".join(line.lstrip() for line in raw.splitlines()).strip()


def _docstring_for_function(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            doc = ast.get_docstring(node)
            if doc is None:
                raise AssertionError(f"{name}() missing docstring")
            return doc
    raise AssertionError(f"{name}() not found in mcp_server.py")


class McpAfterTierATests(unittest.TestCase):
    def test_ssot_has_scoped_post_tier_a_rule(self):
        body = _canonical_body()
        self.assertIn(POST_TIER_A_SCOPE, body)
        self.assertIn(POST_TIER_A_RULE, body)
        self.assertIn(NON_PROJECT_GATES, body)
        self.assertIn("`search_fast()`", body)
        self.assertIn("`ask()`", body)
        self.assertIn("`related()`", body)
        self.assertIn("`stats()`", body)

    def test_tier_a_step2_no_mcp_brief_tail(self):
        body = _tier_a_body()
        self.assertNotIn(REMOVED_TIER_A_MCP_BRIEF, body)
        self.assertNotIn("pass **project=<slug>**", body)

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
                self.assertNotIn(REMOVED_TIER_A_MCP_BRIEF, text)
                self.assertNotIn(FORBIDDEN_UNCONDITIONAL, text)

    def test_mcp_only_instructions_retain_brief_first_and_labeled_paths(self):
        text = MCP_ONLY_INSTRUCTIONS.read_text(encoding="utf-8")
        body = _canonical_body()
        self.assertEqual(text.count(body), 1)
        self.assertIn(TIER_B_BRIEF_FIRST, text)
        self.assertIn("Prefer **`brief()` tool** for session start", text)
        self.assertIn("## Shell (Tier A)", text)  # Continue still needs Tier A path
        for label in MCP_PATH_LABELS:
            with self.subTest(label=label):
                self.assertIn(label, text)
        self.assertNotIn(FORBIDDEN_UNCONDITIONAL, text)

    def test_mcp_server_distinguishes_shell_project_vs_mcp_only_vs_gates(self):
        source = MCP_SERVER.read_text(encoding="utf-8")
        self.assertNotIn(FORBIDDEN_UNCONDITIONAL, source)

        brief_doc = _docstring_for_function(source, "brief")
        folder_doc = _docstring_for_function(source, "folder_state")
        self.assertIn("MCP-only: call brief() first", brief_doc)
        self.assertIn("Shell + project repo after CLI Tier A: do not repeat brief", brief_doc)
        self.assertIn("System runbook", brief_doc)
        self.assertIn("Workspace-local", brief_doc)
        self.assertIn("Shell + project repo after CLI Tier A: do not repeat", folder_doc)
        self.assertIn("MCP-only and non-project modes", folder_doc)

        # Fallback instructions used when agent-protocol-mcp.txt is absent.
        self.assertIn("do not repeat brief()", source)
        self.assertIn("TIER B (MCP only, no shell): call brief() first", source)
        self.assertIn("workspace_local/system_runbook remain brief-first", source)


if __name__ == "__main__":
    unittest.main()
