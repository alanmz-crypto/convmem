"""Tests for Claude Code CLI session jsonl adapter."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adapters.claude_session_jsonl import (
    is_claude_session_jsonl,
    parse,
    read_session_meta,
    strip_injected_context,
    text_from_message_content,
)
from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser


def _claude_record(
    *,
    rtype: str,
    content: object,
    session_id: str = "sess-abc-123",
    timestamp: str | None = "2026-09-18T12:00:00.000Z",
    cwd: str = "/tmp/project",
    is_sidechain: bool = False,
) -> dict:
    record: dict = {
        "type": rtype,
        "sessionId": session_id,
        "uuid": "rec-uuid",
        "cwd": cwd,
        "isSidechain": is_sidechain,
    }
    if timestamp is not None:
        record["timestamp"] = timestamp
    if rtype in ("user", "assistant"):
        record["message"] = {"role": rtype, "content": content}
    return record


class TestClaudeSessionJsonl(unittest.TestCase):
    def _write_claude_transcript(self, tmp: Path, rows: list[dict]) -> Path:
        root = tmp / ".claude" / "projects" / "my-project-slug"
        root.mkdir(parents=True)
        path = root / "session-uuid.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return path

    def test_is_claude_session_jsonl_detects_well_formed_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [
                    _claude_record(rtype="system", content=""),
                    _claude_record(rtype="user", content="hello"),
                ],
            )
            with mock.patch(
                "adapters.claude_session_jsonl.Path.home",
                return_value=Path(tmp),
            ):
                self.assertTrue(is_claude_session_jsonl(path))

    def test_is_claude_session_jsonl_rejects_neighbours(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            claude_like = tmp_path / "other" / "session.jsonl"
            claude_like.parent.mkdir(parents=True)
            claude_like.write_text(
                json.dumps(
                    _claude_record(rtype="user", content="not under claude/projects")
                )
                + "\n",
                encoding="utf-8",
            )
            cursor_path = (
                tmp_path
                / ".cursor"
                / "projects"
                / "foo"
                / "agent-transcripts"
                / "id"
                / "id.jsonl"
            )
            cursor_path.parent.mkdir(parents=True)
            cursor_path.write_text(
                json.dumps({"role": "user", "content": "cursor"}) + "\n",
                encoding="utf-8",
            )
            codex_path = (
                tmp_path
                / ".codex"
                / "sessions"
                / "2026"
                / "09"
                / "18"
                / "rollout-test.jsonl"
            )
            codex_path.parent.mkdir(parents=True)
            codex_path.write_text(
                json.dumps(
                    {
                        "type": "response_item",
                        "timestamp": "2026-09-18T12:00:00Z",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "hi"}],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with mock.patch(
                "adapters.claude_session_jsonl.Path.home",
                return_value=tmp_path,
            ):
                self.assertFalse(is_claude_session_jsonl(claude_like))
                self.assertFalse(is_claude_session_jsonl(cursor_path))
                self.assertFalse(is_claude_session_jsonl(codex_path))

            self.assertEqual(detect_format(cursor_path), "jsonl_cursor")
            with mock.patch(
                "adapters.codex_rollout_jsonl.Path.home",
                return_value=tmp_path,
            ):
                self.assertEqual(detect_format(codex_path), "jsonl_codex_rollout")

    def test_detect_format_and_tool_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [_claude_record(rtype="user", content="index me")],
            )
            with mock.patch(
                "adapters.claude_session_jsonl.Path.home",
                return_value=Path(tmp),
            ):
                fmt = detect_format(path)
                self.assertEqual(fmt, "jsonl_claude_session")
                self.assertEqual(TOOL_BY_FORMAT[fmt], "claude")
                parser = get_parser(path)
                self.assertIsNotNone(parser)
                messages = parser(str(path))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["content"], "index me")

    def test_parse_user_string_and_assistant_text_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [
                    _claude_record(rtype="user", content="What's the status?"),
                    _claude_record(
                        rtype="assistant",
                        content=[
                            {"type": "thinking", "thinking": "internal reasoning"},
                            {"type": "text", "text": "Looks good."},
                            {
                                "type": "tool_use",
                                "name": "bash",
                                "input": {"command": "ls"},
                            },
                        ],
                    ),
                ],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["role"], "user")
            self.assertEqual(messages[0]["content"], "What's the status?")
            self.assertEqual(messages[1]["role"], "assistant")
            self.assertEqual(messages[1]["content"], "Looks good.")
            self.assertNotIn("thinking", messages[1]["content"])
            self.assertNotIn("bash", messages[1]["content"])
            self.assertEqual(messages[0]["source_type"], "claude_session")
            self.assertEqual(messages[0]["session_id"], "sess-abc-123")
            self.assertEqual(messages[0]["workspace_directory"], "/tmp/project")

    def test_strip_injected_context_wrappers(self):
        raw = (
            "<system-reminder>\nEntire CLAUDE.md lives here\n</system-reminder>\n"
            "Actual user question\n"
            "<local-command-caveat>warn</local-command-caveat>\n"
            "<command-name>/status</command-name>"
        )
        self.assertEqual(strip_injected_context(raw), "Actual user question")

    def test_strip_injected_context_fail_closed_on_unclosed_wrapper(self):
        self.assertIsNone(
            strip_injected_context("<system-reminder>truncated injection")
        )
        self.assertIsNone(
            strip_injected_context("speech <local-command-caveat>no close")
        )

    def test_text_from_message_content_strips_list_form_wrappers(self):
        content = text_from_message_content(
            [
                {
                    "type": "text",
                    "text": (
                        "<system-reminder>boilerplate</system-reminder>"
                        "assistant answer"
                    ),
                },
                {"type": "thinking", "thinking": "drop me"},
                {
                    "type": "text",
                    "text": " second paragraph",
                },
            ]
        )
        self.assertEqual(content, "assistant answer\nsecond paragraph")

    def test_text_from_message_content_fail_closed_on_unclosed_list_block(self):
        self.assertIsNone(
            text_from_message_content(
                [{"type": "text", "text": "<system-reminder>leak"}]
            )
        )

    def test_text_from_message_content_skips_blank_or_stripped_list_blocks(self):
        self.assertEqual(
            text_from_message_content(
                [
                    {"type": "text", "text": ""},
                    {
                        "type": "text",
                        "text": "<system-reminder>only boilerplate</system-reminder>",
                    },
                    {"type": "text", "text": "   "},
                    {"type": "text", "text": "safe speech"},
                ]
            ),
            "safe speech",
        )

    def test_parse_keeps_speech_when_list_has_blank_or_stripped_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [
                    _claude_record(
                        rtype="assistant",
                        content=[
                            {"type": "text", "text": ""},
                            {
                                "type": "text",
                                "text": (
                                    "<system-reminder>injected</system-reminder>"
                                ),
                            },
                            {"type": "text", "text": "visible reply"},
                        ],
                    ),
                    _claude_record(
                        rtype="user",
                        content="<system-reminder>only opening tag",
                    ),
                ],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["content"], "visible reply")

    def test_parse_strips_list_form_wrappers_and_keeps_speech(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [
                    _claude_record(
                        rtype="assistant",
                        content=[
                            {"type": "thinking", "thinking": "internal"},
                            {
                                "type": "text",
                                "text": (
                                    "<system-reminder>injected</system-reminder>"
                                    "visible reply"
                                ),
                            },
                        ],
                    ),
                ],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["content"], "visible reply")

    def test_parse_drops_message_with_unclosed_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [
                    _claude_record(
                        rtype="user",
                        content="<system-reminder>only opening tag",
                    ),
                    _claude_record(rtype="user", content="safe follow-up"),
                ],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["content"], "safe follow-up")

    def test_parse_strips_wrappers_and_drops_empty_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [
                    _claude_record(
                        rtype="user",
                        content=(
                            "<system-reminder>boilerplate</system-reminder>"
                            "real ask"
                        ),
                    ),
                    _claude_record(
                        rtype="user",
                        content="<system-reminder>only boilerplate</system-reminder>",
                    ),
                ],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["content"], "real ask")

    def test_parse_excludes_sidechains(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [
                    _claude_record(rtype="user", content="parent turn"),
                    _claude_record(
                        rtype="assistant",
                        content=[{"type": "text", "text": "subagent reply"}],
                        is_sidechain=True,
                    ),
                ],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["content"], "parent turn")

    def test_parse_skips_non_message_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [
                    {"type": "attachment", "sessionId": "sess-abc-123"},
                    {"type": "mode", "sessionId": "sess-abc-123"},
                    _claude_record(rtype="user", content="keep me"),
                ],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["content"], "keep me")

    def test_parse_missing_timestamp_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [_claude_record(rtype="user", content="no ts", timestamp=None)],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            self.assertIsNone(messages[0]["timestamp"])

    def test_parse_tolerates_malformed_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript(
                Path(tmp),
                [_claude_record(rtype="user", content="survives")],
            )
            existing = path.read_text(encoding="utf-8")
            path.write_text("not json\n" + existing, encoding="utf-8")
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["content"], "survives")

    def test_kiro_still_classifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".kiro" / "sessions" / "hash1" / "sess_test-uuid"
            root.mkdir(parents=True)
            msg_path = root / "messages.jsonl"
            msg_path.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-29T06:29:07.854Z",
                        "payload": {"type": "user", "content": "convmem doctor"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(detect_format(msg_path), "jsonl_kiro_session")


class TestClaudeSessionJsonlInvalidUtf8(unittest.TestCase):
    def _write_claude_transcript_bytes(self, tmp: Path, parts: list[bytes]) -> Path:
        root = tmp / ".claude" / "projects" / "my-project-slug"
        root.mkdir(parents=True)
        path = root / "session-uuid.jsonl"
        path.write_bytes(b"".join(parts))
        return path

    @staticmethod
    def _invalid_utf8_line() -> bytes:
        return b"\xff\xfe stray invalid bytes\n"

    def test_read_session_meta_survives_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta_record = _claude_record(
                rtype="system",
                content="",
                session_id="sess-after-bad",
                cwd="/tmp/after-bad",
            )
            path = self._write_claude_transcript_bytes(
                Path(tmp),
                [
                    self._invalid_utf8_line(),
                    (json.dumps(meta_record) + "\n").encode("utf-8"),
                ],
            )
            meta = read_session_meta(str(path))
            self.assertEqual(meta["session_id"], "sess-after-bad")
            self.assertEqual(meta["workspace_directory"], "/tmp/after-bad")

    def test_parse_survives_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = _claude_record(rtype="user", content="before bad line")
            after = _claude_record(rtype="assistant", content="after bad line")
            path = self._write_claude_transcript_bytes(
                Path(tmp),
                [
                    (json.dumps(before) + "\n").encode("utf-8"),
                    self._invalid_utf8_line(),
                    (json.dumps(after) + "\n").encode("utf-8"),
                ],
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["content"], "before bad line")
            self.assertEqual(messages[1]["content"], "after bad line")

    def test_is_claude_session_jsonl_survives_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript_bytes(
                Path(tmp),
                [
                    (json.dumps(_claude_record(rtype="system", content="")) + "\n").encode(
                        "utf-8"
                    ),
                    self._invalid_utf8_line(),
                    (
                        json.dumps(_claude_record(rtype="user", content="probe me"))
                        + "\n"
                    ).encode("utf-8"),
                ],
            )
            with mock.patch(
                "adapters.claude_session_jsonl.Path.home",
                return_value=Path(tmp),
            ):
                self.assertTrue(is_claude_session_jsonl(path))

    def test_invalid_utf8_never_surfaces_in_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_claude_transcript_bytes(
                Path(tmp),
                [
                    (json.dumps(_claude_record(rtype="user", content="safe")) + "\n").encode(
                        "utf-8"
                    ),
                    self._invalid_utf8_line(),
                ],
            )
            meta = read_session_meta(str(path))
            messages = parse(str(path))
            serialized = json.dumps({"meta": meta, "messages": messages})
            self.assertNotIn("\xff", serialized)
            self.assertNotIn("\xfe", serialized)


if __name__ == "__main__":
    unittest.main()
