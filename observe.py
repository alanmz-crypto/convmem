"""Direct observation ingestion — knowledge units from tools, not chat transcripts."""

from __future__ import annotations

import json
from pathlib import Path

from ledger import build_ledger_index, ledger_unit_metadata, normalize_ledger_record


def _upsert_jsonl_line(
    units_export: Path,
    ledger_id: str,
    unit: dict,
) -> None:
    """Replace the line in units_export matching ledger_id, or append if not found."""
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
    from llm import ollama_embed

    unit = normalize_ledger_record(record, min_confidence=min_confidence)
    if unit is None:
        return None

    doc = unit["summary"] + " " + " ".join(unit["keywords"])
    rationale = unit.get("rationale") or ""
    if rationale:
        doc = doc + " Rationale: " + rationale
    embedding = ollama_embed(doc, model=embed_model, host=ollama_host)
    meta = ledger_unit_metadata(unit)
    lid = (unit.get("ledger_id") or "").strip()

    if upsert and lid:
        if by_ledger_id is None:
            by_ledger_id, _ = build_ledger_index(store)
        existing = by_ledger_id.get(lid)
        if existing:
            chroma_id = existing["id"]
            store.update_unit(chroma_id, doc, embedding, meta)
            unit["id"] = chroma_id
            unit["_upserted"] = True
            if units_export:
                _upsert_jsonl_line(units_export, lid, unit)
            return unit

    store.add_unit(unit["id"], doc, embedding, meta)

    if units_export:
        units_export.parent.mkdir(parents=True, exist_ok=True)
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
    stats = {"accepted": 0, "rejected": 0, "updated": 0}
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
