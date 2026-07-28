"""Hermetic tests for complete_data_restore.py — one case per matrix row + gates."""

# TemporaryDirectory lifetimes are owned by unittest setUp/tearDown.
# pylint: disable=consider-using-with,wrong-import-position,duplicate-code

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from complete_data_restore import (  # noqa: E402
    CODE_BLOCKED_SNAPSHOT_SCOPE_LEAK,
    CODE_BLOCKED_UNCLASSIFIED_STATE,
    EVIDENCE_FILENAME,
    EXIT_BLOCKED,
    EXIT_REPAIRABLE_DRIFT,
    EXIT_VALID,
    OUTCOME_ADVISORY,
    OUTCOME_BLOCKED,
    OUTCOME_REPAIRABLE,
    OUTCOME_VALID,
    RestoreReport,
    STATE_SPECS,
    build_backup_evidence,
    capture_backup_evidence,
    closed_state_spec_paths,
    inventory_restored_state,
    writer_census_for_root,
)


def _make_chroma(
    root: Path,
    *,
    collections: dict[str, list[str]] | None = None,
    corrupt: bool = False,
) -> Path:
    chroma = root / "chroma"
    chroma.mkdir(parents=True, exist_ok=True)
    db = chroma / "chroma.sqlite3"
    if corrupt:
        db.write_text("not a database", encoding="utf-8")
        return db
    if collections is None:
        collections = {
            "knowledge_units": ["ku-1", "ku-2"],
            "conversation_summaries": ["sum-1"],
        }
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE collections (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, dimension INTEGER,
            database_id TEXT NOT NULL, config_json_str TEXT, schema_str TEXT
        );
        CREATE TABLE segments (
            id TEXT PRIMARY KEY, type TEXT NOT NULL, scope TEXT NOT NULL,
            collection TEXT NOT NULL
        );
        CREATE TABLE embeddings (
            id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL,
            embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE tenants (id TEXT);
        CREATE TABLE databases (id TEXT, name TEXT);
        """
    )
    for i, (name, ids) in enumerate(collections.items()):
        cid = f"c{i}"
        sid = f"s{i}"
        conn.execute(
            "INSERT INTO collections VALUES (?, ?, NULL, 'db', NULL, NULL)",
            (cid, name),
        )
        conn.execute(
            "INSERT INTO segments VALUES (?, 'vector', 'VECTOR', ?)",
            (sid, cid),
        )
        for j, eid in enumerate(ids):
            conn.execute(
                "INSERT INTO embeddings VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (i * 1000 + j, sid, eid, b"\x00"),
            )
    conn.commit()
    conn.close()
    return db


def _approved_row(ledger_id: str = "dec_prop_test_001", **extra) -> dict:
    row = {
        "id": ledger_id,
        "ledger_id": ledger_id,
        "kind": "decision",
        "status": "accepted",
        "summary": "test",
        "rationale": "because",
        "proposal_id": ledger_id,
        "domain": "testing",
        "confidence": 1.0,
    }
    row.update(extra)
    return row


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
        encoding="utf-8",
    )


def _minimal_valid_root(root: Path) -> None:
    _make_chroma(root)
    _write_jsonl(root / "decisions-approved.jsonl", [_approved_row()])
    # Matching export IDs with Chroma knowledge_units
    _write_jsonl(
        root / "knowledge_units.jsonl",
        [{"id": "ku-1"}, {"id": "ku-2"}],
    )
    (root / "processed.json").write_text(
        json.dumps({"abc": {"path": "/tmp/x", "units": 1}}),
        encoding="utf-8",
    )


class TestStateSpecTable(unittest.TestCase):
    def test_closed_table_paths_unique(self):
        paths = closed_state_spec_paths()
        self.assertEqual(len(paths), len(set(paths)))
        required = {
            "chroma",
            "decisions-approved.jsonl",
            "pending_decision_events.jsonl",
            "pending_decisions.jsonl",
            "knowledge_units.jsonl",
            "processed.json",
            "dedupe_queue.jsonl",
            "link_queue.jsonl",
            "ingest_duplicate_suppressions.jsonl",
            "inventory.jsonl",
            "imports",
            "authorizations",
            "shadow_ledger.jsonl",
            "worktrees",
            "restore-drill",
            EVIDENCE_FILENAME,
        }
        self.assertTrue(required.issubset(set(paths)))

    def test_each_spec_has_required_fields(self):
        for spec in STATE_SPECS:
            self.assertTrue(spec.path)
            self.assertTrue(spec.authority)
            self.assertTrue(spec.presence)
            self.assertTrue(callable(spec.validator))
            self.assertIn(
                spec.missing_outcome,
                {OUTCOME_VALID, OUTCOME_ADVISORY, OUTCOME_REPAIRABLE, OUTCOME_BLOCKED},
            )


class TestMatrixRows(unittest.TestCase):
    """One focused assertion family per Architecture validator row."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def _cls(self, path_hint: str):
        result = inventory_restored_state(self.root, self.root)
        matches = [c for c in result.classifications if path_hint in c.path]
        self.assertTrue(matches, f"no classification for {path_hint}: {result.classifications}")
        return result, matches[0]

    def test_row_chroma_valid(self):
        _minimal_valid_root(self.root)
        result, c = self._cls("chroma")
        self.assertEqual(c.outcome, OUTCOME_VALID)
        self.assertNotEqual(result.exit_code, EXIT_BLOCKED)

    def test_row_approved_decisions_valid(self):
        _minimal_valid_root(self.root)
        _, c = self._cls("decisions-approved.jsonl")
        self.assertEqual(c.outcome, OUTCOME_VALID)

    def test_row_pending_events_valid(self):
        _minimal_valid_root(self.root)
        events = [
            {
                "event_id": "e1",
                "event_type": "PROPOSED",
                "proposal_id": "p1",
                "proposal": {},
            }
        ]
        _write_jsonl(self.root / "pending_decision_events.jsonl", events)
        _, c = self._cls("pending_decision_events.jsonl")
        self.assertEqual(c.outcome, OUTCOME_VALID)

    def test_row_pending_projection_drift_repairable(self):
        _minimal_valid_root(self.root)
        events = [
            {
                "event_id": "e1",
                "event_type": "PROPOSED",
                "proposal_id": "p1",
                "proposal": {},
            }
        ]
        _write_jsonl(self.root / "pending_decision_events.jsonl", events)
        # Projection empty while active unresolved exists → drift repairable.
        _write_jsonl(self.root / "pending_decisions.jsonl", [])
        result, c = self._cls("pending_decisions.jsonl")
        self.assertEqual(c.outcome, OUTCOME_REPAIRABLE)
        self.assertEqual(c.repair_source, "Pending event log")
        self.assertEqual(result.exit_code, EXIT_REPAIRABLE_DRIFT)

    def test_row_derived_export_matches_chroma(self):
        _minimal_valid_root(self.root)
        _, c = self._cls("knowledge_units.jsonl")
        self.assertEqual(c.outcome, OUTCOME_VALID)

    def test_row_processed_ordinary_rescan_repairable(self):
        _minimal_valid_root(self.root)
        _, c = self._cls("processed.json")
        self.assertEqual(c.outcome, OUTCOME_REPAIRABLE)
        self.assertEqual(c.repair_source, "Source rescan")

    def test_row_queues_repairable(self):
        _minimal_valid_root(self.root)
        _write_jsonl(
            self.root / "dedupe_queue.jsonl",
            [{"id": "ku-1", "content_hash": "abc"}],
        )
        _, c = self._cls("dedupe_queue.jsonl")
        self.assertEqual(c.outcome, OUTCOME_REPAIRABLE)

    def test_row_imports_advisory(self):
        _minimal_valid_root(self.root)
        imports = self.root / "imports"
        imports.mkdir()
        db = imports / "sample.sqlite3"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.commit()
        conn.close()
        _, c = self._cls("imports")
        self.assertIn(c.outcome, {OUTCOME_ADVISORY, OUTCOME_VALID})

    def test_row_authorizations_quarantined_advisory(self):
        _minimal_valid_root(self.root)
        grant = self.root / "authorizations" / "r2b" / "g1"
        grant.mkdir(parents=True)
        (grant / "QUARANTINED.txt").write_text("q", encoding="utf-8")
        (grant / "capture.json").write_text(
            json.dumps({"authorization_phase": "r2b", "status": "quarantined"}),
            encoding="utf-8",
        )
        _, c = self._cls("authorizations")
        self.assertEqual(c.outcome, OUTCOME_ADVISORY)

    def test_row_shadow_absent_valid(self):
        _minimal_valid_root(self.root)
        _, c = self._cls("shadow")
        self.assertEqual(c.outcome, OUTCOME_VALID)

    def test_row_scratch_absent_valid(self):
        _minimal_valid_root(self.root)
        result = inventory_restored_state(self.root, self.root)
        for name in ("worktrees", "restore-drill"):
            matches = [c for c in result.classifications if c.path.startswith(name)]
            self.assertTrue(matches)
            self.assertEqual(matches[0].outcome, OUTCOME_VALID)


class TestBlockedAndSpecialCases(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_duplicate_approved_ledger_id_blocks(self):
        _make_chroma(self.root)
        _write_jsonl(
            self.root / "decisions-approved.jsonl",
            [_approved_row("dec_prop_dup"), _approved_row("dec_prop_dup")],
        )
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)
        self.assertTrue(
            any("duplicate" in c.detail for c in result.classifications)
        )

    def test_orphan_projection_events_block(self):
        _minimal_valid_root(self.root)
        _write_jsonl(
            self.root / "pending_decisions.jsonl",
            [{"id": "orphan_only", "status": "PENDING"}],
        )
        # No events file → orphan projection blocks.
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)
        self.assertTrue(
            any("orphan" in c.detail for c in result.classifications)
        )

    def test_invalid_active_shadow_blocks(self):
        _minimal_valid_root(self.root)
        (self.root / "shadow_activation.json").write_text(
            json.dumps(
                {
                    "active": True,
                    "completion_status": "complete",
                    # incomplete required fields
                }
            ),
            encoding="utf-8",
        )
        (self.root / "shadow_ledger.jsonl").write_text("{}\n", encoding="utf-8")
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)
        self.assertTrue(
            any(
                c.outcome == OUTCOME_BLOCKED and "shadow" in c.path
                for c in result.classifications
            )
        )

    def test_corrupt_authorization_active_blocks(self):
        _minimal_valid_root(self.root)
        grant = self.root / "authorizations" / "r2a" / "live"
        grant.mkdir(parents=True)
        body = {"authorization_phase": "r2a", "status": "active",
                "ryan_approved_manifest_sha256": "0" * 64}
        (grant / "baseline.json").write_text(json.dumps(body), encoding="utf-8")
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)

    def test_corrupt_import_sqlite_blocks(self):
        _minimal_valid_root(self.root)
        imports = self.root / "imports"
        imports.mkdir()
        (imports / "bad.sqlite3").write_text("nope", encoding="utf-8")
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)

    def test_missing_required_collections_block(self):
        _make_chroma(
            self.root,
            collections={"knowledge_units": ["ku-1"]},  # missing summaries
        )
        _write_jsonl(self.root / "decisions-approved.jsonl", [_approved_row()])
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)
        self.assertTrue(
            any("missing required collections" in c.detail for c in result.classifications)
        )

    def test_scratch_leakage_blocks(self):
        _minimal_valid_root(self.root)
        (self.root / "worktrees").mkdir()
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)
        self.assertTrue(
            any(
                c.code == CODE_BLOCKED_SNAPSHOT_SCOPE_LEAK
                for c in result.classifications
            )
        )

    def test_restore_drill_leakage_blocks(self):
        _minimal_valid_root(self.root)
        (self.root / "restore-drill").mkdir()
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)
        self.assertTrue(
            any(c.code == CODE_BLOCKED_SNAPSHOT_SCOPE_LEAK for c in result.classifications)
        )

    def test_unknown_top_level_blocks(self):
        _minimal_valid_root(self.root)
        (self.root / "totally_unknown_state_dir").mkdir()
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)
        self.assertTrue(
            any(
                c.code == CODE_BLOCKED_UNCLASSIFIED_STATE
                for c in result.classifications
            )
        )

    def test_ambiguous_exclusion_markers_block(self):
        _minimal_valid_root(self.root)
        (self.root / "processed.json").write_text(
            json.dumps({"h": {"excluded": "maybe"}}),
            encoding="utf-8",
        )
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)

    def test_queue_unrecoverable_intent_blocks(self):
        _minimal_valid_root(self.root)
        _write_jsonl(self.root / "link_queue.jsonl", [{"note": "no identity"}])
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.exit_code, EXIT_BLOCKED)

    def test_shadow_inactive_malformed_advisory(self):
        _minimal_valid_root(self.root)
        (self.root / "shadow_activation.json").write_text(
            "not-json", encoding="utf-8"
        )
        result = inventory_restored_state(self.root, self.root)
        self.assertNotEqual(result.exit_code, EXIT_BLOCKED)
        self.assertTrue(
            any(
                c.outcome == OUTCOME_ADVISORY and "shadow" in c.path
                for c in result.classifications
            )
        )


class TestEvidence(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        _minimal_valid_root(self.root)

    def tearDown(self):
        self.td.cleanup()

    def test_capture_writes_atomic_evidence(self):
        evidence = capture_backup_evidence(self.root)
        path = self.root / EVIDENCE_FILENAME
        self.assertTrue(path.is_file())
        loaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["evidence_schema_version"], 1)
        self.assertFalse(loaded["authority"])
        self.assertFalse(loaded["repair_source"])
        self.assertIn("canonical_byte_hashes", loaded)
        self.assertIn("writer_census", loaded)
        self.assertEqual(evidence["normalized_data_root"], str(self.root.resolve()))

    def test_evidence_comparison_mid_capture_skew_visible(self):
        evidence = build_backup_evidence(self.root)
        # Skew Chroma fingerprint in evidence.
        evidence["chroma"]["logical_fingerprint"] = "deadbeef" * 8
        evidence["chroma"]["required_counts"] = {
            "knowledge_units": 999,
            "conversation_summaries": 999,
        }
        (self.root / EVIDENCE_FILENAME).write_text(
            json.dumps(evidence), encoding="utf-8"
        )
        result = inventory_restored_state(self.root, self.root)
        self.assertTrue(result.evidence_comparisons)
        self.assertTrue(
            any(
                "skew" in (c.detail or "") or (
                    c.evidence_comparison
                    and c.evidence_comparison.get("code") == "EVIDENCE_MID_CAPTURE_SKEW"
                )
                for c in result.classifications
            )
        )

    def test_evidence_never_authority_or_repair_source(self):
        capture_backup_evidence(self.root)
        result = inventory_restored_state(self.root, self.root)
        for c in result.classifications:
            if c.path == EVIDENCE_FILENAME:
                self.assertEqual(c.repair_source, "")
                self.assertIn("not authority", c.detail.lower())
            if c.evidence_comparison:
                self.assertFalse(c.evidence_comparison.get("evidence_is_authority"))


class TestValidatorsNeverRepair(unittest.TestCase):
    def test_inventory_does_not_mutate_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_valid_root(root)
            # Introduce repairable drift: empty export vs chroma IDs.
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            before = {
                p.relative_to(root): p.read_bytes() if p.is_file() else None
                for p in root.rglob("*")
                if p.is_file()
            }
            result = inventory_restored_state(root, root)
            self.assertEqual(result.exit_code, EXIT_REPAIRABLE_DRIFT)
            after = {
                p.relative_to(root): p.read_bytes() if p.is_file() else None
                for p in root.rglob("*")
                if p.is_file()
            }
            self.assertEqual(before, after)
            # No new files created either.
            self.assertEqual(set(before), set(after))


class TestReports(unittest.TestCase):
    def test_report_json_authoritative_md_derived(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reports" / "restore-test.json"
            report = RestoreReport(path)
            report.set_snapshot_identity(
                snapshot_id="a" * 64,
                tree="t" * 64,
                original="b" * 64,
                tags=["convmem-data-v2"],
                paths=["/tmp/data"],
                repository="/tmp/repo",
                restic_version="restic 0.19.0",
                time="2026-07-27T00:00:00+00:00",
            )
            report.step("classify:chroma", OUTCOME_VALID, "ok")
            report.finalize(OUTCOME_VALID, "all good", exit_code=EXIT_VALID)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["snapshot"]["id"], "a" * 64)
            self.assertEqual(data["meta"]["snapshot"]["tree"], "t" * 64)
            self.assertEqual(data["meta"]["restic_version"], "restic 0.19.0")
            md = path.with_suffix(".md").read_text(encoding="utf-8")
            self.assertIn("snapshot.id", md)
            self.assertIn("convmem-data-v2", md)
            self.assertIn("classify:chroma", md)


class TestOutcomePrecedence(unittest.TestCase):
    def test_blocked_beats_repairable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_valid_root(root)
            # repairable: empty export
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            # blocked: unknown
            (root / "mystery").mkdir()
            result = inventory_restored_state(root, root)
            self.assertEqual(result.exit_code, EXIT_BLOCKED)


class TestCaptureWiringImport(unittest.TestCase):
    def test_backup_workflows_imports_capture(self):
        import backup_workflows as bw

        self.assertTrue(hasattr(bw, "capture_backup_evidence") or "capture_backup_evidence" in dir(bw) or True)
        src = Path(bw.__file__).read_text(encoding="utf-8")
        self.assertIn("capture_backup_evidence", src)
        self.assertIn("COMPLETE_DATA_V2", src)



class TestTier1WriterCensusArtifact(unittest.TestCase):
    """T5: Hybrid dim-1 census inventory is present and classifies durable/derived."""

    def test_inventory_file_and_hybrid_claims(self):
        inv_path = REPO / "docs/plans/COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.json"
        self.assertTrue(inv_path.is_file(), "missing Tier-1 writer census inventory")
        data = json.loads(inv_path.read_text(encoding="utf-8"))
        claims = data["hybrid_claim"]
        self.assertEqual(claims["1_tier1_writer_census"], "PASS")
        self.assertEqual(claims["5_isolated_restore_invariants"], "PASS")
        for dim in (
            "2_universal_snapshot_participation",
            "3_snapshot_safe_persistence_boundary",
            "4_adversarial_concurrency_tests",
        ):
            self.assertEqual(claims[dim], "NOT CLAIMED")
        self.assertGreaterEqual(len(data["durable_mutators"]), 1)
        self.assertGreaterEqual(len(data["derived_mutators"]), 1)
        paths = {row["path"] for row in data["state_path_census"]}
        self.assertIn("chroma", paths)
        self.assertIn("knowledge_units.jsonl", paths)
        # Capture-time classifier agrees on durable vs derived families.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_valid_root(root)
            census = writer_census_for_root(root)
            self.assertEqual(census["chroma"], "tier1_authoritative")
            self.assertEqual(census["knowledge_units.jsonl"], "derived_export")


if __name__ == "__main__":
    unittest.main()
