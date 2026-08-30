"""Unforgeable possession tokens gating trusted R2b v2 authority transitions."""

from eval_corpus.r2b_v2._authority_vault import (  # noqa: F401
    AuthorityCapabilityError,
    AuthorityMintCapability,
    MintPhase,
    issue_census_capability,
    issue_lease_capability,
    issue_source_capability,
    reset_capabilities_for_tests,
    trust_class_for_gate_policy,
    verify_live_custodian_lock,
)

__all__ = [
    "AuthorityCapabilityError",
    "AuthorityMintCapability",
    "MintPhase",
    "issue_census_capability",
    "issue_lease_capability",
    "issue_source_capability",
    "reset_capabilities_for_tests",
    "trust_class_for_gate_policy",
    "verify_live_custodian_lock",
]
