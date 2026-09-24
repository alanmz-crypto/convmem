"""Baseline-to-source edit allowlist checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from constants import (  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
    CODE_BASELINE_SHA,
    EDIT_ALLOWLIST_EXACT,
    EDIT_ALLOWLIST_PREFIXES,
    M11_CONTROL_PLANE_INPUTS,
    M11_REVIEWED_OVERLAY_SHA,
    SCHEMA_ALLOWLIST,
)

# Architecture §18.8 exact closed control-plane set — independent of constants so an
# expanded/mutated M11_CONTROL_PLANE_INPUTS fails closed as extra-classified.
_M11_CONTROL_PLANE_EXACT = frozenset(
    {
        "docs/plans/ARCHITECTURE-openclaw-convmem-integration.md",
        "docs/plans/EXECUTION-openclaw-convmem-integration.md",
        "docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md",
        "docs/plans/STATUS-openclaw-convmem-integration.md",
    }
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


def _resolve_commit(repo: Path, sha: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", f"{sha}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
        close_fds=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise SystemExit(f"control_plane_unavailable_commit:{sha}")
    return proc.stdout.strip()


def _git_tree_entry(repo: Path, commit: str, path: str) -> tuple[str, str, str]:
    """Return (mode, type, object_id) for an exact path; fail closed otherwise."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", commit, "--", path],
            check=False,
            capture_output=True,
            text=True,
            close_fds=True,
        )
    except OSError as exc:
        raise SystemExit(f"control_plane_unreadable:{path}") from exc
    if proc.returncode != 0:
        raise SystemExit(f"control_plane_unreadable:{path}")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise SystemExit(f"control_plane_missing:{path}")
    if len(lines) != 1:
        raise SystemExit(f"control_plane_malformed:{path}")
    try:
        meta, name = lines[0].split("	", 1)
    except ValueError as exc:
        raise SystemExit(f"control_plane_malformed:{path}") from exc
    if name != path:
        raise SystemExit(f"control_plane_malformed:{path}")
    parts = meta.split()
    if len(parts) != 3:
        raise SystemExit(f"control_plane_malformed:{path}")
    mode, typ, oid = parts
    if typ != "blob":
        raise SystemExit(f"control_plane_non_blob:{path}")
    if mode != "100644":
        raise SystemExit(f"control_plane_bad_mode:{path}")
    if len(oid) != 40 or any(c not in "0123456789abcdef" for c in oid):
        raise SystemExit(f"control_plane_malformed:{path}")
    return mode, typ, oid


def assert_allowlist(repo: Path, source_commit: str) -> list[str]:
    # D: complete sorted tracked baseline..source path delta.
    delta = sorted(changed_paths(repo, source_commit))

    if M11_CONTROL_PLANE_INPUTS != _M11_CONTROL_PLANE_EXACT:
        raise SystemExit(
            "control_plane_extra_classified:"
            + ",".join(sorted(M11_CONTROL_PLANE_INPUTS ^ _M11_CONTROL_PLANE_EXACT))
        )

    missing = sorted(path for path in _M11_CONTROL_PLANE_EXACT if path not in set(delta))
    if missing:
        raise SystemExit("control_plane_missing:" + ",".join(missing))

    overlay = _resolve_commit(repo, M11_REVIEWED_OVERLAY_SHA)
    source = _resolve_commit(repo, source_commit)

    for path in sorted(_M11_CONTROL_PLANE_EXACT):
        source_entry = _git_tree_entry(repo, source, path)
        overlay_entry = _git_tree_entry(repo, overlay, path)
        if source_entry != overlay_entry:
            raise SystemExit(f"control_plane_mismatch:{path}")

    # P = D - C; product allowlist and Gate-W apply only to P.
    product = [path for path in delta if path not in _M11_CONTROL_PLANE_EXACT]
    forbidden = [p for p in product if not path_allowed(p)]
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
    protected = [p for p in product if p in gate_w]
    if protected:
        raise SystemExit("gate_w_forbidden_change:" + ",".join(protected))
    return product
