"""Deterministic tests for the Pylint regression gate."""

from __future__ import annotations

import importlib.util
import subprocess
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

_GATE = Path(__file__).resolve().parents[1] / "scripts" / "pylint_regression_gate.py"
_spec = importlib.util.spec_from_file_location("pylint_regression_gate", _GATE)
assert _spec and _spec.loader
_gate = importlib.util.module_from_spec(_spec)
sys.modules["pylint_regression_gate"] = _gate
_spec.loader.exec_module(_gate)

baseline_to_counter = _gate.baseline_to_counter
BaselineResolveError = _gate.BaselineResolveError
ensure_git_commit = _gate.ensure_git_commit
resolve_baseline_bytes = _gate.resolve_baseline_bytes
probe_baseline_path_in_commit = _gate.probe_baseline_path_in_commit
git_show_text = _gate.git_show_text
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
        self.assertEqual(a, ("*", "duplicate-code", "R0801", ""))

    def test_baseline_loads_aggregate_r0801(self):
        """Stored aggregate R0801 rows must match live fingerprints (empty message)."""
        baseline = {
            "version": 1,
            "fingerprint": ["path", "symbol", "msg_id", "message"],
            "findings": [
                {
                    "path": "*",
                    "symbol": "duplicate-code",
                    "msg_id": "R0801",
                    "message": "",
                    "count": 72,
                }
            ],
        }
        counts = baseline_to_counter(baseline)
        live = fingerprint_from_message(
            _msg("work_git.py", "duplicate-code", "R0801", _R0801_A)
        )
        self.assertEqual(counts[live], 72)
        ok, _ = compare_reports(
            counts,
            count_fingerprints(
                [_msg("x.py", "duplicate-code", "R0801", _R0801_A) for _ in range(72)]
            ),
        )
        self.assertTrue(ok)

    def test_r0801_aggregated_fingerprint(self):
        """R0801 messages collapse to one aggregate key (CI pairing flakes)."""
        a = fingerprint_from_message(
            _msg("work_git.py", "duplicate-code", "R0801", _R0801_A)
        )
        b = fingerprint_from_message(
            _msg("other.py", "duplicate-code", "R0801", _R0801_SEMANTIC)
        )
        self.assertEqual(a, b)
        self.assertEqual(a[0], "*")
        self.assertEqual(a[2], "R0801")


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
        self.assertEqual(a, ("*", "cyclic-import", "R0401", ""))

    def test_r0801_distinct_bodies_still_aggregate(self):
        """Different bodies/ranges collapse — aggregate blind spot by design."""
        a = fingerprint_from_message(
            _msg(
                "work_git.py",
                "duplicate-code",
                "R0801",
                "Similar lines in 2 files\n==a:[1:2]\n==b:[3:4]\n        return True",
            )
        )
        b = fingerprint_from_message(
            _msg(
                "work_git.py",
                "duplicate-code",
                "R0801",
                "Similar lines in 2 files\n==b:[9:10]\n==a:[7:8]\n    return   True",
            )
        )
        self.assertEqual(a, b)

    def test_r0801_module_header_order_irrelevant_under_aggregate(self):
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
        """Exact-shape: range-only movement shares the aggregate fingerprint."""
        baseline = count_fingerprints(
            [_msg("work_git.py", "duplicate-code", "R0801", _R0801_A)]
        )
        current = count_fingerprints(
            [_msg("work_git.py", "duplicate-code", "R0801", _R0801_B)]
        )
        ok, lines = compare_reports(baseline, current)
        self.assertTrue(ok, lines)

    def test_r0801_increased_aggregate_count_fails(self):
        baseline = count_fingerprints(
            [_msg("work_git.py", "duplicate-code", "R0801", _R0801_A)]
        )
        current = count_fingerprints(
            [
                _msg("work_git.py", "duplicate-code", "R0801", _R0801_A),
                _msg("other.py", "duplicate-code", "R0801", _R0801_SEMANTIC),
            ]
        )
        ok, lines = compare_reports(baseline, current)
        self.assertFalse(ok)
        self.assertTrue(any("R0801" in line for line in lines))

    def test_r0801_equal_count_semantic_replacement_is_blind_spot(self):
        """Documented blind spot: equal aggregate count, different body → PASS."""
        baseline = count_fingerprints(
            [_msg("work_git.py", "duplicate-code", "R0801", _R0801_A)]
        )
        replaced = count_fingerprints(
            [_msg("work_git.py", "duplicate-code", "R0801", _R0801_SEMANTIC)]
        )
        ok, _ = compare_reports(baseline, replaced)
        self.assertTrue(ok)


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

    def test_ci_empty_base_ref_uses_branch_file(self):
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

    def test_invalid_base_ref_fails_closed(self):
        """deadbeef / unresolvable SHA must FAIL — never bootstrap."""
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
                1,
            )
            with self.assertRaises(BaselineResolveError):
                ensure_git_commit("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")


class GitProvenanceTests(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()

    def _init_repo(self, repo: Path) -> None:
        self._git(repo, "init")
        self._git(repo, "config", "user.email", "test@example.com")
        self._git(repo, "config", "user.name", "Test")
        # Avoid depending on default-branch name across git versions.
        self._git(repo, "checkout", "-b", "main")

    def test_valid_commit_without_baseline_bootstraps(self):
        msgs = [_msg("a.py", "unused-import", "W0611", "Unused import x")]
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            self._init_repo(repo)
            (repo / "README").write_text("seed\n", encoding="utf-8")
            self._git(repo, "add", "README")
            self._git(repo, "commit", "-m", "seed without baseline")
            sha = self._git(repo, "rev-parse", "HEAD")

            report = repo / "report.json"
            branch_base = repo / "ci" / "pylint-baseline.json"
            branch_base.parent.mkdir(parents=True)
            report.write_text(json.dumps(msgs), encoding="utf-8")
            branch_base.write_text(
                json.dumps(counter_to_baseline(count_fingerprints(msgs))),
                encoding="utf-8",
            )

            raw, provenance = resolve_baseline_bytes(
                base_ref=sha,
                branch_baseline=branch_base,
                git_cwd=repo,
            )
            self.assertTrue(provenance.startswith("BOOTSTRAP"), provenance)
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
                        sha,
                        "--git-cwd",
                        str(repo),
                    ]
                ),
                0,
            )
            del raw

    def test_path_probe_git_failure_rejects_bootstrap(self):
        """Simulated ls-tree failure must not bootstrap; CI returns failure."""
        msgs = [_msg("a.py", "unused-import", "W0611", "Unused import x")]
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            self._init_repo(repo)
            (repo / "README").write_text("seed\n", encoding="utf-8")
            self._git(repo, "add", "README")
            self._git(repo, "commit", "-m", "seed without baseline")
            sha = self._git(repo, "rev-parse", "HEAD")

            report = repo / "report.json"
            branch_base = repo / "ci" / "pylint-baseline.json"
            branch_base.parent.mkdir(parents=True)
            report.write_text(json.dumps(msgs), encoding="utf-8")
            branch_base.write_text(
                json.dumps(counter_to_baseline(count_fingerprints(msgs))),
                encoding="utf-8",
            )

            real_git = vars(_gate)["_git"]

            def flaky_ls_tree(args, *, cwd=None):
                if args and args[0] == "ls-tree":
                    return subprocess.CompletedProcess(
                        args=["git", *args],
                        returncode=128,
                        stdout="",
                        stderr="fatal: simulated ls-tree failure\n",
                    )
                return real_git(args, cwd=cwd)

            with mock.patch("pylint_regression_gate._git", side_effect=flaky_ls_tree):
                with self.assertRaises(BaselineResolveError) as ctx:
                    resolve_baseline_bytes(
                        base_ref=sha,
                        branch_baseline=branch_base,
                        git_cwd=repo,
                    )
                self.assertIn("ls-tree", str(ctx.exception))
                rc = main(
                    [
                        "ci",
                        "--report",
                        str(report),
                        "--pylint-status",
                        "0",
                        "--branch-baseline",
                        str(branch_base),
                        "--base-ref",
                        sha,
                        "--git-cwd",
                        str(repo),
                    ]
                )
                self.assertEqual(rc, 1)

    def test_present_baseline_show_failure_fail_closed(self):
        """ls-tree says present but git show fails → fail closed, no bootstrap."""
        msgs = [_msg("a.py", "unused-import", "W0611", "Unused import x")]
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            self._init_repo(repo)
            base_path = repo / "ci" / "pylint-baseline.json"
            base_path.parent.mkdir(parents=True)
            base_path.write_text(
                json.dumps(counter_to_baseline(count_fingerprints(msgs))),
                encoding="utf-8",
            )
            self._git(repo, "add", "ci/pylint-baseline.json")
            self._git(repo, "commit", "-m", "baseline present")
            sha = self._git(repo, "rev-parse", "HEAD")

            report = repo / "report.json"
            report.write_text(json.dumps(msgs), encoding="utf-8")
            # Branch file still present on disk (would tempt a mistaken bootstrap).
            self.assertTrue(base_path.is_file())

            real_git = vars(_gate)["_git"]

            def show_fails(args, *, cwd=None):
                if args and args[0] == "show":
                    return subprocess.CompletedProcess(
                        args=["git", *args],
                        returncode=128,
                        stdout="",
                        stderr="fatal: simulated git show failure\n",
                    )
                return real_git(args, cwd=cwd)

            with mock.patch("pylint_regression_gate._git", side_effect=show_fails):
                with self.assertRaises(BaselineResolveError) as ctx:
                    resolve_baseline_bytes(
                        base_ref=sha,
                        branch_baseline=base_path,
                        git_cwd=repo,
                    )
                self.assertIn("git show failed", str(ctx.exception))
                rc = main(
                    [
                        "ci",
                        "--report",
                        str(report),
                        "--pylint-status",
                        "0",
                        "--branch-baseline",
                        str(base_path),
                        "--base-ref",
                        sha,
                        "--git-cwd",
                        str(repo),
                    ]
                )
                self.assertEqual(rc, 1)

    def test_direct_main_push_cannot_self_bless(self):
        """Push-to-main vs event.before: raised baseline + matching report FAIL."""
        clean = [_msg("a.py", "unused-import", "W0611", "Unused import x")]
        blessed = clean + [
            _msg("b.py", "unused-variable", "W0612", "Unused variable hide")
        ]
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            self._init_repo(repo)

            base_path = repo / "ci" / "pylint-baseline.json"
            base_path.parent.mkdir(parents=True)
            base_path.write_text(
                json.dumps(counter_to_baseline(count_fingerprints(clean))),
                encoding="utf-8",
            )
            self._git(repo, "add", "ci/pylint-baseline.json")
            self._git(repo, "commit", "-m", "baseline on main")
            before = self._git(repo, "rev-parse", "HEAD")

            # Simulate a direct push that raises the baseline and invents
            # matching lint debt (as if event.before = prior main tip).
            base_path.write_text(
                json.dumps(counter_to_baseline(count_fingerprints(blessed))),
                encoding="utf-8",
            )
            report = repo / "report.json"
            report.write_text(json.dumps(blessed), encoding="utf-8")

            rc = main(
                [
                    "ci",
                    "--report",
                    str(report),
                    "--pylint-status",
                    "0",
                    "--branch-baseline",
                    str(base_path),
                    "--base-ref",
                    before,
                    "--git-cwd",
                    str(repo),
                ]
            )
            self.assertEqual(rc, 1)




class TestNormalizeMessage(unittest.TestCase):
    def test_normalize_line_count_and_outer_scope_only(self):
        # C0302 module line-count churn is noise.
        self.assertEqual(
            normalize_message(
                "Too many lines in module (1436/1000)",
                symbol="too-many-lines",
                msg_id="C0302",
            ),
            "Too many lines in module (#/#)",
        )
        self.assertEqual(
            normalize_message(
                "Too many lines in module (1418/1000)",
                symbol="too-many-lines",
                msg_id="C0302",
            ),
            "Too many lines in module (#/#)",
        )
        # Outer-scope absolute lines shift on unrelated edits.
        self.assertEqual(
            normalize_message(
                "Redefining name 'stats' from outer scope (line 306)"
            ),
            "Redefining name 'stats' from outer scope (line #)",
        )
        # Complexity magnitude must remain detectable (ChatGPT policy).
        self.assertEqual(
            normalize_message(
                "Too many arguments (10/8)",
                symbol="too-many-arguments",
                msg_id="R0913",
            ),
            "Too many arguments (10/8)",
        )
        self.assertNotEqual(
            normalize_message(
                "Too many arguments (10/8)",
                symbol="too-many-arguments",
                msg_id="R0913",
            ),
            normalize_message(
                "Too many arguments (20/8)",
                symbol="too-many-arguments",
                msg_id="R0913",
            ),
        )

if __name__ == "__main__":
    unittest.main()
