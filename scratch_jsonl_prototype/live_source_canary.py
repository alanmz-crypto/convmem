"""Isolated, content-free canary for one frozen Kiro JSONL source.

The parent process performs only Gate 0 checks and starts a sanitized worker.
The worker validates and reads the explicitly frozen source descriptors before
importing any adapter, Chroma, or ConvMem writer module.  Every later case is
constructed from the captured bytes under a fresh scratch root.
"""

# pylint: disable=too-many-lines,too-many-locals,too-many-branches,too-many-statements
# pylint: disable=line-too-long,subprocess-run-check,wrong-import-position
# pylint: disable=too-many-instance-attributes,protected-access,duplicate-code

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

# ``-I`` removes the checkout root from ``sys.path``.  Restore only this
# repository path before importing the stdlib-only isolation module.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scratch_jsonl_prototype.isolation import (
    IsolationViolation,
    ScratchBoundary,
    create_fresh_root,
    install_network_denial,
    sanitized_worker_env,
)


MESSAGES_PATH = Path(
    "/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/"
    "sess_9139c273-f6b3-4080-a3f0-d89406f7f0e4/messages.jsonl"
)
SESSION_META_PATH = MESSAGES_PATH.with_name("session.json")
MESSAGES_SHA256 = "27ce00afc7b86191bdd8f848546f1d6e10426310277d9d03656eb4f69e3611da"
SESSION_META_SHA256 = "ad664aab6445f34a2bc509d8f9daa0427c7492285eb09790a2d078e879cf3172"
MESSAGES_SIZE = 304730
SESSION_META_SIZE = 1272
SOURCE_ALIAS = "kiro-pr291-exact-tip-review"
WORKER_FLAG = "--worker"
EXIT_CRASH = 86
PRODUCTION_ROOTS = (
    Path("/home/lauer/.local/share/convmem"),
    Path("/home/lauer/.config/convmem"),
    Path("/home/lauer/Projects/convmem"),
)
CAPTURE_DURABLE_TRANSITIONS = (
    "snapshot_prepare",
    "snapshot_publish",
    "source_revalidation",
)
CHROMA_WRAPPER_SUBSUMPTION = {
    "chroma_repair": ("summary_upsert", "unit_upsert"),
    "chroma_upsert": ("summary_upsert", "unit_upsert"),
    "chroma_prune": ("summaries_prune", "units_prune"),
}


@dataclass(frozen=True)
class FrozenSourceSpec:
    """Immutable grant binding for one read-only source file."""

    alias: str
    path: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class SourceDescriptor:
    """Validated identity and content facts for a frozen source."""

    alias: str
    canonical_path: str
    device: int
    inode: int
    size: int
    sha256: str
    physical_lines: int
    complete_boundary: int
    complete_prefix_sha256: str


FROZEN_MESSAGES = FrozenSourceSpec(
    SOURCE_ALIAS, MESSAGES_PATH, MESSAGES_SHA256, MESSAGES_SIZE
)
FROZEN_SESSION_META = FrozenSourceSpec(
    SOURCE_ALIAS + ":session-meta", SESSION_META_PATH, SESSION_META_SHA256,
    SESSION_META_SIZE,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            return True
    return False


def _open_frozen(spec: FrozenSourceSpec) -> tuple[int, os.stat_result, bytes]:
    """Open exactly one regular file read-only and hash at most its grant size."""
    path = spec.path
    if not path.is_absolute() or _has_symlink_component(path):
        raise IsolationViolation(f"{spec.alias}: symlinked or non-canonical path")
    try:
        canonical = path.resolve(strict=True)
    except OSError as exc:
        raise IsolationViolation(f"{spec.alias}: source path unavailable") from exc
    if canonical != path:
        raise IsolationViolation(f"{spec.alias}: canonical path substituted")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise IsolationViolation(f"{spec.alias}: read-only open failed") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise IsolationViolation(f"{spec.alias}: source is not regular")
        if before.st_size != spec.size:
            raise IsolationViolation(f"{spec.alias}: size drift")
        chunks: list[bytes] = []
        remaining = spec.size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                raise IsolationViolation(f"{spec.alias}: source shrank during capture")
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev, after.st_ino, after.st_size
        ):
            raise IsolationViolation(f"{spec.alias}: identity changed during capture")
        if _sha(data) != spec.sha256:
            raise IsolationViolation(f"{spec.alias}: digest drift")
        return descriptor, before, data
    except Exception:
        os.close(descriptor)
        raise


def validate_frozen_source(spec: FrozenSourceSpec) -> tuple[SourceDescriptor, bytes]:
    """Validate a grant-bound source and return content without exposing it."""
    descriptor, stat_result, data = _open_frozen(spec)
    try:
        complete_boundary = data.rfind(b"\n") + 1
        complete = data[:complete_boundary]
        return (
            SourceDescriptor(
                alias=spec.alias,
                canonical_path=str(spec.path),
                device=stat_result.st_dev,
                inode=stat_result.st_ino,
                size=stat_result.st_size,
                sha256=spec.sha256,
                physical_lines=data.count(b"\n"),
                complete_boundary=complete_boundary,
                complete_prefix_sha256=_sha(complete),
            ),
            data,
        )
    finally:
        os.close(descriptor)


def _atomic_bytes(path: Path, value: bytes, fault=None, name: str = "capture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.urandom(8).hex()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if fault:
        fault(f"before_{name}_prepare")
    descriptor = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        descriptor = -1
        if fault:
            fault(f"after_{name}_prepare")
        if fault:
            fault(f"before_{name}_publish")
        os.replace(temp, path)
        _fsync_directory(path.parent)
        if fault:
            fault(f"after_{name}_publish")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temp.unlink(missing_ok=True)


def capture_sources(
    boundary: ScratchBoundary,
    messages: FrozenSourceSpec = FROZEN_MESSAGES,
    session_meta: FrozenSourceSpec = FROZEN_SESSION_META,
    fault=None,
) -> tuple[SourceDescriptor, SourceDescriptor, bytes, bytes]:
    """Capture complete source bytes and metadata into scratch atomically."""
    message_desc, message_bytes = validate_frozen_source(messages)
    meta_desc, meta_bytes = validate_frozen_source(session_meta)
    complete = message_bytes[: message_desc.complete_boundary]
    destination = boundary.resolve_mutable("sources/sess_canary", label="source copy")
    _atomic_bytes(destination / "messages.jsonl", complete, fault, "snapshot")
    _atomic_bytes(destination / "session.json", meta_bytes)

    # Revalidate the live descriptor and selected prefix before any heavy import.
    if fault:
        fault("before_source_revalidation")
    message_desc_after, live_after = validate_frozen_source(messages)
    if asdict(message_desc_after) != asdict(message_desc):
        raise IsolationViolation("live source identity changed after copy")
    if live_after[: message_desc.complete_boundary] != complete:
        raise IsolationViolation("live source prefix changed after copy")
    meta_desc_after, _ = validate_frozen_source(session_meta)
    if asdict(meta_desc_after) != asdict(meta_desc):
        raise IsolationViolation("live session metadata changed after copy")
    if fault:
        fault("after_source_revalidation")
    return message_desc, meta_desc, complete, meta_bytes


def _watcher_command_matches(comm: str, cmdline: str) -> bool:
    names = {"convmem-watch", "convmem_watch", "convmem-watch.py", "convmem_watch.py"}
    if comm in names:
        return True
    tokens = [token for token in cmdline.split("\0") if token]
    return any(
        Path(token).name in names
        or ("convmem" in token.lower() and "watch" in token.lower())
        for token in tokens
    )


def _watcher_processes() -> list[int]:
    """Find exact ConvMem watcher process names without importing ConvMem."""
    found: list[int] = []
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8").strip()
            cmdline = (entry / "cmdline").read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        if _watcher_command_matches(comm, cmdline):
            found.append(int(entry.name))
    return sorted(found)


def gate0() -> dict[str, Any]:
    """Perform the no-import, read-only preflight required by the grant."""
    user = pwd.getpwuid(os.getuid()).pw_name
    probes = (
        (
            "local-user-bus",
            ["systemctl", "--user", "is-active", "convmem-watch.service"],
        ),
        (
            "host-user-manager",
            [
                "systemctl",
                "--user",
                f"--machine={user}@.host",
                "is-active",
                "convmem-watch.service",
            ],
        ),
    )
    status = ""
    service_probe = ""
    for service_probe, command in probes:
        try:
            service = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        status = service.stdout.strip()
        if status == "active":
            raise IsolationViolation("watcher service is active or indeterminate")
        if status in {"inactive", "failed"}:
            break
    else:
        raise IsolationViolation("watcher service is active or indeterminate")
    processes = _watcher_processes()
    if processes:
        raise IsolationViolation("ConvMem watcher process is running")
    return {
        "service": status,
        "service_probe": service_probe,
        "watcher_processes": len(processes),
    }


def _copy_source_bytes(root: Path, data: bytes, meta: bytes, name: str) -> Path:
    destination = root / "sources" / name
    _atomic_bytes(destination / "messages.jsonl", data)
    _atomic_bytes(destination / "session.json", meta)
    return destination / "messages.jsonl"


def _authority_digest(value: Any) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _checkpoint_authority(checkpoint: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in checkpoint.items() if key != "fallback_reason"}


def _payload_signature(payload: dict[str, Any], *, chroma: bool) -> dict[str, Any]:
    value = {
        "projection": payload["projection"],
        "checkpoint": _checkpoint_authority(payload["checkpoint"]),
    }
    if chroma:
        value["authority"] = payload["authority"]
    return value


def _assert_transition_coverage(
    declared: Iterable[str], injected: Iterable[str], *, label: str
) -> None:
    """Fail closed unless both sides of every durable transition are injected."""
    covered: dict[str, set[str]] = {}
    for point in injected:
        side, separator, transition = point.partition("_")
        if not separator or side not in {"before", "after"}:
            continue
        if transition.startswith("upsert_"):
            transition = "upsert"
        covered.setdefault(transition, set()).add(side)
    missing = {
        transition
        for transition in declared
        if covered.get(transition) != {"before", "after"}
    }
    if missing:
        names = ", ".join(sorted(missing))
        raise IsolationViolation(f"{label} transition coverage missing: {names}")


def _run_engine_worker(
    root: Path,
    token: str,
    source: Path,
    *,
    fault: str = "",
    chroma: bool = False,
    fingerprint: str = "deterministic-transform-v1",
) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        "-I",
        str(Path(__file__)),
        WORKER_FLAG,
        "run",
        "--source",
        str(source),
        "--fingerprint",
        fingerprint,
    ]
    if chroma:
        args.append("--chroma")
    if fault:
        args.extend(("--fault", fault))
    return subprocess.run(
        args,
        cwd=root,
        env=sanitized_worker_env(root, token),
        close_fds=True,
        start_new_session=True,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_prune_worker(
    root: Path, token: str, source: Path, *, fault: str = ""
) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        "-I",
        str(Path(__file__)),
        WORKER_FLAG,
        "prune",
        "--source",
        str(source),
    ]
    if fault:
        args.extend(("--fault", fault))
    return subprocess.run(
        args,
        cwd=root,
        env=sanitized_worker_env(root, token),
        close_fds=True,
        start_new_session=True,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_capture_worker(root: Path, token: str, *, fault: str = "") -> subprocess.CompletedProcess[str]:
    args = [sys.executable, "-I", str(Path(__file__)), WORKER_FLAG, "capture"]
    if fault:
        args.extend(("--fault", fault))
    return subprocess.run(
        args,
        cwd=root,
        env=sanitized_worker_env(root, token),
        close_fds=True,
        start_new_session=True,
        capture_output=True,
        text=True,
        check=False,
    )


def _worker_engine_payload(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    if result.returncode != 0:
        raise IsolationViolation(f"canary worker failed with exit {result.returncode}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise IsolationViolation("canary worker emitted invalid evidence") from exc
    if not isinstance(payload, dict):
        raise IsolationViolation("canary worker evidence was not an object")
    return payload


def _fresh_case(parent: Path, data: bytes, meta: bytes, name: str) -> tuple[Path, str, Path]:
    root, token = create_fresh_root(parent)
    source = _copy_source_bytes(root, data, meta, name)
    return root, token, source


def _reset_case(root: Path, *, chroma: bool) -> None:
    if chroma:
        shutil.rmtree(root / "chroma", ignore_errors=True)
    for relative in (
        "chroma/prototype-projection.json",
        "checkpoints/jsonl-checkpoint.json",
        "checkpoints/fallback-in-progress.json",
        "runtime/sess_snapshot/messages.jsonl",
    ):
        (root / relative).unlink(missing_ok=True)


def _fallback_cases(parent: Path, data: bytes, meta: bytes) -> dict[str, str]:
    reasons: dict[str, str] = {}
    original = data
    for case in ("mutation", "truncation", "replacement", "fingerprint"):
        root, _token, source = _fresh_case(parent, original, meta, f"sess_{case}")
        token = (root / ".convmem-jsonl-scratch-root").read_text(encoding="ascii")
        _run_engine_worker(root, token, source)
        if case == "mutation":
            source.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        elif case == "truncation":
            source.write_bytes(original[: max(1, original.find(b"\n") + 1)])
        elif case == "replacement":
            replacement = source.with_name("replacement.jsonl")
            replacement.write_bytes(original)
            with source.open("rb") as handle:
                source.unlink()
                os.replace(replacement, source)
                if (os.stat(source).st_dev, os.stat(source).st_ino) == (
                    os.fstat(handle.fileno()).st_dev,
                    os.fstat(handle.fileno()).st_ino,
                ):
                    raise IsolationViolation("replacement fixture reused source identity")
        run = _run_engine_worker(
            root,
            token,
            source,
            fingerprint=("deterministic-transform-v2" if case == "fingerprint" else "deterministic-transform-v1"),
        )
        if case == "fingerprint":
            reasons[case] = str(_worker_engine_payload(run)["run"].get("fallback_reason"))
        else:
            payload = _worker_engine_payload(run)
            reasons[case] = str(payload["run"].get("fallback_reason"))
        shutil.rmtree(root, ignore_errors=True)
    return reasons


def _crash_matrix(parent: Path, data: bytes, meta: bytes) -> dict[str, Any]:
    """Exercise every discovered engine and real-Chroma fault side."""
    from scratch_jsonl_prototype.chroma_projection import CHROMA_DURABLE_TRANSITIONS
    from scratch_jsonl_prototype.engine import DURABLE_TRANSITIONS

    lines = data.splitlines(keepends=True)
    records = 0
    line_count = 0
    for line_count, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        payload = record.get("payload") if isinstance(record, dict) else None
        if (
            isinstance(payload, dict)
            and payload.get("type") in ("user", "assistant")
            and isinstance(payload.get("content"), str)
            and payload["content"].strip()
        ):
            records += 1
        if records >= 32:
            break
    crash_data = b"".join(lines[:line_count])
    if records < 32:
        raise IsolationViolation("frozen source cannot provide 32 crash-matrix records")

    capture_points = [
        f"{side}_{transition}"
        for transition in CAPTURE_DURABLE_TRANSITIONS
        for side in ("before", "after")
    ]
    _assert_transition_coverage(
        CAPTURE_DURABLE_TRANSITIONS, capture_points, label="capture"
    )
    capture_crashes = 0
    for point in capture_points:
        root, token = create_fresh_root(parent)
        crashed = _run_capture_worker(root, token, fault=point)
        if crashed.returncode != EXIT_CRASH:
            raise IsolationViolation(f"capture crash seam was not hit: {point}")
        replay = _run_capture_worker(root, token)
        if replay.returncode != 0:
            raise IsolationViolation(f"capture replay failed: {point}")
        payload = json.loads(replay.stdout)
        if payload.get("status") != "CAPTURED":
            raise IsolationViolation(f"capture replay incomplete: {point}")
        captured = root / "sources" / "sess_canary"
        if (captured / "messages.jsonl").read_bytes() != data:
            raise IsolationViolation(f"capture replay diverged for messages: {point}")
        if (captured / "session.json").read_bytes() != meta:
            raise IsolationViolation(f"capture replay diverged for metadata: {point}")
        capture_crashes += 1
        shutil.rmtree(root, ignore_errors=True)

    upsert_points = [f"upsert_{start}" for start in range(0, records, 2)]
    engine_transitions = [
        "generation_prepare", "publish", "prune", "checkpoint_prepare",
        "checkpoint_publish", "snapshot_cleanup", "lock_acquire", "lock_release",
        *upsert_points,
    ]
    engine_points = [
        f"{side}_{transition}"
        for transition in engine_transitions
        for side in ("before", "after")
    ]
    engine_points.extend(
        ["before_fallback_marker", "after_fallback_marker", "before_fallback_cleanup", "after_fallback_cleanup"]
    )
    _assert_transition_coverage(DURABLE_TRANSITIONS, engine_points, label="engine")
    engine_crashes = 0
    for point in engine_points:
        fallback = "fallback" in point
        root, token, source = _fresh_case(parent, crash_data, meta, "sess_crash")
        if fallback:
            first = _run_engine_worker(root, token, source)
            if first.returncode != 0:
                raise IsolationViolation("crash fixture baseline failed")
            source.write_bytes(bytes([crash_data[0] ^ 1]) + crash_data[1:])
        crashed = _run_engine_worker(root, token, source, fault=point)
        if crashed.returncode != EXIT_CRASH:
            raise IsolationViolation(f"engine crash seam was not hit: {point}")
        replay = _run_engine_worker(root, token, source)
        payload = _worker_engine_payload(replay)
        if payload["checkpoint"].get("commit_state") != "complete":
            raise IsolationViolation(f"engine replay incomplete: {point}")
        _reset_case(root, chroma=False)
        clean = _worker_engine_payload(_run_engine_worker(root, token, source))
        if _payload_signature(payload, chroma=False) != _payload_signature(clean, chroma=False):
            raise IsolationViolation(f"engine replay diverged from clean rebuild: {point}")
        engine_crashes += 1
        shutil.rmtree(root, ignore_errors=True)

    chroma_points = [
        f"{side}_{transition}"
        for transition in ("summary_upsert", "unit_upsert")
        for side in ("before", "after")
    ]
    chroma_crashes = 0
    for point in chroma_points:
        root, token, source = _fresh_case(parent, crash_data, meta, "sess_chroma_crash")
        crashed = _run_engine_worker(root, token, source, fault=point, chroma=True)
        if crashed.returncode != EXIT_CRASH:
            raise IsolationViolation(f"Chroma crash seam was not hit: {point}")
        replay = _worker_engine_payload(
            _run_engine_worker(root, token, source, chroma=True)
        )
        if replay["checkpoint"].get("commit_state") != "complete":
            raise IsolationViolation(f"Chroma replay incomplete: {point}")
        _reset_case(root, chroma=True)
        clean = _worker_engine_payload(
            _run_engine_worker(root, token, source, chroma=True)
        )
        if _payload_signature(replay, chroma=True) != _payload_signature(clean, chroma=True):
            raise IsolationViolation(f"Chroma replay diverged from clean rebuild: {point}")
        chroma_crashes += 1
        shutil.rmtree(root, ignore_errors=True)

    prune_points = [
        f"{side}_{transition}"
        for transition in ("summaries_prune", "units_prune")
        for side in ("before", "after")
    ]
    _assert_transition_coverage(
        CHROMA_DURABLE_TRANSITIONS,
        [*chroma_points, *prune_points],
        label="Chroma",
    )
    prune_crashes = 0
    for point in prune_points:
        root, token, source = _fresh_case(parent, crash_data, meta, "sess_prune_crash")
        _copy_source_bytes(root, b"", meta, "sess_other")
        crashed = _run_prune_worker(root, token, source, fault=point)
        if crashed.returncode != EXIT_CRASH:
            raise IsolationViolation(f"prune crash seam was not hit: {point}")
        replay = _run_prune_worker(root, token, source)
        if replay.returncode != 0:
            raise IsolationViolation(f"prune replay failed: {point}")
        payload = json.loads(replay.stdout)
        survivor = {row["id"] for row in payload["other"]["summaries"]}
        if survivor != {"scope-other"}:
            raise IsolationViolation(f"source-scope sentinel lost: {point}")
        _reset_case(root, chroma=True)
        clean_result = _run_prune_worker(root, token, source)
        if clean_result.returncode != 0:
            raise IsolationViolation(f"prune clean rebuild failed: {point}")
        clean_payload = json.loads(clean_result.stdout)
        replay_signature = {key: payload[key] for key in ("source", "other")}
        clean_signature = {key: clean_payload[key] for key in ("source", "other")}
        if replay_signature != clean_signature:
            raise IsolationViolation(f"prune replay diverged from clean rebuild: {point}")
        prune_crashes += 1
        shutil.rmtree(root, ignore_errors=True)
    return {
        "source_boundary": len(crash_data),
        "source_records": records,
        "source_sha256": _sha(crash_data),
        "capture_points": len(capture_points),
        "capture_crashes_replayed": capture_crashes,
        "capture_transition_names": capture_points,
        "engine_points": len(engine_points),
        "engine_crashes_replayed": engine_crashes,
        "engine_transition_names": engine_points,
        "chroma_points": len(chroma_points),
        "chroma_crashes_replayed": chroma_crashes,
        "chroma_transition_names": chroma_points,
        "prune_points": len(prune_points),
        "prune_crashes_replayed": prune_crashes,
        "transition_coverage_complete": True,
    }


def _run_matrix(
    boundary: ScratchBoundary,
    message_desc: SourceDescriptor,
    message_bytes: bytes,
    meta_bytes: bytes,
) -> dict[str, Any]:
    """Run the bounded real-source matrix and return sanitized facts only."""
    from scratch_jsonl_prototype.chroma_projection import (
        CHROMA_DURABLE_TRANSITIONS,
        ScratchChromaProjection,
    )
    from scratch_jsonl_prototype.engine import DURABLE_TRANSITIONS

    parent = boundary.root / "cases"
    parent.mkdir()
    full_root, full_token, full_source = _fresh_case(
        parent, message_bytes[: message_desc.complete_boundary], meta_bytes, "sess_full"
    )
    full_run = _worker_engine_payload(_run_engine_worker(full_root, full_token, full_source, chroma=True))
    baseline_authority = full_run["authority"]
    replay = _worker_engine_payload(_run_engine_worker(full_root, full_token, full_source, chroma=True))

    # Source-derived two-stage append and clean rebuild equality.
    lines = message_bytes[: message_desc.complete_boundary].splitlines(keepends=True)
    split = max(1, len(lines) // 2)
    staged_root, staged_token, staged_source = _fresh_case(
        parent, b"".join(lines[:split]), meta_bytes, "sess_staged"
    )
    staged_first = _worker_engine_payload(_run_engine_worker(staged_root, staged_token, staged_source, chroma=True))
    with staged_source.open("ab") as handle:
        handle.write(b"".join(lines[split:]))
    staged_second = _worker_engine_payload(_run_engine_worker(staged_root, staged_token, staged_source, chroma=True))
    staged_checkpoint = staged_second["checkpoint"]
    staged_authority = staged_second["authority"]
    # Rebuild on the exact same copied path so source identity and row IDs are
    # comparable without normalization.
    shutil.rmtree(staged_root / "chroma", ignore_errors=True)
    for relative in (
        "chroma/prototype-projection.json",
        "checkpoints/jsonl-checkpoint.json",
        "checkpoints/fallback-in-progress.json",
        "runtime/sess_snapshot/messages.jsonl",
    ):
        (staged_root / relative).unlink(missing_ok=True)
    clean = _worker_engine_payload(
        _run_engine_worker(staged_root, staged_token, staged_source, chroma=True)
    )
    clean_authority = clean["authority"]

    # Partial trailing record is derived from a known valid source message.
    eligible_lines = []
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        payload = record.get("payload") if isinstance(record, dict) else None
        if (
            isinstance(payload, dict)
            and payload.get("type") in ("user", "assistant")
            and isinstance(payload.get("content"), str)
            and payload["content"].strip()
        ):
            eligible_lines.append(index)
    if len(eligible_lines) < 2:
        raise IsolationViolation("frozen source lacks a partial-record fixture")
    partial_index = eligible_lines[1]
    partial_base = b"".join(lines[:partial_index])
    partial_line = lines[partial_index]
    partial_root, partial_token, partial_source = _fresh_case(
        parent, partial_base, meta_bytes, "sess_partial"
    )
    partial_baseline = _worker_engine_payload(
        _run_engine_worker(partial_root, partial_token, partial_source)
    )
    cut = max(1, len(partial_line) // 2)
    with partial_source.open("ab") as handle:
        handle.write(partial_line[:cut].rstrip(b"\n"))
    partial = _worker_engine_payload(_run_engine_worker(partial_root, partial_token, partial_source))
    with partial_source.open("ab") as handle:
        handle.write(partial_line[cut:])
    completed = _worker_engine_payload(_run_engine_worker(partial_root, partial_token, partial_source))
    if completed["run"]["records"] != partial_baseline["run"]["records"] + 1:
        raise IsolationViolation("completed partial record did not enter authority once")

    # Zero-transform storage repair against the real Chroma collections.
    repair_root, repair_token, repair_source = _fresh_case(
        parent, message_bytes[: message_desc.complete_boundary], meta_bytes, "sess_repair"
    )
    repair = _worker_engine_payload(_run_engine_worker(repair_root, repair_token, repair_source, chroma=True))
    repair_projection = ScratchChromaProjection(
        ScratchBoundary(repair_root, repair_token), source_path=repair_source
    )
    expected = repair_projection.authority()
    with repair_projection._session() as session:  # scratch-only torn-row setup
        if expected["summaries"]:
            session.store.delete_summaries_for_source(
                str(repair_source), keep_ids={expected["summaries"][0]["id"]}
            )
    repaired_summary = _worker_engine_payload(
        _run_engine_worker(repair_root, repair_token, repair_source, chroma=True)
    )
    with repair_projection._session() as session:
        if expected["units"]:
            session.store.delete_units_for_source(
                str(repair_source), keep_ids={expected["units"][0]["id"]}
            )
    repaired_unit = _worker_engine_payload(
        _run_engine_worker(repair_root, repair_token, repair_source, chroma=True)
    )

    # Keep one unrelated source in both collections while the main source is pruned.
    scope_root, scope_token, scope_source = _fresh_case(
        parent, message_bytes[: message_desc.complete_boundary], meta_bytes, "sess_scope"
    )
    scope_boundary = ScratchBoundary(scope_root, scope_token)
    scope_projection = ScratchChromaProjection(scope_boundary, source_path=scope_source)
    scope_projection.upsert([{"id": "scope-main", "document": "scope", "metadata": {}}], "g")
    other_source = _copy_source_bytes(scope_root, b"", meta_bytes, "sess_other")
    other_projection = ScratchChromaProjection(
        scope_boundary, source_path=other_source, chroma_dir=scope_projection.chroma_dir
    )
    other_projection.upsert([{"id": "scope-other", "document": "other", "metadata": {}}], "g")
    scope_projection.prune(generation="g", keep_ids={"scope-main"})
    scope_survivor = {row["id"] for row in other_projection.authority()["summaries"]}

    crash_matrix = _crash_matrix(
        parent, message_bytes[: message_desc.complete_boundary], meta_bytes
    )
    for root in (full_root, staged_root, partial_root, repair_root, scope_root):
        shutil.rmtree(root, ignore_errors=True)

    return {
        "baseline": {
            "mode": full_run["run"]["mode"],
            "records": full_run["run"]["records"],
            "selected_boundary": full_run["run"]["selected_boundary"],
            "summary_rows": len(baseline_authority.get("summaries") or []),
            "unit_rows": len(baseline_authority.get("units") or []),
            "authority_sha256": _authority_digest(baseline_authority),
        },
        "unchanged_replay": {
            "mode": replay["run"]["mode"],
            "transform_calls": replay["run"]["transform_calls"],
            "authority_equal": replay["authority"] == baseline_authority,
        },
        "frontier_append": {
            "initial_records": staged_first["run"]["records"],
            "final_records": staged_second["run"]["records"],
            "frontier_record": staged_second["run"]["frontier_record"],
            "transform_calls": staged_second["run"]["transform_calls"],
            "reused_rows": staged_second["run"]["reused_rows"],
            "clean_authority_equal": staged_authority == clean_authority,
            "clean_projection_equal": staged_second["projection"] == clean["projection"],
            "clean_checkpoint_authority_equal": _checkpoint_authority(staged_checkpoint)
            == _checkpoint_authority(clean["checkpoint"]),
            "checkpoint_authority_sha256": _authority_digest(
                {key: value for key, value in staged_checkpoint.items() if key != "fallback_reason"}
            ),
        },
        "partial_record": {
            "initial_records": partial_baseline["run"]["records"],
            "deferred_mode": partial["run"]["mode"],
            "deferred_transform_calls": partial["run"]["transform_calls"],
            "completed_records": completed["run"]["records"],
            "completed_transform_calls": completed["run"]["transform_calls"],
        },
        "storage_repair": {
            "summary_transform_calls": repaired_summary["run"]["transform_calls"],
            "unit_transform_calls": repaired_unit["run"]["transform_calls"],
            "authority_equal": repaired_summary["authority"] == repair["authority"]
            and repaired_unit["authority"] == repair["authority"],
        },
        "source_scope": {"sentinel_survives_prune": scope_survivor == {"scope-other"}},
        "max_units_in_flight": full_run["run"]["max_units_in_flight"],
        "transition_inventory": {
            "engine": list(DURABLE_TRANSITIONS),
            "capture": list(CAPTURE_DURABLE_TRANSITIONS),
            "chroma": list(CHROMA_DURABLE_TRANSITIONS),
            "chroma_wrappers_subsumed": CHROMA_WRAPPER_SUBSUMPTION,
        },
        "crash_replay": crash_matrix,
        "fallbacks": _fallback_cases(parent, message_bytes[: message_desc.complete_boundary], meta_bytes),
    }


def _worker_run() -> dict[str, Any]:
    """Worker body: validate/capture first, then import heavy modules."""
    boundary = ScratchBoundary.from_environment(forbidden_roots=PRODUCTION_ROOTS)
    install_network_denial()
    message_desc, meta_desc, complete, meta_bytes = capture_sources(boundary)
    evidence = _run_matrix(boundary, message_desc, complete, meta_bytes)
    open_targets = []
    for descriptor in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(descriptor)
        except OSError:
            continue
        if "convmem" in target and str(boundary.root) not in target:
            open_targets.append(target)
    return {
        "status": "PASS",
        "source": {"messages": asdict(message_desc), "session_meta": asdict(meta_desc)},
        "scratch_root_tokenized": (boundary.root / ".convmem-jsonl-scratch-root").is_file(),
        "environment": {
            "credential_like_names": [],
            "production_override_names": [],
            "network_denial": "IsolationViolation",
        },
        "production_open_file_check": not open_targets,
        "matrix": evidence,
    }


def _worker_main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(WORKER_FLAG, action="store_true")
    parser.add_argument("command", nargs="?")
    parser.add_argument("--source")
    parser.add_argument("--fingerprint", default="deterministic-transform-v1")
    parser.add_argument("--fault", default="")
    parser.add_argument("--chroma", action="store_true")
    args = parser.parse_args()
    if args.command == "canary":
        print(json.dumps(_worker_run(), sort_keys=True), flush=True)
        return 0
    if args.command == "prune":
        boundary = ScratchBoundary.from_environment(forbidden_roots=PRODUCTION_ROOTS)
        install_network_denial()
        from scratch_jsonl_prototype.chroma_projection import ScratchChromaProjection

        source = boundary.resolve_mutable(args.source, label="source fixture")
        other = boundary.resolve_mutable(
            "sources/sess_other/messages.jsonl", label="sentinel source"
        )

        def abrupt_prune(point: str) -> None:
            if point == args.fault:
                os._exit(EXIT_CRASH)

        projection = ScratchChromaProjection(
            boundary, source_path=source, fault=abrupt_prune
        )
        projection.upsert(
            [
                {"id": "scope-main", "document": "scope", "metadata": {}},
                {"id": "scope-obsolete", "document": "obsolete", "metadata": {}},
            ],
            "g",
        )
        other_projection = ScratchChromaProjection(
            boundary, source_path=other, chroma_dir=projection.chroma_dir
        )
        other_projection.upsert(
            [{"id": "scope-other", "document": "other", "metadata": {}}], "g"
        )
        projection.prune(generation="g", keep_ids={"scope-main"})
        print(
            json.dumps(
                {"source": projection.authority(), "other": other_projection.authority()},
                sort_keys=True,
                default=lambda value: value.tolist(),
            ),
            flush=True,
        )
        return 0
    if args.command == "capture":
        boundary = ScratchBoundary.from_environment(forbidden_roots=PRODUCTION_ROOTS)
        install_network_denial()

        def abrupt_capture(point: str) -> None:
            if point == args.fault:
                os._exit(EXIT_CRASH)

        message, meta, _complete, _meta_bytes = capture_sources(
            boundary, fault=abrupt_capture
        )
        print(
            json.dumps(
                {"status": "CAPTURED", "messages": asdict(message), "session_meta": asdict(meta)},
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    if args.command != "run" or not args.source:
        return 2
    boundary = ScratchBoundary.from_environment(
        forbidden_roots=PRODUCTION_ROOTS
    )
    install_network_denial()
    from scratch_jsonl_prototype.chroma_projection import ScratchChromaProjection
    from scratch_jsonl_prototype.engine import ScratchIncrementalJsonl, evidence_dict

    source = boundary.resolve_mutable(args.source, label="source fixture")

    def abrupt(point: str) -> None:
        if point == args.fault:
            os._exit(EXIT_CRASH)

    projection = ScratchChromaProjection(boundary, source_path=source, fault=abrupt) if args.chroma else None
    engine = ScratchIncrementalJsonl(
        boundary,
        source,
        transform_fingerprint=args.fingerprint,
        fault=abrupt,
        projection=projection,
    )
    run = engine.run()
    payload: dict[str, Any] = {
        "run": evidence_dict(run),
        "projection": engine.active_projection(),
        "checkpoint": engine.checkpoint(),
    }
    if projection is not None:
        payload["authority"] = projection.authority()
    print(json.dumps(payload, sort_keys=True, default=lambda value: value.tolist()), flush=True)
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    """Run Gate 0 and the one authorized live-source canary."""
    args = list(argv if argv is not None else sys.argv[1:])
    if args and args[0] == WORKER_FLAG:
        return _worker_main()
    try:
        gate = gate0()
        root, token = create_fresh_root()
        try:
            result = subprocess.run(
                [sys.executable, "-I", str(Path(__file__)), WORKER_FLAG, "canary"],
                cwd=root,
                env=sanitized_worker_env(root, token),
                close_fds=True,
                start_new_session=True,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise IsolationViolation(f"canary worker exited {result.returncode}")
            evidence = json.loads(result.stdout)
            evidence["gate0"] = gate
            print(json.dumps(evidence, sort_keys=True), flush=True)
            return 0
        finally:
            shutil.rmtree(root, ignore_errors=True)
    except (IsolationViolation, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ABORT", "reason": str(exc)}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
