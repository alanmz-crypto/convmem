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
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chroma_readonly import (
    collection_config_metadata,
    collection_dimension,
    collection_uuid,
)
from chroma_store import EMBED_MODEL_KEY, SUMMARIES, UNITS, normalize_embed_model

EMBED_DIMENSIONS_KEY = "convmem:embed_dimensions"
ATTESTATION_SCHEMA = "convmem.chroma-embed-attestation.v1"

PASS = "pass"
WARN = "warn"
FAIL = "fail"
_SEVERITY = {PASS: 0, WARN: 1, FAIL: 2}


class AttestationError(ValueError):
    """The attestation sidecar is unreadable, malformed or unusable."""


@dataclass(frozen=True)
class CollectionAttestation:
    """An operator's claim about one collection, bound to what Chroma recorded."""

    name: str
    collection_uuid: str
    dimension: int
    embed_model: str
    attested_at: str | None = None


@dataclass(frozen=True)
class IdentityVerdict:
    status: str  # PASS, WARN or FAIL
    detail: str


def sidecar_path(chroma_dir: str | Path) -> Path:
    """Where the attestation for ``chroma_dir`` lives: beside it, never inside it."""
    base = Path(chroma_dir).expanduser()
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
        evidence = entry.get("evidence")
        attested_at = evidence.get("attested_at") if isinstance(evidence, Mapping) else None
        parsed[name] = CollectionAttestation(
            name=name,
            collection_uuid=uuid.strip(),
            dimension=dimension,
            embed_model=model,
            attested_at=attested_at if isinstance(attested_at, str) else None,
        )
    return parsed


def read_attestations(chroma_dir: str | Path) -> dict[str, CollectionAttestation]:
    """Attestations for ``chroma_dir``; no sidecar means none. Corrupt raises."""
    path = sidecar_path(chroma_dir)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise AttestationError(f"cannot read {path.name}: {exc}") from exc
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise AttestationError(f"{path.name} is not valid JSON: {exc}") from exc
    return parse_attestations(payload)


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
    if configured_model and stored_model != configured_model:
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
    if recorded is not None and chroma_dimension is not None and recorded != chroma_dimension:
        return IdentityVerdict(
            FAIL, f"embed dimension mismatch: recorded={recorded} chroma={chroma_dimension}"
        )
    detail = f"collection embed_model={stored_model!r}"
    if recorded is not None:
        detail += f" dimensions={recorded!r}"
    return IdentityVerdict(PASS, detail)


def _judge_attestation(
    attestation: CollectionAttestation,
    chroma_dimension: int | None,
    configured_model: str,
) -> IdentityVerdict:
    """The attestation applies to this very collection; is it still true?"""
    if chroma_dimension is not None and attestation.dimension != chroma_dimension:
        return IdentityVerdict(
            FAIL,
            f"attested dimension {attestation.dimension} != collection dimension "
            f"{chroma_dimension}",
        )
    if configured_model and attestation.embed_model != configured_model:
        return IdentityVerdict(
            FAIL,
            f"attested embed model mismatch: attested={attestation.embed_model!r} "
            f"config={configured_model!r}",
        )
    when = f" on {attestation.attested_at}" if attestation.attested_at else ""
    return IdentityVerdict(
        PASS,
        f"attested legacy embed_model={attestation.embed_model!r} "
        f"dimensions={attestation.dimension!r}{when}",
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
) -> IdentityVerdict:
    """Decide one collection's identity state from facts already read.

    Pure: no I/O. States, in order:

    * records a model: PASS if it matches the configuration and any recorded
      dimension matches Chroma's own; FAIL otherwise.
    * records no model, with a matching attestation: PASS (attested legacy).
    * records no model, with an attestation for another model or another
      dimension: FAIL. So is an attestation file that cannot be read.
    * records no model and nothing applicable attests it: WARN, or FAIL when
      ``strict`` (the switch to flip once the live collections are attested).
    """
    if not meta:
        return IdentityVerdict(
            WARN,
            "WARN: collection missing or has no collection_metadata "
            f"(configured={configured_model!r}; shadow stores must set metadata)",
        )
    stored_model = str(meta.get(EMBED_MODEL_KEY) or "")
    if stored_model:
        return _judge_recorded(meta, stored_model, chroma_dimension, configured_model)
    if attestation_error is not None:
        return IdentityVerdict(FAIL, f"attestation unusable: {attestation_error}")
    if attestation is None:
        return _judge_unattested(configured_model, "no attestation", strict)
    if attestation.collection_uuid != uuid:
        return _judge_unattested(
            configured_model,
            f"attestation is for another collection (uuid={attestation.collection_uuid})",
            strict,
        )
    return _judge_attestation(attestation, chroma_dimension, configured_model)


def check_embed_identity(
    chroma_dir: str | Path, configured_model: str, *, strict: bool = False
) -> IdentityVerdict:
    """Judge every collection that exists; the worst verdict wins.

    ``knowledge_units`` is always judged (a missing one is a WARN, as before);
    ``conversation_summaries`` is judged only when it exists, because it is
    created lazily. Read errors propagate so the caller can report them.
    """
    try:
        attestations, attestation_error = read_attestations(chroma_dir), None
    except AttestationError as exc:
        attestations, attestation_error = {}, str(exc)

    parts: list[str] = []
    worst = PASS
    for name in (UNITS, SUMMARIES):
        uuid = collection_uuid(chroma_dir, name)
        if uuid is None and name != UNITS:
            continue
        meta = collection_config_metadata(chroma_dir, name)
        verdict = judge_collection(
            meta=meta,
            uuid=uuid or "",
            chroma_dimension=collection_dimension(chroma_dir, name),
            attestation=attestations.get(name),
            attestation_error=attestation_error,
            configured_model=configured_model,
            strict=strict,
        )
        parts.append(verdict.detail if name == UNITS else f"{name}: {verdict.detail}")
        if _SEVERITY[verdict.status] > _SEVERITY[worst]:
            worst = verdict.status
    return IdentityVerdict(worst, "; ".join(parts))
