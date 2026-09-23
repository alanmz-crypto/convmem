"""Strict identities, fixture materialization, and complete-bound state reduction (T1)."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from bound_read_scope import (
    BoundScopeError,
    ProjectBinding,
    reject_hostile_source_keys,
    require_already_nfc,
    sha256_digest,
)
from strict_grounding import (
    QualificationTuple,
    _hashes_equal,
    derive_origin_assurance,
    strict_canonical_bytes,
)

_PRODUCER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,15}$")
_EVENT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_TS_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ASSERTION_ID_RE = re.compile(r"^(?:obs2|dec2|ver2)_[0-9a-f]{64}$")
_LOGICAL_ID_RE = re.compile(r"^(?:find2_|choice2_|check2_)[0-9a-f]{64}$")
_DISP_ID_RE = re.compile(r"^disp_[0-9a-f]{64}$")

_LOGICAL_PREFIX = {"observation": "find2_", "decision": "choice2_", "verification": "check2_"}
_ASSERTION_PREFIX = {"observation": "obs2_", "decision": "dec2_", "verification": "ver2_"}
_SUBJECT_KIND = {
    "observation": "finding",
    "decision": "decision",
    "verification": "verification",
}

DISPOSITION_ACTIONS = frozenset(
    {
        "decision_approved",
        "decision_rejected",
        "decision_revoked",
        "evidence_withdrawn",
        "supersession_authorized",
    }
)
CHECK_ELIGIBILITY = frozenset({"not_applicable", "qualified", "inconclusive_only"})
VERIFICATION_RESULTS = frozenset({"pass", "fail", "inconclusive"})

REDUCER_VERSION = "v1"
IDENTITY_VERSION = "v2"
CANONICALIZATION_VERSION = "v1"
GROUNDING_VERSION = "v1"

SOURCE_RECORD_FIELDS = (
    "record_kind",
    "producer",
    "logical_key",
    "title",
    "document",
    "observed_at",
    "confidence_bps",
    "relates_to_assertion_id",
    "target_assertion_id",
    "verification_result",
    "provenance_assertion_id",
)

DISPOSITION_FIELDS = frozenset(
    {
        "schema",
        "action",
        "project_binding_id",
        "subject_assertion_id",
        "subject_semantic_sha256",
        "target_assertion_ids",
        "basis_snapshot_id",
        "expected_head_assertion_ids",
        "replaces_disposition_ref",
        "review_actor",
        "review_role",
        "review_outcome",
        "reviewed_at",
        "ratifier_actor",
        "ratifier_role",
        "ratified_at",
        "rationale_sha256",
    }
)


class StrictEvidenceError(ValueError):
    """Fail-closed identity/materialization/reducer error."""


class LedgerIdMintDenied(StrictEvidenceError):
    """Generator failure aborts with ledger_id_mint_denied (no UUID fallback)."""


def _require_nfc(value: Any, *, field: str) -> str:
    try:
        return require_already_nfc(value, field=field)
    except BoundScopeError as exc:
        raise StrictEvidenceError(str(exc)) from exc


def _require_nfc_mint(value: Any, *, field: str) -> str:
    try:
        return require_already_nfc(value, field=field)
    except BoundScopeError as exc:
        raise LedgerIdMintDenied("ledger_id_mint_denied") from exc


def _lp(value: str) -> bytes:
    _require_nfc_mint(value, field="lp")
    raw = unicodedata.normalize("NFC", value).encode("utf-8")
    if len(raw) > 0xFFFFFFFF:
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    return struct.pack(">I", len(raw)) + raw


def length_prefixed_digest(tag: str, fields: Sequence[str]) -> str:
    if not isinstance(tag, str):
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    try:
        tag_bytes = tag.encode("ascii")
    except UnicodeEncodeError as exc:
        raise LedgerIdMintDenied("ledger_id_mint_denied") from exc
    if tag_bytes.decode("ascii") != tag:
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    parts = [tag_bytes, b"\x00"]
    for field in fields:
        if not isinstance(field, str):
            raise LedgerIdMintDenied("ledger_id_mint_denied")
        parts.append(_lp(field))
    return hashlib.sha256(b"".join(parts)).hexdigest()


def logical_id_v2(
    *,
    project_binding_id: str,
    source_identity: str,
    authority_site: str,
    producer: str,
    logical_key: str,
    record_kind: str,
    target_assertion_id: str | None,
) -> str:
    _require_nfc_mint(project_binding_id, field="project_binding_id")
    _require_nfc_mint(source_identity, field="source_identity")
    _require_nfc_mint(authority_site, field="authority_site")
    _require_nfc_mint(producer, field="producer")
    _require_nfc_mint(logical_key, field="logical_key")
    if record_kind not in _LOGICAL_PREFIX:
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    if not _PRODUCER_RE.fullmatch(producer):
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    if not (1 <= len(logical_key) <= 256):
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    subject_kind = _SUBJECT_KIND[record_kind]
    if target_assertion_id is None:
        target = ""
    else:
        _require_nfc_mint(target_assertion_id, field="target_assertion_id")
        if not _ASSERTION_ID_RE.fullmatch(target_assertion_id):
            raise LedgerIdMintDenied("ledger_id_mint_denied")
        target = target_assertion_id
    digest = length_prefixed_digest(
        "convmem-logical-id-v2",
        [
            project_binding_id,
            source_identity,
            authority_site,
            producer,
            logical_key,
            subject_kind,
            target,
        ],
    )
    return _LOGICAL_PREFIX[record_kind] + digest


def source_event_id_fixture_scan(
    *,
    source_registration_id: str,
    source_identity: str,
    event_key: str,
) -> str:
    _require_nfc_mint(source_registration_id, field="source_registration_id")
    _require_nfc_mint(source_identity, field="source_identity")
    _require_nfc_mint(event_key, field="event_key")
    if not _EVENT_KEY_RE.fullmatch(event_key) or not (1 <= len(event_key) <= 256):
        raise StrictEvidenceError("event_key_invalid")
    digest = length_prefixed_digest(
        "convmem-fixture-scan-event-v1",
        [source_registration_id, source_identity, event_key],
    )
    return "evt_" + digest


def assertion_id_v2(
    *,
    project_binding_id: str,
    source_registration_id: str,
    source_event_id: str,
    record_kind: str,
    logical_id: str,
) -> str:
    _require_nfc_mint(project_binding_id, field="project_binding_id")
    _require_nfc_mint(source_registration_id, field="source_registration_id")
    _require_nfc_mint(source_event_id, field="source_event_id")
    _require_nfc_mint(logical_id, field="logical_id")
    if record_kind not in _ASSERTION_PREFIX:
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    if not source_event_id.startswith("evt_") or len(source_event_id) != 68:
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    if not _LOGICAL_ID_RE.fullmatch(logical_id):
        raise LedgerIdMintDenied("ledger_id_mint_denied")
    digest = length_prefixed_digest(
        "convmem-assertion-id-v2",
        [
            project_binding_id,
            source_registration_id,
            source_event_id,
            record_kind,
            logical_id,
        ],
    )
    return _ASSERTION_PREFIX[record_kind] + digest


def disposition_id(disposition: Mapping[str, Any]) -> str:
    if not isinstance(disposition, Mapping):
        raise StrictEvidenceError("disposition_type")
    return "disp_" + sha256_digest(strict_canonical_bytes(dict(disposition))).removeprefix(
        "sha256:"
    )


def semantic_sha256(record: Mapping[str, Any]) -> str:
    excluded = {
        "semantic_sha256",
        "payload_sha256",
        "decision_disposition_ref",
        "supersession_disposition_ref",
        "provenance_envelope",
    }
    payload = {k: v for k, v in record.items() if k not in excluded}
    return sha256_digest(strict_canonical_bytes(payload))


def payload_sha256(record: Mapping[str, Any]) -> str:
    payload = {k: v for k, v in record.items() if k != "payload_sha256"}
    return sha256_digest(strict_canonical_bytes(payload))


def citation_ref(
    *,
    project_binding_id: str,
    assertion_id: str,
    provenance_commitment: str,
) -> str:
    _require_nfc(project_binding_id, field="project_binding_id")
    _require_nfc(assertion_id, field="assertion_id")
    _require_nfc(provenance_commitment, field="provenance_commitment")
    obj = {
        "schema": "convmem.strict-citation-ref.v1",
        "project_binding_id": project_binding_id,
        "assertion_id": assertion_id,
        "provenance_commitment": provenance_commitment,
    }
    return "cite1_" + sha256_digest(strict_canonical_bytes(obj)).removeprefix("sha256:")


def public_ledger_id(*, public_binding_ref: str, assertion_id: str) -> str:
    _require_nfc(public_binding_ref, field="public_binding_ref")
    _require_nfc(assertion_id, field="assertion_id")
    return f"cm1.{public_binding_ref}.{assertion_id}"


# Architecture §8.3 — fullmatch grammars; max lengths are code-point counts.
_STORED_LEDGER_ID_RE = re.compile(
    r"(?:(?:obs2|dec2|ver2)_[a-f0-9]{64}|(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+)"
)
_PUBLIC_LEDGER_HANDLE_RE = re.compile(
    r"cm1\.([a-f0-9]{32})\."
    r"((?:(?:obs2|dec2|ver2)_[a-f0-9]{64}|(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+))"
)
_STORED_LEDGER_ID_MAX = 160
_PUBLIC_LEDGER_HANDLE_MAX = 200


def validate_stored_ledger_id(value: Any) -> str:
    """Syntax/length stage for stored ledger IDs (Architecture §8.3)."""

    if not isinstance(value, str):
        raise StrictEvidenceError("stored_ledger_id_type")
    if len(value) > _STORED_LEDGER_ID_MAX:
        raise StrictEvidenceError("stored_ledger_id_length")
    if not _STORED_LEDGER_ID_RE.fullmatch(value):
        raise StrictEvidenceError("stored_ledger_id_grammar")
    return value


def parse_public_ledger_handle(value: Any) -> tuple[str, str]:
    """Parse ``cm1.<public_ref>.<stored_id>``; returns (public_binding_ref, stored_id)."""

    if not isinstance(value, str):
        raise StrictEvidenceError("public_handle_type")
    if len(value) > _PUBLIC_LEDGER_HANDLE_MAX:
        raise StrictEvidenceError("public_handle_length")
    match = _PUBLIC_LEDGER_HANDLE_RE.fullmatch(value)
    if match is None:
        raise StrictEvidenceError("public_handle_grammar")
    public_ref, stored = match.group(1), match.group(2)
    validate_stored_ledger_id(stored)
    return public_ref, stored


def looks_like_public_ledger_handle(value: Any) -> bool:
    """True when value matches the public-handle grammar (search reject path)."""

    if not isinstance(value, str):
        return False
    if len(value) > _PUBLIC_LEDGER_HANDLE_MAX:
        return False
    return _PUBLIC_LEDGER_HANDLE_RE.fullmatch(value) is not None


def strict_source_payload_sha256(source_record: Mapping[str, Any]) -> str:
    if not isinstance(source_record, Mapping):
        raise StrictEvidenceError("source_record_type")
    payload = {k: v for k, v in source_record.items() if k != "provenance_assertion_id"}
    return sha256_digest(strict_canonical_bytes(payload))


def _require_ts(value: Any, name: str) -> str:
    text = _require_nfc(value, field=name)
    if not _TS_RE.fullmatch(text):
        raise StrictEvidenceError(name)
    return text


def _require_sha(value: Any, name: str) -> str:
    text = _require_nfc(value, field=name)
    if not _SHA_RE.fullmatch(text):
        raise StrictEvidenceError(name)
    return text


def _collision_key(
    *,
    project_binding_id: str,
    source_registration_id: str,
    source_event_id: str,
    record_kind: str,
    logical_id: str,
) -> tuple[str, str, str, str, str]:
    return (
        project_binding_id,
        source_registration_id,
        source_event_id,
        record_kind,
        logical_id,
    )


def materialize_authority_records(
    *,
    binding: ProjectBinding,
    source_registration_id: str,
    scan: Mapping[str, Any],
    registered_assertions: Mapping[str, Mapping[str, Any]],
    qualification_by_provenance: Mapping[str, QualificationTuple],
    prior_records: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Trusted construction after hostile-key rejection and registry resolution.

    Qualification is required for every provenance assertion (no default).
    Collision keys that match prior/byte-identical records are idempotent;
    other collisions fail closed.
    """

    if not isinstance(qualification_by_provenance, Mapping):
        raise StrictEvidenceError("qualification_map_required")
    reject_hostile_source_keys(scan)
    if set(scan) != {"schema", "event_key", "captured_at", "records"}:
        raise StrictEvidenceError("scan_keys")
    if scan["schema"] != "convmem.fixture-scan.v1":
        raise StrictEvidenceError("scan_schema")
    event_key = _require_nfc(scan["event_key"], field="event_key")
    if not _EVENT_KEY_RE.fullmatch(event_key) or not (1 <= len(event_key) <= 256):
        raise StrictEvidenceError("event_key_invalid")
    captured_at = _require_ts(scan["captured_at"], "captured_at")
    records_raw = scan["records"]
    if not isinstance(records_raw, list) or not records_raw:
        raise StrictEvidenceError("scan_records")

    _require_nfc(source_registration_id, field="source_registration_id")
    regs = {r.id: r for r in binding.source_registrations}
    if source_registration_id not in regs:
        raise StrictEvidenceError("source_registration_unknown")
    reg = regs[source_registration_id]
    if reg.event_id_resolver != "fixture_scan_event_v1":
        raise StrictEvidenceError("event_id_resolver")

    if binding.site_mode == "exact":
        authority_site = binding.site
        if authority_site is None or reg.site != authority_site:
            raise StrictEvidenceError("authority_site")
    else:
        # Service-owned site vocabulary: literal not_applicable for N/A bindings.
        authority_site = "not_applicable"
    authority_domain = reg.authorization_domain

    source_event_id = source_event_id_fixture_scan(
        source_registration_id=source_registration_id,
        source_identity=reg.source_identity,
        event_key=event_key,
    )

    prior_by_collision: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for prior in prior_records or ():
        if not isinstance(prior, Mapping):
            raise StrictEvidenceError("prior_record_type")
        key = _collision_key(
            project_binding_id=prior["project_binding_id"],
            source_registration_id=prior["source_registration_id"],
            source_event_id=prior["source_event_id"],
            record_kind=prior["record_kind"],
            logical_id=prior["logical_id"],
        )
        if key in prior_by_collision:
            raise StrictEvidenceError("prior_collision_duplicate")
        prior_by_collision[key] = dict(prior)

    out: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    for raw in records_raw:
        if not isinstance(raw, Mapping):
            raise StrictEvidenceError("source_record_type")
        reject_hostile_source_keys(raw)
        if set(raw) != set(SOURCE_RECORD_FIELDS):
            raise StrictEvidenceError("source_record_keys")
        record_kind = raw["record_kind"]
        if record_kind not in _LOGICAL_PREFIX:
            raise StrictEvidenceError("record_kind")
        producer = _require_nfc(raw["producer"], field="producer")
        if not _PRODUCER_RE.fullmatch(producer):
            raise StrictEvidenceError("producer")
        logical_key = _require_nfc(raw["logical_key"], field="logical_key")
        if not (1 <= len(logical_key) <= 256):
            raise StrictEvidenceError("logical_key")
        title = _require_nfc(raw["title"], field="title")
        document = _require_nfc(raw["document"], field="document")
        if not (1 <= len(title) <= 512) or not (1 <= len(document) <= 65536):
            raise StrictEvidenceError("title_or_document")
        observed_at = _require_ts(raw["observed_at"], "observed_at")
        confidence = raw["confidence_bps"]
        if not isinstance(confidence, int) or isinstance(confidence, bool) or not (
            0 <= confidence <= 10000
        ):
            raise StrictEvidenceError("confidence_bps")
        relates = raw["relates_to_assertion_id"]
        if relates is not None:
            relates = _require_nfc(relates, field="relates_to_assertion_id")
            if not _ASSERTION_ID_RE.fullmatch(relates):
                raise StrictEvidenceError("relates_to_assertion_id")
        target = raw["target_assertion_id"]
        verification_result = raw["verification_result"]
        if record_kind == "verification":
            target = _require_nfc(target, field="target_assertion_id")
            if not _ASSERTION_ID_RE.fullmatch(target):
                raise StrictEvidenceError("verification_target")
            if verification_result not in VERIFICATION_RESULTS:
                raise StrictEvidenceError("verification_result")
        else:
            if target is not None:
                raise StrictEvidenceError("target_must_be_null")
            if verification_result is not None:
                raise StrictEvidenceError("verification_result_must_be_null")
            target = None
        prov_id = _require_nfc(
            raw["provenance_assertion_id"], field="provenance_assertion_id"
        )
        if prov_id not in registered_assertions:
            raise StrictEvidenceError("provenance_unregistered")
        if prov_id not in qualification_by_provenance:
            raise StrictEvidenceError("qualification_missing")
        registered = registered_assertions[prov_id]
        if set(registered) != {"assertion_id", "provenance_commitment", "envelope"}:
            raise StrictEvidenceError("registered_assertion_keys")
        if registered["assertion_id"] != prov_id:
            raise StrictEvidenceError("provenance_assertion_mismatch")
        envelope = registered["envelope"]
        commitment = _require_nfc(
            registered["provenance_commitment"], field="provenance_commitment"
        )
        if not isinstance(envelope, Mapping):
            raise StrictEvidenceError("provenance_envelope")
        if envelope.get("assertion_id") != prov_id:
            raise StrictEvidenceError("provenance_assertion_mismatch")

        logical_id = logical_id_v2(
            project_binding_id=binding.id,
            source_identity=reg.source_identity,
            authority_site=authority_site,
            producer=producer,
            logical_key=logical_key,
            record_kind=record_kind,
            target_assertion_id=target if record_kind == "verification" else None,
        )
        assertion_id = assertion_id_v2(
            project_binding_id=binding.id,
            source_registration_id=source_registration_id,
            source_event_id=source_event_id,
            record_kind=record_kind,
            logical_id=logical_id,
        )
        if not logical_id.startswith(_LOGICAL_PREFIX[record_kind]):
            raise StrictEvidenceError("logical_prefix")
        if not assertion_id.startswith(_ASSERTION_PREFIX[record_kind]):
            raise StrictEvidenceError("assertion_prefix")

        source_payload = strict_source_payload_sha256(raw)
        selection = envelope.get("selection_parameters") if isinstance(envelope, Mapping) else None
        if not isinstance(selection, Mapping):
            raise StrictEvidenceError("source_payload_binding")
        output_sha = selection.get("output_sha256")
        if not isinstance(output_sha, str):
            raise StrictEvidenceError("source_payload_binding")
        # envelope may store unlabeled hex; accept labeled or unlabeled exact match
        labeled = source_payload
        unlabeled = source_payload.removeprefix("sha256:")
        if output_sha not in {labeled, unlabeled}:
            raise StrictEvidenceError("source_payload_binding")

        qualification = qualification_by_provenance[prov_id]
        if not isinstance(qualification, QualificationTuple):
            raise StrictEvidenceError("qualification_type")
        # Freeze original-admission qualification bytes; no late mutation path.
        frozen_qualification = QualificationTuple(
            qualification.commitments,
            qualification.byte_grounding,
            qualification.capture,
            qualification.transformer_cap,
        )
        origin = derive_origin_assurance(frozen_qualification)
        check_eligibility = _eligibility_for_record(
            binding=binding,
            record_kind=record_kind,
            source_registration_id=source_registration_id,
            producer=producer,
            envelope=envelope,
            qualification=frozen_qualification,
        )

        record = {
            "schema": "convmem.bound-authority-record.v3",
            "project_binding_id": binding.id,
            "source_registration_id": source_registration_id,
            "authority_site": authority_site,
            "authority_domain": authority_domain,
            "record_kind": record_kind,
            "logical_id": logical_id,
            "assertion_id": assertion_id,
            "source_event_id": source_event_id,
            "producer": producer,
            "logical_key": logical_key,
            "semantic_sha256": None,
            "payload_sha256": None,
            "title": title,
            "document": document,
            "observed_at": observed_at,
            "recorded_at": captured_at,
            "confidence_bps": confidence,
            "relates_to_assertion_id": relates,
            "target_assertion_id": target,
            "verification_result": verification_result,
            "supersedes_assertion_ids": [],
            "decision_disposition_ref": None,
            "supersession_disposition_ref": None,
            "provenance_envelope": dict(envelope),
            "provenance_commitment": commitment,
            "origin_assurance": origin,
            "provenance_qualification": frozen_qualification.as_dict(),
            "check_eligibility": check_eligibility,
        }
        if observed_at > captured_at:
            raise StrictEvidenceError("observed_after_recorded")
        record["semantic_sha256"] = semantic_sha256(record)
        record["payload_sha256"] = payload_sha256(record)

        key = _collision_key(
            project_binding_id=binding.id,
            source_registration_id=source_registration_id,
            source_event_id=source_event_id,
            record_kind=record_kind,
            logical_id=logical_id,
        )
        if key in seen_keys:
            raise StrictEvidenceError("source_event_conflict")
        seen_keys.add(key)
        prior = prior_by_collision.get(key)
        if prior is not None:
            # Exact retry: byte-equivalent complete record is idempotent no-op.
            if (
                prior["assertion_id"] != assertion_id
                or prior["semantic_sha256"] != record["semantic_sha256"]
                or prior["payload_sha256"] != record["payload_sha256"]
                or strict_canonical_bytes(prior) != strict_canonical_bytes(record)
            ):
                raise StrictEvidenceError("source_event_conflict")
            continue
        out.append(record)
    return out


def _eligibility_for_record(
    *,
    binding: ProjectBinding,
    record_kind: str,
    source_registration_id: str,
    producer: str,
    envelope: Mapping[str, Any],
    qualification: QualificationTuple,
) -> str:
    """Derive check_eligibility from the frozen registry verification_producers tuple.

    Exact match requires source_registration_id + producer from the record,
    transformer_identity / transformer_version / transformer_artifact_sha256 /
    transformer_recipe_sha256 (registry recipe_sha256) from the immutable
    provenance envelope, and capture_class from the frozen original
    QualificationTuple. Digest fields accept labeled or bare hex only via the
    existing parent ``_hashes_equal`` rule — no new normalization.
    """

    if record_kind != "verification":
        return "not_applicable"
    if not isinstance(envelope, Mapping):
        return "inconclusive_only"
    identity = envelope.get("transformer_identity")
    version = envelope.get("transformer_version")
    artifact = envelope.get("transformer_artifact_sha256")
    # Envelope field transformer_recipe_sha256 maps to registry recipe_sha256.
    recipe = envelope.get("transformer_recipe_sha256")
    capture = qualification.capture
    matched: Any = None
    for entry in binding.verification_producers:
        if (
            entry.source_registration_id == source_registration_id
            and entry.producer == producer
            and entry.transformer_identity == identity
            and entry.transformer_version == version
            and _hashes_equal(entry.transformer_artifact_sha256, artifact)
            and _hashes_equal(entry.recipe_sha256, recipe)
            and entry.capture_class == capture
        ):
            matched = entry
            break
    if matched is None:
        return "inconclusive_only"
    pq = qualification.as_dict()
    if (
        pq["commitments"] == "valid"
        and pq["byte_grounding"] == "complete"
        and pq["capture"] == matched.capture_class
        and pq["transformer_cap"] == "trusted"
    ):
        return "qualified"
    return "inconclusive_only"


def apply_verification_eligibility(
    records: list[dict[str, Any]],
    *,
    binding: ProjectBinding,
) -> None:
    """Set check_eligibility at materialization only (never a query-time reducer)."""

    for rec in records:
        if "provenance_qualification" not in rec:
            raise StrictEvidenceError("qualification_missing")
        pq = rec["provenance_qualification"]
        if not isinstance(pq, Mapping):
            raise StrictEvidenceError("qualification_type")
        envelope = rec.get("provenance_envelope")
        if not isinstance(envelope, Mapping):
            raise StrictEvidenceError("provenance_envelope")
        qualification = QualificationTuple(
            pq["commitments"],
            pq["byte_grounding"],
            pq["capture"],
            pq["transformer_cap"],
        )
        expected = _eligibility_for_record(
            binding=binding,
            record_kind=rec["record_kind"],
            source_registration_id=rec["source_registration_id"],
            producer=rec["producer"],
            envelope=envelope,
            qualification=qualification,
        )
        if "check_eligibility" in rec and rec["check_eligibility"] != expected:
            raise StrictEvidenceError("qualification_immutable")
        rec["check_eligibility"] = expected


def validate_dispositions(
    dispositions: Sequence[Mapping[str, Any]],
    *,
    records: Sequence[Mapping[str, Any]],
    parent_snapshot_id: str | None,
    parent_heads_by_logical: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Validate disposition set against the action matrix; return disp_id -> disposition."""

    by_assertion = {r["assertion_id"]: r for r in records}
    if len(by_assertion) != len(records):
        raise StrictEvidenceError("duplicate_assertion")
    consumed: dict[str, dict[str, Any]] = {}
    approval_by_subject: dict[str, str] = {}
    rejection_by_subject: dict[str, str] = {}
    revocation_by_subject: dict[str, str] = {}
    withdrawal_by_subject: dict[str, str] = {}
    supersession_by_subject: dict[str, str] = {}

    for raw in dispositions:
        if not isinstance(raw, Mapping):
            raise StrictEvidenceError("disposition_type")
        if set(raw) != DISPOSITION_FIELDS:
            raise StrictEvidenceError("disposition_keys")
        if raw["schema"] != "convmem.authority-disposition.v1":
            raise StrictEvidenceError("disposition_schema")
        if raw["review_role"] != "kiro-design-reviewer":
            raise StrictEvidenceError("review_role")
        if raw["ratifier_role"] != "ryan-authority-owner":
            raise StrictEvidenceError("ratifier_role")
        if raw["review_outcome"] not in {"pass", "fail"}:
            raise StrictEvidenceError("review_outcome")
        _require_nfc(raw["review_actor"], field="review_actor")
        _require_nfc(raw["ratifier_actor"], field="ratifier_actor")
        _require_ts(raw["reviewed_at"], "reviewed_at")
        _require_ts(raw["ratified_at"], "ratified_at")
        _require_sha(raw["rationale_sha256"], "rationale_sha256")
        action = raw["action"]
        if action not in DISPOSITION_ACTIONS:
            raise StrictEvidenceError("disposition_action")
        subject = _require_nfc(raw["subject_assertion_id"], field="subject_assertion_id")
        if subject not in by_assertion:
            raise StrictEvidenceError("disposition_subject_missing")
        subject_rec = by_assertion[subject]
        subject_semantic = _require_sha(raw["subject_semantic_sha256"], "subject_semantic_sha256")
        if subject_semantic != subject_rec["semantic_sha256"]:
            raise StrictEvidenceError("subject_semantic_mismatch")
        binding_id = _require_nfc(raw["project_binding_id"], field="project_binding_id")
        if binding_id != subject_rec["project_binding_id"]:
            raise StrictEvidenceError("disposition_binding")

        targets = raw["target_assertion_ids"]
        expected_heads = raw["expected_head_assertion_ids"]
        if not isinstance(targets, list) or not isinstance(expected_heads, list):
            raise StrictEvidenceError("disposition_arrays")
        parsed_targets = [
            _require_nfc(t, field="target_assertion_id") for t in targets
        ]
        parsed_heads = [
            _require_nfc(h, field="expected_head_assertion_id") for h in expected_heads
        ]
        if parsed_targets != sorted(set(parsed_targets)):
            raise StrictEvidenceError("target_assertion_ids")
        if parsed_heads != sorted(set(parsed_heads)):
            raise StrictEvidenceError("expected_head_assertion_ids")

        basis = raw["basis_snapshot_id"]
        replaces = raw["replaces_disposition_ref"]

        if action in {"decision_approved", "decision_rejected"}:
            if subject_rec["record_kind"] != "decision":
                raise StrictEvidenceError("approval_kind")
            if parsed_targets or parsed_heads:
                raise StrictEvidenceError("approval_targets")
            if basis is not None or replaces is not None:
                raise StrictEvidenceError("approval_basis")
            if action == "decision_approved" and raw["review_outcome"] != "pass":
                raise StrictEvidenceError("approval_outcome")
            if action == "decision_rejected" and raw["review_outcome"] != "fail":
                raise StrictEvidenceError("rejection_outcome")
            bucket = approval_by_subject if action == "decision_approved" else rejection_by_subject
            if subject in bucket or subject in approval_by_subject or subject in rejection_by_subject:
                raise StrictEvidenceError("duplicate_decision_disposition")
        elif action == "decision_revoked":
            if subject_rec["record_kind"] != "decision":
                raise StrictEvidenceError("revoke_kind")
            if parsed_targets or parsed_heads:
                raise StrictEvidenceError("revoke_targets")
            if basis != parent_snapshot_id:
                raise StrictEvidenceError("revoke_basis")
            if raw["review_outcome"] != "pass":
                raise StrictEvidenceError("revoke_outcome")
            replaces = _require_nfc(replaces, field="replaces_disposition_ref")
            if not _DISP_ID_RE.fullmatch(replaces):
                raise StrictEvidenceError("revoke_replaces")
            if subject in revocation_by_subject:
                raise StrictEvidenceError("duplicate_revocation")
            if subject in rejection_by_subject:
                raise StrictEvidenceError("revoke_of_rejection")
        elif action == "evidence_withdrawn":
            if subject_rec["record_kind"] not in {"observation", "verification"}:
                raise StrictEvidenceError("withdraw_kind")
            if parsed_targets or parsed_heads:
                raise StrictEvidenceError("withdraw_targets")
            if basis != parent_snapshot_id:
                raise StrictEvidenceError("withdraw_basis")
            if replaces is not None:
                raise StrictEvidenceError("withdraw_replaces")
            if raw["review_outcome"] != "pass":
                raise StrictEvidenceError("withdraw_outcome")
            if subject in withdrawal_by_subject:
                raise StrictEvidenceError("duplicate_withdrawal")
        elif action == "supersession_authorized":
            if raw["review_outcome"] != "pass":
                raise StrictEvidenceError("supersession_outcome")
            if basis != parent_snapshot_id:
                raise StrictEvidenceError("supersession_basis")
            if replaces is not None:
                raise StrictEvidenceError("supersession_replaces")
            if subject in supersession_by_subject:
                raise StrictEvidenceError("duplicate_supersession")
            if not parsed_targets:
                raise StrictEvidenceError("supersession_targets_empty")
            for target in parsed_targets:
                if target not in by_assertion:
                    raise StrictEvidenceError("supersession_missing_target")
                t_rec = by_assertion[target]
                if t_rec["logical_id"] != subject_rec["logical_id"]:
                    raise StrictEvidenceError("supersession_logical")
                if t_rec["record_kind"] != subject_rec["record_kind"]:
                    raise StrictEvidenceError("supersession_kind")
                if t_rec["project_binding_id"] != subject_rec["project_binding_id"]:
                    raise StrictEvidenceError("supersession_binding")
            record_supersedes = subject_rec.get("supersedes_assertion_ids")
            if not isinstance(record_supersedes, list):
                raise StrictEvidenceError("supersession_array_mismatch")
            if sorted(record_supersedes) != parsed_targets:
                raise StrictEvidenceError("supersession_array_mismatch")
            if parent_heads_by_logical is not None:
                logical = subject_rec["logical_id"]
                expected = sorted(parent_heads_by_logical.get(logical, ()))
                if expected != parsed_heads or expected != parsed_targets:
                    raise StrictEvidenceError("supersession_heads")
            elif parsed_heads != parsed_targets:
                raise StrictEvidenceError("supersession_heads")

        disp_id = disposition_id(raw)
        if disp_id in consumed:
            raise StrictEvidenceError("disposition_duplicate")
        # Store with normalized arrays for deterministic reduction.
        stored = dict(raw)
        stored["target_assertion_ids"] = parsed_targets
        stored["expected_head_assertion_ids"] = parsed_heads
        consumed[disp_id] = stored
        if action == "decision_approved":
            approval_by_subject[subject] = disp_id
        elif action == "decision_rejected":
            rejection_by_subject[subject] = disp_id
        elif action == "decision_revoked":
            revocation_by_subject[subject] = disp_id
        elif action == "evidence_withdrawn":
            withdrawal_by_subject[subject] = disp_id
        elif action == "supersession_authorized":
            supersession_by_subject[subject] = disp_id

    # Revocation must replace the exact prior approval disposition.
    for subject, rev_id in revocation_by_subject.items():
        rev = consumed[rev_id]
        replaces = rev["replaces_disposition_ref"]
        if subject not in approval_by_subject:
            raise StrictEvidenceError("revoke_without_approval")
        if approval_by_subject[subject] != replaces:
            raise StrictEvidenceError("revoke_replaces_mismatch")
        if replaces not in consumed:
            raise StrictEvidenceError("revoke_replaces_unknown")
        if consumed[replaces]["action"] != "decision_approved":
            raise StrictEvidenceError("revoke_replaces_not_approval")

    # Every decision must name exactly one approval or rejection.
    for aid, rec in by_assertion.items():
        if rec["record_kind"] != "decision":
            continue
        has_app = aid in approval_by_subject
        has_rej = aid in rejection_by_subject
        if has_app == has_rej:
            raise StrictEvidenceError("decision_disposition_required")
        named = approval_by_subject.get(aid) or rejection_by_subject.get(aid)
        if rec.get("decision_disposition_ref") not in {None, named}:
            # Allow unset during validate-before-bind; when set must match.
            if rec.get("decision_disposition_ref") != named:
                raise StrictEvidenceError("decision_disposition_ref_mismatch")

    # Every non-empty supersession array must name exactly one matching disposition.
    for aid, rec in by_assertion.items():
        supersedes = rec.get("supersedes_assertion_ids") or []
        if not supersedes:
            if rec.get("supersession_disposition_ref") not in (None,):
                raise StrictEvidenceError("supersession_ref_without_array")
            continue
        if aid not in supersession_by_subject:
            raise StrictEvidenceError("supersession_disposition_required")
        named = supersession_by_subject[aid]
        if rec.get("supersession_disposition_ref") not in {None, named}:
            if rec.get("supersession_disposition_ref") != named:
                raise StrictEvidenceError("supersession_disposition_ref_mismatch")

    return consumed


@dataclass(frozen=True, slots=True)
class ReducedState:
    assertion_id: str
    logical_id: str
    record_kind: str
    authority_state: str
    verification_state: str
    subject_head_assertion_ids: tuple[str, ...]
    verification_inputs: tuple[dict[str, Any], ...]
    state_disposition_refs: tuple[str, ...]
    check_eligibility: str


def _truth_table(effective_results: Sequence[str]) -> str:
    if not effective_results:
        return "unverified"
    s = set(effective_results)
    if s == {"pass"}:
        return "pass"
    if s == {"fail"} or s == {"fail", "inconclusive"}:
        return "fail"
    if s == {"inconclusive"} or s == {"pass", "inconclusive"}:
        return "inconclusive"
    if "pass" in s and "fail" in s:
        return "conflict"
    return "inconclusive"


def reduce_complete_bound_state(
    records: Sequence[Mapping[str, Any]],
    dispositions: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]],
) -> dict[str, ReducedState]:
    """Single complete-bound reducer. Never invoked at query time as a separate reducer."""

    by_id = {r["assertion_id"]: dict(r) for r in records}
    if len(by_id) != len(records):
        raise StrictEvidenceError("duplicate_assertion")

    for rec in by_id.values():
        if "check_eligibility" not in rec:
            raise StrictEvidenceError("check_eligibility_required")
        if rec["check_eligibility"] not in CHECK_ELIGIBILITY:
            raise StrictEvidenceError("check_eligibility")
        if "provenance_qualification" not in rec:
            raise StrictEvidenceError("qualification_missing")

    if isinstance(dispositions, Mapping):
        disp_by_id = {k: dict(v) for k, v in dispositions.items()}
    else:
        disp_by_id = {disposition_id(d): dict(d) for d in dispositions}

    approvals: dict[str, str] = {}
    rejections: dict[str, str] = {}
    revocations: dict[str, str] = {}
    withdrawals: dict[str, str] = {}
    supersessions: dict[str, str] = {}

    for disp_id, disp in disp_by_id.items():
        action = disp["action"]
        subject = disp["subject_assertion_id"]
        if action == "decision_approved":
            if subject in approvals:
                raise StrictEvidenceError("duplicate_approval")
            approvals[subject] = disp_id
        elif action == "decision_rejected":
            if subject in rejections:
                raise StrictEvidenceError("duplicate_rejection")
            rejections[subject] = disp_id
        elif action == "decision_revoked":
            if subject in revocations:
                raise StrictEvidenceError("duplicate_revocation")
            revocations[subject] = disp_id
        elif action == "evidence_withdrawn":
            if subject in withdrawals:
                raise StrictEvidenceError("duplicate_withdrawal")
            withdrawals[subject] = disp_id
        elif action == "supersession_authorized":
            if subject in supersessions:
                raise StrictEvidenceError("duplicate_supersession")
            supersessions[subject] = disp_id
        else:
            raise StrictEvidenceError("disposition_action")

    # Permanent supersession edges: any valid admitted successor supersedes targets forever.
    superseded_by: dict[str, set[str]] = {}
    succ_to_targets: dict[str, list[str]] = {}
    for successor_id, disp_id in supersessions.items():
        successor = by_id.get(successor_id)
        if successor is None:
            raise StrictEvidenceError("supersession_missing_successor")
        if successor["record_kind"] == "decision" and successor_id in rejections:
            raise StrictEvidenceError("supersession_rejected_successor")
        disp = disp_by_id[disp_id]
        targets = list(disp["target_assertion_ids"])
        if sorted(successor.get("supersedes_assertion_ids") or []) != sorted(targets):
            raise StrictEvidenceError("supersession_array_mismatch")
        succ_to_targets[successor_id] = targets
        for target in targets:
            if target not in by_id:
                raise StrictEvidenceError("supersession_missing_target")
            if target == successor_id:
                raise StrictEvidenceError("supersession_self")
            t_rec = by_id[target]
            if t_rec["logical_id"] != successor["logical_id"]:
                raise StrictEvidenceError("supersession_logical")
            if t_rec["record_kind"] != successor["record_kind"]:
                raise StrictEvidenceError("supersession_kind")
            if t_rec["project_binding_id"] != successor["project_binding_id"]:
                raise StrictEvidenceError("supersession_binding")
            superseded_by.setdefault(target, set()).add(successor_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def _walk(node: str) -> None:
        if node in visiting:
            raise StrictEvidenceError("supersession_cycle")
        if node in visited:
            return
        visiting.add(node)
        for target in succ_to_targets.get(node, ()):
            _walk(target)
        visiting.remove(node)
        visited.add(node)

    for node in succ_to_targets:
        _walk(node)

    authority: dict[str, str] = {}
    state_disps: dict[str, list[str]] = {aid: [] for aid in by_id}
    consumed_disps: set[str] = set()

    def _consume(aid: str, disp_id: str) -> None:
        if disp_id in consumed_disps:
            raise StrictEvidenceError("disposition_double_consume")
        consumed_disps.add(disp_id)
        state_disps[aid].append(disp_id)

    # Terminal precedence: withdrawal / rejection / revocation first.
    for aid, rec in by_id.items():
        kind = rec["record_kind"]
        if aid in withdrawals:
            authority[aid] = "withdrawn"
            _consume(aid, withdrawals[aid])
            continue
        if kind == "decision" and aid in rejections:
            authority[aid] = "rejected"
            _consume(aid, rejections[aid])
            continue
        if kind == "decision" and aid in revocations:
            authority[aid] = "revoked"
            _consume(aid, revocations[aid])
            replaces = disp_by_id[revocations[aid]]["replaces_disposition_ref"]
            if replaces not in consumed_disps:
                _consume(aid, replaces)
            continue
        if aid in superseded_by:
            # Permanent supersession does not undo a prior approval disposition.
            if kind == "decision":
                if aid in approvals:
                    _consume(aid, approvals[aid])
                elif aid not in rejections:
                    raise StrictEvidenceError("decision_disposition_required")
            authority[aid] = "superseded"
            for succ in sorted(superseded_by[aid]):
                state_disps[aid].append(supersessions[succ])
            continue
        if kind == "decision":
            if aid not in approvals:
                raise StrictEvidenceError("decision_disposition_required")
            authority[aid] = "approved"
            _consume(aid, approvals[aid])
        else:
            authority[aid] = "current"

    # Each supersession disposition is consumed exactly once on its successor subject.
    for successor_id, disp_id in supersessions.items():
        if disp_id not in consumed_disps:
            _consume(successor_id, disp_id)

    # Conflict among remaining eligible heads per logical_id.
    heads_by_logical: dict[str, list[str]] = {}
    for aid, rec in by_id.items():
        if authority[aid] in {"current", "approved"}:
            heads_by_logical.setdefault(rec["logical_id"], []).append(aid)
    for heads in heads_by_logical.values():
        if len(heads) > 1:
            for aid in heads:
                authority[aid] = "conflict"

    # Recompute head sets after conflict marking.
    final_heads_by_logical: dict[str, list[str]] = {}
    for aid, rec in by_id.items():
        if authority[aid] in {"current", "approved", "conflict"}:
            final_heads_by_logical.setdefault(rec["logical_id"], []).append(aid)
    for logical in final_heads_by_logical:
        final_heads_by_logical[logical] = sorted(final_heads_by_logical[logical])

    verifications_by_target: dict[str, list[str]] = {}
    for aid, rec in by_id.items():
        if rec["record_kind"] == "verification" and authority[aid] in {"current", "conflict"}:
            target = rec["target_assertion_id"]
            if not isinstance(target, str):
                raise StrictEvidenceError("verification_target")
            t_rec = by_id.get(target)
            if t_rec is None:
                raise StrictEvidenceError("verification_target_missing")
            if t_rec["record_kind"] == "verification":
                raise StrictEvidenceError("verification_target_kind")
            if t_rec["project_binding_id"] != rec["project_binding_id"]:
                raise StrictEvidenceError("verification_target_binding")
            if t_rec["record_kind"] == "decision" and authority[target] not in {
                "approved",
                "conflict",
                "superseded",
                "revoked",
                "rejected",
            }:
                raise StrictEvidenceError("verification_target_decision")
            verifications_by_target.setdefault(target, []).append(aid)

    if consumed_disps != set(disp_by_id):
        raise StrictEvidenceError("disposition_incomplete_consumption")

    result: dict[str, ReducedState] = {}
    for aid, rec in by_id.items():
        kind = rec["record_kind"]
        auth_state = authority[aid]
        logical = rec["logical_id"]
        head_set = tuple(final_heads_by_logical.get(logical, ()))
        eligibility = rec["check_eligibility"]
        if kind == "verification":
            result[aid] = ReducedState(
                assertion_id=aid,
                logical_id=logical,
                record_kind=kind,
                authority_state=auth_state,
                verification_state="not_applicable",
                subject_head_assertion_ids=head_set,
                verification_inputs=(),
                state_disposition_refs=tuple(sorted(set(state_disps[aid]))),
                check_eligibility=eligibility,
            )
            continue

        inputs: list[dict[str, Any]] = []
        live = verifications_by_target.get(aid, [])
        by_vlogical: dict[str, list[str]] = {}
        for vid in live:
            by_vlogical.setdefault(by_id[vid]["logical_id"], []).append(vid)

        effective_results: list[str] = []
        competing = False
        for vids in by_vlogical.values():
            live_heads = [v for v in vids if authority[v] in {"current", "conflict"}]
            if len(live_heads) > 1:
                competing = True
            for vid in sorted(live_heads):
                vrec = by_id[vid]
                reported = vrec["verification_result"]
                velig = vrec["check_eligibility"]
                if velig == "qualified":
                    effective = reported
                else:
                    # lacking eligibility contributes inconclusive; never omitted
                    effective = "inconclusive"
                inputs.append(
                    {
                        "assertion_id": vid,
                        "logical_id": vrec["logical_id"],
                        "authority_state": authority[vid],
                        "reported_result": reported,
                        "effective_result": effective,
                        "check_eligibility": velig,
                    }
                )
                effective_results.append(effective)

        if competing:
            verification_state = "conflict"
        else:
            verification_state = _truth_table(effective_results)

        result[aid] = ReducedState(
            assertion_id=aid,
            logical_id=logical,
            record_kind=kind,
            authority_state=auth_state,
            verification_state=verification_state,
            subject_head_assertion_ids=head_set,
            verification_inputs=tuple(sorted(inputs, key=lambda x: x["assertion_id"])),
            state_disposition_refs=tuple(sorted(set(state_disps[aid]))),
            check_eligibility=eligibility,
        )
    return result


def unresolved_predicate(state: ReducedState) -> bool:
    return state.record_kind == "observation" and (
        state.authority_state == "conflict"
        or (state.authority_state == "current" and state.verification_state != "pass")
    )


def state_sha256(
    *,
    lineage_id: str,
    authority_seq: int,
    authority_manifest_sha256: str,
    semantic_contract_sha256: str,
    reduced: ReducedState,
) -> str:
    _require_nfc(lineage_id, field="lineage_id")
    if not isinstance(authority_seq, int) or isinstance(authority_seq, bool):
        raise StrictEvidenceError("authority_seq")
    _require_sha(authority_manifest_sha256, "authority_manifest_sha256")
    _require_sha(semantic_contract_sha256, "semantic_contract_sha256")
    obj = {
        "schema": "convmem.strict-state.v2",
        "lineage_id": lineage_id,
        "authority_seq": authority_seq,
        "authority_manifest_sha256": authority_manifest_sha256,
        "semantic_contract_sha256": semantic_contract_sha256,
        "assertion_id": reduced.assertion_id,
        "authority_state": reduced.authority_state,
        "verification_state": reduced.verification_state,
        "subject_head_assertion_ids": list(reduced.subject_head_assertion_ids),
        "verification_inputs": [dict(x) for x in reduced.verification_inputs],
        "state_disposition_refs": list(reduced.state_disposition_refs),
    }
    return sha256_digest(strict_canonical_bytes(obj))


def _canonical_copy(value: Any) -> Any:
    """Deep-copy via canonical JSON so nested bindings stay byte-equivalent."""

    return json.loads(strict_canonical_bytes(value).decode("utf-8"))


def build_citation_map(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Exactly one citation per record, sorted by citation_ref; bindings from envelope."""

    citations: list[dict[str, Any]] = []
    seen_assertions: set[str] = set()
    for rec in records:
        if not isinstance(rec, Mapping):
            raise StrictEvidenceError("citation_record_type")
        assertion_id = rec.get("assertion_id")
        if not isinstance(assertion_id, str) or not assertion_id:
            raise StrictEvidenceError("citation_assertion_id")
        if assertion_id in seen_assertions:
            raise StrictEvidenceError("citation_duplicate_assertion")
        seen_assertions.add(assertion_id)
        envelope = rec.get("provenance_envelope")
        if not isinstance(envelope, Mapping):
            raise StrictEvidenceError("citation_envelope")
        prov_id = envelope.get("assertion_id")
        if not isinstance(prov_id, str) or not prov_id:
            raise StrictEvidenceError("citation_provenance_id")
        commitment = rec.get("provenance_commitment")
        if not isinstance(commitment, str) or not commitment:
            raise StrictEvidenceError("citation_commitment")
        root_bindings = envelope.get("root_bindings")
        input_bindings = envelope.get("input_bindings")
        if not isinstance(root_bindings, list) or not isinstance(input_bindings, list):
            raise StrictEvidenceError("citation_bindings_type")
        citations.append(
            {
                "citation_ref": citation_ref(
                    project_binding_id=str(rec["project_binding_id"]),
                    assertion_id=assertion_id,
                    provenance_commitment=commitment,
                ),
                "assertion_id": assertion_id,
                "provenance_assertion_id": prov_id,
                "provenance_commitment": commitment,
                "root_bindings": _canonical_copy(root_bindings),
                "input_bindings": _canonical_copy(input_bindings),
            }
        )
    if len(citations) != len(records):
        raise StrictEvidenceError("citation_count")
    citations.sort(key=lambda c: c["citation_ref"])
    refs = [c["citation_ref"] for c in citations]
    if refs != sorted(set(refs)):
        raise StrictEvidenceError("citation_ref_unique")
    citation_map: dict[str, Any] = {
        "schema": "convmem.strict-citation-map.v1",
        "citations": citations,
        "citation_map_payload_sha256": "sha256:" + ("0" * 64),
    }
    body = {k: v for k, v in citation_map.items() if k != "citation_map_payload_sha256"}
    citation_map["citation_map_payload_sha256"] = sha256_digest(
        strict_canonical_bytes(body)
    )
    return citation_map


def build_projection_rows_and_graph(
    *,
    records: Sequence[Mapping[str, Any]],
    reduced: Mapping[str, ReducedState],
    lineage_id: str,
    authority_seq: int,
    authority_manifest_sha256: str,
    semantic_contract_sha256: str,
    binding_public_ref: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rebuild serving rows/graph from authority + reduced state (independent of stored)."""

    rows: list[dict[str, Any]] = []
    nodes: set[str] = set()
    edges: list[dict[str, str]] = []
    for rec in sorted(records, key=lambda r: r["assertion_id"]):
        aid = rec["assertion_id"]
        if aid not in reduced:
            raise StrictEvidenceError("row_missing_state")
        st = reduced[aid]
        nodes.add(aid)
        cite = citation_ref(
            project_binding_id=rec["project_binding_id"],
            assertion_id=aid,
            provenance_commitment=rec["provenance_commitment"],
        )
        row = {
            "schema": "convmem.bound-projection-row.v2",
            "project_binding_id": rec["project_binding_id"],
            "public_binding_ref": binding_public_ref,
            "source_registration_id": rec["source_registration_id"],
            "authority_site": rec["authority_site"],
            "authority_domain": rec["authority_domain"],
            "record_kind": rec["record_kind"],
            "logical_id": rec["logical_id"],
            "assertion_id": aid,
            "public_ledger_id": public_ledger_id(
                public_binding_ref=binding_public_ref, assertion_id=aid
            ),
            "citation_ref": cite,
            "title": rec["title"],
            "document": rec["document"],
            "observed_at": rec["observed_at"],
            "recorded_at": rec["recorded_at"],
            "confidence_bps": rec["confidence_bps"],
            "relates_to_assertion_id": rec["relates_to_assertion_id"],
            "target_assertion_id": rec["target_assertion_id"],
            "verification_result": rec["verification_result"],
            "supersedes_assertion_ids": list(rec["supersedes_assertion_ids"]),
            "decision_disposition_ref": rec["decision_disposition_ref"],
            "supersession_disposition_ref": rec["supersession_disposition_ref"],
            "origin_assurance": rec["origin_assurance"],
            "provenance_qualification": dict(rec["provenance_qualification"]),
            "check_eligibility": rec["check_eligibility"],
            "authority_state": st.authority_state,
            "verification_state": st.verification_state,
            "state_disposition_refs": list(st.state_disposition_refs),
            "payload_sha256": rec["payload_sha256"],
            "state_sha256": state_sha256(
                lineage_id=lineage_id,
                authority_seq=authority_seq,
                authority_manifest_sha256=authority_manifest_sha256,
                semantic_contract_sha256=semantic_contract_sha256,
                reduced=st,
            ),
        }
        rows.append(row)
        if rec["relates_to_assertion_id"]:
            edges.append(
                {
                    "kind": "relates_to",
                    "from_assertion_id": aid,
                    "to_assertion_id": rec["relates_to_assertion_id"],
                }
            )
            nodes.add(rec["relates_to_assertion_id"])
        if rec["target_assertion_id"]:
            edges.append(
                {
                    "kind": "targets",
                    "from_assertion_id": aid,
                    "to_assertion_id": rec["target_assertion_id"],
                }
            )
            nodes.add(rec["target_assertion_id"])
        for target in rec["supersedes_assertion_ids"]:
            edges.append(
                {
                    "kind": "supersedes",
                    "from_assertion_id": aid,
                    "to_assertion_id": target,
                }
            )
            nodes.add(target)

    edge_keys = sorted(
        {(e["kind"], e["from_assertion_id"], e["to_assertion_id"]) for e in edges}
    )
    unique_edges = [
        {"kind": k, "from_assertion_id": f, "to_assertion_id": t} for k, f, t in edge_keys
    ]
    graph: dict[str, Any] = {
        "schema": "convmem.strict-graph.v1",
        "nodes": sorted(nodes),
        "edges": unique_edges,
        "graph_payload_sha256": "sha256:" + ("0" * 64),
    }
    body = {k: v for k, v in graph.items() if k != "graph_payload_sha256"}
    graph["graph_payload_sha256"] = sha256_digest(strict_canonical_bytes(body))
    return rows, graph


__all__ = [
    "CANONICALIZATION_VERSION",
    "GROUNDING_VERSION",
    "IDENTITY_VERSION",
    "LedgerIdMintDenied",
    "REDUCER_VERSION",
    "ReducedState",
    "StrictEvidenceError",
    "assertion_id_v2",
    "apply_verification_eligibility",
    "build_citation_map",
    "build_projection_rows_and_graph",
    "citation_ref",
    "disposition_id",
    "length_prefixed_digest",
    "logical_id_v2",
    "materialize_authority_records",
    "payload_sha256",
    "looks_like_public_ledger_handle",
    "parse_public_ledger_handle",
    "public_ledger_id",
    "reduce_complete_bound_state",
    "semantic_sha256",
    "source_event_id_fixture_scan",
    "state_sha256",
    "strict_source_payload_sha256",
    "unresolved_predicate",
    "validate_dispositions",
    "validate_stored_ledger_id",
]
