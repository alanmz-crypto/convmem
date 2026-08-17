# Execution Plan: CodeQL Complex Therapy

| Field | Value |
|---|---|
| **Arc** | CodeQL Complex Therapy |
| **Phase** | Execute complete; Grant A and separately authorized Grant B controls completed and cleaned up |
| **Pre-correction published tip** | `658a9dab9977ba03dbfc6b1301b0f6bce3762f39` on `plan/2026-08-16-codeql-complex-therapy` |
| **Implementation lane** | Cursor completed Grant A, B1, and B2 on disposable implementation branches; all disposable branches were removed |
| **External gate owner** | Ryan |
| **Independent review** | Kiro, on the same final artifact and revision |

## Consequence

Grant A installed the three observed CodeQL contexts while preserving existing
policy and proved the normal positive case. Ryan then separately authorized B1
and B2. B1 attempt #2 proved that a qualifying GHAS CodeQL failure blocks the
ordinary merge path while the other four required contexts remain green; B2
proved that a same-named user status cannot satisfy the integration-id-bound
GHAS requirement. All disposable PRs were closed without merge and all
disposable branches were removed. No workflow, threshold, native
code-scanning rule, or bypass policy was changed.

## Phase 0 — planning review (Codex complete)

Codex has produced:

* [`ARCHITECTURE-codeql-complex-therapy.md`](ARCHITECTURE-codeql-complex-therapy.md)
  with the exact context decision and scope lock;
* this execution plan with separate Execute and disposable-control gates;
* [`VERIFY-codeql-complex-therapy.md`](VERIFY-codeql-complex-therapy.md) with
  preflight, positive, negative, restoration, and sign-off rows; and
* [`STATUS-codeql-complex-therapy.md`](STATUS-codeql-complex-therapy.md) as the
  current arc brief.
* [`CODEX-2026-08-16-codeql-complex-therapy-planning-handoff.md`](../inter-model/CODEX-2026-08-16-codeql-complex-therapy-planning-handoff.md)
  as the explicit SHA-bound carrier for Kiro/Ryan review.

The live planning evidence was taken from ruleset `19156572`, historical PR
#191, and fresh planning-time PR #197/check-runs. The planning branch contains
documentation only; it does not contain a ruleset mutation, workflow edit,
disposable fixture, or runtime change. The final review must use the full SHA
of the pushed correction tip supplied in the Codex handoff; neither `0ffdc69`
nor this pre-correction SHA is the final review binding.

## Phase 1 — Ryan planning review

Ryan reviews the four planning files and the live-context decision. Review must
explicitly answer:

1. Is the all-three context set (`CodeQL`, `Analyze (python)`, `Analyze
   (actions)`) the intended required subset for the current default setup?
2. Is ruleset-only enforcement, intentionally inheriting the current GHAS
   `CodeQL` results-check failure semantics but without adding or changing a
   native alert-threshold rule, the intended scope?
3. Is the isolated malformed-workflow disposable control acceptable, with the
   explicit stop/new-Ryan-authorization rule if it does not produce a
   red/missing required context?
4. Does Ryan accept the latency trade-off of requiring all three CodeQL
   contexts on ordinary PRs, including documentation-only PRs, based on the
   observed PR #197 timings recorded in ARCHITECTURE?
5. Does Ryan authorize the separate producer-identity probe: one same-named
   user-authenticated status on the disposable commit, only if the fixture
   isolates exactly one red/missing CodeQL context while the other four are
   green?
6. Is Cursor authorized to mutate `Protect Main` under Grant A, with the
   disposable PR/control resources held for a separate Grant B?

Ryan may also choose a path-scoped/placeholder-job policy for documentation-only
PRs instead of the blanket all-three requirement. That choice is not an
Execute approval: it reopens the architecture and workflow-scope decision and
requires a new plan before any mutation.

Ryan has accepted the all-three contexts, inherited GHAS semantics, blanket
latency, exact negative-control scope, and conditional producer-probe scope.
Grant A and the separately issued B1/B2 grants are complete. No further
execution is authorized by this document. Future work is limited to Ryan's
quarterly plus configuration-drift attestation, with Cursor collecting evidence
and Kiro reviewing exceptions.

## Phase 2 — Cursor Execute: ruleset-only mutation (COMPLETE)

Grant A completed on PR #198. The fresh same-session pre-PATCH capture matched
all five required contexts and producer IDs. The planned PATCH returned 404;
the documented ruleset endpoint was then used once via PUT, producing the
intended five-context state. Ryan ratified that narrow method deviation. The
raw pre/post snapshots, payload, responses, and semantic diff are preserved in
the Grant A closeout evidence.

Cursor works from a fresh implementation branch based on the reviewed current
`main`, records the exact branch tip, and performs these read-only checks first:

```bash
git fetch origin
git rev-parse origin/main
gh api repos/alanmz-crypto/convmem/rulesets/19156572
gh run list --workflow CodeQL --limit 20 --json databaseId,displayTitle,event,headSha,createdAt,conclusion
gh pr view <fresh-current-pr> --json number,state,headRefOid,baseRefName,updatedAt
gh pr checks <fresh-current-pr>
gh api repos/alanmz-crypto/convmem/commits/<fresh-pr-head-sha>/check-runs --paginate
```

### Phase 2a — stop-before-PATCH identity gate

Immediately before the PATCH, resolve `<fresh-current-pr>` to the newest
available current PR run from the configured default-setup CodeQL workflow. The
planning-time reference is PR #197, head
`740424884f8921f1586f6b82648a0a290be40836`, but Execute must not assume that
historical run remains current. A current PR may be the implementation/positive
control PR created under the Execute grant; if no current PR run is available,
stop before mutation rather than inventing a context identity.

The captured check-runs must contain exactly these names and producer IDs:

```text
Analyze (actions)   GitHub Actions             app/integration 15368
Analyze (python)    GitHub Actions             app/integration 15368
CodeQL              GitHub Advanced Security   app/integration 57789
```

The PR head SHA, check-run SHA, status names, app IDs, and result URLs are saved
as the pre-PATCH evidence. If any name, producer, or context differs from the
reviewed package, Cursor stops before mutating `Protect Main` and requests a
new Ryan/Kiro decision. This same-session fresh capture is mandatory even
though PR #197 has already confirmed the identities during planning.

The only authorized external ruleset mutation was one update to:

```text
`/repos/alanmz-crypto/convmem/rulesets/19156572`
```

The final `rules` payload must retain every existing rule and replace only the
`required_status_checks` list with these five entries:

```json
[
  {"context":"pylint (3.12)","integration_id":15368},
  {"context":"pytest (3.12)","integration_id":15368},
  {"context":"Analyze (actions)","integration_id":15368},
  {"context":"Analyze (python)","integration_id":15368},
  {"context":"CodeQL","integration_id":57789}
]
```

The update preserved `strict_required_status_checks_policy: true`, the
`refs/heads/main` condition, enforcement `active`, the pull-request rule,
deletion/non-fast-forward rules, review-thread resolution, and the existing
bypass actor/policy. Cursor must save the pre- and post-mutation JSON snapshots
and inspect the diff; a broad “repair” PATCH is not authorized.

If the live API rejects an integration id, context, or payload shape, stop and
report the exact error. Do not retry with a weaker context set or broaden the
mutation without a new Ryan decision.

## Phase 3 — positive control (COMPLETE)

PR #198 at head `e023f55b4d344eea9abffda3bfc53d6b103c90a1` passed all five
required contexts and remained ordinarily `CLEAN`/`MERGEABLE` without bypass.
The fresh post-closeout check evidence is recorded in the Grant A evidence
directory.

Use a normal, harmless PR from the Execute branch or a fresh no-op/documentation
branch after the ruleset mutation. Capture:

* head and base SHAs;
* all five required contexts and their URLs;
* `mergeStateStatus`/equivalent ordinary eligibility; and
* the post-patch ruleset snapshot.

The positive control is complete only when all five statuses are successful and
the PR is ordinarily merge-eligible. No bypass is used.

## Phase 4 — Ryan-authorized disposable negative control (COMPLETE)

B1 attempt #1 used the malformed-YAML fixture and failed isolation: all five
contexts stayed green. Cursor closed PR #199, deleted its branch, and stopped.
After a new Ryan authorization, B1 attempt #2 used the authorized
`actions/code-injection/critical` fixture. It produced exactly one red CodeQL
context with the other four required contexts green, and ordinary merge was
blocked. PR #200 was closed without merge and its branch was deleted.

This phase has a second, separate authorization boundary. Cursor creates one
disposable branch/PR only after Ryan grants disposable controls.

Preferred fixture: add a single malformed YAML file under
`.github/workflows/` so the CodeQL GitHub Actions extractor is expected to
fail. The fixture must be isolated from product code and must not contain a
real long-lived vulnerability. Capture the exact file, branch tip, PR number,
check-run URLs, conclusion, and ordinary merge state.

The control passes only if a required CodeQL context is red or absent, the
pre-existing `pylint (3.12)` and `pytest (3.12)` contexts are successful, and
the ordinary merge path is blocked. B1 attempt #1 used this original fixture:

```text
path: .github/workflows/codeql-negative-control.yml
content: name: [codeql-negative-control
```

That deliberately malformed workflow YAML was disposable and never reached
`main`. When it failed to produce a meaningful analyzer failure, Cursor
closed/deleted the PR and obtained a new Ryan authorization. B1 attempt #2
then used the separately authorized `actions/code-injection/critical` fixture
and produced the passing 1-red/4-green result recorded above.
No fallback that edits an established workflow is pre-authorized; an
unobserved hypothesis is not a pass.

Do not use the repository-role bypass, merge the PR, cancel a check to simulate
failure, or change the ruleset solely to make the control easier to trigger.

### Phase 4a — producer-identity probe (separate disposable authorization, COMPLETE)

After B1 attempt #2 isolated exactly one red CodeQL context, Ryan separately
authorized B2. On disposable head
`d3d0bdd9986c7f77e60f956c6018493f22b784f2`, Cursor posted one same-named green
user status. The genuine GHAS `CodeQL` check remained failed and ordinary merge
remained blocked. Kiro PASSed B2 at that exact SHA. PR #201 was closed without
merge and its branch was verified absent.

Run this probe only when Ryan's disposable-control grant names it explicitly
and Phase 4 has isolated exactly one red or missing CodeQL-required context.
Select that actual target from the fresh check evidence; do not assume that
the malformed workflow will affect a particular surface. Post one green,
same-named commit status through the ordinary user-authenticated `gh` session:

```bash
gh api --method POST \
  repos/alanmz-crypto/convmem/statuses/<disposable-head-sha> \
  -f state=success \
  -f context='<target-codeql-context>' \
  -f description='disposable nonmatching-producer probe'
```

Then capture the raw status, check-run, and PR state:

```bash
gh api repos/alanmz-crypto/convmem/commits/<disposable-head-sha>/status
gh api repos/alanmz-crypto/convmem/commits/<disposable-head-sha>/check-runs --paginate
gh pr view <disposable-pr> --json number,headRefOid,mergeStateStatus,statusCheckRollup
```

The probe passes only when the status is visibly user-authored or otherwise
has no matching integration id, the genuine target context remains red or
absent, the other four required contexts are successful, and ordinary merge
eligibility remains blocked. If more than one CodeQL context is red/absent, or
the status changes the outcome, record the result as inconclusive/FAIL and
stop. Do not retry with another context or producer. The status is attached to
the disposable commit and may remain as immutable evidence after branch
cleanup; prove that commit never reaches `main` rather than attempting a
destructive status rewrite.

## Phase 5 — restoration and cleanup (COMPLETE)

PRs #199, #200, and #201 were closed without merge. Their branches were deleted
and independently verified absent. The disposable fixture is absent from
`main`; no disposable commit is reachable from `main`. The live ruleset remains
active with the intended five contexts and strict policy, and no bypass was
used.

For every disposable control:

1. close the PR without merging;
2. delete the disposable remote branch and remove any local disposable worktree;
3. verify that the fixture does not exist on `main`;
4. re-run the normal positive check and ruleset snapshot; and
5. record that the intended five-context set and strict policy remain intact;
6. for the producer probe, retain its status URL/creator evidence and verify
   its disposable commit is not reachable from `main`.

If the negative control creates a code-scanning alert, verify that it is tied to
the disposable ref and is not a `main` finding. Do not remediate unrelated
Dependabot or code-scanning findings inside this arc.

The post-Execute recurring attestation is owned by Ryan as the stable policy
and gatekeeping role. Its cadence is quarterly plus an immediate trigger on
configuration drift. Cursor may collect the ruleset/default-setup/check-identity
evidence, but is not the policy owner; Kiro reviews exceptions and Ryan decides
whether any policy or gate change requires a new authorization or reopened arc.
No scheduled workflow is added by this plan.

## Phase 6 — review and closeout (CLOSED/PASS)

Cursor handed the final implementation evidence, ruleset snapshots, positive
and negative-control evidence, and cleanup evidence to Kiro. Kiro reviewed
exact implementation SHA `d3d0bdd9986c7f77e60f956c6018493f22b784f2` and exact
planning tip `cd653d95fd3dd7b3e46565c59d44134d84fae44e`, and PASSed both. Ryan
recorded the final `CLOSED/PASS` state and recurring-attestation contract. No
agent merges or changes `main`.

The branch handoff must include:

```text
branch: <implementation branch>
tip: <full SHA>
git log origin/main..HEAD --oneline
push: <explicit refspec and result>
ruleset: Protect Main 19156572, post-patch snapshot path/URL
positive PR: <number and URL>
negative PR(s): <number(s), closed without merge>
```

## Scope lock and stop conditions

Stop immediately for any of the following:

* a request to edit a tracked CodeQL/workflow file in this arc;
* a requested change to Pylint, Pytest, Pinwheel, bypass, CodeQL results
  thresholds, native code-scanning rules, Dependabot, runtime, corpus, or
  production data;
* a missing or renamed context that would require guessing;
* a failed disposable fixture with no reproducible red/missing status;
* a request to post a same-named status without explicit producer-probe
  authorization, or a spoofed status that appears to carry a matching app id;
* a request to exercise admin bypass or merge a disposable PR; or
* an external mutation that differs from the exact ruleset resource and final
  values authorized by Ryan.

**TL;DR:** Grant A, B1, and B2 are complete and Arc CodeQL Complex Therapy is
CLOSED/PASS. The five-context ruleset is live, producer binding is proven, all
disposable resources were cleaned up, and Ryan owns future attestation.
