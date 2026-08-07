"""Operational single-use grant consumption for evidence-producing attempts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_corpus.secure_fs import FilesystemAuthorizationError, receipt_for_path

GRANT_SCHEMA = "single_use_grant_v1"
REQUIRED_FIELDS = {
    "schema_version",
    "grant_id",
    "attempt_id",
    "run_id",
    "operation",
    "manifest_body_sha256",
    "approved_paths",
    "approved_git_oid",
    "not_before",
    "expires_at",
    "max_invocations",
}
EXPECTED_BINDING_FIELDS = {
    "grant_id",
    "attempt_id",
    "run_id",
    "operation",
    "manifest_body_sha256",
    "approved_paths",
    "approved_git_oid",
}
_SAFE_GRANT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _hex(value: Any, *, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(char in "0123456789abcdef" for char in value)
    )


def _parse_time(value: Any, *, field: str) -> datetime | None:
    if value is None and field == "expires_at":
        return None
    if not isinstance(value, str) or not value:
        raise PermissionError(f"grant {field} must be a timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PermissionError(f"grant {field} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PermissionError(f"grant {field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _read_regular_json(path: Path) -> tuple[dict[str, Any], bytes, os.stat_result]:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise FilesystemAuthorizationError(f"grant must be a singly linked regular file: {path}")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        raw = b""
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            raw += chunk
        after = os.fstat(fd)
    finally:
        os.close(fd)
    identity_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in identity_fields):
        raise FilesystemAuthorizationError("grant changed while being read")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PermissionError(f"grant is not UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PermissionError("grant body must be a JSON object")
    return value, raw, before


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor or "/")
    for component in path.parts[1:]:
        current /= component
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise FilesystemAuthorizationError(f"grant path contains a symlink: {current}")


def _write_absent_json(path: Path, value: Mapping[str, Any]) -> None:
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    parent = path.parent
    info = parent.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise FilesystemAuthorizationError(f"grant receipt parent must be a directory: {parent}")
    if path.exists() or path.is_symlink():
        raise FilesystemAuthorizationError(f"grant receipt must be absent: {path}")
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temp_name = f".{path.name}.tmp"
    fd: int | None = None
    try:
        fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        os.write(fd, raw)
        os.fsync(fd)
        os.close(fd)
        fd = None
        os.link(temp_name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
        os.unlink(temp_name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except Exception:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    finally:
        os.close(parent_fd)


def consume_single_use_grant(
    grant_path: Path | str,
    expected: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Consume one exact grant and make replay fail closed.

    The grant is hard-linked into a sibling ``.consumed`` directory using an
    absent destination, then the original name is unlinked.  A pre-existing
    consumed destination therefore wins any race and prevents replay.
    """
    source = Path(grant_path).expanduser().absolute()
    _reject_symlink_components(source)
    grant, raw, source_info = _read_regular_json(source)
    if set(grant) != REQUIRED_FIELDS:
        raise PermissionError("grant fields must exactly match the v1 contract")
    if grant.get("schema_version") != GRANT_SCHEMA:
        raise PermissionError("unsupported grant schema")
    if grant.get("max_invocations") != 1:
        raise PermissionError("grant max_invocations must be 1")
    if not _hex(grant.get("manifest_body_sha256"), length=64):
        raise PermissionError("grant manifest_body_sha256 must be lowercase 64-hex")
    if not _hex(grant.get("approved_git_oid"), length=40):
        raise PermissionError("grant approved_git_oid must be a 40-hex Git object")
    if not isinstance(grant.get("approved_paths"), dict):
        raise PermissionError("grant approved_paths must be an object")
    if set(expected) != EXPECTED_BINDING_FIELDS:
        raise PermissionError(
            "expected grant identity must include exactly the full binding field set"
        )
    if not _SAFE_GRANT_ID.fullmatch(str(grant["grant_id"])):
        raise PermissionError("grant_id contains unsafe path characters")
    for field, expected_value in expected.items():
        if grant.get(field) != expected_value:
            raise PermissionError(f"grant field mismatch: {field}")

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    not_before = _parse_time(grant["not_before"], field="not_before")
    expires_at = _parse_time(grant["expires_at"], field="expires_at")
    assert not_before is not None
    if expires_at is not None and expires_at <= not_before:
        raise PermissionError("grant expires_at must be after not_before")
    if now is not None and now.tzinfo is None:
        raise PermissionError("now must be timezone-aware")
    if current < not_before:
        raise PermissionError("grant is not active yet")
    if expires_at is not None and current >= expires_at:
        raise PermissionError("grant has expired")

    consumed_dir = source.parent / ".consumed"
    if consumed_dir.exists() and consumed_dir.is_symlink():
        raise FilesystemAuthorizationError(f"consumed directory must not be a symlink: {consumed_dir}")
    if not consumed_dir.exists():
        os.mkdir(consumed_dir, mode=0o700)
    consumed_info = consumed_dir.lstat()
    if stat.S_ISLNK(consumed_info.st_mode) or not stat.S_ISDIR(consumed_info.st_mode):
        raise FilesystemAuthorizationError(f"consumed directory must be a directory: {consumed_dir}")
    grant_id = str(grant["grant_id"])
    consumed = consumed_dir / f"{grant_id}.json"
    receipt = consumed_dir / f"{grant_id}.consumed.json"
    if consumed.exists() or consumed.is_symlink() or receipt.exists() or receipt.is_symlink():
        raise PermissionError("grant was already consumed")

    parent_fd = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    consumed_fd = os.open(consumed_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    source_receipt = receipt_for_path(source, require_regular=True)
    try:
        os.link(
            source.name,
            consumed.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=consumed_fd,
            follow_symlinks=False,
        )
        os.fsync(consumed_fd)
        claimed_info = os.stat(consumed, follow_symlinks=False)
        # Linking the inode intentionally changes link count/ctime; device,
        # inode, and size are the stable claim identity.
        identity_fields = ("st_dev", "st_ino", "st_size")
        if any(
            getattr(claimed_info, field) != getattr(source_info, field)
            for field in identity_fields
        ):
            raise FilesystemAuthorizationError(
                "grant path changed between validation and atomic claim"
            )
        os.unlink(source.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        receipt_body = {
            "schema_version": "single_use_grant_consumption_v1",
            "grant_id": grant_id,
            "attempt_id": grant["attempt_id"],
            "run_id": grant["run_id"],
            "operation": grant["operation"],
            "grant_sha256": hashlib.sha256(raw).hexdigest(),
            "source_receipt": source_receipt,
            "consumed_receipt": receipt_for_path(consumed, require_regular=True),
            "consumed_at": current.isoformat().replace("+00:00", "Z"),
        }
        _write_absent_json(receipt, receipt_body)
    finally:
        os.close(consumed_fd)
        os.close(parent_fd)
    return {"grant": grant, "consumed_path": str(consumed), "receipt": receipt_body}


__all__ = ["consume_single_use_grant"]
