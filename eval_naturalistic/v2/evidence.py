"""P1 evidence commitments and condition-neutral availability (Issue #263)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from eval_naturalistic.base import (
    StructuralContractError,
    _enum_from_value,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.v2.identity import digest_hex


class SourcePresenceV2(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class VerbatimEvidenceAvailabilityV2(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class SummaryEvidenceAvailabilityV2(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class PostSealSourceStateV2(str, Enum):
    UNCHANGED = "UNCHANGED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


@dataclass(frozen=True)
class RawRecordCommitmentV2:
    """Raw-record digest commitment — verification only, not identity."""

    raw_record_digest: str

    _FIELDS = {"raw_record_digest"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RawRecordCommitmentV2":
        data = _require_dict(data, "RawRecordCommitmentV2")
        _require_no_unknown_props(data, cls._FIELDS, "RawRecordCommitmentV2")
        return cls(raw_record_digest=digest_hex(data["raw_record_digest"], "raw_record_digest"))

    def to_dict(self) -> dict[str, str]:
        return {"raw_record_digest": self.raw_record_digest}


@dataclass(frozen=True)
class CanonicalContentCommitmentV2:
    canonical_content_digest: str

    _FIELDS = {"canonical_content_digest"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalContentCommitmentV2":
        data = _require_dict(data, "CanonicalContentCommitmentV2")
        _require_no_unknown_props(data, cls._FIELDS, "CanonicalContentCommitmentV2")
        return cls(
            canonical_content_digest=digest_hex(
                data["canonical_content_digest"], "canonical_content_digest"
            )
        )

    def to_dict(self) -> dict[str, str]:
        return {"canonical_content_digest": self.canonical_content_digest}


@dataclass(frozen=True)
class CanonicalizationProfileIdentityV2:
    canonicalization_profile_digest: str
    profile_id: str | None = None

    _FIELDS = {"canonicalization_profile_digest", "profile_id"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalizationProfileIdentityV2":
        data = _require_dict(data, "CanonicalizationProfileIdentityV2")
        _require_no_unknown_props(data, cls._FIELDS, "CanonicalizationProfileIdentityV2")
        profile_id = data.get("profile_id")
        if profile_id is not None:
            profile_id = _require_str(profile_id, "profile_id")
        return cls(
            canonicalization_profile_digest=digest_hex(
                data["canonicalization_profile_digest"], "canonicalization_profile_digest"
            ),
            profile_id=profile_id,
        )

    def to_dict(self) -> dict[str, str | None]:
        out: dict[str, str | None] = {
            "canonicalization_profile_digest": self.canonicalization_profile_digest
        }
        if self.profile_id is not None:
            out["profile_id"] = self.profile_id
        return out


@dataclass(frozen=True)
class AdapterImplementationIdentityV2:
    adapter_implementation_digest: str
    adapter_id: str | None = None

    _FIELDS = {"adapter_implementation_digest", "adapter_id"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdapterImplementationIdentityV2":
        data = _require_dict(data, "AdapterImplementationIdentityV2")
        _require_no_unknown_props(data, cls._FIELDS, "AdapterImplementationIdentityV2")
        adapter_id = data.get("adapter_id")
        if adapter_id is not None:
            adapter_id = _require_str(adapter_id, "adapter_id")
        return cls(
            adapter_implementation_digest=digest_hex(
                data["adapter_implementation_digest"], "adapter_implementation_digest"
            ),
            adapter_id=adapter_id,
        )

    def to_dict(self) -> dict[str, str | None]:
        out: dict[str, str | None] = {
            "adapter_implementation_digest": self.adapter_implementation_digest
        }
        if self.adapter_id is not None:
            out["adapter_id"] = self.adapter_id
        return out


@dataclass(frozen=True)
class EvidenceCompleteEnvelopeCommitmentV2:
    evidence_complete_envelope_digest: str
    attachment_reference_inventory_digest: str | None = None
    source_and_snapshot_identity_digest: str | None = None

    _FIELDS = {
        "evidence_complete_envelope_digest",
        "attachment_reference_inventory_digest",
        "source_and_snapshot_identity_digest",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceCompleteEnvelopeCommitmentV2":
        data = _require_dict(data, "EvidenceCompleteEnvelopeCommitmentV2")
        _require_no_unknown_props(data, cls._FIELDS, "EvidenceCompleteEnvelopeCommitmentV2")
        attachment = data.get("attachment_reference_inventory_digest")
        snapshot = data.get("source_and_snapshot_identity_digest")
        return cls(
            evidence_complete_envelope_digest=digest_hex(
                data["evidence_complete_envelope_digest"],
                "evidence_complete_envelope_digest",
            ),
            attachment_reference_inventory_digest=(
                digest_hex(attachment, "attachment_reference_inventory_digest")
                if attachment is not None
                else None
            ),
            source_and_snapshot_identity_digest=(
                digest_hex(snapshot, "source_and_snapshot_identity_digest")
                if snapshot is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, str]:
        out = {
            "evidence_complete_envelope_digest": self.evidence_complete_envelope_digest
        }
        if self.attachment_reference_inventory_digest is not None:
            out["attachment_reference_inventory_digest"] = (
                self.attachment_reference_inventory_digest
            )
        if self.source_and_snapshot_identity_digest is not None:
            out["source_and_snapshot_identity_digest"] = (
                self.source_and_snapshot_identity_digest
            )
        return out


@dataclass(frozen=True)
class ConditionNeutralEvidenceAvailabilityV2:
    """Orthogonal Issue #263 availability axes — not resolver state."""

    source_presence: SourcePresenceV2
    verbatim_evidence_availability: VerbatimEvidenceAvailabilityV2
    summary_evidence_availability: SummaryEvidenceAvailabilityV2

    _FIELDS = {
        "source_presence",
        "verbatim_evidence_availability",
        "summary_evidence_availability",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConditionNeutralEvidenceAvailabilityV2":
        data = _require_dict(data, "ConditionNeutralEvidenceAvailabilityV2")
        _require_no_unknown_props(data, cls._FIELDS, "ConditionNeutralEvidenceAvailabilityV2")
        return cls(
            source_presence=_enum_from_value(
                SourcePresenceV2, data["source_presence"], "source_presence"
            ),
            verbatim_evidence_availability=_enum_from_value(
                VerbatimEvidenceAvailabilityV2,
                data["verbatim_evidence_availability"],
                "verbatim_evidence_availability",
            ),
            summary_evidence_availability=_enum_from_value(
                SummaryEvidenceAvailabilityV2,
                data["summary_evidence_availability"],
                "summary_evidence_availability",
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "source_presence": self.source_presence.value,
            "verbatim_evidence_availability": self.verbatim_evidence_availability.value,
            "summary_evidence_availability": self.summary_evidence_availability.value,
        }

    def implies_source_absent(self) -> bool:
        return self.source_presence == SourcePresenceV2.ABSENT

    def violates_issue_263(self) -> bool:
        """Source present with unavailable verbatim must never collapse to absent."""

        if self.source_presence != SourcePresenceV2.PRESENT:
            return False
        if self.verbatim_evidence_availability != VerbatimEvidenceAvailabilityV2.UNAVAILABLE:
            return False
        return False

    def validate_issue_263(self) -> None:
        if (
            self.source_presence == SourcePresenceV2.PRESENT
            and self.verbatim_evidence_availability
            == VerbatimEvidenceAvailabilityV2.UNAVAILABLE
            and self.implies_source_absent()
        ):
            raise StructuralContractError(
                "Issue #263: source present with verbatim unavailable must not be reported absent"
            )
        if (
            self.source_presence == SourcePresenceV2.PRESENT
            and self.summary_evidence_availability
            in {
                SummaryEvidenceAvailabilityV2.AVAILABLE,
                SummaryEvidenceAvailabilityV2.UNAVAILABLE,
            }
            and self.source_presence == SourcePresenceV2.ABSENT
        ):
            raise StructuralContractError(
                "Issue #263: summary availability must not emit source absent when source is present"
            )


def normalized_reported_presence(
    availability: ConditionNeutralEvidenceAvailabilityV2,
) -> SourcePresenceV2:
    """Return the only P1-legal reported presence for an availability tuple."""

    availability.validate_issue_263()
    if availability.source_presence == SourcePresenceV2.PRESENT:
        return SourcePresenceV2.PRESENT
    if availability.source_presence == SourcePresenceV2.ABSENT:
        return SourcePresenceV2.ABSENT
    return SourcePresenceV2.UNKNOWN
