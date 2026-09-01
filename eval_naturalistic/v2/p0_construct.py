"""P0 construct-freeze authority artifacts and independent parent resolution."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Protocol

from eval_naturalistic.base import (
    ArtifactHeaderV1,
    StructuralContractError,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
    strip_digest_metadata,
)
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.contracts import ARTIFACT_ID_PREFIX_V2, SCHEMA_NAMESPACE_V2

CONSTRUCT_FREEZE_SCHEMA = f"{SCHEMA_NAMESPACE_V2}/construct-freeze-manifest-v2"


@dataclass(frozen=True)
class ConstructFreezeManifestV2:
    """P0 construct-freeze authority artifact."""

    header: ArtifactHeaderV1
    construct_policy_digest: str
    study_id: str
    authorized_capture_issuer_grants: tuple[dict[str, str], ...]

    _FIELDS = {
        "header",
        "construct_policy_digest",
        "study_id",
        "authorized_capture_issuer_grants",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConstructFreezeManifestV2":
        data = _require_dict(data, "ConstructFreezeManifestV2")
        _require_no_unknown_props(data, cls._FIELDS, "ConstructFreezeManifestV2")
        header = ArtifactHeaderV1.from_dict(_require_dict(data["header"], "header"))
        if header.schema_version != CONSTRUCT_FREEZE_SCHEMA:
            raise StructuralContractError("construct freeze: wrong schema_version")
        grants_raw = data.get("authorized_capture_issuer_grants", [])
        if not isinstance(grants_raw, list):
            raise StructuralContractError("construct freeze: authorized_capture_issuer_grants must be a list")
        grants = tuple(_require_dict(item, "authorized_capture_issuer_grant") for item in grants_raw)
        return cls(
            header=header,
            construct_policy_digest=_require_str(data["construct_policy_digest"], "construct_policy_digest"),
            study_id=_require_str(data["study_id"], "study_id"),
            authorized_capture_issuer_grants=grants,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "construct_policy_digest": self.construct_policy_digest,
            "study_id": self.study_id,
            "authorized_capture_issuer_grants": [dict(grant) for grant in self.authorized_capture_issuer_grants],
        }


def _derive_artifact_id(*, schema: str, content_digest: str) -> str:
    kind = schema.rsplit("/", 1)[-1]
    return f"{ARTIFACT_ID_PREFIX_V2}{kind}_{content_digest}"


def _compute_content_digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_artifact_bytes(strip_digest_metadata(body))).hexdigest()


def seal_construct_freeze_manifest(
    *,
    construct_policy_digest: str,
    study_id: str,
    responsible_role: str,
    created_at: str,
    seal_time: str,
    authorized_capture_issuer_grants: tuple[dict[str, str], ...] = (),
) -> ConstructFreezeManifestV2:
    placeholder_header = ArtifactHeaderV1(
        artifact_id="pending",
        schema_version=CONSTRUCT_FREEZE_SCHEMA,
        parent_artifact_id=None,
        parent_digest=None,
        created_at=created_at,
        seal_time=None,
        responsible_role=responsible_role,
        content_digest=None,
        sealed=False,
    )
    body = {
        "header": placeholder_header.to_dict(),
        "construct_policy_digest": construct_policy_digest,
        "study_id": study_id,
        "authorized_capture_issuer_grants": [dict(grant) for grant in authorized_capture_issuer_grants],
    }
    content_digest = _compute_content_digest(body)
    artifact_id = _derive_artifact_id(schema=CONSTRUCT_FREEZE_SCHEMA, content_digest=content_digest)
    header = ArtifactHeaderV1(
        artifact_id=artifact_id,
        schema_version=CONSTRUCT_FREEZE_SCHEMA,
        parent_artifact_id=None,
        parent_digest=None,
        created_at=created_at,
        seal_time=seal_time,
        responsible_role=responsible_role,
        content_digest=content_digest,
        sealed=True,
    )
    manifest = ConstructFreezeManifestV2(
        header=header,
        construct_policy_digest=construct_policy_digest,
        study_id=study_id,
        authorized_capture_issuer_grants=authorized_capture_issuer_grants,
    )
    verify_construct_freeze_manifest(manifest)
    return manifest


def verify_construct_freeze_manifest(manifest: ConstructFreezeManifestV2) -> ConstructFreezeManifestV2:
    header = manifest.header
    if not header.sealed:
        raise StructuralContractError("construct freeze: sealed=false")
    if not header.seal_time:
        raise StructuralContractError("construct freeze: missing seal_time")
    if header.schema_version != CONSTRUCT_FREEZE_SCHEMA:
        raise StructuralContractError("construct freeze: wrong artifact kind")
    recomputed = _compute_content_digest(manifest.to_dict())
    if recomputed != header.content_digest:
        raise StructuralContractError("construct freeze: content digest mismatch")
    expected_id = _derive_artifact_id(schema=CONSTRUCT_FREEZE_SCHEMA, content_digest=recomputed)
    if header.artifact_id != expected_id:
        raise StructuralContractError("construct freeze: artifact ID mismatch")
    return manifest


class ConstructFreezeAuthorityRepository(Protocol):
    def resolve(
        self, *, artifact_id: str, content_digest: str
    ) -> ConstructFreezeManifestV2: ...


@dataclass
class InMemoryConstructFreezeRepository:
    """Candidate repository for P0 parents.

    Registration proves only artifact structure.  An authority source binding
    is deliberately kept outside serialized state and is required by the
    downstream authority paths.
    """

    _artifacts: dict[str, ConstructFreezeManifestV2]
    _authority_source: Any = field(default=None, repr=False, compare=False)

    def __init__(self, *, authority_source: Any = None) -> None:
        self._artifacts = {}
        self._authority_source = authority_source

    def authority_source(self) -> Any:
        """Return the host-supplied source binding, never serialized."""

        return self._authority_source

    def register(self, manifest: ConstructFreezeManifestV2) -> ConstructFreezeManifestV2:
        verified = verify_construct_freeze_manifest(manifest)
        digest = verified.header.content_digest
        if digest is None:
            raise StructuralContractError("construct freeze: missing digest on register")
        self._artifacts[digest] = verified
        return verified

    def manifests(self) -> tuple[ConstructFreezeManifestV2, ...]:
        return tuple(self._artifacts.values())

    def resolve(self, *, artifact_id: str, content_digest: str) -> ConstructFreezeManifestV2:
        manifest = self._artifacts.get(content_digest)
        if manifest is None:
            raise StructuralContractError("construct freeze parent not found in authority repository")
        if manifest.header.artifact_id != artifact_id:
            raise StructuralContractError("construct freeze parent artifact_id mismatch")
        return verify_construct_freeze_manifest(manifest)


def verify_construct_freeze_parent_binding(
    *,
    parent_kind: str,
    parent_artifact_id: str,
    parent_digest: str,
    construct_freeze_digest: str,
    repository: ConstructFreezeAuthorityRepository,
    authority_source: Any = None,
) -> ConstructFreezeManifestV2:
    if parent_kind != "construct_freeze":
        raise StructuralContractError(f"unknown immediate parent kind: {parent_kind}")
    if parent_digest != construct_freeze_digest:
        raise StructuralContractError("construct_freeze parent digest must match construct_freeze_digest")
    parent = repository.resolve(artifact_id=parent_artifact_id, content_digest=parent_digest)
    if parent.header.content_digest != parent_digest:
        raise StructuralContractError("resolved construct freeze digest mismatch")
    if authority_source is None:
        return parent
    from eval_naturalistic.v2.authority_substrate import validate_authority_source

    source = validate_authority_source(authority_source)
    trusted_parent = source.resolve_construct_freeze(
        artifact_id=parent_artifact_id,
        content_digest=parent_digest,
    )
    verified_trusted = verify_construct_freeze_manifest(trusted_parent)
    if verified_trusted.to_dict() != parent.to_dict():
        raise StructuralContractError(
            "construct freeze parent is not the independently resolved study authority"
        )
    return verified_trusted
