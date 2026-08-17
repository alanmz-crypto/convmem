# Arc Brief — CodeQL Complex Therapy

> Every model working on this arc must read this file at session start. It is a
> current-state snapshot, not a session diary.

## 1. What This Is For (product goal)

ConvMem's `main` branch has required Pylint and Pytest checks, but CodeQL runs
on pull requests as an advisory result. The arc makes the live CodeQL analysis
contract part of ordinary merge protection, intentionally inheriting the
current GHAS `CodeQL` results-check failure semantics without changing the
results threshold, CodeQL workflow, query policy, or repository bypass policy.

**Done means:** `Protect Main` strictly requires the existing Pylint/Pytest
contexts plus the live CodeQL contexts `Analyze (actions)`, `Analyze (python)`,
and `CodeQL`; a normal PR is green; a disposable CodeQL analysis failure or
missing required status is ordinarily blocked; strict policy additionally
requires freshness against the current base; disposable resources are removed;
and Kiro/Ryan review the exact final SHA and evidence.

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
                five required statuses are present/successful;
                    strict=true also requires fresh base
```

The CodeQL workflow is dynamically provided by GitHub; no tracked CodeQL
workflow exists in this repository. The planning package changes only the
required-status membership in `Protect Main` during a separately authorized
Execute phase.

## 3. What Exists Right Now (file and live-surface map)

| Surface | State |
|---|---|
| `docs/plans/ARCHITECTURE-codeql-complex-therapy.md` | Architecture locked; all-three context decision and inherited GHAS result semantics remain the governing design |
| `docs/plans/EXECUTION-codeql-complex-therapy.md` | Execution and cleanup reconciled below; no further mutation is authorized |
| `docs/plans/VERIFY-codeql-complex-therapy.md` | Grant A/B1/B2 evidence recorded; first recurring attestation remains future operational work |
| `docs/plans/STATUS-codeql-complex-therapy.md` | This current arc brief; closeout is awaiting Kiro review of the final planning tip and Ryan's final state record |
| `docs/inter-model/LATEST.md` | Closeout pointer updated in the same docs-only pass |
| `AGENTS.md` / `config/agent-protocol.md` | CodeQL arc state updated from planning-authorized to closeout/closed pending final review |
| `.github/workflows/pylint.yml` | Existing Pylint/Pytest workflow; unchanged and out of scope |
| Tracked CodeQL workflow | None; GitHub dynamic default-setup workflow remains live |
| GitHub `Protect Main` ruleset `19156572` | Active; requires Pylint, Pytest, `Analyze (actions)`, `Analyze (python)`, and `CodeQL` with integration IDs `15368`, `15368`, `15368`, `15368`, and `57789`; strict policy remains true |
| Positive control PR #198 | Five checks green and ordinarily merge-eligible; evidence retained in the Grant A closeout |
| Disposable PRs #199, #200, and #201 | Closed without merge; branches and fixture resources removed; no disposable commit reached `main` |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Planning authorization | **DONE** | Ryan authorized Codex planning |
| Required CodeQL context set | **DONE** | Five-context set is live in `Protect Main` |
| GHAS result semantics | **DONE** | Existing results-check behavior inherited; thresholds and native merge-protection rule unchanged |
| Required-check latency policy | **DONE** | Blanket all-three protection accepted for documentation-only PRs |
| Live context capture | **DONE** | Fresh Grant A capture matched names, producer IDs, head SHA, and URLs |
| Ruleset mutation | **GRANT A CLOSED/PASS** | Five required contexts installed; PATCH 404 → one documented PUT 200; deviation ratified |
| Normal positive control | **GRANT A CLOSED/PASS** | PR #198 all five checks green; ordinary merge eligible without bypass |
| Disposable negative control attempt #1 | **FAIL/CLOSED** | Malformed YAML left all five checks green; PR #199 closed, branch removed, new authorization obtained |
| Disposable negative control attempt #2 | **PASS/CLOSED** | PR #200 produced 1-red/4-green; ordinary merge blocked; PR and branch removed |
| Producer-identity probe | **B2 PASS/CLOSED** | User `CodeQL` success did not satisfy GHAS integration `57789`; PR #201 and branch removed |
| Kiro evidence review | **PASS** | Exact implementation SHA `d3d0bdd9986c7f77e60f956c6018493f22b784f2`; final planning-tip review remains |
| Recurring enforcement attestation | **ACCEPTED by Ryan** | `OWNER=Ryan`; `CADENCE=quarterly + configuration-drift trigger`; first run is not yet due |
| Restoration and arc closeout | **IN PROGRESS** | Kiro reviews this final planning tip; Ryan records final `CLOSED/PASS` state |

## 5. Your Role (read this to know what you're here to do)

The execution lane is complete. Kiro's remaining role is a read-only exact-SHA
review of this closeout revision: confirm that the planning records accurately
map Grant A, B1 attempt #1, B1 attempt #2, and B2 to the preserved evidence, and
that no stale authorization or "not started" claim remains. Kiro does not rerun
the controls or mutate GitHub.

Ryan then owns the final arc state and the recurring policy gate. Cursor may
collect the quarterly or configuration-drift evidence; Kiro reviews exceptions;
Ryan decides whether drift requires a new authorization or a reopened arc.
The first attestation is not part of this closeout and no scheduled workflow is
being added.

## 6. What Remains Before "Live" (sequential)

- [x] Grant A ruleset mutation, PUT-deviation ratification, and positive control.
- [x] B1 attempt #1 safe failure and cleanup.
- [x] B1 attempt #2 1-red/4-green negative control and cleanup.
- [x] B2 producer-identity probe, cleanup, and remote-branch absence verification.
- [x] Kiro PASS on the exact implementation evidence SHA.
- [ ] Kiro reviews the exact full SHA of this final planning-document closeout.
- [ ] Ryan records the final `CLOSED/PASS` arc state after that review.
- [ ] Ryan's first quarterly or configuration-drift attestation, when due.

## 7. Hard Stops (models cannot cross)

| Stop | Gate owner | What it blocks |
|---|---|---|
| Grant boundary | Ryan | Any mutation outside Grant A; all workflow edits, disposable PRs, and Grant B actions until separately granted |
| Exact external resource/value | Ryan | Any mutation other than `Protect Main` `19156572` with the named final contexts |
| CodeQL workflow/default setup | Ryan/separate scope | Workflow, language, query, runner, results-threshold, or setup changes |
| Native code-scanning rule | Ryan/separate scope | Adding the separate alert/security-severity ruleset rule |
| Bypass policy | Ryan | Admin/repository-role bypass use or policy changes as proof |
| Negative-control integrity | Cursor/Kiro | Calling a green alert-only fixture or unobserved hypothesis a pass |
| Producer identity | Ryan/Cursor/Kiro | Posting a same-named status outside the conditional probe authorization or treating a non-isolated result as proof |
| Arc boundary | Ryan | Dependabot, runtime, corpus, Chroma, ledger, Pinwheel, or Kryptonite work |

## 8. Relationship to ConvMem (the bigger picture)

```text
ConvMem merge governance:
├── CI Kryptonite — closed behavioral pytest gate
├── Pinwheel Pytest CI — closed reproducible pytest gate
└── CodeQL Complex Therapy — this arc: required CodeQL completion statuses
```

This arc depends on the existing CI gates but does not modify them. It makes
security-analysis completion and the existing GHAS `CodeQL` results-check
semantics part of the same ordinary merge contract while leaving threshold
changes, native code-scanning rules, and broad dependency remediation for
separate decisions.

## 9. Key Design Files (for deep dives)

| Purpose | Path |
|---|---|
| Planning handoff | [`docs/inter-model/CURSOR-2026-08-16-codeql-complex-therapy-planning-handoff.md`](../inter-model/CURSOR-2026-08-16-codeql-complex-therapy-planning-handoff.md) |
| Architecture | [`docs/plans/ARCHITECTURE-codeql-complex-therapy.md`](ARCHITECTURE-codeql-complex-therapy.md) |
| Execution | [`docs/plans/EXECUTION-codeql-complex-therapy.md`](EXECUTION-codeql-complex-therapy.md) |
| Verification | [`docs/plans/VERIFY-codeql-complex-therapy.md`](VERIFY-codeql-complex-therapy.md) |
| Ryan/Kiro handoff | [`docs/inter-model/CODEX-2026-08-16-codeql-complex-therapy-planning-handoff.md`](../inter-model/CODEX-2026-08-16-codeql-complex-therapy-planning-handoff.md) |
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
| 2026-08-16 | Codex | Applied conditional-pass corrections: inherited GHAS result semantics, full-SHA binding, strict-freshness wording, fresh pre-PATCH identity gate, and concrete disposable fixtures |
| 2026-08-16 | Codex | Removed the tracked-workflow fallback and required CodeQL-independent causality with Pylint/Pytest successful |
| 2026-08-16 | Codex | Added SHA-bound Ryan/Kiro handoff and explicit required-check latency decision gate |

| 2026-08-16 | Codex | Added GitHub mediation trust boundary, separately authorized producer-identity probe, V8 recurring attestation, and path-scoped latency alternative |
| 2026-08-16 | Codex | Bound the hardening package and review carrier to full SHA `190c4683f452c1a2f70ae7630269d92658eb8974` |
| 2026-08-16 | Codex | Added mandatory independent SHA-lineage verification after the transient handoff typo was corrected |
| 2026-08-16 | Codex | Bound the SHA-lineage package and incident-aware review carrier to full SHA `c74c7f8611ac0bf563618270c2c3244715df7d67` |
| 2026-08-16 | Ryan | Accepted all three CodeQL contexts alongside the existing Pylint/Pytest requirements; Execute remains separately unauthorized |
| 2026-08-16 | Ryan | Accepted existing GHAS `CodeQL` results-check semantics; no severity-threshold or native merge-protection rule change |
| 2026-08-16 | Ryan | Accepted blanket all-three CodeQL protection on documentation-only PRs; path-scoped architecture deferred unless latency becomes a real problem |
| 2026-08-16 | Ryan | Authorized only `.github/workflows/codeql-negative-control.yml` for the disposable negative control; no improvisation or fallback |
| 2026-08-16 | Ryan | Conditionally authorized the producer-identity probe because integration IDs are part of the required-status security claim; run only after one isolated CodeQL failure with the other four required contexts green |
| 2026-08-16 | Ryan | Set recurring attestation `OWNER=Ryan`, `CADENCE=quarterly + configuration-drift trigger`; Cursor collects evidence and Kiro reviews exceptions |
| 2026-08-16 | Kiro | PASS on independent SHA-lineage recheck at exact carrier `b7c0895f7e158c30a90b77d9b211cf3a640d9438`; package ancestry, 18-commit planning-only delta, and `9dfaa6722...` → `790d5fd2...` incident verified; Execute remains unauthorized |
| 2026-08-16 | Ryan | Authorized Execute Grant A for ruleset-only `Protect Main` mutation and the normal five-check positive control; Grant B disposable testing remains withheld |
| 2026-08-17 | Codex | Reconciled Grant A/B1/B2 execution evidence, cleanup, Kiro B2 PASS, and Ryan's recurring-attestation contract; final docs-only closeout review remains |

**TL;DR:** Grant A, B1, and B2 are complete and cleaned up; the five-context
ruleset is live, Kiro PASSed the exact implementation evidence, and only the
final planning-tip review plus Ryan's closeout record remain.
