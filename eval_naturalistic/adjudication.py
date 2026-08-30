"""G2 adjudication and target-registry machinery for naturalistic product-value study."""

from __future__ import annotations

# Candidate bundles are fixed governed records, not behavior-heavy classes.
# pylint: disable=too-many-instance-attributes

import copy
from dataclasses import dataclass, field
from typing import Any

from eval_naturalistic.base import ArtifactHeaderV1, NaturalisticValidation
from eval_naturalistic.contracts import (
    AdjudicationRecordV1,
    EpisodeFrameV1,
    EpisodeRecordV1,
    EpisodeRegistryEntryV1,
    RawEvidenceManifestV1,
    TargetRecordV1,
    TargetRegistryV1,
    TargetSpanBindingV1,
    seal_artifact_dict,
)
from eval_naturalistic.digest import artifact_content_digest, make_artifact_id
from eval_naturalistic.enums import (
    AdjudicationResolutionMethod,
    EligibilityDisposition,
    EpisodeRegistryStatus,
    EvidenceCompletenessState,
    RegistryBuildOutcome,
)


@dataclass
class AdjudicationWorkflowConfigV1:
    """Frozen dual-adjudicator workflow bound to an EpisodeFrame."""

    adjudicator_a_id: str
    adjudicator_b_id: str
    resolution_method: AdjudicationResolutionMethod
    registry_policy_version: str
    prohibited_probe_author_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass
class CandidateAdjudicationBundleV1:
    """One census candidate with independent adjudicator submissions."""

    target_id: str
    span_bindings: list[TargetSpanBindingV1]
    adjudication_records: list[AdjudicationRecordV1]
    resolution_record: AdjudicationRecordV1 | None = None
    resolution_identity: str | None = None
    ground_truth_partition_digest: str | None = None
    provenance_requirement: str | None = None
    admissibility_rationale: str | None = None
    unitization_rationale: str | None = None
    duplicate_of_target_id: str | None = None
    parent_target_id: str | None = None
    ambiguity_state: str | None = None
    secondary_strata: list[str] = field(default_factory=list)


@dataclass
class RegistryBuildResult:
    ok: bool
    registry: TargetRegistryV1 | None
    errors: list[str]
    outcome: RegistryBuildOutcome | None = None
    episode_status: EpisodeRegistryStatus | None = None


def build_evidence_adjudication_view(
    evidence: RawEvidenceManifestV1,
) -> dict[str, Any]:
    """Return a raw-evidence-only view suitable for outcome-blind adjudication."""

    return {
        "episode_id": evidence.episode_id,
        "episode_record_artifact_id": evidence.episode_record_artifact_id,
        "episode_record_digest": evidence.episode_record_digest,
        "sources": [source.to_dict() for source in evidence.sources],
        "completeness_state": evidence.completeness_state.value,
        "missing_source_explanation": evidence.missing_source_explanation,
        "evidence_manifest_artifact_id": evidence.header.artifact_id,
        "evidence_manifest_digest": evidence.header.content_digest,
    }


def registry_membership_snapshot(registry: TargetRegistryV1) -> dict[str, Any]:
    """Canonical membership view used to detect post-seal mutation."""

    eligible = sorted(
        target.target_id
        for target in registry.targets
        if target.eligibility_disposition == EligibilityDisposition.ELIGIBLE
    )
    all_targets = sorted(target.target_id for target in registry.targets)
    episode_statuses = {
        entry.episode_id: entry.registry_status.value for entry in registry.episode_entries
    }
    return {
        "eligible_target_ids": eligible,
        "all_target_ids": all_targets,
        "episode_statuses": episode_statuses,
    }


def validate_adjudicator_provenance(
    records: list[AdjudicationRecordV1],
    *,
    required_adjudicator_ids: set[str],
) -> NaturalisticValidation:
    errors: list[str] = []
    seen: set[str] = set()
    for record in records:
        if not record.adjudicator_id:
            errors.append("adjudication record missing adjudicator_id")
            continue
        if not record.rationale:
            errors.append(f"adjudication record for {record.adjudicator_id} missing rationale")
        if record.adjudicator_id in seen:
            errors.append(f"duplicate adjudicator submission: {record.adjudicator_id}")
        seen.add(record.adjudicator_id)
    missing = required_adjudicator_ids - seen
    if missing:
        names = ", ".join(sorted(missing))
        errors.append(f"missing adjudicator provenance for: {names}")
    return NaturalisticValidation(errors=errors)


def validate_prohibited_role_collision(
    adjudicator_ids: set[str],
    *,
    prohibited_probe_author_ids: set[str],
) -> NaturalisticValidation:
    errors: list[str] = []
    overlap = adjudicator_ids & prohibited_probe_author_ids
    if overlap:
        names = ", ".join(sorted(overlap))
        errors.append(f"prohibited role collision: adjudicator overlaps probe author ({names})")
    return NaturalisticValidation(errors=errors)


def _records_by_adjudicator(
    records: list[AdjudicationRecordV1],
) -> dict[str, AdjudicationRecordV1]:
    return {record.adjudicator_id: record for record in records}


def merge_adjudication_disposition(
    bundle: CandidateAdjudicationBundleV1,
    workflow: AdjudicationWorkflowConfigV1,
) -> tuple[EligibilityDisposition | None, list[str]]:
    """Resolve final disposition from dual adjudication and optional resolution."""

    errors: list[str] = []
    required = {workflow.adjudicator_a_id, workflow.adjudicator_b_id}
    provenance = validate_adjudicator_provenance(
        bundle.adjudication_records,
        required_adjudicator_ids=required,
    )
    if not provenance.ok:
        return None, provenance.errors

    by_id = _records_by_adjudicator(bundle.adjudication_records)
    first = by_id[workflow.adjudicator_a_id].disposition
    second = by_id[workflow.adjudicator_b_id].disposition
    if first == second:
        return first, errors

    if bundle.resolution_record is None:
        errors.append(
            f"adjudicator disagreement on {bundle.target_id} requires blinded resolution"
        )
        return None, errors

    if not bundle.resolution_record.adjudicator_id:
        errors.append(f"resolution record for {bundle.target_id} missing adjudicator_id")
        return None, errors
    if not bundle.resolution_record.rationale:
        errors.append(f"resolution record for {bundle.target_id} missing rationale")
        return None, errors
    if bundle.resolution_identity is None:
        errors.append(f"resolution identity required for disagreement on {bundle.target_id}")
        return None, errors

    resolver_id = bundle.resolution_record.adjudicator_id
    if resolver_id in required:
        errors.append(
            f"resolution adjudicator {resolver_id} must not be an original dual adjudicator"
        )
        return None, errors

    return bundle.resolution_record.disposition, errors


def validate_duplicate_target_identity(
    candidates: list[CandidateAdjudicationBundleV1],
) -> NaturalisticValidation:
    errors: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.target_id in seen:
            errors.append(f"duplicate target_id prohibited: {candidate.target_id}")
        seen.add(candidate.target_id)
    for candidate in candidates:
        if (
            candidate.duplicate_of_target_id
            and candidate.duplicate_of_target_id not in seen
        ):
            errors.append(
                f"duplicate_of_target_id references unknown target: {candidate.duplicate_of_target_id}"
            )
        if (
            candidate.duplicate_of_target_id
            and candidate.duplicate_of_target_id == candidate.target_id
        ):
            errors.append(f"target {candidate.target_id} cannot duplicate itself")
    return NaturalisticValidation(errors=errors)


def compute_episode_registry_status(
    *,
    evidence: RawEvidenceManifestV1,
    targets: list[TargetRecordV1],
    unresolved_disagreement: bool,
) -> EpisodeRegistryStatus:
    if evidence.completeness_state != EvidenceCompletenessState.COMPLETE:
        return EpisodeRegistryStatus.EVIDENCE_INCOMPLETE
    if unresolved_disagreement:
        return EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS
    eligible = [
        target
        for target in targets
        if target.eligibility_disposition == EligibilityDisposition.ELIGIBLE
    ]
    if not eligible:
        return EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS
    return EpisodeRegistryStatus.TARGETS_PRESENT


def _build_target_record(
    bundle: CandidateAdjudicationBundleV1,
    *,
    episode_id: str,
    disposition: EligibilityDisposition,
) -> TargetRecordV1:
    adjudicator_ids = sorted(
        {record.adjudicator_id for record in bundle.adjudication_records}
        | (
            {bundle.resolution_record.adjudicator_id}
            if bundle.resolution_record is not None
            else set()
        )
    )
    records = list(bundle.adjudication_records)
    if bundle.resolution_record is not None:
        records = records + [bundle.resolution_record]
    return TargetRecordV1(
        target_id=bundle.target_id,
        episode_id=episode_id,
        span_bindings=list(bundle.span_bindings),
        eligibility_disposition=disposition,
        ground_truth_partition_digest=bundle.ground_truth_partition_digest,
        provenance_requirement=bundle.provenance_requirement,
        admissibility_rationale=bundle.admissibility_rationale,
        unitization_rationale=bundle.unitization_rationale,
        duplicate_of_target_id=bundle.duplicate_of_target_id,
        parent_target_id=bundle.parent_target_id,
        ambiguity_state=bundle.ambiguity_state,
        secondary_strata=list(bundle.secondary_strata),
        adjudication_records=records,
        resolution_identity=bundle.resolution_identity,
        adjudicator_ids=adjudicator_ids,
    )


def _finalize_registry_body(
    body: dict[str, Any],
    *,
    seal_time: str,
) -> TargetRegistryV1:
    digest = artifact_content_digest(body)
    body = copy.deepcopy(body)
    body["header"] = {
        **body["header"],
        "artifact_id": make_artifact_id(kind="registry", content_digest=digest),
        "content_digest": digest,
    }
    sealed = seal_artifact_dict(body, seal_time=seal_time)
    return TargetRegistryV1.from_dict(sealed)


def build_sealed_target_registry(
    *,
    frame: EpisodeFrameV1,
    episode: EpisodeRecordV1,
    evidence: RawEvidenceManifestV1,
    candidates: list[CandidateAdjudicationBundleV1],
    workflow: AdjudicationWorkflowConfigV1,
    seal_time: str = "2026-08-30T02:00:00Z",
    responsible_role: str = "study_owner",
) -> RegistryBuildResult:
    """Turn governed adjudication inputs into a sealed TargetRegistryV1."""

    errors: list[str] = []

    if not frame.header.sealed:
        errors.append("EpisodeFrame must be sealed before registry build")
    if not episode.header.sealed:
        errors.append("EpisodeRecord must be sealed before registry build")
    if not evidence.header.sealed:
        errors.append("RawEvidenceManifest must be sealed before registry build")
    if episode.frame_artifact_id != frame.header.artifact_id:
        errors.append("EpisodeRecord frame binding mismatch")
    if evidence.episode_record_artifact_id != episode.header.artifact_id:
        errors.append("RawEvidenceManifest episode_record binding mismatch")
    if evidence.episode_record_digest != episode.header.content_digest:
        errors.append("RawEvidenceManifest episode_record_digest mismatch")
    if evidence.episode_id != episode.episode_id:
        errors.append("RawEvidenceManifest episode_id mismatch")

    duplicate_check = validate_duplicate_target_identity(candidates)
    errors.extend(duplicate_check.errors)

    if errors:
        return RegistryBuildResult(
            ok=False,
            registry=None,
            errors=errors,
            outcome=RegistryBuildOutcome.PROTOCOL_INVALID,
        )

    if evidence.completeness_state != EvidenceCompletenessState.COMPLETE:
        body = {
            "header": ArtifactHeaderV1(
                artifact_id="pending",
                schema_version=TargetRegistryV1.SCHEMA,
                parent_artifact_id=evidence.header.artifact_id,
                parent_digest=evidence.header.content_digest,
                created_at=seal_time,
                seal_time=None,
                responsible_role=responsible_role,
                content_digest=None,
                sealed=False,
            ).to_dict(),
            "evidence_manifest_ids": [evidence.header.artifact_id],
            "episode_entries": [
                EpisodeRegistryEntryV1(
                    episode_id=episode.episode_id,
                    registry_status=EpisodeRegistryStatus.EVIDENCE_INCOMPLETE,
                    evidence_manifest_digest=evidence.header.content_digest or "",
                    target_ids=[],
                ).to_dict()
            ],
            "targets": [],
            "registry_policy_version": workflow.registry_policy_version,
        }
        registry = _finalize_registry_body(body, seal_time=seal_time)
        return RegistryBuildResult(
            ok=True,
            registry=registry,
            errors=[],
            outcome=RegistryBuildOutcome.EVIDENCE_INCOMPLETE,
            episode_status=EpisodeRegistryStatus.EVIDENCE_INCOMPLETE,
        )

    targets: list[TargetRecordV1] = []
    unresolved_disagreement = False
    required = {workflow.adjudicator_a_id, workflow.adjudicator_b_id}

    for bundle in candidates:
        role_check = validate_prohibited_role_collision(
            required | ({bundle.resolution_record.adjudicator_id} if bundle.resolution_record else set()),
            prohibited_probe_author_ids=set(workflow.prohibited_probe_author_ids),
        )
        if not role_check.ok:
            errors.extend(role_check.errors)
            continue

        provenance = validate_adjudicator_provenance(
            bundle.adjudication_records,
            required_adjudicator_ids=required,
        )
        if not provenance.ok:
            errors.extend(provenance.errors)
            continue

        disposition, merge_errors = merge_adjudication_disposition(bundle, workflow)
        if merge_errors:
            if any("requires blinded resolution" in err for err in merge_errors):
                unresolved_disagreement = True
            else:
                errors.extend(merge_errors)
            continue
        if disposition is None:
            unresolved_disagreement = True
            continue

        targets.append(
            _build_target_record(
                bundle,
                episode_id=episode.episode_id,
                disposition=disposition,
            )
        )

    if errors:
        return RegistryBuildResult(
            ok=False,
            registry=None,
            errors=errors,
            outcome=RegistryBuildOutcome.PROTOCOL_INVALID,
        )

    if unresolved_disagreement:
        body = {
            "header": ArtifactHeaderV1(
                artifact_id="pending",
                schema_version=TargetRegistryV1.SCHEMA,
                parent_artifact_id=evidence.header.artifact_id,
                parent_digest=evidence.header.content_digest,
                created_at=seal_time,
                seal_time=None,
                responsible_role=responsible_role,
                content_digest=None,
                sealed=False,
            ).to_dict(),
            "evidence_manifest_ids": [evidence.header.artifact_id],
            "episode_entries": [
                EpisodeRegistryEntryV1(
                    episode_id=episode.episode_id,
                    registry_status=EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS,
                    evidence_manifest_digest=evidence.header.content_digest or "",
                    target_ids=[],
                ).to_dict()
            ],
            "targets": [],
            "registry_policy_version": workflow.registry_policy_version,
        }
        registry = _finalize_registry_body(body, seal_time=seal_time)
        return RegistryBuildResult(
            ok=True,
            registry=registry,
            errors=[],
            outcome=RegistryBuildOutcome.ADJUDICATION_AMBIGUOUS,
            episode_status=EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS,
        )

    episode_status = compute_episode_registry_status(
        evidence=evidence,
        targets=targets,
        unresolved_disagreement=False,
    )

    eligible_target_ids = [
        target.target_id
        for target in targets
        if target.eligibility_disposition == EligibilityDisposition.ELIGIBLE
    ]
    body = {
        "header": ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=TargetRegistryV1.SCHEMA,
            parent_artifact_id=evidence.header.artifact_id,
            parent_digest=evidence.header.content_digest,
            created_at=seal_time,
            seal_time=None,
            responsible_role=responsible_role,
            content_digest=None,
            sealed=False,
        ).to_dict(),
        "evidence_manifest_ids": [evidence.header.artifact_id],
        "episode_entries": [
            EpisodeRegistryEntryV1(
                episode_id=episode.episode_id,
                registry_status=episode_status,
                evidence_manifest_digest=evidence.header.content_digest or "",
                target_ids=eligible_target_ids,
            ).to_dict()
        ],
        "targets": [target.to_dict() for target in targets],
        "registry_policy_version": workflow.registry_policy_version,
    }
    registry = _finalize_registry_body(body, seal_time=seal_time)
    outcome = (
        RegistryBuildOutcome.SEALED
        if episode_status == EpisodeRegistryStatus.TARGETS_PRESENT
        else RegistryBuildOutcome.SEALED
    )
    return RegistryBuildResult(
        ok=True,
        registry=registry,
        errors=[],
        outcome=outcome,
        episode_status=episode_status,
    )


def validate_registry_build(
    *,
    frame: EpisodeFrameV1,
    episode: EpisodeRecordV1,
    evidence: RawEvidenceManifestV1,
    registry: TargetRegistryV1,
) -> NaturalisticValidation:
    """Hermetic validation of a built registry against upstream authority."""

    errors: list[str] = []
    if registry.header.parent_artifact_id != evidence.header.artifact_id:
        errors.append("TargetRegistry parent_artifact_id must bind to evidence manifest")
    if registry.header.parent_digest != evidence.header.content_digest:
        errors.append("TargetRegistry parent_digest must bind to evidence manifest digest")
    if evidence.header.artifact_id not in registry.evidence_manifest_ids:
        errors.append("TargetRegistry missing evidence manifest id")
    if not registry.header.sealed:
        errors.append("TargetRegistry must be sealed")

    episode_ids = {entry.episode_id for entry in registry.episode_entries}
    if episode.episode_id not in episode_ids:
        errors.append("TargetRegistry missing episode entry")

    for entry in registry.episode_entries:
        if entry.registry_status == EpisodeRegistryStatus.EVIDENCE_INCOMPLETE:
            if evidence.completeness_state == EvidenceCompletenessState.COMPLETE:
                errors.append("EVIDENCE_INCOMPLETE status requires incomplete evidence")
        if entry.registry_status == EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS:
            eligible = [
                target
                for target in registry.targets
                if target.eligibility_disposition == EligibilityDisposition.ELIGIBLE
            ]
            if eligible:
                errors.append("ZERO_ELIGIBLE_TARGETS cannot coexist with eligible targets")
        if entry.registry_status == EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS:
            if registry.targets:
                errors.append("TARGET_ADJUDICATION_AMBIGUOUS cannot include sealed target rows")

    if episode.frame_artifact_id != frame.header.artifact_id:
        errors.append("upstream EpisodeRecord frame binding mismatch during registry validation")

    return NaturalisticValidation(errors=errors)


def validate_registry_membership_immutable(
    sealed_registry: TargetRegistryV1,
    proposed_registry: TargetRegistryV1,
) -> NaturalisticValidation:
    """Reject add/remove/substitute membership changes against a sealed registry."""

    errors: list[str] = []
    if not sealed_registry.header.sealed:
        errors.append("reference registry must be sealed")
        return NaturalisticValidation(errors=errors)

    before = registry_membership_snapshot(sealed_registry)
    after = registry_membership_snapshot(proposed_registry)
    if before != after:
        errors.append("registry membership mutation prohibited after seal")
    if sealed_registry.header.artifact_id != proposed_registry.header.artifact_id:
        errors.append("registry artifact_id substitution prohibited after seal")
    if sealed_registry.header.content_digest != proposed_registry.header.content_digest:
        if before == after:
            errors.append("registry digest changed without membership change")
    return NaturalisticValidation(errors=errors)


def reject_capture_driven_registry_mutation(
    sealed_registry: TargetRegistryV1,
    proposed_registry: TargetRegistryV1,
) -> NaturalisticValidation:
    """Fail closed when downstream capture state attempts registry membership edits."""

    errors: list[str] = []
    membership = validate_registry_membership_immutable(sealed_registry, proposed_registry)
    errors.extend(membership.errors)

    before_eligible = {
        target.target_id
        for target in sealed_registry.targets
        if target.eligibility_disposition == EligibilityDisposition.ELIGIBLE
    }
    after_eligible = {
        target.target_id
        for target in proposed_registry.targets
        if target.eligibility_disposition == EligibilityDisposition.ELIGIBLE
    }
    injected = after_eligible - before_eligible
    removed = before_eligible - after_eligible
    if injected:
        names = ", ".join(sorted(injected))
        errors.append(f"capture-driven target injection rejected: {names}")
    if removed:
        names = ", ".join(sorted(removed))
        errors.append(f"capture-driven target removal rejected: {names}")

    before_all = {target.target_id for target in sealed_registry.targets}
    after_all = {target.target_id for target in proposed_registry.targets}
    substituted = (after_all - before_all) | (before_all - after_all)
    if substituted and not injected and not removed:
        names = ", ".join(sorted(substituted))
        errors.append(f"capture-driven target substitution rejected: {names}")

    return NaturalisticValidation(errors=errors)
