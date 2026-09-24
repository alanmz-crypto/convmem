"""Tests for the watch.py native-crash circuit breaker (Arc Poison Pill hardening)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from watch import (
    CircuitBreakerState,
    is_native_fault_returncode,
    is_timeout_message,
    log_native_crash,
    parse_native_fault_returncode,
)


class ParseNativeFaultReturncodeTests(unittest.TestCase):
    def test_parses_signal_death(self):
        self.assertEqual(parse_native_fault_returncode("index subprocess exit -11"), -11)

    def test_parses_ordinary_nonzero_exit(self):
        self.assertEqual(parse_native_fault_returncode("index subprocess exit 1"), 1)

    def test_none_for_timeout_message(self):
        self.assertIsNone(
            parse_native_fault_returncode("index subprocess timed out after 900 seconds")
        )

    def test_none_for_ordinary_error_text(self):
        self.assertIsNone(parse_native_fault_returncode("Traceback: some parse error"))


class IsNativeFaultReturncodeTests(unittest.TestCase):
    def test_sigsegv_sigabrt_sigbus_are_native_faults(self):
        for code in (-11, -6, -7):
            self.assertTrue(is_native_fault_returncode(code))

    def test_sigkill_sigterm_are_not_native_faults(self):
        for code in (-9, -15):
            self.assertFalse(is_native_fault_returncode(code))

    def test_ordinary_nonzero_exit_is_not_a_native_fault(self):
        self.assertFalse(is_native_fault_returncode(1))

    def test_none_is_not_a_native_fault(self):
        self.assertFalse(is_native_fault_returncode(None))


class IsTimeoutMessageTests(unittest.TestCase):
    def test_matches_timeout_shape(self):
        self.assertTrue(is_timeout_message("index subprocess timed out after 900 seconds"))

    def test_does_not_match_native_fault(self):
        self.assertFalse(is_timeout_message("index subprocess exit -11"))


class CircuitBreakerStateTests(unittest.TestCase):
    def setUp(self):
        # pylint: disable-next=consider-using-with
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.state_path = Path(tmp_dir.name) / "watch_circuit_breaker.json"

    def _fresh(self) -> CircuitBreakerState:
        return CircuitBreakerState(self.state_path)

    def test_native_fault_increments_per_path_counter(self):
        breaker = self._fresh()
        breaker.record_failure("a.jsonl", native_fault=True, timeout=False, crash_threshold=3)
        entry = json.loads(self.state_path.read_text())["paths"]["a.jsonl"]
        self.assertEqual(entry["native_crash_count"], 1)
        self.assertFalse(entry["quarantined"])

    def test_quarantine_after_n_consecutive_native_faults(self):
        breaker = self._fresh()
        for _ in range(2):
            quarantined = breaker.record_failure(
                "a.jsonl", native_fault=True, timeout=False, crash_threshold=3
            )
            self.assertFalse(quarantined)
        quarantined = breaker.record_failure(
            "a.jsonl", native_fault=True, timeout=False, crash_threshold=3
        )
        self.assertTrue(quarantined)
        self.assertTrue(breaker.is_quarantined("a.jsonl"))

    def test_reset_on_success(self):
        breaker = self._fresh()
        breaker.record_failure("a.jsonl", native_fault=True, timeout=False, crash_threshold=3)
        breaker.record_success("a.jsonl")
        self.assertFalse(breaker.is_quarantined("a.jsonl"))
        # Counter reset: two more faults should not yet quarantine at threshold 3.
        breaker.record_failure("a.jsonl", native_fault=True, timeout=False, crash_threshold=3)
        breaker.record_failure("a.jsonl", native_fault=True, timeout=False, crash_threshold=3)
        self.assertFalse(breaker.is_quarantined("a.jsonl"))

    def test_non_signal_failure_is_not_counted(self):
        breaker = self._fresh()
        for _ in range(5):
            quarantined = breaker.record_failure(
                "a.jsonl", native_fault=False, timeout=False, crash_threshold=3
            )
            self.assertFalse(quarantined)
        self.assertFalse(breaker.is_quarantined("a.jsonl"))
        self.assertFalse(breaker.global_breaker_tripped(global_threshold=5))

    def test_timeout_has_independent_threshold(self):
        breaker = self._fresh()
        for _ in range(2):
            quarantined = breaker.record_failure(
                "a.jsonl", native_fault=False, timeout=True, timeout_threshold=3
            )
            self.assertFalse(quarantined)
        quarantined = breaker.record_failure(
            "a.jsonl", native_fault=False, timeout=True, timeout_threshold=3
        )
        self.assertTrue(quarantined)
        # Timeouts do not feed the global native-fault breaker.
        self.assertFalse(breaker.global_breaker_tripped(global_threshold=1))

    def test_global_breaker_trips_across_different_paths(self):
        breaker = self._fresh()
        now = 1_000_000.0
        for i in range(4):
            breaker.record_failure(
                f"path-{i}.jsonl", native_fault=True, timeout=False, crash_threshold=99, now=now
            )
        # No single path hit its own (very high) per-path threshold.
        self.assertFalse(breaker.is_quarantined("path-0.jsonl"))
        self.assertFalse(
            breaker.global_breaker_tripped(now=now, global_threshold=5, global_window_seconds=1800)
        )
        breaker.record_failure(
            "path-4.jsonl", native_fault=True, timeout=False, crash_threshold=99, now=now
        )
        self.assertTrue(
            breaker.global_breaker_tripped(now=now, global_threshold=5, global_window_seconds=1800)
        )

    def test_global_breaker_window_ages_out(self):
        breaker = self._fresh()
        for i in range(5):
            breaker.record_failure(
                f"path-{i}.jsonl",
                native_fault=True,
                timeout=False,
                crash_threshold=99,
                now=1_000_000.0,
            )
        self.assertTrue(
            breaker.global_breaker_tripped(
                now=1_000_000.0, global_threshold=5, global_window_seconds=1800
            )
        )
        # 2000s later, all five events have aged out of a 1800s window.
        self.assertFalse(
            breaker.global_breaker_tripped(
                now=1_000_000.0 + 2000, global_threshold=5, global_window_seconds=1800
            )
        )

    def test_state_persists_atomically_across_instances(self):
        breaker = self._fresh()
        breaker.record_failure("a.jsonl", native_fault=True, timeout=False, crash_threshold=1)
        self.assertTrue(self.state_path.exists())
        for name in self.state_path.parent.iterdir():
            self.assertFalse(name.name.endswith(tuple(f".tmp{n}" for n in range(100000))))
        reloaded = CircuitBreakerState(self.state_path)
        self.assertTrue(reloaded.is_quarantined("a.jsonl"))

    def test_clear_one_path(self):
        breaker = self._fresh()
        breaker.record_failure("a.jsonl", native_fault=True, timeout=False, crash_threshold=1)
        breaker.record_failure("b.jsonl", native_fault=True, timeout=False, crash_threshold=1)
        breaker.clear("a.jsonl")
        self.assertFalse(breaker.is_quarantined("a.jsonl"))
        self.assertTrue(breaker.is_quarantined("b.jsonl"))

    def test_clear_all(self):
        breaker = self._fresh()
        breaker.record_failure("a.jsonl", native_fault=True, timeout=False, crash_threshold=1)
        breaker.record_failure("b.jsonl", native_fault=True, timeout=False, crash_threshold=1)
        breaker.clear()
        self.assertFalse(breaker.is_quarantined("a.jsonl"))
        self.assertFalse(breaker.is_quarantined("b.jsonl"))

    def test_corrupt_state_file_does_not_crash(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text("{not json", encoding="utf-8")
        breaker = self._fresh()
        self.assertFalse(breaker.is_quarantined("a.jsonl"))


class LogNativeCrashTests(unittest.TestCase):
    def test_appends_jsonl_entry(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "native_crash_failures.jsonl"
            log_native_crash("a.jsonl", "index subprocess exit -11", log_path=log_path)
            log_native_crash("b.jsonl", "index subprocess exit -11", log_path=log_path)
            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            entry = json.loads(lines[0])
            self.assertEqual(entry["path"], "a.jsonl")
            self.assertIn("ts", entry)


if __name__ == "__main__":
    unittest.main()
