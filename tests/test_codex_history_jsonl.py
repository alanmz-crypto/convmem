"""Tests for Codex history.jsonl adapter."""

import json
import tempfile
import unittest
from pathlib import Path

from adapters.codex_history_jsonl import is_codex_history_jsonl, parse
from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser


class TestCodexHistoryJsonl(unittest.TestCase):
  def test_is_codex_history_jsonl(self):
    home = Path.home()
    self.assertTrue(is_codex_history_jsonl(home / ".codex" / "history.jsonl"))
    self.assertFalse(is_codex_history_jsonl(home / ".codex" / "other.jsonl"))

  def test_parse_prompt_only_metadata(self):
    with tempfile.TemporaryDirectory() as tmp:
      codex_dir = Path(tmp) / ".codex"
      codex_dir.mkdir()
      path = codex_dir / "history.jsonl"
      row = {
        "session_id": "sess-abc",
        "ts": 1_700_000_000,
        "text": "Help me refactor hybrid-rag",
      }
      path.write_text(json.dumps(row) + "\n", encoding="utf-8")

      # is_codex_history_jsonl uses real home path — test parse directly
      messages = parse(str(path))
      self.assertEqual(len(messages), 1)
      self.assertEqual(messages[0]["role"], "user")
      self.assertEqual(messages[0]["source_type"], "prompt_only")
      self.assertEqual(messages[0]["session_id"], "sess-abc")

  def test_detect_real_home_path(self):
    path = Path.home() / ".codex" / "history.jsonl"
    if not path.is_file():
      self.skipTest("no ~/.codex/history.jsonl on this machine")
    fmt = detect_format(path)
    self.assertEqual(fmt, "jsonl_codex_history")
    self.assertEqual(TOOL_BY_FORMAT[fmt], "codex")
    parser = get_parser(path)
    self.assertIsNotNone(parser)
    messages = parser(str(path))
    self.assertGreater(len(messages), 0)
    self.assertEqual(messages[0].get("source_type"), "prompt_only")


if __name__ == "__main__":
  unittest.main()
