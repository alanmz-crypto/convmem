"""Offline synthetic coverage for JudgeBench calibration metrics."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from eval_judgebench.calibration import CalibrationPackage
from eval_judgebench.contracts import (
    Contradiction,
    Coverage,
    IndependenceClass,
    InvocationStatus,
    JudgeInvocationV1,
    ModelReportedConfidence,
    SemanticJudgmentV1,
    Support,
    Verdict,
)
from eval_judgebench.metrics import (
    build_calibration_report,
    serialize_calibration_report,
)
from eval_judgebench.runner import CaseResult, MechanicalGrade, RunResult


def _judgment(
    verdict: Verdict,
    *,
    support: Support,
    confidence: ModelReportedConfidence | None = None,
):
    return SemanticJudgmentV1(
        support=support,
        coverage=Coverage.COMPLETE,
        contradiction=Contradiction.NONE,
        verdict=verdict,
        model_reported_confidence=confidence,
    )


def _fixture() -> tuple[CalibrationPackage, RunResult]:
    cases = tuple(
        {
            "case_id": f"cal-{index}",
            "tags": [tag],
            "split": "calibration",
        }
        for index, tag in enumerate(
            ("alpha", "alpha", "beta", "beta", "gamma", "gamma"), 1
        )
    )
    verdicts = ("pass", "borderline", "fail", "fail", "fail", "pass")
    gold_by_id = {
        case["case_id"]: {
            "case_id": case["case_id"],
            "j1": {
                "support": "full" if index == 1 else "partial",
                "coverage": "complete",
                "contradiction": "none",
                "verdict": verdict,
            },
        }
        for index, (case, verdict) in enumerate(zip(cases, verdicts), 1)
    }
    gold_by_id["holdout-1"] = {
        "case_id": "holdout-1",
        "j1": {"verdict": "pass", "evidence": "must not appear"},
    }
    package = CalibrationPackage(
        root=Path("/synthetic"),
        manifest={},
        cases=cases,
        gold_by_id=gold_by_id,
        full_hashes={},
        rubric_hashes={},
    )
    invocations = [
        JudgeInvocationV1(
            status=InvocationStatus.OK,
            judge_identity="judge",
            under_test_identity="under-test",
            independence_class=IndependenceClass.CROSS_FAMILY,
            semantic_judgment=_judgment(
                Verdict.PASS,
                support=Support.FULL,
                confidence=ModelReportedConfidence.HIGH,
            ),
        ),
        JudgeInvocationV1(
            status=InvocationStatus.OK,
            judge_identity="judge",
            under_test_identity="under-test",
            independence_class=IndependenceClass.CROSS_FAMILY,
            semantic_judgment=_judgment(
                Verdict.PASS,
                support=Support.PARTIAL,
                confidence=ModelReportedConfidence.LOW,
            ),
        ),
        JudgeInvocationV1(
            status=InvocationStatus.OK,
            judge_identity="judge",
            under_test_identity="under-test",
            independence_class=IndependenceClass.CROSS_FAMILY,
            semantic_judgment=_judgment(Verdict.PASS, support=Support.PARTIAL),
        ),
        JudgeInvocationV1(
            status=InvocationStatus.INVALID_OUTPUT,
            judge_identity="judge",
            under_test_identity="under-test",
        ),
        JudgeInvocationV1(
            status=InvocationStatus.PROVIDER_ERROR,
            judge_identity="judge",
            under_test_identity="under-test",
        ),
        JudgeInvocationV1(
            status=InvocationStatus.NOT_RUN,
            judge_identity="judge",
            under_test_identity="under-test",
        ),
    ]
    results = [
        CaseResult(
            case_id=case["case_id"],
            mechanical=MechanicalGrade(passed=index != 3),
            invocation=invocation,
            gold_verdict=verdicts[index - 1],
            agrees_with_gold=None,
        )
        for index, (case, invocation) in enumerate(zip(cases, invocations), 1)
    ]
    run = RunResult(
        cases=results,
        independence_class=IndependenceClass.CROSS_FAMILY,
        comparison_signature={},
        provenance={},
        gold_hash_before="",
        gold_hash_after="",
        pinned_judge_model="judge",
    )
    return package, run


def test_metrics_rejects_duplicate_result_ids_before_aggregation() -> None:
    package, run = _fixture()
    duplicate = replace(run, cases=[*run.cases, run.cases[0]])
    with pytest.raises(ValueError, match=r"duplicates=\['cal-1'\]"):
        build_calibration_report(package, duplicate)


def test_metrics_rejects_missing_result_ids_before_aggregation() -> None:
    package, run = _fixture()
    missing = replace(run, cases=run.cases[:-1])
    with pytest.raises(ValueError, match=r"missing=\['cal-6'\]"):
        build_calibration_report(package, missing)


def test_metrics_rejects_extra_result_ids_including_holdout_before_aggregation() -> (
    None
):
    package, run = _fixture()
    extra = replace(
        run,
        cases=[
            *run.cases,
            CaseResult(
                case_id="holdout-1",
                mechanical=MechanicalGrade(passed=True),
                invocation=run.cases[0].invocation,
                gold_verdict="pass",
                agrees_with_gold=True,
            ),
        ],
    )
    with pytest.raises(ValueError, match=r"extra=\['holdout-1'\]"):
        build_calibration_report(package, extra)


def test_metrics_counts_confusion_f1_kappa_and_false_pass() -> None:
    package, run = _fixture()
    report = build_calibration_report(package, run)
    assert report["counts"] == {
        "calibration_cases": 6,
        "scored_cases": 3,
        "unscored_cases": 3,
    }
    assert report["invocation"]["counts"] == {
        "ok": 3,
        "invalid_output": 1,
        "provider_error": 1,
        "not_run": 1,
    }
    assert report["verdict"]["confusion_matrix"]["counts"] == {
        "pass": {"pass": 1, "borderline": 0, "fail": 0},
        "borderline": {"pass": 1, "borderline": 0, "fail": 0},
        "fail": {"pass": 1, "borderline": 0, "fail": 0},
    }
    assert report["verdict"]["accuracy"] == 1 / 3
    assert report["verdict"]["macro_f1"]["value"] == 1 / 6
    assert report["verdict"]["quadratic_weighted_cohen_kappa"]["value"] == 0.0
    assert report["critical_false_pass"] == {
        "count": 1,
        "denominator": 3,
        "rate": 1 / 3,
    }


def test_dimension_agreement_tags_statuses_and_confidence_are_explicit() -> None:
    report = build_calibration_report(*_fixture())
    assert report["dimension_agreement"] == {
        "support": {"agree": 3, "count": 3, "rate": 1.0},
        "coverage": {"agree": 3, "count": 3, "rate": 1.0},
        "contradiction": {"agree": 3, "count": 3, "rate": 1.0},
    }
    assert report["j0_j1_by_tag"]["alpha"]["counts"]["pass"]["pass"] == 2
    assert report["j0_j1_by_tag"]["alpha"]["counts"]["pass"]["borderline"] == 0
    assert report["j0_j1_by_tag"]["beta"]["counts"]["fail"]["pass"] == 1
    assert report["confidence_exploratory"]["buckets"]["high"]["count"] == 1
    assert report["confidence_exploratory"]["buckets"]["low"]["error_rate"] == 1.0
    assert "exploratory" in report["confidence_exploratory"]["label"]


def test_kappa_undefined_reason_and_deterministic_redacted_serialization() -> None:
    package, run = _fixture()
    report = build_calibration_report(package, run)
    empty_run = RunResult([], IndependenceClass.CROSS_FAMILY, {}, {}, "", "", "judge")
    empty = build_calibration_report(
        CalibrationPackage(package.root, {}, (), {}, {}, {}), empty_run
    )
    assert empty["verdict"]["quadratic_weighted_cohen_kappa"] == {
        "value": None,
        "reason": "undefined: no scored cases",
    }
    first = serialize_calibration_report(report)
    second = serialize_calibration_report(json.loads(first))
    assert first == second
    for forbidden in ("evidence", "candidate", "instruction", "rationale", "holdout-1"):
        assert forbidden not in first
