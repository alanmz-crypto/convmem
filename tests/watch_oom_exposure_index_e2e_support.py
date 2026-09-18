# pylint: disable=too-many-locals
"""Shared helpers for §9.7 post-merge ingest.index end-to-end measurement."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from chroma_store import ChromaStore
from chroma_readonly import collection_count
from tests.watch_oom_brief_hermetic import ENVELOPE_32K
from tests.watch_oom_exposure_hermetic import write_exposure_register

EMBED_DIM = 2
EMBED_VECTOR = [0.1, 0.2]
FULL_SIZES = (5_000, 20_000, 58_825)
BASELINE_SHA = "5c103aa2f11f54de74be3a7eab90c433c0c019cd"
MIN_RAM_GIB = 8
MIN_SCRATCH_GIB = 8
STOP_RAM_GIB = 4


@dataclass(frozen=True)
class PathCanary:
    path: str
    surface: str
    exists: bool
    size: int | None
    mode: int | None
    mtime_ns: int | None
    sha256: str | None
    device: int | None
    inode: int | None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Handoff § Hermetic rules: Chroma, brief, config, export, watcher/service paths.
CANARY_SURFACE_CONTRACT: dict[str, tuple[Path, ...]] = {
    "brief": (Path.home() / ".local/share/convmem/brief.md",),
    "chroma": (Path.home() / ".local/share/convmem/chroma/chroma.sqlite3",),
    "config": (Path.home() / ".config/convmem/config.toml",),
    "export": (
        Path.home() / ".local/share/convmem/knowledge_units.jsonl",
        Path.home() / ".local/share/convmem/processed.json",
    ),
    "watcher_service": (
        Path.home() / ".config/systemd/user/convmem-watch.service",
        Path.home() / ".config/systemd/user/convmem-refine.service",
        Path.home() / ".config/systemd/user/convmem-monitor.timer",
    ),
    "writer_gate": (
        Path.home() / ".local/share/convmem/locks/chroma_writer_gate.lock",
    ),
}


def production_canary_paths() -> list[tuple[str, Path]]:
    """Return (surface, path) pairs for every required production canary."""
    out: list[tuple[str, Path]] = []
    for surface, paths in CANARY_SURFACE_CONTRACT.items():
        for path in paths:
            out.append((surface, path))
    return out


def production_canary_contract() -> dict[str, list[str]]:
    """Audit-friendly map of handoff surfaces to absolute canary paths."""
    return {
        surface: [str(path) for path in paths]
        for surface, paths in CANARY_SURFACE_CONTRACT.items()
    }


def snapshot_canaries() -> dict[str, PathCanary]:
    out: dict[str, PathCanary] = {}
    for surface, path in production_canary_paths():
        key = str(path)
        if not path.exists():
            out[key] = PathCanary(key, surface, False, None, None, None, None, None, None)
            continue
        stat = path.stat()
        sha = None
        if path.is_file():
            sha = _file_sha256(path)
        out[key] = PathCanary(
            key,
            surface,
            True,
            stat.st_size,
            stat.st_mode,
            stat.st_mtime_ns,
            sha,
            stat.st_dev,
            stat.st_ino,
        )
    return out


def refresh_canary_stats(before: dict[str, PathCanary]) -> dict[str, PathCanary]:
    """Re-stat canaries after an arm; reuse prior sha256 when metadata is unchanged."""
    out: dict[str, PathCanary] = {}
    for key, left in before.items():
        path = Path(key)
        if not path.exists():
            out[key] = PathCanary(
                key, left.surface, False, None, None, None, None, None, None
            )
            continue
        stat = path.stat()
        unchanged = (
            left.exists
            and stat.st_size == left.size
            and stat.st_mode == left.mode
            and stat.st_mtime_ns == left.mtime_ns
            and stat.st_dev == left.device
            and stat.st_ino == left.inode
        )
        if unchanged:
            out[key] = left
            continue
        sha = _file_sha256(path) if path.is_file() else None
        out[key] = PathCanary(
            key,
            left.surface,
            True,
            stat.st_size,
            stat.st_mode,
            stat.st_mtime_ns,
            sha,
            stat.st_dev,
            stat.st_ino,
        )
    return out


def assert_canaries_unchanged(before: dict[str, PathCanary], after: dict[str, PathCanary]) -> None:
    assert before.keys() == after.keys()
    for key, left in before.items():
        right = after[key]
        assert left == right, f"production canary changed: {key}\n{left}\n{right}"


def canary_drift_report(
    before: dict[str, PathCanary], after: dict[str, PathCanary]
) -> list[str]:
    """Return human-readable drift lines; empty when unchanged."""
    drift: list[str] = []
    for key in sorted(before.keys()):
        left = before[key]
        right = after.get(key)
        if right is None or left != right:
            drift.append(
                f"{left.surface} {key}: before={left} after={right}"
            )
    return drift


def available_ram_gib() -> float:
    meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
    available_kib = 0
    for line in meminfo.splitlines():
        if line.startswith("MemAvailable:"):
            available_kib = int(line.split()[1])
            break
    return available_kib / (1024 * 1024)


def scratch_free_gib(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024 ** 3)


def preflight_host(scratch_dir: Path) -> dict[str, Any]:
    ram = available_ram_gib()
    scratch = scratch_free_gib(scratch_dir)
    ok = ram >= MIN_RAM_GIB and scratch >= MIN_SCRATCH_GIB
    return {
        "hostname": os.uname().nodename,
        "ram_available_gib": round(ram, 2),
        "scratch_free_gib": round(scratch, 2),
        "scratch_dir": str(scratch_dir),
        "ok": ok,
    }


def should_stop_between_arms() -> bool:
    return available_ram_gib() < STOP_RAM_GIB


def fixture_manifest(root: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        manifest[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def verify_fixture_manifest(root: Path, manifest: dict[str, str]) -> None:
    observed = fixture_manifest(root)
    assert observed == manifest, f"fixture clone mismatch under {root}"


def clone_fixture_seed(seed_dir: Path, clone_dir: Path) -> None:
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    shutil.copytree(seed_dir, clone_dir)


def _unit_meta(i: int, envelope: str, source_path: str) -> dict[str, Any]:
    kind = "decision" if i % 17 == 0 else "observation"
    lid = f"obs_mem_{i}" if kind != "decision" else f"dec_prop_mem_{i}"
    meta = {
        "ledger_id": lid,
        "ledger_kind": kind,
        "type": "decision" if kind == "decision" else "observation",
        "timestamp": f"2026-09-13T{i % 24:02d}:{(i % 60):02d}:00Z",
        "provenance_envelope": envelope,
        "title": f"Unit {i}",
        "summary": f"Unit {i}",
        "rationale": f"rationale {i}",
        "source_path": source_path,
    }
    if kind == "observation" and i % 23 == 0:
        meta["severity"] = "critical"
        meta["verification_result"] = "pass"
    elif kind == "observation" and i % 29 == 0:
        meta["severity"] = "high"
    return meta


def build_writable_fixture_seed(
    seed_dir: Path,
    n: int,
    *,
    envelope: str = ENVELOPE_32K,
    batch_size: int = 500,
) -> dict[str, Any]:
    """Build a writable Chroma seed outside the measured worker."""
    seed_dir.mkdir(parents=True, exist_ok=True)
    chroma_dir = seed_dir / "chroma"
    source = seed_dir / "Projects" / "convmem" / "agent-transcripts" / "e2e" / "e2e.jsonl"
    source.parent.mkdir(parents=True, exist_ok=True)
    inventory = seed_dir / "inventory.jsonl"
    processed = seed_dir / "processed.json"
    register = write_exposure_register(seed_dir)

    store = ChromaStore(str(chroma_dir))
    try:
        col = store._collection("knowledge_units")
        ids: list[str] = []
        docs: list[str] = []
        embeddings: list[list[float]] = []
        metas: list[dict[str, Any]] = []
        src = str(source)
        for i in range(n):
            eid = f"m-{i:06d}"
            meta = _unit_meta(i, envelope, src)
            ids.append(eid)
            docs.append(f"document body for {eid}")
            embeddings.append(EMBED_VECTOR)
            metas.append(meta)
            if len(ids) >= batch_size:
                col.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)
                ids.clear()
                docs.clear()
                embeddings.clear()
                metas.clear()
        if ids:
            col.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)
    finally:
        store.close()

    inventory.write_text(
        json.dumps({"path": str(source), "format": "jsonl"}) + "\n",
        encoding="utf-8",
    )
    processed.write_text("{}", encoding="utf-8")

    store = ChromaStore(str(chroma_dir))
    try:
        count = collection_count(str(chroma_dir), "knowledge_units")
        assert count == n
        sample = store.get_unit("m-000000")
        assert sample is not None
    finally:
        store.close()

    manifest = fixture_manifest(seed_dir)
    return {
        "seed_dir": str(seed_dir),
        "n": n,
        "envelope_bytes": len(envelope),
        "chroma_dir": str(chroma_dir),
        "inventory": str(inventory),
        "processed": str(processed),
        "register": str(register),
        "source": str(source),
        "manifest": manifest,
    }


def write_synthetic_transcript(path: Path) -> str:
    lines = [
        {
            "role": "user",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "§9.7 e2e measurement transcript: deterministic ingest.index probe.",
                    }
                ]
            },
        },
        {
            "role": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Acknowledged. This transcript exists only to exercise ingest.index.",
                    }
                ]
            },
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in lines) + "\n"
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode()).hexdigest()


def write_e2e_config(
    arm_dir: Path,
    *,
    chroma_dir: Path,
    inventory: Path,
    processed: Path,
    units_export: Path,
    transcript: Path,
) -> Path:
    arm_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = arm_dir / "config.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[sources]",
                f'inventory = "{inventory}"',
                "",
                "[index]",
                f'chroma_dir = "{chroma_dir}"',
                f'processed_log = "{processed}"',
                f'units_export = "{units_export}"',
                "chunk_size = 60",
                "chunk_overlap = 10",
                "",
                "[models]",
                'embed_model = "nomic-embed-text"',
                'summarize_model = "deepseek-v4-flash"',
                'distill_model = "deepseek-v4-flash"',
                'ollama_host = "http://127.0.0.1:9"',
                "",
                "[distill]",
                "min_confidence = 0.6",
                "",
                "[query]",
                "rerank = false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Keep transcript path in arm metadata for callers.
    (arm_dir / "transcript.path").write_text(str(transcript), encoding="utf-8")
    return cfg_path


def arm_layout(scratch_dir: Path, tip_label: str, n: int) -> dict[str, Path]:
    root = scratch_dir / f"n-{n}" / tip_label
    transcript = (
        root
        / "Projects"
        / "convmem"
        / "agent-transcripts"
        / "e2e-measurement"
        / "e2e.jsonl"
    )
    return {
        "root": root,
        "fixture": root / "fixture",
        "arm": root / "arm",
        "writer": root / "writer",
        "brief": root / "brief.md",
        "units_export": root / "knowledge_units.jsonl",
        "transcript": transcript,
        "config": root / "arm" / "config.toml",
    }


def prepare_arm_paths(
    layout: dict[str, Path],
    seed_dir: Path,
    seed_info: dict[str, Any],
    *,
    transcript_path: Path | None = None,
) -> None:
    clone_fixture_seed(seed_dir, layout["fixture"])
    verify_fixture_manifest(layout["fixture"], seed_info["manifest"])

    arm = layout["arm"]
    arm.mkdir(parents=True, exist_ok=True)
    shutil.copy2(seed_info["inventory"], arm / "inventory.jsonl")
    shutil.copy2(seed_info["processed"], arm / "processed.json")
    shutil.copy2(seed_info["register"], arm / "standing-checks-register.json")

    chroma_dir = layout["fixture"] / "chroma"
    assert chroma_dir.is_dir()
    layout["writer"].mkdir(parents=True, exist_ok=True)

    if transcript_path is not None:
        layout["transcript"].parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(transcript_path, layout["transcript"])
    else:
        write_synthetic_transcript(layout["transcript"])
    cfg_path = write_e2e_config(
        arm,
        chroma_dir=chroma_dir,
        inventory=arm / "inventory.jsonl",
        processed=arm / "processed.json",
        units_export=layout["units_export"],
        transcript=layout["transcript"],
    )
    layout["config"] = cfg_path


def harness_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def format_mib(num_bytes: int) -> str:
    return f"{num_bytes / (1024 * 1024):.1f}MiB"
