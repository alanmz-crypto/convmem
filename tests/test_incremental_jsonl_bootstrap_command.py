"""A one-shot bootstrap needs a narrow, owned, reviewable grant file."""

# pylint: disable=duplicate-code

from __future__ import annotations

import copy
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from adapters.kiro_session_jsonl import parse_complete_prefix
from bootstrap_safety import operation_identity
from incremental_jsonl import CallCounters, source_state_id
from tests.incremental_jsonl_helpers import write_source

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-incremental-jsonl.py"


def _namespace() -> dict:
    return runpy.run_path(str(SCRIPT), run_name="bootstrap_test")


def _grant(source: Path, *, prefix: str = "a" * 64, boundary: int = 42, max_chunks: int = 3) -> dict:
    body = {
        "source": str(source),
        "prefix_sha256": prefix,
        "complete_boundary": boundary,
        "max_chunks": max_chunks,
        "embed_dimension": 8,
        "backup_snapshot": "e" * 64,
        "runtime_revision": "b" * 40,
        "config_sha256": "c" * 64,
        "transform_fingerprint": "d" * 64,
        "chunk_size": 2,
        "chunk_overlap": 0,
        "min_confidence": 0.6,
        "summarize_provider": "ollama",
        "summarize_model": "summary-model",
        "summarize_base_url": "http://provider.invalid",
        "distill_provider": "deepseek",
        "distill_model": "deepseek-v4-test",
        "distill_base_url": "https://provider.invalid",
        "embedding_provider": "ollama",
        "embedding_model": "embed-model",
        "embedding_base_url": "http://provider.invalid",
        "max_provider_http_attempts": 12,
        "max_recovery_invocations": 1,
    }
    return {"operation_id": operation_identity(body), **body}


def _binding(grant: dict) -> dict:
    return {
        "runtime_revision": grant["runtime_revision"],
        "config_sha256": grant["config_sha256"],
        "chunk_size": grant["chunk_size"],
        "chunk_overlap": grant["chunk_overlap"],
        "min_confidence": grant["min_confidence"],
        "summarize": {
            "provider": grant["summarize_provider"],
            "model": grant["summarize_model"],
            "base_url": grant["summarize_base_url"],
            "fallback": "false",
        },
        "distill": {
            "provider": grant["distill_provider"],
            "model": grant["distill_model"],
            "base_url": grant["distill_base_url"],
            "fallback": "false",
        },
        "embedding": {
            "provider": grant["embedding_provider"],
            "model": grant["embedding_model"],
            "base_url": grant["embedding_base_url"],
            "fallback": "false",
        },
        "transform_fingerprint": grant["transform_fingerprint"],
    }


def test_grant_file_binds_exact_source_budget_and_transform(tmp_path: Path) -> None:
    grant = _grant(tmp_path / "session" / "messages.jsonl")
    grant_path = tmp_path / "grant.json"
    grant_path.write_text(json.dumps(grant), encoding="utf-8")
    grant_path.chmod(0o600)
    assert _namespace()["_read_grant"](grant_path) == grant
    grant_path.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        _namespace()["_read_grant"](grant_path)


def test_grant_rejects_missing_extra_mistyped_identity_and_symlink(tmp_path: Path) -> None:
    grant = _grant(tmp_path / "source.jsonl")
    grant_path = tmp_path / "grant.json"
    for mutate in (
        lambda value: value.pop("max_provider_http_attempts"),
        lambda value: value.update(extra=True),
        lambda value: value.update(max_recovery_invocations=True),
        lambda value: value.update(operation_id="0" * 64),
    ):
        candidate = dict(grant)
        mutate(candidate)
        grant_path.write_text(json.dumps(candidate), encoding="utf-8")
        grant_path.chmod(0o600)
        with pytest.raises(ValueError):
            _namespace()["_read_grant"](grant_path)
    alias = tmp_path / "alias.json"
    alias.symlink_to(grant_path)
    with pytest.raises(ValueError, match="symlink"):
        _namespace()["_read_grant"](alias)


def test_bootstrap_checks_watcher_and_chunk_cap_before_coordinator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    namespace = _namespace()
    bootstrap = namespace["bootstrap"]
    globals_ = bootstrap.__globals__
    source = write_source(tmp_path, 4)
    view = parse_complete_prefix(str(source))
    data = tmp_path / "data"
    cfg = {
        "index": {
            "chroma_dir": str(data / "chroma"),
            "processed_log": str(data / "processed.json"),
            "units_export": str(data / "units.jsonl"),
            "chunk_size": 2,
            "chunk_overlap": 0,
            "incremental_jsonl": {
                "enabled": False,
                "state_dir": str(data / "incremental"),
                "allow_full_rebuild": False,
            },
        },
        "models": {},
        "distill": {"min_confidence": 0.6},
    }
    config_path = tmp_path / "config.toml"
    config_path.write_text("# hermetic\n", encoding="utf-8")
    calls: list[str] = []

    class FakeBoundary:
        def resolve_mutable(self, path, *, label):
            del label
            return Path(path)

    class FakeCoordinator:  # pylint: disable=too-many-instance-attributes
        def __init__(self, boundary, path, **kwargs):
            assert isinstance(boundary, FakeBoundary)
            assert path == source
            assert kwargs["bootstrap_existing"] is True
            assert kwargs["expected_prefix_sha256"] == view.prefix_sha256
            calls.append("coordinator")
            self.cfg = cfg
            self.state_dir = Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / source_state_id(str(source))
            self.paths = {"transaction": self.state_dir / "transaction.json", "prepared": self.state_dir / "prepared"}
            self.attest_dir = data / "writer_attestations"
            self.census_dir = data / "writer_census"
            self.counters = CallCounters(summarize=2, summarize_success=2)
            self.last_result = None
            self.last_evidence = {}

        def require_existing_embedding_dimension(self, expected):
            assert expected == 8
            calls.append("dimension")
            return {"conversation_summaries": 8, "knowledge_units": 8}

        def run(self):
            calls.append("run")
            self.last_result = SimpleNamespace(
                outcome="committed",
                mode="bootstrap_existing",
                chunks=2,
                units=1,
                active_generation="generation",
                exact_suppressed=0,
                semantic_queued=0,
            )
            return self.last_result

    monkeypatch.setitem(globals_, "CONFIG_PATH", config_path)
    monkeypatch.setitem(globals_, "_require_watcher_disabled", lambda: calls.append("watcher"))
    monkeypatch.setitem(globals_, "load_config", lambda: copy.deepcopy(cfg))
    monkeypatch.setitem(globals_, "ProductionBoundary", lambda *_args, **_kwargs: FakeBoundary())
    monkeypatch.setitem(globals_, "IncrementalJsonlCoordinator", FakeCoordinator)

    capped = _grant(
        source,
        prefix=view.prefix_sha256,
        boundary=view.complete_boundary,
        max_chunks=1,
    )
    monkeypatch.setitem(globals_, "_effective_binding", lambda *_args: _binding(capped))
    with pytest.raises(ValueError, match="chunk cap"):
        bootstrap(capped)
    assert calls == ["watcher"]

    calls.clear()
    allowed = _grant(
        source,
        prefix=view.prefix_sha256,
        boundary=view.complete_boundary,
        max_chunks=4,
    )
    monkeypatch.setitem(globals_, "_effective_binding", lambda *_args: _binding(allowed))
    receipt = bootstrap(allowed)
    assert calls == ["watcher", "coordinator", "dimension", "run"]
    assert receipt["outcome"] == "committed"
    assert receipt["logical_attempts"]["summarize"] == 2
    assert receipt["recovery_remains_available"] is False
