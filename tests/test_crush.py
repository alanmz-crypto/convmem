"""Tests for Crush sqlite_crush adapter."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser
from adapters.sqlite_chat import parse


def _write_crush_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE goose_db_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id INTEGER NOT NULL,
            is_applied INTEGER NOT NULL,
            tstamp TIMESTAMP DEFAULT (datetime('now'))
        );
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            cost REAL NOT NULL DEFAULT 0.0,
            updated_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            parts TEXT NOT NULL DEFAULT '[]',
            model TEXT,
            provider TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            finished_at INTEGER
        );
        """
    )
    con.execute(
        "INSERT INTO sessions VALUES (?, ?, 2, 0, 0, 0.0, ?, ?)",
        ("sess-1", "Test session", 1_700_000_000_000, 1_700_000_000_000),
    )
    user_parts = json.dumps([{"type": "text", "data": {"text": "Hello crush"}}])
    assistant_parts = json.dumps(
        [
            {"type": "reasoning", "data": {"thinking": "Thinking aloud"}},
            {"type": "text", "data": {"text": "Hi there"}},
            {"type": "finish", "data": {"reason": "stop", "time": 1}},
        ]
    )
    con.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, NULL)",
        ("m1", "sess-1", "user", user_parts, 1_700_000_001_000, 1_700_000_001_000),
    )
    con.execute(
        "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        (
            "m2",
            "sess-1",
            "assistant",
            assistant_parts,
            "qwen3.5:latest",
            "ollama-research",
            1_700_000_002_000,
            1_700_000_002_000,
        ),
    )
    con.commit()
    con.close()


class TestCrushAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name) / "myproject"
        crush_dir = root / ".crush"
        crush_dir.mkdir(parents=True)
        cls.db_path = crush_dir / "crush.db"
        _write_crush_db(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_detect_format(self):
        self.assertEqual(detect_format(self.db_path), "sqlite_crush")
        self.assertEqual(TOOL_BY_FORMAT["sqlite_crush"], "crush")
        self.assertIs(get_parser(self.db_path), parse)

    def test_parse_messages(self):
        messages = parse(str(self.db_path))
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Hello crush")
        self.assertEqual(messages[0]["session_id"], "sess-1")
        self.assertIn("2023-11-14", messages[0]["timestamp"])
        self.assertEqual(messages[0]["workspace_directory"], str(self.db_path.parent.parent))

        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "Hi there")
        self.assertNotIn("Thinking aloud", messages[1]["content"])
        self.assertEqual(messages[1]["model"], "qwen3.5:latest")
        self.assertEqual(messages[1]["provider"], "ollama-research")


if __name__ == "__main__":
    unittest.main()
