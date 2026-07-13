"""CLI tests for human-readable pending-decision review before approve."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

import convmem
from propose_decision import approve, format_proposal_review, list_proposals, propose, queue_path, reject


class RecordReviewCliTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp = Path(self.td.name)
        self.cfg = {
            "index": {
                "chroma_dir": str(self.tmp / "chroma"),
                "units_export": str(self.tmp / "knowledge_units.jsonl"),
            },
            "models": {
                "embed_model": "nomic-embed-text",
                "ollama_host": "http://localhost:11434",
            },
        }
        self.runner = CliRunner()

    def tearDown(self):
        self.td.cleanup()

    def _invoke(self, args, *, input_text=None):
        with patch("config.load_config", return_value=self.cfg), patch(
            "runtime_guard.require_write_consent", return_value=None
        ):
            return self.runner.invoke(convmem.app, args, input=input_text)

    def _seed(self, **kwargs):
        defaults = dict(
            relates_to="dec_parent",
            summary="Review card seed",
            rationale="Why approve matters\nsecond line",
            author="cursor",
            alternatives=["blind approve"],
            constraints=["JSONL canonical"],
            domain="coding.tooling",
            site="",
            confidence=0.75,
        )
        defaults.update(kwargs)
        return propose(self.cfg, **defaults)

    def test_list_renders_full_card(self):
        rec = self._seed(site="staging.example", target_ledger_id="dec_target")
        result = self._invoke(["record", "--list"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(format_proposal_review(rec).splitlines()[0], result.output)
        self.assertIn("rationale:", result.output)
        self.assertIn("second line", result.output)
        self.assertIn("- blind approve", result.output)
        self.assertIn("- JSONL canonical", result.output)
        self.assertIn("target_ledger_id: dec_target", result.output)

    def test_list_json_unchanged_machine_path(self):
        rec = self._seed()
        result = self._invoke(["record", "--list", "--json"])
        self.assertEqual(result.exit_code, 0, result.output)
        rows = [json.loads(line) for line in result.output.strip().splitlines() if line.strip()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], rec["id"])
        self.assertEqual(rows[0]["summary"], rec["summary"])
        self.assertEqual(rows[0]["rationale"], rec["rationale"])
        self.assertNotIn("── Decision draft ──", result.output)
        self.assertNotIn("Approve this draft?", result.output)

    def test_approve_cancel_writes_nothing(self):
        rec = self._seed()
        q_before = queue_path(self.cfg).read_text(encoding="utf-8")
        with patch("restic_gate.ensure_chroma_snapshot_for_live_write") as snap, patch(
            "propose_decision.approve", wraps=approve
        ) as wrapped_approve, patch(
            "propose_decision.approve_and_ingest"
        ) as ingest:
            result = self._invoke(["record", "--approve", rec["id"]], input_text="n\n")
        self.assertNotEqual(result.exit_code, 0, result.output)
        self.assertIn("── Decision draft ──", result.output)
        self.assertIn("Approve this draft?", result.output)
        self.assertIn("Cancelled", result.output)
        snap.assert_not_called()
        ingest.assert_not_called()
        wrapped_approve.assert_not_called()
        self.assertEqual(queue_path(self.cfg).read_text(encoding="utf-8"), q_before)
        self.assertEqual(len(list_proposals(self.cfg)), 1)

    def test_approve_eof_writes_nothing(self):
        rec = self._seed()
        q_before = queue_path(self.cfg).read_text(encoding="utf-8")
        with patch("restic_gate.ensure_chroma_snapshot_for_live_write") as snap, patch(
            "propose_decision.approve_and_ingest"
        ) as ingest:
            result = self._invoke(["record", "--approve-last"], input_text="")
        self.assertNotEqual(result.exit_code, 0, result.output)
        self.assertIn("── Decision draft ──", result.output)
        snap.assert_not_called()
        ingest.assert_not_called()
        self.assertEqual(queue_path(self.cfg).read_text(encoding="utf-8"), q_before)

    def test_approve_yes_after_preview(self):
        rec = self._seed()
        ledger = {"id": rec["id"], "summary": rec["summary"]}
        mock_ingest = MagicMock(
            return_value=(rec, ledger, {"accepted": 1, "updated": 0, "skipped": 0})
        )
        with patch("restic_gate.ensure_chroma_snapshot_for_live_write") as snap, patch(
            "propose_decision.approve_and_ingest", mock_ingest
        ):
            result = self._invoke(["record", "--approve", rec["id"]], input_text="y\n")
        self.assertEqual(result.exit_code, 0, result.output)
        preview_at = result.output.find("── Decision draft ──")
        prompt_at = result.output.find("Approve this draft?")
        finish_at = result.output.find("✓ Recorded:")
        self.assertGreaterEqual(preview_at, 0)
        self.assertGreater(prompt_at, preview_at)
        self.assertGreater(finish_at, prompt_at)
        snap.assert_called_once()
        mock_ingest.assert_called_once()

    def test_approve_last_yes_after_preview(self):
        older = self._seed(summary="Older draft")
        newer = self._seed(summary="Newer draft")
        ledger = {"id": newer["id"], "summary": newer["summary"]}
        mock_ingest = MagicMock(
            return_value=(newer, ledger, {"accepted": 1, "updated": 0, "skipped": 0})
        )
        with patch("restic_gate.ensure_chroma_snapshot_for_live_write"), patch(
            "propose_decision.approve_and_ingest", mock_ingest
        ):
            result = self._invoke(["record", "--approve-last"], input_text="y\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(newer["id"], result.output)
        self.assertIn("Newer draft", result.output)
        self.assertNotIn(older["id"], result.output.split("Approve this draft?", 1)[0])
        mock_ingest.assert_called_once()
        self.assertEqual(mock_ingest.call_args.args[1], newer["id"])

    def test_propose_decision_alias_shares_review_path(self):
        rec = self._seed()
        result = self._invoke(["propose_decision", "--list"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("── Decision draft ──", result.output)
        self.assertIn(rec["id"], result.output)
        with patch("restic_gate.ensure_chroma_snapshot_for_live_write") as snap:
            cancelled = self._invoke(
                ["propose_decision", "--approve-last"], input_text="n\n"
            )
        self.assertNotEqual(cancelled.exit_code, 0)
        self.assertIn("Approve this draft?", cancelled.output)
        snap.assert_not_called()

    def test_list_all_stays_compact_with_rejection_reason(self):
        pending = self._seed(summary="Still pending")
        approved = self._seed(summary="Already approved")
        approve(self.cfg, approved["id"], signer="ryan")
        rejected = self._seed(summary="Already rejected")
        reject(self.cfg, rejected["id"], signer="ryan", reason="duplicate of parent")
        result = self._invoke(["record", "--list", "--all"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("ALL (", result.output)
        self.assertNotIn("── Decision draft ──", result.output)
        self.assertNotIn("rationale:", result.output)
        self.assertNotIn("alternatives_rejected:", result.output)
        self.assertIn(f"  {pending['id']}  [PENDING]", result.output)
        self.assertIn(f"  {approved['id']}  [APPROVED]", result.output)
        self.assertIn(f"  {rejected['id']}  [REJECTED]", result.output)
        self.assertIn("rejected: duplicate of parent", result.output)
        # Compact history lines, not full review cards.
        self.assertIn("proposed by cursor · relates_to dec_parent", result.output)

    def test_approve_non_pending_fails_before_confirm(self):
        approved = self._seed(summary="Done")
        approve(self.cfg, approved["id"], signer="ryan")
        rejected = self._seed(summary="Nope")
        reject(self.cfg, rejected["id"], signer="ryan", reason="stale")
        q_before = queue_path(self.cfg).read_text(encoding="utf-8")

        for pid, status in ((approved["id"], "APPROVED"), (rejected["id"], "REJECTED")):
            with patch("restic_gate.ensure_chroma_snapshot_for_live_write") as snap, patch(
                "propose_decision.approve_and_ingest"
            ) as ingest, patch("propose_decision.approve") as do_approve:
                result = self._invoke(["record", "--approve", pid], input_text="y\n")
            self.assertNotEqual(result.exit_code, 0, result.output)
            self.assertIn("not PENDING", result.output)
            self.assertIn(status, result.output)
            self.assertNotIn("Approve this draft?", result.output)
            self.assertNotIn("── Decision draft ──", result.output)
            snap.assert_not_called()
            ingest.assert_not_called()
            do_approve.assert_not_called()
        self.assertEqual(queue_path(self.cfg).read_text(encoding="utf-8"), q_before)


if __name__ == "__main__":
    unittest.main()
