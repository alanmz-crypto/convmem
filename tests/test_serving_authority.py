"""Tests for CG-2 serving authority resolution and repository boundary."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from atomic_files import atomic_write_json
from serving_authority import (
    AuthorityEvidenceSnapshot,
    AuthorityResolutionRetryBudget,
    AuthorityUnstableError,
    OwnerAuthorityMode,
    OwnerAuthorityState,
    OwnerUnavailableError,
    ServingAuthorityError,
    build_legacy_fence,
    discover_owner_digests,
    fence_path,
    generation_root_for_cfg,
    publish_legacy_fence,
    resolve_frozen_authority_vector,
)
from serving_index_repository import open_serving_index_repository


def _cfg(tmp_path: Path, chroma: Path) -> dict:
    return {
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(tmp_path / "file_generations"),
            "processed_log": str(tmp_path / "processed.json"),
        }
    }


def test_legacy_global_when_no_generation_artifacts(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)
    vector = resolve_frozen_authority_vector(cfg)
    assert vector.legacy_global is True
    assert vector.by_owner == {}


def test_fenced_owner_blocks_serving_open(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)
    root = generation_root_for_cfg(cfg)
    owner_key = "source:/tmp/example.jsonl"
    publish_legacy_fence(root, owner_key, "2026-08-15T00:00:00Z")
    assert len(discover_owner_digests(root)) == 1
    with pytest.raises(OwnerUnavailableError):
        with open_serving_index_repository(cfg):
            pass


def test_pointer_without_fence_is_quarantined(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)
    root = generation_root_for_cfg(cfg)
    owner_key = "source:/tmp/example.jsonl"
    from file_generation_contract import canonical_hash, owner_digest

    digest = owner_digest(owner_key)
    pointer = {
        "schema": "convmem/file-active-generation-pointer-v1",
        "owner_key": owner_key,
        "owner_digest": digest,
        "active_generation_id": "gen-test",
        "manifest_filename": "missing.json",
        "manifest_sha256": "abc",
        "source_hash": "src",
        "previous_generation_id": None,
        "backend_fingerprint": "rust-a",
        "published_at": "2026-08-15T00:00:00Z",
    }
    pointer["pointer_payload_hash"] = canonical_hash(
        {k: pointer[k] for k in sorted(pointer)}
    )
    active = root / "active"
    active.mkdir(parents=True, exist_ok=True)
    atomic_write_json(active / f"{digest}.json", pointer)
    with pytest.raises(ServingAuthorityError):
        with open_serving_index_repository(cfg):
            pass


def test_retry_budget_exhaustion_raises_authority_unstable(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = _cfg(tmp_path, chroma)
    from file_generation_contract import owner_digest

    owner_key = "source:/tmp/churn.jsonl"
    digest = owner_digest(owner_key)
    flip = 0

    def flipping_snapshot(_generation_root: Path, _owner_digest_value: str):
        nonlocal flip
        flip += 1
        return AuthorityEvidenceSnapshot(
            fence_sha256=f"fence-{flip}",
            pointer_sha256=None,
            retirement_sha256=None,
        )

    budget = AuthorityResolutionRetryBudget(max_attempts=2, max_elapsed=5.0)
    stable = OwnerAuthorityState(digest, OwnerAuthorityMode.LEGACY)
    with patch("serving_authority._evidence_snapshot", side_effect=flipping_snapshot):
        with patch(
            "serving_authority._derive_owner_state",
            return_value=stable,
        ):
            with pytest.raises(AuthorityUnstableError):
                resolve_frozen_authority_vector(
                    cfg,
                    owner_digests={digest},
                    budget=budget,
                )


def test_build_legacy_fence_validates_payload() -> None:
    fence = build_legacy_fence("source:/tmp/a.jsonl", "2026-08-15T00:00:00Z")
    assert fence["schema"] == "convmem/legacy-owner-fence-v1"
    assert fence["owner_digest"] == fence["owner_digest"]
