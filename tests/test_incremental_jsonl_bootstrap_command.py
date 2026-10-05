"""A one-shot bootstrap needs a narrow, owned, reviewable grant file."""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.kiro_session_jsonl import parse_complete_prefix
from tests.incremental_jsonl_helpers import write_source

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-incremental-jsonl.py"


def _read_grant():
    return runpy.run_path(str(SCRIPT), run_name="bootstrap_test")["_read_grant"]


def test_grant_file_binds_exact_source_and_budget(tmp_path: Path) -> None:
    source = tmp_path / "session" / "messages.jsonl"
    grant = {
        "source": str(source),
        "prefix_sha256": "a" * 64,
        "complete_boundary": 42,
        "max_chunks": 3,
        "embed_dimension": 8,
        "backup_snapshot": "verified-snapshot-id",
    }
    grant_path = tmp_path / "grant.json"
    grant_path.write_text(json.dumps(grant), encoding="utf-8")
    grant_path.chmod(0o600)
    assert _read_grant()(grant_path) == grant
    grant_path.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        _read_grant()(grant_path)


def test_grant_rejects_missing_budget_and_symlink(tmp_path: Path) -> None:
    grant_path = tmp_path / "grant.json"
    grant_path.write_text("{}", encoding="utf-8")
    grant_path.chmod(0o600)
    with pytest.raises(ValueError, match="exactly"):
        _read_grant()(grant_path)
    alias = tmp_path / "alias.json"
    alias.symlink_to(grant_path)
    with pytest.raises(ValueError, match="symlink"):
        _read_grant()(alias)


def test_bootstrap_checks_watcher_and_budget_before_coordinator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    namespace = runpy.run_path(str(SCRIPT), run_name="bootstrap_test")
    bootstrap = namespace["bootstrap"]
    globals_ = bootstrap.__globals__
    source = write_source(tmp_path, 4)
    view = parse_complete_prefix(str(source))
    cfg = {"index": {"chunk_size": 2, "chunk_overlap": 0}}
    calls: list[str] = []

    def watcher_check() -> None:
        calls.append("watcher")

    class FakeCoordinator:
        def __init__(self, boundary, path, **kwargs):
            assert boundary == "bounded"
            assert path == source
            assert kwargs["bootstrap_existing"] is True
            assert kwargs["expected_prefix_sha256"] == view.prefix_sha256
            calls.append("coordinator")

        def run(self):
            return SimpleNamespace(
                outcome="committed",
                mode="bootstrap_existing",
                chunks=2,
                units=1,
                counters=SimpleNamespace(as_dict=lambda: {"summarize": 2}),
            )

    monkeypatch.setitem(globals_, "_require_watcher_disabled", watcher_check)
    monkeypatch.setitem(globals_, "load_config", lambda: cfg)
    monkeypatch.setitem(globals_, "ProductionBoundary", lambda *_args, **_kwargs: "bounded")
    monkeypatch.setitem(globals_, "IncrementalJsonlCoordinator", FakeCoordinator)
    grant = {
        "source": str(source),
        "prefix_sha256": view.prefix_sha256,
        "complete_boundary": view.complete_boundary,
        "max_chunks": 1,
        "embed_dimension": 8,
        "backup_snapshot": "verified-snapshot-id",
    }
    with pytest.raises(ValueError, match="chunk cap"):
        bootstrap(grant)
    assert calls == ["watcher"]
    grant["max_chunks"] = 4
    receipt = bootstrap(grant)
    assert calls == ["watcher", "watcher", "coordinator"]
    assert receipt["provider_calls"] == {"summarize": 2}
    assert cfg["index"]["incremental_jsonl"]["live_sources"] == [str(source)]
