"""Curated JudgeBench model identity registry and alias normalization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class IdentityRegistryVersionError(ValueError):
    """Raised when the registry or one of its records is malformed."""


@dataclass
class IdentityRecord:
    canonical_id: str
    provider: str
    family: str | None
    aliases: list[str] = field(default_factory=list)
    alias_provenance: dict[str, str] = field(default_factory=dict)
    alias_metadata: dict[str, dict[str, Any]] = field(default_factory=dict)
    revision_digest: str | None = None
    quantization: str | None = None
    backend: str | None = None
    stronger_weight_claim: str | None = None


def _alias_key(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IdentityRegistryVersionError(f"{label} must be a non-empty string")
    return value.strip().lower()


def _provenance_map(
    raw: Any,
    *,
    identity: str,
    field_name: str,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    if raw is None:
        return {}, {}
    if not isinstance(raw, dict):
        raise IdentityRegistryVersionError(
            f"identity '{identity}' {field_name} must be an object"
        )
    provenance: dict[str, str] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for alias, value in raw.items():
        key = _alias_key(alias, f"identity '{identity}' {field_name} alias")
        if not isinstance(value, dict):
            raise IdentityRegistryVersionError(
                f"identity '{identity}' {field_name} alias '{alias}' "
                "must have an object provenance record"
            )
        kind = value.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise IdentityRegistryVersionError(
                f"identity '{identity}' {field_name} alias '{alias}' "
                "lacks a provenance kind"
            )
        if key in provenance:
            raise IdentityRegistryVersionError(
                f"identity '{identity}' {field_name} contains duplicate alias '{alias}'"
            )
        provenance[key] = kind.strip()
        metadata[key] = dict(value)
    return provenance, metadata


@dataclass
class IdentityRegistry:
    version: str
    records: dict[str, IdentityRecord]
    _alias_index: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IdentityRegistry:
        if not isinstance(data, dict):
            raise IdentityRegistryVersionError("identity registry must be an object")
        version = data.get("identity_registry_version")
        if not isinstance(version, str) or not version:
            raise IdentityRegistryVersionError("missing identity_registry_version")
        raw_ids = data.get("identities")
        if not isinstance(raw_ids, dict):
            raise IdentityRegistryVersionError("identities must be an object")

        records: dict[str, IdentityRecord] = {}
        alias_index: dict[str, str] = {}
        canonical_ids: set[str] = set()
        for record_id, item in raw_ids.items():
            if not isinstance(item, dict):
                raise IdentityRegistryVersionError(
                    f"identity '{record_id}' must be an object"
                )
            canonical = _alias_key(
                item.get("canonical_id") or record_id, "canonical_id"
            )
            if canonical in canonical_ids:
                raise IdentityRegistryVersionError(
                    f"duplicate canonical identity '{canonical}'"
                )
            canonical_ids.add(canonical)

            raw_aliases = item.get("aliases") or []
            if not isinstance(raw_aliases, list):
                raise IdentityRegistryVersionError(
                    f"identity '{record_id}' aliases must be a list"
                )
            aliases: list[str] = []
            local_public: set[str] = set()
            for raw_alias in raw_aliases:
                key = _alias_key(raw_alias, f"identity '{record_id}' alias")
                if key in local_public:
                    raise IdentityRegistryVersionError(
                        f"identity '{record_id}' contains duplicate alias '{raw_alias}'"
                    )
                local_public.add(key)
                aliases.append(str(raw_alias).strip())

            public_provenance, public_metadata = _provenance_map(
                item.get("alias_provenance"),
                identity=str(record_id),
                field_name="alias_provenance",
            )
            if not set(public_provenance).issubset(local_public):
                extra = sorted(set(public_provenance) - local_public)
                raise IdentityRegistryVersionError(
                    f"identity '{record_id}' provenance aliases are not public aliases: {extra}"
                )
            local_provenance, local_metadata = _provenance_map(
                item.get("provenance_aliases"),
                identity=str(record_id),
                field_name="provenance_aliases",
            )
            overlap = sorted(local_public & set(local_provenance))
            if overlap:
                raise IdentityRegistryVersionError(
                    f"identity '{record_id}' aliases have conflicting provenance: {overlap}"
                )

            record = IdentityRecord(
                canonical_id=canonical,
                provider=str(item.get("provider") or ""),
                family=(str(item["family"]) if item.get("family") else None),
                aliases=aliases,
                alias_provenance={**public_provenance, **local_provenance},
                alias_metadata={**public_metadata, **local_metadata},
                revision_digest=(
                    str(item["revision_digest"])
                    if isinstance(item.get("revision_digest"), str)
                    and item["revision_digest"]
                    else None
                ),
                quantization=(
                    str(item["quantization"])
                    if isinstance(item.get("quantization"), str)
                    and item["quantization"]
                    else None
                ),
                backend=(
                    str(item["backend"])
                    if isinstance(item.get("backend"), str) and item["backend"]
                    else None
                ),
                stronger_weight_claim=(
                    str(item["stronger_weight_claim"])
                    if isinstance(item.get("stronger_weight_claim"), str)
                    and item["stronger_weight_claim"]
                    else None
                ),
            )
            records[str(record_id)] = record

            def register(
                alias: str,
                *,
                allow_canonical_repeat: bool = False,
                canonical_id: str = canonical,
            ) -> None:
                key = _alias_key(alias, "alias")
                previous = alias_index.get(key)
                if previous is not None:
                    if allow_canonical_repeat and previous == canonical_id:
                        return
                    raise IdentityRegistryVersionError(
                        f"alias '{alias}' resolves to multiple or duplicate identities"
                    )
                alias_index[key] = canonical_id

            register(canonical)
            for alias in aliases:
                register(alias, allow_canonical_repeat=True)
            for alias in local_provenance:
                register(alias)

        return cls(version=version, records=records, _alias_index=alias_index)

    def resolve_alias(self, name: str) -> str | None:
        """Resolve a known spelling to its canonical identity."""
        if not name:
            return None
        return self._alias_index.get(str(name).strip().lower())

    def record_for(self, name: str) -> IdentityRecord | None:
        """Return the record for a canonical id or known alias."""
        canonical = self.resolve_alias(name)
        if canonical is None:
            return None
        return next(
            (
                record
                for record in self.records.values()
                if record.canonical_id == canonical
            ),
            None,
        )

    def alias_provenance(self, name: str) -> str | None:
        """Return only provenance explicitly present in the registry."""
        record = self.record_for(name)
        if record is None:
            return None
        key = str(name or "").strip().lower()
        if key == record.canonical_id.lower():
            return "canonical"
        return record.alias_provenance.get(key)

    def alias_metadata(self, name: str) -> dict[str, Any]:
        """Return a defensive copy of explicit alias provenance metadata."""
        record = self.record_for(name)
        if record is None:
            return {}
        return dict(record.alias_metadata.get(str(name or "").strip().lower(), {}))

    def normalize(self, names: list[str]) -> dict[str, str]:
        """Resolve names without guessing unresolved identities."""
        return {
            name: self.resolve_alias(name) or str(name).strip().lower()
            for name in names
        }


def load_identity_registry(path: Path | str) -> IdentityRegistry:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return IdentityRegistry.from_dict(data)
