# Verify Plan: CodeQL Complex Therapy

| Field | Value |
|---|---|
| **Arc** | CodeQL Complex Therapy |
| **Phase** | Verification plan; Execute evidence is not yet collected |
| **Reviewer** | Independent reviewer on the exact final revision; Kiro sign-off and Ryan merge gate |
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

“Planned” means the row must be executed after Ryan grants Execute; it is not a
claim that the future row has already passed.

### V0 — identity, authorization, and scope

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V0a | Reviewed revision is identified | Pre-correction package tip was full SHA `658a9dab9977ba03dbfc6b1301b0f6bce3762f39`; final review binds to the full post-correction pushed SHA in the Codex handoff, never an abbreviated or predecessor SHA | CORRECTED — final SHA supplied after push |
| V0b | Base is current | `git merge-base` resolves to current `origin/main` (`9c2a6784d760de6b39f154ee400033276c9b8336` at planning time) | PASS for planning package |
| V0c | No implementation slipped into planning | Diff contains only planning docs and required status-list/LATEST updates; no workflow/ruleset mutation | PASS at planning tip |
| V0d | Ryan authorized external Execute | Explicit Ryan grant names ruleset `19156572`, final context set, and disposable-control phase | PLANNED — Ryan gate |
| V0e | Same revision is used for review and evidence | Kiro reviews the exact full pushed correction tip named in the Codex handoff; no stale branch claim | PLANNED |
| V0f | Required-check latency policy is consciously selected | Ryan records either acceptance of all-three CodeQL contexts on ordinary/documentation-only PRs, with PR #197 observations (40s/56s/3s CodeQL surfaces) treated as evidence, not an SLA, or selection of a path-scoped alternative that reopens workflow/architecture scope | PLANNED — Ryan planning gate |
| V0g | SHA lineage is independently verified | Kiro runs `git fetch origin`, resolves the package SHA with `git rev-parse`, inspects `git log origin/main..origin/plan/2026-08-16-codeql-complex-therapy --oneline`, resolves the current remote tip independently, and records the transient `9dfaa6722...` typo plus its `790d5fd2...` correction as process evidence | PLANNED — Kiro mandatory |

### V1 — live baseline and context identity

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V1a | Protect Main targets `main` and is active | Ruleset `19156572`, `refs/heads/main`, enforcement `active` | PASS — live capture |
| V1b | Existing required statuses are preserved | `pylint (3.12)` and `pytest (3.12)` remain in the post-patch list | PLANNED |
| V1c | Strict policy is preserved | `strict_required_status_checks_policy=true` before and after | PLANNED |
| V1d | Python analyzer context is exact | `Analyze (python)`, GitHub Actions app/integration `15368` | PASS — fresh PR #197 head `740424884f8921f1586f6b82648a0a290be40836` |
| V1e | Actions analyzer context is exact | `Analyze (actions)`, GitHub Actions app/integration `15368` | PASS — fresh PR #197 head `740424884f8921f1586f6b82648a0a290be40836` |
| V1f | GHAS result context is exact | `CodeQL`, GitHub Advanced Security app/integration `57789` | PASS — fresh PR #197 head `740424884f8921f1586f6b82648a0a290be40836` |
| V1g | Contexts are currently advisory | Pre-Execute ruleset has no three CodeQL entries despite fresh PR #197 passing them | PASS — live capture |
| V1h | Context identities are fresh immediately before mutation | Execute resolves the newest current PR run and rechecks names, app IDs, head SHA, and URLs in the same session before PATCH; mismatch stops mutation | PLANNED — mandatory stop-before-PATCH gate |
| V1i | Observed latency is documented without overclaim | PR #197 records approximately 40s `Analyze (actions)`, 56s `Analyze (python)`, and 3s `CodeQL`; no universal timing promise is inferred | PASS — planning evidence |
| V1j | GitHub complete-mediation boundary is explicit | Review records that current-head, matching-integration ruleset evaluation is trusted server behavior; the arc does not claim to inspect GitHub's internal caching/revalidation on every future re-push | PLANNED — accepted trust boundary |

### V2 — ruleset enforcement implementation

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V2a | Required set is exactly five contexts | Post-patch JSON contains Pylint, Pytest, `Analyze (actions)`, `Analyze (python)`, and `CodeQL`, with recorded integration ids | PLANNED |
| V2b | No unrelated ruleset policy changed | Semantic diff shows only required-status additions; pull-request, deletion, non-fast-forward, bypass, and review-thread settings unchanged | PLANNED |
| V2c | No workflow/default-setup change occurred | Git diff and GitHub workflow/config snapshots show no CodeQL workflow or default-setup edit | PLANNED |
| V2d | Strict policy has the correct responsibility | `strict_required_status_checks_policy=true` is preserved and evidence shows freshness/up-to-date behavior; required membership, not strict alone, accounts for red/missing contexts | PLANNED |

### V3 — positive control

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V3a | Normal PR runs every required context | `gh pr checks <positive-pr>` shows all five successful | PLANNED |
| V3b | Normal PR is ordinarily eligible | PR merge state is not blocked by required checks; no bypass used | PLANNED |
| V3c | Check URLs map to the reviewed PR head | Check-run SHA, PR head SHA, and captured URLs agree | PLANNED |

### V4 — disposable negative control

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V4a | Ryan authorized disposable control | Authorization names the PR/branch purpose and permits create/close/delete only | PLANNED — separate Ryan gate |
| V4b | Analyzer failure fixture is isolated | The only currently authorized fixture is `.github/workflows/codeql-negative-control.yml` with `name: [codeql-negative-control`; no established workflow, product/runtime, or data change | PLANNED |
| V4c | Required CodeQL context is red or missing | `Analyze (actions)`, `Analyze (python)`, or `CodeQL` is failed/absent in the check-run evidence; fixture mechanism is recorded | PLANNED |
| V4d | CodeQL is the independent blocking cause | At least one CodeQL-required context is red/absent, both pre-existing `pylint (3.12)` and `pytest (3.12)` contexts are successful, and PR `mergeStateStatus`/equivalent reports blocked or unsatisfied without bypass | PLANNED |
| V4e | Inherited result semantics are recorded correctly | A green alert-only result is not red evidence; a red `CodeQL` result is valid only with its check conclusion, finding/threshold behavior, and ordinary blocked state recorded; no threshold is changed | PLANNED |
| V4f | No unapproved fallback crosses authorization | If the isolated fixture fails to produce a meaningful CodeQL failure, or Pylint/Pytest are not successful, close/delete the disposable PR and obtain new Ryan authorization before any different fixture | PLANNED |
| V4g | Nonmatching producer cannot satisfy a required context | On the same disposable head, exactly one CodeQL-required context is red/absent, the other four required contexts are successful, and a same-named green Statuses-API result from a user/nonmatching producer is present; ordinary merge remains blocked | PLANNED — separate Ryan producer-probe gate |

### V5 — restoration and no-bypass proof

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V5a | Disposable PR was not merged | Closed PR state and absent merge commit | PLANNED |
| V5b | Disposable branch/resources removed | Remote branch deletion and local worktree cleanup recorded | PLANNED |
| V5c | Main has no disposable fixture | `git show origin/main:<fixture>` fails because the file never entered `main` | PLANNED |
| V5d | Bypass was not exercised | No admin/repository-role bypass action in the evidence; any observed capability is noted only | PLANNED |
| V5e | Ruleset remains intended state after cleanup | Final snapshot still has the exact five contexts and strict policy | PLANNED |
| V5f | Producer probe remains disposable | Status URL/creator evidence is retained, the spoofed status is attached only to a disposable commit, and that commit is not reachable from `main` | PLANNED |

### V6 — regression and boundary checks

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V6a | Pylint/Pytest were not weakened | Existing contexts and their integration ids remain unchanged | PLANNED |
| V6b | Pinwheel/Kryptonite scope is untouched | No workflow, pytest pin, manifest, or contract-test changes in this arc | PLANNED |
| V6c | Default setup remains healthy | GitHub reports configured default setup, successful normal CodeQL run, and no changed results-threshold policy | PLANNED |
| V6d | Dependabot scope remains separate | Critical alert is not modified or reclassified by this work | PLANNED |

### V7 — independent sign-off and closeout

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V7a | Kiro reviews exact final revision | Written PASS/FAIL on the pushed tip, including any conditions | PLANNED |
| V7b | Ryan owns merge/closeout decision | Ryan approves documentation/implementation merge and records arc closeout | PLANNED |
| V7c | Handoff is recoverable | Branch, full tip SHA, `origin/main..HEAD` log, explicit push result, and lowest-effort review links | PLANNED |

### V8 — recurring enforcement attestation

These rows define continuity evidence; they do not claim that a periodic check
has already run during planning.

| ID | Check | Expected evidence | Planning state |
|---|---|---|---|
| V8a | Attestation owner and cadence are explicit | A named owner records a quarterly manual review, plus an immediate review after a ruleset, default-setup, CodeQL workflow-language, or integration-id change | PLANNED — post-Execute operations gate |
| V8b | Attestation compares the externally visible contract | The review captures `gh api repos/alanmz-crypto/convmem/rulesets/19156572`, default-setup state, and recent CodeQL check identities, then diffs required contexts, integration ids, target, enforcement, strict policy, and bypass settings against the recorded baseline | PLANNED — post-Execute operations gate |
| V8c | Drift has a fail-closed response | Any mismatch opens review and stops automatic policy changes; Ryan/Kiro decide whether to update the required set or re-open this arc | PLANNED — post-Execute operations gate |

## Evidence log template

Populate this block only after Execute; do not backfill future results from chat
claims:

```text
VERIFY-codeql-complex-therapy — implementation tip <full SHA> — Cursor — <UTC>
V0: <PASS/FAIL> — identity, authorizations, and scope.
V1: <PASS/FAIL> — live ruleset, fresh pre-PATCH identity gate, and exact contexts.
V2: <PASS/FAIL> — required-status mutation and preservation.
V3: <PASS/FAIL> — normal PR, all five statuses green.
V4: <PASS/FAIL> — disposable CodeQL analyzer failure and ordinary BLOCKED state.
V5: <PASS/FAIL> — closed/unmerged disposable resources, restoration, no bypass.
V6: <PASS/FAIL> — predecessor-gate and out-of-scope regression checks.
V8: <PASS/FAIL> — recurring attestation owner, cadence, baseline, and drift response.
Mechanical: <PASS/FAIL> — commands, snapshots, and links are reproducible.
Sign-off: Kiro <PASS/FAIL> at <revision>; Ryan gate <state>.
```

**TL;DR:** Verify the exact five-context ruleset, distinguish required-status
membership from strict freshness, test nonmatching-producer rejection, record
GitHub's mediation boundary, define recurring attestation, and prove a
Ryan-authorized red/missing disposable control is ordinarily blocked.
