# Codex handoff: willowyhollow review-gate implementation draft

**Date:** 2026-09-18
**Author:** OpenAI Codex
**For:** Ryan, Kiro, Cursor, and the GitHub Copilot audit lane
**Arc:** none (ad-hoc)
**Status:** `POST_CLAUDE_AUDIT_REVISED` (2026-09-18; Track A plan to Kiro and live attribution to Crush, Track B to Ryan for an access decision)

## Goal

Turn Claude's audit of `626d3ba` into a safe implementation sequence for
`alanmz-crypto/willowyhollow-dev`: repair the live staging2 header defect
independently and defer the GitHub human-review gate until deployment credentials
and bot approvals are controlled. ConvMem's bounded-autonomy policy remains
separate. This handoff changes no GitHub ruleset, access, workflow, secret,
Cloudflare setting, or live SiteGround state.

## Accepted conclusions

1. **Track A is the live defect.** The latest of 25 WordPress PRs merged on
   2026-07-19; six staging2 header observations opened on 2026-09-08. Current
   staging2 replies through Cloudflare without CSP, HSTS, or Referrer-Policy.
   Investigate Cloudflare transforms, the pinned header plugin's live status,
   SiteGround, and preserved `.htaccess`; then seek an exact repair grant.
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

## Lane sequence

1. **Crush:** read-only attribution of the missing live headers across
   Cloudflare, SiteGround, preserved `.htaccess`, and WordPress plugins.
2. **Codex:** frames the exact Track A repair and any later Track B access
   architecture; Claude's adversarial audit of `626d3ba` is incorporated here.
3. **Kiro:** reviews Track A's sequence now and the exact repair design after
   attribution; reviews Track B only after Ryan chooses a credential-isolation
   path and an exact execution plan exists.
4. **Ryan:** grants each exact external change, chooses whether Track B is worth
   its access cost, and owns merge/ledger authority.
5. **Cursor:** implements separately granted header, workflow, or ruleset work.
6. **GitHub Copilot audit lane:** targeted security/isolation verification when
   the implementation warrants it.

## Next artifact

The detailed sequence, proposed values, authorization block, and acceptance
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

I finished: [Arc none (ad-hoc)] incorporated Claude's adversarial audit.
Next step: Kiro reviews Track A's sequence while Crush attributes the live headers; Ryan decides whether to fund Track B.
Next lane: Kiro and Crush for Track A, Ryan for Track B, then Cursor after exact grants.
See my work: `docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`
