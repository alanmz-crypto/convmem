"""Subprocess dual-arm compare helpers (isolation one-shot + warm latency).

Fail-closed policy: worker return codes, error results, malformed output,
and startup identity mismatches raise WorkerFailure — they must never be
recorded as plausible misses or 0.0 latency samples.
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

REPO = Path(__file__).resolve().parent.parent
WORKER = REPO / "scripts" / "eval_query_arm_worker.py"

FALLBACK_SENTINEL_TOKEN = "FALLBACK_ONLY_SENTINEL_Z9"
FALLBACK_SENTINEL_ID = "fallback-sentinel-z9"

WARMUPS = 5
TIMED_REPS = 20
VIEWS = ("embedding_influenced", "operational_pipeline")


class WorkerFailure(RuntimeError):
    """A query worker failed; comparison must stop rather than fake a miss."""


EVAL_COLLECTION_NAME = "knowledge_units"

# Provenance keys that must be present and non-empty on every shadow
# collection in addition to the identity keys checked exactly.
REQUIRED_PROVENANCE_KEYS = (
    "convmem:build_manifest_sha256",
    "convmem:schema_version",
    "convmem:embed_dimensions",
)


def canonical_id_set_fingerprint(ids: set[str] | list[str]) -> str:
    """SHA-256 over sorted UTF-8 ids joined by \\n (canonical ID-set hash)."""
    payload = "\n".join(sorted(str(i) for i in ids)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_arm_collection_provenance(
    package_units: list[dict[str, Any]],
    arms: Mapping[str, tuple[Path, str]],
    *,
    collection_name: str = EVAL_COLLECTION_NAME,
) -> dict[str, Any]:
    """Read-only gate: both shadow collections must match the approved package.

    Verifies stored ``convmem:*`` collection metadata AND actual contents
    (row count + exact ID set) against identity recomputed from the package.
    Stored metadata alone cannot detect an interrupted or partially populated
    build, because metadata is written before embeddings finish.

    ``arms`` maps arm name -> (chroma_dir, expected embed model tag).
    Raises ValueError naming the failing key. Never opens a PersistentClient.
    """
    from chroma_readonly import collection_config_metadata, collection_ids

    from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex

    package_id_list = [str(u.get("id") or "") for u in package_units]
    if "" in package_id_list:
        raise ValueError("provenance: package contains a unit without an id")
    package_ids = set(package_id_list)
    if len(package_ids) != len(package_id_list):
        dupes = sorted(
            {i for i in package_id_list if package_id_list.count(i) > 1}
        )
        raise ValueError(f"provenance: duplicate package ids {dupes}")

    expected = {
        "package_sha256": package_sha256_hex(package_units),
        "unit_corpus_fingerprint": corpus_fingerprint_hex(package_units),
        "unit_count": len(package_units),
        "id_set_fingerprint": canonical_id_set_fingerprint(package_ids),
    }

    collections: dict[str, dict[str, Any]] = {}
    for arm, (chroma_dir, model_tag) in arms.items():
        stored = collection_config_metadata(chroma_dir, collection_name)
        if not stored:
            raise ValueError(
                f"provenance: {arm} collection has missing shadow provenance "
                f"(no stored metadata) in {chroma_dir}"
            )
        for key in REQUIRED_PROVENANCE_KEYS:
            if not str(stored.get(key) or "").strip():
                raise ValueError(
                    f"provenance: {arm} collection missing shadow provenance {key}"
                )
        identity_checks = {
            "convmem:embed_model": str(model_tag),
            "convmem:package_sha256": expected["package_sha256"],
            "convmem:unit_corpus_fingerprint": expected["unit_corpus_fingerprint"],
        }
        for key, want in identity_checks.items():
            got = str(stored.get(key) or "")
            if got != want:
                raise ValueError(
                    f"provenance: {arm} {key} mismatch: stored {got!r} "
                    f"expected {want!r}"
                )
        try:
            stored_count = int(stored.get("convmem:unit_count"))
        except (TypeError, ValueError):
            raise ValueError(
                f"provenance: {arm} convmem:unit_count invalid: "
                f"{stored.get('convmem:unit_count')!r}"
            ) from None
        if stored_count != expected["unit_count"]:
            raise ValueError(
                f"provenance: {arm} convmem:unit_count mismatch: stored "
                f"{stored_count} expected {expected['unit_count']}"
            )
        # Actual contents, not just declared metadata.
        actual_ids = set(collection_ids(chroma_dir, collection_name))
        if len(actual_ids) != expected["unit_count"]:
            raise ValueError(
                f"provenance: {arm} actual row count {len(actual_ids)} != "
                f"package unit_count {expected['unit_count']} "
                "(incomplete or over-populated collection)"
            )
        if actual_ids != package_ids:
            missing = sorted(package_ids - actual_ids)[:5]
            extra = sorted(actual_ids - package_ids)[:5]
            raise ValueError(
                f"provenance: {arm} actual id set differs from package: "
                f"missing={missing} extra={extra}"
            )
        collections[arm] = {
            "stored_metadata": {
                k: stored.get(k)
                for k in sorted(stored)
                if k.startswith("convmem:")
            },
            "actual_row_count": len(actual_ids),
            "actual_id_set_fingerprint": canonical_id_set_fingerprint(actual_ids),
        }

    arm_names = list(arms)
    if len(arm_names) == 2:
        a, b = arm_names
        for key in ("convmem:package_sha256", "convmem:unit_corpus_fingerprint", "convmem:unit_count"):
            if collections[a]["stored_metadata"].get(key) != collections[b][
                "stored_metadata"
            ].get(key):
                raise ValueError(
                    f"provenance: arms disagree on {key}: "
                    f"{a}={collections[a]['stored_metadata'].get(key)!r} "
                    f"{b}={collections[b]['stored_metadata'].get(key)!r}"
                )

    return {**expected, "collections": collections}


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
    return env


def _same_path(a: Any, b: Any) -> bool:
    try:
        return Path(str(a)).resolve(strict=False) == Path(str(b)).resolve(strict=False)
    except OSError:
        return str(a) == str(b)


def verify_startup_identity(
    startup: dict[str, Any],
    expected: dict[str, Any],
    *,
    context: str,
) -> None:
    """Raise WorkerFailure when the worker banner disagrees with authorized identity.

    Path-like keys compare resolved; scalar keys compare as strings.
    """
    path_keys = {"config_path", "chroma_dir", "data_dir"}
    for key, want in expected.items():
        got = startup.get(key)
        if key in path_keys:
            ok = got is not None and _same_path(got, want)
        else:
            ok = str(got) == str(want)
        if not ok:
            raise WorkerFailure(
                f"{context}: startup identity mismatch for {key}: "
                f"worker={got!r} authorized={want!r}"
            )


def run_one_shot_query(
    *,
    config_path: Path,
    query: str,
    top_k: int = 5,
    eval_view: str = "embedding_influenced",
    expected_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fresh subprocess; proves CONVMEM_CONFIG is loaded before imports.

    Fail closed: nonzero return code, malformed banner/result, error result,
    or identity mismatch raise WorkerFailure.
    """
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
    if proc.returncode != 0:
        raise WorkerFailure(
            f"one-shot worker exit {proc.returncode} for query {query!r}; "
            f"stderr: {proc.stderr.strip()[:800]}"
        )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise WorkerFailure(
            f"one-shot worker produced {len(lines)} output line(s); "
            f"stderr: {proc.stderr.strip()[:800]}"
        )
    try:
        startup = json.loads(lines[0])
        result = json.loads(lines[1])
    except json.JSONDecodeError as exc:
        raise WorkerFailure(f"one-shot worker emitted malformed JSON: {exc}") from exc
    if startup.get("type") != "startup":
        raise WorkerFailure(f"one-shot worker missing startup banner: {lines[0][:200]}")
    if result.get("type") != "result":
        raise WorkerFailure(
            f"one-shot worker returned non-result: {result.get('type')!r} "
            f"error={result.get('error')!r}"
        )
    if result.get("error"):
        raise WorkerFailure(f"one-shot worker query error: {result['error']}")
    if expected_identity:
        verify_startup_identity(startup, expected_identity, context="one-shot")
    return {
        "returncode": proc.returncode,
        "stderr": proc.stderr,
        "startup": startup,
        "result": result,
        "process_startup_ms": startup_ms,
    }


def start_latency_worker(
    *,
    arm: str,
    config_path: Path,
    expected_identity: dict[str, Any] | None = None,
) -> WorkerHandle:
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
    try:
        startup = json.loads(startup_line) if startup_line.strip() else {}
        ready = json.loads(ready_line) if ready_line.strip() else {}
    except json.JSONDecodeError as exc:
        proc.kill()
        raise WorkerFailure(f"latency worker {arm} malformed startup: {exc}") from exc
    if startup.get("type") != "startup" or ready.get("type") != "ready":
        stderr_tail = ""
        if proc.stderr is not None:
            try:
                proc.kill()
                stderr_tail = proc.stderr.read()[:800]
            except OSError:
                pass
        raise WorkerFailure(
            f"latency worker for {arm} failed ready: {ready_line!r}; {stderr_tail}"
        )
    if expected_identity:
        try:
            verify_startup_identity(
                startup, expected_identity, context=f"latency:{arm}"
            )
        except WorkerFailure:
            proc.kill()
            raise
    return WorkerHandle(
        arm=arm,
        proc=proc,
        config_path=config_path,
        startup=startup,
        startup_ms=startup_ms,
    )


def worker_query(handle: WorkerHandle, query: str, *, top_k: int, eval_view: str) -> dict[str, Any]:
    assert handle.proc.stdin and handle.proc.stdout
    if handle.proc.poll() is not None:
        raise WorkerFailure(f"latency worker {handle.arm} died (exit {handle.proc.returncode})")
    handle.proc.stdin.write(
        json.dumps({"query": query, "top_k": top_k, "eval_view": eval_view}) + "\n"
    )
    handle.proc.stdin.flush()
    line = handle.proc.stdout.readline()
    if not line.strip():
        raise WorkerFailure(f"latency worker {handle.arm} closed output mid-run")
    try:
        res = json.loads(line)
    except json.JSONDecodeError as exc:
        raise WorkerFailure(f"latency worker {handle.arm} malformed result: {exc}") from exc
    if res.get("type") != "result" or res.get("error"):
        raise WorkerFailure(
            f"latency worker {handle.arm} query failed: "
            f"type={res.get('type')!r} error={res.get('error')!r}"
        )
    return res


def stop_latency_worker(handle: WorkerHandle) -> None:
    if handle.proc.poll() is None:
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
    """5 discarded warmups + 20 timed reps; counterbalanced arm order; both views.

    Any worker error aborts measurement (WorkerFailure) — never records 0.0.
    """
    report = LatencyReport(
        process_startup_ms={
            "baseline": baseline.startup_ms,
            "challenger": challenger.startup_ms,
        }
    )
    if not queries:
        return report
    q = queries[0]
    for view in VIEWS:
        report.retrieval_ms[view] = {"baseline": [], "challenger": []}
        for _ in range(WARMUPS):
            worker_query(baseline, q, top_k=top_k, eval_view=view)
            worker_query(challenger, q, top_k=top_k, eval_view=view)
        for i in range(TIMED_REPS):
            if i % 2 == 0:
                order = ("baseline", "challenger")
            else:
                order = ("challenger", "baseline")
            for arm in order:
                handle = baseline if arm == "baseline" else challenger
                res = worker_query(handle, q, top_k=top_k, eval_view=view)
                elapsed = res.get("elapsed_ms")
                if not isinstance(elapsed, (int, float)) or elapsed <= 0:
                    raise WorkerFailure(
                        f"latency worker {arm} returned invalid elapsed_ms {elapsed!r}"
                    )
                report.retrieval_ms[view][arm].append(float(elapsed))
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
    *,
    expected_identity: dict[str, Any] | None = None,
) -> Callable[..., list[dict]]:
    """QueryFn using one-shot workers (scoring path; not warm latency).

    Fail closed: any worker failure raises WorkerFailure and must abort the
    comparison; it is never converted into an empty hit list.
    """

    def _fn(query: str, *, top_k: int, eval_view: str) -> list[dict]:
        payload = run_one_shot_query(
            config_path=config_path,
            query=query,
            top_k=top_k,
            eval_view=eval_view or "embedding_influenced",
            expected_identity=expected_identity,
        )
        hits = payload["result"].get("hits") or []
        return list(hits)

    return _fn


def _fallback_result(payload: dict[str, Any]) -> dict[str, Any]:
    hits = payload["result"].get("hits") or []
    ids = [str(h.get("id") or "") for h in hits]
    exercised = FALLBACK_SENTINEL_ID in ids
    return {
        "fallback_exercised": exercised,
        "fallback_sentinel_id": FALLBACK_SENTINEL_ID,
        "hit_ids": ids,
        "startup": payload.get("startup"),
    }


def exercise_dim_mismatch_fallback(
    *,
    config_path: Path,
    shadow_state_force_wrong: Callable[[bool], None],
) -> dict[str, Any]:
    """In-process variant: toggle a shared fake-server state to wrong dims.

    SQLite is never renamed or removed; only the vector query path fails.
    fallback_exercised is true only when the fallback-only sentinel returns.
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
    return _fallback_result(payload)


def exercise_fallback_via_config(
    *,
    fallback_config_path: Path,
    expected_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """CLI variant: fallback config points at a dedicated wrong-dim embed endpoint.

    The config must be identical to the arm config except models.ollama_host,
    which targets an endpoint that always returns a wrong query-vector
    dimension. Chroma SQLite stays untouched and readable, so the keyword
    fallback path can serve the sentinel.
    """
    payload = run_one_shot_query(
        config_path=fallback_config_path,
        query=f"retrieve {FALLBACK_SENTINEL_TOKEN}",
        top_k=5,
        eval_view="embedding_influenced",
        expected_identity=expected_identity,
    )
    return _fallback_result(payload)
