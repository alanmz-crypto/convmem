# pylint: disable=wrong-import-position,protected-access,too-many-locals
"""Subprocess worker: legacy watch flush_path → index child (issue #268 D1)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


def _require_scratch(path: Path, scratch_root: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(scratch_root.resolve()):
        raise RuntimeError(f"path outside scratch: {resolved}")


def _write_worker_pid() -> None:
    raw = os.environ.get("CONVMEM_LIVE_DIAG_WORKER_PID_PATH", "").strip()
    if not raw:
        return
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{os.getpid()}\n", encoding="ascii")


def _dispatch(args: argparse.Namespace) -> int:
    from live_diagnosis import (
        bootstrap_watch_worker,
        hermetic_denial_snapshot,
        init_index_gate_pending,
        mark,
    )
    from tests.watch_oom_live_diagnosis_support import (
        assert_source_readonly,
        load_external_backup_manifest,
        verify_backup_manifest,
    )

    scratch_root = Path(args.scratch_root).resolve()
    config_path = Path(args.config_path).resolve()
    source = Path(args.source).resolve()
    brief_path = Path(args.brief_path).resolve()
    writer_root = Path(args.writer_root).resolve()
    register_path = Path(args.register_path).resolve()
    phase_path = Path(args.phase_path).resolve()
    incident_canary = Path(args.incident_source_canary_path).resolve()
    manifest_path = Path(args.backup_manifest_path).resolve()

    for role in (
        config_path,
        source,
        brief_path,
        writer_root,
        register_path,
        phase_path,
        incident_canary,
        manifest_path,
    ):
        _require_scratch(role, scratch_root)

    os.environ["CONVMEM_CONFIG"] = str(config_path)
    # Config must be set in main() before bwrap re-exec and any config import.
    os.environ["CONVMEM_LIVE_DIAG_SOURCE_SIZE"] = str(args.source_size)
    os.environ["CONVMEM_LIVE_DIAG_SOURCE_MTIME_NS"] = str(args.source_mtime_ns)
    _write_worker_pid()
    bootstrap_watch_worker()

    manifest = load_external_backup_manifest(manifest_path)
    verify_backup_manifest(manifest=manifest, corpus_root=scratch_root / "arm" / "seed")
    assert_source_readonly(source, args.source_sha256)

    init_index_gate_pending()

    import watch

    with ExitStack() as stack:
        if args.mode == "injected_kill" and not args.cgroup_enforced:
            import subprocess as subprocess_mod

            original_popen = subprocess_mod.Popen

            def killing_popen(cmd, **kwargs):
                proc = original_popen(cmd, **kwargs)
                if args.kill_delay_ms > 0:
                    time.sleep(args.kill_delay_ms / 1000.0)
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                return proc

            stack.enter_context(patch("subprocess.Popen", side_effect=killing_popen))

        inner_marker_raw = os.environ.get("CONVMEM_LIVE_DIAG_INNER_SCOPE_MARKER", "").strip()
        if inner_marker_raw:
            inner_unit = f"convmem-live-diag-index-{uuid.uuid4().hex}.scope"
            marker_path = Path(inner_marker_raw)
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_text(f"{inner_unit}\n", encoding="ascii")
            os.environ["CONVMEM_LIVE_DIAG_INNER_SCOPE_UNIT"] = inner_unit
        os.environ["CONVMEM_LIVE_DIAG_SOURCE_PATH"] = str(source)

        mark("watch_route_start", mode=args.mode)
        started = time.monotonic()
        try:
            result = watch.flush_path(str(source), verbose=False, use_subprocess=True)
        except (OSError, RuntimeError, ValueError) as exc:
            mark("watch_route_error", error=type(exc).__name__)
            payload = {
                "status": "blocked" if args.mode == "injected_kill" else "failed",
                "error": type(exc).__name__,
                "error_detail": str(exc)[:500],
                "elapsed_seconds": round(time.monotonic() - started, 3),
                **hermetic_denial_snapshot(),
            }
            json.dump(payload, sys.stdout)
            sys.stdout.write("\n")
            return 0 if args.mode == "injected_kill" else 1

    phases = [
        json.loads(line)["phase"]
        for line in phase_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    payload = {
        "status": "succeeded",
        "mode": args.mode,
        "flush_result": result,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "phases": phases,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        **hermetic_denial_snapshot(),
    }
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    return 0


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("prefix_route", "injected_kill"), required=True)
    parser.add_argument("--scratch-root", required=True)
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--source-size", type=int, required=True)
    parser.add_argument("--source-mtime-ns", type=int, required=True)
    parser.add_argument("--incident-source-canary-path", required=True)
    parser.add_argument("--backup-manifest-path", required=True)
    parser.add_argument("--chroma-dir", required=True)
    parser.add_argument("--brief-path", required=True)
    parser.add_argument("--writer-root", required=True)
    parser.add_argument("--register-path", required=True)
    parser.add_argument("--phase-path", required=True)
    parser.add_argument("--kill-delay-ms", type=int, default=50)
    parser.add_argument("--cgroup-enforced", action="store_true")
    parser.add_argument("--cgroup-ready", type=Path)
    args = parser.parse_args()

    if args.cgroup_enforced != (args.cgroup_ready is not None):
        parser.error("--cgroup-enforced requires --cgroup-ready, and vice versa")

    os.environ["CONVMEM_CONFIG"] = str(Path(args.config_path).resolve())
    from tests.watch_oom_live_diagnosis_support import d1_worker_enter_bwrap_or_exit

    d1_worker_enter_bwrap_or_exit(
        argv=sys.argv,
        scratch_root=Path(args.scratch_root),
        source_path=Path(args.source),
        repo_root=root,
    )

    if args.cgroup_enforced:
        from tests.watch_oom_cgroup_runner import wait_for_parent_ready, worker_limit_claim

        wait_for_parent_ready(args.cgroup_ready)
        worker_limit_claim(int(os.environ.get("CONVMEM_LIVE_DIAG_MEMORY_MAX", str(256 * 1024**2))))

    return _dispatch(args)


if __name__ == "__main__":
    raise SystemExit(main())
