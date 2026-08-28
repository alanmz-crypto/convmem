# Bounded Execution Plan — R2b v2 writer-gate transaction

**Arc:** R2b Capture Authorization
**Date:** 2026-08-27
**Status:** Planning only; implementation and live execution are unauthorized
**Owner:** Codex architecture/docs; later implementation is Cursor-owned; Ryan owns all HITL gates

**Normative amendment:** ARCHITECTURE-r2b-mutable-source-quiescence-v2.md
**Base execution plan:** EXECUTION-2026-07-20-r2b-capture.md
**Verification:** VERIFY-r2b-v2-quiescence.md

## 1. Purpose and non-authority

This plan makes the accepted v2 architecture executable on paper and defines
the evidence needed before implementation and before the first live grant. It
does not acquire the writer gate, create a packet or sidecar, create a capture
directory, control services/processes, mutate sources, or run a capture.

R2b v2 retains the following exact contract values:

    r2b_contract_version = 2
    service_policy = "no_service_state_changes"
    source_quiescence_policy = "exclusive_writer_gate_v1"

The current shared gate is the existing
~/.local/share/convmem/locks/chroma_writer_gate.lock with protocol version
1. The implementation must bind its canonical identity; this plan does not
authorize touching it.

## 2. Phase plan and gates

| Phase | Work product | Owner | Gate |
|---|---|---|---|
| E0 | Architecture amendment and this bounded plan reviewed | Codex, Ryan | Ryan architecture review; no implementation authority |
| E1 | Exact-tip mutation-route inventory and zero-bypass proof design | Cursor later, reviewed by Copilot/Kiro | Every bound-source mutation route accounted for |
| E2 | Shared gate and attestation implementation design | Cursor later | Same gate/protocol identity; no alternate lock |
| E3 | Representative scratch/runtime duration evidence and proposed bounds | Cursor later | Evidence supports acquisition, HITL, capture, and release/close bounds |
| E4 | v2 implementation and hermetic/adversarial tests | Cursor later | Ryan explicitly authorizes implementation; no live source use |
| E5 | Same-tip Copilot/Kiro review and mechanical verification | Copilot/Kiro | Exact revision and all v2 checks pass |
| E6 | Ryan accepts exact duration values and exact writer coverage | Ryan | Separate written acceptance before any live quiescence grant |
| E7 | Fresh live transaction, if separately authorized | Named operator + Ryan | Full two-stage HITL; this plan does not authorize it |

E0–E3 produce design and evidence requirements. E4–E7 cannot be inferred
from approval or merge of this document.

## 3. E1 — exact-tip writer coverage

The later implementation must generate a trusted coverage manifest at the
exact implementation tip that will be used for the v2 transaction. It must
enumerate every route capable of mutating any bound export, processed state, or
Chroma collection:

- watch/F0 ingestion;
- refine;
- monitor and reconciliation;
- manual production writers;
- CG-2 routes;
- Recovery Authority routes; and
- any other CLI, timer, worker, repair, migration, or maintenance route with
  production mutation capability.

For each route, record its entrypoint, mutation surfaces, shared gate protocol
and identity, code revision, process attestation requirements, and coverage
status. The trusted derivation must prove that no route can bypass the same
gate. “Not running now” is not sufficient if a route can start or mutate
without the gate.

The runtime census must be taken at the gate boundary and bind PID plus start
time, executable/entrypoint, code revision, protocol, gate identity, and source
surfaces. Unknown, uninspectable, stale, PID-reused, alternate-lock, or
bypass-capable observations are HOLDs. No operator may stop or signal a route
to remove it from the census.

Required E1 evidence:

    coverage_manifest.json
    coverage_manifest.sha256
    runtime_census.json
    runtime_census.sha256
    exact implementation revision
    writer gate canonical identity and protocol
    unknown_routes == []
    bypass_routes == []

## 4. E2 — transaction and authority design

The first Ryan authority must be named:

    ACQUIRE WRITER QUIESCENCE AND PREPARE

It authorizes only acquisition and continuous ownership of one exclusive
writer-gate lease plus preparation of one fresh packet. It does not approve the
packet and does not grant capture. The existing packet ACCEPT and ACCEPT AND
GRANT remain separate.

The later implementation must provide an opaque lease handle with:

- exact run ID and authority digest;
- exact implementation revision;
- canonical gate path, identity, and protocol;
- coverage and census digests;
- monotonic start and hard deadline;
- process identity and non-replayable nonce; and
- terminal close requirements.

The handle must be non-caller-constructible and must remain live from the
trusted source snapshot through final source recomputation and durable close.
The implementation must not expose a “quiesced” boolean that can outlive the
lease.

## 5. E3 — duration evidence and proposed bounds

Production duration values are not set by this plan. The later execution
preparation must derive proposed values from representative scratch/runtime
evidence, then Ryan must accept the concrete values separately before the first
live v2 quiescence grant.

The evidence exercise must use a new private scratch profile and representative
data volume/Chroma shape without touching the production export, processed
state, Chroma collection, services, config, or authorization state. It must
measure at least:

| Bound | Measurement |
|---|---|
| Acquisition | Time from authorized acquisition request to exclusive lease and open evidence |
| HITL response/reservation | Time budget from packet-ready evidence to Ryan ACCEPT and reservation of the already-held transaction; record this as an operational coordination bound, not a synthetic code benchmark |
| Capture | Full one-attempt capture plus artifact validation up to final source check |
| Release/close | Durable close evidence and lease release after success and each failure class |
| Overall transaction | Monotonic ceiling covering all phases and cleanup-free terminal closure |

The proposal must state workload identity, scratch profile, observed p50/p95
and worst-case samples, warm/cold conditions, safety margin, clock source,
and why the evidence represents the intended live transaction. It must also
show:

    acquisition_bound
    + hitl_bound
    + capture_bound
    + release_close_bound
    < transaction_deadline

where the inequality includes an explicit safety margin and accounts for the
one-hour packet staleness gate. Synthetic results cannot be used to claim a
live-source stability duration.

No value of 900 seconds is production-approved at architecture lock. The
proposal is incomplete until Ryan accepts the concrete values and evidence.

## 6. Future transaction sequence

The following is the only planned v2 order. It is a future sequence, not an
instruction to run now:

1. Confirm the implementation tip, architecture/VERIFY approvals, exact writer
   coverage, and proposed duration acceptance.
2. Run convmem doctor; require restic_gate: PASS before trusted snapshot work
   or any eval-root write.
3. Allocate a fresh safe run_id; reject all prior runs, especially
   2026-07-21-r2b-capture-01/ and 2026-08-27-r2b-capture-02/.
4. Prove canonical auth/capture paths, no prohibited symlink components, and
   absent EVAL_ROOT/<run_id>/capture.
5. Validate Ryan’s one-shot ACQUIRE WRITER QUIESCENCE AND PREPARE authority
   before gate acquisition.
6. Acquire the existing exclusive writer gate. Write durable open evidence
   binding the gate, holder, revision, deadline, coverage, and census.
7. Re-prove exact-tip zero-bypass coverage at the gate boundary. Any unknown,
   stale, uninspectable, PID-reused, alternate-lock, or bypass route is a
   HOLD; do not control the route.
8. Compute the complete trusted source snapshot while the lease is held:
   export SHA-256, processed state/digest, collection identity, extracted unit
   count, sorted-ID hash, and canonical capture-slice SHA-256.
9. Create one fresh draft capture.json under the new auth root. Bind the exact
   revision, absolute paths, source snapshot, v2 policy fields, fixed
   controls, prohibitions, duration values, quiescence evidence, and fully
   filled future argv. The sidecar remains absent.
10. Ryan performs packet ACCEPT while the lease and all freshness/deadline
    checks remain valid. Any source or authority drift is a terminal HOLD.
11. Trusted binding and materialization recheck the manifest, body digest,
    source identity, paths, symlink containment, target absence, exact argv,
    capability, and lease continuity.
12. Ryan performs the existing ACCEPT AND GRANT. No grant without the filled,
    current packet and the held lease.
13. Execute exactly one capture into the absent target with the fixed controls;
    no service or process operation occurs.
14. Recompute the trusted source identity before completion-marker publication.
    Drift, timeout, exception, or failed outcome prevents the marker.
15. Publish the existing completion marker last and atomically when valid.
16. Write durable close evidence while the lease is still held, then release
    the gate. Stop; independent VERIFY and Ryan GATE are later steps.

The packet’s existing one-hour staleness checks remain in force at ACCEPT,
binder execution, and materialization. The hard monotonic transaction deadline
is independent and may expire sooner. Neither limit may be extended in place.

The future packet must contain a fully filled argv vector with this shape; the
placeholders below are not executable authority:

    cd /home/lauer/Projects/convmem
    python3 scripts/eval_corpus_capture.py
      --run-manifest <AUTH_ROOT>/<run_id>/capture.json
      --export <approved absolute export path>
      --processed <approved absolute processed path>
      --capture-dir <EVAL_ROOT>/<run_id>/capture
      --chroma-dir <approved absolute Chroma path>
      --max-retries 1

## 7. Evidence required before Ryan ACCEPT

The packet-ready evidence must include:

- exact implementation revision and working-tree/revision proof;
- restic_gate: PASS timestamp;
- fresh run ID and proof no prior run is reused;
- exact absolute export, processed, Chroma, auth, and capture paths;
- no-symlink and containment results;
- absent-target proof;
- exact-tip coverage manifest and runtime census digests;
- proof that unknown and bypass route sets are empty;
- gate identity/protocol and held-lease evidence;
- exact pre-quiescence service/process state and gate-waiter observation;
- complete trusted source snapshot and timestamp;
- r2b_contract_version, both exact policy strings, fixed controls, and full
  prohibited actions;
- proposed duration values and Ryan’s separate duration acceptance evidence;
- fully filled future argv; and
- explicit statement that no sidecar, grant, capture, service change, or
  source mutation has occurred.

Ryan ACCEPT is invalid if any field is pending, if the packet is older than the
existing freshness bound, or if the lease/deadline has changed.

## 8. Evidence required before ACCEPT AND GRANT

The operator must prove, after packet ACCEPT and immediately before the grant:

- the accepted body digest and sidecar relationship are exact;
- the lease is the same continuous lease that produced the snapshot;
- the pre-quiescence service/process state remains unchanged except for the
  exclusive lease being held;
- coverage, census, revision, gate identity, and deadline remain valid;
- all source paths and the target remain unchanged and safe;
- the current trusted source snapshot equals the approved snapshot;
- materialization occurred before any capture-directory creation;
- the exact argv is the approved argv; and
- no prohibited operation has occurred.

Only then may Ryan issue the existing ACCEPT AND GRANT. The grant remains
one-run, one-attempt authority and cannot be delegated to a timing window.

## 9. Failure and recovery runbook

| Failure point | Required action |
|---|---|
| Preflight, Restic, coverage, census, path, target, or authority failure | HOLD before source authority; no packet grant or capture |
| Acquisition deadline | Terminal run; close/release as possible; fresh run required |
| Human response/reservation deadline | Terminal run; no packet ACCEPT; fresh run required |
| Snapshot or packet drift | Terminal run; discard authority semantics; fresh run and snapshot required |
| Materialization or grant failure | Do not create capture directory; release/close; fresh run required |
| Capture exception/timeout/FAILED | Preserve partial evidence; no marker; quarantine; no cleanup or resume |
| Final source drift | No marker; quarantine; fresh run required |
| Release/close failure | Terminal quarantine; do not extend or repair in place; escalate only for separately authorized observation |
| Coordinator crash | Rely on kernel lock release; treat run as terminal; never resume or reuse |
| Writer crash/restart | R2b does not restart or control it; source authority fails closed if coverage cannot be proven |

No R2b recovery step deletes, repairs, overwrites, or cleans an old run. A
partial capture remains evidence and is quarantined. A new attempt always has a
new run ID, source snapshot, packet, ACCEPT, and ACCEPT AND GRANT.

## 10. Implementation/review handoff

After Ryan authorizes implementation, Cursor should implement the amendment in
a separate branch and provide:

1. a v2 schema and authority/capability design;
2. exact-tip coverage and runtime census enforcement;
3. one continuous deadline-bound lease;
4. durable open/close evidence and crash refusal;
5. existing capture marker/quarantine preservation; and
6. hermetic and adversarial tests listed by VERIFY-r2b-v2-quiescence.md.

Copilot and Kiro must review the same implementation tip. Only after those
reviews and Ryan’s separate duration/coverage acceptance may a future T4/T5/T6
execution plan be opened. This document itself authorizes none of those steps.
