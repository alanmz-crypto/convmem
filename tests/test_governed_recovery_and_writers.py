"""N8–N12 recovery, hash_schema_version, and per-surface writer gates."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from conflict_events import load_events, reduce_events
from propose_decision import (
    approve,
    approve_and_ingest,
    approved_for_proposal,
    propose,
    recover_approval,
    recovery_action,
)


class HashSchemaOnProposed(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.cfg = {"index": {"chroma_dir": str(Path(self.td.name) / "chroma")}}

    def tearDown(self):
        self.td.cleanup()

    def test_proposed_event_persists_hash_schema_version_1(self):
        rec = propose(
            self.cfg,
            relates_to="dec_a",
            summary="Schema check",
            rationale="Must persist v1",
            author="cursor",
        )
        events = load_events(self.cfg)
        proposed = [e for e in events if e.get("event_type") == "PROPOSED"][-1]
        self.assertEqual(proposed["proposal"].get("hash_schema_version"), 1)
        self.assertTrue(proposed["proposal"].get("proposed_content_hash"))
        self.assertEqual(rec.get("hash_schema_version"), 1)


class NestedLockApproveAndIngest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.cfg = {"index": {"chroma_dir": str(Path(self.td.name) / "chroma")}}

    def tearDown(self):
        self.td.cleanup()

    @patch("propose_decision.ingest_approved_ledger")
    def test_approve_and_ingest_does_not_deadlock(self, mock_ingest):
        mock_ingest.return_value = {"accepted": 1, "rejected": 0, "updated": 0, "skipped": 0}
        rec = propose(
            self.cfg,
            relates_to="dec_a",
            summary="No deadlock",
            rationale="Single flock",
            author="cursor",
        )
        proposal, ledger, stats = approve_and_ingest(self.cfg, rec["id"], signer="ryan")
        self.assertEqual(proposal["status"], "APPROVED")
        self.assertEqual(ledger["proposal_id"], rec["id"])
        self.assertEqual(stats["accepted"], 1)
        states = reduce_events(load_events(self.cfg))
        self.assertEqual(states[rec["id"]]["lifecycle_state"], "APPROVED")


class RecoveryMatrix(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.cfg = {"index": {"chroma_dir": str(Path(self.td.name) / "chroma")}}

    def tearDown(self):
        self.td.cleanup()

    def test_n12_approved_jsonl_keeps_proposal_id(self):
        rec = propose(
            self.cfg,
            relates_to="dec_a",
            summary="N12",
            rationale="proposal keyed",
            author="cursor",
        )
        _, ledger = approve(self.cfg, rec["id"], signer="ryan", ledger_id="dec_shared")
        self.assertEqual(ledger["proposal_id"], rec["id"])
        self.assertEqual(approved_for_proposal(self.cfg, rec["id"])["id"], "dec_shared")

    @patch("propose_decision.ingest_approved_ledger")
    def test_n8_retry_chroma_then_approved(self, mock_ingest):
        mock_ingest.return_value = {"accepted": 1, "rejected": 0, "updated": 0, "skipped": 0}
        rec = propose(
            self.cfg,
            relates_to="dec_a",
            summary="Retry chroma",
            rationale="approved jsonl first",
            author="cursor",
        )
        # Interrupt after APPROVAL_STARTED + approved JSONL (no Chroma, no APPROVED).
        approve(self.cfg, rec["id"], signer="ryan")
        states = reduce_events(load_events(self.cfg))
        self.assertEqual(states[rec["id"]]["lifecycle_state"], "APPROVAL_STARTED")
        with patch("propose_decision.live_decision_snapshot", return_value=("", "")):
            action = recover_approval(self.cfg, rec["id"])
        self.assertEqual(action, "retry_chroma")
        mock_ingest.assert_called()
        states = reduce_events(load_events(self.cfg))
        self.assertEqual(states[rec["id"]]["lifecycle_state"], "APPROVED")

    @patch("propose_decision.ingest_approved_ledger")
    def test_n9_marker_and_hash_append_approved(self, mock_ingest):
        rec = propose(
            self.cfg,
            relates_to="dec_a",
            summary="Marker done",
            rationale="chroma already applied",
            author="cursor",
        )
        approve(self.cfg, rec["id"], signer="ryan")
        proposed = reduce_events(load_events(self.cfg))[rec["id"]]["proposal"][
            "proposed_content_hash"
        ]
        with patch(
            "propose_decision.live_decision_snapshot",
            return_value=(rec["id"], proposed),
        ):
            action = recover_approval(self.cfg, rec["id"])
        self.assertEqual(action, "approve")
        mock_ingest.assert_not_called()
        self.assertEqual(
            reduce_events(load_events(self.cfg))[rec["id"]]["lifecycle_state"], "APPROVED"
        )

    @patch("propose_decision.ingest_approved_ledger")
    def test_n10_uncertain_upsert_leaves_approval_started(self, mock_ingest):
        mock_ingest.side_effect = RuntimeError("chroma timeout")
        rec = propose(
            self.cfg,
            relates_to="dec_a",
            summary="Uncertain",
            rationale="leave started",
            author="cursor",
        )
        with self.assertRaises(RuntimeError):
            approve_and_ingest(self.cfg, rec["id"], signer="ryan")
        states = reduce_events(load_events(self.cfg))
        self.assertEqual(states[rec["id"]]["lifecycle_state"], "APPROVAL_STARTED")
        self.assertIsNotNone(approved_for_proposal(self.cfg, rec["id"]))


class WriterSurfacesN11(unittest.TestCase):
    def test_observe_gate_blocks_dec_upsert(self):
        from observe import _reject_governed_bypass

        with self.assertRaises(ValueError):
            _reject_governed_bypass({"id": "dec_shared", "summary": "x"}, upsert=True)

    def test_chroma_add_unit_blocks_dec_replace_without_proposal_id(self):
        from chroma_store import ChromaStore

        with tempfile.TemporaryDirectory() as td:
            store = ChromaStore(str(Path(td) / "chroma"))
            emb = [0.1] * 384
            # First create without proposal_id is allowed (legacy seed).
            store.add_unit(
                "u1",
                "doc",
                emb,
                {"ledger_id": "dec_shared", "type": "decision"},
            )
            with self.assertRaises(ValueError):
                store.add_unit(
                    "u1",
                    "doc2",
                    emb,
                    {"ledger_id": "dec_shared", "type": "decision"},
                )

    def test_chroma_add_unit_allows_protocol_replace(self):
        from chroma_store import ChromaStore

        with tempfile.TemporaryDirectory() as td:
            store = ChromaStore(str(Path(td) / "chroma"))
            emb = [0.1] * 384
            store.add_unit(
                "u1",
                "doc",
                emb,
                {"ledger_id": "dec_shared", "type": "decision"},
            )
            store.add_unit(
                "u1",
                "doc2",
                emb,
                {
                    "ledger_id": "dec_shared",
                    "type": "decision",
                    "proposal_id": "dec_prop_x",
                },
            )

    def test_ingest_observation_path_blocks_monitor_style_dec_upsert(self):
        from observe import ingest_observation

        store = MagicMock()
        with self.assertRaises(ValueError):
            ingest_observation(
                {
                    "id": "dec_shared",
                    "kind": "decision",
                    "status": "accepted",
                    "relates_to": "dec_a",
                    "summary": "bypass",
                    "rationale": "no",
                    "author_model": "monitor",
                },
                store=store,
                embed_model="x",
                ollama_host="http://127.0.0.1:9",
                upsert=True,
            )


if __name__ == "__main__":
    unittest.main()
