"""Shared helpers for watch-OOM memory subprocess tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MIB = 1024 * 1024
MAX_PEAK_BYTES = 384 * MIB
MAX_FULL_OVER_BASELINE = 160 * MIB


def run_memory_worker(
    worker: Path,
    root: Path,
    *args: str,
    check: bool = True,
) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(worker), *args],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise AssertionError(
            f"worker failed rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return json.loads(proc.stdout), proc.returncode


def memory_brief_worker_args(
    chroma: Path,
    inventory: Path,
    processed: Path,
    out: Path,
    *,
    register: Path | None = None,
) -> tuple[str, ...]:
    args: tuple[str, ...] = (
        "--mode",
        "brief",
        "--chroma-dir",
        str(chroma),
        "--inventory",
        str(inventory),
        "--processed",
        str(processed),
        "--out-path",
        str(out),
    )
    if register is not None:
        args = args + ("--register", str(register))
    return args


def assert_bounded_brief_payload(
    payload: dict,
    rc: int,
    *,
    units: int,
) -> None:
    assert rc == 0
    assert payload["denied_paths"] == []
    assert payload["forbidden_in_rows"] == []
    assert payload["units"] == units
    assert payload["peak_rss_bytes"] < MAX_PEAK_BYTES


def assert_c5_negative_denies_default_brief(
    run_worker: callable,
    fx: dict[str, Path],
) -> None:
    payload, rc = run_worker(
        "--mode",
        "c5-negative",
        "--chroma-dir",
        str(fx["chroma_dir"]),
        "--inventory",
        str(fx["inventory"]),
        "--processed",
        str(fx["processed"]),
        check=False,
    )
    assert rc == 0
    assert payload["denied"] is True
    assert payload["denied_paths"]


def write_inventory_paths(tmp_path: Path, slug: str) -> tuple[Path, Path, Path]:
    source = tmp_path / "Projects" / "convmem" / f"session-{slug}.jsonl"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("memory-source\n", encoding="utf-8")
    inventory = tmp_path / f"inventory-{slug}.jsonl"
    processed = tmp_path / f"processed-{slug}.json"
    inventory.write_text(
        json.dumps({"path": str(source), "format": "jsonl"}) + "\n",
        encoding="utf-8",
    )
    processed.write_text(
        json.dumps({"hash-mem": {"path": str(source), "format": "jsonl"}}),
        encoding="utf-8",
    )
    return source, inventory, processed
