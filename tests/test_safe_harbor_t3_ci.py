# pylint: disable=protected-access
"""Launcher contract tests for Safe Harbor T3 CI integration (plumbing only)."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[1]
_WORKER_PATH = _REPO / "tests" / "_safe_harbor_t3_worker.py"
_BOOTSTRAP_PATH = _REPO / "tests" / "_safe_harbor_bootstrap.py"
_BACKEND_PATH = _REPO / "tests" / "_safe_harbor_t3_backend_worker.py"
_CHECKER = _REPO / "scripts" / "check_ci_critical_invariants.py"
_INERT_HTTP_ENDPOINT = "http://127.0.0.1:9"


def _isolated_node_path(tmp: Path) -> str:
    node_dir = tmp / "node-bin"
    node_dir.mkdir(parents=True, exist_ok=True)
    node = node_dir / "node"
    node.write_text("#!/bin/sh\n", encoding="utf-8")
    node.chmod(0o755)
    return str(node.resolve())


def _assert_parsed_full_ci_config(
    config_path: Path,
    fixture_root: Path,
    fixture_meta: dict[str, str],
) -> None:
    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    root = fixture_root.resolve()
    assert parsed["sources"]["paths"] == []
    assert parsed["refine"]["enabled"] is False
    assert parsed["refine"]["jobs"] == []
    assert parsed["models"]["ollama_host"] == _INERT_HTTP_ENDPOINT
    assert parsed["models"]["deepseek_base_url"] == _INERT_HTTP_ENDPOINT
    path_values = [
        parsed["sources"]["inventory"],
        parsed["index"]["chroma_dir"],
        parsed["index"]["processed_log"],
        parsed["index"]["units_export"],
        parsed["index"]["incremental_jsonl"]["state_dir"],
        parsed["shadow_ledger"]["ledger_path"],
        parsed["shadow_ledger"]["activation_manifest_path"],
        parsed["shadow_ledger"]["health_path"],
    ]
    for raw in path_values:
        resolved = Path(str(raw)).expanduser().resolve()
        if resolved != root and root not in resolved.parents:
            raise AssertionError(f"path escapes fixture root: {resolved}")
    node_executable = fixture_meta.get("node_executable")
    node_bridge = fixture_meta.get("node_bridge")
    node_sha = fixture_meta.get("node_executable_sha256")
    assert node_executable and node_bridge and node_sha
    selected = Path(node_executable).resolve()
    bridge = Path(node_bridge)
    assert bridge.is_symlink()
    assert bridge.resolve() == selected
    assert node_sha == hashlib.sha256(selected.read_bytes()).hexdigest()


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


def _patch_full_ci_restic(case, backend, tmp_path: Path) -> Path:
    restic = tmp_path / "restic-bin" / "restic"
    restic.parent.mkdir(parents=True, exist_ok=True)
    restic.write_text("#!/bin/sh\necho 'restic 0.19.0'\n", encoding="utf-8")
    restic.chmod(0o755)
    resolved = restic.resolve()
    from tests import _safe_harbor_restic_ci as restic_helper

    loader_patch = mock.patch.object(backend, "_load_restic_ci", return_value=restic_helper)
    case.addCleanup(loader_patch.stop)
    loader_patch.start()
    verify_patcher = mock.patch(
        "tests._safe_harbor_restic_ci.verify_restic_binary",
        return_value=None,
    )
    case.addCleanup(verify_patcher.stop)
    verify_patcher.start()
    env_patcher = mock.patch.dict(
        os.environ,
        {"SAFE_HARBOR_CI_RESTIC_EXECUTABLE": str(resolved)},
        clear=False,
    )
    case.addCleanup(env_patcher.stop)
    env_patcher.start()
    resolve_patch = mock.patch.object(restic_helper, "resolve_ci_restic_executable", return_value=resolved)
    case.addCleanup(resolve_patch.stop)
    resolve_patch.start()
    return resolved


class SafeHarborT3CiLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worker = _load_worker()
        self.bootstrap = _load_bootstrap()
        self.backend = _load_backend()

    def _start_cooperative_parent(
        self,
        tmp_path: Path,
        *,
        uid: int | None = None,
        full_ci: bool = False,
    ) -> None:
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
        if full_ci:
            self._patch_full_ci_node(tmp_path)
            _patch_full_ci_restic(self, self.backend, tmp_path)

    def _patch_full_ci_node(self, tmp_path: Path) -> Path:
        """Non-/usr/bin node identity for full_ci profile (no ambient PATH inheritance)."""
        node_dir = tmp_path / "isolated-node-bin"
        node_dir.mkdir(parents=True, exist_ok=True)
        node = node_dir / "node"
        node.write_text("#!/bin/sh\n", encoding="utf-8")
        node.chmod(0o755)
        resolved = node.resolve()
        patcher = mock.patch.object(self.backend, "_select_node_executable", return_value=resolved)
        self.addCleanup(patcher.stop)
        patcher.start()
        return resolved

    def test_run_ci_builds_unfiltered_full_suite_child(self) -> None:
        calls: list[list[str]] = []
        run_kwargs: dict[str, object] = {}

        def fake_run(cmd, **_kwargs):  # type: ignore[no-untyped-def]
            calls.append(list(cmd))
            run_kwargs.update(_kwargs)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._start_cooperative_parent(tmp, uid=1500, full_ci=True)
            with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
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
                "-ra",
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
            self.assertEqual(child_env.get("GITHUB_ACTIONS"), "true")
            config_path = Path(child_env["CONVMEM_CONFIG"])
            bridge = fixture_root / "toolbin" / "node"
            selected = bridge.resolve()
            _assert_parsed_full_ci_config(
                config_path,
                fixture_root,
                {
                    "node_executable": str(selected),
                    "node_bridge": str(bridge),
                    "node_executable_sha256": hashlib.sha256(selected.read_bytes()).hexdigest(),
                },
            )
            path_entries = child_env["PATH"].split(":")
            self.assertEqual(path_entries[0], str(fixture_root / "toolbin"))
            self.assertEqual(
                shutil.which("node", path=child_env["PATH"]),
                str(fixture_root / "toolbin" / "node"),
            )
            restic_bridge = fixture_root / "toolbin" / "restic"
            self.assertTrue(restic_bridge.is_symlink())
            self.assertEqual(
                shutil.which("restic", path=child_env["PATH"]),
                str(restic_bridge),
            )
            tldr = Path(child_env["CONVMEM_ROOT"]) / "docs" / "CONVMEM-TLDR.md"
            self.assertTrue(tldr.is_file())
            self.assertIn("convmem doctor", tldr.read_text(encoding="utf-8"))
            self.assertEqual(
                tldr.read_text(encoding="utf-8"),
                (_REPO / "docs" / "CONVMEM-TLDR.md").read_text(encoding="utf-8"),
            )

    def test_run_ci_propagates_nonzero_child(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td), full_ci=True)
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
            self._start_cooperative_parent(Path(td), full_ci=True)
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(self.bootstrap.subprocess, "run", side_effect=raise_timeout):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        self.assertEqual(self.worker.run_ci(), 124)

    def test_run_ci_refuses_none_returncode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td), full_ci=True)
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
            self._start_cooperative_parent(Path(td), full_ci=True)
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
            self._start_cooperative_parent(Path(td), uid=1500, full_ci=True)
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
            self._start_cooperative_parent(Path(td), full_ci=True)
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
            self._start_cooperative_parent(Path(td), full_ci=True)
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
            self._start_cooperative_parent(Path(td), full_ci=True)
            with mock.patch.object(self.worker, "_load_backend_worker_module", return_value=self.backend):
                with mock.patch.object(self.bootstrap.subprocess, "run", side_effect=raise_timeout):
                    with mock.patch.object(self.worker, "_source_hashes", return_value={"a": "b"}):
                        self.assertEqual(self.worker.run_ci_collect(), 124)

    def test_run_ci_collect_refuses_none_returncode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self._start_cooperative_parent(Path(td), full_ci=True)
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

    def test_builder_refuses_credentials_even_when_github_actions_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            _patch_os_uid(self, 1500)
            merged = {**os.environ, **_ambient_canaries(), "GITHUB_ACTIONS": "true"}
            env_patch = mock.patch.dict(os.environ, merged, clear=True)
            self.addCleanup(env_patch.stop)
            env_patch.start()
            env = self.backend.build_allowlisted_env(fixture, evidence, expected_uid=1500)
            self.assertNotIn("DEEPSEEK_API_KEY", env)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("GITHUB_ACTIONS", env)

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


class SafeHarborT3CiFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = _load_backend()
        # TestCase closes this context after the test through its cleanup stack.
        fixture = self.enterContext(
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )
        # These existing tests isolate node/config/uid plumbing; the separate
        # Restic contract tests exercise the real verifier and missing-tool stop.
        _patch_full_ci_restic(self, self.backend, Path(fixture))

    def test_full_ci_profile_refuses_without_node(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            _patch_os_uid(self, 1500)
            with mock.patch("shutil.which", return_value=None):
                with self.assertRaises(RuntimeError):
                    self.backend.build_allowlisted_env(
                        fixture,
                        evidence,
                        expected_uid=1500,
                        profile="full_ci",
                    )

    def test_full_ci_node_bridge_is_outside_usr_bin(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            _patch_os_uid(self, 1500)
            node_dir = tmp / "isolated-node-bin"
            node_dir.mkdir(parents=True, exist_ok=True)
            node = node_dir / "node"
            node.write_text("#!/bin/sh\n", encoding="utf-8")
            node.chmod(0o755)
            resolved = node.resolve()
            self.assertNotEqual(resolved.parts[1:3], ("usr", "bin"))
            meta: dict[str, str] = {}
            with (
                mock.patch("shutil.which", return_value=str(resolved)),
                mock.patch.dict(os.environ, {"PATH": "/safe-harbor-path-canary"}),
            ):
                env = self.backend.build_allowlisted_env(
                    fixture,
                    evidence,
                    expected_uid=1500,
                    profile="full_ci",
                    fixture_meta=meta,
                )
            bridge = fixture / "toolbin" / "node"
            self.assertTrue(bridge.is_symlink())
            self.assertEqual(bridge.resolve(), resolved)
            self.assertEqual(meta.get("node_executable"), str(resolved))
            self.assertEqual(
                meta.get("node_executable_sha256"),
                hashlib.sha256(resolved.read_bytes()).hexdigest(),
            )
            path_entries = env["PATH"].split(":")
            self.assertEqual(path_entries[0], str(fixture / "toolbin"))
            self.assertEqual(shutil.which("node", path=env["PATH"]), str(bridge))
            self.assertEqual(
                path_entries,
                [str(fixture / "toolbin"), str(Path(sys.executable).absolute().parent),
                 "/usr/bin", "/bin"],
            )
            self.assertNotIn("/safe-harbor-path-canary", path_entries)
            _assert_parsed_full_ci_config(Path(env["CONVMEM_CONFIG"]), fixture, meta)

    def test_full_ci_github_actions_only_when_parent_literal_true(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _patch_os_uid(self, 1500)
            node_dir = tmp / "node-bin"
            node_dir.mkdir()
            node = node_dir / "node"
            node.write_text("#!/bin/sh\n", encoding="utf-8")
            node.chmod(0o755)
            cases = (
                ({}, None),
                ({"GITHUB_ACTIONS": "false"}, None),
                ({"GITHUB_ACTIONS": "true"}, "true"),
            )
            for idx, (parent_env, expected) in enumerate(cases):
                case_fixture = tmp / f"fixture-{idx}"
                case_evidence = tmp / f"evidence-{idx}"
                with mock.patch.dict(os.environ, parent_env, clear=True):
                    with mock.patch("shutil.which", return_value=str(node.resolve())):
                        env = self.backend.build_allowlisted_env(
                            case_fixture,
                            case_evidence,
                            expected_uid=1500,
                            profile="full_ci",
                        )
                self.assertEqual(env.get("GITHUB_ACTIONS"), expected)

    def test_full_ci_refuses_unknown_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _patch_os_uid(self, 1500)
            with self.assertRaises(RuntimeError):
                self.backend.build_allowlisted_env(
                    tmp / "fixture",
                    tmp / "evidence",
                    expected_uid=1500,
                    profile="scratch",
                )

    def test_staging_refuses_symlink_convmem_root_parent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            escape = tmp / "escape-root"
            docs_dir = escape / "docs"
            docs_dir.mkdir(parents=True)
            sentinel = docs_dir / "CONVMEM-TLDR.md"
            sentinel.write_text("SENTINEL_UNCHANGED", encoding="utf-8")
            fixture = tmp / "fixture"
            fixture.mkdir()
            (fixture / "convmem-root").symlink_to(escape)
            with self.assertRaises(RuntimeError):
                self.backend._stage_convmem_readonly_docs(fixture)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "SENTINEL_UNCHANGED")
            self.assertEqual(list(docs_dir.iterdir()), [sentinel])

    def test_full_ci_config_leaf_symlink_refuses_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            fixture.mkdir()
            config_dir = fixture / "config"
            config_dir.mkdir()
            outside = tmp / "outside-config.toml"
            outside.write_bytes(b"OUTSIDE_BYTES")
            (config_dir / "config.toml").symlink_to(outside)
            with self.assertRaises(RuntimeError):
                self.backend._write_full_ci_fixture_config(fixture)
            self.assertEqual(outside.read_bytes(), b"OUTSIDE_BYTES")

    def test_require_isolated_refuses_inherited_credential_with_github_actions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            _patch_os_uid(self, 1500)
            with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
                with mock.patch("shutil.which", return_value=_isolated_node_path(tmp)):
                    env = self.backend.build_allowlisted_env(
                        fixture,
                        evidence,
                        expected_uid=1500,
                        profile="full_ci",
                    )
            polluted = {**env, "DEEPSEEK_API_KEY": "leak"}
            with mock.patch.dict(os.environ, polluted, clear=True):
                with mock.patch.object(self.backend.os, "getuid", return_value=1500):
                    with mock.patch.object(self.backend.os, "geteuid", return_value=1500):
                        with self.assertRaises(RuntimeError):
                            self.backend._require_isolated()

    def test_require_isolated_refuses_escaped_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            outside = tmp / "outside.toml"
            outside.write_text("[index]\n", encoding="utf-8")
            _patch_os_uid(self, 1500)
            with mock.patch("shutil.which", return_value=_isolated_node_path(tmp)):
                env = self.backend.build_allowlisted_env(
                    fixture,
                    evidence,
                    expected_uid=1500,
                    profile="full_ci",
                )
            escaped = {**env, "CONVMEM_CONFIG": str(outside)}
            with mock.patch.dict(os.environ, escaped, clear=True):
                with mock.patch.object(self.backend.os, "getuid", return_value=1500):
                    with mock.patch.object(self.backend.os, "geteuid", return_value=1500):
                        with self.assertRaises(RuntimeError):
                            self.backend._require_isolated()

    def test_require_isolated_refuses_mismatched_uid_with_github_actions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fixture = tmp / "fixture"
            evidence = tmp / "evidence"
            _patch_os_uid(self, 1500)
            with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
                with mock.patch("shutil.which", return_value=_isolated_node_path(tmp)):
                    env = self.backend.build_allowlisted_env(
                        fixture,
                        evidence,
                        expected_uid=1500,
                        profile="full_ci",
                    )
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch.object(self.backend.os, "getuid", return_value=1501):
                    with mock.patch.object(self.backend.os, "geteuid", return_value=1501):
                        with self.assertRaises(RuntimeError):
                            self.backend._require_isolated()


if __name__ == "__main__":
    unittest.main()
