# Codex handoff: willowyhollow review-gate implementation draft

**Date:** 2026-09-18
**Author:** OpenAI Codex
**For:** Ryan, Kiro, Cursor, and the GitHub Copilot audit lane
**Arc:** none (ad-hoc)
**Status:** `DRAFT_NOT_STARTED`

## Goal

Turn the Claude review-gate investigation into a safe implementation sequence for
`alanmz-crypto/willowyhollow-dev`, while preserving ConvMem's separate bounded
autonomy policy. This handoff is a plan and implementation draft. It does not
change GitHub rulesets, workflows, CODEOWNERS, or live SiteGround state.

## Accepted conclusions

1. WordPress remains review required. The first target is one approving human or
   team review on both `main` and `staging` in `willowyhollow-dev`.
2. ConvMem is a separate policy surface. Routine reversible ConvMem work may
   remain under bounded autonomy; architecture, security, and external
   configuration work remains review required. This plan does not raise
   ConvMem's universal approval count.
3. GitHub must enforce real reviewer identities or teams. It cannot enforce
   abstract AI lanes such as “Kiro review” or “Claude review” unless a concrete
   GitHub account, team, app, or service account represents that role.
4. Claude has a defined optional role: adversarial architecture and model-
   allocation review for high-risk or ambiguous deployment, security, ruleset,
   and cross-repository decisions. Claude does not implement, merge, authorize
   external changes, or replace Kiro sign-off or the Copilot audit lane.
5. The ruleset status contexts must be verified against actual GitHub check runs
   before changing them. The current workflow has jobs named `deploy-production`,
   `deploy-staging`, and `theme-gate`; it does not visibly define jobs named
   `theme-engine` or `plugin-lock`.
6. A live staging2 header monitor cannot become a pre-merge required check by
   renaming it. A post-deploy result arrives after the merge that triggered the
   deploy. Header enforcement needs either a pre-merge candidate environment, a
   repository-owned static contract, or a later promotion gate.
7. `strict_required_status_checks_policy` stays a deliberate decision. It is not
   copied from ConvMem automatically because willowyhollow's `main` and
   `staging` branches are independent deploy targets and strict freshness adds
   CI and merge friction.

## Lane sequence

1. **Crush:** read-only inventory of rulesets, workflow check contexts, branch
   behavior, and the six staging2 observations. Use Qwen3.7-Max by default;
   DeepSeek V4 Pro or Flash remains a Crush fallback when Qwen is busy or Cursor
   budget is unavailable.
2. **Codex:** architecture and execution plan, including exact authorization
   requests and the model-cost decision.
3. **Claude:** optional adversarial challenge of the plan and its enforcement
   assumptions.
4. **Kiro:** design and sign-off review of the plan or implementation tip.
5. **Ryan:** grants exact GitHub or SiteGround changes and owns merge/ledger
   authority.
6. **Cursor:** implements the approved workflow or repository changes.
7. **GitHub Copilot audit lane:** performs an independent targeted safety,
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

- [ ] The implementation draft names every proposed repository, ruleset, field,
      and value that would require Ryan authorization.
- [ ] A read-only check-context inventory precedes any ruleset edit.
- [ ] The draft distinguishes pre-merge gates from post-deploy monitors.
- [ ] Claude's new role is recorded as advisory and bounded, not as a merge or
      implementation lane.
- [ ] Kiro and Copilot responsibilities remain distinct.

I finished: [Arc none (ad-hoc)] Codex implementation handoff draft.
Next step: Kiro reviews the plan and Ryan grants any exact external changes.
Next lane: Kiro, then Ryan, then Cursor if authorized.
See my work: `docs/plans/IMPLEMENTATION-willowyhollow-review-gate-enforcement.md`
