# Implementation draft: willowyhollow review-gate enforcement

**Date:** 2026-09-18
**Author:** OpenAI Codex
**Arc:** none (ad-hoc)
**State:** revised draft for Claude adversarial audit; no repository, ruleset, access, or SiteGround change authorized
**Input:** `docs/inter-model/CLAUDE-2026-09-18-willowyhollow-review-gate-comparison-handoff.md`

## Decision for this audit

The two required WordPress PR checks already exist and have reported under the
exact names configured in both rulesets. There is no missing `theme-engine` or
`plugin-lock` PR job to implement. The first missing enforcement primitive is an
independent approving reviewer. The private, user-owned
`alanmz-crypto/willowyhollow-dev` repository currently lists only
`alanmz-crypto` as a collaborator. GitHub does not let a PR author approve their
own PR. Setting the review count to one before a second eligible human has
accepted access would block owner-authored PRs. Do not make that mutation yet.

The recommended target is one qualifying human approval **and** approval of the
most recent reviewable push on both deploy branches, after the reviewer exists
and a test PR proves the gate. Keep the existing two required checks, loose
status freshness, and empty bypass list. Treat staging2 response-header repair
as a separate deployment/security slice: current live evidence arrives after
merge and cannot truthfully be called a pre-merge gate.

## Evidence snapshot and comparison

Read-only GitHub API checks on 2026-09-18 queried the live rulesets, repository
ownership/collaborators, the PR workflow on both protected branches, and check
runs on merged
[`main` PR #25](https://github.com/alanmz-crypto/willowyhollow-dev/pull/25)
and [`staging` PR #24](https://github.com/alanmz-crypto/willowyhollow-dev/pull/24).
Those PRs are from July; they prove the configured contexts have been emitted,
not that a fresh PR will pass today. The local `~/GitClones/willowyhollow-dev`
checkout is on an older, heavily dirty branch and is not evidence of current
GitHub workflow contents.

| Control | Willowyhollow `main` | Willowyhollow `staging` | ConvMem `main` | Proposed WordPress target |
|---|---|---|---|---|
| Ruleset | [`main-integrity-gates` 19155375](https://github.com/alanmz-crypto/willowyhollow-dev/rules/19155375) | [`staging-integrity-gates` 19155380](https://github.com/alanmz-crypto/willowyhollow-dev/rules/19155380) | [`Protect Main` 19156572](https://github.com/alanmz-crypto/convmem/rules/19156572) | Keep existing IDs and branch conditions |
| Enforcement and target | Active; branch `main` | Active; branch `staging` | Active; branch `main` | Keep active |
| PR approval count | 0 | 0 | 0 | 1, only after a second eligible human reviewer is available |
| Reviewer capacity | One listed collaborator: owner `alanmz-crypto` | Same repository | One listed collaborator: owner `alanmz-crypto` | Add an independently controlled human collaborator; exact account and access need Ryan's separate decision |
| Last-push approval / stale dismissal | `false` / `false` | `false` / `false` | `false` / `false` | `true` / `false` when enabling one approval; reapproval after the last reviewable push |
| Extra approval for unattributed Copilot changes | `true` | `true` | `true` | Keep; an unattributed Copilot PR may need another approval beyond the configured count |
| Required PR checks | `theme-engine`, `plugin-lock` | Same | `pylint (3.12)`, `pytest (3.12)`, `Analyze (actions)`, `Analyze (python)`, `CodeQL` | Keep the two existing WordPress contexts |
| Required-check freshness | Loose (`strict_required_status_checks_policy=false`) | Loose | Strict (`true`) | Keep loose for this slice; review after measuring merge behavior |
| Enforce required checks on branch creation | `do_not_enforce_on_create=false` | Same | Same | Keep |
| Check publisher | No `integration_id` pinned in ruleset | Same | Four checks pinned to GitHub Actions; CodeQL pinned to GitHub Advanced Security | Verify publisher on fresh PR; consider source pinning in a later grant |
| Review threads / code owners | Resolution `false`; code-owner review `false`; no required reviewers | Same | Resolution `true`; no required reviewers | Keep current WordPress values; no invented AI/team identities |
| Allowed merge methods | `merge` | `merge` | `merge`, `squash`, `rebase` | Keep current WordPress value |
| Bypass | Empty; current user `never` | Empty; current user `never` | `RepositoryRole` actor id `5`, mode `always`; current user `always` | Keep WordPress empty; assess ConvMem separately |
| Non-fast-forward / deletion | Both rules present | Both rules present | Both rules present | Keep both |

The live [`pr-theme-gate.yml` on `main`](https://github.com/alanmz-crypto/willowyhollow-dev/blob/main/.github/workflows/pr-theme-gate.yml)
and `staging` has matching definitions and
always-reporting `pull_request` jobs named `theme-engine` and
`plugin-lock` for both protected branches. Both names appear as successful
GitHub Actions check runs on the cited PR heads. The push-triggered
[`deploy.yml`](https://github.com/alanmz-crypto/willowyhollow-dev/blob/main/.github/workflows/deploy.yml)
retains plugin and theme checks before deploying to SiteGround. It also
preserves server `.htaccess`, so a tracked configuration assertion alone would
not establish what headers SiteGround actually serves.

The WordPress rulesets already require a PR, even with zero approvals; the
unenforced part is **independent review**, not PR creation. We have not made a
protected direct-push attempt. GitHub's [ruleset documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
explains the rule semantics. GitHub's [review documentation](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request)
states that PR authors cannot approve their own PRs. `cursor[bot]` left
`COMMENTED` reviews on PR #25; those comments are not qualifying human
approvals. The `alanmz-crypto` account owns the repository, so an
organization team is not currently a reviewer mechanism here.

## Verdict on Claude's six proposals

1. **One approval on deploy branches — adopt with a prerequisite.** Use one
   independent human approval on both WordPress branches only after the
   collaborator exists and a test PR proves the account can approve. Do not
   carry this value over to ConvMem automatically; its bypass and bounded
   autonomy policy need a separate decision.
2. **Risk-tiered approval counts — adopt.** The deploy branches merit a stronger
   human gate than routine reversible ConvMem changes. The selected count must
   also be operable with the people who actually have repository access.
3. **Make live staging2 headers a required PR check — reject as phrased.** A
   monitor of the current staging2 site measures the previously deployed
   `staging` commit, not the PR candidate. A passing result can be unrelated to
   the proposed change. Retain live monitoring and design a candidate deploy
   only if Ryan wants true pre-merge live-header enforcement.
4. **Set strict required-check freshness on WordPress — defer.** The existing
   loose checks run on PRs to both branches. Strict mode would force more
   updates and CI; adopt only after a branch-concurrency or stale-check failure
   warrants it. This is a distinct choice from requiring the last push to be
   approved by someone else.
5. **Resolve bypass asymmetry — adopt as a policy decision, not symmetry.**
   WordPress currently has no bypass and should keep it. ConvMem's actor id `5`
   and `current_user_can_bypass=always` mean its rule is bypassable by this
   account; identify the role and document when it may be used in a separate
   ConvMem review. Do not copy that bypass to WordPress or remove it without a
   recovery/operations decision.
6. **Map AI lanes into GitHub review — adopt only at the human boundary.** Kiro,
   Claude, and Copilot audit evidence can be linked in the PR, but none is a
   required human approval simply because it appears in a comment or check.
   The invited human reviewer is the GitHub enforcement actor; Ryan remains
   merge/ledger owner. No CODEOWNERS or required-team rule is proposed for this
   user-owned repository.

## Implementation sequence

### Phase 0 — finish evidence, no mutation

**Owner:** Crush or Codex. The historical ruleset and check-context inventory
above is complete. Before any ruleset change, verify a fresh PR to each branch
reports both required jobs on the relevant head or test-merge commit. Record
the exact app publisher and whether GitHub considers each check satisfied. Check
current branch conditions, bypass actors, and collaborator access again on the
day of change. GitHub [documents](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)
that path-filtered or skipped workflows may leave a required context pending;
the present workflow has no PR path filter.

### Phase 1 — choose an operable reviewer model

**Owner:** Ryan. For one required human approval, name a second real person
with an independent GitHub account, confirm their willingness and response
time, and separately authorize an invitation to this private repository. The
owner can then approve that person's PRs; the second person can approve
owner-authored PRs. Grant only the access GitHub permits for a personal private
repository and verify acceptance before changing the ruleset. This access
change is material and is **not** authorized by this draft.

If Ryan does not choose a second eligible human, keep the count at zero and
retain PR + required checks. Require an explicit out-of-band Ryan/Kiro review
record in the working process, but label it **procedural review, not a GitHub
approval gate**. Do not introduce a bot or second account controlled by the PR
author to manufacture an approval. GitHub allows repository owners to edit
rulesets; the owner must also agree to treat rule edits as an audited exception.

### Phase 2 — ruleset change after the reviewer prerequisite

**Owner:** an operator specifically named in Ryan's grant; Kiro reviews the
exact plan and Claude audits this draft before that grant. On each WordPress
ruleset, change only the pull-request parameters below:

```text
alanmz-crypto/willowyhollow-dev / 19155375 / refs/heads/main:
  rules[type=pull_request].parameters.required_approving_review_count: 0 -> 1
  rules[type=pull_request].parameters.require_last_push_approval: false -> true

alanmz-crypto/willowyhollow-dev / 19155380 / refs/heads/staging:
  rules[type=pull_request].parameters.required_approving_review_count: 0 -> 1
  rules[type=pull_request].parameters.require_last_push_approval: false -> true
```

Preserve `name`, `enforcement`, branch conditions, all other rules and their
parameters, `bypass_actors=[]`, and both required check names. Before an API
update, reread the full ruleset, prepare the complete request payload required
by GitHub's update endpoint, and review its diff: a nested-field shorthand is
not a safe API payload. Re-read both rulesets after the update. If a fresh PR
reveals a name or publisher mismatch, correct that evidence first; do not
replace the already proven contexts based on the old local checkout. No
workflow-file change is in this phase.

### Phase 3 — actual staging2 header control, separately scoped

**Owner:** Codex designs, Claude challenges the trust boundary, Kiro reviews,
and Cursor implements only after Ryan authorizes the exact deployment or
SiteGround change. The six open ConvMem observations are:
`obs_staging2_monitor_csp-missing`, `obs_staging2_monitor_header-hsts`,
`obs_staging2_monitor_header-referrer-policy`, `ver_staging2_mon_csp`,
`ver_staging2_mon_hsts`, and `ver_staging2_mon_referrer-policy`.

First locate the active header source (SiteGround/server configuration,
preserved `.htaccess`, WordPress/plugin configuration, or a combination), choose
the desired CSP/HSTS/Referrer-Policy values, and repair that source. Verify live
HTTPS responses, including redirects and any authenticated staging path. A
post-deploy workflow step or independent monitor can fail and alert on missing
headers, but it runs **after** the triggering merge and deployment. Specify
rollback/incident ownership before making it a deploy failure. A static test of
a tracked file is useful only if that file controls the live response; it is
not a substitute for the live probe. A true pre-merge gate requires an isolated
PR candidate deployment with credentials, cleanup, and cost accounted for.
There is no current staging-to-production promotion path, so do not present a
promotion gate as an existing low-cost option.

## Audit scope and operating cost

Claude should challenge the reviewer-capacity conclusion, whether one approval
plus last-push approval closes the practical unreviewed-change path, the
preserved `.htaccess` trust boundary, and whether the proposed WordPress
ruleset update can be made without changing unrelated parameters. Kiro remains
the design sign-off lane. Copilot's audit lane is for a targeted security or
deployment recheck if that later implementation warrants it; Cursor implements
the granted change. Claude's audit is requested for this high-impact ruleset
decision, not a standing model cost on each routine WordPress PR.

This first slice adds no Actions job: the two required checks already run.
Reviewer availability is its recurring cost. Fresh PR verification consumes
ordinary CI runs. Isolated candidate deployments would add server credentials,
cleanup, runtime, and operational cost and are outside the first slice.

## Artifact ownership and GitHub home

ConvMem is a reasonable home for this **cross-repository comparison** and the
Claude/Codex handoff because its team charter, bounded-autonomy policy, and
inter-model routing live here. It is a poor long-term source of truth for a
WordPress ruleset or workflow implementation: a reviewer of
`willowyhollow-dev` cannot see the controlling plan in the same PR as the
change, and the two repositories can drift.

After Claude's audit and Ryan's scope decision, put the executable WordPress
plan, tests, and verification record in `alanmz-crypto/willowyhollow-dev`
alongside the workflow or as a linked plan in that repository's PR. Keep this
document as the comparison and decision record, then replace its active
implementation pointer in `docs/inter-model/LATEST.md` with the WordPress PR
link. Keep any ConvMem-only bypass/autonomy decision in ConvMem. A new GitHub
repository would add another place to synchronize without owning either gate.

## Authorization and acceptance

**Authorized external changes in this draft: none.** Read-only inventory is
complete. Distinct future grants would be needed for (a) the exact GitHub
account invited to the private WordPress repository and its access, (b) each
ruleset ID and both exact final parameter values above, (c) any repository
workflow edit, and (d) the selected SiteGround/header change with its final
configuration. Approval of one does not authorize the others. ConvMem ruleset
`19156572` is outside this WordPress implementation slice.

Acceptance for a later execution:

- A second independent human can review a fresh owner-authored PR to both
  `main` and `staging`; the invited account is identified in the grant.
- `theme-engine` and `plugin-lock` appear from the expected publisher and pass
  on fresh PRs to each branch before ruleset changes.
- Each active ruleset reads back with count `1`, last-push approval `true`,
  unchanged required checks, branch conditions, and empty bypass list.
- A PR with no qualifying approval is blocked; a final review after the last
  reviewable push plus passing checks permits merge. Verify via GitHub's merge
  state without performing an unauthorized live merge.
- Staging2 header verification is labeled by the event it can block (candidate
  merge, post-deploy alert/rollback, or a newly designed promotion), and the
  six observations are rechecked only after an authorized live change.
- Claude's audit and Kiro's sign-off identify the same document revision;
  Ryan's final grant names exact resources, operations, and values.

**Largest trade-off:** One human approval creates a real availability dependency
for this solo-owned site. Keeping zero approvals preserves availability but
leaves independent review procedural. Neither choice should be described as
achieving the other.

I finished: [Arc none (ad-hoc)] revised implementation draft for Claude audit.
Next step: Claude audits this revision, then Kiro reviews the agreed target.
Next lane: Claude, then Kiro and Ryan; Cursor only after an exact grant.
See my work: `docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`
