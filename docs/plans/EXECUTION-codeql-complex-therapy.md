# Execution Plan: CodeQL Complex Therapy

| Field | Value |
|---|---|
| **Arc** | CodeQL Complex Therapy |
| **Phase** | Planning complete; execution pending Ryan authorization |
| **Planning tip** | `0ffdc69` on `plan/2026-08-16-codeql-complex-therapy` |
| **Implementation lane** | Cursor, after a separate Ryan Execute grant |
| **External gate owner** | Ryan |
| **Independent review** | Kiro, on the same final artifact and revision |

## Consequence

The package gives Cursor a bounded, reversible Execute sequence: snapshot the
live ruleset, add the three observed CodeQL contexts while preserving existing
policy, prove normal and negative behavior, clean up disposable resources, and
hand the exact evidence to Kiro and Ryan. No implementation or disposable PR
is authorized by this planning document.

## Phase 0 — planning review (Codex complete)

Codex has produced:

* [`ARCHITECTURE-codeql-complex-therapy.md`](ARCHITECTURE-codeql-complex-therapy.md)
  with the exact context decision and scope lock;
* this execution plan with separate Execute and disposable-control gates;
* [`VERIFY-codeql-complex-therapy.md`](VERIFY-codeql-complex-therapy.md) with
  preflight, positive, negative, restoration, and sign-off rows; and
* [`STATUS-codeql-complex-therapy.md`](STATUS-codeql-complex-therapy.md) as the
  current arc brief.

The live planning evidence was taken from ruleset `19156572`, PR #191, and the
PR head check-runs. The planning branch contains documentation only; it does
not contain a ruleset mutation, workflow edit, disposable fixture, or runtime
change.

## Phase 1 — Ryan planning review

Ryan reviews the four planning files and the live-context decision. Review must
explicitly answer:

1. Is the all-three context set (`CodeQL`, `Analyze (python)`, `Analyze
   (actions)`) the intended required subset for the current default setup?
2. Is ruleset-only enforcement, without a native alert-threshold rule, the
   intended scope?
3. Is the malformed-workflow disposable control acceptable, with a fallback
   control if it does not produce a red/missing required context?
4. Is Cursor authorized to mutate `Protect Main` and, separately, to create the
   disposable PR/control resources?

Until those answers are granted, Cursor must not call a mutating ruleset API,
edit a CodeQL/workflow file, or create a disposable PR.

## Phase 2 — Cursor Execute: ruleset-only mutation

Cursor works from a fresh implementation branch based on the reviewed current
`main`, records the exact branch tip, and performs these read-only checks first:

```bash
git fetch origin
git rev-parse origin/main
gh api repos/alanmz-crypto/convmem/rulesets/19156572
gh pr checks 191
```

The only authorized external mutation is one patch to:

```text
PATCH /repos/alanmz-crypto/convmem/rulesets/19156572
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

The patch must preserve `strict_required_status_checks_policy: true`, the
`refs/heads/main` condition, enforcement `active`, the pull-request rule,
deletion/non-fast-forward rules, review-thread resolution, and the existing
bypass actor/policy. Cursor must save the pre- and post-mutation JSON snapshots
and inspect the diff; a broad “repair” PATCH is not authorized.

If the live API rejects an integration id, context, or payload shape, stop and
report the exact error. Do not retry with a weaker context set or broaden the
mutation without a new Ryan decision.

## Phase 3 — positive control

Use a normal, harmless PR from the Execute branch or a fresh no-op/documentation
branch after the ruleset mutation. Capture:

* head and base SHAs;
* all five required contexts and their URLs;
* `mergeStateStatus`/equivalent ordinary eligibility; and
* the post-patch ruleset snapshot.

The positive control is complete only when all five statuses are successful and
the PR is ordinarily merge-eligible. No bypass is used.

## Phase 4 — Ryan-authorized disposable negative control

This phase has a second, separate authorization boundary. Cursor creates one
disposable branch/PR only after Ryan grants disposable controls.

Preferred fixture: add a single malformed YAML file under
`.github/workflows/` so the CodeQL GitHub Actions extractor is expected to
fail. The fixture must be isolated from product code and must not contain a
real long-lived vulnerability. Capture the exact file, branch tip, PR number,
check-run URLs, conclusion, and ordinary merge state.

The control passes if a required CodeQL context is red or absent and the
ordinary merge path is blocked. If CodeQL accepts the fixture, close the PR
without merge and run the planned fallback fixture that causes a reproducible
Python or CodeQL analyzer failure. The fallback must be documented with the
same evidence; an unobserved hypothesis is not a pass.

Do not use the repository-role bypass, merge the PR, cancel a check to simulate
failure, or change the ruleset solely to make the control easier to trigger.

## Phase 5 — restoration and cleanup

For every disposable control:

1. close the PR without merging;
2. delete the disposable remote branch and remove any local disposable worktree;
3. verify that the fixture does not exist on `main`;
4. re-run the normal positive check and ruleset snapshot; and
5. record that the intended five-context set and strict policy remain intact.

If the negative control creates a code-scanning alert, verify that it is tied to
the disposable ref and is not a `main` finding. Do not remediate unrelated
Dependabot or code-scanning findings inside this arc.

## Phase 6 — review and closeout

Cursor hands the same final implementation tip, post-patch ruleset snapshot,
positive PR evidence, negative-control evidence, cleanup evidence, and VERIFY
file to Kiro. Kiro reviews the exact artifact/revision and records PASS or FAIL.
Ryan owns the merge and arc closeout. No agent merges or changes `main`.

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
* a requested change to Pylint, Pytest, Pinwheel, bypass, alert thresholds,
  Dependabot, runtime, corpus, or production data;
* a missing or renamed context that would require guessing;
* a failed disposable fixture with no reproducible red/missing status;
* a request to exercise admin bypass or merge a disposable PR; or
* an external mutation that differs from the exact ruleset resource and final
  values authorized by Ryan.

**TL;DR:** Ryan reviews and separately authorizes Cursor’s exact ruleset patch
and disposable PR controls; Cursor then proves all five required contexts on a
normal PR, proves a red/missing CodeQL analysis blocks ordinary merge, restores
the disposable state, and hands the same evidence to Kiro.
