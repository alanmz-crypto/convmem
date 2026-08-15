"""CG-2 promotion source-freshness guard tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import file_generation_pointer as pointers
from tests.test_file_generation_pointer import _cfg, _manifest, _publish


def test_promotion_refuses_stale_source_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("version-a", encoding="utf-8")
    root = tmp_path / "generations"
    reference = pointers.publish_manifest(root, _manifest(source, "1"))
    source.write_text("version-b", encoding="utf-8")
    with pytest.raises(pointers.StaleSourceError):
        pointers.publish_active_pointer(
            root,
            reference,
            chroma_dir=root / "chroma",
            cfg=_cfg(root),
            expected_previous_generation_id=None,
            backend_fingerprint="rust-a",
            candidate_revalidator=lambda manifest: True,
        )
    assert pointers.read_unqualified_pointer(
        root, reference.manifest["owner_digest"]
    ) is None


def test_promotion_succeeds_when_source_bytes_match(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_text("stable", encoding="utf-8")
    root = tmp_path / "generations"
    with patch.object(pointers, "_run_fresh_process_qualification"):
        qualified = _publish(root, source, "1", previous=None)
    assert qualified.pointer["active_generation_id"] == qualified.manifest["generation_id"]
