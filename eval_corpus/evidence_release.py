"""Deterministic Gate 2 evidence inventory, archive, and release receipts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import struct
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from eval_corpus.io_atomic import sha256_file
from eval_corpus.run_manifest import consume_evidence_release_auth
from eval_corpus.secure_fs import (
    FilesystemAuthorizationError,
    assert_regular_evidence_tree,
    receipt_for_path,
)

EVIDENCE_MARKER_NAME = "gate2_evidence_manifest.json"
INVENTORY_SCHEMA = "inventory_root_v1"
ARCHIVE_RECIPE_ID = "gnu_tar_gzip_v1"


def _path_key(relative: str) -> bytes:
    return relative.encode("utf-8")


def _artifact_records(root: Path, *, excluded: Iterable[str]) -> list[dict[str, Any]]:
    excluded_set = set(excluded)
    records: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if relative in excluded_set:
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise FilesystemAuthorizationError(f"evidence symlink forbidden: {path}")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise FilesystemAuthorizationError(
                f"evidence artifact must be a singly linked regular file: {path}"
            )
        records.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "size": info.st_size,
                "executable": bool(stat.S_IMODE(info.st_mode) & 0o111),
            }
        )
    return sorted(records, key=lambda item: _path_key(str(item["path"])))


def _inventory_root(records: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        path_bytes = str(record["path"]).encode("utf-8")
        digest.update(struct.pack(">I", len(path_bytes)))
        digest.update(path_bytes)
        digest.update(bytes.fromhex(str(record["sha256"])))
        digest.update(struct.pack(">Q", int(record["size"])))
        digest.update(struct.pack(">B", int(bool(record["executable"]))))
    return digest.hexdigest()


def inventory_evidence_directory(root: Path | str) -> dict[str, Any]:
    """Return the canonical inventory for a marker-not-yet-written directory."""
    evidence_root = Path(root).expanduser().absolute()
    assert_regular_evidence_tree(evidence_root)
    records = _artifact_records(evidence_root, excluded={EVIDENCE_MARKER_NAME})
    return {
        "schema_version": INVENTORY_SCHEMA,
        "inventory_root_sha256": _inventory_root(records),
        "artifacts": records,
    }


def _write_absent_bytes(path: Path, data: bytes) -> dict[str, Any]:
    """Write one absent regular file with no-follow atomic creation."""
    target = path.expanduser().absolute()
    parent = target.parent
    parent_info = parent.lstat()
    if stat.S_ISLNK(parent_info.st_mode) or not stat.S_ISDIR(parent_info.st_mode):
        raise FilesystemAuthorizationError(f"regular directory required: {parent}")
    if target.exists() or target.is_symlink():
        raise FilesystemAuthorizationError(f"output must be absent: {target}")

    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temp_name = f".{target.name}.tmp"
    temp_fd: int | None = None
    try:
        temp_fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        written = 0
        while written < len(data):
            count = os.write(temp_fd, data[written:])
            if count <= 0:
                raise FilesystemAuthorizationError(f"short write: {target}")
            written += count
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = None
        os.link(
            temp_name,
            target.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
        os.unlink(temp_name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except Exception:
        if temp_fd is not None:
            os.close(temp_fd)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    finally:
        os.close(parent_fd)
    return receipt_for_path(target, require_regular=True)


def write_gate2_marker(
    evidence_root: Path | str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Write the marker last and return its body, hash, and inventory receipt."""
    root = Path(evidence_root).expanduser().absolute()
    marker = root / EVIDENCE_MARKER_NAME
    if marker.exists() or marker.is_symlink():
        raise FilesystemAuthorizationError(f"Gate 2 marker must be absent: {marker}")
    inventory = inventory_evidence_directory(root)
    technical_status = str(fields.get("technical_status") or "")
    evidence_verdict = str(fields.get("evidence_verdict") or "")
    if technical_status not in {"VALID", "INVALID", "INCOMPLETE"}:
        raise ValueError("technical_status must be VALID, INVALID, or INCOMPLETE")
    if evidence_verdict not in {"BETTER", "WORSE", "INCONCLUSIVE", "NOT_ISSUED"}:
        raise ValueError("unsupported evidence_verdict")
    if technical_status != "VALID" and evidence_verdict != "NOT_ISSUED":
        raise ValueError("non-VALID technical status requires NOT_ISSUED")
    body = {
        **fields,
        "schema_version": "gate2_evidence_manifest_v1",
        "inventory_schema_version": inventory["schema_version"],
        "inventory_root_sha256": inventory["inventory_root_sha256"],
        "artifacts": inventory["artifacts"],
        "not_promotion_authority": True,
    }
    raw = (json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    marker_receipt = _write_absent_bytes(marker, raw)
    return {
        "body": body,
        "marker_sha256": hashlib.sha256(raw).hexdigest(),
        "marker_receipt": marker_receipt,
    }


def _tool_version(tool: str) -> str:
    result = subprocess.run([tool, "--version"], capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"cannot resolve {tool} version")
    return result.stdout.decode("utf-8", errors="replace").splitlines()[0].strip()


def create_deterministic_archive(
    evidence_root: Path | str,
    archive_path: Path | str,
) -> dict[str, Any]:
    """Create the post-marker deterministic GNU tar + gzip archive."""
    root = Path(evidence_root).expanduser().absolute()
    archive = Path(archive_path).expanduser().absolute()
    marker = root / EVIDENCE_MARKER_NAME
    if not marker.is_file() or marker.is_symlink():
        raise FilesystemAuthorizationError("archive requires a completed Gate 2 marker")
    assert_regular_evidence_tree(root)
    try:
        archive.relative_to(root)
    except ValueError:
        pass
    else:
        raise FilesystemAuthorizationError("archive must be outside evidence directory")
    if archive.exists() or archive.is_symlink():
        raise FilesystemAuthorizationError(f"archive must be absent: {archive}")
    archive.parent.lstat()
    recipe = {
        "recipe_id": ARCHIVE_RECIPE_ID,
        "tar": _tool_version("tar"),
        "gzip": _tool_version("gzip"),
        "flags": [
            "--format=pax",
            "--sort=name",
            "--mtime=@0",
            "--numeric-owner",
            "--owner=0",
            "--group=0",
            "--mode=go+u,go-w",
            "--pax-option=delete=atime,delete=ctime",
            "gzip -n -9",
        ],
    }
    with tempfile.TemporaryDirectory(prefix="gate2-archive-") as temp_dir:
        raw_tar = Path(temp_dir) / "evidence.tar"
        tar_result = subprocess.run(
            [
                "tar",
                "--format=pax",
                "--sort=name",
                "--mtime=@0",
                "--numeric-owner",
                "--owner=0",
                "--group=0",
                "--mode=go+u,go-w",
                "--pax-option=delete=atime,delete=ctime",
                "-cf",
                str(raw_tar),
                "-C",
                str(root),
                ".",
            ],
            capture_output=True,
            check=False,
        )
        if tar_result.returncode != 0:
            raise RuntimeError(tar_result.stderr.decode("utf-8", errors="replace"))
        gzip_result = subprocess.run(
            ["gzip", "-n", "-9", "-c", str(raw_tar)],
            capture_output=True,
            check=False,
        )
        if gzip_result.returncode != 0:
            raise RuntimeError(gzip_result.stderr.decode("utf-8", errors="replace"))
        archive_receipt = _write_absent_bytes(archive, gzip_result.stdout)
    return {
        "archive_path": str(archive),
        "archive_sha256": sha256_file(archive),
        "archive_receipt": archive_receipt,
        "archive_recipe": recipe,
        "archive_recipe_sha256": hashlib.sha256(
            json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def write_release_receipt(
    receipt_path: Path | str,
    *,
    marker_sha256: str,
    inventory_root_sha256: str,
    archive: dict[str, Any],
    approved_source_git_oid: str,
    run_ids: list[str],
    kiro_review: dict[str, Any],
) -> dict[str, Any]:
    """Write the external release receipt after archive creation."""
    receipt = {
        "schema_version": "gate2_release_receipt_v1",
        "marker_sha256": marker_sha256,
        "inventory_root_sha256": inventory_root_sha256,
        "archive_sha256": archive["archive_sha256"],
        "archive_recipe": archive["archive_recipe"],
        "archive_recipe_sha256": archive["archive_recipe_sha256"],
        "approved_source_git_oid": approved_source_git_oid,
        "run_ids": sorted(run_ids),
        "kiro_review": kiro_review,
        "attestation_type": "operational_review_attestation",
        "not_promotion_authority": True,
    }
    raw = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    receipt_path = Path(receipt_path).expanduser().absolute()
    _write_absent_bytes(receipt_path, raw)
    return {"receipt": receipt, "receipt_sha256": hashlib.sha256(raw).hexdigest()}


def _require_release_auth(auth: Any, operation: str) -> None:
    if getattr(auth, "operation", None) != operation:
        raise PermissionError(f"release operation requires bound {operation} authorization")


def write_authorized_gate2_marker(
    evidence_root: Path | str,
    fields: dict[str, Any],
    *,
    auth: Any,
) -> dict[str, Any]:
    """Authorized wrapper for marker construction."""
    consume_evidence_release_auth(
        auth, "evidence_assembly", {"evidence_root": evidence_root}
    )
    return write_gate2_marker(evidence_root, fields)


def create_authorized_archive(
    evidence_root: Path | str,
    archive_path: Path | str,
    *,
    auth: Any,
) -> dict[str, Any]:
    """Authorized wrapper for deterministic archive creation."""
    consume_evidence_release_auth(
        auth,
        "archive_creation",
        {"evidence_root": evidence_root, "archive_path": archive_path},
    )
    return create_deterministic_archive(evidence_root, archive_path)


def write_authorized_release_receipt(
    receipt_path: Path | str,
    *,
    auth: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Authorized wrapper for external receipt creation."""
    if not isinstance(kwargs.get("archive"), dict):
        raise PermissionError("release receipt requires an archive result object")
    archive = kwargs["archive"]
    archive_path = archive.get("archive_path")
    bound = consume_evidence_release_auth(
        auth,
        "release_receipt",
        {"archive_path": archive_path, "receipt_path": receipt_path},
    )
    archive_file = Path(str(archive_path)).expanduser().absolute()
    if not archive_file.is_file() or archive_file.is_symlink():
        raise FilesystemAuthorizationError("release receipt archive must be a regular file")
    if sha256_file(archive_file) != str(archive.get("archive_sha256") or ""):
        raise FilesystemAuthorizationError("release receipt archive hash does not match file")
    marker_file = Path(bound["evidence_root"]) / EVIDENCE_MARKER_NAME
    if not marker_file.is_file() or marker_file.is_symlink():
        raise FilesystemAuthorizationError("release receipt requires the Gate 2 marker")
    if sha256_file(marker_file) != str(kwargs.get("marker_sha256") or ""):
        raise FilesystemAuthorizationError("release receipt marker hash does not match file")
    return write_release_receipt(receipt_path, **kwargs)


__all__ = [
    "ARCHIVE_RECIPE_ID",
    "EVIDENCE_MARKER_NAME",
    "INVENTORY_SCHEMA",
    "create_authorized_archive",
    "create_deterministic_archive",
    "inventory_evidence_directory",
    "write_authorized_gate2_marker",
    "write_authorized_release_receipt",
    "write_gate2_marker",
    "write_release_receipt",
]
