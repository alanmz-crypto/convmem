"""T4 fixtures must stay local when pytest collects the complete suite."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_t4_modules_do_not_register_global_plugins():
    for path in ROOT.glob("tests/test_safe_harbor_t4*.py"):
        tree = ast.parse(path.read_text())
        assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
        assert not any(
            isinstance(target, ast.Name) and target.id == "pytest_plugins"
            for node in assignments for target in node.targets
        ), path


def test_full_collection_keeps_unrelated_home_checks_intact(tmp_path):
    from tests._safe_harbor_bootstrap import require_t3_bootstrap
    require_t3_bootstrap()
    fixture = Path(os.environ["SAFE_HARBOR_T3_FIXTURE_ROOT"]).resolve(strict=True)
    assert fixture in tmp_path.resolve().parents
    names = (
        "test_is_live_watch_db_copilot_session_db",
        "test_is_live_watch_db_cursor_store",
        "test_scratch_root_ancestor_of_production_fail_closed",
        "test_scratch_root_production_fail_closed",
    )
    # Full collection is required: a minimal file selection did not reproduce
    # the old global-plugin leak. Only these four cases execute; no recursion.
    result = subprocess.run(
        [sys.executable, "-s", "-B", "-m", "pytest", "-q", "-k", " or ".join(names),
         "-p", "no:cacheprovider", "--basetemp=" + str(tmp_path / "nested")],
        cwd=ROOT, env=dict(os.environ), capture_output=True, text=True,
        timeout=120, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed" in result.stdout, result.stdout
