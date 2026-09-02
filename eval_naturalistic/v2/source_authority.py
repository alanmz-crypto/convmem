"""Verified source/issuer-backed authority records for P1 occurrence issuance."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from eval_naturalistic.base import (
    StructuralContractError,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.identity import (
    OccurrenceReferenceV2,
    digest_hex,
    occurrence_reference_from_fields,
    reject_hash_or_locator_identity,
)
from eval_naturalistic.v2.authority_substrate import (
    resolve_shared_authority_source,
    same_authority_object,
)

if TYPE_CHECKING:
    from eval_naturalistic.v2.capture_attestation import CaptureAttestationRepository
    from eval_naturalistic.v2.issuer_attestation_capability import (
        IssuerCaptureAttestationCapabilityRepository,
    )
    from eval_naturalistic.v2.p0_construct import ConstructFreezeAuthorityRepository
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

    def source_evidence_digest(self) -> str:
        """Digest source evidence independently of its attestation pointer.

        The attestation is written into the capture envelope after issuance is
        prepared.  Excluding only that authority-link field avoids a circular
        digest while retaining every source identity, snapshot, raw-record,
        and capture field in the evidence commitment.
        """

        body = {
            key: value
            for key, value in self.capture_body.items()
            if key not in {"issuer_capture_attestation", "capture_envelope_digest"}
        }
        return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


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
class VerifiedSourceAuthorityV2:  # pylint: disable=too-many-instance-attributes
    """Authority record derived from a verified sealed source capture — not caller strings."""

    source_capture_digest: str
    occurrence_reference: OccurrenceReferenceV2
    evidence_snapshot_id: str
    issuer_capture_attestation: str
    authority_record_digest: str
    construct_freeze_digest: str
    construct_freeze_artifact_id: str
    raw_record_digest: str
    _authority_source: Any

    def __init__(
        self,
        *,
        _token: object,
        source_capture_digest: str,
        occurrence_reference: OccurrenceReferenceV2,
        evidence_snapshot_id: str,
        issuer_capture_attestation: str,
        authority_record_digest: str,
        construct_freeze_digest: str = "",
        construct_freeze_artifact_id: str = "",
        raw_record_digest: str = "",
        _authority_source: Any = None,
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
        object.__setattr__(self, "construct_freeze_digest", construct_freeze_digest)
        object.__setattr__(self, "construct_freeze_artifact_id", construct_freeze_artifact_id)
        object.__setattr__(self, "raw_record_digest", raw_record_digest)
        object.__setattr__(self, "_authority_source", _authority_source)

    def to_dict(self) -> dict[str, str]:
        return {
            "source_capture_digest": self.source_capture_digest,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "issuer_capture_attestation": self.issuer_capture_attestation,
            "authority_record_digest": self.authority_record_digest,
            "construct_freeze_digest": self.construct_freeze_digest,
            "construct_freeze_artifact_id": self.construct_freeze_artifact_id,
            "raw_record_digest": self.raw_record_digest,
        }

    def authority_source(self) -> Any:
        """Return the non-serialized source that produced this authority."""

        return self._authority_source


def verify_source_capture_authority(  # pylint: disable=too-many-arguments
    capture: SealedSourceCapturePackageV2 | bytes,
    *,
    attestation_repository: CaptureAttestationRepository | None = None,
    issuer_capability_repository: IssuerCaptureAttestationCapabilityRepository | None = None,
    p0_repository: ConstructFreezeAuthorityRepository | None = None,
    construct_freeze_digest: str | None = None,
    construct_freeze_artifact_id: str | None = None,
    authority_source: Any = None,
) -> VerifiedSourceAuthorityV2:
    """Derive authoritative occurrence identity from verified source capture only."""

    if not construct_freeze_digest:
        raise StructuralContractError("source capture authority requires construct-freeze digest")
    if not construct_freeze_artifact_id:
        raise StructuralContractError("source capture authority requires construct-freeze artifact id")
    if authority_source is None and attestation_repository is None:
        raise StructuralContractError("source capture authority requires attestation repository")
    if authority_source is None and issuer_capability_repository is None:
        raise StructuralContractError(
            "source capture authority requires issuer capability repository"
        )
    if authority_source is None and p0_repository is None:
        raise StructuralContractError("source capture authority requires construct-freeze repository")
    source = resolve_shared_authority_source(
        explicit=authority_source,
        repositories=tuple(
            repo
            for repo in (p0_repository, issuer_capability_repository, attestation_repository)
            if repo is not None
        ),
    )
    from eval_naturalistic.v2.p0_construct import (
        verify_construct_freeze_manifest,
        verify_construct_freeze_parent_binding,
    )
    from eval_naturalistic.v2.source_issuer_authority import SourceIssuerGrantRepository

    trusted_manifest = source.resolve_construct_freeze(
        artifact_id=construct_freeze_artifact_id,
        content_digest=construct_freeze_digest,
    )
    if p0_repository is None:
        manifest = verify_construct_freeze_manifest(trusted_manifest)
    else:
        manifest = verify_construct_freeze_parent_binding(
            parent_kind="construct_freeze",
            parent_artifact_id=construct_freeze_artifact_id,
            parent_digest=construct_freeze_digest,
            construct_freeze_digest=construct_freeze_digest,
            repository=p0_repository,
            authority_source=source,
        )
        if trusted_manifest.to_dict() != manifest.to_dict():
            raise StructuralContractError("source capture authority: P0 source resolution mismatch")
    issuer_grant_repository = SourceIssuerGrantRepository.from_construct_freeze(manifest)
    if isinstance(capture, bytes):
        canonical_bytes = capture
    elif isinstance(capture, SealedSourceCapturePackageV2):
        canonical_bytes = capture.canonical_bytes
    else:
        raise TypeError("verify_source_capture_authority requires bytes or SealedSourceCapturePackageV2")
    sealed = SealedSourceCapturePackageV2.from_canonical_bytes(canonical_bytes)
    fields = sealed.occurrence_fields()
    occurrence = occurrence_reference_from_fields(fields)
    attestation_digest = digest_hex(
        sealed.issuer_capture_attestation(), "issuer_capture_attestation"
    )
    if (
        issuer_capability_repository is not None
        and issuer_capability_repository.construct_freeze_digest() != construct_freeze_digest
    ):
        raise StructuralContractError(
            "source capture authority: issuer capability construct-freeze digest mismatch"
        )
    _verify_capture_attestation_binding(
        attestation_digest=attestation_digest,
        occurrence_reference=occurrence,
        evidence_snapshot_id=sealed.evidence_snapshot_id(),
        source_capture_digest=sealed.source_evidence_digest(),
        raw_record_digest=digest_hex(sealed.capture_body["raw_record_digest"], "raw_record_digest"),
        construct_freeze_digest=construct_freeze_digest,
        construct_freeze_artifact_id=construct_freeze_artifact_id,
        repository=attestation_repository,
        issuer_grant_repository=issuer_grant_repository,
        issuer_capability_repository=issuer_capability_repository,
        authority_source=source,
    )
    trusted_capture = source.resolve_source_capture(sealed.source_evidence_digest())
    if (
        trusted_capture.source_evidence_digest() != sealed.source_evidence_digest()
        or trusted_capture.canonical_bytes != sealed.canonical_bytes
    ):
        raise StructuralContractError("source capture authority: capture bytes not independently resolved")
    record_body = {
        "source_capture_digest": sealed.source_evidence_digest(),
        "occurrence_reference": occurrence.to_dict(),
        "evidence_snapshot_id": sealed.evidence_snapshot_id(),
        "issuer_capture_attestation": sealed.issuer_capture_attestation(),
        "construct_freeze_digest": construct_freeze_digest,
        "construct_freeze_artifact_id": construct_freeze_artifact_id,
        "raw_record_digest": digest_hex(sealed.capture_body["raw_record_digest"], "raw_record_digest"),
    }
    authority_record_digest = hashlib.sha256(canonical_artifact_bytes(record_body)).hexdigest()
    return VerifiedSourceAuthorityV2(
        _token=_SOURCE_AUTHORITY_TOKEN,
        source_capture_digest=sealed.source_evidence_digest(),
        occurrence_reference=occurrence,
        evidence_snapshot_id=sealed.evidence_snapshot_id(),
        issuer_capture_attestation=sealed.issuer_capture_attestation(),
        authority_record_digest=authority_record_digest,
        construct_freeze_digest=construct_freeze_digest,
        construct_freeze_artifact_id=construct_freeze_artifact_id,
        raw_record_digest=digest_hex(sealed.capture_body["raw_record_digest"], "raw_record_digest"),
        _authority_source=source,
    )


def reverify_source_authority_record(record: VerifiedSourceAuthorityV2) -> VerifiedSourceAuthorityV2:
    """Recompute authority digest from embedded fields — integrity check only."""

    digest_hex(record.source_capture_digest, "source_capture_digest")
    digest_hex(record.construct_freeze_digest, "construct_freeze_digest")
    digest_hex(record.raw_record_digest, "raw_record_digest")
    if not record.construct_freeze_artifact_id:
        raise StructuralContractError("source authority record missing construct-freeze artifact id")
    record_body = {
        "source_capture_digest": record.source_capture_digest,
        "occurrence_reference": record.occurrence_reference.to_dict(),
        "evidence_snapshot_id": record.evidence_snapshot_id,
        "issuer_capture_attestation": record.issuer_capture_attestation,
        "construct_freeze_digest": record.construct_freeze_digest,
        "construct_freeze_artifact_id": record.construct_freeze_artifact_id,
        "raw_record_digest": record.raw_record_digest,
    }
    expected = hashlib.sha256(canonical_artifact_bytes(record_body)).hexdigest()
    if expected != record.authority_record_digest:
        raise StructuralContractError("source authority record digest mismatch")
    return record


def _verify_capture_attestation_binding(  # pylint: disable=too-many-arguments
    *,
    attestation_digest: str,
    occurrence_reference: OccurrenceReferenceV2,
    evidence_snapshot_id: str,
    source_capture_digest: str,
    raw_record_digest: str,
    construct_freeze_digest: str,
    construct_freeze_artifact_id: str,
    repository: CaptureAttestationRepository | None,
    issuer_grant_repository: "SourceIssuerGrantRepository",
    issuer_capability_repository: IssuerCaptureAttestationCapabilityRepository | None,
    authority_source: Any,
) -> None:
    from eval_naturalistic.v2.capture_attestation import verify_capture_attestation_artifact
    from eval_naturalistic.v2.issuer_attestation_capability import (
        reverify_issuer_capture_attestation_capability,
    )

    artifact = (
        repository.resolve(attestation_digest)
        if repository is not None
        else authority_source.resolve_capture_attestation(attestation_digest)
    )
    trusted_artifact = authority_source.resolve_capture_attestation(attestation_digest)
    verify_capture_attestation_artifact(artifact)
    verify_capture_attestation_artifact(trusted_artifact)
    same_authority_object(
        artifact,
        trusted_artifact,
        message="capture attestation is not independently resolved",
    )
    if artifact.occurrence_reference.same_occurrence_as(occurrence_reference) is False:
        raise StructuralContractError("capture attestation occurrence mismatch")
    if artifact.evidence_snapshot_id != evidence_snapshot_id:
        raise StructuralContractError("capture attestation evidence snapshot mismatch")
    if artifact.attestation_evidence_digest() != attestation_digest:
        raise StructuralContractError("capture attestation digest mismatch")
    trusted_parent = authority_source.resolve_construct_freeze(
        artifact_id=artifact.construct_freeze_artifact_id,
        content_digest=artifact.construct_freeze_digest,
    )
    if (
        artifact.construct_freeze_digest != construct_freeze_digest
        or artifact.construct_freeze_artifact_id != construct_freeze_artifact_id
        or trusted_parent.header.content_digest != artifact.construct_freeze_digest
        or trusted_parent.header.artifact_id != artifact.construct_freeze_artifact_id
    ):
        raise StructuralContractError("capture attestation: construct-freeze authority mismatch")
    if artifact.source_capture_digest != source_capture_digest:
        raise StructuralContractError("capture attestation: source capture digest mismatch")
    if artifact.raw_record_digest != raw_record_digest:
        raise StructuralContractError("capture attestation: raw record digest mismatch")
    grant = issuer_grant_repository.resolve(
        issuer_identity=artifact.issuer_identity,
        source_system_id=occurrence_reference.source_system_id,
        authority_scope_id=occurrence_reference.authority_scope_id,
    )
    if grant.grant_digest != artifact.issuer_grant_digest:
        raise StructuralContractError("capture attestation: issuer grant digest mismatch")
    capability = (
        issuer_capability_repository.resolve(
            issuer_identity=artifact.issuer_identity,
            issuer_grant_digest=artifact.issuer_grant_digest,
        )
        if issuer_capability_repository is not None
        else authority_source.resolve_issuer_capability(
            issuer_identity=artifact.issuer_identity,
            issuer_grant_digest=artifact.issuer_grant_digest,
            construct_freeze_digest=construct_freeze_digest,
        )
    )
    reverify_issuer_capture_attestation_capability(capability)
    if capability.capability_digest != artifact.issuer_attestation_capability_digest:
        raise StructuralContractError(
            "capture attestation: issuer attestation capability digest mismatch"
        )
    if capability.construct_freeze_digest != construct_freeze_digest:
        raise StructuralContractError(
            "capture attestation: capability construct-freeze binding mismatch"
        )
    trusted_capability = authority_source.resolve_issuer_capability(
        issuer_identity=artifact.issuer_identity,
        issuer_grant_digest=artifact.issuer_grant_digest,
        construct_freeze_digest=artifact.construct_freeze_digest,
    )
    same_authority_object(
        capability,
        trusted_capability,
        message="capture attestation capability is not independently resolved",
    )
