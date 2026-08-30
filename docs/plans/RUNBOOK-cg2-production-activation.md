# Operator runbook — CG-2 production activation

**Scope:** CG-2 production activation operations under Ryan's 2026-08-29 D1
reference-v2 semantic lock. `G_rb` is a retained reference to the exact original
D0-covered LEGACY rows, never a copied Chroma generation. This planning update
does **not** authorize implementation, D1 retry, failed-state cleanup, D2,
production owner activation, `G_canary`, V8c, fence/pointer publication, GC,
Shadow, R2b, or D2+.

## Required grants (Ryan only)

| Step | Grant | What it unlocks |
|------|--------|-----------------|
| Execute (T1–T5) | **DONE** — Kiro PASS; Ryan grant at execution plan `6a808f1` | Prior implementation on feature branch (merged) |
| D1 reference-v2 architecture | **LOCKED** by Ryan 2026-08-29 | Fixes semantics only; unlocks no implementation or production operation |
| Corrective plan review | Independent Kiro PASS on exact planning SHA + Ryan acceptance (pending) | Makes the package eligible for a bounded Cursor implementation grant only |
| Existing D0 chain | **RATIFIED / unchanged**: candidate `d4be814a…`, validation `4af93884…`, Ryan record `ryan-d0-webui-2026-08-29` | Read-only input to reference-v2; no recapture/reratification authorized or required |
| Reference-v2 Execute | Separate Ryan grant naming exact reviewed planning SHA and allowed files (not issued) | Implement manifest/evidence, target-aware reader, qualification, recovery binding, tests/property/model only; no production operation |
| Production D1 reference publication | Separate one-shot grant after implementation review (not issued) | Construct and qualify one reference-v2 target; no cutover or canary |
| Legacy-only gateway soak | **DONE** — V8b PASS (grant); soak completion ACCEPTED 2026-08-21 | Production config pointing all owners `LEGACY` through serving repository |
| First generational owner (V8c) | Exact one-shot activation grant naming exact SHA, owner, `G_rb`, `G_canary` | Fence + `publish_first_cutover_active_pointer` for one owner only |
| Canary completion | Separate later Ryan decision + evidence record | Close first-canary window; not implied by V8c PASS |
| Automatic GC / compaction | Independent evidence + sub-grant | Physical deletion of inactive generations |

Silence on squash-merge = squash OK.

## Evidence artifacts

| Artifact | Path |
|----------|------|
| Architecture corrective | `docs/plans/ARCHITECTURE-cg2-production-activation.md` — retained-reference-v2 semantics locked by Ryan; package review pending |
| Corrective execution plan | `docs/plans/EXECUTION-cg2-design-a.md` — implementation authority only after independent review + Ryan grant |
| D0 candidate attestation | Existing immutable artifact `d4be814abc59e77a2d1420b6d7db8859f5a5fe6f449f107fbdd23eb9aecaa0be` |
| Independent D0 validation | Existing immutable evidence `4af9388454e80dedeb6988500647d2766333e22d4e5fecacadf055d14b667793` |
| Ryan D0 ratification | Existing durable record `ryan-d0-webui-2026-08-29` |
| Failed copied D1 | `2d01dfca08ac388e7ac74d145e789a8a35d8b97c4bf2ee6d971a95a8a74c4b3c` — untouched, quarantined, never reuse/activate |
| Execution plan (prior) | `docs/plans/EXECUTION-cg2-production-activation.md` @ `6a808f1` |
| VERIFY (mechanical + gates) | `docs/plans/VERIFY-cg2-production-activation.md` |
| Formal model map | `docs/plans/formal/cg2/README.md` |
| Property → test map | `cg2_property_map.py` |
| Rehearsal bundle | `cg2_rehearsal.py` (`collect_execute_evidence`) |

## Preflight

```bash
cd ~/Projects/convmem
convmem doctor
convmem brief --stdout-only
git fetch origin && git status
```

Require: `logical_projection` PASS, `source_reconciliation` fresh or WARN only,
no unpushed commits on the implementation branch before PR.

## Design A pre-GATE order (before Ryan V8c)

Do **not** retry D1 or open the V8c GATE until the corrective planning and
implementation gates are exact. The mandatory order is:

```text
Ryan locks reference-v2 semantics (DONE)
→ corrective architecture/execution/runbook/VERIFY/property/formal plan
→ independent Kiro review of exact planning SHA
→ Ryan accepts exact planning SHA
→ bounded Cursor implementation grant
→ implement + mechanically verify reference-v2 at one exact tip
→ independent implementation/model review
→ separate production D1 grant
→ D1 consumes the existing ratified D0 chain
→ publish + fresh-process serving-qualify exact G_rb reference-v2
→ prove complete-data recovery coverage
→ establish RETAINED_ROLLBACK_BASELINE
→ build + cold-qualify exact G_canary
→ complete independent review / evidence packet
→ Ryan V8c GATE
→ V8c PASS / one-shot activation grant
→ fence + exact first-cutover operation
→ canary window (no further serving promotion)
→ separate canary completion decision
```

Packet **before grant** must already bind:

- exact `G_rb` target ID + reference-v2 manifest SHA-256/fingerprint
- exact `G_canary.generation_id` + `G_canary.manifest_sha256`
- production pipeline fingerprints and source hashes
- `G_rb` proof profile=`LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`, with
  `historical_embedding_model.status=UNKNOWN` and identifier `null`
- exact D0 artifact SHA-256 and independent D0 validation-result SHA-256
- Ryan D0 ratification reference binding both evidence digests, owner, accepted
  snapshot/vector roots, producer SHA, capture identity/timestamp, and the exact
  candidate/validator-equal `query_embedding_context_sha256`
- aggregate/per-collection D0 snapshot/vector roots, canonical
  `QUERY_EMBEDDING_CONTEXT_V1` payload, and exact D0-ratified
  `query_embedding_context_sha256`
- exact target-aware serving-selector fingerprint and ordered physical-ID root
- exact rollback-baseline-evidence-v2 SHA and recovery-coverage evidence
- `G_canary` proof profile=`KNOWN_MODEL_AND_VECTOR_V1`, writer-produced model
  provenance, and exact vector identity
- qualification evidence
- exact implementation SHA

No “fill `G_canary` at cutover.” No post-grant packet amendment to discover the
target. If source / current authority / preconditions change after grant but
before publication, first-cutover **refuses**; that one-shot grant is
stale/unused; require a **new packet + new V8c grant**.

D0 capture, independent validation, and Ryan D0 ratification remain three
distinct states. The existing exact chain is valid and immutable. Changing and
rehashing either artifact invalidates ratification; this corrective neither
changes nor recreates them. D1 adds supplementary reference/selector/cold-
serving/recovery evidence only.

D0 candidate capture holds the existing owner `source_flock` for one unchanged
accepted `LEGACY` read, with authority/collection/count/root/context checks
before release; churn refuses. Row leaves are independent of Chroma insertion
order and sort by exact UTF-8
`(collection_name, conversion_logical_id, physical_id)`; missing/duplicate
ordering identities refuse. Independent validation is a separate role and
execution that later rereads persisted state under the same existing lock/
consistency protocol, reproduces the roots, and re-derives the exact
`query_embedding_context_sha256` through the governed query path. It may reuse
the reviewed algorithm, but one self-attesting execution must not issue both
evidence objects.

The three D0 objects are immutable non-serving evidence under one fixed governed
authority root. The reference-v2 manifest is a selector, not a second vector
database. Its exact original Chroma rows become rollback serving state only
when the pointer selects the target and the target-aware reader consumes them.

For the semantic query-vector space, use only Architecture §7.0.1a
`QUERY_EMBEDDING_CONTEXT_V1`. Resolve the actual query model artifact digest,
quantization, dimension, deterministic pipeline fingerprint, and Ollama runtime
identity/version. Do not hash hostname, endpoint authority, credentials,
timeouts, retries, PID, or deployment path. Every field is required/non-null;
failure to resolve one field refuses D0.

## Pause conditions (do not proceed to soak/canary/cutover)

- Any `logical_projection` FAIL or authority failure in doctor
- `source_reconciliation` stale beyond `max_reconciliation_staleness` (300s default)
- Mixed-mode proof gate FAIL (`authorized_cardinality` or `authority_safety`)
- Unexplained eval/gateway divergence during granted soak
- Corrective planning or implementation lacks exact-revision independent PASS
  and Ryan acceptance/grant
- Existing D0 candidate, validation evidence, or Ryan ratification is missing
- Candidate artifact SHA or independent validation-result SHA differs from
  Ryan's ratification
- Independent validation cannot reproduce the exact covered row/vector/
  provenance/snapshot roots from read-only persisted data
- Current config, dimension, Chroma default, caller input, or present-day
  setting is offered as historical embedding-model authority
- `G_rb` does not use exact `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` semantics
  with historical model status `UNKNOWN` and identifier `null`
- `G_canary` or a later prospective generation uses an unknown-model profile or
  lacks `KNOWN_MODEL_AND_VECTOR_V1` writer evidence
- D1 cannot independently reread/rebind the exact D0-covered LEGACY rows under
  the owner lock, or any row/vector/provenance/root drifts
- Reference-v2 selector does not resolve exactly the original collection UUIDs,
  canonical configuration, and physical IDs
- Cold qualification, first-cutover rebind, and rollback serving do not use the
  same target-aware row reader
- Any Chroma copy/upsert, `.f32le`/sidecar vector authority, re-embedding, or
  normalization reconstruction participates in `G_rb`
- Stored evidence is trusted instead of rerunning fresh-process serving-path
  qualification
- Provenance-envelope evidence can be removed, swapped, mutated, substituted,
  or rehashed without refusal
- The live canonical `QUERY_EMBEDDING_CONTEXT_V1` cannot be resolved, or its
  `query_embedding_context_sha256` is not exactly equal to the D0-ratified
  value, during D1, first cutover, or rollback; no fuzzy/same-dimension/current-
  config shortcut
- Exact referenced original rows, D0 authority, rollback-baseline evidence v2,
  serving-selector binding, or required recovery evidence are lost/mismatched;
  do not copy, re-embed, or synthesize a replacement
- Restore lacks the complete D0 candidate + independent validation + Ryan
  ratification chain; non-authoritative backup evidence cannot substitute
- Ambiguous owner/alias state
- Baseline/precondition failure for grant-bound `G_rb` **before** durable fence
  (pause / refuse; no fence, no pointer, no activation)
- Baseline/precondition failure **after** durable fence (owner stays
  `FENCED_NO_POINTER`; never LEGACY; fence monotonic; pause for repair /
  fresh grant as required — do not resurrect LEGACY)
- First pointer would have `previous_generation_id=None` (refuse; Design A)
- Failed copied ID `2d01dfca…` is offered for reuse, activation, cleanup, or as
  the corrected target (refuse; no mutation)
- A `G_RB_CONVERT_COLD_VALIDATED` or `abandoned_d1` record is required or offered
  (stop; neither is authorized)
- Attempted further serving promotion during the first-canary window (refuse)

## First cutover (only after V8c one-shot grant)

1. Confirm packet binds exact reference-v2 `G_rb`, exact `G_canary`, both proof profiles, the
   complete D0 candidate/validation/Ryan chain, roots, canonical
   `QUERY_EMBEDDING_CONTEXT_V1`, its D0-ratified
   `query_embedding_context_sha256`, target-aware serving-selector fingerprint,
   rollback-baseline-evidence-v2 SHA, and recovery coverage; confirm the grant
   names both targets.
2. Revalidate every digest and grant precondition (source, authority, baseline
   structure). Re-derive the live context from the governed query adapter and
   actual selected model/runtime; require exact equality of its SHA-256 to the
   D0-ratified `query_embedding_context_sha256`.
3. In the one existing `source_flock` acquisition for the public authority-
   changing operation, revalidate exact `LEGACY` authority and independently
   reread/rebind through the target-aware serving reader the complete D0-covered
   LEGACY row/vector/provenance roots. A stored D1 snapshot or sidecar is not
   this rebind. Any mismatch returns before fence.
4. Publish monotonic fence; then `publish_first_cutover_active_pointer` with
   `expected_active=None`, `previous_generation_id=G_rb`, target=`G_canary`.
5. If cutover fails **before** the fence is durable: refuse; leave no fence.
   If failure is discovered **after** a durable fence: remain
   `FENCED_NO_POINTER`; **never LEGACY**.
6. Do **not** promote a second serving generation for that owner during the
   canary window.
7. GC remains disabled.

## Rollback vs recovery (do not conflate)

| Need | Operation | Notes |
|------|-----------|--------|
| Restore retained prior target | `rollback_active_pointer` | Fresh-qualify exact reference-v2 target through serving reader plus D0 chain, evidence-v2 SHA, and recovery binding; require exact live-versus-D0-ratified `query_embedding_context_sha256` equality; may proceed after source advance; leave reconciliation-required; fence monotonic; never LEGACY |
| Same-pointer durability repair | `recover_active_pointer` | Exact current pointer bytes only; **never** switches generation |

Do **not** delete physical rows during rollback; GC remains disabled.
Re-run `convmem doctor` and VERIFY V6 checks after either path.

## Rollback posture (first canary — when separately granted)

1. Record active `generation_id` and `previous_generation_id` (`G_rb`) from the
   qualified pointer.
2. Revalidate the exact D0 candidate/validation/Ryan chain, reference-v2
   manifest, evidence-v2 SHA, collection UUID/configuration, ordered physical
   IDs, target-aware serving-reader output, recovery coverage, and canonical live
   `QUERY_EMBEDDING_CONTEXT_V1`. Require its
   `query_embedding_context_sha256` to equal the D0-ratified value exactly;
   missing/unresolvable context or unequal hashes fail closed.
3. Rerun fresh-process qualification through the same target-aware reader used
   by serving; never trust only the stored qualification record.
4. Use **`rollback_active_pointer`** to restore exact `G_rb` (not
   `recover_active_pointer`).
5. If live source has advanced past the retained baseline, leave
   reconciliation-required durable and enqueue desired state.
6. Do **not** resurrect LEGACY; do **not** remove the fence.
7. Do not copy, re-embed, replace the D0-ratified semantic query context, or
   synthesize a same-identity replacement if `G_rb` or its authority is unavailable. A
   semantic context change requires a separately designed migration/transition.
8. Re-run `convmem doctor` and VERIFY V6 checks.

## Complete-data backup and restore posture

While `G_rb` is retained, one governed complete-data recovery set must preserve
and jointly verify:

- original referenced Chroma collections and exact D0-covered physical
  rows/vectors, including collection UUID/configuration;
- reference-v2 manifest, exact serving selector, and rollback-baseline evidence
  v2;
- D0 candidate attestation and independent validation evidence;
- Ryan D0 ratification record;
- applicable pointer/fence/first-canary-guard state;
- canonical `QUERY_EMBEDDING_CONTEXT_V1` payload and D0-ratified
  `query_embedding_context_sha256`.

STOP if any item is outside the governed backup scope, missing after restore, or
does not reproduce its ratified digest/root through the target-aware serving
reader. Classify the restored owner
`BLOCKED`/quarantined. Existing backup capture evidence remains
non-authoritative and cannot substitute for D0 or Ryan ratification. Restore
must not re-embed current source or use current config to claim restoration of
the same `G_rb`.

## V8c vs canary completion

| Gate | Meaning |
|------|---------|
| **V8c PASS** | Complete first-owner packet accepted + exact one-shot activation grant issued |
| **Canary completion** | Separate later evidence record and Ryan decision |

Do **not** treat V8c PASS as canary completion. Do **not** mark V8c PASS in
docs until Ryan issues the grant.

## Mechanical verification (isolated — no live corpus)

```bash
python -m pytest tests/test_cg2_rehearsal.py tests/test_serving_index_repository.py \
  tests/test_mixed_mode_proof.py tests/test_logical_accounting.py \
  tests/test_source_reconciler.py -q
```

Full suite before PR:

```bash
python -m pytest -q
```

## What this runbook deliberately does **not** authorize

- Implementing the corrective before independent plan review and Ryan grant
- D0 capture, validation, evidence changes, or reratification
- Treating a D0 candidate or independent validation self-hash as authority
- Production D1 retry or D2
- Production configuration change without the matching grant
- Legacy fence or production pointer publication without V8c grant
- Publishing reference-v2 `G_rb` / building `G_canary` without matching grants
- Inferring historical embedding-model identity or constructing `G_rb` by
  Chroma copy/upsert, sidecar authority, re-embedding, normalization
  reconstruction, or substitution
- Reusing, activating, cleaning, or deleting failed `2d01dfca…`
- Adding `G_RB_CONVERT_COLD_VALIDATED` or `abandoned_d1`
- Activation manifest without V8c grant
- Automatic inactive-generation deletion or Chroma queue surgery
- Shadow / R2b work
