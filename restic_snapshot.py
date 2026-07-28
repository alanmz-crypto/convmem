"""Authoritative Restic boundary for complete-data backup correction v2.

Owns BackupContext construction, path-layout safety, capability checks,
every Restic subprocess call, snapshot resolution, and copy lineage.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-correction-v2.md
"""

# This module is the single authoritative Restic policy boundary.
# pylint: disable=too-many-lines

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

# ---------------------------------------------------------------------------
# Exit codes — Restic 10/11/12 preserved; domain 20–32 otherwise
# ---------------------------------------------------------------------------
EXIT_OK = 0

# Restic reserved (never overwritten by domain codes)
RESTIC_EXIT_REPOSITORY = 10
RESTIC_EXIT_LOCK = 11
RESTIC_EXIT_PASSWORD = 12
RESTIC_RESERVED_EXITS = frozenset(
    {RESTIC_EXIT_REPOSITORY, RESTIC_EXIT_LOCK, RESTIC_EXIT_PASSWORD}
)

EXIT_INVALID_CONFIG = 20
EXIT_RESTIC_UNAVAILABLE = 21
EXIT_SNAPSHOT_JSON_FAILURE = 22
EXIT_NO_TAGGED_SNAPSHOT = 23
EXIT_WRONG_PATH = 24
EXIT_STALE = 25
EXIT_INVALID_ID = 26
EXIT_COPY_LINEAGE_FAILURE = 27
EXIT_ACTION_FAILURE = 28
EXIT_REPORT_FAILURE = 29
EXIT_REPAIRABLE_DRIFT = 30
EXIT_BLOCKED = 31
EXIT_ISOLATION_FAILURE = 32

TAG_COMPLETE_DATA_V2 = "convmem-data-v2"
TAG_LEGACY_CHROMA = "convmem-chroma"

_DEFAULT_ENV_FILE = Path("~/.config/convmem/restic.env")
_MINIMUM_RESTIC = (0, 19, 0)
_OPAQUE_SCHEMES = (
    "sftp:",
    "rest:",
    "s3:",
    "b2:",
    "azure:",
    "gs:",
    "swift:",
    "rclone:",
)
_FULL_SNAPSHOT_ID_RE = re.compile(r"^[0-9a-f]{64}$")


class BackupProfile(str, Enum):
    """Activation profile for backup protection claims."""

    LEGACY_CHROMA = "legacy-chroma"
    COMPLETE_DATA_V2 = "complete-data-v2"


class ResolverError(Exception):
    """Checked failure with a numeric exit code."""

    def __init__(self, message: str, exit_code: int = EXIT_ACTION_FAILURE):
        super().__init__(message)
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Repository / snapshot refs
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RepositoryRef:
    """Local realpath or opaque remote locator."""

    locator: str
    is_local: bool

    @property
    def path(self) -> Path | None:
        if not self.is_local:
            return None
        return Path(self.locator)

    def __str__(self) -> str:
        return self.locator


@dataclass(frozen=True)
class SnapshotRef:
    """Immutable validated snapshot reference."""

    repository: str
    id: str
    original: str | None
    tree: str
    time: datetime
    paths: tuple[str, ...]
    tags: frozenset[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "id": self.id,
            "original": self.original,
            "tree": self.tree,
            "time": self.time.isoformat(),
            "paths": list(self.paths),
            "tags": sorted(self.tags),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_snapshot_json(cls, repository: str, snap: dict[str, Any]) -> SnapshotRef:
        raw_time = snap.get("time") or ""
        dt = _parse_restic_time(raw_time)
        return cls(
            repository=repository,
            id=str(snap.get("id") or ""),
            original=str(snap.get("original") or "") or None,
            tree=str(snap.get("tree") or ""),
            time=dt,
            paths=tuple(str(p) for p in (snap.get("paths") or [])),
            tags=frozenset(str(t) for t in (snap.get("tags") or [])),
        )


@dataclass(frozen=True)
# The explicit immutable context prevents ambient configuration fallbacks.
# pylint: disable=too-many-instance-attributes
class BackupContext:
    """Immutable backup configuration — no trust-caller bypass."""

    profile: BackupProfile
    local_repository: RepositoryRef
    external_repository: RepositoryRef | None
    password_file: Path
    data_root: Path
    chroma_dir: Path
    restic_bin: Path
    subprocess_env: Mapping[str, str]
    # Clear marking when legacy profile derives data_root from chroma parent.
    data_root_derived: bool = False

    def default_tag(self) -> str:
        if self.profile is BackupProfile.COMPLETE_DATA_V2:
            return TAG_COMPLETE_DATA_V2
        return TAG_LEGACY_CHROMA

    def to_public_dict(self) -> dict[str, Any]:
        """JSON-safe context summary (never includes password contents)."""
        return {
            "profile": self.profile.value,
            "local_repository": self.local_repository.locator,
            "external_repository": (
                self.external_repository.locator if self.external_repository else None
            ),
            "password_file": str(self.password_file),
            "data_root": str(self.data_root),
            "chroma_dir": str(self.chroma_dir),
            "restic_bin": str(self.restic_bin),
            "data_root_derived": self.data_root_derived,
            "default_tag": self.default_tag(),
            "subprocess_env_keys": sorted(self.subprocess_env.keys()),
        }

    @classmethod
    def from_env_file(cls, path: str | Path | None = None) -> BackupContext:
        """Load credentials/cache once, validate layout, build subprocess env.

        There is no trust-caller bypass: every path is normalized and checked.
        """
        env_path = Path(path).expanduser() if path else _DEFAULT_ENV_FILE.expanduser()
        if not env_path.is_file():
            raise ResolverError(
                f"restic env file missing: {env_path}", EXIT_INVALID_CONFIG
            )
        raw = _parse_env_file(env_path)
        return cls.from_mapping(raw, env_file=env_path)

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, str],
        *,
        env_file: Path | None = None,
    ) -> BackupContext:
        """Build a validated context from an already-loaded key/value mapping."""
        del env_file  # reserved for future diagnostics
        profile = _parse_profile(raw.get("CONVMEM_BACKUP_PROFILE", ""))

        chroma_raw = (raw.get("CONVMEM_CHROMA_DIR") or "").strip()
        if not chroma_raw:
            raise ResolverError(
                "CONVMEM_CHROMA_DIR is required", EXIT_INVALID_CONFIG
            )
        chroma_dir = _normalize_existing_dir(chroma_raw, "CONVMEM_CHROMA_DIR")

        data_root_raw = (raw.get("CONVMEM_DATA_ROOT") or "").strip()
        data_root_derived = False
        if profile is BackupProfile.COMPLETE_DATA_V2:
            if not data_root_raw:
                raise ResolverError(
                    "complete-data-v2 requires explicit CONVMEM_DATA_ROOT "
                    "(parent derivation from Chroma is forbidden)",
                    EXIT_INVALID_CONFIG,
                )
            data_root = _normalize_existing_dir(data_root_raw, "CONVMEM_DATA_ROOT")
        else:
            if data_root_raw:
                data_root = _normalize_existing_dir(data_root_raw, "CONVMEM_DATA_ROOT")
            else:
                # Legacy chroma-only layout: derive parent with WARN marking.
                data_root = chroma_dir.parent.resolve()
                data_root_derived = True
                warnings.warn(
                    "WARN_LEGACY_ONLY: CONVMEM_DATA_ROOT unset; derived from "
                    f"CONVMEM_CHROMA_DIR parent ({data_root}). "
                    "This never proves complete-data-v2 protection.",
                    UserWarning,
                    stacklevel=2,
                )

        repo_raw = (raw.get("RESTIC_REPOSITORY") or "").strip()
        if not repo_raw:
            raise ResolverError("RESTIC_REPOSITORY is required", EXIT_INVALID_CONFIG)
        local_repository = parse_repository_ref(repo_raw)

        ext_raw = (raw.get("RESTIC_EXTERNAL_REPOSITORY") or "").strip()
        external_repository = parse_repository_ref(ext_raw) if ext_raw else None

        pw_raw = (raw.get("RESTIC_PASSWORD_FILE") or "").strip()
        if not pw_raw:
            raise ResolverError(
                "RESTIC_PASSWORD_FILE is required", EXIT_INVALID_CONFIG
            )
        password_file = Path(pw_raw).expanduser().resolve()
        if not password_file.is_file():
            raise ResolverError(
                f"RESTIC_PASSWORD_FILE not found: {password_file}",
                EXIT_INVALID_CONFIG,
            )

        restic_bin_raw = (
            raw.get("RESTIC_BIN")
            or raw.get("CONVMEM_RESTIC_BIN")
            or os.environ.get("RESTIC_TEST_BIN")
            or "restic"
        ).strip()
        restic_bin = _resolve_restic_bin(restic_bin_raw)

        cache_raw = (
            raw.get("RESTIC_CACHE_DIR")
            or raw.get("CONVMEM_RESTIC_CACHE_DIR")
            or os.environ.get("RESTIC_CACHE_DIR")
            or ""
        ).strip()
        if cache_raw:
            cache_dir = Path(cache_raw).expanduser().resolve()
        else:
            tmp = os.environ.get("TMPDIR") or "/tmp"
            cache_dir = (Path(tmp) / "convmem-restic-cache").resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)

        validate_path_layout(
            data_root=data_root,
            chroma_dir=chroma_dir,
            local_repo=local_repository,
            external_repo=external_repository,
            password_file=password_file,
        )

        subprocess_env = _build_subprocess_env(
            password_file=password_file,
            cache_dir=cache_dir,
        )

        return cls(
            profile=profile,
            local_repository=local_repository,
            external_repository=external_repository,
            password_file=password_file,
            data_root=data_root,
            chroma_dir=chroma_dir,
            restic_bin=restic_bin,
            subprocess_env=subprocess_env,
            data_root_derived=data_root_derived,
        )


# ---------------------------------------------------------------------------
# Env / path helpers
# ---------------------------------------------------------------------------
def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key:
            values[key] = val
    return values


def _parse_profile(raw: str) -> BackupProfile:
    value = (raw or "").strip()
    if not value:
        return BackupProfile.LEGACY_CHROMA
    try:
        return BackupProfile(value)
    except ValueError as exc:
        raise ResolverError(
            f"invalid CONVMEM_BACKUP_PROFILE={value!r}; "
            f"expected legacy-chroma|complete-data-v2",
            EXIT_INVALID_CONFIG,
        ) from exc


def _normalize_existing_dir(raw: str, label: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise ResolverError(f"{label} does not exist: {path}", EXIT_INVALID_CONFIG)
    if not path.is_dir():
        raise ResolverError(
            f"{label} is not a directory: {path}", EXIT_INVALID_CONFIG
        )
    return path


def _resolve_restic_bin(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return candidate.resolve()
    found = shutil.which(raw)
    if found is None:
        raise ResolverError(
            f"restic not found ({raw!r}); install restic >= 0.19.0",
            EXIT_RESTIC_UNAVAILABLE,
        )
    return Path(found).resolve()


def parse_repository_ref(raw: str) -> RepositoryRef:
    """Normalize local repo paths; leave opaque remotes unchanged."""
    locator = raw.strip()
    if not locator:
        raise ResolverError("empty repository locator", EXIT_INVALID_CONFIG)

    if locator.startswith("local:"):
        path = Path(locator[len("local:") :]).expanduser().resolve()
        return RepositoryRef(locator=str(path), is_local=True)

    lower = locator.lower()
    if any(lower.startswith(scheme) for scheme in _OPAQUE_SCHEMES):
        return RepositoryRef(locator=locator, is_local=False)

    # Absolute, relative, ~, or bare local path (no remote scheme).
    if ":" not in locator or locator.startswith(("/", ".", "~")):
        path = Path(locator).expanduser().resolve()
        return RepositoryRef(locator=str(path), is_local=True)

    # Unknown scheme — treat as opaque to avoid mangling remotes.
    return RepositoryRef(locator=locator, is_local=False)


def normalize_data_root(raw: str | Path) -> Path:
    return Path(raw).expanduser().resolve()


def _is_contained(inner: Path, outer: Path) -> bool:
    try:
        inner.relative_to(outer)
        return True
    except ValueError:
        return False


def _paths_overlap(a: Path, b: Path) -> bool:
    return a == b or _is_contained(a, b) or _is_contained(b, a)


def validate_path_layout(
    *,
    data_root: Path,
    chroma_dir: Path,
    local_repo: RepositoryRef,
    external_repo: RepositoryRef | None,
    password_file: Path,
) -> None:
    """Reject unsafe path configurations before any Restic operation."""
    home = Path.home().resolve()
    if data_root == Path("/") or data_root == home:
        raise ResolverError(
            f"data root must not be / or home directory: {data_root}",
            EXIT_INVALID_CONFIG,
        )
    if chroma_dir == Path("/") or chroma_dir == home:
        raise ResolverError(
            f"chroma dir must not be / or home directory: {chroma_dir}",
            EXIT_INVALID_CONFIG,
        )
    if chroma_dir == data_root:
        raise ResolverError(
            "CONVMEM_DATA_ROOT must not equal CONVMEM_CHROMA_DIR",
            EXIT_INVALID_CONFIG,
        )

    _check_repo_safety(local_repo, data_root, password_file, "local repository")
    if external_repo is not None:
        _check_repo_safety(
            external_repo, data_root, password_file, "external repository"
        )
        if (
            local_repo.is_local
            and external_repo.is_local
            and local_repo.path is not None
            and external_repo.path is not None
            and _paths_overlap(local_repo.path, external_repo.path)
        ):
            raise ResolverError(
                "external repository must not overlap local repository",
                EXIT_INVALID_CONFIG,
            )


def _check_repo_safety(
    repo: RepositoryRef,
    data_root: Path,
    password_file: Path,
    label: str,
) -> None:
    if not repo.is_local or repo.path is None:
        return
    rp = repo.path
    if _paths_overlap(rp, data_root):
        raise ResolverError(
            f"{label} must not overlap data root: {rp} vs {data_root}",
            EXIT_INVALID_CONFIG,
        )
    # Repo/password overlap: password must not live inside the repo tree,
    # and the repo must not be the password file itself. Sibling paths under
    # a shared parent (e.g. hermetic fixtures) are allowed.
    if rp == password_file or _is_contained(password_file, rp) or _is_contained(rp, password_file):
        raise ResolverError(
            f"{label} must not overlap password file path: {rp} vs {password_file}",
            EXIT_INVALID_CONFIG,
        )


def _build_subprocess_env(
    *,
    password_file: Path,
    cache_dir: Path,
) -> dict[str, str]:
    """Exact curated environment for every Restic subprocess."""
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "RESTIC_PASSWORD_FILE": str(password_file),
        "RESTIC_CACHE_DIR": str(cache_dir),
        "HOME": os.environ.get("HOME", str(Path.home())),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", os.environ.get("LANG", "C.UTF-8")),
    }
    for key in ("TMPDIR", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR"):
        if key in os.environ and os.environ[key]:
            env[key] = os.environ[key]
    return env


def _parse_restic_time(raw: str) -> datetime:
    if not raw:
        raise ResolverError("snapshot missing time field", EXIT_SNAPSHOT_JSON_FAILURE)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        m = re.match(
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d{2}:\d{2}|Z)?",
            raw,
        )
        if not m:
            raise ResolverError(
                f"unparseable snapshot time: {raw!r}", EXIT_SNAPSHOT_JSON_FAILURE
            ) from exc
        frac = (m.group(2) or "")[:7]
        tz = m.group(3) or "+00:00"
        if tz == "Z":
            tz = "+00:00"
        dt = datetime.fromisoformat(f"{m.group(1)}{frac}{tz}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def normalize_snapshot_paths(snap_paths: Sequence[str], data_root: Path) -> list[str]:
    """Require exactly one path equal to the normalized data root."""
    normalized = [str(Path(p).expanduser().resolve()) for p in snap_paths]
    expected = str(data_root.resolve())
    if normalized != [expected]:
        raise ResolverError(
            f"snapshot paths {normalized} do not match data root [{expected}]",
            EXIT_WRONG_PATH,
        )
    return normalized


def _is_current_local_day(dt: datetime) -> bool:
    local_dt = dt.astimezone()
    today = datetime.now().astimezone().date()
    return local_dt.date() >= today


# ---------------------------------------------------------------------------
# Restic subprocess boundary
# ---------------------------------------------------------------------------
def _map_restic_exit(returncode: int, domain_fallback: int) -> int:
    """Preserve Restic 10/11/12; otherwise use the domain fallback."""
    if returncode in RESTIC_RESERVED_EXITS:
        return returncode
    return domain_fallback


def _run_restic(
    ctx: BackupContext,
    argv: Sequence[str],
    *,
    repository: RepositoryRef | None = None,
    timeout: float | None = None,
    domain_error_code: int = EXIT_ACTION_FAILURE,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Central entry for ALL restic subprocesses.

    ``argv`` is the restic subcommand and its flags only (no binary, no ``-r``).
    """
    if any(a == "--latest" or str(a).startswith("--latest=") for a in argv):
        raise ResolverError(
            "argv must never contain --latest", EXIT_INVALID_CONFIG
        )

    repo = repository or ctx.local_repository
    cmd = [str(ctx.restic_bin), "-r", repo.locator, *argv]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=dict(ctx.subprocess_env),
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise ResolverError(
            f"restic binary missing: {ctx.restic_bin}", EXIT_RESTIC_UNAVAILABLE
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ResolverError(
            f"restic timed out: {' '.join(cmd)}", domain_error_code
        ) from exc

    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise ResolverError(
            f"restic failed (exit {proc.returncode}): {detail[:500]}",
            _map_restic_exit(proc.returncode, domain_error_code),
        )
    return proc


def parse_restic_version(output: str) -> tuple[int, int, int]:
    parts = output.strip().split()
    for part in parts:
        if part and part[0].isdigit():
            chunks = part.split(".")
            if len(chunks) >= 3:
                try:
                    return (int(chunks[0]), int(chunks[1]), int(chunks[2]))
                except ValueError:
                    continue
    raise ResolverError(
        f"cannot parse restic version from: {output!r}", EXIT_RESTIC_UNAVAILABLE
    )


def check_restic_available(restic_bin: str | Path = "restic") -> str:
    """Verify restic exists and reports >= 0.19.0. Returns version stdout."""
    bin_path = Path(restic_bin)
    resolved: str
    if bin_path.is_file() and os.access(bin_path, os.X_OK):
        resolved = str(bin_path.resolve())
    else:
        found = shutil.which(str(restic_bin))
        if found is None:
            raise ResolverError(
                "restic not on PATH (install: pacman -S restic)",
                EXIT_RESTIC_UNAVAILABLE,
            )
        resolved = found

    proc = subprocess.run(
        [resolved, "version"], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise ResolverError(
            f"restic version command failed: "
            f"{(proc.stderr or proc.stdout).strip()}",
            EXIT_RESTIC_UNAVAILABLE,
        )
    version = parse_restic_version(proc.stdout)
    if version < _MINIMUM_RESTIC:
        raise ResolverError(
            f"restic {version[0]}.{version[1]}.{version[2]} below minimum "
            f"{_MINIMUM_RESTIC[0]}.{_MINIMUM_RESTIC[1]}.{_MINIMUM_RESTIC[2]}",
            EXIT_RESTIC_UNAVAILABLE,
        )
    return proc.stdout.strip()


def verify_restic_capabilities(ctx: BackupContext) -> None:
    """Behavioral capability check — not version-string-only.

    Requires ``snapshots --json`` and, when snapshots exist, explicit-ID
    ``check <id> --read-data-subset``. An empty capability surface fails.
    """
    check_restic_available(ctx.restic_bin)

    help_proc = subprocess.run(
        [str(ctx.restic_bin), "help"],
        capture_output=True,
        text=True,
        env=dict(ctx.subprocess_env),
        check=False,
    )
    help_text = (help_proc.stdout or "") + (help_proc.stderr or "")
    for token in ("snapshots", "backup", "check", "copy"):
        if token not in help_text:
            raise ResolverError(
                f"restic capability missing: {token!r} not in help output",
                EXIT_RESTIC_UNAVAILABLE,
            )

    proc = _run_restic(
        ctx,
        ["snapshots", "--json"],
        domain_error_code=EXIT_SNAPSHOT_JSON_FAILURE,
        check=True,
    )
    try:
        snaps: list[dict[str, Any]] = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ResolverError(
            f"snapshot JSON unparsable during capability check: {exc}",
            EXIT_SNAPSHOT_JSON_FAILURE,
        ) from exc

    if not isinstance(snaps, list):
        raise ResolverError(
            "snapshot JSON capability check expected a list",
            EXIT_SNAPSHOT_JSON_FAILURE,
        )

    if not snaps:
        return

    snap = snaps[0]
    required_fields = ("id", "tree", "time", "paths", "tags")
    missing = [f for f in required_fields if f not in snap]
    if missing:
        raise ResolverError(
            f"snapshot JSON missing fields: {missing}",
            EXIT_SNAPSHOT_JSON_FAILURE,
        )

    snap_id = str(snap["id"])
    if not _FULL_SNAPSHOT_ID_RE.match(snap_id):
        raise ResolverError(
            f"capability check saw non-full snapshot id: {snap_id!r}",
            EXIT_SNAPSHOT_JSON_FAILURE,
        )

    _run_restic(
        ctx,
        ["check", snap_id, "--read-data-subset=1%"],
        timeout=300,
        domain_error_code=EXIT_ACTION_FAILURE,
        check=True,
    )


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------
def _list_tagged_snapshots(
    ctx: BackupContext,
    *,
    repository: RepositoryRef,
    tag: str,
) -> list[SnapshotRef]:
    proc = _run_restic(
        ctx,
        ["snapshots", "--json", "--tag", tag],
        repository=repository,
        domain_error_code=EXIT_SNAPSHOT_JSON_FAILURE,
        check=True,
    )
    try:
        snaps: list[dict[str, Any]] = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ResolverError(
            f"snapshot JSON unparsable: {exc}", EXIT_SNAPSHOT_JSON_FAILURE
        ) from exc
    if not isinstance(snaps, list):
        raise ResolverError(
            "snapshot JSON must be a list", EXIT_SNAPSHOT_JSON_FAILURE
        )
    return [SnapshotRef.from_snapshot_json(repository.locator, s) for s in snaps]


def resolve_snapshot(
    ctx: BackupContext,
    *,
    require_current_local_day: bool = False,
    requested_id: str | None = None,
    required_tag: str | None = None,
    repository: RepositoryRef | None = None,
) -> SnapshotRef:
    """Select a tagged snapshot by exact path filter — never ``--latest``.

    Defaults:
    - complete-data-v2 → tag ``convmem-data-v2``
    - legacy-chroma → tag ``convmem-chroma`` (compatibility only; never proves v2)
    """
    check_restic_available(ctx.restic_bin)
    tag = required_tag if required_tag is not None else ctx.default_tag()
    repo = repository or ctx.local_repository
    expected_root = ctx.data_root.resolve()

    refs = _list_tagged_snapshots(ctx, repository=repo, tag=tag)
    if not refs:
        raise ResolverError(
            f"no snapshots tagged {tag}", EXIT_NO_TAGGED_SNAPSHOT
        )

    if requested_id is not None:
        sid = requested_id.strip()
        if not _FULL_SNAPSHOT_ID_RE.match(sid):
            raise ResolverError(
                f"requested snapshot ID must be a full 64-char hex id "
                f"(got {sid!r})",
                EXIT_INVALID_ID,
            )
        matches = [r for r in refs if r.id == sid]
        if not matches:
            raise ResolverError(
                f"requested snapshot ID {sid} not found in tagged snapshots",
                EXIT_INVALID_ID,
            )
        if len(matches) > 1:
            raise ResolverError(
                f"ambiguous snapshot ID {sid}: {len(matches)} matches",
                EXIT_INVALID_ID,
            )
        ref = matches[0]
        normalize_snapshot_paths(list(ref.paths), expected_root)
        if require_current_local_day and not _is_current_local_day(ref.time):
            raise ResolverError(
                f"requested snapshot {sid[:12]} is stale (not current local day)",
                EXIT_STALE,
            )
        return ref

    correct_path_refs: list[SnapshotRef] = []
    for ref in refs:
        try:
            normalize_snapshot_paths(list(ref.paths), expected_root)
        except ResolverError:
            continue
        correct_path_refs.append(ref)

    if not correct_path_refs:
        raise ResolverError(
            f"no {tag} snapshot matches data root {expected_root}",
            EXIT_WRONG_PATH,
        )

    correct_path_refs.sort(key=lambda r: r.time, reverse=True)
    best = correct_path_refs[0]
    if require_current_local_day and not _is_current_local_day(best.time):
        raise ResolverError(
            "correct-path snapshot exists but is stale (not current local day)",
            EXIT_STALE,
        )
    return best


def resolve_copy_destination(
    ctx: BackupContext,
    source: SnapshotRef,
    *,
    required_tag: str | None = None,
) -> SnapshotRef:
    """Resolve destination copy where ``D.original == source.id``."""
    if ctx.external_repository is None:
        raise ResolverError(
            "external repository is not configured", EXIT_COPY_LINEAGE_FAILURE
        )
    check_restic_available(ctx.restic_bin)
    tag = required_tag if required_tag is not None else ctx.default_tag()
    refs = _list_tagged_snapshots(
        ctx, repository=ctx.external_repository, tag=tag
    )
    if not refs:
        raise ResolverError(
            f"no {tag} snapshots in destination repository",
            EXIT_COPY_LINEAGE_FAILURE,
        )

    candidates = [r for r in refs if r.original == source.id]
    if not candidates:
        raise ResolverError(
            f"no destination snapshot with original={source.id[:12]}",
            EXIT_COPY_LINEAGE_FAILURE,
        )
    if len(candidates) > 1:
        raise ResolverError(
            f"ambiguous copy lineage: {len(candidates)} destinations "
            f"for source {source.id[:12]}",
            EXIT_COPY_LINEAGE_FAILURE,
        )

    dest = candidates[0]
    if dest.tree != source.tree:
        raise ResolverError(
            f"destination tree {dest.tree[:12]} != source tree {source.tree[:12]}",
            EXIT_COPY_LINEAGE_FAILURE,
        )
    if dest.time != source.time:
        raise ResolverError(
            f"destination time {dest.time} != source time {source.time}",
            EXIT_COPY_LINEAGE_FAILURE,
        )
    if set(dest.paths) != set(source.paths):
        raise ResolverError(
            f"destination paths {list(dest.paths)} != source paths {list(source.paths)}",
            EXIT_COPY_LINEAGE_FAILURE,
        )
    if tag not in dest.tags or tag not in source.tags:
        raise ResolverError(
            f"copy lineage missing required tag {tag}",
            EXIT_COPY_LINEAGE_FAILURE,
        )
    return dest



# ---------------------------------------------------------------------------
# Mutating / checking actions (all Restic I/O stays here)
# ---------------------------------------------------------------------------
def ensure_repository_initialized(ctx: BackupContext) -> bool:
    """Return True if ``restic init`` ran; False if repo already existed."""
    check_restic_available(ctx.restic_bin)
    probe = _run_restic(
        ctx,
        ["cat", "config"],
        domain_error_code=EXIT_ACTION_FAILURE,
        check=False,
    )
    if probe.returncode == 0:
        return False
    _run_restic(
        ctx,
        ["init"],
        domain_error_code=EXIT_ACTION_FAILURE,
        check=True,
    )
    return True


def backup_data_root(
    ctx: BackupContext,
    *,
    extra_tags: Sequence[str] | None = None,
) -> tuple[SnapshotRef, tuple[str, ...]]:
    """Backup ``ctx.data_root`` with the profile default tag. Returns (ref, argv)."""
    check_restic_available(ctx.restic_bin)
    tag = ctx.default_tag()
    day_tag = f"convmem-{datetime.now().astimezone().date().isoformat()}"
    tags = [tag, day_tag, *(extra_tags or ())]
    argv = ["backup", str(ctx.data_root.resolve()), "--json"]
    for t in tags:
        argv.extend(["--tag", t])
    full_cmd_preview = (
        str(ctx.restic_bin),
        "-r",
        ctx.local_repository.locator,
        *argv,
    )
    if any(a == "--latest" or str(a).startswith("--latest=") for a in full_cmd_preview):
        raise ResolverError("argv must never contain --latest", EXIT_INVALID_CONFIG)
    proc = _run_restic(
        ctx,
        argv,
        domain_error_code=EXIT_ACTION_FAILURE,
        check=True,
    )
    snap_id: str | None = None
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("message_type") == "summary":
            snap_id = str(msg.get("snapshot_id") or "")
            break
    if not snap_id or not _FULL_SNAPSHOT_ID_RE.match(snap_id):
        raise ResolverError(
            "backup summary missing full snapshot id",
            EXIT_SNAPSHOT_JSON_FAILURE,
        )
    ref = resolve_snapshot(ctx, requested_id=snap_id)
    return ref, full_cmd_preview


def copy_snapshot_to_external(
    ctx: BackupContext,
    source_id: str,
) -> tuple[str, ...]:
    """Copy an explicit full snapshot id to the external repo. Returns argv used."""
    if ctx.external_repository is None:
        raise ResolverError(
            "external repository is not configured", EXIT_COPY_LINEAGE_FAILURE
        )
    sid = source_id.strip()
    if not _FULL_SNAPSHOT_ID_RE.match(sid):
        raise ResolverError(
            f"copy source id must be full 64-char hex (got {sid!r})",
            EXIT_INVALID_ID,
        )
    check_restic_available(ctx.restic_bin)
    argv = [
        "copy",
        sid,
        "--from-repo",
        ctx.local_repository.locator,
        "--from-password-file",
        str(ctx.password_file),
    ]
    full_cmd = (
        str(ctx.restic_bin),
        "-r",
        ctx.external_repository.locator,
        *argv,
    )
    if any(a == "--latest" or str(a).startswith("--latest=") for a in full_cmd):
        raise ResolverError("argv must never contain --latest", EXIT_INVALID_CONFIG)
    _run_restic(
        ctx,
        argv,
        repository=ctx.external_repository,
        domain_error_code=EXIT_COPY_LINEAGE_FAILURE,
        check=True,
    )
    return full_cmd


def check_snapshot(
    ctx: BackupContext,
    snapshot_id: str,
    *,
    full_read_data: bool = False,
    read_data_subset: str | None = "5%",
    repository: RepositoryRef | None = None,
    timeout: float | None = None,
) -> tuple[subprocess.CompletedProcess[str], tuple[str, ...]]:
    """Run ``restic check <full-id>`` — never tag/path reselection."""
    sid = snapshot_id.strip()
    if not _FULL_SNAPSHOT_ID_RE.match(sid):
        raise ResolverError(
            f"check snapshot id must be full 64-char hex (got {sid!r})",
            EXIT_INVALID_ID,
        )
    check_restic_available(ctx.restic_bin)
    argv: list[str] = ["check", sid]
    if full_read_data:
        argv.append("--read-data")
    elif read_data_subset:
        argv.extend(["--read-data-subset", read_data_subset])
    repo = repository or ctx.local_repository
    full_cmd = (str(ctx.restic_bin), "-r", repo.locator, *argv)
    if any(a == "--latest" or str(a).startswith("--latest=") for a in full_cmd):
        raise ResolverError("argv must never contain --latest", EXIT_INVALID_CONFIG)
    proc = _run_restic(
        ctx,
        argv,
        repository=repo,
        timeout=timeout,
        domain_error_code=EXIT_ACTION_FAILURE,
        check=False,
    )
    return proc, full_cmd


def restore_snapshot(
    ctx: BackupContext,
    snapshot_id: str,
    target_dir: str | Path,
    *,
    repository: RepositoryRef | None = None,
) -> tuple[str, ...]:
    """Restore an explicit full snapshot id into ``target_dir``. Returns argv."""
    sid = snapshot_id.strip()
    if not _FULL_SNAPSHOT_ID_RE.match(sid):
        raise ResolverError(
            f"restore snapshot id must be full 64-char hex (got {sid!r})",
            EXIT_INVALID_ID,
        )
    target = Path(target_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    check_restic_available(ctx.restic_bin)
    argv = ["restore", sid, "--target", str(target)]
    repo = repository or ctx.local_repository
    full_cmd = (str(ctx.restic_bin), "-r", repo.locator, *argv)
    if any(a == "--latest" or str(a).startswith("--latest=") for a in full_cmd):
        raise ResolverError("argv must never contain --latest", EXIT_INVALID_CONFIG)
    _run_restic(
        ctx,
        argv,
        repository=repo,
        domain_error_code=EXIT_ACTION_FAILURE,
        check=True,
    )
    return full_cmd


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_error(exc: BaseException) -> None:
    print(f"ERROR: {exc}", file=sys.stderr)


def _cli_load_context(env_file: str | None) -> BackupContext:
    return BackupContext.from_env_file(env_file)


def _cli_resolve(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="restic_snapshot.py resolve")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--require-current-local-day", action="store_true")
    parser.add_argument("--snapshot-id", default=None)
    parser.add_argument("--tag", default=None)
    opts = parser.parse_args(args)

    try:
        ctx = _cli_load_context(opts.env_file)
        ref = resolve_snapshot(
            ctx,
            require_current_local_day=opts.require_current_local_day,
            requested_id=opts.snapshot_id,
            required_tag=opts.tag,
        )
        print(ref.to_json())
        return EXIT_OK
    except ResolverError as exc:
        _print_error(exc)
        return exc.exit_code


def _cli_resolve_copy_destination(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="restic_snapshot.py resolve-copy-destination"
    )
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--source-json", required=True)
    parser.add_argument("--tag", default=None)
    opts = parser.parse_args(args)

    try:
        ctx = _cli_load_context(opts.env_file)
        source_data = json.loads(opts.source_json)
        source = SnapshotRef.from_snapshot_json(
            source_data.get("repository", ""),
            source_data,
        )
        dest = resolve_copy_destination(
            ctx, source, required_tag=opts.tag
        )
        print(dest.to_json())
        return EXIT_OK
    except json.JSONDecodeError as exc:
        _print_error(exc)
        return EXIT_COPY_LINEAGE_FAILURE
    except ResolverError as exc:
        _print_error(exc)
        return exc.exit_code


def _cli_check_capabilities(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="restic_snapshot.py check-capabilities"
    )
    parser.add_argument("--env-file", default=None)
    opts = parser.parse_args(args)

    try:
        ctx = _cli_load_context(opts.env_file)
        verify_restic_capabilities(ctx)
        print(json.dumps({"ok": True, "restic_bin": str(ctx.restic_bin)}))
        return EXIT_OK
    except ResolverError as exc:
        _print_error(exc)
        return exc.exit_code


def _cli_show_context(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="restic_snapshot.py show-context")
    parser.add_argument("--env-file", default=None)
    opts = parser.parse_args(args)

    try:
        ctx = _cli_load_context(opts.env_file)
        print(json.dumps(ctx.to_public_dict(), indent=2))
        return EXIT_OK
    except ResolverError as exc:
        _print_error(exc)
        return exc.exit_code


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "usage: restic_snapshot.py "
            "<resolve|resolve-copy-destination|check-capabilities|show-context> "
            "[...]",
            file=sys.stderr,
        )
        return EXIT_INVALID_CONFIG

    cmd, rest = args[0], args[1:]
    if cmd == "resolve":
        return _cli_resolve(rest)
    if cmd == "resolve-copy-destination":
        return _cli_resolve_copy_destination(rest)
    if cmd == "check-capabilities":
        return _cli_check_capabilities(rest)
    if cmd == "show-context":
        return _cli_show_context(rest)

    print(f"unknown command: {cmd}", file=sys.stderr)
    return EXIT_INVALID_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
