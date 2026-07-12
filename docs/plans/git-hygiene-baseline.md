# Git Hygiene Baseline

```
Planning Status

Phase:        Execute (agent T1–T5)
Characters:   Cursor (writer)
Lanes:        Cursor → Kiro (T5b) → Ryan (T7)
Authority:    HITL + T0 satisfied 2026-07-11
```

| Field | Value |
|-------|-------|
| Plan ID | `git_hygiene_baseline_20260711` |
| Status | **active** — executing on `feat/2026-07-11-git-hygiene-baseline` |
| Depends on | Branching Safety Foundation on `origin/main` (`6d8980a`); tag `v0.1.0-branching-foundation` (T6 done) |
| Scope | `~/Projects/convmem` only |
| Execution plan | [`EXECUTION-git-hygiene-baseline.md`](EXECUTION-git-hygiene-baseline.md) |
| Direction plan | `~/.cursor/plans/git_hygiene_baseline_d048ae33.plan.md` |

---

## Problem

Branching Safety Foundation ships agent-facing git *behavior*. Separately, the repo lacked baseline *hygiene*: no milestone tags, no repo-local pull/rerere/blame preferences, no markdown diff driver. This arc closes that gap — repository-local only.

---

## Principles

- Tags mark **milestone closures**, not every `feat/` merge
- Prefer **repo-local** git config over `--global`
- Ambiguity stops execution (`pull.ff only`) rather than silent rebase/merge
- Agents may stash **own** work; must **not** stash Ryan’s unrelated dirty files without execution-plan authorization
- No blanket `*.jsonl merge=union`
- No new doctor checks in this arc (`_check_tag_freshness` deferred)

---

## Deliverables

| # | Item | How |
|---|------|-----|
| 1 | Milestone tag | Ryan: `v0.1.0-branching-foundation` (done async as T6) |
| 2 | `.git-blame-ignore-revs` | Header-only until eligible mechanical SHAs exist; `blame.ignoreRevsFile` via installer |
| 3 | Unified installer | `scripts/install-repo-config.sh`; `install-git-hooks.sh` thin `exec` wrapper |
| 4 | `pull.ff only` | Repo-local; protocol: fetch + rebase / `pull --ff-only` |
| 5 | `rerere.enabled` | Repo-local; review with `git rerere diff` |
| 6 | `.gitattributes` | `*.md diff=markdown` only |
| 7 | JSONL union | Declined for fixtures/examples (see inventory) |
| 8 | Protocol notes | Tag propose, pull.ff/rebase, rerere diff, stash auth, clone install one-liner |

---

## Blame-ignore audit (2026-07-11)

Eligibility: commits that pollute **logic** blame — typically >5 `*.py` with trivial/mechanical diffs. Config-only (`.pylintrc`, workflow) omitted.

### Wide `*.py` touch sets (`git log` on `origin/main`)

| SHA | Subject | `*.py` count | Include? | Why |
|-----|---------|--------------|----------|-----|
| `5014b30` | WIP: preserve progress on Bug 5… | 13 | No | Behavioral WIP |
| `3bad9ab` | feat: HITL team charter… | 7 | No | Feature |
| `9fdd115` | feat: retrieval hardening… | 20 | No | Feature |
| `7d51e0d` | Ship global agent protocol… | 13 | No | Feature |
| `6cfa5bb` | P1a/P1b: unresolved CLI… | 7 | No | Feature |
| `9b6add2` | Coordination protocol… | 6 | No | Feature |
| `036de85` | Watch OOM fixes… | 8 | No | Feature |
| `0c8ed9b` | Fix re-index duplication… | 6 | No | Bugfix |

### Pylint / config candidates (Crush list)

| SHA | Files | Include? | Why |
|-----|-------|----------|-----|
| `25e16f0` | `.github/workflows/pylint.yml` | No | Workflow-only; no logic-blame pollution |
| `5da5aaa` | `.pylintrc` | No | Config-only |
| `d6511f8` | `.pylintrc` | No | Config-only |
| `6d50da8` | `.pylintrc` | No | Config-only |
| `60bda66` | `.pylintrc` | No | Config-only |

**Outcome:** header-only `.git-blame-ignore-revs` (no SHAs). Add full SHAs when a true mass-reformat lands.

---

## JSONL inventory (union declined)

Tracked JSONL today is fixtures/examples only (`tests/fixtures/golden_*.jsonl`, `examples/*.jsonl`, `docs/chatgpt-pack/examples/*.jsonl`). None are append-only production ledgers in-repo. **No** path-specific `merge=union` in this arc.

---

## Install / clone

After clone (or to refresh local hygiene):

```bash
bash scripts/install-repo-config.sh
```

Sets (all `--local`): `core.hooksPath`, `pull.ff=only`, `rerere.enabled=true`, `blame.ignoreRevsFile=.git-blame-ignore-revs`.

`scripts/install-git-hooks.sh` is a thin wrapper that `exec`s the unified installer (legacy name preserved).

**`pull.ff=only` failure:** histories diverged — do not force a merge pull. Recover with `git fetch origin` then either `git rebase origin/main` (feature branch) or investigate before `git pull --ff-only` on a clean `main`.

---

## Tagging (sparse milestones)

1. Agent proposes `vX.Y.Z-<slug>` or `milestone/<slug>` at milestone handoff  
2. Ryan creates annotated tag + pushes  
3. Work from tag: `git switch -c <branch> <tag>` (no fixed `recovery/` prefix)

Foundation tag: `v0.1.0-branching-foundation` (exists).

---

## Out of scope

| Item | Why |
|------|-----|
| Global `pull.rebase` / any `--global` hygiene | Cross-repo blast radius |
| `_check_tag_freshness` / hygiene doctor | Deferred |
| Tag-every-feat | Too broad |
| Agent-default stash of Ryan’s files | Hides dirty allowlist work |
| `*.jsonl merge=union` | Duplicate / contradiction risk |
| Automated Work Start / worktrees | Separate arcs |

---

## Success criteria

- Installer configs live after `install-repo-config.sh` / wrapper regression
- Blame policy applied (header-only or SHAs)
- Protocol deployed; no `work start`; no global hygiene keys; no JSONL union
- T5b Kiro sign-off dated below → Ryan merge (T7)

**Kiro reviewed:** 2026-07-11

---

## Related

- Branching Foundation: [`branching-strategy.md`](branching-strategy.md)
- Verify Foundation: [`VERIFY-branching-safety-foundation.md`](VERIFY-branching-safety-foundation.md)
- Verify this arc (T5b): [`VERIFY-git-hygiene-baseline.md`](VERIFY-git-hygiene-baseline.md)
- Execution: [`EXECUTION-git-hygiene-baseline.md`](EXECUTION-git-hygiene-baseline.md)
