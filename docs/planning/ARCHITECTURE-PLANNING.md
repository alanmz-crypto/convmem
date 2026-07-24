# Architecture Planning

Answers: **How do I choose and approve a system direction before task shaping?**

Problem/request -> Architecture Direction artifact -> HITL -> [`EXECUTION-PLANNING.md`](EXECUTION-PLANNING.md).

---

## Phase Initialization

| Field | Value |
|-------|-------|
| **Phase** | Architecture Planning |
| **Characters** | Architect, Systems Thinker, Risk Reviewer |
| **Functions** | Planner |
| **Lanes** | OpenAI Codex authors Architecture Direction; Kiro reviews design; Ryan approves (HITL) |
| **Engineering References** | [`builder-reference.md`](../builder-reference.md) when design touches infra patterns |
| **Probe Version** | v2 |
| **Exit Condition** | Architecture Direction artifact complete; HITL approval pending |
| **Authority** | Awaiting HITL |

Only after initialization may planning begin.

---

## Objective

Choose one system direction with explicit boundary, constraints, options compared,
risks named, and a single recommended path — then stop for HITL before task shaping.

Enter for Ryan requests, greenfield or cross-cutting design, revise output that
points upstream, or when the problem is too large to shape as tasks without a
direction decision first.

This phase is direction approval only. It is not task decomposition
([`EXECUTION-PLANNING.md`](EXECUTION-PLANNING.md)), not implementation
([`EXECUTE-TASK.md`](EXECUTE-TASK.md)), not plan revision
([`REVISE-PLANNING.md`](REVISE-PLANNING.md)), not Verify OS, not Contract v2,
not kernel edits, not greenfield bug discovery, and not a new agent or role
framework.

---

## Responsibilities

### Planning Status (emit at start)

```
Planning Status

Phase:        Architecture Planning
Characters:   Architect, Systems Thinker, Risk Reviewer
Functions:    Planner
Lanes:        Codex authors; Kiro reviews; Ryan approves (HITL)
Authority:    Awaiting HITL
```

Character definitions live in [`reasoning-modes.md`](../reasoning-modes.md#architecture-planning).

### When to enter

- Ryan names a problem, request, or cross-cutting change that needs a direction
  before tasks can be shaped.
- Greenfield or structural design where multiple viable approaches exist.
- [`REVISE-PLANNING.md`](REVISE-PLANNING.md) output points upstream — the plan
  needs a direction decision, not more task rows.
- Not for task shaping: route to [`EXECUTION-PLANNING.md`](EXECUTION-PLANNING.md)
  after this direction and HITL approval.
- Not for implementation: route to [`EXECUTE-TASK.md`](EXECUTE-TASK.md) only
  after Execution Planning and HITL.
- Not for stale-plan cleanup: route to [`REVISE-PLANNING.md`](REVISE-PLANNING.md).
- Not for bug discovery: route upstream to [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) and Crush lane.
- Not for verification of shipped work: use the existing verification route
  ([`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md), `pytest -q`,
  `convmem doctor`) — do not build or expand Verify OS here.
- Not for Planning OS kernel or contract changes without a separate approved arc.

### Required inputs

| Input | Why |
|-------|-----|
| Ryan request, problem statement, or revise upstream finding | Authority and source |
| `git status` / branch name / `main` baseline | Branch and repo reality |
| Active phase guide = this file | Precedence |
| [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md) | Repo and surface routing |

Optional when relevant: `convmem doctor`, `convmem brief`, and `convmem "query"`
for history, prior decisions, and builder-reference grounding.

### Architecture Loop (ordered)

| Step | Name | Actions |
|------|------|---------|
| **0** | **Intake** | Restate the problem or request in one sentence; name the source (Ryan, revise upstream, cross-cutting need); state why Architecture Planning is needed instead of jumping to Execution Planning or Execute |
| **1** | **System boundary** | Define what system, surface, or subsystem is in scope; list explicit out-of-scope items and deferred-with-owner items; reject drive-by expansion (**Architect**) |
| **2** | **Existing constraints** | List invariants, current repo reality (`file:line` when citing code), HITL rules, charter must-nots, and non-negotiable dependencies (**Systems Thinker**) |
| **3** | **Options** | Compare two to three directions maximum; one row per option; no open-ended option forks or "we could also…" lists without a decision |
| **4** | **Risk / reversibility** | For each option and the recommended path: failure modes, coupling introduced, migration cost, rollback path, and irreversible choices (**Risk Reviewer**) |
| **5** | **Chosen direction** | Recommend exactly one direction; name rejected alternatives and why; no unresolved forks |
| **6** | **Direction artifact** | Emit the template below; do not decompose tasks, implement, or advance to Execution Planning |

### Architecture Direction Artifact Template

```markdown
## Architecture Direction - <title>

**Source:** <Ryan request | revise upstream | cross-cutting need>
**Authority:** Awaiting HITL @ <date/ref>
**Problem:** <one sentence>

### System boundary

- In scope: ...
- Out of scope: ...

### Constraints and invariants

- ...

### Options considered

| Option | Summary | Rejected because |
|--------|---------|------------------|
| A | ... | ... |
| B | ... | ... |

### Chosen direction

<one paragraph — single path, no forks>

### Risks and reversibility

- ...

### Downstream handoff

- Next phase: EXECUTION-PLANNING.md after HITL approves this direction.
```

Codex authors the direction; Ryan-requested read-only audit does not replace
authorship. Crush and DeepSeek are not architecture lanes.

### Routing table

| Situation | Route |
|-----------|-------|
| Shape approved direction into tasks | [`EXECUTION-PLANNING.md`](EXECUTION-PLANNING.md) after HITL |
| Implement approved task | [`EXECUTE-TASK.md`](EXECUTE-TASK.md) after Execution Planning + HITL |
| Update stale plan | [`REVISE-PLANNING.md`](REVISE-PLANNING.md) |
| Bug discovery | [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) / Crush — approved scope only |
| Verify shipped work | [`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md), gates — not Verify OS |

### Awareness (read-only context)

- [`PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md) - phase order and HITL gates
- [`reasoning-modes.md`](../reasoning-modes.md) - character definitions
- [`builder-reference.md`](../builder-reference.md) - engineering patterns when cited
- [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) - lane ownership and must-nots
- [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md) - repo-specific routes
- [`EXECUTION-PLANNING.md`](EXECUTION-PLANNING.md) - downstream task-shaping phase

### Outputs

- Architecture Direction artifact only.
- No code changes.
- No merge.
- No `convmem record`.
- No new `logs/*.md`.
- No task decomposition or execution plan in this phase.

---

## Exit Criteria

This phase ends when:

- [ ] Four invariant questions answered (from [`PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md#four-question-invariant)):
  1. Where am I? -> Phase
  2. How should I think? -> Character
  3. What function am I performing? -> Function
  4. What standards apply? -> Planning protocol, active guide, and builder-reference when relevant
- [ ] Problem restated and source named
- [ ] System boundary explicit: in-scope, out-of-scope, deferred
- [ ] Two to three options compared; one chosen direction; rejected alternatives named
- [ ] Risks and reversibility documented for the chosen path
- [ ] Architecture Direction artifact emitted
- [ ] No self-transition to Execution Planning, Execute, or implementation
- [ ] No `convmem record` unless Ryan asks

Active phase lane must stop here. Await HITL.
