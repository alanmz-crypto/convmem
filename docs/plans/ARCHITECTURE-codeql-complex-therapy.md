# Architecture: CodeQL Complex Therapy

| Field | Value |
|---|---|
| **Arc** | CodeQL Complex Therapy |
| **Status** | Planning package; Execute is not authorized by this document |
| **Owner** | Codex authors the plan; Cursor executes after Ryan's separate grant; Kiro reviews; Ryan owns external authorization and merge |
| **Baseline** | `origin/main` at `9c2a6784d760de6b39f154ee400033276c9b8336` |
| **Planning branch** | `plan/2026-08-16-codeql-complex-therapy`; pre-correction published tip `658a9dab9977ba03dbfc6b1301b0f6bce3762f39` |
| **Decision** | Make the three live CodeQL-related contexts required on `Protect Main`, intentionally inheriting the current GHAS `CodeQL` results-check failure semantics while preserving strict freshness policy |

## Goal and consequence

GitHub Advanced Security currently runs CodeQL on pull requests, but a passing
CodeQL result is only advisory because `Protect Main` requires Pylint and Pytest
only. A pull request can therefore carry a failed or missing CodeQL analysis and
still satisfy the current required-status set.

This arc closes that merge-protection gap. After Execute, an ordinary merge to
`main` must have successful, fresh results for the existing Pylint and Pytest
contexts plus the three CodeQL contexts observed on the live repository. A
missing or red required context is unsatisfied because it is named in the
required-status set; strict policy additionally requires the PR to be tested
against the current base branch.

Requiring the GHAS `CodeQL` results check intentionally imports that check's
existing failure semantics into merge eligibility. If the current CodeQL
results policy makes a finding cause the `CodeQL` check to fail, that failure
will block an ordinary merge after Execute. This arc does not add or change a
native alert-threshold rule or change the existing results policy; it makes the
current GHAS result a required status surface alongside the two analyzer jobs.

## Live system baseline

The following facts were captured from GitHub on 2026-08-16 rather than inferred
from the handoff:

| Surface | Observed state |
|---|---|
| Ruleset | `Protect Main`, id `19156572`, target `branch`, `refs/heads/main`, enforcement `active` |
| Existing required contexts | `pylint (3.12)` and `pytest (3.12)`, both GitHub Actions integration id `15368` |
| Strict policy | `strict_required_status_checks_policy: true` |
| CodeQL setup | Default setup `configured`, query suite `default`, standard runner; no tracked CodeQL workflow exists in the repository |
| Dynamic workflow | GitHub reports an active `CodeQL` workflow at `dynamic/github-code-scanning/codeql` |
| Historical PR #191 head | `35e090dae25df08a42989d28a9caed5ab1f6255f` (merged as `857a3a244a3ac27d8f1cdc84b34ba4b32d967e0f`) |
| Fresh planning-time PR #197 head | `740424884f8921f1586f6b82648a0a290be40836` (merged; latest completed PR CodeQL run captured before this correction) |

The exact CodeQL-related check contexts on fresh PR #197 were:

| Context | Producer | Integration/app id | Live evidence |
|---|---|---:|---|
| `Analyze (actions)` | GitHub Actions | `15368` / GitHub Actions | run `31955068924`, job `95184347389` |
| `Analyze (python)` | GitHub Actions | `15368` / GitHub Actions | run `31955068924`, job `95184347396` |
| `CodeQL` | GitHub Advanced Security | `57789` / `github-advanced-security` | run `95184414717` |

The current ruleset does not contain any of these three contexts. This is the
live distinction between “CodeQL passed on PR #197” and “CodeQL is required.”
Execute must repeat this identity capture immediately before mutation; this
planning-time capture is not a license to reuse stale names.

## Decision: the required context set

Execute must preserve the current required contexts and add exactly:

```text
Analyze (actions)   integration_id 15368
Analyze (python)    integration_id 15368
CodeQL              integration_id 57789
```

The resulting required-status set is:

```text
pylint (3.12)       integration_id 15368
pytest (3.12)       integration_id 15368
Analyze (actions)   integration_id 15368
Analyze (python)    integration_id 15368
CodeQL              integration_id 57789
```

All three CodeQL contexts are required for a deliberate reason:

* `Analyze (python)` and `Analyze (actions)` are the two live analyzer jobs and
  independently cover the configured Python and GitHub Actions surfaces.
* `CodeQL` is the GitHub Advanced Security result associated with the uploaded
  code-scanning analysis.
* Requiring only the summary would leave the analyzer-job contract implicit;
  requiring only the jobs would leave the GHAS result surface implicit. The
  three-context conjunction makes the current live contract explicit.
* If default setup adds a language, removes a language, or renames a job, a
  required context becomes missing and strict protection fails closed. The
  ruleset must then be intentionally reviewed and updated; it must not be
  silently weakened to make a PR green.

The patch is ruleset-only. It must not add or edit a repository CodeQL workflow,
change default-setup configuration, change the bypass policy, or alter the
existing Pylint/Pytest contexts. The native “require code scanning results”
alert-threshold rule is not part of this arc, and the existing GHAS results
threshold is not changed; the deliberate policy choice is to inherit the
current `CodeQL` results-check semantics by requiring that check.

## Merge and failure semantics

The invariant is:

```text
ordinary merge eligible
  iff all five named required contexts are present and successful
  and, because strict_required_status_checks_policy=true,
      the PR is tested against the current base branch
```

Required-status membership makes a red or absent named context unsatisfied.
Strict policy adds the freshness/up-to-date requirement; it is not the mechanism
that creates the named-context requirement. A stale PR therefore remains
ineligible even when all checks are green until it is tested against the latest
base. The repository-role bypass remains present as an administrative capability
but is not evidence and must not be exercised.

The ruleset update must preserve, byte-for-byte in meaning, the existing
deletion, non-fast-forward, pull-request, review-thread-resolution, and bypass
settings. Only the `required_status_checks` array gains the three named entries.

## Negative-control design

The disposable negative control must create an analysis failure, not merely a
CodeQL alert that the analyzer still reports as successful. The primary
candidate is a disposable PR that adds one deliberately malformed GitHub
Actions workflow YAML file under `.github/workflows/`. It exists only to make
the GitHub Actions CodeQL extractor fail on the `Analyze (actions)` surface;
the PR is never merged and the file is deleted with the disposable branch.

The control is valid only if live logs show one of the required CodeQL contexts
red (or the required context never appears and strict protection blocks the
PR) and the ordinary merge state is blocked. If the malformed-workflow fixture
is accepted without an analyzer failure, it is not evidence. Cursor must use a
second disposable control that causes a reproducible `Analyze (python)` or
CodeQL analysis failure, record the exact fixture and run evidence, and still
leave no change on `main`.

A source-level vulnerability alone is not an acceptable substitute: a finding
may be uploaded while the CodeQL check remains green. Likewise, admin bypass,
manual status manipulation, cancellation, or a broken repository-wide service
is not a negative-control proof.

## Scope and non-goals

In scope:

* one ruleset mutation to `Protect Main` after Ryan authorizes Execute;
* exact live context and integration-id capture;
* strict required-status preservation;
* one or more Ryan-authorized disposable PRs proving red/missing CodeQL blocks
  ordinary merge;
* restoration, cleanup, and independent verification.

Out of scope:

* ruleset or workflow edits during this planning phase;
* adding a tracked CodeQL workflow or switching default setup to advanced setup;
* CodeQL query, language, runner, or results-threshold changes;
* adding the separate native code-scanning alert-threshold ruleset rule;
* the open Dependabot critical alert unless Ryan creates a separate scope grant;
* Pinwheel, Kryptonite, runtime, Chroma, ledger, corpus, or production-data
  changes;
* exercising or changing the repository-role bypass.

## Acceptance conditions for Execute

Execution may start only after Ryan reviews this package and separately grants
the Execute lane, including the disposable-control grant. The arc is complete
only when:

1. the post-patch ruleset contains all five exact required contexts and still
   has strict policy enabled;
2. a normal PR is green on all five contexts;
3. a disposable CodeQL analysis failure or missing required context produces an
   ordinary blocked merge;
4. the disposable resources are closed/removed without entering `main`;
5. restoration leaves the default CodeQL setup healthy and the ruleset unchanged
   except for the intended required contexts; and
6. VERIFY has exact revisions, URLs, ruleset snapshots, and Kiro/Ryan review
   outcomes.

**TL;DR:** Require `Analyze (actions)`, `Analyze (python)`, and `CodeQL` in the
existing strict `Protect Main` status set, using a ruleset-only Execute change;
prove a disposable analysis failure blocks ordinary merge, without changing
workflows, bypass policy, or alert thresholds.
