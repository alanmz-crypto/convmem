"""Live exact-resource P2 runtime for the JSONL production canary.

This module owns the p2-exact-resource-v2 contract: side-effect-free Gate 0,
separately authorized preparation, one-stage transitions, and live evidence.
It must not import tests, pytest, or fake providers.
"""

# pylint: disable=too-many-lines,too-many-locals,too-many-branches,too-many-statements
# pylint: disable=too-many-instance-attributes

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import struct
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Protocol

from chroma_store import SUMMARIES, UNITS
from incremental_jsonl import CallCounters
from incremental_jsonl_canary import (
    ABSENT_DIGEST,
    APPEND_MAX_MESSAGES,
    BASELINE_MAX_MESSAGES,
    BASELINE_MIN_MESSAGES,
    CALL_CEILINGS_WHOLE,
    CRASH_EXIT,
    P2_LIVE_CAPABILITY_MODE,
    STABLE_READ_COUNT,
    STABLE_READ_MIN_SPAN_S,
    ZERO_DIGEST,
    CanaryGrant,
    CanaryRefused,
    ProductionCanaryBoundary,
    ResourceIdentityGrant,
    ServingVisibilityProbe,
    _atomic_json,
    _fsync_directory,
    _has_symlink_component,
    _sha256_bytes,
    _sha256_file,
    assert_not_reused,
    build_allowlisted_child_env,
    canary_coordinator,
    canary_writer_scope,
    capture_rollback_capsule,
    chunk_starts_for_count,
    gate0_watcher_probe,
    install_call_budget_guard,
    is_p2_live_grant,
    restore_rollback_capsule,
    validate_append_profile,
    validate_two_chunk_profile,
    verify_persistent_config_false_false,
    write_canary_overlay,
    write_evidence,
)
from incremental_jsonl_canary_network import install_p2_network_policy  # pylint: disable=unused-import
from incremental_jsonl_isolation import terminate_process_group

LIVE_EVIDENCE_SCHEMA = "convmem/jsonl-production-canary-evidence-exact-resource-live-v1"
LIVE_EVIDENCE_NAME = "p2-exact-resource-live-evidence.json"
STAGE_RECEIPT_NAME = "p2-stage-receipt.json"
COUNTER_LEDGER_NAME = "p2-call-ledger.json"
LIVE_WORKER = Path(__file__).with_name("incremental_jsonl_canary_live_worker.py")

LIVE_STAGE_ORDER = (
    "gate0-pass",
    "prepared",
    "t3-initial-complete",
    "waiting-for-external-append-1",
    "t4-append-complete",
    "waiting-for-external-append-2",
    "t5-fault-1-complete",
    "t5-fault-2-complete",
    "t5-fault-3-complete",
    "t5-fault-4-complete",
    "t5-fault-5-complete",
    "t6-evidence-frozen",
)
FAULT_STAGE = {
    "summary_upsert": "t5-fault-1-complete",
    "unit_upsert": "t5-fault-2-complete",
    "units_prune": "t5-fault-3-complete",
    "checkpoint_publish": "t5-fault-4-complete",
    "dedupe_reconcile": "t5-fault-5-complete",
}
EMBEDDING_MAX_ULP = 1


class ProviderInvoker(Protocol):
    """Production-owned provider interface; tests supply doubles."""

    def summarize(self, text: str, **kwargs: Any) -> Any: ...
    def distill(self, text: str, **kwargs: Any) -> Any: ...
    def embed(self, text: str, **kwargs: Any) -> Any: ...


@dataclass
class LiveGate0Hooks:
    """Injectable Gate 0 probes. Defaults are real grant-bound checks."""

    watcher_probe: Callable[[], dict[str, str]] | None = None
    process_census: Callable[[], dict[str, str]] | None = None
    service_status: Callable[[], dict[str, str]] | None = None
    writer_census: Callable[[ProductionCanaryBoundary], dict[str, str]] | None = None
    model_manifest: Callable[[CanaryGrant], dict[str, str]] | None = None
    network_self_test: Callable[[CanaryGrant], dict[str, str]] | None = None
    restic_identifier: Callable[[CanaryGrant], dict[str, str]] | None = None
    zero_adoption: Callable[[ProductionCanaryBoundary, CanaryGrant], dict[str, str]] | None = None


@dataclass
class StageReceipt:
    nonce: str
    grant_digest: str
    stage: str
    next_stage: str
    capsule_digest: str = ZERO_DIGEST
    source_identity: dict[str, Any] = field(default_factory=dict)
    unrelated_manifest_digest: str = ZERO_DIGEST
    call_counters: dict[str, int] = field(default_factory=dict)
    append_identities: list[str] = field(default_factory=list)
    faults_completed: list[str] = field(default_factory=list)
    recovery_dispositions: list[str] = field(default_factory=list)
    artifact_identities: dict[str, Any] = field(default_factory=dict)
    receipt_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("receipt_sha256", None)
        return payload


def capture_path_identity(path: Path, role: str, owner_uid: int) -> ResourceIdentityGrant:
    """Record uid/mode/device/inode without following symlinks."""
    resolved = path if path.is_absolute() else path.resolve(strict=False)
    if _has_symlink_component(resolved):
        raise CanaryRefused("canary_grant_identities", f"symlink in {role}")
    if not resolved.exists():
        return ResourceIdentityGrant(
            role=role,
            path=str(resolved),
            uid=owner_uid,
            mode=0,
            device=0,
            inode=0,
            file_type="absent",
        )
    stat_result = resolved.lstat()
    if stat.S_ISLNK(stat_result.st_mode):
        raise CanaryRefused("canary_grant_identities", f"{role} is a symlink")
    file_type = "dir" if stat.S_ISDIR(stat_result.st_mode) else "file"
    return ResourceIdentityGrant(
        role=role,
        path=str(resolved),
        uid=int(stat_result.st_uid),
        mode=int(stat.S_IMODE(stat_result.st_mode)),
        device=int(stat_result.st_dev),
        inode=int(stat_result.st_ino),
        file_type=file_type,
    )


def stage_receipt_path(grant: CanaryGrant) -> Path:
    return Path(grant.evidence_dir) / STAGE_RECEIPT_NAME


def call_ledger_path(grant: CanaryGrant) -> Path:
    return Path(grant.evidence_dir) / COUNTER_LEDGER_NAME


def validate_p2_live_grant(
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    code_revision: str,
) -> None:
    """Fail-closed validation for p2-exact-resource-v2 grants."""
    if not is_p2_live_grant(grant):
        raise CanaryRefused("canary_mode", "not a live P2 exact-resource grant")
    digest = _sha256_bytes(grant.digest_payload())
    if digest != expected_sha256.lower():
        raise CanaryRefused("canary_grant_digest", "grant SHA-256 mismatch")
    if grant.code_revision != code_revision:
        raise CanaryRefused("canary_grant_revision", "code revision mismatch")
    try:
        expires = datetime.fromisoformat(grant.expires_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CanaryRefused("canary_grant_expiry", "invalid expires_at") from exc
    if expires <= datetime.now(timezone.utc):
        raise CanaryRefused("canary_grant_expired", "grant expired")
    if grant.persistent_config is None or grant.restic is None or grant.owner_uid is None:
        raise CanaryRefused("canary_grant_live_fields", "live bindings missing")
    if grant.restic.require_current_local_day is not True:
        raise CanaryRefused("canary_grant_restic", "require_current_local_day must be true")
    if len(grant.restic.snapshot_id) != 64:
        raise CanaryRefused("canary_grant_restic", "snapshot_id must be a full 64-char hex id")
    if grant.rollback.expected_digest != ZERO_DIGEST:
        raise CanaryRefused(
            "canary_grant_capsule",
            "un-captured capsule digest must be the zero sentinel",
        )
    required_identity_roles = {
        "source",
        "metadata",
        "overlay",
        "evidence_dir",
        "capsule",
        "persistent_config",
        *{item.role for item in grant.resources},
    }
    present = {item.role for item in grant.resource_identities}
    missing = required_identity_roles - present
    if missing:
        raise CanaryRefused(
            "canary_grant_identities",
            f"missing identity roles: {sorted(missing)}",
        )


def _open_nofollow_readonly(path: Path) -> tuple[int, os.stat_result]:
    if _has_symlink_component(path):
        raise CanaryRefused("canary_gate0_source", f"symlink in path: {path}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        stat_result = os.fstat(descriptor)
        return descriptor, stat_result
    except Exception:
        os.close(descriptor)
        raise


def _stable_read_fd(descriptor: int, size: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        block = os.read(descriptor, remaining)
        if not block:
            break
        chunks.append(block)
        remaining -= len(block)
    return b"".join(chunks)


def _descriptor_source_binding(grant: CanaryGrant, *, allow_append: bool = False) -> dict[str, Any]:
    from adapters.kiro_session_jsonl import parse_complete_prefix

    path = Path(grant.source.path)
    descriptor, stat_result = _open_nofollow_readonly(path)
    try:
        if not stat.S_ISREG(stat_result.st_mode):
            raise CanaryRefused("canary_gate0_source", "source is not regular")
        if stat_result.st_dev != grant.source.device or stat_result.st_ino != grant.source.inode:
            raise CanaryRefused("canary_source_identity", "source identity mismatch")
        if allow_append:
            if stat_result.st_size < grant.source.size:
                raise CanaryRefused("canary_source_identity", "source truncated after baseline")
        elif stat_result.st_size != grant.source.size:
            raise CanaryRefused("canary_source_identity", "source identity mismatch")
        raw = _stable_read_fd(descriptor, stat_result.st_size)
        if len(raw) != stat_result.st_size:
            raise CanaryRefused("canary_source_identity", "source size changed during read")
        prefix = raw[: grant.source.complete_boundary]
        if _sha256_bytes(prefix) != grant.source.prefix_sha256:
            raise CanaryRefused("canary_gate0_baseline", "prefix digest mismatch")
        view = parse_complete_prefix(str(path), raw=raw)
    finally:
        os.close(descriptor)
    count = len(view.messages)
    if allow_append and stat_result.st_size > grant.source.size:
        validate_append_profile(count)
    else:
        if count < BASELINE_MIN_MESSAGES or count > BASELINE_MAX_MESSAGES:
            raise CanaryRefused("canary_gate0_baseline", f"accepted messages {count} outside 61-109")
        if view.complete_boundary != grant.source.complete_boundary:
            raise CanaryRefused("canary_gate0_baseline", "complete boundary mismatch")
        if view.prefix_sha256 != grant.source.prefix_sha256:
            raise CanaryRefused("canary_gate0_baseline", "prefix digest mismatch")
    return {"accepted_messages": count, "complete_boundary": view.complete_boundary}


def _descriptor_metadata_binding(grant: CanaryGrant) -> dict[str, Any]:
    path = Path(grant.source.metadata_path)
    descriptor, stat_result = _open_nofollow_readonly(path)
    try:
        if not stat.S_ISREG(stat_result.st_mode):
            raise CanaryRefused("canary_gate0_source", "metadata is not regular")
        raw = _stable_read_fd(descriptor, stat_result.st_size)
        digest = _sha256_bytes(raw)
        if digest != grant.source.metadata_sha256:
            raise CanaryRefused("canary_gate0_source", "metadata digest mismatch")
        return {
            "path": str(path),
            "digest": digest,
            "device": stat_result.st_dev,
            "inode": stat_result.st_ino,
            "idle": True,
        }
    finally:
        os.close(descriptor)


def _identity_matches(path: Path, expected: ResourceIdentityGrant, owner_uid: int) -> None:
    if _has_symlink_component(path):
        raise CanaryRefused("canary_gate0_paths", f"symlink escape: {path}")
    if expected.file_type == "absent":
        if path.exists():
            raise CanaryRefused("canary_gate0_paths", f"{expected.role} must be absent")
        return
    try:
        stat_result = path.lstat()
    except OSError as exc:
        raise CanaryRefused("canary_gate0_paths", f"cannot inspect {expected.role}: {exc}") from exc
    if stat.S_ISLNK(stat_result.st_mode):
        raise CanaryRefused("canary_gate0_paths", f"{expected.role} is a symlink")
    actual_type = "dir" if stat.S_ISDIR(stat_result.st_mode) else "file"
    if actual_type != expected.file_type:
        raise CanaryRefused("canary_gate0_paths", f"{expected.role} type mismatch")
    if stat_result.st_uid != expected.uid or expected.uid != owner_uid:
        raise CanaryRefused("canary_gate0_paths", f"{expected.role} owner mismatch")
    if stat.S_IMODE(stat_result.st_mode) != expected.mode:
        raise CanaryRefused("canary_gate0_paths", f"{expected.role} mode mismatch")
    if stat_result.st_dev != expected.device or stat_result.st_ino != expected.inode:
        raise CanaryRefused("canary_gate0_paths", f"{expected.role} identity mismatch")


def _ancestor_pids(pid: int) -> set[int]:
    seen: set[int] = set()
    current = pid
    while current > 1 and current not in seen:
        seen.add(current)
        try:
            status = Path(f"/proc/{current}/status").read_text(encoding="utf-8")
        except OSError:
            break
        ppid = 0
        for line in status.splitlines():
            if line.startswith("PPid:"):
                ppid = int(line.split()[1])
                break
        current = ppid
    return seen


def default_process_census() -> dict[str, str]:
    self_tree = _ancestor_pids(os.getpid())
    descendants = _descendant_pids(os.getpid())
    excluded = self_tree | descendants | {os.getpid()}
    patterns = ("convmem-watch", "convmem index", "run-jsonl-production-canary")
    found: list[str] = []
    for pattern in patterns:
        try:
            completed = subprocess.run(
                ["pgrep", "-af", pattern],
                capture_output=True,
                text=True,
                check=False,
                timeout=2.0,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"pass": "false", "detail": "process census unavailable"}
        for line in (completed.stdout or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                foreign_pid = int(stripped.split(None, 1)[0])
            except ValueError:
                found.append(stripped)
                continue
            if foreign_pid in excluded:
                continue
            found.append(stripped)
    if found:
        return {"pass": "false", "matches": str(len(found)), "detail": found[0]}
    return {"pass": "true", "matches": "0"}


def _descendant_pids(root_pid: int) -> set[int]:
    children: dict[int, list[int]] = {}
    proc = Path("/proc")
    if not proc.is_dir():
        return set()
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            status = (entry / "status").read_text(encoding="utf-8")
        except OSError:
            continue
        ppid = 0
        for line in status.splitlines():
            if line.startswith("PPid:"):
                ppid = int(line.split()[1])
                break
        children.setdefault(ppid, []).append(pid)
    found: set[int] = set()
    stack = list(children.get(root_pid, []))
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(children.get(current, []))
    return found


def default_service_status() -> dict[str, str]:
    try:
        completed = subprocess.run(
            ["systemctl", "--user", "is-active", "convmem-watch.service"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"pass": "false", "status": "unavailable", "detail": str(exc)}
    status = (completed.stdout or "").strip()
    if status == "inactive":
        return {"pass": "true", "status": status, "method": "systemctl-is-active"}
    return {"pass": "false", "status": status or "unknown", "method": "systemctl-is-active"}


def default_writer_census(boundary: ProductionCanaryBoundary) -> dict[str, str]:
    layout = boundary.layout
    locks = {
        "writer_lock": layout["writer_lock"],
        "source_lock": layout["source_lock"],
        "export_lock": layout["export_lock"],
        "processed_lock": layout["processed_lock"],
    }
    held: list[str] = []
    for name, lock_path in locks.items():
        if not lock_path.exists():
            continue
        try:
            descriptor = os.open(lock_path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        except OSError as exc:
            raise CanaryRefused("canary_gate0_writer", f"cannot inspect {name}: {exc}") from exc
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            held.append(name)
        finally:
            os.close(descriptor)
    if held:
        return {"pass": "false", "held": ",".join(held)}
    return {"pass": "true"}


def default_model_manifest(grant: CanaryGrant) -> dict[str, str]:
    for manifest in grant.model_manifests:
        path = Path(manifest.manifest_path)
        if not path.is_file() or _has_symlink_component(path):
            return {"pass": "false", "model": manifest.name, "detail": "manifest missing"}
        digest = _sha256_file(path)
        if digest != manifest.digest:
            return {"pass": "false", "model": manifest.name, "detail": "digest mismatch"}
        if digest in {"46e0c10c039e", "0a109f422b47"} or len(digest) != 64:
            return {"pass": "false", "model": manifest.name, "detail": "short alias is not a full identity"}
    return {"pass": "true", "models": str(len(grant.model_manifests))}


def default_network_self_test(grant: CanaryGrant) -> dict[str, str]:
    repo = str(Path(__file__).resolve().parent)
    script = (
        "import sys\n"
        f"sys.path.insert(0, {repo!r})\n"
        "import socket\n"
        "from incremental_jsonl_canary_network import install_p2_network_policy\n"
        "from incremental_jsonl_isolation import IsolationViolation\n"
        f"host={grant.provider.loopback_host!r}\n"
        "addr, _, port = host.partition(':')\n"
        "install_p2_network_policy(host, dry_run=True)\n"
        "loopback='fail'\n"
        "try:\n"
        "    result=socket.create_connection((addr, int(port or 11434)), timeout=0.2)\n"
        "    loopback='allowed' if result else 'denied'\n"
        "except Exception as exc:\n"
        "    loopback='denied:'+type(exc).__name__\n"
        "remote='fail'\n"
        "try:\n"
        "    socket.create_connection(('203.0.113.1', 9), timeout=0.2)\n"
        "    remote='connected'\n"
        "except IsolationViolation:\n"
        "    remote='denied-before-socket'\n"
        "except Exception as exc:\n"
        "    remote=type(exc).__name__\n"
        "print(loopback+','+remote)\n"
    )
    env = dict(os.environ)
    for key in list(env):
        if "API_KEY" in key or key.startswith("DEEPSEEK"):
            env.pop(key, None)
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=3.0,
        env=env,
        cwd=str(Path(__file__).resolve().parent),
    )
    if completed.returncode != 0:
        return {"pass": "false", "detail": completed.stderr.strip() or "network child failed"}
    loopback, _, remote = (completed.stdout or "").strip().partition(",")
    if not loopback.startswith("allowed"):
        return {"pass": "false", "detail": f"loopback not allowed:{loopback}", "loopback": loopback}
    if remote != "denied-before-socket":
        return {
            "pass": "false",
            "detail": f"non-loopback not policy-denied:{remote}",
            "loopback": loopback,
            "non_loopback": remote,
        }
    return {"pass": "true", "loopback": loopback, "non_loopback": remote}


def default_restic_identifier(grant: CanaryGrant) -> dict[str, str]:
    from restic_snapshot import BackupContext, ResolverError, resolve_snapshot

    if grant.restic is None:
        return {"pass": "false", "detail": "restic binding missing"}
    try:
        ctx = BackupContext.from_env_file()
        ref = resolve_snapshot(
            ctx,
            requested_id=grant.restic.snapshot_id,
            required_tag=grant.restic.tag,
            require_current_local_day=True,
        )
    except (ResolverError, OSError, ValueError) as exc:
        return {"pass": "false", "detail": str(exc)}
    data_root = str(Path(grant.restic.data_root).resolve())
    if ref.id != grant.restic.snapshot_id:
        return {"pass": "false", "detail": "snapshot id mismatch"}
    if grant.restic.tag not in ref.tags:
        return {"pass": "false", "detail": "tag mismatch"}
    if data_root not in {str(Path(item).resolve()) for item in ref.paths} and data_root not in ref.paths:
        if data_root not in ref.paths:
            return {"pass": "false", "detail": "data-root coverage mismatch"}
    if ref.repository != grant.restic.repository:
        return {"pass": "false", "detail": "repository mismatch"}
    return {
        "pass": "true",
        "backup_id": ref.id,
        "tag": grant.restic.tag,
        "restore": "not_authorized",
    }


def default_zero_adoption(boundary: ProductionCanaryBoundary, grant: CanaryGrant) -> dict[str, str]:
    from chroma_readonly import count_for_source_path

    layout = boundary.layout
    processed_entry = None
    processed_path = layout["processed"]
    if processed_path.is_file():
        descriptor, _stat = _open_nofollow_readonly(processed_path)
        try:
            payload = json.loads(_stable_read_fd(descriptor, _stat.st_size).decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanaryRefused("canary_gate0_adoption", f"processed unreadable: {exc}") from exc
        finally:
            os.close(descriptor)
        if isinstance(payload, dict):
            processed_entry = payload.get(grant.source.path)
    chroma_path = layout["chroma"]
    summary_count = count_for_source_path(chroma_path, SUMMARIES, grant.source.path)
    unit_count = count_for_source_path(chroma_path, UNITS, grant.source.path)
    state_dir = layout["state"] / hashlib.sha256(grant.source.path.encode()).hexdigest()
    has_state = state_dir.exists() and any(state_dir.iterdir()) if state_dir.exists() else False
    export_hit = False
    export_path = layout["export"]
    if export_path.is_file():
        text = export_path.read_text(encoding="utf-8")
        export_hit = grant.source.path in text
    if processed_entry or summary_count or unit_count or has_state or export_hit:
        return {
            "pass": "false",
            "processed_entry": str(processed_entry),
            "summary_count": str(summary_count),
            "unit_count": str(unit_count),
            "state": str(has_state),
        }
    return {"pass": "true"}


def _identity_from_payload(payload: Mapping[str, Any]) -> ResourceIdentityGrant:
    return ResourceIdentityGrant(
        role=str(payload["role"]),
        path=str(payload["path"]),
        uid=int(payload["uid"]),
        mode=int(payload["mode"]),
        device=int(payload["device"]),
        inode=int(payload["inode"]),
        file_type=str(payload["file_type"]),
    )


def _prepared_receipt(grant: CanaryGrant) -> StageReceipt | None:
    path = stage_receipt_path(grant)
    if not path.is_file():
        return None
    receipt = load_stage_receipt(grant)
    prepared_index = LIVE_STAGE_ORDER.index("prepared")
    if receipt.stage not in LIVE_STAGE_ORDER:
        raise CanaryRefused("canary_stage", f"unknown receipt stage {receipt.stage}")
    if LIVE_STAGE_ORDER.index(receipt.stage) < prepared_index:
        return None
    return receipt


def gate0_preflight_live(
    grant: CanaryGrant,
    boundary: ProductionCanaryBoundary,
    *,
    expected_sha256: str,
    code_revision: str,
    hooks: LiveGate0Hooks | None = None,
) -> dict[str, Any]:
    """Twelve-part read-only Gate 0. Writes nothing, including evidence."""
    hooks = hooks or LiveGate0Hooks()
    validate_p2_live_grant(grant, expected_sha256=expected_sha256, code_revision=code_revision)
    assert_not_reused(boundary.root, grant)
    receipt = stage_receipt_path(grant)
    if receipt.is_file():
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        if payload.get("nonce") == grant.nonce and payload.get("stage") == "t6-evidence-frozen":
            raise CanaryRefused("canary_nonce_reused", "grant nonce already consumed")
    prepared = _prepared_receipt(grant)
    allow_append = prepared is not None and prepared.stage != "prepared"
    checks: dict[str, Any] = {}
    checks["1_grant"] = {
        "digest": expected_sha256,
        "revision": code_revision,
        "nonce": grant.nonce,
        "capability_mode": P2_LIVE_CAPABILITY_MODE,
    }
    checks["2_baseline"] = _descriptor_source_binding(grant, allow_append=allow_append)
    checks["3_source"] = _descriptor_metadata_binding(grant)
    if prepared is None:
        zero = (hooks.zero_adoption or default_zero_adoption)(boundary, grant)
        if zero.get("pass") != "true":
            raise CanaryRefused("canary_gate0_adoption", f"non-zero adoption: {zero}")
        checks["4_zero_adoption"] = zero
    else:
        checks["4_zero_adoption"] = {"pass": "true", "skipped": "post-prepare"}
    persistent = Path(grant.persistent_config.path)  # type: ignore[union-attr]
    if persistent.is_file():
        digest = _sha256_file(persistent)
        if digest != grant.persistent_config.digest:  # type: ignore[union-attr]
            raise CanaryRefused("canary_gate0_config", "persistent config digest mismatch")
        if not verify_persistent_config_false_false(persistent):
            raise CanaryRefused("canary_gate0_config", "persistent config not false/false")
    elif grant.persistent_config.digest != ABSENT_DIGEST:  # type: ignore[union-attr]
        raise CanaryRefused("canary_gate0_config", "persistent config absent-state mismatch")
    checks["5_persistent_config"] = {"pass": "true", "path": str(persistent)}
    watcher = (hooks.watcher_probe or gate0_watcher_probe)()
    process = (hooks.process_census or default_process_census)()
    service = (hooks.service_status or default_service_status)()
    if watcher.get("pass") != "true" or process.get("pass") != "true" or service.get("pass") != "true":
        raise CanaryRefused(
            "canary_gate0_watcher",
            f"watcher/process/service failed: watcher={watcher} process={process} service={service}",
        )
    checks["6_watcher"] = {"watcher": watcher, "process": process, "service": service}
    writer = (hooks.writer_census or default_writer_census)(boundary)
    if writer.get("pass") != "true":
        raise CanaryRefused("canary_gate0_writer", f"writer census failed: {writer}")
    checks["7_writer"] = writer
    identities = {item.role: item for item in grant.resource_identities}
    owner_uid = grant.owner_uid or -1
    capsule_path = Path(grant.rollback.capsule_path)
    if prepared is None:
        if identities["capsule"].file_type == "absent" and capsule_path.exists():
            raise CanaryRefused(
                "canary_gate0_capsule",
                "rollback capsule must be absent before prepare",
            )
        _identity_matches(Path(grant.config_overlay), identities["overlay"], owner_uid)
        _identity_matches(Path(grant.evidence_dir), identities["evidence_dir"], owner_uid)
        _identity_matches(capsule_path, identities["capsule"], owner_uid)
    else:
        artifacts = prepared.artifact_identities
        if "overlay" not in artifacts or "evidence_dir" not in artifacts:
            raise CanaryRefused("canary_gate0_paths", "prepared receipt missing overlay/evidence identities")
        _identity_matches(
            Path(grant.config_overlay),
            _identity_from_payload(artifacts["overlay"]),
            owner_uid,
        )
        _identity_matches(
            Path(grant.evidence_dir),
            _identity_from_payload(artifacts["evidence_dir"]),
            owner_uid,
        )
        if not capsule_path.is_file():
            raise CanaryRefused("canary_gate0_capsule", "rollback capsule missing after prepare")
        digest = _sha256_file(capsule_path)
        if digest != prepared.capsule_digest:
            raise CanaryRefused("canary_gate0_capsule", "capsule digest does not match receipt")
        capsule_stat = capsule_path.lstat()
        if capsule_stat.st_uid != owner_uid or not stat.S_ISREG(capsule_stat.st_mode):
            raise CanaryRefused("canary_gate0_capsule", "capsule owner or type mismatch")
    _identity_matches(Path(grant.source.path), identities["source"], owner_uid)
    _identity_matches(Path(grant.source.metadata_path), identities["metadata"], owner_uid)
    persistent = Path(grant.persistent_config.path)  # type: ignore[union-attr]
    _identity_matches(persistent, identities["persistent_config"], owner_uid)
    for role in grant.resources:
        expected = identities[role.role]
        path = Path(role.path)
        if prepared is not None and expected.file_type == "absent":
            if not path.exists():
                continue
            if _has_symlink_component(path):
                raise CanaryRefused("canary_gate0_paths", f"{role.role} escaped after prepare")
            actual = path.lstat()
            if stat.S_ISLNK(actual.st_mode) or actual.st_uid != owner_uid:
                raise CanaryRefused("canary_gate0_paths", f"{role.role} owner or type mismatch")
            continue
        _identity_matches(path, expected, owner_uid)
    checks["8_paths"] = {"roles": len(grant.resource_identities)}
    models = (hooks.model_manifest or default_model_manifest)(grant)
    if models.get("pass") != "true":
        raise CanaryRefused("canary_gate0_models", f"model manifest failed: {models}")
    checks["9_models"] = models
    env = build_allowlisted_child_env(boundary)
    blocked = [key for key in env if "API_KEY" in key or key.startswith("DEEPSEEK")]
    if blocked:
        raise CanaryRefused("canary_gate0_credentials", f"credentials present: {blocked}")
    network = (hooks.network_self_test or default_network_self_test)(grant)
    if network.get("pass") != "true":
        raise CanaryRefused("canary_gate0_network", f"network self-test failed: {network}")
    checks["10_network"] = {"credentials": "absent", "network": network}
    capsule_path = Path(grant.rollback.capsule_path)
    if prepared is None:
        if capsule_path.exists():
            raise CanaryRefused(
                "canary_gate0_capsule",
                "rollback capsule must be absent before prepare",
            )
        parent = capsule_path.parent
        creatable = parent.exists() and os.access(parent, os.W_OK) or parent.parent.exists()
        checks["11_capsule"] = {
            "path": str(capsule_path),
            "captured": False,
            "readable": False,
            "creatable_later": bool(creatable),
        }
    else:
        checks["11_capsule"] = {
            "path": str(capsule_path),
            "captured": True,
            "readable": True,
            "digest": prepared.capsule_digest,
        }
    restic = (hooks.restic_identifier or default_restic_identifier)(grant)
    if restic.get("pass") != "true":
        raise CanaryRefused("canary_gate0_restic", f"restic evidence failed: {restic}")
    if restic.get("backup_id") in {None, "", "hermetic-stub-no-restore", "hermetic-stub"}:
        raise CanaryRefused("canary_gate0_restic", "restic stub cannot PASS")
    checks["12_restic"] = restic
    return {
        "mode": P2_LIVE_CAPABILITY_MODE,
        "grant_digest": expected_sha256,
        "nonce": grant.nonce,
        "checks": checks,
        "hermetic": False,
    }


def _persist_receipt(grant: CanaryGrant, receipt: StageReceipt) -> StageReceipt:
    path = stage_receipt_path(grant)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = receipt.to_dict()
    digest = _sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    payload["receipt_sha256"] = digest
    _atomic_json(path, payload)
    os.chmod(path, 0o600)
    receipt.receipt_sha256 = digest
    return receipt


def load_stage_receipt(grant: CanaryGrant) -> StageReceipt:
    path = stage_receipt_path(grant)
    if not path.is_file():
        raise CanaryRefused("canary_stage", "stage receipt missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    recorded = str(payload.get("receipt_sha256", ""))
    check = dict(payload)
    check.pop("receipt_sha256", None)
    digest = _sha256_bytes(json.dumps(check, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    if recorded != digest:
        raise CanaryRefused("canary_stage_tamper", "stage receipt digest mismatch")
    return StageReceipt(
        nonce=str(payload["nonce"]),
        grant_digest=str(payload["grant_digest"]),
        stage=str(payload["stage"]),
        next_stage=str(payload["next_stage"]),
        capsule_digest=str(payload.get("capsule_digest", ZERO_DIGEST)),
        source_identity=dict(payload.get("source_identity") or {}),
        unrelated_manifest_digest=str(payload.get("unrelated_manifest_digest", ZERO_DIGEST)),
        call_counters=dict(payload.get("call_counters") or {}),
        append_identities=list(payload.get("append_identities") or []),
        faults_completed=list(payload.get("faults_completed") or []),
        recovery_dispositions=list(payload.get("recovery_dispositions") or []),
        artifact_identities=dict(payload.get("artifact_identities") or {}),
        receipt_sha256=recorded,
    )


def _require_stage(grant: CanaryGrant, expected_next: str, *, expected_sha256: str) -> StageReceipt:
    receipt = load_stage_receipt(grant)
    if receipt.nonce != grant.nonce or receipt.grant_digest != expected_sha256:
        raise CanaryRefused("canary_stage", "receipt does not match grant")
    if receipt.next_stage != expected_next:
        raise CanaryRefused(
            "canary_stage_order",
            f"expected next {expected_next}, found {receipt.next_stage}",
        )
    return receipt


def _source_identity_payload(grant: CanaryGrant) -> dict[str, Any]:
    path = Path(grant.source.path)
    stat_result = path.lstat()
    return {
        "path": grant.source.path,
        "device": stat_result.st_dev,
        "inode": stat_result.st_ino,
        "size": stat_result.st_size,
        "prefix_sha256": grant.source.prefix_sha256,
    }


def _source_immutability_token(grant: CanaryGrant) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for label, path_str in (
        ("source", grant.source.path),
        ("metadata", grant.source.metadata_path),
    ):
        path = Path(path_str)
        stat_result = path.lstat()
        payload[label] = {
            "path": path_str,
            "device": stat_result.st_dev,
            "inode": stat_result.st_ino,
            "mode": stat.S_IMODE(stat_result.st_mode),
            "mtime_ns": stat_result.st_mtime_ns,
            "size": stat_result.st_size,
            "sha256": _sha256_file(path),
        }
    return payload


def assert_source_immutable(grant: CanaryGrant, token: Mapping[str, Any]) -> None:
    actual = _source_immutability_token(grant)
    if actual != dict(token):
        raise CanaryRefused("canary_source_immutable", "source or session.json identity changed")


def _canonical_digest(payload: Any) -> str:
    return _sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _float32_ordered_bits(value: float) -> int:
    bits = struct.unpack(">I", struct.pack(">f", float(value)))[0]
    if bits & 0x80000000:
        return -(bits & 0x7FFFFFFF)
    return bits


def float32_ulp_distance(left: float, right: float) -> int:
    return abs(_float32_ordered_bits(left) - _float32_ordered_bits(right))


def next_float32(value: float, steps: int = 1) -> float:
    ordered = _float32_ordered_bits(value) + int(steps)
    if ordered < 0:
        bits = 0x80000000 | (-ordered)
    else:
        bits = ordered
    return float(struct.unpack(">f", struct.pack(">I", bits & 0xFFFFFFFF))[0])


def _embeddings_within_ulp(left: list[Any], right: list[Any], *, max_ulp: int = EMBEDDING_MAX_ULP) -> bool:
    if len(left) != len(right):
        return False
    for first, second in zip(left, right):
        if float32_ulp_distance(float(first), float(second)) > max_ulp:
            return False
    return True


def _chroma_rows_equivalent(left_rows: Any, right_rows: Any) -> bool:
    left_list = list(left_rows or [])
    right_list = list(right_rows or [])
    if len(left_list) != len(right_list):
        return False
    left_sorted = sorted(left_list, key=lambda row: str(row.get("id")))
    right_sorted = sorted(right_list, key=lambda row: str(row.get("id")))
    for left, right in zip(left_sorted, right_sorted):
        if str(left.get("id")) != str(right.get("id")):
            return False
        if left.get("document") != right.get("document"):
            return False
        if dict(left.get("metadata") or {}) != dict(right.get("metadata") or {}):
            return False
        if left.get("collection") != right.get("collection"):
            return False
        if not _embeddings_within_ulp(
            list(left.get("embedding") or []),
            list(right.get("embedding") or []),
        ):
            return False
    return True


def _rollback_equivalent(pre_rollback: Any, post_rollback: Any) -> bool:
    pre = dict(pre_rollback or {})
    post = dict(post_rollback or {})
    pre_sum = pre.pop("summaries", [])
    post_sum = post.pop("summaries", [])
    pre_units = pre.pop("units", [])
    post_units = post.pop("units", [])
    if _canonical_digest(pre) != _canonical_digest(post):
        return False
    return _chroma_rows_equivalent(pre_sum, post_sum) and _chroma_rows_equivalent(pre_units, post_units)


def recovery_equivalent(pre_fault: Mapping[str, Any], post: Mapping[str, Any]) -> bool:
    """IDs/documents/metadata/state/unrelated are exact; embeddings may drift 1 float32 ULP."""
    if _canonical_digest(pre_fault.get("state_digests")) != _canonical_digest(post.get("state_digests")):
        return False
    if _canonical_digest(pre_fault.get("unrelated_manifest")) != _canonical_digest(
        post.get("unrelated_manifest")
    ):
        return False
    return _rollback_equivalent(pre_fault.get("rollback"), post.get("rollback"))


def _derive_unrelated_sources(boundary: ProductionCanaryBoundary, grant: CanaryGrant) -> list[str]:
    from chroma_readonly import collection_metadata_rows

    chroma = boundary.layout["chroma"]
    discovered: set[str] = set()
    db = chroma / "chroma.sqlite3"
    if db.is_file():
        for collection in (SUMMARIES, UNITS):
            try:
                rows = collection_metadata_rows(chroma, collection)
            except OSError as exc:
                raise CanaryRefused("canary_unrelated", f"chroma scan failed: {exc}") from exc
            for row in rows:
                path = row.get("source_path")
                if path and path != grant.source.path:
                    discovered.add(str(path))
    processed_path = boundary.layout["processed"]
    if processed_path.is_file():
        try:
            payload = json.loads(processed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CanaryRefused("canary_unrelated", f"processed scan failed: {exc}") from exc
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, dict):
                    path = value.get("path")
                    if path and path != grant.source.path:
                        discovered.add(str(path))
    return sorted(discovered)


def _unrelated_readonly_manifest(
    boundary: ProductionCanaryBoundary,
    extra_sources: list[str] | None = None,
    *,
    grant: CanaryGrant | None = None,
) -> dict[str, Any]:
    from chroma_readonly import count_for_source_path, ids_for_source_path

    chroma = boundary.layout["chroma"]
    derived: list[str] = []
    if grant is not None:
        derived = _derive_unrelated_sources(boundary, grant)
    extras = list(extra_sources or [])
    if extras and grant is not None:
        unexpected = [item for item in extras if item not in derived and item != grant.source.path]
        if unexpected and not derived:
            derived = extras
        elif unexpected:
            derived = sorted(set(derived) | set(extras))
    elif extras and grant is None:
        derived = extras
    manifest: dict[str, Any] = {"sources": {}, "derived": True, "source_count": len(derived)}
    for source_path in derived:
        manifest["sources"][source_path] = {
            "summary_count": count_for_source_path(chroma, SUMMARIES, source_path),
            "unit_count": count_for_source_path(chroma, UNITS, source_path),
            "summary_ids": ids_for_source_path(chroma, SUMMARIES, source_path),
            "unit_ids": ids_for_source_path(chroma, UNITS, source_path),
        }
    manifest["digest"] = _sha256_bytes(json.dumps(manifest["sources"], sort_keys=True).encode("utf-8"))
    return manifest


def _readonly_live_capsule(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    unrelated: Mapping[str, Any],
) -> dict[str, Any]:
    from chroma_readonly import ids_for_source_path

    chroma = boundary.layout["chroma"]
    summaries = [{"id": item} for item in ids_for_source_path(chroma, SUMMARIES, grant.source.path)]
    units = [{"id": item} for item in ids_for_source_path(chroma, UNITS, grant.source.path)]
    export_path = boundary.layout["export"]
    export_lines: list[Any] = []
    if export_path.is_file():
        for line in export_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                export_lines.append(("keep", line))
                continue
            if isinstance(row, dict) and row.get("source_path") == grant.source.path:
                export_lines.append(("source", line))
            else:
                export_lines.append(("keep", line))
    processed_preimage: dict[str, Any] = {}
    processed_path = boundary.layout["processed"]
    if processed_path.is_file():
        payload = json.loads(processed_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            processed_preimage = {
                key: value
                for key, value in payload.items()
                if isinstance(value, dict) and value.get("path") == grant.source.path
            }
    rollback = {
        "version": 1,
        "summaries": summaries,
        "units": units,
        "export_lines": export_lines,
        "processed_preimage": processed_preimage,
        "source_path": grant.source.path,
        "state_files": {"checkpoint": None, "transaction": None, "rollback": None},
        "prepared_files": {},
        "dedupe_files": {},
    }
    return {
        "version": 1,
        "rollback": rollback,
        "state_digests": {},
        "unrelated_manifest": dict(unrelated),
        "source_path": grant.source.path,
    }


def _persist_capsule(path: Path, capsule: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_json(path, dict(capsule))
    os.chmod(path, 0o600)
    _fsync_directory(path.parent)
    descriptor, _stat = _open_nofollow_readonly(path)
    os.close(descriptor)
    digest = _sha256_file(path)
    if digest == ZERO_DIGEST:
        raise CanaryRefused("canary_capsule", "captured capsule cannot be the zero sentinel")
    return digest


def prepare_live_p2(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    code_revision: str,
    hooks: LiveGate0Hooks | None = None,
    unrelated_sources: list[str] | None = None,
) -> dict[str, Any]:
    """Create allowlisted dirs, overlay, capsule, and the prepared stage receipt."""
    report = gate0_preflight_live(
        grant,
        boundary,
        expected_sha256=expected_sha256,
        code_revision=code_revision,
        hooks=hooks,
    )
    source_token = _source_immutability_token(grant)
    unrelated = _unrelated_readonly_manifest(boundary, unrelated_sources, grant=grant)
    capsule = _readonly_live_capsule(boundary, grant, unrelated)
    capsule_path = Path(grant.rollback.capsule_path)
    digest = _persist_capsule(capsule_path, capsule)
    write_canary_overlay(boundary)
    Path(grant.evidence_dir).mkdir(parents=True, exist_ok=True)
    os.chmod(Path(grant.evidence_dir), 0o700)
    assert_source_immutable(grant, source_token)
    owner_uid = grant.owner_uid or os.getuid()
    counters = {key: 0 for key in CALL_CEILINGS_WHOLE}
    receipt = StageReceipt(
        nonce=grant.nonce,
        grant_digest=expected_sha256,
        stage="prepared",
        next_stage="t3-initial-complete",
        capsule_digest=digest,
        source_identity=_source_identity_payload(grant),
        unrelated_manifest_digest=str(unrelated["digest"]),
        call_counters=counters,
        artifact_identities={
            "overlay": asdict(
                capture_path_identity(Path(grant.config_overlay), "overlay", owner_uid)
            ),
            "evidence_dir": asdict(
                capture_path_identity(Path(grant.evidence_dir), "evidence_dir", owner_uid)
            ),
        },
    )
    _persist_receipt(grant, receipt)
    _atomic_json(call_ledger_path(grant), counters)
    return {"stage": "prepared", "capsule_digest": digest, "gate0": report}


@contextmanager
def install_provider_invoker(invoker: ProviderInvoker | None, *, provider_mode: str) -> Iterator[None]:
    if provider_mode == "hermetic" and invoker is None:
        raise CanaryRefused("canary_provider_mode", "hermetic mode cannot select real providers")
    if provider_mode == "live" and invoker is not None:
        raise CanaryRefused("canary_provider_mode", "live mode cannot install test fakes")
    if invoker is None:
        yield
        return
    import ingest

    original = (ingest.summarize, ingest.distill, ingest.ollama_embed)
    ingest.summarize = invoker.summarize
    ingest.distill = invoker.distill
    ingest.ollama_embed = invoker.embed
    try:
        yield
    finally:
        ingest.summarize = original[0]
        ingest.distill = original[1]
        ingest.ollama_embed = original[2]


def persist_call_counters(grant: CanaryGrant, counters: Mapping[str, int]) -> None:
    _atomic_json(call_ledger_path(grant), dict(counters))


def load_call_counters(grant: CanaryGrant) -> dict[str, int]:
    path = call_ledger_path(grant)
    if not path.is_file():
        return {key: 0 for key in CALL_CEILINGS_WHOLE}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {key: int(payload.get(key, 0)) for key in CALL_CEILINGS_WHOLE}


def enforce_call_ceilings(grant: CanaryGrant, kind: str, *, stage_ceilings: Mapping[str, int]) -> dict[str, int]:
    counters = load_call_counters(grant)
    whole = grant.call_ceilings.get("whole_run", CALL_CEILINGS_WHOLE)
    if counters.get(kind, 0) >= int(whole.get(kind, 0)):
        raise CanaryRefused("canary_call_cap", f"{kind} whole-run cap exceeded")
    if counters.get(kind, 0) >= int(stage_ceilings.get(kind, 0)):
        raise CanaryRefused("canary_call_cap", f"{kind} stage cap exceeded")
    counters[kind] = counters.get(kind, 0) + 1
    persist_call_counters(grant, counters)
    return counters


def prove_external_append(grant: CanaryGrant, receipt: StageReceipt) -> dict[str, Any]:
    from adapters.kiro_session_jsonl import parse_complete_prefix

    path = Path(grant.source.path)
    descriptor, stat_result = _open_nofollow_readonly(path)
    try:
        if stat_result.st_dev != grant.source.device or stat_result.st_ino != grant.source.inode:
            raise CanaryRefused("canary_append", "source device/inode changed")
        raw = _stable_read_fd(descriptor, stat_result.st_size)
    finally:
        os.close(descriptor)
    prefix = raw[: grant.source.complete_boundary]
    if _sha256_bytes(prefix) != grant.source.prefix_sha256:
        raise CanaryRefused("canary_append", "immutable prefix changed")
    if len(raw) <= grant.source.size:
        raise CanaryRefused("canary_append", "source did not grow")
    if len(raw) > grant.append_envelope.max_byte_boundary:
        raise CanaryRefused("canary_append", "append exceeds byte envelope")
    view = parse_complete_prefix(str(path), raw=raw)
    if len(view.messages) > min(APPEND_MAX_MESSAGES, grant.append_envelope.max_accepted_records):
        raise CanaryRefused("canary_append", "accepted count exceeds envelope")
    validate_append_profile(len(view.messages))
    identity = _sha256_bytes(raw)
    if identity in receipt.append_identities:
        raise CanaryRefused("canary_append", "append identity already used")
    return {
        "accepted_messages": len(view.messages),
        "append_identity": identity,
        "complete_boundary": view.complete_boundary,
        "size": len(raw),
    }


class HermeticCanaryInvoker:
    """Production-owned hermetic provider double; must not import tests."""

    def summarize(self, text: str, **_kwargs: Any) -> str:
        return f"summary:{hashlib.sha256(text.encode()).hexdigest()[:16]}"

    def distill(self, text: str, **_kwargs: Any) -> list[dict[str, Any]]:
        return [
            {
                "type": "explanation",
                "title": f"Isolated unit {text[:12]}",
                "summary": "Reusable isolated knowledge unit for hermetic tests.",
                "keywords": ["kiro", "jsonl", "incremental"],
                "confidence": 0.95,
                "domain": "general",
            }
        ]

    def embed(self, text: str, **_kwargs: Any) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(8)]


def _serving_cfg(boundary: ProductionCanaryBoundary, grant: CanaryGrant) -> dict[str, Any]:
    layout = boundary.layout
    return {
        "models": {
            "embed_model": grant.provider.embed_model,
            "ollama_host": grant.provider.loopback_host,
            "rerank_model": "rerank",
        },
        "query": {"rerank": False, "recency_weight": 0.0, "top_k_candidates": 5},
        "index": {
            "chroma_dir": str(layout["chroma"]),
            "generation_root": str(layout["state"] / "file_generations"),
            "processed_log": str(layout["processed"]),
        },
    }


@contextmanager
def _serving_visibility_monitor(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
) -> Iterator[dict[str, Any]]:
    from serving_index_repository import open_serving_index_repository

    cfg = _serving_cfg(boundary, grant)
    stop = threading.Event()
    holder: dict[str, Any] = {"probe": None, "error": None, "mixed_s": 0.0}
    mixed_started: list[float] = []

    def _loop() -> None:
        deadline = time.monotonic() + 30.0
        while not stop.is_set() and time.monotonic() < deadline:
            try:
                with open_serving_index_repository(cfg) as repo:
                    probe = ServingVisibilityProbe(repo, grant.source.path)
                    holder["probe"] = probe
                    holder["error"] = None
                    while not stop.wait(0.05):
                        obs = probe.sample()
                        if obs.error:
                            holder["error"] = obs.error
                        if obs.mixed:
                            if not mixed_started:
                                mixed_started.append(time.monotonic())
                        elif mixed_started:
                            holder["mixed_s"] += time.monotonic() - mixed_started.pop()
                    return
            except Exception as exc:  # pylint: disable=broad-exception-caught
                holder["error"] = type(exc).__name__
                time.sleep(0.05)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    try:
        yield holder
    finally:
        stop.set()
        thread.join(timeout=5)
        if mixed_started:
            holder["mixed_s"] += time.monotonic() - mixed_started[0]
        probe = holder.get("probe")
        if probe is None:
            raise CanaryRefused(
                "canary_serving_visible",
                f"serving visibility missing or error: {holder.get('error')}",
            )
        timeline = []
        if probe is not None:
            timeline.extend(
                {
                    "monotonic_s": item.monotonic_s,
                    "summary": item.summary_generation,
                    "unit": item.unit_generation,
                    "mixed": item.mixed,
                    "error": item.error,
                }
                for item in probe.observations
            )
        try:
            with open_serving_index_repository(cfg) as repo:
                settle = ServingVisibilityProbe(repo, grant.source.path)
                for index in range(STABLE_READ_COUNT):
                    settle.sample()
                    if index + 1 < STABLE_READ_COUNT:
                        time.sleep(STABLE_READ_MIN_SPAN_S / (STABLE_READ_COUNT - 1))
                settle.assert_stable_reads()
                timeline.extend(
                    {
                        "monotonic_s": item.monotonic_s,
                        "summary": item.summary_generation,
                        "unit": item.unit_generation,
                        "mixed": item.mixed,
                        "error": item.error,
                    }
                    for item in settle.observations
                )
        except CanaryRefused:
            raise
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise CanaryRefused(
                "canary_serving_visible",
                f"serving visibility missing or error: {type(exc).__name__}",
            ) from exc
        holder["timeline"] = timeline
        holder["probe"] = probe


def run_live_t3(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    provider_mode: str,
    invoker: ProviderInvoker | None = None,
) -> dict[str, Any]:
    receipt = _require_stage(grant, "t3-initial-complete", expected_sha256=expected_sha256)
    if receipt.capsule_digest == ZERO_DIGEST:
        raise CanaryRefused("canary_capsule", "zero sentinel cannot satisfy T3 readiness")
    from adapters.kiro_session_jsonl import parse_complete_prefix

    source_token = _source_immutability_token(grant)
    count = len(parse_complete_prefix(grant.source.path).messages)
    validate_two_chunk_profile(count)
    starts = chunk_starts_for_count(count, chunk_size=60, overlap=10)
    with _serving_visibility_monitor(boundary, grant) as visibility:
        with install_provider_invoker(invoker, provider_mode=provider_mode):
            with install_call_budget_guard(grant.call_ceilings["initial"]) as guard:
                coordinator = canary_coordinator(boundary, grant.source.path, counters=guard.counts)
                with canary_writer_scope(boundary):
                    result = coordinator.run()
                persist_call_counters(grant, guard.counts.as_dict())
                if result.outcome != "committed":
                    raise CanaryRefused("canary_p2_t3", f"initial adoption failed: {result.outcome}")
                replay, replay_guard = _replay_zero(boundary, grant)
    assert_source_immutable(grant, source_token)
    receipt.stage = "t3-initial-complete"
    receipt.next_stage = "waiting-for-external-append-1"
    receipt.call_counters = load_call_counters(grant)
    _persist_receipt(grant, receipt)
    return {
        "stage": "t3-initial-complete",
        "outcome": result.outcome,
        "chunk_starts": starts,
        "counters": guard.counts.as_dict(),
        "replay_counters": replay_guard.as_dict(),
        "replay_outcome": replay.outcome,
        "serving": {
            "mixed_s": visibility["mixed_s"],
            "samples": len(visibility.get("timeline") or []),
        },
    }


def _replay_zero(boundary: ProductionCanaryBoundary, grant: CanaryGrant) -> tuple[Any, CallCounters]:
    with install_call_budget_guard(
        {"summarize": 0, "distill": 0, "summary_embed": 0, "unit_embed": 0}
    ) as guard:
        coordinator = canary_coordinator(boundary, grant.source.path, counters=guard.counts)
        with canary_writer_scope(boundary):
            result = coordinator.run()
    if result.outcome != "unchanged" or guard.counts.total != 0:
        raise CanaryRefused("canary_replay", "unchanged replay must perform zero calls")
    return result, guard.counts


def run_live_t4(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    provider_mode: str,
    invoker: ProviderInvoker | None = None,
) -> dict[str, Any]:
    receipt = _require_stage(grant, "waiting-for-external-append-1", expected_sha256=expected_sha256)
    source_token = _source_immutability_token(grant)
    append = prove_external_append(grant, receipt)
    with _serving_visibility_monitor(boundary, grant) as visibility:
        with install_provider_invoker(invoker, provider_mode=provider_mode):
            with install_call_budget_guard(grant.call_ceilings["append"]) as guard:
                coordinator = canary_coordinator(boundary, grant.source.path, counters=guard.counts)
                with canary_writer_scope(boundary):
                    result = coordinator.run()
                persist_call_counters(grant, guard.counts.as_dict())
        if result.outcome != "committed":
            raise CanaryRefused("canary_p2_t4", f"append adoption failed: {result.outcome}")
        replay, replay_guard = _replay_zero(boundary, grant)
    assert_source_immutable(grant, source_token)
    receipt.append_identities.append(str(append["append_identity"]))
    receipt.stage = "t4-append-complete"
    receipt.next_stage = "waiting-for-external-append-2"
    receipt.call_counters = load_call_counters(grant)
    _persist_receipt(grant, receipt)
    return {
        "stage": "t4-append-complete",
        "accepted_messages": append["accepted_messages"],
        "counters": guard.counts.as_dict(),
        "replay_counters": replay_guard.as_dict(),
        "replay_outcome": replay.outcome,
        "serving": {
            "mixed_s": visibility["mixed_s"],
            "samples": len(visibility.get("timeline") or []),
        },
    }


def bind_live_append_for_faults(
    grant: CanaryGrant,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    """Record the second external append before T5 without writing the source."""
    receipt = _require_stage(grant, "waiting-for-external-append-2", expected_sha256=expected_sha256)
    source_token = _source_immutability_token(grant)
    append = prove_external_append(grant, receipt)
    assert_source_immutable(grant, source_token)
    receipt.append_identities.append(str(append["append_identity"]))
    receipt.stage = "waiting-for-external-append-2"
    receipt.next_stage = "t5-fault-1-complete"
    _persist_receipt(grant, receipt)
    return {"stage": "waiting-for-external-append-2", "accepted_messages": append["accepted_messages"]}


def _capture_pre_fault_capsule(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    unrelated_sources: list[str] | None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    unrelated = _unrelated_readonly_manifest(boundary, unrelated_sources, grant=grant)
    coordinator = canary_coordinator(boundary, grant.source.path)
    capsule = capture_rollback_capsule(coordinator, unrelated_manifest=unrelated)
    path = Path(grant.rollback.capsule_path)
    digest = _persist_capsule(path, capsule)
    return digest, capsule, unrelated


def _pgid_members(pgid: int) -> set[int]:
    found: set[int] = set()
    proc = Path("/proc")
    if not proc.is_dir():
        return found
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat_text = (entry / "stat").read_text(encoding="utf-8")
        except OSError:
            continue
        close = stat_text.rfind(")")
        if close < 0:
            continue
        fields = stat_text[close + 2 :].split()
        if len(fields) < 4:
            continue
        try:
            group = int(fields[2])
        except ValueError:
            continue
        if group == pgid:
            found.add(int(entry.name))
    return found


def run_contained_child(argv: list[str], *, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    child = subprocess.Popen(  # noqa: S603
        argv,
        env=dict(env or os.environ),
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    pgid = child.pid
    try:
        stdout, stderr = child.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        terminate_process_group(pgid)
        stdout, stderr = child.communicate(timeout=2)
    remaining = _pgid_members(pgid)
    if remaining:
        terminate_process_group(pgid)
        remaining = _pgid_members(pgid)
    try:
        os.killpg(pgid, 0)
        raise CanaryRefused("canary_descendants", f"process group {pgid} still exists")
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        raise CanaryRefused("canary_descendants", f"cannot prove process group absent: {exc}") from exc
    if remaining:
        raise CanaryRefused("canary_descendants", f"descendants remain: {sorted(remaining)}")
    return {
        "pid": child.pid,
        "pgid": pgid,
        "returncode": child.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "descendants": [],
    }


def _write_live_grant(grant: CanaryGrant) -> Path:
    path = Path(grant.evidence_dir) / "live-grant.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(grant.to_payload(), indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _observe_recovery_disposition(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    pre_fault: Mapping[str, Any],
    unrelated: Mapping[str, Any],
) -> tuple[str, Any]:
    coordinator = canary_coordinator(boundary, grant.source.path)
    restore_rollback_capsule(coordinator, pre_fault)
    post = capture_rollback_capsule(coordinator, unrelated_manifest=unrelated)
    if recovery_equivalent(pre_fault, post):
        return "restored", None
    return "recovery_unproven", None


def run_live_t5(
    boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    fault_selector: str,
    provider_mode: str,
    invoker: ProviderInvoker | None = None,
    child_argv: list[str] | None = None,
    unrelated_sources: list[str] | None = None,
) -> dict[str, Any]:
    if fault_selector not in FAULT_STAGE:
        raise CanaryRefused("canary_fault_unknown", f"unknown fault selector: {fault_selector}")
    if child_argv is not None and "crash-self" in child_argv:
        raise CanaryRefused("canary_fault_evidence", "generic crash-self is not fault evidence")
    if provider_mode == "hermetic" and invoker is None:
        raise CanaryRefused("canary_provider_mode", "hermetic mode cannot select real providers")
    if provider_mode == "live" and invoker is not None:
        raise CanaryRefused("canary_provider_mode", "live mode cannot install test fakes")
    expected_next = FAULT_STAGE[fault_selector]
    receipt = _require_stage(grant, expected_next, expected_sha256=expected_sha256)
    if fault_selector in receipt.faults_completed:
        raise CanaryRefused("canary_stage_order", f"fault {fault_selector} already completed")
    source_token = _source_immutability_token(grant)
    pre_digest, pre_fault, unrelated = _capture_pre_fault_capsule(boundary, grant, unrelated_sources)
    grant_path = _write_live_grant(grant)
    import site

    env = build_allowlisted_child_env(
        boundary,
        extra={
            "CONVMEM_CANARY_GRANT": str(grant_path),
            "CONVMEM_CANARY_GRANT_SHA256": expected_sha256,
            "CONVMEM_CANARY_REVISION": grant.code_revision,
            "CONVMEM_CANARY_FAULT": fault_selector,
            "CONVMEM_CANARY_PROVIDER_MODE": provider_mode,
            "CONVMEM_CANARY_LOOPBACK": grant.provider.loopback_host,
            "CONVMEM_INCREMENTAL_SITE": site.getusersitepackages(),
        },
    )
    argv = child_argv or [
        sys.executable,
        "-I",
        str(LIVE_WORKER),
        "t5-fault",
    ]
    with _serving_visibility_monitor(boundary, grant) as visibility:
        child = run_contained_child(argv, env=env)
        if child["returncode"] != CRASH_EXIT:
            raise CanaryRefused(
                "canary_fault_exit",
                f"expected crash exit {CRASH_EXIT}, got {child['returncode']}: {child['stderr']}",
            )
        disposition, replay = _observe_recovery_disposition(
            boundary,
            grant,
            pre_fault,
            unrelated,
        )
    assert_source_immutable(grant, source_token)
    receipt.faults_completed.append(fault_selector)
    receipt.recovery_dispositions.append(disposition)
    receipt.capsule_digest = pre_digest
    receipt.stage = expected_next
    next_index = LIVE_STAGE_ORDER.index(expected_next) + 1
    receipt.next_stage = LIVE_STAGE_ORDER[next_index]
    _persist_receipt(grant, receipt)
    return {
        "stage": expected_next,
        "fault": fault_selector,
        "child": {"pid": child["pid"], "returncode": child["returncode"], "pgid": child["pgid"]},
        "pre_fault_capsule": pre_digest,
        "replay_outcome": getattr(replay, "outcome", None),
        "disposition": disposition,
        "serving": {
            "mixed_s": visibility["mixed_s"],
            "samples": len(visibility.get("timeline") or []),
        },
    }


def freeze_live_evidence(
    _boundary: ProductionCanaryBoundary,
    grant: CanaryGrant,
    *,
    expected_sha256: str,
    gate0_report: Mapping[str, Any],
    sections: Mapping[str, Any],
    disposition: str | None = None,
) -> str:
    receipt = _require_stage(grant, "t6-evidence-frozen", expected_sha256=expected_sha256)
    if receipt.nonce != grant.nonce or receipt.grant_digest != expected_sha256:
        raise CanaryRefused("canary_evidence", "receipt does not match grant")
    required_faults = set(FAULT_STAGE)
    completed = list(receipt.faults_completed)
    if set(completed) != required_faults or len(completed) != len(required_faults):
        raise CanaryRefused(
            "canary_evidence",
            f"incomplete or repeated faults: {completed}",
        )
    if not receipt.append_identities:
        raise CanaryRefused("canary_evidence", "append receipts missing")
    if receipt.capsule_digest in {ZERO_DIGEST, "", None}:
        raise CanaryRefused("canary_evidence", "capsule digest missing")
    if not gate0_report:
        raise CanaryRefused("canary_evidence", "Gate 0 report missing")
    observed = list(receipt.recovery_dispositions)
    if len(observed) != len(required_faults):
        raise CanaryRefused("canary_evidence", "recovery dispositions incomplete")
    if all(item == "restored" for item in observed):
        derived = "restored"
    elif all(item == "converged" for item in observed):
        derived = "converged"
    else:
        derived = "recovery_unproven"
    if disposition is not None and disposition != derived:
        raise CanaryRefused(
            "canary_evidence",
            f"caller disposition {disposition} does not match observed {derived}",
        )
    payload = {
        "schema": LIVE_EVIDENCE_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hermetic": False,
        "execution_class": "exact-resource-live",
        "grant_digest": expected_sha256,
        "code_revision": grant.code_revision,
        "gate0": dict(gate0_report),
        "capsule_digest": receipt.capsule_digest,
        "unrelated_manifest_digest": receipt.unrelated_manifest_digest,
        "append_receipts": list(receipt.append_identities),
        "faults_completed": completed,
        "call_counters": dict(receipt.call_counters),
        "source_identity": dict(receipt.source_identity),
        "disposition": derived,
        "sections": dict(sections),
        "persistent_config_false_false": True,
    }
    path = Path(grant.evidence_dir) / LIVE_EVIDENCE_NAME
    if path.name == "p2-hermetic-evidence.json":
        raise CanaryRefused("canary_evidence", "live evidence cannot use hermetic filename")
    digest = write_evidence(path, payload)
    receipt.stage = "t6-evidence-frozen"
    receipt.next_stage = "t6-evidence-frozen"
    _persist_receipt(grant, receipt)
    return digest


def refuse_source_mutation() -> None:
    raise CanaryRefused("canary_source_immutable", "live P2 runtime cannot write source/session files")
