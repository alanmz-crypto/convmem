# pylint: disable=too-many-locals
"""Fixtures and fail-closed guards for issue #268 D1 scratch harness."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from tests.watch_oom_exposure_index_e2e_support import (
    PathCanary,
    build_writable_fixture_seed,
    production_canary_paths,
    refresh_canary_stats,
    snapshot_canaries,
    write_e2e_config,
)
from tests.watch_oom_mount_probe import scratch_filesystem_type

PHASE_ORDER = (
    "watch_skip_hash_begin",
    "watch_skip_hash_admit",
    "watch_worker_bootstrap",
    "index_child_bootstrap",
    "index_hash_begin",
    "index_hash_done",
    "source_row_snapshot",
    "parse_chunks_begin",
    "parse_chunks_done",
    "per_chunk_build_begin",
    "per_chunk_chroma_write",
    "processed_commit",
    "brief_refresh_begin",
    "brief_refresh_done",
    "export_compaction_begin",
    "export_compaction_done",
)

# 900s @ 250ms, dual boundaries + index RSS rows (~320 bytes/row) with headroom.
MAX_TELEMETRY_BYTES = 10 * 1024 * 1024
SAMPLE_INTERVAL_SECONDS = 0.25

# Explicit D1 cgroup caps (also written to scratch config [d1_harness]).
D1_OUTER_MEMORY_BYTES = 256 * 1024**2
D1_INNER_MEMORY_BYTES = 2 * 1024**3
D1_BWRAP_ACTIVE_ENV = "CONVMEM_LIVE_DIAG_BWRAP_ACTIVE"


def d1_worker_enter_bwrap_or_exit(
    *,
    argv: list[str],
    scratch_root: Path,
    source_path: Path,
    repo_root: Path,
) -> None:
    """Hermetic D1 worker routes must run under bwrap (RO root, writable scratch, unshared net)."""
    if os.environ.get("CONVMEM_LIVE_DIAG_HERMETIC") != "1":
        return
    from tests.watch_oom_live_diagnosis_bwrap import (
        bwrap_available,
        build_bwrap_command,
        verify_d1_kernel_envelope,
    )

    if os.environ.get(D1_BWRAP_ACTIVE_ENV) == "1":
        verify_d1_kernel_envelope(
            scratch_root=scratch_root,
            source_path=source_path,
            repo_root=repo_root,
        )
        return

    if not bwrap_available():
        raise RuntimeError("d1_bwrap_unavailable")
    cmd = build_bwrap_command(
        [sys.executable, *argv],
        scratch_root=scratch_root.resolve(),
        source_path=source_path.resolve(),
        repo_root=repo_root.resolve(),
    )
    env = os.environ.copy()
    env[D1_BWRAP_ACTIVE_ENV] = "1"
    completed = subprocess.run(cmd, env=env, check=False)
    raise SystemExit(completed.returncode)


def append_d1_harness_limits(config_path: Path) -> None:
    block = (
        "\n[d1_harness]\n"
        f"outer_memory_bytes = {D1_OUTER_MEMORY_BYTES}\n"
        f"inner_memory_bytes = {D1_INNER_MEMORY_BYTES}\n"
    )
    config_path.write_text(config_path.read_text(encoding="utf-8") + block, encoding="utf-8")


def read_d1_harness_limits(config_path: Path) -> tuple[int, int]:
    if not config_path.is_file():
        raise RuntimeError("d1_harness_config_missing")
    section = tomllib.loads(config_path.read_text(encoding="utf-8")).get("d1_harness")
    if not isinstance(section, dict):
        raise RuntimeError("d1_harness_limits_missing")
    try:
        outer = int(section["outer_memory_bytes"])
        inner = int(section["inner_memory_bytes"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("d1_harness_limits_invalid") from exc
    if outer <= 0 or inner <= 0:
        raise RuntimeError("d1_harness_limits_invalid")
    if outer != D1_OUTER_MEMORY_BYTES or inner != D1_INNER_MEMORY_BYTES:
        raise RuntimeError("d1_harness_limits_fixture_mismatch")
    return outer, inner


@contextmanager
def overlay_live_diagnosis_env(env: dict[str, str]) -> Iterator[None]:
    """Temporarily apply harness env for parent postchecks; always restore."""
    keys = [k for k in env if k.startswith("CONVMEM_LIVE_DIAG_") or k == "CONVMEM_CONFIG"]
    saved: dict[str, str | None] = {k: os.environ.get(k) for k in keys}
    try:
        for key in keys:
            os.environ[key] = env[key]
        yield
    finally:
        for key in keys:
            prior = saved[key]
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior


def d1_parent_teardown_postcheck(
    *,
    env: dict[str, str],
    source_path: Path,
    denial_path: Path,
    incident_source_canary: Path,
    canaries_before: dict,
) -> None:
    """Fail-closed parent postchecks (denials, frozen source, production canaries)."""
    assert_denial_events_empty(denial_path)
    inner_ack = Path(env["CONVMEM_LIVE_DIAG_INNER_ACK_PATH"])
    inner_final = Path(env["CONVMEM_LIVE_DIAG_INNER_FINAL_PATH"])
    if inner_final.is_file():
        inner_ack.write_text("ack\n", encoding="ascii")
    with overlay_live_diagnosis_env(env):
        from live_diagnosis import assert_source_identity_postcheck

        assert_source_identity_postcheck(source_path)
    assert_parent_production_canaries_unchanged(
        canaries_before,
        incident_source=incident_source_canary,
    )


@dataclass(frozen=True)
class ScratchCanary:
    rel: str
    sha256: str
    size: int
    mtime_ns: int


def scratch_canary_manifest(root: Path) -> dict[str, ScratchCanary]:
    """Content-and-mtime manifest for mutable scratch surfaces only."""
    out: dict[str, ScratchCanary] = {}
    for rel in (
        "processed.json",
        "knowledge_units.jsonl",
        "chroma/chroma.sqlite3",
        "brief.md",
        "writer/writer.lock",
    ):
        path = root / rel
        if not path.is_file():
            continue
        st = path.stat()
        out[rel] = ScratchCanary(
            rel=rel,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            size=st.st_size,
            mtime_ns=st.st_mtime_ns,
        )
    return out


def assert_scratch_canaries_unchanged(
    before: dict[str, ScratchCanary],
    after: dict[str, ScratchCanary],
) -> None:
    if before != after:
        raise RuntimeError(f"scratch canary drift: before={before} after={after}")


def verify_backup_manifest(
    *,
    manifest: dict[str, str],
    corpus_root: Path,
    expected_fingerprint: str | None = None,
) -> None:
    """Fail closed when a declared backup layout does not match disk."""
    if not manifest:
        raise RuntimeError("backup_manifest_missing")
    observed: dict[str, str] = {}
    for rel, digest in sorted(manifest.items()):
        path = corpus_root / rel
        if not path.is_file():
            raise RuntimeError(f"backup_file_missing:{rel}")
        observed[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed[rel] != digest:
            raise RuntimeError(f"backup_hash_mismatch:{rel}")
    if expected_fingerprint:
        payload = json.dumps(observed, sort_keys=True).encode()
        fp = hashlib.sha256(payload).hexdigest()
        if fp != expected_fingerprint:
            raise RuntimeError("backup_fingerprint_mismatch")


def freeze_source_copy(path: Path) -> str:
    """Return sha256 and deny write-open via mode bits (D2-shaped, test-only)."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return digest


def assert_source_readonly(path: Path, expected_sha256: str) -> None:
    with path.open("rb") as handle:
        observed = hashlib.file_digest(handle, "sha256").hexdigest()
    if observed != expected_sha256:
        raise RuntimeError("source_hash_drift")
    if path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeError("source_not_readonly")


def assert_production_canaries_unchanged() -> list[str]:
    before = snapshot_canaries()
    after = refresh_canary_stats(before)
    return production_canary_drift_lines(before, after)


def d1_mandatory_canary_paths(incident_source: Path) -> list[tuple[str, Path]]:
    """Full production touchpoint census plus mandatory incident-source path."""
    share = Path.home() / ".local/share/convmem"
    seen: set[str] = set()
    out: list[tuple[str, Path]] = []

    def add(surface: str, path: Path) -> None:
        key = str(path)
        if key in seen:
            return
        seen.add(key)
        out.append((surface, path))

    for surface, path in production_canary_paths():
        add(surface, path)
    for rel in (
        "index_failures.jsonl",
        "native_crash_failures.jsonl",
        "synthesis_failures.jsonl",
    ):
        add("failure_log", share / rel)
    add("writer_gate", share / "locks/chroma_writer_gate.lock")
    chroma_root = share / "chroma"
    if chroma_root.is_dir():
        for path in sorted(chroma_root.rglob("*")):
            if path.is_file():
                add("chroma_tree", path)
    for rel in ("writer/attest", "writer/census", "agent_runs"):
        candidate = share / rel
        if candidate.exists():
            if candidate.is_file():
                add("agent_run_state", candidate)
            else:
                for path in sorted(candidate.rglob("*")):
                    if path.is_file():
                        add("agent_run_state", path)
    add("incident_source", incident_source.expanduser())
    return out


def load_external_backup_manifest(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise RuntimeError("backup_manifest_unavailable")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("backup_manifest_unreadable") from exc
    if not isinstance(payload, dict) or not payload:
        raise RuntimeError("backup_manifest_missing")
    manifest: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise RuntimeError("backup_manifest_invalid")
        manifest[key] = value
    return manifest


def supply_external_backup_manifest_file(
    manifest_path: Path,
    *,
    entries: dict[str, str],
) -> Path:
    """Author manifest out-of-band from prepare_scratch_arm (external supply)."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(entries, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def assert_denial_events_empty(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raise RuntimeError(f"denial_event_recorded:{line[:200]}")


def snapshot_d1_parent_canaries(incident_source: Path) -> dict[str, PathCanary]:
    out: dict[str, PathCanary] = {}
    for surface, path in d1_mandatory_canary_paths(incident_source):
        key = str(path)
        if not path.exists():
            out[key] = PathCanary(key, surface, False, None, None, None, None, None, None)
            continue
        st = path.stat()
        sha = None
        if path.is_file():
            with path.open("rb") as handle:
                sha = hashlib.file_digest(handle, "sha256").hexdigest()
        out[key] = PathCanary(
            key,
            surface,
            True,
            st.st_size,
            st.st_mode,
            st.st_mtime_ns,
            sha,
            st.st_dev,
            st.st_ino,
        )
    return out


def refresh_d1_parent_canaries(before: dict[str, PathCanary]) -> dict[str, PathCanary]:
    return refresh_canary_stats(before)


def production_canary_drift_lines(before: dict, after: dict) -> list[str]:
    drift: list[str] = []
    for key, left in before.items():
        right = after.get(key)
        if right != left:
            drift.append(f"{left.surface} {key}")
    return drift


def refresh_canary_stats_unguarded(
    before: dict,
    *,
    open_fn,
) -> dict:
    """Re-stat production canaries using an unguarded open (after hermetic guards)."""
    out: dict = {}
    for key, left in before.items():
        path = Path(key)
        if not path.is_file():
            out[key] = PathCanary(
                key, left.surface, False, None, None, None, None, None, None
            )
            continue
        st = path.stat()
        with open_fn(path, "rb") as handle:
            sha = hashlib.file_digest(handle, "sha256").hexdigest()
        out[key] = PathCanary(
            key,
            left.surface,
            True,
            st.st_size,
            st.st_mode,
            st.st_mtime_ns,
            sha,
            st.st_dev,
            st.st_ino,
        )
    return out


def production_writer_lock_path() -> Path:
    return Path.home() / ".local/share/convmem/locks/chroma_writer_gate.lock"


def assert_no_production_writer_collision() -> None:
    """Read-only probe: never open the production lock for write."""
    lock = production_writer_lock_path()
    if not lock.is_file():
        return
    st_before = lock.stat()
    import fcntl

    fd = os.open(str(lock), os.O_RDONLY | os.O_CLOEXEC)
    acquired = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except BlockingIOError as exc:
            raise RuntimeError("production_writer_lock_held") from exc
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    st_after = lock.stat()
    if (
        st_before.st_size,
        st_before.st_mtime_ns,
        st_before.st_mode,
    ) != (st_after.st_size, st_after.st_mtime_ns, st_after.st_mode):
        raise RuntimeError("production_writer_lock_mutated")


def assert_scratch_disk_backed(scratch_dir: Path) -> None:
    try:
        fstype = scratch_filesystem_type(scratch_dir, timeout=10.0)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("scratch_mount_unknown") from exc
    if not fstype or fstype == "tmpfs":
        raise RuntimeError(f"scratch_not_disk_backed:{fstype}")


def arm_diagnosis_env(
    *,
    scratch_root: Path,
    phase_path: Path,
    telemetry_path: Path,
    source_sha256: str,
    source_size: int,
    source_mtime_ns: int,
    config_path: Path | None = None,
    gate_auto_go: bool = True,
) -> dict[str, str]:
    if not source_sha256 or len(source_sha256) != 64:
        raise ValueError("source_sha256 must be a 64-char hex digest")
    roots = json.dumps([str(scratch_root.resolve())])
    env = os.environ.copy()
    env.pop(D1_BWRAP_ACTIVE_ENV, None)
    from tests.watch_oom_live_diagnosis_bwrap import D1_PARENT_NETNS_ENV, net_namespace_id

    parent_ns = net_namespace_id(os.getpid())
    cfg = config_path or (scratch_root / "arm" / "config" / "config.toml")
    if not cfg.is_file():
        raise ValueError(f"scratch config missing: {cfg}")
    arm = scratch_root / "arm"
    worker_pid_path = arm / "worker.pid"
    inner_scope_marker = arm / "inner_scope_unit.txt"
    index_pid_path = arm / "index.pid"
    denial_path = arm / "denials.jsonl"
    gate_path = arm / "index_gate.txt"
    inner_final_path = arm / "inner_final.json"
    inner_ack_path = arm / "inner_ack.txt"
    scope_ready_path = arm / "inner_scope_ready.txt"
    supervisor_pid_path = arm / "supervisor.pid"
    net_probe_outer_path = arm / "net_probe_outer.json"
    net_probe_inner_path = arm / "net_probe_inner.json"
    env.update(
        {
            "CONVMEM_CONFIG": str(cfg.resolve()),
            "CONVMEM_LIVE_DIAG_SCRATCH_ROOTS": roots,
            "CONVMEM_LIVE_DIAG_PHASE_PATH": str(phase_path),
            "CONVMEM_LIVE_DIAG_HERMETIC": "1",
            "CONVMEM_LIVE_DIAG_SOURCE_SHA256": source_sha256,
            "CONVMEM_LIVE_DIAG_SOURCE_SIZE": str(source_size),
            "CONVMEM_LIVE_DIAG_SOURCE_MTIME_NS": str(source_mtime_ns),
            "CONVMEM_LIVE_DIAG_TELEMETRY_PATH": str(telemetry_path),
            "CONVMEM_LIVE_DIAG_WORKER_PID_PATH": str(worker_pid_path),
            "CONVMEM_LIVE_DIAG_INNER_SCOPE_MARKER": str(inner_scope_marker),
            "CONVMEM_LIVE_DIAG_INDEX_PID_PATH": str(index_pid_path),
            "CONVMEM_LIVE_DIAG_DENIAL_PATH": str(denial_path),
            "CONVMEM_LIVE_DIAG_INDEX_GATE_PATH": str(gate_path),
            "CONVMEM_LIVE_DIAG_INNER_FINAL_PATH": str(inner_final_path),
            "CONVMEM_LIVE_DIAG_INNER_ACK_PATH": str(inner_ack_path),
            "CONVMEM_LIVE_DIAG_SCOPE_READY_PATH": str(scope_ready_path),
            "CONVMEM_LIVE_DIAG_SUPERVISOR_PID_PATH": str(supervisor_pid_path),
            "CONVMEM_LIVE_DIAG_NET_PROBE_OUTER_PATH": str(net_probe_outer_path),
            "CONVMEM_LIVE_DIAG_NET_PROBE_INNER_PATH": str(net_probe_inner_path),
            "CONVMEM_LIVE_DIAG_PHASE_LINES": "0",
        }
    )
    if parent_ns:
        env[D1_PARENT_NETNS_ENV] = parent_ns
    if gate_auto_go:
        from live_diagnosis import GATE_SPAWN_GRANTED

        env["CONVMEM_LIVE_DIAG_SYNTHETIC_FAST"] = "1"
        gate_path.write_text(f"{GATE_SPAWN_GRANTED}\n", encoding="ascii")
    brief = scratch_root / "arm" / "brief.md"
    writer_root = scratch_root / "arm" / "writer"
    if brief.parent.exists():
        env["CONVMEM_LIVE_DIAG_BRIEF_PATH"] = str(brief)
    if writer_root.parent.exists():
        env["CONVMEM_LIVE_DIAG_WRITER_ROOT"] = str(writer_root)
    register = scratch_root / "arm" / "seed" / "standing-checks-register.json"
    if register.is_file():
        env["CONVMEM_LIVE_DIAG_REGISTER_PATH"] = str(register)
    return env


def build_prefix_transcript(path: Path, *, lines: int) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(lines):
        rows.append(
            json.dumps(
                {
                    "role": "user" if i % 2 == 0 else "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"synthetic prefix line {i} for D1 harness",
                            }
                        ]
                    },
                },
                sort_keys=True,
            )
        )
    payload = "\n".join(rows) + "\n"
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode()).hexdigest()


def prepare_scratch_arm(tmp_root: Path, *, corpus_n: int = 8, prefix_lines: int = 2) -> dict[str, Any]:
    tmp_root.mkdir(parents=True, exist_ok=True)
    assert_scratch_disk_backed(tmp_root)
    arm = tmp_root / "arm"
    arm.mkdir(parents=True, exist_ok=True)
    seed = build_writable_fixture_seed(arm / "seed", corpus_n)
    chroma_dir = Path(seed["chroma_dir"])
    processed = Path(seed["processed"])
    inventory = Path(seed["inventory"])
    source = Path(seed["source"])
    build_prefix_transcript(source, lines=prefix_lines)
    source_sha = freeze_source_copy(source)
    units_export = arm / "knowledge_units.jsonl"
    units_export.write_text("", encoding="utf-8")
    brief_path = arm / "brief.md"
    writer_root = arm / "writer"
    writer_root.mkdir(parents=True, exist_ok=True)
    cfg_path = write_e2e_config(
        arm / "config",
        chroma_dir=chroma_dir,
        inventory=inventory,
        processed=processed,
        units_export=units_export,
        transcript=source,
    )
    append_d1_harness_limits(cfg_path)
    phase_path = arm / "phases.jsonl"
    telemetry_path = arm / "telemetry.jsonl"
    source_stat = source.stat()
    incident_source_canary = arm / "incident_source_canary.jsonl"
    incident_source_canary.write_text("", encoding="utf-8")
    inner_scope_marker = arm / "inner_scope_unit.txt"
    index_pid_path = arm / "index.pid"
    backup_manifest_path = arm / "external_backup_manifest.json"
    return {
        "arm": arm,
        "scratch_root": tmp_root,
        "config_path": cfg_path,
        "source": source,
        "source_sha256": source_sha,
        "source_size": source_stat.st_size,
        "source_mtime_ns": source_stat.st_mtime_ns,
        "incident_source_canary": incident_source_canary,
        "backup_manifest_path": backup_manifest_path,
        "chroma_dir": chroma_dir,
        "processed": processed,
        "units_export": units_export,
        "brief_path": brief_path,
        "writer_root": writer_root,
        "register_path": Path(seed["register"]),
        "phase_path": phase_path,
        "telemetry_path": telemetry_path,
        "inner_scope_marker": inner_scope_marker,
        "index_pid_path": index_pid_path,
        "denial_path": arm / "denials.jsonl",
        "d1_outer_memory_bytes": D1_OUTER_MEMORY_BYTES,
        "d1_inner_memory_bytes": D1_INNER_MEMORY_BYTES,
    }


def read_phases(path: Path) -> list[str]:
    if not path.is_file():
        return []
    phases: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        phases.append(json.loads(line)["phase"])
    return phases


def snapshot_production_canaries_for_parent(incident_source: Path) -> dict:
    return snapshot_d1_parent_canaries(incident_source)


def assert_parent_production_canaries_unchanged(
    before: dict, *, incident_source: Path
) -> None:
    after = snapshot_d1_parent_canaries(incident_source)
    drift = production_canary_drift_lines(before, after)
    if drift:
        raise RuntimeError(f"production_canary_drift:{drift}")


def bounded_telemetry_append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, sort_keys=True) + "\n"
    if path.is_file() and path.stat().st_size + len(line) > MAX_TELEMETRY_BYTES:
        raise RuntimeError("telemetry_log_full")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
