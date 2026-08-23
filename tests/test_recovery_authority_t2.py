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
