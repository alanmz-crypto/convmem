# Revise Planning

Answers: **How do I update the plan after implementation?**

---

## Phase Initialization

| Field | Value |
|-------|-------|
| **Phase** | Revise Planning |
| **Characters** | Plan Auditor, Claims Verifier, Risk Reviewer, Prioritizer, Process Steward |
| **Functions** | Planner (produce revised plan), Reviewer (adversarial pass) |
| **Lanes** | Codex owns plan revision; implementation findings return through Ryan; Kiro (design discipline, no unsolicited record); Cursor (honest implementation status) |
| **Engineering References** | Zeller, EvoArch, DDIA per [`builder-reference.md`](../builder-reference.md) |
| **Probe Version** | v2 |
| **Exit Condition** | Plan revised or no-revision evidence table complete |
| **Authority** | Awaiting HITL |

Only after initialization may revision begin.

---

## Objective

Update an existing plan so it matches branch reality, closed priorities, and
verified claims — without auto-advancing to Architecture or Execute.

---

## Responsibilities

### Planning Status (emit at start)

```
Planning Status

Phase:        Revise Planning
Characters:   Plan Auditor, Claims Verifier, Risk Reviewer
Functions:    Planner, Reviewer
Lanes:        Codex owns revision; findings via Ryan; Kiro; Cursor (status)
Authority:    Awaiting HITL
```

### When to enter

- After **Execute Task** and HITL Review (primary loop entry)
- When Ryan asks to revise a plan mid-stream
- When a plan has stale priorities, branch drift, or unverified claims

### Required inputs

| Input | Why |
|-------|-----|
| Active plan file(s) | What to revise |
| `git status` / branch vs `main` | Prevent false "shipped on main" claims |
| `convmem doctor` + `convmem brief` | Ground ops/corpus claims if cited |
| Prior retro | [`retro-template.md`](../retro-template.md) §0 when revising process |

### Revision steps (ordered)

| Step | Action |
|------|--------|
| **0** | Audit previous retro countermeasures — [`retro-template.md`](../retro-template.md) §0; `retro-loop-closure` row |
| **1** | **Stale priority scan** — closed bugs, WIP vs `main`, superseded handoffs |
| **2** | **HITL principle review** — [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) must-nots; handoff ≠ record |
| **3** | **Builder-reference review** — pick digests; name fitness checks (`doctor`, `verify-builder-reference.sh`) |
| **4** | **Ledger-vs-reality sweep** — (a) claims vs code with file:line; `UNVERIFIED(owner)` grep per [`role-mapping.md`](../role-mapping.md) |
| **5** | **Edit the plan** — lock one path; remove option forks; add done criteria and gates |

### Awareness (read-only context)

- [`TEAM-CHARTER-2026-07-06.md`](../inter-model/TEAM-CHARTER-2026-07-06.md)
- [`VERIFICATION-MATRIX.md`](../inter-model/VERIFICATION-MATRIX.md)
- [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md)
- [`SESSION-CLOSE-RECORD.md`](../inter-model/SESSION-CLOSE-RECORD.md)

### Outputs

- Updated plan or explicit no-revision evidence table
- Revision stamp: date, branch, verified/deferred claims, suggested next phase
- No `convmem record` unless Ryan requests

---

## Exit Criteria

This phase ends when:

- [ ] Four invariant questions answered (from [`PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md#four-question-invariant)):
  1. Where am I? → Phase
  2. How should I think? → Character
  3. What function am I performing? → Function
  4. What standards apply? → builder-reference
- [ ] Stale priorities removed or deferred with owner
- [ ] Plan claims verified against branch/code or marked `UNVERIFIED(owner)`
- [ ] Revised plan written (or no-revision evidence table)
- [ ] Revision stamp recorded
- [ ] No auto-transition to Architecture or Execute
- [ ] No `convmem record` unless Ryan asks

Active phase lane must stop here. Await HITL.
