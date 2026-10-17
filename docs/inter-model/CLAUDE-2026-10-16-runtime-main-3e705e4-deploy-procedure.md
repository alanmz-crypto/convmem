# Deploy procedure: promote `runtime-main` from `8a7cdab` to `3e705e4`

**Arc: Codex (#286)**, crossing into **Arc Safe Harbor** (T1–T4 runtime).
**Date:** 2026-10-16
**Author:** Claude (Opus 5.5). **Approver:** Ryan, the owner of both arcs.
**Status:** PROPOSED. Nothing in it has been executed.

## Why this needs a procedure

`runtime-main` only fast-forwards along `main`. Between `8a7cdab` and `3e705e4`, main
carries five PRs:
- #389: binds risky writes to their backup target and rejects future snapshots;
- #391, #392, #394: Safe Harbor T1–T4, covering recovery evidence, incident release,
  approval recovery, and concurrency-test signals;
- #395: the Stage 2 wedge fixes.

Promotion therefore deploys about 3,260 lines of Safe Harbor write-guard, Restic-gate and
approval-recovery code alongside #395. Safe Harbor's STATUS (§6 item 3) requires an
approved procedure first. It must name the interpreter, the disposition of every old
process, the guard-state locations, how existing incident and snapshot schemas are
handled, and rollback compatibility. Each is covered below.

## Pre-deploy check (read-only, done 2026-10-16 ~21:35 CDT)

| Safe Harbor item | Finding |
|---|---|
| **Interpreter** | The units and the `~/.local/bin/convmem` wrapper use `~/miniforge3/envs/convmem/bin/python3.11` (3.11.15). All 20 changed runtime modules import cleanly under it from a scratch worktree at `3e705e4`. No dependency or requirements change. |
| **New code against the live state** | `doctor` from the scratch worktree exits 0. Apart from git-branch lines, it differs from the current doctor only by two new checks: `incremental_rollback_tamper` (0 records) and `wedged_incremental_transaction` (WARN: 11 stale transactions, see below). The run wrote no files beyond the background activity both doctors share. |
| **Backup binding (new for every admitted write)** | Dry run against the live config and backup env: profile `complete-data-v2`, data root `~/.local/share/convmem` (explicit, not derived). Write targets `chroma/`, `chroma.write-guard/` and `knowledge_units.jsonl` are all inside the root, so the **binding passes**. Today's snapshot `a045ba6a…` is current, so the **snapshot check passes**. |
| **Guard state** | `chroma.write-guard`: no quarantine, 2 segment restore points, 0 incidents. The new code reads it as-is (doctor `chroma_write_guard` PASS). No migration. |
| **Old processes** | The watcher, refine and monitor are stopped (watcher disabled), and they stay stopped. The reconcile timer runs `runtime-main` every 2 min, so it gets paused around the checkout. About 28 `mcp_server.py` processes hold the old code. They only read, and their lazy imports (brief, query) touch only `config.py` (+4 lines) and `llm.py` (+6). The worst case is a tool error in a long-lived MCP session, with no write. Each server picks up the new code when its client restarts. The Restic and digest units run scripts from `~/Projects/convmem`, not `runtime-main`, so the promotion doesn't affect them. |
| **Rollback** | `git -C .worktrees/runtime-main switch --detach 8a7cdab` (leaves the `main` ref alone). Old code ignores the new per-source retry-state files and the index-write lock file. One weakening: if the new code quarantines Chroma and we then roll back, the old code's ordinary clear could release a quarantine that the new code allows only through a validated release. Old code still refuses writes while the quarantine stands. |

**Stale incremental transactions (11, found by the new doctor).** These are Codex rollouts
left in PREPARING or APPLYING between 10-12 15:59 and 10-16 13:18:
- 1 is the Stage 2 wedge;
- 10 are later, from agents' manual `convmem index --file` on the old code while the
  watcher was off. That is a small burn outside the watcher.

Together they hold 11 prepared keys. The new code's source-scoped recovery reuses prepared
work instead of paying for it again. It runs the first time each source is indexed again,
which is expected inside canary 2. Promotion also stops new wedges: manual indexing now
takes the store-wide write lock.

## Procedure (on approval)

1. Recheck the preconditions:
   - `runtime-main` is clean and on `main` at `8a7cdab`, and fast-forwards to `3e705e4`;
   - watch, refine and monitor are inactive, and watch is disabled;
   - restic binding OK and today's snapshot current.
2. `systemctl --user stop convmem-reconcile.timer`, then wait until
   `convmem-reconcile.service` is inactive.
3. `git -C ~/Projects/convmem/.worktrees/runtime-main merge --ff-only 3e705e4`. Record the
   SHAs before and after.
4. `systemctl --user start convmem-reconcile.timer`. Confirm the next sweep logs
   `[reconcile] … findings=… queued=…` with no traceback.
5. `convmem doctor` through the wrapper (now `3e705e4`) exits 0, with only the known WARNs
   (11 stale transactions, chroma audit not installed).
6. Leave the watcher, refine and monitor stopped. Leave the MCP servers running.
7. Record before/after SHAs and doctor output in the Arc Codex STATUS log.

**Stop and roll back** if step 4 or 5 shows a traceback, a `write_guard` or `restic_gate`
FAIL, or a quarantine.

## What this does not grant

- The protocol-surface deploy and canary 2. Ryan granted both on 2026-10-16 as later
  steps. Canary 2 still needs a paid-call ceiling and duration; the proposal is 24 h and
  200 paid calls, Stage 2's original ceiling.
- Any T5 work, backup qualification, loss-window decision or corpus operation for Safe
  Harbor.
