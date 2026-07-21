"""Cheap post-filters shared by query_units (search) and ask."""

from __future__ import annotations


def filter_superseded_decisions(results: list[dict]) -> list[dict]:
    """Drop parent decisions when a newer decision in results relates_to them.

    Shared by ``query_units`` (search_fast / CLI search) and ask. Cheap in-list
    filter — not a Chroma unit-tombstone check.
    """
    parent_ids: set[str] = set()
    for r in results:
        meta = r.get("metadata") or {}
        if (meta.get("ledger_kind") or "").strip() != "decision":
            continue
        relates_to = (meta.get("relates_to") or "").strip()
        if relates_to.startswith("dec_"):
            parent_ids.add(relates_to)
    if not parent_ids:
        return results
    return [
        r
        for r in results
        if (r.get("metadata") or {}).get("ledger_id") not in parent_ids
    ]


def dedupe_results_by_ledger_id(results: list[dict]) -> list[dict]:
    """Keep one hit per ledger_id (first wins — list should already be rank-sorted)."""
    seen: set[str] = set()
    out: list[dict] = []
    for r in results:
        lid = ((r.get("metadata") or {}).get("ledger_id") or "").strip()
        if lid:
            if lid in seen:
                continue
            seen.add(lid)
        out.append(r)
    return out
