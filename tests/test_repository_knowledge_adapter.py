"""Chunker, detector-order, and documentary indexer tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser
from adapters.repository_knowledge import (
    RepositoryKnowledgeParseError,
    chunk_javascript,
    chunk_json,
    chunk_markdown,
    chunk_python,
    chunk_text,
    chunk_toml,
    parse,
)
from chroma_store import ChromaStore
import repository_knowledge_scope as rks
from tests.test_repository_knowledge_scope import _commit_all, _init_repo, _write_manifest


class _FakeProductionWrite:
    def __init__(self, store: ChromaStore, cfg: dict) -> None:
        self.store = store
        self.live_cfg = cfg


class ChunkerTests(unittest.TestCase):
    def test_markdown_heading_and_python_ast(self) -> None:
        md = chunk_markdown("# Title\n\nIntro\n\n## Section\n\nBody\n")
        self.assertGreaterEqual(len(md), 2)
        py = chunk_python("'''mod'''\n\ndef foo():\n    return 1\n")
        labels = [chunk.label for chunk in py]
        self.assertTrue(any("preamble" in label or "foo" in label for label in labels))

    def test_json_js_toml_text(self) -> None:
        js = chunk_javascript("import x from 'y';\nexport function f() { return 1 }\n")
        self.assertGreaterEqual(len(js), 1)
        parsed = chunk_json('{"needle": {"x": 1}, "other": [2]}')
        locators = [chunk.locator for chunk in parsed]
        self.assertTrue(any(item.startswith("pointer:/") for item in locators))
        toml = chunk_toml("[fixture]\nneedle = 'x'\n")
        self.assertGreaterEqual(len(toml), 1)
        text = chunk_text("a\n" * 200)
        self.assertGreaterEqual(len(text), 2)

    def test_invalid_json_refuses(self) -> None:
        with self.assertRaises(RepositoryKnowledgeParseError):
            chunk_json("{not json")

    def test_json_preserves_exact_source_span(self) -> None:
        source = '{\n  "needle" : { "escaped": "a\\u0062", "order": [3, 2, 1] }\n}\n'
        chunks = chunk_json(source)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(
            chunks[0].original_source_text,
            '{ "escaped": "a\\u0062", "order": [3, 2, 1] }',
        )
        self.assertEqual(source.encode("utf-8")[chunks[0].byte_start : chunks[0].byte_end].decode(), chunks[0].original_source_text)

    def test_overlong_source_line_refuses_atomically(self) -> None:
        with self.assertRaisesRegex(RepositoryKnowledgeParseError, "resource_limit"):
            chunk_text("x" * 6001)


class DetectorOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        rks.reset_configuration()
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name) / "repo"
        self.root.mkdir()
        _init_repo(self.root)

    def tearDown(self) -> None:
        rks.reset_configuration()
        self._td.cleanup()

    def test_eligible_and_blocked_before_legacy(self) -> None:
        files = {
            "docs/plan.md": ("# Plan\n\nRK_ADAPTER_MD\n", "markdown"),
            "src/mod.py": ("def foo():\n    return 1\n", "python"),
        }
        extra = [
            "docs/inter-model/note.md",
            "agent-transcripts/sess.jsonl",
            "secret.env",
        ]
        man = _write_manifest(self.root, files, extra_unrelated=extra)
        (self.root / "docs/inter-model/note.md").write_text("# IM\n", encoding="utf-8")
        (self.root / "agent-transcripts/sess.jsonl").write_text(
            '{"role":"user","message":{"content":[{"type":"text","text":"hi"}]}}\n',
            encoding="utf-8",
        )
        (self.root / "secret.env").write_text("RK_EXCL\n", encoding="utf-8")
        _commit_all(self.root)
        rks.configure_manifests([str(man)])
        self.assertEqual(detect_format(self.root / "docs/plan.md"), "repository_knowledge_v1")
        self.assertIsNotNone(get_parser(self.root / "docs/plan.md"))
        self.assertEqual(detect_format(self.root / "docs/inter-model/note.md"), "repository_knowledge_blocked")
        self.assertIsNone(get_parser(self.root / "docs/inter-model/note.md"))
        self.assertEqual(
            detect_format(self.root / "agent-transcripts/sess.jsonl"),
            "repository_knowledge_blocked",
        )
        self.assertIsNone(get_parser(self.root / "agent-transcripts/sess.jsonl"))
        self.assertEqual(detect_format(self.root / "secret.env"), "repository_knowledge_blocked")
        self.assertNotIn("repository_knowledge_blocked", TOOL_BY_FORMAT)
        outside = Path(self._td.name) / "loose.md"
        outside.write_text("# loose\n", encoding="utf-8")
        self.assertIsNone(detect_format(outside))

    def test_parse_requires_eligible(self) -> None:
        man = _write_manifest(self.root, {"docs/plan.md": ("# Plan\nRK\n", "markdown")})
        _commit_all(self.root)
        rks.configure_manifests([str(man)])
        messages = parse(str(self.root / "docs/plan.md"))
        self.assertGreaterEqual(len(messages), 1)
        self.assertEqual(messages[0]["source_type"], "repository_knowledge_v1")
        with self.assertRaises(RepositoryKnowledgeParseError):
            parse(str(self.root / "missing.md"))


class IndexerTests(unittest.TestCase):
    def setUp(self) -> None:
        rks.reset_configuration()
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name) / "repo"
        self.root.mkdir()
        _init_repo(self.root)

    def tearDown(self) -> None:
        rks.reset_configuration()
        self._td.cleanup()

    def test_units_are_documentary_with_claimed_provenance(self) -> None:
        from repository_knowledge_index import index_repository_knowledge_messages

        man = _write_manifest(self.root, {"docs/plan.md": ("# Plan\nRK_INDEX_NONCE\n", "markdown")})
        _commit_all(self.root)
        rks.configure_manifests([str(man)])
        path = self.root / "docs/plan.md"
        messages = parse(str(path))
        cfg = {
            "index": {
                "processed_log": str(Path(self._td.name) / "processed.json"),
                "units_export": str(Path(self._td.name) / "units.jsonl"),
                "chroma_dir": str(Path(self._td.name) / "chroma"),
            },
            "ingest_dedup": {
                "semantic_similarity": 0.92,
                "candidate_k": 10,
                "max_semantic_candidates_per_unit": 3,
            },
        }
        Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
        store = ChromaStore(cfg["index"]["chroma_dir"])

        @contextmanager
        def fake_session(*, entrypoint=None):
            del entrypoint
            yield _FakeProductionWrite(store, cfg)

        keep: set[str] = set()
        with mock.patch(
            "repository_knowledge_index.production_chroma_write_session", fake_session
        ), mock.patch(
            "repository_knowledge_index.ollama_embed", return_value=[0.1, 0.2, 0.3]
        ):
            n = index_repository_knowledge_messages(
                str(path),
                messages,
                path_key=str(path.resolve()),
                chroma_dir=cfg["index"]["chroma_dir"],
                embed_model="nomic-embed-text",
                ollama_host="http://localhost:11434",
                cfg=cfg,
                verbose=False,
                unit_ids_out=keep,
            )
        self.assertGreaterEqual(n, 1)
        self.assertEqual(len(keep), n)
        unit = store.get_unit(next(iter(keep)))
        meta = unit.get("metadata") or unit
        self.assertEqual(meta.get("source_type") or unit.get("source_type"), "repository_knowledge_v1")
        self.assertEqual(meta.get("tool") or unit.get("tool"), "repository-knowledge")
        self.assertIn("provenance_commitment", json.dumps(unit))

    def test_unit_identity_is_namespaced_by_frozen_source_identity(self) -> None:
        from repository_knowledge_index import make_repository_unit_id

        common = {
            "relpath": "docs/plan.md",
            "locator": "lines:1-2",
            "chunk_sha256": "a" * 64,
            "adapter_version": "repository_knowledge_v1",
        }
        first = make_repository_unit_id(source_identity="/repo/a|frozen", **common)
        second = make_repository_unit_id(source_identity="/repo/b|frozen", **common)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
