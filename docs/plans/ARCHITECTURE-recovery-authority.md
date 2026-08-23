# Architecture Direction — Recovery Authority

**Arc:** Recovery Authority
**Scope:** V4g–V4l deferred obligations
**Source:** Ryan's Recovery Authority Architecture Planning Authorization
**Baseline:** `origin/main` at `c1fac4c2c40662d9d1f88a1a020835feecce682b`
**Author:** OpenAI Codex architecture-author lane
**Authority:** Awaiting Kiro architecture review/sign-off → Ryan Architecture Lock
**Phase:** Architecture Planning only

This document is the formal Architecture Direction. The evidence, lane
provenance, findings classification, and governing reconciliation are carried
in the [Codex Recovery Authority architecture handoff](../inter-model/CODEX-2026-08-22-recovery-authority-architecture-handoff.md).

## Planning status

```text
Phase:        Architecture Planning
Characters:   Architect, Systems Thinker, Risk Reviewer
Functions:    Planner
Lanes:        Codex authors; Kiro reviews; Ryan approves (HITL)
Authority:    Awaiting HITL
```

## Human consequence

If this direction is approved and later executed under separate grants, a
complete-data recovery can restore provenance authority without mistaking a
capture sidecar, JSONL export, or Chroma projection for that authority. A
recovered registry can remain safely projection-pending while projections are
rebuilt, and rollback can name one exact generation with an independently
anchored continuity witness. An interruption cannot publish a mixed registry,
projection, and serving state.

No part of this document authorizes implementation, migration, bulk restore,
live-data mutation, provenance-authority activation, CG-2 activation, Shadow,
R2b, V1h, V3i, downstream promotion, T3 reopening, or the later broad T5
fault-injection campaign.

## 1. Intake

V4g–V4l are deferred recovery obligations that need a shared direction before
they can be shaped into separately executable work. They are a new Recovery
Authority architecture cycle, not unfinished T3 work. Architecture Planning is
required because the obligations cross complete-data restore, provenance
authority, projections, selected generations, rollback continuity, and crash
publication boundaries; task shaping before those ownership and state choices
would leave material forks unresolved.

## 2. System boundary

### In scope

- V4g complete-data recovery-profile integration for a durable provenance
  registry;
- V4h separate registry-authority validation versus capture-evidence
  validation;
- V4i whole-registry recovery validation, policy/recipe/history and graph
  completeness, projection agreement, and projection-pending semantics;
- V4j Ryan-gated bulk authority recovery, live-authority preservation on
  failure, and rejection of item-by-item identity-preserving import;
- V4k selected complete-data generation binding, rollback-continuity evidence,
  and bounded interfaces to the locked CG-1 foundation and CG-2 pointer model;
- V4l recovery-side interruption, crash closure, atomic publication, and
  no-mixed-state invariants;
- shared contracts that let each row remain a separately executable downstream
  obligation.

### Out of scope or deferred with owner

- T3 substrate changes, including `provenance-envelope-v1`, integrity-meet,
  assertion identity/commitment, bounded recursive verification, and the
  conservative integrity lattice;
- V1h verified ingress bootstrap and V3i migration;
- semantic dedupe, temporal/belief revision, claim-level attribution/support,
  and downstream promotion;
- the CG-2 implementation or activation grant; V4k execution is deferred until
  CG-2 Design A is ratified and its generation/pointer model is stable;
- Shadow, R2b, live restore/replacement, provenance-authority activation, or
  any live-data mutation;
- the later broad T5 fault-injection/endurance campaign;
- execution task decomposition, implementation module selection, and
  operational runbook authoring.

## 3. Existing constraints and inherited invariants

### Repository constraints

The baseline's complete-data restore policy is a closed `StateSpec` matrix.
`writer_census_for_root()` classifies top-level paths from that matrix and
unknown names as unclassified (`complete_data_restore.py:279-294,
:1293-1356`). Validators classify and report; they do not repair. The recovery
guide currently says the future registry must be added to `STATE_SPECS` and
`writer_census_for_root()`, validated separately, and checked before authority
publication (`docs/RECOVER.md:109-120`).

The existing complete-data-v2 contract uses the outcome precedence
`BLOCKED > REPAIRABLE > ADVISORY > VALID`, treats
`.convmem-backup-evidence.json` as evidence rather than authority, and keeps
live replacement behind a separate Ryan grant (`docs/RECOVER.md:66-107`).

The dataflow references establish a single-writer/content-ledger and
rebuildable-Chroma relationship. This direction preserves that ownership
shape: the provenance registry is a second authority for lineage/identity
evidence, not a second content ledger, and Chroma remains a projection.

CG-1 and the CG-2 architecture establish immutable generation identity,
pointer-selected serving authority, expected-active checks, retained previous
generations, request-frozen authority resolution, and fail-closed pointer or
manifest mismatch behavior (`docs/plans/ARCHITECTURE-cg2-production-activation.md:58-76`,
`:161-221`, `:390-427`). Recovery Authority consumes those contracts through a
bounded interface; it does not redefine them.

### Closed inherited provenance invariants

The following are inherited and intentionally not reopened:

- canonical `provenance-envelope-v1` and its semantic serializer;
- integrity is a conservative meet over completely bound inputs and a
  transformer cap; it is not factual truth;
- assertion identity is monitor-minted, content-independent, immutable, and
  commitment-bound;
- parent edges bind exact parent ID plus expected commitment, not equivalent
  content;
- recursive verification is bounded and fails closed on missing ancestors,
  cycles, unavailable history/bindings, mismatches, or budget exhaustion;
- a caller-supplied ID/commitment pair cannot overwrite, alias, or elevate
  identity when it is absent, malformed, or mismatched;
- ranking, recency, supersession, CG-1 durability, CG-2 serving, process
  attestation, and backup-capture evidence cannot self-upgrade provenance;
- T3 is closed. The accepted V4m consistency boundary remains inherited and
  is not silently reopened by recovery planning.

## 4. Architecture questions answered

This direction resolves the questions named in the authorization without
turning them into downstream task forks:

1. **Complete-data profile/version:** choose a new `complete-data-v3`
   provenance-complete profile. Historical `complete-data-v2` remains valid
   for its existing corpus/recovery contract but cannot authorize
   provenance-aware recovery. A v2 tree with no registry is therefore not
   silently upgraded or treated as a partially populated v3 tree.
2. **Authority boundary:** the content authority remains the canonical
   approved-decision/content ledger and its lifecycle controls. The provenance
   authority is the immutable registry generation containing assertion
   envelopes, IDs, commitments, parent edges, root evidence, policy history,
   recipe/transformer history, and its directory manifest. Neither authority
   proves factual truth. A content change and an identity/commitment mismatch
   are quarantined; neither side overwrites the other by convenience.
3. **Registry generation/manifest:** each immutable registry generation `P_g`
   has a stable generation ID and canonical manifest commitment `M_g`. The
   manifest names schema semantics, required objects/files, counts, canonical
   digests, policy/recipe-history digests, graph completeness, content-ledger
   binding, projection binding, and the complete-data tree commitment `T_g`.
   One atomic selector/state record names the currently selected `(P_g, M_g,
   T_g)` tuple; all generation contents are immutable after selection.
4. **Whole-registry validation:** preflight validates the selected v3 tree,
   manifest and every required object, unique IDs, ID/commitment agreement,
   recursive parent resolution, historical schema/policy/recipe availability,
   graph completeness, content-ledger binding, and generation/manifest
   continuity before authority recovery can publish. It never repairs in
   place.
5. **Projection agreement:** JSONL and Chroma are projections of the selected
   registry generation. When present, both must agree exactly on logical
   assertion-ID sets, provenance commitments, generation ID, manifest
   commitment, and the projection/profile binding. Chroma's rebuildable vector
   bytes remain subject to its own generation/qualification oracle; a missing
   or damaged projection blocks projection-backed serving but does not erase a
   verified registry authority.
6. **Restic snapshot/tree binding:** the selected v3 Restic snapshot is bound
   to the registry by the restored data-root tree commitment. `T_g` is the
   canonical hash of sorted `(relative path, size, SHA-256)` entries for all
   manifest-bound tree components, excluding only the mutable selector/state
   record and capture-evidence sidecar. The immutable registry manifest
   commits `T_g`; preflight recomputes it from the selected snapshot/tree and
   records the exact tuple `(restic_snapshot_id, restic_root_tree_id, T_g,
   P_g, M_g)`. A snapshot whose restored tree does not produce that tuple is
   rejected. The sidecar is never the binding authority.
7. **Rollback continuity/freshness:** rollback selects one exact retained
   generation and requires a fresh Ryan rollback grant, an expected-current
   authority tuple read at the publication boundary, and a continuity witness
   linking the previously externally accepted generation/manifest to the
   target generation/manifest, reason, and grant identity. The continuity
   witness cannot be derived only from the candidate being restored. A source
   that has advanced does not make an exact rollback candidate disappear; it
   produces an observable reconciliation-required condition rather than a
   legacy fallback.
8. **Recovery/projection/serving states:** authority recovery and projection
   recovery are separate states. A verified authority with no valid projection
   may be recovered only as projection-pending and cannot serve. Serving-ready
   requires exact projection agreement and an atomic serving-fence activation
   through the bounded CG-2 interface.
9. **Crash closure/publication:** immutable generations plus one atomic
   selector/state record are the publication mechanism. At every write, fsync,
   rename, manifest, selection, projection-rebuild, pointer, fence, rollback,
   and activation boundary, a crash leaves either the prior complete authority
   and valid serving fence or a complete replacement explicitly pending/blocked.
   It may not leave or expose a mixed generation, a partial manifest, a stale
   projection fallback, an auto-elected alternative, or a pointer without its
   qualification evidence.

## 5. Options considered

| Option | Summary | Benefits | Rejected because |
|---|---|---|---|
| A — Extend `complete-data-v2` in place | Add `provenance/` as a conditional v2 path and let the same profile describe both registry-bearing and registry-less snapshots. | Smallest apparent profile change; reuses current tags and restore entry points. | It makes historical v2 snapshots ambiguous, permits a profile labeled complete-data-v2 to mean two different authority contracts, and makes “missing registry” indistinguishable from a valid old v2 corpus. That weakens V4g/V4j fail-closed classification. |
| B — New `complete-data-v3` provenance-complete profile | Preserve v2 semantics; require a whole immutable registry generation, manifest, and tree commitment for v3 recovery. Keep JSONL/Chroma as projections. | Makes profile compatibility explicit, gives restore a closed discriminator, keeps rollback/recovery additive, and preserves v2 as a known lower-capability recovery path. | Requires a new profile validator and new snapshots for provenance-aware recovery; older v2 snapshots cannot be used for the new authority contract. |
| C — Separate provenance backup outside complete-data | Keep complete-data-v2 unchanged and back up the registry in a separate Restic profile/repository, joining it with corpus restore later. | Avoids changing the complete-data profile. | Creates two independently selected recovery roots, makes tree/generation agreement a second authority problem, and expands the rollback/crash surface. It conflicts with the existing complete-data root boundary. |

## 6. Chosen direction

Choose **Option B: a new `complete-data-v3` provenance-complete recovery
profile with one immutable registry-generation authority and projection-pending
publication**.

The v3 profile is the only profile allowed to produce a provenance-aware
recovery selection. It contains the normal complete-data-v2 durable corpus
paths plus `provenance/`, its immutable generation manifest, policy/recipe and
schema history, the canonical content/export surfaces, and any captured
projection components named by the v3 manifest. The registry is rooted at
`CONVMEM_DATA_ROOT/provenance/` and owns lineage/identity evidence. The content
ledger owns content and lifecycle state. JSONL exports and Chroma carry the
registry generation/commitment binding but cannot mint, preserve, or elevate
identity when the registry is absent.

Recovery selects one v3 Restic snapshot/tree and one registry tuple `(P_g,
M_g, T_g)` in scratch. The whole registry and its history/graph are validated
before the immutable selector/state record is atomically published. The
selector is the only mutable authority choice; generation contents are never
edited in place. Projection components are then checked or rebuilt against
that selected tuple. Until exact projection agreement is proven, the
authority may be represented as
`AUTHORITY_RECOVERED_PROJECTION_PENDING(P_g, M_g)` or
`PROVENANCE_STORE_UNAVAILABLE`, but it cannot enter `SERVING_READY`.

Serving activation is a separate bounded handoff to CG-2. V4k may specify the
contract against the locked CG-1 foundation inherited by CG-2: the expected
current generation, exact target generation, previous-generation continuity,
manifest commitments, fence/qualification evidence, rollback reason, and
fresh grant identity are explicit inputs. It must not implement or assume
unratified CG-2 behavior.

### V4g–V4l contract partition

| Obligation | Architecture contract | Execution remains separate |
|---|---|---|
| **V4g** | Register `provenance/` as a required v3 Tier-1 path in the closed restore matrix and writer census; v2 remains a distinct legacy profile. | Restore-policy implementation, fixtures, and preflight evidence. |
| **V4h** | Run registry manifest/graph validation independently from `.convmem-backup-evidence.json`; neither result substitutes for the other. | Two validator implementations and negative controls. |
| **V4i** | Validate the entire selected registry/history/graph and exact projection bindings before recovered-authority publication; missing rebuildable projection means pending, not failure of verified authority. | Whole-registry and projection verification. |
| **V4j** | Make bulk recovery a distinct Ryan-gated operation; missing/partial authority leaves live authority unchanged; item imports cannot preserve caller identity. | Recovery command/workflow and operational grant. |
| **V4k** | Bind every active authority/projection to one v3 snapshot/tree/generation tuple; require independent rollback continuity, fresh grant, exact expected-current CAS, and explicit reconciliation after source advance. | CG-2 Design A ratification first; then separately gated rollback execution. |
| **V4l** | Make selector, registry, projection, fence, pointer, rollback, and activation interruption outcomes closed and observable; no mixed-state or stale-fallback serving. | Narrow recovery crash verification; broad T5 remains out of scope. |

## 7. Recovery, projection, and serving state contract

The names below are architecture states, not implementation task names:

```text
LIVE / SERVING_READY(P_g, M_g, fence)
  ├─ verified recovery selection ───────────────►
  │    AUTHORITY_RECOVERED_PROJECTION_PENDING(P_g', M_g')
  │                                                │
  │                                                ▼
  │                                  PROJECTION_REBUILDING(P_g', M_g')
  │                                                │
  │                                                ▼
  │                                  PROJECTION_VALIDATED(P_g', M_g')
  │                                                │
  │                         atomic bounded CG-2 activation
  │                                                ▼
  └──────────────────────────────────────► SERVING_READY(P_g', M_g', fence')

invalid/missing registry, history, graph, tree, or continuity
  └──────────────────────────────────────────────► BLOCKED / QUARANTINED

content tree valid but registry unavailable
  └──────────────────────────────────────────────► PROVENANCE_STORE_UNAVAILABLE
                                                     (untrusted evidence only)
```

Required state rules:

- `SERVING_READY` names one exact registry generation, manifest commitment,
  projection binding, and serving fence. It is not a generic “healthy” flag.
- `AUTHORITY_RECOVERED_PROJECTION_PENDING` means the registry authority and
  its graph/history are verified, but projection-backed serving is unavailable.
  An old projection may not serve against the new authority.
- `PROJECTION_REBUILDING` is scratch/rebuild state; it has no serving authority.
- `PROJECTION_VALIDATED` is not serving-ready until the bounded serving
  authority performs an atomic activation and creates the new fence.
- `PROVENANCE_STORE_UNAVAILABLE` may expose only explicitly untrusted evidence
  when content recovery is otherwise useful; it never elevates IDs or changes
  live authority.
- `BLOCKED`/`QUARANTINED` is required for missing/partial/unverifiable
  authority, mismatched tree or manifest, unavailable history, invalid
  continuity, mixed generations, or publication ambiguity.

## 8. V4k bounded CG-1/CG-2 interface and required deferral

The Recovery Authority contract may consume the locked CG-1 foundation and the
CG-2 model through a narrow adapter with these semantic inputs:

- owner identity and the exact expected current authority tuple;
- selected target generation and manifest commitment;
- retained previous/rollback generation and its qualification evidence;
- current fence/pointer/manifest qualification state;
- selected v3 Restic snapshot/tree binding and provenance tuple;
- fresh Ryan grant identity, operation reason, and independent continuity
  witness;
- source-freshness/reconciliation result, including the permitted
  reconciliation-required outcome after an exact rollback to an older source
  generation.

The adapter must return typed outcomes such as exact activation, pending,
quarantine, stale precondition, or authority instability. It may not provide a
legacy fallback when generation authority is unavailable, and it may not choose
“most complete” or “latest-looking” state.

**Binding Kiro amendment:** V4k architecture may define this rollback/continuity
contract against the locked CG-1 foundation inherited by CG-2, but V4k's
execution gate cannot open until the CG-2 Design A amendment is ratified and
its generation/pointer model is stable. If CG-2 Design A changes generation
semantics, V4k must absorb that change before execution.

**Evidence/handoff state:** V4k execution interface with the CG-2
generation/pointer model is **DEFERRED pending CG-2 Design A ratification**.
This dependency does not block authoring or reviewing this Recovery Authority
architecture.

## 9. Crash-closure and publication invariants (V4l)

The following are the architecture's closure conditions for recovery-side
interruption; they are not a broad T5 campaign:

| Interruption boundary | Allowed post-crash result | Forbidden result |
|---|---|---|
| Registry object/file write or immutable generation construction | Prior selected generation remains authoritative, or the candidate is incomplete and quarantined. | Partial registry treated as complete authority. |
| Manifest write, hash, or rename | Prior complete selector remains, or the complete immutable candidate is pending. | Manifest/objects from different generations. |
| Restic restore/tree selection | Selection is rejected or remains scratch-only until `(snapshot, tree, P_g, M_g, T_g)` agrees. | “Most complete” snapshot auto-election. |
| Authority selector/state publication | Prior complete authority with valid fence, or a complete selected authority explicitly projection-pending/blocked. | Torn selector, mixed registry/history, or silent live rewrite. |
| Projection rebuild/write/rename | Selected authority remains projection-pending; failed projection is quarantined. | Old projection serving against new authority or partial projection activation. |
| Projection validation to serving activation | Validated candidate remains non-serving until atomic activation; exact recovery decides after crash. | Serving a stale pointer, unqualified projection, or mixed fence. |
| Rollback pointer/fence publication | Prior active tuple remains, or exact target is pending/blocked under the fresh grant; fence monotonicity is preserved. | Legacy resurrection, automatic alternative election, or candidate-only continuity. |

No failure edge permits a favorable projection or content row to override the
registry authority. No recovery edge mutates live authority merely to make a
preflight result look complete.

## 10. Risks and reversibility

- **Profile cost:** v3 requires new complete-data snapshots and rejects old v2
  snapshots for provenance-aware recovery. This is the deliberate cost of
  avoiding ambiguous authority semantics; v2 corpus recovery remains available
  under its old contract.
- **Validator cost:** whole-registry graph/history validation may be expensive.
  It is bounded in operation scope and runs in scratch before publication;
  budget exhaustion is blocked/untrusted rather than partial success.
- **Availability:** missing registry, history, continuity, or projection may
  leave the system pending or blocked. This is safer than silently serving
  mixed or identity-ambiguous state; the state must be observable and
  operator-actionable.
- **CG-2 coupling:** generation/pointer semantics may still change before V4k
  execution. The adapter boundary and explicit deferral contain that change;
  an incompatible ratification requires a new V4k compatibility review before
  execution.
- **Tree-binding complexity:** the canonical tree commitment must avoid
  self-reference and exclude only explicitly mutable evidence/selector paths.
  This is an implementation proof obligation, not permission to weaken the
  selected-tree check.

The direction is reversible before publication: v2 remains unchanged, v3
recovery candidates remain scratch/quarantined, registry selector publication
is atomic, and projection rebuild can be discarded without changing live
authority. After an explicit serving activation, rollback is possible only via
the exact retained generation, fresh grant, continuity witness, and bounded
authority path.

## 11. Existing acceptance oracles and review gate

The downstream VERIFY source remains
[`VERIFY-dependability-provenance.md`](VERIFY-dependability-provenance.md):

- V4g–V4j and V8i–V8j cover profile registration, separate validation,
  completeness, bulk recovery, and missing/partial authority;
- V4k, V6a–V6e, and V7d–V7e cover selected-generation commitment, CG-1
  continuity, and request-frozen CG-2 serving integration;
- V4l and V8l cover interruption closure and registry/JSONL/Chroma mismatch;
- V9e–V9g preserve no-live-mutation, runnable authorization documentation, and
  reuse of existing gates.

These rows remain `PENDING`/deferred until their separately authorized
execution and review. This architecture document does not promote any row to
PASS. The inherited V4g/V8i rows currently name `complete-data-v2`; because
this direction chooses `complete-data-v3`, downstream Execution Planning must
retarget that profile label before execution. That is an oracle wording
amendment, not permission to treat a historical v2 snapshot as v3 authority.

Kiro review should verify, at minimum:

1. the new v3 profile is the least-worst compatibility boundary;
2. content authority and provenance authority cannot silently overwrite or
   mint each other;
3. `T_g`/`M_g` and the selected Restic tuple close the snapshot-generation
   binding without trusting the evidence sidecar;
4. projection-pending and `PROVENANCE_STORE_UNAVAILABLE` cannot leak serving
   authority;
5. rollback continuity is independent of the candidate and correctly deferred
   on CG-2 Design A ratification;
6. every V4l table edge preserves the prior complete state or a complete
   pending/blocked replacement.

## 12. Downstream handoff and authorization boundary

The next phase is **Kiro architecture review/sign-off**, followed by Ryan's
Architecture Lock. Only after those gates may a separately authorized
Execution Planning phase shape V4g, V4h, V4i, V4j, V4k, and V4l into distinct
execution briefs. V4k's execution brief must additionally wait for CG-2 Design
A ratification and absorb any changed generation semantics.

Codex does not transition to Execution Planning, implementation, restore,
activation, or T5 from this document.

## Related reading

- [Recovery Authority evidence/reconciliation handoff](../inter-model/CODEX-2026-08-22-recovery-authority-architecture-handoff.md)
- [T3 closed status and deferred rows](STATUS-dependability-provenance.md)
- [Existing recovery boundary](../RECOVER.md)
- [Locked CG-2 Design A architecture](ARCHITECTURE-cg2-production-activation.md)
- [Existing V4g–V4l acceptance oracles](VERIFY-dependability-provenance.md#v4--representation-continuity)
- [Architecture Planning guide](../planning/ARCHITECTURE-PLANNING.md)

**TL;DR:** Choose a new `complete-data-v3` provenance-complete profile with an immutable registry-generation authority, exact snapshot/tree and projection bindings, explicit pending/blocked states, and bounded CG-1/CG-2 rollback continuity; V4k execution remains deferred until CG-2 Design A ratification, and the package stops for Kiro review.
