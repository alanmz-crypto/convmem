"""Mechanical source and interpreter identity for evidence-producing phases.

Git commit names alone do not prove the interpreter imported that revision.  This
module records the approved worktree, dependency lock, interpreter, and critical
module files, then compares a later observation against an approved receipt.
It intentionally performs no writes and never includes environment secrets.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import site
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


class SourceIdentityError(PermissionError):
    """The executing repository, import path, or dependency identity is unsafe."""


SOURCE_IDENTITY_VERSION = "source_identity_v1"
DEFAULT_CRITICAL_MODULES = (
    "eval_corpus.run_manifest",
    "eval_corpus.shadow_build",
    "eval_corpus.subprocess_compare",
    "query",
)


def sha256_file(path: Path | str) -> str:
    """Hash a regular non-symlinked file without retaining its contents.

    Python and package-manager files may intentionally be hard-linked.  The
    stricter single-link invariant belongs to mutable attempt inputs and final
    evidence artifacts, not the immutable interpreter/dependency receipt.
    """
    target = Path(path).expanduser().resolve(strict=True)
    if not target.is_file() or target.is_symlink():
        raise SourceIdentityError(f"regular non-symlinked file required: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo_root: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise SourceIdentityError(f"git {' '.join(args)} failed: {detail}")
    return proc.stdout


def _repo_root(path: Path | str) -> Path:
    candidate = Path(path).expanduser().resolve(strict=True)
    root = _git(candidate, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    if not root:
        raise SourceIdentityError(f"not a git worktree: {candidate}")
    return Path(root).resolve(strict=True)


def _tracked_status(repo_root: Path) -> tuple[list[str], list[str], list[str]]:
    """Return tracked changes, untracked files, and ignored-file inventory."""
    raw = _git(
        repo_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=matching",
    )
    tracked: list[str] = []
    untracked: list[str] = []
    ignored: list[str] = []
    for record in raw.decode("utf-8", errors="surrogateescape").split("\0"):
        if not record:
            continue
        marker, name = record[:2], record[3:]
        if marker == "??":
            untracked.append(name)
        elif marker == "!!":
            ignored.append(name)
        else:
            tracked.append(record)
    return tracked, sorted(untracked), sorted(ignored)


def _inventory_sha256(items: Iterable[str]) -> str:
    return hashlib.sha256(
        "".join(f"{item}\n" for item in sorted(items)).encode(
            "utf-8", errors="surrogateescape"
        )
    ).hexdigest()


def _tracked_tree_sha256(repo_root: Path) -> str:
    """Hash the Git index's mode/object/path tuples, exactly as tracked now."""
    return hashlib.sha256(_git(repo_root, "ls-files", "-s", "-z")).hexdigest()


def _submodule_state(repo_root: Path) -> list[str]:
    raw = _git(repo_root, "submodule", "status", "--recursive")
    return sorted(line for line in raw.decode("utf-8", errors="replace").splitlines() if line)


def _critical_module_receipts(module_names: Iterable[str]) -> list[dict[str, str]]:
    receipts: list[dict[str, str]] = []
    for name in sorted(set(module_names)):
        spec = importlib.util.find_spec(name)
        location = str(spec.origin or "") if spec is not None else ""
        if not location or location in {"built-in", "frozen"}:
            raise SourceIdentityError(f"critical module lacks a regular file: {name}")
        module_path = Path(location).resolve(strict=True)
        receipts.append(
            {
                "module": name,
                "path": str(module_path),
                "sha256": sha256_file(module_path),
            }
        )
    return receipts


def _dependency_inventory() -> list[str]:
    names = {
        f"{dist.metadata.get('Name', dist.name).lower()}=={dist.version}"
        for dist in importlib.metadata.distributions()
    }
    return sorted(names)


def canonical_identity_sha256(identity: Mapping[str, Any]) -> str:
    """Hash an identity receipt without accepting a self-hash field."""
    body = {key: value for key, value in identity.items() if key != "identity_sha256"}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def collect_source_identity(
    repo_root: Path | str,
    *,
    dependency_lock: Path | str | None = None,
    critical_modules: Iterable[str] = DEFAULT_CRITICAL_MODULES,
    require_clean_tracked: bool = True,
) -> dict[str, Any]:
    """Observe the local source/interpreter identity and reject tracked dirt.

    Untracked and ignored inventories are deliberately captured instead of
    silently discarded: later policy may reject import-shadowing files while
    retaining a reviewable receipt of benign tool caches.
    """
    root = _repo_root(repo_root)
    lock = Path(dependency_lock or root / "requirements.txt").expanduser().resolve(
        strict=True
    )
    try:
        lock.relative_to(root)
    except ValueError as exc:
        raise SourceIdentityError("dependency lock must be inside repository") from exc
    tracked, untracked, ignored = _tracked_status(root)
    if require_clean_tracked and tracked:
        raise SourceIdentityError(f"tracked worktree is dirty: {tracked[:5]}")
    python_path = Path(sys.executable).resolve(strict=True)
    identity: dict[str, Any] = {
        "schema_version": SOURCE_IDENTITY_VERSION,
        "repository_root": str(root),
        "approved_source_git_oid": _git(root, "rev-parse", "HEAD").decode("utf-8").strip(),
        "tracked_source_tree_sha256": _tracked_tree_sha256(root),
        "clean_tracked_worktree": not tracked,
        "untracked_inventory": untracked,
        "untracked_inventory_sha256": _inventory_sha256(untracked),
        "ignored_inventory": ignored,
        "ignored_inventory_sha256": _inventory_sha256(ignored),
        "submodule_status": _submodule_state(root),
        "dependency_lock_path": str(lock),
        "dependency_lock_sha256": sha256_file(lock),
        "python_executable": str(python_path),
        "python_executable_sha256": sha256_file(python_path),
        "python_version": sys.version,
        "pythonpath_present": bool(os.environ.get("PYTHONPATH")),
        "pythonpath_value": os.environ.get("PYTHONPATH", ""),
        "user_site_enabled": bool(site.ENABLE_USER_SITE),
        "critical_modules": _critical_module_receipts(critical_modules),
        "dependency_inventory": _dependency_inventory(),
    }
    identity["dependency_inventory_sha256"] = _inventory_sha256(
        identity["dependency_inventory"]
    )
    identity["identity_sha256"] = canonical_identity_sha256(identity)
    return identity


_APPROVAL_KEYS = (
    "repository_root",
    "approved_source_git_oid",
    "tracked_source_tree_sha256",
    "clean_tracked_worktree",
    "dependency_lock_sha256",
    "python_executable",
    "python_executable_sha256",
    "pythonpath_present",
    "pythonpath_value",
    "user_site_enabled",
    "critical_modules",
    "dependency_inventory_sha256",
)


def verify_source_identity(
    approved: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> None:
    """Require exact agreement with the identity fields that influence imports."""
    if approved.get("schema_version") != SOURCE_IDENTITY_VERSION:
        raise SourceIdentityError("approved source identity schema is unsupported")
    if observed.get("schema_version") != SOURCE_IDENTITY_VERSION:
        raise SourceIdentityError("observed source identity schema is unsupported")
    if not bool(observed.get("clean_tracked_worktree")):
        raise SourceIdentityError("executing worktree has tracked changes")
    for key in _APPROVAL_KEYS:
        if approved.get(key) != observed.get(key):
            raise SourceIdentityError(
                f"source identity mismatch for {key}: "
                f"approved={approved.get(key)!r} observed={observed.get(key)!r}"
            )


def verify_manifest_source_identity(
    manifest: Mapping[str, Any],
    *,
    repo_root: Path | str,
    dependency_lock: Path | str | None = None,
    critical_modules: Iterable[str] = DEFAULT_CRITICAL_MODULES,
) -> dict[str, Any]:
    """Re-observe source identity and bind it to a manifest's approved receipt."""
    approved = manifest.get("source_identity")
    if not isinstance(approved, Mapping):
        raise SourceIdentityError("manifest requires source_identity object")
    observed = collect_source_identity(
        repo_root,
        dependency_lock=dependency_lock,
        critical_modules=critical_modules,
    )
    verify_source_identity(approved, observed)
    return observed


__all__ = [
    "DEFAULT_CRITICAL_MODULES",
    "SOURCE_IDENTITY_VERSION",
    "SourceIdentityError",
    "canonical_identity_sha256",
    "collect_source_identity",
    "sha256_file",
    "verify_manifest_source_identity",
    "verify_source_identity",
]
