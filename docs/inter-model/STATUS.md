# ConvMem Project Status Awareness

> Current cross-arc snapshot for model handoffs. Arc-specific detail belongs in the
> linked `docs/plans/STATUS-*.md` briefs; this file answers what is active, what is
> closed, and what may proceed next.

**Snapshot:** 2026-08-09

## Project goal

ConvMem should answer questions from a durable, locally searchable corpus with
traceable evidence, honest abstention, and evaluation signals that distinguish
retrieval failures from synthesis or judge failures. Chroma is a rebuildable
projection of the ledger/export, and production mutations remain explicitly gated.

## Current system state

- `convmem doctor` passes. The live brief reports 18,721 knowledge units and 2,383
  summaries; rerun `convmem brief --stdout-only` for current counts rather than
  treating these numbers as permanent.
- The Chroma Reconcile Tier L arc is **closed GREEN**: the post-rebuild inventory
  found zero HNSW-without-METADATA orphans, the flatten guard tests passed, the
  legacy calibration path passed 5/5, and doctor passed. See
  [`STATUS-chroma-reconcile-tier-l.md`](../plans/STATUS-chroma-reconcile-tier-l.md)
  and the [Flash R4 handoff](FLASH-2026-08-08-post-rebuild-verify-handoff.md).
- The current calibration command is explicit about the legacy path:
  `python scripts/eval-synthesis.py --judge --legacy --golden <fixture>`.
  The 100% legacy result is informational and does not replace JudgeBench gold
  calibration.
- Two non-fatal doctor warnings remain: legacy `embed_collection_identity`
  metadata and the external restic snapshot/freshness condition. They do not
  authorize corpus mutation or Shadow activation.
- `convmem unresolved` currently reports two open staging2 CSP observations.
  They are operational observations, not evidence that the Chroma rebuild failed.

## Active arcs and next action

| Arc | State | Next authorized action |
|---|---|---|
| JudgeBench semantic calibration v1 | T2–T5 implementation is on `main`; Chroma R4 GREEN unblocks downstream calibration. G3 gold cases/split and G4 judge selection are not started. | Ryan authors/locks the gold corpus and split; then run calibration and choose the judge. Keep the `--legacy` path separate from v1 provenance. |
| Chroma Reconcile Tier L | Code, rebuild, R4 verification, and documentation are complete on `main` (#161). | Optional R5 disposition and Ryan-gated watch/refine operations only; do not re-run gates without a regression request. |
| R2b capture authorization | Implementation is on `main`; live capture remains unauthorized. The old draft packet is quarantined. | Ryan must issue a fresh ACCEPT AND GRANT packet before any capture. |
| Shadow Ledger Phase 0 | Merged and mechanically/independently verified, but disabled by default. | Activation remains a separate Ryan grant; do not edit live config or create an activation manifest. |
| Track 1 complete-data backup | v2 rollout completed; the Hybrid consistency-bar audit remains a separate open track. | Continue only under its exact audit/merge gates; it is not a prerequisite for JudgeBench. |

## Recently completed, not active blockers

- The qwen3.5 automated-ingest GPU contention fix is complete: automated
  summarization uses `deepseek-v4-flash`, embedding timeout is 300 seconds,
  `OLLAMA_MAX_LOADED_MODELS=2`, and ingest chunk failures are logged/retried.
- The former ask-trace/synthesis-calibration work is covered by the current
  evaluation and JudgeBench surfaces; do not create a second competing fixture
  without a new brief.

## Hard boundaries

- JudgeBench G3/G4, live `ask.py` judging, R2b live capture, Shadow activation,
  bulk indexing/refinement, and production configuration changes require the
  named owner/grant in their arc brief.
- A retrieved-evidence miss and an incomplete synthesized answer are different
  failure classes. Preserve that distinction when adding calibration rows.
- Do not use stale July artifacts as current calibration evidence. Prefer the
  current arc STATUS brief and dated handoff, then verify live state with the
  session-start commands.

## Canonical pointers

- [JudgeBench STATUS](../plans/STATUS-judgebench.md)
- [Chroma Reconcile STATUS](../plans/STATUS-chroma-reconcile-tier-l.md)
- [R2b capture STATUS](../plans/STATUS-r2b-capture-auth.md)
- [Shadow Ledger STATUS](../plans/STATUS-shadow-ledger-phase0.md)
- [Latest cross-model handoff](LATEST.md)

**TL;DR:** Chroma is GREEN and JudgeBench is the next substantive arc, but Ryan
still owns gold/split and judge-selection gates; R2b capture and Shadow activation
remain explicitly unauthorized.
