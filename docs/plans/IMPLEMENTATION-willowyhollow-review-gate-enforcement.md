# Implementation draft: willowyhollow review-gate enforcement

**Date:** 2026-09-18
**Author:** OpenAI Codex
**Arc:** none (ad-hoc)
**State:** draft for Kiro review; no implementation authorized
**Source handoff:** `docs/inter-model/CLAUDE-2026-09-18-willowyhollow-review-gate-comparison-handoff.md`
**Codex handoff:** `docs/inter-model/CODEX-2026-09-18-willowyhollow-review-gate-implementation-handoff.md`

## 1. Product and enforcement goal

Make the stated WordPress review requirement effective for the two branches that
deploy `willowyhollow-dev`, while keeping the enforcement small enough to operate
reliably and cheap enough for a small site. Keep ConvMem's bounded-autonomy
policy independent. Give staging2 security findings a control path that matches
when the evidence is available.

The first implementation slice is the repository and pull-request gate. The
staging2 header control is a follow-up design because the current deployment
occurs on a push to `staging`, after the merge decision.

## 2. Current surfaces

### willowyhollow

- Repository: `alanmz-crypto/willowyhollow-dev`
- Rulesets: `main-integrity-gates` id `19155375` and
  `staging-integrity-gates` id `19155380`
- Deploy workflow: `~/GitClones/willowyhollow-dev/.github/workflows/deploy.yml`
- Production deploy: push to `main`
- Staging2 deploy: push to `staging`
- Local practice: `http://localhost:8081`
- Local preview: `http://localhost:8080`
- Source of truth: `~/GitClones/willowyhollow-dev`
- Six open staging2 observations:
  - `obs_staging2_monitor_csp-missing`
  - `obs_staging2_monitor_header-hsts`
  - `obs_staging2_monitor_header-referrer-policy`
  - `ver_staging2_mon_csp`
  - `ver_staging2_mon_hsts`
  - `ver_staging2_mon_referrer-policy`

### ConvMem

- Repository: `alanmz-crypto/convmem`
- Ruleset: `Protect Main` id `19156572`
- Existing policy: bounded autonomy for routine reversible work; review required
  for architecture, security, and external configuration.
- This draft does not change ConvMem's approval count or bypass role.

## 3. Proposed implementation sequence

### Phase 0 — read-only inventory

Owner: Crush or Codex. No external mutation.

1. Fetch the exact JSON for rulesets `19155375`, `19155380`, and `19156572`.
2. Record the complete ruleset fields, not only approval count:
   `enforcement`, `target`, `conditions`, `rules`, `bypass_actors`, deletion,
   non-fast-forward, required status checks, and pull-request settings.
3. Inspect representative pull requests and their actual check-run contexts.
4. Compare those contexts with:
   - the `theme-gate` job in `pr-theme-gate.yml`;
   - the `deploy-production` and `deploy-staging` jobs in `deploy.yml`;
   - the `check-plugin-lock.sh` step, which is currently inside deploy jobs.
5. Resolve whether the ruleset contexts `theme-engine` and `plugin-lock` are
   produced by any workflow or external status publisher. If no publisher exists,
   mark them as stale or unsatisfied rather than silently renaming them.
6. Confirm whether direct pushes are prevented by the ruleset and whether the
   pull-request rule applies to both protected branches.

Evidence required before Phase 1:

- exact ruleset JSON;
- a check-run inventory for at least one relevant PR or a documented reason no
  representative PR exists;
- a clear mapping from each required context to its workflow job;
- a named bypass role for ConvMem's `actor_id: 5`.

### Phase 1 — repository-owned pre-merge checks

Owner: Cursor after Ryan authorizes the repository file changes. Kiro reviews the
plan or tip; Copilot audits only if the change affects safety or isolation.

1. Keep the existing theme gate behavior and expose its actual job context as
   the required check only after Phase 0 verifies the name. The current visible
   job is `theme-gate`; do not assume `theme-engine` is valid.
2. Add a separate pull-request `plugin-lock` job, or add an equivalently named
   job to the existing PR workflow, that runs
   `ops/verify/check-plugin-lock.sh` against the PR checkout.
3. Keep the deployment-time plugin-lock validation as defense in depth.
4. Give both jobs stable, explicit job ids and names. Verify the resulting
   check-run contexts on a test PR before putting them into a ruleset.
5. Keep live CSP/HSTS/Referrer-Policy monitoring out of this pre-merge status
   check until Phase 3 resolves deployment timing.

This phase is the likely implementation with the best cost/performance ratio:
the checks run once on the PR, reuse existing scripts, and do not require a
live SiteGround deployment for every pull request.

### Phase 2 — willowyhollow review gate

Owner: Ryan authorizes the GitHub ruleset mutation; the mutation may be applied
by the authorized operator or a later Cursor execution lane as explicitly named
in the grant.

Proposed target for both willowyhollow rulesets, pending Phase 0 evidence:

```text
repository: alanmz-crypto/willowyhollow-dev
ruleset: 19155375 main-integrity-gates
field: rules.pull_request.required_approving_review_count
value: 1

repository: alanmz-crypto/willowyhollow-dev
ruleset: 19155380 staging-integrity-gates
field: rules.pull_request.required_approving_review_count
value: 1
```

Additional target decisions:

- Use a real human or team reviewer. Do not encode Kiro, Claude, Cursor, Crush,
  or Copilot as a GitHub reviewer unless a concrete identity exists and Ryan
  explicitly chooses it.
- Leave `bypass_actors` empty for willowyhollow unless Ryan deliberately grants
  a documented break-glass actor.
- Keep `strict_required_status_checks_policy` at its current value until Phase 0
  confirms branch topology, check freshness needs, and acceptable CI cost. A
  later change may set it to `true`, but it is not part of this default grant.
- Do not enable `require_code_owner_review` until a human/team ownership model
  exists and has been reviewed.
- Add only verified check contexts to the rulesets. Exact names are a required
  input to Ryan's grant.

### Phase 3 — staging2 header control

Owner: Codex designs; Kiro reviews; Cursor implements only after a separate Ryan
grant because this may change deployment workflow or SiteGround behavior.

The current monitor remains the source of live evidence. Choose one design:

**Option A — repository-owned static contract:**

- Store the intended header policy in a tracked, testable configuration or
  server-side artifact.
- Add a pre-merge test that verifies the artifact contains the required CSP,
  HSTS, and Referrer-Policy contract.
- Keep a post-deploy curl monitor for actual staging2 behavior.
- Treat a mismatch between static intent and live headers as a deployment or
  environment incident.

**Option B — candidate deployment gate:**

- Deploy the PR candidate to an isolated staging target before merge.
- Run the live header check against that candidate.
- Make the candidate result a required PR status check.
- Define cleanup, credentials, cost, and failure behavior before implementation.

**Option C — promotion gate:**

- Keep merge-to-staging and staging2 deployment separate from promotion to a
  later target.
- Use the live header check to block promotion after staging2 verification.
- Do not describe this as a pre-merge gate until the promotion workflow exists.

The default recommendation is Option A if the header source can be made
repository-owned without changing live behavior. Otherwise use Option C and keep
the current monitor as a post-deploy control until the promotion workflow is
authorized. Do not add the monitor's status name directly to the current
`staging-integrity-gates` ruleset.

## 4. ConvMem policy boundary

Do not apply the willowyhollow target to `alanmz-crypto/convmem` automatically.

The current ConvMem ruleset has stronger status checks and strict freshness, but
also has a repository-role bypass actor. Resolve that actor and document the
break-glass policy in a separate, Ryan-authorized ConvMem change if needed.

The fact that both rulesets have zero required approvals is not enough to make
their desired states identical. WordPress is review required by default;
routine reversible ConvMem work may use bounded autonomy.

## 5. Authorization block for a future implementation

The following values are proposed, not authorized:

```text
Authorized external changes: NONE in this draft.

Potential future grant A:
Resource: alanmz-crypto/willowyhollow-dev ruleset 19155375
Operation: set rules.pull_request.required_approving_review_count
Final value: 1

Potential future grant B:
Resource: alanmz-crypto/willowyhollow-dev ruleset 19155380
Operation: set rules.pull_request.required_approving_review_count
Final value: 1

Potential future grant C:
Resource: alanmz-crypto/willowyhollow-dev repository workflow files
Operation: add or rename a pull-request plugin-lock check after Phase 0 confirms
the exact job context
Final value: explicitly named workflow diff and resulting check-run context

Potential future grant D:
Resource: staging2.willowyhollow.com deployment path
Operation: implement the selected Phase 3 header-control design
Final value: exact workflow, tracked configuration, or SiteGround setting
named in a later grant
```

No operator should infer authorization for C or D from the approval of A or B.

## 6. Verification plan

### Before mutation

- Confirm the exact repository tip and clean implementation worktree.
- Capture the current ruleset JSON.
- Confirm actual check-run names and branch behavior.
- Obtain Ryan's exact grant for each external mutation.

### After workflow changes

- Run the workflow's local shell checks where possible.
- Open a disposable PR targeting `main` and one targeting `staging`.
- Confirm the expected theme and plugin-lock checks appear with stable names.
- Confirm a PR without one approval cannot merge.
- Confirm a qualifying approval permits merge only when all required checks pass.
- Confirm direct pushes are blocked or document the exact remaining path.

### After ruleset changes

- Re-read both rulesets through the GitHub API.
- Verify `required_approving_review_count`, status contexts, bypass actors,
  enforcement, and branch conditions.
- Do not test by attempting an unauthorized live merge.

### After any staging2 implementation

- Deploy only through the authorized path.
- Run the exact header checks against staging2.
- Check all six ledger observations again.
- Verify the deployment did not affect production or local practice configuration.
- Record whether the control is pre-merge, post-deploy, or promotion-blocking.

## 7. Risks and trade-offs

- One required approval adds human latency but matches the WordPress review rule.
- Strict status freshness may improve merge correctness while increasing CI cost;
  defer it until branch behavior is measured.
- A live candidate deployment gives stronger evidence than static checks but adds
  SiteGround credentials, cleanup, runtime, and cost.
- A post-deploy monitor is cheap and honest but cannot prevent the merge that
  triggered the deployment.
- Claude's review adds useful adversarial coverage on high-risk plans but should
  remain conditional so routine WordPress fixes do not pay an unnecessary review
  cost.

## 8. Acceptance criteria

- [ ] Phase 0 confirms every required GitHub status context by actual check-run
      evidence.
- [ ] The WordPress ruleset target requires one real human/team approval on both
      deploy branches, or Ryan records a different exact value.
- [ ] ConvMem bounded autonomy remains unchanged by this plan.
- [ ] Claude's advisory role is documented in the handoff and does not become a
      merge authority.
- [ ] The staging2 header design names when the check runs and what it can block.
- [ ] The final implementation grant names exact repositories, rulesets, fields,
      operations, and values.
- [ ] Kiro reviews the plan or implementation tip before execution.
- [ ] Copilot performs targeted audit or independent verification when the change
      affects safety, isolation, or deployment behavior.

I finished: [Arc none (ad-hoc)] implementation draft for review-gate enforcement.
Next step: Kiro reviews this draft and Ryan decides the exact Phase 0/Phase 2 grant.
Next lane: Kiro, then Ryan, then Cursor for authorized repository changes.
See my work: `docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`
