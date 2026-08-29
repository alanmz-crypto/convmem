"""Tests for watch index subprocess memory scope wrapping."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from watch import _flush_path_subprocess, _scoped_index_cmd


class ScopedIndexCmdTests(unittest.TestCase):
    _INNER = ["/usr/bin/python", "convmem.py", "index", "--file", "/tmp/x.jsonl"]

    def test_scoped_cmd_when_systemd_run_present(self):
        cfg = {"watch": {}}
        with mock.patch("watch.shutil.which", return_value="/usr/bin/systemd-run"):
            with mock.patch("watch._user_systemd_session_available", return_value=True):
                cmd = _scoped_index_cmd(self._INNER, cfg)
        self.assertEqual(cmd[:6], ["systemd-run", "--user", "--scope", "--quiet", "-p", "MemoryMax=2G"])
        self.assertIn("-p", cmd)
        self.assertIn("MemoryHigh=1500M", cmd)
        self.assertIn("MemorySwapMax=0", cmd)
        sep = cmd.index("--")
        self.assertEqual(cmd[sep + 1 :], self._INNER)

    def test_fallback_when_systemd_run_absent(self):
        cfg = {"watch": {}}
        with mock.patch("watch.shutil.which", return_value=None):
            cmd = _scoped_index_cmd(self._INNER, cfg)
        self.assertEqual(cmd, self._INNER)

    def test_config_override_memory_max(self):
        cfg = {"watch": {"subprocess_memory_max": "1536M", "subprocess_memory_high": "1200M"}}
        with mock.patch("watch.shutil.which", return_value="/usr/bin/systemd-run"):
            with mock.patch("watch._user_systemd_session_available", return_value=True):
                cmd = _scoped_index_cmd(self._INNER, cfg)
        self.assertIn("MemoryMax=1536M", cmd)
        self.assertIn("MemoryHigh=1200M", cmd)


class FlushPathSubprocessTests(unittest.TestCase):
    def test_nonzero_child_raises_runtime_error(self):
        completed = mock.Mock(returncode=137, stdout="", stderr="Killed")
        with mock.patch("config.load_config", return_value={"watch": {}}):
            with mock.patch("watch._scoped_index_cmd", side_effect=lambda inner, _cfg, **_: inner):
                with mock.patch("subprocess.run", return_value=completed):
                    with self.assertRaises(RuntimeError):
                        _flush_path_subprocess("/tmp/x.jsonl", verbose=False)


if __name__ == "__main__":
    unittest.main()
