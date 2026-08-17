# Architecture — Dependability and Provenance Integrity

```text
Planning status: REVIEW REQUIRED — NOT AUTHORIZED FOR IMPLEMENTATION
Arc owner:       Ryan
Planning lane:   Codex Sol-High (explicit exception for this package)
Review lanes:    Kiro design review; targeted Copilot safety/isolation audit
Baseline:        origin/main @ 2f427fcfb8818dd665310bae7e8cd5ffa066bdcc
```

## 1. Decision and product consequence

ConvMem will treat provenance as evidence that travels with each independent
assertion, not as a caller-supplied trust label. For every representation it
creates, ConvMem will conservatively compute an integrity **upper bound** from
all inputs actually presented to the transformation and from the authorized
transformer's semantic cap. The system will preserve that evidence through
ingest, Chroma, export, reconstruction, CG-1 generations, CG-2 serving, and
retrieval.

This closes a concrete laundering path: today an external or mixed-origin
message can be summarized into a `knowledge_unit` whose durable form no longer
records the input origin. It does **not** prove the statement true, authenticate
current agent identities, stop downstream agents from acting, or establish the
end-to-end non-malleable authority claimed by TMA-NM under stronger assumptions.

## 2. Scope and assurance boundary

This arc owns:

- root-origin evidence and its assurance state;
- complete transformation-boundary input binding;
- conservative derivation integrity;
- independent assertion identity across exact and semantic equivalence;
- canonical provenance representation and commitment continuity;
- per-assertion provenance visibility at retrieval and serving boundaries;
- tests and evidence for those properties.

It coordinates with, but does not absorb:

- **temporal validity** — whether a fact was valid at a requested time;
- **retrieval priority** — relevance, recency, and the existing
  `source_trust_boost` ranking heuristic;
- **serving authority** — which CG-2 owner/generation may answer a request;
- **factual truth** — whether the assertion is correct;
- **downstream action authority** — whether an agent, tool, git operation, or
  other consumer may act on retrieved material.

Those dimensions may be correlated, but none implies another.

### Retained T1–T5 Trust Arc sequence

The wider Trust Arc remains a five-part planning sequence. This package
strengthens T3 provenance; it does not delete the surrounding dependability
work or authorize any of it:

P0, the CI Merge Gate, is prerequisite infrastructure outside Full Fathom Five
and is not counted as one of its five arcs. The canonical parent hierarchy is
FF1/T1 Trust Baseline → FF2/T2 Existing Evidence + Failure-Gap Matrix →
FF3/T3 Compatibility & Provenance → FF4/T4 Security, Privacy & Egress →
FF5/T5 Operational Envelope.

| Track | Planning responsibility | Boundary |
|---|---|---|
| FF1 / T1 | Trust baseline, claim ownership, severity, and declared degraded states | Architecture evidence only; no runtime gate change |
| FF2 / T2 | Inventory existing CG-1/CG-2, backup, restore, projection, and provider evidence; classify gaps | Add a new check only for a distinct failure window or owner |
| FF3 / T3 | Durable-format compatibility and provenance contract, including acknowledgement and migration semantics | No live migration, corpus rewrite, or activation |
| FF4 / T4 | Security/lifecycle and egress planning, including poisoning and provider-failure evidence | No cloud-policy or runtime change in this edit |
| FF5 / T5 | Endurance, resource, maintenance, and operational-envelope planning | Measurements and grants remain later work |

The sequence is a planning map, not five simultaneous implementation streams.
Existing standing checks and accepted evidence are reused where they cover the
claim; a new ceremony, gate, or review is justified only by a distinct failure
window, owner, or oracle.

T1 Trust Baseline completion and T2 existing-proof inventory/gap analysis are
mandatory completed predecessors to any T3/provenance implementation grant.
Stage 1A/1B is a T3 child slice and cannot receive an implementation grant
until T1's architecture output and T2's evidence/gap output are complete and
accepted; T4 and T5 remain parent-sequence work after T3.

The parent roadmap is frozen at this hierarchy. **Full Fathom Five parent
structure frozen; further findings are review findings, not automatic scope
additions.** A later Kiro or Copilot finding may create a bounded review issue,
but it does not silently add a new parent arc, alter the order, or move the
review target without an explicit planning decision.

### Acknowledgement and migration semantics

For the T1 claim about acknowledged data, an acknowledgement is a success from
the named authoritative durable-write boundary. A provider response, projection
visibility, index upsert, client receipt, or retrieval result is not by itself a
durable acknowledgement. If the authoritative boundary cannot prove the write,
the result is failure or unknown rather than an acknowledged success. Strong
durable acknowledgement is additionally conditional on a declared supported
persistence profile covering the filesystem, mount, storage, and database
semantics relied on by that boundary. An unknown or unsupported profile, or
unproven persistence semantics, returns failure or unknown and cannot emit the
strong durable claim. Power-loss and profile campaigns remain later T5 work.

T3 defines a migration contract, not a migration operation: a schema mismatch
does not grant permission to rewrite data. The contract must name the supported
N-1 window, reject unknown future versions, provide a read-only/dry-run path,
require a current backup before any authorized write, and use atomic replacement
with rollback and old-state fixtures. Every authorized migration must also
include an explicit semantic mapping from the old durable representation to the
new representation, plus old-state fixture evidence demonstrating preservation
of durable meaning, including envelope, assertion ID, commitment, and parent-edge
semantics. Any unmapped or intentionally changed meaning must fail closed as
rejected, quarantined, or `needs migration`; procedural migration safety does not
substitute for semantic-preservation evidence. Legacy data remains readable only
under the conservative untrusted policy until Ryan grants a separate migration.
The migration semantic inventory must enumerate every durable meaning-bearing
category, including field presence/default behavior, value and enum domains,
assertion IDs, commitments, parent edges, policy/recipe references, and
extensible or unknown fields where applicable. Fixture or property evidence must
cover every declared category; representative fixtures alone do not establish a
total mapping.

### Authoritative assertion store and recovery boundary

The authoritative provenance boundary is a new planned registry rooted at
`CONVMEM_DATA_ROOT/provenance/`. P1 must lock the exact on-disk encoding and
writer/reader module, but it may not place the authority outside the explicit
complete-data root or leave it implicit in a projection. The registry must
contain, or deterministically address:

- every canonical assertion envelope, assertion ID, and commitment;
- every immutable parent-ID/parent-commitment edge;
- root-origin evidence and assertion lifecycle state;
- every historical `provenance_policy_version` used by a stored envelope; and
- every transformer identity/version/recipe required to recompute a derivation.

The registry's directory-level manifest is authoritative for completeness. It
names the schema, store generation, required files/objects, counts, canonical
digests, policy/recipe history digests, and the complete assertion graph. The
exact file layout remains a P1 implementation choice, but a flat JSONL export
or a Chroma collection alone is not an assertion authority. Existing
`knowledge_units.jsonl` is an export/rebuild surface; Chroma is a retrieval
projection. Neither may mint, preserve, or elevate identity when the registry
is absent.

The registry is intentionally inside the complete-data Restic scope. A legacy
`convmem-chroma` snapshot or a Chroma-only restore is not a provenance-store
backup and cannot authorize identity-preserving recovery. A complete-data-v2
snapshot must include the registry, its manifest, policy/recipe history, the
JSONL export, and the Chroma projection in one verifiable data-root snapshot.

Restoring the registry is a distinct Ryan-gated bulk recovery operation. It
restores and verifies the whole registry directory and its graph in a scratch
target, then publishes one atomically selected recovered store generation. It
is not ordinary item-by-item `convmem add`, JSONL re-import, Chroma rebuild, or
dedupe processing. Those operations may consume a recovered registry, but may
not identity-preserve a caller-supplied ID without the verified store.

Before recovered assertions become publishable, recovery must verify the
directory manifest and every required file/object hash, uniqueness of IDs,
ID/commitment agreement, recursive parent resolution, historical policy and
recipe availability, and exact registry↔JSONL↔Chroma identity/commitment
agreement. The recovered target must be complete for the declared store
generation; partial snapshots, extra unclassified state, truncated files, and
restore/rebuild mismatches remain quarantined.

If the registry is missing or incomplete, do not silently rewrite a valid live
corpus as globally untrusted and do not elevate recovered Chroma/JSONL rows
from caller-supplied IDs. Leave the live corpus and authority unchanged; keep
the recovered projection quarantined or expose it only as explicitly
untrusted evidence with a `provenance_store_unavailable` degraded state. An
individual missing parent still produces R8's per-assertion `untrusted` result,
but that result is not a substitute for completing the bulk store recovery.

The future implementation must extend the existing complete-data-v2 restore
contract: `complete_data_restore.py`'s closed `STATE_SPECS` and
`writer_census_for_root()` must name `provenance/` as a required Tier-1 durable
path, and `docs/RECOVER.md` must classify a valid registry as part of the
required durable recovery set. The registry manifest is not a replacement for
`.convmem-backup-evidence.json`: the former is authoritative store integrity
and graph evidence, while the latter remains backup-capture evidence only. A
separate provenance validator is therefore required, with the restore
preflight invoking it after top-level path classification and before recovered
assertion publication.

## 3. Repository-grounded problem statement

The following are current behaviors on the baseline revision, not hypothetical
risks:

| Boundary | Current behavior | Dependability fault |
|---|---|---|
| Normal ingest | `render_chunk()` budgets and truncates each message before sending one rendered string to summarization/distillation (`ingest.py`). | A source-file or full-message hash does not bind the bytes the model actually saw. Mixed contributors collapse into one artifact-level `source_type`. |
| Distillation | `distill()` truncates again and sends a fixed prompt plus model/provider parameters; `normalize_unit()` omits provenance (`distill.py`, `llm.py`). | An LLM-created representation can look like a fresh neutral unit; provider fallback or recipe drift is not committed. |
| Direct inter-model ingest | `source_type` and `author_model` are ordinary caller arguments; `source_type` reaches Chroma metadata but not the exported unit (`inter_model_index.py`). | Claimed origin can be mistaken for verified origin, and reconstruction loses even the claim. |
| Exact dedupe | Content equality suppresses the incoming unit (`ingest_dedupe.py`). | An independent assertion and its provenance can disappear. A low-trust copy can affect a trusted assertion's lifecycle. |
| Semantic dedupe | Canonical choice is confidence/newness/id; approval tombstones one unit (`refine.py`). | Cross-provenance collapse has no trust rule and destroys assertion evidence. |
| Reconstruction | Canonical metadata allowlist omits `source_type` and provenance (`eval_corpus/reconstruct.py`). | Export/rebuild cannot reproduce provenance semantics. |
| Retrieval | Existing `source_trust_tier()` ranks by type/path and ledger status (`evidence.py`, `query.py`). | A ranking preference can be misread as authenticated provenance. |
| R2b and writer attestation | R2b binds an authorized capture package; writer attestation records process facts. | Package/process integrity does not authenticate the semantic origin of content. |
| CG-1 | Candidate bundles and manifests are content-addressed; cold validation checks selected immutable keys (`file_generation_contract.py`, `file_generation_builder.py`, `file_generation_store.py`). | A missing provenance key can pass if the validator only compares keys that are present. Durability can preserve poison perfectly. |
| CG-2 | A request-frozen authority vector selects the serving owner/generation (`serving_authority.py`, `serving_index_repository.py`). | Serving authority says which generation may answer, not whether an assertion's provenance is strong. |

The current adapter role (`user`/`assistant`), `source_type`, filesystem path, and
`author_model` are classification claims. No inspected ingestion boundary
authenticates the human or model principal that produced the record.

## 4. Vocabulary and integrity lattice

### 4.1 Separate questions

| Term | Question answered |
|---|---|
| Root origin | Who or what supplied a root information item? |
| Origin assurance | Was that origin established by an authenticated channel, merely claimed, or unknown? |
| Producer | What created the current representation? |
| Transformer | What semantic operation and implementation created it? |
| Input binding | Which exact dynamic bytes were presented at that supported boundary? |
| Ancestry completeness | Were all such dynamic inputs bound and was the fixed recipe identified? |
| Effective integrity | What exact conservative result does the versioned policy compute for this representation? |
| Provenance commitment | What canonical digest binds the authoritative provenance envelope? |

`verified` means the channel/origin was verified. It never means the information
is factually true.

### 4.2 Lattice

```text
untrusted < agent < trusted
```

The ordering is authority for security decisions, not confidence or relevance.
There is no empty-input identity that mints authority.

### 4.3 Initial verified-channel inventory

**No current production channel is verified.** Until an authenticated origin
boundary is separately designed and evidenced, use this inventory:

| Ingress evidence | Assurance | Root integrity for security decisions |
|---|---|---|
| Transcript `role=user` or `role=assistant` | claimed/unknown | untrusted |
| Agent/inter-model session artifact | claimed | untrusted |
| Inter-model `author_model` or `source_type` | claimed | untrusted |
| Filesystem path or filename convention | classification only | untrusted |
| Legacy record without the envelope | unknown | untrusted |

Synthetic tests may create verified roots. Production code may not infer
verification from content, role, process identity, source path, or caller input.

## 5. Normative integrity rules

### R1 — Root integrity is not derivation integrity

A root receives integrity only from monitor-controlled ingress policy applied to
authenticated channel evidence. Empty inputs, text that says `origin=trusted`,
caller claims, and an executing process's self-description never mint `agent` or
`trusted` authority.

### R2 — Effective-integrity computation

For every derived unit:

```text
I(output) = meet(
    I(all completely bound dynamic inputs),
    cap(authorized transformer/producer)
)
```

This equality defines the effective-integrity policy result; it is not merely a
ceiling that another component may reinterpret upward. If ancestry is `partial`
or `unknown`, the policy result is `untrusted`. An empty input set cannot produce
`agent` or `trusted`. `agent` is a monitor-computed result of an authorized agent
transformation, never a caller-selectable root label.

Examples:

| Inputs and operation | Effective-integrity result |
|---|---|
| Verified trusted root through tested lossless packaging | trusted |
| Verified trusted root through LLM summarization | agent |
| Trusted + trusted through LLM distillation | agent |
| Trusted + agent through LLM distillation | agent |
| Any contributing untrusted input | untrusted |
| Any omitted or unknown contributor | untrusted |

### R3 — The transformer participates

Deterministic code is not automatically trust-preserving. A transformer has a
versioned cap and may preserve input integrity only when it has a narrow,
tested preservation contract. Initially:

| Transformer class | Initial cap |
|---|---|
| Tested byte/content-preserving packaging | trusted |
| LLM summarize/distill/rewrite/classify | agent |
| Opaque tool with fully bound inputs | policy cap, never above least input |
| Selection/extraction without a preservation contract | agent or untrusted, per policy |
| Missing recipe, fallback identity, or contributor | untrusted |

The trusted-preservation and transformer-cap table is a versioned allowlist
owned by the provenance policy module. A transformer may receive the `trusted`
cap only when its exact class, implementation identity/version, recipe, and
tested preservation contract are present in that allowlist. Caller metadata,
configuration alone, or a conventionally engineered process cannot add an
entry or obtain a trusted cap. Unknown, revoked, or unavailable allowlist
history is `untrusted`.

### R4 — Completeness is boundary completeness

`ancestry_completeness=complete` means:

> Every dynamic byte actually presented at the supported transformation boundary
> is bound, and the fixed recipe responsible for the output is identified.

It does not claim universal causal knowledge of model weights, training data, or
all human influences. Model/provider identity belongs to transformer identity;
the fixed prompt and configuration belong to the recipe.

### R5 — Bind the actual provider request

Every supported generative derivation binds:

- adapter-stable source identity and record locator (native event/message ID
  preferred; otherwise adapter-versioned ordinal/offset);
- hash of the full raw source record;
- hash of each exact rendered/truncated view consumed;
- selection, chunking, ordering, and truncation parameters;
- canonical hash of the **complete provider payload**, including system/fixed
  prompt and every dynamic text/tool/retrieval input sent;
- provider, requested and resolved model, temperature and relevant generation
  parameters, fallback decision, transformer implementation/version;
- fixed recipe/configuration hash and binding schema version;
- response hash and output locator.

Secrets and transport credentials are excluded. Their exclusion must not omit
any corpus-bearing or semantics-bearing request bytes.

### R6 — Independent assertions survive equivalence

Derivation takes the least-trusted contributing input. Equivalence does not.
Exact or semantic duplicates remain independent assertions with independent
provenance. A relation may say they are equivalent; it may not manufacture one
aggregate trusted assertion.

Cross-provenance tombstoning requires explicit human adjudication and is outside
Stage 1. Even after adjudication, audit evidence for both assertions remains.

### R7 — Assertion identity is independent from content

Every assertion has an immutable, opaque `assertion_id` minted by the central
ConvMem monitor. The initial schema uses a content-independent UUIDv4 in
canonical lowercase text: the encoded identifier is 128 bits, but UUIDv4 has
122 random payload bits because version and variant fields are fixed. The
monitor generates and atomically reserves it in the authoritative assertion
store before publication;
it retries a collision rather than reusing an existing identity. The ID is not
derived from content, path, offset, producer, timestamp, or an LLM response.
Callers, adapters, LLMs, dedupe code, exports, and consumers may carry or
reference an ID but may not mint, rewrite, or recycle one. A new root or derived
representation receives a new monitor-minted ID.

The identity contract is:

- `assertion_id` is part of the authoritative envelope and therefore the
  `provenance_commitment` input;
- export → reconstruction → re-import preserves the same ID only as an
  idempotent replay when the canonical envelope matches the commitment exactly,
  recursive parent verification succeeds, and any existing row under that ID
  has the same canonical envelope/commitment;
- a valid idempotent replay creates no new assertion, origin, corroborator, or
  authority evidence;
- identical content alone never establishes identity;
- identical content without a valid existing ID/commitment pair is a new,
  independent assertion with its own ID and provenance;
- a supplied existing ID with a missing, malformed, or mismatching commitment is
  rejected for identity-preserving import and may not overwrite, alias, or
  mutate the existing assertion. If policy permits retaining its content as
  evidence, the monitor mints a new assertion ID and records the attempted
  replay/mismatch as untrusted provenance; it never adopts the supplied ID;
- every non-root `input_binding` has a `parent_assertion_id` and the parent's
  expected commitment. That pair is an immutable edge to one exact parent
  assertion and may not be rebound to equivalent content; it must match the
  resolved parent envelope.

Equivalence and content hashes may support search and dedupe, but they are not
identity. This prevents same-content injection from downgrading, elevating, or
silently replacing an established assertion.

### R8 — Recursive verification fails closed

Effective integrity is recomputed only after recursively verifying the complete
assertion graph. Verification resolves the assertion envelope, commitment,
historical `provenance_policy_version` and its committed semantic-content
digest, transformer identity/version/recipe and its committed semantic-content
digest, every required input binding, and every parent envelope/commitment. It
rejects any policy or recipe identifier that resolves to bytes different from
the committed digest. It tracks a visited-ID set and rejects cycles.

If any parent, ancestor, historical policy or recipe, required binding, or
identity/commitment pair cannot be resolved and verified, the result is
`untrusted`; no favorable child fields or cached tier may be used as a fallback.
The same result applies to a cycle, duplicate ID with divergent envelope, or a
child whose parent commitment does not match the resolved parent. A child with a
valid-looking envelope and commitment but a missing ancestor is therefore not
valid. Recursive failure is observable as a bounded validation/degraded state,
not silently treated as a new root.

Recursive verification has a per-operation node, depth, and byte budget and
memoizes verified subgraphs by `(assertion_id, provenance_commitment,
provenance_policy_version)` for the duration of that operation. Memoization is
an optimization only: it is invalidated when the backing store or policy
snapshot changes and never overrides a missing or mismatching record. Budget
exhaustion, unavailable history, or cache inconsistency returns `untrusted` and
an observable degraded result. P1 must lock these bounds before P3 exposes
recursive verification on broad retrieval paths.

### R8.1 — Store recovery is separate from item import

The assertion registry, policy/recipe history, and directory manifest are one
recoverable authority set. A valid envelope restored without that set is not a
valid identity-preserving import. Store recovery must be performed as a
snapshot/directory-level operation under a separate Ryan grant; item-by-item
JSONL or Chroma reconstruction may populate only a quarantined staging target
until the registry manifest and all cross-surface checks pass. Missing store,
partial snapshot, stale history, and restore/rebuild mismatch are explicit
fail-closed recovery states, not reasons to mint trust from IDs in a payload.

### R8.2 — Recovery binds one selected generation; rollback is explicit

Every recovery selects one complete-data-v2 snapshot/generation before reading
its components, identified by an immutable generation ID and manifest
commitment. The registry, policy/recipe history, JSONL export, and Chroma
projection must all verify against that same selected generation. Individually
valid components from different generations are an impossible authority state
and remain quarantined. A valid older generation is a rollback candidate only;
it is never auto-selected because it is restorable. Publishing it requires a
separate Ryan rollback grant naming the selected generation, the current live
generation, and the reason. That grant is ConvMem governance, not a TUF
requirement. Rollback publication additionally requires trusted continuity
evidence that is not derived solely from the candidate generation or the
rollbackable authority set being restored. That evidence must bind the previous
externally accepted generation and manifest commitment to the authorized target
generation and manifest commitment, the reason, and the fresh rollback-grant
identity. Without that evidence, an internally valid older generation remains
`BLOCKED`/quarantined and cannot become authoritative.

A provenance generation may be sealed and published as complete only when all
manifest-bound authority components were captured from one consistent logical source state;
concurrent mutation during sealing must cause retry, rejection, or quarantine
unless an immutable/staged generation or equivalent consistency proof establishes
that all components belong to the same logical state. This is
a capture/sealing condition, distinct from restore-side selected-generation
binding; it does not prescribe the implementation mechanism.

Recovery publication is also crash-closed: interruption at every durable write,
rename, manifest, pointer, and publication boundary must leave either the prior
complete authority generation selected or one complete, verified replacement.
It must never expose a mixed, missing, or partially selected authority set.

### R9 — Legacy is conservative

Missing provenance maps to `unknown`/`untrusted` for security decisions. No
backfill may infer upward from path, prose, role, `author_model`, `source_type`,
confidence, timestamp, current ranking boost, or survival in a durable generation.

### R10 — Continuity is mandatory; display is supplementary

Canonical representation, propagation, export, reconstruction, and commitment
continuity are mandatory integrity claims. Failure or omission degrades the
assertion to `untrusted` or rejects it at a boundary whose contract is fail-closed.
Only supplementary human-readable display diagnostics may be advisory. A missing
display badge can never make missing envelope/commitment continuity acceptable.

## 6. Canonical provenance envelope and commitment

The authoritative envelope is conceptually:

```text
schema_version
binding_version
assertion_id
root_bindings[]:
  source_identity
  record_locator
  raw_record_sha256
  input_view_sha256
  origin_class
  origin_assurance
  origin_evidence:
    channel_class
    channel_locator
    channel_evidence_sha256
input_bindings[]:
  parent_assertion_id
  parent_provenance_commitment
  exact_input_view_sha256
producer_class
producer_assurance
derivation_kind
transformer_class
transformer_identity
transformer_version
transformer_recipe_id
transformer_recipe_sha256
selection_parameters
provider_payload_sha256
recipe_config_sha256
ancestry_completeness: complete | partial | unknown
provenance_policy_version
provenance_policy_sha256
effective_integrity  # derived/cache only; never authoritative input
```

### 6.1 Allowed producer values and authority semantics

`producer_class` is a closed enum:

```text
user | trusted_tool | agent | external | unknown
```

It identifies who or what directly created the current representation, not who
originally supplied every fact in it. `user` means a representation directly
authored through a user channel; `trusted_tool` means a conventionally engineered
producer selected by policy; `agent` means an LLM/agent-created representation;
`external` means a third-party or otherwise untrusted producer; and `unknown`
means the producer cannot be classified from bound evidence.

`producer_assurance` is also a closed enum:

```text
verified | claimed | unknown
```

`verified` means an authenticated producer/channel boundary supplied the class;
it never means the content is true. `claimed` means the caller or artifact names
the producer without authentication. `unknown` means no usable producer evidence
exists. No current caller may set its own assurance to `verified`; unknown enum
values, caller-supplied verification, and absent producer evidence fail validation
or conservatively become `unknown`/`untrusted` under the versioned policy. The
initial production inventory therefore emits no `verified` producer assurance;
that value is reserved for synthetic tests and a future authenticated boundary.

Neither field grants authority by itself. Root integrity still comes only from
root-origin evidence. Derived integrity still equals the meet of all completely
bound inputs and the authorized transformer/producer cap. In particular:

- `producer_class=agent` cannot mint an `agent` root; an agent cap applies only
  when trusted ConvMem code records an authorized derivation with non-empty,
  completely bound inputs;
- `producer_class=trusted_tool` does not preserve trusted integrity unless the
  exact transformer/recipe has a tested preservation contract;
- `producer_assurance=verified` authenticates identity/channel only and cannot
  override an untrusted input, lossy/generative cap, incomplete ancestry, or
  failed commitment;
- `claimed` and `unknown` producer evidence never elevate effective integrity.

`effective_integrity` is a derived/cache value computed by one policy function
only after R8 recursive verification succeeds.
It is never authoritative caller metadata. Consumers recompute it and degrade to
`untrusted` on cache mismatch, unknown policy, malformed envelope, or commitment
failure. Policy-version and transformer-recipe identifiers are names only; their
semantic bytes are bound by the corresponding content digests above. An
authoritative identifier resolving to different semantic bytes is a continuity
failure and must be rejected or degraded to `untrusted`.

`provenance_commitment` is SHA-256 over versioned canonical JSON of the
authoritative envelope, excluding the commitment itself and derived/cache fields.
Canonical field order, Unicode/number encoding, list order, and null/omission
semantics are part of the schema version. P1 must publish one normative,
versioned ConvMem canonicalization profile and serializer implementation, with
golden vectors covering Unicode, numbers, escaping, lists, nulls, and field
ordering. The vectors are rerun when the serializer library changes; the plan
makes no cross-implementation portability claim unless a later scope decision
explicitly adds one. Hash equality proves byte-level commitment continuity, not
truth.

The commitment and envelope must survive without semantic loss across:

```text
adapter/source records
  → rendered provider payload
  → normalized knowledge unit
  → Chroma flat metadata
  → JSONL export
  → canonical reconstruction
  → CG-1 candidate and immutable manifest
  → CG-1 cold validation
  → CG-2 serving row
  → retrieval result / MCP consumer
```

Chroma's scalar metadata limitation may require a canonical serialized envelope
plus scalar diagnostic fields. The serialized envelope is authoritative; scalar
copies cannot override it. Oversized or malformed metadata fails closed for
trusted use and remains retrievable only as explicitly untrusted evidence.

## 7. CG-1, CG-2, retrieval, and temporal integration

### CG-1 immutable generations

CG-1 must include the provenance commitment in candidate identity and immutable
manifest rows. Cold validation must require the field for new-schema rows and
fail on omission, alteration, unknown schema, or envelope/commitment mismatch.
Comparing only keys that happen to exist is insufficient. Generation durability
and provenance integrity remain separate assurance claims.

### CG-2 serving authority

CG-2 continues to choose a request-frozen serving owner/generation. It must carry
the committed assertion unchanged and must not recompute, aggregate, elevate, or
discard provenance. A valid pointer/fence/manifest qualifies serving authority;
it does not qualify assertion integrity.

### Retrieval and assembly

Every retrieval item exposes its own assertion ID, envelope/commitment,
recomputed integrity, and assurance limitations. Existing relevance, recency,
and source-priority scoring remain unchanged in Stage 1 and must not contribute
to integrity.

If a later answer assembler creates a new synthesis, it is a new agent-capped
derivation bound to the exact selected assertions and prompt/provider payload.
The answer may not inherit the maximum integrity among results or present one
aggregate “trusted sources” label.

### Temporal validity

Temporal policy is a separate arc/slice. Its initial buckets are:

1. explicit total-order version metadata — deterministic current-value policy;
2. valid-time and transaction-time metadata — bitemporal policy;
3. historical/as-of query — preserve period-specific assertions;
4. structured conflict without a total order — surface conflict;
5. no reliable version metadata — do not force a deterministic winner.

Embedding similarity, recency boost, provenance integrity, or serving authority
cannot substitute for temporal evidence.

## 8. Assurance case

The top claim is deliberately bounded:

> ConvMem conservatively preserves and propagates provenance integrity through
> the memory transformations, immutable generations, serving paths, and
> retrieval representations it controls, conditional on correctly classified
> ingress evidence and complete supported-boundary input binding.

| Claim | Argument | Required evidence family |
|---|---|---|
| C1. Roots cannot self-upgrade. | Only monitor policy maps authenticated channel evidence; current production inventory has no verified channel. | Code inspection, negative/property tests, ingress inventory review. |
| C2. Derivations are monotone. | One policy sets integrity equal to the meet of every bound input and transformer cap; incomplete ancestry is untrusted. | Exhaustive lattice tests, metamorphic laundering tests, policy-version fixtures. |
| C3. Provenance is continuous. | One canonical envelope/commitment crosses unit, Chroma, export, reconstruction, CG-1, CG-2, and retrieval. | Round-trip fixtures, cold tamper/omission tests, old-consumer compatibility tests. |
| C4. Equivalence cannot erase authority evidence. | Assertions and equivalence relations have separate identity; cross-provenance collapse is gated. | Exact/semantic dedupe negative controls and lifecycle traces. |
| C4a. Assertion identity is stable. | Only the monitor mints and atomically reserves IDs; a valid ID/commitment pair is idempotent replay with no new corroboration, while same content without that pair creates a new assertion. | Minting/collision, replay/reconstruction, same-content independence, and mismatch tests. |
| C4b. Recursive recomputation is fail-closed. | Every parent, ancestor, policy, recipe, binding, and cycle is verified before integrity is computed. | Missing-ancestor, cycle, parent-mismatch, and unavailable-history negative controls. |
| C5. Retrieval does not invent aggregate trust. | Integrity remains per assertion; synthesis is a new agent derivation. | Retrieval/MCP contract tests and assembly parent-completeness tests. |
| C6. Existing authority controls stay orthogonal. | CG-1 durability, CG-2 serving, R2b capture integrity, and ranking each keep their current owner and claim. | Boundary review against their architecture/VERIFY artifacts. |
| C7. Limits are visible. | Unknown legacy and unauthenticated channels stay untrusted; no factual/action claim is made. | User-visible contract tests, docs review, targeted safety audit. |
| C8. Integrity continuity is mandatory. | Envelope/commitment continuity is fail-closed or degrades to untrusted; only supplementary display diagnostics are advisory. | Required-field omission tests, round trips, consumer compatibility tests. |

CSIRO's structured safety-case taxonomy guides claim/argument/evidence families.
CoDefeater motivates adversarial defeater discovery, but all generated defeaters
require human adjudication. Formal or machine-checked results from another system
are evidence hypotheses, not proof of ConvMem.

## 9. Defeater register

These defeaters remain open until the corresponding evidence passes:

| ID | Defeater |
|---|---|
| D1 | Existing `source_trust_boost` is retrieval priority, not provenance integrity. |
| D2 | A low-trust duplicate can downgrade or erase an independently trusted assertion. |
| D3 | `verified` can be misread as factually true. |
| D4 | Caller-controlled labels can self-upgrade. |
| D5 | Legacy provenance is guessed upward from filenames, roles, or prose. |
| D6 | A policy change makes stored derived tiers stale or unrecomputable. |
| D7 | A derivation binds only its trustworthy parent and omits another contributor. |
| D8 | Retrieval → conversation capture → redistillation launders an untrusted item into agent-authored memory. |
| D9 | Process attestation is mistaken for principal authentication. |
| D10 | Boundary completeness is overstated as universal causal completeness. |
| D11 | A trusted implementation is assumed to be a trust-preserving semantic transformer. |
| D12 | CG-1 cold validation accepts an omitted commitment because it compares only present keys. |
| D13 | Flat Chroma fields and the canonical envelope disagree; a consumer reads the favorable copy. |
| D14 | Provider fallback changes model/prompt limits without changing the committed recipe. |
| D15 | Content that looks like provenance metadata influences labels. |
| D16 | Assertion preservation enables storage-amplification denial of service; quotas may relate/suppress bytes but cannot erase provenance identity. |
| D17 | Retrieval or answer assembly omits selected parents and elevates the synthesis. |
| D18 | A matching hash is presented as proof of factual truth. |
| D19 | Transcript role is treated as authenticated user identity. |
| D20 | Pre-generation exact suppression removes an assertion before CG-1 can manifest it. |
| D21 | Old export/MCP consumers silently drop unfamiliar provenance fields. |
| D22 | R2b or Shadow PASS is cited as proof that origin classification was correct. |
| D23 | A perfectly durable generation preserves poisoned content and is called trustworthy. |
| D24 | Same content is mistaken for assertion identity, allowing an injected copy to replace or inherit provenance. |
| D25 | A child envelope/commitment looks valid while a parent, historical policy, recipe, or binding is unavailable. |
| D26 | Recursive verification follows a cycle or accepts divergent envelopes under one assertion ID. |
| D27 | A valid replay of one assertion is counted as a new origin, corroborator, or authority signal. |

## 10. Literature evidence and limitations

The local packet is under
`/home/lauer/Documents/Computing/convmem_dependability-*`; the original Codex
handoff and addendum remain under `/home/lauer/Downloads`. Primary texts were
used where present.

| Source | Use here | Limitation |
|---|---|---|
| Bloomfield & Rushby, *Assurance of AI Systems From a Dependability Perspective* | Minimize reliance on generative components; defense in depth. | General/cyber-physical framing; not a ConvMem proof. |
| Lee et al., *A Structured Approach to Safety Case Construction for AI Systems* | Claim, argument, and evidence taxonomy. | Taxonomy does not establish claim truth or solve continuous case maintenance. |
| CoDefeater | Systematic defeater prompts. | LLMs miss implicit/domain assumptions; human adjudication is mandatory. |
| TMA-NM, arXiv:2606.24322 | Origin-bound authority, monotone derivation, laundering cases. | Formal guarantee assumes true origin from authenticated channels and an action monitor; ConvMem has neither today. Answer bias is out of scope. |
| MemOps, arXiv:2607.12893 | Operation-level remember/update/forget/reflect test structure. | Benchmark/judge results are not local evidence. |
| MemSecBench | Write–Execute–Forget poisoning test shapes. | External configurations and mixed judging; reported rates are motivation, not acceptance thresholds. |
| Reliable Post-Retrieval Assembly | Separate extraction from deterministic conflict policy when explicit versions exist. | Narrow explicit-version win; real timestamp comparison was small and not a demonstrated win. |
| FRESCO / Temporal Misgrounding / MemStrata | Temporal staleness, deterministic temporal rubrics, bitemporal hypotheses. | Structured temporal metadata is a precondition; none solves free-text conflicts automatically. |
| AgentChaos / MAS-FIRE | API and handoff fault-injection taxonomies. | Later evaluation tools, not first-slice proofs. |
| Benchmark Aging | Gold/reference temporal drift. | Requires local benchmark revalidation policy. |

## 11. Stages and implementation boundaries

### Stage 0 — architecture lock (this package)

Freeze vocabulary, verified-channel inventory, binding contract, transformer
caps, commitment canonicalization, assertion/equivalence semantics, assurance
claims, defeaters, and non-goals. Kiro review and Ryan lock are required.

### Stage 1A — provenance policy and representation substrate

Implement one policy module and canonical envelope; bind normal and direct ingest;
propagate through normalization, Chroma, export, and reconstruction; handle legacy
conservatively. No live migration.

### Stage 1B — assertion continuity and exact dedupe

Preserve independent provenance assertions through exact equivalence and
retrieval. Prevent cross-tier suppression, elevation, and downgrade. This is part
of the primary provenance substrate, not an optional diagnostic feature.

### Stage 2 — provenance-aware semantic dedupe

Represent equivalence separately and require explicit adjudication before any
cross-provenance tombstone. Preserve both audit assertions.

### Stage 3 — retrieval and consumer visibility

Expose per-assertion evidence and derived review hints. Keep ranking independent.
Define consumer contract without claiming downstream enforcement.

### Parallel/later assurance track A — CG-1 and CG-2 continuity

After Stage 1 establishes the canonical representation, require and cold-validate
the commitment in CG-1 and pass it unchanged through CG-2. This track may proceed
in parallel under its own Execute brief, but it does not reopen CG-1 durability or
CG-2 serving-authority architecture and is not allowed to delay definition of the
core provenance substrate.

### Parallel/later assurance track B — broad dependability operations

Egress, backup/restore, recovery, endurance, SLOs, and general operational fault
campaigns remain separate assurance work. They may consume provenance evidence
later; they are not Stage 0 vocabulary or Stage 1 substrate deliverables.

### Stage 4 — temporal and assembly policy

Add only after reliable metadata and separate acceptance criteria exist. Bind
synthesis parents and deterministic temporal rubrics where applicable.

### Stage 5 — lifecycle and injected-fault evaluation

Add laundering, recapture, malformed provenance, provider crash/omission/value
faults, stale state, and multi-agent handoff faults.

## 12. Explicit non-goals

- cryptographic per-agent identity, mTLS/OAuth, or signed agent messages;
- automatic trust elevation or Sybil-resistant corroboration;
- TMA-NM action classes, verdict chain, or single-use action tokens;
- downstream agent/tool/git enforcement;
- factual-truth scoring or automatic poisoning detection;
- automatic suppression of all untrusted retrieval;
- temporal-conflict implementation in Stage 1;
- ranking changes or renaming `source_trust_boost` in Stage 1;
- live corpus migration, Chroma mutation, Shadow activation, or R2b capture;
- CG-2 authority redesign, activation, owner cutover, or GC;
- formal verification of the full ConvMem system.

## 13. Required assurance wording

> ConvMem conservatively preserves and propagates provenance integrity through
> the memory transformations it controls. These guarantees are conditional on
> the correctness of provenance assigned at the ingestion boundary and complete
> binding of supported transformation inputs. They do not establish factual
> truth or authenticate currently unauthenticated agent identities.

> ConvMem exposes provenance and review requirements to consumers, but it does
> not mediate downstream tool, code, git, or external actions. Until authenticated
> origin binding and an enforced action boundary exist, ConvMem does not claim
> TMA-NM end-to-end non-malleable authority or downstream action enforcement.

## 14. Review gates

1. **Kiro design review:** same branch tip, explicit PASS/FAIL against R1–R10,
   Stage 0 decisions, CG-1/CG-2 boundaries, and defeaters.
2. **Targeted Copilot audit:** same branch tip, safety/isolation and continuity
   review; no implementation and no broad re-audit.
3. **Ryan architecture lock:** adjudicates findings and authorizes any execution
   plan. A merge alone does not authorize implementation or operations.
4. **Cursor implementation:** only after a separate Ryan Execute grant.

Sol-High conflict adjudication returns to the team charter after this explicitly
authorized planning exception: it is invoked only for materially conflicting
Kiro and Copilot PASS/FAIL verdicts on the same artifact and revision.

## 15. Kiro blocker-resolution map

The reviewer must inspect the final committed tree, not working-tree edits or an
earlier SHA.

| Kiro blocker | Normative resolution |
|---|---|
| Effective-integrity rule | Sections 4–5: exact equality, lattice, generative cap, incomplete ancestry, tested preservation contracts. |
| Concrete envelope | Section 6: producer, root evidence, inputs, transformation recipe/identity, completeness, policy version, cache-only integrity. |
| Current-ingest binding | R4–R5 and Section 6: stable locator, raw/view/payload hashes, selection parameters, binding/recipe versions. |
| Cross-tier dedupe | R6 and Stages 1B/2: independent assertions, no silent suppression/tombstone, human semantic adjudication. |
| Orthogonal dimensions/actions | Sections 2 and 7 plus required assurance wording. |
| Execution order | Stage 0, Stage 1A/1B, then parallel/later CG-1/CG-2 and broad dependability tracks. |
| Recursive verification | R8 and assurance claim C4b; missing parents/policy/recipes/cycles are untrusted. |
| Mandatory continuity | R10 and assurance claim C8; only supplementary display diagnostics are advisory. |
| Planning safety/status publication | Sections 11–14 and STATUS: no runtime/live operations; cross-arc rollup waits for acceptance. |

## 16. Conditional-PASS correction map

| Required correction | Resolution |
|---|---|
| Repository paths | Existing modules are named at their actual repository-root paths; the only new filename, `provenance.py`, is explicitly labeled planned in EXECUTION. |
| T1–T5 continuity | Retained as a planning sequence; T3 is strengthened with provenance, acknowledgement, and migration semantics while T4/T5 remain planning-only. |
| Producer values/authority | Section 6.1 defines closed enums, verification meaning, initial absence of verified producers, and the rule that producer metadata grants no authority by itself. |
| Anti-ceremony | Existing standing checks and review artifacts are reused; new controls require a distinct failure window, owner, or oracle. |
| Clean review target | Reviewer records and inspects only the final committed SHA; working-tree edits are not review evidence. |
