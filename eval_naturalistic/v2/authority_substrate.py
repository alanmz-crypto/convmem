"""External authority-substrate seams for Naturalistic V2.

Portable artifacts and in-memory candidate repositories can establish
representation and integrity.  They cannot establish study authority.  The
host that owns the study supplies an independent resolver implementing this
protocol; verification compares candidate repositories with that resolver and
never promotes a record solely because its digest is self-consistent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from eval_naturalistic.base import StructuralContractError

if TYPE_CHECKING:
    from eval_naturalistic.v2.capture_attestation import CaptureAttestationArtifactV2
    from eval_naturalistic.v2.p0_construct import ConstructFreezeManifestV2
    from eval_naturalistic.v2.source_authority import SealedSourceCapturePackageV2
    from eval_naturalistic.v2.authority_issuance import IssuanceAuthorityRecordV2
    from eval_naturalistic.v2.issuer_attestation_capability import (
        IssuerCaptureAttestationCapabilityV2,
    )


class IndependentAuthoritySourceV2(Protocol):
    """Read/resolve interface owned outside the claim graph.

    Implementations are supplied by the study authority.  Deliberately no
    constructor, record hydrator, or self-registration operation is provided
    here: a portable artifact must be resolved by this separately managed
    source before it can mint downstream authority.
    """

    def resolve_construct_freeze(
        self, *, artifact_id: str, content_digest: str
    ) -> "ConstructFreezeManifestV2": ...

    def resolve_issuer_capability(
        self,
        *,
        issuer_identity: str,
        issuer_grant_digest: str,
        construct_freeze_digest: str,
    ) -> "IssuerCaptureAttestationCapabilityV2": ...

    def resolve_capture_attestation(
        self, attestation_digest: str
    ) -> "CaptureAttestationArtifactV2": ...

    def resolve_source_capture(
        self, source_capture_digest: str
    ) -> "SealedSourceCapturePackageV2": ...

    def resolve_issuance(self, issuance_digest: str) -> "IssuanceAuthorityRecordV2": ...


_REQUIRED_SOURCE_METHODS = (
    "resolve_construct_freeze",
    "resolve_issuer_capability",
    "resolve_capture_attestation",
    "resolve_source_capture",
    "resolve_issuance",
)


def validate_authority_source(source: Any) -> IndependentAuthoritySourceV2:
    """Require a resolver with every authority-bearing lookup operation."""

    if source is None:
        raise StructuralContractError("independent authority source required")
    missing = [name for name in _REQUIRED_SOURCE_METHODS if not callable(getattr(source, name, None))]
    if missing:
        raise StructuralContractError(
            "independent authority source missing resolver(s): " + ", ".join(missing)
        )
    return source


def repository_authority_source(repository: Any) -> Any:
    """Read the non-serialized source binding from a repository, if present."""

    method = getattr(repository, "authority_source", None)
    return method() if callable(method) else None


def resolve_shared_authority_source(
    *,
    explicit: Any = None,
    repositories: tuple[Any, ...] = (),
) -> IndependentAuthoritySourceV2:
    """Resolve one external authority source shared by all candidate stores."""

    sources = [repository_authority_source(repo) for repo in repositories]
    present = [source for source in sources if source is not None]
    if explicit is not None:
        source = validate_authority_source(explicit)
        if any(candidate is not source for candidate in present):
            raise StructuralContractError("authority repositories are bound to different sources")
        return source
    if not present:
        raise StructuralContractError("authority repositories have no independent source binding")
    source = present[0]
    if any(candidate is not source for candidate in present):
        raise StructuralContractError("authority repositories are bound to different sources")
    return validate_authority_source(source)


def same_authority_object(left: Any, right: Any, *, message: str) -> None:
    """Reject a candidate object that differs from independently resolved data."""

    if left.to_dict() != right.to_dict():
        raise StructuralContractError(message)
