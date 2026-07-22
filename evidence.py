"""Evidence-aware retrieval boosts for ask/search (Milestone E).

Re-ranks semantic hits using the ledger graph: prefer unresolved observations,
failed verifications; deprioritize resolved/passed items. Also applies recency
time-decay (newer results rank slightly higher). Display dedupe and ingest
upsert remain separate concerns.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from ledger import _dedupe_by_ledger_id, _kind, build_ledger_index

# Additive boosts applied to semantic score (0–1 scale).
_BOOST_UNRESOLVED = 0.18
_BOOST_FAILED = 0.14
_BOOST_FAILED_VERIFICATION = 0.12
_PENALTY_RESOLVED = -0.10
_PENALTY_PASSED_VERIFICATION = -0.08
_BOOST_DECISION = 0.02


def evidence_boost(
    meta: dict,
    *,
    by_relates_to: dict[str, list[dict]],
) -> tuple[float, str]:
    """Return (score_adjustment, status_label) for a unit's metadata."""
    lid = (meta.get("ledger_id") or "").strip()
    if not lid:
        return 0.0, ""

    kind = _kind(meta)

    if kind == "verification":
        result = (
            meta.get("result")
            or meta.get("verification_result")
            or ""
        ).strip().lower()
        if result == "fail":
            return _BOOST_FAILED_VERIFICATION, "failed_verification"
        if result == "pass":
            return _PENALTY_PASSED_VERIFICATION, "passed_verification"
        return 0.0, "verification"

    if kind == "decision":
        return _BOOST_DECISION, "decision"

    if kind == "observation" or meta.get("type") == "observation":
        # Only penalize on explicit pass — verifier_model alone is set by
        # convmem verify regardless of outcome; child verifications handle the rest.
        if (meta.get("verification_result") or "").strip().lower() == "pass":
            return _PENALTY_RESOLVED, "resolved"

        children = _dedupe_by_ledger_id(by_relates_to.get(lid, []))
        verifications = [c for c in children if _kind(c) == "verification"]

        if not verifications:
            return _BOOST_UNRESOLVED, "unresolved"

        results = [
            (c.get("result") or c.get("verification_result") or "").strip().lower()
            for c in verifications
        ]
        if any(r == "fail" for r in results):
            return _BOOST_FAILED, "failed_check"
        if any(r == "pass" for r in results):
            return _PENALTY_RESOLVED, "resolved"
        return 0.04, "open"

    return 0.0, ""


def recency_boost(
    meta: dict,
    *,
    weight: float = 0.0,
    half_life_days: float = 30.0,
) -> float:
    """Time-decay boost: newer units get a small bump.

    boost = weight * exp(-age_days / half_life_days)

    Returns 0.0 if weight is 0 or no timestamp is available.
    """
    if weight <= 0:
        return 0.0

    ts = (meta.get("timestamp") or "").strip()
    if not ts:
        return 0.0

    try:
        if "T" in ts:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(ts[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 0.0

    age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    if age_days < 0:
        return 0.0

    return weight * math.exp(-age_days / half_life_days)


def apply_evidence_rerank(
    results: list[dict],
    store,
    *,
    recency_weight: float = 0.0,
    recency_half_life_days: float = 30.0,
) -> list[dict]:
    """Re-order retrieval hits by retrieval score + evidence graph boosts + recency.

    rank_score = rank_fusion_score + evidence_boost + recency_boost

    Older callers without a fused score fall back to the CrossEncoder score,
    then to the original semantic score.
    """
    if not results:
        return results

    _, by_relates_to = build_ledger_index(store)
    scored: list[tuple[float, int, dict]] = []

    for i, r in enumerate(results):
        meta = r.get("metadata") or {}
        base = r.get("rank_fusion_score")
        if base is None:
            base = r.get("rerank_score_norm")
        if base is None:
            base = r.get("score")
        if base is None:
            base = 0.0
        eboost, status = evidence_boost(meta, by_relates_to=by_relates_to)
        rboost = recency_boost(
            meta, weight=recency_weight, half_life_days=recency_half_life_days
        )
        out = dict(r)
        out["evidence_boost"] = round(eboost, 4)
        out["evidence_status"] = status
        out["recency_boost"] = round(rboost, 4)
        out["rank_score"] = round(base + eboost + rboost, 4)
        scored.append((out["rank_score"], i, out))

    scored.sort(key=lambda t: (-t[0], t[1]))
    return [r for _, _, r in scored]


def apply_recency_rerank(
    results: list[dict],
    *,
    recency_weight: float = 0.0,
    recency_half_life_days: float = 30.0,
) -> list[dict]:
    """Re-order retrieval hits by semantic score + recency_boost (search path).

    Lightweight alternative to apply_evidence_rerank — no ledger graph walk.
    """
    if not results or recency_weight <= 0:
        return results

    scored: list[tuple[float, int, dict]] = []
    for i, r in enumerate(results):
        meta = r.get("metadata") or {}
        base = r.get("score")
        if base is None:
            base = 0.0
        rboost = recency_boost(
            meta, weight=recency_weight, half_life_days=recency_half_life_days
        )
        out = dict(r)
        out["recency_boost"] = round(rboost, 4)
        out["rank_score"] = round(base + rboost, 4)
        scored.append((out["rank_score"], i, out))

    scored.sort(key=lambda t: (-t[0], t[1]))
    return [r for _, _, r in scored]


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


def apply_search_postfilters(results: list[dict]) -> list[dict]:
    """Decision-supersede filter then ledger-id dedupe (search/ask parity)."""
    return dedupe_results_by_ledger_id(filter_superseded_decisions(results))
