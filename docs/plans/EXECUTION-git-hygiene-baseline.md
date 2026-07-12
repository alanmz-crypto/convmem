# Execution Plan - Git Hygiene Baseline

```
Planning Status

Phase:        Execute (T1–T5 in progress)
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner → Cursor writer
Lanes:        Cursor
Authority:    HITL + T0 satisfied 2026-07-11 (main 2957e0b; tag v0.1.0-branching-foundation)
```

**Source:** Claude resolved guide + DeepSeek reviews; direction plan  
**Direction plan:** [`~/.cursor/plans/git_hygiene_baseline_d048ae33.plan.md`](/home/lauer/.cursor/plans/git_hygiene_baseline_d048ae33.plan.md)  
**Repo SSoT on execute:** rewrite [`docs/plans/git-hygiene-baseline.md`](git-hygiene-baseline.md) to match this execution plan (replace earlier draft)  
**Goal:** Ship repo-local git hygiene (unified installer, markdown diffs, protocol notes, blame eligibility) after Branching Safety Foundation is on `main`.

### Branch reality (execute 2026-07-11)

| Fact | Value |
|------|-------|
| Hygiene branch | `feat/2026-07-11-git-hygiene-baseline` (from `origin/main` @ `2957e0b`) |
| Dirty allowlist (leave uncommitted) | `WILLOWYHOLLOW-BUG-TRIAGE-2026-07-06.md` (M); `TODO-WH-PRACTICE-READINESS.md` (??); `docs/plans/s2_hotfix_reconcile.md` (??) |
| Foundation on `origin/main` | **YES** — `git merge-base --is-ancestor 6d8980a origin/main` exit 0; tag `v0.1.0-branching-foundation` |
| Scope Guardian | Do not commit allowlisted WH/s2 dirty files on hygiene branch |

### Hard gate

**Do not start T1–T5 until** Branching Safety Foundation is merged to `origin/main` (verify: `git merge-base --is-ancestor 6d8980a origin/main`).

Ryan merge of Foundation is a **stop point**, not part of this arc’s agent work.

---

## Execution Plan - Git Hygiene Baseline

### Tasks

| ID | Deliverable | In scope | Depends on | Gates | Lane |
|----|-------------|----------|------------|-------|------|
| **T0** | Foundation on main | Ryan merges `feat/2026-07-11-branching-strategy`; agent confirms ancestor check | — | `git merge-base --is-ancestor 6d8980a origin/main` exit 0 | Ryan → Cursor confirm |
| **T1** | Dogfood branch | `git fetch origin`; create `feat/<YYYY-MM-DD>-git-hygiene-baseline` from `origin/main` using **date of creation** (not this plan’s draft date — if T0 lands after 2026-07-11, use that day’s date); `git switch --no-track -c feat/<date>-git-hygiene-baseline origin/main`; record dirty allowlist | T0 | HEAD == `origin/main`; status only allowlisted dirt | Cursor |
| **T2** | Blame-ignore + attrs + plan SSoT | Bounded scan; `.git-blame-ignore-revs`; `.gitattributes` (`*.md diff=markdown`); rewrite `docs/plans/git-hygiene-baseline.md`; fix `branching-strategy.md` closure `v0.2.0` → `v0.1.0` | T1 | See T2 gates | Cursor |
| **T3** | Unified installer | `scripts/install-repo-config.sh` (hooksPath + pull.ff + rerere + blame); `install-git-hooks.sh` → thin `exec` wrapper; status echo of four keys; pull.ff failure comment in script | **T2** (needs `.git-blame-ignore-revs` to exist) | See T3 gates | Cursor |
| **T4** | Protocol + deploy | Tier A notes (tag propose, pull.ff/rebase, `git rerere diff`, stash auth); generate + deploy; **no work start** language | T3 | See T4 gates | Cursor |
| **T5** | Agent verify (H7) | Installer status; configs; wrapper regression (unset-then-reinstall); global drift; protocol negatives | T4 | See T5 gates — **no tag required** | Cursor |
| **T5b** | Independent review | Push branch; Kiro reviews `git diff origin/main...HEAD`; sign-off recorded as one line in session handoff **and** append to plan SSoT status (e.g. `Kiro reviewed: YYYY-MM-DD` in `docs/plans/git-hygiene-baseline.md`) | T5 | Handoff + plan file both note Kiro date | Kiro |
| **T6** | Ryan tag (H1 / H1′) | Annotated `v0.1.0-branching-foundation`; push tag | T0 (parallel to T1–T5) | `git rev-parse v0.1.0-branching-foundation` — **async, not in T5 PASS** | Ryan |
| **T7** | Ryan merge | Merge hygiene branch after T5b | T5b | Ryan `--ff-only` or `--squash` | Ryan |

**Required agent order (serial):** T0 → T1 → **T2 → T3** → T4 → T5  

T3 depends on T2 because `blame.ignoreRevsFile` must point at an existing `.git-blame-ignore-revs` (header-only is fine). Do **not** run T3 before T2.

**Parallel:** T6 (Ryan tag) anytime after T0; does not block T5 / T5b / T7.

### T2 gates (blame + attrs)

```bash
# Bounded scan — flag commits touching >5 *.py with trivial diffs.
# Manual scan is acceptable at current repo size (~94 commits; few touch many .py files).
# Eyeball `git log --stat` for wide *.py touch sets; do not invent filler SHAs.
git log --stat --diff-filter=M -- '*.py' origin/main

# Eligibility: logic-file pollution only; .pylintrc / workflow-only → omit
# If zero eligible: header-only .git-blame-ignore-revs with:
#   "No mass-reformat SHAs as of YYYY-MM-DD. Add SHAs here when mechanical
#    refactors occur. Config-only commits (e.g. .pylintrc) are intentionally omitted."

test -f .gitattributes && grep -F '*.md diff=markdown' .gitattributes

# Locate and fix phantom version in closure section:
grep -n 'v0\.2' docs/plans/branching-strategy.md
# Edit those lines → v0.1.0-branching-foundation, then:
grep -F 'v0.1.0-branching-foundation' docs/plans/branching-strategy.md

# No JSONL union anywhere in attributes:
grep -qF 'merge=union' .gitattributes 2>/dev/null && { echo "FAIL: union found"; exit 1; } || true
```

Audit table (SHA / files / include? / why) recorded in rewritten `docs/plans/git-hygiene-baseline.md`.

### T3 gates (installer + wrapper proof)

```bash
bash scripts/install-repo-config.sh
# Must print:
#   core.hooksPath = ...
#   pull.ff = only
#   rerere.enabled = true
#   blame.ignoreRevsFile = .git-blame-ignore-revs

# Wrapper must invoke the FULL installer (not hooksPath-only no-op):
git config --local --unset-all core.hooksPath || true
git config --local --unset-all pull.ff || true
git config --local --unset-all rerere.enabled || true
git config --local --unset-all blame.ignoreRevsFile || true
# Confirm all four unset:
for k in core.hooksPath pull.ff rerere.enabled blame.ignoreRevsFile; do
  git config --get "$k" && { echo "FAIL: $k still set"; exit 1; } || true
done
bash scripts/install-git-hooks.sh   # must restore all four via exec → install-repo-config.sh
test "$(git config --get core.hooksPath)" = "scripts/git-hooks"
test "$(git config --get pull.ff)" = "only"
test "$(git config --get rerere.enabled)" = "true"
test "$(git config --get blame.ignoreRevsFile)" = ".git-blame-ignore-revs"
test -x scripts/git-hooks/pre-push
# Optional: head -5 scripts/install-git-hooks.sh | grep -q install-repo-config
```

Script must contain comment explaining `pull.ff=only` non-ff failure + recovery commands. Never `git config --global`.

### T4 protocol content + gates

**Locked wording:**

1. Milestone: propose `vX.Y.Z-<slug>` or `milestone/<slug>`; Ryan tags; work from tag via `git switch -c <branch> <tag>` (no fixed `recovery/` prefix)
2. Feature branch: `git fetch origin && git rebase origin/main`; clean main: `git pull --ff-only`; if plain `git pull` fails under `pull.ff only`, histories diverged — stop
3. Rerere: review with **`git rerere diff`** (textual reuse ≠ semantic correctness)
4. Stash: may stash **own** uncommitted work to unblock branch switch; must **not** stash Ryan’s unrelated dirty files without execution-plan authorization (`git stash push -u -m "<reason>" -- <paths>` + handoff note if authorized)
5. **After cloning convmem:** run `bash scripts/install-repo-config.sh` (covers hooksPath + pull.ff + rerere + blame-ignore — closes fresh-clone gap for new machines / re-clones)

**Negative gate (direction plan):**

```bash
rg -n "work start" config/agent-protocol.md && echo "FAIL: work start present" || echo "no work start OK"
rg -nF 'install-repo-config.sh' config/agent-protocol.md || echo "WARN: clone install one-liner missing"
```

Then `generate-agent-protocol.sh` + `deploy-agent-protocol.sh`.

### T5 gates (agent verify — tag excluded)

```bash
bash scripts/install-repo-config.sh
git config --get pull.ff                    # only
git config --get rerere.enabled             # true
git config --get blame.ignoreRevsFile       # .git-blame-ignore-revs
git config --get core.hooksPath             # scripts/git-hooks

# Wrapper regression — unset all four, then wrapper-only restore
git config --local --unset-all core.hooksPath || true
git config --local --unset-all pull.ff || true
git config --local --unset-all rerere.enabled || true
git config --local --unset-all blame.ignoreRevsFile || true
bash scripts/install-git-hooks.sh
test "$(git config --get core.hooksPath)" = "scripts/git-hooks"
test "$(git config --get pull.ff)" = "only"
test "$(git config --get rerere.enabled)" = "true"
test "$(git config --get blame.ignoreRevsFile)" = ".git-blame-ignore-revs"
python -m pytest tests/test_doctor.py tests/test_git_hooks.py -q

rg -nF 'git rerere diff' config/agent-protocol.md config/cursor-rules-convmem.mdc.example
rg -n 'pull.ff|pull --ff-only' config/agent-protocol.md
rg -n "work start" config/agent-protocol.md && echo "FAIL" || echo "no work start OK"

# Global drift: no hygiene keys in global config
git config --global --list 2>/dev/null | grep -E 'pull\.|rerere\.|blame\.' \
  && echo "FAIL: global hygiene keys present" || echo "no global hygiene keys"
```

**PASS T5 without** `v0.1.0-branching-foundation` existing.

### Out of scope

- `_check_tag_freshness()` / hygiene config doctor / stash doctor (deferred)
- Global git config / `pull.rebase=true`
- Tagging every `feat/` merge
- Agent-default stash of Ryan’s files
- Blanket `*.jsonl merge=union`
- Automated Work Start / worktrees
- Committing dirty allowlist files

### Implementation watch (accepted limitations)

1. **Fresh-clone gap:** No doctor WARN if `install-repo-config.sh` never runs — clone lacks `pull.ff` / `rerere` / blame-ignore silently. Accepted for single-machine; revisit if multi-clone agents make the gap painful.
2. **Empty blame-ignore:** Header-only file is intentional when scan finds no >5-py mechanical commits; body must state “No mass-reformat SHAs as of YYYY-MM-DD…”.
3. **Wrapper stdout:** `install-git-hooks.sh` via exec will also print hygiene lines — doctor/`hooks_path` depends on hooksPath + executable pre-push, not exact prior stdout.
4. **Ryan tag lag:** T6 is async; clean T5 must not wait on the tag.

### Evidence requirements (Execute)

| ID | Evidence |
|----|----------|
| T0 | Foundation ancestor on `origin/main` |
| T1 | Branch name + HEAD == origin/main |
| T2 | Blame audit table; `.gitattributes`; plan SSoT rewritten; `grep -n 'v0\.2'` clean / `v0.1.0` present |
| T3 | Installer status four lines; wrapper restores **all four** keys after unset |
| T4 | Protocol greps incl. `no work start OK`; deploy done |
| T5 | pytest PASS; configs set; `no global hygiene keys` |
| T5b | Kiro sign-off date in handoff **and** `docs/plans/git-hygiene-baseline.md` |
| T6 | Tag exists (Ryan; separate from T5 PASS) |
| T7 | Ryan merge complete |

### Success criteria

**Agent (T5) PASS:** installer configs live; blame policy applied (SHAs or header-only); protocol deployed; no `work start`; no global drift; no JSONL union; hooks wrapper proven after unset.

**Process:** T5b Kiro sign-off → T7 Ryan merge.

**Ryan (T6) async:** `v0.1.0-branching-foundation` annotated tag pushed.

### Stop points

1. **HITL now:** approve this execution plan (may approve before T0; Execute must still wait for HITL **and** T0)
2. **T0:** Foundation merged — Cursor confirms before T1
3. **After T5:** push branch; **T5b** Kiro reviews diff → sign-off
4. **After T5b:** Ryan merges (T7); optionally completes T6

### Execute entry

- **After HITL approval AND T0 complete:** first agent task is **T1**
- Agent mode required for T1–T5
- Dogfood: `feat/<YYYY-MM-DD>-git-hygiene-baseline` from post-merge `origin/main` (**date of branch creation**, not the draft date in this plan)
- Do **not** start T1 on HITL alone if Foundation is not yet on `origin/main`

### Single active writer

Only Cursor writes in the primary checkout for this arc.
