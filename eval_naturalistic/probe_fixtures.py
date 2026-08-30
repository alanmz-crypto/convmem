"""G3 hermetic fixtures for probe construction and leakage review tests."""

from __future__ import annotations

# Repeated fixture setup is intentionally explicit so each synthetic contract is legible.
# pylint: disable=duplicate-code

from eval_naturalistic.base import ArtifactHeaderV1
from eval_naturalistic.contracts import (
    ProbeAuthorProvenanceV1,
    ScoringKeyContentV1,
    TargetRecordV1,
    TargetRegistryV1,
)
from eval_naturalistic.enums import ProbeFamilyKind
from eval_naturalistic.fixtures import (
    make_synthetic_census,
    make_synthetic_episode,
    make_synthetic_evidence,
    make_synthetic_frame,
    make_synthetic_registry,
)
from eval_naturalistic.probe_construction import (
    ProbeConstructionConfigV1,
    ProbeDraftV1,
    build_sealed_probe_bundle,
    compute_text_digest,
)


CONTINUATION_PROBE_TEXT = (
    "Continue the workflow from where the session left off. "
    "What is the next concrete action the agent should take?"
)
DIRECT_RECALL_PROBE_TEXT = (
    "Without searching external sources, state the key fact established earlier."
)
VALID_GROUND_TRUTH = "deploy staging configuration after review"
LEAK_REVIEWER_ID = "leak-reviewer-001"
PROBE_AUTHOR_ID = "probe-author-001"


def make_default_provenance(*, target_id: str = "tgt-001") -> ProbeAuthorProvenanceV1:
    return ProbeAuthorProvenanceV1(
        probe_author_id=PROBE_AUTHOR_ID,
        target_id=target_id,
        access_recorded=True,
        treatment_blind=True,
        c0_c1_result_blind=True,
        capture_retrieval_blind=True,
        permitted_views=["sealed_target_record", "minimum_raw_context"],
        forbidden_reference_tokens=[],
    )


def make_scoring_key_content_draft(
    *,
    probe_id: str = "probe-001",
    target_id: str = "tgt-001",
    ground_truth: str = VALID_GROUND_TRUTH,
) -> ScoringKeyContentV1:
    return ScoringKeyContentV1(
        header=ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=ScoringKeyContentV1.SCHEMA,
            parent_artifact_id=None,
            parent_digest=None,
            created_at="2026-08-30T02:00:00Z",
            seal_time=None,
            responsible_role="scorer_partition",
            content_digest=None,
            sealed=False,
        ),
        probe_id=probe_id,
        target_id=target_id,
        ground_truth_value=ground_truth,
        rubric_version="rubric-v1",
    )


def make_probe_draft(
    *,
    target: TargetRecordV1,
    probe_text: str = CONTINUATION_PROBE_TEXT,
    probe_family_kind: ProbeFamilyKind = ProbeFamilyKind.CONTINUATION_RECOVERY,
    probe_author_id: str = PROBE_AUTHOR_ID,
    provenance: ProbeAuthorProvenanceV1 | None = None,
    ground_truth: str = VALID_GROUND_TRUTH,
) -> ProbeDraftV1:
    return ProbeDraftV1(
        probe_id="probe-001",
        target_id=target.target_id,
        episode_id=target.episode_id,
        probe_text=probe_text,
        probe_family_kind=probe_family_kind,
        probe_author_id=probe_author_id,
        permitted_context_digest=compute_text_digest("synthetic-permitted-context"),
        author_provenance=provenance or make_default_provenance(target_id=target.target_id),
        scoring_key_content=make_scoring_key_content_draft(
            target_id=target.target_id,
            ground_truth=ground_truth,
        ),
    )


def make_default_probe_config() -> ProbeConstructionConfigV1:
    return ProbeConstructionConfigV1(
        probe_family_id="family-continuation-001",
        scoring_key_partition_identity="partition-scorer-001",
        seal_time="2026-08-30T02:00:00Z",
    )


def make_sealed_registry_and_census() -> tuple[TargetRegistryV1, object]:
    frame = make_synthetic_frame()
    episode = make_synthetic_episode(frame=frame)
    evidence = make_synthetic_evidence(episode=episode)
    registry = make_synthetic_registry(evidence=evidence)
    census = make_synthetic_census(registry=registry)
    return registry, census


def build_valid_probe_bundle():
    registry, census = make_sealed_registry_and_census()
    target = registry.targets[0]
    draft = make_probe_draft(target=target)
    return build_sealed_probe_bundle(
        registry=registry,
        census=census,
        target=target,
        draft=draft,
        leakage_reviewer_id=LEAK_REVIEWER_ID,
        config=make_default_probe_config(),
    )
