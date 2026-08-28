# Verify Plan — R2b v2 writer-gate quiescence

**Arc:** R2b Capture Authorization
**Date:** 2026-08-27
**Status:** Planning only; not executed
**Authority:** Independent mechanical verification, later Copilot/Kiro review, and Ryan HITL; no live grant

**Normative amendment:** ARCHITECTURE-r2b-mutable-source-quiescence-v2.md
**Bounded execution plan:** EXECUTION-2026-08-27-r2b-v2-quiescence.md
**Base verification plan:** VERIFY-r2b-capture.md

## 1. Verification contract

Every later v2 check receives PASS, FAIL, HOLD, or NOT RUN plus one line of
evidence. HOLD is the required result for unknown, unavailable, stale, or
ambiguous authority evidence. A missing check is not a PASS.

This plan verifies a later implementation and one later authorized transaction;
it does not authorize implementation, writer-gate acquisition, packet creation,
sidecar creation, capture, service/process control, source mutation, cleanup,
or reuse of a prior run.

The exact v2 constants are:

    r2b_contract_version = 2
    service_policy = "no_service_state_changes"
    source_quiescence_policy = "exclusive_writer_gate_v1"
    writer_gate_path = ~/.local/share/convmem/locks/chroma_writer_gate.lock
    writer_gate_protocol = 1 (existing gate protocol, bound by trusted code)

The base R2b checks remain mandatory: Restic PASS, trusted complete source
identity, canonical paths/containment, absent target, packet freshness, fixed
controls, opaque capability, last marker, and quarantine semantics.

## 2. Q0 — review, revision, and scope gate

| ID | Check | PASS evidence |
|---|---|---|
| Q0a | Normative v2 amendment and execution plan are reviewed | Ryan architecture review reference |
| Q0b | Implementation is the exact reviewed tip on main | SHA, ancestry, tree proof |
| Q0c | Copilot and Kiro verdicts identify the same implementation tip | Same-SHA written verdicts |
| Q0d | Ryan separately accepted concrete duration values and evidence | Bound proposal, evidence, explicit acceptance |
| Q0e | No implementation/live authority is inferred from docs approval or merge | Scope statement |
| Q0f | The old quarantined runs remain untouched and unbound | Read-only path/hash evidence |

Any Q0 failure blocks the later transaction.

## 3. Q1 — zero-bypass exact-tip coverage

| ID | Check | PASS evidence |
|---|---|---|
| Q1a | Trusted code generates a complete mutation-route inventory at the exact tip | Manifest SHA and revision |
| Q1b | Inventory includes watch/F0, refine, monitor/reconciliation, manual writers, CG-2, Recovery Authority, and other production routes | Route matrix with mutation surfaces |
| Q1c | Every included route uses the same shared gate path and protocol | Route-level gate identity/protocol evidence |
| Q1d | Routes excluded from the bound source have trusted, revision-bound exclusion reasons | Exclusion records |
| Q1e | Runtime census binds PID start time, executable/entrypoint, revision, protocol, gate, and source surface | Census records |
| Q1f | Unknown, unattested, uninspectable, stale-revision, PID-reused, alternate-lock, and bypass sets are empty | Explicit empty sets |
| Q1g | Missing /proc or equivalent inspection fails closed | Negative test/result |
| Q1h | Known service-unit/command signatures are not treated as complete proof by themselves | Review/test evidence |

Any Q1 failure is a hard HOLD before a source snapshot is authoritative. The
operator must not stop, signal, kill, reload, or otherwise control the route.

## 4. Q2 — first authority and lease integrity

| ID | Check | PASS evidence |
|---|---|---|
| Q2a | First authority is named ACQUIRE WRITER QUIESCENCE AND PREPARE | Authority body |
| Q2b | Authority carries exact v2 contract and no-service-state policy | Field dump/body digest |
| Q2c | Authority prohibits service/process control, source/config mutation, backup restore, CG-2/Recovery mutation, capture, and cleanup | Full prohibited list |
| Q2d | Authority binds exact run, revision, gate identity/protocol, coverage/census digests, and duration policy | Canonical body |
| Q2e | Authority is one-shot and replay-protected | Nonce/consumption test |
| Q2f | Lease handle is opaque and non-caller-constructible | Forgery/reflection tests |
| Q2g | Lease has monotonic start, phase bounds, and hard transaction deadline | Lease evidence |
| Q2h | A lease cannot be extended, transferred, serialized for reuse, or turned into a boolean | Negative tests |

## 5. Q3 — gate acquisition and source authority

| ID | Check | PASS evidence |
|---|---|---|
| Q3a | Existing exclusive writer gate is acquired by trusted code at the exact canonical identity | Gate inode/path/protocol evidence |
| Q3b | Compliant writers remain running and wait at their normal shared gate | Writer behavior test; no service-state diff |
| Q3c | Exact pre-quiescence service/process, PID/start-time, executable, revision, and gate state are durably recorded | Pre-state observation |
| Q3d | No service start/stop/restart, process signal/kill, daemon reload, config mutation, or source mutation occurs | Scoped audit evidence |
| Q3e | Open evidence is durable and written while the lease is held | Open record/hash and ordering proof |
| Q3f | Coverage/census is revalidated at the gate boundary | Matching digests/revision |
| Q3g | Trusted snapshot is computed only after Q1 and while the same lease is held | Call trace/order evidence |
| Q3h | Snapshot contains export SHA, processed state/digest, Chroma collection identity, extracted count, sorted-ID hash, and canonical slice SHA | Snapshot report |
| Q3i | Stable-ID document/metadata changes and collection-ID changes are detected | Mutation tests |

The gate lock alone is not Q3 PASS. Q1 and Q3e are prerequisites.

## 6. Q4 — duration policy and freshness

| ID | Check | PASS evidence |
|---|---|---|
| Q4a | Acquisition, HITL response/reservation, capture, release/close, and total bounds are separately represented | Authority/packet fields |
| Q4b | Proposed bounds use representative scratch/runtime evidence with workload identity and safety margin | Evidence package |
| Q4c | Ryan separately accepted the concrete values before live grant | Explicit acceptance |
| Q4d | No architecture or implementation default silently ratifies 900 seconds | Code/docs search and test |
| Q4e | One monotonic hard deadline governs all phase checks | Clock/test trace |
| Q4f | Expiry releases/closes permanently and cannot extend or retry the run | Timeout tests |
| Q4g | Existing one-hour packet freshness is checked independently at ACCEPT, bind, and materialization | Timestamp evidence |
| Q4h | Effective deadline is the earliest applicable freshness/transaction limit | Boundary test |

## 7. Q5 — packet preparation and authority separation

| ID | Check | PASS evidence |
|---|---|---|
| Q5a | Fresh safe run ID and exact auth/capture roots are used | Run/path evidence |
| Q5b | capture.json binds exact implementation revision, absolute source/target paths, full trusted snapshot, policy fields, fixed controls, prohibitions, duration values, quiescence evidence, and full future argv | Packet field dump |
| Q5c | Paths have lexical equality, containment, and no prohibited symlink components | Trusted path proof |
| Q5d | capture_dir is absent before materialization | lstat/containment evidence |
| Q5e | Quiescence evidence is bound into the packet without becoming a caller-provided source of truth | Body digest/call trace |
| Q5f | Sidecar is absent before Ryan ACCEPT | Filesystem evidence |
| Q5g | Packet ACCEPT is distinct from quiescence authority and ACCEPT AND GRANT | Authority event log |
| Q5h | Quarantined prior runs cannot be rebound or upgraded | Negative test |

## 8. Q6 — pre-grant continuity

| ID | Check | PASS evidence |
|---|---|---|
| Q6a | The same opaque lease spans snapshot, packet ACCEPT, binder, and materialization | Lease identity/order trace |
| Q6b | Exact coverage/census/revision/gate identity remain valid | Revalidation evidence |
| Q6c | Trusted current snapshot still equals the approved snapshot | Full component comparison |
| Q6d | Approved body digest, sidecar relationship, timestamp, and paths pass | Binder/materializer evidence |
| Q6e | Target remains absent until capability materialization | Filesystem/order trace |
| Q6f | Exact fixed controls remain capture_id=run_id, canonical overlap, spot n=20, one attempt | Grant/body/report fields |
| Q6g | Exact argv matches the packet and contains no service/process or correction command | Argv digest/excerpt |
| Q6h | Existing ACCEPT AND GRANT is the only capture grant | Ryan authority evidence |

## 9. Q7 — capture, final source check, and marker

| ID | Check | PASS evidence |
|---|---|---|
| Q7a | Capture begins only after grant and capability materialization | Trace/order proof |
| Q7b | Exactly one attempt runs; no same-directory retry | Report and negative test |
| Q7c | Export/processed/Chroma artifacts match the approved source identity | Artifact digests |
| Q7d | Final trusted source recomputation equals the approved snapshot before marker | Final snapshot evidence |
| Q7e | Drift, timeout, exception, or FAILED outcome produces no completion marker | Negative-path evidence |
| Q7f | Valid marker is written last and atomically; no later capture-directory write occurs | Instrumented order + mtime/inventory |
| Q7g | Marker/report/package/fingerprint/unit-count/auth/source bindings agree | Cross-check |
| Q7h | Processed-present/absent inventory is exact | Conditional inventory evidence |

The existing base VERIFY V0–V6 artifact checks remain in force; Q7 supplements
them with lease continuity and source-quiescence evidence.

## 10. Q8 — close, release, crash, and replay

| ID | Check | PASS evidence |
|---|---|---|
| Q8a | Durable close evidence is written before lease release | Ordering trace |
| Q8b | Close binds terminal state, final source result, marker/failure result, deadline status, and release intent | Close record/hash |
| Q8c | Post-release observation matches the authorized pre-quiescence service/process state except for lease release | State digest and gate evidence |
| Q8d | Successful close releases the exclusive lease without changing service state | Gate and service-state evidence |
| Q8e | Acquisition, HITL, capture, release, and close timeouts are terminal | Failure matrix |
| Q8f | Crash before close cannot resume, extend, regrant, or reuse the run | Crash/restart test |
| Q8g | PID reuse, stale capability, replayed authority, and duplicate nonce refuse | Negative tests |
| Q8h | Partial output is quarantined and never cleaned, overwritten, or resumed by R2b | Path/operator evidence |
| Q8i | Old runs remain quarantined and untouched | Read-only evidence |

## 11. Q9 — prohibited-operation and cross-authority isolation

| ID | Check | PASS evidence |
|---|---|---|
| Q9a | No service or process control API is reachable from the v2 authority | Static/runtime guard |
| Q9b | No watch/refine behavior, source, export, processed, Chroma, or config mutation is performed by R2b | Scoped before/after evidence |
| Q9c | No backup restore occurs; Restic PASS remains a precondition only | Audit evidence |
| Q9d | CG-2 is not activated or mutated | Authority/audit evidence |
| Q9e | Recovery Authority is not activated or mutated | Authority/audit evidence |
| Q9f | No approval sidecar or capture directory appears before its HITL gates | Filesystem evidence |
| Q9g | No cleanup of prior evidence occurs | Path/audit evidence |

## 12. Required implementation tests

The later implementation PR must include isolated tests for:

- exact-tip coverage completeness and missing-route refusal;
- unknown, unattested, uninspectable, stale-revision, PID-reused,
  alternate-lock, and bypass-capable route refusal;
- shared/exclusive gate identity and protocol mismatch;
- authority precedence, nonce replay, forged lease/capability, and stale body;
- lease continuity across human waiting, binder, materialization, capture, and
  final recomputation;
- monotonic phase/deadline expiry with no extension or same-run retry;
- crash at every transaction state and close-before-release ordering;
- source content, ID-set, superseded-state, processed-state, and collection-ID
  drift;
- fixed controls and exact argv;
- path containment, lexical equality, symlink components, and absent target;
- marker-last atomic write and no marker on all failure paths; and
- rejection of every prohibited service/process/source/config/backup/CG-2/
  Recovery operation.

## 13. Later evidence record

    VERIFY-r2b-v2-quiescence
    implementation_tip: <exact SHA>
    run_id: <fresh run ID or NOT_RUN>
    timestamp: <timezone-aware ISO-8601>
    Q0: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q1: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q2: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q3: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q4: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q5: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q6: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q7: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q8: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Q9: PASS|FAIL|HOLD|NOT_RUN — <evidence>
    Mechanical: PASS|FAIL|HOLD|NOT_RUN
    Copilot: PASS|FAIL|NOT_RUN — exact tip <SHA>
    Kiro: PASS|FAIL|NOT_RUN — exact tip <SHA>
    Ryan duration acceptance: ACCEPT|NOT_RUN
    Ryan packet ACCEPT: ACCEPT|NOT_RUN
    Ryan ACCEPT AND GRANT: ACCEPT|NOT_RUN
    Ryan GATE: ACCEPT|REJECT|NOT_RUN

No later VERIFY result may claim a stability interval longer than directly
observed, or treat a passing backup gate/count-only observation as complete
source identity.
