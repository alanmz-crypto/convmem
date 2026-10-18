"""T3 two-process race matrix with parent oracle (Arc #286)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from bootstrap_codex_v2_authority import CodexBootstrapV2AuthorityError, claim_initial_authority, load_authority
from bootstrap_codex_v3_preparation_lease import SOURCE_WRITER_BUSY_CODE
from bootstrap_codex_v3_writer_coordination import BootstrapWriterCoordinationError, recheck_reservation_before_commit
from bootstrap_codex_v3_writer_coordination import source_state_dir_for_path
from ingest import commit_processed_index_entry
from tests.fixtures.issue_286_t2_owner_context import t2_owner_context
from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant

CHILD = Path(__file__).with_name("issue_286_codex_bootstrap_t3_race_child.py")
EMPTY = "{}" + chr(10)


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # noqa: ARG001
    import config

    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    grant_path = tmp_path / "grant.json"
    grant_path.write_text(json.dumps(grant), encoding="utf-8")
    state_dir = source_state_dir_for_path(cfg, source)
    toml_path = tmp_path / "config.toml"
    monkeypatch.setenv("CONVMEM_CONFIG", str(toml_path))
    monkeypatch.setattr(config, "CONFIG_PATH", toml_path)
    return source, cfg, grant, cfg_path, grant_path, state_dir


def test_race_legacy_prep_before_bootstrap_claim_parent_oracle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import threading
    import time

    from bootstrap_codex_v3_preparation_lease import legacy_shared_preparation_lease

    source, cfg, grant, _cfg_path, _grant_path, state_dir = _fixture(tmp_path, monkeypatch)
    ready = threading.Event()

    def hold_legacy() -> None:
        with legacy_shared_preparation_lease(state_dir):
            ready.set()
            time.sleep(1.0)

    thread = threading.Thread(target=hold_legacy)
    thread.start()
    assert ready.wait(timeout=2.0)
    with t2_owner_context(state_dir):
        with pytest.raises(CodexBootstrapV2AuthorityError) as exc:
            claim_initial_authority(state_dir, grant)
        assert SOURCE_WRITER_BUSY_CODE in str(exc.value)
    thread.join(timeout=5)
    assert load_authority(state_dir) is None


def test_race_bootstrap_reservation_before_legacy_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    source, cfg, grant, cfg_path, grant_path, state_dir = _fixture(tmp_path, monkeypatch)
    barrier = tmp_path / "barrier"
    with t2_owner_context(state_dir):
        claim_initial_authority(state_dir, grant)
    barrier.write_text("ready", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(CHILD), "recheck_commit", str(cfg_path), str(source), str(grant_path), str(barrier)],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode != 0


def test_race_reservation_before_stale_legacy_recheck(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, grant, _cfg_path, _grant_path, state_dir = _fixture(tmp_path, monkeypatch)
    with t2_owner_context(state_dir):
        claim_initial_authority(state_dir, grant)
    assert load_authority(state_dir) is not None
    with pytest.raises(BootstrapWriterCoordinationError):
        recheck_reservation_before_commit(cfg, source)


def test_disjoint_source_processed_while_reservation_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_a, cfg, grant, _cp, _gp, state_dir = _fixture(tmp_path, monkeypatch)
    source_b = tmp_path / "sessions" / "other-rollout.jsonl"
    source_b.parent.mkdir(parents=True, exist_ok=True)
    source_b.write_text(EMPTY, encoding="utf-8")
    with t2_owner_context(state_dir):
        claim_initial_authority(state_dir, grant)
    processed_path = cfg["index"]["processed_log"]
    Path(processed_path).parent.mkdir(parents=True, exist_ok=True)
    ok = commit_processed_index_entry(
        processed_path,
        file_hash="b" * 64,
        path_key=str(source_b.resolve()),
        chunks=1,
        units=1,
    )
    assert ok is True
