"""Deterministic tests for the Pylint regression gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import importlib.util
import sys

_GATE = Path(__file__).resolve().parents[1] / "scripts" / "pylint_regression_gate.py"
_spec = importlib.util.spec_from_file_location("pylint_regression_gate", _GATE)
assert _spec and _spec.loader
_gate = importlib.util.module_from_spec(_spec)
sys.modules["pylint_regression_gate"] = _gate
_spec.loader.exec_module(_gate)
baseline_to_counter = _gate.baseline_to_counter
compare_reports = _gate.compare_reports
count_fingerprints = _gate.count_fingerprints
find_regressions = _gate.find_regressions
fingerprint_from_message = _gate.fingerprint_from_message
main = _gate.main


def _msg(
    path: str,
    symbol: str,
    msg_id: str,
    message: str,
    *,
    line: int = 1,
) -> dict:
    return {
        "path": path,
        "symbol": symbol,
        "message-id": msg_id,
        "message": message,
        "line": line,
        "column": 0,
        "type": "warning",
    }


class FingerprintTests(unittest.TestCase):
    def test_line_ignored_in_fingerprint(self):
        a = fingerprint_from_message(
            _msg("a.py", "unused-import", "W0611", "Unused import x", line=10)
        )
        b = fingerprint_from_message(
            _msg("a.py", "unused-import", "W0611", "Unused import x", line=99)
        )
        self.assertEqual(a, b)

    def test_path_normalization(self):
        a = fingerprint_from_message(
            _msg("./pkg/a.py", "unused-import", "W0611", "Unused import x")
        )
        b = fingerprint_from_message(
            _msg("pkg/a.py", "unused-import", "W0611", "Unused import x")
        )
        self.assertEqual(a, b)


class CompareTests(unittest.TestCase):
    def test_identical_baseline_passes(self):
        msgs = [
            _msg("a.py", "unused-import", "W0611", "Unused import x", line=1),
            _msg("b.py", "line-too-long", "C0301", "Line too long", line=2),
        ]
        counts = count_fingerprints(msgs)
        ok, lines = compare_reports(counts, counts)
        self.assertTrue(ok)
        self.assertTrue(any("PASS" in line for line in lines))

    def test_new_message_fails(self):
        baseline = count_fingerprints(
            [_msg("a.py", "unused-import", "W0611", "Unused import x")]
        )
        current = count_fingerprints(
            [
                _msg("a.py", "unused-import", "W0611", "Unused import x"),
                _msg("a.py", "unused-variable", "W0612", "Unused variable y"),
            ]
        )
        ok, lines = compare_reports(baseline, current)
        self.assertFalse(ok)
        self.assertTrue(any("FAIL" in line for line in lines))
        self.assertTrue(any("W0612" in line for line in lines))

    def test_increased_duplicate_count_fails(self):
        baseline = count_fingerprints(
            [_msg("a.py", "unused-import", "W0611", "Unused import x", line=1)]
        )
        current = count_fingerprints(
            [
                _msg("a.py", "unused-import", "W0611", "Unused import x", line=1),
                _msg("a.py", "unused-import", "W0611", "Unused import x", line=50),
            ]
        )
        regs = find_regressions(baseline, current)
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0][1], 1)
        self.assertEqual(regs[0][2], 2)
        ok, _ = compare_reports(baseline, current)
        self.assertFalse(ok)

    def test_removed_findings_pass(self):
        baseline = count_fingerprints(
            [
                _msg("a.py", "unused-import", "W0611", "Unused import x"),
                _msg("b.py", "line-too-long", "C0301", "Line too long"),
            ]
        )
        current = count_fingerprints(
            [_msg("a.py", "unused-import", "W0611", "Unused import x")]
        )
        ok, lines = compare_reports(baseline, current)
        self.assertTrue(ok)
        self.assertTrue(any("PASS" in line for line in lines))

    def test_line_only_changes_do_not_fail(self):
        baseline = count_fingerprints(
            [
                _msg("a.py", "unused-import", "W0611", "Unused import x", line=3),
                _msg("a.py", "unused-import", "W0611", "Unused import x", line=4),
            ]
        )
        current = count_fingerprints(
            [
                _msg("a.py", "unused-import", "W0611", "Unused import x", line=100),
                _msg("a.py", "unused-import", "W0611", "Unused import x", line=200),
            ]
        )
        ok, _ = compare_reports(baseline, current)
        self.assertTrue(ok)

    def test_cli_compare_and_write_baseline(self):
        msgs = [_msg("a.py", "unused-import", "W0611", "Unused import x", line=7)]
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            report = td_path / "report.json"
            baseline = td_path / "baseline.json"
            report.write_text(json.dumps(msgs), encoding="utf-8")
            self.assertEqual(
                main(
                    [
                        "write-baseline",
                        "--report",
                        str(report),
                        "--output",
                        str(baseline),
                    ]
                ),
                0,
            )
            loaded = baseline_to_counter(json.loads(baseline.read_text()))
            self.assertEqual(loaded, count_fingerprints(msgs))
            self.assertEqual(
                main(
                    [
                        "compare",
                        "--baseline",
                        str(baseline),
                        "--report",
                        str(report),
                    ]
                ),
                0,
            )
            # Extra finding fails CLI
            worse = td_path / "worse.json"
            worse.write_text(
                json.dumps(
                    msgs
                    + [_msg("b.py", "line-too-long", "C0301", "Line too long (99/80)")]
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                main(
                    [
                        "compare",
                        "--baseline",
                        str(baseline),
                        "--report",
                        str(worse),
                    ]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
