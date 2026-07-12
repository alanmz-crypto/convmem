# Verify Plan — Branching Safety Foundation

```
Planning Status

Phase:        Verify (interim — not Verify OS)
Characters:   Test-First Reviewer; optional Codex independent audit
Functions:    Reviewer
Lanes:        Codex (shell) preferred; Cursor may self-check; Kiro for protocol/roles review
Authority:    Post-Execute HITL — independent of implementer chat claims
```

**Subject:** `feat/2026-07-11-branching-strategy`  
**Tip (at plan write):** `6d8980a` — `feat: Branching Safety Foundation — WIP hook, doctor checks, protocol`  
**Sources:** [`EXECUTION-branching-safety-foundation.md`](EXECUTION-branching-safety-foundation.md), [`branching-strategy.md`](branching-strategy.md), [`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md) format  
**Goal:** Confirm Option A Foundation is correctly installed and behaves as specified — without trusting Cursor session claims.

**Report format:** For each check, state **PASS / FAIL / SKIP / DEFERRED / GATE** and one line of evidence (exit code, command output snippet, or `file:line`).  
**GATE** = process self-check (Ryan); not a mechanical PASS/FAIL.

---

## Layout note (hook vs module)

| Path | Role |
|------|------|
| **`git_hooks.py`** (repo root) | Python module — classifiers, `evaluate_pre_push_stdin`, `REJECTION_STDERR`; imported by doctor + tests |
| **`scripts/git-hooks/pre-push`** | Shell wrapper — sets `PYTHONPATH` to repo root, calls `git_hooks.main()` |

V3–V5 check the **shell wrapper install**. V6 / V13–V14 check the **Python module**.

---

## 0. Preconditions

| Check | Command / action | PASS |
|-------|------------------|------|
| On or reviewing the feature branch | `git branch --show-current` or `git log origin/main..feat/2026-07-11-branching-strategy --oneline` | Branch exists; tip contains Foundation commit |
| Working from repo root | `cd ~/Projects/convmem && pwd` | Path is convmem |
| Dirty allowlist ignored | `git status --short` | Unrelated dirty files do **not** fail verify |

---

## 1. Automated tests (Codex / Cursor)

```bash
cd ~/Projects/convmem
git switch feat/2026-07-11-branching-strategy   # if not already
python -m pytest tests/test_git_hooks.py tests/test_doctor.py::BranchingDoctorTests -q
echo "pytest exit: $?"
rg -n 'def test.*wip.*push|def test.*reject.*wip' tests/test_git_hooks.py
```

| ID | Expect | PASS |
|----|--------|------|
| V1 | pytest exit `0` | All listed tests green |
| V2 | WIP rejection covered by fixture | `rg` finds a `def test_…` matching `wip`+`push` or `reject`+`wip` in `tests/test_git_hooks.py` — **do not** push WIP to real `origin/main` |

**FAIL if:** any test fails, or verifier attempts real-remote WIP push as proof.

---

## 2. Hook install (real clone — no remote push)

```bash
cd ~/Projects/convmem
git config --get core.hooksPath
test -x scripts/git-hooks/pre-push && echo "pre-push executable"
head -5 scripts/git-hooks/pre-push
ls -la git_hooks.py scripts/git-hooks/pre-push
```

| ID | Expect | PASS |
|----|--------|------|
| V3 | `core.hooksPath` is `scripts/git-hooks` | Exact or resolves to repo `scripts/git-hooks` |
| V4 | `scripts/git-hooks/pre-push` exists and is executable | `test -x` prints confirmation |
| V5a | Hooks path already configured | V3+V4 PASS without running install — record evidence; **SKIP V5b** |
| V5b | Install script repairs unset/wrong path | Only if V3 or V4 failed: run `bash scripts/install-git-hooks.sh`, re-check V3–V4, then `convmem doctor` shows `[PASS] hooks_path` |

**Module stderr constant (no remote):**

```bash
cd ~/Projects/convmem
# Repo-root module (not scripts/git-hooks/):
python -c "
from git_hooks import REJECTION_STDERR
assert 'Push rejected: WIP commits on main' in REJECTION_STDERR
assert 'CONVMEM_SKIP_WIP_HOOK=1' in REJECTION_STDERR
print('stderr constant OK')
"
```

| ID | Expect | PASS |
|----|--------|------|
| V6 | Rejection stderr in **repo-root** `git_hooks.py` | `stderr constant OK`; import is `from git_hooks import …` (module at repo root; shell wrapper is separate) |

---

## 3. Doctor checks (order + semantics)

```bash
cd ~/Projects/convmem
convmem doctor 2>&1 | tee /tmp/convmem-doctor-branching.txt
echo "doctor exit: $?"
# Order of the three branching checks among early PASS/WARN lines:
rg -n "hooks_path|wip_on_main|direct_commits_on_main" /tmp/convmem-doctor-branching.txt
```

| ID | Expect | PASS |
|----|--------|------|
| V7 | Doctor **exit code** | `0` **or** known unrelated FAIL only (e.g. `restic_gate` — see **Known non-failures** below) — document; branching checks must not be `[FAIL]` |
| V8 | `hooks_path` appears **before** `wip_on_main` and `direct_commits_on_main` | Line numbers ascending |
| V9 | `hooks_path` | `[PASS]` after install; `[WARN]` if unset (then V5b) |
| V10 | `wip_on_main` | `[PASS]` or `[WARN]` with WIP subjects — **WARN is expected** while historical WIP remains on main (`5014b30`, etc.). Not a Foundation FAIL |
| V11 | `direct_commits_on_main` | Detail contains **`heuristic`**; `[WARN]`/`[SKIP]`/`[PASS]` all acceptable. SKIP must say `unable to measure` / no reflog — **not** silent PASS |
| V12 | Branching checks never `ok=False` / `[FAIL]` | Advisory only |

**Do not fail verify because:**

- `direct_commits_on_main` WARNs (squash / prior `feat:` commits on main look the same)
- `wip_on_main` WARNs on pre-Foundation history
- Unrelated doctor FAILs (e.g. `restic_gate`) — mark **DEFERRED** / out-of-scope for this verify plan

---

## 4. Shared helpers (repo-root `git_hooks.py`)

```bash
cd ~/Projects/convmem
test -f git_hooks.py && echo "module at repo root OK"
python -c "
from git_hooks import wip_commit_blocked, conventional_feat_fix_subject
assert wip_commit_blocked('WIP: x')
assert wip_commit_blocked('wip(scope): y')
assert not wip_commit_blocked('feat: z')
assert not wip_commit_blocked('[WIP] no')
assert conventional_feat_fix_subject('feat: a')
assert conventional_feat_fix_subject('fix(hooks): b')
assert not conventional_feat_fix_subject('docs: c')
print('classifier OK')
"
rg -n "WIP_SUBJECT_RE|CONVENTIONAL_SUBJECT_RE|REJECTION_STDERR" git_hooks.py
```

| ID | Expect | PASS |
|----|--------|------|
| V13 | Classifier smoke via repo-root module | `classifier OK` |
| V14 | Regex / stderr live in **`./git_hooks.py`** (repo root) | Grep hits; path is not under `scripts/git-hooks/` |

---

## 5. Protocol + roles surfaces

```bash
cd ~/Projects/convmem
rg -nF "Branching (convmem prod only" config/agent-protocol.md config/cursor-rules-convmem.mdc.example config/agent-protocol-mcp.txt
rg -n "work start" config/agent-protocol.md config/cursor-rules-convmem.mdc.example && echo "UNEXPECTED work start" || echo "no work start OK"
rg -n "May merge main|plan, docs only|merge to \`main\`" docs/AGENT-ROLES.md config/agent-protocol.md
```

| ID | Expect | PASS |
|----|--------|------|
| V15 | Branching block in SSoT + at least one generated surface | Literal `-F` hits in `agent-protocol.md` and generated example |
| V16 | No `work start` in protocol | `no work start OK` |
| V17 | Kiro scoped to plan/docs; Ryan-only merge | AGENT-ROLES / TEAM_CHARTER language present |
| V18 | Deployed surface (optional) | `rg -F "Branching (convmem" ~/.cursor/rules/convmem.mdc` — PASS if deploy ran; SKIP if verifier has no home deploy |

---

## 6. Scope negatives (Foundation only)

```bash
cd ~/Projects/convmem
rg -n "def work_start|convmem work" convmem.py git_hooks.py doctor.py 2>/dev/null || true
test ! -d ~/.local/share/convmem/worktrees && echo "no worktrees dir OK" || echo "worktrees exist — note only"
```

| ID | Expect | PASS |
|----|--------|------|
| V19 | No `convmem work` CLI shipped | No work-start implementation in this commit |
| V20 | No worktree automation required | Presence of a dir is informational only |

---

## 7. Diff / merge readiness (Ryan or Kiro)

```bash
cd ~/Projects/convmem
git fetch origin
git log origin/main..feat/2026-07-11-branching-strategy --oneline
git diff --stat origin/main...feat/2026-07-11-branching-strategy
```

| ID | Expect | Result type |
|----|--------|-------------|
| V21 | Commits are Foundation-scoped | **PASS/FAIL** — Diff touches hook/doctor/protocol/roles/plans/tests — not unrelated triage/TODO files |
| V22 | Kiro review (optional) | **PASS/SKIP** — Diff reviewed; sign-off or change requests noted |
| V23 | Merge authority | **GATE (Ryan self-check)** — Ryan merges with `--ff-only` or `--squash`; agents do not merge. Not mechanically verifiable — do not search for a programmatic assertion |

---

## 8. Evidence table (filled 2026-07-11 — Cursor verify run)

| ID | Result | Evidence |
|----|--------|----------|
| V1 | **PASS** | `9 passed` pytest exit 0 |
| V2 | **PASS** | `tests/test_git_hooks.py:74 def test_rejects_wip_push_to_main` — no real-remote push |
| V3 | **PASS** | `core.hooksPath=scripts/git-hooks` |
| V4 | **PASS** | `scripts/git-hooks/pre-push` executable (`-rwxr-xr-x`) |
| V5a | **PASS** | V3+V4 already OK; V5b skipped |
| V5b | **SKIP** | Not needed |
| V6 | **PASS** | `stderr constant OK` from repo-root `git_hooks` |
| V7 | **PASS** | Branching checks not FAIL; unrelated `[FAIL] restic_gate` (stale snapshot) — Known non-failure |
| V8 | **PASS** | hooks_path L3 → wip_on_main L4 → direct_commits L5 |
| V9 | **PASS** | `[PASS] hooks_path: hooksPath=scripts/git-hooks (pre-push ok)` |
| V10 | **PASS** | `[WARN] wip_on_main` — expected historical WIP (non-failure) |
| V11 | **PASS** | `[WARN] … heuristic: 12 feat:/fix: commit:` — contains `heuristic` |
| V12 | **PASS** | No branching check `[FAIL]` |
| V13 | **PASS** | `classifier OK` |
| V14 | **PASS** | `./git_hooks.py` lines 11,14,16 — repo root |
| V15 | **PASS** | `-F` hits in agent-protocol.md + cursor-rules + mcp.txt |
| V16 | **PASS** | `no work start OK` |
| V17 | **PASS** | Kiro `plan, docs only`; TEAM_CHARTER merge-to-main must-nots |
| V18 | **PASS** | `~/.cursor/rules/convmem.mdc` contains Branching block |
| V19 | **PASS** | no work-start impl in convmem.py/git_hooks/doctor |
| V20 | **PASS** | `no worktrees dir OK` |
| V21 | **PASS** | `6d8980a` only; 15 Foundation files — triage/TODO/s2_hotfix not in commit |
| V22 | **SKIP** | Kiro review not run this pass |
| V23 | **GATE** | Awaiting Ryan merge (`--ff-only` or `--squash`) |

**Overall: PASS** (no FAIL on scored checks). V23 GATE remains for Ryan.

Note: `docs/plans/VERIFY-branching-safety-foundation.md` is untracked on the working tree — add in a follow-up commit if you want it on the branch before merge.

---

## Known non-failures (do not escalate)

1. Historical WIP on main → `wip_on_main` WARN  
2. Squash / prior feat commits → `direct_commits_on_main` heuristic WARN  
3. Missing/expired reflog → `unable to measure` SKIP  
4. Stale restic / other doctor FAILs unrelated to branching (e.g. `restic_gate`)  
5. `--no-verify` / `CONVMEM_SKIP_WIP_HOOK=1` can bypass hook — client-side only; out of scope for this verify

---

## Exit

- Verifier returns filled evidence table + overall PASS/FAIL  
- Handoff ≠ record; no `convmem record` unless Ryan asks  
- On PASS: Ryan completes V23 GATE and merges; on FAIL: Cursor fix on same branch, re-run this plan  

**Not this verify:** Automated Work Start, worktrees, merge trailers, cleaning `5014b30` history.
