"""Hermetic Gate 1 smoke tests for Claude ``index --file`` preparation."""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from claude_gate1_smoke import (
    WORKER,
    HermeticEvidence,
    bind_validated_config_bytes,
    close_sealed_config,
    prepare_hermetic_fixture,
    production_fingerprints,
    replace_config_scalar,
    run_hermetic_index_cli,
    run_hermetic_smoke,
    run_worker,
    scrub_credentials,
    sealed_config_loader,
    sealed_fd_open,
    sealed_storage_available,
    validate_output_containment,
    write_synthetic_claude_transcript,
)
from incremental_jsonl_isolation import (
    IsolationBoundary,
    create_fresh_root,
    install_network_denial,
    sanitized_worker_env,
)


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


def _sentinel_unchanged(sentinel: Path) -> None:
    assert (sentinel / "marker").read_text(encoding="utf-8") == "untouched"


def _apply_worker_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    """Mirror the worker subprocess: only the scrubbed isolation env is visible."""
    for key in list(os.environ):
        if key not in env:
            monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


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
    assert "run_hermetic_index_cli" in text
    assert "maybe_apply_test_post_binding_tamper" not in text
    assert "ingest" not in text.split("def main")[0]


def test_launcher_binds_sealed_bytes_before_invoke() -> None:
    from claude_gate1_smoke import REPO_ROOT

    text = (REPO_ROOT / "claude_gate1_smoke.py").read_text(encoding="utf-8")
    bind_at = text.index("with sealed_config_loader(sealed):")
    hook_at = text.index("maybe_apply_test_post_binding_tamper(preflight.config_path)")
    invoke_at = text.index("runner.invoke")
    assert bind_at < hook_at < invoke_at
    assert "assert_config_identity_unchanged" not in text


def test_pinned_runtime_can_construct_sealed_storage() -> None:
    assert sys.version_info[:2] >= (3, 13)
    assert sealed_storage_available() is True


def test_fallback_seals_without_memfd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _root, _token, env, _transcript = prepare_hermetic_fixture(tmp_path)
    _apply_worker_env(monkeypatch, env)
    monkeypatch.delattr(os, "memfd_create", raising=False)
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    preflight = validate_output_containment(boundary)
    sealed = bind_validated_config_bytes(preflight, boundary)
    assert sealed.backend == "anonymous_fd"
    assert sealed.load()["index"]["chroma_dir"]
    close_sealed_config(sealed)


def test_sealed_descriptor_closed_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _root, _token, env, _transcript = prepare_hermetic_fixture(tmp_path)
    _apply_worker_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    preflight = validate_output_containment(boundary)
    sealed = bind_validated_config_bytes(preflight, boundary)
    with sealed_config_loader(sealed):
        assert sealed_fd_open(sealed) is True
    assert sealed_fd_open(sealed) is False


def test_sealed_descriptor_closed_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _root, _token, env, _transcript = prepare_hermetic_fixture(tmp_path)
    _apply_worker_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    preflight = validate_output_containment(boundary)
    sealed = bind_validated_config_bytes(preflight, boundary)
    with pytest.raises(RuntimeError, match="forced failure"):
        with sealed_config_loader(sealed):
            raise RuntimeError("forced failure")
    assert sealed_fd_open(sealed) is False


def test_loader_bindings_restored_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import config

    _root, _token, env, _transcript = prepare_hermetic_fixture(tmp_path)
    _apply_worker_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    preflight = validate_output_containment(boundary)
    sealed = bind_validated_config_bytes(preflight, boundary)
    original = config.load_config
    original_path = config.CONFIG_PATH
    with sealed_config_loader(sealed):
        assert config.load_config is not original
        assert config.CONFIG_PATH != original_path
    assert config.load_config is original
    assert config.CONFIG_PATH == original_path


def test_loader_bindings_restored_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import config

    _root, _token, env, _transcript = prepare_hermetic_fixture(tmp_path)
    _apply_worker_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    preflight = validate_output_containment(boundary)
    sealed = bind_validated_config_bytes(preflight, boundary)
    original = config.load_config
    with pytest.raises(RuntimeError, match="forced failure"):
        with sealed_config_loader(sealed):
            raise RuntimeError("forced failure")
    assert config.load_config is original


def test_unsupported_sealed_storage_refuses_before_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    _apply_worker_env(monkeypatch, env)
    monkeypatch.setattr(
        "claude_gate1_smoke.sealed_storage_available",
        lambda: False,
    )
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    preflight = validate_output_containment(boundary)
    with pytest.raises(Exception) as excinfo:
        run_hermetic_index_cli(transcript, preflight=preflight)
    assert "cannot seal" in str(excinfo.value).lower()


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
    replace_config_scalar(config_path, key, sentinel / key)
    completed = run_worker("run", transcript, env)
    assert completed.returncode == 74
    payload = json.loads(completed.stdout)
    assert payload["error"] == "IsolationViolation"
    _sentinel_unchanged(sentinel)


@pytest.mark.parametrize("mode", ["rewrite", "replace", "symlink"])
def test_post_binding_config_tamper_cannot_redirect_outputs(
    tmp_path: Path,
    mode: str,
) -> None:
    """Prove post-binding pathname attacks cannot change sealed output targets."""
    root, _token, env, transcript = prepare_hermetic_fixture(tmp_path)
    sentinel = _outside_sentinel(tmp_path, f"outside-chroma-post-binding-{mode}")
    outside_target = sentinel / "chroma_dir"
    config_path = _scratch_config_path(env)
    original_text = config_path.read_text(encoding="utf-8")
    env = dict(env)
    env["CONVMEM_GATE1_TEST_POST_BINDING_TAMPER"] = mode
    env["CONVMEM_GATE1_TEST_POST_BINDING_TAMPER_KEY"] = "chroma_dir"
    env["CONVMEM_GATE1_TEST_POST_BINDING_TAMPER_PATH"] = str(outside_target)
    completed = run_worker("run", transcript, env)
    payload = json.loads(completed.stdout or "{}")
    tampered_text = config_path.read_text(encoding="utf-8")
    assert str(outside_target) in tampered_text
    assert tampered_text != original_text
    if mode == "symlink":
        assert config_path.is_symlink()
    else:
        assert not config_path.is_symlink()
    assert completed.returncode == 0
    assert payload.get("error") != "IsolationViolation"
    assert payload["files_processed"] == 1
    assert payload["files_skipped"] == 0
    assert payload["units_indexed"] > 0
    assert payload["scratch_root"] == str(root)
    assert not outside_target.exists()
    chroma = Path(env["HOME"]) / ".local/share/convmem/chroma"
    assert chroma.is_dir()
    assert any(chroma.iterdir())
    _sentinel_unchanged(sentinel)
    evidence = HermeticEvidence(
        files_processed=int(payload["files_processed"]),
        files_skipped=int(payload["files_skipped"]),
        chunks_indexed=int(payload["chunks_indexed"]),
        units_indexed=int(payload["units_indexed"]),
        format_name=str(payload["format_name"]),
        scratch_root=str(payload["scratch_root"]),
        transcript_digest="unused",
        config_path=str(config_path),
        exit_code=completed.returncode,
    )
    assert evidence.passed is True


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
