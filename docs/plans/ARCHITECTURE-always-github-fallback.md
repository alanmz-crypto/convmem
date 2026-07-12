# Architecture: Always-Available GitHub Fallback

| Field | Value |
|---|---|
| Status | **Executing** on `feat/2026-07-12-always-github-fallback` — see EXECUTION-always-github-fallback.md |
| Scope | `~/Projects/convmem` first; protocol pattern may later be adopted by other repositories |
| Owner | Ryan approves policy, GitHub settings (Pro required for private protection API), and any `main` emergency override |
| Objective | Every substantive repository edit reaches a recoverable GitHub-backed checkpoint without disturbing `main` or another agent's checkout |
| Gates | Defaults 2026-07-12: fail-closed push-before-edit; MVP local ownership; convmem-only; PR-only intent; local env ≠ authz |

## Problem

The Branching Safety Foundation improved multi-commit work, but it still permits
single-file documentation edits on `main` and relies on agents to remember when
to create and push a branch. A local uncommitted change, and even a local-only
commit, is not a durable fallback against machine loss or a bad checkout change.

The target state is not a branch per keystroke. It is a branch per coherent work
intent, created **before the first tracked-file edit**, with small commits pushed
to GitHub immediately. `main` becomes an integration and recovery reference, not
an agent workspace.

## Decision

Adopt a permanent, repository-wide-in-convmem policy:

1. Agents do not edit tracked files on `main`.
2. Every substantive task starts on a named branch before the first edit.
3. Each coherent checkpoint is committed, verified in proportion to risk, and
   pushed immediately.
4. A pushed branch is the source-code fallback. PRs preserve review context,
   milestone tags preserve explicitly known-good states, and operational data
   uses separate backups.
5. Agents never merge, force-push, or directly push to `main`. Ryan owns merges
   and any documented emergency exception.

## Non-goals

- GitFlow, release branches, or mandatory PRs for every typo.
- Treating Git as a backup for databases, uploads, secrets, generated runtime
  state, or third-party configuration.
- Creating a new branch for each individual commit when the commits belong to
  one coherent task.
- Rewriting shared history to undo a mistake. Use a follow-up commit or
  `git revert`.

## Fallback Layers

| Layer | Protects | Recovery mechanism | Does not protect |
|---|---|---|---|
| Task branch | `main` from in-progress work | discard or recreate branch | local disk loss before push |
| Local commit | a coherent checkpoint | `git revert <sha>` / reset local experiment | local disk loss before push |
| Pushed remote branch | repository-tracked code | clone/fetch branch from GitHub | uncommitted files, DB/runtime data |
| Pull request | review and comparison history | inspect/reopen PR and branch commits | deleted remote branch without retention |
| Annotated milestone tag | deliberate known-good release point | `git switch -c <branch> <tag>` | every intermediate experiment |
| DB/runtime backup | WordPress DB, uploads, secrets, service data | documented restore process | source-code history unless separately committed |

## Required Workflow

### Start work

1. Run the session checks required by `config/agent-protocol.md`.
2. Inspect the current branch and worktree state.
3. If the shared checkout has another writer's changes, do not switch it.
   Create or use a dedicated worktree.
4. From current `origin/main`, create a branch before editing:

```bash
git fetch origin
git switch -c fix/YYYY-MM-DD-short-slug origin/main
git push -u origin fix/YYYY-MM-DD-short-slug
```

The initial empty branch push is intentional: it establishes the remote recovery
location before substantive edits begin.

### Make checkpoints

```bash
git status --short
git add <intentional paths>
git commit -m "fix: concise checkpoint description"
<targeted verification>
git push
```

Split unrelated work into separate branches. Do not use `git commit --amend` to
replace a pushed checkpoint unless Ryan explicitly directs a coordinated history
rewrite; a new commit or `git revert` is the default recovery path.

### Handoff

```bash
git branch --show-current
git log origin/main..HEAD --oneline
git status --short
```

The handoff states the branch, pushed commit list, verification performed, and
whether a PR is ready for Ryan's review. It does not merge `main`.

## Branch Taxonomy

| Prefix | Purpose | Merge rule |
|---|---|---|
| `feat/YYYY-MM-DD-slug` | New capability | Ryan merges after review |
| `fix/YYYY-MM-DD-slug` | Bug fix | Ryan merges after verification |
| `docs/YYYY-MM-DD-slug` | Documentation work, including one-file changes | Ryan merges after coherence check |
| `plan/YYYY-MM-DD-slug` | Long-lived architecture or execution plan | Ryan accepts/merges |
| `wip/YYYY-MM-DD-slug` | Emergency preservation only | Never merge directly; rename to a reviewable prefix |

Remove the current exception permitting a single-file documentation typo on
`main`. The convenience is not worth a policy exception that undermines the
simple rule: edit only on a task branch.

## Concurrency and Worktrees

The existing single-active-writer rule remains safe until worktrees are
standardized. The intended end-state is one worktree per active writer:

```bash
git worktree add ~/.local/share/convmem/worktrees/fix-YYYY-MM-DD-slug \
  -b fix/YYYY-MM-DD-slug origin/main
```

The work-start helper must refuse to reuse a worktree or branch already declared
active by another agent. It must never switch a shared checkout beneath an
active writer. The helper may create and push the branch, but it must not merge.

## Enforcement Design

### Local enforcement

1. **Pre-commit:** reject commits on `main` by default. A Ryan-only emergency
   bypass must be explicit, auditable, and absent from normal agent instructions.
2. **Pre-push:** reject all direct pushes to `main` for agents, not only
   WIP-pattern subjects. Keep a narrow Ryan-controlled bypass if operationally
   required.
3. **Doctor:** report at least:
   - tracked modifications while on `main`;
   - commits on the current branch not present on its upstream;
   - hook installation and GitHub remote reachability;
   - direct commits on `main` as a clearly labelled heuristic or verified check.
4. **Work helper:** design `convmem work start <type> <slug>` to validate a safe
   starting state, fetch `origin/main`, create the correctly named branch or
   worktree, and establish its upstream before edits.

Hooks are guardrails, not the recovery mechanism. The pushed branch is the
recovery mechanism.

### GitHub enforcement (Ryan approval required)

Configure `main` with:

- pull-request-only changes;
- restricted direct pushes, limited to Ryan's emergency ownership if necessary;
- required verification checks selected after the checks are stable;
- blocked force-pushes;
- blocked deletion;
- retained merged-PR history and branch protection audited periodically.

GitHub configuration cannot be inferred solely from local hooks. Record the
approved settings and a verification command or screenshot reference in the
implementation plan.

## Recovery Runbook

| Situation | Default response |
|---|---|
| Bad pushed commit | `git revert <sha>`, verify, push the revert |
| Branch became confused | create a fresh branch/worktree from `origin/main`; selectively cherry-pick good commits |
| Local machine lost | clone/fetch the pushed branch from GitHub |
| Need known-good milestone | `git switch -c <branch> <annotated-tag>` |
| Work not ready to review | commit a small preservation checkpoint and push; use `wip/` only when needed |
| DB or runtime mutation failed | use its dedicated backup/restore process; Git history alone is insufficient |

## Migration

1. Update the canonical wording in `config/agent-protocol.md`.
2. Generate and deploy every per-surface protocol slice; do not hand-edit them
   into divergence.
3. Update `docs/plans/branching-strategy.md` to remove the `main` exception and
   document remote-before-edit behavior.
4. Update `docs/plans/git-hygiene-baseline.md` where recovery guidance depends
   on the new branch model.
5. Correct active Cursor plans that say `push only if Ryan asks`; replace with
   `push immediately after every commit`.
6. Add hooks and doctor checks with tests that demonstrate both rejection and
   the authorized emergency path.
7. Implement `convmem work start` only after the behavior and worktree
   ownership model are accepted.
8. Ryan configures GitHub branch protection and independently verifies it.

## Acceptance Criteria

- No agent task edits tracked files on `main`.
- Every substantive task has a named remote branch before its first edit.
- Every checkpoint commit is pushed before the agent starts unrelated work.
- Handoffs provide branch, upstream status, commits since `origin/main`, and
  verification evidence.
- A direct agent commit or push to `main` is rejected locally and blocked on
  GitHub.
- `doctor` detects missing hooks, dirty `main`, and unpushed task commits.
- A lost-checkout exercise recovers a branch from GitHub; a milestone recovery
  exercise starts correctly from an annotated tag.
- Separate operational-backup procedures remain mandatory for non-Git data.

## Review Questions for Ryan

1. Should the initial empty branch be pushed before edits, or is push-on-first-
   checkpoint adequate where network access is temporarily unavailable?
2. Which emergency bypass, if any, is allowed on `main`, and where is it
   documented and audited?
3. Which checks are mature enough to be GitHub-required at launch?
4. What branch-retention period should apply after merge for recovery and audit?
5. Should the policy be deployed globally to all agent-managed repositories now,
   or proven in convmem before adoption elsewhere?

## Source Material

- `config/agent-protocol.md`
- `docs/plans/branching-strategy.md`
- `docs/plans/git-hygiene-baseline.md`
- `scripts/git-hooks/`
- `scripts/install-repo-config.sh`
