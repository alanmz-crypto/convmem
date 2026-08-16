# Handoff: CI Behavioral Merge Gate Closeout — Planning Package

**Date:** 2026-08-15

**Author:** Codex

**For:** Next review or execution agent
**Purpose:** Review the closeout planning package and finish the one remaining
external evidence step without reopening the shipped CI implementation.

## Resume state

| Field | Value |
|---|---|
| **State** | `NEGATIVE_CONTROL_PASS__READY_FOR_RYAN_DOCS_GATE` |
| **Branch** | `plan/2026-08-15-ci-behavioral-merge-gate-closeout` |
| **Review target** | Current head of `plan/2026-08-15-ci-behavioral-merge-gate-closeout`; reviewer must record the exact SHA from `git rev-parse HEAD` |
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

**Closeout result:** a deliberate failing PR has now demonstrated that the
required pytest status turns red and that ordinary merge is refused. The
technical evidence package is complete; Ryan's documentation-branch merge
decision remains the final process gate.

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
   `19156572`, and completed negative-control PR #188.
4. [`docs/inter-model/LATEST.md`](LATEST.md) now points to this handoff.

Commit `91bb4a5` contains the architecture, VERIFY, manifest, and initial
`LATEST.md` package. Commit `2cb5b4c` adds this agent-ready handoff and the final
`LATEST.md` pointer. The preceding commit `50fc766` contains Kiro's original
planning handoff.

## Evidence already checked

- PR [#187](https://github.com/alanmz-crypto/convmem/pull/187) is merged.
- [Workflow run 31875391865](https://github.com/alanmz-crypto/convmem/actions/runs/31875391865)
  passed both `pylint (3.12)` and `pytest (3.12)`.
- Disposable [PR #188](https://github.com/alanmz-crypto/convmem/pull/188) tested
  head `02ee7392645e8d324c0aaa3fcc62fce610507b7c`.
- [PR #188 pytest job](https://github.com/alanmz-crypto/convmem/actions/runs/31920649555/job/95099894863)
  failed as intended; Pylint passed and the ordinary merge state was `BLOCKED`.
- The repository-role bypass was visible as expected and was not exercised.
- PR #188 was closed without merge; its remote and local disposable branches
  and worktree were deleted.
- `Protect Main` is active for `main`; required status policy is strict.
- `git diff --check` passed for the package.
- All 15 manifest paths exist on the branch.
- `convmem doctor` passed with two pre-existing non-fatal warnings.
- This session was indexed as a Codex Track A session.

No runtime code, workflow, ruleset, or production data was changed by Codex.

## Closeout result — negative control complete

The Ryan-authorized disposable experiment is recorded in
[`VERIFY-ci-behavioral-merge-gate.md`](../plans/VERIFY-ci-behavioral-merge-gate.md):

- PR #188 added one deliberate failing assertion and ran at head `02ee739`.
- Required `pytest (3.12)` failed; Pylint and CodeQL passed.
- The ordinary merge path reported `BLOCKED`.
- The always-available repository-role bypass was recorded but not exercised.
- PR #188 was closed without merge and its branch/worktree were deleted.

No further CI experiment is needed. Ryan's remaining action is review and merge
of the documentation closeout branch.

## Review instructions for the next agent

- Record the exact revision reviewed with `git rev-parse HEAD`; do not infer
  the reviewed SHA from this handoff.
- Review the architecture decision against the actual workflow and ruleset;
  especially retain the distinction between passing CodeQL and required CodeQL.
- Check that the manifest remains advisory and contains only existing paths.
- Treat the VERIFY record as the completed enforcement proof; Ryan still owns
  the documentation merge decision.
- Do not create a `STATUS` file, add a collection gate, pin dependencies, or
  modify runtime code under this handoff; those are separate follow-up grants.
- Do not merge or create a PR. Ryan owns the review/merge decision.

## Leaving checklist

- [x] Architecture decision committed and pushed
- [x] Advisory invariant manifest committed and pushed
- [x] VERIFY record committed and pushed
- [x] `LATEST.md` points to this handoff
- [x] Negative-control PR observed and documented
- [ ] Ryan review and merge decision

**Next lane:** Ryan for external negative-control authorization and final gate;
review agent for documentation critique only.
