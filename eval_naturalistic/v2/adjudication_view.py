"""P1-only AdjudicationEvidenceViewV1 construction — no P2 dependency surface."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from eval_naturalistic.base import StructuralContractError, _require_str
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.contracts import (
    EvidenceAvailabilityManifestV2,
    EvidenceSealManifestV2,
)
from eval_naturalistic.v2.view_deny import validate_adjudication_view_structure

VIEW_SCHEMA = "convmem/naturalistic/v2/adjudication-evidence-view-v1"
CANONICAL_UNSPECIFIED_TIME = "UNSPECIFIED_EVIDENCE_TIME"
CANONICAL_UNSPECIFIED_AUTHOR = "UNSPECIFIED_AUTHORSHIP"
CANONICAL_EMPTY_LIST: list[str] = []


@dataclass(frozen=True)
class P1ViewAuthorityBundle:
    """Bounded P1 inputs for blinded adjudication view construction."""

    construct_freeze_digest: str
    roster_set_id: str
    evidence_seals: tuple[EvidenceSealManifestV2, ...]
    availability_manifests: tuple[EvidenceAvailabilityManifestV2, ...]
    source_classes: tuple[str, ...]
    declared_omissions: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        if len(self.evidence_seals) != len(self.availability_manifests):
            raise StructuralContractError("P1 bundle seal/availability length mismatch")
        if len(self.evidence_seals) != len(self.source_classes):
            raise StructuralContractError("P1 bundle seal/source_class length mismatch")
        if len(self.evidence_seals) != len(self.declared_omissions):
            raise StructuralContractError("P1 bundle seal/omissions length mismatch")


@dataclass(frozen=True)
class AdjudicationEvidenceViewItemV1:
    episode_id: str
    opaque_occurrence_token: str
    opaque_span_token: str
    source_class: str
    condition_neutral_source_inventory: dict[str, Any]
    condition_neutral_evidence_availability: dict[str, str]
    event_time: str
    authorship: str
    chronology: dict[str, str]
    reply_structure: dict[str, str]
    canonical_evidence_content: dict[str, str]
    attachment_material_availability: dict[str, str]
    extension_field_presence: dict[str, str]
    completeness_scope_without_resolver_result: dict[str, Any]

    ALLOWED = frozenset(
        {
            "episode_id",
            "opaque_occurrence_token",
            "opaque_span_token",
            "source_class",
            "condition_neutral_source_inventory",
            "condition_neutral_evidence_availability",
            "event_time",
            "authorship",
            "chronology",
            "reply_structure",
            "canonical_evidence_content",
            "attachment_material_availability",
            "extension_field_presence",
            "completeness_scope_without_resolver_result",
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "opaque_occurrence_token": self.opaque_occurrence_token,
            "opaque_span_token": self.opaque_span_token,
            "source_class": self.source_class,
            "condition_neutral_source_inventory": self.condition_neutral_source_inventory,
            "condition_neutral_evidence_availability": self.condition_neutral_evidence_availability,
            "event_time": self.event_time,
            "authorship": self.authorship,
            "chronology": self.chronology,
            "reply_structure": self.reply_structure,
            "canonical_evidence_content": self.canonical_evidence_content,
            "attachment_material_availability": self.attachment_material_availability,
            "extension_field_presence": self.extension_field_presence,
            "completeness_scope_without_resolver_result": (
                self.completeness_scope_without_resolver_result
            ),
        }


@dataclass(frozen=True)
class AdjudicationEvidenceViewV1:
    schema_version: str
    roster_digest: str
    items: tuple[AdjudicationEvidenceViewItemV1, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "roster_digest": self.roster_digest,
            "items": [item.to_dict() for item in self.items],
        }

    def canonical_bytes(self) -> bytes:
        return canonical_artifact_bytes(self.to_dict())

    def content_digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def _opaque_token(prefix: str, roster_set_id: str, material: str) -> str:
    payload = {"roster_set_id": roster_set_id, "material": material}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _roster_sort_key(seal: EvidenceSealManifestV2) -> tuple[str, ...]:
    return seal.occurrence_reference.identity_key()


def build_adjudication_evidence_view(bundle: P1ViewAuthorityBundle) -> AdjudicationEvidenceViewV1:
    """Pure P1 projection with constant shape — never consults P2."""

    _require_str(bundle.construct_freeze_digest, "construct_freeze_digest")
    _require_str(bundle.roster_set_id, "roster_set_id")
    indexed = list(zip(bundle.evidence_seals, bundle.availability_manifests, strict=True))
    indexed.sort(key=lambda row: _roster_sort_key(row[0]))

    roster_material = [
        {
            "episode_id": seal.episode_id,
            "occurrence_key": seal.occurrence_reference.identity_key(),
        }
        for seal, _ in indexed
    ]
    roster_digest = hashlib.sha256(
        json.dumps(
            {"roster_set_id": bundle.roster_set_id, "rows": roster_material},
            sort_keys=True,
        ).encode()
    ).hexdigest()

    items: list[AdjudicationEvidenceViewItemV1] = []
    for index, (seal, availability) in enumerate(indexed):
        if not availability.occurrence_reference.same_occurrence_as(seal.occurrence_reference):
            raise StructuralContractError("P1 availability occurrence mismatch")
        occ_key = "|".join(seal.occurrence_reference.identity_key())
        opaque_occ = _opaque_token("occ", bundle.roster_set_id, occ_key)
        opaque_span = _opaque_token("span", bundle.roster_set_id, f"{occ_key}:{index}")
        omissions = bundle.declared_omissions[index]
        availability_dict = availability.availability.to_dict()
        item = AdjudicationEvidenceViewItemV1(
            episode_id=seal.episode_id,
            opaque_occurrence_token=opaque_occ,
            opaque_span_token=opaque_span,
            source_class=bundle.source_classes[index],
            condition_neutral_source_inventory={
                "inventory_entries": list(CANONICAL_EMPTY_LIST),
                "scope_state": "P1_CONDITION_NEUTRAL_INVENTORY",
            },
            condition_neutral_evidence_availability=availability_dict,
            event_time=CANONICAL_UNSPECIFIED_TIME,
            authorship=CANONICAL_UNSPECIFIED_AUTHOR,
            chronology={"structure_state": "P1_LINEAR", "ordering_state": "ROSTER_FROZEN"},
            reply_structure={"thread_state": "P1_SESSION_SCOPED"},
            canonical_evidence_content={
                "representation": "OPAQUE_P1_CANONICAL",
                "opaque_content_token": _opaque_token(
                    "content", bundle.roster_set_id, f"{occ_key}:canonical"
                ),
            },
            attachment_material_availability={"attachment_state": "P1_DECLARED_ONLY"},
            extension_field_presence={"extension_state": "P1_DECLARED_ONLY"},
            completeness_scope_without_resolver_result={
                "scope_state": "P1_INVENTORY_AND_OMISSIONS",
                "declared_omissions": list(omissions),
            },
        )
        items.append(item)

    view = AdjudicationEvidenceViewV1(
        schema_version=VIEW_SCHEMA,
        roster_digest=roster_digest,
        items=tuple(items),
    )
    validate_adjudication_view_structure(view.to_dict(), label="AdjudicationEvidenceViewV1")
    _validate_constant_shape(view)
    return view


def _validate_constant_shape(view: AdjudicationEvidenceViewV1) -> None:
    payload = view.to_dict()
    required_top = {"schema_version", "roster_digest", "items"}
    if set(payload) != required_top:
        raise StructuralContractError("AdjudicationEvidenceViewV1 top-level keys must be constant")
    for item in payload["items"]:
        if set(item) != AdjudicationEvidenceViewItemV1.ALLOWED:
            raise StructuralContractError("view item keys must match closed allowlist exactly")


def validate_canonical_view_artifact(view: AdjudicationEvidenceViewV1) -> None:
    validate_adjudication_view_structure(view.to_dict(), label="AdjudicationEvidenceViewV1")
    _validate_constant_shape(view)


def validate_view_payload_shape(payload: dict[str, Any]) -> None:
    validate_adjudication_view_structure(payload, label="AdjudicationEvidenceViewV1")
    required_top = {"schema_version", "roster_digest", "items"}
    if set(payload) != required_top:
        raise StructuralContractError("AdjudicationEvidenceViewV1 top-level keys must be constant")
    for item in payload["items"]:
        if set(item) != AdjudicationEvidenceViewItemV1.ALLOWED:
            raise StructuralContractError("view item keys must match closed allowlist exactly")
