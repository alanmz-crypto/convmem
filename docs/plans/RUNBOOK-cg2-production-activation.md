# Operator runbook — CG-2 production activation

**Scope:** CG-2 production activation operations. The 2026-08-22 legacy exact-
vector bootstrap amendment is an adversarial-review candidate that supersedes
the Design A architecture lock at
`8aff0a316cb4304c5313556abc3cdf5439746835` only after independent review and
Ryan ratification. The execution plan at
`c48d9a9cc2b20df6d9a834f3e4377046504fed76` remains **BLOCKED** and must not be
rewritten until then. This runbook does **not** authorize D0 production capture,
D1 resumption, D2, production owner activation, fence/pointer publication,
`G_rb`/`G_canary` builds, GC, Shadow, or R2b until Ryan issues each matching
exact grant.

## Required grants (Ryan only)

| Step | Grant | What it unlocks |
|------|--------|-----------------|
| Execute (T1–T5) | **DONE** — Kiro PASS; Ryan grant at execution plan `6a808f1` | Prior implementation on feature branch (merged) |
| Architecture amendment | Independent Claude adversarial review + Ryan ratification (pending) | Allows the blocked Design A execution plan to be rewritten; unlocks no implementation or production operation |
| D0 capture | Separate one-shot grant naming owner, read-only persisted-data scope, and exact producer SHA (not issued) | Create one candidate exact-vector attestation only; candidate is not authority |
| Independent D0 validation | Separately assigned independent validation at exact candidate/producer identity (not complete) | Reproduce exact covered row/vector/snapshot roots read-only and publish hash-bound validation evidence; does not ratify |
| Ryan D0 ratification | Exact Ryan ratification naming candidate SHA, validation-result SHA, owner, roots, producer, capture identity/time, and the candidate/validator-equal `query_embedding_context_sha256` (not issued) | Makes the exact three-part D0 chain consumable by a later separately authorized D1; authorizes no build/cutover |
| Amended Design A Execute | Superseding execution plan + Ryan grant after architecture ratification (not yet) | Implement amended D0/D1 contracts and later Design A APIs/tests only; no production operation |
| Legacy-only gateway soak | **DONE** — V8b PASS (grant); soak completion ACCEPTED 2026-08-21 | Production config pointing all owners `LEGACY` through serving repository |
| First generational owner (V8c) | Exact one-shot activation grant naming exact SHA, owner, `G_rb`, `G_canary` | Fence + `publish_first_cutover_active_pointer` for one owner only |
| Canary completion | Separate later Ryan decision + evidence record | Close first-canary window; not implied by V8c PASS |
| Automatic GC / compaction | Independent evidence + sub-grant | Physical deletion of inactive generations |

Silence on squash-merge = squash OK.

## Evidence artifacts

| Artifact | Path |
|----------|------|
| Architecture (amendment candidate) | `docs/plans/ARCHITECTURE-cg2-production-activation.md` (prior lock `8aff0a3`; exact-vector amendment pending independent review/Ryan ratification) |
| Blocked Design A execution plan | `docs/plans/EXECUTION-cg2-design-a.md` @ `c48d9a9cc2b20df6d9a834f3e4377046504fed76` — do not rewrite yet |
| D0 candidate attestation | Future content-addressed artifact under the fixed governed D0 authority root |
| Independent D0 validation | Future separately produced content-addressed validation evidence under that root; exact validation-result SHA required |
| Ryan D0 ratification | Future Ryan-controlled durable record under that root binding candidate + validation evidence exactly |
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

Do **not** resume D1 or open the V8c GATE until the preceding authority and
architecture gates are exact. The mandatory order is:

```text
independent adversarial architecture review
→ Ryan architecture-amendment ratification
→ rewrite + ratify the superseding execution plan
→ D0 capture grant
→ D0 candidate capture
→ independent read-only D0 reproduction/validation
→ Ryan ratifies exact candidate + validation evidence
→ separately authorized D1 consumes exact ratified D0
→ build + cold-qualify exact G_rb (convert-v1)
→ build + cold-qualify exact G_canary
→ complete independent review / evidence packet
→ Ryan V8c GATE
→ V8c PASS / one-shot activation grant
→ fence + exact first-cutover operation
→ canary window (no further serving promotion)
→ separate canary completion decision
```

Packet **before grant** must already bind:

- exact `G_rb.generation_id` + `G_rb.manifest_sha256`
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
- exact `G_rb` retained rollback-baseline evidence SHA
- `G_canary` proof profile=`KNOWN_MODEL_AND_VECTOR_V1`, writer-produced model
  provenance, and exact vector identity
- qualification evidence
- exact implementation SHA

No “fill `G_canary` at cutover.” No post-grant packet amendment to discover the
target. If source / current authority / preconditions change after grant but
before publication, first-cutover **refuses**; that one-shot grant is
stale/unused; require a **new packet + new V8c grant**.

D0 capture, independent validation, and Ryan D0 ratification are three distinct
states. A candidate self-hash is not authority. Changing and rehashing the D0
candidate or validation result invalidates ratification. None of these D0 states
authorizes a production `G_rb`/`G_canary` build, fence, pointer, or owner
activation.

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

The three evidence objects are immutable non-serving evidence under one fixed
governed D0 authority root. They are not a pointer, serving authority, a second
database, or another owner-state machine. Exact layout remains for the amended
execution plan.

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
- Architecture amendment lacks exact-revision independent PASS or Ryan
  ratification (execution-plan rewrite remains blocked)
- Missing D0 capture grant, candidate, independent validation evidence, or Ryan
  D0 ratification
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
- Stored retained evidence is normalized around `sequence_positions`, or
  authority use trusts stored qualification instead of rerunning a fresh process
- Provenance-envelope evidence can be removed, swapped, mutated, substituted,
  or rehashed without refusal
- The live canonical `QUERY_EMBEDDING_CONTEXT_V1` cannot be resolved, or its
  `query_embedding_context_sha256` is not exactly equal to the D0-ratified
  value, during D1, first cutover, or rollback; no fuzzy/same-dimension/current-
  config shortcut
- Exact `G_rb` vectors, D0 authority, retained evidence, or required recovery
  evidence are lost/mismatched; do not re-embed or synthesize a replacement
- Restore lacks the complete D0 candidate + independent validation + Ryan
  ratification chain; non-authoritative backup evidence cannot substitute
- Ambiguous owner/alias state
- Baseline/precondition failure for grant-bound `G_rb` **before** durable fence
  (pause / refuse; no fence, no pointer, no activation)
- Baseline/precondition failure **after** durable fence (owner stays
  `FENCED_NO_POINTER`; never LEGACY; fence monotonic; pause for repair /
  fresh grant as required — do not resurrect LEGACY)
- First pointer would have `previous_generation_id=None` (refuse; Design A)
- Attempted further serving promotion during the first-canary window (refuse)

## First cutover (only after V8c one-shot grant)

1. Confirm packet binds exact `G_rb`, exact `G_canary`, both proof profiles, the
   complete D0 candidate/validation/Ryan chain, roots, canonical
   `QUERY_EMBEDDING_CONTEXT_V1`, its D0-ratified
   `query_embedding_context_sha256`, and exact retained-evidence SHA; confirm
   the grant names both generations.
2. Revalidate every digest and grant precondition (source, authority, baseline
   structure). Re-derive the live context from the governed query adapter and
   actual selected model/runtime; require exact equality of its SHA-256 to the
   D0-ratified `query_embedding_context_sha256`.
3. In the one existing `source_flock` acquisition for the public authority-
   changing operation, revalidate exact `LEGACY` authority and independently
   reread/rebind the complete D0-covered LEGACY row/vector/provenance roots.
   A stored D1 snapshot is not this rebind. Any mismatch returns before fence.
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
| Restore retained prior generation | `rollback_active_pointer` | Fresh-qualify exact retained gen plus D0 chain and retained-evidence SHA; require exact live-versus-D0-ratified `query_embedding_context_sha256` equality; may proceed after source advance; leave durable reconciliation-required for newer source; fence monotonic; never LEGACY |
| Same-pointer durability repair | `recover_active_pointer` | Exact current pointer bytes only; **never** switches generation |

Do **not** delete physical rows during rollback; GC remains disabled.
Re-run `convmem doctor` and VERIFY V6 checks after either path.

## Rollback posture (first canary — when separately granted)

1. Record active `generation_id` and `previous_generation_id` (`G_rb`) from the
   qualified pointer.
2. Revalidate the exact D0 candidate/validation/Ryan chain, `G_rb` manifest and
   retained-evidence SHA, cold-readable vector roots, and canonical live
   `QUERY_EMBEDDING_CONTEXT_V1`. Require its
   `query_embedding_context_sha256` to equal the D0-ratified value exactly;
   missing/unresolvable context or unequal hashes fail closed.
3. Rerun fresh-process qualification; never trust only the stored qualification
   record.
4. Use **`rollback_active_pointer`** to restore exact `G_rb` (not
   `recover_active_pointer`).
5. If live source has advanced past the retained baseline, leave
   reconciliation-required durable and enqueue desired state.
6. Do **not** resurrect LEGACY; do **not** remove the fence.
7. Do not re-embed, replace the D0-ratified semantic query context, or synthesize
   a same-identity replacement if `G_rb` or its authority is unavailable. A
   semantic context change requires a separately designed migration/transition.
8. Re-run `convmem doctor` and VERIFY V6 checks.

## Complete-data backup and restore posture

While `G_rb` is retained, one governed complete-data recovery set must preserve
and jointly verify:

- actual `G_rb` rows/vectors;
- manifest and exact retained rollback-baseline evidence;
- D0 candidate attestation and independent validation evidence;
- Ryan D0 ratification record;
- applicable pointer/fence/first-canary-guard state;
- canonical `QUERY_EMBEDDING_CONTEXT_V1` payload and D0-ratified
  `query_embedding_context_sha256`.

STOP if any item is outside the governed backup scope, missing after restore, or
does not reproduce its ratified digest/root. Classify the restored owner
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

- Rewriting `EXECUTION-cg2-design-a.md` before independent amendment review and
  Ryan architecture ratification
- D0 production capture without its exact one-shot grant
- Treating a D0 candidate or independent validation self-hash as authority
- D1 resumption or D2
- Production configuration change without the matching grant
- Legacy fence or production pointer publication without V8c grant
- Building `G_rb` / `G_canary` without Design A Execute grant
- Inferring historical embedding-model identity or reconstructing `G_rb` by
  re-embedding/substitution
- Activation manifest without V8c grant
- Automatic inactive-generation deletion or Chroma queue surgery
- Shadow / R2b work
