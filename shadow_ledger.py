# pylint: disable=duplicate-code
"""Phase 0 shadow ledger: config resolution and activation baseline (no Chroma import).

Sink injection and append I/O land in later Execute tasks. This module must not
import chroma_store or open production Chroma.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

SHADOW_SCHEMA_VERSION = 1
MANIFEST_VERSION = 1
HASH_RULES_VERSION = 1
COLLECTION_KNOWLEDGE_UNITS = "knowledge_units"

# Strict activation contract (C1). Ledger identity header is validated here;
# secure create/append lands in later slices.
LEDGER_HEADER_RECORD_TYPE = "ledger_header"
SUPPORTED_MANIFEST_VERSION = MANIFEST_VERSION
SUPPORTED_SHADOW_SCHEMA_VERSION = SHADOW_SCHEMA_VERSION
SUPPORTED_HASH_RULES_VERSION = HASH_RULES_VERSION
ENTITY_CLASSIFICATIONS = frozenset({"active", "historical"})
ARTIFACT_FILE_MODE = 0o600
SHADOW_DIR_MODE = 0o700

DEFAULT_LEDGER_PATH = "~/.local/share/convmem/shadow_ledger.jsonl"
DEFAULT_MANIFEST_PATH = "~/.local/share/convmem/shadow_activation.json"
DEFAULT_HEALTH_PATH = "~/.local/share/convmem/shadow_health.json"

# Bounded tail reader window used by read_ledger_header_and_tail (default tail_chunk).
LEDGER_TAIL_CHUNK_BYTES = 65_536


def maximum_supported_event_bytes(
    *, tail_chunk: int = LEDGER_TAIL_CHUNK_BYTES
) -> int:
    """Maximum appendable event byte length including trailing LF.

    Derived mechanically from the tail-reader window: one expand doubles the
    initial tail_chunk, so the largest recoverable final record is
    2 * tail_chunk - 1 bytes (inclusive of the newline).
    """
    if tail_chunk <= 0:
        raise ValueError("tail_chunk must be positive")
    return 2 * tail_chunk - 1


def canonical_json_bytes(obj: Any) -> bytes:
    """UTF-8 canonical JSON: sorted keys, compact separators, reject NaN."""
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_canonical(obj: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def projection_state_hash(
    *,
    stable_entity_id: str,
    deleted: bool,
    document: str | None,
    metadata: Mapping[str, Any] | None,
) -> str:
    """Architecture state_hash over identity, delete flag, document, metadata."""
    payload = {
        "stable_entity_id": stable_entity_id,
        "deleted": bool(deleted),
        "document": document if not deleted else None,
        "metadata": dict(metadata or {}) if not deleted else None,
    }
    return sha256_canonical(payload)


def resolve_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


@dataclass(frozen=True)
class ShadowLedgerSettings:
    """Resolved optional [shadow_ledger] table (paths expanded)."""

    enabled: bool
    ledger_path: Path
    activation_manifest_path: Path
    health_path: Path
    table_present: bool

    @property
    def injection_eligible_config(self) -> bool:
        """True only when enabled=true; manifest still required separately."""
        return self.enabled is True


def shadow_ledger_section(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    if not cfg:
        return {}
    section = cfg.get("shadow_ledger")
    return dict(section) if isinstance(section, dict) else {}


def resolve_shadow_settings(cfg: Mapping[str, Any] | None) -> ShadowLedgerSettings:
    """Absent table and enabled=false are equivalent (no sink)."""
    section = shadow_ledger_section(cfg)
    present = bool(section)
    enabled = bool(section.get("enabled", False)) if present else False
    ledger = resolve_path(section.get("ledger_path", DEFAULT_LEDGER_PATH))
    manifest = resolve_path(
        section.get("activation_manifest_path", DEFAULT_MANIFEST_PATH)
    )
    health = resolve_path(section.get("health_path", DEFAULT_HEALTH_PATH))
    return ShadowLedgerSettings(
        enabled=enabled,
        ledger_path=ledger,
        activation_manifest_path=manifest,
        health_path=health,
        table_present=present,
    )


def ensure_private_file_mode(path: Path) -> None:
    """DEPRECATED for secure Shadow paths — best-effort chmod that swallows errors.

    C2+ secure create/open/health paths must use descriptor fchmod/fstat checks
    and must not call this helper. Retained only for legacy non-secure test
    helpers such as ``atomic_write_json_private`` until those callers migrate.
    """
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def atomic_write_json_private(path: Path, obj: Any) -> None:
    """Temp → fsync → replace → parent dir fsync; mode 0600."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    if not payload.endswith("\n"):
        payload += "\n"
    data = payload.encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        ensure_private_file_mode(path)
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def new_incomplete_manifest(
    *,
    code_commit: str,
    chroma_root: Path,
    configured_embed_model: str | None,
) -> dict[str, Any]:
    """Start a baseline build; completion_status incomplete cannot enable sink."""
    return {
        "manifest_version": MANIFEST_VERSION,
        "baseline_id": str(uuid.uuid4()),
        "completion_status": "incomplete",
        "activation_timestamp_utc": None,
        "code_commit": code_commit,
        "chroma_root": str(resolve_path(chroma_root)),
        "collection": COLLECTION_KNOWLEDGE_UNITS,
        "active_unit_count": None,
        "total_unit_count": None,
        "entity_baselines": {},
        "configured_embed_model": configured_embed_model,
        "observed_embed_model": "unknown",
        "observed_embed_dimensions": None,
        "shadow_ledger_identity": None,
        "starting_sequence": 0,
        "hash_rules_version": HASH_RULES_VERSION,
        "shadow_schema_version": SHADOW_SCHEMA_VERSION,
    }


def finalize_manifest(
    manifest: dict[str, Any],
    *,
    entity_baselines: Mapping[str, Mapping[str, Any]],
    active_unit_count: int,
    total_unit_count: int,
    observed_embed_model: str,
    observed_embed_dimensions: int | None,
    shadow_ledger_identity: str,
    activation_timestamp_utc: str | None = None,
) -> dict[str, Any]:
    out = dict(manifest)
    out["entity_baselines"] = {
        eid: dict(payload) for eid, payload in entity_baselines.items()
    }
    out["active_unit_count"] = int(active_unit_count)
    out["total_unit_count"] = int(total_unit_count)
    out["observed_embed_model"] = observed_embed_model or "unknown"
    out["observed_embed_dimensions"] = observed_embed_dimensions
    out["shadow_ledger_identity"] = shadow_ledger_identity
    out["activation_timestamp_utc"] = (
        activation_timestamp_utc
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    out["completion_status"] = "complete"
    return out


def load_manifest(path: Path) -> dict[str, Any] | None:
    path = Path(path)
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("activation manifest must be a JSON object")
    return data


def manifest_is_complete(manifest: Mapping[str, Any] | None) -> bool:
    if not manifest:
        return False
    if manifest.get("completion_status") != "complete":
        return False
    required = (
        "baseline_id",
        "activation_timestamp_utc",
        "code_commit",
        "chroma_root",
        "collection",
        "active_unit_count",
        "total_unit_count",
        "entity_baselines",
        "shadow_ledger_identity",
        "hash_rules_version",
        "shadow_schema_version",
    )
    return all(manifest.get(key) is not None for key in required)




def lexical_abspath(value: str | Path) -> Path:
    """Absolute path without resolving symlinks (expanduser + abspath + normpath)."""
    expanded = os.path.expanduser(str(value))
    return Path(os.path.normpath(os.path.abspath(expanded)))


def compute_aggregate_baseline_digest(
    entity_baselines: Mapping[str, Mapping[str, Any]],
) -> str:
    """SHA-256 over canonical JSON of sorted entity baseline entries."""
    ordered = {
        eid: dict(entity_baselines[eid])
        for eid in sorted(entity_baselines)
    }
    return sha256_canonical(ordered)


def manifest_body_for_canonical_hash(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Manifest fields included in manifest_canonical_hash (excludes the hash)."""
    body = {k: manifest[k] for k in sorted(manifest) if k != "manifest_canonical_hash"}
    return body


def compute_manifest_canonical_hash(manifest: Mapping[str, Any]) -> str:
    return sha256_canonical(manifest_body_for_canonical_hash(manifest))


def ledger_header_payload(
    *,
    activation_id: str,
    ledger_identity: str,
    starting_sequence: int,
    created_at_utc: str | None = None,
    shadow_schema_version: int = SHADOW_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Identity-only ledger header (no mutation payload)."""
    return {
        "record_type": LEDGER_HEADER_RECORD_TYPE,
        "shadow_schema_version": int(shadow_schema_version),
        "activation_id": str(activation_id),
        "ledger_identity": str(ledger_identity),
        "created_at_utc": created_at_utc
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "starting_sequence": int(starting_sequence),
    }


def compute_ledger_header_hash(header: Mapping[str, Any]) -> str:
    return sha256_canonical(dict(header))


def parse_complete_jsonl_line(line: str) -> dict[str, Any]:
    """Parse one complete JSONL record; reject truncated or non-object lines."""
    if not line.endswith("\n"):
        raise ValueError("incomplete jsonl line")
    raw = line[:-1]
    if not raw:
        raise ValueError("empty jsonl line")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("jsonl record must be an object")
    return data



class SecureLedgerError(Exception):
    """Base error for secure ledger create/open/append helpers."""


class SecureLedgerRefused(SecureLedgerError):
    """Existing or target ledger fails the private-artifact contract."""


@dataclass
class SecureIOHooks:  # pylint: disable=too-many-instance-attributes
    """Injectable OS seams for hermetic fault injection (tests only)."""

    open: Callable[..., int] = os.open
    close: Callable[[int], None] = os.close
    fchmod: Callable[[int, int], None] = os.fchmod
    fstat: Callable[[int], os.stat_result] = os.fstat
    fsync: Callable[[int], None] = os.fsync
    write: Callable[[int, bytes], int] = os.write
    read: Callable[[int, int], bytes] = os.read
    lseek: Callable[..., int] = os.lseek
    fstatat: Callable[..., os.stat_result] | None = None
    unlinkat: Callable[..., None] | None = None
    renameat: Callable[..., None] | None = None
    geteuid: Callable[[], int] = os.geteuid


def _hooks(hooks: SecureIOHooks | None) -> SecureIOHooks:
    # Bind os.* at call time so test monkeypatches on the os module apply.
    if hooks is not None:
        return hooks
    return SecureIOHooks(
        open=os.open,
        close=os.close,
        fchmod=os.fchmod,
        fstat=os.fstat,
        fsync=os.fsync,
        write=os.write,
        read=os.read,
        lseek=os.lseek,
        geteuid=os.geteuid,
    )


def _mode_bits(st: os.stat_result) -> int:
    return stat.S_IMODE(st.st_mode)


def _verify_private_regular(
    st: os.stat_result,
    *,
    euid: int,
    what: str,
) -> None:
    if stat.S_ISLNK(st.st_mode):
        raise SecureLedgerRefused(f"{what}: symlink refused")
    if not stat.S_ISREG(st.st_mode):
        raise SecureLedgerRefused(f"{what}: non-regular file refused")
    if st.st_uid != euid:
        raise SecureLedgerRefused(f"{what}: wrong owner uid={st.st_uid}")
    if _mode_bits(st) != ARTIFACT_FILE_MODE:
        raise SecureLedgerRefused(
            f"{what}: mode={oct(_mode_bits(st))} expected={oct(ARTIFACT_FILE_MODE)}"
        )
    if st.st_nlink != 1:
        raise SecureLedgerRefused(f"{what}: nlink={st.st_nlink} expected=1")


def _verify_private_dir(st: os.stat_result, *, euid: int, what: str) -> None:
    if stat.S_ISLNK(st.st_mode):
        raise SecureLedgerRefused(f"{what}: symlink refused")
    if not stat.S_ISDIR(st.st_mode):
        raise SecureLedgerRefused(f"{what}: not a directory")
    if st.st_uid != euid:
        raise SecureLedgerRefused(f"{what}: wrong owner uid={st.st_uid}")
    if _mode_bits(st) != SHADOW_DIR_MODE:
        raise SecureLedgerRefused(
            f"{what}: mode={oct(_mode_bits(st))} expected={oct(SHADOW_DIR_MODE)}"
        )


def open_shadow_parent_dir(
    parent: str | Path,
    *,
    hooks: SecureIOHooks | None = None,
    euid: int | None = None,
) -> int:
    """Open parent with O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC; verify 0700 + owner."""
    h = _hooks(hooks)
    uid = h.geteuid() if euid is None else int(euid)
    parent_path = lexical_abspath(parent)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        dir_fd = h.open(str(parent_path), flags)
    except OSError as exc:
        raise SecureLedgerRefused(f"parent open refused: {exc}") from exc
    try:
        st = h.fstat(dir_fd)
        _verify_private_dir(st, euid=uid, what="shadow parent")
    except Exception:
        h.close(dir_fd)
        raise
    return dir_fd


def write_all_fd(
    fd: int,
    data: bytes,
    *,
    hooks: SecureIOHooks | None = None,
) -> None:
    """Write every byte or raise; never silently truncates short writes."""
    h = _hooks(hooks)
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        written = h.write(fd, view[offset:])
        if written is None or written <= 0:
            raise OSError(errno.EIO, "short write returned no progress")
        offset += written


def create_shadow_ledger_header(
    ledger_path: str | Path,
    *,
    activation_id: str,
    ledger_identity: str,
    starting_sequence: int = 0,
    created_at_utc: str | None = None,
    hooks: SecureIOHooks | None = None,
    euid: int | None = None,
) -> dict[str, Any]:
    """Create a header-only ledger under a validated 0700 parent (C2/C5 helper).

    Security order: open parent → O_CREAT|O_EXCL|O_NOFOLLOW → fchmod/fstat →
    header bytes → file fsync → parent fsync. No mutation payload is written.
    """
    h = _hooks(hooks)
    uid = h.geteuid() if euid is None else int(euid)
    path = lexical_abspath(ledger_path)
    parent = path.parent
    name = path.name
    header = ledger_header_payload(
        activation_id=activation_id,
        ledger_identity=ledger_identity,
        starting_sequence=starting_sequence,
        created_at_utc=created_at_utc,
    )
    line = (
        json.dumps(header, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
    data = line.encode("utf-8")

    dir_fd = open_shadow_parent_dir(parent, hooks=h, euid=uid)
    fd = -1
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
        )
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = h.open(name, flags, ARTIFACT_FILE_MODE, dir_fd=dir_fd)
        except OSError as exc:
            raise SecureLedgerRefused(f"ledger create refused: {exc}") from exc

        try:
            h.fchmod(fd, ARTIFACT_FILE_MODE)
        except OSError as exc:
            raise SecureLedgerRefused(f"ledger fchmod failed: {exc}") from exc

        st = h.fstat(fd)
        _verify_private_regular(st, euid=uid, what="new ledger")

        # Identity recheck versus directory entry.
        try:
            entry_st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except TypeError:
            entry_st = os.lstat(path)
        if (entry_st.st_dev, entry_st.st_ino) != (st.st_dev, st.st_ino):
            raise SecureLedgerRefused("ledger descriptor/dirent identity mismatch")

        write_all_fd(fd, data, hooks=h)
        h.fsync(fd)
        h.fsync(dir_fd)
        return header
    finally:
        if fd >= 0:
            try:
                h.close(fd)
            except OSError:
                pass
        try:
            h.close(dir_fd)
        except OSError:
            pass


def open_existing_shadow_ledger_fd(
    ledger_path: str | Path,
    *,
    hooks: SecureIOHooks | None = None,
    euid: int | None = None,
) -> tuple[int, int, os.stat_result]:
    """Open existing ledger RDWR under private parent; return (fd, dir_fd, st).

    Refuses missing, empty, symlink, wrong owner/mode/nlink, and non-regular files.
    Caller owns both fds and must close them.
    """
    h = _hooks(hooks)
    uid = h.geteuid() if euid is None else int(euid)
    path = lexical_abspath(ledger_path)
    parent = path.parent
    name = path.name
    dir_fd = open_shadow_parent_dir(parent, hooks=h, euid=uid)
    fd = -1
    try:
        flags = os.O_RDWR | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = h.open(name, flags, dir_fd=dir_fd)
        except FileNotFoundError as exc:
            h.close(dir_fd)
            raise SecureLedgerRefused("ledger missing") from exc
        except OSError as exc:
            h.close(dir_fd)
            raise SecureLedgerRefused(f"ledger open refused: {exc}") from exc
        st = h.fstat(fd)
        _verify_private_regular(st, euid=uid, what="existing ledger")
        if st.st_size == 0:
            h.close(fd)
            h.close(dir_fd)
            raise SecureLedgerRefused("ledger empty/zero-byte")
        try:
            entry_st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except TypeError:
            entry_st = os.lstat(path)
        if (entry_st.st_dev, entry_st.st_ino) != (st.st_dev, st.st_ino):
            h.close(fd)
            h.close(dir_fd)
            raise SecureLedgerRefused("ledger descriptor/dirent identity mismatch")
        return fd, dir_fd, st
    except Exception:
        if fd >= 0:
            try:
                h.close(fd)
            except OSError:
                pass
        raise


def atomic_write_json_private_secure(
    path: str | Path,
    obj: Any,
    *,
    hooks: SecureIOHooks | None = None,
    euid: int | None = None,
) -> None:
    """Descriptor-relative private JSON replace under a 0700 parent (health)."""
    h = _hooks(hooks)
    uid = h.geteuid() if euid is None else int(euid)
    dest = lexical_abspath(path)
    parent = dest.parent
    name = dest.name
    payload = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    if not payload.endswith("\n"):
        payload += "\n"
    data = payload.encode("utf-8")
    tmp_name = f".{name}.{uuid.uuid4().hex}.tmp"

    dir_fd = open_shadow_parent_dir(parent, hooks=h, euid=uid)
    fd = -1
    try:
        # Refuse unsafe existing destination (symlink / non-regular).
        try:
            existing = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        except TypeError:
            try:
                existing = os.lstat(dest)
            except FileNotFoundError:
                existing = None
        if existing is not None:
            if stat.S_ISLNK(existing.st_mode) or not stat.S_ISREG(existing.st_mode):
                raise SecureLedgerRefused("health target unsafe type")

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = h.open(tmp_name, flags, ARTIFACT_FILE_MODE, dir_fd=dir_fd)
        h.fchmod(fd, ARTIFACT_FILE_MODE)
        st = h.fstat(fd)
        _verify_private_regular(st, euid=uid, what="health temp")
        write_all_fd(fd, data, hooks=h)
        h.fsync(fd)
        h.close(fd)
        fd = -1
        os.replace(tmp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        h.fsync(dir_fd)
    except Exception:
        if fd >= 0:
            try:
                h.close(fd)
            except OSError:
                pass
        try:
            os.unlink(tmp_name, dir_fd=dir_fd)
        except OSError:
            pass
        raise
    finally:
        try:
            h.close(dir_fd)
        except OSError:
            pass




@dataclass
class LedgerHeadTail:
    """Bounded header/tail parse result for sequence allocation."""

    header: dict[str, Any]
    last_event: dict[str, Any] | None
    next_sequence: int
    bytes_read: int
    size: int


def read_ledger_header_and_tail(
    fd: int,
    *,
    hooks: SecureIOHooks | None = None,
    max_header_bytes: int = 1_048_576,
    tail_chunk: int = 65_536,
) -> LedgerHeadTail:
    """Read only the first header record and the final complete record.

    Bytes read scale with header size + final event size, not full ledger length.
    """
    h = _hooks(hooks)
    size = h.lseek(fd, 0, os.SEEK_END)
    if size <= 0:
        raise SecureLedgerRefused("ledger empty")
    h.lseek(fd, -1, os.SEEK_END)
    if h.read(fd, 1) != b"\n":
        raise ValueError("shadow ledger truncated tail")

    bytes_read = 0
    h.lseek(fd, 0, os.SEEK_SET)
    header_buf = bytearray()
    header_raw: bytes | None = None
    while len(header_buf) < max_header_bytes:
        chunk = h.read(fd, min(4096, max_header_bytes - len(header_buf)))
        if not chunk:
            break
        header_buf.extend(chunk)
        nl = header_buf.find(b"\n")
        if nl >= 0:
            header_raw = bytes(header_buf[: nl + 1])
            bytes_read += len(header_raw)
            break
    if header_raw is None:
        raise SecureLedgerRefused("ledger headerless/incomplete")

    try:
        header = parse_complete_jsonl_line(
            header_raw.decode("utf-8")
            if header_raw.endswith(b"\n")
            else header_raw.decode("utf-8") + "\n"
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise SecureLedgerRefused(f"ledger header invalid: {exc}") from exc
    if header.get("record_type") != LEDGER_HEADER_RECORD_TYPE:
        raise SecureLedgerRefused("ledger header record_type invalid")
    if header.get("shadow_schema_version") != SHADOW_SCHEMA_VERSION:
        raise SecureLedgerRefused("ledger header schema unsupported")
    for key in ("activation_id", "ledger_identity", "created_at_utc", "starting_sequence"):
        if header.get(key) is None:
            raise SecureLedgerRefused(f"ledger header missing {key}")
    starting = header.get("starting_sequence")
    if isinstance(starting, bool) or not isinstance(starting, int) or starting < 0:
        raise SecureLedgerRefused("ledger header starting_sequence invalid")

    header_len = len(header_raw)
    if size == header_len:
        return LedgerHeadTail(
            header=header,
            last_event=None,
            next_sequence=starting + 1,
            bytes_read=bytes_read,
            size=size,
        )

    # Read a bounded window from EOF only (never the whole post-header body).
    last_line: bytes | None = None
    window = min(tail_chunk, size - header_len)
    for _attempt in range(2):  # one expand if final event exceeds first window
        h.lseek(fd, size - window, os.SEEK_SET)
        body = h.read(fd, window)
        bytes_read += len(body)
        if not body.endswith(b"\n"):
            raise ValueError("shadow ledger truncated tail")
        search = body[:-1]
        prev = search.rfind(b"\n")
        if prev >= 0:
            last_line = body[prev + 1 :]
            break
        if window >= (size - header_len):
            last_line = body
            break
        window = min(window * 2, size - header_len)
    if last_line is None:
        raise SecureLedgerRefused("ledger final record unreadable")

    try:
        last_obj = parse_complete_jsonl_line(
            last_line.decode("utf-8")
            if last_line.endswith(b"\n")
            else last_line.decode("utf-8") + "\n"
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"shadow ledger invalid tail: {exc}") from exc

    # Final record must be an event (not a second header).
    if last_obj.get("record_type") == LEDGER_HEADER_RECORD_TYPE:
        raise SecureLedgerRefused("ledger final record is header")
    seq = last_obj.get("sequence")
    if isinstance(seq, bool) or not isinstance(seq, int):
        raise ValueError("shadow ledger invalid final sequence")
    return LedgerHeadTail(
        header=header,
        last_event=last_obj,
        next_sequence=seq + 1,
        bytes_read=bytes_read,
        size=size,
    )

@dataclass(frozen=True)
class SinkInjectionDecision:
    """Whether a production write factory may attach a sink (T2+)."""

    inject: bool
    reason: str


def decide_sink_injection(
    cfg: Mapping[str, Any] | None,
    *,
    chroma_dir: str | Path,
) -> SinkInjectionDecision:
    """Gate for write-store factory. T1/T2: inject only when fully validated.

    Phase 0 Execute never sets inject=True until T2 provides a sink and Ryan
    activation has produced a complete matching manifest. This function still
    encodes the refusal reasons required by T1 gates.
    """
    settings = resolve_shadow_settings(cfg)
    if not settings.injection_eligible_config:
        return SinkInjectionDecision(
            False,
            "shadow_ledger absent or enabled=false (no sink)",
        )

    root = resolve_path(chroma_dir)
    configured_root = None
    index = (cfg or {}).get("index") if cfg else None
    if isinstance(index, dict) and index.get("chroma_dir"):
        configured_root = resolve_path(index["chroma_dir"])
    if configured_root is not None and root != configured_root:
        return SinkInjectionDecision(
            False,
            f"chroma root mismatch: store={root} config={configured_root}",
        )

    try:
        manifest = load_manifest(settings.activation_manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return SinkInjectionDecision(
            False, f"activation manifest unreadable: {exc}"
        )
    if not manifest_is_complete(manifest):
        return SinkInjectionDecision(
            False,
            "enabled=true but activation manifest missing or incomplete",
        )
    assert manifest is not None
    manifest_root = resolve_path(manifest["chroma_root"])
    if manifest_root != root:
        return SinkInjectionDecision(
            False,
            f"manifest chroma_root mismatch: store={root} manifest={manifest_root}",
        )
    # Complete matching manifest: injection *eligible* for T2 sink wiring.
    # T1 has no sink implementation — callers must still pass mutation_sink=None
    # until T2 attaches one. Report eligibility without claiming a live sink.
    return SinkInjectionDecision(
        True,
        "activation contract satisfied (sink object provided by T2 factory)",
    )


def runtime_stamp(
    *,
    code_commit: str,
    chroma_root: str | Path | None,
    active_count: int | None,
    total_count: int | None,
) -> dict[str, Any]:
    """Fresh stamp for evidence; never hardcodes audit snapshot counts."""
    return {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": code_commit,
        "chroma_root": str(resolve_path(chroma_root)) if chroma_root else None,
        "active_unit_count": active_count,
        "total_unit_count": total_count,
    }
