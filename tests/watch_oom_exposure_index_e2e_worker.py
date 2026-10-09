# pylint: disable=wrong-import-position,protected-access,too-many-locals
"""Subprocess worker for §9.7 ingest.index end-to-end measurement."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path

EMBED_VECTOR = [0.1, 0.2]


def _assert_no_target_modules_loaded() -> None:
    for name in list(sys.modules):
        if name in {
            "ingest",
            "brief",
            "doctor",
            "config",
            "chroma_readonly",
            "chroma_store",
            "chroma_write_store",
            "agent_run_ledger",
            "writer_census",
        } or name.startswith(("ingest.", "brief.", "doctor.", "config.", "chroma_")):
            raise RuntimeError(f"target module imported before boundary setup: {name}")


def _configure_target_imports(target_root: Path) -> None:
    target = str(target_root.resolve())
    sys.path[:] = [p for p in sys.path if p != target]
    sys.path.insert(0, target)


def _assert_target_paths(target_root: Path, modules: dict[str, object]) -> dict[str, str]:
    root = target_root.resolve()
    paths: dict[str, str] = {}
    for name, mod in modules.items():
        file_path = Path(getattr(mod, "__file__", "") or "").resolve()
        if not file_path.is_relative_to(root):
            raise RuntimeError(f"{name} resolved outside target tree: {file_path}")
        paths[name] = str(file_path)
    return paths


def _distill_stub(*_args, **_kwargs):
    units = [
        {
            "type": "explanation",
            "title": "E2E measurement unit",
            "summary": (
                "Deterministic distill output for §9.7 ingest.index probe "
                f"{hashlib.sha256(str(_args).encode()).hexdigest()[:12]}."
            ),
            "keywords": ["e2e", "measurement", "unique"],
            "confidence": 0.95,
            "domain": "coding.storage",
        }
    ]
    return units, json.dumps(units, ensure_ascii=False, sort_keys=True)


def _log(step: str) -> None:
    print(f"[e2e-worker] {step}", file=sys.stderr, flush=True)


def _require_temporary_path(path: Path) -> None:
    resolved = path.resolve()
    forbidden = (
        (Path.home() / ".local/share/convmem").resolve(),
        (Path.home() / ".config/convmem").resolve(),
    )
    if any(resolved.is_relative_to(root) for root in forbidden):
        raise RuntimeError(f"worker role resolves into production: {resolved}")


def _dispatch(args: argparse.Namespace, import_order: list[str]) -> int:
    from unittest.mock import patch

    from tests.linux_proc import peak_rss_bytes as peak_rss_bytes_fn
    from tests.linux_proc import proc_fd_targets as proc_fd_targets_fn
    from tests.linux_proc import rss_bytes as rss_bytes_fn
    from tests.watch_oom_hermetic_isolation import DENIED, NETWORK_DENIED
    from tests.watch_oom_memory_worker_shared import denied_exit_code, emit_worker_json

    target_root = Path(args.target_root).resolve()
    config_path = Path(args.config_path).resolve()
    writer_root = Path(args.writer_root).resolve()
    brief_path = Path(args.brief_path).resolve()
    register_path = Path(args.register_path).resolve()
    transcript = Path(args.transcript).resolve()
    for role in (config_path, writer_root, brief_path, register_path, transcript, Path(args.chroma_dir)):
        _require_temporary_path(role)

    os.environ["CONVMEM_CONFIG"] = str(config_path)
    _log("config set")
    _assert_no_target_modules_loaded()
    _configure_target_imports(target_root)

    import config as config_mod

    import_order.append("config")
    if config_mod.CONFIG_PATH != config_path:
        raise RuntimeError("target config was captured before the temporary path")

    import ingest

    import_order.append("ingest")

    import brief

    import_order.append("brief")

    import doctor

    import_order.append("doctor")

    import chroma_readonly

    import_order.append("chroma_readonly")
    import chroma_store
    import chroma_write_store
    import writer_census
    import agent_run_ledger

    import_order.append("agent_run_ledger")
    _log("target imports ready")

    target_paths = _assert_target_paths(
        target_root,
        {
            "ingest": ingest,
            "brief": brief,
            "doctor": doctor,
            "config": config_mod,
            "chroma_readonly": chroma_readonly,
            "chroma_store": chroma_store,
            "chroma_write_store": chroma_write_store,
            "writer_census": writer_census,
            "agent_run_ledger": agent_run_ledger,
        },
    )

    chroma_dir = Path(args.chroma_dir).resolve()
    writer_census.start_writer_census(
        chroma_root=chroma_dir,
        writer_gate_path=writer_root / "writer.lock",
        census_dir=writer_root / "census",
        now=datetime.now(timezone.utc) - timedelta(days=2),
    )
    import_baseline = rss_bytes_fn()
    started = time.monotonic()

    real_write_session = ingest.production_chroma_write_session
    real_writer_boundary = ingest.production_writer_boundary
    writer_calls: list[dict[str, str]] = []

    def hermetic_write_session(*, entrypoint: str, **kwargs):
        kwargs["config_path"] = config_path
        kwargs["lock_path"] = writer_root / "writer.lock"
        kwargs["attest_dir"] = writer_root / "attest"
        kwargs["census_dir"] = writer_root / "census"
        writer_calls.append({"kind": "write_session", "entrypoint": entrypoint})
        return real_write_session(entrypoint=entrypoint, **kwargs)

    def hermetic_writer_boundary(*, entrypoint: str, **kwargs):
        kwargs["lock_path"] = writer_root / "writer.lock"
        kwargs["attest_dir"] = writer_root / "attest"
        kwargs["census_dir"] = writer_root / "census"
        writer_calls.append({"kind": "writer_boundary", "entrypoint": entrypoint})
        return real_writer_boundary(entrypoint=entrypoint, **kwargs)

    units_before = chroma_readonly.collection_count(str(chroma_dir), "knowledge_units")

    probe_results: list[tuple[bool, str]] = []
    real_probe = doctor._exposure_window_probe
    failure_log = writer_root / "synthesis_failures.jsonl"

    def observed_probe(*probe_args, **probe_kwargs):
        result = real_probe(*probe_args, **probe_kwargs)
        probe_results.append(result)
        return result

    with ExitStack() as stack:
        stack.enter_context(patch.object(brief, "DEFAULT_BRIEF_PATH", brief_path))
        stack.enter_context(patch.object(doctor, "_standing_register_path", return_value=register_path))
        stack.enter_context(
            patch.object(agent_run_ledger, "DEFAULT_DATA_DIR", writer_root / "agent_runs")
        )
        stack.enter_context(patch.object(doctor, "_exposure_window_probe", side_effect=observed_probe))
        stack.enter_context(patch("ingest.summarize", return_value="e2e summary"))
        stack.enter_context(patch("ingest._distill_with_provenance", side_effect=_distill_stub))
        stack.enter_context(patch("ingest.ollama_embed", return_value=EMBED_VECTOR))
        stack.enter_context(patch.object(ingest, "_SYNTHESIS_FAIL_LOG", failure_log))
        stack.enter_context(patch("llm.summarize", return_value="e2e summary"))
        stack.enter_context(patch("llm.ollama_embed", return_value=EMBED_VECTOR))
        stack.enter_context(patch("distill.distill_with_response", side_effect=_distill_stub))
        stack.enter_context(patch("ingest.time.sleep"))
        stack.enter_context(patch("ingest.production_chroma_write_session", side_effect=hermetic_write_session))
        stack.enter_context(patch("ingest.production_writer_boundary", side_effect=hermetic_writer_boundary))
        stack.enter_context(
            patch(
                "brief._systemd_state",
                return_value="enabled/active",
            )
        )
        stack.enter_context(
            patch(
                "brief._mcp_registration",
                return_value={"cursor": "registered", "crush": "registered"},
            )
        )
        stack.enter_context(patch("brief._watch_process_memory", return_value=None))
        stack.enter_context(patch("brief._pending_decision_ingest", return_value=[]))
        _log("starting ingest.index")
        stats = ingest.index(
            force_file=str(transcript),
            verbose=False,
            force_reindex=True,
        )
        _log(f"ingest.index done: {stats}")

    elapsed = time.monotonic() - started
    units_after = chroma_readonly.collection_count(str(chroma_dir), "knowledge_units")

    if stats.get("files_processed", 0) < 1:
        failure_detail = failure_log.read_text(encoding="utf-8")[-1200:] if failure_log.is_file() else ""
        raise RuntimeError(
            f"ingest.index did not process transcript: {stats}; "
            f"temporary_failure_log_tail={failure_detail!r}"
        )
    if units_after <= units_before:
        raise RuntimeError(
            f"expected new units in temporary Chroma: before={units_before} after={units_after}"
        )
    if not brief_path.is_file() or brief_path.stat().st_size < 1:
        raise RuntimeError("brief refresh did not publish output")
    if not probe_results:
        raise RuntimeError("ingest.index did not execute the standing exposure probe")
    if not writer_calls:
        raise RuntimeError("ingest.index did not exercise the temporary writer gate")

    due, detail = probe_results[-1]
    probe_digest = hashlib.sha256(f"{due}|{detail}".encode()).hexdigest()

    for path in (
        writer_root / "writer.lock",
        writer_root / "attest",
        writer_root / "census",
    ):
        resolved = str(path.expanduser().resolve())
        prod_share = str((Path.home() / ".local/share/convmem").resolve())
        if resolved.startswith(prod_share):
            raise RuntimeError(f"writer path resolves into production: {resolved}")
    if not (writer_root / "writer.lock").is_file():
        raise RuntimeError("temporary writer lock was not created")
    if not (writer_root / "attest").is_dir():
        raise RuntimeError("temporary writer attestation directory was not created")
    census_events = writer_root / "census" / "session-events.jsonl"
    if not census_events.is_file() or not census_events.read_text(encoding="utf-8").strip():
        raise RuntimeError("temporary writer census did not record events")

    open_fd_paths = sorted(set(proc_fd_targets_fn()))
    for opened in open_fd_paths:
        if opened.startswith("/"):
            _require_temporary_path(Path(opened))

    emit_worker_json(
        {
            "status": "succeeded",
            "target_sha": args.target_sha,
            "harness_hash": args.harness_hash,
            "import_order": import_order,
            "import_baseline_rss_bytes": import_baseline,
            "peak_rss_bytes": peak_rss_bytes_fn(),
            "elapsed_seconds": round(elapsed, 3),
            "index_stats": stats,
            "units_before": units_before,
            "units_after": units_after,
            "probe_due": due,
            "probe_detail": detail,
            "probe_digest": probe_digest,
            "probe_call_count": len(probe_results),
            "writer_calls": writer_calls,
            "writer_paths": {
                "lock": str(writer_root / "writer.lock"),
                "attest": str(writer_root / "attest"),
                "census": str(census_events),
            },
            "brief_digest": hashlib.sha256(brief_path.read_bytes()).hexdigest(),
            "brief_bytes": brief_path.stat().st_size,
            "target_module_paths": target_paths,
            "opened_paths": open_fd_paths,
            "denied_paths": DENIED,
            "network_denied": NETWORK_DENIED,
            "transcript_sha256": hashlib.sha256(transcript.read_bytes()).hexdigest(),
        }
    )
    return denied_exit_code()


def main() -> int:
    harness_root = Path(__file__).resolve().parents[1]
    if str(harness_root) not in sys.path:
        sys.path.insert(0, str(harness_root))

    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--harness-hash", required=True)
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--chroma-dir", required=True)
    parser.add_argument("--writer-root", required=True)
    parser.add_argument("--brief-path", required=True)
    parser.add_argument("--register-path", required=True)
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--wiring-no-as-limit", action="store_true")
    args = parser.parse_args()

    from tests.watch_oom_memory_worker_shared import prepare_worker

    import_order = [
        "hermetic_guards_installed",
        "wiring_no_as_limit" if args.wiring_no_as_limit else "rlimit_as_2gib",
    ]
    prepare_worker(limit_as=not args.wiring_no_as_limit)
    try:
        return _dispatch(args, import_order)
    except Exception as exc:  # pylint: disable=broad-except
        from tests.watch_oom_memory_worker_shared import emit_worker_json
        from tests.watch_oom_hermetic_isolation import DENIED, NETWORK_DENIED

        emit_worker_json(
            {
                "status": "exited",
                "detail": str(exc),
                "import_order": import_order,
                "denied_paths": list(DENIED),
                "network_denied": list(NETWORK_DENIED),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
