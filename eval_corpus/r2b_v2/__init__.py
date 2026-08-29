"""R2b v2 writer-gate quiescence — contract, state, lease, and coverage substrate."""

from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
)
from eval_corpus.r2b_v2.contract import (
    R2B_CONTRACT_VERSION,
    R2B_V2_REQUIRED_PROHIBITED,
    R2B_V2_REQUIRED_PROHIBITED_PREP,
    SERVICE_POLICY_V2,
    SOURCE_QUIESCENCE_POLICY_V2,
    detect_contract_version,
    make_r2b_v2_run_manifest_for_tests,
    validate_r2b_v2_manifest_schema,
    validate_v2_policy_fields,
)

__all__ = [
    "AuthorityState",
    "AuthorityStateError",
    "AuthorityStateMachine",
    "R2B_CONTRACT_VERSION",
    "R2B_V2_REQUIRED_PROHIBITED",
    "R2B_V2_REQUIRED_PROHIBITED_PREP",
    "SERVICE_POLICY_V2",
    "SOURCE_QUIESCENCE_POLICY_V2",
    "detect_contract_version",
    "make_r2b_v2_run_manifest_for_tests",
    "validate_r2b_v2_manifest_schema",
    "validate_v2_policy_fields",
]
