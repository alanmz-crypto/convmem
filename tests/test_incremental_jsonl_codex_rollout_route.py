"""Production Codex rollout admission route (hermetic, fake providers)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

import incremental_jsonl
from incremental_jsonl_codex_admission import make_uuid7
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import codex_rollout_record, install_fakes
from tests.test_incremental_jsonl_codex_admission import _meta_for, _write_rollout
import watch
from watch import CircuitBreakerState, parse_live_route_refused


def _sessions_root(tmp_path: Path) -> Path:
    return (tmp_path / ".codex" / "sessions").resolve()


def _write_user_config(path: Path, cfg: dict, *, allow_full_rebuild: bool = False) -> None:
    index = cfg["index"]
    admission = index["incremental_jsonl"]["codex_rollout_admission"]
    rebuild_line = (
        f"allow_full_rebuild = {'true' if allow_full_rebuild else 'false'}\n"
    )
    live_sources = index["incremental_jsonl"].get("live_sources") or []
    live_sources_line = "live_sources = [" + ", ".join(f'"{src}"' for src in live_sources) + "]"
    path.write_text(
        "\n".join(
            [
                "[index]",
                f'chroma_dir = "{index["chroma_dir"]}"',
                f'processed_log = "{index["processed_log"]}"',
                f'units_export = "{index["units_export"]}"',
                f"chunk_size = {index.get('chunk_size', 4)}",
                f"chunk_overlap = {index.get('chunk_overlap', 0)}",
                "",
                "[index.incremental_jsonl]",
                "enabled = true",
                rebuild_line.rstrip(),
                f'state_dir = "{index["incremental_jsonl"]["state_dir"]}"',
                f"embed_dimension = {index['incremental_jsonl']['embed_dimension']}",
                live_sources_line,
                "",
                "[index.incremental_jsonl.codex_rollout_admission]",
                f'root = "{admission["root"]}"',
                f'admitted_after = "{admission["admitted_after"]}"',
                f"max_transform_chunks_per_run = {admission['max_transform_chunks_per_run']}",
                f"max_source_bytes = {admission['max_source_bytes']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _production_cfg(
    tmp_path: Path,
    sessions_root: Path,
    admitted: datetime,
    *,
    allow_full_rebuild: bool = False,
) -> dict:
    data = tmp_path / "data"
    return {
        "models": {
            "summarize_model": "fake",
            "distill_model": "fake",
            "embed_model": "fake",
            "ollama_host": "http://127.0.0.1:9",
        },
        "index": {
            "chroma_dir": str(data / "chroma"),
            "processed_log": str(data / "processed.json"),
            "units_export": str(data / "knowledge_units.jsonl"),
            "chunk_size": 4,
            "chunk_overlap": 0,
            "incremental_jsonl": {
                "enabled": True,
                "state_dir": str(data / "incremental-jsonl"),
                "live_sources": [],
                "embed_dimension": 8,
                "allow_full_rebuild": allow_full_rebuild,
                "codex_rollout_admission": {
                    "root": str(sessions_root),
                    "admitted_after": admitted.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "max_transform_chunks_per_run": 20,
                    "max_source_bytes": 256 * 1024 * 1024,
                },
            },
        }
    }


def _admitted_rollout(sessions_root: Path, admitted: datetime) -> Path:
    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 10_000)
    uid = str(uid_obj)
    uuid_dt = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc)
    local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    return _write_rollout(
        sessions_root,
        uid,
        filename_local=local,
        session_meta=_meta_for(uid, uuid_dt),
        extra_lines=8,
    )


def test_non_admitted_rollout_routes_legacy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2099, 1, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    cfg["index"]["incremental_jsonl"]["codex_rollout_admission"]["admitted_after"] = (
        "2099-06-01T00:00:00Z"
    )
    routed = incremental_jsonl.maybe_route_incremental(
        cfg=cfg,
        idx=cfg["index"],
        path=str(source),
        path_key=str(source),
        file_hash="hash-a",
        processed={},
        models={},
        tool="codex",
        units_export=None,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        force_reindex=False,
        supersede_on_reindex=False,
        verbose=False,
        detected_format="jsonl_codex_rollout",
    )
    assert routed is None


def test_admitted_lifecycle_zero_provider_on_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    first = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    ).run()
    assert first.outcome == "committed"
    assert first.counters.summarize > 0
    baseline = first.counters.summarize
    with source.open("ab") as handle:
        handle.write(codex_rollout_record(8))
    second = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    ).run()
    assert second.outcome == "committed"
    assert second.counters.summarize < baseline
    third = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    ).run()
    assert third.outcome == "unchanged"
    assert third.counters.total == 0


def test_bootstrap_required_refusal_quarantines_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    processed = {"legacy": {"path": str(source)}}
    with pytest.raises(incremental_jsonl.IncrementalJsonlError, match="bootstrap_required"):
        incremental_jsonl.maybe_route_incremental(
            cfg=cfg,
            idx=cfg["index"],
            path=str(source),
            path_key=str(source),
            file_hash="new-hash",
            processed=processed,
            models={},
            tool="codex",
            units_export=None,
            chunk_size=4,
            overlap=0,
            min_confidence=0.6,
            force_reindex=False,
            supersede_on_reindex=False,
            verbose=False,
            detected_format="jsonl_codex_rollout",
        )
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    refused = parse_live_route_refused("live_route_refused:bootstrap_required\n")
    assert refused is not None
    from adapters.jsonl_prefix import complete_prefix_digest_for_path

    prefix_digest = complete_prefix_digest_for_path(str(source))
    breaker.record_refusal(str(source), outcome="bootstrap_required", prefix_digest=prefix_digest)
    calls: list[str] = []

    def fake_flush(path: str, **_kwargs):  # noqa: ANN003
        calls.append(path)
        raise RuntimeError(f"live_route_refused:bootstrap_required:{prefix_digest}")

    monkeypatch.setattr(watch, "flush_path", fake_flush)
    for _ in range(3):
        watch._process_ready_path(
            str(source),
            cfg=cfg,
            breaker=breaker,
            verbose=False,
        )
    assert len(calls) == 0


def test_transform_chunk_cap_refuses_without_provider_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg["index"]["incremental_jsonl"]["codex_rollout_admission"]["max_transform_chunks_per_run"] = 1
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    result = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=2,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    ).run()
    assert result.outcome == "transform_chunk_cap"
    assert result.counters.total == 0
