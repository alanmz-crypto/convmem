"""Arc #286 V6 production-route proof gap (excluded from T3 PASS gate)."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.fixtures.issue_286_host_isolation import (
    enforce_issue_286_import_guard,
    isolated_codex_sessions_root,
    subprocess_env_for_issue_286,
)

enforce_issue_286_import_guard()

import config
from incremental_jsonl import LIVE_ROUTE_REFUSED_EXIT, source_state_id
from tests.fixtures.issue_286_t3_fixture import worker_config_path
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _write_user_config,
)
from tests.test_issue_286_codex_bootstrap_v2_t3_cli_watch_e2e import _run_index_child


@pytest.mark.v6_proof_gap
def test_real_cli_bootstrap_required_exit91_unreserved_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = isolated_codex_sessions_root()
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    path_key = str(source.resolve())
    table = dict(cfg["index"].get("incremental_jsonl") or {})
    table.update(enabled=True)
    cfg["index"]["incremental_jsonl"] = table
    toml = worker_config_path()
    toml.parent.mkdir(parents=True, exist_ok=True)
    _write_user_config(toml, cfg)
    models = cfg["models"]
    with toml.open("a", encoding="utf-8") as handle:
        handle.write(
            "
[models]
"
            f'summarize_model = "{models["summarize_model"]}"
'
            f'distill_model = "{models["distill_model"]}"
'
            f'embed_model = "{models["embed_model"]}"
'
            f'ollama_host = "{models["ollama_host"]}"
'
        )
    monkeypatch.setattr(config, "CONFIG_PATH", toml)
    processed_path = Path(cfg["index"]["processed_log"])
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    processed_path.write_text(
        json.dumps({"legacy_processed": {"path": path_key, "chunks": 1, "units": 1}}),
        encoding="utf-8",
    )
    source_state = Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / source_state_id(
        path_key, format_id="jsonl_codex_rollout"
    )
    if source_state.exists():
        shutil.rmtree(source_state)
    proc = _run_index_child(path_key, env=subprocess_env_for_issue_286())
    pytest.xfail(
        "V6 proof gap: ROOT retained => isolated route; cannot assert production exit91 without falsifying isolation"
    )
    assert proc.returncode == LIVE_ROUTE_REFUSED_EXIT
