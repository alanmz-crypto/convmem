"""Shared J1 inner contracts for JudgeBench offline semantic calibration.

Greenfield preview of ARCHITECTURE-judgebench.md (docs/plans) inner contracts:

- ``SemanticJudgmentV1`` - provider-neutral J1 fields/enums.
- ``JudgeInvocationV1`` - execution, identity, independence, telemetry.

These are structure-only contracts: ``from_dict`` rejects unknown JSON
properties (so a drifted producer cannot silently pass), but cross-field
semantic rules (e.g. ``reason`` requiredness, abstention combinations) live
in ``contract_validate.py`` / rubric validators, not here. No Chroma, no
LLM calls, no classification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Support(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"
    NOT_APPLICABLE = "not_applicable"


class Coverage(str, Enum):
    COMPLETE = "complete"
    MINOR_OMISSION = "minor_omission"
    MATERIAL_OMISSION = "material_omission"
    NOT_APPLICABLE = "not_applicable"


class Contradiction(str, Enum):
    NONE = "none"
    PRESENT = "present"


class Verdict(str, Enum):
    PASS = "pass"
    BORDERLINE = "borderline"
    FAIL = "fail"


class ModelReportedConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InvocationStatus(str, Enum):
    OK = "ok"
    INVALID_OUTPUT = "invalid_output"
    PROVIDER_ERROR = "provider_error"
    NOT_RUN = "not_run"


class SelectionRole(str, Enum):
    PRIMARY = "primary"
    FALLBACK = "fallback"


class IndependenceClass(str, Enum):
    SELF = "self"
    SAME_FAMILY = "same_family"
    CROSS_FAMILY = "cross_family"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


def _enum_from_value(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    """Resolve a string to an Enum member; raise ValueError for unknown values."""
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (ValueError, TypeError) as exc:
        allowed = ", ".join(m.value for m in enum_type)
        raise StructuralContractError(
            f"{field_name}: invalid '{value}' (allowed: {allowed})"
        ) from exc


def _require_no_unknown_props(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise StructuralContractError(f"{label}: unknown JSON properties: {names}")


class StructuralContractError(ValueError):
    """Raised when raw data violates the structural JSON contract."""


@dataclass
class SemanticJudgmentV1:
    support: Support
    coverage: Coverage
    contradiction: Contradiction
    verdict: Verdict
    model_reported_confidence: ModelReportedConfidence | None = None
    reason: str | None = None

    _FIELDS = {
        "support",
        "coverage",
        "contradiction",
        "verdict",
        "model_reported_confidence",
        "reason",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticJudgmentV1":
        if not isinstance(data, dict):
            raise StructuralContractError(
                f"SemanticJudgmentV1: expected object, got {type(data).__name__}"
            )
        _require_no_unknown_props(data, cls._FIELDS, "SemanticJudgmentV1")
        try:
            support = _enum_from_value(Support, data["support"], "support")
            coverage = _enum_from_value(Coverage, data["coverage"], "coverage")
            contradiction = _enum_from_value(
                Contradiction, data["contradiction"], "contradiction"
            )
            verdict = _enum_from_value(Verdict, data["verdict"], "verdict")
        except KeyError as exc:
            missing = exc.args[0]
            raise StructuralContractError(
                f"SemanticJudgmentV1: missing required property '{missing}'"
            ) from exc
        conf = data.get("model_reported_confidence")
        confidence = (
            _enum_from_value(ModelReportedConfidence, conf, "model_reported_confidence")
            if conf is not None
            else None
        )
        reason = data.get("reason")
        if reason is not None and not isinstance(reason, str):
            raise StructuralContractError(
                f"SemanticJudgmentV1: 'reason' must be a string, got {type(reason).__name__}"
            )
        return cls(
            support=support,
            coverage=coverage,
            contradiction=contradiction,
            verdict=verdict,
            model_reported_confidence=confidence,
            reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "support": self.support.value,
            "coverage": self.coverage.value,
            "contradiction": self.contradiction.value,
            "verdict": self.verdict.value,
        }
        if self.model_reported_confidence is not None:
            out["model_reported_confidence"] = self.model_reported_confidence.value
        if self.reason is not None:
            out["reason"] = self.reason
        return out


@dataclass
class JudgeInvocationV1:  # pylint: disable=too-many-instance-attributes
    # 12 data fields are dictated by the JudgeInvocationV1 spec (execution,
    # identity, independence, telemetry).
    status: InvocationStatus
    judge_identity: str
    under_test_identity: str
    role: SelectionRole = SelectionRole.PRIMARY
    independence_class: IndependenceClass = IndependenceClass.UNKNOWN
    latency_ms: float | None = None
    response_hash: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost: float | None = None
    failure_code: str | None = None
    semantic_judgment: SemanticJudgmentV1 | None = None

    _FIELDS = {
        "status",
        "judge_identity",
        "under_test_identity",
        "role",
        "independence_class",
        "latency_ms",
        "response_hash",
        "tokens_in",
        "tokens_out",
        "cost",
        "failure_code",
        "semantic_judgment",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JudgeInvocationV1":
        if not isinstance(data, dict):
            raise StructuralContractError(
                f"JudgeInvocationV1: expected object, got {type(data).__name__}"
            )
        _require_no_unknown_props(data, cls._FIELDS, "JudgeInvocationV1")
        try:
            status = _enum_from_value(InvocationStatus, data["status"], "status")
            judge_identity = data["judge_identity"]
            under_test_identity = data["under_test_identity"]
        except KeyError as exc:
            missing = exc.args[0]
            raise StructuralContractError(
                f"JudgeInvocationV1: missing required property '{missing}'"
            ) from exc
        if not isinstance(judge_identity, str) or not isinstance(under_test_identity, str):
            raise StructuralContractError(
                "JudgeInvocationV1: judge_identity and under_test_identity must be strings"
            )
        role = _enum_from_value(
            SelectionRole, data.get("role", SelectionRole.PRIMARY.value), "role"
        )
        independence = _enum_from_value(
            IndependenceClass,
            data.get("independence_class", IndependenceClass.UNKNOWN.value),
            "independence_class",
        )
        sj = data.get("semantic_judgment")
        semantic = (
            SemanticJudgmentV1.from_dict(sj)
            if sj is not None
            else None
        )
        return cls(
            status=status,
            judge_identity=judge_identity,
            under_test_identity=under_test_identity,
            role=role,
            independence_class=independence,
            latency_ms=data.get("latency_ms"),
            response_hash=data.get("response_hash"),
            tokens_in=data.get("tokens_in"),
            tokens_out=data.get("tokens_out"),
            cost=data.get("cost"),
            failure_code=data.get("failure_code"),
            semantic_judgment=semantic,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "status": self.status.value,
            "judge_identity": self.judge_identity,
            "under_test_identity": self.under_test_identity,
            "role": self.role.value,
            "independence_class": self.independence_class.value,
        }
        for field_name in (
            "latency_ms",
            "response_hash",
            "tokens_in",
            "tokens_out",
            "cost",
            "failure_code",
        ):
            value = getattr(self, field_name)
            if value is not None:
                out[field_name] = value
        if self.semantic_judgment is not None:
            out["semantic_judgment"] = self.semantic_judgment.to_dict()
        return out


def dumps(obj: Any) -> str:
    """Serialize a contract (or dict) to compact JSON for round-trip tests."""
    if isinstance(obj, dict):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return json.dumps(obj.to_dict(), sort_keys=True, separators=(",", ":"))
