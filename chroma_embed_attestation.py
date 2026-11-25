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
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chromadb.errors import NotFoundError

from chroma_embed_identity import (
    ATTESTATION_METHOD,
    ATTESTATION_SCHEMA,
    TIMESTAMP_FORMAT,
    AttestationError,
    CollectionAttestation,
    read_attestations,
    sidecar_path,
)
from chroma_readonly import (
    collection_config_metadata,
    collection_dimension,
    collection_ids,
    collection_uuid,
)
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
METHOD = ATTESTATION_METHOD

EmbedFn = Callable[[str], Sequence[float]]


@dataclass(frozen=True)
class SpotCheck:
    """What a re-embedding sample measured on one collection."""

    collection: str
    population: int
    sample_size: int
    dimension: int
    min_cosine: float
    mean_cosine: float
    seed: int


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
    _require_usable(left, "stored vector")
    _require_usable(right, "re-embedded vector")
    dot = math.fsum(a * b for a, b in zip(left, right))
    norm = math.sqrt(math.fsum(a * a for a in left)) * math.sqrt(math.fsum(b * b for b in right))
    score = dot / norm if norm else math.nan
    if not math.isfinite(score):
        raise AttestationError("cosine similarity is not finite")
    return score


def _sample_ids(ids: Sequence[str], sample_size: int | None, seed: int) -> list[str]:
    ordered = sorted(ids)
    if sample_size is None or len(ordered) <= sample_size:
        return ordered
    return sorted(random.Random(seed).sample(ordered, sample_size))


def spot_check(  # pylint: disable=too-many-arguments
    copy_dir: str | Path,
    name: str,
    embed: EmbedFn,
    *,
    sample_size: int | None = DEFAULT_SAMPLE_SIZE,
    seed: int = 0,
) -> SpotCheck:
    """Re-embed a reproducible sample of stored documents and compare to storage.

    ``sample_size=None`` checks every row. Opens ``copy_dir`` with a Chroma client
    (``open_chroma_for_verify``), so ``copy_dir`` must be a restore copy. Missing
    collections are never created.
    """
    ids = collection_ids(copy_dir, name)
    if not ids:
        raise AttestationError(f"{name}: collection has no vectors to check")
    if sample_size is not None and sample_size < min(MIN_SAMPLE_SIZE, len(ids)):
        raise AttestationError(
            f"{name}: sample of {sample_size} is below the minimum "
            f"{min(MIN_SAMPLE_SIZE, len(ids))}"
        )
    sample = _sample_ids(ids, sample_size, seed)
    # The restore-drill opener: get_collection only, so nothing is ever created.
    try:
        with contextlib.closing(open_chroma_for_verify(str(copy_dir))) as store:
            got = store._collection(name).get(  # pylint: disable=protected-access
                ids=sample, include=["embeddings", "documents"]
            )
    except NotFoundError as exc:
        raise AttestationError(f"{name}: the restore copy is incomplete: {exc}") from exc
    stored_ids = list(got["ids"])
    if sorted(stored_ids) != sample:
        raise AttestationError(f"{name}: could not read every sampled vector from the copy")
    documents = got["documents"]
    embeddings = got["embeddings"]
    scores: list[float] = []
    dimension = 0
    for index, doc_id in enumerate(stored_ids):
        document = documents[index]
        if not isinstance(document, str) or not document.strip():
            raise AttestationError(f"{name}: sampled item {doc_id!r} has no document to embed")
        stored = [float(x) for x in embeddings[index]]
        dimension = len(stored)
        scores.append(cosine(stored, [float(x) for x in embed(document)]))
    return SpotCheck(
        collection=name,
        population=len(ids),
        sample_size=len(scores),
        dimension=dimension,
        min_cosine=min(scores),
        mean_cosine=math.fsum(scores) / len(scores),
        seed=seed,
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
    try:
        root.stat()
    except FileNotFoundError:
        return found  # a directory that does not exist shares nothing
    except OSError as exc:
        raise AttestationError(f"cannot inspect {root} to prove it is separate: {exc}") from exc
    try:
        for directory, subdirectories, names in os.walk(root, followlinks=False, onerror=_raise):
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
            json.dump(payload, handle, indent=2, sort_keys=True)
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
    fd = os.open(path.with_name(path.name + ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
    try:
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
    _require_separate_copy(live, copy)

    read_attestations(live)  # refuse early, before any embedding, to build on a corrupt sidecar
    stamp = (now or datetime.now(timezone.utc)).strftime(TIMESTAMP_FORMAT)
    attested: dict[str, CollectionAttestation] = {}
    evidence: dict[str, dict[str, Any]] = {}
    skipped: dict[str, str] = {}

    for name in requested:
        live_uuid = collection_uuid(live, name)
        if live_uuid is None:
            if explicit or name == UNITS:
                raise AttestationError(f"{name}: the live store has no such collection")
            skipped[name] = "collection does not exist"
            continue
        if collection_config_metadata(live, name).get(EMBED_MODEL_KEY):
            skipped[name] = f"already records {EMBED_MODEL_KEY}; nothing to attest"
            continue
        if collection_uuid(copy, name) != live_uuid:
            raise AttestationError(f"{name}: the restore copy is not a copy of this collection")
        live_dim = collection_dimension(live, name)
        if live_dim is None or collection_dimension(copy, name) != live_dim:
            raise AttestationError(
                f"{name}: live and copy must record the same non-empty vector dimension"
            )
        _require_separate_copy(live, copy)  # again, right before a client opens the copy
        check = spot_check(copy, name, embed, sample_size=sample_size, seed=used_seed)
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
            _atomic_write_json(path, _encode(merged, {**kept, **evidence}))
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

    cfg = load_config(args.config)
    live_dir = args.live_chroma_dir or Path(cfg["index"]["chroma_dir"])
    models = cfg.get("models") or {}
    model = args.model or models.get("embed_model") or ""
    host = models.get("ollama_host") or ""
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
        )
    except AttestationError as exc:
        print(f"attestation refused: {exc}", file=sys.stderr)
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
