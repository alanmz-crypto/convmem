# Insight — What an Unintended Kernel Panic Taught Us About ConvMem Durability

> **Author:** Kiro (review/architecture lane). **Date:** 2026-08-31.
> **Arc:** none (ad-hoc). **Type:** retro / durability analysis — not a plan,
> grants no implementation authority.

## Context

At approximately **05:08 CDT on 2026-08-31** the workstation running ConvMem
suffered an *unclean* kernel panic. This was not a graceful shutdown: the kernel
memory-reclaim thread (`kswapd0`) died with IRQs disabled after a NULL/bad-pointer
fault in `__dquot_alloc_space` (the disk-quota block-accounting path), first
triggered by a normal `fallocate()` on tmpfs from a browser worker. The machine
locked up instantly with no chance to flush state. It was **not** a thermal,
memory-exhaustion, or hardware event — filesystems journal-recovered and
databases crash-recovered cleanly on reboot; no MCE, disk, or media errors.

Because the failure was instantaneous and uncontrolled, it functioned as an
unplanned durability stress test against the exact adversary a crash-safety
design is meant to survive. This document records what that test actually
validated — and, more importantly, where it drew the line between the mature
and the acknowledged-incomplete parts of the system.

All findings below are grounded in the ConvMem source at the paths cited.

## 1. Survival was engineered, not luck — the atomic write path

The knowledge-unit export write is crash-safe **by construction**. The JSONL
upsert in `observe.py::_upsert_jsonl_line` writes through
`atomic_write_text` (`eval_corpus/io_atomic.py`), which follows the canonical
crash-safe pattern:

```
write to temp file → flush → os.fsync(fd) → os.replace(tmp, path)
```

`os.replace` is atomic on the same filesystem, and the whole operation runs
under a file lock (`export_flock_path`). The consequence: a process kill at any
instant leaves **either the complete old file or the complete new file — never a
torn write.** The same temp→fsync→rename pattern appears in
`shadow_ledger.py::atomic_write_json_private` (which additionally fsyncs the
parent directory and sets mode 0600) and in `hash_schema_gate.py`.

**Lesson:** The export layer is structurally incapable of the partial-write
corruption a panic would otherwise cause. The panic *confirmed* a property the
code was already written to guarantee. Reality agreed with the design — the
strongest kind of test result.

## 2. The real crash-damage surface is Chroma, not the JSONL

The JSONL export is atomic. **ChromaDB** (`chroma.sqlite3` plus the HNSW vector
binaries `data_level0.bin`, `link_lists.bin`, etc.) is **not** written through
ConvMem's atomic helpers — it is managed by the Chroma library's own SQLite
layer. SQLite in WAL mode is transaction-safe, but the HNSW index binaries are a
separate concern, and a panic mid-embed-write is the one place ConvMem's own
atomic guarantees do not reach.

This is precisely why `doctor.py` maintains two cross-checking integrity gates:

- **`_check_index_drift`** (`doctor.py:125`) compares Chroma's live unit ids
  against the JSONL export's ids and computes **active coverage** (overlap /
  chroma_count). It FAILs on gross identity mismatch and WARNs below 70%
  coverage.
- **`_check_logical_projection`** (`doctor.py:1289`, via
  `logical_accounting.build_corpus_view_stats`) checks `serving_units` vs
  `physical_units`, duplicate logical rows, and orphaned authority owners.

On the post-panic boot both passed cleanly: **99% active coverage, 0
retained-inactive, 0 duplicates, 0 orphaned owners.**

**Lesson:** ConvMem's durability model is *two stores that check each other* —
the atomic, rebuildable JSONL as ground truth; Chroma as the fast but
less-crash-safe query layer; and `doctor` as the referee that detects divergence
between them. The panic proved the referee reads **real crash data** correctly.
That is more valuable than the survival itself, because it means the system can
**detect** damage even in the layer that is not atomically protected.

## 3. Recovery is a continuous background sweep, not a manual restore

The `source_reconciliation` gate (`doctor.py:1272` →
`logical_accounting.build_reconciliation_diagnostics` →
`source_reconciler.pending_owner_work` / `reconciliation_staleness_seconds`)
tracks sources whose content changed but have not been fully re-projected into
the index, reporting `pending`, `dirty_scopes`, and `staleness_seconds`. The
`convmem-reconcile.timer` re-runs this sweep periodically (it fired at 05:52 on
the post-panic boot).

After a crash, any source that was mid-index becomes "pending," and
reconciliation is the mechanism that re-scans and closes that gap **without human
intervention.** Post-panic doctor showed `pending=2` — a small expected backlog,
not a wound.

**Lesson:** ConvMem treats "we might have missed something during a crash" as a
routine, continuously-swept condition. The recovery path for steady-state ingest
is a standing background process, not a manual procedure.

## 4. The crash hit the mature path, not the acknowledged gap

This is the essential honesty check. `docs/plans/STATUS-recovery-authority.md`
documents an entire arc dedicated to recovery correctness:

- **T1 / T2 / T3 are landed** (PRs #234 / #236 / #238): the complete-data-v3
  provenance substrate + registry validation, the projection-agreement state
  machine, and *scratch-only* recovery orchestration with no live publication.
- **T4 — "recovery-side interruption/crash-closure verification" — is explicitly
  `NOT AUTHORIZED / NOT STARTED`.**

Read precisely: the one capability the codebase itself flags as unbuilt is
exactly *"what happens when a recovery operation is interrupted mid-flight by a
crash."* Today's panic did **not** touch that gap — it struck the steady-state
ingest path, which is mature and atomic. The clean pass is real, but it is partly
because the crash landed on the hardened part of the system.

**Lesson:** Do not over-generalize today's success. It validates *steady-state
ingest durability* (excellent). It says *nothing* about *crash-during-recovery*
durability — the T4 work ConvMem has not authorized. A panic during a
`complete_data_restore` instead of during normal indexing would have landed in
untested T4 territory.

## 5. Synthesis — what the unintended test taught us

1. **Steady-state ingest is crash-safe by construction**, not by luck: atomic
   temp→fsync→rename under a lock. The panic confirmed a designed property.
2. **The durability model is dual-store + referee:** atomic JSONL as ground
   truth, Chroma as the crash-vulnerable fast layer, and `doctor`'s
   `index_drift` / `logical_projection` as the divergence detector. The panic
   proved the referee works on real crash data.
3. **Recovery is continuous, not manual:** reconciliation sweeps treat
   crash-missed work as routine pending backlog and self-close it.
4. **The tested boundary was the mature one.** The codebase's own STATUS files
   flag crash-*during-recovery* (Recovery Authority T4) as unbuilt. The green
   result must not be read as "crash-during-restore is safe."
5. **The result draws a precise line** showing exactly where "finished" stops:
   the non-atomic Chroma/HNSW layer (detected, not prevented) and the unbuilt
   T4 crash-closure path.

## 6. Recommended follow-up (testing)

To convert today's *lucky-placement* pass into a *chosen* test of both the
referee and the acknowledged gap, run deliberate fault injection:

1. **Kill mid-ingest:** interrupt a `convmem index` run (SIGKILL the indexing
   subprocess), then run `convmem doctor` and confirm `index_drift` /
   `logical_projection` detect (or cleanly clear) any divergence, and that the
   reconcile sweep closes the pending backlog.
2. **Kill mid-restore:** interrupt a `complete_data_restore` / recovery
   operation — this exercises the **unbuilt T4 boundary** and should be treated
   as exploratory, expecting to surface gaps rather than pass.
3. **Chroma-layer torn-write probe:** simulate an incomplete HNSW binary write
   and confirm `index_drift` flags the Chroma/JSONL divergence.

Existing scaffolding for this work: `scripts/chroma_restore_drill.py`,
`scripts/restic_integrity_check.py`, `scripts/complete_data_restore_preflight.py`.

Any T4-boundary exercise requires a separate Ryan authorization per
`STATUS-recovery-authority.md`; this document proposes it, it does not perform
it.

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| ConvMem | The local, owned, cross-client knowledge-memory system this repo implements. |
| Kiro / Codex / Cursor / Crush | AI agent lanes; Kiro is the review/architecture (non-implementing) lane (see `docs/AGENT-ROLES.md`). |
| Arc | A named unit of design work with ARCHITECTURE/EXECUTION/STATUS docs; "none (ad-hoc)" means routine work outside any arc. |
| doctor | `convmem doctor` — the session-start health command that runs the integrity/backup gates in `doctor.py`. |
| index_drift | Doctor gate comparing live Chroma unit ids to the JSONL export ids (active coverage) to detect index/ground-truth divergence. |
| logical_projection | Doctor gate checking serving vs physical unit counts, duplicate logical rows, and orphaned authority owners. |
| source_reconciliation | Doctor gate + `convmem-reconcile` timer that re-scans changed sources and reports pending/dirty/staleness backlog. |
| units_export / knowledge_units.jsonl | The flat, atomically-written, rebuildable ground-truth export of every knowledge unit. |
| Chroma / HNSW binaries | The vector store (`chroma.sqlite3`) and its approximate-nearest-neighbor index files; the fast query layer, not written via ConvMem's atomic helpers. |
| atomic write (temp→fsync→rename) | Crash-safe file write: write temp, flush, `os.fsync`, `os.replace` — leaves whole-old or whole-new, never torn. |
| complete-data-v2 / v3 | Restic backup contract versions; v2 is the legacy snapshot, v3 the provenance-aware substrate used by Recovery Authority. |
| Recovery Authority T1–T4 | Arc tiers for provenance-aware recovery; T1–T3 landed (PRs #234/#236/#238), **T4 (crash-during-recovery closure) NOT STARTED** (see `docs/plans/STATUS-recovery-authority.md`). |
| restic gate | Doctor checks (`restic_gate`, `restic_external`, `restic_password_backup`) verifying the local snapshot, offsite copy lineage, and offline password backup. |
| MCE | Machine Check Exception — a hardware-level CPU/memory error report; none occurred during this crash. |
| kswapd0 | The Linux kernel page-reclaim thread that died in the panic, causing the lockup. |
| Track A | Indexing this session's chat transcript into ConvMem (the durable capture of the analysis, separate from this file). |
