"""Unit tests for eval_provenance comparison signature (JudgeBench T3)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_provenance import (
    EXIT_NEEDS_REBASELINE,
    attach_comparison_signature,
    build_comparison_signature,
    classify,
    comparison_signature_changed,
    comparison_signature_digest,
)


class ComparisonSignatureTests(unittest.TestCase):
    def _base_sig(self, **overrides):
        base = build_comparison_signature(
            evaluation_surface="judgebench-semantic-v1",
            case_hash="case123",
            fixture_hash_value="fix456",
            gold_hash="gold789",
            identity_policy_version="identity-registry-v1",
            resolved_identities={
                "judge": {"base_lineage": "deepseek-v4-pro"},
                "under_test": {"base_lineage": "llama3.1:8b"},
            },
            judge_pin={"model": "deepseek-v4-pro", "digest": "abc"},
            under_test_provenance={"model": "llama3.1:8b"},
            independence_class="cross_family",
            decoding_params={"temperature": 0},
            model_serving_version="0.5.0",
            metric_policy_version="v1",
        )
        base.update(overrides)
        return base

    def test_identical_signatures_have_stable_digest(self):
        a = self._base_sig()
        b = self._base_sig()
        self.assertEqual(comparison_signature_digest(a), comparison_signature_digest(b))

    def test_judge_pin_change_detected(self):
        base = self._base_sig()
        altered = self._base_sig(judge_pin={"model": "deepseek-v4-flash", "digest": "xyz"})
        changed, reasons = comparison_signature_changed(
            attach_comparison_signature({}, base),
            attach_comparison_signature({}, altered),
        )
        self.assertTrue(changed)
        self.assertTrue(any("judge_pin" in r for r in reasons))

    def test_evidence_id_change_detected(self):
        base = self._base_sig()
        altered = self._base_sig(case_hash="different-case")
        changed, _ = comparison_signature_changed(
            attach_comparison_signature({}, base),
            attach_comparison_signature({}, altered),
        )
        self.assertTrue(changed)

    def test_regression_with_signature_change_needs_rebaseline(self):
        sig = self._base_sig()
        cur_ctx = attach_comparison_signature({"model_name": "llama3.1:8b"}, sig)
        base_ctx = attach_comparison_signature(
            {"model_name": "llama3.1:8b"},
            self._base_sig(judge_pin={"model": "other-judge", "digest": "zzz"}),
        )
        code, msg = classify(regressed=True, current_ctx=cur_ctx, baseline_ctx=base_ctx)
        self.assertEqual(code, EXIT_NEEDS_REBASELINE)
        self.assertIn("NEEDS REBASELINE", msg)


if __name__ == "__main__":
    unittest.main()
