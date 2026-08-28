# Execution Plan — R2b v2 writer-gate quiescence

**Arc:** R2b Capture Authorization  
**Date:** 2026-08-27  
**Status:** Planning only; no implementation, gate acquisition, packet, grant,
capture, cleanup, or live benchmark  
**Base:** D4 `89a7e045b130f005f57539478d9a180cbea905df` on `origin/main`  
**Architecture:** [`ARCHITECTURE-r2b-mutable-source-quiescence-v2.md`](ARCHITECTURE-r2b-mutable-source-quiescence-v2.md)  
**VERIFY:** [`VERIFY-r2b-v2-quiescence.md`](VERIFY-r2b-v2-quiescence.md)

## 1. Execution contract

This plan makes the accepted v2 architecture implementable later. It does not
authorize any runtime action. It is not permission to acquire the writer gate,
change service/process state, create a packet or sidecar, create a capture
directory, mutate source/Chroma, run a production benchmark, clean evidence, or
issue a grant.

The later transaction is one linear, fail-closed chain:

```text
fresh run
→ ACQUIRE WRITER QUIESCENCE AND PREPARE
→ exact-tip zero-bypass proof
→ exclusive lease held
→ trusted snapshot + draft packet
→ Ryan ACCEPT
→ materialization/binder validation
→ Ryan ACCEPT AND GRANT
→ exactly one capture
→ final trusted source recomputation
→ close evidence
→ release gate
→ VERIFY / Ryan GATE
```

The lease is never released between these steps. A pre-quiescence authority
does not authorize capture.

## 2. Policy ledger

| Kind | Required treatment |
|---|---|
| Inherited v1 | Keep phase-scoped R2b schema, trusted export/processed/Chroma snapshot, canonical paths, exact fixed controls, capability/materializer, marker-last, and quarantine semantics |
| Mechanically implied | Use the existing `~/.local/share/convmem/locks/chroma_writer_gate.lock` identity and protocol 1; compliant writers keep running under shared ownership and R2b takes exclusive ownership |
| New v2 | Emit `r2b_contract_version: 2`, `service_policy: "no_service_state_changes"`, `source_quiescence_policy: "exclusive_writer_gate_v1"`; require continuous live capability, exact-tip coverage, open/close evidence, and fail-closed deadlines |
| Ryan-owned pending | All concrete duration values, benchmark acceptance, activation of v2 tooling, refusal activation for new v1 live execution, and every live packet/lease/grant |

No production duration is specified in this plan. The existing one-hour source
snapshot freshness rule remains an inherited outer bound pending any separate
normative review. The value 900 seconds is not a default or ratified proposal.

## 3. Cursor implementation slices (future, separately authorized)

Each slice must land with isolated tests and preserve the v1 historical path.
Cursor must not start these slices until Ryan authorizes implementation.

| Slice | Deliverable | Required proof |
|---|---|---|
| I1 — contract/state | Versioned v2 schema and explicit authority state machine; v1 manifests remain readable as history | Exact policy values; no v1 upgrade/reinterpretation; invalid transition tests |
| I2 — live lease | Opaque process-local lease bound to run, authority/grant digest, path/inode/protocol, coordinator PID/start, revision, coverage/open digests, monotonic deadline, and live ownership | Forgery, serialization, replay, PID reuse, inode replacement, extension, and crash refusal |
| I3 — coverage | Exact-tip route inventory plus runtime census for all export/processed/Chroma mutation routes | Watch/F0, refine, monitor/reconciliation, manual, CG-2/D4, Recovery Authority, and unknown/bypass hard-HOLD tests |
| I4 — source/packet | Snapshot and packet creation under the held lease; bind packet to open evidence and exact paths/argv | Shared canonical Chroma identity; content/metadata drift; sidecar absent before ACCEPT |
| I5 — deadlines | Absolute monotonic transaction deadline and bounded acquisition, HITL reservation, capture, and close/release phases | Remaining-budget proof before grant; expiry consumes run; no in-place extension |
| I6 — capture/close | Pass the live capability through materialization to exactly one capture; final source check; durable close before release | No write before materialization; marker last; no marker on failure; release ordering |
| I7 — adversarial VERIFY | Tests and evidence adapters for every Q/V row, including prohibited operations | Same exact implementation revision across implementation, Copilot, and Kiro evidence |
| I8 — migration guard | New v2-only live emission and separately activated refusal of new v1 live execution | Old manifests and quarantined runs remain untouched and unusable |

Potential implementation surfaces include `chroma_write_store.py`,
`writer_census.py`, `eval_corpus/run_manifest.py`,
`eval_corpus/r2b_capture_auth.py`, `eval_corpus/r2b_capture_run.py`,
`eval_corpus/capture.py`, and the capture CLI. The final slice brief must
confirm actual names at the implementation tip; this plan does not edit or
presume runtime interfaces.

## 4. Later operational state machine

The implementation must expose durable state transitions equivalent to:

```text
NEW
  → PREPARED
  → Q_AUTHORIZED
  → Q_ACQUIRING
  → Q_HELD
  → COVERAGE_PROVEN
  → SNAPSHOT_BOUND
  → PACKET_DRAFTED
  → PACKET_ACCEPTED
  → MATERIALIZED
  → CAPTURE_GRANTED
  → CAPTURING
  → FINAL_SOURCE_CHECKED
  → SEALED
  → CLOSING
  → CLOSED
```

Every state has terminal `ABORTED` or `QUARANTINED` transitions. Neither can
return to a live state. The same run cannot be reacquired, resumed, retried,
regranted, or cleaned by R2b.

### 4.1 Prepare and acquire

1. Generate a fresh safe `run_id`; prove the target capture directory is absent
   and all paths have safe lexical and resolved containment.
2. Verify the existing Restic doctor precondition. This is a precondition, not
   source authority.
3. Validate the one-shot Ryan authority **ACQUIRE WRITER QUIESCENCE AND
   PREPARE** and record `quiescence-start.json`.
4. Derive the exact-tip mutation inventory and runtime census. Any unknown,
   stale, unattested, uninspectable, PID-reused, alternate-gate, or bypass
   route is HOLD; do not control the route.
5. Acquire the canonical exclusive gate within its bounded phase. Record the
   lock identity, coordinator identity, monotonic start/deadline, and
   `quiescence-open.json` while ownership is live.
6. Revalidate coverage at the gate boundary. Only a zero-bypass result may
   establish source authority.

### 4.2 Snapshot and two human gates

7. Compute the complete trusted source snapshot while the same lease is held.
8. Create one draft `capture.json` binding the snapshot, open-evidence digest,
   gate identity, writer coverage, exact revision, fixed controls, packet
   freshness, duration policy, and future argv. Do not create the approval
   sidecar.
9. Ryan issues packet **ACCEPT** only while the same lease and all deadline,
   freshness, source, and target checks remain valid.
10. Trusted binder/materializer rechecks the approved body, sidecar, exact
    paths, source identity, coverage, live lease, deadline, and absent target.
11. Before **ACCEPT AND GRANT**, prove sufficient remaining budget for capture,
    final source recomputation, close evidence, and release. Ryan's grant is
    one-run/one-attempt authority only.

### 4.3 Capture and close

12. Materialize authorization before the first capture-directory write.
13. Execute exactly one capture with inherited fixed controls: `capture_id` is
    `run_id`, canonical overlap, spot `n = 20`, and one attempt.
14. Recompute the complete trusted live source identity. Any difference, writer
    bypass, timeout, exception, or failed outcome prevents the marker.
15. Publish the inherited completion marker last and atomically only for a valid
    complete or unresolved artifact set.
16. Write `quiescence-close.json` while the lease remains live, including the
    marker/failure result and final source comparison.
17. Release the gate, record the post-release observation, and stop. VERIFY and
    Ryan's GATE are separate later stages.

## 5. Duration and benchmark gate

The implementation may define named policy fields, but must leave their values
unresolved until representative scratch evidence exists:

```text
acquisition_bound
hitl_reservation_bound
capture_bound
release_close_bound
transaction_deadline
```

The future scratch benchmark must be isolated from production sources and must
report workload, hardware, implementation revision, measured distribution and
tail, and safety margin. This plan does not run or authorize that benchmark.
Ryan separately accepts the proposed production values before a live grant.
The accepted values are immutable for the run. A timeout aborts/releases and
consumes the run; it never extends in place.

## 6. Failure and recovery runbook

| Condition | Terminal behavior |
|---|---|
| Gate unavailable or bounded acquisition exceeded | No source authority; close/release as possible; consume run |
| Coverage unknown, stale, unattested, uninspectable, PID-reused, alternate, or bypass | HOLD; no process control; no snapshot authority |
| Snapshot or packet failure | No ACCEPT/grant; close/release; fresh run |
| Ryan delay, expiry, or insufficient remaining budget | No grant; close/release; fresh run |
| Binder/materialization refusal | No target write; close/release; fresh run |
| Capture fails before target creation | No marker; close/release; fresh run |
| Capture fails after target creation | Preserve partial output as quarantined evidence; no cleanup/resume/overwrite/retry |
| Source mutates while lease is held | Treat as bypass/noncompliance; no marker; quarantine; fresh authority |
| Coordinator crash | Terminal run; kernel release is not resumption authority; no regrant |
| Missing close evidence or close/release timeout | Terminal quarantine; no extension or repair in place |
| Replay, reacquisition, PID reuse, or lock-inode replacement | Refuse continuity; fresh run and authority chain |

Any retry requires a new run ID, quiescence authority, open evidence, trusted
snapshot, packet, packet ACCEPT, capture grant, and target. No R2b path removes
or cleans the failed output.

## 7. Authority and review gates

| Gate | Owner | Unlocks |
|---|---|---|
| Architecture review | Ryan | Authorization to request implementation, not runtime |
| Implementation | Cursor | A candidate v2 revision only |
| Same-tip safety/fidelity review | Copilot audit lane + Kiro | Evidence for Ryan's merge decision |
| Duration acceptance | Ryan | Concrete production bounds only |
| V2 activation | Ryan | New v2 tooling and v1-refusal behavior, if separately accepted |
| Quiescence preparation | Ryan | One live lease and packet draft only |
| Packet ACCEPT | Ryan | Materialization validation only |
| ACCEPT AND GRANT | Ryan | Exactly one capture |
| VERIFY / close GATE | Kiro + Ryan | Arc closure only |

Docs approval, implementation merge, duration acceptance, packet ACCEPT, and
**ACCEPT AND GRANT** are distinct. None is implied by another.

**TL;DR:** This plan serializes future R2b v2 work from implementation slices
through a single lease-bound transaction, while keeping live execution,
concrete duration values, and every grant behind separate Ryan gates.
