"""Complete-data restore policy — closed StateSpec matrix, evidence, reports.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-correction-v2.md
Validators classify only; they never repair. Capture evidence is not authority
and is never a repair source.
"""

# The closed restore matrix intentionally lives in one auditable policy module.
# Validator/capture boundaries classify arbitrary corruption instead of leaking it.
# pylint: disable=too-many-lines,broad-exception-caught

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from atomic_files import atomic_write_json, atomic_write_text
from conflict_events import reduce_events, unresolved
from ledger_content_hash import ledger_content_hash
from shadow_ledger import manifest_is_complete

# ---------------------------------------------------------------------------
# Outcomes / exits
# ---------------------------------------------------------------------------
OUTCOME_VALID = "VALID"
OUTCOME_ADVISORY = "ADVISORY"
OUTCOME_REPAIRABLE = "REPAIRABLE"
OUTCOME_BLOCKED = "BLOCKED"

OUTCOME_RANK = {
    OUTCOME_VALID: 0,
    OUTCOME_ADVISORY: 1,
    OUTCOME_REPAIRABLE: 2,
    OUTCOME_BLOCKED: 3,
}

EXIT_VALID = 0
EXIT_REPAIRABLE_DRIFT = 30
EXIT_BLOCKED = 31
EXIT_INTERNAL_FAILURE = 32

CODE_BLOCKED_SNAPSHOT_SCOPE_LEAK = "BLOCKED_SNAPSHOT_SCOPE_LEAK"
CODE_BLOCKED_UNCLASSIFIED_STATE = "BLOCKED_UNCLASSIFIED_STATE"
CODE_EVIDENCE_SKEW = "EVIDENCE_MID_CAPTURE_SKEW"

EVIDENCE_FILENAME = ".convmem-backup-evidence.json"
EVIDENCE_SCHEMA_VERSION = 1

REQUIRED_CHROMA_COLLECTIONS = ("knowledge_units", "conversation_summaries")

_APPROVED_REQUIRED = ("kind", "status", "summary", "rationale")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256_bytes(raw.encode("utf-8"))


def _normalize_root(path: Path | str) -> Path:
    return Path(path).expanduser().resolve()


def worse_outcome(a: str, b: str) -> str:
    return a if OUTCOME_RANK.get(a, -1) >= OUTCOME_RANK.get(b, -1) else b


# ---------------------------------------------------------------------------
# Classification / StateSpec
# ---------------------------------------------------------------------------
@dataclass
class Classification:
    path: str
    authority: str
    outcome: str
    detail: str = ""
    repair_source: str = ""
    code: str = ""
    evidence_comparison: dict[str, Any] | None = None


@dataclass(frozen=True)
class StateSpec:
    path: str
    authority: str
    presence: str
    validator: Callable[["RestoreContext"], Classification]
    missing_outcome: str
    repair_source: str


@dataclass
class InventoryResult:
    classifications: list[Classification] = field(default_factory=list)
    overall: str = OUTCOME_VALID
    exit_code: int = EXIT_VALID
    evidence: dict[str, Any] | None = None
    evidence_comparisons: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RestoreContext:
    """Read-only view of a restored (or live-for-capture) data root."""

    root: Path
    expected_data_root: Path | None = None
    evidence: dict[str, Any] | None = None
    # Validators must never mutate this; tests assert no writes beyond reports.
    allow_writes: bool = False


# ---------------------------------------------------------------------------
# Shared parsers / fingerprints
# ---------------------------------------------------------------------------
def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL {path.name} line {number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"non-object JSONL {path.name} line {number}")
        rows.append(row)
    return rows


def _ledger_id_of(record: Mapping[str, Any]) -> str:
    raw = record.get("ledger_id") or record.get("id") or ""
    return str(raw).strip()


def _proposal_linkage(record: Mapping[str, Any]) -> str:
    pid = str(record.get("proposal_id") or "").strip()
    if pid:
        return pid
    lid = _ledger_id_of(record)
    if lid.startswith("dec_prop_"):
        return lid
    return ""


def chroma_logical_snapshot(chroma_dir: Path) -> dict[str, Any]:
    """SQLite-level Chroma fingerprint (no chromadb dependency)."""
    db = chroma_dir / "chroma.sqlite3"
    if not db.is_file():
        raise ValueError("chroma.sqlite3 missing")
    uri = f"file:{db}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()
        quick = cur.execute("PRAGMA quick_check").fetchone()
        if not quick or str(quick[0]).lower() != "ok":
            raise ValueError(f"sqlite quick_check failed: {quick}")

        names = {
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "collections" not in names:
            raise ValueError("collections table missing")

        collections = {
            str(name): str(cid)
            for cid, name in cur.execute("SELECT id, name FROM collections").fetchall()
        }
        missing = [c for c in REQUIRED_CHROMA_COLLECTIONS if c not in collections]
        if missing:
            raise ValueError(f"missing required collections: {missing}")

        per_collection: dict[str, Any] = {}
        for coll_name, coll_id in sorted(collections.items()):
            if "segments" in names and "embeddings" in names:
                ids = [
                    str(r[0])
                    for r in cur.execute(
                        """
                        SELECT e.embedding_id
                        FROM embeddings e
                        JOIN segments s ON e.segment_id = s.id
                        WHERE s.collection = ?
                        ORDER BY e.embedding_id
                        """,
                        (coll_id,),
                    ).fetchall()
                ]
            else:
                ids = []
            per_collection[coll_name] = {
                "collection_id": coll_id,
                "count": len(ids),
                "ids_sha256": _canonical_json_hash(ids),
                "ids": ids,
            }
        fingerprint = _canonical_json_hash(
            {
                name: {
                    "count": info["count"],
                    "ids_sha256": info["ids_sha256"],
                }
                for name, info in per_collection.items()
            }
        )
        # Drop full ID lists from returned summary (keep hashes/counts).
        summary = {
            name: {
                "collection_id": info["collection_id"],
                "count": info["count"],
                "ids_sha256": info["ids_sha256"],
            }
            for name, info in per_collection.items()
        }
        return {
            "collections": summary,
            "logical_fingerprint": fingerprint,
            "required_present": True,
            # Retain IDs only for required collections (evidence compare / export).
            "required_ids": {
                name: per_collection[name]["ids"] for name in REQUIRED_CHROMA_COLLECTIONS
            },
        }
    finally:
        conn.close()


def pending_lifecycle_fingerprint(events: Sequence[Mapping[str, Any]]) -> str:
    states = reduce_events([dict(e) for e in events])
    projection = {
        pid: {
            "lifecycle_state": st["lifecycle_state"],
            "active_conflicts": sorted(st.get("active_conflicts") or []),
        }
        for pid, st in sorted(states.items())
    }
    return _canonical_json_hash(projection)


def derived_export_fingerprint(path: Path) -> dict[str, Any]:
    rows = _read_jsonl(path)
    ids: list[str] = []
    for row in rows:
        uid = str(row.get("id") or row.get("unit_id") or "").strip()
        if uid:
            ids.append(uid)
    ids_sorted = sorted(set(ids))
    return {
        "count": len(ids_sorted),
        "ids_sha256": _canonical_json_hash(ids_sorted),
        "byte_sha256": _sha256_file(path) if path.is_file() else "",
        "ids": ids_sorted,
    }


def writer_census_for_root(root: Path) -> dict[str, str]:
    """Classify each top-level name by closed StateSpec authority family."""
    by_path = {spec.path: spec for spec in STATE_SPECS}
    census: dict[str, str] = {}
    if not root.is_dir():
        return census
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        name = child.name
        if name in by_path:
            census[name] = by_path[name].authority
        elif name.startswith(".") and name != EVIDENCE_FILENAME:
            census[name] = "ephemeral_or_hidden"
        elif name.endswith(".lock"):
            census[name] = "ephemeral_lock"
        else:
            census[name] = "unclassified"
    return census


# ---------------------------------------------------------------------------
# Evidence capture
# ---------------------------------------------------------------------------
def build_backup_evidence(data_root: Path | str) -> dict[str, Any]:
    """Construct capture evidence dict (does not write)."""
    root = _normalize_root(data_root)
    canonical_hashes: dict[str, str] = {}
    for rel in (
        "decisions-approved.jsonl",
        "pending_decision_events.jsonl",
        "pending_decisions.jsonl",
        "knowledge_units.jsonl",
        "processed.json",
        "inventory.jsonl",
        "hash_schema_deploy.json",
        "hash_schema_migration_report.json",
    ):
        p = root / rel
        if p.is_file():
            canonical_hashes[rel] = _sha256_file(p)

    approved_ids: list[str] = []
    approved_linkage: dict[str, str] = {}
    approved = root / "decisions-approved.jsonl"
    if approved.is_file():
        try:
            for row in _read_jsonl(approved):
                lid = _ledger_id_of(row)
                if lid:
                    approved_ids.append(lid)
                    approved_linkage[lid] = _proposal_linkage(row)
        except Exception:  # pylint: disable=broad-exception-caught
            approved_ids = []
            approved_linkage = {}

    pending_fp = ""
    events_path = root / "pending_decision_events.jsonl"
    if events_path.is_file():
        try:
            events = _read_jsonl(events_path)
            pending_fp = pending_lifecycle_fingerprint(events)
        except Exception:  # pylint: disable=broad-exception-caught
            pending_fp = ""

    chroma_info: dict[str, Any] = {}
    chroma_dir = root / "chroma"
    if chroma_dir.is_dir():
        try:
            snap = chroma_logical_snapshot(chroma_dir)
            chroma_info = {
                "collections": snap["collections"],
                "logical_fingerprint": snap["logical_fingerprint"],
                "required_ids_sha256": {
                    name: _canonical_json_hash(snap["required_ids"][name])
                    for name in REQUIRED_CHROMA_COLLECTIONS
                },
                "required_counts": {
                    name: snap["collections"][name]["count"]
                    for name in REQUIRED_CHROMA_COLLECTIONS
                },
            }
        except Exception as exc:  # noqa: BLE001 — capture is best-effort
            # pylint: disable=broad-exception-caught
            chroma_info = {"capture_error": str(exc)}

    export_info: dict[str, Any] = {}
    export_path = root / "knowledge_units.jsonl"
    if export_path.is_file():
        try:
            exp = derived_export_fingerprint(export_path)
            export_info = {
                "count": exp["count"],
                "ids_sha256": exp["ids_sha256"],
                "byte_sha256": exp["byte_sha256"],
            }
        except Exception as exc:  # noqa: BLE001
            # pylint: disable=broad-exception-caught
            export_info = {"capture_error": str(exc)}

    top_level = sorted(p.name for p in root.iterdir()) if root.is_dir() else []

    return {
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "captured_at": _utc_now(),
        "normalized_data_root": str(root),
        "canonical_byte_hashes": canonical_hashes,
        "approved_decision_ids": approved_ids,
        "approved_proposal_linkage": approved_linkage,
        "pending_event_lifecycle_fingerprint": pending_fp,
        "chroma": chroma_info,
        "derived_export": export_info,
        "top_level_inventory": top_level,
        "writer_census": writer_census_for_root(root),
        # Explicit non-authority marker for consumers / reports.
        "authority": False,
        "repair_source": False,
    }


def capture_backup_evidence(data_root: Path | str) -> dict[str, Any]:
    """Atomically publish ``.convmem-backup-evidence.json`` inside data root."""
    root = _normalize_root(data_root)
    evidence = build_backup_evidence(root)
    dest = root / EVIDENCE_FILENAME
    atomic_write_json(dest, evidence, indent=2, sort_keys=True)
    return evidence


def load_backup_evidence(root: Path) -> dict[str, Any] | None:
    path = root / EVIDENCE_FILENAME
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("evidence file is not an object")
    return data


# ---------------------------------------------------------------------------
# Validators (never repair)
# ---------------------------------------------------------------------------
def _missing(spec: StateSpec, detail: str = "missing") -> Classification:
    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=spec.missing_outcome,
        detail=detail,
        repair_source=spec.repair_source if spec.missing_outcome == OUTCOME_REPAIRABLE else "",
    )


def _validate_chroma(ctx: RestoreContext) -> Classification:
    spec = _spec("chroma")
    chroma_dir = ctx.root / "chroma"
    if not chroma_dir.is_dir():
        return _missing(spec, "chroma directory missing")
    try:
        snap = chroma_logical_snapshot(chroma_dir)
    except Exception as exc:  # noqa: BLE001 — classify, do not repair
        # pylint: disable=broad-exception-caught
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"Chroma validation failed: {exc}",
        )

    comparison: dict[str, Any] | None = None
    outcome = OUTCOME_VALID
    detail = (
        f"collections={sorted(snap['collections'])} "
        f"fingerprint={snap['logical_fingerprint'][:12]}"
    )
    if ctx.evidence and isinstance(ctx.evidence.get("chroma"), dict):
        ev = ctx.evidence["chroma"]
        mismatches: list[str] = []
        if ev.get("logical_fingerprint") and ev["logical_fingerprint"] != snap[
            "logical_fingerprint"
        ]:
            mismatches.append("logical_fingerprint")
        for name in REQUIRED_CHROMA_COLLECTIONS:
            ev_count = (ev.get("required_counts") or {}).get(name)
            got = snap["collections"][name]["count"]
            if ev_count is not None and int(ev_count) != got:
                mismatches.append(f"count:{name}")
            ev_ids = (ev.get("required_ids_sha256") or {}).get(name)
            got_ids = _canonical_json_hash(snap["required_ids"][name])
            if ev_ids and ev_ids != got_ids:
                mismatches.append(f"ids:{name}")
        comparison = {
            "code": CODE_EVIDENCE_SKEW if mismatches else "EVIDENCE_MATCH",
            "mismatches": mismatches,
            "evidence_is_authority": False,
        }
        if mismatches:
            outcome = worse_outcome(outcome, OUTCOME_REPAIRABLE)
            detail = f"evidence skew visible: {mismatches}"
            # Evidence never repairs; skew is visible classification only.
            # Mid-capture skew on Tier-1 is reported as REPAIRABLE visibility
            # only when Chroma itself is structurally valid — operators decide.
            # Architecture: evidence comparison on restore; skew becomes visible.
            # Prefer ADVISORY for pure evidence skew without structural damage?
            # VERIFY V6b: mid-capture skew becomes visible classification.
            outcome = OUTCOME_ADVISORY
            detail = f"mid-capture skew visible (not authority): {mismatches}"

    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=outcome,
        detail=detail,
        evidence_comparison=comparison,
    )


def _validate_approved(ctx: RestoreContext) -> Classification:
    spec = _spec("decisions-approved.jsonl")
    path = ctx.root / spec.path
    if not path.is_file():
        return _missing(spec, "file missing")
    try:
        rows = _read_jsonl(path)
    except ValueError as exc:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=str(exc),
        )

    seen: set[str] = set()
    linkage: dict[str, str] = {}
    content_hashes: dict[str, str] = {}
    for row in rows:
        lid = _ledger_id_of(row)
        if not lid:
            return Classification(
                path=spec.path,
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail="record missing ledger_id/id",
            )
        if lid in seen:
            return Classification(
                path=spec.path,
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail=f"duplicate ledger_id: {lid}",
            )
        seen.add(lid)
        for required_field in _APPROVED_REQUIRED:
            if required_field == "kind":
                if not (
                    row.get("kind")
                    or row.get("ledger_kind")
                    or row.get("type")
                ):
                    return Classification(
                        path=spec.path,
                        authority=spec.authority,
                        outcome=OUTCOME_BLOCKED,
                        detail=f"{lid} missing kind",
                    )
            elif required_field not in row or row.get(required_field) in (None, ""):
                return Classification(
                    path=spec.path,
                    authority=spec.authority,
                    outcome=OUTCOME_BLOCKED,
                    detail=f"{lid} missing {required_field}",
                )
        link = _proposal_linkage(row)
        if lid.startswith("dec_") and not link:
            return Classification(
                path=spec.path,
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail=f"{lid} missing proposal linkage",
            )
        linkage[lid] = link
        content_hashes[lid] = ledger_content_hash(dict(row))

    byte_hash = _sha256_file(path)
    comparison = None
    outcome = OUTCOME_VALID
    detail = f"{len(seen)} decision(s) byte={byte_hash[:12]}"
    if ctx.evidence:
        mismatches: list[str] = []
        ev_ids = list(ctx.evidence.get("approved_decision_ids") or [])
        if sorted(ev_ids) != sorted(seen):
            mismatches.append("approved_decision_ids")
        ev_link = ctx.evidence.get("approved_proposal_linkage") or {}
        if dict(ev_link) != linkage:
            mismatches.append("proposal_linkage")
        ev_byte = (ctx.evidence.get("canonical_byte_hashes") or {}).get(spec.path)
        if ev_byte and ev_byte != byte_hash:
            mismatches.append("byte_hash")
        comparison = {
            "code": CODE_EVIDENCE_SKEW if mismatches else "EVIDENCE_MATCH",
            "mismatches": mismatches,
            "content_hashes_sample": list(content_hashes.items())[:3],
            "evidence_is_authority": False,
        }
        if mismatches:
            outcome = OUTCOME_ADVISORY
            detail = f"mid-capture skew visible: {mismatches}"

    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=outcome,
        detail=detail,
        evidence_comparison=comparison,
    )


def _validate_pending_events(ctx: RestoreContext) -> Classification:
    spec = _spec("pending_decision_events.jsonl")
    path = ctx.root / spec.path
    if not path.is_file():
        return _missing(spec, "file missing (empty lifecycle)")
    try:
        events = _read_jsonl(path)
        fp = pending_lifecycle_fingerprint(events)
        # Force reducer to run for corruption detection.
        reduce_events(events)
    except Exception as exc:  # noqa: BLE001
        # pylint: disable=broad-exception-caught
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"pending events invalid: {exc}",
        )

    outcome = OUTCOME_VALID
    detail = f"{len(events)} event(s) lifecycle_fp={fp[:12]}"
    comparison = None
    if ctx.evidence:
        ev_fp = ctx.evidence.get("pending_event_lifecycle_fingerprint") or ""
        mismatch = bool(ev_fp and ev_fp != fp)
        comparison = {
            "code": CODE_EVIDENCE_SKEW if mismatch else "EVIDENCE_MATCH",
            "mismatches": ["pending_event_lifecycle_fingerprint"] if mismatch else [],
            "evidence_is_authority": False,
        }
        if mismatch:
            outcome = OUTCOME_ADVISORY
            detail = "mid-capture skew visible: pending lifecycle fingerprint"
    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=outcome,
        detail=detail,
        evidence_comparison=comparison,
    )


def _validate_pending_projection(ctx: RestoreContext) -> Classification:
    spec = _spec("pending_decisions.jsonl")
    path = ctx.root / spec.path
    events_path = ctx.root / "pending_decision_events.jsonl"
    if not path.is_file():
        return _missing(spec, "absent (normal when no projection)")

    try:
        rows = _read_jsonl(path)
    except ValueError as exc:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"projection corrupt: {exc}",
        )

    try:
        events = _read_jsonl(events_path) if events_path.is_file() else []
        states = reduce_events(events) if events else {}
        active = unresolved(states)
    except Exception as exc:  # noqa: BLE001
        # pylint: disable=broad-exception-caught
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"cannot reduce events for projection compare: {exc}",
        )

    proj_ids = {
        str(r.get("id") or r.get("proposal_id") or "").strip()
        for r in rows
        if str(r.get("id") or r.get("proposal_id") or "").strip()
    }
    # Orphan projection rows (no event history) or orphan events still active
    # without projection — architecture: orphan/conflict/corruption blocks;
    # ordinary drift is repairable.
    event_ids = set(states)
    orphans_proj = sorted(pid for pid in proj_ids if pid and pid not in event_ids)
    # Conflict: same proposal with active_conflicts
    conflicts = sorted(
        pid
        for pid, st in states.items()
        if st.get("active_conflicts")
    )
    if orphans_proj or conflicts:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=(
                f"orphan_projection={orphans_proj[:5]} conflicts={conflicts[:5]}"
            ),
            repair_source="",
        )

    active_ids = set(active)
    # Drift: projection set != unresolved active set → repairable from events.
    if proj_ids != active_ids and (proj_ids or active_ids):
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_REPAIRABLE,
            detail=(
                f"projection drift proj={len(proj_ids)} active={len(active_ids)}"
            ),
            repair_source=spec.repair_source,
        )

    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=OUTCOME_VALID,
        detail=f"{len(proj_ids)} projection row(s) match reducer",
        repair_source=spec.repair_source,
    )


def _validate_derived_export(ctx: RestoreContext) -> Classification:
    spec = _spec("knowledge_units.jsonl")
    path = ctx.root / spec.path
    if not path.is_file():
        return _missing(spec, "missing — regeneratable from Chroma")

    try:
        exp = derived_export_fingerprint(path)
    except ValueError as exc:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"export corrupt: {exc}",
        )

    chroma_dir = ctx.root / "chroma"
    comparison: dict[str, Any] | None = None
    outcome = OUTCOME_VALID
    detail = f"count={exp['count']} ids={exp['ids_sha256'][:12]}"
    repair = ""

    if chroma_dir.is_dir():
        try:
            snap = chroma_logical_snapshot(chroma_dir)
            chroma_ids = snap["required_ids"]["knowledge_units"]
            chroma_set = set(chroma_ids)
            export_set = set(exp["ids"])
            if chroma_set != export_set or len(chroma_ids) != exp["count"]:
                outcome = OUTCOME_REPAIRABLE
                repair = "Chroma"
                detail = (
                    f"export/Chroma drift export={exp['count']} "
                    f"chroma={len(chroma_ids)} (Chroma is named repair source)"
                )
            comparison = {
                "chroma_count": len(chroma_ids),
                "export_count": exp["count"],
                "ids_match": chroma_set == export_set,
                "named_repair_source": "Chroma" if chroma_set != export_set else "",
                "evidence_is_authority": False,
            }
        except Exception as exc:  # noqa: BLE001
            # pylint: disable=broad-exception-caught
            # Cannot deterministically name Chroma as repair source.
            outcome = OUTCOME_BLOCKED
            detail = f"export present but Chroma unreadable for compare: {exc}"
            repair = ""

    if ctx.evidence and isinstance(ctx.evidence.get("derived_export"), dict):
        ev = ctx.evidence["derived_export"]
        mismatches = []
        if ev.get("ids_sha256") and ev["ids_sha256"] != exp["ids_sha256"]:
            mismatches.append("ids_sha256")
        if ev.get("count") is not None and int(ev["count"]) != exp["count"]:
            mismatches.append("count")
        if mismatches:
            outcome = worse_outcome(outcome, OUTCOME_ADVISORY)
            detail = f"{detail}; evidence skew: {mismatches}"
            comparison = {
                **(comparison or {}),
                "evidence_code": CODE_EVIDENCE_SKEW,
                "evidence_mismatches": mismatches,
                "evidence_is_authority": False,
            }

    # Missing-vs-present already REPAIRABLE via missing_outcome; present matching
    # Chroma is VALID; drift REPAIRABLE with Chroma named only when deterministic.
    if outcome == OUTCOME_VALID and not path.is_file():
        outcome = OUTCOME_REPAIRABLE
        repair = "Chroma"

    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=outcome,
        detail=detail,
        repair_source=repair,
        evidence_comparison=comparison,
    )


def _validate_processed(ctx: RestoreContext) -> Classification:
    spec = _spec("processed.json")
    path = ctx.root / spec.path
    if not path.is_file():
        return _missing(spec, "missing — rebuild via source rescan")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"invalid JSON: {exc}",
        )
    if not isinstance(data, dict):
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail="processed.json must be an object",
        )

    ambiguous = 0
    for entry in data.values():
        if not isinstance(entry, dict):
            ambiguous += 1
            continue
        if "excluded" in entry:
            flag = entry.get("excluded")
            if flag is not True and flag is not False:
                ambiguous += 1
            elif flag is True and not str(entry.get("path") or "").strip():
                ambiguous += 1
    if ambiguous:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"ambiguous exclusion markers: {ambiguous}",
        )

    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=OUTCOME_REPAIRABLE,
        detail=f"{len(data)} entries — ordinary rescan drift",
        repair_source=spec.repair_source,
    )


def _validate_queue(path_name: str) -> Callable[[RestoreContext], Classification]:
    def _validator(ctx: RestoreContext) -> Classification:
        spec = _spec(path_name)
        path = ctx.root / path_name
        if not path.is_file():
            return _missing(spec, "absent")
        try:
            rows = _read_jsonl(path)
        except ValueError as exc:
            return Classification(
                path=spec.path,
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail=f"unrecoverable intent (parse): {exc}",
            )
        bad = 0
        for row in rows:
            # Referenced identities: unit/source/path-ish fields when present.
            identity = (
                row.get("id")
                or row.get("unit_id")
                or row.get("source_path")
                or row.get("path")
                or row.get("hash")
                or row.get("content_hash")
            )
            if identity in (None, ""):
                # Empty identity with other keys → unrecoverable intent.
                if row:
                    bad += 1
        if bad:
            return Classification(
                path=spec.path,
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail=f"unrecoverable intent: {bad} row(s) lack referenced identity",
            )
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_REPAIRABLE,
            detail=f"{len(rows)} row(s) — stale derived rows repairable",
            repair_source=spec.repair_source,
        )

    return _validator


def _validate_inventory(ctx: RestoreContext) -> Classification:
    spec = _spec("inventory.jsonl")
    path = ctx.root / spec.path
    if not path.is_file():
        return _missing(spec, "missing")
    try:
        rows = _read_jsonl(path)
    except ValueError as exc:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=str(exc),
        )
    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=OUTCOME_REPAIRABLE,
        detail=f"{len(rows)} inventory row(s)",
        repair_source=spec.repair_source,
    )


def _validate_imports(ctx: RestoreContext) -> Classification:
    spec = _spec("imports")
    path = ctx.root / "imports"
    if not path.exists():
        return _missing(spec, "absent")
    if not path.is_dir():
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail="imports is not a directory",
        )
    hashes: dict[str, str] = {}
    for child in sorted(path.rglob("*")):
        if not child.is_file():
            continue
        rel = str(child.relative_to(path))
        if child.suffix in {".sqlite3", ".db"}:
            uri = f"file:{child}?mode=ro"
            try:
                conn = sqlite3.connect(uri, uri=True)
                try:
                    quick = conn.execute("PRAGMA quick_check").fetchone()
                    if not quick or str(quick[0]).lower() != "ok":
                        return Classification(
                            path=spec.path,
                            authority=spec.authority,
                            outcome=OUTCOME_BLOCKED,
                            detail=f"sqlite integrity failed: {rel} ({quick})",
                        )
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                return Classification(
                    path=spec.path,
                    authority=spec.authority,
                    outcome=OUTCOME_BLOCKED,
                    detail=f"sqlite open failed: {rel}: {exc}",
                )
        hashes[rel] = _sha256_file(child)
    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=OUTCOME_ADVISORY,
        detail=f"{len(hashes)} import artifact(s) hashed",
    )


def _validate_authorizations(ctx: RestoreContext) -> Classification:
    spec = _spec("authorizations")
    path = ctx.root / "authorizations"
    if not path.exists():
        return _missing(spec, "absent")
    if not path.is_dir():
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail="authorizations is not a directory",
        )

    blocked: list[str] = []
    advisory: list[str] = []
    for grant_dir in sorted(p for p in path.rglob("*") if p.is_dir()):
        rel = str(grant_dir.relative_to(path))
        quarantined = (grant_dir / "QUARANTINED.txt").is_file()
        json_files = sorted(grant_dir.glob("*.json"))
        if not json_files:
            continue
        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                if quarantined:
                    advisory.append(f"{rel}/{jf.name}:malformed-quarantined")
                else:
                    blocked.append(f"{rel}/{jf.name}:malformed")
                continue
            if not isinstance(data, dict):
                blocked.append(f"{rel}/{jf.name}:non-object")
                continue
            status = str(data.get("status") or "").lower()
            phase = str(data.get("authorization_phase") or "")
            active = status in {"active", "authorized", "granted"} or (
                status == "" and not quarantined and phase in {"r2a", "r2b"}
            )
            # Historical / quarantined residue is advisory.
            if quarantined or status in {"historical", "expired", "revoked", "quarantined"}:
                advisory.append(f"{rel}/{jf.name}:{status or 'quarantined'}")
                continue
            # Active-ish grants: require phase + hash fields consistency.
            if active or status in {"", "ready"}:
                sha_sidecar = Path(str(jf) + ".approved.sha256")
                body_sha = _sha256_file(jf)
                declared = str(
                    data.get("ryan_approved_manifest_sha256")
                    or data.get("authorization_body_sha256")
                    or ""
                ).strip()
                if sha_sidecar.is_file():
                    side = sha_sidecar.read_text(encoding="utf-8").strip().split()[0]
                    if side and side != body_sha and (not declared or declared != side):
                        # Mismatch between sidecar and bytes.
                        if declared and declared != body_sha:
                            blocked.append(f"{rel}/{jf.name}:hash-mismatch")
                        elif side != body_sha and not declared:
                            # Sidecar may store approved digest of different object;
                            # treat explicit mismatch against declared only.
                            pass
                if declared and declared != body_sha and len(declared) == 64:
                    # Declared hash must match file bytes for active grants.
                    blocked.append(f"{rel}/{jf.name}:declared-hash-mismatch")
                if phase and phase not in {"r2a", "r2b"}:
                    blocked.append(f"{rel}/{jf.name}:bad-phase")
            else:
                advisory.append(f"{rel}/{jf.name}:{status or 'unknown'}")

    if blocked:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"active grant problems: {blocked[:5]}",
        )
    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=OUTCOME_ADVISORY if advisory else OUTCOME_VALID,
        detail=(
            f"advisory residue={len(advisory)}" if advisory else "no active grants"
        ),
    )


def _validate_shadow(ctx: RestoreContext) -> Classification:
    spec = _spec("shadow_ledger.jsonl")
    ledger = ctx.root / "shadow_ledger.jsonl"
    # Phase0 default path name is shadow_activation.json; also accept
    # shadow_activation_manifest.json from earlier sketches.
    manifest_path = ctx.root / "shadow_activation.json"
    if not manifest_path.is_file():
        alt = ctx.root / "shadow_activation_manifest.json"
        if alt.is_file():
            manifest_path = alt
    health = ctx.root / "shadow_health.json"

    absent = not ledger.is_file() and not manifest_path.is_file() and not health.is_file()
    if absent:
        return Classification(
            path="shadow/",
            authority=spec.authority,
            outcome=OUTCOME_VALID,
            detail="absent/disabled (normal Phase 0 default)",
        )

    manifest: dict[str, Any] | None = None
    manifest_error = ""
    if manifest_path.is_file():
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("manifest not an object")
            manifest = raw
        except (json.JSONDecodeError, ValueError) as exc:
            manifest_error = str(exc)

    # Determine active vs inactive.
    active = False
    if manifest:
        if "active" in manifest:
            active = bool(manifest.get("active"))
        elif manifest.get("completion_status") == "complete":
            active = True

    if manifest_error:
        if active:
            return Classification(
                path="shadow/",
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail=f"active shadow manifest corrupt: {manifest_error}",
            )
        return Classification(
            path="shadow/",
            authority=spec.authority,
            outcome=OUTCOME_ADVISORY,
            detail=f"inactive malformed manifest: {manifest_error}",
        )

    if not active:
        # Inactive residue — malformed pieces are advisory only.
        if manifest is not None and not manifest_is_complete(manifest):
            return Classification(
                path="shadow/",
                authority=spec.authority,
                outcome=OUTCOME_ADVISORY,
                detail="inactive incomplete/malformed residue",
            )
        return Classification(
            path="shadow/",
            authority=spec.authority,
            outcome=OUTCOME_ADVISORY,
            detail="inactive shadow residue (non-authoritative)",
        )

    # Active shadow: incomplete / mismatched / corrupt control blocks.
    if not manifest_is_complete(manifest):
        return Classification(
            path="shadow/",
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail="active incomplete activation manifest",
        )
    if not ledger.is_file():
        return Classification(
            path="shadow/",
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail="active shadow missing ledger file",
        )
    try:
        _read_jsonl(ledger)
    except ValueError as exc:
        return Classification(
            path="shadow/",
            authority=spec.authority,
            outcome=OUTCOME_BLOCKED,
            detail=f"active shadow ledger corrupt: {exc}",
        )

    # Chroma root mismatch if declared.
    declared_root = str((manifest or {}).get("chroma_root") or "").strip()
    if declared_root:
        try:
            if _normalize_root(declared_root) != _normalize_root(ctx.root / "chroma"):
                return Classification(
                    path="shadow/",
                    authority=spec.authority,
                    outcome=OUTCOME_BLOCKED,
                    detail="active shadow chroma_root mismatch",
                )
        except OSError:
            return Classification(
                path="shadow/",
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail="active shadow chroma_root unresolvable",
            )

    return Classification(
        path="shadow/",
        authority=spec.authority,
        outcome=OUTCOME_ADVISORY,
        detail="active shadow present — non-authoritative; never a repair source",
    )


def _validate_forbidden_scratch(name: str) -> Callable[[RestoreContext], Classification]:
    def _validator(ctx: RestoreContext) -> Classification:
        spec = _spec(name)
        path = ctx.root / name
        if path.exists():
            return Classification(
                path=f"{name}/",
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail="scratch path must not appear in snapshot contents",
                code=CODE_BLOCKED_SNAPSHOT_SCOPE_LEAK,
            )
        return Classification(
            path=f"{name}/",
            authority=spec.authority,
            outcome=OUTCOME_VALID,
            detail="absent (required)",
        )

    return _validator


def _validate_optional_json(
    path_name: str, *, authority: str | None = None
) -> Callable[[RestoreContext], Classification]:
    def _validator(ctx: RestoreContext) -> Classification:
        spec = _spec(path_name)
        path = ctx.root / path_name
        if not path.is_file():
            return _missing(spec, "absent")
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return Classification(
                path=spec.path,
                authority=authority or spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail=f"invalid JSON: {exc}",
            )
        return Classification(
            path=spec.path,
            authority=authority or spec.authority,
            outcome=OUTCOME_VALID,
            detail="parseable",
        )

    return _validator


def _validate_advisory_present(path_name: str) -> Callable[[RestoreContext], Classification]:
    def _validator(ctx: RestoreContext) -> Classification:
        spec = _spec(path_name)
        path = ctx.root / path_name
        if not path.exists():
            return _missing(spec, "absent")
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_ADVISORY,
            detail="present for investigation",
        )

    return _validator


def _validate_ephemeral(path_name: str) -> Callable[[RestoreContext], Classification]:
    def _validator(ctx: RestoreContext) -> Classification:
        spec = _spec(path_name)
        path = ctx.root / path_name
        if not path.exists():
            return _missing(spec, "absent")
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_VALID,
            detail="ephemeral/operational — not durable authority",
        )

    return _validator


def _validate_evidence_sidecar(ctx: RestoreContext) -> Classification:
    spec = _spec(EVIDENCE_FILENAME)
    path = ctx.root / EVIDENCE_FILENAME
    if not path.is_file():
        return _missing(spec, "absent")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not an object")
        if data.get("authority") is True or data.get("repair_source") is True:
            return Classification(
                path=spec.path,
                authority=spec.authority,
                outcome=OUTCOME_BLOCKED,
                detail="evidence file illegally claims authority/repair_source",
            )
    except (json.JSONDecodeError, ValueError) as exc:
        return Classification(
            path=spec.path,
            authority=spec.authority,
            outcome=OUTCOME_ADVISORY,
            detail=f"evidence unreadable: {exc}",
        )
    return Classification(
        path=spec.path,
        authority=spec.authority,
        outcome=OUTCOME_ADVISORY,
        detail="capture evidence present (not authority, not repair source)",
    )


# ---------------------------------------------------------------------------
# Closed StateSpec table
# ---------------------------------------------------------------------------
def _noop_missing_valid(_ctx: RestoreContext) -> Classification:
    return Classification("?", "?", OUTCOME_VALID, "unused")


STATE_SPECS: tuple[StateSpec, ...] = (
    StateSpec("chroma", "tier1_authoritative", "required", _validate_chroma, OUTCOME_BLOCKED, ""),
    StateSpec(
        "decisions-approved.jsonl",
        "canonical_decisions",
        "required",
        _validate_approved,
        OUTCOME_BLOCKED,
        "",
    ),
    StateSpec(
        "pending_decision_events.jsonl",
        "canonical_control",
        "optional",
        _validate_pending_events,
        OUTCOME_ADVISORY,
        "",
    ),
    StateSpec(
        "pending_decisions.jsonl",
        "compatibility_projection",
        "optional",
        _validate_pending_projection,
        OUTCOME_VALID,
        "Pending event log",
    ),
    StateSpec(
        "knowledge_units.jsonl",
        "derived_export",
        "derived",
        _validate_derived_export,
        OUTCOME_REPAIRABLE,
        "Chroma",
    ),
    StateSpec(
        "processed.json",
        "mixed_incremental_sidecar",
        "optional",
        _validate_processed,
        OUTCOME_REPAIRABLE,
        "Source rescan",
    ),
    StateSpec(
        "dedupe_queue.jsonl",
        "conditional_operational_control",
        "optional",
        _validate_queue("dedupe_queue.jsonl"),
        OUTCOME_VALID,
        "Chroma",
    ),
    StateSpec(
        "link_queue.jsonl",
        "conditional_operational_control",
        "optional",
        _validate_queue("link_queue.jsonl"),
        OUTCOME_VALID,
        "Chroma",
    ),
    StateSpec(
        "ingest_duplicate_suppressions.jsonl",
        "conditional_operational_control",
        "optional",
        _validate_queue("ingest_duplicate_suppressions.jsonl"),
        OUTCOME_VALID,
        "Chroma",
    ),
    StateSpec(
        "inventory.jsonl",
        "source_inventory_cache",
        "optional",
        _validate_inventory,
        OUTCOME_REPAIRABLE,
        "Source rescan/reimport",
    ),
    StateSpec(
        "imports",
        "import_artifacts",
        "optional",
        _validate_imports,
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "authorizations",
        "conditional_authorization_control",
        "optional",
        _validate_authorizations,
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "shadow_ledger.jsonl",
        "non_authoritative_phase0",
        "optional",
        _validate_shadow,
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "shadow_activation.json",
        "non_authoritative_phase0",
        "optional",
        _validate_ephemeral("shadow_activation.json"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "shadow_activation_manifest.json",
        "non_authoritative_phase0",
        "optional",
        _validate_ephemeral("shadow_activation_manifest.json"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "shadow_health.json",
        "non_authoritative_phase0",
        "optional",
        _validate_ephemeral("shadow_health.json"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "hash_schema_deploy.json",
        "canonical_when_referenced",
        "optional",
        _validate_optional_json("hash_schema_deploy.json"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "hash_schema_migration_report.json",
        "canonical_when_referenced",
        "optional",
        _validate_optional_json("hash_schema_migration_report.json"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "attempts.jsonl",
        "operational_evidence",
        "optional",
        _validate_advisory_present("attempts.jsonl"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "index_failures.jsonl",
        "operational_evidence",
        "optional",
        _validate_advisory_present("index_failures.jsonl"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "synthesis_failures.jsonl",
        "operational_evidence",
        "optional",
        _validate_advisory_present("synthesis_failures.jsonl"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "refine_undo",
        "operational_evidence",
        "optional",
        _validate_advisory_present("refine_undo"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "refine_stats.json",
        "operational_evidence",
        "optional",
        _validate_advisory_present("refine_stats.json"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "brief.md",
        "operational_evidence",
        "optional",
        _validate_advisory_present("brief.md"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "digests",
        "operational_evidence",
        "optional",
        _validate_advisory_present("digests"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "logs",
        "operational_evidence",
        "optional",
        _validate_advisory_present("logs"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "eval",
        "operational_evidence",
        "optional",
        _validate_advisory_present("eval"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "integrity-check",
        "operational_evidence",
        "optional",
        _validate_advisory_present("integrity-check"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "locks",
        "ephemeral",
        "optional",
        _validate_ephemeral("locks"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "governed-ledger.lock",
        "ephemeral",
        "optional",
        _validate_ephemeral("governed-ledger.lock"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "worktrees",
        "forbidden_scratch",
        "forbidden_in_snapshot",
        _validate_forbidden_scratch("worktrees"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        "restore-drill",
        "forbidden_scratch",
        "forbidden_in_snapshot",
        _validate_forbidden_scratch("restore-drill"),
        OUTCOME_VALID,
        "",
    ),
    StateSpec(
        EVIDENCE_FILENAME,
        "capture_evidence_non_authority",
        "optional",
        _validate_evidence_sidecar,
        OUTCOME_ADVISORY,
        "",
    ),
)

# Additional glob-ish known names handled in inventory (suffix patterns).
_KNOWN_PREFIXES = (
    "dedupe_queue.jsonl.",
    "knowledge_units.jsonl.",
    "debug-",
    "deepseek-",
)
_KNOWN_EXACT_EXTRA = frozenset(
    {
        "mcp_crush_verified",
        "propose_interactive.lock",
        "refine.lock",
        "watch.lock",
        "processed.json.lock",
        "knowledge_units.jsonl.lock",
        "dedupe_queue.jsonl.lock",
        "ingest_duplicate_suppressions.jsonl.lock",
        "seed.txt",
    }
)


def _spec(path: str) -> StateSpec:
    for spec in STATE_SPECS:
        if spec.path == path:
            return spec
    raise KeyError(path)


def closed_state_spec_paths() -> tuple[str, ...]:
    return tuple(spec.path for spec in STATE_SPECS)


# ---------------------------------------------------------------------------
# Inventory orchestration
# ---------------------------------------------------------------------------
def inventory_restored_state(
    restored_root: Path | str,
    expected_data_root: Path | str | None = None,
    *,
    evidence: dict[str, Any] | None = None,
) -> InventoryResult:
    """Classify restored durable state via the closed StateSpec table."""
    result = InventoryResult()
    root = Path(restored_root)
    expected = (
        _normalize_root(expected_data_root)
        if expected_data_root is not None
        else None
    )

    if not root.is_dir():
        result.classifications.append(
            Classification(
                str(root),
                "missing",
                OUTCOME_BLOCKED,
                "restored root missing",
            )
        )
        result.overall = OUTCOME_BLOCKED
        result.exit_code = EXIT_BLOCKED
        return result

    loaded_evidence = evidence
    if loaded_evidence is None:
        try:
            loaded_evidence = load_backup_evidence(root)
        except (json.JSONDecodeError, ValueError):
            loaded_evidence = None
    result.evidence = loaded_evidence

    ctx = RestoreContext(
        root=root,
        expected_data_root=expected,
        evidence=loaded_evidence,
        allow_writes=False,
    )

    try:
        # Run closed table — one classification per StateSpec path.
        seen_paths: set[str] = set()
        for spec in STATE_SPECS:
            seen_paths.add(spec.path)
            path = root / spec.path
            # Shadow validator covers sibling files; skip redundant sibling specs
            # when the primary shadow validator already ran — still invoke each
            # closed-table row exactly once.
            if not path.exists() and spec.presence in {
                "optional",
                "derived",
                "forbidden_in_snapshot",
            }:
                # Still call validator (handles missing_outcome / forbidden).
                classification = spec.validator(ctx)
            elif not path.exists() and spec.presence == "required":
                classification = _missing(spec)
            else:
                classification = spec.validator(ctx)
            # Never allow validators to claim they repaired.
            result.classifications.append(classification)

        # Unknown top-level durable state.
        known = set(seen_paths) | set(_KNOWN_EXACT_EXTRA)
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            name = child.name
            if name in known:
                continue
            if name.endswith(".lock"):
                continue
            if name in _KNOWN_EXACT_EXTRA:
                result.classifications.append(
                    Classification(
                        name,
                        "operational_residue",
                        OUTCOME_ADVISORY,
                        "known operational/hermetic residue",
                    )
                )
                continue
            if any(name.startswith(prefix) for prefix in _KNOWN_PREFIXES):
                result.classifications.append(
                    Classification(
                        name,
                        "operational_residue",
                        OUTCOME_ADVISORY,
                        "known operational residue prefix",
                    )
                )
                continue
            if name.startswith(".") and name != EVIDENCE_FILENAME:
                result.classifications.append(
                    Classification(
                        name,
                        "ephemeral_or_hidden",
                        OUTCOME_ADVISORY,
                        "hidden path",
                    )
                )
                continue
            result.classifications.append(
                Classification(
                    name,
                    "unknown",
                    OUTCOME_BLOCKED,
                    "not in restore matrix — must be reviewed before replacement",
                    code=CODE_BLOCKED_UNCLASSIFIED_STATE,
                )
            )

        # Aggregate overall with precedence BLOCKED > REPAIRABLE > ADVISORY > VALID.
        overall = OUTCOME_VALID
        for c in result.classifications:
            # Treat special blocked codes as BLOCKED outcome.
            outcome = c.outcome
            if c.code in {
                CODE_BLOCKED_SNAPSHOT_SCOPE_LEAK,
                CODE_BLOCKED_UNCLASSIFIED_STATE,
            }:
                outcome = OUTCOME_BLOCKED
            if outcome == "BLOCKED_UNCLASSIFIED_STATE":
                outcome = OUTCOME_BLOCKED
            overall = worse_outcome(overall, outcome)
            if c.evidence_comparison:
                result.evidence_comparisons.append(
                    {"path": c.path, **c.evidence_comparison}
                )

        result.overall = overall
        if overall == OUTCOME_BLOCKED:
            result.exit_code = EXIT_BLOCKED
        elif overall == OUTCOME_REPAIRABLE:
            result.overall = "VALID_WITH_REPAIRABLE_DERIVED_DRIFT"
            result.exit_code = EXIT_REPAIRABLE_DRIFT
        else:
            # ADVISORY alone is still replacement-valid (exit 0) — advisory residue.
            result.exit_code = EXIT_VALID
            if overall == OUTCOME_ADVISORY:
                result.overall = "VALID_WITH_ADVISORY"
            else:
                result.overall = OUTCOME_VALID
        return result
    except Exception as exc:  # noqa: BLE001
        # pylint: disable=broad-exception-caught
        result.classifications.append(
            Classification(
                str(root),
                "internal",
                OUTCOME_BLOCKED,
                f"validator-internal failure: {exc}",
            )
        )
        result.overall = OUTCOME_BLOCKED
        result.exit_code = EXIT_INTERNAL_FAILURE
        return result


def locate_restored_data_root(
    target_dir: Path | str, expected_data_root: Path | str
) -> Path:
    """Find the restored data root under a restic --target directory."""
    target = Path(target_dir).expanduser().resolve()
    expected = _normalize_root(expected_data_root)
    direct = target / expected.relative_to(expected.anchor)
    # restic often restores absolute paths under target.
    candidate = Path(str(target) + str(expected))
    for cand in (target, candidate, target / expected.name, direct):
        if (cand / "chroma").is_dir() or (cand / "decisions-approved.jsonl").is_file():
            return cand
    # Walk a few levels for chroma.
    for chroma in target.rglob("chroma"):
        if chroma.is_dir() and (chroma / "chroma.sqlite3").exists():
            return chroma.parent
    return target


# ---------------------------------------------------------------------------
# Durable reporting
# ---------------------------------------------------------------------------
class RestoreReport:
    """Authoritative JSON report + derived Markdown."""

    def __init__(self, json_path: Path):
        self.json_path = Path(json_path)
        self.md_path = self.json_path.with_suffix(".md")
        self.started = _utc_now()
        self.meta: dict[str, Any] = {
            "status": "in_progress",
            "kind": "complete_data_restore_preflight",
            "started_at": self.started,
            "finished_at": None,
            "snapshot": {},
            "restic_version": None,
            "evidence_comparisons": [],
            "classifications": [],
        }
        self.steps: list[dict[str, Any]] = []
        self._write()

    def set_meta(self, **kwargs: Any) -> None:
        self.meta.update(kwargs)
        self._write()

    def set_snapshot_identity(
        self,
        *,
        snapshot_id: str,
        tree: str = "",
        original: str | None = None,
        tags: Iterable[str] = (),
        paths: Iterable[str] = (),
        repository: str = "",
        restic_version: str | None = None,
        time: str | None = None,
    ) -> None:
        self.meta["snapshot"] = {
            "id": snapshot_id,
            "tree": tree,
            "original": original,
            "tags": sorted(tags),
            "paths": list(paths),
            "repository": repository,
            "time": time,
        }
        if restic_version is not None:
            self.meta["restic_version"] = restic_version
        self._write()

    def step(self, name: str, status: str, detail: str = "", **extra: Any) -> None:
        entry: dict[str, Any] = {
            "name": name,
            "status": status,
            "detail": detail,
            "at": _utc_now(),
        }
        entry.update(extra)
        self.steps.append(entry)
        self._write()

    def record_inventory(self, inventory: InventoryResult) -> None:
        self.meta["classifications"] = [
            {
                "path": c.path,
                "authority": c.authority,
                "outcome": c.outcome,
                "detail": c.detail,
                "repair_source": c.repair_source,
                "code": c.code,
                "evidence_comparison": c.evidence_comparison,
            }
            for c in inventory.classifications
        ]
        self.meta["evidence_comparisons"] = inventory.evidence_comparisons
        self.meta["inventory_overall"] = inventory.overall
        self.meta["inventory_exit_code"] = inventory.exit_code
        self._write()

    def finalize(self, status: str, detail: str = "", exit_code: int = 0) -> None:
        self.meta["status"] = status
        self.meta["finished_at"] = _utc_now()
        self.meta["exit_code"] = exit_code
        if detail:
            self.meta["final_detail"] = detail
        self._write()

    def _write(self) -> None:
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"meta": self.meta, "steps": self.steps}
        # JSON is authoritative.
        atomic_write_json(self.json_path, payload, indent=2, sort_keys=True)
        # Markdown is derived and may be regenerated.
        snap = self.meta.get("snapshot") or {}
        lines = [
            "# Complete-data restore preflight report",
            "",
            f"- status: **{self.meta.get('status')}**",
            f"- started: {self.meta.get('started_at')}",
            f"- finished: {self.meta.get('finished_at')}",
            f"- exit_code: {self.meta.get('exit_code')}",
            f"- restic_version: {self.meta.get('restic_version')}",
            f"- snapshot.id: `{snap.get('id')}`",
            f"- snapshot.tree: `{snap.get('tree')}`",
            f"- snapshot.original: `{snap.get('original')}`",
            f"- snapshot.tags: `{snap.get('tags')}`",
            f"- snapshot.paths: `{snap.get('paths')}`",
            f"- snapshot.repository: `{snap.get('repository')}`",
        ]
        if self.meta.get("final_detail"):
            lines.append(f"- detail: {self.meta['final_detail']}")
        lines += ["", "## Classifications", ""]
        for c in self.meta.get("classifications") or []:
            lines.append(
                f"- `{c.get('path')}` — {c.get('outcome')} "
                f"({c.get('authority')}): {c.get('detail')}"
            )
        lines += ["", "## Evidence comparisons", ""]
        for ev in self.meta.get("evidence_comparisons") or []:
            lines.append(f"- `{json.dumps(ev, sort_keys=True)}`")
        lines += ["", "## Steps", "", "| # | Step | Status | Detail |", "|---|------|--------|--------|"]
        for i, s in enumerate(self.steps, 1):
            detail = (s.get("detail") or "").replace("|", "\\|")
            lines.append(f"| {i} | {s['name']} | {s['status']} | {detail} |")
        lines.append("")
        atomic_write_text(self.md_path, "\n".join(lines) + "\n")


def run_preflight_validation(
    restored_root: Path | str,
    *,
    expected_data_root: Path | str | None = None,
    report: RestoreReport | None = None,
    snapshot_meta: Mapping[str, Any] | None = None,
) -> InventoryResult:
    """Inventory + validators after a successful restore."""
    if report and snapshot_meta:
        report.set_snapshot_identity(**dict(snapshot_meta))  # type: ignore[arg-type]
    inventory = inventory_restored_state(restored_root, expected_data_root)
    if report:
        report.record_inventory(inventory)
        for c in inventory.classifications:
            report.step(
                f"classify:{c.path}",
                c.outcome,
                c.detail,
                repair_source=c.repair_source,
                code=c.code,
            )
        report.finalize(
            inventory.overall,
            detail=f"classifications={len(inventory.classifications)}",
            exit_code=inventory.exit_code,
        )
    return inventory
