# Execution Plan — CG-2 Design A retained-reference-v2 corrective

```text
Planning Status

Phase:        D1 Reference-v2 Corrective Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Codex authors locked corrective plan; Kiro independently reviews; Ryan HITL; Cursor implements only after grant
Authority:    Ryan semantic lock accepted; exact planning package awaits independent review and Ryan acceptance
```

**Arc:** CG-2 Design A → Production Activation → D1 `G_rb` architecture corrective

**This plan SUPERSEDES the blocked execution plan at:**

`c48d9a9cc2b20df6d9a834f3e4377046504fed76`

That prior plan assumed caller-supplied historic embedding provenance and had no
D0 exact-vector authority substrate. The later convert-v1 execution plan added
D0 but incorrectly defined `G_rb` as a copied cosine Chroma generation. The
production attempt refused at bidirectional equivalence, and two independent
reviews rejected the sidecar corrective because qualification and serving
would consume different physical vector states. This plan replaces only that
D1 meaning under Ryan's 2026-08-29 retained-reference-v2 lock.

**Pre-corrective D0/Design A architecture base (historical input):**

`3d8b151907f02c8b8ead89585fb43904840b210b`

[`ARCHITECTURE-cg2-production-activation.md`](ARCHITECTURE-cg2-production-activation.md),
[`RUNBOOK-cg2-production-activation.md`](RUNBOOK-cg2-production-activation.md), and
[`VERIFY-cg2-production-activation.md`](VERIFY-cg2-production-activation.md) as
present at the ratified architecture SHA.

**Corrective semantic authority:** Ryan's 2026-08-29
`CG-2 D1 Architecture Corrective Lock`. The exact corrective planning SHA is
assigned by this branch commit and becomes reviewable authority only after
independent PASS and Ryan acceptance.

**Superseded architecture lock (historical only):**

`8aff0a316cb4304c5313556abc3cdf5439746835`

**Blocked reusable implementation checkpoint (NOT D1 authority):**

`fca6526e6ae4d5cf008afa8a2f465fd2c37bfa23` on branch
`feat/2026-08-21-cg2-design-a-execute`

**Goal:** translate the locked retained-reference architecture into a bounded,
mechanically executable corrective that preserves D0, rewrites D1 so proof and
rollback serving consume the same original rows, and carries D2–D7 forward only
where compatible.

**Plan status:** planning only. This document authorizes no Python, test, formal
model, configuration, corpus, D0 mutation, generation-root mutation, failed-
generation cleanup, fence, pointer, activation, packet, grant, GC, Shadow, or
R2b change.

## Human consequence

If Ryan approves this superseding plan, Cursor may implement Design A in bounded
hermetic slices on a fresh implementation branch anchored after this planning
commit. The result will preserve the complete ratified D0 chain, make `G_rb` a
versioned reference to the original D0-covered Chroma rows under
`LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`, use one target-aware reader for cold
qualification and rollback serving, and preserve the prior Design A
cutover/rollback separation.

Approval of this plan would authorize only hermetic implementation, tests,
formal verification, rehearsal, and Execute evidence. It would **not** authorize
production D0 mutation, production `G_rb`, production `G_canary`, failed-state
cleanup, production fence/pointer publication, first-owner
activation, V8c PASS/grant, canary closure, GC, Shadow, or R2b. Those remain
separate HITL gates.

### 5 Ws

| Field | Answer |
|---|---|
| **Who** | Cursor implements only after Ryan accepts the independently reviewed exact planning commit; Kiro reviews the implementation tip; Ryan alone gates D1 production execution and V8c. |
| **What** | D1 reference-v2 manifest/evidence + target-aware serving reader + recovery binding + D2–D7/property/formal corrections. |
| **When** | After Ryan's 2026-08-29 semantic lock and independent review of this exact plan; before any D1 retry. |
| **Why** | Re-upserting D0 readback vectors into cosine Chroma changes float32 bytes, while the rejected sidecar proof would not govern serving. |
| **How** | Existing D0 chain → reference-v2 target → same-reader cold proof and serving → recovery coverage → retained eligibility. |

**TL;DR:** Preserve D0; replace copied `G_rb` with a reference-v2 target whose
qualified rows are exactly the rows rollback serving reads. No production
operation or failed-state cleanup is authorized.

## 1. Locked invariants (ratified amendment)

Implementation must preserve all of the following:

1. **Existing D0 remains authoritative.** D1 must load the complete ratified D0
   chain unchanged; this corrective neither recaptures nor reratifies it.
2. **`G_rb` proof profile = `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`.** Historical
   model status is exactly `UNKNOWN` / identifier `null`. No config inference.
3. **`G_canary` and every prospective generation = `KNOWN_MODEL_AND_VECTOR_V1`.**
   Writer-produced model provenance required.
4. **Three-part D0 authority:** candidate → independent validation → Ryan
   durable ratification. Candidate self-hash is never authority.
5. **Separate executions.** Candidate capture and independent validation are
   distinct executions with distinct evidence digests.
6. **D1 is authority consumer only.** D1 loads fixed durable artifacts; it does
   not create D0, ratify, or accept caller authority objects.
7. **No vector staging.** D1 rereads covered rows under lock and publishes only
   reference metadata/evidence. It must not add/upsert Chroma rows or publish
   vector sidecars.
8. **Query-context equality is G_rb-specific.**
   `live_query_embedding_context_sha256 == D0_ratified_query_embedding_context_sha256`
   is required for D1, first cutover, and `G_rb` rollback only — not for later
   known-model rollback generations.
9. **One physical authority.** The same target-aware reader over the exact
   original collection UUIDs and physical IDs is used by cold qualification,
   first-cutover rebind, and rollback serving. Proof and serving cannot diverge.
10. **Retained evidence is byte-exact immutable.** Fresh-process serving-path
    qualification and recovery coverage are mandatory before
    `RETAINED_ROLLBACK_BASELINE`; stored cold evidence is historical, not a
    substitute for current qualification.
11. **Prior Design A cutover semantics remain:** exact `G_rb` + exact `G_canary`,
    dedicated first-cutover CAS `None`, monotonic fence, `FENCED_NO_POINTER`,
    canary-open guard, rollback lineage split, durable reconciliation on
    source-advanced rollback, exact recovery only.
12. **Complete-data restore must preserve the original referenced rows and all
    non-reconstructible authority artifacts** and refuse restore paths that
    would copy, re-embed, or reconstruct the same `G_rb` identity.
13. **The failed convert-v1 target is terminal.** `2d01dfca…` is
    non-authoritative, quarantined, permanently ineligible for activation or
    reuse, and untouched absent a separate cleanup grant.
14. **No new lifecycle literal.** Cold qualification is a predicate;
    `G_RB_CONVERT_COLD_VALIDATED` and `abandoned_d1` are not introduced.

## 2. Frozen implementation inputs — reuse limits

The accepted runtime parent is
`e930ae4c2fb67eabbfa570f7caacda8d9ddac79d`. The rejected corrective
`d6fd5de64cfdcaf039d90f7ea9bb081f03a2240a` and failed production target
`2d01dfca08ac388e7ac74d145e789a8a35d8b97c4bf2ee6d971a95a8a74c4b3c`
are evidence inputs, not implementation bases to repair or reuse.

### Reusable contracts

| Area | Reusable contract | Required corrective |
|---|---|---|
| D0 authority | Existing candidate/validation/Ryan ratification and canonical float32/hash algorithms | Consume unchanged; add only supplementary reference/serving/recovery binding |
| LEGACY classification | Existing owner/source classifier and exact physical-row reader | Restrict new selector to exact D0 physical IDs and original collection UUIDs |
| Safety guards | Existing production-root refusal, owner lock, accepted-source and query-context checks | Apply to reference publication and serving-path qualification |
| Target lineage | Existing pointer/fence/CAS bytes and rollback operation split | Treat pointer ID as opaque target ID; dispatch by manifest variant |
| Serving repository | Existing request-frozen authority view and exact Python scoring | Add typed retained-reference reader; use it for proof and rollback serving |
| Generation manifests | Existing copied-generation manifest remains valid for `G_canary` and later | Add a narrow reference-v2 variant; do not weaken the existing schema |

### Prohibited inheritance

| Rejected behavior | Reason |
|---|---|
| `CONVERT_V1_FINGERPRINT` or failed deterministic ID | Materially different physical meaning; old ID is permanently ineligible |
| Chroma row add/upsert for `G_rb` | Cosine re-insertion changes D0 readback float32 bytes |
| `.f32le` or other sidecar vector authority | Serving does not consume it; creates split proof/serving authority |
| Re-embedding or normalization reconstruction | Cannot restore the D0-attested state |
| `G_RB_CONVERT_COLD_VALIDATED` | Cold qualification is a predicate, not a lifecycle state |
| `abandoned_d1` durable schema or automatic cleanup | Not authorized; failed target remains untouched |
| Shared encoder exception drift | Existing D0 non-finite refusal must remain `D0AttestationError` |

## 3. Stage dependency graph

```text
D0 (freeze existing ratified authority + regression check; no recapture)
  ↓
D1 (reference-v2 manifest + same-reader qualification; no row staging)
  ↓
D2 (typed target resolution in existing authority API)
  ↓
D3 (first-cutover gate + D0/query-context rebind)
  ↓
D4 (rollback after source advance — G_rb-specific D0/query checks)
  ↓
D5 (rehearsal through D0→reference-v2→cutover→serving rollback)
  ↓
D6 (formal model + TLC)
  ↓
D7 (Execute closure / VERIFY evidence — no VERIFY edit in planning)
```

The existing production D0 candidate → validation → Ryan ratification is an
immutable input to this graph. No recapture or reratification is required or
authorized. Production D1 remains outside this implementation graph until
separately granted.

## 4. Canonicalization contract (executable pin)

All D0/D1 roots and artifact digests use one contract unless architecture
explicitly names an exception.

### 4.1 Canonical JSON

Reuse `canonical_json.canonical_json_bytes` via
`file_generation_contract.canonical_bytes`:

- strict typed JSON values;
- valid Unicode scalar strings;
- no duplicate or unknown keys;
- UTF-8, `ensure_ascii=false`, `allow_nan=false`;
- object keys sorted lexicographically;
- comma/colon separators, no insignificant whitespace;
- non-finite numbers refused via `_reject_nonfinite`.

D0 context and pipeline payloads use the exact key orders named in architecture
§7.0.1a. D0 leaf and aggregate schemas use the key orders defined in §4.3–§4.5
below.

### 4.2 SHA-256 digests

- All digests are lowercase 64-hex SHA-256 unless architecture names an external
  digest field stored outside the hashed payload.
- Artifact digests omit the artifact's own digest field from the preimage
  (content-addressed naming carries the digest).
- `query_embedding_context_sha256` is computed over exact canonical UTF-8 context
  bytes and stored outside the hashed context object.

### 4.3 Float32 vector encoding

For each admitted vector:

1. Read persisted values via the same finite-float rules as `_as_float_tuple`.
2. Encode each component as IEEE-754 binary32 **little-endian** using
   `struct.pack("<f", value)`.
3. `vector_encoding_sha256 = SHA256(concatenated component bytes)`.

Non-finite components refuse capture/validation.

### 4.4 Row leaf schema and ordering

Leaf identity tuple (global ordering key):

```text
(collection_name, conversion_logical_id, physical_id)
```

Compare each string as UTF-8 bytes lexicographically. Missing/invalid Unicode
or duplicate tuple refuses.

`conversion_logical_id` = explicit metadata `logical_id` if non-empty, else exact
physical id. Never infer from `ledger_id`.

Each leaf record (hashed as one canonical JSON object) includes at minimum:

- `collection_name`, `conversion_logical_id`, `physical_id`;
- `document_hash`, `immutable_semantic_metadata_hash`;
- `vector_encoding_sha256`;
- provenance fields per architecture: exact canonical envelope + envelope hash,
  `assertion_id`, `provenance_commitment`, or explicit conservative absent/invalid
  encoding without synthesis.

Leaf list for a collection root is ordered by
`(conversion_logical_id, physical_id)` UTF-8 lexicographic order.

Collection root = canonical hash of ordered leaf list + collection UUID/config/
dimension bindings.

Aggregate accepted-legacy snapshot root = canonical hash of ordered collection
roots using global leaf ordering semantics.

### 4.5 D0 artifact schemas (plan pin)

Frozen constants in `cg2_legacy_vector_attestation.py`:

| Schema constant | Role |
|---|---|
| `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` | Proof profile for D0/G_rb historical vector state |
| `KNOWN_MODEL_AND_VECTOR_V1` | Reserved proof profile name for D1+ canary path (D2+) |
| `QUERY_EMBEDDING_CONTEXT_V1` | Contemporary query-space authority payload |
| `QUERY_EMBEDDING_PIPELINE_V1` | Immutable pipeline recipe fingerprint input |
| `CG2_D0_CANDIDATE_V1` | Candidate artifact wrapper |
| `CG2_D0_VALIDATION_RESULT_V1` | Independent validation result wrapper |
| `CG2_D0_RATIFICATION_V1` | Ryan durable ratification record |

Exact field lists mirror architecture §7.0.1–§7.0.2 and §7.0.1a recipe/context
objects. The accepted implementation and ratified artifacts already embody this
contract; reference-v2 must consume them without schema or root changes.

## 5. D0 — Frozen authority compatibility and regression checks

The D0 machinery and production authority chain already exist. The corrective
implementation must consume them unchanged. A later Execute grant authorizes
only compatibility tests and the smallest exception-type regression repair if
needed; it does not authorize schema/root changes, capture, validation, or
ratification.

**Execute does NOT authorize:** production D0 capture, production independent
validation, Ryan production ratification, D0 evidence edits, production `G_rb`,
fence/pointer publication, or D1 execution on the live owner.

### 5.1 Existing surfaces and corrective boundary

The existing public functions and schemas described below are frozen inputs.
If reference-v2 cannot consume them through a narrow read-only boundary, that is
a **plan/scope review STOP** — not license to rewrite D0.

| Path | Responsibility |
|---|---|
| `cg2_legacy_vector_attestation.py` | Existing D0 capture/validation/ratification validators, canonical roots, query context, governed layout, and read-only consumer boundary |
| `tests/test_cg2_legacy_vector_attestation.py` | Existing oracles; corrective adds only the non-finite exception regression if absent |
| `query.py` | Read-only governed query-context reference; no ranking behavior change in the corrective |
| `llm.py` | Governed embedding POST implementation reference (`/api/embeddings`, model+prompt) |
| `eval_provenance.py` | Reference for Ollama version/model digest/quant **resolution semantics** — D0 must fail closed; no eval-style degrade-to-empty |
| `file_generation_contract.py` | Reuse `canonical_bytes` / `canonical_hash` |
| `purge_locks.py` | Reuse existing `source_flock` — no new lock |
| `serving_authority.py` | Reuse `generation_root_for_cfg`, fence/pointer/retirement existence checks |
| `complete_data_restore.py` | Smallest matrix extension so complete-data backup/restore preserves D0 artifacts (see §5.8) |

No D0 runtime module change is expected except a narrowly proved exception-type
regression repair; any other D0 change is a scope stop.

### 5.2 Governed non-serving authority root

Pin layout under configured generation root:

```text
{generation_root}/legacy_vector_attestation/{owner_digest}/
  candidates/{candidate_artifact_sha256}.json
  validations/{validation_result_sha256}.json
  ratifications/{ratification_id}.json
```

Rules:

- content-addressed candidate and validation filenames;
- ratification record references candidate + validation digests explicitly;
- immutable publication: byte-identical rewrite allowed; divergent rewrite refuses;
- **non-serving evidence only** — this root is NOT a serving authority, serving
  database, pointer, owner-state machine, or second generation authority system;
- D1 resolves ratification only within this root.

Hermetic tests use temporary generation roots only.

### 5.3 D0 candidate capture (hermetic API)

**Pinned public contract** (module `cg2_legacy_vector_attestation.py` — names are
reviewed authority; changing any name or signature requires plan/scope review STOP,
not silent Execute drift):

```text
capture_d0_legacy_vector_candidate(cfg, *, owner_key, source_path, accepted_source_hash) -> CandidateReference
```

Under existing `source_flock` once:

1. Resolve canonical source path and owner digest.
2. Bind accepted source hash to processed log (reuse binding semantics from
   blocked checkpoint).
3. Verify exact `LEGACY` authority via `serving_authority.resolve_frozen_authority_vector`.
4. Refuse configured-live Chroma open without writer attestation (reuse blocked
   production-boundary pattern).
5. Existing tests read admitted LEGACY rows from temporary/hermetic Chroma.
6. Bind exact collection UUID/configuration/dimension per collection.
7. Build ordered leaves, collection roots, aggregate snapshot root.
8. Derive `QUERY_EMBEDDING_CONTEXT_V1` through governed adapter (§5.6).
9. End-of-capture recheck: authority still LEGACY, row counts/roots unchanged,
   query-context digest unchanged.
10. Publish candidate artifact with producer SHA, module identity, schema version,
    attestation timestamps labeled processing time only.

Any churn during capture refuses candidate emission.

### 5.4 Independent validation (separate execution)

**Pinned public contract** (same module; name/signature changes require plan/scope
review STOP):

```text
validate_d0_legacy_vector_candidate(cfg, *, owner_key, source_path, accepted_source_hash, candidate_sha256, validator_identity) -> ValidationReference
```

Independent validation is corroboration, not repair of a torn candidate. It uses
the **same existing owner/source locking and consistency protocol** as candidate
capture — no new lock mechanism.

Under existing `source_flock` **exactly once**:

1. Acquire the existing `source_flock` for the owner (single acquisition; no
   nested reentry).
2. Establish exact owner authority = `LEGACY` via
   `serving_authority.resolve_frozen_authority_vector`.
3. Establish accepted-source state and bind accepted source hash to the processed
   log (same binding semantics as capture).
4. Derive live `QUERY_EMBEDDING_CONTEXT_V1` and compute
   `query_embedding_context_sha256`.
5. Reread persisted covered rows/vectors/provenance from Chroma read-only;
   independently reproduce all candidate roots (leaf, collection, aggregate
   snapshot) and query-context digest from persisted state only.
6. Load candidate artifact by content address; refuse if reproduced roots or
   query-context digest do not match candidate claims — no candidate field is
   accepted merely because the candidate says it.
7. **End-of-validation recheck before releasing the lock:** re-verify owner
   authority still `LEGACY`, accepted source unchanged, exact row/vector/provenance
   roots unchanged, and `query_embedding_context_sha256` unchanged.
8. Any start/end drift or mismatch refuses validation publication.

Then publish separate validation artifact with its own validator/code identity and
immutable result SHA-256.

**Separate executions:** candidate capture and validation must not be emitted by
one self-attesting execution. Test oracle: monkeypatch/subprocess/spawn separation
so the candidate path cannot emit validation. Optional: assign independent
validation to a separate lane for stronger separation-of-duties.

Candidate and validation remain distinct evidence artifacts with distinct digests.

### 5.5 Ryan ratification record (contract only)

**Pinned public validators** (same module; name/signature changes require plan/scope
review STOP):

```text
validate_d0_ratification_record(record) -> RatificationView
load_ratified_d0_chain(generation_root, *, owner_digest, ratification_id) -> D0AuthorityChain
```

Ratification binds at minimum:

- candidate artifact SHA-256;
- independent validation-result SHA-256;
- owner digest / owner key;
- accepted snapshot/vector root;
- producer repository SHA;
- attestation capture identity/timestamp;
- D0-ratified `query_embedding_context_sha256`.

Deletion, invalidation, or digest mismatch fails closed. The corrective must not
create or change a production ratification record.

### 5.6 QUERY_EMBEDDING_CONTEXT_V1 — frozen implementation pin

Governed query adapter sources at architecture SHA:

| Field | Frozen repository pin |
|---|---|
| Embedding call path | `query.query_units` / `query.query_raw` → `llm.ollama_embed(text, model=cfg["models"]["embed_model"], host=cfg["models"]["ollama_host"])` |
| Request operation | Ollama `POST /api/embeddings` with JSON `{"model": ..., "prompt": <exact text>}` |
| Output selector | response JSON field `embedding` |
| Input transform | identity Unicode string at embedding boundary |
| Vector transform/normalization | identity float vector / none |
| Model identifier | exact configured `embed_model` sent on wire |
| Model artifact digest | **Pin:** `GET {ollama_host}/api/tags` → matching model entry (`name` or `model` == configured embed model) → field `digest`; normalize to `sha256:<64 lowercase hex>` per architecture; **fail closed if unresolved** — do not copy config; do not infer from dimension |
| Quantization | **Pin:** same `/api/tags` entry → `details.quantization_level` — fail closed if unresolved |
| Dimension | positive int from governed query-embedding response; must equal every admitted collection dimension |
| Runtime identifier | exact string `ollama` for this repository path |
| Runtime version | **Pin:** `GET {ollama_host}/api/version` → JSON field `version` — fail closed if unresolved |

**Implementation note:** `eval_provenance.model_digest_and_quant` and
`eval_provenance.ollama_version` document the intended HTTP sources but degrade
to empty strings on failure. D0 must **not** reuse that degrade behavior; implement
fail-closed resolution in `cg2_legacy_vector_attestation.py` (or a D0-only adapter
calling the same endpoints). If repository inspection during Execute cannot
establish a trustworthy exact resolution path without architecture change, **STOP**
for Luna/Ryan review — do not guess.

**Runtime drift:** a change to the ratified `embedding_runtime_version` changes
`QUERY_EMBEDDING_CONTEXT_V1` and therefore makes the existing `G_rb` D0 authority
chain ineligible until a new separately authorized D0 capture → validation → Ryan
ratification exists. Rehearsal evidence must record this operational risk.

Pipeline fingerprint = SHA-256 over canonical `QUERY_EMBEDDING_PIPELINE_V1` object
with architecture field order.

**Excluded explicitly:** hostname, URL authority, port, credentials, timeout,
retry policy, PID, deployment path.

**Scope guard:** this context is required for D0, D1 `G_rb`, first cutover, and
`G_rb` rollback only — not for arbitrary later known-model generations.

### 5.7 D1 read-only consumption boundary

**Pinned public exports** (same module; name/signature changes require plan/scope
review STOP):

```text
load_ratified_d0_chain(...) -> D0AuthorityChain
verify_d0_chain_for_grb_reference(chain, *, live_query_context_sha256) -> None
```

D1 must not import private D0 capture helpers except through this boundary. The
existing conversion-named export may remain as a deprecated compatibility alias
only if no reference-v2 evidence records that stale name as protocol identity.

### 5.8 Backup/restore preservation (smallest change)

Extend `complete_data_restore.py` StateSpec validation so complete-data restore:

- preserves under `{data_root}`: D0 candidate, validation, ratification, actual
  non-reconstructible `G_rb` Chroma rows, retained rollback evidence, manifests,
  applicable fence/pointer/guard artifacts, query-context binding records;
- refuses restore that would substitute re-embedded vectors as the same `G_rb`;
- keeps existing non-authoritative backup evidence non-authoritative.

Exact path globs follow §5.2 layout plus existing generation/manifest paths.
No D0 evidence retirement/GC in this corrective.

Default retention after first-canary window: **retain** until separately authorized.

### 5.9 D0 red tests (required before green)

- canonical JSON/key-order/refusal oracles;
- float32 encoding + non-finite refusal;
- leaf ordering independent of Chroma insertion order;
- capture churn refusal under mocked row mutation;
- end-of-capture authority recheck;
- independent validation refuses tampered candidate even with recomputed self-hash;
- ratification refuses digest mismatch / missing fields / invalidated record;
- query-context refuses missing model digest, quant, runtime version;
- separate-execution oracle (candidate path cannot emit validation);
- **validation lock oracle:** wrap `source_flock` and assert
  `validate_d0_legacy_vector_candidate` acquires it **exactly once** per call;
- **validation churn oracle:** mutate authority, accepted source, row/vector/provenance
  roots, or query-context digest between validation start and end-of-lock recheck;
  assert validation refuses publication;
- production-boundary refusal on configured-live paths without attestation;
- hermetic-only: no writes under configured live generation root in tests.

### 5.10 D0 verification

```bash
python -m pytest tests/test_cg2_legacy_vector_attestation.py -q
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

### 5.11 D0 STOP if

- canonicalization cannot be pinned without architecture change;
- independent validation cannot be separated without new authority system;
- query-context fields would require hardware/backend identity not in architecture;
- production capture would be required to pass hermetic tests;
- work expands beyond §5.1 surface table.

## 6. D1 — Retained-reference-v2 target from ratified D0 (hermetic)

**Depends on:** D0 public read/validate boundary stable.

**A later Execute grant may authorize:** amended `cg2_rollback_baseline.py`, a
typed target-aware serving reader, reference-manifest validation, recovery
coverage checks, and hermetic tests — never production D1 execution.

### 6.1 Expected surfaces

| Path | Responsibility |
|---|---|
| `cg2_rollback_baseline.py` | D1 authority consumer: load D0 chain, reread exact original rows, derive reference-v2 target ID, publish narrow manifest/evidence v2; no vector staging |
| `file_generation_contract.py` | Add `RETAINED_LEGACY_REFERENCE_V2` manifest variant and exact validator without weakening copied-generation v1 |
| `file_generation_store.py` / `serving_index_repository.py` | Typed target resolver and one exact-ID row reader used by cold qualification and rollback serving; protect referenced rows |
| `file_generation_validate.py` | Fresh-process target-aware qualification dispatcher and evidence result |
| `complete_data_restore.py` / Recovery Authority boundary named by its accepted plan | Bind reference-v2 eligibility to complete-data coverage; do not implement V4k here if it exceeds the accepted interface |
| `tests/test_cg2_rollback_baseline.py` (new/amended) | D1 oracles per §6.3 |
| `tests/test_file_generation_contract.py` | Manifest variant/version and rejection oracles |
| `tests/test_file_generation_store.py`, `tests/test_serving_index_repository.py`, `tests/test_file_generation_validate.py` | Same-reader serving/qualification, exact membership, and retention oracles |
| `tests/test_complete_data_restore.py` | Joint recovery coverage/restore refusal oracles within the pre-agreed boundary |

Do **not** modify `chroma_write_store.py`.

Do not add or retain:

- any Chroma `add`/`upsert` call on the `G_rb` path;
- any copied/vector-sidecar authority;
- caller snapshot or caller embedding-provenance authority;
- in-process-only qualification;
- `G_RB_CONVERT_COLD_VALIDATED` or `abandoned_d1` schemas; or
- any code path that can resolve the failed convert-v1 ID as eligible.

### 6.2 D1 algorithm (authority consumer)

Under existing `source_flock` once:

1. Refuse unauthorized live Chroma or generation-root mutation.
2. Load ratified D0 chain from governed root; verify ratification + digests.
3. Re-derive live `QUERY_EMBEDDING_CONTEXT_V1`; require exact equality with
   D0-ratified digest.
4. Revalidate LEGACY authority and accepted-source binding.
5. Independently reread exact D0-covered rows/vectors/provenance from Chroma;
   recompute all D0 roots; require exact match to ratified roots.
6. Derive deterministic target ID from
   `convmem/cg2-rollback-baseline-reference-v2`, owner/source identity, D0 roots,
   collection UUID/configuration, and ordered physical IDs. The failed v1 ID
   can never collide or be reused.
7. Publish only the `RETAINED_LEGACY_REFERENCE_V2` manifest under unchanged
   `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`; no Chroma or vector-sidecar writes.
8. In a new interpreter, reopen the actual Chroma store and governed generation
   root, reload the D0 chain, and invoke the same target-aware exact-ID reader
   used by serving.
9. Reject missing, additional, substituted, duplicate, wrong-owner, rewritten,
   wrong-collection, wrong-configuration, or wrong-ID rows; recompute all D0
   roots and exact float32 hashes from serving-reader output.
10. Prove no copied generation or sidecar participates and that the manifest's
    selector resolves exactly the D0 row set.
11. Verify complete-data recovery coverage of the original referenced rows,
    manifest/evidence, D0 chain, pointer/fence/guard state, and query context.
12. Publish immutable rollback-baseline evidence v2 binding manifest SHA,
    D0 chain, qualification result, serving-selector fingerprint, and recovery
    evidence; evidence idempotency is exact-byte-only.
13. Establish `RETAINED_ROLLBACK_BASELINE` only after steps 1–12 pass.

Any drift refuses. If the original accepted state changed, a separately
authorized new D0 chain would be required; this corrective does not silently
invalidate or replace the current ratified chain.

### 6.3 Versioning and schema contract

| Surface | Corrective decision |
|---|---|
| Rollback fingerprint | New exact string `convmem/cg2-rollback-baseline-reference-v2`; convert-v1 remains historical/failed only |
| Target ID | New deterministic ID derived from reference-v2 inputs; never reuse `2d01dfca…` |
| Proof profile | Keep `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` byte-for-byte and semantically unchanged |
| Manifest | New narrow `RETAINED_LEGACY_REFERENCE_V2` variant; copied-generation v1 remains unchanged for prospective generations |
| Rollback evidence | New `CG2_ROLLBACK_BASELINE_EVIDENCE_V2` binding D0, manifest, qualification, selector, and recovery evidence |
| Pointer | No wire-schema change; existing ID field is an opaque target ID and resolver dispatches by manifest variant |
| Property map | New `convmem/cg2-design-a-property-map-v3` at implementation closure |
| Lifecycle | Existing `RETAINED_ROLLBACK_BASELINE`; cold qualification and recovery are eligibility predicates, not states |
| Failure record | No `abandoned_d1` schema; failed v1 target remains untouched and permanently ineligible |

The reference manifest must use canonical JSON and contain only identity,
selector, hash, D0, and profile bindings. It must contain no embedding array,
sidecar path, generated physical row ID, or field that can be interpreted as a
replacement vector authority.

### 6.4 D1 required corrections mapped to tests

| Correction | Test oracle |
|---|---|
| One physical authority | spy/fake proves cold qualification and serving call the same exact-ID reader with identical target descriptor |
| Exact membership | each missing/additional/substituted/duplicate/wrong-owner/wrong-collection ID refuses independently |
| Exact readback | one-ULP vector drift, document mutation, metadata/provenance swap, or collection config drift refuses |
| No copy/sidecar | Chroma write spy and sidecar lookup spy remain unused; static inventory rejects such dependencies |
| Version separation | reference-v2 fingerprint/ID differs from convert-v1; `2d01dfca…` always refuses |
| D0 compatibility | frozen candidate/validation/ratification digests load unchanged and reproduce accepted root |
| Fresh process | child process reopens real stores; forged/stale qualification cannot establish retention |
| Serving equality | rollback query scores vectors returned by the exact reader; no ordinary generation `_get_rows` path for `G_rb` |
| Recovery eligibility | missing any jointly required backup/restore component refuses retained/first-cutover eligibility |
| Exception compatibility | non-finite D0 vector still raises `D0AttestationError`, never leaked `ValueError` |

### 6.5 D1 verification

```bash
python -m pytest tests/test_cg2_rollback_baseline.py \
  tests/test_file_generation_validate.py \
  tests/test_serving_index_repository.py \
  tests/test_file_generation_store.py \
  tests/test_file_generation_contract.py \
  tests/test_complete_data_restore.py -q
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

### 6.6 D1 STOP if

- existing D0 chain would need mutation or reratification;
- exact roots cannot be reproduced from persisted rows;
- manifest dispatch would weaken or reinterpret copied-generation v1;
- same-ledger distinct-provenance twins collapse;
- cold qualification and serving cannot share one reader;
- recovery coverage cannot bind the original physical rows;
- any implementation needs a Chroma/vector-sidecar copy for `G_rb`; or
- implementation would mutate/clean/reuse `2d01dfca…`.

## 7. D2 — Authority API separation

**Depends on:** D0 public read boundary stable + D1 reference-manifest/evidence
validator and target-aware reader stable. No production D0 operations required.

**Execute authorizes:** pointer API refactor, cutover guard module, hermetic tests.
**Execute does NOT authorize:** production pointer publication, live cutover, or
production D0 data.

### 7.1 Expected surfaces

| Path | Responsibility |
|---|---|
| `file_generation_pointer.py` | Separate current-active CAS from durable previous lineage; one private lock-held pointer-publication primitive shared by forward publish, first cutover, rollback, and exact recovery; add `rollback_active_pointer`; keep recovery exact-payload only; ordinary forward publication rejects first-pointer use and open-canary promotion |
| `cg2_cutover_guard.py` (new) | Low-level hash-bound first-canary-open artifact, path, immutable publication, and validation; imports no pointer/orchestration module (no authority cycle); no close writer in this Execute |
| `tests/test_file_generation_pointer.py` | CAS/lineage API split, ordinary forward behavior, rollback publication, stale CAS, recovery signature/identity, one-lock oracle |
| `tests/test_file_generation_validate.py` | Fresh qualification of baseline/canary/rollback target and persisted corruption refusal |
| `tests/test_source_freshness_promotion.py` | Stale-source forward refusal (reuse/extend) |

No change expected in `convmem.py`, `mcp_server.py`, production config, `watch.py`,
`doctor.py`, Shadow, or R2b.

### 7.2 Pointer API contracts

Public semantics after Design A:

```text
publish_active_pointer(
    target_manifest_reference,
    expected_active_generation_id=<non-None current active>, ...)

publish_first_cutover_active_pointer(
    canary_manifest_reference,
    rollback_target_reference,
    rollback_baseline_evidence_v2,
    expected_active_generation_id=None, ...)

rollback_active_pointer(
    retained_target_reference,
    expected_active_generation_id=<exact current active>, ...)

recover_active_pointer(owner_key, ...)
```

Each public authority-changing operation acquires the existing `source_flock` for
its owner **exactly once**. Public operations own preflight/orchestration and
locking; one **private lock-held pointer-publication primitive** performs the
actual pointer write for ordinary forward publication, first cutover, rollback,
and exact recovery. The private primitive assumes the correct owner lock is
already held and never acquires it. High-level first-cutover and rollback code
must call that private primitive directly while holding their one lock; they
must **not** call another public operation that reacquires `source_flock`.
`source_flock` itself is not changed to tolerate nested locking. There is no
parallel pointer format or authority file.

- **Ordinary forward publication** CASes against exact current active, performs
  mandatory current-source freshness, and writes durable `previous_generation_id`
  equal to that CAS-proven current active generation.
- **First cutover** CASes against pointer absence while writing durable
  `previous_generation_id=G_rb` and active=`G_canary`.
- **Rollback** CASes against exact current active, fresh-qualifies the retained
  target, does not require target source hash to equal live source, and writes
  durable previous equal to the former active generation.
- **Recovery** accepts no target reference or generation ID. It validates and
  republishes the exact visible payload bytes only.

### 7.3 Red tests first

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

### 7.4 Then implement

- Refactor `file_generation_pointer.py` around one private lock-held writer
  shared by forward publish, first cutover, rollback, and exact recovery.
- Add `cg2_cutover_guard.py`; make ordinary forward publication refuse an open
  guard without importing the high-level cutover orchestrator.

### 7.5 D2 verification

```bash
python -m pytest tests/test_file_generation_pointer.py \
  tests/test_file_generation_validate.py \
  tests/test_source_freshness_promotion.py -q
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

### 7.6 D2 STOP if

- any public API still uses one value for both CAS and durable lineage;
- recovery can select a target generation;
- ordinary forward can create a first pointer;
- first cutover/rollback acquires `source_flock` more than once;
- work expands beyond §7.1 surface table.

## 8. D3 — First-cutover structural gate, fence sequencing, and canary guard

**Depends on:** D0 + amended D1 + D2 complete.

**Execute authorizes:** first-cutover orchestrator, fence immutability, guard
publication, hermetic tests. **Execute does NOT authorize:** production first
cutover or live fence publication.

### 8.1 Expected surfaces

| Path | Responsibility |
|---|---|
| `cg2_first_cutover.py` (new) | Public dedicated first-cutover operation `publish_first_cutover_active_pointer`: one continuous `source_flock` interval for final LEGACY reread through fence/guard/first pointer; resume `FENCED_NO_POINTER` only under fresh grant; no CLI and no production defaults |
| `cg2_cutover_guard.py` | Complete low-level guard publication/validation (started in D2) |
| `serving_authority.py` | Fence publication immutable/idempotent-identical; reject replacement; preserve `FENCED_NO_POINTER` resolution; no fence deletion API |
| `tests/test_cg2_first_cutover.py` (new) | Exact structural gate, pre/post-fence timing, proof profiles, D0 chain, query context, crash/resume states |
| `tests/test_serving_authority.py` | Monotonic fence bytes; durable fence with no pointer resolves only `FENCED_NO_POINTER` |
| `tests/test_serving_index_repository.py` | Supporting authority-resolution fixtures as needed |

### 8.2 Non-lock preflight (before `source_flock`)

`publish_first_cutover_active_pointer` in `cg2_first_cutover.py` may perform
**purely non-authority-mutating** checks before acquiring `source_flock`: grant
binding validation, artifact existence reads, fresh-process qualification of
grant-bound `G_rb` and `G_canary`, and reconstruction of expected fence/guard
evidence for resume paths. These checks must not publish fence, guard, or pointer
bytes and must not reread authoritative LEGACY rows for cutover binding.

If any non-lock preflight check fails, return before acquiring `source_flock`.
The owner remains `LEGACY` with no new fence.

Non-lock preflight must still prove (among grant-bound inputs):

1. `G_rb != G_canary` (distinct target/generation IDs);
2. exact `G_rb` target ID and reference-v2 manifest SHA match immutable
   rollback-baseline evidence v2;
3. exact `G_canary` generation ID and manifest SHA match caller's grant-bound
   inputs;
4. **`G_rb` proof profile = `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`**;
5. **`G_canary` proof profile = `KNOWN_MODEL_AND_VECTOR_V1`**;
6. complete ratified D0 chain verification (candidate + validation + ratification
   digests, accepted snapshot root, ratified query-context digest);
7. exact rollback-baseline-evidence-v2 SHA, serving-selector fingerprint, and
   recovery-coverage binding for `G_rb`;
8. both manifests bind the same owner key/digest and canonical source path;
9. `G_rb` names the exact original collection UUID/configuration and physical
   IDs; `G_canary` has internally consistent copied-generation collection
   dimensions/configuration;
10. both pass fresh-process exact qualification, with `G_rb` using the same
    target-aware reader used by serving;
11. current pointer is absent, current owner is LEGACY, reconciliation is fresh,
    and current source hash equals `G_canary.source_hash`;
12. the first-canary guard does not already exist (initial cutover) or matches
    exact resume expectation (fresh-grant resume).

Missing, corrupt, wrong-owner, wrong-manifest-SHA, non-equivalent, or unqualified
baseline evidence, or D0 chain mismatch, therefore refuses before lock acquisition.

### 8.3 Single-lock cutover interval (authoritative)

The dedicated public `publish_first_cutover_active_pointer` operation acquires
`source_flock` **EXACTLY ONCE** per invocation. There must **NOT** be:

- a non-lock preflight acquisition followed by a second commit acquisition;
- lock release between the final authoritative LEGACY reread and fence publication;
- a second lock acquisition by the private pointer writer or any nested public
  pointer API.

The private lock-held pointer writer assumes the lock is already held and **must
not** call `source_flock` or any public pointer operation that would reacquire it.

**Inside the one lock-held interval, in this order:**

1. revalidate exact `LEGACY` authority;
2. reload/revalidate the ratified D0 chain as required;
3. derive and compare exact `query_embedding_context_sha256`;
4. **first lock-held cutover action:** independently reread the complete
   D0-covered LEGACY rows/vectors/provenance (not a stored D1 snapshot);
5. recompute and compare the exact D0 roots; any drift discovered here refuses
   **before** fence publication;
6. recheck all grant-bound `G_rb`/`G_canary` identities and remaining
   preconditions (pointer still absent on initial cutover; resume preconditions
   per §8.4);
7. only if every check still passes, publish the monotonic fence (initial cutover)
   or revalidate existing fence bytes unchanged (fresh-grant resume);
8. publish/open the first-canary guard as architecturally ordered (or validate
   byte-identical guard on resume);
9. publish the dedicated first pointer via the **private lock-held writer** with:
   - `expected_active_generation_id = None`;
   - durable `previous_generation_id = G_rb`;
   - active/target generation = exact grant-bound `G_canary`;
10. release the one lock only after the authority-changing operation reaches its
    specified durable outcome (pointer published, or fail-closed refusal before
    any fence bytes on initial cutover).

No catch block removes or rewrites the fence. A crash or failure after step 7
(fence published) and before successful step 9 leaves `FENCED_NO_POINTER`; a fresh
request can never resolve LEGACY. The guard is non-serving evidence and may exist
in that fail-closed state.

Successful first pointer fields:

- `expected_active_generation_id = None` (CAS against pointer absence);
- durable `previous_generation_id = G_rb`;
- active generation = exact grant-bound `G_canary`.

While the open guard is present:

- ordinary forward `publish_active_pointer` refuses;
- another first-cutover publish refuses;
- `rollback_active_pointer` remains available under its contract;
- `recover_active_pointer` remains available for exact same-pointer recovery;
- no API in this Execute closes, deletes, or mutates the guard.

### 8.4 Fresh-grant completion from `FENCED_NO_POINTER`

The same public `publish_first_cutover_active_pointer` operation owns the only
normal completion path for both resumable crash states:

- fence present / guard absent / pointer absent;
- fence present / exact guard present / pointer absent.

Neither state may reuse or continue under the pre-crash grant. Resume requires
a fresh Ryan one-shot grant bound to the exact `G_rb` and `G_canary`.

Before acquiring `source_flock`, the operation may requalify both exact grant-bound
generations and reconstruct expected immutable fence/guard evidence (non-lock
preflight per §8.2).

**Resume still uses exactly one `source_flock` acquisition.** Inside that single
lock-held interval (§8.3 steps adapted for resume):

1. revalidate existing fence as immutable and grant-bound;
2. reload/revalidate D0 chain and query context;
3. reread D0-covered LEGACY rows and recompute roots under the lock;
4. validate guard absent or byte-identical; publish missing exact guard if needed;
5. complete first pointer via private lock-held writer (no lock reacquisition).

A missing fence is not a resume state. Conflicting, malformed, or corrupt fence
or guard fails closed and requires operator repair.

### 8.5 Red tests first

- Parameterized non-lock preflight refusal matrix: missing baseline, corrupt
  evidence, wrong owner, wrong source, wrong manifest SHA, failed qualification,
  non-equivalent set, D0 chain mismatch, query-context mismatch, and
  `G_rb == G_canary` — all before `source_flock` acquisition; no fence, no pointer.
- **Single-lock acquisition oracle:** wrap `source_flock` with reentry failure;
  assert `publish_first_cutover_active_pointer` acquires it **exactly once** per
  successful or refused cutover attempt; assert a two-acquisition implementation
  fails the test.
- **Lock-held reread oracle:** assert final D0-covered LEGACY reread occurs while
  `source_flock` is held and before fence publication on initial cutover.
- **Fence-before-release oracle:** assert fence bytes exist before lock release on
  success; assert pointer publication uses private writer without `source_flock`
  reacquisition.
- **Drift-before-fence oracle:** inject row/root/query-context drift during final
  lock-held reread; assert refusal before any fence bytes.
- Inject failure/crash after durable fence and before pointer; assert
  `FENCED_NO_POINTER`, monotonic fence bytes, no pointer, no LEGACY recovery.
- `fence → crash → fresh-grant resume` coverage (one lock on resume).
- `fence → guard → crash → fresh-grant resume` coverage (one lock on resume).
- Wrong-guard refusal: conflicting/corrupt/wrong-owner/wrong-generation guard
  bytes fail closed with no pointer publication.
- Assert successful first pointer has active=`G_canary`, CAS `None`,
  previous=`G_rb`.
- Assert second forward promotion and second first-cutover operation refuse
  while guard is open; rollback and same-pointer recovery remain callable.

### 8.6 D3 verification

```bash
python -m pytest tests/test_cg2_first_cutover.py \
  tests/test_serving_authority.py \
  tests/test_serving_index_repository.py -q
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

### 8.7 D3 STOP if

- `publish_first_cutover_active_pointer` acquires `source_flock` more than once;
- final D0-covered LEGACY reread occurs outside the single lock interval;
- lock is released between final reread and fence publication;
- private pointer writer reacquires `source_flock`;
- any structural check can occur only after the fence without prior lock-held reread;
- an exception path clears the fence;
- a fenced/no-pointer owner can resolve LEGACY;
- resume can reuse the pre-crash grant or overwrite conflicting fence/guard bytes;
- a second promotion bypasses the open guard;
- first cutover can skip D0 reread or query-context check;
- work expands beyond §8.1 surface table.

## 9. D4 — Rollback after source advance and durable reconciliation

**Depends on:** D2 complete; D3 supplies fence and guard fixtures.

**Execute authorizes:** rollback pointer API completion, reconciliation helper,
hermetic tests. **Execute does NOT authorize:** production rollback on live owner.

### 9.1 Expected surfaces

| Path | Responsibility |
|---|---|
| `file_generation_pointer.py` | Complete `rollback_active_pointer` generation-switch rollback under one owner lock |
| `source_reconciler.py` | Add one atomic helper that durably records/coalesces a rollback-created desired-source obligation **before** stale-source rollback pointer publication; reuse existing state file, queue budget, and coalescing semantics |
| `tests/test_file_generation_pointer.py` | Rollback with unchanged/advanced/missing source, stale CAS, corrupt target |
| `tests/test_source_reconciler.py` | Rollback-created reconciliation obligation persists, coalesces to latest desired source, survives restart |
| `tests/test_source_freshness_promotion.py` | Stale-source forward publication still refuses after source advance |
| `tests/test_cg2_first_cutover.py` | Fence/guard fixtures for rollback assertions |

### 9.2 Rollback algorithm

Rollback runs under the existing owner lock in this order:

1. Require monotonic fence, valid active pointer, exact current-active CAS, and
   exact retained target named by durable lineage/retained evidence.
2. Fresh-process qualify the target manifest and rows.
3. **For `G_rb` rollback target only** (reference-v2 manifest and proof profile
   `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`): additionally require complete D0
   chain verification, exact rollback-baseline-evidence-v2 and recovery binding,
   exact collection UUID/configuration and membership, target-aware serving-
   reader equality, and live query-embedding context equality with the D0-
   ratified digest. **Do not impose D0 or query-context requirements on later
   known-model rollback generations.**
4. Observe current source. Equality is not a rollback precondition.
5. If source is missing or differs from target manifest, durably mark the
   existing source-reconciliation state dirty and coalesce/enqueue the latest
   desired source observation **before** pointer publication. Failure to make
   that obligation durable refuses rollback while the current pointer remains.
6. Publish target active with durable previous equal to the former active.
7. Re-read the fence and open-canary guard; neither is removed or cleared.

Source advance does **not** prohibit rollback. The obligation-before-pointer
order permits harmless extra reconciliation if pointer publication later refuses,
but never permits a successful stale-source rollback without durable desired-state
debt. Rollback stays GENERATIONAL and never invokes a LEGACY path.

Recovery remains same-pointer only and cannot substitute for rollback.

### 9.3 Red tests first

- Rollback with unchanged source, advanced source, missing source, stale
  current-active CAS, corrupt target, reconciliation persistence failure.
- Prove stale-source forward publication still refuses.
- Prove source-advanced rollback succeeds only after durable dirty/pending state
  exists and obligation survives process restart.
- Prove newer desired source remains coalesced, fence byte-identical, guard
  remains open, owner remains GENERATIONAL, no LEGACY row selected.
- Prove recovery still cannot switch generation (recovery-separation negative
  oracle).
- Prove `G_rb` rollback refuses without D0 chain / query-context match; prove
  known-model rollback target does **not** require D0 chain.

### 9.4 D4 verification

```bash
python -m pytest tests/test_file_generation_pointer.py \
  tests/test_source_freshness_promotion.py \
  tests/test_source_reconciler.py \
  tests/test_cg2_first_cutover.py -q
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

### 9.5 D4 STOP if

- rollback requires retained source equality with live source;
- successful rollback can precede durable reconciliation debt;
- rollback removes the fence;
- recovery shares the rollback target-selection path;
- D0/query-context checks apply to non-`G_rb` rollback targets;
- work expands beyond §9.1 surface table.

## 10. D5 — Request freeze, retention, and isolated Design A rehearsal

**Depends on:** D0–D4 public contracts stable.

**Execute authorizes:** rehearsal extension, property map update, mixed-mode proof
inventory update, request-freeze test. **Execute does NOT authorize:** live paths,
production roots, GC, or canary closure.

### 10.1 Expected surfaces

| Path | Responsibility |
|---|---|
| `cg2_rehearsal.py` | Isolated Design A drill through D0→ratification fixture→D1→cutover→rollback; evidence bundle collection; architecture identity = ratified `3d8b151…` |
| `cg2_property_map.py` | Design A properties/tests; replace false `FrozenGenerationStable` mapping with dedicated mid-request test |
| `mixed_mode_proof.py` | Include exact retained rollback baselines in retention inventory; physical deletion disabled |
| `tests/test_cg2_rehearsal.py` | End-to-end isolated drill; no live path |
| `tests/test_serving_index_repository.py` | `test_frozen_generation_stays_stable_when_pointer_changes_mid_request` |
| `tests/test_mixed_mode_proof.py` | `G_rb` protected across staging/cutover/rollback/reopen |

Change `ServingIndexRepository` runtime **only** if the dedicated freeze test
exposes an actual violation; that would exceed §10.1 — STOP for Luna/Ryan first.

### 10.2 Hermetic rehearsal contract

All steps use **temporary roots and temporary Chroma only**. No live/production
path. No GC. No canary closure. No production D0 capture or Ryan production
ratification.

Required sequence:

```text
D0 candidate fixture (hermetic Chroma)
→ separate independent D0 validation execution
→ synthetic hermetic Ryan-ratification fixture
→ D1 G_rb (LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1)
→ G_canary qualification (KNOWN_MODEL_AND_VECTOR_V1)
→ first cutover (including fence→crash→fresh-grant resume and
   fence→guard→crash→fresh-grant resume controls)
→ request frozen against one authority vector (FrozenGenerationStable)
→ source advance
→ G_rb rollback (with D0 chain + query-context checks)
→ reconciliation persisted
→ process restart
→ recover exact rolled-back pointer (same-pointer recovery — not generation switch)
→ authority re-open verification
```

Explicit assertions required in rehearsal evidence:

- no live/production path contact;
- `FrozenGenerationStable` / request freeze;
- exact first pointer fields (CAS `None`, previous=`G_rb`, active=`G_canary`);
- fence state monotonic/immutable;
- first-canary guard open and blocking second promotion;
- retained `G_rb` protected in inventory;
- `physical_deletion_disabled=true`;
- no GC eligibility for baseline;
- durable reconciliation obligation after source-advanced rollback;
- source-advanced rollback succeeded only with reconciliation debt present;
- same-pointer recovery distinct from generation-switch rollback;
- complete D0 authority chain digests recorded;
- `G_rb` query-context digest recorded and matched at rollback;
- reference-v2 target ID, manifest SHA, exact collection UUID/configuration,
  ordered physical-ID root, serving-selector fingerprint, and recovery evidence;
- cold qualification and rollback scoring use the same target-aware reader;
- no Chroma write or sidecar vector authority occurs on the `G_rb` path;
- failed convert-v1 ID `2d01dfca…` remains permanently ineligible;
- restart durability for reconciliation state and fence/guard bytes;
- production configured paths absent from rehearsal roots.

### 10.3 Evidence bundle fields

Rehearsal JSON must include at minimum:

- architecture SHA `3d8b151…` and execution-plan SHA;
- implementation SHA at rehearsal tip;
- D0 candidate, validation, and synthetic ratification digests;
- ratified and live query-context digests;
- exact `G_rb` target ID and `G_canary` generation ID plus manifest SHAs;
- rollback-baseline-evidence-v2 SHA and serving-selector fingerprint;
- original collection UUID/configuration and ordered physical-ID root;
- recovery-coverage evidence identity;
- pointer before/after rollback;
- fence and guard content hashes;
- reconciliation state hash before/after restart;
- retention inventory snapshot;
- fresh-grant identities for both resume cases;
- one-acquisition owner-lock oracle results for first cutover and rollback;
- explicit `no_production_operations=true`.

### 10.4 Red tests first

- Add `tests/test_serving_index_repository.py::test_frozen_generation_stays_stable_when_pointer_changes_mid_request`.
- Extend mixed-mode tests: `G_rb` remains protected across `G_canary` staging,
  first cutover, rollback, reopen; physical deletion disabled.
- Extend `tests/test_cg2_rehearsal.py` for full sequence above under temporary
  roots only.

### 10.5 D5 verification

```bash
python -m pytest tests/test_serving_index_repository.py \
  tests/test_mixed_mode_proof.py \
  tests/test_cg2_rehearsal.py -q
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

### 10.6 D5 STOP if

- rehearsal touches configured production roots;
- a retained baseline is classified abandoned/GC-eligible;
- frozen-generation test needs a new authority mechanism;
- rehearsal requires production D0 ratification;
- work expands beyond §10.1 surface table.

## 11. D6 — Formal model restore and extension

**Depends on:** D0–D4 public contracts stable. Model work begins only after those
contracts stabilize.

**Execute authorizes:** formal file restoration and extension, TLC runs, README
evidence update. **Execute does NOT authorize:** treating historical TLC runs as
Design A proof.

### 11.1 Formal surfaces (explicit list)

| Path | Expected change |
|---|---|
| `docs/plans/formal/cg2/CG2Authority.tla` | Extend the current model with typed rollback targets, reference-v2 membership/reader binding, failed-v1 quarantine, recovery eligibility, first-cutover, rollback, query-context, and refusal transitions |
| `docs/plans/formal/cg2/CG2Cutover.cfg` | Restore and rerun cutover/read-authority properties against changed shared model |
| `docs/plans/formal/cg2/CG2StaleReconcile.cfg` | Restore and rerun stale-source reconciliation and recovery properties |
| `docs/plans/formal/cg2/CG2Rename.cfg` | Restore and rerun rename/pinning properties |
| `docs/plans/formal/cg2/CG2DesignA.cfg` | Focused exhaustive instance for reference-v2 authority, D0 chain, first cutover, serving rollback, recovery separation, failed-v1 exclusion, canary guard, and query context |
| `docs/plans/formal/cg2/README.md` | Preserve 2026-08-14 evidence as historical old-revision only; map new properties/configs; record separate Design A run |

Historical TLC PASS evidence remains tied to its old revision and cannot be
claimed for the corrective until every configuration is rerun at one exact tip.

### 11.2 Required new transitions/state

- existing D0 candidate/validation/Ryan ratification as immutable authority
  inputs;
- target kind = copied generation or retained legacy reference;
- deterministic reference-v2 target creation without physical row creation;
- exact reference membership and target-aware serving-reader qualification;
- retention establishment only after cold qualification and recovery coverage;
- permanent failed-v1 quarantine/ineligibility;
- pre-fence structural refusal preserves LEGACY;
- durable fence without pointer (`FENCED_NO_POINTER`);
- fresh-grant resume from fence/no-guard/no-pointer;
- fresh-grant resume from fence/exact-guard/no-pointer;
- wrong/conflicting guard refusal with no pointer and no LEGACY restoration;
- first pointer with CAS `NoGen`, previous=`G_rb`, active=`G_canary`;
- first cutover rebinds current LEGACY root (live reread);
- ordinary forward promotion with CAS separate from lineage;
- source advance followed by exact retained-reference rollback through serving;
- **`G_rb` rollback requires exact query context** (not all retained gens);
- durable reconciliation-required before/with stale-source rollback;
- same-pointer recovery with no generation selection;
- first-canary-open refusal of second forward promotion;
- GC exclusion for `RETAINED_ROLLBACK_BASELINE` and every referenced physical
  row;
- one acquisition/release interval per authority-changing operation.

### 11.3 Required named properties

**New (reference-v2 corrective):**

| Property | Intent |
|---|---|
| `UnknownModelOnlyForRatifiedLegacyBaseline` | Only `G_rb` uses unknown-model profile |
| `ProspectiveGenerationRequiresKnownWriterModel` | Canary/later gens require known profile |
| `D0CandidateNotAuthority` | Candidate self-hash alone proves nothing |
| `D0ValidationRequired` | Validation digest required |
| `D0RatificationRequired` | Ryan ratification required for authority |
| `FirstCutoverRebindsCurrentLegacyRoot` | Live LEGACY reread before fence |
| `GRollbackRequiresExactQueryContext` | **G_rb / LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1 only** |
| `GRbAuthoritySinglePhysicalState` | Qualification, evidence, serving, and rollback resolve the same original rows |
| `GRbReferenceMembershipExact` | Collection UUID/config and physical-ID set equal D0 exactly |
| `GRbServingReadsReferencedRows` | Rollback scoring consumes target-aware reader output for those rows |
| `GRbNoCopiedOrSidecarAuthority` | No copied generation, sidecar, or reconstruction can qualify as `G_rb` |
| `GRbColdQualificationBeforeRetention` | Retention implies fresh-process serving-path qualification |
| `GRbRecoveryCoverageBeforeFirstCutover` | First cutover implies complete recovery coverage of all bound state |
| `GRbFailedV1NeverEligible` | `2d01dfca…` is never target, previous, active, or reusable |
| `GRbReferenceFingerprintVersioned` | Only reference-v2 meaning derives the corrected target ID |

**Prior Design A properties (carry forward):**

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

**Mandatory negative-control model mutations:** selector resolves one wrong ID;
serving consumes a copied target; D0 root changes; query context changes;
recovery coverage is false; reference target reuses the failed v1 ID. Each must
produce an invariant violation or terminal refusal in the focused configuration.

**Prior architecture properties (from restored model — must remain checked):**

- fence monotonicity; `FENCED_NO_POINTER`; first-cutover CAS;
- rollback/recovery distinction; stale-source reconciliation;
- canary-open guard; retention/no-GC; `FrozenGenerationStable` where applicable.

### 11.4 TLC tool preflight (fail-closed input contract)

`TLA_JAR` must be supplied as an **absolute, readable path** to the exact approved
`tla2tools.jar` for the Execute run. Do not guess a path, symlink an unapproved
copy, or silently download a different tool.

Before **any** TLC configuration runs, mechanically require:

```bash
set -euo pipefail

: "${TLA_JAR:?TLA_JAR must be set to absolute readable path to approved tla2tools.jar}"
test -r "$TLA_JAR" || { echo "D6 STOP: TLA_JAR not readable: $TLA_JAR" >&2; exit 1; }

TLA_JAR_SHA256="$(sha256sum "$TLA_JAR" | awk '{print $1}')"
TLC_VERSION="$(java -cp "$TLA_JAR" tlc2.TLC -version 2>&1 | tr -d '\r')"
JAVA_VERSION="$(java -version 2>&1 | head -n1 | tr -d '\r')"

# Execute evidence input must name the approved JAR SHA-256 for this run.
# Mismatch is D6 STOP — do not proceed with a different JAR.
: "${TLA_JAR_APPROVED_SHA256:?approved JAR digest required in Execute evidence input}"
if [[ "$TLA_JAR_SHA256" != "$TLA_JAR_APPROVED_SHA256" ]]; then
  echo "D6 STOP: TLA_JAR SHA-256 mismatch" >&2
  exit 1
fi
```

Record in evidence: `TLA_JAR` path, `TLA_JAR_SHA256`, `TLC_VERSION`, `JAVA_VERSION`,
and the approved digest that matched.

### 11.5 TLC execution (all four configurations — fail-fast)

**Pinned per-configuration timeout:** `1800` seconds (30 minutes). Any timeout is
D6 STOP — not PASS.

**Pinned module:** `docs/plans/formal/cg2/CG2Authority.tla`

**Required configurations (no skips):**

| Config file | Must run |
|---|---|
| `docs/plans/formal/cg2/CG2Cutover.cfg` | yes |
| `docs/plans/formal/cg2/CG2StaleReconcile.cfg` | yes |
| `docs/plans/formal/cg2/CG2Rename.cfg` | yes |
| `docs/plans/formal/cg2/CG2DesignA.cfg` | yes |

Execute all four in order; **abort on first failure** — later configs must not
hide an earlier failure.

```bash
set -euo pipefail

TLA_TIMEOUT_SECONDS=1800
TLA_MODULE="docs/plans/formal/cg2/CG2Authority.tla"
TLC_JAVA_OPTS=(-Xmx2g -XX:+UseParallelGC)

# Run §11.4 preflight first (sets TLA_JAR_SHA256, TLC_VERSION, JAVA_VERSION)

for config in CG2Cutover CG2StaleReconcile CG2Rename CG2DesignA; do
  cfg_path="docs/plans/formal/cg2/${config}.cfg"
  test -r "$cfg_path" || { echo "D6 STOP: missing config $cfg_path" >&2; exit 1; }

  log_path="/tmp/tlc-${config}-$(git rev-parse HEAD).log"
  cmd=(
    timeout "${TLA_TIMEOUT_SECONDS}"
    java "${TLC_JAVA_OPTS[@]}"
    -cp "$TLA_JAR" tlc2.TLC
    -workers 2 -coverage 1
    -config "$cfg_path"
    "$TLA_MODULE"
  )

  start_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  set +e
  "${cmd[@]}" >"$log_path" 2>&1
  exit_status=$?
  set -e
  end_ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [[ $exit_status -eq 124 ]]; then
    echo "D6 STOP: TLC timeout for ${config} after ${TLA_TIMEOUT_SECONDS}s" >&2
    exit 1
  fi
  if [[ $exit_status -ne 0 ]]; then
    echo "D6 STOP: TLC non-zero exit for ${config}: ${exit_status}" >&2
    exit 1
  fi
  if [[ ! -s "$log_path" ]]; then
    echo "D6 STOP: TLC produced no output for ${config}" >&2
    exit 1
  fi

  # Record per-config evidence (see §11.6) before proceeding to next config.
done
```

**Success criteria per configuration:**

- exit status `0` within pinned timeout;
- complete TLC log captured (generated/distinct state counts, depth, coverage);
- empty error queue, zero counterexamples in log;
- nonzero action coverage for every required new transition;
- checksum/version preflight matched approved Execute input.

Any timeout, non-zero status, missing config, skipped config, incomplete output,
or checksum/version mismatch is **D6 STOP**.

Historical TLC results at `e680ce8` / 2026-08-14 remain old-revision evidence only.

### 11.6 README evidence (per configuration — required fields)

Update `docs/plans/formal/cg2/README.md` with a **separate Design A run section**
(one subsection per configuration). Historical 2026-08-14 counts remain
historical-only and must not be rewritten as Design A proof.

For **each** of the four configurations, record:

- exact implementation/model git SHA at TLC run time;
- exact config path;
- exact command line (including `timeout`, Java opts, `-config`, module path);
- `TLA_JAR` path used;
- TLA JAR SHA-256 (`TLA_JAR_SHA256`);
- TLC version string (`TLC_VERSION`);
- Java version string (`JAVA_VERSION`);
- start timestamp and end timestamp (or elapsed seconds);
- exit status;
- PASS or failure result;
- generated states, distinct states, depth, and action-coverage summary from log.

### 11.7 D6 verification

```bash
# After exporting TLA_JAR and TLA_JAR_APPROVED_SHA256 from Execute evidence input:
bash -lc 'source docs/plans/formal/cg2/run-design-a-tlc.sh'  # optional helper script at Execute time only
# Or run §11.4 preflight + §11.5 loop inline at the reviewed implementation tip.

git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

If Execute adds `run-design-a-tlc.sh`, it must implement §11.4–§11.5 exactly;
adding that script is within §11.1 formal surfaces only when D6 Execute begins.

### 11.8 D6 STOP if

- TLC finds a counterexample;
- any required action has zero coverage;
- restored model cannot be tied to `e680ce8`;
- a property needs an architecture decision not already locked at `3d8b151…`;
- `GRollbackRequiresExactQueryContext` is scoped beyond `G_rb`;
- TLA JAR unreadable, digest mismatch, or unapproved tool version;
- any TLC configuration times out, exits non-zero, is skipped, or produces incomplete output;
- work expands beyond §11.1 surface table.

## 12. D7 — Execute closure, evidence, and Ryan stop

**Depends on:** D0–D6 pass at **one implementation tip**.

**Execute authorizes:** evidence collectors, property map, VERIFY row updates
(within Execute evidence phase). **Execute does NOT authorize:** production
operations listed in §12.4.

### 12.1 Execute-time tasks

After D0–D6 pass at one tip:

1. Version `cg2_property_map.py` to
   `convmem/cg2-design-a-property-map-v3` and map every reference-v2 property to
   exact pytest/TLC evidence, including `GRbAuthoritySinglePhysicalState`,
   `GRbReferenceMembershipExact`, `GRbServingReadsReferencedRows`,
   `GRbNoCopiedOrSidecarAuthority`, `GRbColdQualificationBeforeRetention`,
   `GRbRecoveryCoverageBeforeFirstCutover`, `GRbFailedV1NeverEligible`, and
   `GRbReferenceFingerprintVersioned`. Preserve all still-valid v2 mappings.
2. Update `cg2_rehearsal.collect_execute_evidence()` with canonical architecture
   SHA `3d8b151…`, execution-plan SHA, implementation SHA, model SHA, focused/full
   test results, TLC evidence identities, D0 chain fixture digests,
   reference-v2 manifest/evidence schema identities, same-reader proof,
   failed-v1 exclusion, recovery coverage, and explicit no-production flags.
3. Fill the PENDING reference-v2 rows in
   `docs/plans/VERIFY-cg2-production-activation.md` **only after implementation
   evidence exists**; this planning commit defines those rows but does not mark
   them PASS.
4. Request independent review of the exact implementation/model tip.
5. Stop for Ryan. Do not build production generations or prepare V8c.

### 12.2 Required final mechanical bundle

Before Ryan Execute-close stop, all of the following must pass at the **same**
implementation tip:

```bash
# Focused Design A suites (D0–D6)
python -m pytest tests/test_cg2_legacy_vector_attestation.py -q
python -m pytest tests/test_cg2_rollback_baseline.py \
  tests/test_file_generation_store.py \
  tests/test_file_generation_contract.py -q
python -m pytest tests/test_file_generation_pointer.py \
  tests/test_file_generation_validate.py \
  tests/test_source_freshness_promotion.py -q
python -m pytest tests/test_cg2_first_cutover.py \
  tests/test_serving_authority.py \
  tests/test_serving_index_repository.py -q
python -m pytest tests/test_source_reconciler.py -q
python -m pytest tests/test_mixed_mode_proof.py \
  tests/test_cg2_rehearsal.py -q

# Complete repository suite
python -m pytest -q

# Pylint regression gate (any runtime Python change in D0–D6)
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38

git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD

# All four TLC configurations — §11.4 preflight + §11.5 fail-fast loop
# (TLA_JAR absolute path + TLA_JAR_APPROVED_SHA256 from Execute evidence input;
#  pinned timeout 1800s per config; abort on first failure)

# Hermetic rehearsal (real public APIs, temporary roots only)
python -m pytest tests/test_cg2_rehearsal.py -q
```

Also required in bundle:

- architecture-invariant → implementation → exact test-node map;
- property-to-test mapping completeness check;
- architecture SHA `3d8b151…` and plan SHA consistency check;
- hermetic rehearsal JSON artifact;
- independent-review PASS naming the exact same tip SHA.

### 12.3 Same-tip rule

Independent final review must inspect the **exact** implementation/evidence tip
that Ryan would later consider complete. Any implementation correction after
review invalidates that review and requires re-review of the new exact tip.
Review of a different SHA, deferral, or partial bundle is not sign-off.

### 12.4 Failure discipline — explicit closure refusal

Execute closure must **refuse** if any of:

- skipped required tests;
- unexplained timeout (full suite or TLC);
- partial TLC execution (any of four configs skipped);
- Pylint regression gate failure;
- dirty expected worktree or unplanned surface changes;
- scope expansion beyond §14 surface matrix;
- production-path contact in tests or rehearsal;
- changed architecture semantics without Ryan amendment;
- stale or missing evidence artifacts;
- review against a different SHA than implementation tip.

### 12.5 Production-negative confirmations

Execute closure must prove **no**:

- production D0 capture;
- production D0 validation;
- Ryan production ratification;
- production `G_rb`;
- production `G_canary`;
- production fence;
- production pointer;
- owner activation;
- V8c grant/PASS;
- canary closure;
- GC;
- Shadow;
- R2b.

Production `G_rb` and `G_canary` identities are necessarily absent from the
Execute-close bundle; their build is a later separately granted phase.

### 12.6 VERIFY reconciliation (Execute-time only)

During Execute evidence update, reconcile stale VERIFY wording:

- **Current stale wording:** generic "embedding provenance" for both generations.
- **Required distinction after evidence:**
  - `G_rb`: historical-vector-state provenance under
    `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` (D0 ratified chain);
  - `G_canary`: known-model-and-vector provenance under
    `KNOWN_MODEL_AND_VECTOR_V1`.

Do **not** edit VERIFY during planning.

**V6c** remains **PENDING** until real `rollback_active_pointer` drill passes at
reviewed implementation tip. Mocked pointer rewrite does not satisfy V6c.

**V8c** remains **PENDING** until Ryan accepts complete packet and issues exact
one-shot activation grant.

## 13. Dependency boundaries

```text
existing CG-1 contract/store + ratified D0 authority
        │
        ├── D1 reference-v2 manifest/evidence
        │       ├── target-aware serving/qualification reader
        │       └── referenced-row retention + recovery coverage
        │
        └── D2 separated pointer mechanics
                 │
                 ├── D3 first-cutover orchestration + open guard
                 └── D4 rollback + existing reconciliation state
                          │
                          └── D5 integrated rehearsal / request freeze

D0–D4 stable contracts ──► D6 formal refinement
D5 + D6 exact tip ───────► D7 independent review / Ryan HITL
```

Import direction is one-way:

- `cg2_legacy_vector_attestation.py` never writes pointer or fence; exports D1
  read boundary only.
- `cg2_cutover_guard.py` imports only low-level contract/atomic-file helpers.
- `file_generation_pointer.py` may read the low-level guard but does not import
  `cg2_first_cutover.py` or the serving repository.
- `cg2_rollback_baseline.py` uses existing store/manifest contract and D0 chain;
  never writes pointer or fence.
- `cg2_first_cutover.py` orchestrates D0 chain, baseline, guard, fence, pointer,
  source-observation, and reconciliation checks; owns single owner-lock interval;
  calls private lock-held pointer writer only.
- `source_reconciler.py` remains the sole durable desired-source queue.
- `ServingIndexRepository` remains the sole serving read boundary.

No new daemon, CLI command, service, pointer format, current-active registry, or
rollback authority file is permitted.

## 14. Self-contained allowed-surface matrix (D0–D7)

If fulfilling the ratified architecture requires a surface **outside** this table
during Execute: **STOP for Luna/Ryan scope review.** Do not silently widen scope.
Implementation agents must **not** consult superseded plan `c48d9a9…` for omitted
detail — this table and stage sections above are authoritative.

### D0

| Category | Paths |
|---|---|
| Runtime/evidence | `cg2_legacy_vector_attestation.py` (new); `complete_data_restore.py` (minimal extend); read-only refs: `query.py`, `llm.py`, `eval_provenance.py`, `file_generation_contract.py`, `purge_locks.py`, `serving_authority.py` |
| Tests | `tests/test_cg2_legacy_vector_attestation.py` (new) |
| Formal | none |
| Documentation/evidence | none (fixtures inside tests only) |

### D1

| Category | Paths |
|---|---|
| Runtime/evidence | `cg2_rollback_baseline.py`; `file_generation_contract.py`; `file_generation_validate.py`; `file_generation_store.py`; `serving_index_repository.py`; bounded `complete_data_restore.py` interface |
| Tests | `tests/test_cg2_rollback_baseline.py`; `tests/test_file_generation_store.py`; `tests/test_file_generation_contract.py`; `tests/test_file_generation_validate.py`; `tests/test_serving_index_repository.py`; bounded `tests/test_complete_data_restore.py` |
| Formal | none |
| Documentation/evidence | none |

### D2

| Category | Paths |
|---|---|
| Runtime/evidence | `file_generation_pointer.py`; `cg2_cutover_guard.py` (new) |
| Tests | `tests/test_file_generation_pointer.py`; `tests/test_file_generation_validate.py`; `tests/test_source_freshness_promotion.py` |
| Formal | none |
| Documentation/evidence | none |

### D3

| Category | Paths |
|---|---|
| Runtime/evidence | `cg2_first_cutover.py` (new); `cg2_cutover_guard.py`; `serving_authority.py` (fence immutability) |
| Tests | `tests/test_cg2_first_cutover.py` (new); `tests/test_serving_authority.py`; `tests/test_serving_index_repository.py` |
| Formal | none |
| Documentation/evidence | none |

### D4

| Category | Paths |
|---|---|
| Runtime/evidence | `file_generation_pointer.py` (`rollback_active_pointer`); `source_reconciler.py` (rollback obligation helper) |
| Tests | `tests/test_file_generation_pointer.py`; `tests/test_source_reconciler.py`; `tests/test_source_freshness_promotion.py`; `tests/test_cg2_first_cutover.py` |
| Formal | none |
| Documentation/evidence | none |

### D5

| Category | Paths |
|---|---|
| Runtime/evidence | `cg2_rehearsal.py`; `cg2_property_map.py`; `mixed_mode_proof.py`; `ServingIndexRepository` (only if freeze test exposes violation — else STOP first) |
| Tests | `tests/test_cg2_rehearsal.py`; `tests/test_serving_index_repository.py`; `tests/test_mixed_mode_proof.py` |
| Formal | none |
| Documentation/evidence | rehearsal JSON evidence bundle (generated by tests/collect helper) |

### D6

| Category | Paths |
|---|---|
| Runtime/evidence | none |
| Tests | none (formal verification replaces unit tests for model) |
| Formal | `docs/plans/formal/cg2/CG2Authority.tla`; `CG2Cutover.cfg`; `CG2StaleReconcile.cfg`; `CG2Rename.cfg`; `CG2DesignA.cfg` (new); `README.md` |
| Documentation/evidence | TLC run records in formal README |

### D7

| Category | Paths |
|---|---|
| Runtime/evidence | `cg2_property_map.py`; `cg2_rehearsal.py` (evidence collector) |
| Tests | full suite verification (no new tests required unless gap found — then STOP) |
| Formal | TLC re-run confirmation at closure tip |
| Documentation/evidence | `docs/plans/VERIFY-cg2-production-activation.md` (Execute-time update only); Execute-close bundle artifact |

### Explicitly out of scope (all stages)

| Category | Paths — no Execute change without separate authorization |
|---|---|
| Production operations | D0 mutation/recapture/reratification; production `G_rb`/`G_canary`; failed-v1 cleanup/reuse; fence/pointer publication; owner activation; V8c; canary closure; GC; Shadow; R2b |
| Runtime (frozen) | `convmem.py`, `mcp_server.py`, `watch.py`, `doctor.py`, `chroma_write_store.py`, production config |
| Architecture/RUNBOOK | this planning package; no runtime mutation authorized by its publication |

## 15. Architecture invariant → implementation → test map

| Locked invariant | Implementation surface | Required mechanical evidence |
|---|---|---|
| D0 candidate not authority | `cg2_legacy_vector_attestation.py` | validation/ratification required oracles; tampered candidate refuses |
| D0 validation separate execution + one lock | D0 capture vs validation APIs | subprocess/separation oracle; validation acquires `source_flock` exactly once; churn oracle |
| D0 ratification fail-closed | ratification validator | digest mismatch / deletion refuses |
| Query context G_rb-only | D0 adapter; D1/D3/D4 checks | scoped rollback tests; known-model rollback without D0 |
| `G_rb` references the exact accepted LEGACY set | reference-v2 manifest + D0 chain | exact collection UUID/config, ID-set, row, and D0-root match |
| Versioned reference-v2 identity | `cg2_rollback_baseline.py` constant/derivation | deterministic ID differs from v1; failed v1 ID refuses |
| One physical vector authority | target-aware serving reader + cold qualifier | same descriptor/reader/output used by qualification and rollback scoring |
| No copied or sidecar authority | D1 orchestration/import inventory | Chroma write and sidecar dependency negative oracles |
| Unknown-model profile for `G_rb` | manifest under `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` | UNKNOWN/null historic model fields |
| Known-model profile for `G_canary` | canary manifest/evidence | `KNOWN_MODEL_AND_VECTOR_V1` binding |
| Provenance identity preserved | reference manifest + reader rebind | byte-identical envelope/`assertion_id`/`commitment`; no dedupe/remint |
| `RETAINED_ROLLBACK_BASELINE` protected | evidence v2; referenced-row retention | non-serving test; stage-`G_canary` test; reopen/recovery retention |
| CAS and durable lineage separate | `file_generation_pointer.py` | forward, first-cutover, rollback pointer-field matrix |
| Ordinary publish cannot create first pointer | `publish_active_pointer` | `expected_active=None` refusal |
| First cutover exact `G_rb` + `G_canary` + D0 chain | `cg2_first_cutover.publish_first_cutover_active_pointer` | exact IDs/SHAs/D0/query-context tests; single-lock acquisition oracle |
| `G_rb != G_canary` | first-cutover preflight | equality refusal before fence |
| Pre-fence refusal remains LEGACY | preflight before commit | refusal matrix |
| Post-fence failure is `FENCED_NO_POINTER` | one-lock fence/guard/pointer sequence | injected crash test |
| Fresh-grant resume only | dedicated first-cutover resume | fence→crash→resume; guard→crash→resume |
| Fence never clears to LEGACY | immutable fence | fence byte identity across failure/rollback |
| Rollback after source advance | `rollback_active_pointer` | source-advanced rollback + reconciliation |
| Reconciliation before stale rollback pointer | `source_reconciler.py` | persistence/restart/coalescing test |
| `G_rb` rollback needs D0 + query context + recovery | D4 preflight | G_rb-only serving-reader/recovery oracles; known-model negative |
| Recovery cannot switch generation | exact-payload recovery | alternate generation negative test |
| One owner-lock interval per authority change | public orchestration + private writer | reentry-failing `source_flock` oracle; first cutover exactly once; private writer never reacquires |
| No second promotion during canary | immutable open guard | second forward/first-cutover refusal |
| Frozen generation stable mid-request | `ServingIndexRepository` | pointer-change-mid-request test |
| GC disabled / baseline retained | `PHYSICAL_DELETION_DISABLED`; inventory | baseline survives cutover/rollback/reopen |
| Complete-data restore preserves D0/reference-v2 `G_rb` | bounded Recovery Authority interface | original-row + manifest/evidence + D0 + pointer/fence/guard + context restore matrix |

## 16. Reviewer observations (disposition)

| Observation | Disposition in this plan |
|---|---|
| Query-context formal property applies to G_rb only | §1.8, §8.2, §9.2, §11.3 `GRollbackRequiresExactQueryContext` scoped to `G_rb` |
| D0 remains valid unchanged | §1, §5, §6; reference-v2 adds supplementary binding only |
| Cosine copy is non-idempotent | §2 prohibited inheritance; §6 no Chroma write/upsert |
| Sidecar proof would split authority | §1 one physical authority; §6 same-reader and no-sidecar oracles |
| Failed v1 state is preserved but terminal | §1.13, §2, §6.3, D1R10; no cleanup schema/action |
| Cold qualification is a predicate | §1.14, §6.3; no new lifecycle literal |
| Recovery must cover the authoritative rows | §6 algorithm, D1R9, formal recovery property |
| Property/formal surfaces are implementation work | §11–§12; this planning commit edits neither runtime nor model files |

## 17. Global scope-stop rule

If Execute discovers required work outside §14 surface matrix, stop for Kiro/Ryan
review. Do not silently widen scope.

## 18. Global STOP conditions

Stop and report `UNRESOLVED — Ryan decision required` if:

- architecture and implementation diverge without Ryan amendment;
- D0 chain cannot be validated independently;
- D1 would guess historic model identity;
- qualification and serving would resolve different physical rows or readers;
- any copied generation, vector sidecar, re-embedding, or normalization
  reconstruction would become `G_rb` authority;
- query-context equality would apply to non-`G_rb` rollback generations;
- hermetic tests require production paths or live ratification;
- fresh-process qualification is bypassable;
- evidence idempotency masks byte mutation;
- first cutover can skip D0 reread or query-context check;
- formal model lacks required new properties;
- pylint regression gate fails;
- restore path could copy/re-embed and claim same `G_rb` or omit original rows;
- ordinary publication can bypass first cutover or open-canary guard;
- rollback and recovery share target-selection path;
- successful source-advanced rollback without durable reconciliation debt;
- any failure path removes fence or resolves post-fence owner as LEGACY;
- `FENCED_NO_POINTER` resume reuses old grant or overwrites conflicting artifacts;
- first cutover or rollback reacquires `source_flock` or requires nested locking;
- `G_rb` becomes abandoned, GC-eligible, or serving without active pointer;
- failed `2d01dfca…` can be reused, activated, selected, mutated, or cleaned;
- TLC counterexample, zero-coverage transition, unexplained test failure, or timeout;
- required work expands into GC, Shadow, R2b, production activation, or V8c.

## 19. Authorization sequence

1. Kiro independently reviews this exact corrective planning commit.
2. Ryan accepts or revises that exact reviewed plan.
3. Ryan separately grants a bounded Cursor implementation lane.
4. Cursor preserves D0 and implements **D1 reference-v2 → D2 → …** on a fresh
   branch; commit and push every slice.
5. Independent Kiro verification signs exact implementation/model tip (same-tip
   rule §12.3).
6. Ryan receives Execute-close bundle; separately authorizes production D1
   reference publication, then later `G_canary`/packet/V8c phases.

No plan approval implies implementation. No implementation implies production
`G_rb`, cleanup, `G_canary`, fence/pointer, or V8c. D0 remains unchanged.
