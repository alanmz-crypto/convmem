"""Source-backed opaque resolver authority for Naturalistic V2 P2.

The resolver is deliberately a narrow adapter over already verified P1/P2
authority.  It does not discover targets, adjudicate evidence, or expose any
resolver state through the adjudication view.  The only public issuance path
derives its input from a verified P1 evidence seal and V2-02 capability
manifest, runs the closed resolver implementation, and seals a content-bound
manifest.
"""

# Durable authority records repeat validation and serialization blocks by
# design.  Keep the contract visible at the boundary.
# pylint: disable=duplicate-code,too-many-instance-attributes,too-many-lines
# pylint: disable=too-many-arguments,too-many-locals

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from eval_naturalistic.base import (
    ArtifactHeaderV1,
    StructuralContractError,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
    strip_digest_metadata,
)
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.adapters.capability import CapabilityVectorV2
from eval_naturalistic.v2.adapters.capability_manifest import (
    SealedCapabilityManifestV2,
    verify_capability_manifest,
)
from eval_naturalistic.v2.authority_issuance import SealedP1AuthorityV2
from eval_naturalistic.v2.evidence import (
    ConditionNeutralEvidenceAvailabilityV2,
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
)
from eval_naturalistic.v2.identity import OccurrenceReferenceV2, digest_hex

if TYPE_CHECKING:
    from eval_naturalistic.v2.authority_substrate import IndependentAuthoritySourceV2
    from eval_naturalistic.v2.lineage_attestation import LineageAttestationRepository
    from eval_naturalistic.v2.p0_construct import ConstructFreezeAuthorityRepository


RESOLVER_MANIFEST_SCHEMA = "convmem/naturalistic/v2/opaque-resolver-manifest-v2"
RESOLVER_ARTIFACT_KIND = "opaque-resolver-manifest-v2"
RESOLVER_IMPLEMENTATION_ID = "naturalistic-v2-opaque-availability-resolver"

# The implementation registry is intentionally closed.  Adding a resolver is
# a source change that gets a new implementation identity; callers cannot
# register a resolver or declare its digest through an artifact field.
_TRUSTED_RESOLVER_IMPLEMENTATION_IDS = frozenset({RESOLVER_IMPLEMENTATION_ID})
_REPO_ROOT = Path(__file__).resolve().parents[2]
_RESOLVER_IMPLEMENTATION_MODULES = (
    "canonical_json.py",
    "eval_naturalistic/base.py",
    "eval_naturalistic/digest.py",
    "eval_naturalistic/v2/adapters/capability.py",
    "eval_naturalistic/v2/evidence.py",
    "eval_naturalistic/v2/identity.py",
    "eval_naturalistic/v2/resolver.py",
)


class ResolverResultV2(str, Enum):
    """The locked P2 resolver result domain."""

    EXACT_MATCH = "EXACT_MATCH"
    SUMMARY_ONLY = "SUMMARY_ONLY"
    NO_MATCH = "NO_MATCH"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    ERROR = "ERROR"


_RESOLVER_INPUT_TOKEN = object()
_RESOLVER_OUTPUT_TOKEN = object()
_RESOLVER_MANIFEST_TOKEN = object()


def _required(data: dict[str, Any], field_name: str) -> Any:
    try:
        return data[field_name]
    except KeyError as exc:
        raise StructuralContractError(
            f"OpaqueResolverManifestV2: missing required property '{field_name}'"
        ) from exc


def _digest(value: Any, field_name: str) -> str:
    return digest_hex(value, field_name)


def _canonical_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_artifact_bytes(value)).hexdigest()


def _manifest_content_digest(data: dict[str, Any]) -> str:
    return _canonical_digest(strip_digest_metadata(data))


def _derive_artifact_id(content_digest: str) -> str:
    return f"nps2_{RESOLVER_ARTIFACT_KIND}_{content_digest}"


def _hash_file(relative_path: str) -> str:
    try:
        content = (_REPO_ROOT / relative_path).read_bytes()
    except OSError as exc:
        raise StructuralContractError(
            f"resolver implementation module unavailable: {relative_path}"
        ) from exc
    return hashlib.sha256(content).hexdigest()


def compute_resolver_implementation_digest() -> str:
    """Compute the current digest of the closed resolver implementation."""

    manifest = {
        "implementation_id": RESOLVER_IMPLEMENTATION_ID,
        "implementation_version": 2,
        "governed_files": [
            {"path": path, "content_digest": _hash_file(path)}
            for path in _RESOLVER_IMPLEMENTATION_MODULES
        ],
    }
    return hashlib.sha256(
        b"convmem/naturalistic/v2/resolver-implementation\0"
        + canonical_artifact_bytes(manifest)
    ).hexdigest()


def trusted_resolver_implementation_identity() -> dict[str, str]:
    """Return the only implementation identity accepted by P2 authority."""

    return {
        "resolver_implementation_id": RESOLVER_IMPLEMENTATION_ID,
        "resolver_implementation_digest": compute_resolver_implementation_digest(),
    }


@dataclass(frozen=True)
class ResolverInputV2:  # pylint: disable=too-many-instance-attributes
    """Canonical resolver input derived only from verified upstream authority."""

    evidence_seal_artifact_id: str
    evidence_seal_digest: str
    capability_manifest_artifact_id: str
    capability_manifest_digest: str
    construct_freeze_artifact_id: str
    construct_freeze_digest: str
    episode_id: str
    occurrence_reference: OccurrenceReferenceV2
    occurrence_issuance_digest: str
    source_authority_digest: str
    source_capture_digest: str
    issuer_implementation_revision: str
    p1_adapter_implementation_digest: str
    evidence_snapshot_id: str
    raw_record_digest: str
    canonical_content_digest: str
    canonicalization_profile_digest: str
    capability_vector: CapabilityVectorV2
    condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2

    _FIELDS = {
        "evidence_seal_artifact_id",
        "evidence_seal_digest",
        "capability_manifest_artifact_id",
        "capability_manifest_digest",
        "construct_freeze_artifact_id",
        "construct_freeze_digest",
        "episode_id",
        "occurrence_reference",
        "occurrence_issuance_digest",
        "source_authority_digest",
        "source_capture_digest",
        "issuer_implementation_revision",
        "p1_adapter_implementation_digest",
        "evidence_snapshot_id",
        "raw_record_digest",
        "canonical_content_digest",
        "canonicalization_profile_digest",
        "capability_vector",
        "condition_neutral_evidence_availability",
    }

    def __init__(
        self,
        *,
        _token: object,
        evidence_seal_artifact_id: str,
        evidence_seal_digest: str,
        capability_manifest_artifact_id: str,
        capability_manifest_digest: str,
        construct_freeze_artifact_id: str,
        construct_freeze_digest: str,
        episode_id: str,
        occurrence_reference: OccurrenceReferenceV2,
        occurrence_issuance_digest: str,
        source_authority_digest: str,
        source_capture_digest: str,
        issuer_implementation_revision: str,
        p1_adapter_implementation_digest: str,
        evidence_snapshot_id: str,
        raw_record_digest: str,
        canonical_content_digest: str,
        canonicalization_profile_digest: str,
        capability_vector: CapabilityVectorV2,
        condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2,
    ) -> None:
        if _token is not _RESOLVER_INPUT_TOKEN:
            raise TypeError(
                "ResolverInputV2 is derived only from verified P1/P2 authority"
            )
        values = {
            "evidence_seal_artifact_id": evidence_seal_artifact_id,
            "evidence_seal_digest": evidence_seal_digest,
            "capability_manifest_artifact_id": capability_manifest_artifact_id,
            "capability_manifest_digest": capability_manifest_digest,
            "construct_freeze_artifact_id": construct_freeze_artifact_id,
            "construct_freeze_digest": construct_freeze_digest,
            "episode_id": episode_id,
            "occurrence_reference": occurrence_reference,
            "occurrence_issuance_digest": occurrence_issuance_digest,
            "source_authority_digest": source_authority_digest,
            "source_capture_digest": source_capture_digest,
            "issuer_implementation_revision": issuer_implementation_revision,
            "p1_adapter_implementation_digest": p1_adapter_implementation_digest,
            "evidence_snapshot_id": evidence_snapshot_id,
            "raw_record_digest": raw_record_digest,
            "canonical_content_digest": canonical_content_digest,
            "canonicalization_profile_digest": canonicalization_profile_digest,
            "capability_vector": capability_vector,
            "condition_neutral_evidence_availability": condition_neutral_evidence_availability,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @classmethod
    def from_verified_authority(
        cls,
        p1_authority: SealedP1AuthorityV2,
        capability: SealedCapabilityManifestV2,
    ) -> "ResolverInputV2":
        p1 = p1_authority.manifest
        cap = capability.manifest
        p1_digest = p1.header.content_digest
        cap_digest = cap.header.content_digest
        if not p1_digest or not cap_digest:
            raise StructuralContractError("resolver input requires sealed P1/P2 digests")
        if not p1.header.artifact_id or not cap.header.artifact_id:
            raise StructuralContractError("resolver input requires sealed P1/P2 artifact IDs")
        if cap.raw_record_digest is None:
            raise StructuralContractError("resolver input requires raw-record binding")
        return cls(
            _token=_RESOLVER_INPUT_TOKEN,
            evidence_seal_artifact_id=p1.header.artifact_id,
            evidence_seal_digest=p1_digest,
            capability_manifest_artifact_id=cap.header.artifact_id,
            capability_manifest_digest=cap_digest,
            construct_freeze_artifact_id=cap.construct_freeze_artifact_id,
            construct_freeze_digest=cap.construct_freeze_digest,
            episode_id=cap.episode_id,
            occurrence_reference=cap.occurrence_reference,
            occurrence_issuance_digest=cap.occurrence_issuance_digest,
            source_authority_digest=cap.source_authority_digest,
            source_capture_digest=cap.source_capture_digest,
            issuer_implementation_revision=cap.issuer_implementation_revision,
            p1_adapter_implementation_digest=cap.p1_adapter_implementation_digest,
            evidence_snapshot_id=cap.evidence_snapshot_id,
            raw_record_digest=cap.raw_record_digest,
            canonical_content_digest=cap.canonical_content_digest,
            canonicalization_profile_digest=cap.canonicalization_profile_digest,
            capability_vector=cap.capability_vector,
            condition_neutral_evidence_availability=(
                cap.condition_neutral_evidence_availability
            ),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResolverInputV2":
        data = _require_dict(data, "ResolverInputV2")
        _require_no_unknown_props(data, cls._FIELDS, "ResolverInputV2")
        return cls(
            _token=_RESOLVER_INPUT_TOKEN,
            evidence_seal_artifact_id=_require_str(
                _required(data, "evidence_seal_artifact_id"),
                "evidence_seal_artifact_id",
            ),
            evidence_seal_digest=_digest(
                _required(data, "evidence_seal_digest"), "evidence_seal_digest"
            ),
            capability_manifest_artifact_id=_require_str(
                _required(data, "capability_manifest_artifact_id"),
                "capability_manifest_artifact_id",
            ),
            capability_manifest_digest=_digest(
                _required(data, "capability_manifest_digest"),
                "capability_manifest_digest",
            ),
            construct_freeze_artifact_id=_require_str(
                _required(data, "construct_freeze_artifact_id"),
                "construct_freeze_artifact_id",
            ),
            construct_freeze_digest=_digest(
                _required(data, "construct_freeze_digest"), "construct_freeze_digest"
            ),
            episode_id=_require_str(_required(data, "episode_id"), "episode_id"),
            occurrence_reference=OccurrenceReferenceV2.from_dict(
                _require_dict(_required(data, "occurrence_reference"), "occurrence_reference")
            ),
            occurrence_issuance_digest=_digest(
                _required(data, "occurrence_issuance_digest"),
                "occurrence_issuance_digest",
            ),
            source_authority_digest=_digest(
                _required(data, "source_authority_digest"), "source_authority_digest"
            ),
            source_capture_digest=_digest(
                _required(data, "source_capture_digest"), "source_capture_digest"
            ),
            issuer_implementation_revision=_require_str(
                _required(data, "issuer_implementation_revision"),
                "issuer_implementation_revision",
            ),
            p1_adapter_implementation_digest=_digest(
                _required(data, "p1_adapter_implementation_digest"),
                "p1_adapter_implementation_digest",
            ),
            evidence_snapshot_id=_require_str(
                _required(data, "evidence_snapshot_id"), "evidence_snapshot_id"
            ),
            raw_record_digest=_digest(
                _required(data, "raw_record_digest"), "raw_record_digest"
            ),
            canonical_content_digest=_digest(
                _required(data, "canonical_content_digest"),
                "canonical_content_digest",
            ),
            canonicalization_profile_digest=_digest(
                _required(data, "canonicalization_profile_digest"),
                "canonicalization_profile_digest",
            ),
            capability_vector=CapabilityVectorV2.from_dict(
                _require_dict(_required(data, "capability_vector"), "capability_vector")
            ),
            condition_neutral_evidence_availability=ConditionNeutralEvidenceAvailabilityV2.from_dict(
                _require_dict(
                    _required(data, "condition_neutral_evidence_availability"),
                    "condition_neutral_evidence_availability",
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_seal_artifact_id": self.evidence_seal_artifact_id,
            "evidence_seal_digest": self.evidence_seal_digest,
            "capability_manifest_artifact_id": self.capability_manifest_artifact_id,
            "capability_manifest_digest": self.capability_manifest_digest,
            "construct_freeze_artifact_id": self.construct_freeze_artifact_id,
            "construct_freeze_digest": self.construct_freeze_digest,
            "episode_id": self.episode_id,
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "occurrence_issuance_digest": self.occurrence_issuance_digest,
            "source_authority_digest": self.source_authority_digest,
            "source_capture_digest": self.source_capture_digest,
            "issuer_implementation_revision": self.issuer_implementation_revision,
            "p1_adapter_implementation_digest": self.p1_adapter_implementation_digest,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "raw_record_digest": self.raw_record_digest,
            "canonical_content_digest": self.canonical_content_digest,
            "canonicalization_profile_digest": self.canonicalization_profile_digest,
            "capability_vector": self.capability_vector.to_dict(),
            "condition_neutral_evidence_availability": (
                self.condition_neutral_evidence_availability.to_dict()
            ),
        }


@dataclass(frozen=True)
class ResolverOutputV2:
    """Canonical output of the closed resolver implementation."""

    resolver_result: ResolverResultV2
    source_presence: SourcePresenceV2
    verbatim_evidence_availability: VerbatimEvidenceAvailabilityV2
    summary_evidence_availability: SummaryEvidenceAvailabilityV2
    canonical_content_digest: str

    _FIELDS = {
        "resolver_result",
        "source_presence",
        "verbatim_evidence_availability",
        "summary_evidence_availability",
        "canonical_content_digest",
    }

    def __init__(
        self,
        *,
        _token: object,
        resolver_result: ResolverResultV2,
        source_presence: SourcePresenceV2,
        verbatim_evidence_availability: VerbatimEvidenceAvailabilityV2,
        summary_evidence_availability: SummaryEvidenceAvailabilityV2,
        canonical_content_digest: str,
    ) -> None:
        if _token is not _RESOLVER_OUTPUT_TOKEN:
            raise TypeError("ResolverOutputV2 is produced only by the trusted resolver")
        values = {
            "resolver_result": resolver_result,
            "source_presence": source_presence,
            "verbatim_evidence_availability": verbatim_evidence_availability,
            "summary_evidence_availability": summary_evidence_availability,
            "canonical_content_digest": canonical_content_digest,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResolverOutputV2":
        data = _require_dict(data, "ResolverOutputV2")
        _require_no_unknown_props(data, cls._FIELDS, "ResolverOutputV2")
        try:
            result = ResolverResultV2(_require_str(data["resolver_result"], "resolver_result"))
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ResolverResultV2)
            raise StructuralContractError(
                f"resolver_result: invalid value (allowed: {allowed})"
            ) from exc
        try:
            source_presence = SourcePresenceV2(
                _require_str(data["source_presence"], "source_presence")
            )
            verbatim = VerbatimEvidenceAvailabilityV2(
                _require_str(
                    data["verbatim_evidence_availability"],
                    "verbatim_evidence_availability",
                )
            )
            summary = SummaryEvidenceAvailabilityV2(
                _require_str(
                    data["summary_evidence_availability"],
                    "summary_evidence_availability",
                )
            )
        except (KeyError, ValueError) as exc:
            raise StructuralContractError("ResolverOutputV2: invalid availability state") from exc
        return cls(
            _token=_RESOLVER_OUTPUT_TOKEN,
            resolver_result=result,
            source_presence=source_presence,
            verbatim_evidence_availability=verbatim,
            summary_evidence_availability=summary,
            canonical_content_digest=_digest(
                _required(data, "canonical_content_digest"), "canonical_content_digest"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolver_result": self.resolver_result.value,
            "source_presence": self.source_presence.value,
            "verbatim_evidence_availability": self.verbatim_evidence_availability.value,
            "summary_evidence_availability": self.summary_evidence_availability.value,
            "canonical_content_digest": self.canonical_content_digest,
        }


def _result_for_availability(
    availability: ConditionNeutralEvidenceAvailabilityV2,
) -> ResolverResultV2:
    """Derive P2 result without collapsing Issue #263 availability axes."""

    availability.validate_issue_263()
    if availability.source_presence == SourcePresenceV2.ABSENT:
        if (
            availability.verbatim_evidence_availability
            == VerbatimEvidenceAvailabilityV2.AVAILABLE
            or availability.summary_evidence_availability
            == SummaryEvidenceAvailabilityV2.AVAILABLE
        ):
            raise StructuralContractError(
                "resolver availability is contradictory: absent source has available evidence"
            )
        return ResolverResultV2.NO_MATCH
    if availability.source_presence == SourcePresenceV2.PRESENT:
        if (
            availability.verbatim_evidence_availability
            == VerbatimEvidenceAvailabilityV2.AVAILABLE
        ):
            return ResolverResultV2.EXACT_MATCH
        if (
            availability.summary_evidence_availability
            == SummaryEvidenceAvailabilityV2.AVAILABLE
        ):
            return ResolverResultV2.SUMMARY_ONLY
        return ResolverResultV2.EVIDENCE_UNAVAILABLE
    # Unknown source state is not source absence.  The resolver reports an
    # unavailable result while preserving the three input axes in its output.
    return ResolverResultV2.EVIDENCE_UNAVAILABLE


def _run_trusted_resolver(resolver_input: ResolverInputV2) -> ResolverOutputV2:
    """Run the sole closed resolver implementation over derived input."""

    availability = resolver_input.condition_neutral_evidence_availability
    return ResolverOutputV2(
        _token=_RESOLVER_OUTPUT_TOKEN,
        resolver_result=_result_for_availability(availability),
        source_presence=availability.source_presence,
        verbatim_evidence_availability=availability.verbatim_evidence_availability,
        summary_evidence_availability=availability.summary_evidence_availability,
        canonical_content_digest=resolver_input.canonical_content_digest,
    )


@dataclass(frozen=True)
class OpaqueResolverManifestV2:  # pylint: disable=too-many-instance-attributes
    """Content-bound P2 authority for one exact P1/P2 occurrence."""

    header: ArtifactHeaderV1
    p1_authority_artifact_id: str
    p1_authority_digest: str
    evidence_seal_digest: str
    capability_manifest_artifact_id: str
    capability_manifest_digest: str
    construct_freeze_artifact_id: str
    construct_freeze_digest: str
    episode_id: str
    occurrence_reference: OccurrenceReferenceV2
    occurrence_issuance_digest: str
    source_authority_digest: str
    source_capture_digest: str
    issuer_implementation_revision: str
    p1_adapter_implementation_digest: str
    evidence_snapshot_id: str
    raw_record_digest: str
    canonical_content_digest: str
    canonicalization_profile_digest: str
    resolver_implementation_id: str
    resolver_implementation_digest: str
    resolver_input: ResolverInputV2
    resolver_input_digest: str
    resolver_result: ResolverResultV2
    capability_vector: CapabilityVectorV2
    condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2
    resolver_output: ResolverOutputV2
    resolver_output_digest: str

    _FIELDS = {
        "header",
        "p1_authority_artifact_id",
        "p1_authority_digest",
        "evidence_seal_digest",
        "capability_manifest_artifact_id",
        "capability_manifest_digest",
        "construct_freeze_artifact_id",
        "construct_freeze_digest",
        "episode_id",
        "occurrence_reference",
        "occurrence_issuance_digest",
        "source_authority_digest",
        "source_capture_digest",
        "issuer_implementation_revision",
        "p1_adapter_implementation_digest",
        "evidence_snapshot_id",
        "raw_record_digest",
        "canonical_content_digest",
        "canonicalization_profile_digest",
        "resolver_implementation_id",
        "resolver_implementation_digest",
        "resolver_input",
        "resolver_input_digest",
        "resolver_result",
        "capability_vector",
        "condition_neutral_evidence_availability",
        "resolver_output",
        "resolver_output_digest",
    }

    def __init__(
        self,
        *,
        _token: object,
        header: ArtifactHeaderV1,
        p1_authority_artifact_id: str,
        p1_authority_digest: str,
        evidence_seal_digest: str,
        capability_manifest_artifact_id: str,
        capability_manifest_digest: str,
        construct_freeze_artifact_id: str,
        construct_freeze_digest: str,
        episode_id: str,
        occurrence_reference: OccurrenceReferenceV2,
        occurrence_issuance_digest: str,
        source_authority_digest: str,
        source_capture_digest: str,
        issuer_implementation_revision: str,
        p1_adapter_implementation_digest: str,
        evidence_snapshot_id: str,
        raw_record_digest: str,
        canonical_content_digest: str,
        canonicalization_profile_digest: str,
        resolver_implementation_id: str,
        resolver_implementation_digest: str,
        resolver_input: ResolverInputV2,
        resolver_input_digest: str,
        resolver_result: ResolverResultV2,
        capability_vector: CapabilityVectorV2,
        condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2,
        resolver_output: ResolverOutputV2,
        resolver_output_digest: str,
    ) -> None:
        if _token is not _RESOLVER_MANIFEST_TOKEN:
            raise TypeError(
                "OpaqueResolverManifestV2 is issuer-finalized only; "
                "derive it from verified P1/P2 authority"
            )
        values = {
            "header": header,
            "p1_authority_artifact_id": p1_authority_artifact_id,
            "p1_authority_digest": p1_authority_digest,
            "evidence_seal_digest": evidence_seal_digest,
            "capability_manifest_artifact_id": capability_manifest_artifact_id,
            "capability_manifest_digest": capability_manifest_digest,
            "construct_freeze_artifact_id": construct_freeze_artifact_id,
            "construct_freeze_digest": construct_freeze_digest,
            "episode_id": episode_id,
            "occurrence_reference": occurrence_reference,
            "occurrence_issuance_digest": occurrence_issuance_digest,
            "source_authority_digest": source_authority_digest,
            "source_capture_digest": source_capture_digest,
            "issuer_implementation_revision": issuer_implementation_revision,
            "p1_adapter_implementation_digest": p1_adapter_implementation_digest,
            "evidence_snapshot_id": evidence_snapshot_id,
            "raw_record_digest": raw_record_digest,
            "canonical_content_digest": canonical_content_digest,
            "canonicalization_profile_digest": canonicalization_profile_digest,
            "resolver_implementation_id": resolver_implementation_id,
            "resolver_implementation_digest": resolver_implementation_digest,
            "resolver_input": resolver_input,
            "resolver_input_digest": resolver_input_digest,
            "resolver_result": resolver_result,
            "capability_vector": capability_vector,
            "condition_neutral_evidence_availability": condition_neutral_evidence_availability,
            "resolver_output": resolver_output,
            "resolver_output_digest": resolver_output_digest,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpaqueResolverManifestV2":
        data = _require_dict(data, "OpaqueResolverManifestV2")
        _require_no_unknown_props(data, cls._FIELDS, "OpaqueResolverManifestV2")
        try:
            result = ResolverResultV2(_require_str(data["resolver_result"], "resolver_result"))
        except (KeyError, ValueError) as exc:
            raise StructuralContractError("OpaqueResolverManifestV2: invalid resolver_result") from exc
        return cls(
            _token=_RESOLVER_MANIFEST_TOKEN,
            header=ArtifactHeaderV1.from_dict(
                _require_dict(_required(data, "header"), "header")
            ),
            p1_authority_artifact_id=_require_str(
                _required(data, "p1_authority_artifact_id"),
                "p1_authority_artifact_id",
            ),
            p1_authority_digest=_digest(
                _required(data, "p1_authority_digest"), "p1_authority_digest"
            ),
            evidence_seal_digest=_digest(
                _required(data, "evidence_seal_digest"), "evidence_seal_digest"
            ),
            capability_manifest_artifact_id=_require_str(
                _required(data, "capability_manifest_artifact_id"),
                "capability_manifest_artifact_id",
            ),
            capability_manifest_digest=_digest(
                _required(data, "capability_manifest_digest"),
                "capability_manifest_digest",
            ),
            construct_freeze_artifact_id=_require_str(
                _required(data, "construct_freeze_artifact_id"),
                "construct_freeze_artifact_id",
            ),
            construct_freeze_digest=_digest(
                _required(data, "construct_freeze_digest"), "construct_freeze_digest"
            ),
            episode_id=_require_str(_required(data, "episode_id"), "episode_id"),
            occurrence_reference=OccurrenceReferenceV2.from_dict(
                _require_dict(_required(data, "occurrence_reference"), "occurrence_reference")
            ),
            occurrence_issuance_digest=_digest(
                _required(data, "occurrence_issuance_digest"),
                "occurrence_issuance_digest",
            ),
            source_authority_digest=_digest(
                _required(data, "source_authority_digest"), "source_authority_digest"
            ),
            source_capture_digest=_digest(
                _required(data, "source_capture_digest"), "source_capture_digest"
            ),
            issuer_implementation_revision=_require_str(
                _required(data, "issuer_implementation_revision"),
                "issuer_implementation_revision",
            ),
            p1_adapter_implementation_digest=_digest(
                _required(data, "p1_adapter_implementation_digest"),
                "p1_adapter_implementation_digest",
            ),
            evidence_snapshot_id=_require_str(
                _required(data, "evidence_snapshot_id"), "evidence_snapshot_id"
            ),
            raw_record_digest=_digest(
                _required(data, "raw_record_digest"), "raw_record_digest"
            ),
            canonical_content_digest=_digest(
                _required(data, "canonical_content_digest"), "canonical_content_digest"
            ),
            canonicalization_profile_digest=_digest(
                _required(data, "canonicalization_profile_digest"),
                "canonicalization_profile_digest",
            ),
            resolver_implementation_id=_require_str(
                _required(data, "resolver_implementation_id"),
                "resolver_implementation_id",
            ),
            resolver_implementation_digest=_digest(
                _required(data, "resolver_implementation_digest"),
                "resolver_implementation_digest",
            ),
            resolver_input=ResolverInputV2.from_dict(
                _require_dict(_required(data, "resolver_input"), "resolver_input")
            ),
            resolver_input_digest=_digest(
                _required(data, "resolver_input_digest"), "resolver_input_digest"
            ),
            resolver_result=result,
            capability_vector=CapabilityVectorV2.from_dict(
                _require_dict(_required(data, "capability_vector"), "capability_vector")
            ),
            condition_neutral_evidence_availability=ConditionNeutralEvidenceAvailabilityV2.from_dict(
                _require_dict(
                    _required(data, "condition_neutral_evidence_availability"),
                    "condition_neutral_evidence_availability",
                )
            ),
            resolver_output=ResolverOutputV2.from_dict(
                _require_dict(_required(data, "resolver_output"), "resolver_output")
            ),
            resolver_output_digest=_digest(
                _required(data, "resolver_output_digest"), "resolver_output_digest"
            ),
        )

    @classmethod
    def from_canonical_bytes(cls, canonical_bytes: bytes) -> "OpaqueResolverManifestV2":
        if not isinstance(canonical_bytes, bytes):
            raise TypeError("OpaqueResolverManifestV2 canonical bytes must be bytes")
        try:
            data = json.loads(canonical_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StructuralContractError(
                "OpaqueResolverManifestV2: invalid canonical bytes"
            ) from exc
        data = _require_dict(data, "OpaqueResolverManifestV2")
        if canonical_artifact_bytes(data) != canonical_bytes:
            raise StructuralContractError(
                "OpaqueResolverManifestV2: canonical bytes mismatch"
            )
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "p1_authority_artifact_id": self.p1_authority_artifact_id,
            "p1_authority_digest": self.p1_authority_digest,
            "evidence_seal_digest": self.evidence_seal_digest,
            "capability_manifest_artifact_id": self.capability_manifest_artifact_id,
            "capability_manifest_digest": self.capability_manifest_digest,
            "construct_freeze_artifact_id": self.construct_freeze_artifact_id,
            "construct_freeze_digest": self.construct_freeze_digest,
            "episode_id": self.episode_id,
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "occurrence_issuance_digest": self.occurrence_issuance_digest,
            "source_authority_digest": self.source_authority_digest,
            "source_capture_digest": self.source_capture_digest,
            "issuer_implementation_revision": self.issuer_implementation_revision,
            "p1_adapter_implementation_digest": self.p1_adapter_implementation_digest,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "raw_record_digest": self.raw_record_digest,
            "canonical_content_digest": self.canonical_content_digest,
            "canonicalization_profile_digest": self.canonicalization_profile_digest,
            "resolver_implementation_id": self.resolver_implementation_id,
            "resolver_implementation_digest": self.resolver_implementation_digest,
            "resolver_input": self.resolver_input.to_dict(),
            "resolver_input_digest": self.resolver_input_digest,
            "resolver_result": self.resolver_result.value,
            "capability_vector": self.capability_vector.to_dict(),
            "condition_neutral_evidence_availability": (
                self.condition_neutral_evidence_availability.to_dict()
            ),
            "resolver_output": self.resolver_output.to_dict(),
            "resolver_output_digest": self.resolver_output_digest,
        }


@dataclass(frozen=True)
class SealedOpaqueResolverManifestV2:
    """Portable resolver bytes whose authority is re-established on verify."""

    manifest: OpaqueResolverManifestV2
    canonical_bytes: bytes
    content_digest: str

    @classmethod
    def from_canonical_bytes(cls, canonical_bytes: bytes) -> "SealedOpaqueResolverManifestV2":
        manifest = OpaqueResolverManifestV2.from_canonical_bytes(canonical_bytes)
        return cls(
            manifest=manifest,
            canonical_bytes=canonical_bytes,
            content_digest=_manifest_content_digest(manifest.to_dict()),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.manifest.to_dict()


def _require_sealed_capability(authority: Any) -> SealedCapabilityManifestV2:
    if type(authority) is not SealedCapabilityManifestV2:  # pylint: disable=unidiomatic-typecheck
        raise TypeError(
            "resolver authority requires an issued SealedCapabilityManifestV2; "
            "raw capability claims are not accepted"
        )
    return authority


def _verified_upstream(
    capability: SealedCapabilityManifestV2,
    *,
    p1_authority: SealedP1AuthorityV2 | None,
    p0_repository: "ConstructFreezeAuthorityRepository | None",
    issuance_repository: Any,
    lineage_repository: "LineageAttestationRepository | None",
    authority_source: "IndependentAuthoritySourceV2 | None",
) -> tuple[SealedP1AuthorityV2, SealedCapabilityManifestV2]:
    if p1_authority is None:
        raise StructuralContractError("resolver authority requires source-backed P1 authority")
    if issuance_repository is None:
        raise StructuralContractError("resolver authority requires issuance repository")
    capability = _require_sealed_capability(capability)
    verified_capability = verify_capability_manifest(
        capability,
        p1_authority=p1_authority,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )
    return p1_authority, verified_capability


def _compare_upstream_bindings(
    manifest: OpaqueResolverManifestV2,
    *,
    p1: SealedP1AuthorityV2,
    capability: SealedCapabilityManifestV2,
) -> None:
    p1_manifest = p1.manifest
    cap = capability.manifest
    p1_digest = p1_manifest.header.content_digest
    cap_digest = cap.header.content_digest
    if not p1_digest or not cap_digest:
        raise StructuralContractError("resolver authority requires upstream content digests")
    expected = {
        "p1_authority_artifact_id": p1_manifest.header.artifact_id,
        "p1_authority_digest": p1_digest,
        "evidence_seal_digest": p1_digest,
        "capability_manifest_artifact_id": cap.header.artifact_id,
        "capability_manifest_digest": cap_digest,
        "construct_freeze_artifact_id": cap.construct_freeze_artifact_id,
        "construct_freeze_digest": cap.construct_freeze_digest,
        "episode_id": cap.episode_id,
        "occurrence_issuance_digest": cap.occurrence_issuance_digest,
        "source_authority_digest": cap.source_authority_digest,
        "source_capture_digest": cap.source_capture_digest,
        "issuer_implementation_revision": cap.issuer_implementation_revision,
        "p1_adapter_implementation_digest": cap.p1_adapter_implementation_digest,
        "evidence_snapshot_id": cap.evidence_snapshot_id,
        "raw_record_digest": cap.raw_record_digest,
        "canonical_content_digest": cap.canonical_content_digest,
        "canonicalization_profile_digest": cap.canonicalization_profile_digest,
    }
    for field_name, expected_value in expected.items():
        if getattr(manifest, field_name) != expected_value:
            raise StructuralContractError(
                f"resolver manifest: {field_name} is not bound to verified upstream authority"
            )
    if manifest.occurrence_reference.to_dict() != cap.occurrence_reference.to_dict():
        raise StructuralContractError("resolver manifest: occurrence reference mismatch")
    if manifest.capability_vector.to_dict() != cap.capability_vector.to_dict():
        raise StructuralContractError("resolver manifest: capability vector is not derived")
    if (
        manifest.condition_neutral_evidence_availability
        != cap.condition_neutral_evidence_availability
    ):
        raise StructuralContractError(
            "resolver manifest: availability is not derived from capability authority"
        )


def _verify_implementation_identity(manifest: OpaqueResolverManifestV2) -> None:
    if manifest.resolver_implementation_id not in _TRUSTED_RESOLVER_IMPLEMENTATION_IDS:
        raise StructuralContractError("resolver manifest: unknown resolver implementation")
    expected = compute_resolver_implementation_digest()
    if manifest.resolver_implementation_digest != expected:
        raise StructuralContractError(
            "resolver manifest: resolver implementation identity is not trusted"
        )


def _verify_derived_input_and_output(
    manifest: OpaqueResolverManifestV2,
    *,
    p1: SealedP1AuthorityV2,
    capability: SealedCapabilityManifestV2,
) -> None:
    expected_input = ResolverInputV2.from_verified_authority(p1, capability)
    if manifest.resolver_input.to_dict() != expected_input.to_dict():
        raise StructuralContractError("resolver manifest: resolver input is not derived")
    if manifest.resolver_input_digest != _canonical_digest(expected_input.to_dict()):
        raise StructuralContractError("resolver manifest: resolver input digest mismatch")
    expected_output = _run_trusted_resolver(expected_input)
    if manifest.resolver_output.to_dict() != expected_output.to_dict():
        raise StructuralContractError("resolver manifest: resolver output is not trusted")
    if manifest.resolver_output_digest != _canonical_digest(expected_output.to_dict()):
        raise StructuralContractError("resolver manifest: resolver output digest mismatch")
    if manifest.resolver_result != expected_output.resolver_result:
        raise StructuralContractError("resolver manifest: resolver result mismatch")


def _coerce_manifest_input(
    authority: SealedOpaqueResolverManifestV2 | bytes | dict[str, Any],
) -> SealedOpaqueResolverManifestV2:
    if isinstance(authority, bytes):
        return SealedOpaqueResolverManifestV2.from_canonical_bytes(authority)
    if type(authority) is SealedOpaqueResolverManifestV2:  # pylint: disable=unidiomatic-typecheck
        return authority
    if isinstance(authority, dict):
        manifest = OpaqueResolverManifestV2.from_dict(authority)
        return SealedOpaqueResolverManifestV2(
            manifest=manifest,
            canonical_bytes=canonical_artifact_bytes(manifest.to_dict()),
            content_digest=_manifest_content_digest(manifest.to_dict()),
        )
    raise TypeError(
        "resolver verification requires canonical bytes, a sealed resolver, or a mapping"
    )


def verify_opaque_resolver_manifest(
    authority: SealedOpaqueResolverManifestV2 | bytes | dict[str, Any],
    *,
    p1_authority: SealedP1AuthorityV2 | None = None,
    capability_authority: SealedCapabilityManifestV2 | None = None,
    p0_repository: "ConstructFreezeAuthorityRepository | None" = None,
    issuance_repository: Any = None,
    lineage_repository: "LineageAttestationRepository | None" = None,
    authority_source: "IndependentAuthoritySourceV2 | None" = None,
) -> SealedOpaqueResolverManifestV2:
    """Verify resolver bytes and re-establish complete P1/P2 authority."""

    if capability_authority is None:
        raise StructuralContractError(
            "resolver verification requires source-backed capability authority"
        )
    resolver = _coerce_manifest_input(authority)
    p1, capability = _verified_upstream(
        capability_authority,
        p1_authority=p1_authority,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )
    manifest = resolver.manifest
    header = manifest.header
    if header.schema_version != RESOLVER_MANIFEST_SCHEMA:
        raise StructuralContractError("resolver manifest: wrong schema_version")
    if not header.sealed or not header.seal_time:
        raise StructuralContractError("resolver manifest: unsealed or missing seal_time")
    if header.responsible_role != "opaque_resolver":
        raise StructuralContractError("resolver manifest: invalid responsible_role")
    if not header.content_digest:
        raise StructuralContractError("resolver manifest: missing content_digest")
    if header.parent_artifact_id != manifest.capability_manifest_artifact_id:
        raise StructuralContractError("resolver manifest: capability parent artifact mismatch")
    if header.parent_digest != manifest.capability_manifest_digest:
        raise StructuralContractError("resolver manifest: capability parent digest mismatch")
    if header.created_at != capability.manifest.header.created_at:
        raise StructuralContractError("resolver manifest: created_at is not inherited")
    if header.seal_time != p1.manifest.header.seal_time:
        raise StructuralContractError("resolver manifest: seal_time is not inherited")
    _compare_upstream_bindings(manifest, p1=p1, capability=capability)
    _verify_implementation_identity(manifest)
    _verify_derived_input_and_output(manifest, p1=p1, capability=capability)
    recomputed = _manifest_content_digest(manifest.to_dict())
    if recomputed != header.content_digest:
        raise StructuralContractError("resolver manifest: content digest mismatch")
    if recomputed != resolver.content_digest:
        raise StructuralContractError("resolver manifest: wrapper content digest mismatch")
    if header.artifact_id != _derive_artifact_id(recomputed):
        raise StructuralContractError("resolver manifest: artifact ID mismatch")
    if canonical_artifact_bytes(manifest.to_dict()) != resolver.canonical_bytes:
        raise StructuralContractError("resolver manifest: canonical bytes mismatch")
    return resolver


def resolve_opaque_occurrence(
    capability_authority: SealedCapabilityManifestV2,
    *,
    p1_authority: SealedP1AuthorityV2 | None = None,
    p0_repository: "ConstructFreezeAuthorityRepository | None" = None,
    issuance_repository: Any = None,
    lineage_repository: "LineageAttestationRepository | None" = None,
    authority_source: "IndependentAuthoritySourceV2 | None" = None,
) -> SealedOpaqueResolverManifestV2:
    """Resolve one verified capability into an opaque P2 authority artifact."""

    p1, capability = _verified_upstream(
        capability_authority,
        p1_authority=p1_authority,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )
    # Seal verification must use the same repositories and source as issuance;
    # this keeps the public issuance path from introducing a weaker verifier.
    resolver_input = ResolverInputV2.from_verified_authority(p1, capability)
    resolver_output = _run_trusted_resolver(resolver_input)
    sealed = _seal_resolver_manifest_with_context(
        p1=p1,
        capability=capability,
        resolver_input=resolver_input,
        resolver_output=resolver_output,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )
    return sealed


def _seal_resolver_manifest_with_context(
    *,
    p1: SealedP1AuthorityV2,
    capability: SealedCapabilityManifestV2,
    resolver_input: ResolverInputV2,
    resolver_output: ResolverOutputV2,
    p0_repository: "ConstructFreezeAuthorityRepository | None",
    issuance_repository: Any,
    lineage_repository: "LineageAttestationRepository | None",
    authority_source: "IndependentAuthoritySourceV2 | None",
) -> SealedOpaqueResolverManifestV2:
    p1_manifest = p1.manifest
    cap = capability.manifest
    p1_digest = p1_manifest.header.content_digest
    cap_digest = cap.header.content_digest
    if not p1_digest or not cap_digest or cap.raw_record_digest is None:
        raise StructuralContractError("resolver sealing requires complete upstream identity")
    implementation = trusted_resolver_implementation_identity()
    body = OpaqueResolverManifestV2(
        _token=_RESOLVER_MANIFEST_TOKEN,
        header=ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=RESOLVER_MANIFEST_SCHEMA,
            parent_artifact_id=cap.header.artifact_id,
            parent_digest=cap_digest,
            created_at=cap.header.created_at,
            seal_time=p1_manifest.header.seal_time,
            responsible_role="opaque_resolver",
            content_digest=None,
            sealed=False,
        ),
        p1_authority_artifact_id=p1_manifest.header.artifact_id,
        p1_authority_digest=p1_digest,
        evidence_seal_digest=p1_digest,
        capability_manifest_artifact_id=cap.header.artifact_id,
        capability_manifest_digest=cap_digest,
        construct_freeze_artifact_id=cap.construct_freeze_artifact_id,
        construct_freeze_digest=cap.construct_freeze_digest,
        episode_id=cap.episode_id,
        occurrence_reference=cap.occurrence_reference,
        occurrence_issuance_digest=cap.occurrence_issuance_digest,
        source_authority_digest=cap.source_authority_digest,
        source_capture_digest=cap.source_capture_digest,
        issuer_implementation_revision=cap.issuer_implementation_revision,
        p1_adapter_implementation_digest=cap.p1_adapter_implementation_digest,
        evidence_snapshot_id=cap.evidence_snapshot_id,
        raw_record_digest=cap.raw_record_digest,
        canonical_content_digest=cap.canonical_content_digest,
        canonicalization_profile_digest=cap.canonicalization_profile_digest,
        resolver_implementation_id=implementation["resolver_implementation_id"],
        resolver_implementation_digest=implementation["resolver_implementation_digest"],
        resolver_input=resolver_input,
        resolver_input_digest=_canonical_digest(resolver_input.to_dict()),
        resolver_result=resolver_output.resolver_result,
        capability_vector=cap.capability_vector,
        condition_neutral_evidence_availability=cap.condition_neutral_evidence_availability,
        resolver_output=resolver_output,
        resolver_output_digest=_canonical_digest(resolver_output.to_dict()),
    )
    content_digest = _manifest_content_digest(body.to_dict())
    final = OpaqueResolverManifestV2(
        _token=_RESOLVER_MANIFEST_TOKEN,
        header=ArtifactHeaderV1(
            artifact_id=_derive_artifact_id(content_digest),
            schema_version=RESOLVER_MANIFEST_SCHEMA,
            parent_artifact_id=cap.header.artifact_id,
            parent_digest=cap_digest,
            created_at=cap.header.created_at,
            seal_time=p1_manifest.header.seal_time,
            responsible_role="opaque_resolver",
            content_digest=content_digest,
            sealed=True,
        ),
        p1_authority_artifact_id=body.p1_authority_artifact_id,
        p1_authority_digest=body.p1_authority_digest,
        evidence_seal_digest=body.evidence_seal_digest,
        capability_manifest_artifact_id=body.capability_manifest_artifact_id,
        capability_manifest_digest=body.capability_manifest_digest,
        construct_freeze_artifact_id=body.construct_freeze_artifact_id,
        construct_freeze_digest=body.construct_freeze_digest,
        episode_id=body.episode_id,
        occurrence_reference=body.occurrence_reference,
        occurrence_issuance_digest=body.occurrence_issuance_digest,
        source_authority_digest=body.source_authority_digest,
        source_capture_digest=body.source_capture_digest,
        issuer_implementation_revision=body.issuer_implementation_revision,
        p1_adapter_implementation_digest=body.p1_adapter_implementation_digest,
        evidence_snapshot_id=body.evidence_snapshot_id,
        raw_record_digest=body.raw_record_digest,
        canonical_content_digest=body.canonical_content_digest,
        canonicalization_profile_digest=body.canonicalization_profile_digest,
        resolver_implementation_id=body.resolver_implementation_id,
        resolver_implementation_digest=body.resolver_implementation_digest,
        resolver_input=body.resolver_input,
        resolver_input_digest=body.resolver_input_digest,
        resolver_result=body.resolver_result,
        capability_vector=body.capability_vector,
        condition_neutral_evidence_availability=body.condition_neutral_evidence_availability,
        resolver_output=body.resolver_output,
        resolver_output_digest=body.resolver_output_digest,
    )
    sealed = SealedOpaqueResolverManifestV2(
        manifest=final,
        canonical_bytes=canonical_artifact_bytes(final.to_dict()),
        content_digest=content_digest,
    )
    return verify_opaque_resolver_manifest(
        sealed,
        p1_authority=p1,
        capability_authority=capability,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )


def parse_opaque_resolver_manifest_v2(
    canonical_bytes: bytes,
    *,
    p1_authority: SealedP1AuthorityV2 | None = None,
    capability_authority: SealedCapabilityManifestV2 | None = None,
    p0_repository: "ConstructFreezeAuthorityRepository | None" = None,
    issuance_repository: Any = None,
    lineage_repository: "LineageAttestationRepository | None" = None,
    authority_source: "IndependentAuthoritySourceV2 | None" = None,
) -> SealedOpaqueResolverManifestV2:
    """Public reload path; bytes never grant authority without P1/P2 checks."""

    if not isinstance(canonical_bytes, bytes):
        raise TypeError("parse_opaque_resolver_manifest_v2 requires canonical bytes")
    return verify_opaque_resolver_manifest(
        canonical_bytes,
        p1_authority=p1_authority,
        capability_authority=capability_authority,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )


# Descriptive aliases for callers that name the stage rather than the artifact.
OpaqueResolverResultV2 = ResolverResultV2
SealedResolverManifestV2 = SealedOpaqueResolverManifestV2
derive_opaque_resolver_manifest = resolve_opaque_occurrence
parse_resolver_manifest_v2 = parse_opaque_resolver_manifest_v2
resolve_opaque_resolver = resolve_opaque_occurrence
verify_resolver_manifest = verify_opaque_resolver_manifest
