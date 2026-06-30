"""Tests for external Restic live-write gate (wrapper + snapshot script)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "restic-ensure-chroma-snapshot.sh"
WRAPPER = REPO_ROOT / "scripts" / "convmem-live-write.sh"
VERIFY = REPO_ROOT / "scripts" / "verify-restic-gate.sh"


def _restic_available() -> bool:
    return shutil.which("restic") is not None


@unittest.skipUnless(_restic_available(), "restic not on PATH")
class ResticGateTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp = Path(self.td.name)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.chroma = self.tmp / "chroma"
        self.chroma.mkdir()
        (self.chroma / "seed.txt").write_text("seed\n", encoding="utf-8")
        self.repo = self.tmp / "repo"
        self.pass_file = self.tmp / "restic.password"
        self.pass_file.write_text("test-restic-gate-password\n", encoding="utf-8")
        self.pass_file.chmod(0o600)
        self.env_file = self.tmp / "restic.env"
        self.env_file.write_text(
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_PASSWORD_FILE={self.pass_file}\n"
            f"CONVMEM_CHROMA_DIR={self.chroma}\n",
            encoding="utf-8",
        )
        self.fake_convmem = self.bin / "convmem"
        self.fake_convmem.write_text(
            '#!/usr/bin/env bash\necho "FAKE_CONVMEM_CALLED $*"\n',
            encoding="utf-8",
        )
        self.fake_convmem.chmod(0o755)
        self.env = {
            **os.environ,
            "CONVMEM_RESTIC_ENV": str(self.env_file),
            "PATH": f"{self.bin}:{os.environ.get('PATH', '')}",
        }

    def tearDown(self):
        self.td.cleanup()

    def _run(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            list(args),
            cwd=REPO_ROOT,
            env=env or self.env,
            capture_output=True,
            text=True,
        )

    def test_ensure_snapshot_happy_path(self):
        init = self._run(
            "restic",
            "-r",
            str(self.repo),
            f"--password-file={self.pass_file}",
            "init",
        )
        self.assertEqual(init.returncode, 0, init.stderr)

        gate = self._run(str(GATE))
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        self.assertIn("snapshot OK", gate.stdout + gate.stderr)

        require = self._run(str(GATE), "--require-current")
        self.assertEqual(require.returncode, 0, require.stdout + require.stderr)

    def test_wrapper_blocks_on_missing_password_fail_closed(self):
        bad_env = self.tmp / "bad.env"
        bad_env.write_text(
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_PASSWORD_FILE={self.tmp / 'no-such-password'}\n"
            f"CONVMEM_CHROMA_DIR={self.chroma}\n",
            encoding="utf-8",
        )
        env = {**self.env, "CONVMEM_RESTIC_ENV": str(bad_env)}
        proc = self._run(str(WRAPPER), "record", "--list", env=env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("BLOCKED", proc.stderr)
        self.assertNotIn("FAKE_CONVMEM_CALLED", proc.stdout)

    def test_wrapper_reaches_convmem_when_gate_passes(self):
        init = self._run(
            "restic",
            "-r",
            str(self.repo),
            f"--password-file={self.pass_file}",
            "init",
        )
        self.assertEqual(init.returncode, 0)
        gate = self._run(str(GATE))
        self.assertEqual(gate.returncode, 0, gate.stderr)

        proc = self._run(str(WRAPPER), "record", "--list")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("FAKE_CONVMEM_CALLED", proc.stdout)

    def test_verify_restic_gate_script(self):
        proc = self._run(str(VERIFY))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
