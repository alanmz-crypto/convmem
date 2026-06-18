"""Verification — attach a verifier's opinion to an existing unit."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ledger import resolve_unit_ref


def verify_unit(
    store,
    unit_ref: str,
    *,
    verifier_model: str,
    confidence: float | None = None,
    notes: str | None = None,
    result: str = "pass",
    record_ledger: bool = True,
    embed_model: str | None = None,
    ollama_host: str | None = None,
    units_export=None,
) -> dict | None:
    """Attach a verifier's opinion. `unit_ref` may be chroma id or ledger id.

    When `record_ledger` is True (default), also ingests a verification ledger
    record linked via `relates_to` — the evidence-chain path for Workflow #1.
    """
    existing = resolve_unit_ref(store, unit_ref)
    if existing is None:
        return None

    meta = dict(existing["metadata"])
    verified_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if confidence is not None:
        meta["verified_confidence"] = float(confidence)
    else:
        meta["verified_confidence"] = meta.get(
            "verified_confidence", meta.get("confidence", 0.0)
        )
    meta["verifier_model"] = verifier_model
    meta["verified_at"] = verified_at
    if notes:
        meta["notes"] = notes
    meta["verification_result"] = result.strip().lower()

    store.update_unit_metadata(meta["id"], meta)

    if record_ledger and embed_model and ollama_host:
        from observe import ingest_observation

        relates_to = meta.get("ledger_id") or unit_ref
        title = meta.get("title") or relates_to
        summary = notes or f"Verified {title}: {result}"
        verification = {
            "id": f"ver_{uuid.uuid4().hex[:12]}",
            "kind": "verification",
            "author_model": verifier_model,
            "relates_to": relates_to,
            "result": result,
            "summary": summary,
            "notes": notes or "",
            "domain": meta.get("domain") or "web_stack.security",
            "site": meta.get("site") or "",
            "confidence": meta["verified_confidence"],
            "timestamp": verified_at,
        }
        ingest_observation(
            verification,
            store=store,
            embed_model=embed_model,
            ollama_host=ollama_host,
            units_export=units_export,
        )

    return meta
