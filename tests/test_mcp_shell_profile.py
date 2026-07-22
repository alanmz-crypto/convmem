"""Fitness: CONVMEM_MCP_PROFILE=shell makes no-repeat-brief mechanical in project repos.

Covers:
- shell + project: brief tools/resources absent
- shell + non-project: brief endpoints present
- default/full + project: brief endpoints present
- compact shell instructions ≤40 words
- Cursor/Kiro/Crush examples/deploy receive the profile; Continue does not
- deploy merge preserves unrelated env values
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SSOT = REPO_ROOT / "config" / "agent-protocol.md"
SHELL_INSTRUCTIONS = REPO_ROOT / "config" / "agent-protocol-mcp-shell.txt"
FULL_INSTRUCTIONS = REPO_ROOT / "config" / "agent-protocol-mcp.txt"
MERGE_SCRIPT = REPO_ROOT / "scripts" / "merge_mcp_shell_profile.py"
PYTHON = sys.executable

BRIEF_TOOLS = frozenset({"brief", "folder_state"})
BRIEF_RESOURCE_MARKERS = ("memories://brief", "memory://brief")

CURSOR_EXAMPLE = REPO_ROOT / "config" / "cursor-mcp.json.example"
KIRO_EXAMPLE = REPO_ROOT / "config" / "kiro-mcp.json.example"
CONTINUE_JSON_EXAMPLE = REPO_ROOT / "config" / "continue-mcp.json.example"
CONTINUE_YAML_EXAMPLE = REPO_ROOT / "config" / "continue-mcp-servers.yaml.example"

_MARKER_RE = re.compile(
    r"<!-- MCP_AFTER_TIER_A_START -->\n?(.*?)\n?<!-- MCP_AFTER_TIER_A_END -->",
    re.DOTALL,
)


def _word_count(text: str) -> int:
    return len(text.split())


def _inventory(profile: str, cwd: str) -> dict:
    """Spawn an isolated MCP module load; return tool names + resource URIs."""
    env = {k: v for k, v in os.environ.items() if k != "CONVMEM_MCP_PROFILE"}
    if profile:
        env["CONVMEM_MCP_PROFILE"] = profile
    env["PYTHONPATH"] = str(REPO_ROOT)
    code = r"""
import asyncio, json, os, sys
sys.path.insert(0, os.environ["PYTHONPATH"])
import mcp_server

async def main():
    tools = await mcp_server.mcp.list_tools()
    resources = await mcp_server.mcp.list_resources()
    templates = await mcp_server.mcp.list_resource_templates()
    print(json.dumps({
        "profile": mcp_server._mcp_profile(),
        "omit": mcp_server._shell_profile_omits_brief_endpoints(),
        "tools": sorted(t.name for t in tools),
        "resources": sorted(str(r.uri) for r in resources),
        "templates": sorted(str(getattr(t, "uriTemplate", getattr(t, "uri_template", ""))) for t in templates),
        "base_instructions": mcp_server._BASE_INSTRUCTIONS,
    }))

asyncio.run(main())
"""
    proc = subprocess.run(
        [PYTHON, "-c", code],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"inventory failed profile={profile!r} cwd={cwd!r}:\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return json.loads(proc.stdout)


def _has_brief_resources(inv: dict) -> bool:
    blob = " ".join(inv.get("resources", []) + inv.get("templates", []))
    return any(m in blob for m in BRIEF_RESOURCE_MARKERS)


class McpShellProfileTests(unittest.TestCase):
    def test_compact_shell_instructions_le_40_words(self):
        self.assertTrue(SHELL_INSTRUCTIONS.is_file(), "shell instructions missing — regenerate")
        text = SHELL_INSTRUCTIONS.read_text(encoding="utf-8").strip()
        words = _word_count(text)
        self.assertLessEqual(words, 40, f"shell instructions are {words} words (ceiling 40)")
        # Must be exactly MCP_AFTER_TIER_A body (no Tier B brief-first)
        ssot = SSOT.read_text(encoding="utf-8")
        match = _MARKER_RE.search(ssot)
        self.assertIsNotNone(match)
        body = "\n".join(line.lstrip() for line in match.group(1).splitlines()).strip()
        body_compact = "\n".join(line for line in body.splitlines() if line.strip())
        self.assertEqual(text, body_compact)
        self.assertNotIn("brief() first", text)

    def test_shell_project_brief_endpoints_absent(self):
        inv = _inventory("shell", str(REPO_ROOT))
        tool_set = set(inv["tools"])
        self.assertTrue(BRIEF_TOOLS.isdisjoint(tool_set), f"brief tools present: {tool_set}")
        self.assertFalse(_has_brief_resources(inv), f"brief resources present: {inv}")
        self.assertIn("search_fast", tool_set)
        self.assertIn("ask", tool_set)
        self.assertTrue(inv["omit"])


    def test_shell_alien_cwd_instructions_have_no_workspace_local(self):
        """Cursor cwd=$HOME must not advertise brief-first under shell profile."""
        with tempfile.TemporaryDirectory(prefix="convmem-shell-alien-") as tmp:
            inv = _inventory("shell", tmp)
        instr = inv.get("instructions") or inv["base_instructions"]
        self.assertNotIn("workspace_local", instr)
        self.assertNotIn("FIRST tool call MUST", instr)
        self.assertNotIn("ACTIVE SESSION", instr)
        self.assertIn("Do **not** repeat `brief()`", instr)

    def test_shell_non_project_brief_endpoints_present(self):
        with tempfile.TemporaryDirectory(prefix="convmem-shell-np-") as tmp:
            inv = _inventory("shell", tmp)
        tool_set = set(inv["tools"])
        self.assertTrue(BRIEF_TOOLS.issubset(tool_set), f"missing brief tools: {tool_set}")
        # Shell profile never advertises brief resources (CLI Tier A + tools only).
        self.assertFalse(_has_brief_resources(inv), f"unexpected brief resources: {inv}")
        self.assertFalse(inv["omit"])

    def test_full_project_brief_endpoints_present(self):
        inv = _inventory("", str(REPO_ROOT))
        tool_set = set(inv["tools"])
        self.assertEqual(inv["profile"], "full")
        self.assertTrue(BRIEF_TOOLS.issubset(tool_set), f"missing brief tools: {tool_set}")
        self.assertTrue(_has_brief_resources(inv), f"missing brief resources: {inv}")
        self.assertFalse(inv["omit"])

    def test_cursor_kiro_crush_receive_profile_continue_does_not(self):
        cursor = json.loads(CURSOR_EXAMPLE.read_text(encoding="utf-8"))
        kiro = json.loads(KIRO_EXAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(
            cursor["mcpServers"]["convmem"]["env"].get("CONVMEM_MCP_PROFILE"),
            "shell",
        )
        self.assertEqual(
            kiro["mcpServers"]["convmem"]["env"].get("CONVMEM_MCP_PROFILE"),
            "shell",
        )
        # Crush has no separate example file; merge script must support crush client.
        self.assertIn(b'"crush"', MERGE_SCRIPT.read_bytes())

        cont_json = CONTINUE_JSON_EXAMPLE.read_text(encoding="utf-8")
        cont_yaml = CONTINUE_YAML_EXAMPLE.read_text(encoding="utf-8")
        self.assertNotIn("CONVMEM_MCP_PROFILE", cont_json)
        self.assertNotIn("CONVMEM_MCP_PROFILE", cont_yaml)
        # Full MCP instructions still exist for Continue/default.
        self.assertTrue(FULL_INSTRUCTIONS.is_file())
        self.assertIn("**`brief()` first**", FULL_INSTRUCTIONS.read_text(encoding="utf-8"))

    def test_deploy_merge_preserves_unrelated_env_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cursor = home / "cursor-mcp.json"
            crush = home / "crush.json"
            sentinel = "PRESERVE_ME_UNRELATED_VALUE_xyz"
            cursor.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "convmem": {
                                "command": "python",
                                "args": ["mcp_server.py"],
                                "env": {
                                    "DEEPSEEK_API_KEY": sentinel,
                                    "OTHER_KEEP": "keep-me",
                                },
                            }
                        }
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            crush.write_text(
                json.dumps(
                    {
                        "mcp": {
                            "convmem": {
                                "command": "python",
                                "args": ["mcp_server.py"],
                                "env": {"HOME": "/tmp/fake", "DEEPSEEK_API_KEY": sentinel},
                            }
                        }
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            for path, client in ((cursor, "cursor"), (crush, "crush")):
                proc = subprocess.run(
                    [PYTHON, str(MERGE_SCRIPT), str(path), client],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertEqual(proc.stdout.strip(), "added")
                # Merge must never echo secret/env values
                self.assertNotIn(sentinel, proc.stdout)
                self.assertNotIn(sentinel, proc.stderr)

            cdata = json.loads(cursor.read_text(encoding="utf-8"))
            env = cdata["mcpServers"]["convmem"]["env"]
            self.assertEqual(env["CONVMEM_MCP_PROFILE"], "shell")
            self.assertEqual(env["DEEPSEEK_API_KEY"], sentinel)
            self.assertEqual(env["OTHER_KEEP"], "keep-me")

            cr = json.loads(crush.read_text(encoding="utf-8"))
            cenv = cr["mcp"]["convmem"]["env"]
            self.assertEqual(cenv["CONVMEM_MCP_PROFILE"], "shell")
            self.assertEqual(cenv["DEEPSEEK_API_KEY"], sentinel)
            self.assertEqual(cenv["HOME"], "/tmp/fake")

            # Idempotent
            proc2 = subprocess.run(
                [PYTHON, str(MERGE_SCRIPT), str(cursor), "cursor"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(proc2.stdout.strip(), "unchanged")

    def test_merge_missing_convmem_leaves_cursor_config_byte_identical(self):
        """No convmem block → missing + no write (do not invent a server)."""
        with tempfile.TemporaryDirectory() as tmp:
            cursor = Path(tmp) / "cursor-mcp.json"
            # Deliberately odd formatting so json.dump rewrite would change bytes.
            original = (
                '{\n'
                '  "mcpServers" : {\n'
                '    "other-server":{"command":"echo","args":["hi"]}\n'
                '  }\n'
                '}\n'
            )
            cursor.write_text(original, encoding="utf-8")
            before = cursor.read_bytes()

            proc = subprocess.run(
                [PYTHON, str(MERGE_SCRIPT), str(cursor), "cursor"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(proc.stdout.strip(), "missing")
            self.assertEqual(cursor.read_bytes(), before)
            data = json.loads(cursor.read_text(encoding="utf-8"))
            self.assertNotIn("convmem", data.get("mcpServers", {}))
            self.assertEqual(set(data["mcpServers"]), {"other-server"})


if __name__ == "__main__":
    unittest.main()
