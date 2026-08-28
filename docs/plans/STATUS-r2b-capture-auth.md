# Arc Brief — R2b Capture Authorization

> Every model working on this arc must read this file at session start.

**Arc codename:** R2b Capture Authorization

## 1. What This Is For (product goal)

ConvMem answers questions from a local knowledge corpus. R2b is the
phase-scoped authorization boundary for producing one deterministic capture
from an export, processed state, and Chroma collection. The packet binds the
exact sources, controls, implementation revision, and output location; the
completion marker proves the resulting artifact set is complete.

The v1 boundary is implemented on main, but normal production ingestion is
mutable. The observed complete-identity stability window was insufficient for a
human-gated timing-only T4 to T6 transaction. V2 corrects that feasibility gap
with exclusive writer-gate quiescence while preserving exact source binding and
fail-closed authorization.

Done means: a reviewed and implemented v2 transaction obtains Ryan's separate
writer-quiescence preparation authority, Ryan ACCEPTs a fresh packet, Ryan
ACCEPT AND GRANTs one capture, the held gate spans snapshot through final source
recomputation, and independent VERIFY plus Ryan GATE close the arc.

## 2. System Design (how the pieces connect)

    exact-tip mutation-route coverage
      -> Ryan ACQUIRE WRITER QUIESCENCE AND PREPARE
      -> one continuously held exclusive writer-gate lease
      -> trusted complete source snapshot
      -> fresh packet -> Ryan ACCEPT -> ACCEPT AND GRANT
      -> one capture -> final source check -> marker -> close -> release

Quiescence means owning the existing exclusive writer gate. Compliant writers
remain running and wait at their normal shared gate. R2b does not stop, pause,
restart, signal, kill, reload, reconfigure, or otherwise control services or
processes.

V2 exact contract:

    r2b_contract_version = 2
    service_policy = "no_service_state_changes"
    source_quiescence_policy = "exclusive_writer_gate_v1"

The base R2b controls remain capture_id=run_id, canonical overlap, historical
spot n=20, and one attempt/max-retries 1. Trusted source identity includes
export SHA-256, processed state and digest, Chroma collection identity,
extracted unit count, sorted-ID hash, and canonical capture-slice SHA-256.

## 3. What Exists Right Now (file map)

### Merged v1 machinery on main

| File | Product role | State |
|---|---|---|
| eval_corpus/r2b_capture_auth.py | R2b schema, trusted binding, opaque capability, materialization | Complete v1; v2 extension not implemented |
| eval_corpus/r2b_capture_run.py | Capability-gated capture and last completion marker | Complete v1; v2 lease continuity not implemented |
| eval_corpus/capture.py | Shared canonical Chroma source identity/extraction | Complete v1 |
| scripts/eval_corpus_capture.py | Fixed-control capture CLI and exit mapping | Complete v1 |
| chroma_write_store.py | Existing shared/exclusive writer gate | Merged machinery; v2 lease integration not implemented |
| writer_census.py | Payload-free writer session census | Existing machinery; v2 zero-bypass binding not implemented |
| tests/r2b_hermetic.py and tests/test_eval_r2b_*.py | v1 authorization and marker tests | Complete v1 |

### Review documents on the current docs branch

| File | Product role | State |
|---|---|---|
| docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md | Normative v2 architecture amendment | Prepared for review |
| docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md | Bounded phases, duration evidence, and future transaction order | Prepared for review |
| docs/plans/VERIFY-r2b-v2-quiescence.md | Q0-Q9 implementation and transaction checks | Prepared; not run |
| docs/plans/ARCHITECTURE-r2b-capture-auth.md | Base v1 architecture, now linked to v2 amendment | Updated pointer |
| docs/plans/EXECUTION-2026-07-20-r2b-capture.md | Base v1 execution sequence | Updated pointer |
| docs/plans/VERIFY-r2b-capture.md | Base v1 verification sequence | Updated pointer |

The base v1 implementation was merged through PR #67 with the historical tree
proof recorded in the prior status. The current v2 docs branch is not main
and does not authorize implementation or execution.

### Does NOT Exist Yet

| What | Why not | Owner after review |
|---|---|---|
| Exact-tip zero-bypass coverage proof for v2 | Every route capable of mutating export, processed state, or Chroma must be accounted for | Cursor implementation, Copilot/Kiro review |
| Evidence-derived production duration values | Architecture defines separately bounded phases; 900 seconds is not ratified | Cursor evidence, Ryan acceptance |
| v2 quiescence authority and lease | Requires reviewed implementation and one-shot authority schema | Cursor after explicit Ryan authorization |
| Current v2 packet | Both 2026-07-21-r2b-capture-01/ and 2026-08-27-r2b-capture-02/ remain quarantined and unusable | Later named operator |
| Ryan packet ACCEPT / ACCEPT AND GRANT | Requires the future v2 chain and a fresh run | Ryan |
| Live v2 capture and VERIFY | Requires all preceding gates | Named operator, Kiro, Ryan |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Base v1 architecture and implementation | DONE on main | — |
| v1 timing-only T4 retry | CLOSED AS INFEASIBLE | Complete-identity stability window too short |
| V2 architecture amendment and bounded plans | IN REVIEW on docs branch | Ryan architecture review |
| V2 implementation and adversarial tests | NOT AUTHORIZED | Ryan implementation authorization |
| Exact-tip zero-bypass proof | NOT AVAILABLE | V2 implementation and same-tip review |
| Duration proposal and Ryan acceptance | NOT AVAILABLE | Representative scratch/runtime evidence |
| Fresh v2 packet | BLOCKED | V2 implementation, coverage proof, accepted bounds |
| Packet ACCEPT and ACCEPT AND GRANT | NOT STARTED | Fresh valid v2 packet and Ryan |
| Capture, mechanical VERIFY, Kiro sign-off, Ryan GATE | NOT STARTED | Ryan grant and capture |

The current gap is architecture review followed by implementation and evidence,
not another timing-only packet retry. No model may acquire production
quiescence, create a v2 packet, grant, or capture from this status.

## 5. Your Role (for the next model)

Review the v2 amendment, bounded execution plan, and Q0-Q9 verification plan.
Check that exclusive gate ownership is never described as service/process
control; that every mutation route is covered; that unknown, unattested,
uninspectable, stale-revision, PID-reused, alternate-lock, and bypass-capable
routes are hard HOLDs; and that duration values remain unratified until Ryan
separately accepts evidence-derived values.

After review, wait for explicit implementation authorization. Do not create a
packet, sidecar, capture directory, or grant. Do not stop or signal services,
mutate sources, activate CG-2 or Recovery Authority, clean evidence, or reuse
either quarantined run.

## 6. What Remains Before Live v2

- [ ] Ryan reviews the v2 amendment and bounded execution/VERIFY plans
- [ ] Cursor receives explicit authorization and implements v2
- [ ] Exact-tip route inventory and runtime census prove zero bypass
- [ ] Scratch/runtime evidence proposes acquisition, HITL, capture, release/close, and total bounds
- [ ] Ryan separately accepts the concrete duration values
- [ ] Copilot and Kiro issue same-tip implementation verdicts
- [ ] A fresh run obtains the first authority and held gate
- [ ] Trusted snapshot and filled packet are prepared; Ryan ACCEPTs
- [ ] Existing materialization and Ryan ACCEPT AND GRANT succeed
- [ ] One capture runs with fixed controls into an absent target
- [ ] Final source check, last marker, close/release, mechanical VERIFY, Kiro sign-off, and Ryan GATE complete
- [ ] Stop before B-Accept; that requires a new architecture and grant

## 7. Hard Stops

| Stop | Gate owner | Effect |
|---|---|---|
| Architecture review | Ryan | No implementation or live authority from this docs branch |
| Implementation authorization | Ryan | No Cursor v2 implementation before explicit authorization |
| Zero-bypass proof | Trusted v2 code/review | Any unknown or bypass-capable route is HOLD; never remove it by service control |
| Duration acceptance | Ryan | No live v2 grant before evidence-derived concrete values are accepted |
| Restic gate | Operational precondition | No trusted snapshot or eval-root write unless PASS |
| Packet ACCEPT | Ryan | No sidecar/materialization/capture grant |
| ACCEPT AND GRANT | Ryan | No capture |
| Existing one-hour freshness | Trusted binder/materializer | Stale/future/naive packet refuses; no in-place extension |
| Quarantined runs | Operator protocol | Never reuse, repair, upgrade, or grant from 2026-07-21-r2b-capture-01/ or 2026-08-27-r2b-capture-02/ |
| No-service-state policy | Architecture | No start/stop/restart, signal/kill, reload, config mutation, or source mutation |
| Marker authority | Capture/VERIFY | No valid last marker means no structurally complete capture |
| Failure/replay | Trusted implementation | Timeout, crash, drift, replay, or partial output permanently closes the run |

## 8. Relationship to ConvMem

    R2b v2 — source authority and one capture
      -> corpus package / knowledge_units
      -> downstream retrieval and embedding evaluation
      -> separate JudgeBench and Gate 2 work

CG-2 and Recovery Authority are independent authority domains. V2 must
enumerate their potentially mutating routes for coverage but does not activate,
pause, roll back, restore, or mutate either domain. B-Accept and promotion are
out of scope.

## 9. Key Design Files

| Purpose | Path |
|---|---|
| Normative v2 architecture | docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md |
| Bounded v2 execution | docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md |
| V2 verification | docs/plans/VERIFY-r2b-v2-quiescence.md |
| Base architecture | docs/plans/ARCHITECTURE-r2b-capture-auth.md |
| Base execution | docs/plans/EXECUTION-2026-07-20-r2b-capture.md |
| Base verification | docs/plans/VERIFY-r2b-capture.md |
| Current arc brief | docs/plans/STATUS-r2b-capture-auth.md |

## 10. How to Update This Brief (departure protocol)

Keep this file as a current-state snapshot, not a session diary. Update the
file map, completion state, next-model role, and remaining gates when a
milestone changes. Preserve the quarantine and authority boundaries. Put
session narrative in Track A session ingest rather than here. Keep one
milestone-level line in the update log below.

### Update Log

| Date | Who | Milestone change |
|---|---|---|
| 2026-08-09 | Crush | Initial arc brief; v1 code on main; prior draft quarantined |
| 2026-08-27 | Codex | Added the accepted-in-principle v2 exclusive writer-gate correction and bounded execution/VERIFY plans; implementation and live execution remain unauthorized |
