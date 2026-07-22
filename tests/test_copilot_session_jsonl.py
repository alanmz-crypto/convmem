"""Tests for GitHub Copilot CLI session events.jsonl adapter."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adapters.copilot_session_jsonl import (
    is_copilot_session_jsonl,
    parse,
    read_session_meta,
)
from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser


class TestCopilotSessionJsonl(unittest.TestCase):
    def test_is_copilot_session_jsonl(self):
        home = Path.home()
        p = home / ".copilot" / "session-state" / "abc-uuid" / "events.jsonl"
        self.assertTrue(is_copilot_session_jsonl(p))
        self.assertFalse(
            is_copilot_session_jsonl(home / ".copilot" / "session-store.db")
        )
        self.assertFalse(
            is_copilot_session_jsonl(home / "other" / "session-state" / "x" / "events.jsonl")
        )
        self.assertFalse(
            is_copilot_session_jsonl(
                home / ".kiro" / "sessions" / "h" / "sess_x" / "messages.jsonl"
            )
        )

    def test_parse_user_and_assistant(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp) / "sess"
            session.mkdir()
            path = session / "events.jsonl"
            (session / "workspace.yaml").write_text(
                "id: test-sess\ncwd: /tmp/project\nname: Sample Session\n",
                encoding="utf-8",
            )
            rows = [
                {
                    "type": "session.start",
                    "data": {
                        "sessionId": "test-sess",
                        "context": {"cwd": "/tmp/project"},
                    },
                    "timestamp": "2026-07-19T12:00:00.000Z",
                },
                {
                    "type": "system.message",
                    "data": {"content": "You are Copilot CLI boilerplate…"},
                    "timestamp": "2026-07-19T12:00:01.000Z",
                },
                {
                    "type": "user.message",
                    "data": {"content": "What's the repo state?"},
                    "timestamp": "2026-07-19T12:00:02.000Z",
                },
                {
                    "type": "assistant.message",
                    "data": {"content": ""},
                    "timestamp": "2026-07-19T12:00:03.000Z",
                },
                {
                    "type": "tool.execution_start",
                    "data": {"toolName": "bash"},
                    "timestamp": "2026-07-19T12:00:04.000Z",
                },
                {
                    "type": "assistant.message",
                    "data": {"content": "Looks healthy."},
                    "timestamp": "2026-07-19T12:00:05.000Z",
                },
            ]
            path.write_text(
                "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
            )

            with mock.patch(
                "adapters.copilot_session_jsonl.Path.home",
                return_value=Path(tmp),
            ):
                # is_* uses real home; parse does not — call parse directly
                messages = parse(str(path))

            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["role"], "user")
            self.assertEqual(messages[0]["content"], "What's the repo state?")
            self.assertEqual(messages[1]["role"], "assistant")
            self.assertEqual(messages[1]["content"], "Looks healthy.")
            self.assertTrue(
                all(m.get("source_type") == "copilot_session" for m in messages)
            )
            self.assertEqual(messages[0]["session_id"], "test-sess")
            self.assertEqual(messages[0]["workspace_directory"], "/tmp/project")

            meta = read_session_meta(str(path))
            self.assertEqual(meta["title"], "Sample Session")
            self.assertEqual(meta["workspace_directory"], "/tmp/project")

    def test_detect_real_session(self):
        root = Path.home() / ".copilot" / "session-state"
        if not root.is_dir():
            self.skipTest("no ~/.copilot/session-state on this machine")
        events = list(root.rglob("events.jsonl"))
        if not events:
            self.skipTest("no Copilot events.jsonl files")
        path = max(events, key=lambda p: p.stat().st_mtime)
        fmt = detect_format(path)
        self.assertEqual(fmt, "jsonl_copilot_session")
        self.assertEqual(TOOL_BY_FORMAT[fmt], "copilot")
        parser = get_parser(path)
        assert parser is not None
        parsed = parser(str(path))
        self.assertTrue(parsed, msg=f"empty parse for {path}")
        self.assertIn(parsed[0].get("role"), ("user", "assistant"))
