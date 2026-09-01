"""Shared structural helpers for naturalistic study contracts."""

from __future__ import annotations

# Fixed durable-schema records intentionally exceed Pylint's generic class-size heuristic.
# pylint: disable=too-many-instance-attributes,duplicate-code

import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any


class StructuralContractError(ValueError):
    """Raised when raw data violates a naturalistic JSON contract."""


@dataclass
class NaturalisticValidation:
    """Fail-closed validation result shared across methodology stages."""

    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_status(self) -> str:
        return "pass" if self.ok else "fail"


def _enum_from_value(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (ValueError, TypeError) as exc:
        allowed = ", ".join(m.value for m in enum_type)
        raise StructuralContractError(
            f"{field_name}: invalid '{value}' (allowed: {allowed})"
        ) from exc


def _require_no_unknown_props(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise StructuralContractError(f"{label}: unknown JSON properties: {names}")


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StructuralContractError(f"{label}: expected object, got {type(value).__name__}")
    return value


def _require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise StructuralContractError(f"{field_name}: must be a non-empty string")
    return value


def _optional_str(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, field_name)




def _require_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise StructuralContractError(
        f"{field_name}: must be a JSON boolean, got {type(value).__name__}"
    )

def _require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise StructuralContractError(f"{field_name}: must be a list")
    return value


def _digest_excluded_keys() -> frozenset[str]:
    return frozenset({"content_digest", "seal_time", "sealed", "artifact_id"})


def strip_digest_metadata(body: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of artifact body suitable for content hashing."""

    stripped = copy.deepcopy(body)
    header = stripped.get("header")
    if isinstance(header, dict):
        for key in _digest_excluded_keys():
            header.pop(key, None)
    for key in _digest_excluded_keys():
        stripped.pop(key, None)
    return stripped


@dataclass
class ArtifactHeaderV1:
    """Immutable identity envelope shared by durable study artifacts."""

    artifact_id: str
    schema_version: str
    parent_artifact_id: str | None
    parent_digest: str | None
    created_at: str
    seal_time: str | None
    responsible_role: str
    content_digest: str | None
    sealed: bool

    _FIELDS = {
        "artifact_id",
        "schema_version",
        "parent_artifact_id",
        "parent_digest",
        "created_at",
        "seal_time",
        "responsible_role",
        "content_digest",
        "sealed",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactHeaderV1":
        data = _require_dict(data, "ArtifactHeaderV1")
        _require_no_unknown_props(data, cls._FIELDS, "ArtifactHeaderV1")
        try:
            artifact_id = _require_str(data["artifact_id"], "artifact_id")
            schema_version = _require_str(data["schema_version"], "schema_version")
            responsible_role = _require_str(data["responsible_role"], "responsible_role")
            created_at = _require_str(data["created_at"], "created_at")
        except KeyError as exc:
            missing = exc.args[0]
            raise StructuralContractError(
                f"ArtifactHeaderV1: missing required property '{missing}'"
            ) from exc
        sealed = data.get("sealed", False)
        if not isinstance(sealed, bool):
            raise StructuralContractError("ArtifactHeaderV1: sealed must be boolean")
        return cls(
            artifact_id=artifact_id,
            schema_version=schema_version,
            parent_artifact_id=_optional_str(data.get("parent_artifact_id"), "parent_artifact_id"),
            parent_digest=_optional_str(data.get("parent_digest"), "parent_digest"),
            created_at=created_at,
            seal_time=_optional_str(data.get("seal_time"), "seal_time"),
            responsible_role=responsible_role,
            content_digest=_optional_str(data.get("content_digest"), "content_digest"),
            sealed=sealed,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "artifact_id": self.artifact_id,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "responsible_role": self.responsible_role,
            "sealed": self.sealed,
        }
        if self.parent_artifact_id is not None:
            out["parent_artifact_id"] = self.parent_artifact_id
        if self.parent_digest is not None:
            out["parent_digest"] = self.parent_digest
        if self.seal_time is not None:
            out["seal_time"] = self.seal_time
        if self.content_digest is not None:
            out["content_digest"] = self.content_digest
        return out
