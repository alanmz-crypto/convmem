# Execution Plan: Enforce Explicit Arc Classification Before Execute

## Planning Status

| Field | Value |
|-------|-------|
| **Phase** | Execution Planning |
| **Characters** | Task Decomposer, Dependency Mapper, Scope Guardian |
| **Functions** | Planner |
| **Lanes** | Codex authors; Kiro reviewed the architecture direction PASS; Cursor implements after Ryan approval; Ryan gates |
| **Authority** | Awaiting Ryan HITL approval for Execute |
| **Baseline** | Architecture direction `ARCHITECTURE-arc-classification-verify-gate.md`; current checkout `docs/2026-08-13-codex-planning-only-guard` |

**Source:** Ryan request to complete the Codex plan and prepare it for Cursor; Kiro design review PASS on the architecture direction.

**Goal:** Make the arc/non-arc decision explicit for eligible work, block unresolved classification, and surface missing or contradictory records without burdening trivial drive-by changes.

## Human consequence

Cursor receives a finite implementation brief with one authoritative intake record, deterministic doctor checks, and scenario tests. Ryan must approve this execution plan before Cursor edits tracked implementation files; Cursor must stop and return to planning if the repository cannot support the stated metadata boundary without broadening scope.

## Scope lock

### In scope

- `docs/PLANNING-PROTOCOL.md`
- `docs/planning/EXECUTE-TASK.md`
- A new `docs/plans/INTAKE-<slug>.md` template and the classification contract it represents
- `doctor.py` and focused doctor tests
- Protocol generation/parity updates only if the canonical protocol source requires them
- `docs/plans/VERIFY-arc-classification-verify-gate.md` stub and the worktree-cleanup disposition record

### Out of scope

- Any rewrite of `VERIFY-PLANNING.md` or existing VERIFY plans
- Automatic creation of intake or VERIFY records
- Automatic classification, embedding/model inference, branch-wide commit heuristics, or task orchestration
- Changes to unrelated active arcs, historical handoffs, ledger data, user-level agent configuration, or runtime deployment
- Implementing the worktree-cleanup remediation itself

## Classification contract to implement

The new intake artifact is the durable, task-owned source for eligible work:

```markdown
# Intake — <slug>

task_classification: arc | non_arc | arc_review
classification_reason: <one sentence>
classification_authority: <Ryan approval / named waiver / intake owner>
classification_slug: <same slug for arc; n/a otherwise>
classification_review_by: <date or event for arc_review; n/a otherwise>
verify_path: docs/plans/VERIFY-<slug>.md | n/a
scope_triggers_observed: <comma-separated hard/soft trigger names, or none>
```

Rules:

1. `arc` requires a non-empty slug and an existing VERIFY stub at `verify_path`.
2. `non_arc` requires a reason and authority reference; it must state why no VERIFY is required.
3. `arc_review` is unresolved and blocks Execute handoff; it requires `classification_review_by` and may not use `n/a` for the reason.
4. A hard trigger, or any two soft triggers, changes an existing `non_arc` record to `arc_review` before more execution.
5. Trivial drive-by work does not need an intake artifact unless it enters the Execute Task lifecycle or later meets an escalation trigger.

## Tasks

| ID | Deliverable | In scope | Depends on | Gates | Execution lane |
|----|-------------|-----------|------------|-------|----------------|
| T1 | Canonical intake and protocol rule | Add the classification states, eligibility boundary, hard/soft triggers, stop semantics, and `INTAKE-<slug>.md` template; replace the informal `(arc?)` branch. | — | Markdown review; protocol contract/parity checks | Cursor |
| T2 | Execute handoff integration | Update Execute Task Step 0, required inputs, handoff, and exit criteria so eligible work names the intake record; require `arc`→VERIFY pairing and `arc_review` stop. | T1 | Focused text/anchor tests; planning-guide contract | Cursor |
| T3 | Doctor backstop | Add a deterministic doctor check for intake records: missing/invalid classification, missing reason/authority, unresolved review, arc slug/path mismatch, and missing VERIFY stub. It must scan only `docs/plans/INTAKE-*.md`; it must not infer from branch history. | T1 | Unit tests for clean, malformed, arc, non-arc, review, and unrelated-branch cases; doctor smoke | Cursor |
| T4 | Scenario coverage and generated surfaces | Add tests for trivial non-arc, multi-session escalation, hard-trigger escalation, valid arc, and existing declared-arc compatibility. Regenerate protocol projections only through the existing generator and verify parity. | T2, T3 | `pytest -q`; generation idempotence/parity; `convmem doctor` | Cursor |
| T5 | Proof-case disposition and VERIFY stub | Add the classification record for the worktree-cleanup case only after Ryan chooses `arc` or explicitly authorizes `non_arc`; create/fill the VERIFY companion stub if arc is chosen. Do not invent historical evidence. | T1, T2 | Ryan decision recorded; no claim of retroactive VERIFY execution | Cursor after Ryan disposition |

## Dependencies and stop points

```text
T1 ──> T2 ──┐
  └──> T3 ───┴──> T4 ──> Cursor handoff
                         |
                         └──> T5 only after Ryan proof-case decision
```

- T1–T3 are serial in the stated order because T2 and T3 must consume one contract.
- T4 can begin after T2 and T3 are both complete.
- T5 is blocked on Ryan's explicit worktree-cleanup classification and must not be guessed by Cursor.
- Any implementation discovery that requires scanning arbitrary branch history, changing Verify OS semantics, or inventing a task database returns to Codex Architecture Planning.

## Evidence requirements for Cursor

| Evidence | Required result |
|----------|-----------------|
| Trivial drive-by fixture | `non_arc` with reason/authority passes without VERIFY; missing reason fails. |
| Valid arc fixture | `arc` with matching slug and existing VERIFY stub passes. |
| Arc mismatch fixture | Missing stub or mismatched `verify_path` fails. |
| Unresolved fixture | `arc_review` is surfaced and blocks the protocol handoff. |
| Escalation fixtures | One hard trigger or two soft triggers require reclassification; one soft trigger alone does not create bureaucracy. |
| Noise-control fixture | Unrelated commits/dirty files do not affect the intake check. |
| Existing workflow | Existing declared arcs and planning-guide contract remain green. |
| Repository gates | `pytest -q`, `convmem doctor`, `git diff --check`; run protocol generation/parity checks if T1 changes the source slice. |

Execute evidence must include the exact subject tip SHA, changed-file list, test exit codes, doctor output summary, and the BugBot applicability row required by `EXECUTE-TASK.md`. Docs-only changes may record the valid BugBot exemption with its reason.

## Arc VERIFY companion

- **Path:** `docs/plans/VERIFY-arc-classification-verify-gate.md`
- **Status:** Stub required before Execute handoff; fill after implementation.
- **Template:** `docs/plans/VERIFY-TEMPLATE.md`
- **Planned checks:** protocol classification contract, doctor detection matrix, escalation scenarios, generated-surface parity, and proof-case disposition.

## Ryan decisions required before Cursor Execute

1. Approve this execution plan and authorize Cursor implementation.
2. Decide whether the worktree-cleanup proof case is `arc` or an explicitly documented `non_arc` exemption. If `arc`, provide/confirm its stable slug and authorize creation of the VERIFY stub; if exempt, provide the reason and authority reference.
3. Confirm that the current checkout branch mismatch/read-only Git metadata is resolved before implementation begins. Cursor must not implement from an uncommitted plan on the wrong branch.

## Execute entry

- First task: T1 after Ryan approves this plan.
- Cursor must read the architecture direction and this execution plan before editing.
- Cursor must stop at the Execute HITL boundary after evidence collection; it must not self-advance to Verify closeout or alter unrelated files.

**Active phase lane must stop here. Await HITL.**
