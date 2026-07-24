"""Tests for external Restic live-write gate (wrapper + snapshot script)."""

from __future__ import annotations

import json
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
COPY_EXTERNAL = REPO_ROOT / "scripts" / "restic-copy-external.sh"


def _restic_available() -> bool:
    return shutil.which("restic") is not None


@unittest.skipUnless(_restic_available(), "restic not on PATH")
class ResticGateTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp = Path(self.td.name)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.data_root = self.tmp / "data"
        self.chroma = self.data_root / "chroma"
        self.chroma.mkdir(parents=True)
        (self.chroma / "seed.txt").write_text("seed\n", encoding="utf-8")
        (self.data_root / "decisions-approved.jsonl").write_text(
            '{"id":"decision-1"}\n', encoding="utf-8"
        )
        (self.data_root / "processed.json").write_text("{}\n", encoding="utf-8")
        (self.data_root / "knowledge_units.jsonl").write_text(
            '{"id":"unit-1"}\n', encoding="utf-8"
        )
        imports = self.data_root / "imports"
        imports.mkdir()
        (imports / "source.jsonl").write_text("source\n", encoding="utf-8")
        worktrees = self.data_root / "worktrees" / "scratch"
        worktrees.mkdir(parents=True)
        (worktrees / "untracked.txt").write_text("scratch\n", encoding="utf-8")
        restore_run = self.data_root / "restore-drill" / "runs" / "scratch"
        restore_run.mkdir(parents=True)
        (restore_run / "restored-copy.txt").write_text("scratch\n", encoding="utf-8")
        self.repo = self.tmp / "repo"
        self.cache = self.tmp / "cache"
        self.cache.mkdir()
        self.pass_file = self.tmp / "restic.password"
        self.pass_file.write_text("test-restic-gate-password\n", encoding="utf-8")
        self.pass_file.chmod(0o600)
        self.env_file = self.tmp / "restic.env"
        self.env_file.write_text(
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_PASSWORD_FILE={self.pass_file}\n"
            f"CONVMEM_DATA_ROOT={self.data_root}\n"
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

    def _init_repo(self) -> None:
        init = self._run(
            "restic",
            "-r",
            str(self.repo),
            f"--password-file={self.pass_file}",
            "init",
        )
        self.assertEqual(init.returncode, 0, init.stderr)

    def test_ensure_snapshot_happy_path(self):
        self._init_repo()

        gate = self._run(str(GATE))
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        self.assertIn("snapshot OK", gate.stdout + gate.stderr)

        require = self._run(str(GATE), "--require-current")
        self.assertEqual(require.returncode, 0, require.stdout + require.stderr)

        snapshots = self._run(
            "restic",
            "-r",
            str(self.repo),
            f"--password-file={self.pass_file}",
            "snapshots",
            "--tag",
            "convmem-data-v1",
            "--json",
        )
        self.assertEqual(snapshots.returncode, 0, snapshots.stderr)
        payload = json.loads(snapshots.stdout)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["paths"], [str(self.data_root)])
        self.assertIn("convmem-chroma", payload[0]["tags"])

    def test_snapshot_recovers_canonical_state_and_excludes_scratch(self):
        self._init_repo()
        gate = self._run(str(GATE))
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)

        listing = self._run(
            "restic",
            "-r",
            str(self.repo),
            f"--password-file={self.pass_file}",
            "ls",
            "latest",
            "--tag",
            "convmem-data-v1",
            "--json",
        )
        self.assertEqual(listing.returncode, 0, listing.stdout + listing.stderr)
        entries = [json.loads(line) for line in listing.stdout.splitlines() if line]
        paths = {entry["path"] for entry in entries if entry.get("path")}
        self.assertIn(str(self.data_root / "chroma" / "seed.txt"), paths)
        self.assertIn(str(self.data_root / "decisions-approved.jsonl"), paths)
        self.assertIn(str(self.data_root / "processed.json"), paths)
        self.assertIn(str(self.data_root / "knowledge_units.jsonl"), paths)
        self.assertIn(str(self.data_root / "imports" / "source.jsonl"), paths)
        self.assertFalse(any("/worktrees/" in path for path in paths))
        self.assertFalse(any("/restore-drill/runs/" in path for path in paths))

        recovered = self._run(
            "restic",
            "-r",
            str(self.repo),
            f"--password-file={self.pass_file}",
            "dump",
            "latest",
            str(self.data_root / "decisions-approved.jsonl"),
            "--tag",
            "convmem-data-v1",
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        self.assertEqual(recovered.stdout, '{"id":"decision-1"}\n')

    def test_current_legacy_chroma_snapshot_does_not_satisfy_data_gate(self):
        self._init_repo()
        legacy = self._run(
            "restic",
            "-r",
            str(self.repo),
            f"--password-file={self.pass_file}",
            "backup",
            str(self.chroma),
            "--tag",
            "convmem-chroma",
        )
        self.assertEqual(legacy.returncode, 0, legacy.stdout + legacy.stderr)

        require = self._run(str(GATE), "--require-current")
        self.assertNotEqual(require.returncode, 0)
        self.assertIn("freshness=none", require.stderr)

        migrated = self._run(str(GATE))
        self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)

    def test_data_tag_for_wrong_path_does_not_satisfy_gate(self):
        self._init_repo()
        other = self.tmp / "other-data"
        other.mkdir()
        (other / "seed.txt").write_text("wrong root\n", encoding="utf-8")
        wrong = self._run(
            "restic",
            "-r",
            str(self.repo),
            f"--password-file={self.pass_file}",
            "backup",
            str(other),
            "--tag",
            "convmem-data-v1",
        )
        self.assertEqual(wrong.returncode, 0, wrong.stdout + wrong.stderr)

        require = self._run(str(GATE), "--require-current")
        self.assertNotEqual(require.returncode, 0)
        self.assertIn("freshness=wrong-path", require.stderr)

    def test_existing_env_derives_data_root_from_chroma_parent(self):
        self._init_repo()
        existing_env = self.tmp / "existing-restic.env"
        existing_env.write_text(
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_PASSWORD_FILE={self.pass_file}\n"
            f"CONVMEM_CHROMA_DIR={self.chroma}\n",
            encoding="utf-8",
        )
        env = {**self.env, "CONVMEM_RESTIC_ENV": str(existing_env)}

        gate = self._run(str(GATE), env=env)
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        self.assertIn(f"backing up {self.data_root}", gate.stdout)

        require = self._run(str(GATE), "--require-current", env=env)
        self.assertEqual(require.returncode, 0, require.stdout + require.stderr)

    def test_rejects_chroma_as_the_complete_data_root(self):
        self._init_repo()
        unsafe_env = self.tmp / "unsafe-restic.env"
        unsafe_env.write_text(
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_PASSWORD_FILE={self.pass_file}\n"
            f"CONVMEM_DATA_ROOT={self.chroma}\n"
            f"CONVMEM_CHROMA_DIR={self.chroma}\n",
            encoding="utf-8",
        )
        env = {**self.env, "CONVMEM_RESTIC_ENV": str(unsafe_env)}

        gate = self._run(str(GATE), env=env)
        self.assertNotEqual(gate.returncode, 0)
        self.assertIn("data root cannot be the Chroma directory", gate.stderr)

    def test_external_copy_selects_complete_data_snapshot(self):
        self._init_repo()
        gate = self._run(str(GATE))
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)

        external = self.tmp / "external-repo"
        init_external = self._run(
            "restic",
            "-r",
            str(external),
            f"--password-file={self.pass_file}",
            "init",
        )
        self.assertEqual(init_external.returncode, 0, init_external.stderr)
        copy_env_file = self.tmp / "copy-restic.env"
        copy_env_file.write_text(
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_EXTERNAL_REPOSITORY={external}\n"
            f"RESTIC_PASSWORD_FILE={self.pass_file}\n",
            encoding="utf-8",
        )
        env = {**self.env, "CONVMEM_RESTIC_ENV": str(copy_env_file)}

        copied = self._run(str(COPY_EXTERNAL), env=env)
        self.assertEqual(copied.returncode, 0, copied.stdout + copied.stderr)

        snapshots = self._run(
            "restic",
            "-r",
            str(external),
            f"--password-file={self.pass_file}",
            "snapshots",
            "--tag",
            "convmem-data-v1",
            "--json",
        )
        self.assertEqual(snapshots.returncode, 0, snapshots.stderr)
        payload = json.loads(snapshots.stdout)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["paths"], [str(self.data_root)])

    def test_wrapper_blocks_on_missing_password_fail_closed(self):
        bad_env = self.tmp / "bad.env"
        bad_env.write_text(
            f"RESTIC_REPOSITORY={self.repo}\n"
            f"RESTIC_PASSWORD_FILE={self.tmp / 'no-such-password'}\n"
            f"CONVMEM_DATA_ROOT={self.data_root}\n"
            f"CONVMEM_CHROMA_DIR={self.chroma}\n",
            encoding="utf-8",
        )
        env = {**self.env, "CONVMEM_RESTIC_ENV": str(bad_env)}
        proc = self._run(str(WRAPPER), "record", "--list", env=env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("BLOCKED", proc.stderr)
        self.assertNotIn("FAKE_CONVMEM_CALLED", proc.stdout)

    def test_wrapper_reaches_convmem_when_gate_passes(self):
        self._init_repo()
        gate = self._run(str(GATE))
        self.assertEqual(gate.returncode, 0, gate.stderr)

        proc = self._run(str(WRAPPER), "record", "--list")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("FAKE_CONVMEM_CALLED", proc.stdout)

    def test_gate_module_exits_on_script_failure(self):
        with patch("restic_gate.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="restic-gate: ERROR: bad repo"
            )
            with self.assertRaises(SystemExit) as ctx:
                import restic_gate

                restic_gate.ensure_chroma_snapshot_for_live_write()
            self.assertEqual(ctx.exception.code, 1)

    def test_gate_module_skipped_with_env(self):
        with patch("restic_gate.subprocess.run") as mock_run:
            import restic_gate

            os.environ["CONVMEM_SKIP_RESTIC_GATE"] = "1"
            try:
                restic_gate.ensure_chroma_snapshot_for_live_write()
            finally:
                os.environ.pop("CONVMEM_SKIP_RESTIC_GATE", None)
            mock_run.assert_not_called()

    def test_verify_restic_gate_script(self):
        proc = self._run(str(VERIFY))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
