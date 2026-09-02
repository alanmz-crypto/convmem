"""P1 occurrence, physical, native, revision, and lineage identity types."""

# Identity records intentionally repeat field validation and serialization.
# pylint: disable=duplicate-code,too-many-instance-attributes

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from eval_naturalistic.base import (
    StructuralContractError,
    _enum_from_value,
    _require_dict,
    _require_no_unknown_props,
    _require_bool,
    _require_str,
)

OCCURRENCE_REFERENCE_FIELDS = frozenset(
    {
        "source_system_id",
        "tenant_or_realm_id",
        "authority_scope_id",
        "occurrence_namespace_id",
        "physical_source_instance_id",
        "native_id_namespace",
        "native_record_id",
        "source_revision_or_asof_id",
    }
)

VERIFICATION_ONLY_IDENTITY_FIELDS = frozenset(
    {
        "content_digest",
        "raw_record_digest",
        "canonical_content_digest",
        "locator",
        "source_path",
        "byte_offset",
        "ordinal",
        "line_number",
    }
)


def _require_digest(value: Any, field_name: str) -> str:
    digest = _require_str(value, field_name)
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise StructuralContractError(
            f"{field_name}: must be 64-character lowercase SHA-256 hex digest"
        )
    return digest


@dataclass(frozen=True)
class NativeRecordIdentityV2:
    """Native-ID namespace plus record identity within a source instance."""

    native_id_namespace: str
    native_record_id: str

    _FIELDS = {"native_id_namespace", "native_record_id"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NativeRecordIdentityV2":
        data = _require_dict(data, "NativeRecordIdentityV2")
        _require_no_unknown_props(data, cls._FIELDS, "NativeRecordIdentityV2")
        return cls(
            native_id_namespace=_require_str(
                data["native_id_namespace"], "native_id_namespace"
            ),
            native_record_id=_require_str(data["native_record_id"], "native_record_id"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "native_id_namespace": self.native_id_namespace,
            "native_record_id": self.native_record_id,
        }


@dataclass(frozen=True)
class OccurrenceReferenceV2:  # pylint: disable=too-many-instance-attributes
    """Typed occurrence identity — hashes and locators are never sufficient alone."""

    source_system_id: str
    tenant_or_realm_id: str
    authority_scope_id: str
    occurrence_namespace_id: str
    physical_source_instance_id: str
    native_id_namespace: str
    native_record_id: str
    source_revision_or_asof_id: str

    _FIELDS = OCCURRENCE_REFERENCE_FIELDS

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OccurrenceReferenceV2":
        data = _require_dict(data, "OccurrenceReferenceV2")
        _require_no_unknown_props(data, cls._FIELDS, "OccurrenceReferenceV2")
        _reject_verification_only_identity_payload(data, "OccurrenceReferenceV2")
        try:
            return cls(
                source_system_id=_require_str(data["source_system_id"], "source_system_id"),
                tenant_or_realm_id=_require_str(
                    data["tenant_or_realm_id"], "tenant_or_realm_id"
                ),
                authority_scope_id=_require_str(
                    data["authority_scope_id"], "authority_scope_id"
                ),
                occurrence_namespace_id=_require_str(
                    data["occurrence_namespace_id"], "occurrence_namespace_id"
                ),
                physical_source_instance_id=_require_str(
                    data["physical_source_instance_id"], "physical_source_instance_id"
                ),
                native_id_namespace=_require_str(
                    data["native_id_namespace"], "native_id_namespace"
                ),
                native_record_id=_require_str(data["native_record_id"], "native_record_id"),
                source_revision_or_asof_id=_require_str(
                    data["source_revision_or_asof_id"], "source_revision_or_asof_id"
                ),
            )
        except KeyError as exc:
            missing = exc.args[0]
            raise StructuralContractError(
                f"OccurrenceReferenceV2: missing required property '{missing}'"
            ) from exc

    def to_dict(self) -> dict[str, str]:
        return {
            "source_system_id": self.source_system_id,
            "tenant_or_realm_id": self.tenant_or_realm_id,
            "authority_scope_id": self.authority_scope_id,
            "occurrence_namespace_id": self.occurrence_namespace_id,
            "physical_source_instance_id": self.physical_source_instance_id,
            "native_id_namespace": self.native_id_namespace,
            "native_record_id": self.native_record_id,
            "source_revision_or_asof_id": self.source_revision_or_asof_id,
        }

    def identity_key(self) -> tuple[str, ...]:
        return tuple(self.to_dict()[field] for field in sorted(self._FIELDS))

    def native_record_identity(self) -> NativeRecordIdentityV2:
        return NativeRecordIdentityV2(
            native_id_namespace=self.native_id_namespace,
            native_record_id=self.native_record_id,
        )

    def same_occurrence_as(self, other: "OccurrenceReferenceV2") -> bool:
        return self.identity_key() == other.identity_key()


def occurrence_reference_from_fields(fields: dict[str, Any]) -> OccurrenceReferenceV2:
    """Build occurrence identity from the verified source-capture field set."""

    return OccurrenceReferenceV2(
        source_system_id=_require_str(fields["source_system_id"], "source_system_id"),
        tenant_or_realm_id=_require_str(fields["tenant_or_realm_id"], "tenant_or_realm_id"),
        authority_scope_id=_require_str(fields["authority_scope_id"], "authority_scope_id"),
        occurrence_namespace_id=_require_str(
            fields["occurrence_namespace_id"], "occurrence_namespace_id"
        ),
        physical_source_instance_id=_require_str(
            fields["physical_source_instance_id"], "physical_source_instance_id"
        ),
        native_id_namespace=_require_str(fields["native_id_namespace"], "native_id_namespace"),
        native_record_id=_require_str(fields["native_record_id"], "native_record_id"),
        source_revision_or_asof_id=_require_str(
            fields["source_revision_or_asof_id"], "source_revision_or_asof_id"
        ),
    )


@dataclass(frozen=True)
class PhysicalInstanceIdV2:
    """Physical/source instance identity — distinct from lineage continuity."""

    physical_instance_id: str

    _FIELDS = {"physical_instance_id"}

    @classmethod
    def from_value(cls, value: str) -> "PhysicalInstanceIdV2":
        return cls(physical_instance_id=_require_str(value, "physical_instance_id"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PhysicalInstanceIdV2":
        data = _require_dict(data, "PhysicalInstanceIdV2")
        _require_no_unknown_props(data, cls._FIELDS, "PhysicalInstanceIdV2")
        return cls.from_value(data["physical_instance_id"])

    def to_dict(self) -> dict[str, str]:
        return {"physical_instance_id": self.physical_instance_id}


@dataclass(frozen=True)
class RevisionOrAsofIdV2:
    """Revision or immutable as-of binding for mutable evidence."""

    revision_or_asof_id: str

    _FIELDS = {"revision_or_asof_id"}

    @classmethod
    def from_value(cls, value: str) -> "RevisionOrAsofIdV2":
        return cls(revision_or_asof_id=_require_str(value, "revision_or_asof_id"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RevisionOrAsofIdV2":
        data = _require_dict(data, "RevisionOrAsofIdV2")
        _require_no_unknown_props(data, cls._FIELDS, "RevisionOrAsofIdV2")
        return cls.from_value(data["revision_or_asof_id"])

    def to_dict(self) -> dict[str, str]:
        return {"revision_or_asof_id": self.revision_or_asof_id}


class LineageRelationKind(str, Enum):
    CLONE = "CLONE"
    RESTORE = "RESTORE"
    MIGRATION = "MIGRATION"
    IMPORT_EXPORT = "IMPORT_EXPORT"
    PROVIDER_EDIT = "PROVIDER_EDIT"
    DELETE_RECREATE = "DELETE_RECREATE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class LineageEdgeV2:  # pylint: disable=too-many-instance-attributes
    """Records continuity without collapsing physical-instance separation."""

    logical_lineage_id: str
    from_physical_instance_id: str
    to_physical_instance_id: str
    relation_kind: LineageRelationKind
    issuer_attested: bool
    child_occurrence_digest: str
    parent_occurrence_digest: str
    attestation_evidence_digest: str | None = None

    _FIELDS = {
        "logical_lineage_id",
        "from_physical_instance_id",
        "to_physical_instance_id",
        "relation_kind",
        "issuer_attested",
        "child_occurrence_digest",
        "parent_occurrence_digest",
        "attestation_evidence_digest",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageEdgeV2":
        data = _require_dict(data, "LineageEdgeV2")
        _require_no_unknown_props(data, cls._FIELDS, "LineageEdgeV2")
        issuer_attested = _require_bool(data["issuer_attested"], "issuer_attested")
        attestation = data.get("attestation_evidence_digest")
        if issuer_attested and attestation is None:
            raise StructuralContractError(
                "LineageEdgeV2: issuer_attested requires attestation_evidence_digest"
            )
        if not issuer_attested and attestation is not None:
            raise StructuralContractError(
                "LineageEdgeV2: attestation_evidence_digest requires issuer_attested=true"
            )
        return cls(
            logical_lineage_id=_require_str(data["logical_lineage_id"], "logical_lineage_id"),
            from_physical_instance_id=_require_str(
                data["from_physical_instance_id"], "from_physical_instance_id"
            ),
            to_physical_instance_id=_require_str(
                data["to_physical_instance_id"], "to_physical_instance_id"
            ),
            relation_kind=_enum_from_value(
                LineageRelationKind, data["relation_kind"], "relation_kind"
            ),
            issuer_attested=issuer_attested,
            child_occurrence_digest=digest_hex(
                data["child_occurrence_digest"], "child_occurrence_digest"
            ),
            parent_occurrence_digest=digest_hex(
                data["parent_occurrence_digest"], "parent_occurrence_digest"
            ),
            attestation_evidence_digest=(
                digest_hex(attestation, "attestation_evidence_digest")
                if attestation is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "logical_lineage_id": self.logical_lineage_id,
            "from_physical_instance_id": self.from_physical_instance_id,
            "to_physical_instance_id": self.to_physical_instance_id,
            "relation_kind": self.relation_kind.value,
            "issuer_attested": self.issuer_attested,
            "child_occurrence_digest": self.child_occurrence_digest,
            "parent_occurrence_digest": self.parent_occurrence_digest,
        }
        if self.attestation_evidence_digest is not None:
            out["attestation_evidence_digest"] = self.attestation_evidence_digest
        return out

    def preserves_physical_separation(self) -> bool:
        return self.from_physical_instance_id != self.to_physical_instance_id


@dataclass(frozen=True)
class EvidenceSnapshotIdV2:
    """Evidence snapshot identity — not occurrence authority on its own."""

    evidence_snapshot_id: str

    _FIELDS = {"evidence_snapshot_id"}

    @classmethod
    def from_value(cls, value: str) -> "EvidenceSnapshotIdV2":
        return cls(evidence_snapshot_id=_require_str(value, "evidence_snapshot_id"))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceSnapshotIdV2":
        data = _require_dict(data, "EvidenceSnapshotIdV2")
        _require_no_unknown_props(data, cls._FIELDS, "EvidenceSnapshotIdV2")
        return cls.from_value(data["evidence_snapshot_id"])

    def to_dict(self) -> dict[str, str]:
        return {"evidence_snapshot_id": self.evidence_snapshot_id}


def _reject_verification_only_identity_payload(
    data: dict[str, Any], label: str
) -> None:
    present = VERIFICATION_ONLY_IDENTITY_FIELDS & set(data)
    if present and not OCCURRENCE_REFERENCE_FIELDS.issubset(set(data)):
        names = ", ".join(sorted(present))
        raise StructuralContractError(
            f"{label}: verification-only fields ({names}) cannot establish occurrence identity"
        )


def reject_hash_or_locator_identity(data: dict[str, Any]) -> None:
    """Fail closed when identity is attempted from hash/locator/offset alone."""

    if not isinstance(data, dict):
        raise StructuralContractError("identity payload must be an object")
    has_verification = bool(VERIFICATION_ONLY_IDENTITY_FIELDS & set(data))
    has_occurrence = bool(OCCURRENCE_REFERENCE_FIELDS & set(data))
    if has_verification and not has_occurrence:
        raise StructuralContractError(
            "identity cannot be established from hash, locator, offset, or content equality alone"
        )
    if has_verification and has_occurrence:
        missing = sorted(OCCURRENCE_REFERENCE_FIELDS - set(data))
        if missing:
            raise StructuralContractError(
                "partial occurrence tuple with verification-only fields is incomplete identity"
            )


def digest_hex(value: str, field_name: str) -> str:
    """Public digest validator for commitment fields."""

    return _require_digest(value, field_name)
