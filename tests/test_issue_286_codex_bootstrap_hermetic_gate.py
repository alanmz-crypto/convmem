"""Hermetic gate for Arc Codex #286 T1: isolation probe plus scoped pytest."""

# pylint: disable=consider-using-with

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from incremental_jsonl_isolation import (
    IsolationBoundary,
    create_fresh_root,
    known_production_roots,
    sanitized_worker_env,
)

WORKER = Path(__file__).with_name("issue_286_codex_bootstrap_isolation_worker.py")
REPO_ROOT = Path(__file__).resolve().parents[1]

ISOLATED_PYTEST_TARGETS = (
    "tests/test_issue_286_codex_bootstrap_v2_t1.py",
    "tests/test_incremental_jsonl_bootstrap_command.py",
    "tests/test_incremental_jsonl_bootstrap_safety.py::test_paid_transport_disables_automatic_redirects",
    "tests/test_incremental_jsonl_bootstrap_safety.py::test_invocation_journal_allows_exactly_one_recovery",
    "tests/test_incremental_jsonl_bootstrap_supersession.py::test_admissible_supersession_archives_exact_bytes_and_preserves_evidence",
)
EXPECTED_ISOLATED_PASS_COUNT = 10


def _worker_env(tmp_path: Path) -> tuple[IsolationBoundary, dict[str, str]]:
    root, token = create_fresh_root(tmp_path)
    parent_home = Path.home()
    env = sanitized_worker_env(
        root, token, forbidden_roots=known_production_roots(home=parent_home)
    )
    with pytest.MonkeyPatch.context() as mp:
        for key, value in env.items():
            mp.setenv(key, value)
        for name in tuple(os.environ):
            if name in {"CONVMEM_INCREMENTAL_TOKEN", "CONVMEM_INCREMENTAL_FORBIDDEN"}:
                continue
            if any(marker in name.upper() for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")):
                mp.delenv(name, raising=False)
        boundary = IsolationBoundary.from_environment()
    return boundary, env


def _run_worker(
    boundary: IsolationBoundary,
    env: dict[str, str],
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(WORKER), *args],
        cwd=REPO_ROOT,
        env=env,
        close_fds=True,
        start_new_session=True,
        check=False,
        capture_output=True,
        text=True,
    )


def test_boundary_probe_denies_network_filesystem_and_services(tmp_path: Path) -> None:
    boundary, env = _worker_env(tmp_path)
    result = _run_worker(boundary, env, "boundary-probe")
    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["root"] == str(boundary.root)
    assert evidence["network"] == "IsolationViolation"
    assert evidence["watcher"] == "IsolationViolation"
    assert evidence["forbidden_root"] == "IsolationViolation"
    assert evidence["root_escape"] == "IsolationViolation"
    assert evidence["credential_names"] == []
    assert evidence["production_override_names"] == []
    assert str(evidence["home"]).startswith(str(boundary.root))


def test_hash_oracle_vectors_are_stable(tmp_path: Path) -> None:
    boundary, env = _worker_env(tmp_path)
    result = _run_worker(boundary, env, "hash-oracle")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    for key in (
        "operation_id",
        "grant_fingerprint_v2",
        "source_state_id",
        "kiro_default_state_id",
    ):
        assert key in payload
        assert isinstance(payload[key], str) and len(payload[key]) > 0
    assert payload["source_state_id"] != payload["kiro_default_state_id"]


def test_t1_and_v1_regressions_in_isolated_worker(tmp_path: Path) -> None:
    boundary, env = _worker_env(tmp_path)
    args = ["pytest", "-q", *ISOLATED_PYTEST_TARGETS]
    result = _run_worker(boundary, env, *args)
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    combined = result.stdout + result.stderr
    assert "10 passed" in combined
