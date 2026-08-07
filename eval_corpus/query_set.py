"""Strict query-set validation for the real embedding pilot."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from eval_corpus.recipe_strata import validate_recipe_stratum

QUERY_SCHEMA_VERSION = "canonical_real_v1"
QUERY_NORMALIZATION_VERSION = "nfkc_casefold_whitespace_v1"
APPROVED_DOMAINS = (
    "coding.tooling",
    "web_stack.wordpress",
    "web_stack.security",
    "workflow.git",
    "ai.embedding_eval",
)


class QuerySetValidationError(ValueError):
    """The query set or its package references are not evaluation-safe."""


def normalize_query_text(value: str) -> str:
    """Canonical text used only for duplicate detection, not retrieval."""
    normalized = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def normalized_query_sha256(value: str) -> str:
    return hashlib.sha256(normalize_query_text(value).encode("utf-8")).hexdigest()


def _package_indexes(
    package_units: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_unit: dict[str, dict[str, Any]] = {}
    by_ledger: dict[str, dict[str, Any]] = {}
    for unit in package_units:
        if not isinstance(unit, Mapping):
            raise QuerySetValidationError("package rows must be objects")
        unit_id = str(unit.get("id") or "").strip()
        if not unit_id:
            raise QuerySetValidationError("package unit id must be nonempty")
        if unit_id in by_unit:
            raise QuerySetValidationError(f"duplicate unit_id in package: {unit_id}")
        by_unit[unit_id] = dict(unit)
        ledger_id = str(unit.get("ledger_id") or "").strip()
        if ledger_id:
            if ledger_id in by_ledger:
                raise QuerySetValidationError(
                    f"ambiguous ledger_id in package: {ledger_id}"
                )
            by_ledger[ledger_id] = dict(unit)
    return by_unit, by_ledger


def _resolve_reference(
    reference: Mapping[str, Any],
    *,
    by_unit: dict[str, dict[str, Any]],
    by_ledger: dict[str, dict[str, Any]],
    label: str,
) -> dict[str, Any]:
    namespace = reference.get("namespace")
    if namespace not in {"unit_id", "ledger_id"}:
        raise QuerySetValidationError(
            f"{label} namespace must be unit_id or ledger_id: {namespace!r}"
        )
    identifier = str(reference.get("id") or "").strip()
    if not identifier:
        raise QuerySetValidationError(f"{label} id must be nonempty")
    index = by_unit if namespace == "unit_id" else by_ledger
    unit = index.get(identifier)
    if unit is None:
        raise QuerySetValidationError(f"{label} does not resolve: {namespace}:{identifier}")
    return unit


def _validate_relevance(
    row: Mapping[str, Any],
    *,
    by_unit: dict[str, dict[str, Any]],
    by_ledger: dict[str, dict[str, Any]],
    row_label: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    relevant = row.get("relevant")
    if not isinstance(relevant, list) or not relevant:
        raise QuerySetValidationError(f"{row_label}.relevant must be nonempty")
    resolved: list[dict[str, Any]] = []
    seen_refs: set[tuple[str, str]] = set()
    seen_units: set[str] = set()
    for index, raw in enumerate(relevant):
        label = f"{row_label}.relevant[{index}]"
        if not isinstance(raw, Mapping):
            raise QuerySetValidationError(f"{label} must be an object")
        namespace = raw.get("namespace")
        identifier = str(raw.get("id") or "").strip()
        key = (str(namespace), identifier)
        if key in seen_refs:
            raise QuerySetValidationError(f"duplicate relevance reference: {key}")
        seen_refs.add(key)
        grade = raw.get("grade")
        if isinstance(grade, bool) or not isinstance(grade, (int, float)):
            raise QuerySetValidationError(f"{label}.grade must be numeric")
        if not math.isfinite(float(grade)) or float(grade) <= 0:
            raise QuerySetValidationError(f"{label}.grade must be finite and positive")
        unit = _resolve_reference(
            raw,
            by_unit=by_unit,
            by_ledger=by_ledger,
            label=label,
        )
        unit_id = str(unit["id"])
        if unit_id in seen_units:
            raise QuerySetValidationError(
                f"relevance aliases the same unit more than once: {unit_id}"
            )
        seen_units.add(unit_id)
        resolved.append(dict(unit))
    recipes = [str(unit.get("document_recipe_version") or "") for unit in resolved]
    if any(not recipe for recipe in recipes):
        raise QuerySetValidationError(f"{row_label} relevance has missing recipe")
    try:
        validate_recipe_stratum(str(row.get("recipe_stratum") or ""), recipes)
    except ValueError as exc:
        raise QuerySetValidationError(f"{row_label}: {exc}") from exc
    return resolved, recipes


def validate_canonical_real_query_set(
    rows: list[dict[str, Any]],
    package_units: list[dict[str, Any]],
    *,
    expected_domains: tuple[str, ...] = APPROVED_DOMAINS,
    rows_per_domain: int = 8,
    top_k: int = 5,
) -> dict[str, Any]:
    """Validate the exact schema used by the real pilot against an accepted package."""
    by_unit, by_ledger = _package_indexes(package_units)
    if len(rows) != len(expected_domains) * rows_per_domain:
        raise QuerySetValidationError(
            f"query set must contain {len(expected_domains) * rows_per_domain} rows; "
            f"got {len(rows)}"
        )
    counts: dict[str, int] = defaultdict(int)
    query_ids: set[str] = set()
    normalized_queries: set[str] = set()
    groups: dict[str, str] = {}
    for index, row in enumerate(rows):
        label = f"query[{index}]"
        if not isinstance(row, Mapping):
            raise QuerySetValidationError(f"{label} must be an object")
        if "acceptable_ids" in row:
            raise QuerySetValidationError(f"{label} must not use acceptable_ids")
        query_id = str(row.get("query_id") or "").strip()
        if not query_id or query_id in query_ids:
            raise QuerySetValidationError(f"{label} query_id must be unique and nonempty")
        query_ids.add(query_id)
        domain = str(row.get("domain") or "").strip()
        if domain not in expected_domains:
            raise QuerySetValidationError(f"{label} has unapproved domain: {domain!r}")
        counts[domain] += 1
        query = str(row.get("query") or "").strip()
        if not query:
            raise QuerySetValidationError(f"{label}.query must be nonempty")
        normalized = normalize_query_text(query)
        if normalized in normalized_queries:
            raise QuerySetValidationError(f"duplicate normalized query text: {normalized!r}")
        normalized_queries.add(normalized)
        if row.get("query_normalized_sha256") != normalized_query_sha256(query):
            raise QuerySetValidationError(f"{label}.query_normalized_sha256 mismatch")
        if row.get("top_k") != top_k:
            raise QuerySetValidationError(f"{label}.top_k must equal {top_k}")
        for key in ("author", "reviewer", "source_group_id"):
            if not str(row.get(key) or "").strip():
                raise QuerySetValidationError(f"{label}.{key} must be nonempty")
        source_group = str(row["source_group_id"])
        prior_domain = groups.setdefault(source_group, domain)
        if prior_domain != domain:
            raise QuerySetValidationError(
                f"source_group_id spans domains: {source_group!r}"
            )
        if not isinstance(row.get("relevant_complete"), bool):
            raise QuerySetValidationError(f"{label}.relevant_complete must be boolean")
        resolved, _recipes = _validate_relevance(
            row,
            by_unit=by_unit,
            by_ledger=by_ledger,
            row_label=label,
        )
        if row["relevant_complete"]:
            evidence = row.get("completeness_evidence")
            if not isinstance(evidence, list) or not evidence:
                raise QuerySetValidationError(
                    f"{label}.completeness_evidence required when relevant_complete=true"
                )
        refs = row.get("source_refs")
        if not isinstance(refs, list) or not refs:
            raise QuerySetValidationError(f"{label}.source_refs must be nonempty")
        for ref_index, raw_ref in enumerate(refs):
            if not isinstance(raw_ref, Mapping):
                raise QuerySetValidationError(f"{label}.source_refs[{ref_index}] must be an object")
            _resolve_reference(
                raw_ref,
                by_unit=by_unit,
                by_ledger=by_ledger,
                label=f"{label}.source_refs[{ref_index}]",
            )
        if not resolved:
            raise QuerySetValidationError(f"{label} has no resolved relevance")
    expected_counts = {domain: rows_per_domain for domain in expected_domains}
    if dict(counts) != expected_counts:
        raise QuerySetValidationError(
            f"domain counts mismatch: expected={expected_counts} got={dict(counts)}"
        )
    return {
        "schema_version": QUERY_SCHEMA_VERSION,
        "normalization_version": QUERY_NORMALIZATION_VERSION,
        "row_count": len(rows),
        "domain_counts": dict(sorted(counts.items())),
        "query_ids": sorted(query_ids),
        "source_group_count": len(groups),
        "package_unit_count": len(by_unit),
    }


__all__ = [
    "APPROVED_DOMAINS",
    "QUERY_NORMALIZATION_VERSION",
    "QUERY_SCHEMA_VERSION",
    "QuerySetValidationError",
    "normalize_query_text",
    "normalized_query_sha256",
    "validate_canonical_real_query_set",
]
