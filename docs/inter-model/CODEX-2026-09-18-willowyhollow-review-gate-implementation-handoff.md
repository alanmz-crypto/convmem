# Codex handoff: willowyhollow review-gate implementation draft

**Date:** 2026-09-18
**Author:** OpenAI Codex
**For:** Ryan, Kiro, Cursor, and the GitHub Copilot audit lane
**Arc:** none (ad-hoc)
**Status:** `PHASE1_REPAIR_CANDIDATE` (2026-09-18; Kiro design PASS at `12401a1`, followed by a read-only Cloudflare challenge finding requiring targeted acceptance recheck; runtime CSP evidence, Ryan's HSTS choice, exact-value review, and grant remain; Track B deferred)

## Goal

Turn Claude's audit of `626d3ba` into a safe implementation sequence for
`alanmz-crypto/willowyhollow-dev`: repair the live staging2 header defect
independently and defer the GitHub human-review gate until deployment credentials
and bot approvals are controlled. ConvMem's bounded-autonomy policy remains
separate. This handoff changes no GitHub ruleset, access, workflow, secret,
Cloudflare setting, or live SiteGround state.

## Accepted conclusions

1. **Track A is the live defect.** The latest of 25 WordPress PRs merged on
   2026-07-19; six staging2 header observations opened on 2026-09-08. Crush's
   read-only origin check found that the server `.htaccess` lost a previously
   deployed header block during a July 12 rewrite. The header plugin is
   installed but inactive; the deploy workflow preserves the server file.
   Kiro PASSed the attribution-first sequence at `1363056`, requiring a
   single-owner header check and an explicit staging HSTS decision in the
   repair proposal.
2. **Track B cannot begin with a reviewer invite.** This private personal repo
   has only its owner as collaborator. A second approver gets write access;
   repository-scoped `SG_*` Actions secrets include the SiteGround SSH key.
   Isolate credentials before extending write access. An organization transfer
   alone does not remove repository-secret exposure.
3. **A numeric approval may be a bot approval.** The Cursor App has
   `pull_requests:write` and `cursor[bot]` submitted an `APPROVED` review on PR
   #2. Its successful Router and Approver check is distinct from an approving
   review. A future gate must prove bot-only approval cannot satisfy its human
   requirement; all-path human CODEOWNERS is a candidate mechanism.
4. The existing `theme-engine` and `plugin-lock` PR jobs already run on both
   branches and reported success on historical PRs. A fresh PR is still needed
   before a ruleset change. No PR workflow addition is proposed.
5. GitHub says the unattributed-Copilot extra-approval setting has no effect
   while required approvals remain zero. ConvMem's `RepositoryRole` actor id
   `5` is Admin with an `always` bypass. Its bounded-autonomy and bypass policy
   stay separate from WordPress.
6. Cloudflare or a plugin change cannot be inferred from public response
   headers alone. The live monitor is post-deploy evidence; a true pre-merge
   header gate would require an isolated PR candidate deployment.
7. ConvMem remains the cross-repository comparison/handoff home. An executable
   WordPress plan belongs in `willowyhollow-dev` when one is authorized, with
   deliberate access for its reviewers and a link from ConvMem.
8. Ryan's original local web-design model quality/cost question remains a
   separate unanswered model-routing slice. Claude's audit of the ruleset plan
   does not answer it or create a standing Claude review requirement.
9. A fresh public GET found a Cloudflare-generated `/wp-admin/` `403`
   (`cf-mitigated: challenge`) with its own CSP and Referrer-Policy. That is a
   separate edge-owned response, not a duplicate origin policy. The SiteGround
   `.htaccess` candidate cannot control it. Public origin-served `200`/`404`
   responses still lack all three headers; no browser canary was run because
   this Codex session had no connected browser.

## Lane sequence

1. **Crush:** Phase 0 attribution and a read-only six-page static CSP spot
   check are complete. No definite static source mismatch was found, but
   current browser interactions and CSP violations remain untested. The
   proposed local Chrome DevTools override canary is Crush's next
   investigative slice; it changes no hosted response. This Codex session
   had no connected browser to run it.
2. **Codex:** this draft frames a narrow `.htaccess` repair candidate and
   stop/rollback gates; it does not approve the policy or an external write.
3. **Kiro:** the Track A sequence passed at `1363056` and the Phase 1 design
   passed at `12401a1`. Targeted recheck is needed for the newly documented
   edge-challenge response split, then exact-value review after runtime CSP
   evidence. Track B still awaits Ryan's credential-isolation decision.
4. **Ryan:** grants each exact external change, chooses whether Track B is worth
   its access cost, and owns merge/ledger authority.
5. **Cursor:** implements separately granted header, workflow, or ruleset work.
6. **GitHub Copilot audit lane:** targeted security/isolation verification when
   the implementation warrants it.

## Next artifact

The detailed sequence, proposed values, authorization boundary, and acceptance
checks are in:

`docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`

## Explicit non-goals

- Do not edit rulesets or branch protection in this slice.
- Do not invite a second repository writer while `SG_*` remains accessible to
  workflows on arbitrary repository branches.
- Do not add the staging2 header check to a required-check list until its timing
  and check-run behavior are designed and verified.
- Do not create CODEOWNERS entries for AI products without a real GitHub identity
  and Ryan's approval.
- Do not change ConvMem's ruleset merely to make it resemble willowyhollow.
- Do not investigate or remediate the four Dependabot findings in this slice;
  track them as a separate security task.

## Handoff acceptance

- [x] Claude's F1–F6 findings are incorporated or resolved with live API/docs
      evidence; the Cursor App approval capability is explicitly recorded.
- [x] Track A can proceed without adding a writer or changing a ruleset.
- [x] Track B keeps zero approvals until secrets are isolated and a human-only
      gate has been verified on both branches.
- [x] Kiro, Copilot audit, Cursor, and Ryan retain distinct responsibilities.
- [x] The local web-design model-routing question is identified as a separate
      open slice.
- [x] Kiro's two Phase 1 conditions are incorporated: verify one effective
      noncontradictory owner/value for each header, and make staging HSTS
      lifetime/subdomain/preload an explicit Ryan decision.
- [x] The six-page static CSP spot check is recorded without treating it as
      browser compatibility proof.
- [x] Kiro PASSed the Phase 1 design at `12401a1`, without granting an
      enforcing SiteGround change.
- [ ] Kiro rechecks the edge-challenge acceptance clarification. Crush's
      local Chrome override canary, or a separately authorized report-only
      trial implemented by Cursor, demonstrates runtime CSP compatibility.
      Kiro reviews the exact final values/evidence before Ryan grants an
      enforcing SiteGround change. Ryan explicitly accepts or revises the
      HSTS/CSP values, with Kiro re-review if they change.

I finished: [Arc none (ad-hoc)] narrowed the header acceptance gate to origin-served responses after finding a Cloudflare challenge.
Next step: Kiro rechecks that distinction; obtain runtime CSP canary evidence and Ryan's HSTS choice before exact-value review and any enforcing grant.
Next lane: Kiro, a separately authorized canary/verification lane, Ryan for policy, Kiro for exact values, then Ryan/Cursor for any grant and execution.
See my work: `docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`
