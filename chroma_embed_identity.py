"""Which embedding model made a collection's vectors: what it says, what was attested.

Read side only, used by ``convmem doctor``. Collections created by the
production writer record ``convmem:embed_model`` themselves. Collections that
predate that cannot be relabelled in place (Chroma ignores new metadata on an
existing collection, and ``modify`` would drop ``hnsw:space``), so an operator
can instead *attest* them in a sidecar file that sits next to the Chroma
directory, never inside it. ``chroma_embed_attestation`` writes that file only
after re-embedding a sample of real documents on a restore copy.

Everything here is read-only: collection metadata, the UUID and Chroma's own
vector dimension come from SQLite ``mode=ro`` (``chroma_readonly``), and the
sidecar is plain JSON. No Chroma client is opened and no embedding provider is
called.

The sidecar is an operator's claim plus evidence, not a cryptographic proof. It
binds the claim to the collection UUID and to the dimension Chroma recorded, so
a replaced or re-shaped collection stops matching it.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from chroma_readonly import collection_identity_facts
from chroma_store import (
    EMBED_MODEL_KEY,
    SUMMARIES,
    UNITS,
    normalize_embed_model,
)
from chroma_embed_model_names import same_embed_model

EMBED_DIMENSIONS_KEY = "convmem:embed_dimensions"
ATTESTATION_SCHEMA = "convmem.chroma-embed-attestation.v1"
ATTESTATION_METHOD = "reembed-spot-check-v1"
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# round(cosine, 6) is what the writer stores; allow that much slack when re-checking.
_SCORE_SLACK = 1e-6

PASS = "pass"
WARN = "warn"
FAIL = "fail"
_SEVERITY = {PASS: 0, WARN: 1, FAIL: 2}


class AttestationError(ValueError):
    """The attestation sidecar is unreadable, malformed or unusable."""


@dataclass(frozen=True)
class CollectionAttestation:  # pylint: disable=too-many-instance-attributes
    """An operator's claim about one collection, bound to what Chroma recorded."""

    name: str
    collection_uuid: str
    dimension: int
    embed_model: str
    attested_at: str | None = None
    sample_size: int | None = None
    population: int | None = None
    min_cosine: float | None = None
    threshold: float | None = None


@dataclass(frozen=True)
class IdentityVerdict:
    status: str  # PASS, WARN or FAIL
    detail: str


def sidecar_path(chroma_dir: str | Path) -> Path:
    """Where the attestation for ``chroma_dir`` lives: beside it, never inside it."""
    # abspath, not resolve(): "." or a relative spelling must still land *beside* the
    # directory, and a symlinked chroma dir keeps its sidecar next to the link.
    base = Path(os.path.abspath(Path(chroma_dir).expanduser()))
    if not base.name:
        raise AttestationError("a sidecar cannot be placed beside the filesystem root")
    return base.parent / f"{base.name}.embed-attestation.json"


def _as_dimension(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("not an integer")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
    else:
        raise ValueError("not an integer")
    if number <= 0:
        raise ValueError("not positive")
    return number


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AttestationError(f"evidence {label} must be a positive integer")
    return value


def _score(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AttestationError(f"evidence {label} must be a number")
    try:
        number = float(value)
    except OverflowError as exc:  # a JSON integer too large for a float
        raise AttestationError(f"evidence {label} is out of range") from exc
    if not math.isfinite(number) or abs(number) > 1.0 + _SCORE_SLACK:
        raise AttestationError(f"evidence {label} must be a finite cosine, got {value!r}")
    return number


def _parse_evidence(name: str, evidence: object) -> tuple[str, int, int, float, float]:
    """Check that the evidence is what the attestation tool writes; return what to show.

    A sidecar with no evidence, or evidence that does not even reach its own
    threshold, is a hand-written claim and does not count.
    """
    if not isinstance(evidence, Mapping):
        raise AttestationError(f"{name}: missing evidence")
    try:
        if evidence.get("method") != ATTESTATION_METHOD:
            raise AttestationError(f"evidence method must be {ATTESTATION_METHOD!r}")
        stamp = evidence.get("attested_at")
        try:
            datetime.strptime(stamp, TIMESTAMP_FORMAT)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise AttestationError("evidence attested_at must be a UTC timestamp") from exc
        population = _count(evidence.get("population"), "population")
        sample = _count(evidence.get("sample_size"), "sample_size")
        if sample > population:
            raise AttestationError("evidence sample_size exceeds its population")
        threshold = _score(evidence.get("threshold"), "threshold")
        if not 0.0 < threshold <= 1.0 + _SCORE_SLACK:
            raise AttestationError("evidence threshold must be in (0, 1]")
        lowest = _score(evidence.get("min_cosine"), "min_cosine")
        mean = _score(evidence.get("mean_cosine"), "mean_cosine")
        if lowest + _SCORE_SLACK < threshold:
            raise AttestationError("evidence min_cosine is below its own threshold")
        if mean + _SCORE_SLACK < lowest or (sample == 1 and abs(mean - lowest) > 2 * _SCORE_SLACK):
            raise AttestationError("evidence mean_cosine contradicts its min_cosine")
    except AttestationError as exc:
        raise AttestationError(f"{name}: {exc}") from exc
    return stamp, sample, population, threshold, lowest


def parse_attestations(payload: object) -> dict[str, CollectionAttestation]:
    """Validate a decoded sidecar. Anything unexpected raises, never half-loads."""
    if not isinstance(payload, Mapping) or payload.get("schema") != ATTESTATION_SCHEMA:
        raise AttestationError(f"not a {ATTESTATION_SCHEMA} document")
    collections = payload.get("collections")
    if not isinstance(collections, Mapping):
        raise AttestationError("'collections' must be an object")
    parsed: dict[str, CollectionAttestation] = {}
    for name, entry in collections.items():
        if not isinstance(name, str) or not isinstance(entry, Mapping):
            raise AttestationError("each collection entry must be an object")
        uuid = entry.get("collection_uuid")
        model = normalize_embed_model(entry.get("embed_model"))
        if not isinstance(uuid, str) or not uuid.strip():
            raise AttestationError(f"{name}: missing collection_uuid")
        if model is None:
            raise AttestationError(f"{name}: missing embed_model")
        try:
            dimension = _as_dimension(entry.get("dimension"))
        except ValueError as exc:
            raise AttestationError(f"{name}: dimension is {exc}") from exc
        stamp, sample, population, threshold, lowest = _parse_evidence(name, entry.get("evidence"))
        parsed[name] = CollectionAttestation(
            name=name,
            collection_uuid=uuid.strip(),
            dimension=dimension,
            embed_model=model,
            attested_at=stamp,
            sample_size=sample,
            population=population,
            min_cosine=lowest,
            threshold=threshold,
        )
    return parsed


def _reject_constant(token: str) -> object:
    raise ValueError(f"{token} is not valid in an attestation")


def read_attestations(chroma_dir: str | Path) -> dict[str, CollectionAttestation]:
    """Attestations for ``chroma_dir``; no sidecar means none. Corrupt raises."""
    path = sidecar_path(chroma_dir)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        raise AttestationError(f"cannot read {path.name}: {exc}") from exc
    try:
        payload = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:  # nesting deep enough overflows the parser
        raise AttestationError(f"{path.name} is not valid JSON: {exc}") from exc
    try:
        return parse_attestations(payload)
    except AttestationError:
        raise
    except (ValueError, TypeError, AttributeError, ArithmeticError, RecursionError) as exc:
        raise AttestationError(f"{path.name} is malformed: {exc!r}") from exc


def _recorded_dimension(meta: Mapping[str, Any]) -> int | None:
    raw = meta.get(EMBED_DIMENSIONS_KEY)
    if raw is None:
        return None
    return _as_dimension(raw)


def _judge_recorded(
    meta: Mapping[str, Any],
    stored_model: str,
    chroma_dimension: int | None,
    configured_model: str,
) -> IdentityVerdict:
    if configured_model and not same_embed_model(stored_model, configured_model):
        return IdentityVerdict(
            FAIL,
            f"embed model mismatch: collection={stored_model!r} config={configured_model!r}",
        )
    try:
        recorded = _recorded_dimension(meta)
    except ValueError as exc:
        return IdentityVerdict(
            FAIL, f"recorded {EMBED_DIMENSIONS_KEY}={meta.get(EMBED_DIMENSIONS_KEY)!r} is {exc}"
        )
    # An unknown Chroma dimension means no vector has been stored yet, so a recorded
    # dimension has nothing to contradict; it is only a mismatch when both are known.
    if recorded is not None and chroma_dimension is not None and recorded != chroma_dimension:
        return IdentityVerdict(
            FAIL, f"embed dimension mismatch: recorded={recorded} chroma={chroma_dimension}"
        )
    detail = f"collection embed_model={stored_model!r}"
    if recorded is not None:
        detail += f" dimensions={recorded!r}"
    return IdentityVerdict(PASS, detail)


def _covers_every_row(attestation: CollectionAttestation) -> bool:
    return (
        attestation.sample_size is not None
        and attestation.population is not None
        and attestation.sample_size >= attestation.population
    )


def _judge_attestation(
    attestation: CollectionAttestation,
    chroma_dimension: int,
    configured_model: str,
    strict: bool,
) -> IdentityVerdict:
    """The attestation applies to this very collection; is it still true?

    Strict mode accepts only a full check: a sample cannot rule out a minority of
    rows from another model, and strict is the setting that claims there are none.
    """
    if attestation.dimension != chroma_dimension:
        return IdentityVerdict(
            FAIL,
            f"attested dimension {attestation.dimension} != collection dimension "
            f"{chroma_dimension}",
        )
    if configured_model and not same_embed_model(attestation.embed_model, configured_model):
        return IdentityVerdict(
            FAIL,
            f"attested embed model mismatch: attested={attestation.embed_model!r} "
            f"config={configured_model!r}",
        )
    if strict and not _covers_every_row(attestation):
        return IdentityVerdict(
            FAIL,
            f"attested legacy embed_model={attestation.embed_model!r} covers "
            f"{attestation.sample_size} of {attestation.population} rows; "
            "require_embed_identity needs a full check "
            "(re-run chroma_embed_attestation with --sample-size all)",
        )
    when = f" on {attestation.attested_at}" if attestation.attested_at else ""
    coverage = ""
    if attestation.sample_size and attestation.population:
        measured = ""
        if attestation.min_cosine is not None and attestation.threshold is not None:
            measured = f", min cosine {attestation.min_cosine:.4f}, threshold {attestation.threshold}"
        coverage = (
            f" (restore copy at attestation time: sampled {attestation.sample_size} of "
            f"{attestation.population} rows{measured})"
        )
    return IdentityVerdict(
        PASS,
        f"attested legacy embed_model={attestation.embed_model!r} "
        f"dimensions={attestation.dimension!r}{when}{coverage}",
    )


def _judge_unattested(configured_model: str, reason: str, strict: bool) -> IdentityVerdict:
    if strict:
        return IdentityVerdict(
            FAIL,
            f"collection metadata lacks {EMBED_MODEL_KEY} and nothing attests it "
            f"({reason}; configured={configured_model!r}; require_embed_identity is on)",
        )
    return IdentityVerdict(
        WARN,
        f"WARN: legacy collection metadata lacks {EMBED_MODEL_KEY} "
        f"(configured={configured_model!r}; shadow stores must set metadata; {reason})",
    )


def judge_collection(  # pylint: disable=too-many-arguments
    *,
    meta: Mapping[str, Any],
    uuid: str,
    chroma_dimension: int | None,
    attestation: CollectionAttestation | None,
    attestation_error: str | None,
    configured_model: str,
    strict: bool,
    row_count: int | None = None,
) -> IdentityVerdict:
    """Decide one collection's identity state from facts already read.

    Pure: no I/O. States, in order:

    * no metadata, no dimension and no trace of any row: nothing to judge yet, WARN.
      (A collection that holds rows but lost its metadata is unproven, like any other.)
    * records a model: PASS if it matches the configuration and any recorded
      dimension matches Chroma's own; FAIL otherwise.
    * records no model (including empty metadata on a collection that holds
      vectors), with an attestation for this collection, this dimension and this
      model: PASS (attested legacy). An attestation for another model or another
      dimension is FAIL, and so is an attestation file that cannot be read. Under
      ``strict`` the attestation must also have checked every row.
    * records no model and nothing applicable attests it: WARN, or FAIL when
      ``strict`` (the switch to flip once the live collections are attested).
    """
    if not meta and chroma_dimension is None and not row_count:
        return IdentityVerdict(
            WARN,
            "WARN: collection missing, or empty with no collection_metadata "
            f"(configured={configured_model!r}; shadow stores must set metadata)",
        )
    raw_model = meta.get(EMBED_MODEL_KEY)
    if raw_model is not None and raw_model != "":
        stored_model = normalize_embed_model(raw_model)
        if stored_model is None:
            return IdentityVerdict(
                FAIL, f"collection {EMBED_MODEL_KEY}={raw_model!r} is not a usable model name"
            )
        return _judge_recorded(meta, stored_model, chroma_dimension, configured_model)
    if attestation_error is not None:
        return IdentityVerdict(FAIL, f"attestation unusable: {attestation_error}")
    if attestation is None:
        reason = "no attestation"
        if chroma_dimension is None and row_count == 0:
            # Verified empty: created by a read or a refine job before any write could stamp it.
            reason += (
                "; it holds no vectors, so it can be dropped and the next write "
                f"will recreate it recording {EMBED_MODEL_KEY}"
            )
        return _judge_unattested(configured_model, reason, strict)
    if attestation.collection_uuid != uuid:
        return _judge_unattested(
            configured_model,
            f"attestation is for another collection (uuid={attestation.collection_uuid})",
            strict,
        )
    if chroma_dimension is None:
        return _judge_unattested(
            configured_model,
            "the collection records no vector dimension, so the attestation has nothing to bind to",
            strict,
        )
    return _judge_attestation(attestation, chroma_dimension, configured_model, strict)


def _judge_named(  # pylint: disable=too-many-arguments
    chroma_dir: str | Path,
    name: str,
    *,
    attestations: Mapping[str, CollectionAttestation],
    attestation_error: str | None,
    configured_model: str,
    strict: bool,
) -> IdentityVerdict | None:
    """Judge one collection, or None for an optional collection that does not exist."""
    # One read transaction: the UUID, dimension and metadata used for a verdict must describe
    # the same collection, even if another session replaces it while this runs.
    try:
        facts = collection_identity_facts(chroma_dir, name)
    except FileNotFoundError:
        if name != UNITS:
            return None  # knowledge_units reports a missing database; summaries add nothing
        raise
    if facts.uuid is None and name != UNITS:
        return None
    return judge_collection(
        meta=facts.metadata,
        uuid=facts.uuid or "",
        chroma_dimension=facts.dimension,
        # A missing dimension is not proof of emptiness (damaged metadata): the facts count
        # every trace of a row in any segment or the log, not just the one view that may be damaged.
        row_count=facts.row_evidence,
        attestation=attestations.get(name),
        attestation_error=attestation_error,
        configured_model=configured_model,
        strict=strict,
    )


def check_embed_identity(
    chroma_dir: str | Path, configured_model: str, *, strict: bool = False
) -> IdentityVerdict:
    """Judge every collection that exists; the worst verdict wins.

    ``knowledge_units`` is always judged (a missing one is a WARN, as before);
    ``conversation_summaries`` is judged only when it exists, because it is
    created lazily. Each collection is judged on its own: a collection whose
    identity cannot be read is a WARN (FAIL when ``strict``) and never hides
    another collection's verdict. The configured model is normalised the way the
    stamp is, and an absent one can pass nothing.
    """
    configured = normalize_embed_model(configured_model) or ""
    try:
        attestations, attestation_error = read_attestations(chroma_dir), None
    except Exception as exc:  # pylint: disable=broad-exception-caught
        attestations, attestation_error = {}, str(exc)  # an unusable sidecar fails, never raises

    parts: list[str] = []
    worst = PASS
    for name in (UNITS, SUMMARIES):
        try:
            verdict = _judge_named(
                chroma_dir,
                name,
                attestations=attestations,
                attestation_error=attestation_error,
                configured_model=configured,
                strict=strict,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Whatever went wrong with one collection must not hide the other's verdict.
            verdict = IdentityVerdict(
                FAIL if strict else WARN,
                f"WARN: cannot read collection metadata ({type(exc).__name__}): {exc}",
            )
        if verdict is None:
            continue
        parts.append(verdict.detail if name == UNITS else f"{name}: {verdict.detail}")
        if _SEVERITY[verdict.status] > _SEVERITY[worst]:
            worst = verdict.status
    if not configured:
        # Nothing to compare against: that is unproven, not a pass.
        floor = FAIL if strict else WARN
        parts.insert(0, "WARN: no [models] embed_model is configured, so no collection can be compared")
        if _SEVERITY[floor] > _SEVERITY[worst]:
            worst = floor
    return IdentityVerdict(worst, "; ".join(parts))
