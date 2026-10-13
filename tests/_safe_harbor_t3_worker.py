"""Stdlib-isolated launcher for Safe Harbor T3 implementation tests.

Qualified entry:

    /home/lauer/miniforge3/bin/python -I -S -B tests/_safe_harbor_t3_worker.py run-t3
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve()
TEST_MODULE = ROOT / "tests" / "test_safe_harbor_t3.py"
PYTHON = "/home/lauer/miniforge3/bin/python"
PYTHON_CHILD = [PYTHON, "-s", "-B"]
REQUIRED_UID = 1000
RUN_TIMEOUT_SECONDS = 600.0

def run_t3_launcher() -> int:
    from tests._safe_harbor_t3_backend_worker import (  # pylint: disable=import-outside-toplevel
        build_allowlisted_env,
        _require_isolated,
        _require_uid,
    )
    _require_uid()
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise RuntimeError("bootstrap requires python -I -S -B before run-t3")
    evidence_root = Path(tempfile.mkdtemp(prefix="safe-harbor-t3-impl-", dir="/tmp"))
    fixture_root = evidence_root / "fixture"
    fixture_root.mkdir(parents=True)
    env = build_allowlisted_env(fixture_root, evidence_root)
    os.environ.update(env)
    _require_isolated()
    pytest_cmd = [
        *PYTHON_CHILD,
        "-m",
        "pytest",
        str(TEST_MODULE),
        "-v",
        "--tb=line",
        "-p",
        "no:cacheprovider",
        f"--basetemp={fixture_root / 'pytest-tmp'}",
    ]
    summary: dict[str, object] = {
        "pytest_command": pytest_cmd,
        "uid": os.getuid(),
        "fixture_root": str(fixture_root),
        "evidence_root": str(evidence_root),
        "timeout_seconds": RUN_TIMEOUT_SECONDS,
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
        (evidence_root / "pytest.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        summary["pytest_timed_out"] = True
        (evidence_root / "pytest.log").write_text(
            (exc.stdout or b"").decode(errors="replace") + (exc.stderr or b"").decode(errors="replace"),
            encoding="utf-8",
        )
        summary["pytest_returncode"] = 124
    (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return int(summary.get("pytest_returncode") or 1)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "run-t3":
        print(f"usage: {WORKER.name} run-t3", file=sys.stderr)
        return 2
    return run_t3_launcher()


if __name__ == "__main__":
    raise SystemExit(main())
