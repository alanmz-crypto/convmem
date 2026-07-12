# Branching Strategy — convmem

| Field | Value |
|-------|-------|
| Plan ID | `branching_strategy_20260711` (Foundation) → superseded in part by Always-GitHub-Fallback |
| Status | **active** — Foundation shipped; **Always-Available GitHub Fallback** is current policy |
| Scope | `~/Projects/convmem` only |
| Current arc | [`ARCHITECTURE-always-github-fallback.md`](ARCHITECTURE-always-github-fallback.md) / [`EXECUTION-always-github-fallback.md`](EXECUTION-always-github-fallback.md) |
| Prior arc | Branching Safety Foundation (Option A) — WIP hook baseline |

Foundation execution: [`EXECUTION-branching-safety-foundation.md`](EXECUTION-branching-safety-foundation.md)

---

## Problem

88 commits to `main` in 4 weeks; 3 branches ever (all `wip/`). Trunk-only multi-agent development. WIP on main, no pre-merge review surface, weak rollback. Foundation fixed WIP-on-main; Always-GitHub-Fallback removes the remaining typo-on-main exception and requires a **pushed** task branch before any tracked edit.

---

## Design principles

- Lightweight — no GitFlow, no release branches
- Branch-per-intent **before first tracked edit**
- Main stay deployable (doctor + smoke)
- Ryan merges — agents never merge or force-push main
- **Pushed remote branch** is the source-code fallback
- Worktrees for concurrent writers (`convmem work … --worktree`)

---

## Capability honesty

| Capability | Status |
|------------|--------|
| Models permitted to create branches | Defined |
| Branch before edit | Protocol + `convmem work start` |
| Any push to main | **Client-side blocked** (pre-push); GitHub Pro required for server protection |
| Commit on main | **Client-side blocked** (pre-commit) |
| Local bypass env | Hook skip + audit only — **not** authz (`CONVMEM_SKIP_MAIN_HOOK`) |
| Concurrent agent isolation | Worktrees + MVP local conflict detect |

---

## Branch taxonomy

| Prefix | Use case | Merge | Lifespan |
|--------|----------|-------|----------|
| `feat/<YYYY-MM-DD>-<slug>` | New capability | Review + Ryan merge | 1–5 days |
| `fix/<YYYY-MM-DD>-<slug>` | Bug fix | Test + verify | hours–2 days |
| `docs/<YYYY-MM-DD>-<slug>` | Docs **including one-file changes** | Coherence check | 1–3 days |
| `wip/<YYYY-MM-DD>-<slug>` | Preservation only | **Never merge** — rename to feat when ready | indefinite |
| `plan/<YYYY-MM-DD>-<slug>` | Long-lived plans | Ryan acceptance; monthly review | days–weeks |

Naming: `<prefix>/<YYYY-MM-DD>-<short-slug>`

**wip → feat:** `git branch -m wip/old-name feat/YYYY-MM-DD-topic` (rename, not checkout -b).

**No edits on `main`** — including single-file doc typos (exception removed).

---

## Who may create / merge

| Agent | May create | Prefixes | May merge main |
|-------|------------|----------|----------------|
| Ryan | Yes | any | Yes |
| Cursor | Yes | feat, fix, docs, wip, plan | No |
| Crush | Yes | fix, wip | No |
| Codex | Yes | fix, feat, docs | No |
| Kiro | Yes | **plan, docs only** | No — sign-off |
| ChatGPT / Claude Cloud | No | — | No |
| DeepSeek | No | — | No |

---

## Enforcement

1. **Pre-commit** — rejects commits when HEAD is `main`/`master`. Bypass env: `CONVMEM_SKIP_MAIN_HOOK=1` (hook skip only; never in agent protocol).
2. **Pre-push** — rejects **any** push targeting `main`/`master` (not only WIP subjects). Same bypass env (legacy `CONVMEM_SKIP_WIP_HOOK` still honored as alias).
3. **Doctor** (advisory WARN, exit 0): `hooks_path`, `wip_on_main`, `dirty_main`, `unpushed_commits`. Historical `direct_commits_on_main` heuristic **retired**.
4. **`convmem work start|resume`** — taxonomy-first, explicit refspec push, fail closed on fetch/push errors.

Install: `bash scripts/install-repo-config.sh` (or `install-git-hooks.sh` wrapper).

Shared helpers: [`git_hooks.py`](../../git_hooks.py), [`work_git.py`](../../work_git.py)

**GitHub:** Branch protection / rulesets need GitHub Pro on this private repo (API 403 as of 2026-07-12). Until Ryan enables Pro (or equivalent), do **not** claim server-side `main` protection — local hooks only. Intent: PR-only / no agent bypass actor.

---

## Agent workflow

```
convmem work start feat slug   # or work resume …
edit → commit → push immediately (explicit refspec) → notify Ryan
Ryan reviews → PR merge to main
```

**The remote branch IS the backup.** Commit often, push every commit. Unpushed work is unrecoverable.

```bash
convmem work start feat short-slug
# or resume:
convmem work resume feat/YYYY-MM-DD-short-slug
```

Handoff:

```bash
git branch --show-current
git log origin/main..HEAD --oneline
git status -sb
```

---

## Success criteria

| Criterion | Kind | Signal |
|-----------|------|--------|
| Zero agent commits/pushes to main | Client-side | pre-commit + pre-push |
| Remote branch before first edit | Process + helper | `work start` / explicit push |
| Dirty main / unpushed | Doctor WARN | `dirty_main`, `unpushed_commits` |
| GitHub protects main | Ryan / Pro | `gh api …/protection` when available |

---

## Closure — Foundation milestone (historical)

Foundation tag: `v0.1.0-branching-foundation` (exists). Recovery: `git switch -c <branch> v0.1.0-branching-foundation`.

See also: [`git-hygiene-baseline.md`](git-hygiene-baseline.md) recovery kit.
