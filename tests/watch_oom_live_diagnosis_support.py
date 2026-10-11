# pylint: disable=too-many-locals
"""Fixtures and fail-closed guards for issue #268 D1 scratch harness."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.watch_oom_exposure_index_e2e_support import (
    PathCanary,
    build_writable_fixture_seed,
    production_canary_paths,
    refresh_canary_stats,
    snapshot_canaries,
    write_e2e_config,
    write_synthetic_transcript,
)

_D1_INCIDENT_SOURCE_MARKER = (
    Path.home() / ".local/share/convmem/live-diag-incident-source.path"
)

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

MAX_TELEMETRY_BYTES = 512 * 1024
SAMPLE_INTERVAL_SECONDS = 0.25


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


def d1_extended_production_canary_paths() -> list[tuple[str, Path]]:
    """Handoff surfaces plus failure logs, locks, and optional incident source."""
    share = Path.home() / ".local/share/convmem"
    seen: set[str] = set()
    out: list[tuple[str, Path]] = []
    for surface, path in production_canary_paths():
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append((surface, path))
    for rel in (
        "index_failures.jsonl",
        "native_crash_failures.jsonl",
        "synthesis_failures.jsonl",
    ):
        path = share / rel
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(("failure_log", path))
    lock = share / "locks/chroma_writer_gate.lock"
    key = str(lock)
    if key not in seen:
        out.append(("writer_gate", lock))
    if _D1_INCIDENT_SOURCE_MARKER.is_file():
        raw = _D1_INCIDENT_SOURCE_MARKER.read_text(encoding="utf-8").strip()
        if raw:
            incident = Path(raw).expanduser()
            key = str(incident)
            if key not in seen:
                out.append(("incident_source", incident))
    return out


def snapshot_d1_parent_canaries() -> dict[str, PathCanary]:
    out: dict[str, PathCanary] = {}
    for surface, path in d1_extended_production_canary_paths():
        key = str(path)
        if not path.exists():
            out[key] = PathCanary(key, surface, False, None, None, None, None, None, None)
            continue
        stat = path.stat()
        sha = None
        if path.is_file():
            with path.open("rb") as handle:
                sha = hashlib.file_digest(handle, "sha256").hexdigest()
        out[key] = PathCanary(
            key,
            surface,
            True,
            stat.st_size,
            stat.st_mode,
            stat.st_mtime_ns,
            sha,
            stat.st_dev,
            stat.st_ino,
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
    from tests.watch_oom_exposure_index_e2e_support import PathCanary

    out: dict = {}
    for key, left in before.items():
        path = Path(key)
        if not path.is_file():
            out[key] = PathCanary(
                key, left.surface, False, None, None, None, None, None, None
            )
            continue
        stat = path.stat()
        with open_fn(path, "rb") as handle:
            sha = hashlib.file_digest(handle, "sha256").hexdigest()
        out[key] = PathCanary(
            key,
            left.surface,
            True,
            stat.st_size,
            stat.st_mode,
            stat.st_mtime_ns,
            sha,
            stat.st_dev,
            stat.st_ino,
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
        mount = subprocess.run(
            ["findmnt", "-n", "-o", "FSTYPE", "-T", str(scratch_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        fstype = mount.stdout.strip()
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
    config_path: Path | None = None,
) -> dict[str, str]:
    if not source_sha256 or len(source_sha256) != 64:
        raise ValueError("source_sha256 must be a 64-char hex digest")
    roots = json.dumps([str(scratch_root.resolve())])
    env = os.environ.copy()
    cfg = config_path or (scratch_root / "arm" / "config" / "config.toml")
    if not cfg.is_file():
        raise ValueError(f"scratch config missing: {cfg}")
    arm = scratch_root / "arm"
    worker_pid_path = arm / "worker.pid"
    inner_scope_marker = arm / "inner_scope_unit.txt"
    index_pid_path = arm / "index.pid"
    env.update(
        {
            "CONVMEM_CONFIG": str(cfg.resolve()),
            "CONVMEM_LIVE_DIAG_SCRATCH_ROOTS": roots,
            "CONVMEM_LIVE_DIAG_PHASE_PATH": str(phase_path),
            "CONVMEM_LIVE_DIAG_HERMETIC": "1",
            "CONVMEM_LIVE_DIAG_SOURCE_SHA256": source_sha256,
            "CONVMEM_LIVE_DIAG_TELEMETRY_PATH": str(telemetry_path),
            "CONVMEM_LIVE_DIAG_WORKER_PID_PATH": str(worker_pid_path),
            "CONVMEM_LIVE_DIAG_INNER_SCOPE_MARKER": str(inner_scope_marker),
            "CONVMEM_LIVE_DIAG_INDEX_PID_PATH": str(index_pid_path),
        }
    )
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
    phase_path = arm / "phases.jsonl"
    telemetry_path = arm / "telemetry.jsonl"
    backup_manifest = {
        "processed.json": hashlib.sha256(processed.read_bytes()).hexdigest(),
        "chroma/chroma.sqlite3": hashlib.sha256(
            (chroma_dir / "chroma.sqlite3").read_bytes()
        ).hexdigest(),
    }
    verify_backup_manifest(manifest=backup_manifest, corpus_root=arm / "seed")
    inner_scope_marker = arm / "inner_scope_unit.txt"
    index_pid_path = arm / "index.pid"
    return {
        "arm": arm,
        "scratch_root": tmp_root,
        "config_path": cfg_path,
        "source": source,
        "source_sha256": source_sha,
        "chroma_dir": chroma_dir,
        "processed": processed,
        "units_export": units_export,
        "brief_path": brief_path,
        "writer_root": writer_root,
        "register_path": Path(seed["register"]),
        "phase_path": phase_path,
        "telemetry_path": telemetry_path,
        "backup_manifest": backup_manifest,
        "production_canary_count": len(d1_extended_production_canary_paths()),
        "inner_scope_marker": inner_scope_marker,
        "index_pid_path": index_pid_path,
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


def snapshot_production_canaries_for_parent() -> dict:
    return snapshot_d1_parent_canaries()


def assert_parent_production_canaries_unchanged(before: dict) -> None:
    after = refresh_d1_parent_canaries(before)
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
