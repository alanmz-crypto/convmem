"""Stdlib-only Safe Harbor T3 test bootstrap (no pytest / project imports)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _fixture_root_from_env() -> Path | None:
    raw = os.environ.get("SAFE_HARBOR_T3_FIXTURE_ROOT", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve(strict=False)


def _path_under_fixture(path: Path, fixture_root: Path) -> bool:
    try:
        resolved = path.expanduser().resolve(strict=False)
        root = fixture_root.resolve(strict=False)
    except OSError:
        return False
    if resolved == root or root in resolved.parents:
        return True
    return False


def validate_chroma_argv_path(raw: str, *, fixture_root: Path | None) -> Path:
    """Reject escape, dangling symlinks, and paths outside the fixture root when configured."""
    if not raw or not isinstance(raw, str):
        raise RuntimeError("refusing empty chroma path argument")
    path = Path(raw).expanduser()
    parts = path.parts
    if ".." in parts:
        raise RuntimeError(f"refusing path with parent traversal: {raw}")
    for part in path.parts:
        if part == "..":
            raise RuntimeError(f"refusing path with parent traversal: {raw}")
    cursor = path
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise RuntimeError(f"refusing symlink component in path: {cursor}")
        cursor = cursor.parent
    resolved = path.resolve(strict=False)
    if fixture_root is not None and not _path_under_fixture(resolved, fixture_root):
        raise RuntimeError(f"refusing chroma path outside fixture root: {resolved}")
    return resolved


def require_t3_bootstrap() -> None:
    """Exit the process if T3 launcher isolation was not established."""
    if os.environ.get("SAFE_HARBOR_T3_BOOTSTRAPPED") != "1":
        msg = (
            "refusing import without launcher isolation: run "
            "/home/lauer/miniforge3/bin/python -I -S -B tests/_safe_harbor_t3_worker.py run-suite"
        )
        print(msg, file=sys.stderr)
        raise SystemExit(5)
    if os.getuid() != 1000:
        print("refusing non-owner uid for Safe Harbor T3 tests", file=sys.stderr)
        raise SystemExit(5)
    # The parent requires -I -S -B before building an environment allowlist.
    # Package-using children deliberately use -s -B under that clean environment.
    if not (sys.flags.no_user_site and sys.dont_write_bytecode):
        raise RuntimeError("fixture child requires python -s -B")
    from tests._safe_harbor_t3_backend_worker import _require_isolated

    _require_isolated()
