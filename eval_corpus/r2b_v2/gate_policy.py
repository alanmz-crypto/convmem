"""Canonical writer-gate identity policy for R2b v2 leases."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from chroma_write_store import DEFAULT_WRITER_LOCK, WRITER_GATE_PROTOCOL_VERSION


@dataclass(frozen=True)
class GatePolicy:
    canonical_path: Path
    canonical_identity: str
    protocol: int
    policy_class: str

    def resolve_path(self) -> Path:
        return self.canonical_path.expanduser().resolve(strict=False)


def _gate_identity(path: Path) -> str:
    return hashlib.sha256(str(path.expanduser().resolve(strict=False)).encode("utf-8")).hexdigest()


def production_gate_policy() -> GatePolicy:
    path = DEFAULT_WRITER_LOCK.expanduser()
    return GatePolicy(
        canonical_path=DEFAULT_WRITER_LOCK,
        canonical_identity=_gate_identity(path),
        protocol=WRITER_GATE_PROTOCOL_VERSION,
        policy_class="production",
    )


def test_gate_policy(lock_path: Path) -> GatePolicy:
    resolved = lock_path.expanduser()
    return GatePolicy(
        canonical_path=resolved,
        canonical_identity=_gate_identity(resolved),
        protocol=WRITER_GATE_PROTOCOL_VERSION,
        policy_class="test_fixture",
    )


def resolve_trusted_gate_policy(
    gate_policy: GatePolicy | None,
    test_gate_path: Path | None,
    *,
    error_cls: type[Exception],
    mutual_exclusion_message: str,
    untrusted_policy_message: str,
) -> GatePolicy:
    """Resolve gate policy for trusted authority minting — rejects caller production policy."""
    if gate_policy is not None and test_gate_path is not None:
        raise error_cls(mutual_exclusion_message)
    if gate_policy is not None:
        if gate_policy.policy_class != "test_fixture":
            raise error_cls(untrusted_policy_message)
        return gate_policy
    if test_gate_path is not None:
        return test_gate_policy(test_gate_path)
    return production_gate_policy()
