# Stage 2 burn report: new Codex sessions are cheap; old sessions and agent self-indexing are not

**Arc: Codex (#286), Stage 2 (24 h watcher canary).**
**Date:** 2026-10-12 (CDT)
**Author:** Claude (Opus 5.5), the ops runner under Ryan's Stage 2 grant
**For:** Ryan, who decides. Cursor implements the fixes once Ryan authorizes
them. Copilot and Kiro review.
**Evidence:** the run log
`docs/inter-model/CLAUDE-2026-10-12-issue-286-codex-stage2-run.md`, on the
same branch.

## Result

**Verdict: stopped at the paid ceiling after 12.8 h. This is not a PASS.**
The watcher ran from 08:31:18 to 21:21:14. The guard stopped it when the
estimate passed Ryan's ceiling: about 410 calls against 400.

- **The Codex fix works.** 4 new Codex sessions were captured on the
  incremental route in 6 runs, for about 12 paid calls. No new session went
  down the legacy route.
- **The money went elsewhere.** 398 of the roughly 410 calls were legacy
  re-indexes:
  - old Codex sessions: one-time catch-up, plus one old thread still in use;
  - Kiro and Cursor transcripts, which have no incremental route yet.
- **Two new sessions are wedged.** Agents ran `convmem index` on sessions the
  watcher was capturing. Capture of both sessions is frozen. The retries cost
  nothing, but they never stop.
- **Memory is fixed.** The watcher stayed at about 110 MB all day, against
  4 GiB in 16 minutes this morning before the manifest was removed.

**Permanent activation: not yet.** First P1–P3 below need to land, then a
second canary.

## Burn by cause

The estimate is 2 paid calls per chunk (summarize and distill). It counts
runs that paid and were then discarded.

| Cause | Runs | Calls | Repeats? |
|---|---:|---:|---|
| One old Codex thread still in use (started Oct 10 23:16, 62 MB) | 7 | 138 | Yes, on every change. 4 of the 7 runs were discarded after paying (P4) |
| Catch-up wave 1 (14:19–15:02): the Codex app opened old sessions | 9 | 106 | Once per session |
| Catch-up wave 2 (17:39–18:25): opened when the ChatGPT app launched | 34 | 106 | Once per session |
| Kiro transcripts (legacy route) | 9 | 30 | Yes |
| Cursor transcripts (legacy route) | 7 | 16 | Yes |
| Another old Codex session | 1 | 2 | Once |
| **New Codex sessions (incremental route)** | 6 | **12** | Yes, but cheap |
| **Total** | | **~410** | |

**Caveats:**
- The estimate is not reconciled with DeepSeek billing. Comparing it with
  DeepSeek's usage page for Oct 12 calibrates it.
- 24 `convmem index` runs launched by agents ran outside the watcher's
  journal and are not counted: 18 by Codex, 3 by Claude and 3 from shells.

**Repeating cost at today's activity:** leave out the one-time catch-up (214
calls) and the in-use old thread (138). What remains is about 58 calls in
12.8 h, roughly 100 a day:
- Kiro: 30;
- Cursor: 16;
- new Codex sessions: 12.

It is unknown how many stale old sessions are still waiting to be caught up.
Wave 2 went from Oct 10 back to Sep 25, and later opens of older files found
them unchanged, so most of the backlog is probably cleared.

## What worked

- **Admission:** every Codex rollout started after the cutoff took the
  incremental route, at 1 chunk per run.
- **#308 (inter-model rejection):** one rejected doc was spawned once. After
  that it was skipped 201 times, with no new spawn.
- **Memory:** watcher RSS stayed at 108–112 MB. The cgroup peak was
  1.34 GiB. There were no OOM events and 0 restarts.
- **Recovery:** an interrupted `PREPARING` transaction (14:42) recovered
  without paying again.
- **Quarantine:** the 593 MiB Sep 21 rollout was skipped every time.
- **The guard** stopped the watcher at the ceiling, as granted. It had two
  false stops earlier in the day, both bugs in my stop check, now fixed and
  replayed clean.

## Problems found (proposed handoffs; none authorized yet)

**P1: a concurrent writer wedges a session. Blocks activation; Cursor code
fix.**
- **What happens:** another process changed shared state while the
  watcher was in the middle of applying a run for that session. The watcher
  run then fails with `non_source_isolation_changed`. The transaction stays
  in `APPLYING`, and every retry after that fails with
  `rollback_export_foreign_changed`. The retries keep coming with no new
  writes: the failed run's own reads re-queue the file (see P3).
- **Affected sessions:**
  - `rollout-2026-10-12T14-21-47-…`: transaction `d70a723d…` has been stuck
    since 15:59:40, with 61 failed retries.
  - `rollout-2026-10-12T20-20-37-…`: it was never captured, with 6 failed
    retries.
- **The fix needs:**
  - a safe way out of `APPLYING` after a foreign change, so the run either
    replays forward or rolls back without losing the session's data;
  - a stop to unbounded retries.

**P2: agents index their own sessions. Blocks activation; protocol change
plus code.**
- **Why it happens:** the standing Track A rule tells every agent to run
  `convmem index --file` on its own transcript at each handoff. Codex did this
  18 times today. Asking each session to stop doesn't hold: the 20:20
  session started after Ryan's message, followed the rule 6 times between
  20:24 and 20:36, and was wedged by the watcher's first run at 20:41.
- **Options:**
  - **(a) Protocol:** in `config/agent-protocol.md` and its generated
    surfaces, skip Track A for watched sources (Codex rollouts, Kiro, Cursor)
    while the watcher is active. Claude transcripts are not watched, so
    Claude keeps Track A.
  - **(b) Code:** `convmem index --file` on a source the watcher captures
    waits for the source lock or hands the work to the watcher, instead of
    racing it.
- **Recommendation:** both. (b) is the durable fix, and (a) stops the
  collisions today.

**P3: plain opens queue indexes. Should land before activation; Cursor.**
- The watcher queues a path on any event, including open and
  close-without-write (`watch.py:734`). The result:
  - any app that reads old sessions, such as the ChatGPT app at launch,
    starts a catch-up wave;
  - the watcher's own reads keep re-queueing files: 23,496
    `skip (unchanged)` checks, plus the endless P1 retries.
- **The fix:** ignore events that don't write.

**P4: the legacy route pays before it checks for changes. Cursor.**
- `_process_file_chunks` does the paid work before `_prune_completed_reindex`
  checks whether the file changed during the run (`ingest.py:1251`,
  `:1270`).
- Today 10 runs paid and were then discarded. 4 of them were the in-use old
  thread, about 78 calls.
- **The fix:** check before paying, or keep the paid results.

**P5: the watcher drops the stderr of a successful child. Small fix; Cursor.**
- `watch.py:336–374` forwards only stdout on success. The
  `incremental_codex_admitted_run` event is printed on stderr, so it never
  reaches the journal.
- This caused the second false stop. It also means admitted runs can't be
  audited from the journal.

**P6: runs launched by agents are outside burn accounting.** P2 and P5
mostly fix this. Until then, provider usage is the only complete measure.

**P7: old sessions stay on the legacy route. A policy decision for Ryan.**
- Retire old threads still in use: start a new thread instead of resuming.
- An incremental route for Kiro and Cursor JSONL is the next burn slice.

## Production state now

- `convmem-watch.service` has been inactive and disabled since 21:21:14.
  Nothing is captured automatically.
- `runtime-main` is at `8a7cdab`.
- Live config:
  - Codex admission is on (`admitted_after = 2026-10-12T04:04:00Z`);
  - no repository-knowledge manifest. The backup is kept, and the manifest fix
    is a separate reminder.
- The two wedged transactions are untouched. There was no manual repair.
  They wait for P1.

## Decisions for Ryan

1. **Authorize the fix handoffs:**
   - P1, P3, P4 and P5 to Cursor, as one handoff or split (P1 and P3
     first);
   - P2 as a protocol change plus code.
2. **The watcher until then:** I recommend leaving it off. The burn is zero
   while it's off, and nothing new gets wedged. The trade-off: capture of
   Codex sessions is manual until then.
3. **The old Oct 10 23:16 Codex thread:** move that work to a new thread.
4. **Activation:** after P1–P3 land, run a second canary with the same stop
   conditions.

## TL;DR

- [Arc Codex] The canary stopped at about 410 of 400 calls after 12.8 h.
  New Codex sessions cost only about 12 calls; old sessions and Kiro/Cursor
  cost the rest.
- Two new sessions are wedged because agents index their own sessions while
  the watcher captures them.
- Before activation: the wedge fix (P1), a stop to agent self-indexing (P2),
  and ignoring plain opens (P3).
