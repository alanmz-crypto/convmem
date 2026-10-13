# pylint: disable=protected-access
"""Launcher contract tests for Safe Harbor T3 CI integration (plumbing only)."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[1]
_WORKER_PATH = _REPO / "tests" / "_safe_harbor_t3_worker.py"
_BOOTSTRAP_PATH = _REPO / "tests" / "_safe_harbor_bootstrap.py"
_BACKEND_PATH = _REPO / "tests" / "_safe_harbor_t3_backend_worker.py"
_CHECKER = _REPO / "scripts" / "check_ci_critical_invariants.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_worker():
    return _load_module(_WORKER_PATH, "safe_harbor_t3_worker_ci")


def _load_bootstrap():
    return _load_module(_BOOTSTRAP_PATH, "safe_harbor_bootstrap_ci")


def _load_backend():
    return _load_module(_BACKEND_PATH, "safe_harbor_t3_backend_worker_ci")


def _ambient_canaries() -> dict[str, str]:
    return {
        "DEEPSEEK_API_KEY": "canary-deepseek",
        "OPENAI_API_KEY": "canary-openai",
        "PYTHONPATH": "/evil/ambient",
        "CONVMEM_CONFIG": "/evil/config.toml",
        "TMPDIR": "/evil/tmp",
    }


def _patch_os_uid(case: unittest.TestCase, uid: int) -> None:
    if uid == os.getuid():
        return
    for patcher in (
        mock.patch.object(os, "getuid", return_value=uid),
        mock.patch.object(os, "geteuid", return_value=uid),
    ):
        case.addCleanup(patcher.stop)
        patcher.start()


def _real_builder_env(
    case: unittest.TestCase,
    tmp_path: Path,
    *,
    expected_uid: int,
) -> tuple[Path, Path, dict[str, str]]:
    backend = _load_backend()
    fixture = tmp_path / "fixture"
    evidence = tmp_path / "evidence"
    _patch_os_uid(case, expected_uid)
    merged = {**os.environ, **_ambient_canaries()}
    env_patch = mock.patch.dict(os.environ, merged, clear=True)
    case.addCleanup(env_patch.stop)
    env_patch.start()
    env = backend.build_allowlisted_env(fixture, evidence, expected_uid=expected_uid)
    assert "DEEPSEEK_API_KEY" not in env
    assert "OPENAI_API_KEY" not in env
    assert env["PYTHONPATH"] == str(_REPO)
    assert env["CONVMEM_CONFIG"].startswith(str(fixture.resolve()))
    assert env["SAFE_HARBOR_T3_EXPECTED_UID"] == str(expected_uid)
    assert env["TMPDIR"].startswith(str(fixture.resolve()))
    bin_dir = str(Path(sys.executable).absolute().parent)
    assert env["PATH"].startswith(f"{bin_dir}:")
    return fixture, evidence, env


class SafeHarborT3CiLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worker = _load_worker()
        self.bootstrap = _load_bootstrap()
        self.backend = _load_backend()

    def _start_cooperative_parent(self, tmp_path: Path, *, uid: int | None = None) -> None:
        bound = uid if uid is not None else os.getuid()
        patchers = [
            mock.patch.object(self.worker, "_load_bootstrap_module", return_value=self.bootstrap),
            mock.patch.object(self.backend, "_load_bootstrap_module", return_value=self.bootstrap),
            mock.patch.object(self.worker, "_temp_parent_dir", side_effect=lambda _backend: str(tmp_path)),
            mock.patch.object(self.bootstrap, "require_parent_bootstrap_flags"),
        ]
        for patcher in patchers:
            self.addCleanup(patcher.stop)
            patcher.start()
        _patch_os_uid(self, bound)

    def test_run_ci_builds_unfiltered_full_suite_child(self) -> None:
        calls: list[list[str]] = []
        run_kwargs: dict[str, object] = {}

        def fake_run(cmd, **_kwargs):  # type: ignore[no-untyped-def]
            calls.append(list(cmd))
            run_kwargs.update(_kwargs)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._start_cooperative_parent(tmp, uid=1500)
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(self.bootstrap.subprocess, "run", side_effect=fake_run):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        rc = self.worker.run_ci()
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 1)
        child_env = run_kwargs["env"]
        assert isinstance(child_env, dict)
        fixture_root = Path(child_env["SAFE_HARBOR_T3_FIXTURE_ROOT"])
        # pylint: disable=duplicate-code
        expected_cmd = [
            sys.executable,
            "-s",
            "-B",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={fixture_root / 'pytest-tmp' / 'full-suite'}",
        ]
        # pylint: enable=duplicate-code
        self.assertEqual(calls[0], expected_cmd)
        self.assertEqual(run_kwargs["cwd"], _REPO)
        self.assertIs(run_kwargs["capture_output"], True)
        self.assertIs(run_kwargs["text"], True)
        self.assertIs(run_kwargs["check"], False)
        self.assertEqual(run_kwargs["timeout"], self.worker.FULL_SUITE_TIMEOUT_SECONDS)
        self.assertEqual(child_env["SAFE_HARBOR_T3_EXPECTED_UID"], "1500")
        self.assertNotIn("DEEPSEEK_API_KEY", child_env)

    def test_run_ci_propagates_nonzero_child(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td))
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(
                    self.bootstrap.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 7, "", "fail"),
                ):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        rc = self.worker.run_ci()
        self.assertEqual(rc, 7)

    def test_run_ci_refuses_timeout(self) -> None:
        def raise_timeout(*_a, **_k):  # type: ignore[no-untyped-def]
            raise subprocess.TimeoutExpired(cmd=["pytest"], timeout=1, output="timed")

        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td))
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(self.bootstrap.subprocess, "run", side_effect=raise_timeout):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        self.assertEqual(self.worker.run_ci(), 124)

    def test_run_ci_refuses_none_returncode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td))
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(
                    self.bootstrap.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], None, "", ""),
                ):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        self.assertEqual(self.worker.run_ci(), 124)

    def test_run_ci_refuses_source_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td))
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(
                    self.bootstrap.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0, "", ""),
                ):
                    with mock.patch.object(self.worker, "_source_hashes", side_effect=[{"a": "1"}, {"a": "2"}]):
                        self.assertEqual(self.worker.run_ci(), 1)

    def test_run_ci_collect_delegates_to_checker_unchanged_argv(self) -> None:
        recorded: list[list[str]] = []
        run_kwargs: dict[str, object] = {}

        def fake_run(cmd, **_kwargs):  # type: ignore[no-untyped-def]
            recorded.append(list(cmd))
            run_kwargs.update(_kwargs)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td), uid=1500)
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(self.bootstrap.subprocess, "run", side_effect=fake_run):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        rc = self.worker.run_ci_collect()
        self.assertEqual(rc, 0)
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0], [sys.executable, "-s", "-B", str(_CHECKER)])
        self.assertEqual(run_kwargs["cwd"], _REPO)
        self.assertIs(run_kwargs["capture_output"], True)
        self.assertIs(run_kwargs["text"], True)
        self.assertIs(run_kwargs["check"], False)
        self.assertEqual(run_kwargs["timeout"], self.worker.CHECKER_TIMEOUT_SECONDS)

    def test_run_ci_collect_propagates_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td))
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(
                    self.bootstrap.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 3, "", ""),
                ):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        self.assertEqual(self.worker.run_ci_collect(), 3)

    def test_run_ci_collect_refuses_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td))
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(self.worker, "_source_hashes", side_effect=[{"a": "1"}, {"a": "2"}]):
                    with mock.patch.object(
                        self.bootstrap.subprocess,
                        "run",
                        return_value=subprocess.CompletedProcess([], 0, "", ""),
                    ):
                        self.assertEqual(self.worker.run_ci_collect(), 1)

    def test_run_ci_collect_refuses_timeout(self) -> None:
        def raise_timeout(*_a, **_k):  # type: ignore[no-untyped-def]
            raise subprocess.TimeoutExpired(cmd=["checker"], timeout=1, output="x")

        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td))
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(self.bootstrap.subprocess, "run", side_effect=raise_timeout):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        self.assertEqual(self.worker.run_ci_collect(), 124)

    def test_run_ci_collect_refuses_none_returncode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td))
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(
                    self.bootstrap.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], None, "", ""),
                ):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        self.assertEqual(self.worker.run_ci_collect(), 124)

    def test_parent_refuses_without_bootstrap_flags(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            patcher = mock.patch.object(self.worker, "_temp_parent_dir", side_effect=lambda _b: str(tmp))
            self.addCleanup(patcher.stop)
            patcher.start()
            with mock.patch.object(self.worker, "_load_bootstrap_module", return_value=self.bootstrap):
                with mock.patch.object(
                    self.bootstrap,
                    "require_parent_bootstrap_flags",
                    side_effect=RuntimeError("bootstrap requires python -I -S -B"),
                ):
                    with self.assertRaises(RuntimeError):
                        self.worker._parent_uid_and_env(self.backend)

    def test_bootstrap_uid_controls(self) -> None:
        env_patch = mock.patch.dict(os.environ, {}, clear=False)
        self.addCleanup(env_patch.stop)
        env_patch.start()
        os.environ.pop("SAFE_HARBOR_T3_EXPECTED_UID", None)
        with self.assertRaises(RuntimeError):
            self.bootstrap.require_expected_uid_match()
        uid_patch = mock.patch.dict(os.environ, {"SAFE_HARBOR_T3_EXPECTED_UID": "1500"}, clear=False)
        self.addCleanup(uid_patch.stop)
        uid_patch.start()
        with mock.patch.object(self.bootstrap.os, "getuid", return_value=1500):
            with mock.patch.object(self.bootstrap.os, "geteuid", return_value=1501):
                with self.assertRaises(RuntimeError):
                    self.bootstrap.require_expected_uid_match()
        with mock.patch.object(self.bootstrap.os, "getuid", return_value=0):
            with mock.patch.object(self.bootstrap.os, "geteuid", return_value=0):
                with self.assertRaises(RuntimeError):
                    self.bootstrap.refuse_root()
        with mock.patch.object(self.bootstrap.os, "getuid", return_value=1500):
            with mock.patch.object(self.bootstrap.os, "geteuid", return_value=1500):
                self.assertEqual(self.bootstrap.require_explicit_uid_binding(1500), 1500)

    def test_builder_drops_ambient_before_child(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            _real_builder_env(self, Path(td), expected_uid=1500)

    def test_builder_without_expected_uid_refuses_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            env_patch = mock.patch.dict(os.environ, {}, clear=False)
            self.addCleanup(env_patch.stop)
            env_patch.start()
            os.environ.pop("SAFE_HARBOR_T3_EXPECTED_UID", None)
            with self.assertRaises(RuntimeError):
                self.backend.build_allowlisted_env(fixture, evidence)
            self.assertFalse(fixture.exists())
            self.assertFalse(evidence.exists())

    def test_subprocess_bootstrap_entry_refuses_missing_uid(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(_BOOTSTRAP_PATH)],
            cwd=_REPO,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp")},
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("SAFE_HARBOR_T3_EXPECTED_UID", proc.stderr)

    def test_main_dispatches_ci_modes_without_running_full_suite(self) -> None:
        with mock.patch.object(self.worker, "run_ci", return_value=0) as run_ci:
            with mock.patch.object(sys, "argv", [str(_WORKER_PATH), "run-ci"]):
                self.assertEqual(self.worker.main(), 0)
            run_ci.assert_called_once()
        with mock.patch.object(self.worker, "run_ci_collect", return_value=0) as collect:
            with mock.patch.object(sys, "argv", [str(_WORKER_PATH), "run-ci-collect"]):
                self.assertEqual(self.worker.main(), 0)
            collect.assert_called_once()

    def test_no_arbitrary_command_mode_in_main(self) -> None:
        with mock.patch.object(sys, "argv", [str(_WORKER_PATH), "run-shell"]):
            self.assertEqual(self.worker.main(), 2)

    def test_finalize_summary_refuses_missing_lint_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td)
            rc = self.worker._finalize_summary(
                evidence,
                mode="lint-missing",
                parent_uid=os.getuid(),
                fixture_root=evidence / "fixture",
                source_hashes_before=self.worker._source_hashes(),
                runs=[],
                lint={},
            )
            self.assertEqual(rc, 124)


if __name__ == "__main__":
    unittest.main()
