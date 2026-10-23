"""Claude C1/C2: preserve fault evidence across record and decoding boundaries."""

import hashlib
import json
import subprocess

import pytest

import cpu_tripwire as tripwire
import cpu_tripwire_ack as ack
from tests import test_cpu_tripwire_ack as fixtures

# Reuse the autouse HOME, timezone, proc/sys, subprocess and network guard.
hermetic = fixtures.hermetic


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
@pytest.mark.parametrize("read_mode", ["complete", "timeout_text", "timeout_bytes"])
def test_claude_c1_journal_records_split_only_on_lf(separator, read_mode):
    message = (
        fixtures.MESSAGE.replace("CPU 13", "CPU 14") + separator + "diagnostic suffix"
    )
    output = "\n\n" + json.dumps(fixtures.entry(message), ensure_ascii=False) + "\n\n"
    assert separator in output

    def journal(argv):
        assert argv[0] == "journalctl"
        if read_mode != "complete":
            partial = output.encode("utf-8") if read_mode == "timeout_bytes" else output
            raise subprocess.TimeoutExpired(argv, 1, output=partial)
        return subprocess.CompletedProcess(argv, 0, output, "")

    result = tripwire.read_kernel_faults(journal)
    assert len(result.faults) == 1
    fault = result.faults[0]
    assert fault.cpu == 14 and fault.kind == "segfault"
    assert fault.message == message.encode("utf-8")
    assert (
        fault.key.message_sha256 == hashlib.sha256(message.encode("utf-8")).hexdigest()
    )
    assert result.problems == (
        [] if read_mode == "complete" else ["journalctl timed out"]
    )
    verdict = tripwire.evaluate_signals(
        tripwire.SignalRead(result, [], set(), {4, 5, 8, 9}), ack.AckSet(), None
    )
    assert verdict.status == "fail" and "CPU 14" in verdict.detail


@pytest.mark.parametrize(
    "failed_reader,has_fault,online,status,detail",
    [
        ("coredumpctl", True, "0-3,6-7,10-19", "fail", "timeshift"),
        ("journalctl", False, "0-23", "fail", "ONLINE again"),
        ("journalctl", False, "0-3,6-7,10-19", "warn", "kernel log unreadable"),
        ("coredumpctl", False, "0-3,6-7,10-19", "warn", "coredump list unreadable"),
    ],
)
def test_claude_c2_reader_decode_error_preserves_other_signals(
    tmp_path, *, failed_reader, has_fault, online, status, detail
):
    runner = fixtures.FakeRunner([fixtures.entry()] if has_fault else [])

    def undecodable(argv):
        if argv[0] == failed_reader:
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        return runner(argv)

    result = tripwire.check(
        fixtures.CFG, runner=undecodable, **fixtures.paths(tmp_path, online=online)
    )
    assert result.status == status and detail in result.detail


# ref: ../cpu_tripwire.py, ./test_cpu_tripwire_ack.py — reader boundaries and shared hermetic fixtures
# src: ../docs/inter-model/KIRO-2026-10-22-doctor-fault-ack-design-review-handoff.md — Claude C1/C2
