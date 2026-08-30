"""Provenance continuity when re-indexing inter-model sections."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest

from adapters.inter_model_doc import parse
from chroma_store import ChromaStore
from inter_model_index import InterModelIndexError, index_inter_model_messages


def _cfg(tmp_path: Path) -> dict:
    return {
        "index": {
            "processed_log": str(tmp_path / "processed.json"),
            "units_export": str(tmp_path / "knowledge_units.jsonl"),
            "chroma_dir": str(tmp_path / "chroma"),
        },
        "ingest_dedup": {
            "semantic_similarity": 0.92,
            "candidate_k": 10,
            "max_semantic_candidates_per_unit": 3,
        },
    }


def _run_index(cfg: dict, path: Path, store: ChromaStore) -> int:
    messages = parse(str(path))

    @contextmanager
    def fake_session(*, entrypoint=None):
        class _PW:
            pass

        pw = _PW()
        pw.store = store
        pw.live_cfg = cfg
        yield pw

    with mock.patch(
        "inter_model_index.production_chroma_write_session", fake_session
    ), mock.patch("inter_model_index.ollama_embed", return_value=[0.1, 0.2, 0.3]):
        Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
        return index_inter_model_messages(
            str(path),
            messages,
            path_key=str(path.resolve()),
            chroma_dir=cfg["index"]["chroma_dir"],
            embed_model="nomic-embed-text",
            ollama_host="http://localhost:11434",
            cfg=cfg,
            verbose=False,
        )


def test_reindex_unchanged_section_replays_provenance_identity(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    path = tmp_path / "docs" / "inter-model" / "HANDOFF-test.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "## Packet\n\nStable inter-model body for provenance replay.\n",
        encoding="utf-8",
    )
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        assert _run_index(cfg, path, store) == 1
        first_messages = parse(str(path))
        unit_id = __import__("distill").make_unit_id(
            str(path.resolve()), int(first_messages[0]["section_index"]), "Packet", 0
        )
        first = store.get_unit(unit_id)
        assert first is not None
        first_assertion = first["metadata"]["assertion_id"]

        assert _run_index(cfg, path, store) == 1
        second = store.get_unit(unit_id)
        assert second is not None
        assert second["metadata"]["assertion_id"] == first_assertion
    finally:
        store.close()


def test_reindex_changed_section_fails_closed(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    path = tmp_path / "docs" / "inter-model" / "HANDOFF-change.md"
    path.parent.mkdir(parents=True)
    path.write_text("## Packet\n\nOriginal body.\n", encoding="utf-8")
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        assert _run_index(cfg, path, store) == 1
        path.write_text("## Packet\n\nReplacement body.\n", encoding="utf-8")
        with pytest.raises(InterModelIndexError, match="supersession"):
            _run_index(cfg, path, store)
    finally:
        store.close()
