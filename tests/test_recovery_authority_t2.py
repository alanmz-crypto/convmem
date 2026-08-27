"""Recovery Authority T2 — authority recovery and projection agreement state machine."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from complete_data_restore import (  # noqa: E402  # pylint: disable=wrong-import-position
    EVIDENCE_FILENAME,
    capture_backup_evidence,
)
from provenance_registry_restore import (  # noqa: E402  # pylint: disable=wrong-import-position
    build_registry_fixture,
    validate_provenance_registry,
)
from recovery_authority import (  # noqa: E402  # pylint: disable=wrong-import-position
    RecoveryState,
    evaluate_recovery_authority,
    write_matching_projections,
)


def _write_decisions(root: Path) -> None:
    (root / "decisions-approved.jsonl").write_text(
        json.dumps(
            {
                "id": "dec_prop_t2_001",
                "ledger_id": "dec_prop_t2_001",
                "kind": "decision",
                "status": "accepted",
                "summary": "t2",
                "rationale": "fixture",
                "proposal_id": "dec_prop_t2_001",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "processed.json").write_text("{}", encoding="utf-8")


def _seal_candidate(
    root: Path,
    *,
    assertion_ids: tuple[str, ...] = ("assert-fixture-001",),
    with_bindings: bool = True,
    include_chroma: bool = True,
    include_jsonl: bool = True,
):
    """Seal a v3 registry candidate with optional matching projections."""
    _write_decisions(root)
    # Seed empty projection bodies so T_g can include them, then seal registry.
    if include_jsonl:
        rows = [
            {"id": aid, "assertion_id": aid, "generation_id": "pg-fixture-001"}
            for aid in assertion_ids
        ]
        (root / "knowledge_units.jsonl").write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
            encoding="utf-8",
        )
    provenance_tuple = build_registry_fixture(
        root, generation_id="pg-fixture-001", assertion_ids=assertion_ids
    )
    write_matching_projections(
        root,
        provenance_tuple,
        assertion_ids=assertion_ids,
        include_jsonl=include_jsonl,
        include_chroma=include_chroma,
        rewrite_bodies=True,
    )
    shutil.rmtree(root / "provenance")
    provenance_tuple = build_registry_fixture(
        root, generation_id="pg-fixture-001", assertion_ids=assertion_ids
    )
    if with_bindings:
        write_matching_projections(
            root,
            provenance_tuple,
            assertion_ids=assertion_ids,
            include_jsonl=include_jsonl,
            include_chroma=include_chroma,
            rewrite_bodies=False,
        )
    return provenance_tuple


def _install_registry_fixture(
    root: Path,
    *,
    include_jsonl: bool = True,
    include_chroma: bool = True,
    rewrite_bodies: bool = False,
):
    """Install the shared pg-fixture-001 registry with matching projections."""
    provenance_tuple = build_registry_fixture(
        root, generation_id="pg-fixture-001", assertion_ids=("assert-fixture-001",)
    )
    write_matching_projections(
        root,
        provenance_tuple,
        assertion_ids=("assert-fixture-001",),
        include_jsonl=include_jsonl,
        include_chroma=include_chroma,
        rewrite_bodies=rewrite_bodies,
    )
    return provenance_tuple


class TestRecoveryStateMachine(unittest.TestCase):
    def test_complete_valid_registry_and_projections(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.PROJECTION_VALIDATED)
            self.assertFalse(result.serving_ready)
            self.assertTrue(result.state.authority_recovered)
            self.assertEqual(result.projection_agreement.get("status"), "validated")

    def test_valid_authority_projections_unavailable_is_pending(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_decisions(root)
            pt = build_registry_fixture(root)
            result = evaluate_recovery_authority(root)
            self.assertEqual(
                result.state, RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
            )
            self.assertFalse(result.serving_ready)
            self.assertEqual(result.provenance_tuple.generation_id, pt.generation_id)

    def test_missing_chroma_with_valid_jsonl_is_pending(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root, include_chroma=False, include_jsonl=True)
            result = evaluate_recovery_authority(root)
            self.assertEqual(
                result.state, RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
            )
            self.assertFalse(result.serving_ready)

    def test_missing_history_quarantines_or_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            (
                root
                / "provenance/generations/pg-fixture-001/history/policy_registry.json"
            ).unlink()
            result = evaluate_recovery_authority(root)
            self.assertIn(result.state, {RecoveryState.BLOCKED, RecoveryState.QUARANTINED})
            self.assertFalse(result.serving_ready)

    def test_missing_graph_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            (root / "provenance/generations/pg-fixture-001/graph.json").unlink()
            result = evaluate_recovery_authority(root)
            self.assertIn(result.state, {RecoveryState.BLOCKED, RecoveryState.QUARANTINED})

    def test_provenance_store_unavailable_when_selector_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_decisions(root)
            capture_backup_evidence(root)
            self.assertTrue((root / EVIDENCE_FILENAME).is_file())
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.PROVENANCE_STORE_UNAVAILABLE)
            self.assertFalse(result.serving_ready)
            self.assertFalse(
                result.registry_report.get("evidence_repairs_registry", True)
            )

    def test_sidecar_cannot_repair_invalid_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            capture_backup_evidence(root)
            (
                root / "provenance/generations/pg-fixture-001/manifest.json"
            ).write_text("{}", encoding="utf-8")
            result = evaluate_recovery_authority(root)
            self.assertIn(
                result.state,
                {
                    RecoveryState.BLOCKED,
                    RecoveryState.QUARANTINED,
                    RecoveryState.PROVENANCE_STORE_UNAVAILABLE,
                },
            )
            self.assertFalse(result.serving_ready)

    def test_stale_projection_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pt = _seal_candidate(root)
            bind = json.loads(
                (root / "knowledge_units.projection.json").read_text(encoding="utf-8")
            )
            bind["generation_id"] = "stale-generation"
            (root / "knowledge_units.projection.json").write_text(
                json.dumps(bind, sort_keys=True), encoding="utf-8"
            )
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.QUARANTINED)
            self.assertIn("generation", result.detail)
            self.assertEqual(result.provenance_tuple.generation_id, pt.generation_id)

    def test_commitment_mismatch_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            bind = json.loads(
                (root / "knowledge_units.projection.json").read_text(encoding="utf-8")
            )
            aid = bind["assertion_ids"][0]
            bind["provenance_commitments"][aid] = "0" * 64
            (root / "knowledge_units.projection.json").write_text(
                json.dumps(bind, sort_keys=True), encoding="utf-8"
            )
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.QUARANTINED)
            self.assertIn("commitment", result.detail.lower())

    def test_binding_mismatch_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            bind = json.loads(
                (root / "chroma/projection_binding.json").read_text(encoding="utf-8")
            )
            bind["projection_binding"] = "f" * 64
            (root / "chroma/projection_binding.json").write_text(
                json.dumps(bind, sort_keys=True), encoding="utf-8"
            )
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.QUARANTINED)

    def test_stale_fallback_attempt_rejected(self):
        with tempfile.TemporaryDirectory() as td_a, tempfile.TemporaryDirectory() as td_b:
            root = Path(td_a)
            stale = Path(td_b)
            _seal_candidate(root)
            _seal_candidate(stale, assertion_ids=("assert-stale-001",))
            result = evaluate_recovery_authority(
                root,
                allow_stale_fallback=True,
                stale_projection_root=stale,
            )
            self.assertEqual(result.state, RecoveryState.QUARANTINED)
            self.assertEqual(result.code, "QUARANTINED_STALE_PROJECTION_FALLBACK")
            self.assertFalse(result.serving_ready)

    def test_projection_cannot_mint_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            bind = json.loads(
                (root / "knowledge_units.projection.json").read_text(encoding="utf-8")
            )
            bind["assertion_ids"].append("forged-assertion")
            bind["provenance_commitments"]["forged-assertion"] = "a" * 64
            (root / "knowledge_units.projection.json").write_text(
                json.dumps(bind, sort_keys=True), encoding="utf-8"
            )
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.QUARANTINED)
            self.assertFalse(result.serving_ready)

    def test_stale_body_generation_without_sidecar_quarantined(self):
        """Body generation stamps must match recovered authority even without bindings."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            rows = []
            for line in (root / "knowledge_units.jsonl").read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                row["generation_id"] = "stale-body-generation"
                rows.append(row)
            (root / "knowledge_units.jsonl").write_text(
                "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                encoding="utf-8",
            )
            # Re-seal registry so T_g matches the stale-stamped body; authority gen stays fixture id.
            shutil.rmtree(root / "provenance")
            build_registry_fixture(root, generation_id="pg-fixture-001", assertion_ids=("assert-fixture-001",))
            (root / "knowledge_units.projection.json").unlink(missing_ok=True)
            (root / "chroma" / "projection_binding.json").unlink(missing_ok=True)
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.QUARANTINED)
            self.assertIn("generation", result.detail.lower())

    def test_sidecar_cannot_hide_stale_body_generation(self):
        """Sidecar generation must not override a disagreeing body stamp into validated."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            rows = []
            for line in (root / "knowledge_units.jsonl").read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                row["generation_id"] = "stale-body-generation"
                rows.append(row)
            (root / "knowledge_units.jsonl").write_text(
                "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                encoding="utf-8",
            )
            shutil.rmtree(root / "provenance")
            _install_registry_fixture(
                root,
                include_jsonl=True,
                include_chroma=True,
                rewrite_bodies=False,
            )
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.QUARANTINED)
            self.assertNotEqual(result.state, RecoveryState.PROJECTION_VALIDATED)
            self.assertFalse(result.serving_ready)

    def test_non_object_jsonl_row_is_pending(self):
        """Damaged JSONL body is rebuildable when authority is valid."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root, include_chroma=False)
            (root / "knowledge_units.jsonl").write_text("[\"not-an-object\"]\n", encoding="utf-8")
            shutil.rmtree(root / "provenance")
            build_registry_fixture(
                root, generation_id="pg-fixture-001", assertion_ids=("assert-fixture-001",)
            )
            (root / "knowledge_units.projection.json").unlink(missing_ok=True)
            result = evaluate_recovery_authority(root)
            self.assertEqual(
                result.state, RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
            )
            self.assertFalse(result.serving_ready)
            self.assertTrue(result.state.authority_recovered)

    def test_unreadable_chroma_is_pending(self):
        """Unreadable Chroma with valid authority is rebuildable, not quarantine."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root, include_jsonl=False, include_chroma=True)
            db = root / "chroma" / "chroma.sqlite3"
            db.write_bytes(b"not-a-sqlite-db")
            shutil.rmtree(root / "provenance")
            build_registry_fixture(
                root, generation_id="pg-fixture-001", assertion_ids=("assert-fixture-001",)
            )
            result = evaluate_recovery_authority(root)
            self.assertEqual(
                result.state, RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
            )
            self.assertFalse(result.serving_ready)
            self.assertTrue(result.state.authority_recovered)

    def test_rebuildable_projection_missing_bindings_is_pending(self):
        """Present bodies without binding metadata are rebuildable, not quarantine."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            # Drop binding sidecars only — bodies remain, authority remains valid.
            (root / "knowledge_units.projection.json").unlink()
            (root / "chroma" / "projection_binding.json").unlink()
            result = evaluate_recovery_authority(root)
            self.assertEqual(
                result.state, RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
            )
            self.assertFalse(result.serving_ready)
            self.assertTrue(result.state.authority_recovered)

    def test_empty_chroma_dir_without_sqlite_is_pending(self):
        """Placeholder chroma/ without sqlite is unavailable, not broken."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root, include_chroma=False)
            (root / "chroma").mkdir(exist_ok=True)
            result = evaluate_recovery_authority(root)
            self.assertEqual(
                result.state, RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
            )
            self.assertFalse(result.serving_ready)

    def test_sidecar_cannot_override_missing_body_assertion_ids(self):
        """Body assertion-id set is authoritative; sidecar cannot fill gaps."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root)
            # Empty JSONL body while sidecar still lists matching registry IDs.
            (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
            # Empty Chroma embedding set while binding sidecar still lists IDs.
            db = root / "chroma" / "chroma.sqlite3"
            if db.is_file():
                import sqlite3

                conn = sqlite3.connect(db)
                try:
                    conn.execute("DELETE FROM embeddings")
                    conn.commit()
                finally:
                    conn.close()
            result = evaluate_recovery_authority(root)
            self.assertEqual(result.state, RecoveryState.QUARANTINED)
            self.assertFalse(result.serving_ready)
            self.assertNotEqual(result.state, RecoveryState.PROJECTION_VALIDATED)
            detail = (result.detail + " " + json.dumps(result.reports)).lower()
            self.assertTrue(
                "disagree" in detail or "assertion-id" in detail or "mismatch" in detail,
                msg=result.detail,
            )

    def test_no_state_is_serving_ready(self):
        for state in RecoveryState:
            self.assertFalse(state.is_serving_ready)


class TestT1StillIndependent(unittest.TestCase):
    def test_registry_validation_independent_of_projections(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _seal_candidate(root, with_bindings=False)
            registry = validate_provenance_registry(root)
            self.assertTrue(registry.ok)


if __name__ == "__main__":
    unittest.main()
