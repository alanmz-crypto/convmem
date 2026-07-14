"""Regression: index() limit_files and files_skipped category semantics."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _write_inventory(path: Path, entries: list[str]) -> None:
    path.write_text(
        "".join(json.dumps({"path": p}) + "\n" for p in entries),
        encoding="utf-8",
    )


def _cursor_line(text: str = "hello") -> str:
    return json.dumps(
        {
            "role": "user",
            "message": {"content": [{"type": "text", "text": text}]},
        }
    )


class IndexLimitSkipStatsTests(unittest.TestCase):
    def _cfg(self, root: Path, inventory: Path) -> dict:
        return {
            "index": {
                "processed_log": str(root / "processed.json"),
                "units_export": str(root / "knowledge_units.jsonl"),
                "chroma_dir": str(root / "chroma"),
                "chunk_size": 60,
                "chunk_overlap": 10,
            },
            "models": {
                "summarize_model": "dummy",
                "distill_model": "dummy",
                "embed_model": "dummy",
                "ollama_host": "http://localhost:11434",
            },
            "distill": {"min_confidence": 0.1},
            "sources": {"inventory": str(inventory)},
        }

    def _run_index(self, cfg: dict, **kwargs):
        with mock.patch("ingest.load_config", return_value=cfg), mock.patch(
            "ingest.summarize", return_value="summary"
        ), mock.patch(
            "ingest.distill",
            return_value=[
                {
                    "type": "explanation",
                    "title": "T",
                    "summary": "S",
                    "keywords": ["k"],
                    "confidence": 0.9,
                    "domain": "coding.tooling",
                }
            ],
        ), mock.patch(
            "ingest.ollama_embed", return_value=[0.1, 0.2]
        ), mock.patch("brief.refresh_brief_after_change", lambda *_a, **_k: None):
            from ingest import index

            return index(verbose=False, **kwargs)

    def test_unsupported_before_supported_does_not_consume_limit(self):
        """inventory=[unsupported, supported], limit_files=1 => supported processed."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            unsupported = root / "notes.md"  # detect_format -> None
            unsupported.write_text("# hi\n", encoding="utf-8")
            supported = root / "agent-transcripts" / "s" / "chat.jsonl"
            supported.parent.mkdir(parents=True)
            supported.write_text(_cursor_line() + "\n", encoding="utf-8")
            inv = root / "inventory.jsonl"
            _write_inventory(inv, [str(unsupported), str(supported)])
            cfg = self._cfg(root, inv)

            stats = self._run_index(cfg, limit_files=1)
            self.assertEqual(stats["files_processed"], 1)
            self.assertEqual(stats["files_skipped"], 0)

    def test_unsupported_does_not_increment_files_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            unsupported = root / "notes.md"
            unsupported.write_text("# hi\n", encoding="utf-8")
            inv = root / "inventory.jsonl"
            _write_inventory(inv, [str(unsupported)])
            cfg = self._cfg(root, inv)

            stats = self._run_index(cfg)
            self.assertEqual(stats["files_processed"], 0)
            self.assertEqual(stats["files_skipped"], 0)

    def test_unreadable_does_not_increment_files_skipped(self):
        """Prior behavior: OSError on hash => continue with no files_skipped."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            missing = root / "agent-transcripts" / "s" / "gone.jsonl"
            missing.parent.mkdir(parents=True)
            # Inventory points at a supported path spelling, but file is absent.
            inv = root / "inventory.jsonl"
            _write_inventory(inv, [str(missing)])
            cfg = self._cfg(root, inv)

            stats = self._run_index(cfg)
            self.assertEqual(stats["files_processed"], 0)
            self.assertEqual(stats["files_skipped"], 0)

    def test_parse_failure_does_not_increment_files_skipped(self):
        """Prior behavior: parse exception => continue with no files_skipped."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "chroma").mkdir()
            (root / "processed.json").write_text("{}", encoding="utf-8")
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            supported = root / "agent-transcripts" / "s" / "chat.jsonl"
            supported.parent.mkdir(parents=True)
            supported.write_text(_cursor_line() + "\n", encoding="utf-8")
            inv = root / "inventory.jsonl"
            _write_inventory(inv, [str(supported)])
            cfg = self._cfg(root, inv)

            def boom(_path):
                raise RuntimeError("parse boom")

            with mock.patch("ingest.get_parser", return_value=boom):
                stats = self._run_index(cfg)
            self.assertEqual(stats["files_processed"], 0)
            self.assertEqual(stats["files_skipped"], 0)

    def test_excluded_increments_files_skipped(self):
        """Control: exclusion still counts as skipped."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "chroma").mkdir()
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            supported = root / "agent-transcripts" / "s" / "chat.jsonl"
            supported.parent.mkdir(parents=True)
            supported.write_text(_cursor_line() + "\n", encoding="utf-8")
            from ingest import exclude_processed_path, sha256_file

            path_key = str(supported.resolve())
            file_hash = sha256_file(path_key)
            processed = root / "processed.json"
            processed.write_text("{}", encoding="utf-8")
            exclude_processed_path(str(processed), path_key, file_hash, reason="test")
            inv = root / "inventory.jsonl"
            _write_inventory(inv, [str(supported)])
            cfg = self._cfg(root, inv)

            stats = self._run_index(cfg)
            self.assertEqual(stats["files_processed"], 0)
            self.assertEqual(stats["files_skipped"], 1)


if __name__ == "__main__":
    unittest.main()
