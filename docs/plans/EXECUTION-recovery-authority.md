# Execution Plan — Recovery Authority

**Arc:** Recovery Authority  
**Phase:** Execution Planning  
**Source:** Ryan's Execution Planning authorization for the locked Recovery Authority direction  
**Architecture lock:** `22852a07e66920874045e0e85c4572ab6c0b29b8` (the locked architecture bytes)  
**Carrier branch:** `plan/2026-08-22-recovery-authority`  
**Carrier tip:** `a133629f96cc34c4df2fda2730b5bcb272d743da`  
**Baseline:** `origin/main` at `c1fac4c2c40662d9d1f88a1a020835feecce682b`  
**Kiro architecture verdict:** PASS, no required architecture amendments  
**Authority:** Ryan — Execution Planning only; Execute is NOT AUTHORIZED

## Planning Status

```text
Phase:        Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Codex authors; Kiro reviews; Cursor downstream implementation
Authority:    Ryan — Execution Planning only; Kiro Execution Plan review pending
Execute:      NOT AUTHORIZED
```

## Human consequence

If Kiro passes this plan and Ryan later grants individual tasks, Cursor will
have a bounded path to implement provenance-aware recovery without changing the
legacy v2 recovery contract, treating a projection as authority, mutating live
data during preflight, or allowing a crash to expose mixed state. The plan does
not itself restore data, activate authority, publish a serving pointer, or
grant any Execute work.

### 5 Ws

| | |
|---|---|
| **Who** | Codex shapes the plan; Kiro reviews it; Cursor is the later default implementation lane; Ryan owns each Execute grant and all live operations. |
| **What** | Four bounded V4g–V4j/V4l execution tasks plus one separately represented, genuinely blocked V4k task. |
| **When** | After the Recovery Authority Architecture Direction was locked at `22852a07`; before any Execute grant. |
| **Why** | Deferred complete-data recovery obligations cross registry authority, projections, generation binding, rollback continuity, and crash closure. |
| **How** | A serial plan establishes the v3 substrate, authority/projection state machine, scratch-only bulk workflow, and recovery-side crash evidence; V4k cannot open until CG-2 Design A is ratified and stable. |

**TL;DR:** This is a planning-only package. It creates no implementation,
migration, restore, activation, or serving authority.

## 1. Intake and invariant questions

The approved direction is the Recovery Authority Architecture Direction at the
locked bytes `22852a07e66920874045e0e85c4572ab6c0b29b8`. The later carrier tip
`a133629f96cc34c4df2fda2730b5bcb272d743da` only binds the review package SHA;
it does not replace the architecture revision.

| Planning question | Answer |
|---|---|
| **Where am I?** | Execution Planning, after Architecture HITL and Ryan Architecture Lock. |
| **How should I think?** | Task Decomposer, Dependency Mapper, and Scope Guardian. |
| **What function am I performing?** | Shape the locked direction into bounded, separately grantable execution tasks. |
| **What standards apply?** | `docs/planning/EXECUTION-PLANNING.md`, the locked architecture, existing VERIFY rows, Team Charter, and the builder-reference data-ownership/module-boundary guidance. |

## 2. Locked architecture and scope boundary

The following are locked decisions, not execution-plan options:

- `complete-data-v3` is the provenance-aware recovery profile; `complete-data-v2`
  retains its existing legacy recovery contract.
- There is no automatic v2→v3 migration, upgrade, or reinterpretation. Existing
  v2 snapshots remain valid under v2 and are not made v3 by this arc.
- Provenance authority and content authority remain distinct. The immutable
  registry generation is provenance authority; JSONL and Chroma are projections.
- The selected Restic snapshot/tree binds exactly to `T_g`, `P_g`, and `M_g`.
  The capture-evidence sidecar is evidence only and never binding authority.
- Whole-registry validation is separate from projection validation.
- A valid recovered authority may be projection-pending and non-serving.
  Serving activation is a separate bounded CG-2 handoff.
- Rollback requires independent continuity evidence, a fresh Ryan grant, and
  expected-current authority checks.
- Crash closure leaves only the prior complete state or a complete
  pending/blocked replacement; no mixed state and no stale fallback.
- T3 remains closed. Broad T5 fault-injection/endurance work remains outside
  this arc.

### In scope

- V4g–V4j complete-data-v3 and provenance-registry recovery integration.
- V4l recovery-side interruption and crash-closure verification only.
- Shared registry, manifest, tree, projection, state, and no-live-change
  contracts needed by those rows.
- The three required downstream documentation obligations from Kiro:
  `docs/RECOVER.md` provenance-aware wording uses v3; the V8i provenance-aware
  oracle/profile label is v3; and v2 snapshots are explicitly not migrated or
  reinterpreted.
- A bounded V4k contract and dependency record, but not executable V4k work.

### Out of scope

- Any implementation, migration, bulk restore, live-data mutation, or
  provenance-authority activation during this planning phase.
- CG-2 implementation or activation, V1h, V3i, Shadow, R2b, V3/V1h
  downstream promotion, or T3 reopening.
- Broad T5 fault-injection, endurance, SLO, egress, or general operational
  campaigns.
- Reopening `provenance-envelope-v1`, integrity-meet semantics, assertion
  identity/commitment semantics, bounded recursive verification, or the
  conservative integrity lattice.
- Dedicated DeepSeek R1 direct/API adversarial critique. Routine local Ollama
  and ordinary ConvMem retrieval remain unaffected.

### Deferred dependencies

| Dependency | State and consequence |
|---|---|
| **CG-2 Design A ratification and stable generation/pointer semantics** | **BLOCKED for V4k execution.** The plan may describe the interface and evidence but no V4k branch, implementation, rollback drill, or serving publication may open. If Design A changes generation semantics, the V4k task must absorb that change before execution. |
| **Ryan Execute grant** | Required separately for each executable task. This plan is not an Execute grant and does not authorize Cursor to begin. |
| **Live v3 snapshot/registry and authority activation** | Not available or authorized in planning. All later evidence must use isolated fixtures/scratch roots until Ryan separately grants live operations. |

## 3. Task decomposition

The sequence is intentionally four executable tasks plus one blocked task. It
does not mirror every VERIFY row: V4g/V4h share a substrate, V4i is the state
machine, V4j is the separately gated workflow, and V4l is the narrow recovery
crash boundary. V4k is represented separately so the CG-2 prerequisite cannot
be mistaken for a soft deferral.

| ID | Deliverable | In-scope surface | Depends on | Acceptance gate | Execution lane |
|---|---|---|---|---|---|
| **T1** | v3 recovery profile and durable registry validation substrate | `complete_data_restore.py`, profile/Restic boundary modules, `scripts/complete_data_restore_preflight.py`, `docs/RECOVER.md`, focused restore/profile tests and fixtures | Locked architecture only | v2/v3 coexistence, required registry path, independent manifest/sidecar validation, exact `P_g/M_g/T_g` evidence, no migration | Cursor, after Ryan T1 grant |
| **T2** | Authority-recovery and projection-agreement state machine | Recovery authority/registry surfaces, `complete_data_restore.py` integration boundary, projection/generation bindings, focused state/negative tests | T1 | Whole registry/history/graph validation; pending/blocked/quarantined states; no stale projection or serving fallback | Cursor, after T1 completion and Ryan T2 grant |
| **T3** | Bounded scratch-only bulk-recovery workflow and no-live-change contract | `backup_workflows.py`, `restic_snapshot.py`, restore-preflight CLI/reporting, workflow tests and isolated fixtures | T1 and T2 | Explicit Ryan grant required by workflow; exact snapshot/tree binding; missing/partial authority leaves live state unchanged; no item-by-item identity import | Cursor, after T2 completion and Ryan T3 grant |
| **T4** | Recovery-side interruption/crash-closure verification | Durable registry selector/publication/recovery boundaries, fault-injection seams, focused crash-closure tests and evidence reports | T1, T2, and T3; does not require V4k execution | Every recovery-side boundary closes to prior complete or complete pending/blocked state; no mixed state or stale fallback; no T5 expansion | Cursor, after Ryan T4 grant |
| **D1 / V4k BLOCKED** | Selected-generation and rollback-continuity contract plus later integration evidence | Bounded interface to locked CG-1 foundation and CG-2 generation/pointer surfaces | **CG-2 Design A ratification and stable semantics;** T1/T2 contracts as applicable | Cannot open until exact Design A ratification and stable generation/pointer model are recorded; fresh grant, expected-current CAS, independent continuity witness, and exact target evidence required | Cursor later, only after dependency unlock and a new Ryan V4k grant |

No task may silently combine V4g–V4j, V4k, or V4l into one Execute grant.

## 4. Task contracts and predeclared evidence

### T1 — v3 recovery profile and durable registry validation substrate

**Deliverable:** A closed, provenance-aware `complete-data-v3` restore profile
and a separate immutable registry validator, while preserving the existing v2
profile as a valid legacy contract.

**File/surface scope:**

- Extend the existing restore policy/profile boundary in
  `complete_data_restore.py`, `restic_snapshot.py`,
  `backup_workflows.py`, and `scripts/complete_data_restore_preflight.py`
  only as needed to distinguish v2 from v3.
- Add the `provenance/` Tier-1 classification and writer-census entry without
  changing the closed v2 meaning of existing paths.
- Add registry manifest/graph/history/schema/policy/recipe validation as a
  separate validator; `.convmem-backup-evidence.json` remains evidence-only.
- Update `docs/RECOVER.md` so provenance-aware recovery names v3, while the
  legacy v2 section explicitly remains valid and non-migrating.
- In the later execution closure, retain the V8i row identity and substantive
  oracle while retargeting its provenance-aware profile label to v3. The
  companion VERIFY below maps this without creating a second oracle.
- Focused fixtures/tests: `tests/test_complete_data_restore.py`,
  `tests/test_restic_snapshot.py`, `tests/test_backup_workflows.py`, plus a
  narrowly named recovery-authority profile/registry test module if needed.

**Acceptance gates:**

1. A v2 fixture/snapshot continues to validate only under its existing v2
   contract; it is not upgraded, migrated, or interpreted as v3.
2. A v3 candidate requires `provenance/`, immutable `P_g`, `M_g`, `T_g`, and
   the required history/graph/profile bindings; missing or partial registry
   state is blocked or quarantined.
3. Registry manifest validation and capture-evidence validation are separate
   calls with separate failure outcomes; a valid sidecar cannot satisfy a
   missing or invalid registry manifest.
4. The exact Restic selection/tree tuple is retained as evidence for later
   workflow use; “most complete” or automatic snapshot election is rejected.
5. No migration, live write, restore replacement, authority activation, or
   serving change occurs in focused execution tests.

**Evidence required:** exact test command/output at the task tip; v2 legacy
fixture pass; v3 valid/invalid registry fixtures; sidecar-versus-manifest
negative control; profile and writer-census report; `docs/RECOVER.md` and V8i
wording diff; `git diff --check`; changed-file inventory.

**HITL stop:** Cursor stops after T1 evidence. Ryan must grant T2 separately;
no v2-to-v3 conversion or live snapshot is permitted.

### T2 — authority recovery and projection agreement state machine

**Deliverable:** Recovery states and transitions that verify the complete v3
registry before authority publication and qualify JSONL/Chroma only as exact
projections of the selected authority.

**File/surface scope:**

- A narrow registry/recovery authority surface integrated with the T1 validator
  and existing provenance commitment/recursive verification contracts.
- Existing generation/manifest metadata and projection read/qualification
  boundaries; no redesign of CG-2 serving authority.
- Focused tests for complete registry, missing history/graph, missing Chroma,
  stale projection, commitment mismatch, generation mismatch, and stale
  fallback attempts.

**Acceptance gates:**

1. The selected registry directory, manifest, object identities, commitments,
   graph, and historical semantic registries validate before recovered
   authority publication.
2. JSONL and Chroma agreement checks cover logical assertion-ID sets,
   provenance commitments, generation ID, manifest commitment, and projection
   binding.
3. A valid authority with unavailable/rebuildable projections becomes
   `AUTHORITY_RECOVERED_PROJECTION_PENDING` and remains non-serving.
4. Broken or stale projections are quarantined; no prior projection can serve
   against a newer authority, and no projection can mint or elevate identity.
5. Missing/invalid authority becomes `BLOCKED`, `QUARANTINED`, or
   `PROVENANCE_STORE_UNAVAILABLE` as specified; it does not silently degrade
   the live authority or use a stale fallback.

**Evidence required:** state-transition table exercised in isolated fixtures;
whole-registry and projection-agreement reports; negative controls for missing
history, mixed generations, stale projection, and sidecar substitution; exact
focused test output; no-live-state assertion.

**HITL stop:** Cursor stops at the state-machine evidence. Serving activation
and any CG-2 pointer publication remain separately gated and are not implied by
T2 completion.

### T3 — bounded bulk-recovery workflow and no-live-change safety contract

**Deliverable:** A scratch-only, explicitly Ryan-gated recovery workflow that
selects and validates one exact v3 Restic snapshot/tree and can prepare a
replacement candidate without mutating live authority.

**File/surface scope:**

- `backup_workflows.py`, `restic_snapshot.py`,
  `scripts/complete_data_restore_preflight.py`, and their focused tests.
- Isolated restore targets, machine-readable reports, grant/precondition
  records, and the existing live-replacement boundary in `docs/RECOVER.md`.
- No live `CONVMEM_DATA_ROOT`, Chroma, registry, selector, or serving pointer
  operation.

**Acceptance gates:**

1. The workflow refuses to run as an authority-changing operation without a
   fresh, explicit Ryan grant naming the exact operation and target.
2. It selects one exact Restic snapshot/tree and proves the tuple
   `(restic_snapshot_id, restic_root_tree_id, T_g, P_g, M_g)` before reading or
   combining authority components.
3. Missing, partial, mismatched, or invalid authority leaves live authority
   unchanged and produces observable blocked/quarantined evidence.
4. Item-by-item imports cannot preserve caller IDs or act as a substitute for
   registry recovery. A valid registry with unavailable projections remains
   projection-pending and non-serving.
5. Existing v2 snapshots remain usable under the v2 contract and are not
   migrated, upgraded, or reinterpreted as v3.

**Evidence required:** isolated scratch-root fingerprints before/after;
exact-snapshot selection record; grant and expected-current precondition record;
valid, missing, partial, mixed-tree, and item-import negative controls; live-root
nonmutation proof; report showing pending/blocked state; focused test output.

**HITL stop:** Cursor stops before any live replacement or authority activation.
Ryan must separately authorize live operations, and that authorization is not
part of this plan.

### T4 — recovery-side interruption and crash closure

**Deliverable:** Narrow recovery-side fault-injection evidence for durable
registry writes, selector/state publication, recovery transitions, projection
rebuild/qualification, and bounded publication fences.

**File/surface scope:**

- Recovery-side durable-write, rename, manifest, selector/state, projection
  qualification, and publication boundaries introduced by T1–T3.
- Existing generation durability/fault-test conventions may be reused; no
  change to CG-2 implementation or activation semantics.
- Focused fault-injection tests and machine-readable closure evidence.

**Acceptance gates:**

1. Each declared recovery-side interruption boundary is exercised, including
   writes, fsync/rename, manifest seal, selector publication, recovery state
   transition, projection rebuild/qualification, and publication handoff.
2. Every injected interruption closes to either the prior complete authority
   plus valid serving fence, or a complete replacement explicitly
   pending/blocked. Mixed registry/projection/selector state is never serving.
3. A stale projection, partially selected generation, missing pointer, or stale
   fallback is rejected or quarantined.
4. The test campaign remains recovery-side and bounded; it does not become the
   later broad T5 fault-injection/endurance campaign.
5. No live corpus, Chroma, registry, selector, pointer, or serving activation
   occurs during evidence collection.

**Evidence required:** boundary inventory; fault matrix with one result per
   boundary and transition; prior-state/complete-replacement fingerprints;
   mixed-state and stale-fallback negative controls; exact focused test output;
   scope proof excluding broad T5.

**HITL stop:** T4 completion returns to Kiro/Ryan review; it does not open T5,
CG-2 activation, or live recovery.

### D1 / V4k — selected-generation and rollback continuity (**BLOCKED**)

**Contract to plan, not executable work:** V4k may define the interface against
the locked CG-1 foundation inherited by CG-2. Its later evidence must bind an
exact selected generation/tree/manifest tuple, expected-current authority, fresh
Ryan grant, and an independent continuity witness linking the previously
accepted generation to the rollback target. The rollback operation must remain
distinct from same-pointer durability recovery and must record reconciliation
when the source has advanced.

**Blocking condition:** V4k execution cannot open until CG-2 Design A is
ratified and its generation/pointer semantics are stable. The unlock packet must
name the exact Design A ratification revision and stable model. If Design A
changes generation semantics, this task must be amended to absorb that change
before any Cursor execution grant. Until then there is no V4k implementation,
rollback drill, pointer publication, or serving activation.

**Later surfaces/evidence:** bounded interfaces in the existing generation and
serving surfaces (`file_generation_pointer.py`, `file_generation_contract.py`,
`serving_authority.py`, and focused tests) plus the Recovery Authority binding;
exact target qualification, expected-current CAS, independent witness, fresh
grant identity, source-advance reconciliation, and no-auto-rollback negative
controls.

**HITL stop:** Kiro/Ryan must first accept the dependency unlock and issue a
separate V4k Execute grant. A label of `DEFERRED` alone is insufficient; this
task is explicitly `BLOCKED`.

## 5. Evidence requirements for the later Execute phase

Every task must report:

- exact implementation tip SHA and branch/worktree;
- task-specific focused tests plus relevant existing regression tests;
- `convmem doctor`, `git diff --check`, and changed-file inventory where
  applicable;
- fixture/report paths or machine-readable evidence, not chat-only claims;
- explicit negative controls for v2/v3 confusion, sidecar substitution,
  missing/partial authority, mixed generations, stale projections, stale
  fallback, item-by-item identity import, and interruption closure;
- a declaration that no live corpus, Chroma, provenance authority, CG-2
  pointer, Shadow, R2b, migration, or T5 operation occurred unless a separate
  Ryan grant names it.

Existing oracles are reused. New evidence is justified only for the distinct
failure windows owned by V4g–V4l; no duplicate governance ceremony is added.

## 6. HITL and Execute entry

The active phase ends here. The next lane is Kiro Execution Plan review. Kiro
should return exactly one of `PASS`, `PASS WITH REQUIRED AMENDMENTS`, or
`FAIL`, checking task boundaries, V4k blocking, v2/v3 coexistence, predeclared
evidence, T5 containment, VERIFY authority, and no implicit activation.

After Kiro review, Ryan decides whether to accept the plan and issue one
separate Execute grant at a time. The first eligible task is T1 only after that
grant. D1/V4k is not eligible even after this plan passes until its CG-2 Design
A dependency is ratified and stable.

No self-transition to Execute is permitted by this artifact.

## 7. Arc VERIFY companion

- **Path:** [`docs/plans/VERIFY-recovery-authority.md`](VERIFY-recovery-authority.md)
- **Status:** planning companion; no execution evidence or PASS claims
- **Authority relationship:** it maps Recovery Authority task evidence onto the
  existing authoritative V4g–V4l, V8i/V8j/V8l, V6, and V7 rows in
  [`VERIFY-dependability-provenance.md`](VERIFY-dependability-provenance.md).
  It does not duplicate, fork, or silently supersede those rows.
- **Template basis:** [`docs/plans/VERIFY-TEMPLATE.md`](VERIFY-TEMPLATE.md)

The companion explicitly carries the v3 terminology required by the locked
architecture. The existing source row IDs and substantive oracles remain the
authority; any later wording correction (including V8i v2→v3) must preserve
the row identity and oracle substance.

## 8. Out of scope and stop condition

This plan does not authorize implementation, migration, restore, live-data
mutation, provenance-authority activation, CG-2 activation, Shadow, R2b, V1h,
V3i, T5, downstream promotion, T3 reopening, merge to main, or any direct
DeepSeek R1 adversarial API call.

**Stop condition:** Once this package is committed and pushed on
`plan/2026-08-22-recovery-authority`, stop for Kiro Execution Plan review →
Ryan. Do not self-transition to Execute.

**TL;DR:** Four serial Cursor tasks cover v3 substrate, authority/projection
recovery, scratch-only bulk workflow, and narrow crash closure; D1/V4k is
genuinely BLOCKED on CG-2 Design A ratification and stable generation/pointer
semantics. [Arc Recovery Authority]
