from __future__ import annotations

import copy
import inspect
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

import file_generation_pointer as pointers
import cg2_cutover_guard
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
from source_observation import observe_source_hash

real_fresh_process_qualification = (
    pointers._run_fresh_process_qualification  # pylint: disable=protected-access
)


def _cfg(tmp_path: Path) -> dict:
    root = tmp_path / "generations"
    return {
        "index": {
            "processed_log": str(tmp_path / "data" / "processed.json"),
            "generation_root": str(root),
            "chroma_dir": str(root / "chroma"),
        }
    }


def _ensure_fence(root: Path, owner_key: str) -> None:
    from serving_authority import publish_legacy_fence

    publish_legacy_fence(root, owner_key, "2026-08-10T00:00:00Z")


def _manifest(source: Path, label: str) -> dict:
    canonical = canonical_source_path(source)
    key = ownership_key(canonical)
    source_hash = observe_source_hash(canonical)
    bundle = candidate_bundle_hash(
        [{"logical_id": f"logical-{label}", "document": f"fact-{label}"}], []
    )
    generation = make_generation_id(
        owner_digest=owner_digest(key),
        source_hash=source_hash,
        pipeline_fingerprint="pipeline",
        candidate_bundle_hash=bundle,
    )
    physical = make_physical_id("knowledge_units", generation, f"logical-{label}")
    return build_generation_manifest(
        owner_key=key,
        generation_id=generation,
        canonical_source=canonical,
        source_hash=source_hash,
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


GRB_GENERATION_ID = "cg2-rollback-baseline-placeholder"


def _publish_first_cutover(
    root: Path,
    source: Path,
    label: str,
    *,
    grb_id: str = GRB_GENERATION_ID,
) -> pointers.QualifiedActivePointer:
    reference = pointers.publish_manifest(root, _manifest(source, label))
    return pointers.publish_first_cutover_active_pointer(
        root,
        reference,
        rollback_baseline_generation_id=grb_id,
        chroma_dir=root / "chroma",
        cfg=_cfg(root),
        backend_fingerprint="rust-a",
        candidate_revalidator=lambda manifest: True,
        published_at=f"2026-08-10T00:00:0{label}Z",
    )


def _publish(
    root: Path,
    source: Path,
    label: str,
    *,
    previous: str | None,
) -> pointers.QualifiedActivePointer:
    if previous is None:
        return _publish_first_cutover(root, source, label)
    reference = pointers.publish_manifest(root, _manifest(source, label))
    return pointers.publish_active_pointer(
        root,
        reference,
        chroma_dir=root / "chroma",
        cfg=_cfg(root),
        expected_active_generation_id=previous,
        backend_fingerprint="rust-a",
        candidate_revalidator=lambda manifest: True,
        published_at=f"2026-08-10T00:00:0{label}Z",
    )


def _publish_first_cutover_ref(
    root: Path,
    reference: pointers.ManifestReference,
    *,
    grb_id: str = GRB_GENERATION_ID,
) -> pointers.QualifiedActivePointer:
    return pointers.publish_first_cutover_active_pointer(
        root,
        reference,
        rollback_baseline_generation_id=grb_id,
        chroma_dir=root / "chroma",
        cfg=_cfg(root),
        backend_fingerprint="rust-a",
        candidate_revalidator=lambda manifest: True,
    )


def _publish_forward_ref(
    root: Path,
    reference: pointers.ManifestReference,
    *,
    expected_active: str,
) -> pointers.QualifiedActivePointer:
    return pointers.publish_active_pointer(
        root,
        reference,
        chroma_dir=root / "chroma",
        cfg=_cfg(root),
        expected_active_generation_id=expected_active,
        backend_fingerprint="rust-a",
        candidate_revalidator=lambda manifest: True,
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
    assert n.pointer["previous_generation_id"] == GRB_GENERATION_ID

    stale_ref = pointers.publish_manifest(root, _manifest(source, "2"))
    with pytest.raises(pointers.GenerationPublicationError, match="non-None"):
        pointers.publish_active_pointer(
            root,
            stale_ref,
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_active_generation_id=None,
            backend_fingerprint="rust-a",
        )
    with pytest.raises(pointers.StaleGenerationError):
        pointers.publish_active_pointer(
            root,
            stale_ref,
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_active_generation_id="wrong-active",
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
            pointers.publish_first_cutover_active_pointer(
                root,
                reference,
                rollback_baseline_generation_id=GRB_GENERATION_ID,
                chroma_dir=root / "chroma",
                cfg=_cfg(root),
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
            expected_active_generation_id=n.manifest["generation_id"],
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
            expected_active_generation_id=n.manifest["generation_id"],
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
        pointers.publish_first_cutover_active_pointer(  # pylint: disable=unexpected-keyword-arg
            root,
            reference,
            rollback_baseline_generation_id=GRB_GENERATION_ID,
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            backend_fingerprint="rust-a",
            exact_generation_validator=lambda manifest: True,
        )
    with pytest.raises(TypeError, match="exact_generation_validator"):
        pointers.recover_active_pointer(  # pylint: disable=unexpected-keyword-arg
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
            _seal=pointers._QUALIFIED_POINTER_SEAL,  # pylint: disable=protected-access
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
    object.__setattr__(
        subclass,
        "_seal",
        pointers._QUALIFIED_POINTER_SEAL,  # pylint: disable=protected-access
    )
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
    token = pointers._make_qualified_active_pointer(  # pylint: disable=protected-access
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
        real_fresh_process_qualification(root / "chroma", reference)


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

def test_forward_refuses_first_pointer_creation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    reference = pointers.publish_manifest(root, _manifest(source, "1"))
    with pytest.raises(pointers.GenerationPublicationError, match="first active pointer"):
        pointers.publish_active_pointer(
            root,
            reference,
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_active_generation_id=reference.manifest["generation_id"],
            backend_fingerprint="rust-a",
        )


def test_forward_writes_previous_from_cas_proven_active(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    first = _publish(root, source, "1", previous=None)
    second = _publish(root, source, "2", previous=first.manifest["generation_id"])
    assert second.pointer["active_generation_id"] == second.manifest["generation_id"]
    assert second.pointer["previous_generation_id"] == first.manifest["generation_id"]


def test_first_cutover_pointer_capability(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    qualified = _publish_first_cutover(root, source, "1", grb_id="G_rb")
    assert qualified.pointer["active_generation_id"] == qualified.manifest["generation_id"]
    assert qualified.pointer["previous_generation_id"] == "G_rb"
    with pytest.raises(pointers.StaleGenerationError, match="pointer absence"):
        _publish_first_cutover(root, source, "2", grb_id="G_rb2")


def test_rollback_switches_to_retained_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    retained_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    rolled = _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    assert rolled.pointer["active_generation_id"] == retained.manifest["generation_id"]
    assert rolled.pointer["previous_generation_id"] == current.manifest["generation_id"]


def test_rollback_stale_cas_refuses_independent_of_target_validity(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    retained_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    _ensure_fence(root, str(retained_ref.manifest["owner_key"]))
    with pytest.raises(pointers.StaleGenerationError, match="rollback CAS mismatch"):
        pointers.rollback_active_pointer(
            root,
            retained_ref,
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_active_generation_id="wrong-active",
            backend_fingerprint="rust-a",
            candidate_revalidator=lambda manifest: True,
        )
    still = pointers.read_unqualified_pointer(root, retained.manifest["owner_digest"])
    assert still["active_generation_id"] == current.manifest["generation_id"]


def test_rollback_does_not_require_live_source_match(tmp_path: Path) -> None:
    root, retained, current, retained_ref, _cfg = _rollback_setup_after_source_change(tmp_path)
    rolled = _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    assert rolled.pointer["active_generation_id"] == retained.manifest["generation_id"]




def _rollback(
    root: Path,
    reference: pointers.ManifestReference,
    *,
    expected_active: str,
    **kwargs,
) -> pointers.QualifiedActivePointer:
    _ensure_fence(root, str(reference.manifest["owner_key"]))
    return pointers.rollback_active_pointer(
        root,
        reference,
        chroma_dir=root / "chroma",
        cfg=_cfg(root),
        expected_active_generation_id=expected_active,
        backend_fingerprint="rust-a",
        candidate_revalidator=lambda manifest: True,
        **kwargs,
    )


def _rollback_setup_after_source_change(
    tmp_path: Path,
    *,
    initial: str = "v1",
    advanced: str | None = "v2-advanced",
    remove_source: bool = False,
) -> tuple[Path, pointers.QualifiedActivePointer, pointers.QualifiedActivePointer, pointers.ManifestReference, dict]:
    source = tmp_path / "source"
    source.write_text(initial, encoding="utf-8")
    root = tmp_path / "generations"
    cfg = _cfg(root)
    retained_manifest = _manifest(source, "1")
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    if remove_source:
        source.unlink()
    elif advanced is not None:
        source.write_text(advanced, encoding="utf-8")
    retained_ref = pointers.publish_manifest(root, retained_manifest)
    return root, retained, current, retained_ref, cfg


def test_rollback_exact_previous_generation_target_succeeds(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    retained_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    rolled = _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    assert rolled.pointer["active_generation_id"] == retained.manifest["generation_id"]
    assert rolled.pointer["previous_generation_id"] == current.manifest["generation_id"]


def test_rollback_refuses_orphan_generation_outside_lineage(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    orphan_ref = pointers.publish_manifest(root, _manifest(source, "orphan"))
    with pytest.raises(pointers.GenerationPublicationError, match="durable previous_generation_id"):
        _rollback(root, orphan_ref, expected_active=current.manifest["generation_id"])


def test_rollback_refuses_current_active_as_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    current_ref = pointers.publish_manifest(root, _manifest(source, "2"))
    with pytest.raises(pointers.GenerationPublicationError, match="durable previous_generation_id"):
        _rollback(root, current_ref, expected_active=current.manifest["generation_id"])


def test_rollback_refuses_another_complete_fresh_qualified_generation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    other_ref = pointers.publish_manifest(root, _manifest(source, "3"))
    with pytest.raises(pointers.GenerationPublicationError, match="durable previous_generation_id"):
        _rollback(root, other_ref, expected_active=current.manifest["generation_id"])


def test_rollback_refuses_missing_durable_previous(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    only = _publish_first_cutover(root, source, "1")
    target_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    with pytest.raises(pointers.GenerationPublicationError, match="durable previous_generation_id"):
        _rollback(root, target_ref, expected_active=only.manifest["generation_id"])


def test_rollback_refuses_target_one_value_off_from_previous(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    near_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    with patch.object(
        pointers,
        "read_unqualified_pointer",
        wraps=pointers.read_unqualified_pointer,
    ) as reader:
        original = pointers.read_unqualified_pointer(root, retained.manifest["owner_digest"])

        def _patched(_root_arg, digest):
            value = original if digest == retained.manifest["owner_digest"] else None
            if value is not None:
                mutated = dict(value)
                mutated["previous_generation_id"] = "almost-" + str(value["previous_generation_id"])
                return mutated
            return value

        reader.side_effect = _patched
        with pytest.raises(pointers.GenerationPublicationError, match="durable previous_generation_id"):
            _rollback(root, near_ref, expected_active=current.manifest["generation_id"])


def test_rollback_stale_cas_precedes_valid_previous_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    _publish(root, source, "2", previous=retained.manifest["generation_id"])
    retained_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    with pytest.raises(pointers.StaleGenerationError, match="rollback CAS mismatch"):
        _rollback(root, retained_ref, expected_active="wrong-active")


def test_rollback_stale_cas_precedes_orphan_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    _publish(root, source, "2", previous=retained.manifest["generation_id"])
    orphan_ref = pointers.publish_manifest(root, _manifest(source, "orphan"))
    with pytest.raises(pointers.StaleGenerationError, match="rollback CAS mismatch"):
        _rollback(root, orphan_ref, expected_active="wrong-active")

def test_recovery_has_no_generation_selection_parameter() -> None:
    params = inspect.signature(pointers.recover_active_pointer).parameters
    forbidden = {
        name
        for name in params
        if name.endswith("_generation_id")
        or name.endswith("_manifest_reference")
        or "target" in name
    }
    assert forbidden == set()


def test_recovery_cannot_switch_to_another_complete_generation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    visible = _publish(root, source, "1", previous=None)
    alt_ref = pointers.publish_manifest(root, _manifest(source, "2"))
    recovered = pointers.recover_active_pointer(
        root,
        visible.manifest["owner_key"],
        chroma_dir=root / "chroma",
        cfg=_cfg(root),
        recovery_revalidator=lambda manifest: True,
    )
    assert recovered.pointer["active_generation_id"] == visible.manifest["generation_id"]
    assert recovered.pointer["active_generation_id"] != alt_ref.manifest["generation_id"]


def test_open_canary_guard_blocks_ordinary_forward(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    active = _publish(root, source, "1", previous=None)
    cg2_cutover_guard.publish_canary_open_guard(
        root,
        owner_key=active.manifest["owner_key"],
        canary_generation_id="canary-gen",
        rollback_baseline_generation_id=GRB_GENERATION_ID,
        published_at="2026-08-10T00:00:00Z",
    )
    forward_ref = pointers.publish_manifest(root, _manifest(source, "2"))
    with pytest.raises(pointers.GenerationPublicationError, match="first-canary guard"):
        _publish_forward_ref(root, forward_ref, expected_active=active.manifest["generation_id"])


class _OneLockOracle:
    def __init__(self) -> None:
        self.acquisitions: list[str] = []
        self._held = False

    def __call__(self, cfg, canonical_source):
        if self._held:
            raise AssertionError(f"nested source_flock reentry for {canonical_source}")
        self._held = True
        self.acquisitions.append(str(canonical_source))
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._held = False
        return False


@pytest.mark.parametrize(
    "operation",
    [
        "forward",
        "first_cutover",
        "rollback",
        "recovery",
    ],
)
def test_public_pointer_operations_acquire_source_flock_once(
    tmp_path: Path, operation: str
) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    oracle = _OneLockOracle()
    if operation == "forward":
        active = _publish(root, source, "1", previous=None)
        forward_ref = pointers.publish_manifest(root, _manifest(source, "2"))
        with patch.object(pointers, "source_flock", oracle):
            pointers.publish_active_pointer(
                root,
                forward_ref,
                chroma_dir=root / "chroma",
                cfg=_cfg(root),
                expected_active_generation_id=active.manifest["generation_id"],
                backend_fingerprint="rust-a",
                candidate_revalidator=lambda manifest: True,
            )
    elif operation == "first_cutover":
        reference = pointers.publish_manifest(root, _manifest(source, "1"))
        with patch.object(pointers, "source_flock", oracle):
            _publish_first_cutover_ref(root, reference)
    elif operation == "rollback":
        retained_manifest = _manifest(source, "1")
        retained = _publish(root, source, "1", previous=None)
        current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
        retained_ref = pointers.publish_manifest(root, retained_manifest)
        _ensure_fence(root, str(retained_ref.manifest["owner_key"]))
        with patch.object(pointers, "source_flock", oracle):
            pointers.rollback_active_pointer(
                root,
                retained_ref,
                chroma_dir=root / "chroma",
                cfg=_cfg(root),
                expected_active_generation_id=current.manifest["generation_id"],
                backend_fingerprint="rust-a",
                candidate_revalidator=lambda manifest: True,
            )
    else:
        active = _publish(root, source, "1", previous=None)
        with patch.object(pointers, "source_flock", oracle):
            pointers.recover_active_pointer(
                root,
                active.manifest["owner_key"],
                chroma_dir=root / "chroma",
                cfg=_cfg(root),
                recovery_revalidator=lambda manifest: True,
            )
    assert len(oracle.acquisitions) == 1


def test_rollback_unchanged_source_skips_reconciliation_debt(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("stable", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    retained_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    with patch("source_reconciler.record_rollback_reconciliation_obligation") as recorder:
        rolled = _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
        recorder.assert_not_called()
    assert rolled.pointer["active_generation_id"] == retained.manifest["generation_id"]


def test_rollback_reconciliation_persistence_failure_leaves_pointer_unchanged(
    tmp_path: Path,
) -> None:
    root, retained, current, retained_ref, _cfg = _rollback_setup_after_source_change(tmp_path)
    from source_reconciler import RollbackReconciliationError

    with patch(
        "source_reconciler.record_rollback_reconciliation_obligation",
        side_effect=RollbackReconciliationError("simulated persistence failure"),
    ):
        with pytest.raises(pointers.GenerationPublicationError, match="persistence failure"):
            _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    still = pointers.read_unqualified_pointer(root, retained.manifest["owner_digest"])
    assert still["active_generation_id"] == current.manifest["generation_id"]


def test_rollback_refuses_without_monotonic_fence(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    retained_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    with pytest.raises(pointers.GenerationPublicationError, match="monotonic legacy fence"):
        pointers.rollback_active_pointer(
            root,
            retained_ref,
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_active_generation_id=current.manifest["generation_id"],
            backend_fingerprint="rust-a",
            candidate_revalidator=lambda manifest: True,
        )


def test_rollback_refuses_corrupt_target_qualification(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    retained_ref = pointers.publish_manifest(root, _manifest(source, "1"))
    with patch.object(
        pointers,
        "_run_fresh_process_qualification",
        side_effect=pointers.GenerationQualificationError("corrupt target"),
    ):
        with pytest.raises(pointers.GenerationQualificationError, match="corrupt target"):
            _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    still = pointers.read_unqualified_pointer(root, retained.manifest["owner_digest"])
    assert still["active_generation_id"] == current.manifest["generation_id"]
