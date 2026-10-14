"""Direct observation ingestion — knowledge units from tools, not chat transcripts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from atomic_files import atomic_write_text
from ledger import build_ledger_index, ledger_unit_document, ledger_unit_metadata, normalize_ledger_record


class ObservationIngestDriftError(Exception):
    """Prepared target changed or vanished before commit under C1."""

    def __init__(
        self, ledger_id: str, *, ledger_ids: set[str] | None = None
    ) -> None:
        self.ledger_id = ledger_id
        self.ledger_ids = ledger_ids or {ledger_id}
        super().__init__(
            f"observation ingest drift for {', '.join(sorted(self.ledger_ids))}"
        )


class ObservationIngestDriftRefusedError(Exception):
    """Drift persisted after the allowed re-prepare round."""


_READER_ONLY_TARGET_METADATA_KEYS = frozenset({"document"})


def _canonical_observation_target(unit_row: dict | None) -> dict | None:
    """Document text plus durable metadata, independent of store representation."""
    if unit_row is None:
        return None
    doc = (unit_row.get("document") or "").strip()
    meta = dict(unit_row.get("metadata") or {})
    for key in _READER_ONLY_TARGET_METADATA_KEYS:
        meta.pop(key, None)
    return {"document": doc, "metadata": meta}


def _observation_target_digest(unit_row: dict | None) -> str:
    if unit_row is None:
        return "missing"
    payload = _canonical_observation_target(unit_row)
    assert payload is not None
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _prepared_observation_drifted(
    prepared: PreparedObservationIngest,
    *,
    store,
    by_ledger_id: dict[str, dict],
) -> bool:
    unit = prepared.unit
    lid = (unit.get("ledger_id") or "").strip()

    if prepared.skipped_unchanged or prepared.upsert_update:
        chroma_id, row = _lookup_target_row(store, lid)
        current_digest = _observation_target_digest(row)
        if prepared.skipped_unchanged:
            return row is None or current_digest != prepared.target_digest
        if row is None or chroma_id != prepared.existing_chroma_id:
            return True
        return current_digest != prepared.target_digest

    if prepared.target_digest == "missing":
        return bool(lid and lid in by_ledger_id)
    return False


def _fresh_readonly_embed_store(embed_store):
    chroma_dir = getattr(embed_store, "chroma_dir", None)
    if chroma_dir is None:
        return embed_store
    from chroma_readonly import open_readonly_unit_store
    from ledger import invalidate_ledger_index_cache

    invalidate_ledger_index_cache(chroma_dir)
    return open_readonly_unit_store(chroma_dir)


def _lookup_target_row(store, ledger_id: str) -> tuple[str | None, dict | None]:
    by_ledger_id, _ = build_ledger_index(store)
    existing = by_ledger_id.get(ledger_id)
    if not existing:
        return None, None
    chroma_id = str(existing.get("id") or "")
    row = store.get_unit(chroma_id) if chroma_id else None
    return chroma_id or None, row


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
    from purge_locks import export_flock_path

    with export_flock_path(units_export):
        units_export.parent.mkdir(parents=True, exist_ok=True)
        if not units_export.exists():
            atomic_write_text(units_export, json.dumps(unit) + "\n")
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

        atomic_write_text(units_export, "".join(lines))


def normalize_observation(raw: dict, *, min_confidence: float = 0.0) -> dict | None:
    """Validate a ledger JSONL record (observation, decision, or verification)."""
    return normalize_ledger_record(raw, min_confidence=min_confidence)


def ledger_record_document_text(
    record: dict, *, min_confidence: float = 0.0
) -> str | None:
    """Normalized document text exactly as stored by ``ingest_observation``."""
    unit = normalize_ledger_record(record, min_confidence=min_confidence)
    if unit is None:
        return None
    return ledger_unit_document(unit)


def embed_ledger_record_for_storage(
    record: dict,
    *,
    store,
    embed_model: str,
    ollama_host: str,
    min_confidence: float = 0.0,
    by_ledger_id: dict[str, dict] | None = None,
    upsert: bool = False,
) -> list[float] | None:
    """Embed the stored document text; return None when the row is unchanged."""
    unit = normalize_ledger_record(record, min_confidence=min_confidence)
    if unit is None:
        return None
    doc = ledger_unit_document(unit)
    lid = (unit.get("ledger_id") or "").strip()
    if upsert and lid:
        if by_ledger_id is None:
            by_ledger_id, _ = build_ledger_index(store)
        existing = by_ledger_id.get(lid)
        if existing and _ledger_unchanged_in_index(existing, unit, store):
            return None
    from llm import ollama_embed

    return ollama_embed(doc, model=embed_model, host=ollama_host)


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


@dataclass
class PreparedObservationIngest:
    """Validated unit plus embedding computed before the index write lock."""

    record: dict
    unit: dict
    doc: str
    embedding: list[float]
    upsert: bool
    existing_chroma_id: str | None = None
    skipped_unchanged: bool = False
    upsert_update: bool = False
    target_digest: str = "missing"


def prepare_observation_ingest(
    record: dict,
    *,
    store,
    embed_model: str,
    ollama_host: str,
    min_confidence: float = 0.0,
    upsert: bool = False,
    by_ledger_id: dict[str, dict] | None = None,
    precomputed_embedding: list[float] | None = None,
) -> PreparedObservationIngest | None:
    """Validate and embed one ledger record without opening a write session."""
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
            chroma_id = existing["id"]
            target_row = store.get_unit(chroma_id)
            target_digest = _observation_target_digest(target_row)
            if _ledger_unchanged_in_index(existing, unit, store):
                unit["id"] = chroma_id
                return PreparedObservationIngest(
                    record=record,
                    unit=unit,
                    doc=doc,
                    embedding=precomputed_embedding or [],
                    upsert=upsert,
                    existing_chroma_id=chroma_id,
                    skipped_unchanged=True,
                    target_digest=target_digest,
                )
            if precomputed_embedding is None:
                from llm import ollama_embed

                embedding = ollama_embed(doc, model=embed_model, host=ollama_host)
            else:
                embedding = precomputed_embedding
            return PreparedObservationIngest(
                record=record,
                unit=unit,
                doc=doc,
                embedding=embedding,
                upsert=upsert,
                existing_chroma_id=chroma_id,
                upsert_update=True,
                target_digest=target_digest,
            )

    if precomputed_embedding is None:
        from llm import ollama_embed

        embedding = ollama_embed(doc, model=embed_model, host=ollama_host)
    else:
        embedding = precomputed_embedding
    return PreparedObservationIngest(
        record=record,
        unit=unit,
        doc=doc,
        embedding=embedding,
        upsert=upsert,
        target_digest="missing",
    )


def commit_observation_ingest(
    prepared: PreparedObservationIngest,
    *,
    store,
    units_export: Path | None = None,
) -> dict | None:
    """Persist a prepared observation under an open write store."""
    from ledger import invalidate_ledger_index_cache

    unit = prepared.unit
    lid = (unit.get("ledger_id") or "").strip()
    chroma_dir = getattr(store, "chroma_dir", None)
    if chroma_dir:
        invalidate_ledger_index_cache(chroma_dir)
    by_ledger_id, _ = build_ledger_index(store)
    if _prepared_observation_drifted(
        prepared, store=store, by_ledger_id=by_ledger_id
    ):
        raise ObservationIngestDriftError(lid or str(unit.get("id") or ""))

    if prepared.skipped_unchanged:
        chroma_id, _row = _lookup_target_row(store, lid)
        unit["id"] = chroma_id or prepared.existing_chroma_id or unit.get("id")
        unit["_skipped"] = True
        return unit

    if prepared.upsert_update and prepared.existing_chroma_id:
        meta = ledger_unit_metadata(unit)
        chroma_id = prepared.existing_chroma_id
        store.update_unit(chroma_id, prepared.doc, prepared.embedding, meta)
        if store.get_unit(chroma_id) is None:
            raise ObservationIngestDriftError(lid)
        unit["id"] = chroma_id
        unit["_upserted"] = True
        if units_export and lid:
            _upsert_jsonl_line(units_export, lid, unit)
        return unit

    meta = ledger_unit_metadata(unit)
    store.add_unit(unit["id"], prepared.doc, prepared.embedding, meta)

    if units_export and prepared.upsert and lid:
        _upsert_jsonl_line(units_export, lid, unit)
    elif units_export:
        from purge_locks import export_flock_path

        units_export.parent.mkdir(parents=True, exist_ok=True)
        with export_flock_path(units_export):
            line = json.dumps(unit) + "\n"
            if units_export.exists():
                atomic_write_text(units_export, units_export.read_text(encoding="utf-8") + line)
            else:
                atomic_write_text(units_export, line)

    return unit


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
    precomputed_embedding: list[float] | None = None,
) -> dict | None:
    """Validate, embed, and store one ledger record. Returns the stored unit or None."""
    prepared = prepare_observation_ingest(
        record,
        store=store,
        embed_model=embed_model,
        ollama_host=ollama_host,
        min_confidence=min_confidence,
        upsert=upsert,
        by_ledger_id=by_ledger_id,
        precomputed_embedding=precomputed_embedding,
    )
    if prepared is None:
        return None
    return commit_observation_ingest(prepared, store=store, units_export=units_export)


def prepare_observation_file_rows(
    path: str,
    *,
    embed_store,
    embed_model: str,
    ollama_host: str,
    min_confidence: float = 0.0,
    upsert: bool = False,
    verbose: bool = True,
) -> tuple[list[tuple[int, PreparedObservationIngest | None]], dict]:
    """Parse a JSONL file and prepare commits (no write lock required)."""
    stats = {"accepted": 0, "rejected": 0, "updated": 0, "skipped": 0}
    by_ledger_id: dict[str, dict] | None = None
    if upsert:
        by_ledger_id, _ = build_ledger_index(embed_store)

    prepared: list[tuple[int, PreparedObservationIngest | None]] = []
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
            embedding = embed_ledger_record_for_storage(
                record,
                store=embed_store,
                embed_model=embed_model,
                ollama_host=ollama_host,
                min_confidence=min_confidence,
                by_ledger_id=by_ledger_id,
                upsert=upsert,
            )
            prep = prepare_observation_ingest(
                record,
                store=embed_store,
                embed_model=embed_model,
                ollama_host=ollama_host,
                min_confidence=min_confidence,
                upsert=upsert,
                by_ledger_id=by_ledger_id,
                precomputed_embedding=embedding if embedding is not None else [],
            )
            prepared.append((line_no, prep))
    return prepared, stats


def _stats_from_committed_unit(
    unit: dict,
    stats: dict,
    *,
    verbose: bool,
    by_ledger_id: dict[str, dict] | None,
) -> None:
    if unit.pop("_upserted", False):
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


def commit_prepared_observation_file_rows(
    prepared_rows: list[tuple[int, PreparedObservationIngest | None]],
    *,
    store,
    units_export: Path | None = None,
    verbose: bool = True,
    upsert: bool = False,
    by_ledger_id: dict[str, dict] | None = None,
) -> dict:
    """Commit prepared rows without re-embedding under the write lock."""
    from ledger import invalidate_ledger_index_cache

    stats = {"accepted": 0, "rejected": 0, "updated": 0, "skipped": 0}
    chroma_dir = getattr(store, "chroma_dir", None)
    if chroma_dir:
        invalidate_ledger_index_cache(chroma_dir)
    by_ledger_id, _ = build_ledger_index(store)
    drift_ids: set[str] = set()
    for _line_no, prepared in prepared_rows:
        if prepared is None:
            continue
        lid = (prepared.unit.get("ledger_id") or "").strip()
        if _prepared_observation_drifted(
            prepared, store=store, by_ledger_id=by_ledger_id
        ):
            drift_ids.add(lid or str(prepared.unit.get("id") or ""))
    if drift_ids:
        raise ObservationIngestDriftError(
            next(iter(drift_ids)), ledger_ids=drift_ids
        )
    for line_no, prepared in prepared_rows:
        if prepared is None:
            stats["rejected"] += 1
            if verbose:
                print(f"  [skip] line {line_no}: rejected (missing/invalid fields)")
            continue
        try:
            unit = commit_observation_ingest(
                prepared, store=store, units_export=units_export
            )
        except ObservationIngestDriftError:
            raise
        if unit is None:
            stats["rejected"] += 1
            if verbose:
                print(f"  [skip] line {line_no}: rejected (missing/invalid fields)")
            continue
        _stats_from_committed_unit(
            unit, stats, verbose=verbose, by_ledger_id=by_ledger_id
        )
    return stats


def reprepare_observation_file_rows(
    path: str,
    prepared_rows: list[tuple[int, PreparedObservationIngest | None]],
    *,
    drift_ledger_ids: set[str],
    embed_store,
    embed_model: str,
    ollama_host: str,
    min_confidence: float = 0.0,
    upsert: bool = False,
) -> list[tuple[int, PreparedObservationIngest | None]]:
    """Re-prepare only rows that drifted (outside C1)."""
    by_ledger_id: dict[str, dict] | None = None
    if upsert:
        by_ledger_id, _ = build_ledger_index(embed_store)
    records_by_line: dict[int, dict] = {}
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records_by_line[line_no] = json.loads(line)
            except json.JSONDecodeError:
                continue
    refreshed: list[tuple[int, PreparedObservationIngest | None]] = []
    for line_no, prepared in prepared_rows:
        if prepared is None:
            refreshed.append((line_no, None))
            continue
        lid = (prepared.unit.get("ledger_id") or "").strip()
        if lid not in drift_ledger_ids:
            refreshed.append((line_no, prepared))
            continue
        record = records_by_line.get(line_no) or prepared.record
        embedding = embed_ledger_record_for_storage(
            record,
            store=embed_store,
            embed_model=embed_model,
            ollama_host=ollama_host,
            min_confidence=min_confidence,
            by_ledger_id=by_ledger_id,
            upsert=upsert,
        )
        refreshed.append(
            (
                line_no,
                prepare_observation_ingest(
                    record,
                    store=embed_store,
                    embed_model=embed_model,
                    ollama_host=ollama_host,
                    min_confidence=min_confidence,
                    upsert=upsert,
                    by_ledger_id=by_ledger_id,
                    precomputed_embedding=embedding if embedding is not None else [],
                ),
            )
        )
    return refreshed


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
    embedding_store=None,
    prepared_rows: list[tuple[int, PreparedObservationIngest | None]] | None = None,
) -> dict:
    """Ingest a JSONL file of ledger records. Returns counts."""
    embed_index_store = embedding_store if embedding_store is not None else store
    if prepared_rows is None:
        prepared_rows, prep_stats = prepare_observation_file_rows(
            path,
            embed_store=embed_index_store,
            embed_model=embed_model,
            ollama_host=ollama_host,
            min_confidence=min_confidence,
            upsert=upsert,
            verbose=verbose,
        )
    else:
        prep_stats = {"rejected": 0}
    stats = commit_prepared_observation_file_rows(
        prepared_rows,
        store=store,
        units_export=units_export,
        verbose=verbose,
        upsert=upsert,
        by_ledger_id=None if embedding_store is not None else None,
    )
    stats["rejected"] += prep_stats["rejected"]
    return stats


def ingest_observation_file_with_drift_retry(
    path: str,
    *,
    embed_store,
    open_write_commit,
    embed_model: str,
    ollama_host: str,
    min_confidence: float = 0.0,
    upsert: bool = False,
    verbose: bool = True,
    prepared_rows: list[tuple[int, PreparedObservationIngest | None]] | None = None,
) -> dict:
    """Prepare outside C1; commit with at most one drift re-prepare round."""

    if prepared_rows is None:
        prepared_rows, prep_stats = prepare_observation_file_rows(
            path,
            embed_store=embed_store,
            embed_model=embed_model,
            ollama_host=ollama_host,
            min_confidence=min_confidence,
            upsert=upsert,
            verbose=verbose,
        )
    else:
        prep_stats = {"rejected": 0}
    last_drift: ObservationIngestDriftError | None = None
    for attempt in range(2):
        try:
            stats = open_write_commit(
                lambda store, units_export: commit_prepared_observation_file_rows(
                    prepared_rows,
                    store=store,
                    units_export=units_export,
                    verbose=verbose,
                    upsert=upsert,
                )
            )
            stats["rejected"] += prep_stats["rejected"]
            return stats
        except ObservationIngestDriftError as drift:
            last_drift = drift
            if attempt == 1:
                raise ObservationIngestDriftRefusedError(str(drift)) from drift
            prepared_rows = reprepare_observation_file_rows(
                path,
                prepared_rows,
                drift_ledger_ids=set(drift.ledger_ids),
                embed_store=_fresh_readonly_embed_store(embed_store),
                embed_model=embed_model,
                ollama_host=ollama_host,
                min_confidence=min_confidence,
                upsert=upsert,
            )
    raise ObservationIngestDriftRefusedError(str(last_drift or "drift"))


def repair_empty_ledger_documents(
    cfg: dict,
    *,
    dry_run: bool = False,
    limit: int = 0,
    verbose: bool = True,
) -> dict:
    """Re-embed ledger units whose Chroma document is empty (decision/verification)."""
    from chroma_write_store import open_production_write_store
    from ledger import invalidate_ledger_index_cache
    from ledger_recent import load_approved_decision_by_id
    from purge_locks import index_write_flock

    lock_cfg = cfg if cfg.get("index") else None
    if lock_cfg is None:
        from config import load_config

        lock_cfg = load_config()
    from chroma_readonly import open_readonly_unit_store

    reader = open_readonly_unit_store(lock_cfg["index"]["chroma_dir"])
    by_ledger_id, _ = build_ledger_index(reader)
    models = lock_cfg["models"]
    pending: list[PreparedObservationIngest] = []
    stats = {"scanned": 0, "empty": 0, "repaired": 0, "skipped": 0, "missing_source": 0}
    for lid, meta in by_ledger_id.items():
        kind = (meta.get("ledger_kind") or "").strip()
        if kind not in ("decision", "verification"):
            continue
        stats["scanned"] += 1
        row = reader.get_unit(meta["id"])
        if row is None or (row.get("document") or "").strip():
            continue
        stats["empty"] += 1
        rec = load_approved_decision_by_id(lock_cfg, lid)
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
        repair_rec = {
            **rec,
            "_governed_protocol": True,
            "proposal_id": (
                rec.get("proposal_id")
                or meta.get("proposal_id")
                or f"repair:{lid}"
            ),
        }
        prepared = prepare_observation_ingest(
            repair_rec,
            store=reader,
            embed_model=models["embed_model"],
            ollama_host=models["ollama_host"],
            upsert=True,
            by_ledger_id=by_ledger_id,
        )
        if prepared is None:
            stats["missing_source"] += 1
            continue
        pending.append(prepared)
        if limit and len(pending) >= limit:
            break

    chroma_dir = lock_cfg["index"]["chroma_dir"]
    for prepared in pending:
        current = prepared
        unit = None
        drift_skip = False
        for attempt in range(2):
            try:
                with index_write_flock(lock_cfg):
                    _pw = open_production_write_store(
                        entrypoint="observe.repair_empty_ledger_documents"
                    )
                    store = _pw.store
                    try:
                        unit = commit_observation_ingest(current, store=store)
                    finally:
                        store.close()
                break
            except ObservationIngestDriftError:
                if attempt == 1:
                    stats["skipped"] += 1
                    drift_skip = True
                    unit = None
                    break
                invalidate_ledger_index_cache(chroma_dir)
                fresh_reader = open_readonly_unit_store(chroma_dir)
                by_ledger_id, _ = build_ledger_index(fresh_reader)
                current = prepare_observation_ingest(
                    current.record,
                    store=fresh_reader,
                    embed_model=models["embed_model"],
                    ollama_host=models["ollama_host"],
                    upsert=True,
                    by_ledger_id=by_ledger_id,
                )
                if current is None:
                    unit = None
                    break
        if drift_skip:
            continue
        if unit is None:
            stats["missing_source"] += 1
        elif unit.pop("_skipped", False):
            stats["skipped"] += 1
        elif unit.pop("_upserted", False) or unit:
            stats["repaired"] += 1
            if verbose:
                lid = (unit.get("ledger_id") or "").strip()
                print(f"  [repair] {lid}")
    invalidate_ledger_index_cache(chroma_dir)
    return stats
