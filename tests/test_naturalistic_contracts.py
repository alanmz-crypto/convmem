"""Hermetic G1 tests for naturalistic product-value methodology substrate."""

from __future__ import annotations

# Hermetic path bootstrapping precedes project imports; repeated setup is intentional.
# pylint: disable=wrong-import-position,duplicate-code
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.adjudication import build_sealed_target_registry
from eval_naturalistic.adjudication_fixtures import (
    make_agreeing_eligible_candidate,
    make_default_workflow,
)
from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.contract_validate import (
    validate_artifact_chain,
    validate_capture_independent_registry,
    validate_generation_integrity,
    validate_parent_binding,
    validate_role_collision,
    validate_scoring_key_separation,
    validate_seal_immutability,
    validate_terminal_state_distinction,
)
from eval_naturalistic.contracts import (
    EpisodeFrameV1,
    EpisodeOutcomeV1,
    EpisodeRecordV1,
    RawEvidenceManifestV1,
    StudyAnalysisV1,
    TargetRecordV1,
    TargetRegistryV1,
    TargetSpanBindingV1,
    TrialIdentityV1,
    artifact_content_digest,
    seal_artifact_dict,
    verify_artifact_digest,
)
from eval_naturalistic.digest import artifact_content_digest as digest_fn
from eval_naturalistic.enums import (
    CaptureDiagnosticState,
    EligibilityDisposition,
    EpisodeRegistryStatus,
    ReliabilityState,
    StudyTerminalDisposition,
    TrialCondition,
    TrialTerminalDisposition,
)
from eval_naturalistic.fixtures import (
    make_synthetic_capture,
    make_synthetic_census,
    make_synthetic_episode,
    make_synthetic_evidence,
    make_synthetic_frame,
    make_synthetic_probe,
    make_synthetic_registry,
    make_synthetic_scoring_key,
)

ARTIFACT_ROUND_TRIP_CASES = [
    ("EpisodeFrameV1", EpisodeFrameV1, make_synthetic_frame),
    ("EpisodeRecordV1", EpisodeRecordV1, lambda: make_synthetic_episode(frame=make_synthetic_frame())),
    (
        "RawEvidenceManifestV1",
        RawEvidenceManifestV1,
        lambda: make_synthetic_evidence(episode=make_synthetic_episode(frame=make_synthetic_frame())),
    ),
    (
        "TargetRegistryV1",
        TargetRegistryV1,
        lambda: make_synthetic_registry(
            evidence=make_synthetic_evidence(
                episode=make_synthetic_episode(frame=make_synthetic_frame())
            )
        ),
    ),
]


class SchemaRoundTripTests(unittest.TestCase):
    def test_all_primary_artifacts_round_trip_and_digest(self):
        frame = make_synthetic_frame()
        episode = make_synthetic_episode(frame=frame)
        evidence = make_synthetic_evidence(episode=episode)
        registry = make_synthetic_registry(evidence=evidence)
        census = make_synthetic_census(registry=registry)
        probe = make_synthetic_probe(registry=registry, census=census)
        scoring_key = make_synthetic_scoring_key(probe=probe)
        capture = make_synthetic_capture(registry=registry)

        for label, obj in (
            ("frame", frame),
            ("episode", episode),
            ("evidence", evidence),
            ("registry", registry),
            ("census", census),
            ("probe", probe),
            ("scoring_key", scoring_key),
            ("capture", capture),
        ):
            with self.subTest(artifact=label):
                raw = obj.to_dict()
                reloaded = type(obj).from_dict(raw)
                self.assertEqual(reloaded.to_dict(), raw)
                self.assertTrue(verify_artifact_digest(raw))
                self.assertEqual(
                    raw["header"]["content_digest"],
                    artifact_content_digest(raw),
                )

    def test_trial_outcome_analysis_round_trip(self):
        frame = make_synthetic_frame()
        header = frame.header
        trial = TrialIdentityV1.from_dict(
            {
                "header": header.to_dict(),
                "trial_id": "trial-001",
                "session_identity": "session-fresh-001",
                "condition": TrialCondition.C1.value,
                "environment_manifest_id": "env-manifest-001",
                "probe_id": "probe-001",
                "raw_trace_identity": "trace-001",
                "terminal_disposition": TrialTerminalDisposition.COMPLETE.value,
            }
        )
        outcome = EpisodeOutcomeV1.from_dict(
            {
                "header": header.to_dict(),
                "episode_id": "ep-001",
                "registry_status": EpisodeRegistryStatus.TARGETS_PRESENT.value,
                "conditional_effect": 0.12,
                "reliability_state": ReliabilityState.RELIABILITY_ACCEPTABLE.value,
                "opportunity_component": 1.0,
            }
        )
        analysis = StudyAnalysisV1.from_dict(
            {
                "header": header.to_dict(),
                "terminal_disposition": StudyTerminalDisposition.COMPLETE_POSITIVE.value,
                "opportunity_prevalence": 0.5,
                "conditional_episode_effect": 0.1,
                "reliability_state": ReliabilityState.RELIABILITY_ACCEPTABLE.value,
                "sparse_state": ReliabilityState.RELIABILITY_NOT_APPLICABLE.value,
            }
        )
        for obj in (trial, outcome, analysis):
            raw = obj.to_dict()
            reloaded = type(obj).from_dict(raw)
            self.assertEqual(reloaded.to_dict(), raw)

    def test_unknown_property_rejected(self):
        frame = make_synthetic_frame().to_dict()
        frame["bogus"] = True
        with self.assertRaises(StructuralContractError):
            EpisodeFrameV1.from_dict(frame)


class ParentBindingTests(unittest.TestCase):
    def setUp(self):
        self.frame = make_synthetic_frame()
        self.episode = make_synthetic_episode(frame=self.frame)
        self.evidence = make_synthetic_evidence(episode=self.episode)
        self.registry = make_synthetic_registry(evidence=self.evidence)

    def test_valid_chain_passes(self):
        result = validate_artifact_chain(
            frame=self.frame,
            episode=self.episode,
            evidence=self.evidence,
            registry=self.registry,
            census=make_synthetic_census(registry=self.registry),
            probe=make_synthetic_probe(registry=self.registry),
        )
        self.assertTrue(result.ok, result.errors)

    def test_wrong_parent_id_rejected(self):
        bad = copy.deepcopy(self.episode)
        bad.frame_artifact_id = "nps1_frame_deadbeefdeadbeef"
        result = validate_artifact_chain(
            frame=self.frame,
            episode=bad,
            evidence=self.evidence,
            registry=self.registry,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("frame_artifact_id mismatch" in err for err in result.errors))

    def test_wrong_parent_digest_rejected(self):
        bad = copy.deepcopy(self.evidence)
        bad.episode_record_digest = "0" * 64
        result = validate_artifact_chain(
            frame=self.frame,
            episode=self.episode,
            evidence=bad,
            registry=self.registry,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("episode_record_digest mismatch" in err for err in result.errors))

    def test_missing_parent_binding_rejected(self):
        result = validate_parent_binding(
            self.episode,
            expected_parent_id="missing",
            expected_parent_digest="0" * 64,
            label="EpisodeRecord",
        )
        self.assertFalse(result.ok)


class SealImmutabilityTests(unittest.TestCase):
    def test_post_seal_mutation_changes_digest(self):
        frame = make_synthetic_frame()
        original_digest = frame.header.content_digest
        mutated = copy.deepcopy(frame.to_dict())
        mutated["study_id"] = "study-mutated"
        self.assertNotEqual(digest_fn(mutated), original_digest)
        result = validate_seal_immutability(
            frame,
            label="EpisodeFrame",
            mutated_body=mutated,
        )
        self.assertTrue(result.ok, result.errors)

    def test_sealed_registry_required_for_census(self):
        registry = make_synthetic_registry(
            evidence=make_synthetic_evidence(
                episode=make_synthetic_episode(frame=make_synthetic_frame())
            )
        )
        unsealed = copy.deepcopy(registry.to_dict())
        unsealed["header"]["sealed"] = False
        unsealed["header"]["seal_time"] = None
        bad_registry = TargetRegistryV1.from_dict(unsealed)
        census = make_synthetic_census(registry=registry)
        result = validate_artifact_chain(
            frame=make_synthetic_frame(),
            episode=make_synthetic_episode(frame=make_synthetic_frame()),
            evidence=make_synthetic_evidence(
                episode=make_synthetic_episode(frame=make_synthetic_frame())
            ),
            registry=bad_registry,
            census=census,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("must be sealed" in err for err in result.errors))


class ZeroTargetDistinctionTests(unittest.TestCase):
    def test_zero_target_differs_from_evidence_incomplete_and_ambiguous(self):
        episode = make_synthetic_episode(frame=make_synthetic_frame())
        evidence = make_synthetic_evidence(episode=episode)
        zero = make_synthetic_registry(evidence=evidence, zero_targets=True)
        incomplete = make_synthetic_registry(evidence=evidence, evidence_incomplete=True)
        ambiguous = make_synthetic_registry(evidence=evidence, ambiguous=True)

        statuses = {
            zero.episode_entries[0].registry_status,
            incomplete.episode_entries[0].registry_status,
            ambiguous.episode_entries[0].registry_status,
        }
        self.assertEqual(len(statuses), 3)
        self.assertIn(EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS, statuses)
        self.assertIn(EpisodeRegistryStatus.EVIDENCE_INCOMPLETE, statuses)
        self.assertIn(EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS, statuses)


class CaptureIndependenceTests(unittest.TestCase):
    def test_changing_capture_state_does_not_remove_eligible_target(self):
        frame = make_synthetic_frame()
        episode = make_synthetic_episode(frame=frame)
        evidence = make_synthetic_evidence(episode=episode)
        workflow = make_default_workflow()
        build = build_sealed_target_registry(
            frame=frame,
            episode=episode,
            evidence=evidence,
            candidates=[make_agreeing_eligible_candidate()],
            workflow=workflow,
        )
        assert build.registry is not None
        registry = build.registry
        absent = make_synthetic_capture(registry=registry)
        captured = make_synthetic_capture(
            registry=registry,
            capture_state=CaptureDiagnosticState.CAPTURED,
        )
        self.assertEqual(len(registry.targets), 1)
        result_absent = validate_capture_independent_registry(registry, absent)
        result_captured = validate_capture_independent_registry(registry, captured)
        self.assertTrue(result_absent.ok, result_absent.errors)
        self.assertTrue(result_captured.ok, result_captured.errors)
        self.assertEqual(
            {t.target_id for t in registry.targets},
            {t.target_id for t in registry.targets},
        )

    def test_capture_driven_injection_rejected(self):
        frame = make_synthetic_frame()
        episode = make_synthetic_episode(frame=frame)
        evidence = make_synthetic_evidence(episode=episode)
        workflow = make_default_workflow()
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
                target_id="tgt-injected-adversarial",
                episode_id=episode.episode_id,
                span_bindings=[TargetSpanBindingV1(source_id="src-001", span_start=1, span_end=2)],
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
        injected_body = seal_artifact_dict(injected_body, seal_time="2026-08-30T04:00:00Z")
        injected_registry = TargetRegistryV1.from_dict(injected_body)
        result = validate_capture_independent_registry(
            registry,
            capture,
            proposed_registry=injected_registry,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("injection rejected" in err for err in result.errors))


class RoleCollisionTests(unittest.TestCase):
    def test_probe_author_equals_adjudicator_rejected(self):
        registry = make_synthetic_registry(
            evidence=make_synthetic_evidence(
                episode=make_synthetic_episode(frame=make_synthetic_frame())
            )
        )
        probe = make_synthetic_probe(registry=registry, probe_author_id="adj-a")
        result = validate_role_collision(
            probe,
            adjudicator_ids_for_target={"adj-a", "adj-b"},
        )
        self.assertFalse(result.ok)

    def test_valid_probe_passes_collision_check(self):
        registry = make_synthetic_registry(
            evidence=make_synthetic_evidence(
                episode=make_synthetic_episode(frame=make_synthetic_frame())
            )
        )
        probe = make_synthetic_probe(registry=registry)
        result = validate_role_collision(
            probe,
            adjudicator_ids_for_target={"adj-a", "adj-b"},
        )
        self.assertTrue(result.ok, result.errors)


class ScoringKeySeparationTests(unittest.TestCase):
    def test_agent_b_view_binds_digest_without_key_content(self):
        registry = make_synthetic_registry(
            evidence=make_synthetic_evidence(
                episode=make_synthetic_episode(frame=make_synthetic_frame())
            )
        )
        probe = make_synthetic_probe(registry=registry)
        public = probe.agent_b_view()
        self.assertNotIn("scoring_key_digest", public)
        self.assertIn("scoring_key_integrity_digest", public)
        self.assertNotIn("key_content", public)
        result = validate_scoring_key_separation(probe)
        self.assertTrue(result.ok, result.errors)


class TerminalStateDistinctionTests(unittest.TestCase):
    def test_blocked_non_estimable_not_null_equivalent(self):
        result = validate_terminal_state_distinction(
            StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE,
            StudyTerminalDisposition.COMPLETE_NULL_EQUIVALENT,
        )
        self.assertTrue(result.ok, result.errors)
        self.assertNotEqual(
            StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE.value,
            StudyTerminalDisposition.COMPLETE_NULL_EQUIVALENT.value,
        )


class SparseNullCollapseTests(unittest.TestCase):
    def test_sparse_and_null_reliability_states_distinct(self):
        sparse = ReliabilityState.RELIABILITY_SPARSE
        non_estimable = ReliabilityState.RELIABILITY_NON_ESTIMABLE
        self.assertNotEqual(sparse, non_estimable)
        self.assertNotEqual(sparse.value, StudyTerminalDisposition.COMPLETE_NULL_EQUIVALENT.value)


class GenerationIntegrityTests(unittest.TestCase):
    def test_obsolete_parent_digest_rejected(self):
        episode = make_synthetic_episode(frame=make_synthetic_frame())
        result = validate_generation_integrity(
            episode,
            expected_parent_digest="f" * 64,
            label="EpisodeRecord",
        )
        self.assertFalse(result.ok)


class AdversarialNegativeTests(unittest.TestCase):
    def test_unsealed_registry_parent_for_probe_fails(self):
        frame = make_synthetic_frame()
        episode = make_synthetic_episode(frame=frame)
        evidence = make_synthetic_evidence(episode=episode)
        registry_body = make_synthetic_registry(evidence=evidence).to_dict()
        registry_body["header"]["sealed"] = False
        registry_body["header"]["content_digest"] = artifact_content_digest(registry_body)
        bad_registry = TargetRegistryV1.from_dict(registry_body)
        probe = make_synthetic_probe(registry=make_synthetic_registry(evidence=evidence))
        result = validate_artifact_chain(
            frame=frame,
            episode=episode,
            evidence=evidence,
            registry=bad_registry,
            probe=probe,
        )
        self.assertFalse(result.ok)

    def test_missing_episode_in_registry_fails(self):
        frame = make_synthetic_frame()
        episode = make_synthetic_episode(frame=frame)
        evidence = make_synthetic_evidence(episode=episode)
        registry = make_synthetic_registry(evidence=evidence)
        registry_body = registry.to_dict()
        registry_body["episode_entries"] = []
        registry_body = seal_artifact_dict(registry_body, seal_time="2026-08-30T02:00:00Z")
        empty_registry = TargetRegistryV1.from_dict(registry_body)
        result = validate_artifact_chain(
            frame=frame,
            episode=episode,
            evidence=evidence,
            registry=empty_registry,
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("missing episode entry" in err for err in result.errors))

    def test_wrong_parent_generation_digest_fails(self):
        census = make_synthetic_census(
            registry=make_synthetic_registry(
                evidence=make_synthetic_evidence(
                    episode=make_synthetic_episode(frame=make_synthetic_frame())
                )
            )
        )
        bad = copy.deepcopy(census)
        bad.target_registry_digest = "0" * 64
        result = validate_artifact_chain(
            frame=make_synthetic_frame(),
            episode=make_synthetic_episode(frame=make_synthetic_frame()),
            evidence=make_synthetic_evidence(
                episode=make_synthetic_episode(frame=make_synthetic_frame())
            ),
            registry=make_synthetic_registry(
                evidence=make_synthetic_evidence(
                    episode=make_synthetic_episode(frame=make_synthetic_frame())
                )
            ),
            census=bad,
        )
        self.assertFalse(result.ok)



class ProspectiveManifestG5CTests(unittest.TestCase):
    def test_pending_manifest_requires_all_eight_slots(self):
        from eval_naturalistic.contracts import (
            make_pending_prospective_manifest,
            validate_prospective_manifest_structural,
        )
        from eval_naturalistic.fixtures import make_synthetic_frame

        manifest = make_pending_prospective_manifest(frame=make_synthetic_frame())
        body = manifest.to_dict()
        check = validate_prospective_manifest_structural(body, require_logged_freeze=False)
        self.assertTrue(check.ok, check.errors)
        self.assertEqual(len(body["information_slots"]), 8)

    def test_incomplete_manifest_rejected(self):
        from eval_naturalistic.contracts import (
            make_pending_prospective_manifest,
            validate_prospective_manifest_structural,
        )
        from eval_naturalistic.fixtures import make_synthetic_frame

        body = make_pending_prospective_manifest(frame=make_synthetic_frame()).to_dict()
        body["information_slots"] = body["information_slots"][:2]
        check = validate_prospective_manifest_structural(body, require_logged_freeze=False)
        self.assertFalse(check.ok)

    def test_stage_ledger_derives_group_summaries(self):
        from eval_naturalistic.contracts import StageBoundaryLedgerEntryV1, StageBoundaryLedgerV1
        from eval_naturalistic.enums import StudyStageId

        entries = [
            StageBoundaryLedgerEntryV1(
                stage_id=stage,
                input_artifact_digest="0" * 64,
                required_predicates=[],
                validator_identity="test",
                validator_version="1",
                output_artifact_digest=None,
                guarantees_exported=["g"],
                next_stage_assumptions=["a"],
                failure_reasons=[],
                passed=True,
            )
            for stage in StudyStageId
        ]
        ledger = StageBoundaryLedgerV1(entries=entries)
        summaries = ledger.derived_group_summaries()
        self.assertTrue(all(summaries.values()))

    def test_structural_content_invalid_fails_closed(self):
        from eval_naturalistic.contracts import validate_prospective_manifest_structural

        body = {
            "header": "not-a-dict",
            "study_id": "study-synthetic-001",
            "frame_artifact_id": "frame-001",
            "frame_digest": "d" + "0" * 63,
            "information_slots": [],
            "opportunity_authority_rule": "policy-opportunity-authority-v1",
            "failure_reason_taxonomy": ["reason-protocol-invalid"],
            "missing_outcome_bounds_policy": "policy-missing-outcome-bounds-v1",
            "orthogonal_state_precedence": ["protocol_invalid"],
            "paired_replay_policy": "policy-paired-replay-v1",
            "scorer_integrity_policy": "policy-scorer-integrity-v1",
            "scorer_reliability_policy": "policy-scorer-reliability-v1",
        }
        check = validate_prospective_manifest_structural(body)
        self.assertFalse(check.ok)
        self.assertTrue(check.errors)
        self.assertIn("header", check.errors[0])

    def test_non_boolean_passed_raises_structural_error(self):
        from eval_naturalistic.contracts import StageBoundaryPredicateResultV1

        with self.assertRaises(StructuralContractError):
            StageBoundaryPredicateResultV1.from_dict(
                {"predicate_name": "x", "passed": "notbool"}
            )

    def test_raw_serialization_decode_not_contracts_layer(self):
        """Canonical JSON byte decode is upstream; contracts validators take decoded dict bodies."""

        import inspect

        from eval_naturalistic.contracts import validate_prospective_manifest_structural

        param = inspect.signature(validate_prospective_manifest_structural).parameters[
            "serialized_body"
        ]
        self.assertNotEqual(param.annotation, bytes)

    def test_pending_slots_fail_frame_frozen_transition(self):
        from eval_naturalistic.contracts import (
            make_frozen_prospective_manifest,
            make_pending_prospective_manifest,
            seal_artifact_dict,
            validate_prospective_manifest_freeze_transition,
            validate_prospective_manifest_structural,
        )
        from eval_naturalistic.digest import artifact_content_digest
        from eval_naturalistic.fixtures import make_synthetic_frame

        frame = make_synthetic_frame()
        pending = make_pending_prospective_manifest(frame=frame)
        pending_body = seal_artifact_dict(pending.to_dict(), seal_time="2026-08-30T01:00:00Z")
        pending_body["logged_freeze_digest"] = artifact_content_digest(pending_body)

        draft_ok = validate_prospective_manifest_structural(pending_body, require_logged_freeze=False)
        self.assertTrue(draft_ok.ok, draft_ok.errors)
        freeze_fail = validate_prospective_manifest_freeze_transition(
            pending_body,
            require_logged_freeze=True,
        )
        self.assertFalse(freeze_fail.ok)
        self.assertTrue(any("pending at FRAME_FROZEN" in err for err in freeze_fail.errors))

        frozen = make_frozen_prospective_manifest(frame=frame)
        frozen_body = seal_artifact_dict(frozen.to_dict(), seal_time="2026-08-30T01:00:00Z")
        frozen_body["logged_freeze_digest"] = artifact_content_digest(frozen_body)
        freeze_ok = validate_prospective_manifest_freeze_transition(
            frozen_body,
            require_logged_freeze=True,
        )
        self.assertTrue(freeze_ok.ok, freeze_ok.errors)

    def test_unsealed_manifest_fails_freeze_transition_with_valid_digest(self):
        import copy

        from eval_naturalistic.contracts import (
            make_frozen_prospective_manifest,
            seal_artifact_dict,
            validate_prospective_manifest_freeze_transition,
        )
        from eval_naturalistic.digest import artifact_content_digest
        from eval_naturalistic.fixtures import make_synthetic_frame

        frame = make_synthetic_frame()
        frozen = make_frozen_prospective_manifest(frame=frame)
        sealed = seal_artifact_dict(frozen.to_dict(), seal_time="2026-08-30T01:00:00Z")
        unsealed = copy.deepcopy(sealed)
        header = dict(unsealed["header"])
        header["sealed"] = False
        unsealed["header"] = header
        body_for_digest = copy.deepcopy(unsealed)
        body_for_digest.pop("logged_freeze_digest", None)
        unsealed["logged_freeze_digest"] = artifact_content_digest(body_for_digest)

        freeze_fail = validate_prospective_manifest_freeze_transition(
            unsealed,
            require_logged_freeze=True,
        )
        self.assertFalse(freeze_fail.ok)
        self.assertTrue(
            any("must be sealed at FRAME_FROZEN" in err for err in freeze_fail.errors)
        )

if __name__ == "__main__":
    unittest.main()
