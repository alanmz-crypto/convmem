# [Arc Codex #286] Reduce incremental commit cost without hiding lost evidence

**Recommendation:** Ship reuse of the duplicate pre-write Chroma digest first,
with phase timing and the post-write full comparison intact. Next externalize
provenance envelopes, then qualify a source-scoped mutation census before
removing the remaining hot-path full digests. Collapse the export passes after
the representation is smaller. Keep option C on hold unless measurements still
justify it. Neither the 60-second commit nor five-second C1 target is proven yet.

**Who / what / when / why / how:** Codex, architecture lane, 2026-10-17. Ryan
accepted Kiro's REDIRECT of the proportional-export design and supplied Claude's
read-only profile. This document replaces that design's implementation
recommendation with staged cost reduction, explicit proof limits and recovery
compatibility requirements. Kiro reviews the direction; Ryan grants subsequent
execution. It does not authorize any implementation or production operation.

**Baseline:** fetched `origin/main` at
`bd379463345b360737b84c9d87d16b854fe265d0`. All code coordinates below refer to
that tree. Prior Codex design: `7af3073`,
`docs/plans/DESIGN-issue-286-proportional-export-commit.md`. Kiro's redirect:
`c8d8700`, `docs/inter-model/KIRO-2026-10-17-issue-286-proportional-export-review.md`
on `docs/2026-10-17-issue-286-proportional-export-review`.

**Planning status:** Architecture Planning; Architect, Systems Thinker, Risk
Reviewer; function Planner. Codex authors, Kiro reviews, Ryan approves. The
accepted redirect authorizes this re-plan, not the proposed proof substitution.
Only this document is delivered. STATUS/LATEST are stale orientation for the
latest canary and remain untouched under the one-document instruction.

## 1. Evidence and scope

Claude measured live data read-only on 2026-10-17, runtime-main `bd37946`, using
a scratch Chroma copy. Ryan supplied these results; Codex has not rerun them:

- One `non_source_inventory_digest`: knowledge units **71.0 s**, 111,348 rows
  including embeddings; conversation summaries **1.9 s**, 5,106 rows.
- Three calls per fresh commit cost approximately **218.7 s**. Against observed
  one-chunk commits of **307–378 s**, this is about **58–71%**, not a precise
  75%. The supplied “~75%” is a useful rough attribution, not an additive trace.
- One streaming parse: **16.7 s**, **5.19 GiB**, **203,441 export rows**.
  `provenance_envelope` accounts for **96.8% of export bytes**, roughly 32 KB
  per measured envelope-bearing row. Removing that field leaves about
  **0.166 GiB / 170 MiB**, before references and serialization overhead: a
  theoretical export-size reduction near **31×**, not a demonstrated 50×.
- The repeatable measurement script is
  `~/.cache/claude-export-profile/profile.sh`; the measurement is in arc memory.
  Future use against live resources needs its own authority. It was not run here.

These are different measurements, not a complete wall-time decomposition.
Subtracting all three scans leaves **88–159 s** of unexplained/remaining time;
subtracting one leaves **234–305 s**. Cache state, Chroma guard saves, filesystem
I/O and measurement overhead prevent treating those arithmetic estimates as
predictions. Smaller export bytes do not imply proportionally faster JSON parse,
fsync or Chroma access. A fresh additive trace is an acceptance requirement.

Startup `doctor` exited 0 with warnings; brief/unresolved were read-only. Doctor
still reported APPLYING transaction `46313d437ae4446282a752270770c614` with
`recovery_unproven` for the Oct 13 Codex rollout. This is a migration blocker
for that source, not authority to repair it. No semantic search was invoked
because it could call an embedding provider. Repository source, the pinned
prior design/review and Ryan's supplied measurement ground this design. No
indexing, provider calls, production changes or implementation tests were run.

Scope: incremental isolation evidence, provenance representation, export pass
cost, duplicate semantics and acceptance. References to Safe Harbor, R2b,
Shadow, CG-2 and Recovery Authority specify compatibility obligations explicitly
requested by Ryan; they do not reopen those arcs or grant their operations.

## 2. What the present isolation checks actually establish

`incremental_jsonl.py:_commit_generation` at 2142 takes source then C1 locks.
At 2167 it captures an attempt-local digest; `_snapshot_before_images` at 1488
captures another digest for the original rollback journal; after apply,
`_verify_non_source_collections` at 1529 compares a fresh digest to the attempt
baseline. Replay retains the original journal but takes a fresh attempt
baseline, so intervening foreign commits are not mistaken for this attempt's
damage. That distinction must survive every optimization.

`chroma_store.py:non_source_inventory_digest` at 763 pages both collections
with documents, embeddings and metadata, excludes rows by exact `source_path`,
and hashes/sorts the rest. Equality is evidence that the API-visible foreign
row set and those fields match at two observation points. It is not an atomic
cross-collection database snapshot, proof of all HNSW bytes, or proof against
a malicious actor able to rewrite the evidence. Without a cooperating writer
boundary, paging itself can observe a changing collection.

The desired guarantee has two meanings that cannot be silently conflated:

1. **Causal isolation:** this admitted commit issued no mutation of a row owned
   by another source, under the supported Chroma API's exact-ID semantics.
2. **Observed physical noninterference:** no foreign API-visible document,
   metadata, vector or row membership changed between the observation points,
   including unexpected backend corruption or a bypass writer.

A source-proportional protocol can establish (1) through complete mediation.
It cannot freshly establish (2) for arbitrary untouched foreign data without
reading it, or trusting a separately maintained backend integrity mechanism.
Keep “this commit changed no non-source row” as the causal contract, with these
assumptions printed in evidence. If Kiro/Ryan require the full current
observation guarantee on every commit, retain full pre/post scans and report
the performance target unmet; a journal is not a substitute for that guarantee.

### 2.1 Alternatives and their exact losses

**Reuse one pre-write digest, retain a separate post-write digest — first slice.**
On a fresh attempt, pass the already captured value into before-image assembly
under the same uninterrupted C1 lock; deep-copy/freeze it. No intervening Chroma
mutation may occur. The rollback journal still records that original value,
and the post-apply comparison remains fresh. Three scans become two, saving
one measured collection pair (~72.9 s). This removes a redundant observation,
not document/vector coverage. It loses the chance to observe out-of-band damage
between two adjacent pre-write samples; neither version guarantees detection
of arbitrary concurrent bypasses. Replays must never replace the original
journal or its hash with a new attempt baseline. A single digest reused as
both “before” and “after” proves nothing about changes and is rejected.

**ID + metadata digest without documents/embeddings — do not substitute.**
With before/after scans it detects ID membership, ownership and metadata changes.
It misses same-ID document/vector changes, and an envelope-heavy metadata scan
still reads substantial data. Omitting envelopes additionally misses envelope
changes unless resolved and hashed. It remains O(all rows). It may be a labeled
diagnostic, never a successful result under today's full-isolation field name.

**Write-session census/journal — chosen eventual hot-path proof, conditional.**
Prevention at the native mutation boundary plus durable attempted/completed
write records establishes the causal property under complete mediation and
backend exact-ID semantics. It can also verify touched source rows. It does
not discover silent corruption in an untouched foreign row, transient foreign
writes later undone outside the boundary, or direct database manipulation.
Approval must explicitly accept this narrower observation coverage.

**Maintained per-collection digest — defer.**
A digest cannot be updated from the old digest alone: retain per-row hashes
and authenticated membership/count/owner structure, then replace touched leaves
under the same write protocol. A Merkle tree gives O(k log N) maintenance, not
strictly O(source rows), and must handle insert/delete/ownership transfer.
For source-exclusion proofs use an owner-partitioned tree or authenticated
foreign-subtree decomposition; equality of the whole collection root is wrong
because owned rows legitimately change. XOR-only aggregates are rejected.
Bootstrap requires a complete verified scan; crashes between Chroma and digest
publication need a durable intent and touched-row reconciliation. An uncertain
or stale root blocks acceptance; it cannot be silently trusted or rebuilt in
the next commit. Every writer, migration and restore must participate. Even a
correctly maintained root commits recorded state; it does not freshly validate
untouched disk contents. This adds another recovery-critical projection while
depending on the same complete-mediation work as the census. Not the first path.

## 3. Proposed source-scoped mutation proof

The proof belongs at `ChromaStore._native` (179), reached through
`chroma_write_store.py`'s admitted production sessions and deny-by-default
`_IndexWriteGuardedChromaStore`. The existing C3 shared writer lease attests a
writer; it is not an exclusive commit lock. The existing native guard serializes
individual native writes and contains segment faults; it does not enforce row
ownership. An after-the-fact Shadow event stream is not a prevention boundary.

Proposed contract, before full digests can be disabled:

1. Mint an internal scoped operation token bound to canonical Chroma target,
   collection identities, exact source string, transaction, attempt, runtime
   protocol and immutable rollback-authority hash. Caller-supplied metadata or
   a public `source_path` argument cannot widen it. Nested sessions inherit the
   scope; a nested unscoped session, background thread or subprocess cannot
   escape it. Unknown mutation methods and collection create/drop/reset refuse.
2. Enumerate the source's actual rows through the existing indexed owner query,
   retaining exact before-images. Expand any delete predicate into explicit
   IDs under serialization. Authorize the union of owned preimage IDs and
   prepared candidate IDs, including derived provenance-selected physical IDs.
   Validate final IDs after dedupe, not just original requested IDs.
3. Under the native guard, immediately before each call, look up every target
   ID. Existing IDs must belong to this source; new IDs must be absent and in
   the bound candidate set. Updates cannot change ownership; supplied metadata
   must retain the exact owner. Foreign ID collisions, ownerless existing rows
   and cross-collection substitution refuse before any call. A foreign exact
   dedupe match may suppress a write; it never becomes authority to modify it.
4. Enforce the scope against the **actual** `ids`/metadata sent to the native
   API, after reload and with ownership check/use inside the same serialization
   interval. No raw collection handle or unrestricted `where` mutation escapes.
   Every production route must already obey C1 or be refused; static call-site
   inventories plus runtime negative tests qualify this, not regex alone.
5. Before each native call, durably append a monotonically sequenced intent
   binding operation, collection, explicit IDs, preimage/candidate hashes and
   scope. After return, record completion and verify expected touched-row state.
   Partial batch outcomes remain “unknown”; reconcile all listed IDs on restart.
   A missing receipt is never evidence that the call did not happen. Keep the
   immutable original rollback journal; attempt receipts are separate evidence.
6. Before checkpoint publication, require a complete census with no denied or
   unknown operation and verified owned post-state. Restore uses the same
   scope against current ownership: if an ID now belongs elsewhere, refuse
   rather than overwrite it. Replay binds a new attempt to the same original
   authority and current owned state; foreign writers between attempts survive.

With fixed row size and O(k) enumerated IDs, added validation/journal bytes are
O(k), where k includes **all source rows plus candidates and attempted writes**,
not just the changed chunk. Indexed database lookup costs and segment-save work
are measured, not claimed constant. If the backend owner query scans all rows,
the implementation fails the scaling gate even though returned data is small.
No global receipt-history read, PID scan or corpus census belongs in each
commit; writer compatibility is a deployment admission prerequisite.

Keep a versioned evidence mode (`full_inventory_v1` versus proposed
`scoped_writes_v1`), collection/owner/attempt binding and measured coverage.
Initially run the census alongside full digests on hermetic fixtures to detect
coverage mistakes. Removing scans is a separate reviewed gate, not the default
effect of merely adding receipts.

### 3.1 Failure and recovery semantics

**`non_source_isolation_changed`:** retain its current meaning for full mode:
observed foreign ID/metadata/document/embedding evidence differed. Scoped mode
must not fabricate `non_source_collections_after` or report that comparison PASS.
Use distinct typed outcomes for a denied foreign write and incomplete census;
only a separately observed mismatch may use the existing changed-state code.
Consumers must branch on evidence mode and refuse an unsupported schema.

**Safe Harbor:** guard validation, retained incident evidence, stale-client
checks, quarantine and recovery authority remain enabled. A segment restoration,
native crash, integrity fault or unknown native outcome invalidates a clean
scoped receipt and routes to existing containment/recovery. A source journal
does not certify an entire segment restored by the guard. Full integrity and
qualified-backup checks remain separately budgeted operations; no claim that
periodic audits restore immediate detection of untouched-row corruption.
New receipts/store paths require explicit StateSpec and affected-path coverage.

**`rollback_export_tamper`:** this is independent of Chroma isolation. Baseline
`_restore_export` (1801) detects unexpected owned export IDs and changed parsed
payloads for preimage IDs, restores exact saved source bytes, and retains current
foreign bytes. It does not compare current foreign bytes to the saved foreign
hash, nor fully authenticate all newly expected IDs against a prepared candidate.
Retain those detection rules, source/transaction/count fields and doctor signal.
Do not describe it as a full export-tamper detector. Receipt optimization must
not remove it. Envelope refs require authenticated hydration for semantic
comparisons while the physical original before-image remains immutable.

## 4. Externalize envelopes without discarding provenance

`provenance_binding.py:validate_projection` (172) currently treats a missing
envelope as untrusted. `enforce_projection_metadata` (276) rejects a malformed
envelope/commitment pair on writes. Removing the field without changing these
contracts would break identity preservation, dedupe and recovery. A commitment
is not a recoverable envelope and is not registry authority.

### 4.1 Side-store contract

Use one local immutable envelope repository keyed by `provenance_commitment`,
behind explicit resolve/store/hydrate operations. Proposed layout under an
admitted data-root member `provenance_envelopes/`: format/store UUID and sharded
commitment directories. Do not silently reuse `provenance/generations`, whose
selector/manifests have Recovery Authority semantics. Reuse its validated
envelopes as input only when their identity/commitment matches; coverage of all
historical envelopes in that registry is not established.

The key uses existing `provenance.py:provenance_commitment` (404), including its
typed validation and canonicalization. It excludes `effective_integrity` and
the embedded commitment. Therefore a commitment alone does **not** uniquely
identify every serialized envelope value. Within each commitment directory,
retain immutable representation variants keyed by a separate SHA-256 over the
typed original value (string versus object included). Store the exact original
string or object value and its variant digest. This preserves legacy envelope
hash semantics and string formatting; do not redefine existing
`provenance_envelope_hash` to mean the commitment or a new byte hash.

A reference row keeps assertion ID, commitment and existing integrity/hash
fields, removes only the envelope value, and adds an explicit versioned ref
containing store UUID and variant digest. The key is derived from a validated
commitment, never an arbitrary filesystem path. Resolver checks containment,
no symlinks, object type/size bounds, UUID, variant hash, typed envelope validity,
recomputed commitment and assertion ID equality. Inline-plus-ref disagreement
is corruption, not “prefer whichever works.” Missing/corrupt refs fail closed
for mutation/recovery; retrieval labels them unavailable/untrusted and must not
collapse distinct identities. No resolver repairs storage or calls providers.

Store canonical envelope identity once and retain required exact variants.
Same-key/different-canonical-content refuses; existing objects are validated,
never overwritten. Write/fsync object and parent before publishing a reference
in Chroma or export. Crash before the reference leaves a harmless retained
orphan; after reference publication every dependency is durable. Bounded caches
are keyed by UUID/commitment/variant, with explicit no-writer/tamper assumptions;
authoritative verification revalidates the bytes it relies on. Self-consistency
still never promotes `effective_integrity`; registry-bound recursive verification
and policy/schema history remain authoritative.

This shrinks hot projection reads, not necessarily total retained bytes. If
every envelope is unique, the side store retains roughly the original envelope
volume plus metadata. Deduplication benefit depends on measured distinct
commitments/variants. GC is out of the initial slice: keep objects reachable from
exports, Chroma, journals, prepared artifacts, capture/recovery bundles, backups
and retained incidents; no per-commit reachability scan.

### 4.2 Closed consumer inventory required before reference publication

The following is a pinned source inventory, including indirect consumers. The
implementation must close aliases/direct opens and regenerate coverage evidence.

1. **Provenance core and Chroma:** `provenance_binding.py`, `provenance.py`,
   `chroma_store.py` add explicit resolver context; keep pure validation free of
   hidden global config/I/O. `projection_metadata`, identity continuity, update
   and restore paths accept both forms. Raw storage snapshots remain distinct
   from hydrated logical rows so scoped hot-path reads do not re-inline everything.
   While full-inventory proof remains selected, its logical envelope comparison
   must resolve and hash referenced values, as well as checking physical metadata.
   Merely hashing refs loses detection of changed side-store contents. That full
   compatibility mode may remain expensive until scoped-proof acceptance.
2. **Ingest and replay:** `ingest.py`, `incremental_jsonl.py`,
   `ingest_dedupe.py`, `inter_model_index.py`, `repository_knowledge_index.py`
   validate hydrated identity before suppression/reuse. New objects precede
   prepared/cache/Chroma/export references. Carry resolver context into exact
   replay; reference representation alone must not change transform identity
   or force paid reprocessing of an unchanged source.
3. **Retrieval and refinement:** `ask.py`, `query.py`, `evidence.py`, `refine.py`
   use provenance identity for grouping, evidence continuity and tombstones.
   Hydrate only needed rows, preserve prior grouping and never collapse unresolved
   references into one trusted identity. Public APIs that promised envelopes
   return hydrated values or an explicit unavailable result.
4. **Decision/observation/verification:** `propose_decision.py` approval recovery
   and `observe.py:export_unit_matches_normalized` compare whole normalized
   rows today. Hydrate both operands and remove only recognized storage-ref
   fields for logical comparison; unknown fields still participate. Keep raw
   preimage hashes for physical authority. Multiple matching `ledger_id` rows,
   malformed export rows, conflicting projections, verified-base replacement
   and `RecoveryCompletionUnknown` remain unchanged. `verify.py` forwards to
   observe and updates Chroma metadata; it is not itself an envelope parser.
   `monitor.py` and CLI/MCP forwarding must preserve the admitted resolver.
5. **R2b / Shadow / governed protocol:** `chroma_write_store.py`,
   `eval_corpus/r2b_v2/coverage/inventory.py`, `shadow_sink.py`,
   `shadow_ledger.py` and both writer coverage inventories must include object
   creation, refs, migration, rollback and capture dependencies. Shadow hashes
   metadata/state today: preserve its logical hash input by hydrating exact
   values, or introduce a reviewed versioned hash contract; never change old
   hash meaning in place. Capture bundles must be self-contained or include
   a verified object closure; a host-local ref is not a portable event payload.
   The scope census is separate from Shadow activation and events.
6. **Export maintenance:** `export_compaction.py` operates on ID/raw bytes;
   it need not hydrate every row merely to select last-ID winners. Preserve refs
   byte-for-byte and retain their objects. A typed store-closure validation is
   required for qualified outputs, not inferred from syntactically valid refs.
   `source_purge.py` keeps ownership predicates and never opportunistically
   deletes shared envelopes. `doctor.py` must distinguish a missing object from
   ordinary historical export drift. Portable export/materialization explicitly
   hydrates; diagnostics may read IDs without doing so.
7. **Recovery and exact evidence:** `cg2_rollback_baseline.py`,
   `cg2_legacy_vector_attestation.py`, `eval_corpus/reconstruct.py`,
   `recovery_authority.py`, `provenance_registry_restore.py`,
   `complete_data_restore.py`, `bootstrap_supersession.py` and incremental
   canary/live-boundary/isolation helpers need typed physical versus logical
   identities, complete dependency capture and scratch restore. CG-2 records
   envelope values/hashes in row identities; hydration must reproduce those
   values, not mint replacement provenance. Recovery Authority generation IDs,
   manifests and commitments are unchanged by side-store UUIDs. Exact older
   grants/snapshots cannot be reinterpreted as covering new files.
8. **Operational readers/scripts:** projection-parity reports, export path
   forwarding, backup profiles and scratch configuration builders must carry
   the side-store binding or reject reference mode. Inventory all tracked uses
   of `units_export`, `knowledge_units.jsonl`, envelope constants, projection
   validation/identity helpers and direct serialization. Unknown consumers block
   removing inline data; copying only the skinny JSONL is no longer a full export.

## 5. Migration, continuous availability and rollback

Prefer additive rolling compatibility, **not a long no-writer window**. There
is still a serialized cutover; “no outage” must not mean no coordination.

1. Deploy readers that support inline and refs, with ref-writing disabled.
   Qualify forward and reverse scratch restores, new StateSpec/backup closure
   and governed affected paths before any live reference. Inline legacy writers
   remain compatible during additive object backfill; backfill validates copied
   values and does not alter old rows or evidence.
2. Inventory long-lived CLI/MCP/watch/refine/monitor, tools and recovery runtimes.
   Before enabling refs, drain in-flight incompatible sessions and fence future
   old entrypoints with a required storage-capability epoch at admission. The
   current protocol version/attestation alone is not this fence. An old binary
   that ignores the fence cannot be allowed to keep using storage. If deployment
   cannot exclude such processes, a bounded no-writer maintenance window is
   required; no seamless-rollout claim is available on today's code.
3. New capable writers may publish refs after object durability, while untouched
   rows remain inline. Start with export-only references, leaving Chroma inline
   until Chroma readers/identity paths qualify; this separates export savings
   from later metadata-size savings. Every export writer must use the codec so
   reconciliation does not silently re-expand envelopes.
4. For the existing flat export, build a candidate from a pinned read-only inode
   outside C1, preserving rows/order/duplicates and leaving ineligible rows raw.
   Each participating export writer takes C1 then export lock, publishes a
   durable dirty intent before mutation, and completes a new durable export
   epoch only after file and directory durability, covering appends and
   replacements. A dirty/unknown epoch bars candidate publication until the
   bound operation is reconciled. At publication, compare the bound clean epoch
   and file identity under those locks; stale candidates are discarded, never
   published. Identity/mtime alone is not the authority. A
   durable migration intent ties old/new byte hashes to the epoch; unknown
   publication outcomes reconcile before another writer proceeds. Active writes
   can starve a whole-file sweep; lazy per-source conversion remains useful,
   or Ryan can later authorize a bounded maintenance window. Do not add a
   general catch-up log merely to promise an uninterrupted sweep.
5. Convert Chroma metadata in bounded source batches through governed writes,
   only after envelope dependencies validate. Read/recheck each row before
   replacement; preserve IDs, document bytes and exact stored vectors without
   embedding calls. Confirm the supported Chroma replacement behavior actually
   removes the old envelope key: merging a ref into metadata while retaining
   the envelope provides no size saving. Publish representation-version evidence
   without changing semantic provenance or source/checkpoint authority.
6. Do not convert any source with unresolved old APPLYING/recovery authority.
   In particular, resolve `46313d437ae4446282a752270770c614` under its original
   versioned authority before converting that source. A sweep skips its bytes;
   global compaction waits. Never rewrite journal bytes or recompute its bound
   SHA to accommodate migration. A normal new transaction may legitimately
   snapshot inline before-images and produce refs, but old recovery must still
   have its compatible decoder. If fingerprint/recovery compatibility cannot
   be preserved, defer conversion until the transaction is terminal.

Publication is monotonic: immutable object first, ref second. No atomicity across
Chroma/export/object files is presumed. On ENOSPC, missing object, short write,
rename/fsync failure or crash, recover a validated old/new representation or
refuse with retained authority. No ambiguous state is declared clean. Old
byte-hash evidence remains labeled physical; hydrated equality is additional
semantic evidence, never a replacement SHA for an existing grant.

**Rollback:** before any refs, stop conversion and keep inline storage; retain
objects as harmless unpublished data. After refs, disable new reference writes
using the capable release, resolve transactions and re-inline the **current**
logical values in export and Chroma through the same compare-and-publish/batch
protocol. Preserve all intervening commits. Verify complete closure, exact
legacy identity/hash semantics and scratch restore before admitting old code.
Restoring the pre-migration export would lose later writes and is not a valid
downgrade. Retain the side store, migration intent and receipts until no live,
backup, journal or incident reference needs them; initial delivery has no GC.

## 6. Export duplicates: compaction is not reconciliation

**203,441 export rows versus 111,348 Chroma units does not establish 92,093
duplicate rows.** Export includes historical unique IDs and different provenance
identities; Chroma physical/active/logical counts also differ. Startup doctor
independently reported ~203k historical export IDs and ~111k units, consistent
with substantial unique history, but that is a different live sample and not a
duplicate census. Kiro also encountered non-object/null records. The exact
number of removable same-ID duplicates remains unknown.

`export_compaction.py:compact_units_export` (52) is bounded-memory and atomic:
it takes the export lock, builds a private SQLite offset index, validates every
nonblank record (object with nonempty string ID, <=16 MiB), checks file identity,
and publishes last payload per ID in first-occurrence order. With no duplicates,
it is byte-identical/no-op; on real compaction it strips retained records and
adds newlines. Invalid records refuse without publishing. It does **not** select
only current Chroma IDs, resolve distinct IDs sharing `ledger_id`, validate
provenance continuity, or remove historical unique IDs. A successful return is
not evidence that the export now equals the live corpus.

Consumers and reliance:

- Legacy ingest, inter-model and repository writers append accepted projections;
  incremental reconciliation removes only its own source rows and copies all
  foreign lines. These routes explain possible history/duplicates, not an
  authoritative count of which cause dominates this export.
- Doctor collapses IDs for comparison but reports historical raw counts.
  No serving contract found requires multiple copies of the same ID to improve
  retrieval. Distinct IDs/assertions must not be conflated as content duplicates.
- Approval recovery in `propose_decision.py`/`observe.py` deliberately rejects
  multiple matching `ledger_id` rows. Compaction could hide such a conflict if
  they also share an ID; it cannot be used to bypass that refusal.
- Incremental rollback retains exact source bytes and foreign-line positions.
  Pending rollback, bootstrap mutation inventories, qualified snapshots, CG-2
  identity evidence and forensic artifacts can rely on multiplicity/order/bytes,
  even where normal serving does not. Purge must remove all matching rows.
- Complete-data checks compare export/Chroma identity sets; same-ID compaction
  cannot repair historical-only IDs or qualify a recovery profile by itself.

**Disposition: do not run live compaction on the evidence available.** The
algorithm is safe to evaluate on a hermetic copy; the primitive's export lock
alone is not governed-operation admission. Production use needs a fresh
grant, qualified recoverable preimage, no unresolved byte/ordering-dependent
transactions, a strict validity census and conflict classification. Measure
same-ID identical rows, same-ID differing payload/provenance/owner, distinct-ID
same-ledger rows, historical-only IDs and malformed rows separately. Refuse
conflicting groups pending owner disposition. Historical-only deletion is a
separate reconciliation policy, not compaction. Retain the original artifact;
do not silently filter invalid rows to make the utility run. Keep full
compaction off the ordinary per-commit/post-index path in the optimized route;
any later scheduling is explicit maintenance with separate accounting.

## 7. Collapse export work without importing option C

The flat JSONL remains O(total export bytes) per replacement. Shrinking it is
a constant-factor improvement; do not label it source-proportional.

The existing snapshot and reconcile read the export twice. A future combined
pass can collect exact source before-images/full and foreign hashes while
spooling unchanged foreign bytes to an unpublished temp. Do this before Chroma
apply; durably publish the original rollback journal and APPLYING authority
before mutation. After apply, append final source rows to that temp, fsync,
publish the checkpoint and then replace/fsync export in the existing order.
Validate the export epoch at publication under the export lock; never overwrite
foreign changes made since spooling. All writers must participate in the epoch
protocol. If it drifted, discard/rebuild from current bytes, charge the extra
work and retain original rollback authority; it is not a passing bounded fast
case. Temp content is not authority and can be rebuilt after crash. Keep the
existing export rollback and foreign-byte preservation behavior.

Avoid holding export while acquiring a Chroma/native session. Preserve outer
governed lease/admission, source → C1 → native/export lock ordering and the
separate processed-state critical section. Moving spooling outside C1 is a
later measured optimization requiring the epoch check, not permission to use a
stale snapshot. Whether checkpoint/follower crash handling can safely reuse the
spool must be proven with failure injection before this optimization ships.

## 8. Shipping order and acceptance

**First slice: duplicate pre-write digest reuse plus phase instrumentation.**
Keep the full post-check, all guards, rollback schemas and export behavior.
This is the smallest independently useful change and uses the new attribution
to remove ~73 s of avoidable work before the more coupled envelope migration.
It is a sequencing refinement of Kiro's shrink/collapse redirect, not a return
to option C. Kiro should explicitly accept this order. Instrument baseline and
candidate with the same harness; do not count startup, fixture construction or
provider preparation as C1 savings.

Then, as separately reviewed directions/slices:

1. Reader-compatible envelope repository, durability/recovery qualification,
   export refs and optional online backfill; measure export parse/rewrite and
   remaining full-digest cost. Qualify Chroma ref storage next, without changing
   full-digest field coverage. A digest of refs alone is not a digest of resolved
   envelopes; label physical versus logical evidence explicitly.
2. Source-scoped prevention/census in shadow comparison against full digests,
   then an explicit proof-mode acceptance gate to remove full scans. Keep full
   integrity audits/backup qualification available outside the commit path.
3. One-pass export staging and removal of synchronous whole-export compaction
   from the optimized route. Re-measure every remaining C1 component; smaller
   envelopes and removal of scans may expose guard saves, dedupe or fsync as
   the next limit. Revisit option C only if export I/O is then binding, or Ryan
   separately prioritizes its immutable-publication safety goal.

### 8.1 Two performance gates, neither inferred

**Gate A:** on the declared qualification host, every successful measured
one-chunk prepared commit completes in **<=60.0 s**, timed from commit entry
through all required checkpoint/export/dedupe/processed followers and cleanup.
Report source/C1 wait separately and also the complete indexing command with
deterministic providers; real provider latency is not fabricated. Require an
uncontended series and a bounded-contention series with a waiting foreign
writer making progress. Report maximum, p95, median, failures and all samples.

**Gate B:** each measured uncontended one-chunk commit has **<5.0 s maximum
continuous C1 hold**, with total C1 hold per operation also <5.0 s. Splitting a
100-second hold into tiny acquisitions is not success. Both warm and cold-ish
conditions must pass, including normal segment-save thresholds. Preserve Gate A
while satisfying B. Large-source and fault/recovery latency are separate
reported distributions, not exemptions hidden in the one-chunk average.

The first slice cannot meet either target by itself. Even eliminating all
three measured scans leaves more than 60 s in the rough residual estimate.
These gates require measurements after each step, not savings added from
unmatched runs. Failure to reach five seconds is a design result, not permission
to disable the native guard, skip durability or weaken source recovery.

### 8.2 Hermetic benchmark and correctness evidence

Use a network-denied subprocess and real isolated Chroma, deterministic fake
providers, synthetic envelopes/vectors/transcripts and actual production
coordinator/locks/guards. Set disposable HOME, XDG, config, data, cache and TMPDIR
before imports; remove credentials and allow writes only to the scratch root.
No live Chroma copy is required; no provider endpoint or production path may be
opened by the worker. Safety-negative controls must show those accesses denied.

Pin baseline `bd37946`, candidate SHA, dependencies, host CPU/RAM/storage/FS,
resource limits, fixture seed and instrumentation overhead. Reproduce the
111,348-unit/5,106-summary and 203,441-row/5.19-GiB shape with non-sparse synthetic
data. Vary foreign Chroma count independently of export bytes (10k, ~111k, 2×),
then vary envelope size/uniqueness, same-ID repetition and historical unique
generations. Keep owned source fixed for that sweep; separately vary owned
source rows/bytes. Include both new and existing source transactions, small
and large source histories, replay and segment-sync crossings.

At least 30 measured commits per size/cache condition, baseline/candidate
interleaved after recorded warmups. Cold-ish uses fresh fixture files/per-file
cache advice, not host-wide cache dropping. Time each digest, source snapshot,
export snapshot/spool/replace, native apply/guard save, projection fingerprint,
dedupe, journal, fsync and processed update; nested spans must not be summed
twice. Attribute CPU, RSS, logical bytes, `rchar`, physical disk I/O and lock
wait/hold separately. Count actual returned IDs/documents/embedding payloads,
read/pread and mmap work where observable; warm cache must not hide a scan.

Structural acceptance: first slice performs exactly two full inventory passes
per collection and one before/after comparison on a fresh attempt, and preserves
replay authority; scoped mode performs zero full
foreign inventories and no foreign payload read merely to certify isolation.
Native mutation calls must enumerate only authorized IDs. For fixed source,
added census/receipt bytes and returned rows must stay bounded as foreign count
grows; internal database lookup and segment I/O are reported separately. Flat
export remains linear and is explicitly charged. No synchronous background or
post-return compaction may move costs out of the reported commit.

Required correctness/fault cases include:

- Foreign ID collision, owner change, missing owner, broad predicate delete,
  hidden/nested session, raw collection bypass, collection reset and malformed
  scope; all deny before native mutation. An injected same-ID foreign vector
  edit demonstrates full mode detects what scoped mode cannot attest.
- Crash before/after intent, native call, completion, journal/APPLYING,
  checkpoint, export rename/fsync and cleanup; partial native batch and replay
  reconcile or refuse without replacing original rollback authority. Foreign
  commits between crash and recovery survive; no provider work repeats.
- Existing export tamper tests for unexpected IDs and changed old-ID payloads;
  foreign append/delete/reorder; malformed/non-object/unterminated/oversized rows;
  absent/empty source and source ownership after a collision.
- Inline/ref parity across every consumer above; wrong UUID, missing/corrupt
  object, wrong assertion/commitment/variant, inline-ref disagreement, path
  substitution, two representations sharing one commitment and conflicting
  provenance twins. Preserve raw preimages and legacy hash meanings.
- Online writer racing a migration candidate, old-runtime admission, repeated
  stale candidate, active v1 journal skip, interrupted forward/reverse conversion
  after new commits, ENOSPC and uncertain fsync. Full closure capture and scratch
  restore for old/new profiles; retained incident and no-GC dependencies.
- Compaction no-op/golden/SIGKILL cases, same-ID conflicting provenance and
  same-ledger duplicates; no logical dedup view may hide approval refusal.
  Negative controls deliberately reintroduce a full scan, re-inline envelopes
  or run post-index compaction; performance/accounting tests must catch them.

These are future acceptance requirements, not tests run or results claimed
in this document. Full-corpus benchmark construction, migration and audit cost
is separately reported; it is never silently amortized into a fast-path claim.

## 9. Decisions requested from Kiro and handoff

1. **First slice/order:** accept two full scans plus instrumentation before
   envelope migration? Recommendation yes: immediate measured waste removed,
   full post-write field coverage retained; no 60-second claim for this slice.
2. **Proof contract:** accept causal scoped-write proof for ordinary commits,
   with loss of immediate untouched-row corruption detection stated explicitly?
   Recommendation conditional on complete-mediation evidence and new typed
   outcomes. If no, retain scans; metadata-only is not a fallback compromise.
3. **Provenance representation:** accept commitment-keyed objects with exact
   variants and explicit resolver context, while registry authority stays
   unchanged? Confirm physical/logical hash handling, especially Shadow and
   CG-2, before any implementation grant.
4. **Rolling migration:** accept additive dual-read/inline-write deployment,
   capability fencing before refs, epoch-bound sweep and active-journal skips?
   If old processes cannot be fenced, require a bounded maintenance window.
   No claim of no-writer-window migration is made for the present runtime.
5. **Duplicates and gates:** accept no live compaction until validity/conflict
   classification and recovery preconditions pass, and the strict 60 s then
   5 s host-qualified gates? Which source-size distribution should supplement
   the measured one-chunk fixture before production acceptance?

The largest trade-off is removal of an immediate foreign-state observation
when replacing full digests, coupled with a new required envelope dependency
for skinny exports. Smaller files and faster calls do not themselves justify
either change. Kiro reviews this exact artifact; after Ryan direction approval,
Codex can produce a bounded Cursor execution plan. Production migration,
runtime changes, indexing, providers, compaction and recovery remain separately
gated. No PR is requested or opened here.

Suggested later PR title: **Plan cheaper incremental commits while preserving recovery**

Suggested PR description: Ryan can review a measured path away from multi-minute
commits without adopting the deferred segmented export format. Codex authored
this Arc Codex re-plan on 2026-10-17 after Ryan accepted Kiro's redirect. It
recommends digest reuse first, then compatible provenance references and a
separately approved scoped-write proof; it specifies duplicate/rollback behavior
and hermetic 60-second/5-second gates. Documentation only; source contracts and
whitespace checked, no implementation tests or live mutation. Merge reading:
`docs/plans/DESIGN-issue-286-commit-cost-reduction.md`. TL;DR: staged cost reduction,
explicit proof limits, Kiro review before execution.

**I finished:** [Arc Codex #286] Revised architecture direction.
**Next step:** Review the first slice, proof substitution and migration conditions.
**Next lane:** Kiro; Ryan decides subsequent direction/execution authority.
**See my work:** this file, especially §§2–5 and §§8–9.

**TL;DR:** [Arc Codex #286] Reuse the duplicate pre-write digest first; retain the
post-write check. Externalize envelopes through compatible, recoverable refs,
then require explicit approval and complete mediation before scoped receipts
replace global scans. Compaction does not remove unique history and is not
cleared for live use. Option C stays on hold; 60 s/5 s are unproven gates.

<!-- src: ../../incremental_jsonl.py, ../../chroma_store.py, ../../chroma_write_store.py, ../../chroma_write_guard.py, ../../provenance.py, ../../provenance_binding.py, ../../export_compaction.py, ../../observe.py, ../../propose_decision.py, ../../complete_data_restore.py — baseline bd37946 contracts -->
<!-- src: ../inter-model/KIRO-2026-10-17-issue-286-proportional-export-review.md, ./DESIGN-issue-286-proportional-export-commit.md — separate review/design branches pinned in the header -->
<!-- src: ~/.cache/claude-export-profile/profile.sh — Ryan-supplied measurement procedure; not executed for this design -->
<!-- ref: ./STATUS-codex-jsonl-production-integration.md, ./STATUS-safe-harbor.md, ./STATUS-r2b-capture-auth.md, ./STATUS-shadow-ledger-phase0.md, ./STATUS-recovery-authority.md — arc and compatibility boundaries, no cross-arc execution grant -->
