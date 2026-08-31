"""G5 synthetic T5–T7 mechanical checks.

These validators exercise fail-closed environment, snapshot, fresh-session,
and controller contracts against synthetic packages only. They are not a live
Agent A/B runner, do not access ConvMem, and do not freeze G6 parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

from eval_naturalistic.base import NaturalisticValidation
from eval_naturalistic.enums import TrialCondition

SYNTHETIC_ORDINARY_TOOLS = frozenset({"read_file", "list_dir", "search_workspace"})
SYNTHETIC_ORDINARY_ROOTS = frozenset({"/synthetic/workspace"})
SYNTHETIC_MODEL_IDENTITY = "synthetic-model-001"
SYNTHETIC_BUDGET_IDENTITY = "synthetic-budget-001"
SYNTHETIC_STOPPING_IDENTITY = "synthetic-stop-001"


@dataclass(frozen=True)
class SyntheticConditionPackageV1:
    """Hermetic C0/C1 package used only by the G5 dry-run."""

    condition: TrialCondition
    tools: frozenset[str]
    readable_roots: frozenset[str]
    model_identity: str
    convmem_available: bool
    budget_identity: str
    stopping_identity: str


@dataclass(frozen=True)
class SyntheticSnapshotDiagnosisV1:
    """Hermetic T5 capture/snapshot diagnosis used only by the G5 dry-run."""

    natural_capture_only: bool
    target_directed_reindex: bool
    snapshot_mutable: bool
    registry_unchanged: bool


@dataclass(frozen=True)
class SyntheticTrialExecutionV1:  # pylint: disable=too-many-instance-attributes
    """Hermetic T7 trial package used only by the G5 dry-run."""

    trial_id: str
    condition: TrialCondition
    session_identity: str
    prior_session_mounted: bool
    controller_provided_answer: bool
    controller_provided_search: bool
    complete_trace: bool
    reused_agent_b_context: bool


def make_symmetric_condition_packages() -> tuple[SyntheticConditionPackageV1, SyntheticConditionPackageV1]:
    shared = {
        "tools": SYNTHETIC_ORDINARY_TOOLS,
        "readable_roots": SYNTHETIC_ORDINARY_ROOTS,
        "model_identity": SYNTHETIC_MODEL_IDENTITY,
        "budget_identity": SYNTHETIC_BUDGET_IDENTITY,
        "stopping_identity": SYNTHETIC_STOPPING_IDENTITY,
    }
    c0 = SyntheticConditionPackageV1(
        condition=TrialCondition.C0,
        convmem_available=False,
        **shared,
    )
    c1 = SyntheticConditionPackageV1(
        condition=TrialCondition.C1,
        convmem_available=True,
        **shared,
    )
    return c0, c1


def qualify_c0_c1_environment(
    c0: SyntheticConditionPackageV1,
    c1: SyntheticConditionPackageV1,
) -> NaturalisticValidation:
    """T6: packages must match except ConvMem availability."""

    errors: list[str] = []
    if c0.condition != TrialCondition.C0:
        errors.append("c0 package condition must be c0")
    if c1.condition != TrialCondition.C1:
        errors.append("c1 package condition must be c1")
    if c0.convmem_available:
        errors.append("c0 must not have ConvMem available")
    if not c1.convmem_available:
        errors.append("c1 must have ConvMem available")
    for attr in ("tools", "readable_roots", "model_identity", "budget_identity", "stopping_identity"):
        if getattr(c0, attr) != getattr(c1, attr):
            errors.append(f"c0/c1 {attr} asymmetry")
    return NaturalisticValidation(errors=errors)


def validate_natural_c1_snapshot(diagnosis: SyntheticSnapshotDiagnosisV1) -> NaturalisticValidation:
    """T5: reject target-directed recapture and mutable snapshots."""

    errors: list[str] = []
    if diagnosis.target_directed_reindex:
        errors.append("target-directed reindex rejected as non-natural")
    if diagnosis.snapshot_mutable:
        errors.append("mutable C1 snapshot rejected")
    if not diagnosis.natural_capture_only:
        errors.append("C1 snapshot must be natural-capture only")
    if not diagnosis.registry_unchanged:
        errors.append("registry must remain unchanged by capture diagnosis")
    return NaturalisticValidation(errors=errors)


def validate_trial_execution(
    trial: SyntheticTrialExecutionV1,
    *,
    seen_session_identities: frozenset[str],
) -> NaturalisticValidation:
    """T7: reject reused context, controller-as-agent, and incomplete traces."""

    errors: list[str] = []
    if trial.prior_session_mounted or trial.reused_agent_b_context:
        errors.append("reused Agent-B context / prior session mounted")
    if trial.session_identity in seen_session_identities:
        errors.append("session identity reused")
    if trial.controller_provided_answer:
        errors.append("controller provided an answer")
    if trial.controller_provided_search:
        errors.append("controller provided a search")
    if not trial.complete_trace:
        errors.append("incomplete trial trace")
    if not trial.session_identity.startswith("synthetic-session-"):
        errors.append("trial session identity must be synthetic")
    return NaturalisticValidation(errors=errors)


def validate_opportunity_roster(
    *,
    sealed_episode_ids: frozenset[str],
    aggregation_episode_ids: frozenset[str],
) -> NaturalisticValidation:
    """T9: opportunity file must retain every sealed episode, including zeros."""

    errors: list[str] = []
    missing = sorted(sealed_episode_ids - aggregation_episode_ids)
    extra = sorted(aggregation_episode_ids - sealed_episode_ids)
    if missing:
        errors.append("opportunity roster dropped sealed episodes: " + ", ".join(missing))
    if extra:
        errors.append("opportunity roster includes unknown episodes: " + ", ".join(extra))
    return NaturalisticValidation(errors=errors)
