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
**Goal:** prove what shipped, identify what is still unproven, and record the
negative-control experiment that demonstrates enforcement.

## Human consequence

**Consequence:** The ordinary merge path now requires both behavioral pytest and
Pylint status checks, and a known-bad PR has now been observed to be blocked.
The technical evidence closeout is complete and the closeout documentation merged via #189; Arc CI Kryptonite is CLOSED. No docs-merge gate remains.

| | |
|---|---|
| **Who** | Cursor shipped #187; Ryan changed `Protect Main`; Codex records the closeout |
| **What** | Hermetic Python 3.12 pytest check required alongside Pylint |
| **When** | Merged to `main` on 2026-08-15 as `c2c6429` |
| **Why** | Existing behavioral tests were not previously merge-gating |
| **How** | GitHub required-status checks reject an ordinary merge when either is not green |

**TL;DR:** Shipped behavior is verified green and the negative control proved
that ordinary merge is blocked by a failing required pytest check.

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

**Status: `PASS`.** The experiment used disposable PR [#188](https://github.com/alanmz-crypto/convmem/pull/188),
then closed it without merge and deleted its branch.

| ID | Check | Result | Evidence |
|----|-------|--------|----------|
| V3a | Deliberately failing assertion fails locally | **PASS** | Commit `02ee739`; targeted run: 9 passed, 1 failed |
| V3b | Disposable PR targets `main` at the tested tip | **PASS** | PR #188; head `02ee7392645e8d324c0aaa3fcc62fce610507b7c` |
| V3c | Required pytest check turns red | **PASS** | [`pytest (3.12)` failed](https://github.com/alanmz-crypto/convmem/actions/runs/31920649555/job/95099894863) |
| V3d | Ordinary non-bypass merge path is unsatisfied | **PASS** | PR #188 `mergeStateStatus=BLOCKED`; `mergeable=MERGEABLE` |
| V3e | Break-glass bypass is distinguished and untouched | **PASS** | Ruleset reports `current_user_can_bypass=always`; bypass not exercised |
| V3f | Disposable PR and branch are removed without merge | **PASS** | PR #188 closed; remote and local branch deleted |

The experiment passes because the same PR tip showed a failed required pytest
result and a blocked ordinary merge path. The privileged bypass is expected
break-glass capability, not a failure of the gate, and was not exercised.

## V4 — Independent sign-off

| ID | Check | Result |
|----|-------|--------|
| V4a | All shipped implementation and ruleset checks above remain true | **PASS** |
| V4b | Negative control proves a bad candidate is blocked | **PASS** |
| V4c | Arc CI Kryptonite evidence package is complete | **PASS** — closeout documentation merged via #189 |

## Evidence log

```text
VERIFY-ci-behavioral-merge-gate — merge c2c6429; negative control 02ee739 — Codex — 2026-08-16
V0: PASS — PR #187 run 31875391865 passed pylint (3.12) and pytest (3.12).
V1: PASS — Protect Main ruleset 19156572 requires both contexts strictly.
V2: PASS — advisory manifest added; enforcement intentionally deferred.
V3: PASS — PR #188 run 31920649555 failed pytest (3.12); ordinary merge was BLOCKED; bypass unused.
Mechanical: PASS; Arc CI Kryptonite evidence closeout complete.
Sign-off: Mendel PASS at review target 062750f; Ryan authorized and observed the negative control; docs merge remains Ryan GATE.
```
