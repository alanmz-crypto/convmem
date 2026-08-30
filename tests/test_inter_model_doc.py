"""Tests for inter-model coordination doc adapter and indexing."""

from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest

from adapters.detect import detect_format, get_parser
from adapters.inter_model_doc import is_inter_model_doc, parse
from chroma_store import ChromaStore
from distill import make_unit_id
from inter_model_index import InterModelIndexError, index_inter_model_messages


class _FakeProductionWrite:
    def __init__(self, store: ChromaStore, cfg: dict) -> None:
        self.store = store
        self.live_cfg = cfg


def _inter_model_index_cfg(tmp_path: Path) -> dict:
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


def _run_inter_model_index(cfg: dict, path: Path, store: ChromaStore) -> int:
    messages = parse(str(path))

    @contextmanager
    def fake_session(*, entrypoint=None):
        del entrypoint
        yield _FakeProductionWrite(store, cfg)

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


class InterModelDocAdapterTests(unittest.TestCase):
    def test_is_inter_model_doc(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            good = root / "docs" / "inter-model" / "PLAN-test.md"
            good.parent.mkdir(parents=True)
            good.write_text("# Plan\n", encoding="utf-8")
            self.assertTrue(is_inter_model_doc(good))
            self.assertEqual(detect_format(good), "inter_model_doc")
            self.assertIsNotNone(get_parser(good))

            archived = root / "docs" / "archive" / "inter-model" / "old.md"
            archived.parent.mkdir(parents=True)
            archived.write_text("# Old\n", encoding="utf-8")
            self.assertFalse(is_inter_model_doc(archived))

            random_md = root / "notes.md"
            random_md.write_text("# Notes\n", encoding="utf-8")
            self.assertFalse(is_inter_model_doc(random_md))


    def test_nested_and_excluded_inter_model_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nested = root / "docs" / "inter-model" / "debate-test" / "README.md"
            nested.parent.mkdir(parents=True)
            nested.write_text("# Debate\n", encoding="utf-8")
            self.assertTrue(is_inter_model_doc(nested))
            self.assertEqual(detect_format(nested), "inter_model_doc")
            self.assertIsNotNone(get_parser(nested))

            deep = root / "docs" / "inter-model" / "a" / "b" / "c" / "notes.md"
            deep.parent.mkdir(parents=True)
            deep.write_text("# Deep\n", encoding="utf-8")
            self.assertTrue(is_inter_model_doc(deep))

            kiro_snap = (
                root / ".kiro" / "sessions" / "s" / "snapshots" / "h"
                / "docs" / "inter-model" / "debate" / "f.md"
            )
            kiro_snap.parent.mkdir(parents=True)
            kiro_snap.write_text("# KIRO\n", encoding="utf-8")
            self.assertFalse(is_inter_model_doc(kiro_snap))

            wrong_parent = root / "other" / "inter-model" / "file.md"
            wrong_parent.parent.mkdir(parents=True)
            wrong_parent.write_text("# Other\n", encoding="utf-8")
            self.assertFalse(is_inter_model_doc(wrong_parent))

            non_md = root / "docs" / "inter-model" / "debate-test" / "notes.txt"
            non_md.write_text("txt\n", encoding="utf-8")
            self.assertFalse(is_inter_model_doc(non_md))

    def test_parse_sections(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "docs" / "inter-model" / "HANDOFF-test.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "# Handoff title\n\nIntro.\n\n## First section\n\nAlpha body.\n\n"
                "## Second section\n\nBeta body.\n",
                encoding="utf-8",
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["section_title"], "First section")
            self.assertIn("Alpha body", messages[0]["content"])
            self.assertEqual(messages[0]["section_index"], 0)
            self.assertEqual(messages[1]["section_title"], "Second section")


class InterModelIndexTests(unittest.TestCase):
    @mock.patch("inter_model_index.ollama_embed", return_value=[0.1, 0.2])
    @mock.patch("inter_model_index.production_chroma_write_session")
    def test_index_inter_model_messages(self, mock_session, _embed):
        store = mock.MagicMock()
        session = mock.MagicMock()
        session.store = store
        mock_session.return_value.__enter__.return_value = session
        mock_session.return_value.__exit__.return_value = False
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "docs" / "inter-model" / "CROSS-PROJECT-DIGEST-PILOT.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "## Run 8\n\nDigest pilot run eight notes.\n",
                encoding="utf-8",
            )
            messages = parse(str(path))
            cfg = {
                "index": {
                    "processed_log": str(Path(td) / "processed.json"),
                    "units_export": str(Path(td) / "knowledge_units.jsonl"),
                    "chroma_dir": str(Path(td) / "chroma"),
                }
            }
            session.live_cfg = cfg
            Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
            n = index_inter_model_messages(
                str(path),
                messages,
                path_key=str(path.resolve()),
                chroma_dir=cfg["index"]["chroma_dir"],
                embed_model="nomic-embed-text",
                ollama_host="http://localhost:11434",
                cfg=cfg,
                verbose=False,
            )
            self.assertEqual(n, 1)
            store.add_unit.assert_called_once()
            _args, kwargs = store.add_unit.call_args
            meta = kwargs.get("metadata") if kwargs else _args[3]
            if isinstance(meta, dict):
                self.assertEqual(meta.get("tool"), "inter-model")
                self.assertEqual(meta.get("source_type"), "inter_model_doc")


def test_reindex_unchanged_section_replays_provenance_identity(tmp_path: Path) -> None:
    cfg = _inter_model_index_cfg(tmp_path)
    path = tmp_path / "docs" / "inter-model" / "HANDOFF-test.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "## Packet\n\nStable inter-model body for provenance replay.\n",
        encoding="utf-8",
    )
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        assert _run_inter_model_index(cfg, path, store) == 1
        first_messages = parse(str(path))
        unit_id = make_unit_id(
            str(path.resolve()), int(first_messages[0]["section_index"]), "Packet", 0
        )
        first = store.get_unit(unit_id)
        assert first is not None
        first_assertion = first["metadata"]["assertion_id"]

        assert _run_inter_model_index(cfg, path, store) == 1
        second = store.get_unit(unit_id)
        assert second is not None
        assert second["metadata"]["assertion_id"] == first_assertion
    finally:
        store.close()


def test_reindex_changed_section_fails_closed(tmp_path: Path) -> None:
    cfg = _inter_model_index_cfg(tmp_path)
    path = tmp_path / "docs" / "inter-model" / "HANDOFF-change.md"
    path.parent.mkdir(parents=True)
    path.write_text("## Packet\n\nOriginal body.\n", encoding="utf-8")
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        assert _run_inter_model_index(cfg, path, store) == 1
        path.write_text("## Packet\n\nReplacement body.\n", encoding="utf-8")
        with pytest.raises(InterModelIndexError, match="supersession"):
            _run_inter_model_index(cfg, path, store)
    finally:
        store.close()


if __name__ == "__main__":
    unittest.main()
