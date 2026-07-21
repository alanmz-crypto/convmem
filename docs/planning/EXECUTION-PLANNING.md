# Execution Planning

Answers: **How do I turn an approved direction into bounded executable tasks?**

Approved direction -> bounded execution plan -> HITL -> [`EXECUTE-TASK.md`](EXECUTE-TASK.md).

---

## Phase Initialization

| Field | Value |
|-------|-------|
| **Phase** | Execution Planning |
| **Characters** | Task Decomposer, Dependency Mapper, Scope Guardian |
| **Functions** | Planner |
| **Lanes** | Cursor (Tier A); Codex read-only if Ryan requests plan audit |
| **Engineering References** | [`builder-reference.md`](../builder-reference.md) when infra scope is unclear |
| **Probe Version** | v1 |
| **Exit Condition** | Bounded execution plan artifact complete; HITL approval pending |
| **Authority** | Awaiting HITL |

Only after initialization may planning begin.

---

## Objective

Shape an approved direction into one to five bounded tasks with scope,
dependencies, gates, stop points, and evidence requirements.

Enter after Architecture direction plus HITL, a [`REVISE-PLANNING.md`](REVISE-PLANNING.md)
output, an approved bug scope, or a Ryan-named scope.

This phase is task-shaping only. It is not implementation
([`EXECUTE-TASK.md`](EXECUTE-TASK.md)), not plan revision
([`REVISE-PLANNING.md`](REVISE-PLANNING.md)), not Verify OS
([`VERIFY-PLANNING.md`](VERIFY-PLANNING.md)), and not greenfield bug discovery.
For an **arc**, the execution plan artifact must name the companion
`docs/plans/VERIFY-<slug>.md` (stub from
[`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md) is OK until
post-execute fill).

---

## Responsibilities

### Planning Status (emit at start)

```
Planning Status

Phase:        Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Cursor
Authority:    Awaiting HITL
```

Character definitions live in [`reasoning-modes.md`](../reasoning-modes.md#execution-planning).

### When to enter

- After Architecture direction and HITL approval.
- After [`REVISE-PLANNING.md`](REVISE-PLANNING.md) identifies execution work.
- After Ryan approves a bug scope or names a concrete task-shaping scope.
- Not for implementation: route to [`EXECUTE-TASK.md`](EXECUTE-TASK.md) after this plan and HITL.
- Not for stale-plan cleanup: route to [`REVISE-PLANNING.md`](REVISE-PLANNING.md).
- Not for greenfield design: route to [`ARCHITECTURE-PLANNING.md`](ARCHITECTURE-PLANNING.md) / [`builder-reference.md`](../builder-reference.md).
- Not for bug discovery: route upstream to [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) and Crush lane.

### Required inputs

| Input | Why |
|-------|-----|
| Approved direction, bug scope, revise finding, or Ryan-named scope | Authority and source |
| `git status` / branch name / `main` baseline | Branch reality |
| Active phase guide = this file | Precedence |
| [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md) | Repo and surface routing |

Optional when relevant: `convmem doctor`, `convmem brief`, and `convmem "query"`
for history, architecture, or prior-decision grounding.

### Planning Loop (ordered)

| Step | Name | Actions |
|------|------|---------|
| **0** | **Intake** | Restate the direction; name the source; confirm HITL approval of the direction |
| **1** | **Scope boundary** | List in-scope, out-of-scope, and deferred items; reject drive-by expansion (**Scope Guardian**) |
| **2** | **Decompose** | Produce one to five tasks; one deliverable each; no option forks (**Task Decomposer**) |
| **3** | **Dependencies** | Order tasks; identify blockers; mark parallel-safe vs serial work (**Dependency Mapper**) |
| **4** | **Gates and evidence** | Name per-task verification and evidence; link [`EXECUTE-TASK.md`](EXECUTE-TASK.md#verification-routes-interim--not-verify-os) where applicable |
| **5** | **Arc VERIFY companion** | If this plan is an **arc**, name `docs/plans/VERIFY-<slug>.md` (create stub from template if needed) |
| **6** | **Stop points** | State where HITL approval is required before Execute |
| **7** | **Plan artifact** | Emit the template below; do not implement |

### Execution Plan Artifact Template

```markdown
## Execution Plan - <title>

**Source:** <Ryan request | Revise stamp | bug approval | architecture waiver>
**Authority:** HITL-approved direction @ <date/ref>
**Goal:** <one sentence>

### Tasks

| ID | Deliverable | In scope | Depends on | Gates | Execution lane |
|----|-------------|----------|------------|-------|----------------|
| T1 | ... | ... | - | pytest -q; doctor | Cursor |

### Out of scope

- ...

### Evidence requirements (for Execute phase)

- ...

### Arc VERIFY companion (required for arcs)

- Path: `docs/plans/VERIFY-<slug>.md`
- Status: stub | filled
- Template: `docs/plans/VERIFY-TEMPLATE.md`

### Execute entry

- First task: T1 after HITL approves this plan.
```

Execution lane defaults to Cursor unless Ryan explicitly says otherwise. Codex
audit is post-handoff only. Crush and DeepSeek are not execution lanes.

### Awareness (read-only context)

- [`PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md) - phase order and HITL gates
- [`reasoning-modes.md`](../reasoning-modes.md) - character definitions
- [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) - lane ownership and must-nots
- [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md) - repo-specific routes
- [`EXECUTE-TASK.md`](EXECUTE-TASK.md) - downstream implementation phase
- [`VERIFY-PLANNING.md`](VERIFY-PLANNING.md) - post-execute arc Verify OS
- [`REVISE-PLANNING.md`](REVISE-PLANNING.md) - stale-plan cleanup phase

### Outputs

- Execution plan artifact only.
- No code changes.
- No merge.
- No `convmem record`.
- No new `logs/*.md`.

---

## Exit Criteria

This phase ends when:

- [ ] Four invariant questions answered (from [`PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md#four-question-invariant)):
  1. Where am I? -> Phase
  2. How should I think? -> Character
  3. What function am I performing? -> Function
  4. What standards apply? -> builder-reference
- [ ] Direction restated and source named
- [ ] Scope boundary explicit: in-scope, out-of-scope, deferred
- [ ] One to five bounded tasks; no option forks
- [ ] Dependencies, blockers, and parallel-safe work named
- [ ] Gates and evidence requirements named per task
- [ ] If arc: companion VERIFY path named (stub OK)
- [ ] Execution plan artifact emitted
- [ ] No self-transition to Execute or Architecture
- [ ] No `convmem record` unless Ryan asks

Cursor must stop here. Await HITL.
