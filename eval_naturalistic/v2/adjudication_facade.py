"""Blinded adjudication facade, closure state machine, and append-only P2 join."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.adjudication_view import (
    AdjudicationEvidenceViewV1,
    P1ViewAuthorityBundle,
    build_adjudication_evidence_view,
    validate_canonical_view_artifact,
)
from eval_naturalistic.v2.contracts import (
    EvidenceAvailabilityManifestV2,
    EvidenceSealManifestV2,
)
from eval_naturalistic.v2.resolver_contracts import OpaqueResolverManifestV2
from eval_naturalistic.v2.role_access import (
    AdjudicationRoleV2,
    VerifiedRoleContextV2,
    create_verified_role_context,
    validate_role_collision,
    verify_role_context,
)


class JoinStateV2(str, Enum):
    NOT_JOINED = "NOT_JOINED"
    JOIN_BLOCKED = "JOIN_BLOCKED"
    JOINED = "JOINED"


@dataclass
class AdjudicationSubmissionV2:
    actor_id: str
    decisions: dict[str, str]
    submission_digest: str
    sealed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "decisions": self.decisions,
            "submission_digest": self.submission_digest,
            "sealed": self.sealed,
        }


@dataclass
class DisagreementResolutionV2:
    disagreement_keys: tuple[str, ...]
    resolutions: dict[str, str]
    resolution_digest: str
    sealed: bool = False


@dataclass
class CandidateClosureV2:
    candidate_ids: tuple[str, ...]
    unitization_digest: str
    deduplication_digest: str
    membership_digest: str
    sealed: bool = False


@dataclass
class PostAdjudicationP2JoinRecordV2:
    adjudication_closure_digest: str
    opaque_p2_output_digest: str
    join_digest: str

    def to_dict(self) -> dict[str, str]:
        return {
            "adjudication_closure_digest": self.adjudication_closure_digest,
            "opaque_p2_output_digest": self.opaque_p2_output_digest,
            "join_digest": self.join_digest,
        }


@dataclass
class AdjudicationWorkflowStateV2:
    p1_bundle: P1ViewAuthorityBundle
    view: AdjudicationEvidenceViewV1 | None = None
    view_sealed: bool = False
    role_contexts: list[VerifiedRoleContextV2] = field(default_factory=list)
    submission_a: AdjudicationSubmissionV2 | None = None
    submission_b: AdjudicationSubmissionV2 | None = None
    disagreement: DisagreementResolutionV2 | None = None
    candidate_closure: CandidateClosureV2 | None = None
    adjudication_closure_digest: str | None = None
    join_record: PostAdjudicationP2JoinRecordV2 | None = None
    join_state: JoinStateV2 = JoinStateV2.NOT_JOINED

    def seal_view_roster(self) -> AdjudicationEvidenceViewV1:
        if self.view_sealed and self.view is not None:
            return self.view
        before_seals = [seal.to_dict() for seal in self.p1_bundle.evidence_seals]
        self.view = build_adjudication_evidence_view(self.p1_bundle)
        validate_canonical_view_artifact(self.view)
        after_seals = [seal.to_dict() for seal in self.p1_bundle.evidence_seals]
        if before_seals != after_seals:
            raise StructuralContractError("view construction mutated canonical P1 bytes")
        self.view_sealed = True
        return self.view

    def register_role_context(self, context: VerifiedRoleContextV2) -> None:
        if not self.view_sealed or self.view is None:
            raise StructuralContractError("view roster must be sealed before role registration")
        verify_role_context(context, view=self.view)
        if context.manifest.role == AdjudicationRoleV2.CONTROLLER:
            raise StructuralContractError("controller role cannot access adjudication facade")
        self.role_contexts.append(context)
        validate_role_collision(tuple(self.role_contexts))

    def _require_view(self) -> AdjudicationEvidenceViewV1:
        if not self.view_sealed or self.view is None:
            raise StructuralContractError("view roster not sealed")
        return self.view

    def _all_roster_keys(self) -> set[str]:
        view = self._require_view()
        return {item.opaque_occurrence_token for item in view.items}

    def submit_independent_adjudication(
        self,
        *,
        context: VerifiedRoleContextV2,
        decisions: dict[str, str],
    ) -> AdjudicationSubmissionV2:
        view = self._require_view()
        verify_role_context(context, view=view)
        if context.manifest.role not in {
            AdjudicationRoleV2.ADJUDICATOR_A,
            AdjudicationRoleV2.ADJUDICATOR_B,
        }:
            raise StructuralContractError("only independent adjudicators may submit")
        roster = self._all_roster_keys()
        if set(decisions) != roster:
            raise StructuralContractError("submission must cover every sealed roster item")
        submission = AdjudicationSubmissionV2(
            actor_id=context.manifest.actor_id,
            decisions=decisions,
            submission_digest=_digest({"decisions": decisions, "view": view.content_digest()}),
            sealed=True,
        )
        if context.manifest.role == AdjudicationRoleV2.ADJUDICATOR_A:
            if self.submission_a is not None:
                raise StructuralContractError("first adjudicator already submitted")
            self.submission_a = submission
        else:
            if self.submission_b is not None:
                raise StructuralContractError("second adjudicator already submitted")
            self.submission_b = submission
        return submission

    def seal_disagreement_resolution(
        self,
        *,
        context: VerifiedRoleContextV2,
        resolutions: dict[str, str],
    ) -> DisagreementResolutionV2:
        view = self._require_view()
        verify_role_context(context, view=view)
        if context.manifest.role != AdjudicationRoleV2.DISAGREEMENT_RESOLVER:
            raise StructuralContractError("disagreement resolution requires resolver role")
        if self.submission_a is None or self.submission_b is None:
            raise StructuralContractError("both submissions required before disagreement seal")
        disagreement_keys = tuple(
            key
            for key in self._all_roster_keys()
            if self.submission_a.decisions[key] != self.submission_b.decisions[key]
        )
        if set(resolutions) != set(disagreement_keys):
            raise StructuralContractError("resolution must cover disagreement set exactly")
        self.disagreement = DisagreementResolutionV2(
            disagreement_keys=disagreement_keys,
            resolutions=resolutions,
            resolution_digest=_digest(
                {
                    "disagreement_keys": disagreement_keys,
                    "resolutions": resolutions,
                    "view": view.content_digest(),
                }
            ),
            sealed=True,
        )
        return self.disagreement

    def seal_candidate_closure(
        self,
        *,
        candidate_ids: tuple[str, ...],
    ) -> CandidateClosureV2:
        if self.submission_a is None or self.submission_b is None:
            raise StructuralContractError("submissions incomplete")
        if self.disagreement is None or not self.disagreement.sealed:
            raise StructuralContractError("disagreement resolution must be sealed first")
        view = self._require_view()
        unitization_digest = _digest({"candidate_ids": candidate_ids, "phase": "unitization"})
        dedup_digest = _digest({"candidate_ids": candidate_ids, "phase": "deduplication"})
        membership_digest = _digest({"candidate_ids": candidate_ids, "phase": "membership"})
        self.candidate_closure = CandidateClosureV2(
            candidate_ids=candidate_ids,
            unitization_digest=unitization_digest,
            deduplication_digest=dedup_digest,
            membership_digest=membership_digest,
            sealed=True,
        )
        self.adjudication_closure_digest = _digest(
            {
                "view": view.content_digest(),
                "submission_a": self.submission_a.submission_digest,
                "submission_b": self.submission_b.submission_digest,
                "disagreement": self.disagreement.resolution_digest,
                "candidate_membership": membership_digest,
            }
        )
        return self.candidate_closure

    def append_p2_join(
        self,
        *,
        p2_manifest: OpaqueResolverManifestV2,
    ) -> PostAdjudicationP2JoinRecordV2:
        if self.adjudication_closure_digest is None:
            self.join_state = JoinStateV2.JOIN_BLOCKED
            raise StructuralContractError("P2 join forbidden before adjudication closure")
        if self.submission_a is None or self.submission_b is None:
            self.join_state = JoinStateV2.JOIN_BLOCKED
            raise StructuralContractError("P2 join forbidden before two submissions")
        if self.disagreement is None or not self.disagreement.sealed:
            self.join_state = JoinStateV2.JOIN_BLOCKED
            raise StructuralContractError("P2 join forbidden before disagreement closure")
        if self.candidate_closure is None or not self.candidate_closure.sealed:
            self.join_state = JoinStateV2.JOIN_BLOCKED
            raise StructuralContractError("P2 join forbidden before candidate closure")

        before_view = self.view.to_dict() if self.view else None
        join_body = {
            "adjudication_closure_digest": self.adjudication_closure_digest,
            "opaque_p2_output_digest": p2_manifest.resolver_output_digest,
        }
        join_digest = _digest(join_body)
        record = PostAdjudicationP2JoinRecordV2(
            adjudication_closure_digest=self.adjudication_closure_digest,
            opaque_p2_output_digest=p2_manifest.resolver_output_digest,
            join_digest=join_digest,
        )
        self.join_record = record
        self.join_state = JoinStateV2.JOINED
        after_view = self.view.to_dict() if self.view else None
        if before_view != after_view:
            raise StructuralContractError("P2 join mutated sealed adjudication view")
        return record


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class AdjudicationFacadeV2:
    """Hermetic adjudication-facing API — canonical view artifact + verified role only."""

    @staticmethod
    def accept_view_for_role(
        view: AdjudicationEvidenceViewV1,
        *,
        context: VerifiedRoleContextV2,
    ) -> bytes:
        verify_role_context(context, view=view)
        validate_canonical_view_artifact(view)
        return view.canonical_bytes()

    @staticmethod
    def reject_raw_p1_object(raw: EvidenceSealManifestV2) -> None:
        raise StructuralContractError("raw P1 objects are rejected by adjudication facade")

    @staticmethod
    def reject_raw_p2_object(raw: OpaqueResolverManifestV2) -> None:
        raise StructuralContractError("raw P2 objects are rejected by adjudication facade")

    @staticmethod
    def reject_forged_context(
        context: VerifiedRoleContextV2,
        *,
        view: AdjudicationEvidenceViewV1,
    ) -> None:
        verify_role_context(context, view=view, expected_verification_digest="0" * 64)

    @staticmethod
    def reject_arbitrary_mapping(payload: dict[str, Any]) -> None:
        raise StructuralContractError("arbitrary mappings are rejected by adjudication facade")
