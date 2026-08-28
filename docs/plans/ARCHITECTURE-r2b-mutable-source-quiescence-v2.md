# Architecture Amendment — R2b mutable-source quiescence v2

**Arc:** R2b Capture Authorization
**Date:** 2026-08-27
**Decision:** Accepted in principle by Ryan, with required refinements below
**Status:** Normative amendment for review; implementation, live quiescence, packet creation, and capture remain unauthorized

**Base architecture:** ARCHITECTURE-r2b-capture-auth.md
**Bounded execution plan:** EXECUTION-2026-08-27-r2b-v2-quiescence.md
**Verification plan:** VERIFY-r2b-v2-quiescence.md

This document is the normative correction for the mutable-live-source problem
identified after the v1 timing-only retry. The base document remains the source
for the packet schema, trusted source identity, path rules, fixed capture
controls, marker contract, and quarantine semantics unless this amendment says
otherwise.

## 1. Decision and boundary

R2b v2 uses exclusive writer-gate quiescence. The coordinator acquires and
continuously owns the existing exclusive writer gate. Compliant writers remain
running and wait at their normal shared gate. R2b does not stop, pause,
restart, signal, kill, reload, reconfigure, or otherwise control a service or
process.

The selected correction is not a timing-only retry and is not an immutable
backup authority. It introduces one narrowly scoped source-quiescence
transaction around the existing R2b authorization chain:

    exact-tip coverage proof
      -> Ryan: ACQUIRE WRITER QUIESCENCE AND PREPARE
      -> acquire one exclusive writer-gate lease
      -> trusted source snapshot while the lease is held
      -> draft packet and Ryan packet ACCEPT
      -> materialize and Ryan ACCEPT AND GRANT
      -> capture and final trusted source recomputation
      -> durable close evidence
      -> release the lease and stop

The lease is a transaction boundary, not a service-management capability. No
R2b action activates CG-2, invokes Recovery Authority mutation, restores a
backup, mutates a source, changes configuration, or changes service state.

The old runs 2026-07-21-r2b-capture-01/ and 2026-08-27-r2b-capture-02/
remain quarantined and unusable. No v2 mechanism may reinterpret, reopen,
repair, or continue either run. Any eventual v2 execution requires a fresh run
ID and a new authority chain.

## 2. Contract delta

Every v2 packet and every v2 authority record must carry these exact values:

    r2b_contract_version: 2
    service_policy: "no_service_state_changes"
    source_quiescence_policy: "exclusive_writer_gate_v1"

service_policy means that no service or process state transition is in the
R2b authority surface. source_quiescence_policy names ownership of the existing
exclusive gate only; it is not shorthand for stopping or pausing writers.

The base R2b values remain fixed:

    authorization_phase: "r2b"
    execution_mode: "real"
    operations: ["capture"]
    capture_id: run_id
    overlap_policy: "canonical"
    spot_check_n: 20
    max_attempts: 1

The v2 contract adds a separate preparatory authority. It does not replace
packet ACCEPT or ACCEPT AND GRANT:

| Authority | Exact human action | Permitted effect | Not permitted |
|---|---|---|---|
| Quiescence preparation | ACQUIRE WRITER QUIESCENCE AND PREPARE | Acquire and continuously hold one exclusive writer-gate lease; prove coverage; compute the trusted snapshot; prepare one fresh packet | Any service/process control, packet approval, capture, grant, or reuse |
| Packet approval | Existing ACCEPT | Approve the exact filled packet while its snapshot and bindings remain valid | Acquiring the gate, changing the packet, or granting capture |
| Capture grant | Existing ACCEPT AND GRANT | Permit one already-bound capture through the opaque capability chain | Any second attempt, alternate argv, retry, directory reuse, or unrelated operation |

Releasing the lease is a mandatory lifecycle action of the first authority and
the transaction. It is not an independent operator permission and cannot be
used to extend, repair, or resume a run.

## 3. Normative invariants

The v2 design adds these invariants to the six base R2b invariants:

1. One continuous lease: the same exclusive writer-gate lease is acquired
   before the trusted source snapshot and remains held through packet ACCEPT,
   materialization, ACCEPT AND GRANT, capture, final trusted source
   recomputation, and durable close evidence. It is released only after the
   run is terminal.
2. Quiescence is gate ownership: quiescence means ownership of the existing
   exclusive writer gate. Compliant writers wait at their ordinary shared gate.
   No service or process-control authority is implied.
3. Zero bypass before source authority: trusted exact-tip evidence must show
   that every production route capable of mutating any bound export, processed
   state, or Chroma collection participates in this same writer-gate protocol.
   A gate lock by itself is never sufficient.
4. Unknown is unsafe: an unknown, unattested, uninspectable, stale-revision,
   PID-reused, alternate-lock, or bypass-capable route is a hard HOLD. There is
   no best-effort or count-only exception.
5. Deadline is monotonic and final: the transaction has one monotonic hard
   deadline and separately bounded acquisition, HITL response/reservation,
   capture, and release/close phases. No timeout may be extended in place.
6. Expiry closes the run: any phase expiry releases the gate using the
   fail-closed close path, permanently closes the run, and requires a fresh run
   ID and full authority chain. A timeout is never a retry signal for the same
   run.
7. Two independent human gates remain: quiescence preparation, packet ACCEPT,
   and ACCEPT AND GRANT are separate authority events. The first does not
   imply either of the latter two.
8. No source authority from backup alone: a passing Restic gate proves the
   required backup precondition only. It does not replace the trusted source
   snapshot or prove an atomic export/processed/Chroma image.

## 4. Existing gate and zero-bypass proof

The current merged machinery identifies the existing gate as:

    writer_gate_path: ~/.local/share/convmem/locks/chroma_writer_gate.lock
    writer_gate_protocol: 1

The implementation must resolve and bind the exact gate identity, protocol,
implementation revision, and bound Chroma root. An alternate lock path or a
caller-supplied lock identity is a refusal.

### 4.1 Exact-tip coverage manifest

Before the exclusive gate can establish source authority, trusted code must
derive a coverage manifest from the exact implementation revision under review.
The manifest is immutable evidence and must include, for every route that can
mutate a bound source:

| Required field | Meaning |
|---|---|
| route_id | Stable route identity, not a display label |
| entrypoint | CLI/module/function entrypoint |
| mutation_surfaces | Export, processed state, Chroma collection, or combinations |
| writer_gate_protocol | Exact shared protocol version |
| writer_gate_identity | Canonical identity of the existing gate |
| code_revision | Exact implementation tip |
| attestation_requirements | PID start time, executable/entrypoint, and protocol evidence where a live process exists |
| coverage_status | Must be covered; any unknown value is a HOLD |

The inventory must explicitly account for all applicable watch/F0 ingestion,
refine, monitor/reconciliation, manual production writers, CG-2 routes,
Recovery Authority routes, and any other route capable of changing the bound
source. “Not observed” is not “not capable.” Routes that do not mutate the
currently bound source must be excluded by a trusted, revision-bound reason,
not by an operator assertion.

### 4.2 Runtime exact-tip census

The preparation authority must combine the exact-tip coverage manifest with a
runtime census at the gate boundary. For each observed writer or writer-like
process, the evidence must bind:

    pid
    process start time
    executable identity
    entrypoint
    code revision
    writer-gate protocol and identity
    bound source surfaces
    gate state (shared waiter, absent, or other attested state)

The census must detect or refuse on PID reuse, stale code revision, missing
/proc or equivalent inspection, uninspectable open file descriptors, alternate
lock use, unknown command/signature, or a process capable of bypassing the
shared gate. A list of known systemd units or command-line patterns is useful
evidence but is not by itself a zero-bypass proof.

Before acquisition, the coordinator records the exact observed pre-quiescence
state: relevant service/unit state, writer PIDs and start times, executable and
entrypoint identities, code revisions, gate ownership/waiter state, and the
source surfaces each process could mutate. This is an observation and
attestation record, not permission to change that state. A missing or
uninspectable pre-state field is a HOLD.

The trusted proof is therefore:

    exact implementation tip
      + complete mutation-route inventory
      + shared gate/protocol identity
      + runtime census and attestations
      + unknown/bypass set == empty
      -> source authority may be established

If any part cannot be derived or inspected, preparation returns HOLD before a
source snapshot is authoritative. The coordinator must not “stop whatever
seems active” to make the proof pass.

## 5. Authority records and capability chain

The first authority is named exactly for its boundary:

    ACQUIRE WRITER QUIESCENCE AND PREPARE

Its body is a one-shot, run-bound record containing at least:

    authority_kind: "r2b_writer_quiescence_prepare"
    run_id
    r2b_contract_version: 2
    service_policy: "no_service_state_changes"
    source_quiescence_policy: "exclusive_writer_gate_v1"
    implementation_revision
    writer_gate_path
    writer_gate_protocol
    writer_gate_identity
    coverage_manifest_sha256
    runtime_census_sha256
    bound_source_paths
    bound_chroma_identity
    duration_policy_version
    phase_deadlines (proposed values only until Ryan separately accepts them)
    prohibited_actions

Its prohibited list must include, at minimum:

    service_start
    service_stop
    service_restart
    process_signal
    process_kill
    daemon_reload
    config_mutation
    source_mutation
    backup_restore
    cg2_activation
    recovery_authority_mutation
    capture
    packet_accept
    accept_and_grant
    cleanup_external

The quiescence authority is validated before any gate acquisition. It mints
an opaque, non-caller-constructible quiescence lease handle only after the
zero-bypass proof and authority bindings pass. The handle binds the authority
body, exact revision, gate identity, coverage digests, run ID, and monotonic
deadline. It cannot be serialized into a reusable grant.

The v2 capture chain is:

    Ryan ACQUIRE WRITER QUIESCENCE AND PREPARE
      -> trusted exact-tip coverage proof
      -> opaque held exclusive-gate lease
      -> trusted source snapshot
      -> fresh draft capture.json
      -> Ryan ACCEPT
      -> existing bind_r2b_capture and opaque _R2bCapability
      -> materialize_r2b_write_authorization
      -> Ryan ACCEPT AND GRANT
      -> run_capture(..., r2b_capability=capability)
      -> capture and final source check
      -> durable close evidence
      -> release lease

No caller-provided boolean, path equality, process name, snapshot, or
capability field can substitute for trusted derivation from the authoritative
records.

## 6. Transaction state machine

The normative states are:

    PREPARED
      -> Q_AUTHORIZED
      -> Q_ACQUIRING
      -> Q_HELD
      -> COVERAGE_PROVEN
      -> SNAPSHOT_BOUND
      -> PACKET_DRAFTED
      -> PACKET_ACCEPTED
      -> CAPTURE_GRANTED
      -> CAPTURING
      -> FINAL_SOURCE_CHECKED
      -> SEALED
      -> CLOSING
      -> CLOSED

The normal sequence is linear. Every state has a terminal failure transition
to ABORTED or QUARANTINED; neither terminal state can transition back to a
live state.

Required evidence boundaries:

1. PREPARED: fresh run ID, absent target, canonical paths, Restic PASS,
   exact implementation revision, and authority body are validated.
2. Q_AUTHORIZED: Ryan’s one-shot ACQUIRE WRITER QUIESCENCE AND PREPARE
   authority is present and not expired.
3. Q_HELD: the exclusive gate is held; a durable open record binds the process,
   lock identity, monotonic start/deadline, and authority digest.
4. COVERAGE_PROVEN: exact-tip route inventory and runtime census prove zero
   bypass. Otherwise HOLD and release.
5. SNAPSHOT_BOUND: the trusted complete source identity is computed while the
   same lease is held.
6. PACKET_DRAFTED: capture.json binds the source snapshot, paths, fixed
   controls, full future argv, exact revision, quiescence evidence, and
   duration policy. It is not approved.
7. PACKET_ACCEPTED: Ryan ACCEPTs the filled packet while all age, identity,
   coverage, path, and target checks remain valid.
8. CAPTURE_GRANTED: existing materialization and ACCEPT AND GRANT checks pass;
   the capability is for this one run only.
9. FINAL_SOURCE_CHECKED: the trusted source identity still equals the
   approved snapshot. Capture drift is a hard failure with no marker.
10. SEALED: the existing last atomic completion marker is valid and no further
    artifact write is allowed.
11. CLOSED: close evidence is durable, including final identity, marker result
    or failure, deadline status, and release intent. Only then is the gate
    released.

The close record must be written before releasing the kernel lock. A crash
before CLOSED permanently invalidates the run for further execution. A recovery
observer may report the state, but may not resume, repair, clean, or regrant
the run. Any partial capture directory remains quarantined.

After release, trusted close verification records the corresponding
post-release service/process observation and proves that the authorized
pre-quiescence service/process state was unchanged by R2b, except for the
exclusive lease no longer being held. A mismatch is a failure requiring
separate investigation; R2b does not restart, stop, signal, or otherwise
restore a service.

## 7. Duration policy

Architecture lock ratifies the shape of the policy, not production numbers.
The execution plan must derive and document proposed values from representative
scratch/runtime evidence for:

    acquisition_timeout
    hitl_response_and_reservation_timeout
    capture_timeout
    release_and_close_timeout
    transaction_deadline (monotonic hard ceiling)

The proposal must include measured distributions, workload and hardware
identity, safety margin, and the relationship between the sum of phase bounds
and the outer transaction deadline. Synthetic fixture results must not be
represented as live-source timing evidence.

No value of 900 seconds is ratified here. Before the first live v2 quiescence
grant, Ryan must separately accept the concrete proposed values and their
evidence. The accepted values become immutable for that run and are included
in the authority and packet body.

The deadline uses a monotonic clock and starts at the defined transaction start
boundary. Every phase checks the same absolute deadline as well as its own
bound. The one-hour packet staleness rule remains mandatory at ACCEPT, binder
execution, and materialization; it is an independent freshness gate, not a
substitute for the transaction deadline. The effective time limit is the
earliest applicable limit.

Expiry or any failed phase causes a fail-closed release/close attempt. It does
not permit a deadline extension, a new ACCEPT on the old body, or a retry in
the old run. If release/close itself exceeds its bound, the run is terminally
quarantined and requires a separately reviewed recovery observation; R2b does
not signal or kill a holder.

## 8. Evidence and write ordering

The quiescence evidence is separate from the capture directory and is
write-once under the private authorization root:

| Evidence | Required contents |
|---|---|
| quiescence-authority.json | Ryan authority body and canonical digest |
| quiescence-open.json | Run, authority digest, exact revision, coverage/census digests, gate identity, monotonic start/deadline, wall-clock observations, and holder identity |
| capture.json | Fresh v2 packet draft, including snapshot and exact future argv |
| quiescence-close.json | Terminal state, final snapshot comparison, marker/failure result, deadline status, release intent, and close timestamp |

The existing sidecar is still forbidden until Ryan ACCEPTs the packet. No
capture.json.approved.sha256 is created by preparation or architecture work.
The capture directory remains absent until materialization after packet ACCEPT
AND GRANT.

The existing capture write order remains authoritative:

    materialize -> create absent capture_dir -> write artifacts
      -> final trusted source check
      -> last atomic completion marker
      -> close evidence
      -> release gate

There is no write after the completion marker inside the capture directory.
The close record is authorization evidence outside that directory and is
durably written before release.

## 9. Failure, crash, and replay semantics

| Condition | Required result |
|---|---|
| Restic, authority, revision, path, target, coverage, census, or gate refusal | HOLD before source authority; no packet grant or capture |
| Unknown/bypass writer route | HOLD; do not stop or signal it; no snapshot authority |
| Gate acquisition timeout | Release/close as possible; permanent terminal run; fresh run required |
| HITL response/reservation timeout | Release/close; packet is not accepted; fresh run required |
| Capture or release/close timeout | Terminal failure; no in-place extension; quarantine any partial output |
| Source drift before ACCEPT, at materialization, or final check | No sidecar/grant or no marker as applicable; fresh source/packet/run required |
| Coordinator crash before close | Kernel lock may release; run remains terminal and any partial output quarantined; no resume |
| Writer crash while waiting at the shared gate | R2b does not restart or control it; coverage/reconciliation failure is a HOLD |
| Lease-holder process restart | R2b does not restart it; prior run is terminal and cannot be resumed |
| Duplicate authority, replayed nonce, or stale capability | Refuse; no gate reuse or capture |
| Marker or close evidence incomplete | Run is not closed successfully; no reinterpretation or cleanup by R2b |

The normal service/process pre-state is not changed by R2b, so restoration is
not a stop/start operation. The only state restored by the transaction is the
absence of the exclusive lease: the kernel releases it after close, allowing
compliant writers to proceed under their existing service state. R2b must
record the gate’s pre-acquisition and post-release ownership facts, not claim
service-state restoration.

## 10. Option B assessment

Immutable-backup authority is rejected for this correction. The current
complete-data/Restic gate and artifacts can prove backup health and repository
integrity, but a passing gate alone does not prove that export, processed state,
and Chroma were captured as one coherent point-in-time image. If backup
creation reads mutable components at different moments, the resulting image
would need a new cross-component atomicity contract, provenance schema, restore
dependency, and source-of-truth decision.

Option B would also change the scientific claim from “capture the current
authoritative source” to “capture snapshot X.” That can be a valid future
architecture, but it is a larger authority and provenance change and risks a
second source of truth. It is not needed when the existing writer gate can
provide a narrow, auditable interval of source stability.

## 11. Interaction with CG-2 and Recovery Authority

The coverage proof must enumerate CG-2 and Recovery Authority routes even when
their current state is inactive or non-mutating. An inactive route is safe only
when the exact tip proves that it cannot mutate the bound surfaces during the
transaction, and the proof is included in the coverage manifest.

R2b v2 does not activate, pause, roll back, restore, or otherwise mutate either
authority. CG-2 and Recovery Authority remain independent authority domains.
Their writer paths must use the same shared gate if they are capable of
production mutation; otherwise v2 cannot prove zero bypass and must HOLD.

## 12. Implementation surface and tests

Implementation is a later Cursor-owned phase after this amendment and the
bounded plans are reviewed and authorized. The implementation must cover, at
minimum:

| Surface | Required work |
|---|---|
| chroma_write_store.py | Expose the existing gate identity/protocol to trusted v2 code; preserve shared-writer behavior; provide one non-reentrant, deadline-bound exclusive lease handle |
| writer_census.py and coverage machinery | Generate exact-tip route coverage and runtime attestations; fail closed on unknown, stale, uninspectable, PID-reused, or alternate-lock writers |
| eval_corpus/r2b_capture_auth.py | Validate v2 fields, quiescence authority, nonce/replay rules, evidence digests, deadlines, and the existing packet/capability chain |
| eval_corpus/r2b_capture_run.py | Require the held lease from snapshot through final source check and close evidence; preserve marker/quarantine behavior |
| scripts/eval_corpus_capture.py | Pass the opaque lease/capability without adding caller knobs; enforce fixed argv and one attempt |
| Tests | Exercise timing, crash, replay, coverage, gate identity, PID reuse, unknown route, drift, target precreation, marker ordering, and all prohibited operations |

Adversarial tests must prove that:

- a lock held by an unknown or stale-revision route cannot become source
  authority;
- a process with an alternate lock or bypass path is a hard HOLD;
- a PID reused with a different start time cannot satisfy an attestation;
- a missing or uninspectable runtime census cannot pass;
- the lease remains held while human approval/reservation is pending, but its
  monotonic deadline cannot be extended;
- crash at every state produces no reusable authority and no same-run retry;
- final source drift prevents the marker;
- service-control, source-mutation, backup-restore, CG-2, and Recovery
  Authority operations are rejected by schema and execution paths;
- the old quarantined runs cannot be rebound or upgraded; and
- the sidecar and capture directory remain absent before their existing gates.

## 13. Verification additions and migration

The companion VERIFY plan adds pre-execution checks for exact-tip coverage,
runtime census, gate identity, authority separation, duration acceptance, lease
continuity, failure closure, and restoration of gate availability without
service-state changes. It preserves all existing V0–V6 R2b checks.

The migration is non-upgrading and fail-closed:

1. Existing v1 packets, drafts, sidecars, directories, and capabilities are
   not converted to v2.
2. Existing quarantined runs remain unusable and are retained as evidence.
3. v2 code must reject a v1 packet when r2b_contract_version or the required
   quiescence policy is missing or mismatched.
4. No live v2 grant occurs until the exact implementation tip, coverage
   manifest, runtime-census behavior, and proposed duration values have passed
   the required reviews and Ryan has separately accepted the concrete bounds.
5. A v2 run always starts with a fresh run ID, fresh authority, fresh trusted
   snapshot, absent capture target, and the full two-stage Ryan HITL chain.

No architecture approval, documentation merge, or implementation merge is an
execution grant.

## 14. Acceptance bar for this amendment

Before implementation may begin, reviewers must agree that:

- the selected mechanism is the existing exclusive writer gate, not service or
  process control;
- r2b_contract_version = 2, service_policy =
  "no_service_state_changes", and source_quiescence_policy =
  "exclusive_writer_gate_v1" are exact;
- zero-bypass exact-tip proof is a prerequisite to source authority;
- duration values are proposed by evidence and separately accepted by Ryan,
  with no architecture-level ratification of 900 seconds;
- packet ACCEPT and ACCEPT AND GRANT remain separate;
- crash, timeout, drift, replay, and quarantine paths are terminal and
  fail-closed; and
- no service, process, source, configuration, backup, CG-2, Recovery Authority,
  sidecar, capture, or prior-run state is mutated by this planning phase.

This document is ready for architecture review only.
