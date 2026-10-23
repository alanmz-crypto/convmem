"""Exact-source Kiro admission for guarded incremental routing."""

from __future__ import annotations

from dataclasses import dataclass

KIRO_SESSION_FORMAT = "jsonl_kiro_session"
DEFAULT_KIRO_MAX_TRANSFORM_CHUNKS_PER_RUN = 20
DEFAULT_KIRO_MAX_SOURCE_BYTES = 268435456


@dataclass(frozen=True)
class KiroSessionPolicySettings:
    max_transform_chunks_per_run: int
    max_source_bytes: int
    allow_full_rebuild: bool
    cohort_ledger_path: str | None = None
    cohort_max_paid_http_attempts: int | None = None
    cohort_operation_id: str | None = None


def kiro_admitted_live(
    *,
    production_boundary: bool,
    path_key: str,
    live_sources: tuple[str, ...],
    detected_format: str | None,
    policy: KiroSessionPolicySettings | None,
) -> bool:
    """True when this Kiro transcript is selected for the incremental v2 route."""
    if not production_boundary:
        return False
    if policy is None:
        return False
    if detected_format != KIRO_SESSION_FORMAT:
        return False
    return path_key in live_sources


def selected_kiro_path(
    *,
    path_key: str,
    live_sources: tuple[str, ...],
    detected_format: str | None,
) -> bool:
    if detected_format != KIRO_SESSION_FORMAT:
        return False
    return path_key in live_sources
