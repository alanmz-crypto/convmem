# Architecture: CI Behavioral Merge Gate

| Field | Value |
|-------|-------|
| **Status** | Proposed closeout record; implementation already merged |
| **Owner** | Ryan owns ruleset scope and merge; Codex maintains the planning record |
| **Scope** | GitHub-hosted behavioral testing for ordinary pull requests into `main` |
| **Decision** | Require the hermetic Python 3.12 pytest check alongside the existing Pylint regression check |

## Problem

ConvMem had a substantial behavioral test suite, but GitHub Actions previously
ran static analysis without executing that suite. A pull request could therefore
pass the required Pylint check while introducing a failing or undiscovered test.
The goal is to make the existing behavioral evidence a normal merge condition,
without turning this repair into a new test architecture.

## Decision

Keep the additive `pytest` job in `.github/workflows/pylint.yml`. It checks out
the proposed commit on a clean Ubuntu runner, uses Python 3.12, installs the
repository requirements, creates a temporary ConvMem configuration, and runs
`python -m pytest -q`. The `Protect Main` ruleset requires the resulting
`pytest (3.12)` status together with `pylint (3.12)` under strict status policy.

The checks remain independent and may run in parallel. Merge requires all
required checks to pass for the exact proposed commit; no ordering between
pytest and Pylint is part of the contract.

## Hermeticity contract

The behavioral job must succeed on a clean GitHub runner without:

- Ollama, a DeepSeek key, or any live model call;
- Ryan's home directory or the live ConvMem corpus;
- a production Chroma directory or Restic credentials; or
- systemd services or other workstation-only state.

The workflow supplies `CONVMEM_CONFIG=/tmp/convmem-ci/config.toml` and the
tests explicitly skip or fixture-isolate behavior that requires live services.
Any new test that requires workstation state is a test-harness defect to fix,
not a reason to weaken the required gate.

## What the gate proves

For a normal pull request, GitHub has executed the collected pytest suite and
the Pylint regression gate on the proposed commit, and the ruleset refuses an
ordinary merge while either required status is failing, missing, or stale under
the strict policy.

This does not prove that pytest collected every intended test, that CodeQL is a
required merge condition, or that a privileged break-glass bypass is impossible.
The current ruleset records CodeQL success on #187 but requires only `pylint
(3.12)` and `pytest (3.12)`.

## Critical-invariant manifest

`tests/ci-critical-invariants.txt` names a small advisory set of tests whose
disappearance from collection would be catastrophic. The manifest is not a
second test runner and is not enforced in v1. It is a durable inventory for a
future collection-regression check. Paths must exist on the branch when the
manifest is updated; the initial list uses the current CG-1/CG-2 proof files.

## Relationship to other gates

- **Pylint:** required independently through the existing regression baseline.
- **CodeQL:** useful security analysis and currently observed on the PR, but not
  required by this ruleset decision.
- **BugBot and human review:** independent review surfaces; neither substitutes
  for the behavioral status check.
- **Future collection gate:** intentionally deferred until this basic workflow
  has stable evidence over several merges.

## Break-glass and residual risk

The repository-role bypass remains as a break-glass escape hatch while the gate
beds in. A bypass is an emergency exception, not evidence that the checks passed,
and should carry an explicit Ryan justification naming the reason and tip.

The main residual risks are unpinned pytest installation, silent test-discovery
loss, runtime drift as the suite grows, and permanent reliance on the bypass.
Pinning dependencies and enforcing the manifest are follow-up hardening work;
neither is silently included in this closeout.

## Non-goals

- coverage-percentage, performance, or benchmark gating;
- Python or operating-system matrices;
- live Ollama/DeepSeek tests;
- test refactoring or adding behavioral tests; or
- changing the workflow or ruleset as part of this documentation closeout.

## Acceptance

The arc is ready for closeout when the architecture record, advisory manifest,
and VERIFY record are committed; `LATEST.md` points to the shipped gate; and a
throwaway deliberately failing PR has produced evidence that `pytest (3.12)`
turns red and the ruleset blocks ordinary merge. Until that experiment occurs,
the implementation is live but enforcement is not independently demonstrated.
