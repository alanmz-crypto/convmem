"""P1 durable artifact contracts for Naturalistic V2 evidence sealing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eval_naturalistic.base import (
    ArtifactHeaderV1,
    StructuralContractError,
    _require_dict,
    _require_list,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.v2.evidence import (
    ConditionNeutralEvidenceAvailabilityV2,
    PostSealSourceStateV2,
)
from eval_naturalistic.v2.identity import (
    EvidenceSnapshotIdV2,
    LineageEdgeV2,
    OccurrenceReferenceV2,
    PhysicalInstanceIdV2,
    RevisionOrAsofIdV2,
    digest_hex,
)

SCHEMA_NAMESPACE_V2 = "convmem/naturalistic/v2"
ARTIFACT_ID_PREFIX_V2 = "nps2_"

P1_FORBIDDEN_FIELDS = frozenset(
    {
        "resolver_status",
        "resolver_failure_reason",
        "resolver_result",
        "capability_vector",
        "resolver_output_digest",
        "target_census",
        "target_ground_truth",
        "registry_membership",
        "probe_keys",
        "agent_b_outputs",
        "scores",
        "effects",
    }
)


def _header_from(data: dict[str, Any]) -> ArtifactHeaderV1:
    return ArtifactHeaderV1.from_dict(_require_dict(data.get("header"), "header"))


def _header_to(header: ArtifactHeaderV1) -> dict[str, Any]:
    return header.to_dict()


@dataclass
class EvidenceSealManifestV2:
    """P1 evidence seal authority — identity and envelope commitments only."""

    header: ArtifactHeaderV1
    construct_freeze_digest: str
    episode_id: str
    occurrence_reference: OccurrenceReferenceV2
    physical_instance_id: str
    revision_or_asof_id: str
    evidence_snapshot_id: str
    evidence_complete_envelope_digest: str
    canonical_content_digest: str
    canonicalization_profile_digest: str
    adapter_implementation_digest: str
    condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2
    logical_lineage_id: str | None = None
    lineage_edges: list[LineageEdgeV2] = field(default_factory=list)
    raw_record_digest: str | None = None
    attachment_reference_inventory_digest: str | None = None
    source_and_snapshot_identity_digest: str | None = None

    SCHEMA = f"{SCHEMA_NAMESPACE_V2}/evidence-seal-manifest-v2"
    _FIELDS = {
        "header",
        "construct_freeze_digest",
        "episode_id",
        "occurrence_reference",
        "physical_instance_id",
        "revision_or_asof_id",
        "evidence_snapshot_id",
        "evidence_complete_envelope_digest",
        "canonical_content_digest",
        "canonicalization_profile_digest",
        "adapter_implementation_digest",
        "condition_neutral_evidence_availability",
        "logical_lineage_id",
        "lineage_edges",
        "raw_record_digest",
        "attachment_reference_inventory_digest",
        "source_and_snapshot_identity_digest",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceSealManifestV2":
        data = _require_dict(data, "EvidenceSealManifestV2")
        _require_no_unknown_props(data, cls._FIELDS, "EvidenceSealManifestV2")
        for forbidden in P1_FORBIDDEN_FIELDS:
            if forbidden in data:
                raise StructuralContractError(
                    f"EvidenceSealManifestV2: forbidden P2/resolver field '{forbidden}'"
                )
        availability = ConditionNeutralEvidenceAvailabilityV2.from_dict(
            _require_dict(
                data["condition_neutral_evidence_availability"],
                "condition_neutral_evidence_availability",
            )
        )
        raw = data.get("raw_record_digest")
        attachment = data.get("attachment_reference_inventory_digest")
        snapshot_identity = data.get("source_and_snapshot_identity_digest")
        return cls(
            header=_header_from(data),
            construct_freeze_digest=digest_hex(
                data["construct_freeze_digest"], "construct_freeze_digest"
            ),
            episode_id=_require_str(data["episode_id"], "episode_id"),
            occurrence_reference=OccurrenceReferenceV2.from_dict(
                _require_dict(data["occurrence_reference"], "occurrence_reference")
            ),
            physical_instance_id=_require_str(
                data["physical_instance_id"], "physical_instance_id"
            ),
            revision_or_asof_id=_require_str(
                data["revision_or_asof_id"], "revision_or_asof_id"
            ),
            evidence_snapshot_id=_require_str(
                data["evidence_snapshot_id"], "evidence_snapshot_id"
            ),
            evidence_complete_envelope_digest=digest_hex(
                data["evidence_complete_envelope_digest"],
                "evidence_complete_envelope_digest",
            ),
            canonical_content_digest=digest_hex(
                data["canonical_content_digest"], "canonical_content_digest"
            ),
            canonicalization_profile_digest=digest_hex(
                data["canonicalization_profile_digest"],
                "canonicalization_profile_digest",
            ),
            adapter_implementation_digest=digest_hex(
                data["adapter_implementation_digest"],
                "adapter_implementation_digest",
            ),
            condition_neutral_evidence_availability=availability,
            logical_lineage_id=data.get("logical_lineage_id"),
            lineage_edges=[
                LineageEdgeV2.from_dict(item)
                for item in _require_list(data.get("lineage_edges", []), "lineage_edges")
            ],
            raw_record_digest=digest_hex(raw, "raw_record_digest") if raw is not None else None,
            attachment_reference_inventory_digest=(
                digest_hex(attachment, "attachment_reference_inventory_digest")
                if attachment is not None
                else None
            ),
            source_and_snapshot_identity_digest=(
                digest_hex(snapshot_identity, "source_and_snapshot_identity_digest")
                if snapshot_identity is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "construct_freeze_digest": self.construct_freeze_digest,
            "episode_id": self.episode_id,
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "physical_instance_id": self.physical_instance_id,
            "revision_or_asof_id": self.revision_or_asof_id,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "evidence_complete_envelope_digest": self.evidence_complete_envelope_digest,
            "canonical_content_digest": self.canonical_content_digest,
            "canonicalization_profile_digest": self.canonicalization_profile_digest,
            "adapter_implementation_digest": self.adapter_implementation_digest,
            "condition_neutral_evidence_availability": (
                self.condition_neutral_evidence_availability.to_dict()
            ),
            "lineage_edges": [edge.to_dict() for edge in self.lineage_edges],
        }
        if self.logical_lineage_id is not None:
            out["logical_lineage_id"] = self.logical_lineage_id
        if self.raw_record_digest is not None:
            out["raw_record_digest"] = self.raw_record_digest
        if self.attachment_reference_inventory_digest is not None:
            out["attachment_reference_inventory_digest"] = (
                self.attachment_reference_inventory_digest
            )
        if self.source_and_snapshot_identity_digest is not None:
            out["source_and_snapshot_identity_digest"] = (
                self.source_and_snapshot_identity_digest
            )
        return out

    def bound_physical_instance(self) -> PhysicalInstanceIdV2:
        return PhysicalInstanceIdV2.from_value(self.physical_instance_id)

    def bound_revision(self) -> RevisionOrAsofIdV2:
        return RevisionOrAsofIdV2.from_value(self.revision_or_asof_id)

    def bound_snapshot(self) -> EvidenceSnapshotIdV2:
        return EvidenceSnapshotIdV2.from_value(self.evidence_snapshot_id)


@dataclass
class EvidenceAvailabilityManifestV2:
    """Condition-neutral availability inventory bound to a sealed occurrence."""

    header: ArtifactHeaderV1
    evidence_seal_digest: str
    episode_id: str
    occurrence_reference: OccurrenceReferenceV2
    availability: ConditionNeutralEvidenceAvailabilityV2

    SCHEMA = f"{SCHEMA_NAMESPACE_V2}/evidence-availability-manifest-v2"
    _FIELDS = {
        "header",
        "evidence_seal_digest",
        "episode_id",
        "occurrence_reference",
        "availability",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceAvailabilityManifestV2":
        data = _require_dict(data, "EvidenceAvailabilityManifestV2")
        _require_no_unknown_props(data, cls._FIELDS, "EvidenceAvailabilityManifestV2")
        for forbidden in P1_FORBIDDEN_FIELDS | frozenset({"resolver_result"}):
            if forbidden in data:
                raise StructuralContractError(
                    f"EvidenceAvailabilityManifestV2: forbidden field '{forbidden}'"
                )
        return cls(
            header=_header_from(data),
            evidence_seal_digest=digest_hex(data["evidence_seal_digest"], "evidence_seal_digest"),
            episode_id=_require_str(data["episode_id"], "episode_id"),
            occurrence_reference=OccurrenceReferenceV2.from_dict(
                _require_dict(data["occurrence_reference"], "occurrence_reference")
            ),
            availability=ConditionNeutralEvidenceAvailabilityV2.from_dict(
                _require_dict(data["availability"], "availability")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": _header_to(self.header),
            "evidence_seal_digest": self.evidence_seal_digest,
            "episode_id": self.episode_id,
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "availability": self.availability.to_dict(),
        }


@dataclass(frozen=True)
class SnapshotAuthorityDecisionV2:
    """Ordered snapshot-authority outcome for post-seal source state."""

    result: str
    package_use: str
    post_seal_source_state: PostSealSourceStateV2

    _FIELDS = {"result", "package_use", "post_seal_source_state"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SnapshotAuthorityDecisionV2":
        data = _require_dict(data, "SnapshotAuthorityDecisionV2")
        _require_no_unknown_props(data, cls._FIELDS, "SnapshotAuthorityDecisionV2")
        return cls(
            result=_require_str(data["result"], "result"),
            package_use=_require_str(data["package_use"], "package_use"),
            post_seal_source_state=PostSealSourceStateV2(
                _require_str(data["post_seal_source_state"], "post_seal_source_state")
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "result": self.result,
            "package_use": self.package_use,
            "post_seal_source_state": self.post_seal_source_state.value,
        }
