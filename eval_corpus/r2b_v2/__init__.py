"""R2b v2 writer-gate quiescence — contract, state, lease, and coverage substrate."""

from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
    new_authority_state_machine,
    observe_authority_state,
    reconstruct_state_machine,
    transition_to_coverage_proven,
    transition_to_q_held,
)
from eval_corpus.r2b_v2.contract import (
    R2B_CONTRACT_VERSION,
    R2B_V2_REQUIRED_PROHIBITED,
    R2B_V2_REQUIRED_PROHIBITED_PREP,
    SERVICE_POLICY_V2,
    SOURCE_QUIESCENCE_POLICY_V2,
    _contract_version_errors,
    detect_contract_version,
    make_r2b_v2_run_manifest_for_tests,
    validate_r2b_v2_manifest_schema,
    validate_v2_policy_fields,
)
from eval_corpus.r2b_v2.coverage.inventory import REQUIRED_ROUTE_CATEGORIES
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageHoldClass,
    CoverageProofError,
    DiagnosticCoverageResult,
    TrustedCoverageProof,
    mint_trusted_coverage_proof,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.gate_policy import GatePolicy, production_gate_policy, test_gate_policy
from eval_corpus.r2b_v2.lease import (
    R2bQuiescenceLease,
    R2bQuiescenceLeaseError,
    acquire_r2b_quiescence_lease,
    verify_r2b_quiescence_lease,
)

__all__ = [
    "AuthorityState",
    "AuthorityStateError",
    "AuthorityStateMachine",
    "CoverageHoldClass",
    "CoverageProofError",
    "DiagnosticCoverageResult",
    "GatePolicy",
    "R2B_CONTRACT_VERSION",
    "R2B_V2_REQUIRED_PROHIBITED",
    "R2B_V2_REQUIRED_PROHIBITED_PREP",
    "R2bQuiescenceLease",
    "R2bQuiescenceLeaseError",
    "REQUIRED_ROUTE_CATEGORIES",
    "SERVICE_POLICY_V2",
    "SOURCE_QUIESCENCE_POLICY_V2",
    "TrustedCoverageProof",
    "_contract_version_errors",
    "acquire_r2b_quiescence_lease",
    "detect_contract_version",
    "make_r2b_v2_run_manifest_for_tests",
    "mint_trusted_coverage_proof",
    "new_authority_state_machine",
    "observe_authority_state",
    "production_gate_policy",
    "prove_zero_bypass_coverage",
    "reconstruct_state_machine",
    "source_authority_from_lease_and_coverage",
    "test_gate_policy",
    "transition_to_coverage_proven",
    "transition_to_q_held",
    "validate_r2b_v2_manifest_schema",
    "validate_v2_policy_fields",
    "verify_r2b_quiescence_lease",
]
