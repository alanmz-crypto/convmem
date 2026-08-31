"""Evidence adapter profile contract — separate from legacy ingest parsers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from eval_naturalistic.base import (
    StructuralContractError,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.v2.adapters.capability import CapabilityVectorV2
from eval_naturalistic.v2.adapters.reduction import (
    CapabilityDecisionV2,
    CapabilityUseV2,
    evaluate_capability_for_use,
)
from eval_naturalistic.v2.evidence import (
    ConditionNeutralEvidenceAvailabilityV2,
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
    normalized_reported_presence,
)


class NativeRecordIdentityMode(str, Enum):
    PROVIDER_NATIVE = "provider_native"
    DERIVED = "derived"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ProfileSemanticsV2:
    """Explicit adapter semantics — silent omission is prohibited."""

    acceptance_rejection: str
    ordering: str
    duplicate_handling: str
    authorship: str
    chronology_timezone: str
    reply_structure: str
    validity_currentness: str
    unknown_extension_fields: str
    attachments_blobs: str
    tool_referenced_material: str
    omissions_truncation: str
    canonicalization_profile: str
    source_instance_binding: str
    native_record_identity: str
    revision_asof: str
    raw_envelope_recovery: str
    replay_asof: str

    _FIELDS = {
        "acceptance_rejection",
        "ordering",
        "duplicate_handling",
        "authorship",
        "chronology_timezone",
        "reply_structure",
        "validity_currentness",
        "unknown_extension_fields",
        "attachments_blobs",
        "tool_referenced_material",
        "omissions_truncation",
        "canonicalization_profile",
        "source_instance_binding",
        "native_record_identity",
        "revision_asof",
        "raw_envelope_recovery",
        "replay_asof",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileSemanticsV2":
        data = _require_dict(data, "ProfileSemanticsV2")
        _require_no_unknown_props(data, cls._FIELDS, "ProfileSemanticsV2")
        try:
            return cls(**{field: _require_str(data[field], field) for field in cls._FIELDS})
        except KeyError as exc:
            missing = exc.args[0]
            raise StructuralContractError(
                f"ProfileSemanticsV2: missing required property '{missing}'"
            ) from exc

    def to_dict(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in sorted(self._FIELDS)}


@dataclass(frozen=True)
class EvidenceAdapterProfileV2:
    """V2 evidence-specific adapter profile — does not mutate legacy parse() outputs."""

    profile_id: str
    legacy_format: str | None
    adapter_implementation_digest: str
    capability_vector: CapabilityVectorV2
    native_record_identity_mode: NativeRecordIdentityMode
    semantics: ProfileSemanticsV2
    declared_omissions: tuple[str, ...]
    default_availability: ConditionNeutralEvidenceAvailabilityV2
    schema_version: str | None = None

    _FIELDS = {
        "profile_id",
        "legacy_format",
        "adapter_implementation_digest",
        "capability_vector",
        "native_record_identity_mode",
        "semantics",
        "declared_omissions",
        "default_availability",
        "schema_version",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceAdapterProfileV2":
        data = _require_dict(data, "EvidenceAdapterProfileV2")
        _require_no_unknown_props(data, cls._FIELDS, "EvidenceAdapterProfileV2")
        legacy = data.get("legacy_format")
        if legacy is not None:
            legacy = _require_str(legacy, "legacy_format")
        schema_version = data.get("schema_version")
        if schema_version is not None:
            schema_version = _require_str(schema_version, "schema_version")
        omissions = data.get("declared_omissions", [])
        if not isinstance(omissions, list):
            raise StructuralContractError("declared_omissions must be a list")
        return cls(
            profile_id=_require_str(data["profile_id"], "profile_id"),
            legacy_format=legacy,
            adapter_implementation_digest=_require_str(
                data["adapter_implementation_digest"], "adapter_implementation_digest"
            ),
            capability_vector=CapabilityVectorV2.from_dict(
                _require_dict(data["capability_vector"], "capability_vector")
            ),
            native_record_identity_mode=NativeRecordIdentityMode(
                _require_str(data["native_record_identity_mode"], "native_record_identity_mode")
            ),
            semantics=ProfileSemanticsV2.from_dict(
                _require_dict(data["semantics"], "semantics")
            ),
            declared_omissions=tuple(_require_str(item, "declared_omissions[]") for item in omissions),
            default_availability=ConditionNeutralEvidenceAvailabilityV2.from_dict(
                _require_dict(data["default_availability"], "default_availability")
            ),
            schema_version=schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "profile_id": self.profile_id,
            "legacy_format": self.legacy_format,
            "adapter_implementation_digest": self.adapter_implementation_digest,
            "capability_vector": self.capability_vector.to_dict(),
            "native_record_identity_mode": self.native_record_identity_mode.value,
            "semantics": self.semantics.to_dict(),
            "declared_omissions": list(self.declared_omissions),
            "default_availability": self.default_availability.to_dict(),
        }
        if self.schema_version is not None:
            out["schema_version"] = self.schema_version
        return out

    def validate(self) -> None:
        if (
            self.native_record_identity_mode == NativeRecordIdentityMode.PROVIDER_NATIVE
            and self.capability_vector.occurrence_identity.value
            not in {"NATIVE_UNIQUE", "ISSUER_ATTESTED"}
        ):
            raise StructuralContractError(
                "provider-native label requires occurrence_identity NATIVE_UNIQUE or ISSUER_ATTESTED"
            )
        if (
            self.native_record_identity_mode == NativeRecordIdentityMode.DERIVED
            and self.capability_vector.occurrence_identity.value == "NATIVE_UNIQUE"
        ):
            raise StructuralContractError(
                "derived identity mode cannot claim NATIVE_UNIQUE occurrence authority"
            )
        normalized_reported_presence(self.default_availability)
        if not self.semantics.omissions_truncation.strip():
            raise StructuralContractError("omissions_truncation must be explicitly declared")

    def capability_for_use(self, use: CapabilityUseV2) -> CapabilityDecisionV2:
        return evaluate_capability_for_use(self.capability_vector, use)

    def with_capability_vector(self, vector: CapabilityVectorV2) -> "EvidenceAdapterProfileV2":
        return EvidenceAdapterProfileV2(
            profile_id=self.profile_id,
            legacy_format=self.legacy_format,
            adapter_implementation_digest=self.adapter_implementation_digest,
            capability_vector=vector,
            native_record_identity_mode=self.native_record_identity_mode,
            semantics=self.semantics,
            declared_omissions=self.declared_omissions,
            default_availability=self.default_availability,
            schema_version=self.schema_version,
        )


def profile_implementation_digest(profile_id: str, *, schema_version: str | None = None) -> str:
    """Deterministic synthetic implementation digest for a profile declaration."""

    payload = {"profile_id": profile_id, "schema_version": schema_version}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
