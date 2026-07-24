"""Regression: Crush-shaped MCP stdio must not deadlock on tools/call.

Crush 0.86 advertises roots, then calls tools/list → prompts/list → ping →
tools/call. Shell-profile sync handlers used to nested-await list_roots while
the stdio loop was blocked in tools/call (hang). Unit coverage lives in
test_mcp_roots_probe.py; this exercises the live stdio server path.
"""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MCP_SERVER = REPO / "mcp_server.py"
# Hang class waited up to 60s on nested list_roots; healthy stats is ~1s.
STATS_DEADLINE_S = 12.0


class CrushMcpStdioSequence(unittest.TestCase):
    def _recv(self, proc: subprocess.Popen, timeout: float) -> dict | None:
        r, _, _ = select.select([proc.stdout], [], [], timeout)
        if not r:
            return None
        line = proc.stdout.readline()
        if not line:
            return None
        return json.loads(line)

    def _send(self, proc: subprocess.Popen, obj: dict) -> None:
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def test_shell_profile_stats_after_crush_handshake(self):
        env = os.environ.copy()
        env["CONVMEM_MCP_PROFILE"] = "shell"
        env.setdefault("HOME", str(Path.home()))
        proc = subprocess.Popen(
            [sys.executable, "-u", str(MCP_SERVER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
            cwd=str(REPO),
        )
        try:
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "clientInfo": {
                            "name": "crush",
                            "title": "Crush",
                            "version": "v0.86.0",
                        },
                        "protocolVersion": "2025-11-25",
                        "capabilities": {"roots": {"listChanged": True}},
                    },
                },
            )
            init = self._recv(proc, 20.0)
            self.assertIsNotNone(init, "initialize timed out")
            self.assertEqual(init.get("id"), 1)
            self.assertIn("result", init)

            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                },
            )
            self._send(
                proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            )
            self.assertIsNotNone(self._recv(proc, 20.0), "tools/list timed out")
            self._send(
                proc, {"jsonrpc": "2.0", "id": 3, "method": "prompts/list", "params": {}}
            )
            self.assertIsNotNone(self._recv(proc, 10.0), "prompts/list timed out")
            self._send(proc, {"jsonrpc": "2.0", "id": 4, "method": "ping"})
            self.assertIsNotNone(self._recv(proc, 10.0), "ping timed out")

            t0 = time.monotonic()
            self._send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "stats", "arguments": {}},
                },
            )
            call = self._recv(proc, STATS_DEADLINE_S)
            elapsed = time.monotonic() - t0
            self.assertIsNotNone(
                call,
                f"tools/call stats timed out after {STATS_DEADLINE_S}s "
                "(Crush hang class: tools/call ↔ roots/list deadlock)",
            )
            self.assertLess(
                elapsed,
                STATS_DEADLINE_S,
                f"stats too slow ({elapsed:.2f}s) — possible regression toward hang",
            )
            self.assertEqual(call.get("id"), 5)
            result = call.get("result") or {}
            content = result.get("content") or []
            self.assertTrue(content, f"empty tools/call result: {call}")
            text = content[0].get("text") or ""
            payload = json.loads(text)
            self.assertIn("total_units", payload)
            self.assertGreaterEqual(payload["total_units"], 0)
        finally:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    unittest.main()
