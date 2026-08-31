"""P2 opaque resolver contracts and result states."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from eval_naturalistic.base import (
    ArtifactHeaderV1,
    StructuralContractError,
    _enum_from_value,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.v2.adapters.capability import CapabilityVectorV2
from eval_naturalistic.v2.contracts import SCHEMA_NAMESPACE_V2, _header_from, _header_to
from eval_naturalistic.v2.evidence import SourcePresenceV2
from eval_naturalistic.v2.identity import digest_hex


class ResolverResultV2(str, Enum):
    """Locked source_resolution_contract.resolver_result domain."""

    EXACT_MATCH = "EXACT_MATCH"
    SUMMARY_ONLY = "SUMMARY_ONLY"
    NO_MATCH = "NO_MATCH"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    ERROR = "ERROR"


class ResolutionDetailV2(str, Enum):
    """Orthogonal ERROR/detail states — not additional resolver_result authority."""

    UNSUPPORTED_SOURCE_PROFILE = "UNSUPPORTED_SOURCE_PROFILE"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    WRONG_SOURCE_INSTANCE = "WRONG_SOURCE_INSTANCE"
    WRONG_REVISION_ASOF = "WRONG_REVISION_ASOF"
    HASH_MISMATCH = "HASH_MISMATCH"
    INPUT_MUTATION = "INPUT_MUTATION"
    IMPLEMENTATION_DIGEST_MISMATCH = "IMPLEMENTATION_DIGEST_MISMATCH"
    OUTPUT_DIGEST_MISMATCH = "OUTPUT_DIGEST_MISMATCH"
    LOCATOR_HASH_FALLBACK_REJECTED = "LOCATOR_HASH_FALLBACK_REJECTED"
    RESOLVER_INTEGRITY_ERROR = "RESOLVER_INTEGRITY_ERROR"
    TARGET_AUTHORITY_FORBIDDEN = "TARGET_AUTHORITY_FORBIDDEN"


@dataclass(frozen=True)
class OpaqueResolverManifestV2:
    """P2 resolver authority artifact — hidden from adjudicators until V2-04 join."""

    header: ArtifactHeaderV1
    evidence_seal_digest: str
    resolver_implementation_digest: str
    resolver_input_digest: str
    resolver_result: ResolverResultV2
    capability_vector: CapabilityVectorV2
    resolver_output_digest: str
    preserved_source_presence: SourcePresenceV2
    resolution_detail: ResolutionDetailV2 | None = None

    SCHEMA = f"{SCHEMA_NAMESPACE_V2}/opaque-resolver-manifest-v2"
    _FIELDS = {
        "header",
        "evidence_seal_digest",
        "resolver_implementation_digest",
        "resolver_input_digest",
        "resolver_result",
        "capability_vector",
        "resolver_output_digest",
        "preserved_source_presence",
        "resolution_detail",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpaqueResolverManifestV2":
        data = _require_dict(data, "OpaqueResolverManifestV2")
        _require_no_unknown_props(data, cls._FIELDS, "OpaqueResolverManifestV2")
        detail = data.get("resolution_detail")
        return cls(
            header=_header_from(data),
            evidence_seal_digest=digest_hex(data["evidence_seal_digest"], "evidence_seal_digest"),
            resolver_implementation_digest=digest_hex(
                data["resolver_implementation_digest"], "resolver_implementation_digest"
            ),
            resolver_input_digest=digest_hex(data["resolver_input_digest"], "resolver_input_digest"),
            resolver_result=_enum_from_value(
                ResolverResultV2, data["resolver_result"], "resolver_result"
            ),
            capability_vector=CapabilityVectorV2.from_dict(
                _require_dict(data["capability_vector"], "capability_vector")
            ),
            resolver_output_digest=digest_hex(
                data["resolver_output_digest"], "resolver_output_digest"
            ),
            preserved_source_presence=SourcePresenceV2(
                _require_str(data["preserved_source_presence"], "preserved_source_presence")
            ),
            resolution_detail=(
                ResolutionDetailV2(_require_str(detail, "resolution_detail"))
                if detail is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "header": _header_to(self.header),
            "evidence_seal_digest": self.evidence_seal_digest,
            "resolver_implementation_digest": self.resolver_implementation_digest,
            "resolver_input_digest": self.resolver_input_digest,
            "resolver_result": self.resolver_result.value,
            "capability_vector": self.capability_vector.to_dict(),
            "resolver_output_digest": self.resolver_output_digest,
            "preserved_source_presence": self.preserved_source_presence.value,
        }
        if self.resolution_detail is not None:
            out["resolution_detail"] = self.resolution_detail.value
        return out

    def authority_body_for_digest(self) -> dict[str, Any]:
        return {
            "evidence_seal_digest": self.evidence_seal_digest,
            "resolver_implementation_digest": self.resolver_implementation_digest,
            "resolver_input_digest": self.resolver_input_digest,
            "resolver_result": self.resolver_result.value,
            "capability_vector": self.capability_vector.to_dict(),
            "preserved_source_presence": self.preserved_source_presence.value,
            "resolution_detail": (
                self.resolution_detail.value if self.resolution_detail is not None else None
            ),
        }
