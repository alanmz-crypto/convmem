# pylint: disable=redefined-outer-name
"""C5 hermetic path denial and C6 bounded-memory evidence for exposure-window probe."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.watch_oom_brief_hermetic import ENVELOPE_2K, ENVELOPE_32K, write_c0_fixture
from tests.watch_oom_exposure_hermetic import (
    write_exposure_memory_fixture,
    write_exposure_register,
)

WORKER = Path(__file__).resolve().parent / "watch_oom_exposure_memory_worker.py"
ROOT = Path(__file__).resolve().parents[1]
MIB = 1024 * 1024
MAX_PEAK_BYTES = 384 * MIB
MAX_FULL_OVER_BASELINE = 160 * MIB
MAX_ENVELOPE_DELTA = 16 * MIB
FULL_SIZES = (5_000, 20_000, 58_825)
RUN_FULL = os.environ.get("CONVMEM_C6_FULL") == "1"


def _inventory_paths(tmp_path: Path, slug: str) -> tuple[Path, Path, Path]:
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


def _run_worker(*args: str, check: bool = True) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(WORKER), *args],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise AssertionError(
            f"worker failed rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return json.loads(proc.stdout), proc.returncode


def test_c5_probe_worker_denies_production_default_brief(tmp_path: Path) -> None:
    fx = write_c0_fixture(tmp_path / "c0")
    payload, rc = _run_worker(
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


def test_c6_probe_alone_five_thousand_stays_bounded(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    write_exposure_memory_fixture(chroma, 5_000, envelope=ENVELOPE_32K)
    baseline, _rc = _run_worker("--mode", "baseline")
    payload, rc = _run_worker("--mode", "probe", "--chroma-dir", str(chroma))
    assert rc == 0
    assert payload["denied_paths"] == []
    assert payload["peak_rss_bytes"] < MAX_PEAK_BYTES
    print(
        f"c6 probe 5k: peak={payload['peak_rss_bytes']/MIB:.1f}MiB "
        f"baseline={baseline['baseline_rss_bytes']/MIB:.1f}MiB",
        flush=True,
    )

    chroma2 = tmp_path / "chroma-2k"
    write_exposure_memory_fixture(chroma2, 5_000, envelope=ENVELOPE_2K)
    small, rc2 = _run_worker("--mode", "probe", "--chroma-dir", str(chroma2))
    assert rc2 == 0
    delta = abs(payload["peak_rss_bytes"] - small["peak_rss_bytes"])
    assert delta <= MAX_ENVELOPE_DELTA, delta


def test_c6_brief_chain_with_standing_row(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    write_exposure_memory_fixture(chroma, 5_000, envelope=ENVELOPE_32K)
    _source, inventory, processed = _inventory_paths(tmp_path, "5k")
    reg = write_exposure_register(tmp_path)
    out = tmp_path / "brief.md"
    baseline, _rc = _run_worker("--mode", "baseline")
    payload, rc = _run_worker(
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
        "--register",
        str(reg),
    )
    assert rc == 0
    assert payload["denied_paths"] == []
    assert payload["forbidden_in_rows"] == []
    assert payload["units"] == 5_000
    assert payload["peak_rss_bytes"] < MAX_PEAK_BYTES
    extra = payload["peak_rss_bytes"] - baseline["baseline_rss_bytes"]
    print(
        f"c6 brief 5k: peak={payload['peak_rss_bytes']/MIB:.1f}MiB extra={extra/MIB:.1f}MiB",
        flush=True,
    )


@pytest.mark.skipif(not RUN_FULL, reason="full C6 curve is host evidence, not CI RSS gate")
def test_c6_memory_curve_probe_and_brief(tmp_path: Path) -> None:
    baseline, _rc = _run_worker("--mode", "baseline")
    probe_rows = []
    brief_rows = []
    for n in FULL_SIZES:
        chroma = tmp_path / f"chroma-{n}"
        write_exposure_memory_fixture(chroma, n, envelope=ENVELOPE_32K)
        _source, inventory, processed = _inventory_paths(tmp_path, str(n))
        reg = write_exposure_register(tmp_path)
        probe, rc = _run_worker("--mode", "probe", "--chroma-dir", str(chroma))
        assert rc == 0, probe
        assert probe["peak_rss_bytes"] < MAX_PEAK_BYTES
        probe_rows.append(probe)
        out = tmp_path / f"brief-{n}.md"
        brief, rc2 = _run_worker(
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
            "--register",
            str(reg),
        )
        assert rc2 == 0, brief
        assert brief["denied_paths"] == []
        assert brief["forbidden_in_rows"] == []
        assert brief["units"] == n
        assert brief["peak_rss_bytes"] < MAX_PEAK_BYTES
        brief_rows.append(brief)
        print(
            f"c6 {n}: probe={probe['peak_rss_bytes']/MIB:.1f}MiB "
            f"brief={brief['peak_rss_bytes']/MIB:.1f}MiB",
            flush=True,
        )
    extra_full = brief_rows[-1]["peak_rss_bytes"] - baseline["baseline_rss_bytes"]
    assert extra_full <= MAX_FULL_OVER_BASELINE, extra_full

    chroma20_32k = tmp_path / "chroma-20k-32k"
    chroma20_2k = tmp_path / "chroma-20k-2k"
    write_exposure_memory_fixture(chroma20_32k, 20_000, envelope=ENVELOPE_32K)
    write_exposure_memory_fixture(chroma20_2k, 20_000, envelope=ENVELOPE_2K)
    big_probe, _ = _run_worker("--mode", "probe", "--chroma-dir", str(chroma20_32k))
    small_probe, _ = _run_worker("--mode", "probe", "--chroma-dir", str(chroma20_2k))
    delta = abs(big_probe["peak_rss_bytes"] - small_probe["peak_rss_bytes"])
    assert delta <= MAX_ENVELOPE_DELTA, delta
