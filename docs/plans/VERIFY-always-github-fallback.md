# Verify Plan — Always-Available GitHub Fallback

```
Planning Status

Phase:        Verify
Authority:    Post-Execute
```

**Subject:** `feat/2026-07-12-always-github-fallback`  
**Raised bar:** [`~/.cursor/plans/verify_github_fallback_5f18ba72.plan.md`](/home/lauer/.cursor/plans/verify_github_fallback_5f18ba72.plan.md)  
**Gates:** defaults accepted 2026-07-12 (see EXECUTION)

**Mechanical PASS requires:** hermetic `tests/test_work_git.py`; V0–V5 from a **unique** clean worktree; never `convmem` wrapper for doctor; installer only in an independent temp clone.

---

## 0. Preconditions (unique clean verify worktree)

Do **not** run V1–V5 in the dirty shared checkout. Preserve WH / TODO-WH / `s2_hotfix` dirt.

```bash
cd ~/Projects/convmem && git fetch origin
TIP=$(git rev-parse origin/feat/2026-07-12-always-github-fallback)
echo "TIP=$TIP"
git cat-file -e "$TIP:tests/test_work_git.py" || { echo 'FAIL V0a'; exit 1; }

if git log origin/main.."$TIP" --format='%s' | grep -qiE '^wip[:(! ]'; then
  echo 'FAIL V0d: WIP subject on tip'; exit 1
fi

VERIFY_WT=$(mktemp -d /tmp/convmem-verify-ghfb-XXXXXXXX)
rmdir "$VERIFY_WT"
git worktree add --detach "$VERIFY_WT" "$TIP" || exit 1
echo "VERIFY_WT=$VERIFY_WT"
cd "$VERIFY_WT"
if git status --porcelain -- config/ docs/plans/ convmem.py doctor.py git_hooks.py work_git.py \
  scripts/git-hooks/ scripts/install-repo-config.sh tests/ | grep -q .; then
  echo 'FAIL V0e dirty'; exit 1
fi
```

| ID | PASS |
|----|------|
| V0a | `git cat-file -e "$TIP:tests/test_work_git.py"` |
| V0d | No WIP subjects (explicit exit 1 on match) |
| V0e | Unique detached worktree; in-scope clean |

Teardown: `git worktree remove "$VERIFY_WT"` (no `--force`).

---

## 1. Diff inventory (exact path set)

```bash
EXPECTED=$(mktemp)
printf '%s\n' \
  config/agent-protocol-mcp.txt \
  config/agent-protocol.md \
  config/codex-agents-convmem.example.md \
  config/crush-rules-convmem.example.md \
  config/cursor-rules-convmem.mdc.example \
  config/kiro-steering-convmem.example.md \
  convmem.py \
  docs/plans/ARCHITECTURE-always-github-fallback.md \
  docs/plans/EXECUTION-always-github-fallback.md \
  docs/plans/VERIFY-always-github-fallback.md \
  docs/plans/branching-strategy.md \
  doctor.py \
  git_hooks.py \
  scripts/git-hooks/pre-commit \
  scripts/git-hooks/pre-push \
  scripts/install-repo-config.sh \
  tests/test_doctor.py \
  tests/test_git_hooks.py \
  tests/test_work_git.py \
  work_git.py | sort > "$EXPECTED"
diff -u "$EXPECTED" <(git diff origin/main...HEAD --name-only | sort)
# empty = V1a PASS
```

---

## 2. Protocol + branching-strategy

```bash
(rg -nF 'Single-file doc typos may stay' config/agent-protocol.md docs/plans/branching-strategy.md && echo FAIL) || echo 'no typo exception OK'
rg -nF 'Always-Available GitHub Fallback' config/agent-protocol.md
rg -nF 'convmem work start' config/agent-protocol.md
rg -nF 'refs/heads/' config/agent-protocol.md docs/plans/branching-strategy.md
(rg -nF 'git push -u origin HEAD' config/agent-protocol.md docs/plans/branching-strategy.md && echo FAIL) || echo 'no bare HEAD push OK'
(rg -n 'CONVMEM_SKIP_MAIN_HOOK=1' config/agent-protocol.md && echo 'FAIL: bypass in agent protocol') || echo 'no bypass instruction OK'
(rg -nF 'direct_commits_on_main' docs/plans/branching-strategy.md && echo 'FAIL still documenting heuristic') || echo 'heuristic retired from strategy OK'
```

| ID | Expect |
|----|--------|
| V2a–V2e | Typo gone; Always-Available + work start; explicit refspec; no bypass instruction; heuristic retired |

---

## 3. Hooks + installer

**Do not** run installer in linked `$VERIFY_WT` (shared `.git/config`).

```bash
INSTALL_CLONE=$(mktemp -d /tmp/convmem-install-check-XXXXXXXX)
rmdir "$INSTALL_CLONE"
git clone "$VERIFY_WT" "$INSTALL_CLONE"
git -C "$INSTALL_CLONE" checkout --detach "$TIP"
cd "$INSTALL_CLONE"
bash scripts/install-repo-config.sh
test "$(git config --get core.hooksPath)" = "scripts/git-hooks"
test -x scripts/git-hooks/pre-commit && test -x scripts/git-hooks/pre-push

cd "$VERIFY_WT"
PY="${CONVMEM_PYTHON:-$HOME/miniforge3/envs/convmem/bin/python}"
test -x "$VERIFY_WT/.venv/bin/python" && PY="$VERIFY_WT/.venv/bin/python"
"$PY" -m pytest tests/test_git_hooks.py -q
rg -nF 'not GitHub authz' git_hooks.py
```

---

## 4. Work CLI — hermetic tests required

Greps alone do **not** PASS V4.

```bash
test -f tests/test_work_git.py
"$PY" -m pytest tests/test_work_git.py -q
```

Must prove: start from `origin/main`; explicit remote ref + upstream; origin-only resume; taxonomy before mutate; fetch/push fail-closed.

---

## 5. Doctor

**Do not** use `convmem` wrapper (hard-coded shared checkout).

```bash
cd "$VERIFY_WT"
DOC_ROOT=$("$PY" -c "import doctor; print(doctor._repo_root())")
test "$(realpath "$DOC_ROOT")" = "$(realpath "$VERIFY_WT")"

"$PY" -m pytest tests/test_doctor.py::BranchingDoctorTests -q

OUT=$(mktemp /tmp/doctor-verify-wt-XXXXXXXX.out)
doctor_rc=0
"$PY" "$VERIFY_WT/convmem.py" doctor >"$OUT" 2>&1 || doctor_rc=$?
rg -q 'dirty_main' "$OUT"
rg -q 'unpushed_commits' "$OUT"
rg -q 'hooks_path' "$OUT"
! rg -q 'direct_commits_on_main' "$OUT"
# Nonzero: only [FAIL] restic_gate: allowed
if [ "$doctor_rc" -ne 0 ]; then
  other=$(rg '^\[FAIL\]' "$OUT" | rg -v '^\[FAIL\] restic_gate:' || true)
  test -z "$other"
  rg -q '^\[FAIL\] restic_gate:' "$OUT"
fi
```

---

## 6. GitHub + process

| ID | Result |
|----|--------|
| V6a | SKIP/GATE until Pro — do not claim main protected on 403 |
| V6c | Kiro reviewed after Mechanical PASS |
| V6d | Ryan merge GATE |

```bash
gh api repos/alanmz-crypto/convmem/branches/main/protection 2>&1 | head -5
```

---

## Verdict

| Result | When |
|--------|------|
| Mechanical PASS | V0–V5 including hermetic `test_work_git` + unique clean worktree |
| GitHub GATE | Ryan enables Pro and configures PR-only protection |
| Sign-off | Kiro / Ryan after Mechanical PASS |

## Evidence paste template

```text
VERIFY-always-github-fallback — tip <sha> VERIFY_WT=<path> OUT=<path>
V0a cat-file test_work_git.py: PASS/FAIL
V0d no WIP subjects: PASS/FAIL
V0e unique clean worktree: PASS/FAIL
V1a exact path-set: PASS/FAIL
V2a-e protocol/strategy: PASS/FAIL
V3a installer in temp clone: PASS/FAIL
V3b-c hooks pytest + authz wording: PASS/FAIL
V4a-e pytest test_work_git: PASS/FAIL
V5a-e doctor from VERIFY_WT: PASS/FAIL
V6a gh protection: SKIP(403 Pro) | PASS
Mechanical: PASS|FAIL
V6c Kiro reviewed: 2026-07-12
```

## Ryan GitHub Pro checklist (Phase 2a)

When Pro is available:

1. Protect `main`: require PR, no force-push, no deletion
2. No bypass for agents; Ryan-only if any bypass actor
3. Verify: `gh api repos/alanmz-crypto/convmem/branches/main/protection`
4. Then claim “main protected” in handoff
