"""Tests for Cursor store.db (sqlite_cursor_store) adapter."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from adapters.detect import detect_format, get_parser
from adapters.sqlite_chat import (
    _cursor_normalize_content,
    _cursor_root_blob_ids,
    parse,
)


def _write_store_db(path: Path, *, messages: list[dict], root_id: str = "aa" * 32) -> None:
    msg_ids: list[str] = []
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE meta (key INTEGER PRIMARY KEY, value TEXT)")
    con.execute("CREATE TABLE blobs (id TEXT PRIMARY KEY, data BLOB)")

    for i, msg in enumerate(messages):
        blob_id = f"{i:064x}"[:64]
        con.execute(
            "INSERT INTO blobs (id, data) VALUES (?, ?)",
            (blob_id, json.dumps(msg).encode()),
        )
        msg_ids.append(blob_id)

    root_data = b"".join(b"\x0a\x20" + bytes.fromhex(blob_id) for blob_id in msg_ids)
    con.execute("INSERT INTO blobs (id, data) VALUES (?, ?)", (root_id, root_data))

    meta = {
        "agentId": "test-agent",
        "latestRootBlobId": root_id,
        "name": "Test Chat",
        "createdAt": 1_700_000_000_000,
    }
    con.execute(
        "INSERT INTO meta (key, value) VALUES (0, ?)",
        (meta["latestRootBlobId"] and json.dumps(meta).encode().hex(),),
    )
    con.commit()
    con.close()


class TestCursorStoreAdapter(unittest.TestCase):
    def test_normalize_content(self):
        self.assertEqual(_cursor_normalize_content("hello"), "hello")
        blocks = [
            {"type": "text", "text": "Hi"},
            {"type": "tool_use", "name": "bash"},
            {"type": "text", "text": "there"},
        ]
        self.assertEqual(_cursor_normalize_content(blocks), "Hi\nthere")

    def test_root_blob_ids(self):
        ids = ["ab" * 32, "cd" * 32]
        root = b"".join(b"\x0a\x20" + bytes.fromhex(i) for i in ids)
        self.assertEqual(_cursor_root_blob_ids(root), ids)

    def test_parse_synthetic_db(self):
        tmp = tempfile.TemporaryDirectory()
        chat_dir = Path(tmp.name) / "composer-uuid-1234"
        chat_dir.mkdir()
        db_path = chat_dir / "store.db"
        _write_store_db(
            db_path,
            messages=[
                {"role": "system", "content": "ignored"},
                {"role": "user", "content": "Hello store"},
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Hi back"}],
                },
                {"role": "tool", "content": "noise"},
            ],
        )

        self.assertEqual(detect_format(db_path), "sqlite_cursor_store")
        self.assertIs(get_parser(db_path), parse)

        messages = parse(str(db_path))
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "Hello store")
        self.assertEqual(messages[0]["session_id"], "composer-uuid-1234")
        self.assertEqual(messages[1]["content"], "Hi back")

        tmp.cleanup()

    def test_richest_live_db_if_present(self):
        live = Path(
            "/home/lauer/.config/cursor/chats/1427524c79cf9b6f124866b167841e16/"
            "5d3e6fdf-9bbd-4f90-aca7-6c21f9c8af18/store.db"
        )
        if not live.is_file():
            self.skipTest("live store.db not present")
        messages = parse(str(live))
        self.assertGreaterEqual(len(messages), 14)
        roles = {m["role"] for m in messages}
        self.assertEqual(roles, {"user", "assistant"})
        self.assertEqual(sum(1 for m in messages if m["role"] == "user"), 4)


if __name__ == "__main__":
    unittest.main()
