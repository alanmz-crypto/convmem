# Execution Plan — CG-2 Design A exact-vector bootstrap (superseding)

```text
Planning Status

Phase:        Design A Superseding Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Sol authors; Luna coordinates; Ryan HITL; Cursor implements only after grant
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
- not a serving pointer, not active generation state;
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
validate_d0_legacy_vector_candidate(generation_root, *, candidate_sha256, validator_identity) -> ValidationReference
```

Requirements:

- read-only reopen of persisted candidate + Chroma state;
- independently reproduce all roots and query-context digest;
- publish separate validation artifact with its own validator/code identity and
  result SHA-256;
- refuse if candidate fields cannot be reproduced;
- must not be callable from the same execution path that emitted the candidate
  (test oracle: monkeypatch/subprocess/spawn separation).

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
| Model artifact digest | resolve from Ollama model registry for selected model; emit `sha256:<64 lowercase hex>` — **fail closed if unresolved** (do not copy config; do not use eval degrade-to-empty) |
| Quantization | resolve from same registry record — fail closed if unresolved |
| Dimension | positive int from governed query-embedding response; must equal every admitted collection dimension |
| Runtime identifier | exact string `ollama` for this repository path |
| Runtime version | Ollama `/api/version` `version` field — fail closed if unresolved |

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

**Depends on:** D0 boundary stable + amended D1 public evidence validator stable.

Carry forward prior plan (`c48d9a9…`) with dependency note: first cutover and
rollback preflight will later require D0 chain fields — implement APIs now without
live D0 production data.

Surfaces (unchanged intent):

- `file_generation_pointer.py` — CAS vs lineage split, private lock-held writer,
  rollback/recovery separation;
- `cg2_cutover_guard.py` (new);
- `tests/test_file_generation_pointer.py` amendments;
- lock oracle via existing `source_flock` patterns.

**STOP if:** ordinary publish can create first pointer; rollback/recovery share
target selection; nested owner lock required.

## 8. D3 — First-cutover structural gate

**Depends on:** D2 + D1 retained-evidence validator.

Add to first-cutover preflight (prior plan plus):

- complete ratified D0 chain verification;
- `G_rb` proof profile = `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1`;
- exact retained-evidence SHA;
- live query-context re-derivation equals D0-ratified digest;
- before fence, independent reread/rebind of D0-covered current LEGACY rows
  (not stored D1 snapshot).

Surfaces:

- `cg2_first_cutover.py` (new);
- `cg2_cutover_guard.py`;
- `tests/test_cg2_first_cutover.py` (new);
- pointer/store/orchestration tests from prior plan.

## 9. D4 — Rollback after source advance

**Depends on:** D2 + D3 contracts stable.

For **`G_rb` rollback specifically** require:

- fresh qualification;
- complete D0 chain;
- retained-evidence SHA binding;
- exact query-context equality.

Do **not** impose D0 on later known-model rollback targets.

Preserve durable reconciliation-before-pointer rule from prior plan.

## 10. D5 — Rehearsal extension

**Depends on:** D1–D4 public contracts stable.

Extend `cg2_rehearsal.py` hermetic drill:

```text
D0 candidate (fixture)
→ independent validation (fixture)
→ synthetic Ryan ratification fixture
→ D1 G_rb
→ G_canary (KNOWN_MODEL_AND_VECTOR_V1)
→ first cutover
→ source advance
→ G_rb rollback
→ restart/recovery
```

All temporary roots/temporary Chroma. No live path.

Record: D0 digests, query-context digests, evidence SHAs, fence/guard hashes,
production paths absent.

## 11. D6 — Formal model

**Depends on:** D1–D4 stable public contracts.

Restore/update `docs/plans/formal/cg2/*` per prior plan and add properties:

| Property | Intent |
|---|---|
| `UnknownModelOnlyForRatifiedLegacyBaseline` | Only `G_rb` uses unknown-model profile |
| `ProspectiveGenerationRequiresKnownWriterModel` | Canary/later gens require known profile |
| `D0CandidateNotAuthority` | Candidate self-hash alone proves nothing |
| `D0ValidationRequired` | Validation digest required |
| `D0RatificationRequired` | Ryan ratification required for authority |
| `FirstCutoverRebindsCurrentLegacyRoot` | Live reread before fence |
| `GRollbackRequiresExactQueryContext` | **G_rb-only** query-context equality |

Carry forward all prior Design A properties from blocked plan mapping.

Verification:

```bash
# Exact TLC commands pinned in formal/README at Execute time
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

2026-08-14 TLC evidence remains historical old-revision only.

## 12. D7 — Execute closure

**Depends on:** D1–D6 pass at one implementation tip.

Update Execute evidence collectors (`cg2_rehearsal.collect_execute_evidence`,
property map, mixed-mode proof labels) at Execute time only.

**Do not edit** `VERIFY-cg2-production-activation.md` during Execute planning.

Flag for later Execute evidence: VERIFY still contains stale generic
"embedding provenance for both generations" wording — must be reconciled when
VERIFY is updated after implementation evidence exists.

V6c remains **PENDING** until real rollback drill passes at reviewed tip.

V8c remains **PENDING**.

Final suite before Ryan stop:

```bash
python -m pytest -q
python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report.json \
  --pylint-status $? \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref 06d9064648c96e46642d1820a504dace8af5ab38
git diff --check 06d9064648c96e46642d1820a504dace8af5ab38...HEAD
```

## 13. Reviewer observations (disposition)

| Observation | Disposition in this plan |
|---|---|
| Query-context formal property applies to G_rb only | §1.8, D3, D4, D6 property scoped explicitly |
| VERIFY generic embedding-provenance wording stale | Flagged §12; no VERIFY edit in planning |
| Ollama runtime version equality operationally significant | Noted §5.6; rehearsal should record runtime version drift risk |
| D0 candidate/validation must be separate executions | §5.4, D0 tests; optional independent validation lane noted for Ryan |
| Pin Ollama digest/quant/runtime sources | §5.6 table |
| Ratification format + fail-closed invalidation explicit | §5.5 |
| D0 evidence default retain after canary | §5.8 |
| Quiet-owner preference for later V8c | Noted for production phase outside Execute |
| Hardware/backend not ratified query context | Explicitly excluded §5.6; optional hermetic measurement only |

## 14. Global scope-stop rule

If Execute discovers required work outside the stage surface tables in §5.1, §6.1,
and prior-plan D2–D7 tables ( amended dependencies only ), stop for Luna/Ryan
review. Do not silently widen scope.

## 15. Global STOP conditions

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
- restore path could re-embed and claim same `G_rb`.

## 16. Authorization sequence

1. Luna reviews this superseding plan against architecture `3d8b151…`.
2. Ryan grants Design A Execute against this exact planning commit (or revises).
3. Cursor implements **D0 → D1 → D2 → …** on a fresh branch; push each slice.
4. Independent Luna verification signs exact implementation tip.
5. Ryan receives Execute-close bundle; separately authorizes production D0, then
   production D1 `G_rb`, then later packet/V8c phases.

No plan approval implies implementation. No implementation implies production D0,
ratification, `G_rb`, fence/pointer, or V8c.
