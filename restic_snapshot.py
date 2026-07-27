"""Authoritative Restic snapshot resolver for complete-data backup protection.

This module owns all snapshot selection, path validation, explicit-ID
handoff, and copy-lineage verification. Python consumers import it; shell
consumers invoke its CLI and parse a single JSON object.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-audit-closure.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Exit codes (T1 domain codes 20-29; Restic 10-12 preserved unchanged)
# ---------------------------------------------------------------------------
EXIT_OK = 0
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


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------
class ResolverError(Exception):
    """Checked failure with a numeric exit code."""

    def __init__(self, message: str, exit_code: int = EXIT_ACTION_FAILURE):
        super().__init__(message)
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Snapshot reference
# ---------------------------------------------------------------------------
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

    def to_json(self) -> str:
        return json.dumps(
            {
                "repository": self.repository,
                "id": self.id,
                "original": self.original,
                "tree": self.tree,
                "time": self.time.isoformat(),
                "paths": list(self.paths),
                "tags": sorted(self.tags),
            }
        )

    @classmethod
    def from_snapshot_json(cls, repository: str, snap: dict[str, Any]) -> SnapshotRef:
        """Build a SnapshotRef from a Restic snapshot JSON object."""
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


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------
def _parse_restic_time(raw: str) -> datetime:
    """Parse a Restic snapshot timestamp into a timezone-aware datetime."""
    if not raw:
        raise ResolverError("snapshot missing time field", EXIT_SNAPSHOT_JSON_FAILURE)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        # Trim fractional to at most 6 digits for Python's fromisoformat
        import re

        m = re.match(
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d{2}:\d{2}|Z)?",
            raw,
        )
        if not m:
            raise ResolverError(
                f"unparseable snapshot time: {raw!r}", EXIT_SNAPSHOT_JSON_FAILURE
            )
        frac = (m.group(2) or "")[:7]
        tz = m.group(3) or "+00:00"
        if tz == "Z":
            tz = "+00:00"
        dt = datetime.fromisoformat(f"{m.group(1)}{frac}{tz}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Path normalization and safety contract
# ---------------------------------------------------------------------------
def normalize_data_root(raw: str | Path) -> Path:
    """Expand, absolutize, and resolve a data-root path for safety checks."""
    p = Path(raw).expanduser().resolve()
    return p


def validate_path_layout(
    data_root: Path,
    chroma_dir: Path | None = None,
    *,
    local_repo: str | None = None,
    external_repo: str | None = None,
    password_file: str | None = None,
    require_existence: bool = True,
) -> None:
    """Reject unsafe path configurations before any Restic operation.

    Raises ResolverError(EXIT_INVALID_CONFIG) on any violation.
    """
    if require_existence:
        if not data_root.exists():
            raise ResolverError(
                f"data root does not exist: {data_root}", EXIT_INVALID_CONFIG
            )
        if not data_root.is_dir():
            raise ResolverError(
                f"data root is not a directory: {data_root}", EXIT_INVALID_CONFIG
            )

    # Reject / and home directory
    home = Path.home().resolve()
    if data_root == Path("/") or data_root == home:
        raise ResolverError(
            f"data root must not be / or home directory: {data_root}",
            EXIT_INVALID_CONFIG,
        )

    # Reject chroma dir equals data root
    if chroma_dir is not None:
        cd = normalize_data_root(chroma_dir)
        if cd == data_root:
            raise ResolverError(
                "CONVMEM_DATA_ROOT must not equal CONVMEM_CHROMA_DIR", EXIT_INVALID_CONFIG
            )

    # Reject local repo overlap with data root or password file
    if local_repo is not None:
        _check_repo_safety(local_repo, data_root, "local repository", password_file)

    # Reject external repo overlap with local repo or data root
    if external_repo is not None:
        _check_repo_safety(external_repo, data_root, "external repository", password_file)
        if local_repo is not None:
            lr = _repo_path(local_repo)
            er = _repo_path(external_repo)
            if lr is not None and er is not None:
                if er == lr or _is_contained(er, lr) or _is_contained(lr, er):
                    raise ResolverError(
                        "external repository must not overlap local repository",
                        EXIT_INVALID_CONFIG,
                    )


def _repo_path(repo: str) -> Path | None:
    """Return the filesystem Path for a local repo locator, or None."""
    repo = repo.strip()
    if repo.startswith("local:"):
        return Path(repo[6:]).expanduser().resolve()
    # Absolute paths, relative paths, or bare directory names are local
    if ":" not in repo or repo.startswith("/") or repo.startswith(".") or repo.startswith("~"):
        return Path(repo).expanduser().resolve()
    # sftp:, rest:, s3:, b2:, azure:, gs:, swift:, rclone: are opaque
    return None


def _check_repo_safety(
    repo: str,
    data_root: Path,
    label: str,
    password_file: str | None,
) -> None:
    rp = _repo_path(repo)
    if rp is None:
        return
    if rp == data_root or _is_contained(rp, data_root) or _is_contained(data_root, rp):
        raise ResolverError(
            f"{label} must not overlap data root: {rp} vs {data_root}",
            EXIT_INVALID_CONFIG,
        )
    if password_file:
        pf = Path(password_file).expanduser().resolve()
        if rp == pf.parent or _is_contained(rp, pf.parent) or _is_contained(pf.parent, rp):
            raise ResolverError(
                f"{label} must not contain the password file: {rp} contains {pf}",
                EXIT_INVALID_CONFIG,
            )


def _is_contained(a: Path, b: Path) -> bool:
    """True if a is a subdirectory of b (or equal)."""
    try:
        a.relative_to(b)
        return True
    except ValueError:
        return False


def normalize_snapshot_paths(snap_paths: list[str], data_root: Path) -> list[str]:
    """Normalize snapshot paths and validate they match the data root.

    Returns the normalized path list. Raises ResolverError on mismatch.
    """
    normalized = [str(Path(p).expanduser().resolve()) for p in snap_paths]
    expected = str(data_root)
    if normalized != [expected]:
        raise ResolverError(
            f"snapshot paths {normalized} do not match data root [{expected}]",
            EXIT_WRONG_PATH,
        )
    return normalized


# ---------------------------------------------------------------------------
# Restic version and capability contract
# ---------------------------------------------------------------------------
_MINIMUM_RESTIC = (0, 19, 0)


def parse_restic_version(output: str) -> tuple[int, int, int]:
    """Parse 'restic 0.19.0 compiled with ...' into (0, 19, 0)."""
    parts = output.strip().split()
    for part in parts:
        if part[0].isdigit():
            chunks = part.split(".")
            if len(chunks) >= 3:
                return (int(chunks[0]), int(chunks[1]), int(chunks[2]))
    raise ResolverError(
        f"cannot parse restic version from: {output!r}", EXIT_RESTIC_UNAVAILABLE
    )


def check_restic_available(restic_bin: str = "restic") -> str:
    """Verify restic is on PATH and >= 0.19.0. Returns the version string."""
    import shutil

    if shutil.which(restic_bin) is None:
        raise ResolverError(
            f"restic not on PATH (install: pacman -S restic)", EXIT_RESTIC_UNAVAILABLE
        )
    proc = subprocess.run(
        [restic_bin, "version"], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise ResolverError(
            f"restic version command failed: {proc.stderr.strip() or proc.stdout.strip()}",
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


def verify_restic_capabilities(
    restic_bin: str,
    repository: str,
    password_file: str,
    env: dict[str, str] | None = None,
) -> None:
    """Behavioral verification of required Restic features.

    Verifies explicit-ID check and snapshot JSON fields.
    """
    check_env = dict(env or os.environ)
    check_env["RESTIC_PASSWORD_FILE"] = str(Path(password_file).expanduser().resolve())

    # List snapshots to get a real ID for capability tests
    proc = subprocess.run(
        [restic_bin, "-r", repository, "snapshots", "--json"],
        capture_output=True,
        text=True,
        env=check_env,
        check=False,
    )
    if proc.returncode != 0:
        raise ResolverError(
            f"cannot list snapshots for capability verification: "
            f"{proc.stderr.strip() or 'exit ' + str(proc.returncode)}",
            EXIT_SNAPSHOT_JSON_FAILURE,
        )
    snaps: list[dict] = json.loads(proc.stdout or "[]")
    if not snaps:
        # No snapshots to test with — verify JSON parsing at minimum
        return

    snap_id = snaps[0]["id"]
    # Verify JSON fields are present
    required_fields = ["id", "tree", "time", "paths", "tags"]
    missing = [f for f in required_fields if f not in snaps[0]]
    if missing:
        raise ResolverError(
            f"snapshot JSON missing fields: {missing}", EXIT_SNAPSHOT_JSON_FAILURE
        )

    # Verify explicit-ID check works
    proc = subprocess.run(
        [restic_bin, "-r", repository, "check", snap_id, "--read-data-subset=1%"],
        capture_output=True,
        text=True,
        env=check_env,
        check=False,
        timeout=300,
    )
    if proc.returncode != 0:
        raise ResolverError(
            f"restic check <id> --read-data-subset failed (behavioral test): "
            f"{proc.stderr.strip() or proc.stdout.strip()[:200]}",
            EXIT_ACTION_FAILURE,
        )


# ---------------------------------------------------------------------------
# Snapshot resolution
# ---------------------------------------------------------------------------
def _run_restic_snapshots(
    restic_bin: str,
    repository: str,
    tag: str,
    env: dict[str, str],
) -> list[dict[str, Any]]:
    """Run `restic snapshots --json --tag <tag>` and return parsed list.

    Never passes --latest.
    """
    proc = subprocess.run(
        [restic_bin, "-r", repository, "snapshots", "--json", "--tag", tag],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise ResolverError(
            f"restic snapshots failed: {proc.stderr.strip() or proc.stdout.strip()}",
            EXIT_SNAPSHOT_JSON_FAILURE,
        )
    try:
        snaps: list[dict[str, Any]] = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise ResolverError(
            f"snapshot JSON unparsable: {exc}", EXIT_SNAPSHOT_JSON_FAILURE
        )
    return snaps


def resolve_snapshot(
    repository: str,
    *,
    expected_data_root: Path,
    required_tag: str = "convmem-data-v1",
    require_current_local_day: bool = False,
    requested_id: str | None = None,
    restic_bin: str = "restic",
    env: dict[str, str] | None = None,
) -> SnapshotRef:
    """Select and validate the correct complete-data snapshot.

    Lists all tagged snapshots as JSON without --latest, filters by exact
    normalized path, and sorts only validated candidates by timestamp.

    When requested_id is supplied, that exact full ID is validated against
    the same path/tag/freshness contract.

    Raises ResolverError with domain codes 22-26 on failure.
    """
    run_env = dict(env or os.environ)

    # Verify restic availability
    check_restic_available(restic_bin)

    expected_root = normalize_data_root(expected_data_root)

    snaps = _run_restic_snapshots(restic_bin, repository, required_tag, run_env)

    if not snaps:
        raise ResolverError(
            f"no snapshots tagged {required_tag}", EXIT_NO_TAGGED_SNAPSHOT
        )

    # Build SnapshotRef for each
    refs = [SnapshotRef.from_snapshot_json(repository, s) for s in snaps]

    if requested_id:
        # Validate the exact ID against the contract
        sid = requested_id.strip()
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
        # Validate paths
        normalize_snapshot_paths(list(ref.paths), expected_root)
        if require_current_local_day and not _is_current_local_day(ref.time):
            raise ResolverError(
                f"requested snapshot {sid[:12]} is stale (not current local day)",
                EXIT_STALE,
            )
        return ref

    # Filter by exact normalized path
    try:
        correct_path_refs = []
        for ref in refs:
            try:
                normalize_snapshot_paths(list(ref.paths), expected_root)
                correct_path_refs.append(ref)
            except ResolverError:
                continue
    except Exception:
        pass

    if not correct_path_refs:
        raise ResolverError(
            f"no {required_tag} snapshot matches data root {expected_root}",
            EXIT_WRONG_PATH,
        )

    # Sort by timestamp, newest first
    correct_path_refs.sort(key=lambda r: r.time, reverse=True)

    best = correct_path_refs[0]

    if require_current_local_day and not _is_current_local_day(best.time):
        raise ResolverError(
            "correct-path snapshot exists but is stale (not current local day)",
            EXIT_STALE,
        )

    return best


def _is_current_local_day(dt: datetime) -> bool:
    """True if dt is on or after local midnight today."""
    local_dt = dt.astimezone()
    today = datetime.now().astimezone().date()
    return local_dt.date() >= today


def resolve_copy_destination(
    destination_repository: str,
    *,
    source: SnapshotRef,
    required_tag: str = "convmem-data-v1",
    restic_bin: str = "restic",
    env: dict[str, str] | None = None,
) -> SnapshotRef:
    """Resolve the destination snapshot from a Restic copy.

    Requires exactly one destination snapshot whose JSON `original` field
    equals source.id and whose path/tag/timestamp/tree match the source.
    """
    run_env = dict(env or os.environ)
    check_restic_available(restic_bin)

    snaps = _run_restic_snapshots(restic_bin, destination_repository, required_tag, run_env)

    if not snaps:
        raise ResolverError(
            f"no {required_tag} snapshots in destination repository",
            EXIT_COPY_LINEAGE_FAILURE,
        )

    refs = [SnapshotRef.from_snapshot_json(destination_repository, s) for s in snaps]

    # Find destination(s) whose original matches source.id
    candidates = [r for r in refs if r.original == source.id]

    if not candidates:
        raise ResolverError(
            f"no destination snapshot with original={source.id[:12]}",
            EXIT_COPY_LINEAGE_FAILURE,
        )
    if len(candidates) > 1:
        raise ResolverError(
            f"ambiguous copy lineage: {len(candidates)} destinations for source {source.id[:12]}",
            EXIT_COPY_LINEAGE_FAILURE,
        )

    dest = candidates[0]

    # Verify tree, time, paths, and tag equality with source
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
    if required_tag not in dest.tags:
        raise ResolverError(
            f"destination missing required tag {required_tag}",
            EXIT_COPY_LINEAGE_FAILURE,
        )

    return dest


# ---------------------------------------------------------------------------
# CLI for shell consumers
# ---------------------------------------------------------------------------
def _cli_resolve(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="restic_snapshot.py resolve")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--password-file", required=True)
    parser.add_argument("--expected-data-root", required=True)
    parser.add_argument("--require-current-local-day", action="store_true")
    parser.add_argument("--snapshot-id", default=None)
    parser.add_argument("--restic-bin", default="restic")
    opts = parser.parse_args(args)

    env = dict(os.environ)
    env["RESTIC_PASSWORD_FILE"] = str(Path(opts.password_file).expanduser().resolve())

    try:
        ref = resolve_snapshot(
            repository=opts.repository,
            expected_data_root=Path(opts.expected_data_root),
            require_current_local_day=opts.require_current_local_day,
            requested_id=opts.snapshot_id,
            restic_bin=opts.restic_bin,
            env=env,
        )
        print(ref.to_json())
        return EXIT_OK
    except ResolverError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return exc.exit_code


def _cli_resolve_copy_destination(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="restic_snapshot.py resolve-copy-destination")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--password-file", required=True)
    parser.add_argument("--source-json", required=True)
    parser.add_argument("--restic-bin", default="restic")
    opts = parser.parse_args(args)

    env = dict(os.environ)
    env["RESTIC_PASSWORD_FILE"] = str(Path(opts.password_file).expanduser().resolve())

    try:
        source_data = json.loads(opts.source_json)
        source = SnapshotRef.from_snapshot_json(source_data.get("repository", ""), source_data)
        dest = resolve_copy_destination(
            destination_repository=opts.repository,
            source=source,
            restic_bin=opts.restic_bin,
            env=env,
        )
        print(dest.to_json())
        return EXIT_OK
    except (json.JSONDecodeError, ResolverError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if isinstance(exc, ResolverError):
            return exc.exit_code
        return EXIT_COPY_LINEAGE_FAILURE


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "usage: restic_snapshot.py <resolve|resolve-copy-destination> [...]",
            file=sys.stderr,
        )
        return EXIT_INVALID_CONFIG

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if cmd == "resolve":
        return _cli_resolve(rest)
    elif cmd == "resolve-copy-destination":
        return _cli_resolve_copy_destination(rest)
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return EXIT_INVALID_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())
