# Design: recovery parity for Kiro exact-path live sources (#286 follow-up)

**Arc: Codex (#286).**
**Date:** 2026-10-11
**Author:** Claude (Opus 5.5), design author
**Status:** DRAFT for Kiro review. No implementation is authorized.

---

## Why this exists

The Codex rollout admission branch
(`feat/2026-10-10-issue-286-codex-rollout-admission`, tip `78b9295`) closed two
recovery gaps for Codex-admitted sources:

- **C1b:** recovery with no checkpoint now applies the fresh-run bootstrap rule.
- **D8:** a legacy re-index after a checkpoint is now detected through lineage.

Both guards return early for any source that isn't Codex-admitted, so Kiro
exact-path live sources still have both gaps. Cursor reported this during
corrective 5, and Claude confirmed it in the code. Ryan agreed to handle it as
a separate follow-up rather than inside the Codex admission PR.

## Current state (checked read-only on 2026-10-11)

- **The route is off.** The live config has no `[index.incremental_jsonl]`
  table, and `convmem-watch.service` is inactive and disabled.
- **One production transaction is pending:** the failed Kiro bootstrap of
  2026-10-10.
  - Its phase is `transform_failed`, with `bootstrap_existing: true`. It is
    bound to that bootstrap's grant, and has no checkpoint, no rollback file
    and no prepared keys.
  - Only a matching one-shot bootstrap can recover it.
    `incremental_jsonl.py:2336–2344` refuses any other run with
    `bootstrap_requires_one_shot` or `bootstrap_replay_grant_mismatch`.
- **No production checkpoint exists** for any source.

So neither gap below can be triggered today.

## The gaps (code at `78b9295`)

**G1. Recovery without a checkpoint.**

`_codex_roll_forward_refusal` (`incremental_jsonl.py:1152`) returns `None` at
`:1160` for a source that isn't Codex-admitted. So the C1b rule,
`_codex_recovery_bootstrap_required` (`:1098`), never runs for Kiro sources.

Scenario: a new Kiro exact-path source runs incrementally for the first time
and crashes. The operator takes it off `live_sources`, and legacy indexing
indexes it. The operator then restores it. Recovery transforms and commits on
top of the legacy projection, so the source ends up indexed twice.

**G2. Legacy indexing after a checkpoint.**

Lineage is recorded only for Codex-admitted commits:

- the `lineage` value at `:1919–1923`;
- `processed_lineage_digest` at `:2067–2069`.

The D8 check, `_codex_projection_checkpoint_mismatch` (`:1068`), is
Codex-only. `_continuity_reason` (`:442`) compares only the source's identity
and content, never the projection.

Scenario: a Kiro source with a checkpoint is taken off `live_sources`, and
after an append, legacy indexing re-indexes it. When it is restored, the next
run continues from the old checkpoint, on top of a projection that legacy
indexing has rewritten. This affects fresh runs as well as recovery.

## Proposed rules

- **R1 (closes G1).** Apply the C1b rule to every `ProductionBoundary` source,
  not only Codex-admitted ones. When a recovery run that isn't a bootstrap
  finds no checkpoint, it refuses `bootstrap_required` if the source has a
  processed entry, or has Chroma rows that this transaction didn't write.
  Bootstrap transactions stay under the existing one-shot binding.
- **R2 (closes G2).** Record lineage on every `ProductionBoundary` commit: the
  checkpoint's `processed_lineage_digest` and the processed entry's
  `incremental_jsonl_lineage`. Apply the D8 check to every `ProductionBoundary`
  source, in fresh runs and in recovery, refusing
  `rebuild_required:projection_checkpoint_mismatch`. As with D8, taking a Kiro
  source off the route becomes one-way. Putting it back requires a new
  one-shot bootstrap grant.
- **R3.** No new outcome codes, config keys or admission rules. Runs inside
  the isolation boundary (hermetic tests) are unchanged.

## Ordering constraint (decision for Ryan and the Kiro bootstrap track)

The successor Kiro bootstrap (Sol's track) will write the first production
checkpoint. If R2 lands after that bootstrap, the checkpoint has no lineage,
and the D8 check must do one of three things with it:

- **(a) Skip lineage-less checkpoints.** This leaves G2 open for that source.
- **(b) Refuse them.** This forces a second paid bootstrap.
- **(c) Backfill.** On the first run after the fix, accept the checkpoint
  only if both hold:
  - the source's Chroma rows equal the checkpoint's `summary_ids` and
    `unit_ids`;
  - the processed entry's hash equals the checkpoint's `processed_hash`.

  If they hold, record lineage; otherwise refuse.

**Recommendation:** land R1 and R2 before the successor bootstrap. Its
checkpoint then carries lineage from the start, and no compatibility rule is
needed. If the bootstrap must go first, (c) is the only option that keeps the
gap closed without a second paid run. Kiro would need to confirm that
equality is a sound substitute for lineage.

## Questions for Kiro

1. Is a one-way route rollback (R2) the right policy for Kiro exact-path
   sources? The alternative is that a fresh bootstrap grant re-admits a source
   after a legacy run, which R2 already provides through `rebuild_required`.
2. Does this gap block the Codex admission PR? Claude recommends not: it
   can't be reached until a Kiro source is live.
3. Which ordering applies: before the successor bootstrap (recommended), or
   after it with backfill (c)?

## Tests (hermetic only)

- **G1:** for a new Kiro exact-path source, a crash, then a legacy index,
  then a restore refuses `bootstrap_required`. It makes zero provider calls
  and changes nothing in Chroma or the processed log. A `PREPARING` or
  `APPLYING` recovery with no legacy run in between still commits.
- **G2:** a checkpoint, then a legacy re-index, then a restore refuses
  `rebuild_required:projection_checkpoint_mismatch`, in both a fresh run and
  recovery, with zero provider calls.
- **Bootstrap:** a successor bootstrap commit records lineage. The existing
  bootstrap recovery refusals (`bootstrap_requires_one_shot`,
  `bootstrap_replay_grant_mismatch`) and the failed-operation supersession
  tests are unchanged.
- **Codex:** the corrective-4 and corrective-5 tests pass unchanged.

## What not to build

- No live config, bootstrap, watcher start, index run or provider call.
- No change to the bootstrap grant and binding, failed-operation supersession,
  the Codex admission rules, or the isolation boundary.

## Sequencing

1. Kiro reviews this design and answers questions 1–3.
2. Once the Codex admission PR merges (both changes touch the same
   functions), Cursor implements this on a fix branch from `main`, under a
   Ryan grant.
3. Copilot and Kiro review the exact tip, and Ryan merges. This lands before
   any Kiro exact-path live incremental run. If question 3 is answered as
   recommended, it also lands before the successor bootstrap.
