# EXECUTION — Arc Poison Pill: resume under a provisional fix

**Date:** 2026-09-20 · **Arc:** Poison Pill (`chroma-upsert-crash`)
**Author:** Claude Opus 5 (Kiro design/plan lane) · **Adopted by:** Ryan, 2026-09-20
**Companion:** `docs/plans/STATUS-chroma-upsert-crash.md` (arc brief)

---

## 1. The working assumption, stated plainly

**The 2026-09-18→20 instability was a BIOS misconfiguration — PL2 unenforced at 4095 W against a
correct 253 W PL1 on an i7-13700K — and it has been corrected.** We proceed as if this is true.

It is **not proven**. The BIOS correction and the clean upsert matrix fall in the same window, so
"chromadb is innocent" and "the platform now behaves" cannot be separated by anything we have run.
This plan exists so that acting on an unproven assumption is a managed risk rather than an
accident: the proof runs underneath (§3), and named tripwires revoke it (§5).

### What the assumption licenses
Resuming corpus writes in stages; resuming the other arcs; normal agent work on this machine.

### What it does not license
Closing this arc; deleting the quarantined indices; dropping the watcher's retry defect from the
backlog; claiming anything about Trapdoor Hunt / #268; or describing the cause as *established*
in any handoff, ledger record or PR.

---

## 2. Resume staging

Each stage is reversible and gated. Do not skip ahead to buy time — the gates are the only thing
converting the assumption into evidence.

| Stage | Action | Gate to enter |
|---|---|---|
| **0** | Record the rollback point (see §2.2 — a *fresh* one is not currently possible) + structural baseline | now |
| **1** | Readers and queries only (already the case: MCP servers, `ask`, `search`) | stage 0 complete |
| **2** | `systemctl --user enable --now convmem-refine convmem-reconcile.timer convmem-monitor.timer convmem-cg2-soak-check.timer` | ≥6 loaded hours clean (§3) |
| **3** | Watcher back: `systemctl --user enable --now convmem-watch` | circuit breaker merged (§7.1) **or** interim exclusion in place (§2.1), **and** ≥24 h clean |

### 2.1 Interim control if the watcher must return before the circuit breaker

Exclude the known 67-retry input rather than leaving the loop unguarded:
`convmem exclude` (see `exclude_cli.py`) on
`~/.codex/sessions/2026/09/17/rollout-2026-09-17T23-18-39-01a0b2bc-e7cc-7a53-94b6-676fdfc966f0.jsonl`.
This is a stopgap for one known file, not a substitute for §7.1 — any *other* file that starts
crashing will loop exactly the same way.

### 2.2 Stage 0 detail — and a blocker found while executing it

**Attempted 2026-09-20 11:21: a fresh snapshot could not be taken.** Starting
`convmem-restic-local.service` succeeded (`Result=success`) but deliberately took no snapshot —
it reported *"current — snapshot covers today (id=e51f849a…)"* and exited. `ensure_current_snapshot`
(`backup_workflows.py:128`) is a **guarantee** function: it ensures a current-day snapshot exists.
It is not an on-demand snapshot, and neither `scripts/restic-ensure-chroma-snapshot.sh` nor the
`backup_workflows` CLI exposes a force path.

**Do not work around this with a raw `restic backup`.** The complete-data-v2 workflow carries
lineage and provenance semantics (see the Recovery Authority arc); a snapshot taken outside it may
not satisfy the verification tooling.

**So the rollback point for this resumption is `e51f849a…`, taken 00:19 today**, with an honest gap:
it predates the 04:57 HNSW rebuild and the ~234 units indexed at 10:38–10:41. Restoring it would
cost roughly eleven hours of corpus change. The offsite copy (`f27bd91e…`) matches it.

- Proceed on that rollback point, knowing its age.
- Record the structural baseline of the live index with the validator described in §4.2, so later
  corruption is detectable by comparison rather than by a crash.

---

## 3. The proof, pre-registered before we start

Pre-registered so the thresholds cannot drift once results come in.

**Metric:** process core dumps and kernel faults, split convmem / non-convmem, per hour of *loaded*
use (idle hours do not count — the pre-fix faults occurred under load).

**Pre-fix baseline:** 46 CPU-attributed kernel faults over the 81-hour retained window =
**0.57 faults/hour** machine-wide; ~0.21/hour on the worst core (CPU 4).

| Reading | Threshold | Interpretation |
|---|---|---|
| Clean | **≥6 loaded hours** | Probability of a wholly clean stretch at the pre-fix rate is <5%. Provisional fix is **credible** — enter stage 2 |
| Clean | **≥24 loaded hours** | Provisional fix **accepted**; downgrade the arc to hardening only |
| Any non-convmem fault | any | **Revoke** — go to §5 |

**How to read the counter** (no daemon required; the journal already holds the history):

```bash
coredumpctl list --since "$(uptime -s)" --no-pager
journalctl -k -b 0 --no-pager | grep -cE 'segfault|general protection'
```

---

## 4. Instrumentation

### 4.1 `doctor` check — `platform_faults` (Cursor)
Count core dumps since boot, split convmem vs non-convmem, and report hours-clean. WARN on any
non-convmem fault; this is what makes the tripwire automatic instead of remembered.

### 4.2 `doctor` check — HNSW structural integrity (Cursor)
Port the validator used in this arc's forensics: per segment, assert size invariants
(`data_level0.bin` = elements × bytes-per-element), level-0 link counts ≤ maxM0 **after masking
hnswlib's delete-mark bit 0x10000**, neighbour ids in range, a clean `link_lists.bin` walk to exact
EOF, unique labels, and `len(id_to_label)` == elements − delete-marked. Reference implementation:
`~/.cache/arc-poison-pill/` plus this session's transcript. This detects corruption **structurally,
before a crash** — the check that would have settled hypothesis (c) on day one.

---

## 5. Tripwires — any one revokes the assumption

1. Any **non-convmem** process core dump.
2. Any convmem child dying from a **signal** (not a non-zero exit).
3. Any **structural failure** from §4.2.

**On any tripwire:** stop and disable the writers again (`convmem-watch`, `-refine`,
`-reconcile.timer`, `-monitor.timer`, `-cg2-soak-check.timer`), record the timestamp and the
faulting CPU, and resume hardware investigation at the arc brief § 6.2 — two-DIMM test, then RMA
under Intel's extended 5-year warranty for affected 13th/14th-gen parts. Do not re-litigate the
software hypothesis; the matrix closed it.

---

## 6. Safety nets while the assumption is unproven

- **Rollback point** before each stage — currently `e51f849a…` (00:19), ~11 hours stale (§2.2).
- **Keep both quarantined indices** (`chroma.corrupt-2026-09-19`, `…-2026-09-20`, 9.2 GB) until the
  arc closes. They are the only surviving pre-fix artefacts.
- **Keep** `~/.cache/arc-poison-pill/{probe.py,matrix.sh,matrix.log}`. The 4.5 GB index copies were
  deleted and are reproducible with one `cp -a` from a quarantine directory.
- Re-run §4.2 at each stage transition.

---

## 7. Hardening backlog — do these regardless of the cause

1. **Global crash circuit breaker + per-file quarantine (Cursor, highest value).** If N index
   children die from signals within M minutes *regardless of file*, stop spawning, log, and raise
   an observation. Per-file logic alone would have quarantined `docs/inter-model/LATEST.md`, which
   the corpus needs. This is the control that would have stopped 67 DeepSeek passes on one file.
2. **Crash accounting (Cursor).** A native crash must not be attributed as a provider drop, so
   `doctor synthesis_gate` stops absorbing them silently.
3. **Ad-hoc writer governance (design question, unowned).** Stopping the systemd units does not
   stop an agent running `convmem index --file`: one did exactly that at 10:38–10:41 today, inside
   a declared quiet window, adding ~234 units. Either the freeze becomes enforceable (a flag the
   CLI honours) or we stop claiming the store is frozen. Today the honest statement is the latter.
4. **Reader discipline (design question, unowned).** Nine `mcp_server.py` processes hold the live
   store outside the writer lease, and one wrote to it with every unit disabled.
5. **No on-demand pre-change snapshot (Cursor/Codex — new, found 2026-09-20).** The backup system
   guarantees one snapshot per day and offers no way to checkpoint before a risky operation. For a
   safety story that rests on "the restic gate covers today", that is a real gap: today it meant a
   staged resumption had to proceed on an eleven-hour-old rollback point. Needs a
   `take_snapshot(reason=…)` sibling or a `--force` path that **preserves** complete-data-v2 lineage
   semantics — design care, not a quick flag, since it intersects the Recovery Authority arc.
6. **Export/projection drift.** 3,548 export rows against 436 live units for a single source;
   ~3,100 of `doctor index_drift`'s ~69,040 historical-only ids come from that one file. Export
   compaction dedupes by id and these ids are all distinct, so it cannot reclaim them.

---

## 8. Decision record

- **2026-09-20** — Ryan adopted the BIOS-misconfiguration assumption and authorised proceeding
  under it, with proof to follow. Revocation conditions are §5. Review at 24 clean loaded hours.

---

## 9. Monitoring runbook (written for a light-weight model)

**Your job is to report, not to interpret.** Run the block, match the output against the table, and
do exactly what the matching row says. Do not diagnose, do not form theories about causes, and do
not run anything not listed here. If output does not match any row, say so and stop.

**Cadence:** every 30–60 minutes while the machine is in use. Skip checks while it is idle — idle
hours do not count toward the clock.

### The check

```bash
echo "boot: $(uptime -s)   now: $(date '+%F %T')   $(uptime -p)"
journalctl -k -b 0 --no-pager | grep -E 'segfault|general protection' | tail -5
echo "kernel_faults=$(journalctl -k -b 0 --no-pager | grep -cE 'segfault|general protection')"
coredumpctl list --since "$(uptime -s)" --no-pager 2>&1 | tail -5
```

### Decision table

| Output | Action |
|---|---|
| `kernel_faults=0` and `No coredumps found.` | Report: "clean, N hours since boot". Nothing else. |
| Any core dump whose executable is **not** under `…/envs/convmem/…` | **TRIPWIRE.** Run the stop block below, then escalate. |
| Any core dump that **is** convmem, with signal SIGSEGV/SIGABRT | **TRIPWIRE.** Run the stop block below, then escalate. |
| Any `segfault` / `general protection` line | **TRIPWIRE.** Run the stop block below, then escalate. |
| Command errors, or output you cannot match | Report the raw output verbatim and stop. |

### Stop block (run on any tripwire, before escalating)

```bash
systemctl --user stop    convmem-watch.service convmem-refine.service
systemctl --user disable convmem-watch.service convmem-refine.service
systemctl --user stop    convmem-reconcile.timer convmem-monitor.timer convmem-cg2-soak-check.timer
systemctl --user disable convmem-reconcile.timer convmem-monitor.timer convmem-cg2-soak-check.timer
date -Is
```

### Escalation message (send this to Ryan verbatim, filling the blanks)

> Arc Poison Pill tripwire at `<timestamp>`. Faulting process `<name>`, signal `<sig>`, CPU `<n>`.
> Writers stopped and disabled. The BIOS-misconfiguration assumption is **revoked** per
> `EXECUTION-poison-pill-resume.md` §5. Next step is §6.2 of the arc brief: two-DIMM test, then RMA.
> Do not re-open the software hypothesis — the upsert matrix closed it.

### Clock

Report hours since boot and the fault count. **Ryan judges whether those hours were loaded** —
do not estimate that yourself. Thresholds are in §3: ≥6 loaded hours clean is credible, ≥24 accepted.

---

## 10. Ledger corrections (Ryan runs these; stage 2 or later)

Three observations assert a cause the evidence contradicts. `convmem verify` writes to Chroma, so
these are **stage-2 actions** — not to be run while the store is held at stage 1.

```bash
convmem verify obs_a09dbfa9e237 --model claude-opus-5 --result fail \
  --notes "Two-problem separation not supported: the crash is not file-specific (index --file LATEST.md and the refine daemon both SIGSEGV), and 'XMP-off fixed it' does not hold — unrelated programs kept faulting across four boots. Superseded by Arc Poison Pill; see docs/plans/STATUS-chroma-upsert-crash.md."

convmem verify obs_e8db779df8c3 --model claude-opus-5 --result fail \
  --notes "Chroma 1.5.9 heap corruption not supported: 300,000 update-in-place upserts into the same pre-rebuild index across default threads, num_threads=1, and nine concurrent readers returned 15/15 clean. Cause reattributed to platform (PL2 unenforced at 4095 W on a 13700K), now mitigated but unproven."

convmem verify obs_c1499a660d4f --model claude-opus-5 --result fail \
  --notes "Live Chroma index corruption not supported: both quarantined indices and the live index as it stood two minutes before the 07:20 crash pass every structural check — size invariants, neighbour ranges, link-list walk to exact EOF, unique labels, pickle/delete-mark consistency, SQLite quick_check."
```
