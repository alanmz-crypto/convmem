"""Pending decision queue — propose, list, approve, reject (no Chroma writes)."""
# pylint: disable=too-many-lines

from __future__ import annotations

import json
import os
import math
import re
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

PROPOSAL_KIND = "decision_proposal"
NO_CONSTRAINT_SENTINEL = "none-identified"
VALID_SIGNERS = frozenset({"ryan", "kiro-review"})
INTERACTIVE_LOCK_NAME = "propose_interactive.lock"


class InteractiveLockError(ValueError):
    """Another propose_decision -i session holds the lock."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def data_dir(cfg: dict) -> Path:
    return Path(cfg["index"]["chroma_dir"]).expanduser().parent


def queue_path(cfg: dict) -> Path:
    return data_dir(cfg) / "pending_decisions.jsonl"


def approved_path(cfg: dict) -> Path:
    return data_dir(cfg) / "decisions-approved.jsonl"


def is_valid_signer(signer: str) -> bool:
    s = signer.strip()
    return s in VALID_SIGNERS


def generate_proposal_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"dec_prop_{ts}_{secrets.token_hex(2)}"


def load_queue(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def save_queue(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )
    tmp.replace(path)


def append_approved(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def approved_for_proposal(cfg: dict, proposal_id: str) -> dict | None:
    """Find the durable approved intent by proposal id, never by ledger id alone."""
    path = approved_path(cfg)
    if not path.exists():
        return None
    for raw in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if row.get("proposal_id") == proposal_id:
            return row
    return None


_CONTENT_HASH_RE = re.compile(r"^[a-f0-9]{64}$")


def _valid_content_hash(value: str | None) -> bool:
    return bool(value and _CONTENT_HASH_RE.fullmatch(str(value).strip()))


def recovery_action(  # pylint: disable=too-many-arguments
    cfg: dict,
    proposal_id: str,
    *,
    live_marker: str = "",
    live_hash: str = "",
    base_hash: str = "",
    proposed_hash: str = "",
    live_absent: bool = False,
    live_read_failed: bool = False,
    intent_present: bool = True,
) -> str:
    """Classify recovery using strict inputs (tests and legacy callers)."""
    del cfg  # compat: callers pass config; classification uses explicit flat state only
    return classify_recovery_action(
        proposal_id=proposal_id,
        intent_present=intent_present,
        proposed_hash=proposed_hash,
        live_marker=live_marker,
        live_hash=live_hash if _valid_content_hash(live_hash) else "",
        live_absent=live_absent,
        live_read_failed=live_read_failed,
        base_hash=base_hash if _valid_content_hash(base_hash) else "",
    )


def classify_recovery_action(  # pylint: disable=too-many-arguments
    *,
    proposal_id: str,
    intent_present: bool,
    proposed_hash: str,
    live_marker: str,
    live_hash: str,
    live_absent: bool,
    live_read_failed: bool,
    base_hash: str,
) -> str:
    """Flat explicit recovery state machine (no opaque kwargs)."""
    if live_read_failed or not intent_present or not _valid_content_hash(proposed_hash):
        return "review"
    if live_absent:
        return "retry_chroma"
    if not _valid_content_hash(live_hash):
        return "review"
    if live_hash == proposed_hash:
        if not live_marker:
            return "repair_marker"
        if live_marker == proposal_id:
            return "approve"
        return "review"
    # A revised decision retains the previous approval marker at its valid base.
    # Matching proposed content still requires this proposal's marker (above).
    if _valid_content_hash(base_hash) and live_hash == base_hash:
        return "retry_chroma"
    return "review"


# pylint: disable=duplicate-code
# Strict queue/intent readers intentionally do not reuse tolerant legacy or restore parsers.
def _load_queue_strict(path: Path) -> list[dict]:
    """Parse the queue JSONL without skipping malformed lines."""
    if not path.is_file():
        raise ValueError("queue_missing")
    records: list[dict] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed queue line {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"invalid queue line {number}")
        records.append(row)
    return records


def _validate_recovery_event_authority(events: list[dict]) -> None:
    """Refuse contradictory or malformed lifecycle events for recovery."""
    seen: dict[str, str] = {}
    for number, event in enumerate(events, 1):
        if not isinstance(event, dict):
            raise ValueError(f"invalid event log record {number}")
        eid = event.get("event_id")
        if not isinstance(eid, str) or not eid.strip():
            raise ValueError(f"event missing id at record {number}")
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        prior = seen.get(eid)
        if prior is not None and prior != canonical:
            raise ValueError(f"contradictory event_id {eid}")
        seen[eid] = canonical


def load_strict_approved_intent(cfg: dict, proposal_id: str, event_prop: dict) -> dict:
    """Strict approved JSONL authority bound to the signed queue and event proposal."""
    from ledger_content_hash import ledger_content_hash

    pid = proposal_id.strip()
    qrows = _load_queue_strict(queue_path(cfg))
    qmatches = [r for r in qrows if str(r.get("id") or "").strip() == pid]
    if not qmatches:
        raise ValueError("queue_proposal_missing")
    if len(qmatches) > 1:
        raise ValueError("duplicate_queue_proposal")
    qrow = qmatches[0]
    if (qrow.get("status") or "").strip() != "APPROVED":
        raise ValueError("queue_proposal_not_approved")
    signer = str(qrow.get("signer") or "").strip()
    if not is_valid_signer(signer):
        raise ValueError("queue_proposal_unsigned")
    if not str(qrow.get("signed_at") or "").strip():
        raise ValueError("queue_proposal_unsigned")

    path = approved_path(cfg)
    if not path.is_file():
        raise ValueError("approved_intent_missing")
    matches: list[dict] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed approved intent line {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"invalid approved intent line {number}")
        if str(row.get("proposal_id") or "").strip() == pid:
            matches.append(row)
    if not matches:
        raise ValueError("approved_intent_missing")
    if len(matches) > 1:
        raise ValueError("duplicate_approved_intent")
    row = matches[0]

    target = str(
        event_prop.get("target_ledger_id")
        or event_prop.get("proposed_ledger_id")
        or pid
    ).strip()
    ledger_id = str(row.get("id") or row.get("ledger_id") or "").strip()
    if ledger_id and target and ledger_id != target:
        raise ValueError("approved_intent_target_mismatch")
    if str(row.get("proposal_id") or "").strip() != pid:
        raise ValueError("approved_proposal_id_mismatch")

    approved_signer = str(row.get("author_model") or row.get("tool") or "").strip()
    if not is_valid_signer(approved_signer) or approved_signer != signer:
        raise ValueError("approved_intent_unsigned")

    expected_ledger = proposal_to_ledger(qrow, signer=signer, ledger_id=target)
    if ledger_content_hash(row) != ledger_content_hash(expected_ledger):
        raise ValueError("approved_intent_semantic_mismatch")

    ev_proposed = str(event_prop.get("proposed_content_hash") or "").strip()
    if not _valid_content_hash(ev_proposed):
        raise ValueError("event_proposed_hash_missing")
    raw_proposed = ledger_content_hash(expected_ledger)
    if ev_proposed != raw_proposed:
        raise ValueError("event_proposed_hash_mismatch")
    if qrow.get("proposed_content_hash") != ev_proposed:
        raise ValueError("queue_event_proposed_hash_mismatch")
    queue_target = str(qrow.get("target_ledger_id") or pid).strip()
    if queue_target != target:
        raise ValueError("queue_event_target_mismatch")
    from ledger_content_hash import HASH_SCHEMA_VERSION
    if any(record.get("hash_schema_version") != HASH_SCHEMA_VERSION for record in (qrow, event_prop)):
        raise ValueError("unknown_recovery_hash_schema")
    ev_base = str(event_prop.get("base_content_hash") or "").strip()
    queue_base = str(qrow.get("base_content_hash") or "").strip()
    if queue_base != ev_base or (ev_base and not _valid_content_hash(ev_base)):
        raise ValueError("queue_event_base_hash_mismatch")

    ingest_hash = ingestion_content_hash_from_record(row)
    if not ingest_hash:
        raise ValueError("approved_intent_invalid_ingest_hash")

    return row


# pylint: enable=duplicate-code

def validate_governed_apply(*, target_ledger_id: str | None, live_hash: str | None,
                           base_hash: str | None, unresolved_targets: set[str],
                           proposal_id: str, proposed_ledger_id: str,
                           live_tombstoned: bool = False,
                           unresolved_creates: set[str] | None = None) -> str | None:
    """Return the fail-closed conflict reason, if any, before a governed write."""
    creates = unresolved_creates if unresolved_creates is not None else set()
    if target_ledger_id:
        if target_ledger_id in unresolved_targets:
            return "pending_sibling"
        if live_tombstoned:
            return "target_tombstoned"
        if live_hash is None:
            return "target_missing"
        if base_hash is None or live_hash != base_hash:
            return "stale_base"
    else:
        if proposed_ledger_id in creates or proposed_ledger_id in unresolved_targets:
            return "pending_create_collision"
        if live_hash is not None:
            return "create_target_exists"
    return None


def event_proposal(cfg: dict, proposal_id: str) -> dict:
    """Return the PROPOSED payload for a proposal id (empty dict if missing)."""
    from conflict_events import load_events, reduce_events
    states = reduce_events(load_events(cfg))
    state = states.get(proposal_id) or {}
    proposal = state.get("proposal") or {}
    return dict(proposal) if isinstance(proposal, dict) else {}


def unresolved_target_ids(cfg: dict) -> set[str]:
    """Ledger ids claimed by unresolved proposals (targets or create ids)."""
    from conflict_events import load_events, reduce_events, unresolved
    out: set[str] = set()
    for pid, state in unresolved(reduce_events(load_events(cfg))).items():
        prop = state.get("proposal") or {}
        target = prop.get("target_ledger_id")
        if target:
            out.add(str(target))
        else:
            # create-if-absent: proposed ledger id defaults to proposal id
            out.add(str(prop.get("proposed_ledger_id") or pid))
    return out


class RecoveryCompletionUnknown(RuntimeError):
    """Recovery effects may be partial; completion outcome is unknown."""


def ingestion_content_hash_from_record(record: dict) -> str | None:
    """Ingestion-side semantic hash for an approved JSONL row or protocol record."""
    from ledger import ledger_unit_metadata, normalize_ledger_record

    unit = normalize_ledger_record(record)
    if unit is None:
        return None
    meta = ledger_unit_metadata(unit)
    digest = str(meta.get("content_hash") or "").strip()
    return digest or None


def stored_content_hash(unit: dict) -> str:
    """Return persisted content_hash only; never synthesize eligibility."""
    meta = dict(unit.get("metadata") or {})
    digest = str(meta.get("content_hash") or "").strip()
    return digest if _valid_content_hash(digest) else ""


def _metadata_semantic_record(meta: dict, ledger_id: str) -> dict:
    """Rebuild the v1 semantic record from persisted Chroma metadata."""

    def _list(key: str) -> list:
        raw = meta.get(key) or "[]"
        if isinstance(raw, list):
            return list(raw)
        val = json.loads(raw)
        if not isinstance(val, list):
            raise ValueError(f"invalid semantic list: {key}")
        return list(val)

    return {
        "ledger_id": meta.get("ledger_id") or ledger_id,
        "kind": meta.get("ledger_kind") or meta.get("type") or "decision",
        "status": meta.get("status") or "",
        "title": meta.get("title") or "",
        "summary": meta.get("summary") or "",
        "rationale": meta.get("rationale") or "",
        "relates_to": meta.get("relates_to") or "",
        "confidence": meta.get("confidence"),
        "domain": meta.get("domain") or "",
        "site": meta.get("site") or "",
        "notes": meta.get("notes") or "",
        "result": meta.get("result") or "",
        "alternatives_rejected": _list("alternatives_rejected_json"),
        "constraints": _list("constraints_json"),
    }


def verified_stored_content_hash(unit: dict) -> str:
    """Return content_hash only when it matches recomputed semantic metadata."""
    from ledger_content_hash import ledger_content_hash

    stored = stored_content_hash(unit)
    if not stored:
        return ""
    meta = dict(unit.get("metadata") or {})
    ledger_id = str(meta.get("ledger_id") or "").strip()
    try:
        recomputed = ledger_content_hash(_metadata_semantic_record(meta, ledger_id))
    except (ValueError, TypeError):
        return ""
    return stored if stored == recomputed else ""


def _governed_recovery_affected_paths(cfg: dict) -> list[Path]:
    from conflict_events import event_path, lock_path
    from hash_schema_gate import deploy_path, migration_report_path

    return [
        event_path(cfg),
        lock_path(cfg),
        queue_path(cfg),
        approved_path(cfg),
        deploy_path(cfg),
        migration_report_path(cfg),
    ]


def live_decision_state(cfg: dict, ledger_id: str) -> tuple[str, str, bool]:
    """Return (proposal_id_marker, content_hash, tombstoned) for a live decision."""
    if not ledger_id:
        return "", "", False
    try:
        from chroma_store import is_superseded, open_chroma_for_read
        from ledger import find_unit_by_ledger_id
        from ledger_content_hash import ledger_content_hash
    except Exception:
        return "", "", False
    chroma_dir = (cfg.get("index") or {}).get("chroma_dir")
    if not chroma_dir:
        return "", "", False
    try:
        store = open_chroma_for_read(chroma_dir)
        try:
            unit = find_unit_by_ledger_id(store, ledger_id)
        finally:
            store.close()
    except Exception:
        return "", "", False
    if unit is None:
        return "", "", False
    meta = dict(unit.get("metadata") or {})
    marker = str(meta.get("proposal_id") or "").strip()
    tombstoned = is_superseded(meta)
    live_hash = str(meta.get("content_hash") or "").strip()
    if live_hash:
        return marker, live_hash, tombstoned
    try:
        def _list(key: str) -> list:
            raw = meta.get(key) or "[]"
            if isinstance(raw, list):
                return list(raw)
            try:
                val = json.loads(raw)
                return list(val) if isinstance(val, list) else []
            except Exception:
                return []

        record = {
            "ledger_id": meta.get("ledger_id") or ledger_id,
            "kind": meta.get("ledger_kind") or meta.get("type") or "decision",
            "status": meta.get("status") or "",
            "title": meta.get("title") or "",
            "summary": meta.get("summary") or "",
            "rationale": meta.get("rationale") or "",
            "relates_to": meta.get("relates_to") or "",
            "confidence": meta.get("confidence"),
            "domain": meta.get("domain") or "",
            "site": meta.get("site") or "",
            "notes": meta.get("notes") or "",
            "result": meta.get("result") or "",
            "alternatives_rejected": _list("alternatives_rejected_json"),
            "constraints": _list("constraints_json"),
        }
        return marker, ledger_content_hash(record), tombstoned
    except Exception:
        return marker, "", tombstoned


def live_decision_snapshot(cfg: dict, ledger_id: str) -> tuple[str, str]:
    """Return (proposal_id_marker, content_hash) for a live decision, or ("", "")."""
    marker, live_hash, _tomb = live_decision_state(cfg, ledger_id)
    return marker, live_hash


def _recovery_classify_live(store, ledger_id: str) -> dict:
    """Fresh authoritative lookup under native lock (includes superseded rows)."""
    from chroma_store import is_superseded
    # Whole-repo Pylint also loads stale docs/chatgpt-pack modules with these names.
    from ledger import invalidate_ledger_index_cache  # pylint: disable=no-name-in-module

    invalidate_ledger_index_cache(getattr(store, "chroma_dir", ""))
    needle = ledger_id.strip()
    if not needle:
        return {"review": "target_missing"}
    try:
        rows = store.units_metadata(include_superseded=True)
    except Exception:  # pylint: disable=broad-exception-caught
        # Read boundary: any Chroma/metadata failure → refuse as unknown live state.
        return {"review": "missing_collection"}
    matches = [dict(m) for m in rows if str(m.get("ledger_id") or "").strip() == needle]
    if not matches:
        return {"review": None, "absent": True, "marker": "", "live_hash": "", "unit": None}
    active = [m for m in matches if not is_superseded(m)]
    tombstoned = [m for m in matches if is_superseded(m)]
    if len(active) > 1:
        return {"review": "duplicate_ledger_identity"}
    if active and tombstoned:
        return {"review": "tombstone_and_active_identity"}
    if not active:
        return {"review": "target_tombstoned"}
    meta = active[0]
    try:
        unit = store.get_unit(meta["id"], include_embedding=True)
    except Exception:  # pylint: disable=broad-exception-caught
        # Read boundary: unreadable unit → refuse rather than guess.
        return {"review": "chroma_unreadable"}
    if unit is None:
        return {"review": "chroma_unreadable"}
    live_hash = verified_stored_content_hash(unit)
    if not live_hash:
        return {"review": "missing_content_hash"}
    return {
        "review": None,
        "absent": False,
        "marker": str(meta.get("proposal_id") or "").strip(),
        "live_hash": live_hash,
        "unit": unit,
    }


def _verify_live_matches_intent(unit: dict, intent_row: dict, store) -> str | None:
    # Whole-repo Pylint also loads stale docs/chatgpt-pack modules with these names.
    from ledger import ledger_unit_document, normalize_ledger_record  # pylint: disable=no-name-in-module
    from ledger_content_hash import ledger_content_hash

    normalized = normalize_ledger_record(intent_row)
    if normalized is None:
        return "invalid_intent"
    expected_hash = ingestion_content_hash_from_record(intent_row)
    if not expected_hash:
        return "invalid_intent_hash"
    meta = dict(unit.get("metadata") or {})
    ledger_id = str(meta.get("ledger_id") or "").strip()
    live_hash = verified_stored_content_hash(unit)
    if not live_hash:
        return "missing_content_hash"
    if ledger_content_hash(_metadata_semantic_record(meta, ledger_id)) != live_hash:
        return "hash_metadata_mismatch"
    if live_hash != expected_hash:
        return "hash_mismatch"
    document = (unit.get("document") or "").strip()
    if document != ledger_unit_document(normalized):
        return "document_mismatch"
    chroma_id = meta.get("id") or unit.get("id")
    if chroma_id:
        try:
            fetched = store.get_unit(chroma_id, include_embedding=True)
            embedding = (fetched or {}).get("embedding")
            if not isinstance(embedding, list) or not embedding:
                return "missing_embedding"
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in embedding):
                return "invalid_embedding"
        except Exception:  # pylint: disable=broad-exception-caught
            # Read boundary: embedding fetch failure → refuse unknown live corpus.
            return "chroma_unreadable"
    return None


def _repair_marker_only(
    store,
    unit: dict,
    proposal_id: str,
    intent_row: dict,
) -> None:
    reason = _verify_live_matches_intent(unit, intent_row, store)
    if reason:
        raise ValueError(f"marker repair refused ({reason})")
    meta = dict(unit.get("metadata") or {})
    if meta.get("proposal_id"):
        raise ValueError("marker repair refused (nonempty marker)")
    chroma_id = meta.get("id") or unit.get("id")
    new_meta = {**meta, "proposal_id": proposal_id}
    store.update_unit_metadata(chroma_id, new_meta)


def _recovery_apply_intent(store, intent_row: dict, models: dict) -> dict:
    # Whole-repo Pylint also loads stale docs/chatgpt-pack modules with these names.
    from ledger import build_ledger_index, invalidate_ledger_index_cache  # pylint: disable=no-name-in-module
    from observe import ingest_observation

    invalidate_ledger_index_cache(store.chroma_dir)
    by_ledger_id, _ = build_ledger_index(store)
    protocol_row = {**intent_row, "_governed_protocol": True}
    unit = ingest_observation(
        protocol_row,
        store=store,
        embed_model=models.get("embed_model", "nomic-embed-text"),
        ollama_host=models.get("ollama_host", ""),
        upsert=True,
        units_export=None,
        by_ledger_id=by_ledger_id,
    )
    if unit is None:
        raise ValueError("ingestion rejected approved intent")
    return unit


def _export_unit_for_recovery(intent_row: dict, live_unit: dict) -> dict:
    """Normalized export row using the live Chroma id and stable projection fields."""
    from ledger import normalize_ledger_record

    unit = normalize_ledger_record(intent_row)
    if unit is None:
        raise ValueError("invalid export intent")
    meta = dict(live_unit.get("metadata") or {})
    chroma_id = str(live_unit.get("id") or meta.get("id") or "").strip()
    if not chroma_id:
        raise ValueError("export_missing_chroma_id")
    unit["id"] = chroma_id
    timestamp = meta.get("timestamp") or unit.get("timestamp")
    if timestamp:
        unit["timestamp"] = str(timestamp)
    return unit


def _check_recovery_export(units_export, intent_row, live, base_hash):
    """Validate an existing projection before any corpus change; recheck at publication."""
    # Whole-repo Pylint also loads stale docs/chatgpt-pack modules with these names.
    from ledger import (  # pylint: disable=no-name-in-module
        ledger_unit_document, ledger_unit_metadata, normalize_ledger_record,
    )
    # Whole-repo Pylint also loads stale docs/chatgpt-pack modules with these names.
    from observe import export_projection_records, export_unit_matches_normalized  # pylint: disable=no-name-in-module
    from purge_locks import export_flock_path

    if units_export is None:
        return None
    if units_export.exists() and not units_export.is_file():
        raise ValueError("export is not a regular file")
    expected = normalize_ledger_record(intent_row)
    if expected is None:
        raise ValueError("invalid export intent")
    with export_flock_path(units_export):
        rows, reason = export_projection_records(units_export, expected["ledger_id"])
        if reason:
            raise ValueError(reason)
        if not rows:
            return None
        existing = rows[0]
        unit = live.get("unit")
        if unit is not None and live.get("live_hash") == ingestion_content_hash_from_record(intent_row):
            expected = _export_unit_for_recovery(intent_row, unit)
        else:
            expected["id"] = existing.get("id")
        if export_unit_matches_normalized(expected, existing):
            return dict(existing)
        if unit is not None and base_hash and live.get("live_hash") == base_hash:
            try:
                projection_hash = ledger_unit_metadata(existing)["content_hash"]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("invalid base export projection") from exc
            if (projection_hash == base_hash and existing.get("id") == unit["id"]
                    and ledger_unit_document(existing) == unit.get("document")
                    and existing.get("proposal_id", "") == live.get("marker", "")):
                return dict(existing)
        raise ValueError("conflicting_export_projection")


def _fsync_export_path(units_export: Path, durability_root: Path) -> None:
    try:
        with open(units_export, "rb") as handle:
            os.fsync(handle.fileno())
        from conflict_events import _ensure_directory_chain_durable

        _ensure_directory_chain_durable(units_export.parent, stop=durability_root)
    except OSError as exc:
        raise RecoveryCompletionUnknown(f"export durability outcome unknown: {exc}") from exc


def _ensure_export_for_recovery(
    units_export: Path | None,
    intent_row: dict,
    live_unit: dict,
    *,
    allow_replace: bool,
    durability_root: Path,
    base_export_row: dict | None = None,
) -> None:
    from atomic_files import atomic_write_text
    # Whole-repo Pylint also loads stale docs/chatgpt-pack modules with these names.
    from observe import export_unit_matches_normalized  # pylint: disable=no-name-in-module
    from purge_locks import export_flock_path

    if units_export is None:
        return
    expected = _export_unit_for_recovery(intent_row, live_unit)
    ledger_id = str(expected.get("ledger_id") or "").strip()
    if not ledger_id:
        raise ValueError("export repair requires ledger_id")

    with export_flock_path(units_export):
        units_export.parent.mkdir(parents=True, exist_ok=True)
        parsed: list[tuple[str, dict | None]] = []
        if units_export.is_file():
            for number, raw in enumerate(
                units_export.read_text(encoding="utf-8").splitlines(keepends=True), 1
            ):
                stripped = raw.strip()
                if not stripped:
                    parsed.append((raw, None))
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"malformed_export_line_{number}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"invalid_export_line_{number}")
                parsed.append((raw, row))

        existing_rows = [
            row
            for _raw, row in parsed
            if row is not None and str(row.get("ledger_id") or "").strip() == ledger_id
        ]
        if len(existing_rows) > 1:
            raise ValueError("duplicate_export_identity")

        compare_expected = {
            k: v for k, v in expected.items() if not str(k).startswith("_")
        }
        if existing_rows:
            existing = existing_rows[0]
            if export_unit_matches_normalized(compare_expected, existing):
                _fsync_export_path(units_export, durability_root)
                return
            if not allow_replace:
                raise ValueError("conflicting_export_projection")
            if base_export_row is None:
                raise ValueError("conflicting_export_projection")
            if not export_unit_matches_normalized(base_export_row, existing):
                raise ValueError("export_replace_not_verified")
            out_lines: list[str] = []
            replaced = False
            for _raw, row in parsed:
                if row is not None and str(row.get("ledger_id") or "").strip() == ledger_id:
                    out_lines.append(json.dumps(compare_expected) + "\n")
                    replaced = True
                else:
                    out_lines.append(_raw)
            if not replaced:
                out_lines.append(json.dumps(compare_expected) + "\n")
            atomic_write_text(units_export, "".join(out_lines))
            _fsync_export_path(units_export, durability_root)
            return

        payload = json.dumps(compare_expected) + "\n"
        if parsed:
            atomic_write_text(
                units_export, "".join(raw for raw, _row in parsed) + payload
            )
        else:
            atomic_write_text(units_export, payload)
        _fsync_export_path(units_export, durability_root)


def _publish_recovery_event(
    cfg: dict, proposal_id: str, *, lifecycle_approved: bool, durability_root: Path
) -> None:
    from conflict_events import append_event_durable, ensure_event_log_durable, new_event

    if lifecycle_approved:
        ensure_event_log_durable(cfg, durability_root=durability_root)
        return
    append_event_durable(
        cfg, new_event("APPROVED", proposal_id), durability_root=durability_root
    )


def _load_recovery_event_states(cfg: dict) -> dict:
    from conflict_events import load_events, reduce_events

    events = load_events(cfg)
    _validate_recovery_event_authority(events)
    return reduce_events(events)


@dataclass(frozen=True)
class _RecoveryIntent:
    lifecycle: str
    target: str
    base_hash: str
    row: dict
    proposed_hash: str


def _recovery_authority_from_states(
    states: dict, cfg: dict, proposal_id: str
) -> _RecoveryIntent:
    """Resolve lifecycle, target ledger, hashes, and strict approved intent."""
    state = states.get(proposal_id)
    if state is None:
        raise ValueError(f"Proposal not found in event log: {proposal_id}")
    lifecycle = state.get("lifecycle_state")
    if lifecycle not in {"APPROVAL_STARTED", "APPROVED"}:
        raise ValueError(
            f"Proposal {proposal_id} is not recoverable (lifecycle={lifecycle})"
        )
    if state.get("active_conflicts"):
        raise ValueError(f"Proposal {proposal_id} needs human review (active conflicts)")
    prop = dict(state.get("proposal") or {})
    target = str(
        prop.get("target_ledger_id") or prop.get("proposed_ledger_id") or proposal_id
    )
    base_hash = str(prop.get("base_content_hash") or "")
    if not _valid_content_hash(base_hash):
        base_hash = ""
    intent_row = load_strict_approved_intent(cfg, proposal_id, prop)
    proposed_hash = ingestion_content_hash_from_record(intent_row) or ""
    if not _valid_content_hash(proposed_hash):
        raise ValueError(f"Proposal {proposal_id} needs human review (invalid intent hash)")
    return _RecoveryIntent(lifecycle, target, base_hash, intent_row, proposed_hash)


def _execute_recovery_inside_guard(op, proposal_id, intent, store, guard, *, durability_root) -> str:
    """One serialized inspect/apply/validate/export/approve sequence."""
    from chroma_write_store import admitted_units_export_path, verify_admitted_operation_unchanged

    cfg = op.config()
    units_export = admitted_units_export_path(cfg)
    live = _recovery_classify_live(store, intent.target)
    if live.get("review"):
        raise ValueError(f"Proposal {proposal_id} needs human review ({live['review']})")
    action = classify_recovery_action(
        proposal_id=proposal_id, intent_present=True, proposed_hash=intent.proposed_hash,
        live_marker=live.get("marker") or "", live_hash=live.get("live_hash") or "",
        live_absent=bool(live.get("absent")), live_read_failed=False, base_hash=intent.base_hash,
    )
    if action == "review" or (intent.lifecycle == "APPROVED" and action != "approve"):
        raise ValueError(f"Proposal {proposal_id} needs human review (action={action})")
    base_export = _check_recovery_export(units_export, intent.row, live, intent.base_hash)
    if action == "repair_marker":
        _repair_marker_only(store, live["unit"], proposal_id, intent.row)
    elif action == "retry_chroma":
        _recovery_apply_intent(store, intent.row, cfg.get("models") or {})

    after = _recovery_classify_live(store, intent.target)
    if after.get("review") or after.get("absent"):
        raise ValueError(f"Proposal {proposal_id} needs human review (post-write state unavailable)")
    reason = _verify_live_matches_intent(after["unit"], intent.row, store)
    if reason or after.get("marker") != proposal_id:
        raise ValueError(f"Proposal {proposal_id} needs human review ({reason or 'marker incomplete'})")
    verify_admitted_operation_unchanged(op)
    guard.finalize_approval_recovery()
    _ensure_export_for_recovery(
        units_export, intent.row, after["unit"], allow_replace=action == "retry_chroma",
        durability_root=durability_root, base_export_row=base_export,
    )
    verify_admitted_operation_unchanged(op)
    _publish_recovery_event(
        cfg, proposal_id, lifecycle_approved=intent.lifecycle == "APPROVED",
        durability_root=durability_root,
    )
    return action


def _recover_approval_impl(op, proposal_id: str) -> str:
    from chroma_write_guard import ChromaWriteGuardError, ChromaWriteQuarantinedError
    from chroma_write_store import (
        recovery_durability_root,
        open_production_recovery_write_store,
        verify_admitted_operation_unchanged,
        verify_admitted_targets_unchanged,
        verify_recovery_config_binding,
    )
    from conflict_events import EventPublicationError, governed_lock
    from purge_locks import index_write_flock

    proposal_id = proposal_id.strip()
    cfg = op.config()
    verify_recovery_config_binding(op, cfg)
    durability_root = recovery_durability_root(op)
    with governed_lock(cfg), index_write_flock(cfg):
        try:
            states = _load_recovery_event_states(cfg)
        except ValueError as exc:
            raise ValueError(f"event authority unreadable for {proposal_id}: {exc}") from exc
        intent = _recovery_authority_from_states(
            states, cfg, proposal_id
        )

        verify_admitted_operation_unchanged(op)
        session = open_production_recovery_write_store(entrypoint=op.entrypoint)
        store = session.store
        action = "review"
        try:
            guard = store._write_guard  # pylint: disable=protected-access
            if guard is None:
                raise ValueError(
                    f"Proposal {proposal_id} needs human review (write guard required)"
                )
            with guard.approval_recovery_critical_section(
                reload_client=store._reload_client,  # pylint: disable=protected-access
            ) as recovery_guard:
                verify_recovery_config_binding(op, cfg)
                verify_admitted_operation_unchanged(op)
                verify_admitted_targets_unchanged(op)
                action = _execute_recovery_inside_guard(
                    op, proposal_id, intent, store, recovery_guard, durability_root=durability_root
                )
        except (EventPublicationError, OSError) as exc:
            raise RecoveryCompletionUnknown(
                f"recovery completion outcome unknown for {proposal_id}: {exc}"
            ) from exc
        except (ChromaWriteQuarantinedError, ChromaWriteGuardError) as exc:
            raise ValueError(f"Proposal {proposal_id} needs human review ({exc})") from exc
        finally:
            store.close()
        return action


def recover_approval(cfg: dict | None, proposal_id: str) -> str:
    """Reconcile APPROVAL_STARTED / verify APPROVED completion under admission."""
    from chroma_write_store import (
        _bound_operation,
        admitted_write_operation,
        verify_recovery_config_binding,
    )

    op = _bound_operation()
    if op is not None:
        verify_recovery_config_binding(op, cfg)
        return _recover_approval_impl(op, proposal_id.strip())
    with admitted_write_operation(
        entrypoint="propose_decision.write",
        extra_affected_paths=_governed_recovery_affected_paths,
    ) as admitted:
        verify_recovery_config_binding(admitted, cfg)
        return _recover_approval_impl(admitted, proposal_id.strip())


def find_proposal(records: list[dict], proposal_id: str) -> dict | None:
    needle = proposal_id.strip()
    for rec in reversed(records):
        if rec.get("id") == needle:
            return rec
    return None


def pending_proposal_for_review(cfg: dict, proposal_id: str) -> dict:
    """Load one PENDING proposal for human review, or raise ValueError."""
    needle = (proposal_id or "").strip()
    if not needle:
        raise ValueError("Proposal id is required")
    proposal = find_proposal(load_queue(queue_path(cfg)), needle)
    if proposal is None:
        raise ValueError(f"Proposal not found: {needle}")
    status = proposal.get("status") or "PENDING"
    if status != "PENDING":
        raise ValueError(f"Proposal {needle} is not PENDING (status={status})")
    return proposal


def format_proposal_review(row: dict) -> str:
    """Pure human-readable review card for a proposal row (JSONL stays canonical)."""

    def _scalar(key: str, *, default: str = "") -> str:
        val = row.get(key)
        if val is None:
            return default
        text = str(val).strip() if isinstance(val, str) else str(val)
        return text if text else default

    def _block(label: str, text: str) -> list[str]:
        if not text:
            return [f"{label}:"]
        lines = text.splitlines() or [text]
        if len(lines) == 1:
            return [f"{label}: {lines[0]}"]
        out = [f"{label}:"]
        out.extend(f"  {line}" for line in lines)
        return out

    def _bullets(label: str, items) -> list[str]:
        out = [f"{label}:"]
        if not items:
            out.append("  (none)")
            return out
        for item in items:
            text = str(item).strip() if item is not None else ""
            if not text:
                out.append("  -")
                continue
            item_lines = text.splitlines() or [text]
            out.append(f"  - {item_lines[0]}")
            out.extend(f"    {line}" for line in item_lines[1:])
        return out

    target = row.get("target_ledger_id")
    target_s = _scalar("target_ledger_id") if target not in (None, "") else "(none)"
    site = _scalar("site")
    conf = row.get("confidence")
    conf_s = "" if conf is None else str(conf)

    lines: list[str] = [
        "── Decision draft ──",
        f"id: {_scalar('id', default='?')}",
        f"status: {_scalar('status', default='PENDING')}",
        *_block("summary", _scalar("summary")),
        *_block("rationale", _scalar("rationale")),
        f"relates_to: {_scalar('relates_to')}",
        f"proposed_by: {_scalar('proposed_by')}",
        f"proposed_at: {_scalar('proposed_at')}",
        f"domain: {_scalar('domain')}",
        f"site: {site if site else '(none)'}",
        f"confidence: {conf_s}",
        f"target_ledger_id: {target_s}",
        *_bullets("alternatives_rejected", row.get("alternatives_rejected")),
        *_bullets("constraints", row.get("constraints")),
    ]
    return "\n".join(lines)


def proposal_to_ledger(
    proposal: dict,
    *,
    signer: str,
    ledger_id: str | None = None,
) -> dict:
    """Shape for decisions-approved.jsonl → normalize_ledger_record."""
    return {
        "id": (ledger_id or proposal["id"]).strip(),
        "kind": "decision",
        "status": "accepted",
        "relates_to": proposal["relates_to"],
        "summary": proposal["summary"],
        "rationale": proposal.get("rationale") or "",
        "alternatives_rejected": list(proposal.get("alternatives_rejected") or []),
        "constraints": list(proposal.get("constraints") or []),
        "author_model": signer.strip(),
        "domain": proposal.get("domain") or "coding.tooling",
        "site": proposal.get("site") or "",
        "confidence": float(proposal.get("confidence", 0.8)),
        "timestamp": _now_iso(),
        "tool": signer.strip(),
        # This link is required for recovery when ledger_id is reused by revisions.
        "proposal_id": proposal["id"],
    }


def _normalize_constraints(constraints: list[str] | None) -> list[str]:
    values = [str(value).strip() for value in (constraints or [])]
    if not values or any(not value for value in values):
        raise ValueError(
            "--constraint is required; use the exact sentinel "
            f"{NO_CONSTRAINT_SENTINEL!r} when none are identified"
        )
    for value in values:
        normalized_sentinel = value.casefold().replace("_", "-").replace(" ", "-")
        if normalized_sentinel == NO_CONSTRAINT_SENTINEL and value != NO_CONSTRAINT_SENTINEL:
            raise ValueError(
                f"no-constraint sentinel must be exactly {NO_CONSTRAINT_SENTINEL!r}"
            )
    if NO_CONSTRAINT_SENTINEL in values and len(values) != 1:
        raise ValueError(f"{NO_CONSTRAINT_SENTINEL!r} cannot accompany other constraints")
    return values


def propose(
    cfg: dict,
    *,
    relates_to: str,
    summary: str,
    rationale: str,
    author: str,
    alternatives: list[str] | None = None,
    constraints: list[str] | None = None,
    domain: str = "coding.tooling",
    site: str = "",
    confidence: float = 0.8,
    proposal_id: str | None = None,
    source: str = "cli",
    target_ledger_id: str | None = None,
) -> dict:
    relates_to = relates_to.strip()
    summary = summary.strip()
    rationale = rationale.strip()
    author = author.strip()
    if not relates_to:
        raise ValueError("--relates-to is required")
    if not summary:
        raise ValueError("--summary is required")
    if not rationale:
        raise ValueError("--rationale is required")
    if not author:
        raise ValueError("--author is required")
    normalized_constraints = _normalize_constraints(constraints)

    pid = (proposal_id or generate_proposal_id()).strip()
    target = (target_ledger_id or "").strip() or None
    record = {
        "id": pid,
        "kind": PROPOSAL_KIND,
        "status": "PENDING",
        "relates_to": relates_to,
        "summary": summary,
        "rationale": rationale,
        "alternatives_rejected": list(alternatives or []),
        "constraints": normalized_constraints,
        "domain": domain.strip() or "coding.tooling",
        "site": site.strip(),
        "confidence": confidence,
        "proposed_by": author,
        "proposed_at": _now_iso(),
        "source": source,
        "signer": None,
        "signed_at": None,
        "rejection_reason": None,
        "target_ledger_id": target,
    }

    # The legacy queue remains a compatibility input until T5 migration; the
    # event is the protocol record used for conflict/lifecycle reduction.
    from conflict_events import append_event, governed_lock, new_event
    from hash_schema_gate import ensure_schema_deploy_recorded
    from ledger_content_hash import HASH_SCHEMA_VERSION, ledger_content_hash
    with governed_lock(cfg):
        ensure_schema_deploy_recorded(cfg)
        qpath = queue_path(cfg)
        records = load_queue(qpath)
        if find_proposal(records, pid) is not None:
            raise ValueError(f"Proposal already exists: {pid}")
        # Snapshot hashes under the same lock as the PROPOSED append.
        proposed_ledger_id = target or pid
        draft = proposal_to_ledger(record, signer=author, ledger_id=proposed_ledger_id)
        proposed_hash = ledger_content_hash(draft)
        base_hash = None
        if target:
            _marker, base_hash = live_decision_snapshot(cfg, target)
            base_hash = base_hash or None
        if target and target in unresolved_target_ids(cfg):
            raise ValueError(f"pending_sibling for target {target}")
        if (not target) and pid in unresolved_target_ids(cfg):
            raise ValueError(f"pending_create_collision for {pid}")
        record["base_content_hash"] = base_hash
        record["proposed_content_hash"] = proposed_hash
        record["hash_schema_version"] = HASH_SCHEMA_VERSION
        records.append(record)
        save_queue(qpath, records)
        append_event(cfg, new_event("PROPOSED", pid, proposal={
            "target_ledger_id": target,
            "proposed_ledger_id": proposed_ledger_id,
            "base_content_hash": base_hash,
            "proposed_content_hash": proposed_hash,
            "hash_schema_version": HASH_SCHEMA_VERSION,
            "summary": summary,
            "rationale": rationale,
            "proposed_by": author,
            "relates_to": relates_to,
            "alternatives_rejected": list(alternatives or []),
            "constraints": normalized_constraints,
            "domain": record["domain"],
            "site": record["site"],
            "confidence": confidence,
        }))
    return record


def list_proposals(
    cfg: dict,
    *,
    show_all: bool = False,
) -> list[dict]:
    records = load_queue(queue_path(cfg))
    if show_all:
        return records
    return [r for r in records if (r.get("status") or "PENDING") == "PENDING"]


def latest_pending(cfg: dict) -> dict | None:
    """Newest PENDING proposal by proposed_at (ISO), then queue order."""
    records = load_queue(queue_path(cfg))
    pending_indexed = [
        (i, r)
        for i, r in enumerate(records)
        if (r.get("status") or "PENDING") == "PENDING"
    ]
    if not pending_indexed:
        return None
    pending_indexed.sort(
        key=lambda t: (t[1].get("proposed_at") or "", t[0]),
    )
    return pending_indexed[-1][1]


def ingest_approved_file(cfg: dict, *, verbose: bool = False) -> dict:
    """Upsert decisions-approved.jsonl into Chroma."""

    from chroma_write_store import open_production_write_store
    from observe import ingest_observation_file
    from purge_locks import index_write_flock

    models = cfg.get("models")
    if not models:
        from config import load_config

        models = load_config()["models"]
    lock_cfg = cfg if cfg.get("index") else None
    if lock_cfg is None:
        from config import load_config

        lock_cfg = load_config()
    from chroma_readonly import open_readonly_unit_store
    from observe import ingest_observation_file_with_drift_retry

    approved = str(approved_path(cfg))
    embed_store = open_readonly_unit_store(lock_cfg["index"]["chroma_dir"])

    def open_write_commit(commit_fn):
        with index_write_flock(lock_cfg):
            _pw = open_production_write_store(entrypoint="propose_decision.write")
            store = _pw.store
            live = _pw.live_cfg
            units_export = live["index"].get("units_export")
            units_export_path = Path(units_export).expanduser() if units_export else None
            try:
                return commit_fn(store, units_export_path)
            finally:
                store.close()

    return ingest_observation_file_with_drift_retry(
        approved,
        embed_store=embed_store,
        open_write_commit=open_write_commit,
        embed_model=models["embed_model"],
        ollama_host=models["ollama_host"],
        upsert=True,
        verbose=verbose,
    )


def ingest_approved_ledger(cfg: dict, ledger: dict, *, verbose: bool = False) -> dict:
    """Index one approved decision (fast path for record --approve-last)."""

    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import open_production_write_store
    # Whole-repo Pylint also loads stale docs/chatgpt-pack modules with these names.
    from ledger import invalidate_ledger_index_cache  # pylint: disable=no-name-in-module
    from observe import (
        ObservationIngestDriftError,
        ObservationIngestDriftRefusedError,
        commit_observation_ingest,
        prepare_observation_ingest,
    )
    from purge_locks import index_write_flock

    models = cfg.get("models")
    if not models:
        from config import load_config

        models = load_config()["models"]
    lock_cfg = cfg if cfg.get("index") else None
    if lock_cfg is None:
        from config import load_config

        lock_cfg = load_config()
    protocol_ledger = {**ledger, "_governed_protocol": True}
    reader = open_readonly_unit_store(lock_cfg["index"]["chroma_dir"])
    prepared = prepare_observation_ingest(
        protocol_ledger,
        store=reader,
        embed_model=models["embed_model"],
        ollama_host=models["ollama_host"],
        upsert=True,
    )
    stats = {"accepted": 0, "rejected": 0, "updated": 0, "skipped": 0}
    if prepared is None:
        stats["rejected"] = 1
        return stats
    unit = None
    for attempt in range(2):
        try:
            with index_write_flock(lock_cfg):
                _pw = open_production_write_store(entrypoint="propose_decision.write")
                store = _pw.store
                live = _pw.live_cfg
                units_export = live["index"].get("units_export")
                units_export_path = Path(units_export).expanduser() if units_export else None
                try:
                    unit = commit_observation_ingest(
                        prepared,
                        store=store,
                        units_export=units_export_path,
                    )
                finally:
                    store.close()
            break
        except ObservationIngestDriftError:
            if attempt == 1:
                raise ObservationIngestDriftRefusedError("approved ledger ingest drift") from None
            invalidate_ledger_index_cache(lock_cfg["index"]["chroma_dir"])
            fresh_reader = open_readonly_unit_store(lock_cfg["index"]["chroma_dir"])
            prepared = prepare_observation_ingest(
                protocol_ledger,
                store=fresh_reader,
                embed_model=models["embed_model"],
                ollama_host=models["ollama_host"],
                upsert=True,
            )
            if prepared is None:
                stats["rejected"] = 1
                return stats
    if unit is None:
        stats["rejected"] = 1
    elif unit.pop("_upserted", False):
        stats["updated"] = 1
    elif unit.pop("_skipped", False):
        stats["skipped"] = 1
    else:
        stats["accepted"] = 1
    invalidate_ledger_index_cache(lock_cfg["index"]["chroma_dir"])
    return stats


def _approve_unlocked(
    cfg: dict,
    proposal_id: str,
    *,
    signer: str,
    ledger_id: str | None = None,
) -> tuple[dict, dict]:
    """Apply APPROVAL_STARTED + approved JSONL. Caller MUST hold governed_lock."""
    from conflict_events import append_event, load_events, new_event, reduce_events, unresolved
    from ledger_content_hash import ledger_content_hash

    qpath = queue_path(cfg)
    records = load_queue(qpath)
    proposal = find_proposal(records, proposal_id)
    if proposal is None:
        raise ValueError(f"Proposal not found: {proposal_id}")
    if proposal.get("status") != "PENDING":
        raise ValueError(
            f"Proposal {proposal_id} is not PENDING (status={proposal.get('status')})"
        )

    prop = event_proposal(cfg, proposal_id)
    # Gate 5: hashless targeted proposals warn then block after graduation.
    from hash_schema_gate import enforce_hashless_on_approve, ensure_schema_deploy_recorded
    ensure_schema_deploy_recorded(cfg)
    gate5_payload = {
        **prop,
        "id": proposal_id,
        "target_ledger_id": prop.get("target_ledger_id") or proposal.get("target_ledger_id"),
        "base_content_hash": prop.get("base_content_hash") or proposal.get("base_content_hash"),
        "proposed_content_hash": prop.get("proposed_content_hash") or proposal.get("proposed_content_hash"),
    }
    gate5_warning = enforce_hashless_on_approve(cfg, gate5_payload)
    if gate5_warning:
        # Surface via stderr for CLI operators; library callers can inspect later.
        import sys
        print(f"⚠ Gate 5: {gate5_warning}", file=sys.stderr)

    target = (ledger_id or prop.get("target_ledger_id") or prop.get("proposed_ledger_id")
              or proposal.get("target_ledger_id") or proposal_id)
    target = str(target).strip()
    base_hash = prop.get("base_content_hash")
    if base_hash is None:
        base_hash = proposal.get("base_content_hash")

    # Exclude this proposal from sibling set for the duration of its own approve.
    unresolved_targets: set[str] = set()
    unresolved_creates: set[str] = set()
    for pid, state in unresolved(reduce_events(load_events(cfg))).items():
        if pid == proposal_id:
            continue
        p = state.get("proposal") or {}
        if p.get("target_ledger_id"):
            unresolved_targets.add(str(p["target_ledger_id"]))
        else:
            unresolved_creates.add(str(p.get("proposed_ledger_id") or pid))

    live_marker, live_hash, live_tombstoned = live_decision_state(cfg, target)
    live_hash_or_none = live_hash or None
    # create-if-absent when proposal has no target_ledger_id
    target_for_validate = prop.get("target_ledger_id") or proposal.get("target_ledger_id")
    conflict = validate_governed_apply(
        target_ledger_id=target_for_validate,
        live_hash=live_hash_or_none,
        base_hash=base_hash,
        unresolved_targets=unresolved_targets,
        proposal_id=proposal_id,
        proposed_ledger_id=target,
        live_tombstoned=live_tombstoned,
        unresolved_creates=unresolved_creates,
    )
    if conflict:
        raise ValueError(conflict)

    append_event(cfg, new_event("APPROVAL_STARTED", proposal_id))
    now = _now_iso()
    proposal["status"] = "APPROVED"
    proposal["signer"] = signer.strip()
    proposal["signed_at"] = now
    save_queue(qpath, records)
    ledger = proposal_to_ledger(proposal, signer=signer, ledger_id=target)
    # Keep proposed hash aligned with the durable approved row.
    if not prop.get("proposed_content_hash"):
        prop_hash = ledger_content_hash(ledger)
    else:
        prop_hash = prop.get("proposed_content_hash")
    ledger["_proposed_content_hash"] = prop_hash  # not persisted long-term; stripped below
    row = {k: v for k, v in ledger.items() if not k.startswith("_")}
    append_approved(approved_path(cfg), row)
    return proposal, row


def approve(
    cfg: dict,
    proposal_id: str,
    *,
    signer: str,
    ledger_id: str | None = None,
) -> tuple[dict, dict]:
    if not is_valid_signer(signer):
        raise ValueError(
            f"Invalid --signer {signer!r}; use ryan or kiro-review (or kiro-* identity)"
        )

    from conflict_events import governed_lock
    with governed_lock(cfg):
        return _approve_unlocked(cfg, proposal_id, signer=signer, ledger_id=ledger_id)


def _mark_approved_unlocked(cfg: dict, proposal_id: str) -> None:
    """Append APPROVED. Caller MUST hold governed_lock."""
    from conflict_events import append_event, new_event
    append_event(cfg, new_event("APPROVED", proposal_id))


def mark_approved(cfg: dict, proposal_id: str) -> None:
    """Finish a successfully indexed approval while holding the same data-root lock."""
    from conflict_events import governed_lock
    with governed_lock(cfg):
        _mark_approved_unlocked(cfg, proposal_id)


def approve_and_ingest(cfg: dict, proposal_id: str, *, signer: str, ledger_id: str | None = None) -> tuple[dict, dict, dict]:
    """Run the durable approval saga under one data-root flock.

    An apply error deliberately leaves APPROVAL_STARTED for proposal-keyed
    recovery; it is not converted into a terminal failure event.
    """
    if not is_valid_signer(signer):
        raise ValueError(
            f"Invalid --signer {signer!r}; use ryan or kiro-review (or kiro-* identity)"
        )
    from chroma_write_store import production_writer_boundary
    from conflict_events import governed_lock

    with production_writer_boundary(entrypoint="propose_decision.write"):
        with governed_lock(cfg):
            proposal, ledger = _approve_unlocked(
                cfg, proposal_id, signer=signer, ledger_id=ledger_id
            )
            stats = ingest_approved_ledger(cfg, ledger)
            _mark_approved_unlocked(cfg, proposal_id)
            return proposal, ledger, stats



def rebase_proposal(
    cfg: dict,
    proposal_id: str,
    *,
    author: str | None = None,
) -> dict:
    """Gate 9: stale-base resolution — new proposal_id; old → SUPERSEDED.

    Never mutates the old proposal's base hash. Fresh base is snapshotted under lock.
    """
    from conflict_events import append_event, governed_lock, load_events, new_event, reduce_events
    from ledger_content_hash import HASH_SCHEMA_VERSION, ledger_content_hash

    proposal_id = proposal_id.strip()
    with governed_lock(cfg):
        qpath = queue_path(cfg)
        records = load_queue(qpath)
        old = find_proposal(records, proposal_id)
        if old is None:
            raise ValueError(f"Proposal not found: {proposal_id}")
        if old.get("status") != "PENDING":
            raise ValueError(
                f"Proposal {proposal_id} is not PENDING (status={old.get('status')})"
            )
        states = reduce_events(load_events(cfg))
        state = states.get(proposal_id)
        if state is not None and state.get("lifecycle_state") not in {"PROPOSED"}:
            raise ValueError(
                f"Proposal {proposal_id} cannot rebase "
                f"(lifecycle={state.get('lifecycle_state')})"
            )
        prop = dict((state or {}).get("proposal") or {})
        target = (
            prop.get("target_ledger_id")
            or old.get("target_ledger_id")
        )
        if not target:
            raise ValueError("rebase requires a targeted update proposal (target_ledger_id)")

        _marker, live_hash, tombstoned = live_decision_state(cfg, str(target))
        if tombstoned:
            raise ValueError("target_tombstoned: cannot rebase onto a tombstoned unit")
        if not live_hash:
            raise ValueError("target_missing: cannot rebase without a live base hash")

        new_id = generate_proposal_id()
        author_s = (author or old.get("proposed_by") or "rebase").strip()
        draft = {
            "id": new_id,
            "kind": PROPOSAL_KIND,
            "status": "PENDING",
            "relates_to": old["relates_to"],
            "summary": old["summary"],
            "rationale": old.get("rationale") or "",
            "alternatives_rejected": list(old.get("alternatives_rejected") or []),
            "constraints": _normalize_constraints(old.get("constraints")),
            "domain": old.get("domain") or "coding.tooling",
            "site": old.get("site") or "",
            "confidence": float(old.get("confidence", 0.8)),
            "proposed_by": author_s,
            "proposed_at": _now_iso(),
            "source": "rebase",
            "signer": None,
            "signed_at": None,
            "rejection_reason": None,
            "target_ledger_id": target,
            "base_content_hash": live_hash,
            "rebases_proposal_id": proposal_id,
            "hash_schema_version": HASH_SCHEMA_VERSION,
        }
        proposed_hash = ledger_content_hash(
            proposal_to_ledger(draft, signer=author_s, ledger_id=str(target))
        )
        draft["proposed_content_hash"] = proposed_hash

        old["status"] = "SUPERSEDED"
        old["superseded_by_proposal_id"] = new_id
        old["signed_at"] = _now_iso()
        records.append(draft)
        save_queue(qpath, records)

        append_event(
            cfg,
            new_event(
                "SUPERSEDED",
                proposal_id,
                superseded_by_proposal_id=new_id,
            ),
        )
        append_event(
            cfg,
            new_event(
                "PROPOSED",
                new_id,
                proposal={
                    "target_ledger_id": target,
                    "proposed_ledger_id": target,
                    "base_content_hash": live_hash,
                    "proposed_content_hash": proposed_hash,
                    "hash_schema_version": HASH_SCHEMA_VERSION,
                    "summary": draft["summary"],
                    "rationale": draft["rationale"],
                    "proposed_by": author_s,
                    "relates_to": draft["relates_to"],
                    "alternatives_rejected": draft["alternatives_rejected"],
                    "constraints": draft["constraints"],
                    "domain": draft["domain"],
                    "site": draft["site"],
                    "confidence": draft["confidence"],
                    "rebases_proposal_id": proposal_id,
                },
            ),
        )
        return draft


def reject(
    cfg: dict,
    proposal_id: str,
    *,
    signer: str,
    reason: str,
) -> dict:
    if not is_valid_signer(signer):
        raise ValueError(
            f"Invalid --signer {signer!r}; use ryan or kiro-review (or kiro-* identity)"
        )
    reason = reason.strip()
    if not reason:
        raise ValueError("--reason is required for reject")

    from conflict_events import append_event, governed_lock, new_event
    with governed_lock(cfg):
        qpath = queue_path(cfg)
        records = load_queue(qpath)
        proposal = find_proposal(records, proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal not found: {proposal_id}")
        if proposal.get("status") != "PENDING":
            raise ValueError(
                f"Proposal {proposal_id} is not PENDING (status={proposal.get('status')})"
            )

        proposal["status"] = "REJECTED"
        proposal["signer"] = signer.strip()
        proposal["signed_at"] = _now_iso()
        proposal["rejection_reason"] = reason
        save_queue(qpath, records)
        append_event(cfg, new_event("REJECTED", proposal_id, reason=reason))
        return proposal


def interactive_lock_path(cfg: dict) -> Path:
    return data_dir(cfg) / INTERACTIVE_LOCK_NAME


@contextmanager
def interactive_session_lock(cfg: dict):
    """Exclusive lock for propose_decision -i (one wizard session at a time)."""
    path = interactive_lock_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as e:
        holder = "unknown"
        try:
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                holder = f"pid {lines[0]} since {lines[1] if len(lines) > 1 else '?'}"
        except OSError:
            pass
        raise InteractiveLockError(
            f"propose_decision -i already running ({holder}). "
            f"Lock: {path}. Remove only if that process is dead."
        ) from e
    try:
        os.write(fd, f"{os.getpid()}\n{_now_iso()}\n".encode())
        os.close(fd)
        yield path
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def collect_interactive_fields(
    *,
    relates_to: str = "",
    summary: str = "",
    rationale: str = "",
    author: str = "",
    domain: str = "coding.tooling",
    site: str = "",
    constraints: list[str] | None = None,
    prompt,
) -> dict:
    """Prompt for proposal fields one at a time (npm init style)."""
    rt = relates_to.strip() or prompt(
        "relates_to (parent decision or observation id, e.g. dec_prop_...)"
    ).strip()
    sm = summary.strip() or prompt("summary (one sentence)").strip()
    ra = rationale.strip() or prompt("rationale (why this choice)").strip()
    au = author.strip() or prompt("author", default="cursor-session").strip()
    dom = domain.strip() or prompt("domain", default="coding.tooling").strip()
    st = site.strip() if site else prompt("site (optional, press Enter to skip)", default="").strip()
    cons = list(constraints or [])
    if not cons:
        first = prompt(
            "constraint (required; use 'none-identified' when none)", default=""
        ).strip()
        if not first:
            raise ValueError(
                "--constraint is required; use 'none-identified' when none are identified"
            )
        cons.append(first)
    while True:
        extra = prompt(
            "additional constraint (optional, press Enter when done)", default=""
        ).strip()
        if not extra:
            break
        cons.append(extra)
    return {
        "relates_to": rt,
        "summary": sm,
        "rationale": ra,
        "author": au,
        "domain": dom or "coding.tooling",
        "site": st,
        "constraints": _normalize_constraints(cons),
    }


def interactive_submit_snapshot(cfg: dict) -> dict:
    """Fresh brief + queue state immediately before interactive submit."""
    from brief import gather_brief_data

    data = gather_brief_data(cfg, with_tests=False)
    pending = list_proposals(cfg)
    stale = data.get("handoff_staleness") or {}
    return {
        "brief_at": data.get("generated_at", "?"),
        "stale_handoff": bool(stale.get("stale")),
        "stale_file": stale.get("newest_file"),
        "pending": pending,
    }


def confirm_interactive_submit(
    cfg: dict,
    fields: dict,
    *,
    confirm,
    echo,
) -> bool:
    """Show fresh state and ask before writing the proposal."""
    snap = interactive_submit_snapshot(cfg)
    echo("\n--- Submit check (fresh state) ---")
    echo(f"brief @ {snap['brief_at']}")
    if snap["stale_handoff"]:
        echo(f"STALE HANDOFF: LATEST.md older than {snap.get('stale_file')}")
    echo(f"Pending drafts in queue: {len(snap['pending'])}")
    for row in snap["pending"][:5]:
        echo(f"  - {row.get('id')}: {row.get('summary', '')[:60]}")
    echo(f"Your summary: {fields['summary']}")
    echo(f"  relates_to: {fields['relates_to']}")
    echo(f"  author: {fields['author']}")
    return bool(confirm("Save this draft?", default=True))
