"""M4/T3 — unforgeable / revocable QualifiedStrictGeneration capability.

Parent Architecture §6.5.4: module-sealed capability; forged dataclass construction
and revoked instances are unusable. Reader path never mutates files/mtimes/caches.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def test_strict_projection_capability_present():
    spec = importlib.util.find_spec("strict_projection")
    assert spec is not None, "[T3] module strict_projection absent"
    module = importlib.import_module("strict_projection")
    assert hasattr(module, "revoke_snapshot")
    assert hasattr(module, "open_published_generation")
    assert hasattr(module, "QualifiedStrictGeneration")
    assert hasattr(module, "StrictProjectionReader")


def test_qualified_strict_generation_constructor_forges_nothing():
    """Callers cannot mint a usable capability by constructing the class."""

    from strict_projection import QualifiedStrictGeneration

    with pytest.raises(TypeError):
        QualifiedStrictGeneration(  # type: ignore[call-arg]
            lineage_id="a" * 32,
            authority_seq=1,
            snapshot_id="snap2_" + "0" * 64,
            authority_manifest_sha256="sha256:" + ("0" * 64),
            generation_id="gen2_" + "0" * 64,
            projection_manifest_sha256="sha256:" + ("0" * 64),
            rows_sha256="sha256:" + ("0" * 64),
            graph_sha256="sha256:" + ("0" * 64),
            publication_payload_sha256="sha256:" + ("0" * 64),
            semantic_contract_sha256="sha256:" + ("0" * 64),
            as_of="2026-09-21T00:00:00Z",
            expires_at="2027-09-21T00:00:00Z",
            scope=None,
            registry=None,
            rows=(),
            graph={},
        )


def test_object_new_forged_instance_rejected_by_reader_and_revoke():
    from strict_projection import (
        QualifiedStrictGeneration,
        StrictProjectionError,
        StrictProjectionReader,
        revoke_snapshot,
    )

    forged = object.__new__(QualifiedStrictGeneration)
    with pytest.raises(StrictProjectionError, match="forged_capability"):
        StrictProjectionReader(forged)  # type: ignore[arg-type]
    with pytest.raises(StrictProjectionError, match="forged_capability"):
        revoke_snapshot(forged)  # type: ignore[arg-type]


def test_revoke_snapshot_no_filesystem_mutation(tmp_path: Path):
    """Revocation is in-process only — no mtime/file/cache writes."""

    marker = tmp_path / "untouched"
    marker.write_text("x", encoding="utf-8")
    before = marker.stat().st_mtime_ns
    from strict_projection import QualifiedStrictGeneration, StrictProjectionError, revoke_snapshot

    forged = object.__new__(QualifiedStrictGeneration)
    with pytest.raises(StrictProjectionError, match="forged_capability"):
        revoke_snapshot(forged)  # type: ignore[arg-type]
    after = marker.stat().st_mtime_ns
    assert after == before
    assert marker.read_text(encoding="utf-8") == "x"
