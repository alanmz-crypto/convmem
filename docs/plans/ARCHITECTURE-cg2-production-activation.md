# Architecture Direction — CG-2 production activation

> **ARCHITECTURE LOCKED — Design A first-cutover rollback bootstrap (Ryan,
> 2026-08-21).** Restored from `e680ce837653698a5be8b78ba02db2f880c40c63` and
> amended only for the Design A lock. This document does **not** authorize
> implementation, production configuration, corpus mutation, owner cutover,
> garbage collection, Shadow, R2b, or V8c activation. CG-1 remains the committed-
> generation identity contract. Design A is an architecture correction for
> first-owner cutover/rollback; Execute and production grants remain separate.

**Source:** Codex synthesis of the merged CG-1 implementation and closure
evidence, the ChatGPT CG-2 advisory research memo, ConvMem builder-reference
guidance, and primary literature listed in §15; Design A amendments from Ryan
Architecture HITL 2026-08-21.

**Reviewed CG-1 stabilization:**
`2ed229244ea1d7cdf9a83630ad56d5a194426826`

**Design A lock base (`main` at lock):**
`cd9554e4c3006f7e0695d5d17a69696cc913c566`

**Prior architecture lock SHA (restored text):**
`e680ce837653698a5be8b78ba02db2f880c40c63`

**Problem:** Activate CG-1's committed-generation substrate in production
without allowing legacy rows, inactive generations, stale source bytes, raw
Chroma reads, or premature reclamation to become serving authority.

## 1. Planning status and product goal

| Field | Value |
|---|---|
| Phase | Architecture Locked — Design A (2026-08-21) |
| Product goal | Failed or interrupted reindexing can never corrupt the corpus that ConvMem serves |
| This arc | Move CG-1 from hermetic substrate to bounded production use |
| Author | OpenAI Codex (original); Design A amendments Cursor Auto under Ryan lock |
| Research input | ChatGPT advisory memo; external claims rechecked before inclusion; Design A HITL |
| Review lanes | Kiro design review; Crush evidence/risk review; Cursor implementation feasibility review |
| Authority | Architecture locked for Design A only; Execute and V8c activation grants separate |
| Next phase | Execution Planning only after architecture lock |

The activation order is the central decision:

```text
global read authority first
        ↓
logical accounting and source-staleness guards
        ↓
legacy-only production soak through the new boundary
        ↓
one explicitly granted owner canary
        ↓
bounded owner batches
        ↓
reclamation last, behind a separate evidence gate
```

## 2. Locked CG-1 foundation

CG-2 inherits these constraints and does not reopen them:

1. Build and commit are separate.
2. The lifecycle is `built → fresh-process cold-validated → durably promoted → serving`.
3. Exactly one generation per canonical source owner has serving authority.
4. The durable per-owner pointer names the serving generation.
5. File-derived rows use generation-specific copy-on-write physical IDs.
6. Logical identity and physical storage identity are separate namespaces.
7. Previous-generation rows remain intact during promotion.
8. Promotion compares the expected previous generation and rejects stale work.
9. Recovery accepts only the generation named by the visible pointer; it never
   elects a “most complete” candidate.
10. Fresh-process qualification is structurally mandatory and cannot be
    replaced by a caller-supplied permissive validator.
11. Candidate staging emits no authoritative Shadow Ledger events.
12. Authority is per owner; ConvMem does not claim a corpus-wide atomic snapshot.
13. CG-1's measured durability bar covers process-crash recovery and its
    documented SQLite/Chroma behavior; it does not claim full power-loss durability.
14. One unresolved abandoned candidate per owner already blocks further staging.

## 3. Repository facts that shape CG-2

These are observed implementation facts, not literature analogies:

| Surface | Current fact | CG-2 consequence |
|---|---|---|
| Owner identity | `ownership_key(path)` is `source:<Path.resolve(strict=False)>`; manifests validate that relationship | A rename creates a new owner unless CG-1 is reopened; CG-2 chooses explicit owner migration |
| Production wiring | Production code has no caller of the CG-1 pointer/builder APIs | Activation needs a new orchestration boundary, not a config toggle |
| Read inventory | The CG-1 AST inventory classifies four `cg2-production-bypass` constructors: `ask.py`, CLI `search`, MCP `related`, MCP `stats` | All four classifications must reach zero before a generational owner serves |
| Generation store | `FileGenerationStore` snapshots the active owner→generation map once per read and defensively rechecks returned rows | Preserve this request-frozen authority behavior |
| Generation query | The hermetic store computes cosine distance over all active embeddings in Python | It proves filtering semantics but is not automatically production-scale |
| Query fallback | `query.py` catches broad failures and uses a read-only fallback | CG-2 must prevent a generation-authority failure from silently becoming an unmediated legacy read |
| Drift | `doctor._check_index_drift` compares raw Chroma IDs with export IDs | Physical generation churn makes the current percentage semantically false |
| Parity | `projection_parity.entity_key` prefers `ledger_id`, then `row["id"]` | File-derived generation rows need namespaced logical identity |
| Collection metadata | Live doctor reports legacy embedding identity missing | First generational canary must prove embedding provenance rather than infer it |

The ChatGPT memo's Chroma report is upstream issue
[`#7463`](https://github.com/chroma-core/chroma/issues/7463), opened against
`chromadb==1.5.9` and `PersistentClient`. The reporter explicitly classifies it
as an operational replay-cost/missing-flush-primitive report, not data loss:
sub-threshold writes recovered in the reporter's hard-kill test through WAL
replay while HNSW persistence lagged. The report is motivating evidence from a
different environment, not a ConvMem guarantee or activation premise. Pinned-
version behavior on ConvMem's Linux filesystem remains an empirical gate (§13).

## 4. Architecture options and decision

| Option | Safety | Migration/rollback | Cost | Decision |
|---|---|---|---|---|
| Corpus-wide build and one global switch | Large blast radius; one source can block all | Corpus-scale rollback | High | Reject unless mixed operation proves impossible |
| Global read boundary, then per-owner cutover | Explicit authority; bounded blast radius | Owner-local rollback | Medium-high | **Choose** |
| Full parallel shadow corpus, then global switch | Strong comparison evidence | Final switch remains corpus-wide | Very high | Use shadowing as verification only |
| Permanent generation-first read with legacy fallback | Two competing authorities; stale data can resurrect | Superficially easy, semantically unsafe | Medium | Reject |

### Decision

CG-2 uses **incremental per-owner migration behind one globally enforced serving
repository**. Code-path cutover and data cutover are separate:

1. Every serving read moves behind the repository while all owners still use
   legacy compatibility semantics.
2. Only after that boundary soaks successfully may an explicitly named owner be
   fenced and promoted to committed-generation authority.

Compatibility is an intentional authority mode, never “try generation and fall
back on error.”

## 5. Deep module boundary: the serving repository

CG-2 introduces one deep core boundary, conceptually `ServingIndexRepository`.
The name is illustrative; the execution plan chooses the file/module name.

It owns:

- one request-frozen authority view;
- legacy-versus-generational classification;
- active-generation predicates and defensive row verification;
- mixed-mode candidate retrieval and deduplication;
- exact/logical lookup semantics;
- serving counts distinct from physical-storage counts;
- fail-closed authority errors;
- lifecycle/close behavior for the underlying Chroma client.

The boundary covers both `knowledge_units` and `conversation_summaries`,
including CLI `--raw` fallback. A raw-summary search is still a serving read and
cannot bypass owner authority after the first generational cutover.

It does **not** own:

- CLI or MCP presentation;
- ranking, evidence injection, or answer synthesis;
- owner migration policy;
- candidate construction;
- operator activation grants;
- physical GC policy.

`query.py`, ledger/evidence helpers, and the CLI/MCP adapters consume this one
repository contract. `mcp_server.py` and `convmem.py` remain thin adapters. CG-2
does not create a service, daemon, global transaction coordinator, or second
vector database.

### 5.1 Request-frozen authority vector

At the start of one serving operation, the repository resolves:

```text
owner digest → LEGACY | FENCED | ACTIVE(generation_id) | QUARANTINED
```

That immutable mapping governs the whole request. A multi-owner query may
contain generations promoted at different times. It is a **request-frozen
authority vector**, not a corpus snapshot and not Snapshot Isolation.

The resolver derives state, rather than accepting it from a caller:

| Durable evidence | Resolved state |
|---|---|
| No fence and no pointer; row satisfies the locked legacy classifier | `LEGACY` |
| Valid fence and no pointer | `FENCED` (unavailable) |
| Valid fence plus recovered/qualified exact pointer | `ACTIVE(generation_id)` |
| Pointer without the required first-cutover fence | `QUARANTINED` |
| Malformed, mismatched, or unqualified fence/pointer/manifest | `QUARANTINED` |
| Explicit old-owner retirement record | retired/excluded from serving |

Stable non-file projections are admitted through a separate explicit projection
allowlist and governing contract. They do not become a synthetic legacy owner,
and an unclassified projection cannot serve.

Before the first canary, every physically serving legacy row must be classified
as stable-governed or as one canonical legacy owner. An unknown legacy source
class blocks activation rather than becoming an implicit global legacy owner.

Visible pointer bytes are not automatically qualified authority in a new
process. Startup or lazy authority loading must run exact CG-1 recovery/
qualification before adding that pointer to the serving map. A cache may retain
the qualified result, but it is keyed by the exact pointer/manifest hashes and
backend fingerprint and is invalidated when those bytes change.

The active and immediately previous generations remain physically available
long enough for a request that resolved the old vector to finish.

#### Authority-resolution linearization

Fence, pointer, manifest, and retirement evidence are separate durable objects.
The resolver must not compose a serving decision from a torn observation of
those objects. Per owner it therefore follows a seqlock-like protocol without
introducing another authority:

1. capture the exact identities/hashes (including explicit absence) of the
   relevant fence, pointer, manifest, and retirement evidence;
2. derive and, where required, qualify the tentative owner state;
3. reread the relevant evidence identities before admitting the state;
4. discard the tentative state and retry if any evidence changed;
5. publish the state into the immutable request vector only after a successful
   unchanged verification.

Each attempt reads the pointer again **last**, after manifest qualification and
the fence/retirement reread, because pointer publication is the final serving-
authority step. Rename-linked old/new owners receive one final exclusion-group
check before the vector freezes; if lineage evidence changed or both owners
would be admitted, the request retries or refuses rather than freezing a torn
rename view. This group check uses the same fence/pointer/retirement evidence,
not a second durable authority.

The successful final verification is that owner's read linearization point.
No serving-row dereference occurs before it. This is a read/copy/verify/retry
pattern, not a kernel seqlock claim and not a new durable sequence authority.

Resolution is bounded by a named `authority_resolution_retry_budget` containing
both `max_attempts` and `max_elapsed`. The execution plan must measure and ratify
both values before the legacy-only gateway soak; the earlier exhausted limit
wins. Exhaustion returns an observable request-scoped `AUTHORITY_UNSTABLE`
refusal, emits retry/churn metrics, and admits no rows, cache entry, or fallback.
It does **not** durably quarantine an owner whose individual artifacts remain
valid. Malformed or contradictory stable evidence still resolves to
`QUARANTINED` under the existing authority table.

The precise fence property is:

> An owner-authority resolution that linearizes after durable fence publication
> cannot resolve that owner as `LEGACY`.

A request whose owner state linearized before the fence may finish with its
frozen legacy view while retained rows remain protected. Different owners in
one request can linearize at different instants; CG-2 still makes no corpus-wide
snapshot claim.

### 5.2 Mixed-mode vector retrieval

Once the first owner is generational, a raw top-k query over the collection is
unsafe: inactive or fenced legacy rows can consume nearest-neighbor slots.
Correctness therefore precedes optimization:

1. Query stable-governed plus exact active-generation rows with a backend
   predicate derived from the frozen authority vector.
2. Query legacy physical rows separately for owners still in `LEGACY`.
3. Reject inactive generations, fenced/retired legacy owners, unknown scopes,
   and owner/generation mismatches after retrieval.
4. If the backend cannot express the full legacy-authority predicate, widen the
   legacy candidate query only under a tested backend-specific condition that
   establishes an authority-complete eligible candidate set.
5. Merge the eligible partitions by distance, then run existing ConvMem ranking.
6. Deduplicate on namespaced logical identity, not physical ID.

The backend predicate is an optimization and narrowing mechanism; the frozen
owner→generation map is authority. If correctness would require an unbounded or
over-budget scan, the request fails observably and rollout pauses. It must not
return a silently incomplete ranking or switch to raw fallback.

This is an authority-correctness guarantee under ConvMem's existing Chroma
approximate-nearest-neighbor contract, not a claim of mathematically exact
nearest neighbors. The spike must test whether filtered queries or candidate
expansion preserve the required eligible result. If no sufficient condition is
available on Chroma 1.5.9, incremental mixed-mode activation is blocked and the
architecture must revisit a physically separated live view or global migration.

The spike and eventual VERIFY plan keep three properties separate:

1. **Authority safety:** every returned row belongs to the request-frozen
   authority vector; this is absolute and fail-closed.
2. **Authorized cardinality:** when an authority-clean reference view returns
   `k` authorized rows under the same query settings, inactive/history rows in
   the mixed physical collection cannot cause silent underfill.
3. **Retrieval quality:** ranking/recall divergence is measured independently
   because Chroma HNSW is already approximate.

The primary control oracle is a temporary Chroma 1.5.9 collection containing
only rows admitted by the frozen vector, with the same embeddings, metric, and
HNSW settings as the mixed collection. This isolates filtering damage from the
backend's ordinary ANN approximation. Exact cosine remains a secondary recall
diagnostic; it does not turn CG-2 into an exact-kNN project.

Before implementation is approved, a representative-scale spike must determine
whether Chroma 1.5.9 can push the active-generation filter efficiently. If not,
the execution plan must choose between bounded adaptive widening, explicit
legacy metadata expansion, or revisiting the rejected global migration option.

### 5.3 Fallback taxonomy

CG-2 separates failures that current broad exception handling can conflate:

| Failure | Allowed behavior |
|---|---|
| Chroma reader-open transient while all owners are legacy | Existing observable read-only fallback may remain if it preserves the same authority set |
| Ranking/reranker failure | Existing documented ranking fallback may remain |
| Pointer, manifest, qualification, fence, or authority-map failure | Fail closed; no legacy fallback |
| Mixed-mode query cannot satisfy authority safety/cardinality within budget | Observable degraded/error result; no raw fallback |
| Quarantined owner | Exclude only if the API contract permits partial multi-owner results and names the exclusion; otherwise fail the request |

#### Structural fallback guard

The serving repository owns fallback classification and exposes typed failure
domains to its adapters:

- `ServingAuthorityError`: fence, pointer, manifest, qualification, quarantine,
  retry-exhaustion, or authority-filter proof failure — always fail closed;
- `ServingBackendIntegrityError`: corruption or contradictory persisted backend
  state — always fail closed;
- `ServingBackendTransient`: an explicitly recognized Chroma open/contention
  condition — the only class eligible for fallback.

These names are architectural categories; the execution plan may refine their
concrete class names. They must not share a catch-all base that adapters treat
as fallback-eligible. CLI/MCP/answer adapters do not catch `Exception` and then
choose a storage path. A repository-internal transient fallback may use readonly
metadata only when it receives the same frozen authority vector and proves the
same authority-safety and authorized-cardinality contract. Otherwise it refuses.

`_fallback_query_rows`, `collection_metadata_rows`, `open_chroma_for_read`,
`open_readonly_unit_store`, keyword fallback, CLI related, MCP unresolved, and
serving count/digest callers are therefore either mediated by this repository
or explicitly classified non-serving. Eliminating the four frozen
`cg2-production-bypass` constructors is necessary but not sufficient. The
boundary fitness test must fail if discovery is empty and must classify every
serving-adjacent Chroma/SQLite read, including calls hidden beneath core-storage
helpers.

## 6. Owner and cutover state machines

### 6.1 Owner authority states

```text
LEGACY
  │ create durable monotonic legacy fence
  ▼
FENCED_NO_POINTER  ── recovery completes exact promotion or explicit operator repair
  │ publish qualified CG-1 pointer
  ▼
GENERATIONAL
  │ pointer repromotion only
  ├──────────────► GENERATIONAL(previous retained)
  │ integrity failure
  ▼
QUARANTINED
```

Interpretation:

- `LEGACY`: no fence and no qualified pointer; explicit compatibility reads are legal.
- `FENCED_NO_POINTER`: legacy reads are permanently disabled, but no pointer can
  yet serve. The owner is unavailable. This is the intentional fail-closed crash
  state between first-cutover steps.
- `GENERATIONAL`: the qualified CG-1 pointer is sole serving authority.
- `QUARANTINED`: authority cannot be proven; data remains physically untouched.

The fence is monotonic, hash-bound, atomically published, and directory-synced.
It does not name a generation and does not compete with the pointer. Removing a
fence is not ordinary rollback and requires a separately scoped operator repair.

### 6.2 Candidate state

```text
QUEUED → BUILDING → BUILT → STAGED → COLD_VALIDATED → PROMOTABLE → ACTIVE
             └──────── failure at any pre-active stage ────────► ABANDONED

ACTIVE → PREVIOUS_RETAINED → GC_ELIGIBLE → DELETING → DELETED

COLD_VALIDATED ──(Design A convert-v1)──► RETAINED_ROLLBACK_BASELINE
```

`GC_ELIGIBLE` is a proved state, not a synonym for inactive.

**`RETAINED_ROLLBACK_BASELINE` (Design A):** A lifecycle/evidence state for the
first-cutover rollback generation `G_rb`. The generation is manifested,
embedding-proven, cold-qualified, physically retained, and grant-bound. It is
**not** a second durable serving authority: it never holds serving authority
until selected by generation-switch rollback (or appears only as
`previous_generation_id` on the first canary pointer). It is not `LEGACY`
authority and does not compete with the active pointer.

### 6.3 Rollback, recovery, and forward publication (Design A)

Three distinct operations — never conflated:

| Operation | API | Role |
|---|---|---|
| Forward promotion | `publish_active_pointer` | Promote a new generation; **mandatory** current-source freshness |
| Generation-switch rollback | `rollback_active_pointer` | Restore exact retained/grant-bound generation; may proceed after source advance |
| Same-pointer durability recovery | `recover_active_pointer` | Republish **exact current pointer bytes** only; never switches generation |

**Forward `publish_active_pointer`:** CAS requires `expected_active_generation_id`
equal to the current active generation (`None` only via the dedicated first-
cutover path). Durable `previous_generation_id` is the §6.3 rollback target for
the new pointer. Current canonical `source_hash` must equal the target
manifest's `source_hash` or publication refuses and queues rebuild.

**First cutover** uses dedicated `publish_first_cutover_active_pointer`:
`expected_active=None`, durable `previous_generation_id=G_rb`, with structural
revalidation of the grant-bound baseline (see §7).

**`rollback_active_pointer`:** Normal rollback never resurrects legacy. It:

1. selects the exact retained previous/grant-bound generation (first-canary
   window: `G_rb`);
2. fresh-process qualifies that exact manifest and rows (embedding, completeness);
3. acquires the owner lock;
4. CAS-requires the current active generation exactly;
5. publishes the retained generation as active **without** requiring
   live source bytes to equal the retained manifest `source_hash`;
6. if live source has advanced, durably marks reconciliation-required and
   enqueues desired state for the newer source;
7. records the former active generation as retained history;
8. leaves the fence monotonic — owner remains GENERATIONAL; **never LEGACY**.

**`recover_active_pointer`:** Durability recovery only. Same generation, exact
pointer payload. Not rollback.

## 7. Production ingest and source-observation binding

The production path becomes:

```text
filesystem event / explicit index --file
        ↓
canonical source owner + owner lock domain
        ↓
secure open and immutable source observation
        ↓
CG-1 candidate build → stage → cold validate
        ↓
reacquire owner lock
        ↓
mandatory current-source hash check + expected-active check
        ↓
first cutover fence if needed
        ↓
durable pointer publication
        ↓
serving; previous generation retained
```

CG-1 already binds `source_hash` into the generation manifest, but its public
promotion API permits an optional candidate revalidator. CG-2 requires source
freshness to be structurally mandatory on the production **forward** promotion
path:

- candidate construction reads from one securely opened file object or private
  byte snapshot;
- the manifest's existing `source_hash` represents those exact bytes;
- immediately before publication and while holding the owner lock, production
  code securely reopens the canonical source and recomputes the content hash;
- mismatch or disappearance refuses promotion and queues a rebuild;
- the production import/call boundary is statically enforced so callers cannot
  invoke pointer publication without the source check.

This closes a race distinct from CG-1's generation CAS:

```text
candidate built from S0 → source becomes S1 → active pointer unchanged
```

CG-1 catches stale active generations; CG-2 must also catch stale source bytes
on **forward** publication. The architecture does not claim to prevent a source
edit immediately after the final check; that edit is a new desired source state.
Convergence does not rely on delivery of one filesystem notification.

### 7.0 Design A — first-cutover rollback bootstrap (`G_rb`)

**Problem:** On a first owner canary today, `previous_generation_id` would be
`None`, so generation-switch rollback cannot name a committed prior generation.
Design A forbids proceeding with that gap.

**`G_rb` definition:** Exact convert of the accepted pre-cutover LEGACY serving
set for the named owner under a **ratified convert-v1** pipeline fingerprint
(example name: `convmem/cg2-rollback-baseline-convert-v1` or equivalent
ratified string). Distinct from ordinary live-source rebuild fingerprints.
Deterministic under CG-1 `make_generation_id` (no random salt required when the
fingerprint and convert inputs are exact).

**Before fence / before V8c activation grant — both generations exact:**

1. Build and cold-qualify **`G_rb`** (manifested, embedding-proven, retained as
   `RETAINED_ROLLBACK_BASELINE`, grant-bound).
2. Build and cold-qualify the **exact** first-canary generation **`G_canary`**
   (manifested, embedding-proven, pipeline fingerprint, source hash, and
   qualification evidence bound into the activation packet).

There is **no** “fill `G_canary` at cutover” path and **no** post-grant packet
amendment to discover the target. Ryan issues the one-shot activation grant
only after both IDs and both manifest SHA-256 digests are already in the packet.

**Dedicated first cutover:** `publish_first_cutover_active_pointer` with:

- `expected_active_generation_id = None` (CAS against no current pointer);
- durable `previous_generation_id = G_rb`;
- target generation = exact grant-bound `G_canary`;
- structural revalidation that `G_rb` still matches the grant-bound baseline
  (generation id, manifest SHA, convert-v1 fingerprint, retained/qualified
  evidence). Failure → **pause / refuse**; no fence, no pointer, no activation.

**One-shot grant self-invalidation:** If source bytes, current authority, or
preconditions change after the grant but before successful first-cutover
publication, forward/first-cutover publication **refuses**. That grant is
stale/unused. A fresh evidence packet and a **new** Ryan V8c grant are required.
V8c PASS never means a refused operation nevertheless completed.

**Semantics split (papered; not marked PASS here):**

- **V8c PASS** = Ryan accepted the complete first-owner packet (including exact
  `G_rb` + exact `G_canary`) and issued the exact one-shot first-owner
  activation grant.
- **Canary completion** = separate later evidence record and Ryan decision.

Ordinary later forward promotions continue to use `publish_active_pointer` with
mandatory source freshness. Generation-switch restore uses
`rollback_active_pointer` (§6.3).

### 7.1 Notifications schedule work; reconciliation proves convergence

Filesystem notifications are scheduling hints, not source-of-truth change
records. Linux inotify queues can overflow, events can be coalesced, and rename
pairs are not an atomic or necessarily consecutive observation. The current
watcher therefore cannot be the sole mechanism that discovers source drift.

CG-2 adds a bounded source reconciler that securely compares the current source
inventory/observation with the active manifest for generational owners and the
recorded processed source observation for legacy owners. A mismatch, missing
source, new eligible source, or unresolved rename enqueues the latest desired
owner state through the same bounded admission path. Reconciliation is
mandatory:

- at watcher startup and restart;
- after any surfaced `IN_Q_OVERFLOW` or equivalent backend uncertainty;
- after a watch root is rebuilt, moved, mounted over, or reattached;
- periodically at a measured, ratified cadence;
- before an owner is declared clean for canary or legacy retirement.

The baseline convergence strategy does **not** depend on watchdog exposing
`IN_Q_OVERFLOW`: an independent periodic reconciler must visit every eligible
owner within a ratified finite `max_reconciliation_staleness`. Startup and
observer restart request an immediate sweep; the periodic schedule still runs
when the observer appears healthy. A surfaced raw overflow signal may mark a
scope dirty and accelerate its sweep, but no raw inotify side channel is
required for the first activation slice and no missing signal can suppress the
periodic proof.

Reconciliation-required state remains observable until the affected scope
completes a successful sweep; restarting the observer alone does not clear it.
The forced-loss gate suppresses or overflows notifications, mutates a source,
and proves that the independent sweep discovers and queues/quarantines the
mismatch before `max_reconciliation_staleness`. It does not assert that
watchdog reports an overflow event. The execution plan must bound scan cadence,
work admission, and source hashing cost without using unbounded bulk indexing.

Deletes and canonical renames are discovered by inventory difference and enter
the explicit retirement/migration policy in §8; they are never inferred solely
from pairing two watcher events.

## 8. Path identity, aliases, and rename

CG-1's owner key is path-derived and manifest validation enforces it. CG-2 will
not silently replace that identity contract.

### Decision: rename is explicit owner migration

- Lexical aliases and supported symlinks may resolve to the same canonical
  owner before enrollment.
- A canonical-path rename creates a new owner key.
- Transparent rename continuity is implemented, if needed, as an explicit
  old-owner → new-owner migration with ordered owner locks and a durable
  retirement record.
- The old owner remains serving until the new candidate is cold-validated and
  promotable; CG-1 qualification remains structurally bound to publication.
- The migration then fences the new owner, retires the old owner from the
  request authority vector, and publishes the new pointer. A crash after the
  new fence but before old-owner retirement leaves the old owner serving; a
  crash after retirement but before new-pointer publication yields temporary
  unavailability; recovery after publication admits only the new owner. No
  **newly resolved** request-authority vector admits both owners.
- A request frozen before old-owner retirement may finish against retained old-
  owner rows while a later request resolves the new owner. Physical/read-side
  overlap is intentional multiversion behavior, not duplicate serving authority.
- Rename migration is excluded from the first canary. Alias ambiguity blocks
  canary selection.

Device/inode observations may detect that two locators currently name one
filesystem object, but `(st_dev, st_ino)` is not durable semantic identity. A
hardlink collision is quarantined for explicit disposition.

### Path-opening contract

On Linux, authority-critical opens are relative to a trusted corpus-directory
file descriptor and use `openat2`-style resolution restrictions where the
deployment policy permits. The architecture requires an explicit policy for:

- symlinks;
- mount/bind-mount traversal;
- sources outside registered corpus roots;
- portable platforms without `openat2`.

`Path.resolve()` remains identity normalization; it is not treated as a
TOCTOU defense.

## 9. Logical identity and truthful health accounting

### 9.1 Namespaced identity

For file-derived committed rows, semantic comparison uses:

```text
(owner_digest, collection/projection kind, logical_id)
```

`ledger_id` remains the semantic key for governed ledger projections where the
existing contract already establishes it. Physical IDs remain diagnostic
addresses only.

### 9.2 Generation-aware drift

For each active manifest:

```text
M = expected namespaced logical keys in the manifest
P = observed namespaced logical keys in the exact active Chroma projection

missing      = M - P
unexpected   = P - M
completeness = |M ∩ P| / |M|       (empty-set convention specified in execution)
purity       = |M ∩ P| / |P|       (empty-set convention specified in execution)
```

Doctor reports separately:

- missing active logical rows;
- unexpected active logical rows;
- duplicate logical rows;
- wrong-owner and wrong-generation rows;
- unqualified pointer/manifest authority failures;
- retained inactive rows;
- abandoned rows;
- physical storage amplification.

Retained historical generations are not drift. An invalid pointer is not a low
percentage; it is an authority failure.

### 9.3 Serving versus physical statistics

Every count surface labels one of two views:

- **serving:** stable-governed rows plus legacy-authorized rows plus exact active
  generation rows under the request authority vector;
- **physical:** all stored rows, inactive generations, abandoned rows, and WAL/
  segment diagnostics.

MCP `stats` must not label a raw physical count as corpus serving size.

### 9.4 Fitness-function ownership

Each gate has one owner and one stated bad outcome:

| Property | Authoritative gate | Bad outcome prevented |
|---|---|---|
| Serving authority | `generation_authority` | Unqualified or ambiguous rows serve |
| Logical membership | `logical_projection` | Missing/extra/duplicate active semantics are hidden |
| Export parity | `projection_parity` | Physical churn is mistaken for semantic change |
| Direct-read boundary | static inventory test | A serving surface bypasses authority |
| Alias/path integrity | alias/path gate | One locator maps ambiguously or escapes policy |
| Source convergence | reconciliation freshness gate | A lost watcher event leaves active source state stale indefinitely |
| Chroma backlog/recovery | operational probe | Generation churn makes restart or disk growth unbounded |
| Performance | representative benchmark | Correctness path becomes operationally unusable |

Doctor may compose these checks, but duplicate scripts may not invent different
thresholds for the same property.

Operational output records authority-resolution retries, reconciliation-
required scopes, overflow/observer-failure counts, last successful reconcile
time and duration, source mismatches enqueued/quarantined, mixed-mode safety
rejections, authorized underfill, and control-view retrieval divergence.

## 10. Backpressure, retention, and reclamation

### 10.1 Initial activation policy

Automatic physical deletion is disabled for the global gateway soak and first
owner canary. Preserve:

- active generation (`G_canary` after first cutover);
- Design A retained rollback baseline `G_rb` (`RETAINED_ROLLBACK_BASELINE`);
- immediately previous committed generation after later promotions;
- in-flight candidate;
- abandoned candidate until explicit inspection/cleanup;
- all legacy rows during the canary evidence window.

**First-canary window (Design A):** After successful first-cutover publication,
**no further serving promotion** of that owner (no second forward
`publish_active_pointer` / no second canary generation) until the canary
window closes under a separate Ryan decision. GC remains disabled. Promotion
and reclamation remain separate operations. This adopts RCU's useful
removal/reclamation split without claiming kernel RCU semantics.

### 10.2 Admission control

CG-2 requires bounded work rather than using memory, Chroma, or disk as an
implicit queue:

- one executing build per owner;
- at most one coalesced “latest desired source state” pending per owner;
- bounded global runnable builds and embedders;
- CG-1's one-unresolved-abandoned-generation owner guard;
- projected disk-headroom admission before staging;
- soft and hard inactive-row/storage-amplification limits;
- Chroma backlog and cold-reopen limits;
- observable refusal and retry state at hard limits.

The default product semantics converge to the latest observed source state;
ConvMem does not preserve every intermediate file edit. Changing that policy is
a separate product decision.

### 10.3 Online GC gate

Naive epoch reclamation is rejected because a dead process can pin reclamation
indefinitely. Online GC is a later sub-gate requiring either:

- proven maintenance quiescence, or
- crash-aware, expiring reader leases that distinguish process instances and
  cannot be held forever by PID reuse or process death.

A generation is GC-eligible only when it is not active, previous/rollback-
protected, candidate-protected, operator-held, recovery-held, or visible to a
live request pin. Chroma row deletion, WAL effects, and physical compaction are
separate measured operations.

Online GC must also close the resolve-then-pin race. Before dereferencing any
generation or retirement-protected legacy rows, a reader must either establish
its pin atomically with authority resolution or:

1. resolve a tentative authority target;
2. establish a pin for that exact target;
3. revalidate the authority evidence;
4. release and retry if the evidence changed;
5. dereference rows only after successful revalidation.

GC cannot reclaim a target between tentative resolution and a validated pin.
The formal model must cover this interleaving before online deletion is
admitted. Linux pidfds are a candidate future process-instance primitive that
avoids ordinary PID-reuse races, but they do not replace durable lease expiry,
reboot reconciliation, or the pin protocol.

No execution plan may add direct SQL/WAL deletion as generation GC.

## 11. Failure behavior

| Failure | Required behavior |
|---|---|
| Parser, embedding, LLM, or staging failure | Candidate fails/abandons; current authority unchanged |
| Process crash before pointer publication | Candidate remains non-authoritative |
| Crash after first-cutover fence, before pointer | Owner unavailable; legacy cannot resurrect; fence monotonic |
| Crash after pointer bytes, before caller observes success | Exact recovery/qualification decides; no fallback |
| Active generation changes during build | Existing CG-1 stale-generation check refuses promotion |
| Source bytes change during forward build/publication | Mandatory source-hash check refuses promotion; queues rebuild |
| First-cutover baseline structural failure (`G_rb`) | Pause / refuse; no fence, no pointer, no activation |
| First cutover would set `previous_generation_id=None` | Refuse; Design A requires exact `G_rb` |
| Grant preconditions stale before first-cutover publish | Refuse; one-shot grant unused/stale; new packet + new V8c grant required |
| Watch event is lost, coalesced, or overflows | Mark scope reconciliation-required; compare source inventory/manifests and enqueue latest drift before clearing |
| Authority evidence changes during resolution | Discard tentative mapping and retry before row dereference |
| Authority resolution exhausts retry budget | Return observable `AUTHORITY_UNSTABLE`; no durable quarantine, cache entry, rows, or fallback |
| Authority/integrity exception reaches serving adapter | Typed repository boundary propagates fail-closed error; adapter cannot choose raw fallback |
| Chroma transaction failure | No pointer publication |
| Pointer/manifest mismatch | Quarantine/fail closed; never elect another generation |
| Raw direct-read bypass discovered | Activation gate fails; affected surface is authority-unsafe |
| Mixed query exceeds proof/performance budget | Observable refusal/degradation; rollout pauses |
| Source alias ambiguity or hardlink collision | Owner is ineligible for cutover |
| Reader races authority change before pin | Pin then revalidate or retry; no row dereference and no GC eligibility until pin is valid |
| Rollback after source advance | May restore retained generation; leave durable reconciliation-required for newer source; never LEGACY |
| GC crash | Active pointer unaffected; deletion resumes or is inspected from explicit state |
| Machine crash/power loss | Preserve CG-1 durability claim; restart qualification fails closed if rows do not match pointer |
| Filesystem corruption | Quarantine and restore from backup evidence; no completeness heuristic |

## 12. Rollout sequence and authorization boundaries

### A0 — architecture

- This document reviewed at one exact SHA.
- Kiro reviews design coherence.
- Crush reviews repository/evidence claims and failure coverage.
- Cursor reviews implementation feasibility without implementing.
- Codex resolves material findings and produces the bounded TLA+/PlusCal model
  (or an equivalently exhaustive transition model) against the settled state
  machine.
- Reviewers confirm the architecture and model describe the same revision.
- Ryan either requests revision or locks architecture.

### A1 — execution planning

After architecture lock, Codex writes the execution and verification plans with
exact file ownership, slices, gates, rollback, and reviewer sequence. Planning
does not authorize implementation.

### A2 — global repository implementation, no activation

- Add the serving repository and frozen authority view.
- Route all serving surfaces through it.
- Keep every owner `LEGACY`.
- Eliminate all `cg2-production-bypass` classifications.
- Separate serving and physical statistics.

### A3 — identity, accounting, and promotion guards

- Add monotonic fence and owner authority resolution.
- Add mandatory production source-hash revalidation.
- Add startup/overflow/periodic source reconciliation and its freshness gate.
- Make drift/parity logical and generation-aware.
- Add bounded admission/backlog/storage diagnostics.
- Keep automatic GC disabled.

### A4 — offline and copied-corpus verification

- Unit, integration, concurrency, path-race, crash, and accounting matrices.
- Representative-scale mixed-mode query spike against an authority-clean Chroma
  control view, with safety/cardinality/quality reported separately.
- Pinned Chroma 1.5.9 backlog, replay, delete, and storage-amplification probes.
- Re-run the architecture-locked formal model and map implementation tests to
  its transitions/invariants (§13).

### A5 — production legacy-only gateway soak

Requires its own exact operation grant. All owners remain legacy. Evidence must
show query equivalence, zero bypasses, acceptable latency, and observable
fallback taxonomy.

### A6 — one-owner canary (Design A)

Requires a separate **one-shot** activation grant naming:

- exact implementation SHA;
- exact owner / source path;
- exact `G_rb.generation_id` + `G_rb.manifest_sha256` (convert-v1, cold-qualified,
  `RETAINED_ROLLBACK_BASELINE`);
- exact `G_canary.generation_id` + `G_canary.manifest_sha256` (already built and
  cold-qualified **before** the grant);
- exact source hashes, production pipeline fingerprints, and embedding provenance
  for both generations;
- qualification evidence and independent review packet;
- operation = first-cutover fence + `publish_first_cutover_active_pointer` only.

The grant is **self-invalidating**: if source, current authority, or
preconditions change before successful publication, the operation refuses and a
**new packet + new V8c grant** are required. V8c PASS does not imply a refused
cutover completed.

**V8c PASS (definition only — not issued by this architecture papering):**
complete first-owner packet accepted + exact one-shot activation grant issued.

**Canary completion:** separate later evidence record and Ryan decision — not
implied by V8c PASS.

The owner must have no alias ambiguity, known embedding identity, modest size,
and exact logical parity. Automatic GC and rename migration remain off. During
the first-canary window, no further serving promotion of that owner.

### A7 — bounded owner batches

Each batch is named and pauses automatically on authority, parity, storage,
backlog, recovery, or performance gate failure.

### A8 — reclamation and legacy retirement

Online GC is independently reviewed and enabled only after read-pin and Chroma
deletion evidence. Legacy serving code is removed only after every intended
owner is generational, rollback no longer depends on legacy rows, and the
accepted soak window has zero fallback events.

## 13. Required evidence before first generational canary

The activation packet must bind all evidence to one tested/reviewed
implementation SHA, and must already contain **exact** `G_rb` and **exact**
`G_canary` (IDs + manifest SHA-256 + source hashes + pipeline fingerprints +
embedding provenance + qualification evidence) **before** Ryan issues the V8c
activation grant. No post-grant packet amendment to discover either target.

1. Full repository and focused CG-2 suites pass with no unexplained failures.
2. Independent architecture and implementation reviews PASS the same revision.
3. All four current production bypass classifications are eliminated, every
   serving-adjacent Chroma/SQLite helper and fallback is mediated or explicitly
   non-serving, and the inventory fails loudly on empty discovery.
4. The read-boundary inventory works from normal, `/tmp`, and hidden-parent
   worktree paths; the CG-1 hidden-parent discovery weakness is fixed.
5. Legacy-only gateway soak meets ratified correctness and latency budgets.
6. Mixed-mode verification separately proves absolute authority safety,
   authorized cardinality against an authority-clean Chroma 1.5.9 control view,
   and ratified retrieval-quality divergence. Adversarial cases place inactive
   or fenced rows nearest to the query; exact cosine is diagnostic only.
7. Logical completeness, purity, duplicate, wrong-owner, wrong-generation, and
   parity fixtures all receive distinct truthful diagnoses.
8. Candidate source changes before **forward** promotion are refused.
9. Startup, watcher restart, forced event loss/overflow, rename-pair disruption,
   and the watchdog-independent periodic sweep all converge current source
   observations to queued/quarantined desired state within ratified
   `max_reconciliation_staleness`; stale reconciliation health blocks canary.
10. Concurrent fence/pointer/retirement changes force authority-resolution
    retry; pointer is rechecked last; both retry limits terminate in observable
    `AUTHORITY_UNSTABLE`; tests distinguish pre-fence frozen readers from post-
    fence resolutions and reject torn rename-linked vectors.
11. Pointer/fence/source-path crash injection passes every transition. A real
    child-process kill during first-cutover / forward publication is followed by
    fresh recovery proving that the exact durable authority is honored and both
    the active and immediate-previous (`G_rb`) generation rows remain physically
    intact and exact-generation readable.
12. Alias ambiguity and hardlink collision block owner eligibility.
13. Embedding model/dimension provenance is known for **both** `G_rb` and
    `G_canary`.
14. Recent ingest-degraded evidence affecting the owner is reconciled.
15. Pinned Chroma 1.5.9 tests bound WAL/backlog, vector persistence lag,
    cold-reopen replay, repeated generation churn, delete behavior, and physical
    storage amplification.
16. **Design A rollback drill:** `rollback_active_pointer` restores exact `G_rb`
    through fresh qualification; when source has advanced, reconciliation-
    required remains durable; fence stays monotonic; never LEGACY. Separate
    tests prove `recover_active_pointer` cannot switch generations.
17. Numeric p50/p95/p99 read, build, qualification, promotion-lock, recovery,
    queue, and storage budgets are measured and ratified. No percentage in this
    architecture is a substitute for baseline evidence.
18. A TLA+/PlusCal model or equivalently reviewable exhaustive transition model
    checks at least these safety properties (carry forward existing CG-2 formal
    evidence; Design A requires the following **additional** properties to be
    modeled/tested before first canary Execute closes):
    - only a qualified pointer target serves a generational owner;
    - at most one generation serves per owner;
    - an owner resolution linearized after the fence cannot resolve legacy;
    - a pre-fence frozen reader may finish while retained legacy rows are protected;
    - active/source stale checks prevent **forward** promotion;
    - first-cutover refuses unless grant-bound `G_rb` structurally validates and
      durable `previous_generation_id` is exactly that `G_rb` (never `None`);
    - `rollback_active_pointer` may restore retained generation after source
      advance while leaving reconciliation-required; never resurrect LEGACY;
    - `recover_active_pointer` never changes generation identity;
    - during the first-canary window, no second serving promotion of that owner;
    - under a stated fair-reconciler assumption, lost notification state cannot
      remain the only record of source drift: reconciliation queues or
      quarantines an observed source/manifest mismatch;
    - recovery never changes pointer choice by completeness;
    - GC never selects an active/protected/pinned/`RETAINED_ROLLBACK_BASELINE`
      generation;
    - no target is reclaimed between tentative resolution and a validated pin;
    - rename migration never admits old and new owners to one newly resolved
      vector;
    - one request never changes its frozen owner generation mid-request;
    - authority resolution terminates within the finite attempt bound and
      produces terminal `AUTHORITY_UNSTABLE` refusal on exhaustion;
    - a one-shot activation grant whose preconditions are stale refuses
      publication without completing cutover.

    The executable model and three property-focused lock configurations live
    under `docs/plans/formal/cg2/`. They were exhaustively checked on 2026-08-14
    with checksum-verified TLA+ v1.7.4 / TLC 2.19 (`5a47802`) using a 2 GiB heap
    and two workers. The cutover, stale/reconcile/recovery, and rename/pinning
    instances generated 123,281 states in total (38,134 distinct across the
    three independent graphs), exhausted every queue, and reported zero
    errors. Action coverage was nonzero for retry exhaustion, typed fallback,
    stale rejection, reconciliation, recovery, eligible GC, rename begin/
    retirement, torn-vector refusal, and both legacy and generation reads.
    This is architecture evidence only; Design A properties above are
    **newly required** and are not claimed PASS by the 2026-08-14 run.
    Implementation must later refine these transitions and map tests to them.
19. Ryan issues a separate one-shot production activation grant naming exact
    resource, operation, owner, final value/state, exact `G_rb`, and exact
    `G_canary`. Grant is self-invalidating on precondition change before
    publication (§7.0 / A6). **V8c PASS** means packet accepted + grant issued;
    canary completion is a separate later Ryan decision.

## 14. Scope fences and rejected mechanisms

CG-2 does not authorize:

- corpus-wide transactions, Snapshot Isolation, or serializability claims;
- distributed consensus or microservices;
- a second source of serving-generation truth;
- permanent opportunistic legacy fallback;
- heuristic “most complete” recovery;
- changing CG-1 owner identity to an unrelated stable-ID scheme;
- automatic hardlink owner merging;
- naive epoch-based reclamation;
- a full Merkle object graph without a measured partial-validation need;
- direct Chroma WAL/SQLite surgery;
- Chroma/SQLite durability pragma changes;
- Shadow Ledger activation;
- automatic GC in the first canary;
- transparent rename migration in the first canary;
- implementation before Architecture and Execution HITL.

## 15. Literature and authoritative references

The references support principles, not product guarantees:

- Berenson et al., [A Critique of ANSI SQL Isolation Levels](https://www.microsoft.com/en-us/research/publication/a-critique-of-ansi-sql-isolation-levels/) — multiversion snapshots are useful, but Snapshot Isolation is a specific database contract ConvMem does not claim.
- Linux kernel documentation, [What is RCU?](https://docs.kernel.org/RCU/whatisRCU.html) — publication/removal and reclamation are separate phases.
- Linux man-pages, [inotify(7)](https://man7.org/linux/man-pages/man7/inotify.7.html) — queues can overflow and lose events; robust consumers reconcile/rebuild rather than treating notifications as a complete change ledger.
- Linux kernel documentation, [sequence counters and sequential locks](https://docs.kernel.org/locking/seqlock.html) — read/copy/revalidate/retry motivates torn-evidence detection; ConvMem does not adopt kernel seqlocks as durable authority.
- Trevor Brown, [Reclaiming Memory for Lock-Free Data Structures](https://www.cs.toronto.edu/~tabrown/debra/fullpaper.pdf) — classic EBR can stop reclaiming when a participant sleeps or crashes.
- Git, [update-ref](https://git-scm.com/docs/git-update-ref) — conditional ref updates validate the expected old value before publication.
- OSTree, [Anatomy of an OSTree repository](https://ostreedev.github.io/ostree/repo/) — immutable content-addressed objects plus small mutable refs.
- Linux man-pages, [openat2(2)](https://man7.org/linux/man-pages/man2/openat2.2.html) — handle-relative resolution and `RESOLVE_*` containment controls.
- SQLite, [PRAGMA synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous) and [Atomic Commit](https://www.sqlite.org/atomiccommit.html) — durability depends on journal mode, synchronization, filesystem assumptions, and directory persistence.
- Rollins et al., [Online, Asynchronous Schema Change in F1](https://www.vldb.org/pvldb/vol6/p1045-rae.pdf) — mixed-version transitions require explicit compatible states; ConvMem adapts the discipline, not F1's distributed machinery.
- TLA+ Foundation, [TLA+ tools](https://github.com/tlaplus/tlaplus) and Lamport's [TLA+ tools overview](https://lamport.org/tla/tools.html) — executable state models can check bounded safety/liveness properties.
- Patel et al., [ACORN](https://arxiv.org/abs/2403.04871) — filtered HNSW has predicate-dependent recall/performance behavior, supporting separate authority-safety, cardinality, and retrieval-quality gates.
- Chroma documentation, [collection HNSW configuration](https://docs.trychroma.com/docs/collections/configure), the source repository's pinned [1.5.9 release](https://github.com/chroma-core/chroma/releases/tag/1.5.9), and upstream operational report [`#7463`](https://github.com/chroma-core/chroma/issues/7463) — the report motivates replay-cost probes but implementation-specific behavior still requires local evidence.
- Python documentation, [`os.pidfd_open`](https://docs.python.org/3/library/os.html#os.pidfd_open) — pidfds are a future Linux process-instance primitive to investigate for leases, not a complete durable reclamation design.

## 16. Reviewer questions and exit condition

Reviewers should answer explicitly:

1. Does explicit old-owner → new-owner migration correctly preserve CG-1's
   path-derived identity, or is reopening that contract justified?
2. Can the mixed-mode query path prove authority safety and authorized
   cardinality against the authority-clean Chroma control while measuring ANN
   quality separately and staying within ratified cost?
3. Is the monotonic fence + pointer sequence the smallest correct first-cutover
   state machine?
4. Is source-hash revalidation structurally unavoidable on every production
   promotion path?
5. Do any production, fallback, exact-lookup, evidence, count, restore, or MCP
   paths remain outside the proposed serving repository classification?
6. Are activation and reclamation separated strongly enough?
7. Which symlink/mount policy should be locked for the actual Linux deployment?
8. Does source reconciliation close startup, restart, overflow, rename, and
   periodic lost-event cases without creating unbounded indexing work?
9. Do authority-resolution and future pin linearization permit pre-cutover
   readers to finish while preventing post-fence legacy resolution and
   resolve-before-pin reclamation?

Architecture exits only when Kiro/Crush/Cursor reviews target the same
architecture/model revision and Ryan locks that revision. The next artifact is
an execution plan; no production activation follows directly from this document.
