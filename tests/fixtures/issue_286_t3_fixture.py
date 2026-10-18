"""Shared T3 hermetic fixtures (Arc #286)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.fixtures.issue_286_host_isolation import enforce_issue_286_import_guard

enforce_issue_286_import_guard()

import config
from bootstrap_codex_v2_authority import claim_initial_authority
from bootstrap_codex_v3_writer_coordination import source_state_dir_for_path
from tests.fixtures.issue_286_t2_owner_context import t2_owner_context
from tests.test_incremental_jsonl_codex_rollout_route import _write_user_config
from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant

_FAKE_MODELS = {
    "summarize_model": "deterministic-fake",
    "distill_model": "deterministic-fake",
    "embed_model": "deterministic-fake",
    "ollama_host": "",
}


def worker_config_path() -> Path:
    """Config path under isolated layout HOME (never operator ~/.config/convmem)."""
    if os.environ.get("CONVMEM_ISSUE_286_INNER_BWRAP_WORKER") == "1":
        from incremental_jsonl_isolation import _layout

        root = Path(os.environ["CONVMEM_INCREMENTAL_ROOT"]).resolve()
        return _layout(root)["user_config"]
    enforce_issue_286_import_guard()
    from tests.fixtures.issue_286_host_isolation import isolated_default_config_path

    configured = os.environ.get("CONVMEM_CONFIG")
    if configured:
        return Path(configured).expanduser().resolve()
    return isolated_default_config_path()


def _isolated_rollout_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from datetime import datetime, timezone

    from incremental_jsonl_codex_admission import make_uuid7
    from tests.fixtures.issue_286_host_isolation import (
        isolated_codex_sessions_root,
        isolated_layout_home,
    )
    from tests.test_incremental_jsonl_codex_admission import _meta_for, _write_rollout
    from tests.test_incremental_jsonl_codex_rollout_route import _production_cfg

    layout_home = isolated_layout_home()
    monkeypatch.setenv("HOME", str(layout_home))
    sessions = isolated_codex_sessions_root()
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 5)
    uid = str(uid_obj)
    local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    source = _write_rollout(
        sessions,
        uid,
        filename_local=local,
        session_meta=_meta_for(
            uid,
            datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc),
        ),
    )
    cfg = _production_cfg(tmp_path, sessions, admitted)
    from incremental_jsonl_formats import get_format_spec

    spec = get_format_spec("jsonl_codex_rollout")
    view = spec.parse_complete_prefix(str(source))
    return source, cfg, view.prefix_sha256, view.complete_boundary


def t3_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    if os.environ.get("CONVMEM_ISSUE_286_INNER_BWRAP_WORKER") == "1":
        source, cfg, prefix, boundary = _isolated_rollout_source(tmp_path, monkeypatch)
    else:
        source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    toml_path = worker_config_path()
    toml_path.parent.mkdir(parents=True, exist_ok=True)
    _write_user_config(toml_path, cfg)
    models = _FAKE_MODELS
    with toml_path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n[models]\n"
            f'summarize_model = "{models["summarize_model"]}"\n'
            f'distill_model = "{models["distill_model"]}"\n'
            f'embed_model = "{models["embed_model"]}"\n'
            f'ollama_host = "{models["ollama_host"]}"\n'
        )
    monkeypatch.setattr(config, "CONFIG_PATH", toml_path)
    state_dir = source_state_dir_for_path(cfg, source)
    return source, cfg, grant, state_dir


def claim_active_reservation(state_dir: Path, grant: dict) -> None:
    with t2_owner_context(state_dir):
        claim_initial_authority(state_dir, grant)


def idx_dict(cfg: dict) -> dict:
    return cfg["index"]
