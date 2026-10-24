"""Per-CPU crash tripwire (cpu_tripwire): kernel log and coredump parsing, verdict policy.

Hermetic: journalctl/coredumpctl are replaced by a fake runner and sysfs/procfs by
temp files. Nothing is crashed. Kernel lines are copied from real i7-13700K logs
(Arc Poison Pill, 2026-09-24/25) plus the kernel's documented trap/MCE formats.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import pytest

from cpu_tripwire import Fault, check, evaluate, parse_cpu_list, parse_kernel_faults

SEGV_CPU8 = (
    "2026-09-25T05:09:57-05:00 archlinux kernel: python3.11[60770]: segfault at 0 ip 0000000000000000 "
    "sp 00007ffc32658af8 error 14 likely on CPU 8 (core 16, socket 0)"
)
SEGV_CPU4 = (
    "2026-09-24T17:17:11-05:00 archlinux kernel: node[5123]: segfault at 7f00 ip 00007f1 sp 00007ff "
    "error 4 in libnode.so[7f00+100] likely on CPU 4 (core 8, socket 0)"
)
GP_NO_CPU = (
    "2026-09-24T17:20:02-05:00 archlinux kernel: traps: python3.11[7788] general protection fault "
    "ip:7f3a sp:7ffd error:0 in libhnsw.so[7f3a+2000]"
)
INVALID_OPCODE = (
    "2026-09-24T17:21:00-05:00 archlinux kernel: traps: rg[9001] trap invalid opcode ip:55e0 sp:7ffc "
    "error:0 in rg[55e0+1000] likely on CPU 10 (core 20, socket 0)"
)
MCE = "2026-09-24T17:22:00-05:00 archlinux kernel: mce: [Hardware Error]: CPU 8: Machine Check: 0 Bank 1: b200"
TYPORA_GPF = (
    "2026-10-16T22:31:33-05:00 archlinux kernel: traps: Typora[2198961] general protection fault "
    "ip:55c9153ebb7b sp:7fff1c4096a0 error:0 in Typora[2acdb7b,55c914f9f000+9aa1000]"
)
NOISE = [
    "2026-09-25T04:37:19-05:00 archlinux kernel: smpboot: Total of 24 processors activated",
    "2026-09-25T05:11:26-05:00 archlinux kernel: smpboot: CPU 8 is now offline",
    "2026-09-25T06:00:00-05:00 archlinux kernel: usb 1-4: new high-speed USB device number 5",
]
KNOWN_BAD = {"hardware": {"known_bad_cpus": [8, 9]}}


@pytest.fixture(autouse=True)
def _isolated_ack_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))


def _fault(cpu: int | None, pid: int | None = 1) -> Fault:
    return Fault("t", "segfault", cpu, "p", pid)


def test_parses_real_fault_lines_and_ignores_the_rest() -> None:
    faults = parse_kernel_faults(
        [*NOISE, SEGV_CPU8, SEGV_CPU4, GP_NO_CPU, INVALID_OPCODE, MCE]
    )
    assert [(f.kind, f.cpu, f.process, f.pid) for f in faults] == [
        ("segfault", 8, "python3.11", 60770),
        ("segfault", 4, "node", 5123),
        ("general_protection", None, "python3.11", 7788),
        ("invalid_opcode", 10, "rg", 9001),
        ("machine_check", 8, "kernel", None),
    ]
    assert faults[0].when == "2026-09-25T05:09:57-05:00"


def test_cpu_list_ranges() -> None:
    assert parse_cpu_list("0-7,10-23\n") == set(range(8)) | set(range(10, 24))
    assert parse_cpu_list("0") == {0}


def test_clean_boot_passes() -> None:
    verdict = evaluate([], [], set(range(8)) | set(range(10, 24)), {8, 9})
    assert verdict.status == "pass" and "[8, 9] offline" in verdict.detail


def test_faults_only_on_a_known_bad_cpu_warn() -> None:
    verdict = evaluate([_fault(8)], [{"pid": 1, "sig": 11}], set(range(8)), {8, 9})
    assert verdict.status == "warn"


def test_cpu_attributed_fault_on_healthy_cpu_still_fails() -> None:
    # Kernel pinned the fault to CPU 4, which is not known-bad -> real per-CPU alarm, FAIL.
    assert evaluate([_fault(4)], [], set(range(8)), {8, 9}).status == "fail"


def test_userspace_fault_no_cpu_warns() -> None:
    # No CPU attribution and not a machine check -> advisory WARN, not a gate-failing FAIL.
    assert evaluate([_fault(None)], [], set(range(8)), {8, 9}).status == "warn"
    # A kernel-CPU-attributed fault stays FAIL even with nothing configured known-bad.
    assert evaluate([_fault(8)], [], set(range(8)), set()).status == "fail"


def test_userspace_gpf_no_cpu_warns_and_names_process() -> None:
    gpf = Fault("t", "general_protection", None, "python3.11", 7788)
    verdict = evaluate([gpf], [], set(range(8)), {8, 9})
    assert verdict.status == "warn"
    assert "python3.11[7788]" in verdict.detail and "advisory" in verdict.detail


def test_machine_check_always_fails() -> None:
    mce = Fault("t", "machine_check", None, "kernel", None)
    assert evaluate([mce], [], set(range(8)), {8, 9}).status == "fail"


def test_hardware_fail_dominates_userspace_warn() -> None:
    mce = Fault("t", "machine_check", None, "kernel", None)
    typora = Fault("t", "general_protection", None, "Typora", 2198961)
    verdict = evaluate([mce, typora], [], set(range(8)), {8, 9})
    assert verdict.status == "fail"


def test_known_bad_cpu_back_online_fails() -> None:
    verdict = evaluate([], [], set(range(24)), {8, 9})
    assert verdict.status == "fail" and "ONLINE again" in verdict.detail


def test_crash_dump_without_a_kernel_line_warns_and_aborts_excluded() -> None:
    # Orphan hardware-signal dump is now a visible WARN (was FAIL); SIGABRT electron dump stays excluded.
    dumps = [
        {"pid": 42, "sig": 11, "exe": "/usr/bin/python3.11"},
        {"pid": 43, "sig": 6, "exe": "/x/electron"},
    ]
    verdict = evaluate([], dumps, set(range(8)), {8, 9})
    assert verdict.status == "warn" and "python3.11[42] SIGSEGV" in verdict.detail
    assert "electron" not in verdict.detail


class _FakeRunner:
    def __init__(self, journal: list[str] | None, dumps: list[dict] | None) -> None:
        self.journal, self.dumps = journal, dumps
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        if argv[0] == "journalctl":
            if self.journal is None:
                return subprocess.CompletedProcess(
                    argv, 1, "", "No journal files were opened"
                )
            rows = self.journal
            if "json" in argv:
                rows = []
                for index, line in enumerate(self.journal):
                    head, _, message = line.partition(" kernel: ")
                    stamp = datetime.fromisoformat(head.split(" ", 1)[0])
                    rows.append(
                        json.dumps(
                            {
                                "MESSAGE": message,
                                "_BOOT_ID": "a" * 32,
                                "__REALTIME_TIMESTAMP": str(
                                    int(stamp.timestamp()) * 1_000_000
                                ),
                                "_SOURCE_MONOTONIC_TIMESTAMP": str(index + 1),
                                "__CURSOR": f"test-{index}",
                            }
                        )
                    )
            return subprocess.CompletedProcess(argv, 0, "\n".join(rows), "")
        if self.dumps is None:
            return subprocess.CompletedProcess(argv, 1, "", "boom")
        if not self.dumps:
            return subprocess.CompletedProcess(argv, 1, "", "No coredumps found.\n")
        return subprocess.CompletedProcess(argv, 0, json.dumps(self.dumps), "")


def _sys(tmp_path: Path, online: str = "0-7,10-23") -> dict[str, Path]:
    (tmp_path / "online").write_text(online + "\n", encoding="utf-8")
    (tmp_path / "stat").write_text("cpu  1 2 3\nbtime 1790329033\n", encoding="utf-8")
    return {"online_path": tmp_path / "online", "proc_stat": tmp_path / "stat"}


def test_check_reads_this_boot_only(tmp_path: Path) -> None:
    runner = _FakeRunner(
        [*NOISE, SEGV_CPU8], [{"pid": 60770, "sig": 11, "exe": "/bin/python3.11"}]
    )
    verdict = check(KNOWN_BAD, runner=runner, **_sys(tmp_path))
    assert verdict.status == "warn"
    assert runner.calls[0][:4] == ["journalctl", "-k", "-b", "0"]
    assert runner.calls[1][-2:] == ["--since", "@1790329033"]


def test_check_empty_coredump_list_passes(tmp_path: Path) -> None:
    assert (
        check(KNOWN_BAD, runner=_FakeRunner(NOISE, []), **_sys(tmp_path)).status
        == "pass"
    )


def test_check_real_typora_userspace_fault_warns_not_fail(tmp_path: Path) -> None:
    # The observed 2026-10-16 Typora GPF (no CPU attribution) must not exit doctor 1.
    runner = _FakeRunner([*NOISE, TYPORA_GPF], [])
    verdict = check(KNOWN_BAD, runner=runner, **_sys(tmp_path))
    assert verdict.status == "warn" and "Typora[2198961]" in verdict.detail


def test_blind_tripwire_warns(tmp_path: Path) -> None:
    assert (
        check(KNOWN_BAD, runner=_FakeRunner(None, []), **_sys(tmp_path)).status
        == "warn"
    )
    assert (
        check(KNOWN_BAD, runner=_FakeRunner(NOISE, None), **_sys(tmp_path)).status
        == "warn"
    )
    bad_cfg = {"hardware": {"known_bad_cpus": ["eight"]}}
    assert (
        check(bad_cfg, runner=_FakeRunner(NOISE, []), **_sys(tmp_path)).status == "warn"
    )


def test_doctor_maps_the_verdict(monkeypatch) -> None:
    import cpu_tripwire
    from cpu_tripwire import Verdict
    from doctor import _check_cpu_tripwire

    monkeypatch.setattr(cpu_tripwire, "check", lambda cfg: Verdict("fail", "x"))
    result = _check_cpu_tripwire({})
    assert result.effective_status() == "fail" and not result.ok
    monkeypatch.setattr(cpu_tripwire, "check", lambda cfg: Verdict("warn", "y"))
    assert _check_cpu_tripwire({}).ok


# ref: ../cpu_tripwire.py, ../cpu_tripwire_events.py — legacy policy and JSON reader regression coverage
