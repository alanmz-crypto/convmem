"""Per-CPU crash tripwire: this boot's native faults, attributed to CPUs (read-only).

Background (Arc Poison Pill, 2026-09-24): the "Chroma upsert heap corruption" crashes
were defective CPU cores, not Chroma: an i7-13700K with Raptor Lake Vmin shift.
CPU 8 failed first; CPU 4 failed the next morning once CPU 8 was offline. Both
favoured cores are now kept offline with their sibling threads (CPUs 4, 5, 8, 9).
Degradation spreads, so this check alerts on *any* native fault this boot, and on
a known-bad CPU coming back online.

Signals, all readable without root:

* the kernel log for the current boot (``journalctl -k -b 0``): user-space segfaults
  and traps carry ``likely on CPU N``; machine-check lines carry ``CPU N``;
* systemd-coredump's list for the current boot, because the kernel rate-limits its
  fault lines -- a SIGSEGV/SIGBUS/SIGILL/SIGFPE dump with no matching kernel line is an
  unattributed fault;
* ``/sys/devices/system/cpu/online``.

Known-bad CPUs come from ``[hardware] known_bad_cpus`` in the convmem config, not from
the current offline set, so a failed ``offline-bad-core.service`` is caught too.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HARDWARE_SIGNALS = {4: "SIGILL", 7: "SIGBUS", 8: "SIGFPE", 11: "SIGSEGV"}
SYS_CPU_ONLINE = Path("/sys/devices/system/cpu/online")
PROC_STAT = Path("/proc/stat")
_SAMPLES = 3

_PROCESS = re.compile(r"(?P<process>[^\s\[\]:]+)\[(?P<pid>\d+)\]")
_LIKELY_CPU = re.compile(r"likely on CPU (?P<cpu>\d+)")
_MCE_CPU = re.compile(r"\[Hardware Error\]: CPU (?P<cpu>\d+): Machine Check")
_TRAP = re.compile(r"\btrap (?P<trap>[a-z][a-z ]*?) ip[: ]")
_KINDS = (
    ("segfault at ", "segfault"),
    ("general protection fault", "general_protection"),
    ("Machine check events logged", "machine_check"),
    ("Oops:", "kernel_oops"),
)

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


@dataclass(frozen=True)
class Fault:
    """One native fault the kernel reported this boot."""

    when: str
    kind: str
    cpu: int | None
    process: str
    pid: int | None

    def describe(self) -> str:
        where = f"CPU {self.cpu}" if self.cpu is not None else "unknown CPU"
        who = f"{self.process}[{self.pid}]" if self.pid is not None else self.process
        return f"{who} {self.kind} on {where} at {self.when}"


@dataclass(frozen=True)
class Verdict:
    status: str  # "pass", "warn", "fail" or "skip"
    detail: str


def _fault_kind(message: str) -> str | None:
    if _MCE_CPU.search(message):
        return "machine_check"
    trap = _TRAP.search(message)
    if trap and "traps:" in message:
        return trap.group("trap").replace(" ", "_")
    for needle, kind in _KINDS:
        if needle in message:
            return kind
    return None


def parse_kernel_faults(lines: Iterable[str]) -> list[Fault]:
    """Faults in ``journalctl -k -o short-iso`` output; other lines are ignored."""
    faults: list[Fault] = []
    for line in lines:
        head, sep, message = line.partition(" kernel: ")
        if not sep:
            continue
        kind = _fault_kind(message)
        if kind is None:
            continue
        cpu_match = _LIKELY_CPU.search(message) or _MCE_CPU.search(message)
        proc = _PROCESS.search(message) if kind not in ("machine_check", "kernel_oops") else None
        faults.append(
            Fault(
                when=head.split(" ", 1)[0],
                kind=kind,
                cpu=int(cpu_match.group("cpu")) if cpu_match else None,
                process=proc.group("process") if proc else "kernel",
                pid=int(proc.group("pid")) if proc else None,
            )
        )
    return faults


def parse_cpu_list(text: str) -> set[int]:
    """``0-7,10-23`` -> {0..7, 10..23}."""
    cpus: set[int] = set()
    for part in text.strip().split(","):
        if not part:
            continue
        low, _, high = part.partition("-")
        cpus.update(range(int(low), int(high or low) + 1))
    return cpus


def known_bad_cpus(cfg: Mapping[str, Any] | None) -> set[int]:
    raw = ((cfg or {}).get("hardware") or {}).get("known_bad_cpus") or []
    return {int(cpu) for cpu in raw}


def boot_epoch(proc_stat: Path = PROC_STAT) -> int | None:
    try:
        for line in proc_stat.read_text(encoding="utf-8").splitlines():
            if line.startswith("btime "):
                return int(line.split()[1])
    except (OSError, ValueError):
        return None
    return None


def _run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(argv), capture_output=True, text=True, timeout=30, check=False)


def read_kernel_faults(runner: Runner = _run) -> list[Fault] | None:
    """This boot's kernel faults, or None when the kernel log cannot be read."""
    try:
        done = runner(["journalctl", "-k", "-b", "0", "-o", "short-iso", "--no-pager", "-q"])
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return parse_kernel_faults(done.stdout.splitlines())


def read_coredumps(since_epoch: int, runner: Runner = _run) -> list[dict[str, Any]] | None:
    """systemd-coredump entries since ``since_epoch``; [] when there are none, None if unreadable."""
    try:
        done = runner(["coredumpctl", "list", "--no-pager", "--json=short", "--since", f"@{since_epoch}"])
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        # coredumpctl exits 1 with "No coredumps found." when the list is empty.
        return [] if "No coredumps found" in done.stderr + done.stdout else None
    try:
        rows = json.loads(done.stdout or "[]")
    except json.JSONDecodeError:
        return None
    return rows if isinstance(rows, list) else None


def evaluate(
    faults: list[Fault],
    coredumps: list[dict[str, Any]],
    online: set[int] | None,
    known_bad: set[int],
) -> Verdict:
    """FAIL on a known-bad CPU back online or any fault not pinned to a known-bad CPU."""
    problems: list[str] = []
    back_online = sorted(known_bad & online) if online is not None else []
    if back_online:
        problems.append(
            f"known-bad CPU(s) {back_online} are ONLINE again -- is offline-bad-core.service running?"
        )
    unexplained = [f for f in faults if f.cpu is None or f.cpu not in known_bad]
    if unexplained:
        sample = "; ".join(f.describe() for f in unexplained[:_SAMPLES])
        problems.append(f"{len(unexplained)} native fault(s) not on a known-bad CPU: {sample}")
    reported_pids = {f.pid for f in faults if f.pid is not None}
    orphan_dumps = [
        d for d in coredumps if d.get("sig") in HARDWARE_SIGNALS and d.get("pid") not in reported_pids
    ]
    if orphan_dumps:
        sample = "; ".join(
            f"{Path(str(d.get('exe') or '?')).name}[{d.get('pid')}] {HARDWARE_SIGNALS[d['sig']]}"
            for d in orphan_dumps[:_SAMPLES]
        )
        problems.append(f"{len(orphan_dumps)} crash dump(s) with no CPU in the kernel log: {sample}")
    if problems:
        return Verdict("fail", "; ".join(problems) + " -- see: journalctl -k -b 0 | grep 'likely on CPU'")
    if faults:
        cpus = sorted({f.cpu for f in faults if f.cpu is not None})
        return Verdict(
            "warn",
            f"{len(faults)} fault(s) this boot, all on known-bad CPU(s) {cpus} before they went offline "
            f"(latest: {faults[-1].describe()})",
        )
    offline_note = f"; known-bad CPU(s) {sorted(known_bad)} offline" if known_bad else ""
    return Verdict("pass", f"0 native faults this boot{offline_note}")


def check(
    cfg: Mapping[str, Any] | None,
    *,
    runner: Runner = _run,
    online_path: Path = SYS_CPU_ONLINE,
    proc_stat: Path = PROC_STAT,
) -> Verdict:
    """Gather the three signals and evaluate them; WARN when the tripwire is blind."""
    try:
        known_bad = known_bad_cpus(cfg)
    except (TypeError, ValueError):
        return Verdict("warn", "[hardware] known_bad_cpus must be a list of CPU numbers")
    faults = read_kernel_faults(runner)
    if faults is None:
        return Verdict("warn", "kernel log unreadable (journalctl -k -b 0); CPU fault tripwire is blind")
    since = boot_epoch(proc_stat)
    dumps = read_coredumps(since, runner) if since is not None else None
    try:
        online = parse_cpu_list(online_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        online = None
    verdict = evaluate(faults, dumps or [], online, known_bad)
    if dumps is None and verdict.status == "pass":
        return Verdict("warn", verdict.detail + "; coredump list unreadable (coredumpctl)")
    return verdict
