"""Hermetic gate for Arc Codex #286 T1 (external bwrap boundary)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from incremental_jsonl_isolation import (
    IsolationBoundary,
    create_fresh_root,
    known_production_roots,
    sanitized_worker_env,
)
from tests.issue_286_codex_bootstrap_bwrap import (
    ISSUE_286_BWRAP_ACTIVE_ENV,
    REPO_ROOT,
    issue_286_bwrap_integration_available,
    run_bwrap,
)
from tests.issue_286_codex_bootstrap_bwrap import run_bwrap_capability_check
from tests.watch_oom_live_diagnosis_net_probe import (
    parent_can_connect_loopback,
    parent_loopback_listener,
    parent_net_namespace_id,
    verify_dual_net_probe_artifacts,
    write_self_loopback_probe,
)

WORKER = Path(__file__).with_name("issue_286_codex_bootstrap_isolation_worker.py")

ISOLATED_PYTEST_TARGETS = (
    "tests/test_issue_286_codex_bootstrap_v2_t1.py",
    "tests/test_issue_286_codex_bootstrap_v2_t1_contract.py",
    "tests/test_issue_286_codex_bootstrap_v2_t1_gate.py",
    "tests/test_incremental_jsonl_bootstrap_command.py",
    "tests/test_incremental_jsonl_bootstrap_safety.py::test_paid_transport_disables_automatic_redirects",
    "tests/test_incremental_jsonl_bootstrap_safety.py::test_invocation_journal_allows_exactly_one_recovery",
    "tests/test_incremental_jsonl_bootstrap_supersession.py::test_admissible_supersession_archives_exact_bytes_and_preserves_evidence",
)
EXPECTED_ISOLATED_PASS_COUNT = 38

ISOLATED_PYTEST_TARGETS_T2 = (
    "tests/test_issue_286_codex_bootstrap_v2_t2_authority.py",
    "tests/test_issue_286_codex_bootstrap_v2_t2_accounting.py",
    "tests/test_issue_286_codex_bootstrap_v2_t2_crash_matrix.py",
    "tests/test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py",
    "tests/test_issue_286_codex_bootstrap_v2_t2_contract_evidence.py",
)
EXPECTED_ISOLATED_T2_PASS_COUNT = 87

ISOLATED_PYTEST_TARGETS_T3 = (
    "tests/test_issue_286_codex_bootstrap_v2_t3_writer_coordination.py",
    "tests/test_issue_286_codex_bootstrap_v2_t3_race_matrix.py",
    "tests/test_issue_286_codex_bootstrap_v2_t3_watch_integration.py",
    "tests/test_issue_286_codex_bootstrap_v2_t3_oracles.py",
    "tests/test_issue_286_codex_bootstrap_v2_t3_cli_watch_e2e.py",
    "tests/test_issue_286_codex_bootstrap_v2_t3_inventory.py",
)
EXPECTED_ISOLATED_T3_PASS_COUNT = 55  # set after count




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


@pytest.mark.skipif(
    not issue_286_bwrap_integration_available(),
    reason="issue_286_bwrap_unavailable",
)
def test_external_network_namespace_denied(tmp_path: Path) -> None:
    scratch = tmp_path / "bwrap-scratch"
    scratch.mkdir()
    outer_path = scratch / "outer.json"
    inner_path = scratch / "inner.json"
    with parent_loopback_listener() as port:
        assert parent_can_connect_loopback(port) is True
        inner_script = (
            "import sys\n"
            f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
            "from pathlib import Path\n"
            "from tests.watch_oom_live_diagnosis_net_probe import write_self_loopback_probe\n"
            f"write_self_loopback_probe(port={port}, result_path=Path({str(outer_path)!r}), role='outer')\n"
            f"write_self_loopback_probe(port={port}, result_path=Path({str(inner_path)!r}), role='inner')\n"
        )
        result = run_bwrap(
            [sys.executable, "-I", "-c", inner_script],
            scratch_root=scratch,
        )
        assert result.returncode == 0, result.stderr
    verify_dual_net_probe_artifacts(
        outer_path=outer_path,
        inner_path=inner_path,
        port=port,
        parent_netns=parent_net_namespace_id(),
        parent_positive_control=True,
    )


@pytest.mark.skipif(
    not issue_286_bwrap_integration_available(),
    reason="issue_286_bwrap_unavailable",
)
def test_external_filesystem_masks_production_paths(tmp_path: Path) -> None:
    scratch = tmp_path / "bwrap-fs"
    scratch.mkdir()
    source = scratch / "sources" / "probe.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text("{}\n", encoding="utf-8")
    repo_probe = REPO_ROOT / "README.md"
    caps = run_bwrap_capability_check(
        scratch_root=scratch,
        source_path=source,
        repo_probe_file=repo_probe,
    )
    assert caps["scratch_writable"] is True
    assert caps["production_share_read_blocked"] is True
    assert caps["production_share_write_blocked"] is True


@pytest.mark.skipif(
    not issue_286_bwrap_integration_available(),
    reason="issue_286_bwrap_unavailable",
)
def test_worker_boundary_probe_without_python_network_hooks(tmp_path: Path) -> None:
    boundary, env = _worker_env(tmp_path)
    result = run_bwrap(
        [sys.executable, "-I", str(WORKER), "boundary-probe"],
        scratch_root=boundary.root,
        extra_env=env,
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["network"]["status"] == "connect_failed"
    assert evidence["network"]["errno"] is not None
    assert evidence["forbidden_root"] == "IsolationViolation"
    assert evidence["root_escape"] == "IsolationViolation"


@pytest.mark.skipif(
    not issue_286_bwrap_integration_available(),
    reason="issue_286_bwrap_unavailable",
)
def test_t1_and_v1_regressions_in_bwrap(tmp_path: Path) -> None:
    boundary, env = _worker_env(tmp_path)
    args = ["pytest", "-q", *ISOLATED_PYTEST_TARGETS]
    result = run_bwrap(
        [sys.executable, "-I", str(WORKER), *args],
        scratch_root=boundary.root,
        extra_env=env,
        timeout=300.0,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    combined = result.stdout + result.stderr
    assert f"{EXPECTED_ISOLATED_PASS_COUNT} passed" in combined


@pytest.mark.skipif(
    not issue_286_bwrap_integration_available(),
    reason="issue_286_bwrap_unavailable",
)
def test_t2_authority_accounting_and_crash_matrix_in_bwrap(tmp_path: Path) -> None:
    boundary, env = _worker_env(tmp_path)
    args = ["pytest", "-q", *ISOLATED_PYTEST_TARGETS_T2]
    result = run_bwrap(
        [sys.executable, "-I", str(WORKER), *args],
        scratch_root=boundary.root,
        extra_env=env,
        timeout=300.0,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    combined = result.stdout + result.stderr
    assert f"{EXPECTED_ISOLATED_T2_PASS_COUNT} passed" in combined


@pytest.mark.skipif(
    not issue_286_bwrap_integration_available(),
    reason="issue_286_bwrap_unavailable",
)
def test_t3_writer_mediation_in_bwrap(tmp_path: Path) -> None:
    boundary, env = _worker_env(tmp_path)
    args = ["pytest", "-q", *ISOLATED_PYTEST_TARGETS_T3]
    result = run_bwrap(
        [sys.executable, "-I", str(WORKER), *args],
        scratch_root=boundary.root,
        extra_env=env,
        timeout=300.0,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    combined = result.stdout + result.stderr
    assert f"{EXPECTED_ISOLATED_T3_PASS_COUNT} passed" in combined
