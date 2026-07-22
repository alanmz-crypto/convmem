# Architecture: CI Wait Workflow

| Field | Value |
|-------|-------|
| Status | Approved for docs-only execution |
| Owner | Ryan owns scope and merge; PR Steward delivers the bounded brief |
| Scope | Optional, project-generic guidance for work while CI or automated review runs |
| Decision | One terse playbook with three discovery pointers and no enforcement |

## Problem

CI and automated review create a real development phase. Without guidance,
people and models may either watch checks idly or treat the wait as permission
to invent follow-on work. Both outcomes waste time or expand authority.

The repository needs a portable answer that does not turn this workflow into
agent governance, change existing lanes, or trigger speculative CI work.

## Decision

Add `docs/CI-WAIT-WORKFLOW.md` as optional workflow guidance. It describes
safe same-PR work, tightly bounded parallel work, advice for persistently slow
checks, and a simple cadence for returning to the original PR.

The playbook uses three options:

| Option | Use while the original PR waits |
|--------|---------------------------------|
| **A — Same PR** | Self-review, local verification, and confirmed current-tip Mechanical CI fixes |
| **B — Another branch** | A separate task only when it was already assigned or authorized |
| **C — Review/read-only** | Review only when the actor's lane permits it; otherwise hand off or stop |

Option A is the default. Options B and C do not create authority.

## Required textual rules

**Rule 1 — Parallel work requires prior authority.** Option B is available only
for work already assigned or authorized. Option C is available only when the
actor's lane permits that review. Without either condition, hand off, do
read-only context work, or stop.

**Rule 2 — Do not push speculatively during healthy CI.** Push only a confirmed,
current-tip Mechanical CI fix. The new push supersedes the running checks, so
unnecessary pushes discard useful in-flight evidence.

These rules are required in the document text. They are guidance, not enforced
policy: this arc adds no hook, workflow, doctor check, protocol rule, or new
authorization mechanism.

## Discovery boundary

Keep discovery thin by adding one pointer in each existing router:

- `docs/MODEL-WORKFLOW.md`
- `docs/planning/EXECUTE-TASK.md`
- `docs/README.md`

The routers point to the playbook; they do not restate it. This preserves one
source for the workflow and avoids widening Tier A protocol.

## Charter compatibility

The live PR Steward charter requires an explicit bounded assignment, prohibits
self-assigned follow-on work, permits brief-contained mechanical fixes, requires
explicit branch pushes, and routes unexpected CI failures to Ryan. Rules 1 and
2 restate those boundaries in project-generic language and do not change the
charter.

## Non-goals

- Editing `config/agent-protocol.md` or generated protocol surfaces
- Editing the HITL team charter
- Changing GitHub Actions, hooks, doctor, or the standing register
- Authorizing a new task, review lane, CI rerun, merge, or deployment
- Tuning CI as part of this documentation change

## Residual risk

The three pointers are intentionally lightweight. Some contributors may not
discover or adopt the optional playbook. Low adoption is accepted rather than
adding enforcement or duplicating the guidance across governance surfaces.

## Acceptance

- The playbook has the contracted five sections and two examples.
- Rules 1 and 2, Mechanical CI, and flaky/unrelated handling are explicit.
- Each router contains one resolving pointer.
- Only the six authorized documentation files change.
- The pull request states that it is docs-only with no runtime or CI changes.
