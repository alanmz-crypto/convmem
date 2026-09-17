# pylint: disable=redefined-outer-name
"""C5 hermetic path denial and C6 bounded-memory evidence for brief metadata."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.watch_oom_brief_hermetic import (
    ENVELOPE_2K,
    ENVELOPE_32K,
    write_c0_fixture,
    write_memory_fixture,
)
from tests.watch_oom_memory_test_support import (
    MAX_FULL_OVER_BASELINE,
    MAX_PEAK_BYTES,
    MIB,
    assert_bounded_brief_payload,
    assert_c5_negative_denies_default_brief,
    memory_brief_worker_args,
    run_memory_worker,
)

WORKER = Path(__file__).resolve().parent / "watch_oom_brief_memory_worker.py"
ROOT = Path(__file__).resolve().parents[1]
MAX_ENVELOPE_DELTA = 32 * MIB
FULL_SIZES = (5_000, 20_000, 58_825)
RUN_FULL = os.environ.get("CONVMEM_C6_FULL") == "1"


def _run_worker(*args: str, check: bool = True) -> tuple[dict, int]:
    return run_memory_worker(WORKER, ROOT, *args, check=check)


def test_c5_write_brief_does_not_touch_production(tmp_path: Path) -> None:
    out = tmp_path / "brief.md"
    payload, rc = _run_worker(
        "--mode",
        "c0",
        "--tmp-root",
        str(tmp_path / "c0-run"),
        "--out-path",
        str(out),
    )
    assert rc == 0
    assert payload["denied_paths"] == []
    golden = Path(__file__).resolve().parent / "golden" / "watch-oom-stream-brief"
    expected = json.loads((golden / "c0-payload.json").read_text(encoding="utf-8"))
    assert payload["core"] == expected
    assert "Dropped sixth decision" not in payload["render"]


def test_c5_negative_temp_config_without_out_path_is_denied(tmp_path: Path) -> None:
    fx = write_c0_fixture(tmp_path)
    assert_c5_negative_denies_default_brief(_run_worker, fx)


def test_c6_five_thousand_stays_under_ceiling(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    source = tmp_path / "Projects" / "convmem" / "session.jsonl"
    inventory = tmp_path / "inventory.jsonl"
    processed = tmp_path / "processed.json"
    write_memory_fixture(
        chroma,
        5_000,
        envelope=ENVELOPE_32K,
        inventory=inventory,
        processed=processed,
        source_path=source,
    )
    out = tmp_path / "brief.md"
    baseline, _rc = _run_worker("--mode", "baseline")
    payload, rc = _run_worker(
        *memory_brief_worker_args(chroma, inventory, processed, out, mode="memory")
    )
    assert_bounded_brief_payload(payload, rc, units=5_000)
    extra = payload["peak_rss_bytes"] - baseline["baseline_rss_bytes"]
    print(
        f"c6 5k 32KiB: peak={payload['peak_rss_bytes']/MIB:.1f}MiB "
        f"baseline={baseline['baseline_rss_bytes']/MIB:.1f}MiB extra={extra/MIB:.1f}MiB",
        flush=True,
    )
    chroma2 = tmp_path / "chroma-2k"
    source2 = tmp_path / "Projects" / "convmem" / "session-2k.jsonl"
    inv2 = tmp_path / "inventory-2k.jsonl"
    proc2 = tmp_path / "processed-2k.json"
    write_memory_fixture(
        chroma2,
        5_000,
        envelope=ENVELOPE_2K,
        inventory=inv2,
        processed=proc2,
        source_path=source2,
    )
    small, rc2 = _run_worker(
        *memory_brief_worker_args(
            chroma2, inv2, proc2, tmp_path / "brief-2k.md", mode="memory"
        )
    )
    assert rc2 == 0
    delta = abs(payload["peak_rss_bytes"] - small["peak_rss_bytes"])
    print(
        f"c6 5k envelope delta={delta/MIB:.1f}MiB "
        f"2KiB peak={small['peak_rss_bytes']/MIB:.1f}MiB",
        flush=True,
    )
    assert delta <= MAX_ENVELOPE_DELTA, delta


@pytest.mark.skipif(not RUN_FULL, reason="full C6 curve is host evidence, not CI RSS gate")
def test_c6_memory_curve_and_envelope_delta(tmp_path: Path) -> None:
    baseline, _rc = _run_worker("--mode", "baseline")
    rows = []
    for n in FULL_SIZES:
        chroma = tmp_path / f"chroma-{n}"
        source = tmp_path / "Projects" / "convmem" / f"session-{n}.jsonl"
        inventory = tmp_path / f"inventory-{n}.jsonl"
        processed = tmp_path / f"processed-{n}.json"
        write_memory_fixture(
            chroma,
            n,
            envelope=ENVELOPE_32K,
            inventory=inventory,
            processed=processed,
            source_path=source,
        )
        out = tmp_path / f"brief-{n}.md"
        payload, rc = _run_worker(
            *memory_brief_worker_args(chroma, inventory, processed, out, mode="memory")
        )
        assert rc == 0, payload
        assert payload["denied_paths"] == []
        assert payload["forbidden_in_rows"] == []
        assert payload["units"] == n
        assert payload["peak_rss_bytes"] < MAX_PEAK_BYTES
        extra = payload["peak_rss_bytes"] - baseline["baseline_rss_bytes"]
        print(
            f"c6 {n}: peak={payload['peak_rss_bytes']/MIB:.1f}MiB extra={extra/MIB:.1f}MiB",
            flush=True,
        )
        rows.append(payload)
    full = rows[-1]
    extra_full = full["peak_rss_bytes"] - baseline["baseline_rss_bytes"]
    assert extra_full <= MAX_FULL_OVER_BASELINE, extra_full

    chroma2 = tmp_path / "chroma-5k-2k"
    source2 = tmp_path / "Projects" / "convmem" / "session-2k.jsonl"
    inv2 = tmp_path / "inventory-2k.jsonl"
    proc2 = tmp_path / "processed-2k.json"
    write_memory_fixture(
        chroma2,
        5_000,
        envelope=ENVELOPE_2K,
        inventory=inv2,
        processed=proc2,
        source_path=source2,
    )
    small, rc = _run_worker(
        "--mode",
        "memory",
        "--chroma-dir",
        str(chroma2),
        "--inventory",
        str(inv2),
        "--processed",
        str(proc2),
        "--out-path",
        str(tmp_path / "brief-2k.md"),
    )
    assert rc == 0
    delta = abs(rows[0]["peak_rss_bytes"] - small["peak_rss_bytes"])
    assert delta <= MAX_ENVELOPE_DELTA, delta
