# Execution Plan — Dependability and Provenance Integrity

```text
Status:       P2 IMPLEMENTATION IN PROGRESS — P1 merged; VERIFY pending
Depends on:  locked T3 basis; P1 closeout `809de5c6b296ea56428cf766bab4eb8912cafff3`
Owner:       Cursor P2 implementation lane under Ryan's exact Execute grant
Baseline:    locked T3 @ aae0cad0bb05b0e436e213b28abbe0ff05ba2e91
Grant:       Ryan T3 P1 Execute @ 83f63eb82a18fae38dfe0920146e9e427d39aabb
Branch:      impl/2026-08-17-trapdoor-t3-p1; PR #203
Closeout:    PR #203 merged at `836e83960e834327868fedef0368366622869db7`
P2 grant:     Ryan T3 P2 Execute from `809de5c6b296ea56428cf766bab4eb8912cafff3`
P2 branch:    impl/2026-08-18-trapdoor-t3-p2; `/home/lauer/Projects/convmem-trapdoor-t3-p2`
P2 PR:        [PR #204](https://github.com/alanmz-crypto/convmem/pull/204)
```

## Human consequence

This plan decomposes the implementation slices so reviewers can test their
feasibility. Ryan authorized P1 and it is now complete and merged. Ryan has
now separately authorized only the named P2 implementation surface. It does not authorize
migrations, live Chroma/corpus mutation,
CG-2 activation, Shadow activation, R2b capture, or external changes.
Stage 1 must be additive and conservative: existing records remain queryable but
are untrusted for security decisions until they carry valid provenance.
Stage 1A/1B may therefore operate as an explicitly untrusted-only production
substrate. A non-degenerate production integrity feature is separately gated:
Verified Ingress Bootstrap must be designed and evidenced before Stage 3
consumer-facing integrity exposure is considered complete. This plan does not
design or implement that bootstrap.

## Scope lock

### In scope for Stage 1A/1B

- one canonical provenance envelope, commitment algorithm, and policy function;
- root-ingress evidence with no production channel initially verified;
- exact normal-ingest and direct inter-model transformation bindings;
- transformer-aware monotone integrity propagation;
- unit/Chroma/export/reconstruction parity;
- per-assertion retrieval visibility;
- legacy-as-unknown behavior;
- exact-dedupe protection for independent cross-provenance assertions;
- property, round-trip, negative, and laundering tests.

Stage 1A/1B does not claim operational production access to the `agent` or
`trusted` tiers while the verified-channel inventory is empty. Synthetic
fixtures exercise those tiers for substrate verification only.

### Explicitly out of scope

- production data migration or backfill;
- semantic-dedupe adjudication implementation (Stage 2);
- ranking, recency, or temporal-conflict changes;
- authenticated identity, automatic elevation, or downstream action gates;
- Shadow/R2b/CG-2 operational work;
- renaming existing `source_trust` code;
- factual correctness or poisoning classifiers.

### Parallel/later assurance tracks

- CG-1 immutable-manifest/cold-validation continuity and unchanged CG-2
  provenance pass-through follow the canonical Stage 1 representation under a
  separate Execute brief.
- Egress, backup/restore, recovery, endurance, SLO, and broad operational fault
  work remain separate dependability tracks.
- Overall arc closure eventually requires the CG-1/CG-2 continuity evidence, but
  those integrations do not precede or redefine the Stage 1 substrate.

## Retained T1–T5 planning sequence

The implementation packages below are the bounded provenance slice within the
existing Trust Arc sequence. T1–T5 remain visible so later work cannot be
mistaken for discarded scope, but this document authorizes none of it.

P0, the CI Merge Gate, is prerequisite infrastructure outside Full Fathom Five
and is not counted among the five arcs. The canonical order is FF1/T1 Trust
Baseline → FF2/T2 Existing Evidence + Failure-Gap Matrix → FF3/T3
Compatibility & Provenance → FF4/T4 Security, Privacy & Egress → FF5/T5
Operational Envelope.

| Track | Decomposition | Current disposition |
|---|---|---|
| FF1 / T1 | Trust baseline, claim matrix, severity, and degraded-state contract | Planning only; no runtime gate change |
| FF2 / T2 | Existing-proof inventory and smallest missing oracles | Planning only; reuse standing evidence where sufficient |
| FF3 / T3 | Compatibility/provenance contract and fixtures | This package's strengthened Stage 1A/1B focus |
| FF4 / T4 | Security/lifecycle and egress evidence | Separate plan and grant; no cloud-policy or runtime change |
| FF5 / T5 | Endurance/resource/maintenance envelope | Separate plan and grant; no operational change |

T1 Trust Baseline and T2 existing-proof inventory/gap analysis must be
completed and accepted before any T3/provenance implementation grant. Stage
1A/1B is the T3 child architecture/execution slice, so it cannot receive that
grant until T1's architecture output and T2's evidence/gap output are complete;
T4 and T5 remain in the parent sequence after T3.

This is a crystallization boundary, not a new implementation stage:
**Full Fathom Five parent structure frozen; further findings are review
findings, not automatic scope additions.** New findings must be recorded
against the relevant arc and cannot create a new handoff, grant, or parent-plan
scope without an explicit planning decision.

T3's acknowledgement rule is precise: only the named authoritative durable
write boundary may return an acknowledged-success result; provider completion,
projection visibility, index upsert, client receipt, and retrieval are not
durable acknowledgement on their own. T3 migration semantics are equally
bounded: define the supported N-1 window, reject future versions, support
dry-run, require backup-before-write, and specify atomic replacement/rollback;
none authorizes a live migration or backfill.

Use existing standing checks and review artifacts when they already cover a
claim. Add a new check only for a distinct failure window, owner, or oracle.

## Preconditions

Before implementation begins:

1. Kiro reviews the architecture and this decomposition at one exact SHA.
2. Copilot performs the targeted safety/isolation and continuity audit at that
   same SHA.
3. Ryan resolves findings and records an architecture lock.
4. Ryan issues a distinct Execute grant for exactly one of P1, P2, or P3; the
   grant names its branch, worktree, and PR. One grant never covers multiple
   slices.
5. Cursor rebases from the then-current `origin/main` and re-traces any changed
   ingest, dedupe, CG-1, CG-2, export, or retrieval boundary.
6. Before Stage 3 may claim a non-degenerate production integrity lattice or
   expose `agent`/`trusted` as operational production capabilities, Ryan must
   separately approve a Verified Ingress Bootstrap design and evidence showing
   at least one monitor-controlled authenticated origin boundary. This is a
   sequencing gate, not an implementation grant in this package.

## Ordered work packages

```text
Stage 0 vocabulary/architecture lock
  → Stage 1A policy + envelope + exact transformation bindings
  → Stage 1B representation + assertion/dedupe/retrieval continuity
  → Stage 1 verification and independent review
  → Verified Ingress Bootstrap design/evidence
  → Stage 3 consumer-facing non-degenerate integrity exposure

Parallel/later after the representation is locked:
  A. CG-1/CG-2 commitment continuity
  B. egress/recovery/operational assurance
```

### Separate Ryan execution units

P1, P2, and P3 are serially related but independently authorized delivery units.
Each uses its own branch/worktree and PR; P2 starts only after P1 is merged or
Ryan explicitly authorizes a reviewed rebase, and P3 follows the same rule for
P2. The names below are reserved planning targets, not branches created by this
planning package:

| Slice | Scope | Ryan grant | Implementation branch | PR | Gate |
|---|---|---|---|---|---|
| P1 | Policy, envelope, monitor-minted assertion identity, recursive verification | Complete; granted at `83f63eb82a18fae38dfe0920146e9e427d39aabb`, final head `ec093b10afb6bd8a51a131174857ecbded4287bc` | `impl/2026-08-17-trapdoor-t3-p1` (`/tmp/convmem-trapdoor-t3-p1`) | [PR #203](https://github.com/alanmz-crypto/convmem/pull/203) | Focused/full validation, Kiro PASS, Copilot PASS, merged at `836e83960e834327868fedef0368366622869db7` |
| P2 | Current-ingest bindings and unit/Chroma/export/reconstruction continuity | **Granted** from `809de5c6b296ea56428cf766bab4eb8912cafff3` | `impl/2026-08-18-trapdoor-t3-p2` | [PR #204](https://github.com/alanmz-crypto/convmem/pull/204) | Binding/round-trip VERIFY, P1 regression, Kiro PASS, Copilot PASS, then Ryan merge decision |
| P3 | Assertion-preserving exact dedupe, retrieval visibility, and same-content independence | Separate P3 Execute grant | `feat/2026-08-15-provenance-assertion-continuity` | Separate P3 PR | Identity/dedupe/retrieval VERIFY plus review |

P1 implementation was authorized only on the named branch/worktree and PR for
that grant, and is now merged. P2 is authorized only on the named branch and PR
above. P3 and later work remain unauthorized; no migration, live operation,
Bootstrap, CG-2, Shadow, R2b, or T4/T5 work follows from P2.

### P1 / Stage 1A — Canonical policy and representation

Create one deep module that owns:

- schema/versioned envelope types and validation;
- canonical JSON and `provenance_commitment` calculation;
- root mapping from monitor-controlled ingress evidence;
- `untrusted < agent < trusted` meet;
- transformer caps and ancestry-completeness rules;
- closed-enum validation for `producer_class` (`user | trusted_tool | agent |
  external | unknown`) and `producer_assurance` (`verified | claimed | unknown`),
  with no caller-controlled `verified` value or direct authority grant;
- effective-integrity recomputation and cache-mismatch degradation;
- legacy/malformed/unknown-policy fallback to untrusted.

P1 must mint content-independent UUIDv4 `assertion_id` values centrally (128-bit
encoded identifiers with 122 random payload bits), atomically reserve them
before publication, preserve valid ID/commitment pairs only as idempotent replay,
and create a new ID for same-content independent assertions. Replay under an
existing ID requires the same canonical envelope and commitment and creates no
corroboration or authority evidence. An invalid or mismatching pair fails
identity-preserving import; retaining the content requires a new monitor-minted
untrusted assertion. P1 recursively verifies parents,
historical policy/recipes, bindings, cycles, and commitments before computing
integrity. A missing ancestor or parent mismatch is untrusted.

No adapter, caller, Chroma field, source path, role, confidence, or ranking code
may independently compute integrity. The empty-input and caller-self-upgrade
negative tests are P1 gates.

### P1 precondition — census of manifest-bound mutators

Before P1 closes, P1 must complete and lock a census of every mutator affecting
manifest-bound authority components, together with the consistency mechanism
that covers each path. Each path must either be covered by one capture/sealing
consistency protocol or be explicitly classified outside the provenance
authority set. Every later phase must update and revalidate that census for any
manifest-bound writer it introduces or changes. Existing Restic freshness gates,
shared writer leases, process locks, and exclusive leases are not proof of V4m
unless the census and consistency contract establish their coverage. P1 must
not claim final V4m PASS from the census alone: V4m reaches PASS only after the
final implemented writer set has the required universal evidence before T3 arc
closure. This is a planning dependency/precondition only: it is not a grant to
implement CG-1, backup/restore, or Shadow, nor to wire the existing
exclusive-writer lease. That primitive is implementation context only and does
not satisfy the guarantee.

P1 must also choose and document one R8 pin-retention mechanism: either no
implementation-controlled reclamation of authority generations or snapshots
that an active verification operation can pin, or a pin-aware lease/reference
mechanism. If the bound state can nevertheless be reclaimed, the operation must
detect that loss and fail closed or restart without substituting another state;
it may not continue against substituted state. Retention periods, compaction,
quotas, and mature garbage-collection policy remain later lifecycle work.

P1 must also define the future restore integration: extend
`complete_data_restore.py` `STATE_SPECS` and `writer_census_for_root()` to
classify `provenance/` as a required Tier-1 durable path, update
`docs/RECOVER.md`, and add a separate provenance validator. The registry
manifest validates store graph/commitment integrity; `.convmem-backup-evidence.json`
remains capture evidence and does not replace that validator. The preflight must
run both contracts before a recovered registry can publish. The recovery plan
must select one immutable complete-data-v2 generation/manifest commitment before
reading components; registry, policy/recipe history, JSONL, and Chroma must all
match it. An older valid generation requires a separate Ryan rollback grant and
may not be auto-selected. Before sealing, all manifest-bound authority
components must be captured from one consistent logical source state; concurrent
mutation without an immutable/staged or equivalent consistency proof must cause
retry, rejection, or quarantine. This capture/sealing condition is distinct
from restore-side selected-generation binding and leaves the implementation
mechanism open. Crash interruption must be injected at every durable write,
rename, manifest, pointer, and publication boundary, proving the result is either
the prior complete authority generation or one complete verified replacement,
never a mixed or missing authority set. P1 must define one normative, versioned
ConvMem canonicalization profile/serializer and publish golden vectors that
detect serializer-library drift; no cross-implementation portability
requirement is implied by this slice.

### P1 review-finding disposition and predecessor binding

The bounded Kiro findings are handled on this correction branch as follows:

- root and derivation transformer caps, recursive cycle/depth/node/byte bounds,
  literal canonicalization vectors, V2a lattice/property coverage, successful
  replay, origin/schema validation, and the P1 mutator census are implemented
  and tested in the P1 surface;
- the restore item is limited to the future `provenance/` validator and
  `STATE_SPECS`/writer-census integration boundary in `docs/RECOVER.md`;
  restore execution remains deferred because it belongs to later recovery and
  durable-data scope, not this in-memory P1 grant;
- active-pin retention is closed for P1 by disabling implementation-controlled
  reclamation. Pin-aware GC, retention periods, compaction, quotas, and loss
  drills remain deferred under the locked T4/T5 lifecycle boundary;
- final universal V4m evidence remains deferred beyond P1 because P2/P3 and
  later CG-1/restore/projection writers have not yet entered the implementation
  set. The P1 census is a required baseline, not a VERIFY PASS;
- V0f is bound to existing accepted predecessor evidence, not recreated here:
  [FF1/T1 accepted at `3c746faa`](https://github.com/alanmz-crypto/convmem/commit/3c746faa47409f7def02d2fd24351fbc936a9720),
  [FF2/T2 accepted at `0c2ab32`](https://github.com/alanmz-crypto/convmem/commit/0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361),
  and [Interlude locked at `17609b2`](https://github.com/alanmz-crypto/convmem/commit/17609b2d11b824cc3474337aca20cd7506d5699e).

All repository VERIFY rows remain `PENDING`; these dispositions do not
self-promote any candidate result.

Likely surfaces after re-trace:

- new repository-root provenance policy/serialization module (`provenance.py`,
  subject to implementation re-trace and naming review);
- focused policy and canonicalization tests under `tests/`.

### P2 / Stage 1A — Transformation-boundary binding and durable continuity

For normal ingest, bind adapter-stable source records, raw-record hashes, each
exact rendered/truncated view, ordering/chunk/selection parameters, and the full
provider payload. Bind both ingest rendering and the additional distillation
truncation. Record requested/resolved provider/model, fallback, generation
parameters, binding version, fixed recipe/config hash, response hash, producer,
and transformer.

For direct inter-model indexing, treat `source_type` and `author_model` as
claimed classification only. Direct packaging may preserve only a tested
content-preservation contract; a caller cannot mark itself verified or trusted.

Propagate the canonical envelope and commitment through normalized units,
Chroma scalar-safe metadata, export, and canonical reconstruction. Add fixtures
for malformed fields, old rows, unknown policy versions, and old consumers.

Likely surfaces after re-trace:

- `ingest.py`
- `distill.py`
- `llm.py`
- relevant adapters under `adapters/`
- `inter_model_index.py`
- `eval_corpus/reconstruct.py`
- export/reingest tests and fixtures

### P3 / Stage 1B — Assertion-preserving dedupe and retrieval

Separate assertion identity from content/equivalence identity. Exact duplicates
with independent or different provenance cannot cause the incoming assertion's
provenance to disappear and cannot elevate or downgrade the existing assertion.
Storage optimization may relate assertions or share immutable content bytes,
but retrieval/audit must be able to recover each provenance assertion.

Do not implement automatic semantic cross-provenance collapse. Existing semantic
approval must fail closed or require explicit human adjudication when provenance
differs. A later Stage 2 design decides durable equivalence/tombstone semantics.

Expose the canonical envelope, commitment, and recomputed effective integrity per
assertion at retrieval boundaries. Representation, propagation, export, and
retrieval continuity are mandatory integrity requirements. Only supplementary
display diagnostics may be advisory. Keep relevance, recency, temporal status,
and `source_trust_boost` outside the integrity calculation.

Likely surfaces after re-trace:

- `ingest_dedupe.py`
- `refine.py`
- assertion/equivalence persistence and lifecycle tests
- `query.py`, `evidence.py`, and response-schema tests

### A1 / parallel-later — CG-1 and CG-2 continuity

This is not part of the initial substrate implementation order. It receives a
separate Execute brief after Stage 1 representation is locked.

Make the provenance commitment a required immutable attribute for new-schema
CG-1 candidates and manifest rows. Include it in candidate/bundle identity as
specified by the locked architecture. Cold validation must reject omission,
mutation, unknown schema, or envelope/commitment mismatch rather than comparing
only keys that are present.

Carry the assertion and commitment unchanged through CG-2 serving. The
request-frozen authority vector remains the sole serving-authority mechanism;
CG-2 does not recompute provenance or aggregate trust.

Likely surfaces after re-trace:

- `file_generation_contract.py`
- `file_generation_builder.py`
- `file_generation_store.py`
- `serving_authority.py`
- `serving_index_repository.py`

### P4 — Stage 1 verification packet and compatibility closure

Run the locked tests in `VERIFY-dependability-provenance.md`. Produce evidence
for the exact implementation tip, including focused and full regression runs,
diff checks, no-live-mutation proof, serialized fixtures, and negative controls.

Kiro reviews the implementation design/result. Copilot performs the targeted
safety/isolation audit because this changes security-relevant data continuity.
Ryan alone decides merge and any later migration/activation grant.

### A2 / parallel-later — Broad dependability assurance

Egress controls, backup/restore, recovery, endurance, SLOs, and general
operational fault injection retain separate owners and plans. They may consume
the provenance envelope after Stage 1, but they cannot broaden this Execute scope
or make provenance continuity advisory.

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
I(output) = meet(I(all completely bound inputs), transformer_cap)
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
3. Missing mandatory envelope/commitment continuity fails or degrades to
   untrusted; it is never an advisory integrity result.
4. Retrieval preserves each assertion's provenance independently.

### Dedupe

1. Cross-provenance exact duplicates remain independently auditable.
2. A low-integrity duplicate cannot downgrade a trusted assertion.
3. A high-integrity duplicate cannot elevate an untrusted assertion.
4. Semantic cross-provenance tombstoning cannot occur without explicit human
   adjudication and retained audit evidence.

### Parallel/later CG-1/CG-2 continuity

1. CG-1 cold validation rejects missing or altered commitments.
2. CG-2 returns the same assertion/commitment selected by serving authority.
3. Neither integration redefines effective integrity, serving authority, or
   the Stage 1 envelope.

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
