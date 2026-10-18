#!/usr/bin/env python3
"""Single-process Arc #286 guarded pytest launcher with outer bwrap envelope.

Host usage (never run raw pytest for issue #286 guarded suites):
  python3 scripts/issue_286_guarded_pytest_launcher.py [pytest args...]

Outer pass captures operator HOME, re-execs inside bwrap; inner pass installs scratch
isolation env before importing pytest or app modules.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTER_ACTIVE_ENV = "CONVMEM_ISSUE_286_OUTER_BWRAP_ACTIVE"


def _repo_on_path() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _capture_operator_home() -> Path:
    _repo_on_path()
    from tests.fixtures.issue_286_real_home_capture import capture_operator_home_now

    return capture_operator_home_now()


def _inner_pytest(argv: list[str]) -> int:
    _repo_on_path()
    os.environ["CONVMEM_ISSUE_286_FORCE_HOST_ISOLATION"] = "1"
    os.environ.setdefault(OUTER_ACTIVE_ENV, "1")
    from tests.fixtures.issue_286_host_isolation import enforce_issue_286_import_guard

    enforce_issue_286_import_guard()
    import pytest

    scratch = Path(os.environ["CONVMEM_INCREMENTAL_ROOT"])
    basetemp = scratch / "pytest-basetemp"
    basetemp.mkdir(parents=True, exist_ok=True)
    return int(pytest.main(["--basetemp", str(basetemp), "-p", "no:cacheprovider", *argv]))


def _outer_bwrap(argv: list[str]) -> int:
    _repo_on_path()
    from tests.issue_286_codex_bootstrap_bwrap import (
        build_issue_286_bwrap_command,
        ensure_probe_source,
        issue_286_bwrap_integration_available,
    )

    if not issue_286_bwrap_integration_available():
        raise SystemExit("issue_286_outer_bwrap_unavailable: bubblewrap user-ns integration required")
    real_home = _capture_operator_home()
    host_scratch = Path(tempfile.mkdtemp(prefix="issue-286-outer-", dir="/tmp"))
    source = ensure_probe_source(host_scratch)
    inner = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--inner",
        *argv,
    ]
    cmd = build_issue_286_bwrap_command(
        inner,
        scratch_root=host_scratch,
        source_path=source,
        repo_root=REPO_ROOT,
    )
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "CONVMEM_TEST_REAL_HOME": str(real_home),
        OUTER_ACTIVE_ENV: "1",
        "CONVMEM_ISSUE_286_FORCE_HOST_ISOLATION": "1",
    }
    proc = subprocess.run(cmd, env=env, cwd=REPO_ROOT, check=False)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--inner", action="store_true")
    args, pytest_argv = parser.parse_known_args()
    if args.inner or os.environ.get(OUTER_ACTIVE_ENV) == "1":
        return _inner_pytest(pytest_argv)
    return _outer_bwrap(pytest_argv)


if __name__ == "__main__":
    raise SystemExit(main())
