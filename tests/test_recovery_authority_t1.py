"""Recovery Authority T1 — v3 profile and durable registry validation substrate."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from complete_data_restore import (  # noqa: E402  # pylint: disable=wrong-import-position
    EVIDENCE_FILENAME,
    OUTCOME_BLOCKED,
    RestoreProfile,
    build_backup_evidence,
    capture_backup_evidence,
    inventory_restored_state,
    state_specs_for_profile,
    writer_census_for_root,
)
from provenance_registry_restore import (  # noqa: E402  # pylint: disable=wrong-import-position
    OUTCOME_QUARANTINED,
    build_registry_fixture,
    compute_tree_commitment,
    validate_provenance_registry,
)
from restic_snapshot import (  # noqa: E402  # pylint: disable=wrong-import-position
    BackupProfile,
    TAG_COMPLETE_DATA_V2,
    TAG_COMPLETE_DATA_V3,
    captures_backup_evidence,
)


def _make_chroma(root: Path) -> None:
    chroma = root / "chroma"
    chroma.mkdir(parents=True, exist_ok=True)
    db = chroma / "chroma.sqlite3"
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
        """
    )
    for i, name in enumerate(("knowledge_units", "conversation_summaries")):
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
        conn.execute(
            "INSERT INTO embeddings VALUES (?, ?, 'ku-1', ?, CURRENT_TIMESTAMP)",
            (i, sid, b"\x00"),
        )
    conn.commit()
    conn.close()


def _minimal_v2_root(root: Path) -> None:
    _make_chroma(root)
    (root / "decisions-approved.jsonl").write_text(
        json.dumps(
            {
                "id": "dec_prop_test_001",
                "ledger_id": "dec_prop_test_001",
                "kind": "decision",
                "status": "accepted",
                "summary": "test",
                "rationale": "because",
                "proposal_id": "dec_prop_test_001",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "knowledge_units.jsonl").write_text('{"id": "ku-1"}\n', encoding="utf-8")
    (root / "processed.json").write_text("{}", encoding="utf-8")


class TestProfileCoexistence(unittest.TestCase):
    def test_v2_state_specs_exclude_provenance(self):
        paths = {spec.path for spec in state_specs_for_profile(RestoreProfile.COMPLETE_DATA_V2)}
        self.assertNotIn("provenance", paths)

    def test_v3_state_specs_require_provenance(self):
        paths = {spec.path for spec in state_specs_for_profile(RestoreProfile.COMPLETE_DATA_V3)}
        self.assertIn("provenance", paths)

    def test_v2_fixture_valid_without_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            result = inventory_restored_state(root, root, profile=RestoreProfile.COMPLETE_DATA_V2)
            self.assertNotEqual(result.overall, OUTCOME_BLOCKED)
            census = writer_census_for_root(root, profile=RestoreProfile.COMPLETE_DATA_V2)
            self.assertNotIn("provenance", census)

    def test_v3_inventory_blocks_without_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            result = inventory_restored_state(root, root, profile=RestoreProfile.COMPLETE_DATA_V3)
            self.assertEqual(result.overall, OUTCOME_BLOCKED)
            prov = [c for c in result.classifications if c.path == "provenance"]
            self.assertTrue(prov)
            self.assertEqual(prov[0].outcome, OUTCOME_BLOCKED)


class TestRegistryValidation(unittest.TestCase):
    def test_valid_v3_registry_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            provenance_tuple = build_registry_fixture(root)
            result = validate_provenance_registry(root)
            self.assertTrue(result.ok, result.detail)
            self.assertIsNotNone(result.provenance_tuple)
            self.assertEqual(result.provenance_tuple.generation_id, provenance_tuple.generation_id)
            self.assertEqual(result.provenance_tuple.manifest_commitment, provenance_tuple.manifest_commitment)
            self.assertEqual(result.provenance_tuple.tree_commitment, provenance_tuple.tree_commitment)

    def test_missing_registry_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            result = validate_provenance_registry(root)
            self.assertEqual(result.outcome, OUTCOME_BLOCKED)
            self.assertIn("selector missing", result.detail)

    def test_partial_registry_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            selector = root / "provenance" / "selector.json"
            selector.parent.mkdir(parents=True)
            selector.write_text("{}", encoding="utf-8")
            result = validate_provenance_registry(root)
            self.assertIn(result.outcome, {OUTCOME_BLOCKED, OUTCOME_QUARANTINED})

    def test_sidecar_valid_registry_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            capture_backup_evidence(root)
            evidence = root / EVIDENCE_FILENAME
            self.assertTrue(evidence.is_file())
            result = validate_provenance_registry(root)
            self.assertFalse(result.ok)
            inv = inventory_restored_state(root, root, profile=RestoreProfile.COMPLETE_DATA_V2)
            self.assertNotEqual(inv.overall, OUTCOME_BLOCKED)

    def test_v3_inventory_with_valid_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            build_registry_fixture(root)
            registry = validate_provenance_registry(root)
            self.assertTrue(registry.ok)
            inv = inventory_restored_state(root, root, profile=RestoreProfile.COMPLETE_DATA_V3)
            self.assertNotEqual(inv.overall, OUTCOME_BLOCKED)
            census = writer_census_for_root(root, profile=RestoreProfile.COMPLETE_DATA_V3)
            self.assertEqual(census.get("provenance"), "tier1_provenance_authority")


class TestResticProfileBinding(unittest.TestCase):
    def test_v3_restic_tag_distinct_from_v2(self):
        self.assertNotEqual(TAG_COMPLETE_DATA_V2, TAG_COMPLETE_DATA_V3)
        self.assertEqual(BackupProfile.COMPLETE_DATA_V3.value, "complete-data-v3")

    def test_tree_commitment_excludes_selector_and_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            before = compute_tree_commitment(root)
            capture_backup_evidence(root)
            (root / "provenance").mkdir()
            (root / "provenance" / "selector.json").write_text("{}", encoding="utf-8")
            after = compute_tree_commitment(root)
            self.assertEqual(before, after)


class TestEvidenceSeparateFromRegistry(unittest.TestCase):
    def test_build_backup_evidence_not_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _minimal_v2_root(root)
            evidence = build_backup_evidence(root)
            self.assertFalse(evidence.get("authority"))
            self.assertFalse(evidence.get("repair_source"))



class TestBackupEvidenceProfilePredicate(unittest.TestCase):
    def test_complete_data_profiles_capture_sidecar(self):
        self.assertTrue(captures_backup_evidence(BackupProfile.COMPLETE_DATA_V2))
        self.assertTrue(captures_backup_evidence(BackupProfile.COMPLETE_DATA_V3))
        self.assertFalse(captures_backup_evidence(BackupProfile.LEGACY_CHROMA))

if __name__ == "__main__":
    unittest.main()
