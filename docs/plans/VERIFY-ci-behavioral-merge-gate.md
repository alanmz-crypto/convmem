# Verify Plan — CI Behavioral Merge Gate

```
Planning Status

Phase:        Verify (CI behavioral merge gate)
Characters:   Independent reviewer
Functions:    Confirm shipped CI behavior and preserve honest limits
Lanes:        Codex (documentation); Ryan (external experiment and GATE)
Authority:    Post-implementation evidence; do not treat prior chat claims as proof
```

**Subject:** merged CI gate from PR #187

**Merge SHA:** `c2c6429f6cfbd8ebd528be39acf2168d9f3f2964`

**PR:** [#187](https://github.com/alanmz-crypto/convmem/pull/187)

**Workflow run:** [Pylint run 31875391865](https://github.com/alanmz-crypto/convmem/actions/runs/31875391865)

**Architecture:** [`ARCHITECTURE-ci-behavioral-merge-gate.md`](ARCHITECTURE-ci-behavioral-merge-gate.md)
**Goal:** prove what shipped, identify what is still unproven, and avoid closing
the arc until the negative-control experiment demonstrates enforcement.

## Human consequence

**Consequence:** The ordinary merge path now requires both behavioral pytest and
Pylint status checks, but the closeout remains incomplete until a known-bad PR
is observed to be blocked.

| | |
|---|---|
| **Who** | Cursor shipped #187; Ryan changed `Protect Main`; Codex records the closeout |
| **What** | Hermetic Python 3.12 pytest check required alongside Pylint |
| **When** | Merged to `main` on 2026-08-15 as `c2c6429` |
| **Why** | Existing behavioral tests were not previously merge-gating |
| **How** | GitHub required-status checks reject an ordinary merge when either is not green |

**TL;DR:** Shipped behavior is verified green; enforcement remains
`BLOCKED_ON_RYAN` pending one disposable failing PR.

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| PR #187's merged workflow and `Protect Main` required contexts | Changing Actions or ruleset configuration |
| Hermetic pytest contract and advisory invariant manifest | Collection-regression enforcement |
| One negative-control PR proving ordinary merge refusal | Coverage, performance, or platform matrices |

## V0 — Shipped implementation

| ID | Check | Result | Evidence |
|----|-------|--------|----------|
| V0a | PR #187 merged to `main` | **PASS** | Merge SHA `c2c6429`; merged 2026-08-15 |
| V0b | Exact PR run executed Pylint and pytest on Python 3.12 | **PASS** | Run `31875391865`: `pylint (3.12)` and `pytest (3.12)` success |
| V0c | Workflow runs the full command rather than an ignore-based subset | **PASS** | `.github/workflows/pylint.yml`: `python -m pytest -q` |
| V0d | Clean-runner config is supplied | **PASS** | `CONVMEM_CONFIG=/tmp/convmem-ci/config.toml` in the pytest job |

## V1 — Ruleset enforcement

| ID | Check | Result | Evidence |
|----|-------|--------|----------|
| V1a | `Protect Main` is active for `refs/heads/main` | **PASS** | Ruleset `19156572`, enforcement `active` |
| V1b | Pylint is required | **PASS** | Required context `pylint (3.12)` |
| V1c | pytest is required | **PASS** | Required context `pytest (3.12)` |
| V1d | Status checks are strict | **PASS** | `strict_required_status_checks_policy=true` |
| V1e | CodeQL is required by this ruleset | **N/A** | CodeQL passed on #187 but is not in the required-status list |

## V2 — Advisory invariant inventory

| ID | Check | Result | Evidence |
|----|-------|--------|----------|
| V2a | Manifest exists and is advisory | **PASS** | `tests/ci-critical-invariants.txt`; no workflow references it |
| V2b | Every listed module exists on this branch | **PASS** | Local path check covers all 15 entries |
| V2c | Manifest disappearance is mechanically detected | **SKIP** | Deferred collection-regression hardening; not v1 scope |

## V3 — Negative control

**Status: `BLOCKED_ON_RYAN`.** This requires an external GitHub mutation and
observation cycle that is not performed by this documentation pass.

Ryan's one-shot procedure:

1. Create a disposable branch from current `main`.
2. Add one deliberate `assert False, "CI gate negative control"` to an existing
   test, commit it, and push it explicitly.
3. Open a PR targeting `main`; record the PR URL, head SHA, and Actions run URL.
4. Confirm `pytest (3.12)` is red and capture the failed job link.
5. Confirm the PR's ordinary merge control reports blocked by the required
   failing status; record that status evidence.
6. Close the PR without merging, delete the disposable branch, and remove the
   deliberate failure from any local copy.

The experiment passes only when both the failed pytest result and the blocked
ordinary merge are visible for the same disposable PR tip. A passing workflow
on #187 is not a negative-control result.

## V4 — Independent sign-off

| ID | Check | Result |
|----|-------|--------|
| V4a | All shipped implementation and ruleset checks above remain true | **PASS** |
| V4b | Negative control proves a bad candidate is blocked | **BLOCKED_ON_RYAN** |
| V4c | Arc may be called fully closed | **BLOCKED_ON_RYAN** |

## Evidence log

```text
VERIFY-ci-behavioral-merge-gate — merge c2c6429 — Codex — 2026-08-15
V0: PASS — PR #187 run 31875391865 passed pylint (3.12) and pytest (3.12).
V1: PASS — Protect Main ruleset 19156572 requires both contexts strictly.
V2: PASS — advisory manifest added; enforcement intentionally deferred.
V3: BLOCKED_ON_RYAN — disposable failing PR and merge-refusal observation not run.
Mechanical: PASS for shipped state; closeout: BLOCKED_ON_RYAN.
Sign-off: Ryan must perform or authorize the external negative-control cycle.
```
