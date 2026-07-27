"""Complete-data restore preflight library.

Validates restored state against the fixed restore matrix, classifies
findings without repairing, and writes durable reports outside the
disposable run.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-audit-closure.md
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Classification codes
# ---------------------------------------------------------------------------
EXIT_VALID = 0
EXIT_REPAIRABLE_DRIFT = 30
EXIT_BLOCKED = 31
EXIT_INTERNAL_FAILURE = 32


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
class RestoreReport:
    """Durable machine- and human-readable restore report."""

    def __init__(self, json_path: Path):
        self.json_path = json_path
        self.md_path = json_path.with_suffix(".md")
        self.started = datetime.now(timezone.utc).isoformat()
        self.meta: dict[str, Any] = {
            "status": "in_progress",
            "kind": "complete_data_restore_preflight",
            "started_at": self.started,
            "finished_at": None,
        }
        self.steps: list[dict[str, Any]] = []
        self._write()

    def set_meta(self, **kwargs: Any) -> None:
        self.meta.update(kwargs)
        self._write()

    def step(self, name: str, status: str, detail: str = "", **extra: Any) -> None:
        entry: dict[str, Any] = {
            "name": name,
            "status": status,
            "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        entry.update(extra)
        self.steps.append(entry)
        self._write()

    def finalize(self, status: str, detail: str = "", exit_code: int = 0) -> None:
        self.meta["status"] = status
        self.meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        self.meta["exit_code"] = exit_code
        if detail:
            self.meta["final_detail"] = detail
        self._write()

    def _write(self) -> None:
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"meta": self.meta, "steps": self.steps}
        self.json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        lines = [
            "# Complete-data restore preflight report",
            "",
            f"- status: **{self.meta.get('status')}**",
            f"- started: {self.meta.get('started_at')}",
            f"- finished: {self.meta.get('finished_at')}",
        ]
        for k in ("snapshot_id", "data_root", "restored_root", "repository"):
            if k in self.meta:
                lines.append(f"- {k}: `{self.meta[k]}`")
        if self.meta.get("final_detail"):
            lines.append(f"- detail: {self.meta['final_detail']}")
        lines += ["", "| # | Step | Status | Detail |", "|---|------|--------|--------|"]
        for i, s in enumerate(self.steps, 1):
            detail = (s.get("detail") or "").replace("|", "\\|")
            lines.append(f"| {i} | {s['name']} | {s['status']} | {detail} |")
        lines.append("")
        self.md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Inventory and classification matrix
# ---------------------------------------------------------------------------
@dataclass
class StateClassification:
    path_hint: str
    authority: str
    classification: str  # VALID, REPAIRABLE, BLOCKED, ADVISORY
    detail: str = ""
    repair_source: str = ""


@dataclass
class InventoryResult:
    classifications: list[StateClassification] = field(default_factory=list)
    overall: str = "VALID"
    exit_code: int = EXIT_VALID


def _sha256_file(path: Path) -> str:
    """SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl_line_count(path: Path) -> int:
    """Count non-empty lines in a JSONL file."""
    if not path.is_file():
        return 0
    count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def inventory_restored_state(restored_root: Path, expected_data_root: Path) -> InventoryResult:
    """Walk the restored root and classify every durable state path.

    Follows the fixed restore matrix from the Architecture doc.
    Unknown top-level durable state returns BLOCKED_UNCLASSIFIED_STATE.
    """
    result = InventoryResult()

    # Map of expected top-level paths relative to data root
    if not restored_root.is_dir():
        result.classifications.append(
            StateClassification(str(restored_root), "missing", "BLOCKED", "restored root missing")
        )
        result.overall = "BLOCKED"
        result.exit_code = EXIT_BLOCKED
        return result

    # Chroma directory
    chroma_dir = restored_root / "chroma"
    if chroma_dir.is_dir():
        db = chroma_dir / "chroma.sqlite3"
        if db.is_file():
            try:
                _verify_chroma_db(db, result)
            except Exception as exc:
                result.classifications.append(
                    StateClassification("chroma/", "Tier-1 authoritative", "BLOCKED",
                                        f"Chroma verification failed: {exc}")
                )
                result.overall = "BLOCKED"
                result.exit_code = EXIT_BLOCKED
        else:
            result.classifications.append(
                StateClassification("chroma/", "Tier-1 authoritative", "BLOCKED",
                                    "chroma.sqlite3 missing")
            )
            result.overall = "BLOCKED"
            result.exit_code = EXIT_BLOCKED
    else:
        result.classifications.append(
            StateClassification("chroma/", "Tier-1 authoritative", "BLOCKED",
                                "chroma directory missing")
        )
        result.overall = "BLOCKED"
        result.exit_code = EXIT_BLOCKED
    approved = restored_root / "decisions-approved.jsonl"
    if approved.is_file():
        try:
            _verify_jsonl(approved, "decisions-approved.jsonl", result)
        except Exception as exc:
            result.classifications.append(
                StateClassification("decisions-approved.jsonl", "canonical decisions", "BLOCKED",
                                    str(exc))
            )
            result.overall = "BLOCKED"
            result.exit_code = EXIT_BLOCKED
    else:
        result.classifications.append(
            StateClassification("decisions-approved.jsonl", "canonical decisions", "BLOCKED",
                                "file missing")
        )
        result.overall = "BLOCKED"
        result.exit_code = EXIT_BLOCKED

    # Pending decision events
    events = restored_root / "pending_decision_events.jsonl"
    if events.is_file():
        _verify_jsonl(events, "pending_decision_events.jsonl", result)
    else:
        result.classifications.append(
            StateClassification("pending_decision_events.jsonl", "canonical control", "ADVISORY",
                                "file missing (may be normal)")
        )

    # Pending decisions (compatibility projection)
    pending = restored_root / "pending_decisions.jsonl"
    if pending.is_file():
        count = _jsonl_line_count(pending)
        result.classifications.append(
            StateClassification("pending_decisions.jsonl", "compatibility projection",
                                "REPAIRABLE" if count > 0 else "VALID",
                                f"{count} line(s)",
                                repair_source="Pending event log")
        )
    else:
        result.classifications.append(
            StateClassification("pending_decisions.jsonl", "compatibility projection",
                                "VALID", "absent (normal)")
        )

    # Hash schema files
    for schema_file in ("hash_schema_deploy.json", "hash_schema_migration_report.json"):
        sf = restored_root / schema_file
        if sf.is_file():
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
                result.classifications.append(
                    StateClassification(schema_file, "canonical when referenced", "VALID",
                                        f"version={data.get('version', 'unknown')}")
                )
            except json.JSONDecodeError:
                result.classifications.append(
                    StateClassification(schema_file, "canonical when referenced", "BLOCKED",
                                        "invalid JSON")
                )
                result.overall = "BLOCKED"
                result.exit_code = EXIT_BLOCKED

    # Derived export (knowledge_units.jsonl)
    export = restored_root / "knowledge_units.jsonl"
    if export.is_file():
        count = _jsonl_line_count(export)
        result.classifications.append(
            StateClassification("knowledge_units.jsonl", "derived export", "REPAIRABLE",
                                f"{count} line(s) — regeneratable from Chroma",
                                repair_source="Chroma")
        )
    else:
        result.classifications.append(
            StateClassification("knowledge_units.jsonl", "derived export", "REPAIRABLE",
                                "missing — regeneratable from Chroma",
                                repair_source="Chroma")
        )

    # Processed.json
    proc = restored_root / "processed.json"
    if proc.is_file():
        try:
            data = json.loads(proc.read_text(encoding="utf-8"))
            result.classifications.append(
                StateClassification("processed.json", "mixed incremental sidecar", "REPAIRABLE",
                                    f"{len(data)} entries — rescan from sources",
                                    repair_source="Source rescan")
            )
        except json.JSONDecodeError:
            result.classifications.append(
                StateClassification("processed.json", "mixed incremental sidecar", "BLOCKED",
                                    "invalid JSON")
            )
            result.overall = "BLOCKED"
            result.exit_code = EXIT_BLOCKED

    # Queue files
    for qf in ("dedupe_queue.jsonl", "link_queue.jsonl", "ingest_duplicate_suppressions.jsonl"):
        qp = restored_root / qf
        if qp.is_file():
            result.classifications.append(
                StateClassification(qf, "conditional operational control", "REPAIRABLE",
                                    f"present — stale derived rows repairable",
                                    repair_source="Chroma")
            )

    # Inventory
    inv = restored_root / "inventory.jsonl"
    if inv.is_file():
        result.classifications.append(
            StateClassification("inventory.jsonl", "source inventory/cache", "REPAIRABLE",
                                "regeneratable from source rescan",
                                repair_source="Source rescan/reimport")
        )

    # Authorizations
    auth_dir = restored_root / "authorizations"
    if auth_dir.is_dir():
        for auth_file in auth_dir.rglob("*.json"):
            result.classifications.append(
                StateClassification(str(auth_file.relative_to(restored_root)),
                                    "conditional authorization control", "ADVISORY",
                                    "preserve for review")
            )

    # Operational evidence
    for ev_file in ("attempts.jsonl", "index_failures.jsonl", "synthesis_failures.jsonl"):
        ep = restored_root / ev_file
        if ep.is_file():
            result.classifications.append(
                StateClassification(ev_file, "operational evidence", "ADVISORY",
                                    "present for investigation")
            )

    # Refine undo
    undo_dir = restored_root / "refine_undo"
    if undo_dir.is_dir():
        result.classifications.append(
            StateClassification("refine_undo/", "operational evidence", "ADVISORY",
                                "present for investigation")
        )

    # Shadow ledger (Phase 0 — non-authoritative)
    shadow_ledger = restored_root / "shadow_ledger.jsonl"
    shadow_manifest = restored_root / "shadow_activation_manifest.json"
    shadow_health = restored_root / "shadow_health.json"
    if shadow_manifest.is_file() or shadow_ledger.is_file():
        if shadow_manifest.is_file() and shadow_ledger.is_file():
            try:
                manifest = json.loads(shadow_manifest.read_text(encoding="utf-8"))
                if manifest.get("active"):
                    result.classifications.append(
                        StateClassification("shadow_ledger/", "non-authoritative Phase 0",
                                            "ADVISORY", "active — bounded check only; "
                                            "never a repair source")
                    )
                else:
                    result.classifications.append(
                        StateClassification("shadow_ledger/", "non-authoritative Phase 0",
                                            "ADVISORY", "inactive — non-authoritative")
                    )
            except json.JSONDecodeError:
                result.classifications.append(
                    StateClassification("shadow_ledger/", "non-authoritative Phase 0",
                                        "ADVISORY", "malformed manifest — advisory only")
                )
        else:
            result.classifications.append(
                StateClassification("shadow_ledger/", "non-authoritative Phase 0",
                                    "ADVISORY", "partial residue — advisory only")
            )
    else:
        result.classifications.append(
            StateClassification("shadow_ledger/", "non-authoritative Phase 0",
                                "VALID", "disabled/absent (normal)")
        )

    # Lock files and scratch dirs — expected, not counted as state
    for scratch in ("worktrees", "restore-drill", "locks"):
        sp = restored_root / scratch
        if sp.exists():
            result.classifications.append(
                StateClassification(f"{scratch}/", "ephemeral/scratch", "VALID",
                                    "expected scratch — excluded from state")
            )

    # Scan for unknown top-level durable paths
    known = {
        "chroma", "decisions-approved.jsonl", "pending_decision_events.jsonl",
        "pending_decisions.jsonl", "hash_schema_deploy.json",
        "hash_schema_migration_report.json", "knowledge_units.jsonl",
        "processed.json", "dedupe_queue.jsonl", "link_queue.jsonl",
        "ingest_duplicate_suppressions.jsonl", "inventory.jsonl",
        "authorizations", "attempts.jsonl", "index_failures.jsonl",
        "synthesis_failures.jsonl", "refine_undo", "shadow_ledger.jsonl",
        "shadow_activation_manifest.json", "shadow_health.json",
        "worktrees", "restore-drill", "locks", "imports",
    }
    for child in restored_root.iterdir():
        if child.name not in known and not child.name.startswith("."):
            result.classifications.append(
                StateClassification(child.name, "unknown", "BLOCKED_UNCLASSIFIED_STATE",
                                    f"not in restore matrix — must be reviewed before replacement")
            )
            result.overall = "BLOCKED"
            result.exit_code = EXIT_BLOCKED

    # Determine overall classification
    if result.overall != "BLOCKED":
        has_repairable = any(c.classification == "REPAIRABLE" for c in result.classifications)
        if has_repairable:
            result.overall = "VALID_WITH_REPAIRABLE_DERIVED_DRIFT"
            result.exit_code = EXIT_REPAIRABLE_DRIFT
        else:
            result.overall = "VALID"
            result.exit_code = EXIT_VALID

    return result


def _verify_chroma_db(db_path: Path, result: InventoryResult) -> None:
    """Verify Chroma SQLite database integrity and record findings."""
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        expected = {"collections", "embeddings", "segments", "embedding_queue",
                    "embedding_metadata", "tenants", "databases"}
        missing = expected - set(tables)
        if missing:
            result.classifications.append(
                StateClassification("chroma/", "Tier-1 authoritative", "BLOCKED",
                                    f"missing tables: {missing}")
            )
            result.overall = "BLOCKED"
            result.exit_code = EXIT_BLOCKED
            return

        cur.execute("SELECT COUNT(*) FROM collections")
        col_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM embeddings")
        emb_count = cur.fetchone()[0]

        result.classifications.append(
            StateClassification("chroma/", "Tier-1 authoritative", "VALID",
                                f"collections={col_count} embeddings={emb_count}")
        )
    finally:
        conn.close()


def _verify_jsonl(path: Path, name: str, result: InventoryResult) -> None:
    """Verify a JSONL file is parseable and record findings."""
    count = 0
    errors = 0
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                json.loads(stripped)
                count += 1
            except json.JSONDecodeError:
                errors += 1
    if errors > 0:
        result.classifications.append(
            StateClassification(name, "canonical", "BLOCKED",
                                f"{count} valid, {errors} parse error(s)")
        )
        result.overall = "BLOCKED"
        result.exit_code = EXIT_BLOCKED
    else:
        result.classifications.append(
            StateClassification(name, "canonical", "VALID", f"{count} record(s)")
        )
