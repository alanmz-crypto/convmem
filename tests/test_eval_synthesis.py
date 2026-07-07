"""Offline unit tests for synthesis-eval grading + judge independence gating.

No live model / Chroma — exercises the deterministic answer grader and the rule
that a non-independent (same-model) judge score is never used for gating.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_grading import grade_answer  # noqa: E402
from eval_judge import JudgeResult, aggregate  # noqa: E402


class AnswerGradingTests(unittest.TestCase):
    def test_answer_with_facts_and_valid_cite_passes(self):
        grade = grade_answer(
            "The SG Security plugin renamed the login slug [1], causing the 404.",
            n_citations=2,
            must_include=["slug"],
            must_cite=True,
        )
        self.assertTrue(grade["pass"])

    def test_hallucinated_citation_index_fails(self):
        grade = grade_answer(
            "The slug changed [5].",
            n_citations=2,
            must_include=["slug"],
            must_cite=True,
        )
        self.assertFalse(grade["pass"])
        self.assertEqual(grade["invalid_cites"], [5])

    def test_missing_required_citation_fails(self):
        grade = grade_answer(
            "The slug changed.",
            n_citations=2,
            must_include=["slug"],
            must_cite=True,
        )
        self.assertFalse(grade["pass"])

    def test_missing_must_include_fails(self):
        grade = grade_answer(
            "Something unrelated [1].",
            n_citations=2,
            must_include=["slug"],
            must_cite=True,
        )
        self.assertFalse(grade["pass"])

    def test_abstention_control_passes_when_it_abstains(self):
        grade = grade_answer(
            "The excerpts do not contain enough information to answer that.",
            n_citations=0,
            should_abstain=True,
        )
        self.assertTrue(grade["pass"])
        self.assertEqual(grade["mode"], "abstain")

    def test_abstention_control_fails_when_it_answers(self):
        grade = grade_answer(
            "The airspeed velocity is 24 miles per hour [1].",
            n_citations=1,
            should_abstain=True,
        )
        self.assertFalse(grade["pass"])


class JudgeIndependenceGatingTests(unittest.TestCase):
    def _gate_uses_judge(self, report: dict, baseline: dict) -> bool:
        """Replicates the eval scripts' judge-gating condition."""
        return bool(
            report.get("judge_independent")
            and baseline.get("judge_independent")
            and report.get("judge_mean") is not None
            and baseline.get("judge_mean") is not None
            and report["judge_mean"] < baseline["judge_mean"]
        )

    def test_non_independent_batch_reported_not_independent(self):
        jrs = [
            JudgeResult(5, "ok", independent=True, judge_model="llama3.1:8b", under_test_model="llama3.1:8b"),
            JudgeResult(2, "meh", independent=False, judge_model="llama3.1:8b", under_test_model="llama3.1:8b"),
        ]
        agg = aggregate(jrs)
        self.assertFalse(agg["judge_independent"])  # mixed -> not independent

    def test_non_independent_judge_excluded_from_gate(self):
        # Judge score dropped hard, but judge is not independent -> must NOT gate.
        report = {"judge_independent": False, "judge_mean": 1.0}
        baseline = {"judge_independent": False, "judge_mean": 5.0}
        self.assertFalse(self._gate_uses_judge(report, baseline))

    def test_independent_judge_drop_does_gate(self):
        report = {"judge_independent": True, "judge_mean": 2.0}
        baseline = {"judge_independent": True, "judge_mean": 4.0}
        self.assertTrue(self._gate_uses_judge(report, baseline))


if __name__ == "__main__":
    unittest.main()
