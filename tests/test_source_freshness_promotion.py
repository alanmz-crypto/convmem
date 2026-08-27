"""CG-2 promotion source-freshness guard tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import file_generation_pointer as pointers
from tests.test_file_generation_pointer import (
    _manifest,
    _publish,
    _publish_first_cutover,
    _publish_first_cutover_ref,
    _publish_forward_ref,
)


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
