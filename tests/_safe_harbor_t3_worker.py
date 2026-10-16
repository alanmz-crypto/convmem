"""Stdlib-isolated launcher for Safe Harbor T3 + guard regression suites."""

from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve()
PYTHON_CHILD = [sys.executable, "-s", "-B"]
RUN_TIMEOUT_SECONDS = 900.0
FULL_SUITE_TIMEOUT_SECONDS = 90 * 60.0
CHECKER_TIMEOUT_SECONDS = 30 * 60.0

SUITES = {
    "t3": ROOT / "tests" / "test_safe_harbor_t3.py",
    "guard": ROOT / "tests" / "test_chroma_write_guard.py",
    "t1": ROOT / "tests" / "test_safe_harbor_t1.py",
}

INTEGRATION_MODULES = (
    SUITES["t3"],
    ROOT / "tests" / "test_safe_harbor_t3_matrix.py",
    SUITES["guard"],
    SUITES["t1"],
    ROOT / "tests" / "test_safe_harbor_t3_backend_proof.py",
    ROOT / "tests" / "test_ci_contract.py",
    ROOT / "tests" / "test_safe_harbor_t3_ci.py",
    ROOT / "tests" / "test_r2b_v2_implementation_revision.py",
)

HASH_TRACKED_PATHS = (
    ROOT / "chroma_write_guard.py",
    ROOT / "doctor.py",
    ROOT / "watch.py",
    ROOT / "scripts" / "chroma_guard.py",
    ROOT / "scripts" / "check_ci_critical_invariants.py",
    ROOT / ".github" / "workflows" / "pylint.yml",
    ROOT / "tests" / "ci-critical-invariants.txt",
    ROOT / "docs" / "plans" / "R2B-V2-WRITER-COVERAGE-INVENTORY.json",
    ROOT / "docs" / "plans" / "SHADOW-WRITER-COVERAGE-INVENTORY.json",
    ROOT / "docs" / "CONVMEM-TLDR.md",
    ROOT / "tests" / "test_safe_harbor_t3_backend_proof.py",
    ROOT / "tests" / "test_r2b_v2_implementation_revision.py",
    ROOT / "tests" / "test_chroma_write_guard.py",
    ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
    ROOT / "tests" / "_safe_harbor_restic_ci.py",
    ROOT / "tests" / "test_safe_harbor_t3.py",
    ROOT / "tests" / "test_safe_harbor_t3_matrix.py",
    ROOT / "tests" / "safe_harbor_t3_fixtures.py",
    ROOT / "tests" / "_safe_harbor_bootstrap.py",
    ROOT / "tests" / "_safe_harbor_t3_fault_worker.py",
    ROOT / "tests" / "_chroma_write_guard_worker.py",
    ROOT / "tests" / "test_ci_contract.py",
    ROOT / "tests" / "test_safe_harbor_t3_ci.py",
    WORKER,
)

LINT_PYTHON_PATHS = (
    ROOT / "tests" / "_safe_harbor_bootstrap.py",
    ROOT / "tests" / "_safe_harbor_t3_worker.py",
    ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
    ROOT / "tests" / "_safe_harbor_restic_ci.py",
    ROOT / "tests" / "test_safe_harbor_t3_backend_proof.py",
    ROOT / "tests" / "test_safe_harbor_t3_ci.py",
    ROOT / "tests" / "test_ci_contract.py",
)

CHECKER_SCRIPT = ROOT / "scripts" / "check_ci_critical_invariants.py"

@functools.lru_cache(maxsize=1)
def _load_bootstrap_module() -> ModuleType:
    # pylint: disable=duplicate-code
    # -I parent must file-spec bootstrap before package imports exist (mirrored in backend_worker).
    path = ROOT / "tests" / "_safe_harbor_bootstrap.py"
    spec = importlib.util.spec_from_file_location("safe_harbor_t3_bootstrap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bootstrap from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# pylint: enable=duplicate-code


def _load_backend_worker_module() -> ModuleType:
    bootstrap = _load_bootstrap_module()
    return bootstrap.load_stdlib_module(
        ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
        "safe_harbor_t3_backend_worker",
    )


def _temp_parent_dir(backend: ModuleType) -> str:
    return backend.mkdtemp_parent_dir()


def _parent_uid_and_env(
    backend: ModuleType,
    *,
    env_profile: str = "proof",
) -> tuple[int, Path, Path, dict[str, str], dict[str, str]]:
    bootstrap = _load_bootstrap_module()
    bootstrap.require_parent_bootstrap_flags()
    parent_uid = bootstrap.parent_launcher_uid()
    evidence_root = Path(tempfile.mkdtemp(prefix="safe-harbor-t3-suite-", dir=_temp_parent_dir(backend)))
    fixture_root = evidence_root / "fixture"
    fixture_root.mkdir(parents=True)
    (fixture_root / "pytest-tmp").mkdir()
    fixture_meta: dict[str, str] = {}
    env = backend.build_allowlisted_env(
        fixture_root,
        evidence_root,
        expected_uid=parent_uid,
        profile=env_profile,
        fixture_meta=fixture_meta,
    )
    return parent_uid, fixture_root, evidence_root, env, fixture_meta


def _source_hashes() -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in HASH_TRACKED_PATHS}


def _decode_timeout_streams(exc: subprocess.TimeoutExpired) -> str:
    def _part(data: object) -> str:
        if data is None:
            return ""
        if isinstance(data, str):
            return data
        if isinstance(data, bytes):
            return data.decode(errors="replace")
        return str(data)

    return _part(exc.stdout) + _part(exc.stderr)


def _write_log(evidence_root: Path, name: str, payload: str, *, echo: bool) -> None:
    path = evidence_root / name
    path.write_text(payload, encoding="utf-8")
    if echo and payload.strip():
        end = "" if payload.endswith("\n") else "\n"
        print(payload, file=sys.stderr, end=end)


def _emit_evidence_hint(evidence_root: Path, rc: int) -> None:
    if rc != 0:
        print(f"safe-harbor evidence: {evidence_root}", file=sys.stderr)


def _child_returncode(proc: subprocess.CompletedProcess[str]) -> int | None:
    return proc.returncode


def _exit_code(summary: dict[str, object]) -> int:
    rc = summary.get("pytest_returncode")
    if rc is None:
        return 124
    return int(rc)


def _run_pytest_suite(
    *,
    module: Path,
    env: dict[str, str],
    fixture_root: Path,
    evidence_root: Path,
    label: str,
    timeout: float = RUN_TIMEOUT_SECONDS,
    verbose: bool = True,
) -> dict[str, object]:
    pytest_cmd = [
        *PYTHON_CHILD,
        "-m",
        "pytest",
        str(module),
    ]
    if verbose:
        pytest_cmd.extend(["-v", "--tb=line"])
    else:
        pytest_cmd.append("-q")
    pytest_cmd.extend(
        [
            "-p",
            "no:cacheprovider",
            f"--basetemp={fixture_root / 'pytest-tmp' / label}",
        ]
    )
    harness_before = hashlib.sha256(module.read_bytes()).hexdigest()
    summary: dict[str, object] = {
        "label": label,
        "pytest_command": pytest_cmd,
        "harness_sha256_before": harness_before,
    }
    started = time.monotonic()
    log_name = f"{label}.pytest.log"
    bootstrap = _load_bootstrap_module()
    try:
        proc = bootstrap.run_harness_child(pytest_cmd, env=env, timeout=timeout)
        rc = _child_returncode(proc)
        summary["pytest_returncode"] = rc if rc is not None else 124
        summary["pytest_elapsed_seconds"] = time.monotonic() - started
        combined = proc.stdout + proc.stderr
        _write_log(evidence_root, log_name, combined, echo=bool(rc))
    except subprocess.TimeoutExpired as exc:
        summary["pytest_timed_out"] = True
        summary["pytest_returncode"] = 124
        _write_log(evidence_root, log_name, _decode_timeout_streams(exc), echo=True)
    summary["harness_sha256_after"] = hashlib.sha256(module.read_bytes()).hexdigest()
    return summary


def _run_pylint(paths: list[Path], env: dict[str, str], evidence_root: Path) -> dict[str, object]:
    lint_cmd = [*PYTHON_CHILD, "-m", "pylint", "--output-format=json", *[str(path) for path in paths]]
    started = time.monotonic()
    summary: dict[str, object] = {"pylint_command": lint_cmd}
    bootstrap = _load_bootstrap_module()
    try:
        proc = bootstrap.run_harness_child(lint_cmd, env=env, timeout=RUN_TIMEOUT_SECONDS)
        lint_rc = _child_returncode(proc)
        summary["pylint_returncode"] = lint_rc if lint_rc is not None else 124
        summary["pylint_elapsed_seconds"] = time.monotonic() - started
        report = evidence_root / "pylint-report.json"
        report.write_text(proc.stdout, encoding="utf-8")
        gate_cmd = [
            *PYTHON_CHILD,
            str(ROOT / "scripts" / "pylint_regression_gate.py"),
            "ci",
            "--report",
            str(report),
            "--pylint-status",
            str(summary["pylint_returncode"]),
            "--base-ref",
            "e08100ff1c2fe8474f897d6ae3d3c55e5b1c7e5f",
            "--git-cwd",
            str(ROOT),
        ]
        gate = bootstrap.run_harness_child(gate_cmd, env=env, timeout=RUN_TIMEOUT_SECONDS)
        gate_rc = _child_returncode(gate)
        summary["pylint_gate_command"] = gate_cmd
        summary["pylint_gate_returncode"] = gate_rc if gate_rc is not None else 124
        combined = proc.stderr + gate.stdout + gate.stderr
        _write_log(evidence_root, "pylint.log", combined, echo=bool(gate_rc))
    except subprocess.TimeoutExpired as exc:
        summary["pylint_timed_out"] = True
        summary["pylint_returncode"] = 124
        summary["pylint_gate_returncode"] = 124
        _write_log(evidence_root, "pylint.log", _decode_timeout_streams(exc), echo=True)
    return summary


def _lint_exit_code(lint: dict[str, object]) -> int:
    gate_rc = lint.get("pylint_gate_returncode")
    if gate_rc is None:
        gate_rc = lint.get("pylint_returncode")
    if gate_rc is None:
        return 124
    return int(gate_rc)


def _finalize_summary(
    evidence_root: Path,
    *,
    mode: str,
    parent_uid: int,
    fixture_root: Path,
    source_hashes_before: dict[str, str],
    runs: list[dict[str, object]],
    lint: dict[str, object] | None = None,
    extra: dict[str, object] | None = None,
) -> int:
    source_hashes_after = _source_hashes()
    summary: dict[str, object] = {
        "mode": mode,
        "uid": parent_uid,
        "interpreter": sys.executable,
        "fixture_root": str(fixture_root),
        "evidence_root": str(evidence_root),
        "source_hashes_before": source_hashes_before,
        "source_hashes_after": source_hashes_after,
        "runs": runs,
    }
    if lint is not None:
        summary["lint"] = lint
    if extra:
        summary.update(extra)
    (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if source_hashes_before != source_hashes_after:
        rc = 1
        _emit_evidence_hint(evidence_root, rc)
        return rc
    for item in runs:
        if _exit_code(item) != 0:
            rc = _exit_code(item)
            _emit_evidence_hint(evidence_root, rc)
            return rc
    if lint is not None:
        lint_rc = _lint_exit_code(lint)
        if lint_rc != 0:
            _emit_evidence_hint(evidence_root, lint_rc)
            return lint_rc
    checker_rc = summary.get("checker_returncode")
    if checker_rc is not None and int(checker_rc) != 0:
        rc = int(checker_rc)
        _emit_evidence_hint(evidence_root, rc)
        return rc
    full_rc = summary.get("full_suite_returncode")
    if full_rc is not None and int(full_rc) != 0:
        rc = int(full_rc)
        _emit_evidence_hint(evidence_root, rc)
        return rc
    return 0


def run_suite(mode: str) -> int:
    backend = _load_backend_worker_module()
    parent_uid, fixture_root, evidence_root, env, _fixture_meta = _parent_uid_and_env(backend)
    child_env = dict(env)
    if mode == "suite":
        modules = [
            SUITES["t3"],
            ROOT / "tests" / "test_safe_harbor_t3_matrix.py",
            SUITES["guard"],
            SUITES["t1"],
        ]
    elif mode in SUITES:
        modules = [SUITES[mode]]
    else:
        raise RuntimeError(f"unknown mode {mode}")
    source_hashes_before = _source_hashes()
    results: list[dict[str, object]] = []
    for module in modules:
        results.append(
            _run_pytest_suite(
                module=module,
                env=child_env,
                fixture_root=fixture_root,
                evidence_root=evidence_root,
                label=module.stem,
            )
        )
    lint = _run_pylint(list(LINT_PYTHON_PATHS), child_env, evidence_root)
    return _finalize_summary(
        evidence_root,
        mode=mode,
        parent_uid=parent_uid,
        fixture_root=fixture_root,
        source_hashes_before=source_hashes_before,
        runs=results,
        lint=lint,
    )


def run_integration() -> int:
    """Codex-supervised local selection (not a full default workstation suite)."""
    backend = _load_backend_worker_module()
    parent_uid, fixture_root, evidence_root, env, _fixture_meta = _parent_uid_and_env(backend)
    source_hashes_before = _source_hashes()
    results: list[dict[str, object]] = []
    for module in INTEGRATION_MODULES:
        results.append(
            _run_pytest_suite(
                module=module,
                env=env,
                fixture_root=fixture_root,
                evidence_root=evidence_root,
                label=module.stem,
            )
        )
    lint = _run_pylint(list(LINT_PYTHON_PATHS), env, evidence_root)
    return _finalize_summary(
        evidence_root,
        mode="run-integration",
        parent_uid=parent_uid,
        fixture_root=fixture_root,
        source_hashes_before=source_hashes_before,
        runs=results,
        lint=lint,
    )


def run_ci_collect() -> int:
    backend = _load_backend_worker_module()
    parent_uid, _, evidence_root, env, fixture_meta = _parent_uid_and_env(backend, env_profile="full_ci")
    source_hashes_before = _source_hashes()
    checker_cmd = [*PYTHON_CHILD, str(CHECKER_SCRIPT)]
    summary: dict[str, object] = {
        "checker_command": checker_cmd,
        "uid": parent_uid,
        "interpreter": sys.executable,
        "source_hashes_before": source_hashes_before,
        "selected_tools": dict(fixture_meta),
    }
    started = time.monotonic()
    bootstrap = _load_bootstrap_module()
    try:
        proc = bootstrap.run_harness_child(checker_cmd, env=env, timeout=CHECKER_TIMEOUT_SECONDS)
        rc = _child_returncode(proc)
        summary["checker_returncode"] = rc if rc is not None else 124
        summary["checker_elapsed_seconds"] = time.monotonic() - started
        combined = proc.stdout + proc.stderr
        _write_log(evidence_root, "checker.log", combined, echo=True)
    except subprocess.TimeoutExpired as exc:
        summary["checker_timed_out"] = True
        summary["checker_returncode"] = 124
        _write_log(evidence_root, "checker.log", _decode_timeout_streams(exc), echo=True)
    source_hashes_after = _source_hashes()
    summary["source_hashes_after"] = source_hashes_after
    (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if source_hashes_before != source_hashes_after:
        rc = 1
        _emit_evidence_hint(evidence_root, rc)
        return rc
    checker_rc = summary.get("checker_returncode")
    if checker_rc is None:
        rc = 124
        _emit_evidence_hint(evidence_root, rc)
        return rc
    rc = int(checker_rc)
    _emit_evidence_hint(evidence_root, rc)
    return rc


def run_ci() -> int:
    backend = _load_backend_worker_module()
    parent_uid, fixture_root, evidence_root, env, fixture_meta = _parent_uid_and_env(
        backend,
        env_profile="full_ci",
    )
    source_hashes_before = _source_hashes()
    pytest_cmd = [
        *PYTHON_CHILD,
        "-m",
        "pytest",
        "-q",
        "-ra",
        "-p",
        "no:cacheprovider",
        f"--basetemp={fixture_root / 'pytest-tmp' / 'full-suite'}",
    ]
    summary: dict[str, object] = {
        "full_suite_command": pytest_cmd,
        "uid": parent_uid,
        "interpreter": sys.executable,
        "source_hashes_before": source_hashes_before,
        "selected_tools": dict(fixture_meta),
    }
    started = time.monotonic()
    bootstrap = _load_bootstrap_module()
    try:
        proc = bootstrap.run_harness_child(
            pytest_cmd,
            env=env,
            timeout=FULL_SUITE_TIMEOUT_SECONDS,
        )
        rc = _child_returncode(proc)
        summary["full_suite_returncode"] = rc if rc is not None else 124
        summary["full_suite_elapsed_seconds"] = time.monotonic() - started
        combined = proc.stdout + proc.stderr
        _write_log(evidence_root, "full-suite.pytest.log", combined, echo=True)
    except subprocess.TimeoutExpired as exc:
        summary["full_suite_timed_out"] = True
        summary["full_suite_returncode"] = 124
        _write_log(evidence_root, "full-suite.pytest.log", _decode_timeout_streams(exc), echo=True)
    source_hashes_after = _source_hashes()
    summary["source_hashes_after"] = source_hashes_after
    (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if source_hashes_before != source_hashes_after:
        rc = 1
        _emit_evidence_hint(evidence_root, rc)
        return rc
    full_rc = summary.get("full_suite_returncode")
    if full_rc is None:
        rc = 124
        _emit_evidence_hint(evidence_root, rc)
        return rc
    rc = int(full_rc)
    _emit_evidence_hint(evidence_root, rc)
    return rc


def main() -> int:
    if len(sys.argv) < 2:
        print(
            f"usage: {WORKER.name} run-suite|run-t3|run-guard|run-t1|"
            "run-ci-collect|run-ci|run-integration",
            file=sys.stderr,
        )
        return 2
    mode = sys.argv[1]
    if mode == "run-suite":
        return run_suite("suite")
    if mode == "run-t3":
        return run_suite("t3")
    if mode == "run-guard":
        return run_suite("guard")
    if mode == "run-t1":
        return run_suite("t1")
    if mode == "run-ci-collect":
        return run_ci_collect()
    if mode == "run-ci":
        return run_ci()
    if mode == "run-integration":
        return run_integration()
    print(f"unknown mode {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
