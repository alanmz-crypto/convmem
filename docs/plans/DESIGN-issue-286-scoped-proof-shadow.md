# [Arc Codex #286] Qualify source-scoped mutation proof in shadow mode

**Decision:** implement an opt-in shadow observer for incremental commits. Run
the proposed source-scoped policy alongside the existing full pre/post digests,
record disagreements and missing coverage, and let the existing full path make
every commit/recovery decision. This slice removes **zero** inventory scans.
Removing the two remaining scans is a later, explicitly approved substitution
of evidence, conditional on §9. Envelope externalization is excluded.

**Who / what / when / why / how:** Codex, 2026-10-18, designs the next bounded
commit-cost slice for Ryan and Kiro. Slice 1, the redundant digest removal
PR `#404`, is on fetched `origin/main` at
`07117ed6196292b3156c0e165dd69e84fe967cdd`. Ryan reports it deployed. The remaining
two digest phases account for approximately 144 seconds per measured one-chunk
commit. Shadow observation tests the proposed cheaper proof without making it
commit authority. Kiro reviews this document next; Ryan grants implementation
and any later production experiment separately.

**Planning Status:** Execution Planning; Task Decomposer, Dependency Mapper,
Scope Guardian; function Planner. Codex authors, Kiro reviews, Cursor implements
after Ryan's grant. Ryan's present request authorizes this execution-ready
design, branch and push only. Stop: Await HITL after Kiro review.

## 1. Inputs, freshness and boundaries

The parent design is `docs/plans/DESIGN-issue-286-commit-cost-reduction.md` at
`a827ee1f808970ebb869ffe54b348d88911ce1af` on
`origin/docs/2026-10-17-issue-286-commit-cost-reduction`. Kiro's conditional review
is `docs/inter-model/KIRO-2026-10-17-issue-286-commit-cost-reduction-review.md` at
`fc56151f6cff0a1fc7cfaeacc7043441122e0569` on
`origin/docs/2026-10-17-issue-286-commit-cost-review`. These files are on separate
branches, not this main baseline; retrieve them with `git show <ref>:<path>`.
This document supersedes the parent's envelope-before-shadow sequencing only.
Its proof limits, recovery obligations and Gates A/B remain binding.

Kiro's Slice 1 deploy review, on
`kiro/2026-10-18-issue-286-commit-digest-reuse-deploy-review` at `483b14c`, accepted
live timing for that slice's saving. That exception does not waive this slice's
hermetic qualification or confer a Gate A/B pass.

Ryan supplied these live `incremental_commit_phase_timing` observations:
`non_source_digest` approximately 72 s, `verify_non_source` approximately 72 s,
`before_images` approximately 25 s, `export_reconcile` approximately 19 s;
C1 hold approximately 190–220 s; whole-run median 215 s, previously 295 s.
Sample count, host/cache distribution and paired raw events were not supplied.
These are planning inputs, not measurements rerun by Codex or a complete
additive trace. Whole-run time includes work outside a prepared commit.

Startup doctor passed, with warnings including the existing APPLYING transaction
`46313d437ae4446282a752270770c614` (`recovery_unproven`). This design does not
repair, convert or retry that transaction. The arc STATUS/LATEST documents lag
deployment; under Ryan's one-document scope they remain unchanged. Repository
reads and the supplied evidence establish this slice's baseline. Corpus search
returned unrelated older Gate-B material and supplies no evidence for this slice.

Scope is the incremental commit's Chroma mutation observation, local diagnostic
receipts, tests and timing. Here **SHADOW** means a proof observer, not the
separate Shadow Ledger arc or its optional mutation sink. No provenance format,
export format, compaction, live config/runtime, provider, recovery authority or
cross-arc operation is changed by this design delivery.

## 2. Existing seams and the precise claim

All code coordinates below refer to baseline `07117ed`:

- `incremental_jsonl.py:_commit_generation` takes source then C1 locks, captures
  the full attempt baseline, reuses it in `_snapshot_before_images`, writes the
  immutable rollback journal and APPLYING transaction, applies/prunes, and runs
  `_verify_non_source_collections` before checkpoint publication. Export/dedupe
  follow under C1; processed/cleanup follow outside it.
- `_restore_replay_before_images` takes a fresh full attempt baseline; replay
  retains the original journal SHA through `_require_rollback_authority`.
  This distinction protects foreign commits made between attempts.
- `chroma_store.py:179`, `_native`, obtains the collection after native-guard
  reload. Observe final arguments here, inside the guard, after reload.
  Completion is recorded only after the guard context exits successfully:
  native API return alone does not establish successful guard finalization.
- `chroma_write_store.py:1029`, `_IndexWriteGuardedChromaStore`, blocks `client`
  access but returns `_collection` under C1. A caller with that handle can issue
  mutations outside `_native`. C1 possession alone is not source ownership.
  This is a concrete **promotion blocker**, not evidence of a live exploit.
- `snapshot_source_rows` reads source-owned documents, embeddings and metadata;
  `ids_for_source` uses an exact owner predicate. `_apply_prepared` can select a
  different physical ID after provenance/dedupe decisions. Observe the final
  ID, not just the original prepared ID. Foreign dedupe suppression is not
  permission to mutate the matched foreign row.

The candidate claim is **causal isolation**: all mediated calls in this attempt
target only authorized source rows, under the supported backend's exact-ID
semantics. The full digest additionally observes foreign membership, metadata,
documents and embeddings at two points. A compliant call census cannot detect
backend corruption or an out-of-boundary edit to an untouched foreign row.
The scheduled Chroma audit checks vector loss/segment validity; **it is not a
compensating control for this loss, at any cadence**. A future periodic content
audit would still not restore immediate per-commit observation.

Options considered: switching directly to scoped enforcement would combine new
prevention, new recovery evidence and removal of the independent oracle; defer
it. Externalizing envelopes first would expand reader/restore compatibility and
still leave the two full scans; defer it. Shadow-first is chosen because it
exposes false acceptance, false rejection and overhead while preserving today's
decision path. Its cost is extra work before any speedup.

## 3. Modes and noninterference contract

Add a strictly parsed `index.incremental_jsonl.mutation_proof_observer` setting
with values `off` (absent/default) and `shadow`. Invalid values, including
`scoped`, refuse configuration before an operation begins. No production scoped
switch or environment-variable shortcut ships in this slice. An admitted
operation's frozen config selects observation; the observer cannot widen source
admission or select a new Chroma root.

**OFF:** identical mutation calls, journal/checkpoint schemas, scan counts and
error handling to Slice 1; no new proof files or ownership lookups.

**SHADOW:** authoritative evidence remains `full_inventory_v1`. Diagnostic
schema is `scoped_writes_shadow_v1`; its policy identifier is
`scoped_writes_v1`. A diagnostic `would_deny` never denies a native call. It
records what the proposed policy would do while the original route proceeds.
No shadow result changes return status, checkpoint/export/processed publication,
retry, quarantine, paid work, rollback selection or cleanup of original state.
Ordinary old guard/store failures still act exactly as before.

This means invalid writes injected into a disposable SHADOW fixture may reach
Chroma and then fail today's full check. Never inject those controls in
production. Prevention tests and causal coverage tests are separate evidence.

Observer failures are caught only around observer-owned reads/serialization/
diagnostic I/O. Never wrap the actual native call or guard exit in a broad
"ignore observer error" handler. Process termination and original storage
errors propagate normally. Extra reads/fsyncs can affect latency; no-change
means unchanged decisions and authoritative artifacts, not zero overhead.

## 4. Scope construction and native observation

### 4.1 Immutable attempt context

After source/C1 acquisition construct a fresh attempt UUID. After original
rollback publication, bind the observer to its SHA. The context contains:
canonical target identity, actual collection UUIDs plus names for both
collections, exact canonical `source_path` and source identity, transaction ID,
attempt ID, generation/prepared-artifact commitments, rollback SHA, runtime
revision and observer/policy versions. Missing collection identity or binding
is `incomplete`, never inferred from a matching name. No collection creation is
performed to make observation succeed.

Use independent frozen copies of the existing source snapshots on fresh
attempts. A replay uses a fresh current source census for observation while
binding to the unchanged original journal. Build per-collection owned-ID sets
and authorized candidate descriptors from prepared data; include deterministic
provenance-derived physical IDs. At the actual write, validate the relationship
between the final ID/payload and its descriptor. Do not authorize arbitrary IDs
merely because a caller adds them to a set during `_native`.

The initial owned set, candidates and attempted writes define k. Proof work is
O(k) returned rows and receipt bytes, **not** O(new chunks). Large source
histories can remain expensive. No all-collection scan is allowed inside the
observer, even while the authoritative full digests continue separately.

### 4.2 Per-call policy

At `_native`, inside native serialization after client reload and before the
underlying API call, freeze the actual operation/IDs/payload descriptors. Resolve
target ownership by explicit IDs in that same serialization interval. Read only
IDs and ownership metadata for a collision; read payload/vector only for owned
rows whose post-state is being certified. No foreign payload census.

The pure policy evaluator returns `allow`, `would_deny(reason)` or
`incomplete(reason)` and implements these rules:

1. Only the bound target and two bound collection identities qualify. Require
   source lock, C1 and native serialization in their existing order. The C3
   shared writer lease is admission, not an exclusive commit lock.
2. Support explicit nonempty, duplicate-free ID batches for add/upsert/update/
   delete. No unrestricted `where`/`where_document`, reset, create/drop or
   unknown mutation. Existing prune helpers already lower owner predicates to
   explicit IDs; no new predicate expansion in the observer.
3. Existing targets must have the exact owner. Ownerless/foreign rows and
   ownership transfers fail policy. New targets must be absent, valid bound
   candidates and carry the exact owner. An update/delete of an absent target
   fails policy unless that absence is an explicitly modeled replay no-op.
4. Match final payload commitments and ID derivation to authorized descriptors;
   updates preserve ownership, omitted metadata preserves the verified owner.
   A foreign exact-dedupe hit can suppress a call but cannot authorize an update.
5. Same-thread nested sessions inherit the attempt without widening it. Bind
   PID, process start and thread identity; another thread or fork must not
   inherit authority through a copied token. Record unbound/nested widening as
   missing coverage or would-deny. No new blocking lock order is introduced.

Record intent immediately before the call, then API-return outcome and guard
completion separately. Read back explicit touched owned IDs under the same C1
interval; verify final document/metadata/vector values or absence against the
expected operations. If an ID changes owner, do not fetch its foreign payload
or declare success. Preserve operation order: insert-then-prune is valid;
omitted/reordered/duplicated operations are not a complete sequence.

### 4.3 Honest coverage boundary

In SHADOW, a context carried through `_native` proves only what it observed.
Track native calls, IDs, intents, returns and finalized outcomes independently;
an empty census is not a successful proof for a nonempty apply. Maintain a
static inventory of supported production writers, raw clients/collections,
aliases, dynamic dispatch, nested sessions, collection lifecycle and recovery
routes, with an owner/disposition for each. Regenerate it at the candidate SHA.

Use independent low-level mutation spies in tests to compare actual calls with
observer events. A raw-handle bypass must make the coverage test fail even if
the full digest passes because the bypass touched only an owned row. Do not use
the observer's own counter as its only coverage oracle. Report unresolved raw
access as `coverage_unqualified`; a compliant observed census remains diagnostic.
Closing production bypasses is a required later enforcement change, not a
behavior change smuggled into this shadow slice.

## 5. Diagnostic evidence and storage

Write attempt-local append-only records under the already admitted incremental
source state directory: `scoped-shadow/<transaction-id>/<attempt-id>.jsonl`.
Generate path components internally; require containment, no symlinks, exclusive
creation, directory mode 0700 and file mode 0600. Do not append to rollback,
transaction, prepared files or checkpoint. Register/classify the new subtree
and affected paths in existing StateSpec/backup inventories before live use;
diagnostics confer no recovery authority. Existing restore qualification cannot
be weakened merely to accommodate them.

Records contain schema/policy version, full-mode tag, scope binding, monotonic
sequence, previous-record hash, phase, collection/operation, explicit target IDs,
owner-check disposition, payload/pre/post commitments, and API/guard outcomes.
Keep source paths and row IDs in this private file only; never log documents,
vectors or envelope bodies. A hash chain detects broken sequencing, not a
malicious actor who can rewrite the file. Hash exact typed logical values with
the existing comparison semantics; introduce no provenance/hash redefinition.

Fsync the header and parent, each intent before its associated call, completion
after guard success, and terminal summary. These timings approximate the future
receipt cost. In SHADOW, an fsync/write/read failure disables clean qualification
for that attempt and lets the full path continue. The writer journal records a
bounded `incomplete` diagnostic best-effort. Neither sink available means the
attempt has no qualifying evidence; it is not counted as a success.

Bound memory by streaming records and hashing payloads. Initial diagnostic caps:
8 MiB per attempt, 64 MiB per source retained files. Reaching a cap produces
`incomplete:capacity`, stops recording that attempt and leaves indexing behavior
unchanged. Charge/check only this source's directory; never scan all receipt
history. No automatic deletion of mismatch, interrupted or unreviewed receipts.
Increase limits only in a declared qualification fixture/configuration; report
all saturation and disk usage. These caps qualify diagnostics, not future
recovery storage. Later authoritative receipts need separate retention rules.

Terminal evidence includes full result (`equal`, `changed`, `not_reached`),
candidate result (`observed_compliant`, `would_deny`, `incomplete`), coverage
qualification, all reason codes, timing/call/row/byte counters and final
authoritative operation outcome. Publish a compact new
`incremental_scoped_proof_shadow` event without raw identifiers or payloads.
Do not alter the existing timing event's field contract. Interrupted attempts
lack a terminal record and are incomplete; never turn a surviving intent into
completion by inference. Readers reject unknown diagnostic schemas for
qualification without affecting original recovery.

## 6. Comparison and failure semantics

Capture full comparison outcome without taking a third scan. Observe the value
already produced by `_verify_non_source_collections`; preserve its exception.
An outer `finally` attempts diagnostic finalization on success and ordinary
failure. A kill may leave only an incomplete file.

- **Full equal + candidate compliant:** observed agreement, qualified only if
  all required coverage is established. This alone never proves mediation.
- **Full equal + candidate would-deny:** record policy disagreement. Full mode
  may have permitted a foreign attempt that was a no-op or restored itself, or
  the candidate policy may be too strict. Preserve full behavior; investigate
  before promotion. No automatic "false positive" classification.
- **Full changed + candidate compliant:** record detection-gap disagreement and
  preserve `non_source_isolation_changed`. On a deliberately injected untouched
  foreign content edit this is the expected limitation; on an ordinary run it
  blocks promotion pending diagnosis and a new clean qualification cohort.
- **Full changed + candidate would-deny:** both saw a problem, but only the
  full digest establishes observed changed state. Do not merge their meanings.
- **Any incomplete or full not reached:** not a passing sample. Report the
  actual phase/error without inventing a comparison or declaring equality.

Shadow ownership/census failures use diagnostic reasons such as
`foreign_target`, `owner_missing`, `scope_binding`, `unmediated_call`,
`incomplete_census`, `receipt_io`, `post_state_mismatch`, `native_unknown` and
`guard_invalidated`. They do not create new production refusal codes in this
slice. Later enforcing mode must distinguish `scoped_write_denied` and
`scoped_census_incomplete` from `non_source_isolation_changed`.

Native exceptions, partial batch effects, cancellation, guard finalization
failure, segment restoration or integrity/quarantine evidence invalidate clean
candidate evidence. Use existing containment/recovery decisions; do not clear
an incident or certify restored segment contents from a source receipt.
Capture guard state at entry/exit through its existing authority interface;
if a trustworthy no-restore/no-unknown outcome cannot be obtained, mark incomplete.
No Safe Harbor repair operation is added here.

On restart use the original transaction protocol, fresh full attempt digest
and original journal SHA. Start a new observer attempt if enabled; old diagnostic
files cannot authorize replay, replace a before-image or trigger another paid
transform. Foreign commits between attempts must survive. Checkpoint-before-
export, processed-state ordering, `rollback_export_tamper`, exact source bytes,
foreign export bytes and existing retry budgets are unchanged. The known wedged
transaction is exercised only as a synthetic shape, never repaired for this slice.

Disable observation to roll back this slice's feature; retained diagnostics are
inert. No data migration, journal rewrite or old-checkpoint conversion is needed.
Separately honor the existing runtime/transform compatibility admission on any
deployment or downgrade; diagnostic-only changes are not a blanket deploy grant.

## 7. Bounded implementation tasks after approval

All tasks are serial, owned by Cursor after Ryan's Execute grant. Existing arc
verification companion: `docs/plans/VERIFY-codex-jsonl-production-integration.md`;
the implementer adds a clearly separate commit-cost-shadow evidence section
when authorized. No new VERIFY or handoff file is created by this design-only turn.

**T1 — Policy and coverage specification.** Add a small proof module (proposed
`incremental_mutation_proof.py`) with immutable context, pure policy and typed
diagnostic schema; strictly parse off/shadow in `config.py`. Inventory writer
routes and physical-ID derivation. Unit tests cover policy/serialization and
independent coverage spies. Exit: no unknown route is silently marked covered;
known bypasses are explicit promotion blockers. No enforcing production mode.

**T2 — Shadow observation and bounded receipts.** Wire `incremental_jsonl.py`,
`chroma_store.py:_native` and internal session context in `chroma_write_store.py`.
Add only read-only guard-status observation if needed; preserve guard behavior.
Use the admitted state root and classify the diagnostic subtree in
`complete_data_restore.py`/affected-path inventories as needed. Exit: off/shadow
differential tests demonstrate identical authoritative behavior and rollback
bytes, including observer failures; full scan budget remains exactly two per
collection for a fresh one-chunk commit. Stop for review if a required hook
would change a guard/recovery decision or require a new cross-arc contract.

**T3 — Adversarial and recovery qualification.** Add focused tests (proposed
`tests/test_issue_286_scoped_proof_shadow.py`) plus real isolated Chroma cases.
Run §8 positive/negative/fault tests and affected existing suites. Exit: every
specified mutant is caught; no production file/provider is reachable; failures
and missed coverage are retained. Report enforcement obligations still open.

**T4 — Performance and handoff evidence.** Produce the paired measurements in
§10, raw samples and code/dependency/fixture identities in the authorized VERIFY
section. Exit: shadow overhead budget and structural criteria pass; label Gates
A/B independently PASS/FAIL/NOT_MEASURED. Kiro reviews exact code+evidence.
This ends the implementation slice. Production shadow observation, production
scoped enforcement and removal of full digests each require later authority.

## 8. Required tests, including controls that must fail

Run tests in a network-denied child with disposable HOME/XDG/config/data/cache/
TMPDIR set before imports, credentials removed, fake deterministic providers,
real scratch Chroma and actual coordinator/locks/guards. Synthetic non-sparse
envelopes/vectors/transcripts only. No live Chroma copy or provider endpoint.
Production-path and network escape controls must be refused before access.

**Behavior parity:** compare OFF versus SHADOW on identical frozen fixtures and
controlled IDs/clocks: native arguments/order, results/refusals, checkpoint,
transaction and original rollback bytes, export bytes/order, processed state,
prepared reuse and paid-call count. Compare diagnostic files separately. Cover
new/existing source, one/multiple chunks, empty result, source exclusion, prune,
same-source suppression, foreign suppression and provenance-derived physical ID.
Run admitted Codex and supported Kiro fixtures; never widen adapter admission.

**Policy/coverage:** foreign collision; missing owner; attempted ownership change;
wrong root/UUID/source/transaction/attempt/SHA; broad delete; duplicate IDs; new
candidate with wrong derivation; unknown op/create/drop/reset; nested unscoped
session; thread, fork/subprocess and stale client; raw collection handle. In
SHADOW these record would-deny or incomplete while preserving baseline behavior.
Use disposable low-level spies to show whether a call actually occurred.
Pure evaluator tests are not proof of pre-native enforcement (§9 requires that
separately on the eventual enforcing implementation).

**Differential negative controls:** bypass `_native` with an owned-row raw write
and assert the independent coverage test fails; remove one receipt and assert
completeness fails; make the candidate always allow and assert policy tests fail;
omit derived physical IDs and assert valid-case parity fails. Mutate a foreign
row's document, metadata, vector and membership separately, leaving touched
source rows valid: full comparison must detect it, candidate may remain compliant,
and the detection-gap event must be recorded. Include a foreign no-op/transient
write undone before the full post-scan: census policy can reject while digest
equality alone does not establish safe calls.

**Failure injection:** stop before/after header, original rollback/APPLYING,
intent/fsync, native call/partial batch, API return, guard exit, completion,
post-read, full comparison, checkpoint, export rename/fsync, processed and
cleanup. Inject observer-only ENOSPC/short write/fsync/read failure, caps,
truncation, duplicate/gap sequence, wrong hash and unknown schema. Assert SHADOW
does not change original outcomes; incomplete receipts never pass. Native and
guard failures remain failures, not swallowed diagnostics. Recovery uses original
authority and fresh full baselines; foreign intervening commits survive; replay
does not repeat paid transformations. Retain existing export tamper tests.

**Accounting controls:** accidentally add a third full digest, remove the post
digest, read all foreign payloads from the observer, do unbounded receipt scans,
or run synchronous/post-return compaction; structural/performance tests must
fail. OFF emits no observer I/O. No reference format is introduced, so the
parent's re-inline-envelope mutant belongs to the deferred representation slice.

Existing regression surfaces include `test_issue_286_commit_digest_reuse.py`,
`test_incremental_jsonl_isolation.py`, `test_incremental_jsonl_state.py`,
`test_incremental_jsonl_exact_path_recovery_parity.py`,
`test_incremental_jsonl_physical_keep_set.py`,
`test_governed_recovery_and_writers.py`,
`test_incremental_transform_compatibility.py` and watcher/canary timing tests.
Run applicable CI checks once after focused acceptance; record actual commands,
counts and failures. These are future requirements, not tests run for this doc.

## 9. Acceptance gates before any switch to scoped mode

**S — Accept the SHADOW implementation.** T1–T4 pass at one pinned revision;
two full inventories per collection remain on fresh commits; diagnostics never
alter authoritative outcomes; failure samples are not excluded from evidence;
the overhead budget in §10 passes. Kiro accepts the implementation and evidence.
This permits a request for production shadow observation, not scan removal.

**Q — Qualify shadow observations.** After a separate exact-runtime/config/source
grant, require at least 100 complete ordinary one-chunk shadow attempts over at
least 24 hours on the intended admitted source class, covering at least three
sources and both first and appended commits. Require zero unexplained full/
candidate disagreements, would-deny results, incomplete receipts, guard-invalidated
attempts or unaccounted attempts. Reconcile scheduled/started/terminal counts;
diagnostic loss is an evidence failure. Use hermetic replay/fault and large-source
results for shapes unsafe or unavailable live. Missing live source diversity
leaves Q incomplete; it does not authorize adding sources. Any unexplained event
stops qualification and requires diagnosis, correction and a fresh pinned cohort.
Intentional hermetic faults are separately labeled and must produce their expected
non-PASS results. A clean cohort supports the design; it does not prove mediation.

**M — Prove enforcing mediation on the exact promotion revision.** A subsequent
bounded implementation must close raw handles and all inventoried bypasses,
enforce policy before actual native calls, and provide measured complete coverage.
Native-entry spies must show **zero calls** for foreign/ownerless collisions,
scope widening, hidden/nested sessions, threads/subprocesses, raw handles,
unrestricted predicates and create/drop/reset. No unrelated writer may borrow
the active token. All participating writers obey C1 or are refused; stale/unfenced
processes are excluded by verified deployment admission. C3 attestation alone
is insufficient. A no-other-writer deployment window is required where older
processes cannot enforce admission. Tests against an evaluator or a mock wrapper
alone do not clear M. Safety/isolation changes receive the charter's targeted
independent audit and Kiro review. This slice does not implement that enforcement.

**R — Qualify authoritative receipts and recovery.** Later scoped evidence must
be versioned as `scoped_writes_v1`, bound to collection/owner/transaction/attempt/
runtime/original journal SHA, durably complete before checkpoint. Missing intent
durability denies before native call; missing completion/unknown outcome after
mutation preserves APPLYING and uses qualified recovery or refuses. Never fall
back to a newly computed full baseline after an unproven scoped mutation: it
cannot reconstruct the missing before-state. New attempts may select full mode
only before mutation under a valid full baseline and compatible journal.

The scoped transaction/journal decoder and protocol must explicitly distinguish
full and scoped evidence. No fabricated `non_source_collections_after`, no full
comparison PASS when unperformed, no unsupported schema acceptance. Old full-mode
journals always replay in full mode with their original SHA; config cannot convert
them. Initially keep replay/recovery/bootstrap and unsupported source shapes full
and label their cost separately. A new scoped journal still needs a qualified
recovery path for crashes; keeping legacy recovery full is not a substitute for
that test. Scoped recovery rechecks current ownership immediately before every
restore/delete; a now-foreign or ownerless target refuses instead of being
overwritten by an old source preimage. Reconcile every ID in an uncertain batch;
never assume a missing completion means no mutation. Downgrade resolves scoped
transactions using the capable runtime
before admitting an old decoder. Exact before-images, export tamper checks,
StateSpec/backup closure and Safe Harbor containment remain mandatory.

**P — Measure and accept the substitution.** The eventual scoped fresh path
performs zero full foreign inventories and no foreign payload reads solely for
isolation. Fixed owned source: added returned rows, receipt bytes and census work
remain bounded across the foreign-count sweep. Report backend lookup and segment
I/O separately; a hidden global scan fails qualification. Run matched full/shadow/
scoped fixtures and Gates A/B. Promotion requires a measured net commit saving
with no new correctness failure; a failed A or B remains explicitly failed and
cannot be called arc completion. Ryan may approve a partial improvement only
with those unmet targets stated in the grant.

**Human acceptance:** Kiro's exact-revision PASS and Ryan's explicit scoped-mode
grant must accept **loss of immediate per-commit detection of changes to untouched
foreign content**. The grant must not cite `chroma_audit` as compensation. Name
runtime, eligible sources/operations, evidence mode and rollback procedure.
S/Q do not clear M/R/P; no count of clean shadow runs auto-enables scoped mode.
This design carries Kiro C2-a–e and C4-a–g; it does not self-approve them.

## 10. Cost model, measurement and Gates A/B

**Expected phase effects:**

- `non_source_digest`, about 72 s: SHADOW saves 0; eventual scoped fresh mode
  removes this pass, gross saving about 72 s before new proof overhead.
- `verify_non_source`, about 72 s: SHADOW saves 0; eventual scoped fresh mode
  removes this pass, gross saving about 72 s before touched-row verification.
- `before_images`, about 25 s: no saving budgeted in either mode. It includes
  source snapshots and the export preimage scan; Slice 1 already removed its
  redundant inventory. Reusing source snapshots avoids duplicating work but
  does not remove the original recovery evidence or export pass.
- `export_reconcile`, about 19 s: no saving; flat JSONL remains linear in total
  export bytes. No staging, refs, compaction or asynchronous deferral here.
- `apply`, `journal`, projection fingerprint, checkpoint, dedupe, processed and
  cleanup: preserve existing work. Observer ownership/readback/hash/fsync adds
  cost, attributed to its actual parent phase plus separately labeled nested
  observer timing. Do not add nested subspans to the leaf-phase total twice.

SHADOW is expected to be slower by the measured observer overhead. Proposed
acceptance budget for the one-chunk fixture: paired median added C1/commit time
each <=5 s and p95 added time each <=10 s; report maximum and RSS/bytes too.
These are engineering budgets for this slice, not Gate B. Failure keeps
production shadow rollout gated; it cannot justify dropping full digests or
skipping receipt durability. Large-source overhead is reported separately.

Later scoped mode has a **gross** opportunity of about 144 s per comparable
fresh commit. Subtracting that from the supplied C1 range gives about 46–76 s
**plus scoped proof cost**. Subtracting from the whole-run median gives roughly
71 s plus proof cost, an illustrative arithmetic residual, not a predicted
median (unpaired phase summaries and whole-run samples cannot prove it).
The surviving measured before-image/export phases alone total roughly 44 s;
this slice cannot plausibly establish Gate B. Gate A is also unproven.

Use at least 30 measured commits per size/cache/contention condition, paired
baseline `07117ed` and candidate, interleaved after recorded warmups. Pin host,
dependencies, resource limits, fixture seed, CPU/storage/FS and code revisions.
Use the parent's synthetic live-shape fixture: 111,348 units, 5,106 summaries,
203,441 export rows and approximately 5.19 GiB actual nonsparse bytes. Vary
foreign Chroma rows 10k/~111k/2x with source and export held fixed; separately
vary export size and source history (at least 100 generations and 10,000 owned
unit rows). Vary envelope size and segment-save crossings. Cold-ish means fresh
fixture files/per-file cache advice, never host-wide cache dropping. Report
setup separately, all samples, failures, median/p95/max, lock wait/hold, CPU,
RSS, returned rows/bytes, read/pread/mmap work where observable, and logical vs
physical disk I/O. Sparse data/warm cache cannot conceal a scan.

**Gate A (unchanged):** every successful measured one-chunk prepared commit
<=60.0 s from commit entry through checkpoint, all followers and cleanup;
report source/C1 wait separately alongside total elapsed and the complete
deterministic-provider command. Include uncontended and bounded-contention
series with a waiting foreign writer making progress. Provider preparation and
fixture setup are not commit savings. Report failures as well as successes.

**Gate B (unchanged):** maximum continuous C1 hold **and total C1 hold per
operation** each <5.0 s on uncontended one-chunk fixtures, warm and cold-ish,
including ordinary segment-save thresholds, while preserving Gate A. Repeated
small acquisitions cannot hide a long total hold. Report large-source and
fault/recovery latency separately. Never infer either gate from the other,
the live median, a plan PASS, merge or a structural scan reduction.

Keep full audit, fixture construction, backup qualification and any later
maintenance separately budgeted. No hidden synchronous/post-return compaction.
Failure to hit a gate does not authorize disabling guards, dropping fsync or
weakening recovery.

## 11. Envelope boundary and deferred work

This shadow implementation consumes current inline metadata and commits opaque
typed values; its policy needs ownership and exact payload/identity bindings,
not an envelope side store. It can ship, be disabled and be evaluated without
changing provenance consumers or on-disk representation. That establishes its
independence from externalization.

An export-only envelope slice could later be measured independently while
Chroma remains inline, as Kiro required. Its safety is **not yet qualified**:
consumer inventory, immutable commitment-plus-variant objects, resolver failure
semantics, capability fencing, epochs, original-journal handling and restore
closure remain separate obligations. This document therefore includes no envelope
implementation, migration or associated saving. A later format change must
requalify this proof against logical/physical values; no old hash meaning changes.
The unresolved transaction remains a migration blocker under its original
authority. No live compaction is authorized; export row counts do not establish
duplicates or justify historical-row deletion. Option C remains deferred.

## 12. Review and delivery

Kiro should decide whether T1–T4 are bounded and execution-ready, whether shadow
failure noninterference and the explicit unqualified-mediation label are sound,
and whether S/Q/M/R/P are sufficient before a later scoped substitution. Ryan
then decides a Cursor implementation grant. No reviewer should read this design
as a production shadow grant or permission to remove scans.

Design validation in this turn: read the pinned parent/review, Slice 1 code and
deploy review; traced apply/replay/native/guard seams; checked documentation diff
and whitespace. No implementation tests, benchmark, live migration or recovery
were run. Only this design file changes; no PR is created.

Suggested later PR title: **Plan shadow validation before removing commit scans**

Suggested later PR description: Ryan can review the next commit-cost slice with
the full isolation checks retained. Codex authored this Arc Codex design on
2026-10-18 after deployed Slice 1; Cursor would add opt-in shadow observations,
bounded receipts, adversarial tests and phase measurements after Kiro review and
Ryan's grant. It defines separate mediation, recovery and acceptance gates for
later scoped mode. Documentation only; source contracts and whitespace checked.
Merge reading: `docs/plans/DESIGN-issue-286-scoped-proof-shadow.md`.
TL;DR: qualify the cheaper proof alongside full digests before accepting its
narrower detection coverage. This is supplied text, not a request to open a PR.

I finished: [Arc Codex #286] Execution-ready shadow-proof design.
Next step: Kiro reviews this exact document, especially §§3–6 and §9.
Next lane: Kiro; Ryan grants any subsequent Cursor implementation.
See my work: `docs/plans/DESIGN-issue-286-scoped-proof-shadow.md`.

**TL;DR:** [Arc Codex #286] Ship opt-in SHADOW observation with both full digests
authoritative. Record disagreements, gaps and failures without changing commit
decisions. Later scoped mode requires real prevention, versioned recovery,
measured savings and explicit acceptance of lost untouched-row detection.
Its gross opportunity is about 144 s; SHADOW saves zero, and Gates A/B remain
unproven. Envelope migration and live compaction are excluded.

<!-- src: ./DESIGN-issue-286-commit-cost-reduction.md — a827ee1 on the parent design branch named in section 1 -->
<!-- src: ../inter-model/KIRO-2026-10-17-issue-286-commit-cost-reduction-review.md — fc56151 on the review branch named in section 1 -->
<!-- src: ../../incremental_jsonl.py, ../../chroma_store.py, ../../chroma_write_store.py, ../../chroma_write_guard.py, ../../config.py — baseline 07117ed implementation seams -->
<!-- ref: ./STATUS-codex-jsonl-production-integration.md, ./VERIFY-codex-jsonl-production-integration.md — existing Arc Codex routing and future implementation evidence -->
