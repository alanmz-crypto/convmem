"""Identity registry loader + alias normalization (JudgeBench slice S7).

Loads and normalizes a curated versioned identity registry (JSON). It resolves
known aliases to their canonical identity *only* - it never performs model
identity classification. Use ``eval_model_identity`` for independence class.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class IdentityRegistryVersionError(ValueError):
    """Raised when the registry version is missing/unexpected."""


@dataclass
class IdentityRecord:
    canonical_id: str
    provider: str
    family: str | None
    aliases: list[str] = field(default_factory=list)


@dataclass
class IdentityRegistry:
    version: str
    records: dict[str, IdentityRecord]
    _alias_index: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IdentityRegistry":
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
        for rec_id, item in raw_ids.items():
            if not isinstance(item, dict):
                raise IdentityRegistryVersionError(
                    f"identity '{rec_id}' must be an object"
                )
            canonical = str(item.get("canonical_id") or rec_id)
            aliases = [str(a) for a in (item.get("aliases") or [])]
            records[rec_id] = IdentityRecord(
                canonical_id=canonical,
                provider=str(item.get("provider") or ""),
                family=(str(item["family"]) if item.get("family") else None),
                aliases=aliases,
            )
            alias_index[canonical] = canonical
            for alias in aliases:
                alias_index[alias.lower()] = canonical
        return cls(version=version, records=records, _alias_index=alias_index)

    def resolve_alias(self, name: str) -> str | None:
        """Normalize any known alias (or canonical id) to its canonical id.

        Registration keyed by ``name.lower()`` for forgiving alias matching;
        returns the canonical id, or None if the name is not in the registry.
        """
        if not name:
            return None
        return self._alias_index.get(str(name).lower())

    def normalize(self, names: list[str]) -> dict[str, str]:
        """Resolve every distinct input name to its canonical id.

        Names not present in the registry are mapped to themselves (unresolved)
        so downstream identity work can see at a glance which identities are
        known vs unknown. Never infers family/cross_family.
        """
        out: dict[str, str] = {}
        for name in names:
            canonical = self.resolve_alias(name)
            if canonical is None:
                out[name] = name.lower()
            else:
                out[name] = canonical
        return out


def load_identity_registry(path: Path | str) -> IdentityRegistry:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return IdentityRegistry.from_dict(data)
