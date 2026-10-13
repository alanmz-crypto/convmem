# pylint: disable=too-many-lines
"""Contain native Chroma write crashes so they cannot corrupt the shared HNSW index.

chromadb 1.5.9 saves each collection's HNSW segment in place, from inside ordinary
``upsert``/``update``/``delete`` calls, roughly every ``sync_threshold`` records, and
then purges its write-ahead log up to that save.  Reproduced on scratch stores
(Arc Poison Pill, Part B, 2026-09-24):

1. A process that dies during a save leaves the on-disk segment torn.
2. Restoring the *last* save and letting Chroma replay its own log loses nothing.
3. Restoring an *older* save silently drops every record between the two saves.
4. A writer whose in-process Chroma system loaded the index before another process
   saved overwrites that newer save on its own next save.

Cases 3 and 4 pass structural validation, so they have to be prevented rather than
detected.  :class:`ChromaWriteGuard` keeps four invariants around each production
native write:

* one native write at a time across processes (exclusive ``flock``);
* a writer whose in-process system predates the on-disk save reloads it first, and
  the write is refused when that reload is impossible;
* every segment has a validated copy of its last save, refreshed after each save;
* a live segment that fails validation is replaced by that copy before anyone
  writes -- and only then, because restoring over a valid segment is case 3.

SQLite needs none of this: its rollback journal already makes each transaction
atomic across a crash.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import stat
import pickle
import shutil
import sqlite3
import struct
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

import numpy as np

SEGMENT_FILES = (
    "header.bin",
    "data_level0.bin",
    "length.bin",
    "link_lists.bin",
    "index_metadata.pickle",
)
HEADER_BYTES = 100
DEFAULT_LOCK_TIMEOUT_SECONDS = 120.0
AUDIT_LOCK_TIMEOUT_SECONDS = 60.0
GUARD_DIR_SUFFIX = ".write-guard"
INCIDENT_SCHEMA = "convmem.safe_harbor.incident_set"
INCIDENT_VERSION = 2
PRESERVATION_MANIFEST_SCHEMA = "convmem.safe_harbor.preservation_manifest"
PRESERVATION_MANIFEST_VERSION = 1
_SUPPORTED_INCIDENT_VERSIONS = frozenset({1, 2})
_SUPPORTED_CHROMADB_VERSIONS = frozenset({"1.5.9"})
_RESTORE_REQUIRED_REASON = "segment failed validation; bounded restore required before further writes"
LEGACY_BYTES_NAME = "QUARANTINE.legacy-bytes"
_ADMISSION_BARRIER_ENV = "CONVMEM_GUARD_ADMISSION_BARRIER"
_LOCK_HOLD_BARRIER_ENV = "CONVMEM_GUARD_LOCK_BARRIER"
_GUARD_STATE_NAMES = frozenset(
    {
        "QUARANTINE.json",
        LEGACY_BYTES_NAME,
        "events.jsonl",
        "audit.json",
        "native-write.lock",
    }
)
_DELETE_MARK = 0x10000
_MAX_LEVELS = 64
_ROWS_PER_CHUNK = 8192

Signature = list[list[Any]]


class ChromaWriteGuardError(RuntimeError):
    """A production Chroma write was refused to protect the shared index."""


class ChromaWriteQuarantinedError(ChromaWriteGuardError):
    """Writes stay stopped until a human repairs the index and clears the quarantine."""


class ChromaStaleSystemError(ChromaWriteGuardError):
    """This process holds a Chroma system older than the on-disk save and cannot reload it."""


class ChromaContainmentUnavailableError(ChromaWriteGuardError):
    """Incident publication failed; no durable stop was established."""


class ChromaReleaseUncertaintyError(ChromaWriteGuardError):
    """Release disposition may be durable but quarantine marker state is uncertain."""


class ReleaseEvidenceCaptureUnavailable(ChromaWriteGuardError):
    """Snapshot-time SQL state cannot yet form strict release evidence (expected before first persist)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _unavailable_release_evidence(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "reason": reason}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------------------
# Structural validation (read-only)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SegmentReport:
    """Structural verdict for one HNSW segment directory."""

    segment: str
    ok: bool
    failures: tuple[str, ...]
    notes: tuple[str, ...]


class _NoGlobalsUnpickler(pickle.Unpickler):
    """Chroma's id map is plain dicts, ints and strings; any class reference is refused."""

    def find_class(self, module: str, name: str) -> Any:
        raise pickle.UnpicklingError(f"refusing pickle global {module}.{name}")


def load_segment_id_map(seg_dir: Path) -> dict[str, Any] | None:
    """Read ``index_metadata.pickle`` without executing any pickled code."""
    path = seg_dir / "index_metadata.pickle"
    if not path.exists():
        return None
    with path.open("rb") as fh:
        data = _NoGlobalsUnpickler(fh).load()
    if not isinstance(data, dict):
        raise pickle.UnpicklingError("index_metadata.pickle does not hold a dict")
    return data


def _read_header(path: Path) -> dict[str, int]:
    """Chroma's persistent hnswlib header: a 4-byte prefix, then hnswlib's fields."""
    raw = path.read_bytes()
    if len(raw) != HEADER_BYTES:
        raise ValueError(f"header.bin is {len(raw)} bytes, expected {HEADER_BYTES}")

    def u64(offset: int) -> int:
        return int(struct.unpack_from("<Q", raw, offset)[0])

    return {
        "max_elements": u64(12),
        "count": u64(20),
        "bytes_per_element": u64(28),
        "label_offset": u64(36),
        "offset_data": u64(44),
        "max_level": int(struct.unpack_from("<i", raw, 52)[0]),
        "entry_point": int(struct.unpack_from("<I", raw, 56)[0]),
        "max_m": u64(60),
        "max_m0": u64(68),
    }


def _header_failures(header: dict[str, int]) -> list[str]:
    failures: list[str] = []
    links0 = header["max_m0"] * 4 + 4
    if not (0 < header["max_m"] <= 4096 and 0 < header["max_m0"] <= 4096):
        failures.append(f"implausible M/maxM0 {header['max_m']}/{header['max_m0']}")
    if header["offset_data"] != links0:
        failures.append("offset_data does not follow the level-0 link block")
    vector_bytes = header["label_offset"] - links0
    if vector_bytes <= 0 or vector_bytes % 4 or header["label_offset"] % 4:
        failures.append("vector block size is not a positive multiple of 4")
    if header["bytes_per_element"] != header["label_offset"] + 8:
        failures.append("bytes per element does not equal label offset + 8")
    if header["count"] > header["max_elements"]:
        failures.append(f"element count {header['count']} exceeds capacity {header['max_elements']}")
    if header["count"]:
        if header["entry_point"] >= header["count"]:
            failures.append(f"entry point {header['entry_point']} >= element count {header['count']}")
        if not 0 <= header["max_level"] < _MAX_LEVELS:
            failures.append(f"implausible max level {header['max_level']}")
    return failures


def _level0_failures(seg_dir: Path, header: dict[str, int]) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Walk level 0 in chunks: link counts, neighbour ids, finite vectors, unique labels."""
    count = header["count"]
    path = seg_dir / "data_level0.bin"
    size = path.stat().st_size
    empty = np.empty(0, dtype=np.uint64)
    if count == 0:
        # Created but never synced: Chroma writes the file pre-sized to capacity.
        allowed = {0, header["max_elements"] * header["bytes_per_element"]}
        if size not in allowed:
            return [f"data_level0.bin is {size} bytes for an unsynced index"], empty, np.empty(0, dtype=bool)
        return [], empty, np.empty(0, dtype=bool)
    expected = count * header["bytes_per_element"]
    if size != expected:
        return [f"data_level0.bin is {size} bytes, expected {expected}"], empty, np.empty(0, dtype=bool)
    width = header["bytes_per_element"] // 4
    max_m0 = header["max_m0"]
    first_vec, label_col = header["offset_data"] // 4, header["label_offset"] // 4
    rows = np.memmap(path, dtype="<u4", mode="r", shape=(count, width))
    labels = np.empty(count, dtype=np.uint64)
    deleted = np.empty(count, dtype=bool)
    over = bad_nbr = nonfinite = 0
    slot = np.arange(max_m0)[None, :]
    for start in range(0, count, _ROWS_PER_CHUNK):
        chunk = np.ascontiguousarray(rows[start:start + _ROWS_PER_CHUNK])
        head = chunk[:, 0]
        links = head & 0xFFFF
        deleted[start:start + len(chunk)] = (head & _DELETE_MARK) != 0
        over += int((links > max_m0).sum())
        used = slot < np.minimum(links, max_m0)[:, None]
        bad_nbr += int(((chunk[:, 1:1 + max_m0] >= count) & used).any(axis=1).sum())
        vectors = chunk[:, first_vec:label_col].view("<f4")
        nonfinite += int((~np.isfinite(vectors)).any(axis=1).sum())
        labels[start:start + len(chunk)] = chunk[:, label_col].astype(np.uint64) | (
            chunk[:, label_col + 1].astype(np.uint64) << np.uint64(32)
        )
    del rows
    failures: list[str] = []
    if over:
        failures.append(f"{over} element(s) with a level-0 link count above maxM0")
    if bad_nbr:
        failures.append(f"{bad_nbr} element(s) with out-of-range level-0 neighbours")
    if nonfinite:
        failures.append(f"{nonfinite} element(s) with non-finite vector values")
    duplicates = labels.size - np.unique(labels).size
    if duplicates:
        failures.append(f"{duplicates} duplicate label(s)")
    return failures, labels, deleted


def _link_list_failures(seg_dir: Path, header: dict[str, int]) -> tuple[list[str], int]:
    """Walk link_lists.bin element by element; it must land exactly on EOF."""
    count, max_m, max_level = header["count"], header["max_m"], header["max_level"]
    data = np.fromfile(seg_dir / "link_lists.bin", dtype=np.uint8)
    block = max_m * 4 + 4
    slot = np.arange(max_m)[None, :]
    offset = higher = entry_levels = 0
    for element in range(count):
        if offset + 4 > data.size:
            return [f"link_lists.bin ends inside element {element}'s size field"], higher
        size = int(struct.unpack_from("<I", data, offset)[0])
        offset += 4
        if element == header["entry_point"]:
            entry_levels = size // block
        if not size:
            continue
        higher += 1
        if size % block or size // block > max(max_level, 0):
            return [f"element {element}: upper link list of {size} bytes is not 1..maxlevel blocks"], higher
        if offset + size > data.size:
            return [f"element {element}: upper link list runs past EOF"], higher
        blocks = data[offset:offset + size].view("<u4").reshape(-1, max_m + 1)
        links = blocks[:, 0] & 0xFFFF
        if (links > max_m).any() or ((blocks[:, 1:] >= count) & (slot < links[:, None])).any():
            return [f"element {element}: upper-level link count or neighbour out of range"], higher
        offset += size
    failures: list[str] = []
    if offset != data.size:
        failures.append(f"link_lists.bin walk ends at byte {offset}, file has {data.size}")
    if count and entry_levels != max(max_level, 0):
        failures.append(f"entry point has {entry_levels} upper levels, header says {max_level}")
    return failures, higher


def _id_map_failures(seg_dir: Path, labels: np.ndarray, deleted: np.ndarray) -> tuple[list[str], list[str]]:
    """The id map must name exactly the segment's non-deleted element labels."""
    try:
        id_map = load_segment_id_map(seg_dir)
    except (pickle.UnpicklingError, EOFError, ValueError, TypeError, AttributeError) as exc:
        return [f"index_metadata.pickle unreadable: {exc}"], []
    if id_map is None:
        return [], ["index_metadata.pickle absent (segment not yet fully synced)"]
    id_to_label = id_map.get("id_to_label")
    if not isinstance(id_to_label, dict):
        return ["index_metadata.pickle has no id_to_label map"], []
    failures: list[str] = []
    live = labels[~deleted] if labels.size else labels
    if len(id_to_label) != live.size:
        failures.append(f"id map has {len(id_to_label)} ids, segment has {live.size} live elements")
    else:
        mapped = np.fromiter(id_to_label.values(), dtype=np.uint64, count=len(id_to_label))
        if not np.array_equal(np.sort(mapped), np.sort(live)):
            failures.append("id map labels differ from the segment's live element labels")
    label_to_id = id_map.get("label_to_id")
    if isinstance(label_to_id, dict) and len(label_to_id) != len(id_to_label):
        failures.append("label_to_id and id_to_label differ in size")
    return failures, [f"id_map={len(id_to_label)}"]


def validate_segment(seg_dir: str | Path) -> SegmentReport:
    """Structurally validate one HNSW segment directory (read-only).

    Extends the Arc Poison Pill section 4.2 validator: header consistency, level-0
    link counts and neighbour ranges, finite vectors and norms, unique labels, an
    exact link_lists.bin walk including upper-level neighbours, and id-map/label
    agreement.  Torn saves fail it; silently lost records (cases 3 and 4 in the
    module docstring) do not -- see :func:`vector_census` for those.
    """
    seg = Path(seg_dir)
    try:
        header = _read_header(seg / "header.bin")
    except (OSError, ValueError, struct.error) as exc:
        return SegmentReport(seg.name, False, (f"header.bin unreadable: {exc}",), ())
    failures = _header_failures(header)
    notes = [
        (
            f"elements={header['count']} capacity={header['max_elements']} "
            f"M={header['max_m']} maxM0={header['max_m0']} bytes/element={header['bytes_per_element']}"
        )
    ]
    if failures:
        return SegmentReport(seg.name, False, tuple(failures), tuple(notes))
    try:
        level0, labels, deleted = _level0_failures(seg, header)
        failures.extend(level0)
        notes.append(f"deleted={int(deleted.sum())}")
        norms = seg / "length.bin"
        if norms.exists():
            allowed = {header["count"] * 4} if header["count"] else {0, header["max_elements"] * 4}
            if norms.stat().st_size not in allowed:
                failures.append(f"length.bin is {norms.stat().st_size} bytes, expected {header['count'] * 4}")
            elif header["count"] and not np.isfinite(np.fromfile(norms, dtype="<f4")).all():
                failures.append("length.bin holds non-finite vector norms")
        links, higher = _link_list_failures(seg, header)
        failures.extend(links)
        notes.append(f"elements_with_upper_levels={higher}")
        if not level0:
            id_failures, id_notes = _id_map_failures(seg, labels, deleted)
            failures.extend(id_failures)
            notes.extend(id_notes)
    except OSError as exc:
        failures.append(f"segment file unreadable: {exc}")
    return SegmentReport(seg.name, not failures, tuple(failures), tuple(notes))


def segment_dirs(chroma_dir: str | Path) -> dict[str, Path]:
    """HNSW segment directories holding any saved file.

    A directory whose first save was torn before ``header.bin`` appeared is included
    on purpose, so it fails validation instead of being skipped.
    """
    root = Path(chroma_dir)
    try:
        entries = sorted(root.iterdir())
    except FileNotFoundError:
        return {}
    return {
        entry.name: entry
        for entry in entries
        if entry.is_dir() and any((entry / name).is_file() for name in SEGMENT_FILES)
    }


def _header_count(seg_dir: Path) -> int | None:
    try:
        raw = (seg_dir / "header.bin").read_bytes()
    except OSError:
        return None
    return int(struct.unpack_from("<Q", raw, 20)[0]) if len(raw) == HEADER_BYTES else None


def segment_signature(seg_dir: Path) -> Signature:
    """Identity of a segment's saved state; any Chroma save or restore changes it.

    A segment Chroma created but never synced (header count 0) is identified by its
    file sizes alone: each new client that loads it rewrites those files unchanged,
    which must not look like another process's save.
    """
    files: Signature = []
    for name in SEGMENT_FILES:
        try:
            st = (seg_dir / name).stat()
        except FileNotFoundError:
            continue
        files.append([name, st.st_size, st.st_mtime_ns, st.st_ino])
    if files and _header_count(seg_dir) == 0:
        return [["unsynced"]] + [[name, size] for name, size, _mtime, _ino in files]
    return files


def store_signature(chroma_dir: str | Path) -> dict[str, Signature]:
    return {seg_id: segment_signature(seg) for seg_id, seg in segment_dirs(chroma_dir).items()}


# --------------------------------------------------------------------------------------
# Silent-loss census (read-only)
# --------------------------------------------------------------------------------------


def _seq_id(value: Any) -> int:
    if isinstance(value, bytes):  # chromadb < 0.5 stored seq ids as big-endian blobs
        return int.from_bytes(value, "big")
    return int(value or 0)


def _seq_id_strict(value: Any) -> int:
    if value is None or isinstance(value, bool):
        raise ValueError("invalid seq_id")
    if isinstance(value, bytes):
        if not value:
            raise ValueError("empty seq_id bytes")
        return int.from_bytes(value, "big")
    if isinstance(value, int):
        return int(value)
    raise TypeError(f"unsupported seq_id type {type(value)!r}")


def vector_census(chroma_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Per collection: metadata rows whose vector is neither in the HNSW nor pending.

    ``lost`` counts records Chroma still lists but can no longer return by vector --
    the silent loss that structural validation cannot see.  Opens SQLite read-only
    and never constructs a Chroma client.
    """
    root = Path(chroma_dir)
    database = root / "chroma.sqlite3"
    if not database.is_file():
        raise FileNotFoundError(f"no Chroma database at {database}")
    con = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        applied = {sid: _seq_id(seq) for sid, seq in con.execute("select segment_id, seq_id from max_seq_id")}
        result: dict[str, dict[str, Any]] = {}
        for collection_id, name in con.execute("select id, name from collections").fetchall():
            scopes = dict(
                con.execute("select scope, id from segments where collection = ?", (collection_id,)).fetchall()
            )
            meta_seg, vec_seg = scopes.get("METADATA"), scopes.get("VECTOR")
            metadata_ids = {
                row[0] for row in con.execute("select embedding_id from embeddings where segment_id = ?", (meta_seg,))
            }
            floor = min(applied.get(meta_seg, 0), applied.get(vec_seg, 0))
            pending = {
                row[0]
                for row in con.execute(
                    "select id from embeddings_queue where topic like ? and seq_id > ?",
                    (f"%/{collection_id}", floor),
                )
            }
            id_map = load_segment_id_map(root / str(vec_seg)) if vec_seg else None
            hnsw_ids = set((id_map or {}).get("id_to_label") or {})
            lost = metadata_ids - hnsw_ids - pending
            extra = hnsw_ids - metadata_ids - pending
            result[name] = {
                "vector_segment": vec_seg,
                "metadata_rows": len(metadata_ids),
                "hnsw_ids": len(hnsw_ids),
                "pending": len(pending),
                "lost": len(lost),
                "extra": len(extra),
                "lost_sample": sorted(lost)[:5],
            }
        return result
    finally:
        con.close()


# --------------------------------------------------------------------------------------
# Safe Harbor T3 — release evidence (client-free), preservation, validated release
# --------------------------------------------------------------------------------------


def segment_file_digests(seg_dir: Path) -> dict[str, str]:
    """Content hashes for every present segment file (no inode/mtime)."""
    out: dict[str, str] = {}
    for name in SEGMENT_FILES:
        path = seg_dir / name
        if path.is_file():
            out[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def sqlite_schema_digest(chroma_dir: Path) -> str:
    database = Path(chroma_dir) / "chroma.sqlite3"
    con = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        con.execute("BEGIN")
        rows = con.execute(
            "select type, name, sql from sqlite_master where name not like 'sqlite_%' order by type, name"
        ).fetchall()
    finally:
        con.execute("ROLLBACK")
        con.close()
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def live_backend_identity(chroma_dir: str | Path) -> dict[str, Any]:
    """Installed backend/schema identity without opening a Chroma client."""
    root = Path(chroma_dir)
    import importlib.metadata

    import chromadb
    from chromadb.api.client import Client
    from chromadb.config import Settings

    from chromadb_rust_bindings import chromadb_rust_bindings as native_binding

    rust_path = Path(native_binding.__file__).resolve()
    if not rust_path.is_file():
        raise FileNotFoundError(f"missing rust binding at {rust_path}")
    settings = Settings()
    con = sqlite3.connect(f"file:{root / 'chroma.sqlite3'}?mode=ro", uri=True)
    try:
        con.execute("BEGIN")
        migrations = tuple(row[0] for row in con.execute("select version from migrations order by version"))
    finally:
        con.execute("ROLLBACK")
        con.close()
    identity = {
        "chromadb_version": chromadb.__version__,
        "client_api": f"{Client.__module__}.{Client.__qualname__}",
        "chroma_api_impl": str(getattr(settings, "chroma_api_impl", None)),
        "rust_binding_sha256": hashlib.sha256(rust_path.read_bytes()).hexdigest(),
        "sqlite_migrations": migrations,
        "sqlite_schema_digest": sqlite_schema_digest(root),
        "hnswlib": importlib.metadata.version("hnswlib"),
    }
    _assert_supported_backend_identity(identity)
    return identity


def _collection_segments_sql(con: sqlite3.Connection, collection: str) -> tuple[str, str, str]:
    row = con.execute("select id, name from collections where name = ?", (collection,)).fetchone()
    if not row:
        raise KeyError(f"collection {collection!r} missing")
    collection_id, _ = row
    scopes = dict(con.execute("select scope, id from segments where collection = ?", (collection_id,)).fetchall())
    meta_seg = scopes.get("METADATA")
    vec_seg = scopes.get("VECTOR")
    if not meta_seg or not vec_seg:
        raise KeyError(f"collection {collection!r} missing METADATA/VECTOR segments")
    return collection_id, meta_seg, vec_seg


def _sqlite_reader_lock(con: sqlite3.Connection) -> None:
    """Establish a read lock without nesting BEGIN on an active transaction."""
    if con.in_transaction:
        con.execute("SELECT 1")
        return
    con.execute("BEGIN")


def build_release_evidence_for_collection(
    chroma_dir: str | Path,
    collection_name: str,
    *,
    segment_dir: Path | None = None,
    con: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Capture strict empty-changed-set inputs (read-only SQLite; optional pinned segment dir)."""
    root = Path(chroma_dir)
    owned = con is None
    if owned:
        con = sqlite3.connect(f"file:{root / 'chroma.sqlite3'}?mode=ro", uri=True)
    try:
        _sqlite_reader_lock(con)
        collection_id, meta_seg, vec_seg = _collection_segments_sql(con, collection_name)
        applied = {sid: _seq_id_strict(raw) for sid, raw in con.execute("select segment_id, seq_id from max_seq_id")}
        if vec_seg not in applied:
            raise ReleaseEvidenceCaptureUnavailable("vector_watermark_not_persisted")
        vector_watermark = applied[vec_seg]
        if vector_watermark <= 0:
            raise ReleaseEvidenceCaptureUnavailable("vector_watermark_not_positive")
        meta_wm = applied.get(meta_seg) if meta_seg in applied else None
        vec_dir = segment_dir if segment_dir is not None else root / str(vec_seg)
        if segment_dir is not None:
            guard_root = root.parent / f"{root.name}{GUARD_DIR_SUFFIX}"
            _assert_path_under_root(vec_dir, guard_root, "snapshot staging")
        else:
            _assert_live_segment_dir(vec_dir, root)
        if not vec_dir.is_dir():
            raise FileNotFoundError(f"vector segment directory missing: {vec_dir}")
        for name in SEGMENT_FILES:
            path = vec_dir / name
            if path.exists():
                _reject_symlink_path(path)
                _assert_regular_segment_file(path)
        digests = segment_file_digests(vec_dir)
        backend = _backend_identity_for_storage(live_backend_identity(root))
        return {
            "collection_name": collection_name,
            "collection_id": collection_id,
            "metadata_segment_id": meta_seg,
            "vector_segment_id": vec_seg,
            "vector_watermark": vector_watermark,
            "metadata_watermark": meta_wm,
            "segment_digests": digests,
            "backend_identity": backend,
        }
    finally:
        if owned:
            if con.in_transaction:
                con.execute("ROLLBACK")
            con.close()


def _normalize_backend_identity(identity: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(identity)
    migrations = out.get("sqlite_migrations")
    if isinstance(migrations, (list, tuple)):
        out["sqlite_migrations"] = tuple(int(item) for item in migrations)
    return out


def _backend_identity_for_storage(identity: Mapping[str, Any]) -> dict[str, Any]:
    out = _normalize_backend_identity(identity)
    out["sqlite_migrations"] = list(out.get("sqlite_migrations") or ())
    return out


def _assert_supported_backend_identity(identity: Mapping[str, Any]) -> None:
    version = identity.get("chromadb_version")
    if version not in _SUPPORTED_CHROMADB_VERSIONS:
        raise ChromaWriteGuardError(f"unsupported chromadb backend {version!r} for release evidence")


def authority_submission_digest(document: Mapping[str, Any]) -> str:
    """Digest of the full current unresolved authority (incidents, findings, repair state)."""
    incidents_out: list[dict[str, Any]] = []
    for incident in document.get("incidents") or []:
        if not isinstance(incident, dict):
            raise ChromaWriteGuardError("invalid incident set for authority digest")
        findings_out = []
        for finding in incident.get("findings") or []:
            if not isinstance(finding, dict):
                raise ChromaWriteGuardError("invalid finding set for authority digest")
            findings_out.append(
                {
                    "id": finding.get("id"),
                    "revision": finding.get("revision"),
                    "digest": finding.get("digest"),
                    "kind": finding.get("kind"),
                    "reason": finding.get("reason"),
                }
            )
        findings_out.sort(key=lambda item: str(item.get("id")))
        incidents_out.append(
            {
                "id": incident.get("id"),
                "segment": incident.get("segment"),
                "occurrence": incident.get("occurrence"),
                "findings": findings_out,
                "preservation": incident.get("preservation"),
                "pinned_source": incident.get("pinned_source"),
                "repair": incident.get("repair"),
            }
        )
    incidents_out.sort(key=lambda item: str(item.get("id")))
    payload = {
        "schema": INCIDENT_SCHEMA,
        "version": document.get("version"),
        "target": document.get("target"),
        "incidents": incidents_out,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _reject_symlink_path(path: Path) -> None:
    cursor = path
    while True:
        if cursor.is_symlink():
            raise ChromaWriteGuardError(f"refusing symlink path component {cursor}")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent


def _assert_path_under_root(path: Path, root: Path, label: str) -> Path:
    _reject_symlink_path(path)
    _reject_symlink_path(root)
    resolved = path.expanduser().resolve(strict=False)
    root_resolved = root.expanduser().resolve(strict=False)
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ChromaWriteGuardError(f"refusing {label} path outside root {resolved}")
    return resolved


def _assert_guard_relative_path(path: Path, root: Path) -> Path:
    return _assert_path_under_root(path, root, "guard")


def _assert_live_segment_dir(seg_dir: Path, chroma_dir: Path) -> Path:
    return _assert_path_under_root(seg_dir, chroma_dir, "live segment")


def _new_occurrence_epoch() -> str:
    return f"occ_{time.time_ns()}-{os.getpid()}"


def _coerce_occurrence(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    epoch = value.get("epoch")
    if not isinstance(epoch, str) or not epoch or "/" in epoch or ".." in epoch:
        return None
    return {"epoch": epoch}


def _assert_regular_segment_file(path: Path) -> None:
    if path.is_symlink():
        raise ChromaWriteGuardError(f"refusing symlink segment file {path}")
    if path.exists() and not path.is_file():
        raise ChromaWriteGuardError(f"refusing non-regular segment file {path}")


def _reject_unsafe_directory_entry(entry: Path) -> None:
    _reject_symlink_path(entry)
    if entry.is_symlink():
        if not entry.exists():
            raise ChromaWriteGuardError(f"refusing dangling symlink {entry}")
        raise ChromaWriteGuardError(f"refusing symlink entry {entry}")
    try:
        mode = entry.lstat().st_mode
    except OSError as exc:
        raise ChromaWriteGuardError(f"refusing unreadable segment entry {entry}: {exc}") from exc
    if stat.S_ISSOCK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
        raise ChromaWriteGuardError(f"unsupported segment entry {entry.name}")


def _source_facts_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if set(left.keys()) != set(right.keys()):
        return False
    for name in left:
        if left[name] != right[name]:
            return False
    return True


def _preservation_original_facts(incident: Mapping[str, Any]) -> dict[str, Any] | None:
    preservation = incident.get("preservation")
    if not isinstance(preservation, dict):
        return None
    recorded = preservation.get("original_facts")
    if not isinstance(recorded, dict):
        return None
    return recorded


def _release_identity_mismatch(live: Mapping[str, Any], saved: Mapping[str, Any]) -> str:
    for key in (
        "sqlite_schema_digest",
        "chromadb_version",
        "chroma_api_impl",
        "rust_binding_sha256",
        "client_api",
        "hnswlib",
    ):
        if live.get(key) != saved.get(key):
            return f"{key}_mismatch"
    if tuple(live.get("sqlite_migrations") or ()) != tuple(saved.get("sqlite_migrations") or ()):
        return "sqlite_migrations_mismatch"
    return "backend_identity_mismatch"


def _release_evidence_admission_status(evidence: Mapping[str, Any]) -> tuple[bool, str]:
    if not evidence:
        return False, "missing_release_evidence"
    if evidence.get("status") == "unavailable":
        reason = str(evidence.get("reason") or "unknown")
        return False, f"release_evidence_unavailable:{reason}"
    return True, ""


def _evaluate_release_saved_watermark(evidence: Mapping[str, Any]) -> tuple[int | None, str]:
    try:
        saved_wm = _seq_id_strict(evidence.get("vector_watermark"))
    except (TypeError, ValueError):
        return None, "missing_vector_watermark"
    if saved_wm <= 0:
        return None, "missing_vector_watermark"
    return saved_wm, ""


def _evaluate_release_backend_identity(root: Path, evidence: Mapping[str, Any]) -> tuple[bool, str]:
    try:
        live_identity = _normalize_backend_identity(live_backend_identity(root))
        _assert_supported_backend_identity(live_identity)
    except ChromaWriteGuardError as exc:
        return False, f"unsupported_backend {exc}"
    except (OSError, ImportError, FileNotFoundError) as exc:
        return False, f"backend_identity_unavailable {exc}"
    saved_identity = evidence.get("backend_identity")
    if not isinstance(saved_identity, dict):
        return False, "missing_backend_identity"
    saved_identity = _normalize_backend_identity(saved_identity)
    try:
        _assert_supported_backend_identity(saved_identity)
    except ChromaWriteGuardError as exc:
        return False, f"unsupported_saved_backend {exc}"
    if live_identity != saved_identity:
        reason = _release_identity_mismatch(live_identity, saved_identity)
        return False, reason if reason != "backend_identity_mismatch" else "backend_identity_mismatch"
    return True, ""


def _evaluate_release_sql_watermarks(
    evidence: Mapping[str, Any],
    saved_wm: int,
    *,
    con: sqlite3.Connection,
) -> tuple[bool, str]:
    collection_name = evidence.get("collection_name")
    if not isinstance(collection_name, str) or not collection_name:
        return False, "missing_collection_name"
    row = con.execute("select id, name from collections where name = ?", (collection_name,)).fetchone()
    if not row:
        return False, "collection_missing"
    collection_id, _ = row
    if collection_id != evidence.get("collection_id"):
        return False, "collection_id_mismatch"
    scopes = dict(con.execute("select scope, id from segments where collection = ?", (collection_id,)).fetchall())
    meta_seg, vec_seg = scopes.get("METADATA"), scopes.get("VECTOR")
    if meta_seg != evidence.get("metadata_segment_id") or vec_seg != evidence.get("vector_segment_id"):
        return False, "segment_identity_mismatch"
    applied = {sid: _seq_id_strict(raw) for sid, raw in con.execute("select segment_id, seq_id from max_seq_id")}
    if vec_seg not in applied:
        return False, "sequence_evidence_missing"
    meta_wm = applied.get(meta_seg)
    if meta_wm is None:
        return False, "sequence_evidence_missing"
    vec_wm = applied[vec_seg]
    if meta_wm != saved_wm or vec_wm != saved_wm:
        return False, f"watermark_drift meta={meta_wm} vec={vec_wm} saved={saved_wm}"
    pending = con.execute(
        "select count(*) from embeddings_queue where topic like ? and seq_id > ?",
        (f"%/{collection_id}", saved_wm),
    ).fetchone()[0]
    if pending:
        return False, f"queue_pending={pending}"
    return True, ""


def _evaluate_release_live_segment(
    root: Path, evidence: Mapping[str, Any], collection_name: str
) -> tuple[bool, str]:
    vec_seg_id = str(evidence.get("vector_segment_id") or "")
    vec_dir = root / vec_seg_id
    if not vec_dir.is_dir():
        return False, "vector_segment_missing"
    saved_digests = evidence.get("segment_digests")
    if not isinstance(saved_digests, dict):
        return False, "missing_segment_digests"
    if segment_file_digests(vec_dir) != saved_digests:
        return False, "segment_digest_mismatch"
    report = validate_segment(vec_dir)
    if not report.ok:
        return False, f"structural_invalid {list(report.failures)}"
    try:
        census_all = vector_census(root)
    except (FileNotFoundError, sqlite3.Error, OSError) as exc:
        return False, f"census_unavailable {exc}"
    row = census_all.get(collection_name)
    if row is None:
        return False, "census_missing"
    if row.get("lost") or row.get("extra"):
        return False, f"census_mismatch {row}"
    return True, ""


def evaluate_release_evidence(
    chroma_dir: str | Path,
    evidence: Mapping[str, Any],
    *,
    con: sqlite3.Connection | None = None,
) -> tuple[bool, str]:
    """Strict empty-changed-set release oracle (no Chroma client)."""
    root = Path(chroma_dir)
    ok, reason = _release_evidence_admission_status(evidence)
    if not ok:
        return False, reason
    saved_wm, reason = _evaluate_release_saved_watermark(evidence)
    if saved_wm is None:
        return False, reason
    ok, reason = _evaluate_release_backend_identity(root, evidence)
    if not ok:
        return False, reason
    collection_name = evidence.get("collection_name")
    if not isinstance(collection_name, str) or not collection_name:
        return False, "missing_collection_name"
    owned = con is None
    if owned:
        con = sqlite3.connect(f"file:{root / 'chroma.sqlite3'}?mode=ro", uri=True)
    try:
        _sqlite_reader_lock(con)
        ok, reason = _evaluate_release_sql_watermarks(evidence, saved_wm, con=con)
        if not ok:
            return False, reason
    finally:
        if owned and con is not None:
            if con.in_transaction:
                con.execute("ROLLBACK")
            con.close()
    return _evaluate_release_live_segment(root, evidence, collection_name)


def _manifest_digest_payload(manifest: Mapping[str, Any]) -> str:
    body = {key: value for key, value in manifest.items() if key != "manifest_digest"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _safe_preservation_name(name: str) -> bool:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        return False
    return name in SEGMENT_FILES or name == "MANIFEST.json"


# --------------------------------------------------------------------------------------
# Process-level view of what each in-process Chroma system has loaded
# --------------------------------------------------------------------------------------

_VIEWS_LOCK = threading.Lock()
_SYSTEM_VIEWS: dict[str, dict[str, Signature]] = {}


def canonical_target(path: str | Path) -> Path:
    """Absolute symlink-resolved identity of a Chroma store directory."""
    return Path(path).expanduser().resolve(strict=False)


def _view_key(identifier: str | Path) -> str:
    """Cache identity for the guard's record of what a system has loaded."""
    return str(canonical_target(identifier))


def chroma_system_cached(identifier: str) -> bool:
    """True when this process already holds a Chroma system for ``identifier``.

    Chroma keys that table by the exact path string given to PersistentClient.
    Store construction passes the canonical target, and the guard's load record
    uses that same target (see ``_view_key``).
    """
    from chromadb.api.shared_system_client import SharedSystemClient

    return identifier in SharedSystemClient._identifier_to_system  # pylint: disable=protected-access


def note_system_created(identifier: str) -> None:
    """Record the on-disk saves a Chroma system about to be created will load.

    Call *before* constructing the client: Chroma loads segments lazily, so the
    system can only be newer than this record, never older. The record is stored
    under the canonical target so path aliases share one guard view.
    """
    key = _view_key(identifier)
    with _VIEWS_LOCK:
        _SYSTEM_VIEWS[key] = store_signature(key)


def note_unguarded_write(identifier: str, before: dict[str, Signature]) -> None:
    """After a native write this process made without the guard.

    If the write saved, this process's system produced the files on disk, so it is
    not stale. If it did not save, leave the recorded view alone: any save another
    process made earlier is still unseen.
    """
    key = _view_key(identifier)
    after = store_signature(key)
    if after != before:
        _set_system_view(key, after)


def _synced_only(view: dict[str, Signature] | None) -> dict[str, Signature] | None:
    """The part of a view that can make a system stale.

    Chroma purges its log only when a segment syncs, so a system that loaded before an
    *unsynced* change still replays every record from the log. Only a changed synced
    segment means records were saved and purged where this system cannot see them.
    """
    if view is None:
        return None
    return {seg: sig for seg, sig in view.items() if not (sig and sig[0] == ["unsynced"])}


def _system_view(identifier: str) -> dict[str, Signature] | None:
    with _VIEWS_LOCK:
        return _SYSTEM_VIEWS.get(identifier)


def _set_system_view(identifier: str, view: dict[str, Signature] | None) -> None:
    with _VIEWS_LOCK:
        if view is None:
            _SYSTEM_VIEWS.pop(identifier, None)
        else:
            _SYSTEM_VIEWS[identifier] = view


# --------------------------------------------------------------------------------------
# Durable file helpers and the cross-process lock
# --------------------------------------------------------------------------------------


def _fsync(path: Path, *, directory: bool = False) -> None:
    fd = os.open(path, os.O_RDONLY | (os.O_DIRECTORY if directory else 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_directory_chain(path: Path, *, stop: Path) -> None:
    """Fsync each directory from path up through stop (inclusive)."""
    start = path
    if not start.exists():
        start = start.parent
    current = start.resolve(strict=False)
    stop_resolved = stop.resolve(strict=False)
    while True:
        if not current.is_dir():
            raise OSError(f"cannot durably link non-directory {current}")
        _fsync(current, directory=True)
        if current in (stop_resolved, current.parent):
            break
        current = current.parent


def _copy_durable(src: Path, dst: Path) -> None:
    shutil.copyfile(src, dst)
    _fsync(dst)


def _write_json_durable(path: Path, data: Mapping[str, Any]) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _fsync(tmp)
    os.replace(tmp, path)
    _fsync(path.parent, directory=True)


_LOCK_STATE = threading.local()
_EVENT_APPEND_LOCK = threading.Lock()
_RELEASE_SUPPORTED_FINDING_KINDS = frozenset({"structural", "segment_restored", "lost_vectors", "legacy"})


@contextmanager
def _exclusive_flock(path: Path, timeout_seconds: float) -> Iterator[None]:
    """Exclusive cross-process lock, re-entrant within one thread."""
    held: dict[str, int] = getattr(_LOCK_STATE, "held", None) or {}
    _LOCK_STATE.held = held
    key = str(path)
    if held.get(key):
        held[key] += 1
        try:
            yield
        finally:
            held[key] -= 1
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(key, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    try:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"chroma native-write lock still busy after {timeout_seconds:g}s: {key}"
                    ) from exc
                time.sleep(0.01)
        held[key] = 1
        try:
            yield
        finally:
            held.pop(key, None)
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# --------------------------------------------------------------------------------------
# Incident authority (QUARANTINE.json)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthorityView:
    """Read-only interpretation of the quarantine marker. Never a reason to rewrite it."""

    state: str
    blocking: bool
    summary: str
    incidents: tuple[dict[str, Any], ...]
    document: dict[str, Any] | None
    error: str | None
    legacy: bool


def _same_location(left: Path, right: Path) -> bool:
    return left.expanduser().resolve(strict=False) == right.expanduser().resolve(strict=False)


def _guard_location_occupied(path: Path) -> bool:
    if not path.exists():
        return False
    if not path.is_dir():
        return True
    try:
        children = list(path.iterdir())
    except OSError:
        return True
    return any(child.name in _GUARD_STATE_NAMES or child.name == "snapshots" for child in children)


def _containment_text(exc: BaseException) -> str:
    return (
        "containment unavailable: durable incident publication failed "
        f"({exc}). Request owner process-level containment; this is not a durable stop."
    )


def _wait_barrier(spec: str) -> None:
    """Block until another process releases a ready/release file pair.

    The specification is ``ready_path:release_path``. It only orders tests.
    It does not skip quarantine or admit a write.
    """
    ready_s, sep, release_s = spec.partition(":")
    if sep != ":" or not ready_s or not release_s:
        raise ChromaWriteGuardError("invalid guard barrier specification")
    ready = Path(ready_s)
    ready.parent.mkdir(parents=True, exist_ok=True)
    ready.write_text("ready", encoding="utf-8")
    release = Path(release_s)
    while not release.is_file():
        time.sleep(0.01)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json_object(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    parsed = json.loads(encoded)
    if not isinstance(parsed, dict):
        raise ChromaWriteGuardError("incident detail must be a JSON object")
    return parsed


def _finding_digest(kind: str, reason: str, failures: list[str], detail: Mapping[str, Any] | None) -> str:
    payload = {"detail": _json_object(detail), "failures": list(failures), "kind": kind, "reason": reason}
    return _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _finding_id(segment: str, kind: str, reason: str) -> str:
    return "find_" + _sha256_text(f"{segment}\0{kind}\0{reason}")[:24]


def _incident_id(target: str, segment: str) -> str:
    return "inc_" + _sha256_text(f"{target}\0{segment}")[:24]


def _finding_spec(
    segment: str,
    kind: str,
    reason: str,
    failures: tuple[str, ...] | list[str],
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    failure_list = [str(item) for item in failures]
    return {
        "segment": segment,
        "kind": kind,
        "reason": reason,
        "failures": failure_list,
        "detail": _json_object(detail),
    }


def _empty_incident_document(target: str) -> dict[str, Any]:
    return {"schema": INCIDENT_SCHEMA, "version": INCIDENT_VERSION, "target": target, "incidents": []}


def _sort_incidents(document: dict[str, Any]) -> None:
    document["incidents"].sort(key=lambda item: item["id"])
    for incident in document["incidents"]:
        incident["findings"].sort(key=lambda item: item["id"])


def _summary(incidents: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> str:
    parts = [
        f"{incident['segment']}: {finding['reason']}"
        for incident in incidents
        for finding in incident["findings"]
    ]
    if not parts:
        return "unresolved quarantine"
    shown = "; ".join(parts[:4])
    extra = len(parts) - 4
    if extra > 0:
        shown += f"; +{extra} more"
    return shown


def _blocked(summary: str) -> AuthorityView:
    return AuthorityView("blocked", True, summary, (), None, summary, False)


def _absent() -> AuthorityView:
    return AuthorityView("absent", False, "no quarantine marker", (), None, None, False)


def _is_recognized_legacy(parsed: Mapping[str, Any]) -> bool:
    if any(key in parsed for key in ("schema", "version", "incidents")):
        return False
    if not isinstance(parsed.get("segment"), str) or not parsed.get("segment"):
        return False
    if not isinstance(parsed.get("reason"), str) or not parsed.get("reason"):
        return False
    failures = parsed.get("failures", [])
    return isinstance(failures, list) and all(isinstance(item, str) for item in failures)


def _legacy_spec(parsed: Mapping[str, Any]) -> dict[str, Any]:
    extra = {key: value for key, value in parsed.items() if key not in {"segment", "reason", "failures"}}
    detail = {"legacy": extra} if extra else {}
    return _finding_spec(
        str(parsed["segment"]),
        "legacy",
        str(parsed["reason"]),
        list(parsed.get("failures") or []),
        detail,
    )


def _coerce_finding(finding: Any) -> dict[str, Any] | None:
    if not isinstance(finding, dict):
        return None
    finding_id = finding.get("id")
    kind = finding.get("kind")
    reason = finding.get("reason")
    revision = finding.get("revision")
    digest = finding.get("digest")
    failures = finding.get("failures")
    observed_at = finding.get("observed_at")
    if not all(isinstance(item, str) and item for item in (finding_id, kind, reason, observed_at)):
        return None
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        return None
    if not isinstance(digest, str) or len(digest) != 64:
        return None
    if not isinstance(failures, list) or not all(isinstance(item, str) for item in failures):
        return None
    detail = finding.get("detail", {})
    if not isinstance(detail, dict):
        return None
    if digest != _finding_digest(kind, reason, list(failures), detail):
        return None
    if finding_id != _finding_id(str(finding.get("segment") or ""), kind, reason) and "segment" in finding:
        return None
    return {
        "id": finding_id,
        "kind": kind,
        "reason": reason,
        "failures": list(failures),
        "detail": detail,
        "revision": revision,
        "digest": digest,
        "observed_at": observed_at,
    }


def _coerce_incident(incident: Any, target: str) -> dict[str, Any] | None:
    if not isinstance(incident, dict):
        return None
    incident_id = incident.get("id")
    segment = incident.get("segment")
    findings = incident.get("findings")
    if not isinstance(incident_id, str) or not isinstance(segment, str) or not isinstance(findings, list):
        return None
    if incident_id != _incident_id(target, segment) or not findings:
        return None
    coerced: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in findings:
        if isinstance(item, dict):
            item = {**item, "segment": segment}
        finding = _coerce_finding(item)
        if finding is None or finding["id"] in seen:
            return None
        if finding["id"] != _finding_id(segment, finding["kind"], finding["reason"]):
            return None
        seen.add(finding["id"])
        coerced.append(finding)
    out: dict[str, Any] = {"id": incident_id, "segment": segment, "findings": coerced}
    occurrence = _coerce_occurrence(incident.get("occurrence"))
    if incident.get("occurrence") is not None and occurrence is None:
        return None
    if occurrence is not None:
        out["occurrence"] = occurrence
    for optional in ("preservation", "repair", "pinned_source"):
        extra = incident.get(optional)
        if extra is not None:
            if not isinstance(extra, dict):
                return None
            out[optional] = copy.deepcopy(extra)
    return out


def _interpret_current(parsed: Mapping[str, Any], expected_target: str) -> AuthorityView:
    version = parsed.get("version")
    if version not in _SUPPORTED_INCIDENT_VERSIONS:
        return _blocked("unknown incident schema version")
    target = parsed.get("target")
    if not isinstance(target, str) or target != expected_target:
        return _blocked(f"quarantine target {target!r} does not match canonical target {expected_target}")
    raw_incidents = parsed.get("incidents")
    if not isinstance(raw_incidents, list):
        return _blocked("invalid incident set")
    incidents: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_incidents:
        coerced = _coerce_incident(item, expected_target)
        if coerced is None or coerced["id"] in seen:
            return _blocked("invalid incident set")
        seen.add(coerced["id"])
        incidents.append(coerced)
    document: dict[str, Any] = {
        "schema": INCIDENT_SCHEMA,
        "version": max(int(version), INCIDENT_VERSION),
        "target": expected_target,
        "incidents": incidents,
    }
    legacy_hash = parsed.get("legacy_original_sha256")
    if isinstance(legacy_hash, str):
        document["legacy_original_sha256"] = legacy_hash
    # A present marker is never a release. An empty incident list is still
    # unresolved: only a missing file admits writers. The document stays
    # recognizable so a later finding can be merged into it.
    summary = _summary(incidents) if incidents else "persisted empty incident set refuses admission"
    return AuthorityView("unresolved", True, summary, tuple(incidents), document, None, False)


def _document_from_legacy(parsed: Mapping[str, Any], target: str, raw: bytes) -> dict[str, Any]:
    document = _empty_incident_document(target)
    document["legacy_original_sha256"] = hashlib.sha256(raw).hexdigest()
    _upsert_finding(document, _legacy_spec(parsed))
    return document


def _interpret_marker(raw: bytes, expected_target: str) -> AuthorityView:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _blocked(f"unreadable quarantine record: {exc}")
    if parsed is None or not isinstance(parsed, dict):
        return _blocked("quarantine marker is not an object")
    if not parsed:
        return _blocked("quarantine marker is empty")
    if parsed.get("schema") == INCIDENT_SCHEMA:
        return _interpret_current(parsed, expected_target)
    if _is_recognized_legacy(parsed):
        document = _document_from_legacy(parsed, expected_target, raw)
        return AuthorityView(
            "unresolved",
            True,
            _summary(document["incidents"]),
            tuple(document["incidents"]),
            None,
            None,
            True,
        )
    return _blocked("unrecognized quarantine marker")


def _upsert_finding(document: dict[str, Any], spec: Mapping[str, Any]) -> bool:
    """Insert or revise one finding. Return whether the unresolved set changed."""
    segment = str(spec["segment"])
    kind = str(spec["kind"])
    reason = str(spec["reason"])
    failures = [str(item) for item in spec["failures"]]
    detail = _json_object(spec.get("detail") if isinstance(spec.get("detail"), Mapping) else {})
    digest = _finding_digest(kind, reason, failures, detail)
    finding_id = _finding_id(segment, kind, reason)
    incident_id = _incident_id(str(document["target"]), segment)
    incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
    if incident is None:
        incident = {
            "id": incident_id,
            "segment": segment,
            "findings": [],
            "occurrence": {"epoch": _new_occurrence_epoch()},
        }
        document["incidents"].append(incident)
    elif not isinstance(incident.get("occurrence"), dict) or not incident["occurrence"].get("epoch"):
        incident["occurrence"] = {"epoch": _new_occurrence_epoch()}
    current = next((item for item in incident["findings"] if item["id"] == finding_id), None)
    if current is None:
        incident["findings"].append(
            {
                "id": finding_id,
                "kind": kind,
                "reason": reason,
                "failures": failures,
                "detail": detail,
                "revision": 1,
                "digest": digest,
                "observed_at": _utc_now(),
            }
        )
        _sort_incidents(document)
        return True
    if current["digest"] == digest:
        return False
    current.update(
        kind=kind,
        reason=reason,
        failures=failures,
        detail=detail,
        digest=digest,
        revision=int(current["revision"]) + 1,
        observed_at=_utc_now(),
    )
    _sort_incidents(document)
    return True


def _collect_reports(chroma_dir: Path) -> tuple[list[SegmentReport], BaseException | None]:
    try:
        return [validate_segment(seg) for seg in segment_dirs(chroma_dir).values()], None
    except OSError as exc:
        return [], exc


def _collect_census(chroma_dir: Path) -> tuple[dict[str, dict[str, Any]] | None, BaseException | None]:
    try:
        return vector_census(chroma_dir), None
    except (sqlite3.Error, OSError, pickle.UnpicklingError, EOFError) as exc:
        return None, exc


def _audit_findings(
    reports: list[SegmentReport],
    report_error: BaseException | None,
    census: dict[str, dict[str, Any]] | None,
    census_error: BaseException | None,
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    if report_error is None:
        for report in reports:
            if report.ok:
                continue
            specs.append(
                _finding_spec(report.segment, "structural", "segment failed structural validation", report.failures)
            )
    if census_error is None and census is not None:
        for name, row in census.items():
            if int(row.get("lost") or 0) <= 0:
                continue
            segment = str(row.get("vector_segment") or name)
            specs.append(
                _finding_spec(
                    segment,
                    "lost_vectors",
                    "records without vectors",
                    (),
                    {
                        "collection": name,
                        "lost": int(row["lost"]),
                        "lost_sample": list(row.get("lost_sample") or []),
                    },
                )
            )
    return specs


def _fill_audit_result(
    result: dict[str, Any],
    gathered: Mapping[str, Any],
    specs: list[dict[str, Any]],
    publication_error: BaseException | None,
) -> None:
    reports: list[SegmentReport] = gathered["reports"]
    report_error: BaseException | None = gathered["report_error"]
    census: dict[str, dict[str, Any]] | None = gathered["census"]
    census_error: BaseException | None = gathered["census_error"]
    if isinstance(publication_error, ChromaContainmentUnavailableError):
        result.update(status="error", reason=str(publication_error), containment="unavailable")
        return
    if publication_error is not None:
        result.update(status="error", reason=str(publication_error))
        return
    invalid = [report for report in reports if not report.ok] if report_error is None else []
    lost = None if census is None else sum(int(row["lost"]) for row in census.values())
    vectors = None if census is None else sum(int(row["hnsw_ids"]) for row in census.values())
    if specs:
        result.update(
            status="fail",
            segments=len(reports),
            invalid_segments={report.segment: list(report.failures)[:5] for report in invalid},
            lost=lost,
            vectors=vectors,
            census=census,
        )
        if census_error is not None:
            result["census_error"] = f"{type(census_error).__name__}: {census_error}"
        return
    if report_error is not None or census_error is not None:
        err = report_error or census_error
        result.update(status="error", reason=f"{type(err).__name__}: {err}")
        return
    result.update(
        status="pass",
        segments=len(reports),
        invalid_segments={},
        lost=lost,
        vectors=vectors,
        census=census,
    )


# --------------------------------------------------------------------------------------
# The guard
# --------------------------------------------------------------------------------------


class ChromaWriteGuard:  # pylint: disable=too-many-instance-attributes
    """Keeps a validated copy of each segment's last save and serialises native writes.

    State lives beside the canonical store in ``<chroma_dir>.write-guard/``: the lock
    file, ``snapshots/<segment>/`` (the copies), ``events.jsonl`` and ``QUARANTINE.json``.
    ``QUARANTINE.json`` is the only admission authority. ``audit.json`` is the latest
    observation and cannot release writers.
    """

    def __init__(
        self,
        chroma_dir: str | Path,
        *,
        lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        requested = Path(chroma_dir).expanduser()
        self.chroma_dir = canonical_target(requested)
        self.root = self.chroma_dir.parent / f"{self.chroma_dir.name}{GUARD_DIR_SUFFIX}"
        lexical_root = requested.parent / f"{requested.name}{GUARD_DIR_SUFFIX}"
        self.identity_conflict: tuple[str, str] | None = None
        if not _same_location(lexical_root, self.root) and _guard_location_occupied(lexical_root):
            self.identity_conflict = (str(lexical_root), str(self.root))
        self.lock_path = self.root / "native-write.lock"
        self.snapshots = self.root / "snapshots"
        self.events_path = self.root / "events.jsonl"
        self.quarantine_path = self.root / "QUARANTINE.json"
        self.legacy_bytes_path = self.root / LEGACY_BYTES_NAME
        self.preservation_root = self.root / "preservation"
        self.lock_timeout_seconds = lock_timeout_seconds

    @property
    def audit_path(self) -> Path:
        return self.root / "audit.json"

    def _durable_directory_stop(self) -> Path:
        return self.root.parent

    # -- quarantine -------------------------------------------------------------------

    def _reject_identity_conflict(self) -> None:
        if not self.identity_conflict:
            return
        lexical, canonical = self.identity_conflict
        raise ChromaWriteGuardError(
            "refusing competing guard locations "
            f"{lexical} and {canonical}; not creating an empty authority"
        )

    def read_authority(self) -> AuthorityView:
        """Interpret the marker. A missing file is the only non-blocking state."""
        if self.identity_conflict:
            lexical, canonical = self.identity_conflict
            return _blocked(f"competing guard locations {lexical} and {canonical}")
        try:
            raw = self.quarantine_path.read_bytes()
        except FileNotFoundError:
            return _absent()
        except OSError as exc:
            return _blocked(f"unreadable quarantine record: {exc}")
        return _interpret_marker(raw, str(self.chroma_dir))

    def quarantine_state(self) -> dict[str, Any] | None:
        """Return the admission view, or None when the marker is genuinely absent."""
        view = self.read_authority()
        if view.state == "absent":
            return None
        payload = {
            "state": view.state,
            "blocking": view.blocking,
            "summary": view.summary,
            "reason": view.summary,
            "incidents": [copy.deepcopy(item) for item in view.incidents],
            "target": str(self.chroma_dir),
            "error": view.error,
            "legacy": view.legacy,
        }
        if view.document is not None:
            payload["authority_submission_digest"] = authority_submission_digest(view.document)
        return payload

    def require_not_quarantined(self) -> None:
        self._reject_identity_conflict()
        view = self.read_authority()
        if view.blocking:
            raise ChromaWriteQuarantinedError(
                f"chroma writes are quarantined: {view.summary}; see {self.quarantine_path}"
            )

    def clear_quarantine(
        self,
        *,
        disposition_ref: str | None = None,
        authority_digest: str | None = None,
    ) -> bool:
        """Ordinary clear refuses; validated release requires disposition and authority digest."""
        if disposition_ref is not None or authority_digest is not None:
            if not disposition_ref or not authority_digest:
                raise ChromaWriteGuardError(
                    "validated clear requires both disposition and current authority digest"
                )
            return self.release_quarantine(
                disposition_ref=disposition_ref,
                authority_digest=authority_digest,
            )
        self._reject_identity_conflict()
        if self.read_authority().state == "absent":
            return False
        with _exclusive_flock(self.lock_path, self.lock_timeout_seconds):
            if self.read_authority().state == "absent":
                return False
            raise ChromaWriteGuardError(
                "ordinary clear refuses unresolved incidents; "
                "validated release requires --disposition and --authority-digest; "
                f"see {self.quarantine_path}"
            )

    def release_quarantine(
        self,
        *,
        disposition_ref: str,
        authority_digest: str,
    ) -> bool:
        """Validated all-or-nothing release after durable disposition publication."""
        self._reject_identity_conflict()
        disposition = str(disposition_ref or "").strip()
        if not disposition:
            raise ChromaWriteGuardError("release requires a non-empty disposition reference")
        submitted = str(authority_digest or "").strip()
        if len(submitted) != 64:
            raise ChromaWriteGuardError("release requires a 64-char authority digest for the current incidents")
        if self.read_authority().state == "absent":
            return False
        with _exclusive_flock(self.lock_path, self.lock_timeout_seconds):
            view = self.read_authority()
            if view.state == "absent":
                return False
            if view.state == "blocked" or view.document is None:
                raise ChromaWriteGuardError(f"refusing release: {view.summary}")
            document = view.document
            current_digest = authority_submission_digest(document)
            if submitted != current_digest:
                raise ChromaWriteGuardError(
                    "release authority digest does not match the current unresolved incident set"
                )
            incidents = document.get("incidents")
            if not isinstance(incidents, list) or not incidents:
                raise ChromaWriteGuardError("release refuses empty incident document")
            con = sqlite3.connect(f"file:{self.chroma_dir / 'chroma.sqlite3'}?mode=ro", uri=True)
            try:
                _sqlite_reader_lock(con)
                self._validate_release_evidence_for_document(document, con=con)
                with self._events_cross_process_lock():
                    self._validate_events_tail_for_release()
                    self._append_event_record_durable(
                        "release_disposition",
                        disposition_ref=disposition,
                        authority_digest=current_digest,
                        incidents=[item["id"] for item in document["incidents"]],
                    )
                try:
                    self._remove_quarantine_marker_durable()
                except OSError as exc:
                    raise ChromaReleaseUncertaintyError(
                        "release disposition may be durable but quarantine marker removal is uncertain "
                        f"({exc}); request process-level containment and retry after review"
                    ) from exc
            finally:
                if con.in_transaction:
                    con.execute("ROLLBACK")
                con.close()
            return True

    def _release_evidence_for_incident(
        self, incident: Mapping[str, Any], *, snap_meta: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        pinned = incident.get("pinned_source")
        if not isinstance(pinned, dict):
            raise ChromaWriteGuardError("pinned restore source missing for release evidence")
        generation = pinned.get("generation")
        segment = incident.get("segment")
        if not isinstance(generation, str) or not isinstance(segment, str):
            raise ChromaWriteGuardError("invalid pinned generation for release evidence")
        if "/" in generation or generation.startswith("."):
            raise ChromaWriteGuardError("invalid pinned generation name")
        snap_dir = self.snapshots / segment / generation
        _assert_guard_relative_path(snap_dir, self.root)
        self._assert_snapshot_generation_dir(snap_dir)
        snap_meta_path = snap_dir / "SNAPSHOT.json"
        _reject_symlink_path(snap_meta_path)
        try:
            meta = snap_meta if snap_meta is not None else json.loads(
                snap_meta_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ChromaWriteGuardError(f"pinned snapshot metadata unreadable: {exc}") from exc
        expected_meta_digest = pinned.get("snapshot_meta_digest")
        if not isinstance(expected_meta_digest, str) or len(expected_meta_digest) != 64:
            raise ChromaWriteGuardError("pinned snapshot meta digest missing")
        actual_meta_digest = hashlib.sha256(
            json.dumps(meta, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if expected_meta_digest != actual_meta_digest:
            raise ChromaWriteGuardError("pinned snapshot metadata digest mismatch")
        saved_digests = pinned.get("segment_digests")
        if not isinstance(saved_digests, dict):
            raise ChromaWriteGuardError("pinned segment digests missing")
        if segment_file_digests(snap_dir) != saved_digests:
            raise ChromaWriteGuardError("pinned segment file digests mismatch")
        evidence = meta.get("release_evidence")
        if not isinstance(evidence, dict):
            raise ChromaWriteGuardError("pinned snapshot lacks release evidence")
        if evidence.get("status") == "unavailable":
            raise ChromaWriteGuardError("pinned snapshot release evidence is not yet admissible")
        return evidence

    def _validate_release_evidence_for_document(
        self, document: Mapping[str, Any], *, con: sqlite3.Connection
    ) -> None:
        for incident in document.get("incidents") or []:
            if not isinstance(incident, dict):
                raise ChromaWriteGuardError("invalid incident set for release")
            if _coerce_occurrence(incident.get("occurrence")) is None:
                raise ChromaWriteGuardError(
                    f"incident {incident.get('id')} lacks occurrence epoch; validated release unavailable"
                )
            for finding in incident.get("findings") or []:
                if not isinstance(finding, dict):
                    raise ChromaWriteGuardError("invalid finding set for release")
                kind = finding.get("kind")
                if kind not in _RELEASE_SUPPORTED_FINDING_KINDS:
                    raise ChromaWriteGuardError(f"unsupported finding kind {kind!r} for release")
            repair = incident.get("repair")
            if not isinstance(repair, dict) or repair.get("status") != "complete":
                raise ChromaWriteGuardError(f"incident {incident.get('id')} repair is not complete")
            preservation = incident.get("preservation")
            if not isinstance(preservation, dict) or preservation.get("status") != "complete":
                raise ChromaWriteGuardError(
                    f"incident {incident.get('id')} lacks complete preservation evidence"
                )
            manifest_digest = preservation.get("manifest_digest")
            if not isinstance(manifest_digest, str) or len(manifest_digest) != 64:
                raise ChromaWriteGuardError("preservation manifest digest missing or invalid")
            if not self._verify_preservation_manifest(str(incident.get("id")), manifest_digest, incident):
                raise ChromaWriteGuardError("preservation source evidence changed or is missing")
            evidence = self._release_evidence_for_incident(incident)
            ok, reason = evaluate_release_evidence(self.chroma_dir, evidence, con=con)
            if not ok:
                raise ChromaWriteGuardError(f"release evidence refuses admission: {reason}")

    def _validate_events_tail_for_release(self) -> None:
        if not self.events_path.is_file():
            return
        raw = self.events_path.read_bytes()
        if not raw:
            return
        if not raw.endswith(b"\n"):
            raise ChromaWriteGuardError("events log has a truncated final record; release blocked")
        for line in raw.decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ChromaWriteGuardError(f"events log contains malformed JSON: {exc}") from exc
            if not isinstance(parsed, dict):
                raise ChromaWriteGuardError("events log contains a non-object record")

    def _append_event_durable(self, event: str, **detail: Any) -> dict[str, Any]:
        with _EVENT_APPEND_LOCK:
            with self._events_cross_process_lock():
                return self._append_event_record_durable(event, **detail)

    @contextmanager
    def _events_cross_process_lock(self) -> Iterator[None]:
        lock_path = self.root / ".events-append.lock"
        with _exclusive_flock(lock_path, self.lock_timeout_seconds):
            yield

    def _append_event_record_durable(self, event: str, **detail: Any) -> dict[str, Any]:
        record = {"ts": _utc_now(), "event": event, "pid": os.getpid(), **detail}
        self.root.mkdir(parents=True, exist_ok=True)
        stop = self._durable_directory_stop()
        _fsync_directory_chain(self.root, stop=stop)
        line = json.dumps(record, sort_keys=True) + "\n"
        payload = line.encode("utf-8")
        with self.events_path.open("ab") as fh:
            written = fh.write(payload)
            if written != len(payload):
                raise OSError("short write of events log record")
            fh.flush()
            os.fsync(fh.fileno())
        _fsync_directory_chain(self.events_path.parent, stop=stop)
        return record

    def _remove_quarantine_marker_durable(self) -> bool:
        if not self.quarantine_path.is_file():
            return False
        self.quarantine_path.unlink()
        try:
            _fsync(self.quarantine_path.parent, directory=True)
        except OSError as exc:
            if self.quarantine_path.is_file():
                raise ChromaWriteGuardError(
                    f"quarantine marker retained after directory fsync failure ({exc})"
                ) from exc
            raise ChromaReleaseUncertaintyError(
                f"quarantine marker removal fsync uncertain ({exc}); request process-level containment"
            ) from exc
        return True

    def _pinned_generations(self, document: Mapping[str, Any] | None = None) -> set[tuple[str, str]]:
        pinned: set[tuple[str, str]] = set()
        if document is None:
            view = self.read_authority()
            if view.state == "absent":
                return pinned
            if view.state == "blocked" or view.document is None:
                raise ChromaWriteGuardError(
                    "cannot determine pinned generations from unrecognized quarantine authority"
                )
            document = view.document
        for incident in document.get("incidents") or []:
            if not isinstance(incident, dict):
                continue
            source = incident.get("pinned_source")
            segment = incident.get("segment")
            if isinstance(source, dict) and isinstance(segment, str):
                generation = source.get("generation")
                if isinstance(generation, str) and generation:
                    pinned.add((segment, generation))
        return pinned

    def _preservation_epoch(self, incident: Mapping[str, Any]) -> str:
        occ = _coerce_occurrence(incident.get("occurrence"))
        if occ is None:
            raise ChromaWriteGuardError("incident lacks occurrence epoch for preservation path")
        return occ["epoch"]

    def _preservation_dir(self, incident_id: str, incident: Mapping[str, Any] | None = None) -> Path:
        if not incident_id or "/" in incident_id or ".." in incident_id:
            raise ChromaWriteGuardError("invalid preservation incident id")
        if incident is None:
            view = self.read_authority()
            if view.document is None:
                raise ChromaWriteGuardError("missing incident document for preservation path")
            incident = next(
                (item for item in view.document.get("incidents") or [] if item.get("id") == incident_id),
                None,
            )
            if not isinstance(incident, dict):
                raise ChromaWriteGuardError(f"missing incident {incident_id} for preservation path")
        epoch = self._preservation_epoch(incident)
        if "/" in epoch or ".." in epoch:
            raise ChromaWriteGuardError("invalid preservation occurrence epoch")
        base = self.preservation_root / incident_id / epoch
        _assert_guard_relative_path(base, self.root)
        return base

    def _preservation_manifest_digest(self, raw: bytes) -> str:
        return hashlib.sha256(raw).hexdigest()

    def _segment_source_file_facts(self, seg_dir: Path) -> dict[str, Any]:
        _assert_live_segment_dir(seg_dir, self.chroma_dir)
        _reject_symlink_path(seg_dir)
        for child in seg_dir.iterdir():
            _reject_unsafe_directory_entry(child)
            if child.name in SEGMENT_FILES:
                continue
            if child.is_dir() or child.is_fifo():
                raise ChromaWriteGuardError(f"unsupported segment entry {child.name}")
            if child.is_file():
                raise ChromaWriteGuardError(f"unsupported extra segment file {child.name}")
        files: dict[str, Any] = {}
        for name in SEGMENT_FILES:
            src = seg_dir / name
            _reject_symlink_path(src)
            if not src.exists():
                files[name] = {"missing": True}
                continue
            if not src.is_file():
                raise ChromaWriteGuardError(f"preservation source {name} is not a regular file")
            _assert_regular_segment_file(src)
            data = src.read_bytes()
            files[name] = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
        return files

    def _preservation_manifest_header_valid(
        self, manifest: Mapping[str, Any], incident_id: str, incident: Mapping[str, Any]
    ) -> bool:
        if manifest.get("schema") != PRESERVATION_MANIFEST_SCHEMA:
            return False
        if manifest.get("version") != PRESERVATION_MANIFEST_VERSION:
            return False
        if manifest.get("status") != "complete":
            return False
        if manifest.get("incident_id") != incident_id:
            return False
        if manifest.get("occurrence_epoch") != self._preservation_epoch(incident):
            return False
        if manifest.get("segment") != incident.get("segment"):
            return False
        return manifest.get("target") == str(self.chroma_dir)

    def _preservation_originals_match_manifest(self, originals: Path, files: Mapping[str, Any]) -> bool:
        if set(files.keys()) != set(SEGMENT_FILES):
            return False
        _reject_symlink_path(originals)
        for name in SEGMENT_FILES:
            if not _safe_preservation_name(name):
                return False
            entry = files.get(name)
            if not isinstance(entry, dict):
                return False
            if entry.get("missing"):
                if (originals / name).exists():
                    return False
                continue
            path = originals / name
            _reject_symlink_path(path)
            _assert_regular_segment_file(path)
            if not path.is_file():
                return False
            sha = entry.get("sha256")
            size = entry.get("size")
            if not isinstance(sha, str) or len(sha) != 64 or not isinstance(size, int):
                return False
            data = path.read_bytes()
            if len(data) != size or hashlib.sha256(data).hexdigest() != sha:
                return False
        return True

    def _verify_preservation_manifest(
        self, incident_id: str, expected_digest: str, incident: Mapping[str, Any]
    ) -> bool:
        base = self._preservation_dir(incident_id, incident)
        manifest_path = base / "MANIFEST.json"
        if not manifest_path.is_file():
            return False
        _reject_symlink_path(manifest_path)
        _assert_regular_segment_file(manifest_path)
        try:
            raw = manifest_path.read_bytes()
        except OSError:
            return False
        if self._preservation_manifest_digest(raw) != expected_digest:
            return False
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        if not isinstance(manifest, dict):
            return False
        if not self._preservation_manifest_header_valid(manifest, incident_id, incident):
            return False
        files = manifest.get("files")
        if not isinstance(files, dict):
            return False
        recorded = _preservation_original_facts(incident)
        if recorded is None or not _source_facts_equal(files, recorded):
            return False
        return self._preservation_originals_match_manifest(base / "originals", files)

    def _bind_preservation_to_incident(self, document: dict[str, Any], incident_id: str, manifest_digest: str) -> None:
        incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
        if incident is None:
            raise ChromaWriteGuardError(f"missing incident {incident_id} for preservation binding")
        preservation = incident.get("preservation")
        original_facts = _preservation_original_facts(incident) if isinstance(preservation, dict) else None
        if isinstance(preservation, dict) and preservation.get("status") == "complete":
            bound = preservation.get("manifest_digest")
            if isinstance(bound, str) and bound != manifest_digest:
                raise ChromaWriteGuardError("preservation manifest binding is immutable")
            if bound == manifest_digest:
                return
        bound_preservation: dict[str, Any] = {
            "status": "complete",
            "manifest_digest": manifest_digest,
        }
        if original_facts is not None:
            bound_preservation["original_facts"] = copy.deepcopy(original_facts)
        incident["preservation"] = bound_preservation
        document["version"] = INCIDENT_VERSION
        self._publish_marker(document)

    def _require_live_source_facts_match(
        self,
        seg_dir: Path,
        recorded: Mapping[str, Any],
    ) -> None:
        live = self._segment_source_file_facts(seg_dir)
        if not _source_facts_equal(live, recorded):
            raise ChromaWriteGuardError(
                "live segment source facts changed since preservation original facts were recorded"
            )

    def _publish_preservation_original_facts(
        self,
        document: dict[str, Any],
        incident_id: str,
        source_facts: Mapping[str, Any],
    ) -> None:
        incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
        if incident is None:
            raise ChromaWriteGuardError(f"missing incident {incident_id} for preservation recording")
        preservation = incident.get("preservation")
        if isinstance(preservation, dict) and preservation.get("status") == "complete":
            recorded = preservation.get("original_facts")
            if isinstance(recorded, dict) and not _source_facts_equal(recorded, source_facts):
                raise ChromaWriteGuardError("preservation original facts are immutable")
            return
        if isinstance(preservation, dict) and preservation.get("status") == "in_progress":
            recorded = preservation.get("original_facts")
            if isinstance(recorded, dict):
                if not _source_facts_equal(recorded, source_facts):
                    raise ChromaWriteGuardError("preservation original facts are immutable")
                return
        incident["preservation"] = {
            "status": "in_progress",
            "original_facts": copy.deepcopy(dict(source_facts)),
        }
        document["version"] = INCIDENT_VERSION
        self._publish_marker(document)

    def _ensure_preservation_complete(
        self,
        document: dict[str, Any],
        incident_id: str,
        segment: str,
        seg_dir: Path,
    ) -> str:
        incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
        if incident is None:
            raise ChromaWriteGuardError(f"missing incident {incident_id} for preservation")
        preservation = incident.get("preservation")
        base = self._preservation_dir(incident_id, incident)
        manifest_path = base / "MANIFEST.json"
        if manifest_path.is_file():
            raw = manifest_path.read_bytes()
            digest = self._preservation_manifest_digest(raw)
            if self._verify_preservation_manifest(incident_id, digest, incident):
                if not isinstance(preservation, dict) or preservation.get("manifest_digest") != digest:
                    self._bind_preservation_to_incident(document, incident_id, digest)
                return digest
            raise ChromaWriteGuardError("existing preservation manifest failed validation")
        if isinstance(preservation, dict) and preservation.get("status") == "complete":
            digest = preservation.get("manifest_digest")
            if isinstance(digest, str) and self._verify_preservation_manifest(incident_id, digest, incident):
                return digest
            raise ChromaWriteGuardError("completed preservation failed revalidation")
        durable_stop = self._durable_directory_stop()
        recorded = _preservation_original_facts(incident)
        if isinstance(preservation, dict) and preservation.get("status") == "in_progress" and recorded is None:
            raise ChromaWriteGuardError("preservation in progress lacks recorded original facts")
        if recorded is not None:
            self._require_live_source_facts_match(seg_dir, recorded)
            source_facts = recorded
        else:
            source_facts = self._segment_source_file_facts(seg_dir)
            self._publish_preservation_original_facts(document, incident_id, source_facts)
            incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
            if incident is None:
                raise ChromaWriteGuardError(f"missing incident {incident_id} after preservation recording")
        base.mkdir(parents=True, exist_ok=True)
        _fsync_directory_chain(base, stop=durable_stop)
        originals = base / "originals"
        originals.mkdir(parents=True, exist_ok=True)
        _fsync_directory_chain(originals, stop=durable_stop)
        for name in SEGMENT_FILES:
            entry = source_facts[name]
            if entry.get("missing"):
                continue
            src = seg_dir / name
            dst = originals / name
            if dst.exists():
                data = dst.read_bytes()
                if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["size"]:
                    raise ChromaWriteGuardError(f"preservation originals for {name} differ; refusing overwrite")
            else:
                _copy_durable(src, dst)
                data = dst.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["size"]:
                raise ChromaWriteGuardError(f"preservation copy for {name} does not match pre-captured source facts")
        manifest: dict[str, Any] = {
            "schema": PRESERVATION_MANIFEST_SCHEMA,
            "version": PRESERVATION_MANIFEST_VERSION,
            "incident_id": incident_id,
            "occurrence_epoch": self._preservation_epoch(incident),
            "segment": segment,
            "target": str(self.chroma_dir),
            "files": source_facts,
            "status": "complete",
            "completed_at": _utc_now(),
        }
        if manifest_path.is_file():
            raw = manifest_path.read_bytes()
            digest = self._preservation_manifest_digest(raw)
            if self._verify_preservation_manifest(incident_id, digest, incident):
                self._bind_preservation_to_incident(document, incident_id, digest)
                return digest
            raise ChromaWriteGuardError("existing preservation manifest failed validation")
        raw = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        tmp = manifest_path.with_name(f".MANIFEST.{os.getpid()}.tmp")
        tmp.write_bytes(raw)
        _fsync(tmp)
        if tmp.read_bytes() != raw:
            raise OSError("short write of preservation manifest")
        os.replace(tmp, manifest_path)
        _fsync_directory_chain(base, stop=durable_stop)
        digest = self._preservation_manifest_digest(raw)
        self._bind_preservation_to_incident(document, incident_id, digest)
        return digest

    def _bind_restore_source_to_incident(
        self,
        document: dict[str, Any],
        incident_id: str,
        segment: str,
        snapshot: tuple[Path, dict[str, Any]],
    ) -> None:
        snap_dir, meta = snapshot
        generation = snap_dir.name
        if "/" in generation or generation.startswith("."):
            raise ChromaWriteGuardError("invalid snapshot generation name")
        _assert_guard_relative_path(snap_dir, self.root)
        incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
        if incident is None:
            raise ChromaWriteGuardError(f"missing incident {incident_id} for restore binding")
        pinned = incident.get("pinned_source")
        if isinstance(pinned, dict) and pinned.get("generation"):
            if pinned.get("generation") != generation or pinned.get("segment") != segment:
                raise ChromaWriteGuardError("incident repair bound to a different source generation")
            return
        if meta.get("release_evidence") is None:
            raise ChromaWriteGuardError(
                "pinned restore source lacks release evidence; release remains unknown"
            )
        incident["pinned_source"] = {
            "segment": segment,
            "generation": generation,
            "segment_digests": segment_file_digests(snap_dir),
            "snapshot_meta_digest": hashlib.sha256(
                json.dumps(meta, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }
        incident["repair"] = {"status": "in_progress", "phase": "preservation"}
        document["version"] = INCIDENT_VERSION
        self._publish_marker(document)

    def _write_bytes(self, path: Path, payload: bytes) -> None:
        path.write_bytes(payload)

    def _fsync_published(self, path: Path, *, directory: bool = False) -> None:
        _fsync(path, directory=directory)

    def _write_exact(self, path: Path, payload: bytes) -> None:
        """Publish exact bytes durably. Refuse to replace a different preserved payload."""
        self.root.mkdir(parents=True, exist_ok=True)
        if path.exists():
            try:
                existing = path.read_bytes()
            except OSError as exc:
                raise ChromaContainmentUnavailableError(_containment_text(exc)) from exc
            if existing != payload:
                raise ChromaWriteGuardError(
                    f"preserved quarantine bytes at {path} differ; refusing to overwrite them"
                )
            return
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            self._write_bytes(tmp, payload)
            self._fsync_published(tmp)
            if tmp.read_bytes() != payload:
                raise OSError(f"short write of {path.name}")
            os.replace(tmp, path)
            self._fsync_published(path.parent, directory=True)
        except OSError as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise ChromaContainmentUnavailableError(_containment_text(exc)) from exc

    def _publish_marker(self, document: Mapping[str, Any]) -> None:
        payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.quarantine_path.with_name(f".{self.quarantine_path.name}.{os.getpid()}.tmp")
        replaced = False
        try:
            self._write_bytes(tmp, payload)
            self._fsync_published(tmp)
            if tmp.read_bytes() != payload:
                raise OSError("short write of quarantine marker")
            os.replace(tmp, self.quarantine_path)
            replaced = True
            self._fsync_published(self.quarantine_path.parent, directory=True)
        except OSError as exc:
            if tmp.exists() and not replaced:
                tmp.unlink(missing_ok=True)
            raise ChromaContainmentUnavailableError(_containment_text(exc)) from exc

    def _load_incident_document(self) -> tuple[dict[str, Any], bytes | None]:
        """Return the document to update, plus original legacy bytes when adopting."""
        try:
            raw = self.quarantine_path.read_bytes()
        except FileNotFoundError:
            return _empty_incident_document(str(self.chroma_dir)), None
        except OSError as exc:
            raise ChromaContainmentUnavailableError(_containment_text(exc)) from exc
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ChromaWriteGuardError(f"refusing to replace unrecognized quarantine marker: {exc}") from exc
        if isinstance(parsed, dict) and parsed.get("schema") == INCIDENT_SCHEMA:
            view = _interpret_current(parsed, str(self.chroma_dir))
            if view.state == "blocked" or view.document is None:
                raise ChromaWriteGuardError(
                    f"refusing to replace unrecognized quarantine marker: {view.summary}"
                )
            return copy.deepcopy(view.document), None
        if isinstance(parsed, dict) and _is_recognized_legacy(parsed):
            return _document_from_legacy(parsed, str(self.chroma_dir), raw), raw
        raise ChromaWriteGuardError("refusing to replace unrecognized quarantine marker")

    def _publish_findings(self, specs: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge findings into the marker. Caller holds the native lock."""
        self._reject_identity_conflict()
        document, legacy_raw = self._load_incident_document()
        changed = legacy_raw is not None
        for spec in specs:
            changed = _upsert_finding(document, spec) or changed
        if not changed:
            return document
        if legacy_raw is not None:
            self._write_exact(self.legacy_bytes_path, legacy_raw)
        self._publish_marker(document)
        return document

    def _contain(self, specs: list[dict[str, Any]]) -> NoReturn:
        """Publish every finding, then refuse the operation. Publication failure is not a stop."""
        document = self._publish_findings(specs)
        try:
            self._event(
                "quarantined",
                incidents=[item["id"] for item in document["incidents"]],
                findings=sum(len(item["findings"]) for item in document["incidents"]),
            )
        except OSError:
            pass
        raise ChromaWriteQuarantinedError(
            f"chroma writes quarantined: {_summary(document['incidents'])}; see {self.quarantine_path}"
        )

    def _event(self, event: str, **detail: Any) -> dict[str, Any]:
        return self._append_event_durable(event, **detail)

    # -- the write protocol -------------------------------------------------------------

    @contextmanager
    def native_write(self, *, identifier: str, reload_client: Callable[[], None]) -> Iterator[None]:
        """Run one native Chroma mutation under the containment invariants."""
        self._reject_identity_conflict()
        if canonical_target(identifier) != self.chroma_dir:
            raise ChromaWriteGuardError(
                f"write identifier {identifier} is not the canonical target {self.chroma_dir}"
            )
        key = _view_key(identifier)
        self.require_not_quarantined()
        barrier = os.environ.get(_ADMISSION_BARRIER_ENV)
        if barrier:
            _wait_barrier(barrier)
        with _exclusive_flock(self.lock_path, self.lock_timeout_seconds):
            self.require_not_quarantined()
            self.reconcile()
            if self.read_authority().blocking:
                view = self.read_authority()
                raise ChromaWriteQuarantinedError(
                    f"chroma writes are quarantined: {view.summary}; see {self.quarantine_path}"
                )
            before = store_signature(self.chroma_dir)
            if _synced_only(_system_view(key)) != _synced_only(before):
                reload_client()
                _set_system_view(key, before)
            try:
                yield
            except BaseException:
                self._after_write(key, before, system_trusted=False)
                raise
            self._after_write(key, before, system_trusted=True)

    def _after_write(self, identifier: str, before: dict[str, Signature], *, system_trusted: bool) -> None:
        after = store_signature(self.chroma_dir)
        # A failed native call leaves the in-process system's state unknown: reload next time.
        _set_system_view(identifier, after if system_trusted else None)
        pending: list[dict[str, Any]] = []
        for seg_id, seg in segment_dirs(self.chroma_dir).items():
            if before.get(seg_id) == after.get(seg_id):
                continue
            report = validate_segment(seg)
            if report.ok:
                self._refresh_snapshot(seg_id, seg, after[seg_id])  # logs only a first copy
                continue
            pending.append(
                _finding_spec(
                    seg_id,
                    "structural",
                    "this process's own save failed validation; not restoring the previous save "
                    "because Chroma has already purged the records written since it",
                    report.failures,
                )
            )
        if pending:
            self._contain(pending)

    def resume_bounded_restore(
        self,
        *,
        incident_id: str,
        authority_digest: str,
    ) -> list[dict[str, Any]]:
        """Resume bounded automatic restore for one quarantined incident (acquires native lock)."""
        with _exclusive_flock(self.lock_path, self.lock_timeout_seconds):
            return self._resume_bounded_restore_locked(
                incident_id=incident_id,
                authority_digest=authority_digest,
            )

    def _resume_bounded_restore_locked(
        self,
        *,
        incident_id: str,
        authority_digest: str,
    ) -> list[dict[str, Any]]:
        submitted = str(authority_digest or "").strip()
        if len(submitted) != 64:
            raise ChromaWriteGuardError("resume requires a 64-char authority digest")
        view = self.read_authority()
        if view.document is None:
            raise ChromaWriteGuardError("no quarantine authority to resume")
        document = view.document
        if authority_submission_digest(document) != submitted:
            raise ChromaWriteGuardError("resume authority digest does not match current incidents")
        incident = next((item for item in document["incidents"] if item.get("id") == incident_id), None)
        if not isinstance(incident, dict):
            raise ChromaWriteGuardError(f"resume incident {incident_id} not found")
        segment = incident.get("segment")
        pinned = incident.get("pinned_source")
        repair = incident.get("repair")
        if not isinstance(segment, str) or not isinstance(pinned, dict):
            raise ChromaWriteGuardError("resume requires a pinned restore source")
        if not isinstance(repair, dict) or repair.get("status") not in {"in_progress", "complete"}:
            raise ChromaWriteGuardError("resume requires repair already bound to the incident")
        generation = pinned.get("generation")
        if not isinstance(generation, str):
            raise ChromaWriteGuardError("resume pinned generation missing")
        snap_dir = self.snapshots / segment / generation
        _assert_guard_relative_path(snap_dir, self.root)
        snap_meta_path = snap_dir / "SNAPSHOT.json"
        _reject_symlink_path(snap_meta_path)
        try:
            meta = json.loads(snap_meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ChromaWriteGuardError(f"resume pinned snapshot unreadable: {exc}") from exc
        self._release_evidence_for_incident(incident, snap_meta=meta)
        if segment_file_digests(snap_dir) != pinned.get("segment_digests"):
            raise ChromaWriteGuardError("resume pinned segment digests mismatch")
        seg_dirs = segment_dirs(self.chroma_dir)
        if segment not in seg_dirs:
            raise ChromaWriteGuardError("resume segment missing from live store")
        seg = seg_dirs[segment]
        document, _ = self._load_incident_document()
        self._ensure_preservation_complete(document, incident_id, segment, seg)
        live_report = validate_segment(seg)
        if live_report.ok and repair.get("status") == "complete":
            return []
        snapshot = (snap_dir, meta)
        event, extra = self._restore(segment, seg, snapshot, live_report)
        events: list[dict[str, Any]] = []
        if event is not None:
            events.append(event)
        if extra:
            self._contain(extra)
        return events

    def reconcile(self) -> list[dict[str, Any]]:
        """Bring every live segment back to a validated save; the caller holds the lock."""
        self.require_not_quarantined()
        events: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []
        restores: list[tuple[str, Path, tuple[Path, dict[str, Any]], SegmentReport]] = []
        for seg_id, seg in segment_dirs(self.chroma_dir).items():
            live_sig = segment_signature(seg)
            snapshot = self.current_snapshot(seg_id)
            if snapshot is not None and snapshot[1].get("live_signature") == live_sig:
                continue
            report = validate_segment(seg)
            if report.ok:
                # A newer complete save nobody copied yet: a writer died after saving,
                # or this is the first guarded contact with the store.
                created = self._refresh_snapshot(seg_id, seg, live_sig)
                events.append(created or self._event("snapshot_adopted", segment=seg_id))
                continue
            if snapshot is None:
                pending.append(
                    _finding_spec(
                        seg_id,
                        "structural",
                        "live segment failed validation and no validated save exists",
                        report.failures,
                    )
                )
                continue
            snap_report = validate_segment(snapshot[0])
            if not snap_report.ok:
                pending.append(
                    _finding_spec(
                        seg_id,
                        "structural",
                        "live segment failed validation and its saved copy failed too",
                        report.failures,
                        {"snapshot_failures": list(snap_report.failures)},
                    )
                )
                continue
            restores.append((seg_id, seg, snapshot, report))
        if pending:
            self._contain(pending)
        post: list[dict[str, Any]] = []
        for seg_id, seg, snapshot, report in restores:
            event, extra = self._restore(seg_id, seg, snapshot, report)
            if event is not None:
                events.append(event)
            post.extend(extra)
        if post:
            self._contain(post)
        return events

    # -- snapshots ------------------------------------------------------------------------

    def _validate_snapshot_generation_name(self, generation: str) -> None:
        if not generation or "/" in generation or ".." in generation or generation.startswith("."):
            raise ChromaWriteGuardError(f"invalid snapshot generation name {generation!r}")

    def _assert_snapshot_generation_dir(self, snap_dir: Path) -> None:
        _reject_symlink_path(snap_dir)
        if snap_dir.is_symlink() or not snap_dir.is_dir():
            raise ChromaWriteGuardError(f"refusing unsafe snapshot generation directory {snap_dir}")
        for child in snap_dir.iterdir():
            _reject_unsafe_directory_entry(child)
            if child.name in SEGMENT_FILES or child.name == "SNAPSHOT.json":
                _reject_symlink_path(child)
                if child.exists():
                    _assert_regular_segment_file(child)
                continue
            raise ChromaWriteGuardError(f"unsupported snapshot generation entry {child.name}")

    def current_snapshot(self, seg_id: str) -> tuple[Path, dict[str, Any]] | None:
        if not seg_id or "/" in seg_id or ".." in seg_id:
            raise ChromaWriteGuardError("invalid snapshot segment id")
        base = self.snapshots / seg_id
        _assert_guard_relative_path(base, self.root)
        current_path = base / "CURRENT"
        if not current_path.is_file():
            return None
        _reject_symlink_path(current_path)
        try:
            generation = current_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ChromaWriteGuardError(f"refusing unreadable snapshot CURRENT for {seg_id}: {exc}") from exc
        if not generation:
            raise ChromaWriteGuardError(f"refusing empty snapshot CURRENT for {seg_id}")
        self._validate_snapshot_generation_name(generation)
        snap_dir = base / generation
        _assert_guard_relative_path(snap_dir, self.root)
        self._assert_snapshot_generation_dir(snap_dir)
        meta_path = snap_dir / "SNAPSHOT.json"
        _reject_symlink_path(meta_path)
        if not meta_path.is_file():
            raise ChromaWriteGuardError(f"refusing snapshot generation without SNAPSHOT.json for {seg_id}")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ChromaWriteGuardError(f"refusing malformed snapshot metadata for {seg_id}: {exc}") from exc
        if not isinstance(meta, dict):
            raise ChromaWriteGuardError(f"refusing non-object snapshot metadata for {seg_id}")
        if meta.get("segment") != seg_id:
            raise ChromaWriteGuardError(
                f"refusing snapshot segment binding mismatch for {seg_id}: {meta.get('segment')!r}"
            )
        return snap_dir, meta

    def _refresh_snapshot(self, seg_id: str, seg: Path, live_sig: Signature) -> dict[str, Any] | None:
        """Copy the live save as the segment's restore point; returns the event for a first copy."""
        base = self.snapshots / seg_id
        first = not (base / "CURRENT").exists()
        base.mkdir(parents=True, exist_ok=True)
        generation = f"g{time.time_ns()}-{os.getpid()}"
        staging = base / f".{generation}.partial"
        staging.mkdir()
        try:
            for name in SEGMENT_FILES:
                if (seg / name).is_file():
                    _copy_durable(seg / name, staging / name)
            if segment_signature(seg) != live_sig:
                raise ChromaWriteGuardError(
                    f"segment {seg_id} changed while its save was being copied; "
                    "something is writing the store outside the write guard"
                )
            meta: dict[str, Any] = {
                "segment": seg_id,
                "live_signature": live_sig,
                "created_at": _utc_now(),
                "pid": os.getpid(),
            }
            con: sqlite3.Connection | None = None
            try:
                con = sqlite3.connect(f"file:{self.chroma_dir / 'chroma.sqlite3'}?mode=ro", uri=True)
                _sqlite_reader_lock(con)
                census = self._census_for_segment(seg_id)
                collection = census.get("collection")
                if isinstance(collection, str) and collection:
                    try:
                        evidence = build_release_evidence_for_collection(
                            self.chroma_dir,
                            collection,
                            segment_dir=staging,
                            con=con,
                        )
                    except ReleaseEvidenceCaptureUnavailable as exc:
                        meta["release_evidence"] = _unavailable_release_evidence(exc.reason)
                    else:
                        if segment_file_digests(staging) != evidence.get("segment_digests"):
                            raise ChromaWriteGuardError(
                                "snapshot copy digests do not match captured release evidence"
                            )
                        meta["release_evidence"] = evidence
            finally:
                if con is not None:
                    if con.in_transaction:
                        con.execute("ROLLBACK")
                    con.close()
            _write_json_durable(staging / "SNAPSHOT.json", meta)
            _fsync(staging, directory=True)
            os.rename(staging, base / generation)
            _fsync(base, directory=True)
            current_tmp = base / f".CURRENT.{os.getpid()}.tmp"
            current_tmp.write_text(generation, encoding="utf-8")
            _fsync(current_tmp)
            os.replace(current_tmp, base / "CURRENT")
            _fsync(base, directory=True)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        pinned = self._pinned_generations()
        for old in base.iterdir():
            if old.is_dir() and old.name != generation:
                if (seg_id, old.name) in pinned:
                    continue
                shutil.rmtree(old, ignore_errors=True)
            elif old.name.startswith(".CURRENT."):
                old.unlink(missing_ok=True)  # left by a writer killed mid-refresh
        return self._event("snapshot_created", segment=seg_id) if first else None

    def _restore(
        self,
        seg_id: str,
        seg: Path,
        snapshot: tuple[Path, dict[str, Any]],
        live_report: SegmentReport,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        snap_dir, _snap_meta = snapshot
        snap_report = validate_segment(snap_dir)
        if not snap_report.ok:
            return None, [
                _finding_spec(
                    seg_id,
                    "structural",
                    "live segment failed validation and its saved copy failed too",
                    live_report.failures,
                    {"snapshot_failures": list(snap_report.failures)},
                )
            ]
        incident_id = _incident_id(str(self.chroma_dir), seg_id)
        document, _ = self._load_incident_document()
        incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
        repair = incident.get("repair") if isinstance(incident, dict) else None
        if not isinstance(repair, dict) or repair.get("status") not in {"in_progress", "complete"}:
            document = self._publish_findings(
                [
                    _finding_spec(
                        seg_id,
                        "structural",
                        _RESTORE_REQUIRED_REASON,
                        live_report.failures,
                        {"phase": "restore_required"},
                    )
                ]
            )
        document, _ = self._load_incident_document()
        try:
            self._bind_restore_source_to_incident(document, incident_id, seg_id, snapshot)
        except ChromaWriteGuardError as exc:
            return None, [
                _finding_spec(
                    seg_id,
                    "structural",
                    "bounded restore refused before replacement",
                    live_report.failures,
                    {"error": str(exc)},
                )
            ]
        document, _ = self._load_incident_document()
        incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
        pinned_source = incident.get("pinned_source") if isinstance(incident, dict) else None
        if isinstance(pinned_source, dict):
            saved_digests = pinned_source.get("segment_digests")
            if isinstance(saved_digests, dict) and segment_file_digests(snap_dir) != saved_digests:
                return None, [
                    _finding_spec(
                        seg_id,
                        "structural",
                        "pinned restore source generation changed before replacement",
                        live_report.failures,
                    )
                ]
        self._ensure_preservation_complete(document, incident_id, seg_id, seg)
        document, _ = self._load_incident_document()
        for name in SEGMENT_FILES:
            target = seg / name
            if (snap_dir / name).exists():
                staging = seg / f".{name}.guard-restore"
                _copy_durable(snap_dir / name, staging)
                os.replace(staging, target)
            elif target.exists():
                target.unlink()
        _fsync(seg, directory=True)
        restored = validate_segment(seg)
        if not restored.ok:
            return None, [
                _finding_spec(seg_id, "structural", "restored segment failed validation", restored.failures)
            ]
        census = self._census_for_segment(seg_id)
        document, _ = self._load_incident_document()
        incident = next((item for item in document["incidents"] if item["id"] == incident_id), None)
        if isinstance(incident, dict):
            incident["repair"] = {"status": "complete", "phase": "restored"}
            document["version"] = INCIDENT_VERSION
            self._publish_marker(document)
        event = self._event(
            "segment_restored",
            segment=seg_id,
            torn=list(live_report.failures)[:5],
            census=census,
        )
        if census.get("lost"):
            return event, [
                _finding_spec(
                    seg_id,
                    "lost_vectors",
                    "restoring the last save left records without vectors",
                    live_report.failures,
                    {"census": census},
                )
            ]
        return event, [
            _finding_spec(
                seg_id,
                "segment_restored",
                "automatic segment restore completed; owner disposition required before release",
                live_report.failures,
                {"census": census},
            )
        ]

    def _census_for_segment(self, seg_id: str) -> dict[str, Any]:
        last_exc: BaseException | None = None
        for attempt in range(2):
            try:
                for name, row in vector_census(self.chroma_dir).items():
                    if row.get("vector_segment") == seg_id:
                        return {"collection": name, **row}
                return {"unavailable": "segment not listed in chroma.sqlite3"}
            except (sqlite3.Error, OSError, pickle.UnpicklingError, EOFError) as exc:
                last_exc = exc
                if attempt == 0:
                    continue
                return {"unavailable": str(exc)}
        return {"unavailable": str(last_exc) if last_exc else "census unavailable"}

    # -- scheduled silent-loss audit ----------------------------------------------------

    def audit(self, *, lock_timeout_seconds: float = AUDIT_LOCK_TIMEOUT_SECONDS) -> dict[str, Any]:
        """Validate every live segment and count lost vectors; never modifies the store.

        Holds the native-write lock so no save is read half-written: writers wait for
        the audit instead of the audit reporting a torn read as corruption. Findings
        are published to ``QUARANTINE.json`` before the lock is released. A later
        pass, skip, or error updates ``audit.json`` only and cannot clear incidents.
        A busy lock records ``skipped``. A diagnostic error alone is not corruption.
        """
        result: dict[str, Any] = {"started": _utc_now(), "pid": os.getpid()}
        if self.identity_conflict:
            lexical, canonical = self.identity_conflict
            result.update(
                status="error",
                reason=f"competing guard locations {lexical} and {canonical}",
                ts=_utc_now(),
            )
            return result
        try:
            with _exclusive_flock(self.lock_path, lock_timeout_seconds):
                self._audit_locked(result)
        except TimeoutError as exc:
            result.update(status="skipped", reason=str(exc), ts=_utc_now())
            self.root.mkdir(parents=True, exist_ok=True)
            _write_json_durable(self.audit_path, result)
            self._event("audit", status="skipped", lost=result.get("lost"))
        return result

    def _audit_locked(self, result: dict[str, Any]) -> None:
        barrier = os.environ.get(_LOCK_HOLD_BARRIER_ENV)
        if barrier:
            _wait_barrier(barrier)
        reports, report_error = _collect_reports(self.chroma_dir)
        census, census_error = _collect_census(self.chroma_dir)
        specs = _audit_findings(reports, report_error, census, census_error)
        publication_error = self._publish_audit_findings(specs)
        _fill_audit_result(
            result,
            {
                "reports": reports,
                "report_error": report_error,
                "census": census,
                "census_error": census_error,
            },
            specs,
            publication_error,
        )
        result["ts"] = _utc_now()
        self.root.mkdir(parents=True, exist_ok=True)
        _write_json_durable(self.audit_path, result)
        self._event("audit", status=result["status"], lost=result.get("lost"))

    def _publish_audit_findings(self, specs: list[dict[str, Any]]) -> BaseException | None:
        if not specs:
            return None
        try:
            document = self._publish_findings(specs)
        except (ChromaContainmentUnavailableError, ChromaWriteGuardError) as exc:
            return exc
        try:
            self._event(
                "quarantined",
                incidents=[item["id"] for item in document["incidents"]],
                findings=sum(len(item["findings"]) for item in document["incidents"]),
            )
        except OSError:
            return None
        return None

    def last_audit(self) -> dict[str, Any] | None:
        try:
            data = json.loads(self.audit_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as exc:
            return {"status": "error", "reason": f"unreadable audit record: {exc}"}
        return data if isinstance(data, dict) else {"status": "error", "reason": "audit record is not an object"}


def recover(
    chroma_dir: str | Path,
    *,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    incident_id: str | None = None,
    authority_digest: str | None = None,
) -> list[dict[str, Any]]:
    """Restore torn segments now -- e.g. right after a writer died from a native fault."""
    guard = ChromaWriteGuard(chroma_dir, lock_timeout_seconds=lock_timeout_seconds)
    guard._reject_identity_conflict()  # pylint: disable=protected-access
    barrier = os.environ.get(_ADMISSION_BARRIER_ENV)
    if barrier:
        _wait_barrier(barrier)
    if incident_id is not None or authority_digest is not None:
        if not incident_id or not authority_digest:
            raise ChromaWriteGuardError(
                "bounded resume requires both incident id and authority digest"
            )
        return guard.resume_bounded_restore(
            incident_id=incident_id,
            authority_digest=authority_digest,
        )
    with _exclusive_flock(guard.lock_path, lock_timeout_seconds):
        guard.require_not_quarantined()
        return guard.reconcile()


def write_guard_enabled(cfg: Mapping[str, Any] | None) -> bool:
    """``[index] chroma_write_guard = false`` turns the guard off; it is on by default."""
    index = (cfg or {}).get("index")
    if not isinstance(index, Mapping):
        return True
    return index.get("chroma_write_guard", True) is not False
