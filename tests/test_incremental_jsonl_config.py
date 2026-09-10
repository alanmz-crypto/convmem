"""T1 default-off config and exact Kiro eligibility."""

from __future__ import annotations

from pathlib import Path

import pytest

import config
from adapters.detect import detect_format
from config import incremental_jsonl_settings, load_config
from incremental_jsonl import decide_eligibility
from incremental_jsonl_isolation import IsolationViolation
from tests.incremental_jsonl_helpers import isolated_env, write_source


def test_example_config_is_default_off() -> None:
    example = Path("config.example.toml").read_text(encoding="utf-8")
    assert "[index.incremental_jsonl]" in example
    assert "enabled = false" in example
    assert "allow_full_rebuild = false" in example


def test_missing_table_equals_disabled(tmp_path: Path) -> None:
    cfg_path = tmp_path / "bare.toml"
    cfg_path.write_text(
        "[index]\nchroma_dir = '/tmp/x'\nprocessed_log = '/tmp/p.json'\n",
        encoding="utf-8",
    )
    loaded = load_config(cfg_path)
    settings = incremental_jsonl_settings(loaded)
    assert settings.enabled is False
    assert settings.allow_full_rebuild is False
    assert settings.table_present is False
    assert decide_eligibility(
        enabled=settings.enabled,
        detected_format="jsonl_kiro_session",
        path_key="/tmp/s",
        processed={},
        chroma_row_count=0,
        checkpoint=None,
    ) == "disabled"


def test_malformed_boolean_fails_closed(tmp_path: Path) -> None:
    cfg_path = tmp_path / "bad.toml"
    cfg_path.write_text(
        "[index]\nchroma_dir = '/tmp/x'\nprocessed_log = '/tmp/p.json'\n"
        "[index.incremental_jsonl]\nenabled = \"yes\"\n",
        encoding="utf-8",
    )
    loaded = load_config(cfg_path)
    with pytest.raises(config.IncrementalJsonlConfigError, match="invalid_enabled"):
        incremental_jsonl_settings(loaded)


def test_true_flag_cannot_select_non_kiro(tmp_path: Path) -> None:
    cursor = tmp_path / "agent-transcripts" / "id" / "id.jsonl"
    cursor.parent.mkdir(parents=True)
    cursor.write_text("{}\n", encoding="utf-8")
    fmt = detect_format(cursor)
    assert fmt != "jsonl_kiro_session"
    assert (
        decide_eligibility(
            enabled=True,
            detected_format=fmt,
            path_key=str(cursor),
            processed={},
            chroma_row_count=0,
            checkpoint=None,
        )
        == "ineligible_format"
    )


def test_bootstrap_required_for_processed_without_checkpoint(tmp_path: Path) -> None:
    source = tmp_path / "hash" / "sess_x" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text("{}\n", encoding="utf-8")
    path_key = str(source)
    assert (
        decide_eligibility(
            enabled=True,
            detected_format="jsonl_kiro_session",
            path_key=path_key,
            processed={"abc": {"path": path_key, "chunks": 1, "units": 1}},
            chroma_row_count=0,
            checkpoint=None,
        )
        == "bootstrap_required"
    )
    assert (
        decide_eligibility(
            enabled=True,
            detected_format="jsonl_kiro_session",
            path_key=path_key,
            processed={},
            chroma_row_count=4,
            checkpoint=None,
        )
        == "bootstrap_required"
    )


def test_new_empty_authority_is_eligible(tmp_path: Path) -> None:
    source = tmp_path / "hash" / "sess_x" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text("{}\n", encoding="utf-8")
    assert (
        decide_eligibility(
            enabled=True,
            detected_format="jsonl_kiro_session",
            path_key=str(source),
            processed={},
            chroma_row_count=0,
            checkpoint=None,
        )
        == "eligible_new_source"
    )


def test_false_flag_does_not_construct_coordinator(monkeypatch) -> None:
    from incremental_jsonl import IncrementalJsonlCoordinator, maybe_route_incremental

    constructed = {"count": 0}
    original = IncrementalJsonlCoordinator.__init__

    def wrapped(self, *args, **kwargs):
        constructed["count"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(IncrementalJsonlCoordinator, "__init__", wrapped)
    result = maybe_route_incremental(
        cfg={"index": {"incremental_jsonl": {"enabled": False}}},
        idx={},
        path="/tmp/x",
        path_key="/tmp/x",
        file_hash="0",
        processed={},
        models={},
        tool="kiro",
        units_export=None,
        chunk_size=2,
        overlap=0,
        min_confidence=0.6,
        force_reindex=False,
        supersede_on_reindex=False,
        verbose=False,
        detected_format="jsonl_kiro_session",
    )
    assert result is None
    assert constructed["count"] == 0


def test_symlink_state_root_rejected(tmp_path: Path) -> None:
    boundary, _env = isolated_env(tmp_path)
    source = write_source(boundary.root, 2)
    outside = tmp_path / "outside-state"
    outside.mkdir()
    alias = boundary.root / "state-alias"
    alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises(IsolationViolation, match="symlink"):
        boundary.resolve_mutable(alias / "x", label="incremental state")
    assert detect_format(source) == "jsonl_kiro_session"


def test_force_unsupported() -> None:
    assert (
        decide_eligibility(
            enabled=True,
            detected_format="jsonl_kiro_session",
            path_key="/tmp/s",
            processed={},
            chroma_row_count=0,
            checkpoint=None,
            force_reindex=True,
        )
        == "incremental_force_unsupported"
    )
