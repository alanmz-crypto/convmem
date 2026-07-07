"""Offline unit tests for summarization-eval grading + provenance triage.

No live model / Chroma — exercises the deterministic helpers the live
scripts/eval-summaries.py relies on.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_grading import count_sentences, grade_summary, keyword_recall  # noqa: E402
from eval_provenance import (  # noqa: E402
    EXIT_NEEDS_REBASELINE,
    EXIT_OK,
    EXIT_REGRESSION,
    classify,
)

GOOD_SUMMARY = (
    "Ollama runs locally and serves embeddings via nomic-embed-text. "
    "It also summarizes conversations with llama3.1:8b at http://localhost:11434. "
    "The distill path uses deepseek-v4-flash when a key is set.\n"
    "Keywords: ollama, nomic-embed-text, llama3.1:8b, deepseek, embeddings, summarization"
)


class SummaryGradingTests(unittest.TestCase):
    def test_version_dots_do_not_inflate_sentence_count(self):
        # "llama3.1:8b" and "3.1" must NOT be counted as sentence boundaries.
        self.assertEqual(count_sentences(GOOD_SUMMARY.split("\nKeywords")[0]), 3)

    def test_good_summary_passes(self):
        grade = grade_summary(GOOD_SUMMARY, must_mention=["nomic-embed-text", "llama3.1:8b"])
        self.assertTrue(grade["structural_pass"])
        self.assertEqual(grade["n_sentences"], 3)
        self.assertTrue(5 <= grade["n_keywords"] <= 8)

    def test_banned_phrase_fails(self):
        bad = (
            "The session covered various topics. It resolved several issues. "
            "Work continued afterward.\nKeywords: a, b, c, d, e"
        )
        self.assertFalse(grade_summary(bad)["structural_pass"])

    def test_missing_must_mention_fails(self):
        grade = grade_summary(GOOD_SUMMARY, must_mention=["kubernetes"])
        self.assertFalse(grade["structural_pass"])
        self.assertIn("kubernetes", grade["missing_mentions"])

    def test_wrong_keyword_count_fails(self):
        too_few = (
            "One sentence here. Two sentences here. Three sentences here.\n"
            "Keywords: a, b"
        )
        self.assertFalse(grade_summary(too_few)["structural_pass"])

    def test_keyword_recall(self):
        self.assertEqual(keyword_recall("has ollama and deepseek", ["ollama", "deepseek"]), 1.0)
        self.assertEqual(keyword_recall("has ollama only", ["ollama", "deepseek"]), 0.5)


class ProvenanceTriageTests(unittest.TestCase):
    def test_no_regression_ok(self):
        code, _ = classify(regressed=False, current_ctx={}, baseline_ctx={})
        self.assertEqual(code, EXIT_OK)

    def test_regression_same_model_is_genuine(self):
        ctx = {"model_digest": "abc123", "model_name": "llama3.1:8b"}
        code, msg = classify(regressed=True, current_ctx=ctx, baseline_ctx=ctx)
        self.assertEqual(code, EXIT_REGRESSION)
        self.assertIn("REGRESSION", msg)

    def test_regression_changed_model_needs_rebaseline(self):
        base = {"model_digest": "abc123", "model_name": "llama3.1:8b"}
        cur = {"model_digest": "def456", "model_name": "llama3.1:8b"}
        code, msg = classify(regressed=True, current_ctx=cur, baseline_ctx=base)
        self.assertEqual(code, EXIT_NEEDS_REBASELINE)
        self.assertIn("NEEDS REBASELINE", msg)


if __name__ == "__main__":
    unittest.main()
