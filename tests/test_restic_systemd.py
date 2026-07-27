"""Tests for systemd timer and service unit validation."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _systemd_available() -> bool:
    try:
        subprocess.run(
            ["systemd-analyze", "--version"],
            capture_output=True,
            check=False,
        )
        return True
    except FileNotFoundError:
        return False


@unittest.skipUnless(_systemd_available(), "systemd-analyze not available")
class TestSystemdUnits(unittest.TestCase):
    def test_local_timer_calendar_parses(self):
        proc = subprocess.run(
            ["systemd-analyze", "calendar", "*-*-* 00:15:00"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Next elapse", proc.stdout)

    def test_external_timer_calendar_parses(self):
        proc = subprocess.run(
            ["systemd-analyze", "calendar", "*-*-* 01/2:00:00"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Next elapse", proc.stdout)

    def test_unit_files_exist(self):
        units = [
            "convmem-restic-local.service.example",
            "convmem-restic-local.timer.example",
            "convmem-restic-external.service.example",
            "convmem-restic-external.timer.example",
        ]
        for unit in units:
            path = REPO / "systemd" / unit
            self.assertTrue(path.is_file(), f"Missing {unit}")

    def test_unit_files_verify(self):
        # systemd-analyze verify requires .service/.timer suffix, not .example.
        # Copy to temp dir with correct suffixes, verify, then clean up.
        import shutil
        import tempfile
        src_units = {
            "convmem-restic-local.service.example": "convmem-restic-local.service",
            "convmem-restic-local.timer.example": "convmem-restic-local.timer",
            "convmem-restic-external.service.example": "convmem-restic-external.service",
            "convmem-restic-external.timer.example": "convmem-restic-external.timer",
        }
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            unit_paths = []
            for src, dst in src_units.items():
                src_path = REPO / "systemd" / src
                dst_path = tmp / dst
                shutil.copy2(src_path, dst_path)
                unit_paths.append(str(dst_path))
            proc = subprocess.run(
                ["systemd-analyze", "verify"] + unit_paths,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                self.fail(f"systemd-analyze verify failed: {proc.stderr}")

    def test_local_timer_has_persistent(self):
        content = (REPO / "systemd" / "convmem-restic-local.timer.example").read_text()
        self.assertIn("Persistent=true", content)

    def test_external_timer_has_persistent(self):
        content = (REPO / "systemd" / "convmem-restic-external.timer.example").read_text()
        self.assertIn("Persistent=true", content)

    def test_external_service_has_after_local(self):
        content = (REPO / "systemd" / "convmem-restic-external.service.example").read_text()
        self.assertIn("After=convmem-restic-local.service", content)

    def test_external_service_documents_after_is_non_authoritative(self):
        content = (REPO / "systemd" / "convmem-restic-external.service.example").read_text()
        self.assertIn("does not pull in", content.lower())
        self.assertIn("does not", content.lower())


if __name__ == "__main__":
    unittest.main()
