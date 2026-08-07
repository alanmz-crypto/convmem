"""Hermetic tests for restic integrity preflight helpers (workflow-backed)."""

from __future__ import annotations

import importlib.util
import json
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
        sid = "a" * 64
        argv = mod.build_check_argv(snapshot_id=sid)
        self.assertEqual(
            argv,
            ["restic", "check", sid, "--read-data-subset", "5%"],
        )
        self.assertNotIn("--tag", argv)
        self.assertNotIn("--latest", argv)

    def test_full_read_data(self) -> None:
        sid = "b" * 64
        argv = mod.build_check_argv(snapshot_id=sid, full_read_data=True, subset=None)
        self.assertEqual(argv, ["restic", "check", sid, "--read-data"])


class TestClassify(unittest.TestCase):
    def test_ok(self) -> None:
        mod.classify_check_result(0)

    def test_lock_exit_11(self) -> None:
        with self.assertRaises(mod.CheckError) as ctx:
            mod.classify_check_result(11, "already locked")
        self.assertEqual(ctx.exception.code, "restic_lock")
        self.assertEqual(ctx.exception.exit_code, 11)

    def test_missing_repo_exit_10(self) -> None:
        with self.assertRaises(mod.CheckError) as ctx:
            mod.classify_check_result(10, "does not exist")
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
        from backup_workflows import WorkflowOutcome
        from restic_snapshot import SnapshotRef
        from datetime import datetime, timezone

        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            data_root = parent / "data"
            data_root.mkdir()
            chroma = data_root / "chroma"
            chroma.mkdir()
            pass_file = parent / "pass"
            pass_file.write_text("x\n", encoding="utf-8")
            repo = parent / "repo"
            repo.mkdir()
            env_file = parent / "restic.env"
            env_file.write_text(
                "CONVMEM_BACKUP_PROFILE=complete-data-v2\n"
                f"CONVMEM_DATA_ROOT={data_root}\n"
                f"RESTIC_REPOSITORY={repo}\n"
                f"RESTIC_PASSWORD_FILE={pass_file}\n"
                f"CONVMEM_CHROMA_DIR={chroma}\n"
                f"RESTIC_CACHE_DIR={parent / 'cache'}\n",
                encoding="utf-8",
            )
            (parent / "cache").mkdir()
            sid = "c" * 64
            source = SnapshotRef(
                repository=str(repo),
                id=sid,
                original=None,
                tree="t" * 64,
                time=datetime.now(timezone.utc),
                paths=(str(data_root.resolve()),),
                tags=frozenset({"convmem-data-v2"}),
            )
            outcome = WorkflowOutcome(
                status="PASS",
                message="ok",
                source=source,
                argv=("restic", "-r", str(repo), "check", sid, "--read-data-subset", "5%"),
                details={"restic_exit_code": 0},
            )
            with mock.patch.object(mod, "run_integrity_check", return_value=outcome):
                with mock.patch.object(mod, "BackupContext") as mock_ctx_cls:
                    mock_ctx = mock.Mock()
                    mock_ctx.local_repository.locator = str(repo)
                    mock_ctx.default_tag.return_value = "convmem-data-v2"
                    mock_ctx_cls.from_env_file.return_value = mock_ctx
                    code = mod.main(
                        ["--parent", str(parent), "--env-file", str(env_file)]
                    )
            self.assertEqual(code, 0)
            reports = list((parent / "reports").glob("integrity-*.json"))
            self.assertEqual(len(reports), 1)
            meta = json.loads(reports[0].read_text(encoding="utf-8"))["meta"]
            self.assertEqual(meta["status"], "PASS")
            self.assertIn(sid, meta["argv"])
            self.assertIn("--read-data-subset", meta["argv"])

    def test_resolver_failure_mocked(self) -> None:
        from backup_workflows import WorkflowOutcome

        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            data_root = parent / "data"
            data_root.mkdir()
            chroma = data_root / "chroma"
            chroma.mkdir()
            pass_file = parent / "pass"
            pass_file.write_text("x\n", encoding="utf-8")
            repo = parent / "repo"
            repo.mkdir()
            env_file = parent / "restic.env"
            env_file.write_text(
                "CONVMEM_BACKUP_PROFILE=complete-data-v2\n"
                f"CONVMEM_DATA_ROOT={data_root}\n"
                f"RESTIC_REPOSITORY={repo}\n"
                f"RESTIC_PASSWORD_FILE={pass_file}\n"
                f"CONVMEM_CHROMA_DIR={chroma}\n"
                f"RESTIC_CACHE_DIR={parent / 'cache'}\n",
                encoding="utf-8",
            )
            (parent / "cache").mkdir()
            outcome = WorkflowOutcome(
                status="FAIL",
                message="no snapshots",
                exit_code=23,
                details={},
            )
            with mock.patch.object(mod, "run_integrity_check", return_value=outcome):
                with mock.patch.object(mod, "BackupContext") as mock_ctx_cls:
                    mock_ctx = mock.Mock()
                    mock_ctx.local_repository.locator = str(repo)
                    mock_ctx.default_tag.return_value = "convmem-data-v2"
                    mock_ctx_cls.from_env_file.return_value = mock_ctx
                    code = mod.main(
                        ["--parent", str(parent), "--env-file", str(env_file)]
                    )
            self.assertEqual(code, 23)
            reports = list((parent / "reports").glob("integrity-*.json"))
            self.assertEqual(len(reports), 1)
            data = json.loads(reports[0].read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
