"""JudgeBench contract + structural-validation tests (slices S3 and S4).

Covers the golden cases for:

- S3 ``eval_judgebench/contracts.py``: SemanticJudgmentV1 / JudgeInvocationV1
  to_dict round-trip and rejection of unknown JSON properties.
- S4 ``eval_judgebench/contract_validate.py``: universal structural rules
  (reason requiredness/length for borderline and fail, universal
  contradiction-present-with-pass, malformed -> invalid_output signal).

No Chroma and no live model calls.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_judgebench import contract_validate as cv  # noqa: E402
from eval_judgebench.contracts import (  # noqa: E402
    InvocationStatus,
    JudgeInvocationV1,
    SemanticJudgmentV1,
    SelectionRole,
    StructuralContractError,
)


class SemanticJudgmentContractTests(unittest.TestCase):
    VALID = {
        "support": "full",
        "coverage": "complete",
        "contradiction": "none",
        "verdict": "pass",
    }

    def test_round_trip_valid(self):
        j = SemanticJudgmentV1.from_dict(self.VALID)
        self.assertEqual(j.to_dict(), self.VALID)

    def test_extra_key_rejected(self):
        with self.assertRaises(StructuralContractError):
            SemanticJudgmentV1.from_dict({**self.VALID, "bogus": 1})

    def test_invalid_enum_rejected(self):
        with self.assertRaises(StructuralContractError):
            SemanticJudgmentV1.from_dict({**self.VALID, "contradiction": "mutant"})

    def test_missing_required_rejected(self):
        with self.assertRaises(StructuralContractError):
            SemanticJudgmentV1.from_dict({"support": "full"})

    def test_optional_confidence_and_reason_round_trip(self):
        raw = {
            **self.VALID,
            "verdict": "borderline",
            "model_reported_confidence": "low",
            "reason": "candidate grounding is thin",
        }
        j = SemanticJudgmentV1.from_dict(raw)
        self.assertEqual(j.to_dict(), raw)

    def test_invalid_confidence_rejected(self):
        with self.assertRaises(StructuralContractError):
            SemanticJudgmentV1.from_dict(
                {**self.VALID, "model_reported_confidence": "very-high"}
            )

    def test_from_dict_non_object_rejected(self):
        with self.assertRaises(StructuralContractError):
            SemanticJudgmentV1.from_dict(["not", "a", "dict"])


class JudgeInvocationContractTests(unittest.TestCase):
    def test_round_trip_with_semantic_judgment(self):
        base = {
            "status": "ok",
            "judge_identity": "judge-a",
            "under_test_identity": "model-b",
        }
        sj = {
            "support": "full",
            "coverage": "complete",
            "contradiction": "none",
            "verdict": "pass",
        }
        inv = JudgeInvocationV1.from_dict({**base, "semantic_judgment": sj})
        self.assertEqual(inv.status, InvocationStatus.OK)
        self.assertEqual(inv.role, SelectionRole.PRIMARY)
        self.assertEqual(inv.to_dict()["semantic_judgment"], sj)
        # non-ok status with no judgment still round-trips
        fail_inv = JudgeInvocationV1.from_dict(
            {**base, "status": "provider_error", "failure_code": "E_TIMEOUT"}
        )
        self.assertEqual(fail_inv.status, InvocationStatus.PROVIDER_ERROR)
        self.assertIsNone(fail_inv.semantic_judgment)

    def test_unknown_props_rejected(self):
        base = {
            "status": "ok",
            "judge_identity": "judge-a",
            "under_test_identity": "model-b",
        }
        with self.assertRaises(StructuralContractError):
            JudgeInvocationV1.from_dict({**base, "extra": True})


class UniversalContractValidationTests(unittest.TestCase):
    def _judgment(self, **overrides):
        base = {
            "support": "full",
            "coverage": "complete",
            "contradiction": "none",
            "verdict": "pass",
        }
        base.update(overrides)
        return SemanticJudgmentV1.from_dict(base)

    def test_valid_pass_ok(self):
        res = cv.validate_judgment(self._judgment())
        self.assertTrue(res.valid)
        self.assertEqual(res.as_status(), InvocationStatus.OK)

    def test_borderline_without_reason_invalid(self):
        res = cv.validate_judgment(
            self._judgment(verdict="borderline", coverage="minor_omission")
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.as_status(), InvocationStatus.INVALID_OUTPUT)

    def test_fail_without_reason_invalid(self):
        res = cv.validate_judgment(
            self._judgment(
                verdict="fail",
                support="none",
                coverage="material_omission",
                contradiction="present",
            )
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.as_status(), InvocationStatus.INVALID_OUTPUT)

    def test_fail_with_reason_valid(self):
        res = cv.validate_judgment(
            self._judgment(
                verdict="fail",
                support="none",
                coverage="material_omission",
                contradiction="present",
                reason="material omissions present; baseline unsupported",
            )
        )
        self.assertTrue(res.valid)

    def test_reason_too_long_invalid(self):
        res = cv.validate_judgment(
            self._judgment(
                verdict="fail",
                support="none",
                coverage="material_omission",
                contradiction="present",
                reason="x" * 321,
            )
        )
        self.assertFalse(res.valid)

    def test_contradiction_present_with_pass_invalid(self):
        res = cv.validate_judgment(
            self._judgment(contradiction="present")
        )
        self.assertFalse(res.valid)

    def test_malformed_raw_signal_invalid_output(self):
        res = cv.validate_judgment_dict(
            {"support": "full", "contradiction": "??", "coverage": "bad"}
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.as_status(), InvocationStatus.INVALID_OUTPUT)


if __name__ == "__main__":
    unittest.main()
