# Implementation Handoff: Fix convmem indexer Chroma-upsert SIGSEGV (poison-pill + upsert isolation)

**Date:** 2026-09-20 (updated after two post-XMP-off crashes confirmed a distinct software bug)
**Author:** Kiro (diagnosis / root-cause; review-required lane — cannot implement in convmem prod)
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-09-20 (verbal: "let's work on a fix", delegated to Cursor). Kiro cannot edit convmem prod code per lane rules.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | create `fix/2026-09-20-chroma-upsert-poison-pill` |
| **Push status** | n/a (Kiro wrote no code) |
| **PR** | not opened |
| **Ryan GATE** | none for implementation; Ryan reviews PR before merge |
| **Related ledger** | `obs_a09dbfa9e237` (two-problem separation), `obs_e8db779df8c3` + `obs_c1499a660d4f` (Chroma root cause) |

---

## Critical context: this is ONE of TWO problems (do not conflate)

Today had a tangled incident. It has been separated:

1. **Hardware/XMP instability (NOT this task).** Caused hard lockups + system-wide corruption
   (udevadm-as-root SIGABRT, git SIGBUS, Chrome). Ryan disabled XMP on the i7-13700K /
   Z790 board; appears fixed (48min+ uptime, no lockup/multi-program corruption). Confirm
   separately with memtest86+ (XMP off). **Do not chase this in code.**

2. **convmem/Chroma indexer software bug (THIS task).** Independent of XMP. Deterministic,
   file-specific SIGSEGV in the Chroma Rust HNSW upsert path. This is what keeps spamming
   "python crashed again."

---

## Root cause (reproduced, grounded)

- Indexer children SIGSEGV/abort during ingest. faulthandler traceback:
  `munmap_chunk(): invalid pointer` at `chromadb/api/rust.py:541 _upsert` <-
  `chroma_store.py:227 add_summary`. Kernel: `segfault ... in chromadb_rust_bindings.abi3.so`.
- Env: `chromadb 1.5.9`, `python 3.11.15`.
- **Not a blanket Chroma break:** fresh `PersistentClient` upserts fine (incl. 2 MB doc; 1200
  real-payload replays). Crash reproduces via the real indexer against the **live/large HNSW index**.
- **Poison transcript:** `~/.codex/sessions/2026/09/17/rollout-2026-09-17T23-18-39-01a0b2bc-e7cc-7a53-94b6-676fdfc966f0.jsonl`
  (40 MB, 13 chunks). Crashes reproducibly; also hangs sometimes.
- **Re-corruption loop:** rebuilding the HNSW from clean SQLite fixes it temporarily, but ~2h of
  normal indexing re-corrupts it — because the watcher **retries the crashing file forever**
  (no skiplist), and each crashed upsert can corrupt the shared on-disk HNSW.
- SQLite metadata stays clean (`integrity_check: ok`) — corruption is in the HNSW segment files.

---

## Integration points (exact)

- **Watcher error handler — `watch.py:463`** (`print(f"[watch] error processing {path}: {e}")`).
  The subprocess raise is at `watch.py:252` (`RuntimeError(... index subprocess exit {returncode})`,
  returncode `-11` = SIGSEGV). Poison-pill logic goes in this handler.
- **Upsert call sites — `chroma_store.py:227` (`add_summary`) and `chroma_store.py:282` (`add_unit`).**
  Both do a plain `self._collection(...).upsert(...)`. This is the native crash surface.
- Watcher already subprocess-isolates *indexing* (parent survives) — good; the gap is retry policy
  and upsert-level containment.

---

## Specification

### Part A — Poison-pill skiplist (stops the loop + re-corruption) — REQUIRED, highest value
- Track per-file consecutive hard-crash count (SIGSEGV/`returncode < 0`, and timeouts) keyed by
  path + content hash, persisted (e.g. under `~/.local/share/convmem/watch-quarantine.json`).
- When a file crashes the indexer **N times (default 2)**, **quarantine** it: stop re-spawning it,
  log `[watch] quarantined (repeated crash): <name>`, and surface it (count in doctor, or an
  `unresolved`/observation) so it is visible, not silently dropped.
- Provide a way to clear quarantine (CLI flag or deleting the state file) after a fix.

### Part B — Upsert containment (stops index corruption) — REQUIRED
- Ensure a native crash in `_upsert` cannot corrupt the shared HNSW. Options (choose per testing):
  - Run the Chroma write in a short-lived worker/subprocess so a crash is contained; on crash,
    mark the file degraded with the **real reason** (native crash), not "provider drop".
  - And/or add bounded retry with fresh client, and verify index integrity after batches.

### Part C — Investigate the poison transcript — REQUIRED (diagnosis, may inform B)
- Determine what about `rollout-2026-09-17T23-18-39` triggers the Rust upsert crash on a large
  index (chunk 13 accumulation? a specific metadata/embedding shape? index size threshold?).
- If a Chroma version tolerates it, pin `chromadb` explicitly (currently unpinned in the repo).

### Output / contract
- Watcher never enters an infinite crash-retry loop on one file.
- A poison file is quarantined + visible, not silently lost and not re-corrupting the index.
- Degraded/crash counts are attributed accurately (distinct from network provider drops) so
  `doctor synthesis_gate`'s "ingest-degraded" number stops absorbing native crashes silently.

---

## What NOT to build
- Do NOT "sanitize payloads" as the fix — payloads are well-formed; not the cause.
- Do NOT touch XMP/BIOS/hardware — that is problem (1), out of scope here.
- Do NOT disable the watcher permanently or delete transcripts.
- No corpus-wide re-index without Ryan authorization + a DB backup (restic gate covers today).

---

## Reproduction harness (already built by Kiro — reuse)
- Point the indexer at an isolated copy via a scratch config:
  `CONVMEM_CONFIG=<scratch>.toml` with `chroma_dir` set to a copy — the real indexer crashes on
  the copy, so you can iterate a fix with zero risk to the live store. (Kiro used `/tmp/chroma-bisect`.)
- HNSW rebuild-from-SQLite script proven working: rebuild into a new dir, swap. ~54s for 80k units.

---

## Test expectations
1. **Repro before:** indexing the poison transcript SIGSEGVs / hangs on baseline.
2. **Poison-pill:** after N crashes, file is quarantined; watcher continues other files; no loop.
3. **Containment:** a simulated upsert crash does not corrupt the shared index (integrity check passes after).
4. **Regression:** normal small transcripts index fine; existing suite green.
5. **Accounting:** residual failures increment an explicit native-crash/quarantine counter.

---

## Acceptance criteria
- [ ] Watcher cannot infinite-retry a crashing file (poison-pill quarantine after N).
- [ ] Native upsert crash cannot corrupt the shared HNSW (contained).
- [ ] Poison transcript investigated; `chromadb` pinned in manifest.
- [ ] No regression; Ruff/pylint clean.
- [ ] doctor no longer silently absorbs these as generic ingest-degraded.

---

## Related files

| What | Path |
|------|------|
| Watcher retry/error handler | `watch.py:463` (raise at `:252`) |
| Upsert call sites | `chroma_store.py:227` (`add_summary`), `:282` (`add_unit`) |
| Root-cause observations | `obs_a09dbfa9e237`, `obs_e8db779df8c3`, `obs_c1499a660d4f` |
| Poison input | `~/.codex/sessions/2026/09/17/rollout-2026-09-17T23-18-39-01a0b2bc-e7cc-7a53-94b6-676fdfc966f0.jsonl` |

---

## Leaving / picking up checklist

**Author (Kiro, leaving):**
- [x] Root cause reproduced + recorded (`obs_a09dbfa9e237` and prior)
- [x] Two-problem separation documented
- [x] This handoff written with exact integration points
- [x] Watcher STOPPED to halt the re-corruption loop (Ryan: restart with `systemctl --user start convmem-watch` after fix)
- [ ] LATEST.md bullet — add on the fix branch (current branch is unrelated #263 work)

**Implementer (Cursor, picking up):**
- [ ] Read this file before first edit
- [ ] `convmem work start fix chroma-upsert-poison-pill`
- [ ] Reproduce on an isolated copy (harness above), implement A+B+C, verify against poison transcript
