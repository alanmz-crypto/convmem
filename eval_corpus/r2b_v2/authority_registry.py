"""Process-local trusted authority registry for R2b v2 lease and coverage proofs.

Public re-exports are derived from ``_registry_mint.__all__`` so pylint R0801
duplicate-code debt stays off the public mint boundary.
"""
# pylint: disable=unused-import

from eval_corpus.r2b_v2 import _registry_mint
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

_MINT_ONLY_EXPORTS = frozenset(
    {
        "AuthorityMintCapability",
        "compose_and_mint_source_authority",
        "finalize_diagnostic_and_mint_coverage",
        "mint_lease_handle",
        "register_diagnostic_ticket",
    }
)

__all__ = [name for name in _registry_mint.__all__ if name not in _MINT_ONLY_EXPORTS]
