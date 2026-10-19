"""Issue #286 Kiro semantic sidecar contract (C-KI2)."""

from __future__ import annotations

import json
from pathlib import Path

import incremental_jsonl
from tests.test_incremental_jsonl_exact_path_recovery_parity import (
    _kiro_production_setup,
    _projection_state,
)
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


def test_effective_sidecar_change_refuses_unchanged_checkpoint(tmp_path, monkeypatch):
    source, cfg, _cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    cfg["index"]["incremental_jsonl"]["kiro_session"] = {}
    first = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    assert first.kiro_admitted_live
    assert first.run().outcome == "committed"
    checkpoint_bytes = first.paths["checkpoint"].read_bytes()
    projection = _projection_state(first, cfg)
    prefix_bytes = source.read_bytes()

    unchanged = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    assert unchanged.run().outcome == "unchanged"
    sidecar = source.parent / "session.json"
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata["workspacePaths"] = [str(source.parent / "different-workspace")]
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")

    changed = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    result = changed.run()
    assert source.read_bytes() == prefix_bytes
    assert result.outcome == "rebuild_required:source_identity_changed"
    assert result.counters.total == 0
    assert result.reused_artifacts == 0
    assert changed.paths["checkpoint"].read_bytes() == checkpoint_bytes
    assert _projection_state(changed, cfg) == projection

# ref: ../incremental_jsonl.py — refuse stale checkpoint provenance after effective sidecar changes
# src: ./test_incremental_jsonl_exact_path_recovery_parity.py — hermetic admitted-source fixture and projection checks
