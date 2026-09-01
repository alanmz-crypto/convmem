# ConvMem Project Status Awareness

> Current cross-arc snapshot for model handoffs. Arc-specific detail belongs in the
> linked `docs/plans/STATUS-*.md` briefs; this file answers what is active, what is
> closed, and what may proceed next.

**Snapshot:** 2026-09-01 (`origin/main` is at `0b6b436ca054a1b04dc9c5c46eb2533268fe0a90`; branch and PR work named below is not on `main` unless explicitly stated)

> **Trapdoor Hunt / T3:** CLOSED and Claude whole-surge PASSed. PR #221 is
> squash-merged onto current main; its bounded writer-boundary and
> provenance-supersession corrections are included. Runway Ledger is CLOSED and
> its current-main integration is complete.

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
- **R2b capture** v1 code, the v2 normative plan, and the v2 I1–I3
  implementation are on `main`. Corrective IX integration landed via PR #264
  (merge `58375ad`, reviewed integration `39eab77`); live capture remains
  unauthorized, and quarantined v1 / `2026-08-27-r2b-capture-02` packets must
  not be reused.
- Two non-fatal doctor warnings often present: legacy `embed_collection_identity` metadata
  and external restic freshness. They do not authorize corpus mutation or Shadow activation.

## Active arcs — work remaining

| Arc | State | Next authorized action |
|---|---|---|
| JudgeBench semantic calibration v1 | G3 locked on `main` (#170); Phase A prep merged (#171); Chroma R4 GREEN | Ryan's separate 60-call calibration experiment grant, then G4 judge selection. Keep `--legacy` path separate from v1 provenance. |
| Shadow Ledger Phase 0 | Code + VERIFY complete; **disabled** | **Activation-ready path:** C6 event-size evidence → C7 7-day census report → C6 canary PASS → fresh writer census → runbook → Ryan readiness sign-off → **then** live activation grant + `shadow-activate`. Do not hand-edit config. |
| R2b capture authorization | v2 I1–I3 implementation and Corrective IX integration are **landed** via PR #264; implementation review is complete. Draft PRs #246/#248/#249/#251 are closed as superseded, with their branches preserved. | Separately accept zero-bypass coverage and duration policy, then obtain fresh writer-gate/packet/grant authority. No live gate, packet ACCEPT, **ACCEPT AND GRANT**, capture, or I4–I8 advancement is authorized. |
| Track 1 complete-data backup | v2 rollout complete | Hybrid consistency-bar Copilot audit remains a **separate** open track — not a JudgeBench or Shadow prerequisite. See [`STATUS-complete-data-backup-correction-v2.md`](../plans/STATUS-complete-data-backup-correction-v2.md). |
| CG-2 authority migration | Design A Execute-close is **LANDED** via PR #250 at `e930ae4c…`; the accepted D7 source was transplanted onto current main. A later retained-reference-v2 corrective remains branch-only and must not be attributed to `main`. V8c and every production step remain PENDING/unauthorized. | No further Design A landing work. Separately governed reference-v2 review/implementation may proceed only under its own accepted plan/grant. Do not run production D0/D1, publish fence/pointer, activate an owner, run GC, or enable Shadow/R2b. See [`ARCHITECTURE-cg2-production-activation.md`](../plans/ARCHITECTURE-cg2-production-activation.md), [`VERIFY-cg2-production-activation.md`](../plans/VERIFY-cg2-production-activation.md), and [`RUNBOOK-cg2-production-activation.md`](../plans/RUNBOOK-cg2-production-activation.md). |
| Trapdoor Hunt — T3 provenance trust substrate | T3 **CLOSED**; PR #221 squash-merged at `722141d31e586151f361ef7006ad74c71cdff534` from final reviewed head `bfe79f728cde60ec5e8f7021c87dcebf23ee1eca`; bounded writer-boundary and provenance-supersession corrections are on current `main` with Runway integration complete | No further T3 integration work. Bootstrap, migration/backfill, CG-2 activation, Shadow/R2b, GC, T4, and T5 remain separately governed and unauthorized. |
| Recovery Authority | T1 landed via PR #234, T2 via PR #236, and scratch-only T3 via PR #238 at `d250feb2…`. T3 prepares an isolated replacement candidate and does not publish serving state or touch live authority. T4 remains unstarted; V4k remains **BLOCKED** on separately governed CG-2 reference-v2 closure. | T4 is next in the accepted sequence but **NOT AUTHORIZED**. V4k needs a later fresh grant after its dependency closes. No live restore, replacement, projection activation, serving, migration, mutation, or T5 campaign. |
| Naturalistic product-value evaluation | G1–G5 **LANDED on `main`** (routing PR #261 at `676d6b5`). Methodology validation complete; not product evidence. Arc brief: [`STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md). | **G6 Ryan-LOCKED** until ChatGPT review; favorable synthetic results do not open G6. Then Ryan explicit grant or park arc. |
| Portland baseline experiment | Protocol-v3 branch `experiment/2026-08-30-portland-rerun3-v3` ended in **RERUN3 SEED-GENERATION FAILURE** at `9ba72378…`; pre-v3 seed evidence is superseded but preserved. Nothing is on `main`. | No retry and no Agent B execution are authorized. Preserve the failed/superseded evidence; do not treat it as a product verdict. |

## Closed arcs — reference STATUS only

| Arc | State | Notes |
|---|---|---|
| Chroma Reconcile Tier L | **Closed GREEN** (#161) | Optional R5 anomaly disposition; Ryan-gated watch/refine ops only. Do not re-run R4 without regression request. |
| Pinwheel Pytest CI | **Closed** (#191; closeout #195/#196/#197) | Reproducible pytest gate live on `main`. No further Pinwheel work. |
| CodeQL Complex Therapy | **Closed/PASS** (#202) | `Protect Main` requires the five CodeQL/Pylint/Pytest contexts. Ryan owns the quarterly + config-drift attestation. No technical execution remains. |
| Runway Ledger — Agent Run identity tracking | **CLOSED** | Core implementation merged (#215); hook-enable soak passed + #216 merged; other clients are future optional slices, not unfinished Runway work; no remaining Runway execution. See [`STATUS-agent-run-ledger.md`](../plans/STATUS-agent-run-ledger.md). |

## Recently completed, not active blockers

- Watch subprocess OOM isolation **landed** via PR #245 at `3dd355a5`; the
  prior READY_FOR_PR handoff is historical.
- Relocation retrieval scoping **landed** via PR #247 at `a19b5cbb`.
- Shared writer-attestation hardening **landed** via PR #243 at `872a0e48`.
- STATUS arc-brief pattern on `main` (#160–#161): arc briefs + cross-arc rollup (this file); Naturalistic brief added in the post-merge reconciliation for PR #255.
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
- [Recovery Authority STATUS](../plans/STATUS-recovery-authority.md)
- [Naturalistic product-value STATUS](../plans/STATUS-naturalistic-product-value.md)
- [Agent workflow cheat sheet](../MODEL-WORKFLOW.md)

**TL;DR:** `origin/main` is `0b6b436c`: Naturalistic G1–G5 methodology is landed
but non-live; G6 and every study/live/product-disposition step remain
Ryan-gated. Recovery/CG-2 remain non-live, R2b implementation is landed but
operational capture is separately gated, and Portland is stopped at
seed-generation failure.

## Jargon TL;DR

| Term | Meaning |
|---|---|
| Cross-arc snapshot | This file’s current-state rollup across named project arcs. |
| I1–I3 / I4–I8 | R2b implementation and later operational milestones; landing does not grant live capture. |
| G6 | The Ryan-gated prospective naturalistic product-value study freeze. |
| T4 | The next Recovery Authority execution stage; it is not authorized here. |
| V4k | A Recovery Authority verification item blocked on CG-2 reference-v2 closure. |
