"""Tests for external Restic live-write gate (workflow + thin shell wrapper)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        # Layout: data_root and repo are siblings (no overlap).
        self.data_root = self.tmp / "data-root"
        self.data_root.mkdir()
        self.chroma = self.data_root / "chroma"
        self.chroma.mkdir()
        (self.chroma / "seed.txt").write_text("seed\n", encoding="utf-8")
        (self.data_root / "seed.txt").write_text("data\n", encoding="utf-8")
        self.repo = self.tmp / "repo"
        self.pass_file = self.tmp / "restic.password"
        self.pass_file.write_text("test-restic-gate-password\n", encoding="utf-8")
        self.pass_file.chmod(0o600)
        self.cache = self.tmp / "cache"
        self.cache.mkdir()
        self.env_file = self.tmp / "restic.env"
        self.env_file.write_text(
            "CONVMEM_BACKUP_PROFILE=complete-data-v2\n"
            f"CONVMEM_DATA_ROOT={self.data_root}\n"
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_PASSWORD_FILE={self.pass_file}\n"
            f"CONVMEM_CHROMA_DIR={self.chroma}\n"
            f"RESTIC_CACHE_DIR={self.cache}\n",
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
            "RESTIC_CACHE_DIR": str(self.cache),
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
        gate = self._run(str(GATE))
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        combined = gate.stdout + gate.stderr
        self.assertTrue(
            "snapshot OK" in combined or "current —" in combined or "OK:" in combined,
            combined,
        )

        require = self._run(str(GATE), "--require-current")
        self.assertEqual(require.returncode, 0, require.stdout + require.stderr)

    def test_wrapper_blocks_on_missing_password_fail_closed(self):
        bad_env = self.tmp / "bad.env"
        bad_env.write_text(
            "CONVMEM_BACKUP_PROFILE=complete-data-v2\n"
            f"CONVMEM_DATA_ROOT={self.data_root}\n"
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_PASSWORD_FILE={self.tmp / 'no-such-password'}\n"
            f"CONVMEM_CHROMA_DIR={self.chroma}\n"
            f"RESTIC_CACHE_DIR={self.cache}\n",
            encoding="utf-8",
        )
        env = {**self.env, "CONVMEM_RESTIC_ENV": str(bad_env)}
        proc = self._run(str(WRAPPER), "record", "--list", env=env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("BLOCKED", proc.stderr)
        self.assertNotIn("FAKE_CONVMEM_CALLED", proc.stdout)

    def test_wrapper_reaches_convmem_when_gate_passes(self):
        gate = self._run(str(GATE))
        self.assertEqual(gate.returncode, 0, gate.stderr)

        proc = self._run(str(WRAPPER), "record", "--list")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("FAKE_CONVMEM_CALLED", proc.stdout)

    def test_gate_module_exits_on_workflow_failure(self):
        from backup_workflows import WorkflowOutcome

        with patch("restic_gate.ensure_current_snapshot") as mock_ensure:
            mock_ensure.return_value = WorkflowOutcome(
                status="FAIL",
                message="bad repo",
                exit_code=1,
            )
            with patch("restic_gate.BackupContext.from_env_file") as mock_ctx:
                mock_ctx.return_value = object()
                with self.assertRaises(SystemExit) as ctx:
                    import restic_gate

                    restic_gate.ensure_chroma_snapshot_for_live_write()
                self.assertEqual(ctx.exception.code, 1)

    def test_gate_module_skipped_with_env(self):
        with patch("restic_gate.ensure_current_snapshot") as mock_ensure:
            import restic_gate

            os.environ["CONVMEM_SKIP_RESTIC_GATE"] = "1"
            try:
                restic_gate.ensure_chroma_snapshot_for_live_write()
            finally:
                os.environ.pop("CONVMEM_SKIP_RESTIC_GATE", None)
            mock_ensure.assert_not_called()

    def test_verify_restic_gate_script(self):
        proc = self._run(str(VERIFY))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
