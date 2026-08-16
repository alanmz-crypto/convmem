# Architecture: Pinwheel Pytest CI

| Field | Value |
|---|---|
| **Status** | Planning package; implementation not authorized by this document |
| **Owner** | Ryan owns execution, disposable PRs, external GitHub state, and merge; Codex owns this record |
| **Scope** | Reproducible pytest installation and explicit critical-module collection in the existing required pytest job |
| **Base** | `main` at `bc83c85d0522023ea6e404bff4aaed135c47815a` when this plan was prepared |
| **Decision** | Exact pytest pin in both jobs; version logging; job-scoped CI contract test; per-module manifest checker using pytest exit status |

## Problem

Arc CI Kryptonite shipped the required hermetic Python 3.12 pytest job and
proved that a deliberately failing test blocks ordinary merge. It deliberately
left two follow-on risks open: the workflow installs pytest without a patch
pin, and the named critical tests could disappear or collect zero tests while
the remaining suite stays green.

Pinwheel closes those two risks without reopening Kryptonite, changing required
status contexts, or introducing general test-count governance.

## Decision

Keep `.github/workflows/pylint.yml` as the workflow and keep the existing
`pytest (3.12)` status context. In both the `pylint` and `pytest` jobs, install
the same approved version with exact `pytest==X.Y.Z` syntax. The version is not
guessed in planning: Cursor selects it from a fresh Python 3.12 installation
on the current runner and records the selection in a workflow comment and the
CI contract test.

Both jobs log `python -m pytest --version` after installation. This is audit
evidence of what the runner actually imported; it is not the enforcement
mechanism by itself.

The pytest job adds a dedicated manifest-checker step after the hermetic config
is prepared and before the full test command. The step runs under the same
`CONVMEM_CONFIG=/tmp/convmem-ci/config.toml` environment as the full suite.

The new `tests/test_ci_contract.py` is a focused contract test. It is added to
`tests/ci-critical-invariants.txt`, intentionally taking the manifest from 15
to 16 entries. It must assert, scoped to the named jobs, that:

1. both install sites contain the same approved exact `pytest==X.Y.Z` pin;
2. the pytest job still contains the full `python -m pytest -q` command; and
3. the pytest job still contains the exact manifest-checker invocation.

This prevents a green required job from hiding deletion of either the full
suite or the new checker while the two install pins remain present.

## Manifest-checker contract

The checker accepts the manifest as a small explicit set, not as a census:

- ignore documented comments and blank lines;
- accept only repository-relative pytest-module paths under `tests/`;
- reject absolute paths, option-like values, malformed paths, and duplicates;
- require each path to exist as a regular file before collection;
- invoke `python -m pytest --collect-only -q <path>` once per path;
- treat only return code `0` as successful collection;
- treat return code `5` (no tests collected), collection errors, usage errors,
  and every other nonzero return code as failure; and
- print the command/output for diagnosis without making textual output parsing
  part of the safety decision.

The checker does not parse pytest's human-readable collection count. Pytest's
exit status is the stable contract: zero means collection completed with at
least one collected item for the requested module; nonzero fails closed.

## Hermeticity and ordering

The checker must run after `Prepare hermetic CI config`, with the same
`CONVMEM_CONFIG` environment. It uses the same pinned interpreter selected by
the job. The intended pytest-job order is:

1. install dependencies and exact pytest pin;
2. log the installed pytest version;
3. prepare `/tmp/convmem-ci/config.toml`;
4. run the manifest checker; and
5. run the full `python -m pytest -q` suite.

The Pylint job logs its installed pytest version because it installs pytest,
but it does not run the manifest checker or full suite.

## What this proves

For the existing required `pytest (3.12)` status, Pinwheel proves that:

- both jobs install the reviewed exact pytest version;
- the pytest job still executes the full suite and checker;
- every listed critical module exists and collects successfully; and
- accidental pin drift, workflow-step deletion, manifest disappearance, and
  zero-collection controls turn the required pytest job red.

It does not prove that unlisted tests exist, that total suite size is stable,
that CodeQL is required, or that the privileged ruleset bypass is impossible.

## Relationship to other governance

- **Protect Main:** unchanged; `pylint (3.12)` and `pytest (3.12)` remain the
  only required status contexts under this arc.
- **CodeQL:** observed but not required; CodeQL Complex Therapy is separate.
- **Kryptonite:** closed; its negative control remains historical evidence and
  is not reused as proof of Pinwheel-specific controls.
- **Runtime and data:** no runtime, Chroma, ledger, production config, or
  corpus mutation is in scope.

## Non-goals

- changing rulesets, status-check names, or bypass policy;
- adding a coverage, performance, platform-matrix, or collection-count gate;
- pinning every repository dependency;
- changing pytest discovery rules or refactoring tests; or
- opening disposable PRs without Ryan's explicit authorization.

## Residual risks

- A malicious change could remove both the contract test and its manifest line;
  ordinary review remains part of the control boundary.
- The selected patch version will eventually need an intentional upgrade;
  upgrades must change the workflow and contract together and repeat the
  baseline/negative-control evidence.
- Pytest collection can still execute import-time test-module code; that is
  consistent with the full suite and remains a test-harness concern.

## Acceptance

The architecture is accepted for execution when the planning package remains
consistent with this decision, Kiro and ChatGPT's conditions are recorded, and
Ryan authorizes Cursor to implement on a branch based on current `main`. The
arc closes only after Pinwheel-specific negative controls produce a red
required pytest check, ordinary merge is blocked without bypass, restoration
produces a normal green PR, and VERIFY records the exact evidence.
