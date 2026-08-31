"""P1/P2 structural firewall — normalize known aliases, deny all P2 leakage."""

from __future__ import annotations

import re
from typing import Any

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.contracts import P1_FORBIDDEN_FIELDS

P2_CANONICAL_FORBIDDEN_ON_P1 = frozenset({"resolver_result", "capability_vector"})

P2_KNOWN_ALIASES: dict[str, tuple[str, ...]] = {
    "resolver_result": ("resolverResult", "resolver-result"),
    "capability_vector": ("capabilityVector", "capability-vector"),
}

P2_EXTENDED_FORBIDDEN_ON_P1 = P1_FORBIDDEN_FIELDS | P2_CANONICAL_FORBIDDEN_ON_P1

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in P2_KNOWN_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical

_P2_LIKE_UNKNOWN = re.compile(
    r"(^resolver[_-]|resolver$|capability[_-]|capability$|_vector$)",
    re.IGNORECASE,
)


def canonicalize_field_name(field_name: str) -> str:
    """Map a known alias to its canonical P2 field name."""

    if field_name in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[field_name]
    return field_name


def _is_unknown_p2_like_alias(field_name: str) -> bool:
    if field_name in P2_EXTENDED_FORBIDDEN_ON_P1:
        return False
    if field_name in _ALIAS_TO_CANONICAL:
        return False
    lower = field_name.lower()
    if "resolver" in lower or "capability" in lower:
        return True
    return bool(_P2_LIKE_UNKNOWN.search(field_name))


def scan_object_for_p2_leakage(
    data: Any,
    *,
    label: str,
    path: str = "",
) -> None:
    """Normalize-then-deny scan for P1 payloads."""

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            canonical = canonicalize_field_name(key)
            if canonical in P2_EXTENDED_FORBIDDEN_ON_P1:
                raise StructuralContractError(
                    f"{label}: forbidden P2 field '{canonical}' at {current_path}"
                )
            if _is_unknown_p2_like_alias(key):
                raise StructuralContractError(
                    f"{label}: unknown P2-like alias '{key}' at {current_path}"
                )
            scan_object_for_p2_leakage(value, label=label, path=current_path)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            scan_object_for_p2_leakage(item, label=label, path=f"{path}[{index}]")


def reject_p2_fields_on_p1(data: dict[str, Any], *, label: str) -> None:
    """Fail closed when P1 structural data carries P2 authority fields or aliases."""

    scan_object_for_p2_leakage(data, label=label)


def p1_payload_unchanged_by_p2_scan(before: dict[str, Any], after: dict[str, Any]) -> bool:
    """P1 bytes/authority must not mutate as a side effect of P2 execution."""

    return before == after
