"""Strict identities, fixture materialization, and complete-bound state reduction (T1)."""

# pylint: disable=C0302  # preserved evidence-state reducer/disposition component boundary


from __future__ import annotations

import hashlib
import json
import re
import struct
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from types import SimpleNamespace

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


def _evidence_field_set(*names: str) -> frozenset[str]:
    """Build closed evidence field sets from an explicit name tuple."""

    return frozenset(names)


DISPOSITION_ACTIONS = frozenset(
    {
        "decision_approved",
        "decision_rejected",
        "decision_revoked",
        "evidence_withdrawn",
        "supersession_authorized",
    }
)
CHECK_ELIGIBILITY = _evidence_field_set(
    "not_applicable",
    "qualified",
    "inconclusive_only",
)
VERIFICATION_RESULTS = _evidence_field_set(
    "pass",
    "fail",
    "inconclusive",
)

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

DISPOSITION_FIELDS = _evidence_field_set(
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
    if not 1 <= len(logical_key) <= 256:
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
    if not _EVENT_KEY_RE.fullmatch(event_key) or not 1 <= len(event_key) <= 256:
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
    return "disp_" + sha256_digest(strict_canonical_bytes(dict(disposition))).removeprefix("sha256:")


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
_STORED_LEDGER_ID_RE = re.compile(r"(?:(?:obs2|dec2|ver2)_[a-f0-9]{64}|(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+)")
_PUBLIC_LEDGER_HANDLE_RE = re.compile(
    r"cm1\.([a-f0-9]{32})\."
    + r"((?:(?:obs2|dec2|ver2)_[a-f0-9]{64}|(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+))"
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


def _materialize_phase_0(work: SimpleNamespace) -> None:
    if not isinstance(work.raw, Mapping):
        raise StrictEvidenceError('source_record_type')
    reject_hostile_source_keys(work.raw)
    if set(work.raw) != set(SOURCE_RECORD_FIELDS):
        raise StrictEvidenceError('source_record_keys')
    work.record_kind = work.raw['record_kind']
    if work.record_kind not in _LOGICAL_PREFIX:
        raise StrictEvidenceError('record_kind')
    work.producer = _require_nfc(work.raw['producer'], field='producer')
    if not _PRODUCER_RE.fullmatch(work.producer):
        raise StrictEvidenceError('producer')
    work.logical_key = _require_nfc(work.raw['logical_key'], field='logical_key')
    if not 1 <= len(work.logical_key) <= 256:
        raise StrictEvidenceError('logical_key')
    work.title = _require_nfc(work.raw['title'], field='title')
    work.document = _require_nfc(work.raw['document'], field='document')
    if not 1 <= len(work.title) <= 512 or not 1 <= len(work.document) <= 65536:
        raise StrictEvidenceError('title_or_document')
    work.observed_at = _require_ts(work.raw['observed_at'], 'observed_at')
    work.confidence = work.raw['confidence_bps']
    if not isinstance(work.confidence, int) or isinstance(work.confidence, bool) or (not 0 <= work.confidence <= 10000):
        raise StrictEvidenceError('confidence_bps')
    work.relates = work.raw['relates_to_assertion_id']
    if work.relates is not None:
        work.relates = _require_nfc(work.relates, field='relates_to_assertion_id')
        if not _ASSERTION_ID_RE.fullmatch(work.relates):
            raise StrictEvidenceError('relates_to_assertion_id')
    work.target = work.raw['target_assertion_id']
    work.verification_result = work.raw['verification_result']

def _materialize_phase_1(work: SimpleNamespace) -> None:
    if work.record_kind == 'verification':
        work.target = _require_nfc(work.target, field='target_assertion_id')
        if not _ASSERTION_ID_RE.fullmatch(work.target):
            raise StrictEvidenceError('verification_target')
        if work.verification_result not in VERIFICATION_RESULTS:
            raise StrictEvidenceError('verification_result')
    else:
        if work.target is not None:
            raise StrictEvidenceError('target_must_be_null')
        if work.verification_result is not None:
            raise StrictEvidenceError('verification_result_must_be_null')
        work.target = None
    work.prov_id = _require_nfc(work.raw['provenance_assertion_id'], field='provenance_assertion_id')
    if work.prov_id not in work.registered_assertions:
        raise StrictEvidenceError('provenance_unregistered')
    if work.prov_id not in work.qualification_by_provenance:
        raise StrictEvidenceError('qualification_missing')
    work.registered = work.registered_assertions[work.prov_id]
    if set(work.registered) != {'assertion_id', 'provenance_commitment', 'envelope'}:
        raise StrictEvidenceError('registered_assertion_keys')
    if work.registered['assertion_id'] != work.prov_id:
        raise StrictEvidenceError('provenance_assertion_mismatch')
    work.envelope = work.registered['envelope']
    work.commitment = _require_nfc(work.registered['provenance_commitment'], field='provenance_commitment')
    if not isinstance(work.envelope, Mapping):
        raise StrictEvidenceError('provenance_envelope')
    if work.envelope.get('assertion_id') != work.prov_id:
        raise StrictEvidenceError('provenance_assertion_mismatch')
    work.logical_id = logical_id_v2(project_binding_id=work.binding.id, source_identity=work.reg.source_identity, authority_site=work.authority_site, producer=work.producer, logical_key=work.logical_key, record_kind=work.record_kind, target_assertion_id=work.target if work.record_kind == 'verification' else None)
    work.assertion_id = assertion_id_v2(project_binding_id=work.binding.id, source_registration_id=work.source_registration_id, source_event_id=work.source_event_id, record_kind=work.record_kind, logical_id=work.logical_id)
    if not work.logical_id.startswith(_LOGICAL_PREFIX[work.record_kind]):
        raise StrictEvidenceError('logical_prefix')
    if not work.assertion_id.startswith(_ASSERTION_PREFIX[work.record_kind]):
        raise StrictEvidenceError('assertion_prefix')
    work.source_payload = strict_source_payload_sha256(work.raw)
    work.selection = work.envelope.get('selection_parameters') if isinstance(work.envelope, Mapping) else None
    if not isinstance(work.selection, Mapping):
        raise StrictEvidenceError('source_payload_binding')
    work.output_sha = work.selection.get('output_sha256')

def _materialize_phase_2(work: SimpleNamespace) -> dict[str, Any] | None:
    if not isinstance(work.output_sha, str):
        raise StrictEvidenceError('source_payload_binding')
    work.labeled = work.source_payload
    work.unlabeled = work.source_payload.removeprefix('sha256:')
    if work.output_sha not in {work.labeled, work.unlabeled}:
        raise StrictEvidenceError('source_payload_binding')
    work.qualification = work.qualification_by_provenance[work.prov_id]
    if not isinstance(work.qualification, QualificationTuple):
        raise StrictEvidenceError('qualification_type')
    work.frozen_qualification = QualificationTuple(work.qualification.commitments, work.qualification.byte_grounding, work.qualification.capture, work.qualification.transformer_cap)
    work.origin = derive_origin_assurance(work.frozen_qualification)
    work.check_eligibility = _eligibility_for_record(binding=work.binding, record_kind=work.record_kind, source_registration_id=work.source_registration_id, producer=work.producer, envelope=work.envelope, qualification=work.frozen_qualification)
    work.record = {'schema': 'convmem.bound-authority-record.v3', 'project_binding_id': work.binding.id, 'source_registration_id': work.source_registration_id, 'authority_site': work.authority_site, 'authority_domain': work.authority_domain, 'record_kind': work.record_kind, 'logical_id': work.logical_id, 'assertion_id': work.assertion_id, 'source_event_id': work.source_event_id, 'producer': work.producer, 'logical_key': work.logical_key, 'semantic_sha256': None, 'payload_sha256': None, 'title': work.title, 'document': work.document, 'observed_at': work.observed_at, 'recorded_at': work.captured_at, 'confidence_bps': work.confidence, 'relates_to_assertion_id': work.relates, 'target_assertion_id': work.target, 'verification_result': work.verification_result, 'supersedes_assertion_ids': [], 'decision_disposition_ref': None, 'supersession_disposition_ref': None, 'provenance_envelope': dict(work.envelope), 'provenance_commitment': work.commitment, 'origin_assurance': work.origin, 'provenance_qualification': work.frozen_qualification.as_dict(), 'check_eligibility': work.check_eligibility}
    if work.observed_at > work.captured_at:
        raise StrictEvidenceError('observed_after_recorded')
    work.record['semantic_sha256'] = semantic_sha256(work.record)
    work.record['payload_sha256'] = payload_sha256(work.record)
    work.key = _collision_key(project_binding_id=work.binding.id, source_registration_id=work.source_registration_id, source_event_id=work.source_event_id, record_kind=work.record_kind, logical_id=work.logical_id)
    if work.key in work.seen_keys:
        raise StrictEvidenceError('source_event_conflict')
    work.seen_keys.add(work.key)
    work.prior = work.prior_by_collision.get(work.key)
    if work.prior is not None:
        if work.prior['assertion_id'] != work.assertion_id or work.prior['semantic_sha256'] != work.record['semantic_sha256'] or work.prior['payload_sha256'] != work.record['payload_sha256'] or (strict_canonical_bytes(work.prior) != strict_canonical_bytes(work.record)):
            raise StrictEvidenceError('source_event_conflict')
        return None
    return work.record

def _materialize_one_source_record(raw: Any, ctx: SimpleNamespace) -> dict[str, Any] | None:
    """Materialize one source record; None means idempotent prior match."""

    work = SimpleNamespace()
    binding = ctx.binding
    source_registration_id = ctx.source_registration_id
    source_event_id = ctx.source_event_id
    authority_site = ctx.authority_site
    authority_domain = ctx.authority_domain
    captured_at = ctx.captured_at
    reg = ctx.reg
    registered_assertions = ctx.registered_assertions
    qualification_by_provenance = ctx.qualification_by_provenance
    prior_by_collision = ctx.prior_by_collision
    seen_keys = ctx.seen_keys
    work.raw = raw
    work.binding = binding
    work.source_registration_id = source_registration_id
    work.source_event_id = source_event_id
    work.authority_site = authority_site
    work.authority_domain = authority_domain
    work.captured_at = captured_at
    work.reg = reg
    work.registered_assertions = registered_assertions
    work.qualification_by_provenance = qualification_by_provenance
    work.prior_by_collision = prior_by_collision
    work.seen_keys = seen_keys

    _materialize_phase_0(work)
    _materialize_phase_1(work)
    return _materialize_phase_2(work)



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
    if not _EVENT_KEY_RE.fullmatch(event_key) or not 1 <= len(event_key) <= 256:
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
        record = _materialize_one_source_record(
            raw,
            SimpleNamespace(
                binding=binding,
                source_registration_id=source_registration_id,
                source_event_id=source_event_id,
                authority_site=authority_site,
                authority_domain=authority_domain,
                captured_at=captured_at,
                reg=reg,
                registered_assertions=registered_assertions,
                qualification_by_provenance=qualification_by_provenance,
                prior_by_collision=prior_by_collision,
                seen_keys=seen_keys,
            ),
        )
        if record is not None:
            out.append(record)
    return out


def _verification_producer_matches(
    entry: Any,
    *,
    source_registration_id: str,
    producer: str,
    identity: Any,
    version: Any,
    artifact: Any,
    recipe: Any,
    capture: Any,
) -> bool:
    """True when a binding verification_producers entry matches record+envelope fields."""

    if entry.source_registration_id != source_registration_id:
        return False
    if entry.producer != producer:
        return False
    if entry.transformer_identity != identity:
        return False
    if entry.transformer_version != version:
        return False
    if not _hashes_equal(entry.transformer_artifact_sha256, artifact):
        return False
    if not _hashes_equal(entry.recipe_sha256, recipe):
        return False
    return entry.capture_class == capture


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
        if _verification_producer_matches(
            entry,
            source_registration_id=source_registration_id,
            producer=producer,
            identity=identity,
            version=version,
            artifact=artifact,
            recipe=recipe,
            capture=capture,
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


def _validate_phase_0(work: SimpleNamespace) -> None:
    if not isinstance(work.raw, Mapping):
        raise StrictEvidenceError('disposition_type')
    if set(work.raw) != DISPOSITION_FIELDS:
        raise StrictEvidenceError('disposition_keys')
    if work.raw['schema'] != 'convmem.authority-disposition.v1':
        raise StrictEvidenceError('disposition_schema')
    if work.raw['review_role'] != 'kiro-design-reviewer':
        raise StrictEvidenceError('review_role')
    if work.raw['ratifier_role'] != 'ryan-authority-owner':
        raise StrictEvidenceError('ratifier_role')
    if work.raw['review_outcome'] not in {'pass', 'fail'}:
        raise StrictEvidenceError('review_outcome')
    _require_nfc(work.raw['review_actor'], field='review_actor')
    _require_nfc(work.raw['ratifier_actor'], field='ratifier_actor')
    _require_ts(work.raw['reviewed_at'], 'reviewed_at')

def _validate_phase_1(work: SimpleNamespace) -> None:
    _require_ts(work.raw['ratified_at'], 'ratified_at')
    _require_sha(work.raw['rationale_sha256'], 'rationale_sha256')
    work.action = work.raw['action']
    if work.action not in DISPOSITION_ACTIONS:
        raise StrictEvidenceError('disposition_action')
    work.subject = _require_nfc(work.raw['subject_assertion_id'], field='subject_assertion_id')
    if work.subject not in work.by_assertion:
        raise StrictEvidenceError('disposition_subject_missing')
    work.subject_rec = work.by_assertion[work.subject]
    work.subject_semantic = _require_sha(work.raw['subject_semantic_sha256'], 'subject_semantic_sha256')
    if work.subject_semantic != work.subject_rec['semantic_sha256']:
        raise StrictEvidenceError('subject_semantic_mismatch')

def _validate_phase_2(work: SimpleNamespace) -> None:
    work.binding_id = _require_nfc(work.raw['project_binding_id'], field='project_binding_id')
    if work.binding_id != work.subject_rec['project_binding_id']:
        raise StrictEvidenceError('disposition_binding')
    work.targets = work.raw['target_assertion_ids']
    work.expected_heads = work.raw['expected_head_assertion_ids']
    if not isinstance(work.targets, list) or not isinstance(work.expected_heads, list):
        raise StrictEvidenceError('disposition_arrays')
    work.parsed_targets = [_require_nfc(t, field='target_assertion_id') for t in work.targets]
    work.parsed_heads = [_require_nfc(h, field='expected_head_assertion_id') for h in work.expected_heads]
    if work.parsed_targets != sorted(set(work.parsed_targets)):
        raise StrictEvidenceError('target_assertion_ids')
    if work.parsed_heads != sorted(set(work.parsed_heads)):
        raise StrictEvidenceError('expected_head_assertion_ids')

def _x_ar_0(work: SimpleNamespace) -> None:
    if work.subject_rec['record_kind'] != 'decision':
        raise StrictEvidenceError('approval_kind')
    if work.parsed_targets or work.parsed_heads:
        raise StrictEvidenceError('approval_targets')
    if work.basis is not None or work.replaces is not None:
        raise StrictEvidenceError('approval_basis')
    if work.action == 'decision_approved' and work.raw['review_outcome'] != 'pass':
        raise StrictEvidenceError('approval_outcome')
    if work.action == 'decision_rejected' and work.raw['review_outcome'] != 'fail':
        raise StrictEvidenceError('rejection_outcome')
    work.bucket = work.approval_by_subject if work.action == 'decision_approved' else work.rejection_by_subject
    if work.subject in work.bucket or work.subject in work.approval_by_subject or work.subject in work.rejection_by_subject:
        raise StrictEvidenceError('duplicate_decision_disposition')

def _x_ar_1(work: SimpleNamespace) -> None:
    if work.subject_rec['record_kind'] != 'decision':
        raise StrictEvidenceError('revoke_kind')
    if work.parsed_targets or work.parsed_heads:
        raise StrictEvidenceError('revoke_targets')
    if work.basis != work.parent_snapshot_id:
        raise StrictEvidenceError('revoke_basis')
    if work.raw['review_outcome'] != 'pass':
        raise StrictEvidenceError('revoke_outcome')
    work.replaces_nfc = _require_nfc(work.replaces, field='replaces_disposition_ref')
    if not _DISP_ID_RE.fullmatch(work.replaces_nfc):
        raise StrictEvidenceError('revoke_replaces')
    if work.subject in work.revocation_by_subject:
        raise StrictEvidenceError('duplicate_revocation')
    if work.subject in work.rejection_by_subject:
        raise StrictEvidenceError('revoke_of_rejection')

def _x_ar_2(work: SimpleNamespace) -> None:
    if work.subject_rec['record_kind'] not in {'observation', 'verification'}:
        raise StrictEvidenceError('withdraw_kind')
    if work.parsed_targets or work.parsed_heads:
        raise StrictEvidenceError('withdraw_targets')
    if work.basis != work.parent_snapshot_id:
        raise StrictEvidenceError('withdraw_basis')
    if work.replaces is not None:
        raise StrictEvidenceError('withdraw_replaces')
    if work.raw['review_outcome'] != 'pass':
        raise StrictEvidenceError('withdraw_outcome')
    if work.subject in work.withdrawal_by_subject:
        raise StrictEvidenceError('duplicate_withdrawal')

def _x_ar_3(work: SimpleNamespace) -> None:
    if work.raw['review_outcome'] != 'pass':
        raise StrictEvidenceError('supersession_outcome')
    if work.basis != work.parent_snapshot_id:
        raise StrictEvidenceError('supersession_basis')
    if work.replaces is not None:
        raise StrictEvidenceError('supersession_replaces')
    if work.subject in work.supersession_by_subject:
        raise StrictEvidenceError('duplicate_supersession')
    if not work.parsed_targets:
        raise StrictEvidenceError('supersession_targets_empty')
    for target in work.parsed_targets:
        if target not in work.by_assertion:
            raise StrictEvidenceError('supersession_missing_target')
        work.t_rec = work.by_assertion[target]
        if work.t_rec['logical_id'] != work.subject_rec['logical_id']:
            raise StrictEvidenceError('supersession_logical')
        if work.t_rec['record_kind'] != work.subject_rec['record_kind']:
            raise StrictEvidenceError('supersession_kind')
        if work.t_rec['project_binding_id'] != work.subject_rec['project_binding_id']:
            raise StrictEvidenceError('supersession_binding')
    work.record_supersedes = work.subject_rec.get('supersedes_assertion_ids')
    if not isinstance(work.record_supersedes, list):
        raise StrictEvidenceError('supersession_array_mismatch')
    if sorted(work.record_supersedes) != work.parsed_targets:
        raise StrictEvidenceError('supersession_array_mismatch')
    if work.parent_heads_by_logical is not None:
        work.logical = work.subject_rec['logical_id']
        work.expected = sorted(work.parent_heads_by_logical.get(work.logical, ()))
        if work.expected != work.parsed_heads or work.expected != work.parsed_targets:
            raise StrictEvidenceError('supersession_heads')
    elif work.parsed_heads != work.parsed_targets:
        raise StrictEvidenceError('supersession_heads')

def _x_action_rules(work: SimpleNamespace) -> None:

    if work.action in {'decision_approved', 'decision_rejected'}:
        _x_ar_0(work)
        return
    if work.action == 'decision_revoked':
        _x_ar_1(work)
        return
    if work.action == 'evidence_withdrawn':
        _x_ar_2(work)
        return
    if work.action == 'supersession_authorized':
        _x_ar_3(work)
        return


def _validate_phase_3(work: SimpleNamespace) -> None:
    work.basis = work.raw['basis_snapshot_id']
    work.replaces = work.raw['replaces_disposition_ref']

    _x_action_rules(work)
    work.disp_id = disposition_id(work.raw)
    if work.disp_id in work.consumed:
        raise StrictEvidenceError('disposition_duplicate')
    work.stored = dict(work.raw)
    work.stored['target_assertion_ids'] = work.parsed_targets
    work.stored['expected_head_assertion_ids'] = work.parsed_heads
    work.consumed[work.disp_id] = work.stored
    if work.action == 'decision_approved':
        work.approval_by_subject[work.subject] = work.disp_id
    elif work.action == 'decision_rejected':
        work.rejection_by_subject[work.subject] = work.disp_id
    elif work.action == 'decision_revoked':
        work.revocation_by_subject[work.subject] = work.disp_id
    elif work.action == 'evidence_withdrawn':
        work.withdrawal_by_subject[work.subject] = work.disp_id
    elif work.action == 'supersession_authorized':
        work.supersession_by_subject[work.subject] = work.disp_id


def _validate_one_disposition(raw: Any, ctx: SimpleNamespace) -> None:
    """Validate and index one disposition into subject maps."""

    work = SimpleNamespace()
    by_assertion = ctx.by_assertion
    parent_snapshot_id = ctx.parent_snapshot_id
    parent_heads_by_logical = ctx.parent_heads_by_logical
    consumed = ctx.consumed
    approval_by_subject = ctx.approval_by_subject
    rejection_by_subject = ctx.rejection_by_subject
    revocation_by_subject = ctx.revocation_by_subject
    withdrawal_by_subject = ctx.withdrawal_by_subject
    supersession_by_subject = ctx.supersession_by_subject
    work.raw = raw
    work.by_assertion = by_assertion
    work.parent_snapshot_id = parent_snapshot_id
    work.parent_heads_by_logical = parent_heads_by_logical
    work.consumed = consumed
    work.approval_by_subject = approval_by_subject
    work.rejection_by_subject = rejection_by_subject
    work.revocation_by_subject = revocation_by_subject
    work.withdrawal_by_subject = withdrawal_by_subject
    work.supersession_by_subject = supersession_by_subject

    _validate_phase_0(work)
    _validate_phase_1(work)
    _validate_phase_2(work)
    _validate_phase_3(work)



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
        _validate_one_disposition(
            raw,
            SimpleNamespace(
                by_assertion=by_assertion,
                parent_snapshot_id=parent_snapshot_id,
                parent_heads_by_logical=parent_heads_by_logical,
                consumed=consumed,
                approval_by_subject=approval_by_subject,
                rejection_by_subject=rejection_by_subject,
                revocation_by_subject=revocation_by_subject,
                withdrawal_by_subject=withdrawal_by_subject,
                supersession_by_subject=supersession_by_subject,
            ),
        )

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
class ReducedState:  # pylint: disable=R0902  # attributes mirror reduced authority-state fields
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
    if s in ({"fail"}, {"fail", "inconclusive"}):
        return "fail"
    if s in ({"inconclusive"}, {"pass", "inconclusive"}):
        return "inconclusive"
    if "pass" in s and "fail" in s:
        return "conflict"
    return "inconclusive"


def _reduce_consume(work: SimpleNamespace, aid: str, disp_id: str) -> None:
    if disp_id in work.consumed_disps:
        raise StrictEvidenceError("disposition_double_consume")
    work.consumed_disps.add(disp_id)
    work.state_disps[aid].append(disp_id)

def _reduce_phase_0(work: SimpleNamespace) -> None:
    work.by_id = {r["assertion_id"]: dict(r) for r in work.records}
    if len(work.by_id) != len(work.records):
        raise StrictEvidenceError("duplicate_assertion")
    for rec in work.by_id.values():
        if "check_eligibility" not in rec:
            raise StrictEvidenceError("check_eligibility_required")
        if rec["check_eligibility"] not in CHECK_ELIGIBILITY:
            raise StrictEvidenceError("check_eligibility")
        if "provenance_qualification" not in rec:
            raise StrictEvidenceError("qualification_missing")
    if isinstance(work.dispositions, Mapping):
        work.disp_by_id = {k: dict(v) for k, v in work.dispositions.items()}
    else:
        work.disp_by_id = {disposition_id(d): dict(d) for d in work.dispositions}
    work.approvals: dict[str, str] = {}
    work.rejections: dict[str, str] = {}
    work.revocations: dict[str, str] = {}

def _reduce_phase_1(work: SimpleNamespace) -> None:
    work.withdrawals: dict[str, str] = {}
    work.supersessions: dict[str, str] = {}
    for disp_id, disp in work.disp_by_id.items():
        work.action = disp["action"]
        work.subject = disp["subject_assertion_id"]
        if work.action == "decision_approved":
            if work.subject in work.approvals:
                raise StrictEvidenceError("duplicate_approval")
            work.approvals[work.subject] = disp_id
        elif work.action == "decision_rejected":
            if work.subject in work.rejections:
                raise StrictEvidenceError("duplicate_rejection")
            work.rejections[work.subject] = disp_id
        elif work.action == "decision_revoked":
            if work.subject in work.revocations:
                raise StrictEvidenceError("duplicate_revocation")
            work.revocations[work.subject] = disp_id
        elif work.action == "evidence_withdrawn":
            if work.subject in work.withdrawals:
                raise StrictEvidenceError("duplicate_withdrawal")
            work.withdrawals[work.subject] = disp_id
        elif work.action == "supersession_authorized":
            if work.subject in work.supersessions:
                raise StrictEvidenceError("duplicate_supersession")
            work.supersessions[work.subject] = disp_id
        else:
            raise StrictEvidenceError("disposition_action")
    work.superseded_by: dict[str, set[str]] = {}
    work.succ_to_targets: dict[str, list[str]] = {}
    for successor_id, disp_id in work.supersessions.items():
        work.successor = work.by_id.get(successor_id)
        if work.successor is None:
            raise StrictEvidenceError("supersession_missing_successor")
        if work.successor["record_kind"] == "decision" and successor_id in work.rejections:
            raise StrictEvidenceError("supersession_rejected_successor")
        disp = work.disp_by_id[disp_id]
        work.targets = list(disp["target_assertion_ids"])
        if sorted(work.successor.get("supersedes_assertion_ids") or []) != sorted(work.targets):
            raise StrictEvidenceError("supersession_array_mismatch")
        work.succ_to_targets[successor_id] = work.targets
        for target in work.targets:
            if target not in work.by_id:
                raise StrictEvidenceError("supersession_missing_target")
            if target == successor_id:
                raise StrictEvidenceError("supersession_self")
            work.t_rec = work.by_id[target]
            if work.t_rec["logical_id"] != work.successor["logical_id"]:
                raise StrictEvidenceError("supersession_logical")
            if work.t_rec["record_kind"] != work.successor["record_kind"]:
                raise StrictEvidenceError("supersession_kind")
            if work.t_rec["project_binding_id"] != work.successor["project_binding_id"]:
                raise StrictEvidenceError("supersession_binding")
            work.superseded_by.setdefault(target, set()).add(successor_id)
    work.visiting: set[str] = set()

def _x_walk(work: SimpleNamespace, node: str) -> None:
    if node in work.visiting:
        raise StrictEvidenceError("supersession_cycle")
    if node in work.visited:
        return
    work.visiting.add(node)
    for target in work.succ_to_targets.get(node, ()):
        _x_walk(work, target)
    work.visiting.remove(node)
    work.visited.add(node)

def _reduce_phase_2(work: SimpleNamespace) -> None:
    work.visited: set[str] = set()

    for node in work.succ_to_targets:
        _x_walk(work, node)
    work.authority: dict[str, str] = {}
    work.state_disps: dict[str, list[str]] = {aid: [] for aid in work.by_id}
    work.consumed_disps: set[str] = set()


def _reduce_phase_3(work: SimpleNamespace) -> None:
    for aid, rec in work.by_id.items():
        work.kind = rec["record_kind"]
        if aid in work.withdrawals:
            work.authority[aid] = "withdrawn"
            _reduce_consume(work, aid, work.withdrawals[aid])
            continue
        if work.kind == "decision" and aid in work.rejections:
            work.authority[aid] = "rejected"
            _reduce_consume(work, aid, work.rejections[aid])
            continue
        if work.kind == "decision" and aid in work.revocations:
            work.authority[aid] = "revoked"
            _reduce_consume(work, aid, work.revocations[aid])
            work.replaces = work.disp_by_id[work.revocations[aid]]["replaces_disposition_ref"]
            if work.replaces not in work.consumed_disps:
                _reduce_consume(work, aid, work.replaces)
            continue
        if aid in work.superseded_by:
            if work.kind == "decision":
                if aid in work.approvals:
                    _reduce_consume(work, aid, work.approvals[aid])
                elif aid not in work.rejections:
                    raise StrictEvidenceError("decision_disposition_required")
            work.authority[aid] = "superseded"
            for succ in sorted(work.superseded_by[aid]):
                work.state_disps[aid].append(work.supersessions[succ])
            continue
        if work.kind == "decision":
            if aid not in work.approvals:
                raise StrictEvidenceError("decision_disposition_required")
            work.authority[aid] = "approved"
            _reduce_consume(work, aid, work.approvals[aid])
        else:
            work.authority[aid] = "current"
    for successor_id, disp_id in work.supersessions.items():
        if disp_id not in work.consumed_disps:
            _reduce_consume(work, successor_id, disp_id)
    work.heads_by_logical: dict[str, list[str]] = {}
    for aid, rec in work.by_id.items():
        if work.authority[aid] in {"current", "approved"}:
            work.heads_by_logical.setdefault(rec["logical_id"], []).append(aid)
    for heads in work.heads_by_logical.values():
        if len(heads) > 1:
            for aid in heads:
                work.authority[aid] = "conflict"
    work.final_heads_by_logical: dict[str, list[str]] = {}
    for aid, rec in work.by_id.items():
        if work.authority[aid] in {"current", "approved", "conflict"}:
            work.final_heads_by_logical.setdefault(rec["logical_id"], []).append(aid)

def _reduce_phase_4(work: SimpleNamespace) -> dict[str, ReducedState]:
    for logical in work.final_heads_by_logical:
        work.final_heads_by_logical[logical] = sorted(work.final_heads_by_logical[logical])
    work.verifications_by_target: dict[str, list[str]] = {}
    for aid, rec in work.by_id.items():
        if rec["record_kind"] == "verification" and work.authority[aid] in {"current", "conflict"}:
            target = rec["target_assertion_id"]
            if not isinstance(target, str):
                raise StrictEvidenceError("verification_target")
            work.t_rec = work.by_id.get(target)
            if work.t_rec is None:
                raise StrictEvidenceError("verification_target_missing")
            if work.t_rec["record_kind"] == "verification":
                raise StrictEvidenceError("verification_target_kind")
            if work.t_rec["project_binding_id"] != rec["project_binding_id"]:
                raise StrictEvidenceError("verification_target_binding")
            if work.t_rec["record_kind"] == "decision" and work.authority[target] not in {
                "approved",
                "conflict",
                "superseded",
                "revoked",
                "rejected",
            }:
                raise StrictEvidenceError("verification_target_decision")
            work.verifications_by_target.setdefault(target, []).append(aid)
    if work.consumed_disps != set(work.disp_by_id):
        raise StrictEvidenceError("disposition_incomplete_consumption")
    work.result: dict[str, ReducedState] = {}
    for aid, rec in work.by_id.items():
        work.kind = rec["record_kind"]
        work.auth_state = work.authority[aid]
        logical = rec["logical_id"]
        work.head_set = tuple(work.final_heads_by_logical.get(logical, ()))
        work.eligibility = rec["check_eligibility"]
        if work.kind == "verification":
            work.result[aid] = ReducedState(
                assertion_id=aid,
                logical_id=logical,
                record_kind=work.kind,
                authority_state=work.auth_state,
                verification_state="not_applicable",
                subject_head_assertion_ids=work.head_set,
                verification_inputs=(),
                state_disposition_refs=tuple(sorted(set(work.state_disps[aid]))),
                check_eligibility=work.eligibility,
            )
            continue
        work.inputs: list[dict[str, Any]] = []
        work.live = work.verifications_by_target.get(aid, [])
        work.by_vlogical: dict[str, list[str]] = {}
        for vid in work.live:
            work.by_vlogical.setdefault(work.by_id[vid]["logical_id"], []).append(vid)
        work.effective_results: list[str] = []
        work.competing = False
        for vids in work.by_vlogical.values():
            work.live_heads = [v for v in vids if work.authority[v] in {"current", "conflict"}]
            if len(work.live_heads) > 1:
                work.competing = True
            for vid in sorted(work.live_heads):
                work.vrec = work.by_id[vid]
                work.reported = work.vrec["verification_result"]
                work.velig = work.vrec["check_eligibility"]
                if work.velig == "qualified":
                    work.effective = work.reported
                else:
                    work.effective = "inconclusive"
                work.inputs.append(
                    {
                        "assertion_id": vid,
                        "logical_id": work.vrec["logical_id"],
                        "authority_state": work.authority[vid],
                        "reported_result": work.reported,
                        "effective_result": work.effective,
                        "check_eligibility": work.velig,
                    }
                )
                work.effective_results.append(work.effective)
        if work.competing:
            work.verification_state = "conflict"
        else:
            work.verification_state = _truth_table(work.effective_results)
        work.result[aid] = ReducedState(
            assertion_id=aid,
            logical_id=logical,
            record_kind=work.kind,
            authority_state=work.auth_state,
            verification_state=work.verification_state,
            subject_head_assertion_ids=work.head_set,
            verification_inputs=tuple(sorted(work.inputs, key=lambda x: x["assertion_id"])),
            state_disposition_refs=tuple(sorted(set(work.state_disps[aid]))),
            check_eligibility=work.eligibility,
        )
    return work.result

def reduce_complete_bound_state(
    records: Sequence[Mapping[str, Any]], dispositions: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]]
) -> dict[str, ReducedState]:
    """Single complete-bound reducer. Never invoked at query time as a separate reducer."""
    work = SimpleNamespace(records=records, dispositions=dispositions)

    _reduce_phase_0(work)
    _reduce_phase_1(work)
    _reduce_phase_2(work)
    _reduce_phase_3(work)
    return _reduce_phase_4(work)



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
    citation_map["citation_map_payload_sha256"] = sha256_digest(strict_canonical_bytes(body))
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
            "public_ledger_id": public_ledger_id(public_binding_ref=binding_public_ref, assertion_id=aid),
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

    edge_keys = sorted({(e["kind"], e["from_assertion_id"], e["to_assertion_id"]) for e in edges})
    unique_edges = [{"kind": k, "from_assertion_id": f, "to_assertion_id": t} for k, f, t in edge_keys]
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
