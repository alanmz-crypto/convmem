"""Issue #286 Kiro incremental routing and policy gates (design section 9.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
import incremental_jsonl
from incremental_jsonl_kiro_admission import kiro_admitted_live
from tests.incremental_jsonl_helpers import install_fakes, kiro_record, write_source


def _hermetic_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    home = tmp_path / "home"
    config_dir = home / ".config" / "convmem"
    data = home / ".local" / "share" / "convmem"
    config_dir.mkdir(parents=True)
    data.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    monkeypatch.setenv("CONVMEM_CONFIG", str(config_dir / "config.toml"))
    monkeypatch.setenv("CONVMEM_INCREMENTAL_ROOT", str(data / "incremental-jsonl"))
    return {"home": home, "config_dir": config_dir, "data": data}


def _write_config(path: Path, *, live_sources: list[str], with_policy: bool) -> None:
    policy = ""
    if with_policy:
        policy = """
[index.incremental_jsonl.kiro_session]
max_source_bytes = 268435456
max_transform_chunks_per_run = 20
allow_full_rebuild = false
"""
    sources = "\n".join(f'live_sources = ["{source}"]' for source in live_sources) or "live_sources = []"
    path.write_text(
        f"""
[index]
chroma_dir = "{path.parent / 'chroma'}"
processed_log = "{path.parent / 'processed.json'}"
units_export = "{path.parent / 'units.jsonl'}"

[index.incremental_jsonl]
enabled = true
state_dir = "{path.parent / 'incremental-state'}"
embed_dimension = 8
{sources}
{policy}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_selected_kiro_requires_exact_live_source_not_time_admission(tmp_path: Path) -> None:
    source = tmp_path / "sess_a" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_bytes(kiro_record(0))
    (source.parent / "session.json").write_text(
        json.dumps({"id": "sess_a", "workspacePaths": [str(tmp_path / "ws")]}),
        encoding="utf-8",
    )
    other = tmp_path / "sess_b" / "messages.jsonl"
    other.parent.mkdir(parents=True)
    other.write_bytes(kiro_record(1))
    (other.parent / "session.json").write_text(
        json.dumps({"id": "sess_b", "workspacePaths": [str(tmp_path / "ws")]}),
        encoding="utf-8",
    )
    assert not kiro_admitted_live(
        production_boundary=True,
        path_key=str(other.resolve()),
        live_sources=(str(source.resolve()),),
        detected_format="jsonl_kiro_session",
        policy=object(),  # type: ignore[arg-type]
    )


def test_missing_kiro_policy_refuses_before_route(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    source = write_source(tmp_path, 4)
    cfg = {
        "index": {
            "chroma_dir": str(tmp_path / "chroma"),
            "processed_log": str(tmp_path / "processed.json"),
            "units_export": str(tmp_path / "units.jsonl"),
            "incremental_jsonl": {
                "enabled": True,
                "state_dir": str(tmp_path / "incremental-jsonl"),
                "live_sources": [str(source.resolve())],
                "embed_dimension": 8,
                "kiro_session": {"allow_full_rebuild": True},
            },
        }
    }
    with pytest.raises(config.IncrementalJsonlConfigError, match="kiro_rebuild_forbidden"):
        config.incremental_jsonl_settings(cfg)
    cfg["index"]["incremental_jsonl"].pop("kiro_session")
    # test_config reloads config; resolve the class held by the raising module.
    with pytest.raises(incremental_jsonl.IncrementalJsonlConfigError, match="kiro_policy_required"):
        incremental_jsonl.maybe_route_incremental(
            cfg=cfg,
            idx=cfg["index"],
            path=str(source),
            path_key=str(source.resolve()),
            file_hash="hash",
            processed={},
            models={},
            tool="kiro",
            units_export=None,
            chunk_size=4,
            overlap=0,
            min_confidence=0.6,
            force_reindex=False,
            supersede_on_reindex=False,
            verbose=False,
            detected_format="jsonl_kiro_session",
        )


def test_isolated_kiro_uses_transform_v2_descriptor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fakes(monkeypatch)
    from tests.incremental_jsonl_helpers import isolated_env

    boundary, env = isolated_env(tmp_path)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    source = write_source(boundary.root, 6)
    coord = incremental_jsonl.IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    )
    assert coord.transform_v2 is True
    assert coord.transform_descriptor is not None
    assert coord.codex_admitted_live is False
    assert coord.kiro_admitted_live is False

# ref: ../incremental_jsonl.py, ./test_config.py — exception identity after config reload
