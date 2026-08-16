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
| `main` | `bc83c85d0522023ea6e404bff4aaed135c47815a`, PR #189 merge |
| `.github/workflows/pylint.yml` | Existing Pylint and pytest jobs; pytest unpinned |
| `tests/ci-critical-invariants.txt` | 15 advisory modules on `main`; remains 15 until implementation adds the contract test atomically |
| `Protect Main` ruleset `19156572` | Active; requires exactly `pylint (3.12)` and `pytest (3.12)`; unchanged by this arc |
| CodeQL | Passing checks observed, not required; out of scope |
| Pinwheel implementation | Complete locally on `fix/2026-08-16-pinwheel-pytest-ci` |
| Pinwheel docs | This STATUS, Architecture, Execution, VERIFY, and handoff are the planning package |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Kiro architecture review | PASS with execution conditions | incorporated below |
| ChatGPT architecture review | PASS with conditions | incorporated below |
| Planning package | In progress on this branch | Ryan review / execution authorization |
| Cursor CI implementation | **Complete locally** | PR + disposable controls |
| Disposable Pinwheel negative controls | Not authorized | explicit Ryan grant |
| CodeQL hardening | Separate follow-on arc | Pinwheel stability |

## 5. Your Role

Codex owns the architecture, execution, VERIFY, and handoff records. Kiro and
ChatGPT provide independent design review. Ryan owns execution authorization,
disposable PR authorization, external GitHub state, and merge. Cursor owns
implementation after Ryan's grant. No actor may alter Protect Main, CodeQL, or
exercise the bypass under this arc.

## 6. What Remains Before "Live"

- [ ] Ryan reviews this planning package and authorizes execution.
- [x] Cursor selected `pytest==9.1.1` with execution-time venv evidence from a fresh Python 3.12
  install and records it in the workflow contract.
- [x] `tests/test_ci_contract.py`, checker, and 16-entry manifest added
- [x] Focused tests pass; full suite 1348 pass with 2 isolated pre-existing failures
- [ ] Ryan authorizes disposable Pinwheel controls and ordinary PR evidence. **PENDING**
- [ ] Required pytest turns red for each control, ordinary merge is blocked,
  controls are restored, and a normal green PR passes.
- [ ] VERIFY and successor handoff are updated at the verified tip.

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
