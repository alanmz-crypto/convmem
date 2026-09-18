# Arc Brief — Generalize the Append Cursor

> **Arc: Codex.** Current-state snapshot for the proposed format extension.
> This plan is independent of the still-gated Arc Codex P2 canary and does not
> grant production use.

## 1. What This Is For (product goal)

ConvMem should avoid paying to transform unchanged transcript history after
small appends, while preserving full source coverage, exact replay, and
governed projection writes. This extension asks whether the landed incremental
coordinator can safely serve one more JSONL format. Kiro PASSed the original
architecture and bounded Execute plan at stated tip `9e2d0ef`. Issue #286's
shared seam has since landed on `main`; this post-merge plan revision awaits a
targeted Kiro recheck. A live feature would still require authorized
implementation, hermetic proof, separate bootstrap/canary decisions, and
separate activation.

## 2. System Design (how the pieces connect)

```text
exact detected JSONL format + normal parser identity
                    |
          closed capability registry
                    |
       format-specific complete-prefix view
                    |
      existing incremental coordinator
      source/sidecar continuity + overlap frontier
      durable prepared cache + rollback journal
                    |
          governed writer/pruner
                    |
       checkpoint, then derived followers
```

Source bytes and parse-relevant sidecars are input authority. The checkpoint
is processing/recovery authority. Chroma and processed/export/dedupe files
are followers. A complete selected prefix may gain a pure append; it may not
be rewritten, truncated, replaced, or semantically changed before commit.
Unknown formats remain on the legacy path or refuse. Eligibility is a
reviewed code capability, never a broad user-config format list.

## 3. What Exists Right Now (file map)

| Surface | Current state |
|---|---|
| `incremental_jsonl.py` | On `main` through PR #307; default-off, format-specific coordinator and replay. Normal production route remains Kiro-only; isolated Codex routes require `CONVMEM_INCREMENTAL_ROOT`. |
| `incremental_jsonl_formats.py` | On `main`; closed Kiro/Codex capability registry with version, parser module, snapshot, and optional sidecar path. No Copilot entry. |
| `adapters/jsonl_prefix.py` | On `main`; complete-line scanner, byte ranges, outcomes, and `CompletePrefixView`. |
| `adapters/kiro_session_jsonl.py` | Existing `parse_complete_prefix()` provider and compatibility oracle. |
| `adapters/jsonl_io.py` | Common whole-file legacy JSONL iterator; scanner lives in `jsonl_prefix.py`. |
| `adapters/copilot_session_jsonl.py` | Whole-file parser with `workspace.yaml` and `session.start` metadata; no prefix capability or proven writer contract. |
| Codex rollout, history, Cursor adapters | Codex history/rollout complete-prefix adapters and fresh isolated route landed via PR #307. Rolling production history remains excluded; Cursor writer contract is unknown. |
| `ARCHITECTURE-generalize-append-cursor.md` | Original Kiro PASS at `9e2d0ef`; post-merge reconciliation targets the landed seam and needs targeted recheck. |
| `EXECUTION-generalize-append-cursor.md` | Original Kiro PASS at `9e2d0ef`; E1/E2 now reuse landed scanner/registry, while E0 remains the hard writer gate. |
| `.claude/worktrees/agent-…` under shared ROOT | Locked by a live harness; polluted R2b scan. Verification must use a clean worktree outside ROOT. |

The 2026-09-17 `origin/main` `18f63db` full-suite baseline has one
deterministic golden retrieval failure and zero R2b failures. It is unrelated
to this planning change; see the execution plan for the exact count.

## 4. Completion State

| Milestone | State | Next owner |
|---|---|---|
| Candidate inventory and design | Complete on pushed `plan/2026-09-17-generalize-append-cursor` at `9e2d0ef` | — |
| Architecture/Execute review | Kiro PASS on original `9e2d0ef`; post-merge plan correction on this branch awaits targeted Kiro recheck before any Execute grant | Kiro |
| Cross-arc coordination | Ryan selected the Codex Sol-medium lane that authored the coordination handoff; it assigned the completed #286 writer, reconciles the merged base, and returns later Execute choices to Ryan without implementation authority | Codex Sol-medium |
| #286 shared base | [PR #307](https://github.com/alanmz-crypto/convmem/pull/307) squash-merged to `main` as `d657767`; Kiro/Copilot PASSed reviewed tip and all six CI checks passed. The shared registry/scanner are now the base for this Copilot proposal. | Codex reconciles plan; Kiro rechecks |
| Condition A — Copilot metadata evidence | Pending: E3 must exercise `workspace.yaml` id changes, `session.start` versus YAML precedence, and chosen digest-versus-effective-fields invalidation | Cursor if granted; Kiro verifies evidence |
| Condition B — shared-code base | Resolved: issue #286 landed as `d657767`, so Copilot work must extend the merged registry/scanner. A later Copilot code-writer assignment belongs to Ryan's Execute grant. | Ryan |
| E0 writer-contract evidence | Not started; ungranted pending targeted plan recheck and an exact real-client action/provider-cost bound | Ryan decides whether Cursor may run it later |
| E1–E4 implementation and hermetic verification | Not started; conditional on E0 evidence/review and a later Ryan grant | Cursor if authorized |
| Existing-source bootstrap | Unauthorized; separate cost/authority decision | Ryan |
| Live canary and activation | Unauthorized; existing Arc Codex gates remain | Ryan |

## 5. Your Role

**If sent for coordination:** Ryan selected the Codex Sol-medium lane that
authored the [coordination handoff](../inter-model/CODEX-2026-09-18-append-cursor-ownership-handoff.md).
Reconcile the Copilot plan with the merged #286 seam, obtain targeted Kiro
recheck, and return a concrete E0-only choice to Ryan. This role carries no
implementation or Sol-High authority.

**If Ryan sent you to decide Execute:** Kiro PASSed the original planning
packet at `9e2d0ef`; the post-merge correction needs targeted Kiro recheck.
The shared-code base is now `main` at `d657767`. E0 remains ungranted until
an exact action/provider-cost bound is approved; E1–E4 require later evidence
and a separate grant. Kiro's PASS grants no operation. See the
[Codex-to-Codex coordination handoff](../inter-model/CODEX-2026-09-18-append-cursor-ownership-handoff.md).

**If sent for Cursor implementation:** stop until Ryan issues an exact E0-only
grant; E1–E4 require a later separate grant. E0 failure ends the proposed
Copilot route. If E3 is
granted, show sidecar `session_id` change and `session.start` versus YAML
precedence explicitly, and state whether digest change or effective-field
change triggers rebuild. No substitute format, live source, provider, or
activation is implied.

**If sent for operational work:** consult the existing
`STATUS-codex-jsonl-production-integration.md` and its Ryan gates. This
planning brief provides no P2, bootstrap, watcher, or configuration authority.

## 6. What Remains Before Live (sequential)

1. Kiro rechecks this post-merge planning tip against the landed #286
   registry/scanner and prior design conditions. Inspect the plan at this
   branch tip and code at `origin/main` `d657767`; the planning checkout's code
   predates the squash merge. Isolated Codex history does not establish
   eligibility for rolling production history.
2. Ryan decides whether to grant **E0 alone** in temporary isolated resources,
   with exact real-client actions and a provider-call/cost ceiling. E0 remains
   ungranted until that decision.
3. Cursor proves or rejects Copilot writer eligibility; E0 failure returns
   `NO_COPILOT_ROUTE` without substituting another format.
4. If E0 passes review, Ryan separately grants a bounded E1–E4 implementation
   against the merged base; Cursor supplies clean-worktree hermetic evidence.
5. E3 evidence exercises sidecar id change and `session.start`/YAML
   precedence, and declares the implemented invalidation discipline.
6. Kiro reviews the exact implementation tip; Ryan separately chooses PR
   disposition.
7. Existing-source adoption, live canary, and activation each require their
   own later evidence, review, and Ryan decision. No date is assumed.

## 7. Hard Stops

| Stop | Owner | Blocks |
|---|---|---|
| Execute grant | Ryan | Any coordinator, adapter, test, or config implementation |
| Shared-code writer for Copilot | Ryan | Arc Codex E1–E4 touching merged coordinator until a later writer assignment |
| E0 writer proof | Cursor evidence + Kiro review | Copilot eligibility and E2 routing |
| Bootstrap cost/authority | Ryan | Adopting or rebuilding already-indexed sources |
| P2/live canary | Existing Arc Codex gates + Ryan | Production source, Chroma, or provider operations |
| Activation | Ryan | Live config and watcher route |

No gate implies another.

## 8. Relationship to ConvMem

This is a scoped extension of Arc Codex's ingestion efficiency/recovery
mechanism. It does not alter retrieval ranking, semantic calibration, R2b
attestation, Shadow Ledger, or the source/projection authority direction.
Trapdoor Hunt issue #286's Codex-format implementation landed on `main` as
`d657767`. The Copilot proposal reuses its shared registry/scanner and grants
no new work in that arc.

## 9. Key Design Files

| Purpose | Path |
|---|---|
| Format-extension design | `docs/plans/ARCHITECTURE-generalize-append-cursor.md` |
| Proposed bounded Execute | `docs/plans/EXECUTION-generalize-append-cursor.md` |
| Existing Kiro design | `docs/plans/ARCHITECTURE-codex-jsonl-production-integration.md` |
| Existing Arc Codex state/gates | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Coordinator | `incremental_jsonl.py` |
| Adapter seam | `adapters/jsonl_io.py`, `adapters/kiro_session_jsonl.py`, `adapters/copilot_session_jsonl.py` |
| Source handoff | `docs/inter-model/CODEX-2026-09-17-generalize-append-cursor-handoff.md` at `439b5fc` (separate branch) |
| Distinct Codex-format implementation | [PR #307](https://github.com/alanmz-crypto/convmem/pull/307), squash-merged as `d657767` on `main` |

## 10. How to Update This Brief

After each milestone, overwrite sections 3–6 with current state and the next
lane. Remove completed checklist items. Add one milestone-level Update Log
line. Keep this file a snapshot, not a session diary.

### Update Log

| Date | Who | Milestone change |
|---|---|---|
| 2026-09-17 | Codex | Created the conditional one-format architecture and proposed Execute packet for Kiro review; no implementation authority |
| 2026-09-18 | Kiro / Codex | Kiro PASSed planning tip `9e2d0ef` with metadata-evidence and shared-code-owner conditions; Codex verified the local and remote tip; Ryan's Execute decision is next |
| 2026-09-18 | Codex | Reassessed the pushed #286 integration successor and handed Codex Sol a single-owner recommendation; Ryan's ownership and E0 decisions remain pending |
| 2026-09-18 | Ryan / Codex | Ryan selected the authoring Codex Sol-medium lane for cross-arc coordination; shared-code writer and E0 gates remain pending |
| 2026-09-18 | Ryan / Codex | Ryan delegated the writer choice; Codex assigned the existing #286 Cursor integrator through branch disposition and deferred Copilot E0 |
| 2026-09-18 | Codex | Prepared exact-tip Copilot and Kiro read-only recheck handoffs for the unmerged #286 integration successor |
| 2026-09-18 | Kiro / Codex | Kiro returned exact-tip PASS on #286 integration with 116 passing focused tests; Copilot audit remains pending |
| 2026-09-18 | Copilot / Codex | Copilot returned exact-tip FAIL on #286 documentation acceptance while affirming runtime safety; bounded Cursor docs correction and fresh reviews are next |
| 2026-09-18 | Cursor / Codex | Cursor pushed three-doc correction at `19d34a5`; Codex verified clean diff-check and issued fresh exact-tip Copilot/Kiro recheck handoffs |
| 2026-09-18 | Kiro / Codex | Kiro PASSed corrected #286 exact tip `19d34a5` for S0–S3 continuity and routing; Copilot audit remains pending |
| 2026-09-18 | Copilot / Codex | Copilot PASSed corrected #286 exact tip `19d34a5`; both reviewers now PASS and Ryan's PR decision is next |
| 2026-09-18 | Ryan / Codex | Ryan authorized PR steward; PR #307 opened at reviewed `19d34a5` with initial CI pending and merge reserved to Ryan |
| 2026-09-18 | Codex | PR #307 reached mergeable state with all six checks PASS and no unresolved threads; Ryan owns merge |
| 2026-09-18 | Ryan / Codex | Ryan squash-merged #286 as `d657767`; Codex reconciled the Copilot plan with the landed registry/scanner for targeted Kiro recheck |

## TL;DR

- [Arc Codex] The generalization is technically possible only through a
  reviewed, versioned complete-prefix capability per adapter.
- Kiro PASSed the planning packet at stated tip `9e2d0ef`; Copilot's writer
  behavior still must be proven. Codex Sol-medium coordinates, and the existing
  #286 Cursor integrator owns shared-code edits through disposition. E0 and
  later implementation remain ungranted; no live operation is granted.
