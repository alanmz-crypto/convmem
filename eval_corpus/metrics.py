"""Eval metrics with correct Hit@k vs Recall@k naming + namespaced relevance."""

from __future__ import annotations

from typing import Any


def expand_acceptable_ids(row: dict) -> list[dict[str, Any]]:
    """Normalize golden row to relevant[] with namespaces."""
    if row.get("relevant"):
        return list(row["relevant"])
    out: list[dict[str, Any]] = []
    for lid in row.get("acceptable_ids") or []:
        out.append({"namespace": "ledger_id", "id": str(lid), "grade": 1})
    return out


def resolve_hit_ids(
    ranked_hits: list[dict],
    relevant: list[dict[str, Any]],
) -> list[str]:
    """Map ranked query hits to comparable IDs using namespaces; dedupe."""
    # Build lookup from hit -> set of ids in each namespace
    resolved_relevant: set[str] = set()
    for item in relevant:
        ns = item.get("namespace") or "ledger_id"
        rid = str(item.get("id") or "")
        resolved_relevant.add(f"{ns}:{rid}")

    hit_keys: list[str] = []
    seen: set[str] = set()
    for h in ranked_hits:
        meta = h.get("metadata") or {}
        chroma_id = str(h.get("id") or meta.get("id") or "")
        ledger_id = str(meta.get("ledger_id") or "")
        keys = []
        if chroma_id:
            keys.append(f"unit_id:{chroma_id}")
        if ledger_id:
            keys.append(f"ledger_id:{ledger_id}")
        for k in keys:
            if k in resolved_relevant and k not in seen:
                seen.add(k)
                hit_keys.append(k)
                break
    return hit_keys


def first_relevant_rank(
    ranked_hits: list[dict],
    relevant: list[dict[str, Any]],
) -> int | None:
    want = {(r.get("namespace") or "ledger_id", str(r.get("id") or "")) for r in relevant}
    for i, h in enumerate(ranked_hits, 1):
        meta = h.get("metadata") or {}
        chroma_id = str(h.get("id") or meta.get("id") or "")
        ledger_id = str(meta.get("ledger_id") or "")
        if ("unit_id", chroma_id) in want or ("ledger_id", ledger_id) in want:
            return i
    return None


def hit_at_k(ranked_hits: list[dict], relevant: list[dict[str, Any]], k: int) -> bool:
    """Binary: any relevant ID appears in top-k."""
    rank = first_relevant_rank(ranked_hits[:k], relevant)
    return rank is not None


def recall_at_k(
    ranked_hits: list[dict],
    relevant: list[dict[str, Any]],
    k: int,
) -> float | None:
    """True recall when relevant set is complete; else None.

    Rows may set relevant_complete=true to enable Recall@k.
    """
    return None  # caller checks flag


def recall_at_k_complete(
    ranked_hits: list[dict],
    relevant: list[dict[str, Any]],
    k: int,
) -> float:
    if not relevant:
        return 0.0
    want = {(r.get("namespace") or "ledger_id", str(r.get("id") or "")) for r in relevant}
    found: set[tuple[str, str]] = set()
    for h in ranked_hits[:k]:
        meta = h.get("metadata") or {}
        chroma_id = str(h.get("id") or meta.get("id") or "")
        ledger_id = str(meta.get("ledger_id") or "")
        if ("unit_id", chroma_id) in want:
            found.add(("unit_id", chroma_id))
        if ("ledger_id", ledger_id) in want:
            found.add(("ledger_id", ledger_id))
    # Count unique relevant items retrieved (by their declared namespace+id)
    retrieved = 0
    for ns, rid in want:
        if (ns, rid) in found:
            retrieved += 1
    return retrieved / len(want)


def mrr(ranked_hits: list[dict], relevant: list[dict[str, Any]]) -> float:
    rank = first_relevant_rank(ranked_hits, relevant)
    if not rank:
        return 0.0
    return 1.0 / rank


def p_at_1(ranked_hits: list[dict], relevant: list[dict[str, Any]]) -> bool:
    return hit_at_k(ranked_hits, relevant, 1)


def dcg_at_k(grades: list[float], k: int) -> float:
    import math

    score = 0.0
    for i, g in enumerate(grades[:k], 1):
        score += (2**g - 1) / math.log2(i + 1)
    return score


def ndcg_at_k(
    ranked_hits: list[dict],
    relevant: list[dict[str, Any]],
    k: int,
) -> float:
    grade_map = {
        (r.get("namespace") or "ledger_id", str(r.get("id") or "")): float(r.get("grade") or 0)
        for r in relevant
    }
    gains: list[float] = []
    for h in ranked_hits[:k]:
        meta = h.get("metadata") or {}
        chroma_id = str(h.get("id") or meta.get("id") or "")
        ledger_id = str(meta.get("ledger_id") or "")
        g = 0.0
        if ("unit_id", chroma_id) in grade_map:
            g = max(g, grade_map[("unit_id", chroma_id)])
        if ("ledger_id", ledger_id) in grade_map:
            g = max(g, grade_map[("ledger_id", ledger_id)])
        gains.append(g)
    ideal = sorted(grade_map.values(), reverse=True)
    idcg = dcg_at_k(ideal, k)
    if idcg <= 0:
        return 0.0
    return dcg_at_k(gains, k) / idcg
