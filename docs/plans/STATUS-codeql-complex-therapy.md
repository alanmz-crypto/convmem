# Arc Brief — CodeQL Complex Therapy

> Every model working on this arc must read this file at session start. It is a
> current-state snapshot, not a session diary.

## 1. What This Is For (product goal)

ConvMem's `main` branch has required Pylint and Pytest checks, but CodeQL runs
on pull requests as an advisory result. The arc makes the live CodeQL analysis
contract part of ordinary merge protection without changing the CodeQL workflow,
query policy, or repository bypass policy.

**Done means:** `Protect Main` strictly requires the existing Pylint/Pytest
contexts plus the live CodeQL contexts `Analyze (actions)`, `Analyze (python)`,
and `CodeQL`; a normal PR is green; a disposable CodeQL analysis failure or
missing required status is ordinarily blocked; disposable resources are removed;
and Kiro/Ryan review the exact evidence.

## 2. System Design (how the pieces connect)

```text
                         GitHub Advanced Security
                    default setup: configured / standard
                                  │
                ┌─────────────────┼──────────────────┐
                ▼                 ▼                  ▼
       Analyze (actions)  Analyze (python)          CodeQL
       Actions app 15368  Actions app 15368  GHAS app 57789
                └─────────────────┼──────────────────┘
                                  ▼
                         Protect Main 19156572
                    refs/heads/main, strict=true
                                  │
                ┌─────────────────┼──────────────────┐
                ▼                 ▼                  ▼
          pylint (3.12)     pytest (3.12)       CodeQL set
                                  │
                                  ▼
                  ordinary merge eligible only when all
                     five required statuses are successful
```

The CodeQL workflow is dynamically provided by GitHub; no tracked CodeQL
workflow exists in this repository. The planning package changes only the
required-status membership in `Protect Main` during a separately authorized
Execute phase.

## 3. What Exists Right Now (file and live-surface map)

| Surface | State |
|---|---|
| `docs/inter-model/CURSOR-2026-08-16-codeql-complex-therapy-planning-handoff.md` | Complete input handoff; planning authorized, Execute not authorized |
| `docs/plans/ARCHITECTURE-codeql-complex-therapy.md` | Complete on this planning branch; exact all-three context decision |
| `docs/plans/EXECUTION-codeql-complex-therapy.md` | Complete on this planning branch; separate Ryan gates for Execute/disposable controls |
| `docs/plans/VERIFY-codeql-complex-therapy.md` | Complete on this planning branch; V0–V7 evidence matrix, future rows unexecuted |
| `docs/plans/STATUS-codeql-complex-therapy.md` | This current arc brief; planning package ready for review |
| `.github/workflows/pylint.yml` | Existing Pylint/Pytest workflow; out of scope for this arc |
| Tracked CodeQL workflow | None; GitHub dynamic default-setup workflow is live |
| GitHub `Protect Main` ruleset `19156572` | Active; currently requires only Pylint/Pytest; no CodeQL contexts yet |
| GitHub default CodeQL setup | Configured, default query suite, standard runner |
| Disposable PR/control | Does not exist and is not authorized yet |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Planning authorization | **DONE** | Ryan authorized Codex planning on 2026-08-16 |
| Live context capture | **DONE** | PR #191: `Analyze (actions)`, `Analyze (python)`, `CodeQL` |
| Architecture package | **DONE on planning branch** | Ryan/Kiro review |
| Execution package | **DONE on planning branch** | Ryan/Kiro review and Execute grant |
| VERIFY package | **DONE on planning branch** | Execute evidence |
| STATUS package/list updates | **DONE on planning branch** | Review/merge |
| Ruleset mutation | **NOT STARTED** | Separate Ryan Execute authorization; Cursor |
| Normal positive control | **NOT STARTED** | Ruleset mutation and a green PR |
| Disposable negative control | **NOT STARTED** | Separate Ryan disposable-control authorization |
| Restoration and arc closeout | **NOT STARTED** | Positive/negative evidence; Kiro/Ryan |

## 5. Your Role (read this to know what you're here to do)

If you are reviewing, inspect the four planning files and verify that the
all-three context decision is supported by live PR/check-run evidence, that the
ruleset mutation is narrowly scoped, and that the negative control can prove a
red/missing required status without entering `main`.

If Ryan has granted Execute, Cursor owns the bounded ruleset mutation and the
separately authorized disposable controls. Preserve exact snapshots and do not
edit workflows or broaden the scope.

If Execute evidence exists, Kiro reviews the same final revision and Ryan owns
the merge and arc closeout. Do not treat a passing chat report as verification.

## 6. What Remains Before "Live" (sequential)

- [ ] Ryan reviews and accepts the architecture, execution, VERIFY, and STATUS
  package.
- [ ] Ryan separately authorizes Cursor to patch `Protect Main` with the exact
  five-context required-status set.
- [ ] Cursor captures before/after ruleset snapshots and proves a normal green
  PR on all five contexts.
- [ ] Ryan separately authorizes disposable controls.
- [ ] Cursor proves a red/missing CodeQL context blocks ordinary merge, then
  closes and removes the disposable resources without merging them.
- [ ] Kiro reviews the exact final revision and evidence.
- [ ] Ryan merges and closes the arc; STATUS and LATEST are then updated to the
  post-close current state.

## 7. Hard Stops (models cannot cross)

| Stop | Gate owner | What it blocks |
|---|---|---|
| Planning-only boundary | Ryan | Ruleset mutation, workflow edits, and disposable PRs before Execute |
| Exact external resource/value | Ryan | Any mutation other than `Protect Main` `19156572` with the named final contexts |
| CodeQL workflow/default setup | Ryan/separate scope | Workflow, language, query, runner, or setup changes |
| Bypass policy | Ryan | Admin/repository-role bypass use or policy changes as proof |
| Negative-control integrity | Cursor/Kiro | Calling a green alert-only fixture or unobserved hypothesis a pass |
| Arc boundary | Ryan | Dependabot, runtime, corpus, Chroma, ledger, Pinwheel, or Kryptonite work |

## 8. Relationship to ConvMem (the bigger picture)

```text
ConvMem merge governance:
├── CI Kryptonite — closed behavioral pytest gate
├── Pinwheel Pytest CI — closed reproducible pytest gate
└── CodeQL Complex Therapy — this arc: required CodeQL completion statuses
```

This arc depends on the existing CI gates but does not modify them. It makes
security-analysis completion part of the same ordinary merge contract while
leaving vulnerability alert thresholds and broad dependency remediation for
separate decisions.

## 9. Key Design Files (for deep dives)

| Purpose | Path |
|---|---|
| Planning handoff | [`docs/inter-model/CURSOR-2026-08-16-codeql-complex-therapy-planning-handoff.md`](../inter-model/CURSOR-2026-08-16-codeql-complex-therapy-planning-handoff.md) |
| Architecture | [`docs/plans/ARCHITECTURE-codeql-complex-therapy.md`](ARCHITECTURE-codeql-complex-therapy.md) |
| Execution | [`docs/plans/EXECUTION-codeql-complex-therapy.md`](EXECUTION-codeql-complex-therapy.md) |
| Verification | [`docs/plans/VERIFY-codeql-complex-therapy.md`](VERIFY-codeql-complex-therapy.md) |
| Predecessor gate | [`docs/plans/ARCHITECTURE-ci-behavioral-merge-gate.md`](ARCHITECTURE-ci-behavioral-merge-gate.md) |
| Predecessor evidence | [`docs/plans/VERIFY-ci-behavioral-merge-gate.md`](VERIFY-ci-behavioral-merge-gate.md) |
| Pinwheel boundary | [`docs/plans/VERIFY-pinwheel-pytest-ci.md`](VERIFY-pinwheel-pytest-ci.md) |
| Cross-arc current state | [`docs/inter-model/LATEST.md`](../inter-model/LATEST.md) |

## 10. How to Update This Brief (departure protocol)

Keep this file a current snapshot. Overwrite sections 3–6 when the milestone
state changes; do not append session narrative. Remove completed checklist items
when the arc advances, rewrite the next model's role, and add one milestone-level
line to the Update Log. Session details belong in Track A ingest, not here.

## Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-16 | Codex | Created the planning arc brief with live CodeQL contexts and separate Execute/disposable gates |

**TL;DR:** The planning package is complete on the plan branch; the live system
still has advisory CodeQL, and the next authorized action is Ryan/Kiro review
before Cursor Execute.
