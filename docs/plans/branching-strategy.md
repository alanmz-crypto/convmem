# Branching Strategy — convmem (Branching Safety Foundation)

| Field | Value |
|-------|-------|
| Plan ID | `branching_strategy_20260711` |
| Status | **active** — Foundation shipped on `feat/2026-07-11-branching-strategy` |
| Scope | `~/Projects/convmem` only (lab + willowyhollow-practice excluded) |
| Arc | **Branching Safety Foundation** (Option A) |
| Next arc | Automated Work Start (`convmem work *`) — gated on 2-week measurement |

Execution plan: [`EXECUTION-branching-safety-foundation.md`](EXECUTION-branching-safety-foundation.md)

---

## Problem

88 commits to `main` in 4 weeks; 3 branches ever (all `wip/`). Trunk-only multi-agent development. WIP on main, no pre-merge review surface, weak rollback.

---

## Design principles

- Lightweight — no GitFlow, no release branches
- Branch-per-intent (agents may share a branch)
- Main stay deployable (doctor + smoke)
- Ryan merges — agents never merge or force-push main
- **Single active writer** until worktrees exist

---

## Capability honesty

| Capability | Status |
|------------|--------|
| Models permitted to create branches | Defined |
| Models instructed when to branch | Protocol |
| WIP pushes to main | **Client-side blocked** (pre-push; `--no-verify` / `CONVMEM_SKIP_WIP_HOOK=1` bypass) |
| Direct feat:/fix: on main | Measured **heuristically** (doctor reflog) |
| Branch creation itself | Not automated (next arc) |
| Concurrent agent isolation | Not handled — single active writer |

---

## Branch taxonomy

| Prefix | Use case | Merge | Lifespan |
|--------|----------|-------|----------|
| `feat/<YYYY-MM-DD>-<slug>` | New capability | Review + Ryan merge | 1–5 days |
| `fix/<YYYY-MM-DD>-<slug>` | Bug fix | Test + verify | hours–2 days |
| `docs/<YYYY-MM-DD>-<slug>` | Multi-file docs | Coherence check | 1–3 days |
| `wip/<YYYY-MM-DD>-<slug>` | Preservation only | **Never merge** — rename to feat when ready | indefinite |
| `plan/<YYYY-MM-DD>-<slug>` | Long-lived plans | Ryan acceptance; monthly review | days–weeks |

Naming: `<prefix>/<YYYY-MM-DD>-<short-slug>`

**wip → feat:** `git branch -m wip/old-name feat/YYYY-MM-DD-topic` (rename, not checkout -b).

Single-file doc typos: OK on main (non-WIP subjects).

---

## Who may create / merge

| Agent | May create | Prefixes | May merge main |
|-------|------------|----------|----------------|
| Ryan | Yes | any | Yes |
| Cursor | Yes | feat, fix, docs, wip | No |
| Crush | Yes | fix, wip | No |
| Codex | Yes | fix, feat, docs | No |
| Kiro | Yes | **plan, docs only** | No — sign-off |
| ChatGPT / Claude Cloud | No | — | No |
| DeepSeek | No | — | No |

---

## Enforcement (two lines)

1. **Pre-push hook** (`scripts/git-hooks/pre-push`) — rejects WIP-pattern subjects (`^[Ww][Ii][Pp][:(! ]`) targeting `main`. Install: `bash scripts/install-git-hooks.sh`. Bypass (Ryan only): `CONVMEM_SKIP_WIP_HOOK=1`.
2. **Doctor** (advisory WARN, exit 0):
   - `hooks_path` — early; `core.hooksPath` + executable pre-push
   - `wip_on_main` — last 50 subjects on main
   - `direct_commits_on_main` — **heuristic** main reflog `commit:` + feat/fix; squash may flag; missing reflog = unable to measure

Shared helpers: [`git_hooks.py`](../../git_hooks.py)

---

## Agent workflow

```
Agent works → branch → push branch → notify Ryan in session chat
Ryan reviews → merges to main
```

After `convmem doctor` in convmem cwd: `git branch --show-current`. If on `main` and multi-commit work → create branch before first commit.

Handoff notification:

```bash
git branch --show-current
git log main..HEAD --oneline
```

```
Branch: feat/YYYY-MM-DD-slug
Ready for review. Commits since main:
  <output>
```

---

## Success criteria (2 weeks)

| Criterion | Kind | Signal |
|-----------|------|--------|
| Zero new WIP on main | Client-side enforced | hook + `wip_on_main` + `hooks_path` |
| Zero feat/fix while on main | Protocol-only | `direct_commits_on_main` (heuristic) |
| Kiro ≥2 branch reviews | Process | session chat |
| No force-push main | Process | git log |

If heuristic WARNs and Ryan confirms true direct commits (not squash noise) → pre-commit nudge and/or Automated Work Start.

---

## Closure — milestone tag (Ryan, after merge)

This arc is a **milestone** (subsystem operational), not a routine feat merge. After Ryan merges `feat/2026-07-11-branching-strategy` to `main`:

```bash
git tag -a v0.1.0-branching-foundation \
  -m "Branching Safety Foundation operational — WIP pre-push, doctor checks, protocol"
git push origin refs/tags/v0.1.0-branching-foundation
```

Recovery from the tag (do not leave detached HEAD; any branch name is fine):

```bash
git switch -c feat/from-branching-foundation v0.1.0-branching-foundation
```

Agents may **suggest** a tag name in handoff for milestone closures; **Ryan** creates and pushes tags. Do not tag every `feat/` merge — see follow-up [`git-hygiene-baseline.md`](git-hygiene-baseline.md).

---

## Deferred

- `convmem work start|status|handoff|finish|abandon`
- Worktrees under `~/.local/share/convmem/worktrees/`
- Merge trailers / `--no-ff` / server-side protection
- Pre-commit nudge hook
- Tag freshness doctor / full tagging tooling → [`git-hygiene-baseline.md`](git-hygiene-baseline.md)
- Git config hygiene (blame-ignore, pull.ff, rerere, gitattributes) → same follow-up
