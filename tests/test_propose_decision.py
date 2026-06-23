"""Tests for propose_decision queue CLI."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ledger import normalize_ledger_record
from propose_decision import (
    PROPOSAL_KIND,
    approve,
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


if __name__ == "__main__":
    unittest.main()
