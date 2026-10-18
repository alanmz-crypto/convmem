# [Arc Codex #286] Codex handoff — free-provider coverage work (2026-10-18)

**Lane:** Codex (OpenAI Codex CLI, `gpt-5.6-luna`, reasoning effort **high**). **Author:** Claude.
**Audit afterwards (optional):** Astra (Codex audit lane). Not Sol-High: there is no reviewer conflict.

## Resume state

`NOT_STARTED`. Ryan authorized this handoff on 2026-10-18 by sending it to Codex. Parts A2 and A3 are
granted by that send. Part A1 (bootstrap) needs one more explicit Ryan "go" after Codex's dry-run
packet. Part B (other arcs' evaluations) is **not** granted here.

## Why now

DeepSeek (the paid summarize/distill provider) is temporarily free for Ryan. Work that was parked
**only** because it costs paid calls should run now and leave permanent index coverage. Embeddings are
local Ollama and always free. When billing resumes, all of this stops and the live flag in
"Live state" below must be reverted (Ryan or Claude does that, not Codex).

## Live state you are working beside (do not change it)

- `runtime-main` = `633f1d1`, used by the `convmem` wrapper (`~/.local/bin/convmem`). The watcher
  (`convmem-watch.service`) is running under Claude's canary guard (ceiling 3,000 paid calls).
- `main` is ahead (`#399`–`#401` merged, `#402` pending). It is **not deployed**. Don't deploy, and don't
  touch `.worktrees/runtime-main`.
- Live config has `allow_full_rebuild = true` under `[index.incremental_jsonl]`
  (`~/.config/convmem/config.toml`). Leave it; don't edit the config at all.
- Claude's overnight queue is indexing Claude/Copilot transcripts, one at a time:
  `scratchpad/backfill/bigfirst.sh` under `/tmp/claude-1000/-home-lauer-Projects-convmem/4199516e-e787-4f9f-b671-3f42ce73a4ce/`.
  Every commit takes the single global write lock (C1) for about 5 minutes, so your runs queue behind it.
  That's expected; don't kill other processes.

## What to build / do

### A2 — Index the sources the watcher deliberately skips (granted)

1. **Crush databases.** Find every `*/.crush/crush.db` under `/home/lauer` (about 48; the largest are
   `~/Projects/SubProjects/ButsabaJobScout/.crush/crush.db` 128.7 MB, `~/Projects/convmem/.crush/crush.db`
   100.8 MB, `…/ButsabaJobScout/Job_Lists/.crush/crush.db` 74.5 MB, `~/Projects/SubProjects/Mirror/.crush/crush.db`
   51.3 MB, `~/Projects/protean-environment/.crush/crush.db` 41.2 MB). Keep only files whose current
   SHA-256 is **not** a key in the processed log (`load_config()["index"]["processed_log"]`). Sort
   largest first.
2. **Kiro CLI database** `~/.local/share/kiro-cli/data.sqlite3` (78.8 MB, roughly 144 paid calls per
   full index). The watcher skips it because it changes constantly. Index it once, only while the Kiro
   CLI is **not** running (`pgrep -f kiro-cli` empty).
3. For each file, one at a time: skip it if modified in the last 30 minutes (retry deferred files once at
   the end), then `convmem index --file <path> --now`. Record path, exit code, seconds and size only.
   Never print or store transcript content.
4. Watch memory: stop the run if any `convmem` index process exceeds 4 GB RSS, or if `convmem doctor`
   reports a new FAIL. A 2026-10-12 incident leaked memory on live databases.

### A3 — Real-provider commit-time baseline for Gate A (granted; no new calls)

Today's runs already carry real provider latency. Build the "before slice 1" baseline from
`scratchpad/backfill/events.jsonl` and `rebuild-events.jsonl` (same folder as above; each line has
`ev.elapsed_seconds`, `ev.chunks_transformed`, `ev.outcome`). Report median, p95 and max seconds for
`committed` runs with `chunks_transformed == 1`, and the count. The commit-cost design
(`docs/plans/DESIGN-issue-286-commit-cost-reduction.md`, Gate A ≤ 60 s) needs this number.

### A1 — Bootstrap the 3 `bootstrap_required` Codex sessions (packet first, then Ryan "go")

These admitted-window rollouts were indexed on the legacy route before admission, so the incremental
route refuses them with `bootstrap_required`:

- `~/.codex/sessions/2026/10/13/rollout-2026-10-13T15-33-20-01a136f8-3c55-7c12-ad90-1d3c07f286a1.jsonl` (16.2 MB)
- `~/.codex/sessions/2026/10/14/rollout-2026-10-14T01-56-33-01a13932-d05c-7680-8cf8-d54f0f0e9dc0.jsonl` (7.1 MB)
- `~/.codex/sessions/2026/10/14/rollout-2026-10-14T01-58-25-01a13934-85b6-7360-9e3a-b14928d462c8.jsonl` (13.7 MB)

Adapt your Stage 1 packet (`docs/inter-model/CLAUDE-2026-10-11-issue-286-codex-stage1-packet.md`) into an
exact-source dry-run packet for these three on runtime `633f1d1`: the bootstrap entrypoint and its
existing paid cap, the expected chunk count and calls per source, backups, preconditions (no pending
transaction or rollback, not live, watcher interaction), and rollback limits. Run only read-only checks.
Hand the packet to Ryan. Execute only after Ryan replies "go A1".

## Integration point

- CLI: `convmem index --file <path> --now` (the `--now` flag bypasses the defer-to-watcher rule).
- Processed log: `config.load_config()["index"]["processed_log"]`, keyed by file SHA-256.
- Bootstrap: the existing-source bootstrap merged in PR #377 (`d1c28f9`) and its Stage 1 packet.

## What NOT to do

- No deploy, no `runtime-main` change, no config edit, no watcher stop or restart.
- No `convmem watch --clear-quarantine`, no exclusion changes, no deleting or moving source files.
- No indexing of files modified in the last 30 minutes, and none of Claude's live session
  `~/.claude/projects/-home-lauer-Projects-convmem/4199516e-e787-4f9f-b671-3f42ce73a4ce.jsonl`.
- No code changes and no PRs. Part B (JudgeBench, golden-eval #320, naturalistic G6) belongs to other
  arcs and needs Ryan's separate authorization.

## Test expectations / evidence

Per part: a table of path → rc → seconds → MB (A2), the latency statistics (A3), the packet (A1). Before
and after A2: `convmem doctor` exit code and its WARN/FAIL lines.

## Acceptance criteria

- A2: every stale Crush DB and the Kiro CLI DB is indexed or explicitly skipped with a reason, with no
  doctor FAIL introduced and no process over 4 GB.
- A3: baseline numbers with sample count.
- A1: packet delivered; execution only after "go A1".

## Branch convention

Report in chat. If you write the A1 packet or the A3 baseline to the repo, use a new branch from
`origin/main` (`docs/2026-10-18-issue-286-free-window-coverage`), push with an explicit refspec, no PR.

## Ryan GATE

A2 and A3 are granted by sending this handoff. A1 execution needs "go A1". Part B is not granted.
