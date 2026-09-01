"""Tests for watch index subprocess memory scope wrapping."""

from __future__ import annotations

import signal
import subprocess
import unittest
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
    def test_child_has_a_default_timeout(self):
        completed = mock.Mock(returncode=0)
        completed.communicate.return_value = ("", "")
        with (
            mock.patch("config.load_config", return_value={"watch": {}}),
            mock.patch(
                "watch._scoped_index_cmd", side_effect=lambda inner, _cfg, **_: inner
            ),
            mock.patch("subprocess.Popen", return_value=completed) as popen,
        ):
            _flush_path_subprocess("/tmp/x.jsonl", verbose=False)
        self.assertEqual(completed.communicate.call_args.kwargs["timeout"], 900)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_child_timeout_is_reported_as_index_failure(self):
        completed = mock.Mock(pid=4242, returncode=None)
        completed.communicate.side_effect = [
            subprocess.TimeoutExpired("cmd", 12),
            ("", ""),
        ]
        with (
            mock.patch(
                "config.load_config",
                return_value={"watch": {"subprocess_timeout_seconds": 12}},
            ),
            mock.patch(
                "watch._scoped_index_cmd", side_effect=lambda inner, _cfg, **_: inner
            ),
            mock.patch("subprocess.Popen", return_value=completed),
            mock.patch("watch.os.killpg") as killpg,
        ):
            with self.assertRaisesRegex(RuntimeError, "timed out after 12 seconds"):
                _flush_path_subprocess("/tmp/x.jsonl", verbose=False)
        killpg.assert_called_once_with(4242, signal.SIGTERM)

    def test_nonzero_child_raises_runtime_error(self):
        completed = mock.Mock(returncode=137)
        completed.communicate.return_value = ("", "Killed")
        with (
            mock.patch("config.load_config", return_value={"watch": {}}),
            mock.patch(
                "watch._scoped_index_cmd", side_effect=lambda inner, _cfg, **_: inner
            ),
            mock.patch("subprocess.Popen", return_value=completed),
        ):
            with self.assertRaises(RuntimeError):
                _flush_path_subprocess("/tmp/x.jsonl", verbose=False)


if __name__ == "__main__":
    unittest.main()
