# Implementation Handoff: unwedge concurrent writers, stop agent self-indexing, ignore plain opens

**Arc: Codex (#286), after Stage 2.** These are the fixes the watcher needs
before it can stay on.
**Date:** 2026-10-12
**Author:** Claude (Opus 5.5), from the Stage 2 canary
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-10-12 ("authorized"), for fixes P1–P3 of the
Stage 2 report and the Track A rule change. P4–P7 are not authorized here.

## Resume state

| Field | Value |
|-------|--------|
| **State** | `IN_PROGRESS`: Claude's round 9 FAILs corrective 7 (`905e602`). The index-route burn is fixed through the real entrypoint, but refine, monitor and repository-knowledge retirement now take C1 inside an open store session and fail on every write; refine pays one DeepSeek call first. Corrective 8 (T0–T5, T0 first) is in `CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md`, round 9 |
| **Branch** | `fix/2026-10-12-issue-286-stage2-wedge-fixes`, created from `origin/main` |
| **Tip SHA** | base `origin/main` `8a7cdab` |
| **Push status** | handoff pushed on `docs/2026-10-12-issue-286-stage2-fixes-handoff` |
| **PR** | not opened |
| **Ryan GATE** | none for hermetic implementation. Ryan alone merges. Deploying (promoting `runtime-main`, deploying the regenerated protocol surfaces, any watcher start) needs separate Ryan grants after the merge. |
| **Track A ingest** | your Cursor transcript, at handoff |

## What to build

**Why:** the Stage 2 canary ran on 2026-10-12 and stopped at the paid ceiling
after 12.8 h. The report is
`docs/inter-model/CLAUDE-2026-10-12-issue-286-codex-stage2-report.md`, on
branch `docs/2026-10-11-issue-286-codex-stage1-run`. It found these
problems:

- **The wedge (P1).** Two new Codex sessions are stuck for good:
  - `rollout-2026-10-12T14-21-47-…`, transaction `d70a723d…`, in
    `APPLYING` since 15:59:40, with 61 failed retries;
  - `rollout-2026-10-12T20-20-37-…`, which was never captured, with 6 failed
    retries.

  In each case another writer indexed a *different* source while the
  incremental apply was running. The apply then failed with
  `non_source_isolation_changed`. After that, every retry fails with
  `rollback_export_foreign_changed`, because recovery demands that
  everything else in the store and the export be byte-identical to how it
  was when the transaction started. Once any other source has indexed, that
  can never be true again.
- **Agent self-indexing (P2).** The standing Track A rule tells every agent
  to run `convmem index --file` on its own transcript at each handoff. Codex
  did this 18 times during the canary, and those runs caused the second
  wedge. Asking each session to stop doesn't hold: new sessions read the
  standing rule.
- **Plain opens queue indexes (P3).** The watcher queues a path on every
  filesystem event, including open and close-without-write. The effects:
  - any app that reads old sessions (the ChatGPT app at launch) starts a
    paid catch-up wave, 34 sessions in one case;
  - the watcher's own reads re-queue files: 23,496 `skip (unchanged)`
    checks, and the endless P1 retries.

Build C1–C4 below. All four are binding.

## Integration points

All lines are at `8a7cdab`.

| What | Where |
|---|---|
| Incremental apply (holds only this source's lock) | `incremental_jsonl.py:1984` `_commit_generation`; `source_flock` at `:2005` |
| Isolation check pinned to transaction-start state | `incremental_jsonl.py:1487` `_verify_non_source_collections`; called at `:2036`, `:2046`, `:2134` |
| Export rollback that demands identical foreign bytes | `incremental_jsonl.py:1668` `_restore_export`; the refusal at `:1723–1733` |
| Before-image restore | `incremental_jsonl.py:1615` `_restore_before_images` |
| Recovery entry for `APPLYING` (`replay_forward`) | `incremental_jsonl.py:2140` `_roll_forward`, then `_commit_generation` with `rollback_authority_sha256` |
| Legacy write phase (another source's writer) | `ingest.py:628` `_commit_chunk_to_stores` (`source_flock` `:652`, Chroma session `:661`, `export_flock` `:700`); `ingest.py:1232` `_snapshot_reindex_rows`; `ingest.py:1251` `_prune_completed_reindex` |
| Lock helpers and ordering | `purge_locks.py` (`source_flock` `:83`, `export_flock` `:112`, `assert_lock_ordering_ok` `:39`) |
| Watcher retries (plain errors are never counted) | `watch.py:602` `_record_ready_path_failure`; refusal quarantine via exit `_LIVE_ROUTE_REFUSED_EXIT = 91` (`watch.py:31`) |
| Watcher event intake | `watch.py:733–739` `Handler.on_any_event` |
| Watcher singleton lock | `watch.py:515` `_lock_path_from_config`, `watch.py:544` `acquire_lock`; doctor reads it at `doctor.py:1712` |
| `index --file` command | `convmem.py:279` `index` |
| Track A rule (protocol source) | `config/agent-protocol.md`, the "Session tracking" block (about lines 46–75: "Agents still **nudge both**…"); regenerate with `scripts/generate-agent-protocol.sh` |

## Specification

**C1, one shared index write window (binding; prevents P1).**
- Add one exclusive, store-wide index write lock, for example
  `purge_locks.index_write_flock(cfg)`, beside the existing lock helpers.
- Lock order: `source_flock` → index write lock → Chroma writer session →
  `export_flock`. Extend `assert_lock_ordering_ok` to enforce it.
- The incremental route holds it in `_commit_generation`, from the
  before-image snapshot through `_reconcile_dedupe`, under the existing
  `source_flock`.
- The legacy route holds it for each write phase:
  - `_commit_chunk_to_stores`;
  - the snapshot and prune in `_snapshot_reindex_rows` and
    `_prune_completed_reindex`.
- Every other writer that changes summaries, units or the export in a
  session can share that store holds it too, as soon as it writes:
  - `convmem add`, `forget` and `monitor`;
  - the deferred or semantic dedupe writers, if they write those
    collections.

  List the ones you wrap in your report.
- **Never hold it during paid provider work** (summarize, distill or embed
  calls). It covers only store and export writes, so a slow model call can't
  stall every writer.
- **Result:** a cooperating writer can no longer change non-source state in
  the middle of an apply, so `non_source_isolation_changed` means a real
  foreign writer.

**C2, recovery is source-scoped (binding; unwedges P1).**
- In replay and rollback, stop requiring foreign state to equal the state
  at transaction start. Prove only what this transaction owns:
  - **Isolation:** `_verify_non_source_collections` compares against a
    digest taken under the C1 lock at the start of *this* apply attempt,
    not the digest saved in the rollback journal. Keep the check after
    apply, under the same lock hold.
  - **Export rollback:** `_restore_export` passes current foreign lines
    through unchanged (as it does now). It drops the requirement that
    foreign bytes, lines and digest match the before-image. It must still
    prove that this source's current export lines are one of:
    - its before-image lines;
    - lines this transaction wrote;
    - a mix of the two.

    Any other line owned by this source is foreign tampering, and the
    rollback keeps refusing with `rollback_export_foreign_changed`. If export
    order matters anywhere, keep the current placement where possible.
    Otherwise, document that restored lines go at the end.
  - Keep every other authority check unchanged: the rollback journal hash,
    the source path, the prepared keys and the prefix revalidation.
- **Acceptance case:** after a C2 deploy, the next run of each existing
  wedged transaction (`APPLYING` with prepared keys, foreign export grown)
  must either replay forward to `committed` or roll back cleanly and then
  commit. It must not transform again: prepared work is reused, so the
  paid calls are 0 for already-prepared chunks.
- This relaxes a reviewed invariant. Explain the reasoning in the PR body:
  C1 makes foreign interleaving impossible during an apply, so foreign
  changes *between* attempts are legitimate.

**C3, bounded retries (binding).**
- When an incremental run fails with the same error code for the same
  source and the same source prefix digest twice in a row, the child exits
  with the existing `live_route_refused:` contract (exit 91). The watcher's
  refusal quarantine then holds the path until its prefix changes.
- The diagnostic must name:
  - the source;
  - the transaction id;
  - the code;
  - the remedy ("wedged incremental transaction; see doctor").
- `convmem doctor` reports a wedged incremental transaction as WARN, with
  the same fields.

**C4, the watcher ignores events that don't write, and agents don't
self-index watched sources (binding; P3 and P2).**
- **C4a, watcher intake:** `Handler.on_any_event` queues only `created`,
  `modified`, `moved` and `closed` (closed after write). For `moved`, queue
  `dest_path`, plus `src_path` as before. It ignores `opened` and
  `closed_no_write` (watchdog 6.0.0 event types). Keep the
  directory-event skip.
- **C4b, `index --file` defers to a running watcher:**
  - **Defer when:** the target is watchable (`watch.is_watchable`) and
    inside the configured watch roots, and the watcher's singleton lock is
    held by a live watcher.
  - **Then:** `convmem index --file` prints one line, `[index] deferred:
    the convmem watcher captures <path>`, and exits 0 without indexing.
  - **Override:** `--now` runs anyway, serialized by C1.
  - **Unchanged:** Claude transcripts, `docs/inter-model` docs and any path
    outside the watch roots, and everything while the watcher is not
    running.
- **C4c, the Track A rule:** in `config/agent-protocol.md`, replace "Agents
  still **nudge both**" with these points:
  - the watcher captures Codex, Kiro, Cursor, Copilot and Crush transcripts
    while it runs;
  - `convmem index --file` on them is deferred automatically, so agents
    need not run it;
  - Claude transcripts still need Track A.

  Regenerate the surfaces with `scripts/generate-agent-protocol.sh`, and keep
  the existing protocol tests passing. **Do not run**
  `scripts/deploy-agent-protocol.sh`: deploying to live surfaces is Ryan's
  step.

## Output contract

- No change to the transaction or checkpoint file formats, unless you need
  to. If you do, bump the version, and make old `APPLYING` transactions
  readable and recoverable.
- The admitted-run telemetry (`incremental_codex_admitted_run`) is
  unchanged.
- The `live_route_refused:` stderr format and exit code 91 are unchanged.

## What NOT to build

- P4 (the legacy route pays before the "changed during index" check), P5
  (stderr dropped by the watcher), P6 and P7. These are not authorized
  here.
- No manual repair of the two wedged production transactions. C2 must
  recover them on the next run after deploy.
- No live config edits, no `runtime-main` promotion, no watcher start or
  restart, no `deploy-agent-protocol.sh`.
- No paid provider calls. Tests are hermetic: a temporary `HOME`, `env -i`
  without API keys, and providers pointed at `127.0.0.1:9`.
- No changes to the admission policy (`admitted_after`) or to Kiro and
  Cursor routing.

## Test expectations

Tests 1–5 must **fail at `8a7cdab`** and pass on your tip.

1. **The wedge reproduction.**
   - Setup: start an incremental apply, and between the before-image and
     the post-apply check, write rows and export lines for another source.
     At `8a7cdab`, the next two runs fail with
     `rollback_export_foreign_changed`.
   - Expected after the fix:
     - the next run reaches `committed`;
     - the checkpoint advances;
     - no transform runs again for prepared keys;
     - the other source's rows and lines are byte-identical before and
       after.
2. **The lock.** A legacy `_commit_chunk_to_stores` started during an
   incremental apply blocks until the apply's write window ends. Use a
   deterministic thread or event harness, not sleeps. Paid work, which is
   mocked, does not hold the lock.
3. **Bounded retries.** The same failure twice with an unchanged prefix
   gives exit 91 and a refusal quarantine. A third watcher pass does not
   spawn. A prefix change re-allows the path.
4. **Watcher intake.** `FileOpenedEvent` and `FileClosedNoWriteEvent` are
   not queued. `FileModifiedEvent`, `FileCreatedEvent`, `FileClosedEvent`
   and `FileMovedEvent` (with `dest_path`) are queued.
5. **Deferral.**
   - With the watch lock held by a live process, `index --file <watched
     rollout>` prints the deferral line, exits 0 and writes nothing.
   - `--now` indexes.
   - A Claude transcript path is not deferred.
   - With no watcher running, nothing is deferred.
6. **Tamper is still refused.** A line owned by this source that is neither
   a before-image line nor one this transaction wrote still makes the
   rollback refuse.
7. The full existing suite passes. Known local false failures are listed in
   memory: golden eval #320 and platform segfaults. Note any you hit.

## Acceptance criteria

- C1–C4 are implemented as specified. Tests 1–6 are new and failed at
  `8a7cdab`; the full suite is green apart from the known local false
  failures.
- Your report lists the writers wrapped by the C1 lock. It also gives the
  lock order and confirms that no lock is held across paid calls.
- `git diff origin/main --stat` touches only code, tests,
  `config/agent-protocol.md` and the regenerated protocol surfaces.
- All commits are pushed with an explicit refspec. No PR, no merge.

## Branch convention

`fix/2026-10-12-issue-286-stage2-wedge-fixes` from `origin/main`. Push every
commit with `git push -u origin
"fix/2026-10-12-issue-286-stage2-wedge-fixes:refs/heads/fix/2026-10-12-issue-286-stage2-wedge-fixes"`.
Report the tip SHA, the test results and `git log origin/main..HEAD
--oneline`.

## Next after implementation

1. Claude verifies:
   - re-runs tests 1–6 at your tip and at `8a7cdab`;
   - runs a hermetic watcher reproduction: concurrent legacy writes during an
     apply, plus an app-style open storm.
2. The Copilot audit lane does a targeted safety and isolation audit, since
   C2 relaxes an isolation invariant. Kiro does a design review of C1 and
   C2.
3. Ryan opens and merges the PR.
4. Separate Ryan grants follow:
   - promote `runtime-main`;
   - deploy the protocol surfaces;
   - run a second watcher canary with the Stage 2 stop conditions. The two
     wedged sessions should recover in its first hour.

## Related files

| What | Path |
|------|------|
| Stage 2 report (P1–P7) | `docs/inter-model/CLAUDE-2026-10-12-issue-286-codex-stage2-report.md` (branch `docs/2026-10-11-issue-286-codex-stage1-run`) |
| Stage 2 run log (evidence) | `docs/inter-model/CLAUDE-2026-10-12-issue-286-codex-stage2-run.md` (same branch) |
| Arc brief | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Incremental route | `incremental_jsonl.py` |
| Legacy route | `ingest.py` |
| Locks | `purge_locks.py` |
| Watcher | `watch.py` |
| Protocol source and generator | `config/agent-protocol.md`, `scripts/generate-agent-protocol.sh` |
