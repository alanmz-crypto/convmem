# pylint: disable=redefined-outer-name,too-many-statements,too-many-locals
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
    FROZEN_MAIN_SHA,
    FULL_SIZES,
    arm_layout,
    assert_canaries_unchanged,
    build_writable_fixture_seed,
    canary_drift_report,
    format_mib,
    harness_bundle_hash,
    harness_file_hashes,
    preflight_host,
    prepare_arm_paths,
    production_canary_contract,
    production_canary_paths,
    refresh_canary_stats,
    should_stop_between_arms,
    snapshot_canaries,
    write_synthetic_transcript,
    watcher_state,
)
from tests.watch_oom_memory_test_support import run_memory_worker

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve().parent / "watch_oom_exposure_index_e2e_worker.py"
HARNESS_FILES = (
    WORKER,
    Path(__file__).resolve().parent / "watch_oom_exposure_index_e2e_support.py",
    Path(__file__).resolve(),
)
BASELINE_ROOT = Path("/home/lauer/Projects/convmem-watch-oom-exposure-e2e-baseline")
RUN_FULL = os.environ.get("CONVMEM_E2E_FULL") == "1" or os.environ.get("CONVMEM_C6_FULL") == "1"
WORKER_CEILING = 2 * 1024 * 1024 * 1024
WORKER_TIMEOUT_SECONDS = 90


def _git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def _assert_frozen_candidate() -> str:
    branch_tip = _git_sha(ROOT)
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise AssertionError("measurement harness tree must be clean")
    subprocess.run(["git", "merge-base", "--is-ancestor", FROZEN_MAIN_SHA, branch_tip], cwd=ROOT, check=True)
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", FROZEN_MAIN_SHA, branch_tip, "--", "*.py"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert all(path.startswith("tests/") for path in changed), changed
    assert _git_sha(BASELINE_ROOT) == BASELINE_SHA
    return branch_tip


def _run_index_worker(
    *,
    target_root: Path,
    target_sha: str,
    layout: dict[str, Path],
    harness_hash: str,
    timeout: int = WORKER_TIMEOUT_SECONDS,
    wiring_no_as_limit: bool = False,
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
            ] + (["--wiring-no-as-limit"] if wiring_no_as_limit else []),
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

    status = payload.pop("status", "invalid_output")
    if status == "succeeded" and proc.returncode != 0:
        status = "invalid_output"
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
    after = refresh_canary_stats(before)
    drift = canary_drift_report(before, after)
    if drift:
        canary_ambiguity.extend(
            [f"{label} n={n}: {line}" for line in drift]
        )
        return
    assert_canaries_unchanged(before, after)


def test_production_canary_contract_covers_handoff_surfaces() -> None:
    contract = production_canary_contract()
    assert set(contract) == {
        "brief",
        "chroma",
        "config",
        "export",
        "watcher_service",
        "writer_gate",
    }
    assert len(production_canary_paths()) == 9


def test_e2e_negative_control_denies_production_default_brief(tmp_path: Path) -> None:
    from tests.watch_oom_memory_test_support import assert_c5_negative_denies_default_brief
    from tests.watch_oom_brief_hermetic import write_c0_fixture

    exposure_worker = Path(__file__).resolve().parent / "watch_oom_exposure_memory_worker.py"
    fx = write_c0_fixture(tmp_path / "c0")

    def _run(*args: str, check: bool = True):
        return run_memory_worker(exposure_worker, ROOT, *args, check=check)

    assert_c5_negative_denies_default_brief(_run, fx)


@pytest.mark.skipif(not RUN_FULL, reason="full §9.7 curve is host evidence, not CI RSS gate")
def test_e2e_paired_ingest_index_measurement() -> None:
    scratch_setting = os.environ.get("CONVMEM_E2E_SCRATCH")
    assert scratch_setting, "name a disk-backed CONVMEM_E2E_SCRATCH for the host run"
    scratch = Path(scratch_setting).resolve()
    forbidden = (
        (Path.home() / ".local/share/convmem").resolve(),
        (Path.home() / ".config/convmem").resolve(),
    )
    assert not any(scratch.is_relative_to(root) for root in forbidden)
    scratch.mkdir(parents=True, exist_ok=True)
    host = preflight_host(scratch)
    assert host["ok"], host

    branch_tip = _assert_frozen_candidate()
    file_hashes = harness_file_hashes(HARNESS_FILES)
    harness_hash = harness_bundle_hash(file_hashes)
    rows: list[dict] = []
    outcome_counts = {
        "timed_out": 0,
        "exited": 0,
        "invalid_output": 0,
        "succeeded": 0,
    }
    canary_ambiguity: list[str] = []
    hard_failures: list[str] = []
    complete_pairs = 0
    print(
        json.dumps(
            {
                "event": "preflight",
                "host": host,
                "candidate_main_sha": FROZEN_MAIN_SHA,
                "harness_branch_tip": branch_tip,
                "baseline_sha": BASELINE_SHA,
                "harness_hash": harness_hash,
                "harness_file_hashes": file_hashes,
                "worker_as_limit_gib": 2,
                "worker_timeout_seconds": WORKER_TIMEOUT_SECONDS,
            },
            indent=2,
        ),
        flush=True,
    )

    for n in FULL_SIZES:
        if canary_ambiguity or hard_failures:
            break
        if should_stop_between_arms():
            pytest.fail(f"stop condition: available RAM below 4 GiB before n={n}")

        seed_dir = scratch / f"n-{n}" / "seed"
        if seed_dir.exists():
            shutil.rmtree(seed_dir)
        seed_info = build_writable_fixture_seed(seed_dir, n)
        transcript_path = arm_layout(scratch, "shared", n)["transcript"]
        transcript_hash = write_synthetic_transcript(transcript_path)

        pair: dict[str, dict] = {}
        for label, tip_root, tip_sha in (
            ("baseline", BASELINE_ROOT, BASELINE_SHA),
            ("candidate", ROOT, branch_tip),
        ):
            if canary_ambiguity or hard_failures:
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
                if watcher_state() != host["watcher"]:
                    canary_ambiguity.append(f"{label} n={n}: watcher state changed")

            if outcome is not None:
                status = outcome["status"]
                outcome_counts[status] = outcome_counts.get(status, 0) + 1
                pair[label] = outcome
                if outcome.get("denied_paths") or outcome.get("network_denied"):
                    hard_failures.append(f"{label} n={n}: hermetic denial: {outcome}")

                if status == "succeeded":
                    assert outcome["denied_paths"] == []
                    assert outcome["network_denied"] == []
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

            if canary_ambiguity or hard_failures or status != "succeeded":
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
            complete_pairs += 1
        rows.append(row)
        shutil.rmtree(seed_dir, ignore_errors=True)
        if baseline.get("status") != "succeeded" or candidate.get("status") != "succeeded":
            break

    blocked = complete_pairs != len(FULL_SIZES) or bool(canary_ambiguity) or bool(hard_failures)
    if canary_ambiguity:
        verdict = (
            "Measurement stopped: production canary drift detected during the paired "
            "run (active watch may have changed a canary). Do not operate the watcher "
            "from this evidence. No remaining-floor delta is claimed for §9.8. "
            "The live 12.5 GiB watcher OOM remains unexplained and issue #268 is not closed."
        )
    elif hard_failures:
        verdict = "Measurement refused after a hermetic denial. No floor delta is authorized for §9.8."
    elif complete_pairs == 0:
        verdict = (
            "The real ingest.index(force_file=...) paired curve under the 2 GiB "
            "RLIMIT_AS worker ceiling did not complete. No remaining-floor delta "
            "is claimed for §9.8. The live 12.5 GiB watcher OOM remains unexplained "
            "and issue #268 is not closed."
        )
    elif blocked:
        verdict = (
            "Only part of the paired curve completed; no full-curve floor claim is "
            "authorized for §9.8. The live 12.5 GiB watcher OOM remains open."
        )
    else:
        verdict = (
            "All three paired ingest.index sizes completed under the 2 GiB "
            "RLIMIT_AS ceiling. This quantifies the measured brief-path floor only; the live "
            "12.5 GiB watcher OOM remains unexplained and issue #268 is not closed."
        )

    evidence = {
        "hostname": host["hostname"],
        "candidate_main_sha": FROZEN_MAIN_SHA,
        "harness_branch_tip": branch_tip,
        "baseline_sha": BASELINE_SHA,
        "harness_hash": harness_hash,
        "harness_file_hashes": file_hashes,
        "canary_contract": production_canary_contract(),
        "worker_as_limit_gib": 2,
        "worker_timeout_seconds": WORKER_TIMEOUT_SECONDS,
        "outcome_counts": outcome_counts,
        "canary_ambiguity": canary_ambiguity,
        "hard_failures": hard_failures,
        "complete_pairs": complete_pairs,
        "measurement_blocked": blocked,
        "rows": rows,
        "verdict": verdict,
    }
    evidence_path = ROOT / "docs" / "plans" / "EVIDENCE-watch-oom-exposure-index-e2e.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)
    if hard_failures:
        pytest.fail("hermetic denial during §9.7 measurement")


def test_e2e_wiring_in_denied_subprocess(tmp_path: Path) -> None:
    """Exercise a small writable fixture with guards before target imports."""
    seed_info = build_writable_fixture_seed(tmp_path / "seed", 64)
    layout = arm_layout(tmp_path, "candidate", 64)
    prepare_arm_paths(layout, Path(seed_info["seed_dir"]), seed_info)
    before = snapshot_canaries()
    try:
        outcome = _run_index_worker(
            target_root=ROOT,
            target_sha=_git_sha(ROOT),
            layout=layout,
            harness_hash=harness_bundle_hash(harness_file_hashes(HARNESS_FILES)),
            timeout=300,
            wiring_no_as_limit=True,
        )
    finally:
        assert_canaries_unchanged(before, refresh_canary_stats(before))

    assert outcome["status"] == "succeeded", outcome
    assert outcome["returncode"] == 0
    assert outcome["denied_paths"] == []
    assert outcome["network_denied"] == []
    assert outcome["import_order"][:2] == ["hermetic_guards_installed", "wiring_no_as_limit"]
    assert outcome["index_stats"]["files_processed"] == 1
    assert outcome["units_after"] > outcome["units_before"]
    assert outcome["probe_call_count"] >= 1
    assert outcome["writer_calls"]
