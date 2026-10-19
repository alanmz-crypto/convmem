"""Hermetic tests for read-only full-chunk expansion."""

# pylint: disable=protected-access

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser
from chunk_expand import (
    DEFAULT_MAX_CHARS,
    expand_record,
    format_expand_output,
    redact_secrets,
    truncate_text,
)
from ingest import render_chunk, render_chunk_message_views
from provenance_binding import attach_unit_provenance, build_ingest_envelope, projection_metadata
from tests.incremental_jsonl_helpers import (
    kiro_record,
    write_codex_history_source,
    write_codex_rollout_source,
)
from tests.test_crush import _write_crush_db


def _cfg(tmp_path: Path) -> dict:
    data = tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    return {
        "models": {
            "summarize_model": "fake",
            "distill_model": "fake",
            "embed_model": "fake",
            "ollama_host": "http://127.0.0.1:9",
        },
        "index": {
            "chroma_dir": str(data / "chroma"),
            "processed_log": str(data / "processed.json"),
            "units_export": str(data / "units.jsonl"),
            "chunk_size": 4,
            "chunk_overlap": 0,
        },
    }


def _envelope_for_window(
    *,
    source_path: str,
    window: list[dict],
    start: int,
    end: int,
    sha: str,
) -> dict:
    views = render_chunk_message_views(window)
    envelope = build_ingest_envelope(
        records=window,
        consumed_views=views,
        source_identity=source_path,
        locator_prefix=f"chunk:{start}",
        source_type="external",
        transformer_class="distill",
        transformer_identity="fake-distill",
        transformer_version="distill-v1",
        derivation_kind="distill",
        producer_class="agent",
        producer_assurance="claimed",
        selection_parameters={
            "chunk_start": start,
            "chunk_end": end,
            "rendered_chunk_sha256": sha,
        },
        provider_payload={},
        recipe_id="normal-ingest-distill-v1",
        recipe_spec={"kind": "normal-ingest-distill-v1"},
        output_locator=f"{source_path}#chunk:{start}:unit:0",
        output_value={"summary": "fixture"},
    )
    unit = attach_unit_provenance(
        {
            "id": "fixture-unit",
            "title": "Fixture",
            "summary": "fixture",
            "keywords": [],
            "source_path": source_path,
        },
        envelope,
    )
    return projection_metadata(unit)


def _seed_unit(
    store,
    *,
    unit_id: str,
    source_path: str,
    start: int,
    end: int,
    window: list[dict],
    tool: str,
) -> None:
    text = render_chunk(window)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    meta = {
        "id": unit_id,
        "title": "Fixture chunk",
        "source_path": source_path,
        "start_offset": start,
        "end_offset": end,
        "tool": tool,
    }
    meta.update(
        _envelope_for_window(
            source_path=source_path,
            window=window,
            start=start,
            end=end,
            sha=sha,
        )
    )
    store.add_unit(unit_id, "fixture document", [0.1] * 8, meta)


def _cursor_source(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "agent-transcripts" / "sess" / "chat.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path.resolve()


def _kiro_source(home: Path, count: int = 4) -> Path:
    session_dir = home / ".kiro" / "sessions" / "abc" / "sess_expand"
    session_dir.mkdir(parents=True)
    path = session_dir / "messages.jsonl"
    path.write_bytes(b"".join(kiro_record(i) for i in range(count)))
    (session_dir / "session.json").write_text(
        json.dumps({"id": "sess_expand", "workspacePaths": [str(home)]}),
        encoding="utf-8",
    )
    return path.resolve()


def _cursor_line(role: str, text: str) -> str:
    return json.dumps(
        {
            "role": role,
            "message": {"content": [{"type": "text", "text": text}]},
        }
    )


@pytest.fixture
def expand_env(tmp_path, monkeypatch):
    import config

    cfg = _cfg(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    from chroma_store import ChromaStore

    store = ChromaStore(cfg["index"]["chroma_dir"])
    yield cfg, store, home
    store.close()


def test_redact_and_truncate_helpers() -> None:
    assert "[REDACTED]" in redact_secrets("key sk-abcdefghijklmnopqrstuvwxyz")
    assert "Bearer [REDACTED]" in redact_secrets("Authorization: Bearer secret-token-xyz")
    long_text = "x" * 100
    clipped, truncated = truncate_text(long_text, 40)
    assert truncated
    assert "truncated" in clipped


def test_exact_cursor_chunk(expand_env) -> None:
    cfg, store, home = expand_env
    path = _cursor_source(
        home,
        [_cursor_line("user", "hello expand"), _cursor_line("assistant", "world")],
    )
    parser = get_parser(path)
    messages = parser(str(path))
    _seed_unit(
        store,
        unit_id="unit-cursor-1",
        source_path=str(path),
        start=0,
        end=1,
        window=messages[0:2],
        tool="cursor",
    )
    result = expand_record("unit-cursor-1", cfg=cfg)
    assert result.status == "exact"
    assert "hello expand" in result.text
    assert "world" in result.text


@pytest.mark.parametrize(
    "writer",
    [
        lambda root: write_codex_rollout_source(root, 4, name="rollout-expand"),
        lambda root: write_codex_history_source(root, 4),
        lambda root: _kiro_source(root, 4),
    ],
    ids=["codex_rollout", "codex_history", "kiro"],
)
def test_exact_jsonl_adapters(expand_env, writer) -> None:
    cfg, store, home = expand_env
    path = writer(home).resolve()
    fmt = detect_format(path)
    assert fmt in {
        "jsonl_codex_rollout",
        "jsonl_codex_history",
        "jsonl_kiro_session",
    }
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id=f"unit-{fmt}",
        source_path=str(path),
        start=0,
        end=1,
        window=messages[0:2],
        tool=TOOL_BY_FORMAT[fmt],
    )
    result = expand_record(f"unit-{fmt}", cfg=cfg)
    assert result.status == "exact"
    assert result.format == fmt
    assert result.text.strip()


def test_exact_claude_session(expand_env) -> None:
    cfg, store, home = expand_env

    def claude_row(rtype: str, content: str) -> dict:
        return {
            "type": rtype,
            "sessionId": "sess-claude",
            "message": {"role": rtype, "content": content},
            "timestamp": "2026-01-01T00:00:00.000Z",
        }

    root = home / ".claude" / "projects" / "slug"
    root.mkdir(parents=True)
    path = root / "sess.jsonl"
    rows = [
        claude_row("user", "claude-expand-user"),
        claude_row("assistant", "claude-expand-assistant"),
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    path = path.resolve()
    assert detect_format(path) == "jsonl_claude_session"
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-claude",
        source_path=str(path),
        start=0,
        end=1,
        window=messages[0:2],
        tool="claude",
    )
    result = expand_record("unit-claude", cfg=cfg)
    assert result.status == "exact"
    assert "claude-expand-user" in result.text


def test_exact_copilot_events(expand_env) -> None:
    cfg, store, home = expand_env
    session_dir = home / ".copilot" / "session-state" / "uuid-1"
    session_dir.mkdir(parents=True)
    path = session_dir / "events.jsonl"
    rows = [
        {
            "type": "user.message",
            "timestamp": "2026-01-01T00:00:00Z",
            "data": {"content": "copilot user"},
        },
        {
            "type": "assistant.message",
            "timestamp": "2026-01-01T00:00:01Z",
            "data": {"content": "copilot assistant"},
        },
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    path = path.resolve()
    assert detect_format(path) == "jsonl_copilot_session"
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-copilot",
        source_path=str(path),
        start=0,
        end=1,
        window=messages[0:2],
        tool="copilot",
    )
    result = expand_record("unit-copilot", cfg=cfg)
    assert result.status == "exact"
    assert "copilot user" in result.text


def test_exact_crush_sqlite(expand_env) -> None:
    cfg, store, home = expand_env
    root = home / "proj"
    crush_dir = root / ".crush"
    crush_dir.mkdir(parents=True)
    db_path = crush_dir / "crush.db"
    _write_crush_db(db_path)
    path = db_path.resolve()
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-crush",
        source_path=str(path),
        start=0,
        end=1,
        window=messages[0:2],
        tool="crush",
    )
    result = expand_record("unit-crush", cfg=cfg)
    assert result.status == "exact"
    assert "Hello crush" in result.text


def test_drifted_when_source_changes(expand_env) -> None:
    cfg, store, home = expand_env
    path = _cursor_source(
        home,
        [_cursor_line("user", "original"), _cursor_line("assistant", "tail")],
    )
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-drift",
        source_path=str(path),
        start=0,
        end=1,
        window=messages[0:2],
        tool="cursor",
    )
    path.write_text(
        _cursor_line("user", "changed after index") + "\n"
        + _cursor_line("assistant", "tail") + "\n",
        encoding="utf-8",
    )
    result = expand_record("unit-drift", cfg=cfg)
    assert result.status == "drifted"
    assert result.warning
    assert "changed after index" in result.text


def test_missing_source_file(expand_env) -> None:
    cfg, store, home = expand_env
    path = _cursor_source(home, [_cursor_line("user", "gone soon")])
    fake_messages = [{"role": "user", "content": "x", "timestamp": "2026-01-01"}]
    _seed_unit(
        store,
        unit_id="unit-missing",
        source_path=str(path),
        start=0,
        end=0,
        window=fake_messages,
        tool="cursor",
    )
    path.unlink()
    result = expand_record("unit-missing", cfg=cfg)
    assert result.status == "missing"


def test_excluded_source_still_expands(expand_env) -> None:
    cfg, store, home = expand_env
    path = _cursor_source(
        home,
        [_cursor_line("user", "secret")],
    )
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-excluded",
        source_path=str(path),
        start=0,
        end=0,
        window=messages[0:1],
        tool="cursor",
    )
    processed_path = Path(cfg["index"]["processed_log"])
    processed_path.write_text(
        json.dumps(
            {
                "deadbeef": {
                    "path": str(path),
                    "excluded": True,
                    "reason": "noise",
                }
            }
        ),
        encoding="utf-8",
    )
    result = expand_record("unit-excluded", cfg=cfg)
    assert result.status == "exact"
    assert "secret" in result.text
    assert "archived from re-indexing" in (result.warning or "").lower()


def test_not_session_inter_model_doc(expand_env, tmp_path) -> None:
    cfg, store, _home = expand_env
    path = tmp_path / "docs" / "inter-model" / "handoff.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Handoff\n\nBody.\n", encoding="utf-8")
    resolved = str(path.resolve())
    meta = {
        "id": "unit-inter-model",
        "title": "Handoff",
        "source_path": resolved,
        "start_offset": 0,
        "tool": "inter-model",
    }
    store.add_unit("unit-inter-model", "handoff", [0.1] * 8, meta)
    result = expand_record("unit-inter-model", cfg=cfg)
    assert result.status == "not_session"
    assert result.source_path == resolved
    assert "not a session transcript" in result.message.lower()


def test_exact_kiro_legacy_sqlite(expand_env) -> None:
    import sqlite3

    cfg, store, home = expand_env
    db_path = home / ".local" / "share" / "kiro-cli" / "data.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "conversation_id": "c1",
        "history": [
            {
                "user": {"content": {"Prompt": {"prompt": "kiro sqlite user"}}},
                "assistant": {
                    "Response": {"content": "kiro sqlite assistant"},
                },
            }
        ],
    }
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE conversations_v2 (value TEXT)")
    conn.execute("INSERT INTO conversations_v2 VALUES (?)", (json.dumps(payload),))
    conn.commit()
    conn.close()
    path = db_path.resolve()
    assert detect_format(path) == "sqlite_kiro"
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-kiro-sqlite",
        source_path=str(path),
        start=0,
        end=1,
        window=messages[0:2],
        tool="kiro",
    )
    result = expand_record("unit-kiro-sqlite", cfg=cfg)
    assert result.status == "exact"
    assert "kiro sqlite user" in result.text


def test_redaction_toggle(expand_env) -> None:
    cfg, store, home = expand_env
    secret = "sk-" + ("a" * 24)
    path = _cursor_source(
        home,
        [_cursor_line("user", f"token {secret}")],
    )
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-redact",
        source_path=str(path),
        start=0,
        end=0,
        window=messages[0:1],
        tool="cursor",
    )
    redacted = expand_record("unit-redact", cfg=cfg, redact=True)
    plain = expand_record("unit-redact", cfg=cfg, redact=False)
    assert secret not in redacted.text
    assert secret in plain.text


def test_max_chars_truncation(expand_env) -> None:
    cfg, store, home = expand_env
    path = _cursor_source(
        home,
        [_cursor_line("user", "x" * 500)],
    )
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-cap",
        source_path=str(path),
        start=0,
        end=0,
        window=messages[0:1],
        tool="cursor",
    )
    result = expand_record("unit-cap", cfg=cfg, max_chars=80)
    assert result.truncated
    assert len(result.text) < 500


def test_mcp_expand_is_read_only_json(expand_env) -> None:
    cfg, store, home = expand_env
    path = _cursor_source(
        home,
        [_cursor_line("user", "mcp path")],
    )
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-mcp",
        source_path=str(path),
        start=0,
        end=0,
        window=messages[0:1],
        tool="cursor",
    )
    import mcp_server

    payload = json.loads(
        mcp_server.expand("unit-mcp", max_chars=DEFAULT_MAX_CHARS, no_redact=False)
    )
    assert payload["status"] == "exact"
    assert "mcp path" in payload["text"]


def test_expand_never_calls_providers(expand_env, monkeypatch) -> None:  # noqa: ARG001
    import llm

    def boom(*_a, **_k):
        raise RuntimeError("provider must not be called")

    monkeypatch.setattr(llm.requests, "post", boom)
    monkeypatch.setattr(llm, "ollama_embed", boom)
    cfg, store, home = expand_env
    path = _cursor_source(
        home,
        [_cursor_line("user", "no llm")],
    )
    messages = get_parser(path)(str(path))
    _seed_unit(
        store,
        unit_id="unit-no-llm",
        source_path=str(path),
        start=0,
        end=0,
        window=messages[0:1],
        tool="cursor",
    )
    result = expand_record("unit-no-llm", cfg=cfg)
    assert result.status == "exact"


def test_format_expand_output_header() -> None:
    from chunk_expand import ExpandResult

    text = format_expand_output(
        ExpandResult(
            record_id="abc",
            status="exact",
            source_path="/tmp/x.jsonl",
            start_offset=0,
            end_offset=2,
            date="2026-01-01",
            text="body",
        )
    )
    assert "status: exact" in text
    assert "messages: 0–2" in text
    assert "body" in text
