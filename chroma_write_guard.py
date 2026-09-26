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

import fcntl
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


def chroma_system_cached(identifier: str) -> bool:
    """True when this process already holds a Chroma system for ``identifier``."""
    from chromadb.api.shared_system_client import SharedSystemClient

    return identifier in SharedSystemClient._identifier_to_system  # pylint: disable=protected-access


def note_system_created(identifier: str) -> None:
    """Record the on-disk saves a Chroma system about to be created will load.

    Call *before* constructing the client: Chroma loads segments lazily, so the
    system can only be newer than this record, never older.
    """
    with _VIEWS_LOCK:
        _SYSTEM_VIEWS[identifier] = store_signature(identifier)


def note_unguarded_write(identifier: str, before: dict[str, Signature]) -> None:
    """After a native write this process made without the guard.

    If the write saved, this process's system produced the files on disk, so it is
    not stale. If it did not save, leave the recorded view alone: any save another
    process made earlier is still unseen.
    """
    after = store_signature(identifier)
    if after != before:
        _set_system_view(identifier, after)


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
# The guard
# --------------------------------------------------------------------------------------


class ChromaWriteGuard:
    """Keeps a validated copy of each segment's last save and serialises native writes.

    State lives beside the store in ``<chroma_dir>.write-guard/``: the lock file,
    ``snapshots/<segment>/`` (the copies), ``events.jsonl`` and, when writes have been
    stopped, ``QUARANTINE.json``.
    """

    def __init__(
        self,
        chroma_dir: str | Path,
        *,
        lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.chroma_dir = Path(chroma_dir).expanduser()
        self.root = self.chroma_dir.parent / f"{self.chroma_dir.name}{GUARD_DIR_SUFFIX}"
        self.lock_path = self.root / "native-write.lock"
        self.snapshots = self.root / "snapshots"
        self.events_path = self.root / "events.jsonl"
        self.quarantine_path = self.root / "QUARANTINE.json"
        self.lock_timeout_seconds = lock_timeout_seconds

    @property
    def audit_path(self) -> Path:
        return self.root / "audit.json"

    # -- quarantine -------------------------------------------------------------------

    def quarantine_state(self) -> dict[str, Any] | None:
        try:
            return json.loads(self.quarantine_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as exc:
            return {"reason": f"unreadable quarantine record: {exc}"}

    def require_not_quarantined(self) -> None:
        state = self.quarantine_state()
        if state is not None:
            raise ChromaWriteQuarantinedError(
                f"chroma writes are quarantined: {state.get('reason')} "
                f"(segment {state.get('segment')}); see {self.quarantine_path}"
            )

    def clear_quarantine(self) -> bool:
        """Re-allow writes after a human repaired the index; False when none was set."""
        if self.quarantine_state() is None:
            return False
        self.quarantine_path.unlink(missing_ok=True)
        self._event("quarantine_cleared")
        return True

    def _quarantine(self, segment: str, reason: str, failures: tuple[str, ...], **extra: Any) -> NoReturn:
        self.root.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": _utc_now(),
            "segment": segment,
            "reason": reason,
            "failures": list(failures)[:20],
            "pid": os.getpid(),
            "to_clear": "repair the index, then run: python scripts/chroma_guard.py clear-quarantine",
            **extra,
        }
        _write_json_durable(self.quarantine_path, record)
        self._event("quarantined", segment=segment, reason=reason)
        raise ChromaWriteQuarantinedError(
            f"chroma writes quarantined: {reason} (segment {segment}); see {self.quarantine_path}"
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
        self.require_not_quarantined()
        with _exclusive_flock(self.lock_path, self.lock_timeout_seconds):
            self.require_not_quarantined()
            self.reconcile()
            before = store_signature(self.chroma_dir)
            if _synced_only(_system_view(identifier)) != _synced_only(before):
                reload_client()
                _set_system_view(identifier, before)
            try:
                yield
            except BaseException:
                self._after_write(identifier, before, system_trusted=False)
                raise
            self._after_write(identifier, before, system_trusted=True)

    def _after_write(self, identifier: str, before: dict[str, Signature], *, system_trusted: bool) -> None:
        after = store_signature(self.chroma_dir)
        # A failed native call leaves the in-process system's state unknown: reload next time.
        _set_system_view(identifier, after if system_trusted else None)
        for seg_id, seg in segment_dirs(self.chroma_dir).items():
            if before.get(seg_id) == after.get(seg_id):
                continue
            report = validate_segment(seg)
            if report.ok:
                self._refresh_snapshot(seg_id, seg, after[seg_id])  # logs only a first copy
                continue
            self._quarantine(
                seg_id,
                "this process's own save failed validation; not restoring the previous save "
                "because Chroma has already purged the records written since it",
                report.failures,
            )

    def reconcile(self) -> list[dict[str, Any]]:
        """Bring every live segment back to a validated save; the caller holds the lock."""
        events: list[dict[str, Any]] = []
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
                self._quarantine(seg_id, "live segment failed validation and no validated save exists", report.failures)
            events.append(self._restore(seg_id, seg, snapshot, report))
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
    ) -> dict[str, Any]:
        snap_dir, meta = snapshot
        snap_report = validate_segment(snap_dir)
        if not snap_report.ok:
            self._quarantine(
                seg_id,
                "live segment failed validation and its saved copy failed too",
                live_report.failures,
                snapshot_failures=list(snap_report.failures),
            )
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
            self._quarantine(seg_id, "restored segment failed validation", restored.failures)
        _write_json_durable(snap_dir / "SNAPSHOT.json", {**meta, "live_signature": segment_signature(seg)})
        census = self._census_for_segment(seg_id)
        event = self._event(
            "segment_restored",
            segment=seg_id,
            torn=list(live_report.failures)[:5],
            census=census,
        )
        if census.get("lost"):
            self._quarantine(
                seg_id,
                "restoring the last save left records without vectors",
                live_report.failures,
                census=census,
            )
        return event

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
        the audit (well under a second on the live store) instead of the audit
        reporting a torn read as corruption.  A busy lock records ``skipped``.  The
        result goes to ``audit.json`` for ``convmem doctor``.
        """
        result: dict[str, Any] = {"started": _utc_now(), "pid": os.getpid()}
        try:
            with _exclusive_flock(self.lock_path, lock_timeout_seconds):
                reports = [validate_segment(seg) for seg in segment_dirs(self.chroma_dir).values()]
                census = vector_census(self.chroma_dir)
        except TimeoutError as exc:
            result.update(status="skipped", reason=str(exc))
        except (sqlite3.Error, OSError, pickle.UnpicklingError, EOFError) as exc:
            result.update(status="error", reason=f"{type(exc).__name__}: {exc}")
        else:
            invalid = [r for r in reports if not r.ok]
            lost = sum(int(row["lost"]) for row in census.values())
            result.update(
                status="fail" if invalid or lost else "pass",
                segments=len(reports),
                invalid_segments={r.segment: list(r.failures)[:5] for r in invalid},
                lost=lost,
                vectors=sum(int(row["hnsw_ids"]) for row in census.values()),
                census=census,
            )
        result["ts"] = _utc_now()
        self.root.mkdir(parents=True, exist_ok=True)
        _write_json_durable(self.audit_path, result)
        self._event("audit", status=result["status"], lost=result.get("lost"))
        return result

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
    guard.require_not_quarantined()
    with _exclusive_flock(guard.lock_path, lock_timeout_seconds):
        return guard.reconcile()


def write_guard_enabled(cfg: Mapping[str, Any] | None) -> bool:
    """``[index] chroma_write_guard = false`` turns the guard off; it is on by default."""
    index = (cfg or {}).get("index")
    if not isinstance(index, Mapping):
        return True
    return index.get("chroma_write_guard", True) is not False
