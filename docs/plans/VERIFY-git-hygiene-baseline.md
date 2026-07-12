# Verify Plan — Git Hygiene Baseline (T5b)

```
Planning Status

Phase:        Verify (T5b — independent of implementer)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Kiro (primary); Codex optional for shell re-run
Authority:    Post-Execute HITL — do not trust Cursor session claims alone
```

**Subject:** `feat/2026-07-11-git-hygiene-baseline`  
**Tip (at plan write):** `8f64562` — `feat: Git Hygiene Baseline — installer, blame-ignore, markdown diffs, protocol`  
**Base:** `origin/main` @ `2957e0b` (Foundation already merged; tag `v0.1.0-branching-foundation` exists)  
**Sources:** [`EXECUTION-git-hygiene-baseline.md`](EXECUTION-git-hygiene-baseline.md), [`git-hygiene-baseline.md`](git-hygiene-baseline.md), [`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md) format  
**Goal:** Confirm repo-local hygiene (unified installer, attrs, blame policy, protocol) matches locked decisions — without expanding scope into Work Start, global config, JSONL union, or new doctor checks.

**Report format:** For each check, state **PASS / FAIL / SKIP / DEFERRED / GATE** and one line of evidence (exit code, command output snippet, or `file:line`).  
**GATE** = process step for Ryan (merge); not a mechanical agent PASS.

**Sign-off (required for T5b):** After overall PASS, append `Kiro reviewed: YYYY-MM-DD` to [`git-hygiene-baseline.md`](git-hygiene-baseline.md) **and** note the same date in session handoff.

---

## Scope lock (fail if violated)

| In scope | Out of scope (FAIL if this branch adds them) |
|----------|-----------------------------------------------|
| `install-repo-config.sh` + thin hooks wrapper | `git config --global` / `pull.rebase=true` |
| `.gitattributes` `*.md diff=markdown` | `*.jsonl merge=union` (any path) |
| Header-only or audited `.git-blame-ignore-revs` | `_check_tag_freshness` / hygiene doctor |
| Protocol: tag propose, pull.ff/rebase, `git rerere diff`, stash auth, clone install | “work start” / `convmem work *` language |
| Fix Foundation tag docs → `v0.1.0-branching-foundation` | Tagging every feat; worktrees |

---

## 0. Preconditions

| ID | Check | Command / action | PASS |
|----|-------|------------------|------|
| V0a | Reviewing the hygiene branch | `git fetch origin && git log origin/main..origin/feat/2026-07-11-git-hygiene-baseline --oneline` | Tip is hygiene commit(s); not empty |
| V0b | Diff base is post-Foundation main | `git merge-base --is-ancestor 6d8980a origin/main` | Exit 0 |
| V0c | Dirty allowlist ignored | `git status --short` | WH triage / TODO-WH / `s2_hotfix_reconcile` dirt does **not** fail verify |
| V0d | Working tree for review | Prefer `git switch feat/2026-07-11-git-hygiene-baseline` or review via `git diff origin/main...origin/feat/2026-07-11-git-hygiene-baseline` | Evidence recorded |

```bash
cd ~/Projects/convmem
git fetch origin
git log origin/main..origin/feat/2026-07-11-git-hygiene-baseline --oneline
git diff --stat origin/main...origin/feat/2026-07-11-git-hygiene-baseline
```

---

## 1. Diff inventory (Kiro — read first)

```bash
git diff origin/main...origin/feat/2026-07-11-git-hygiene-baseline --name-only
```

| ID | Expect | PASS |
|----|--------|------|
| V1a | Expected paths only | Roughly: `.git-blame-ignore-revs`, `.gitattributes`, `scripts/install-repo-config.sh`, `scripts/install-git-hooks.sh`, `config/agent-protocol*` + generated surfaces, `docs/plans/{git-hygiene-baseline,EXECUTION-git-hygiene-baseline,branching-strategy}.md` |
| V1b | No surprise runtime | Diff does **not** add doctor `_check_*` for tags/hygiene, work-start CLI, or global config scripts |
| V1c | Allowlist not smuggled | Diff does **not** include `WILLOWYHOLLOW-BUG-TRIAGE*`, `TODO-WH-PRACTICE*`, `s2_hotfix_reconcile.md` |

---

## 2. Blame-ignore + attributes

```bash
cd ~/Projects/convmem
git switch feat/2026-07-11-git-hygiene-baseline   # if reviewing live tree
test -f .git-blame-ignore-revs
grep -F 'No mass-reformat SHAs as of' .git-blame-ignore-revs
# Body SHAs (if any) must be full 40-char; pylintrc-only must not appear
grep -E '^[0-9a-f]{40}$' .git-blame-ignore-revs || echo "header-only OK"
grep -F '*.md diff=markdown' .gitattributes
(grep -qF 'merge=union' .gitattributes && echo FAIL) || echo "no union OK"
grep -n 'v0\.2' docs/plans/branching-strategy.md && echo FAIL || echo "no phantom v0.2 OK"
grep -F 'v0.1.0-branching-foundation' docs/plans/branching-strategy.md
```

| ID | Expect | PASS |
|----|--------|------|
| V2a | Blame file exists with dated “no mass-reformat” note | Header present (SHAs optional) |
| V2b | Audit table in plan SSoT | [`git-hygiene-baseline.md`](git-hygiene-baseline.md) has blame audit table; omit reasons match eligibility (logic pollution only) |
| V2c | Markdown diff only | `*.md diff=markdown` present |
| V2d | No JSONL union | `no union OK` |
| V2e | Tag version fix | No `v0.2` in branching-strategy closure; `v0.1.0-branching-foundation` present |

**FAIL if:** pylintrc-only SHAs listed “to fill the file,” or any `merge=union` in `.gitattributes`.

---

## 3. Unified installer + wrapper regression

```bash
cd ~/Projects/convmem
# Installer must never use --global
rg -n 'config --global|git config --global' scripts/install-repo-config.sh scripts/install-git-hooks.sh \
  && echo FAIL || echo "no global OK"
# pull.ff failure comment present
rg -n 'pull\.ff|diverged|rebase origin/main|pull --ff-only' scripts/install-repo-config.sh

bash scripts/install-repo-config.sh
# Expect four status lines:
#   core.hooksPath = ...
#   pull.ff = only
#   rerere.enabled = true
#   blame.ignoreRevsFile = .git-blame-ignore-revs

test "$(git config --get core.hooksPath)" = "scripts/git-hooks"
test "$(git config --get pull.ff)" = "only"
test "$(git config --get rerere.enabled)" = "true"
test "$(git config --get blame.ignoreRevsFile)" = ".git-blame-ignore-revs"
test -x scripts/git-hooks/pre-push

# Wrapper must restore ALL four (not hooksPath-only)
git config --local --unset-all core.hooksPath || true
git config --local --unset-all pull.ff || true
git config --local --unset-all rerere.enabled || true
git config --local --unset-all blame.ignoreRevsFile || true
for k in core.hooksPath pull.ff rerere.enabled blame.ignoreRevsFile; do
  git config --get "$k" && { echo "FAIL: $k still set"; exit 1; } || true
done
bash scripts/install-git-hooks.sh
test "$(git config --get core.hooksPath)" = "scripts/git-hooks"
test "$(git config --get pull.ff)" = "only"
test "$(git config --get rerere.enabled)" = "true"
test "$(git config --get blame.ignoreRevsFile)" = ".git-blame-ignore-revs"
head -5 scripts/install-git-hooks.sh | grep -q install-repo-config && echo "wrapper exec OK"
```

| ID | Expect | PASS |
|----|--------|------|
| V3a | No `--global` in install scripts | `no global OK` |
| V3b | `pull.ff` recovery comment in installer | Mentions diverged / rebase / `--ff-only` |
| V3c | Installer sets four keys + prints them | Values match table above |
| V3d | Wrapper is thin `exec` → full installer | After unset-all four, wrapper restores all four |
| V3e | Pre-push still executable | `test -x` passes (Foundation hook not broken) |

---

## 4. Protocol + generated surfaces

```bash
cd ~/Projects/convmem
rg -nF 'install-repo-config.sh' config/agent-protocol.md
rg -nF 'git rerere diff' config/agent-protocol.md config/cursor-rules-convmem.mdc.example
rg -n 'pull.ff|pull --ff-only' config/agent-protocol.md
rg -n 'stash' config/agent-protocol.md | head -5
(rg -n "work start" config/agent-protocol.md && echo FAIL) || echo "no work start OK"
# Generated surfaces should carry the same Git hygiene paragraph
rg -nF 'Git Hygiene Baseline' config/cursor-rules-convmem.mdc.example \
  config/codex-agents-convmem.example.md config/kiro-steering-convmem.example.md
```

| ID | Expect | PASS |
|----|--------|------|
| V4a | Clone install one-liner | `install-repo-config.sh` in Tier A |
| V4b | Rerere review wording | Exact phrase `git rerere diff` in protocol + Cursor example |
| V4c | pull.ff / rebase / ff-only | Present in protocol |
| V4d | Stash: own OK; Ryan dirt needs plan auth | Present; not “never stash” absolute |
| V4e | No Work Start | `no work start OK` |
| V4f | Surfaces regenerated | Hygiene paragraph in Cursor/Codex/Kiro examples |

**Locked content checklist (all must appear):**

1. Propose `vX.Y.Z-<slug>` or `milestone/<slug>`; Ryan tags; `git switch -c <branch> <tag>`
2. Feature: `git fetch origin && git rebase origin/main`; clean main: `git pull --ff-only`
3. `git rerere diff`
4. Stash authorization rule
5. After clone: `bash scripts/install-repo-config.sh`

---

## 5. Regression tests + global drift

```bash
cd ~/Projects/convmem
python -m pytest tests/test_doctor.py tests/test_git_hooks.py -q
echo "pytest exit: $?"

git config --global --list 2>/dev/null | grep -E 'pull\.|rerere\.|blame\.' \
  && echo "FAIL: global hygiene keys present" || echo "no global hygiene keys"
```

| ID | Expect | PASS |
|----|--------|------|
| V5a | Foundation tests still green | pytest exit `0` |
| V5b | No global hygiene drift from this arc | `no global hygiene keys` (or pre-existing keys documented as SKIP with evidence they were not set by these scripts) |

---

## 6. Async / process (not blocking mechanical PASS)

| ID | Check | PASS / GATE |
|----|-------|-------------|
| V6a | Foundation tag exists | `git rev-parse v0.1.0-branching-foundation` — **informational** (T6); hygiene T5b PASS does not require creating the tag |
| V6b | Plan SSoT status | [`git-hygiene-baseline.md`](git-hygiene-baseline.md) reflects active execute + audit table |
| V6c | Kiro sign-off line | After review: set `Kiro reviewed: YYYY-MM-DD` in plan SSoT + handoff |
| V6d | Ryan merge | **GATE** — Ryan `--ff-only` or squash merge after V6c (T7) |

---

## Overall verdict

| Result | When |
|--------|------|
| **PASS** | V0–V5 all PASS (or justified SKIP); V6c completed |
| **FAIL** | Any scope-lock violation, wrapper restores hooks only, `merge=union`, `work start`, `--global` in install scripts, or phantom `v0.2` tag docs |
| **GATE** | V6d Ryan merge only |

**Accepted limitations (do not FAIL):** fresh-clone silent gap until install runs; header-only blame-ignore; wrapper stdout includes hygiene lines.

---

## Evidence paste template (Kiro handoff)

```text
VERIFY-git-hygiene-baseline — tip <sha>
V0: …
V1: …
V2: …
V3: wrapper four-key restore: PASS/FAIL
V4: no work start OK; install-repo-config + git rerere diff: PASS/FAIL
V5: pytest …; no global hygiene keys: PASS/FAIL
Overall: PASS|FAIL
Kiro reviewed: YYYY-MM-DD
```

Then edit [`git-hygiene-baseline.md`](git-hygiene-baseline.md): replace `_(pending T5b)_` with the date.
