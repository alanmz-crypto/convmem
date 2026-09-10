"""Shared hermetic helpers for incremental JSONL production tests."""

# Helpers intentionally mirror the reviewed scratch fault/replay harness.
# pylint: disable=duplicate-code

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from incremental_jsonl_isolation import (
    IsolationBoundary,
    PRODUCTION_OVERRIDE_ENV,
    create_fresh_root,
    known_production_roots,
    sanitized_worker_env,
)


WORKER = Path(__file__).with_name("incremental_jsonl_isolation_worker.py")
EMBED_DIM = 8


def fake_summarize(text, **_kwargs):
    return f"summary:{hashlib.sha256(text.encode()).hexdigest()[:16]}"


def fake_embed(text, **_kwargs):
    digest = hashlib.sha256(text.encode()).digest()
    return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(EMBED_DIM)]


def fake_distill(text, **_kwargs):
    return [
        {
            "type": "explanation",
            "title": f"Isolated unit {text[:12]}",
            "summary": "Reusable isolated knowledge unit for hermetic tests.",
            "keywords": ["kiro", "jsonl", "incremental"],
            "confidence": 0.95,
            "domain": "general",
        }
    ]


def install_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    import ingest

    monkeypatch.setattr(ingest, "summarize", fake_summarize)
    monkeypatch.setattr(ingest, "ollama_embed", fake_embed)
    monkeypatch.setattr(ingest, "distill", fake_distill)


def kiro_record(index: int, *, content: str | None = None) -> bytes:
    row = {
        "timestamp": f"2026-09-10T00:00:{index % 60:02d}Z",
        "payload": {
            "type": "user" if index % 2 == 0 else "assistant",
            "content": content or f"message-{index:05d}",
        },
    }
    return (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")


def write_source(root: Path, count: int, *, name: str = "sess_prod") -> Path:
    source = root / "sources" / "hash" / name / "messages.jsonl"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"".join(kiro_record(i) for i in range(count)))
    (source.parent / "session.json").write_text(
        json.dumps(
            {
                "id": name,
                "workspacePaths": [str(root / "workspace")],
                "title": "isolated",
            }
        ),
        encoding="utf-8",
    )
    return source


def isolated_env(tmp_path: Path) -> tuple[IsolationBoundary, dict[str, str]]:
    root, token = create_fresh_root(tmp_path)
    parent_home = Path.home()
    env = sanitized_worker_env(
        root, token, forbidden_roots=known_production_roots(home=parent_home)
    )
    with pytest.MonkeyPatch.context() as mp:
        for key, value in env.items():
            mp.setenv(key, value)
        for name in tuple(os.environ):
            if name in {"CONVMEM_INCREMENTAL_TOKEN", "CONVMEM_INCREMENTAL_FORBIDDEN"}:
                continue
            if any(
                marker in name.upper()
                for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
            ):
                mp.delenv(name, raising=False)
        for name in (*PRODUCTION_OVERRIDE_ENV, "DEEPSEEK_API_KEY"):
            mp.delenv(name, raising=False)
        boundary = IsolationBoundary.from_environment()
    return boundary, env


def apply_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for name in tuple(os.environ):
        if name in env or name in {
            "CONVMEM_INCREMENTAL_TOKEN",
            "CONVMEM_INCREMENTAL_FORBIDDEN",
        }:
            continue
        if any(
            marker in name.upper()
            for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
        ):
            monkeypatch.delenv(name, raising=False)
    for name in (*PRODUCTION_OVERRIDE_ENV, "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def enable_incremental(boundary: IsolationBoundary, *, rebuild: bool = False) -> None:
    path = boundary.layout["user_config"]
    text = path.read_text(encoding="utf-8")
    text = text.replace("enabled = false", "enabled = true", 1)
    if rebuild:
        text = text.replace("allow_full_rebuild = false", "allow_full_rebuild = true", 1)
    path.write_text(text, encoding="utf-8")


def worker_run(
    boundary: IsolationBoundary,
    env: dict[str, str],
    source: Path,
    *,
    enabled: bool = True,
    fault: str = "",
) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        "-I",
        str(WORKER),
        "run",
        str(source),
        "1" if enabled else "0",
    ]
    if fault:
        args.append(fault)
    return subprocess.run(
        args,
        cwd=boundary.root,
        env=env,
        close_fds=True,
        start_new_session=True,
        capture_output=True,
        text=True,
        check=False,
    )


def chroma_authority(boundary: IsolationBoundary, source: Path) -> dict:
    from chroma_store import SUMMARIES, UNITS
    from incremental_jsonl import IncrementalJsonlCoordinator

    coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    )
    with coordinator._session() as session:  # pylint: disable=protected-access
        summaries = session.store.snapshot_source_rows(SUMMARIES, str(source))
        units = session.store.snapshot_source_rows(UNITS, str(source))
    summaries.sort(key=lambda row: row["id"])
    units.sort(key=lambda row: row["id"])
    checkpoint = coordinator.checkpoint() or {}
    keep = {
        name: checkpoint.get(name)
        for name in (
            "version",
            "commit_state",
            "adapter_format",
            "source_identity",
            "complete_boundary",
            "prefix_sha256",
            "transform_fingerprint",
            "record_count",
            "summary_ids",
            "unit_ids",
            "processed_hash",
        )
    }
    return {"summaries": summaries, "units": units, "checkpoint": keep}
