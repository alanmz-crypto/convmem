# Arc Brief — R2b Capture Authorization

> **Arc: R2b Capture Authorization.** This is a current-state snapshot, not a
> session log. Historical v1 facts remain in the linked v1 documents.

## 1. Product goal

ConvMem capture must produce a package whose export, processed state, and bound
Chroma state are proven to be one trusted source state and whose one capture is
authorized by Ryan. Because those sources can mutate continuously, R2b v2
establishes source authority only while one exclusive writer-gate lease is held
continuously across the authoritative transaction.

Done means: the v2 I1–I3 implementation is independently reviewed and landed;
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

R2b v1 is historical policy and code provenance. The v2 architecture, execution
plan, and I1–I3 implementation are on `main`. Corrective IX integration landed
via PR #264 (merge commit `58375ad`, reviewed integration commit `39eab77`).
Authority-content identity and committed inventory convergence are closed at
implementation identity `4a3f3a17…` and inventory digest `760a4396…`.

**Landing the implementation does not authorize live operation.** No v2 lease,
packet, sidecar, grant, capture directory, live source mutation, or
service/process mutation is authorized without separate explicit Ryan authority.

## 3. Repository facts and document map

| Artifact | Current state |
|---|---|
| `origin/main` | `58375ad4585af6097988e86f1c4ef2dc7e4aeaa6`; v2 normative plan **and** I1–I3 implementation landed |
| PR #264 | **MERGED** — Corrective IX integration; reviewed tip `39eab771c5acba5b312b8b3c4704ce3676f7acbf`; Luna + Kiro PASS before merge |
| PR #260 | **MERGED** — Corrective VI/VII vault closure and authority boundary |
| PR #252 | **MERGED** — initial I1–I3 authority-boundary corrective chain |
| Draft PRs #246/#248/#249/#251 | **SUPERSEDED BUT PRESERVED** candidate chain; not actionable merge candidates |
| `docs/plans/ARCHITECTURE-r2b-capture-auth.md` | Historical v1 architecture; preserved |
| `docs/plans/EXECUTION-2026-07-20-r2b-capture.md` | Historical v1 execution plan; not valid for v2 live execution |
| `docs/plans/VERIFY-r2b-capture.md` | Historical v1 verification matrix; v2 supplement is required |
| `docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md` | Normative v2 amendment on `main`; live operation unauthorized |
| `docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md` | Bounded v2 implementation and later operational sequence; I1–I3 landed; I4–I8 not started |
| `docs/plans/VERIFY-r2b-v2-quiescence.md` | v2 verification matrix; no operational VERIFY PASS |
| `chroma_write_store.py` | Writer gate substrate with v2 attestation (protocol 1) |
| `writer_census.py` | Writer-session census substrate; v2 evidence extended |
| D4 CG-2 surfaces | Landed on `main`; included in v2 writer-coverage analysis only |
| Recovery Authority | Separate governed route; included in v2 writer-coverage analysis only |

The existing complete-data-v2/v3 Restic artifacts remain backup evidence and a
doctor precondition. They are not R2b source authority.

## 4. Completion state

| Milestone | Status | Blocking condition |
|---|---|---|
| v1 architecture/implementation | Historical/landed | Does not solve continuous mutation |
| v2 architecture amendment and execution plan | **LANDED on `main`** at `c6e8b2b0293edf8b0faf29e9e393e69eca6ca494` | — |
| v2 I1–I3 implementation | **LANDED on `main`** via PR #264 at merge `58375ad` | — |
| I1–I3 independent review | **COMPLETE** — Luna + Kiro PASS on integration commit `39eab77` | — |
| authority-content / inventory identity | **CLOSED** — `4a3f3a17…` / `760a4396…` | — |
| earlier I1–I3 candidates | **SUPERSEDED BUT PRESERVED** in draft PRs #246/#248/#249/#251 | Provenance only |
| exact-tip zero-bypass coverage proof | **NOT ACCEPTED** | Separate operational gate; not implied by implementation landing |
| duration policy values | **Policy-pending** | Scratch benchmark evidence and separate Ryan acceptance; no 900-second default |
| v2 packet / lease / capture | **Not started and prohibited** | All operational gates plus fresh authority chain |
| implementation review / merge | **COMPLETE** | PR #264 merged by regular merge 2026-08-31 |
| operational VERIFY and Ryan GATE | **Not started** | Later separately authorized attempt |

## 5. Current role and next action

I1–I3 implementation and merge are complete. The arc is waiting on **separate
operational authority** — not further implementation work. No operator may create
a v2 packet, acquire the production gate, activate shadow/capture, or advance
I4–I8 from this brief. Next actions require explicit Ryan grants for: zero-bypass
coverage acceptance, duration policy ratification, writer-gate acquisition, packet
drafting, or capture attempt.

## 6. Required future sequence

1. Scratch-only benchmark evidence proposes phase bounds. Ryan separately
   accepts concrete production values; 900 seconds is not ratified.
2. Zero-bypass writer coverage is proven and independently accepted at an
   operational tip (separate from implementation landing).
3. A fresh run obtains **ACQUIRE WRITER QUIESCENCE AND PREPARE**, proves zero
   bypass, holds the exclusive gate, and drafts the packet.
4. Ryan **ACCEPTs** the packet; materialization/binder validation occurs while
   the same lease remains live.
5. Ryan **ACCEPT AND GRANTs**; exactly one capture runs, followed by final source
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
  refused only after the v2 amendment is properly activated; implementation
  landing does not activate that refusal or any live gate.

## 8. Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-31 | Cursor | Reconciled post–Corrective IX landing: I1–I3 implementation and merge gate complete on `main` via PR #264; operational gates remain separately blocked. |
| 2026-08-30 | Codex Sol | Reconciled live GitHub state: PR #252 now carries unreviewed Corrective V `20d7f567` with required Pylint failing; #246/#248/#249/#251 are superseded but preserved; no live or merge authority was added. |
| 2026-08-27 | Luna High | Recast the arc as v2 writer-gate planning; v1 remains historical, live operation remains prohibited, and duration/coverage policy remains pending. |
| 2026-08-28 | Cursor | Clean-base recovery onto `872a0e4`; reviewed-base SHA pointers reconciled; normative content preserved from accepted `b7f4764`. |

**TL;DR:** R2b v2 I1–I3 implementation is **landed on `main`** via PR #264
(merge `58375ad`, reviewed integration `39eab77`; Luna + Kiro PASS). Authority-content
identity convergence is closed. Implementation merge gate is complete. **No live
writer gate, duration acceptance, packet, grant, capture, or I4–I8 advancement
is authorized** — operational gates require separate explicit Ryan authority.
