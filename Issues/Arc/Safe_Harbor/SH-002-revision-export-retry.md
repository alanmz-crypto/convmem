# SH-002 — Partial revision leaves an export that retry cannot complete

**Arc:** Safe Harbor · **Status:** open, static finding; not reproduced · **Priority:** P2

Codex, 2026-10-25. Source at `1a686753d8fd1b710883050e8a4f9c45b7ae1e26`; unchanged in inspected `origin/main`. **Confidence: 90% in the refusal path.** Interface issue between Chroma completion, export completion and retry evidence.

## Failure sequence

1. An existing decision and its export both contain approved base A. A valid proposal intends revision B.
2. Recovery verifies A's export, updates Chroma to B, and validates the new unit.
3. Export replacement fails, or the process stops just before it. Chroma now has B and its proposal marker; the export still has A; the proposal remains APPROVAL_STARTED.
4. A fresh retry classifies Chroma as already complete, but rejects A's export as conflicting. Repeating the command cannot complete this otherwise expected partial state.

This is an availability/recovery gap. **The refusal is safer than overwriting an arbitrary conflict**, and this report does not claim silent loss or a false successful retry.

## Source trace

- [propose_decision.py:652](../../../propose_decision.py#L652): `_check_recovery_export()` accepts an old export only while the live unit still has `base_hash` (lines 683–691). Otherwise it requires the proposed projection and raises `conflicting_export_projection`.
- [propose_decision.py:868](../../../propose_decision.py#L868): the accepted base export is held only in local variable `base_export`, before the native mutation at line 877. Export publication happens later, at lines 887–890.
- [propose_decision.py:151](../../../propose_decision.py#L151): after restart, proposed content plus this proposal's marker produces action `approve`, not `retry_chroma`.
- Even if the precheck were relaxed alone, [line 888](../../../propose_decision.py#L888) passes `allow_replace=False` for `approve`; `_ensure_export_for_recovery()` refuses replacement at lines 762–767.

The accepted T4 contract calls for recoverability of partial Chroma/export/event completion. Here the prior base-projection verification is lost with the process, and retry has no matching completion route.

## Evidence gap and qualification

[The base-retry fixture](../../../tests/_safe_harbor_t4_common.py#L466) exercises a successful existing-decision revision. [The export-failure fixture](../../../tests/_safe_harbor_t4_publication.py#L24) starts from `_setup_event_only`, where an interrupted approval has already ingested/exported the new unit. Neither combines a base revision with failure between its native update and export replacement.

The design also deliberately sends contradictory effects to human review. That supports retaining today's refusal until there is enough proof to distinguish this old verified projection from an unrelated edit. It does not establish that partial revision recovery is complete.

## Bounded resolution

First add the missing isolated interruption case. Define what existing approved-intent/base-hash and export evidence can safely license completion of A→B after Chroma has advanced. If that evidence is insufficient, document a bounded owner-mediated recovery route and narrow the completion claim. Do not simply allow replacement on every `approve`, replay Chroma, or weaken conflict refusal.

**Proposed evidence, not run:** fail before export replacement during a real base revision, restart, and independently inspect Chroma, old/new export rows and terminal-event count. A supported completion must leave one correct B projection and one APPROVED without rewriting B's vector; an unrelated conflicting export must still refuse.

<!-- ref: ./SH-001-jsonl-append-boundaries.md — distinct export framing defect -->
<!-- src: ../../../propose_decision.py, ../../../tests/_safe_harbor_t4_common.py, ../../../tests/_safe_harbor_t4_publication.py, ../../../docs/plans/EXECUTION-safe-harbor.md -->
