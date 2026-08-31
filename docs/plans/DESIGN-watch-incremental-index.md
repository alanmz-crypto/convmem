# DESIGN — Bounded, incremental watch indexing (watch OOM durable fix)

**Arc: Trapdoor Hunt**

**Status:** REVISED after adversarial review → Ryan gate. Design-only; no implementation authority.
**Review:** Two independent adversarial reviewers (correctness attack + resource/ops attack) each broke the first draft. §3A had a **fatal prune flaw**; §3B (2G bound) and §3C (900s timeout) were quantitatively wrong. All findings are dispositioned in §10; §3–§5 below are the corrected design.
**Author:** Kiro (design/review lane)
**Date:** 2026-08-31
**Upstream evidence:** [`CODEX-2026-08-31-kiro-watch-oom-followup-handoff.md`](../inter-model/CODEX-2026-08-31-kiro-watch-oom-followup-handoff.md) · [`KIRO-2026-08-31-watch-oom-fullfile-reindex-design-handoff.md`](../inter-model/KIRO-2026-08-31-watch-oom-fullfile-reindex-design-handoff.md)

---

## 0. Problem statement (consequence first)

`convmem-watch.service` repeatedly OOM-kills its index children. On 2026-08-31 four
kills occurred in ~72 minutes (16:28, 16:36, 17:33, 17:39), each at the child's own
6 GiB cgroup ceiling (`exit -9`), against **actively-changing live files**: `~/.codex/history.jsonl`
and running Cursor agent transcripts. One child lived **51 minutes** (2m49s CPU / 6G peak),
mostly blocked on Ollama round-trips. The repeated 6 GiB-resident children pushed the whole
host into swap (zram 8G full, 20G disk swap used), so the desktop reported system-wide low
memory. The parent watcher survived each kill (the 2026-08-29 subprocess cap did its job),
but affected files were left stale and notifications recurred.

**What must change for the operator:** a one-line append to a watched file must cost
bounded, near-constant work — not a full-file rebuild — and no single index child may live
for tens of minutes or demand unbounded memory.

## 1. Verified root cause (code-grounded, not assumed)

Every claim below was confirmed by reading the current tree at session time.

| # | Mechanism | Evidence |
|---|-----------|----------|
| 1 | Idempotency keyed on **whole-file** hash | `ingest.py:1058` `file_hash = sha256_file(path)`; `ingest.py:474` `if file_hash in processed: skip`. Any appended byte changes the hash → skip never fires. |
| 2 | Every adapter re-parses the **entire** file | All 10 `adapters/*.py` expose `parse(filepath) -> list[dict]`; none accept an offset/cursor. |
| 3 | Whole message list re-chunked + re-modeled every change | `ingest.py:_process_file_chunks` → `chunk_messages(messages, 60, 10)`; per chunk: `summarize` + `ollama_embed` + `_distill_with_provenance`. history.jsonl (2768 lines) ≈ 55 chunks × 3 model calls per append. |
| 4 | Per-unit Chroma query multiplies working set | `ingest_dedupe.evaluate_ingest_batch` → `store.query_units(embedding, candidate_k=10)` per candidate unit across the whole file. |
| 5 | force_file adds two more full passes | watch always uses `force_file` → `_snapshot_reindex_rows` (pre) + `_prune_completed_reindex` (post) over the source's rows. |
| 6 | No per-child timeout | `watch.py:208` `subprocess.run(...)` has **no `timeout=`** → a stuck child (Ollama retries `time.sleep(5/10)` at `ingest.py:745,769`) can live ~51 min. |
| 7 | Child cannot swap | scope sets `MemorySwapMax=0` → child hits 6 GiB anon RAM and dies regardless of host swap. |

**Diagnosis:** peak memory and lifetime are dominated by *quantity of full-file work per change*,
compounded by an unbounded child lifetime. Not a leak; not model residency alone; not a single
oversized allocation.


## 2. Rejected options (with reasons)

| Option | Verdict | Reason |
|--------|---------|--------|
| Increase zram / enable child swap | **Reject** | Child scope is `MemorySwapMax=0` → more swap gives it zero headroom; zram is RAM-not-extra-memory (RAM-negative under real allocation); ledger explicitly rejects "increase swap when workload exceeds RAM". |
| Raise `MemoryMax` above 6G | **Reject as fix** | Moves the ceiling; next larger transcript re-hits it. Legitimate work already reached exactly 6G. |
| Exclude history.jsonl / transcripts | **Reject** | Data loss; forbidden by handoff; next source OOMs anyway. |
| Add spawn concurrency | **Reject** | Loop is intentionally serial (`subprocess.run` blocks). Concurrency multiplies peak memory. |

## 3. Proposed design (three bounded, independent changes)

Each change is independently valuable and independently testable. Together they remove the
OOM class. The whole-file rebuild path **remains the default and the correctness fallback.**

### 3A. Append-aware incremental indexing (removes the recurring cause)

For sources that can *prove* monotonic append, index only the new tail. **The append path
MUST NOT prune** (see §10 Attack-1: pruning on append deletes the entire prior index).

- **State (additive to `processed.json`):** per resolved path, store `indexed_message_count`
  (absolute number of messages already indexed), `indexed_byte_offset` (byte offset of the
  last consumed newline — never mid-line), `indexed_size` (file size at last index), and
  `tail_fingerprint` (sha256 of the ~4 KiB immediately before `indexed_byte_offset`). Absent
  → full rebuild (today's behavior). Backward compatible (extra dict keys; readers ignore).
- **Adapter capability:** per-adapter `supports_append: bool`, **restricted to strictly
  one-JSON-object-per-line formats** (Codex `history.jsonl`, Codex rollout, and JSONL
  transcripts proven append-only). SQLite, markdown, and any rewrite-prone format stay `False`.
- **Change detection (cheap, O(window) not O(filesize)):** append is *provable* iff
  current size ≥ `indexed_size` AND `sha256(bytes[offset-4KiB : offset]) == tail_fingerprint`.
  This is deliberately cheaper than re-hashing the whole prefix (see §10 Attack-4). **Documented
  weakening:** a tail fingerprint cannot detect an interior edit that preserves the last 4 KiB
  before the cursor. §5 restates the edit-detection guarantee accordingly and adds a
  size-anomaly / periodic audit rebuild.
- **Fast path (append proven):**
  1. `snapshot = None` — **do not** call `_snapshot_reindex_rows` / `_prune_completed_reindex`.
     Old chunks are kept as-is; only new units are added. (This is the core correction.)
  2. Parse only `bytes[indexed_byte_offset:]`, stopping at the last complete newline; carry the
     trailing `overlap` messages of the last indexed window by **re-deriving chunks from
     `last_chunk_start` with absolute, rebased offsets** so `make_unit_id` (which hashes
     absolute `start_offset`+`unit_index`) reproduces stable IDs and upserts the seam window
     deterministically instead of colliding at offset 0.
  3. Commit: `store.add_unit` the new/seam units, then advance `indexed_message_count`,
     `indexed_byte_offset`, `indexed_size`, `tail_fingerprint` **in the same transaction** as
     the file-hash commit, under the existing processed-state lock.
- **Fallback to full rebuild (any of):** no capability, size < `indexed_size` (truncation),
  tail fingerprint mismatch (rewrite/interior edit within window), inode change (rotation),
  missing state (first index), parse anomaly, or a periodic audit interval elapsed.

### 3B. Hard per-child work bound — bound *units-in-flight*, not messages/chars

Adversarial review (§10 Attack-1 resource) proved memory is **decoupled from input size**:
successful children of ordinary transcripts already peak 3.4–4.5 GiB, tiny files have spiked to
5.4 GiB, and the embedding model is **not** resident in the child (it lives in the remote Ollama
server; summarize/distill are remote DeepSeek). The real driver is
`ingest_dedupe.evaluate_ingest_batch` accumulating `accepted_rows` — full float embedding
vectors — for the **whole file**, plus an O(n²) in-memory cosine pass and a per-unit Chroma
`query_units`. So a message/char bound is the wrong knob and a 2 GiB cap would OOM files that
succeed today.

- **Correct bound:** cap **resident units-in-flight** — flush `accepted_rows` and per-batch
  embedding vectors to Chroma every `K` accepted units, releasing vector memory between
  batches, within a **single child** (a bounded internal loop — *not* multiple children, which
  re-pay Python/Chroma startup per batch per §10 Attack-3).
- **`K` and the resulting cap are derived from a mandatory profiling step** (§0 precondition
  from the Codex handoff, which the draft skipped): instrument one representative large-file
  index, plot RSS vs units-in-flight, choose `K` so measured peak sits under the target cap.
  The cap value is set from that measurement, not asserted a priori.

### 3C. Bounded child lifetime — fix the retry backoff, not just add a timeout

Adversarial review (§10 Attack-2 resource) showed 900s is a no-op: fast children OOM at 6 GiB
in 90 s–4 min (before 900 s fires), and the 51-minute child was blocked in
`ollama_embed(timeout=300)` × 3 retries with `sleep(5/10)` per chunk. The retry backoff — not
the absence of a timeout — is the true cause of multi-minute-to-51-minute lifetimes.

- Shrink the embed HTTP timeout from 300 s toward ~20–30 s and reduce/curtail the per-chunk
  retry sleeps in `_process_file_chunks` (`ingest.py:745,769`). Healthy children complete
  in ≲65 s wall.
- Add an **outer** `timeout=` to `watch.py:208 subprocess.run` of ~120 s (backstop, chosen
  above healthy completion + margin), not 900 s.
- On child failure (timeout / OOM exit -9 / -15) record a short **per-path cooldown** so the
  watcher does not re-spawn the same expensive child every debounce cycle. This cooldown is
  needed **interim too**, not just fix-era (§6).
- No concurrency added; loop stays serial.

## 4. Memory & swap policy recommendation

- **Keep** the per-child systemd scope (2026-08-29 fix).
- After 3A+3B land, **re-measure** a bounded child's peak, then **lower** the live child cap
  from the current `6G` stopgap back toward `2G`/`1500M`. Cap value change is a Ryan-owned
  operational action, not part of the implementation branch.
- Do **not** raise MemoryMax or enable child swap.

## 5. Correctness contract (the hard part — must all hold)

| Hazard | Required behavior |
|--------|-------------------|
| Truncation | `size < indexed_offset` → full rebuild. |
| Rewrite / edit of indexed prefix | Tail-fingerprint mismatch → full rebuild. **Weakened guarantee (honest):** an interior edit that preserves the last 4 KiB before the cursor is NOT detected by the fingerprint. Mitigated by: full rebuild on any size decrease, inode change, and a periodic audit-rebuild interval. Documented as a known limitation, not a silent guarantee. |
| Rotation (file replaced) | inode change or fingerprint mismatch → full rebuild. |
| Duplicate content across appends | Routed through existing exact/semantic dedupe unchanged; append path adds no new suppression semantics. |
| Crash mid-append | Cursor state advances **only** after durable `commit_processed_index_entry`, under the existing processed-state lock; interrupted child re-processes the same tail. |
| Torn append (half-written final line) | Cursor advances only to the byte offset of the **last complete newline**; a partially-written trailing record is re-read on the next change, never skipped. `supports_append` restricted to strictly one-object-per-line formats. |
| Chunk-boundary overlap | Seam window re-derived from stored `last_chunk_start` with **absolute rebased offsets**, so `make_unit_id` reproduces stable IDs (deterministic upsert), including non-step-aligned partial final windows. |
| Prune on append | **Never.** Append path sets `snapshot=None`; it only adds units, never deletes. Full-rebuild path retains today's snapshot/prune behavior. |
| Non-append format claiming append | Capability is per-adapter and conservative; unknown → `False`. |

## 6. Interim operational relief (Ryan-owned; not implementation)

While the fix is built, to stop live notifications now (in order of preference):
1. `systemctl --user stop convmem-watch.service` — instant, reversible, no data loss; files index later. Safe and sufficient.
2. **Cheapest safe reduction (higher-leverage than a cap change):** shrink the embed HTTP
   timeout (300 s → ~20–30 s) and curtail the retry sleeps. This directly kills the
   multi-minute-to-51-minute hung-child pathology and needs no service/cap change. (Still a
   config/code touch → Ryan-owned; noted here as the best interim lever the review surfaced.)
3. **Do NOT naively drop the live cap to 2G.** Review (§10 Attack-4 resource) + the config.toml
   comment (lines 55–67) show that a low `MemoryMax` with `MemoryHigh` below the working set
   caused the PR #245 uninterruptible cgroup-reclaim hang holding the export flock. If the cap
   is lowered at all, `MemoryHigh` must equal `MemoryMax` (no throttle band) so the child
   fails fast instead of hanging — and even then it will fail files that succeed today.
4. Add a per-path cooldown on child failure (the 90 s debounce + immediate re-spawn is a tight
   loop attacking live files every 90 s). Interim need, not just fix-era.
5. Leave running and accept periodic per-file failures (parent survives; no corruption).

These are operational actions for Ryan. Kiro does not touch the live service or config.
The parent watcher itself peaked only 1.7 GiB over 9h45m — the parent is healthy; the problem
is entirely in the children.

## 7. Design-only vs Cursor-implementable

**Design-only (this doc):** root cause, options, correctness contract, memory policy, test plan.
**Cursor-implementable (needs a separate Ryan Execute grant):** the `processed.json` schema
addition, the append-tail path, the `supports_append` flags, the input bound, and the
timeout/cooldown in `watch.py`. Whole-file rebuild remains default + fallback throughout.

## 8. Test plan (fixtures/monkeypatch only — no real systemd-run/Ollama/Chroma in CI)

1. Append advances cursor: append N lines → only tail chunks built (assert model-call count ∝ tail).
2. Prefix mismatch → full rebuild (no corrupt partial index).
3. Truncation → full rebuild.
4. Crash before commit → cursor not advanced; tail re-processed next run.
5. Overlap boundary: unit spanning last pre-append chunk boundary still produced.
6. Input bound: oversized file processed in bounded batches; no invocation exceeds bound.
7. Timeout: stuck child terminated at `index_timeout_seconds`; parent survives; cooldown set.
8. OOM child cooldown: exit -9 records cooldown; no immediate re-spawn.
9. Dedupe unchanged: identical-content append still routed through existing dedupe.
10. Non-append adapter: SQLite/rewrite format never takes the append path.

## 9. Acceptance criteria

- [ ] Append to an append-only source performs tail-bounded work (verified by call counts).
- [ ] No single index invocation exceeds the input bound (3B) regardless of file size.
- [ ] No index child can exceed `index_timeout_seconds` (3C).
- [ ] All correctness-contract hazards (§5) degrade to full rebuild or safe re-process; zero record loss.
- [ ] Existing dedupe semantics unchanged.
- [ ] Full suite + focused watch/ingest tests green; ruff/pylint clean.
- [ ] No live service/DB/config mutation in the implementation branch.


## 10. Adversarial review dispositions

Two independent reviewers attacked the first draft. A third fact-check stage failed to return
twice (orchestration issue); its critical questions were instead verified directly by Kiro
against the code (`make_unit_id` in `distill.py:125`, `delete_units_for_source` in
`chroma_store.py:494–511`) — findings below are code-confirmed, not reviewer-asserted.

### Correctness attack (append-cursor data integrity)

| # | Attack | Result | Disposition |
|---|--------|--------|-------------|
| C1 | **Prune flaw** — append passes only tail IDs as `keep_ids` while snapshot `candidate_ids` = whole file → `selected = candidate_ids − keep_ids` deletes the **entire prior index** on a one-line append. | **SUCCEEDS — FATAL.** Confirmed: `chroma_store.delete_units_for_source` line 511 `selected = candidate_ids − keep_ids`; old rows survive today only because full reparse reproduces identical `make_unit_id`s. | **Design corrected (§3A):** append path sets `snapshot=None`, never prunes; adds units only. |
| C2 | **Torn append** — cursor advances past a half-written final line → completed record never re-read (silent loss). | SUCCEEDS. | **Corrected (§5):** cursor stops at last complete newline; `supports_append` = one-object-per-line only. |
| C3 | **Overlap seam** — "prepend trailing 10 msgs" under-specified for non-step-aligned partial windows. | SUCCEEDS. | **Corrected (§3A/§5):** re-derive seam from stored `last_chunk_start` with absolute rebased offsets; test non-step-aligned length. |
| C4 | **prefix_hash O(filesize)** per append reintroduces the removed cost. | SUCCEEDS. | **Corrected (§3A):** replaced full-prefix hash with `indexed_size` + 4 KiB `tail_fingerprint` (O(window)); edit-detection weakening honestly restated in §5 with audit-rebuild mitigation. |

### Resource / ops attack (does it still OOM?)

| # | Attack | Result | Disposition |
|---|--------|--------|-------------|
| R1 | **2 GiB input bound infeasible;** model-floor hypothesis. | Model-floor FALSE (embed model is remote Ollama/GPU, not in child; distill/summarize remote DeepSeek). But 2G still infeasible — successful children already peak 3.4–4.5 G; memory decoupled from input size; real driver is `evaluate_ingest_batch` accumulating whole-file embedding vectors + O(n²) cosine + per-unit Chroma query. | **Design corrected (§3B):** bound **units-in-flight** (flush every K units in one child), K derived from a mandatory profiling step; subprocess-per-file model KEPT (reviewer confirmed it's correct). |
| R2 | **900 s timeout is a no-op** — children OOM in 90 s–4 min; 51-min child was blocked in embed retries. | SUCCEEDS. | **Corrected (§3C):** outer timeout ~120 s + shrink embed HTTP timeout 300→~20–30 s + curtail retry sleeps (the true lifetime cause). |
| R3 | **Multiple bounded children re-pay startup.** | SUCCEEDS (Python/Chroma startup, not model reload). | **Corrected (§3B):** single child, bounded internal loop — not multiple children. |
| R4 | **Interim "drop cap to 2G" is unsafe** — PR #245 cgroup-reclaim hang if `MemoryHigh` < working set. | SUCCEEDS. | **Corrected (§6):** removed as default interim; if used, `MemoryHigh==MemoryMax`; preferred interim is shrinking embed timeout + per-path cooldown. |

**Net:** the first draft would have (a) deleted the entire index of any append-only file on the
next append, and (b) set two bounds that don't bound anything. Both classes are corrected above.
The append-never-prunes rule (C1) is the single most important constraint for any implementer.

## 11. Recommended next steps

1. **Ryan (interim, now):** stop the watcher, or apply the embed-timeout/retry reduction + per-path cooldown. (Operational — Kiro will not run it.)
2. **Ryan → Cursor (Execute grant):** implement §3A/§3B/§3C under the §5 correctness contract and §8 test plan, **preceded by the §3B profiling step**. Whole-file rebuild stays default + fallback.
3. **Kiro:** independent exact-tip review of the implementation before merge.
4. **Second adversarial reviewer** (Copilot audit lane or ChatGPT) on the implemented append-cursor before merge — data-loss risk warrants two reviewers, per charter.

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Trapdoor Hunt | Dependability & provenance trust architecture arc (see `config/agent-protocol.md`). |
| watch / watcher | `convmem-watch.service`, the systemd user service that incrementally indexes changed files. |
| index child | The `convmem index --file` subprocess the watcher spawns per changed file, in a memory-capped systemd scope. |
| append-cursor / append-tail | Proposed scheme: index only newly-appended messages instead of re-indexing the whole file. |
| indexed_message_count / indexed_byte_offset | Proposed `processed.json` state: how far into a file has been indexed (message count / last-newline byte). |
| tail_fingerprint | Proposed sha256 of the ~4 KiB before the cursor, used to cheaply detect rewrite vs pure append. |
| prune / _prune_completed_reindex | Post-build step that deletes a source's stale units (`candidate_ids − keep_ids`); must be skipped on append. |
| keep_ids / candidate_ids | Reindex sets: units to retain vs units eligible for deletion in `delete_units_for_source`. |
| make_unit_id | `sha256(source_path \0 start_offset \0 unit_index)` — stable unit id keyed on absolute chunk offset (`distill.py:125`). |
| units-in-flight | Accepted units + their embedding vectors held in memory during one file's ingest; the true memory driver. |
| evaluate_ingest_batch | Ingest-dedup step (`ingest_dedupe.py`) that queries Chroma per unit and holds whole-file vectors. |
| subprocess scope / MemoryMax / MemoryHigh | The systemd `--user --scope` memory caps around each index child (`[watch]` config). |
| exit -9 / -15 | Child killed by SIGKILL (OOM) / SIGTERM in its scope. |
| chunk_size / overlap | Ingest windowing: 60 messages per chunk, 10-message overlap (step 50). |
| Execute grant | Ryan-authorized permission for the implementer lane (Cursor) to write runtime code from a design. |
| Copilot audit lane | Independent safety/isolation review lane in the team charter. |
| PR #245 | The prior watch-OOM subprocess-cap fix; its config comment documents the low-cap cgroup-reclaim hang. |
