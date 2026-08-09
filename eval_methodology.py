"""Runtime methodology controls shared by LLM-judge eval harnesses."""

from __future__ import annotations

from typing import Any, Callable

NEGATIVE_CONTROL_MAX_EXCLUSIVE = 3

_LEGACY_JUDGE_ERROR = "error: --judge requires --legacy (legacy 1-5 path only)"


def enforce_legacy_judge_gate(use_judge: bool, legacy: bool) -> int | None:
    """Return exit code 2 when ``--judge`` is set without ``--legacy``."""
    if use_judge and not legacy:
        import sys

        print(_LEGACY_JUDGE_ERROR, file=sys.stderr)
        return 2
    return None


_CONTROLS = {
    "summary": {
        "source": "The deployment remained disabled for the entire observation window.",
        "output": "The deployment was enabled and serving production traffic.",
    },
    "synthesis": {
        "source": (
            "Question: Was Shadow enabled?\n"
            "Retrieved evidence: Shadow remained disabled; activation was forbidden."
        ),
        "output": "Yes. Shadow was enabled and activation completed successfully.",
    },
}


def run_judge_negative_control(
    kind: str,
    *,
    under_test_model: str,
    cfg: dict,
    judge_fn: Callable[..., Any] | None = None,
    legacy: bool = True,
) -> dict:
    """Run one known-false output through the actual judge path.

    A score of 3 means "broadly/mostly correct" in the existing rubrics, so a
    deliberately contradictory output proves rejection only when it scores
    below 3. Missing scores and judge errors fail closed for judge evidence.
    """
    if kind not in _CONTROLS:
        raise ValueError(f"unknown negative-control kind: {kind!r}")
    if judge_fn is None:
        from eval_judge import judge

        judge_fn = judge
    control = _CONTROLS[kind]
    result = judge_fn(
        kind,
        control["source"],
        control["output"],
        under_test_model=under_test_model,
        cfg=cfg,
        legacy=legacy,
    )
    score = result.score
    passed = score is not None and score < NEGATIVE_CONTROL_MAX_EXCLUSIVE
    return {
        "kind": kind,
        "passed": passed,
        "score": score,
        "threshold": f"<{NEGATIVE_CONTROL_MAX_EXCLUSIVE}",
        "independent": bool(result.independent),
        "judge_model": result.judge_model,
        "reason": result.reason,
    }


def print_judge_summary(report: dict) -> None:
    """Print advisory judge mean and negative-control lines for eval CLIs."""
    indep = report.get("judge_independent")
    tag = "INDEPENDENT" if indep else "NON-INDEPENDENT (informational only)"
    print(f"Judge mean: {report.get('judge_mean')} [{tag}] model={report.get('judge_model')}")
    control = report["negative_control"]
    mark = "PASS" if control["passed"] else "FAIL"
    print(
        f"Judge negative control: {mark} score={control['score']} expected={control['threshold']}"
    )


def exit_if_judge_negative_control_failed(use_judge: bool, report: dict) -> int | None:
    """Return exit code 1 when judge negative control failed."""
    if use_judge and not report["negative_control"]["passed"]:
        import sys

        print("\nJudge evidence unusable: negative control failed", file=sys.stderr)
        return 1
    return None


def judge_mean_regressed(report: dict, baseline: dict) -> bool:
    """True when an independent judge mean dropped below the stored baseline."""
    return bool(
        report.get("judge_independent")
        and baseline.get("judge_independent")
        and report.get("judge_mean") is not None
        and baseline.get("judge_mean") is not None
        and report["judge_mean"] < baseline["judge_mean"]
    )


def eval_metric_regressed(report: dict, baseline: dict, *, metric_key: str) -> bool:
    """Regression on deterministic metric, plus independent judge mean when applicable."""
    regressed = report[metric_key] < baseline.get(metric_key, 0)
    if judge_mean_regressed(report, baseline):
        regressed = True
    return regressed


def finalize_eval_against_baseline(
    *,
    baseline_path,
    update_baseline: bool,
    report: dict,
    metric_key: str,
) -> int:
    """Write baseline, or compare report against stored baseline and classify."""
    import json
    import sys
    from pathlib import Path

    from eval_provenance import EXIT_OK, classify

    path = Path(baseline_path)
    if update_baseline:
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote baseline {path}")
        return EXIT_OK

    if not path.is_file():
        print(f"\nNo baseline at {path} — run with --update-baseline", file=sys.stderr)
        return 1

    baseline = json.loads(path.read_text(encoding="utf-8"))
    regressed = eval_metric_regressed(report, baseline, metric_key=metric_key)
    code, msg = classify(
        regressed=regressed,
        current_ctx=report["provenance"],
        baseline_ctx=baseline.get("provenance", {}),
    )
    print(f"\n{msg}")
    return code
