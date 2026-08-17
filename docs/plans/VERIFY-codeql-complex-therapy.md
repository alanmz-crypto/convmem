# Verify Plan: CodeQL Complex Therapy

| Field | Value |
|---|---|
| **Arc** | CodeQL Complex Therapy |
| **Phase** | Execute and planning-document closeout complete; recurring attestation future |
| **Reviewer** | Kiro exact-revision PASS; Ryan closeout and recurring-attestation owner |
| **Authority** | Live GitHub API/check-run evidence; do not trust chat claims alone |
| **Primary target** | `Protect Main` ruleset `19156572` on `refs/heads/main` |

## Consequence

This VERIFY plan distinguishes the existing advisory CodeQL behavior from the
post-Execute required-status behavior. It proves the exact status names and
producer identities, required-status membership, strict freshness semantics,
normal green behavior, a disposable red/missing CodeQL control, and restoration.
A code-scanning alert alone does not count as evidence; a failed `CodeQL`
results check does count, and its inherited current failure semantics must be
recorded without changing the threshold policy. It also tests that a
same-named status from a nonmatching producer cannot satisfy an integration-id
bound requirement, records GitHub's server-side mediation as an accepted trust
boundary, and defines a recurring post-Execute attestation rather than treating
one successful Execute as permanent proof.

## Scope lock

| In scope | Out of scope |
|---|---|
| `Protect Main` required-status membership and strict policy | Workflow edits on `main` or during planning |
| Exact live contexts `Analyze (actions)`, `Analyze (python)`, `CodeQL` | Switching default setup to advanced setup |
| Normal green PR and ordinary merge eligibility | CodeQL query/language/runner changes |
| Ryan-authorized disposable analyzer-failure PR | Changing CodeQL results thresholds or adding a native code-scanning rule |
| Ryan-authorized nonmatching-producer status probe | Scheduled automation for recurring attestation |
| Cleanup, restoration, Kiro review, and Ryan gate | Bypass exercise, runtime, Chroma, ledger, corpus, Dependabot |

## Evidence commands

Run from the exact revision under review and preserve raw output or linked
GitHub pages:

```bash
git rev-parse HEAD
git merge-base HEAD origin/main
gh api repos/alanmz-crypto/convmem/rulesets/19156572
gh run list --workflow CodeQL --limit 20 --json databaseId,displayTitle,event,headSha,createdAt,conclusion
gh pr view <pr> --json number,state,headRefOid,baseRefName,mergeStateStatus,statusCheckRollup
gh pr checks <pr>
gh api repos/alanmz-crypto/convmem/commits/<head-sha>/check-runs --paginate
gh api repos/alanmz-crypto/convmem/commits/<head-sha>/status
```

The ruleset snapshot is the authority for required membership. PR checks and
check-runs are the authority for the observed producer, conclusion, and URL.

## Verification matrix

The matrix records completed Execute evidence separately from the recurring
attestation obligation. The latter is accepted and defined, but has not yet had
its first quarterly or drift-triggered run.

### V0 — identity, authorization, and scope

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V0a | Reviewed revision is identified | Pre-correction package tip was full SHA `658a9dab9977ba03dbfc6b1301b0f6bce3762f39`; final review binds to the full post-correction pushed SHA in the Codex handoff, never an abbreviated or predecessor SHA | CORRECTED — final SHA supplied after push |
| V0b | Base is current | `git merge-base` resolves to current `origin/main` (`9c2a6784d760de6b39f154ee400033276c9b8336` at planning time) | PASS for planning package |
| V0c | No implementation slipped into planning | Diff contains only planning docs and required status-list/LATEST updates; no workflow/ruleset mutation | PASS at planning tip |
| V0d | Ryan authorized external Execute | Grant A explicitly named only ruleset `19156572`, the final five-context set, and the normal positive control; B1 and B2 were separately authorized | PASS — authorization boundaries honored |
| V0e | Same revision is used for review and evidence | Kiro reviewed the exact implementation evidence revision `d3d0bdd9986c7f77e60f956c6018493f22b784f2` and the exact planning closeout tip `cd653d95fd3dd7b3e46565c59d44134d84fae44e` | PASS — Kiro exact-revision reviews |
| V0f | Required-check latency policy is consciously selected | Ryan accepted all-three CodeQL contexts on ordinary/documentation-only PRs; PR #197 timing observations remain evidence, not an SLA | PASS — blanket policy accepted by Ryan |
| V0g | SHA lineage is independently verified | Kiro independently resolved package `c74c7f8611ac0bf563618270c2c3244715df7d67`, fetched carrier `b7c0895f7e158c30a90b77d9b211cf3a640d9438`, confirmed ancestry, inspected the 18-commit planning-only lineage, and verified the `9dfaa6722...` typo plus `790d5fd2...` correction | PASS — Kiro exact-revision recheck |

### V1 — live baseline and context identity

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V1a | Protect Main targets `main` and is active | Ruleset `19156572`, `refs/heads/main`, enforcement `active` | PASS — live capture |
| V1b | Existing required statuses are preserved | `pylint (3.12)` and `pytest (3.12)` remain in the post-patch list | PASS — Grant A pre/post snapshots |
| V1c | Strict policy is preserved | `strict_required_status_checks_policy=true` before and after | PASS — Grant A pre/post snapshots |
| V1d | Python analyzer context is exact | `Analyze (python)`, GitHub Actions app/integration `15368` | PASS — fresh PR #197 head `740424884f8921f1586f6b82648a0a290be40836` |
| V1e | Actions analyzer context is exact | `Analyze (actions)`, GitHub Actions app/integration `15368` | PASS — fresh PR #197 head `740424884f8921f1586f6b82648a0a290be40836` |
| V1f | GHAS result context is exact | `CodeQL`, GitHub Advanced Security app/integration `57789` | PASS — fresh PR #197 head `740424884f8921f1586f6b82648a0a290be40836` |
| V1g | Contexts are currently advisory | Pre-Execute ruleset has no three CodeQL entries despite fresh PR #197 passing them | PASS — live capture |
| V1h | Context identities are fresh immediately before mutation | PR #198 same-session capture matched all three CodeQL names, producer IDs, head SHA, and result URLs before the ruleset update; mismatch would have stopped mutation | PASS — Grant A pre-PATCH gate |
| V1i | Observed latency is documented without overclaim | PR #197 records approximately 40s `Analyze (actions)`, 56s `Analyze (python)`, and 3s `CodeQL`; no universal timing promise is inferred | PASS — planning evidence |
| V1j | GitHub complete-mediation boundary is explicit | The arc records GitHub's server-side current-head and matching-integration evaluation as an accepted trust boundary; B2 empirically confirms the producer-binding behavior | PASS — accepted boundary and B2 evidence |

### V2 — ruleset enforcement implementation

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V2a | Required set is exactly five contexts | Post-patch JSON and live ruleset contain Pylint, Pytest, `Analyze (actions)`, `Analyze (python)`, and `CodeQL` with integration IDs `15368`, `15368`, `15368`, `15368`, and `57789` | PASS — Grant A closeout and live ruleset |
| V2b | No unrelated ruleset policy changed | Semantic diff shows only the three CodeQL-related required-status additions; pull-request, deletion, non-fast-forward, bypass, and review-thread settings are unchanged | PASS — Grant A semantic diff |
| V2c | No workflow/default-setup change occurred | Planning and implementation evidence contain no tracked CodeQL workflow/default-setup mutation; disposable files never reached `main` | PASS — planning-only plus cleanup evidence |
| V2d | Strict policy has the correct responsibility | `strict_required_status_checks_policy=true` is preserved; required membership accounts for red/missing contexts, while strict policy supplies freshness | PASS — ruleset snapshots and B1/B2 behavior |

### V3 — positive control

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V3a | Normal PR runs every required context | PR #198 head `e023f55b4d344eea9abffda3bfc53d6b103c90a1` has all five required contexts successful | PASS — [PR #198](https://github.com/alanmz-crypto/convmem/pull/198) |
| V3b | Normal PR is ordinarily eligible | PR #198 is `CLEAN`/`MERGEABLE` without bypass | PASS — Grant A positive control |
| V3c | Check URLs map to the reviewed PR head | All five fresh check runs have SHA equal to PR #198 head `e023f55b4d344eea9abffda3bfc53d6b103c90a1` | PASS — Grant A closeout |

### V4 — disposable negative control

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V4a | Ryan authorized disposable control | Ryan separately authorized B1 and later B2; each control was limited to disposable create/close/delete and the named probe | PASS — authorization boundaries honored |
| V4b | Analyzer failure fixture is isolated | B1 attempt #2 used the authorized `actions/code-injection/critical` fixture; no established workflow, product/runtime, or data change reached `main` | PASS — [PR #200](https://github.com/alanmz-crypto/convmem/pull/200) |
| V4c | Required CodeQL context is red or missing | The genuine GHAS `CodeQL` context from integration `57789` failed on disposable head `ef07d6f2163532a3abb729f6fdb1c67c3a11862d` | PASS — B1 attempt #2 |
| V4d | CodeQL is the independent blocking cause | `CodeQL` failed, Pylint/Pytest and both analyzer contexts succeeded, and ordinary merge state was `BLOCKED` without bypass | PASS — B1 attempt #2 |
| V4e | Inherited result semantics are recorded correctly | The critical `actions/code-injection/critical` finding caused the GHAS result failure; the secondary warning was not needed; thresholds and native merge protection were unchanged | PASS — B1 evidence |
| V4f | No unapproved fallback crosses authorization | B1 attempt #1 failed isolation and was closed/deleted; B1 attempt #2 used a separately authorized fixture; no fallback or improvisation occurred | PASS — stop/reauthorize boundary honored |
| V4g | Nonmatching producer cannot satisfy a required context | On disposable head `d3d0bdd9986c7f77e60f956c6018493f22b784f2`, GHAS `CodeQL` remained failure while a same-named user status was success and the other four required contexts succeeded; merge remained blocked | PASS — B2, status `52336197622` |

### V5 — restoration and no-bypass proof

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V5a | Disposable PR was not merged | PRs #199, #200, and #201 are closed without merge; no disposable merge commit exists | PASS — cleanup evidence |
| V5b | Disposable branch/resources removed | All disposable remote branches were deleted/verified absent; no disposable worktree remains in the final handoff | PASS — B1/B2 cleanup |
| V5c | Main has no disposable fixture | The negative-control fixture is absent from `main`; disposable commits are not reachable from `main` | PASS — cleanup verification |
| V5d | Bypass was not exercised | No admin/repository-role bypass was used in Grant A, B1, or B2 | PASS — all handbacks |
| V5e | Ruleset remains intended state after cleanup | Live ruleset `19156572` retains all five contexts, `active` enforcement, `refs/heads/main`, and strict policy | PASS — fresh B2 ruleset fetch |
| V5f | Producer probe remains disposable | User status `52336197622` is retained on disposable commit `d3d0bdd...`, which is not reachable from `main` | PASS — B2 evidence |

### V6 — regression and boundary checks

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V6a | Pylint/Pytest were not weakened | Existing contexts and integration ID `15368` remain unchanged in pre/post/live ruleset evidence | PASS — Grant A closeout |
| V6b | Pinwheel/Kryptonite scope is untouched | No pytest pin, manifest, contract-test, runtime, or predecessor-gate change occurred in this arc | PASS — branch deltas and cleanup evidence |
| V6c | Default setup remains healthy | Normal CodeQL surfaces succeeded in Grant A; the existing GHAS result semantics and threshold policy were not changed | PASS — Grant A and B1 evidence |
| V6d | Dependabot scope remains separate | No unrelated Dependabot or code-scanning finding was modified or reclassified | PASS — scope evidence |

### V7 — independent sign-off and closeout

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V7a | Kiro reviews exact final revision | Kiro issued PASS at exact implementation evidence SHA `d3d0bdd9986c7f77e60f956c6018493f22b784f2` and exact planning tip `cd653d95fd3dd7b3e46565c59d44134d84fae44e` | PASS — exact-revision reviews |
| V7b | Ryan owns merge/closeout decision | Ryan ratified Grant A, authorized B1/B2 separately, and recorded the final `CLOSED/PASS` state and recurring-attestation ownership | PASS — Ryan closeout recorded |
| V7c | Handoff is recoverable | PR/evidence URLs, full implementation SHAs, cleanup results, and exact Kiro review are recorded; this commit supplies the final planning tip | PASS — closeout handoff |

### V8 — recurring enforcement attestation

These rows define continuity evidence; they do not claim that a periodic check
has already run during planning.

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V8a | Attestation owner and cadence are explicit | `OWNER=Ryan`; `CADENCE=quarterly + configuration-drift trigger`; Cursor collects evidence and Kiro reviews exceptions | ACCEPTED — first run not yet due |
| V8b | Attestation compares the externally visible contract | Future evidence captures the live ruleset, default-setup state, and recent CodeQL identities, then compares contexts, integration IDs, target, enforcement, strictness, and bypass settings to the Grant A baseline | ACCEPTED — baseline recorded; first run pending |
| V8c | Drift has a fail-closed response | Any mismatch stops automatic policy changes; Kiro reviews the exception and Ryan decides whether to update the set or reopen the arc | ACCEPTED — response defined; first run pending |

## Closeout evidence record

The following record is based on the preserved GitHub evidence and exact-revision
reviews, not on an unverified chat claim:

```text
VERIFY-codeql-complex-therapy — implementation evidence tip
`d3d0bdd9986c7f77e60f956c6018493f22b784f2` — Cursor — 2026-08-17
V0: PASS — identity, authorizations, and scope.
V1: PASS — live ruleset, fresh pre-PATCH identity gate, and exact contexts.
V2: PASS — required-status mutation and preservation.
V3: PASS — PR #198, all five statuses green and ordinarily eligible.
V4: PASS — B1 attempt #2 red CodeQL result and ordinary BLOCKED state;
    B2 producer probe also passed.
V5: PASS — PRs #199–#201 closed unmerged, resources removed, no bypass.
V6: PASS — predecessor-gate and out-of-scope regression checks.
V8: ACCEPTED — Ryan owns quarterly plus configuration-drift attestation;
    first recurring run is not yet due.
Mechanical: PASS — snapshots, raw responses, check URLs, and live ruleset
evidence are preserved in the Grant A closeout and disposable handoffs.
Sign-off: Kiro PASS at implementation SHA
`d3d0bdd9986c7f77e60f956c6018493f22b784f2` and planning SHA
`cd653d95fd3dd7b3e46565c59d44134d84fae44e`; Ryan CLOSED/PASS recorded.
```

**TL;DR:** Arc CodeQL Complex Therapy is CLOSED/PASS: Grant A, B1, and B2
evidence PASSed, the five-context ruleset is live, producer binding is proven,
and all disposable resources were removed. Ryan owns the future quarterly or
drift-triggered attestation.
