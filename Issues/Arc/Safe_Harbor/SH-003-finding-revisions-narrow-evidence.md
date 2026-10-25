# SH-003 — A changed finding replaces earlier unresolved evidence

**Arc:** Safe Harbor · **Status:** open, static contract gap; not reproduced · **Priority:** P2

Codex, 2026-10-25. Source at `1a686753d8fd1b710883050e8a4f9c45b7ae1e26`; unchanged in inspected `origin/main`. **Confidence: 95% in replacement behavior; 85% that it violates the retained-scope contract.** Interface issue within the existing incident authority.

## What is lost

The marker retains distinct finding IDs, but a revised finding overwrites its previous failure list and details. Two observations of the same segment/kind/reason can therefore narrow the unresolved evidence without a disposition.

Example: an audit records header and link failures; a later audit reports only link failures. The marker retains one finding at revision 2 with only the link failure. Similarly, a lost-vector finding's earlier count/sample is replaced by the later count/sample. There is no retained earlier payload in the incident authority.

## Source trace

- [chroma_write_guard.py:1175](../../../chroma_write_guard.py#L1175): finding identity hashes only segment, kind and reason.
- [chroma_write_guard.py:1474](../../../chroma_write_guard.py#L1474): audits use a fixed structural reason per segment; lost-vector audits likewise use a fixed reason at lines 1482–1491.
- [chroma_write_guard.py:1433](../../../chroma_write_guard.py#L1433): a changed digest triggers `current.update(...)`, replacing `failures` and `detail` while incrementing revision. Neither unions nor retains the displaced evidence.
- [chroma_write_guard.py:2896](../../../chroma_write_guard.py#L2896): the quarantine event contains incident IDs and a finding count, not the previous finding payload. Audit telemetry is also replaced on the next run.

Architecture invariant 4 and §6.4 explicitly prohibit replacing or narrowing unresolved scope; event history alone would not satisfy that contract either.

## What still works

The marker still blocks writers. Revision/digest changes invalidate old disposition submissions, and release runs full current structural/census checks. **This is not evidence that the current code releases a corrupt segment.** It is evidence that earlier unresolved details can disappear before the owner investigates/disposes of them.

[The existing revision test](../../../tests/test_safe_harbor_t1.py#L285) changes `[header]` into `[header, links]` and checks revision/digest movement. It never supplies a narrowing or disjoint second payload. The A→B overwrite control uses distinct IDs, so it tests a different failure.

## Bounded resolution

Retain the unresolved evidence in the existing `QUARANTINE.json` schema, with deterministic aggregation or explicit retained revisions. Keep identical reobservations idempotent, bind authorization to the complete retained set, and reserve removal of unresolved scope for disposition. No second ledger is needed.

**Proposed isolated evidence, not run:** publish `[header, links]` then `[links]`, and publish disjoint lost-ID samples under the same segment/kind/reason. Across restart, the authority must still expose the earlier unresolved evidence; older disposition digests must refuse. Keep a repeated-identical-observation control to avoid unbounded duplicate entries.

<!-- src: ../../../chroma_write_guard.py, ../../../tests/test_safe_harbor_t1.py, ../../../docs/plans/ARCHITECTURE-safe-harbor.md -->
