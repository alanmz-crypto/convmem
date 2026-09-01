"""Issuer possession capabilities — separate from construct-freeze grant metadata."""

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
from eval_naturalistic.v2.source_issuer_authority import SourceIssuerGrantV2, reverify_source_issuer_grant

_CAPABILITY_TOKEN = object()


@dataclass(frozen=True)
class IssuerCaptureAttestationCapabilityV2:
    """Authority-bearing issuer capability — not construct-freeze grant metadata."""

    issuer_identity: str
    issuer_grant_digest: str
    construct_freeze_digest: str
    capability_digest: str

    _FIELDS = {
        "issuer_identity",
        "issuer_grant_digest",
        "construct_freeze_digest",
        "capability_digest",
    }

    def __init__(
        self,
        *,
        _token: object,
        issuer_identity: str,
        issuer_grant_digest: str,
        construct_freeze_digest: str,
        capability_digest: str,
    ) -> None:
        if _token is not _CAPABILITY_TOKEN:
            raise TypeError(
                "IssuerCaptureAttestationCapabilityV2 is only materialized from study issuer authority"
            )
        object.__setattr__(self, "issuer_identity", issuer_identity)
        object.__setattr__(self, "issuer_grant_digest", issuer_grant_digest)
        object.__setattr__(self, "construct_freeze_digest", construct_freeze_digest)
        object.__setattr__(self, "capability_digest", capability_digest)

    def to_dict(self) -> dict[str, str]:
        return {
            "issuer_identity": self.issuer_identity,
            "issuer_grant_digest": self.issuer_grant_digest,
            "construct_freeze_digest": self.construct_freeze_digest,
            "capability_digest": self.capability_digest,
        }


def _digest_hex(value: Any, field_name: str) -> str:
    digest = _require_str(value, field_name)
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise StructuralContractError(
            f"{field_name}: must be 64-character lowercase SHA-256 hex digest"
        )
    return digest


def _capability_body(
    *,
    issuer_identity: str,
    issuer_grant_digest: str,
    construct_freeze_digest: str,
) -> dict[str, str]:
    return {
        "capability_kind": "issuer_capture_attestation_v2",
        "issuer_identity": issuer_identity,
        "issuer_grant_digest": issuer_grant_digest,
        "construct_freeze_digest": construct_freeze_digest,
    }


def build_issuer_capture_attestation_capability_record(
    *,
    issuer_identity: str,
    issuer_grant_digest: str,
    construct_freeze_digest: str,
) -> dict[str, str]:
    """Build a portable capability record for study issuer-authority substrate."""

    body = _capability_body(
        issuer_identity=issuer_identity,
        issuer_grant_digest=issuer_grant_digest,
        construct_freeze_digest=construct_freeze_digest,
    )
    return {
        "issuer_identity": issuer_identity,
        "issuer_grant_digest": issuer_grant_digest,
        "construct_freeze_digest": construct_freeze_digest,
        "capability_digest": hashlib.sha256(canonical_artifact_bytes(body)).hexdigest(),
    }


def _capability_from_record(record: dict[str, Any]) -> IssuerCaptureAttestationCapabilityV2:
    record = _require_dict(record, "issuer capture attestation capability record")
    _require_no_unknown_props(
        record, IssuerCaptureAttestationCapabilityV2._FIELDS, "issuer capture attestation capability record"
    )
    issuer_identity = _require_str(record["issuer_identity"], "issuer_identity")
    issuer_grant_digest = _digest_hex(record["issuer_grant_digest"], "issuer_grant_digest")
    construct_freeze_digest = _digest_hex(record["construct_freeze_digest"], "construct_freeze_digest")
    capability_digest = _digest_hex(record["capability_digest"], "capability_digest")
    expected = hashlib.sha256(
        canonical_artifact_bytes(
            _capability_body(
                issuer_identity=issuer_identity,
                issuer_grant_digest=issuer_grant_digest,
                construct_freeze_digest=construct_freeze_digest,
            )
        )
    ).hexdigest()
    if expected != capability_digest:
        raise StructuralContractError("issuer capture attestation capability digest mismatch")
    return IssuerCaptureAttestationCapabilityV2(
        _token=_CAPABILITY_TOKEN,
        issuer_identity=issuer_identity,
        issuer_grant_digest=issuer_grant_digest,
        construct_freeze_digest=construct_freeze_digest,
        capability_digest=capability_digest,
    )


def mint_issuer_capture_attestation_capability(
    grant: SourceIssuerGrantV2,
    *,
    construct_freeze_digest: str,
) -> IssuerCaptureAttestationCapabilityV2:
    """Mint issuer capability at study bootstrap — not from construct-freeze grant records."""

    verified_grant = reverify_source_issuer_grant(grant)
    construct_digest = _digest_hex(construct_freeze_digest, "construct_freeze_digest")
    capability_digest = hashlib.sha256(
        canonical_artifact_bytes(
            _capability_body(
                issuer_identity=verified_grant.issuer_identity,
                issuer_grant_digest=verified_grant.grant_digest,
                construct_freeze_digest=construct_digest,
            )
        )
    ).hexdigest()
    return IssuerCaptureAttestationCapabilityV2(
        _token=_CAPABILITY_TOKEN,
        issuer_identity=verified_grant.issuer_identity,
        issuer_grant_digest=verified_grant.grant_digest,
        construct_freeze_digest=construct_digest,
        capability_digest=capability_digest,
    )


def reverify_issuer_capture_attestation_capability(
    capability: IssuerCaptureAttestationCapabilityV2,
) -> IssuerCaptureAttestationCapabilityV2:
    expected = hashlib.sha256(
        canonical_artifact_bytes(
            _capability_body(
                issuer_identity=capability.issuer_identity,
                issuer_grant_digest=capability.issuer_grant_digest,
                construct_freeze_digest=capability.construct_freeze_digest,
            )
        )
    ).hexdigest()
    if expected != capability.capability_digest:
        raise StructuralContractError("issuer capture attestation capability digest mismatch")
    return capability


class IssuerCaptureAttestationCapabilityRepository:
    """Pre-issued issuer capabilities — not self-registered or grant-derived at mint time."""

    def __init__(
        self,
        *,
        construct_freeze_digest: str,
        capabilities: tuple[IssuerCaptureAttestationCapabilityV2, ...],
    ) -> None:
        self._construct_freeze_digest = construct_freeze_digest
        self._capabilities = {
            (cap.issuer_identity, cap.issuer_grant_digest): cap for cap in capabilities
        }

    @classmethod
    def from_capabilities(
        cls,
        *,
        construct_freeze_digest: str,
        capabilities: tuple[IssuerCaptureAttestationCapabilityV2, ...],
    ) -> "IssuerCaptureAttestationCapabilityRepository":
        digest = _digest_hex(construct_freeze_digest, "construct_freeze_digest")
        verified = tuple(
            reverify_issuer_capture_attestation_capability(cap) for cap in capabilities
        )
        for cap in verified:
            if cap.construct_freeze_digest != digest:
                raise StructuralContractError(
                    "issuer capture attestation capability: construct-freeze digest mismatch"
                )
        return cls(construct_freeze_digest=digest, capabilities=verified)

    @classmethod
    def from_capability_records(
        cls,
        *,
        construct_freeze_digest: str,
        records: tuple[dict[str, str], ...],
    ) -> "IssuerCaptureAttestationCapabilityRepository":
        capabilities = tuple(_capability_from_record(record) for record in records)
        return cls.from_capabilities(
            construct_freeze_digest=construct_freeze_digest,
            capabilities=capabilities,
        )

    def construct_freeze_digest(self) -> str:
        return self._construct_freeze_digest

    def capabilities(self) -> tuple[IssuerCaptureAttestationCapabilityV2, ...]:
        return tuple(self._capabilities.values())

    def resolve(
        self,
        *,
        issuer_identity: str,
        issuer_grant_digest: str,
    ) -> IssuerCaptureAttestationCapabilityV2:
        capability = self._capabilities.get((issuer_identity, issuer_grant_digest))
        if capability is None:
            raise StructuralContractError(
                "issuer capture attestation capability not found in authority repository"
            )
        return reverify_issuer_capture_attestation_capability(capability)
