# Cursor Handoff: Forward-announcement norm + stuck-branch cleanup

**Date:** 2026-08-14  
**Author:** Kiro (design review + triage)  
**For:** Cursor (implementation)  
**Authorization:** Ryan, 2026-08-13 (forward-announcement norm); triage routing from this session  
**Branch context:** Starting from `main` (create new branch per task)

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `READY_FOR_CURSOR` |
| **Prior work** | Kiro triage session — all 4 open PRs merged; forward-announcement norm reviewed PASS |
| **Blocked on** | Nothing — all three tasks below are independently actionable |

---

## Task 1: Deploy the forward-announcement norm

**What:** Add the forward-announcement behavioral convention to `config/agent-protocol.md` so it propagates to all agent surfaces.

**Where:** Insert immediately after the existing `Handoff:` line in the Branching section (Tier A). The current line reads:

```
Handoff: branch name + `git log origin/main..HEAD --oneline` + push status.
```

**Add this paragraph after it:**

```markdown
**Forward announcement (required at phase completion).** When finishing a phase (implementation, plan, verification, review), end with:

```
I finished: [phase name]
Next step:  [what needs to happen next]
Next lane:  [who does it — e.g. Kiro, Cursor, Ryan]
See my work: [single easiest path to evaluate — PR URL, file path, or diff command]
```

"See my work" must be the lowest-effort viewing path — a PR diff URL, a single file to read, or a targeted `git diff` command. Not a branch name and SHA that requires spelunking. Trivial work (one-line fix, single ack) scales down to one sentence naturally.
```

**Then:** Run `bash scripts/deploy-agent-protocol.sh` to propagate to all surfaces.

**Branch:** `feat/2026-08-14-forward-announcement-norm`  
**Verify:** `convmem doctor` still passes; grep all deployed surfaces for "Forward announcement" to confirm propagation.

---

## Task 2: Rebase and open PRs for 3 stuck branches

These branches have unique unmerged code (1-3 commits each) that got stuck because the implementing model didn't announce forward. They've diverged from main due to CG-1 code being added then removed — the rebase will be large in diff but the actual conflicts should be minimal (these branches don't touch CG-1 files).

### 2a. `fix/2026-08-08-judge-injection-hardening`

- **What it does:** Hardens the LLM judge (`eval_judge.py`) against prompt injection from graded excerpts. Seals untrusted input behind structural delimiters.
- **Unique content:** 1 commit (`harden LLM judge against injected instructions in graded excerpts`)
- **Rebase strategy:** `git checkout fix/2026-08-08-judge-injection-hardening && git rebase origin/main` — resolve conflicts in `eval_judge.py` only (the branch's change is isolated to that file).
- **PR title:** `Harden LLM judge against prompt injection from graded excerpts`
- **Verify:** `pytest tests/test_judgebench_contracts.py` + pylint gate

### 2b. `fix/2026-08-06-ask-eval-trace`

- **What it does:** Adds eval trace to `ask.py` — records effective synthesis model and adds judge-facing trace output.
- **Unique content:** 3 commits (add trace, record model, clear lint regression)
- **Rebase strategy:** `git checkout fix/2026-08-06-ask-eval-trace && git rebase origin/main` — conflicts likely in `ask.py` (CG-1 touched it).
- **PR title:** `Record synthesis model and judge trace in ask eval output`
- **Verify:** `pytest tests/test_ask_trace.py` + pylint gate

### 2c. `feat/2026-08-07-synthesis-calibration-expansion`

- **What it does:** Preserves operational details (model name, timing) in synthesis answers.
- **Unique content:** 1 commit, 3 files (ask.py +2 lines, golden fixture +1, test +2)
- **Rebase strategy:** Simple — tiny change. `git checkout feat/2026-08-07-synthesis-calibration-expansion && git rebase origin/main`
- **PR title:** `Preserve operational details in synthesis answers`
- **Verify:** `pytest tests/test_ask_trace.py` + pylint gate

**Note:** If rebase conflicts are too complex on any branch (especially 2b which touches ask.py heavily), cherry-pick the unique commit(s) onto a fresh branch from main instead.

---

## Task 3: Finish intake-classification code (if Ryan authorizes)

**Context:** Branch `plan/2026-08-14-arc-classification-verify-gate` has uncommitted work:
- `intake_contract.py` (new file — parse/validate INTAKE-*.md)
- `doctor.py` change (+32 lines: `_check_intake_classification` function)
- `docs/PLANNING-PROTOCOL.md` (+35 lines: Arc classification section)
- `docs/planning/EXECUTE-TASK.md` (+38 lines: intake step)
- `tests/test_intake_contract.py` (new)
- `tests/test_doctor_intake_classification.py` (new)
- `docs/plans/INTAKE-TEMPLATE.md` (new)

**Status:** Code is scaffolded but uncommitted. Tests exist but haven't been verified against current main.

**If authorized:** Commit the dirty state, rebase on main, verify tests pass, open PR.  
**If not authorized:** Leave it. The forward-announcement norm (Task 1) solves the same problem behaviorally without infrastructure.

---

## Priority order

1. Task 1 (norm deployment) — highest value, lowest risk, prevents future stuck work
2. Task 2 (stuck branches) — clears the backlog, each is independent
3. Task 3 (intake classification) — only if Ryan explicitly authorizes

---

## What NOT to do

- Do not touch the parked branches (judgebench-live-driver, shadow C6/C7, r2b-capture) — they're waiting on Ryan gates
- Do not delete stale remote branches — Ryan handles that directly
- Do not modify LATEST.md beyond what the norm deployment requires
- Do not implement anything from the `fix/2026-08-04-embedding-eval-gate1-hardening` branch — Ryan is deciding its fate

---

## Forward announcement (practicing the norm)

```
I finished: Design review — triage of all open PRs, classification of branches, norm review PASS.
Next step:  Deploy norm to agent-protocol.md, rebase 3 stuck branches into PRs.
Next lane:  Cursor.
See my work: This file (docs/inter-model/KIRO-2026-08-14-cursor-forward-announcement-and-stuck-branches.md)
```
