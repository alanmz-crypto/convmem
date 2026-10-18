"""Issue #286 Kiro semantic sidecar contract (C-KI2)."""

from __future__ import annotations

import json
from pathlib import Path

from adapters.kiro_session_jsonl import (
    parse_complete_prefix,
    semantic_session_meta_digest,
)


def _write_session(tmp_path: Path, *, title: str) -> Path:
    session_dir = tmp_path / "sess_test"
    session_dir.mkdir(parents=True)
    messages = session_dir / "messages.jsonl"
    messages.write_bytes(
        (
            json.dumps(
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "payload": {"type": "user", "content": "hello"},
                }
            )
            + "\n"
        ).encode("utf-8")
    )
    (session_dir / "session.json").write_text(
        json.dumps(
            {
                "id": "sess_test",
                "workspacePaths": [str(tmp_path / "workspace")],
                "title": title,
                "lastModifiedAt": "2026-01-02T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    return messages


def test_title_only_sidecar_change_keeps_semantic_digest(tmp_path: Path) -> None:
    messages = _write_session(tmp_path, title="alpha")
    first = parse_complete_prefix(str(messages))
    (messages.parent / "session.json").write_text(
        json.dumps(
            {
                "id": "sess_test",
                "workspacePaths": [str(tmp_path / "workspace")],
                "title": "beta",
                "lastModifiedAt": "2026-01-03T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    second = parse_complete_prefix(str(messages))
    assert first.session_meta_digest == second.session_meta_digest
    assert first.session_meta_raw_digest != second.session_meta_raw_digest


def test_workspace_change_changes_semantic_digest(tmp_path: Path) -> None:
    messages = _write_session(tmp_path, title="same")
    first = parse_complete_prefix(str(messages))
    (messages.parent / "session.json").write_text(
        json.dumps(
            {
                "id": "sess_test",
                "workspacePaths": [str(tmp_path / "other-workspace")],
                "title": "same",
            }
        ),
        encoding="utf-8",
    )
    second = parse_complete_prefix(str(messages))
    assert first.session_meta_digest != second.session_meta_digest
    expected = semantic_session_meta_digest("sess_test", str(tmp_path / "other-workspace"))
    assert second.session_meta_digest == expected
