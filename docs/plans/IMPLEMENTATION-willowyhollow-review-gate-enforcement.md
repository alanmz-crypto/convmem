# Implementation draft: willowyhollow review-gate enforcement

**Date:** 2026-09-18
**Author:** OpenAI Codex
**Arc:** none (ad-hoc)
**State:** Track A sequence PASS from Kiro at `1363056`; Crush's read-only attribution is in hand; the Phase 1 candidate below requires Kiro re-review and Ryan's exact policy/grant decision; Track B remains deferred; no external change authorized
**Input:** `docs/inter-model/CLAUDE-2026-09-18-willowyhollow-review-gate-comparison-handoff.md`

## Decision for this audit

The two required WordPress PR checks already run. The live defect is missing
staging2 security headers, while neither deploy branch has received a merge
since 2026-07-19. Prioritize the header-source investigation and repair. The
review gate is a separate, slower governance track.

**Do not invite a reviewer or set the approval count to one now.** This private,
user-owned repository has only its owner as a collaborator. A second reviewer
needs write access, and GitHub says a repository writer can access repository
Actions secrets. The four `SG_*` values include the SiteGround SSH key and are
repository scoped. An installed Cursor App has `pull_requests:write` and has
already submitted an `APPROVED` review on PR #2. A numeric count alone cannot
be presented as a verified human gate. First isolate deployment credentials
and prove a bot-only approval cannot satisfy the proposed rule. If Ryan chooses
not to fund that redesign, retain zero required approvals and describe review
as procedural.

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
| PR approval count | 0 | 0 | 0 | Keep 0 now; propose 1 only after secret isolation and a proven human-specific gate |
| Reviewer capacity | One listed collaborator: owner `alanmz-crypto` | Same repository | One listed collaborator: owner `alanmz-crypto` | A second human would receive write access to this private personal repository |
| Last-push approval / stale dismissal | `false` / `false` | `false` / `false` | `false` / `false` | Keep now; propose `true` / `false` with a future human gate |
| Extra approval for unattributed Copilot changes | `true` | `true` | `true` | Keep; GitHub says this has no effect while the required count is 0 |
| Required PR checks | `theme-engine`, `plugin-lock` | Same | `pylint (3.12)`, `pytest (3.12)`, `Analyze (actions)`, `Analyze (python)`, `CodeQL` | Keep the two existing WordPress contexts |
| Required-check freshness | Loose (`strict_required_status_checks_policy=false`) | Loose | Strict (`true`) | Keep loose for this slice; review after measuring merge behavior |
| Enforce required checks on branch creation | `do_not_enforce_on_create=false` | Same | Same | Keep |
| Check publisher | No `integration_id` pinned in ruleset | Same | Four checks pinned to GitHub Actions; CodeQL pinned to GitHub Advanced Security | Verify publisher on fresh PR; consider source pinning in a later grant |
| Review threads / code owners | Resolution `false`; code-owner review `false`; no required reviewers | Same | Resolution `true`; no required reviewers | Human CODEOWNERS review is a candidate future safeguard; verify it on both branches |
| Allowed merge methods | `merge` | `merge` | `merge`, `squash`, `rebase` | Keep current WordPress value |
| Bypass | Empty; current user `never` | Empty; current user `never` | Admin `RepositoryRole` actor id `5`, mode `always`; current user `always` | Keep WordPress empty; assess ConvMem separately |
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

Claude's audit prompted further read-only checks on 2026-09-18:

- The repository has four repository-scoped Actions secrets: `SG_HOST`,
  `SG_USERNAME`, `SG_PRIVATE_KEY`, and `SG_PASSPHRASE`. Its Actions setting allows
  all actions without SHA pinning; `GITHUB_TOKEN` defaults to read and has
  `can_approve_pull_request_reviews=false`. The sole existing `copilot`
  environment has no secrets or protection rules. GitHub's
  [Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use)
  says users with repository write access can read repository secrets. On a
  [personal private repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository),
  collaborators can only be granted write access. Granting an approver access
  therefore expands the SSH credential's trust boundary unless those secrets
  are moved or otherwise isolated first.
- The public Cursor App metadata reports `pull_requests:write`; its
  [`cursor[bot]` review on PR #2](https://github.com/alanmz-crypto/willowyhollow-dev/pull/2)
  has state `APPROVED`. Both PR #24 and #25 also have a successful `Cursor
  Approval Agent: Pull Request Router and Approver` check, although their
  reviews were comments. The repository's `GITHUB_TOKEN` approval setting does
  not settle what this separate App can do. The App's ability to submit an
  approval is proven; whether GitHub would count its approval under a proposed
  one-review rule is not yet proven. A future test must show a bot-only approval
  leaves a PR blocked if the promised control is human review.
- The latest of 25 recorded WordPress PRs merged on 2026-07-19. The six
  staging2 observations were filed on 2026-09-08, with no intervening merge to
  either deploy branch. A PR gate would not have detected this live defect.
- Live `curl -I` on 2026-09-18 returned `server: cloudflare` and HTTP 200 for
  staging2; CSP, HSTS, and Referrer-Policy were absent. Production returned
  Cloudflare HTTP 401. Cloudflare is on the response path, but that alone does
  not identify which layer omitted a header. The tracked plugin lock includes
  `headers-security-advanced-hsts-wp`; installed files do not establish its
  activation or settings on staging2.

GitHub [documents](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
that `require_extra_approval_for_unattributed_changes=true` has no effect when
the required count is zero, resolving the suspected current AI-PR deadlock for
that rule. The count-one behavior should still be included in later test PRs.
GitHub's [maintained Terraform provider reference](https://github.com/integrations/terraform-provider-github/blob/main/docs/resources/organization_ruleset.md)
maps `RepositoryRole` id `5` to Admin, closing the ConvMem bypass identity
question. ConvMem's owner can bypass `Protect Main`; this is a separate policy
decision, not a reason to copy that bypass to WordPress.

## Verdict on Claude's six proposals

1. **One approval on deploy branches — defer the mutation.** A real human gate
   requires a second writer; current repository secrets make that an SSH
   credential access decision. The Cursor App can submit `APPROVED` reviews.
   Isolate credentials and prove bot-only approval cannot pass before proposing
   count `1`. ConvMem remains a separate bounded-autonomy decision.
2. **Risk-tiered approval counts — adopt as a design rule.** Deploy branches
   merit stronger review, but a count without secret isolation and human
   reviewer identity could reduce safety. Keep the operationally honest count
   `0` while those prerequisites are unresolved.
3. **Make live staging2 headers a required PR check — reject as phrased.** A
   monitor of the current staging2 site measures the previously deployed
   `staging` commit, not the PR candidate. A passing result can be unrelated to
   the proposed change. There have been no merges since before the observations
   opened. Investigate and repair the live header source first; consider a
   candidate deployment only if pre-merge live-header evidence becomes valuable.
4. **Set strict required-check freshness on WordPress — defer.** The existing
   loose checks run on PRs to both branches. Strict mode would force more
   updates and CI; adopt only after a branch-concurrency or stale-check failure
   warrants it. This is a distinct choice from requiring the last push to be
   approved by someone else.
5. **Resolve bypass asymmetry — document the actual role.** WordPress has no
   bypass and should keep it. ConvMem's id `5` is the Admin role with an
   `always` bypass; `current_user_can_bypass=always` confirms this account can
   use it. Any change to that recovery posture belongs in a separate ConvMem
   decision.
6. **Map AI lanes into GitHub review — require a human-specific mechanism.**
   Kiro, Claude, Copilot, and Cursor evidence can be linked in the PR, but the
   Cursor App has already submitted an approval. A future numeric gate needs
   either a tested all-path human CODEOWNERS requirement or another proven
   mechanism that rejects bot-only approvals. Ryan remains merge/ledger owner.

## Implementation sequence

### Phase 0 — identify the live header owner first (read-only)

**Owner:** Crush investigates; Codex frames the repair; Kiro reviews its
design. On staging2, inspect Cloudflare Response Header Transform Rules and
Managed Transforms, the origin response and preserved `.htaccess`, and the
activation/settings of `headers-security-advanced-hsts-wp` and other
header-writing plugins. Compare the public Cloudflare response with the origin
response where a safe authenticated read is available. Cloudflare
[can add, replace, or remove](https://developers.cloudflare.com/rules/transform/response-header-modification/)
response headers, so `server: cloudflare` proves the proxy path, not the source
of the omission. The plugin lock proves files are tracked, not that the plugin
is active or configured. Existing history suggests an `.htaccess` header block
was tested in practice; verify its current state rather than treating that
session as a live deployment.

Capture the actual CSP/HSTS/Referrer-Policy policy target, response classes
(`200`, redirects, and `401`), and which layer should own each header. Keep
Cloudflare, SiteGround, and WordPress writes out of this read-only phase.
The six open observations remain evidence until live verification passes.
Their ledger ids are `obs_staging2_monitor_csp-missing`,
`obs_staging2_monitor_header-hsts`,
`obs_staging2_monitor_header-referrer-policy`, `ver_staging2_mon_csp`,
`ver_staging2_mon_hsts`, and `ver_staging2_mon_referrer-policy`.

**Phase 0 result (Crush, 2026-09-18T11:18Z):** the public HTTPS `200`,
natural `404`, and `/wp-json/` responses and the SiteGround origin all lack
the three headers. The current origin `.htaccess` has no `Header` directives;
its preserved July 8 backup contains the old three-header block, apparently
stripped during a July 12 server rewrite. The live header plugin is inactive;
`sg-security` emits the already-present X-Content-Type-Options and
X-XSS-Protection, not these three. Cloudflare is on the public path but was
not observed adding the missing headers. The exact source of the July 12
rewrite is an inference, not an attribution of an actor. Recheck the live
file, backup, Cloudflare rules, and plugin state immediately before any grant:
Codex independently confirmed the practice snippet and remote deploy/lock
files, but could not reread the server backup through its sandbox.
The `1363056` review identifier is a ConvMem documentation commit, not a
`willowyhollow-dev` commit; its absence from WordPress refs is expected.

### Phase 1 — repair and verify staging2 headers (separate grant)

**Owner:** Cursor implements the Kiro-reviewed repair after Ryan names the
exact host, configuration surface, operations, and final header values. Choose
one controlling layer for each header and avoid accidental duplicate or
contradictory CSP values. If WordPress/plugin settings or another database
value must change, take a `practice_backup` or `mysqldump` before that DB
mutation. If `.htaccess` is the chosen surface, account for the deployment
workflow's preservation of the server copy; a tracked-file edit alone will not
update it. A Cloudflare Managed Transform may add some security headers but
does not by itself define an application-compatible CSP or HSTS policy.

After the authorized change, check live HTTPS response headers for staging2's
home and representative pages, redirects, and authenticated paths as
applicable. Compare them with the intended values, check for site breakage,
then recheck all six observations. The monitor remains post-deploy evidence;
there is no current pre-merge candidate environment or staging-to-production
promotion path. This track does not depend on recruiting a reviewer or changing
a ruleset.

#### Phase 1 candidate for Kiro review — not an Execute grant

**Proposed owner and resource:** only the SiteGround origin's
`~/www/staging2.willowyhollow.com/public_html/.htaccess`, using `mod_headers`.
The practice file `scripts/staging2-security-headers.htaccess.snippet` was
committed as `deca4ba2ad8d543e35b37245c3cc05ae6aede62c` on July 8 and
is unchanged locally. The remote `staging` deploy workflow preserves this
server file across checkout. The plugin lock expects
`headers-security-advanced-hsts-wp` to remain inactive; activating it would
introduce additional unreviewed headers and is not proposed.

Candidate *enforcing* values, subject to the gates below:

```apache
<IfModule mod_headers.c>
  Header always set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://app.cal.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' data: https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://app.cal.com; frame-src 'self' https://app.cal.com https://maps.google.com https://www.google.com; object-src 'none'; base-uri 'self'; form-action 'self'"
  Header always set Strict-Transport-Security "max-age=300"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>
```

The CSP and Referrer-Policy values copy the July snippet. The proposed HSTS
value is **different**: `max-age=300` is a short, staging-host-only canary;
neither `includeSubDomains` nor `preload` is set. The saved one-year value
(`31536000`) would keep returning browsers on HTTPS for much longer and is
not silently restored. Ryan must explicitly choose the HSTS lifetime and
whether staging2 should emit HSTS at all. If `300` is approved, it is a
canary, not a durable security target; a later increase needs a separate
decision. Any value Ryan chooses instead must go back to Kiro on the exact
revised proposal before a grant. The [HSTS standard](https://www.rfc-editor.org/info/rfc6797/)
describes browser caching and the optional subdomain scope.
If Ryan chooses no HSTS, the HSTS observation cannot pass or close under the
current monitor; that outcome needs an explicit exception and revised Track A
acceptance, not a claimed six-observation closure.

The July CSP allows inline scripts/styles and any HTTPS image origin; it
restores the old monitored baseline, **not** a claim of strong XSS or
exfiltration resistance. Its July layout check predates the current
theme/UAGB content. A read-only public HTML spot check at
2026-09-18T13:27–13:31Z covered home, Services, Thai, Therapeutic,
Relaxation, and Contact; it found no definite static resource-origin mismatch
with this candidate. A Maps iframe matched `frame-src`; the Cal.com URL was
an outbound link, not evidence of a required Cal.com fetch. Inline script and
style tags were present and permitted by this candidate. This is **not**
dynamic CSP compatibility evidence: combined assets, lazy loading, plugin
behavior, booking, and browser violations remain untested. Before an
*enforcing* grant, exercise today's pages/interactions with the candidate in
a safe browser canary or separately granted
`Content-Security-Policy-Report-Only` trial, recording network and violation
evidence. Any staging report-only write needs its own exact Ryan grant and
Cursor implementation; a local browser canary must not mutate the hosted
site. Report-only alone will not close the enforcing-CSP observation. If
any required source would be blocked, revise the value and return it to Kiro;
do not install the old string merely to turn the presence-only monitor green.
The [CSP specification](https://www.w3.org/TR/CSP/)
requires browsers to apply every enforced policy, so a second policy can
break a page even if the proposed one is permissive.

**Pre-grant gates:** capture the current server file's contents, hash, owner,
and mode through read-only access; diff its current content, the July backup,
and only the candidate block. Confirm Cloudflare rules, SiteGround/Apache, active
plugins, and page-level CSP meta tags will not create a second enforcing
policy or conflicting final value. Capture raw, uncombined public and origin
response headers, including duplicate counts, for representative HTTPS
`200`, natural `404`, HTTPS redirects, and an existing authenticated/`401`
path if available. The Cloudflare-generated HTTP-to-HTTPS `301` is checked
for continued redirection; HSTS on that HTTP response is not required.
Apache's [`always` and `onsuccess` header tables](https://httpd.apache.org/docs/2.4/mod/mod_headers.html)
can otherwise produce duplicate final fields; a dictionary-style header
readout is not sufficient for this gate.
If SiteGround/nginx serves a relevant response without applying `.htaccess`,
this owner choice must be revised before an Execute grant.
GitHub's current `staging` branch and the live server file must be reread
immediately before execution, not inferred from a dirty local checkout.
Resolve `~` to the exact SiteGround account path before Ryan's grant.

**Conditional one-shot execution, only after Kiro review and Ryan's exact
grant:** Cursor saves a fresh pre-change backup outside the webroot, verifies
the live file hash still matches the reviewed preflight, and atomically
inserts only the approved block while preserving unrelated directives,
ownership, and mode. The July backup is evidence, **not** a rollback image:
copying it wholesale could erase later server rules. On failure, restore the
fresh backup only if the post-edit file hash still matches Cursor's write;
otherwise stop for Ryan. Removing an HSTS header does not instantly clear
browsers that cached it; a valid HTTPS `max-age=0` response may be needed
for an authorized rollback, and even that reaches only returning clients.

**Post-change acceptance:** raw origin and public HTTPS responses show exactly one
Content-Security-Policy, one Strict-Transport-Security, and one
Referrer-Policy field with the approved values and no second source;
X-Content-Type-Options, the HTTP-to-HTTPS redirect, and normal status codes
remain intact. Check applicable `200`, natural `404`, HTTPS redirect, and
existing auth/error responses separately, without `curl -L` hiding a hop.
Browser-test current layout and interactions, fonts, media, Cal.com, Maps,
navigation, and forms for CSP violations; roll back on material breakage.
Then run the staging2 monitor dry-run and recheck all six listed ledger
observations. The [monitor implementation](../../monitor.py) checks only
for nonempty CSP/HSTS/Referrer-Policy values; a green monitor is **not** proof of correct policy
or page compatibility. Ryan, not Cursor, owns any ledger closure.

### Phase 2 — choose whether an enforced human gate is worth the access redesign

**Owner:** Ryan chooses; Codex designs; Kiro reviews. The default at this
milestone is **no access or ruleset mutation**. With only the owner writing and
no merges in two months, keeping count `0` plus documented Ryan/Kiro review is
an honest, low-blast-radius choice. It is procedural review, not GitHub-enforced
independent approval.

If Ryan wants GitHub enforcement, first remove the SiteGround credentials from
the trust boundary of arbitrary repository branches. Two candidate
architectures need an exact, separately reviewed implementation plan:

1. **Restricted GitHub Environments:** verify the account's private-repository
   plan supports environment secrets and deployment branch policies. Place
   deployment credentials in `production` and `staging` environments, restrict
   each to its corresponding protected branch, make each deploy job reference
   its environment, then remove the four repository-scoped `SG_*` secrets only
   after successful cutover and rollback verification. No second writer gets
   access during migration. The protected branches must also have a proven
   human gate before that writer is invited; branch restrictions alone are
   insufficient if a writer can self-merge a malicious workflow. Do not assume
   environment *required reviewers* are available: GitHub
   [limits them to public repositories on Free, Pro, and Team](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
2. **Separate owner-controlled deployment repository or service:** keep the SSH
   credentials outside `willowyhollow-dev` entirely. Its deployer must accept
   only an identified commit from the protected branch and never run untrusted
   workflow code from a contributor branch. This costs another repository or
   service, credential rotation, and a carefully tested trigger/rollback path.

Moving the code repository to an organization alone does not isolate a secret
that remains repository scoped: GitHub's write-access rule still applies. Nor
do `allowed_actions` restrictions or a read-only `GITHUB_TOKEN` prevent a
writer from using a workflow to access a repository secret. Do not invite a
second writer until the chosen isolation is effective and verified. If neither
architecture is justified, retain the current reviewer model.

### Phase 3 — conditional human gate after credential isolation

**Owner:** Cursor prepares the exact WordPress repository/ruleset changes after
Ryan grants them; Kiro reviews the design and the implementation tip. The
desired gate is one **human code-owner** approval on every changed path, with
the latest reviewable push approved by someone other than its pusher. A numeric
count without the code-owner rule is insufficient while Cursor can submit an
`APPROVED` review. GitHub
[defines code owners as people or teams with write access](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners);
the final `CODEOWNERS` file must cover every deployable and workflow path on
both branches. A user-owned repository has no team target.

One safe candidate sequence, subject to an exact Kiro-reviewed execution plan:

1. Verify the chosen credential isolation, remove repository-scoped `SG_*`, and
   prove a workflow on an unprotected branch cannot obtain deployment secrets.
   Keep collaborator access unchanged.
2. Land `.github/CODEOWNERS` on both `main` and `staging`, initially assigning
   all paths and the CODEOWNERS file itself to `@alanmz-crypto`. Verify GitHub
   recognizes the file on each base branch.
3. With only the owner holding write access, set each ruleset's pull-request
   parameters to count `1`, `require_code_owner_review=true`, and
   `require_last_push_approval=true`. This intentionally freezes owner-authored
   merges until the second human can review. Confirm a PR with only a Cursor
   App approval remains blocked, or withhold the collaborator invitation if
   the human-only guarantee cannot be demonstrated.
4. Invite the exact second human account named by Ryan. That person authors a
   CODEOWNERS update on both branches adding their handle as an owner alongside
   `@alanmz-crypto`; Ryan approves those PRs. Then test an owner-authored PR
   with no review, bot-only review, and qualifying human review. The gate is
   live only after both branches pass the same tests.

Proposed conditional ruleset deltas, **not authorized now**:

```text
alanmz-crypto/willowyhollow-dev / 19155375 / refs/heads/main:
  rules[type=pull_request].parameters.required_approving_review_count: 0 -> 1
  rules[type=pull_request].parameters.require_code_owner_review: false -> true
  rules[type=pull_request].parameters.require_last_push_approval: false -> true

alanmz-crypto/willowyhollow-dev / 19155380 / refs/heads/staging:
  rules[type=pull_request].parameters.required_approving_review_count: 0 -> 1
  rules[type=pull_request].parameters.require_code_owner_review: false -> true
  rules[type=pull_request].parameters.require_last_push_approval: false -> true
```

Preserve `name`, `enforcement`, branch conditions, all other rule parameters,
`bypass_actors=[]`, and both required check names. Reread each full ruleset,
prepare GitHub's required complete update payload, review its diff, and reread
the result. Verify fresh `theme-engine` and `plugin-lock` checks on PRs to both
branches before any count change. The current PR workflow has no path filter.
GitHub's [required-check guidance](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)
explains why a skipped required workflow can otherwise block merging.

## Review lanes, cost, and the separate model-routing question

Claude's adversarial audit of `626d3ba` found no factual errors and raised the
credential-access and Cursor-App approval problems treated as blockers here.
It was an audit, not Kiro sign-off. Kiro then PASSed Track A's sequence at
`1363056`, with two conditions for Phase 1: prove a single noncontradictory
owner/value for each final header and make HSTS on staging an explicit policy
decision. The candidate above incorporates both but has **not** received
Kiro's exact-revision repair review. The human-review gate still needs Ryan's
access-architecture choice and a concrete secret-isolation plan before Kiro
signs off on its execution. Copilot's audit lane remains a targeted
security/deployment recheck if the later implementation warrants one; Cursor
implements only granted work.

The existing two PR checks need no new Actions job. A human gate adds reviewer
availability and, in this repository, credential-isolation work. A candidate
deployment adds server credentials, cleanup, and runtime cost. Claude's audit
is not a standing cost on routine WordPress PRs.

Ryan's original question about which model gives the best local web-design
quality per dollar remains unanswered. That is a separate model-routing slice;
this ruleset plan neither chooses a default design model nor treats a GitHub
approval setting as a proxy for model quality.

## Artifact ownership and GitHub home

ConvMem is a reasonable home for this **cross-repository comparison** and the
Claude/Codex handoff because its team charter, bounded-autonomy policy, and
inter-model routing live here. It is a poor long-term source of truth for a
WordPress ruleset or workflow implementation: a reviewer of
`willowyhollow-dev` cannot see the controlling plan in the same PR as the
change, and the two repositories can drift.

After Ryan's scope decision, put an executable WordPress plan, tests, and
verification record in `alanmz-crypto/willowyhollow-dev` alongside the changed
workflow or in its PR. Both repositories are private, so check that each
intended reviewer can actually read the chosen plan; a future WordPress
collaborator would not automatically see this ConvMem document. Keep this
comparison as the decision record and point `docs/inter-model/LATEST.md` to the
WordPress PR when one exists. ConvMem-only bypass/autonomy work stays here. A
new central GitHub repository would add synchronization without owning either
site or ConvMem policy.

## Authorization and acceptance

**Authorized external changes in this draft: none.** Header repair needs a
separate grant naming the controlling Cloudflare, SiteGround, WordPress, or
tracked-workflow resource and exact final header values. For the SiteGround
candidate above, the grant must name the resolved absolute staging2
`.htaccess` path, its reviewed preflight hash, the exact three approved
header strings (including HSTS lifetime and flags), the one-shot backup/edit
operation, rollback image/path, and verification/stop conditions. It does not
include production, plugin activation, Cloudflare changes, or a DB write.
A DB settings change also requires a backup before mutation. Credential redesign would need its
own exact environment/deployer, secret migration, branch-policy, workflow, and
rollback grants. A later reviewer invitation requires the person's handle and
write-access decision. Each ruleset mutation requires the exact ID and final
values above. These grants are independent. ConvMem ruleset `19156572` is
outside the WordPress implementation slice.

Acceptance for **Track A (headers)**:

- Read-only evidence identifies where Cloudflare, SiteGround, `.htaccess`, and
  the locked header plugin affect the final staging2 response.
- Kiro reviews this repair candidate now, then the exact final values after
  runtime CSP canary evidence. Ryan explicitly chooses staging HSTS `max-age`,
  `includeSubDomains`, and `preload` posture before an enforcing grant; any DB
  mutation follows a backup.
- Raw HTTPS responses have exactly one intended value for each of the three
  headers, with no second Cloudflare, SiteGround, plugin, or meta-CSP owner.
  Applicable `200`, `404`, HTTPS redirect, and auth/error responses preserve
  their behavior; current pages/interactions have no material CSP breakage.
  All six observations are rechecked, but monitor presence alone is not a
  functional or security-policy proof.

Acceptance for **Track B only if Ryan chooses GitHub-enforced human review**:

- No repository-scoped SiteGround credentials remain, and a workflow from an
  unprotected branch cannot obtain deployment credentials before a second
  writer is invited.
- Both base branches recognize all-path human CODEOWNERS. A PR with only a
  Cursor App `APPROVED` review remains unmergeable; a qualifying human owner
  approval after the last reviewable push can satisfy the review gate.
- Fresh `theme-engine` and `plugin-lock` checks pass on PRs to both branches.
  Each ruleset reads back with count `1`, code-owner review `true`, last-push
  approval `true`, unchanged branch conditions/check names, and empty bypass.
- The exact invited human can review owner-authored PRs; no live merge is made
  merely to test this plan. Ryan's grants name all resources, operations, and
  final values, and Kiro reviews the exact implementation tip.

**Largest trade-off:** A second repository writer currently gets a path to the
SiteGround SSH credential. Isolating that credential and proving a human-only
gate costs more than changing the approval count. Keeping count `0` preserves
the present access boundary and availability, but independent review remains
procedural.

I finished: [Arc none (ad-hoc)] integrated Phase 0 attribution and a conditional Phase 1 repair candidate.
Next step: Kiro reviews this candidate; obtain runtime CSP evidence and exact-value re-review before Ryan's enforcing grant.
Next lane: Kiro, a separately authorized canary/verification lane, Kiro, and Ryan; then Cursor only after an exact grant.
See my work: `docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`
