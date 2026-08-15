"""CG-2 owner authority resolution and typed serving failure domains.

Resolves per-owner LEGACY / FENCED / GENERATIONAL / QUARANTINED / RETIRED states
from durable fence, pointer, manifest, and retirement evidence.  Production
serving callers consume a request-frozen vector from
:class:`ServingIndexRepository`; this module owns the resolver only.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from atomic_files import atomic_write_json
from file_generation_contract import (
    GenerationContractError,
    canonical_hash,
    owner_digest,
    validate_payload_hash,
)
from file_generation_pointer import (
    GenerationQualificationError,
    pointer_path,
    provision_generation_layout,
    read_unqualified_pointer,
    recover_active_pointer,
    _read_json,
)

FENCE_SCHEMA = "convmem/legacy-owner-fence-v1"
RETIREMENT_SCHEMA = "convmem/owner-retirement-v1"


class ServingAuthorityError(RuntimeError):
    """Fence, pointer, manifest, qualification, quarantine, or retry exhaustion."""


class AuthorityUnstableError(ServingAuthorityError):
    """Authority evidence churn exceeded the resolution retry budget."""


class OwnerUnavailableError(ServingAuthorityError):
    """Owner is fenced without a qualified pointer and cannot serve."""


class ServingBackendIntegrityError(RuntimeError):
    """Corruption or contradictory persisted backend state."""


class ServingBackendTransient(RuntimeError):
    """Recognized Chroma open/contention condition eligible for mediated fallback."""


class OwnerAuthorityMode(str, Enum):
    LEGACY = "LEGACY"
    FENCED_NO_POINTER = "FENCED_NO_POINTER"
    GENERATIONAL = "GENERATIONAL"
    QUARANTINED = "QUARANTINED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class OwnerAuthorityState:
    owner_digest: str
    mode: OwnerAuthorityMode
    generation_id: str | None = None
    owner_key: str | None = None

    def is_servable(self) -> bool:
        return self.mode in {OwnerAuthorityMode.LEGACY, OwnerAuthorityMode.GENERATIONAL}


@dataclass(frozen=True)
class AuthorityEvidenceSnapshot:
    fence_sha256: str | None
    pointer_sha256: str | None
    retirement_sha256: str | None


@dataclass(frozen=True)
class AuthorityResolutionRetryBudget:
    max_attempts: int = 5
    max_elapsed: float = 2.0


def _empty_owner_generation_map() -> Mapping[str, str]:
    return MappingProxyType({})


@dataclass(frozen=True)
class FrozenAuthorityVector:
    """Immutable owner→authority mapping frozen for one serving operation."""

    by_owner: Mapping[str, OwnerAuthorityState]
    legacy_global: bool
    resolution_attempts: int
    evidence_snapshots: Mapping[str, AuthorityEvidenceSnapshot]
    generation_root: str
    chroma_dir: str
    previous_by_owner: Mapping[str, str] = field(
        default_factory=_empty_owner_generation_map
    )

    def active_generations(self) -> dict[str, str]:
        return {
            owner: str(state.generation_id)
            for owner, state in self.by_owner.items()
            if state.mode == OwnerAuthorityMode.GENERATIONAL and state.generation_id
        }

    def previous_generations(self) -> dict[str, str]:
        return dict(self.previous_by_owner)


def generation_root_for_cfg(cfg: Mapping[str, Any]) -> Path:
    index = cfg.get("index") or {}
    chroma = str(index.get("chroma_dir") or "").strip()
    if not chroma:
        raise ServingAuthorityError("config lacks index.chroma_dir")
    explicit = index.get("generation_root")
    if explicit:
        return Path(str(explicit)).expanduser()
    return Path(chroma).expanduser().parent / "file_generations"


def fence_path(generation_root: str | Path, owner_digest_value: str) -> Path:
    return Path(generation_root) / "active" / f"{owner_digest_value}.fence.json"


def retirement_path(generation_root: str | Path, owner_digest_value: str) -> Path:
    return Path(generation_root) / "active" / f"{owner_digest_value}.retired.json"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_legacy_fence(fence: Mapping[str, Any]) -> None:
    if fence.get("schema") != FENCE_SCHEMA:
        raise GenerationContractError("unsupported legacy fence schema")
    if fence.get("owner_digest") != owner_digest(str(fence.get("owner_key", ""))):
        raise GenerationContractError("fence owner digest mismatch")
    validate_payload_hash(fence, "fence_payload_hash")


def validate_retirement_record(record: Mapping[str, Any]) -> None:
    if record.get("schema") != RETIREMENT_SCHEMA:
        raise GenerationContractError("unsupported owner retirement schema")
    if record.get("owner_digest") != owner_digest(str(record.get("owner_key", ""))):
        raise GenerationContractError("retirement owner digest mismatch")
    validate_payload_hash(record, "retirement_payload_hash")


def build_legacy_fence(owner_key: str, published_at: str) -> dict[str, Any]:
    fence = {
        "schema": FENCE_SCHEMA,
        "owner_key": owner_key,
        "owner_digest": owner_digest(owner_key),
        "published_at": published_at,
    }
    fence["fence_payload_hash"] = canonical_hash(
        {key: fence[key] for key in sorted(fence)}
    )
    validate_legacy_fence(fence)
    return fence


def publish_legacy_fence(generation_root: str | Path, owner_key: str, published_at: str) -> Path:
    provision_generation_layout(generation_root)
    digest = owner_digest(owner_key)
    path = fence_path(generation_root, digest)
    payload = build_legacy_fence(owner_key, published_at)
    atomic_write_json(path, payload)
    return path


def _evidence_snapshot(
    generation_root: Path, owner_digest_value: str
) -> AuthorityEvidenceSnapshot:
    fence_file = fence_path(generation_root, owner_digest_value)
    pointer_file = pointer_path(generation_root, owner_digest_value)
    retired_file = retirement_path(generation_root, owner_digest_value)
    fence_sha = _file_sha256(fence_file) if fence_file.exists() else None
    pointer_sha = _file_sha256(pointer_file) if pointer_file.exists() else None
    retired_sha = _file_sha256(retired_file) if retired_file.exists() else None
    return AuthorityEvidenceSnapshot(
        fence_sha256=fence_sha,
        pointer_sha256=pointer_sha,
        retirement_sha256=retired_sha,
    )


def _derive_owner_state(
    generation_root: Path,
    owner_digest_value: str,
    snapshot: AuthorityEvidenceSnapshot,
    *,
    chroma_dir: str,
    cfg: Mapping[str, Any],
) -> OwnerAuthorityState:
    fence_file = fence_path(generation_root, owner_digest_value)
    retired_file = retirement_path(generation_root, owner_digest_value)

    if retired_file.exists():
        record = _read_json(retired_file)
        validate_retirement_record(record)
        if str(record["owner_digest"]) != owner_digest_value:
            raise GenerationQualificationError("retirement stored under wrong owner")
        return OwnerAuthorityState(
            owner_digest_value,
            OwnerAuthorityMode.RETIRED,
            owner_key=str(record.get("owner_key")),
        )

    has_fence = snapshot.fence_sha256 is not None
    has_pointer = snapshot.pointer_sha256 is not None

    if has_pointer and not has_fence:
        return OwnerAuthorityState(
            owner_digest_value, OwnerAuthorityMode.QUARANTINED
        )

    if has_fence:
        fence = _read_json(fence_file)
        validate_legacy_fence(fence)
        if str(fence["owner_digest"]) != owner_digest_value:
            raise GenerationQualificationError("fence stored under wrong owner")
        if not has_pointer:
            return OwnerAuthorityState(
                owner_digest_value,
                OwnerAuthorityMode.FENCED_NO_POINTER,
                owner_key=str(fence.get("owner_key")),
            )
        pointer = read_unqualified_pointer(generation_root, owner_digest_value)
        if pointer is None:
            return OwnerAuthorityState(
                owner_digest_value, OwnerAuthorityMode.QUARANTINED
            )
        try:
            qualified = recover_active_pointer(
                generation_root,
                str(pointer["owner_key"]),
                chroma_dir=chroma_dir,
                cfg=dict(cfg),
            )
        except (GenerationQualificationError, GenerationContractError) as exc:
            raise ServingAuthorityError(str(exc)) from exc
        return OwnerAuthorityState(
            owner_digest_value,
            OwnerAuthorityMode.GENERATIONAL,
            generation_id=str(qualified.pointer["active_generation_id"]),
            owner_key=str(qualified.pointer["owner_key"]),
        )

    if not has_fence and not has_pointer:
        return OwnerAuthorityState(owner_digest_value, OwnerAuthorityMode.LEGACY)

    return OwnerAuthorityState(owner_digest_value, OwnerAuthorityMode.QUARANTINED)


def discover_owner_digests(generation_root: Path) -> set[str]:
    active = generation_root / "active"
    if not active.is_dir():
        return set()
    digests: set[str] = set()
    for path in active.iterdir():
        if not path.is_file():
            continue
        name = path.name
        if name.endswith(".fence.json"):
            digests.add(name[:-len(".fence.json")])
        elif name.endswith(".retired.json"):
            digests.add(name[:-len(".retired.json")])
        elif name.endswith(".json") and "--" not in name:
            digests.add(name[:-len(".json")])
    return digests


def resolve_frozen_authority_vector(
    cfg: Mapping[str, Any],
    *,
    owner_digests: set[str] | None = None,
    budget: AuthorityResolutionRetryBudget | None = None,
) -> FrozenAuthorityVector:
    """Resolve and freeze owner authority for one serving operation."""

    budget = budget or AuthorityResolutionRetryBudget()
    generation_root = generation_root_for_cfg(cfg)
    chroma_dir = str((cfg.get("index") or {})["chroma_dir"])
    if owner_digests is None:
        if generation_root.exists():
            provision_generation_layout(generation_root)
        owner_digests = discover_owner_digests(generation_root)

    legacy_global = len(owner_digests) == 0
    started = time.monotonic()
    attempts = 0

    states: dict[str, OwnerAuthorityState] = {}
    final_snapshots: dict[str, AuthorityEvidenceSnapshot] = {}

    while attempts < budget.max_attempts:
        attempts += 1
        elapsed = time.monotonic() - started
        if elapsed > budget.max_elapsed:
            raise AuthorityUnstableError(
                "authority evidence churn exceeded max_elapsed without linearization"
            )
        before = {
            digest: _evidence_snapshot(generation_root, digest)
            for digest in owner_digests
        }
        try:
            states = {
                digest: _derive_owner_state(
                    generation_root,
                    digest,
                    before[digest],
                    chroma_dir=chroma_dir,
                    cfg=cfg,
                )
                for digest in owner_digests
            }
        except (GenerationQualificationError, GenerationContractError) as exc:
            raise ServingAuthorityError(str(exc)) from exc

        after = {
            digest: _evidence_snapshot(generation_root, digest)
            for digest in owner_digests
        }
        if before == after:
            final_snapshots = after
            break
    else:
        raise AuthorityUnstableError(
            "authority evidence churn exceeded max_attempts without linearization"
        )

    frozen_states = MappingProxyType(dict(states))
    previous_by_owner: dict[str, str] = {}
    for digest, state in states.items():
        if state.mode != OwnerAuthorityMode.GENERATIONAL:
            continue
        pointer = read_unqualified_pointer(generation_root, digest)
        if pointer is None:
            continue
        previous_id = pointer.get("previous_generation_id")
        if isinstance(previous_id, str) and previous_id.strip():
            previous_by_owner[digest] = previous_id.strip()
    return FrozenAuthorityVector(
        by_owner=frozen_states,
        legacy_global=legacy_global,
        resolution_attempts=attempts,
        evidence_snapshots=MappingProxyType(dict(final_snapshots)),
        generation_root=str(generation_root),
        chroma_dir=chroma_dir,
        previous_by_owner=MappingProxyType(dict(previous_by_owner)),
    )
