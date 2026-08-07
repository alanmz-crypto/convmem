"""Tests for Kiro steering-file adapter (P1.0a)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.detect import detect_format, get_parser
from adapters.kiro_steering import is_kiro_steering_doc, parse


class KiroSteeringAdapterTests(unittest.TestCase):
    def test_is_kiro_steering_doc_positive(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / ".kiro" / "steering" / "ksweep-deploy.md"
            path.parent.mkdir(parents=True)
            path.write_text("# ksweep deploy\n\nCheck one.\n", encoding="utf-8")
            self.assertTrue(is_kiro_steering_doc(path))
            self.assertEqual(detect_format(path), "kiro_steering")
            self.assertIsNotNone(get_parser(path))

    def test_negatives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            random_md = root / "notes.md"
            random_md.write_text("# Notes\n", encoding="utf-8")
            self.assertFalse(is_kiro_steering_doc(random_md))
            self.assertIsNone(detect_format(random_md))

            inter = root / "docs" / "inter-model" / "PLAN.md"
            inter.parent.mkdir(parents=True)
            inter.write_text("# Plan\n", encoding="utf-8")
            self.assertFalse(is_kiro_steering_doc(inter))
            self.assertEqual(detect_format(inter), "inter_model_doc")

            session = root / ".kiro" / "sessions" / "s" / "notes.md"
            session.parent.mkdir(parents=True)
            session.write_text("# Session\n", encoding="utf-8")
            self.assertFalse(is_kiro_steering_doc(session))
            self.assertIsNone(detect_format(session))

            non_md = root / ".kiro" / "steering" / "notes.txt"
            non_md.parent.mkdir(parents=True)
            non_md.write_text("txt\n", encoding="utf-8")
            self.assertFalse(is_kiro_steering_doc(non_md))

    def test_parse_includes_path_and_name(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "repo" / ".kiro" / "steering" / "ksweep-deploy.md"
            path.parent.mkdir(parents=True)
            path.write_text(
                "---\ninclusion: manual\n---\n\n"
                "# ksweep — willowyhollow-dev\n\nExecute checks.\n",
                encoding="utf-8",
            )
            messages = parse(str(path))
            self.assertEqual(len(messages), 1)
            msg = messages[0]
            self.assertEqual(msg["source_type"], "kiro_steering")
            self.assertEqual(msg["section_index"], 0)
            self.assertIn("ksweep — willowyhollow-dev", msg["section_title"])
            content = msg["content"]
            self.assertIn("ksweep-deploy.md", content)
            self.assertIn("exists on disk at", content)
            self.assertIn(str(path.resolve()), content)


if __name__ == "__main__":
    unittest.main()
