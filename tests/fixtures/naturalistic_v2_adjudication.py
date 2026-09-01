"""Hermetic fixtures for Naturalistic V2-04 adjudication tests."""

from __future__ import annotations

from eval_naturalistic.digest import artifact_content_digest
from eval_naturalistic.v2.adjudication_facade import AdjudicationWorkflowStateV2
from eval_naturalistic.v2.adjudication_view import P1ViewAuthorityBundle
from eval_naturalistic.v2.adapters.registry import profile_for_legacy_format
from eval_naturalistic.v2.contracts import EvidenceAvailabilityManifestV2
from eval_naturalistic.v2.evidence import (
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
)
from eval_naturalistic.v2.identity import OccurrenceReferenceV2
from eval_naturalistic.v2.resolver import ResolverInputV2, resolve_opaque
from eval_naturalistic.v2.resolver_contracts import OpaqueResolverManifestV2, ResolverResultV2
from eval_naturalistic.v2.role_access import (
    AdjudicationRoleV2,
    RoleAccessManifestV2,
    create_verified_role_context,
    role_access_manifest_digest,
)
from tests.fixtures.naturalistic_v2_p1 import FIXED_DIGEST, sample_availability, sample_seal_manifest
from tests.fixtures.naturalistic_v2_resolver import crush_resolver_input


def _bind_availability(seal) -> EvidenceAvailabilityManifestV2:
    availability = seal.condition_neutral_evidence_availability
    from tests.fixtures.naturalistic_v2_resolver import _bind_availability_manifest

    return _bind_availability_manifest(seal, availability)


def sample_p1_bundle(*, roster_set_id: str = "roster-1") -> P1ViewAuthorityBundle:
    seal = sample_seal_manifest()
    return P1ViewAuthorityBundle(
        construct_freeze_digest=FIXED_DIGEST,
        roster_set_id=roster_set_id,
        evidence_seals=(seal,),
        availability_manifests=(_bind_availability(seal),),
        source_classes=("sqlite_crush",),
        declared_omissions=(("tool_parts",),),
    )


def sample_p1_bundle_present_verbatim_unavailable() -> P1ViewAuthorityBundle:
    availability = sample_availability(
        presence=SourcePresenceV2.PRESENT,
        verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
        summary=SummaryEvidenceAvailabilityV2.UNAVAILABLE,
    )
    seal = sample_seal_manifest(availability=availability)
    return P1ViewAuthorityBundle(
        construct_freeze_digest=FIXED_DIGEST,
        roster_set_id="roster-present-unavail",
        evidence_seals=(seal,),
        availability_manifests=(_bind_availability(seal),),
        source_classes=("sqlite_crush",),
        declared_omissions=(("verbatim_unavailable",),),
    )


def role_manifest(actor_id: str, role: AdjudicationRoleV2) -> RoleAccessManifestV2:
    manifest = RoleAccessManifestV2(
        actor_id=actor_id,
        role=role,
        manifest_digest="pending",
        authorized_view_type="convmem/naturalistic/v2/adjudication-evidence-view-v1",
        collision_forbidden_actor_ids=(),
    )
    digest = role_access_manifest_digest(manifest)
    return RoleAccessManifestV2(
        actor_id=actor_id,
        role=role,
        manifest_digest=digest,
        authorized_view_type=manifest.authorized_view_type,
        collision_forbidden_actor_ids=(),
    )


def closed_workflow(*, roster_set_id: str = "roster-closed") -> AdjudicationWorkflowStateV2:
    state = AdjudicationWorkflowStateV2(p1_bundle=sample_p1_bundle(roster_set_id=roster_set_id))
    view = state.seal_view_roster()
    ctx_a = create_verified_role_context(
        role_manifest("adj-a", AdjudicationRoleV2.ADJUDICATOR_A), view=view
    )
    ctx_b = create_verified_role_context(
        role_manifest("adj-b", AdjudicationRoleV2.ADJUDICATOR_B), view=view
    )
    state.register_role_context(ctx_a)
    state.register_role_context(ctx_b)
    keys = {item.opaque_occurrence_token for item in view.items}
    state.submit_independent_adjudication(
        context=ctx_a, decisions={key: "yes" for key in keys}
    )
    state.submit_independent_adjudication(
        context=ctx_b, decisions={key: "no" for key in keys}
    )
    resolver_ctx = create_verified_role_context(
        role_manifest("resolver", AdjudicationRoleV2.DISAGREEMENT_RESOLVER), view=view
    )
    state.register_role_context(resolver_ctx)
    disagreement_keys = tuple(keys)
    state.seal_disagreement_resolution(
        context=resolver_ctx,
        resolutions={key: "resolved" for key in disagreement_keys},
    )
    state.seal_candidate_closure(candidate_ids=("candidate-1",))
    return state


def p2_manifest_for_result(result: ResolverResultV2) -> OpaqueResolverManifestV2:
    resolver_input = crush_resolver_input()
    if result == ResolverResultV2.EXACT_MATCH:
        return resolve_opaque(resolver_input)
    if result == ResolverResultV2.SUMMARY_ONLY:
        from tests.fixtures.naturalistic_v2_resolver import crush_resolver_input as cri

        return resolve_opaque(
            cri(
                verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
                summary=SummaryEvidenceAvailabilityV2.AVAILABLE,
            )
        )
    if result == ResolverResultV2.NO_MATCH:
        other = sample_p1_bundle().evidence_seals[0].occurrence_reference

        mutated = ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=resolver_input.evidence_availability,
            adapter_profile=resolver_input.adapter_profile,
            legacy_format=resolver_input.legacy_format,
            query_occurrence_reference=OccurrenceReferenceV2(
                source_system_id=other.source_system_id,
                tenant_or_realm_id=other.tenant_or_realm_id,
                authority_scope_id=other.authority_scope_id,
                occurrence_namespace_id="other-ns",
                physical_source_instance_id="other-phys",
                native_id_namespace=other.native_id_namespace,
                native_record_id=other.native_record_id,
                source_revision_or_asof_id=other.source_revision_or_asof_id,
            ),
        )
        return resolve_opaque(mutated)
    if result == ResolverResultV2.EVIDENCE_UNAVAILABLE:
        from tests.fixtures.naturalistic_v2_resolver import crush_resolver_input as cri

        return resolve_opaque(
            cri(
                verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
                summary=SummaryEvidenceAvailabilityV2.UNAVAILABLE,
            )
        )
    return resolve_opaque(
        ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=resolver_input.evidence_availability,
            adapter_profile=profile_for_legacy_format("sqlite_kiro"),
            legacy_format="sqlite_kiro",
            query_occurrence_reference=resolver_input.query_occurrence_reference,
        )
    )
