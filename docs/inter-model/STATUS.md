# ConvMem Project Status Awareness

> Current cross-arc snapshot for model handoffs. Arc-specific detail belongs in the
> linked `docs/plans/STATUS-*.md` briefs; this file answers what is active, what is
> closed, and what may proceed next.

**Snapshot:** 2026-08-21 (coordination through PR #220; draft integration PR #221 refreshed from main `9381efe`)

> **Trapdoor Hunt / T3:** CLOSED and Claude whole-surge PASSed. Draft PR #221
> integrates frozen T3 onto current main without reopening it; Runway Ledger
> semantics remain externally owned and unchanged.

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
- **JudgeBench G3 corpus is merged and locked on `main` (#170)**; Phase A fail-closed calibration prep is merged on `main` (#171). Running the calibration experiment and G4 judge selection remain Ryan-gated. Upstream Chroma R4 GREEN.
- **Shadow Ledger Phase 0 code + corrective C1–C7 are on `main`** (#122, #126, #131, #134);
  shadow remains **disabled**. Activation requires **activation-ready evidence** then a
  separate Ryan grant — see [`STATUS-shadow-ledger-phase0.md`](../plans/STATUS-shadow-ledger-phase0.md).
- **R2b capture** code is on `main`; live capture is unauthorized; quarantined draft packet
  must not be reused.
- Two non-fatal doctor warnings often present: legacy `embed_collection_identity` metadata
  and external restic freshness. They do not authorize corpus mutation or Shadow activation.

## Active arcs — work remaining

| Arc | State | Next authorized action |
|---|---|---|
| JudgeBench semantic calibration v1 | G3 locked on `main` (#170); Phase A prep merged (#171); Chroma R4 GREEN | Ryan's separate 60-call calibration experiment grant, then G4 judge selection. Keep `--legacy` path separate from v1 provenance. |
| Shadow Ledger Phase 0 | Code + VERIFY complete; **disabled** | **Activation-ready path:** C6 event-size evidence → C7 7-day census report → C6 canary PASS → fresh writer census → runbook → Ryan readiness sign-off → **then** live activation grant + `shadow-activate`. Do not hand-edit config. |
| R2b capture authorization | Code on `main`; live capture unauthorized | Fresh T4 packet + Ryan ACCEPT AND GRANT before any capture. |
| Track 1 complete-data backup | v2 rollout complete | Hybrid consistency-bar Copilot audit remains a **separate** open track — not a JudgeBench or Shadow prerequisite. See [`STATUS-complete-data-backup-correction-v2.md`](../plans/STATUS-complete-data-backup-correction-v2.md). |
| CG-2 authority migration | Merged on `main` (#186); V8b (legacy-only gateway soak grant) **recorded/PASS**; **soak completion UNRESOLVED**. First generational owner / activation / GC not authorized. | Do not activate, grant a first owner, or run GC. Do not claim soak success until completion is verified. See [`VERIFY-cg2-production-activation.md`](../plans/VERIFY-cg2-production-activation.md) and [`RUNBOOK-cg2-production-activation.md`](../plans/RUNBOOK-cg2-production-activation.md). |
| Runway Ledger — Agent Run identity tracking | Implemented on `main` (#215); hooks enabled (#216); soak passed 2026-08-20; **arc closing** (Ryan recorded arc-close). Other clients are future slices, not arc requirements. | Stay clear unless on the Runway lane: the arc is Runway-owned and in closeout. Reflect only its current status. See [`STATUS-agent-run-ledger.md`](../plans/STATUS-agent-run-ledger.md). |
| Trapdoor Hunt — T3 provenance trust substrate | T3 **CLOSED** on frozen branch; Claude whole-surge PASS; draft main-integration PR #221 under exact-SHA validation/review | Finish Kiro/Copilot review of the integration candidate, then stop for Ryan before any merge. Deferred Bootstrap/migration/CG-2/Shadow/R2b/T4/T5 work remains unauthorized. |

## Closed arcs — reference STATUS only

| Arc | State | Notes |
|---|---|---|
| Chroma Reconcile Tier L | **Closed GREEN** (#161) | Optional R5 anomaly disposition; Ryan-gated watch/refine ops only. Do not re-run R4 without regression request. |
| Pinwheel Pytest CI | **Closed** (#191; closeout #195/#196/#197) | Reproducible pytest gate live on `main`. No further Pinwheel work. |
| CodeQL Complex Therapy | **Closed/PASS** (#202) | `Protect Main` requires the five CodeQL/Pylint/Pytest contexts. Ryan owns the quarterly + config-drift attestation. No technical execution remains. |

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
- [Pinwheel Pytest CI STATUS](../plans/STATUS-pinwheel-pytest-ci.md) (closed)
- [CodeQL Complex Therapy STATUS](../plans/STATUS-codeql-complex-therapy.md) (closed)
- [CG-2 VERIFY](../plans/VERIFY-cg2-production-activation.md) and [CG-2 RUNBOOK](../plans/RUNBOOK-cg2-production-activation.md)
- [Runway Ledger STATUS](../plans/STATUS-agent-run-ledger.md)
- [Agent workflow cheat sheet](../MODEL-WORKFLOW.md)

**TL;DR:** Closed T3 is in draft main-integration PR #221 without reopening deferred work; Runway Ledger remains unchanged, and all other arc gates retain their existing owners.
