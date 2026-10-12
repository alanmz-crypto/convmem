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
INCIDENT_VERSION = 1
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
    The guard's own load record uses the canonical target (see ``_view_key``).
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
    return {"id": incident_id, "segment": segment, "findings": coerced}


def _interpret_current(parsed: Mapping[str, Any], expected_target: str) -> AuthorityView:
    if parsed.get("version") != INCIDENT_VERSION:
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
        "version": INCIDENT_VERSION,
        "target": expected_target,
        "incidents": incidents,
    }
    legacy_hash = parsed.get("legacy_original_sha256")
    if isinstance(legacy_hash, str):
        document["legacy_original_sha256"] = legacy_hash
    blocking = bool(incidents)
    summary = _summary(incidents) if blocking else "no unresolved incidents"
    state = "unresolved" if blocking else "clear"
    return AuthorityView(state, blocking, summary, tuple(incidents), document, None, False)


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
        incident = {"id": incident_id, "segment": segment, "findings": []}
        document["incidents"].append(incident)
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
        self.lock_timeout_seconds = lock_timeout_seconds

    @property
    def audit_path(self) -> Path:
        return self.root / "audit.json"

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
        """Interpret the marker. Missing is the only non-blocking state besides a valid empty set."""
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
        return {
            "state": view.state,
            "blocking": view.blocking,
            "summary": view.summary,
            "reason": view.summary,
            "incidents": [copy.deepcopy(item) for item in view.incidents],
            "target": str(self.chroma_dir),
            "error": view.error,
            "legacy": view.legacy,
        }

    def require_not_quarantined(self) -> None:
        self._reject_identity_conflict()
        view = self.read_authority()
        if view.blocking:
            raise ChromaWriteQuarantinedError(
                f"chroma writes are quarantined: {view.summary}; see {self.quarantine_path}"
            )

    def clear_quarantine(self) -> bool:
        """Refuse every present marker. Validated release is not part of this task.

        Returns False only when the marker is absent. Any unresolved, legacy, or
        unrecognized marker stays on disk.
        """
        self._reject_identity_conflict()
        if self.read_authority().state == "absent":
            return False
        with _exclusive_flock(self.lock_path, self.lock_timeout_seconds):
            if self.read_authority().state == "absent":
                return False
            raise ChromaWriteGuardError(
                "ordinary clear refuses unresolved incidents; "
                "validated release is not available; "
                f"see {self.quarantine_path}"
            )

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
        record = {"ts": _utc_now(), "event": event, "pid": os.getpid(), **detail}
        self.root.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
        return record

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

    def current_snapshot(self, seg_id: str) -> tuple[Path, dict[str, Any]] | None:
        base = self.snapshots / seg_id
        try:
            generation = (base / "CURRENT").read_text(encoding="utf-8").strip()
            meta = json.loads((base / generation / "SNAPSHOT.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return base / generation, meta

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
            meta = {"segment": seg_id, "live_signature": live_sig, "created_at": _utc_now(), "pid": os.getpid()}
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
        for old in base.iterdir():
            if old.is_dir() and old.name != generation:
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
        snap_dir, meta = snapshot
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
        _write_json_durable(snap_dir / "SNAPSHOT.json", {**meta, "live_signature": segment_signature(seg)})
        census = self._census_for_segment(seg_id)
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
        return event, []

    def _census_for_segment(self, seg_id: str) -> dict[str, Any]:
        try:
            for name, row in vector_census(self.chroma_dir).items():
                if row.get("vector_segment") == seg_id:
                    return {"collection": name, **row}
        except (sqlite3.Error, OSError, pickle.UnpicklingError, EOFError) as exc:
            return {"unavailable": str(exc)}
        return {"unavailable": "segment not listed in chroma.sqlite3"}

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
) -> list[dict[str, Any]]:
    """Restore torn segments now -- e.g. right after a writer died from a native fault."""
    guard = ChromaWriteGuard(chroma_dir, lock_timeout_seconds=lock_timeout_seconds)
    guard._reject_identity_conflict()  # pylint: disable=protected-access
    guard.require_not_quarantined()
    barrier = os.environ.get(_ADMISSION_BARRIER_ENV)
    if barrier:
        _wait_barrier(barrier)
    with _exclusive_flock(guard.lock_path, lock_timeout_seconds):
        guard.require_not_quarantined()
        return guard.reconcile()


def write_guard_enabled(cfg: Mapping[str, Any] | None) -> bool:
    """``[index] chroma_write_guard = false`` turns the guard off; it is on by default."""
    index = (cfg or {}).get("index")
    if not isinstance(index, Mapping):
        return True
    return index.get("chroma_write_guard", True) is not False
