"""Stdlib-isolated launcher for Safe Harbor T3 + guard regression suites."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve()
PYTHON = "/home/lauer/miniforge3/bin/python"
PYTHON_CHILD = [PYTHON, "-s", "-B"]
REQUIRED_UID = 1000
RUN_TIMEOUT_SECONDS = 900.0

SUITES = {
    "t3": ROOT / "tests" / "test_safe_harbor_t3.py",
    "guard": ROOT / "tests" / "test_chroma_write_guard.py",
    "t1": ROOT / "tests" / "test_safe_harbor_t1.py",
}


def _load_backend_worker_module() -> ModuleType:
    path = ROOT / "tests" / "_safe_harbor_t3_backend_worker.py"
    spec = importlib.util.spec_from_file_location("safe_harbor_t3_backend_worker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load backend worker from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
) -> dict[str, object]:
    pytest_cmd = [
        *PYTHON_CHILD,
        "-m",
        "pytest",
        str(module),
        "-v",
        "--tb=line",
        "-p",
        "no:cacheprovider",
        f"--basetemp={fixture_root / 'pytest-tmp' / label}",
    ]
    harness_before = hashlib.sha256(module.read_bytes()).hexdigest()
    summary: dict[str, object] = {
        "label": label,
        "pytest_command": pytest_cmd,
        "harness_sha256_before": harness_before,
    }
    started = time.monotonic()
    try:
        proc = subprocess.run(
            pytest_cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
            check=False,
        )
        summary["pytest_returncode"] = proc.returncode
        summary["pytest_elapsed_seconds"] = time.monotonic() - started
        (evidence_root / f"{label}.pytest.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        summary["pytest_timed_out"] = True
        summary["pytest_returncode"] = 124
        (evidence_root / f"{label}.pytest.log").write_text(
            (exc.stdout or b"").decode(errors="replace") + (exc.stderr or b"").decode(errors="replace"),
            encoding="utf-8",
        )
    summary["harness_sha256_after"] = hashlib.sha256(module.read_bytes()).hexdigest()
    return summary


def _run_pylint(paths: list[Path], env: dict[str, str], evidence_root: Path) -> dict[str, object]:
    lint_cmd = [*PYTHON_CHILD, "-m", "pylint", "-sn", *[str(path) for path in paths]]
    started = time.monotonic()
    summary: dict[str, object] = {"pylint_command": lint_cmd}
    try:
        proc = subprocess.run(
            lint_cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
            check=False,
        )
        summary["pylint_returncode"] = proc.returncode
        summary["pylint_elapsed_seconds"] = time.monotonic() - started
        (evidence_root / "pylint.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired:
        summary["pylint_timed_out"] = True
        summary["pylint_returncode"] = 124
    return summary


def run_suite(mode: str) -> int:
    if os.getuid() != REQUIRED_UID:
        raise RuntimeError(f"refusing uid {os.getuid()} (required {REQUIRED_UID})")
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise RuntimeError("bootstrap requires python -I -S -B")
    backend = _load_backend_worker_module()
    evidence_root = Path(tempfile.mkdtemp(prefix="safe-harbor-t3-suite-", dir="/tmp"))
    fixture_root = evidence_root / "fixture"
    fixture_root.mkdir(parents=True)
    (fixture_root / "pytest-tmp").mkdir()
    env = backend.build_allowlisted_env(fixture_root, evidence_root)
    child_env = dict(env)
    if mode == "suite":
        modules = [SUITES["t3"], SUITES["guard"], SUITES["t1"]]
    elif mode in SUITES:
        modules = [SUITES[mode]]
    else:
        raise RuntimeError(f"unknown mode {mode}")
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
    lint = _run_pylint(
        [ROOT / "tests" / "test_safe_harbor_t3.py", WORKER, ROOT / "chroma_write_guard.py"],
        child_env,
        evidence_root,
    )
    summary = {
        "mode": mode,
        "uid": os.getuid(),
        "fixture_root": str(fixture_root),
        "evidence_root": str(evidence_root),
        "runs": results,
        "lint": lint,
    }
    (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    for item in results:
        if _exit_code(item) != 0:
            return _exit_code(item)
    lint_rc = lint.get("pylint_returncode")
    if lint_rc is not None and int(lint_rc) != 0:
        return int(lint_rc)
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {WORKER.name} run-suite|run-t3|run-guard|run-t1", file=sys.stderr)
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
    print(f"unknown mode {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
