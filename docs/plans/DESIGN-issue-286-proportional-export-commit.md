# [Arc Codex #286] Proportional export publication for incremental commits

**Verdict:** Recommend **option C: immutable per-source export segments, addressed
through a bounded-depth copy-on-write directory and one atomic root pointer**.
This removes corpus-sized export reads and writes from source commit and rollback.
It requires a versioned export format and coordinated reader/writer migration;
it is not a safe one-function substitution of append for reconciliation.

**Who / what / when / why / how:** Codex architect, 2026-10-17. Ryan requested
this design after canary 2 at runtime-main `bd37946` reported roughly five-minute
commits even for one chunk. Publish a new segment for the changed source and
replace a small root pointer; retain the previous source image for exact recovery.
Kiro reviews this direction next; Ryan approves any subsequent execution plan.

**Baseline:** `bd379463345b360737b84c9d87d16b854fe265d0`, fetched `origin/main`
when this branch was created. Branch:
`docs/2026-10-17-issue-286-proportional-export-commit`.
All source coordinates below refer to that baseline.

**Planning status:** Architecture Planning. Characters: Architect, Systems
Thinker, Risk Reviewer. Function: Planner. Lanes: Codex authors; Kiro reviews;
Ryan approves. Authority: design requested, direction awaiting review/HITL.
This document specifies contracts and acceptance evidence, not an Execute grant.

## 1. Evidence, scope, and product consequence

Ryan's canary evidence: the live export is about 5.3 GB; one admitted child read
39 GB `rchar` / 8 GB disk and wrote about 1.4 GB. These are reported process
measurements, not measurements reproduced here or attributable solely to one
function. `rchar` includes cached/repeated reads and is not disk-read volume.

The baseline explains a corpus-sized export cost:

- `incremental_jsonl.py:1452`, `_snapshot_export_before_image`, reads every raw
  line to save the source's bytes and foreign-line positions and hash both the
  whole file and its foreign portion.
- `incremental_jsonl.py:1488`, `_snapshot_before_images`, additionally captures
  Chroma source rows, non-source collection digests and recovery sidecars.
- `incremental_jsonl.py:1906`, `_reconcile_export`, streams all foreign lines to
  a temporary file, appends the source's current Chroma rows, fsyncs, replaces
  the export and fsyncs its parent.
- `incremental_jsonl.py:2142`, `_commit_generation`, holds source and C1 locks
  over this work. It durably publishes the checkpoint before the export and
  dedupe followers. Processed state publishes after that critical section.
- `ingest.py:699` appends accepted legacy rows under the export lock, but
  `ingest.py:1675,1785` invokes compaction after index. Merely adopting append
  can move the same full scan to the tail of each index command.

The product goal is that unrelated export growth no longer makes a small
incremental commit monopolize the shared writer lock. Let `S_old` and `S_new`
be this source's old and replacement export bytes, and `n_old`, `n_new` their
record counts. The requirement is proportional to **this source's entire
export contribution**, not necessarily to one changed chunk. A very large
single source can still require substantial work.

Scope includes the export storage abstraction, coordinator integration,
compatibility of every consumer, recovery evidence, migration and downgrade
contracts. Source capture, chunking, provider selection, Chroma authority,
dedupe policy and admission eligibility remain their existing contracts.
Safe Harbor, R2b, Shadow and backup interfaces below are compatibility
requirements within Ryan's requested design scope, not authorization to execute
those arcs or alter their authority policy.

Only this requested design file is delivered. Existing STATUS/LATEST files are
historical orientation, not current canary evidence; they are not updated in
this single-file scope. After the startup diagnostics (which themselves read
production state), inspection was confined to repository files. No production
migration, inference-provider call, indexing or implementation test was run for
this design. Startup doctor/brief were read-only orientation; Ryan explicitly
waived doctor's remaining CPU-tripwire failure. `unresolved` encountered a database
lock. Semantic corpus search was omitted to honor the no-provider-call limit;
the findings here come from the pinned repository and Ryan's supplied evidence.

## 2. Options and decision

### A. Append rows plus source supersession/tombstone records

Commit can append an operation containing source identity, predecessor,
replacement rows and a durable commit marker. A source deletion needs an
explicit tombstone: last-value-per-ID alone cannot remove IDs absent from the
new generation. Torn records must be ignored until their complete operation
is authenticated and committed. Rollback is another source operation, never
truncation of a shared log after other writers append.

This is viable only with a common log-aware reader and a durable source index.
Existing readers would count stale IDs, treat markers as units, reject them as
malformed, or reject historical ledger duplicates. Without the index, recovery
still scans the entire log for the source. With it, publication must coordinate
log durability and index visibility, and compaction must atomically rebase the
index. Periodic compaction is necessary; invoking it after each index defeats
the objective. Rejected as the primary design because the supporting machinery
is comparable to C while adding log-tail recovery, dead-history filtering and
marker semantics to the critical correctness surface.

### B. A byte-range sidecar for the existing mutable flat file

Offsets, lengths, owner and per-range hashes make before-image reads
proportional. They do not make variable-length replacement or deletion in a
contiguous JSONL file proportional: preserving a plain file requires moving
foreign bytes. In-place padding/tombstoning exposes partially changed rows to
unlocked readers and backups; overwriting adjacent bytes risks foreign data.
Append plus indirection solves that by becoming A. Replacing/compacting the
file invalidates every offset and requires a paired generation identity and
atomic publication of file plus index.

Rejected as a stand-alone solution. It optimizes the lookup but leaves either
the rewrite cost or a new read/recovery format. Offsets remain useful **inside
an immutable segment**, where they cannot shift under a reader.

### C. Immutable source segments with an atomic directory root — chosen

Each source owns a segment and descriptor. Updating it writes only its new
bytes and a bounded number of small directory nodes. A single pointer publishes
the complete export view. Readers resolve one root and see either the previous
or replacement source image; unreferenced candidate files are never export
rows. Rollback substitutes the original source leaf into the **current** root,
preserving other sources' later commits.

The trade-off is a coordinated storage-format migration, retained immutable
objects and a more complex export module. It avoids per-commit global scans,
in-place data mutation, dual authoritative flat/log representations and a
log-length-dependent replay path. It also makes snapshot acquisition constant
size. A generic global SQLite index was considered within C: its page work,
checkpointing and vacuum are database-size-dependent. The fixed-depth directory
below provides a more explicit bound for Ryan's source-plus-constant target.

Builder reasoning: hide storage and publication behind one deep module
(Ousterhout); preserve source/checkpoint versus derived-projection authority
and idempotent replay (DDIA); accept and name the cross-consumer migration cost
instead of moving it to implicit reader assumptions (Hard Parts).

## 3. Proposed storage and logical export contract

### 3.1 One live representation

In v2, the configured `index.units_export` path names a private **directory**,
not a regular JSONL file. Its name may remain `knowledge_units.jsonl` to keep
the canonical target and sibling export-lock location stable. This deliberate
format break makes old append/open writers fail with a type error. It is not
sufficient protection against old readers that silently treat a directory as
an absent file; deployment fencing in section 9 is mandatory.

Conceptual contents (names are proposed, not existing APIs):

```text
knowledge_units.jsonl/
  FORMAT                         immutable schema + store UUID
  CURRENT                        small atomic root record
  objects/<hash-prefix>/<hash>    immutable trie nodes, source descriptors,
                                 ordered raw source segments
  pins/<pin-id>                   durable snapshot/recovery references
  staging/<operation-id>/         unpublished, identified candidates
```

All durable members are within the admitted export root. Private directories
and files use the existing ownership/no-symlink discipline, 0700/0600, and
same-filesystem rename. Path containment must be checked at use, not just on
config parse; descriptor paths cannot escape via `..`, links or retargeting.
The sibling export lock remains outside the directory exactly as today.

`CURRENT` binds format version, store UUID, publication sequence, directory
root hash and last publication operation ID. It is bounded (proposed maximum
4 KiB), replaced atomically and followed by parent fsync. There is no second
live flat mirror. A requested JSONL materialization is an explicit snapshot
artifact with a root identity and freshness label, not an alternate live input.

### 3.2 Source directory with a concrete bound

Key a leaf by SHA-256 of a domain separator and the **exact stored source_path
string**, preserving the coordinator's current equality rule. Missing/non-string
source paths use an explicit residual owner; empty string is distinguishable
from missing. Never normalize historical source paths during migration.
Purge continues to use its candidate/predicate rules across owners. Hash
collisions or descriptor-owner mismatch refuse; they never merge ownership.

Use an immutable 16-way radix directory over the 64 hex digits of that hash.
A node has 16 fixed child slots, no unbounded map. A source replacement visits
and copies at most 64 internal nodes plus its leaf. Cap each encoded internal
node at 2 KiB, including schema and bounded aggregate counts/tail metadata.
Subtree maximum ordering token and termination status allow the root to bind
the logical tail without reading foreign payloads. The root record
and nodes are validated on read. Object names are hashes of exact encoded
bytes; publish files before referring to them. Directory fanout for object
filenames is fixed. No recursive `rglob`, full catalog read, root-wide hashing
or global JSON map rewrite is allowed in a normal source operation.

This is a bound on application export I/O, not a claim that filesystem lookup,
allocation or fsync latency is mathematically independent of disk state.
The benchmark must include node, descriptor, journal and directory work.

A source descriptor binds owner, segment hash, byte length, row count,
per-row offset/length and ordering token, operation/transaction ID and source
generation. Descriptors may grow with source size and must be streamed or
bounded-spooled. A segment preserves exact row bytes; the descriptor is not
trusted without hashing those bytes when used for rollback or publication.
An empty source is an explicit empty leaf, distinguishable from corruption.

### 3.3 Duplicates and ordering are explicit views

The primary view is the **logical raw export**: all currently referenced raw
records, including legitimate duplicates, malformed records and blank lines,
in their defined order. Storage metadata is never emitted as a knowledge unit.
Do not silently impose one duplicate policy on all callers.

Migration assigns each physical line token `(0, line_number)`. Subsequent
append/replacement operations allocate a monotonically increasing publication
sequence under C1/export locks, then tokens `(sequence, row_number)`. Both token
components are unsigned 128-bit integers; row counts are bounded unsigned
64-bit integers. Overflow refuses pending explicit maintenance.
Incremental replacement removes all that source's old logical records and
puts its replacement records at the end, matching `_reconcile_export`.
Legacy append preserves old source records and appends new ones. Ledger upsert
retains the affected records' positions. Byte strings and tokens are separate,
so serialization metadata does not change exported records.

Preserve an unterminated final line on import and read-only materialization.
Do not mistake an object/segment boundary for a newline. Ordinary v2 mutations
must refuse before Chroma mutation when the current logical tail is unterminated,
using a bounded tail descriptor in the root;
an explicit qualified repair is required. Silently adding a newline changes
bytes, while baseline concatenation can create malformed JSON. This stricter
refusal is an additional explicit compatibility decision for Kiro, tested
separately from successful commits on well-formed inputs. This includes replacing
the tail's owner: otherwise a later rollback could reintroduce an unterminated
old row ahead of another source's intervening append. Newly written rows always
include their newline; imported unterminated bytes remain inspectable and
reversibly materializable until a separately authorized repair.

An all-export iterator pins one root and merges rows by ordering token. A
bounded disk sorter/merge may be used for a large global read; it never runs
as part of a source commit. Equal tokens across different live records are
invalid. Reader policies remain distinct:

- raw/source view preserves duplicate rows and exact bytes;
- compaction uses last value per non-empty string `id`, in first-occurrence
  order, with the baseline malformed/oversized refusal and no-op rules;
- ledger recovery requires at most one matching `ledger_id`, and retains its
  full-export malformed-record refusal;
- diagnostic ID sets may collapse duplicates but report raw counts separately.

### 3.4 Narrow module interface

One proposed export repository module owns format detection, validated reads,
source images, publication, snapshot pins, and legacy materialization. Callers
request operations such as `read_source_image`, `replace_source`,
`append_source_rows`, `iter_raw_snapshot`, `restore_source_image`, and a strict
ledger projection lookup. These names express contracts, not a prescribed
class hierarchy. Every mutator requires the caller's governed writer lease,
admitted target and existing locks; it cannot create a parallel writer route.

The v1 backend supports existing journals/read behavior until migration is
complete. The v2 backend returns typed source/root identities. Do not overload
`file_sha256` with a directory-root hash: they prove different things.

## 4. Commit, locks, and authority

Lock order remains **source → C1 (`index_write_flock`) → Chroma session →
export**. Nested scopes may omit a lock they do not need; no operation acquires
C1 or a Chroma session while holding export, or source while holding C1.
No provider work is moved into these scopes. Source recovery remains under
the source lock and the existing admitted writer boundary.

Proposed successful commit sequence:

1. Existing source snapshot/transform preparation completes durably outside
   C1. Unpublished export staging may also occur outside C1 when based only
   on immutable prepared data, but it is not authority for dedupe/prune output.
2. Acquire source then C1; recheck exclusion, live-source continuity and pinned
   operation targets. Take existing Chroma before-images/integrity evidence.
3. Under export lock, validate `CURRENT`, traverse only this source's path,
   read/hash its old descriptor/segment and capture its exact bytes/order.
   Pin the old image. Release export before any new Chroma session acquisition.
4. Write and fsync the original rollback journal, then hash its exact bytes
   into `rollback_authority_sha256` in the durable APPLYING transaction, as
   today. It contains the typed v2 export preimage described below. No Chroma
   apply begins without this authority.
5. Apply prepared Chroma changes and pruning through existing governed
   sessions. Preserve `_require_rollback_authority` checks before/after replay
   and the current non-source collection checks. Revalidate the source prefix.
6. Obtain the exact post-apply source rows, build/validate the replacement
   segment and record a durable candidate identity tied to this transaction.
   This covers all source rows, including stable rows and exclusions by dedupe.
   Do not construct the final export from provider output alone.
7. Publish the complete checkpoint, retaining its position **before** export
   publication. Its v2 fields bind the expected source export content digest
   and transaction identity, not a guessed corpus-wide root. The transaction
   remains APPLYING until all existing followers finish.
8. Under export lock, recheck the current source leaf against the expected
   predecessor or this transaction's already-published candidate. Build the
   source leaf and at most 64 directory nodes against the latest root; fsync
   the objects and their directories before atomic `CURRENT` replacement and
   directory fsync. Publish sequence and directory root in the same record.
   On matching replay, verify and reuse publication; do not allocate more
   ordering tokens or append duplicate rows. If only an unpublished candidate
   exists and another source has since advanced the root, reuse its validated
   payload but rebuild its descriptor with a fresh sequence from the current
   root. Unpublished sequence values confer no reservation or visibility.
9. Complete dedupe reconciliation; leave the nested writer scopes in existing
   order. Publish processed state under its existing standalone lock/recheck,
   then perform existing transaction cleanup. A purge exclusion after the
   checkpoint retains the existing `excluded_after_checkpoint` behavior.

Source transcript remains input authority; checkpoint/transaction/journal
remain processing and rollback authority. The export root commits a projection
view, not successful indexing of the whole transaction. A visible new root
must not substitute for checkpoint validation or authorize processed advance.
Chroma's two-collection visibility seam is still present and measured separately.

### Export before-image version

Introduce a new rollback schema with a tagged `export_preimage` backend;
retain the baseline version-2 journal validator/replayer for unmigrated v1.
A v2 export preimage includes format/store UUID, owner, original root identity,
source descriptor digest, exact raw source bytes and ordering tokens, and
existence/empty-state distinction. The journal embeds the before-image bytes
(or an equally digest-bound, durably pinned object bundle); initial preference
is embedded bytes to keep rollback self-contained if a segment is lost.

The original journal is immutable across replay. Candidate publication binding
belongs in a separately fsynced transaction field/artifact, never by rewriting
the journal and recomputing an allegedly original authority hash. Missing,
malformed, changed or wrong-owner original authority remains
`recovery_unproven`; never re-snapshot a damaged current export to manufacture
new rollback authority. Existing checkpoint, prepared, processed, dedupe and
Chroma preimages keep their contracts.

## 5. Rollback, tamper detection, and limits of hashes

Restore only the source leaf into the current directory root, through the same
publication protocol. Never restore the entire old root: another source may
have committed after the crash. Read and authenticate the original journal
before reading candidate state and again before completing recovery.

Compare current source rows with original preimage rows and the transaction's
exact candidate. Preserve the baseline detection of unexpected source IDs and
changed payloads for old IDs (`_restore_export`, `incremental_jsonl.py:1801`).
Also detect wrong owner, wrong store UUID, changed descriptor, length/hash
mismatch, truncated segment and unexpected source generation. A matching unit
ID alone is insufficient. Authenticated storage files may still contain an
unauthorized candidate, so compare transaction binding as well as object hashes.

When the directory is valid and the affected source is recoverable, retain
the suspicious source image as incident evidence, durably record
`rollback_export_tamper.jsonl`, then republish the authenticated preimage.
Keep existing timestamp/source/transaction/count fields used by doctor; add
typed reason and image identities. If a corrupt segment cannot be parsed, do
not fabricate a line count; emit an explicit corruption reason with unknown
count and update doctor accordingly. Tamper reporting must be idempotent by
transaction plus evidence digest and retryable after an I/O failure. Failure
to durably preserve/report an incident cannot be reported as clean recovery.

If root/path structure is corrupt, ownership cannot be established, or the
original journal fails `_require_rollback_authority`, refuse recovery and
retain evidence. Do not rewind foreign data to get a parseable root. Orphan
objects not referenced by any committed root are not logical export rows;
they are classified as interrupted staging/evidence and never auto-adopted.
Bound reads by the authenticated descriptor length and record limits; a
size mismatch or oversized unexpected object produces an incident/refusal
without an unbounded scan. Preserve it by a durable evidence reference where
safe; any full forensic copy is separately budgeted maintenance. Failed
tamper recovery must not be called a successful proportional rollback.

Foreign byte tampering is not globally detectable in source-proportional I/O.
The baseline snapshot records full/foreign byte hashes, but baseline
`_restore_export` preserves current foreign bytes rather than requiring that
the foreign byte hash still match. V2 retains that isolation policy. A source
operation verifies its traversed nodes and owned bytes; it does **not** attest
that every foreign segment is unchanged on disk. A root hash is a commitment
to object contents, not proof those contents were freshly read. Full integrity
audits and qualified backup/snapshot checks walk and hash the complete closure.
Same-user modification of all authority files remains outside this cooperative
guard model, as it does for the current journal SHA checks.

**Ordering compatibility decision for Kiro:** restore original source ordering
tokens. With unchanged foreign data, materialized bytes are identical to the
preimage. With foreign appends, all original interleaving is preserved and
appends remain at the end. With foreign deletion/reordering, restore the
source's original relative anchors and preserve current foreign order, rather
than recalculating baseline `foreign_lines_before` integer insertion positions
against the changed foreign stream. That edge case is an explicit v2 semantic
change, not byte-for-byte v1 equivalence. If exact v1 rank behavior under
foreign deletion is required, this direction needs revision with a bounded
order-statistics structure before approval; do not hide a full foreign scan
inside rollback. Existing v1 transactions continue to use v1 behavior.

## 6. Crash consistency and concurrent operations

Every durable file publication uses temp write → flush/fsync → atomic rename
→ directory fsync. Object directories become durable before pointer publication.
Do not overwrite an existing content-addressed object; verify it or refuse.
The single `CURRENT` replacement is the export visibility point. Directory
fsync failure after rename is an **unknown durability outcome**, not proof of
failure or success. Preserve the APPLYING transaction and reconcile on restart.

- **Before rollback durability:** no Chroma/export mutation; discard only
  proven unreferenced staging after evidence policy permits.
- **After journal but before APPLYING:** retain the original authority; use
  validated existing recovery rules. No candidate is visible.
- **During Chroma apply / before checkpoint:** export still points to old
  source. Existing exact-image replay/restore handles partial collections.
- **After candidate objects, before checkpoint or root:** candidate is invisible;
  reuse only if its transaction/content binding validates.
- **After checkpoint, before root:** export lags; APPLYING replay completes
  publication from durable prepared/current validated source state or performs
  authenticated rollback. Never infer cleanup from checkpoint alone.
- **After root rename, before directory fsync:** root may recover old or new.
  Either must be valid and refer only to already durable objects. Re-read and
  validate; never truncate or blindly publish a second copy.
- **After root durability, before dedupe/processed/cleanup:** replay recognizes
  the source operation and finishes the remaining followers exactly once under
  their existing identities. It may still need rollback on existing refusal
  conditions; that rollback publishes a new root containing the old source.
- **During rollback:** old and suspicious images remain available. Retry the
  incident record and source restoration idempotently; original journal hash
  must stay identical. Cleanup only after recovery has durably completed.
- **ENOSPC, short write, fsync failure, permission error or SIGKILL at any edge:**
  no success receipt before required durability; retain authority and expose
  an actionable refusal/unknown result. Never catch and continue as committed.

Other-source writers serialize on existing C1/export locks. A source recovery
after an intervening foreign commit applies to the latest root. Compaction
builds from a pinned root outside C1, then takes C1/export and publishes only
if that exact root is still current; otherwise abandon/retry later. It must
not block a source writer by holding export while waiting for C1. Compaction
must defer while unresolved incremental transactions or snapshot contracts
pin ordering that it would change; do not remap their journals in place.

Readers pin one root before iteration. Initial v2 retains all referenced and
historical objects, so a reader never loses an object mid-read; ordinary read
pinning can be process-local. Durable recovery/backup pins are files included
in the closed inventory. Garbage collection is a later explicitly authorized
maintenance operation with a complete pin/reachability protocol, never a
post-commit directory walk. Storage growth is a deliberate initial trade-off.

## 7. Reader and writer inventory at the baseline

Each entry names current assumptions and the required v2 behavior. Some named
modules bind or forward export paths rather than parse export rows; that
distinction matters. All direct file access must be classified before activation.

1. **`bootstrap_supersession.py:269,393`.** `_path_inventory` hashes a file or
   recursively inventories a directory. It compares physical mutation state,
   not last-ID winners; byte order and duplicate bytes affect the proof. V2
   inventory must bind the root and its complete closure, pins/staging and
   retained predecessor evidence with an explicit schema. No logical-ID digest
   may replace a physical snapshot/mutation proof. This full inspection is an
   explicit bootstrap operation, not an ordinary incremental commit.
2. **`chroma_write_store.py:792,848,860`.** No duplicate/order interpretation;
   pins canonical export target and affected paths for admission and alias
   rechecks. Bind backend/store UUID and all new durable roles as well. Existing
   guard, native lock, writer attestation and post-admission target revalidation
   remain mandatory. A path that still resolves identically but changes store
   UUID/format must not pass an old admission.
3. **`doctor.py:123,136`.** Reads nonblank lines, skips malformed JSON, counts
   raw lines and sets of `id`/`ledger_id`; duplicates increase line count, not
   unique IDs. Order is irrelevant. V2 uses the logical raw view, reports backend
   health separately, and must never report a v2 directory as an absent export.
   Historical-only IDs are not automatically corruption or tombstones.
4. **`export_compaction.py:52,175,237`.** Strict valid-object/non-empty-string-ID
   parsing; 16 MiB inclusive record ceiling; last payload by ID, ordered at the
   first occurrence. A no-duplicate valid input is byte-identical/no-op, including
   blank lines and final newline shape. A real compaction strips retained rows
   and terminates each with newline. Preserve these distinctions in v2's global
   maintenance operation; same-ID rows in different sources need a global pass.
5. **`incremental_jsonl.py:1434–1952` and `:2142–2470`.** Owns rows by exact
   source-path equality, preserves foreign raw bytes, removes every owned row
   and appends current source rows. Rollback binds exact owned bytes and detects
   unexpected IDs/altered old rows. Use source image/replace/restore operations,
   retain authority hashes, and implement the explicit ordering policy in §5.
6. **Other `incremental_jsonl_*` modules.** Production boundary `:74–145` treats
   export as an exact mutable role; isolation/canary code generates an export
   file, validates file roles and binds snapshots/grants. Format-specific
   wrappers must permit only the complete export directory closure, not the
   entire data root. Update canary/P2 Gate-0 manifests, capsules, restore proofs,
   inventory hashes and failure fixtures together. Format/admission/parser
   modules that do not touch export retain their present contracts. Inventory
   tests must catch new or hidden accesses, including test helpers.
7. **`inter_model_index.py:278–331`.** Appends each accepted unit after source
   exclusion/replay/dedupe checks. It does not resolve export duplicates or
   read order; retries can leave historical copies. Route accepted rows through
   append semantics, preserving batch order and existing Chroma/prune behavior.
8. **`live_diagnosis.py:376–411`.** Checks mutable paths lie under scratch roots;
   no duplicate policy. V2 must constrain every object, pin, staging, snapshot
   and lock path, and forbid production roots before imports/subprocesses.
   Directory configuration cannot become a path-escape loophole.
9. **`ingest.py:577,699,1675,1785`.** Appends projection rows; later compacts
   globally. It has no per-append deletion marker semantics. Preserve append
   and provenance-selected IDs; replace automatic full compaction on normal
   source index completion with explicit scheduled/threshold maintenance.
   Threshold accounting must use bounded counters, not an export scan. Merely
   queuing maintenance cannot cause it to run synchronously under this commit.
10. **`monitor.py:591–605`.** Forwards export to prepared observation commits
    under C1 and a governed Chroma session. Duplicate/order rules come from
    `observe`; retain preparation/drift recheck and idempotent retry boundaries.
11. **`propose_decision.py:652–789`.** Approval recovery rejects any malformed
    or non-object export row, multiple matching `ledger_id` rows and conflicting
    projections. Exact match is idempotent; replacement requires the previously
    verified base; unrelated rows retain order. It fsyncs before completion and
    reports `RecoveryCompletionUnknown` for durability uncertainty. V2 strict
    raw scanning preserves these checks even if expensive. Do not feed it a
    deduplicated view that hides an invalid authority state.
12. **`verify.py:11–75`.** Updates unit metadata and optionally forwards a new
    verification ledger record to `observe`. It is not a direct export reader;
    duplicate/order behavior is delegated. Preserve the distinction between
    Chroma metadata update and an exported verification record.
13. **`repository_knowledge_index.py:235–290`.** Appends accepted units after
    source/exclusion, replay and dedupe checks; no export duplicate resolver.
    Route through append semantics, retaining source ownership and batch order.
14. **`source_purge.py:35–110,193–218,326–400`.** Preview tolerates malformed
    records; execution/counting fail closed on malformed/non-object records.
    Purge uses path candidates and `line_matches_purge`, removes every matching
    row (including duplicates) and retains foreign relative order. A real v1
    purge strips surviving lines, removes blanks and writes final newlines;
    a zero-removal operation leaves the file unchanged. Preserve this distinction
    in the global v2 operation, including reserialization of foreign owners
    when needed; purge is not subject to the source-commit I/O bound. V2 must use the
    predicate, not assume a single source hash is exhaustive. Preserve global
    malformed refusal; explicit purge can scan globally. Commit the resulting
    multi-owner export change in one root publication, retaining the exclusion
    fence and existing partial-Chroma-failure behavior.
15. **`observe.py:153–225,387–427`.** Strict lookup rejects duplicate ledger
    identities and malformed/non-object rows; generic upsert instead replaces
    *all* matching ledger rows in position and preserves malformed/blank foreign
    lines. Plain ingestion appends. Do not unify these different contracts by
    deduping at storage entry. Implement ledger operations over a pinned raw
    view, then publish affected owners atomically; owner can be residual or
    source-specific. Ledger IDs must not be assumed globally unique on disk.

Additional direct consumers found by repository search are part of the closed
inventory, even though they were not in the initial list:

- `complete_data_restore.py:286,390,741,1562`: file-byte fingerprint plus sorted
  unique-ID evidence, registered state classification and export/Chroma checks.
  V2 needs a typed closure fingerprint and logical-view evidence; old snapshot
  schemas retain exact flat-byte meaning. Unknown format is not missing data.
- `recovery_authority.py:254`: reads the fixed filename, rejects malformed rows
  and mixed `generation_id`, and binds assertion/provenance commitments. V2
  must preserve those checks. Storage root sequence/UUID must never masquerade
  as a Recovery Authority generation or grant a serving migration.
- `scripts/projection_parity_report.py:50`, CLI/config/exclusion forwarding,
  capture/shadow-config modules and `scripts/bootstrap-incremental-jsonl.py`
  must accept a pinned logical view or a named materialization, and bind the
  backend in generated scratch configuration. The scratch prototype remains
  v1-only and must explicitly reject v2 inputs if not ported.

Required implementation inventory: all tracked references to `units_export`,
`knowledge_units.jsonl`, `export_projection_records`, and direct open/append/
replace/fsync calls through aliases. Classify production, recovery, scripts,
fixtures and documentation examples separately. The above is a source-review
inventory, not a claim that regex discovery mechanically proves zero bypass.

## 8. Safe Harbor, backups, R2b and Shadow compatibility

Safe Harbor's existing admission binds exact affected resources to qualified
recovery evidence. V2 changes the recovery profile: `CURRENT` alone is not a
backup. Qualification must cover FORMAT, root-reachable nodes/descriptors/raw
segments, durable pins, unresolved transaction journals/prepared objects,
retained incident objects and existing Chroma/processed/dedupe state. Every new
durable member needs a StateSpec classification; transient locks and staging
need explicit replay/retention treatment. An old profile expecting a regular
file cannot be accepted by calling the directory 'derived and rebuildable'.

Pinning an export root gives an exact export snapshot and permits streaming
its closure outside C1. It does not make Chroma, checkpoint and all sidecars
an atomic multi-store snapshot. Preserve the existing complete-data capture
consistency bar and qualified-artifact checks. If that bar requires a writer
window, the new export format does not remove it. Backups must either capture
a quiescent qualified closure or a manifest-pinned closure proven complete;
copying CURRENT at one time and objects at another without verification fails.

Restore into scratch first. Verify root/closure hashes, source ownership,
logical bytes/IDs/provenance, unresolved journal bindings, missing objects and
wrong-store refusals before any authorized publication. Retain pre-incident
evidence before replacement. Existing quarantine release and uncertain-outcome
rules remain unchanged. Schema migration/downgrade is a separately qualified
operation with explicit old-process disposition and usable recovery artifacts.

R2b inventory (`eval_corpus/r2b_v2/coverage/inventory.py`) currently identifies
incremental, canary, purge and other routes and their export mutation surfaces.
Add source segment/descriptor/node publication, CURRENT replacement, pins,
migration, maintenance, materialization publication and later retention to the
same governed-route census. Do not label an export-only writer read-only
because it never constructs Chroma. Fix stale surface classifications where
forwarders actually write export; capture authority must include new paths.

Regenerate `R2B-V2-WRITER-COVERAGE-INVENTORY.json` with its existing generator
from the final implementation tree. Reconcile
`SHADOW-WRITER-COVERAGE-INVENTORY.json`, call-site coordinates, protocol/revision
binding and existing inventory tests. Shadow Chroma mutation events retain
their current meaning; storage projection writes must not fabricate additional
semantic-unit events. Any new event policy needs separate owner acceptance.
Neither registry regeneration nor this design enables live R2b capture or Shadow.

## 9. Migration of the existing 5.3 GB export and downgrade

Migration is an explicitly authorized maintenance operation, not lazy work
performed by the next one-chunk commit. It is O(total export bytes), requires
space for the immutable candidate plus retained v1 and qualified backup, and
must measure the actual free-space margin including temporary indexes. Do not
rely on the reported 5.3 GB value as a permanent capacity figure.

The recommended first migration uses a planned no-writer window. All CLI/MCP/
watch/refine/monitor/maintenance processes must be inventoried and stopped or
fenced; C1/export alone do not stop an old process that reads without locks.
No rollout authorization is supplied here.

1. Land a dual-format-aware release while v1 remains selected. Its launcher,
   reader entrypoints and writer admission reject unsupported backend/version.
   Qualify restore and reverse materialization in scratch before live cutover.
2. Under a fresh exact-resource grant, qualify a usable recovery artifact and
   establish the no-writer window. Resolve all outstanding v1 incremental
   transactions using their original runtime/authority first. Any unresolved
   APPLYING/PREPARING state blocks cutover; never translate a bound journal
   in place or assume today's reported wedged transaction has been cleared.
3. Retain the original flat file and its identity/digest. Stream it once into
   private v2 staging with bounded buffers/open-file count, a temporary disk
   index if needed, exact owner strings, raw bytes, duplicates, blanks, malformed
   lines and unterminated final line. Do not perform implicit compaction or
   infer 'current' rows from Chroma during import. Oversized/invalid inputs
   require a documented refuse/preserve path, never silent deletion.
4. Build the source descriptors/directory, fsync all candidate files/directories,
   and validate by re-materializing: full byte SHA, byte count, line count,
   per-source bytes, duplicates/ordering and opaque rows must equal v1.
   Compute separately labeled logical-ID and recovery evidence. This second
   full pass is migration cost, never a commit fast-path cost.
5. Write a durable migration intent naming old identity, candidate closure,
   final path, supported runtime and migration stage. Under C1/export and the
   no-writer window, rename old file to a retained v1 path and candidate directory
   to the configured path; fsync each parent. File-to-directory replacement is
   **not** one atomic rename over the old regular file. An intermediate missing
   path is expected and all entrypoints refuse while migration intent is pending.
6. Recovery of interrupted migration uses the bound intent: before old rename,
   remain v1; after old rename/before candidate rename, either finish verified
   candidate publication or restore the verified old path; after candidate
   rename, validate closure and complete the format state. Ambiguous, unexpected
   or hash-mismatched paths stop for owner disposition. Never create an empty
   export in response to the intermediate missing path.
7. Verify migrated format/closure and grant bindings, produce the required
   post-migration qualified snapshot, then retire the migration intent durably
   and admit only supported processes. Keep retained v1 and intent evidence
   until separately authorized retention. An old runtime must not be restarted
   against v2 merely by turning the incremental feature flag off.

**Rollback of the software/storage change:** before cutover, discard only
unpublished candidate state under its retention rules and keep v1. After
cutover, quiesce writers again and resolve all v2 transactions with the v2-aware
runtime. Pin the **latest** root and materialize its exact logical raw view to
a new flat file, fsync and verify bytes/IDs/order. Use a reverse migration
intent and the same fenced two-rename procedure to retain v2 and install v1.
Qualify the restored v1 recovery profile before restarting old code. Reverting
to the original 5.3 GB pre-migration file after new commits would lose data and
is not a valid software downgrade. Physical inode/object layout need not
match v1; the materialized logical bytes and surviving corpus state must.

## 10. Acceptance gates and hermetic proof design

These are required future tests/measurements, **not results from this design**.
Migration and full diagnostic/backup work are measured separately from source
commit; normal indexing may not secretly invoke them after returning its
commit result.

### 10.1 Export I/O bound

Define `D = S_old + S_new + 128*(n_old+n_new)` to include per-row descriptors.
For successful source replacement and a source rollback, count all export
data, descriptor, directory-node, publication-record and export-before-image
journal bytes read/written. Proposed executable ceiling per operation:
`12*D + 2 MiB`, with at most 64 directory levels per source lookup/update.
Implementation must show its accounting fits this ceiling, not tune the
ceiling upward to fit a scan. Hashing/validation reads and failed attempts
are charged. A fixed-count fault/retry scenario gets that count times the
same bound; repeated recovery cannot accumulate a history scan.

Mandatory structural assertions: no foreign raw segment is opened by source
commit/rollback; no whole-export iterator, catalog walk or compaction occurs;
the number/bytes of fixed directory operations are bounded; no dependency on
the number of previous generations. Audit `read`, `pread`, mmap faults and
writes, not only high-level Python `open` calls. Report actual disk bytes and
`rchar` separately; warm cache must not hide a full scan. Include the retained
journal/object and fsync overhead in physical write observations.

### 10.2 C1 latency

Target: **each measured uncontended one-chunk commit holds C1 for less than
5.0 seconds** on the declared qualification host, for both warm and cold-ish
cache series. Time every C1 acquisition from successful flock to release,
report the maximum continuous hold and total hold per operation; separately
report source/C1 wait, Chroma session, export lock, hashing/fsync, publication,
and full command wall time. Averages or p95 alone cannot certify this target.
Run a waiting foreign writer to show it proceeds after the measured bounded
hold. Scheduled maintenance wait is a separate operational metric, not hidden
inside the source operation's latency result.

The baseline also performs whole-collection non-source Chroma inventory scans
(`_non_source_collection_digest`, `_snapshot_before_images`,
`_verify_non_source_collections`), source projection fingerprinting and processed/
dedupe work. Export redesign alone does not prove the five-second target.
The full coordinator benchmark must keep these real checks enabled. If they
dominate, mark end-to-end acceptance FAIL and return the measured cause for a
bounded follow-up design; do not stub, remove or weaken rollback/isolation checks
to obtain a passing number. An export-only PASS is a partial result.

### 10.3 Hermetic benchmark shape

Use synthetic nonsparse exports of 10 MiB, 100 MiB, 1 GiB, 5.3 GB and 10.6 GB
(record exact bytes and decimal/binary units). Keep one source's preimage and
one-chunk replacement fixed, initially at no more than 128 KiB each; increase
foreign row count and separately foreign row size. A second series varies
owned source size, and a third adds many obsolete generations while holding
the current source fixed. Baseline v1 should expose its linear scan slope;
candidate v2 must satisfy the same absolute source-I/O bound at every size.

Run both a storage-level harness and the actual coordinator using real isolated
Chroma plus deterministic fake providers. Keep source before-image, expected
units and lock timing equivalent between baseline and candidate. One series
holds Chroma inventory fixed as foreign export grows, isolating export cost;
another grows the real foreign Chroma population to expose remaining C1 costs.
Use at least 30 measured one-chunk commits per size/cache condition, preserve
all samples, and report maximum, median, p95 and failures. Warmups and synthetic
fixture construction are outside the timing but recorded. Candidate source
commit is timed after explicit migration, not charged a hidden first-use scan.

Before imports, collection or subprocess launch, use an allowlisted environment
with disposable HOME/XDG/config/data/cache/TMPDIR and no provider credentials.
Deny network in the worker; fake-provider code raises if a real endpoint is
attempted. Use the existing qualified isolation patterns rather than production
CLI/config. Fixtures and benchmark evidence live only in the scratch root.
Record exact baseline/candidate SHA, Python/dependency versions, OS/filesystem/
storage, cache method, CPU/memory limits and instrumentation overhead. Use
per-file advice/new fixture files for cold-ish runs; do not globally drop host
caches or require production disks. A process-kill/fsync-injection test is not
a claim of proven hardware power-loss recovery.

### 10.4 Required regression/fault matrix

- Empty/absent/new source; zero-row replacement; stable source IDs with changed
  payloads; shorter/longer rows; Unicode and escaped source paths; duplicates
  within/across owners; blank/malformed/non-object/oversized rows; absent ID;
  missing final newline; exact migration round trip and compaction no-op.
- Replay after each durable edge in §6, repeated SIGKILL, partial file write,
  ENOSPC, rename/fsync errors, torn CURRENT, missing object and stale stage.
  Every run converges to a validated old/new source view or explicit refusal;
  no mixed source view is returned as complete and no provider call repeats.
- Rollback authority absent/altered/truncated/wrong source; forged unexpected
  source row; old ID with altered payload; valid-hash but wrong transaction
candidate; wrong UUID; source disappearance and purge during follower replay.
  Original journal SHA stays unchanged and doctor sees durable tamper evidence.
- Foreign append/replace/purge between crash and recovery; rollback preserves
  foreign current bytes and source preimage, with §5 ordering expectations
  asserted explicitly. Root rewind must be a negative control that fails.
- Ledger recovery duplicate/malformed refusal, exact-match durability,
  verified-base replacement, conflicting projection, uncertain export outcome;
  monitor/verify forwarding and generic observation multi-match semantics.
- Reader pins old root while another writer publishes; multi-owner purge
  atomic root; stale compaction candidate; lock-order inversion; unsupported
  old reader/writer; alias/store-UUID retargeting; unclassified new durable file.
- Complete-data/Safe Harbor capture and scratch restore of v1 and v2, incomplete
  closure refusal, retained incident preservation, interrupted forward/reverse
  migration and downgrade after new writes. Check R2b/Shadow inventory coverage
  from generated final-tree evidence, not hand-maintained success claims.

Reuse/extend existing incremental state/bootstrap safety, issue-286 wedge and
tamper, compaction golden/SIGKILL, purge/lock, Safe Harbor recovery, complete-data
restore and inventory suites. Add negative controls that deliberately scan a
foreign segment or run post-index compaction: the performance gate must fail
even on a warm cache. No new tests are implemented or executed by this document.

## 11. Risks, open questions for Kiro, and handoff

The largest cost is coordinated format adoption across every export consumer
and recovery profile. This is larger than changing `_reconcile_export`, but
the flat-file atomicity contract is the reason that local change cannot meet
the I/O bound safely. Retained segments consume disk until a separately proven
retention mechanism exists. The directory has more metadata/fsync operations;
the proposed fixed ceilings and measured latency, rather than assumed fast
hash lookups, determine acceptance.

Kiro's review questions, with a proposed answer for each:

1. **Accept C's format migration rather than the append-log alternative?**
   Recommend yes: the immutable source boundary serves commit, rollback and
   snapshots with one publication rule. If migration scope is unacceptable,
   return for redesign; do not approve append without complete reader adoption.
2. **Accept the explicit rollback ordering rule when foreign rows were deleted
   or reordered after the snapshot (§5), and the malformed-tail refusal (§3.3)?**
   Recommend yes, preserving original source positions and current foreign
   relative order. This is the one known
   rollback-order delta requiring an explicit verdict; exact v1 rank compatibility
   would require additional design, not an undocumented fallback scan.
   Refuse ordinary mutations of an export with an unterminated tail instead of silently
   repairing it or publishing concatenated malformed JSON.
3. **Is targeted hash verification plus full qualified snapshot/audit sufficient?**
   Recommend yes with honest evidence labels. No source-proportional design can
   freshly hash arbitrary unrelated bytes. Reject claims that a root digest
   alone proves current physical integrity of the entire export.
4. **Are the dual-format recovery boundaries and downgrade gates complete?**
   Recommend refusing cutover with any unresolved old transaction, preserving
   both formats' authority validators and requiring updated Safe Harbor/
   complete-data profile acceptance before live migration.
5. **Are the I/O ceiling and strict five-second host-qualified gate appropriate?**
   Recommend the stated bound and full-coordinator measurement. Treat remaining
   Chroma census cost as a real blocker if observed, not an exemption.

No Kiro review is represented as completed. After Kiro's written direction
review and Ryan's approval, Codex can shape a bounded execution plan for Cursor,
including the named compatibility-owner reviews and hermetic proof. Migration,
runtime promotion, provider use, indexing and live activation need their own
explicit grants. No PR is opened for this delivery.

**I finished:** [Arc Codex #286] Architecture direction and acceptance design.
**Next step:** Kiro reviews this exact document and the five questions above.
**Next lane:** Kiro; Ryan decides direction approval afterward.
**See my work:** this file, especially §§2, 5, 7, 9 and 10.

**TL;DR:** [Arc Codex #286] Choose immutable per-source segments with a bounded
copy-on-write directory and atomic root publication. Commit/rollback export
I/O becomes source-proportional; recovery authority, consumer-specific duplicate
rules and snapshot qualification remain mandatory. Coordinated migration,
rollback ordering and stricter malformed-tail refusal require Kiro review.
Five-second C1 performance remains an unmeasured acceptance gate, not a claimed result.

<!-- src: ../../incremental_jsonl.py, ../../export_compaction.py, ../../ingest.py, ../../observe.py, ../../propose_decision.py, ../../bootstrap_supersession.py, ../../chroma_write_store.py, ../../source_purge.py, ../../complete_data_restore.py, ../../recovery_authority.py — pinned bd37946 source contracts -->
<!-- ref: ./STATUS-codex-jsonl-production-integration.md, ./STATUS-safe-harbor.md, ./STATUS-r2b-capture-auth.md, ./STATUS-shadow-ledger-phase0.md, ../planning/ARCHITECTURE-PLANNING.md — review routing and compatibility boundaries -->
