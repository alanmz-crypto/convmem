# ConvMem Project Status Awareness

> Current cross-arc snapshot for model handoffs. Arc-specific detail belongs in the
> linked `docs/plans/STATUS-*.md` briefs; this file answers what is active, what is
> closed, and what may proceed next.

**Snapshot:** 2026-08-14

## Project goal

ConvMem should answer questions from a durable, locally searchable corpus with
traceable evidence, honest abstention, and evaluation signals that distinguish
retrieval failures from synthesis or judge failures. Chroma is a rebuildable
projection of the ledger/export, and production mutations remain explicitly gated.

## Current system state

- `convmem doctor` passes. Rerun `convmem brief --stdout-only` for current unit/summary
  counts — do not treat snapshot numbers as permanent.
- **Chroma Reconcile Tier L is closed GREEN** — 0 HNSW-without-METADATA orphans post-rebuild;
  legacy calibration path passed 5/5. See
  [`STATUS-chroma-reconcile-tier-l.md`](../plans/STATUS-chroma-reconcile-tier-l.md).
- **JudgeBench T2–T5 code is on `main` (#155)**; G3 gold corpus and G4 judge selection are
  Ryan-gated. Upstream Chroma R4 GREEN unblocks calibration work.
- **Shadow Ledger Phase 0 code + corrective C1–C7 are on `main`** (#122, #126, #131, #134);
  shadow remains **disabled**. Activation requires **activation-ready evidence** then a
  separate Ryan grant — see [`STATUS-shadow-ledger-phase0.md`](../plans/STATUS-shadow-ledger-phase0.md).
- **R2b capture** code is on `main`; live capture is unauthorized; quarantined draft packet
  must not be reused.
- **CG-1 committed-generation dependability is merged and accepted** (#172–#174), but
  remains hermetic. CG-2 production activation is in Architecture Planning only; no
  production owner uses generation authority yet.
- Two non-fatal doctor warnings often present: legacy `embed_collection_identity` metadata
  and external restic freshness. They do not authorize corpus mutation or Shadow activation.

## Active arcs — work remaining

| Arc | State | Next authorized action |
|---|---|---|
| JudgeBench semantic calibration v1 | T2–T5 on `main`; Chroma R4 GREEN | Ryan authors/locks G3 gold + split; then calibration run and G4 judge selection. Keep `--legacy` path separate from v1 provenance. |
| Shadow Ledger Phase 0 | Code + VERIFY complete; **disabled** | **Activation-ready path:** C6 event-size evidence → C7 7-day census report → C6 canary PASS → fresh writer census → runbook → Ryan readiness sign-off → **then** live activation grant + `shadow-activate`. Do not hand-edit config. |
| R2b capture authorization | Code on `main`; live capture unauthorized | Fresh T4 packet + Ryan ACCEPT AND GRANT before any capture. |
| Track 1 complete-data backup | v2 rollout complete | Hybrid consistency-bar Copilot audit remains a **separate** open track — not a JudgeBench or Shadow prerequisite. See [`STATUS-complete-data-backup-correction-v2.md`](../plans/STATUS-complete-data-backup-correction-v2.md). |
| CG-2 production activation | Architecture locked at `e680ce837653698a5be8b78ba02db2f880c40c63`; Kiro PASS and Ryan Execute granted to Cursor for `6a808f1`; production remains legacy | Cursor implements T1–T5 on a fresh branch. No gateway soak, owner activation, or GC yet. See [`STATUS-cg2-production-activation.md`](../plans/STATUS-cg2-production-activation.md). |

## Closed arcs — reference STATUS only

| Arc | State | Notes |
|---|---|---|
| Chroma Reconcile Tier L | **Closed GREEN** (#161) | Optional R5 anomaly disposition; Ryan-gated watch/refine ops only. Do not re-run R4 without regression request. |

## Recently completed, not active blockers

- STATUS arc-brief pattern on `main` (#160–#161): four arc briefs + cross-arc rollup (this file).
- Summarizer GPU contention fix: automated ingest uses `deepseek-v4-flash`; embed timeout 300s;
  `OLLAMA_MAX_LOADED_MODELS=2`; chunk failures logged/retried.
- Prior C7 writer census was **removed 2026-08-06** after freeze lift — Shadow activation
  needs a **fresh** census arm; do not assume the old run still exists.

## Hard boundaries

- JudgeBench G3/G4, live `ask.py` judging, R2b live capture, Shadow activation,
  bulk indexing/refinement, and production configuration changes require the named
  owner/grant in their arc brief.
- **Merge ≠ activate** for Shadow. **C7 arm ≠ activate.** **C6 canary PASS ≠ activate.**
- A retrieved-evidence miss and an incomplete synthesized answer are different failure
  classes. Preserve that distinction when adding calibration rows.
- Prefer arc STATUS briefs + dated handoffs over stale July chat artifacts; verify live
  state with session-start commands.

## Canonical pointers

- [Cross-arc rollup](STATUS.md) (this file)
- [Latest session handoff](LATEST.md)
- [JudgeBench STATUS](../plans/STATUS-judgebench.md)
- [Chroma Reconcile STATUS](../plans/STATUS-chroma-reconcile-tier-l.md) (closed)
- [Complete-data backup STATUS](../plans/STATUS-complete-data-backup-correction-v2.md)
- [R2b capture STATUS](../plans/STATUS-r2b-capture-auth.md)
- [Shadow Ledger STATUS](../plans/STATUS-shadow-ledger-phase0.md)
- [CG-2 production activation STATUS](../plans/STATUS-cg2-production-activation.md)
- [Agent workflow cheat sheet](../MODEL-WORKFLOW.md)

**TL;DR:** CG-1 is merged but still hermetic; CG-2 is architecture-review only.
Chroma is GREEN; JudgeBench, Shadow, and R2b retain their separate named gates.
