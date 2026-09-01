"""RoleAccess manifest and verified adjudication role context."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from eval_naturalistic.base import (
    StructuralContractError,
    _enum_from_value,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
)
from eval_naturalistic.v2.adjudication_view import AdjudicationEvidenceViewV1, VIEW_SCHEMA
from eval_naturalistic.v2.contracts import SCHEMA_NAMESPACE_V2

ROLE_ACCESS_SCHEMA = f"{SCHEMA_NAMESPACE_V2}/role-access-manifest-v2"


class AdjudicationRoleV2(str, Enum):
    ADJUDICATOR_A = "ADJUDICATOR_A"
    ADJUDICATOR_B = "ADJUDICATOR_B"
    DISAGREEMENT_RESOLVER = "DISAGREEMENT_RESOLVER"
    CONTROLLER = "CONTROLLER"


@dataclass(frozen=True)
class RoleAccessManifestV2:
    actor_id: str
    role: AdjudicationRoleV2
    manifest_digest: str
    authorized_view_type: str
    collision_forbidden_actor_ids: tuple[str, ...]

    _FIELDS = {
        "actor_id",
        "role",
        "manifest_digest",
        "authorized_view_type",
        "collision_forbidden_actor_ids",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoleAccessManifestV2":
        data = _require_dict(data, "RoleAccessManifestV2")
        _require_no_unknown_props(data, cls._FIELDS, "RoleAccessManifestV2")
        actors = data.get("collision_forbidden_actor_ids", [])
        if not isinstance(actors, list):
            raise StructuralContractError("collision_forbidden_actor_ids must be a list")
        return cls(
            actor_id=_require_str(data["actor_id"], "actor_id"),
            role=_enum_from_value(AdjudicationRoleV2, data["role"], "role"),
            manifest_digest=_require_str(data["manifest_digest"], "manifest_digest"),
            authorized_view_type=_require_str(
                data["authorized_view_type"], "authorized_view_type"
            ),
            collision_forbidden_actor_ids=tuple(
                _require_str(item, "collision_forbidden_actor_ids[]") for item in actors
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "role": self.role.value,
            "manifest_digest": self.manifest_digest,
            "authorized_view_type": self.authorized_view_type,
            "collision_forbidden_actor_ids": list(self.collision_forbidden_actor_ids),
        }


@dataclass(frozen=True)
class VerifiedRoleContextV2:
    """Explicit verified context required by the adjudication facade."""

    manifest: RoleAccessManifestV2
    bound_view_digest: str
    verification_digest: str

    _FIELDS = {"manifest", "bound_view_digest", "verification_digest"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerifiedRoleContextV2":
        data = _require_dict(data, "VerifiedRoleContextV2")
        _require_no_unknown_props(data, cls._FIELDS, "VerifiedRoleContextV2")
        return cls(
            manifest=RoleAccessManifestV2.from_dict(
                _require_dict(data["manifest"], "manifest")
            ),
            bound_view_digest=_require_str(data["bound_view_digest"], "bound_view_digest"),
            verification_digest=_require_str(data["verification_digest"], "verification_digest"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "bound_view_digest": self.bound_view_digest,
            "verification_digest": self.verification_digest,
        }


def role_access_manifest_digest(manifest: RoleAccessManifestV2) -> str:
    return hashlib.sha256(
        json.dumps(manifest.to_dict(), sort_keys=True).encode()
    ).hexdigest()


def verify_role_context(
    context: VerifiedRoleContextV2,
    *,
    view: AdjudicationEvidenceViewV1,
    expected_verification_digest: str | None = None,
) -> None:
    if context.manifest.authorized_view_type != VIEW_SCHEMA:
        raise StructuralContractError("role context authorized view type mismatch")
    if context.bound_view_digest != view.content_digest():
        raise StructuralContractError("stale role context: view digest mismatch")
    expected = expected_verification_digest or _compute_verification_digest(
        context.manifest, view
    )
    if context.verification_digest != expected:
        raise StructuralContractError("forged or stale role context verification digest")


def _compute_verification_digest(
    manifest: RoleAccessManifestV2,
    view: AdjudicationEvidenceViewV1,
) -> str:
    payload = {
        "manifest_digest": role_access_manifest_digest(manifest),
        "view_digest": view.content_digest(),
        "role": manifest.role.value,
        "actor_id": manifest.actor_id,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def create_verified_role_context(
    manifest: RoleAccessManifestV2,
    *,
    view: AdjudicationEvidenceViewV1,
) -> VerifiedRoleContextV2:
    if manifest.authorized_view_type != VIEW_SCHEMA:
        raise StructuralContractError("manifest not authorized for adjudication view")
    verification_digest = _compute_verification_digest(manifest, view)
    return VerifiedRoleContextV2(
        manifest=manifest,
        bound_view_digest=view.content_digest(),
        verification_digest=verification_digest,
    )


def validate_role_collision(
    contexts: tuple[VerifiedRoleContextV2, ...],
) -> None:
    seen: set[str] = set()
    for context in contexts:
        actor = context.manifest.actor_id
        if actor in seen:
            raise StructuralContractError("role collision: duplicate actor identity")
        seen.add(actor)
        for forbidden in context.manifest.collision_forbidden_actor_ids:
            if forbidden in seen:
                raise StructuralContractError("role collision constraint violated")
