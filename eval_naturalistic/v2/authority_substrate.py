"""External authority-substrate seams for Naturalistic V2.

Portable artifacts and in-memory candidate repositories can establish
representation and integrity.  They cannot establish study authority.  The
host that owns the study supplies an independent resolver implementing this
protocol; verification compares candidate repositories with that resolver and
never promotes a record solely because its digest is self-consistent.
"""

from __future__ import annotations

import hashlib
import hmac
import inspect
import os
import weakref
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

# The resolver protocol is intentionally structural so a host integration can
# implement it without inheriting from this package. Structural compatibility
# is not authority, however. Host provisioning records the exact resolver
# object in a private registry and requires an out-of-band bootstrap secret
# supplied by the host before this module is imported. A weak reference also
# avoids retaining authority after a host integration has been torn down.
_HOST_BOOTSTRAP_SECRET_ENV = "CONVMEM_NATURALISTIC_V2_AUTHORITY_BOOTSTRAP_SECRET"


def _secret_digest(secret: bytes | str | None) -> bytes | None:
    if secret is None:
        return None
    if isinstance(secret, str):
        secret = secret.encode("utf-8")
    if not isinstance(secret, bytes):
        return None
    if not secret:
        return None
    return hashlib.sha256(secret).digest()


# Only the host process can establish this value before importing the V2
# authority substrate. It is retained as a digest so the raw bootstrap secret
# is not held by this module after import.
_HOST_BOOTSTRAP_SECRET_DIGEST = _secret_digest(
    os.environ.get(_HOST_BOOTSTRAP_SECRET_ENV)
)


class _HostProvisionedSourceRegistry:
    """Host registry whose mutation path is internal and credential-gated."""

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        self._entries: dict[int, weakref.ReferenceType[Any]] = {}

    def _trusted_frame_active(self, allowed_names: frozenset[str]) -> bool:
        frame = inspect.currentframe()
        while frame is not None:
            if (
                frame.f_globals.get("__name__") == __name__
                and frame.f_code.co_name in allowed_names
            ):
                return True
            frame = frame.f_back
        return False

    def register(self, source_id: int, reference: weakref.ReferenceType[Any]) -> None:
        if not self._trusted_frame_active(
            frozenset({"_provision_host_authority_source"})
        ):
            raise StructuralContractError(
                "host authority registry mutation is internal only"
            )
        self._entries[source_id] = reference

    def lookup(self, source_id: int) -> weakref.ReferenceType[Any] | None:
        return self._entries.get(source_id)

    def discard(self, source_id: int, reference: weakref.ReferenceType[Any]) -> None:
        if not self._trusted_frame_active(frozenset({"_forget_host_source"})):
            raise StructuralContractError(
                "host authority registry mutation is internal only"
            )
        if self._entries.get(source_id) is reference:
            del self._entries[source_id]


_HOST_PROVISIONED_SOURCES = _HostProvisionedSourceRegistry()


def _validate_source_shape(source: Any) -> None:
    missing = [
        name for name in _REQUIRED_SOURCE_METHODS
        if not callable(getattr(source, name, None))
    ]
    if missing:
        raise StructuralContractError(
            "independent authority source missing resolver(s): " + ", ".join(missing)
        )


def _forget_host_source(source_id: int, reference: weakref.ReferenceType[Any]) -> None:
    if _HOST_PROVISIONED_SOURCES.lookup(source_id) is reference:
        _HOST_PROVISIONED_SOURCES.discard(source_id, reference)


def _provision_host_authority_source(
    source: Any,
    *,
    bootstrap_secret: bytes | str,
) -> IndependentAuthoritySourceV2:
    """Register a resolver from the host-owned integration boundary.

    The host process supplies ``bootstrap_secret`` from outside the claimant
    graph. Importing this helper or constructing a resolver-shaped object does
    not provide that credential. Authority paths accept only this exact
    provisioned object identity after the host credential is verified.
    """

    if source is None:
        raise StructuralContractError("independent authority source required")
    expected = _HOST_BOOTSTRAP_SECRET_DIGEST
    actual = _secret_digest(bootstrap_secret)
    if expected is None:
        raise StructuralContractError("host authority bootstrap is unavailable")
    if actual is None or not hmac.compare_digest(actual, expected):
        raise StructuralContractError("host authority bootstrap credential rejected")
    _validate_source_shape(source)
    try:
        source_id = id(source)
        reference = weakref.ref(
            source,
            lambda ref: _forget_host_source(source_id, ref),
        )
    except TypeError as exc:
        raise StructuralContractError(
            "independent authority source must be host-provisioned and weak-referenceable"
        ) from exc
    _HOST_PROVISIONED_SOURCES.register(source_id, reference)
    return source


def validate_authority_source(source: Any) -> IndependentAuthoritySourceV2:
    """Require a host-provisioned resolver with every authority lookup."""

    if source is None:
        raise StructuralContractError("independent authority source required")
    _validate_source_shape(source)
    provisioned = _HOST_PROVISIONED_SOURCES.lookup(id(source))
    if provisioned is None or provisioned() is not source:
        raise StructuralContractError(
            "independent authority source must be provisioned by the host authority"
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
