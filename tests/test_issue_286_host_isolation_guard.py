"""Production-path guard for Arc #286 host isolation (no operator path writes)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.issue_286_host_isolation import (
    INSTALLED_ENV,
    ISOLATION_MODE_VALUE,
    ISOLATION_ROOT_ENV,
    ISOLATION_TOKEN_ENV,
    approved_scratch_root,
    capture_real_home,
    enforce_issue_286_import_guard,
    path_must_live_under_scratch,
    production_path_prefixes,
    resolves_under_production_path,
    subprocess_env_for_issue_286,
    subprocess_negative_must_reject_operator_home,
    validate_derived_live_paths,
    validate_isolated_env,
)

enforce_issue_286_import_guard()


def test_guard_home_differs_from_operator_real_home() -> None:
    real_home = capture_real_home()
    assert Path(os.environ["HOME"]).resolve() != real_home


def test_guard_required_env_under_scratch_and_not_production() -> None:
    real_home = capture_real_home()
    scratch = approved_scratch_root()
    keys = (
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "TMPDIR",
        "TEMP",
        "TMP",
        ISOLATION_ROOT_ENV,
    )
    for key in keys:
        value = os.environ[key]
        path_must_live_under_scratch(value, scratch, label=key)
        if key in {"HOME", "TMPDIR", ISOLATION_ROOT_ENV}:
            assert not resolves_under_production_path(value, real_home=real_home)


def test_guard_isolation_token_and_mode_are_not_paths() -> None:
    scratch = approved_scratch_root()
    token = os.environ[ISOLATION_TOKEN_ENV]
    assert token
    assert os.environ["CONVMEM_INCREMENTAL_MODE"] == ISOLATION_MODE_VALUE
    marker = scratch / ".convmem-jsonl-production-root"
    assert marker.read_text(encoding="ascii").strip() == token.strip()


def test_guard_derived_live_paths_under_scratch() -> None:
    real_home = capture_real_home()
    scratch = approved_scratch_root()
    validate_derived_live_paths(scratch=scratch, real_home=real_home)


def test_guard_config_module_path_not_production() -> None:
    import config

    real_home = capture_real_home()
    scratch = approved_scratch_root()
    path_must_live_under_scratch(config.CONFIG_PATH, scratch, label="config.CONFIG_PATH")
    assert not resolves_under_production_path(config.CONFIG_PATH, real_home=real_home)


def test_guard_all_protected_prefixes_resolve_as_production() -> None:
    real_home = capture_real_home()
    prefixes = production_path_prefixes(real_home)
    assert len(prefixes) == 4
    for prefix in prefixes:
        assert resolves_under_production_path(prefix, real_home=real_home)


def test_guard_protected_prefix_negative_controls_reject_scratch_violation() -> None:
    real_home = capture_real_home()
    scratch = approved_scratch_root()
    for prefix in production_path_prefixes(real_home):
        with pytest.raises(RuntimeError, match=r"issue_286_scratch_violation"):
            path_must_live_under_scratch(prefix, scratch, label="production.prefix")


def test_guard_child_env_inherits_isolated_home_and_root() -> None:
    real_home = capture_real_home()
    child = subprocess_env_for_issue_286()
    assert Path(child["HOME"]).resolve() != real_home
    assert child[ISOLATION_ROOT_ENV] == os.environ[ISOLATION_ROOT_ENV]
    assert child[ISOLATION_TOKEN_ENV] == os.environ[ISOLATION_TOKEN_ENV]


def test_guard_subprocess_inherited_env_matches_isolated_home() -> None:
    child = subprocess_env_for_issue_286()
    probe = subprocess.run(
        [sys.executable, "-c", "import os; print(os.environ['HOME'])"],
        env=child,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert Path(probe.stdout.strip()).resolve() == Path(child["HOME"]).resolve()
    assert probe.stdout.strip() != str(capture_real_home())


def test_guard_subprocess_negative_rejects_operator_home() -> None:
    subprocess_negative_must_reject_operator_home()


def test_guard_child_env_rejects_operator_home_in_extra() -> None:
    real_home = capture_real_home()
    with pytest.raises(RuntimeError, match=r"issue_286_child_env_leak|issue_286_production_path_leak|issue_286_scratch_violation"):
        subprocess_env_for_issue_286(extra={"HOME": str(real_home)})


def test_guard_forged_token_rejected() -> None:
    with pytest.raises(RuntimeError, match=r"issue_286_scratch_token_mismatch|forged|stale"):
        subprocess_env_for_issue_286(extra={ISOLATION_TOKEN_ENV: "forged-token-value"})


def test_guard_missing_incremental_root_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match=r"issue_286_child_env_missing|issue_286_env_missing|issue_286_env_not_absolute",
    ):
        subprocess_env_for_issue_286(extra={ISOLATION_ROOT_ENV: ""})


def test_guard_symlink_escape_inside_scratch_rejected(tmp_path: Path) -> None:
    scratch = approved_scratch_root()
    trap = scratch / "symlink-trap"
    outside = capture_real_home() / ".config"
    try:
        trap.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(RuntimeError, match=r"issue_286_scratch_violation"):
        path_must_live_under_scratch(trap / "convmem" / "config.toml", scratch, label="symlink.escape")


def test_guard_broad_pytest_argv_triggers_installed_isolation() -> None:
    assert os.environ.get(INSTALLED_ENV) == "1"
    validate_isolated_env(strict=True)
