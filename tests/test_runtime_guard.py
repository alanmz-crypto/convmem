"""Tests for prod/lab write boundary guards."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from runtime_guard import (
    LAB_DATA_ROOT,
    PROD_DATA_ROOT,
    data_profile,
    require_write_consent,
    runtime_summary,
    workspace_repo,
    write_boundary_message,
)


class RuntimeGuardTests(unittest.TestCase):
    def test_data_profile_prod_and_lab(self):
        self.assertEqual(data_profile(PROD_DATA_ROOT / "chroma"), "prod")
        self.assertEqual(data_profile(LAB_DATA_ROOT / "chroma"), "lab")

    def test_blocks_lab_workspace_prod_chroma(self):
        with tempfile.TemporaryDirectory() as tmp:
            lab_dir = Path(tmp) / "convmem-lab"
            lab_dir.mkdir()
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("CONVMEM_CONFIRM_PROD", None)
                with mock.patch("runtime_guard.workspace_repo", return_value="lab"):
                    msg = write_boundary_message(PROD_DATA_ROOT / "chroma")
        self.assertIsNotNone(msg)
        self.assertIn("CONVMEM_CONFIRM_PROD", msg or "")

    def test_allows_prod_workspace_prod_chroma(self):
        with mock.patch("runtime_guard.workspace_repo", return_value="prod"):
            msg = write_boundary_message(PROD_DATA_ROOT / "chroma")
        self.assertIsNone(msg)

    def test_confirm_prod_overrides_lab_workspace(self):
        with mock.patch.dict(os.environ, {"CONVMEM_CONFIRM_PROD": "1"}):
            with mock.patch("runtime_guard.workspace_repo", return_value="lab"):
                msg = write_boundary_message(PROD_DATA_ROOT / "chroma")
        self.assertIsNone(msg)

    def test_blocks_prod_workspace_lab_chroma_without_confirm(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONVMEM_CONFIRM_LAB", None)
            with mock.patch("runtime_guard.workspace_repo", return_value="prod"):
                msg = write_boundary_message(LAB_DATA_ROOT / "chroma")
        self.assertIsNotNone(msg)
        self.assertIn("CONVMEM_CONFIRM_LAB", msg or "")

    def test_require_write_consent_raises(self):
        with mock.patch("runtime_guard.write_boundary_message", return_value="blocked"):
            with self.assertRaises(RuntimeError):
                require_write_consent(PROD_DATA_ROOT / "chroma")

    def test_workspace_repo_from_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            lab = Path(tmp) / "convmem-lab" / "docs"
            lab.mkdir(parents=True)
            with mock.patch("runtime_guard.os.environ", {}):
                self.assertEqual(workspace_repo(lab), "lab")

    def test_runtime_summary_includes_lane(self):
        summary = runtime_summary(PROD_DATA_ROOT / "chroma")
        self.assertIn("lane=prod", summary)


if __name__ == "__main__":
    unittest.main()
