"""Recipe stratum validation and reporting helpers."""

from __future__ import annotations

from collections import Counter
from typing import Any

from eval_corpus.reconstruct import (
    RECIPE_GOVERNED,
    RECIPE_INTER_MODEL,
    RECIPE_ORDINARY,
)

STRATUM_ORDINARY = "ordinary"
STRATUM_INTER_MODEL = "inter_model"
STRATUM_GOVERNED = "governed"
STRATUM_MIXED = "mixed"

RECIPE_TO_STRATUM = {
    RECIPE_ORDINARY: STRATUM_ORDINARY,
    RECIPE_INTER_MODEL: STRATUM_INTER_MODEL,
    RECIPE_GOVERNED: STRATUM_GOVERNED,
}

UNIFORM_STRATA = {STRATUM_ORDINARY, STRATUM_INTER_MODEL, STRATUM_GOVERNED}


def recipe_to_stratum(recipe: str) -> str:
    if recipe not in RECIPE_TO_STRATUM:
        raise ValueError(f"unknown document_recipe_version {recipe!r}")
    return RECIPE_TO_STRATUM[recipe]


def resolve_relevant_recipes(
    relevant: list[dict[str, Any]],
    package_by_key: dict[str, dict],
) -> list[str]:
    """Resolve document_recipe_version for each relevant item.

    package_by_key keys are 'ledger_id:<id>' and/or 'unit_id:<id>'.
    Missing/ambiguous resolution fails closed (raises).
    """
    recipes: list[str] = []
    for item in relevant:
        ns = str(item.get("namespace") or "ledger_id")
        rid = str(item.get("id") or "")
        if not rid:
            raise ValueError("relevant item missing id")
        key = f"{ns}:{rid}"
        unit = package_by_key.get(key)
        if unit is None and ns == "ledger_id":
            # try unit_id fallback only if unique match by ledger_id field
            matches = [
                u
                for k, u in package_by_key.items()
                if k.startswith("unit_id:")
                and str(u.get("ledger_id") or "") == rid
            ]
            if len(matches) == 1:
                unit = matches[0]
            elif len(matches) > 1:
                raise ValueError(f"ambiguous relevant resolution for {key}")
        if unit is None:
            raise ValueError(f"missing relevant-unit resolution for {key}")
        recipe = str(unit.get("document_recipe_version") or "")
        if not recipe:
            raise ValueError(f"unit {key} missing document_recipe_version")
        recipes.append(recipe)
    return recipes


def validate_recipe_stratum(
    declared: str,
    resolved_recipes: list[str],
) -> dict[str, Any]:
    """Validate declared stratum against resolved recipes; fail closed on disagreement."""
    declared = str(declared or "")
    if declared not in UNIFORM_STRATA | {STRATUM_MIXED}:
        raise ValueError(f"invalid recipe_stratum {declared!r}")
    if not resolved_recipes:
        raise ValueError("no resolved recipes for stratum validation")
    strata = {recipe_to_stratum(r) for r in resolved_recipes}
    if declared in UNIFORM_STRATA:
        if strata != {declared}:
            raise ValueError(
                f"recipe_stratum {declared!r} disagrees with resolved {sorted(strata)}"
            )
    elif declared == STRATUM_MIXED:
        if len(strata) < 2:
            raise ValueError(
                f"recipe_stratum mixed requires >=2 distinct recipes; got {sorted(strata)}"
            )
    return {
        "declared": declared,
        "resolved_recipes": list(resolved_recipes),
        "resolved_strata": sorted(strata),
        "ok": True,
    }


def index_package_units(units: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for u in units:
        uid = str(u.get("id") or "")
        if uid:
            out[f"unit_id:{uid}"] = u
        lid = str(u.get("ledger_id") or "")
        if lid:
            out[f"ledger_id:{lid}"] = u
    return out


def stratum_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in rows:
        c[str(r.get("recipe_stratum") or "")] += 1
    return dict(c)
