# Architecture: BugBot as a PR-Level External Review Gate

| Field | Value |
|-------|-------|
| **Status** | Approved for docs-only execution on 2026-07-22 |
| **Owner** | Ryan owns scope and merge; Execute owns applicability; Verify confirms evidence |
| **Scope** | PR-native BugBot gate for correctness-affecting changes |
| **Decision** | Use GitHub PR evidence; create no local report or waiver subsystem |

## Problem

convmem needs durable external review for runtime and correctness-affecting pull
requests. BugBot's authoritative evidence already exists on GitHub as review
comments and a `Cursor Bugbot` check associated with a commit SHA. Copying that
evidence into local report or waiver files would create a second, weaker source
of truth with new retention and verification mechanics.

## Decision

Use BugBot as a **PR-level gate only**. Execute decides whether it applies and
owns invocation/disposition policy. Verify OS confirms PR-native evidence.
`.cursor/BUGBOT.md` supplies technical review context. GitHub remains the
durable evidence source.

| Surface | Owns | Does not own |
|---------|------|--------------|
| `docs/planning/EXECUTE-TASK.md` | Applicability, timing, dispositions, evidence rows | Review heuristics |
| `docs/planning/VERIFY-PLANNING.md` and `docs/plans/VERIFY-TEMPLATE.md` | Arc-close confirmation of SHAs and dispositions | Deciding whether the gate applied |
| `.cursor/BUGBOT.md` | Tests, invariants, false-positive boundaries, sensitive areas | Workflow triggers or when to run |
| GitHub PR | BugBot check, review comments, reviewed SHA | Local policy ownership |

## Universal SHA terms

- **Subject tip SHA:** the commit being accepted or handed off.
- **BugBot-reviewed SHA:** the commit BugBot evaluated.

Shipped policy must not use ambiguous “current head SHA” wording unless the
sentence immediately binds it to one of these terms.

## Role boundaries

BugBot is the routine External Review gate in Execute. It is not the GitHub
Copilot audit lane, Kiro design sign-off, Sol-High adjudication, or merge
authority.

When BugBot and Copilot both apply, they are independent and non-substituting.
They may run in parallel once a tip exists, but each assigned gate needs its own
evidence and disposition before merge readiness.

## Applicability

BugBot is **required** when a pull request includes runtime or
correctness-affecting changes involving:

- executable code;
- control flow or error handling;
- persistence, schema, or API behavior;
- concurrency or state;
- security, authentication, or input validation; or
- bug fixes, features, and nontrivial refactors.

BugBot is **exempt**, with a reason recorded in evidence, for:

- docs, plans, charter, or register-only diffs;
- comments or formatting-only diffs; and
- rename-only changes whose diff changes only paths or identifier tokens plus
  rename metadata, with no behavior-bearing literals, expressions, control
  flow, defaults, schema, or API payloads.

When unsure, the gate is required.

## Gate satisfaction

An applicable gate is satisfied only when visible GitHub PR BugBot evidence
exists whose associated **BugBot-reviewed SHA equals the subject tip SHA**.
“Ensure BugBot has completed” is not sufficient wording.

`/review-bugbot` before push may front-load review for an identical diff, but it
does not satisfy the gate unless PR-native evidence is associated with the
subject tip SHA. A copied local report never satisfies the gate.

## Tip change after review

Any subject-tip SHA change after a BugBot review requires a new BugBot result
whose reviewed SHA equals the new subject-tip SHA. There is no materiality
judgment.

A new tip that independently qualifies for the docs, rename, or formatting
exemption may instead record a fresh exemption and reason. When unsure, rerun
BugBot.

## External-mutation constraint

Posting `bugbot run`, `cursor review`, or equivalent text is a GitHub comment.
An agent may post it only under standing comment authority or an exact
`Authorized external changes` grant naming the PR, operation, and comment text.
Without that authority, record the blocked-trigger reason and stop.

Branch pushes and PR creation are separate external operations. Authorization
for them does not imply authorization for a BugBot-trigger comment, and denial
of trigger-comment authority does not prohibit an otherwise authorized branch
push or PR.

## Outage or unreachable BugBot

An agent must not create an outage exemption. Record what was attempted, the
subject tip SHA, and when; then stop and escalate to Ryan. The only escape hatch
is Ryan's written, tip-specific acceptance for that subject tip.

## Finding lifecycle

| Disposition | Meaning | Required evidence |
|-------------|---------|-------------------|
| **clean** | No open findings on the accepted tip | PR-native evidence for the subject tip shows no unresolved findings |
| **fixed** | A finding was addressed | BugBot evidence for the accepted subject tip no longer reports it, or rare Ryan tip-acceptance during outage |
| **Ryan accepted** | An unresolved finding may remain | Ryan's written acceptance names the finding and subject tip SHA |

A later commit alone does not dispose a finding. “Fixed” is bound to evidence
for the accepted tip.

## Evidence schema

| Field | Allowed value or purpose |
|-------|--------------------------|
| `gate_applicability` | `required` or `exempt` |
| `reason` | Why the gate is required or exempt |
| `subject_tip_sha` | Commit being accepted |
| `bugbot_reviewed_sha` | SHA BugBot evaluated; `n/a` when exempt or accepted during outage without a run |
| `result` | `clean`, `findings`, `unreachable`, or `n/a` |
| `finding_disposition` | Per finding: `fixed`, `ryan_accepted`, or `none` |
| `authority_reference` | Ryan acceptance, comment authority, or `n/a` |

## Verify OS

Verify treats BugBot evidence as a conditional prerequisite when Execute marked
the gate required. V0 records the subject tip SHA and BugBot-reviewed SHA and
returns **FAIL**, not SKIP, when they differ. Verify confirms each finding's
disposition or records N/A with an exemption or Ryan tip-acceptance reference.
It does not reconsider applicability.

## `.cursor/BUGBOT.md` governance

`.cursor/BUGBOT.md` is git-tracked review context. It may contain test and doctor
commands, architectural invariants, false-positive boundaries, and sensitive
areas. It must not contain applicability or when-to-run policy.

Changes that alter review boundaries, false-positive carve-outs, or
sensitive-area guidance require normal PR review. This bootstrap file is
gate-exempt because it does not change executable product behavior, but Ryan
must review its exact content before merge. A BugBot result on the bootstrap PR
cannot validate its own configuration.

## Non-goals

- No `.convmem/bugbot-reports` or waiver files.
- No protocol-kernel, doctor, CI, hook, or branch-protection changes.
- No new HITL role.
- No conflation of BugBot with Copilot, Kiro, or Sol-High.
- No automated tip watcher beyond Verify's explicit SHA comparison.

## Residual risks

- Comment authority can stall invocation; Ryan or an authorized Steward must
  resolve it.
- A stale review can look complete; exact SHA equality and Verify FAIL expose
  it.
- Pre-push review synchronizes only when the PR diff is identical.
- Cursor-specific outage blocks the gate unless Ryan accepts that exact tip.
- `.cursor/BUGBOT.md` influences future review quality, so human review remains
  important even though the bootstrap change is gate-exempt.

## Acceptance

- PR-native evidence is the only BugBot evidence of record.
- Copilot and BugBot remain independent and non-substituting.
- Applicability and the rename-only litmus are explicit; uncertainty means
  required.
- Any subject-tip change needs a matching result or fresh valid exemption.
- Finding dispositions are bound to accepted-tip evidence.
- Execute contains the complete minimum evidence schema.
- Verify fails applicable SHA mismatches.
- `.cursor/BUGBOT.md` is tracked, context-only, and normally reviewed.
- The rollout remains a seven-file docs/policy PR.
