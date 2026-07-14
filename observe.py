"""Direct observation ingestion — knowledge units from tools, not chat transcripts."""

from __future__ import annotations

import json
from pathlib import Path

from ledger import build_ledger_index, ledger_unit_document, ledger_unit_metadata, normalize_ledger_record


def _reject_governed_bypass(record: dict, *, upsert: bool) -> None:
    """Only the approval protocol may replace an existing governed decision."""
    if not upsert:
        return
    ledger_id = str(record.get("id") or record.get("ledger_id") or "")
    if ledger_id.startswith("dec_") and not (str(record.get("proposal_id") or "").strip() or record.get("_governed_protocol")):
        raise ValueError("governed decision upsert requires proposal_id from approval protocol")


def _upsert_jsonl_line(
    units_export: Path,
    ledger_id: str,
    unit: dict,
) -> None:
    """Replace the line in units_export matching ledger_id, or append if not found."""
    from source_purge import export_flock_path

    with export_flock_path(units_export):
        if not units_export.exists():
            units_export.parent.mkdir(parents=True, exist_ok=True)
            with open(units_export, "a", encoding="utf-8") as f:
                f.write(json.dumps(unit) + "\n")
            return

        lines: list[str] = []
        found = False
        with open(units_export, encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    lines.append(raw_line)  # preserve blank lines
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    lines.append(raw_line)
                    continue
                if (rec.get("ledger_id") or "").strip() == ledger_id:
                    lines.append(json.dumps(unit) + "\n")
                    found = True
                else:
                    lines.append(raw_line)

        if not found:
            lines.append(json.dumps(unit) + "\n")

        with open(units_export, "w", encoding="utf-8") as f:
            f.writelines(lines)


def normalize_observation(raw: dict, *, min_confidence: float = 0.0) -> dict | None:
    """Validate a ledger JSONL record (observation, decision, or verification)."""
    return normalize_ledger_record(raw, min_confidence=min_confidence)


def _ledger_unchanged_in_index(existing: dict, unit: dict, store) -> bool:
    """True when Chroma already has this ledger row with the same durable text."""
    existing_unit = store.get_unit(existing["id"])
    if existing_unit is None:
        return False
    existing_doc = (existing_unit.get("document") or "").strip()
    if not existing_doc:
        return False
    if existing_doc != ledger_unit_document(unit):
        return False
    return (
        (existing.get("title") or "") == (unit.get("title") or "")
        and (existing.get("rationale") or "") == (unit.get("rationale") or "")
        and (existing.get("relates_to") or "") == (unit.get("relates_to") or "")
    )


def ingest_observation(
    record: dict,
    *,
    store,
    embed_model: str,
    ollama_host: str,
    min_confidence: float = 0.0,
    units_export: Path | None = None,
    upsert: bool = False,
    by_ledger_id: dict[str, dict] | None = None,
) -> dict | None:
    """Validate, embed, and store one ledger record. Returns the stored unit or None."""
    _reject_governed_bypass(record, upsert=upsert)
    unit = normalize_ledger_record(record, min_confidence=min_confidence)
    if unit is None:
        return None

    doc = ledger_unit_document(unit)
    lid = (unit.get("ledger_id") or "").strip()

    if upsert and lid:
        if by_ledger_id is None:
            by_ledger_id, _ = build_ledger_index(store)
        existing = by_ledger_id.get(lid)
        if existing:
            if _ledger_unchanged_in_index(existing, unit, store):
                unit["id"] = existing["id"]
                unit["_skipped"] = True
                return unit
            from llm import ollama_embed

            embedding = ollama_embed(doc, model=embed_model, host=ollama_host)
            meta = ledger_unit_metadata(unit)
            chroma_id = existing["id"]
            store.update_unit(chroma_id, doc, embedding, meta)
            unit["id"] = chroma_id
            unit["_upserted"] = True
            if units_export:
                _upsert_jsonl_line(units_export, lid, unit)
            return unit

    from llm import ollama_embed

    embedding = ollama_embed(doc, model=embed_model, host=ollama_host)
    meta = ledger_unit_metadata(unit)

    store.add_unit(unit["id"], doc, embedding, meta)

    if units_export:
        from source_purge import export_flock_path

        units_export.parent.mkdir(parents=True, exist_ok=True)
        with export_flock_path(units_export):
            with open(units_export, "a", encoding="utf-8") as uf:
                uf.write(json.dumps(unit) + "\n")

    return unit


def ingest_observation_file(
    path: str,
    *,
    store,
    embed_model: str,
    ollama_host: str,
    min_confidence: float = 0.0,
    units_export: Path | None = None,
    verbose: bool = True,
    upsert: bool = False,
) -> dict:
    """Ingest a JSONL file of ledger records. Returns counts."""
    stats = {"accepted": 0, "rejected": 0, "updated": 0, "skipped": 0}
    by_ledger_id: dict[str, dict] | None = None
    if upsert:
        by_ledger_id, _ = build_ledger_index(store)

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                stats["rejected"] += 1
                if verbose:
                    print(f"  [skip] line {line_no}: invalid JSON ({e})")
                continue
            unit = ingest_observation(
                record,
                store=store,
                embed_model=embed_model,
                ollama_host=ollama_host,
                min_confidence=min_confidence,
                units_export=units_export,
                upsert=upsert,
                by_ledger_id=by_ledger_id,
            )
            if unit is None:
                stats["rejected"] += 1
                if verbose:
                    print(f"  [skip] line {line_no}: rejected (missing/invalid fields)")
            elif unit.pop("_upserted", False):
                stats["updated"] += 1
                if verbose:
                    lid = unit.get("ledger_id", unit["id"][:8])
                    print(
                        f"  [upd] {unit['ledger_kind']:<14} {unit['domain']:<28} "
                        f"{lid}  {unit['title'][:50]}"
                    )
            elif unit.pop("_skipped", False):
                stats["skipped"] += 1
                if verbose:
                    lid = unit.get("ledger_id", unit["id"][:8])
                    print(f"  [skip] unchanged {lid}")
            else:
                stats["accepted"] += 1
                if by_ledger_id is not None:
                    lid = (unit.get("ledger_id") or "").strip()
                    if lid:
                        row = ledger_unit_metadata(unit)
                        row["id"] = unit["id"]
                        by_ledger_id[lid] = row
                if verbose:
                    lid = unit.get("ledger_id", unit["id"][:8])
                    print(
                        f"  [add] {unit['ledger_kind']:<14} {unit['domain']:<28} "
                        f"{lid}  {unit['title'][:50]}"
                    )
    return stats


def repair_empty_ledger_documents(
    cfg: dict,
    *,
    dry_run: bool = False,
    limit: int = 0,
    verbose: bool = True,
) -> dict:
    """Re-embed ledger units whose Chroma document is empty (decision/verification)."""
    from chroma_store import ChromaStore
    from config import load_config
    from ledger import invalidate_ledger_index_cache
    from ledger_recent import load_approved_decision_by_id

    if not cfg:
        cfg = load_config()
    models = cfg["models"]
    store = ChromaStore(cfg["index"]["chroma_dir"])
    by_ledger_id, _ = build_ledger_index(store)
    stats = {"scanned": 0, "empty": 0, "repaired": 0, "skipped": 0, "missing_source": 0}

    try:
        for lid, meta in by_ledger_id.items():
            kind = (meta.get("ledger_kind") or "").strip()
            if kind not in ("decision", "verification"):
                continue
            stats["scanned"] += 1
            row = store.get_unit(meta["id"])
            if row is None or (row.get("document") or "").strip():
                continue
            stats["empty"] += 1
            rec = load_approved_decision_by_id(cfg, lid)
            if rec is None:
                stats["missing_source"] += 1
                if verbose:
                    print(f"  [miss] no approved row for {lid}")
                continue
            if dry_run:
                stats["repaired"] += 1
                if verbose:
                    print(f"  [dry-run] would repair {lid}")
                continue
            # Document repair is not a semantic replace; mark protocol-safe.
            repair_rec = {
                **rec,
                "_governed_protocol": True,
                "proposal_id": (
                    rec.get("proposal_id")
                    or meta.get("proposal_id")
                    or f"repair:{lid}"
                ),
            }
            unit = ingest_observation(
                repair_rec,
                store=store,
                embed_model=models["embed_model"],
                ollama_host=models["ollama_host"],
                upsert=True,
                by_ledger_id=by_ledger_id,
            )
            if unit is None:
                stats["missing_source"] += 1
            elif unit.pop("_skipped", False):
                stats["skipped"] += 1
            elif unit.pop("_upserted", False) or unit:
                stats["repaired"] += 1
                if verbose:
                    print(f"  [repair] {lid}")
            if limit and stats["repaired"] >= limit:
                break
    finally:
        store.close()
    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    return stats
