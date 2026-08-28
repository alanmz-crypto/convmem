# Architecture Amendment — R2b mutable-source quiescence v2

**Arc:** R2b Capture Authorization  
**Date:** 2026-08-27  
**Status:** Normative planning amendment; implementation and live operation are
unauthorized  
**Base:** [`ARCHITECTURE-r2b-capture-auth.md`](ARCHITECTURE-r2b-capture-auth.md)  
**Base revision:** D4 `89a7e045b130f005f57539478d9a180cbea905df` on `origin/main`

This versioned amendment corrects the v1 architecture's incompatibility with a
continuously mutating live source. It preserves v1 as historical evidence and
changes only the live R2b authority boundary. The existing v1 packet schema,
trusted source identity, path containment, fixed capture controls, completion
marker, and quarantine rules are inherited unless explicitly amended below.

## 1. Decision and non-negotiable boundary

R2b v2 establishes source quiescence by acquiring and continuously holding the
existing exclusive writer gate. Every compliant production writer continues to
run and obtains the same gate in shared mode. R2b does not stop, pause,
restart, signal, kill, reload, reconfigure, or otherwise control a service or
process.

This is not timing-only retry, service stopping, or Restic snapshot authority.
The gate is the serialization boundary; the trusted source snapshot is still
computed from the live export, processed state, and Chroma while that boundary
is held.

The v2 policy values are exactly:

```text
r2b_contract_version = 2
service_policy = "no_service_state_changes"
source_quiescence_policy = "exclusive_writer_gate_v1"
```

The v1 value `service_policy = "no_service_changes"` remains in the historical
v1 document and old manifests. It is not silently rewritten. New v2 tooling
must emit the v2 value only after separate implementation and activation
authority.

## 2. Inherited, implied, and pending policy

| Category | Policy |
|---|---|
| Inherited v1 | `authorization_phase: "r2b"`; `execution_mode: "real"`; `operations: ["capture"]`; exact path/sidecar binding; trusted complete source identity; `capture_id = run_id`; canonical overlap; spot `n = 20`; one attempt; last atomic completion marker; no same-directory retry; quarantine on failure |
| Mechanically implied by the existing gate | Shared writers use the existing gate path/protocol; exclusive ownership excludes compliant shared holders; lock acquisition is bounded; a held lease is live process/kernel state, not a JSON claim |
| New v2 normative values | Contract version 2; `service_policy = "no_service_state_changes"`; `source_quiescence_policy = "exclusive_writer_gate_v1"`; continuous lease; exact-tip zero-bypass proof; four-stage quiescence evidence; fail-closed close/release |
| Ryan-owned and policy-pending | Concrete acquisition, HITL reservation, capture, release/close, and hard transaction deadline values; acceptable benchmark population and safety margin; activation of v2 tooling and refusal of new v1 live execution |

No concrete production duration is ratified here. In particular, **900 seconds
is not ratified**.

## 3. Authority sequence

The following sequence is normative and linear:

1. **ACQUIRE WRITER QUIESCENCE AND PREPARE** — Ryan authorizes one fresh run's
   preparation. Trusted code proves zero-bypass coverage, acquires the exclusive
   gate, and records the open lease.
2. While that same lease remains live, trusted code creates the complete source
   snapshot and drafts one capture packet. This is not packet approval.
3. Ryan issues packet **ACCEPT** against the still-live lease and exact snapshot.
4. Trusted materialization/binder validation rechecks the packet, source,
   paths, target absence, deadline, and lease continuity.
5. Ryan issues **ACCEPT AND GRANT** only after sufficient remaining budget is
   proven for capture, final source recomputation, close evidence, and release.
6. Exactly one capture runs into the previously absent target.
7. Trusted code recomputes the final source identity before publishing the
   existing completion marker.
8. Trusted code durably records close evidence while the lease is still held,
   then releases the exclusive gate.
9. Independent VERIFY and Ryan's close GATE occur after release; they do not
   extend, repair, or regrant the transaction.

A pre-quiescence authority can authorize preparation only. It can never
authorize capture because the exact source identity and live lease evidence do
not yet exist.

## 4. Continuous live capability

The implementation must expose no caller-constructible substitute for the live
lease. It must hold an opaque, process-local capability whose validity requires
the kernel lock to remain owned. Copied, replayed, edited, or deserialized JSON
must never substitute for that capability.

The live quiescence capability binds, at minimum:

```text
run_id
grant_digest                         # digest of the active authority event
writer_gate_path
writer_gate_inode
writer_gate_protocol
coordinator_pid
coordinator_start_time
implementation_revision
writer_coverage_digest
open_evidence_digest
monotonic_deadline
live_lock_ownership
```

The implementation must additionally bind the authority digest, monotonic
lease start, phase bounds, bound source paths, and source identity. The capture
capability derived after packet ACCEPT must bind the exact ACCEPT AND GRANT
digest as a second live authority event. The grant digest is never accepted
from a packet field alone: trusted code obtains it from the authenticated
authority record and attaches it to the live capability state.

`writer_gate_inode` is the identity observed for the open lock descriptor, not
just a path string. If the path is replaced, the inode changes, ownership is
lost, or the descriptor cannot be proven live, the transaction fails closed.
Coordinator PID identity always includes start time so PID reuse cannot look
like continuity. The capability cannot be transferred, extended, serialized
for reuse, reacquired, or converted to a boolean.

The preparation authority record must bind, at minimum, the fresh `run_id`,
authority kind, v2 policy values, authority digest, exact implementation
revision, gate identity/protocol, bound source paths, coverage/census digests,
deadline policy, and prohibited actions. Its minimum prohibited set is:

```text
service_start, service_stop, service_restart, process_signal, process_kill,
daemon_reload, config_mutation, source_mutation, backup_restore,
cg2_activation, recovery_authority_mutation, capture, packet_accept,
accept_and_grant, cleanup_external
```

The preparation record may authorize only lease acquisition, proof, snapshot,
and packet drafting. Packet **ACCEPT** and **ACCEPT AND GRANT** are separate
Ryan authority records. The latter's digest is attached to the live capture
capability only after trusted materialization; no JSON field or copied record
can mint either capability.

## 5. Zero-bypass writer coverage

Exclusive ownership is not source authority until trusted exact-tip evidence
proves that every production route capable of mutating a bound source uses the
same writer-gate protocol. The proof has two parts:

1. an immutable route inventory derived from the exact implementation revision;
2. a runtime census at the gate boundary binding each observed writer or
   writer-like process to PID/start time, executable, entrypoint, revision,
   gate identity/protocol, and mutable source surfaces.

The inventory must explicitly cover:

- watch/F0 ingestion;
- refine;
- monitor and reconciliation;
- manual production entrypoints;
- CG-2 mutation/reconciliation routes, including D4's landed
  `file_generation_pointer.py` and `source_reconciler.py` surfaces and their
  serving/generation helpers;
- Recovery Authority routes; and
- every other route capable of mutating export, processed state, or bound
  Chroma.

Each route record must include a stable route ID, exact entrypoint, mutation
surfaces, writer-gate path/protocol, code revision, and coverage status. A route
excluded from the bound source requires a trusted, revision-bound reason;
“not observed” is not “not capable.”

The proof must explicitly show empty sets for unknown, stale-revision,
unattested, uninspectable, PID-reused, alternate-gate, and bypass-capable
writers. Missing process inspection, an unknown executable or entrypoint, an
open descriptor that cannot be inspected, an alternate/replaced lock inode, or
any possible direct mutation route is a hard **HOLD**. There is no count-only,
best-effort, or operator-assertion exception.

The writer coverage digest and runtime census digest are bound into the open
evidence, packet, live capability, and close evidence. Coverage is revalidated
at acquisition, packet ACCEPT, materialization, capture start, and final source
check. A mismatch ends the run.

## 6. Trusted source and Restic boundary

The existing v1 trusted snapshot contract is inherited: export bytes,
processed presence/bytes, and the complete canonical Chroma collection slice
(collection name and ID, IDs, documents, and superseded state) are recomputed
by trusted code. The same canonical helper must produce the approved snapshot,
capture extract, and final comparison. The one-hour freshness rule remains an
outer inherited bound at ACCEPT, binder execution, and materialization unless a
future normative authority review changes it.

Restic `complete-data-v2`/`complete-data-v3` artifacts remain backup evidence and
the existing doctor precondition. They are **not** R2b source authority and do
not prove export + processed + Chroma are one coherent point-in-time state.
R2b must not redefine the transaction as “capture immutable snapshot X.”

Any source mutation while the exclusive lease is held is a hard failure: it is
evidence of a bypass, noncompliant writer, or untrusted source path. The final
trusted recomputation must equal the approved snapshot before the marker can be
published.

## 7. Duration policy

The transaction has one monotonic hard deadline from a defined transaction
start. It also has separately bounded:

```text
writer_gate_acquisition
hitl_response_and_reservation
capture
release_and_close
```

The implementation must prove sufficient remaining budget before **ACCEPT AND
GRANT** for the capture, final recomputation, close evidence, and release. The
effective limit is the earliest of the hard transaction deadline, current
phase bound, and inherited packet-freshness bound.

Concrete production values remain Ryan-owned and policy-pending. A future
scratch benchmark must state workload, hardware, implementation revision,
sample distribution, tail choice, and safety margin; fixture timing cannot be
represented as production evidence. Ryan must separately accept the proposed
values before any live v2 grant. A timeout never extends in place. It aborts,
records/attempts fail-closed release, permanently consumes the run, and
requires a new authority chain.

## 8. Evidence chain and write ordering

The immutable authorization evidence is equivalent to these records under the
private authorization root, with no capture-directory write implied:

| Record | Minimum contents |
|---|---|
| `quiescence-start.json` | Fresh run, v2 policy, authority digest, exact revision, bound paths, target-absence proof, Restic precondition, and transaction start/deadline policy |
| `quiescence-open.json` | Same run and authority, gate path/inode/protocol, coordinator PID/start time, live lease start/deadline, writer coverage and runtime census digests, pre-quiescence service/process observation, and live-ownership proof |
| `capture.json` | Fresh v2 packet, complete trusted source snapshot, exact paths and argv, fixed controls, implementation revision, policy, deadline, gate identity, and `quiescence-open.json` digest; sidecar absent until packet ACCEPT |
| `quiescence-close.json` | Terminal state, final source comparison, marker or failure result, deadline status, close timestamp, release intent/result, and post-release observation |

The packet binds the live open evidence and the exact gate identity; open JSON
alone cannot establish continuity. The capture directory remains absent until
materialization after packet ACCEPT and **ACCEPT AND GRANT**.

The inherited capture ordering is:

```text
live materialization
→ create absent capture_dir
→ write all non-marker artifacts
→ final trusted source recomputation
→ write corpus_package_manifest.json last and atomically
→ no further capture-directory write
→ write quiescence-close.json while lease remains held
→ release gate
```

The marker remains the sole structural completion authority. A `FAILED` report,
drift, exception, timeout, crash, or missing close evidence never completes a
run. No cleanup, overwrite, resume, or partial-output reuse is part of R2b.

## 9. Failure semantics

| Failure | Normative result |
|---|---|
| Gate unavailable or acquisition timeout | HOLD/abort before source authority; fail-closed close/release attempt; run permanently consumed |
| Unknown, stale, unattested, uninspectable, PID-reused, alternate, or bypass writer | HOLD; do not stop, signal, or control it; no authoritative snapshot |
| Source snapshot failure or source drift | Abort; no packet ACCEPT/grant or marker; fresh run and snapshot required |
| Packet creation, digest, sidecar, or authority failure | Abort before grant; no reuse or packet upgrade |
| Ryan delay, reservation expiry, or packet freshness expiry | Abort/release; no ACCEPT or grant on the old run; fresh authority chain |
| Binder/materialization refusal | No target creation; abort/release; fresh run required |
| Capture failure before target creation | No capture; abort/release; fresh run required |
| Capture failure after target creation | Preserve partial output as quarantined evidence; no marker, cleanup, overwrite, resume, or same-run retry |
| Source mutation while gate is held | Hard fail as writer bypass; no marker; quarantine and fresh authority |
| Coordinator crash | Run is terminal; kernel lock release is not permission to resume; stale evidence cannot regrant |
| Missing close evidence or release/close timeout | Terminal quarantine; no extension or repair in place |
| Replay or reacquisition | Refuse consumed run, nonce, authority, capability, or lock identity; fresh run required |
| PID reuse or replaced/alternate lock inode | Refuse continuity; no capture or regrant |

Every failed attempt requires a fresh run ID, quiescence authority, packet,
packet ACCEPT, and capture grant. A failed grant never authorizes cleanup or
reuse of its partial output.

## 10. CG-2 and Recovery Authority firewall

R2b v2 may inspect CG-2 and Recovery Authority routes only for writer coverage.
It must never:

- select, advance, roll back, or activate generations;
- invoke reconciliation as a workaround;
- restore backup state;
- publish recovered authority;
- change serving state; or
- reinterpret Chroma or backup evidence as a new source of truth.

Those operations remain governed by their own arcs and grants. Their presence
in the coverage inventory is not permission to invoke them.

## 11. Migration and historical evidence

- Existing v1 manifests and packets remain v1 historical evidence; no packet is
  upgraded or reinterpreted.
- `2026-07-21-r2b-capture-01` and `2026-08-27-r2b-capture-02` remain quarantined
  and permanently unusable.
- New live tooling eventually emits v2 only, and only after separate
  implementation and activation authority.
- New v1 live execution becomes refused only when the v2 amendment is properly
  activated. This planning amendment does not activate that refusal.
- No migration mutates a source, Chroma, service state, backup, capture
  directory, old packet, or sidecar.

## 12. Later implementation slices and acceptance

After Ryan accepts this plan, Cursor may implement these separately reviewable
slices:

1. v2 schema and explicit authority-state model, preserving v1 historical
   validation and adding the exact policy values;
2. writer-gate identity and opaque live lease with inode/PID-start/deadline
   continuity and crash/replay refusal;
3. exact-tip route inventory, runtime census, and zero-bypass hard HOLDs;
4. trusted snapshot/packet binding to open evidence and the existing capture
   capability/materializer;
5. monotonic deadline and HITL reservation with remaining-budget proof;
6. one-attempt capture integration, final source check, close evidence, and
   marker-last ordering;
7. adversarial tests for every failure row and the full VERIFY matrix; and
8. explicit migration guard that refuses new v1 live execution only after
   activation authority.

Copilot audit and Kiro review must name the same implementation revision. Ryan
alone accepts concrete durations, merges implementation, activates v2, grants
live quiescence, and records the final GATE. This document authorizes none of
those actions.

**TL;DR:** R2b v2 makes one continuously held exclusive writer-gate lease the
source-authority boundary from trusted snapshot through packet ACCEPT,
materialization, ACCEPT AND GRANT, capture, final recomputation, close evidence,
and release; zero-bypass coverage and all concrete durations remain pending.
