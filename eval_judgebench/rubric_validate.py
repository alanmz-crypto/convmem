"""Rubric-scoped validation of SemanticJudgmentV1 against rubric data.

The rubric file (a versioned JSON under a corpus ``rubrics/`` dir) carries the
permitted/forbidden field combinations for its task. This validator is fully
data-driven: it reads ``rules.forbids``, ``rules.justified_abstention``, and
``rules.unjustified_abstention_verdict`` from the rubric.

It deliberately hard-codes **no** task semantics (e.g. synthesis abstention
combinations are data in the rubric, not code here), so a future task that
uses SemanticJudgmentV1 does not inherit synthesis abstention rules.

A judgment matching a ``forbids`` combination is ``invalid_output`` -- never a
coerced semantic guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eval_judgebench.contract_validate import validate_judgment
from eval_judgebench.contracts import (
    InvocationStatus,
    SemanticJudgmentV1,
    Support,
)
from eval_judgebench.rubric import Rubric, load_rubric


@dataclass
class RubricValidation:
    valid: bool
    violations: list[str]
    # Human-readable classification note produced from rubric data.
    note: str

    def as_status(self) -> InvocationStatus:
        return InvocationStatus.OK if self.valid else InvocationStatus.INVALID_OUTPUT


def _combination(judgment: SemanticJudgmentV1) -> dict[str, str]:
    return {
        "support": judgment.support.value,
        "coverage": judgment.coverage.value,
        "contradiction": judgment.contradiction.value,
        "verdict": judgment.verdict.value,
    }


def _pattern_matches(pattern: dict[str, list[str]] | None, combo: dict[str, str]) -> bool:
    if not pattern:
        return False
    for field_key, allowed in pattern.items():
        if combo.get(field_key) not in allowed:
            return False
    return True


def validate_against_rubric(
    judgment: SemanticJudgmentV1,
    rubric: Rubric,
) -> RubricValidation:
    """Check a judgment against a rubric's permitted combinations (as data)."""
    rules = rubric.rules or {}
    structural = validate_judgment(judgment)
    if not structural.valid:
        return RubricValidation(
            valid=False,
            violations=structural.violations,
            note="failed universal contract validation",
        )

    combo = _combination(judgment)
    forbids: list[dict[str, list[str]]] = rules.get("forbids") or []
    for pattern in forbids:
        if _pattern_matches(pattern, combo):
            fields = dict(pattern.items())
            return RubricValidation(
                valid=False,
                violations=[
                    f"judgment matches a forbidden combination in rubric "
                    f"'{rubric.id}': {fields}"
                ],
                note=(
                    f"unjustified or inconsistent per rubric '{rubric.id}' "
                    f"({rubric.task})"
                ),
            )

    # Abstention judgement classification, purely from rubric data.
    if judgment.support == Support.NOT_APPLICABLE:
        justified = rules.get("justified_abstention")
        if _pattern_matches(justified, combo):
            return RubricValidation(
                valid=True,
                violations=[],
                note=f"justified abstention per rubric '{rubric.id}'",
            )
        expected = rules.get("unjustified_abstention_verdict")
        note = (
            f"abstention not classified as justified by rubric '{rubric.id}'"
            + (f"; expected verdict '{expected}'" if expected else "")
        )
        return RubricValidation(valid=True, violations=[], note=note)

    return RubricValidation(
        valid=True,
        violations=[],
        note=f"permitted combination per rubric '{rubric.id}'",
    )


def validate_judgment_against_rubric_file(
    judgment: SemanticJudgmentV1,
    rubric_dir: Path | str,
    rubric_id: str,
) -> RubricValidation:
    """Convenience: load the rubric by id, then validate the judgment."""
    rubric = load_rubric(rubric_dir, rubric_id)
    return validate_against_rubric(judgment, rubric)
