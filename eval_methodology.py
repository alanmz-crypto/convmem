"""Runtime methodology controls shared by LLM-judge eval harnesses."""

from __future__ import annotations

from typing import Any, Callable

NEGATIVE_CONTROL_MAX_EXCLUSIVE = 3

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
