# Execution Plan — Chroma orphan vector repair

```
Planning Status

Phase:        Execute (two independent P0 tracks)
Characters:   Cursor (implement + inventory); DeepSeek Flash (plan critique); Ryan (authorize reconcile)
Lanes:        Cursor — not JudgeBench implementation branch
Authority:    Read-only diagnosis complete 2026-08-07; Ryan authorized plan + DeepSeek delegation
```

**Evidence SSoT:** `/tmp/claude-chroma-raw-20260807T233007Z.json`  
**Diagnosis:** HNSW vector index returns IDs with `document=None`, `metadata=None`; IDs absent from SQLite METADATA segment; `_flatten()` preserves `None` → `rerank.py` crashes.  
**Blocker:** JudgeBench T5 calibration (`eval-synthesis.py --judge --golden /tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl`) fails on fixture `cal_bad_unknown`.  
**Branch:** `plan/2026-08-07-2026-08-07-chroma-orphan-vector-repair`

**Do not touch:**
- `~/.local/share/convmem/worktrees/fix-2026-08-07-judge-bench-judge-upgrades`
- JudgeBench judge-upgrade source, tests, fixtures, or baselines on that branch

---

## Problem summary

| Layer | Finding |
|-------|---------|
| Crash | `ValueError: Unsupported input type: NoneType` at `rerank.py:39–40` |
| Leak point | `chroma_store.py:517–531` `_flatten()` preserves `documents[i] is None` |
| Call sites | `_flatten()` at lines **206** (`query_summaries`), **267** (`query_units` superseded), **276** (`query_units` normal) — grep-verified |
| Storage | ≥11 distinct orphan IDs from 2 of 6 bounded queries; zero overlap between `cal_bad_unknown` (7) and `cal_good_transition` (4) |
| SQLite | Fresh corpus scan: 16,747 `chroma:document` rows, 0 null, 0 empty — not a persisted-null write bug |
| Supersede filter | Ineffective: `metadata=None` → `{}` → `is_superseded` false |

**Radius framing:**
- **Crash radius:** orphans must land in top-20 rerank window.
- **Contamination radius:** orphans appear in most queries tested; passing fixtures are rank-position lucky, not clean retrieval.

---

## Two independent P0 tracks (not sequenced)

### P0-A — Read-side guard (greenlight without inventory)

**Goal:** Stop `None` documents from reaching any `_flatten()` consumer.

**Change:** In `ChromaStore._flatten()`, **skip** rows matching the orphan signature: `documents[i] is None and metadatas[i] is None`. Do **not** coalesce `None → ""` (would admit unrankable ghosts into rerank slots). Do **not** skip rows where metadata is present but document is absent (embedding-only edge case).

**Flash critique (2026-08-07):** verify `query_summaries()` semantics before applying the same rule to the summaries collection.

**Tests:**
- Unit test: synthetic Chroma response with mixed valid + `None` documents → `_flatten` returns only valid rows.
- Regression: `cal_bad_unknown` path no longer raises through `query_units` → rerank (may use mocked rerank or integration with identity rerank mode if configured).

**Done when:** pytest passes; `ask()` on `cal_bad_unknown` question completes without `NoneType` rerank crash.

**Does not require:** orphan inventory count, reconcile/reindex, or JudgeBench branch changes.

---

### P0-B — Bounded orphan inventory (read-only; before reconcile design)

**Goal:** Size HNSW-vs-METADATA drift to choose targeted evict vs full rebuild.

**Method (read-only; evidence under `/tmp` only):**

1. **METADATA ID set** — `chroma_readonly.collection_ids(chroma_dir, UNITS)`.
2. **Query-surfaced orphans** — union of `none_ids` from:
   - All 5 JudgeBench calibration fixture questions
   - Negative control from diagnosis (`convmem doctor` question)
   - 3–5 additional diverse probes (inter-model, ledger, WordPress, abstain-style)
   - **Must use** `open_chroma_for_verify` → `collection.query()` directly — **never** `query_units()` / `ask` / post-`_flatten()` paths (P0-B data must not depend on P0-A guard)
   - Include ≥1 probe with `n_results ≥ collection.count() + slack` to enumerate HNSW entries beyond top-20
3. **Diff (bidirectional)** — query/HNSW ID set − METADATA IDs (orphans); METADATA IDs − query-enumerated set (metadata-without-vector, if any)
4. **Per-ID SQLite** — for each diff ID: `row_found: bool`, `chroma:document` presence, `superseded`, `deleted`, JSONL lookup if historical.
5. **Artifact** — `/tmp/chroma-orphan-inventory-<timestamp>.json` with explicit `row_found` flags (fix prior evidence schema gap).

**Ceiling:** If union exceeds 500 IDs, report count + sample + source-path families; note whether full vector-segment enumeration is needed as follow-up.

**Done when:** artifact written; report states total distinct orphans, overlap across queries, and reconcile recommendation tier:

| Tier | Orphan profile | Likely reconcile |
|------|----------------|------------------|
| S | ≤50, one source family (e.g. Kiro snapshot purge) | Targeted evict / complete purge metadata cleanup |
| M | 50–500, multiple families | Partial reindex or segment compaction arc |
| L | >500 or widespread | Full `knowledge_units` collection rebuild |

**Does not require:** P0-A guard to be merged first (can run in parallel).

**Does not authorize:** `convmem index` full corpus, `rm processed.json`, DB mutation, or reconcile execution — Ryan lock after inventory.

---

## Out of scope (this arc)

- JudgeBench judge model / prompt upgrades (`fix-2026-08-07-judge-bench-judge-upgrades`)
- Reconcile/reindex execution (blocked on P0-B + Ryan lock)
- `doctor._check_embed_collection_identity` changes (different failure mode)
- Modifying `/tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl`

---

## Task order

| ID | Track | Work | Owner | Done when |
|----|-------|------|-------|-----------|
| T1 | Both | This EXECUTION plan + DeepSeek Flash critique | Cursor → DeepSeek | Plan filed; critique received |
| T2 | P0-A | `_flatten()` null-document skip + unit test | Cursor | pytest PASS |
| T3 | P0-A | Integration: `cal_bad_unknown` ask path no crash | Cursor | manual or test PASS |
| T4 | P0-B | Read-only inventory script or ad hoc pass | Cursor | `/tmp/chroma-orphan-inventory-*.json` |
| T5 | P0-B | Inventory summary + reconcile tier recommendation | Cursor | written in handoff |
| T6 | Gate | JudgeBench T5 calibration re-run | Ryan/Cursor | `eval-synthesis.py --judge --golden …` completes |
| T7 | Future | Reconcile/reindex (separate arc) | Ryan lock | after T4 tier known |

T2–T4 are **parallel** — neither blocks the other.

**Independence constraint (Flash critique):** P0-A implementation and P0-B inventory **work** can proceed in parallel, but P0-B **data collection** must use pre-`_flatten()` raw Chroma query capture and must not assume P0-A is already deployed.

**Critique:** [`docs/inter-model/DEEPSEEK-FLASH-2026-08-07-chroma-orphan-plan-critique.md`](../inter-model/DEEPSEEK-FLASH-2026-08-07-chroma-orphan-plan-critique.md) — **APPROVE WITH CHANGES**

---

## Verification

```bash
cd ~/Projects/convmem

# P0-A
python -m pytest tests/test_chroma_flatten.py -q   # new or extended
python -c "
from ask import ask
ask('What is the exact production launch date of the fictional Moonbeam integration, according to ConvMem?', top_k=6, evidence=False)
print('OK: no rerank NoneType crash')
"

# P0-B (read-only)
# Run inventory pass; inspect /tmp/chroma-orphan-inventory-*.json

# T6 gate (after P0-A)
python scripts/eval-synthesis.py --judge --golden /tmp/CODEX-2026-08-07-judge-bench-calibration.jsonl
```

---

## Sign-off

**Mechanical:** Cursor fills tasks T2–T5; T6 proves T5 calibration unblocked.  
**Ryan:** authorize reconcile arc only after P0-B tier report.  
**DeepSeek Flash:** adversarial plan critique (T1) — risks, gaps, inventory methodology.
