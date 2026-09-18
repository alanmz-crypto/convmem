"""Hermetic Gate 1 smoke tests for Claude ``index --file`` preparation."""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_gate1_smoke import (
    WORKER,
    prepare_hermetic_fixture,
    production_fingerprints,
    run_hermetic_smoke,
    run_worker,
    scrub_credentials,
    write_synthetic_claude_transcript,
)
from incremental_jsonl_isolation import create_fresh_root, sanitized_worker_env


def _worker(
    env: dict[str, str],
    command: str,
    target: Path,
) -> dict:
    completed = run_worker(command, target, env)
    payload = json.loads(completed.stdout or "{}")
    payload["returncode"] = completed.returncode
    payload["stderr"] = completed.stderr
    return payload


def test_hermetic_cli_index_passes(tmp_path: Path) -> None:
    root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    before = production_fingerprints()
    payload = _worker(env, "run", transcript)
    after = production_fingerprints()
    assert before == after
    assert payload["returncode"] == 0
    assert payload["files_processed"] == 1
    assert payload["files_skipped"] == 0
    assert payload["units_indexed"] > 0
    assert payload["format_name"] == "jsonl_claude_session"
    assert payload["scratch_root"] == str(root)
    config = Path(payload["config_path"])
    assert config.is_file()
    assert str(root) in str(config)


def test_unsupported_neighbor_is_not_claude_format(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    env = scrub_credentials(sanitized_worker_env(root, token))
    home = Path(env["HOME"])
    neighbor = home / "other" / "cursor-like.jsonl"
    neighbor.parent.mkdir(parents=True)
    neighbor.write_text(
        json.dumps({"role": "user", "content": "not claude"}) + "\n",
        encoding="utf-8",
    )
    payload = _worker(env, "probe", neighbor)
    assert payload["returncode"] == 0
    assert payload["format_name"] is None


def test_production_config_override_rejected(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    env = scrub_credentials(sanitized_worker_env(root, token))
    env["CONVMEM_CONFIG"] = "/home/lauer/.config/convmem/config.toml"
    transcript = write_synthetic_claude_transcript(Path(env["HOME"]))
    completed = run_worker("run", transcript, env)
    assert completed.returncode == 74
    payload = json.loads(completed.stdout)
    assert payload["error"] == "IsolationViolation"
    assert "production configuration override" in payload["detail"]


def test_inherited_credentials_rejected(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    env = scrub_credentials(sanitized_worker_env(root, token))
    env["DEEPSEEK_API_KEY"] = "must-not-enter-worker"
    transcript = write_synthetic_claude_transcript(Path(env["HOME"]))
    completed = run_worker("run", transcript, env)
    assert completed.returncode == 74
    payload = json.loads(completed.stdout)
    assert payload["error"] == "IsolationViolation"
    assert "credential inherited" in payload["detail"]


def test_zero_units_is_not_pass(tmp_path: Path) -> None:
    """Document that units_indexed=0 is FAIL for Gate 1 acceptance."""
    root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    env = dict(env)
    env["CONVMEM_GATE1_FORCE_ZERO_UNITS"] = "1"
    payload = _worker(env, "run", transcript)
    assert payload["files_processed"] == 1
    assert payload["units_indexed"] == 0
    assert not (
        payload["returncode"] == 0
        and payload["files_processed"] == 1
        and payload["units_indexed"] > 0
    )


def test_launcher_entrypoint_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "claude_gate1_smoke.run_hermetic_smoke",
        lambda parent=None: run_hermetic_smoke(parent or tmp_path),
    )
    from claude_gate1_smoke import _main

    assert _main(["run"]) == 0


def test_worker_imports_only_reviewed_modules() -> None:
    text = WORKER.read_text(encoding="utf-8")
    assert "claude_gate1_smoke" in text
    assert "incremental_jsonl_isolation" in text
    assert "ingest" not in text.split("def main")[0]
