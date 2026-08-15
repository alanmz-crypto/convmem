# Execution Plan — Dependability and Provenance Integrity

```text
Status:       DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
Depends on:  Kiro review, targeted Copilot audit, Ryan architecture lock
Owner:       Cursor after a separate Ryan Execute grant
Baseline:    origin/main @ 2f427fcfb8818dd665310bae7e8cd5ffa066bdcc
```

## Human consequence

This plan decomposes the first implementation slice so reviewers can test its
feasibility. It does not authorize code changes, migrations, live Chroma/corpus
mutation, CG-2 activation, Shadow activation, R2b capture, or external changes.
Stage 1 must be additive and conservative: existing records remain queryable but
are untrusted for security decisions until they carry valid provenance.

## Scope lock

### In scope for Stage 1

- one canonical provenance envelope, commitment algorithm, and policy function;
- root-ingress evidence with no production channel initially verified;
- exact normal-ingest and direct inter-model transformation bindings;
- transformer-aware monotone integrity propagation;
- unit/Chroma/export/reconstruction parity;
- CG-1 immutable-manifest and cold-validation continuity;
- unchanged CG-2 serving with provenance pass-through;
- per-assertion retrieval visibility;
- legacy-as-unknown behavior;
- exact-dedupe protection for independent cross-provenance assertions;
- property, round-trip, negative, and laundering tests.

### Explicitly out of scope

- production data migration or backfill;
- semantic-dedupe adjudication implementation (Stage 2);
- ranking, recency, or temporal-conflict changes;
- authenticated identity, automatic elevation, or downstream action gates;
- Shadow/R2b/CG-2 operational work;
- renaming existing `source_trust` code;
- factual correctness or poisoning classifiers.

## Preconditions

Before implementation begins:

1. Kiro reviews the architecture and this decomposition at one exact SHA.
2. Copilot performs the targeted safety/isolation and continuity audit at that
   same SHA.
3. Ryan resolves findings and records an architecture lock.
4. Ryan issues a separate Execute grant naming the implementation branch/scope.
5. Cursor rebases from the then-current `origin/main` and re-traces any changed
   ingest, dedupe, CG-1, CG-2, export, or retrieval boundary.

## Ordered work packages

### P1 — Canonical policy and representation

Create one deep module that owns:

- schema/versioned envelope types and validation;
- canonical JSON and `provenance_commitment` calculation;
- root mapping from monitor-controlled ingress evidence;
- `untrusted < agent < trusted` meet;
- transformer caps and ancestry-completeness rules;
- effective-integrity recomputation and cache-mismatch degradation;
- legacy/malformed/unknown-policy fallback to untrusted.

No adapter, caller, Chroma field, source path, role, confidence, or ranking code
may independently compute integrity. The empty-input and caller-self-upgrade
negative tests are P1 gates.

Likely surfaces after re-trace:

- new internal provenance policy/serialization module under `src/convmem/`;
- focused policy and canonicalization tests under `tests/`.

### P2 — Transformation-boundary binding and durable continuity

For normal ingest, bind adapter-stable source records, raw-record hashes, each
exact rendered/truncated view, ordering/chunk/selection parameters, and the full
provider payload. Bind both ingest rendering and the additional distillation
truncation. Record requested/resolved provider/model, fallback, generation
parameters, fixed recipe/config hash, response hash, producer, and transformer.

For direct inter-model indexing, treat `source_type` and `author_model` as
claimed classification only. Direct packaging may preserve only a tested
content-preservation contract; a caller cannot mark itself verified or trusted.

Propagate the canonical envelope and commitment through normalized units,
Chroma scalar-safe metadata, export, and canonical reconstruction. Add fixtures
for malformed fields, old rows, unknown policy versions, and old consumers.

Likely surfaces after re-trace:

- `src/convmem/ingest.py`
- `src/convmem/distill.py`
- `src/convmem/llm.py`
- relevant adapters under `src/convmem/adapters/`
- `src/convmem/inter_model_index.py`
- `eval_corpus/reconstruct.py`
- export/reingest tests and fixtures

### P3 — Assertion-preserving exact dedupe

Separate assertion identity from content/equivalence identity. Exact duplicates
with independent or different provenance cannot cause the incoming assertion's
provenance to disappear and cannot elevate or downgrade the existing assertion.
Storage optimization may relate assertions or share immutable content bytes,
but retrieval/audit must be able to recover each provenance assertion.

Do not implement automatic semantic cross-provenance collapse. Existing semantic
approval must fail closed or require explicit human adjudication when provenance
differs. A later Stage 2 design decides durable equivalence/tombstone semantics.

Likely surfaces after re-trace:

- `src/convmem/ingest_dedupe.py`
- `src/convmem/refine.py`
- assertion/equivalence persistence and lifecycle tests

### P4 — CG-1, CG-2, and retrieval continuity

Make the provenance commitment a required immutable attribute for new-schema
CG-1 candidates and manifest rows. Include it in candidate/bundle identity as
specified by the locked architecture. Cold validation must reject omission,
mutation, unknown schema, or envelope/commitment mismatch rather than comparing
only keys that are present.

Carry the assertion and commitment unchanged through CG-2 serving. The
request-frozen authority vector remains the sole serving-authority mechanism;
CG-2 does not recompute provenance or aggregate trust.

Expose per-assertion provenance/effective integrity at retrieval/MCP boundaries.
Keep relevance, recency, and `source_trust_boost` behavior bit-for-bit unchanged
unless a compatibility shim is strictly necessary. Any derived synthesis is out
of this slice unless it binds all selected parents and is capped at agent.

Likely surfaces after re-trace:

- `src/convmem/file_generation_contract.py`
- `src/convmem/file_generation_builder.py`
- `src/convmem/file_generation_store.py`
- `src/convmem/serving_authority.py`
- `src/convmem/serving_index_repository.py`
- `src/convmem/query.py`, `src/convmem/evidence.py`, and response schemas

### P5 — Verification packet and compatibility closure

Run the locked tests in `VERIFY-dependability-provenance.md`. Produce evidence
for the exact implementation tip, including focused and full regression runs,
diff checks, no-live-mutation proof, serialized fixtures, and negative controls.

Kiro reviews the implementation design/result. Copilot performs the targeted
safety/isolation audit because this changes security-relevant data continuity.
Ryan alone decides merge and any later migration/activation grant.

## Required Stage 1 properties

### Root authority

1. Empty input cannot produce `agent` or `trusted`.
2. Text or caller fields claiming `verified`, `trusted`, `trusted_tool`, or
   `user` cannot self-upgrade.
3. No current production adapter produces a verified root.
4. Legacy/malformed/unknown-policy records are untrusted for security decisions.

### Transformation monotonicity

For all three lattice values and supported transformer classes:

```text
I(output) <= meet(I(all bound inputs), transformer_cap)
```

Required cases include trusted→lossless packaging, trusted→LLM, agent→LLM,
trusted+agent, trusted+untrusted, unknown input, missing parent, provider fallback,
repeat summarization, and content that embeds fake provenance fields.

### Exact binding

1. Changing any rendered/truncated byte changes its view or payload commitment.
2. Changing message order, selection, chunk budget, prompt, model, provider,
   temperature, fallback resolution, or recipe version changes the proper hash.
3. Overlapping chunks bind the same source record locator but distinct consumed
   views when their projections differ.
4. Unseen truncated raw text is not falsely represented as model input.

### Continuity

1. Unit → Chroma → export → reconstruction is semantically lossless.
2. Flat diagnostics cannot override the canonical envelope.
3. CG-1 cold validation rejects missing or altered commitments.
4. CG-2 returns the same assertion/commitment selected by serving authority.
5. Retrieval preserves each assertion's provenance independently.

### Dedupe

1. Cross-provenance exact duplicates remain independently auditable.
2. A low-integrity duplicate cannot downgrade a trusted assertion.
3. A high-integrity duplicate cannot elevate an untrusted assertion.
4. Semantic cross-provenance tombstoning cannot occur without explicit human
   adjudication and retained audit evidence.

## Fault-focused test cases

- self-summarization laundering: untrusted input → LLM summary → untrusted;
- trusted-tool echo: trusted code touching untrusted data → untrusted;
- manufactured corroboration: two summaries of one root remain one origin;
- partial-parent laundering: omitted contributor → untrusted;
- recapture loop: untrusted retrieval → chat → ingest → distill never rises;
- provider fallback drift: resolved recipe identity changes and remains bounded;
- commitment split brain: canonical envelope wins and inconsistency degrades;
- omission attack: missing new-schema commitment fails CG-1 cold validation;
- duplicate downgrade/elevation attempts preserve independent assertions;
- old consumer/reconstructor cannot silently label dropped provenance trusted.

## Stop conditions

Stop and return to architecture review if:

- complete provider payload cannot be deterministically canonicalized without
  retaining secrets;
- a supported derivation cannot bind all dynamic inputs;
- CG-1 identity changes require an in-place live migration;
- CG-2 would need to recompute integrity rather than pass through evidence;
- exact-dedupe preservation requires a public schema or retention decision not
  settled by the architecture;
- an existing consumer cannot carry the commitment without silent data loss;
- implementation would alter ranking, temporal behavior, live data, activation,
  or downstream action policy.

## Review and delivery path

```text
Codex planning package
  → Kiro architecture/design verdict (required)
  → Copilot targeted safety/isolation verdict
  → Ryan architecture lock + separate Execute grant
  → Cursor implementation
  → focused VERIFY + full regression
  → Kiro implementation design review
  → Copilot targeted final audit
  → Ryan merge decision
```

The reviewers must record `git rev-parse HEAD`; no committed document attempts to
contain its own review-tip SHA. Different revisions are not conflicting verdicts.
