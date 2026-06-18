"""Evidence-aware retrieval boosts for ask/search (Milestone E).

Re-ranks semantic hits using the ledger graph: prefer unresolved observations,
failed verifications; deprioritize resolved/passed items. Display dedupe and
ingest upsert remain separate concerns.
"""

from __future__ import annotations

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


def apply_evidence_rerank(
    results: list[dict],
    store,
) -> list[dict]:
    """Re-order retrieval hits by semantic score + evidence graph boosts."""
    if not results:
        return results

    _, by_relates_to = build_ledger_index(store)
    scored: list[tuple[float, int, dict]] = []

    for i, r in enumerate(results):
        meta = r.get("metadata") or {}
        base = r.get("score")
        if base is None:
            base = 0.0
        boost, status = evidence_boost(meta, by_relates_to=by_relates_to)
        out = dict(r)
        out["evidence_boost"] = round(boost, 4)
        out["evidence_status"] = status
        out["rank_score"] = round(base + boost, 4)
        scored.append((out["rank_score"], i, out))

    scored.sort(key=lambda t: (-t[0], t[1]))
    return [r for _, _, r in scored]
