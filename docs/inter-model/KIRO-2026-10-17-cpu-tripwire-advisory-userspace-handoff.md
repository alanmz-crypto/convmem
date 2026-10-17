# Implementation Handoff: `cpu_tripwire` — FAIL only on unambiguous hardware signals, demote userspace faults to WARN

**Date:** 2026-10-17
**Author:** Kiro (design/review — not implemented; Kiro is review-required)
**For:** Cursor (implementation) → Ryan review / PR
**Arc:** none (ad-hoc) — safety-check policy change
**Resume state:** `NOT_STARTED` — design only; no code written, no branch cut.
**Supersedes:** an earlier GUI-allowlist approach (drafted then discarded 2026-10-17 when the CPU
fix retired its premise; see "Why this replaces the allowlist design"). No allowlist doc remains.

---

## Consequence (what changes for Ryan)

The Poison Pill CPU has been fixed, so the tripwire's original premise — "FAIL on *any*
unexplained native fault, because the chip might be lying" — no longer holds. Right now
`convmem doctor` **exits 1** and stalls agents whenever any userspace process (Typora,
Chromium, or even convmem's own `python3.11`/`libhnsw.so`) faults during this boot, even
though none of that indicates a hardware problem anymore.

After this change, `cpu_tripwire` **only FAILs on unambiguous hardware signals**
(machine-check events, a known-bad CPU coming back online, or a fault the kernel actually
pinned to a specific CPU). Every ambiguous userspace fault — including a `libhnsw.so` GPF
with no CPU — becomes a **visible WARN**, not a gate-failing FAIL. Agents stop stalling,
but a real future CPU death still trips a hard stop, and a possible native-code bug in the
compute path is still surfaced loudly.

## Who / What / When / Why / How

- **Who:** Cursor implements; Kiro authored this design; Ryan reviews/merges.
- **What:** Reclassify the verdict policy in `cpu_tripwire.evaluate(...)`: keep FAIL for
  MCE, known-bad-CPU-online, and CPU-attributed faults; demote all `cpu is None` userspace
  faults and orphan coredumps to WARN.
- **When:** Build on current `main` (includes Poison Pill circuit breaker PR #328,
  `81efa35`). Do **not** branch from `fix/2026-10-16-issue-286-watcher-child-now`.
- **Why:** CPU is fixed (Ryan, 2026-10-17). The broad hard-stop is now pure false-positive
  noise for userspace faults. A `libhnsw.so` GPF with the CPU healthy is now *more* likely a
  real software memory-safety bug than silicon — worth surfacing (WARN), not worth blocking
  every agent (FAIL).
- **How:** Reclassify the three `problems.append(...)` sites in `evaluate()` into
  FAIL-contributors vs WARN-contributors (detail below).

---

## Why this replaces the allowlist design

The prior handoff proposed a GUI/Electron executable allowlist so Typora/Chromium faults
became WARN while the `libhnsw.so` GPF kept FAILing (treated as the Poison Pill signature).
Ryan's 2026-10-17 decision retires that premise: the CPU is fixed, so there is no reason to
hard-block on the compute-path GPF either. An allowlist is now unnecessary complexity — the
right axis is **"did the kernel give us an unambiguous hardware signal?"**, not **"which app
crashed?"**. Delete/ignore the allowlist handoff.

---

## New verdict policy (precise)

`evaluate(faults, coredumps, online, known_bad)` — signature unchanged, no new config, no
allowlist.

**FAIL (hard stop) — unambiguous hardware only. Unchanged behavior for these:**
1. **Known-bad CPU back online** (`known_bad & online`) → FAIL (current behavior).
2. **Any fault the kernel pinned to a CPU that is NOT already known-bad**
   (`f.cpu is not None and f.cpu not in known_bad`) → FAIL. This is a real,
   kernel-attributed per-CPU fault — the genuine "a core is going bad" alarm.
3. **Machine-check events** (`f.kind == "machine_check"`) → FAIL **always**, regardless of
   CPU attribution. MCEs are hardware by definition and near-zero false-positive.

**WARN (visible, non-blocking) — ambiguous userspace. Newly demoted:**
4. **Userspace faults with no CPU attribution** (`f.cpu is None` and
   `f.kind != "machine_check"`) → WARN. This now includes the `libhnsw.so`/`python3.11` GPF
   that previously FAILed, plus Typora/Chromium. The WARN detail must still name the
   processes so a compute-path crash is noticeable, e.g.
   `"N userspace fault(s) this boot, no CPU attribution (advisory): <sample>"`.
5. **Orphan coredumps** (dump with a hardware signal but no matching kernel line) → WARN
   (was FAIL). Still surfaced, no longer blocking.

**PASS:** no faults, no MCE, no known-bad CPU online, no orphan dumps — unchanged.

**Verdict precedence:** if any FAIL-condition is present → `Verdict("fail", ...)` (FAIL
detail wins and should still list the hardware problem(s)). Else if any WARN-condition is
present → `Verdict("warn", ...)`. Else `Verdict("pass", ...)`. A WARN-level userspace fault
must **never** rescue or mask a concurrent FAIL-level hardware signal — FAIL dominates.

Keep the existing blind-tripwire WARNs (`kernel log unreadable`, `coredump list unreadable`,
malformed `known_bad_cpus`) exactly as they are.

---

## Integration point (file)

**File:** `cpu_tripwire.py`, function `evaluate(...)`. Current relevant block:

```python
unexplained = [f for f in faults if f.cpu is None or f.cpu not in known_bad]
if unexplained:
    sample = "; ".join(f.describe() for f in unexplained[:_SAMPLES])
    problems.append(f"{len(unexplained)} native fault(s) not on a known-bad CPU: {sample}")
```

Replace the single `unexplained` bucket with two:
- `hardware_faults = [f for f in faults if f.cpu is not None and f.cpu not in known_bad] + [f for f in faults if f.kind == "machine_check"]`
  (dedupe; an MCE may already have a CPU) → contributes to `problems` (FAIL), same message style.
- `userspace_faults = [f for f in faults if f.cpu is None and f.kind != "machine_check"]`
  → contributes to a **WARN** list, never to `problems`.

Move the orphan-coredump block out of `problems` and into the WARN list.

Then: `if problems: return Verdict("fail", ...)`; `elif warn_notes: return Verdict("warn", ...)`;
else the existing PASS path.

Keep the FAIL detail suffix (`-- see: journalctl -k -b 0 | grep 'likely on CPU'`) on the
FAIL branch only.

`doctor._check_cpu_tripwire` → `cpu_tripwire.check` wiring needs **no change**
(`DoctorCheck("cpu_tripwire", verdict.status != "fail", ...)` already treats WARN as ok).

---

## What NOT to build

- Do **not** demote `machine_check` — MCE is always FAIL.
- Do **not** demote CPU-attributed faults on non-known-bad CPUs — that is the real
  future-CPU-death alarm Ryan chose to keep (Option B).
- Do **not** demote "known-bad CPU back online" — still FAIL.
- Do **not** add an executable allowlist, per-CPU auto-silencing, auto-reboot, or any state
  mutation. This is a pure reclassification of verdict severity.
- Do **not** branch from the issue-286 branch.

## Test expectations (`tests/test_cpu_tripwire.py`)

Existing tests that must **change** (they currently pin the old broad-FAIL policy):
- `test_any_fault_on_a_healthy_or_unknown_cpu_fails` — the `_fault(None)` and
  `_fault(8), known_bad=set()` cases must now be **WARN**, not FAIL (both are `cpu is None`
  or non-attributed userspace). The `_fault(4)` case (CPU-attributed, healthy CPU) stays
  **FAIL**. Split this test accordingly rather than deleting coverage.
- `test_crash_dump_without_a_kernel_line_fails_but_aborts_do_not` — orphan dump is now
  **WARN**, not FAIL. Rename/retarget; keep the assertion that the SIGABRT electron dump is
  still excluded from the hardware set.

Existing tests that must stay green unchanged:
- `test_clean_boot_passes`, `test_faults_only_on_a_known_bad_cpu_warn`,
  `test_known_bad_cpu_back_online_fails`, `test_blind_tripwire_warns`,
  `test_parses_real_fault_lines_and_ignores_the_rest`, `test_cpu_list_ranges`,
  `test_check_reads_this_boot_only`, `test_check_empty_coredump_list_passes`.

New tests to add:
1. `test_cpu_attributed_fault_on_healthy_cpu_still_fails` — `_fault(4)` with `known_bad={8,9}` → FAIL.
2. `test_userspace_gpf_no_cpu_warns` — `Fault("t","general_protection",None,"python3.11",7788)`
   (the old `GP_NO_CPU`/`libhnsw.so` signature) → **WARN**, detail names python3.11.
3. `test_machine_check_always_fails` — `_fault` with `kind="machine_check"`, `cpu=None` → FAIL.
4. `test_hardware_fail_dominates_userspace_warn` — one MCE + one Typora GPF → FAIL.
5. End-to-end `check(...)` with a fake runner feeding the real observed Typora line → WARN,
   not FAIL (so `doctor` stops exiting 1 for that reason).

## Acceptance criteria

- `convmem doctor` reports `cpu_tripwire` as **WARN (not FAIL)** on a boot whose only native
  faults are userspace with no CPU attribution (the current Typora situation) → `doctor` no
  longer exits 1 for that reason.
- A machine-check event, a CPU-attributed fault on a healthy CPU, or a known-bad CPU back
  online still produces **FAIL**.
- A `libhnsw.so`/`python3.11` GPF with no CPU is **WARN** and still **named** in the detail.
- `pylint` + full `pytest` green locally; CI green (pylint, pytest, CodeQL ×2, Analyze ×2,
  secret-scan).

## Branch convention

`fix/2026-10-17-cpu-tripwire-advisory-userspace` cut from current `main`.

## Ryan GATE

This narrows a hardware-safety tripwire per Ryan's explicit 2026-10-17 decision (CPU fixed;
stop blocking on userspace faults). The design keeps MCE / CPU-attributed / known-bad-online
as FAIL so a genuine future CPU failure still hard-stops. Confirm that keeping only those
three as blocking matches intent before merge.

## Merge reading

- [`cpu_tripwire.py`](../../cpu_tripwire.py) — the check being modified
- [`tests/test_cpu_tripwire.py`](../../tests/test_cpu_tripwire.py) — verdict-policy tests to update
- [`CLAUDE-2026-09-23-poison-pill-circuit-breaker-handoff.md`](CLAUDE-2026-09-23-poison-pill-circuit-breaker-handoff.md) — original (now-retired) broad-FAIL rationale

<!-- ref: ../../cpu_tripwire.py — this handoff specifies a verdict-policy change to that check -->
<!-- ref: ../../tests/test_cpu_tripwire.py — tests specified here update this suite -->
<!-- src: CLAUDE-2026-09-23-poison-pill-circuit-breaker-handoff.md — Poison Pill history the policy change retires -->
