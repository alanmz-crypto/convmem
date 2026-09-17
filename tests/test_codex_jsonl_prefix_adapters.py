"""S1 — Codex complete-prefix adapters and auditable line outcomes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.codex_history_jsonl import parse, parse_complete_prefix
from adapters.codex_rollout_jsonl import (
    parse as parse_rollout,
    parse_complete_prefix as parse_rollout_prefix,
)
from adapters.jsonl_prefix import complete_line_outcomes_cover_prefix


def _history_record(text: str, **extra) -> bytes:
    row = {"text": text, "session_id": "sess", "ts": 1_700_000_000}
    row.update(extra)
    return (json.dumps(row) + "\n").encode("utf-8")


def _rollout_record(role: str, text: str, *, rtype: str = "response_item") -> bytes:
    payload_type = "user_message" if role == "user" else "agent_message"
    row = {
        "type": rtype,
        "timestamp": "2026-01-01T00:00:00Z",
        "payload": {"type": payload_type, "message": text},
    }
    return (json.dumps(row) + "\n").encode("utf-8")


@pytest.fixture
def codex_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_history_prefix_matches_legacy_parse(codex_home: Path) -> None:
    path = codex_home / ".codex" / "history.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(_history_record("one") + _history_record("two"))
    assert parse(str(path)) == parse_complete_prefix(str(path)).messages


def test_history_line_outcomes_cover_every_complete_line(codex_home: Path) -> None:
    path = codex_home / ".codex" / "history.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(
        b"\n"
        + _history_record("ok")
        + b"{not-json}\n"
        + bytes.fromhex("c3") + b"\n"  # invalid utf-8 line
        + _history_record("after")
    )
    view = parse_complete_prefix(str(path))
    assert complete_line_outcomes_cover_prefix(view.line_outcomes, view.complete_boundary)
    kinds = [item.outcome for item in view.line_outcomes]
    assert "skipped_blank" in kinds
    assert "skipped_malformed_json" in kinds
    assert "skipped_invalid_utf8" in kinds
    assert kinds.count("emitted") == 2
    assert len(view.messages) == 2


def test_history_partial_line_excluded_until_newline(codex_home: Path) -> None:
    path = codex_home / ".codex" / "history.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(_history_record("stable"))
    first = parse_complete_prefix(str(path))
    with path.open("ab") as handle:
        handle.write(b'{"text":"part')
    second = parse_complete_prefix(str(path))
    assert second.complete_boundary == first.complete_boundary
    assert second.messages == first.messages
    with path.open("ab") as handle:
        handle.write(b'ial"}\n')
    third = parse_complete_prefix(str(path))
    assert len(third.messages) == 2


def test_history_skipped_no_message_is_not_emitted(codex_home: Path) -> None:
    path = codex_home / ".codex" / "history.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(json.dumps({"session_id": "x"}).encode() + b"\n")
    view = parse_complete_prefix(str(path))
    assert view.messages == []
    assert view.line_outcomes[0].outcome == "skipped_no_message"


def test_rollout_prefix_matches_legacy_parse(codex_home: Path) -> None:
    path = (
        codex_home
        / ".codex"
        / "sessions"
        / "2026"
        / "rollout-test.jsonl"
    )
    path.parent.mkdir(parents=True)
    path.write_bytes(_rollout_record("user", "hi") + _rollout_record("assistant", "yo"))
    assert parse_rollout(str(path)) == parse_rollout_prefix(str(path)).messages


def test_rollout_line_outcomes_cover_ignored_and_malformed(codex_home: Path) -> None:
    path = (
        codex_home
        / ".codex"
        / "sessions"
        / "2026"
        / "rollout-matrix.jsonl"
    )
    path.parent.mkdir(parents=True)
    path.write_bytes(
        _rollout_record("user", "one")
        + json.dumps({"type": "event_msg", "payload": {"type": "tool_call"}}).encode()
        + b"\n"
        + b"{bad\n"
        + _rollout_record("assistant", "two")
    )
    view = parse_rollout_prefix(str(path))
    assert complete_line_outcomes_cover_prefix(view.line_outcomes, view.complete_boundary)
    assert len(view.messages) == 2
    assert sum(1 for item in view.line_outcomes if item.outcome == "skipped_no_message") >= 1
    assert any(item.outcome == "skipped_malformed_json" for item in view.line_outcomes)


def test_rollout_partial_line_excluded_until_newline(codex_home: Path) -> None:
    path = (
        codex_home
        / ".codex"
        / "sessions"
        / "2026"
        / "rollout-partial.jsonl"
    )
    path.parent.mkdir(parents=True)
    path.write_bytes(_rollout_record("user", "stable"))
    first = parse_rollout_prefix(str(path))
    with path.open("ab") as handle:
        handle.write(b'{"type":"response_item","payload":')
    second = parse_rollout_prefix(str(path))
    assert second.complete_boundary == first.complete_boundary
    with path.open("ab") as handle:
        handle.write(
            b'{"type":"user_message","message":"done"}}\n'
        )
    third = parse_rollout_prefix(str(path))
    assert len(third.messages) == 2
