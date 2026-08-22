# Verify Plan — Recovery Authority

**Arc:** Recovery Authority  
**Phase:** Pre-Execute VERIFY companion  
**Status:** Planning companion only; no implementation evidence and no PASS claims  
**Architecture:** locked at `22852a07e66920874045e0e85c4572ab6c0b29b8`  
**Execution plan:** [`EXECUTION-recovery-authority.md`](EXECUTION-recovery-authority.md)  
**Baseline:** `origin/main` at `c1fac4c2c40662d9d1f88a1a020835feecce682b`  
**Authority:** Existing [`VERIFY-dependability-provenance.md`](VERIFY-dependability-provenance.md) owns the canonical row IDs and substantive oracles; this file maps this arc's task evidence onto them.

## Planning Status

```text
Phase:        Verify companion prepared during Execution Planning
Characters:   Independent Reviewer
Functions:    Define post-Execute evidence and row mapping
Lanes:        Cursor supplies mechanical evidence; Kiro reviews; Ryan gates
Authority:    Post-Execute HITL — not active yet
```

## Human consequence

This companion gives Kiro one Recovery Authority checklist without creating a
second oracle table. When later filled, it will prove the four executable tasks
against the existing V4/V8/V6/V7 rows and will keep V4k visibly blocked until
CG-2 Design A is ratified. It is not evidence that any task has executed.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor will produce task evidence later; Kiro independently reviews it; Ryan owns the gate. |
| **What** | A mapping and evidence contract for V4g–V4l Recovery Authority work. |
| **When** | Authored with the Execution Plan, before Execute. |
| **Why** | The canonical dependability VERIFY already owns these oracles but the new arc needs bounded task-to-oracle traceability. |
| **How** | Map by row ID, preserve the source oracle, carry v3 profile terminology, and record no PASS until exact execution evidence exists. |

**TL;DR:** This file is a review-ready VERIFY companion, not a verification
result.

## Authority relationship and v2/v3 retarget

`docs/plans/VERIFY-dependability-provenance.md` remains the authoritative
owner of V4g–V4l, V8i/V8j/V8l, V6, and V7 row identity and substantive oracle
meaning. This companion does not copy those rows into a competing checklist
and does not promote their current `PENDING` results.

The Recovery Authority interpretation is explicitly **complete-data-v3**:

- V4g/V8i provenance-aware recovery evidence must name v3, not v2.
- The existing complete-data-v2 contract and snapshots remain valid for their
  existing legacy recovery purpose and are not migrated, upgraded, or
  reinterpreted.
- The later documentation closure must retarget the V8i provenance-aware
  profile label from v2 to v3 while preserving the V8i row identity and
  substantive oracle. If the canonical source row is edited, it must remain a
  single row; this companion is not a substitute or silent fork.
- The `docs/RECOVER.md` provenance-aware wording must likewise use v3 where the
  new authority contract applies, while retaining explicit v2 legacy wording.

## Scope lock

| In scope | Out of scope |
|---|---|
| V4g–V4j complete-data-v3/registry recovery, V4l recovery-side crash closure, and the blocked V4k contract | Implementation, migration, live restore/replacement, authority activation, CG-2 activation, Shadow, R2b, V1h, V3i, T3 reopening, broad T5 campaign |
| Reuse of V4g–V4l/V8/V6/V7 authoritative rows | New generic VERIFY governance class or duplicate oracle definitions |
| Exact task-level evidence, negative controls, and HITL stop points | PASS claims before later Execute evidence and independent Kiro review |

## Verification design

| Field | Answer |
|---|---|
| **Independent oracle** | Existing `VERIFY-dependability-provenance.md` rows plus exact fixture/report evidence at the implementation SHA; no chat-only claims. |
| **Failure-injection method** | Isolated missing/partial/mixed registry and projection fixtures; exact snapshot/tree mismatch; sidecar substitution; stale fallback; per-boundary recovery interruption injection for V4l. |
| **Negative control** | v2 labeled as v3; v3 registry omitted; valid sidecar with invalid registry; mixed `P_g/M_g/T_g`; stale JSONL/Chroma; caller-ID item import; crash at each durable boundary. Each must block, quarantine, remain pending, or close to prior complete state as specified. |
| **Dual-path coverage** | Scratch restore/preflight and recovery authority/projection paths; CG-2 serving remains a later bounded handoff and is not claimed here. |

## V0 — Planning and preconditions

| ID | Check | Planned result |
|---|---|---|
| V0a | Exact locked architecture bytes are `22852a07e66920874045e0e85c4572ab6c0b29b8`; carrier `a133629f96cc34c4df2fda2730b5bcb272d743da` is not a replacement architecture revision | Required before Execute; no result yet |
| V0b | Execution Plan is reviewed by Kiro at one exact committed tip | Required; pending |
| V0c | Ryan issues separate Execute grants per eligible task | Required; pending |
| V0d | V4k remains blocked until exact CG-2 Design A ratification and stable generation/pointer semantics are recorded | Required; currently BLOCKED |
| V0e | No live mutation, migration, activation, or broad T5 operation occurred | Required evidence; no result yet |

## Task-to-authoritative-oracle mapping

| Plan task | Canonical authoritative rows | Evidence to carry here later | Planning disposition |
|---|---|---|---|
| **T1** v3 profile and registry substrate | V4g, V4h, V8i, V9e, V9f | v3 profile/registry fixtures; v2 legacy compatibility; separate manifest/sidecar failures; `P_g/M_g/T_g`; `docs/RECOVER.md`; V8i v3 wording; no-live proof | Pending later Execute |
| **T2** authority recovery/projection state machine | V4i, V8i, V8l, V7d, V7e | Whole-registry/history/graph validation; exact JSONL/Chroma agreement; pending/blocked/quarantine states; stale-projection negative controls | Pending later Execute; V7 remains later CG-2 scope where applicable |
| **T3** bounded bulk recovery/no-live-change workflow | V4j, V8i, V8j, V9e, V9f | Exact Restic snapshot/tree binding; fresh grant/preconditions; scratch fingerprints; missing/partial authority; item-import rejection; v2 non-migration | Pending later Execute |
| **T4** recovery crash closure | V4l, V9e, V9g | Boundary inventory; interruption matrix; prior-complete or complete-pending/blocked closure; mixed/stale fallback negatives; T5 exclusion | Pending later Execute |
| **D1 / V4k BLOCKED** selected generation/rollback continuity | V4k; bounded interfaces to V6a–V6e and V7d–V7e | Exact Design A unlock; exact target and expected-current tuple; fresh Ryan grant; independent continuity witness; source-advance reconciliation; no-auto-rollback | **BLOCKED — no execution evidence may be produced** |

### Row preservation rules

- The existing V4g–V4l and V8 rows remain the oracle source. This companion
  records mapping, not a new acceptance standard.
- V8i's substantive oracle is unchanged: a valid provenance-aware recovery may
  be projection-pending, while projection-backed serving remains blocked. Only
  the provenance-aware profile label is retargeted to v3 in later documentation
  closure.
- V4k does not become executable because T1–T4 pass. Its CG-2 dependency is a
  hard gate.
- V6/V7 rows remain separately owned downstream CG-1/CG-2 assurance. Their
  mapping here is an interface trace, not a claim that this arc closes those
  tracks.

## Later report format

For each task, a post-Execute fill must state `PASS`, `FAIL`, or `SKIP` only with
one line of exact evidence and the subject tip SHA. An applicable SHA mismatch
is `FAIL`, never `SKIP`. No verifier may repair or silently broaden scope.

| ID | Check | Result at planning time |
|---|---|---|
| T1 evidence | v3 substrate and documentation obligations | NOT RUN |
| T2 evidence | authority/projection state machine | NOT RUN |
| T3 evidence | bounded scratch workflow and no live change | NOT RUN |
| T4 evidence | recovery-side crash closure | NOT RUN |
| D1/V4k evidence | selected generation/rollback continuity | BLOCKED |
| Kiro plan review | plan boundary and evidence review | PENDING |
| Ryan Execute gate | separate grants | PENDING |

## Sign-off and evidence log

```text
VERIFY-recovery-authority — planning companion — no execution evidence
Architecture bytes: 22852a07e66920874045e0e85c4572ab6c0b29b8
Carrier tip: a133629f96cc34c4df2fda2730b5bcb272d743da
T1–T4: NOT RUN
D1/V4k: BLOCKED pending CG-2 Design A ratification and stable semantics
Mechanical: NOT RUN
Kiro Execution Plan review: PENDING
Ryan Execute gate: PENDING
```

**TL;DR:** Recovery Authority reuses the canonical V4/V8/V6/V7 oracles,
retargets provenance-aware terminology to v3 without implicit migration, and
keeps V4k BLOCKED; no verification result is claimed. [Arc Recovery Authority]
