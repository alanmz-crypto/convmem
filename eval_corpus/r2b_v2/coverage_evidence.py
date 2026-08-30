"""Shared coverage-evidence field bundle for R2b v2 registry and proof."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoverageEvidenceIdentity:
    code_revision: str
    inventory_digest: str
    runtime_census_digest: str
    coverage_digest: str
    gate_identity: str
    gate_path: str
    gate_protocol: int
