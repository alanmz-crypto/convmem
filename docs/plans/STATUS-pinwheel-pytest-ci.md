# Arc Brief — Pinwheel Pytest CI

> Every model working on this arc must read this file before acting.

## 1. What This Is For (product goal)

ConvMem's required Python 3.12 pytest job currently installs the latest
available pytest on each clean runner, and its critical-test inventory is only
advisory. Pinwheel makes the existing behavioral gate reproducible and makes
the named catastrophic-invariant modules fail closed when they disappear,
rename, or collect no tests.

**Done means:** both CI jobs use one documented exact pytest pin; both jobs
log the installed version; the required pytest job checks every manifest path
individually with pytest collection; a CI-contract test protects the full
pytest command and manifest-checker invocation; and the verification package
proves broken controls fail without changing Protect Main or CodeQL.

## 2. System Design (how the pieces connect)

```
workflow install -> exact pytest pin -> version log
                                      |
                                      v
                         pytest (3.12) required status
                                      |
             +------------------------+------------------------+
             |                                                 |
  test_ci_contract.py                              manifest checker step
  protects pins, full pytest                       per path: exists +
  command, checker invocation                      pytest --collect-only
             |                                                 |
             +------------------------+------------------------+
                                      v
                              full python -m pytest -q
```

The checker is an explicit CI step for clear failure messages. Its unit and
contract coverage lives in `tests/test_ci_contract.py`, which is added to the
critical manifest at implementation time, taking the manifest from 15 to 16
entries. The checker accepts only repository-relative pytest module paths,
rejects malformed or duplicate entries, and treats only pytest exit code 0 as
successful collection.

## 3. What Exists Right Now

| Surface | State |
|---|---|
| `main` | `857a3a2` — Pinwheel [#191](https://github.com/alanmz-crypto/convmem/pull/191) merged |
| `.github/workflows/pylint.yml` | Pinwheel: `pytest==9.1.1`, version logs, checker, full suite |
| `tests/ci-critical-invariants.txt` | 16 enforced modules including `tests/test_ci_contract.py` |
| `Protect Main` ruleset `19156572` | Active; requires exactly `pylint (3.12)` and `pytest (3.12)`; unchanged by this arc |
| CodeQL | Passing checks observed, not required; out of scope |
| Pinwheel implementation | **Merged** [#191](https://github.com/alanmz-crypto/convmem/pull/191) |
| Pinwheel docs | This STATUS, Architecture, Execution, VERIFY, and handoff are the planning package |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Kiro architecture review | PASS with execution conditions | incorporated below |
| ChatGPT architecture review | PASS with conditions | incorporated below |
| Planning package | Complete on `main` | — |
| Cursor CI implementation | **MERGED** [#191](https://github.com/alanmz-crypto/convmem/pull/191) | — |
| Disposable Pinwheel negative controls | **PASS** | #192–#194 closed without merge |
| CodeQL hardening | Separate follow-on arc | Pinwheel stability |

## 5. Your Role

**Arc closed 2026-08-16.** Reference only. Successor: CodeQL Complex Therapy (separate arc).

## 6. What Remains Before "Live"

All milestones complete. Gate is live on `main`.

## 7. Hard Stops

| Stop | Owner | Effect |
|---|---|---|
| Fresh-main branch | Ryan / Codex | No work from the old Kryptonite checkout |
| Exact version selection | Cursor, recorded for review | Do not guess or use a floating constraint |
| Disposable PRs | Ryan | No external negative-control resources without grant |
| Protect Main / CodeQL | Ryan, separate arc | Pinwheel cannot change governance |
| Admin bypass | Nobody as evidence | It remains documented but unused |
| Collection census | Architecture scope lock | Explicit manifest only; no total-count floor |

## 8. Relationship to ConvMem

Pinwheel hardens the existing behavioral merge gate. It does not change
runtime behavior, retrieval, Chroma, the ledger, CodeQL analysis, or required
status contexts. CodeQL Complex Therapy remains a later security-governance
arc with its own architecture and external authorization.

## 9. Key Design Files

| Purpose | Path |
|---|---|
| Architecture | `docs/plans/ARCHITECTURE-pinwheel-pytest-ci.md` |
| Execution | `docs/plans/EXECUTION-pinwheel-pytest-ci.md` |
| Verification | `docs/plans/VERIFY-pinwheel-pytest-ci.md` |
| Current handoff | `docs/inter-model/CODEX-2026-08-15-pinwheel-pytest-ci-handoff.md` |
| Existing gate baseline | `docs/plans/ARCHITECTURE-ci-behavioral-merge-gate.md` |
| Existing manifest | `tests/ci-critical-invariants.txt` |

## 10. How to Update This Brief

Keep this file a current-state snapshot. Overwrite sections 3–6 when the
branch, review, implementation, or verification state changes. Do not append
session narrative. Add one milestone-level line below per update.

## Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-16 | Codex | Created Pinwheel planning brief after Kiro and ChatGPT PASS-with-conditions reviews; locked contract and exit-status requirements |

| 2026-08-16 | Cursor | Implementation + local verification on `fix/2026-08-16-pinwheel-pytest-ci`; V0d/V3d/V5c-V6a pending external controls |
| 2026-08-16 | Cursor | Rebased onto `3453a3f`; pin-contract gaps closed; PR [#191](https://github.com/alanmz-crypto/convmem/pull/191) opened (V3d CI_PENDING) |
| 2026-08-16 | Cursor | Disposable controls #192–#194 PASS; VERIFY/LATEST closeout; V7a Kiro pending |
| 2026-08-16 | Kiro | V7a PASS at merge SHA `857a3a2`; Ryan arc-close (V7b) pending |
