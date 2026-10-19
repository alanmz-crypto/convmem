"""Watcher session.json forwarding for selected Kiro only (C-KI5 partial)."""

from __future__ import annotations

import json
from pathlib import Path

from watch_kiro_paths import expand_selected_kiro_session_meta_paths
from watch_circuit_breaker import CircuitBreakerState


def test_session_json_maps_to_messages_for_selected_kiro(tmp_path: Path) -> None:
    session_dir = tmp_path / "hash" / "sess_watch"
    session_dir.mkdir(parents=True)
    messages = session_dir / "messages.jsonl"
    messages.write_bytes(b"\n")
    session_json = session_dir / "session.json"
    session_json.write_text(
        json.dumps({"id": "sess_watch", "workspacePaths": [str(tmp_path)]}),
        encoding="utf-8",
    )
    cfg = {
        "index": {
            "chroma_dir": str(tmp_path / "chroma"),
            "processed_log": str(tmp_path / "processed.json"),
            "units_export": str(tmp_path / "units.jsonl"),
            "incremental_jsonl": {
                "enabled": True,
                "state_dir": str(tmp_path / "state"),
                "live_sources": [str(messages.resolve())],
                "embed_dimension": 8,
                "kiro_session": {
                    "max_source_bytes": 268435456,
                    "max_transform_chunks_per_run": 20,
                    "allow_full_rebuild": False,
                },
            },
        }
    }
    expanded = expand_selected_kiro_session_meta_paths(cfg, [str(session_json)])
    assert str(messages.resolve()) in expanded

def test_kiro_prefix_change_does_not_clear_terminal_refusal_quarantine(tmp_path: Path) -> None:
    """C-KI5: prefix digest change must not forgive a terminal refusal hold."""
    messages = tmp_path / "sess_q" / "messages.jsonl"
    messages.parent.mkdir(parents=True)
    messages.write_bytes(b"\n")
    path_key = str(messages.resolve())
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    breaker.record_refusal(path_key, outcome="rolled_back", prefix_digest="a" * 64)
    assert breaker.should_skip_refusal_quarantine(path_key, "b" * 64)
