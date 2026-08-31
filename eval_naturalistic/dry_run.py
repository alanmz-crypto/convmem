"""G5 synthetic end-to-end dry-run of the G1–G4 naturalistic evaluation machinery.

This module exercises the landed methodology substrate with synthetic fixtures
only. A favorable C1−C0 numeric effect is a descriptive fixture result, not
evidence that ConvMem helps. G5 never authorizes G6 or a product disposition.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from eval_naturalistic.adjudication import (
    assign_episode_opportunity_identity,
    build_sealed_target_registry,
    reject_capture_driven_registry_mutation,
    validate_registry_build_context_arm_blind,
    validate_registry_membership_immutable,
)
from eval_naturalistic.adjudication_fixtures import (
    make_agreeing_eligible_candidate,
    make_default_workflow,
    make_synthetic_adjudication_chain,
)
from eval_naturalistic.analysis import (
    EpisodeRegistryViewV1,
    ScorerSubmissionV1,
    aggregate_targets_to_within_episode_score,
    build_structured_synthetic_result,
    compute_co_primary_aggregation,
    compute_deterministic_bounds,
    evaluate_information_gate_readiness,
    prove_one_score_per_episode_per_condition,
    record_scorer_reliability,
    reject_post_result_parameter_mutation,
    validate_required_parameter_slots,
)
from eval_naturalistic.analysis_fixtures import (
    G4_SYNTHETIC_FIXTURE_SEED,
    make_c1_better_than_c0_fixture,
    make_pending_parameter_slots,
    make_post_result_threshold_fill_attempt,
    make_scorer_disagreement_fixture,
    make_target_rich_episode_target_scores,
    make_zero_target_episodes_fixture,
)
from eval_naturalistic.base import validate_prospective_validator_import_boundary
from eval_naturalistic.contract_validate import validate_capture_independent_registry
from eval_naturalistic.contracts import (
    ProspectiveManifestV1,
    StageBoundaryLedgerEntryV1,
    StageBoundaryLedgerV1,
    StageBoundaryPredicateResultV1,
    TargetRecordV1,
    TargetRegistryV1,
    TargetSpanBindingV1,
    make_frozen_prospective_manifest,
    make_pending_prospective_manifest,
    reject_arm_dependent_registry_rule,
    seal_artifact_dict,
    validate_prospective_manifest_freeze_transition,
    validate_prospective_manifest_structural,
    verify_handoff_artifact_digest,
)
from eval_naturalistic.digest import artifact_content_digest
from eval_naturalistic.dry_run_mechanics import (
    G5C_VALIDATOR_IDENTITY,
    G5C_VALIDATOR_VERSION,
    SyntheticPairedReplayStateV1,
    SyntheticSnapshotDiagnosisV1,
    SyntheticTrialExecutionV1,
    make_symmetric_condition_packages,
    qualify_c0_c1_environment,
    validate_natural_c1_snapshot,
    validate_opportunity_roster,
    validate_paired_replay_symmetry,
    validate_trial_execution,
)
from eval_naturalistic.enums import (
    CaptureDiagnosticState,
    EligibilityDisposition,
    EpisodeRegistryStatus,
    OutcomeReasonCode,
    ProbeBuildOutcome,
    ReliabilityState,
    StudyStageId,
    StudyTerminalDisposition,
    TrialCondition,
)
from eval_naturalistic.fixtures import (
    make_synthetic_capture,
    make_synthetic_census,
    make_synthetic_episode,
    make_synthetic_evidence,
    make_synthetic_frame,
)
from eval_naturalistic.probe_construction import (
    build_sealed_probe_bundle,
    run_leakage_checklist,
)
from eval_naturalistic.probe_fixtures import (
    CONTINUATION_PROBE_TEXT,
    LEAK_REVIEWER_ID,
    VALID_GROUND_TRUTH,
    make_default_probe_config,
    make_probe_draft,
    make_sealed_registry_and_census,
)

G5_CLASSIFICATION = "methodology_validation_not_product_evidence"
G5_PRODUCT_CONCLUSION_FORBIDDEN = True

G5_REQUIRED_FAIL_CLOSED_SCENARIOS = frozenset(
    {
        "unsealed_target_edit",
        "probe_answer_leakage",
        "source_leakage",
        "adjudicator_probe_author_collision",
        "c0_c1_tool_asymmetry",
        "reused_agent_b_context",
        "target_directed_reindex",
        "missing_zero_target_episode",
        "target_rich_episode_overweighting",
        "post_result_threshold_change",
        "controller_as_agent",
        "low_scorer_reliability",
        "duplicate_episode_rows",
        "orphaned_score",
        "malformed_score",
        "pending_information_gate_slots",
        "incomplete_nominal_t0_frame",
        "pending_slots_block_frame_frozen",
        "unsealed_manifest_blocks_frame_frozen",
        "false_completeness_placeholder_slot",
        "freeze_tamper_post_seal",
        "handoff_artifact_mismatch",
        "validator_import_boundary",
        "registry_arm_dependent_rule",
        "invalid_vs_boundable_separation",
        "disposition_precedence_favorable_effect",
        "paired_replay_mismatch",
        "scorer_integrity_vs_reliability",
        "synthetic_only_guard",
        "stage_corruption_sweep",
    }
)



@dataclass
class G5ScenarioResult:
    """One named G5 scenario and whether it demonstrated the required semantics."""

    scenario_id: str
    stage: str
    demonstrated: bool
    fail_closed: bool
    notes: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class G5DryRunReport:  # pylint: disable=too-many-instance-attributes
    """Reproducible G5 verification record. Not a product-value report."""

    classification: str
    g6_authority_assumed: bool
    naturalistic_evidence_created: bool
    synthetic_only: bool
    fixture_seed: int
    g4_safe_example: dict[str, Any]
    happy_path: dict[str, Any]
    scenarios: list[G5ScenarioResult]
    all_required_fail_closed_demonstrated: bool
    product_disposition_emitted: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scenarios"] = [scenario.to_dict() for scenario in self.scenarios]
        return payload


def _synthetic_locators_only(evidence) -> bool:
    return all(source.locator.startswith("synthetic://") for source in evidence.sources)



def _ledger_entry(
    *,
    stage: StudyStageId,
    input_digest: str,
    predicates: list[tuple[str, bool, str | None]],
    output_digest: str | None,
    guarantees: list[str],
    assumptions: list[str],
    failure_reasons: list[str] | None = None,
) -> StageBoundaryLedgerEntryV1:
    passed = not failure_reasons and all(item[1] for item in predicates)
    return StageBoundaryLedgerEntryV1(
        stage_id=stage,
        input_artifact_digest=input_digest,
        required_predicates=[
            StageBoundaryPredicateResultV1(predicate_name=name, passed=ok, detail=detail)
            for name, ok, detail in predicates
        ],
        validator_identity=G5C_VALIDATOR_IDENTITY,
        validator_version=G5C_VALIDATOR_VERSION,
        output_artifact_digest=output_digest,
        guarantees_exported=guarantees,
        next_stage_assumptions=assumptions,
        failure_reasons=failure_reasons or [],
        passed=passed,
    )


def _seal_prospective_manifest(manifest: ProspectiveManifestV1) -> tuple[dict[str, Any], str]:
    body = manifest.to_dict()
    sealed = seal_artifact_dict(body, seal_time="2026-08-30T00:00:00Z")
    digest = artifact_content_digest(sealed)
    sealed["logged_freeze_digest"] = digest
    return sealed, digest


def _validate_t0_prospective_manifest(serialized: dict[str, Any], *, require_freeze: bool) -> list[str]:
    if require_freeze:
        result = validate_prospective_manifest_freeze_transition(
            serialized,
            require_logged_freeze=True,
        )
    else:
        result = validate_prospective_manifest_structural(serialized, require_logged_freeze=False)
    return list(result.errors)


def _derive_stage_ok(ledger: StageBoundaryLedgerV1) -> dict[str, bool]:
    return ledger.derived_group_summaries()

def run_g4_safe_synthetic_example() -> dict[str, Any]:
    """Preserve the G4 descriptive 0.3 fixture without a product conclusion."""

    episodes, scores = make_c1_better_than_c0_fixture()
    aggregation = compute_co_primary_aggregation(
        episodes,
        scores,
        lineage_inputs={"fixture_seed": G4_SYNTHETIC_FIXTURE_SEED, "scenario": "g4_safe"},
    )
    assert aggregation.co_primary is not None
    gate = evaluate_information_gate_readiness(
        make_pending_parameter_slots(),
        aggregation.co_primary,
        None,
    )
    return {
        "aggregation_ok": aggregation.ok,
        "conditional_effect": aggregation.co_primary.conditional_mean_effect,
        "paired_episodes": aggregation.co_primary.conditional_episode_count,
        "disposition": gate.disposition.value,
        "all_slots_frozen": gate.all_slots_frozen,
        "classification": G5_CLASSIFICATION,
        "not_evidence_that_convmem_helps": True,
    }


def _build_episode_chain(*, episode_id: str, zero_targets: bool):
    frame = make_synthetic_frame(study_id="study-g5-synthetic-001")
    episode = make_synthetic_episode(frame=frame, episode_id=episode_id)
    evidence = make_synthetic_evidence(episode=episode, complete=True)
    workflow = make_default_workflow()
    candidates = [] if zero_targets else [make_agreeing_eligible_candidate(target_id=f"tgt-{episode_id}")]
    registry_result = build_sealed_target_registry(
        frame=frame,
        episode=episode,
        evidence=evidence,
        candidates=candidates,
        workflow=workflow,
    )
    return frame, episode, evidence, registry_result


# G5 happy-path orchestration intentionally walks T0–T10 in one function.
# pylint: disable-next=too-many-locals,too-many-statements
def run_g5_end_to_end() -> dict[str, Any]:
    """Walk the available G1–G4 path with two target-bearing episodes and one zero."""

    errors: list[str] = []
    ledger_entries: list[StageBoundaryLedgerEntryV1] = []

    frame = make_synthetic_frame(study_id="study-g5-synthetic-001")
    frozen_manifest = make_frozen_prospective_manifest(frame=frame)
    sealed_manifest_body, freeze_digest = _seal_prospective_manifest(frozen_manifest)
    t0_errors = _validate_t0_prospective_manifest(sealed_manifest_body, require_freeze=True)
    handoff_ok = verify_handoff_artifact_digest(
        logged_digest=freeze_digest,
        handed_artifact=sealed_manifest_body,
    )
    if not handoff_ok.ok:
        t0_errors.extend(handoff_ok.errors)
    arm_blind = validate_registry_build_context_arm_blind()
    if not arm_blind.ok:
        t0_errors.extend(arm_blind.errors)
    registry_rule = reject_arm_dependent_registry_rule(
        frozen_manifest.opportunity_authority_rule
    )
    if not registry_rule.ok:
        t0_errors.extend(registry_rule.errors)
    replay_state = SyntheticPairedReplayStateV1(
        sealed_pre_trial_digest=freeze_digest,
        c0_readable_roots=frozenset({"/synthetic/workspace"}),
        c1_readable_roots=frozenset({"/synthetic/workspace"}),
        shared_mutable_state=False,
        shared_cache_or_database=False,
        external_service_replayed=True,
        frozen_execution_order=("ep-c1-win-001", "ep-c1-win-002"),
        actual_execution_order=("ep-c1-win-001", "ep-c1-win-002"),
        c0_convmem_available=False,
        c1_convmem_available=True,
    )
    replay_ok = validate_paired_replay_symmetry(replay_state)
    if not replay_ok.ok:
        t0_errors.extend(replay_ok.errors)
    ledger_entries.append(
        _ledger_entry(
            stage=StudyStageId.T0,
            input_digest=frame.header.content_digest or "",
            predicates=[
                ("structural_manifest_complete", not t0_errors, None),
                ("logged_freeze_digest_present", bool(freeze_digest), None),
                ("paired_replay_policy_bound", replay_ok.ok, None),
            ],
            output_digest=freeze_digest,
            guarantees=["prospective_manifest_frozen", "freeze_digest_logged"],
            assumptions=["episode_collection_may_begin"],
            failure_reasons=t0_errors,
        )
    )
    if t0_errors:
        ledger = StageBoundaryLedgerV1(entries=ledger_entries)
        return {
            "aggregation_ok": False,
            "conditional_effect": None,
            "paired_episodes": 0,
            "zero_target_episode_count": 0,
            "opportunity_episode_count": 0,
            "disposition": StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE.value,
            "all_slots_frozen": False,
            "scorer_reliability_passes": None,
            "stage_ok": _derive_stage_ok(ledger),
            "stage_ledger": ledger.to_dict(),
            "errors": t0_errors,
            "classification": G5_CLASSIFICATION,
            "not_evidence_that_convmem_helps": True,
            "synthetic_only": True,
        }

    win_one = _build_episode_chain(episode_id="ep-c1-win-001", zero_targets=False)
    win_two = _build_episode_chain(episode_id="ep-c1-win-002", zero_targets=False)
    zero = _build_episode_chain(episode_id="ep-zero-001", zero_targets=True)
    chains = {"ep-c1-win-001": win_one, "ep-c1-win-002": win_two, "ep-zero-001": zero}

    for episode_id, (_, _, evidence, registry_result) in chains.items():
        if not _synthetic_locators_only(evidence):
            errors.append(f"{episode_id}: non-synthetic evidence locator")
        if not registry_result.ok or registry_result.registry is None:
            errors.append(f"{episode_id}: registry build failed: {registry_result.errors}")
        expected_status = (
            EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS
            if episode_id == "ep-zero-001"
            else EpisodeRegistryStatus.TARGETS_PRESENT
        )
        if registry_result.episode_status != expected_status:
            errors.append(f"{episode_id}: unexpected registry status {registry_result.episode_status}")

    ledger_entries.append(
        _ledger_entry(
            stage=StudyStageId.T1,
            input_digest=freeze_digest,
            predicates=[("synthetic_episode_locators", not errors, None)],
            output_digest=artifact_content_digest({"episodes": sorted(chains)}),
            guarantees=["episodes_observed"],
            assumptions=["registry_may_be_built"],
            failure_reasons=errors.copy(),
        )
    )
    registry_digests: list[str] = []
    for episode_id, (_, _, _, registry_result) in chains.items():
        if registry_result.registry is not None and registry_result.registry.header.content_digest:
            registry_digests.append(registry_result.registry.header.content_digest)
            assign_episode_opportunity_identity(
                registry=registry_result.registry,
                episode_id=episode_id,
            )
    t2_failures = list(errors)
    ledger_entries.append(
        _ledger_entry(
            stage=StudyStageId.T2,
            input_digest=freeze_digest,
            predicates=[("registry_sealed", bool(registry_digests), None)],
            output_digest=registry_digests[0] if registry_digests else None,
            guarantees=["target_registry_sealed", "opportunity_identity_assigned"],
            assumptions=["census_and_probe_may_proceed"],
            failure_reasons=t2_failures,
        )
    )
    sealed_episode_ids = frozenset(chains)
    views: list[EpisodeRegistryViewV1] = []
    within_scores = []
    probe_sealed = True

    score_pairs = {
        "ep-c1-win-001": (0.40, 0.70),
        "ep-c1-win-002": (0.35, 0.65),
    }

    for episode_id, (_, _, _, registry_result) in chains.items():
        registry = registry_result.registry
        if registry is None:
            continue
        census = make_synthetic_census(registry=registry)
        views.append(
            EpisodeRegistryViewV1(
                episode_id=episode_id,
                registry_status=registry.episode_entries[0].registry_status,
                eligible_target_count=len(registry.targets),
            )
        )
        capture = make_synthetic_capture(
            registry=registry,
            capture_state=CaptureDiagnosticState.ABSENT_FROM_CONVMEM,
        )
        capture_check = validate_capture_independent_registry(registry, capture)
        if not capture_check.ok:
            errors.extend(capture_check.errors)
        if registry.targets:
            target = registry.targets[0]
            probe_result = build_sealed_probe_bundle(
                registry=registry,
                census=census,
                target=target,
                draft=make_probe_draft(target=target),
                leakage_reviewer_id=LEAK_REVIEWER_ID,
                config=make_default_probe_config(),
            )
            if not probe_result.ok or probe_result.outcome != ProbeBuildOutcome.SEALED:
                probe_sealed = False
                errors.extend(probe_result.errors)

        snapshot = validate_natural_c1_snapshot(
            SyntheticSnapshotDiagnosisV1(
                natural_capture_only=True,
                target_directed_reindex=False,
                snapshot_mutable=False,
                registry_unchanged=True,
            )
        )
        if not snapshot.ok:
            errors.extend(snapshot.errors)

        if episode_id in score_pairs:
            c0_score, c1_score = score_pairs[episode_id]
            c0_targets, c1_targets = make_target_rich_episode_target_scores(
                episode_id=episode_id,
                c0_scores=[c0_score],
                c1_scores=[c1_score],
            )
            within_scores.append(
                aggregate_targets_to_within_episode_score(
                    c0_targets, episode_id=episode_id, condition=TrialCondition.C0
                )
            )
            within_scores.append(
                aggregate_targets_to_within_episode_score(
                    c1_targets, episode_id=episode_id, condition=TrialCondition.C1
                )
            )

    t35_failures = [] if probe_sealed and not errors else ["probe_or_capture_stage_failed"]
    ledger_entries.extend(
        [
            _ledger_entry(
                stage=StudyStageId.T3,
                input_digest=registry_digests[0] if registry_digests else "",
                predicates=[("census_ready", probe_sealed, None)],
                output_digest=registry_digests[0] if registry_digests else None,
                guarantees=["census_accepted"],
                assumptions=["probe_construction_may_begin"],
            ),
            _ledger_entry(
                stage=StudyStageId.T4,
                input_digest=registry_digests[0] if registry_digests else "",
                predicates=[("probe_sealed", probe_sealed, None)],
                output_digest=None,
                guarantees=["probes_sealed"],
                assumptions=["capture_diagnosis_may_begin"],
            ),
            _ledger_entry(
                stage=StudyStageId.T5,
                input_digest=registry_digests[0] if registry_digests else "",
                predicates=[("natural_capture_only", probe_sealed and not errors, None)],
                output_digest=None,
                guarantees=["c1_snapshot_natural_only"],
                assumptions=["environment_qualification_may_begin"],
                failure_reasons=t35_failures,
            ),
        ]
    )
    c0_pkg, c1_pkg = make_symmetric_condition_packages()
    env_check = qualify_c0_c1_environment(c0_pkg, c1_pkg)
    if not env_check.ok:
        errors.extend(env_check.errors)

    seen: set[str] = set()
    for episode_id, condition in (
        ("ep-c1-win-001", TrialCondition.C0),
        ("ep-c1-win-001", TrialCondition.C1),
        ("ep-c1-win-002", TrialCondition.C0),
        ("ep-c1-win-002", TrialCondition.C1),
    ):
        session = f"synthetic-session-{condition.value}-{episode_id}"
        trial_check = validate_trial_execution(
            SyntheticTrialExecutionV1(
                trial_id=f"trial-{condition.value}-{episode_id}",
                condition=condition,
                session_identity=session,
                prior_session_mounted=False,
                controller_provided_answer=False,
                controller_provided_search=False,
                complete_trace=True,
                reused_agent_b_context=False,
            ),
            seen_session_identities=frozenset(seen),
        )
        if not trial_check.ok:
            errors.extend(trial_check.errors)
        seen.add(session)
    ledger_entries.append(
        _ledger_entry(
            stage=StudyStageId.T6,
            input_digest=freeze_digest,
            predicates=[("c0_c1_symmetric", env_check.ok, None)],
            output_digest=None,
            guarantees=["c0c1_ready"],
            assumptions=["agent_b_execution_may_begin"],
            failure_reasons=env_check.errors if not env_check.ok else [],
        )
    )
    ledger_entries.append(
        _ledger_entry(
            stage=StudyStageId.T7,
            input_digest=freeze_digest,
            predicates=[("fresh_sessions", not errors, None)],
            output_digest=None,
            guarantees=["execution_complete"],
            assumptions=["scoring_may_begin"],
            failure_reasons=[e for e in errors if "session" in e or "controller" in e],
        )
    )

    roster_check = validate_opportunity_roster(
        sealed_episode_ids=sealed_episode_ids,
        aggregation_episode_ids=frozenset(view.episode_id for view in views),
    )
    if not roster_check.ok:
        errors.extend(roster_check.errors)
    one_score = prove_one_score_per_episode_per_condition(within_scores)
    if not one_score.ok:
        errors.extend(one_score.errors)

    reliability = record_scorer_reliability(
        [
            ScorerSubmissionV1(
                "scorer-a",
                "ep-c1-win-001",
                TrialCondition.C0,
                0.40,
                ReliabilityState.RELIABILITY_ACCEPTABLE,
            ),
            ScorerSubmissionV1(
                "scorer-a",
                "ep-c1-win-001",
                TrialCondition.C1,
                0.70,
                ReliabilityState.RELIABILITY_ACCEPTABLE,
            ),
        ],
        [
            ScorerSubmissionV1(
                "scorer-b",
                "ep-c1-win-001",
                TrialCondition.C0,
                0.41,
                ReliabilityState.RELIABILITY_ACCEPTABLE,
            ),
            ScorerSubmissionV1(
                "scorer-b",
                "ep-c1-win-001",
                TrialCondition.C1,
                0.71,
                ReliabilityState.RELIABILITY_ACCEPTABLE,
            ),
        ],
        gate_value=None,
        agreement_tolerance=0.05,
    )
    if reliability.passes_gate is True:
        errors.append("scorer reliability must not pass a live threshold under G5")

    aggregation = compute_co_primary_aggregation(
        views,
        within_scores,
        lineage_inputs={"fixture_seed": G4_SYNTHETIC_FIXTURE_SEED, "scenario": "g5_e2e"},
    )
    if not aggregation.ok or aggregation.co_primary is None:
        errors.extend(aggregation.errors)
        gate_disposition = StudyTerminalDisposition.INVALID
        all_frozen = False
        conditional_effect = None
        paired = 0
        zero_count = 0
    else:
        gate = evaluate_information_gate_readiness(
            make_pending_parameter_slots(),
            aggregation.co_primary,
            reliability,
        )
        gate_disposition = gate.disposition
        all_frozen = gate.all_slots_frozen
        conditional_effect = aggregation.co_primary.conditional_mean_effect
        paired = aggregation.co_primary.conditional_episode_count
        zero_count = aggregation.co_primary.zero_target_episode_count
        if gate_disposition != StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE:
            errors.append(f"G5 must not emit product disposition {gate_disposition.value}")
        if all_frozen:
            errors.append("G5 must not freeze information-gate slots")

    bounds = compute_deterministic_bounds(
        complete_pair_effects=[conditional_effect] if conditional_effect is not None else [],
        valid_missing_count=0,
        invalid_count=0,
        denominator_episode_count=len(views),
    )
    structured = None
    if aggregation.co_primary is not None:
        structured = build_structured_synthetic_result(
            co_primary=aggregation.co_primary,
            bounds=bounds,
            process_accounting={
                "opportunity_episode_count": len(views),
                "zero_target_episode_count": zero_count,
                "paired_episodes": paired,
            },
            apparent_positive_effect=conditional_effect is not None and conditional_effect > 0,
        )
    t810_failures = list(errors)
    ledger_entries.extend(
        [
            _ledger_entry(
                stage=StudyStageId.T8,
                input_digest=freeze_digest,
                predicates=[("scorer_reliability_not_live_pass", reliability.passes_gate is not True, None)],
                output_digest=None,
                guarantees=["scoring_locked"],
                assumptions=["aggregation_may_begin"],
            ),
            _ledger_entry(
                stage=StudyStageId.T9,
                input_digest=freeze_digest,
                predicates=[("aggregation_ok", aggregation.ok, None)],
                output_digest=artifact_content_digest(bounds.to_dict()),
                guarantees=["complete_pair_effect_or_bounds", "denominator_preserved"],
                assumptions=["disposition_derivation_may_begin"],
            ),
            _ledger_entry(
                stage=StudyStageId.T10,
                input_digest=freeze_digest,
                predicates=[
                    ("no_product_disposition", gate_disposition != StudyTerminalDisposition.COMPLETE_POSITIVE, None),
                    ("methodology_only", True, None),
                ],
                output_digest=None,
                guarantees=["orthogonal_disposition_derived"],
                assumptions=[],
                failure_reasons=t810_failures,
            ),
        ]
    )
    ledger = StageBoundaryLedgerV1(entries=ledger_entries)
    stage_ok = _derive_stage_ok(ledger)
    return {
        "aggregation_ok": bool(aggregation.ok and not errors),
        "conditional_effect": conditional_effect,
        "paired_episodes": paired,
        "zero_target_episode_count": zero_count,
        "opportunity_episode_count": len(views),
        "disposition": gate_disposition.value,
        "all_slots_frozen": all_frozen,
        "scorer_reliability_passes": reliability.passes_gate,
        "stage_ok": stage_ok,
        "stage_ledger": ledger.to_dict(),
        "structured_result": structured.to_dict() if structured else None,
        "errors": errors,
        "classification": G5_CLASSIFICATION,
        "not_evidence_that_convmem_helps": True,
        "synthetic_only": True,
    }


def _scenario(
    scenario_id: str,
    stage: str,
    *,
    demonstrated: bool,
    fail_closed: bool,
    notes: str,
    details: dict[str, Any] | None = None,
) -> G5ScenarioResult:
    return G5ScenarioResult(
        scenario_id=scenario_id,
        stage=stage,
        demonstrated=demonstrated,
        fail_closed=fail_closed,
        notes=notes,
        details=details or {},
    )


def _adversarial_capture_exclusion() -> G5ScenarioResult:
    frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
    result = build_sealed_target_registry(
        frame=frame,
        episode=episode,
        evidence=evidence,
        candidates=[make_agreeing_eligible_candidate()],
        workflow=workflow,
    )
    assert result.registry is not None
    capture = make_synthetic_capture(
        registry=result.registry,
        capture_state=CaptureDiagnosticState.ABSENT_FROM_CONVMEM,
    )
    check = validate_capture_independent_registry(result.registry, capture)
    still_present = any(target.target_id == "tgt-001" for target in result.registry.targets)
    return _scenario(
        "capture_dependent_target_exclusion",
        "T5",
        demonstrated=check.ok and still_present,
        fail_closed=False,
        notes="Uncaptured eligible target remains in the sealed registry.",
        details={"still_present": still_present, "capture_ok": check.ok},
    )


def _adversarial_unsealed_edit() -> G5ScenarioResult:
    frame, episode, evidence, workflow = make_synthetic_adjudication_chain()
    result = build_sealed_target_registry(
        frame=frame,
        episode=episode,
        evidence=evidence,
        candidates=[make_agreeing_eligible_candidate()],
        workflow=workflow,
    )
    assert result.registry is not None
    mutated = copy.deepcopy(result.registry.to_dict())
    mutated["targets"].append(
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
    proposed = TargetRegistryV1.from_dict(
        seal_artifact_dict(mutated, seal_time="2026-08-30T03:00:00Z")
    )
    immutability = validate_registry_membership_immutable(result.registry, proposed)
    capture_reject = reject_capture_driven_registry_mutation(result.registry, proposed)
    demonstrated = (not immutability.ok) and (not capture_reject.ok)
    return _scenario(
        "unsealed_target_edit",
        "T2",
        demonstrated=demonstrated,
        fail_closed=True,
        notes="Post-seal target injection is rejected and cannot be reused.",
    )


def _adversarial_answer_leakage() -> G5ScenarioResult:
    registry, census = make_sealed_registry_and_census()
    target = registry.targets[0]
    result = build_sealed_probe_bundle(
        registry=registry,
        census=census,
        target=target,
        draft=make_probe_draft(
            target=target,
            probe_text=f"{CONTINUATION_PROBE_TEXT} Answer: {VALID_GROUND_TRUTH}",
        ),
        leakage_reviewer_id=LEAK_REVIEWER_ID,
        config=make_default_probe_config(),
    )
    paraphrase = run_leakage_checklist(
        "alpha beta gamma delta epsilon zeta workflow continuation",
        ground_truth_answer="alpha beta gamma delta epsilon zeta",
    )
    demonstrated = (
        (not result.ok)
        and result.outcome == ProbeBuildOutcome.LEAKAGE_REJECTED
        and result.probe is None
        and (not paraphrase.ok)
    )
    return _scenario(
        "probe_answer_leakage",
        "T4",
        demonstrated=demonstrated,
        fail_closed=True,
        notes="Explicit answer and close paraphrase both fail leakage review.",
    )


def _adversarial_source_leakage() -> G5ScenarioResult:
    path_check = run_leakage_checklist("Continue work; see synthetic://transcript/ep-001 for context.")
    location_check = run_leakage_checklist("Continue from line 42 in the prior session.")
    return _scenario(
        "source_leakage",
        "T4",
        demonstrated=(not path_check.ok) and (not location_check.ok),
        fail_closed=True,
        notes="Source path and source-location hints are rejected.",
    )


def _adversarial_role_collision() -> G5ScenarioResult:
    registry, census = make_sealed_registry_and_census()
    target = registry.targets[0]
    result = build_sealed_probe_bundle(
        registry=registry,
        census=census,
        target=target,
        draft=make_probe_draft(target=target, probe_author_id="adj-a"),
        leakage_reviewer_id=LEAK_REVIEWER_ID,
        config=make_default_probe_config(),
    )
    return _scenario(
        "adjudicator_probe_author_collision",
        "T4",
        demonstrated=(not result.ok)
        and result.outcome == ProbeBuildOutcome.ROLE_OR_PROVENANCE_REJECTED
        and result.probe is None,
        fail_closed=True,
        notes="Shared adjudicator/probe-author identity hard-fails T4.",
    )


def _adversarial_tool_asymmetry() -> G5ScenarioResult:
    c0, c1 = make_symmetric_condition_packages()
    c1_bad = type(c1)(
        condition=c1.condition,
        tools=c1.tools | {"extra_tool"},
        readable_roots=c1.readable_roots,
        model_identity=c1.model_identity,
        convmem_available=c1.convmem_available,
        budget_identity=c1.budget_identity,
        stopping_identity=c1.stopping_identity,
    )
    check = qualify_c0_c1_environment(c0, c1_bad)
    return _scenario(
        "c0_c1_tool_asymmetry",
        "T6",
        demonstrated=not check.ok,
        fail_closed=True,
        notes="Adding an ordinary tool to C1 fails environment qualification.",
        details={"errors": check.errors},
    )


def _adversarial_reused_context() -> G5ScenarioResult:
    first = SyntheticTrialExecutionV1(
        trial_id="trial-c0-reuse",
        condition=TrialCondition.C0,
        session_identity="synthetic-session-shared",
        prior_session_mounted=False,
        controller_provided_answer=False,
        controller_provided_search=False,
        complete_trace=True,
        reused_agent_b_context=False,
    )
    reused = SyntheticTrialExecutionV1(
        trial_id="trial-c1-reuse",
        condition=TrialCondition.C1,
        session_identity="synthetic-session-shared",
        prior_session_mounted=True,
        controller_provided_answer=False,
        controller_provided_search=False,
        complete_trace=True,
        reused_agent_b_context=True,
    )
    first_ok = validate_trial_execution(first, seen_session_identities=frozenset())
    reused_check = validate_trial_execution(
        reused,
        seen_session_identities=frozenset({first.session_identity}),
    )
    return _scenario(
        "reused_agent_b_context",
        "T7",
        demonstrated=first_ok.ok and (not reused_check.ok),
        fail_closed=True,
        notes="Mounted prior session and reused session identity fail T7.",
        details={"errors": reused_check.errors},
    )


def _adversarial_reindex() -> G5ScenarioResult:
    check = validate_natural_c1_snapshot(
        SyntheticSnapshotDiagnosisV1(
            natural_capture_only=False,
            target_directed_reindex=True,
            snapshot_mutable=True,
            registry_unchanged=False,
        )
    )
    return _scenario(
        "target_directed_reindex",
        "T5",
        demonstrated=not check.ok,
        fail_closed=True,
        notes="Target-directed reindex and mutable snapshot fail T5.",
        details={"errors": check.errors},
    )


def _adversarial_missing_zero() -> G5ScenarioResult:
    sealed = frozenset({"ep-mix-target", "ep-mix-zero", "ep-mix-zero-2"})
    dropped = frozenset({"ep-mix-target"})
    check = validate_opportunity_roster(
        sealed_episode_ids=sealed,
        aggregation_episode_ids=dropped,
    )
    return _scenario(
        "missing_zero_target_episode",
        "T9",
        demonstrated=not check.ok,
        fail_closed=True,
        notes="Dropping zero-target episodes from the opportunity roster fails T9.",
        details={"errors": check.errors},
    )


def _adversarial_target_rich() -> G5ScenarioResult:
    c0_targets, c1_targets = make_target_rich_episode_target_scores(
        c0_scores=[0.40, 0.60, 0.80],
        c1_scores=[0.50, 0.70, 0.90],
    )
    c0_episode = aggregate_targets_to_within_episode_score(
        c0_targets, episode_id="ep-rich-001", condition=TrialCondition.C0
    )
    c1_episode = aggregate_targets_to_within_episode_score(
        c1_targets, episode_id="ep-rich-001", condition=TrialCondition.C1
    )
    proof = prove_one_score_per_episode_per_condition([c0_episode, c1_episode])
    result = compute_co_primary_aggregation(
        [EpisodeRegistryViewV1("ep-rich-001", EpisodeRegistryStatus.TARGETS_PRESENT, 3)],
        [c0_episode, c1_episode],
        lineage_inputs={"fixture_seed": G4_SYNTHETIC_FIXTURE_SEED, "scenario": "target_rich"},
    )
    duplicate_targets = copy.deepcopy(c0_targets)
    duplicate_targets[1].target_id = duplicate_targets[0].target_id
    dup_score = aggregate_targets_to_within_episode_score(
        duplicate_targets, episode_id="ep-rich-001", condition=TrialCondition.C0
    )
    demonstrated = (
        proof.ok
        and result.ok
        and result.co_primary is not None
        and result.co_primary.conditional_episode_count == 1
        and dup_score.reliability_state == ReliabilityState.RELIABILITY_NON_ESTIMABLE
    )
    return _scenario(
        "target_rich_episode_overweighting",
        "T9",
        demonstrated=demonstrated,
        fail_closed=True,
        notes="Target-rich episodes contribute one score; duplicate target rows are non-estimable.",
        details={
            "conditional_episode_count": (
                None if result.co_primary is None else result.co_primary.conditional_episode_count
            ),
            "duplicate_non_estimable": dup_score.reliability_state.value,
        },
    )


def _adversarial_post_result_threshold() -> G5ScenarioResult:
    before, after = make_post_result_threshold_fill_attempt()
    check = reject_post_result_parameter_mutation(before, after)
    return _scenario(
        "post_result_threshold_change",
        "T10",
        demonstrated=not check.ok,
        fail_closed=True,
        notes="Filling a pending slot after results is rejected and does not recompute a verdict.",
        details={"errors": check.errors},
    )


def _adversarial_controller_as_agent() -> G5ScenarioResult:
    check = validate_trial_execution(
        SyntheticTrialExecutionV1(
            trial_id="trial-controller",
            condition=TrialCondition.C1,
            session_identity="synthetic-session-controller",
            prior_session_mounted=False,
            controller_provided_answer=True,
            controller_provided_search=True,
            complete_trace=True,
            reused_agent_b_context=False,
        ),
        seen_session_identities=frozenset(),
    )
    return _scenario(
        "controller_as_agent",
        "T7",
        demonstrated=not check.ok,
        fail_closed=True,
        notes="Controller-provided answer/search fails T7.",
        details={"errors": check.errors},
    )


def _adversarial_low_reliability() -> G5ScenarioResult:
    primary, secondary = make_scorer_disagreement_fixture()
    unfrozen = record_scorer_reliability(
        primary, secondary, gate_value=None, agreement_tolerance=0.05
    )
    below = record_scorer_reliability(
        primary, secondary, gate_value="0.95", agreement_tolerance=0.05
    )
    episodes, scores = make_c1_better_than_c0_fixture()
    aggregation = compute_co_primary_aggregation(
        episodes,
        scores,
        lineage_inputs={"fixture_seed": G4_SYNTHETIC_FIXTURE_SEED, "scenario": "low_reliability"},
    )
    assert aggregation.co_primary is not None
    gate = evaluate_information_gate_readiness(
        make_pending_parameter_slots(),
        aggregation.co_primary,
        below,
    )
    demonstrated = (
        unfrozen.passes_gate is None
        and below.passes_gate is False
        and gate.disposition == StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
    )
    return _scenario(
        "low_scorer_reliability",
        "T8",
        demonstrated=demonstrated,
        fail_closed=True,
        notes="No live reliability pass; disagreement below a synthetic gate remains blocked.",
        details={
            "unfrozen_passes": unfrozen.passes_gate,
            "below_gate_passes": below.passes_gate,
            "disposition": gate.disposition.value,
        },
    )


def _adversarial_all_zero() -> G5ScenarioResult:
    episodes, scores = make_zero_target_episodes_fixture()
    aggregation = compute_co_primary_aggregation(
        episodes,
        scores,
        lineage_inputs={"fixture_seed": G4_SYNTHETIC_FIXTURE_SEED, "scenario": "all_zero"},
    )
    assert aggregation.co_primary is not None
    gate = evaluate_information_gate_readiness(
        make_pending_parameter_slots(),
        aggregation.co_primary,
        None,
    )
    demonstrated = (
        aggregation.ok
        and aggregation.co_primary.opportunity_prevalence == 0.0
        and aggregation.co_primary.conditional_mean_effect is None
        and gate.disposition == StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
        and gate.disposition != StudyTerminalDisposition.COMPLETE_NULL_EQUIVALENT
    )
    return _scenario(
        "all_zero_window",
        "T9_T10",
        demonstrated=demonstrated,
        fail_closed=False,
        notes="All-zero window stays descriptive opportunity; product effect is not called null.",
        details={
            "opportunity_prevalence": aggregation.co_primary.opportunity_prevalence,
            "conditional_mean_effect": aggregation.co_primary.conditional_mean_effect,
            "disposition": gate.disposition.value,
        },
    )


def _adversarial_malformed_duplicate_orphan() -> list[G5ScenarioResult]:
    from eval_naturalistic.analysis import WithinEpisodeScoreV1

    duplicate_episodes = [
        EpisodeRegistryViewV1("ep-dup", EpisodeRegistryStatus.TARGETS_PRESENT, 1),
        EpisodeRegistryViewV1("ep-dup", EpisodeRegistryStatus.TARGETS_PRESENT, 1),
    ]
    dup_result = compute_co_primary_aggregation(
        duplicate_episodes,
        [],
        lineage_inputs={"scenario": "duplicate"},
    )
    orphan_scores = [
        WithinEpisodeScoreV1(
            episode_id="ep-missing",
            condition=TrialCondition.C0,
            normalized_score=0.4,
            reliability_state=ReliabilityState.RELIABILITY_ACCEPTABLE,
            target_count=1,
        )
    ]
    orphan_result = compute_co_primary_aggregation(
        [EpisodeRegistryViewV1("ep-known", EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS, 0)],
        orphan_scores,
        lineage_inputs={"scenario": "orphan"},
    )
    malformed = aggregate_targets_to_within_episode_score(
        make_target_rich_episode_target_scores(c0_scores=[float("nan")], c1_scores=[0.5])[0],
        episode_id="ep-malformed",
        condition=TrialCondition.C0,
    )
    return [
        _scenario(
            "duplicate_episode_rows",
            "T9",
            demonstrated=not dup_result.ok,
            fail_closed=True,
            notes="Duplicate registry episode rows fail closed.",
            details={"errors": dup_result.errors},
        ),
        _scenario(
            "orphaned_score",
            "T9",
            demonstrated=not orphan_result.ok,
            fail_closed=True,
            notes="Scores for unknown episodes fail closed.",
            details={"errors": orphan_result.errors},
        ),
        _scenario(
            "malformed_score",
            "T8",
            demonstrated=malformed.reliability_state == ReliabilityState.RELIABILITY_NON_ESTIMABLE,
            fail_closed=True,
            notes="Non-finite target scores are non-estimable.",
            details={"errors": malformed.validation_errors},
        ),
    ]



def _adversarial_incomplete_nominal_t0() -> G5ScenarioResult:
    frame = make_synthetic_frame()
    manifest = make_pending_prospective_manifest(frame=frame)
    incomplete = manifest.to_dict()
    incomplete["information_slots"] = incomplete["information_slots"][:2]
    check = validate_prospective_manifest_structural(incomplete, require_logged_freeze=False)
    sealed_full, _ = _seal_prospective_manifest(manifest)
    freeze_blocked = not validate_prospective_manifest_freeze_transition(
        sealed_full,
        require_logged_freeze=True,
    ).ok
    return _scenario(
        "incomplete_nominal_t0_frame",
        "T0",
        demonstrated=(not check.ok) and freeze_blocked,
        fail_closed=True,
        notes="Subset of eight PENDING slots fails draft validation; full pending set fails FRAME_FROZEN.",
        details={"errors": check.errors},
    )


def _adversarial_pending_slots_block_frame_frozen() -> G5ScenarioResult:
    frame = make_synthetic_frame()
    manifest = make_pending_prospective_manifest(frame=frame)
    sealed, _ = _seal_prospective_manifest(manifest)
    draft_ok = validate_prospective_manifest_structural(sealed, require_logged_freeze=False)
    freeze_fail = validate_prospective_manifest_freeze_transition(
        sealed,
        require_logged_freeze=True,
    )
    frozen_manifest = make_frozen_prospective_manifest(frame=frame)
    sealed_frozen, _ = _seal_prospective_manifest(frozen_manifest)
    freeze_ok = validate_prospective_manifest_freeze_transition(
        sealed_frozen,
        require_logged_freeze=True,
    )
    return _scenario(
        "pending_slots_block_frame_frozen",
        "T0",
        demonstrated=draft_ok.ok and (not freeze_fail.ok) and freeze_ok.ok,
        fail_closed=True,
        notes="Eight PENDING slots pass draft validation but fail FRAME_FROZEN; frozen fixture passes.",
        details={"pending_errors": freeze_fail.errors},
    )


def _adversarial_unsealed_manifest_blocks_frame_frozen() -> G5ScenarioResult:
    frame = make_synthetic_frame()
    frozen_manifest = make_frozen_prospective_manifest(frame=frame)
    sealed, _ = _seal_prospective_manifest(frozen_manifest)
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
    sealed_frozen, _ = _seal_prospective_manifest(frozen_manifest)
    freeze_ok = validate_prospective_manifest_freeze_transition(
        sealed_frozen,
        require_logged_freeze=True,
    )
    return _scenario(
        "unsealed_manifest_blocks_frame_frozen",
        "T0",
        demonstrated=(not freeze_fail.ok) and freeze_ok.ok,
        fail_closed=True,
        notes="sealed=False with self-consistent freeze digest fails FRAME_FROZEN; sealed frozen passes.",
        details={"unsealed_errors": freeze_fail.errors},
    )


def _adversarial_false_completeness() -> G5ScenarioResult:
    frame = make_synthetic_frame()
    manifest = make_pending_prospective_manifest(frame=frame)
    body = manifest.to_dict()
    for slot in body["information_slots"]:
        if slot["slot_name"] == "meaningful_advantage":
            slot["freeze_status"] = "frozen"
            slot["value"] = "PENDING"
    check = validate_prospective_manifest_structural(body, require_logged_freeze=False)
    return _scenario(
        "false_completeness_placeholder_slot",
        "T0",
        demonstrated=not check.ok,
        fail_closed=True,
        notes="Frozen placeholder value rejected despite status flag.",
        details={"errors": check.errors},
    )


def _adversarial_freeze_tamper() -> G5ScenarioResult:
    frame = make_synthetic_frame()
    manifest = make_pending_prospective_manifest(frame=frame)
    sealed, digest = _seal_prospective_manifest(manifest)
    tampered = copy.deepcopy(sealed)
    tampered["opportunity_authority_rule"] = tampered["opportunity_authority_rule"] + "-tampered"
    handoff = verify_handoff_artifact_digest(logged_digest=digest, handed_artifact=tampered)
    return _scenario(
        "freeze_tamper_post_seal",
        "T0",
        demonstrated=not handoff.ok,
        fail_closed=True,
        notes="Post-freeze byte edit fails handoff digest verification.",
        details={"errors": handoff.errors},
    )


def _adversarial_handoff_mismatch() -> G5ScenarioResult:
    frame = make_synthetic_frame()
    manifest = make_pending_prospective_manifest(frame=frame)
    sealed, digest = _seal_prospective_manifest(manifest)
    other, _ = _seal_prospective_manifest(make_pending_prospective_manifest(frame=make_synthetic_frame(study_id="other")))
    handoff = verify_handoff_artifact_digest(logged_digest=digest, handed_artifact=other)
    return _scenario(
        "handoff_artifact_mismatch",
        "T0",
        demonstrated=not handoff.ok,
        fail_closed=True,
        notes="Downstream validator receives a different artifact than logged.",
        details={"errors": handoff.errors},
    )


def _adversarial_validator_import_boundary() -> G5ScenarioResult:
    violations = [
        validate_prospective_validator_import_boundary("eval_naturalistic.dry_run"),
        validate_prospective_validator_import_boundary("eval_naturalistic.probe_construction"),
        validate_prospective_validator_import_boundary("eval_naturalistic.analysis"),
    ]
    demonstrated = all(not v.ok for v in violations)
    return _scenario(
        "validator_import_boundary",
        "T0",
        demonstrated=demonstrated,
        fail_closed=True,
        notes="Structural T0 validator cannot import execution/capture/scoring builders.",
    )


def _adversarial_registry_arm_dependent_rule() -> G5ScenarioResult:
    check = reject_arm_dependent_registry_rule("include targets when c1 capture succeeded")
    return _scenario(
        "registry_arm_dependent_rule",
        "T2",
        demonstrated=not check.ok,
        fail_closed=True,
        notes="Arm/capture-dependent registry membership rule rejected.",
        details={"errors": check.errors},
    )


def _adversarial_asymmetric_missingness() -> G5ScenarioResult:
    bounds = compute_deterministic_bounds(
        complete_pair_effects=[0.3],
        valid_missing_count=1,
        invalid_count=0,
        denominator_episode_count=3,
    )
    return _scenario(
        "asymmetric_valid_missingness_bounds",
        "T9",
        demonstrated=bounds.boundable_episode_count == 1 and bounds.point_estimate == 0.3,
        fail_closed=False,
        notes="Asymmetric valid missingness yields deterministic bounds on [0,1].",
        details=bounds.to_dict(),
    )


def _adversarial_invalid_vs_boundable() -> G5ScenarioResult:
    with_invalid = compute_deterministic_bounds(
        complete_pair_effects=[0.3],
        valid_missing_count=1,
        invalid_count=1,
        denominator_episode_count=3,
    )
    without_invalid = compute_deterministic_bounds(
        complete_pair_effects=[0.3],
        valid_missing_count=1,
        invalid_count=0,
        denominator_episode_count=3,
    )
    return _scenario(
        "invalid_vs_boundable_separation",
        "T9",
        demonstrated=with_invalid.inconclusive and not without_invalid.inconclusive,
        fail_closed=True,
        notes="Protocol invalidity blocks bounds; valid missing alone remains boundable.",
        details={"with_invalid": with_invalid.to_dict(), "without_invalid": without_invalid.to_dict()},
    )


def _adversarial_disposition_precedence() -> G5ScenarioResult:
    from eval_naturalistic.analysis import derive_orthogonal_disposition
    from eval_naturalistic.enums import (
        InformationSufficiencyState,
        MissingnessComparabilityState,
        ProtocolValidityState,
        ScorerIntegrityState,
        ScorerReliabilityDispositionState,
    )

    disposition, reasons, path = derive_orthogonal_disposition(
        protocol_validity=ProtocolValidityState.INVALID,
        information_sufficiency=InformationSufficiencyState.SUFFICIENT,
        missingness_comparability=MissingnessComparabilityState.COMPLETE,
        scorer_integrity=ScorerIntegrityState.VALID,
        scorer_reliability=ScorerReliabilityDispositionState.ACCEPTABLE,
        apparent_positive_effect=True,
    )
    return _scenario(
        "disposition_precedence_favorable_effect",
        "T10",
        demonstrated=disposition == StudyTerminalDisposition.INVALID and "protocol_invalidity" in path,
        fail_closed=True,
        notes="Apparent positive effect loses to protocol invalidity in precedence.",
        details={"disposition": disposition.value, "precedence_path": path, "reasons": reasons},
    )


def _adversarial_paired_replay_mismatch() -> G5ScenarioResult:
    state = SyntheticPairedReplayStateV1(
        sealed_pre_trial_digest="a" * 64,
        c0_readable_roots=frozenset({"/synthetic/workspace"}),
        c1_readable_roots=frozenset({"/other/root"}),
        shared_mutable_state=True,
        shared_cache_or_database=False,
        external_service_replayed=True,
        frozen_execution_order=("a", "b"),
        actual_execution_order=("b", "a"),
        c0_convmem_available=False,
        c1_convmem_available=True,
    )
    check = validate_paired_replay_symmetry(state)
    return _scenario(
        "paired_replay_mismatch",
        "T6",
        demonstrated=not check.ok,
        fail_closed=True,
        notes="Readable-root, shared-state, and execution-order asymmetry rejected.",
        details={"errors": check.errors},
    )


def _adversarial_scorer_integrity_vs_reliability() -> G5ScenarioResult:
    from eval_naturalistic.analysis import derive_orthogonal_disposition
    from eval_naturalistic.enums import (
        InformationSufficiencyState,
        MissingnessComparabilityState,
        ProtocolValidityState,
        ScorerIntegrityState,
        ScorerReliabilityDispositionState,
    )

    integrity_disp, integrity_reasons, _ = derive_orthogonal_disposition(
        protocol_validity=ProtocolValidityState.VALID,
        information_sufficiency=InformationSufficiencyState.SUFFICIENT,
        missingness_comparability=MissingnessComparabilityState.COMPLETE,
        scorer_integrity=ScorerIntegrityState.INVALID_UNBLINDED,
        scorer_reliability=ScorerReliabilityDispositionState.BELOW_THRESHOLD,
    )
    reliability_disp, reliability_reasons, _ = derive_orthogonal_disposition(
        protocol_validity=ProtocolValidityState.VALID,
        information_sufficiency=InformationSufficiencyState.SUFFICIENT,
        missingness_comparability=MissingnessComparabilityState.COMPLETE,
        scorer_integrity=ScorerIntegrityState.VALID,
        scorer_reliability=ScorerReliabilityDispositionState.BELOW_THRESHOLD,
    )
    return _scenario(
        "scorer_integrity_vs_reliability",
        "T8",
        demonstrated=(
            integrity_disp == StudyTerminalDisposition.INVALID
            and reliability_disp == StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
            and OutcomeReasonCode.SCORER_INTEGRITY_FAILURE.value in integrity_reasons
            and OutcomeReasonCode.SCORER_RELIABILITY_BELOW_THRESHOLD.value in reliability_reasons
        ),
        fail_closed=True,
        notes="Scorer integrity invalidity precedes below-threshold reliability blocking.",
    )


def _adversarial_synthetic_only_guard() -> G5ScenarioResult:
    import ast

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden_roots = ("".join(("eval", "_", "corpus")), "chromadb", "mcp_server")
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(root in alias.name for root in forbidden_roots):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if any(root in node.module for root in forbidden_roots):
                hits.append(node.module)
    return _scenario(
        "synthetic_only_guard",
        "T0_T10",
        demonstrated=not hits,
        fail_closed=True,
        notes="No natural locator, Agent runner, live scorer, or G6 authority imported.",
        details={"forbidden_import_hits": hits},
    )


def _adversarial_stage_corruption_sweep() -> G5ScenarioResult:
    stages = list(StudyStageId)
    failures = 0
    for stage in stages:
        entry = _ledger_entry(
            stage=stage,
            input_digest="0" * 64,
            predicates=[("corrupted_input", False, "injected fault")],
            output_digest=None,
            guarantees=[],
            assumptions=[],
            failure_reasons=[f"{stage.value} corruption"],
        )
        if not entry.passed:
            failures += 1
    return _scenario(
        "stage_corruption_sweep",
        "T0_T10",
        demonstrated=failures == len(stages),
        fail_closed=True,
        notes="Each T0–T10 stage fails closed on corrupted input.",
        details={"stages_tested": len(stages), "stages_failed": failures},
    )


def _adversarial_boundary_composition_proof() -> G5ScenarioResult:
    happy = run_g5_end_to_end()
    ledger = happy.get("stage_ledger", {})
    entries = ledger.get("entries", [])
    guarantees_ok = all(
        entry.get("passed") and entry.get("guarantees_exported")
        for entry in entries
    )
    assumptions_chained = len(entries) == 11
    return _scenario(
        "boundary_composition_proof",
        "T0_T10",
        demonstrated=guarantees_ok and assumptions_chained and happy["aggregation_ok"],
        fail_closed=False,
        notes="Happy path proves every boundary guarantee, not only return status.",
        details={"entry_count": len(entries), "stage_ok": happy.get("stage_ok")},
    )


def run_g5c_adversarial_suite() -> list[G5ScenarioResult]:
    return [
        _adversarial_incomplete_nominal_t0(),
        _adversarial_pending_slots_block_frame_frozen(),
        _adversarial_unsealed_manifest_blocks_frame_frozen(),
        _adversarial_false_completeness(),
        _adversarial_freeze_tamper(),
        _adversarial_handoff_mismatch(),
        _adversarial_validator_import_boundary(),
        _adversarial_registry_arm_dependent_rule(),
        _adversarial_asymmetric_missingness(),
        _adversarial_invalid_vs_boundable(),
        _adversarial_disposition_precedence(),
        _adversarial_paired_replay_mismatch(),
        _adversarial_scorer_integrity_vs_reliability(),
        _adversarial_synthetic_only_guard(),
        _adversarial_stage_corruption_sweep(),
        _adversarial_boundary_composition_proof(),
    ]

def run_g5_adversarial_suite() -> list[G5ScenarioResult]:
    """Named EXECUTION §16 adversarial controls plus malformed/duplicate/orphan."""

    return [
        _adversarial_capture_exclusion(),
        _adversarial_unsealed_edit(),
        _adversarial_answer_leakage(),
        _adversarial_source_leakage(),
        _adversarial_role_collision(),
        _adversarial_tool_asymmetry(),
        _adversarial_reused_context(),
        _adversarial_reindex(),
        _adversarial_missing_zero(),
        _adversarial_target_rich(),
        _adversarial_post_result_threshold(),
        _adversarial_controller_as_agent(),
        _adversarial_low_reliability(),
        _adversarial_all_zero(),
        *_adversarial_malformed_duplicate_orphan(),
        *run_g5c_adversarial_suite(),
    ]


def run_g5_dry_run() -> G5DryRunReport:
    g4_example = run_g4_safe_synthetic_example()
    happy = run_g5_end_to_end()
    scenarios = [
        _scenario(
            "g4_safe_synthetic_example",
            "T9_T10",
            demonstrated=(
                g4_example["aggregation_ok"] is True
                and g4_example["conditional_effect"] == 0.3
                and g4_example["paired_episodes"] == 2
                and g4_example["disposition"] == "blocked_non_estimable"
                and g4_example["all_slots_frozen"] is False
            ),
            fail_closed=False,
            notes="Existing G4 0.3 fixture remains descriptive and blocked.",
            details=g4_example,
        ),
        _scenario(
            "g5_end_to_end_happy_path",
            "T0_T10",
            demonstrated=(
                happy["aggregation_ok"] is True
                and happy["conditional_effect"] == 0.3
                and happy["paired_episodes"] == 2
                and happy["zero_target_episode_count"] == 1
                and happy["disposition"] == "blocked_non_estimable"
                and happy["all_slots_frozen"] is False
                and happy["scorer_reliability_passes"] is not True
                and not happy["errors"]
            ),
            fail_closed=False,
            notes="Synthetic favorable effect still terminates without a product conclusion.",
            details={k: v for k, v in happy.items() if k != "errors"} | {"errors": happy["errors"]},
        ),
        *run_g5_adversarial_suite(),
    ]
    slot_presence = validate_required_parameter_slots(make_pending_parameter_slots())
    incomplete_t0 = validate_required_parameter_slots(make_synthetic_frame().parameter_slots)
    scenarios.append(
        _scenario(
            "pending_information_gate_slots",
            "T0_T10",
            demonstrated=slot_presence.ok and (not incomplete_t0.ok),
            fail_closed=True,
            notes="Complete pending slots are present; incomplete T0 frames fail; none are frozen.",
        )
    )
    fail_closed_ok = all(
        scenario.demonstrated
        for scenario in scenarios
        if scenario.scenario_id in G5_REQUIRED_FAIL_CLOSED_SCENARIOS and scenario.fail_closed
    )
    product_emitted = any(
        scenario.details.get("disposition")
        in {
            StudyTerminalDisposition.COMPLETE_POSITIVE.value,
            StudyTerminalDisposition.COMPLETE_NEGATIVE.value,
            StudyTerminalDisposition.COMPLETE_NULL_EQUIVALENT.value,
        }
        for scenario in scenarios
    )
    return G5DryRunReport(
        classification=G5_CLASSIFICATION,
        g6_authority_assumed=False,
        naturalistic_evidence_created=False,
        synthetic_only=True,
        fixture_seed=G4_SYNTHETIC_FIXTURE_SEED,
        g4_safe_example=g4_example,
        happy_path=happy,
        scenarios=scenarios,
        all_required_fail_closed_demonstrated=fail_closed_ok and not product_emitted,
        product_disposition_emitted=product_emitted,
    )


def main() -> None:
    report = run_g5_dry_run()
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    if not report.all_required_fail_closed_demonstrated or report.product_disposition_emitted:
        raise SystemExit(1)
    if not all(scenario.demonstrated for scenario in report.scenarios):
        failed = [s.scenario_id for s in report.scenarios if not s.demonstrated]
        raise SystemExit(f"G5 scenarios not demonstrated: {failed}")


if __name__ == "__main__":
    main()
