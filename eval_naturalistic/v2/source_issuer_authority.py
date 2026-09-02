"""Independently granted source-issuer capabilities anchored to construct freeze."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from eval_naturalistic.base import (
    StructuralContractError,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.p0_construct import ConstructFreezeManifestV2, verify_construct_freeze_manifest

_GRANT_TOKEN = object()


@dataclass(frozen=True)
class SourceIssuerGrantV2:
    """Study-authority grant — not caller-constructible."""

    issuer_identity: str
    source_system_id: str
    authority_scope_id: str
    grant_digest: str

    _FIELDS = {"issuer_identity", "source_system_id", "authority_scope_id", "grant_digest"}

    def __init__(
        self,
        *,
        _token: object,
        issuer_identity: str,
        source_system_id: str,
        authority_scope_id: str,
        grant_digest: str,
    ) -> None:
        if _token is not _GRANT_TOKEN:
            raise TypeError("SourceIssuerGrantV2 is only materialized from construct-freeze grants")
        object.__setattr__(self, "issuer_identity", issuer_identity)
        object.__setattr__(self, "source_system_id", source_system_id)
        object.__setattr__(self, "authority_scope_id", authority_scope_id)
        object.__setattr__(self, "grant_digest", grant_digest)

    def to_dict(self) -> dict[str, str]:
        return {
            "issuer_identity": self.issuer_identity,
            "source_system_id": self.source_system_id,
            "authority_scope_id": self.authority_scope_id,
            "grant_digest": self.grant_digest,
        }


def _digest_hex(value: Any, field_name: str) -> str:
    digest = _require_str(value, field_name)
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise StructuralContractError(
            f"{field_name}: must be 64-character lowercase SHA-256 hex digest"
        )
    return digest


def _grant_body(*, issuer_identity: str, source_system_id: str, authority_scope_id: str) -> dict[str, str]:
    return {
        "issuer_identity": issuer_identity,
        "source_system_id": source_system_id,
        "authority_scope_id": authority_scope_id,
    }


def _grant_from_record(record: dict[str, Any]) -> SourceIssuerGrantV2:
    record = _require_dict(record, "source issuer grant record")
    _require_no_unknown_props(
        record,
        SourceIssuerGrantV2._FIELDS,  # pylint: disable=protected-access
        "source issuer grant record",
    )
    issuer_identity = _require_str(record["issuer_identity"], "issuer_identity")
    source_system_id = _require_str(record["source_system_id"], "source_system_id")
    authority_scope_id = _require_str(record["authority_scope_id"], "authority_scope_id")
    grant_digest = _digest_hex(record["grant_digest"], "grant_digest")
    expected = hashlib.sha256(
        canonical_artifact_bytes(
            _grant_body(
                issuer_identity=issuer_identity,
                source_system_id=source_system_id,
                authority_scope_id=authority_scope_id,
            )
        )
    ).hexdigest()
    if expected != grant_digest:
        raise StructuralContractError("source issuer grant digest mismatch")
    return SourceIssuerGrantV2(
        _token=_GRANT_TOKEN,
        issuer_identity=issuer_identity,
        source_system_id=source_system_id,
        authority_scope_id=authority_scope_id,
        grant_digest=grant_digest,
    )


def build_source_issuer_grant_record(
    *,
    issuer_identity: str,
    source_system_id: str,
    authority_scope_id: str,
) -> dict[str, str]:
    """Build a portable grant record for inclusion in construct-freeze authority."""

    body = _grant_body(
        issuer_identity=issuer_identity,
        source_system_id=source_system_id,
        authority_scope_id=authority_scope_id,
    )
    return {
        **body,
        "grant_digest": hashlib.sha256(canonical_artifact_bytes(body)).hexdigest(),
    }


def reverify_source_issuer_grant(grant: SourceIssuerGrantV2) -> SourceIssuerGrantV2:
    expected = hashlib.sha256(
        canonical_artifact_bytes(
            _grant_body(
                issuer_identity=grant.issuer_identity,
                source_system_id=grant.source_system_id,
                authority_scope_id=grant.authority_scope_id,
            )
        )
    ).hexdigest()
    if expected != grant.grant_digest:
        raise StructuralContractError("source issuer grant digest mismatch")
    return grant


class SourceIssuerGrantRepository:
    """Issuer grants loaded from verified construct-freeze authority — not self-registered."""

    def __init__(
        self,
        *,
        construct_freeze_digest: str,
        grants: tuple[SourceIssuerGrantV2, ...],
    ) -> None:
        self._construct_freeze_digest = construct_freeze_digest
        self._grants = {
            (grant.issuer_identity, grant.source_system_id, grant.authority_scope_id): grant
            for grant in grants
        }

    @classmethod
    def from_construct_freeze(cls, manifest: ConstructFreezeManifestV2) -> "SourceIssuerGrantRepository":
        verified = verify_construct_freeze_manifest(manifest)
        digest = verified.header.content_digest
        if digest is None:
            raise StructuralContractError("construct freeze: missing digest for issuer grants")
        grants = tuple(_grant_from_record(record) for record in verified.authorized_capture_issuer_grants)
        return cls(construct_freeze_digest=digest, grants=grants)

    def construct_freeze_digest(self) -> str:
        return self._construct_freeze_digest

    def grants(self) -> tuple[SourceIssuerGrantV2, ...]:
        return tuple(self._grants.values())

    def resolve(
        self,
        *,
        issuer_identity: str,
        source_system_id: str,
        authority_scope_id: str,
    ) -> SourceIssuerGrantV2:
        grant = self._grants.get((issuer_identity, source_system_id, authority_scope_id))
        if grant is None:
            raise StructuralContractError("source issuer grant not found in authority repository")
        return reverify_source_issuer_grant(grant)

    def resolve_for_occurrence(self, occurrence: "OccurrenceReferenceV2") -> SourceIssuerGrantV2:
        from eval_naturalistic.v2.identity import OccurrenceReferenceV2

        if not isinstance(occurrence, OccurrenceReferenceV2):
            raise TypeError("resolve_for_occurrence requires OccurrenceReferenceV2")
        matches = [
            grant
            for grant in self._grants.values()
            if grant.source_system_id == occurrence.source_system_id
            and grant.authority_scope_id == occurrence.authority_scope_id
        ]
        if len(matches) != 1:
            raise StructuralContractError(
                "source issuer grant not uniquely resolved for occurrence scope"
            )
        return reverify_source_issuer_grant(matches[0])
