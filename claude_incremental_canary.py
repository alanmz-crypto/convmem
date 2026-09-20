"""Hermetic Claude incremental JSONL canary boundary.

Canary-only module for Arc Claude Watch Parity Gate 2. Not registered in the
normal CLI or watcher. Live-source execution requires a separate Ryan grant.

Capability-bound redesign: hold the isolation root directory descriptor after a
single validation; publish only via directory-relative atomic rename after all
fallible checks; Gate 0 is internal-only; evidence is closed typed objects.
"""

# pylint: disable=too-many-lines,duplicate-code,too-many-arguments,too-many-locals

from __future__ import annotations

import contextlib
import enum
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import tempfile
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from adapters.claude_session_jsonl import parse_complete_prefix
from incremental_jsonl import DURABLE_TRANSITIONS, IncrementalJsonlCoordinator
from incremental_jsonl_isolation import (
    ISOLATION_MODE,
    ISOLATION_MODE_ENV,
    ISOLATION_ROOT_ENV,
    ISOLATION_TOKEN_ENV,
    IsolationBoundary,
    IsolationViolation,
    known_production_roots,
    sanitized_worker_env,
)

CANARY_MODE = "claude-incremental-canary-v1"
CRASH_EXIT = 86


class _RecoverableWorkerCrash(Exception):
    """Host-side sentinel for injected CRASH_EXIT during capture."""
_SOURCE_ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_SAFE_DETAIL = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,63}$")
_REBUILD_REASON = re.compile(r"^[a-z_]+$")
_SNAPSHOT_CAPTURE_PARTS = ("sources", "claude-capture")
_MARKER_NAME = ".convmem-jsonl-production-root"
BWRAP_PATH = Path("/usr/bin/bwrap")
BWRAP_MIN_VERSION = (0, 12, 0)
CANARY_INTERNAL_ROOT = "/canary-root"
_CONTROL_SCRATCH_NAME = "scratch"
_CONTROL_VAULT_NAME = "snapshot-vault"
_MARKER_ACTIVE = ".active"
_MARKER_QUARANTINED = ".quarantined"
_CONTROL_PARENT_ENV = "CONVMEM_CLAUDE_GATE2_CONTROL_PARENT"
_GRANTED_PROJECTS = ("home", ".claude", "projects", "granted")
_NAMESPACE_APP_ROOT = "/app"
_MINIFORGE_PREFIX = Path("/home/lauer/miniforge3")
_VENV_SITE = Path(
    "/home/lauer/Projects/convmem/.venv/lib/python3.13/site-packages"
)
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


class PublicationDurability(enum.StrEnum):
    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"


@dataclass(frozen=True)
class PublicationResult:
    """Final publication outcome; directory fsync failure is not rolled back."""

    stat: os.stat_result
    durability: PublicationDurability


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
    raise IsolationViolation(f"{label} must be a closed coordinator outcome")


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
    durability: PublicationDurability

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
            "durability": str(self.durability),
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
    durability: PublicationDurability


@dataclass(frozen=True)
class WatcherProbeResult:
    status: WatcherStatus
    method: WatcherMethod
    passed: PassToken
    detail: DetailToken | None = None


@dataclass(frozen=True)
class NetworkProbeResult:
    passed: PassToken
    detail: DetailToken | None = None


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
# Publication — O_TMPFILE probe, held anonymous inode, capability linkat
# ---------------------------------------------------------------------------

_O_TMPFILE = getattr(os, "O_TMPFILE", 0o20000000)


def _tmpfile_open_flags() -> int:
    return _O_TMPFILE | os.O_WRONLY | os.O_CLOEXEC


def _probe_tmpfile_available(parent_fd: int) -> bool:
    """Probe O_TMPFILE under parent_fd; close probe fd so no artifact remains."""
    if not _O_TMPFILE:
        return False
    probe_fd = -1
    try:
        probe_fd = os.open(".", _tmpfile_open_flags(), 0o600, dir_fd=parent_fd)
        return True
    except OSError:
        return False
    finally:
        if probe_fd >= 0:
            os.close(probe_fd)


def _write_fd_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise OSError("snapshot short write")
        offset += written
    os.fsync(fd)


def _stage_anonymous_dirfd(parent_fd: int, payload: bytes) -> int:
    """Stage payload in a held anonymous inode; caller must link or close."""
    if not _probe_tmpfile_available(parent_fd):
        raise IsolationViolation("O_TMPFILE unavailable for snapshot publication")
    fd = os.open(".", _tmpfile_open_flags(), 0o600, dir_fd=parent_fd)
    try:
        _write_fd_all(fd, payload)
        return fd
    except Exception:
        os.close(fd)
        raise


def _linkat_anonymous(parent_fd: int, anon_fd: int, final_name: str) -> None:
    """Publish held anonymous inode via directory-relative linkat."""
    link_src = f"/proc/self/fd/{anon_fd}"
    os.link(link_src, final_name, dst_dir_fd=parent_fd)


def _publish_anonymous_dirfd(
    parent_fd: int,
    anon_fd: int,
    final_name: str,
) -> PublicationResult:
    """Final publication transition; fsync failure yields durability=unconfirmed."""
    try:
        existing = os.stat(final_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        existing = None
    if existing is not None:
        if stat.S_ISLNK(existing.st_mode):
            raise IsolationViolation("snapshot destination is symlinked")
        if not stat.S_ISREG(existing.st_mode):
            raise IsolationViolation("snapshot destination is not a regular file")
        os.unlink(final_name, dir_fd=parent_fd)
    try:
        _linkat_anonymous(parent_fd, anon_fd, final_name)
    finally:
        os.close(anon_fd)
    stat_result = os.stat(final_name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISREG(stat_result.st_mode):
        raise IsolationViolation("published snapshot is not a regular file")
    try:
        os.fsync(parent_fd)
        durability = PublicationDurability.CONFIRMED
    except OSError:
        durability = PublicationDurability.UNCONFIRMED
    return PublicationResult(stat=stat_result, durability=durability)


def _granted_source_parts(alias: str) -> tuple[str, ...]:
    validate_source_alias(alias)
    return (*_GRANTED_PROJECTS, f"{alias}.jsonl")


def _granted_source_relative(alias: str) -> str:
    return "/".join(_granted_source_parts(alias))


def _discover_control_root(scratch_root: Path) -> Path:
    control = scratch_root.parent.resolve()
    scratch_name = _CONTROL_SCRATCH_NAME
    vault_name = _CONTROL_VAULT_NAME
    if not (control / scratch_name).exists():
        raise IsolationViolation("control root layout missing scratch")
    if not (control / vault_name).exists():
        raise IsolationViolation("control root layout missing snapshot-vault")
    try:
        if not (control / scratch_name).resolve().samefile(scratch_root):
            raise IsolationViolation("scratch not bound to control root")
    except OSError as exc:
        raise IsolationViolation("scratch control binding unavailable") from exc
    return control


def snapshot_publication_paths(
    boundary: IsolationBoundary, alias: str
) -> tuple[Path, Path]:
    """Return granted placeholder directory and filename inside the scratch root."""
    validate_source_alias(alias)
    capture_dir = boundary.resolve_mutable(
        Path(*_GRANTED_PROJECTS),
        label="granted source directory",
    )
    return capture_dir, Path(f"{alias}.jsonl")


def list_snapshot_artifacts(boundary: IsolationBoundary, alias: str) -> list[str]:
    """List vault snapshot artifacts for the current control root, if any."""
    control = _discover_control_root(boundary.root)
    vault = control / _CONTROL_VAULT_NAME
    if not vault.is_dir():
        return []
    return sorted(str(entry.resolve()) for entry in vault.iterdir() if entry.is_file())


def assert_no_snapshot_artifacts(boundary: IsolationBoundary, alias: str) -> None:
    """Fail closed when vault snapshot publication left residue behind."""
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
    """Derive the granted placeholder path inside the scratch root."""
    validate_source_alias(alias)
    relative = Path(*_granted_source_parts(alias))
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


def _generate_capture_id() -> str:
    return secrets.token_hex(16)


def _open_vault_dirfd(control_path: Path) -> int:
    control_fd = os.open(str(control_path), _dir_open_flags())
    try:
        try:
            return os.open(_CONTROL_VAULT_NAME, _dir_open_flags(), dir_fd=control_fd)
        except OSError as exc:
            raise IsolationViolation("snapshot vault unavailable") from exc
    finally:
        os.close(control_fd)


def capture_source(
    boundary: IsolationBoundary,
    spec: FrozenSourceSpec,
    *,
    fault: Callable[[str], None] | None = None,
) -> SourceDescriptor:
    """Publish the complete prefix into the unbound vault; worker sees granted path."""
    root_cap: IsolationRootCapability | None = None
    vault_fd = -1
    anon_fd = -1
    snapshot_name = ""
    published = False
    failure: BaseException | None = None

    def emit(name: str) -> None:
        if fault is not None:
            fault(name)

    try:
        root_cap = _enforce_gate0_for_mutable(boundary)
        root_cap.assert_still_bound(boundary)
        control_path = _discover_control_root(boundary.root)
        vault_fd = _open_vault_dirfd(control_path)

        emit("before_snapshot_prepare")
        binding, data = bind_frozen_source(spec)
        emit("after_snapshot_prepare")
        view = parse_complete_prefix(binding.canonical_path, raw=data)

        snapshot_name = f"{_generate_capture_id()}.jsonl"

        emit("before_temp_stage")
        try:
            anon_fd = _stage_anonymous_dirfd(vault_fd, view.raw_prefix)
        except FileNotFoundError as exc:
            raise IsolationViolation("snapshot destination unavailable") from exc
        emit("after_temp_stage")

        emit("before_source_revalidation")
        revalidate_source_identity(spec, binding)
        emit("after_source_revalidation")

        root_cap.assert_still_bound(boundary)

        emit("before_snapshot_publish")
        publish_fd = anon_fd
        anon_fd = -1
        publication = _publish_anonymous_dirfd(vault_fd, publish_fd, snapshot_name)
        published = True
        emit("after_snapshot_publish")

        relative = RelativePath.from_parts(*_granted_source_parts(spec.alias))
        copied_stat = publication.stat
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
            durability=publication.durability,
        )
    except BaseException as exc:
        failure = exc
    finally:
        if anon_fd >= 0:
            os.close(anon_fd)
            anon_fd = -1
        if vault_fd >= 0:
            os.close(vault_fd)
            vault_fd = -1
        if root_cap is not None:
            root_cap.close()
            root_cap = None

    if failure is not None:
        if not published:
            assert_no_snapshot_artifacts(boundary, spec.alias)
        raise failure
    raise IsolationViolation("capture_source returned without result or failure")


# ---------------------------------------------------------------------------
# Gate 0 — internal only; private probes; no caller authority surfaces
# ---------------------------------------------------------------------------


def _probe_watcher_status() -> WatcherProbeResult:
    """Private watcher probe; hermetic isolation mode skips production systemctl."""
    if os.environ.get(ISOLATION_MODE_ENV) == ISOLATION_MODE:
        return WatcherProbeResult(
            status=WatcherStatus.INACTIVE,
            method=WatcherMethod.HERMETIC,
            passed=PassToken.TRUE,
        )
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
            return WatcherProbeResult(
                status=WatcherStatus.INACTIVE,
                method=WatcherMethod.SYSTEMCTL,
                passed=PassToken.TRUE,
            )
        if stdout in {"failed", "activating", "active"}:
            return WatcherProbeResult(
                status=WatcherStatus(stdout),
                method=WatcherMethod.SYSTEMCTL,
                passed=PassToken.FALSE,
            )
        detail = DetailToken(value=completed.stderr.strip() or "unknown")
        return WatcherProbeResult(
            status=WatcherStatus(stdout or WatcherStatus.UNKNOWN),
            method=WatcherMethod.SYSTEMCTL,
            passed=PassToken.FALSE,
            detail=detail,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return WatcherProbeResult(
            status=WatcherStatus.UNAVAILABLE,
            method=WatcherMethod.SYSTEMCTL,
            passed=PassToken.FALSE,
            detail=DetailToken(value=type(exc).__name__),
        )


def _probe_network_isolation() -> NetworkProbeResult:
    """Private network probe; hermetic isolation mode skips outbound socket."""
    if os.environ.get(ISOLATION_MODE_ENV) == ISOLATION_MODE:
        return NetworkProbeResult(
            passed=PassToken.TRUE,
            detail=DetailToken(value="hermetic"),
        )
    import socket

    try:
        socket.create_connection(("203.0.113.1", 9), timeout=0.01)
        return NetworkProbeResult(
            passed=PassToken.FALSE,
            detail=DetailToken(value="unexpected-success"),
        )
    except OSError as exc:
        return NetworkProbeResult(
            passed=PassToken.TRUE,
            detail=DetailToken(value=type(exc).__name__),
        )


@contextlib.contextmanager
def _scrub_host_credentials():
    removed: dict[str, str] = {}
    for name in list(os.environ):
        if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
            if name not in {"CONVMEM_INCREMENTAL_TOKEN"}:
                removed[name] = os.environ.pop(name)
    try:
        yield
    finally:
        os.environ.update(removed)


def _refuse_inherited_gate0_authority() -> None:
    if os.environ.get("CONVMEM_CLAUDE_CANARY_GATE0_DIGEST"):
        raise IsolationViolation("caller-supplied gate0 digest refused")
    if os.environ.get("CONVMEM_CLAUDE_CANARY_GATE0_REPORT"):
        raise IsolationViolation("caller-supplied gate0 report refused")
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


def _build_gate0_evidence() -> Gate0Evidence:
    """Run private probes and return closed Gate0Evidence only."""
    _refuse_inherited_gate0_authority()
    watcher = _probe_watcher_status()
    if watcher.passed is not PassToken.TRUE:
        raise IsolationViolation("watcher active or indeterminate")
    network = _probe_network_isolation()
    if network.passed is not PassToken.TRUE:
        raise IsolationViolation("network self-test failed")
    return Gate0Evidence(
        mode=CanaryMode.V1,
        watcher=Gate0WatcherEvidence(
            status=watcher.status,
            method=watcher.method,
            passed=watcher.passed,
            detail=watcher.detail,
        ),
        network=Gate0NetworkEvidence(
            passed=network.passed,
            detail=network.detail,
        ),
    )


def _enforce_gate0_for_mutable(
    boundary: IsolationBoundary,
) -> IsolationRootCapability:
    """Internal Gate 0: open root, run private probes, bind identities, re-check."""
    _refuse_inherited_gate0_authority()
    root_cap = open_isolation_root(boundary)
    try:
        _build_gate0_evidence()
        root_cap.assert_still_bound(boundary)
        watcher_now = _probe_watcher_status()
        if watcher_now.passed is not PassToken.TRUE:
            raise IsolationViolation("watcher active or indeterminate")
        return root_cap
    except Exception:
        root_cap.close()
        raise


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


def _trusted_control_parent(parent: Path | None = None) -> Path:
    if parent is not None:
        return parent
    raw = os.environ.get(_CONTROL_PARENT_ENV, "")
    if raw:
        path = Path(raw).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path
    return Path(tempfile.gettempdir()) / "convmem-claude-gate2-control-parent"


def _assert_dir_identity(fd: int, *, label: str) -> os.stat_result:
    st = os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode):
        raise IsolationViolation(f"{label} is not a directory")
    if stat.S_ISLNK(st.st_mode):
        raise IsolationViolation(f"{label} is symlinked")
    if st.st_uid != os.geteuid():
        raise IsolationViolation(f"{label} uid mismatch")
    mode = stat.S_IMODE(st.st_mode)
    if mode != 0o700:
        raise IsolationViolation(f"{label} mode is not 0700")
    return st


@dataclass
class ControlRootSession:
    """Held control-root descriptors for scratch and snapshot vault."""

    root_id: str
    control_path: Path
    control_fd: int
    scratch_fd: int
    vault_fd: int
    scratch_path: Path
    scratch_dev: int
    _closed: bool = field(default=False, repr=False)

    def close(self) -> None:
        if self._closed:
            return
        for fd in (self.vault_fd, self.scratch_fd, self.control_fd):
            if fd >= 0:
                os.close(fd)
        self._closed = True

    def __enter__(self) -> ControlRootSession:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def _mkdirat_open(parent_fd: int, name: str, *, label: str) -> int:
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
    except FileExistsError:
        pass
    fd = os.open(name, _dir_open_flags(), dir_fd=parent_fd)
    _assert_dir_identity(fd, label=label)
    return fd


def create_control_root(parent: Path | None = None) -> ControlRootSession:
    """Create a mode-0700 control root with sibling scratch and vault."""
    parent_path = _trusted_control_parent(parent)
    parent_path.mkdir(parents=True, exist_ok=True)
    parent_fd = os.open(str(parent_path), _dir_open_flags())
    root_id = secrets.token_hex(12)
    try:
        os.mkdir(root_id, 0o700, dir_fd=parent_fd)
        control_fd = os.open(root_id, _dir_open_flags(), dir_fd=parent_fd)
        control_st = _assert_dir_identity(control_fd, label="control root")
        scratch_fd = _mkdirat_open(control_fd, _CONTROL_SCRATCH_NAME, label="scratch")
        vault_fd = _mkdirat_open(control_fd, _CONTROL_VAULT_NAME, label="snapshot-vault")
        scratch_st = os.fstat(scratch_fd)
        vault_st = os.fstat(vault_fd)
        if scratch_st.st_dev != vault_st.st_dev or control_st.st_dev != scratch_st.st_dev:
            raise IsolationViolation("control root crosses filesystems")
        control_path = (parent_path / root_id).resolve()
        scratch_path = (control_path / _CONTROL_SCRATCH_NAME).resolve()
        return ControlRootSession(
            root_id=root_id,
            control_path=control_path,
            control_fd=control_fd,
            scratch_fd=scratch_fd,
            vault_fd=vault_fd,
            scratch_path=scratch_path,
            scratch_dev=int(scratch_st.st_dev),
        )
    finally:
        os.close(parent_fd)


def _reopen_control_root(parent: Path, root_id: str) -> ControlRootSession:
    if not root_id or "/" in root_id or root_id in {".", ".."}:
        raise IsolationViolation("invalid control root id")
    parent_fd = os.open(str(parent), _dir_open_flags())
    try:
        control_fd = os.open(root_id, _dir_open_flags(), dir_fd=parent_fd)
        _assert_dir_identity(control_fd, label="control root")
        scratch_fd = os.open(
            _CONTROL_SCRATCH_NAME, _dir_open_flags(), dir_fd=control_fd
        )
        vault_fd = os.open(
            _CONTROL_VAULT_NAME, _dir_open_flags(), dir_fd=control_fd
        )
        control_st = os.fstat(control_fd)
        scratch_st = _assert_dir_identity(scratch_fd, label="scratch")
        vault_st = _assert_dir_identity(vault_fd, label="snapshot-vault")
        if scratch_st.st_dev != vault_st.st_dev or control_st.st_dev != scratch_st.st_dev:
            raise IsolationViolation("control root crosses filesystems")
        control_path = (parent / root_id).resolve()
        return ControlRootSession(
            root_id=root_id,
            control_path=control_path,
            control_fd=control_fd,
            scratch_fd=scratch_fd,
            vault_fd=vault_fd,
            scratch_path=(control_path / _CONTROL_SCRATCH_NAME).resolve(),
            scratch_dev=int(scratch_st.st_dev),
        )
    finally:
        os.close(parent_fd)


def prepare_fixture_env(
    parent: Path,
    *,
    count: int = 4,
    alias: str = "canary-fixture",
) -> tuple[Path, str, dict[str, str], Path, FrozenSourceSpec]:
    """Create control root, scratch root, env, Claude fixture, and frozen spec."""
    parent_home = Path.home()
    control = create_control_root(parent)
    root = control.scratch_path
    token = os.urandom(24).hex()
    (root / _MARKER_NAME).write_text(token, encoding="ascii")
    from incremental_jsonl_isolation import write_hermetic_config

    write_hermetic_config(root)
    granted_dir = root.joinpath(*_GRANTED_PROJECTS)
    granted_dir.mkdir(parents=True, exist_ok=True)
    placeholder = granted_dir / f"{alias}.jsonl"
    placeholder.touch()
    os.chmod(placeholder, 0o600)
    control.close()
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
    with _enforce_gate0_for_mutable(boundary) as root_cap:
        root_cap.assert_still_bound(boundary)
        _rewrite_config_enabled(root_cap)


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
        text = data.decode("utf-8")
        if "enabled = true" in text:
            return
        text = text.replace("enabled = false", "enabled = true", 1)
        payload = text.encode("utf-8")
        anon_fd = _stage_anonymous_dirfd(parent_fd, payload)
        _publish_anonymous_dirfd(parent_fd, anon_fd, name)
    finally:
        for handle in reversed(owned):
            os.close(handle)


def run_coordinator(
    boundary: IsolationBoundary,
    source: Path,
    *,
    chunk_size: int = 2,
    overlap: int = 0,
) -> dict[str, Any]:
    with _enforce_gate0_for_mutable(boundary) as root_cap:
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
) -> dict[str, Any]:
    """Exercise baseline, unchanged replay, and append under isolation."""
    with _enforce_gate0_for_mutable(boundary) as root_cap:
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


def _parse_bwrap_version(text: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        raise IsolationViolation("bubblewrap version unavailable")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def validate_bwrap_binary() -> None:
    """Validate bubblewrap binary path, version, and ownership."""
    path = BWRAP_PATH
    if not path.is_file():
        raise IsolationViolation("bubblewrap binary missing")
    if path.is_symlink():
        raise IsolationViolation("bubblewrap binary is symlinked")
    st = path.stat()
    if st.st_uid == 0 and (st.st_mode & stat.S_ISUID):
        raise IsolationViolation("bubblewrap binary is setuid")
    completed = subprocess.run(
        [str(path), "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5.0,
    )
    version = _parse_bwrap_version((completed.stdout or completed.stderr or "").strip())
    if version < BWRAP_MIN_VERSION:
        raise IsolationViolation("bubblewrap version below minimum")


def _probe_bwrap_namespace() -> None:
    """Run a disposable descriptor-bind probe in a real namespace."""
    validate_bwrap_binary()
    scratch = tempfile.mkdtemp(prefix="convmem-bwrap-probe-")
    scratch_fd = os.open(scratch, _dir_open_flags())
    try:
        cmd = _base_bwrap_command(scratch_fd=scratch_fd, snapshot_fd=None, config_fd=None)
        cmd.extend(["--", "/bin/true"])
        completed = subprocess.run(
            cmd,
            pass_fds=[scratch_fd],
            close_fds=True,
            check=False,
            timeout=10.0,
        )
        if completed.returncode != 0:
            raise IsolationViolation("bubblewrap namespace probe failed")
    finally:
        os.close(scratch_fd)


def _configured_watch_roots() -> list[Path]:
    """Return configured watch roots; hermetic callers use empty/synthetic lists."""
    if os.environ.get(ISOLATION_MODE_ENV) == ISOLATION_MODE:
        return []
    try:
        from watch import watch_roots as _watch_roots

        config_path = Path.home() / ".config" / "convmem" / "config.toml"
        if not config_path.is_file():
            return []
        import tomllib

        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
        watch_cfg = payload.get("watch") or {}
        sources_cfg = payload.get("sources") or {}
        paths = watch_cfg.get("paths") or sources_cfg.get("paths") or []
        return _watch_roots([str(item) for item in paths if isinstance(item, str)])
    except Exception:
        return []


def _paths_disjoint(left: Path, right: Path) -> bool:
    try:
        left.resolve().relative_to(right.resolve())
        return False
    except ValueError:
        pass
    try:
        right.resolve().relative_to(left.resolve())
        return False
    except ValueError:
        return True


def assert_watch_roots_disjoint(
    control: Path,
    scratch: Path,
    vault: Path,
    *,
    watch_roots_list: Sequence[Path] | None = None,
) -> None:
    """Fail closed unless canary roots and watch roots are disjoint both ways."""
    canary_roots = (control.resolve(), scratch.resolve(), vault.resolve())
    roots = list(watch_roots_list or _configured_watch_roots())
    for watch_root in roots:
        watch = watch_root.expanduser().resolve(strict=False)
        for canary in canary_roots:
            if not _paths_disjoint(canary, watch):
                raise IsolationViolation("watch root overlaps canary root")


def _marker_present(control_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=control_fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _acquire_control_lock(control_fd: int) -> None:
    try:
        fcntl.flock(control_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise IsolationViolation("control root lock contention") from exc


def _release_control_lock(control_fd: int) -> None:
    try:
        fcntl.flock(control_fd, fcntl.LOCK_UN)
    except OSError:
        pass


def _fsync_dir(fd: int) -> None:
    os.fsync(fd)


def _create_active_marker(control_fd: int) -> None:
    fd = os.open(_MARKER_ACTIVE, _file_open_flags(write=True, create=True), dir_fd=control_fd)
    try:
        os.write(fd, b"1")
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_dir(control_fd)


def _remove_active_marker(control_fd: int) -> None:
    try:
        os.unlink(_MARKER_ACTIVE, dir_fd=control_fd)
    except FileNotFoundError:
        pass
    _fsync_dir(control_fd)


def _quarantine_control_root(control_fd: int) -> None:
    if _marker_present(control_fd, _MARKER_ACTIVE):
        os.rename(_MARKER_ACTIVE, _MARKER_QUARANTINED, src_dir_fd=control_fd, dst_dir_fd=control_fd)
    elif not _marker_present(control_fd, _MARKER_QUARANTINED):
        fd = os.open(
            _MARKER_QUARANTINED,
            _file_open_flags(write=True, create=True),
            dir_fd=control_fd,
        )
        os.close(fd)
    _fsync_dir(control_fd)


def _assert_marker_terminal_state(control_fd: int) -> None:
    active = _marker_present(control_fd, _MARKER_ACTIVE)
    quarantined = _marker_present(control_fd, _MARKER_QUARANTINED)
    if active and quarantined:
        raise IsolationViolation("control markers both present")
    if not active and not quarantined:
        raise IsolationViolation("control markers neither present")


def _namespace_config_bytes() -> bytes:
    root = CANARY_INTERNAL_ROOT
    payload = (
        "[index]\n"
        f'chroma_dir = "{root}/home/.local/share/convmem/chroma"\n'
        f'processed_log = "{root}/home/.local/share/convmem/processed.json"\n'
        f'units_export = "{root}/home/.local/share/convmem/knowledge_units.jsonl"\n'
        "chunk_size = 2\n"
        "chunk_overlap = 0\n"
        "\n"
        "[index.incremental_jsonl]\n"
        "enabled = true\n"
        f'state_dir = "{root}/home/.local/share/convmem/incremental-jsonl"\n'
        "allow_full_rebuild = false\n"
        "\n"
        "[models]\n"
        'embed_model = "deterministic-fake"\n'
        'summarize_model = "deterministic-fake"\n'
        'distill_model = "deterministic-fake"\n'
        'ollama_host = ""\n'
        "\n"
        "[distill]\n"
        "min_confidence = 0.6\n"
    )
    return payload.encode("utf-8")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _python_executable() -> str:
    return str(_MINIFORGE_PREFIX / "bin" / "python3")


def _base_bwrap_command(
    *,
    scratch_fd: int,
    snapshot_fd: int | None,
    config_fd: int | None,
    alias: str | None = None,
) -> list[str]:
    repo = _repo_root()
    cmd = [
        str(BWRAP_PATH),
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--unshare-all",
        "--unshare-user",
        "--disable-userns",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "--setenv",
        "HOME",
        f"{CANARY_INTERNAL_ROOT}/home",
        "--setenv",
        "PYTHONPATH",
        f"{_NAMESPACE_APP_ROOT}:{_VENV_SITE}",
        "--setenv",
        "PYTHONIOENCODING",
        "utf-8",
        "--setenv",
        "PYTHONDONTWRITEBYTECODE",
        "1",
        "--setenv",
        "LC_ALL",
        "C.UTF-8",
        "--setenv",
        ISOLATION_MODE_ENV,
        ISOLATION_MODE,
        "--setenv",
        "CONVMEM_CLAUDE_CANARY_MODE",
        CANARY_MODE,
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/bin",
        "/bin",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/lib64",
        "/lib64",
        "--ro-bind",
        str(_MINIFORGE_PREFIX),
        str(_MINIFORGE_PREFIX),
        "--ro-bind",
        str(repo),
        _NAMESPACE_APP_ROOT,
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        "/run",
        f"--bind-fd",
        str(scratch_fd),
        CANARY_INTERNAL_ROOT,
    ]
    if snapshot_fd is not None and alias is not None:
        granted = f"{CANARY_INTERNAL_ROOT}/{_granted_source_relative(alias)}"
        cmd.extend(["--ro-bind-fd", str(snapshot_fd), granted])
    if config_fd is not None:
        config_path = f"{CANARY_INTERNAL_ROOT}/home/.config/convmem/config.toml"
        cmd.extend(["--ro-bind-data", str(config_fd), config_path])
    return cmd


def _host_capture_to_vault(
    vault_fd: int,
    spec: FrozenSourceSpec,
    *,
    fault: Callable[[str], None] | None = None,
) -> tuple[str, SourceIdentityBinding, bytes, str]:
    def emit(name: str) -> None:
        if fault is not None:
            fault(name)

    emit("before_snapshot_prepare")
    binding, data = bind_frozen_source(spec)
    emit("after_snapshot_prepare")
    view = parse_complete_prefix(binding.canonical_path, raw=data)
    capture_id = _generate_capture_id()
    snapshot_name = f"{capture_id}.jsonl"
    emit("before_temp_stage")
    anon_fd = _stage_anonymous_dirfd(vault_fd, view.raw_prefix)
    emit("after_temp_stage")
    emit("before_source_revalidation")
    revalidate_source_identity(spec, binding)
    emit("after_source_revalidation")
    emit("before_snapshot_publish")
    publication = _publish_anonymous_dirfd(vault_fd, anon_fd, snapshot_name)
    emit("after_snapshot_publish")
    digest = hashlib.sha256(view.raw_prefix).hexdigest()
    if publication.stat.st_size != binding.size:
        raise IsolationViolation("vault snapshot size mismatch")
    return capture_id, binding, data, digest


def _open_vault_snapshot(vault_fd: int, capture_id: str) -> int:
    name = f"{capture_id}.jsonl"
    fd = os.open(name, _file_open_flags(), dir_fd=vault_fd)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode):
        os.close(fd)
        raise IsolationViolation("vault snapshot is not regular")
    return fd


def _revalidate_vault_snapshot(
    vault_fd: int,
    capture_id: str,
    *,
    expected_stat: os.stat_result,
    expected_digest: str,
) -> None:
    name = f"{capture_id}.jsonl"
    fd = os.open(name, _file_open_flags(), dir_fd=vault_fd)
    try:
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino, st.st_size) != (
            expected_stat.st_dev,
            expected_stat.st_ino,
            expected_stat.st_size,
        ):
            raise IsolationViolation("vault snapshot identity changed")
        data = os.read(fd, st.st_size)
    finally:
        os.close(fd)
    if hashlib.sha256(data).hexdigest() != expected_digest:
        raise IsolationViolation("vault snapshot digest changed")


def _cleanup_vault_snapshot(vault_fd: int, capture_id: str) -> None:
    os.unlink(f"{capture_id}.jsonl", dir_fd=vault_fd)
    _fsync_dir(vault_fd)


def _scrub_sensitive_output(text: str, *, control_prefix: str, capture_id: str) -> str:
    cleaned = text.replace(control_prefix, "<redacted-control>")
    cleaned = cleaned.replace(capture_id, "<redacted-capture>")
    return cleaned


def _namespace_worker_path(command: str, source: Path | None) -> list[str]:
    worker = _NAMESPACE_APP_ROOT + "/tests/claude_incremental_canary_worker.py"
    args = [_python_executable(), "-I", worker, command]
    if source is not None:
        args.append(str(source))
    return args


def _run_namespace_once(
    command: str,
    *,
    root: Path,
    token: str,
    source: Path | None,
    spec: FrozenSourceSpec | None,
    extra_env: dict[str, str] | None,
    diagnostic: bool = False,
) -> subprocess.CompletedProcess[str]:
    validate_bwrap_binary()
    control_path = _discover_control_root(root)
    control = _reopen_control_root(control_path.parent, control_path.name)
    capture_id = ""
    capture_stat: os.stat_result | None = None
    capture_digest = ""
    snapshot_fd = -1
    config_fd = -1
    config_bytes = _namespace_config_bytes()
    if hasattr(os, "memfd_create"):
        config_fd = os.memfd_create("convmem-canary-config")
        os.write(config_fd, config_bytes)
        os.lseek(config_fd, 0, os.SEEK_SET)
    else:
        reader, writer = os.pipe()
        os.write(writer, config_bytes)
        os.close(writer)
        config_fd = reader

    try:
        _acquire_control_lock(control.control_fd)
        if _marker_present(control.control_fd, _MARKER_QUARANTINED):
            raise IsolationViolation("control root quarantined")
        if _marker_present(control.control_fd, _MARKER_ACTIVE):
            _quarantine_control_root(control.control_fd)
            raise IsolationViolation("control root stale active marker")
        assert_watch_roots_disjoint(
            control.control_path,
            control.scratch_path,
            control.control_path / _CONTROL_VAULT_NAME,
        )
        with _scrub_host_credentials():
            _build_gate0_evidence()
        _create_active_marker(control.control_fd)

        alias = spec.alias if spec is not None else ""
        if spec is not None:
            fault_name = (extra_env or {}).get("CONVMEM_CLAUDE_CANARY_FAULT", "")

            def host_fault(name: str) -> None:
                if fault_name and name == fault_name:
                    raise _RecoverableWorkerCrash()

            try:
                capture_id, _binding, _data, capture_digest = _host_capture_to_vault(
                    control.vault_fd,
                    spec,
                    fault=host_fault if command == "capture" else None,
                )
            except _RecoverableWorkerCrash:
                return subprocess.CompletedProcess(
                    args=[],
                    returncode=CRASH_EXIT,
                    stdout="",
                    stderr="",
                )
            snapshot_fd = _open_vault_snapshot(control.vault_fd, capture_id)
            capture_stat = os.fstat(snapshot_fd)

        env = worker_env(root, token, extra=extra_env)
        env[ISOLATION_ROOT_ENV] = CANARY_INTERNAL_ROOT
        env["HOME"] = f"{CANARY_INTERNAL_ROOT}/home"
        env["XDG_CONFIG_HOME"] = f"{CANARY_INTERNAL_ROOT}/xdg-config"
        env["XDG_DATA_HOME"] = f"{CANARY_INTERNAL_ROOT}/xdg-data"
        env["XDG_CACHE_HOME"] = f"{CANARY_INTERNAL_ROOT}/xdg-cache"
        env["PYTHONPATH"] = f"{_NAMESPACE_APP_ROOT}:{_VENV_SITE}"
        if diagnostic:
            env["CONVMEM_CLAUDE_CANARY_DIAGNOSTIC"] = "1"

        bwrap_cmd = _base_bwrap_command(
            scratch_fd=control.scratch_fd,
            snapshot_fd=snapshot_fd if snapshot_fd >= 0 else None,
            config_fd=config_fd,
            alias=alias or None,
        )
        worker_source: Path | None = source
        if spec is not None:
            worker_source = Path(*_granted_source_parts(spec.alias))
        for key, value in env.items():
            if key == "PATH":
                continue
            bwrap_cmd.extend(["--setenv", key, value])
        bwrap_cmd.extend(
            [
                "--setenv",
                ISOLATION_ROOT_ENV,
                CANARY_INTERNAL_ROOT,
                "--setenv",
                ISOLATION_TOKEN_ENV,
                token,
            ]
        )
        worker_args = _namespace_worker_path(command, worker_source)
        bwrap_cmd.extend(["--chdir", _NAMESPACE_APP_ROOT, "--"])
        bwrap_cmd.extend(worker_args)

        pass_fds = [control.scratch_fd, config_fd]
        if snapshot_fd >= 0:
            pass_fds.append(snapshot_fd)
        completed = subprocess.run(
            bwrap_cmd,
            pass_fds=pass_fds,
            close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            start_new_session=True,
        )
        stdout = _scrub_sensitive_output(
            completed.stdout or "",
            control_prefix=str(control.control_path),
            capture_id=capture_id,
        )
        stderr = _scrub_sensitive_output(
            completed.stderr or "",
            control_prefix=str(control.control_path),
            capture_id=capture_id,
        )
        completed = subprocess.CompletedProcess(
            args=completed.args,
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
        )

        if completed.returncode == 0 and capture_id and capture_stat is not None:
            _revalidate_vault_snapshot(
                control.vault_fd,
                capture_id,
                expected_stat=capture_stat,
                expected_digest=capture_digest,
            )
            _cleanup_vault_snapshot(control.vault_fd, capture_id)
            with _scrub_host_credentials():
                _build_gate0_evidence()
            assert_watch_roots_disjoint(
                control.control_path,
                control.scratch_path,
                control.control_path / _CONTROL_VAULT_NAME,
            )
            _remove_active_marker(control.control_fd)
        else:
            if capture_id and capture_stat is not None:
                try:
                    _revalidate_vault_snapshot(
                        control.vault_fd,
                        capture_id,
                        expected_stat=capture_stat,
                        expected_digest=capture_digest,
                    )
                    _cleanup_vault_snapshot(control.vault_fd, capture_id)
                except IsolationViolation:
                    pass
            _quarantine_control_root(control.control_fd)
        return completed
    finally:
        if snapshot_fd >= 0:
            os.close(snapshot_fd)
        if config_fd >= 0:
            os.close(config_fd)
        _release_control_lock(control.control_fd)
        control.close()


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
    """Launch the canary worker inside a bubblewrap namespace."""
    spec: FrozenSourceSpec | None = None
    if source is not None:
        data = source.read_bytes()
        spec = FrozenSourceSpec(
            alias=source.stem,
            path=source,
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
        )
    try:
        completed = _run_namespace_once(
            command,
            root=root,
            token=token,
            source=source,
            spec=spec,
            extra_env=extra_env,
        )
    except IsolationViolation as exc:
        return subprocess.CompletedProcess(
            args=[],
            returncode=74,
            stdout=json.dumps({"error": "IsolationViolation", "detail": str(exc)}),
            stderr="",
        )
    if completed.returncode == CRASH_EXIT:
        return completed
    if completed.returncode not in {0, 74, CRASH_EXIT}:
        try:
            diagnostic = _run_namespace_once(
                command,
                root=root,
                token=token,
                source=source,
                spec=spec,
                extra_env=extra_env,
                diagnostic=True,
            )
        except IsolationViolation as exc:
            diagnostic = subprocess.CompletedProcess(
                args=[],
                returncode=74,
                stdout=json.dumps({"error": "IsolationViolation", "detail": str(exc)}),
                stderr="",
            )
        combined_stdout = (completed.stdout or "") + (diagnostic.stdout or "")
        combined_stderr = (completed.stderr or "") + (diagnostic.stderr or "")
        return subprocess.CompletedProcess(
            args=completed.args,
            returncode=completed.returncode,
            stdout=combined_stdout,
            stderr=combined_stderr,
        )
    return completed


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
    "Gate0WatcherEvidence",
    "PublicationDurability",
    "PublicationResult",
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
    "install_fake_providers",
    "list_snapshot_artifacts",
    "open_isolation_root",
    "prepare_fixture_env",
    "_build_gate0_evidence",
    "_probe_network_isolation",
    "_probe_tmpfile_available",
    "_probe_watcher_status",
    "revalidate_source_identity",
    "run_coordinator",
    "run_hermetic_matrix",
    "run_worker",
    "scrub_credentials",
    "assert_watch_roots_disjoint",
    "create_control_root",
    "validate_bwrap_binary",
    "snapshot_publication_paths",
    "validate_frozen_source",
    "validate_source_alias",
    "worker_env",
]
