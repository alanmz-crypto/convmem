"""Per-CPU crash tripwire: this boot's native faults, attributed to CPUs (read-only).

Background (Arc Poison Pill, 2026-09-24): the "Chroma upsert heap corruption" crashes
were defective CPU cores, not Chroma: an i7-13700K with Raptor Lake Vmin shift.
CPU 8 failed first; CPU 4 failed the next morning once CPU 8 was offline. Both
favoured cores are now kept offline with their sibling threads (CPUs 4, 5, 8, 9).

Policy (Ryan, 2026-10-17, after the Poison Pill CPU was fixed): FAIL only on
*unambiguous hardware* signals -- a machine-check event, a fault the kernel pinned
to a CPU that is not already known-bad, or a known-bad CPU coming back online.
Ambiguous userspace faults with no CPU attribution (a desktop app, or even convmem's
own native code) are demoted to a visible WARN: still surfaced, no longer a hard
stop that stalls every agent at session start. FAIL always dominates WARN.

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
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cpu_tripwire_ack import AckContext, AckSet, load_acks
from cpu_tripwire_events import (
    Fault,
    JournalRead,
    normalize_boot_id,
    parse_kernel_faults,
    parse_kernel_journal,
)

__all__ = ["Fault", "check", "evaluate", "parse_cpu_list", "parse_kernel_faults"]

HARDWARE_SIGNALS = {4: "SIGILL", 7: "SIGBUS", 8: "SIGFPE", 11: "SIGSEGV"}
SYS_CPU_ONLINE = Path("/sys/devices/system/cpu/online")
PROC_STAT = Path("/proc/stat")
_SAMPLES = 3

BOOT_ID_PATH = Path("/proc/sys/kernel/random/boot_id")
Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


@dataclass(frozen=True)
class Verdict:
    status: str  # "pass", "warn", "fail" or "skip"
    detail: str


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
    hardware = (cfg or {}).get("hardware") or {}
    if not isinstance(hardware, Mapping):
        raise TypeError("[hardware] must be a table")
    raw = hardware.get("known_bad_cpus", [])
    if not isinstance(raw, list) or any(
        not isinstance(cpu, int) or isinstance(cpu, bool) or cpu < 0 for cpu in raw
    ):
        raise ValueError("known_bad_cpus must be a list of nonnegative CPU numbers")
    return set(raw)


def boot_epoch(proc_stat: Path = PROC_STAT) -> int | None:
    try:
        for line in proc_stat.read_text(encoding="utf-8").splitlines():
            if line.startswith("btime "):
                return int(line.split()[1])
    except (OSError, ValueError):
        return None
    return None


def _run(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv), capture_output=True, text=True, timeout=30, check=False
    )


def read_kernel_faults(runner: Runner = _run) -> JournalRead:
    """Read once, preserving detected faults when other entries are unreadable."""
    try:
        done = runner(
            [
                "journalctl",
                "-k",
                "-b",
                "0",
                "-o",
                "json",
                "--all",
                "--output-fields=MESSAGE,_SOURCE_MONOTONIC_TIMESTAMP,_HOSTNAME",
                "--no-pager",
                "-q",
            ]
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        result = parse_kernel_journal(line for line in output.split("\n") if line)
        result.problems.append("journalctl timed out")
        return result
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return JournalRead(problems=["journalctl failed"])
    result = parse_kernel_journal(line for line in done.stdout.split("\n") if line)
    if done.returncode != 0:
        result.problems.append("journalctl failed")
    return result


def read_boot_id(path: Path = BOOT_ID_PATH) -> str | None:
    try:
        return normalize_boot_id(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError):
        return None


def read_coredumps(
    since_epoch: int, runner: Runner = _run
) -> list[dict[str, Any]] | None:
    """systemd-coredump entries since ``since_epoch``; [] when there are none, None if unreadable."""
    try:
        done = runner(
            [
                "coredumpctl",
                "list",
                "--no-pager",
                "--json=short",
                "--since",
                f"@{since_epoch}",
            ]
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None
    if done.returncode != 0:
        # coredumpctl exits 1 with "No coredumps found." when the list is empty.
        return [] if "No coredumps found" in done.stderr + done.stdout else None
    try:
        rows = json.loads(done.stdout or "[]")
    except (ValueError, RecursionError):
        return None
    if not isinstance(rows, list) or any(
        not isinstance(row, dict)
        or type(row.get("pid")) is not int  # pylint: disable=unidiomatic-typecheck
        or type(row.get("sig")) is not int  # pylint: disable=unidiomatic-typecheck
        for row in rows
    ):
        return None
    return rows


def _base_evaluate(
    faults: list[Fault],
    coredumps: list[dict[str, Any]],
    online: set[int] | None,
    known_bad: set[int],
) -> Verdict:
    """FAIL only on unambiguous hardware signals; demote ambiguous userspace faults to WARN.

    Hardware (FAIL): a known-bad CPU back online, a fault the kernel pinned to a CPU that is
    not already known-bad, or any machine-check event. Everything else -- userspace faults
    with no CPU attribution and orphan crash dumps -- is a visible WARN, not a gate-failing
    FAIL (Ryan, 2026-10-17: Poison Pill CPU fixed, so unexplained userspace faults are no
    longer treated as possible silent-silicon corruption). FAIL always dominates WARN.
    """
    problems: list[str] = []  # FAIL-level: unambiguous hardware
    warn_notes: list[str] = []  # WARN-level: ambiguous userspace, non-blocking

    back_online = sorted(known_bad & online) if online is not None else []
    if back_online:
        problems.append(
            f"known-bad CPU(s) {back_online} are ONLINE again -- is offline-bad-core.service running?"
        )

    # Hardware faults: kernel-attributed to a healthy CPU, or any machine-check event.
    hardware_faults = [
        f
        for f in faults
        if (f.cpu is not None and f.cpu not in known_bad) or f.kind == "machine_check"
    ]
    if hardware_faults:
        sample = "; ".join(f.describe() for f in hardware_faults[:_SAMPLES])
        problems.append(
            f"{len(hardware_faults)} hardware fault(s) not on a known-bad CPU: {sample}"
        )

    # Userspace faults: no CPU attribution and not a machine check. Advisory only.
    userspace_faults = [
        f for f in faults if f.cpu is None and f.kind != "machine_check"
    ]
    if userspace_faults:
        sample = "; ".join(f.describe() for f in userspace_faults[:_SAMPLES])
        warn_notes.append(
            f"{len(userspace_faults)} userspace fault(s) this boot, no CPU attribution (advisory): {sample}"
        )

    # Orphan crash dumps (hardware signal, no matching kernel line): advisory, not blocking.
    reported_pids = {f.pid for f in faults if f.pid is not None}
    orphan_dumps = [
        d
        for d in coredumps
        if d.get("sig") in HARDWARE_SIGNALS and d.get("pid") not in reported_pids
    ]
    if orphan_dumps:
        sample = "; ".join(
            f"{Path(str(d.get('exe') or '?')).name}[{d.get('pid')}] {HARDWARE_SIGNALS[d['sig']]}"
            for d in orphan_dumps[:_SAMPLES]
        )
        warn_notes.append(
            f"{len(orphan_dumps)} crash dump(s) with no CPU in the kernel log: {sample}"
        )

    if problems:
        return Verdict(
            "fail",
            "; ".join(problems) + " -- see: journalctl -k -b 0 | grep 'likely on CPU'",
        )

    # Faults confined to known-bad CPUs (before they went offline) stay a WARN with their own note.
    known_bad_faults = [f for f in faults if f.cpu is not None and f.cpu in known_bad]
    if known_bad_faults:
        cpus = sorted({f.cpu for f in known_bad_faults})
        warn_notes.append(
            f"{len(known_bad_faults)} fault(s) this boot, all on known-bad CPU(s) {cpus} before they "
            f"went offline (latest: {known_bad_faults[-1].describe()})"
        )

    if warn_notes:
        return Verdict("warn", "; ".join(warn_notes))

    offline_note = (
        f"; known-bad CPU(s) {sorted(known_bad)} offline" if known_bad else ""
    )
    return Verdict("pass", f"0 native faults this boot{offline_note}")


@dataclass
class SignalRead:
    journal: JournalRead
    dumps: list[dict[str, Any]] | None
    online: set[int] | None
    known_bad: set[int]
    config_problem: str | None = None

    def ack_context(self, boot_id: str | None) -> AckContext:
        problem = self.config_problem
        if self.journal.problems:
            problem = "kernel log incomplete: " + self.journal.problems[0]
        if boot_id is None or any(value != boot_id for value in self.journal.boot_ids):
            problem = "boot identity mismatch"
        return AckContext(
            self.journal.faults, boot_id, self.known_bad, self.dumps or [], problem
        )


def read_signals(
    cfg: Mapping[str, Any] | None,
    *,
    runner: Runner = _run,
    online_path: Path = SYS_CPU_ONLINE,
    proc_stat: Path = PROC_STAT,
) -> SignalRead:
    problem = None
    try:
        known_bad = known_bad_cpus(cfg)
    except (TypeError, ValueError):
        known_bad = set()
        problem = "[hardware] known_bad_cpus must be a list of CPU numbers"
    journal = read_kernel_faults(runner)
    since = boot_epoch(proc_stat)
    dumps = read_coredumps(since, runner) if since is not None else None
    try:
        online = parse_cpu_list(online_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        online = None
    return SignalRead(journal, dumps, online, known_bad, problem)


def evaluate(
    faults: list[Fault],
    coredumps: list[dict[str, Any]],
    online: set[int] | None,
    known_bad: set[int],
    *,
    acks: AckSet | None = None,
    current_boot_id: str | None = None,
    ack_problem: str | None = None,
) -> Verdict:
    """Apply only unique exact acknowledgments; every other FAIL remains a FAIL."""
    if acks is None:
        return _base_evaluate(faults, coredumps, online, known_bad)
    if current_boot_id is None and acks.present:
        ack_problem = ack_problem or "boot identity mismatch"
    selection = acks.select(
        AckContext(faults, current_boot_id, known_bad, coredumps, ack_problem)
    )
    keys = {fault.key for fault, _ in selection.applied}
    explained_pids = {fault.pid for fault, _ in selection.applied}
    verdict = _base_evaluate(
        [fault for fault in faults if fault.key not in keys],
        [dump for dump in coredumps if dump.get("pid") not in explained_pids],
        online,
        known_bad,
    )
    status, detail = verdict.status, verdict.detail
    if selection.applied:
        descriptions = "; ".join(
            f"{fault.describe()} [ack {record['ack_id'][:12]} by {record['acknowledged_by']} "
            f"{record['acknowledged_at']}: {record['reason'][:80]}]"
            for fault, record in selection.applied
        )
        count = len(selection.applied)
        note = f"{count} acknowledged CPU-attributed fault(s), not cleared (hardware health unproven): {descriptions}"
        if status == "fail":
            ids = ", ".join(
                "ack " + record["ack_id"][:12] for _, record in selection.applied
            )
            detail += f"; plus {count} acknowledged fault ({ids}); {note}"
        elif status == "pass":
            status, detail = "warn", note
        else:
            detail = note + "; " + detail
    if selection.notes:
        detail += "; " + "; ".join(selection.notes)
    if selection.degraded and status == "pass":
        status = "warn"
    return Verdict(status, detail)


def evaluate_signals(signals: SignalRead, acks: AckSet, boot_id: str | None) -> Verdict:
    context = signals.ack_context(boot_id) if acks.present else None
    verdict = evaluate(
        signals.journal.faults,
        signals.dumps or [],
        signals.online,
        signals.known_bad,
        acks=acks,
        current_boot_id=boot_id,
        ack_problem=context.problem if context else None,
    )
    notes = []
    if signals.config_problem:
        notes.append(signals.config_problem)
    if signals.journal.problems:
        notes.append(
            "kernel log unreadable or incomplete (journalctl -k -b 0); "
            "CPU fault tripwire is blind to unreadable entries; "
            + signals.journal.problems[0]
        )
    if signals.dumps is None and verdict.status == "pass":
        notes.append("coredump list unreadable (coredumpctl)")
    if notes:
        detail = verdict.detail
        if signals.journal.problems and detail.startswith("0 native faults this boot"):
            detail = detail.replace(
                "0 native faults this boot", "kernel fault count unknown this boot", 1
            )
        return Verdict(
            "warn" if verdict.status == "pass" else verdict.status,
            detail + "; " + "; ".join(notes),
        )
    return verdict


def check(
    cfg: Mapping[str, Any] | None,
    *,
    runner: Runner = _run,
    online_path: Path = SYS_CPU_ONLINE,
    proc_stat: Path = PROC_STAT,
    ack_path: Path | None = None,
    boot_id_path: Path = BOOT_ID_PATH,
) -> Verdict:
    """Read current evidence and apply boot-bound acknowledgments without caching."""
    signals = read_signals(
        cfg, runner=runner, online_path=online_path, proc_stat=proc_stat
    )
    acks = load_acks(ack_path)
    boot_id = read_boot_id(boot_id_path) if acks.present else None
    return evaluate_signals(signals, acks, boot_id)


# ref: ./cpu_tripwire_events.py, ./cpu_tripwire_ack.py, ./cpu_tripwire_cli.py — tripwire boundaries
# src: ./docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md — exact acknowledgment and FAIL preservation
