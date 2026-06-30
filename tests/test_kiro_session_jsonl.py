"""Tests for kiro-cli session jsonl adapter."""

import json
import tempfile
import unittest
from pathlib import Path

from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser
from adapters.kiro_session_jsonl import is_kiro_session_jsonl, parse, read_session_meta


class TestKiroSessionJsonl(unittest.TestCase):
  def test_is_kiro_session_jsonl_matches_sess_parent(self):
    p = Path(
      "/home/user/.kiro/sessions/abc123/sess_uuid-here/messages.jsonl"
    )
    self.assertTrue(is_kiro_session_jsonl(p))

  def test_is_kiro_session_jsonl_rejects_cli_history(self):
    p = Path("/home/user/.kiro/sessions/cli/sess_abc.history")
    self.assertFalse(is_kiro_session_jsonl(p))

  def test_is_kiro_session_jsonl_rejects_snapshots(self):
    p = Path(
      "/home/user/.kiro/sessions/hash/snapshots/foo/messages.jsonl"
    )
    self.assertFalse(is_kiro_session_jsonl(p))

  def test_is_kiro_session_jsonl_rejects_cursor_transcripts(self):
    p = Path(
      "/home/user/.cursor/projects/foo/agent-transcripts/id/id.jsonl"
    )
    self.assertFalse(is_kiro_session_jsonl(p))

  def test_detect_format_and_parser(self):
    with tempfile.TemporaryDirectory() as tmp:
      root = Path(tmp) / ".kiro" / "sessions" / "hash1" / "sess_test-uuid"
      root.mkdir(parents=True)
      msg_path = root / "messages.jsonl"
      lines = [
        {
          "timestamp": "2026-06-29T06:29:07.854Z",
          "payload": {"type": "user", "content": "convmem doctor"},
        },
        {
          "timestamp": "2026-06-29T06:29:07.857Z",
          "payload": {"type": "turn_start", "executionId": "x"},
        },
        {
          "timestamp": "2026-06-29T06:33:32.102Z",
          "payload": {
            "type": "assistant",
            "content": "doctor: all checks passed",
          },
        },
      ]
      with open(msg_path, "w", encoding="utf-8") as f:
        for row in lines:
          f.write(json.dumps(row) + "\n")
      with open(root / "session.json", "w", encoding="utf-8") as f:
        json.dump(
          {
            "id": "sess_test-uuid",
            "title": "System logs",
            "workspacePaths": ["/home/user/Projects/convmem"],
          },
          f,
        )

      fmt = detect_format(msg_path)
      self.assertEqual(fmt, "jsonl_kiro_session")
      self.assertEqual(TOOL_BY_FORMAT[fmt], "kiro")
      parser = get_parser(msg_path)
      self.assertIsNotNone(parser)
      messages = parser(str(msg_path))
      self.assertEqual(len(messages), 2)
      self.assertEqual(messages[0]["role"], "user")
      self.assertEqual(messages[0]["content"], "convmem doctor")
      self.assertEqual(messages[0]["session_id"], "sess_test-uuid")
      self.assertEqual(
        messages[0]["workspace_directory"], "/home/user/Projects/convmem"
      )

  def test_read_session_meta_missing_file(self):
    self.assertEqual(read_session_meta("/nonexistent/messages.jsonl"), {})


if __name__ == "__main__":
  unittest.main()
