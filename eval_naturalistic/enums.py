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
