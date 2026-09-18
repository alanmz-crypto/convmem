# Codex handoff: willowyhollow review-gate implementation draft

**Date:** 2026-09-18
**Author:** OpenAI Codex
**For:** Ryan, Kiro, Cursor, and the GitHub Copilot audit lane
**Arc:** none (ad-hoc)
**Status:** `CLAUDE_AUDIT_READY` (revised 2026-09-18)

## Goal

Turn the Claude review-gate investigation into a safe implementation sequence for
`alanmz-crypto/willowyhollow-dev`, while preserving ConvMem's separate bounded
autonomy policy. This handoff is a plan and implementation draft. It does not
change GitHub rulesets, workflows, CODEOWNERS, or live SiteGround state.

## Accepted conclusions

1. WordPress remains review required. The target is one independent human
   approval on both `main` and `staging`, conditional on adding a second eligible
   human reviewer. GitHub currently lists only the owner as collaborator, and
   PR authors cannot approve their own PRs. Setting count `1` now would block
   owner-authored PRs.
2. ConvMem is a separate policy surface. Routine reversible ConvMem work may
   remain under bounded autonomy; architecture, security, and external
   configuration work remains review required. This plan does not raise
   ConvMem's universal approval count.
3. GitHub must enforce real reviewer identities or teams. It cannot enforce
   abstract AI lanes such as “Kiro review” or “Claude review” unless a concrete
   GitHub account, team, app, or service account represents that role.
4. Claude has a defined advisory role: adversarial architecture and model-
   allocation review for high-risk or ambiguous deployment, security, ruleset,
   and cross-repository decisions. Ryan requested Claude's audit of this draft.
   Claude does not implement, merge, authorize external changes, or replace
   Kiro sign-off or the Copilot audit lane.
5. Live GitHub evidence corrects the original local-checkout assumption: the
   current PR workflow already defines `theme-engine` and `plugin-lock`, and
   both contexts passed on representative `main` and `staging` PRs. Fresh PR
   evidence is still needed before a ruleset mutation. The older, heavily dirty
   local checkout is not authoritative for current GitHub workflow contents.
6. A live staging2 header monitor cannot become a pre-merge required check by
   renaming it. A post-deploy result arrives after the merge that triggered the
   deploy. Repair the actual server or WordPress header source and verify the
   live response. A true pre-merge check needs an isolated PR candidate
   deployment; a static file assertion cannot prove the current live headers.
7. `strict_required_status_checks_policy` stays a deliberate decision. It is not
   copied from ConvMem automatically because willowyhollow's `main` and
   `staging` branches are independent deploy targets and strict freshness adds
   CI and merge friction.
8. The first executable WordPress slice needs a real second reviewer, then a
   narrowly scoped ruleset change (`required_approving_review_count=1` and
   `require_last_push_approval=true` on each branch). No PR workflow addition
   is currently needed. A tracked header assertion cannot prove the live
   response while the deploy preserves server `.htaccess`.
9. ConvMem is appropriate for the cross-repo comparison and model handoff.
   After this audit, the executable WordPress plan belongs in
   `willowyhollow-dev` with its workflow/ruleset PR; ConvMem retains a link.

## Lane sequence

1. **Codex:** the read-only ruleset, workflow, collaborator, and historical PR
   check inventory is in the revised implementation draft.
2. **Claude:** adversarial audit of reviewer feasibility, ruleset semantics,
   staging2 timing, and the chosen model allocation on this exact revision.
3. **Kiro:** design and sign-off review of the audited plan.
4. **Ryan:** chooses a reviewer model, grants exact GitHub or SiteGround changes,
   and owns merge/ledger authority.
5. **Cursor:** implements only the approved repository or deployment changes.
6. **GitHub Copilot audit lane:** performs an independent targeted safety,
   isolation, or post-implementation verification pass when warranted.

## Next artifact

The detailed sequence, proposed values, authorization block, and acceptance
checks are in:

`docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`

## Explicit non-goals

- Do not edit rulesets or branch protection in this slice.
- Do not add the staging2 header check to a required-check list until its timing
  and check-run behavior are designed and verified.
- Do not create CODEOWNERS entries for AI products without a real GitHub identity
  and Ryan's approval.
- Do not change ConvMem's ruleset merely to make it resemble willowyhollow.
- Do not investigate or remediate the four Dependabot findings in this slice;
  track them as a separate security task.

## Handoff acceptance

- [x] The implementation draft names every proposed repository, ruleset, field,
      and value that would require Ryan authorization.
- [x] A read-only historical check-context inventory precedes any ruleset edit;
      a fresh PR check remains an execution prerequisite.
- [x] The draft distinguishes pre-merge gates from post-deploy monitors.
- [x] Claude's role is recorded as advisory and bounded, not as a merge or
      implementation lane.
- [x] Kiro and Copilot responsibilities remain distinct.

I finished: [Arc none (ad-hoc)] corrected Codex implementation handoff draft.
Next step: Claude audits the revised plan; Kiro reviews after audit.
Next lane: Claude, then Kiro and Ryan; Cursor only if authorized.
See my work: `docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`
