"""Recursive structural deny rules for adjudicator-visible artifacts."""

from __future__ import annotations

import re
from typing import Any

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.firewall import canonicalize_field_name

ADJUDICATION_VIEW_ALLOWED_FIELDS = frozenset(
    {
        "schema_version",
        "roster_digest",
        "items",
        "episode_id",
        "opaque_occurrence_token",
        "opaque_span_token",
        "source_class",
        "condition_neutral_source_inventory",
        "condition_neutral_evidence_availability",
        "event_time",
        "authorship",
        "chronology",
        "reply_structure",
        "canonical_evidence_content",
        "attachment_material_availability",
        "extension_field_presence",
        "completeness_scope_without_resolver_result",
        "source_presence",
        "verbatim_evidence_availability",
        "summary_evidence_availability",
        "inventory_entries",
        "declared_omissions",
        "representation",
        "opaque_content_token",
        "structure_state",
        "ordering_state",
        "thread_state",
        "attachment_state",
        "extension_state",
        "scope_state",
    }
)

_FORBIDDEN_KEY_FRAGMENTS = (
    "resolver",
    "capability",
    "assurance",
    "locator",
    "path",
    "native_",
    "physical_instance",
    "revision_or_asof",
    "profile_id",
    "adapter_implementation",
    "retry",
    "queue",
    "backoff",
    "cache",
    "join_readiness",
    "capture_timestamp",
    "capture_time",
    "resolver_timestamp",
    "resolved_at",
    "latency",
    "duration",
    "traceback",
    "metadata",
    "debug",
    "extra",
    "registry",
    "target_census",
    "candidate_id",
    "target_id",
    # Operational side-channel / error diagnostics (structural keys only).
    "attempt",
    "error",
    "errno",
    "exception",
    "stack_trace",
    "stacktrace",
    "stack",
    "status_code",
    "error_category",
    "filesystem_mtime",
    "file_mtime",
    "fs_time",
    "mtime",
)

_ESCAPE_KEYS = frozenset({"metadata", "debug", "extra"})

_ALIAS_DENY = {
    "resolverResult": "resolver_result",
    "resolver-result": "resolver_result",
    "capabilityVector": "capability_vector",
    "capability-vector": "capability_vector",
}

_CAMEL_BOUNDARY_LOWER_UPPER = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_BOUNDARY_UPPER_RUN = re.compile(r"([A-Z]+)([A-Z][a-z])")


def _normalize_structural_key_for_deny(key: str) -> str:
    """Collapse snake/camel/Pascal/hyphen spellings to one comparison token."""

    normalized = key.replace("-", "_")
    normalized = _CAMEL_BOUNDARY_LOWER_UPPER.sub(r"\1_\2", normalized)
    normalized = _CAMEL_BOUNDARY_UPPER_RUN.sub(r"\1_\2", normalized)
    return normalized.lower().replace("_", "")


def _is_forbidden_structural_key(key: str, *, allowed: frozenset[str]) -> bool:
    if key in allowed:
        return False
    canonical = _ALIAS_DENY.get(key, canonicalize_field_name(key))
    if canonical in {"resolver_result", "capability_vector"}:
        return True
    if key in _ESCAPE_KEYS:
        return True
    normalized_key = _normalize_structural_key_for_deny(key)
    return any(
        _normalize_structural_key_for_deny(fragment) in normalized_key
        for fragment in _FORBIDDEN_KEY_FRAGMENTS
    )


def validate_adjudication_view_structure(
    value: Any,
    *,
    label: str,
    allowed: frozenset[str] = ADJUDICATION_VIEW_ALLOWED_FIELDS,
    path: str = "",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{path}.{key}" if path else key
            if _is_forbidden_structural_key(key, allowed=allowed):
                raise StructuralContractError(
                    f"{label}: forbidden structural field '{key}' at {current}"
                )
            validate_adjudication_view_structure(
                child, label=label, allowed=allowed, path=current
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_adjudication_view_structure(
                child, label=label, allowed=allowed, path=f"{path}[{index}]"
            )
