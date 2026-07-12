"""Hermetic tests for restic integrity preflight helpers."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent


def _load_mod():
    path = REPO / "scripts" / "restic_integrity_check.py"
    spec = importlib.util.spec_from_file_location("restic_integrity_check", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["restic_integrity_check"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load_mod()


class TestBuildArgv(unittest.TestCase):
    def test_default_subset(self) -> None:
        argv = mod.build_check_argv()
        self.assertEqual(
            argv,
            ["restic", "check", "--tag", "convmem-chroma", "--read-data-subset", "5%"],
        )

    def test_full_read_data(self) -> None:
        argv = mod.build_check_argv(full_read_data=True, subset=None)
        self.assertEqual(argv, ["restic", "check", "--tag", "convmem-chroma", "--read-data"])


class TestClassify(unittest.TestCase):
    def test_ok(self) -> None:
        proc = subprocess.CompletedProcess(["restic"], 0, "", "")
        mod.classify_check_result(proc)

    def test_lock_exit_11(self) -> None:
        proc = subprocess.CompletedProcess(["restic"], 11, "", "already locked")
        with self.assertRaises(mod.CheckError) as ctx:
            mod.classify_check_result(proc)
        self.assertEqual(ctx.exception.code, "restic_lock")
        self.assertEqual(ctx.exception.exit_code, 11)

    def test_missing_repo_exit_10(self) -> None:
        proc = subprocess.CompletedProcess(["restic"], 10, "", "does not exist")
        with self.assertRaises(mod.CheckError) as ctx:
            mod.classify_check_result(proc)
        self.assertEqual(ctx.exception.code, "restic_missing_repo")


class TestReport(unittest.TestCase):
    def test_report_written_and_finalized(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reports" / "integrity-test.json"
            report = mod.Report(path)
            report.step("build_argv", "PASS", "restic check")
            report.finalize("PASS", "ok")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["status"], "PASS")
            self.assertEqual(data["steps"][0]["name"], "build_argv")
            self.assertTrue(path.with_suffix(".md").is_file())


class TestMainMocked(unittest.TestCase):
    def test_happy_path_mocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            env_file = parent / "restic.env"
            env_file.write_text(
                "RESTIC_REPOSITORY=/tmp/fake-repo\nRESTIC_PASSWORD_FILE=/tmp/fake-pass\n",
                encoding="utf-8",
            )
            (parent / "fake-pass").write_text("x\n", encoding="utf-8")
            # point password file to existing path
            env_file.write_text(
                f"RESTIC_REPOSITORY=/tmp/fake-repo\nRESTIC_PASSWORD_FILE={parent / 'fake-pass'}\n",
                encoding="utf-8",
            )
            ok = subprocess.CompletedProcess(
                ["restic", "check"], 0, "ok\n", ""
            )
            with mock.patch.object(mod, "run_restic_check", return_value=ok):
                code = mod.main(
                    ["--parent", str(parent), "--env-file", str(env_file)]
                )
            self.assertEqual(code, 0)
            reports = list((parent / "reports").glob("integrity-*.json"))
            self.assertEqual(len(reports), 1)
            meta = json.loads(reports[0].read_text(encoding="utf-8"))["meta"]
            self.assertEqual(meta["status"], "PASS")
            self.assertIn("--read-data-subset", meta["argv"])
            self.assertIn("5%", meta["argv"])

    def test_intentional_missing_repo_mocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            pass_file = parent / "pass"
            pass_file.write_text("x\n", encoding="utf-8")
            env_file = parent / "restic.env"
            env_file.write_text(
                f"RESTIC_REPOSITORY=/tmp/real-looking\nRESTIC_PASSWORD_FILE={pass_file}\n",
                encoding="utf-8",
            )
            bad = subprocess.CompletedProcess(
                ["restic", "check"], 10, "", "repository does not exist"
            )
            with mock.patch.object(mod, "run_restic_check", return_value=bad):
                code = mod.main(
                    [
                        "--parent",
                        str(parent),
                        "--env-file",
                        str(env_file),
                        "--intentional-missing-repo",
                    ]
                )
            self.assertEqual(code, 10)
            reports = list((parent / "reports").glob("integrity-*.json"))
            self.assertEqual(len(reports), 1)
            data = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["status"], "FAIL")
            codes = [s.get("code") for s in data["steps"] if s["name"] == "restic_check"]
            self.assertEqual(codes, ["restic_missing_repo"])


if __name__ == "__main__":
    unittest.main()
