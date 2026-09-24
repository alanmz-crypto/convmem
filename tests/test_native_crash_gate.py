"""Tests for doctor._check_native_crash_gate.

Distinct from synthesis_gate's ingest_degraded: this gate counts watch-spawned
index children killed by a native fault (SIGSEGV/SIGABRT/SIGBUS), read from
native_crash_failures.jsonl, which watch.py's circuit breaker writes.
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from doctor import _check_native_crash_gate


def _ts(offset_hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=offset_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


class NativeCrashGateTests(unittest.TestCase):
    def setUp(self):
        # pylint: disable-next=consider-using-with
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.log = Path(tmp_dir.name) / "native_crash_failures.jsonl"
        orig = Path.expanduser
        log_path = self.log

        def _expanduser(self_path):
            if str(self_path).endswith("native_crash_failures.jsonl"):
                return log_path
            return orig(self_path)

        patcher = patch.object(Path, "expanduser", _expanduser)
        self.addCleanup(patcher.stop)
        patcher.start()

    def _write(self, entries):
        self.log.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")

    def test_no_log_file_passes_zero(self):
        check = _check_native_crash_gate()
        self.assertTrue(check.ok, check.detail)
        self.assertIn("0 native crashes", check.detail)

    def test_below_threshold_passes_but_reports_count(self):
        self._write(
            [
                {"ts": _ts(1), "path": "a.jsonl", "message": "index subprocess exit -11"},
                {"ts": _ts(2), "path": "b.jsonl", "message": "index subprocess exit -6"},
            ]
        )
        check = _check_native_crash_gate()
        self.assertTrue(check.ok, check.detail)
        self.assertIn("2 native crash", check.detail)

    def test_at_threshold_fails(self):
        self._write(
            [
                {"ts": _ts(i), "path": f"path-{i}.jsonl", "message": "index subprocess exit -11"}
                for i in (1, 2, 3)
            ]
        )
        check = _check_native_crash_gate()
        self.assertFalse(check.ok, check.detail)
        self.assertIn("3 native crashes", check.detail)

    def test_entries_outside_window_ignored(self):
        self._write(
            [{"ts": _ts(24 * 30), "path": "old.jsonl", "message": "index subprocess exit -11"}]
        )
        check = _check_native_crash_gate()
        self.assertTrue(check.ok, check.detail)
        self.assertIn("0 native crashes", check.detail)

    def test_malformed_lines_are_skipped(self):
        self.log.write_text("not json\n" + json.dumps({"ts": _ts(1), "path": "a.jsonl"}) + "\n")
        check = _check_native_crash_gate()
        self.assertTrue(check.ok, check.detail)
        self.assertIn("1 native crash", check.detail)


if __name__ == "__main__":
    unittest.main()
