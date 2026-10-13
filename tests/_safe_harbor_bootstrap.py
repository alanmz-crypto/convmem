"""Stdlib-only Safe Harbor T3 test bootstrap (no pytest / project imports)."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

EXPECTED_UID_ENV = "SAFE_HARBOR_T3_EXPECTED_UID"
_LAUNCHER_HINT = "python -I -S -B tests/_safe_harbor_t3_worker.py run-suite"
_ROOT = Path(__file__).resolve().parents[1]


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


def refuse_root() -> None:
    uid = os.getuid()
    euid = os.geteuid()
    if uid == 0 or euid == 0:
        raise RuntimeError(f"refusing root uid (uid={uid}, euid={euid})")


def require_parent_bootstrap_flags() -> None:
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise RuntimeError("bootstrap requires python -I -S -B")


def parse_expected_uid(raw: str | None) -> int:
    if raw is None or not str(raw).strip():
        raise RuntimeError(f"refusing missing {EXPECTED_UID_ENV}")
    try:
        value = int(str(raw).strip())
    except ValueError as exc:
        raise RuntimeError(f"refusing non-integer {EXPECTED_UID_ENV}={raw!r}") from exc
    if value <= 0:
        raise RuntimeError(f"refusing non-positive {EXPECTED_UID_ENV}={value}")
    return value


def _assert_process_uid_equals(expected_uid: int) -> int:
    refuse_root()
    if expected_uid <= 0:
        raise RuntimeError(f"refusing non-positive expected uid {expected_uid}")
    uid = os.getuid()
    euid = os.geteuid()
    if uid != expected_uid or euid != expected_uid:
        raise RuntimeError(
            f"refusing uid mismatch (expected {expected_uid}, uid={uid}, euid={euid})"
        )
    return expected_uid


def require_expected_uid_match() -> int:
    """Require inherited expected uid to match actual uid/euid (cooperative boundary)."""
    expected = parse_expected_uid(os.environ.get(EXPECTED_UID_ENV))
    return _assert_process_uid_equals(expected)


def require_explicit_uid_binding(expected_uid: int) -> int:
    """Bind an explicit parent uid to the current process identity before fixture setup."""
    return _assert_process_uid_equals(expected_uid)


def parent_launcher_uid() -> int:
    """Record the non-root parent uid for child environments (launcher modes only)."""
    refuse_root()
    require_parent_bootstrap_flags()
    uid = os.getuid()
    euid = os.geteuid()
    if uid != euid:
        raise RuntimeError(f"refusing setuid mismatch uid={uid} euid={euid}")
    return uid


def with_expected_uid(env: dict[str, str], expected_uid: int) -> dict[str, str]:
    if expected_uid <= 0:
        raise RuntimeError(f"refusing non-positive expected uid {expected_uid}")
    out = dict(env)
    out[EXPECTED_UID_ENV] = str(expected_uid)
    return out


def load_stdlib_module(path: Path, module_name: str) -> ModuleType:
    """Load a stdlib-isolated module by file path (-I entry cannot use package imports)."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_harness_child(
    cmd: list[str],
    *,
    env: dict[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    """Repo-root captured text subprocess for isolated T3 launcher harnesses."""
    # pylint: disable=duplicate-code
    # Keep this one subprocess adapter explicit; older T1 tests spell out the same
    # capture/check contract independently and are outside this harness correction.
    return subprocess.run(
        cmd,
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
# pylint: enable=duplicate-code


def _load_backend_worker_for_isolation() -> object:
    return load_stdlib_module(
        _ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
        "safe_harbor_t3_backend_worker",
    )


def require_t3_bootstrap() -> None:
    """Exit the process if T3 launcher isolation was not established."""
    if os.environ.get("SAFE_HARBOR_T3_BOOTSTRAPPED") != "1":
        msg = (
            "refusing import without launcher isolation: run "
            f"{_LAUNCHER_HINT}"
        )
        print(msg, file=sys.stderr)
        raise SystemExit(5)
    require_expected_uid_match()
    if not (sys.flags.no_user_site and sys.dont_write_bytecode):
        raise RuntimeError("fixture child requires python -s -B")
    backend = _load_backend_worker_for_isolation()
    backend._require_isolated()  # pylint: disable=protected-access  # launcher-only isolation gate


def stdlib_entry_refusal() -> int:
    """Isolated file entry for refusal checks without project package imports."""
    try:
        require_expected_uid_match()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(stdlib_entry_refusal())
