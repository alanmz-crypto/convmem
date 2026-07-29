# pylint: disable=duplicate-code
"""Private one-shot authorization primitives for Shadow activation.

The token file is authority supplied by the operator.  Its exact 0600 mode,
ownership, canonical request hash, bounded lifetime, and unused nonce are all
validated before activation can request the writer gate.  Nonce consumption is
append-only and fsync-durable; an uncertain write therefore fails closed.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from shadow_ledger import ARTIFACT_FILE_MODE, SHADOW_DIR_MODE, canonical_json_bytes

TOKEN_VERSION = 1
TOKEN_OPERATION = "shadow_activate"
MAX_TOKEN_LIFETIME_SECONDS = 3600
MAX_CLOCK_SKEW_SECONDS = 60
NONCE_RE = re.compile(r"^[A-Za-z0-9._-]{16,128}$")


class AuthorizationRefused(RuntimeError):
    """A mechanical authorization refusal with a stable public code."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ValidatedAuthorization:
    """Validated token material safe to retain in memory during activation."""

    payload: Mapping[str, Any]
    token_sha256: str
    nonce: str
    activation_id: str


def _utc_timestamp(value: Any, *, field: str) -> float:
    if not isinstance(value, str) or not value.strip():
        raise AuthorizationRefused("authorization_mismatch", f"{field} missing")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise AuthorizationRefused(
            "authorization_mismatch", f"{field} is not ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        raise AuthorizationRefused(
            "authorization_mismatch", f"{field} must be timezone-aware"
        )
    return parsed.timestamp()


def canonical_request_hash(payload: Mapping[str, Any]) -> str:
    """Hash a token body excluding its self-consistency field."""
    body = {key: payload[key] for key in sorted(payload) if key != "request_hash"}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _open_dir_chain(path: str | Path) -> int:
    """Open an absolute directory one component at a time without symlinks."""
    target = Path(os.path.abspath(os.path.expanduser(str(path))))
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in target.parts[1:]:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def open_directory_nofollow(path: str | Path) -> int:
    """Public descriptor-relative directory walk used by C5 config commits."""
    try:
        return _open_dir_chain(path)
    except OSError as exc:
        raise AuthorizationRefused(
            "authorization_mismatch", "directory path is missing or contains a symlink"
        ) from exc


def ensure_private_directory(path: str | Path) -> Path:
    """Create one private directory under a symlink-free existing parent."""
    target = Path(os.path.abspath(os.path.expanduser(str(path))))
    parent_fd = open_directory_nofollow(target.parent)
    created = False
    try:
        try:
            os.mkdir(target.name, SHADOW_DIR_MODE, dir_fd=parent_fd)
            created = True
        except FileExistsError:
            pass
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        child_fd = os.open(target.name, flags, dir_fd=parent_fd)
        try:
            st = os.fstat(child_fd)
            if st.st_uid != os.geteuid():
                raise AuthorizationRefused(
                    "authorization_mismatch", "private directory has wrong owner"
                )
            mode = stat.S_IMODE(st.st_mode)
            if created:
                os.fchmod(child_fd, SHADOW_DIR_MODE)
                st = os.fstat(child_fd)
                mode = stat.S_IMODE(st.st_mode)
            if mode != SHADOW_DIR_MODE:
                raise AuthorizationRefused(
                    "authorization_mismatch", "private directory mode must be 0700"
                )
            entry = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
            if (entry.st_dev, entry.st_ino) != (st.st_dev, st.st_ino):
                raise AuthorizationRefused(
                    "authorization_mismatch", "private directory identity changed"
                )
            if created:
                os.fsync(parent_fd)
        finally:
            os.close(child_fd)
    finally:
        os.close(parent_fd)
    return target


def _verify_private_file(st: os.stat_result, *, detail: str) -> None:
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise AuthorizationRefused(
            "authorization_mismatch", f"{detail} must be a single regular file"
        )
    if st.st_uid != os.geteuid():
        raise AuthorizationRefused(
            "authorization_mismatch", f"{detail} has wrong owner"
        )
    if stat.S_IMODE(st.st_mode) != ARTIFACT_FILE_MODE:
        raise AuthorizationRefused(
            "authorization_mismatch", f"{detail} mode must be 0600"
        )


def _read_private_file(path: str | Path, *, missing_code: str) -> bytes:
    target = Path(os.path.abspath(os.path.expanduser(str(path))))
    try:
        parent_fd = open_directory_nofollow(target.parent)
    except AuthorizationRefused as exc:
        if not target.parent.exists():
            raise AuthorizationRefused(missing_code, "authorization path missing") from exc
        raise
    try:
        flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(target.name, flags, dir_fd=parent_fd)
        except FileNotFoundError as exc:
            raise AuthorizationRefused(missing_code, "authorization file missing") from exc
        except OSError as exc:
            raise AuthorizationRefused(
                "authorization_mismatch", "authorization file open refused"
            ) from exc
        try:
            st = os.fstat(fd)
            _verify_private_file(st, detail="authorization file")
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            entry = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
            if (entry.st_dev, entry.st_ino) != (st.st_dev, st.st_ino):
                raise AuthorizationRefused(
                    "authorization_mismatch", "authorization file identity changed"
                )
            return b"".join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def _decode_token(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthorizationRefused(
            "authorization_mismatch", "authorization JSON is invalid"
        ) from exc
    if not isinstance(payload, dict):
        raise AuthorizationRefused(
            "authorization_mismatch", "authorization token must be an object"
        )
    return payload


def load_authorization_payload(token_path: str | Path) -> dict[str, Any]:
    """Read a private token for routing; authority is granted only by validate."""
    raw = _read_private_file(token_path, missing_code="authorization_missing")
    return _decode_token(raw)


def load_private_json(path: str | Path) -> dict[str, Any]:
    """Load any current-user 0600 single-link JSON object without symlinks."""
    return _decode_token(
        _read_private_file(path, missing_code="authorization_missing")
    )


def validate_authorization_token(
    token_path: str | Path,
    *,
    expected: Mapping[str, Any],
    nonce_store: "NonceStore",
    now: datetime | None = None,
) -> ValidatedAuthorization:
    """Validate exact token bindings and confirm the nonce remains unused."""
    raw = _read_private_file(token_path, missing_code="authorization_missing")
    payload = _decode_token(raw)
    required = {
        "token_version",
        "operation",
        "activation_id",
        "nonce",
        "issued_at_utc",
        "expires_at_utc",
        "code_revision",
        "config_path",
        "shadow_dir",
        "ledger_path",
        "manifest_path",
        "health_path",
        "first_event_timeout_seconds",
        "quiesce_timeout_seconds",
        "allowed_filesystems",
        "baseline_derivation",
        "manifest_derivation",
        "target_config",
        "nonce_store_path",
        "writer_lock_path",
        "census_path",
        "request_hash",
    }
    if set(payload) != required:
        raise AuthorizationRefused(
            "authorization_mismatch", "authorization fields are not the exact schema"
        )
    if payload["token_version"] != TOKEN_VERSION or payload["operation"] != TOKEN_OPERATION:
        raise AuthorizationRefused(
            "authorization_mismatch", "authorization version or operation mismatch"
        )
    declared_hash = payload.get("request_hash")
    if not isinstance(declared_hash, str) or declared_hash != canonical_request_hash(payload):
        raise AuthorizationRefused(
            "authorization_mismatch", "request_hash self-consistency failed"
        )
    for key, value in expected.items():
        if payload.get(key) != value:
            raise AuthorizationRefused(
                "authorization_mismatch", f"authorization binding mismatch: {key}"
            )

    nonce = payload.get("nonce")
    activation_id = payload.get("activation_id")
    if not isinstance(nonce, str) or not NONCE_RE.fullmatch(nonce):
        raise AuthorizationRefused("authorization_mismatch", "nonce format invalid")
    if not isinstance(activation_id, str) or not activation_id.strip():
        raise AuthorizationRefused(
            "authorization_mismatch", "activation_id format invalid"
        )

    issued = _utc_timestamp(payload.get("issued_at_utc"), field="issued_at_utc")
    expires = _utc_timestamp(payload.get("expires_at_utc"), field="expires_at_utc")
    if expires <= issued or expires - issued > MAX_TOKEN_LIFETIME_SECONDS:
        raise AuthorizationRefused(
            "authorization_mismatch", "authorization lifetime exceeds 3600 seconds"
        )
    current = (now or datetime.now(timezone.utc)).timestamp()
    if issued - current > MAX_CLOCK_SKEW_SECONDS:
        raise AuthorizationRefused(
            "authorization_mismatch", "authorization issued in the future"
        )
    if current >= expires:
        raise AuthorizationRefused("authorization_expired", "authorization expired")
    if nonce_store.contains(nonce):
        raise AuthorizationRefused("authorization_reused", "authorization nonce reused")
    return ValidatedAuthorization(
        payload=payload,
        token_sha256=hashlib.sha256(raw).hexdigest(),
        nonce=nonce,
        activation_id=activation_id,
    )


class NonceStore:
    """Private, locked JSONL append store for consumed activation nonces."""

    def __init__(
        self,
        path: str | Path,
        *,
        fsync: Callable[[int], None] = os.fsync,
        write: Callable[[int, bytes], int] = os.write,
    ) -> None:
        self.path = Path(os.path.abspath(os.path.expanduser(str(path))))
        self._fsync = fsync
        self._write = write

    def _open_locked(self) -> tuple[int, int, bool]:
        parent_fd = open_directory_nofollow(self.path.parent)
        flags = os.O_RDWR | os.O_APPEND | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        created = False
        fd = -1
        try:
            try:
                fd = os.open(self.path.name, flags, dir_fd=parent_fd)
            except FileNotFoundError:
                fd = os.open(
                    self.path.name,
                    flags | os.O_CREAT | os.O_EXCL,
                    ARTIFACT_FILE_MODE,
                    dir_fd=parent_fd,
                )
                created = True
                os.fchmod(fd, ARTIFACT_FILE_MODE)
            st = os.fstat(fd)
            _verify_private_file(st, detail="nonce store")
            entry = os.stat(self.path.name, dir_fd=parent_fd, follow_symlinks=False)
            if (entry.st_dev, entry.st_ino) != (st.st_dev, st.st_ino):
                raise AuthorizationRefused(
                    "authorization_mismatch", "nonce store identity changed"
                )
            fcntl.flock(fd, fcntl.LOCK_EX)
            if created:
                self._fsync(parent_fd)
            return fd, parent_fd, created
        except Exception:
            if fd >= 0:
                os.close(fd)
            os.close(parent_fd)
            raise

    @staticmethod
    def _records(fd: int) -> list[dict[str, Any]]:
        os.lseek(fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        if raw and not raw.endswith(b"\n"):
            raise AuthorizationRefused(
                "authorization_mismatch", "nonce store has a truncated record"
            )
        records: list[dict[str, Any]] = []
        for line in raw.splitlines():
            try:
                value = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise AuthorizationRefused(
                    "authorization_mismatch", "nonce store record is corrupt"
                ) from exc
            if not isinstance(value, dict) or not isinstance(value.get("nonce"), str):
                raise AuthorizationRefused(
                    "authorization_mismatch", "nonce store record shape invalid"
                )
            records.append(value)
        return records

    def contains(self, nonce: str) -> bool:
        if not os.path.lexists(self.path):
            return False
        try:
            fd, parent_fd, _created = self._open_locked()
        except OSError as exc:
            raise AuthorizationRefused(
                "authorization_mismatch", "nonce store open refused"
            ) from exc
        try:
            return any(row["nonce"] == nonce for row in self._records(fd))
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            os.close(parent_fd)

    def consume(
        self,
        *,
        nonce: str,
        activation_id: str,
        token_sha256: str,
        consumed_at_utc: str | None = None,
    ) -> None:
        try:
            fd, parent_fd, _created = self._open_locked()
        except OSError as exc:
            raise AuthorizationRefused(
                "authorization_mismatch", "nonce store open refused"
            ) from exc
        try:
            if any(row["nonce"] == nonce for row in self._records(fd)):
                raise AuthorizationRefused(
                    "authorization_reused", "authorization nonce reused"
                )
            record = {
                "activation_id": activation_id,
                "consumed_at_utc": consumed_at_utc
                or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "nonce": nonce,
                "token_sha256": token_sha256,
            }
            data = canonical_json_bytes(record) + b"\n"
            view = memoryview(data)
            offset = 0
            while offset < len(view):
                written = self._write(fd, view[offset:])
                if written is None or written <= 0:
                    raise OSError("nonce store short write")
                offset += written
            self._fsync(fd)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            os.close(parent_fd)


def secure_atomic_write_json(
    path: str | Path,
    payload: Mapping[str, Any],
    *,
    replace_existing: bool = True,
) -> os.stat_result:
    """Atomically publish one 0600 JSON object under an existing 0700 parent."""
    target = Path(os.path.abspath(os.path.expanduser(str(path))))
    parent_fd = open_directory_nofollow(target.parent)
    parent_st = os.fstat(parent_fd)
    if (
        parent_st.st_uid != os.geteuid()
        or stat.S_IMODE(parent_st.st_mode) != SHADOW_DIR_MODE
    ):
        os.close(parent_fd)
        raise AuthorizationRefused(
            "authorization_mismatch", "private artifact parent must be owned 0700"
        )
    temp_name = f".{target.name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
    fd = -1
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(temp_name, flags, ARTIFACT_FILE_MODE, dir_fd=parent_fd)
        os.fchmod(fd, ARTIFACT_FILE_MODE)
        _verify_private_file(os.fstat(fd), detail="private temporary file")
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            written = os.write(fd, view[offset:])
            if written <= 0:
                raise OSError("private JSON short write")
            offset += written
        os.fsync(fd)
        os.close(fd)
        fd = -1
        if replace_existing:
            os.replace(
                temp_name,
                target.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        else:
            os.link(
                temp_name,
                target.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
            os.unlink(temp_name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        temp_name = ""
        result = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
        _verify_private_file(result, detail="private JSON file")
        return result
    except Exception:
        try:
            if temp_name:
                os.unlink(temp_name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(parent_fd)
