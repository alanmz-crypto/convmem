# Git Hygiene Baseline — follow-up arc (draft)

| Field | Value |
|-------|-------|
| Plan ID | `git_hygiene_baseline_20260711` |
| Status | **draft** — start after Branching Safety Foundation merges |
| Depends on | `feat/2026-07-11-branching-strategy` merged + optional tag `v0.2.0-branching-foundation` |
| Scope | `~/Projects/convmem` only |

**Not part of Branching Safety Foundation.** That arc stays bounded (protocol + roles + WIP hook + three doctor checks). This plan is the coherent follow-up Claude recommended.

---

## Problem

Branching Safety Foundation ships agent-facing git *behavior*. Separately, the repo lacks baseline *hygiene*: no milestone tags, blame polluted by pylint formatting commits, no repo-local pull/rerere preferences, no markdown diff driver. Crush proposed a global tooling dump; Claude narrowed it — adopt carefully, repository-local, no expansion of the live branching arc.

---

## Principles (from Claude review)

- Tags mark **milestone closures**, not every `feat/` merge
- Prefer **repo-local** git config over `--global` (WordPress / other clones must not inherit convmem defaults)
- Ambiguity stops execution (`pull.ff only`) rather than silent rebase/merge
- Agents must **not** stash Ryan’s unrelated work without explicit plan authority
- `merge=union` only on path-proven append-only files — never `*.jsonl` globally
- Doctor/protocol tooling only where agents make recurring decisions; one-time config stays install-script / commit-and-forget

---

## In scope

| # | Item | How |
|---|------|-----|
| 1 | First annotated milestone tag | Ryan: `v0.2.0-branching-foundation` after Foundation merge (see branching-strategy closure) |
| 2 | `.git-blame-ignore-revs` | Audit pylint/format SHAs as behavior-neutral; add file; `git config --local blame.ignoreRevsFile .git-blame-ignore-revs` via install script |
| 3 | Install/bootstrap | Document + set local blame ignore (and other local configs below) in existing install path (`scripts/install-git-hooks.sh` or sibling) |
| 4 | `pull.ff only` | **Repo-local only** — `git config --local pull.ff only`. Protocol: `git fetch` + explicit `rebase` / `pull --ff-only` |
| 5 | `rerere.enabled` | **Repo-local** — `git config --local rerere.enabled true`. Protocol note: reused resolutions must be reviewed in final diff |
| 6 | `.gitattributes` | `*.md diff=markdown` only in this pass |
| 7 | JSONL merge drivers | Investigate individual files; path-specific `merge=union` only if append-only + duplicate-tolerant + validated |
| 8 | Stash policy | Document: agents do **not** stash unrelated user work without explicit authorization; prefer allowlist / preservation branch / worktree |

## Out of scope

| Item | Why |
|------|-----|
| Global `pull.rebase=true` | Changes every repo on the machine — rejected |
| `_check_tag_freshness()` doctor | Premature; “N commits since tag” is arbitrary — revisit after 2–3 arcs if tags are forgotten |
| Tag-every-feat protocol rule | Too broad — milestones only |
| Agent-default stash discipline | Hides Ryan’s work; allowlist stays for branching-style arcs |
| Global `*.jsonl merge=union` | Duplicates / contradictory records risk |
| Worktrees / commit signing / aliases | Deferred (worktrees when concurrent writers; signing N/A) |
| Automated Work Start (`convmem work *`) | Separate arc, gated on branching 2-week data |

---

## Tagging discipline (lightweight — two layers only)

1. **Handoff:** on milestone closure, agent suggests `vX.Y.Z-<slug>` in session chat  
2. **Ryan:** creates annotated tag + pushes  

```bash
git tag -a v0.2.0-branching-foundation -m "…"
git push origin refs/tags/v0.2.0-branching-foundation
```

Recovery:

```bash
git switch -c recovery/<slug> v0.2.0-branching-foundation
```

**Do not** add doctor tag-freshness until evidence shows tags are being skipped.

---

## Blame-ignore audit gate

Before listing any SHA in `.git-blame-ignore-revs`:

```bash
git show --stat <sha>
git show <sha> -- '*.py' | head   # spot-check: formatting/config only
```

If any commit mixes behavior change with formatting → **omit** that SHA (or split history later — do not ignore).

Candidate range from Crush (verify each): `25e16f0` … `60bda66` pylint/config scaffolding on recent main.

---

## Protocol / install touchpoints (this arc only)

| Change | File |
|--------|------|
| Suggest milestone tags at handoff; Ryan tags | Short note in `config/agent-protocol.md` Tier A / handoff — **no** every-feat rule |
| `pull.ff only` + fetch/rebase wording | Protocol one-liner + install script |
| rerere review note | Protocol one-liner |
| No agent stash without authority | Protocol one-liner |
| Local git config | `scripts/install-git-hooks.sh` or `scripts/install-git-hygiene.sh` |

No new doctor checks in v1 of this arc.

---

## Suggested tasks (execution planning later)

| ID | Deliverable |
|----|-------------|
| H1 | Annotated tag `v0.2.0-branching-foundation` (Ryan, post-merge) |
| H2 | Audit + commit `.git-blame-ignore-revs` |
| H3 | `.gitattributes` with `*.md diff=markdown` |
| H4 | Install script sets local `blame.ignoreRevsFile`, `pull.ff only`, `rerere.enabled` |
| H5 | Protocol notes (tag suggest / pull.ff / rerere review / no unauthorized stash) |
| H6 | JSONL inventory note — candidates for path-specific union or “none” |

---

## Success criteria

- One annotated milestone tag exists for Branching Foundation  
- `git blame` on pylint-touched files skips ignored revs after local config  
- Accidental `git pull` on diverged main fails closed (`pull.ff only`) instead of merge commit  
- No global git config changes from this arc  
- No `*.jsonl merge=union` unless a specific path is proven  

---

## Related

- Branching Foundation: [`branching-strategy.md`](branching-strategy.md)  
- Verify: [`VERIFY-branching-safety-foundation.md`](VERIFY-branching-safety-foundation.md)  
- Next after hygiene + 2-week branching data: Automated Work Start
