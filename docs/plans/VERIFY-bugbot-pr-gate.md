# Verify Plan — BugBot PR Gate

```text
Planning Status

Phase:        Verify (bugbot-pr-gate)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Crush (mechanical, Ryan-authorized for this tip); Kiro or Ryan-named lane (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Status:** Mechanical V0–V5 PASS; tip-rebind after merge-`main` to `511418b`; V6 Kiro PASS on prior tip `6be6c92` carries (seven-file content identical); V4d PENDING Ryan GATE; ready for Ryan GATE/merge.
**Subject / tip:** `511418b8f208433692350c542f7043767368d883`
**PR:** BugBot gate rollout PR
[`#91`](https://github.com/alanmz-crypto/convmem/pull/91)
**EXECUTION:** `docs/plans/EXECUTION-2026-07-22-bugbot-pr-gate.md`
**ARCHITECTURE:** `docs/plans/ARCHITECTURE-bugbot-pr-gate.md`
**Goal:** Prove the seven-file policy rollout preserves Planning OS invariants,
binds applicable BugBot evidence to the accepted tip, and keeps review context
separate from workflow triggers.

For each check, record **PASS / FAIL / SKIP** plus one line of evidence.
BugBot-specific rows may use **N/A (exempt)** only with the recorded exemption
reason. An applicable SHA mismatch is always **FAIL**.

## Run contract and STOP conditions

The mechanical runner works from a clean checkout of PR `#91`'s exact head and
pins that commit as the **subject tip SHA** for the whole run.

1. Fetch `origin`, read `headRefOid` from PR `#91`, and confirm local `HEAD`
   equals it before collecting evidence.
2. Run V0–V5 without editing files, committing, pushing, commenting, or merging.
3. Record one PASS / FAIL / SKIP / N/A result and one evidence line per row.
4. If the PR head changes, all earlier evidence is stale: stop, discard the
   aggregate verdict, pin the new subject tip, and rerun V0–V5.
5. Hand the completed mechanical table to an independent reviewer for V6. Ryan
   owns the final GATE.

Stop and return **Mechanical FAIL** when a required check fails, the seven-path
scope changes, the worktree is dirty, or an applicability/evidence claim cannot
be proved. A queued required GitHub check is **PENDING**, not PASS. Use SKIP only
for a genuinely unavailable non-required check with contemporaneous evidence;
do not repair findings in the verifier lane.

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Exactly seven authorized paths; architecture and execution policy; Verify OS confirmation; BUGBOT review context | Runtime code; CI/hooks; protocol kernel; charter; local report/waiver storage; GitHub configuration; BugBot trigger comment |

Authorized paths:

1. `docs/plans/EXECUTION-2026-07-22-bugbot-pr-gate.md`
2. `docs/plans/ARCHITECTURE-bugbot-pr-gate.md`
3. `docs/planning/EXECUTE-TASK.md`
4. `docs/planning/VERIFY-PLANNING.md`
5. `docs/plans/VERIFY-TEMPLATE.md`
6. `docs/plans/VERIFY-bugbot-pr-gate.md`
7. `.cursor/BUGBOT.md`

## V0 — Preconditions and External Review evidence

```bash
git fetch origin
subject_tip_sha=$(gh pr view 91 --json headRefOid --jq '.headRefOid')
test "$(git rev-parse HEAD)" = "$subject_tip_sha"
test -z "$(git status --porcelain)"
git diff --name-only origin/main...HEAD
pytest -q tests/test_planning_guide_contract.py
convmem doctor
```

Execute evidence expected for this rollout:

| Field | Value |
|-------|-------|
| `gate_applicability` | `exempt` |
| `reason` | Policy/review-context-only rollout; no executable product behavior |
| `subject_tip_sha` | `511418b8f208433692350c542f7043767368d883` |
| `bugbot_reviewed_sha` | `n/a` |
| `result` | `n/a` |
| `finding_disposition` | `none` |
| `authority_reference` | `n/a` |

| ID | Check | Result |
|----|-------|--------|
| V0a | Subject tip SHA resolves to the commit being verified | PASS — `511418b8f208433692350c542f7043767368d883` (post-merge tip-rebind) |
| V0b | Execute applicability and reason are present | PASS — EXECUTION:94-95 records `exempt` + reason |
| V0c | Exemption is consistent with the final seven-file policy/context diff | PASS — all 7 files are docs/policy/planning; no runtime code |
| V0d | Exactly the seven authorized paths differ from `origin/main` | PASS — 7 paths match authorized list (`origin/main...511418b`) |
| V0e | Worktree is clean and PR head equals the pinned subject tip SHA | PASS — HEAD=`511418b`, PR headRefOid=`511418b`, 0 dirty files |
| V0f | Planning contract test and `convmem doctor` pass | PASS — 8/8 tests, doctor all checks passed |

## V1 — Binding architecture

```bash
rg -n 'Subject tip SHA|BugBot-reviewed SHA|When unsure|independent and non-substituting|Finding lifecycle|Evidence schema|Outage or unreachable' \
  docs/plans/ARCHITECTURE-bugbot-pr-gate.md
```

| ID | Check | Result |
|----|-------|--------|
| V1a | Architecture assigns applicability to Execute, confirmation to Verify, review context to BUGBOT, and durable evidence to GitHub | PASS — ARCH:6,20,28 (roles), ARCH:64-65 (PR-native evidence) |
| V1b | Universal SHA terms, any-tip-change rule, rename litmus, and unsure→required are explicit | PASS — ARCH:34-35 (SHA terms), 46 (rename), 70 (unsure→required) |
| V1c | Copilot independence, finding lifecycle, evidence schema, and outage→Ryan tip-acceptance are explicit | PASS — ARCH:46 (independence), 104 (outage), 110 (lifecycle), 121 (schema) |
| V1d | Local report/waiver storage, CI/hooks, protocol, charter, and branch protection remain non-goals | PASS — ARCH:8,15 (no local report), 64 (charter exempt), 156 (CI/hooks/protocol non-goals) |

## V2 — Execute Task invariants

```bash
rg -n '^\| \*\*[0-7]\*\*' docs/planning/EXECUTE-TASK.md
rg -n '^\| \*\*D[0-6]\*\*' docs/planning/EXECUTE-TASK.md
rg -n 'steps 4–6|steps 5–7' docs/planning/EXECUTE-TASK.md
```

| ID | Check | Result |
|----|-------|--------|
| V2a | Main loop is exactly 0–7 and External Review is step 3 | PASS — EXECUTE-TASK.md:89-96; step 3 = External Review |
| V2b | D0–D6 labels remain unchanged and D6 points to main-loop steps 5–7 | PASS — EXECUTE-TASK.md:195-201; D6 = steps 5–7 |
| V2c | Applicability, SHA equality, any-tip-change, lifecycle, outage, Copilot independence, and evidence schema are present | PASS — EXECUTE-TASK.md:103,116,122,137,144-145,156,167,171,179 |
| V2d | Awareness points to BUGBOT as review context, not policy ownership | PASS — EXECUTE-TASK.md:224 "BugBot review context only" |
| V2e | Exit criteria require a valid External Review disposition | PASS — EXECUTE-TASK.md:249 requires applicability + SHA match + finding disposition or exemption |

## V3 — Verify OS confirmation

```bash
rg -n 'BugBot confirmation prerequisite|FAIL.*, not SKIP|N/A \(exempt\)' \
  docs/planning/VERIFY-PLANNING.md docs/plans/VERIFY-TEMPLATE.md
rg -n 'gate_applicability|subject_tip_sha|bugbot_reviewed_sha|result|finding_disposition|authority_reference' \
  docs/plans/VERIFY-TEMPLATE.md
```

| ID | Check | Result |
|----|-------|--------|
| V3a | Verify copies Execute applicability and does not reclassify it | PASS — VERIFY-PLANNING.md:98 "BugBot confirmation prerequisite" redirects to Execute |
| V3b | Applicable subject-tip / BugBot-reviewed SHA mismatch is FAIL, never SKIP | PASS — VERIFY-PLANNING.md:109 "FAIL, not SKIP" |
| V3c | Required finding dispositions and outage acceptance are checked | PASS — VERIFY-TEMPLATE.md:52-53 covers dispositions + outage fields |
| V3d | Template mirrors all seven evidence fields and permits N/A only for a valid exemption | PASS — VERIFY-TEMPLATE.md:19,48-54 (7 fields + N/A exemption clause) |

## V4 — `.cursor/BUGBOT.md` boundary

```bash
git ls-files --error-unmatch .cursor/BUGBOT.md
if rg -ni '/review-bugbot|bugbot run|cursor review|gate_applicability|when to run' \
  .cursor/BUGBOT.md; then
  exit 1
fi
```

| ID | Check | Result |
|----|-------|--------|
| V4a | `.cursor/BUGBOT.md` is git-tracked | PASS — `git ls-files --error-unmatch .cursor/BUGBOT.md` succeeds |
| V4b | It contains tests, invariants, false-positive boundaries, and sensitive areas | PASS — 6 keyword matches (test/invariant/false positive/sensitive) |
| V4c | It contains no applicability, invocation, waiver, or merge-readiness policy | PASS — no matches for banned trigger/policy terms (rg exit 1) |
| V4d | Ryan reviews the bootstrap file's exact content before merge | PENDING — Ryan GATE; Cursor content read on `6be6c92` recommended PASS (banned-term clean; four sections present) |

## V5 — Exact-tip PR evidence and CI

```bash
gh pr view 91 \
  --json state,headRefOid,baseRefName,mergeable,body,statusCheckRollup
gh api repos/alanmz-crypto/convmem/issues/91/comments \
  --jq '.[].body'
```

| ID | Check | Result |
|----|-------|--------|
| V5a | PR `#91` is open against `main`, and `headRefOid` equals the pinned subject tip SHA | PASS — OPEN against main; headRefOid = `511418b` |
| V5b | PR is not conflicting and every required check for the subject tip is completed successfully; queued/in-progress is PENDING and failure is FAIL | PASS — MERGEABLE; pylint (3.12) SUCCESS on tip `511418b` |
| V5c | PR body records the seven-field exempt BugBot evidence row with the pinned subject tip SHA | PASS — body `subject_tip_sha` synced to tip in this tip-rebind (was lagging at `2f5d60c`) |
| V5d | No unauthorized BugBot trigger comment is present; any automatic bootstrap review is treated as informational | PASS — 0 PR comments |

## V6 — Independent sign-off

| ID | Check | Result |
|----|-------|--------|
| V6a | Independent reviewer confirms the mechanical evidence without editing implementation artifacts | PASS — Kiro independent sign-off on tip `6be6c9204b1c030d6e9368ed139926d0c230339a` (2026-07-22); no implementation edits |
| V6b | Written PASS/FAIL names the pinned subject tip SHA, PR `#91`, and residual risks | PASS — Kiro PASS naming tip `6be6c92`, PR `#91`, residuals V4d + former V5c body lag; post-merge tip `511418b` carries via seven-file identity proof |
| V6c | Ryan records the final GATE decision; verifier does not infer merge or arc-close authority | PENDING — Ryan GATE (V4d content accept + merge) |

The verifier performs no cleanup or correction. Findings return to the
implementation lane; Ryan owns the final GATE.

## Evidence log

```text
VERIFY-bugbot-pr-gate — fill tip 2f5d60c → rebind 637586a/6be6c92 → post-merge tip 511418b
Runners: Crush mechanical (Ryan-authorized); Kiro V6 on 6be6c92; Cursor tip-rebind 2026-07-22T19:41:28Z
Tip move cause: merge commit 511418b (merge main into docs/2026-07-22-bugbot-pr-gate)
Runtime proof: git diff --exit-code 6be6c92..511418b — all seven authorized paths identical (narrow tip-rebind allowed; not VERIFY-only, but content-identity vs Kiro tip)
Rechecked: V0a, V0d, V0e, V0f, V5a, V5b, V5c, V5d
V0: PASS
V1: PASS (unchanged content)
V2: PASS (unchanged content)
V3: PASS (unchanged content)
V4: PASS (V4d PENDING Ryan GATE; Cursor recommended PASS)
V5: PASS (pylint SUCCESS on 511418b; PR body tip sync in this rebind)
V6: PASS (Kiro on 6be6c92; carries via seven-file identity)
Mechanical: PASS (V4d PENDING Ryan)
Sign-off: PASS (Kiro)
Ryan GATE: PENDING
```

## Completion rule

Mechanical PASS requires V0–V5 to pass, except the explicitly evidenced
`N/A (exempt)` BugBot rows. Arc close additionally requires V6 independent
sign-off and Ryan's GATE. Any new PR tip invalidates all three statuses.
