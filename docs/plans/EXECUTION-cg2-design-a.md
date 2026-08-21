# Execution Plan — CG-2 Design A first-cutover rollback bootstrap

```text
Planning Status

Phase:        Design A Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Sol authors; Luna coordinates; Ryan HITL; Cursor implements only after grant
Authority:    Awaiting Ryan HITL — planning artifact only
```

**Arc:** CG-2

**Canonical base:** `origin/main` at
`06d9064648c96e46642d1820a504dace8af5ab38`

**Locked authority:**
[`ARCHITECTURE-cg2-production-activation.md`](ARCHITECTURE-cg2-production-activation.md),
[`RUNBOOK-cg2-production-activation.md`](RUNBOOK-cg2-production-activation.md),
and [`VERIFY-cg2-production-activation.md`](VERIFY-cg2-production-activation.md)
as present at the canonical base.

**Post-#221 compatibility confirmation:** The change from the prior Design A
base through this canonical tip is documentation/coordination-only
(`docs/inter-model/LATEST.md`, `docs/inter-model/STATUS.md`, and
`docs/plans/STATUS-dependability-provenance.md`). It does not change the locked
Design A Architecture, RUNBOOK, or VERIFY semantics. This refresh records
compatibility with that post-#221 state; it does not reopen the lock.

**Prior CG-2 execution-plan authority:**
`6a808f1543f2c93270d9f0ed1ae88cad27f6556b`. Its T1–T5 implementation is
already merged; this plan does not repeat or reopen it.

**Goal:** close the first-owner rollback gap by converting the accepted LEGACY
serving set into exact retained generation `G_rb`, separating forward publish,
first cutover, rollback, and same-pointer recovery, and proving those
transitions before any first-owner activation packet or grant.

**Plan status:** planning only. This document authorizes no Python, test, formal
model, configuration, corpus, generation-root, fence, pointer, activation,
packet, grant, GC, Shadow, or R2b change.

## Human consequence

If Ryan approves this plan, Cursor can implement Design A in bounded slices on
a fresh implementation branch. The result will make first cutover refuse
unless exact, independently qualified `G_rb` and `G_canary` are both known;
make rollback use a retained generation even after source advance; and prevent
a second owner promotion while the first canary remains open. Approval of this
plan will still not authorize building either production generation or
activating an owner.

### 5 Ws

| Field | Answer |
|---|---|
| **Who** | Cursor implements after Ryan Execute grant; an independent reviewer signs the exact implementation/model tip; Ryan alone gates later production generation builds and V8c. |
| **What** | A bounded extension of existing CG-1 pointer/store and CG-2 authority/reconciliation machinery. |
| **When** | After Design A architecture lock on `main`, before any production `G_rb`/`G_canary` build or V8c packet preparation. |
| **Why** | The first canary otherwise has no committed prior generation and cannot perform generation-switch rollback without resurrecting LEGACY. |
| **How** | Exact LEGACY conversion, hash-bound evidence, distinct authority APIs, monotonic fence sequencing, durable reconciliation on rollback, tests, rehearsal, formal checking, and independent review. |

**TL;DR:** Extend the existing authority system with one exact retained rollback
baseline and three distinct publication operations. Keep V6c and V8c PENDING
until their named downstream evidence exists; do not perform production work in
this phase.

## 1. Locked invariants translated into execution constraints

Implementation must preserve all of the following without comparing Design A
to alternatives:

1. `G_rb` is an exact generational conversion of the accepted pre-cutover
   LEGACY serving set for one owner. It is manifested, embedding-proven,
   cold-qualified, logically equivalent, physically retained, and recorded as
   `RETAINED_ROLLBACK_BASELINE`.
2. The ratified conversion fingerprint is the literal string
   `convmem/cg2-rollback-baseline-convert-v1`. Ordinary live-source build
   fingerprints are not accepted in its place.
3. `G_rb` is evidence/protected lifecycle state, not a second serving pointer.
   Only the active pointer serves.
4. Ordinary forward publication, first cutover, generation-switch rollback,
   and same-pointer recovery are separate operations:
   `publish_active_pointer`, `publish_first_cutover_active_pointer`,
   `rollback_active_pointer`, and `recover_active_pointer`.
5. Current-active CAS and durable rollback lineage are distinct values. The
   ordinary forward path derives durable previous lineage from the CAS-proven
   current active generation; first cutover uses CAS `None` while durable
   previous is exact `G_rb`; rollback CASes against current active while making
   the rollback target active and retaining the former active generation.
6. Ordinary `publish_active_pointer` cannot create an owner's first pointer.
   The only `expected_active_generation_id=None` route is the dedicated first-
   cutover operation.
7. First cutover requires exact `G_rb` generation ID and manifest SHA, exact
   `G_canary` generation ID and manifest SHA, common owner/source binding,
   explicit embedding provenance, fresh-process qualification of both, and
   `G_rb != G_canary`.
8. A refusal before durable fence publication leaves the owner `LEGACY` with
   no pointer. A failure after durable fence publication leaves
   `FENCED_NO_POINTER`. No Design A operation removes the fence or recovers
   LEGACY.
9. Forward publication still refuses stale source. Rollback may restore the
   exact retained generation after source advance, but the newer desired source
   remains a durable reconciliation obligation.
10. `recover_active_pointer` republishes the exact visible pointer payload. It
    has no target-generation argument and cannot switch generation identity.
11. The first-canary-open guard blocks every second forward serving promotion
    for that owner. Rollback and exact same-pointer recovery remain available.
    This Execute does not implement or exercise canary closure; a separate Ryan
    canary-close decision and separately scoped operation are required.
12. The fence is monotonic, GC remains disabled, `G_rb` stays protected, and
    all legacy rows remain physically present during the canary evidence window.
13. The 2026-08-14 TLC run remains evidence for the old model revision only. It
    does not prove any Design A transition or property.

## 2. Scope boundary

### In scope after a separate Ryan Execute grant

- Hermetic conversion of an owner-scoped accepted LEGACY serving snapshot into
  generation-scoped rows using the existing CG-1 manifest/store contract.
- Hash-bound rollback-baseline evidence and a durable first-canary-open guard;
  neither is serving authority.
- Pointer API separation and common private publication mechanics under the
  existing owner lock.
- Dedicated first-cutover preflight and fence/pointer orchestration.
- Generation-switch rollback with fresh qualification and durable source
  reconciliation when live source differs.
- Tests, isolated rehearsal, property mapping, restored/updated formal model,
  and VERIFY mechanical evidence.

### Out of scope

- Production generation-root provisioning or configuration.
- Building production `G_rb` or `G_canary`.
- Publishing any production fence or pointer.
- Preparing or amending a V8c packet, issuing a grant, or activating an owner.
- Closing the first-canary window.
- Physical deletion, GC, compaction, lease/pin implementation, or legacy-row
  retirement.
- Shadow Ledger, R2b, rename migration, hardlink policy, or a second authority
  system.
- Changes to `chroma_write_store.py` merely to accommodate #221's universal
  writer boundary.
- Changes to the locked architecture or production runbook semantics.

Design A Execute is hermetic: conversion, staging, qualification, rehearsal,
and evidence collection use temporary roots and temporary Chroma only. A later
separately authorized production `G_rb`/`G_canary` build must enter the
existing universal production writer boundary. Direct use of hermetic
`FileGenerationStore` against live Chroma outside that boundary is prohibited.

## 3. Canonical repository facts

The plan is based on these observed `main` surfaces:

- `file_generation_pointer.py::publish_active_pointer` currently uses one
  `expected_previous_generation_id` value both for CAS and durable
  `previous_generation_id`; the two responsibilities must be split.
- `file_generation_pointer.py::recover_active_pointer` already selects only the
  visible pointer, but needs explicit negative coverage proving no generation
  switch is possible.
- `serving_authority.py` owns fence publication and authority resolution. Its
  current fence writer can replace bytes; Design A requires immutable,
  monotonic, idempotent-identical publication.
- `file_generation_store.py::_assert_owner_budget` protects only active and
  previous generations. Without a baseline-protection input, staging
  `G_canary` after `G_rb` classifies `G_rb` as abandoned and refuses the second
  stage.
- `chroma_write_store.py` is the existing universal production writer boundary
  after #221. Design A Execute must not modify it merely to enable the
  hermetic plan; production generation construction is a later separately
  authorized operation and may not bypass that boundary.
- `source_reconciler.py` already owns durable dirty scopes and coalesced desired
  owner work. Rollback must reuse it rather than create another queue.
- `ServingIndexRepository` already freezes one authority vector per operation.
  The missing `FrozenGenerationStable` evidence is a dedicated mid-request
  pointer-change test, not a new read architecture.
- `mixed_mode_proof.py` already fixes `PHYSICAL_DELETION_DISABLED = True` and
  reports retention. It must learn to label exact baseline protection.
- `cg2_property_map.py` currently maps `FrozenGenerationStable` to a retry-
  budget test; that mapping is insufficient and must be corrected.
- VERIFY references `docs/plans/formal/cg2/`, but those files are absent on
  canonical `main`. Their last architecture revision exists at
  `e680ce837653698a5be8b78ba02db2f880c40c63` and must be restored before Design
  A modifications.

## 4. Exact expected Execute surfaces

These are the only expected implementation/evidence surfaces. Discovery that a
required change falls outside this set is a scope-stop for Luna/Ryan review.

### Runtime and evidence modules

| Path | Expected Design A responsibility |
|---|---|
| `cg2_rollback_baseline.py` (new) | Capture one frozen owner-scoped accepted LEGACY serving set; convert rows without re-embedding; create/validate immutable `RETAINED_ROLLBACK_BASELINE` evidence; prove bidirectional logical equivalence. |
| `cg2_cutover_guard.py` (new) | Low-level hash-bound first-canary-open artifact, path, immutable publication, and validation. It imports no pointer/orchestration module, avoiding an authority cycle. No close writer in this Execute. |
| `cg2_first_cutover.py` (new) | Public dedicated first-cutover operation: preflight exact bindings before fence; acquire the owner lock exactly once for monotonic fence, open guard, and dedicated first pointer; resume `FENCED_NO_POINTER` only under a fresh grant; no CLI and no production defaults. |
| `file_generation_pointer.py` | Separate current-active CAS from durable previous lineage; provide one private lock-held pointer-publication primitive shared by forward publish, first cutover, rollback, and exact recovery; add rollback API; keep recovery exact-payload only; make ordinary forward publication reject first-pointer use and open-canary promotion. |
| `file_generation_store.py` | Accept an exact retained-baseline protection map when evaluating staging backpressure; never treat protected `G_rb` as abandoned. |
| `serving_authority.py` | Make fence publication immutable/idempotent-identical and reject replacement; preserve `FENCED_NO_POINTER` resolution. No fence deletion API. |
| `source_reconciler.py` | Add one atomic helper that durably records/coalesces a rollback-created desired-source obligation before stale-source rollback pointer publication. Reuse existing state file and budgets. |
| `mixed_mode_proof.py` | Include exact retained rollback baselines in retention inventory while keeping physical deletion disabled. |
| `cg2_property_map.py` | Add Design A properties/tests and replace the false `FrozenGenerationStable` mapping with the dedicated mid-request test. |
| `cg2_rehearsal.py` | Add isolated Design A conversion, first-cutover crash, rollback-after-source-advance, retention, and evidence-bundle collection. Update architecture identity to the canonical Design A lock. |

No change is expected in `convmem.py`, `mcp_server.py`, production config,
`watch.py`, `doctor.py`, Shadow modules, or R2b modules.

### Tests

| Path | Expected coverage |
|---|---|
| `tests/test_cg2_rollback_baseline.py` (new) | Frozen LEGACY snapshot, convert-v1 identity, exact provenance preservation/equivalence, same-ledger-ID plus distinct-valid-provenance positive case, invalid/missing-provenance conservative negative case, and malformed/wrong-owner/wrong-SHA/non-equivalent refusals. |
| `tests/test_cg2_first_cutover.py` (new) | Exact structural gate, pre/post-fence timing, `G_rb != G_canary`, first pointer fields, open-canary guard, crash state. |
| `tests/test_file_generation_pointer.py` | CAS/lineage API split, ordinary forward behavior, rollback publication, stale CAS, recovery signature/identity. |
| `tests/test_file_generation_validate.py` | Fresh qualification of baseline/canary/rollback target and persisted corruption refusal. |
| `tests/test_file_generation_store.py` | `G_rb` protection permits staging `G_canary`; unrelated abandoned generation still blocks; no deletion. |
| `tests/test_serving_authority.py` | Monotonic fence bytes; durable fence with no pointer resolves only `FENCED_NO_POINTER`. |
| `tests/test_source_reconciler.py` | Rollback-created reconciliation obligation persists, coalesces to latest desired source, and survives restart. |
| `tests/test_serving_index_repository.py` | Dedicated pointer-change-mid-request `FrozenGenerationStable` test. |
| `tests/test_mixed_mode_proof.py` | GC disabled and exact baseline retained/protected in inventory across reopen. |
| `tests/test_cg2_rehearsal.py` | End-to-end isolated Design A drill and evidence status; no live path. |

### Formal and governed evidence

| Path | Expected change |
|---|---|
| `docs/plans/formal/cg2/CG2Authority.tla` | Restore from `e680ce8`, then add Design A baseline, first-cutover, rollback, recovery, reconciliation, canary-window, and refusal transitions. |
| `docs/plans/formal/cg2/CG2Cutover.cfg` | Restore and rerun old cutover properties against the changed shared model. |
| `docs/plans/formal/cg2/CG2StaleReconcile.cfg` | Restore and rerun old stale/reconcile properties against the changed shared model. |
| `docs/plans/formal/cg2/CG2Rename.cfg` | Restore and rerun old rename/pinning properties against the changed shared model. |
| `docs/plans/formal/cg2/CG2DesignA.cfg` (new) | Focused exhaustive instance for exact baseline, first cutover, rollback-after-source-advance, recovery separation, and canary guard. |
| `docs/plans/formal/cg2/README.md` | Restore historical evidence, clearly label it old-revision only, map new properties/config, and record the later Design A run separately. |
| `docs/plans/VERIFY-cg2-production-activation.md` | After Execute evidence only: bind new implementation/model SHA and mechanical/rehearsal/review results. V6c and V8c remain PENDING until their exact gates below. |

The locked architecture and runbook are read-only inputs for Execute. If a code
name must differ from this plan, update this execution plan before
implementation review; do not silently drift the runbook or architecture.

## 5. Design A data and API contracts

### 5.1 Accepted LEGACY serving snapshot

`cg2_rollback_baseline.py` captures one owner under the existing source lock
and the already-soaked LEGACY serving classifier:

1. Resolve the owner as `LEGACY`; any fence, pointer, retirement, quarantine,
   unknown source class, or owner/source ambiguity refuses capture.
2. Read both `knowledge_units` and `conversation_summaries` by exact canonical
   `source_path`. Use existing serving semantics: superseded units are excluded;
   summary rows admitted by the current LEGACY path are included; stable-
   governed projections are excluded.
3. Require every admitted row to have one unambiguous owner, logical identity,
   document, persisted float32 embedding, and collection membership. Missing or
   duplicate logical identity refuses conversion. For a provenance-bearing row,
   a valid `(assertion_id, provenance_commitment)` pair and its provenance
   envelope are part of that row's immutable identity. A `ledger_id` alone is
   never assertion identity. Rows without valid provenance retain the existing
   conservative legacy identity treatment; conversion does not synthesize a
   provenance pair for them.
4. Bind the processed/accepted source hash that produced the LEGACY set. Do not
   substitute the current filesystem hash when it differs; current source
   freshness belongs to forward `G_canary`, not rollback baseline identity.
5. Recheck the same owner authority and exact normalized LEGACY set while still
   under the lock. Any row/authority change discards the snapshot and refuses;
   it does not publish partial evidence.

The normalized row identity is:

```text
(owner_digest, collection_name, logical_id,
 document_hash, persisted_embedding_hash,
 embedding_model, embedding_dimension,
 immutable_semantic_metadata_hash,
 provenance_envelope_hash, assertion_id, provenance_commitment)
```

Generation-only metadata and physical IDs are excluded from equivalence.
Supersession state participates through admission: excluded superseded units
cannot appear in `G_rb`. For rows with valid provenance, the envelope,
`assertion_id`, and `provenance_commitment` are preserved exactly and
participate in the bidirectional equivalence evidence. Two rows with the same
`ledger_id` but distinct valid provenance identities therefore remain two
distinct rows. Conversion never dedupes, merges, or remints provenance.

### 5.2 Convert-v1 and embedding provenance

Conversion copies admitted documents and persisted embeddings; it never calls
an embedder, parser, LLM, or deduper. It copies each valid provenance envelope,
`assertion_id`, and `provenance_commitment` byte-for-byte into the generation
evidence; it never dedupes, merges, or remints those identities. It assigns
CG-1 generation-scoped physical IDs and manifests them through `FileGenerationStore` and
`build_generation_manifest`.

The conversion refuses unless explicit provenance names, for each collection:

- source collection UUID and exact Chroma configuration;
- embedding model identifier from ratified evidence, never dimension inference;
- embedding dimension, verified on every row;
- provenance evidence digest and capture timestamp;
- literal convert pipeline fingerprint
  `convmem/cg2-rollback-baseline-convert-v1`.

The resulting `generation_id` remains deterministic through existing
`make_generation_id(owner_digest, accepted_source_hash, convert_fingerprint,
candidate_bundle_hash)`.

### 5.3 Retained rollback-baseline evidence

After staging, manifest publication, fresh-process qualification, and exact
equivalence pass, publish one immutable evidence record at:

```text
<generation_root>/rollback_baselines/
  <owner_digest>--<generation_id>.json
```

Required hash-bound fields:

- schema and state=`RETAINED_ROLLBACK_BASELINE`;
- owner key/digest and canonical source path;
- accepted LEGACY source hash and normalized snapshot digest;
- exact convert-v1 fingerprint;
- `G_rb.generation_id`, manifest filename, and manifest SHA-256;
- per-collection embedding provenance;
- provenance envelope, `assertion_id`, and `provenance_commitment` identity
  evidence for every provenance-bearing row;
- cold-qualification result identity;
- bidirectional equivalence result with zero missing, unexpected, duplicate,
  wrong-owner, non-equivalent, or provenance-identity-changing rows;
- evidence payload hash.

Publication is idempotent only for identical bytes. The record cannot be
overwritten, cannot name an active pointer, and cannot itself serve.

### 5.4 Pointer APIs

Public semantics after Design A:

```text
publish_active_pointer(
    target_manifest_reference,
    expected_active_generation_id=<non-None current active>, ...)

publish_first_cutover_active_pointer(
    canary_manifest_reference,
    rollback_baseline_evidence,
    expected_active_generation_id=None, ...)

rollback_active_pointer(
    retained_manifest_reference,
    expected_active_generation_id=<exact current active>, ...)

recover_active_pointer(owner_key, ...)
```

Each public authority-changing operation acquires the existing `source_flock`
for its owner exactly once. Public operations own preflight/orchestration and
locking; one private lock-held pointer-publication primitive performs the
actual pointer write for ordinary forward publication, first cutover, rollback,
and exact recovery. The private primitive assumes the correct owner lock is
already held and never acquires it. High-level first-cutover and rollback code
must call that private primitive directly while holding their one lock; they
must not call another public operation that reacquires `source_flock`.
`source_flock` itself is not changed to tolerate nested locking. There is no
parallel pointer format or authority file.

- Ordinary forward publication CASes against exact current active, performs
  mandatory current-source freshness, and writes durable
  `previous_generation_id` equal to that CAS-proven current active generation.
- First cutover CASes against pointer absence while writing durable
  `previous_generation_id=G_rb` and active=`G_canary`.
- Rollback CASes against exact current active, fresh-qualifies the retained
  target, does not require target source hash to equal live source, and writes
  durable previous equal to the former active generation.
- Recovery accepts no target reference or generation ID. It validates and
  republishes the exact visible payload bytes only.

### 5.5 First-cutover structural gate and ordering

`cg2_first_cutover.py` has a preflight phase and one commit phase.

Before any fence bytes exist, preflight must prove exactly:

1. exact `G_rb` generation ID and manifest SHA match immutable retained-
   baseline evidence;
2. exact `G_canary` generation ID and manifest SHA match the caller's grant-
   bound inputs;
3. both manifests bind the same owner key/digest and canonical source path;
4. both have explicit, internally consistent embedding provenance and exact
   collection dimensions/configuration;
5. both pass fresh-process exact qualification;
6. `G_rb.generation_id != G_canary.generation_id`;
7. current pointer is absent, current owner is LEGACY, reconciliation is fresh,
   and current source hash equals `G_canary.source_hash`;
8. the first-canary guard does not already exist.

Any preflight failure returns before fence publication. Missing, corrupt,
wrong-owner, wrong-manifest-SHA, non-equivalent, or unqualified baseline
evidence therefore leaves the owner LEGACY.

The commit phase acquires the existing owner lock once, rechecks all exact
artifact hashes, pointer absence, current source, and owner binding, then:

1. atomically publishes the immutable monotonic fence;
2. atomically publishes the immutable first-canary-open guard naming exact
   `G_rb` and `G_canary`;
3. reruns the final exact qualification/binding checks and invokes the private
   lock-held pointer writer with first-cutover semantics: CAS `None`,
   previous=`G_rb`, and active=`G_canary`;
4. returns the module-sealed qualified active pointer.

No catch block removes or rewrites the fence. A crash or failure after step 1
and before successful step 3 leaves `FENCED_NO_POINTER`; a fresh request can
never resolve LEGACY. The guard is non-serving evidence and may exist in that
fail-closed state.

#### 5.5.1 Fresh-grant completion from `FENCED_NO_POINTER`

The dedicated public `publish_first_cutover_active_pointer` operation also owns
the only normal completion path for both resumable crash states:

- fence present / guard absent / pointer absent;
- fence present / exact guard present / pointer absent.

Neither state may reuse or continue under the pre-crash grant. Resume requires
a fresh Ryan one-shot grant bound to the exact `G_rb` and `G_canary`. Before
acquiring the owner lock,
the operation requalifies both exact grant-bound generations and reconstructs
the exact expected immutable fence/guard evidence. Under its single owner-lock
commit section it then:

1. revalidates the existing fence as immutable, structurally valid, and bound
   to the exact owner/source expected by the fresh grant;
2. validates the guard as either absent or exact/byte-identical to the expected
   guard for the same `G_rb`, `G_canary`, owner/source, and evidence hashes;
3. if the guard is absent, atomically publishes that exact guard; if it is
   already exact, leaves its bytes unchanged;
4. rechecks pointer absence and the fresh grant's exact structural and
   qualification preconditions;
5. invokes the private lock-held pointer writer once to complete the exact
   first pointer with CAS `None`, previous=`G_rb`, and active=`G_canary`.

A missing fence is not a resume state and follows ordinary pre-fence cutover.
A conflicting, malformed, or corrupt fence or guard fails closed and requires
operator repair; normal code neither rewrites the artifact nor attempts a
different generation. Resume never clears the fence, removes the guard,
restores LEGACY, or reuses the stale pre-crash grant.

### 5.6 Rollback after source advance

Rollback runs under the existing owner lock and in this order:

1. Require monotonic fence, valid active pointer, exact current-active CAS, and
   exact retained target named by durable lineage/retained evidence.
2. Fresh-process qualify the target manifest and rows.
3. Observe current source. Equality is not a rollback precondition.
4. If source is missing or differs from target manifest, durably mark the
   existing source-reconciliation state dirty and coalesce/enqueue the latest
   desired source observation **before** pointer publication. Failure to make
   that obligation durable refuses rollback while the current pointer remains.
5. Publish target active with durable previous equal to the former active.
6. Re-read the fence and open-canary guard; neither is removed or cleared.

The obligation-before-pointer order permits harmless extra reconciliation if
pointer publication later refuses, but never permits a successful stale-source
rollback without durable desired-state debt. Rollback stays GENERATIONAL and
never invokes a LEGACY path.

### 5.7 First-canary guard

The immutable open guard is published before the first pointer and names owner,
exact `G_rb`, exact `G_canary`, and evidence hashes. While it is present:

- ordinary forward `publish_active_pointer` refuses;
- another first-cutover publish refuses;
- `rollback_active_pointer` remains available;
- `recover_active_pointer` remains available for exact same-pointer recovery;
- no API in this Execute closes, deletes, or mutates the guard.

This structurally enforces “no second serving promotion” until a separate Ryan
canary-close decision and separately scoped follow-up operation.

## 6. Ordered tests-first implementation slices

Every slice begins with the named failing tests. Implementation does not start
until reviewers can see the negative oracle. Each slice commits independently
and is pushed immediately by the implementation lane.

### D1 — Exact LEGACY snapshot, convert-v1, and retained baseline

**Red tests first**

- Add `tests/test_cg2_rollback_baseline.py` fixtures for both collections,
  superseded units, stable-governed rows, duplicate logical IDs, absent model
  provenance, mixed dimensions, wrong owner/source, row churn, and persisted
  float32 embeddings.
- Require exact snapshot-to-`G_rb` set equality in both directions.
- Require deterministic generation ID and literal convert-v1 fingerprint.
- Require immutable retained evidence and manifest SHA binding.
- Add a positive case with two LEGACY rows sharing one `ledger_id` but carrying
  distinct valid `(assertion_id, provenance_commitment)` identities; both must
  survive conversion and equivalence.
- Add a negative case with missing or invalid provenance; it must follow the
  existing conservative legacy identity policy, without synthesized provenance.
- Assert provenance envelopes, assertion identities, and commitments are
  byte-identical through `G_rb`; conversion never dedupes, merges, or remints
  them.
- Prove missing/corrupt/wrong-owner/wrong-SHA/non-equivalent evidence refuses.

**Then implement**

- Add `cg2_rollback_baseline.py`.
- Extend `file_generation_store.py` with exact retained-baseline protection so
  `G_canary` can stage after `G_rb` without weakening the abandoned-generation
  guard.

**Dependencies:** merged CG-1 contract/store and current LEGACY classifier only.

**Verification**

```bash
python -m pytest tests/test_cg2_rollback_baseline.py \
  tests/test_file_generation_store.py tests/test_file_generation_contract.py -q
```

**Stop if:** provenance must be guessed, exact owner rows cannot be frozen, a
same-ledger-ID distinct-provenance pair collapses, provenance is reminted or
deduped, the conversion would re-embed/re-dedupe, or `G_canary` staging requires
weakening the one-abandoned-generation guard.

### D2 — Authority API separation

**Red tests first**

- In `tests/test_file_generation_pointer.py`, assert ordinary publication
  rejects `expected_active_generation_id=None`.
- Prove stale CAS refusal is independent of retained rollback target.
- Prove ordinary forward writes previous=current active.
- Prove first cutover can express expected active `None` with previous=`G_rb`.
- Prove rollback switches to an exact retained target and writes former active
  as previous.
- Prove `recover_active_pointer` has no target-generation parameter and cannot
  change active generation even when another complete generation exists.
- Add a lock-acquisition oracle that wraps `source_flock`, fails immediately on
  reentry, and records exactly one acquisition for each public operation;
  explicitly exercise first cutover and rollback so neither can call a public
  pointer API while already holding the owner lock.

**Then implement**

- Refactor `file_generation_pointer.py` around one private lock-held writer
  shared by forward publish, first cutover, rollback, and exact recovery.
- Add `cg2_cutover_guard.py`; make ordinary forward publication refuse an open
  guard without importing the high-level cutover orchestrator.

**Dependencies:** D1's retained-evidence validator type; no cutover orchestration.

**Verification**

```bash
python -m pytest tests/test_file_generation_pointer.py \
  tests/test_file_generation_validate.py \
  tests/test_source_freshness_promotion.py -q
```

**Stop if:** any public API still uses one value for both CAS and durable
lineage, recovery can select a target, ordinary forward can create a first
pointer, or first cutover/rollback acquires `source_flock` more than once.

### D3 — First-cutover structural gate, fence sequencing, and canary guard

**Red tests first**

- Add `tests/test_cg2_first_cutover.py` with a parameterized pre-fence refusal
  matrix: missing baseline, corrupt evidence, wrong owner, wrong source,
  wrong manifest SHA, failed qualification, non-equivalent set, missing
  provenance, and `G_rb == G_canary`.
- Assert every pre-fence refusal leaves no fence and no pointer.
- Inject failure/crash after durable fence and before pointer; assert
  `FENCED_NO_POINTER`, monotonic fence bytes, no pointer, and no LEGACY recovery.
- Add explicit `fence -> crash -> fresh-grant resume` coverage: start from
  fence present / guard absent / pointer absent, requalify exact grant-bound
  `G_rb` and `G_canary`, publish the missing exact guard and first pointer, and
  prove the fence bytes never change.
- Add explicit `fence -> guard -> crash -> fresh-grant resume` coverage: start
  from fence present / exact guard present / pointer absent, preserve exact
  guard/fence bytes, and complete only the grant-bound first pointer.
- Add wrong-guard refusal coverage: conflicting, corrupt, wrong-owner, or
  wrong-generation guard bytes fail closed with no pointer publication and an
  operator-repair result.
- Assert successful first pointer has active=`G_canary`,
  `expected_active=None`, previous=`G_rb`.
- Assert a second forward promotion and second first-cutover operation refuse
  while the guard is open; rollback and same-pointer recovery remain callable.

**Then implement**

- Add `cg2_first_cutover.py`.
- Make fence publication immutable/idempotent-identical in
  `serving_authority.py`.
- Complete low-level guard publication/validation in `cg2_cutover_guard.py`.
- Implement both resume states in the same dedicated first-cutover operation;
  require a fresh one-shot grant and reuse the private lock-held pointer writer.

**Dependencies:** D1 and D2 complete.

**Verification**

```bash
python -m pytest tests/test_cg2_first_cutover.py \
  tests/test_serving_authority.py tests/test_serving_index_repository.py -q
```

**Stop if:** any structural check can occur only after the fence, an exception
path clears the fence, a fenced/no-pointer owner can resolve LEGACY, a resume
can reuse the pre-crash grant or overwrite conflicting fence/guard bytes, or a
second promotion bypasses the open guard.

### D4 — Rollback after source advance and durable reconciliation

**Red tests first**

- Extend pointer/source-reconciler tests for rollback with unchanged source,
  advanced source, missing source, stale current-active CAS, corrupt target,
  and reconciliation persistence failure.
- Prove stale-source forward publication still refuses.
- Prove source-advanced rollback succeeds only after durable dirty/pending
  state exists and that the obligation survives process restart.
- Prove the newer desired source remains coalesced, fence remains byte-identical,
  guard remains open, owner remains GENERATIONAL, and no LEGACY row is selected.
- Prove recovery still cannot switch generation.

**Then implement**

- Complete `rollback_active_pointer` in `file_generation_pointer.py`.
- Add the rollback-obligation helper to `source_reconciler.py` using its current
  state file, queue budget, and coalescing semantics.

**Dependencies:** D2; D3 supplies fence and guard fixtures.

**Verification**

```bash
python -m pytest tests/test_file_generation_pointer.py \
  tests/test_source_freshness_promotion.py \
  tests/test_source_reconciler.py tests/test_cg2_first_cutover.py -q
```

**Stop if:** rollback requires retained source equality, successful rollback can
precede durable reconciliation debt, rollback removes the fence, or recovery
shares the rollback target-selection path.

### D5 — Request freeze, retention, and isolated Design A rehearsal

**Red tests first**

- Add
  `tests/test_serving_index_repository.py::test_frozen_generation_stays_stable_when_pointer_changes_mid_request`:
  open one repository, change the durable pointer through a separately opened
  writer fixture, and prove all reads through the already-open repository use
  its original frozen generation.
- Extend mixed-mode tests to prove `G_rb` remains protected across `G_canary`
  staging, first cutover, rollback, and reopen; physical deletion remains
  disabled.
- Extend `tests/test_cg2_rehearsal.py` to run, only under temporary roots:
  LEGACY snapshot → `G_rb` conversion/qualification → exact `G_canary`
  qualification → first cutover → source advance → rollback → restart/recovery.
- Rehearsal asserts no production path, no GC, no second promotion, no fence
  removal, and durable desired-source debt after rollback.

**Then implement**

- Update `mixed_mode_proof.py`, `cg2_property_map.py`, and `cg2_rehearsal.py`.
- Change `ServingIndexRepository` runtime only if the dedicated test exposes an
  actual freeze violation; because that would exceed the exact expected
  surface list, stop for Luna/Ryan before editing it.

**Dependencies:** D1–D4 complete.

**Verification**

```bash
python -m pytest tests/test_serving_index_repository.py \
  tests/test_mixed_mode_proof.py tests/test_cg2_rehearsal.py -q
```

**Stop if:** the rehearsal touches configured production roots, a retained
baseline is classified abandoned/GC-eligible, or the frozen-generation test
needs a new authority mechanism rather than the existing request vector.

### D6 — Restore and extend the formal model

**Model work begins only after D1–D4 public contracts stabilize.** Restore the
five historical files exactly from `e680ce8`, review the restoration diff, then
change the shared model and README and add `CG2DesignA.cfg`.

Required new transitions/state:

- exact LEGACY-set conversion to qualified retained baseline;
- pre-fence structural refusal;
- durable fence without pointer;
- fresh-grant resume from fence/no-guard/no-pointer;
- fresh-grant resume from fence/exact-guard/no-pointer;
- wrong/conflicting guard refusal with no pointer and no LEGACY restoration;
- first pointer with CAS `NoGen`, previous=`G_rb`, active=`G_canary`;
- ordinary forward promotion with CAS separate from lineage;
- source advance followed by exact retained-generation rollback;
- durable reconciliation-required before/with stale-source rollback;
- same-pointer recovery with no generation selection;
- first-canary-open refusal of a second forward promotion;
- GC exclusion for `RETAINED_ROLLBACK_BASELINE`.
- one acquisition/release interval per authority-changing operation, with the
  lock-held publication action unable to reacquire the owner lock.

Required new named checks:

- `FirstCutoverHasExactRollbackBaseline`
- `FirstCutoverGenerationsDistinct`
- `CASSeparateFromRollbackLineage`
- `PreFenceRefusalPreservesLegacy`
- `PostFenceFailureNeverLegacy`
- `FenceCrashResumeRequiresFreshGrant`
- `GuardCrashResumeRequiresFreshGrant`
- `WrongGuardRefusesFirstPointer`
- `RollbackAfterSourceAdvanceKeepsReconciliation`
- `RollbackNeverResurrectsLegacy`
- `RecoveryNeverSwitchesGeneration`
- `FirstCanaryBlocksSecondPromotion`
- `RollbackBaselineNeverGCEligible`
- `AuthorityOperationAcquiresOwnerLockOnce`

The three restored historical configurations and the new Design A
configuration must all run; a shared-model change can invalidate old checks.

**Verification**

```bash
for config in CG2Cutover CG2StaleReconcile CG2Rename CG2DesignA; do
  java -Xmx2g -XX:+UseParallelGC -cp /path/to/tla2tools.jar tlc2.TLC \
    -workers 2 -coverage 1 \
    -config "docs/plans/formal/cg2/${config}.cfg" \
    docs/plans/formal/cg2/CG2Authority.tla
done
```

Record TLA+ release/JAR checksum, command, per-configuration generated and
distinct state counts, depth, nonzero action coverage for every new transition,
empty queues, and zero errors. The README must preserve the 2026-08-14 counts
as historical old-revision evidence and add a separate Design A run section;
never rewrite the old run as Design A proof.

**Stop if:** TLC finds a counterexample, any required action has zero coverage,
the restored model cannot be tied to `e680ce8`, or a property needs an
architecture decision not already locked.

### D7 — Execute evidence, independent review, and Ryan stop

After D1–D6 pass at one implementation tip:

1. Update `cg2_property_map.py` with every Design A property → exact pytest
   node mapping.
2. Update `cg2_rehearsal.collect_execute_evidence()` with canonical architecture
   SHA, execution-plan SHA, implementation SHA, model SHA, focused/full test
   results, TLC evidence identities, and explicit no-production flags.
3. Update VERIFY mechanical rows without changing gate definitions.
4. Request independent review of the exact implementation/model tip.
5. Stop for Ryan. Do not build production generations or prepare V8c.

**Verification**

```bash
python -m pytest tests/test_cg2_rollback_baseline.py \
  tests/test_cg2_first_cutover.py \
  tests/test_file_generation_pointer.py \
  tests/test_file_generation_validate.py \
  tests/test_file_generation_store.py \
  tests/test_serving_authority.py \
  tests/test_source_freshness_promotion.py \
  tests/test_source_reconciler.py \
  tests/test_serving_index_repository.py \
  tests/test_mixed_mode_proof.py tests/test_cg2_rehearsal.py -q

python -m pytest -q
git diff --check
```

Full-suite timeout is not PASS. Any unexplained failure, skipped Design A test,
or test that opens a configured live path blocks handoff.

## 7. Dependency boundaries

```text
existing CG-1 contract/store
        │
        ├── D1 baseline conversion/evidence
        │       └── retained-baseline protection
        │
        └── D2 separated pointer mechanics
                 │
                 ├── D3 first-cutover orchestration + open guard
                 └── D4 rollback + existing reconciliation state
                          │
                          └── D5 integrated rehearsal / request freeze

D1–D4 stable contracts ──► D6 formal refinement
D5 + D6 exact tip ───────► D7 independent review / Ryan HITL
```

Import direction is one-way:

- `cg2_cutover_guard.py` imports only low-level contract/atomic-file helpers.
- `file_generation_pointer.py` may read the low-level guard but does not import
  `cg2_first_cutover.py` or the serving repository.
- `cg2_rollback_baseline.py` uses the existing store/manifest contract and
  never writes a pointer or fence.
- `cg2_first_cutover.py` orchestrates existing baseline, guard, fence, pointer,
  source-observation, and reconciliation checks; its public operation owns the
  single owner-lock interval and calls the private lock-held pointer writer,
  never another public pointer operation; lower modules never import it.
- `file_generation_pointer.py` public forward/rollback/recovery operations each
  own one `source_flock` interval; the shared private writer assumes that lock
  and cannot reacquire it. Do not modify `source_flock` for nested locking.
- `source_reconciler.py` remains the sole durable desired-source queue.
- `ServingIndexRepository` remains the sole serving read boundary.

No new daemon, CLI command, service, pointer format, current-active registry, or
rollback authority file is permitted.

## 8. Architecture invariant → implementation → test map

| Locked invariant | Implementation surface | Required mechanical evidence |
|---|---|---|
| Accepted LEGACY set converts exactly to `G_rb` | `cg2_rollback_baseline.py`, existing store/manifest APIs | `test_frozen_legacy_set_is_bidirectionally_equivalent_to_grb`; same-ledger-ID distinct-provenance positive/negative D1 cases |
| Ratified convert-v1 fingerprint | `cg2_rollback_baseline.py` constant + evidence validator | deterministic ID/fingerprint test; wrong fingerprint refusal |
| Embedding provenance is explicit | baseline evidence + manifest collection specs | missing/model/dimension/config mismatch refusals |
| Provenance identity is preserved | baseline conversion/evidence; no ledger-only identity | exact envelope/`assertion_id`/`provenance_commitment` preservation; no dedupe/remint |
| `RETAINED_ROLLBACK_BASELINE` is protected, not serving | baseline evidence; store protection map; mixed inventory | baseline non-serving test; stage-`G_canary` test; reopen retention test |
| CAS and durable rollback lineage are separate | `file_generation_pointer.py` public APIs/private writer | forward, first-cutover, rollback pointer-field matrix |
| Ordinary publish cannot create first pointer | `publish_active_pointer` | `expected_active=None` refusal test |
| First cutover has exact `G_rb` and `G_canary` | baseline evidence + `cg2_first_cutover.py` | exact IDs/SHAs/owner/source/qualification tests |
| `G_rb != G_canary` | first-cutover preflight | equality refusal before fence |
| Pre-fence refusal remains LEGACY | preflight before commit phase | missing/corrupt/wrong-owner/wrong-SHA/non-equivalent matrix |
| Post-fence failure is `FENCED_NO_POINTER` | one-lock fence/guard/pointer sequence; authority resolver | injected crash between fence and pointer; serving-open refusal |
| `FENCED_NO_POINTER` resumes only under fresh exact grant | dedicated first-cutover resume path; immutable fence/guard validation | fence→crash→resume; fence→guard→crash→resume; wrong-guard refusal |
| Fence never clears to recover LEGACY | immutable fence; no delete API | fence byte identity across failure/rollback/recovery |
| Forward stale source refuses | ordinary/first forward source check | existing + Design A stale-source tests |
| Rollback may follow source advance | `rollback_active_pointer` | source-advanced exact retained-generation rollback test |
| Newer desired source remains durable | existing reconciliation state helper | persistence/restart/coalescing test after rollback |
| Rollback never resurrects LEGACY | rollback pointer path + monotonic fence | authority mode and row-selection assertions |
| Recovery cannot switch generation | exact-payload recovery only | alternate complete generation negative test/signature test |
| Every authority change owns one owner-lock interval | public orchestration + shared private lock-held pointer writer | reentry-failing/counting `source_flock` oracle for first cutover and rollback |
| No second serving promotion during canary | immutable open guard checked by forward APIs | second ordinary/first-cutover refusal; rollback/recovery allowed |
| Frozen generation stays stable mid-request | existing `ServingIndexRepository` frozen vector | dedicated pointer-change-mid-request test |
| GC disabled / baseline retained | `PHYSICAL_DELETION_DISABLED`; retention inventory | baseline survives cutover/rollback/reopen; no delete call |

## 9. Evidence classes and gate semantics

### Mechanical evidence

- Focused tests named in D1–D5 at exact implementation SHA.
- Full repository pytest result at the same SHA.
- Static API/signature evidence that recovery accepts no target and ordinary
  publish accepts no first-pointer path.
- Property map with exact pytest node IDs, including dedicated
  `FrozenGenerationStable`.
- `git diff --check` and no unplanned surface changes.

### Hermetic rehearsal evidence

One temporary-root run must exercise real public Design A APIs, not mocks of
the transition under test. It must use temporary Chroma only; it must not open
live Chroma through hermetic `FileGenerationStore` or modify
`chroma_write_store.py`:

```text
LEGACY snapshot
→ exact convert-v1 G_rb
→ fresh qualification + equivalence
→ exact G_canary qualification
→ fence → crash → fresh-grant resume
→ fence → guard → crash → fresh-grant resume
→ wrong-guard fail-closed control
→ exact first pointer
→ source advance
→ rollback_active_pointer to G_rb
→ restart
→ recover exact rolled-back pointer
```

Evidence must include exact IDs/SHAs, pointer before/after, fence/guard hashes,
reconciliation state hash, retention inventory, production paths absent, and
`physical_deletion_disabled=true`. The rehearsal also records fresh grant
identities for both resume cases and the one-acquisition owner-lock oracle for
first cutover and rollback.

**V6c remains PENDING** until this drill uses the implemented, real
`rollback_active_pointer` and passes at the reviewed implementation tip.
Previous-generation retention tests alone do not satisfy V6c. A mocked pointer
rewrite does not satisfy V6c.

### Independent-review evidence

The independent reviewer receives one exact implementation/model tip and must
explicitly answer:

1. Did implementation preserve locked Design A without reopening alternatives?
2. Are rollback and recovery distinct in API and behavior?
3. Can any pre-fence failure publish a fence, or any post-fence failure restore
   LEGACY?
4. Does source-advanced rollback durably preserve newer desired state before
   pointer switch?
5. Can any ordinary path bypass exact `G_rb`/`G_canary` or the canary guard?
6. Does the formal model cover the implemented transitions at the same tip?
7. Were production roots/configuration/operations untouched?

PASS/FAIL must name the exact SHA. Deferral or review of a different revision is
not sign-off.

### Later production-generation and live-canary evidence

These require separate Ryan grants and are not performed by this plan or
Design A Execute:

- exact production owner/source selection and alias eligibility;
- exact production `G_rb` build/qualification/equivalence/provenance evidence;
- exact production `G_canary` build/qualification/provenance/source-freshness
  evidence;
- complete pre-grant packet binding both IDs and both manifest SHAs plus exact
  implementation SHA;
- after V8c grant, fence hash, first pointer payload, open guard, authority
  resolution, no second promotion, GC-off/retention, doctor and retrieval
  evidence;
- if separately granted, operational rollback evidence proving exact retained
  restoration and durable desired-source debt after source advance;
- separate later canary-close evidence and Ryan decision.

**V8c remains PENDING.** It can pass only when Ryan accepts the complete packet
and issues the exact one-shot activation grant. Execute, V6c PASS, independent
review, production generation builds, or packet preparation alone do not make
V8c PASS. Canary completion remains a later decision.

## 10. Final Execute-close bundle before V8c packet preparation

Before any lane asks to build production generations or prepare a V8c packet,
the Design A Execute-close bundle must contain:

1. canonical architecture base `8aff0a316cb4304c5313556abc3cdf5439746835`;
2. Ryan-approved execution-plan commit and exact implementation tip;
3. planned-files-only diff inventory;
4. focused and full pytest commands/results;
5. hermetic rehearsal JSON with real public APIs and no live paths;
6. V6c result, remaining PENDING unless the real rollback drill criteria above
   are fully met;
7. all four TLC command/results, tool checksum, state counts, depth, coverage,
   and zero-error status, with 2026-08-14 evidence labeled historical only;
8. architecture-invariant → implementation → exact test-node map;
9. independent-review PASS at the same implementation/model tip;
10. explicit confirmations: no production root provisioned, no production
    `G_rb`/`G_canary` built, no fence/pointer published, no packet/grant, no
    activation, no canary closure, no GC, no Shadow, no R2b;
11. residual risks and any deferred operational evidence;
12. Ryan stop/HITL request for the next separately bounded phase.

Production `G_rb` and `G_canary` identities are necessarily absent from this
Execute-close bundle because their build is a later separately granted phase.
They must exist and be exact before the later V8c packet can be complete.

## 11. Global stop conditions

Stop and report to Luna/Ryan if any of the following occurs:

- A locked requirement is internally contradictory or cannot be represented
  without changing architecture.
- Exact legacy logical equivalence or embedding provenance cannot be proved.
- The implementation needs production paths, config, generation-root
  provisioning, or a live corpus to pass tests.
- Ordinary publication can bypass first cutover or the open-canary guard.
- Rollback and recovery share a target-selection path.
- Successful source-advanced rollback can occur without durable reconciliation
  obligation.
- Any failure path removes the fence or resolves a post-fence owner as LEGACY.
- A `FENCED_NO_POINTER` resume can reuse an old grant, accept non-identical
  fence/guard evidence, or overwrite a conflicting artifact instead of
  requiring operator repair.
- First cutover or rollback reacquires `source_flock`, calls a public pointer
  API while already locked, or requires changing `source_flock` to permit
  nesting.
- `G_rb` becomes abandoned, GC-eligible, or serving without active pointer
  selection.
- A formal counterexample, zero-coverage required transition, unexplained test
  failure, or full-suite timeout remains.
- Required work expands into GC, Shadow, R2b, rename migration, production
  activation, or V8c packet/grant work.

The required contradiction report is exactly:

```text
UNRESOLVED — Ryan decision required
```

## 12. Handoff and authorization sequence

1. Luna checks this plan for scope drift and contradictions.
2. Ryan reviews and either revises or grants Design A Execute against this exact
   planning commit.
3. Cursor implements D1–D7 on a fresh branch from the Ryan-named base; commit
   and push every slice.
4. Independent review signs the exact implementation/model tip.
5. Ryan receives the Execute-close bundle and decides whether to authorize the
   later production-generation build/evidence phase.
6. Only after exact production `G_rb` and `G_canary` exist and the full packet
   is independently reviewed may Ryan consider V8c.

No plan approval implies implementation authority. No implementation or V6c
PASS implies production generation-build authority. No complete packet implies
V8c. No V8c grant implies fence or pointer publication. No V8c PASS implies
canary completion.
