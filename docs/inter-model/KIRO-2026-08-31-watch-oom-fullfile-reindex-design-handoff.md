# Design/Review Handoff: watch OOM is full-file re-index, not child blast radius

**Arc: Trapdoor Hunt**

**Date:** 2026-08-31
**Author:** Kiro (design/review)
**For:** Ryan (decision) → Cursor (implementation, under a later Execute grant)
**Upstream:** [`CODEX-2026-08-31-kiro-watch-oom-followup-handoff.md`](CODEX-2026-08-31-kiro-watch-oom-followup-handoff.md)
**Prior fix:** [`KIRO-2026-08-29-watch-oom-subprocess-cap-handoff.md`](KIRO-2026-08-29-watch-oom-subprocess-cap-handoff.md)

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `READY_FOR_RYAN` (design-only; no runtime change made) |
| **Branch** | `docs/2026-08-31-kiro-watch-oom-followup` |
| **Push status** | push after commit |
| **PR** | not opened |
| **Ryan GATE** | implementation requires a separate Execute grant to Cursor |
| **Track A ingest** | this Kiro session transcript |

---

## Consequence first (what changes for Ryan)

The subprocess memory cap is working exactly as designed — it is **containing** the
problem, not causing it. The real defect is that **every append to a watched file
re-indexes the entire file from scratch**. The cap turns a would-be service crash into
a per-file error, but the affected file is left stale and the desktop OOM notification
still fires. Raising the cap or enabling swap would only move the ceiling; the next
larger transcript would hit it again.

The fix that removes the OOM class (not just the symptom) is **incremental,
append-aware indexing** so a one-line append does one-chunk work, plus a **hard input
bound** so no single file can ever demand unbounded memory. Both are implementable and
testable without touching live services.


---

## Root cause — code-grounded

The dominant allocation source is **repeated full-file work**, not Ollama model residency
alone and not Chroma steady state. Chain of evidence in the current tree:

1. **Idempotency is keyed on the whole-file hash.** `ingest.py:_index_one_file()` computes
   `file_hash = sha256_file(path)` and skips only when `file_hash in processed`. A single
   appended line changes the whole-file hash → the skip never fires → the entire file is
   re-processed.

2. **Every adapter returns the full message list.** `adapters/codex_history_jsonl.py:parse()`
   (and every other `parse()` — `jsonl_chat.py` for Cursor, `kiro_session_jsonl.py`,
   `codex_rollout_jsonl.py`, etc.) reads the whole file into a list. There is no offset or
   cursor. Confirmed: all ten adapters expose the same `parse(filepath) -> list[dict]`
   whole-file contract.

3. **The whole message list is re-chunked and re-summarized every time.**
   `_process_file_chunks()` calls `chunk_messages(messages, 60, 10)` (config: `chunk_size=60`,
   `chunk_overlap=10`, step 50). For the live `~/.codex/history.jsonl` (2768 lines,
   ~5.0 MB) that is ~55 chunks. **Each chunk** runs one `summarize()` + one `ollama_embed()`
   + one `_distill_with_provenance()`. So a single new prompt re-runs ~55×3 model calls over
   the whole file.

4. **Per-unit Chroma queries multiply the working set.** In the batch write,
   `ingest_dedupe.evaluate_ingest_batch()` calls `store.query_units(embedding, candidate_k)`
   (config default `candidate_k=10`) for **every** candidate unit across the whole file, each
   pulling candidate rows + metadata into memory.

5. **Reindex snapshot doubles the Chroma touch.** Because watch always calls with
   `force_file`, `_index_one_file()` runs `_snapshot_reindex_rows()` before the build and
   `_prune_completed_reindex()` after — two more full passes over the source's existing rows.

### Why the 6 GiB cap is genuinely reached

The observed kills were a full history rebuild (`history.jsonl` at 15:41) and a full **Cursor
agent transcript** rebuild (16:31). Agent transcripts carry far more text per message than
prompt-only history, so `render_chunk()` + `distill` inputs and the accumulated
`raw_units` / `message_views` / `units_to_add` per chunk, held across ~dozens of chunks in
one child, plus the resident embedding model and Chroma HNSW query working set, legitimately
exceed 6 GiB. Both failures reported exactly `usage 6291456kB, limit 6291456kB` — the child
hit its own scope ceiling doing honest full-file work. The parent survived (cap did its job).

**Conclusion:** the memory is dominated by *quantity of full-file work per append*, not by a
leak and not by a single oversized allocation. This is consistent with the ledger
(`dec_prop_20260623_004023_44a1`: prior OOM root cause was `force_file` bypassing skip checks;
the same full-file-rebuild family recurs here for *changed* files that legitimately re-index).


---

## Options reviewed (with disposition)

| Option | Verdict | Reason |
|--------|---------|--------|
| Raise `MemoryMax` / enable child swap | **Reject as primary** | Moves the ceiling; the next larger transcript re-hits it. Ledger already rejects "increase swap when workload exceeds RAM". |
| Exclude `history.jsonl` / transcripts | **Reject** | Data loss; handoff explicitly forbids. Does not stop the next source from OOMing. |
| Append-only cursor for append-only sources | **Accept (primary)** | Removes the recurring class for the common case (history + rollout append). One-line append → bounded one-chunk work. |
| Hard per-file input bound (message + char cap per child) | **Accept (primary)** | Guarantees no single child can demand unbounded memory even for rewrite/first-index of a huge file. Safety net that makes the cap sufficient. |
| Per-child timeout + retry/backoff | **Accept (secondary)** | Bounds wall-clock blast radius and stops churn on a repeatedly-failing file; does not itself reduce peak memory. |
| Backlog/concurrency gate | **Partially accept** | Loop is already serial (`subprocess.run` blocks — confirmed). A *backoff/skip* gate for a file that OOMs repeatedly is worth adding; do NOT add spawn concurrency. |
| Smaller Chroma/embedding unit of work | **Fold into append-cursor** | Processing only the new tail chunks naturally shrinks the per-child Chroma query count and Python retention. |

### Recommended shape (design intent only)

1. **Append detection.** For append-only sources (Codex history/rollout, and any adapter
   that can prove monotonic append), record the last-indexed byte offset (or line count) in
   `processed.json` alongside the file hash. On change, if the stored prefix still matches
   (file grew, prefix unchanged), parse and index **only the new tail** as its own chunk set,
   and skip the whole-file rebuild. Correctness fallbacks below.

2. **Hard input bound per child.** Cap messages-per-index-invocation and characters-per-chunk
   render so a first-index or rewrite of a very large file is processed in **bounded batches**
   (multiple bounded children or a bounded internal loop), never one unbounded pass.

3. **Repeated-failure backoff.** If a file's index child exits non-zero (OOM = exit 137 / -9
   in scope), record a short cooldown so the watcher does not immediately re-spawn the same
   expensive child in a loop. Keep the existing "one error line, unit survives" behavior.

### Correctness guards (must hold — these are the hard part)

Append-cursor optimization must **degrade to full rebuild** whenever append cannot be proven:

- **Truncation / rewrite / rotation:** stored offset > current size, or stored prefix hash
  ≠ recomputed prefix hash → treat as changed-from-start, full rebuild.
- **Duplicate prompts across appends:** existing ingest dedupe (`evaluate_ingest_batch`
  exact + semantic) already handles content equivalence; the cursor must not suppress a
  genuinely new-but-identical prompt beyond current dedupe semantics.
- **Crash mid-append:** advance the cursor only after a durable commit
  (`commit_processed_index_entry`), so an interrupted child re-processes the same tail rather
  than skipping records. Cursor advance and hash commit must be one transaction under the
  existing processed-state lock.
- **Chunk-boundary overlap:** because chunking uses `overlap=10`, the tail parse must include
  the trailing `overlap` messages of the prior window so cross-boundary units are not lost.


---

## Memory & swap policy recommendation (from evidence)

- **Keep** the per-child systemd scope (the 2026-08-29 fix). It is correct and must stay.
- **Do not** raise `MemoryMax` or enable child swap as the fix. Evidence shows the child was
  doing legitimate full-file work up to exactly 6 GiB; the durable fix is to make that work
  bounded, not to grant it more room.
- After incremental + input-bound land, the appropriate child cap is expected to drop back
  toward the original `2G` / `1500M` defaults (a bounded tail-index of a few chunks should sit
  well under that). **Recommend re-measuring** a bounded child's peak before lowering the
  live cap; the cap value change is a Ryan-owned operational decision, not part of the
  implementation branch.
- The current live `subprocess_memory_max = "6G"` / `subprocess_memory_high = "6G"` in
  `~/.config/convmem/config.toml` was raised as a stopgap; note it for Ryan to lower once the
  bounded child is measured. Do not edit that file from the implementation branch.

---

## Design-only vs Cursor-implementable

**Design-only (this handoff):** root-cause diagnosis, option dispositions, correctness
contract, and the memory/swap recommendation above. No runtime code changed by Kiro.

**Cursor-implementable (under a later Ryan Execute grant):**

- `processed.json` schema addition: per-path `indexed_offset` + `prefix_hash` (additive,
  backward-compatible; absent → full rebuild).
- Append-tail path in `ingest.py` (`_index_one_file` / `_process_file_chunks`) guarded by the
  correctness fallbacks; whole-file rebuild remains the default and the fallback.
- Per-adapter `supports_append` capability flag (only append-only formats opt in; SQLite and
  rewrite-prone formats stay full-rebuild).
- Hard input bound (messages-per-invocation, chars-per-chunk) in the ingest config with
  documented defaults.
- Repeated-failure cooldown in `watch.py`'s spawn loop (no concurrency added).

---

## Test plan (for the Cursor Execute slice)

Fixtures/monkeypatch only — do not spawn real `systemd-run`, real Ollama, or real Chroma in CI.

1. **Append advances cursor:** index a file, append N lines, assert only the new tail chunks
   are built (mock `summarize`/`distill`/`embed`; assert call count ∝ tail, not whole file).
2. **Prefix-mismatch → full rebuild:** rewrite an early line; assert stored `prefix_hash`
   mismatch triggers full rebuild, not a corrupt partial index.
3. **Truncation → full rebuild:** shrink file below stored offset; assert full rebuild.
4. **Crash before commit → no skip:** simulate child failure after build, before
   `commit_processed_index_entry`; assert cursor not advanced, tail re-processed next run.
5. **Overlap boundary:** unit spanning the last pre-append chunk boundary is still produced.
6. **Input bound:** a file exceeding the message/char cap is processed in bounded batches;
   assert no single invocation exceeds the bound.
7. **OOM child cooldown:** child exit 137 records a cooldown; watcher does not immediately
   re-spawn the same path; unit stays alive (existing `test_watch_subprocess_memcap.py` style).
8. **Dedupe unchanged:** identical-content append still routed through existing exact/semantic
   dedupe (no regression in `evaluate_ingest_batch` semantics).

---

## Acceptance criteria (investigation)

- [x] Dominant memory-growth mechanism identified with code proof — repeated **full-file**
      summarize/embed/distill + per-unit Chroma queries on every append, keyed by whole-file
      hash. Not a leak; not model residency alone.
- [x] Proposed mitigation preserves watched-source coverage and crash recovery — append-cursor
      degrades to full rebuild on any un-provable append; cursor advances only post-commit.
- [x] Proposal addresses both repeated full-file work (append cursor) and child blast radius
      (hard input bound + cooldown).
- [x] Focused test plan covers append, rewrite/truncate, timeout/OOM, retry/cooldown, backlog.
- [x] Design-only vs Cursor-implementable boundary stated explicitly.
- [x] No live service or database mutation performed.

---

## Safety and scope locks honored

- No `history.jsonl` / transcript exclusion proposed.
- No live DB mutation, bulk index, or service reconfiguration performed.
- No edit to the systemd unit or config drop-in from this branch.
- No spawn concurrency added to the watcher.
- Incremental indexing is presented as a **new proposal**, not an approved/documented design.
- No crossing into R2b, Recovery Authority, Shadow Ledger, or other governed arcs. The
  untracked naturalistic-G5c/G6 and PRE-G6 files in the tree were not touched.

---

I finished: [Arc Trapdoor Hunt] watch OOM root-cause diagnosis + bounded mitigation design
Next step:  Ryan decides whether to grant a Cursor Execute slice for append-cursor + input bound
Next lane:  Ryan (grant) → Cursor (implement)
See my work: docs/inter-model/KIRO-2026-08-31-watch-oom-fullfile-reindex-design-handoff.md

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Trapdoor Hunt | Dependability & provenance trust architecture arc (see `config/agent-protocol.md`). |
| Track A | Indexing this session's chat transcript into convmem. |
| Execute grant / Execute slice | Ryan-authorized permission for the implementer lane (Cursor) to write runtime code from a design. |
| force_file | Ingest mode (used by watch) that indexes one specific file; triggers reindex snapshot/prune. |
| append-cursor | Proposed per-path byte-offset/line marker in `processed.json` so appends index only the new tail. |
| prefix_hash | Proposed hash of the already-indexed file prefix, used to detect rewrite/truncation and force full rebuild. |
| processed.json | Ingest idempotency ledger mapping file content-hash → indexed chunks/units (`index.processed_log`). |
| chunk_size / overlap | Ingest windowing: 60 messages per chunk, 10-message overlap (step 50). |
| candidate_k | Number of Chroma neighbors queried per unit during ingest dedupe (default 10). |
| subprocess_memory_max/high | Per-index-child systemd scope memory cap set in `[watch]` config (currently 6G stopgap). |
| supports_append | Proposed per-adapter capability flag; only monotonic-append formats opt into the append-cursor path. |
| OOM | Out-of-memory kill; in a systemd scope surfaces as child exit 137 / -9. |
