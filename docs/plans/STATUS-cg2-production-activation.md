# STATUS — CG-2 production activation

**Last updated:** 2026-08-15
**Arc:** CG-2 production activation of committed generations
**State:** Architecture locked; Kiro execution-plan review PASS; Ryan Execute granted to Cursor for `6a808f1`; implementation not yet started; no production activation authority

## 1. Purpose and product goal

ConvMem must never serve a hybrid or partially replaced file generation after
an interrupted reindex. CG-1 built and proved the committed-generation
substrate. CG-2 makes that substrate the production authority through a bounded,
reviewed migration.

The product is done only when production reads and reindexing use committed
generation authority, logical health accounting is truthful, rollback is
drilled, and activation/GC remain separately gated.

## 2. System model

```text
source file
   │
   ├─ watcher hint + bounded source reconciliation
   ├─ secure open + source hash
   ▼
CG-1 build → stage → cold validate
   │
   ├─ expected-active check
   ├─ current-source hash check (CG-2)
   ▼
legacy fence (first cutover only) → qualified pointer
                                      │
                                      ▼
                           request-frozen authority vector
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
       legacy-authorized owners                   active generations
                 └────────────────────┬────────────────────┘
                                      ▼
                         serving repository/gateway
                                      │
                  query / ask / related / serving stats

Inactive generations stay physical but cannot serve.
Promotion happens before reclamation; automatic GC is initially disabled.
```

Key invariants:

- pointer authority remains per owner;
- compatibility is explicit and never error fallback;
- a monotonic fence prevents legacy resurrection after first cutover;
- one request freezes its authority mapping after per-owner evidence
  read/derive/revalidate succeeds;
- pre-fence readers may finish, but post-fence owner resolution cannot select legacy;
- rename is explicit owner migration because CG-1 identity is path-derived;
- logical identity governs parity; physical IDs are diagnostic;
- source freshness and active-generation freshness are separate promotion checks;
- filesystem notifications schedule work; startup/overflow/periodic
  reconciliation proves eventual source convergence;
- future online GC requires pin-before-dereference or pin/revalidate/retry;
- no automatic GC in the first activation slice.

## 3. What exists on disk now

| Artifact | State | Meaning |
|---|---|---|
| `file_generation_contract.py` | Complete on `main` | CG-1 deterministic owner/generation/physical identity and manifests |
| `file_generation_builder.py` | Complete on `main`, hermetic | Candidate construction; not wired to production ingest |
| `file_generation_store.py` | Complete on `main`, hermetic | Staging, exact validation, mediated proof reads |
| `file_generation_pointer.py` | Complete on `main`, hermetic | Fresh qualification, pointer publication/recovery, stale-generation refusal |
| `file_generation_validate.py` | Complete on `main`, hermetic | Fresh-process cold validation |
| `ingest_dedupe.py` logical-ID support | Complete on `main` | CG-1 logical dedupe support |
| `tests/test_file_generation_*.py` | Complete on `main` | CG-1 proof and frozen read-boundary inventory |
| `docs/plans/ARCHITECTURE-cg2-production-activation.md` | **Locked at `e680ce837653698a5be8b78ba02db2f880c40c63` on `plan/2026-08-14-cg2-production-activation`** | Ryan-approved production authority, migration, health, and rollout design |
| `docs/inter-model/CURSOR-2026-08-15-cg2-delta-confirmation.md` | **Complete on branch** | Kiro/Crush/Cursor exact-SHA PASS rollup |
| `docs/inter-model/CURSOR-2026-08-14-cg2-feasibility-review.md` | **Complete on branch** | `1222b1e` feasibility review (historical; superseded by delta confirmation) |
| `docs/inter-model/CRUSH-2026-08-14-cg2-evidence-review.md` | **Complete on branch** | `1222b1e` evidence review (historical; superseded by delta confirmation) |
| `docs/plans/EXECUTION-cg2-production-activation.md` | **Reviewed PASS by Kiro at `6a808f1`** | Ryan Execute granted to Cursor for the bounded five-task package |
| `docs/plans/VERIFY-cg2-production-activation.md` | **Planning stub on this plan branch** | Cursor fills from mechanical Execute evidence before arc close |
| Production serving repository | Missing | Existing query surfaces still use legacy `ChromaStore` paths |
| Legacy fence/owner authority artifacts | Missing | No owner is cut over |
| Generation-aware doctor/parity | Missing | Current checks compare raw IDs |
| Source-observation promotion guard | Missing | CG-1 stale-generation guard exists; current-source guard does not |
| Source reconciliation | Missing | Current watchdog path has no startup/overflow/periodic manifest reconciliation contract |
| Authority-resolution/pin linearization | Missing | Proposed in architecture; no production reader or online GC exists |
| `docs/plans/formal/cg2/` | **Complete and mechanically checked on branch** | One TLA+ transition model, three exhaustive lock configurations, 123,281 generated / 38,134 distinct states, zero errors |
| Activation manifest/grant | Forbidden/not present | No production activation authorized |

Current production state remains legacy. `convmem doctor` is operationally
green with non-fatal legacy identity warnings, but that is not CG-2 readiness
evidence.

## 4. Completion state

| Milestone | Status | Blocking on |
|---|---|---|
| CG-1 substrate merged and accepted | **DONE** | — |
| ChatGPT research/advisory review | **PASS WITH DISPOSITIONS RECEIVED** | Four required dispositions incorporated on branch; does not replace designated lane reviews |
| Kiro design review at `1222b1e` | **PASS** | Delta confirmation recorded at the locked revision |
| Cursor feasibility review at `1222b1e` | **PASS WITH RISKS → PASS** | N1–N3 disposition and exact-SHA delta confirmation complete |
| Crush evidence/failure review at `1222b1e` | **PASS WITH RISKS → PASS** | N1–N3 disposition and exact-SHA delta confirmation complete |
| N1–N3 architecture addenda | **RESOLVED** | Preserved path-derived identity and explicit rename migration |
| Bounded formal authority model | **DONE — 3/3 TLC PASS** | 123,281 generated / 38,134 distinct states; zero errors |
| Ryan Architecture HITL | **DONE — 2026-08-15** | Locked `e680ce837653698a5be8b78ba02db2f880c40c63` as the execution baseline |
| Execution and VERIFY plans | **Kiro PASS — `6a808f1`** | Execute scope granted; implementation handoff is active |
| Implementation | **AUTHORIZED / NOT STARTED** | Cursor T1–T5 on a fresh implementation branch |
| Legacy-only serving-gateway soak | **NOT AUTHORIZED** | Implementation and verification evidence + exact production operation grant |
| First owner canary | **NOT AUTHORIZED** | All activation gates + separate named-owner grant |
| Broad rollout | **NOT AUTHORIZED** | Canary PASS |
| Online GC | **DEFERRED / OFF** | Separate read-pin, deletion, crash, and Chroma evidence |
| Legacy retirement | **NOT STARTED** | Intended owners migrated and accepted soak complete |

## 5. Your role

**Current Codex role:** Support Cursor’s implementation handoff and preserve the
separate grants for plan approval, implementation, gateway soak, owner activation,
and GC. Codex does not implement runtime code in this lane.

**Implementation lane:** Authorized for the exact T1–T5 package at `6a808f1`.
Cursor implements on a fresh branch; production operations remain separately
gated.

**Production state:** CG-1 is merged but hermetic; all production owners still
use legacy semantics. The architecture lock does not make CG-2 live.

**If a concrete architectural defect is discovered:** Stop plan authoring and
raise a targeted change request against the locked SHA. Do not silently revise
the architecture while drafting execution work.

## 6. What remains before live activation

1. Cursor implements T1–T5 on a fresh branch under the handoff.
2. Independent code/safety verification, copied-corpus rehearsal,
   implementation-to-model transition mapping, and pinned-Chroma operational evidence.
3. Separate grant for production legacy-only gateway soak.
4. Soak PASS and exact activation packet for one eligible owner.
5. Separate Ryan named-owner canary grant.
6. Canary, rollback, restart, parity, backlog, and performance evidence PASS.
7. Bounded owner rollout grants.
8. Separate GC sub-gate, then eventual legacy retirement.

## 7. Hard stops

| Stop | Owner | Blocks |
|---|---|---|
| Architecture lock | **DONE — Ryan, 2026-08-15** | Execution baseline `e680ce8` |
| Execute grant | **DONE — Ryan, 2026-08-15** | Cursor T1–T5 scope at plan tip `6a808f1` |
| Production gateway-soak grant | Ryan, exact operation | Any live read-path switch |
| Named-owner activation grant | Ryan, exact SHA/owner/state | First or later owner promotion |
| Zero serving bypasses | Architecture fitness gate | Any generational owner serving |
| Source/active stale checks | Promotion contract | Pointer publication |
| Source reconciliation freshness | Watch/reconciliation contract | Canary selection and legacy retirement |
| Authority-resolution linearization | Serving repository contract | Any mixed legacy/generation serving |
| Logical parity + provenance | Activation evidence | Canary selection |
| Chroma backlog/recovery/storage budgets | Operational evidence | Canary and batch expansion |
| GC sub-gate | Ryan after independent evidence | Automatic physical deletion |

No model may infer one grant from another. Merge is not activation.

## 8. Relationship to ConvMem

```text
CG-1 committed-generation substrate — merged, hermetic
             │
             ▼
CG-2 production activation — THIS ARC
             ├─ serving authority boundary
             ├─ production ingest/promotion guard
             ├─ logical drift/parity
             ├─ legacy migration and rollback
             └─ operational activation gates

Related but separate:
├─ Shadow Ledger Phase 0 — still disabled; no implied activation
├─ Chroma reconcile Tier L — closed GREEN foundation
├─ Complete-data backup v2 — active safety dependency
└─ JudgeBench — separate evaluation arc
```

The JSONL ledger remains authoritative for durable knowledge facts. Chroma is a
derived serving projection. CG-2 changes which physical Chroma rows may serve;
it does not make Chroma the fact ledger.

## 9. Key files

| Purpose | Path |
|---|---|
| Canonical architecture draft | `docs/plans/ARCHITECTURE-cg2-production-activation.md` |
| This arc brief | `docs/plans/STATUS-cg2-production-activation.md` |
| Cursor Execute handoff | `docs/inter-model/CODEX-2026-08-15-cg2-execute-cursor-handoff.md` |
| Bounded authority model and checked configurations | `docs/plans/formal/cg2/` |
| CG-1 implementation handoff | `docs/inter-model/HANDOFF-CG1-DEPENDABILITY-2026-08-10.md` |
| CG-1 reviewed closure | `docs/inter-model/CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md` |
| Read-boundary inventory | `tests/test_file_generation_read_path_inventory.py` |
| Current drift check | `doctor.py` |
| Current parity semantics | `projection_parity.py` |
| Production query path | `query.py` |
| Storage repository | `chroma_store.py` |
| Team workflow | `docs/inter-model/TEAM-CHARTER-2026-07-06.md` |

## 10. Update protocol

Keep this file as current-state orientation, not a diary:

1. Overwrite sections 3–6 when milestone state changes.
2. Move branch-only artifacts to `main` only after merge.
3. Delete completed “what remains” items rather than appending history.
4. Rewrite “Your role” for the next lane.
5. Keep one milestone-level Update Log line per update.
6. Put session narrative in Track A, not here.

### Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-15 | Cursor | Landed `1222b1e` feasibility and evidence reviews on plan branch with supersession banners to delta confirmation |
| 2026-08-15 | Ryan | Granted Execute to Cursor for the exact five-task CG-2 package at `6a808f1`; production soak, owner activation, and GC remain separate grants |
| 2026-08-15 | Kiro | Reviewed the execution and VERIFY planning package PASS at `6a808f1`; four implementation-lane observations are non-blocking |
| 2026-08-15 | OpenAI Codex | Drafted the five-task CG-2 execution plan and VERIFY planning stub from the Ryan-locked architecture; Kiro plan review is next |
| 2026-08-15 | Ryan | Locked the CG-2 architecture at `e680ce837653698a5be8b78ba02db2f880c40c63` after Kiro, Crush, and Cursor exact-SHA PASS confirmations; execution planning is next |
| 2026-08-15 | Cursor | Recorded triple exact-SHA delta PASS at `e680ce8`; Ryan Architecture HITL is next |
| 2026-08-14 | OpenAI Codex | Completed and mechanically checked the 12-property bounded authority model in three exhaustive configurations; lock-candidate delta review is next |
| 2026-08-14 | OpenAI Codex | Recorded all three review verdicts and resolved N1–N3 as bounded architecture mechanisms; formal model is the remaining pre-lock artifact |
| 2026-08-14 | OpenAI Codex | Incorporated advisory correctness dispositions for lost events, read/pin linearization, mixed-mode ANN acceptance, and request-scoped rename semantics |
| 2026-08-14 | OpenAI Codex | Created the CG-2 arc brief with architecture draft in review state; implementation and activation remain unauthorized |
