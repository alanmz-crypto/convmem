# [Arc Codex #286] Next-model handoff: deploy the merged fence to the live watcher, then refresh the arc brief

**Date:** 2026-10-22
**Author:** Claude Code (Opus 5.5; independent review lane for the #286 fence)
**For:** a new model, in any lane. Read the stop rule before doing anything.
**Authorization:** Ryan, 2026-10-22, in chat: "I want you to continue only with implementation or review. If we need redesign, stop. Stop and create a handoff for a new model."

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` (Part A needs a runtime-promotion grant). Part B needs no gate. |
| **Branch** | `docs/2026-10-22-2026-10-22-arc-codex-post-fence-next-model` (this handoff only) |
| **Tip SHA** | see `git log -1 origin/docs/2026-10-22-2026-10-22-arc-codex-post-fence-next-model` |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | Part A: an explicit grant naming the target SHA for `.worktrees/runtime-main`, plus a watcher restart |
| **Track A ingest** | `~/.claude/projects/-home-lauer-Projects-convmem/5703fcf1-1d48-46b8-8321-620281cd5318.jsonl` (not yet indexed: `OPENAI_API_KEY` was unset) |

## Stop rule (Ryan, 2026-10-22)

Do only implementation, verification or review. If anything below turns out to need a **redesign**, stop. That includes a new lock order, a changed transform contract, a new gate, or a different deployment model. Write a handoff for a new model instead of improvising.

---

## What to build

No new code. Every #286 implementation and review lane is merged. Two pieces of work remain:

- **Part A (Ryan-gated deploy):** put the merged fence (#411) into the running watcher.
- **Part B (docs, no gate):** correct the Arc Codex brief, which no longer describes production.

**Why this exists:** the fence is merged on `main`, but production does not run it yet. As of 2026-10-22 (read-only checks):

| Fact | Value |
|---|---|
| `origin/main` | `1a68675` (#412) |
| `.worktrees/runtime-main` | branch `main` at `686d50e` (#409); it lacks #410, #411 and #412 |
| `convmem-watch.service` | `active (running)` |
| Live config `[index.incremental_jsonl]` | `enabled = true`, `live_sources = []`, `mutation_proof_observer = "shadow"`, `allow_full_rebuild = true` |
| Live config `[index.incremental_jsonl.codex_rollout_admission]` | root `~/.codex/sessions`, `admitted_after = "2026-10-12T04:04:00Z"`, `max_transform_chunks_per_run = 10` (lowered from 20 on 2026-10-20), `max_source_bytes = 268435456`. The config comment cites a Ryan grant of 2026-10-12. |

So Codex rollout incremental indexing is **live**. The window #411 closes is still open in production: the watcher's incremental commit can release the source lock before the processed row is published. A same-file manual, Track A or legacy run in that window can have its processed row deleted.

LATEST's line "no config/runtime activation" is true only of the #411 merge itself. It does not mean incremental indexing is off.

## Part A: promote `runtime-main` and restart the watcher (only after Ryan's grant)

### What the promotion carries

`git log 686d50e..origin/main`:

| PR | Commit | Contents |
|---|---|---|
| #410 | `a5405ad` | Crush doctor single-flight: `scripts/crush-hook-convmem-ritual-autorun.sh`, `scripts/deploy-agent-protocol.sh`, a manifest entry and a test |
| #411 | `6cacc1b` | The fence: `ingest.py`, `incremental_jsonl.py`, inventories and tests |
| #412 | `1a68675` | Docs only |

Promotion moves the checkout only. It does **not** run `deploy-agent-protocol.sh`, and that script clobbers hand-edited `CLAUDE.md`/`AGENTS.md`, so leave it alone.

### Checkpoint safety (verified by Claude, 2026-10-22)

#399's transform contract hashes semantic inputs: prompts and contract constants from `distill.py`, `llm.py` and `incremental_transform_contract.py`. It does not hash module files. `git diff --stat 686d50e origin/main` shows those three files and `incremental_checkpoint_migration.py` unchanged. The promotion therefore cannot change the contract digest, invalidate checkpoints, or trigger a paid rebuild. The #411 diff only widens lock scope; I reviewed it at `e6ce3c4` and re-verified it at `1916a15`.

### Steps (each read-only check first; stop on any surprise)

1. Get Ryan's grant, naming the target SHA (expected `1a68675`, or the current `origin/main` if newer; in that case re-list what the promotion carries and re-run the checkpoint-safety diff).
2. `git -C ~/Projects/convmem/.worktrees/runtime-main status --porcelain`. Expect empty output and branch `main`. If it is dirty or on another branch, stop and ask.
3. Prefer an idle window. Check `journalctl --user -u convmem-watch -n 80 --no-pager` for no in-progress incremental run. Crash recovery rolls forward, but do not test that on production.
4. `git -C ~/Projects/convmem/.worktrees/runtime-main fetch origin && git -C ~/Projects/convmem/.worktrees/runtime-main merge --ff-only <granted SHA>`
5. `systemctl --user restart convmem-watch.service`
6. Verify:
   - `rev-parse HEAD` equals the granted SHA;
   - `systemctl --user is-active convmem-watch.service` reports `active`;
   - the journal shows no traceback or refusal for 10 minutes;
   - `convmem doctor` exits 0.
7. Report the result to Ryan, then add one line to the STATUS Update Log and update the LATEST bullet.

## Part B: refresh `docs/plans/STATUS-codex-jsonl-production-integration.md`

Sections 3–6 still describe the arc as of about 2026-10-11. Verified drift (`gh pr view` / `git merge-base` on 2026-10-22):

| STATUS says | Reality |
|---|---|
| S0–S3 successor `19d34a5` "unmerged" | Integration merged as PR #307; #365 also merged |
| Test-isolation fix `eaae6e9`: "Ryan decides PR" (§5, §6 step 1) | Merged as PR #384 |
| "fix #308 (inter-model rejection loop)" (§6 Codex step 2) | #308 closed COMPLETED by PR #390 on 2026-10-12 |
| "land the exact-path recovery parity fix" (§6 Codex step 3) | Merged as PR #396 |
| Stage 1 grant "next"; the watcher "stopped and disabled 2026-10-05" (§3) | The watcher is running, and admission is live with `admitted_after = 2026-10-12T04:04:00Z` |
| (not mentioned) | Merged since then: #395 (Stage 2 wedge fixes), #399 (transform compatibility), #403 (manifest failure cache and refresh), #405 (scoped-proof shadow, off by default; live config sets `mutation_proof_observer = "shadow"`), #406 (opt-in Kiro incremental with a crash-safe paid-call budget) |
| 4G watch drop-in "to reconcile" | Resolved on 2026-10-12 per Claude memory (effective 8G). Verify with `systemctl --user show convmem-watch -p MemoryMax` before writing it into STATUS |

Rewrite §3–6 as a current-state snapshot (departure protocol), add one Update Log line, and keep §7 hard stops intact. Do **not** state Stage 1/Stage 2 grant outcomes, or the residual-burn decision for pre-activation rollouts, from inference. If the ledger (`convmem ask "Arc Codex Stage 2 canary result"`) and the repo don't settle them, list them as "Ryan to confirm".

---

## What NOT to build

- No production code, tests, scripts or config edits.
- No change to the live `config.toml`, to `live_sources`, or to the admission settings.
- No `deploy-agent-protocol.sh` run; no bootstrap, bulk index, or paid-provider calls.
- No merge, force-push or PR creation without Ryan asking.
- No crash tests on production (if a crash test is ever needed elsewhere, use SIGKILL and warn Ryan first).

## Test expectations

None new. Part A's verification is step 6. Part B is docs-only, so `git diff --check` must be clean and `tests/test_repository_knowledge_committed_manifest.py` must still pass. Classify any new docs file there the way #412 did (`2464bd1`).

## Acceptance criteria

- [ ] Part A: `runtime-main` HEAD equals the granted SHA, the watcher is active, the journal is clean for 10 minutes, and `convmem doctor` exits 0; Ryan was told.
- [ ] Part B: STATUS §3–6 match the drift table above, each claim has a PR or commit, and there is one Update Log line.
- [ ] LATEST top bullet updated; branch pushed with an explicit refspec.

## Branch convention

```
docs/YYYY-MM-DD-<slug>   (Part B; start with `convmem work start docs <slug> --worktree`)
```

Push immediately after each commit. Ryan squash-merges unless the PR says **Do not squash**.

## Related files

| What | Path |
|------|------|
| Arc brief (stale §3–6) | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Fence review and Luna fixes | `docs/inter-model/CODEX-LUNA-2026-10-21-issue-286-fence-ci-fixes-handoff.md` |
| Transform-compatibility review | `docs/inter-model/KIRO-2026-10-17-issue-286-transform-compatibility-review.md` |
| Stage 1 packet | `docs/inter-model/CLAUDE-2026-10-11-issue-286-codex-stage1-packet.md` |
| Transform contract | `incremental_transform_contract.py` |

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` bullet at top with link and resume state
- [x] `STATUS-*.md` Update Log line
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Read this file and the stop rule before the first action
- [ ] `convmem work resume <branch>` or start a fresh docs branch for Part B
- [ ] State Goal / role / system state / next action from the STATUS file

<!-- ref: ./CODEX-LUNA-2026-10-21-issue-286-fence-ci-fixes-handoff.md — fence review this follows -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc brief Part B corrects -->
