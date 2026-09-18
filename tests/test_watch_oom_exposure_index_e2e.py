# pylint: disable=redefined-outer-name,too-many-statements
"""§9.7 post-merge ingest.index paired measurement (host evidence)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.watch_oom_exposure_index_e2e_support import (
    BASELINE_SHA,
    FULL_SIZES,
    arm_layout,
    assert_canaries_unchanged,
    build_writable_fixture_seed,
    canary_drift_report,
    format_mib,
    harness_file_hash,
    preflight_host,
    prepare_arm_paths,
    should_stop_between_arms,
    snapshot_canaries,
    write_synthetic_transcript,
)
from tests.watch_oom_memory_test_support import MIB, run_memory_worker

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve().parent / "watch_oom_exposure_index_e2e_worker.py"
BASELINE_ROOT = Path("/home/lauer/Projects/convmem-watch-oom-exposure-e2e-baseline")
RUN_FULL = os.environ.get("CONVMEM_E2E_FULL") == "1" or os.environ.get("CONVMEM_C6_FULL") == "1"
WORKER_CEILING = 2 * 1024 * 1024 * 1024
WORKER_TIMEOUT_SECONDS = 90


def _candidate_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _run_index_worker(
    *,
    target_root: Path,
    target_sha: str,
    layout: dict[str, Path],
    harness_hash: str,
    timeout: int = WORKER_TIMEOUT_SECONDS,
) -> dict:
    chroma_dir = layout["fixture"] / "chroma"
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(WORKER),
                "--target-root",
                str(target_root),
                "--target-sha",
                target_sha,
                "--harness-hash",
                harness_hash,
                "--config-path",
                str(layout["config"]),
                "--chroma-dir",
                str(chroma_dir),
                "--writer-root",
                str(layout["writer"]),
                "--brief-path",
                str(layout["brief"]),
                "--register-path",
                str(layout["arm"] / "standing-checks-register.json"),
                "--transcript",
                str(layout["transcript"]),
            ],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = round(time.monotonic() - started, 3)
        stderr = exc.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        detail = (stderr or "").strip() or f"worker timed out after {timeout}s"
        return {
            "status": "timed_out",
            "returncode": None,
            "elapsed_seconds": elapsed,
            "detail": detail,
        }

    elapsed = round(time.monotonic() - started, 3)
    stdout = proc.stdout.strip()
    if not stdout:
        return {
            "status": "exited",
            "returncode": proc.returncode,
            "elapsed_seconds": elapsed,
            "detail": proc.stderr.strip() or f"worker exited {proc.returncode} with no stdout",
        }
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "status": "invalid_output",
            "returncode": proc.returncode,
            "elapsed_seconds": elapsed,
            "detail": proc.stderr.strip() or proc.stdout.strip(),
        }

    status = payload.pop("status", "succeeded")
    payload["status"] = status
    payload["returncode"] = proc.returncode
    payload.setdefault("elapsed_seconds", elapsed)
    return payload


def _remaining_floor(payload: dict) -> int:
    return int(payload["peak_rss_bytes"]) - int(payload["import_baseline_rss_bytes"])


def _finalize_arm_canaries(
    before: dict,
    *,
    label: str,
    n: int,
    canary_ambiguity: list[str],
) -> None:
    after = snapshot_canaries()
    drift = canary_drift_report(before, after)
    if drift:
        canary_ambiguity.extend(
            [f"{label} n={n}: {line}" for line in drift]
        )
        return
    assert_canaries_unchanged(before, after)


def test_e2e_negative_control_denies_production_default_brief() -> None:
    from tests.watch_oom_memory_test_support import assert_c5_negative_denies_default_brief
    from tests.watch_oom_brief_hermetic import write_c0_fixture

    exposure_worker = Path(__file__).resolve().parent / "watch_oom_exposure_memory_worker.py"
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / "convmem-e2e-negative"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    fx = write_c0_fixture(tmp / "c0")

    def _run(*args: str, check: bool = True):
        return run_memory_worker(exposure_worker, ROOT, *args, check=check)

    assert_c5_negative_denies_default_brief(_run, fx)


@pytest.mark.skipif(not RUN_FULL, reason="full §9.7 curve is host evidence, not CI RSS gate")
def test_e2e_paired_ingest_index_measurement(tmp_path: Path) -> None:
    scratch = Path(
        os.environ.get(
            "CONVMEM_E2E_SCRATCH",
            str(Path.home() / ".cache/convmem-e2e-scratch"),
        )
    )
    scratch.mkdir(parents=True, exist_ok=True)
    host = preflight_host(scratch)
    assert host["ok"], host

    candidate_sha = _candidate_sha()
    harness_hash = harness_file_hash(WORKER)
    rows: list[dict] = []
    outcome_counts = {
        "timed_out": 0,
        "exited": 0,
        "invalid_output": 0,
        "succeeded": 0,
    }
    canary_ambiguity: list[str] = []
    print(
        json.dumps(
            {
                "event": "preflight",
                "host": host,
                "candidate_sha": candidate_sha,
                "baseline_sha": BASELINE_SHA,
                "harness_hash": harness_hash,
                "worker_as_limit_gib": 2,
                "worker_timeout_seconds": WORKER_TIMEOUT_SECONDS,
            },
            indent=2,
        ),
        flush=True,
    )

    for n in FULL_SIZES:
        if canary_ambiguity:
            break
        if should_stop_between_arms():
            pytest.fail(f"stop condition: available RAM below 4 GiB before n={n}")

        seed_dir = scratch / f"n-{n}" / "seed"
        if seed_dir.exists():
            shutil.rmtree(seed_dir)
        seed_info = build_writable_fixture_seed(seed_dir, n)
        transcript_path = (
            scratch
            / f"n-{n}"
            / "shared"
            / "Projects"
            / "convmem"
            / "agent-transcripts"
            / "e2e-measurement"
            / "e2e.jsonl"
        )
        transcript_hash = write_synthetic_transcript(transcript_path)

        pair: dict[str, dict] = {}
        for label, tip_root, tip_sha in (
            ("baseline", BASELINE_ROOT, BASELINE_SHA),
            ("candidate", ROOT, candidate_sha),
        ):
            if canary_ambiguity:
                break
            if should_stop_between_arms():
                pytest.fail(f"stop condition before {label} arm at n={n}")

            layout = arm_layout(scratch, label, n)
            prepare_arm_paths(
                layout,
                Path(seed_info["seed_dir"]),
                seed_info,
                transcript_path=transcript_path,
            )
            canaries_before = snapshot_canaries()
            outcome: dict | None = None
            try:
                outcome = _run_index_worker(
                    target_root=tip_root,
                    target_sha=tip_sha,
                    layout=layout,
                    harness_hash=harness_hash,
                )
            finally:
                _finalize_arm_canaries(
                    canaries_before,
                    label=label,
                    n=n,
                    canary_ambiguity=canary_ambiguity,
                )

            if outcome is not None:
                status = outcome["status"]
                outcome_counts[status] = outcome_counts.get(status, 0) + 1
                pair[label] = outcome

                if status == "succeeded":
                    assert outcome["denied_paths"] == []
                    assert outcome.get("import_order", [])[:2] == [
                        "hermetic_guards_installed",
                        "rlimit_as_2gib",
                    ]
                    print(
                        f"§9.7 {label} n={n}: import={format_mib(outcome['import_baseline_rss_bytes'])} "
                        f"peak={format_mib(outcome['peak_rss_bytes'])} "
                        f"floor={format_mib(_remaining_floor(outcome))} "
                        f"probe={outcome['probe_digest']}",
                        flush=True,
                    )
                else:
                    print(
                        f"§9.7 {label} n={n}: {status} "
                        f"rc={outcome.get('returncode')} "
                        f"elapsed={outcome.get('elapsed_seconds')}s "
                        f"{outcome.get('detail', '')}",
                        flush=True,
                    )

            if canary_ambiguity:
                break

            shutil.rmtree(layout["root"], ignore_errors=True)

        row = {
            "n": n,
            "transcript_sha256": transcript_hash,
            "baseline": pair.get("baseline"),
            "candidate": pair.get("candidate"),
        }
        baseline = pair.get("baseline") or {}
        candidate = pair.get("candidate") or {}
        if (
            baseline.get("status") == "succeeded"
            and candidate.get("status") == "succeeded"
            and "peak_rss_bytes" in baseline
            and "peak_rss_bytes" in candidate
        ):
            row["delta_peak_bytes"] = (
                candidate["peak_rss_bytes"] - baseline["peak_rss_bytes"]
            )
            row["delta_floor_bytes"] = (
                _remaining_floor(candidate) - _remaining_floor(baseline)
            )
            assert baseline["probe_digest"] == candidate["probe_digest"]
        rows.append(row)
        shutil.rmtree(seed_dir, ignore_errors=True)

    succeeded_arms = outcome_counts.get("succeeded", 0)
    blocked = succeeded_arms == 0 or bool(canary_ambiguity)
    if canary_ambiguity:
        verdict = (
            "Measurement stopped: production canary drift detected during the paired "
            "run (active watch may have changed a canary). Do not operate the watcher "
            "from this evidence. No remaining-floor delta is claimed for §9.8. "
            "The live 12.5 GiB watcher OOM remains unexplained and issue #268 is not closed."
        )
    elif succeeded_arms == 0:
        verdict = (
            "On archlinux, real ingest.index(force_file=...) under the mandated 2 GiB "
            f"RLIMIT_AS worker ceiling did not complete within {WORKER_TIMEOUT_SECONDS}s "
            "for any paired arm on writable Chroma fixtures. No remaining-floor delta "
            "is claimed for §9.8. The live 12.5 GiB watcher OOM remains unexplained "
            "and issue #268 is not closed."
        )
    else:
        verdict = (
            "Paired ingest.index measurement completed for at least one arm under the "
            "mandated 2 GiB RLIMIT_AS ceiling; see per-row deltas where both arms "
            "succeeded. This quantifies the measured brief-path floor only; the live "
            "12.5 GiB watcher OOM remains unexplained and issue #268 is not closed."
        )

    evidence = {
        "hostname": host["hostname"],
        "candidate_sha": candidate_sha,
        "baseline_sha": BASELINE_SHA,
        "harness_hash": harness_hash,
        "worker_as_limit_gib": 2,
        "worker_timeout_seconds": WORKER_TIMEOUT_SECONDS,
        "outcome_counts": outcome_counts,
        "canary_ambiguity": canary_ambiguity,
        "measurement_blocked": blocked,
        "rows": rows,
        "verdict": verdict,
    }
    evidence_path = ROOT / "docs" / "plans" / "EVIDENCE-watch-oom-exposure-index-e2e.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)


def test_e2e_5k_harness_wiring_without_as_ceiling(tmp_path: Path) -> None:
    """Prove harness wiring without RLIMIT_AS (not the mandated measurement arm)."""
    from contextlib import ExitStack
    from unittest.mock import patch

    from tests.watch_oom_exposure_index_e2e_worker import EMBED_VECTOR, _distill_stub

    seed_dir = tmp_path / "seed"
    seed_info = build_writable_fixture_seed(seed_dir, 5_000)
    layout = arm_layout(tmp_path, "candidate", 5_000)
    prepare_arm_paths(layout, Path(seed_info["seed_dir"]), seed_info)
    os.environ["CONVMEM_CONFIG"] = str(layout["config"])

    import brief
    import doctor
    import ingest

    writer_root = layout["writer"]
    real_ws = ingest.production_chroma_write_session
    real_wb = ingest.production_writer_boundary

    def hermetic_ws(*, entrypoint: str, **kwargs):
        kwargs["lock_path"] = writer_root / "writer.lock"
        kwargs["attest_dir"] = writer_root / "attest"
        kwargs["census_dir"] = writer_root / "census"
        return real_ws(entrypoint=entrypoint, **kwargs)

    def hermetic_wb(*, entrypoint: str, **kwargs):
        kwargs["lock_path"] = writer_root / "writer.lock"
        kwargs["attest_dir"] = writer_root / "attest"
        kwargs["census_dir"] = writer_root / "census"
        return real_wb(entrypoint=entrypoint, **kwargs)

    canaries_before = snapshot_canaries()
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(brief, "DEFAULT_BRIEF_PATH", layout["brief"]))
            stack.enter_context(
                patch.object(
                    doctor,
                    "_standing_register_path",
                    return_value=layout["arm"] / "standing-checks-register.json",
                )
            )
            stack.enter_context(patch("ingest.summarize", return_value="e2e summary"))
            stack.enter_context(patch("ingest._distill_with_provenance", side_effect=_distill_stub))
            stack.enter_context(patch("ingest.ollama_embed", return_value=EMBED_VECTOR))
            stack.enter_context(patch("ingest.time.sleep"))
            stack.enter_context(patch("ingest.production_chroma_write_session", side_effect=hermetic_ws))
            stack.enter_context(patch("ingest.production_writer_boundary", side_effect=hermetic_wb))
            stats = ingest.index(
                force_file=str(layout["transcript"]),
                verbose=False,
                force_reindex=True,
            )
    finally:
        canaries_after = snapshot_canaries()
        assert_canaries_unchanged(canaries_before, canaries_after)

    assert stats["files_processed"] == 1
    assert layout["brief"].is_file()
    print(f"§9.7 wiring 5k: files_processed={stats['files_processed']}", flush=True)
