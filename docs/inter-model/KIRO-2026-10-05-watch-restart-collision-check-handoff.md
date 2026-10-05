# Collision-Check Handoff: watch restart + runtime-main clean

**Date:** 2026-10-05
**Author:** Kiro (review/design lane — non-implementing)
**For:** Any agent currently working on convmem (esp. Switchboard Arc, OpenClaw Watch Coverage, Trapdoor Hunt / issue #286 incremental-index)
**Authorization:** Ryan, 2026-10-05 (verbal — asked me to circulate my plan so active agents can flag conflicts before I act)

> **Purpose of this doc:** This is NOT an implementation brief. It is a
> **collision check.** I (Kiro) intend to perform the operational actions in
> "Planned actions" below on the **live runtime**. Before I do, Ryan wants
> active agents to confirm these actions will not disturb in-flight work.
> **If any planned action touches your work, say so and I will stop.**

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `DONE` — Ryan authorized 2026-10-05; all four steps executed successfully |
| **Branch** | current checkout: `feat/2026-09-24-2026-09-24-branch-cleanup-report-gate` (this doc only) |
| **Target of actions** | live runtime, NOT a branch: `~/.local/share/convmem/` + `.worktrees/runtime-main` worktree |
| **Push status** | this doc is local until pushed; the planned actions are operational, not commits |
| **PR** | not opened (operational change, no code change proposed here) |
| **Ryan GATE** | Ryan must give explicit go-ahead to run Planned actions 1–4; agents must clear collisions first |

---

## Why this exists (the problem)

1. **Watch is down ~2 days.** `convmem-watch.service` is `inactive (dead)`
   since Sat 2026-10-03 11:02. It fails to start because `watch.lock` holds a
   **stale pid 1218 that is not running** — a stale-lock deadlock. No
   incremental filesystem indexing has happened since. (Indexing *store* is
   otherwise healthy: `convmem doctor` exits 0, live Chroma clean, written
   today; restic daily + offsite both cover today.)

2. **The runtime worktree is running unreviewed code.** `.worktrees/runtime-main`
   (HEAD = clean `a92a74e`, "Classify new tracked files… (#339)") has
   **uncommitted edits** that were made directly in the live runtime dir by a
   Crush session on 2026-09-25 while working in ButsabaJobScout:
   - modified (tracked): `adapters/detect.py` (+5), `ingest.py` (+1/-1)
   - untracked (new): `adapters/butsaba_scout_doc.py`, `tests/test_butsaba_scout_doc_adapter.py`

   This is the `dirty_main` WARN in doctor. The new adapter indexes Butsaba's
   job documents, **including `.docx` resumes containing real-person PII**. It
   was never committed or reviewed, and it bypassed the branch/review lane.
   Restarting watch as-is keeps the production indexer running unreviewed code
   that ingests resume PII into the shared corpus.

3. **These two block each other.** Can't safely restart watch while the live
   dir runs unreviewed PII-ingesting code; can't leave watch down indefinitely.

**Preservation already done (no data loss risk):** the uncommitted edits are
archived verbatim in the git-ignored `artifacts/runtime-main-uncommitted-2026-09-25.zip`
(holds both new files + a `tracked-changes.patch` for `detect.py`/`ingest.py`;
ignored via `.git/info/exclude` so Butsaba's name stays out of the public repo).

---

## Planned actions (what I intend to run on the live runtime)

```bash
# 1. Restore runtime-main worktree to clean a92a74e (archive already holds the edits)
cd /home/lauer/Projects/convmem/.worktrees/runtime-main
git restore adapters/detect.py ingest.py
rm -f adapters/butsaba_scout_doc.py tests/test_butsaba_scout_doc_adapter.py

# 2. Confirm clean
git status --short            # expect empty

# 3. Clear the stale watch lock (pid 1218 is dead) and restart watch
rm -f ~/.local/share/convmem/watch.lock
systemctl --user start convmem-watch.service
systemctl --user status convmem-watch.service --no-pager
journalctl --user -u convmem-watch -n 20 --no-pager

# 4. Re-run doctor to confirm dirty_main cleared and watch healthy
cd /home/lauer/Projects/convmem && convmem doctor
```

**Recommended follow-up (NOT in this operational pass):** if the adapter is
wanted, it goes through a proper branch + review with naming that does **not**
expose Butsaba, sourced from the archive. That is a separate implementation
handoff, not this doc.

---

## What this plan will and will NOT touch (Switchboard Arc guardrail)

**WILL touch:**
- the uncommitted Crush edits in `.worktrees/runtime-main` (reverted; archived)
- `~/.local/share/convmem/watch.lock` (stale pid removed)
- `convmem-watch.service` (started)

**Will NOT touch (left exactly as-is — believed intentionally off/pinned):**
- `convmem-monitor.timer` — `disabled`/dead (intentional; leaving off)
- shadow-ledger — disabled, Phase 0 default (leaving off)
- the runtime worktree's **pinned commit** `a92a74e` — HEAD is unchanged; I only
  discard working-tree edits, I do **not** move or advance the pin
- any OpenClaw Watch Coverage pin / admitted-file manifest (service stays on the
  clean runtime worktree commit; I am not promoting or advancing it)
- restic password-backup WARN — left for Ryan (drive not mounted)
- no code committed, no PR, no merge, no corpus mutation beyond normal watch resume

---

## Outcome (2026-10-05, executed)

All four steps ran successfully after Ryan's go-ahead:

1. **runtime-main restored** to clean `a92a74e` — `git status` empty, HEAD pin
   unchanged. Uncommitted Crush edits remain preserved in the git-ignored
   `artifacts/runtime-main-uncommitted-2026-09-25.zip`.
2. **Stale `watch.lock` removed** (dead pid 1218).
3. **`convmem-watch.service` restarted** — now `active (running)`, new pid
   3687429, memory ~165 MB (well under 4G cap), observing all paths,
   `debounce=90.0s, subprocess_index=on` (upsert-isolation containment active).
   ButsabaJobScout `.crush/crush.db` continues to be skipped as `quarantined`
   at the watch layer.
4. **`convmem doctor` → all checks passed**, warnings dropped 5→4, and the
   **`dirty_main` WARN is cleared**. The 4 remaining warnings are pre-existing
   and unrelated (legacy embed metadata, restic-password offline copy,
   standing-register due, arc staleness). Corpus 104,241 → 105,236.

Nothing intentionally-off was touched: monitor timer, shadow-ledger, OpenClaw
manifest, and the `a92a74e` pin are all unchanged.

**Follow-up (separate, not done here):** if the Butsaba adapter is wanted, it
goes through a branch + review with privacy-safe naming, sourced from the
archive. Not authorized in this pass.

---

## Collision clearance status

| Lane | Verdict | By / when |
|------|---------|-----------|
| **Switchboard Arc** | ✅ CLEAR — no collision; plan OK within stated WILL/WILL NOT bounds | Switchboard agent, 2026-10-05 (work isolated, committed, pushed; does not depend on watcher or `watch.lock`) |
| **OpenClaw Watch Coverage** | ✅ CLEAR (no active owner) — no agent assigned, none working the lane now; plan preserves pinned commit `a92a74e` and admitted-file manifest untouched | Ryan, 2026-10-05 |
| **issue #286 incremental-index (Trapdoor Hunt)** | ✅ CLEAR (no active owner) — no agent assigned, none running; no live measurement to invalidate | Ryan, 2026-10-05 |

> **All collision lanes resolved.** Switchboard explicitly cleared; the other
> two have no assigned/active owner, and the plan does not alter the durable
> state those arcs depend on (pin `a92a74e`, OpenClaw manifest). Only remaining
> gate: Ryan's go-ahead to run the four operational steps. Push to distribute
> this doc is moot — no owner to deliver it to.

## Collision questions for active agents (please answer)

Answer any that apply to your lane; silence on a point = "no conflict" at your own risk:

1. **Switchboard Arc:** Is anything in your arc depending on `convmem-watch`
   staying **down**, or on `watch.lock` as-is? Do you need the monitor timer or
   shadow-ledger to remain off (I am already leaving them off)?
2. **OpenClaw Watch Coverage:** Does restarting watch now disturb the pinned
   runtime worktree / admitted-file manifest state? Is a controlled promotion
   mid-flight that a restart would interfere with?
3. **issue #286 incremental-index (Trapdoor Hunt):** Are you mid-measurement
   against the live watcher or live Chroma such that a restart or a dirty→clean
   flip of `detect.py`/`ingest.py` would invalidate results?
4. **Anyone:** Is any process relying on the uncommitted `butsaba_scout_doc`
   adapter being live right now (i.e. actively indexing Butsaba docs)? If so,
   reverting it will stop that indexing.
5. **Anyone holding `watch.lock` legitimately:** pid 1218 reads as dead and no
   convmem watch process exists — but confirm you don't have a watcher you
   expect to be holding it.

---

## Related files

| What | Path |
|------|------|
| Preserved uncommitted edits (git-ignored) | `artifacts/runtime-main-uncommitted-2026-09-25.zip` |
| Live runtime store (healthy) | `~/.local/share/convmem/chroma` |
| Stale lock to clear | `~/.local/share/convmem/watch.lock` (pid 1218, dead) |
| Runtime worktree (dirty) | `.worktrees/runtime-main` (HEAD `a92a74e`) |
| Root-cause of prior crash incident | ledger `obs_c1499a660d4f`, `obs_e8db779df8c3` |

---

## Leaving / picking up checklist

**Author (Kiro, leaving this for collision review):**

- [x] This file written under `docs/inter-model/`
- [ ] `LATEST.md` bullet (will add on Ryan's say-so so I don't jump ahead of active work)
- [ ] Not pushed yet (local) — flag `local-only` if another machine needs it

**Reviewer (active agent picking up):**

- [ ] Read "Planned actions" + "WILL / WILL NOT touch"
- [ ] Answer the Collision questions for your lane
- [ ] Flag STOP if any action disturbs your in-flight work

<!-- Collision-check handoff, not an implementation brief. Kiro is review-required; actions above are operational and Ryan-gated. -->
