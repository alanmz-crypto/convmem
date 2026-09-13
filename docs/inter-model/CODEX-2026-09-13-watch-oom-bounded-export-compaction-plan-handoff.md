# Plan review handoff — issue #268 bounded export compaction

**Arc:** Trapdoor Hunt (issue #268 operational follow-up)

**Goal:** remove the demonstrated corpus-sized memory spike from export
compaction without changing valid export results or widening production writer
authority.

**My role:** Codex plan author. I designed the corrective but did not implement
or run it.

**The system currently:** merged runtime `8983a6fc…` reads the entire global
export into several Python structures after indexing. Hermetic measurement
peaked at 351.88 MiB for a conservative 128 MiB duplicate-heavy export; the
production export was approximately 2.4 GiB. Watch-triggered children have
repeatedly reached their 12 GiB cgroup ceiling. Exclusions are temporary
containment, and Arc Codex P2 remains paused.

**Next action:** Kiro reviews the plan. No Cursor Execute, PR, live compaction,
watcher operation, re-inclusion, or P2 progression is authorized.

## Exact review target

- Plan: `docs/plans/EXECUTION-watch-oom-bounded-export-compaction.md`
- Branch: `plan/2026-09-13-watch-oom-bounded-export-compaction`
- Base: `8983a6fc909344239e6e3051d85c50c5508c1a16`
- Prior issue #268 design: `git show
  92395e9:docs/plans/DESIGN-watch-incremental-index.md`
- Recurrence handoff: `git show
  3eea055:docs/inter-model/KIRO-2026-09-12-arc-codex-watch-oom-recurrence-handoff.md`

## What changed from the prior issue #268 design

The prior design correctly identified repeated full-file work, but its leading
memory claim is now superseded: `accepted_rows` is per chunk. New measurements
identify `_deduplicate_units_export_impl()` as a direct corpus-sized
accumulator. This plan therefore isolates the smallest demonstrated correction
instead of implementing the prior append-cursor, batching, timeout, and cooldown
package together.

## Kiro decision requested

Return PASS, CONDITIONAL PASS, or FAIL on:

1. the disk-backed `id → first sequence + last byte range` algorithm;
2. valid-row legacy parity and malformed-row fail-closed hardening;
3. the 16 MiB per-record bound;
4. callback-based streaming atomic publication and crash states;
5. memory verification thresholds;
6. writer-inventory and Arc Codex baseline refresh obligations;
7. whether C0–C7 are narrow and complete enough for a later Cursor Execute
   grant.

If not PASS, name the smallest required plan correction. Do not implement.

## Negative confirmation

This planning branch performs no runtime edits, live compaction, corpus access,
source re-inclusion, provider/network call, watcher/systemd action, memory-cap
change, Gate 0, P2, grant, PR, merge, or activation.

I finished: [Arc Trapdoor Hunt / issue #268] bounded export-compaction plan
Next step: Kiro reviews the plan and returns a written verdict
Next lane: Kiro — plan review only
See my work: `docs/plans/EXECUTION-watch-oom-bounded-export-compaction.md`

**TL;DR:** Review the narrow disk-backed, streaming, crash-safe compaction plan;
no implementation or production action is authorized.
