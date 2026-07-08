"""Behavioral regression: durable-write CLI paths gate on Restic (fail-closed).

Proves the *wiring*, not just presence (the position-vs-presence trap): with the
Restic gate forced to fail and ``CONVMEM_SKIP_RESTIC_GATE`` unset, both
``add --upsert`` and ``record --approve-last`` must abort AND leave the Chroma
corpus unchanged. Guards against silently removing (or defanging) the inline
``ensure_chroma_snapshot_for_live_write()`` calls in ``convmem.py`` -- a
reference-only check would pass even if the call were wrapped in a swallowed
exception or a dead branch.

The write-lane guard is patched to a no-op so the *only* possible blocker is the
Restic gate; the test asserts the gate actually ran (its subprocess was invoked)
and that no unit was written.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

import convmem
from chroma_store import ChromaStore


def _fake_embed(text, model=None, host=None):
    base = (sum(ord(c) for c in text) % 997) / 997.0
    return [base] * 768


class WriteGateEffectTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp = Path(self.td.name)
        self.chroma_dir = str(self.tmp / "chroma")
        self.cfg = {
            "index": {
                "chroma_dir": self.chroma_dir,
                "units_export": str(self.tmp / "knowledge_units.jsonl"),
            },
            "models": {
                "embed_model": "nomic-embed-text",
                "ollama_host": "http://localhost:11434",
            },
        }
        store = ChromaStore(self.chroma_dir)
        for i in range(3):
            store.add_unit(
                f"seed-{i}",
                f"seed {i}",
                [0.1 * (i + 1)] * 768,
                {
                    "id": f"seed-{i}",
                    "title": f"Seed {i}",
                    "ledger_id": f"obs_seed_{i}",
                    "type": "observation",
                },
            )
        store.close()
        self.baseline = self._count()
        self.assertEqual(self.baseline, 3)
        # The gate must not be short-circuited by the test escape hatch.
        os.environ.pop("CONVMEM_SKIP_RESTIC_GATE", None)
        self.runner = CliRunner()

    def tearDown(self):
        self.td.cleanup()

    def _count(self) -> int:
        store = ChromaStore(self.chroma_dir)
        try:
            return store.count_units()
        finally:
            store.close()

    def _run_gate_failing(self, args):
        """Invoke the CLI with the Restic gate forced to return non-zero."""
        gate_call = MagicMock(
            return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="restic gate forced-fail"
            )
        )
        with patch("config.load_config", return_value=self.cfg), patch(
            "runtime_guard.require_write_consent", return_value=None
        ), patch("restic_gate.subprocess.run", gate_call), patch(
            "llm.ollama_embed", side_effect=_fake_embed
        ):
            result = self.runner.invoke(convmem.app, args)
        return result, gate_call

    def test_add_upsert_blocked_leaves_corpus_unchanged(self):
        obs = self.tmp / "obs.jsonl"
        obs.write_text(
            '{"summary":"gate wiring probe","type":"observation",'
            '"confidence":0.8,"domain":"coding.tooling"}\n',
            encoding="utf-8",
        )
        result, gate_call = self._run_gate_failing(
            ["add", "--file", str(obs), "--upsert"]
        )
        self.assertNotEqual(result.exit_code, 0, "add --upsert should abort on gate failure")
        self.assertGreaterEqual(gate_call.call_count, 1, "the Restic gate must run on this path")
        self.assertEqual(self._count(), self.baseline, "no unit may be written when the gate fails")

    def test_record_approve_last_blocked_leaves_corpus_unchanged(self):
        from propose_decision import propose

        propose(
            self.cfg,
            relates_to="dec_prop_seed_write_gate",
            summary="write-gate wiring test",
            rationale="verify record --approve-last gates before the Chroma index write",
            author="ryan",
        )
        result, gate_call = self._run_gate_failing(["record", "--approve-last"])
        self.assertNotEqual(result.exit_code, 0, "record --approve-last should abort on gate failure")
        self.assertGreaterEqual(gate_call.call_count, 1, "the Restic gate must run on this path")
        self.assertEqual(self._count(), self.baseline, "the approved decision must not reach Chroma when the gate fails")


if __name__ == "__main__":
    unittest.main()
