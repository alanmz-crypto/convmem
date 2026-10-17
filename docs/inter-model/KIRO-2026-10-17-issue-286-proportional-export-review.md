# [Arc Codex #286] Kiro design review — proportional export publication

**Verdict: REDIRECT (to the constant-factor path first).**

**Arc: Codex (#286).**

**Who / what / when / why / how:** Kiro (design-review lane), 2026-10-17. Reviewing
Codex's design `docs/plans/DESIGN-issue-286-proportional-export-commit.md` at
`origin/docs/2026-10-17-issue-286-proportional-export-commit` tip `7af3073`,
baseline `bd37946`. Codex recommends **option C** (immutable per-source export
segments + bounded copy-on-write directory + atomic root) to make incremental
commit/rollback export I/O source-proportional. Ryan asked me to answer
PROPORTIONALITY first, then Codex's five §11 questions, and deliver this review
only (no code, no indexing, no provider calls). I ran read-only startup
diagnostics, read the pinned baseline source for every claim I rely on, and
took read-only measurements of the live export. One PR is not opened.

**This is a review of direction, not an Execute grant. No code was written, no
indexing run, no provider called.**

---

## 0. PROPORTIONALITY — answer first

**Option C is not justified by the evidence as it stands. REDIRECT to the
constant-factor path first.** The design is technically careful and its baseline
reading is accurate, but it is scoped against a cost model that the live data
does not support. Three measured facts, all verified this session, move the
verdict:

### Finding 1 — The dominant per-commit cost is Chroma, not the export file

Inside the single C1 critical section (`index_write_flock`) of one successful
one-chunk commit (`incremental_jsonl.py:_commit_generation`, baseline lines
2162–2227), the baseline performs **three full non-source Chroma scans** and
**two full export-file passes**:

| Step | Call site | Full-corpus work |
|------|-----------|------------------|
| attempt digest | `:2167` `_non_source_collection_digest` | scans **both** collections, every row incl. documents + embeddings |
| before-images | `:2169` `_snapshot_before_images` → `:1493` | another full non-source digest of both collections **+** full export read (`_snapshot_export_before_image :1452`) |
| verify isolation | `:2199` `_verify_non_source_collections` | **another** full non-source scan of both collections |
| export reconcile | `:2226` `_reconcile_export :1906` | second full export read + rewrite |

`non_source_inventory_digest` (`chroma_store.py:763`) pages the **entire
collection** and pulls `["documents","embeddings","metadatas"]` for every row,
hashing and sorting all of them. With ~115k active vectors and
`nomic-embed-text` 768-dim embeddings, one such scan materializes on the order
of hundreds of MB of float payload through the Chroma client; three of them per
commit, plus client/JSON overhead, plausibly accounts for the bulk of the
reported 39 GB `rchar`. **Option C does nothing to these scans** — it only
changes the export file. The design concedes exactly this in §10.2 and
question 5, but then still recommends adopting C now.

### Finding 2 — The export is bloated by one field, not by row count or record floor

Live measurements (`/home/lauer/.local/share/convmem/knowledge_units.jsonl`,
read-only):

- Size: **5.57 GB**; **203,354 lines**; mean line **27.4 KB**, max **67.7 KB**,
  zero lines over 100 KB.
- Sampling the recent tail: mean object line ~34 KB, of which **`provenance_envelope`
  is ~33–40 KB — about 98% of every recent record and ~98% of the whole file.**
  The actual knowledge content (`summary` ~155 B, `keywords`, `title`, `id`) is
  ~500 B/record.
- `_export_unit_payload` (`incremental_jsonl.py:712`) writes `metadata + id`
  with no embeddings/documents, so the bloat is entirely the metadata field
  `provenance_envelope`, which already travels beside a 66 B
  `provenance_commitment` hash and a `provenance_envelope_hash`.

So the "5.3 GB for ~115k vectors ≈ 46 KB/unit" framing in the task brief is
real in magnitude but **misdiagnosed**: it is not many fat units and not a
46 KB structural floor. It is one Recovery-Authority/CG-2 provenance structure
serialized in full into each unit's projection row, duplicated across
generations. The export carrying ~90× the live corpus is a symptom of the same
thing: full envelopes retained per generation under `_reconcile_export`'s
"copy all foreign lines" rule.

### Finding 3 — The two constant-factor levers are large, not marginal

- **Lever (b), shrink the export:** if the full `provenance_envelope` does not
  need to live in the knowledge-unit projection (its hash commitment already
  does), dropping/externalizing it is plausibly a **~50× reduction** — 5.57 GB →
  ~0.1 GB. That is not a 2× tweak; it changes the problem class. This needs a
  compatibility check (who reads `provenance_envelope` back out of the export vs
  the provenance ledger), but the field is structurally redundant with its own
  hash for projection purposes.
- **Lever (a), collapse the passes:** the export is read twice per commit
  (snapshot + reconcile) and could be a single streaming pass that computes the
  before-image hashes *and* produces the reconciled output in one read. More
  importantly, the **three** full non-source Chroma digests per commit are the
  real latency driver and are independent of the export entirely.

### Why this is a REDIRECT, not a FAIL

Option C is a sound design *for the problem it names* (making export file I/O
source-proportional and removing in-place mutation). If, after the
constant-factor fixes, export file I/O were still the measured bottleneck for a
one-chunk commit, C would be the right shape and this document would say
PASS-with-conditions. But on current evidence the export file is not the
binding constraint — the triple Chroma embedding scan is — and the export's
size is a removable field-bloat problem, not an intrinsic one. Committing now to
a versioned storage-format migration across ~20 readers/writers, dual-format
recovery, forward/reverse migration of a 5.57 GB file, and new Safe Harbor / R2b
/ Shadow qualification is a large, mostly-irreversible investment against an
unmeasured premise.

**The honest sequencing is:**

1. **Measure** where the ~5 min actually goes: instrument the C1 section and
   attribute wall time across the three non-source digests, the two export
   passes, Chroma apply, dedupe, and fsync. This is the single most important
   missing artifact; C is being chosen before it exists.
2. **Shrink** the export (lever b): remove or externalize `provenance_envelope`
   from the unit projection, keeping the commitment hash. Re-measure.
3. **Collapse** the passes (lever a): one streaming export pass; and reduce the
   non-source digest from three full embedding scans per commit toward the
   minimum needed for the isolation proof (e.g. verify once, or digest metadata
   without re-pulling embeddings, or scope the isolation check).
4. **Re-test against the ~60 s / 5 s gate.** If a one-chunk commit is then under
   ~60 s (and plausibly under the 5 s C1 target), **C is deferred until a
   measured need re-appears.** If export file I/O is still binding after (2)+(3),
   return to C with that measurement as its justification.

If Ryan's intent is specifically to eliminate *in-place mutable-file* risk
(unlocked readers seeing torn rows, backup-during-rewrite) rather than to hit a
latency number, that is a legitimate separate goal that C serves and the
constant-factor path does not — but the design frames itself around the
five-minute latency evidence, and against that evidence the redirect holds. I
flag this as the one place where my REDIRECT could become PASS-with-conditions:
if the real requirement is mutation-safety, say so and C is defensible.


---

## 1–5. Codex's five §11 questions

I answer each on its own merits. Where my proportionality verdict changes the
weight of a "yes," I say so. These answers describe what the design would need
**if C proceeds anyway** (Ryan may authorize C despite the redirect, e.g. for
mutation-safety); they are not an endorsement of proceeding now.

### 1. Accept C's format migration over the append-log alternative?

**Conditionally yes — but only if C proceeds at all.** Codex's rejection of
option A (append + supersession/tombstone) is correct and well-argued: A adds
log-tail recovery, dead-history filtering, and marker semantics to the
correctness surface while needing comparable reader adoption. Option B
(byte-range sidecar on a mutable flat file) is correctly rejected as not solving
variable-length replacement/deletion. Among the three, C is the right one.

The condition I attach is the one from §0: the *comparison that actually
matters* is not A-vs-B-vs-C, it is **C vs. doing nothing structural and fixing
the constant factors.** The design never runs that comparison with numbers. So:
yes, C over A/B; but C is not yet justified over the constant-factor path.

### 2. Accept the rollback ordering rule (§5) and malformed-tail refusal (§3.3)?

**Yes on both, with one caveat.**

- **Rollback ordering under foreign deletion/reorder:** restoring the source's
  original relative anchors and preserving current foreign order (rather than
  recomputing baseline `foreign_lines_before` integer insertion positions
  against a changed foreign stream) is the right call. The baseline
  `_restore_export` (`:1801`) already preserves current foreign bytes rather
  than reasserting the foreign hash, so V2's policy is continuous with existing
  isolation semantics, not a regression. The design is honest that this is a
  semantic change from exact v1 rank behavior under foreign deletion, and that
  exact v1 equivalence would require a bounded order-statistics structure. That
  honesty is correct and the trade-off is acceptable **provided** the §10.4
  fault matrix actually asserts the three sub-cases (unchanged / appended /
  deleted-reordered foreign) with explicit expected bytes, and includes the
  negative control that a full foreign scan inside rollback fails the I/O gate.
- **Malformed-tail refusal:** refusing ordinary v2 mutations when the current
  logical tail is unterminated (rather than silently appending a newline or
  concatenating into malformed JSON) is the right stricter behavior. Caveat:
  this is a **behavior change that can surface as a new refusal in production**
  the first time a real unterminated tail is hit. It must ship with the explicit
  qualified-repair path implemented and documented in the same release, not as a
  TODO — otherwise a legitimate commit can wedge on a pre-existing tail the
  operator cannot clear. The live export's non-object/`null` lines I hit while
  sampling confirm malformed rows already exist in the corpus, so this path will
  be exercised.

### 3. Is targeted hash verification + full qualified snapshot/audit sufficient?

**Yes, with the design's own honesty labels enforced.** The core claim — that
no source-proportional design can freshly hash arbitrary unrelated (foreign)
bytes, so a root digest commits object *contents* but does not prove current
physical integrity of the whole export — is correct and must not be softened. I
agree with every "limits of hashes" statement in §5:

- a matching unit ID alone is insufficient (owner/UUID/descriptor/length/hash/
  generation must all be checked);
- an authenticated storage object can still hold an *unauthorized* candidate, so
  transaction-binding comparison is required beyond object-hash equality;
- same-user modification of all authority files is outside the cooperative guard
  model, exactly as the current journal-SHA checks already are.

Condition: the acceptance evidence must label targeted-vs-full plainly, and the
full-closure integrity audit (walk + hash the complete reachable closure) must
be a real, separately-budgeted operation, not implied by the per-commit root
digest. A "root digest = integrity proof" claim anywhere in implementation or
docs is a FAIL trigger at review time.

### 4. Are the dual-format recovery boundaries and downgrade gates complete?

**Directionally yes; not yet complete enough to execute.** The strong parts:
refusing cutover with any unresolved old transaction; preserving both formats'
authority validators; requiring updated Safe Harbor / complete-data profile
acceptance before live migration; file-to-directory replacement explicitly *not*
being one atomic rename; the fenced two-rename procedure with a bound migration
intent; and the correct insistence that reverting to the original pre-migration
5.57 GB file after new commits would lose data (reverse migration must
materialize the *latest* root's logical view).

Gaps I want closed before any Execute grant:

- **The already-wedged transaction is not hypothetical.** `convmem doctor` this
  session reports a stale APPLYING incremental transaction
  (`transaction=46313d4...`, phase `APPLYING`, age ~42,495 s) on a Codex
  rollout source. §9 step 2 says cutover must resolve all outstanding v1
  transactions first and "never assume today's reported wedged transaction has
  been cleared." Good — but the migration plan should name *this specific
  wedged transaction* as a concrete precondition and show it resolved with its
  original v1 runtime, not just state the rule.
- **No-writer-window enforcement is asserted but not mechanized.** §9 correctly
  says C1/export locks do not stop an old process that reads/writes without
  locks, and that all CLI/MCP/watch/refine/monitor processes must be inventoried
  and fenced. The watcher is `enabled/active` right now (per brief). The plan
  needs a concrete fencing mechanism (e.g. a migration-intent sentinel every
  entrypoint checks before touching the export, which §3.1/§9 gesture at) and a
  test that an un-fenced old process is actually refused, not merely expected to
  be absent.
- **Downgrade qualification of the restored v1 recovery profile** is stated but
  needs the same scratch-restore-then-verify evidence as forward migration.

### 5. Are the I/O ceiling and the strict 5 s host-qualified C1 gate appropriate?

**The gates are appropriate; the recommendation to adopt C against them is
premature.** The `D = S_old + S_new + 128*(n_old+n_new)` definition and the
`12*D + 2 MiB` ceiling with ≤64 directory levels are reasonable and, crucially,
the design charges hashing/validation reads, failed attempts, and fsync/journal
overhead, and demands `read`/`pread`/mmap-fault accounting rather than
high-level `open` counts. The 5.0 s C1 target with max-continuous-hold reporting
(not averages/p95 alone) and a waiting foreign writer to prove progress is the
right shape.

But §10.2 states the decisive caveat itself: the baseline's whole-collection
non-source Chroma inventory scans, source-projection fingerprinting, and
processed/dedupe work remain enabled, and *"Export redesign alone does not prove
the five-second target. If they dominate, mark end-to-end acceptance FAIL."*
My Finding 1 says they **will** dominate: three full embedding scans per commit.
So the honest reading of question 5 is: **the five-second gate is correct, and
on current evidence C alone cannot pass it.** That is the strongest internal
argument for the redirect — the design's own acceptance gate predicts an
export-only PASS would be a partial result, and the real blocker (Chroma census)
is untouched by C.


---

## What I verified vs. did not

**Verified (read-only, pinned baseline `bd37946` + live state):**

- `_commit_generation` call graph and that three full non-source Chroma digests
  + two full export passes occur per one-chunk commit
  (`incremental_jsonl.py:2162–2227`, `:1452`, `:1488`, `:1906`, `:2167`,
  `:2199`, `:2226`).
- `non_source_inventory_digest` reads every row of each collection including
  documents and embeddings (`chroma_store.py:763`).
- `_export_unit_payload` writes `metadata + id` only; no embeddings/documents in
  the export (`incremental_jsonl.py:712`).
- Live export: 5.57 GB, 203,354 lines, mean 27.4 KB/line, max 67.7 KB;
  `provenance_envelope` ≈ 33–40 KB and ≈ 98% of recent records and of the file.
- `provenance_envelope` already co-stored with `provenance_commitment` /
  `provenance_envelope_hash` (`provenance_binding.py:29`,
  `cg2_rollback_baseline.py`).
- Doctor reports a real stale APPLYING transaction (age ~42,495 s) relevant to
  §9 cutover preconditions.

**Did NOT verify (and the design should not be read as having proven):**

- The actual wall-time split of the ~5 min commit. **No one has measured it**;
  that is the gap the redirect is built around. My Finding-1 attribution of the
  39 GB `rchar` to the Chroma scans is a strongly-supported inference from the
  code paths and corpus size, not a profiled measurement.
- Whether every reader of `provenance_envelope` can tolerate it being
  externalized from the unit projection (the lever-b compatibility question).
  This needs the same consumer inventory §7 builds for C, applied to the field.
- I did not run the hermetic benchmark, migration, or any mutation. No provider
  calls, no indexing.

## Review-scope conformance

Review-only per the lane: no code, no tests, no indexing, no provider calls. The
startup diagnostics and the read-only `wc`/`awk`/`python3` inspections of the
export were orientation and evidence-gathering only; they did not mutate corpus,
Chroma, or the export. Delivered as a single document on a new branch from
`origin/main`; pushed with an explicit refspec; no PR.

## Forward announcement

I finished: Kiro design review of DESIGN-issue-286-proportional-export-commit (verdict REDIRECT).
Next step:  Decide direction — authorize the constant-factor path (measure → shrink provenance_envelope → collapse passes → re-test against ~60 s / 5 s), or override to C if the real goal is mutation-safety rather than latency.
Next lane:  Ryan decides; Codex re-plans whichever path is chosen.
See my work: docs/inter-model/KIRO-2026-10-17-issue-286-proportional-export-review.md (§0 is the proportionality answer).

## TL;DR

- **Verdict: REDIRECT.** Option C is a sound design for source-proportional
  export file I/O, but it is scoped against an unmeasured premise. On live
  evidence the export file is not the binding constraint.
- The one-chunk commit does **three full non-source Chroma scans (incl. 768-dim
  embeddings) per commit** inside C1 — the likely real latency driver — and C
  touches none of it. The design's own §10.2 predicts an export-only change
  cannot pass the 5 s gate.
- The 5.57 GB export is ~98% one redundant field (`provenance_envelope`, already
  beside its own hash), not a 46 KB/unit structural floor. Shrinking it is
  plausibly ~50×, not marginal.
- Recommended order: **measure the commit → externalize `provenance_envelope` →
  collapse export passes and the triple Chroma digest → re-test against ~60 s /
  5 s.** Defer C unless export I/O is still binding afterward, or unless the real
  requirement is in-place-mutation safety (which C serves and the constant-factor
  path does not — Ryan should state which).
- On Codex's five questions: (1) C over A/B yes, but C-vs-constant-factor is the
  comparison that matters; (2) rollback-order + malformed-tail refusal yes, ship
  the repair path in the same release; (3) targeted hash + full audit sufficient
  with honesty labels enforced; (4) downgrade gates directionally right but name
  the real wedged transaction and mechanize writer fencing before Execute;
  (5) gates are correct and, on current evidence, C alone fails the 5 s gate.

<!-- src: ../plans/DESIGN-issue-286-proportional-export-commit.md @7af3073, ../../incremental_jsonl.py @bd37946, ../../chroma_store.py, ../../provenance_binding.py, ../../cg2_rollback_baseline.py, /home/lauer/.local/share/convmem/knowledge_units.jsonl (live, read-only) -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md, ../plans/STATUS-recovery-authority.md, ../plans/STATUS-safe-harbor.md, ../plans/STATUS-r2b-capture-auth.md — arc routing and compatibility boundaries -->
