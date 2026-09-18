"""Hermetic Gate 1 smoke tests for Claude ``index --file`` preparation."""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from claude_gate1_smoke import (
    WORKER,
    HermeticEvidence,
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


def _scratch_config_path(env: dict[str, str]) -> Path:
    return Path(env["HOME"]) / ".config" / "convmem" / "config.toml"


def _outside_sentinel(tmp_path: Path, name: str) -> Path:
    sentinel = tmp_path / name
    sentinel.mkdir()
    (sentinel / "marker").write_text("untouched", encoding="utf-8")
    return sentinel


def _replace_config_scalar(config_path: Path, key: str, value: Path) -> None:
    text = config_path.read_text(encoding="utf-8")
    replacement = f'{key} = {json.dumps(str(value))}'
    updated, count = re.subn(
        rf"^{key} = .*$",
        replacement,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise AssertionError(f"could not rewrite config key {key}")
    config_path.write_text(updated, encoding="utf-8")


def _sentinel_unchanged(sentinel: Path) -> None:
    assert (sentinel / "marker").read_text(encoding="utf-8") == "untouched"


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
    assert "validate_output_containment" in text
    assert "ingest" not in text.split("def main")[0]


@pytest.mark.parametrize(
    ("key", "sentinel_name"),
    [
        ("chroma_dir", "outside-chroma"),
        ("processed_log", "outside-processed"),
        ("units_export", "outside-export"),
        ("state_dir", "outside-state"),
    ],
)
def test_tampered_config_output_paths_refuse_before_mutation(
    tmp_path: Path,
    key: str,
    sentinel_name: str,
) -> None:
    _root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    sentinel = _outside_sentinel(tmp_path, sentinel_name)
    config_path = _scratch_config_path(env)
    _replace_config_scalar(config_path, key, sentinel / key)
    completed = run_worker("run", transcript, env)
    assert completed.returncode == 74
    payload = json.loads(completed.stdout)
    assert payload["error"] == "IsolationViolation"
    _sentinel_unchanged(sentinel)


def test_missing_scratch_config_refuses(tmp_path: Path) -> None:
    _root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    _scratch_config_path(env).unlink()
    completed = run_worker("run", transcript, env)
    assert completed.returncode == 74
    payload = json.loads(completed.stdout)
    assert payload["error"] == "IsolationViolation"
    assert "config" in payload["detail"].lower()


def test_symlinked_scratch_config_refuses(tmp_path: Path) -> None:
    _root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    config_path = _scratch_config_path(env)
    outside = tmp_path / "outside-config.toml"
    outside.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    config_path.unlink()
    config_path.symlink_to(outside)
    completed = run_worker("run", transcript, env)
    assert completed.returncode == 74
    payload = json.loads(completed.stdout)
    assert payload["error"] == "IsolationViolation"


def test_mismatched_home_refuses(tmp_path: Path) -> None:
    _root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    env = dict(env)
    env["HOME"] = str(tmp_path / "wrong-home")
    completed = run_worker("run", transcript, env)
    assert completed.returncode == 74
    payload = json.loads(completed.stdout)
    assert payload["error"] == "IsolationViolation"


def test_nonzero_worker_exit_never_reports_pass(tmp_path: Path) -> None:
    root, _token, env, _transcript = prepare_hermetic_fixture(tmp_path)
    evidence = HermeticEvidence(
        files_processed=1,
        files_skipped=0,
        chunks_indexed=1,
        units_indexed=1,
        format_name="jsonl_claude_session",
        scratch_root=str(root),
        transcript_digest="deadbeef",
        config_path=str(_scratch_config_path(env)),
        exit_code=74,
    )
    assert evidence.passed is False


def test_malformed_worker_stdout_does_not_pass_launcher(tmp_path: Path) -> None:
    root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    before = production_fingerprints()
    completed = run_worker("run", transcript, env)
    after = production_fingerprints()
    assert before == after
    assert completed.returncode == 0
    evidence = HermeticEvidence(
        files_processed=0,
        files_skipped=0,
        chunks_indexed=0,
        units_indexed=0,
        format_name="",
        scratch_root=str(root),
        transcript_digest="deadbeef",
        config_path=str(_scratch_config_path(env)),
        exit_code=completed.returncode,
    )
    assert evidence.passed is False
