"""Baseline-to-source edit allowlist checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from constants import (
    CODE_BASELINE_SHA,
    EDIT_ALLOWLIST_EXACT,
    EDIT_ALLOWLIST_PREFIXES,
    SCHEMA_ALLOWLIST,
)


def path_allowed(path: str) -> bool:
    if path in EDIT_ALLOWLIST_EXACT or path in SCHEMA_ALLOWLIST:
        return True
    return any(path.startswith(prefix) for prefix in EDIT_ALLOWLIST_PREFIXES)


def changed_paths(repo: Path, source_commit: str, baseline: str = CODE_BASELINE_SHA) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", f"{baseline}..{source_commit}"],
        check=True,
        capture_output=True,
        text=True,
        close_fds=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def assert_allowlist(repo: Path, source_commit: str) -> list[str]:
    paths = changed_paths(repo, source_commit)
    forbidden = [p for p in paths if not path_allowed(p)]
    if forbidden:
        raise SystemExit("allowlist_violation:" + ",".join(forbidden))
    # Gate W admission schemas stay reject-only even if mistakenly allowlisted.
    # mcp_server.py is an authorized M4/T3 legacy-profile refusal surface.
    gate_w = (
        "schemas/convmem-approved-admission-v1.schema.json",
        "schemas/convmem-admission-intent-v1.schema.json",
        "schemas/convmem-admission-review-v1.schema.json",
        "schemas/convmem-admission-ratification-v1.schema.json",
        "schemas/convmem-admission-event-v1.schema.json",
    )
    protected = [p for p in paths if p in gate_w]
    if protected:
        raise SystemExit("gate_w_forbidden_change:" + ",".join(protected))
    return paths
