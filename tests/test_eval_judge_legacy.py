"""Legacy eval_judge isolation tests (JudgeBench T5)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_judge import JudgeResult, LegacyJudgeRequiredError, aggregate, judge

_V1_FIELDS = {
    "support",
    "coverage",
    "contradiction",
    "verdict",
    "model_reported_confidence",
    "independence_class",
    "semantic_judgment",
    "comparison_signature",
    "comparison_signature_digest",
}


class LegacyJudgeGateTests(unittest.TestCase):
    def test_judge_without_legacy_raises(self):
        with self.assertRaises(LegacyJudgeRequiredError):
            judge("summary", "src", "out", under_test_model="m", cfg={"models": {}})

    @patch("eval_judge.generate", return_value="SCORE: 4\nREASON: ok\nCONFIDENCE: high")
    @patch("eval_judge.resolve_judge_model", return_value=("deepseek-v4-pro", True))
    def test_legacy_path_returns_byte_compatible_dict(self, _model, _gen):
        result = judge(
            "summary",
            "source text",
            "output text",
            under_test_model="llama3.1:8b",
            cfg={"models": {}},
            legacy=True,
        )
        payload = result.to_dict()
        self.assertEqual(
            set(payload.keys()),
            {
                "score",
                "reason",
                "independent",
                "judge_model",
                "under_test_model",
                "confidence",
                "low_confidence",
            },
        )
        self.assertTrue(all(key not in payload for key in _V1_FIELDS))

    def test_aggregate_has_no_v1_fields(self):
        results = [
            JudgeResult(
                score=4,
                reason="ok",
                independent=True,
                judge_model="deepseek-v4-pro",
                under_test_model="llama3.1:8b",
            )
        ]
        payload = aggregate(results)
        self.assertIn("judge_mean", payload)
        self.assertTrue(all(key not in payload for key in _V1_FIELDS))


if __name__ == "__main__":
    unittest.main()
