# Handoff: CI Behavioral Merge Gate Closeout — Planning Package

**Date:** 2026-08-15

**Author:** Codex

**For:** Next review or execution agent
**Purpose:** Review the closeout planning package and finish the one remaining
external evidence step without reopening the shipped CI implementation.

## Resume state

| Field | Value |
|---|---|
| **State** | `DOCS_READY__NEGATIVE_CONTROL_PENDING` |
| **Branch** | `plan/2026-08-15-ci-behavioral-merge-gate-closeout` |
| **Tip** | `91bb4a5702310c3d304139167c8484a54abee140` |
| **Push status** | Pushed to `origin` with the explicit branch ref |
| **PR** | Not opened |
| **Unrelated worktree item** | Untracked `pylint-report.json`; preserve it |

## Goal and current system state

**Goal:** make ConvMem's behavioral CI merge gate discoverable, reviewable, and
provably enforced.

**Shipped system:** PR #187 merged as `c2c6429`. `.github/workflows/pylint.yml`
now runs a hermetic Python 3.12 `python -m pytest -q` job alongside Pylint.
The active `Protect Main` ruleset (`19156572`) requires exactly `pylint (3.12)`
and `pytest (3.12)` under strict status policy. The PR's CodeQL checks passed,
but CodeQL is not currently a required status in this ruleset.

**Honest boundary:** the implementation is live and required for ordinary
merges, but no deliberate failing PR has yet demonstrated that the required
pytest status turns red and that ordinary merge is refused.

## What Codex added

The closeout package is a docs-and-inventory change only:

1. [`docs/plans/ARCHITECTURE-ci-behavioral-merge-gate.md`](../plans/ARCHITECTURE-ci-behavioral-merge-gate.md)
   records the problem, decision, hermeticity contract, proof limits,
   break-glass policy, non-goals, and residual risks.
2. [`tests/ci-critical-invariants.txt`](../../tests/ci-critical-invariants.txt)
   lists 15 existing critical pytest modules. It is advisory and deliberately
   not wired into CI in v1.
3. [`docs/plans/VERIFY-ci-behavioral-merge-gate.md`](../plans/VERIFY-ci-behavioral-merge-gate.md)
   binds the shipped evidence to PR #187, workflow run `31875391865`, ruleset
   `19156572`, and the pending negative control.
4. [`docs/inter-model/LATEST.md`](LATEST.md) now points to this handoff.

Commit `91bb4a5` contains these four tracked changes. The preceding commit
`50fc766` contains Kiro's original planning handoff.

## Evidence already checked

- PR [#187](https://github.com/alanmz-crypto/convmem/pull/187) is merged.
- [Workflow run 31875391865](https://github.com/alanmz-crypto/convmem/actions/runs/31875391865)
  passed both `pylint (3.12)` and `pytest (3.12)`.
- `Protect Main` is active for `main`; required status policy is strict.
- `git diff --check` passed for the package.
- All 15 manifest paths exist on the branch.
- `convmem doctor` passed with two pre-existing non-fatal warnings.
- This session was indexed as a Codex Track A session.

No runtime code, workflow, ruleset, or production data was changed by Codex.

## Remaining action — Ryan-controlled negative control

Do not create or push a deliberate failing PR without Ryan's explicit external
change authorization. When authorized, use a disposable branch from current
`main`:

1. Add `assert False, "CI gate negative control"` to an existing tracked test.
2. Commit and push the disposable branch with an explicit refspec.
3. Open a PR targeting `main` and record its URL, head SHA, and Actions run URL.
4. Confirm `pytest (3.12)` is red for that exact tip.
5. Confirm ordinary merge is blocked by the required failing status.
6. Close the PR without merging, delete the disposable branch, and preserve the
   run/status evidence.

The arc closes only when both the red pytest result and blocked merge are
recorded in [`VERIFY-ci-behavioral-merge-gate.md`](../plans/VERIFY-ci-behavioral-merge-gate.md).
Then update the `LATEST.md` bullet from `BLOCKED_ON_RYAN` to the observed result,
commit, and push. Do not change the workflow or ruleset during that experiment.

## Review instructions for the next agent

- Review the architecture decision against the actual workflow and ruleset;
  especially retain the distinction between passing CodeQL and required CodeQL.
- Check that the manifest remains advisory and contains only existing paths.
- Treat the VERIFY record as `BLOCKED_ON_RYAN`, not as a completed enforcement
  proof.
- Do not create a `STATUS` file, add a collection gate, pin dependencies, or
  modify runtime code under this handoff; those are separate follow-up grants.
- Do not merge or create a PR. Ryan owns the review/merge decision.

## Leaving checklist

- [x] Architecture decision committed and pushed
- [x] Advisory invariant manifest committed and pushed
- [x] VERIFY record committed and pushed
- [x] `LATEST.md` points to this handoff
- [ ] Negative-control PR observed and documented
- [ ] Ryan review and merge decision

**Next lane:** Ryan for external negative-control authorization and final gate;
review agent for documentation critique only.
