"""Claude complete-prefix adapter tests for Gate 2 isolated route."""

# pylint: disable=redefined-outer-name

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from adapters.claude_session_jsonl import parse, parse_complete_prefix
from adapters.jsonl_prefix import complete_line_outcomes_cover_prefix


def _claude_record(
    *,
    rtype: str,
    content: object,
    session_id: str = "sess-claude-prefix",
    is_sidechain: bool = False,
) -> bytes:
    row = {
        "type": rtype,
        "sessionId": session_id,
        "uuid": "rec-prefix",
        "cwd": "/tmp/project",
        "isSidechain": is_sidechain,
        "timestamp": "2026-09-18T12:00:00.000Z",
    }
    if rtype in ("user", "assistant"):
        row["message"] = {"role": rtype, "content": content}
    return (json.dumps(row) + "\n").encode("utf-8")


@pytest.fixture
def claude_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _write_transcript(home: Path, *chunks: bytes) -> Path:
    path = home / ".claude" / "projects" / "prefix-slug" / "session.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"".join(chunks))
    return path


def test_claude_prefix_matches_legacy_parse(claude_home: Path) -> None:
    path = _write_transcript(
        claude_home,
        json.dumps({"type": "system", "sessionId": "sess-claude-prefix"}).encode()
        + b"\n",
        _claude_record(rtype="user", content="one"),
        _claude_record(rtype="assistant", content=[{"type": "text", "text": "two"}]),
    )
    with mock.patch(
        "adapters.claude_session_jsonl.Path.home",
        return_value=claude_home,
    ):
        assert parse(str(path)) == parse_complete_prefix(str(path)).messages


def test_claude_line_outcomes_cover_every_complete_line(claude_home: Path) -> None:
    path = _write_transcript(
        claude_home,
        b"\n",
        _claude_record(rtype="user", content="ok"),
        b"{not-json}\n",
        bytes.fromhex("c3") + b"\n",
        _claude_record(
            rtype="assistant",
            content=[
                {"type": "thinking", "thinking": "drop"},
                {"type": "text", "text": "after"},
            ],
        ),
        _claude_record(
            rtype="assistant",
            content=[{"type": "text", "text": "sidechain reply"}],
            is_sidechain=True,
        ),
        _claude_record(
            rtype="user",
            content=(
                "<system-reminder>injected CLAUDE.md</system-reminder>real ask"
            ),
        ),
        _claude_record(
            rtype="user",
            content="<system-reminder>only boilerplate</system-reminder>",
        ),
    )
    view = parse_complete_prefix(str(path))
    assert complete_line_outcomes_cover_prefix(view.line_outcomes, view.complete_boundary)
    kinds = [item.outcome for item in view.line_outcomes]
    assert "skipped_blank" in kinds
    assert "skipped_malformed_json" in kinds
    assert "skipped_invalid_utf8" in kinds
    assert kinds.count("emitted") == 3
    assert len(view.messages) == 3
    assert view.messages[0]["content"] == "ok"
    assert view.messages[1]["content"] == "after"
    assert view.messages[2]["content"] == "real ask"


def test_claude_partial_line_excluded_until_newline(claude_home: Path) -> None:
    path = _write_transcript(
        claude_home,
        _claude_record(rtype="user", content="stable"),
    )
    first = parse_complete_prefix(str(path))
    with path.open("ab") as handle:
        handle.write(b'{"type":"user","message":{"role":"user","content":"part')
    second = parse_complete_prefix(str(path))
    assert second.complete_boundary == first.complete_boundary
    assert second.messages == first.messages
    with path.open("ab") as handle:
        handle.write(b'ial"}}\n')
    third = parse_complete_prefix(str(path))
    assert len(third.messages) == 2


def test_claude_prefix_digest_is_stable(claude_home: Path) -> None:
    path = _write_transcript(
        claude_home,
        _claude_record(rtype="user", content="digest-check"),
    )
    first = parse_complete_prefix(str(path))
    second = parse_complete_prefix(str(path))
    assert first.prefix_sha256 == second.prefix_sha256
    assert first.complete_boundary == second.complete_boundary
