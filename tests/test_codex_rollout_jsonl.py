"""Tests for Codex rollout jsonl adapter."""

import json
import tempfile
import unittest
from pathlib import Path

from adapters.codex_rollout_jsonl import is_codex_rollout_jsonl, parse
from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser


class TestCodexRolloutJsonl(unittest.TestCase):
    def test_is_codex_rollout_jsonl(self):
        home = Path.home()
        p = home / ".codex" / "sessions" / "2026" / "07" / "05" / "rollout-test.jsonl"
        self.assertTrue(is_codex_rollout_jsonl(p))
        self.assertFalse(is_codex_rollout_jsonl(home / ".codex" / "history.jsonl"))
        self.assertFalse(is_codex_rollout_jsonl(home / "other" / "rollout-x.jsonl"))

    def test_parse_user_and_assistant(self):
        with tempfile.TemporaryDirectory() as tmp:
            sessions = Path(tmp) / ".codex" / "sessions" / "2026" / "07" / "05"
            sessions.mkdir(parents=True)
            path = sessions / "rollout-sample.jsonl"
            rows = [
                {
                    "timestamp": "2026-07-06T01:58:42.252Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "Verify the bug log."}],
                    },
                },
                {
                    "timestamp": "2026-07-06T01:58:45.284Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "agent_message",
                        "message": "Checking the corpus first.",
                    },
                },
                {
                    "timestamp": "2026-07-06T01:58:45.284Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "Checking the corpus first."}],
                    },
                },
            ]
            path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

            # is_codex_rollout_jsonl uses real home — test parse directly
            messages = parse(str(path))
            self.assertGreaterEqual(len(messages), 2)
            roles = [m["role"] for m in messages]
            self.assertIn("user", roles)
            self.assertIn("assistant", roles)
            self.assertTrue(all(m.get("source_type") == "codex_rollout" for m in messages))

    def test_detect_real_rollout(self):
        root = Path.home() / ".codex" / "sessions"
        if not root.is_dir():
            self.skipTest("no ~/.codex/sessions on this machine")
        rollouts = list(root.rglob("rollout-*.jsonl"))
        if not rollouts:
            self.skipTest("no rollout files")
        path = max(rollouts, key=lambda p: p.stat().st_mtime)
        fmt = detect_format(path)
        self.assertEqual(fmt, "jsonl_codex_rollout")
        self.assertEqual(TOOL_BY_FORMAT[fmt], "codex")
        parser = get_parser(path)
        self.assertIsNotNone(parser)
        messages = parser(str(path))
        self.assertGreater(len(messages), 0)


if __name__ == "__main__":
    unittest.main()
