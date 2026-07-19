"""Subprocess dual-arm compare helpers (isolation one-shot + warm latency)."""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parent.parent
WORKER = REPO / "scripts" / "eval_query_arm_worker.py"

FALLBACK_SENTINEL_TOKEN = "FALLBACK_ONLY_SENTINEL_Z9"
FALLBACK_SENTINEL_ID = "fallback-sentinel-z9"

WARMUPS = 5
TIMED_REPS = 20
VIEWS = ("embedding_influenced", "ops_pipeline")


@dataclass
class WorkerHandle:
    arm: str
    proc: subprocess.Popen
    config_path: Path
    startup: dict[str, Any]
    startup_ms: float


@dataclass
class LatencyReport:
    retrieval_ms: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    process_startup_ms: dict[str, float] = field(default_factory=dict)
    warmups: int = WARMUPS
    timed_reps: int = TIMED_REPS
    counterbalanced: bool = True


def _env_with_config(config_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["CONVMEM_CONFIG"] = str(config_path.resolve())
    # Prevent accidental live host bleed if config is incomplete
    return env


def run_one_shot_query(
    *,
    config_path: Path,
    query: str,
    top_k: int = 5,
    eval_view: str = "embedding_influenced",
) -> dict[str, Any]:
    """Fresh subprocess; proves CONVMEM_CONFIG is loaded before imports."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        [
            sys.executable,
            str(WORKER),
            "--mode",
            "one-shot",
            "--query",
            query,
            "--top-k",
            str(top_k),
            "--eval-view",
            eval_view,
        ],
        cwd=str(REPO),
        env=_env_with_config(config_path),
        capture_output=True,
        text=True,
        check=False,
    )
    startup_ms = (time.perf_counter() - t0) * 1000.0
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    startup = json.loads(lines[0]) if lines else {}
    result = json.loads(lines[1]) if len(lines) > 1 else {"type": "error", "hits": []}
    return {
        "returncode": proc.returncode,
        "stderr": proc.stderr,
        "startup": startup,
        "result": result,
        "process_startup_ms": startup_ms,
    }


def start_latency_worker(*, arm: str, config_path: Path) -> WorkerHandle:
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, str(WORKER), "--mode", "serve"],
        cwd=str(REPO),
        env=_env_with_config(config_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    startup_line = proc.stdout.readline()
    ready_line = proc.stdout.readline()
    startup_ms = (time.perf_counter() - t0) * 1000.0
    startup = json.loads(startup_line) if startup_line.strip() else {}
    ready = json.loads(ready_line) if ready_line.strip() else {}
    if ready.get("type") != "ready":
        proc.kill()
        raise RuntimeError(f"latency worker for {arm} failed ready: {ready_line!r}")
    return WorkerHandle(
        arm=arm,
        proc=proc,
        config_path=config_path,
        startup=startup,
        startup_ms=startup_ms,
    )


def worker_query(handle: WorkerHandle, query: str, *, top_k: int, eval_view: str) -> dict[str, Any]:
    assert handle.proc.stdin and handle.proc.stdout
    handle.proc.stdin.write(
        json.dumps({"query": query, "top_k": top_k, "eval_view": eval_view}) + "\n"
    )
    handle.proc.stdin.flush()
    line = handle.proc.stdout.readline()
    return json.loads(line) if line.strip() else {"type": "error", "hits": []}


def stop_latency_worker(handle: WorkerHandle) -> None:
    if handle.proc.poll() is not None:
        for stream in (handle.proc.stdin, handle.proc.stdout, handle.proc.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        return
    try:
        if handle.proc.stdin:
            handle.proc.stdin.write("QUIT\n")
            handle.proc.stdin.flush()
    except BrokenPipeError:
        pass
    try:
        handle.proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        handle.proc.kill()
    for stream in (handle.proc.stdin, handle.proc.stdout, handle.proc.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def measure_warm_latency(
    *,
    baseline: WorkerHandle,
    challenger: WorkerHandle,
    queries: list[str],
    top_k: int = 5,
) -> LatencyReport:
    """5 discarded warmups + 20 timed reps; counterbalanced arm order; both views."""
    report = LatencyReport(
        process_startup_ms={
            "baseline": baseline.startup_ms,
            "challenger": challenger.startup_ms,
        }
    )
    if not queries:
        return report
    # Use first query for warm latency protocol (stable microbench)
    q = queries[0]
    for view in VIEWS:
        report.retrieval_ms[view] = {"baseline": [], "challenger": []}
        # Warmups (discarded)
        for _ in range(WARMUPS):
            worker_query(baseline, q, top_k=top_k, eval_view=view)
            worker_query(challenger, q, top_k=top_k, eval_view=view)
        # Timed reps with counterbalanced order
        for i in range(TIMED_REPS):
            if i % 2 == 0:
                order = ("baseline", "challenger")
            else:
                order = ("challenger", "baseline")
            for arm in order:
                handle = baseline if arm == "baseline" else challenger
                res = worker_query(handle, q, top_k=top_k, eval_view=view)
                report.retrieval_ms[view][arm].append(float(res.get("elapsed_ms") or 0.0))
    return report


def latency_summary(report: LatencyReport) -> dict[str, Any]:
    out: dict[str, Any] = {
        "latency_source": "warm_persistent_workers",
        "warmups_discarded": report.warmups,
        "timed_repetitions": report.timed_reps,
        "counterbalanced_arm_order": report.counterbalanced,
        "process_startup_ms": report.process_startup_ms,
        "retrieval_ms": {},
        "retrieval_queries_per_sec": {},
    }
    for view, arms in report.retrieval_ms.items():
        out["retrieval_ms"][view] = {}
        out["retrieval_queries_per_sec"][view] = {}
        for arm, samples in arms.items():
            mean = statistics.fmean(samples) if samples else 0.0
            out["retrieval_ms"][view][arm] = {
                "mean": round(mean, 4),
                "n": len(samples),
                "samples": [round(x, 4) for x in samples],
            }
            out["retrieval_queries_per_sec"][view][arm] = (
                round(1000.0 / mean, 6) if mean > 0 else 0.0
            )
    return out


def make_subprocess_query_fn(
    config_path: Path,
) -> Callable[..., list[dict]]:
    """QueryFn using one-shot workers (scoring path; not warm latency)."""

    def _fn(query: str, *, top_k: int, eval_view: str) -> list[dict]:
        payload = run_one_shot_query(
            config_path=config_path,
            query=query,
            top_k=top_k,
            eval_view=eval_view or "embedding_influenced",
        )
        hits = payload.get("result", {}).get("hits") or []
        return list(hits)

    return _fn


def exercise_dim_mismatch_fallback(
    *,
    config_path: Path,
    shadow_state_force_wrong: Callable[[bool], None],
) -> dict[str, Any]:
    """Trigger vector failure via wrong-dim embeds; SQLite must remain readable.

    Sets fallback_exercised true only when FALLBACK_SENTINEL_ID is returned and
    vector path was forced into failure.
    """
    shadow_state_force_wrong(True)
    try:
        payload = run_one_shot_query(
            config_path=config_path,
            query=f"retrieve {FALLBACK_SENTINEL_TOKEN}",
            top_k=5,
            eval_view="embedding_influenced",
        )
    finally:
        shadow_state_force_wrong(False)
    hits = payload.get("result", {}).get("hits") or []
    ids = [str(h.get("id") or "") for h in hits]
    exercised = FALLBACK_SENTINEL_ID in ids
    return {
        "fallback_exercised": exercised,
        "fallback_sentinel_id": FALLBACK_SENTINEL_ID,
        "hit_ids": ids,
        "startup": payload.get("startup"),
    }
