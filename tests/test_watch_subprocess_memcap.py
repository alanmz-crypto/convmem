"""Tests for watch index subprocess memory scope wrapping."""

from __future__ import annotations

import io
import json
import os
import signal
import subprocess
import unittest
from unittest import mock

from watch import IndexSubprocessError, _flush_path_subprocess, _scoped_index_cmd


class ScopedIndexCmdTests(unittest.TestCase):
    _INNER = [
        "/usr/bin/python",
        "convmem.py",
        "index",
        "--file",
        "/tmp/x.jsonl",
        "--now",
    ]

    def setUp(self) -> None:
        for key in list(os.environ):
            if key.startswith("CONVMEM_LIVE_DIAG_"):
                os.environ.pop(key, None)

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
        completed = mock.MagicMock(returncode=0)
        completed.communicate.return_value = ("", "")
        completed.__enter__.return_value = completed
        with (
            mock.patch("config.load_config", return_value={"watch": {}}),
            mock.patch(
                "watch._scoped_index_cmd", side_effect=lambda inner, _cfg, **_: inner
            ),
            mock.patch("subprocess.Popen", return_value=completed) as popen,
        ):
            _flush_path_subprocess("/tmp/x.jsonl", verbose=False)
        inner = popen.call_args.args[0]
        self.assertEqual(inner[-4:], ["index", "--file", "/tmp/x.jsonl", "--now"])
        self.assertEqual(completed.communicate.call_args.kwargs["timeout"], 900)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_child_timeout_is_reported_as_index_failure(self):
        completed = mock.MagicMock(pid=4242, returncode=None)
        completed.communicate.side_effect = [
            subprocess.TimeoutExpired("cmd", 12),
            ("", ""),
        ]
        completed.__enter__.return_value = completed
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
        completed = mock.MagicMock(returncode=137)
        completed.communicate.return_value = ("", "Killed")
        completed.__enter__.return_value = completed
        with (
            mock.patch("config.load_config", return_value={"watch": {}}),
            mock.patch(
                "watch._scoped_index_cmd", side_effect=lambda inner, _cfg, **_: inner
            ),
            mock.patch("subprocess.Popen", return_value=completed),
        ):
            with self.assertRaises(RuntimeError):
                _flush_path_subprocess("/tmp/x.jsonl", verbose=False)


def _admitted_event(**overrides):
    payload = {
        "chunks_reused": 0,
        "chunks_transformed": 1,
        "elapsed_seconds": 0.125,
        "event": "incremental_codex_admitted_run",
        "format": "codex_jsonl",
        "outcome": "committed",
        "provider_requests": {"summarize": 1},
        "source_bytes": 42,
    }
    payload.update(overrides)
    return json.dumps(payload, sort_keys=True)


def _padded_admitted_event(length: int) -> str:
    prefix = '{"event":"incremental_codex_admitted_run","pad":"'
    suffix = '"}'
    pad = length - len(prefix) - len(suffix)
    if pad < 0:
        raise ValueError("length too small for admitted-run event")
    return prefix + ("x" * pad) + suffix


class FlushPathChildEventForwardTests(unittest.TestCase):
    def _run(self, *, returncode=0, stdout="", stderr="", verbose=False):
        completed = mock.MagicMock(returncode=returncode)
        completed.communicate.return_value = (stdout, stderr)
        completed.__enter__.return_value = completed
        buf = io.StringIO()
        with (
            mock.patch("config.load_config", return_value={"watch": {}}),
            mock.patch(
                "watch._scoped_index_cmd", side_effect=lambda inner, _cfg, **_: inner
            ),
            mock.patch("subprocess.Popen", return_value=completed),
            mock.patch("sys.stderr", buf),
        ):
            if returncode != 0:
                with self.assertRaises(IndexSubprocessError) as ctx:
                    _flush_path_subprocess("/tmp/x.jsonl", verbose=verbose)
                return buf.getvalue(), ctx.exception
            result = _flush_path_subprocess("/tmp/x.jsonl", verbose=verbose)
        return buf.getvalue(), result

    def test_allowlisted_json_event_is_forwarded(self):
        event = _admitted_event()
        captured, result = self._run(stderr=event + "\n")
        self.assertEqual(result["subprocess"], True)
        self.assertIn("[watch] child-event: " + event, captured.splitlines())
        self.assertEqual(captured.count("[watch] child-event: "), 1)

    def test_commit_phase_timing_event_is_forwarded(self):
        from watch import _CHILD_EVENT_ALLOWLIST

        event = json.dumps(
            {
                "c1_hold_seconds": 1.25,
                "event": "incremental_commit_phase_timing",
                "full_inventory_passes": {
                    "conversation_summaries": 2,
                    "knowledge_units": 2,
                },
                "phases": {"apply": 0.2, "non_source_digest": 0.8},
            },
            sort_keys=True,
        )
        self.assertIn("incremental_commit_phase_timing", _CHILD_EVENT_ALLOWLIST)
        captured, result = self._run(stderr=event + "\n")
        self.assertEqual(result["subprocess"], True)
        self.assertIn("[watch] child-event: " + event, captured.splitlines())

    def test_non_json_stderr_is_dropped(self):
        captured, _result = self._run(
            stderr="Traceback (most recent call last):\nValueError: chunk text\n"
        )
        self.assertEqual(captured, "")

    def test_non_allowlisted_json_is_dropped(self):
        other = json.dumps({"event": "not_on_the_allowlist", "outcome": "committed"})
        array = json.dumps(["incremental_codex_admitted_run"])
        captured, _result = self._run(stderr=other + "\n" + array + "\n")
        self.assertEqual(captured, "")

    def test_line_and_count_caps_hold(self):
        event = _admitted_event()
        oversize = _padded_admitted_event(2049)
        self.assertEqual(len(_padded_admitted_event(2048)), 2048)
        self.assertEqual(len(oversize), 2049)
        stderr = "\n".join([oversize, event, event, event, event, event, event]) + "\n"
        captured, _result = self._run(stderr=stderr)
        lines = [
            line
            for line in captured.splitlines()
            if line.startswith("[watch] child-event: ")
        ]
        self.assertEqual(len(lines), 5)
        self.assertTrue(all(line == "[watch] child-event: " + event for line in lines))
        self.assertNotIn(oversize, captured)

    def test_failure_path_does_not_forward_child_events(self):
        event = _admitted_event(outcome="rolled_back")
        captured, exc = self._run(returncode=1, stderr=event + "\nsecret content\n")
        self.assertNotIn("child-event", captured)
        self.assertIn("secret content", exc.stderr_text)
        self.assertIn(event, exc.stderr_text)
        self.assertEqual(exc.returncode, 1)


if __name__ == "__main__":
    unittest.main()
