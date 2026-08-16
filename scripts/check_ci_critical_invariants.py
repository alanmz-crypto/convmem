#!/usr/bin/env python3
"""Verify each critical-invariant manifest path collects pytest tests.

Collection success is subprocess return code 0 only from:
  python -m pytest --collect-only -q <path>

Human-readable output is diagnostic; exit status is the safety contract.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_MANIFEST = "tests/ci-critical-invariants.txt"
# Direct-file-only grammar: tests/<filename>.py (no nested subdirectories).
_PATH_RE = re.compile(r"^tests/[A-Za-z0-9_.-]+\.py$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_manifest(manifest_path: Path) -> list[str]:
    if not manifest_path.is_file():
        raise SystemExit(f"manifest missing: {manifest_path}")

    entries: list[str] = []
    seen: set[str] = set()
    for line_no, raw in enumerate(manifest_path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-") or line.startswith("/") or "\\" in line:
            raise SystemExit(f"manifest line {line_no}: rejected path/options: {raw!r}")
        if line in {".", ".."} or "/../" in line or line.startswith("../"):
            raise SystemExit(f"manifest line {line_no}: traversal rejected: {raw!r}")
        if not _PATH_RE.fullmatch(line):
            raise SystemExit(
                f"manifest line {line_no}: must match tests/<filename>.py: {raw!r}"
            )
        if line in seen:
            raise SystemExit(f"manifest line {line_no}: duplicate entry: {line}")
        seen.add(line)
        entries.append(line)
    if not entries:
        raise SystemExit(f"manifest empty after parsing: {manifest_path}")
    return entries


def _validate_target(repo_root: Path, rel_path: str) -> Path:
    tests_root = (repo_root / "tests").resolve()
    candidate = (repo_root / rel_path).resolve()
    try:
        under_tests = candidate.is_relative_to(tests_root)
    except AttributeError:
        under_tests = str(candidate).startswith(str(tests_root) + os.sep)
    if not under_tests:
        raise SystemExit(f"path escapes tests/: {rel_path}")
    if not candidate.is_file():
        raise SystemExit(f"manifest path is not a regular file: {rel_path}")
    return candidate


def _collect_one(repo_root: Path, rel_path: str, env: dict[str, str]) -> int:
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q", rel_path]
    print(f"collect: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", flush=True)
    print(f"exit code: {proc.returncode}", flush=True)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check CI critical invariant manifest.")
    parser.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        help="Repository-relative manifest path (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path

    entries = _parse_manifest(manifest_path)
    env = os.environ.copy()

    failures: list[str] = []
    for rel_path in entries:
        _validate_target(repo_root, rel_path)
        code = _collect_one(repo_root, rel_path, env)
        if code != 0:
            failures.append(f"{rel_path} (exit {code})")

    if failures:
        print("critical invariant collection FAIL:", flush=True)
        for item in failures:
            print(f"  - {item}", flush=True)
        return 1

    print(f"critical invariant collection PASS ({len(entries)} modules)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
