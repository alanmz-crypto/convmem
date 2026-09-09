# ConvMem Incremental Indexing — Second-Opinion Adversarial Handoff

> Status: **open review request** — ConvMem’s current watcher still performs full-source reprocessing when a watched source changes. The proposed remedy is not yet implemented or authorised for production rollout.

## TL;DR

ConvMem is incurring avoidable model, embedding, CPU, and memory cost because a small append to a watched source invalidates the whole-file hash and causes the entire source to be parsed, rechunked, summarised, embedded, deduplicated, and written again.

Please challenge the proposed chunk-level incremental-indexing approach before implementation. The desired outcome is a reversible, conservative change that materially reduces append cost without losing, duplicating, or corrupting memories.

## Reviewer role

Act as an independent senior storage/indexing reviewer. Do not edit this handoff or the ConvMem repository. Return a claim-by-claim verdict, identify missing invariants, and give corrected one-line formulations for any claim that is too strong.

## Ground truth

The repository is `alanmz-crypto/convmem`.

### Confirmed issue evidence

- [Issue #286 — Make changed-file indexing incremental at chunk/append level](https://github.com/alanmz-crypto/convmem/issues/286) states that a 1 KB change causes the entire file to be reindexed. Its confirmed root cause is whole-file SHA-256 idempotency followed by full parsing, sliding-window rechunking, summarisation, embedding, distillation, deduplication, and writes.
- [Issue #268 — Watch OOM: full-file re-index on every append](https://github.com/alanmz-crypto/convmem/issues/268) records repeated OOM incidents and states that raising the child cap from 6G to 12G is only an interim mitigation, not the fix.
- The proposed design in #286 calls for a persisted byte/message offset, prefix hash validation, parsing only complete new records, reprocessing only the final affected chunk and new chunks, reuse of unchanged chunk results, and conservative full rebuild fallback.

### Current local operating context

- The ConvMem corpus is shared across multiple projects and currently contains roughly 40,000 active knowledge units.
- The watchdog configuration was narrowed to the exact relocation session database:
  `/home/lauer/Projects/SubProjects/Relocating_Habitat/Shipping_Transportation/.crush/crush.db`.
- The relocation Markdown plans are not ordinary watcher inputs; plain `.md` files have no active parser in the current watch path.
- Cost containment recommendation: keep the watcher paused until the incremental path has been reviewed and tested.
- The existing full-rebuild path must remain available as a recovery fallback.

## Proposed implementation boundary

### Phase 1 — append-only JSONL

Implement incremental indexing only for explicitly supported append-only JSONL adapters:

1. Persist the last indexed byte/message offset and a hash of the indexed prefix.
2. Verify the prefix is unchanged before trusting incremental mode.
3. Parse only complete records after the saved offset.
4. Reprocess the final boundary chunk if the append changes its context, then process new chunks.
5. Reuse unchanged chunk outputs, embeddings, provenance, and deduplication decisions where valid.
6. Never prune existing units merely because an append occurred.
7. Fall back to a full rebuild on truncation, rotation, rewrite, prefix mismatch, parser/config/model change, malformed state, or uncertain crash recovery.

### Phase 2 — SQLite / `.crush` source

Handle SQLite separately rather than assuming the JSONL algorithm applies. The reviewer should assess whether stable row identity, transaction boundaries, database WAL state, and a monotonic record identifier can support safe incremental reads. If not, `.crush` should remain paused or full-rebuild-only.

### Containment and rollout

- Keep current full indexing behind the existing path.
- Gate incremental mode by adapter/source capability.
- Add a dry-run or metrics mode reporting `reused_chunks`, `new_chunks`, `reprocessed_chunks`, `full_rebuild`, and fallback reason.
- Canary one large JSONL source before enabling broad watch coverage.
- Compare model calls, embedding calls, wall time, memory peak, and indexed coverage before/after.
- Do not delete or rewrite existing corpus data as part of the first rollout.

## Suspected weak links to challenge

| ID | Claim or design assumption | Required challenge |
|---|---|---|
| W1 | A byte cursor plus prefix hash is sufficient to detect safe append-only continuation. | Test partial writes, newline boundaries, encoding changes, concurrent writers, rotation, and prefix-hash collision/implementation mistakes. |
| W2 | Only the final boundary chunk and new chunks need processing after an append. | Check sliding-window overlap, summary context, chunk numbering, downstream references, and whether earlier deterministic IDs can change. |
| W3 | Unchanged chunk outputs can be safely reused. | Require exact cache-key inputs: source identity, chunk content, parser version, chunking parameters, model/version, prompt, and configuration. |
| W4 | Append mode must never prune. | Determine how stale units are removed after rewrites and how append/rewrite mode transitions are recorded without orphaning or duplicating units. |
| W5 | Full rebuild fallback preserves safety. | Specify atomicity, crash recovery, processed-log ordering, and how a failed incremental attempt is prevented from falsely marking a source complete. |
| W6 | JSONL is the right first implementation target. | Confirm it addresses the largest cost drivers and does not create a second inconsistent ingest path. |
| W7 | SQLite `.crush` can be handled later without architectural rework. | Identify shared interfaces needed now so Phase 1 does not hard-code JSONL-only assumptions into provenance or pruning. |
| W8 | The expected savings are material. | Demand a measurable baseline and define what counts as a successful reduction in model/embedding calls and memory. |
| W9 | Existing corpus data can remain untouched. | Check whether reused chunks require migration, metadata backfill, deterministic-ID changes, or Chroma schema changes. |
| W10 | Pausing the watcher is operationally safe. | Check pending events, changed sources, restart behaviour, and whether refine or reconciliation can still trigger expensive work independently. |

## Required reviewer questions

1. What is the minimum durable state needed to make append indexing crash-safe?
2. What exact invariants prove that no source record is lost or indexed twice?
3. Which identifiers must remain stable for provenance, Chroma rows, summaries, deduplication, and pruning?
4. What events force a full rebuild, and how are they detected before any destructive write?
5. Can an incremental run be made idempotent if it crashes after writing some new chunks but before advancing the cursor?
6. How should the system behave when the source changes during parsing or indexing?
7. Should summary/embedding reuse be content-addressed, chunk-position-addressed, or both?
8. What is the safe treatment of a SQLite WAL, checkpoint, vacuum, or live database writer?
9. What metrics and canary threshold should gate production enablement?
10. Is the proposed 3–5 working-day estimate for a safe JSONL first slice realistic, or what work is missing?

## Defensible core — protect unless disproved

- Whole-file reprocessing on append is an established cost and memory problem in the current implementation.
- Raising the memory cap is containment, not a cost fix.
- A conservative fallback to full rebuild is preferable to guessing when source continuity is uncertain.
- The first implementation should be adapter-scoped and reversible.
- SQLite/`.crush` handling deserves separate review from append-only JSONL.
- No initial rollout should delete existing memories or require an irreversible corpus migration.

## Required verdict format

Return exactly these sections:

### Overall verdict

`PASS`, `PASS WITH CONDITIONS`, or `FAIL`

One paragraph explaining whether the proposed rollout is safe to implement.

### Claim-by-claim verdicts

| ID | Verdict (`agree` / `refute` / `restate`) | Evidence or reasoning | Corrected formulation if needed |
|---|---|---|---|
| W1 |  |  |  |
| W2 |  |  |  |
| W3 |  |  |  |
| W4 |  |  |  |
| W5 |  |  |  |
| W6 |  |  |  |
| W7 |  |  |  |
| W8 |  |  |  |
| W9 |  |  |  |
| W10 |  |  |  |

### Blocking conditions

List only conditions that must be resolved before implementation or before production enablement. Distinguish implementation blockers from later hardening.

### Recommended execution order

Give a short ordered sequence with the smallest safe first slice, required tests, canary source, rollback trigger, and recommendation for `.crush` SQLite handling.

### Confidence

State `high`, `medium`, or `low`, with one sentence explaining what remains unverified.

## Review boundary

This is a design and safety review only. Do not merge, deploy, restart services, alter ConvMem configuration, modify the corpus, or claim that the cost reduction has been demonstrated. Implementation should occur in an isolated ConvMem worktree after the review and explicit execution authorisation.
