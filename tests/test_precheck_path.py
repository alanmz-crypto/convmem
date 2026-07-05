"""Tests for scripts/precheck-path.sh."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(script: Path, target: str, *, attempts: Path) -> subprocess.CompletedProcess[str]:
    env = {"ATTEMPTS_FILE": str(attempts)}
    return subprocess.run(
        [str(script), target],
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), **env},
        check=False,
    )


def test_precheck_warns_on_known_failed_path(tmp_path):
    attempts = tmp_path / "attempts.jsonl"
    attempts.write_text(
        '{"obs_id":"obs_001","outcome":"failed","path":"a.py",'
        '"summary":"fail","timestamp":"2026-07-05T12:00:00Z"}\n',
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "precheck-path.sh"
    result = _run(script, "a.py", attempts=attempts)
    assert result.returncode == 0
    assert "WARN" in result.stdout


def test_precheck_silent_on_unknown_path(tmp_path):
    attempts = tmp_path / "attempts.jsonl"
    attempts.write_text(
        '{"obs_id":"obs_001","outcome":"failed","path":"a.py",'
        '"summary":"fail","timestamp":"2026-07-05T12:00:00Z"}\n',
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "precheck-path.sh"
    result = _run(script, "b.py", attempts=attempts)
    assert result.returncode == 0
    assert "WARN" not in result.stdout


def test_precheck_exits_zero_on_missing_attempts_file(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "precheck-path.sh"
    missing = tmp_path / "no-such-attempts.jsonl"
    result = _run(script, "nonexistent.py", attempts=missing)
    assert result.returncode == 0
