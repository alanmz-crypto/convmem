"""Hermetic G3 tests for naturalistic probe/leakage/scoring-key machinery."""

from __future__ import annotations

# Hermetic path bootstrapping precedes project imports; repeated setup is intentional.
# pylint: disable=wrong-import-position,duplicate-code

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.contract_validate import (
    validate_generation_integrity,
    validate_scoring_key_separation,
    validate_seal_immutability,
)
from eval_naturalistic.contracts import ProbeManifestV1, verify_artifact_digest
from eval_naturalistic.enums import (
    LeakageReviewDisposition,
    ProbeBuildOutcome,
    ProbeFamilyKind,
)
from eval_naturalistic.probe_construction import (
    build_sealed_probe_bundle,
    reject_post_freeze_probe_mutation,
    reject_probe_repair_after_outcomes,
    run_leakage_checklist,
    validate_probe_freeze,
    validate_scoring_key_integrity_binding,
)
from eval_naturalistic.probe_fixtures import (
    CONTINUATION_PROBE_TEXT,
    DIRECT_RECALL_PROBE_TEXT,
    LEAK_REVIEWER_ID,
    VALID_GROUND_TRUTH,
    build_valid_probe_bundle,
    make_default_probe_config,
    make_default_provenance,
    make_probe_draft,
    make_sealed_registry_and_census,
)


class ProbeConstructionHappyPathTests(unittest.TestCase):
    def test_valid_continuation_recovery_probe_seals(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        assert result.probe is not None
        assert result.scoring_key is not None
        assert result.leakage_review is not None
        assert result.key_content is not None
        self.assertEqual(result.outcome, ProbeBuildOutcome.SEALED)
        self.assertTrue(result.probe.header.sealed)
        self.assertEqual(
            result.probe.probe_family_kind,
            ProbeFamilyKind.CONTINUATION_RECOVERY,
        )

    def test_direct_recall_probe_where_allowed(self):
        registry, census = make_sealed_registry_and_census()
        target = registry.targets[0]
        draft = make_probe_draft(
            target=target,
            probe_text=DIRECT_RECALL_PROBE_TEXT,
            probe_family_kind=ProbeFamilyKind.DIRECT_RECALL,
        )
        result = build_sealed_probe_bundle(
            registry=registry,
            census=census,
            target=target,
            draft=draft,
            leakage_reviewer_id=LEAK_REVIEWER_ID,
            config=make_default_probe_config(),
        )
        self.assertTrue(result.ok, result.errors)
        assert result.probe is not None
        self.assertEqual(result.probe.probe_family_kind, ProbeFamilyKind.DIRECT_RECALL)


class ProbeRoleAndProvenanceTests(unittest.TestCase):
    def test_probe_author_equals_adjudicator_rejected(self):
        registry, census = make_sealed_registry_and_census()
        target = registry.targets[0]
        draft = make_probe_draft(target=target, probe_author_id="adj-a")
        result = build_sealed_probe_bundle(
            registry=registry,
            census=census,
            target=target,
            draft=draft,
            leakage_reviewer_id=LEAK_REVIEWER_ID,
            config=make_default_probe_config(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome, ProbeBuildOutcome.ROLE_OR_PROVENANCE_REJECTED)
        self.assertIsNone(result.probe)

    def test_missing_probe_author_provenance_rejected(self):
        registry, census = make_sealed_registry_and_census()
        target = registry.targets[0]
        provenance = make_default_provenance(target_id=target.target_id)
        provenance.access_recorded = False
        draft = make_probe_draft(target=target, provenance=provenance)
        result = build_sealed_probe_bundle(
            registry=registry,
            census=census,
            target=target,
            draft=draft,
            leakage_reviewer_id=LEAK_REVIEWER_ID,
            config=make_default_probe_config(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome, ProbeBuildOutcome.ROLE_OR_PROVENANCE_REJECTED)


class LeakageReviewTests(unittest.TestCase):
    def test_answer_explicit_in_probe_rejected(self):
        registry, census = make_sealed_registry_and_census()
        target = registry.targets[0]
        draft = make_probe_draft(
            target=target,
            probe_text=f"{CONTINUATION_PROBE_TEXT} Answer: {VALID_GROUND_TRUTH}",
        )
        result = build_sealed_probe_bundle(
            registry=registry,
            census=census,
            target=target,
            draft=draft,
            leakage_reviewer_id=LEAK_REVIEWER_ID,
            config=make_default_probe_config(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome, ProbeBuildOutcome.LEAKAGE_REJECTED)
        self.assertIsNone(result.probe)

    def test_close_answer_paraphrase_rejected(self):
        answer = "alpha beta gamma delta epsilon zeta"
        registry, census = make_sealed_registry_and_census()
        target = registry.targets[0]
        draft = make_probe_draft(
            target=target,
            probe_text="alpha beta gamma delta epsilon zeta workflow continuation",
            ground_truth=answer,
        )
        result = build_sealed_probe_bundle(
            registry=registry,
            census=census,
            target=target,
            draft=draft,
            leakage_reviewer_id=LEAK_REVIEWER_ID,
            config=make_default_probe_config(),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.outcome, ProbeBuildOutcome.LEAKAGE_REJECTED)

    def test_source_path_disclosed_rejected(self):
        checklist = run_leakage_checklist(
            "Continue work; see synthetic://transcript/ep-001 for context."
        )
        self.assertFalse(checklist.ok)

    def test_source_location_disclosed_rejected(self):
        checklist = run_leakage_checklist("Continue from line 42 in the prior session.")
        self.assertFalse(checklist.ok)

    def test_treatment_cue_rejected(self):
        checklist = run_leakage_checklist("Under C1, continue the workflow.")
        self.assertFalse(checklist.ok)

    def test_convmem_retrieval_cue_rejected(self):
        checklist = run_leakage_checklist("Use convmem retrieval rank to continue.")
        self.assertFalse(checklist.ok)

    def test_missing_leakage_signoff_blocks_authoritative_freeze(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        assert result.leakage_review is not None
        rejected = copy.deepcopy(result.leakage_review.to_dict())
        rejected["disposition"] = LeakageReviewDisposition.REJECTED.value
        from eval_naturalistic.contracts import LeakageReviewManifestV1

        bad_review = LeakageReviewManifestV1.from_dict(rejected)
        registry, census = make_sealed_registry_and_census()
        validation = validate_probe_freeze(
            registry=registry,
            census=census,
            probe=result.probe,  # type: ignore[arg-type]
            scoring_key=result.scoring_key,  # type: ignore[arg-type]
            leakage_review=bad_review,
            key_content=result.key_content,  # type: ignore[arg-type]
        )
        self.assertFalse(validation.ok)

    def test_failed_leakage_checklist_yields_no_authoritative_probe(self):
        registry, census = make_sealed_registry_and_census()
        target = registry.targets[0]
        draft = make_probe_draft(
            target=target,
            probe_text="Treatment arm C0 should guide your next action.",
        )
        result = build_sealed_probe_bundle(
            registry=registry,
            census=census,
            target=target,
            draft=draft,
            leakage_reviewer_id=LEAK_REVIEWER_ID,
            config=make_default_probe_config(),
        )
        self.assertFalse(result.ok)
        self.assertIsNone(result.probe)

    def test_leakage_review_seal_verifies_without_exception(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        assert result.leakage_review is not None
        review_dict = result.leakage_review.to_dict()
        self.assertTrue(verify_artifact_digest(review_dict))
        seal_check = validate_seal_immutability(
            result.leakage_review,
            label="LeakageReviewManifest",
        )
        self.assertTrue(seal_check.ok, seal_check.errors)
        self.assertNotIn("exception_record", review_dict)

    def test_leakage_review_seal_verifies_with_exception(self):
        registry, census = make_sealed_registry_and_census()
        target = registry.targets[0]
        draft = make_probe_draft(target=target)
        exception = "ordinary-task exception documented before freeze"
        result = build_sealed_probe_bundle(
            registry=registry,
            census=census,
            target=target,
            draft=draft,
            leakage_reviewer_id=LEAK_REVIEWER_ID,
            config=make_default_probe_config(),
            ordinary_task_exception=exception,
        )
        self.assertTrue(result.ok, result.errors)
        assert result.leakage_review is not None
        review_dict = result.leakage_review.to_dict()
        self.assertEqual(review_dict.get("exception_record"), exception)
        self.assertTrue(verify_artifact_digest(review_dict))
        seal_check = validate_seal_immutability(
            result.leakage_review,
            label="LeakageReviewManifest",
        )
        self.assertTrue(seal_check.ok, seal_check.errors)


class ScoringKeySeparationTests(unittest.TestCase):
    def test_agent_b_view_strips_scoring_key_contents(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        assert result.probe is not None
        public = result.probe.agent_b_view()
        self.assertNotIn("scoring_key_digest", public)
        self.assertNotIn("scoring_key_partition_identity", public)
        self.assertNotIn("ground_truth_value", public)
        separation = validate_scoring_key_separation(result.probe)
        self.assertTrue(separation.ok, separation.errors)

    def test_wrong_scoring_key_digest_binding_rejected(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        assert result.probe is not None
        assert result.scoring_key is not None
        assert result.key_content is not None
        bad_key = copy.deepcopy(result.scoring_key.to_dict())
        bad_key["key_content_digest"] = "0" * 64
        from eval_naturalistic.contracts import ScoringKeyV1

        wrong_key = ScoringKeyV1.from_dict(bad_key)
        binding = validate_scoring_key_integrity_binding(
            result.probe,
            wrong_key,
            result.key_content,
        )
        self.assertFalse(binding.ok)


class FreezeIntegrityTests(unittest.TestCase):
    def test_post_freeze_probe_mutation_rejected(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        assert result.probe is not None
        mutated = copy.deepcopy(result.probe.to_dict())
        mutated["prompt_content_digest"] = "f" * 64
        mutated["header"] = {
            **mutated["header"],
            "content_digest": result.probe.header.content_digest,
        }
        proposed = ProbeManifestV1.from_dict(mutated)
        rejection = reject_post_freeze_probe_mutation(result.probe, proposed)
        self.assertFalse(rejection.ok)

    def test_probe_repair_after_outcomes_rejected(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        assert result.probe is not None
        mutated = copy.deepcopy(result.probe.to_dict())
        mutated["prompt_content_digest"] = "a" * 64
        proposed = ProbeManifestV1.from_dict(mutated)
        repair = reject_probe_repair_after_outcomes(
            sealed_probe=result.probe,
            proposed_probe=proposed,
            outcomes_known=True,
        )
        self.assertFalse(repair.ok)

    def test_wrong_target_registry_parent_rejected(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        registry, census = make_sealed_registry_and_census()
        assert result.probe is not None
        bad_probe = copy.deepcopy(result.probe.to_dict())
        bad_probe["target_registry_digest"] = "deadbeef" * 8
        proposed = ProbeManifestV1.from_dict(bad_probe)
        from eval_naturalistic.probe_construction import validate_registry_sample_parent_binding

        binding = validate_registry_sample_parent_binding(
            registry=registry,
            census=census,
            probe=proposed,
        )
        self.assertFalse(binding.ok)

    def test_obsolete_parent_generation_rejected(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        assert result.probe is not None
        stale = validate_generation_integrity(
            result.probe,
            expected_parent_digest="0" * 64,
            label="ProbeManifest",
        )
        self.assertFalse(stale.ok)


class NoDownstreamExecutionProofTests(unittest.TestCase):
    def test_no_agent_b_or_trial_modules_imported(self):
        import eval_naturalistic.probe_construction as module

        source = Path(module.__file__).read_text(encoding="utf-8")
        forbidden = (
            "AgentBTrialRecord",
            "run_agent_b",
            "execute_trial",
            "C0C1EnvironmentManifest",
            "StudyAnalysisV1",
            "paired_stats",
        )
        for token in forbidden:
            self.assertNotIn(token, source)

    def test_sealed_bundle_passes_freeze_validation(self):
        result = build_valid_probe_bundle()
        self.assertTrue(result.ok, result.errors)
        registry, census = make_sealed_registry_and_census()
        validation = validate_probe_freeze(
            registry=registry,
            census=census,
            probe=result.probe,  # type: ignore[arg-type]
            scoring_key=result.scoring_key,  # type: ignore[arg-type]
            leakage_review=result.leakage_review,  # type: ignore[arg-type]
            key_content=result.key_content,  # type: ignore[arg-type]
        )
        self.assertTrue(validation.ok, validation.errors)


if __name__ == "__main__":
    unittest.main()
