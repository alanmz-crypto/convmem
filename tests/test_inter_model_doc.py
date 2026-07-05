"""Tests for inter-model coordination doc adapter and indexing."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adapters.detect import detect_format, get_parser
from adapters.inter_model_doc import is_inter_model_doc, parse
from inter_model_index import index_inter_model_messages


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
    @mock.patch("inter_model_index.ChromaStore")
    def test_index_inter_model_messages(self, mock_store_cls, _embed):
        store = mock_store_cls.return_value.__enter__.return_value
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "docs" / "inter-model" / "CROSS-PROJECT-DIGEST-PILOT.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "## Run 8\n\nDigest pilot run eight notes.\n",
                encoding="utf-8",
            )
            messages = parse(str(path))
            n = index_inter_model_messages(
                str(path),
                messages,
                path_key=str(path.resolve()),
                chroma_dir=str(Path(td) / "chroma"),
                embed_model="nomic-embed-text",
                ollama_host="http://localhost:11434",
                verbose=False,
            )
            self.assertEqual(n, 1)
            store.add_unit.assert_called_once()
            _args, kwargs = store.add_unit.call_args
            meta = kwargs.get("metadata") if kwargs else _args[3]
            if isinstance(meta, dict):
                self.assertEqual(meta.get("tool"), "inter-model")
                self.assertEqual(meta.get("source_type"), "inter_model_doc")


if __name__ == "__main__":
    unittest.main()
