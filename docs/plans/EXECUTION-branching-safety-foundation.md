# Execution Plan - Branching Safety Foundation

```
Planning Status

Phase:        Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Cursor
Authority:    Awaiting HITL
```

**Source:** Ryan — Option A locked; Claude pre-impl refinements; "go build it" after execution plan  
**Authority:** HITL-approved direction @ 2026-07-11 (architecture/adoption plan)  
**Direction plan:** [`~/.cursor/plans/branching_strategy_adoption_beedac5a.plan.md`](/home/lauer/.cursor/plans/branching_strategy_adoption_beedac5a.plan.md)  
**Goal:** Ship Branching Safety Foundation (protocol + roles + client-side WIP hook + three doctor WARNs) on dogfood branch `feat/2026-07-11-branching-strategy`.

### Branch reality (intake)

| Fact | Value |
|------|-------|
| Current branch | `main` |
| vs `origin/main` | **behind 5** — T1 branches from `origin/main` without updating local `main` |
| Dirty allowlist | `WILLOWYHOLLOW-BUG-TRIAGE-2026-07-06.md` (modified); `TODO-WH-PRACTICE-READINESS.md` (untracked) |
| Scope Guardian | Record allowlist before branch; leave dirty files alone; do not commit them on this branch |

---

## Execution Plan - Branching Safety Foundation

### Tasks

| ID | Deliverable | In scope | Depends on | Gates | Execution lane |
|----|-------------|----------|------------|-------|----------------|
| **T1** | Dogfood branch ready | `git fetch origin`; create `feat/2026-07-11-branching-strategy` directly from `origin/main` via `git switch --no-track -c feat/2026-07-11-branching-strategy origin/main` — do **not** update local `main` first; record the pre-existing dirty-file allowlist before branching | — | See T1 gates below | Cursor |
| **T2** | Docs + protocol surfaces | Update `docs/plans/branching-strategy.md` (active, Foundation); Tier A branching block + TEAM_CHARTER merge line in `config/agent-protocol.md`; AGENT-ROLES create/merge matrix; regenerate protocol examples via `generate-agent-protocol.sh` | T1 | Grep: branching block present in generated `config/cursor-rules-convmem.mdc.example`; no `work start` language | Cursor |
| **T3** | Hook + classification helpers | Repo-root `git_hooks.py` (`wip_commit_blocked`, `conventional_feat_fix_subject`); `scripts/git-hooks/pre-push`; `scripts/install-git-hooks.sh`; `tests/test_git_hooks.py` (unit + one integration) | T1 | `pytest tests/test_git_hooks.py -q`; WIP rejection demonstrated **only** via the temp-repo integration fixture (never against the real remote); real-repo check limited to `core.hooksPath` value + `scripts/git-hooks/pre-push` existence/executable bit | Cursor |
| **T4** | Doctor checks | `_check_hooks_path` (**early** in `run_doctor` order; verifies both `core.hooksPath` resolves correctly **and** `scripts/git-hooks/pre-push` exists + is executable), `_check_wip_on_main`, `_check_direct_commits_on_main` (primary signal: `main` reflog `commit:` actions matching feat/fix subject regex; returns `no main reflog; unable to measure` when reflog unavailable; WARN text says heuristic — squash merges create an ordinary `commit:` entry and may still be flagged; rebase-then-fast-forward should *not* be flagged since it reflogs as a fast-forward, not `commit:`); tests in `tests/test_doctor.py` | T3 | `pytest tests/test_doctor.py -q`; `convmem doctor` shows three checks; exit code still 0 on WARN | Cursor |
| **T5** | Cleanup + deploy + verify | Delete 3 stale `wip/` branches; run `deploy-agent-protocol.sh` + `install-git-hooks.sh`; session-chat handoff block | T2, T4 | Doctor `hooks_path` PASS after install; handoff lists branch + `git log main..HEAD --oneline` | Cursor |

**Serial order:** T1 → T2 ∥ T3 → T4 → T5 (T2 and T3 parallel-safe after T1; T4 needs T3; T5 needs T2+T4).

**Recommended execute order in one session:** T1, T3, T4, T2, T5 (code path first so tests gate docs).

### T1 gates (stop if dirty-file conflict)

```
git branch --show-current   # feat/2026-07-11-branching-strategy
git rev-parse HEAD           # equals origin/main
git rev-parse origin/main
git status --short           # only WILLOWYHOLLOW-BUG-TRIAGE-2026-07-06.md
                              # and TODO-WH-PRACTICE-READINESS.md
```

Stop if the switch would overwrite or conflict with either dirty file.

### Out of scope

- `convmem work start|status|handoff|finish|abandon`
- Worktrees / concurrent multi-writer isolation
- Merge trailers / `--no-ff` policy / server-side branch protection
- Pre-commit nudge hook
- Cleaning historical `5014b30 WIP:` from main history
- willowyhollow-practice or lab branching
- Committing unrelated dirty/untracked files listed above

### Implementation watch (known limitations — not blockers)

1. **`direct_commits_on_main` noise:** reflog `commit:` detection correctly excludes clean fast-forward merges (rebase-then-`--ff-only` reflogs as a fast-forward, not `commit:`) but still flags squash merges, which create an ordinary commit indistinguishable from a direct one. Reflog is local and eventually expires, and a rewritten or missing reflog will read as "unable to measure" rather than PASS. WARN/SKIP detail must say **heuristic**; at 2-week review, do not misread squash noise or an expired/missing reflog as "agents misbehaving" or "no problem."
2. **`hooks_path` order:** register `_check_hooks_path` **before** WIP/direct checks in `run_doctor()` so triage reads root-cause first.

### Evidence requirements (for Execute phase)

- `pytest tests/test_git_hooks.py tests/test_doctor.py -q` → PASS
- `convmem doctor` → exit 0; `hooks_path` / `wip_on_main` / `direct_commits_on_main` present
- Hook stderr matches plan text on WIP rejection, demonstrated via the temp-repo integration fixture
- Generated protocol surface contains branching block
- Handoff notification with `git branch --show-current` + commits since main
- No `convmem record` unless Ryan asks

### Stop points

- **HITL now:** approve this execution plan → enter [`EXECUTE-TASK.md`](../planning/EXECUTE-TASK.md) for T1…
- **HITL after T5:** Ryan reviews branch diff; optional Kiro `git diff main..feat/2026-07-11-branching-strategy`; Ryan merges (agents do not)

### Execute entry

- First task: **T1** after HITL approves this plan.
- Switch Cursor to **Agent mode** for Execute (Plan mode cannot write code).
- Dogfood: all T2–T5 commits land on `feat/2026-07-11-branching-strategy`.

### Single active writer

Until worktrees exist: only Cursor implements this arc in the primary checkout; do not run parallel Crush/Kiro/Codex writers in the same worktree.
