# EXECUTION — Bounded-memory, crash-safe export compaction

**Arc:** Trapdoor Hunt (issue #268 operational follow-up; does not reopen the
closed provenance T3 gate)

**Status:** DRAFT FOR KIRO REVIEW. Planning only. This file authorizes no code,
configuration, service, corpus, provider, or production operation.

**Date:** 2026-09-13

## 1. Consequence for Ryan

Every `convmem index` invocation that reaches post-index cleanup while the
global `knowledge_units.jsonl` export exists currently scans that complete file
and materializes it as a Python string, a list of lines, a dictionary of
retained lines, and sometimes a joined replacement string. A small watched
transcript can therefore trigger corpus-sized work.

The narrow correction replaces only that compactor with a bounded-memory,
disk-backed implementation. It preserves the existing writer boundary, export
lock, valid-row result, and caller contract while making publication durable and
atomic. It does **not** implement append-aware watch indexing, change watcher
timeouts, alter memory caps, or resume Arc Codex P2.

## 2. Evidence and corrected diagnosis

The recurring September 12 OOMs reached the watch child's 12 GiB cgroup ceiling
while indexing 5.8–9.7 MiB Codex JSONL files. Arc Codex review found no active
watch-path regression at merged runtime
`8983a6fc909344239e6e3051d85c50c5508c1a16`. The small source merely triggered
global post-index work.

A Ryan-authorized hermetic diagnostic at that revision measured
`ingest._deduplicate_units_export_impl()` under a 2 GiB address-space limit:

| Synthetic export | Peak RSS | Elapsed |
|---:|---:|---:|
| 16 MiB | 130.07 MiB | 0.045 s |
| 64 MiB | 219.92 MiB | 0.158 s |
| 128 MiB | 351.88 MiB | 0.309 s |

The 128 MiB parse-and-chunk comparison peaked lower at 258.71 MiB. The export
fixture was duplicate-heavy, so the `seen` dictionary retained only one entry;
this is a **conservative** memory shape, not a worst case. A mostly-unique real
export retains substantially more data. The production export was observed by
read-only stat at approximately 2.4 GiB.

This corrects one claim in the earlier issue #268 design at commit `92395e9`:
`evaluate_ingest_batch()`'s `accepted_rows` is per chunk, not retained for the
whole source. Append-aware ingestion remains valuable, but the demonstrated
size-independent OOM floor is now most directly explained by global export
compaction, potentially stacked with Chroma/brief allocations.

No further memory profiling is a precondition for this narrow correction. The
implementation PR must repeat a bounded hermetic memory check against the new
code as verification, not as design discovery.

## 3. Scope lock

### In scope

- Replace the in-memory implementation behind export compaction.
- Add one deep module that owns scanning, disk-backed indexing, bounded record
  handling, and streaming output.
- Add streaming durable publication to the existing `atomic_files.py` boundary
  rather than inventing a second atomic-replace protocol.
- Preserve the `production_writer_boundary(entrypoint="ingest.export")` and the
  export flock for the entire scan and publication.
- Add semantic-parity, fault-injection, concurrency, and bounded-memory tests.
- Refresh code-derived writer inventories and intentionally rebaseline the Arc
  Codex `ingest.py` hash after proving its routing/default-off behavior did not
  change.

### Out of scope

- Append-aware Codex/Cursor/Kiro watcher ingestion.
- Chroma/HNSW memory, global brief scans, model calls, retry policy, cooldown,
  debounce, timeout, or watcher subprocess construction.
- Any live configuration, memory-cap, systemd, watcher, exclusion, or source
  change.
- Production compaction, live indexing, corpus repair, purge, or re-inclusion.
- Arc Codex Gate 0, P2, grant preparation, digest issuance, or activation.
- A new CLI/config knob or a second compaction mode.

The broader issue #268 plan remains open after this slice. Landing this
correction does not by itself authorize the watcher or Arc Codex P2 to resume.

## 4. Existing observable contract

The replacement must preserve these results for valid JSON-object rows:

1. Blank lines do not count as records.
2. A non-empty string `id` is the deduplication key.
3. The retained value is the **last** record seen for an ID.
4. Retained IDs are emitted in **first-occurrence order**. Updating an existing
   Python dictionary value does not move its position; the disk-backed index
   must reproduce that behavior deliberately.
5. When every nonblank row has a unique valid ID, return `0` and do not replace
   the export; its bytes, whitespace, and metadata remain unchanged.
6. When compaction occurs, retained lines are stripped and written with one
   trailing newline; the return value is `nonblank_rows - retained_ids`.

The current code's malformed-row behavior is unsafe and internally
contradictory: its comment says malformed lines are preserved, but decode errors
and missing IDs can be silently dropped when any rewrite occurs, while valid
non-object JSON can raise `AttributeError`. This slice makes one intentional
hardening change:

> Any nonblank row that is invalid UTF-8, invalid JSON, not an object, lacks an
> `id`, has an empty `id`, or has a non-string `id` aborts compaction before
> publication. The original export remains byte-identical and the error is
> visible to the caller.

No repair, skipping, quarantine, or best-effort rewrite is permitted in this
slice.

## 5. Chosen design

### 5.1 Deep module boundary

Add `export_compaction.py` with one production entry point:

```python
compact_units_export(export_path: Path) -> int
```

The module hides scratch storage, row validation, offset indexing, streaming
publication, and cleanup. `ingest.py` retains the existing governed wrapper and
delegates to this function. No CLI or configuration surface is added.

### 5.2 Bounded input records

Open the export read-only with `O_CLOEXEC | O_NOFOLLOW`, require a regular file,
and record its device, inode, size, mode, uid, gid, mtime, and ctime while the
export flock is held. Read one binary line at a time with a hard maximum of
**16 MiB per record**, including the line terminator.

An oversized or unterminated-over-limit record raises a typed pre-publication
error. This numeric bound is intentionally code-owned rather than configurable:
it prevents one corrupt JSONL record from recreating the OOM class and avoids a
new operational knob. Kiro must explicitly accept or revise the 16 MiB value.

Enforce the ceiling **incrementally while scanning for the line terminator**:
each read is bounded by the remaining record budget plus one detection byte,
and the scanner aborts as soon as consumed bytes exceed 16 MiB. It must never
call an unbounded line-read operation and then measure the completed result, so
an unterminated multi-gigabyte record cannot be materialized first.

### 5.3 Disk-backed offset index

Use Python's standard-library `sqlite3` in an invocation-owned private scratch
directory created beside the export so the implementation does not depend on a
second filesystem or an uncontrolled system temp directory. Create the
directory as `0700` and its files as `0600`; reject symlinks and do not reuse a
pre-existing path. The database stores only:

- `id` — primary key;
- `first_seq` — ordinal of the first occurrence;
- `last_offset` — byte offset of the latest occurrence;
- `last_length` — byte length of the latest occurrence.

For each valid row, insert the four values. On ID conflict, update only
`last_offset` and `last_length`; never update `first_seq`. Add an index on
`first_seq` so output order does not require an in-memory sort. Use a fixed
SQLite page-cache budget and file-backed temporary storage. Commit scratch
transactions in bounded batches.

The database does **not** store complete JSON lines. RSS is therefore bounded by
Python/import overhead, a fixed SQLite cache, one bounded input record, and one
bounded output record. Scratch disk grows with the number and size of IDs, not
with retained document text. This deliberately exchanges corpus-sized RAM for
bounded RAM plus local scratch I/O; the implementation must surface disk-full
errors without publishing or modifying the original export.

### 5.4 No-op path

After the scan:

- zero nonblank rows → close scratch and return `0`;
- unique valid IDs equal nonblank rows → close scratch and return `0` without
  opening a publication temp;
- otherwise stream a replacement.

This preserves the important byte-identical no-op behavior and avoids rewriting
a multi-gigabyte export merely because it was checked.

### 5.5 Streaming replacement

Extend `atomic_files.py` with a callback-based binary streaming primitive:

```python
atomic_write_stream(
    path,
    writer,
    *,
    preserve_mode=True,
    validate_before_replace=None,
) -> None
```

It owns temp creation in the destination directory, callback execution,
flush/fsync, mode preservation, atomic `os.replace`, parent-directory fsync,
failure classification, descriptor closure, and cleanup of only its own
unpublished temp. Existing `atomic_write_bytes/text/json` behavior must remain
unchanged; refactoring them through the new primitive is optional only if their
current fault suite remains byte-for-byte green.

After the writer callback and temp-file fsync, but before `os.replace`, invoke
the optional validator. A validator failure is a `PrePublicationError`: the
original remains visible and the helper removes only its unpublished temp. This
narrow hook lets the compactor perform its final source-identity check at the
actual publication boundary rather than before a potentially long output pass.

The compactor queries offsets ordered by `first_seq`, uses bounded `pread` (or
equivalent exact-offset reads) against the still-open original descriptor,
strips the retained record exactly once, and writes it plus `\n` directly to the
atomic temp stream. It never builds a list of retained lines or a joined output
string.

Through `validate_before_replace`, revalidate that the path still identifies
the same regular file, device, inode, size, uid, gid, mode, mtime, and ctime
observed at scan start. Although the export flock is the primary concurrency
boundary, this check prevents a non-cooperating replacement or same-size
in-place mutation from being overwritten. Keep the original descriptor open
through publication; replacing the pathname while reading through that
descriptor is safe and avoids reopening a path that changed outside the lock.

### 5.6 Crash and failure states

| Failure point | Required visible state |
|---|---|
| Scan, validation, SQLite, or output callback fails | Original export unchanged; invocation-owned handled-failure scratch removed. |
| Output flush/fsync or mode preservation fails | Original export unchanged; `PrePublicationError`. |
| Identity changes before replace | Original export unchanged; typed pre-publication refusal. |
| Replace succeeds | Complete compacted export visible; never a partial file. |
| Parent-directory fsync fails after replace | Complete new export visible; `PostPublicationDurabilityError` reports uncertain crash durability. |
| Process is SIGKILLed before replace | Original export remains visible; private scratch/temp may remain but is never published. |
| Process is SIGKILLed after replace | Complete new export is visible; durability follows whether parent fsync completed. |

Do not add broad stale-temp cleanup. Normal exceptions clean only artifacts
owned by that invocation, matching the existing `atomic_files.py` safety rule.
A hard kill may leave private scratch; that bounded operational residue is safer
than deleting files by glob or weakening publication isolation.

## 6. Alternatives considered

### A. Keep the Python dictionary and read incrementally — rejected

Streaming the input alone is insufficient because complete retained JSON lines
still accumulate in `seen`, and the final join duplicates them again.

### B. SQLite storing complete retained lines — rejected

This bounds RSS but duplicates much of a 2.4 GiB export into both the scratch DB
and the replacement. Offsets preserve the same result with less scratch I/O and
disk demand.

### C. External `sort`/shell pipeline — rejected

It introduces platform/process dependencies and makes JSON validation,
first-occurrence order, last-value selection, and atomic error reporting harder
to express and test.

### D. Skip compaction after watched indexing — rejected

It avoids the immediate OOM but restores unbounded export growth and changes the
existing output-maintenance contract.

### E. Full issue #268 append-aware watcher implementation — deferred

It is broader and has independent prune/cursor/crash hazards. The measured
compactor defect can be removed without coupling it to watcher state.

## 7. Cursor implementation sequence

Implementation requires a separate Ryan Execute authorization after Kiro
accepts this plan.

### C0 — Freeze legacy semantics

Add golden tests around the current implementation before replacement:

- all-unique valid rows produce no rewrite;
- duplicates retain last value in first-ID order;
- whitespace/blank-line/trailing-newline behavior;
- malformed, non-object, missing-ID, empty-ID, and non-string-ID inputs;
- return count and file mode.

Record which malformed cases intentionally change to fail-closed behavior.

### C1 — Add streaming atomic publication

Add `atomic_write_stream` and fault tests for callback failure, partial write,
flush, temp fsync, mode preservation, replace, directory fsync, temp cleanup,
and repeated-call descriptor stability.

### C2 — Implement the offset-index compactor

Implement the bounded scanner, typed validation failures, SQLite offset table,
no-op decision, identity revalidation, and streaming replacement in
`export_compaction.py`.

### C3 — Integrate without widening authority

Route the existing `ingest.export` writer boundary to the new module. Keep the
export flock held across scan, scratch work, and publication. Do not change
watch routing, processed-state commits, Chroma writes, or CLI/config surfaces.

### C4 — Prove correctness and crash safety

Add focused tests for:

1. valid-row golden parity, including a final record without a newline;
2. malformed/oversized fail-closed behavior with byte-identical original;
3. input replacement and same-inode size/content mutation during compaction;
4. injected SQLite and ENOSPC/write failures;
5. every atomic publication fault boundary;
6. lock contention with an append writer;
7. handled-failure scratch cleanup and no foreign-temp deletion;
8. exact mode preservation and zero descriptor growth.

### C5 — Prove bounded memory

Run the compactor in fresh hermetic subprocesses over duplicate-heavy and
unique-heavy 16, 64, and 128 MiB exports. Use a fixed address-space ceiling and
report baseline/peak RSS and throughput. Acceptance requires:

- all cases complete below **512 MiB peak RSS** on the implementation host;
- 128 MiB peak is no more than 96 MiB above the import-only baseline;
- unique-heavy growth does not scale with retained document bytes;
- original and compacted SHA-256/output counts match the golden oracle.

These are verification thresholds for the measured host, not a claim that every
platform has the same import floor. CI runs semantic/fault tests; the PR records
the dedicated memory evidence.

### C6 — Refresh governed surfaces and regressions

- Update/regenerate R2b v2 and Shadow writer inventories for any moved sink.
- Keep `ingest.export` in `writer_census.KNOWN_ENTRYPOINTS`.
- Intentionally update `tests/test_incremental_jsonl_canary_baseline.py` and the
  Arc Codex VERIFY hash for `ingest.py`; do not describe the old hash as still
  current.
- Re-run Arc Codex baseline/runtime-readiness suites to prove default-off,
  source immutability, and P2 denial did not change.
- Run the focused export/atomic/lock suites, repo-wide pytest, compileall,
  `git diff --check`, scoped pylint, and the repository pylint regression gate.

### C7 — Stop for review

Commit and push the implementation branch, report exact SHAs and memory results,
and stop. No PR, live compaction, source re-inclusion, watcher operation, or P2
progression follows from implementation.

## 8. Acceptance criteria

- Peak RSS is bounded independently of total export bytes and retained-row
  count, subject only to the explicit 16 MiB record bound and fixed caches.
- The valid-row output and return count match the frozen legacy oracle.
- Malformed or oversized input fails closed without altering the export.
- Original-or-complete-new visibility holds across every injected failure.
- File mode is preserved; output file and parent directory are fsynced.
- The export lock covers the full compaction transaction.
- No processed, Chroma, source, watcher, configuration, or provider behavior
  changes.
- Writer inventories and Arc Codex baseline evidence are honestly refreshed.
- Focused and repo-wide verification pass on one exact tip.

## 9. Required review and delivery order

1. **Kiro:** review this plan, especially valid-row parity, malformed-row
   fail-closed policy, the 16 MiB record bound, SQLite offset semantics, crash
   states, and memory thresholds.
2. **Ryan:** if Kiro PASSes, issue a separate bounded Cursor Execute grant.
3. **Cursor:** implement C0–C7 and stop at an exact pushed tip.
4. **GitHub Copilot audit lane:** targeted audit for data loss, authority/lock
   escape, temp/symlink hazards, and false memory evidence.
5. **Kiro:** exact-tip implementation review.
6. **Ryan:** PR and merge disposition.
7. **Ryan:** separately decide when exclusions, watcher activity, and Arc Codex
   P2 may be reconsidered.

Claude is not required. Sol-High is invoked only if the Copilot audit lane and
Kiro issue materially conflicting PASS/FAIL verdicts on the same revision.

## 10. Kiro review questions

1. Does the disk-backed offset index reproduce Python-dictionary ordering and
   last-value semantics for every valid row?
2. Is fail-closed refusal preferable to the legacy malformed-row deletion?
3. Is 16 MiB an adequate explicit per-record ceiling?
4. Does the atomic publication contract distinguish pre- and post-publication
   failures honestly?
5. Are the proposed memory thresholds strong enough without making CI flaky?
6. Does any step widen writer authority or interfere with Arc Codex's
   default-off/live-denial guarantees?

## TL;DR

- Replace whole-export Python materialization with a SQLite offset index and
  streaming atomic publication.
- Preserve valid-row semantics; malformed or oversized rows fail closed and
  leave the original byte-identical.
- Prove crash safety, lock coverage, bounded RSS, inventory accuracy, and Arc
  Codex non-regression before review.
- Plan review grants no implementation or production authority.
