# pylint: disable=redefined-outer-name
"""C5 hermetic RSS and throughput evidence for export compaction."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKER = Path(__file__).resolve().parent / "export_compaction_memory_worker.py"
ROOT = Path(__file__).resolve().parents[1]
MIB = 1024 * 1024
MAX_PEAK_BYTES = 512 * MIB
MAX_128_OVER_BASELINE = 96 * MIB
SIZES = (16, 64, 128)
KINDS = ("duplicate", "unique", "mostly_unique")


def _run_worker(*args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(WORKER), *args],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def import_baseline() -> dict:
    return _run_worker("--kind", "unique", "--size-mib", "16", "--baseline-only")


@pytest.fixture(scope="module")
def measurements(import_baseline: dict) -> list[dict]:
    rows = []
    for kind in KINDS:
        for size in SIZES:
            row = _run_worker("--kind", kind, "--size-mib", str(size))
            row["import_baseline_rss_bytes"] = import_baseline["baseline_rss_bytes"]
            rows.append(row)
            extra = row["peak_rss_bytes"] - import_baseline["baseline_rss_bytes"]
            print(
                f"compaction memory {kind} {size}MIB: "
                f"peak={row['peak_rss_bytes']/MIB:.2f}MIB "
                f"baseline={import_baseline['baseline_rss_bytes']/MIB:.2f}MIB "
                f"extra={extra/MIB:.2f}MIB "
                f"elapsed={row['elapsed_s']:.3f}s "
                f"mib_s={(row['bytes']/MIB)/row['elapsed_s']:.1f} "
                f"sha={row['sha256_after'][:12]} rows={row['output_rows']}",
                flush=True,
            )
    return rows


def test_all_cases_stay_under_512_mib(measurements: list[dict]) -> None:
    for row in measurements:
        assert row["peak_rss_bytes"] < MAX_PEAK_BYTES, row


def test_128_mib_extra_rss_is_bounded(measurements: list[dict], import_baseline: dict) -> None:
    for row in measurements:
        if row["size_mib"] != 128:
            continue
        extra = row["peak_rss_bytes"] - import_baseline["baseline_rss_bytes"]
        assert extra <= MAX_128_OVER_BASELINE, row


def test_unique_heavy_does_not_scale_with_document_bytes(measurements: list[dict], import_baseline: dict) -> None:
    unique = {row["size_mib"]: row for row in measurements if row["kind"] == "unique"}
    extra_16 = unique[16]["peak_rss_bytes"] - import_baseline["baseline_rss_bytes"]
    extra_128 = unique[128]["peak_rss_bytes"] - import_baseline["baseline_rss_bytes"]
    # Document bytes grew 8x; extra RSS must not follow that slope.
    assert extra_128 - extra_16 < 48 * MIB, (extra_16, extra_128)


def test_hashes_and_counts_match_golden_oracle(measurements: list[dict]) -> None:
    for row in measurements:
        assert row["output_rows"] == row["expected_rows"], row
        assert row["removed"] == row["expected_removed"], row
        assert row["sha256_after"] == row["expected_sha256"], row
        if row["kind"] == "unique":
            assert row["sha256_before"] == row["sha256_after"], row
            assert row["removed"] == 0, row


def test_mostly_unique_rewrites_large_retained_output(measurements: list[dict]) -> None:
    rows = [row for row in measurements if row["kind"] == "mostly_unique"]
    assert rows
    for row in rows:
        assert row["removed"] > 0, row
        assert row["output_bytes"] > (row["bytes"] * 8) // 10, row
        if row["size_mib"] == 128:
            assert row["output_bytes"] > 64 * MIB, row
