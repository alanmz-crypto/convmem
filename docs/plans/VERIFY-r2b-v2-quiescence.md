# VERIFY Plan — R2b v2 writer-gate quiescence

**Arc:** R2b Capture Authorization
**Date:** 2026-08-27
**Status:** Planning only; NOT RUN
**Architecture:** [`ARCHITECTURE-r2b-mutable-source-quiescence-v2.md`](ARCHITECTURE-r2b-mutable-source-quiescence-v2.md)
**Execution:** [`EXECUTION-2026-08-27-r2b-v2-quiescence.md`](EXECUTION-2026-08-27-r2b-v2-quiescence.md)
**Base VERIFY:** [`VERIFY-r2b-capture.md`](VERIFY-r2b-capture.md)

This matrix verifies a later implementation and one later authorized
transaction. It authorizes neither. Every row receives `PASS`, `FAIL`,
`HOLD`, or `NOT RUN` plus one evidence line. Missing evidence is not PASS.

## V0 — scope, revision, and authority

| ID | Check | Required evidence |
|---|---|---|
| V0a | Architecture, execution, and VERIFY are the same reviewed v2 document set | Ryan review reference and document hashes |
| V0b | Implementation is the exact reviewed `main` revision | SHA, ancestry, and tree proof |
| V0c | Copilot audit and Kiro verdicts name that same revision | Written same-tip verdicts |
| V0d | Docs approval/merge did not grant implementation or live operation | Scope statement |
| V0e | Old v1 manifests remain historical; `2026-07-21-r2b-capture-01` and `2026-08-27-r2b-capture-02` are untouched and unusable | Read-only paths/hashes |

## V1 — contract and policy separation

| ID | Check | Required evidence |
|---|---|---|
| V1a | New packet emits `r2b_contract_version: 2` | Packet/schema output |
| V1b | New packet has exact `service_policy: "no_service_state_changes"` and `source_quiescence_policy: "exclusive_writer_gate_v1"` | Packet field dump |
| V1c | `authorization_phase`, `execution_mode`, `operations`, exact paths, sidecar, source snapshot, and v1 fixed controls remain enforced | Schema tests and validator output |
| V1d | Historical v1 value/manifest is not upgraded or reinterpreted | Migration test and preserved fixture |
| V1e | No concrete production duration, including 900 seconds, is silently ratified | Static search and policy test |
| V1f | Existing one-hour freshness bound remains independently checked at ACCEPT, bind, and materialization | Timestamp evidence |

## V2 — exact-tip zero-bypass coverage

| ID | Check | Required evidence |
|---|---|---|
| V2a | Trusted inventory is derived from the exact implementation tip | Inventory digest and revision |
| V2b | Inventory includes watch/F0, refine, monitor/reconciliation, manual production entrypoints, CG-2/D4 mutation and reconciliation surfaces, Recovery Authority, and every other export/processed/Chroma writer | Route matrix with mutation surfaces |
| V2c | Every included route binds the same writer-gate path and protocol | Per-route gate evidence |
| V2d | Excluded routes have trusted, revision-bound reasons; “not observed” is rejected | Exclusion evidence |
| V2e | Runtime census binds PID, process start time, executable, entrypoint, code revision, gate identity/protocol, and mutable surfaces | Census records |
| V2f | Unknown, stale-revision, unattested, uninspectable, PID-reused, alternate-gate, and bypass-capable sets are empty | Explicit empty-set report |
| V2g | Missing process inspection or unknown writer signature produces hard HOLD | Negative tests |
| V2h | A gate lock without complete coverage proof cannot establish source authority | Negative test/review |

## V3 — authority and live lease

| ID | Check | Required evidence |
|---|---|---|
| V3a | First authority is exactly **ACQUIRE WRITER QUIESCENCE AND PREPARE** and is one-shot | Authority record and transition test |
| V3b | Preparation does not authorize packet ACCEPT, capture, grant, service control, source mutation, backup restore, CG-2, Recovery Authority, or cleanup | Full prohibited list |
| V3c | Opaque capability binds run ID, active grant digest, gate path/inode/protocol, coordinator PID/start time, implementation revision, writer-coverage digest, open-evidence digest, monotonic deadline, and live lock ownership | Capability inspection through trusted verifier; no JSON reconstruction |
| V3d | Lease also binds authority digest, monotonic start, phase bounds, source paths, and source identity | Capability/evidence cross-check |
| V3e | Capability cannot be forged, copied, serialized, replayed, transferred, extended, reacquired, or reduced to a boolean | Adversarial tests |
| V3f | Replaced/alternate lock inode and lost ownership fail closed | Lock identity tests |

## V4 — quiescence, source snapshot, and packet

| ID | Check | Required evidence |
|---|---|---|
| V4a | Services/processes remain running and only compliant writers wait on the shared protocol | Before/after observation; no service-state diff |
| V4b | `quiescence-start.json` records fresh run, policy, exact revision, paths, target absence, and preconditions | Hash and field evidence |
| V4c | `quiescence-open.json` is durable while the same exclusive lease is held and binds gate, coordinator, coverage/census, deadline, and pre-state | Ordering proof and digest |
| V4d | Trusted snapshot is computed only after coverage proof and while that lease remains live | Call trace/order evidence |
| V4e | Snapshot binds export bytes, processed presence/bytes, collection name/ID, full Chroma extracted set, documents, and superseded state | Recomputed digest |
| V4f | Packet binds complete snapshot, open-evidence digest, gate identity, coverage, revision, deadline, exact paths/argv, and fixed controls | Packet digest/field dump |
| V4g | Sidecar and capture directory are absent before their respective gates | Filesystem/order evidence |
| V4h | Snapshot, packet, or source drift requires a fresh run; it is never repaired in place | Negative test |

## V5 — HITL, materialization, and remaining budget

| ID | Check | Required evidence |
|---|---|---|
| V5a | Ryan packet **ACCEPT** is distinct from quiescence preparation | Authority event chain |
| V5b | The same live lease spans snapshot, packet ACCEPT, binder, and materialization | Lease identity/order trace |
| V5c | Materialization rechecks body/sidecar, source identity, paths, symlinks, target absence, coverage, gate inode, deadline, and exact revision | Trusted trace |
| V5d | Acquisition, HITL reservation, capture, release/close, and hard transaction bounds are separately represented | Policy fields |
| V5e | Proposed values are supported by representative scratch evidence and separately accepted by Ryan; no 900-second ratification | Benchmark evidence and Ryan decision |
| V5f | Sufficient remaining budget is proven before **ACCEPT AND GRANT** | Boundary calculation |
| V5g | Expiry is terminal and cannot extend, re-ACCEPT, regrant, or retry the run | Timeout tests |

## V6 — capture and marker

| ID | Check | Required evidence |
|---|---|---|
| V6a | Ryan **ACCEPT AND GRANT** is the only capture grant and is bound to the live lease and exact packet | Grant digest and capability trace |
| V6b | Exactly one capture runs with `capture_id = run_id`, canonical overlap, spot `n = 20`, and one attempt | argv/report evidence |
| V6c | No service/process control, source/config mutation, backup restore, reconciliation workaround, generation operation, or cleanup occurs | Scoped audit |
| V6d | Final trusted source recomputation occurs before marker publication and equals the approved snapshot | Full comparison |
| V6e | `corpus_package_manifest.json` is last and atomic; it validates exact inventory and every required non-marker hash | Instrumented write order and marker validation |
| V6f | `capture_report.json` is required and agrees with the marker; report status alone is not completeness authority | Cross-check |
| V6g | Complete/unresolved may publish a valid marker; failed/drift/exception/timeout/crash may not | Positive and negative paths |

## V7 — close, release, and failure behavior

| ID | Check | Required evidence |
|---|---|---|
| V7a | `quiescence-close.json` is durable before lock release and includes terminal state, final source result, marker/failure result, deadline status, and release intent/result | Ordering proof |
| V7b | Post-release observation matches pre-quiescence service/process state except lease release | State digest |
| V7c | Gate-unavailable, unknown writer, snapshot, packet, Ryan expiry, binder, pre-target capture, post-target capture, source mutation, crash, missing close, replay, PID reuse, and inode replacement each fail closed as specified | Failure matrix evidence |
| V7d | Partial output is quarantined and never cleaned, overwritten, resumed, or reused | Path and negative evidence |
| V7e | Every retry has a new run ID, authority, lease, snapshot, packet, ACCEPT, grant, and absent target | New-chain evidence or N/A |

## V8 — independent review and close

| ID | Check | Required evidence |
|---|---|---|
| V8a | Mechanical result covers V0–V7 with no unexplained HOLD/FAIL | Filled matrix |
| V8b | Copilot audit and Kiro review name the same implementation revision and inspect the same packet/evidence hashes | Written verdicts |
| V8c | Kiro confirms no corrective mutation, cleanup, service control, grant, or reinterpretation occurred during review | Explicit statement |
| V8d | Ryan separately accepts duration values, activation, packet ACCEPT, and ACCEPT AND GRANT as applicable | Exact authority records |
| V8e | Ryan records the final GATE only after all required evidence is complete | GATE record |

## Later evidence record

```text
VERIFY-r2b-v2-quiescence
implementation_tip: <exact SHA>
run_id: <fresh run ID or NOT_RUN>
V0..V8: PASS|FAIL|HOLD|NOT_RUN — <one evidence line each>
Mechanical: PASS|FAIL|HOLD|NOT_RUN
Copilot: PASS|FAIL|NOT_RUN — exact tip <SHA>
Kiro: PASS|FAIL|NOT_RUN — exact tip <SHA>
Ryan duration acceptance: ACCEPT|NOT_RUN
Ryan packet ACCEPT: ACCEPT|NOT_RUN
Ryan ACCEPT AND GRANT: ACCEPT|NOT_RUN
Ryan GATE: ACCEPT|REJECT|NOT_RUN
```

**TL;DR:** Verification remains NOT RUN and will require same-tip code review,
zero-bypass proof, continuous lease evidence, independent source identity,
marker-last capture evidence, fail-closed failure paths, and separate Ryan
duration and grant decisions.
