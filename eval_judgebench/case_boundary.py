"""Calibration-only projection of locked cases into adapter-safe payloads."""

# Schema projections intentionally mirror the locked corpus field contract.
# pylint: disable=duplicate-code

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class CalibrationBoundaryError(ValueError):
    """Raised before transport when calibration preflight is not exact."""


class HoldoutAccessError(CalibrationBoundaryError):
    """A prompt/report serializer was asked to process a holdout row."""


_SAFE_CASE_FIELDS = {
    "case_id",
    "task_kind",
    "rubric_id",
    "instruction",
    "evidence",
    "candidate",
    "candidate_mode",
}


def _require_calibration(row: Mapping[str, Any]) -> None:
    if row.get("split") == "calibration":
        return
    # Adapter-safe projections intentionally omit split and all corpus-only
    # metadata. They may be re-serialized for provider prompts/reports.
    if "split" not in row and not set(row) - _SAFE_CASE_FIELDS:
        return
    raise HoldoutAccessError(
        "only calibration rows may reach a serializer or transport"
    )


def safe_case(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project a validated calibration row to the adapter-safe case shape."""
    _require_calibration(row)
    return {
        "case_id": row["case_id"],
        "task_kind": row["task_kind"],
        "rubric_id": row["rubric_id"],
        "instruction": row["instruction"],
        "evidence": [
            {"id": item["id"], "text": item["text"]} for item in row["evidence"]
        ],
        "candidate": row["candidate"],
        "candidate_mode": row["candidate_mode"],
    }


def serialize_prompt_case(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return the only case fields permitted in a prompt input envelope."""
    return safe_case(row)
