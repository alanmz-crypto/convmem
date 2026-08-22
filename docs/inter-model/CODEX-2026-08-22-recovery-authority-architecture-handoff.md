# Codex Handoff — Recovery Authority Architecture Planning

**Arc:** Recovery Authority
**Date:** 2026-08-22
**From:** OpenAI Codex architecture-author lane
**To:** Kiro architecture review/sign-off → Ryan Architecture Lock
**Branch:** `plan/2026-08-22-recovery-authority`
**Review package SHA:** to be filled after the package commit; the immutable
baseline is `c1fac4c2c40662d9d1f88a1a020835feecce682b`
**State:** `READY_FOR_KIRO_REVIEW`
**Push status:** branch created from and pushed against the exact baseline;
package commit will be pushed immediately after commit

## Planning status

```text
Phase:        Architecture Planning
Characters:   Architect, Systems Thinker, Risk Reviewer
Functions:    Planner
Lanes:        Codex authors; Kiro reviews; Ryan approves (HITL)
Authority:    Awaiting Kiro review/sign-off and Ryan Architecture Lock
```

## Consequence

The package turns the deferred V4g–V4l obligations into one bounded Recovery
Authority direction while keeping each row separately executable downstream.
It gives complete-data recovery one authoritative provenance-generation
contract, makes JSONL and Chroma projections subordinate to that authority,
and defines fail-closed recovery/projection/serving states. It does not
implement recovery, alter live data, activate CG-2, or create an execution
grant.

## Authorization and scope

Ryan authorized architecture planning/documentation only from the verified
baseline named above. This package does not authorize:

- implementation, migration, bulk restore, live-data mutation, or provenance-
  authority activation;
- CG-2 activation, Shadow, R2b, V1h, V3i, downstream promotion, or T3 reopening;
- a new generic planning guide, Pre-Architecture Challenge phase, or new
  governance/document class;
- a dedicated DeepSeek R1 direct-provider/API adversarial call;
- execution-plan task shaping before Kiro review/sign-off and Ryan lock.

The later broad T5 fault-injection campaign remains outside V4l. V4l owns the
recovery-side interruption and crash-closure invariants only.

## Evidence packet

### Exact baseline and repository facts

**Baseline:** `origin/main = c1fac4c2c40662d9d1f88a1a020835feecce682b`.

The following are **OBSERVATION** unless marked otherwise:

| Observation | Evidence | Why it matters |
|---|---|---|
| `complete_data_restore.py` has a closed `STATE_SPECS` table and classifies unknown top-level names as unclassified. `writer_census_for_root()` derives its authority map from that table. | `complete_data_restore.py:279-294`, `:1293-1356` | V4g must add the provenance path to the existing closed restore contract; an unregistered path is not safe by default. |
| `.convmem-backup-evidence.json` is explicitly evidence-only and never a repair source. | `complete_data_restore.py:397-403`; `docs/RECOVER.md:81-88` | V4h must keep capture evidence separate from registry authority. |
| The current recovery guide says the future registry is not a durable restore surface and names the required integration points. | `docs/RECOVER.md:109-120` | This is the deferred seam that Recovery Authority materializes. |
| Existing complete-data-v2 restore outcomes are ordered `BLOCKED > REPAIRABLE > ADVISORY > VALID`, and validators do not repair. | `docs/RECOVER.md:66-88` | Recovery must classify first and keep repair/rebuild outside authority publication. |
| JSONL is the durable leader and Chroma is an asynchronous, rebuildable follower in the repository's dataflow model. | `docs/builder-reference/ddia-builder-digest.md`; `docs/builder-reference/hard-parts-builder-digest.md` | The provenance registry must not become a second content ledger, and Chroma must not become authority. |
| CG-1/CG-2 architecture already separates pointer-selected serving authority from legacy compatibility, requires request-frozen authority resolution, and rejects pointer/manifest mismatch. | `docs/plans/ARCHITECTURE-cg2-production-activation.md:58-76`, `:161-221`, `:390-427` | V4k can define a bounded adapter contract without redesigning CG-1 or assuming unratified CG-2 execution semantics. |
| The existing CG-2 Design A architecture requires an exact retained rollback baseline, explicit rollback, monotonic fencing, and no legacy resurrection after a durable fence. | `docs/plans/ARCHITECTURE-cg2-production-activation.md:476-534`, `:769-795` | V4k must bind to these semantics where they are locked, while deferring execution until the amendment is ratified. |
| Existing verification rows already define V4g–V4l, V8i–V8l, V6a–V6e, and V7d–V7e as pending later-gate or cross-arc oracles. | `docs/plans/VERIFY-dependability-provenance.md:136-210`, `:240-257` | Recovery Authority reuses these acceptance-oracle families rather than inventing a duplicate VERIFY system. The current V4g/V8i wording says `complete-data-v2`; the chosen v3 direction requires that profile label to be retargeted before execution, not silently treated as a v2 extension. |

The following are **INFERENCE** from those observations and the accepted
planning scope:

- A provenance-aware recovery cannot safely be represented as an optional
  extension of historical complete-data-v2 snapshots: old v2 trees do not
  contain the registry and must not be mistaken for authority-complete trees.
- The least-surprising safe direction is a new complete-data profile/version
  whose validator requires a registry generation and its binding commitment,
  while legacy v2 remains valid only for its existing corpus/recovery contract.
- Recovery publication needs one mutable selector/state record over immutable
  registry generations; independently replaceable files cannot safely express
  a single selected authority/projection tuple.

### Evidence provenance by lane

| Lane | Evidence state | Classification and use |
|---|---|---|
| **Crush** | The CG-1 closure packet records an independent Crush review at reviewed SHA `2ed229244ea1d7cdf9a83630ad56d5a194426826`, including fresh-process qualification, owner/generation/manifest binding, request-frozen row reads, and 1,284 passed plus 230 subtests. | **OBSERVATION / AGREED inherited evidence.** It is used only to preserve the locked CG-1 substrate and its boundary; it is not a Recovery Authority sign-off. Source: [`CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md`](CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md). |
| **Crush repository facts for V4g–V4l** | No separate V4g–V4l Crush packet is present on the baseline. Codex rechecked the cited files and records those checks as Codex observations, not as a relabeled Crush result. | **UNKNOWN for a dedicated new Crush packet; no missing result is silently synthesized.** |
| **DeepSeek R1** | No recovery-specific independent R1 artifact is present in the baseline evidence packet. | **DEFERRED/UNKNOWN.** Architecture Planning did not implicitly authorize a dedicated R1 direct API/provider call, so no R1 result is claimed. Routine local Ollama and ordinary ConvMem retrieval remain allowed. |
| **Kiro** | The authorization carries two binding Kiro amendments; no Kiro review/sign-off has yet been issued against this Recovery Authority package. | **Governing reconciliation carried forward; review/sign-off pending.** The amendments are binding constraints, not a fabricated Kiro verdict. |
| **GitHub Copilot audit lane** | Baseline inspection did not leave an unresolved allow-listed safety/isolation or code-grounded feasibility question. The remaining CG-2 question is a ratification dependency, not a Copilot trigger. | **Explicit skip.** No Copilot audit was invoked for planning-only documentation. |
| **ChatGPT** | No separate strategic review was requested for this package. | **Normalization only.** No ChatGPT verdict or architecture decision is imported. |
| **Codex** | Codex authors the formal Architecture Direction after the above evidence/reconciliation boundary. | **Current lane and artifact owner.** |

### Inherited closed invariants

Recovery Authority inherits without reopening or redefining:

- `provenance-envelope-v1` canonical envelope semantics;
- integrity-meet semantics and conservative integrity lattice;
- assertion identity/commitment semantics, including monitor-minted immutable
  identity, parent ID/commitment edges, and no identity-preserving caller
  replay without a valid pair;
- bounded recursive verification, including fail-closed missing-parent,
  cycle, history, binding, and budget behavior;
- T3's explicit limit that provenance integrity is not factual truth, ranking,
  recency, serving authority, migration authority, or downstream action
  permission;
- T3 closure and the accepted V4m consistency boundary.

### Ownership map

| Row | Recovery Authority ownership | Separate downstream gate |
|---|---|---|
| V4g | Complete-data recovery-profile integration: required registry path, closed StateSpec/census registration, and recovery documentation boundary. | Complete-data implementation/verification. |
| V4h | Separate registry-manifest/graph validator versus capture-evidence validator. | Validator implementation/verification. |
| V4i | Whole-registry validation, history/graph/commitment checks, projection agreement, and projection-pending state. | Authority recovery implementation/verification. |
| V4j | Ryan-gated bulk recovery and no-live-change behavior for missing/partial authority; no item-by-item identity import. | Operational recovery grant and verification. |
| V4k | Selected-generation binding, rollback-continuity contract, and bounded CG-1/CG-2 interfaces. | CG-2 Design A ratification first; then a separate V4k execution gate. |
| V4l | Recovery-side interruption/crash-closure/publication invariants across registry, projection, and serving-state transitions. | Narrow recovery interruption verification; not the later broad T5 campaign. |

### Existing acceptance oracles

The package keeps the existing oracles as the downstream truth source:

- V4g–V4j: restore-preflight registration, separate validator, whole-registry
  completeness, and bulk-recovery negative controls;
- V4k: one selected complete-data generation/manifest commitment, independent
  rollback continuity evidence, exact grant identity, and no mixed generations;
- V4l: interruption at every listed durable/publication boundary leaves either
  the prior complete serving state or a complete replacement explicitly
  projection-pending/blocked;
- V8i–V8l: valid registry with missing projection, missing/partial registry,
  stale history, and registry/JSONL/Chroma disagreement;
- V6a–V6e and V7d–V7e: CG-1 commitment continuity and CG-2 request-frozen
  serving integration;
- V9e/V9f/V9g: no live mutation, runnable grant documentation, and reuse of
  existing governance rather than ceremony duplication.

## Findings and reconciliation state

| Finding | State | Disposition |
|---|---|---|
| The provenance registry must be a durable authority inside the explicit complete-data root. | **AGREED** | Adopted as the Recovery Authority boundary. |
| JSONL and Chroma alone cannot preserve or mint identity. | **AGREED** | They remain projections/rebuild surfaces. |
| Capture sidecar evidence and registry authority are interchangeable. | **DISPUTED** | Rejected; V4h requires independent validators. |
| Historical complete-data-v2 can be silently upgraded to provenance-complete authority. | **DISPUTED** | Rejected; choose a new profile/version. |
| Existing V4g/V8i oracle labels can remain `complete-data-v2` after the architecture chooses v3. | **DISPUTED** | The oracle semantics are retained, but downstream VERIFY/Execution Planning must retarget the profile label to `complete-data-v3` before execution; this planning package does not edit or promote the inherited VERIFY file. |
| Exact registry on-disk file layout and implementation module. | **UNKNOWN** | Architecture fixes the contract and selector semantics; execution must choose concrete files/modules. |
| Whole-registry graph/history validator implementation and complexity bounds. | **UNKNOWN** | Downstream execution design; must satisfy the existing R8/V4/V8 oracles. |
| CG-2 generation/pointer semantics are stable enough for V4k execution. | **DEFERRED** | V4k interface is documented now; execution waits for CG-2 Design A ratification and model stability. |
| Dedicated DeepSeek R1 adversarial result for this cycle. | **DEFERRED** | Direct call not authorized; no result claimed. |
| Copilot safety/feasibility audit required for this planning package. | **AGREED SKIP** | No unresolved allow-listed code-grounded question remains. |

## Kiro governing reconciliation (binding amendments)

These amendments are carried from Ryan's authorization as binding Kiro
requirements. They are not a final Kiro review of this package:

1. **V4k/CG-2 dependency:** V4k architecture may define the rollback/
   continuity contract against the locked CG-1 foundation inherited by CG-2,
   but V4k's execution gate cannot open until the CG-2 Design A amendment is
   ratified and its generation/pointer model is stable. If CG-2 Design A changes
   generation semantics, V4k must absorb that change before execution.
2. **Model-call boundary:** Architecture Planning does not implicitly authorize
   dedicated DeepSeek R1 direct-API adversarial calls. Routine Tier-A
   capabilities remain unaffected, including local Ollama inference and
   ordinary ConvMem `ask` retrieval synthesis. The restriction applies only to
   the special R1 adversarial architecture call.

**Required evidence/handoff classification:**

> V4k execution interface with CG-2 generation/pointer model: **DEFERRED
> pending CG-2 Design A ratification.**

This dependency does not block opening or authoring Recovery Authority
architecture.

## Questions Codex decides in the Architecture Direction

- whether provenance-aware complete recovery uses a new complete-data profile/
  version or an extension of v2;
- the provenance-authority versus corpus/content-authority boundary;
- generation/manifest commitments and the selected Restic tree binding;
- whole-registry validation and projection agreement semantics;
- rollback continuity/freshness evidence requirements;
- recovery/projection/serving states and crash-closure/publication invariants;
- the bounded interface shape that keeps V4k dependent on, but not coupled to,
  unratified CG-2 execution details.

## Questions Codex is not authorized to decide

- whether Ryan grants a dedicated DeepSeek R1 direct/API call;
- whether Kiro signs off or Ryan locks this architecture;
- when CG-2 Design A is ratified or whether its generation/pointer model changes;
- any implementation module/file layout, migration, restore, pointer publication,
  live replacement, activation, or fault-injection execution;
- reopening T3 or changing V1h, V3i, CG-2 activation, Shadow, R2b, or T5 scope.

## Review reading

- [`ARCHITECTURE-recovery-authority.md`](../plans/ARCHITECTURE-recovery-authority.md)
- [`ARCHITECTURE-dependability-provenance.md`](../plans/ARCHITECTURE-dependability-provenance.md)
- [`VERIFY-dependability-provenance.md`](../plans/VERIFY-dependability-provenance.md)
- [`ARCHITECTURE-cg2-production-activation.md`](../plans/ARCHITECTURE-cg2-production-activation.md)
- [`RECOVER.md`](../RECOVER.md)
- [`STATUS-dependability-provenance.md`](../plans/STATUS-dependability-provenance.md)

## Leaving / picking up

**Codex (leaving):**

- [x] Architecture Direction authored on the exact baseline branch.
- [x] Evidence provenance, OBSERVATION/INFERENCE split, inherited invariants,
      ownership map, existing oracles, findings classifications, model-call
      boundary, and Kiro reconciliation recorded.
- [x] No implementation, restore, migration, activation, or execution plan
      performed.
- [ ] Fill the final package SHA after commit and push.

**Kiro (picking up):**

- [ ] Independently verify the branch tip and exact baseline.
- [ ] Review the single chosen direction and the Kiro amendments for invariant
      completeness; issue PASS/FAIL or requested amendments.
- [ ] Do not implement runtime code or grant execution.

**Ryan (after Kiro):**

- [ ] Decide Architecture Lock or return a bounded revision request.
- [ ] Separately authorize any future Execution Planning or CG-2/V4k gate.

I finished: [Arc Recovery Authority] evidence and architecture handoff package
Next step: Kiro reviews the exact package and issues architecture amendments or sign-off
Next lane: Kiro → Ryan
See my work: [`ARCHITECTURE-recovery-authority.md`](../plans/ARCHITECTURE-recovery-authority.md)

**TL;DR:** Recovery Authority is a new planning-only arc for V4g–V4l; the evidence packet preserves the complete-data/provenance and CG-1 facts, records R1 as unauthorized/deferred and Copilot as an explicit skip, carries Kiro's binding amendments, and stops at Kiro review.
