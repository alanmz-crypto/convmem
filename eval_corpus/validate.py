"""Stratified overlap validation + historical non-overlap spot-check reporting."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from eval_corpus.reconstruct import (
    RECIPE_GOVERNED,
    RECIPE_INTER_MODEL,
    RECIPE_ORDINARY,
    reconstruct_document,
    select_recipe,
)

QUOTA = {
    RECIPE_ORDINARY: 40,
    RECIPE_INTER_MODEL: 30,
    RECIPE_GOVERNED: 30,
}


def deterministic_sample_ids(ids: list[str], *, capture_id: str, n: int) -> list[str]:
    """Sort by sha256(id + capture_id), take first n."""
    scored = sorted(
        ids,
        key=lambda i: hashlib.sha256(f"{i}{capture_id}".encode()).hexdigest(),
    )
    return scored[:n]


@dataclass
class OverlapRecipeResult:
    recipe: str
    overlap_count: int
    sampled: int
    exact_matches: int
    mismatches: list[str] = field(default_factory=list)
    status: str = "UNRESOLVED"  # PASS | FAILED | UNRESOLVED


def validate_overlap(
    package_units: list[dict],
    live_documents: dict[str, str],
    *,
    capture_id: str,
) -> dict[str, Any]:
    """Compare reconstructed docs to live Chroma documents for overlapping IDs."""
    by_recipe: dict[str, list[dict]] = {
        RECIPE_ORDINARY: [],
        RECIPE_INTER_MODEL: [],
        RECIPE_GOVERNED: [],
    }
    for u in package_units:
        uid = str(u.get("id") or "")
        if uid not in live_documents:
            continue
        recipe = select_recipe(u)
        by_recipe.setdefault(recipe, []).append(u)

    results: dict[str, Any] = {}
    overall = "PASS"
    any_sampled = False
    for recipe, quota in QUOTA.items():
        units = by_recipe.get(recipe, [])
        overlap_ids = [str(u["id"]) for u in units]
        if not overlap_ids:
            results[recipe] = {
                "overlap_count": 0,
                "quota": quota,
                "sampled": 0,
                "exact_matches": 0,
                "mismatches": [],
                "status": "SKIP",
                "sample_ids": [],
            }
            continue
        # Under-quota still verifies all available IDs (hermetic + sparse live).
        n = min(quota, len(overlap_ids))
        sample_ids = deterministic_sample_ids(
            overlap_ids, capture_id=capture_id, n=n
        )
        status = "PASS"
        mismatches: list[str] = []
        exact = 0
        for uid in sample_ids:
            unit = next(u for u in units if str(u["id"]) == uid)
            # Prefer packaged document when present (canonical units).
            got = str(unit.get("document") or "") or reconstruct_document(unit)
            expected = live_documents[uid]
            if got == expected:
                exact += 1
            else:
                mismatches.append(uid)
                status = "FAILED"
        any_sampled = True
        if status == "FAILED":
            overall = "FAILED"
        results[recipe] = {
            "overlap_count": len(overlap_ids),
            "quota": quota,
            "sampled": len(sample_ids),
            "exact_matches": exact,
            "mismatches": mismatches,
            "status": status,
            "sample_ids": sample_ids,
            "under_quota": len(overlap_ids) < quota,
        }
    if not any_sampled and overall == "PASS":
        overall = "UNRESOLVED"
    return {"overall": overall, "by_recipe": results}


def historical_spot_check_plan(
    export_ids_absent_from_chroma: list[str],
    *,
    capture_id: str,
    n: int = 20,
) -> dict[str, Any]:
    """Deterministic ~20 IDs for human structural sanity review (diagnostic)."""
    sample = deterministic_sample_ids(
        export_ids_absent_from_chroma, capture_id=capture_id, n=n
    )
    return {
        "n_requested": n,
        "n_available": len(export_ids_absent_from_chroma),
        "sample_ids": sample,
        "rule": (
            "Every anomaly must be adjudicated before corpus approval; "
            "systematic reconstruction class stops immediately; "
            "no >50% auto-pass threshold. "
            "Adjudications are recorded in a separate file — this plan is immutable."
        ),
    }
