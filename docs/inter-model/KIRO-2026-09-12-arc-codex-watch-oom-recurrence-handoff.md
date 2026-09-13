# Investigation Handoff: Watch index-child OOM recurrence — was this expected right now?

**Date:** 2026-09-12
**Author:** Kiro (design/triage)
**For:** Arc Codex agent (Codex lane — Kiro JSONL production integration)
**Authorization:** Ryan, 2026-09-12 (verbal — "make a handoff to the agent working on Arc Codex to see if this was expected at the moment")

> **This is a diagnostic question handoff, not an implementation authorization.**
> It asks the Arc Codex agent one thing: *did any in-flight or recently merged
> Arc Codex work touch the JSONL/Codex index read path in a way that would
> explain a sudden watch-child memory regression tonight (2026-09-12)?* No build
> is authorized here. The P2 corrective Execute routing in `LATEST.md` is
> unchanged and remains Ryan-gated.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` (diagnostic — awaiting Arc Codex answer; no build authorized) |
| **Branch** | `docs/2026-09-11-2026-09-11-codex-jsonl-p2-corrective-execute` (this doc written here; untracked, does not modify tracked files) |
| **Tip SHA** | `b83d2a8` (branch tip at time of writing) |
| **Push status** | `local-only — push before cloud handoff` |
| **PR** | `not opened` |
| **Ryan GATE** | Any fix to the index path remains Ryan-authorized; this handoff only asks Arc Codex whether the timing is expected |

---

## The question (why you were pinged)

The convmem **watch index child** OOM-looped tonight and fired repeated desktop
notifications ("system is low on memory / close browser tabs"). The system was
**not** low on memory (62 GiB total, ~42 GiB free throughout). It was a
**per-cgroup OOM**: each spawned `index --file` child grew to a flat **~12.5 GiB
RSS** and was SIGKILLed at the configured `subprocess_memory_max = 12G`, then the
watcher retried the same files every cycle → notification storm.

This is a **known recurring bug** (GitHub issue **#268**: the watcher re-indexes
each transcript *in full on every append*; prior fixes were interim cap raises
6G→12G, never the incremental fix). That part is expected background.

**What is NOT explained by #268 alone, and why this is for you:** tonight's
OOM'd files were **tiny** — 9.7 MB, 7.8 MB, and a 5.8 MB `history.jsonl` — yet
each drove the child to ~12.5 GiB (a ~1300× size→RSS blowup, and *flat* across
different small file sizes). File growth does **not** explain the trigger. A
flat multi-GiB working set independent of input size looks like an **unbounded
structure in the code path**, not size-proportional embedding.

The timing lines up with **Arc Codex — Kiro JSONL production integration**:
recent merges touch the exact code that reads Codex/JSONL transcripts into the
indexer, and the current checkout is the P2 corrective Execute branch.

**Please answer:** Did any Arc Codex change — merged or in-flight — alter how
Codex/JSONL rollouts are parsed or indexed such that the per-file index child
could accumulate an unbounded in-memory structure? Is a memory-behavior change
on the JSONL read path **expected at this moment**, or would this be an
unintended regression?

---

## Evidence to ground the investigation

**Kernel OOM kills tonight (all `constraint=CONSTRAINT_MEMCG`, task `python3.11`, anon-rss ≈ 12.5 GiB):**

```
Sep 12 18:05:38  run-p816799-i780746.scope   Killed pid 816799  anon-rss 12555984kB
Sep 12 19:51:02  run-p880132-i785397.scope   Killed pid 880132  anon-rss 12556160kB
Sep 12 20:12:37  run-p895258-i882128.scope   Killed pid 895258  anon-rss 12556300kB
Sep 12 20:30:48  run-p905242-i871930.scope   Killed pid 905242  anon-rss 12556420kB
```

**Watch journal — files that OOM-looped (from `journalctl --user -u convmem-watch.service`):**

```
19:28  spawn: index --file ~/.codex/history.jsonl
19:43  error processing ~/.codex/history.jsonl: index subprocess timed out after 900 seconds
19:49  spawn: index --file .../2026/09/12/rollout-...01a09438...jsonl
19:51  error processing .../rollout-...01a09438...jsonl: index subprocess exit -9   (SIGKILL/OOM)
20:27  spawn: index --file .../2026/09/12/rollout-...01a0948f...jsonl
20:30  error processing .../rollout-...01a0948f...jsonl: index subprocess exit -9   (SIGKILL/OOM)
```

**File sizes at time of OOM (the crux — these are SMALL):**

| File | Size | Outcome |
|------|------|---------|
| `~/.codex/sessions/2026/09/12/rollout-...01a09438...jsonl` | 9.7 MB | exit -9 (OOM at 12G) |
| `~/.codex/sessions/2026/09/12/rollout-...01a0948f...jsonl` | 7.8 MB | exit -9 (OOM at 12G) |
| `~/.codex/history.jsonl` | 5.8 MB | 900s timeout (then re-loops) |

**Prior ledger context (issue #268 arc):**

- "A watched transcript indexer that re-indexes the entire file on every append will eventually OOM once transcripts grow large; the real fix requires incremental indexing rather than a cap raise alone."
- "A small input file doesn't rule out OOM — the memory growth is likely in the parent/subprocess; investigate the complete spawn sequence and RSS before fixing."
- "Reprocessing an entire append-only JSONL file on every change makes memory usage grow with file length and can OOM even when the file is small on disk."
- Interim mitigation history: `subprocess_memory_max` raised 6G→12G on 2026-08-31 (config comment in `~/.config/convmem/config.toml [watch]`).

**Recent Arc Codex / JSONL-path commits (suspect window):**

```
881133d  Add default-off incremental indexing for Kiro JSONL sessions (#293)
907c828  Add a hermetic harness for the JSONL production canary (#296)
ac6a56b / 3db219e  fix: bound retrieval and harden watcher file handling
(current branch: docs/2026-09-11-...-codex-jsonl-p2-corrective-execute)
```

---

## Interim mitigation already applied (reversible, no code)

To stop the notification storm, Kiro excluded the three looping files via the
built-in CLI (no `--purge`; existing indexed rows retained):

```
convmem exclude ~/.codex/history.jsonl
convmem exclude ~/.codex/sessions/2026/09/12/rollout-...01a09438...jsonl
convmem exclude ~/.codex/sessions/2026/09/12/rollout-...01a0948f...jsonl
```

Verified after: watcher now logs `skip (excluded)` for these; **no OOM kills
after 20:30:48**; watch service healthy (`active`, ~1.6G current / 2.1G peak vs
8G ceiling). Undo any with `convmem exclude --undo <path>`.

**Caveat:** this is whack-a-mole. The OOM is size-independent, so any *new*
active Codex transcript can hit the same 12G wall. Exclusions are a stopgap, not
a fix.

---

## What NOT to do from this handoff

- Do **not** treat this as authorization to change the index path, watcher, or
  config — any fix is Ryan-gated.
- Do **not** raise `subprocess_memory_max` again as "the fix" — the ledger
  already flags cap raises as interim-only, and a flat 12.5G working set on a
  6 MB file will just move the wall.
- Do **not** `--purge` the excluded sources — we want to re-include them once the
  root cause is understood.

---

## Requested response from Arc Codex agent

1. **Expected-or-not:** Is a memory-behavior change on the Codex/JSONL index
   read path expected at this moment (part of #293 / P2 corrective work), or is
   this an unintended regression?
2. **Code pointer:** If plausibly related, point to the function/commit in the
   JSONL parse/index path that could accumulate an unbounded in-memory structure
   (flat ~12.5 GiB regardless of input size).
3. **Interaction check:** Does `#293`'s "default-off incremental indexing"
   interact with the *watch* full-file path in a way that could double-buffer or
   retain per-line state?
4. **Routing:** Confirm whether the durable fix belongs to the Arc Codex arc
   (incremental JSONL indexing) or to issue #268 (watch full-file re-index), so
   Ryan can route the eventual implementation to the right lane.

---

## Related files

| What | Path |
|------|------|
| Arc Codex STATUS | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Watch incremental fix design | `docs/plans/DESIGN-watch-incremental-index.md` |
| P2 corrective Execute brief | `docs/inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-corrective-execute.md` |
| Watch config + cap history | `~/.config/convmem/config.toml` (`[watch]`), `~/.config/systemd/user/convmem-watch.service.d/oom-mitigation.drop-in.conf` |
| Prior watch-OOM arc | GitHub issue #268 (resume plan commit `92395e9`) |

---

## Leaving / picking up checklist

**Author (Kiro, leaving):**

- [x] This file written on the current branch (untracked; no tracked-file edits)
- [x] `LATEST.md` bullet at top with link and resume state
- [ ] Branch pushed (flag `local-only` until pushed)
- [ ] Track A: index this Kiro session transcript at handoff

**Implementer / responder (Arc Codex, picking up):**

- [ ] Read this file before answering
- [ ] Answer the four questions above (expected-or-not is the priority)
- [ ] If a regression, note the suspect commit; do not fix without Ryan gate

<!-- Diagnostic handoff. Storm already mitigated via exclusions; this asks Arc Codex whether the timing is expected. -->
