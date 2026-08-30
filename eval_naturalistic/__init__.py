"""Naturalistic ConvMem product-value study methodology substrate (G1).

Schema-only contracts, content-addressing, and validation for the accepted
artifact chain. No live study execution, adjudication, or statistical analysis.
"""

from eval_naturalistic.contracts import (
    ActionLatencyRecordV1,
    AgentBTraceV1,
    CensusSampleManifestV1,
    ConvMemCaptureStateV1,
    EpisodeFrameV1,
    EpisodeOutcomeV1,
    EpisodeRecordV1,
    ProbeManifestV1,
    RawEvidenceManifestV1,
    ScoringKeyV1,
    StudyAnalysisV1,
    TargetRegistryV1,
    TargetScoreV1,
    TrialIdentityV1,
)
from eval_naturalistic.contract_validate import (
    NaturalisticValidation,
    validate_artifact_chain,
    validate_capture_independent_registry,
    validate_parent_binding,
    validate_role_collision,
    validate_seal_immutability,
    validate_terminal_state_distinction,
)
from eval_naturalistic.digest import (
    ARTIFACT_ID_PREFIX,
    artifact_content_digest,
    make_artifact_id,
)
from eval_naturalistic.enums import (
    CaptureDiagnosticState,
    CensusMode,
    EligibilityDisposition,
    EpisodeDisposition,
    EpisodeRegistryStatus,
    LeakageReviewDisposition,
    ParameterFreezeStatus,
    ReliabilityState,
    SamplingMode,
    StudyTerminalDisposition,
    TrialCondition,
    TrialTerminalDisposition,
)

__all__ = [
    "ARTIFACT_ID_PREFIX",
    "ActionLatencyRecordV1",
    "AgentBTraceV1",
    "CensusMode",
    "CensusSampleManifestV1",
    "CaptureDiagnosticState",
    "ConvMemCaptureStateV1",
    "EligibilityDisposition",
    "EpisodeDisposition",
    "EpisodeFrameV1",
    "EpisodeOutcomeV1",
    "EpisodeRecordV1",
    "EpisodeRegistryStatus",
    "LeakageReviewDisposition",
    "NaturalisticValidation",
    "ParameterFreezeStatus",
    "ProbeManifestV1",
    "RawEvidenceManifestV1",
    "ReliabilityState",
    "SamplingMode",
    "ScoringKeyV1",
    "StudyAnalysisV1",
    "StudyTerminalDisposition",
    "TargetRegistryV1",
    "TargetScoreV1",
    "TrialCondition",
    "TrialIdentityV1",
    "TrialTerminalDisposition",
    "artifact_content_digest",
    "make_artifact_id",
    "validate_artifact_chain",
    "validate_capture_independent_registry",
    "validate_parent_binding",
    "validate_role_collision",
    "validate_seal_immutability",
    "validate_terminal_state_distinction",
]
