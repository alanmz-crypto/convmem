# ConvMem Project Status Awareness

> Current cross-arc snapshot for model handoffs. Arc-specific detail belongs in the
> linked `docs/plans/STATUS-*.md` briefs; this file answers what is active, what is
> closed, and what may proceed next.

**Snapshot:** 2026-08-28 (R2b v2 clean-base recovery candidate prepared; `main` is at `872a0e483dd5eff09ccaef3c655af82f5e81e92e`; reviewed base was `89a7e045b130f005f57539478d9a180cbea905df`)

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
- **R2b capture** v1 code is on `main`, but its timing-only live path is superseded for
  future execution by the v2 exclusive writer-gate amendment. Live capture remains
  unauthorized; quarantined v1 and `2026-08-27-r2b-capture-02` packets must not be reused.
- Two non-fatal doctor warnings often present: legacy `embed_collection_identity` metadata
  and external restic freshness. They do not authorize corpus mutation or Shadow activation.

## Active arcs — work remaining

| Arc | State | Next authorized action |
|---|---|---|
| JudgeBench semantic calibration v1 | G3 locked on `main` (#170); Phase A prep merged (#171); Chroma R4 GREEN | Ryan's separate 60-call calibration experiment grant, then G4 judge selection. Keep `--legacy` path separate from v1 provenance. |
| Shadow Ledger Phase 0 | Code + VERIFY complete; **disabled** | **Activation-ready path:** C6 event-size evidence → C7 7-day census report → C6 canary PASS → fresh writer census → runbook → Ryan readiness sign-off → **then** live activation grant + `shadow-activate`. Do not hand-edit config. |
| R2b capture authorization | v2 writer-gate plan prepared; implementation and live capture unauthorized | Ryan architecture review → Cursor implementation → same-tip Copilot/Kiro review. Only then: policy-pending duration acceptance, fresh quiescence authority, packet ACCEPT, and **ACCEPT AND GRANT**. No v1 packet upgrade/reuse. |
| Track 1 complete-data backup | v2 rollout complete | Hybrid consistency-bar Copilot audit remains a **separate** open track — not a JudgeBench or Shadow prerequisite. See [`STATUS-complete-data-backup-correction-v2.md`](../plans/STATUS-complete-data-backup-correction-v2.md). |
| CG-2 authority migration | Gateway implementation merged (#186); V8a/V8b PASS and legacy-only soak Ryan-accepted. Production copied D1 failed at equivalence; two independent reviews rejected its sidecar corrective. Ryan locked reference-v2 semantics 2026-08-29: `G_rb` references exact original D0-covered LEGACY rows; D0 remains valid; failed `2d01dfca…` is quarantined/ineligible/untouched. V6c reference-v2 and V8c are **PENDING**. | Exact corrective planning package is on `plan/2026-08-29-cg2-d1-reference-v2-corrective`; next is independent Kiro review, then Ryan plan acceptance. No implementation, production D1 retry, cleanup, `G_canary`, V8c, fence/pointer, cutover, retirement, GC, Shadow/R2b, or D2+. See [`ARCHITECTURE-cg2-production-activation.md`](../plans/ARCHITECTURE-cg2-production-activation.md), [`EXECUTION-cg2-design-a.md`](../plans/EXECUTION-cg2-design-a.md), [`VERIFY-cg2-production-activation.md`](../plans/VERIFY-cg2-production-activation.md), and [`RUNBOOK-cg2-production-activation.md`](../plans/RUNBOOK-cg2-production-activation.md). |
| Trapdoor Hunt — T3 provenance trust substrate | T3 **CLOSED**; PR #221 squash-merged at `722141d31e586151f361ef7006ad74c71cdff534` from final reviewed head `bfe79f728cde60ec5e8f7021c87dcebf23ee1eca`; bounded writer-boundary and provenance-supersession corrections are on current `main` with Runway integration complete | No further T3 integration work. Bootstrap, migration/backfill, CG-2 activation, Shadow/R2b, GC, T4, and T5 remain separately governed and unauthorized. |
| Recovery Authority | Architecture/plan accepted; T1 landed via PR #234 and T2 via PR #236; recovered authority/projection validity/serving readiness remain separate. Ryan has locked CG-2 reference-v2 semantics, but V4k remains **BLOCKED** until the corrective plan is independently accepted and the reference-v2 serving/recovery contract is implemented and verified. | Scratch-only bulk recovery (V4j/T3) remains next but NOT AUTHORIZED; V4k requires a fresh later grant after CG-2 corrective closure. No implementation, restore, activation, migration, live mutation, or T5 campaign. |

## Closed arcs — reference STATUS only

| Arc | State | Notes |
|---|---|---|
| Chroma Reconcile Tier L | **Closed GREEN** (#161) | Optional R5 anomaly disposition; Ryan-gated watch/refine ops only. Do not re-run R4 without regression request. |
| Pinwheel Pytest CI | **Closed** (#191; closeout #195/#196/#197) | Reproducible pytest gate live on `main`. No further Pinwheel work. |
| CodeQL Complex Therapy | **Closed/PASS** (#202) | `Protect Main` requires the five CodeQL/Pylint/Pytest contexts. Ryan owns the quarterly + config-drift attestation. No technical execution remains. |
| Runway Ledger — Agent Run identity tracking | **CLOSED** | Core implementation merged (#215); hook-enable soak passed + #216 merged; other clients are future optional slices, not unfinished Runway work; no remaining Runway execution. See [`STATUS-agent-run-ledger.md`](../plans/STATUS-agent-run-ledger.md). |

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
- [Recovery Authority STATUS](../plans/STATUS-recovery-authority.md)
- [Agent workflow cheat sheet](../MODEL-WORKFLOW.md)

**TL;DR:** CG-2 reference-v2 semantics are Ryan-locked and the corrective plan
awaits independent review; implementation, production D1 retry, cleanup,
activation, Shadow/R2b, GC, T4, and T5 remain separately governed and
unauthorized.
