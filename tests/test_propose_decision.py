"""Tests for propose_decision queue CLI."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ledger import normalize_ledger_record
from propose_decision import (
    PROPOSAL_KIND,
    approve,
    ingest_approved_ledger,
    latest_pending,
    list_proposals,
    propose,
    queue_path,
    reject,
)


class ProposeDecisionTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.cfg = {
            "index": {
                "chroma_dir": str(Path(self.td.name) / "chroma"),
            }
        }

    def tearDown(self):
        self.td.cleanup()

    def test_propose_writes_pending_queue(self):
        rec = propose(
            self.cfg,
            relates_to="dec_convmem_no_auto_merge",
            summary="Test decision",
            rationale="Because testing",
            author="cursor-implementer",
        )
        self.assertEqual(rec["kind"], PROPOSAL_KIND)
        self.assertEqual(rec["status"], "PENDING")
        qfile = queue_path(self.cfg)
        self.assertTrue(qfile.is_file())
        lines = qfile.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["id"], rec["id"])

    def test_list_pending_only_by_default(self):
        propose(
            self.cfg,
            relates_to="dec_a",
            summary="One",
            rationale="R1",
            author="cursor",
        )
        pending = list_proposals(self.cfg)
        self.assertEqual(len(pending), 1)
        pid = pending[0]["id"]
        approve(self.cfg, pid, signer="kiro-review")
        self.assertEqual(len(list_proposals(self.cfg)), 0)
        self.assertEqual(len(list_proposals(self.cfg, show_all=True)), 1)

    def test_approve_writes_ledger_shape(self):
        rec = propose(
            self.cfg,
            relates_to="dec_convmem_workspace_standard",
            summary="Approve me",
            rationale="Good idea",
            author="chatgpt",
            alternatives=["bad"],
            constraints=["no chroma auto-write"],
        )
        _, ledger = approve(
            self.cfg,
            rec["id"],
            signer="ryan",
            ledger_id="dec_test_approved",
        )
        unit = normalize_ledger_record(ledger)
        self.assertIsNotNone(unit)
        self.assertEqual(ledger["id"], "dec_test_approved")
        self.assertEqual(ledger["author_model"], "ryan")
        self.assertEqual(ledger["relates_to"], "dec_convmem_workspace_standard")
        self.assertEqual(ledger["proposal_id"], rec["id"])

    def test_recovery_uses_proposal_id_not_reused_ledger_id(self):
        from propose_decision import approved_for_proposal, recovery_action
        rec = propose(self.cfg, relates_to="dec_a", summary="One", rationale="R", author="cursor")
        _, ledger = approve(self.cfg, rec["id"], signer="ryan", ledger_id="dec_shared")
        self.assertEqual(approved_for_proposal(self.cfg, rec["id"]), ledger)
        self.assertEqual(recovery_action(self.cfg, rec["id"], base_hash="b", proposed_hash="p"), "retry_chroma")
        self.assertEqual(recovery_action(self.cfg, rec["id"], live_hash="p", proposed_hash="p"), "repair_marker")

    def test_governed_apply_rejects_sibling_stale_and_create_collision(self):
        from propose_decision import validate_governed_apply
        common = {"unresolved_targets": set(), "proposal_id": "p", "proposed_ledger_id": "dec_new"}
        assert validate_governed_apply(target_ledger_id="dec_a", live_hash="new", base_hash="old", **common) == "stale_base"
        assert validate_governed_apply(target_ledger_id=None, live_hash="exists", base_hash=None, **common) == "create_target_exists"
        common["unresolved_targets"] = {"dec_a"}
        assert validate_governed_apply(target_ledger_id="dec_a", live_hash="old", base_hash="old", **common) == "pending_sibling"

    @patch("observe.ingest_observation")
    def test_ingest_approved_ledger_indexes_one(self, mock_ingest):
        mock_ingest.return_value = {"id": "u1", "ledger_id": "dec_test_approved"}
        ledger = {
            "id": "dec_test_approved",
            "kind": "decision",
            "status": "accepted",
            "relates_to": "dec_parent",
            "summary": "Fast index",
            "rationale": "One record only",
            "author_model": "ryan",
        }
        stats = ingest_approved_ledger(self.cfg, ledger)
        self.assertEqual(stats["accepted"], 1)
        mock_ingest.assert_called_once()

    def test_reject_requires_reason(self):
        rec = propose(
            self.cfg,
            relates_to="dec_a",
            summary="No",
            rationale="R",
            author="cursor",
        )
        with self.assertRaises(ValueError):
            reject(self.cfg, rec["id"], signer="ryan", reason="")
        out = reject(self.cfg, rec["id"], signer="ryan", reason="duplicate")
        self.assertEqual(out["status"], "REJECTED")

    def test_invalid_signer_rejected(self):
        rec = propose(
            self.cfg,
            relates_to="dec_a",
            summary="S",
            rationale="R",
            author="cursor",
        )
        with self.assertRaises(ValueError):
            approve(self.cfg, rec["id"], signer="cursor-implementer")

    def test_proposal_kind_not_ledger_ingestible(self):
        raw = {"kind": PROPOSAL_KIND, "summary": "x", "author_model": "a", "relates_to": "y"}
        self.assertIsNone(normalize_ledger_record(raw))

    def test_collect_interactive_fields(self):
        from propose_decision import collect_interactive_fields

        answers = iter(
            [
                "dec_parent",
                "One sentence summary",
                "Because reasons",
                "kiro-session",
                "coding.tooling",
                "",
                "",
            ]
        )

        def fake_prompt(label, default=""):
            return next(answers) or default

        fields = collect_interactive_fields(prompt=fake_prompt)
        self.assertEqual(fields["relates_to"], "dec_parent")
        self.assertEqual(fields["summary"], "One sentence summary")
        self.assertEqual(fields["author"], "kiro-session")

    def test_interactive_lock_exclusive(self):
        from propose_decision import InteractiveLockError, interactive_session_lock

        with interactive_session_lock(self.cfg):
            with self.assertRaises(InteractiveLockError):
                with interactive_session_lock(self.cfg):
                    pass

    def test_confirm_interactive_submit_false_cancels(self):
        from unittest.mock import patch

        from propose_decision import confirm_interactive_submit

        fields = {
            "summary": "Test",
            "relates_to": "dec_a",
            "author": "cursor",
        }
        with patch(
            "propose_decision.interactive_submit_snapshot",
            return_value={
                "brief_at": "2026-06-23T00:00:00Z",
                "stale_handoff": False,
                "stale_file": None,
                "pending": [],
            },
        ):
            ok = confirm_interactive_submit(
                self.cfg,
                fields,
                confirm=lambda *a, **k: False,
                echo=lambda *a, **k: None,
            )
        self.assertFalse(ok)

    def test_latest_pending_returns_newest(self):
        r1 = propose(
            self.cfg,
            relates_to="dec_a",
            summary="First",
            rationale="R1",
            author="cursor",
        )
        r2 = propose(
            self.cfg,
            relates_to="dec_b",
            summary="Second",
            rationale="R2",
            author="cursor",
        )
        latest = latest_pending(self.cfg)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["id"], r2["id"])
        self.assertNotEqual(latest["id"], r1["id"])

    def test_latest_pending_empty_queue(self):
        self.assertIsNone(latest_pending(self.cfg))

    def test_format_proposal_review_full_fields(self):
        from propose_decision import format_proposal_review

        card = format_proposal_review(
            {
                "id": "dec_prop_review_full",
                "status": "PENDING",
                "summary": "Ship human review cards",
                "rationale": "Line one\nLine two",
                "relates_to": "dec_parent",
                "proposed_by": "cursor",
                "proposed_at": "2026-07-13T18:00:00Z",
                "domain": "coding.tooling",
                "site": "example.com",
                "confidence": 0.9,
                "target_ledger_id": "dec_target",
                "alternatives_rejected": ["blind approve", "web UI\nphase 2"],
                "constraints": ["JSONL canonical", "no --yes"],
            }
        )
        for needle in (
            "id: dec_prop_review_full",
            "status: PENDING",
            "summary: Ship human review cards",
            "rationale:",
            "Line one",
            "Line two",
            "relates_to: dec_parent",
            "proposed_by: cursor",
            "proposed_at: 2026-07-13T18:00:00Z",
            "domain: coding.tooling",
            "site: example.com",
            "confidence: 0.9",
            "target_ledger_id: dec_target",
            "alternatives_rejected:",
            "- blind approve",
            "- web UI",
            "phase 2",
            "constraints:",
            "- JSONL canonical",
            "- no --yes",
        ):
            self.assertIn(needle, card)

    def test_format_proposal_review_missing_optionals(self):
        from propose_decision import format_proposal_review

        card = format_proposal_review({"id": "dec_prop_sparse"})
        self.assertIn("id: dec_prop_sparse", card)
        self.assertIn("status: PENDING", card)
        self.assertIn("site: (none)", card)
        self.assertIn("target_ledger_id: (none)", card)
        self.assertIn("alternatives_rejected:", card)
        self.assertIn("constraints:", card)
        self.assertIn("(none)", card)
        self.assertNotIn("None", card.split("confidence:", 1)[1].splitlines()[0])


if __name__ == "__main__":
    unittest.main()
