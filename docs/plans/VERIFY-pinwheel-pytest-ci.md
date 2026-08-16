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
| V0a | Subject tip and PR resolve to the same implementation revision | **PASS** | branch `fix/2026-08-16-pinwheel-pytest-ci`; tip recorded at handoff |
| V0b | Base is current `main`, not the old Kryptonite planning branch | **PASS** | base `bc83c85d0522023ea6e404bff4aaed135c47815a` |
| V0c | Selected pytest version was established from fresh Python 3.12 evidence | **PASS** | pytest 9.1.1 from isolated Python 3.12.13 venv; candidate baseline 2026-08-16T05:34:00Z |
| V0d | Ryan authorization is recorded for any disposable PR/resource | **PASS** | Ryan authorized disposable controls 2026-08-16; PRs #192–#194 closed without merge |
| V0e | No Protect Main, CodeQL, runtime, or data changes are in the diff | **PASS** | local diff scope review |

## V1 — Pin and workflow contract

| ID | Check | Result |
|---|---|---|
| V1a | Pylint job contains exact approved `pytest==X.Y.Z` | **PASS** | local implementation + contract tests |
| V1b | Pytest job contains the identical exact pin | **PASS** | local implementation + contract tests |
| V1c | Both jobs log `python -m pytest --version` | **PASS** | local implementation + contract tests |
| V1d | Contract test scopes assertions to the named jobs | **PASS** | local implementation + contract tests |
| V1e | Contract test preserves full `python -m pytest -q` | **PASS** | local implementation + contract tests |
| V1f | Contract test preserves checker invocation | **PASS** | local implementation + contract tests |

## V2 — Manifest checker

| ID | Check | Result |
|---|---|---|
| V2a | Comments/blanks are ignored; malformed/options-like paths fail | **PASS** | local implementation + contract tests |
| V2b | Duplicate entries fail; paths are repository-relative regular files | **PASS** | local implementation + contract tests |
| V2c | Checker runs each manifest path separately under `CONVMEM_CONFIG` | **PASS** | local implementation + contract tests |
| V2d | Return code 0 passes; exit code 5 and all other nonzero codes fail | **PASS** | local implementation + contract tests |
| V2e | Checker does not make human-readable count parsing authoritative | **PASS** | local implementation + contract tests |
| V2f | Manifest is intentionally 16 entries after contract test is added | **PASS** | local implementation + contract tests |

## V3 — Clean baseline

| ID | Check | Result |
|---|---|---|
| V3a | Focused contract/checker tests pass | **PASS** | 21 contract tests |
| V3b | All 16 manifest modules collect successfully | **PASS** | checker PASS |
| V3c | Full local suite passes or unrelated pre-existing failures are isolated | **PASS** | 1348 passed; isolated: `test_eval_golden` (live corpus), `test_file_generation_read_path_inventory` |
| V3d | Authorized ordinary PR has green `pytest (3.12)` and `pylint (3.12)` | **PASS** | [#191](https://github.com/alanmz-crypto/convmem/pull/191) merged `857a3a2`; green CI on tip `35e090d` |

## V4 — Pin controls

| ID | Check | Result |
|---|---|---|
| V4a | Removing the Pylint-job pin fails the contract | **PASS** | local contract negative controls (pylint-job pin isolated in V4a) |
| V4b | Removing/replacing the pytest-job pin fails the contract | **PASS** | local contract negative controls (pylint-job pin isolated in V4a) |
| V4c | Removing the full pytest command fails the contract | **PASS** | local contract negative controls (pylint-job pin isolated in V4a) |
| V4d | Removing the checker invocation fails the contract | **PASS** | local contract negative controls (pylint-job pin isolated in V4a) |

## V5 — Manifest controls

| ID | Check | Result |
|---|---|---|
| V5a | Missing/renamed listed module fails the checker | **PASS** | local checker controls |
| V5b | Listed zero-test module fails by nonzero collection status | **PASS** | local checker controls |
| V5c | Required `pytest (3.12)` is red on each bad candidate | **PASS** | [#192](https://github.com/alanmz-crypto/convmem/pull/192) `b4d2fbc`; [#193](https://github.com/alanmz-crypto/convmem/pull/193) `003a449`; [#194](https://github.com/alanmz-crypto/convmem/pull/194) `aae0e20` — pytest jobs failed |
| V5d | Ordinary merge path is blocked; bypass is not exercised | **PASS** | #192–#194 `mergeStateStatus=BLOCKED`; ruleset `19156572` bypass `always` recorded, not exercised |

## V6 — Restoration and governance

| ID | Check | Result |
|---|---|---|
| V6a | Controls restored and normal PR is green | **PASS** | `main` at `857a3a2`; disposable PRs closed; branches deleted |
| V6b | Protect Main required contexts remain unchanged | **PASS** | no local Protect Main/status-context changes in diff (live ruleset not proven by diff alone) |
| V6c | CodeQL remains out of scope and unchanged | **PASS** | no CodeQL workflow/ruleset edits in diff |
| V6d | No collection census, runtime, or production-data change slipped in | **PASS** | diff scope lock held |

## V7 — Independent sign-off

| ID | Check | Result |
|---|---|---|
| V7a | Reviewer records written PASS/FAIL naming exact tip SHA and residuals | **PENDING** | post-PR / Ryan GATE |
| V7b | Ryan records the merge/closeout GATE | **PASS** | [#191](https://github.com/alanmz-crypto/convmem/pull/191) squash-merged 2026-08-16 |

## Evidence log

```text
VERIFY-pinwheel-pytest-ci — merge 857a3a2; disposable b4d2fbc / 003a449 / aae0e20 — Cursor — 2026-08-16T13:45Z
V0: PASS — V0d Ryan authorized disposable controls; scope lock held.
V1-V2: PASS — exact pin, logs, manifest checker, 21 contract tests.
V3: PASS — #191 green CI; merge 857a3a2.
V4: PASS — local contract negative controls.
V5: PASS — #192–#194 failed pytest (3.12); merge BLOCKED; bypass unused; branches deleted.
V6: PASS — main at 857a3a2; disposable resources removed.
Mechanical: PASS
Sign-off: V7a pending Kiro at merge SHA 857a3a2
Ryan GATE: #191 merged; arc evidence complete pending V7a
```
