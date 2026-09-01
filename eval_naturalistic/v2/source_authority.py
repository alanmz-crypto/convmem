"""Verified source/issuer-backed authority records for P1 occurrence issuance."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from eval_naturalistic.base import (
    StructuralContractError,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.capture_attestation import (
    CaptureAttestationRepository,
    verify_capture_attestation_binding,
)
from eval_naturalistic.v2.identity import OccurrenceReferenceV2, digest_hex, reject_hash_or_locator_identity
from eval_naturalistic.v2.p0_construct import (
    ConstructFreezeAuthorityRepository,
    verify_construct_freeze_parent_binding,
)
from eval_naturalistic.v2.source_issuer_authority import SourceIssuerGrantRepository

_SOURCE_AUTHORITY_TOKEN = object()

REQUIRED_SOURCE_CAPTURE_FIELDS = frozenset(
    {
        "source_system_id",
        "tenant_or_realm_id",
        "authority_scope_id",
        "occurrence_namespace_id",
        "physical_source_instance_id",
        "native_id_namespace",
        "native_record_id",
        "source_revision_or_asof_id",
        "evidence_snapshot_id",
        "raw_record_digest",
        "capture_envelope_digest",
        "issuer_capture_attestation",
    }
)


@dataclass(frozen=True)
class SealedSourceCapturePackageV2:
    """Immutable sealed capture of source truth — not caller-declared identity."""

    capture_body: dict[str, Any]
    canonical_bytes: bytes
    content_digest: str

    _FIELDS = REQUIRED_SOURCE_CAPTURE_FIELDS | {"schema_version"}

    @classmethod
    def from_canonical_bytes(cls, canonical_bytes: bytes) -> "SealedSourceCapturePackageV2":
        import json

        try:
            body = json.loads(canonical_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StructuralContractError("source capture: invalid canonical bytes") from exc
        body = _require_dict(body, "SealedSourceCapturePackageV2")
        _require_no_unknown_props(body, cls._FIELDS, "SealedSourceCapturePackageV2")
        if body.get("schema_version") != "convmem/naturalistic/v2/sealed-source-capture-v2":
            raise StructuralContractError("source capture: wrong schema_version")
        reject_hash_or_locator_identity(body)
        body_without_envelope = {
            key: value for key, value in body.items() if key != "capture_envelope_digest"
        }
        recomputed = hashlib.sha256(canonical_artifact_bytes(body_without_envelope)).hexdigest()
        if recomputed != digest_hex(body["capture_envelope_digest"], "capture_envelope_digest"):
            raise StructuralContractError("source capture: envelope digest mismatch")
        if canonical_artifact_bytes(body) != canonical_bytes:
            raise StructuralContractError("source capture: canonical bytes mismatch")
        return cls(capture_body=body, canonical_bytes=canonical_bytes, content_digest=recomputed)

    def occurrence_fields(self) -> dict[str, str]:
        return {
            key: _require_str(self.capture_body[key], key)
            for key in (
                "source_system_id",
                "tenant_or_realm_id",
                "authority_scope_id",
                "occurrence_namespace_id",
                "physical_source_instance_id",
                "native_id_namespace",
                "native_record_id",
                "source_revision_or_asof_id",
            )
        }

    def evidence_snapshot_id(self) -> str:
        return _require_str(self.capture_body["evidence_snapshot_id"], "evidence_snapshot_id")

    def issuer_capture_attestation(self) -> str:
        return _require_str(
            self.capture_body["issuer_capture_attestation"], "issuer_capture_attestation"
        )


def seal_source_capture_package(body: dict[str, Any]) -> SealedSourceCapturePackageV2:
    """Seal ordinary source capture bytes for authority verification."""

    working = dict(body)
    working.setdefault("schema_version", "convmem/naturalistic/v2/sealed-source-capture-v2")
    if "capture_envelope_digest" in working:
        raise StructuralContractError("source capture: envelope digest is assigned at seal time")
    _require_no_unknown_props(working, SealedSourceCapturePackageV2._FIELDS - {"capture_envelope_digest"}, "source capture seal")
    reject_hash_or_locator_identity(working)
    digest_hex(working["issuer_capture_attestation"], "issuer_capture_attestation")
    envelope_digest = hashlib.sha256(canonical_artifact_bytes(working)).hexdigest()
    working["capture_envelope_digest"] = envelope_digest
    canonical_bytes = canonical_artifact_bytes(working)
    return SealedSourceCapturePackageV2.from_canonical_bytes(canonical_bytes)


@dataclass(frozen=True)
class VerifiedSourceAuthorityV2:
    """Authority record derived from a verified sealed source capture — not caller strings."""

    source_capture_digest: str
    occurrence_reference: OccurrenceReferenceV2
    evidence_snapshot_id: str
    issuer_capture_attestation: str
    authority_record_digest: str

    def __init__(
        self,
        *,
        _token: object,
        source_capture_digest: str,
        occurrence_reference: OccurrenceReferenceV2,
        evidence_snapshot_id: str,
        issuer_capture_attestation: str,
        authority_record_digest: str,
    ) -> None:
        if _token is not _SOURCE_AUTHORITY_TOKEN:
            raise TypeError(
                "VerifiedSourceAuthorityV2 is only materialized from verified source capture"
            )
        object.__setattr__(self, "source_capture_digest", source_capture_digest)
        object.__setattr__(self, "occurrence_reference", occurrence_reference)
        object.__setattr__(self, "evidence_snapshot_id", evidence_snapshot_id)
        object.__setattr__(self, "issuer_capture_attestation", issuer_capture_attestation)
        object.__setattr__(self, "authority_record_digest", authority_record_digest)

    def to_dict(self) -> dict[str, str]:
        return {
            "source_capture_digest": self.source_capture_digest,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "issuer_capture_attestation": self.issuer_capture_attestation,
            "authority_record_digest": self.authority_record_digest,
        }


def verify_source_capture_authority(
    capture: SealedSourceCapturePackageV2 | bytes,
    *,
    attestation_repository: CaptureAttestationRepository | None = None,
    p0_repository: ConstructFreezeAuthorityRepository | None = None,
    construct_freeze_digest: str | None = None,
    construct_freeze_artifact_id: str | None = None,
) -> VerifiedSourceAuthorityV2:
    """Derive authoritative occurrence identity from verified source capture only."""

    if attestation_repository is None:
        raise StructuralContractError("source capture authority requires attestation repository")
    if p0_repository is None:
        raise StructuralContractError("source capture authority requires construct-freeze repository")
    if not construct_freeze_digest:
        raise StructuralContractError("source capture authority requires construct-freeze digest")
    if not construct_freeze_artifact_id:
        raise StructuralContractError("source capture authority requires construct-freeze artifact id")
    manifest = verify_construct_freeze_parent_binding(
        parent_kind="construct_freeze",
        parent_artifact_id=construct_freeze_artifact_id,
        parent_digest=construct_freeze_digest,
        construct_freeze_digest=construct_freeze_digest,
        repository=p0_repository,
    )
    issuer_grant_repository = SourceIssuerGrantRepository.from_construct_freeze(manifest)
    if isinstance(capture, bytes):
        canonical_bytes = capture
    elif isinstance(capture, SealedSourceCapturePackageV2):
        canonical_bytes = capture.canonical_bytes
    else:
        raise TypeError("verify_source_capture_authority requires bytes or SealedSourceCapturePackageV2")
    sealed = SealedSourceCapturePackageV2.from_canonical_bytes(canonical_bytes)
    fields = sealed.occurrence_fields()
    occurrence = OccurrenceReferenceV2(
        source_system_id=fields["source_system_id"],
        tenant_or_realm_id=fields["tenant_or_realm_id"],
        authority_scope_id=fields["authority_scope_id"],
        occurrence_namespace_id=fields["occurrence_namespace_id"],
        physical_source_instance_id=fields["physical_source_instance_id"],
        native_id_namespace=fields["native_id_namespace"],
        native_record_id=fields["native_record_id"],
        source_revision_or_asof_id=fields["source_revision_or_asof_id"],
    )
    attestation_digest = digest_hex(
        sealed.issuer_capture_attestation(), "issuer_capture_attestation"
    )
    verify_capture_attestation_binding(
        attestation_digest=attestation_digest,
        occurrence_reference=occurrence,
        evidence_snapshot_id=sealed.evidence_snapshot_id(),
        repository=attestation_repository,
        issuer_grant_repository=issuer_grant_repository,
    )
    record_body = {
        "source_capture_digest": sealed.content_digest,
        "occurrence_reference": occurrence.to_dict(),
        "evidence_snapshot_id": sealed.evidence_snapshot_id(),
        "issuer_capture_attestation": sealed.issuer_capture_attestation(),
    }
    authority_record_digest = hashlib.sha256(canonical_artifact_bytes(record_body)).hexdigest()
    return VerifiedSourceAuthorityV2(
        _token=_SOURCE_AUTHORITY_TOKEN,
        source_capture_digest=sealed.content_digest,
        occurrence_reference=occurrence,
        evidence_snapshot_id=sealed.evidence_snapshot_id(),
        issuer_capture_attestation=sealed.issuer_capture_attestation(),
        authority_record_digest=authority_record_digest,
    )


def reverify_source_authority_record(record: VerifiedSourceAuthorityV2) -> VerifiedSourceAuthorityV2:
    """Recompute authority digest from embedded fields — integrity check only."""

    record_body = {
        "source_capture_digest": record.source_capture_digest,
        "occurrence_reference": record.occurrence_reference.to_dict(),
        "evidence_snapshot_id": record.evidence_snapshot_id,
        "issuer_capture_attestation": record.issuer_capture_attestation,
    }
    expected = hashlib.sha256(canonical_artifact_bytes(record_body)).hexdigest()
    if expected != record.authority_record_digest:
        raise StructuralContractError("source authority record digest mismatch")
    return record
