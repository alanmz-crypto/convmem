# STATUS — CG-2 production activation

**Last updated:** 2026-08-14
**Arc:** CG-2 production activation of committed generations
**State:** Reviews complete; N1–N3 architecture addenda resolved on planning branch; formal model in progress; no implementation or activation authority

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
| `docs/plans/ARCHITECTURE-cg2-production-activation.md` | **Draft on `plan/2026-08-14-cg2-production-activation`** | Proposed production authority, migration, health, and rollout design |
| CG-2 execution plan | Missing by design | Written only after architecture lock |
| CG-2 VERIFY plan/results | Missing by design | Authored during execution planning; no results exist |
| Production serving repository | Missing | Existing query surfaces still use legacy `ChromaStore` paths |
| Legacy fence/owner authority artifacts | Missing | No owner is cut over |
| Generation-aware doctor/parity | Missing | Current checks compare raw IDs |
| Source-observation promotion guard | Missing | CG-1 stale-generation guard exists; current-source guard does not |
| Source reconciliation | Missing | Current watchdog path has no startup/overflow/periodic manifest reconciliation contract |
| Authority-resolution/pin linearization | Missing | Proposed in architecture; no production reader or online GC exists |
| Formal authority model | Missing / Codex lane active | Required before reviewer delta confirmation and Ryan Architecture HITL lock |
| Activation manifest/grant | Forbidden/not present | No production activation authorized |

Current production state remains legacy. `convmem doctor` is operationally
green with non-fatal legacy identity warnings, but that is not CG-2 readiness
evidence.

## 4. Completion state

| Milestone | Status | Blocking on |
|---|---|---|
| CG-1 substrate merged and accepted | **DONE** | — |
| ChatGPT research/advisory review | **PASS WITH DISPOSITIONS RECEIVED** | Four required dispositions incorporated on branch; does not replace designated lane reviews |
| Kiro design review at `1222b1e` | **PASS** | Delta confirmation after model revision |
| Cursor feasibility review at `1222b1e` | **PASS WITH RISKS** | N1–N3 disposition + delta confirmation |
| Crush evidence/failure review at `1222b1e` | **PASS WITH RISKS** | N1–N3 disposition + delta confirmation |
| N1–N3 architecture addenda | **RESOLVED ON BRANCH** | Formal model and same-revision reviewer confirmation |
| Ryan Architecture HITL | **NOT DONE** | Formal model + Kiro/Crush/Cursor delta confirmation on one exact revision |
| Execution and VERIFY plans | **NOT STARTED** | Architecture lock |
| Implementation | **NOT AUTHORIZED** | Execution plan review + Ryan Execute grant |
| Legacy-only serving-gateway soak | **NOT AUTHORIZED** | Implementation and verification evidence + exact production operation grant |
| First owner canary | **NOT AUTHORIZED** | All activation gates + separate named-owner grant |
| Broad rollout | **NOT AUTHORIZED** | Canary PASS |
| Online GC | **DEFERRED / OFF** | Separate read-pin, deletion, crash, and Chroma evidence |
| Legacy retirement | **NOT STARTED** | Intended owners migrated and accepted soak complete |

## 5. Your role

**If Ryan sent you as Codex now:** Finish the bounded formal authority model
against the N1–N3-resolved architecture. Check all 12 required properties,
update this current-state brief and `LATEST.md`, and push one exact lock-candidate
revision. Do not write an execution plan or implementation.

**If Ryan sent you for delta confirmation:** Review only the N1–N3 addenda and
formal model against the new exact SHA. Confirm or reject whether they preserve
your existing verdict; do not implement.

**If Ryan sent you to revise architecture:** Change only planning/status
artifacts on the plan branch, reconcile every material reviewer finding, and
produce a new review SHA. Do not write an execution plan until the architecture
is locked.

**If Ryan sent you to implement:** Stop. Implementation is not authorized.

**If Ryan asks whether CG-2 is live:** It is not. CG-1 is merged but hermetic;
all production owners still use legacy semantics.

## 6. What remains before live activation

1. Codex authors and mechanically checks the bounded formal authority model
   against the N1–N3-resolved architecture.
2. Kiro, Crush, and Cursor quick-confirm the same architecture/model revision.
3. Ryan Architecture HITL lock.
4. Codex authors execution and VERIFY plans only after that separate lock.
5. Plan review and separate Ryan Execute grant.
6. Cursor implements global serving boundary with all owners legacy.
7. Independent code/safety verification, copied-corpus rehearsal,
   implementation-to-model transition mapping, and pinned-Chroma operational evidence.
8. Separate grant for production legacy-only gateway soak.
9. Soak PASS and exact activation packet for one eligible owner.
10. Separate Ryan named-owner canary grant.
11. Canary, rollback, restart, parity, backlog, and performance evidence PASS.
12. Bounded owner rollout grants.
13. Separate GC sub-gate, then eventual legacy retirement.

## 7. Hard stops

| Stop | Owner | Blocks |
|---|---|---|
| Architecture lock | Ryan after same-revision reviews/model | Execution planning and implementation |
| Execute grant | Ryan | Code/runtime/config changes |
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
| 2026-08-14 | OpenAI Codex | Recorded all three review verdicts and resolved N1–N3 as bounded architecture mechanisms; formal model is the remaining pre-lock artifact |
| 2026-08-14 | OpenAI Codex | Incorporated advisory correctness dispositions for lost events, read/pin linearization, mixed-mode ANN acceptance, and request-scoped rename semantics |
| 2026-08-14 | OpenAI Codex | Created the CG-2 arc brief with architecture draft in review state; implementation and activation remain unauthorized |
