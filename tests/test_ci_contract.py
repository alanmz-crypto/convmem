"""CI workflow and critical-invariant checker contract tests."""

from __future__ import annotations

import importlib.util
import os
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

def _load_checker():
    spec = importlib.util.spec_from_file_location("check_ci_critical_invariants", _CHECKER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_ci_critical_invariants"] = mod
    spec.loader.exec_module(mod)
    return mod

_checker = _load_checker()

def _job_run_blocks(workflow_path: Path, job_name: str) -> list[str]:
    data = yaml.safe_load(workflow_path.read_text())
    job = data["jobs"][job_name]
    runs: list[str] = []
    for step in job.get("steps", []):
        if "run" in step:
            runs.append(step["run"])
    return runs

def _job_install_run(workflow_path: Path, job_name: str) -> str:
    for block in _job_run_blocks(workflow_path, job_name):
        if "pip install" in block:
            return block
    raise AssertionError(f"no install run block in job {job_name}")

def _assert_workflow_contract(workflow_path: Path) -> None:
    pylint_install = _job_install_run(workflow_path, "pylint")
    pytest_install = _job_install_run(workflow_path, "pytest")
    assert APPROVED_PYTEST_PIN in pylint_install
    assert APPROVED_PYTEST_PIN in pytest_install
    pylint_runs = _job_run_blocks(workflow_path, "pylint")
    pytest_runs = _job_run_blocks(workflow_path, "pytest")
    assert any(isinstance(block, str) and VERSION_LOG_CMD in block for block in pylint_runs)
    assert any(isinstance(block, str) and VERSION_LOG_CMD in block for block in pytest_runs)
    assert any(isinstance(block, str) and FULL_SUITE_CMD in block for block in pytest_runs)
    assert any(isinstance(block, str) and CHECKER_INVOCATION in block for block in pytest_runs)

class WorkflowContractTests(unittest.TestCase):
    def test_workflow_contract_live_file(self):
        _assert_workflow_contract(_WORKFLOW)

    def test_pin_constants_document_execution_evidence(self):
        self.assertEqual(APPROVED_PYTEST_PIN, "pytest==9.1.1")
        self.assertTrue(PYTEST_PIN_EXECUTION_EVIDENCE.endswith("Z"))

    def test_contract_fails_without_pylint_pin(self):
        text = _WORKFLOW.read_text().replace(APPROVED_PYTEST_PIN, "pytest")
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as tmp:
            tmp.write(text)
            tmp_path = Path(tmp.name)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_without_pytest_job_pin(self):
        data = yaml.safe_load(_WORKFLOW.read_text())
        install = data["jobs"]["pytest"]["steps"][2]["run"]
        data["jobs"]["pytest"]["steps"][2]["run"] = install.replace(
            APPROVED_PYTEST_PIN, "pytest"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as tmp:
            yaml.safe_dump(data, tmp)
            tmp_path = Path(tmp.name)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_without_full_suite(self):
        text = _WORKFLOW.read_text().replace(FULL_SUITE_CMD, "python -m pytest")
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as tmp:
            tmp.write(text)
            tmp_path = Path(tmp.name)
        try:
            with self.assertRaises(AssertionError):
                _assert_workflow_contract(tmp_path)
        finally:
            tmp_path.unlink()

    def test_contract_fails_without_checker(self):
        text = _WORKFLOW.read_text().replace(CHECKER_INVOCATION, "echo no-checker")
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as tmp:
            tmp.write(text)
            tmp_path = Path(tmp.name)
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
            manifest.write_text("tests/test_ci_contract.py" + chr(10) + "tests/test_ci_contract.py" + chr(10))
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
                with mock.patch.dict(os.environ, {"CONVMEM_CONFIG": "/tmp/convmem-ci/config.toml"}, clear=False):
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

if __name__ == "__main__":
    unittest.main()
