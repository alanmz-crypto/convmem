# Execution Plan — CG-2 Design A exact-vector bootstrap (superseding)

```text
Planning Status

Phase:        Design A Superseding Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Cursor Auto authors superseding plan; Luna independently reviews; Ryan HITL; Cursor implements only after grant
Authority:    Awaiting Ryan HITL — planning artifact only
```

**Arc:** CG-2

**This plan SUPERSEDES the blocked execution plan at:**

`c48d9a9cc2b20df6d9a834f3e4377046504fed76`

That prior plan assumed caller-supplied historic embedding provenance and had no
D0 exact-vector authority substrate. It correctly stopped at independent Luna
verification. This document replaces it under the ratified architecture
amendment below.

**Ratified architecture authority (planning base):**

`3d8b151907f02c8b8ead89585fb43904840b210b`

[`ARCHITECTURE-cg2-production-activation.md`](ARCHITECTURE-cg2-production-activation.md),
[`RUNBOOK-cg2-production-activation.md`](RUNBOOK-cg2-production-activation.md), and
[`VERIFY-cg2-production-activation.md`](VERIFY-cg2-production-activation.md) as
present at the ratified architecture SHA.

**Superseded architecture lock (historical only):**

`8aff0a316cb4304c5313556abc3cdf5439746835`

**Blocked reusable implementation checkpoint (NOT D1 authority):**

`fca6526e6ae4d5cf008afa8a2f465fd2c37bfa23` on branch
`feat/2026-08-21-cg2-design-a-execute`

**Goal:** translate the ratified exact-vector bootstrap architecture into a
bounded, mechanically executable plan that adds D0, rewrites D1 around D0
authority, and carries D2–D7 forward only where still compatible.

**Plan status:** planning only. This document authorizes no Python, test, formal
model, configuration, corpus, D0 production capture, D0 validation,
Ryan ratification, generation-root mutation, fence, pointer, activation, packet,
grant, GC, Shadow, or R2b change.

## Human consequence

If Ryan approves this superseding plan, Cursor may implement Design A in bounded
hermetic slices on a fresh implementation branch anchored after this planning
commit. The result will require a complete three-part D0 authority chain before
any `G_rb` conversion; make `G_rb` an exact-vector historical-state baseline
under `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`; bind first-cutover and `G_rb`
rollback to exact D0-ratified query-embedding context; and preserve the prior
Design A cutover/rollback separation.

Approval of this plan would authorize only hermetic implementation, tests,
formal verification, rehearsal, and Execute evidence. It would **not** authorize
production D0 capture, production D0 validation/ratification, production
`G_rb`, production `G_canary`, production fence/pointer publication, first-owner
activation, V8c PASS/grant, canary closure, GC, Shadow, or R2b. Those remain
separate HITL gates.

### 5 Ws

| Field | Answer |
|---|---|
| **Who** | Cursor implements after Ryan Execute grant against this exact planning commit; independent Luna/Codex review signs the implementation tip; Ryan alone gates production D0, ratification, generation builds, and V8c. |
| **What** | D0 exact-vector attestation machinery + amended D1 `G_rb` conversion + prior Design A D2–D7 surfaces updated for D0/query-context bindings. |
| **When** | After architecture ratification at `3d8b151…`, before any production D0 capture or `G_rb` build. |
| **Why** | Accepted LEGACY vectors have no durable historic model identity; guessing model provenance was correctly blocked at `fca6526`. |
| **How** | Hermetic D0 substrate → ratified D0 chain (production, later) → D1 authority consumer → D2–D7 as amended below. |

**TL;DR:** Add D0 exact-vector authority, rewrite D1 to consume it, preserve
valid D2–D7 work with updated dependencies. No production operations in Execute.

## 1. Locked invariants (ratified amendment)

Implementation must preserve all of the following:

1. **D0 before D1.** No `G_rb` conversion without complete ratified D0 chain.
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
7. **No caller-held snapshot staging.** D1 rereads covered rows under lock and
   stages those reread rows only.
8. **Query-context equality is G_rb-specific.**
   `live_query_embedding_context_sha256 == D0_ratified_query_embedding_context_sha256`
   is required for D1, first cutover, and `G_rb` rollback only — not for later
   known-model rollback generations.
9. **Retained evidence is byte-exact immutable.** Fresh-process qualification is
   mandatory at authority use; stored cold evidence is historical, not a
   substitute for current qualification.
10. **Prior Design A cutover semantics remain:** exact `G_rb` + exact `G_canary`,
    dedicated first-cutover CAS `None`, monotonic fence, `FENCED_NO_POINTER`,
    canary-open guard, rollback lineage split, durable reconciliation on
    source-advanced rollback, exact recovery only.
11. **Complete-data restore must preserve non-reconstructible authority artifacts**
    and refuse restore paths that would re-embed and claim the same `G_rb`.

## 2. Blocked checkpoint `fca6526` — reusable vs must correct

Branch `feat/2026-08-21-cg2-design-a-execute` at `fca6526` is a **reusable
engineering checkpoint**, not amended D1 authority.

### Reusable (carry forward with amendment)

| Area | Reusable artifact | Amendment required |
|---|---|---|
| Production Chroma/generation-root refusal | `_resolve_live_production_paths`, `_refuse_unattested_production_chroma`, `_refuse_unattested_production_generation_root`, `FileGenerationStore._assert_not_unattested_production_chroma` | None beyond D0/D1 path wiring |
| LEGACY owner/source classifier | `_require_legacy_owner`, `_is_legacy_serving_row`, superseded/stable exclusion | D0 capture uses same classifier; D1 consumes D0-covered set |
| Accepted-source binding | `_bind_accepted_source_hash`, canonical SHA-256 hex enforcement | D1 must rebind at conversion boundary (already started in `fca6526` correction 3) |
| Persisted embedding reads | `_as_float_tuple`, non-finite refusal | D0 must pin canonical float32 byte encoding for hashes |
| Convert-v1 identity | `CONVERT_V1_FINGERPRINT`, `make_generation_id`, candidate bundle hash | Manifest must use `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` profile |
| Retained baseline protection | `FileGenerationStore` retained-baseline map | Unchanged |
| Manifest / cold validation plumbing | `publish_manifest`, `run_cold_validation`, `file_generation_validate.cold_validate` | D1 evidence must not treat stored cold as authority substitute |
| Bidirectional equivalence algorithm | `prove_bidirectional_equivalence`, normalized row identity helpers | Rebind from manifest + D0 reread, not caller snapshot |
| Same-ledger distinct-provenance twins | provenance identity evidence structure | Full envelope rebind per architecture §7.0.3 |
| Adversarial evidence tests | pattern in `tests/test_cg2_rollback_baseline.py` | Extend for D0 chain + query context + fresh-process |

### Must discard or rewrite

| Blocked behavior | Why |
|---|---|
| `capture_accepted_legacy_serving_snapshot` as D1 entry | D1 must reread under lock from persisted state, not caller snapshot |
| Caller `embedding_provenance` authority | Historic model fields forbidden for `G_rb`; authority is D0 chain + unknown-model profile |
| `run_fresh_process_qualification=False` bypass | Removed in `fca6526`; plan requires stored cold never substitutes live qualification |
| Evidence idempotency ignoring `sequence_positions` drift | Architecture requires byte-exact immutability; only exact-byte idempotency |
| Implicit historic model in manifest collection specs | Replace with `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` semantics |

## 3. Stage dependency graph

```text
D0 (hermetic substrate only)
  ↓
D1 (amended G_rb from ratified D0 chain — hermetic fixtures)
  ↓
D2 (authority API separation)
  ↓
D3 (first-cutover gate + D0/query-context rebind)
  ↓
D4 (rollback after source advance — G_rb-specific D0/query checks)
  ↓
D5 (rehearsal extended through D0→D1→cutover→rollback)
  ↓
D6 (formal model + TLC)
  ↓
D7 (Execute closure / VERIFY evidence — no VERIFY edit in planning)
```

Production D0 capture → validation → Ryan ratification is **outside** this graph
until separately authorized.

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

Implement as constants in `cg2_legacy_vector_attestation.py`:

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
objects. Planning does not duplicate every field here; Execute must implement
field-for-field parity with architecture SHA `3d8b151…`.

## 5. D0 — Exact-vector authority substrate (hermetic implementation only)

**Execute authorizes:** hermetic machinery, validators, readers, tests, fixture
ratification records.

**Execute does NOT authorize:** production D0 capture, production independent
validation, Ryan production ratification, production `G_rb`, fence/pointer, D1
resumption on live owner.

### 5.1 Expected surfaces

| Path | Responsibility |
|---|---|
| `cg2_legacy_vector_attestation.py` (new) | D0 candidate capture; independent validation; ratification record validator; canonical roots; query-context derivation; governed-root layout; read-only D1 consumption helpers |
| `tests/test_cg2_legacy_vector_attestation.py` (new) | Red-first oracles for canonicalization, capture consistency, separate-execution validation, ratification chain, query context, adversarial tamper+rehash |
| `query.py` | **Read-only reference only during D0 planning.** Execute may add a thin adapter function in D0 module calling existing `ollama_embed` path — do not modify query ranking behavior in D0 |
| `llm.py` | Governed embedding POST implementation reference (`/api/embeddings`, model+prompt) |
| `eval_provenance.py` | Reference for Ollama version/model digest/quant **resolution semantics** — D0 must fail closed; no eval-style degrade-to-empty |
| `file_generation_contract.py` | Reuse `canonical_bytes` / `canonical_hash` |
| `purge_locks.py` | Reuse existing `source_flock` — no new lock |
| `serving_authority.py` | Reuse `generation_root_for_cfg`, fence/pointer/retirement existence checks |
| `complete_data_restore.py` | Smallest matrix extension so complete-data backup/restore preserves D0 artifacts (see §5.8) |

No other runtime modules in D0 unless scope-stop.

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

Public hermetic entry (exact name may adjust during Execute if repo conventions
require, but single module above):

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
5. Read admitted LEGACY rows from temporary/hermetic Chroma only in Execute tests.
6. Bind exact collection UUID/configuration/dimension per collection.
7. Build ordered leaves, collection roots, aggregate snapshot root.
8. Derive `QUERY_EMBEDDING_CONTEXT_V1` through governed adapter (§5.6).
9. End-of-capture recheck: authority still LEGACY, row counts/roots unchanged,
   query-context digest unchanged.
10. Publish candidate artifact with producer SHA, module identity, schema version,
    attestation timestamps labeled processing time only.

Any churn during capture refuses candidate emission.

### 5.4 Independent validation (separate execution)

Public hermetic entry:

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

Public validators:

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

Deletion, invalidation, or digest mismatch fails closed. Execute implements
reader/validator + hermetic synthetic ratification fixtures only. Ryan production
ratification remains unauthorized.

### 5.6 QUERY_EMBEDDING_CONTEXT_V1 — implementation pin

Governed query adapter sources at architecture SHA:

| Field | Execute pin (repository inspection) |
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

Export from D0 module only:

```text
load_ratified_d0_chain(...) -> D0AuthorityChain
verify_d0_chain_for_grb_conversion(chain, *, live_query_context_sha256) -> None
```

D1 must not import private D0 capture helpers except through this boundary.

### 5.8 Backup/restore preservation (smallest change)

Extend `complete_data_restore.py` StateSpec validation so complete-data restore:

- preserves under `{data_root}`: D0 candidate, validation, ratification, actual
  non-reconstructible `G_rb` Chroma rows, retained rollback evidence, manifests,
  applicable fence/pointer/guard artifacts, query-context binding records;
- refuses restore that would substitute re-embedded vectors as the same `G_rb`;
- keeps existing non-authoritative backup evidence non-authoritative.

Exact path globs follow §5.2 layout plus existing generation/manifest paths.
No D0 evidence retirement/GC in this Execute.

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

## 6. D1 — Exact G_rb conversion from ratified D0 (hermetic)

**Depends on:** D0 public read/validate boundary stable.

**Execute authorizes:** amended `cg2_rollback_baseline.py`, store protection,
hermetic tests using synthetic D0 chain fixtures — not production ratification.

### 6.1 Expected surfaces

| Path | Responsibility |
|---|---|
| `cg2_rollback_baseline.py` (new/amended from checkpoint) | D1 authority consumer: load D0 chain, reread rows under lock, convert-v1 staging, manifest under unknown-model profile, fresh-process qualification, immutable retained evidence |
| `file_generation_store.py` | Retained-baseline protection (reuse checkpoint) |
| `tests/test_cg2_rollback_baseline.py` (new/amended) | D1 oracles per §6.3 |
| `tests/test_file_generation_store.py` | Retained baseline backpressure (reuse checkpoint) |

Do **not** modify `chroma_write_store.py`.

Remove/never restore:

- caller snapshot convert entrypoint;
- caller `embedding_provenance` authority;
- in-process-only qualification path;
- semantic-equivalence idempotency that ignores cold byte fields.

### 6.2 D1 algorithm (authority consumer)

Under existing `source_flock` once:

1. Refuse configured-live Chroma/generation-root mutation without writer
   attestation (reuse checkpoint guards).
2. Load ratified D0 chain from governed root; verify ratification + digests.
3. Re-derive live `QUERY_EMBEDDING_CONTEXT_V1`; require exact equality with
   D0-ratified digest.
4. Revalidate LEGACY authority and accepted-source binding.
5. Independently reread exact D0-covered rows/vectors/provenance from Chroma;
   recompute all D0 roots; require exact match to ratified roots.
6. Stage reread rows only (never caller-held snapshot).
7. Build manifest under `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` with historic model
   fields exactly unknown/null.
8. Publish manifest; run **fresh-process** qualification via
   `file_generation_validate.run_cold_validation` in a new interpreter.
9. Prove bidirectional equivalence against reread set.
10. Publish immutable retained evidence with complete provenance envelope evidence
    rebound from manifest immutable metadata.
11. Evidence idempotent **only** on exact immutable byte equality.

Any drift → refuse; require new D0 capture → validation → ratification (production,
later).

### 6.3 D1 required corrections mapped to tests

| Correction | Test oracle |
|---|---|
| A1 no caller snapshot trust | tampered in-memory snapshot ignored; convert rereads persisted rows |
| A2 fresh-process mandatory | patch `run_cold_validation` failure refuses; forged cold without `sequence_positions` fails validation |
| B1/B3 no historic model authority | manifest collections show UNKNOWN/null; caller model/digest/timestamp rejected |
| B2 envelope rebind | adversarial envelope swap + rehash refuses |
| Reuse production guards | configured-live paths refuse without attestation |
| Reuse accepted-source rebind | uppercase/wrong hash refuses at convert boundary |

### 6.4 D1 verification

```bash
python -m pytest tests/test_cg2_rollback_baseline.py \
  tests/test_file_generation_store.py \
  tests/test_file_generation_contract.py -q
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

### 6.5 D1 STOP if

- D0 chain cannot be represented without widening scope;
- exact roots cannot be reproduced from persisted rows;
- manifest cannot express unknown-model profile without CG-1 contract change;
- same-ledger distinct-provenance twins collapse;
- fresh-process qualification cannot run hermetically.

## 7. D2 — Authority API separation

**Depends on:** D0 public read boundary stable + amended D1 retained-evidence
validator stable. No production D0 operations required.

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
    rollback_baseline_evidence,
    expected_active_generation_id=None, ...)

rollback_active_pointer(
    retained_manifest_reference,
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
| `cg2_first_cutover.py` (new) | Public dedicated first-cutover operation: preflight exact bindings before fence; acquire owner lock exactly once for monotonic fence, open guard, and dedicated first pointer; resume `FENCED_NO_POINTER` only under fresh grant; no CLI and no production defaults |
| `cg2_cutover_guard.py` | Complete low-level guard publication/validation (started in D2) |
| `serving_authority.py` | Fence publication immutable/idempotent-identical; reject replacement; preserve `FENCED_NO_POINTER` resolution; no fence deletion API |
| `tests/test_cg2_first_cutover.py` (new) | Exact structural gate, pre/post-fence timing, proof profiles, D0 chain, query context, crash/resume states |
| `tests/test_serving_authority.py` | Monotonic fence bytes; durable fence with no pointer resolves only `FENCED_NO_POINTER` |
| `tests/test_serving_index_repository.py` | Supporting authority-resolution fixtures as needed |

### 8.2 First-cutover preflight (before any fence bytes)

`cg2_first_cutover.py` has a preflight phase and one commit phase. Before any
fence bytes exist, preflight must prove exactly:

1. `G_rb != G_canary` (distinct generation IDs);
2. exact `G_rb` generation ID and manifest SHA match immutable retained-baseline
   evidence;
3. exact `G_canary` generation ID and manifest SHA match caller's grant-bound inputs;
4. **`G_rb` proof profile = `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`**;
5. **`G_canary` proof profile = `KNOWN_MODEL_AND_VECTOR_V1`**;
6. complete ratified D0 chain verification (candidate + validation + ratification
   digests, accepted snapshot root, ratified query-context digest);
7. exact retained-evidence SHA binding for `G_rb`;
8. live query-embedding context re-derivation equals D0-ratified
   `query_embedding_context_sha256`;
9. both manifests bind the same owner key/digest and canonical source path;
10. both have internally consistent collection dimensions/configuration under their
    respective proof profiles;
11. both pass fresh-process exact qualification;
12. current pointer is absent, current owner is LEGACY, reconciliation is fresh,
    and current source hash equals `G_canary.source_hash`;
13. the first-canary guard does not already exist;
14. **before fence:** independent reread/rebind of D0-covered current LEGACY rows
    under the existing owner lock — not a stored D1 snapshot; reproduced roots must
    match ratified D0 roots.

Any preflight failure returns before fence publication. Missing, corrupt,
wrong-owner, wrong-manifest-SHA, non-equivalent, unqualified baseline evidence,
D0 chain mismatch, or query-context mismatch therefore leaves the owner LEGACY.

### 8.3 Commit phase (one owner lock)

The commit phase acquires the existing owner lock once, rechecks all exact
artifact hashes, pointer absence, current source, owner binding, D0 chain, and
query context, then:

1. atomically publishes the immutable monotonic fence;
2. atomically publishes the immutable first-canary-open guard naming exact
   `G_rb` and `G_canary` and evidence hashes;
3. reruns the final exact qualification/binding checks and invokes the private
   lock-held pointer writer with first-cutover semantics:
   `expected_active_generation_id=None`, durable `previous_generation_id=G_rb`,
   active=`G_canary` (exact grant-bound `G_canary`);
4. returns the module-sealed qualified active pointer.

No catch block removes or rewrites the fence. A crash or failure after step 1
and before successful step 3 leaves `FENCED_NO_POINTER`; a fresh request can
never resolve LEGACY. The guard is non-serving evidence and may exist in that
fail-closed state.

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

The dedicated public `publish_first_cutover_active_pointer` operation owns the
only normal completion path for both resumable crash states:

- fence present / guard absent / pointer absent;
- fence present / exact guard present / pointer absent.

Neither state may reuse or continue under the pre-crash grant. Resume requires
a fresh Ryan one-shot grant bound to the exact `G_rb` and `G_canary`. Before
acquiring the owner lock, the operation requalifies both exact grant-bound
generations and reconstructs the exact expected immutable fence/guard evidence.
Under its single owner-lock commit section it then:

1. revalidates the existing fence as immutable, structurally valid, and bound
   to the exact owner/source expected by the fresh grant;
2. validates the guard as either absent or exact/byte-identical to the expected
   guard for the same `G_rb`, `G_canary`, owner/source, and evidence hashes;
3. if the guard is absent, atomically publishes that exact guard; if already
   exact, leaves bytes unchanged;
4. rechecks pointer absence and the fresh grant's exact structural and
   qualification preconditions (including D0 chain and query context for `G_rb`);
5. invokes the private lock-held pointer writer once to complete the exact
   first pointer with CAS `None`, previous=`G_rb`, and active=`G_canary`.

A missing fence is not a resume state. Conflicting, malformed, or corrupt fence
or guard fails closed and requires operator repair.

### 8.5 Red tests first

- Parameterized pre-fence refusal matrix: missing baseline, corrupt evidence,
  wrong owner, wrong source, wrong manifest SHA, failed qualification,
  non-equivalent set, D0 chain mismatch, query-context mismatch, and
  `G_rb == G_canary`.
- Assert every pre-fence refusal leaves no fence and no pointer.
- Inject failure/crash after durable fence and before pointer; assert
  `FENCED_NO_POINTER`, monotonic fence bytes, no pointer, no LEGACY recovery.
- `fence → crash → fresh-grant resume` coverage.
- `fence → guard → crash → fresh-grant resume` coverage.
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

- any structural check can occur only after the fence;
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
3. **For `G_rb` rollback target only** (proof profile
   `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`): additionally require complete D0
   chain verification, exact retained-evidence SHA binding, and live
   query-embedding context equality with D0-ratified digest. **Do not impose
   D0 or query-context requirements on later known-model rollback generations.**
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
- restart durability for reconciliation state and fence/guard bytes;
- production configured paths absent from rehearsal roots.

### 10.3 Evidence bundle fields

Rehearsal JSON must include at minimum:

- architecture SHA `3d8b151…` and execution-plan SHA;
- implementation SHA at rehearsal tip;
- D0 candidate, validation, and synthetic ratification digests;
- ratified and live query-context digests;
- exact `G_rb` and `G_canary` generation IDs and manifest SHAs;
- retained-evidence SHA;
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
| `docs/plans/formal/cg2/CG2Authority.tla` | Restore from `e680ce837653698a5be8b78ba02db2f880c40c63`, then add Design A baseline, D0 chain, first-cutover, rollback, recovery, reconciliation, canary-window, query-context (G_rb-only), and refusal transitions |
| `docs/plans/formal/cg2/CG2Cutover.cfg` | Restore and rerun cutover/read-authority properties against changed shared model |
| `docs/plans/formal/cg2/CG2StaleReconcile.cfg` | Restore and rerun stale-source reconciliation and recovery properties |
| `docs/plans/formal/cg2/CG2Rename.cfg` | Restore and rerun rename/pinning properties |
| `docs/plans/formal/cg2/CG2DesignA.cfg` (new) | Focused exhaustive instance for exact baseline, D0 chain, first cutover, rollback-after-source-advance, recovery separation, canary guard, query-context (G_rb-only) |
| `docs/plans/formal/cg2/README.md` | Preserve 2026-08-14 evidence as historical old-revision only; map new properties/configs; record separate Design A run |

Restoration diff must be reviewed against `e680ce8` before model edits.

### 11.2 Required new transitions/state

- D0 candidate capture (non-authoritative until ratified);
- independent D0 validation required;
- Ryan D0 ratification required for authority;
- exact LEGACY-set conversion to qualified retained baseline under unknown-model
  profile;
- pre-fence structural refusal preserves LEGACY;
- durable fence without pointer (`FENCED_NO_POINTER`);
- fresh-grant resume from fence/no-guard/no-pointer;
- fresh-grant resume from fence/exact-guard/no-pointer;
- wrong/conflicting guard refusal with no pointer and no LEGACY restoration;
- first pointer with CAS `NoGen`, previous=`G_rb`, active=`G_canary`;
- first cutover rebinds current LEGACY root (live reread);
- ordinary forward promotion with CAS separate from lineage;
- source advance followed by exact retained-generation rollback;
- **`G_rb` rollback requires exact query context** (not all retained gens);
- durable reconciliation-required before/with stale-source rollback;
- same-pointer recovery with no generation selection;
- first-canary-open refusal of second forward promotion;
- GC exclusion for `RETAINED_ROLLBACK_BASELINE`;
- one acquisition/release interval per authority-changing operation.

### 11.3 Required named properties

**New (ratified amendment):**

| Property | Intent |
|---|---|
| `UnknownModelOnlyForRatifiedLegacyBaseline` | Only `G_rb` uses unknown-model profile |
| `ProspectiveGenerationRequiresKnownWriterModel` | Canary/later gens require known profile |
| `D0CandidateNotAuthority` | Candidate self-hash alone proves nothing |
| `D0ValidationRequired` | Validation digest required |
| `D0RatificationRequired` | Ryan ratification required for authority |
| `FirstCutoverRebindsCurrentLegacyRoot` | Live LEGACY reread before fence |
| `GRollbackRequiresExactQueryContext` | **G_rb / LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1 only** |

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

**Prior architecture properties (from restored model — must remain checked):**

- fence monotonicity; `FENCED_NO_POINTER`; first-cutover CAS;
- rollback/recovery distinction; stale-source reconciliation;
- canary-open guard; retention/no-GC; `FrozenGenerationStable` where applicable.

### 11.4 TLC invocation (all four configurations required)

```bash
TLA_JAR=/path/to/tla2tools.jar  # record exact JAR path, TLC version, checksum

for config in CG2Cutover CG2StaleReconcile CG2Rename CG2DesignA; do
  java -Xmx2g -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC \
    -workers 2 -coverage 1 \
    -config "docs/plans/formal/cg2/${config}.cfg" \
    docs/plans/formal/cg2/CG2Authority.tla
done
```

**Success criteria per configuration:**

- empty error queue, zero counterexamples;
- generated/distinct state counts and depth recorded in README;
- nonzero action coverage for every required new transition;
- no skipped configuration accepted;
- timeout is not PASS — investigate or STOP.

**Evidence recording:** TLA+ release/JAR checksum, exact command lines, per-config
generated/distinct counts, depth, coverage summary. README preserves 2026-08-14
counts as historical old-revision evidence only; Design A run is a separate section.

Historical TLC results at `e680ce8` / 2026-08-14 remain old-revision evidence only.

### 11.5 D6 verification

```bash
for config in CG2Cutover CG2StaleReconcile CG2Rename CG2DesignA; do
  java -Xmx2g -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC \
    -workers 2 -coverage 1 \
    -config "docs/plans/formal/cg2/${config}.cfg" \
    docs/plans/formal/cg2/CG2Authority.tla
done
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

### 11.6 D6 STOP if

- TLC finds a counterexample;
- any required action has zero coverage;
- restored model cannot be tied to `e680ce8`;
- a property needs an architecture decision not already locked at `3d8b151…`;
- `GRollbackRequiresExactQueryContext` is scoped beyond `G_rb`;
- work expands beyond §11.1 surface table.

## 12. D7 — Execute closure, evidence, and Ryan stop

**Depends on:** D0–D6 pass at **one implementation tip**.

**Execute authorizes:** evidence collectors, property map, VERIFY row updates
(within Execute evidence phase). **Execute does NOT authorize:** production
operations listed in §12.4.

### 12.1 Execute-time tasks

After D0–D6 pass at one tip:

1. Update `cg2_property_map.py` with every Design A property → exact pytest
   node mapping (including D0 properties and dedicated `FrozenGenerationStable`).
2. Update `cg2_rehearsal.collect_execute_evidence()` with canonical architecture
   SHA `3d8b151…`, execution-plan SHA, implementation SHA, model SHA, focused/full
   test results, TLC evidence identities, D0 chain fixture digests, and explicit
   no-production flags.
3. Update `docs/plans/VERIFY-cg2-production-activation.md` mechanical rows **only
   after implementation evidence exists** — do not edit VERIFY during planning.
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

# All four TLC configurations (see §11.4)
for config in CG2Cutover CG2StaleReconcile CG2Rename CG2DesignA; do
  java -Xmx2g -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC \
    -workers 2 -coverage 1 \
    -config "docs/plans/formal/cg2/${config}.cfg" \
    docs/plans/formal/cg2/CG2Authority.tla
done

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
existing CG-1 contract/store + D0 hermetic substrate
        │
        ├── D1 amended G_rb conversion/evidence
        │       └── retained-baseline protection
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
| Runtime/evidence | `cg2_rollback_baseline.py` (new/amended); `file_generation_store.py` (retained-baseline protection) |
| Tests | `tests/test_cg2_rollback_baseline.py` (new/amended); `tests/test_file_generation_store.py`; `tests/test_file_generation_contract.py` |
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
| Production operations | live D0 capture; live D0 validation; Ryan production ratification; production `G_rb`/`G_canary`; fence/pointer publication; owner activation; V8c; canary closure; GC; Shadow; R2b |
| Runtime (frozen) | `convmem.py`, `mcp_server.py`, `watch.py`, `doctor.py`, `chroma_write_store.py`, production config |
| Architecture/RUNBOOK | read-only inputs at `3d8b151…` |

## 15. Architecture invariant → implementation → test map

| Locked invariant | Implementation surface | Required mechanical evidence |
|---|---|---|
| D0 candidate not authority | `cg2_legacy_vector_attestation.py` | validation/ratification required oracles; tampered candidate refuses |
| D0 validation separate execution | D0 capture vs validation APIs | subprocess/separation oracle |
| D0 ratification fail-closed | ratification validator | digest mismatch / deletion refuses |
| Query context G_rb-only | D0 adapter; D1/D3/D4 checks | scoped rollback tests; known-model rollback without D0 |
| Accepted LEGACY set converts exactly to `G_rb` | `cg2_rollback_baseline.py` + D0 chain | bidirectional equivalence; D0 root match |
| Ratified convert-v1 fingerprint | `cg2_rollback_baseline.py` constant | deterministic ID/fingerprint test |
| Unknown-model profile for `G_rb` | manifest under `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` | UNKNOWN/null historic model fields |
| Known-model profile for `G_canary` | canary manifest/evidence | `KNOWN_MODEL_AND_VECTOR_V1` binding |
| Provenance identity preserved | D1 envelope rebind | byte-identical envelope/`assertion_id`/`commitment`; no dedupe/remint |
| `RETAINED_ROLLBACK_BASELINE` protected | baseline evidence; store protection | non-serving test; stage-`G_canary` test; reopen retention |
| CAS and durable lineage separate | `file_generation_pointer.py` | forward, first-cutover, rollback pointer-field matrix |
| Ordinary publish cannot create first pointer | `publish_active_pointer` | `expected_active=None` refusal |
| First cutover exact `G_rb` + `G_canary` + D0 chain | `cg2_first_cutover.py` | exact IDs/SHAs/D0/query-context tests |
| `G_rb != G_canary` | first-cutover preflight | equality refusal before fence |
| Pre-fence refusal remains LEGACY | preflight before commit | refusal matrix |
| Post-fence failure is `FENCED_NO_POINTER` | one-lock fence/guard/pointer sequence | injected crash test |
| Fresh-grant resume only | dedicated first-cutover resume | fence→crash→resume; guard→crash→resume |
| Fence never clears to LEGACY | immutable fence | fence byte identity across failure/rollback |
| Rollback after source advance | `rollback_active_pointer` | source-advanced rollback + reconciliation |
| Reconciliation before stale rollback pointer | `source_reconciler.py` | persistence/restart/coalescing test |
| `G_rb` rollback needs D0 + query context | D4 preflight | G_rb-only oracles; known-model negative |
| Recovery cannot switch generation | exact-payload recovery | alternate generation negative test |
| One owner-lock interval per authority change | public orchestration + private writer | reentry-failing `source_flock` oracle |
| No second promotion during canary | immutable open guard | second forward/first-cutover refusal |
| Frozen generation stable mid-request | `ServingIndexRepository` | pointer-change-mid-request test |
| GC disabled / baseline retained | `PHYSICAL_DELETION_DISABLED`; inventory | baseline survives cutover/rollback/reopen |
| Complete-data restore preserves D0/G_rb | `complete_data_restore.py` | restore matrix tests |

## 16. Reviewer observations (disposition)

| Observation | Disposition in this plan |
|---|---|
| Query-context formal property applies to G_rb only | §1.8, §8.2, §9.2, §11.3 `GRollbackRequiresExactQueryContext` scoped to `G_rb` |
| VERIFY generic embedding-provenance wording stale | §12.6 Execute-time reconciliation; no VERIFY edit in planning |
| Ollama runtime version equality operationally significant | §5.6 runtime drift paragraph; §10.2 rehearsal records risk |
| D0 candidate/validation must be separate executions | §5.3–§5.4; D0 tests; optional independent validation lane |
| Pin Ollama digest/quant/runtime sources | §5.6 exact `/api/tags` and `/api/version` pins; STOP if untrustworthy |
| Ratification format + fail-closed invalidation explicit | §5.5 |
| D0 evidence default retain after canary | §5.8 |
| Quiet-owner preference for later V8c | Noted — production phase outside Execute; LEGACY ingest after D0 invalidates chain |
| Hardware/backend not ratified query context | §5.6 excluded; optional hermetic measurement only |

## 17. Global scope-stop rule

If Execute discovers required work outside §14 surface matrix, stop for Luna/Ryan
review. Do not silently widen scope.

## 18. Global STOP conditions

Stop and report `UNRESOLVED — Ryan decision required` if:

- architecture and implementation diverge without Ryan amendment;
- D0 chain cannot be validated independently;
- D1 would guess historic model identity;
- query-context equality would apply to non-`G_rb` rollback generations;
- hermetic tests require production paths or live ratification;
- fresh-process qualification is bypassable;
- evidence idempotency masks byte mutation;
- first cutover can skip D0 reread or query-context check;
- formal model lacks required new properties;
- pylint regression gate fails;
- restore path could re-embed and claim same `G_rb`;
- ordinary publication can bypass first cutover or open-canary guard;
- rollback and recovery share target-selection path;
- successful source-advanced rollback without durable reconciliation debt;
- any failure path removes fence or resolves post-fence owner as LEGACY;
- `FENCED_NO_POINTER` resume reuses old grant or overwrites conflicting artifacts;
- first cutover or rollback reacquires `source_flock` or requires nested locking;
- `G_rb` becomes abandoned, GC-eligible, or serving without active pointer;
- TLC counterexample, zero-coverage transition, unexplained test failure, or timeout;
- required work expands into GC, Shadow, R2b, production activation, or V8c.

## 19. Authorization sequence

1. Luna re-reviews this superseding plan against architecture `3d8b151…`.
2. Ryan grants Design A Execute against this exact planning commit (or revises).
3. Cursor implements **D0 → D1 → D2 → …** on a fresh branch; commit and push
   every slice.
4. Independent Luna verification signs exact implementation/model tip (same-tip
   rule §12.3).
5. Ryan receives Execute-close bundle; separately authorizes production D0, then
   production D1 `G_rb`, then later packet/V8c phases.

No plan approval implies implementation. No implementation implies production D0,
ratification, `G_rb`, fence/pointer, or V8c.
