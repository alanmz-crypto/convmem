"""Process-local trusted authority registry for R2b v2 lease and coverage proofs."""
# pylint: disable=duplicate-code
# __all__ intentionally overlaps _registry_mint (public façade vs private mint).

from eval_corpus.r2b_v2._registry_mint import (  # noqa: F401
    AuthorityHandle,
    AuthorityRegistryError,
    CoverageAuthorityRecord,
    DiagnosticMintTicket,
    LeaseAuthorityRecord,
    SourceAuthorityRecord,
    current_authority_epoch,
    invalidate_all_authority,
    invalidate_coverage_handle,
    invalidate_lease_handle,
    lookup_coverage_handle,
    lookup_custodian,
    lookup_lease_handle,
    lookup_source_handle,
    release_lease_handle,
)

__all__ = [
    "AuthorityHandle",
    "AuthorityRegistryError",
    "CoverageAuthorityRecord",
    "DiagnosticMintTicket",
    "LeaseAuthorityRecord",
    "SourceAuthorityRecord",
    "current_authority_epoch",
    "invalidate_all_authority",
    "invalidate_coverage_handle",
    "invalidate_lease_handle",
    "lookup_coverage_handle",
    "lookup_custodian",
    "lookup_lease_handle",
    "lookup_source_handle",
    "release_lease_handle",
]
