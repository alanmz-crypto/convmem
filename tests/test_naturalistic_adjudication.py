"""Hermetic G2 tests for naturalistic adjudication and target-registry machinery."""

from __future__ import annotations

# Hermetic path bootstrapping precedes project imports; repeated setup is intentional.
# pylint: disable=wrong-import-position,duplicate-code
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.adjudication import (
    CandidateAdjudicationBundleV1,
    build_evidence_adjudication_view,
    build_sealed_target_registry,
    reject_capture_driven_registry_mutation,
    validate_registry_build,
    validate_registry_membership_immutable,
)
from eval_naturalistic.adjudication_fixtures import (
    make_agreeing_eligible_candidate,
    make_default_workflow,
    make_disagreeing_candidate_with_resolution,
    make_disagreeing_candidate_without_resolution,
    make_synthetic_adjudication_chain,
)
from eval_naturalistic.contract_validate import (
    validate_artifact_chain,
    validate_capture_independent_registry,
    validate_generation_integrity,
    validate_parent_binding,
)
from eval_naturalistic.contracts import (
    AdjudicationRecordV1,
    TargetRecordV1,
    TargetRegistryV1,
    TargetSpanBindingV1,
    seal_artifact_dict,
)
from eval_naturalistic.enums import (
    EligibilityDisposition,
    EpisodeRegistryStatus,
    RegistryBuildOutcome,
)
from eval_naturalistic.fixtures import make_synthetic_capture, make_synthetic_registry


class AdjudicationWorkflowTests(unittest.TestCase):
    def test_two_adjudicators_agree_on_eligible_target(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        candidate = make_agreeing_eligible_candidate()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[candidate],
            workflow=workflow,
        )
        self.assertTrue(result.ok, result.errors)
        self.assertIsNotNone(result.registry)
        assert result.registry is not None
        self.assertEqual(result.episode_status, EpisodeRegistryStatus.TARGETS_PRESENT)
        self.assertEqual(len(result.registry.targets), 1)
        self.assertTrue(result.registry.header.sealed)
        validation = validate_registry_build(
            frame=frame,
            episode=episode,
            evidence=evidence,
            registry=result.registry,
        )
        self.assertTrue(validation.ok, validation.errors)
        chain = validate_artifact_chain(
            frame=frame,
            episode=episode,
            evidence=evidence,
            registry=result.registry,
        )
        self.assertTrue(chain.ok, chain.errors)

    def test_zero_eligible_targets_with_agreeing_ineligible_candidates(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        candidate = CandidateAdjudicationBundleV1(
            target_id="tgt-ineligible-001",
            span_bindings=[TargetSpanBindingV1(source_id="src-001", span_start=0, span_end=10)],
            adjudication_records=[
                AdjudicationRecordV1(
                    adjudicator_id="adj-a",
                    disposition=EligibilityDisposition.INELIGIBLE,
                    rationale="no semantic support",
                ),
                AdjudicationRecordV1(
                    adjudicator_id="adj-b",
                    disposition=EligibilityDisposition.INELIGIBLE,
                    rationale="no semantic support",
                ),
            ],
        )
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[candidate],
            workflow=workflow,
        )
        self.assertTrue(result.ok, result.errors)
        assert result.registry is not None
        self.assertEqual(result.episode_status, EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS)
        self.assertEqual(
            result.registry.episode_entries[0].registry_status,
            EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS,
        )

    def test_zero_eligible_targets_with_empty_candidate_census(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[],
            workflow=workflow,
        )
        self.assertTrue(result.ok, result.errors)
        assert result.registry is not None
        self.assertEqual(result.episode_status, EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS)

    def test_adjudicator_disagreement_resolved_by_third_adjudicator(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        candidate = make_disagreeing_candidate_with_resolution()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[candidate],
            workflow=workflow,
        )
        self.assertTrue(result.ok, result.errors)
        assert result.registry is not None
        self.assertEqual(result.episode_status, EpisodeRegistryStatus.TARGETS_PRESENT)
        self.assertEqual(result.registry.targets[0].resolution_identity, "third-adj-resolver-001")

    def test_adjudicator_disagreement_without_resolution_is_ambiguous(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        candidate = make_disagreeing_candidate_without_resolution()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[candidate],
            workflow=workflow,
        )
        self.assertTrue(result.ok, result.errors)
        assert result.registry is not None
        self.assertEqual(result.outcome, RegistryBuildOutcome.ADJUDICATION_AMBIGUOUS)
        self.assertEqual(result.episode_status, EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS)
        self.assertEqual(result.registry.targets, [])

    def test_incomplete_evidence_fails_closed_to_evidence_incomplete(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain(complete_evidence=False)
        candidate = make_agreeing_eligible_candidate()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[candidate],
            workflow=workflow,
        )
        self.assertTrue(result.ok, result.errors)
        assert result.registry is not None
        self.assertEqual(result.outcome, RegistryBuildOutcome.EVIDENCE_INCOMPLETE)
        self.assertEqual(result.episode_status, EpisodeRegistryStatus.EVIDENCE_INCOMPLETE)
        self.assertEqual(result.registry.targets, [])

    def test_missing_adjudicator_provenance_rejected(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        candidate = CandidateAdjudicationBundleV1(
            target_id="tgt-missing-prov",
            span_bindings=[TargetSpanBindingV1(source_id="src-001", span_start=0, span_end=5)],
            adjudication_records=[
                AdjudicationRecordV1(
                    adjudicator_id="adj-a",
                    disposition=EligibilityDisposition.ELIGIBLE,
                    rationale="only one adjudicator",
                ),
            ],
        )
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[candidate],
            workflow=workflow,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome, RegistryBuildOutcome.PROTOCOL_INVALID)
        self.assertTrue(any("missing adjudicator provenance" in err for err in result.errors))

    def test_prohibited_role_collision_rejected(self):
        frame, episode, evidence, _workflow = make_synthetic_adjudication_chain()
        workflow = make_default_workflow(prohibited_probe_author_ids=frozenset({"adj-a"}))
        candidate = make_agreeing_eligible_candidate()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[candidate],
            workflow=workflow,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome, RegistryBuildOutcome.PROTOCOL_INVALID)
        self.assertTrue(any("prohibited role collision" in err for err in result.errors))

    def test_duplicate_target_identity_rejected(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        candidate = make_agreeing_eligible_candidate()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[candidate, candidate],
            workflow=workflow,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("duplicate target_id" in err for err in result.errors))

    def test_wrong_parent_digest_rejected(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        bad_evidence = copy.deepcopy(evidence)
        bad_evidence.episode_record_digest = "0" * 64
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=bad_evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("digest mismatch" in err for err in result.errors))


class RegistrySealTests(unittest.TestCase):
    def test_registry_mutation_after_seal_rejected(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        assert result.registry is not None
        mutated_body = copy.deepcopy(result.registry.to_dict())
        mutated_body["targets"].append(
            TargetRecordV1(
                target_id="tgt-injected",
                episode_id=episode.episode_id,
                span_bindings=[TargetSpanBindingV1(source_id="src-001", span_start=99, span_end=100)],
                eligibility_disposition=EligibilityDisposition.ELIGIBLE,
                ground_truth_partition_digest=None,
                provenance_requirement=None,
                admissibility_rationale=None,
                unitization_rationale=None,
                duplicate_of_target_id=None,
                parent_target_id=None,
                ambiguity_state=None,
                secondary_strata=[],
                adjudication_records=[],
                resolution_identity=None,
                adjudicator_ids=[],
            ).to_dict()
        )
        mutated_body = seal_artifact_dict(mutated_body, seal_time="2026-08-30T03:00:00Z")
        proposed = TargetRegistryV1.from_dict(mutated_body)
        immutability = validate_registry_membership_immutable(result.registry, proposed)
        self.assertFalse(immutability.ok)
        capture_reject = reject_capture_driven_registry_mutation(result.registry, proposed)
        self.assertFalse(capture_reject.ok)
        self.assertTrue(any("injection rejected" in err for err in capture_reject.errors))


class CaptureIndependenceAdversarialTests(unittest.TestCase):
    def test_capture_cannot_inject_registry_target(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        build = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        assert build.registry is not None
        registry = build.registry
        capture = make_synthetic_capture(registry=registry)

        injected_body = copy.deepcopy(registry.to_dict())
        injected_body["targets"].append(
            TargetRecordV1(
                target_id="tgt-capture-injected",
                episode_id=episode.episode_id,
                span_bindings=[TargetSpanBindingV1(source_id="src-001", span_start=50, span_end=60)],
                eligibility_disposition=EligibilityDisposition.ELIGIBLE,
                ground_truth_partition_digest=None,
                provenance_requirement=None,
                admissibility_rationale=None,
                unitization_rationale=None,
                duplicate_of_target_id=None,
                parent_target_id=None,
                ambiguity_state=None,
                secondary_strata=[],
                adjudication_records=[],
                resolution_identity=None,
                adjudicator_ids=[],
            ).to_dict()
        )
        injected_body["episode_entries"][0]["target_ids"].append("tgt-capture-injected")
        injected_body = seal_artifact_dict(injected_body, seal_time="2026-08-30T03:00:00Z")
        injected_registry = TargetRegistryV1.from_dict(injected_body)

        result = validate_capture_independent_registry(
            registry,
            capture,
            proposed_registry=injected_registry,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("injection rejected" in err for err in result.errors))

    def test_capture_cannot_remove_eligible_target_from_registry(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        build = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        assert build.registry is not None
        registry = build.registry
        capture = make_synthetic_capture(registry=registry)

        removed_body = copy.deepcopy(registry.to_dict())
        removed_body["targets"] = []
        removed_body["episode_entries"][0]["target_ids"] = []
        removed_body = seal_artifact_dict(removed_body, seal_time="2026-08-30T03:00:00Z")
        removed_registry = TargetRegistryV1.from_dict(removed_body)

        result = validate_capture_independent_registry(
            registry,
            capture,
            proposed_registry=removed_registry,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("removal rejected" in err for err in result.errors))

    def test_capture_cannot_substitute_target_identity(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        build = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        assert build.registry is not None
        registry = build.registry
        capture = make_synthetic_capture(registry=registry)

        substituted_body = copy.deepcopy(registry.to_dict())
        substituted_body["targets"][0]["target_id"] = "tgt-substituted"
        substituted_body["episode_entries"][0]["target_ids"] = ["tgt-substituted"]
        substituted_body = seal_artifact_dict(substituted_body, seal_time="2026-08-30T03:00:00Z")
        substituted_registry = TargetRegistryV1.from_dict(substituted_body)

        result = validate_capture_independent_registry(
            registry,
            capture,
            proposed_registry=substituted_registry,
        )
        self.assertFalse(result.ok)

    def test_changing_capture_state_alone_does_not_mutate_registry(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        build = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        assert build.registry is not None
        registry = build.registry
        before = {target.target_id for target in registry.targets}
        capture_absent = make_synthetic_capture(registry=registry)
        capture_present = make_synthetic_capture(registry=registry)
        capture_present.target_states[0].capture_state = capture_present.target_states[0].capture_state
        result = validate_capture_independent_registry(registry, capture_absent)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(before, {target.target_id for target in registry.targets})


class EvidenceViewTests(unittest.TestCase):
    def test_evidence_view_excludes_capture_material(self):
        _frame, _episode, evidence, _workflow = make_synthetic_adjudication_chain()
        view = build_evidence_adjudication_view(evidence)
        self.assertIn("sources", view)
        self.assertNotIn("target_states", view)
        self.assertNotIn("capture_state", view)
        self.assertEqual(view["episode_id"], evidence.episode_id)


class GenerationIntegrityTests(unittest.TestCase):
    def test_wrong_parent_generation_rejected(self):
        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        build = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        assert build.registry is not None
        bad = copy.deepcopy(build.registry)
        bad.header.parent_digest = "f" * 64
        result = validate_generation_integrity(
            bad,
            expected_parent_digest=evidence.header.content_digest or "",
            label="TargetRegistry",
        )
        self.assertFalse(result.ok)

    def test_obsolete_evidence_parent_rejected(self):
        _frame, _episode, evidence, _workflow = make_synthetic_adjudication_chain()
        registry = make_synthetic_registry(evidence=evidence)
        parent = validate_parent_binding(
            registry,
            expected_parent_id="nps1_evidence_deadbeefdead",
            expected_parent_digest="0" * 64,
            label="TargetRegistry",
        )
        self.assertFalse(parent.ok)


class TerminalStateDistinctionTests(unittest.TestCase):
    def test_evidence_incomplete_differs_from_zero_and_ambiguous(self):
        frame, episode, evidence_complete, workflow = make_synthetic_adjudication_chain()
        evidence_incomplete, = (make_synthetic_adjudication_chain(complete_evidence=False)[2],)

        zero = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence_complete,
            candidates=[],
            workflow=workflow,
        )
        incomplete = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence_incomplete,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        ambiguous = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence_complete,
            candidates=[make_disagreeing_candidate_without_resolution()],
            workflow=workflow,
        )
        statuses = {
            zero.episode_status,
            incomplete.episode_status,
            ambiguous.episode_status,
        }
        self.assertEqual(len(statuses), 3)
        self.assertIn(EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS, statuses)
        self.assertIn(EpisodeRegistryStatus.EVIDENCE_INCOMPLETE, statuses)
        self.assertIn(EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS, statuses)



class G5CAdjudicationTests(unittest.TestCase):
    def test_episode_opportunity_identity_bound_to_registry(self):
        from eval_naturalistic.adjudication import (
            assign_episode_opportunity_identity,
            build_sealed_target_registry,
        )
        from eval_naturalistic.adjudication_fixtures import (
            make_agreeing_eligible_candidate,
            make_default_workflow,
            make_synthetic_adjudication_chain,
        )

        frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
        result = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        self.assertTrue(result.ok)
        assert result.registry is not None
        identity = assign_episode_opportunity_identity(
            registry=result.registry,
            episode_id=episode.episode_id,
        )
        self.assertEqual(identity.registry_digest, result.registry.header.content_digest)

    def test_registry_build_rejects_arm_context(self):
        from eval_naturalistic.adjudication import validate_registry_build_context_arm_blind

        check = validate_registry_build_context_arm_blind(condition="c1")
        self.assertFalse(check.ok)

if __name__ == "__main__":
    unittest.main()
