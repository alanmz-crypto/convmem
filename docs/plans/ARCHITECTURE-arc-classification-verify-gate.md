# Architecture Direction: Make Arc Classification Explicit Before Execution

## Planning Status

| Field | Value |
|-------|-------|
| **Phase** | Architecture Planning |
| **Characters** | Architect, Systems Thinker, Risk Reviewer |
| **Functions** | Planner |
| **Lanes** | OpenAI Codex authors; Kiro reviews; Ryan approves (HITL); Cursor implements after an approved execution plan |
| **Authority** | Awaiting Ryan HITL approval |
| **Baseline** | `docs/2026-08-13-arc-classification-verify-gap` at `984b83b`, 2026-08-13 handoff |

**Source:** Kiro implementation handoff `KIRO-2026-08-13-arc-classification-verify-gap-handoff.md`, authorized by Ryan for Codex architecture planning.

**Problem:** The Verify OS correctly requires `VERIFY-<slug>.md` for declared arcs, but the workflow does not require anyone to declare whether eligible work is an arc or an explicitly exempt non-arc before implementation.

## Human consequence

Ryan gets an explicit, inspectable answer at intake. A trivial drive-by can remain non-arc with one short reason; work that crosses an objective risk or duration threshold must either enter the arc/VERIFY path or carry a Ryan-approved waiver. The worktree-cleanup proof case can no longer disappear into the unclassified branch.

## System boundary

### In scope

- The planning intake contract used before Execute Task begins.
- A durable classification record attached to the task or handoff.
- Objective scope-escalation rules for work that starts small and grows.
- A `convmem doctor` check that surfaces missing, malformed, stale, or contradictory classification/VERIFY metadata.
- Protocol, phase-guide, generated-surface, and focused-test updates required to keep the rule live.
- A one-time disposition of the worktree-cleanup proof case.

### Out of scope

- Rewriting the existing Verify OS, its V0–Vn minimum bar, or its independent sign-off model.
- Automatically creating VERIFY files or automatically converting work into an arc.
- Inferring classification from branch names, commit counts alone, model identity, or unrelated dirty worktree state.
- Making `doctor` a substitute for intake or Ryan's authority to waive work.
- Reclassifying historical plans, transcripts, ledger records, or completed work in bulk.
- Adding a new orchestrator, task database, or cross-repository service.

### Deferred with owner

- A future task-management surface may store the same schema outside Markdown; Ryan owns that separate architecture decision.
- Threshold tuning after observing three eligible arcs belongs in a follow-up decision, not in implementation discovery.

## Current repository evidence

| Surface | Current behavior | Gap this direction closes |
|---------|------------------|---------------------------|
| `docs/PLANNING-PROTOCOL.md` | The Execute → HITL Review branch shows `(arc?)`, with no required decision artifact. | Add classification as a named state before the branch can proceed. |
| `docs/planning/EXECUTE-TASK.md` | Step 0 records scope and authority, and only says an arc must name VERIFY. | Make classification a required intake field and define reclassification on scope growth. |
| `docs/planning/VERIFY-PLANNING.md` | Defines an arc and the required VERIFY artifact, but assumes entry was already selected. | Keep this contract unchanged; intake becomes the entry guard. |
| `doctor.py` / `tests/test_doctor_arc_staleness.py` | Doctor already reports stale active STATUS arcs, but does not inspect task classification or VERIFY pairing. | Add a bounded advisory check for protocol omissions and contradictions. |
| Handoff branch | Worktree cleanup had multiple review rounds and no classification or VERIFY artifact. | Require a documented arc or explicit Ryan exemption before the fix is considered complete. |

## Constraints and invariants

1. **Classification is explicit, not inferred.** Every eligible task records exactly one of `arc`, `non_arc`, or `arc_review` before Execute Task proceeds.
2. **Non-arc is an affirmative exception, not absence.** `non_arc` requires a concise reason and an owner/authority reference; a blank or omitted field is invalid for eligible work.
3. **Arc implies VERIFY.** `arc` requires a stable slug and a `docs/plans/VERIFY-<slug>.md` stub before the Execute handoff is merge-ready. The existing Verify OS remains the authority for contents and closeout.
4. **Uncertainty escalates.** `arc_review` blocks the Execute handoff until Ryan resolves it to `arc` or `non_arc`; agents may not silently choose the less burdensome branch.
5. **Growth reopens classification.** If objective escalation criteria are met after intake, the record changes to `arc_review` and the workflow returns to the classification gate before further execution.
6. **Trivial work stays cheap.** A single-session, reversible, single-commit change with no evidence dependency can use a one-line `non_arc` reason; it does not need a VERIFY stub.
7. **Doctor is a detector, not an authority.** Doctor may warn or fail on malformed protocol state, but never creates metadata, grants a waiver, or self-classifies work.
8. **One source, generated projections.** The canonical classification wording belongs in the governing protocol/phase guide; generated agent surfaces are regenerated from the source rather than hand-edited.
9. **Historical evidence is preserved.** The implementation updates the proof case and current protocol, not old work products that predate this gate.

## Classification contract

The execution intake gets a small, copyable block. The exact serialization (front matter versus Markdown table) is an execution-plan choice, but the fields and allowed values are fixed here:

```text
task_classification: arc | non_arc | arc_review
classification_reason: <one sentence>
classification_authority: <Ryan approval / named waiver / intake owner>
classification_slug: <required for arc; blank for non_arc>
classification_review_by: <required for arc_review; otherwise n/a>
verify_path: docs/plans/VERIFY-<slug>.md | n/a
```

`arc_review` is the safe initial value when the intake cannot establish the answer. It is not a third execution category and cannot be used to bypass the decision.

## Escalation trigger

The protocol should use observable criteria rather than a fuzzy “feels like an arc” test. A task must move from `non_arc` to `arc_review` when any one hard trigger occurs, or when any two soft triggers occur:

| Trigger | Type | Examples |
|---------|------|----------|
| Irreversible/destructive operation, production or external configuration change, authorization boundary, schema/public API change, security/correctness invariant, or evidence-dependent claim | Hard | Cleanup/delete, live grant, migration, externally visible behavior, proof needed to establish safety |
| Work spans a second session or second implementation handoff | Soft | More than one session is evidence of duration, not a classification by itself |
| More than one implementation commit or more than one review round | Soft | Prevents review-only churn from silently becoming an untracked milestone |
| Multiple downstream consumers, explicit stop conditions, or a dependency on a prior gate | Soft | Indicates bounded milestone behavior |

The hard-trigger list is intentionally more important than a numeric threshold. Commit/session counts are escalation signals only and must not classify unrelated branch history. A task may remain `non_arc` after one soft trigger if its reason states why the trigger does not apply; two soft triggers require `arc_review`.

## Options considered

| Option | Summary | Decision |
|--------|---------|----------|
| A — Doctor-only heuristic | Warn when a branch has age/commit/session signals without a VERIFY file. | Rejected as the primary gate: too late, branch history is noisy, and it cannot prove which task owns the commits. Retain a narrower doctor check as a backstop. |
| B — Required intake classification plus escalation and doctor backstop | Record classification before Execute; escalate on objective scope growth; doctor detects omissions and contradictions. | **Chosen.** It places the decision where task identity and authority are known, catches handoff omissions, and preserves a low-cost path for trivial work. |
| C — Automatic arc classification | Convert work to an arc whenever heuristics fire and create the VERIFY stub automatically. | Rejected: it invents human intent, can attach unrelated work, and violates the handoff requirement that automation must not create VERIFY intent. |

## Chosen direction

Adopt Option B. Add the classification block to Execute Task Step 0 and the planning protocol branch. Require `arc` or an explicit `non_arc` reason before an eligible task enters execution; use `arc_review` for uncertainty and for objective scope escalation. Require an existing VERIFY stub for `arc` before merge-ready handoff. Add a doctor check that scans only explicitly supported current task/handoff metadata and reports missing classification, invalid values, an arc without a VERIFY path, a non-arc without a reason/authority, or an unresolved `arc_review`. Doctor remains advisory for ordinary repository state, while the protocol/HITL stop is the blocking control.

## Target lifecycle

```text
Ryan request / approved scope
            |
            v
Execute Task Step 0: record classification
            |
     +------+------+
     |             |
   arc        non_arc (reason + authority)
     |             |
 VERIFY stub   execute with ordinary task gates
     |             |
     +------ scope grows? ------+
                                |
                         arc_review (stop)
                                |
                    Ryan resolves arc or non_arc
                                |
                         arc -> VERIFY closeout
```

No branch permits silent omission. No automated path creates the VERIFY artifact or waives Ryan's decision.

## Public seams and ownership

| Decision/artifact | Owner | Boundary |
|-------------------|-------|----------|
| Classification wording and escalation rules | `PLANNING-PROTOCOL.md` + `EXECUTE-TASK.md` | Canonical protocol; no generated-surface hand edits |
| Classification record | Execute Task intake author | Must identify task, scope, authority, and current state |
| Scope reclassification | Implementer/reviewer who observes trigger; Ryan resolves | Observation may stop work; only Ryan resolves ambiguity/waiver |
| VERIFY stub and closeout evidence | Codex predeclares; Cursor supplies evidence; independent reviewer signs; Ryan gates | Existing Verify OS remains unchanged |
| Doctor diagnostic | `doctor.py` implementation lane after approval | Detect/report only; no mutation or authority |
| Proof-case disposition | Ryan | Must explicitly classify worktree cleanup as arc or exempt non-arc |

## Required implementation surfaces (for downstream Execution Planning)

1. Update `PLANNING-PROTOCOL.md` to replace the informal `(arc?)` branch with the classification states and explicit stop semantics.
2. Update `docs/planning/EXECUTE-TASK.md` Step 0, required inputs, handoff, and exit criteria with the classification block, escalation triggers, and `arc`→VERIFY pairing.
3. Add the canonical check contract and a focused `doctor.py` check/tests. The check must be deterministic from supplied repository metadata and must not inspect unrelated branch history as task identity.
4. Update generated protocol surfaces through the existing generator and add parity/contract assertions where required.
5. Add a current, human-readable disposition for the worktree-cleanup proof case; do not manufacture verification evidence retroactively.

## Fitness properties and acceptance evidence

| Property | Evidence required |
|----------|-------------------|
| Classification cannot be silently skipped | A fixture/intake test rejects missing or invalid classification for eligible work; protocol text names the HITL stop. |
| Arc cannot bypass VERIFY | A fixture/test rejects `arc` with missing/mismatched VERIFY path and accepts a valid stub. |
| Non-arc remains lightweight but explicit | A trivial single-commit scenario accepts `non_arc` with reason/authority and no VERIFY file; missing reason fails. |
| Scope growth is surfaced | A scenario with one hard trigger or two soft triggers changes to `arc_review` and blocks continuation until resolution. |
| Doctor is useful without false positives | Doctor fixtures cover clean trivial work, unresolved review, malformed metadata, and unrelated branch history; only task-owned metadata is considered. |
| Existing VERIFY flow is unchanged | Existing planning-contract and VERIFY tests pass; declared arcs still reach the same V0–Vn and independent-signoff gates. |
| Surfaces do not drift | Protocol generation is idempotent and generated slices match the canonical source. |

## Risks and reversibility

- **False escalation:** Mitigate by treating commit/session counts as soft signals, requiring two soft signals, and requiring task-owned metadata rather than branch-wide inference. Thresholds can be tuned without changing the state model.
- **Protocol friction:** Keep `non_arc` to a compact reason/authority line and do not require VERIFY for trivial reversible work.
- **Doctor noise:** Make the doctor check metadata-scoped and advisory; a noisy heuristic must not become a blocking health failure.
- **Stale exemptions:** Require an authority reference and optional review-by field; doctor reports unresolved or expired records. Ryan can revise the record without changing implementation code.
- **Migration ambiguity:** The proof case is a required acceptance item. It must be explicitly classified by Ryan, with no claim that a missing historical VERIFY can be reconstructed.
- **Rollback:** Remove the new doctor check and protocol fields as one reviewed revert if adoption proves harmful. Existing VERIFY files and declared arcs remain valid because the direction does not alter Verify OS semantics.

## Downstream handoff

- Next phase: `EXECUTION-PLANNING.md` after Ryan approves this direction.
- Cursor implementation must remain bounded to the listed protocol, doctor, tests, generated-surface, and proof-case files.
- Kiro reviews this direction; Ryan decides whether the proof case is `arc` or an explicitly authorized `non_arc` exemption.
- No implementation, VERIFY execution, merge, deployment, or ledger record is authorized by this document.

**Active phase lane must stop here. Await HITL.**
