# Execution Plan — Pinwheel Pytest CI

```
Planning Status

Phase:        Execute (planning package)
Characters:   Codex plan; Cursor implementation; Kiro/ChatGPT review; Ryan gate
Authority:    No CI, ruleset, CodeQL, or disposable-PR action is authorized by this file
Base:         main at bc83c85d0522023ea6e404bff4aaed135c47815a
```

## Human consequence

**Consequence:** The existing required pytest status becomes reproducible and
cannot silently lose the named catastrophic-invariant tests, while Protect
Main and CodeQL governance remain unchanged.

| | |
|---|---|
| **Who** | Codex plans; Cursor implements after Ryan authorization; Kiro/ChatGPT review; Ryan owns external evidence and merge |
| **What** | Exact pytest pin, version logs, job contract test, and per-module manifest checker |
| **When** | Planning package prepared after Kryptonite closeout and two independent PASS-with-conditions reviews |
| **Why** | Remove unpinned-runner drift and silent critical-test disappearance |
| **How** | Required `pytest (3.12)` turns red for each broken control; restored ordinary PR turns green |

**TL;DR:** Implement the narrow CI hardening contract, prove its controls with
Ryan-authorized disposable PRs, and leave Protect Main/CodeQL untouched.

## Scope lock

| In scope | Out of scope |
|---|---|
| `.github/workflows/pylint.yml` install pins, version logs, checker step | Protect Main or required status changes |
| `tests/test_ci_contract.py` and its manifest entry | CodeQL configuration or merge protection |
| Manifest parser/checker and focused tests | General collection census or coverage |
| Planning/VERIFY/handoff records and LATEST/STATUS pointers | Runtime, data, Chroma, ledger, production configuration |
| Ryan-authorized disposable PR evidence | Admin bypass evidence or unauthorized external resources |

## Tasks

### T0 — Fresh-main and version selection (Ryan gate)

1. Start from the current `origin/main`; record the exact base SHA.
2. Create the `plan/YYYY-MM-DD-pinwheel-pytest-ci` planning branch/worktree.
3. On a fresh Python 3.12 environment, install the current unpinned pytest
   once and record `python -m pytest --version`.
4. Select one exact patch version. Do not guess from a local non-3.12 or stale
   environment. Record the reason and date in the workflow comment and
   `tests/test_ci_contract.py`.

### T1 — CI contract test

Cursor adds `tests/test_ci_contract.py` and adds it to the manifest in the same
change. The test must parse/inspect the workflow in job scope and assert:

- the named `pylint` job has the approved exact `pytest==X.Y.Z` install;
- the named `pytest` job has the identical exact install;
- the pytest job includes the complete `python -m pytest -q` command; and
- the pytest job includes the exact checker invocation.

Comments or unrelated duplicate strings must not satisfy these assertions.

### T2 — Manifest checker

Add a small checker (planned path: `scripts/check_ci_critical_invariants.py`)
with focused coverage from `tests/test_ci_contract.py`:

- strict comments/blanks/path parsing;
- repository-relative `tests/*.py` validation;
- duplicate and malformed-entry rejection;
- existence check before subprocess execution; and
- per-module `python -m pytest --collect-only -q <path>` execution where only
  return code `0` passes.

The checker must preserve the same environment and interpreter as the pytest
job. It may log stdout/stderr, but must not parse human-readable collection
counts to decide success.

### T3 — Workflow update

Update both install sites to the same exact `pytest==X.Y.Z` string, add the
version log in both jobs, and add the checker after hermetic config preparation
with `CONVMEM_CONFIG=/tmp/convmem-ci/config.toml`. Keep the final full command
exactly `python -m pytest -q` and do not alter status names.

### T4 — Mechanical verification

Run focused contract/checker tests, then the 15 existing manifest modules plus
the new contract test, then the full local suite as environment permits. Run
`git diff --check` and inspect the workflow diff for accidental governance or
CodeQL changes.

### T5 — Ryan-authorized external controls

Only after explicit Ryan authorization, use disposable branches/PRs to prove:

1. removing or replacing either exact pin makes the required pytest job fail;
2. removing or renaming one manifest module makes the checker fail;
3. making one listed module collect zero tests makes the checker fail;
4. the ordinary merge path is blocked for each bad candidate; and
5. the admin bypass is not exercised.

Close/delete disposable resources only under the authorized experiment plan.

### T6 — Restoration and closeout

Restore the controls, run a normal green PR, record exact tip/run/check data in
VERIFY, update STATUS to the current state, update LATEST, and prepare the
successor handoff. Ryan owns the final merge decision.

## Stop conditions

Stop and return to Ryan if the fresh runner cannot establish a stable pytest
version, the checker needs a collection-count census, the workflow contract
cannot distinguish the named jobs, a negative control requires a real
vulnerability, or any proposed change touches Protect Main/CodeQL.
