"""V2-04 — blinded P3 access boundary and post-adjudication join tests."""

from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.adjudication_facade import (
    AdjudicationFacadeV2,
    AdjudicationWorkflowStateV2,
    JoinStateV2,
)
from eval_naturalistic.v2.adjudication_view import (
    VIEW_SCHEMA,
    AdjudicationEvidenceViewItemV1,
    build_adjudication_evidence_view,
    validate_view_payload_shape,
)
from eval_naturalistic.v2.adapters.capability import CapabilityVectorV2, EvidenceCompletenessCapability
from eval_naturalistic.v2.evidence import SourcePresenceV2, VerbatimEvidenceAvailabilityV2
from eval_naturalistic.v2.resolver import resolve_opaque
from eval_naturalistic.v2.resolver_contracts import ResolverResultV2
from eval_naturalistic.v2.role_access import (
    AdjudicationRoleV2,
    VerifiedRoleContextV2,
    create_verified_role_context,
)
from eval_naturalistic.v2.view_deny import validate_adjudication_view_structure
from tests.fixtures.naturalistic_v2_adjudication import (
    closed_workflow,
    p2_manifest_for_result,
    role_manifest,
    sample_p1_bundle,
    sample_p1_bundle_present_verbatim_unavailable,
)
from tests.fixtures.naturalistic_v2_resolver import crush_resolver_input


def _view_bytes_from_p1(bundle) -> bytes:
    return build_adjudication_evidence_view(bundle).canonical_bytes()


class NaturalisticV2AdjudicationTests(unittest.TestCase):
    def test_exact_vs_summary_only_identical_visible_bytes(self) -> None:
        bundle = sample_p1_bundle()
        p1_bytes = _view_bytes_from_p1(bundle)
        _ = p2_manifest_for_result(ResolverResultV2.EXACT_MATCH)
        _ = p2_manifest_for_result(ResolverResultV2.SUMMARY_ONLY)
        self.assertEqual(p1_bytes, _view_bytes_from_p1(bundle))

    def test_all_five_p2_states_identical_visible_artifacts(self) -> None:
        bundle = sample_p1_bundle()
        baseline = _view_bytes_from_p1(bundle)
        for result in ResolverResultV2:
            _ = p2_manifest_for_result(result)
            self.assertEqual(_view_bytes_from_p1(bundle), baseline)

    def test_p2_error_cannot_remove_row(self) -> None:
        view = build_adjudication_evidence_view(sample_p1_bundle())
        before = len(view.items)
        _ = p2_manifest_for_result(ResolverResultV2.ERROR)
        after = len(build_adjudication_evidence_view(sample_p1_bundle()).items)
        self.assertEqual(before, after)

    def test_capability_variations_identical_visible_artifacts(self) -> None:
        bundle = sample_p1_bundle()
        baseline = _view_bytes_from_p1(bundle)
        profile = crush_resolver_input().adapter_profile
        for completeness in EvidenceCompletenessCapability:
            vector = profile.capability_vector.with_overrides(
                evidence_completeness=completeness.value
            )
            _ = profile.with_capability_vector(vector)
            self.assertEqual(_view_bytes_from_p1(bundle), baseline)

    def test_unsupported_profile_cannot_omit_p1_row(self) -> None:
        view = build_adjudication_evidence_view(sample_p1_bundle())
        _ = p2_manifest_for_result(ResolverResultV2.ERROR)
        self.assertEqual(len(view.items), 1)

    def test_p2_failure_leaks_no_exception_text(self) -> None:
        with self.assertRaises(StructuralContractError):
            AdjudicationFacadeV2.reject_raw_p2_object(p2_manifest_for_result(ResolverResultV2.ERROR))
        try:
            build_adjudication_evidence_view(sample_p1_bundle())
        except StructuralContractError as exc:
            self.assertNotIn("traceback", str(exc).lower())

    def test_nested_path_locator_rejected(self) -> None:
        payload = build_adjudication_evidence_view(sample_p1_bundle()).to_dict()
        payload["items"][0]["source_path"] = "/tmp/x"
        with self.assertRaises(StructuralContractError):
            validate_adjudication_view_structure(payload, label="view")

    def test_resolver_capability_aliases_rejected(self) -> None:
        payload = build_adjudication_evidence_view(sample_p1_bundle()).to_dict()
        payload["resolverResult"] = "EXACT_MATCH"
        with self.assertRaises(StructuralContractError):
            validate_adjudication_view_structure(payload, label="view")
        payload = build_adjudication_evidence_view(sample_p1_bundle()).to_dict()
        payload["capability-vector"] = {}
        with self.assertRaises(StructuralContractError):
            validate_adjudication_view_structure(payload, label="view")

    def test_unknown_structural_escape_alias_rejected(self) -> None:
        payload = build_adjudication_evidence_view(sample_p1_bundle()).to_dict()
        payload["metadata"] = {"resolver_result": "x"}
        with self.assertRaises(StructuralContractError):
            validate_adjudication_view_structure(payload, label="view")

    def test_missing_key_rejected(self) -> None:
        payload = build_adjudication_evidence_view(sample_p1_bundle()).to_dict()
        del payload["items"][0]["event_time"]
        with self.assertRaises(StructuralContractError):
            validate_view_payload_shape(payload)

    def test_join_after_one_submission_rejected(self) -> None:
        state = AdjudicationWorkflowStateV2(p1_bundle=sample_p1_bundle())
        view = state.seal_view_roster()
        ctx_a = create_verified_role_context(
            role_manifest("adj-a", AdjudicationRoleV2.ADJUDICATOR_A), view=view
        )
        state.register_role_context(ctx_a)
        key = view.items[0].opaque_occurrence_token
        state.submit_independent_adjudication(context=ctx_a, decisions={key: "yes"})
        with self.assertRaises(StructuralContractError):
            state.append_p2_join(p2_manifest=p2_manifest_for_result(ResolverResultV2.EXACT_MATCH))
        self.assertEqual(state.join_state, JoinStateV2.JOIN_BLOCKED)

    def test_join_before_disagreement_closure_rejected(self) -> None:
        state = AdjudicationWorkflowStateV2(p1_bundle=sample_p1_bundle())
        view = state.seal_view_roster()
        ctx_a = create_verified_role_context(
            role_manifest("adj-a", AdjudicationRoleV2.ADJUDICATOR_A), view=view
        )
        ctx_b = create_verified_role_context(
            role_manifest("adj-b", AdjudicationRoleV2.ADJUDICATOR_B), view=view
        )
        state.register_role_context(ctx_a)
        state.register_role_context(ctx_b)
        key = view.items[0].opaque_occurrence_token
        state.submit_independent_adjudication(context=ctx_a, decisions={key: "yes"})
        state.submit_independent_adjudication(context=ctx_b, decisions={key: "no"})
        with self.assertRaises(StructuralContractError):
            state.append_p2_join(p2_manifest=p2_manifest_for_result(ResolverResultV2.EXACT_MATCH))

    def test_disagreement_resolver_role_cannot_access_p2(self) -> None:
        state = closed_workflow()
        with self.assertRaises(StructuralContractError):
            AdjudicationFacadeV2.reject_raw_p2_object(
                p2_manifest_for_result(ResolverResultV2.EXACT_MATCH)
            )

    def test_p2_cannot_determine_adjudication_or_candidate_ids(self) -> None:
        join = closed_workflow().append_p2_join(
            p2_manifest=p2_manifest_for_result(ResolverResultV2.EXACT_MATCH)
        )
        payload = join.to_dict()
        self.assertNotIn("candidate_id", payload)
        self.assertNotIn("adjudication_id", payload)

    def test_issue_263_present_verbatim_unavailable_visible(self) -> None:
        view = build_adjudication_evidence_view(sample_p1_bundle_present_verbatim_unavailable())
        avail = view.items[0].condition_neutral_evidence_availability
        self.assertEqual(avail["source_presence"], SourcePresenceV2.PRESENT.value)
        self.assertEqual(
            avail["verbatim_evidence_availability"],
            VerbatimEvidenceAvailabilityV2.UNAVAILABLE.value,
        )

    def test_present_verbatim_unavailable_not_zero_targets(self) -> None:
        view = build_adjudication_evidence_view(sample_p1_bundle_present_verbatim_unavailable())
        self.assertEqual(len(view.items), 1)

    def test_view_construction_leaves_p1_bytes_unchanged(self) -> None:
        bundle = sample_p1_bundle()
        before = [seal.to_dict() for seal in bundle.evidence_seals]
        build_adjudication_evidence_view(bundle)
        after = [seal.to_dict() for seal in bundle.evidence_seals]
        self.assertEqual(before, after)

    def test_p2_execution_leaves_p1_bytes_unchanged(self) -> None:
        bundle = sample_p1_bundle()
        before = [seal.to_dict() for seal in bundle.evidence_seals]
        resolve_opaque(crush_resolver_input())
        after = [seal.to_dict() for seal in bundle.evidence_seals]
        self.assertEqual(before, after)

    def test_raw_p1_rejected_by_facade(self) -> None:
        with self.assertRaises(StructuralContractError):
            AdjudicationFacadeV2.reject_raw_p1_object(sample_p1_bundle().evidence_seals[0])

    def test_raw_p2_rejected_by_facade(self) -> None:
        with self.assertRaises(StructuralContractError):
            AdjudicationFacadeV2.reject_raw_p2_object(
                p2_manifest_for_result(ResolverResultV2.EXACT_MATCH)
            )

    def test_forged_role_context_rejected(self) -> None:
        view = build_adjudication_evidence_view(sample_p1_bundle())
        context = create_verified_role_context(
            role_manifest("adj-a", AdjudicationRoleV2.ADJUDICATOR_A), view=view
        )
        with self.assertRaises(StructuralContractError):
            AdjudicationFacadeV2.reject_forged_context(context, view=view)

    def test_stale_role_context_rejected(self) -> None:
        view = build_adjudication_evidence_view(sample_p1_bundle())
        context = create_verified_role_context(
            role_manifest("adj-a", AdjudicationRoleV2.ADJUDICATOR_A), view=view
        )
        other_view = build_adjudication_evidence_view(sample_p1_bundle(roster_set_id="other"))
        with self.assertRaises(StructuralContractError):
            AdjudicationFacadeV2.accept_view_for_role(other_view, context=context)

    def test_deterministic_repeat_serialization(self) -> None:
        first = build_adjudication_evidence_view(sample_p1_bundle()).canonical_bytes()
        second = build_adjudication_evidence_view(sample_p1_bundle()).canonical_bytes()
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(second))

    def test_join_cannot_mutate_sealed_closure(self) -> None:
        state = closed_workflow()
        closure_before = state.adjudication_closure_digest
        view_before = copy.deepcopy(state.view.to_dict())
        join = state.append_p2_join(p2_manifest=p2_manifest_for_result(ResolverResultV2.ERROR))
        self.assertEqual(state.adjudication_closure_digest, closure_before)
        self.assertEqual(state.view.to_dict(), view_before)
        self.assertIsNotNone(join.join_digest)

    def test_closed_allowlist_exact(self) -> None:
        self.assertEqual(
            AdjudicationEvidenceViewItemV1.ALLOWED,
            frozenset(
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
            ),
        )

    def test_metamorphic_membership_order_ids_stable(self) -> None:
        bundle = sample_p1_bundle()
        base_view = build_adjudication_evidence_view(bundle)
        tokens = [item.opaque_occurrence_token for item in base_view.items]
        for result in ResolverResultV2:
            _ = p2_manifest_for_result(result)
            view = build_adjudication_evidence_view(bundle)
            self.assertEqual([item.opaque_occurrence_token for item in view.items], tokens)
            self.assertEqual(view.content_digest(), base_view.content_digest())

    def test_arbitrary_mapping_rejected(self) -> None:
        with self.assertRaises(StructuralContractError):
            AdjudicationFacadeV2.reject_arbitrary_mapping({"foo": "bar"})

    def test_view_schema_constant(self) -> None:
        view = build_adjudication_evidence_view(sample_p1_bundle())
        self.assertEqual(view.schema_version, VIEW_SCHEMA)


class NaturalisticV2AdjudicationStaticDependencyTests(unittest.TestCase):
    FORBIDDEN_IMPORT_FRAGMENTS = (
        "eval_naturalistic.v2.resolver",
        "eval_naturalistic.v2.adapters.reduction",
        "eval_naturalistic.v2.adapters.registry",
        "queue",
        "pathlib",
        "os",
        "time",
    )

    def test_view_builder_has_no_resolver_dependency(self) -> None:
        source_path = (
            Path(__file__).resolve().parent.parent
            / "eval_naturalistic/v2/adjudication_view.py"
        )
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        joined = "\n".join(imports)
        for fragment in self.FORBIDDEN_IMPORT_FRAGMENTS:
            self.assertNotIn(fragment, joined, msg=f"forbidden import surface: {fragment}")
        self.assertNotIn("capability", joined)


if __name__ == "__main__":
    unittest.main()
