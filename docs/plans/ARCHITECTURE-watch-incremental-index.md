# ARCHITECTURE — Incremental indexing for Codex JSONL

**Arc: Trapdoor Hunt** · **Issue:** [#286](https://github.com/alanmz-crypto/convmem/issues/286) · **State:** DRAFT FOR KIRO REVIEW · **Date:** 2026-09-17

This is a design, not an Execute grant. It does not change production indexing,
watcher behavior, configuration, memory caps, exclusions, or Arc Codex P2.

## 1. Product goal and decision

A small append to Codex prompt history or a rollout transcript should preserve
all source coverage while avoiding another summarize, embed, and distill pass
over unchanged historical chunks. The first safe deliverable is **transform
reuse with full-prefix verification**. It still reads the existing source
prefix. A claim of tail-only *file I/O* requires a stronger source-mutation
contract or an explicitly weaker edit-detection guarantee and is a separate
decision (§8).

The older Kiro design at `92395e9:docs/plans/DESIGN-watch-incremental-index.md`
is historical input, not the current contract. The Kiro-only, default-off
coordinator merged in [PR #293](https://github.com/alanmz-crypto/convmem/pull/293)
as `881133d`; the bounded brief fix merged in
[PR #305](https://github.com/alanmz-crypto/convmem/pull/305) as `ef4a7dd`.
The current baseline for this draft is `origin/main` `ef4a7dd972435de1fbb684cd3aba43076b8232f6`.
Both [#286](https://github.com/alanmz-crypto/convmem/issues/286) and
[#268](https://github.com/alanmz-crypto/convmem/issues/268) remain open.

## 2. Current path and corrected diagnosis

```text
watch event → watch_skip_reason: whole-file SHA-256
            → index --file: second whole-file SHA-256
            → format detection → optional Kiro-only coordinator
            → legacy Codex parser: full-file messages list
            → all sliding-window transforms → Chroma/export/processed.json
```

`watch.py` still dispatches `index --file`; `ingest.py` hashes before optional
incremental routing. Both Codex adapters expose only full-file `parse()` and
skip non-message records. `incremental_jsonl.py` accepts only
`jsonl_kiro_session`, refuses a source with a prior processed entry or Chroma
rows but no checkpoint, and reads, snapshots, parses, and revalidates the
complete selected prefix. Its prepared cache avoids historical model calls;
it does not make source I/O tail-only. Default-off and isolation gates remain.

The old design's claim that `evaluate_ingest_batch().accepted_rows` grows for
the **whole source** was wrong even at `92395e9`: the normal ingest path calls
it once per chunk. It may still consume memory per chunk, but a proposed
whole-file “units-in-flight K” fix has no supporting diagnosis. The later
export-compaction and brief fixes addressed different demonstrated
accumulators. Claude 3's paired hermetic, sampled-RSS comparison of pre-#305
`5c103aa` and post-#305 `ef4a7dd` measured exposure-probe growth at 20,000
synthetic units: +527.5 to +2.6 MiB with a small trigger and +510.4 to
+3.0 MiB with a larger trigger. At 5,000 units with a small trigger, growth
changed from +43.5 to −2.4 MiB. The narrow conclusion is that #305 removed
roughly 0.5 GiB of the targeted probe spike at 20,000 units.

That diagnostic used fake providers and synthetic data at only 5,000 and
20,000 corpus units. Its address-space ceiling was 6 GiB because real Chroma
reserves more than 2 GiB virtually; corpus seeding used real-Chroma upsert.
There is no committed harness artifact. It did not reproduce the historical
~12.5 GiB watcher OOM or measure the live corpus. Do not extrapolate a
remaining OOM “gap,” claim #286 solves that OOM, or close #268 from this result.

`watch.py` now has a 900-second child timeout. It limits a 51-minute hung child
to roughly 15 minutes, while a child can still OOM before that deadline. The
timeout is containment, not a memory bound. Retuning timeout, retry policy,
cooldown, and caps belongs to a separate #268 operational decision.

## 3. Authority and invariants

1. **Source authority.** The selected *complete* raw JSONL prefix is the
   source of truth for records. A checkpoint is processing/recovery authority;
   prepared artifacts and Chroma/export/processed entries are derived. Source
   bytes after the last newline are uncommitted and must be reconsidered on
   the next run.
2. **Format identity.** Codex history and rollout have distinct adapter
   contracts and state IDs. History contains user prompts only; rollout
   contains selected user/assistant messages. A format or path mismatch may
   not adopt another format's checkpoint or cached artifact.
3. **Continuity.** Before reusing a prior generation, compare resolved path,
   adapter contract, `(device, inode)`, selected boundary, and SHA-256 of the
   entire *prior complete prefix*. Size and a matching tail window cannot
   authorize reuse. Same-size interior edits, truncate-and-regrow, and
   replacement with identical tail must rebuild or refuse. Revalidate the
   selected prefix before publish, with a source lock/identity check across
   capture and commit. A mere `stat`/hash pair cannot prevent an uncontrolled
   concurrent writer from changing bytes between checks; a changed source
   aborts publication and retries from a new snapshot.
4. **Coverage.** A checkpoint records raw complete-line ranges and outcomes
   (emitted message or deliberately skipped by the adapter), canonical
   message count, chunk frontier, and exact summary/unit projection IDs.
   Coverage means every complete line before the boundary is accounted for,
   not that every raw line creates a message. Malformed *complete* lines follow
   a documented adapter rule; a partial last line never becomes a skip.
5. **Stable overlap.** Recompute the prior final chunk window and any new
   windows using absolute canonical-message offsets from the same
   `chunk_messages(size, overlap)` contract. Input digests include the exact
   canonical messages/rendered view, start and end offsets, adapter version,
   and transform fingerprint. Same-input chunks reuse prepared artifacts;
   the changed seam gets a new artifact. Existing summary/unit IDs and
   provenance identities must remain stable for a genuinely unchanged chunk.
6. **Complete keep set.** Publication derives a complete current-generation
   manifest, including unchanged historical chunks, the recomputed seam, and
   new chunks. The keep set contains actual physical summary and unit
   projection IDs *after* dedupe and provenance-ID selection, not only logical
   IDs from prepared units. Prune only snapshotted source-scoped candidates
   absent from that complete set, after all required writes succeed. A
   tail-only keep set is forbidden; “never prune on append” is insufficient
   for replaced seam rows and recovery.
7. **Replay.** Before any Chroma write, persist a complete prepared transform
   (summary, units, embeddings, provenance/provider binding, input digest,
   physical-ID recipe) by fsyncing the file and its parent after atomic
   replace. Replay validates its digest, source/format, fingerprint, input,
   and embedding shape. If a crash follows the first write, replay uses those
   *same* outputs and deterministic IDs; it must not call an LLM again and
   silently overwrite a previously visible result with different text.
   Missing/corrupt prepared output after a possible write means rollback from
   exact before-images or fail closed, never speculative regeneration.
8. **Authority order.** A transaction journal and source-scoped before-images
   cover both Chroma collections and affected sidecars. Revalidate source,
   apply prepared artifacts, publish checkpoint, reconcile export/dedupe, then
   publish `processed.json`. Interrupted transitions roll forward from valid
   prepared outputs or restore before-images. Exclusion checks and existing
   source/write locks remain authoritative.
9. **Fingerprint.** Key cache and checkpoint to explicit versions of both
   Codex parsers, record selection, chunking/overlap, rendering limits,
   prompts, summarize/distill/embed models and dimensions, normalization,
   provenance/ID/dedupe contracts, and relevant implementation revision.
   Any changed field invalidates reuse. A changed fingerprint requires an
   authorized rebuild path or refusal; it cannot keep stale rows and advance.

## 4. Proposed module boundary

Keep the existing `incremental_jsonl.py` transaction/replay mechanism as a
reference and extract only the shared behavior proven common to three formats.
The eligibility registry maps an exact detected format to a versioned parser
and state namespace. Kiro's existing route and default-off behavior form a
regression boundary, not a reason to expand Arc Codex P2.

Each Codex adapter needs a read-only complete-prefix parse contract returning:
complete byte boundary, prefix hash, raw line ranges/outcomes, canonical
messages in legacy order, and `(device, inode)` captured from the same open
descriptor. The history parser must preserve prompt-only filtering and
timestamp normalization; rollout must preserve its two accepted event kinds,
text-block ordering, and ignored-event behavior. Mixed newline styles, blank
lines, invalid complete JSON, invalid UTF-8, and a final unterminated record
need explicit parity/fail-closed tests. The output must agree with legacy
`parse()` on the complete prefix, including skipped lines.

The coordinator should expose one format-specific contract rather than
duplicate the state machine. The first implementation retains full-prefix
capture and verification and reuses prepared unchanged chunks. It must be
reentrant under the existing isolated root and positive mutable-path grants.
The route stays absent/false by default, Codex-only eligibility remains
explicit, and a missing `CONVMEM_INCREMENTAL_ROOT` continues to refuse live
activation. No watcher or config change is part of this plan.

## 5. Matching-tail rotation and other adversaries

An atomic replacement can have the same size and last 4 KiB as the prior
file, yet contain a different earlier conversation. The old design's
`indexed_size + tail_fingerprint` test would accept it while its prose promised
an inode check that the state did not store. Persist and compare `(device,
inode)` and hash the entire prior complete prefix. Inode reuse is possible,
so identity alone is insufficient. A same-inode interior rewrite is found by
the prefix hash. If identity or hash cannot be proven, refuse/rebuild without
advancing coverage. The new prefix hash is computed over the selected
complete bytes, not a partially written trailing line.

On a crash after writing a seam unit but before checkpoint publication, a
fresh LLM answer under the same offset-derived ID could replace content that
was already observed. Prepared-output replay closes that specific hole only
if preparation is durable before the first write and replay validates the
artifact. Fault injection must cover each durable transition.

## 6. Existing-source adoption is a separate gate

Today a Codex source may already have a `processed.json` entry and Chroma
rows. The Kiro coordinator returns `bootstrap_required` in that case. Simply
inventing a checkpoint from the current file hash would assert coverage and
cache contents that are not proven. Legacy chunks may be missing due to prior
failed transforms, exact dedupe, or projection-ID divergence. Existing rows
may also lack a complete reconstructable prepared artifact.

An adoption design may claim **zero LLM calls** only after a hermetic proof
that it can map every canonical chunk to its exact source inputs, current
summary/unit physical IDs and provenance, verify complete coverage in both
collections and relevant sidecars, and recover unchanged chunks after crash
without needing lost provider output. The proof must include a negative
fixture for missing/ambiguous rows and a byte-for-byte or semantic clean
rebuild oracle. If it cannot prove this, defer adoption: keep the legacy route
for existing sources, or propose a separately measured, Ryan-approved
one-time rebuild that may make LLM calls. No existing source is silently
adopted and no baseline is declared complete from `processed.json` alone.

## 7. Performance claim and measurement

For a verified append after a valid checkpoint, unchanged chunks should
trigger **zero** summarize, distill, summary-embed, and unit-embed calls.
Model calls scale with the affected final window plus new windows. Record
counts, reused/built chunks, model-call counters, bytes read/hashed,
wall-clock, and peak RSS must be reported separately. A fixed-source
hermetic comparison should include 1-line append to large history and rollout
fixtures and full-rebuild baseline.

This release cannot claim O(tail) source reads: `watch_skip_reason` hashes the
file, `_index_one_file` hashes it again, and the current coordinator captures
and revalidates full selected prefixes. Even a streaming prefix verifier
remains O(prefix) I/O, though its memory can be bounded. A future true
tail-seek route would have to bypass those earlier hashes *and* obtain a
trusted append-only writer guarantee, an authenticated mutation journal, or
accept an explicit interior-edit detection gap. A 4 KiB tail hash and
periodic audit are not equivalent to full-prefix authority. That separate
route needs a fresh architecture and authorization; it is not an acceptance
claim for #286's transform-reuse slice.

## 8. Decisions for Kiro review

1. Accept full-prefix verification plus transform reuse as #286's first
   complete, safety-preserving outcome, with tail-only I/O deferred?
2. Which exact malformed-complete-line and invalid-UTF-8 policy preserves
   legacy parser parity while making raw-line coverage auditable?
3. Can physical projection IDs and dedupe suppressions be reconstructed into
   a complete keep set using the existing writer API, or must the shared
   coordinator contract be amended first?
4. Is zero-call adoption provable for any existing-source class? If not,
   retain `bootstrap_required` and seek a separate one-time rebuild decision.
5. Does Claude 3's now-available, synthetic post-#305 result change the
   priority of a separate #268 memory investigation? Keep its exact revisions,
   two corpus sizes, sampled-RSS method, and 6 GiB address-space limit in
   view; it is not a live-OOM or remaining-gap measurement.

**Review request:** Kiro should pin the post-evidence commit SHA and issue a
written PASS/FAIL on that exact architecture and companion execution plan,
especially source authority, physical keep-set completeness, adoption,
replay, default-off isolation, and the bounded interpretation of Claude 3's
measurement. A review of ancestor `131ab425` does not cover this correction.
Review does not grant Execute.
