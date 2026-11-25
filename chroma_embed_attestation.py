"""Attest which embedding model made the vectors of collections that predate identity.

The live collections were created before the writer recorded
``convmem:embed_model``. Chroma ignores new metadata on an existing collection
and ``modify`` replaces the whole metadata dict (dropping ``hnsw:space``), and
CG2 hashes that metadata, so nothing here edits a collection. Instead the proof
is a sidecar file beside the Chroma directory (``chroma_embed_identity``).

The claim is only written after evidence:

1. The collection UUID and Chroma's own recorded dimension of the *restore copy*
   equal the live collection's, so the copy is the same collection.
2. A sample of stored documents is re-embedded with the claimed model and every
   re-embedded vector matches its stored vector (cosine at or above the
   threshold). A different model fails this by a wide margin. The sample size
   and seed are recorded, and a sample cannot rule out a minority of rows from
   another model (10 foreign rows in 1000 slip past a 50-row sample about 60% of
   the time), so ``--sample-size all`` checks every row.

The sample runs against a restic *restore copy* because reading stored vectors
needs a Chroma client, and the live directory must never be opened with one
(``Issues/read-tools-open-chroma-with-writing-client.md``). The live directory is
read only through SQLite ``mode=ro``. This module refuses a copy that is, or
overlaps, the live directory.

Operator steps (nothing here writes to the live store):

1. Restore the latest chroma snapshot to a scratch directory, for example with
   ``scripts/chroma_restore_drill.py --keep-run-dir`` (it restores a snapshot into a
   disposable run directory). ``--restore-copy`` is the restored directory that
   contains ``chroma.sqlite3``.
2. Dry run: ``python chroma_embed_attestation.py --restore-copy <dir> --sample-size all``.
   It performs every check and the embedding calls (the embedding service must be
   up) and writes nothing.
3. If the report looks right: the same command with ``--write``.
4. ``convmem doctor`` now reports ``attested legacy``. Once both collections pass,
   ``[index] require_embed_identity = true`` makes doctor FAIL on any collection that
   nothing proves, which is the fail-closed state. Strict accepts an attestation only
   if it checked every row, so run step 2 and 3 with ``--sample-size all`` before
   flipping it; a sampled attestation still passes in the default mode.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import math
import os
import random
import secrets
import sqlite3
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chromadb.errors import ChromaError, NotFoundError

from chroma_embed_identity import (
    ATTESTATION_METHOD,
    ATTESTATION_SCHEMA,
    TIMESTAMP_FORMAT,
    AttestationError,
    CollectionAttestation,
    parse_attestations,
    read_attestations,
    sidecar_path,
)
from chroma_readonly import (
    collection_change_fingerprint,
    collection_dimension,
    collection_identity_facts_many,
    collection_uuid,
    may_create_wal_files,
)
from chroma_write_guard import ChromaStaleSystemError
from chroma_store import (
    EMBED_MODEL_KEY,
    SUMMARIES,
    UNITS,
    normalize_embed_model,
    open_chroma_for_verify,
)

DEFAULT_SAMPLE_SIZE = 50
MIN_SAMPLE_SIZE = 10
DEFAULT_THRESHOLD = 0.99
# Chroma's get() binds one SQL variable per id; SQLite caps those (32766 on current builds).
READ_BATCH = 500
# A failed embedding is retried this many times (backoff doubling from EMBED_BACKOFF seconds)
# before the run is refused, naming the collection and row. A census can be tens of thousands
# of calls; one transient error must not discard it, and a permanent one must say where.
EMBED_RETRIES = 2
EMBED_BACKOFF = 0.5
METHOD = ATTESTATION_METHOD

EmbedFn = Callable[[str], Sequence[float]]
ProgressFn = Callable[[str, int, int], None]


@dataclass(frozen=True)
class SpotCheck:  # pylint: disable=too-many-instance-attributes
    """What a re-embedding sample measured on one collection."""

    collection: str
    population: int
    sample_size: int
    dimension: int
    min_cosine: float
    mean_cosine: float
    seed: int
    fingerprint: tuple[int, int, int, int] | None = None  # of the copy when this collection was done


@dataclass(frozen=True)
class AttestationReport:
    """Outcome of one attestation run."""

    path: Path
    attested: dict[str, CollectionAttestation]
    evidence: dict[str, dict[str, Any]]
    skipped: dict[str, str]
    written: bool


def _require_usable(vector: Sequence[float], what: str) -> None:
    if not all(math.isfinite(x) for x in vector):
        raise AttestationError(f"{what} has a non-finite component")
    if not any(vector):
        raise AttestationError(f"{what} is all zeros")


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity. Anything that is not a real measurement is an error.

    Vectors of different length, non-finite components and zero vectors are
    refused rather than scored, so no run can publish a result that measured
    nothing (a NaN compares false against every threshold).
    """
    if len(left) != len(right):
        raise AttestationError(
            f"re-embedded vector has {len(right)} dimensions, stored vector has {len(left)}"
        )
    # Unit vectors first: squaring tiny components underflows to zero and squaring huge ones
    # overflows, either of which turns a real measurement into an impossible score.
    left_unit, right_unit = _unit(left, "stored vector"), _unit(right, "re-embedded vector")
    score = math.fsum(a * b for a, b in zip(left_unit, right_unit))
    if not math.isfinite(score) or abs(score) > 1.0 + 1e-9:
        raise AttestationError(f"cosine similarity {score!r} is not a valid measurement")
    return max(-1.0, min(1.0, score))


def _unit(vector: Sequence[float], what: str) -> list[float]:
    _require_usable(vector, what)
    # Divide by the largest component first: hypot of subnormal components rounds the length
    # to one of them, which would turn [5e-324, 5e-324] into [1, 1] instead of a unit vector.
    peak = max(abs(x) for x in vector)
    scaled = [x / peak for x in vector]
    length = math.hypot(*scaled)
    if not math.isfinite(length) or length == 0.0:
        raise AttestationError(f"{what} has no usable length")
    return [x / length for x in scaled]


def _sample_ids(ids: Sequence[str], sample_size: int | None, seed: int) -> list[str]:
    ordered = sorted(ids)
    if sample_size is None or len(ordered) <= sample_size:
        return ordered
    return sorted(random.Random(seed).sample(ordered, sample_size))


def _embed_row(embed: EmbedFn, name: str, doc_id: str, document: str) -> list[float]:
    """Embed one stored document; refuse with the collection and row if the provider keeps failing."""
    for attempt in range(EMBED_RETRIES + 1):
        try:
            return [float(x) for x in embed(document)]
        except (Exception, SystemExit) as exc:  # pylint: disable=broad-exception-caught
            if attempt == EMBED_RETRIES:
                raise AttestationError(
                    f"{name}: embedding row {doc_id!r} failed after {attempt + 1} attempts: {exc!r}"
                ) from exc
            time.sleep(EMBED_BACKOFF * 2**attempt)
    raise AssertionError("unreachable")  # pragma: no cover


def spot_check(  # pylint: disable=too-many-arguments,too-many-locals
    copy_dir: str | Path,
    name: str,
    embed: EmbedFn,
    *,
    sample_size: int | None = DEFAULT_SAMPLE_SIZE,
    seed: int = 0,
    before_open: Callable[[], None] | None = None,
    progress: ProgressFn | None = None,
    fail_below: float | None = None,
    expected_uuid: str | None = None,
) -> SpotCheck:
    """Re-embed a reproducible sample of stored documents and compare to storage.

    ``sample_size=None`` checks every row. Opens ``copy_dir`` with a Chroma client
    (``open_chroma_for_verify``), so ``copy_dir`` must be a restore copy. Missing
    collections are never created. ``before_open`` runs immediately before the client
    opens, so a guard there leaves the least room for the directory to change after it.

    The rows to check are listed by the opened collection, not read from SQLite beforehand:
    a restore can hold log records Chroma only replays when it opens, and a census that
    missed them would vouch for fewer rows than the collection holds. Rows are then read,
    embedded and scored one batch at a time, so memory does not grow with the collection;
    ``progress(name, done, total)`` is called after each batch. With ``fail_below`` the run
    stops at the first row under that cosine and names it. With ``expected_uuid`` the opened
    collection must be that collection: the UUID was checked through SQLite before the
    client opened the path, and the directory can change in between, so the handle that is
    scored is compared with it.
    """
    if before_open is not None:
        before_open()
    scores: list[float] = []
    scored_ids: list[str] = []
    dimension = 0
    # The restore-drill opener: get_collection only, so nothing is ever created.
    try:
        with contextlib.closing(open_chroma_for_verify(str(copy_dir))) as store:
            # A system this process already holds for the path can serve an index older than the
            # disk (another process may have updated a vector since). The repo's own protocol for
            # "show me the disk": drop the system and load it again; if another client in this
            # process still holds one, that view cannot be trusted and nothing is scored.
            try:
                store._reload_client()  # pylint: disable=protected-access
            except ChromaStaleSystemError as exc:
                raise AttestationError(
                    f"{name}: this process already holds a Chroma client for the restore copy, whose cached "
                    "index can differ from the disk; run the attestation in a fresh process"
                ) from exc
            collection = store._collection(name)  # pylint: disable=protected-access
            if expected_uuid is not None and str(collection.id) != expected_uuid:
                raise AttestationError(
                    f"{name}: the restore copy that was opened is collection {collection.id}, not "
                    f"{expected_uuid}; it changed after it was checked, so nothing was scored"
                )
            ids = sorted(collection.get(include=[])["ids"])
            population = collection.count()
            if len(ids) != population:
                raise AttestationError(
                    f"{name}: the copy lists {len(ids)} rows but counts {population}"
                )
            if not ids:
                raise AttestationError(f"{name}: collection has no vectors to check")
            if sample_size is not None and sample_size < min(MIN_SAMPLE_SIZE, len(ids)):
                raise AttestationError(
                    f"{name}: sample of {sample_size} is below the minimum "
                    f"{min(MIN_SAMPLE_SIZE, len(ids))}"
                )
            sample = _sample_ids(ids, sample_size, seed)
            before = collection_change_fingerprint(copy_dir, name)
            for start in range(0, len(sample), READ_BATCH):
                batch = sample[start : start + READ_BATCH]
                got = collection.get(ids=batch, include=["embeddings", "documents"])
                if sorted(got["ids"]) != batch:
                    raise AttestationError(f"{name}: could not read every sampled vector from the copy")
                for doc_id, document, vector in zip(got["ids"], got["documents"], got["embeddings"]):
                    if not isinstance(document, str) or not document.strip():
                        raise AttestationError(f"{name}: sampled item {doc_id!r} has no document to embed")
                    values = [float(x) for x in vector]
                    dimension = len(values)
                    embedded = _embed_row(embed, name, doc_id, document)
                    try:
                        score = cosine(values, embedded)
                    except AttestationError as exc:
                        raise AttestationError(f"{name}: row {doc_id!r}: {exc}") from exc
                    if fail_below is not None and score < fail_below:
                        raise AttestationError(
                            f"{name}: re-embedding with the claimed model does not reproduce the stored "
                            f"vector of row {doc_id!r} (cosine {score:.4f} < {fail_below}); "
                            "the claimed model is not the model that made it"
                        )
                    scores.append(score)
                    scored_ids.append(doc_id)
                if progress is not None:
                    progress(name, len(scores), len(sample))
            if sample_size is None and sorted(scored_ids) != ids:
                raise AttestationError(f"{name}: the census did not cover every row the copy holds")
            # Batches are read one after another, so a second writer on this copy could repair a row
            # not yet read and break one already scored while the UUID and the ids stay the same.
            # A restore copy must be private; if it changed, what was scored is not one state.
            after = collection_change_fingerprint(copy_dir, name)
            if sorted(collection.get(include=[])["ids"]) != ids or after != before:
                raise AttestationError(
                    f"{name}: the restore copy changed while it was being checked; nothing was attested. "
                    "Check a private copy that no other process writes to."
                )
    except NotFoundError as exc:
        raise AttestationError(f"{name}: the restore copy is incomplete: {exc}") from exc
    except ChromaError as exc:  # a copy Chroma itself cannot read (e.g. damaged collection config)
        raise AttestationError(
            f"{name}: the restore copy cannot be read by Chroma: {type(exc).__name__}: {exc}"
        ) from exc
    except BaseException as exc:  # pylint: disable=broad-exception-caught
        if type(exc).__name__ == "PanicException":  # pyo3 maps a Rust panic to a BaseException
            raise AttestationError(
                f"{name}: Chroma's native layer failed on the restore copy: {type(exc).__name__}: {exc}"
            ) from exc
        raise
    return SpotCheck(
        collection=name,
        population=population,
        sample_size=len(scores),
        dimension=dimension,
        min_cosine=min(scores),
        mean_cosine=math.fsum(scores) / len(scores),
        seed=seed,
        fingerprint=after,
    )


def _overlaps(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _raise(exc: OSError) -> None:
    raise exc


def _file_identities(root: Path, *, forbid_symlinks: bool) -> set[tuple[int, int]]:
    """(device, inode) of every file under ``root``; any doubt is an error.

    A hardlinked or bind-mounted "copy" (``cp -al``) has other paths but the same
    inodes, and a client writing through it would modify the live files, so every
    file is compared, not just the SQLite one. A directory that cannot be listed or
    a file that cannot be stat'ed refuses the copy instead of being skipped.
    """
    found: set[tuple[int, int]] = set()
    visited: set[tuple[int, int]] = set()
    try:
        root.stat()
    except FileNotFoundError:
        return found  # a directory that does not exist shares nothing
    except OSError as exc:
        raise AttestationError(f"cannot inspect {root} to prove it is separate: {exc}") from exc
    try:
        # The live side follows links: a file reached through a linked directory is still
        # a live file. The copy side forbids links outright, so it never needs to follow.
        for directory, subdirectories, names in os.walk(
            root, followlinks=not forbid_symlinks, onerror=_raise
        ):
            here = os.stat(directory)
            if (here.st_dev, here.st_ino) in visited:
                subdirectories[:] = []  # a link cycle: already walked
                continue
            visited.add((here.st_dev, here.st_ino))
            found.add((here.st_dev, here.st_ino))  # an empty shared directory is shared storage
            for entry in (*subdirectories, *names):
                path = Path(directory, entry)
                if forbid_symlinks and path.is_symlink():
                    raise AttestationError(f"the restore copy contains a symlink: {path}")
                if entry in names:
                    info = path.stat()
                    found.add((info.st_dev, info.st_ino))
    except OSError as exc:
        raise AttestationError(f"cannot inspect {root} to prove it is separate: {exc}") from exc
    return found


def _require_separate_copy(live_dir: Path, copy_dir: Path) -> None:
    live, copy = live_dir.expanduser().resolve(), copy_dir.expanduser().resolve()
    if _overlaps(live, copy) or (
        _file_identities(live, forbid_symlinks=False) & _file_identities(copy, forbid_symlinks=True)
    ):
        raise AttestationError(
            "the restore copy must be a separate directory with its own files; "
            "refusing to open the live Chroma directory with a client"
        )


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


@contextlib.contextmanager
def _sidecar_lock(path: Path):
    """Serialise read-merge-replace so two attestations cannot drop each other's entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(
            path.with_name(path.name + ".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
    except OSError as exc:  # includes ELOOP: a symlink planted at the lock path
        raise AttestationError(f"cannot take the sidecar lock: {exc}") from exc
    try:  # from here the descriptor is always closed, whatever fails
        try:
            os.fchmod(fd, 0o600)  # the mode argument above only applies when the file is created
        except OSError as exc:
            raise AttestationError(f"cannot take the sidecar lock: {exc}") from exc
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)  # closing the descriptor releases the lock


def _encode(
    attested: Mapping[str, CollectionAttestation], evidence: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema": ATTESTATION_SCHEMA,
        "collections": {
            name: {
                "collection_uuid": item.collection_uuid,
                "dimension": item.dimension,
                "embed_model": item.embed_model,
                "evidence": dict(evidence[name]),
            }
            for name, item in sorted(attested.items())
        },
    }


def _validated_threshold(threshold: float) -> float:
    if isinstance(threshold, bool) or not math.isfinite(threshold) or not 0.0 < threshold <= 1.0:
        raise AttestationError(f"threshold must be a finite number in (0, 1], got {threshold!r}")
    return float(threshold)


def attest_collections(  # pylint: disable=too-many-arguments,too-many-locals
    live_dir: str | Path,
    copy_dir: str | Path,
    *,
    model: str,
    embed: EmbedFn,
    names: Sequence[str] | None = None,
    sample_size: int | None = DEFAULT_SAMPLE_SIZE,
    threshold: float = DEFAULT_THRESHOLD,
    seed: int | None = None,
    note: str = "",
    write: bool = False,
    now: datetime | None = None,
    progress: ProgressFn | None = None,
) -> AttestationReport:
    """Verify, and with ``write=True`` record, the model behind unmarked collections.

    Nothing is written unless every requested collection passes. ``names=None``
    means ``knowledge_units`` plus ``conversation_summaries`` when it exists; a name
    given explicitly must exist. A collection that already records a model is
    skipped, never relabelled. ``sample_size=None`` checks every row; ``seed=None``
    draws a fresh seed, which is recorded.
    """
    claimed = normalize_embed_model(model)
    if claimed is None:
        raise AttestationError("a non-empty embed model is required")
    threshold = _validated_threshold(threshold)
    used_seed = secrets.randbits(32) if seed is None else int(seed)
    explicit = names is not None
    requested = tuple(dict.fromkeys(names if names is not None else (UNITS, SUMMARIES)))
    live, copy = Path(live_dir).expanduser(), Path(copy_dir).expanduser()
    if may_create_wal_files(live):
        # SQLite may create -wal/-shm beside a WAL database even for a read-only open; the live
        # directory must stay untouched, so refuse instead of reading it. Anything that is not
        # verifiably a plain rollback-journal file (WAL, mixed or unreadable header) counts.
        raise AttestationError(
            "the live database is not verifiably a rollback-journal SQLite file (WAL mode, an "
            "inconsistent or an unreadable header): a read-only open could create -wal/-shm files "
            "in the live directory, so it is not read"
        )
    _require_separate_copy(live, copy)

    read_attestations(live)  # refuse early, before any embedding, to build on a corrupt sidecar
    stamp = (now or datetime.now(timezone.utc)).strftime(TIMESTAMP_FORMAT)
    attested: dict[str, CollectionAttestation] = {}
    evidence: dict[str, dict[str, Any]] = {}
    skipped: dict[str, str] = {}
    fingerprints: dict[str, tuple[int, int, int, int] | None] = {}

    # The live catalog is read once, in one read transaction, and never again: one moment for every
    # collection, and one short opening of a directory this command promises to leave untouched.
    live_facts = collection_identity_facts_many(live, requested)
    for name in requested:
        facts = live_facts[name]
        if isinstance(facts, Exception):
            raise AttestationError(
                f"{name}: cannot read the live catalog: {type(facts).__name__}: {facts}"
            ) from facts
        live_uuid = facts.uuid
        if live_uuid is None:
            if explicit or name == UNITS:
                raise AttestationError(f"{name}: the live store has no such collection")
            skipped[name] = "collection does not exist"
            continue
        if facts.metadata.get(EMBED_MODEL_KEY):
            skipped[name] = f"already records {EMBED_MODEL_KEY}; nothing to attest"
            continue
        if collection_uuid(copy, name) != live_uuid:
            raise AttestationError(f"{name}: the restore copy is not a copy of this collection")
        live_dim = facts.dimension
        if live_dim is None or collection_dimension(copy, name) != live_dim:
            raise AttestationError(
                f"{name}: live and copy must record the same non-empty vector dimension"
            )
        check = spot_check(
            copy,
            name,
            embed,
            sample_size=sample_size,
            seed=used_seed,
            # checked again right before a client opens the copy
            before_open=lambda: _require_separate_copy(live, copy),
            progress=progress,
            fail_below=threshold,
            expected_uuid=live_uuid,
        )
        if check.dimension != live_dim:
            raise AttestationError(
                f"{name}: stored vectors have {check.dimension} dimensions, Chroma recorded {live_dim}"
            )
        if check.min_cosine < threshold:
            raise AttestationError(
                f"{name}: re-embedding with {claimed!r} does not reproduce the stored vectors "
                f"(minimum cosine {check.min_cosine:.4f} < {threshold}); "
                "the claimed model is not the model that made them"
            )
        fingerprints[name] = check.fingerprint
        attested[name] = CollectionAttestation(
            name=name,
            collection_uuid=live_uuid,
            dimension=live_dim,
            embed_model=claimed,
            attested_at=stamp,
            sample_size=check.sample_size,
            population=check.population,
        )
        evidence[name] = {
            "method": METHOD,
            "attested_at": stamp,
            "population": check.population,
            "sample_size": check.sample_size,
            "seed": check.seed,
            "threshold": threshold,
            "min_cosine": round(check.min_cosine, 6),
            "mean_cosine": round(check.mean_cosine, 6),
            "note": note,
        }

    # Each census only guards its own collection while it runs. Once every collection is done, look
    # at each one again: a writer that changed an already-checked collection while a later one was
    # being checked would otherwise leave a sidecar describing no single state of the copy.
    for name, expected in fingerprints.items():
        if collection_change_fingerprint(copy, name) != expected:
            raise AttestationError(
                f"{name}: the restore copy changed after it was checked, while another collection was "
                "being checked; nothing was attested. Check a private copy that no other process writes to."
            )

    if not attested:
        raise AttestationError(
            "nothing to attest: " + "; ".join(f"{k}: {v}" for k, v in sorted(skipped.items()))
        )

    path = sidecar_path(live)
    written = False
    if write:
        # The sampling above is slow; another attestation may have finished meanwhile.
        # Read what is on disk only now, under the lock, and merge into that.
        with _sidecar_lock(path):
            current = read_attestations(live)
            merged = {**current, **attested}
            kept = _existing_evidence(path, set(current) - set(attested))
            payload = _encode(merged, {**kept, **evidence})
            # What is written must be what doctor will read; refuse before replacing a good file.
            parse_attestations(json.loads(json.dumps(payload, allow_nan=False)))
            _atomic_write_json(path, payload)
        written = True
    return AttestationReport(path, attested, evidence, skipped, written)


def _existing_evidence(path: Path, names: set[str]) -> dict[str, dict[str, Any]]:
    """Carry the evidence of untouched entries forward verbatim."""
    if not names or not path.is_file():
        return {}
    collections = json.loads(path.read_text(encoding="utf-8")).get("collections", {})
    return {name: dict(collections[name].get("evidence") or {}) for name in names}


def _ollama_embedder(model: str, host: str) -> EmbedFn:
    from llm import ollama_embed

    def embed(text: str) -> Sequence[float]:
        return ollama_embed(text, model, host)

    return embed


def _sample_size_arg(value: str) -> int | None:
    if value.strip().lower() == "all":
        return None
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer or 'all'") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer or 'all'")
    return number


def _threshold_arg(value: str) -> float:
    try:
        return _validated_threshold(float(value))
    except (ValueError, AttestationError) as exc:
        raise argparse.ArgumentTypeError("must be a finite number in (0, 1]") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Attest the embedding model behind legacy (unmarked) collections.",
        epilog="Dry run unless --write is given. The restore copy must be a separate directory.",
    )
    parser.add_argument("--restore-copy", required=True, type=Path, help="restic restore of chroma/")
    parser.add_argument("--config", type=Path, default=None, help="config.toml (default: standard)")
    parser.add_argument("--live-chroma-dir", type=Path, default=None, help="default: index.chroma_dir")
    parser.add_argument("--model", default=None, help="model to attest (default: models.embed_model)")
    parser.add_argument(
        "--sample-size",
        type=_sample_size_arg,
        default=DEFAULT_SAMPLE_SIZE,
        help="documents to re-embed, or 'all' to check every row (default: %(default)s)",
    )
    parser.add_argument("--threshold", type=_threshold_arg, default=DEFAULT_THRESHOLD)
    parser.add_argument("--seed", type=int, default=None, help="default: random, and recorded")
    parser.add_argument("--note", default="", help="free text stored with the evidence")
    parser.add_argument("--write", action="store_true", help="write the sidecar (default: dry run)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from config import load_config

    try:
        cfg = load_config(args.config)
        live_dir = args.live_chroma_dir or Path(cfg["index"]["chroma_dir"])
        models = cfg.get("models") or {}
        if not isinstance(models, dict):
            raise ValueError("[models] must be a table")
        model = args.model or models.get("embed_model") or ""
        host = models.get("ollama_host") or ""
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:  # missing or malformed config
        print(f"attestation refused: cannot use the configuration: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    def show(name: str, done: int, total: int) -> None:
        if done == total or done % 2000 == 0:
            print(f"  {name}: {done}/{total} rows checked", file=sys.stderr, flush=True)

    try:
        report = attest_collections(
            live_dir,
            args.restore_copy,
            model=model,
            embed=_ollama_embedder(str(model), str(host)),
            sample_size=args.sample_size,
            threshold=args.threshold,
            seed=args.seed,
            note=args.note,
            write=args.write,
            progress=show,
        )
    except AttestationError as exc:
        print(f"attestation refused: {exc}", file=sys.stderr)
        return 2
    except (sqlite3.Error, OSError, ChromaError) as exc:  # an unreadable or damaged store
        print(f"attestation refused: cannot read a store: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for name, item in sorted(report.attested.items()):
        ev = report.evidence[name]
        print(
            f"{name}: model={item.embed_model!r} dimension={item.dimension} "
            f"sample={ev['sample_size']}/{ev['population']} seed={ev['seed']} "
            f"min_cosine={ev['min_cosine']} mean_cosine={ev['mean_cosine']}"
        )
        if ev["sample_size"] < ev["population"]:
            print(
                f"  note: {ev['population'] - ev['sample_size']} rows were not re-embedded; "
                "a sample cannot rule out a minority from another model (use --sample-size all)"
            )
    for name, why in sorted(report.skipped.items()):
        print(f"{name}: skipped ({why})")
    print(f"{'wrote' if report.written else 'dry run, would write'} {report.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
