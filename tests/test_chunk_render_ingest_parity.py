# pylint: disable=duplicate-code
"""Parity between chunk_render helpers and ingest's pinned renderer."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from adapters.detect import get_parser
from chunk_render import (
    chunk_date as render_chunk_date,
    load_processed as render_load_processed,
    path_is_excluded as render_path_is_excluded,
    processed_path_str as render_processed_path_str,
    render_chunk as render_render_chunk,
    render_chunk_message_views as render_render_chunk_message_views,
)
from ingest import (
    _chunk_date as ingest_chunk_date,
    _path_is_excluded as ingest_path_is_excluded,
    _processed_path_str as ingest_processed_path_str,
    load_processed as ingest_load_processed,
    render_chunk as ingest_render_chunk,
    render_chunk_message_views as ingest_render_chunk_message_views,
)
from tests.incremental_jsonl_helpers import (
    write_codex_history_source,
    write_codex_rollout_source,
)
from tests.test_crush import _write_crush_db
from tests.test_full_chunk_expansion import (
    _cursor_line,
    _cursor_source,
    _kiro_source,
)

pytest_plugins = ["tests.test_full_chunk_expansion"]

_BUDGETS = (150, 151, 300, 10_000, 50_000)


def _assert_render_parity(messages: list[dict], total_budget: int) -> None:
    assert render_render_chunk_message_views(messages, total_budget=total_budget) == (
        ingest_render_chunk_message_views(messages, total_budget=total_budget)
    )
    assert render_render_chunk(messages, total_budget=total_budget) == ingest_render_chunk(
        messages, total_budget=total_budget
    )
    assert render_chunk_date(messages) == ingest_chunk_date(messages)


def _message_windows(messages: list[dict]) -> list[list[dict]]:
    windows: list[list[dict]] = [[]]
    if not messages:
        return windows
    windows.append(messages[0:1])
    if len(messages) >= 2:
        windows.append(messages[0:2])
    windows.append(messages)
    return windows


def _claude_source(home: Path) -> Path:
    def claude_row(rtype: str, content: str) -> dict:
        return {
            "type": rtype,
            "sessionId": "sess-claude-parity",
            "message": {"role": rtype, "content": content},
            "timestamp": "2026-01-01T00:00:00.000Z",
        }

    root = home / ".claude" / "projects" / "slug"
    root.mkdir(parents=True)
    path = root / "sess.jsonl"
    rows = [
        claude_row("user", "claude-parity-user"),
        claude_row("assistant", "claude-parity-assistant"),
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path.resolve()


def _copilot_source(home: Path) -> Path:
    session_dir = home / ".copilot" / "session-state" / "uuid-parity"
    session_dir.mkdir(parents=True)
    path = session_dir / "events.jsonl"
    rows = [
        {
            "type": "user.message",
            "timestamp": "2026-01-01T00:00:00Z",
            "data": {"content": "copilot parity user"},
        },
        {
            "type": "assistant.message",
            "timestamp": "2026-01-01T00:00:01Z",
            "data": {"content": "copilot parity assistant"},
        },
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path.resolve()


def _kiro_sqlite_source(home: Path) -> Path:
    db_path = home / ".local" / "share" / "kiro-cli" / "data.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "conversation_id": "c1",
        "history": [
            {
                "user": {"content": {"Prompt": {"prompt": "kiro sqlite parity user"}}},
                "assistant": {
                    "Response": {"content": "kiro sqlite parity assistant"},
                },
            }
        ],
    }
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE conversations_v2 (value TEXT)")
    conn.execute("INSERT INTO conversations_v2 VALUES (?)", (json.dumps(payload),))
    conn.commit()
    conn.close()
    return db_path.resolve()


def _expansion_fixture_messages(home: Path) -> list[tuple[str, list[dict]]]:
    catalog: list[tuple[str, list[dict]]] = []

    cursor_path = _cursor_source(
        home,
        [
            _cursor_line("user", "parity cursor user"),
            _cursor_line("assistant", "parity cursor assistant"),
        ],
    )
    catalog.append(("jsonl_cursor", get_parser(cursor_path)(str(cursor_path))))

    for fmt_id, writer in (
        ("jsonl_codex_rollout", lambda: write_codex_rollout_source(home, 4, name="rollout-parity")),
        ("jsonl_codex_history", lambda: write_codex_history_source(home, 4)),
        ("jsonl_kiro_session", lambda: _kiro_source(home, 4)),
    ):
        path = writer().resolve()
        catalog.append((fmt_id, get_parser(path)(str(path))))

    claude_path = _claude_source(home)
    catalog.append(("jsonl_claude_session", get_parser(claude_path)(str(claude_path))))

    copilot_path = _copilot_source(home)
    catalog.append(("jsonl_copilot_session", get_parser(copilot_path)(str(copilot_path))))

    crush_dir = home / "proj" / ".crush"
    crush_dir.mkdir(parents=True)
    crush_path = crush_dir / "crush.db"
    _write_crush_db(crush_path)
    crush_path = crush_path.resolve()
    catalog.append(("sqlite_crush", get_parser(crush_path)(str(crush_path))))

    kiro_db = _kiro_sqlite_source(home)
    catalog.append(("sqlite_kiro", get_parser(kiro_db)(str(kiro_db))))

    return catalog


def _synthetic_message_sets() -> list[tuple[str, list[dict]]]:
    return [
        ("empty", []),
        ("blank_content", [{"role": "user", "content": "   "}]),
        ("unicode", [{"role": "user", "content": "日本語 🎉", "timestamp": "2026-06-01T00:00:00Z"}]),
        ("long_single", [{"role": "user", "content": "x" * 25_000}]),
        (
            "many_turns",
            [{"role": f"role-{i}", "content": f"payload-{i}-" + ("z" * 400)} for i in range(30)],
        ),
    ]


def _parity_cases(home: Path) -> Iterator[tuple[str, list[dict]]]:
    for fixture_id, messages in _expansion_fixture_messages(home):
        yield fixture_id, messages
    yield from _synthetic_message_sets()


def test_render_and_chunk_date_parity_on_expansion_fixtures(expand_env) -> None:
    _cfg, _store, home = expand_env
    for _case_id, messages in _parity_cases(home):
        for window in _message_windows(messages):
            for budget in _BUDGETS:
                _assert_render_parity(window, budget)


def test_load_processed_parity(tmp_path: Path) -> None:
    missing = tmp_path / "missing-processed.json"
    assert ingest_load_processed(str(missing)) == render_load_processed(str(missing)) == {}

    valid = tmp_path / "processed.json"
    payload = {"abc123": {"path": "/tmp/x", "excluded": False}}
    valid.write_text(json.dumps(payload), encoding="utf-8")
    assert ingest_load_processed(str(valid)) == render_load_processed(str(valid))

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not-json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="processed.json corrupt"):
        ingest_load_processed(str(corrupt))
    with pytest.raises(RuntimeError, match="processed.json corrupt"):
        render_load_processed(str(corrupt))


def test_processed_path_and_exclusion_parity(tmp_path: Path, expand_env) -> None:
    _cfg, _store, home = expand_env
    path = _cursor_source(home, [_cursor_line("user", "exclusion parity")])
    resolved_ingest = ingest_processed_path_str(str(path))
    resolved_render = render_processed_path_str(str(path))
    assert resolved_ingest == resolved_render

    processed = {
        "deadbeef": {
            "path": str(path),
            "excluded": True,
            "reason": "noise",
        }
    }
    assert ingest_path_is_excluded(processed, resolved_ingest) == render_path_is_excluded(
        processed, resolved_render
    )
    assert ingest_path_is_excluded(processed, resolved_ingest) is True

    other = tmp_path / "other.jsonl"
    other.write_text("{}", encoding="utf-8")
    other_key = ingest_processed_path_str(str(other))
    assert ingest_path_is_excluded(processed, other_key) == render_path_is_excluded(
        processed, other_key
    )
    assert ingest_path_is_excluded(processed, other_key) is False
