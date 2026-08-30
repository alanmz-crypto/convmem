# Arc Brief — Unbroken Key (R2b Capture Authorization)

> **Arc: Unbroken Key.** This is a current-state snapshot for R2b Capture
> Authorization, not a session log. Historical v1 facts remain in the linked
> v1 documents.

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

R2b v1 is historical policy and code provenance. The v2 architecture and
execution plan are on `main`; draft PR #252 implements I1-I3. Copilot's
independent exact-tip review of Corrective IV at
`6b5a8f9e441d028bafe8d586ec91199c3ecca219` failed because ordinary Python can
still manufacture production capability and mutate authoritative registry
state. Cursor has since created local, unpushed Corrective V candidate
`20d7f567184500c33c9c82eb0d1c4d90fe6bc5f2`; it is unreviewed and not a durable
remote review target. No v2 lease, packet, sidecar, grant, capture directory,
source mutation, or service/process mutation is authorized.

## 3. Repository facts and document map

| Artifact | Current state |
|---|---|
| `origin/main` | `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d`, the integration base for #252 |
| Draft PR #252 | Corrective IV remains unmerged at reviewed CI-green tip `6b5a8f9e441d028bafe8d586ec91199c3ecca219`; Copilot verdict is **FAIL** |
| Corrective IV authority implementation | `eval_corpus/r2b_v2/` on #252; valid hermetic lifecycle works, but in-process capability and registry isolation is not a security boundary |
| Local Corrective V candidate | Branch `fix/2026-08-30-2026-08-30-r2b-v2-corrective-v`, tip `20d7f567184500c33c9c82eb0d1c4d90fe6bc5f2`; local branch is 13 commits ahead while its remote remains at `e930ae4`; no PR or independent review |
| Corrective IV review handoff | `docs/inter-model/COPILOT-2026-08-30-r2b-corrective-iv-fail-handoff.md`; Cursor owns the next corrective |
| `docs/plans/ARCHITECTURE-r2b-capture-auth.md` | Historical v1 architecture; preserved |
| `docs/plans/EXECUTION-2026-07-20-r2b-capture.md` | Historical v1 execution plan; not valid for v2 live execution |
| `docs/plans/VERIFY-r2b-capture.md` | Historical v1 verification matrix; v2 supplement is required |
| `docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md` | Normative v2 amendment on `main`; live operation unauthorized |
| `docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md` | Bounded v2 implementation and later operational sequence; I1-I3 implementation is under corrective review |
| `docs/plans/VERIFY-r2b-v2-quiescence.md` | v2 verification matrix; operational VERIFY has not run |
| `chroma_write_store.py` | Existing shared/exclusive writer gate substrate, protocol 1 |
| `writer_census.py` | Existing writer-session census substrate; zero-bypass evidence remains required |
| D4 CG-2 surfaces | Landed on `main`; included in v2 writer-coverage analysis only |
| Recovery Authority | Separate governed route; included in v2 writer-coverage analysis only |

The existing complete-data-v2/v3 Restic artifacts remain backup evidence and a
doctor precondition. They are not R2b source authority.

## 4. Completion state

| Milestone | Status | Blocking condition |
|---|---|---|
| v1 architecture/implementation | Historical/landed | Does not solve continuous mutation |
| v2 architecture amendment | **On `main`** | No architecture gate remains for I1-I3 corrective work |
| v2 I1-I3 implementation | **Corrective V local candidate; unpushed and unreviewed** | Confirm single-writer ownership, stabilize `20d7f56`, push explicitly, and obtain CI-green immutable bytes |
| capability and registry authority boundary | **BLOCKING RESIDUAL DEFECT** | Production authority remains forgeable and backing state remains reachable by ordinary Python |
| exact implementation-revision binding | **BLOCKING RESIDUAL DEFECT** | Reviewed runtime binds authority to stale inventory SHA `1b0dd44f...` |
| exact mutation-sink governance | **BLOCKING RESIDUAL DEFECT** | Known filenames can conceal new generation-pointer sinks |
| genuine lifecycle / kernel-lock loss | **Focused PASS** | Preserve while closing manufacture paths; not sufficient for overall PASS |
| exact-tip zero-bypass coverage proof | **Not accepted** | Scanner concealment defect must close before evidence can be trusted |
| duration policy values | **Policy-pending** | Scratch benchmark evidence and separate Ryan acceptance; no 900-second default |
| v2 packet / lease / capture | **Not started and prohibited** | All preceding gates plus fresh authority chain |
| Copilot / Kiro review | **Copilot FAIL; Kiro blocked** | Fresh Copilot PASS on one new exact tip, then Kiro reviews that same tip |
| Operational VERIFY and Ryan GATE | **Not started** | Later merged implementation and one separately authorized attempt |

## 5. Current role and next action

The current role is Cursor corrective stabilization. First confirm no other
agent owns the shared checkout, then inspect local Corrective V tip
`20d7f567184500c33c9c82eb0d1c4d90fe6bc5f2` against the Copilot failure
handoff. Finish its evidence and tests, push with an explicit refspec, and
produce one CI-green immutable review target. Do not send Corrective IV or the
unreviewed local candidate to Kiro. No operator may create a v2 packet, acquire
production authority, or activate capture from this state.

## 6. Required future sequence

1. Cursor confirms single-writer ownership, inspects and stabilizes local
   Corrective V candidate `20d7f56`, and pushes it with an explicit refspec.
   The candidate must close the capability-manufacture, registry-reachability,
   implementation-revision, and mutation-sink governance defects documented in
   the Corrective IV failure handoff.
2. The new candidate passes focused adversarial tests, full pytest, pylint,
   CodeQL, and both Analyze jobs.
3. Copilot audit lane performs a fresh adversarial review of one immutable tip.
4. Only after Copilot PASS does Kiro review that same exact revision; Ryan may
   then decide whether to merge.
5. Scratch-only benchmark evidence proposes phase bounds. Ryan separately
   accepts concrete production values; 900 seconds is not ratified.
6. A fresh run obtains **ACQUIRE WRITER QUIESCENCE AND PREPARE**, proves zero
   bypass, holds the exclusive gate, and drafts the packet.
7. Ryan **ACCEPTs** the packet; materialization/binder validation occurs while
   the same lease remains live.
8. Ryan **ACCEPT AND GRANTs**; exactly one capture runs, followed by final source
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
| 2026-08-30 | Copilot audit | Named Arc Unbroken Key; Corrective IV failed exact-tip review, and local unpushed Corrective V candidate `20d7f56` now awaits Cursor stabilization and publication. |

**TL;DR:** **[Arc Unbroken Key]** draft #252 remains unmerged and unauthorized.
Corrective IV preserves genuine lock-loss invalidation but fails the
ordinary-Python capability, registry, revision, and mutation-sink boundaries;
local Corrective V `20d7f56` is unpushed and unreviewed, so Cursor must
stabilize and publish it before any Copilot re-review, Kiro review, or live gate.
