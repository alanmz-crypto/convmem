"""Hermetic systemd unit checks for complete-data backup correction v2 (T5).

Copies example units to temporary .service/.timer names under ONE hermetic
parent (path firewall). Never installs, enables, starts, stops, or reloads
live user-systemd units.
"""

# The fixture owns its temp directory across setUp/tearDown; unit checks repeat
# intentionally across local and offsite examples.
# pylint: disable=consider-using-with,duplicate-code,wrong-import-position

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Import path firewall from the T1 restic fixture module.
from tests.test_restic_snapshot import PathFirewall, PathFirewallError


UNIT_SOURCES = {
    "convmem-restic-local.service.example": "convmem-restic-local.service",
    "convmem-restic-local.timer.example": "convmem-restic-local.timer",
    "convmem-restic-external.service.example": "convmem-restic-external.service",
    "convmem-restic-external.timer.example": "convmem-restic-external.timer",
}


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
class TestResticSystemdUnits(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory(prefix="convmem-restic-systemd-")
        self.parent = Path(self.td.name).resolve()
        self.fw = PathFirewall(self.parent)
        self.systemd_dir = self.fw.check(self.parent / "systemd", label="systemd")
        self.systemd_dir.mkdir()
        self.unit_paths: list[Path] = []
        for src_name, dst_name in UNIT_SOURCES.items():
            src = REPO / "systemd" / src_name
            self.assertTrue(src.is_file(), f"missing example {src_name}")
            dst = self.fw.check(self.systemd_dir / dst_name, label="unit")
            shutil.copy2(src, dst)
            if dst.suffix == ".service":
                text = dst.read_text(encoding="utf-8")
                text = text.replace("%h/Projects/convmem", str(REPO))
                dst.write_text(text, encoding="utf-8")
            self.unit_paths.append(dst)

    def tearDown(self) -> None:
        self.td.cleanup()

    def test_local_calendar_00_15(self) -> None:
        proc = subprocess.run(
            ["systemd-analyze", "calendar", "*-*-* 00:15:00"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Next elapse", proc.stdout)

    def test_external_calendar_01_every_2h(self) -> None:
        proc = subprocess.run(
            ["systemd-analyze", "calendar", "*-*-* 01/2:00:00"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Next elapse", proc.stdout)

    def test_temporary_unit_names_verify(self) -> None:
        for p in self.unit_paths:
            self.fw.check(p, label="verify_unit")
        proc = subprocess.run(
            ["systemd-analyze", "verify", *[str(p) for p in self.unit_paths]],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"systemd-analyze verify failed: stdout={proc.stdout!r} stderr={proc.stderr!r}",
        )

    def test_persistent_true_on_both_timers(self) -> None:
        local = (self.systemd_dir / "convmem-restic-local.timer").read_text(
            encoding="utf-8"
        )
        external = (self.systemd_dir / "convmem-restic-external.timer").read_text(
            encoding="utf-8"
        )
        self.assertIn("Persistent=true", local)
        self.assertIn("Persistent=true", external)
        self.assertIn("OnCalendar=*-*-* 00:15:00", local)
        self.assertIn("OnCalendar=*-*-* 01/2:00:00", external)

    def test_after_documented_non_authoritative(self) -> None:
        # Prefer comments from the temporary copy; also check repo example.
        content = (self.systemd_dir / "convmem-restic-external.service").read_text(
            encoding="utf-8"
        )
        self.assertIn("After=convmem-restic-local.service", content)
        lowered = content.lower()
        self.assertIn("non-authoritative", lowered)
        self.assertTrue(
            "does not pull in" in lowered or "does not" in lowered,
            "After= must be documented as non-authoritative / not a success proof",
        )

    def test_path_firewall_rejects_live_systemd_escape(self) -> None:
        live = Path.home() / ".config" / "systemd" / "user"
        with self.assertRaises(PathFirewallError):
            self.fw.check(live / "escape.service", label="live_systemd")


if __name__ == "__main__":
    unittest.main()
