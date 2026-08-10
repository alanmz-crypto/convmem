"""Deterministic, calibration-only JudgeBench metrics and report rendering."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from eval_judgebench.calibration import CalibrationPackage
from eval_judgebench.contracts import InvocationStatus
from eval_judgebench.runner import CaseResult, RunResult

VERDICT_ORDER = ("pass", "borderline", "fail")
DIMENSIONS = ("support", "coverage", "contradiction")
STATUS_ORDER = ("ok", "invalid_output", "provider_error", "not_run")
CONFIDENCE_ORDER = ("low", "medium", "high", "missing")


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _empty_matrix(
    rows: tuple[str, ...], columns: tuple[str, ...]
) -> dict[str, dict[str, int]]:
    return {row: {column: 0 for column in columns} for row in rows}


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _invocation_status(case: CaseResult) -> str:
    if case.invocation is None:
        return InvocationStatus.NOT_RUN.value
    return str(_value(case.invocation.status))


def _judgment(case: CaseResult) -> Any | None:
    invocation = case.invocation
    if invocation is None or _invocation_status(case) != InvocationStatus.OK.value:
        return None
    return invocation.semantic_judgment


def _field(judgment: Any, name: str) -> str | None:
    if judgment is None:
        return None
    return _value(getattr(judgment, name, None))


def _matrix_report(
    matrix: dict[str, dict[str, int]],
    *,
    row_name: str = "gold",
    column_name: str = "judge",
) -> dict[str, Any]:
    return {
        "rows": row_name,
        "columns": column_name,
        "order": list(VERDICT_ORDER),
        "counts": matrix,
    }


def _quadratic_kappa(
    matrix: Mapping[str, Mapping[str, int]], scored: int
) -> dict[str, Any]:
    if scored == 0:
        return {"value": None, "reason": "undefined: no scored cases"}
    observed = (
        sum(
            count * ((i - j) ** 2 / 4)
            for i, gold in enumerate(VERDICT_ORDER)
            for j, judge in enumerate(VERDICT_ORDER)
            for count in (matrix[gold][judge],)
        )
        / scored
    )
    gold_margins = {gold: sum(matrix[gold].values()) for gold in VERDICT_ORDER}
    judge_margins = {
        judge: sum(matrix[gold][judge] for gold in VERDICT_ORDER)
        for judge in VERDICT_ORDER
    }
    expected = sum(
        (gold_margins[gold] * judge_margins[judge] / scored**2) * ((i - j) ** 2 / 4)
        for i, gold in enumerate(VERDICT_ORDER)
        for j, judge in enumerate(VERDICT_ORDER)
    )
    if expected == 0:
        return {
            "value": None,
            "reason": "undefined: zero expected quadratic disagreement",
        }
    value = 1 - (observed / expected)
    return {"value": 0.0 if abs(value) < 1e-12 else value, "reason": None}


def _macro_f1(matrix: Mapping[str, Mapping[str, int]]) -> dict[str, Any]:
    values: dict[str, float] = {}
    for label in VERDICT_ORDER:
        tp = matrix[label][label]
        fp = sum(matrix[gold][label] for gold in VERDICT_ORDER if gold != label)
        fn = sum(matrix[label][judge] for judge in VERDICT_ORDER if judge != label)
        divisor = 2 * tp + fp + fn
        values[label] = 2 * tp / divisor if divisor else 0.0
    return {
        "value": sum(values.values()) / len(VERDICT_ORDER),
        "per_verdict": values,
        "zero_division": "per-verdict F1 is 0.0 when TP+FP+FN is zero",
    }


# The report is one deterministic pass over coupled metric accumulators.
# pylint: disable=too-many-locals
def build_calibration_report(
    package: CalibrationPackage, run: RunResult
) -> dict[str, Any]:
    """Build a JSON-ready report from an exact package calibration result set."""
    calibration_cases = tuple(package.cases)
    calibration_ids = {str(case["case_id"]) for case in calibration_cases}
    result_ids = [str(case.case_id) for case in run.cases]
    duplicate_ids = sorted(
        case_id for case_id in set(result_ids) if result_ids.count(case_id) > 1
    )
    result_id_set = set(result_ids)
    missing_ids = sorted(calibration_ids - result_id_set)
    extra_ids = sorted(result_id_set - calibration_ids)
    if duplicate_ids or missing_ids or extra_ids:
        raise ValueError(
            "RunResult case IDs must exactly match calibration IDs; "
            f"duplicates={duplicate_ids}, missing={missing_ids}, extra={extra_ids}"
        )
    gold_by_id = {
        case_id: package.gold_by_id[case_id] for case_id in sorted(calibration_ids)
    }
    results_by_id = {case.case_id: case for case in run.cases}

    matrix = _empty_matrix(VERDICT_ORDER, VERDICT_ORDER)
    status_counts = {status: 0 for status in STATUS_ORDER}
    dimension_counts = {dimension: {"agree": 0, "count": 0} for dimension in DIMENSIONS}
    confidence = {
        bucket: {"count": 0, "errors": 0, "error_rate": None}
        for bucket in CONFIDENCE_ORDER
    }
    tag_matrices: dict[str, dict[str, Any]] = {}
    scored = 0
    gold_fail_count = 0
    critical_false_passes = 0

    for case in calibration_cases:
        case_id = str(case["case_id"])
        result = results_by_id.get(case_id)
        gold = gold_by_id[case_id].get("j1") or {}
        status = _invocation_status(result) if result is not None else "not_run"
        if status not in status_counts:
            raise ValueError(f"unknown invocation status: {status!r}")
        status_counts[status] += 1
        gold_verdict = str(gold.get("verdict"))
        for tag in sorted(str(tag) for tag in case.get("tags") or []):
            tag_matrices.setdefault(
                tag,
                {
                    "rows": ["pass", "fail"],
                    "columns": list(VERDICT_ORDER),
                    "counts": _empty_matrix(("pass", "fail"), VERDICT_ORDER),
                    "scored_cases": 0,
                    "unscored_cases": 0,
                },
            )
        if gold_verdict == "fail":
            gold_fail_count += 1
        judgment = _judgment(result) if result is not None else None
        judge_verdict = _field(judgment, "verdict")
        correct = judge_verdict == gold_verdict if judge_verdict is not None else False
        if judge_verdict is not None and gold_verdict in VERDICT_ORDER:
            scored += 1
            matrix[gold_verdict][judge_verdict] += 1
            for dimension in DIMENSIONS:
                dimension_counts[dimension]["count"] += 1
                if _field(judgment, dimension) == gold.get(dimension):
                    dimension_counts[dimension]["agree"] += 1
            if gold_verdict == "fail" and judge_verdict == "pass":
                critical_false_passes += 1
            bucket = _field(judgment, "model_reported_confidence") or "missing"
            if bucket not in confidence:
                raise ValueError(f"unknown confidence bucket: {bucket!r}")
            confidence[bucket]["count"] += 1
            confidence[bucket]["errors"] += int(not correct)

            j0 = "pass" if result.mechanical.passed else "fail"
            for tag in sorted(str(tag) for tag in case.get("tags") or []):
                tag_report = tag_matrices[tag]
                tag_report["counts"][j0][judge_verdict] += 1
                tag_report["scored_cases"] += 1
        else:
            for tag in sorted(str(tag) for tag in case.get("tags") or []):
                tag_matrices[tag]["unscored_cases"] += 1

    for dimension in DIMENSIONS:
        item = dimension_counts[dimension]
        item["rate"] = _rate(item["agree"], item["count"])
    for item in confidence.values():
        item["error_rate"] = _rate(item["errors"], item["count"])

    unscored = len(calibration_cases) - scored
    status_rates = {
        status: _rate(count, len(calibration_cases))
        for status, count in status_counts.items()
    }
    return {
        "schema_version": "judgebench-calibration-report-v1",
        "metric_policy": {
            "direction": "descriptive_only",
            "verdict_order": list(VERDICT_ORDER),
            "kappa": "quadratic_weighted_cohen_kappa",
            "kappa_weighting": "quadratic; agreement weight = 1 - ((gold_index - judge_index)^2 / 4)",
        },
        "counts": {
            "calibration_cases": len(calibration_cases),
            "scored_cases": scored,
            "unscored_cases": unscored,
        },
        "invocation": {"counts": status_counts, "rates": status_rates},
        "verdict": {
            "confusion_matrix": _matrix_report(matrix),
            "accuracy": _rate(
                sum(matrix[label][label] for label in VERDICT_ORDER), scored
            ),
            "macro_f1": _macro_f1(matrix),
            "quadratic_weighted_cohen_kappa": _quadratic_kappa(matrix, scored),
        },
        "critical_false_pass": {
            "count": critical_false_passes,
            "denominator": gold_fail_count,
            "rate": _rate(critical_false_passes, gold_fail_count),
        },
        "dimension_agreement": dimension_counts,
        "j0_j1_by_tag": {tag: tag_matrices[tag] for tag in sorted(tag_matrices)},
        "confidence_exploratory": {
            "label": "exploratory; model-reported confidence is telemetry only",
            "buckets": confidence,
        },
    }


# pylint: enable=too-many-locals


def serialize_calibration_report(report: Mapping[str, Any]) -> str:
    """Serialize a report with stable key ordering and JSON separators."""
    return json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


build_report = build_calibration_report
