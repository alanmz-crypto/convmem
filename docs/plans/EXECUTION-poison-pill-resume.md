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
| **0** | Fresh restic snapshot + structural baseline of the live index | now |
| **1** | Readers and queries only (already the case: MCP servers, `ask`, `search`) | stage 0 complete |
| **2** | `systemctl --user enable --now convmem-refine convmem-reconcile.timer convmem-monitor.timer convmem-cg2-soak-check.timer` | ≥6 loaded hours clean (§3) |
| **3** | Watcher back: `systemctl --user enable --now convmem-watch` | circuit breaker merged (§7.1) **or** interim exclusion in place (§2.1), **and** ≥24 h clean |

### 2.1 Interim control if the watcher must return before the circuit breaker

Exclude the known 67-retry input rather than leaving the loop unguarded:
`convmem exclude` (see `exclude_cli.py`) on
`~/.codex/sessions/2026/09/17/rollout-2026-09-17T23-18-39-01a0b2bc-e7cc-7a53-94b6-676fdfc966f0.jsonl`.
This is a stopgap for one known file, not a substitute for §7.1 — any *other* file that starts
crashing will loop exactly the same way.

### 2.2 Stage 0 detail

- Take a snapshot **now, while the store is quiescent**. The newest complete-data-v2 snapshot
  (`e51f849a…`) was taken 00:19 today, which is *before* the 04:57 rebuild — so today's only
  rollback point is a pre-rebuild state.
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

- **Rollback point** before each stage (§2.2).
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
5. **Export/projection drift.** 3,548 export rows against 436 live units for a single source;
   ~3,100 of `doctor index_drift`'s ~69,040 historical-only ids come from that one file. Export
   compaction dedupes by id and these ids are all distinct, so it cannot reclaim them.

---

## 8. Decision record

- **2026-09-20** — Ryan adopted the BIOS-misconfiguration assumption and authorised proceeding
  under it, with proof to follow. Revocation conditions are §5. Review at 24 clean loaded hours.
