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
| `docs/inter-model/CURSOR-2026-08-16-codeql-complex-therapy-planning-handoff.md` | Complete input handoff; planning authorized, Execute not authorized |
| `docs/plans/ARCHITECTURE-codeql-complex-therapy.md` | Corrected on this planning branch; all-three context decision and inherited GHAS result semantics |
| `docs/plans/EXECUTION-codeql-complex-therapy.md` | Corrected on this planning branch; fresh stop-before-PATCH identity gate, isolated negative-control stop, and separately authorized producer probe |
| `docs/plans/VERIFY-codeql-complex-therapy.md` | Corrected on this planning branch; V0–V8 evidence matrix, future Execute/attestation rows unexecuted |
| `docs/inter-model/CODEX-2026-08-16-codeql-complex-therapy-planning-handoff.md` | Explicitly names review package SHA `c74c7f8611ac0bf563618270c2c3244715df7d67`; additive carrier for Kiro/Ryan |
| `docs/plans/STATUS-codeql-complex-therapy.md` | This current arc brief; Ryan accepted the three policy decisions, the exact disposable fixture, and conditional producer-probe authorization, with ruleset Execute authorization open |
| `.github/workflows/pylint.yml` | Existing Pylint/Pytest workflow; out of scope for this arc |
| Tracked CodeQL workflow | None; GitHub dynamic default-setup workflow is live |
| GitHub `Protect Main` ruleset `19156572` | Active; currently requires only Pylint/Pytest; no CodeQL contexts yet |
| GitHub default CodeQL setup | Configured, default query suite, standard runner |
| Disposable PR/control | Does not exist; the exact fixture and conditional producer probe are authorized, but execution is not authorized yet |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Planning authorization | **DONE** | Ryan authorized Codex planning on 2026-08-16 |
| Required CodeQL context set | **ACCEPTED by Ryan** | All three CodeQL contexts remain required alongside Pylint/Pytest; Execute is still separately unauthorized |
| GHAS result semantics | **ACCEPTED by Ryan** | Existing `CodeQL` results-check behavior is inherited; severity thresholds and the separate native merge-protection rule remain unchanged |
| Required-check latency policy | **ACCEPTED by Ryan** | Blanket all-three protection applies to documentation-only PRs; path-scoped/placeholder architecture is deferred unless latency becomes a separately authorized problem |
| Disposable negative control | **AUTHORIZED by Ryan — NOT STARTED** | Only `.github/workflows/codeql-negative-control.yml`; failed isolation with green Pylint/Pytest requires close/delete and stop; no improvisation |
| Live context capture | **DONE** | Fresh PR #197: `Analyze (actions)`, `Analyze (python)`, `CodeQL`; Execute must repeat before PATCH |
| Architecture package | **CORRECTED on planning branch** | Kiro/Ryan review |
| Execution package | **CORRECTED on planning branch** | Kiro/Ryan review and Execute grant |
| VERIFY package | **CORRECTED on planning branch** | Execute evidence; CodeQL causality, producer binding, and V8 continuity rows required |
| STATUS package/list updates | **CORRECTED on planning branch** | Review/merge |
| SHA-bound Codex handoff | **READY on planning branch** | Kiro adversarial review |
| SHA lineage audit | **NOT RECORDED** | Kiro must independently resolve the package and current remote carrier; the transient `9dfaa6722...` typo is review evidence, not authority |
| Ruleset mutation | **NOT STARTED** | Separate Ryan Execute authorization; Cursor |
| Normal positive control | **NOT STARTED** | Ruleset mutation and a green PR |
| Disposable negative-control evidence | **NOT STARTED** | Exact fixture is authorized; requires exactly one red/missing CodeQL context with Pylint/Pytest green, otherwise close/delete and stop |
| Producer-identity probe | **AUTHORIZED by Ryan — CONDITIONAL / NOT STARTED** | Run only after the fixture isolates exactly one red/missing CodeQL context and the other four required contexts are green; post one same-named green status through the ordinary authenticated user session, then stop on any non-isolated or inconclusive result |
| Recurring enforcement attestation | **PLANNED** | Named owner, quarterly cadence, baseline, and fail-closed drift response must be recorded |
| Restoration and arc closeout | **NOT STARTED** | Positive/negative evidence; Kiro/Ryan |

## 5. Your Role (read this to know what you're here to do)

If you are reviewing, inspect the four planning files plus the SHA-bound Codex
handoff and verify that Ryan's accepted all-three context, inherited-GHAS
semantics, and blanket-latency decisions are supported by fresh PR/check-run
evidence, that
requiring `CodeQL` intentionally inherits its current results-check failure
semantics, that required-status membership is distinguished from strict
freshness, and that the negative control can prove a red/missing required status
without entering `main`. The review must also decide whether to authorize the
nonmatching-producer probe, record GitHub's server-side mediation as an accepted
trust boundary, choose the latency policy, and assign the recurring attestation.
Kiro must independently resolve the package and remote carrier SHAs; the
intermediate mistyped package string is part of the review evidence.

If Ryan has granted Execute, Cursor owns the bounded ruleset mutation and the
separately authorized disposable controls. Preserve exact snapshots and do not
edit workflows or broaden the scope.

If Execute evidence exists, Kiro reviews the same final revision and Ryan owns
the merge and arc closeout. Do not treat a passing chat report as verification.

## 6. What Remains Before "Live" (sequential)

- [ ] Kiro/Ryan review the architecture, execution, VERIFY, STATUS, and
  SHA-bound handoff package; Ryan's accepted trust boundary and conditional
  producer-probe authorization are recorded, while the recurring-attestation
  owner remains open.
- [ ] Kiro independently verifies the package SHA, the remote branch tip, and
  the `git log` lineage, including the transient `9dfaa6722...` typo and
  corrective `790d5fd2...` commit.
- [ ] Ryan separately authorizes Cursor to patch `Protect Main` with the exact
  five-context required-status set.
- [ ] Cursor captures before/after ruleset snapshots and proves a normal green
  PR on all five contexts.
- [ ] Cursor creates only the exact Ryan-authorized disposable fixture and
  proves a red/missing CodeQL context blocks ordinary merge; failed isolation
  with green Pylint/Pytest requires close/delete and stop.
- [ ] If the exact fixture technically isolates one CodeQL-required context,
  Cursor proves a same-named nonmatching-producer status cannot satisfy the
  CodeQL requirement; otherwise close/delete the disposable PR and record the
  probe as not run/inconclusive, not silently marked PASS.
- [ ] Kiro reviews the exact final revision and evidence.
- [ ] Ryan merges and closes the arc; STATUS and LATEST are then updated to the
  post-close current state.

## 7. Hard Stops (models cannot cross)

| Stop | Gate owner | What it blocks |
|---|---|---|
| Planning-only boundary | Ryan | Ruleset mutation, workflow edits, and disposable PRs before Execute |
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

**TL;DR:** Ryan has conditionally authorized the producer-identity probe after
the exact disposable fixture isolates one CodeQL failure with the other four
required contexts green; recurring attestation and ruleset Execute authorization
remain open.
