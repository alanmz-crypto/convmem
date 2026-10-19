"""Issue #286 Kiro semantic sidecar contract (C-KI2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import incremental_jsonl
from tests.test_incremental_jsonl_exact_path_recovery_parity import (
    _kiro_production_setup,
    _projection_state,
)
from adapters.kiro_session_jsonl import (
    parse_complete_prefix,
    semantic_session_meta_digest,
    session_meta_digest_for_dir,
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


@pytest.mark.parametrize("field", ["workspacePaths", "id"])
def test_effective_sidecar_change_refuses_unchanged_checkpoint(tmp_path, monkeypatch, field):
    source, cfg, _cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    cfg["index"]["incremental_jsonl"]["kiro_session"] = {}
    first = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    assert first.kiro_admitted_live
    assert first.run().outcome == "committed"
    assert first.checkpoint()["session_meta_digest"] == session_meta_digest_for_dir(source.parent)
    checkpoint_bytes = first.paths["checkpoint"].read_bytes()
    projection = _projection_state(first, cfg)
    prefix_bytes = source.read_bytes()

    unchanged = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    assert unchanged.run().outcome == "unchanged"
    sidecar = source.parent / "session.json"
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata[field] = (
        [str(source.parent / "different-workspace")]
        if field == "workspacePaths" else "sess_different"
    )
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")

    changed = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    # Refuse before capture, including when the new id fails live-dir validation.
    monkeypatch.setattr(changed, "_capture", lambda *_: pytest.fail("capture reached"))
    result = changed.run()
    assert source.read_bytes() == prefix_bytes
    assert result.outcome == "rebuild_required:source_identity_changed"
    assert result.counters.total == 0
    assert result.reused_artifacts == 0
    assert changed.paths["checkpoint"].read_bytes() == checkpoint_bytes
    assert _projection_state(changed, cfg) == projection


@pytest.mark.parametrize("change", ["title", "lastModifiedAt", "extra_workspace"])
@pytest.mark.parametrize("admitted", [True, False])
def test_non_effective_sidecar_change_keeps_checkpoint_unchanged(
    tmp_path, monkeypatch, change, admitted
):
    source, cfg, _cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    if admitted:
        cfg["index"]["incremental_jsonl"]["kiro_session"] = {}
    first = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    assert first.kiro_admitted_live is admitted
    assert first.run().outcome == "committed"
    checkpoint_bytes = first.paths["checkpoint"].read_bytes()
    projection = _projection_state(first, cfg)
    prefix_bytes = source.read_bytes()
    sidecar = source.parent / "session.json"
    original = sidecar.read_bytes()
    metadata = json.loads(original)
    if change == "extra_workspace":
        metadata["workspacePaths"].append(str(source.parent / "secondary-workspace"))
    else:
        metadata[change] = "updated value"
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    assert sidecar.read_bytes() != original

    changed = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    monkeypatch.setattr(changed, "_capture", lambda *_: pytest.fail("capture reached"))
    result = changed.run()
    assert result.outcome == "unchanged"
    assert result.counters.total == 0
    assert result.reused_artifacts == 0
    assert source.read_bytes() == prefix_bytes
    assert changed.paths["checkpoint"].read_bytes() == checkpoint_bytes
    assert _projection_state(changed, cfg) == projection


@pytest.mark.parametrize("bypass_shortcut", [True, False])
@pytest.mark.parametrize("admitted", [True, False])
def test_effective_sidecar_guard_after_capture_is_admitted_only(
    tmp_path, monkeypatch, admitted, bypass_shortcut
):
    source, cfg, _cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    if admitted:
        cfg["index"]["incremental_jsonl"]["kiro_session"] = {}
    first = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    assert first.run().outcome == "committed"
    checkpoint_bytes = first.paths["checkpoint"].read_bytes()
    projection = _projection_state(first, cfg)
    sidecar = source.parent / "session.json"
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata["workspacePaths"] = [str(source.parent / "different-workspace")]
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")

    changed = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    # Exercise the shared guard even if the pre-capture shortcut is bypassed.
    if bypass_shortcut:
        monkeypatch.setattr(changed, "_unchanged_short_circuit_if_applicable", lambda: None)
    result = changed.run()
    expected = "rebuild_required:source_identity_changed" if admitted else "unchanged"
    assert result.outcome == expected
    assert result.counters.total == 0
    assert result.reused_artifacts == 0
    assert changed.paths["checkpoint"].read_bytes() == checkpoint_bytes
    assert _projection_state(changed, cfg) == projection

# ref: ../incremental_jsonl.py — refuse stale checkpoint provenance after effective sidecar changes
# src: ./test_incremental_jsonl_exact_path_recovery_parity.py — hermetic admitted-source fixture and projection checks
