# Evidence — Current-State Pointer Classification

**Status:** Read-only classification evidence; Kiro PASS after a targeted
canonical-source correction of one stale backup row.

**Authority:** This document does not update LATEST.md, archive material, create
a new current-state authority, or authorize implementation. It supports the
reviewed Current-State Pointer Reconciliation plan.

## Classification basis

The candidate below reconciles:

- docs/inter-model/LATEST.md;
- docs/inter-model/README.md, docs/README.md, docs/STATUS.md, and
  docs/MODEL-WORKFLOW.md;
- SYNTHESIS-STATUS.md;
- current standing-check plans;
- complete-data backup correction-v2 architecture; and
- the Neutral/Office Gate 0 phased path.

Kiro independently classified the pointer, then confirmed two corrections:
PR #120 commit 492e6e7 is immutable Ryan A-FAIL/FAIL evidence, not active work;
Neutral/Office Gate 0 is Waiting/gated under Ryan HITL.

## Global operating guardrail

The deployed checkout remains frozen at
76126e07a97187f68d925dd8b431d2d03967084f through 2026-08-07 00:00 UTC.
This belongs above the manifest as a boundary notice, not as a work lane. It
permits only separate-worktree docs/planning, read-only investigation, and
tests that do not change the deployed checkout or live artifacts.

## Candidate compact manifest

### Active now

| Canonical artifact | Next actor | Now | Recheck/remove when |
|---|---|---|---|
| CURRENT-STATE-POINTER-RECONCILIATION.md | Codex, then Kiro/Ryan | Contract is Kiro PASS; read-only classification is complete and the candidate manifest awaits Ryan decisions on disputed lanes and the future routing change. | Ryan accepts, changes, or declines the contract/migration direction. |
| PLAN-2026-07-31-RETRIEVAL-GAP-TRIAGE.md | Codex / Crush | Reproduce the remaining current-testing and CLI/synthesis-pointer retrieval gaps after pointer routing is clarified; classify documentation versus retrieval causes. | Fixed regression queries show the pointer contract is sufficient, or evidence supports a separate retrieval change. |

### Waiting / gated

| Canonical artifact | Next actor | Now | Recheck/remove when |
|---|---|---|---|
| EXECUTION-shadow-phase0-activation-corrective.md | Ryan, then Cursor | Shadow remains disabled. A corrective activation plan exists, but implementation and any live activation require Ryan approval/grant. | Ryan approves or rejects the corrective plan; a separate activation grant remains required after implementation. |
| ARCHITECTURE-r2b-capture-auth.md | Ryan | R2b code is on main, but live capture is unauthorized; the prior T4 packet is quarantined. | Ryan issues a fresh T4 packet and ACCEPT AND GRANT, or formally closes the track. |
| research-pack-2026-07-24-backup-neutral/attachments/PHASED-PATH.md | Ryan and Office authorities | Neutral/Office Gate 0 awaits authorization of an Office repository/pass and identification of a real office policy artifact. | Gate 0 is granted or the direction is explicitly declined; no Office or Neutral implementation before then. |

### Standing / deferred

| Canonical artifact | Next actor | Now | Recheck/remove when |
|---|---|---|---|
| PLAN-2026-07-31-RECENCY-BOOST-RETUNE-EVALUATION.md | Ryan schedules evaluation; Codex plans; Cursor implements only after approval | Standing check is due because corpus growth crossed its trigger. A post-freeze, sealed-set evaluation is designed; no config retune is authorized. | A reviewed post-freeze evaluation and Ryan decision complete, or the trigger is replaced by approved evidence. |
| PLAN-2026-07-31-ESCALATION-THRESHOLD-STANDING-CHECK.md | Ryan / planning lane | Standing check is due, but current logs lack an attempt denominator; the honest state is count-only HOLD, not a threshold change. | Approved attempt instrumentation and two complete windows support a review, or Ryan accepts continued HOLD. |
| SYNTHESIS-STATUS.md | Ryan | Digest Phase 1 is shipped; Phase 2 linker product remains deferred on agent-habit/value evidence. | Ryan finds the agent-habit gate met, changes the phase decision, or closes the product path. |
| VERIFY-semantic-dedupe-hygiene.md | Ryan | Default dedupe band is complete. Lower bands and Phase D snapshot steering remain separate, unauthorized work. | Ryan grants a bounded lower-band or Phase D brief, or explicitly retires it. |

## Material deliberately excluded from the candidate pointer

| Material | Classification | Reason |
|---|---|---|
| PR #120 / 492e6e7 complete-data backup attempt | Historical failed evidence | Correction-v2 architecture records Ryan A-FAIL/FAIL and says never rehabilitate. The later complete-data-v2 rollout is complete. |
| Complete-data-v2 rollout | Completed history | It is an operational completion, not an open lane. Link it from archive/history if needed. |
| Merged protocol, PR Steward, BugBot, audit-substitute, CI, source-trust, retrieval, and lane-split entries | Durable procedure or completed history | These define reusable rules or shipped work; they require no current actor unless an explicit future trigger occurs. |
| Workspace salvage and research-pack mechanics | Supporting provenance | The Neutral Gate 0 row links the actual current decision; the pack itself is not a separate active lane. |
| Old Shadow Architecture HITL entry | Superseded history | Execute merged; the only possible live residual is captured by the one Shadow activation row. |

## Disputed or insufficient-evidence items

1. Change Feed Phase 3: the pointer says hold until a date that has passed.
   Ryan must reaffirm, retire, or assign a new evidence/gate condition.
2. Crush UI waiting-for-tool-response residual: it has no canonical plan, owner,
   or recheck condition. Do not add it as a live row until a current observation
   or owner establishes one.
3. C6/C7 freeze-readiness detail: retain the deployment freeze as a global
   notice. Add a separate lane only if a canonical current C6/C7 plan names an
   actionable next actor beyond the existing hold.

## Routing contradictions proven by this classification

- LATEST.md mixes live gates, completed work, and historical narrative inside
  one Active handoff section.
- README and STATUS still direct mtime/newest-file discovery despite LATEST
  claiming to be the single pointer and docs/README naming brief plus ledger as
  operational truth.
- The old backup-audit row conflicts directly with correction-v2 immutable FAIL
  evidence and must not survive a reconciliation.
- Standing checks are due and have current design artifacts, contrary to the
  stale claim that they have no plan.
- Neutral/Office Gate 0 is a current Ryan gate but is easy to miss in the
  research-pack history.

## Next safe action

Use this evidence for Kiro/Ryan review of the proposed manifest. Do not edit
LATEST.md or archive anything until the pointer contract's Ryan decisions and
the later coupled brief.py routing change are authorized.
