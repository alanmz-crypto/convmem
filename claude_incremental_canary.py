"""Hermetic Claude incremental JSONL canary boundary.

Canary-only module for Arc Claude Watch Parity Gate 2. Not registered in the
normal CLI or watcher. Live-source execution requires a separate Ryan grant.
"""

# pylint: disable=too-many-lines,duplicate-code

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from adapters.claude_session_jsonl import parse_complete_prefix
from incremental_jsonl import DURABLE_TRANSITIONS, IncrementalJsonlCoordinator
from incremental_jsonl_isolation import (
    IsolationBoundary,
    IsolationViolation,
    create_fresh_root,
    known_production_roots,
    sanitized_worker_env,
)

CANARY_MODE = "claude-incremental-canary-v1"
CRASH_EXIT = 86
_SOURCE_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_SAFE_DETAIL = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,63}$")
_SNAPSHOT_CAPTURE_PARTS = ("sources", "claude-capture")
_COORDINATOR_OUTCOMES = frozenset(
    {
        "committed",
        "unchanged",
        "bootstrap_required",
        "excluded",
        "excluded_after_checkpoint",
        "ineligible_format",
        "incremental_force_unsupported",
        "disabled",
        "invalid_state",
        "source_moved",
        "rolled_back",
    }
)
_COORDINATOR_MODES = frozenset(
    {
        "incremental",
        "unchanged",
        "initial_full",
        "replay_forward",
        "aborted",
        "rollback",
    }
)
_WATCHER_STATUSES = frozenset(
    {"inactive", "active", "failed", "activating", "unknown", "unavailable"}
)
_WATCHER_METHODS = frozenset({"systemctl", "hermetic", "test"})
_GATE0_PASS_VALUES = frozenset({"true", "false"})
_EVIDENCE_SECTION_SCHEMA: dict[str, frozenset[str]] = {
    "gate0": frozenset({"watcher", "network", "mode"}),
    "matrix": frozenset(
        {
            "first_outcome",
            "second_outcome",
            "third_outcome",
            "third_mode",
            "append_summarize",
            "append_reused",
        }
    ),
    "capture": frozenset(
        {
            "alias",
            "canonical_path",
            "device",
            "inode",
            "size",
            "complete_boundary",
            "prefix_sha256",
            "sha256",
            "physical_lines",
        }
    ),
    "coordinator": frozenset({"outcome", "mode", "counters", "reused_artifacts"}),
    "source": frozenset({"alias", "validated", "size"}),
}
EVIDENCE_SECTION_ALLOWLIST = frozenset(_EVIDENCE_SECTION_SCHEMA)
_CAPTURE_TRANSITIONS = (
    "before_snapshot_prepare",
    "after_snapshot_prepare",
    "before_snapshot_publish",
    "after_snapshot_publish",
    "before_source_revalidation",
    "after_source_revalidation",
)
_CREDENTIAL_MARKERS = ("API_KEY", "SECRET", "PASSWORD", "CREDENTIAL", "TOKEN")
PRODUCTION_ROOTS = known_production_roots()


@dataclass(frozen=True)
class FrozenSourceSpec:
    """Exact-source grant identity for read-only capture."""

    alias: str
    path: Path
    sha256: str
    size: int

    def __post_init__(self) -> None:
        validate_source_alias(self.alias)


@dataclass(frozen=True)
class SourceIdentityBinding:
    """Grant-bound source identity observed at capture entry."""

    canonical_path: str
    device: int
    inode: int
    size: int
    sha256: str


@dataclass(frozen=True)
class Gate0Authority:
    """In-process Gate 0 authority bound to one isolation boundary."""

    root: str
    token: str
    config_digest: str
    report: dict[str, Any]
    digest: str

    @classmethod
    def establish(
        cls,
        boundary: IsolationBoundary,
        *,
        hooks: Gate0ProbeHooks | None = None,
    ) -> Gate0Authority:
        report = gate0(hooks=hooks)
        config_digest = _config_digest(boundary)
        body = {
            "config_digest": config_digest,
            "report": report,
            "root": str(boundary.root.resolve()),
            "token": boundary.token,
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            root=str(boundary.root.resolve()),
            token=boundary.token,
            config_digest=config_digest,
            report=report,
            digest=digest,
        )

    def verify_live(self, boundary: IsolationBoundary) -> None:
        """Reject stale, cross-root, or cross-token authority replay."""
        if str(boundary.root.resolve()) != self.root:
            raise IsolationViolation("gate0 authority root mismatch")
        if boundary.token != self.token:
            raise IsolationViolation("gate0 authority token mismatch")
        if _config_digest(boundary) != self.config_digest:
            raise IsolationViolation("gate0 authority config mismatch")


@dataclass(frozen=True)
class SourceDescriptor:
    """Content-free source identity for evidence."""

    alias: str
    canonical_path: str
    device: int
    inode: int
    size: int
    complete_boundary: int
    prefix_sha256: str
    sha256: str
    physical_lines: int


@dataclass
class Gate0ProbeHooks:
    """Injectable probes for hermetic Gate 0 tests."""

    watcher_probe: Callable[[], dict[str, str]] | None = None
    network_self_test: Callable[[], dict[str, str]] | None = None


def gate0_watcher_probe() -> dict[str, str]:
    """Probe watcher state; inactive stdout is PASS even with nonzero exit."""
    try:
        completed = subprocess.run(
            ["systemctl", "--user", "is-active", "convmem-watch.service"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        stdout = (completed.stdout or "").strip()
        if stdout == "inactive":
            return {"status": "inactive", "method": "systemctl", "pass": "true"}
        if stdout in {"failed", "activating", "active"}:
            return {"status": stdout, "method": "systemctl", "pass": "false"}
        return {
            "status": stdout or "unknown",
            "method": "systemctl",
            "pass": "false",
            "detail": completed.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "unavailable",
            "method": "systemctl",
            "pass": "false",
            "detail": str(exc),
        }


def _default_network_self_test() -> dict[str, str]:
    import socket

    try:
        socket.create_connection(("203.0.113.1", 9), timeout=0.01)
        return {"pass": "false", "detail": "unexpected-success"}
    except OSError as exc:
        return {"pass": "true", "detail": type(exc).__name__}


def _config_digest(boundary: IsolationBoundary) -> str:
    config_path = boundary.layout["user_config"]
    if config_path.is_symlink():
        raise IsolationViolation("config path is symlinked")
    return hashlib.sha256(config_path.read_bytes()).hexdigest()


def _dir_open_flags(*, write: bool = False) -> int:
    flags = os.O_DIRECTORY | os.O_CLOEXEC
    if write:
        flags |= os.O_RDONLY
    else:
        flags |= os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _file_open_flags(*, write: bool = False, create: bool = False) -> int:
    flags = os.O_CLOEXEC
    if write:
        flags |= os.O_WRONLY
    else:
        flags |= os.O_RDONLY
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _verify_dir_entry_identity(parent_fd: int, name: str, st: os.stat_result) -> None:
    entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if (entry.st_dev, entry.st_ino) != (st.st_dev, st.st_ino):
        raise IsolationViolation("directory entry substitution detected")
    if stat.S_ISLNK(entry.st_mode):
        raise IsolationViolation("directory entry is symlinked")


def _open_boundary_subdir(
    boundary: IsolationBoundary,
    parts: tuple[str, ...],
    *,
    label: str,
) -> int:
    """Open a boundary subdirectory via anchored descriptors."""
    root_fd = os.open(str(boundary.root), _dir_open_flags())
    fd = root_fd
    try:
        for part in parts:
            if not part or part in {".", ".."} or os.sep in part:
                raise IsolationViolation(f"{label} invalid path component")
            try:
                os.mkdir(part, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child_fd = os.open(part, _dir_open_flags(), dir_fd=fd)
            try:
                child_st = os.fstat(child_fd)
                if not stat.S_ISDIR(child_st.st_mode):
                    raise IsolationViolation(f"{label} is not a directory")
                _verify_dir_entry_identity(fd, part, child_st)
            except Exception:
                os.close(child_fd)
                raise
            if fd != root_fd:
                os.close(fd)
            fd = child_fd
        if fd != root_fd:
            os.close(root_fd)
        return fd
    except Exception:
        if fd != root_fd:
            os.close(fd)
        os.close(root_fd)
        raise


def _publish_regular_file_dirfd(
    parent_fd: int,
    name: str,
    payload: bytes,
    *,
    label: str,
) -> os.stat_result:
    """Atomically publish one regular file under an already-open directory."""
    temp_name = f".{name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
    fd = -1
    try:
        fd = os.open(temp_name, _file_open_flags(write=True, create=True), 0o600, dir_fd=parent_fd)
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            written = os.write(fd, view[offset:])
            if written <= 0:
                raise OSError("snapshot short write")
            offset += written
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(temp_name, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
        result = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(result.st_mode):
            raise IsolationViolation(f"{label} is not a regular file")
        _verify_dir_entry_identity(parent_fd, name, result)
        return result
    except Exception:
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except OSError:
            pass
        try:
            os.unlink(name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    finally:
        if fd >= 0:
            os.close(fd)


def _remove_regular_file_dirfd(parent_fd: int, name: str) -> None:
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(entry.st_mode):
        raise IsolationViolation("snapshot cleanup target is not a regular file")
    os.unlink(name, dir_fd=parent_fd)
    os.fsync(parent_fd)


def snapshot_publication_paths(
    boundary: IsolationBoundary, alias: str
) -> tuple[Path, Path]:
    """Return capture directory and filename derived from the boundary."""
    validate_source_alias(alias)
    capture_dir = boundary.resolve_mutable(
        Path(*_SNAPSHOT_CAPTURE_PARTS),
        label="snapshot capture directory",
    )
    return capture_dir, Path(f"{alias}.jsonl")


def list_snapshot_artifacts(boundary: IsolationBoundary, alias: str) -> list[str]:
    """List regular snapshot artifacts for one alias under the capture directory."""
    capture_dir, filename = snapshot_publication_paths(boundary, alias)
    if not capture_dir.exists():
        return []
    artifacts: list[str] = []
    for entry in capture_dir.iterdir():
        if not entry.is_file():
            continue
        if entry.name == filename.name or entry.name.startswith(f".{filename.name}."):
            artifacts.append(str(entry.resolve()))
    return artifacts


def assert_no_snapshot_artifacts(boundary: IsolationBoundary, alias: str) -> None:
    """Fail closed when snapshot publication left residue behind."""
    artifacts = list_snapshot_artifacts(boundary, alias)
    if artifacts:
        names = ", ".join(sorted(artifacts))
        raise IsolationViolation(f"snapshot residue remains: {names}")
    for artifact in artifacts:
        if not _path_under_roots(Path(artifact), (boundary.root,)):
            raise IsolationViolation("snapshot residue escaped isolation root")


def _path_under_roots(path: Path, roots: tuple[Path, ...]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _assert_regular_non_symlink(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise IsolationViolation(f"{label} is symlinked")
    if not path.is_file():
        raise IsolationViolation(f"{label} is not a regular file")


def validate_source_alias(alias: str) -> str:
    """Reject aliases that could escape snapshot containment."""
    if not alias or alias in {".", ".."}:
        raise IsolationViolation("invalid source alias")
    if "/" in alias or "\\" in alias or os.sep in alias:
        raise IsolationViolation("source alias contains path separator")
    if not _SOURCE_ALIAS_PATTERN.fullmatch(alias):
        raise IsolationViolation("source alias not allowlisted")
    return alias


def derive_snapshot_destination(
    boundary: IsolationBoundary, alias: str
) -> Path:
    """Derive the snapshot path exclusively from a validated isolation boundary."""
    validate_source_alias(alias)
    relative = Path("sources") / "claude-capture" / f"{alias}.jsonl"
    return boundary.resolve_mutable(relative, label="snapshot destination")


def bind_frozen_source(
    spec: FrozenSourceSpec,
) -> tuple[SourceIdentityBinding, bytes]:
    """Open one grant-bound source read-only and return identity plus bytes."""
    path = spec.path
    if path.is_symlink():
        raise IsolationViolation("frozen source is symlinked")
    if not path.is_absolute():
        raise IsolationViolation("frozen source path is not absolute")
    canonical = path.resolve(strict=True)
    if str(canonical) != str(path):
        raise IsolationViolation("frozen source canonical path substituted")
    _assert_regular_non_symlink(canonical, label="frozen source")
    if _path_under_roots(canonical, PRODUCTION_ROOTS):
        raise IsolationViolation("frozen source aliases production root")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(str(canonical), flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise IsolationViolation("frozen source is not regular")
        if before.st_size != spec.size:
            raise IsolationViolation("size drift")
        data = os.read(fd, spec.size)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    if len(data) != spec.size:
        raise IsolationViolation("size drift")
    if (before.st_dev, before.st_ino, before.st_size) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
    ):
        raise IsolationViolation("source identity changed during read")
    digest = hashlib.sha256(data).hexdigest()
    if digest != spec.sha256:
        raise IsolationViolation("digest drift")
    binding = SourceIdentityBinding(
        canonical_path=str(canonical),
        device=int(before.st_dev),
        inode=int(before.st_ino),
        size=int(before.st_size),
        sha256=digest,
    )
    return binding, data


def validate_frozen_source(spec: FrozenSourceSpec) -> bytes:
    """Open the granted source read-only and validate exact identity."""
    _binding, data = bind_frozen_source(spec)
    return data


def revalidate_source_identity(
    spec: FrozenSourceSpec, binding: SourceIdentityBinding
) -> None:
    """Re-open the live source and reject identity or digest drift."""
    fresh, _data = bind_frozen_source(spec)
    if fresh != binding:
        raise IsolationViolation("live source identity changed during capture")


def capture_source(
    boundary: IsolationBoundary,
    spec: FrozenSourceSpec,
    *,
    fault: Callable[[str], None] | None = None,
) -> SourceDescriptor:
    """Copy the complete prefix atomically under an isolation-bound snapshot path."""
    capture_dir_fd = -1
    snapshot_name = ""

    def emit(name: str) -> None:
        if fault is not None:
            fault(name)

    try:
        emit("before_snapshot_prepare")
        binding, data = bind_frozen_source(spec)
        emit("after_snapshot_prepare")
        view = parse_complete_prefix(binding.canonical_path, raw=data)
        emit("before_snapshot_publish")
        _capture_dir, filename = snapshot_publication_paths(boundary, spec.alias)
        snapshot_name = filename.name
        capture_dir_fd = _open_boundary_subdir(
            boundary,
            _SNAPSHOT_CAPTURE_PARTS,
            label="snapshot capture directory",
        )
        copied_stat = _publish_regular_file_dirfd(
            capture_dir_fd,
            snapshot_name,
            view.raw_prefix,
            label="snapshot destination",
        )
        emit("after_snapshot_publish")
        emit("before_source_revalidation")
        try:
            revalidate_source_identity(spec, binding)
        except IsolationViolation:
            _remove_regular_file_dirfd(capture_dir_fd, snapshot_name)
            snapshot_name = ""
            assert_no_snapshot_artifacts(boundary, spec.alias)
            raise
        emit("after_source_revalidation")
        capture_dir, _filename = snapshot_publication_paths(boundary, spec.alias)
        copied_path = capture_dir / snapshot_name
        return SourceDescriptor(
            alias=spec.alias,
            canonical_path=str(copied_path.resolve()),
            device=int(copied_stat.st_dev),
            inode=int(copied_stat.st_ino),
            size=int(copied_stat.st_size),
            complete_boundary=view.complete_boundary,
            prefix_sha256=view.prefix_sha256,
            sha256=hashlib.sha256(view.raw_prefix).hexdigest(),
            physical_lines=view.raw_prefix.count(b"\n"),
        )
    except IsolationViolation:
        if capture_dir_fd >= 0 and snapshot_name:
            _remove_regular_file_dirfd(capture_dir_fd, snapshot_name)
        assert_no_snapshot_artifacts(boundary, spec.alias)
        raise
    finally:
        if capture_dir_fd >= 0:
            os.close(capture_dir_fd)


def _hermetic_gate0_hooks() -> Gate0ProbeHooks:
    return Gate0ProbeHooks(
        watcher_probe=lambda: {"status": "inactive", "method": "hermetic", "pass": "true"},
        network_self_test=lambda: {"pass": "true", "detail": "hermetic"},
    )


def gate0(*, hooks: Gate0ProbeHooks | None = None) -> dict[str, Any]:
    """Gate 0 checks before imports/writes; fail closed on indeterminate watcher."""
    hooks = hooks or Gate0ProbeHooks()
    watcher = (hooks.watcher_probe or gate0_watcher_probe)()
    if watcher.get("pass") != "true":
        raise IsolationViolation("watcher active or indeterminate")
    for name in os.environ:
        if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
            if name not in {"CONVMEM_INCREMENTAL_TOKEN"}:
                raise IsolationViolation(f"credential inherited: {name}")
    for override in (
        "CONVMEM_CONFIG",
        "CONVMEM_CHROMA_DIR",
        "CONVMEM_PROCESSED_LOG",
    ):
        if override in os.environ:
            raise IsolationViolation(f"production override present: {override}")
    network = (hooks.network_self_test or _default_network_self_test)()
    if network.get("pass") != "true":
        raise IsolationViolation(f"network self-test failed: {network}")
    return {
        "watcher": watcher,
        "network": network,
        "mode": CANARY_MODE,
    }


def establish_gate0_authority(
    boundary: IsolationBoundary,
    *,
    hooks: Gate0ProbeHooks | None = None,
) -> Gate0Authority:
    """Run Gate 0 and return root-bound in-process authority."""
    return Gate0Authority.establish(boundary, hooks=hooks)


def require_gate0_authority(
    boundary: IsolationBoundary,
    *,
    hooks: Gate0ProbeHooks | None = None,
) -> Gate0Authority:
    """Establish Gate 0 authority for one mutable command in this process."""
    authority = establish_gate0_authority(boundary, hooks=hooks)
    authority.verify_live(boundary)
    return authority


def assert_transition_coverage(
    declared: tuple[str, ...],
    observed: tuple[str, ...],
    *,
    label: str,
) -> None:
    """Fail closed unless both sides of every durable transition are observed."""
    covered: dict[str, set[str]] = {}
    for point in observed:
        side, separator, transition = point.partition("_")
        if not separator or side not in {"before", "after"}:
            continue
        covered.setdefault(transition, set()).add(side)
    missing = {
        transition
        for transition in declared
        if covered.get(transition) != {"before", "after"}
    }
    if missing:
        names = ", ".join(sorted(missing))
        raise IsolationViolation(f"{label} transition coverage missing: {names}")


def scrub_credentials(env: dict[str, str]) -> dict[str, str]:
    cleaned = dict(env)
    for name in list(cleaned):
        if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
            if name not in {"CONVMEM_INCREMENTAL_TOKEN"}:
                cleaned.pop(name, None)
    return cleaned


def prepare_fixture_env(
    parent: Path,
    *,
    count: int = 4,
    alias: str = "canary-fixture",
) -> tuple[Path, str, dict[str, str], Path, FrozenSourceSpec]:
    """Create scratch root, env, Claude fixture, and frozen spec."""
    parent_home = Path.home()
    root, token = create_fresh_root(parent)
    env = scrub_credentials(
        sanitized_worker_env(
            root,
            token,
            forbidden_roots=known_production_roots(home=parent_home),
        )
    )
    home = Path(env["HOME"])
    source = (
        home
        / ".claude"
        / "projects"
        / "canary-slug"
        / f"{alias}.jsonl"
    )
    source.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        json.dumps({"type": "system", "sessionId": "sess-claude-canary"}),
    ]
    for index in range(count):
        role = "user" if index % 2 == 0 else "assistant"
        content = f"canary-message-{index:05d}"
        row = {
            "type": role,
            "sessionId": "sess-claude-canary",
            "uuid": f"rec-{index:05d}",
            "cwd": "/tmp/canary",
            "isSidechain": False,
            "timestamp": f"2026-09-18T00:00:{index % 60:02d}Z",
            "message": {"role": role, "content": content},
        }
        rows.append(json.dumps(row, sort_keys=True))
    source.write_text("\n".join(rows) + "\n", encoding="utf-8")
    data = source.read_bytes()
    spec = FrozenSourceSpec(
        alias=alias,
        path=source,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
    )
    return root, token, env, source, spec


def install_fake_providers() -> None:
    import ingest

    def fake_summarize(text: str, **_kwargs) -> str:
        return f"summary:{hashlib.sha256(text.encode()).hexdigest()[:16]}"

    def fake_embed(text: str, **_kwargs) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(8)]

    def fake_distill(text: str, **_kwargs) -> list[dict[str, Any]]:
        del text
        return [
            {
                "type": "explanation",
                "title": "Hermetic Claude canary unit",
                "summary": "Synthetic knowledge unit for canary matrix.",
                "keywords": ["claude", "canary"],
                "confidence": 0.95,
                "domain": "general",
            }
        ]

    ingest.summarize = fake_summarize
    ingest.ollama_embed = fake_embed
    ingest.distill = fake_distill


def enable_incremental(boundary: IsolationBoundary) -> None:
    path = boundary.layout["user_config"]
    text = path.read_text(encoding="utf-8")
    text = text.replace("enabled = false", "enabled = true", 1)
    path.write_text(text, encoding="utf-8")


def run_coordinator(
    boundary: IsolationBoundary,
    source: Path,
    *,
    chunk_size: int = 2,
    overlap: int = 0,
) -> dict[str, Any]:
    install_fake_providers()
    enable_incremental(boundary)
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary,
        source,
        enabled=True,
        chunk_size=chunk_size,
        overlap=overlap,
    ).run()
    return {
        "outcome": result.outcome,
        "mode": result.mode,
        "counters": result.counters.as_dict(),
        "reused_artifacts": result.reused_artifacts,
    }


def run_hermetic_matrix(
    boundary: IsolationBoundary,
    source: Path,
) -> dict[str, Any]:
    """Exercise baseline, unchanged replay, and append under isolation."""
    install_fake_providers()
    enable_incremental(boundary)
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    ).run()
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    ).run()
    with source.open("ab") as handle:
        handle.write(
            json.dumps(
                {
                    "type": "user",
                    "sessionId": "sess-claude-canary",
                    "uuid": "rec-append",
                    "cwd": "/tmp/canary",
                    "isSidechain": False,
                    "timestamp": "2026-09-18T00:01:00Z",
                    "message": {
                        "role": "user",
                        "content": "canary-message-append",
                    },
                },
                sort_keys=True,
            ).encode()
            + b"\n"
        )
    third = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=2, overlap=0
    ).run()
    return {
        "first_outcome": first.outcome,
        "second_outcome": second.outcome,
        "third_outcome": third.outcome,
        "third_mode": third.mode,
        "append_summarize": third.counters.summarize,
        "append_reused": third.reused_artifacts,
    }


_REBUILD_OUTCOME = re.compile(r"^rebuild_required:[a-z_]+$")
_EVIDENCE_INT_MAX = 1_000_000_000


def _validate_enum(value: Any, *, label: str, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise IsolationViolation(f"{label} is not an allowed enum")
    return value


def _validate_bool(value: Any, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise IsolationViolation(f"{label} must be a boolean")
    return value


def _validate_bounded_int(
    value: Any,
    *,
    label: str,
    minimum: int = 0,
    maximum: int = _EVIDENCE_INT_MAX,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise IsolationViolation(f"{label} must be an integer")
    if value < minimum or value > maximum:
        raise IsolationViolation(f"{label} out of bounds")
    return value


def _validate_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_HEX.fullmatch(value):
        raise IsolationViolation(f"{label} must be a sha256 hex digest")
    return value


def _validate_safe_detail(value: Any, *, label: str) -> str:
    if value == "":
        return ""
    if not isinstance(value, str) or not _SAFE_DETAIL.fullmatch(value):
        raise IsolationViolation(f"{label} must be a safe detail token")
    return value


def _validate_coordinator_outcome(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise IsolationViolation(f"{label} must be a coordinator outcome")
    if value in _COORDINATOR_OUTCOMES or _REBUILD_OUTCOME.fullmatch(value):
        return value
    raise IsolationViolation(f"{label} is not an allowed coordinator outcome")


def _validate_safe_absolute_path(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("/"):
        raise IsolationViolation(f"{label} must be an absolute path")
    if "\n" in value or "\r" in value or "\x00" in value:
        raise IsolationViolation(f"{label} contains disallowed content")
    if "canary-message" in value:
        raise IsolationViolation(f"{label} contains transcript-like content")
    candidate = Path(value)
    if candidate.is_symlink():
        raise IsolationViolation(f"{label} is symlinked")
    return value


def _validate_gate0_section(section: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    if "mode" in section:
        validated["mode"] = _validate_enum(
            section["mode"], label="gate0.mode", allowed=frozenset({CANARY_MODE})
        )
    if "watcher" in section:
        watcher = section["watcher"]
        if not isinstance(watcher, dict):
            raise IsolationViolation("gate0.watcher must be a mapping")
        allowed = frozenset({"status", "method", "pass", "detail"})
        unknown = set(watcher) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise IsolationViolation(f"gate0.watcher contains unknown keys: {names}")
        nested: dict[str, Any] = {}
        if "status" in watcher:
            nested["status"] = _validate_enum(
                watcher["status"],
                label="gate0.watcher.status",
                allowed=_WATCHER_STATUSES,
            )
        if "method" in watcher:
            nested["method"] = _validate_enum(
                watcher["method"],
                label="gate0.watcher.method",
                allowed=_WATCHER_METHODS,
            )
        if "pass" in watcher:
            nested["pass"] = _validate_enum(
                watcher["pass"],
                label="gate0.watcher.pass",
                allowed=_GATE0_PASS_VALUES,
            )
        if "detail" in watcher:
            nested["detail"] = _validate_safe_detail(
                watcher["detail"], label="gate0.watcher.detail"
            )
        validated["watcher"] = nested
    if "network" in section:
        network = section["network"]
        if not isinstance(network, dict):
            raise IsolationViolation("gate0.network must be a mapping")
        allowed = frozenset({"pass", "detail"})
        unknown = set(network) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise IsolationViolation(f"gate0.network contains unknown keys: {names}")
        nested = {}
        if "pass" in network:
            nested["pass"] = _validate_enum(
                network["pass"],
                label="gate0.network.pass",
                allowed=_GATE0_PASS_VALUES,
            )
        if "detail" in network:
            nested["detail"] = _validate_safe_detail(
                network["detail"], label="gate0.network.detail"
            )
        validated["network"] = nested
    return validated


def _validate_matrix_section(section: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    for key in ("first_outcome", "second_outcome", "third_outcome"):
        if key in section:
            validated[key] = _validate_coordinator_outcome(
                section[key], label=f"matrix.{key}"
            )
    if "third_mode" in section:
        validated["third_mode"] = _validate_enum(
            section["third_mode"],
            label="matrix.third_mode",
            allowed=_COORDINATOR_MODES,
        )
    for key in ("append_summarize", "append_reused"):
        if key in section:
            validated[key] = _validate_bounded_int(section[key], label=f"matrix.{key}")
    return validated


def _validate_capture_section(section: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    if "alias" in section:
        validated["alias"] = validate_source_alias(str(section["alias"]))
    if "canonical_path" in section:
        validated["canonical_path"] = _validate_safe_absolute_path(
            section["canonical_path"], label="capture.canonical_path"
        )
    for key in ("device", "inode", "size", "complete_boundary", "physical_lines"):
        if key in section:
            validated[key] = _validate_bounded_int(section[key], label=f"capture.{key}")
    for key in ("prefix_sha256", "sha256"):
        if key in section:
            validated[key] = _validate_sha256(section[key], label=f"capture.{key}")
    return validated


def _validate_coordinator_section(section: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    if "outcome" in section:
        validated["outcome"] = _validate_coordinator_outcome(
            section["outcome"], label="coordinator.outcome"
        )
    if "mode" in section:
        validated["mode"] = _validate_enum(
            section["mode"], label="coordinator.mode", allowed=_COORDINATOR_MODES
        )
    if "reused_artifacts" in section:
        validated["reused_artifacts"] = _validate_bounded_int(
            section["reused_artifacts"], label="coordinator.reused_artifacts"
        )
    if "counters" in section:
        counters = section["counters"]
        if not isinstance(counters, dict):
            raise IsolationViolation("coordinator.counters must be a mapping")
        allowed = frozenset({"summarize", "embed", "distill", "chroma_upsert", "total"})
        unknown = set(counters) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise IsolationViolation(f"coordinator.counters contains unknown keys: {names}")
        validated["counters"] = {
            key: _validate_bounded_int(counters[key], label=f"coordinator.counters.{key}")
            for key in counters
            if key in allowed
        }
    return validated


def _validate_source_section(section: dict[str, Any]) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    if "alias" in section:
        validated["alias"] = validate_source_alias(str(section["alias"]))
    if "validated" in section:
        validated["validated"] = _validate_bool(section["validated"], label="source.validated")
    if "size" in section:
        validated["size"] = _validate_bounded_int(section["size"], label="source.size")
    return validated


_SECTION_VALIDATORS = {
    "gate0": _validate_gate0_section,
    "matrix": _validate_matrix_section,
    "capture": _validate_capture_section,
    "coordinator": _validate_coordinator_section,
    "source": _validate_source_section,
}


def _evidence_key_allowed(key: str, schema: frozenset[str]) -> bool:
    if key not in schema:
        return False
    upper = key.upper()
    if any(marker in upper for marker in _CREDENTIAL_MARKERS):
        return False
    return True


def _validate_evidence_section(name: str, section: Any) -> dict[str, Any]:
    schema = _EVIDENCE_SECTION_SCHEMA.get(name)
    if schema is None:
        raise IsolationViolation(f"unknown evidence section: {name}")
    if not isinstance(section, dict):
        raise IsolationViolation(f"evidence section {name} must be a mapping")
    unknown = set(section) - schema
    if unknown:
        names = ", ".join(sorted(unknown))
        raise IsolationViolation(f"evidence section {name} has unknown keys: {names}")
    for key in section:
        if not _evidence_key_allowed(key, schema):
            raise IsolationViolation(f"evidence section {name} rejects key: {key}")
    validator = _SECTION_VALIDATORS[name]
    return validator(section)


def assemble_evidence(**sections: Any) -> dict[str, Any]:
    """Return content-free evidence with a closed typed section allowlist."""
    unknown = set(sections) - EVIDENCE_SECTION_ALLOWLIST
    if unknown:
        names = ", ".join(sorted(unknown))
        raise IsolationViolation(f"unknown evidence sections: {names}")
    validated = {
        name: _validate_evidence_section(name, section)
        for name, section in sections.items()
    }
    payload = {"mode": CANARY_MODE, "sections": validated}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["evidence_digest"] = digest
    return payload


def worker_env(
    root: Path,
    token: str,
    *,
    parent_home: Path | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    env = scrub_credentials(
        sanitized_worker_env(
            root,
            token,
            forbidden_roots=known_production_roots(
                home=parent_home or Path.home()
            ),
        )
    )
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    env["CONVMEM_CLAUDE_CANARY_MODE"] = CANARY_MODE
    if extra:
        env.update(extra)
    return env


def run_worker(
    command: str,
    *,
    root: Path,
    token: str,
    source: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    worker = Path(__file__).resolve().parent / "tests" / "claude_incremental_canary_worker.py"
    args = [sys.executable, "-I", str(worker), command]
    if source is not None:
        args.append(str(source))
    return subprocess.run(
        args,
        cwd=root,
        env=worker_env(root, token, extra=extra_env),
        close_fds=True,
        start_new_session=True,
        capture_output=True,
        text=True,
        check=False,
    )


__all__ = [
    "CANARY_MODE",
    "CRASH_EXIT",
    "DURABLE_TRANSITIONS",
    "EVIDENCE_SECTION_ALLOWLIST",
    "_CAPTURE_TRANSITIONS",
    "FrozenSourceSpec",
    "Gate0Authority",
    "Gate0ProbeHooks",
    "PRODUCTION_ROOTS",
    "SourceDescriptor",
    "SourceIdentityBinding",
    "assemble_evidence",
    "assert_no_snapshot_artifacts",
    "assert_transition_coverage",
    "bind_frozen_source",
    "capture_source",
    "derive_snapshot_destination",
    "enable_incremental",
    "establish_gate0_authority",
    "gate0",
    "gate0_watcher_probe",
    "_hermetic_gate0_hooks",
    "install_fake_providers",
    "list_snapshot_artifacts",
    "prepare_fixture_env",
    "revalidate_source_identity",
    "require_gate0_authority",
    "run_coordinator",
    "run_hermetic_matrix",
    "run_worker",
    "scrub_credentials",
    "snapshot_publication_paths",
    "validate_frozen_source",
    "validate_source_alias",
    "worker_env",
]
