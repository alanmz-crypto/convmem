# Arc Brief — Poison Pill (convmem indexer SIGSEGV / Chroma upsert crash)

**Arc codename:** Poison Pill · **Slug:** `chroma-upsert-crash`
**Opened:** 2026-09-20 · **State:** Active — diagnosis re-scoped; execution blocked on a Ryan platform gate

---

## 1. What This Is For (product goal)

convmem's corpus is only trustworthy if ingest is trustworthy. Since 2026-09-18 the indexer has
been dying with SIGSEGV/SIGABRT during Chroma writes, the watcher has been retrying crashing files
indefinitely, and the HNSW index has twice been rebuilt and quarantined. The arc is done when we
know **why** writes crash, the watcher can no longer loop on a crashing input, and the corpus can
be written to again with confidence.

## 2. System Design (how the pieces connect)

`convmem.py index --file <p>` → `ingest.index/_index_impl` (wrapped in `production_writer_boundary`
→ exclusive flock) → `_index_one_file` → `_process_file_chunks` → `build_chunk_artifact`
(summarize + distill + `ollama_embed` per unit) → `commit_chunk_artifact` → `_commit_chunk_to_stores`
→ `ChromaStore.add_summary` (`chroma_store.py:227`) and `add_unit` (`:282`), both `upsert` over
**deterministic, content-addressed ids**, followed by `_prune_completed_reindex`.

The watcher (`watch.py`) spawns one child per file: `<python> convmem.py index --file <path>`, no
`--force`, wrapped in `systemd-run --user --scope -p MemoryMax=12G -p MemorySwapMax=0`. Writers —
ingest, `refine`, `monitor`, `propose_decision`, `conflict_events` — serialize through
`exclusive_writer_lease` (`chroma_write_store.py:502`). Readers (`doctor`, `ask`, the MCP servers)
do not take that lease.

## 3. What Exists Right Now (file map)

| Surface | State |
|---|---|
| `docs/inter-model/KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md` | On this branch (`aaa6eff`). Remediation spec (Part A/B) valid; **root-cause premise superseded** |
| `docs/inter-model/KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` | On this branch. Corrected Phase C′ design + the evidence that superseded the old one |
| `~/.local/share/convmem/chroma.corrupt-2026-09-19` (4.7 G), `…-2026-09-20` (4.5 G) | Quarantined evidence; **forensically examined, structurally sound** |
| Live `~/.local/share/convmem/chroma` | Rebuilt 2026-09-20 04:57; last write 09:53:01; all writers stopped 09:57:02 |
| Poison-pill quarantine / circuit breaker | **Does not exist** — no code written |
| Phase C′ replay harness | **Does not exist** — Cursor's to build, after the gate |
| Replay set + raw reconstruction method | **Verified offline**; specified in the Phase C′ handoff |

## 4. Completion State

- [x] Crash reproduced and characterized (Kiro, 2026-09-20)
- [x] C0 code trace: upsert-not-insert, `ingest.distill` seam, no export→Chroma rebuild path
- [x] Chroma writers stopped; quiet window opened 2026-09-20T09:57:02-05:00
- [x] Read-only forensics on both quarantined indices and the live index
- [x] Experiment redesigned (Phase C′) against the evidence
- [x] Replay fidelity **proven offline**: 3,548/3,548 assertion ids reconstruct from the export
- [x] Replay set identified: the 436 live unit ids, not the 3,548 export rows (~67 generations)
- [ ] **Ryan platform gate** — kernel A/B, memtest86+, quiet verdict
- [ ] Phase C′ execution (Cursor) — blocked on the gate
- [ ] Remediation: per-file quarantine + global crash circuit breaker (Cursor)
- [ ] Ledger corrections to the three `obs_` records (Ryan)

## 5. Your Role (read this to know what you're here to do)

If you are picking this up **before the platform gate clears**: you are not running experiments.
Read § 6, and do only work that does not depend on crash counts.

If the gate has cleared: you are Cursor, and your brief is
`KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md`. Run the id-fidelity preflight before you
count a single run.

Whoever you are: do not restart the watcher, do not open the live Chroma directory with a client,
and do not reintroduce the "poison transcript" framing — it is refuted (§ 6).

## 6. What Remains Before "Live" (sequential)

1. **Platform gate (Ryan).** Kernel A/B against `linux 7.2.4` (in the pacman cache) first; then
   memtest86+ with XMP off; then a quiet verdict — zero non-convmem core dumps under load for a
   duration Ryan sets.
2. **Phase C′ (Cursor).** The 2×2 arms, id-fidelity preflight, crash/hang/clean counted separately,
   every count paired with its background fault count.
3. **Remediation (Cursor).** Per-file quarantine **and** a global circuit breaker; accurate
   crash accounting so `doctor synthesis_gate` stops absorbing native crashes as provider drops.
4. **Ledger correction (Ryan).** Three `obs_` records assert a two-problem split and a
   file-specific cause that the evidence contradicts.

**Hypothesis status:** (a) poison payload — **refuted** (`LATEST.md` and `refine` crash identically).
(b) index size / accumulated state — open; rebuild halves the element count and buys ~2 h.
(c) residual on-disk corruption — **unsupported**; the quarantined indices and the live index at
crash time all validate clean. (d) platform-level memory corruption — **strongly indicated**, untested; the distill survival
curve (67 runs start, 2 finish, deaths spread across all 14 chunks) is independent support.

## 7. Hard Stops (models cannot cross)

- No Phase C′ run before the Ryan platform gate.
- No live-store writes; no Chroma-client open on the live directory; read-only SQLite via backup
  API or `mode=ro` only.
- No watcher restart, no corpus-wide reindex, no external provider calls, no hardware/BIOS action.
- Ledger writes and merges are Ryan's.

## 8. Relationship to ConvMem (the bigger picture)

This arc gates everything that writes: with writers stopped, the corpus is frozen, `brief`/`doctor`
counts go stale, and Track A session indexing is paused. It is adjacent to **Trapdoor Hunt / #268**
(watcher OOM) but distinct — #268 is about memory bounds under load, this is about writes aborting
in the native allocator. Do not merge the two without Ryan's say-so. The platform question also
reaches beyond convmem: `git` took a SIGBUS today, so any repo work on this machine carries risk
until the gate clears.

## 9. Key Design Files (for deep dives)

| What | Path |
|---|---|
| Corrected experiment brief | `docs/inter-model/KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` |
| Original remediation spec | `docs/inter-model/KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md` |
| Crash surface | `chroma_store.py:227`, `:282` |
| Id determinism | `ingest.py:918-922` (`assertion_seed`), `:121-144` (`_uuid4_from_seed`) |
| Writer serialization | `chroma_write_store.py:502-575` |
| Watcher spawn + caps | `watch.py:160`, `:169`, `:203-233`; `config.toml` `[watch]` |

## 10. How to Update This Brief (departure protocol)

Overwrite §§ 3–6 to reflect reality now — move items from "does not exist" to "on branch" to
"on `main`", delete completed checklist items, rewrite § 5 for the next model. Do not append
session narrative; that belongs in Track A. One line in the Update Log. Test: could a fresh model
read only this file and orient itself?

## Update Log

- 2026-09-20 — Claude Opus 5 (Kiro design/plan lane): arc opened. Chroma writers stopped (quiet
  window 09:57:02); read-only forensics found no structural corruption in either quarantined index;
  poison-payload premise refuted; Phase C′ redesigned and blocked on a Ryan platform gate.
