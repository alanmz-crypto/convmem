"""R2b v2 contract constants and version-aware manifest validation."""

from __future__ import annotations

import re
from typing import Any

from eval_corpus.run_manifest import (
    R2B_REQUIRED_PROHIBITED,
    REQUIRED_R2B_FIELDS,
    canonical_manifest_body_sha256,
    validate_r2b_manifest_schema,
)

R2B_CONTRACT_VERSION = 2
SERVICE_POLICY_V2 = "no_service_state_changes"
SOURCE_QUIESCENCE_POLICY_V2 = "exclusive_writer_gate_v1"

# Preparation authority prohibited set (architecture §4).
R2B_V2_REQUIRED_PROHIBITED_PREP = frozenset(
    {
        "service_start",
        "service_stop",
        "service_restart",
        "process_signal",
        "process_kill",
        "daemon_reload",
        "config_mutation",
        "source_mutation",
        "backup_restore",
        "cg2_activation",
        "recovery_authority_mutation",
        "capture",
        "packet_accept",
        "accept_and_grant",
        "cleanup_external",
    }
)

# v2 capture manifests inherit v1 prohibited actions plus prep-only extras where
# applicable; schema validation requires the v1 capture set at minimum.
R2B_V2_REQUIRED_PROHIBITED = frozenset(R2B_REQUIRED_PROHIBITED) | R2B_V2_REQUIRED_PROHIBITED_PREP

_RATIFIED_DURATION_RE = re.compile(
    r"\b(900|acquisition_bound|hitl_reservation_bound|capture_bound|"
    r"release_close_bound|transaction_deadline)\s*[:=]\s*\d+",
    re.IGNORECASE,
)


def _contract_version_errors(manifest: dict[str, Any]) -> list[str]:
    """Strict contract version parsing — only exact int 2 is valid."""
    raw = manifest.get("r2b_contract_version")
    if raw is None:
        return ["r2b_contract_version is required for v2 manifests"]
    if isinstance(raw, bool):
        return [f"r2b_contract_version must be exact int {R2B_CONTRACT_VERSION}, not bool"]
    if not isinstance(raw, int):
        return [
            f"r2b_contract_version must be exact int {R2B_CONTRACT_VERSION}, "
            f"got {type(raw).__name__}"
        ]
    if raw != R2B_CONTRACT_VERSION:
        return [f"r2b_contract_version must be exact int {R2B_CONTRACT_VERSION}, got {raw}"]
    return []


def detect_contract_version(manifest: dict[str, Any]) -> int:
    """Return manifest contract version; absent or non-exact means v1."""
    raw = manifest.get("r2b_contract_version")
    if raw is None:
        return 1
    if isinstance(raw, int) and not isinstance(raw, bool) and raw == R2B_CONTRACT_VERSION:
        return R2B_CONTRACT_VERSION
    return 1


def validate_v2_policy_fields(manifest: dict[str, Any]) -> list[str]:
    """Validate only the v2 policy triple; does not upgrade v1 manifests."""
    errors: list[str] = []
    errors.extend(_contract_version_errors(manifest))
    if str(manifest.get("service_policy") or "") != SERVICE_POLICY_V2:
        errors.append(f'service_policy must be "{SERVICE_POLICY_V2}"')
    if str(manifest.get("source_quiescence_policy") or "") != SOURCE_QUIESCENCE_POLICY_V2:
        errors.append(
            f'source_quiescence_policy must be "{SOURCE_QUIESCENCE_POLICY_V2}"'
        )
    return errors


def validate_r2b_v2_manifest_schema(manifest: dict[str, Any]) -> list[str]:
    """Phase-scoped R2b v2 capture schema — distinct from v1 validation."""
    errors: list[str] = []
    version = detect_contract_version(manifest)
    if version == 1:
        errors.append(
            "r2b_contract_version absent or 1 — use validate_r2b_manifest_schema for v1"
        )
        return errors
    errors.extend(validate_v2_policy_fields(manifest))
    # Inherited v1 capture fields (authorization_phase, paths, snapshot, etc.).
    v1_errors = validate_r2b_manifest_schema(manifest)
    for msg in v1_errors:
        if "no_service_changes" in msg:
            # v2 uses a different service_policy string by design.
            continue
        errors.append(msg)
    for key in ("r2b_contract_version", "source_quiescence_policy"):
        if key not in manifest:
            errors.append(f"missing required R2b v2 field {key}")
    prohibited = manifest.get("prohibited_actions")
    if isinstance(prohibited, list):
        prohibited_set = {str(x) for x in prohibited if isinstance(x, str)}
        missing = sorted(R2B_V2_REQUIRED_PROHIBITED - prohibited_set)
        if missing:
            errors.append(f"prohibited_actions missing required v2 entries: {missing}")
    # Duration policy fields may exist as names only; concrete values are forbidden.
    for field in (
        "acquisition_bound",
        "hitl_reservation_bound",
        "capture_bound",
        "release_close_bound",
        "transaction_deadline",
    ):
        value = manifest.get(field)
        if value is not None and value != "":
            errors.append(
                f"{field} must not carry a concrete production value in v2 manifests"
            )
    return errors


def assert_no_ratified_duration_defaults(payload: str) -> list[str]:
    """Static guard: no silent duration ratification in policy-bearing text."""
    if _RATIFIED_DURATION_RE.search(payload):
        return ["concrete production duration value detected in policy text"]
    if "900 seconds" in payload.lower() or "900s" in payload.lower():
        return ["900 seconds is not ratified"]
    return []


def make_r2b_v2_run_manifest_for_tests(
    *,
    paths: dict[str, Any],
    run_id: str = "test-r2b-v2-run",
    source_snapshot: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Construct an R2b v2 real manifest body (sidecar written separately)."""
    from eval_corpus.run_manifest import make_r2b_run_manifest_for_tests

    body = make_r2b_run_manifest_for_tests(
        paths=paths,
        run_id=run_id,
        source_snapshot=source_snapshot,
        service_policy=SERVICE_POLICY_V2,
        **overrides,
    )
    body["r2b_contract_version"] = R2B_CONTRACT_VERSION
    body["source_quiescence_policy"] = SOURCE_QUIESCENCE_POLICY_V2
    body["prohibited_actions"] = sorted(R2B_V2_REQUIRED_PROHIBITED)
    digest = canonical_manifest_body_sha256(body)
    body["ryan_approved_manifest_sha256"] = digest
    return body


__all__ = [
    "R2B_CONTRACT_VERSION",
    "R2B_V2_REQUIRED_PROHIBITED",
    "R2B_V2_REQUIRED_PROHIBITED_PREP",
    "SERVICE_POLICY_V2",
    "SOURCE_QUIESCENCE_POLICY_V2",
    "REQUIRED_R2B_FIELDS",
    "_contract_version_errors",
    "assert_no_ratified_duration_defaults",
    "detect_contract_version",
    "make_r2b_v2_run_manifest_for_tests",
    "validate_r2b_v2_manifest_schema",
    "validate_v2_policy_fields",
]
