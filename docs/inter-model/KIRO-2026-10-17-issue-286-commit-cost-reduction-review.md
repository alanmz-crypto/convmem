# [Arc Codex #286] Kiro design review — reduce incremental commit cost

**Verdict: PASS-with-conditions. Slice 1 (duplicate pre-write digest reuse +
phase instrumentation) is a clean PASS and may start now.**

**Arc: Codex (#286).**

**Who / what / when / why / how:** Kiro (design-review lane), 2026-10-17.
Reviewing Codex's re-plan `docs/plans/DESIGN-issue-286-commit-cost-reduction.md`
on `origin/docs/2026-10-17-issue-286-commit-cost-reduction` at `a827ee1`,
baseline `bd37946`. This re-plan follows my earlier REDIRECT
(`docs/inter-model/KIRO-2026-10-17-issue-286-proportional-export-review.md` at
`c8d8700`), which Ryan accepted; option C is on hold. Ryan asked me to rule on
the design's four §9 questions (the task numbers them 1–4; the document's §9
lists five, 1–5, with duplicates/gates as its fifth), give a verdict per
question plus an overall verdict, and — if slice 1 PASSes — say so explicitly so
Cursor can start it while the larger slices are refined. I ran read-only startup
diagnostics and read the pinned baseline source for every claim I rely on.

**This is a review of direction, not an Execute grant. No code was written, no
indexing run, no provider called. Delivered as one document on a new branch from
`origin/main`, pushed with an explicit refspec, no PR.**

---

## 0. Overall verdict and why

**PASS-with-conditions**, and the strongest thing I can say about this re-plan is
that it did the honest work my REDIRECT asked for and did not oversell any of
it. It sequences the cheap, measured win first; it refuses to claim the 60 s /
5 s targets are met by anything shipped here; and on the one place where Ryan's
own question invites an easy "yes" — treating the scheduled Chroma audit as a
compensating control — the design's own text already denies it, and I agree with
the design over the question (see §2 below).

Three independent correctness checks against baseline `bd37946`:

- **Slice 1 is real and correct.** On a fresh attempt, `_commit_generation`
  (`incremental_jsonl.py:2142`) computes `non_source_inventory_digest` over both
  collections **three** times: the attempt digest at `:2167`, again inside
  `_snapshot_before_images` at `:1493`, and once more in
  `_verify_non_source_collections` at `:2199`. The first two are captured back
  to back under the same uninterrupted `index_write_flock` with no Chroma
  mutation between them. Reusing the first value for before-image assembly
  collapses 3 scans → 2 and preserves the fresh post-apply comparison. Verified
  in source, not inferred.
- **The provenance-key subtlety is real and the design caught it.**
  `provenance_commitment` (`provenance.py:404`) hashes
  `authoritative_envelope`, which pops `effective_integrity` **and** the embedded
  `provenance_commitment` before canonicalizing (`provenance.py:379`). So the
  commitment does **not** uniquely identify a serialized envelope value: two
  envelopes that differ only in `effective_integrity`, or in string-vs-object
  serialization of identical canonical content, share a commitment. A side store
  keyed by commitment alone would silently collapse distinct serialized variants
  and corrupt legacy `provenance_envelope_hash` semantics. §4.1 keys by
  commitment **plus** a separate variant SHA-256 over the typed original value —
  the correct mitigation.
- **The compensating-control claim does not hold, and the design agrees.**
  `scripts/chroma_guard.py audit` reports `segments`, `vectors`, `lost`, and
  `invalid_segments` (`guard.audit()`); `doctor._check_chroma_audit`
  (`doctor.py:842`) FAILs on lost vectors or invalid HNSW segments, WARNs when
  stale (>36 h). That surface is **vector-loss + segment-structure validity**,
  not **foreign-row content equality**. It cannot detect a silent in-place
  change to an untouched foreign row whose vector still exists in a structurally
  valid segment. That is precisely the detection the full pre/post digest
  provides and the scoped proof gives up. So the audit is **not** a like-for-like
  compensating control. The design says exactly this in §3.1; I enforce it as a
  hard honesty condition, not a softenable one.

Nothing here is cleared to execute beyond slice 1, and even slice 1 is a plan
PASS, not an Execute grant — Ryan grants execution. The 60 s / 5 s gates remain
unproven and must not be claimed by any slice until measured on the hermetic
harness.

---

## 1. Ship slice 1 first (3 scans → 2, ~73 s) + phase timing, before the envelope migration?

**Verdict: PASS. Slice 1 is accepted and may start now.**

This is the question I most wanted answered with a plain yes, and the code
supports it exactly. Verified against baseline `bd37946`:

- `_commit_generation` at `incremental_jsonl.py:2142`. Inside the single
  `source_flock` → `index_write_flock` critical section:
  - `:2167` `attempt_non_source = self._non_source_collection_digest()` — scan #1.
  - `:2169` `rollback = self._snapshot_before_images()`, whose body at `:1493`
    calls `non_source_inventory_digest` for both collections again — scan #2.
  - `:2199` `self._verify_non_source_collections(attempt_non_source)` recomputes
    the digest and compares — scan #3.
- Scans #1 and #2 are captured back-to-back under the same uninterrupted lock
  with no Chroma mutation between them (nothing between `:2167` and the
  `_snapshot_before_images` call writes to Chroma). They are, by construction,
  equal. `non_source_inventory_digest` (`chroma_store.py:763`) pages every row
  of each collection pulling `["documents","embeddings","metadatas"]` — the
  768-dim embedding payload is the cost. Removing one such scan is the ~73 s the
  measurement attributes to one collection-pair digest.

The design's proposed mechanism is correct and I hold it to its own guardrails,
which are the right ones:

1. **Reuse under the same lock only, deep-copy/freeze.** The reused value must be
   captured at `:2167` and passed into before-image assembly without releasing
   `index_write_flock` and without any intervening Chroma mutation. Freeze it so
   a later mutation of the dict cannot retroactively alter the rollback journal's
   recorded baseline.
2. **The rollback journal still records that original value**, and the
   **post-apply comparison at `:2199` stays fresh** — this is a one-scan
   reduction in observation count, not a loss of document/vector field coverage.
   A single digest reused as both "before" and "after" proves nothing and is
   correctly rejected by the design.
3. **Replay must not be touched.** The replay/roll-forward path takes a **fresh**
   attempt baseline (`incremental_jsonl.py:2289` recomputes
   `_non_source_collection_digest()` before `_restore_before_images` and
   re-verifies) while retaining the **original** immutable journal. That
   distinction — fresh attempt baseline, original journal preserved — is what
   lets a replay avoid blaming this attempt for a foreign commit that landed
   between attempts. Slice 1 touches only the fresh-attempt commit path and must
   leave the replay baseline exactly as-is. I will FAIL any implementation that
   reuses a stored digest in place of the fresh replay baseline, or that lets the
   reused value replace the original journal hash.

**Conditions on slice 1 (all cheap, none blocking the start):**

- **C1-a — same-lock, no-mutation invariant asserted in a test.** A test must
  prove that between the attempt digest and before-image assembly the lock is
  never released and no Chroma write occurs, so the reuse is sound by
  construction rather than by inspection.
- **C1-b — freeze/deep-copy, not alias.** The reused value handed to the journal
  must be independent of any later mutation; assert that mutating the live
  collection after capture does not change the recorded rollback baseline.
- **C1-c — replay baseline untouched.** A test must show the roll-forward path
  still computes a fresh `_non_source_collection_digest()` and preserves the
  original journal SHA; reuse must not leak into replay.
- **C1-d — structural scan-count assertion.** Instrument so a fresh one-chunk
  commit performs **exactly two** full inventory passes per collection and one
  before/after comparison, and a negative control that reintroduces the third
  scan fails the test. This is the design's own §8.2 structural acceptance; I
  require it for slice 1 specifically.
- **C1-e — honest timing attribution.** The phase instrumentation must not count
  startup, fixture construction, or provider preparation as C1 savings, and must
  report per-phase spans without double-counting nested spans (§8.2). The ~73 s
  claim is a measured attribution to one collection-pair digest from Claude's
  read-only run; slice 1's own benchmark must reproduce the delta on the hermetic
  harness, not inherit the number from an unmatched run.

**Why slice 1 is safe to parallelize with refinement of the larger slices:** it
changes observation *count*, not the correctness contract. It retains the full
post-write field comparison, every guard, the rollback schema, and all export
behavior. It makes no claim on the 60 s / 5 s gates (the design is explicit that
even eliminating all three scans leaves >60 s of residual). It is the smallest
independently useful change and it is a sequencing refinement of my
shrink/collapse redirect, not a return to option C. **Cursor can start slice 1
under a normal Execute grant from Ryan while slices 2–4 are still being
refined.**

One scope note I want on the record: slice 1 removes the *redundant adjacent*
pre-write sample. It therefore also removes the (never-guaranteed) chance to
observe an out-of-band foreign change *between* those two adjacent samples. That
is not a regression in any guarantee the system actually makes today — neither
the one-scan nor the two-scan version detects an arbitrary concurrent bypass —
and the design states this plainly. Accepted.

---

## 2. Accept the scoped-write proof's explicit loss of immediate untouched-row corruption detection? Is the scheduled Chroma audit an adequate compensating control, and at what cadence?

**Verdict: PASS-with-conditions on the proof; the Chroma audit is NOT an
adequate compensating control, and no cadence makes it one. Approval of scope
substitution must therefore accept the detection loss on its own terms, not
behind an audit that covers a different failure class.**

This is the most important ruling in the review, so I will be precise about what
is given up and what the audit actually does.

### 2.1 What the full digest detects today, and what the scoped proof gives up

`_verify_non_source_collections` (`incremental_jsonl.py:1529`) raises
`non_source_isolation_changed` when the fresh post-apply digest differs from the
pre-apply baseline on **id / metadata / document / embedding** evidence for
every foreign row (`chroma_store.py:763` pages all four). So today, within one
commit, the system **observes** that no foreign row's content changed between two
points in time — including a change caused by something other than this commit
(backend corruption, a bypass writer). The design (§2) names the two meanings
cleanly:

1. **Causal isolation** — this commit issued no mutation of a foreign-owned row.
2. **Observed physical noninterference** — no foreign API-visible
   document/metadata/vector/membership changed between the two observations.

The scoped-write proof (§3) establishes (1) by complete mediation at the native
mutation boundary. It **cannot** freshly establish (2) for arbitrary untouched
foreign rows without reading them — which is the whole point of making the cost
source-proportional. So the explicit loss is: **immediate, per-commit detection
of a content change to an untouched foreign row.** That is exactly as stated.

### 2.2 Why the scheduled Chroma audit does not fill that gap

I verified the audit's coverage at baseline `bd37946`:

- `scripts/chroma_guard.py audit` → `guard.audit()` reports `segments`,
  `vectors`, `lost`, `invalid_segments`. `_audit` prints
  `segments/vectors/lost` and per-segment FAIL reasons.
- `doctor._check_chroma_audit` (`doctor.py:842`) FAILs on **lost vectors** or an
  **invalid HNSW segment**, WARNs when the audit never ran / is stale (>36 h) /
  was skipped / errored, PASS otherwise. Live doctor this session:
  `chroma_audit: 115655 vectors, 0 lost, 2 segment(s) valid (13h ago)`.

The audit's detection surface is **(a) records with no vector (silent loss)** and
**(b) structurally invalid HNSW segments.** It does **not** hash or compare
foreign-row *content* (document bytes, metadata values, embedding values) against
any known-good baseline. The exact loss the scoped proof introduces — a silent
in-place content change to an untouched foreign row whose vector still exists and
whose segment is structurally valid — falls **outside** the audit's surface. It
is a different corruption class.

Therefore:

- **The audit is not a like-for-like compensating control.** Increasing its
  cadence (hourly, continuous) does not help, because it is not measuring the
  thing that was lost. More frequent segment-validity checks still never compare
  untouched foreign content.
- A control that *would* compensate is a **full-closure content integrity audit**
  — walk and hash the complete reachable foreign closure against a durable
  known-good baseline — run as a **separately budgeted** operation off the commit
  path. The design already treats this as separate and refuses to amortize it
  into the fast path (§3.1: "Full integrity and qualified-backup checks remain
  separately budgeted operations; no claim that periodic audits restore immediate
  detection of untouched-row corruption"). I agree and require that this honesty
  survives into implementation and evidence verbatim.

### 2.3 Conditions

- **C2-a — accept the loss explicitly, not by proxy.** The acceptance gate that
  removes full scans must state, in evidence and docs, that immediate per-commit
  untouched-foreign-row content-corruption detection is given up, and must **not**
  cite the `chroma_guard` audit (or `doctor chroma_audit`) as restoring it. Any
  text implying the audit compensates is a FAIL trigger at review time.
- **C2-b — complete mediation is proven, not asserted.** The causal property
  depends on the native boundary at `ChromaStore._native` (`chroma_store.py:179`)
  mediating **every** production write. The design's own requirement stands:
  static call-site inventories **plus** runtime negative tests (hidden/nested
  session, background thread/subprocess, raw collection handle, unrestricted
  `where`, create/drop/reset) must each deny before any native call. Regex alone
  does not qualify. If any production route can reach `_native` outside the
  scope, the proof is void.
- **C2-c — distinct typed outcomes.** Scoped mode must not fabricate
  `non_source_collections_after` or report the full-mode comparison as PASS. A
  denied foreign write and an incomplete census must each have their own typed
  outcome; only a separately observed mismatch may use the existing
  `non_source_isolation_changed` code (§3.1). Consumers branch on evidence mode
  and refuse an unknown schema.
- **C2-d — versioned evidence mode and shadow period.** Keep
  `full_inventory_v1` vs `scoped_writes_v1` with collection/owner/attempt binding
  and measured coverage. Run the census **alongside** full digests on hermetic
  fixtures first to catch coverage mistakes; removing scans is a **separate**
  reviewed gate, not the side effect of adding receipts (§8 slice 2).
- **C2-e — recovery routing preserved.** A segment restoration, native crash,
  integrity fault, or unknown native outcome must invalidate a clean scoped
  receipt and route to existing Safe Harbor containment/recovery. A source
  journal does not certify a guard-restored segment (§3.1).

**On the cadence question specifically:** the honest answer is that the audit's
cadence is irrelevant to this gap. For the *vector-loss / segment-validity* class
it already covers, the current daily cadence with a 36 h WARN threshold is
reasonable and I would keep it. But it should not be presented as the
compensating control for the scoped proof's loss at any cadence. If Ryan wants a
genuine compensating control for untouched-foreign-content corruption, that is a
**separately scheduled full-closure content audit** with its own budget and its
own cadence decision — and even then it is *periodic* detection, never the
*immediate per-commit* detection being traded away. The scope substitution should
be approved, if at all, with that trade-off accepted openly.

---

## 3. Commitment-keyed envelope variants, compatibility fencing, epoch-checked migration?

**Verdict: PASS-with-conditions. The representation scheme is correct and catches
a real subtlety; the migration mechanics are directionally right but must not
claim a no-writer-window rollout on the present runtime, and must name the real
wedged transaction as a concrete precondition.**

### 3.1 Commitment-keyed variants — correct, with conditions

The design's §4.1 key design is the right one and rests on a fact I verified:
`provenance_commitment` (`provenance.py:404`) hashes `authoritative_envelope`
(`provenance.py:379`), which **pops `effective_integrity` and the embedded
`provenance_commitment`** before `canonical_bytes`. Consequences the design
handles correctly:

- A commitment alone does **not** uniquely identify a serialized envelope value.
  Two envelopes differing only in `effective_integrity`, or in string-vs-object
  serialization of identical canonical content, collapse to one commitment.
- Keying the side store by **commitment + a separate SHA-256 variant digest over
  the typed original value** (string vs object included) preserves legacy
  `provenance_envelope_hash` semantics and exact string formatting. Storing one
  value per commitment would corrupt identity.
- `validate_projection` (`provenance_binding.py:172`) treats a missing/malformed
  envelope as `untrusted` and a commitment mismatch as `untrusted`; it never
  promotes `effective_integrity` beyond `untrusted` (the comment is explicit:
  authority stays registry-bound). Externalizing the field must preserve this —
  a ref is not authority, a commitment is not a recoverable envelope.

**Conditions:**

- **C3-a — do not redefine existing hashes.** `provenance_envelope_hash` must
  keep its current meaning; do not redefine it to mean the commitment or a new
  byte hash. The variant digest is a **new** field, additive.
- **C3-b — resolver fails closed and never repairs.** The resolver must check
  containment, no symlinks, type/size bounds, UUID, variant hash, typed envelope
  validity, recomputed commitment, and assertion-id equality; inline-plus-ref
  disagreement is corruption (not "prefer whichever works"); missing/corrupt refs
  fail closed for mutation/recovery and are labeled unavailable/untrusted for
  retrieval. No resolver calls providers or rewrites storage.
- **C3-c — full-inventory compatibility mode stays honest.** While
  `full_inventory_v1` remains selected, its logical envelope comparison must
  **resolve and hash referenced values**, not merely hash the ref — otherwise a
  changed side-store object escapes detection. The design states this (§4.2(1));
  it is a hard condition. That mode may stay expensive until scoped-proof
  acceptance; that is acceptable.
- **C3-d — closed consumer inventory before any ref publication.** §4.2 pins a
  consumer inventory across provenance core, ingest/replay, retrieval/refine,
  decision/observe/verify, R2b/Shadow/governed protocol, export maintenance,
  recovery/exact-evidence, and operational scripts. I require this inventory
  regenerated as coverage evidence (static call-site + negative tests), with
  **Shadow** and **CG-2** called out specifically:
  - **Shadow** hashes metadata/state today; preserve the logical hash input by
    hydrating exact values, **or** introduce a reviewed *versioned* hash contract.
    Never change the old hash meaning in place.
  - **CG-2** records envelope values/hashes in row identities; hydration must
    reproduce those exact values, never mint replacement provenance. Recovery
    Authority generation IDs/manifests/commitments are unchanged by side-store
    UUIDs. I will not pass any slice that lets a side-store UUID leak into CG-2 or
    Recovery Authority identity.
- **C3-e — side store is not `provenance/generations`.** Correctly kept separate
  (that path has Recovery Authority selector/manifest semantics). Reuse its
  validated envelopes only when identity/commitment matches; do not assume it
  covers all historical envelopes.
- **C3-f — durability ordering.** Immutable object fsynced (object + parent)
  **before** publishing any ref in Chroma or export; crash-before-ref leaves a
  harmless orphan; no GC in the initial slice (keep objects reachable from
  exports/Chroma/journals/prepared/capture/backups/incidents).

This slice must be **export-refs-first, Chroma inline until Chroma readers
qualify** (§5.3), so export-size savings are separated from later metadata-size
savings and can be measured independently.

### 3.2 Compatibility fencing and epoch-checked migration — right shape, two hard limits

The §5 migration is additive dual-read / inline-write first, with ref-writing
disabled until readers qualify, then capability-fenced ref enablement, an
epoch-bound export sweep, and active-journal skips. The shape is correct and
continuous with existing isolation semantics. Two conditions carry over from my
REDIRECT and remain non-negotiable:

- **C3-g — no seamless no-writer-window claim on today's runtime.** The design
  already concedes this (§5.2: "If deployment cannot exclude such processes, a
  bounded no-writer maintenance window is required; no seamless-rollout claim is
  available on today's code"). I hold it. C1/export locks do not stop an old
  binary that reads/writes without locks. The fence must be a concrete
  **storage-capability epoch checked at admission** by **every** CLI / MCP /
  watch / refine / monitor / tools / recovery entrypoint, with a runtime negative
  test proving an un-fenced old process is **refused**, not merely assumed
  absent. The current protocol-version/attestation alone is not that fence.
- **C3-h — name the real wedged transaction.** `convmem doctor` this session
  reports APPLYING transaction `46313d437ae4446282a752270770c614`,
  `recovery_unproven`, phase `APPLYING`, age ~45,225 s, on the Oct 13 Codex
  rollout source. §5.6 names it and says it must be resolved under its original
  versioned authority before converting that source, that a sweep skips its bytes
  and global compaction waits, and that its journal bytes / bound SHA must never
  be rewritten to accommodate migration. Correct — and I require the execution
  plan to carry this specific transaction id as a concrete precondition with
  evidence it was resolved by its original v1 runtime, not merely restate the
  rule. The design is review-only and may not repair it; that remains a separate
  authority.

**Epoch mechanics (accepted):** build export candidates from a pinned read-only
inode outside C1; each participating writer takes C1 then export lock, publishes
a durable dirty intent before mutation, completes a new durable epoch only after
file+dir durability; a dirty/unknown epoch bars candidate publication; at
publication compare the bound clean epoch and file identity under the locks and
discard stale candidates. Identity/mtime alone is not authority. A durable
migration intent ties old/new byte hashes to the epoch. **Confirm the Chroma
metadata replacement actually removes the old envelope key** (§5.5) — merging a
ref while retaining the envelope yields no size saving; this must be proven, not
assumed.

**Rollback (accepted):** before refs, stop and keep inline (objects are harmless
unpublished data); after refs, disable new ref writes on the capable release,
resolve transactions, and re-inline the **current** logical values through the
same compare-and-publish/batch protocol, preserving all intervening commits.
Restoring the pre-migration flat file would lose later writes and is not a valid
downgrade (§5). Retain side store / intent / receipts until nothing live, backup,
journal, or incident references them; no GC in initial delivery.

---

## 4. Compaction preconditions and the 60 s / 5 s gates?

**Verdict: PASS-with-conditions. The "do not run live compaction on current
evidence" disposition is correct; the gates are correctly specified and correctly
declared unmet; neither gate may be inferred from the other or from any slice's
success.**

### 4.1 Export duplicates and compaction — disposition correct

The design does not treat `203,441 export rows vs 111,348 Chroma units` as
`92,093 duplicates`, and that restraint is right: export carries historical
unique IDs and distinct provenance identities, and Chroma physical/active/logical
counts differ. Startup doctor this session independently reported ~203k
historical export IDs and ~111k active units with 92,529 historical-only — a
*different* live sample consistent with substantial unique history, **not** a
duplicate census. I verified the primitive: `compact_units_export`
(`export_compaction.py:52`) takes the export lock, builds a bounded-memory SQLite
offset index, validates each record (object, nonempty string id, ≤16 MiB), checks
file identity, and publishes last-payload-per-id in first-occurrence order. It is
byte-identical/no-op with no duplicates; it does **not** select only live Chroma
IDs, resolve distinct IDs sharing `ledger_id`, validate provenance continuity, or
remove historical unique IDs. A successful return is **not** evidence the export
equals the live corpus. The design states all of this.

**Conditions (accepted as stated, enforced at review):**

- **C4-a — no live compaction on current evidence.** Hermetic evaluation only;
  the export lock is not governed-operation admission. Production use needs a
  fresh grant, qualified recoverable preimage, no unresolved
  byte/ordering-dependent transactions, a strict validity census, and conflict
  classification (same-id identical; same-id differing payload/provenance/owner;
  distinct-id same-ledger; historical-only; malformed — each measured
  separately). Refuse conflicting groups pending owner disposition.
- **C4-b — preserve approval-refusal semantics.** `propose_decision.py` /
  `observe.py` deliberately reject multiple matching `ledger_id` rows; no logical
  dedup view and no compaction may hide that refusal.
- **C4-c — multiplicity/order/bytes authority preserved.** Incremental rollback,
  bootstrap mutation inventories, qualified snapshots, CG-2 identity evidence, and
  forensic artifacts can depend on multiplicity/order/bytes even where serving
  does not; purge must remove **all** matching rows. Historical-only deletion is a
  separate reconciliation policy, not compaction.
- **C4-d — keep compaction off the per-commit / post-index path** in the
  optimized route; any later scheduling is explicit maintenance with separate
  accounting. Retain the original artifact; do not silently filter invalid rows to
  make the utility run.

### 4.2 The 60 s / 5 s gates — correctly specified, correctly unmet

Gate A (≤60.0 s end-to-end for a successful one-chunk prepared commit, timed from
commit entry through all followers and cleanup, source/C1 wait reported
separately, uncontended **and** bounded-contention series, max/p95/median/failures
and all samples) and Gate B (<5.0 s maximum continuous C1 hold **and** <5.0 s
total C1 hold per operation, warm and cold-ish, splitting a long hold into tiny
acquisitions is not success) are the right gates and are specified at the right
granularity. The design is explicit, and I agree, that:

- **No slice here meets either gate.** Even eliminating all three measured scans
  leaves >60 s in the rough residual (§1, §8.1). Slice 1 makes **no** gate claim.
- **Neither gate may be inferred from the other**, and neither may be inferred
  from plan PASS, code merge, or a measured per-phase saving. §8.1 of the arc's
  hard-stops discipline applies: a saving measured in an unmatched run is not a
  gate pass.
- **Failure to reach 5 s is a design result, not license** to disable the native
  guard, skip durability, or weaken source recovery (§8.1). I will FAIL any
  implementation that trades a gate number for a safety contract.

**Conditions:**

- **C4-e — gates proven on the hermetic harness (§8.2) after each step**, with
  real isolated Chroma, deterministic fake providers, synthetic
  envelopes/vectors/transcripts, disposable HOME/XDG/config/data/cache/TMPDIR,
  credentials removed, writes confined to scratch, and safety-negative controls
  showing provider/production-path access **denied**. No live Chroma copy and no
  provider endpoint in the worker.
- **C4-f — structural acceptance enforced.** First slice performs exactly two full
  inventory passes per collection and one before/after comparison on a fresh
  attempt and preserves replay authority; scoped mode performs **zero** full
  foreign inventories and reads no foreign payload merely to certify isolation;
  native calls enumerate only authorized IDs; added census/receipt bytes and
  returned rows stay bounded as foreign count grows (internal DB lookup and
  segment I/O reported separately); flat export remains linear and is explicitly
  charged; no synchronous background or post-return compaction moves cost out of
  the reported commit. Negative controls that reintroduce a full scan, re-inline
  envelopes, or run post-index compaction must be **caught** by the
  performance/accounting tests.
- **C4-g — supplementary source-size distribution.** The design asks which
  distribution should supplement the one-chunk fixture (§9 Q5). My direction: in
  addition to the measured one-chunk fixture at the live shape
  (111,348 units / 5,106 summaries / 203,441 export rows / 5.19 GiB), require at
  minimum (i) a **large-history single source** (many generations, large owned
  row/byte count) to exercise the O(k) census where k includes all source rows +
  candidates, and (ii) a **foreign-count sweep** (10k, ~111k, 2×) with owned
  source fixed, to prove scoped cost is independent of foreign count. Report
  large-source and fault/recovery latency as separate distributions, never hidden
  in the one-chunk average. These supplement, not replace, the live-shape fixture.

The gate design is sound; the correct posture is that it is **unproven** and must
remain so in every artifact until measured.

---

## Verdict summary

| # | Question | Verdict |
|---|----------|---------|
| — | **Overall** | **PASS-with-conditions** |
| 1 | Ship slice 1 (3 scans → 2, ~73 s) + phase timing before envelope migration | **PASS** — may start now (conditions C1-a…C1-e, none blocking the start) |
| 2 | Accept scoped-write proof's loss of immediate untouched-row detection; is the Chroma audit an adequate compensating control, and at what cadence | **PASS-with-conditions** on the proof; **audit is NOT an adequate compensating control at any cadence** (it covers vector-loss/segment-validity, not foreign-row content); accept the loss explicitly (C2-a…C2-e) |
| 3 | Commitment-keyed envelope variants, compatibility fencing, epoch-checked migration | **PASS-with-conditions** — variant scheme correct; no no-writer-window claim on today's runtime; name wedged tx `46313d43…` (C3-a…C3-h) |
| 4 | Compaction preconditions and the 60 s / 5 s gates | **PASS-with-conditions** — no live compaction on current evidence; gates correct and unmet; neither inferred (C4-a…C4-g) |

**Slice 1 is explicitly PASS.** Cursor can start it under a normal Ryan Execute
grant while slices 2–4 are refined, carrying conditions C1-a…C1-e. The expectation
Ryan stated — ~73 s off each commit — is the right order of magnitude and matches
the one-collection-pair digest cost; slice 1's own hermetic benchmark must
reproduce the delta rather than inherit Claude's read-only number, and must make
no 60 s claim.

## What I verified vs. did not

**Verified (read-only, pinned baseline `bd37946`):**

- `_commit_generation` computes three full `non_source_inventory_digest` passes
  per fresh one-chunk commit — attempt `:2167`, inside `_snapshot_before_images`
  `:1493`, verify `:2199` — the first two back-to-back under one uninterrupted
  `index_write_flock` with no intervening Chroma mutation (`incremental_jsonl.py`).
- Replay path takes a fresh baseline and preserves the original journal
  (`incremental_jsonl.py:2289`).
- `non_source_inventory_digest` pages all rows pulling
  documents+embeddings+metadatas, excluding by exact `source_path`
  (`chroma_store.py:763`).
- `provenance_commitment` hashes `authoritative_envelope`, which pops
  `effective_integrity` and `provenance_commitment` before canonicalizing — so a
  commitment does not uniquely identify a serialized envelope value
  (`provenance.py:379,404`). `validate_projection` keeps `effective_integrity`
  `untrusted` and registry-bound (`provenance_binding.py:172`).
- `chroma_guard` audit reports segments/vectors/lost/invalid_segments;
  `doctor._check_chroma_audit` FAILs on lost vectors / invalid segments, WARNs
  when stale (>36 h) (`scripts/chroma_guard.py`, `doctor.py:842`). Live:
  `115655 vectors, 0 lost, 2 segment(s) valid (13h ago)`.
- `compact_units_export` is bounded-memory, atomic, last-payload-per-id, no-op
  without duplicates; does not reconcile against live Chroma
  (`export_compaction.py:52`).
- Doctor reports the live wedged transaction `46313d437ae4446282a752270770c614`,
  `recovery_unproven`, APPLYING, age ~45,225 s.
- Baseline `bd37946` is an ancestor of `origin/main` (`9ef4ecd`).

**Did NOT verify (and this review does not claim as proven):**

- The full wall-time decomposition of a one-chunk commit. The ~73 s / 71.0 s /
  16.7 s figures are Ryan-supplied from Claude's read-only run on `bd37946`; I did
  not rerun them. Residual time (88–159 s subtracting all three scans) is
  unattributed and the design treats it as such.
- Whether every §4.2 consumer tolerates envelope externalization. That is the
  closed-inventory + negative-test work the design defers to the slice-2 Execute
  plan; I require it, I did not perform it.
- No benchmark, migration, compaction, indexing, provider call, or mutation was
  run. Semantic search was not invoked (it can call a provider).

## Review-scope conformance

Review-only per the lane: no code, no tests, no indexing, no provider calls. The
startup diagnostics (`doctor`/`brief`/`unresolved`) and the read-only `git show`
inspections of baseline source were orientation and evidence-gathering only; they
mutated nothing. Delivered as a single document on a new branch from
`origin/main` (`docs/2026-10-17-issue-286-commit-cost-review`), pushed with an
explicit refspec, no PR.

## Forward announcement

I finished: Kiro design review of DESIGN-issue-286-commit-cost-reduction at `a827ee1` (overall PASS-with-conditions; slice 1 PASS).
Next step:  Ryan writes the Cursor prompt for slice 1 (digest reuse + phase instrumentation, conditions C1-a…C1-e) and verifies ~73 s off each commit with the timing harness; slices 2–4 refined under their conditions.
Next lane:  Ryan (grant + Cursor prompt for slice 1); Codex refines slices 2–4; Cursor executes slice 1 after grant.
See my work: docs/inter-model/KIRO-2026-10-17-issue-286-commit-cost-reduction-review.md (§0 overall; §1 slice-1 PASS; §2 audit-is-not-a-compensating-control).

## TL;DR

- **Overall PASS-with-conditions; slice 1 is an explicit PASS and can start now.**
  Verified against baseline `bd37946` that a fresh one-chunk commit does three
  full non-source Chroma digests, the first two back-to-back under one lock with
  no mutation between — reusing the first (frozen) collapses 3 → 2 (~73 s) with
  the fresh post-apply check and replay authority intact.
- **Q2: the scheduled Chroma audit is NOT an adequate compensating control at any
  cadence** — it detects vector-loss and invalid HNSW segments, not content
  changes to untouched foreign rows, which is exactly what the scoped proof gives
  up. The design already says this; accept the detection loss on its own terms,
  never behind the audit.
- **Q3: commitment + variant-digest keying is correct** (the commitment excludes
  `effective_integrity` and the embedded commitment, so it alone can't identify a
  serialized value); no no-writer-window claim on today's runtime; name wedged tx
  `46313d43…` as a concrete migration precondition.
- **Q4: no live compaction on current evidence; the 60 s / 5 s gates are correctly
  specified and correctly unmet** and may not be inferred from any slice or from
  each other. Supplement the one-chunk fixture with a large-history source and a
  foreign-count sweep.

<!-- src: ../plans/DESIGN-issue-286-commit-cost-reduction.md @a827ee1, ../../incremental_jsonl.py @bd37946, ../../chroma_store.py, ../../provenance.py, ../../provenance_binding.py, ../../export_compaction.py, ../../doctor.py, ../../scripts/chroma_guard.py -->
<!-- src: ./KIRO-2026-10-17-issue-286-proportional-export-review.md @c8d8700 — the accepted REDIRECT this re-plan follows -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md, ../plans/STATUS-recovery-authority.md, ../plans/STATUS-safe-harbor.md, ../plans/STATUS-r2b-capture-auth.md, ../plans/STATUS-shadow-ledger-phase0.md — arc routing and compatibility boundaries; no cross-arc execution grant -->
