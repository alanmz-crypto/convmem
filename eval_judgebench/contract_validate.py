"""Universal structural validation for SemanticJudgmentV1.

Only rules that hold across every rubric go here (ARCHITECTURE-judgebench.md
"Universal contract examples"):

- `reason` required when `verdict in {borderline, fail}` and <= 320 chars.
- Truly-universal structural contradiction: cannot assert `contradiction=present`
  while declaring `verdict=pass`.
- Enum membership and unknown-property rejection (defense in depth; the
  contracts layer already enforces these in `from_dict`).

Rubric-scoped semantics (e.g. synthesis abstention combinations, coverage
thresholds) deliberately live in the rubric validator (S5/S6) as data - never
hard-coded here, so future tasks using SemanticJudgmentV1 do not inherit them.

Malformed output yields an ``invalid_output`` signal via ``as_status()`` - it is
never coerced into a plausible verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from eval_judgebench.contracts import (
    InvocationStatus,
    SemanticJudgmentV1,
    Verdict,
)


@dataclass
class JudgmentValidation:
    valid: bool
    violations: list[str]

    def as_status(self) -> InvocationStatus:
        """Signal valid vs invalid_output (never a coerced verdict)."""
        return InvocationStatus.OK if self.valid else InvocationStatus.INVALID_OUTPUT


def _reason_rules(j: SemanticJudgmentV1, violations: list[str]) -> None:
    if j.verdict in (Verdict.BORDERLINE, Verdict.FAIL):
        if not j.reason:
            violations.append(
                f"reason is required when verdict='{j.verdict.value}'"
            )
    if j.reason is not None and len(j.reason) > 320:
        violations.append(
            f"reason exceeds 320 chars ({len(j.reason)})"
        )


def _universal_contradiction(j: SemanticJudgmentV1, violations: list[str]) -> None:
    if j.contradiction.value == "present" and j.verdict == Verdict.PASS:
        violations.append(
            "cannot assert contradiction=present while verdict=pass"
        )


def validate_judgment_dict(raw: dict[str, Any]) -> JudgmentValidation:
    """Validate a raw JSON-adjacent dict, producing an invalid_output signal.

    Uses the contracts layer for enum/unknown-property rejection so malformed
    input cannot silently pass through into a fabricated verdict.
    """
    try:
        judgment = SemanticJudgmentV1.from_dict(raw)
    except Exception as exc:  # StructuralContractError and subclasses
        return JudgmentValidation(valid=False, violations=[str(exc)])
    return validate_judgment(judgment)


def validate_judgment(judgment: SemanticJudgmentV1) -> JudgmentValidation:
    violations: list[str] = []
    _reason_rules(judgment, violations)
    _universal_contradiction(judgment, violations)
    return JudgmentValidation(valid=not violations, violations=violations)


def validate_judgments(judgments: Iterable[SemanticJudgmentV1]) -> list[JudgmentValidation]:
    return [validate_judgment(j) for j in judgments]
