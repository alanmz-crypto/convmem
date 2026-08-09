"""Tests for the stage-aware synthesis_gate classification.

The gate (doctor._check_synthesis_gate) splits synthesis_failures.jsonl
entries in the 7-day window into three categories:
  - stage in {distill, summarize} -> ingest_degraded (provider drops on
    background jobs, no data loss, WARN-only)
  - stage == "ask"                -> ask_failures (real ask-path failures,
    FAIL at >=3)
  - missing/unknown stage         -> ignored (legacy telemetry from before
    stage tagging was added; not counted as ask, to avoid false-alarms)
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from doctor import _check_synthesis_gate


def _ts(offset_hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=offset_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class SynthesisGateStageTests(unittest.TestCase):
    def setUp(self):
        # pylint: disable-next=consider-using-with
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.log = Path(tmp_dir.name) / "synthesis_failures.jsonl"
        orig = Path.expanduser
        log_path = self.log

        def _expanduser(self_path):
            if str(self_path).endswith("synthesis_failures.jsonl"):
                return log_path
            return orig(self_path)

        patcher = patch.object(Path, "expanduser", _expanduser)
        self.addCleanup(patcher.stop)
        patcher.start()

    def _write(self, entries):
        self.log.write_text(
            "\n".join(json.dumps(e) for e in entries), encoding="utf-8"
        )

    def test_missing_stage_not_counted_as_ask(self):
        self._write([{"ts": _ts(i), "error": f"legacy {i}"} for i in (1, 2, 3)])
        check = _check_synthesis_gate()
        self.assertTrue(check.ok, check.detail)
        self.assertIn("0 ask failures", check.detail)

    def test_distill_summarize_counted_as_ingest_degraded(self):
        self._write([
            {"ts": _ts(1), "stage": "distill", "error": "x"},
            {"ts": _ts(2), "stage": "distill", "error": "x"},
            {"ts": _ts(3), "stage": "summarize", "error": "x"},
        ])
        check = _check_synthesis_gate()
        self.assertTrue(check.ok)
        self.assertIn("3 ingest-degraded", check.detail)

    def test_ask_stage_triggers_fail_at_threshold(self):
        self._write(
            [{"ts": _ts(i), "stage": "ask", "error": "x"} for i in (1, 2, 3)]
        )
        check = _check_synthesis_gate()
        self.assertFalse(check.ok)
        self.assertIn("3 ask failures in 7d", check.detail)

    def test_mixed_classification(self):
        self._write([
            {"ts": _ts(1), "stage": "distill", "error": "x"},
            {"ts": _ts(2), "stage": "summarize", "error": "x"},
            {"ts": _ts(3), "stage": "ask", "error": "x"},
            {"ts": _ts(4), "error": "legacy no stage"},
        ])
        check = _check_synthesis_gate()
        self.assertTrue(check.ok)
        self.assertIn("1 ask failures", check.detail)
        self.assertIn("2 ingest-degraded", check.detail)


if __name__ == "__main__":
    unittest.main()
