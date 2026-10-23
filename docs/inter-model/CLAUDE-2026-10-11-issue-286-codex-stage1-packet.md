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

**Run 2 (after more turns; 00:07 CDT 2026-10-12):** the source grew from
1,077,790 to 2,385,272 bytes.

- **Result:** `committed`, with 1 chunk transformed: the still-open chunk 0,
  redone with the new turns.
- **Provider requests:** summarize 1 and distill 1 (**2 paid calls**), plus
  embeds 1+7 (local). It produced 7 units.
- 215.7 s elapsed, with a scope memory peak of 6.7G.
- **Coverage agrees, with no duplicates.** The checkpoint, `processed.json`,
  the export and Chroma all show 1 summary and 7 units, and the lineage
  matches. The 8 units from run 1 were replaced.

**Run 3 (no change):** `[skip] unchanged`, with **0 provider calls**, 18.5 s
elapsed, a 112M memory peak, and coverage unchanged.

### Stage 1 result: PASS

| Criterion (design §9) | Result |
|---|---|
| Run 2 transforms at most frontier + 1 chunks | 1 chunk (frontier 0) |
| Run 3 makes zero provider calls | 0 |
| Checkpoint, both Chroma collections, `processed.json` and export agree | Yes, after runs 1, 2 and 3 |
| A pre-activation rollout still routes legacy | Yes, with 0 calls and processed unchanged |
| Child peak memory recorded | 6.3G, 6.7G and 0.1G |

**Total paid calls: 4**, against the 40-call ceiling.

**What this does and doesn't show about the burn:**

- This session is still a single open chunk, so a legacy re-index would also
  have cost 2 paid calls. Stage 1 shows that the route is correct and bounded;
  it doesn't show savings yet.
- Savings grow with the number of chunks. A legacy re-index redoes every
  chunk, while the incremental route redoes only the open frontier chunk and
  any new ones. The 590.7 MiB pre-activation rollout has 26 chunks.
- Each indexing run still costs about 4 CPU-minutes and over 6 GiB of memory,
  whichever route it takes. Admission doesn't change that, and in Stage 2 it
  scales with how often the watcher indexes.

**Stage 2 notes:**

- Promote the runtime and install the live config with the **same**
  `admitted_after = 2026-10-12T04:04:00Z`, so the Stage 1 session stays
  admitted.
- Until then, the hazard rule above still applies.

**Correction to the #308 diagnosis (Codex, read-only review of `main`):**

- On `main`, the watcher never reads the reconciler's queued work.
  `run_startup_reconciliation` runs only at startup, and child launches come
  from filesystem events.
- So my "reconciliation timer every 2 minutes, then respawn" link is
  unproven, and it may be deployment behavior.
- The defect itself is confirmed: a deterministic provenance rejection
  returns `skipped` and is never recorded, so every later event retries it.
- Codex recommends a separate rejection record, keyed by canonical path and
  full-file SHA-256. The reconciler and `watch_skip_reason` would both consult
  it, and it would be released when the content changes. Only the
  provenance guard writes it; other exceptions stay retryable.

## Stage 2 prerequisites (Ryan grant 2026-10-12; done by Claude 00:15–00:40 CDT)

Ryan granted all four: the #308 handoff, the drop-in, runtime promotion with
the live config, and the residual-burn plan.

1. **Backup:** the daily timer took the current-day complete-data snapshot
   `b9a8977a…` at 00:17, before any change below.
2. **4G drop-in reconciled.**
   - Removed `zz-openclaw-watch-limits.conf`. Its backup is
     `~/.config/convmem/backups/zz-openclaw-watch-limits.conf.removed-2026-10-12`.
   - After `daemon-reload` the effective limits are `MemoryMax=8G`, no
     `MemoryHigh`, `MemorySwapMax=0`, from `oom-mitigation.drop-in.conf`.
   - The watcher is still inactive and disabled.
3. **Runtime promoted.** `.worktrees/runtime-main` was fast-forwarded from
   `a92a74e` to `05aa2c8` (44 commits, including #341, #365, #388 and #387).
   - Before promoting, a doctor preview on `05aa2c8` with the live config
     showed no new FAIL. It added two PASSes (`cpu_tripwire`,
     `incremental_refusals`) and one WARN (`chroma_audit`: the audit timer
     isn't installed).
   - After promoting, doctor exits 0.
4. **Live config.** The backup is
   `~/.config/convmem/backups/config.toml.pre-codex-admission-2026-10-12`
   (mode 600). The appended `[index.incremental_jsonl]` and
   `codex_rollout_admission` tables use the **same**
   `admitted_after = 2026-10-12T04:04:00Z`.
   - Route decisions under the new runtime: the Stage 1 session is
     **incremental**. The 590.7 MiB Sep 21 rollout, today's 18:59
     pre-activation rollout and the latest Kiro session are all **legacy**.
     Sources that aren't granted return `None` and take the legacy route
     (`incremental_jsonl.py` `maybe_route_incremental`).
   - **The legacy-index hazard is lifted.** The normal CLI, including any
     lane's Track A, now routes admitted Codex sessions incrementally.
5. **#308:** the Cursor handoff is on
   `docs/2026-10-12-issue-308-inter-model-rejection-handoff`.

**Corrections:**

- **Legacy check.** `ingest.py` checks for "unchanged" (line 1362) *before*
  routing (line 1368). So the zero-cost legacy check proved only that
  nothing was written. Legacy routing for pre-activation rollouts is proved
  by the pure admission check (NOT admitted) together with the
  `return None` path above.
- **There is no catch-up wave.** Only accounting and proof modules read the
  reconciler's queued owner work. The reconcile timer just writes a report,
  and the watcher indexes only on filesystem events. A stale pre-activation
  rollout that stops growing is never re-indexed. So retiring the three
  long-lived sessions takes their residual burn to about zero.
- **What stays on the legacy route in Stage 2:** Kiro transcripts (35
  spawns, Sep 26–Oct 5) and Cursor JSONL (29), against Codex's 133. Kiro's
  fix is the exact-path route (the bootstrap track, plus the recovery-parity
  follow-up). Cursor JSONL isn't eligible for the incremental route.

**Remaining before the Stage 2 grant:** #308 merged (Cursor, then reviews,
then Ryan). The tripwire deploy's chroma-audit timer is optional for Stage 2
and is still a WARN.

## Stage 2 packet: 24 h watcher canary (DRAFT, needs a Ryan grant)

**Purpose:** bring automatic capture back, and measure the burn with the
admission fix and the #308 fix both live. Activation, meaning leaving the
watcher on after the canary, is a separate grant.

**State at drafting (Claude, 2026-10-12, read-only):**

- #308 is merged on `main` as `8a7cdab` (PR #390).
- `runtime-main` is at `05aa2c8` with a clean tree, so it doesn't yet have
  #308.
- `convmem-watch.service` is inactive and disabled, with `MemoryMax=8G` and
  `MemoryHigh=infinity`.
- The live config admits Codex rollouts started after
  `2026-10-12T04:04:00Z`.
- The current-day complete-data snapshot is `b9a8977a…` (00:17).

**Steps (one grant; Claude runs them):**

1. **Backup gate:** `backup_workflows.py ensure` through
   `convmem-restic-local.service`. Today's snapshot should make this a
   no-op.
2. **Doctor preview:** run doctor on `8a7cdab` with the live config, from a
   scratch worktree (read-only). Expect no new FAIL compared with
   `05aa2c8`.
3. **Promote:** fast-forward `runtime-main` from `05aa2c8` to `8a7cdab`, then
   run `convmem doctor` and expect exit 0.
4. **Start:** `systemctl --user enable --now convmem-watch.service` (T0).
   Watch the journal live for the first 15 minutes.

**Measure (read-only):** the service journal since T0, `systemctl show`,
cgroup `memory.events`, the rejection sidecar and `processed.json`
metadata.

- **Paid calls, admitted Codex runs:** the sum of `summarize + distill` from
  the `incremental_codex_admitted_run` stderr lines.
- **Paid calls, legacy runs:** about 2 × the re-indexed source's chunk count.
  This is an estimate, because legacy runs don't log provider calls, and the
  report labels it that way.
- **Spawns per source family,** against the Sep 26–Oct 5 daily baseline:
  Codex 13.3 per day, Kiro 3.5, Cursor JSONL 2.9 and inter-model docs 331.5.
- **#308:** the `[watch] skip (inter_model_rejected)` count, the sidecar
  records, and no repeat spawn for a (path, hash) pair already recorded.
- **Health:** the service `MemoryPeak`, OOM kills, native crashes and
  circuit-breaker trips, refusal markers (`live_route_refused:`), and doctor
  at the end.

**Stop conditions.** On any of these, Claude runs
`systemctl --user disable --now convmem-watch.service` at once, reports, and
changes nothing else:

- a Codex rollout started after `admitted_after` is indexed on the legacy
  route;
- an admitted run makes provider calls beyond its frontier + new chunks, or
  hits the 20-chunk cap;
- a repeat inter-model spawn happens for a (path, hash) pair that is already
  in the sidecar;
- an OOM kill (a cgroup `oom_kill` increment), a native crash or a
  circuit-breaker trip. For reference, each index child peaked at
  6.3–6.7 GiB in Stage 1, against the service's 8G;
- any refusal other than an expected one. A pre-activation rollout is
  simply not admitted and takes the legacy route, which is not a refusal;
- paid calls over the 24 h ceiling. Claude proposes 200, and Ryan sets the
  number.

**Expected residual burn:**

- Kiro transcripts and Cursor JSONL stay on the legacy route, at about 6.4
  runs a day at the baseline rate.
- The three long-lived pre-activation Codex sessions add burn only if they
  are resumed. Start fresh sessions instead.

**Checkpoints:** T0 + 15 min (live), T0 + 2 h and T0 + 24 h. Each reports
burn first.

**Rollback:** `systemctl --user disable --now convmem-watch.service`.
- The runtime promotion can stay: #308 only adds a skip path and a sidecar.
- The config backup is
  `~/.config/convmem/backups/config.toml.pre-codex-admission-2026-10-12`.

**PASS:** no stop condition fires in 24 h. Claude then writes the burn
report, and Ryan decides activation.
