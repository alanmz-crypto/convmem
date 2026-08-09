"""JudgeBench contract + structural-validation tests (slices S3 and S4).

Covers the golden cases for:

- S3 ``eval_judgebench/contracts.py``: SemanticJudgmentV1 / JudgeInvocationV1
  to_dict round-trip and rejection of unknown JSON properties.
- S4 ``eval_judgebench/contract_validate.py``: universal structural rules
  (reason requiredness/length for borderline and fail, universal
  contradiction-present-with-pass, malformed -> invalid_output signal).

No Chroma and no live model calls.
"""

# pylint: disable=wrong-import-position
# Import must follow the repository-root sys.path bootstrap below so this test
# runs both under pytest and as a direct script (matching existing test style).
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_judge import JudgeResult, LegacyJudgeRequiredError, aggregate
from eval_judge import judge as legacy_judge
from eval_judgebench import contract_validate as cv
from eval_judgebench.contracts import (
    Contradiction,
    Coverage,
    IndependenceClass,
    InvocationStatus,
    JudgeInvocationV1,
    SelectionRole,
    SemanticJudgmentV1,
    StructuralContractError,
    Support,
    Verdict,
)
from eval_judgebench.corpus_validate import CorpusValidationError
from eval_judgebench.runner import run_judgebench
from eval_model_identity import (
    CanonicalPreflightError,
    ModelIdentityV1,
    assert_canonical_preflight,
    classify_independence,
    load_registry,
    resolve_identity,
)
from eval_provenance import (
    EXIT_NEEDS_REBASELINE,
    attach_comparison_signature,
    build_comparison_signature,
    classify,
    comparison_signature_changed,
    comparison_signature_digest,
)

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "eval_corpus/fixtures/judgebench/semantic-v1"
REGISTRY = REPO / "eval_corpus/fixtures/judgebench/identity-registry-v1.json"
_CFG = {"models": {"ollama_host": "http://localhost:11434"}}
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


def _identity(
    *,
    configured: str,
    normalized: str,
    provider: str = "ollama",
    family: str | None = "llama",
    lineage: str | None = None,
) -> ModelIdentityV1:
    return ModelIdentityV1(
        configured_name=configured,
        normalized_name=normalized,
        serving_provider=provider,
        family=family,
        base_lineage=lineage or normalized,
        revision_digest="abc",
        quantization="Q4_K_M",
    )


def _write_single_case_corpus(
    root: Path,
    *,
    case_id: str,
    verdict: str = "pass",
    human_curated: bool = True,
) -> None:
    rubric_dir = root / "rubrics"
    rubric_dir.mkdir()
    rubric_src = CORPUS / "rubrics" / "synthesis-grounded-v1.json"
    (rubric_dir / "synthesis-grounded-v1.json").write_text(
        rubric_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    case = {
        "case_id": case_id,
        "task_kind": "synthesis",
        "rubric_id": "synthesis-grounded-v1",
        "instruction": "Answer only from the evidence.",
        "evidence": [{"id": 1, "text": "The launch is Friday."}],
        "candidate": "The launch is Friday [1].",
        "candidate_mode": "answer",
        "candidate_origin": (
            {"kind": "human_curated", "author": "test", "version": "v1"}
            if human_curated
            else {
                "kind": "model_generated",
                "model": "llama3.1:8b",
                "provider": "ollama",
                "version": "test",
            }
        ),
        "tags": ["supported"],
        "split": "calibration",
    }
    cases_text = json.dumps(case, sort_keys=True) + "\n"
    (root / "cases.jsonl").write_text(cases_text, encoding="utf-8")
    gold = {
        "case_id": case_id,
        "j0": {
            "expected_pass": True,
            "expected_candidate_mode": "answer",
            "required_tokens": ["[1]"],
        },
        "j1": {
            "support": "full",
            "coverage": "complete",
            "contradiction": "none",
            "verdict": verdict,
            **({"reason": "test expected non-pass"} if verdict != "pass" else {}),
        },
        "rationale": "Frozen test fixture.",
        "lock": {"status": "locked", "owner": "Ryan", "locked_at": "2026-08-09"},
    }
    gold_text = json.dumps(gold, sort_keys=True) + "\n"
    (root / "gold.jsonl").write_text(gold_text, encoding="utf-8")
    manifest = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
    manifest.update(
        {
            "case_count": 1,
            "case_rows": [case_id],
            "split_policy": {
                "strategy": "stratified",
                "calibration_count": 1,
                "holdout_count": 0,
                "minimum_holdout": 0,
            },
            "gold_lock": {"status": "locked", "owner": "Ryan"},
            "hashes": {
                "cases.jsonl": hashlib.sha256(cases_text.encode()).hexdigest(),
                "gold.jsonl": hashlib.sha256(gold_text.encode()).hexdigest(),
            },
        }
    )
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class ResolveIdentityTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry(REGISTRY)

    @patch("eval_model_identity.model_digest_and_quant", return_value=("d1", "Q4"))
    def test_alias_resolves_to_canonical(self, _mock):
        ident = resolve_identity("qwen3-coder:30b", self.registry, _CFG)
        self.assertEqual(ident.normalized_name, "qwen3-coder")
        self.assertEqual(ident.family, "qwen")

    @patch("eval_model_identity.model_digest_and_quant", return_value=("", ""))
    def test_unknown_name_has_no_family(self, _mock):
        ident = resolve_identity("totally-unknown-model", self.registry, _CFG)
        self.assertIsNone(ident.family)
        self.assertEqual(ident.base_lineage, "totally-unknown-model")


class ClassifyIndependenceTests(unittest.TestCase):
    def test_same_canonical_is_self_including_quant_alias(self):
        judge = _identity(configured="qwen3-coder:30b", normalized="qwen3-coder", family="qwen")
        under = _identity(configured="qwen3-coder:latest", normalized="qwen3-coder", family="qwen")
        self.assertEqual(classify_independence(judge, under), IndependenceClass.SELF)

    def test_cross_family_when_both_families_known(self):
        judge = _identity(
            configured="deepseek-v4-pro",
            normalized="deepseek-v4-pro",
            provider="deepseek",
            family="deepseek",
            lineage="deepseek-v4-pro",
        )
        under = _identity(
            configured="llama3.1:8b",
            normalized="llama3.1:8b",
            family="llama",
            lineage="llama3.1:8b",
        )
        self.assertEqual(classify_independence(judge, under), IndependenceClass.CROSS_FAMILY)

    def test_unknown_when_family_missing(self):
        judge = _identity(configured="deepseek-v4-pro", normalized="deepseek-v4-pro", family="deepseek")
        under = _identity(configured="mystery", normalized="mystery", family=None)
        self.assertEqual(classify_independence(judge, under), IndependenceClass.UNKNOWN)

    def test_not_applicable_for_human_curated(self):
        judge = _identity(configured="deepseek-v4-pro", normalized="deepseek-v4-pro", family="deepseek")
        under = _identity(configured="curated", normalized="curated", family=None)
        result = classify_independence(judge, under, under_test_human_curated=True)
        self.assertEqual(result, IndependenceClass.NOT_APPLICABLE)


class CanonicalPreflightTests(unittest.TestCase):
    def test_cross_family_allowed(self):
        assert_canonical_preflight(IndependenceClass.CROSS_FAMILY)

    def test_unknown_fail_closed(self):
        with self.assertRaises(CanonicalPreflightError):
            assert_canonical_preflight(IndependenceClass.UNKNOWN)

    def test_human_curated_not_applicable_allowed(self):
        assert_canonical_preflight(IndependenceClass.NOT_APPLICABLE)


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
        self.assertEqual(
            comparison_signature_digest(self._base_sig()),
            comparison_signature_digest(self._base_sig()),
        )

    def test_judge_pin_change_detected(self):
        base = self._base_sig()
        altered = self._base_sig(judge_pin={"model": "deepseek-v4-flash", "digest": "xyz"})
        changed, reasons = comparison_signature_changed(
            attach_comparison_signature({}, base),
            attach_comparison_signature({}, altered),
        )
        self.assertTrue(changed)
        self.assertTrue(any("judge_pin" in r for r in reasons))

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


class RunnerDryRunTests(unittest.TestCase):
    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_proposed_corpus_refused_for_canonical(self, _mock_digest, _mock_ver):
        with self.assertRaisesRegex(CorpusValidationError, "Ryan lock"):
            run_judgebench(
                CORPUS,
                cfg=_CFG,
                judge_model="deepseek-v4-pro",
                under_test_model="llama3.1:8b",
                registry_path=REGISTRY,
                semantic_judge=None,
            )

    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_proposed_corpus_informational_dry_run(self, _mock_digest, _mock_ver):
        result = run_judgebench(
            CORPUS,
            cfg=_CFG,
            judge_model="deepseek-v4-pro",
            under_test_model="llama3.1:8b",
            registry_path=REGISTRY,
            semantic_judge=None,
            canonical=False,
        )
        self.assertEqual(len(result.cases), 30)
        self.assertTrue(
            all(case.invocation.status == InvocationStatus.NOT_RUN for case in result.cases)
        )
        self.assertEqual(result.independence_class, IndependenceClass.CROSS_FAMILY)
        self.assertEqual(result.gold_hash_before, result.gold_hash_after)
        self.assertIn(
            "rubric:synthesis-grounded-v1",
            result.comparison_signature["contract_hashes"],
        )
        self.assertIn(
            "rubric:summary-grounded-v1",
            result.comparison_signature["contract_hashes"],
        )

    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_model_generated_origin_cannot_be_overridden_by_config(
        self, _mock_digest, _mock_ver
    ):
        cfg = {**_CFG, "under_test_human_curated": True}
        result = run_judgebench(
            CORPUS,
            cfg=cfg,
            judge_model="deepseek-v4-pro",
            under_test_model="llama3.1:8b",
            registry_path=REGISTRY,
            canonical=False,
        )
        self.assertEqual(result.independence_class, IndependenceClass.CROSS_FAMILY)

    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_same_family_preflight_refused_for_canonical(self, _mock):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_single_case_corpus(
                root,
                case_id="same-family",
                human_curated=False,
            )
            with self.assertRaises(CanonicalPreflightError):
                run_judgebench(
                    root,
                    cfg=_CFG,
                    judge_model="deepseek-v4-pro",
                    under_test_model="deepseek-v4-flash",
                    registry_path=REGISTRY,
                )

    @patch("eval_judgebench.runner.ollama_version", return_value="0.5.0")
    @patch("eval_model_identity.model_digest_and_quant", return_value=("remote", ""))
    def test_conformance_verdict_matches_gold(self, _mock_digest, _mock_ver):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_single_case_corpus(root, case_id="conf-1")
            judgment = SemanticJudgmentV1(
                support=Support.FULL,
                coverage=Coverage.COMPLETE,
                contradiction=Contradiction.NONE,
                verdict=Verdict.PASS,
            )

            def _judge(_case):
                return JudgeInvocationV1(
                    status=InvocationStatus.OK,
                    judge_identity="deepseek-v4-pro",
                    under_test_identity="llama3.1:8b",
                    independence_class=IndependenceClass.CROSS_FAMILY,
                    semantic_judgment=judgment,
                )

            result = run_judgebench(
                root,
                cfg=_CFG,
                judge_model="deepseek-v4-pro",
                under_test_model="llama3.1:8b",
                registry_path=REGISTRY,
                semantic_judge=_judge,
            )
            self.assertTrue(result.cases[0].agrees_with_gold)
            self.assertEqual(
                result.independence_class,
                IndependenceClass.NOT_APPLICABLE,
            )


class LegacyJudgeGateTests(unittest.TestCase):
    def test_judge_without_legacy_raises(self):
        with self.assertRaises(LegacyJudgeRequiredError):
            legacy_judge("summary", "src", "out", under_test_model="m", cfg={"models": {}})

    @patch("eval_judge.generate", return_value="SCORE: 4\nREASON: ok\nCONFIDENCE: high")
    @patch("eval_judge.resolve_judge_model", return_value=("deepseek-v4-pro", True))
    def test_legacy_path_returns_byte_compatible_dict(self, _model, _gen):
        payload = legacy_judge(
            "summary",
            "source text",
            "output text",
            under_test_model="llama3.1:8b",
            cfg={"models": {}},
            legacy=True,
        ).to_dict()
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
        payload = aggregate(
            [
                JudgeResult(
                    score=4,
                    reason="ok",
                    independent=True,
                    judge_model="deepseek-v4-pro",
                    under_test_model="llama3.1:8b",
                )
            ]
        )
        self.assertIn("judge_mean", payload)
        self.assertTrue(all(key not in payload for key in _V1_FIELDS))


if __name__ == "__main__":
    unittest.main()
