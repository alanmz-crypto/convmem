"""S0 contract inventory — parity oracles pinned before Codex adapter work."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.detect import detect_format, get_parser
from adapters.kiro_session_jsonl import parse, parse_complete_prefix
from incremental_jsonl import (
    ADAPTER_CONTRACT_VERSION,
    CHECKPOINT_VERSION,
    ELIGIBLE_FORMAT,
    decide_eligibility,
    compute_transform_fingerprint,
)
from tests.incremental_jsonl_helpers import kiro_record, write_source


def test_kiro_is_only_default_eligible_format() -> None:
    assert ELIGIBLE_FORMAT == "jsonl_kiro_session"
    assert ADAPTER_CONTRACT_VERSION == "kiro-complete-prefix-v1"
    assert CHECKPOINT_VERSION == 1


def test_decide_eligibility_oracle_table() -> None:
    assert decide_eligibility(enabled=False, detected_format=ELIGIBLE_FORMAT, path_key="/x", processed={}, chroma_row_count=0, checkpoint=None) == "disabled"
    assert (
        decide_eligibility(
            enabled=True,
            detected_format="jsonl_codex_history",
            path_key="/x",
            processed={},
            chroma_row_count=0,
            checkpoint=None,
        )
        == "ineligible_format"
    )
    assert (
        decide_eligibility(
            enabled=True,
            detected_format=ELIGIBLE_FORMAT,
            path_key="/x",
            processed={"a": {"path": "/x"}},
            chroma_row_count=0,
            checkpoint=None,
        )
        == "bootstrap_required"
    )
    assert (
        decide_eligibility(
            enabled=True,
            detected_format=ELIGIBLE_FORMAT,
            path_key="/x",
            processed={},
            chroma_row_count=0,
            checkpoint=None,
        )
        == "eligible_new_source"
    )


def test_transform_fingerprint_keys_are_stable() -> None:
    fp = compute_transform_fingerprint(
        chunk_size=2,
        overlap=0,
        min_confidence=0.6,
        models={"summarize_model": "s", "distill_model": "d", "embed_model": "e"},
        embed_dimension=8,
        implementation_revision="test",
    )
    assert isinstance(fp, str) and len(fp) == 64


def test_kiro_prefix_matches_legacy_parse(tmp_path: Path) -> None:
    boundary_root = tmp_path / "root"
    source = write_source(boundary_root, 5)
    legacy = parse(str(source))
    view = parse_complete_prefix(str(source))
    assert view.messages == legacy
    assert len(view.byte_ranges) == len(legacy)
    assert view.complete_boundary == source.stat().st_size


def test_codex_formats_detect_and_parse_without_prefix_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    history = tmp_path / ".codex" / "history.jsonl"
    history.parent.mkdir(parents=True)
    history.write_text(
        json.dumps({"text": "hello", "session_id": "s1", "ts": 1_700_000_000}) + "\n",
        encoding="utf-8",
    )
    assert detect_format(history) == "jsonl_codex_history"
    parser = get_parser(history)
    assert parser is not None
    messages = parser(str(history))
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["source_type"] == "prompt_only"

    rollout = tmp_path / ".codex" / "sessions" / "2026" / "rollout-test.jsonl"
    rollout.parent.mkdir(parents=True)
    rollout.write_text(
        json.dumps(
            {
                "type": "response_item",
                "timestamp": "2026-01-01T00:00:00Z",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "rollout hello"}],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert detect_format(rollout) == "jsonl_codex_rollout"
    rollout_messages = get_parser(rollout)(str(rollout))
    assert len(rollout_messages) == 1
    assert rollout_messages[0]["source_type"] == "codex_rollout"
