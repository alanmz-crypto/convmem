"""Tests for the OpenCode SQLite session adapter."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser
from adapters.sqlite_chat import is_sqlite_opencode_schema, parse


def _write_opencode_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE session (id TEXT PRIMARY KEY);
        CREATE TABLE message (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            data TEXT NOT NULL
        );
        CREATE TABLE part (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            time_created INTEGER NOT NULL,
            data TEXT NOT NULL
        );
        """
    )
    con.execute("INSERT INTO session VALUES (?)", ("ses-1",))
    con.executemany(
        "INSERT INTO message VALUES (?, ?, ?, ?)",
        [
            (
                "msg-user",
                "ses-1",
                1_700_000_000_000,
                json.dumps(
                    {
                        "role": "user",
                        "model": {"providerID": "openai", "modelID": "gpt-5"},
                    }
                ),
            ),
            (
                "msg-assistant",
                "ses-1",
                1_700_000_001_000,
                json.dumps(
                    {
                        "role": "assistant",
                        "providerID": "ollama",
                        "modelID": "qwen3:latest",
                    }
                ),
            ),
            # Same timestamp as the first message: distinct IDs must remain distinct.
            (
                "msg-same-time",
                "ses-1",
                1_700_000_000_000,
                json.dumps({"role": "user"}),
            ),
        ],
    )
    con.executemany(
        "INSERT INTO part VALUES (?, ?, ?, ?)",
        [
            (
                "part-user-text",
                "msg-user",
                1_700_000_000_001,
                json.dumps({"type": "text", "text": "Hello OpenCode"}),
            ),
            (
                "part-user-noise",
                "msg-user",
                1_700_000_000_002,
                json.dumps({"type": "reasoning", "text": "not user content"}),
            ),
            (
                "part-assistant-one",
                "msg-assistant",
                1_700_000_001_001,
                json.dumps({"type": "text", "text": "First part"}),
            ),
            (
                "part-assistant-two",
                "msg-assistant",
                1_700_000_001_002,
                json.dumps({"type": "text", "text": "Second part"}),
            ),
            (
                "part-same-time",
                "msg-same-time",
                1_700_000_000_003,
                json.dumps({"type": "text", "text": "Separate turn"}),
            ),
        ],
    )
    con.commit()
    con.close()


class TestOpenCodeAdapter(unittest.TestCase):
    def test_schema_requires_all_three_tables(self):
        self.assertTrue(is_sqlite_opencode_schema({"message", "part", "session"}))
        self.assertFalse(is_sqlite_opencode_schema({"message", "part"}))

    def test_detect_format_and_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.db"
            _write_opencode_db(path)
            self.assertEqual(detect_format(path), "sqlite_opencode")
            self.assertEqual(TOOL_BY_FORMAT["sqlite_opencode"], "opencode")
            self.assertIs(get_parser(path), parse)

    def test_parse_text_parts_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.db"
            _write_opencode_db(path)
            messages = parse(str(path))

        self.assertEqual([message["content"] for message in messages], [
            "Separate turn",
            "Hello OpenCode",
            "First part\n\nSecond part",
        ])
        self.assertEqual(messages[1]["session_id"], "ses-1")
        self.assertEqual(messages[1]["model"], "gpt-5")
        self.assertEqual(messages[1]["provider"], "openai")
        self.assertEqual(messages[2]["model"], "qwen3:latest")
        self.assertEqual(messages[2]["provider"], "ollama")
        self.assertEqual(messages[1]["timestamp"], "2023-11-14T22:13:20+00:00")


if __name__ == "__main__":
    unittest.main()
