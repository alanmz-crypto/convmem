"""Stdlib-isolated launcher for Safe Harbor T4 evidence suites."""

from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve()
PROBE = ROOT / "tests" / "_safe_harbor_t4_probe.py"
HARNESS = ROOT / "tests" / "_safe_harbor_t4_harness.py"
PYTHON_CHILD = [sys.executable, "-s", "-B"]
RUN_TIMEOUT_SECONDS = 900.0

SUITES = tuple(sorted(ROOT.glob("tests/test_safe_harbor_t4*.py"), key=lambda p: p.name))

HASH_TRACKED_PATHS = (
    ROOT / "propose_decision.py",
    ROOT / "conflict_events.py",
    ROOT / "observe.py",
    ROOT / "chroma_write_guard.py",
    ROOT / "chroma_write_store.py",
    ROOT / "convmem.py",
    WORKER,
    PROBE,
    HARNESS,
    ROOT / "tests" / "_safe_harbor_bootstrap.py",
    ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
    ROOT / "tests" / "_safe_harbor_t2_cli.py",
    *SUITES,
    *sorted(ROOT.glob("tests/_safe_harbor_t4*.py")),
)


@functools.lru_cache(maxsize=1)
def _load_bootstrap_module() -> ModuleType:
    path = ROOT / "tests" / "_safe_harbor_bootstrap.py"
    spec = importlib.util.spec_from_file_location("safe_harbor_t4_bootstrap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bootstrap from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_backend_worker() -> ModuleType:
    bootstrap = _load_bootstrap_module()
    return bootstrap.load_stdlib_module(
        ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
        "safe_harbor_t4_backend_worker",
    )


def _source_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    missing: list[str] = []
    for path in HASH_TRACKED_PATHS:
        if not path.is_file():
            missing.append(str(path))
            continue
        out[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    if missing:
        raise RuntimeError(f"T4 worker tracked inputs missing: {missing}")
    return out


def _child_returncode(proc) -> int | None:
    return proc.returncode


def _run_pytest(module: Path, env: dict[str, str], fixture_root: Path, evidence_root: Path) -> dict:
    bootstrap = _load_bootstrap_module()
    harness_before = _source_hashes()
    cmd = [
        *PYTHON_CHILD,
        "-c",
        "import sys,runpy; assert getattr(sys, '_safe_harbor_t4_network_refused', False); "
        "sys.argv[0]='pytest'; runpy.run_module('pytest',run_name='__main__')",
        str(module),
        "-v",
        "--tb=line",
        "-p",
        "no:cacheprovider",
        f"--basetemp={fixture_root / 'pytest-tmp' / module.stem}",
    ]
    label = module.stem
    summary: dict[str, object] = {"module": str(module), "pytest_command": cmd}
    summary["harness_sha256_before"] = harness_before
    started = time.monotonic()
    try:
        proc = bootstrap.run_harness_child(cmd, env=env, timeout=RUN_TIMEOUT_SECONDS)
        rc = _child_returncode(proc)
        summary["pytest_returncode"] = rc
        summary["pytest_timed_out"] = rc is None
        if rc is None:
            summary["pytest_returncode"] = 124
        combined = (proc.stdout or "") + (proc.stderr or "")
        log_path = evidence_root / f"{label}.pytest.log"
        log_path.write_text(combined, encoding="utf-8")
        summary["log_path"] = str(log_path)
        summary["stdout_sha256"] = hashlib.sha256((proc.stdout or "").encode()).hexdigest()
        summary["stderr_sha256"] = hashlib.sha256((proc.stderr or "").encode()).hexdigest()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        summary["pytest_returncode"] = 124
        summary["pytest_error"] = str(exc)
    summary["pytest_elapsed_seconds"] = time.monotonic() - started
    harness_after = _source_hashes()
    summary["harness_sha256_after"] = harness_after
    if harness_before != harness_after:
        summary["harness_drift"] = True
    else:
        summary["harness_drift"] = False
    return summary


def _resolve_modules(args: list[str]) -> tuple[list[Path], list[str]]:
    if not args or args[0] != "run-suite":
        return [], []
    rest = args[1:]
    if not rest:
        return list(SUITES), []
    modules: list[Path] = []
    for raw in rest:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        path = path.resolve()
        if path not in SUITES:
            raise RuntimeError(f"refusing module outside focused T4 suites: {path}")
        modules.append(path)
    return modules, rest


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args or args[0] != "run-suite":
        print(
            "usage: python -I -S -B tests/_safe_harbor_t4_worker.py run-suite "
            "[tests/test_safe_harbor_t4_matrix.py ...]",
            file=sys.stderr,
        )
        return 2
    try:
        modules, _extra = _resolve_modules(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not modules:
        print("refusing empty T4 suite selection", file=sys.stderr)
        return 2

    bootstrap = _load_bootstrap_module()
    backend = _load_backend_worker()
    bootstrap.require_parent_bootstrap_flags()
    parent_uid = bootstrap.parent_launcher_uid()
    before_hashes = _source_hashes()
    evidence_root = Path(
        tempfile.mkdtemp(prefix="safe-harbor-t4-suite-", dir=backend.mkdtemp_parent_dir())
    )
    fixture_root = evidence_root / "fixture"
    fixture_root.mkdir(parents=True)
    (fixture_root / "pytest-tmp").mkdir()
    env = backend.build_allowlisted_env(
        fixture_root,
        evidence_root,
        expected_uid=parent_uid,
        profile="proof",
        fixture_meta={},
    )
    env["SAFE_HARBOR_T3_BOOTSTRAPPED"] = "1"
    env["SAFE_HARBOR_T3_FIXTURE_ROOT"] = str(fixture_root)
    env["SAFE_HARBOR_T3_EVIDENCE_ROOT"] = str(evidence_root)
    env["SAFE_HARBOR_T3_EXPECTED_UID"] = str(parent_uid)

    network_hook = fixture_root / "network-hook"
    network_hook.mkdir()
    (network_hook / "sitecustomize.py").write_bytes(
        (ROOT / "tests" / "_safe_harbor_t4_network.py").read_bytes()
    )
    network_log = fixture_root / "network-refusals.jsonl"
    env["SAFE_HARBOR_T4_NETWORK_LOG"] = str(network_log)
    env["PYTHONPATH"] = str(network_hook) + ":" + str(ROOT)
    results = [_run_pytest(module, env, fixture_root, evidence_root) for module in modules]
    for row in results:
        print(f"T4 evidence log: {row.get('log_path')}", file=sys.stderr)
    after_hashes = _source_hashes()
    refusals = [json.loads(line) for line in network_log.read_text().splitlines()] if network_log.exists() else []
    unexpected_network = [row for row in refusals if row != {
        "event": "socket.getaddrinfo", "destination": "safe-harbor-canary.invalid"
    }]
    summary = {
        "network_refusals": refusals,
        "unexpected_network_attempts": unexpected_network,
        "source_hashes_before": before_hashes,
        "source_hashes_after": after_hashes,
        "source_hash_drift": before_hashes != after_hashes,
        "suites": results,
        "evidence_root": str(evidence_root),
    }
    (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if unexpected_network:
        print("unexpected Python network attempt: see summary", file=sys.stderr)
        return 4
    if summary["source_hash_drift"]:
        print("refusing suite completion: tracked input hash drift", file=sys.stderr)
        return 3
    if any(row.get("harness_drift") for row in results):
        return 3
    if any(row.get("pytest_returncode") is None for row in results):
        return 124
    return 0 if all(int(row.get("pytest_returncode", 124)) == 0 for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
