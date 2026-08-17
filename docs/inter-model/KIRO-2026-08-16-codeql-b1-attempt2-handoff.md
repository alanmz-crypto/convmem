# Implementation Handoff: CodeQL B1 Attempt #2 — code-injection/critical fixture

**Date:** 2026-08-16
**Author:** Kiro (design review + handoff)
**For:** Cursor (execution lane)
**Authorization:** Ryan, 2026-08-16 (verbal, this session — exact fixture authorized)
**Arc:** CodeQL Complex Therapy

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | Start fresh from current `main` (`9c2a678`) or reuse `feat/2026-08-16-2026-08-16-codeql-grant-b1` after force-replacing the old malformed fixture |
| **Tip SHA** | N/A — Cursor creates the implementation commit |
| **Push status** | N/A |
| **PR** | `not opened` — Cursor opens one disposable PR |
| **Ryan GATE** | None — B1 attempt #2 is fully authorized. B2 remains separately gated. |
| **Track A ingest** | Cursor indexes session transcript at handoff |

---

## What to build

Open one disposable PR containing a single valid-but-vulnerable GitHub Actions
workflow file that triggers the `actions/code-injection/critical` CodeQL query
(severity `error`, security-severity `9.0`, precision `very-high`). The PR
proves that the GHAS `CodeQL` results check fails while all four other required
contexts remain green, and that ordinary merge is blocked.

**Why this exists:** B1 attempt #1 (malformed YAML) failed because invalid
workflow YAML does not break default-setup CodeQL analysis — it targets the
wrong failure path. This fixture targets the correct path: the GHAS
code-scanning *results check* fails due to a severity-`error` finding, while
the analysis jobs themselves succeed.

---

## Integration point

`.github/workflows/codeql-negative-control.yml` — new disposable file on the PR
branch only; must never reach `main`.

---

## Specification

### Inputs

- None. The fixture is self-contained.

### Exact authorized fixture (path + content)

```yaml
# .github/workflows/codeql-negative-control.yml
# DISPOSABLE — must not reach main
name: codeql-negative-control
on: issue_comment

jobs:
  echo-body:
    runs-on: ubuntu-latest
    steps:
      - run: echo '${{ github.event.comment.body }}'
```

This is the canonical "incorrect usage" example from GitHub's own
`actions/code-injection/critical` query documentation.

### Expected behavior

1. `Analyze (actions)` — **GREEN** (analysis job succeeds; uploads the finding)
2. `Analyze (python)` — **GREEN** (no Python change)
3. `CodeQL` (GHAS results check, app 57789) — **RED** (error-severity finding)
4. `pylint (3.12)` — **GREEN** (no Python change)
5. `pytest (3.12)` — **GREEN** (no Python change)
6. `mergeStateStatus` — **BLOCKED** (required `CodeQL` context unsatisfied)

### Why the fixture does not execute at runtime

`issue_comment` workflows only trigger when the workflow file exists on the
**default branch**. A file that exists only on the disposable PR branch will not
be triggered at runtime. CodeQL statically analyzes the file content without
executing it.

### Output / contract

Cursor captures and commits as evidence:

- PR number and head SHA
- All 5 check-run statuses (names, conclusions, app IDs, URLs)
- `mergeStateStatus` and `mergeable` from `gh pr view`
- The code-scanning alert raised (rule ID, severity, file, line)

---

## What NOT to build

- No ruleset change
- No other workflow file changes
- No Python code changes
- No B2 producer-identity probe
- No fallback or mutation of the fixture content
- No bypass exercise
- No merge of the disposable PR
- Do not reuse the old malformed-YAML fixture (`name: [codeql-negative-control`)
- Do not create a second disposable PR if the first one fails — stop and report

---

## Test expectations (empirical — B1 is the test)

1. **1-red/4-green isolation:** Exactly `CodeQL` fails; the other four required
   contexts pass.
2. **Merge blocked:** `mergeStateStatus != CLEAN` because the required `CodeQL`
   result is unsatisfied.
3. **No runtime execution:** The `issue_comment` workflow does not appear in the
   Actions run log as an executed workflow (only as an analyzed file).

---

## Acceptance criteria

- [ ] Disposable PR opened with exactly the authorized fixture (path + content)
- [ ] `CodeQL` check conclusion = `failure` (or equivalent blocked/action_required)
- [ ] `Analyze (actions)` check conclusion = `success`
- [ ] `Analyze (python)` check conclusion = `success`
- [ ] `pylint (3.12)` check conclusion = `success`
- [ ] `pytest (3.12)` check conclusion = `success`
- [ ] `mergeStateStatus` = `BLOCKED` (ordinary merge not eligible)
- [ ] Evidence captured (check-run JSON, PR state, alert detail)
- [ ] Cursor stops and hands evidence back — does NOT proceed to B2

## Failure / stop conditions

If the result is anything other than exactly 1-red/4-green + merge blocked:

- [ ] Close the disposable PR without merge
- [ ] Delete the disposable remote branch
- [ ] Stop and report the unexpected result to Ryan/Kiro
- [ ] Do not retry, modify the fixture, or attempt a different approach

---

## Branch convention

```
feat/2026-08-16-codeql-grant-b1-v2
```

Or Cursor may reset the existing `feat/2026-08-16-2026-08-16-codeql-grant-b1`
branch to `main` and reuse it (since PR #199 is already closed/deleted). Either
approach is acceptable. Push immediately after each commit.

---

## Cleanup (Phase 5 — after evidence capture)

Per the existing EXECUTION plan Phase 5:

1. Close the disposable PR without merging
2. Delete the disposable remote branch
3. Verify the fixture file does not exist on `main`
4. Record that the five-context set and strict policy remain intact

---

## Related files

| What | Path |
|------|------|
| Architecture | `docs/plans/ARCHITECTURE-codeql-complex-therapy.md` (on `plan/` branch) |
| Execution plan | `docs/plans/EXECUTION-codeql-complex-therapy.md` (on `plan/` branch) |
| VERIFY matrix | `docs/plans/VERIFY-codeql-complex-therapy.md` (on `plan/` branch) |
| Grant A evidence | `docs/grant-a-evidence/` (on `feat/.../codeql-grant-a` branch) |
| B1 attempt #1 (failed) | PR #199 — closed, branch deleted |
| Kiro fixture review | This session (2026-08-16) — PASS with wording correction |
| Ryan authorization | This session (2026-08-16) — exact fixture authorized |
| CodeQL query docs | https://codeql.github.com/codeql-query-help/actions/actions-code-injection-critical/ |

---

## Leaving / picking up checklist

**Author (Kiro, leaving):**

- [x] This file committed on pushed branch
- [x] `LATEST.md` bullet at top with link and resume state
- [x] `STATUS-*.md` Update Log line (arc tracked — on planning branch only; note here)
- [x] Branch pushed

**Implementer (Cursor, picking up):**

- [ ] Read this file before first edit
- [ ] Start fresh branch or reset existing B1 branch
- [ ] Replace malformed YAML with exact authorized fixture
- [ ] Open disposable PR targeting `main`
- [ ] Wait for all 5 checks to complete
- [ ] Capture evidence
- [ ] If success: hand back to Kiro/Ryan; if failure: close/delete and stop

---

## Forward announcement

I finished: [Arc CodeQL Complex Therapy] B1 attempt #2 fixture design review + Cursor handoff doc
Next step: Cursor executes B1 attempt #2 with exact authorized fixture
Next lane: Cursor
See my work: `docs/inter-model/KIRO-2026-08-16-codeql-b1-attempt2-handoff.md`
