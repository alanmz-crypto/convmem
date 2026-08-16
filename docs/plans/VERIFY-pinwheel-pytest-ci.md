# Verify Plan — Pinwheel Pytest CI

```
Planning Status

Phase:        Verify (Pinwheel Pytest CI)
Characters:   Independent reviewer
Functions:    Confirm exact pins, workflow-step preservation, and manifest fail-closed behavior
Lanes:        Cursor (mechanical); Kiro/ChatGPT (independent review); Ryan (external GATE)
Authority:    Exact implementation tip and live CI evidence; do not trust chat claims alone
```

**Subject / tip:** implementation tip to be recorded after Cursor execution
**PR(s):** Ryan-authorized implementation PR and disposable controls, if granted
**Architecture:** `ARCHITECTURE-pinwheel-pytest-ci.md`
**Execution:** `EXECUTION-pinwheel-pytest-ci.md`
**Goal:** Prove the existing required pytest check is reproducible and that
the explicit critical manifest cannot silently disappear or collect zero tests.

## Human consequence

**Consequence:** A green required pytest check will mean the reviewed pytest
version was installed, the full suite and manifest checker still ran, and each
listed critical module collected successfully.

| | |
|---|---|
| **Who** | Cursor executes; independent reviewer verifies; Ryan authorizes external controls and merge |
| **What** | Pinning, workflow-contract preservation, and per-module collection enforcement |
| **When** | After the planning package is authorized and implementation reaches a recorded tip |
| **Why** | Close the two residual risks explicitly named by Kryptonite |
| **How** | Broken controls make required `pytest (3.12)` red; ordinary merge is unsatisfied; restoration is green |

**TL;DR:** Verify Pinwheel-specific failures, not only Kryptonite's historical
deliberate test failure.

## Scope lock

| In scope | Out of scope |
|---|---|
| Exact same `pytest==X.Y.Z` in both jobs | Protect Main edits |
| Version logs and job-scoped contract assertions | CodeQL enforcement |
| Manifest parser, existence check, and per-module collection exit status | General test-count census |
| Required pytest red/blocked behavior and restored green PR | Admin bypass use, runtime, or production data |

## Verification design

| Field | Answer |
|---|---|
| Independent oracle | GitHub Actions job result plus required-status and ordinary merge state on the same PR tip |
| Failure injection | Controlled pin, workflow-step, manifest-path, and zero-collection edits on disposable authorized branches |
| Negative control | Each broken control must make the required `pytest (3.12)` check fail; no real vulnerability |
| Dual-path coverage | Pylint job pin/log and pytest job pin/log; pytest job's checker and full command |
| Collection success contract | Each subprocess must return code 0; no textual count parsing |

## V0 — Preconditions

| ID | Check | Result |
|---|---|---|
| V0a | Subject tip and PR resolve to the same implementation revision | pending |
| V0b | Base is current `main`, not the old Kryptonite planning branch | pending |
| V0c | Selected pytest version was established from fresh Python 3.12 evidence | pending |
| V0d | Ryan authorization is recorded for any disposable PR/resource | pending |
| V0e | No Protect Main, CodeQL, runtime, or data changes are in the diff | pending |

## V1 — Pin and workflow contract

| ID | Check | Result |
|---|---|---|
| V1a | Pylint job contains exact approved `pytest==X.Y.Z` | pending |
| V1b | Pytest job contains the identical exact pin | pending |
| V1c | Both jobs log `python -m pytest --version` | pending |
| V1d | Contract test scopes assertions to the named jobs | pending |
| V1e | Contract test preserves full `python -m pytest -q` | pending |
| V1f | Contract test preserves checker invocation | pending |

## V2 — Manifest checker

| ID | Check | Result |
|---|---|---|
| V2a | Comments/blanks are ignored; malformed/options-like paths fail | pending |
| V2b | Duplicate entries fail; paths are repository-relative regular files | pending |
| V2c | Checker runs each manifest path separately under `CONVMEM_CONFIG` | pending |
| V2d | Return code 0 passes; exit code 5 and all other nonzero codes fail | pending |
| V2e | Checker does not make human-readable count parsing authoritative | pending |
| V2f | Manifest is intentionally 16 entries after contract test is added | pending |

## V3 — Clean baseline

| ID | Check | Result |
|---|---|---|
| V3a | Focused contract/checker tests pass | pending |
| V3b | All 16 manifest modules collect successfully | pending |
| V3c | Full local suite passes or unrelated pre-existing failures are isolated | pending |
| V3d | Authorized ordinary PR has green `pytest (3.12)` and `pylint (3.12)` | pending |

## V4 — Pin controls

| ID | Check | Result |
|---|---|---|
| V4a | Removing the Pylint-job pin fails the contract | pending |
| V4b | Removing/replacing the pytest-job pin fails the contract | pending |
| V4c | Removing the full pytest command fails the contract | pending |
| V4d | Removing the checker invocation fails the contract | pending |

## V5 — Manifest controls

| ID | Check | Result |
|---|---|---|
| V5a | Missing/renamed listed module fails the checker | pending |
| V5b | Listed zero-test module fails by nonzero collection status | pending |
| V5c | Required `pytest (3.12)` is red on each bad candidate | pending |
| V5d | Ordinary merge path is blocked; bypass is not exercised | pending |

## V6 — Restoration and governance

| ID | Check | Result |
|---|---|---|
| V6a | Controls restored and normal PR is green | pending |
| V6b | Protect Main required contexts remain unchanged | pending |
| V6c | CodeQL remains out of scope and unchanged | pending |
| V6d | No collection census, runtime, or production-data change slipped in | pending |

## V7 — Independent sign-off

| ID | Check | Result |
|---|---|---|
| V7a | Reviewer records written PASS/FAIL naming exact tip SHA and residuals | pending |
| V7b | Ryan records the merge/closeout GATE | pending |

## Evidence log

```text
VERIFY-pinwheel-pytest-ci — tip <sha> — runner <lane> — <ISO-8601>
V0: <PASS/FAIL/SKIP> — base, authorization, and scope.
V1: <PASS/FAIL> — exact pin, logs, and preserved workflow commands.
V2: <PASS/FAIL> — strict manifest parsing and per-module exit-status collection.
V3: <PASS/FAIL> — clean baseline.
V4: <PASS/FAIL> — pin and workflow-contract negative controls.
V5: <PASS/FAIL> — missing/renamed/zero-collection controls and blocked merge.
V6: <PASS/FAIL> — restoration and governance unchanged.
Mechanical: PASS|FAIL
Sign-off: <reviewer, verdict, exact tip, residuals>
Ryan GATE: <accepted|not accepted>
```
