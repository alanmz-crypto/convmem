# Stage 1 packet: first measurement of the Codex burn fix

**Arc: Codex (#286).**
**Date:** 2026-10-11
**Author:** Claude (Opus 5.5), design author
**For:** Ryan (grant), plus whichever lane runs it.
**State:** DRAFT. It can run only after the Codex admission PR merges, and
under an explicit Ryan grant. Nothing here is authorized yet.

---

## The burn, measured (read-only, file metadata and processed counts)

- **The burn:** the legacy route re-indexes the whole rollout on every
  change, with paid summarize and distill calls. I found no per-chunk
  summary cache in `ingest.py`, so every re-index pays for every chunk
  again.
  - The 590.7 MiB rollout's processed entry has 26 chunks and 312 units,
    which is the work redone per re-index.
  - One rollout was re-indexed 44 times between Sep 26 and Oct 5.
- **Production burn today is zero only because the watcher has been off
  since Oct 5.** Nothing is being captured either.
- **Active pre-activation rollouts** (all stay on the legacy route, even
  after this fix):
  - 590.7 MiB, started Sep 21, last written Oct 11 13:47. It is also above
    the 256 MiB admission ceiling, so it can never be admitted.
  - 110.2 MiB, started Oct 5, last written Oct 11 16:30.
  - 92.0 MiB, started Oct 9, last written Oct 11 21:09.
  - Overall, 10 rollouts changed in the last day, 24 in 7 days and 100 in
    14 days (660 rollouts, 3.36 GiB).
- **A catch-up wave waits for the watcher.** On start, the watcher's
  reconciliation sweep (`run_startup_reconciliation`) queues re-index work,
  under a budget, for sources that changed while it was off. Every one of
  those is a pre-activation rollout, so each gets a legacy full re-index.

**Consequence:** the admission fix stops the burn only for Codex sessions
started after `admitted_after`. The active long-lived sessions above, and
the catch-up wave, need their own plan (see "Residual burn" below).

## Preconditions

1. The Codex admission PR is merged (Copilot and Kiro PASS on the exact tip).
2. The watcher stays stopped and disabled for all of Stage 1.
3. A fresh complete-data backup, through the existing backup gate.
4. **Do not add the incremental table to the shared live config while the
   runtime is still on `a92a74e`.**
   - `~/.local/bin/convmem` and the MCP server run
     `.worktrees/runtime-main`, which is still at `a92a74e` (#339, before
     the guarded route).
   - Per the arc STATUS brief, that coordinator returns `skipped` when Kiro
     routing is enabled without the hermetic root. Ordinary Kiro indexing
     would silently stop.
   - Pick one option (Ryan):
     - **(A) Recommended.** Run Stage 1 from a scratch worktree at the merge
       SHA, with a Stage 1 copy of the config passed through
       `CONVMEM_CONFIG`. The live config and the runtime stay untouched.
       A reviewer must confirm that a non-default config path is acceptable
       production authority under RC-2.
     - **(B)** First promote `runtime-main` to the merged `main`, then edit
       the live config. This is the same promotion the pending CPU-tripwire
       deploy needs (PR #341).
5. **CPU-tripwire deploy caution.** Its reminder says to "restart
   convmem-watch". `systemctl --user restart` starts a disabled unit too.
   That would bring back the legacy burn and the catch-up wave before the
   fix is active. Deploy the tripwire without starting the watcher.

## Stage 1 config (added to the Stage 1 config copy only)

```toml
[index.incremental_jsonl]
enabled = true
embed_dimension = 768
live_sources = []

[index.incremental_jsonl.codex_rollout_admission]
root = "/home/lauer/.codex/sessions"      # absolute; "~" is rejected (C6b)
admitted_after = "<install time + 10 min, UTC, e.g. 2026-10-1xT15:10:00Z>"
max_transform_chunks_per_run = 20
max_source_bytes = 268435456
```

## Steps

1. Install the Stage 1 config, then wait until after `admitted_after`.
2. Start one fresh Codex session, and use it for a few turns.
3. Run `convmem index --file <that rollout>` three times:
   - after creation;
   - after more turns;
   - with no change.

   Use the Stage 1 runtime and config.
4. Run `convmem index --file` on one pre-activation rollout that has
   changed. It must route legacy. Use a small one, not the 590 MiB file.

## Pass criteria (from design §9)

- Run 2 transforms at most frontier + 1 chunks.
- Run 3 makes zero provider calls.
- The checkpoint, both Chroma collections, `processed.json` and the export
  agree on coverage.
- The pre-activation rollout routes legacy.
- Child peak memory is recorded for each run.

**Burn metric to report:** paid calls for run 2, compared with the legacy
cost of re-indexing the same file in full (its chunk count).

## Budget and stop conditions

- Each run is bounded by the 20-chunk cap. A proposed hard ceiling for all
  of Stage 1 is 40 paid calls (Ryan sets the final number).
- Stop, and change nothing further, on any of these:
  - any refusal other than an expected one;
  - any provider call in run 3;
  - a coverage mismatch;
  - a child above 4 GiB;
  - any change to a source other than the two named ones.

## Residual burn (decide before Stage 2, not needed for Stage 1)

None of these options needs code:

1. **Retire the long-lived sessions.** After `admitted_after`, start fresh
   Codex sessions instead of resuming the three active pre-activation ones.
   The new sessions are admitted.
2. **Exclude what can't be retired.** `convmem exclude <path> --reason …`
   marks a rollout excluded, and `--undo` reverses it. It writes to
   `processed.json`, so Ryan runs it. The trade-off: that session's later
   turns aren't captured.
3. **Bound the catch-up wave.** Before the Stage 2 watcher start, decide
   whether to let the startup sweep re-index the stale pre-activation
   rollouts once, or to exclude the large ones first.

## Next after Stage 1

Stage 2 is a 24 h watcher canary under a separate grant. It also needs the
#308 fix and the 4G watch drop-in reconciliation (design §9).

### #308 diagnosis (Claude, 2026-10-11, read-only; CPU churn, not paid calls)

**The loop, on current `main`:**

1. Any exception during inter-model indexing returns `skipped`
   (`ingest.py:748–751` and `:1423–1429`) and leaves `processed.json`
   unchanged. That includes the provenance-supersession guard
   (`inter_model_index.py:118`).
2. The reconciliation timer, every 2 minutes, reports a doc with no
   processed record as `new_eligible_source` (`source_reconciler.py:169`).
3. The watcher spawns a child, the guard rejects the doc again, and the
   cycle repeats while the content stays the same.

**Exposure now:** the watcher reads `~/Projects/convmem/docs/inter-model`
(172 docs), which follows whatever branch that shared checkout has checked
out. Of those docs:

- 6 have never been recorded;
- about 15 have changed since their last record.

Any that trip the guard will loop once the watcher starts.

**Fix shape (needs a Ryan grant and a Cursor handoff):**

- Make a provenance rejection terminal for that content: record the
  rejected hash, then skip in both the reconciler and the watcher until the
  content changes.
- This mirrors the Codex refusal quarantine, but it releases when the
  content changes instead of being terminal by path.
- No paid calls are involved. The inter-model path does no summarizing or
  distilling.

### 4G watch drop-in (Ryan-gated host config; owned by OpenClaw Watch Coverage)

`~/.config/systemd/user/convmem-watch.service.d/zz-openclaw-watch-limits.conf`
sorts after `oom-mitigation.drop-in.conf`, and still re-imposes
`MemoryMax=4G` and `MemoryHigh=3G` over the 8G mitigation. That pair is
documented as the cause of the service OOM kills on Sep 28 and 29.
Reconcile it before the Stage 2 watcher start.

## Stage 1 run log

**Grant:** Ryan, 2026-10-11, approving the options this packet recommends:

- **Runtime:** option (A).
- **Residual burn:** retire the three long-lived pre-activation sessions.
  New Codex work starts in fresh sessions after `admitted_after`.

**Preparation (Claude, 2026-10-11 22:50–23:00 CDT):**

- **Runtime:** a scratch worktree at `main` `5550def`, in
  `~/.cache/convmem-stage1-5550def` (disk-backed).
- **Config:** `~/.config/convmem/stage1-codex-config.toml`, mode 0600. It is a
  byte-exact copy of the live config, with the Stage 1 tables appended
  (`admitted_after = 2026-10-12T04:04:00Z`, which is 23:04 CDT).
  - It parses under `5550def`.
  - Its data paths are the live production ones.
  - The live config is unchanged, and `runtime-main` still sees the route as
    off.
- **Kiro ruling (headless, file reads only): option (A) is ACCEPTED.**
  - `CONVMEM_CONFIG` only selects which config file loads. Live authority
    comes from the config's own content.
  - Binding condition: the data paths are the live ones, and
    `CONVMEM_INCREMENTAL_ROOT` stays unset. Both hold.
- **Backup gate:** `convmem-restic-local.service` reports a current-day
  snapshot (`89aaf9ef…`, taken at 00:18). Other sessions wrote production
  data at 22:48, so the gate is rerun right before run 1. After 00:15, the
  daily timer takes a new snapshot.

**Hazard (operational rule until Stage 2):** a rollout created after
`admitted_after` must never be indexed through the legacy route. If it is,
it gets a processed entry with no checkpoint, the incremental route then
refuses it as `bootstrap_required`, and it stays legacy for good.

- The normal `convmem` CLI still runs the legacy route (`runtime-main` is at
  `a92a74e`). So does any lane's Track A (`convmem index --file <rollout>`).
- At 22:48, another session legacy-indexed the 18:59 rollout. That was
  allowed, because it predates `admitted_after`, but it is the same burn,
  done by hand.
- Until the runtime is promoted for Stage 2, no lane may index a Codex
  rollout created after 23:04 CDT, except Stage 1 itself through the scratch
  runtime.

**Canary source:** the fresh Codex session started 23:24:18 CDT
(`rollout-2026-10-11T23-24-18-01a12e5a-…`). Its first message told it not to
index itself. The pure admission check returns ADMITTED, and the source had
no processed entry beforehand.

**Run 1 (after creation; 23:3x CDT):**

- Backup gate passed (current day). No other index process was running, and
  the watcher was inactive.
- The run used the scratch runtime under a `systemd-run --user --scope`
  capped at 12G.
- **Result:** `committed`, with 1 chunk transformed out of 1,077,790 source
  bytes.
- **Provider requests:** summarize 1 and distill 1 (**2 paid calls**), plus
  summary_embed 1 and unit_embed 8 (local). It produced 8 units.
- 222.6 s elapsed, and a scope **memory peak of 6.3G**. That peak is far
  above what this source needs, so it is probably the Chroma load. Watch it
  against the 4G watch drop-in before Stage 2.
- **Coverage agrees across all five records:**
  - the checkpoint has 1 summary and 8 units, with its lineage digest set;
  - `processed.json` has 1 chunk and 8 units, and its lineage matches the
    checkpoint;
  - the export has the same 8 unit IDs;
  - Chroma has 1 summary row and 8 unit rows.

**Legacy routing check:** an unchanged pre-activation rollout from Aug 20,
run through the Stage 1 runtime, took the legacy route ("No files changed").
It produced no incremental log line, made 0 paid calls, and left
`processed.json` byte-identical.
