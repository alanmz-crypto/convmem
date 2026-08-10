from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

import file_generation_pointer as pointers
from atomic_files import PostPublicationDurabilityError, PrePublicationError
from file_generation_contract import (
    build_generation_manifest,
    candidate_bundle_hash,
    canonical_source_path,
    make_generation_id,
    make_physical_id,
    owner_digest,
    ownership_key,
)


def _cfg(tmp_path: Path) -> dict:
    return {"index": {"processed_log": str(tmp_path / "data" / "processed.json")}}


def _manifest(source: Path, label: str) -> dict:
    canonical = canonical_source_path(source)
    key = ownership_key(canonical)
    bundle = candidate_bundle_hash(
        [{"logical_id": f"logical-{label}", "document": f"fact-{label}"}], []
    )
    generation = make_generation_id(
        owner_digest=owner_digest(key),
        source_hash=f"source-{label}",
        pipeline_fingerprint="pipeline",
        candidate_bundle_hash=bundle,
    )
    physical = make_physical_id("knowledge_units", generation, f"logical-{label}")
    return build_generation_manifest(
        owner_key=key,
        generation_id=generation,
        canonical_source=canonical,
        source_hash=f"source-{label}",
        candidate_bundle_hash=bundle,
        fingerprints={"pipeline": "pipeline"},
        collections={
            "knowledge_units": {
                "collection_uuid": "units",
                "configuration": {"space": "cosine"},
                "embedding_model": "embed",
                "embedding_dimension": 2,
                "logical_to_physical": {f"logical-{label}": physical},
                "rows": {
                    physical: {
                        "logical_id": f"logical-{label}",
                        "document_hash": f"document-{label}",
                        "embedding_hash": f"embedding-{label}",
                        "embedding_dimension": 2,
                        "embedding_model": "embed",
                        "immutable_metadata": {
                            "start_offset": 0,
                            "content_hash": f"content-{label}",
                        },
                    }
                },
            }
        },
    )


def _publish(
    root: Path,
    source: Path,
    label: str,
    *,
    previous: str | None,
) -> pointers.QualifiedActivePointer:
    reference = pointers.publish_manifest(root, _manifest(source, label))
    return pointers.publish_active_pointer(
        root,
        reference,
        cfg=_cfg(root),
        expected_previous_generation_id=previous,
        backend_fingerprint="rust-a",
        exact_generation_validator=lambda manifest: True,
        candidate_revalidator=lambda manifest: True,
        published_at=f"2026-08-10T00:00:0{label}Z",
    )


def test_manifest_is_immutable_and_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    first = pointers.publish_manifest(root, _manifest(source, "1"))
    second = pointers.publish_manifest(root, _manifest(source, "1"))
    assert first.file_sha256 == second.file_sha256
    assert first.path == second.path
    assert (root / "layout.json").exists()
    assert (root / "active").is_dir()

    collision = copy.deepcopy(first.manifest)
    collision["recorded_only_annotations"]["note"] = "different bytes"
    unsigned = dict(collision)
    unsigned.pop("manifest_payload_hash")
    from file_generation_contract import canonical_hash

    collision["manifest_payload_hash"] = canonical_hash(unsigned)
    with pytest.raises(pointers.GenerationPublicationError, match="collision"):
        pointers.publish_manifest(root, collision)


def test_promote_and_stale_candidate_guard(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    n = _publish(root, source, "1", previous=None)
    assert n.pointer["active_generation_id"] == n.manifest["generation_id"]

    stale_ref = pointers.publish_manifest(root, _manifest(source, "2"))
    with pytest.raises(pointers.StaleGenerationError):
        pointers.publish_active_pointer(
            root,
            stale_ref,
            cfg=_cfg(root),
            expected_previous_generation_id=None,
            backend_fingerprint="rust-a",
            exact_generation_validator=lambda manifest: True,
        )
    still_n = pointers.read_unqualified_pointer(root, n.manifest["owner_digest"])
    assert still_n["active_generation_id"] == n.manifest["generation_id"]


def test_exact_set_or_candidate_drift_refuses_promotion(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    reference = pointers.publish_manifest(root, _manifest(source, "1"))

    for exact, drift in ((False, True), (True, False)):
        with pytest.raises(pointers.GenerationQualificationError):
            pointers.publish_active_pointer(
                root,
                reference,
                cfg=_cfg(root),
                expected_previous_generation_id=None,
                backend_fingerprint="rust-a",
                exact_generation_validator=lambda manifest, value=exact: value,
                candidate_revalidator=lambda manifest, value=drift: value,
            )
        assert (
            pointers.read_unqualified_pointer(root, reference.manifest["owner_digest"])
            is None
        )


def test_prepublication_failure_leaves_n_serving(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    n = _publish(root, source, "1", previous=None)
    candidate = pointers.publish_manifest(root, _manifest(source, "2"))
    real_atomic = pointers.atomic_write_json

    def fail_pointer(path, payload, **kwargs):
        if Path(path).parent.name == "active":
            raise PrePublicationError("fault before replace")
        return real_atomic(path, payload, **kwargs)

    with (
        patch.object(pointers, "atomic_write_json", side_effect=fail_pointer),
        pytest.raises(PrePublicationError),
    ):
        pointers.publish_active_pointer(
            root,
            candidate,
            cfg=_cfg(root),
            expected_previous_generation_id=n.manifest["generation_id"],
            backend_fingerprint="rust-a",
            exact_generation_validator=lambda manifest: True,
        )
    current = pointers.read_unqualified_pointer(root, n.manifest["owner_digest"])
    assert current["active_generation_id"] == n.manifest["generation_id"]


def test_postpublication_failure_requires_exact_durable_republish(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    n = _publish(root, source, "1", previous=None)
    candidate = pointers.publish_manifest(root, _manifest(source, "2"))
    real_atomic = pointers.atomic_write_json

    def visible_but_uncertain(path, payload, **kwargs):
        real_atomic(path, payload, **kwargs)
        if Path(path).parent.name == "active":
            raise PostPublicationDurabilityError("directory fsync fault")

    with (
        patch.object(pointers, "atomic_write_json", side_effect=visible_but_uncertain),
        pytest.raises(PostPublicationDurabilityError),
    ):
        pointers.publish_active_pointer(
            root,
            candidate,
            cfg=_cfg(root),
            expected_previous_generation_id=n.manifest["generation_id"],
            backend_fingerprint="rust-a",
            exact_generation_validator=lambda manifest: True,
        )

    # The visible bytes are deliberately unqualified; the read API returns only
    # a dict and cannot mint a serving token.
    visible = pointers.read_unqualified_pointer(root, n.manifest["owner_digest"])
    assert visible["active_generation_id"] == candidate.manifest["generation_id"]
    assert not isinstance(visible, pointers.QualifiedActivePointer)
    uncertain = pointers.unverified_state(
        candidate.manifest["owner_key"],
        "directory fsync failed after replacement",
        visible_generation_id=visible["active_generation_id"],
    )
    assert uncertain.state is pointers.GenerationHealthState.UNVERIFIED_FAIL
    assert uncertain.may_serve is False

    recovered = pointers.recover_active_pointer(
        root,
        candidate.manifest["owner_key"],
        cfg=_cfg(root),
        exact_generation_validator=lambda manifest: True,
        recovery_revalidator=lambda manifest: True,
    )
    assert recovered.recovered is True
    assert recovered.pointer == visible
    assert pointers.healthy_state(recovered).may_serve is True


def test_candidate_failure_is_degraded_safe_only_while_previous_token_validates(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    previous = _publish(tmp_path / "generations", source, "1", previous=None)
    health = pointers.degraded_safe_state(previous, "provider timeout during candidate")
    assert health.state is pointers.GenerationHealthState.DEGRADED_SAFE
    assert health.generation_id == previous.manifest["generation_id"]
    assert health.may_serve is True


def test_recovery_does_not_guess_when_manifest_or_rows_fail(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    qualified = _publish(root, source, "1", previous=None)

    with pytest.raises(pointers.GenerationQualificationError, match="expected Chroma"):
        pointers.recover_active_pointer(
            root,
            qualified.manifest["owner_key"],
            cfg=_cfg(root),
            exact_generation_validator=lambda manifest: False,
        )

    manifest_file = root / "manifests" / qualified.pointer["manifest_filename"]
    manifest_file.write_text("{}\n", encoding="utf-8")
    with pytest.raises(pointers.GenerationQualificationError, match="hash mismatch"):
        pointers.recover_active_pointer(
            root,
            qualified.manifest["owner_key"],
            cfg=_cfg(root),
            exact_generation_validator=lambda manifest: True,
        )


def test_unrelated_owner_promotions_do_not_clobber(tmp_path: Path) -> None:
    root = tmp_path / "generations"
    source_a = tmp_path / "a.jsonl"
    source_b = tmp_path / "b.jsonl"
    source_a.write_text("a", encoding="utf-8")
    source_b.write_text("b", encoding="utf-8")

    def promote(source: Path, label: str) -> pointers.QualifiedActivePointer:
        return _publish(root, source, label, previous=None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_a = pool.submit(promote, source_a, "1")
        future_b = pool.submit(promote, source_b, "2")
        active_a = future_a.result(timeout=10)
        active_b = future_b.result(timeout=10)

    assert active_a.path != active_b.path
    read_a = pointers.read_unqualified_pointer(root, active_a.manifest["owner_digest"])
    read_b = pointers.read_unqualified_pointer(root, active_b.manifest["owner_digest"])
    assert read_a["active_generation_id"] == active_a.manifest["generation_id"]
    assert read_b["active_generation_id"] == active_b.manifest["generation_id"]
