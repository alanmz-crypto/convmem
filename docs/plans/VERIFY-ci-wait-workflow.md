# Verify Plan — CI Wait Workflow

```
Planning Status

Phase:        Verify Planning
Characters:   Independent Reviewer, Test-First Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro or Ryan-named lane (sign-off); Ryan (GATE)
Authority:    Post-execute HITL — do not trust prior chat claims alone
```

**Subject:** CI-wait documentation arc on draft PR `#81`
**Repository:** `alanmz-crypto/convmem`
**Branch:** `plan/2026-07-22-ci-wait-workflow`
**Base:** `main`
**Architecture:** `docs/plans/ARCHITECTURE-ci-wait-workflow.md`
**Goal:** Independently prove the optional CI-wait documentation matches its
approved content, discovery, and governance boundaries.

**Report format:** For every numbered check, state **PASS / FAIL / SKIP /
DEFERRED** and one line of evidence. A command exit code, exact count, path
list, or quoted heading is evidence; a prior chat claim is not.

This is a read-only verification run. Cursor must not edit the PR branch,
resolve a failure, rerun CI, comment on the PR, merge, or create a ledger
record. On failure, preserve the evidence and return it to Ryan.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| PR `#81` exact tip and its six-file diff | Correcting findings during verification |
| Playbook structure and semantic content | Runtime behavior or full pytest |
| Architecture boundary and charter compatibility | Protocol, charter, Actions, hooks, doctor, standing register |
| Three router pointers and relative-link resolution | CI redesign or speculative pushes |
| Draft PR metadata and exact-tip check state | Merge, labels, reviewers, reruns, branch deletion |

The approximately 80-line playbook target is aspirational. Record the actual
line count, but do not fail solely for a small overrun or underrun when the
content contract is satisfied.

---

## Verifier rules

1. Pin the PR head SHA before reading the change.
2. Use a detached temporary worktree; do not switch the shared checkout.
3. Run only read-only inspection and the existing GitHub check observation.
4. If the PR tip moves, mark the run **DEFERRED** and restart at V0.
5. If a check fails, report it; do not repair it in the verifier lane.
6. Cursor's mechanical verdict is not independent sign-off or Ryan's GATE.

---

## V0 — Session health and exact-tip worktree

Run from the canonical repository checkout. Keep the setup block in one shell
so `ci_wait_tip` is captured once.

```bash
cd /home/lauer/Projects/convmem
convmem doctor
convmem brief --stdout-only
convmem unresolved
git fetch origin

test ! -e /tmp/convmem-ci-wait-verify-pr81
ci_wait_tip=$(gh pr view 81 --repo alanmz-crypto/convmem --json headRefOid --jq .headRefOid)
test "$(git rev-parse origin/plan/2026-07-22-ci-wait-workflow)" = "$ci_wait_tip"
git worktree add --detach /tmp/convmem-ci-wait-verify-pr81 "$ci_wait_tip"
git -C /tmp/convmem-ci-wait-verify-pr81 status --short --branch
git -C /tmp/convmem-ci-wait-verify-pr81 rev-parse HEAD
```

If `/tmp/convmem-ci-wait-verify-pr81` already exists, stop and inspect ownership;
do not delete or reuse an unknown worktree.

| ID | Check | PASS evidence |
|----|-------|---------------|
| V0a | `convmem doctor` exits `0` | Final doctor summary |
| V0b | Session orientation completed | Brief timestamp and unresolved count |
| V0c | Remote branch tip equals PR head SHA | Equality command exits `0` |
| V0d | Detached verification worktree is clean | Status shows detached HEAD and no file entries |

---

## V1 — Pull request identity

```bash
gh pr view 81 --repo alanmz-crypto/convmem \
  --json number,url,isDraft,title,baseRefName,headRefName,headRefOid
git -C /tmp/convmem-ci-wait-verify-pr81 rev-parse HEAD
```

| ID | Check | Expected |
|----|-------|----------|
| V1a | PR identity | Number `81`; draft `true` |
| V1b | PR title | `Add guidance for productive work while CI runs` |
| V1c | Base and head | `main` ← `plan/2026-07-22-ci-wait-workflow` |
| V1d | Local detached HEAD | Exact `headRefOid` returned by GitHub |

---

## V2 — Exact six-file scope

```bash
cd /tmp/convmem-ci-wait-verify-pr81
ci_wait_base=$(git merge-base origin/main HEAD)
git diff --name-only "$ci_wait_base...HEAD"
git diff --check "$ci_wait_base...HEAD"
git status --short
```

The changed-path output must contain exactly these six paths:

```text
docs/CI-WAIT-WORKFLOW.md
docs/MODEL-WORKFLOW.md
docs/README.md
docs/planning/EXECUTE-TASK.md
docs/plans/ARCHITECTURE-ci-wait-workflow.md
docs/plans/VERIFY-ci-wait-workflow.md
```

| ID | Check | PASS evidence |
|----|-------|---------------|
| V2a | Changed paths equal the allowlist | Six paths above; no extras or omissions |
| V2b | Diff has no whitespace errors | `git diff --check` exits `0` with no output |
| V2c | Verification checkout remains clean | `git status --short` has no output |

The exact allowlist proves that protocol, charter, Actions, hooks, doctor, and
standing-register surfaces were not modified.

---

## V3 — Playbook structure and required text

```bash
cd /tmp/convmem-ci-wait-verify-pr81
wc -l docs/CI-WAIT-WORKFLOW.md
rg -n '^## ' docs/CI-WAIT-WORKFLOW.md
test "$(rg -c '^## ' docs/CI-WAIT-WORKFLOW.md)" -eq 5
test "$(rg -c '^\*\*Example —' docs/CI-WAIT-WORKFLOW.md)" -eq 2
test "$(rg -c '^\*\*Rule 1 ' docs/CI-WAIT-WORKFLOW.md)" -eq 1
test "$(rg -c '^\*\*Rule 2 ' docs/CI-WAIT-WORKFLOW.md)" -eq 1
rg -n 'Mechanical CI|supersedes|flaky or unrelated CI|not enforced policy' \
  docs/CI-WAIT-WORKFLOW.md
```

The five headings must appear once and in this order:

```text
## 1. Purpose
## 2. Same PR safe defaults
## 3. Parallel work on another branch
## 4. If waits stay long (advice only)
## 5. Cadence
```

| ID | Check | Expected |
|----|-------|----------|
| V3a | Opening | CI/automated-review waiting is described as a distinct work phase |
| V3b | Optional boundary | Text says guidance is optional and not enforced policy |
| V3c | Rule 1 | Task B requires prior assignment/authorization; review C requires lane permission |
| V3d | Rule 2 | No speculative push; only a confirmed current-tip Mechanical CI fix |
| V3e | Mechanical CI | Limited to reproducible formatter, linter, or unit-test failures with one non-material correction |
| V3f | Push semantics | Text says a new push supersedes running checks |
| V3g | Flaky/unrelated CI | Re-run only if allowed or escalate; do not expand scope |
| V3h | Examples | One current-tip mechanical fix and one pre-authorized task B example |
| V3i | Long-wait advice | Fast linters, cache, and job splitting are advice for separately scoped work |
| V3j | Length | Record line count; approximately 80 is guidance, not a hard gate |

---

## V4 — Router pointers and link resolution

```bash
cd /tmp/convmem-ci-wait-verify-pr81
rg -c 'CI-WAIT-WORKFLOW\.md' \
  docs/MODEL-WORKFLOW.md \
  docs/planning/EXECUTE-TASK.md \
  docs/README.md

rg -F -x '| [`docs/CI-WAIT-WORKFLOW.md`](CI-WAIT-WORKFLOW.md) | What to do while CI / automated review runs |' \
  docs/MODEL-WORKFLOW.md
rg -F -x -- '- [`CI-WAIT-WORKFLOW.md`](../CI-WAIT-WORKFLOW.md) — when CI is pending: what to do while automated review runs' \
  docs/planning/EXECUTE-TASK.md
rg -F -x '| [`CI-WAIT-WORKFLOW.md`](CI-WAIT-WORKFLOW.md) | What to do while CI / automated review runs |' \
  docs/README.md

test -f docs/CI-WAIT-WORKFLOW.md
test "$(realpath docs/planning/../CI-WAIT-WORKFLOW.md)" = \
  "$(realpath docs/CI-WAIT-WORKFLOW.md)"
```

| ID | Check | PASS evidence |
|----|-------|---------------|
| V4a | One pointer per router | Each `rg -c` result is `1` |
| V4b | Pointer text | All three exact-line searches succeed |
| V4c | Placement | MODEL-WORKFLOW after TEAM-CHARTER; README after AGENT-ROLES; EXECUTE-TASK under Awareness |
| V4d | Relative target | Both resolved paths identify `docs/CI-WAIT-WORKFLOW.md` |

---

## V5 — Architecture and governance boundary

```bash
cd /tmp/convmem-ci-wait-verify-pr81
rg -n 'A — Same PR|B — Another branch|C — Review/read-only' \
  docs/plans/ARCHITECTURE-ci-wait-workflow.md
rg -n 'Rule 1|Rule 2|required in the document text|not enforced' \
  docs/plans/ARCHITECTURE-ci-wait-workflow.md
rg -n 'Charter compatibility|do not change the|Low adoption is accepted' \
  docs/plans/ARCHITECTURE-ci-wait-workflow.md
rg -n 'Protocol|charter|Actions|hooks|doctor|standing register' \
  docs/plans/ARCHITECTURE-ci-wait-workflow.md
```

Read the architecture record and compare it with the live PR Steward section
of `docs/inter-model/TEAM-CHARTER-2026-07-06.md`.

| ID | Check | Expected |
|----|-------|----------|
| V5a | Options A/B/C | Same-PR default; authorized branch B; lane-permitted review C |
| V5b | Required-in-text boundary | Rules are mandatory wording, not enforcement |
| V5c | Charter compatibility | No self-assignment; mechanical fixes stay narrow; unexpected CI returns to Ryan |
| V5d | Non-goals | No protocol, charter, workflow, hook, doctor, or register change |
| V5e | Residual risk | Low discovery/adoption is explicitly accepted |

Any semantic conflict with the live charter is **FAIL**. Cursor reports the
conflict and performs no correction.

---

## V6 — PR body and exact-tip CI

```bash
gh pr view 81 --repo alanmz-crypto/convmem --json body --jq .body | \
  rg -F '**Docs-only; no runtime or CI changes.**'
gh pr checks 81 --repo alanmz-crypto/convmem --watch --interval 10
```

| ID | Check | Result rule |
|----|-------|-------------|
| V6a | PR body states docs-only boundary | Exact phrase found |
| V6b | Required checks complete successfully | PASS only when every required check on the pinned tip passes |
| V6c | Pending check | DEFERRED; wait or report live state, but do not rerun |
| V6d | Failed or unexpected check | FAIL; report to Ryan without changing scope |

The docs-only brief does not require local pytest or protocol/runtime smoke.
Record those as **SKIP — out of scope**, not as unrun PASS claims.

---

## V7 — Tip stability and checkout integrity

```bash
ci_wait_final_tip=$(gh pr view 81 --repo alanmz-crypto/convmem --json headRefOid --jq .headRefOid)
test "$(git -C /tmp/convmem-ci-wait-verify-pr81 rev-parse HEAD)" = \
  "$ci_wait_final_tip"
git -C /tmp/convmem-ci-wait-verify-pr81 status --short
```

| ID | Check | Result rule |
|----|-------|-------------|
| V7a | PR tip unchanged during verification | PASS when detached HEAD equals final `headRefOid` |
| V7b | Tip changed | DEFERRED; discard the aggregate verdict and restart at V0 |
| V7c | Verifier made no edits | Clean status with no output |

---

## V8 — Mechanical verdict and handoff

Cursor may report **Mechanical PASS** only when V0–V7 pass, including successful
exact-tip CI. Use **DEFERRED** for a moving tip or checks still pending. Any
scope, content, link, governance, metadata, or CI mismatch is **FAIL**.

Paste this report to Ryan without editing the PR:

```text
VERIFY-ci-wait-workflow — PR #81 — tip <full SHA> — Cursor — <ISO-8601>
V0: PASS|FAIL — doctor/orientation + pinned clean worktree evidence
V1: PASS|FAIL — PR identity evidence
V2: PASS|FAIL — exact six paths + diff check evidence
V3: PASS|FAIL — five sections + rules + examples + line count
V4: PASS|FAIL — pointer counts, exact text, placement, resolved link
V5: PASS|FAIL — architecture/charter/non-goal/residual-risk review
V6: PASS|FAIL|DEFERRED — PR body + exact-tip CI state
V7: PASS|FAIL|DEFERRED — final tip equality + clean verifier status
Runtime tests: SKIP — docs-only brief; no runtime gate
Mechanical: PASS|FAIL|DEFERRED
Independent sign-off: PENDING — Kiro or Ryan-named lane
Ryan GATE: PENDING
Unexpected findings: none | <precise finding>
```

After capturing the report, remove only the clean temporary worktree created in
V0:

```bash
git -C /tmp/convmem-ci-wait-verify-pr81 status --short
cd /home/lauer/Projects/convmem
git worktree remove /tmp/convmem-ci-wait-verify-pr81
```

If status is not clean, stop and report it; do not force removal. Cursor then
stops for independent sign-off and Ryan's GATE. Do not run `convmem record`.
