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

R2b v1 is historical policy and code provenance. The v2 architecture and
execution plan are on `main`; v2 I1–I3 implementation is under corrective work
in draft PR #252. Its current head is unreviewed Corrective V
`20d7f567184500c33c9c82eb0d1c4d90fe6bc5f2`, and required Pylint is failing.
No v2 lease, packet, sidecar, grant, capture directory, live source mutation,
or service/process mutation is authorized.

## 3. Repository facts and document map

| Artifact | Current state |
|---|---|
| `origin/main` | `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d`; it contains the v2 normative plan, not the I1–I3 implementation |
| Draft PR #252 | Current carrier on `main@e930ae4`; live head `20d7f567184500c33c9c82eb0d1c4d90fe6bc5f2` (Corrective V), **unreviewed and required-CI red** |
| Draft PRs #246/#248/#249/#251 | **SUPERSEDED BUT PRESERVED** candidate chain; not actionable merge candidates and not deleted or repurposed |
| `docs/plans/ARCHITECTURE-r2b-capture-auth.md` | Historical v1 architecture; preserved |
| `docs/plans/EXECUTION-2026-07-20-r2b-capture.md` | Historical v1 execution plan; not valid for v2 live execution |
| `docs/plans/VERIFY-r2b-capture.md` | Historical v1 verification matrix; v2 supplement is required |
| `docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md` | Normative v2 amendment on `main`; live operation unauthorized |
| `docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md` | Bounded v2 implementation and later operational sequence; only I1–I3 is in corrective implementation |
| `docs/plans/VERIFY-r2b-v2-quiescence.md` | v2 verification matrix; no exact-tip implementation PASS or operational VERIFY |
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
| v2 architecture amendment and execution plan | **LANDED on `main`** at `c6e8b2b0293edf8b0faf29e9e393e69eca6ca494` | — |
| v2 I1–I3 implementation | **ACTIVE CORRECTIVE, BRANCH ONLY** in draft PR #252 at `20d7f567…` | Required Pylint failure; no immutable exact-tip review PASS |
| earlier I1–I3 candidates | **SUPERSEDED BUT PRESERVED** in draft PRs #246/#248/#249/#251 | Provenance only; do not merge, delete, or repurpose from this brief |
| exact-tip zero-bypass coverage proof | **NOT ACCEPTED** | One CI-green immutable tip plus required independent review |
| duration policy values | **Policy-pending** | Scratch benchmark evidence and separate Ryan acceptance; no 900-second default |
| v2 packet / lease / capture | **Not started and prohibited** | All preceding gates plus fresh authority chain |
| implementation review / merge | **BLOCKED** | Fresh Copilot PASS, then same-tip Kiro review, then Ryan merge decision |
| operational VERIFY and Ryan GATE | **Not started** | Later landed implementation and one separately authorized attempt |

## 5. Current role and next action

The current implementation route is draft PR #252. Its PR description still
names an older frozen pair, so reviewers must use the live GitHub head rather
than the stale body coordinates. Corrective V must first restore all required CI
and freeze one immutable review tip. Copilot then reviews that exact tip; Kiro
reviews only after Copilot PASS. No operator may create a v2 packet, acquire the
production gate, merge, or activate capture from this brief.

## 6. Required future sequence

1. Corrective V on draft PR #252 restores every required GitHub check and
   freezes one immutable full-SHA review target.
2. Copilot audit lane performs a fresh adversarial review of that exact tip.
3. Only after Copilot PASS does Kiro review that same exact revision; Ryan may
   then decide whether to merge. Earlier draft PRs remain preserved provenance.
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
| 2026-08-30 | Codex Sol | Reconciled live GitHub state: PR #252 now carries unreviewed Corrective V `20d7f567` with required Pylint failing; #246/#248/#249/#251 are superseded but preserved; no live or merge authority was added. |
| 2026-08-27 | Luna High | Recast the arc as v2 writer-gate planning; v1 remains historical, live operation remains prohibited, and duration/coverage policy remains pending. |
| 2026-08-28 | Cursor | Clean-base recovery onto `872a0e4`; reviewed-base SHA pointers reconciled; normative content preserved from accepted `b7f4764`. |

**TL;DR:** R2b v2 planning is on `main`, while I1–I3 implementation remains
branch-only in draft PR #252 at unreviewed, required-CI-red Corrective V
`20d7f567`. Draft PRs #246/#248/#249/#251 are superseded but preserved. No
merge, live writer gate, duration, packet, grant, or capture is authorized.
