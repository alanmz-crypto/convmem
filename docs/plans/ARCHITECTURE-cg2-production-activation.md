# Architecture Direction — CG-2 production activation

> **DRAFT — architecture review only (2026-08-14).** This document does not
> authorize implementation, production configuration, corpus mutation, owner
> cutover, garbage collection, or activation. CG-1 remains the only locked
> committed-generation contract. CG-2 requires Kiro/Crush/Cursor review and Ryan
> Architecture HITL before execution planning.

**Source:** Codex synthesis of the merged CG-1 implementation and closure
evidence, the ChatGPT CG-2 advisory research memo, ConvMem builder-reference
guidance, and primary literature listed in §15.

**Reviewed CG-1 stabilization:**
`2ed229244ea1d7cdf9a83630ad56d5a194426826`

**Problem:** Activate CG-1's committed-generation substrate in production
without allowing legacy rows, inactive generations, stale source bytes, raw
Chroma reads, or premature reclamation to become serving authority.

## 1. Planning status and product goal

| Field | Value |
|---|---|
| Phase | Architecture Planning |
| Product goal | Failed or interrupted reindexing can never corrupt the corpus that ConvMem serves |
| This arc | Move CG-1 from hermetic substrate to bounded production use |
| Author | OpenAI Codex |
| Research input | ChatGPT advisory memo; external claims rechecked before inclusion |
| Review lanes | Kiro design review; Crush evidence/risk review; Cursor implementation feasibility review |
| Authority | Draft only; awaiting Ryan Architecture HITL |
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

The ChatGPT memo referred to a specific open Chroma 1.5.9 issue. That exact
issue could not be independently located during synthesis, so it is **not** an
architecture fact. Chroma's WAL, brute-force buffer, HNSW sync threshold, and
replay model are documented; pinned-version behavior remains an empirical CG-2
gate (§13).

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
| Mixed-mode query cannot prove top-k within budget | Observable degraded/error result; no raw fallback |
| Quarantined owner | Exclude only if the API contract permits partial multi-owner results and names the exclusion; otherwise fail the request |

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
```

`GC_ELIGIBLE` is a proved state, not a synonym for inactive.

### 6.3 Rollback

Normal rollback never resurrects legacy rows. It:

1. selects the exact retained previous committed generation;
2. reruns mandatory fresh-process qualification;
3. acquires the owner lock;
4. republishes it through the CG-1 authority path with the expected active generation;
5. records the former active generation as retained history.

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
freshness to be structurally mandatory on the production promotion path:

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

CG-1 catches stale active generations; CG-2 must also catch stale source bytes.
The architecture does not claim to prevent a source edit immediately after the
final check; that edit is a new event and converges through the next generation.

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
  interval admits both owners.
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
| Chroma backlog/recovery | operational probe | Generation churn makes restart or disk growth unbounded |
| Performance | representative benchmark | Correctness path becomes operationally unusable |

Doctor may compose these checks, but duplicate scripts may not invent different
thresholds for the same property.

## 10. Backpressure, retention, and reclamation

### 10.1 Initial activation policy

Automatic physical deletion is disabled for the global gateway soak and first
owner canary. Preserve:

- active generation;
- immediately previous committed generation;
- in-flight candidate;
- abandoned candidate until explicit inspection/cleanup;
- all legacy rows during the canary evidence window.

Promotion and reclamation are separate operations. This adopts RCU's useful
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

No execution plan may add direct SQL/WAL deletion as generation GC.

## 11. Failure behavior

| Failure | Required behavior |
|---|---|
| Parser, embedding, LLM, or staging failure | Candidate fails/abandons; current authority unchanged |
| Process crash before pointer publication | Candidate remains non-authoritative |
| Crash after first-cutover fence, before pointer | Owner unavailable; legacy cannot resurrect |
| Crash after pointer bytes, before caller observes success | Exact recovery/qualification decides; no fallback |
| Active generation changes during build | Existing CG-1 stale-generation check refuses promotion |
| Source bytes change during build | Mandatory source-hash check refuses promotion |
| Chroma transaction failure | No pointer publication |
| Pointer/manifest mismatch | Quarantine/fail closed; never elect another generation |
| Raw direct-read bypass discovered | Activation gate fails; affected surface is authority-unsafe |
| Mixed query exceeds proof/performance budget | Observable refusal/degradation; rollout pauses |
| Source alias ambiguity or hardlink collision | Owner is ineligible for cutover |
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
- Make drift/parity logical and generation-aware.
- Add bounded admission/backlog/storage diagnostics.
- Keep automatic GC disabled.

### A4 — offline and copied-corpus verification

- Unit, integration, concurrency, path-race, crash, and accounting matrices.
- Representative-scale mixed-mode query spike.
- Pinned Chroma 1.5.9 backlog, replay, delete, and storage-amplification probes.
- Bounded formal state model (§13).

### A5 — production legacy-only gateway soak

Requires its own exact operation grant. All owners remain legacy. Evidence must
show query equivalence, zero bypasses, acceptable latency, and observable
fallback taxonomy.

### A6 — one-owner canary

Requires a separate activation grant naming exact SHA, owner, source path,
accepted previous state, rollback generation, and evidence packet. The owner
must have no alias ambiguity, known embedding identity, modest size, and exact
logical parity. Automatic GC and rename migration remain off.

### A7 — bounded owner batches

Each batch is named and pauses automatically on authority, parity, storage,
backlog, recovery, or performance gate failure.

### A8 — reclamation and legacy retirement

Online GC is independently reviewed and enabled only after read-pin and Chroma
deletion evidence. Legacy serving code is removed only after every intended
owner is generational, rollback no longer depends on legacy rows, and the
accepted soak window has zero fallback events.

## 13. Required evidence before first generational canary

The activation packet must bind all evidence to one tested/reviewed SHA:

1. Full repository and focused CG-2 suites pass with no unexplained failures.
2. Independent architecture and implementation reviews PASS the same revision.
3. All four current production bypass classifications are eliminated; no new
   serving bypass exists.
4. The read-boundary inventory works from normal, `/tmp`, and hidden-parent
   worktree paths; the CG-1 hidden-parent discovery weakness is fixed.
5. Legacy-only gateway soak meets ratified correctness and latency budgets.
6. Mixed-mode top-k proof passes adversarial cases where the nearest physical
   rows are inactive or fenced.
7. Logical completeness, purity, duplicate, wrong-owner, wrong-generation, and
   parity fixtures all receive distinct truthful diagnoses.
8. Candidate source changes before promotion are refused.
9. Pointer/fence/source-path crash injection passes every transition.
10. Alias ambiguity and hardlink collision block owner eligibility.
11. Embedding model/dimension provenance is known for the canary generation.
12. Recent ingest-degraded evidence affecting the owner is reconciled.
13. Pinned Chroma 1.5.9 tests bound WAL/backlog, vector persistence lag,
    cold-reopen replay, repeated generation churn, delete behavior, and physical
    storage amplification.
14. Rollback to the exact previous generation is drilled through fresh
    qualification.
15. Numeric p50/p95/p99 read, build, qualification, promotion-lock, recovery,
    queue, and storage budgets are measured and ratified. No percentage in this
    architecture is a substitute for baseline evidence.
16. A TLA+/PlusCal model or equivalently reviewable exhaustive transition model
    checks at least these safety properties:
    - only a qualified pointer target serves a generational owner;
    - at most one generation serves per owner;
    - legacy cannot serve after the fence;
    - active/source stale checks prevent promotion;
    - recovery never changes pointer choice by completeness;
    - GC never selects an active/protected/pinned generation;
    - one request never changes its frozen owner generation mid-request.
17. Ryan issues a separate one-shot production activation grant naming exact
    resource, operation, owner, and final value/state.

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
- Trevor Brown, [Reclaiming Memory for Lock-Free Data Structures](https://www.cs.toronto.edu/~tabrown/debra/fullpaper.pdf) — classic EBR can stop reclaiming when a participant sleeps or crashes.
- Git, [update-ref](https://git-scm.com/docs/git-update-ref) — conditional ref updates validate the expected old value before publication.
- OSTree, [Anatomy of an OSTree repository](https://ostreedev.github.io/ostree/repo/) — immutable content-addressed objects plus small mutable refs.
- Linux man-pages, [openat2(2)](https://man7.org/linux/man-pages/man2/openat2.2.html) — handle-relative resolution and `RESOLVE_*` containment controls.
- SQLite, [PRAGMA synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous) and [Atomic Commit](https://www.sqlite.org/atomiccommit.html) — durability depends on journal mode, synchronization, filesystem assumptions, and directory persistence.
- Rollins et al., [Online, Asynchronous Schema Change in F1](https://www.vldb.org/pvldb/vol6/p1045-rae.pdf) — mixed-version transitions require explicit compatible states; ConvMem adapts the discipline, not F1's distributed machinery.
- TLA+ Foundation, [TLA+ tools](https://github.com/tlaplus/tlaplus) and Lamport's [TLA+ tools overview](https://lamport.org/tla/tools.html) — executable state models can check bounded safety/liveness properties.
- Chroma documentation, [collection HNSW configuration](https://docs.trychroma.com/docs/collections/configure) and the source repository's pinned [1.5.9 release](https://github.com/chroma-core/chroma/releases/tag/1.5.9) — implementation-specific backlog/replay claims still require local evidence.

## 16. Reviewer questions and exit condition

Reviewers should answer explicitly:

1. Does explicit old-owner → new-owner migration correctly preserve CG-1's
   path-derived identity, or is reopening that contract justified?
2. Can the mixed-mode query algorithm prove semantic top-k under Chroma 1.5.9
   without an unacceptable full-corpus scan?
3. Is the monotonic fence + pointer sequence the smallest correct first-cutover
   state machine?
4. Is source-hash revalidation structurally unavoidable on every production
   promotion path?
5. Do any production, fallback, exact-lookup, evidence, count, restore, or MCP
   paths remain outside the proposed serving repository classification?
6. Are activation and reclamation separated strongly enough?
7. Which symlink/mount policy should be locked for the actual Linux deployment?

Architecture exits only when Kiro/Crush/Cursor reviews target the same revision
and Ryan locks that revision. The next artifact is an execution plan; no
production activation follows directly from this document.
