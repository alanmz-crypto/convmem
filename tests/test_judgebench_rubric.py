"""JudgeBench rubric loader + data-driven validation tests (slices S5 and S6).

Covers:

- S5 ``eval_judgebench/rubric.py``: load a versioned rubric by id, unknown ids
  raise, id/version mismatch refused.
- S6 ``eval_judgebench/rubric_validate.py``: judgments are checked against the
  reference rubric's data (permitted vs forbidden combinations, justified vs
  unjustified abstention) with no hard-coded task semantics.

Golden judgments are the ones specified for synthesis in
ARCHITECTURE-judgebench.md (S5/S6 reference rubric data).
"""

# pylint: disable=wrong-import-position
# Import must follow the repository-root sys.path bootstrap below so this test
# runs both under pytest and as a direct script (matching existing test style).
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_judgebench.contracts import (
    InvocationStatus,
    SemanticJudgmentV1,
)
from eval_judgebench.rubric import (
    RubricFormatError,
    RubricNotFoundError,
    load_rubric,
)
from eval_judgebench.rubric_validate import (
    validate_against_rubric,
)

RUBRIC_DIR = (
    Path(__file__).resolve().parent.parent
    / "eval_corpus"
    / "fixtures"
    / "judgebench"
    / "semantic-v1"
    / "rubrics"
)
RUBRIC_ID = "synthesis-grounded-v1"


def _judgment(supp, cov, contra, verdict, reason=None):
    raw = {
        "support": supp,
        "coverage": cov,
        "contradiction": contra,
        "verdict": verdict,
    }
    if reason is not None:
        raw["reason"] = reason
    return SemanticJudgmentV1.from_dict(raw)


class RubricLoaderTests(unittest.TestCase):
    def test_load_reference_rubric(self):
        r = load_rubric(RUBRIC_DIR, RUBRIC_ID)
        self.assertEqual(r.id, RUBRIC_ID)
        self.assertEqual(r.task, "synthesis")
        self.assertTrue(r.rules)

    def test_unknown_id_raises(self):
        with self.assertRaises(RubricNotFoundError):
            load_rubric(RUBRIC_DIR, "no-such-rubric")

    def test_absent_directory_unknown_id_raises(self):
        with self.assertRaises(RubricNotFoundError):
            load_rubric(Path(tempfile.mkdtemp()), "whatever")

    def test_id_mismatch_in_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "alias.json"
            path.write_text(
                json.dumps({"id": "other", "version": 1, "task": "synthesis"})
            )
            with self.assertRaises(RubricFormatError):
                load_rubric(Path(td), "alias")

    def test_missing_field_raises(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "t.json"
            path.write_text(json.dumps({"version": 1}))
            with self.assertRaises(RubricFormatError):
                load_rubric(Path(td), "t")


class RubricValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rubric = load_rubric(RUBRIC_DIR, RUBRIC_ID)

    def test_permitted_pass(self):
        res = validate_against_rubric(
            _judgment("full", "complete", "none", "pass"), self.rubric
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.as_status(), InvocationStatus.OK)

    def test_justified_abstention_is_valid(self):
        res = validate_against_rubric(
            _judgment("not_applicable", "complete", "none", "pass"), self.rubric
        )
        self.assertTrue(res.valid)
        self.assertIn("justified", res.note)

    def test_unjustified_abstention_as_pass_is_invalid(self):
        # claiming a pass while coverage materially omitted is forbidden
        res = validate_against_rubric(
            _judgment("not_applicable", "material_omission", "none", "pass"),
            self.rubric,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.as_status(), InvocationStatus.INVALID_OUTPUT)

    def test_full_coverage_material_omission_pass_invalid(self):
        res = validate_against_rubric(
            _judgment("full", "material_omission", "none", "pass"), self.rubric
        )
        self.assertFalse(res.valid)

    def test_honest_unjustified_abstention_fail_valid(self):
        res = validate_against_rubric(
            _judgment(
                "not_applicable",
                "material_omission",
                "none",
                "fail",
                reason="material omissions present",
            ),
            self.rubric,
        )
        self.assertTrue(res.valid)
        self.assertIn("expected verdict 'fail'", res.note)

    def test_fail_without_reason_fails_universal_first(self):
        # universal structural rule fires before rubric classification
        res = validate_against_rubric(
            _judgment("not_applicable", "material_omission", "none", "fail"),
            self.rubric,
        )
        self.assertFalse(res.valid)


if __name__ == "__main__":
    unittest.main()
