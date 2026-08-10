from __future__ import annotations

import copy
import inspect
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

_REAL_FRESH_PROCESS_QUALIFICATION = pointers._run_fresh_process_qualification


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


@pytest.fixture(autouse=True)
def _pointer_mechanics_fresh_process_seam():
    """Keep pointer mechanics hermetic; integration tests use the real runner."""
    with patch.object(pointers, "_run_fresh_process_qualification") as runner:
        yield runner


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
        chroma_dir=root / "chroma",
        cfg=_cfg(root),
        expected_previous_generation_id=previous,
        backend_fingerprint="rust-a",
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
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_previous_generation_id=None,
            backend_fingerprint="rust-a",
        )
    still_n = pointers.read_unqualified_pointer(root, n.manifest["owner_digest"])
    assert still_n["active_generation_id"] == n.manifest["generation_id"]


def test_fresh_qualification_or_candidate_drift_refuses_promotion(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    reference = pointers.publish_manifest(root, _manifest(source, "1"))

    for cold_failure, drift in ((True, True), (False, False)):
        cold_runner = (
            patch.object(
                pointers,
                "_run_fresh_process_qualification",
                side_effect=pointers.GenerationQualificationError("expected Chroma set"),
            )
            if cold_failure
            else patch.object(pointers, "_run_fresh_process_qualification")
        )
        with pytest.raises(pointers.GenerationQualificationError), cold_runner:
            pointers.publish_active_pointer(
                root,
                reference,
                chroma_dir=root / "chroma",
                cfg=_cfg(root),
                expected_previous_generation_id=None,
                backend_fingerprint="rust-a",
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
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_previous_generation_id=n.manifest["generation_id"],
            backend_fingerprint="rust-a",
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
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_previous_generation_id=n.manifest["generation_id"],
            backend_fingerprint="rust-a",
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
        chroma_dir=root / "chroma",
        cfg=_cfg(root),
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

    with (
        patch.object(
            pointers,
            "_run_fresh_process_qualification",
            side_effect=pointers.GenerationQualificationError("expected Chroma set"),
        ),
        pytest.raises(pointers.GenerationQualificationError, match="expected Chroma"),
    ):
        pointers.recover_active_pointer(
            root,
            qualified.manifest["owner_key"],
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
        )

    manifest_file = root / "manifests" / qualified.pointer["manifest_filename"]
    manifest_file.write_text("{}\n", encoding="utf-8")
    with pytest.raises(pointers.GenerationQualificationError, match="hash mismatch"):
        pointers.recover_active_pointer(
            root,
            qualified.manifest["owner_key"],
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
        )


def test_public_authority_apis_have_no_fake_validator_seam(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    reference = pointers.publish_manifest(root, _manifest(source, "1"))

    assert "exact_generation_validator" not in inspect.signature(
        pointers.publish_active_pointer
    ).parameters
    assert "exact_generation_validator" not in inspect.signature(
        pointers.recover_active_pointer
    ).parameters

    with pytest.raises(TypeError, match="exact_generation_validator"):
        pointers.publish_active_pointer(
            root,
            reference,
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_previous_generation_id=None,
            backend_fingerprint="rust-a",
            exact_generation_validator=lambda manifest: True,
        )
    with pytest.raises(TypeError, match="exact_generation_validator"):
        pointers.recover_active_pointer(
            root,
            reference.manifest["owner_key"],
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            exact_generation_validator=lambda manifest: True,
        )


def test_direct_or_forged_token_cannot_claim_healthy_serving(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does-not-exist.json"
    with pytest.raises(TypeError, match="sealed"):
        pointers.QualifiedActivePointer(
            nonexistent,
            {"owner_key": "source:/missing", "active_generation_id": "fake"},
            {},
        )
    with pytest.raises(TypeError, match="sealed"):
        pointers.QualifiedActivePointer(
            nonexistent,
            {"owner_key": "source:/missing", "active_generation_id": "fake"},
            {},
            _seal=pointers._QUALIFIED_POINTER_SEAL,
        )

    forged = object.__new__(pointers.QualifiedActivePointer)
    object.__setattr__(forged, "path", nonexistent)
    object.__setattr__(
        forged,
        "pointer",
        {"owner_key": "source:/missing", "active_generation_id": "fake"},
    )
    object.__setattr__(forged, "manifest", {})
    object.__setattr__(forged, "recovered", False)
    object.__setattr__(forged, "_seal", object())
    with pytest.raises(pointers.GenerationQualificationError, match="module-sealed"):
        pointers.healthy_state(forged)
    with pytest.raises(pointers.GenerationQualificationError, match="module-sealed"):
        pointers.degraded_safe_state(forged, "forged token")

    class TokenSubclass(pointers.QualifiedActivePointer):
        pass

    subclass = object.__new__(TokenSubclass)
    object.__setattr__(subclass, "path", nonexistent)
    object.__setattr__(
        subclass,
        "pointer",
        {"owner_key": "source:/missing", "active_generation_id": "fake"},
    )
    object.__setattr__(subclass, "manifest", {})
    object.__setattr__(subclass, "recovered", False)
    object.__setattr__(subclass, "_seal", pointers._QUALIFIED_POINTER_SEAL)
    with pytest.raises(pointers.GenerationQualificationError, match="module-sealed"):
        pointers.healthy_state(subclass)
    with pytest.raises(pointers.GenerationQualificationError, match="module-sealed"):
        pointers.degraded_safe_state(subclass, "subclass token")


def test_sealed_token_detaches_and_freezes_authority_payloads(tmp_path: Path) -> None:
    pointer = {
        "owner_key": "source:/original",
        "active_generation_id": "generation-original",
        "nested": {"value": "original"},
    }
    manifest = {"nested": {"value": "original"}}
    token = pointers._make_qualified_active_pointer(
        path=tmp_path / "pointer.json",
        pointer=pointer,
        manifest=manifest,
        recovered=False,
    )

    pointer["owner_key"] = "source:/rewritten"
    pointer["nested"]["value"] = "rewritten"
    manifest["nested"]["value"] = "rewritten"
    assert token.pointer["owner_key"] == "source:/original"
    assert token.pointer["nested"]["value"] == "original"
    assert token.manifest["nested"]["value"] == "original"
    with pytest.raises(TypeError):
        token.pointer["owner_key"] = "source:/forged"
    with pytest.raises(TypeError):
        token.manifest["nested"]["value"] = "forged"
    assert pointers.healthy_state(token).may_serve is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("owner_digest", "wrong-owner", "owner mismatch"),
        ("generation_id", "wrong-generation", "generation mismatch"),
        ("manifest_sha256", "wrong-hash", "manifest hash mismatch"),
    ],
)
def test_private_fresh_qualification_binds_child_result_to_manifest(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    reference = pointers.publish_manifest(root, _manifest(source, "1"))
    result = {
        "valid": True,
        "owner_digest": reference.manifest["owner_digest"],
        "generation_id": reference.manifest["generation_id"],
        "manifest_sha256": reference.file_sha256,
    }
    result[field] = value

    with (
        patch("file_generation_validate.run_cold_validation", return_value=result),
        pytest.raises(pointers.GenerationQualificationError, match=message),
    ):
        _REAL_FRESH_PROCESS_QUALIFICATION(root / "chroma", reference)


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
