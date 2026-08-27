"""CG-2 promotion source-freshness guard tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import file_generation_pointer as pointers
from tests.test_file_generation_pointer import (
    _ensure_fence,
    _manifest,
    _publish,
    _publish_first_cutover,
    _publish_first_cutover_ref,
    _publish_forward_ref,
    _rollback,
    _rollback_setup_after_source_change,
)


@pytest.fixture(autouse=True)
def _patch_fresh_process_qualification():
    with patch.object(pointers, "_run_fresh_process_qualification"):
        yield


def test_forward_refuses_stale_current_source_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("version-a", encoding="utf-8")
    root = tmp_path / "generations"
    with patch.object(pointers, "_run_fresh_process_qualification"):
        active = _publish_first_cutover(root, source, "1")
    forward_ref = pointers.publish_manifest(root, _manifest(source, "2"))
    source.write_text("version-b", encoding="utf-8")
    with pytest.raises(pointers.StaleSourceError):
        _publish_forward_ref(root, forward_ref, expected_active=active.manifest["generation_id"])
    still = pointers.read_unqualified_pointer(root, active.manifest["owner_digest"])
    assert still["active_generation_id"] == active.manifest["generation_id"]


def test_first_cutover_does_not_require_live_source_match_for_rollback_path(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.write_text("version-a", encoding="utf-8")
    root = tmp_path / "generations"
    reference = pointers.publish_manifest(root, _manifest(source, "1"))
    source.write_text("version-b", encoding="utf-8")
    with patch.object(pointers, "_run_fresh_process_qualification"):
        qualified = _publish_first_cutover_ref(root, reference)
    assert qualified.pointer["previous_generation_id"] is not None


def test_promotion_succeeds_when_source_bytes_match(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("stable", encoding="utf-8")
    root = tmp_path / "generations"
    with patch.object(pointers, "_run_fresh_process_qualification"):
        qualified = _publish(root, source, "1", previous=None)
    assert qualified.pointer["active_generation_id"] == qualified.manifest["generation_id"]


def test_rollback_advanced_source_records_reconciliation_obligation(tmp_path: Path) -> None:
    root, _retained, current, retained_ref, cfg = _rollback_setup_after_source_change(tmp_path)
    _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    from source_reconciler import pending_owner_work, reconciliation_state_path

    pending = pending_owner_work(cfg)
    assert len(pending) == 1
    assert pending[0].reason == "generational_source_hash_mismatch"
    state = __import__("json").loads(reconciliation_state_path(cfg).read_text(encoding="utf-8"))
    assert any("rollback:" in marker for marker in state.get("dirty_scopes") or [])


def test_rollback_reconciliation_precedes_pointer_publication(tmp_path: Path) -> None:
    root, _retained, current, retained_ref, _cfg_value = _rollback_setup_after_source_change(
        tmp_path
    )
    call_order: list[str] = []
    original_record = __import__("source_reconciler").record_rollback_reconciliation_obligation
    original_publish = pointers._publish_pointer_under_lock  # pylint: disable=protected-access

    def _track_record(*args, **kwargs):
        call_order.append("reconciliation")
        return original_record(*args, **kwargs)

    def _track_publish(*args, **kwargs):
        call_order.append("publish")
        return original_publish(*args, **kwargs)

    with patch(
        "source_reconciler.record_rollback_reconciliation_obligation",
        side_effect=_track_record,
    ), patch.object(pointers, "_publish_pointer_under_lock", side_effect=_track_publish):
        _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    assert call_order == ["reconciliation", "publish"]


def test_forward_refuses_but_rollback_succeeds_after_source_advance(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("v1", encoding="utf-8")
    root = tmp_path / "generations"
    retained_manifest = _manifest(source, "1")
    retained = _publish(root, source, "1", previous=None)
    current = _publish(root, source, "2", previous=retained.manifest["generation_id"])
    forward_ref = pointers.publish_manifest(root, _manifest(source, "3"))
    source.write_text("v2-advanced", encoding="utf-8")
    with pytest.raises(pointers.StaleSourceError):
        _publish_forward_ref(root, forward_ref, expected_active=current.manifest["generation_id"])
    retained_ref = pointers.publish_manifest(root, retained_manifest)
    rolled = _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    assert rolled.pointer["active_generation_id"] == retained.manifest["generation_id"]


def test_rollback_reconciliation_obligation_may_remain_when_pointer_refuses(
    tmp_path: Path,
) -> None:
    root, _retained, current, retained_ref, cfg = _rollback_setup_after_source_change(tmp_path)
    _ensure_fence(root, str(retained_ref.manifest["owner_key"]))
    from source_reconciler import pending_owner_work

    with patch.object(
        pointers,
        "_publish_pointer_under_lock",
        side_effect=pointers.GenerationPublicationError("simulated publish refusal"),
    ):
        with pytest.raises(pointers.GenerationPublicationError, match="publish refusal"):
            _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    assert pending_owner_work(cfg)


def _known_model_manifest(source: Path, label: str) -> dict:
    from cg2_legacy_vector_attestation import KNOWN_MODEL_AND_VECTOR_V1
    from file_generation_contract import canonical_hash

    manifest = _manifest(source, label)
    annotations = dict(manifest.get("recorded_only_annotations") or {})
    annotations["proof_profile"] = KNOWN_MODEL_AND_VECTOR_V1
    manifest["recorded_only_annotations"] = annotations
    unsigned = dict(manifest)
    unsigned.pop("manifest_payload_hash", None)
    manifest["manifest_payload_hash"] = canonical_hash(unsigned)
    return manifest


def _known_model_cutover_pair(
    root: Path,
    source: Path,
) -> tuple[pointers.QualifiedActivePointer, pointers.QualifiedActivePointer, pointers.ManifestReference]:
    retained_ref = pointers.publish_manifest(root, _known_model_manifest(source, "1"))
    retained = _publish_first_cutover_ref(root, retained_ref)
    forward_ref = pointers.publish_manifest(root, _known_model_manifest(source, "2"))
    current = _publish_forward_ref(
        root, forward_ref, expected_active=retained.manifest["generation_id"]
    )
    return retained, current, retained_ref


def test_known_model_rollback_does_not_require_grb_ratification(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    root = tmp_path / "generations"
    retained, current, retained_ref = _known_model_cutover_pair(root, source)
    _ensure_fence(root, str(retained.manifest["owner_key"]))
    rolled = _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    assert rolled.pointer["active_generation_id"] == retained.manifest["generation_id"]


def test_rollback_missing_source_records_reconciliation_obligation(tmp_path: Path) -> None:
    root, _retained, current, retained_ref, cfg = _rollback_setup_after_source_change(
        tmp_path, advanced=None, remove_source=True
    )
    _rollback(root, retained_ref, expected_active=current.manifest["generation_id"])
    from source_reconciler import pending_owner_work

    pending = pending_owner_work(cfg)
    assert len(pending) == 1
    assert pending[0].reason == "generational_source_missing"
