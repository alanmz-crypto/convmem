"""Terminal, eligibility, reliability, and lifecycle enums for naturalistic study artifacts."""

from __future__ import annotations

from enum import Enum


class StudyTerminalDisposition(str, Enum):
    INVALID = "invalid"
    DIAGNOSTIC = "diagnostic"
    BLOCKED_NON_ESTIMABLE = "blocked_non_estimable"
    COMPLETE_POSITIVE = "complete_positive"
    COMPLETE_NULL_EQUIVALENT = "complete_null_equivalent"
    COMPLETE_NEGATIVE = "complete_negative"


class EpisodeRegistryStatus(str, Enum):
    TARGETS_PRESENT = "targets_present"
    ZERO_ELIGIBLE_TARGETS = "zero_eligible_targets"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    TARGET_ADJUDICATION_AMBIGUOUS = "target_adjudication_ambiguous"
    TARGETS_PRESENT_BUT_NOT_EVALUABLE = "targets_present_but_not_evaluable"
    PROTOCOL_INVALID = "protocol_invalid"


class EpisodeDisposition(str, Enum):
    OBSERVED_COMPLETE = "observed_complete"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    INSTRUMENTATION_FAILURE = "instrumentation_failure"


class EligibilityDisposition(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    AMBIGUOUS_NON_EVALUABLE = "ambiguous_non_evaluable"


class ReliabilityState(str, Enum):
    RELIABILITY_ACCEPTABLE = "reliability_acceptable"
    RELIABILITY_SPARSE = "reliability_sparse"
    RELIABILITY_NON_ESTIMABLE = "reliability_non_estimable"
    RELIABILITY_NOT_APPLICABLE = "reliability_not_applicable"


class CaptureDiagnosticState(str, Enum):
    CAPTURED = "captured"
    ABSENT_FROM_CONVMEM = "absent_from_convmem"
    AMBIGUOUS_CAPTURE = "ambiguous_capture"
    MALFORMED_CAPTURE = "malformed_capture"


class ParameterFreezeStatus(str, Enum):
    PENDING = "pending"
    FROZEN = "frozen"
    NOT_APPLICABLE = "not_applicable"


class CensusMode(str, Enum):
    COMPLETE = "complete"
    SAMPLE = "sample"


class SamplingMode(str, Enum):
    WHOLE_EPISODE = "whole_episode"
    INDIVIDUAL_TARGET = "individual_target"
    NOT_APPLICABLE = "not_applicable"


class LeakageReviewDisposition(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class TrialCondition(str, Enum):
    C0 = "c0"
    C1 = "c1"


class TrialTerminalDisposition(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    PROTOCOL_VIOLATION = "protocol_violation"
    INSTRUMENTATION_FAILURE = "instrumentation_failure"


class EvidenceCompletenessState(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"


class AdmissibleSourceClass(str, Enum):
    TRANSCRIPT = "transcript"
    TOOL_OUTPUT = "tool_output"
    FILE = "file"
    REPOSITORY = "repository"
    GITHUB = "github"
    OTHER = "other"


class AdjudicationResolutionMethod(str, Enum):
    THIRD_ADJUDICATOR = "third_adjudicator"
    BLINDED_CONSENSUS = "blinded_consensus"


class RegistryBuildOutcome(str, Enum):
    SEALED = "sealed"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    ADJUDICATION_AMBIGUOUS = "adjudication_ambiguous"
    PROTOCOL_INVALID = "protocol_invalid"


class ProbeFamilyKind(str, Enum):
    CONTINUATION_RECOVERY = "continuation_recovery"
    DIRECT_RECALL = "direct_recall"


class ProbeBuildOutcome(str, Enum):
    SEALED = "sealed"
    ROLE_OR_PROVENANCE_REJECTED = "role_or_provenance_rejected"
    LEAKAGE_REJECTED = "leakage_rejected"
    PROTOCOL_INVALID = "protocol_invalid"


class LeakageCheckKind(str, Enum):
    ANSWER_LEAKAGE = "answer_leakage"
    CLOSE_PARAPHRASE = "close_paraphrase"
    SOURCE_PATH = "source_path"
    SOURCE_LOCATION = "source_location"
    TREATMENT_CONDITION = "treatment_condition"
    CONVMEM_RETRIEVAL = "convmem_retrieval"

class StudyStageId(str, Enum):
    """Individual T0–T10 methodology boundaries."""

    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"
    T6 = "T6"
    T7 = "T7"
    T8 = "T8"
    T9 = "T9"
    T10 = "T10"


class ProtocolValidityState(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNRESOLVED = "unresolved"


class InformationSufficiencyState(str, Enum):
    SUFFICIENT = "sufficient"
    SPARSE = "sparse"
    INSUFFICIENT = "insufficient"


class MissingnessComparabilityState(str, Enum):
    COMPLETE = "complete"
    BOUNDED = "bounded"
    INCONCLUSIVE_BOUNDS = "inconclusive_bounds"
    NOT_APPLICABLE = "not_applicable"


class ScorerIntegrityState(str, Enum):
    VALID = "valid"
    INVALID_UNBLINDED = "invalid_unblinded"
    UNRESOLVED = "unresolved"


class ScorerReliabilityDispositionState(str, Enum):
    ACCEPTABLE = "acceptable"
    BELOW_THRESHOLD = "below_threshold"
    NOT_APPLICABLE = "not_applicable"


class TrialEvidenceCaptureState(str, Enum):
    CAPTURED = "captured"
    NOT_CAPTURED = "not_captured"
    INVALID = "invalid"


class ScoreEvaluabilityState(str, Enum):
    EVALUABLE = "evaluable"
    NOT_EVALUABLE = "not_evaluable"
    INVALID = "invalid"


class OutcomeReasonCode(str, Enum):
    """Fixed synthetic reason vocabulary for G5C outcome axes."""

    VALID_MISSING_OUTCOME = "valid_missing_outcome"
    PROTOCOL_INVALID = "protocol_invalid"
    ENVIRONMENT_ASYMMETRY = "environment_asymmetry"
    ISOLATION_BREACH = "isolation_breach"
    LINEAGE_MISMATCH = "lineage_mismatch"
    REGISTRY_MUTATION = "registry_mutation"
    FREEZE_TAMPER = "freeze_tamper"
    HANDOFF_MISMATCH = "handoff_mismatch"
    SCORER_INTEGRITY_FAILURE = "scorer_integrity_failure"
    SCORER_RELIABILITY_BELOW_THRESHOLD = "scorer_reliability_below_threshold"
    DIAGNOSTIC_SECONDARY_DISAGREEMENT = "diagnostic_secondary_disagreement"
    TRIAL_EVIDENCE_NOT_CAPTURED = "trial_evidence_not_captured"
    SCORE_NOT_EVALUABLE = "score_not_evaluable"
    CONVMEM_NOT_CAPTURED = "convmem_not_captured"
    PLACEHOLDER_CONTENT = "placeholder_content"
    INCOMPLETE_PROSPECTIVE_MANIFEST = "incomplete_prospective_manifest"

