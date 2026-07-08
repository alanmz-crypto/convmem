# Planning Protocol

The Planning OS kernel. Answers one question: **Where am I in the workflow?**

---

## Single-Agent Principle

The planning system presently executes as one autonomous planner.

Until orchestration exists, the planner internally adopts the reasoning
behaviors, responsibilities, and review disciplines of multiple lanes.

This internal simulation does not replace Human-in-the-Loop approval.
Every HITL checkpoint remains a human decision gate.

---

## Documentation Rule

Every planning document answers exactly one question.
If a document answers multiple questions, split it.

| Document | Question |
|----------|----------|
| `PLANNING-PROTOCOL.md` | Where am I? |
| `reasoning-modes.md` | How should I think? |
| `planning/<PHASE>.md` | What function do I perform next? |
| `AGENT-ROLES.md` | Which agent lane and capability tier? |
| `role-charters.md` | What does each engineering role own? |
| `builder-reference.md` | How should I build? |

---

## Doctrine

Planning guides are executable specifications.

- Humans read them.
- Cursor follows them.
- Doctor verifies them.

---

## Loaded Vocabulary

| Term | Meaning |
|------|---------|
| **Phase** | Where I am in the workflow |
| **Character** | How I think (reasoning mode) |
| **Function** | What workflow job I am performing |
| **Role** | What an engineering role owns (seven charter cards only) |
| **Lane** | Which agent surface's constraints apply |
| **Authority** | Who may advance the workflow |

**Character vs Lane:** Characters are cognitive styles (adversarial review,
systems thinking). Lanes are capability tiers and must-not rules from
`AGENT-ROLES.md` (tool access, record discipline). They answer different
questions.

**Function vs Role:** Functions (Planner, Reviewer, Implementer) live in
phase guides. Roles (Retrieval / ML Engineer, Tech Writer, …) live in
`role-charters.md` only.

---

## Four-Question Invariant

Every phase must answer these before work begins:

| Question | Answer |
|----------|--------|
| Where am I? | Phase |
| How should I think? | Character → `reasoning-modes.md` |
| What function am I performing? | Function → active phase guide |
| What standards apply? | `builder-reference.md` |

When work touches engineering-team design, also consult **Role** via
`role-charters.md` — not every phase requires it.

---

## Planning Status

At the start of every planning-phase response, emit:

```
Planning Status

Phase:        ...
Characters:   ...
Functions:    ...
Lanes:        ...
Authority:    ...
```

---

## Workflow

```
Architecture Planning
    ↓
HITL Approval
    ↓
Execution Planning
    ↓
HITL Approval
    ↓
Execute Task
    ↓
HITL Review
    ↓
Revise Planning
    ↓
(repeat)
```

| Phase | Guide |
|-------|-------|
| Architecture Planning | `planning/ARCHITECTURE-PLANNING.md` |
| Execution Planning | `planning/EXECUTION-PLANNING.md` |
| Execute Task | `planning/EXECUTE-TASK.md` |
| Revise Planning | `planning/REVISE-PLANNING.md` |

---

## Phase Initialization

Before beginning any work:

1. Determine the current **Phase**.
2. Load the phase guide from `planning/`.
3. Execute that guide's Phase Initialization block.
4. Answer the four invariant questions.
5. Execute only the active phase's responsibilities.
6. Stop when Exit Criteria are met.

Each task or session declares a stop state: either `Stop: Continue` or
`Stop: Await HITL-N`.

---

## Precedence

On conflict, unless a human explicitly overrides:

1. `PLANNING-PROTOCOL.md`
2. `reasoning-modes.md`
3. Active phase guide
4. `AGENT-ROLES.md` (lanes)
5. `role-charters.md` (when engineering-role scope applies)
6. `builder-reference.md`

---

## State Transitions

All phase transitions pass through HITL gates. The planner does not
self-approve advancement. Authority remains with the human at each gate.

---

## Kernel Stability

`PLANNING-PROTOCOL.md` defines the Planning OS kernel.

Changes to the kernel should be rare and only when introducing new workflow
concepts.

Behavioral improvements belong in:

- Phase guides
- `reasoning-modes.md`
- `builder-reference.md`
- `AGENT-ROLES.md`

Do not expand the kernel with phase-specific behavior.

---

## Planning Guide Contract

Contract SSoT: [`planning/CONTRACT.md`](planning/CONTRACT.md).

Phase guides must satisfy the Planning Guide Contract. Doctor enforces
structure; humans enforce content.
