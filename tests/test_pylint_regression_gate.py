"""Deterministic tests for the Pylint regression gate."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

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
normalize_message = _gate.normalize_message
pylint_status_ok = _gate.pylint_status_ok
validate_baseline_change = _gate.validate_baseline_change
counter_to_baseline = _gate.counter_to_baseline


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


_R0801_A = (
    "Similar lines in 2 files\n"
    "==adapters.detect:[121:127]\n"
    "==inventory:[94:100]\n"
    "        path.relative_to(sessions_dir)\n"
    "        return True"
)
_R0801_B = (
    "Similar lines in 2 files\n"
    "==adapters.detect:[200:206]\n"
    "==inventory:[150:156]\n"
    "        path.relative_to(sessions_dir)\n"
    "        return True"
)
_R0801_SEMANTIC = (
    "Similar lines in 2 files\n"
    "==adapters.detect:[121:127]\n"
    "==inventory:[94:100]\n"
    "        path.relative_to(OTHER_DIR)\n"
    "        return False"
)


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

    def test_r0801_range_only_movement_same_fingerprint(self):
        a = fingerprint_from_message(
            _msg("work_git.py", "duplicate-code", "R0801", _R0801_A, line=1)
        )
        b = fingerprint_from_message(
            _msg("work_git.py", "duplicate-code", "R0801", _R0801_B, line=1)
        )
        self.assertEqual(a, b)
        self.assertIn("adapters.detect:[#:#]", a[3])
        self.assertIn("inventory:[#:#]", a[3])
        self.assertNotIn("[121:127]", a[3])

    def test_r0801_semantic_body_change_differs(self):
        a = fingerprint_from_message(
            _msg("work_git.py", "duplicate-code", "R0801", _R0801_A)
        )
        b = fingerprint_from_message(
            _msg("work_git.py", "duplicate-code", "R0801", _R0801_SEMANTIC)
        )
        self.assertNotEqual(a, b)


    def test_r0401_cycle_order_canonical(self):
        a = fingerprint_from_message(
            _msg(
                "work_git.py",
                "cyclic-import",
                "R0401",
                "Cyclic import (brief -> doctor -> mcp_server)",
            )
        )
        b = fingerprint_from_message(
            _msg(
                "work_git.py",
                "cyclic-import",
                "R0401",
                "Cyclic import (mcp_server -> brief -> doctor)",
            )
        )
        self.assertEqual(a, b)
        self.assertEqual(
            a[3], "Cyclic import modules: brief, doctor, mcp_server"
        )

    def test_r0801_module_header_order_canonical(self):
        a_msg = (
            "Similar lines in 2 files\n"
            "==inventory:[#:#]\n"
            "==adapters.detect:[#:#]\n"
            "        return True"
        )
        b_msg = (
            "Similar lines in 2 files\n"
            "==adapters.detect:[#:#]\n"
            "==inventory:[#:#]\n"
            "        return True"
        )
        a = fingerprint_from_message(
            _msg("work_git.py", "duplicate-code", "R0801", a_msg)
        )
        b = fingerprint_from_message(
            _msg("work_git.py", "duplicate-code", "R0801", b_msg)
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

    def test_r0801_range_only_movement_passes_vs_baseline(self):
        baseline = count_fingerprints(
            [_msg("work_git.py", "duplicate-code", "R0801", _R0801_A)]
        )
        current = count_fingerprints(
            [_msg("work_git.py", "duplicate-code", "R0801", _R0801_B)]
        )
        ok, lines = compare_reports(baseline, current)
        self.assertTrue(ok, lines)
        # Semantic change still fails
        worse = count_fingerprints(
            [_msg("work_git.py", "duplicate-code", "R0801", _R0801_SEMANTIC)]
        )
        ok2, _ = compare_reports(baseline, worse)
        self.assertFalse(ok2)


class StatusTests(unittest.TestCase):
    def test_status_0_and_30_accepted(self):
        ok0, msg0 = pylint_status_ok(0)
        ok30, msg30 = pylint_status_ok(30)
        self.assertTrue(ok0, msg0)
        self.assertTrue(ok30, msg30)

    def test_status_1_32_33_rejected(self):
        for code in (1, 32, 33):
            ok, msg = pylint_status_ok(code)
            self.assertFalse(ok, msg)
            self.assertIn(str(code), msg)


class BaselineBlessingTests(unittest.TestCase):
    def test_pr_modified_baseline_cannot_hide_new_finding(self):
        """Raising the baseline to include a new finding is rejected."""
        base = count_fingerprints(
            [_msg("a.py", "unused-import", "W0611", "Unused import x")]
        )
        # Branch "blesses" a new finding into the baseline
        blessed = count_fingerprints(
            [
                _msg("a.py", "unused-import", "W0611", "Unused import x"),
                _msg("b.py", "unused-variable", "W0612", "Unused variable hide"),
            ]
        )
        ok, lines = validate_baseline_change(base, blessed)
        self.assertFalse(ok)
        self.assertTrue(any("self-blessing" in line or "FAIL" in line for line in lines))

        # And even if someone tried to use the blessed baseline for compare,
        # ci path compares the *report* to the base reference — new finding fails.
        report = blessed  # live report matches the "blessed" raised baseline
        ok_report, _ = compare_reports(base, report)
        self.assertFalse(ok_report)


class CliTests(unittest.TestCase):
    def test_cli_compare_write_and_status(self):
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
            self.assertEqual(
                main(
                    [
                        "compare",
                        "--baseline",
                        str(baseline),
                        "--report",
                        str(report),
                        "--pylint-status",
                        "30",
                    ]
                ),
                0,
            )
            # Fatal status rejected even with clean report
            self.assertEqual(
                main(
                    [
                        "compare",
                        "--baseline",
                        str(baseline),
                        "--report",
                        str(report),
                        "--pylint-status",
                        "1",
                    ]
                ),
                1,
            )
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
                        "--pylint-status",
                        "0",
                    ]
                ),
                1,
            )

    def test_ci_bootstrap_and_base_ref(self):
        msgs = [_msg("a.py", "unused-import", "W0611", "Unused import x")]
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            report = td_path / "report.json"
            branch_base = td_path / "ci" / "pylint-baseline.json"
            branch_base.parent.mkdir(parents=True)
            report.write_text(json.dumps(msgs), encoding="utf-8")
            branch_base.write_text(
                json.dumps(counter_to_baseline(count_fingerprints(msgs))),
                encoding="utf-8",
            )
            # Empty base-ref → branch HEAD baseline (not BOOTSTRAP)
            self.assertEqual(
                main(
                    [
                        "ci",
                        "--report",
                        str(report),
                        "--pylint-status",
                        "0",
                        "--branch-baseline",
                        str(branch_base),
                        "--base-ref",
                        "",
                    ]
                ),
                0,
            )
            # Nonexistent base SHA (git show fails) → BOOTSTRAP to branch file
            self.assertEqual(
                main(
                    [
                        "ci",
                        "--report",
                        str(report),
                        "--pylint-status",
                        "0",
                        "--branch-baseline",
                        str(branch_base),
                        "--base-ref",
                        "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                    ]
                ),
                0,
            )


if __name__ == "__main__":
    unittest.main()
