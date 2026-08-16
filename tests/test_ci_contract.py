"""CI workflow and critical-invariant checker contract tests."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

_REPO = Path(__file__).resolve().parents[1]
_WORKFLOW = _REPO / ".github/workflows/pylint.yml"
_CHECKER = _REPO / "scripts" / "check_ci_critical_invariants.py"

APPROVED_PYTEST_PIN = "pytest==9.1.1"
PYTEST_PIN_CANDIDATE_EVIDENCE = "2026-08-16T04:46:06Z"
PYTEST_PIN_EXECUTION_EVIDENCE = "2026-08-16T05:34:00Z"

VERSION_LOG_CMD = "python -m pytest --version"
FULL_SUITE_CMD = "python -m pytest -q"
CHECKER_INVOCATION = "python scripts/check_ci_critical_invariants.py"

_UNPINNED_PYTEST_RE = re.compile(r"pip\s+install\b.*\bpytest\b(?!\s*==)")


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_ci_critical_invariants", _CHECKER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_ci_critical_invariants"] = mod
    spec.loader.exec_module(mod)
    return mod


_checker = _load_checker()


def _executable_lines(run_block: str) -> list[str]:
    lines: list[str] = []
    for raw in run_block.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        line = stripped.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def _job_run_blocks(workflow_path: Path, job_name: str) -> list[str]:
    data = yaml.safe_load(workflow_path.read_text())
    job = data["jobs"][job_name]
    runs: list[str] = []
    for step in job.get("steps", []):
        run = step.get("run")
        if isinstance(run, str):
            runs.append(run)
    return runs


def _job_install_run(workflow_path: Path, job_name: str) -> str:
    for block in _job_run_blocks(workflow_path, job_name):
        if any("pip install" in line for line in _executable_lines(block)):
            return block
    raise AssertionError(f"no install run block in job {job_name}")


def _assert_install_pytest_pins(run_block: str, job_name: str) -> None:
    pip_lines = [line for line in _executable_lines(run_block) if "pip install" in line]
    pytest_lines = [line for line in pip_lines if re.search(r"\bpytest\b", line)]
    if not pytest_lines:
        raise AssertionError(f"{job_name}: no executable pytest pip install line")
    for line in pytest_lines:
        if APPROVED_PYTEST_PIN not in line:
            raise AssertionError(f"{job_name}: missing exact pin in executable line: {line}")
    unpinned = [line for line in pip_lines if _UNPINNED_PYTEST_RE.search(line)]
    if unpinned:
        raise AssertionError(f"{job_name}: unpinned pytest install: {unpinned}")


def _assert_executable_command(run_blocks: list[str], command: str) -> None:
    for block in run_blocks:
        if command in _executable_lines(block):
            return
    raise AssertionError(f"executable command missing: {command}")


def _assert_workflow_contract(workflow_path: Path) -> None:
    _assert_install_pytest_pins(_job_install_run(workflow_path, "pylint"), "pylint")
    _assert_install_pytest_pins(_job_install_run(workflow_path, "pytest"), "pytest")
    pylint_runs = _job_run_blocks(workflow_path, "pylint")
    pytest_runs = _job_run_blocks(workflow_path, "pytest")
    _assert_executable_command(pylint_runs, VERSION_LOG_CMD)
    _assert_executable_command(pytest_runs, VERSION_LOG_CMD)
    _assert_executable_command(pytest_runs, FULL_SUITE_CMD)
    _assert_executable_command(pytest_runs, CHECKER_INVOCATION)


def _load_workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _write_temp_workflow(data: dict) -> Path:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False)
    yaml.safe_dump(data, tmp)
    return Path(tmp.name)


def _mutate_pylint_install(data: dict, new_run: str) -> None:
    for step in data["jobs"]["pylint"]["steps"]:
        if isinstance(step.get("run"), str) and "pip install" in step["run"]:
            step["run"] = new_run
            return
    raise AssertionError("pylint install step not found")


def _mutate_pytest_step_run(data: dict, step_name: str, new_run: str) -> None:
    for step in data["jobs"]["pytest"]["steps"]:
        if step.get("name") == step_name:
            step["run"] = new_run
            return
    raise AssertionError(f"pytest step not found: {step_name}")


class WorkflowContractTests(unittest.TestCase):
    def test_workflow_contract_live_file(self):
        _assert_workflow_contract(_WORKFLOW)

    def test_pin_constants_document_execution_evidence(self):
        self.assertEqual(APPROVED_PYTEST_PIN, "pytest==9.1.1")
        self.assertTrue(PYTEST_PIN_EXECUTION_EVIDENCE.endswith("Z"))

    def test_contract_fails_without_pylint_pin_only(self):
        data = _load_workflow(_WORKFLOW)
        install = _job_install_run(_WORKFLOW, "pylint")
        _mutate_pylint_install(data, install.replace(APPROVED_PYTEST_PIN, "pytest"))
        tmp_path = _write_temp_workflow(data)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
            _assert_install_pytest_pins(_job_install_run(tmp_path, "pytest"), "pytest")
        finally:
            tmp_path.unlink()

    def test_contract_fails_without_pytest_job_pin(self):
        data = _load_workflow(_WORKFLOW)
        install = _job_install_run(_WORKFLOW, "pytest")
        for step in data["jobs"]["pytest"]["steps"]:
            if isinstance(step.get("run"), str) and "pip install" in step["run"]:
                step["run"] = install.replace(APPROVED_PYTEST_PIN, "pytest")
        tmp_path = _write_temp_workflow(data)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_when_full_suite_is_comment_only(self):
        data = _load_workflow(_WORKFLOW)
        _mutate_pytest_step_run(data, "Run pytest", "# " + FULL_SUITE_CMD)
        tmp_path = _write_temp_workflow(data)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_when_full_suite_is_echo_only(self):
        data = _load_workflow(_WORKFLOW)
        _mutate_pytest_step_run(data, "Run pytest", "echo " + FULL_SUITE_CMD)
        tmp_path = _write_temp_workflow(data)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_when_checker_is_comment_only(self):
        data = _load_workflow(_WORKFLOW)
        _mutate_pytest_step_run(
            data,
            "Check critical invariant manifest",
            "# " + CHECKER_INVOCATION,
        )
        tmp_path = _write_temp_workflow(data)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_when_checker_is_echo_only(self):
        data = _load_workflow(_WORKFLOW)
        _mutate_pytest_step_run(
            data,
            "Check critical invariant manifest",
            "echo " + CHECKER_INVOCATION,
        )
        tmp_path = _write_temp_workflow(data)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_when_pin_only_in_comment(self):
        data = _load_workflow(_WORKFLOW)
        _mutate_pylint_install(
            data,
            "python -m pip install --upgrade pip\n"
            "pip install -r requirements.txt\n"
            "pip install pylint==4.0.6\n"
            "# " + APPROVED_PYTEST_PIN,
        )
        tmp_path = _write_temp_workflow(data)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_when_unpinned_pytest_reinstall_follows_pin(self):
        data = _load_workflow(_WORKFLOW)
        install = _job_install_run(_WORKFLOW, "pytest")
        _mutate_pytest_step_run(
            data,
            "Install dependencies",
            install + "\npip install pytest",
        )
        tmp_path = _write_temp_workflow(data)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()


class ManifestParserTests(unittest.TestCase):
    def test_rejects_malformed_paths(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "bad.txt"
            manifest.write_text("tests/../outside.py" + chr(10))
            with self.assertRaises(SystemExit):
                _checker._parse_manifest(manifest)

    def test_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "dup.txt"
            manifest.write_text(
                "tests/test_ci_contract.py" + chr(10) + "tests/test_ci_contract.py" + chr(10)
            )
            with self.assertRaises(SystemExit):
                _checker._parse_manifest(manifest)

    def test_rejects_absolute_path(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "abs.txt"
            manifest.write_text("/etc/passwd" + chr(10))
            with self.assertRaises(SystemExit):
                _checker._parse_manifest(manifest)

    def test_missing_manifest_exits_nonzero(self):
        proc = subprocess.run(
            [sys.executable, str(_CHECKER), "--manifest", "tests/nonexistent-manifest.txt"],
            cwd=_REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)


class CheckerSubprocessTests(unittest.TestCase):
    def test_collect_return_zero_passes(self):
        with mock.patch("check_ci_critical_invariants.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            with tempfile.TemporaryDirectory() as td:
                manifest = Path(td) / "manifest.txt"
                manifest.write_text("tests/test_ci_contract.py" + chr(10))
                with mock.patch.dict(
                    os.environ,
                    {"CONVMEM_CONFIG": "/tmp/convmem-ci/config.toml"},
                    clear=False,
                ):
                    code = _checker.main(["--manifest", str(manifest)])
        self.assertEqual(code, 0)
        kwargs = run.call_args.kwargs
        self.assertFalse(kwargs.get("shell", False))
        self.assertEqual(kwargs["cwd"], _checker._repo_root())
        self.assertEqual(kwargs["env"]["CONVMEM_CONFIG"], "/tmp/convmem-ci/config.toml")

    def test_collect_return_five_fails(self):
        with mock.patch("check_ci_critical_invariants.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 5, "", "")
            with tempfile.TemporaryDirectory() as td:
                manifest = Path(td) / "manifest.txt"
                manifest.write_text("tests/test_ci_contract.py" + chr(10))
                code = _checker.main(["--manifest", str(manifest)])
        self.assertEqual(code, 1)

    def test_collect_other_nonzero_fails(self):
        with mock.patch("check_ci_critical_invariants.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 2, "", "error")
            with tempfile.TemporaryDirectory() as td:
                manifest = Path(td) / "manifest.txt"
                manifest.write_text("tests/test_ci_contract.py" + chr(10))
                code = _checker.main(["--manifest", str(manifest)])
        self.assertEqual(code, 1)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tests_dir = Path(td) / "tests"
            tests_dir.mkdir()
            outside = Path(td) / "outside.py"
            outside.write_text("def test_outside(): pass" + chr(10))
            link = tests_dir / "escape_link.py"
            link.symlink_to(outside)
            with self.assertRaises(SystemExit):
                _checker._validate_target(Path(td), "tests/escape_link.py")

    def test_in_tree_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tests_dir = Path(td) / "tests"
            tests_dir.mkdir()
            real = tests_dir / "real_target.py"
            real.write_text("def test_real(): pass" + chr(10))
            link = tests_dir / "alias.py"
            link.symlink_to(real)
            with self.assertRaises(SystemExit):
                _checker._validate_target(Path(td), "tests/alias.py")


if __name__ == "__main__":
    unittest.main()
