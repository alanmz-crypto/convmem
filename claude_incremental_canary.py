"""Hermetic Claude incremental JSONL canary boundary.

Canary-only module for Arc Claude Watch Parity Gate 2. Not registered in the
normal CLI or watcher. Live-source execution requires a separate Ryan grant.

Capability-bound redesign: hold the isolation root directory descriptor after a
single validation; publish only via directory-relative atomic rename after all
fallible checks; Gate 0 is internal-only; evidence is closed typed objects.
"""

# pylint: disable=too-many-lines,duplicate-code,too-many-arguments,too-many-locals

from __future__ import annotations

import enum
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from adapters.claude_session_jsonl import parse_complete_prefix
from incremental_jsonl import DURABLE_TRANSITIONS, IncrementalJsonlCoordinator
from incremental_jsonl_isolation import (
    ISOLATION_MODE,
    ISOLATION_MODE_ENV,
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
_REBUILD_REASON = re.compile(r"^[a-z_]+$")
_SNAPSHOT_CAPTURE_PARTS = ("sources", "claude-capture")
_MARKER_NAME = ".convmem-jsonl-production-root"
_CONFIG_REL_PARTS = ("home", ".config", "convmem", "config.toml")
_CREDENTIAL_MARKERS = ("API_KEY", "SECRET", "PASSWORD", "CREDENTIAL", "TOKEN")
PRODUCTION_ROOTS = known_production_roots()
_EVIDENCE_INT_MAX = 1_000_000_000

_CAPTURE_TRANSITIONS = (
    "before_snapshot_prepare",
    "after_snapshot_prepare",
    "before_temp_stage",
    "after_temp_stage",
    "before_source_revalidation",
    "after_source_revalidation",
    "before_snapshot_publish",
    "after_snapshot_publish",
)


# ---------------------------------------------------------------------------
# Closed enums and value objects
# ---------------------------------------------------------------------------


class CanaryMode(enum.StrEnum):
    V1 = CANARY_MODE


class WatcherStatus(enum.StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    FAILED = "failed"
    ACTIVATING = "activating"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class WatcherMethod(enum.StrEnum):
    SYSTEMCTL = "systemctl"
    HERMETIC = "hermetic"
    TEST = "test"


class PassToken(enum.StrEnum):
    TRUE = "true"
    FALSE = "false"


class CoordinatorOutcome(enum.StrEnum):
    COMMITTED = "committed"
    UNCHANGED = "unchanged"
    BOOTSTRAP_REQUIRED = "bootstrap_required"
    EXCLUDED = "excluded"
    EXCLUDED_AFTER_CHECKPOINT = "excluded_after_checkpoint"
    INELIGIBLE_FORMAT = "ineligible_format"
    INCREMENTAL_FORCE_UNSUPPORTED = "incremental_force_unsupported"
    DISABLED = "disabled"
    INVALID_STATE = "invalid_state"
    SOURCE_MOVED = "source_moved"
    ROLLED_BACK = "rolled_back"


class CoordinatorMode(enum.StrEnum):
    INCREMENTAL = "incremental"
    UNCHANGED = "unchanged"
    INITIAL_FULL = "initial_full"
    REPLAY_FORWARD = "replay_forward"
    ABORTED = "aborted"
    ROLLBACK = "rollback"


def _reject_coercion(value: Any, *, label: str, expected: str) -> None:
    if isinstance(value, bool) and expected != "bool":
        raise IsolationViolation(f"{label} must be a {expected}")
    if expected == "str" and not isinstance(value, str):
        raise IsolationViolation(f"{label} must be a {expected}")
    if expected == "int" and (isinstance(value, bool) or not isinstance(value, int)):
        raise IsolationViolation(f"{label} must be a {expected}")
    if expected == "bool" and not isinstance(value, bool):
        raise IsolationViolation(f"{label} must be a {expected}")


@dataclass(frozen=True)
class SourceAlias:
    """Allowlisted source alias — never accepts integers or path separators."""

    value: str

    def __post_init__(self) -> None:
        _reject_coercion(self.value, label="source alias", expected="str")
        if not self.value or self.value in {".", ".."}:
            raise IsolationViolation("invalid source alias")
        if "/" in self.value or "\\" in self.value or os.sep in self.value:
            raise IsolationViolation("source alias contains path separator")
        if not _SOURCE_ALIAS_PATTERN.fullmatch(self.value):
            raise IsolationViolation("source alias not allowlisted")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RelativePath:
    """Validated relative path under the isolation root — never absolute."""

    parts: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.parts:
            raise IsolationViolation("relative path is empty")
        for part in self.parts:
            _reject_coercion(part, label="relative path component", expected="str")
            if not part or part in {".", ".."} or os.sep in part or "/" in part or "\\" in part:
                raise IsolationViolation("relative path component invalid")
            if part.startswith("/"):
                raise IsolationViolation("relative path must not be absolute")

    @classmethod
    def from_parts(cls, *parts: str) -> RelativePath:
        return cls(parts=tuple(parts))

    def joined(self) -> str:
        return "/".join(self.parts)

    def __str__(self) -> str:
        return self.joined()


@dataclass(frozen=True)
class DetailToken:
    """Closed detail token for evidence — not free-form transcript text."""

    value: str

    def __post_init__(self) -> None:
        _reject_coercion(self.value, label="detail", expected="str")
        if self.value == "":
            return
        if (
            "canary-message" in self.value
            or "/" in self.value
            or "\\" in self.value
            or "\n" in self.value
        ):
            raise IsolationViolation("detail contains transcript-like content")
        if not _SAFE_DETAIL.fullmatch(self.value):
            raise IsolationViolation("detail must be a safe detail token")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Sha256Digest:
    value: str

    def __post_init__(self) -> None:
        _reject_coercion(self.value, label="sha256", expected="str")
        if not _SHA256_HEX.fullmatch(self.value):
            raise IsolationViolation("sha256 must be a sha256 hex digest")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class BoundedInt:
    value: int

    def __post_init__(self) -> None:
        _reject_coercion(self.value, label="bounded int", expected="int")
        if self.value < 0 or self.value > _EVIDENCE_INT_MAX:
            raise IsolationViolation("bounded int out of bounds")

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True)
class RebuildOutcome:
    reason: str

    def __post_init__(self) -> None:
        _reject_coercion(self.reason, label="rebuild reason", expected="str")
        if not _REBUILD_REASON.fullmatch(self.reason):
            raise IsolationViolation("rebuild reason is not an allowed enum")

    def as_value(self) -> str:
        return f"rebuild_required:{self.reason}"


def _parse_coordinator_outcome(value: Any, *, label: str) -> CoordinatorOutcome | RebuildOutcome:
    if isinstance(value, CoordinatorOutcome):
        return value
    if isinstance(value, RebuildOutcome):
        return value
    _reject_coercion(value, label=label, expected="str")
    try:
        return CoordinatorOutcome(value)
    except ValueError:
        pass
    if isinstance(value, str) and value.startswith("rebuild_required:"):
        return RebuildOutcome(reason=value.split(":", 1)[1])
    raise IsolationViolation(f"{label} is not an allowed coordinator outcome")


def _parse_coordinator_mode(value: Any, *, label: str) -> CoordinatorMode:
    if isinstance(value, CoordinatorMode):
        return value
    _reject_coercion(value, label=label, expected="str")
    try:
        return CoordinatorMode(value)
    except ValueError as exc:
        raise IsolationViolation(f"{label} is not an allowed enum") from exc


def _outcome_to_str(value: CoordinatorOutcome | RebuildOutcome) -> str:
    if isinstance(value, RebuildOutcome):
        return value.as_value()
    return str(value)


@dataclass(frozen=True)
class Gate0WatcherEvidence:
    status: WatcherStatus
    method: WatcherMethod
    passed: PassToken
    detail: DetailToken | None = None

    def to_mapping(self) -> dict[str, str]:
        payload = {
            "status": str(self.status),
            "method": str(self.method),
            "pass": str(self.passed),
        }
        if self.detail is not None:
            payload["detail"] = str(self.detail)
        return payload


@dataclass(frozen=True)
class Gate0NetworkEvidence:
    passed: PassToken
    detail: DetailToken | None = None

    def to_mapping(self) -> dict[str, str]:
        payload = {"pass": str(self.passed)}
        if self.detail is not None:
            payload["detail"] = str(self.detail)
        return payload


@dataclass(frozen=True)
class Gate0Evidence:
    mode: CanaryMode
    watcher: Gate0WatcherEvidence
    network: Gate0NetworkEvidence

    def to_mapping(self) -> dict[str, Any]:
        return {
            "mode": str(self.mode),
            "watcher": self.watcher.to_mapping(),
            "network": self.network.to_mapping(),
        }


@dataclass(frozen=True)
class MatrixEvidence:
    first_outcome: CoordinatorOutcome | RebuildOutcome | None = None
    second_outcome: CoordinatorOutcome | RebuildOutcome | None = None
    third_outcome: CoordinatorOutcome | RebuildOutcome | None = None
    third_mode: CoordinatorMode | None = None
    append_summarize: BoundedInt | None = None
    append_reused: BoundedInt | None = None

    def to_mapping(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.first_outcome is not None:
            payload["first_outcome"] = _outcome_to_str(self.first_outcome)
        if self.second_outcome is not None:
            payload["second_outcome"] = _outcome_to_str(self.second_outcome)
        if self.third_outcome is not None:
            payload["third_outcome"] = _outcome_to_str(self.third_outcome)
        if self.third_mode is not None:
            payload["third_mode"] = str(self.third_mode)
        if self.append_summarize is not None:
            payload["append_summarize"] = int(self.append_summarize)
        if self.append_reused is not None:
            payload["append_reused"] = int(self.append_reused)
        return payload


@dataclass(frozen=True)
class CaptureEvidence:
    alias: SourceAlias
    relative_path: RelativePath
    device: BoundedInt
    inode: BoundedInt
    size: BoundedInt
    complete_boundary: BoundedInt
    prefix_sha256: Sha256Digest
    sha256: Sha256Digest
    physical_lines: BoundedInt

    def to_mapping(self) -> dict[str, Any]:
        return {
            "alias": str(self.alias),
            "relative_path": str(self.relative_path),
            "device": int(self.device),
            "inode": int(self.inode),
            "size": int(self.size),
            "complete_boundary": int(self.complete_boundary),
            "prefix_sha256": str(self.prefix_sha256),
            "sha256": str(self.sha256),
            "physical_lines": int(self.physical_lines),
        }


@dataclass(frozen=True)
class CoordinatorCountersEvidence:
    summarize: BoundedInt | None = None
    embed: BoundedInt | None = None
    distill: BoundedInt | None = None
    chroma_upsert: BoundedInt | None = None
    total: BoundedInt | None = None

    def to_mapping(self) -> dict[str, int]:
        payload: dict[str, int] = {}
        for name in ("summarize", "embed", "distill", "chroma_upsert", "total"):
            value = getattr(self, name)
            if value is not None:
                payload[name] = int(value)
        return payload


@dataclass(frozen=True)
class CoordinatorEvidence:
    outcome: CoordinatorOutcome | RebuildOutcome | None = None
    mode: CoordinatorMode | None = None
    counters: CoordinatorCountersEvidence | None = None
    reused_artifacts: BoundedInt | None = None

    def to_mapping(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.outcome is not None:
            payload["outcome"] = _outcome_to_str(self.outcome)
        if self.mode is not None:
            payload["mode"] = str(self.mode)
        if self.counters is not None:
            payload["counters"] = self.counters.to_mapping()
        if self.reused_artifacts is not None:
            payload["reused_artifacts"] = int(self.reused_artifacts)
        return payload


@dataclass(frozen=True)
class SourceEvidence:
    alias: SourceAlias
    validated: bool
    size: BoundedInt

    def __post_init__(self) -> None:
        _reject_coercion(self.validated, label="source.validated", expected="bool")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "alias": str(self.alias),
            "validated": self.validated,
            "size": int(self.size),
        }


EVIDENCE_SECTION_ALLOWLIST = frozenset(
    {"gate0", "matrix", "capture", "coordinator", "source"}
)

_SECTION_TYPES = {
    "gate0": Gate0Evidence,
    "matrix": MatrixEvidence,
    "capture": CaptureEvidence,
    "coordinator": CoordinatorEvidence,
    "source": SourceEvidence,
}


def _reject_mapping_evidence(value: Any, *, label: str) -> None:
    if isinstance(value, Mapping) and not is_dataclass(value):
        raise IsolationViolation(f"{label} must be a closed evidence object, not a mapping")
    if isinstance(value, dict):
        raise IsolationViolation(f"{label} must be a closed evidence object, not a mapping")


def assemble_evidence(**sections: Any) -> dict[str, Any]:
    """Serialize and hash only validated closed evidence objects."""
    unknown = set(sections) - EVIDENCE_SECTION_ALLOWLIST
    if unknown:
        names = ", ".join(sorted(unknown))
        raise IsolationViolation(f"unknown evidence sections: {names}")
    validated: dict[str, Any] = {}
    for name, section in sections.items():
        _reject_mapping_evidence(section, label=f"evidence section {name}")
        expected = _SECTION_TYPES[name]
        if not isinstance(section, expected):
            raise IsolationViolation(
                f"evidence section {name} must be {expected.__name__}"
            )
        for item in fields(section):
            getattr(section, item.name)
        validated[name] = section.to_mapping()
    payload = {"mode": CANARY_MODE, "sections": validated}
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["evidence_digest"] = digest
    return payload


# ---------------------------------------------------------------------------
# Source grant types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrozenSourceSpec:
    """Exact-source grant identity for read-only capture."""

    alias: str
    path: Path
    sha256: str
    size: int

    def __post_init__(self) -> None:
        validate_source_alias(self.alias)
        _reject_coercion(self.sha256, label="frozen source sha256", expected="str")
        _reject_coercion(self.size, label="frozen source size", expected="int")
        if not _SHA256_HEX.fullmatch(self.sha256):
            raise IsolationViolation("frozen source sha256 must be a sha256 hex digest")


@dataclass(frozen=True)
class SourceIdentityBinding:
    """Grant-bound source identity observed at capture entry."""

    canonical_path: str
    device: int
    inode: int
    size: int
    sha256: str


@dataclass(frozen=True)
class SourceDescriptor:
    """Content-free source identity for evidence (relative path only)."""

    alias: str
    relative_path: str
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


# ---------------------------------------------------------------------------
# Isolation root capability — open once, never reopen by pathname
# ---------------------------------------------------------------------------


@dataclass
class IsolationRootCapability:
    """Held isolation-root directory descriptor and bound stat identity."""

    root_fd: int
    st_dev: int
    st_ino: int
    token: str
    config_digest: str
    _closed: bool = field(default=False, repr=False)

    def close(self) -> None:
        if not self._closed and self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1
            self._closed = True

    def __enter__(self) -> IsolationRootCapability:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def assert_identity(self) -> None:
        if self._closed or self.root_fd < 0:
            raise IsolationViolation("isolation root capability closed")
        current = os.fstat(self.root_fd)
        if (current.st_dev, current.st_ino) != (self.st_dev, self.st_ino):
            raise IsolationViolation("isolation root identity changed")
        if not stat.S_ISDIR(current.st_mode):
            raise IsolationViolation("isolation root is not a directory")

    def assert_still_bound(self, boundary: IsolationBoundary) -> None:
        """Refuse replaced roots, stale markers, or replaced configuration."""
        self.assert_identity()
        marker_fd = os.open(
            _MARKER_NAME,
            _file_open_flags(),
            dir_fd=self.root_fd,
        )
        try:
            marker_st = os.fstat(marker_fd)
            if not stat.S_ISREG(marker_st.st_mode):
                raise IsolationViolation("isolation freshness token mismatch")
            token = os.read(marker_fd, 128).decode("ascii")
        finally:
            os.close(marker_fd)
        if token != self.token or token != boundary.token:
            raise IsolationViolation("isolation freshness token mismatch")
        try:
            path_st = os.stat(str(boundary.root), follow_symlinks=False)
        except OSError as exc:
            raise IsolationViolation("isolation root path unavailable") from exc
        if (path_st.st_dev, path_st.st_ino) != (self.st_dev, self.st_ino):
            raise IsolationViolation("isolation root replaced at pathname")
        if _config_digest_via_root(self) != self.config_digest:
            raise IsolationViolation("gate0 authority config mismatch")

    def open_subdir(self, parts: tuple[str, ...], *, label: str) -> int:
        """Resolve and create descendants relative to the held root descriptor."""
        self.assert_identity()
        fd = self.root_fd
        owned: list[int] = []
        try:
            for part in parts:
                if not part or part in {".", ".."} or os.sep in part or "/" in part:
                    raise IsolationViolation(f"{label} invalid path component")
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                try:
                    child_fd = os.open(part, _dir_open_flags(), dir_fd=fd)
                except OSError as exc:
                    raise IsolationViolation(f"{label} is symlinked") from exc
                try:
                    child_st = os.fstat(child_fd)
                    if not stat.S_ISDIR(child_st.st_mode):
                        raise IsolationViolation(f"{label} is not a directory")
                    _verify_dir_entry_identity(fd, part, child_st)
                except Exception:
                    os.close(child_fd)
                    raise
                owned.append(child_fd)
                fd = child_fd
            # Return the leaf; close intermediate descriptors only.
            if not owned:
                return self.root_fd
            leaf = owned.pop()
            for handle in owned:
                os.close(handle)
            owned.clear()
            return leaf
        except Exception:
            for handle in reversed(owned):
                os.close(handle)
            raise


def _dir_open_flags() -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
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


def _config_digest_via_root(root_cap: IsolationRootCapability) -> str:
    """Read configuration bytes via the held root descriptor only."""
    root_cap.assert_identity()
    parent_fd = root_cap.root_fd
    owned: list[int] = []
    try:
        for part in _CONFIG_REL_PARTS[:-1]:
            child_fd = os.open(part, _dir_open_flags(), dir_fd=parent_fd)
            owned.append(child_fd)
            parent_fd = child_fd
        name = _CONFIG_REL_PARTS[-1]
        fd = os.open(name, _file_open_flags(), dir_fd=parent_fd)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                raise IsolationViolation("config path is not a regular file")
            data = os.read(fd, st.st_size)
        finally:
            os.close(fd)
        return hashlib.sha256(data).hexdigest()
    finally:
        for handle in reversed(owned):
            os.close(handle)


def open_isolation_root(boundary: IsolationBoundary) -> IsolationRootCapability:
    """Open and validate the isolation root once; retain descriptor + identity."""
    if boundary.root.is_symlink():
        raise IsolationViolation("isolation root is symlinked")
    root_fd = os.open(str(boundary.root), _dir_open_flags())
    try:
        st = os.fstat(root_fd)
        if not stat.S_ISDIR(st.st_mode):
            raise IsolationViolation("isolation root is not a directory")
        marker_fd = os.open(_MARKER_NAME, _file_open_flags(), dir_fd=root_fd)
        try:
            marker_st = os.fstat(marker_fd)
            if not stat.S_ISREG(marker_st.st_mode):
                raise IsolationViolation("isolation freshness token mismatch")
            token = os.read(marker_fd, 128).decode("ascii")
        finally:
            os.close(marker_fd)
        if token != boundary.token:
            raise IsolationViolation("isolation freshness token mismatch")
        path_st = os.stat(str(boundary.root), follow_symlinks=False)
        if (path_st.st_dev, path_st.st_ino) != (st.st_dev, st.st_ino):
            raise IsolationViolation("isolation root path identity mismatch")
        cap = IsolationRootCapability(
            root_fd=root_fd,
            st_dev=int(st.st_dev),
            st_ino=int(st.st_ino),
            token=token,
            config_digest="",
        )
        digest = _config_digest_via_root(cap)
        cap.config_digest = digest
        root_fd = -1
        return cap
    finally:
        if root_fd >= 0:
            os.close(root_fd)


# ---------------------------------------------------------------------------
# Publication — stage temp, revalidate, then final atomic rename
# ---------------------------------------------------------------------------


def _stage_regular_file_dirfd(
    parent_fd: int,
    name: str,
    payload: bytes,
) -> str:
    """Write and fsync a temporary file beneath the anchored destination directory."""
    temp_name = f".{name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
    fd = os.open(
        temp_name,
        _file_open_flags(write=True, create=True),
        0o600,
        dir_fd=parent_fd,
    )
    try:
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            written = os.write(fd, view[offset:])
            if written <= 0:
                raise OSError("snapshot short write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    return temp_name


def _publish_staged_rename(
    parent_fd: int,
    temp_name: str,
    final_name: str,
) -> os.stat_result:
    """Directory-relative atomic rename — final infallible publication transition."""
    try:
        existing = os.stat(final_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        existing = None
    if existing is not None:
        if stat.S_ISLNK(existing.st_mode):
            raise IsolationViolation("snapshot destination is symlinked")
        if not stat.S_ISREG(existing.st_mode):
            raise IsolationViolation("snapshot destination is not a regular file")
    try:
        temp_st = os.stat(temp_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise IsolationViolation("staged snapshot missing before publish") from exc
    if not stat.S_ISREG(temp_st.st_mode):
        raise IsolationViolation("staged snapshot is not a regular file")
    os.replace(temp_name, final_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    os.fsync(parent_fd)
    return os.stat(final_name, dir_fd=parent_fd, follow_symlinks=False)


def _unlink_dirfd(parent_fd: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except FileNotFoundError:
        return


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


def validate_source_alias(alias: Any) -> str:
    """Reject aliases that could escape snapshot containment — no coercion."""
    if not isinstance(alias, str):
        raise IsolationViolation("source alias must be a str")
    return str(SourceAlias(value=alias))


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
    hooks: Gate0ProbeHooks | None = None,
) -> SourceDescriptor:
    """Copy the complete prefix under isolation; publication is the final step."""
    root_cap: IsolationRootCapability | None = None
    capture_dir_fd = -1
    temp_name: str | None = None
    snapshot_name = ""
    published = False
    failure: BaseException | None = None

    def emit(name: str) -> None:
        if fault is not None:
            fault(name)

    try:
        root_cap = _enforce_gate0_for_mutable(boundary, hooks=hooks)
        root_cap.assert_still_bound(boundary)

        emit("before_snapshot_prepare")
        binding, data = bind_frozen_source(spec)
        emit("after_snapshot_prepare")
        view = parse_complete_prefix(binding.canonical_path, raw=data)

        _capture_dir, filename = snapshot_publication_paths(boundary, spec.alias)
        snapshot_name = filename.name
        capture_dir_fd = root_cap.open_subdir(
            _SNAPSHOT_CAPTURE_PARTS,
            label="snapshot capture directory",
        )

        emit("before_temp_stage")
        try:
            temp_name = _stage_regular_file_dirfd(
                capture_dir_fd, snapshot_name, view.raw_prefix
            )
        except FileNotFoundError as exc:
            raise IsolationViolation("snapshot destination unavailable") from exc
        emit("after_temp_stage")

        emit("before_source_revalidation")
        revalidate_source_identity(spec, binding)
        emit("after_source_revalidation")

        root_cap.assert_still_bound(boundary)

        emit("before_snapshot_publish")
        copied_stat = _publish_staged_rename(
            capture_dir_fd, temp_name, snapshot_name
        )
        temp_name = None
        published = True
        emit("after_snapshot_publish")

        relative = RelativePath.from_parts(*_SNAPSHOT_CAPTURE_PARTS, snapshot_name)
        return SourceDescriptor(
            alias=spec.alias,
            relative_path=str(relative),
            device=int(copied_stat.st_dev),
            inode=int(copied_stat.st_ino),
            size=int(copied_stat.st_size),
            complete_boundary=view.complete_boundary,
            prefix_sha256=view.prefix_sha256,
            sha256=hashlib.sha256(view.raw_prefix).hexdigest(),
            physical_lines=view.raw_prefix.count(b"\n"),
        )
    except BaseException as exc:
        failure = exc
    finally:
        if temp_name is not None and capture_dir_fd >= 0:
            _unlink_dirfd(capture_dir_fd, temp_name)
            temp_name = None
        if capture_dir_fd >= 0:
            os.close(capture_dir_fd)
            capture_dir_fd = -1
        if root_cap is not None:
            root_cap.close()
            root_cap = None

    if failure is not None:
        if not published:
            assert_no_snapshot_artifacts(boundary, spec.alias)
        raise failure
    raise IsolationViolation("capture_source returned without result or failure")


# ---------------------------------------------------------------------------
# Gate 0 — internal only; never accept caller authority / digests / reports
# ---------------------------------------------------------------------------


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


def _hermetic_gate0_hooks() -> Gate0ProbeHooks:
    return Gate0ProbeHooks(
        watcher_probe=lambda: {
            "status": "inactive",
            "method": "hermetic",
            "pass": "true",
        },
        network_self_test=lambda: {"pass": "true", "detail": "hermetic"},
    )


def _default_hooks_for_isolation() -> Gate0ProbeHooks | None:
    if os.environ.get(ISOLATION_MODE_ENV) == ISOLATION_MODE:
        return _hermetic_gate0_hooks()
    return None


def _validate_live_gate0_report(report: dict[str, Any]) -> Gate0Evidence:
    """Accept only a live probe report — refuse forged / failed / nested junk."""
    if not isinstance(report, dict):
        raise IsolationViolation("gate0 report must be a mapping from live probes")
    allowed_top = frozenset({"watcher", "network", "mode"})
    unknown = set(report) - allowed_top
    if unknown:
        names = ", ".join(sorted(unknown))
        raise IsolationViolation(f"gate0 report has unknown keys: {names}")
    for required in ("watcher", "network", "mode"):
        if required not in report:
            raise IsolationViolation(f"gate0 report missing {required}")
    mode_raw = report["mode"]
    _reject_coercion(mode_raw, label="gate0.mode", expected="str")
    try:
        mode = CanaryMode(mode_raw)
    except ValueError as exc:
        raise IsolationViolation("gate0.mode is not an allowed enum") from exc

    watcher = report["watcher"]
    if not isinstance(watcher, dict):
        raise IsolationViolation("gate0.watcher must be a mapping")
    watcher_allowed = frozenset({"status", "method", "pass", "detail"})
    unknown_w = set(watcher) - watcher_allowed
    if unknown_w:
        names = ", ".join(sorted(unknown_w))
        raise IsolationViolation(f"gate0.watcher contains unknown keys: {names}")
    for required in ("status", "method", "pass"):
        if required not in watcher:
            raise IsolationViolation(f"gate0.watcher missing {required}")
    try:
        status = WatcherStatus(watcher["status"])
        method = WatcherMethod(watcher["method"])
        passed = PassToken(watcher["pass"])
    except (TypeError, ValueError) as exc:
        raise IsolationViolation("gate0.watcher fields are not allowed enums") from exc
    if passed is not PassToken.TRUE:
        raise IsolationViolation("gate0 report did not pass")
    detail = None
    if "detail" in watcher:
        detail = DetailToken(value=watcher["detail"])

    network = report["network"]
    if not isinstance(network, dict):
        raise IsolationViolation("gate0.network must be a mapping")
    network_allowed = frozenset({"pass", "detail"})
    unknown_n = set(network) - network_allowed
    if unknown_n:
        names = ", ".join(sorted(unknown_n))
        raise IsolationViolation(f"gate0.network contains unknown keys: {names}")
    if "pass" not in network:
        raise IsolationViolation("gate0.network missing pass")
    try:
        net_pass = PassToken(network["pass"])
    except (TypeError, ValueError) as exc:
        raise IsolationViolation("gate0.network.pass is not an allowed enum") from exc
    if net_pass is not PassToken.TRUE:
        raise IsolationViolation("gate0 report did not pass")
    net_detail = None
    if "detail" in network:
        net_detail = DetailToken(value=network["detail"])

    return Gate0Evidence(
        mode=mode,
        watcher=Gate0WatcherEvidence(
            status=status, method=method, passed=passed, detail=detail
        ),
        network=Gate0NetworkEvidence(passed=net_pass, detail=net_detail),
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


def _enforce_gate0_for_mutable(
    boundary: IsolationBoundary,
    *,
    hooks: Gate0ProbeHooks | None = None,
) -> IsolationRootCapability:
    """Internal Gate 0: open root, run live probes, bind identities, re-check.

    Mutable commands call this themselves. Caller-supplied authority objects,
    reports, digests, or environment digests are never accepted.
    """
    if os.environ.get("CONVMEM_CLAUDE_CANARY_GATE0_DIGEST"):
        raise IsolationViolation("caller-supplied gate0 digest refused")
    if os.environ.get("CONVMEM_CLAUDE_CANARY_GATE0_REPORT"):
        raise IsolationViolation("caller-supplied gate0 report refused")

    effective = hooks if hooks is not None else _default_hooks_for_isolation()
    root_cap = open_isolation_root(boundary)
    try:
        report = gate0(hooks=effective)
        evidence = _validate_live_gate0_report(report)
        if evidence.watcher.passed is not PassToken.TRUE:
            raise IsolationViolation("gate0 report did not pass")
        root_cap.assert_still_bound(boundary)
        watcher_now = (
            (effective.watcher_probe if effective else None) or gate0_watcher_probe
        )()
        if watcher_now.get("pass") != "true":
            raise IsolationViolation("watcher active or indeterminate")
        return root_cap
    except Exception:
        root_cap.close()
        raise


def require_gate0_authority(
    boundary: IsolationBoundary,
    *,
    hooks: Gate0ProbeHooks | None = None,
) -> IsolationRootCapability:
    """Establish Gate 0 for one mutable command (returns held root capability)."""
    return _enforce_gate0_for_mutable(boundary, hooks=hooks)


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


def enable_incremental(
    boundary: IsolationBoundary,
    *,
    hooks: Gate0ProbeHooks | None = None,
    _gate0: bool = True,
) -> None:
    if _gate0:
        with _enforce_gate0_for_mutable(boundary, hooks=hooks) as root_cap:
            root_cap.assert_still_bound(boundary)
            _rewrite_config_enabled(root_cap)
        return
    path = boundary.layout["user_config"]
    text = path.read_text(encoding="utf-8")
    text = text.replace("enabled = false", "enabled = true", 1)
    path.write_text(text, encoding="utf-8")


def _rewrite_config_enabled(root_cap: IsolationRootCapability) -> None:
    """Flip incremental enabled via descriptors under the held root."""
    parent_fd = root_cap.root_fd
    owned: list[int] = []
    try:
        for part in _CONFIG_REL_PARTS[:-1]:
            child_fd = os.open(part, _dir_open_flags(), dir_fd=parent_fd)
            owned.append(child_fd)
            parent_fd = child_fd
        name = _CONFIG_REL_PARTS[-1]
        fd = os.open(name, _file_open_flags(), dir_fd=parent_fd)
        try:
            st = os.fstat(fd)
            data = os.read(fd, st.st_size)
        finally:
            os.close(fd)
        text = data.decode("utf-8").replace("enabled = false", "enabled = true", 1)
        payload = text.encode("utf-8")
        temp = _stage_regular_file_dirfd(parent_fd, name, payload)
        try:
            _publish_staged_rename(parent_fd, temp, name)
        except Exception:
            _unlink_dirfd(parent_fd, temp)
            raise
    finally:
        for handle in reversed(owned):
            os.close(handle)


def run_coordinator(
    boundary: IsolationBoundary,
    source: Path,
    *,
    chunk_size: int = 2,
    overlap: int = 0,
    hooks: Gate0ProbeHooks | None = None,
) -> dict[str, Any]:
    with _enforce_gate0_for_mutable(boundary, hooks=hooks) as root_cap:
        root_cap.assert_still_bound(boundary)
        install_fake_providers()
        _rewrite_config_enabled(root_cap)
        # Intentional config flip: rebind digest, then re-check root/marker.
        root_cap.config_digest = _config_digest_via_root(root_cap)
        root_cap.assert_still_bound(boundary)
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
    *,
    hooks: Gate0ProbeHooks | None = None,
) -> dict[str, Any]:
    """Exercise baseline, unchanged replay, and append under isolation."""
    with _enforce_gate0_for_mutable(boundary, hooks=hooks) as root_cap:
        root_cap.assert_still_bound(boundary)
        install_fake_providers()
        _rewrite_config_enabled(root_cap)
        root_cap.config_digest = _config_digest_via_root(root_cap)
        root_cap.assert_still_bound(boundary)
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
    "BoundedInt",
    "CanaryMode",
    "CaptureEvidence",
    "CoordinatorCountersEvidence",
    "CoordinatorEvidence",
    "CoordinatorMode",
    "CoordinatorOutcome",
    "DetailToken",
    "FrozenSourceSpec",
    "Gate0Evidence",
    "Gate0NetworkEvidence",
    "Gate0ProbeHooks",
    "Gate0WatcherEvidence",
    "IsolationRootCapability",
    "MatrixEvidence",
    "PRODUCTION_ROOTS",
    "PassToken",
    "RebuildOutcome",
    "RelativePath",
    "Sha256Digest",
    "SourceAlias",
    "SourceDescriptor",
    "SourceEvidence",
    "SourceIdentityBinding",
    "WatcherMethod",
    "WatcherStatus",
    "assemble_evidence",
    "assert_no_snapshot_artifacts",
    "assert_transition_coverage",
    "bind_frozen_source",
    "capture_source",
    "derive_snapshot_destination",
    "enable_incremental",
    "gate0",
    "gate0_watcher_probe",
    "_hermetic_gate0_hooks",
    "install_fake_providers",
    "list_snapshot_artifacts",
    "open_isolation_root",
    "prepare_fixture_env",
    "require_gate0_authority",
    "revalidate_source_identity",
    "run_coordinator",
    "run_hermetic_matrix",
    "run_worker",
    "scrub_credentials",
    "snapshot_publication_paths",
    "validate_frozen_source",
    "validate_source_alias",
    "worker_env",
]
