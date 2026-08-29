# Arc Brief — R2b Capture Authorization

> **Arc: R2b Capture Authorization.** This is a current-state snapshot, not a
> session log. Historical v1 facts remain in the linked v1 documents.

## 1. Product goal

ConvMem capture must produce a package whose export, processed state, and bound
Chroma state are proven to be one trusted source state and whose one capture is
authorized by Ryan. Because those sources can mutate continuously, R2b v2
establishes source authority only while one exclusive writer-gate lease is held
continuously across the authoritative transaction.

Done means: the v2 implementation is independently reviewed at one exact tip;
zero-bypass writer coverage and concrete duration values are separately accepted;
Ryan accepts a fresh packet and then issues **ACCEPT AND GRANT**; one capture
completes or fails closed; and independent VERIFY plus Ryan's GATE closes it.

## 2. System state

```text
exact-tip route inventory + runtime census
        │ zero unknown/bypass writers
        ▼
Ryan ACQUIRE WRITER QUIESCENCE AND PREPARE
        │ one live exclusive writer-gate lease
        ▼
trusted source snapshot + draft packet
        │ Ryan ACCEPT
        ▼
materialization (no capture output) → remaining-budget proof → Ryan ACCEPT AND GRANT
        │ one capture begins → create target → final trusted source recomputation
        ▼
quiescence-close evidence → release gate → release evidence → independent VERIFY / Ryan GATE
```

R2b v1 is historical policy and code provenance. The v2 correction is planning
only; no v2 lease, packet, sidecar, grant, capture directory, source mutation,
or service/process mutation exists or is authorized.

## 3. Repository facts and document map

| Artifact | Current state |
|---|---|
| `origin/main` | `872a0e483dd5eff09ccaef3c655af82f5e81e92e` (#243 writer-attestation hardening atop reviewed D4 base `89a7e045b130f005f57539478d9a180cbea905df`) |
| `docs/plans/ARCHITECTURE-r2b-capture-auth.md` | Historical v1 architecture; preserved |
| `docs/plans/EXECUTION-2026-07-20-r2b-capture.md` | Historical v1 execution plan; not valid for v2 live execution |
| `docs/plans/VERIFY-r2b-capture.md` | Historical v1 verification matrix; v2 supplement is required |
| `docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md` | This branch's normative v2 amendment; implementation/live operation unauthorized |
| `docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md` | Bounded v2 implementation and later operational sequence; not executed |
| `docs/plans/VERIFY-r2b-v2-quiescence.md` | v2 independent verification matrix; NOT RUN |
| `chroma_write_store.py` | Existing shared/exclusive writer gate substrate, protocol 1 |
| `writer_census.py` | Existing writer-session census substrate; v2 must extend its evidence, not assume coverage |
| D4 CG-2 surfaces | Landed on `main`; included in v2 writer-coverage analysis only |
| Recovery Authority | Separate governed route; included in v2 writer-coverage analysis only |

The existing complete-data-v2/v3 Restic artifacts remain backup evidence and a
doctor precondition. They are not R2b source authority.

## 4. Completion state

| Milestone | Status | Blocking condition |
|---|---|---|
| v1 architecture/implementation | Historical/landed | Does not solve continuous mutation |
| v2 architecture amendment | **Planning on this branch** | Ryan architecture review and acceptance |
| v2 implementation | **Not authorized** | Ryan authorizes a separate Cursor implementation slice |
| exact-tip zero-bypass coverage proof | **Does not exist for R2b** | Implementation plus route/census evidence |
| duration policy values | **Policy-pending** | Scratch benchmark evidence and separate Ryan acceptance; no 900-second default |
| v2 packet / lease / capture | **Not started and prohibited** | All preceding gates plus fresh authority chain |
| VERIFY and Ryan GATE | **Not started** | Later implementation and one authorized attempt |

## 5. Current role and next action

The current role is architecture/documentation review. The next authorized
action after Ryan accepts this plan is a Cursor-owned implementation PR covering
the v2 capability, exact-tip coverage/census, deadline state machine, evidence
chain, capture integration, and adversarial tests. No operator may create a v2
packet or acquire the gate from this document.

## 6. Required future sequence

1. Ryan reviews and accepts the v2 architecture, execution plan, and VERIFY.
2. Cursor implements the approved slices on an exact branch tip.
3. Copilot audit lane and Kiro review that same implementation revision; Ryan
   merges if satisfied.
4. Scratch-only benchmark evidence proposes phase bounds. Ryan separately
   accepts concrete production values; 900 seconds is not ratified.
5. A fresh run obtains **ACQUIRE WRITER QUIESCENCE AND PREPARE**, proves zero
   bypass, holds the exclusive gate, and drafts the packet.
6. Ryan **ACCEPTs** the packet; materialization/binder validation occurs while
   the same lease remains live.
7. Ryan **ACCEPT AND GRANTs**; exactly one capture runs, followed by final source
   recomputation, durable close evidence, gate release, release evidence, and VERIFY.

Every failure consumes the run and authority chain. Retry means a new run ID,
new lease authority, new packet, new ACCEPT, and new grant. No partial output is
cleaned or reused by R2b.

## 7. Hard stops and migration

- Services and processes remain running. R2b never starts, stops, restarts,
  signals, kills, reloads, or reconfigures them.
- Unknown, stale-revision, unattested, uninspectable, PID-reused,
  alternate-gate, or bypass-capable writers are a hard HOLD.
- R2b never selects, advances, rolls back, activates, reconciles, restores, or
  publishes CG-2/Recovery Authority state.
- `2026-07-21-r2b-capture-01` and `2026-08-27-r2b-capture-02` remain quarantined
  and permanently unusable. No old packet is upgraded or reinterpreted.
- Historical v1 manifests remain evidence. New live tooling emits only v2 after
  separate implementation/activation authority. New v1 live execution is
  refused only after the v2 amendment is properly activated; this docs branch
  does not activate that refusal.

## 8. Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-27 | Luna High | Recast the arc as v2 writer-gate planning; v1 remains historical, live operation remains prohibited, and duration/coverage policy remains pending. |
| 2026-08-28 | Cursor | Clean-base recovery onto `872a0e4`; reviewed-base SHA pointers reconciled; normative content preserved from accepted `b7f4764`. |

**TL;DR:** R2b v2 is a documentation-only correction on top of D4: one live
exclusive writer-gate lease must span snapshot through close, with zero-bypass
coverage and concrete durations still awaiting implementation evidence and Ryan
acceptance.
