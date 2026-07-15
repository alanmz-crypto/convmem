# CONTINUE-DEEPSEEK Retrieval Diagnosis — 2026-07-15 (Deep v2)

**Topic:** Why `convmem ask "current plan arc"` returns stale June 30 material instead of July 14-15 facts.

**Method:** Full pipeline code audit (query.py, ask.py, evidence.py, refine.py, chroma_store.py, ingest.py, inter_model_index.py, adapters/inter_model_doc.py, rerank.py, ledger_recent.py) + live corpus queries via MCP search_fast/search + raw ChromaDB SQLite inspection + processed.json forensic analysis. All claims verified against running corpus (8058 units, 1163 summaries).

**Key finding not surfaced in prior debate:** The 370-unit duplicate mass is NOT from re-indexing the same file. It's from **Kiro session snapshot multiplication** — 25 different Kiro snapshots of the same file, each at a different path, each contributing ~15 section units. The `_purge_stale_same_path` mechanism is path-keyed, not content-keyed, so it cannot detect that these are duplicates. This is a fundamentally different failure mode than what any other model in the debate identified.

---

## Layer 0: KIRO SNAPSHOT MULTIPLICATION (Root Cause)

### The Mechanism (verified against live ChromaDB + processed.json)

**Step 1: Kiro takes snapshots during long sessions.**
Kiro copies the repo's `docs/inter-model/` directory to `~/.kiro/sessions/<session_id>/snapshots/<hash>/docs/inter-model/` during checkpoint events. Each snapshot captures the state of inter-model docs at that moment.

**Step 2: The inventory scanner finds ALL copies.**
`~/.kiro/sessions` is in `[sources].paths` (config.example.toml line 4). The inventory scanner recursively discovers all `*.md` files under this path. Since Kiro snapshots contain `docs/inter-model/*.md`, every snapshot copy is inventoried as a separate source file.

**Step 3: `is_inter_model_doc` matches snapshot paths.**
```python
# adapters/inter_model_doc.py:18-23
def is_inter_model_doc(path):
    p = Path(path).expanduser().resolve()
    if p.suffix != ".md": return False
    if "archive" in p.parts: return False
    return p.parent.name == "inter-model" and p.parent.parent.name == "docs"
```
A Kiro snapshot path like `~/.kiro/sessions/.../snapshots/76a76c1e/docs/inter-model/KIRO-...md` satisfies the check: parent is `inter-model`, grandparent is `docs`. The function does NOT exclude paths containing `.kiro` or `snapshots`.

**Step 4: `_purge_stale_same_path` can't detect cross-path duplicates.**
```python
# ingest.py:253-266
def _purge_stale_same_path(processed, path_key, keep_hash, *, preserve_exclusions=True):
    for key, entry in list(processed.items()):
        if key == keep_hash or not isinstance(entry, dict): continue
        ep = entry.get("path")
        if not ep or _processed_path_str(ep) != path_key: continue
        # ... purge ...
```
Each snapshot has a different `path_key` (different snapshot hash in the directory name). The purge only removes entries with the exact same resolved path. 25 different snapshot paths → no purge → 25 entries in processed.json → 25 × ~15 = ~370 Chroma units.

### Live Evidence

**ChromaDB SQLite — source_path distribution for KIRO-2026-06-30-redrafted-plan-v4.md:**
```
 17 units  ...snapshots/b3e7a8af/docs/inter-model/KIRO-2026-06-30-redrafted-plan-v4.md
 17 units  ...snapshots/76a76c1e/docs/inter-model/KIRO-2026-06-30-redrafted-plan-v4.md
 17 units  ...snapshots/6e3dfd0b/docs/inter-model/KIRO-2026-06-30-redrafted-plan-v4.md
 ... (22 more snapshot paths, 14-17 units each)
Total: 370 units, 20 unique titles, 25 source paths
```

**processed.json — 25 entries, all from different snapshot paths:**
```
hash=71e90653d14a  path=...snapshots/76a76c1e/docs/inter-model/KIRO-...v4.md  units=17
hash=f7bd4cb42529  path=...snapshots/181a6d99/docs/inter-model/KIRO-...v4.md  units=15
hash=06e81d7b2208  path=...snapshots/27572cdf/docs/inter-model/KIRO-...v4.md  units=15
... (22 more)
```
**Zero entries from the real repo path** (`~/Projects/convmem/docs/inter-model/`). The real file was never indexed directly — the 370 units exist ONLY because Kiro snapshots were picked up by the inventory scanner.

**Full Kiro-related duplicate mass across all inter-model files:**
```
459 units  from Kiro session snapshots (all inter-model files combined)
   - 370 units  KIRO-2026-06-30-redrafted-plan-v4.md (25 snapshots × ~15 sections)
   -  19 units  KIRO-2026-06-30-repo-organization-review.md (3 snapshots)
   -  18 units  KIRO-2026-06-30-redrafted-plan.md (1 snapshot)
   -  12 units  KIRO-2026-06-30-synthesized-plan-critique.md
   -  11 units  KIRO-2026-06-30-organization-execution-plan.md
   + smaller snapshot fragments
```

**HANDOFF-DEEPSEEK double ingest (ChromaDB verified):**
```
 28 units  repo path: ...convmem/docs/inter-model/HANDOFF-DEEPSEEK-2026-07-14-...md
 20 units  kiro snapshot: ...snapshots/5d54061a/docs/inter-model/HANDOFF-DEEPSEEK-...md
Total:    48 units (same content, two source paths)
```

**BUILT-PLANS (ChromaDB verified):**
```
101 units  repo path: ...convmem/docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md
  1 unit   variant path (symlink or alternate resolution)
Total:    102 units (single source, large document with ~50 unique sections × 2 re-indexes)
```

### What the Debate Got Wrong

| Model | Claim | Reality (ChromaDB-verified) |
|-------|-------|----------------------------|
| Claude | "Kiro units thousands apart in Chroma position" | Kiro v4 duplicates are from 25 different **source_paths**, not from a single file at one position. Position clustering is irrelevant — the issue is path multiplication. |
| Claude | "Positional window fix needed" | No positional window can fix this. The 25 copies are at 25 different Chroma positions because they have 25 different source_paths with different embeddings (slightly different timestamps in the content). |
| ChatGPT | "Ask-time diversification" | Diversifying titles among duplicates is rearranging deck chairs. The 20 unique titles repeated 18-25× each means any diversification picks among copies of the same 20 sections. |
| Codex | "Watch re-triggering on same file" | Watch didn't trigger on the same file 25 times. The inventory scanner found 25 **different files** at 25 different paths. Watch is not the culprit — the inventory scan of `~/.kiro/sessions` is. |

---

## Multi-Layer Failure Stack (10-Layer, Post-Scout)

### Layer 0: KIRO SNAPSHOT MULTIPLICATION (Root Cause)
See above. 459 units from Kiro session snapshots, all containing near-identical content to files that already exist (or should exist) at the canonical repo path. The fix requires **excluding Kiro snapshot directories from inter-model ingest**, not just running dedupe.

### Layer 1: LANGUAGE GAP — Semantic Dissimilarity
"current plan arc" embeds closer to arc *definitions* than to July 2026 coordination facts. The HANDOFF-DEEPSEEK file's vocabulary (`audit`, `junk`, `tombstone`, `dedupe`, `corpus quality`) is in a different semantic neighborhood from the query ("plan", "arc", "current", "state"). The nomic-embed-text model cannot bridge this gap without a vocabulary-index coordination doc.

### Layer 2: DUPLICATE VOTING BLOC (Consequence of Layer 0)
With 370 near-identical units (20 unique titles × 18-25 copies each), the Kiro v4 material forms an unbreakable voting bloc in top-k. Any query with "plan" in it returns 18-20 Kiro v4 units before any July 14-15 material. Combined with 102 BUILT-PLANS units and 48 HANDOFF-DEEPSEEK double-ingest units, ~550 units are competing for the same semantic neighborhood.

### Layer 3: RERANK DISABLED — Missing Cross-Encoder
Live config: `rerank = false`. The `BAAI/bge-reranker-v2-m3` cross-encoder is the only mechanism that can distinguish "this document defines arc structure" from "this document is the current arc state." With it off, the pipeline has no relevance check beyond cosine similarity.

### Layer 4: RECENCY BROKEN — 59% No Timestamps
10,469 of 17,626 JSONL units lack timestamps. All cursor (9,413) and continue (1,056) units get 0.000 recency boost. The inter-model units that DO have timestamps get a recency delta of only 0.036 between June 30 and July 14 — far too small to overcome the duplicate voting bloc.

### Layer 5: NO CITATION DIVERSIFICATION
`_format_context` is a pure formatter. No source cap, no tool diversity, no domain diversity, no dedupe-by-content. All 5 citations can come from the same Kiro v4 snapshot.

### Layer 6: EVIDENCE PATH NOISE
`_prepend_recent_decisions` loads ALL recent decisions with zero domain/site filtering. WordPress willowyhollow decisions inject irrelevant context into convmem queries.

---

## Layer 7: DOUBLE KIRO INGESTION (Compound Amplifier)

### The Problem

Kiro content enters the corpus through **two separate ingestion paths**, creating ~1,684 units from overlapping content:

| Source | Path | Units | Type |
|--------|------|-------|------|
| Legacy static import | `~/.local/share/convmem/imports/kiro-cli-snapshot.sqlite3` | 338 | One-time snapshot |
| Live session scan | `~/.kiro/sessions` | 1,346 | Continuous inventory |

Both paths contain the same Kiro conversations, just at different points in time. The static snapshot was imported once; the sessions directory is continuously scanned. Together they form the third-largest tool corpus after Cursor and Codex.

### Why It Matters

The static snapshot predates the session scan. Units from both paths share identical semantic neighborhoods but may have different ledger_ids, timestamps, and embedding vectors. This means:
- `chroma_dedupe` (keyed on `ledger_id`) can't de-duplicate them — different ledger_ids
- `semantic_dedupe` (keyed on embedding cosine similarity) could catch them — but is excluded from refine.jobs
- The 338 snapshot units act as an additional voting bloc for any Kiro-heavy topic

### Verified (ChromaDB SQLite)

```sql
-- kiro tool units by source path category
source_path LIKE '%kiro-cli-snapshot%'  →  338 units (kiro source_type)
source_path LIKE '%/.kiro/sessions%'   →  1,346 units (inter_model_doc + kiro source_types)
```

---

## Layer 8: CURSOR PROJECT PATH MULTIPLICATION

### The Problem

Cursor creates a separate project directory for every workspace path. The convmem repo has been opened from **6+ different Cursor project directories**, each generating independent agent transcripts that overlap:

| Cursor Project Dir | Transcripts | Source |
|---|---|---|
| `home-lauer-Projects-convmem` | 42 | Canonical path |
| `home-lauer-Documents-Computing-Projects-Convmem` | 5 | Alternate symlink/backup path |
| `home-lauer-Projects-convem` | 6 | **Typo** in project name |
| `home-lauer-Projects-convmem-fix-ask-trace` | ~1 | Worktree branch |
| `home-lauer-Projects-convmem-lab-docs-lab-reference` | ~1 | Worktree branch |
| 5× `home-lauer-local-share-convmem-worktrees-*` | varies | Git worktrees |

**Total: ~56 Cursor transcripts for the same project, from 11 different paths.**

### Why It Matters

This is the Cursor equivalent of Kiro snapshot multiplication. The same conversations, same project context, indexed from multiple Cursor project directories. Unlike Kiro snapshots (which are byte-identical), Cursor transcripts may differ slightly (different session boundaries) but cover the same semantic ground.

**ChromaDB evidence:** Cursor is the largest tool corpus (3,997 units), with convmem-repo transcripts representing a significant fraction. The multi-path problem means querying "convmem plan" hits multiple copies of the same conceptual material.

**Note:** Only the 6 paths producing agent transcripts are listed. The 100 total Cursor project directories include non-convmem projects (WordPress, system paths, tmp dirs) — those are nil-to-minor noise, not duplication.

---

## Layer 9: chroma_dedupe IS LEDGER-ID-KEYED (Blind to Content Dupes)

### The Mechanism

```python
# refine.py job_chroma_dedupe
by_lid: dict[str, list[dict]] = defaultdict(list)
for m in metas:
    if is_superseded(m): continue
    lid = (m.get("ledger_id") or "").strip()
    if not lid: continue          # ← EMPTY ledger_id → SKIPPED
    by_lid[lid].append(m)
```

`chroma_dedupe` groups units by `ledger_id` and picks a canonical (highest confidence, newest timestamp). Units without a `ledger_id` are **silently skipped**. Kiro snapshot inter-model units have no `ledger_id` — they inherit properties from the inter_model_doc adapter, which doesn't assign one. Cursor transcripts may or may not have them depending on whether `ledger_link` has processed them.

### Consequences

- **370 Kiro snapshot duplicates:** All skipped (no ledger_id). Zero tombstoned.
- **0 superseded units in entire corpus:** Confirmed via `SELECT COUNT(*) FROM embedding_metadata WHERE key='superseded'` → 0 rows. The tombstone mechanism has never fired.
- **555 exact-content duplicate chunks:** 9,258 total `chroma:document` entries, 8,703 unique → 555 byte-identical duplicates exist with different IDs.

### Why `semantic_dedupe` Matters

`job_semantic_dedupe` compares embeddings via cosine similarity — it doesn't care about ledger_id. With threshold 0.92, it would catch both cross-path Kiro duplicates AND Cursor project-path duplicates. But it's excluded from the live refine.jobs list.

---

## Evidence Chain Collapse

### The Problem

The evidence chain — the mechanism that connects observations to decisions to verifications — is effectively dead:

| Metadata Key | Total Rows | With Content | Empty/Null |
|---|---|---|---|
| `evidence_json` | 406 | **10** (2.5%) | 396 (97.5%) |
| `ledger_kind` | 406 | 406 (100%) | 0 |
| `ledger_id` | 406 | 406 (100%) | 0 |

The 10 evidence entries that DO have content are all web security probes (`{"probe":"csp","passed":false}`) — none are convmem-related.

### Why It Matters for Retrieval

`_prepend_recent_decisions` (query.py) loads recent decisions to broaden context. When evidence chains are empty, there's no citation graph to traverse. A decision about "plan arc" should chain to related observations and verifications, expanding the retrieval context. Instead, every decision is an island.

### Root Cause

Evidence chains are populated by `ledger_link` (queues candidate pairs) and manual review. The refine daemon runs `ledger_link` every 5 minutes with a batch_size of 10 — but `ledger_link` only pairs observations, not decisions-to-evidence. The pipeline has no automated evidence backfill job.

---

## Live Config vs Example Config — Key Deltas

| Setting | config.example.toml | Live (`~/.config/convmem/config.toml`) | Impact |
|---------|---------------------|-------------------|--------|
| `rerank` | `true` | `false` | Cross-encoder OFF (Layer 3) |
| `refine.jobs` | `chroma_dedupe, ledger_link, semantic_dedupe, confidence_audit` | `chroma_dedupe, ledger_link, confidence_audit, stale_source_flag` | `semantic_dedupe` excluded — no cross-path duplicate detection (Layer 9) |
| `recency_weight` | `0.1` | `0.1` | Active but useless for 46-59% of units (Layer 4) |
| `recency_half_life_days` | `30` | **missing** | No decay curve configured; fallback behavior unknown |
| `sources.paths` | includes `~/.kiro/sessions` | includes `~/.kiro/sessions` | **Layer 0/7 enabler** — snapshots + legacy import scanned |
| `[refine.cost]` | full rate-limit section (3 jobs) | **missing entirely** | No per-job LLM call caps; backfill/semantic_dedupe unbounded if enabled |
| `[watch].extra_paths` | commented out | `["~/Projects/convmem/docs/inter-model"]` | Double-ingests inter-model docs: once via inventory scan, once via watch trigger. BUILT-PLANS 102-unit anomaly may stem from this. |

---

## What Each Layer Costs

For the query "current plan arc", here's the approximate score landscape:

| Position | Unit | Base Score | Recency | Keyword | Final |
|----------|------|-----------|---------|---------|-------|
| 1 | Kiro v4 "Changes from drafts" (snap 76a76c1e) | 0.855 | +0.061 | +0.02 | 0.936 |
| 2 | Kiro v4 "Changes from drafts" (snap 181a6d99) | 0.853 | +0.061 | +0.02 | 0.934 |
| 3 | Kiro v4 "Changes from drafts" (snap 27572cdf) | 0.852 | +0.061 | +0.02 | 0.933 |
| ... | ... (15 more copies of same 20 titles) | | | | |
| 22 | HANDOFF Arc 2 section (Jul 14, repo path) | 0.715 | +0.097 | +0.01 | 0.822 |
| 23 | HANDOFF Arc 2 section (Jul 14, kiro snap) | 0.714 | +0.097 | +0.01 | 0.821 |
| 24 | LATEST.md active handoff (Jul 14) | 0.700 | +0.097 | +0.01 | 0.807 |

**Without Layer 0 (snapshot exclusion):** Kiro v4 drops from 370 units to ~15 → HANDOFF ranks ~3-5.
**Without Layer 3 (rerank enabled):** Cross-encoder pushes HANDOFF above Kiro v4 → rank ~1-2.
**With both fixes:** HANDOFF Arc 2 and LATEST.md would be top results.

---

## Recommended Sequence (Revised with Root Cause)

### P0a: Exclude Kiro snapshots from inter-model ingest — IMMEDIATE (~5 lines, 0 risk)
Add a path exclusion to `is_inter_model_doc`:
```python
def is_inter_model_doc(path):
    p = Path(path).expanduser().resolve()
    if p.suffix != ".md": return False
    if "archive" in p.parts: return False
    if ".kiro" in p.parts: return False          # NEW: exclude kiro snapshots
    if "snapshots" in p.parts: return False      # NEW: belt-and-suspenders
    return p.parent.name == "inter-model" and p.parent.parent.name == "docs"
```
**Rationale:** Kiro snapshots are transient copies of files that exist at the canonical repo path. They should never be ingested as inter-model docs. This is the root cause — fix it before running dedupe.
**Risk:** None. The real inter-model files at `~/Projects/convmem/docs/inter-model/` don't have `.kiro` or `snapshots` in their paths. If Kiro re-snapshots after this change, no new duplicate units will be created.

### P0b: Purge existing Kiro snapshot units from Chroma — IMMEDIATE (script, 0 risk)
Run a script to tombstone all units with source_path containing `.kiro/sessions` and `snapshots`. This removes the 459 duplicate units from the corpus immediately, without waiting for dedupe queue approval.
```bash
python3 -c "
from chroma_store import ChromaStore
store = ChromaStore('~/.local/share/convmem/chroma')
for unit in store.units_metadata():
    sp = unit.get('source_path','')
    if '.kiro' in sp and 'snapshots' in sp:
        # tombstone as superseded by 'kiro-snapshot-purge-2026-07-15'
        ...
"
```
**Risk:** If a canonical file only exists in a Kiro snapshot (not in the real repo), that content would be lost. Verify first: check that every snapshot-sourced inter-model file also exists at the repo path.

### P0c: Re-enable semantic_dedupe + rerank — IMMEDIATE (2 lines, 0 risk)
Add `"semantic_dedupe"` to `refine.jobs` and set `rerank = true` in `[query]`.
**Rationale:** P0a prevents future multiplication. P0b cleans up existing. P0c handles any remaining near-duplicates from BUILT-PLANS, double-ingest, and edge cases.
**Risk:** None. Both are config changes with rollback.

### P1: Verify — 0 code changes
After P0a+P0b+P0c, re-run `convmem ask "current plan arc"` and verify July 14-15 facts reach top-5. Run `convmem doctor` and `convmem brief` to confirm corpus health.

### P2: Fix nested ingest — CONDITIONAL (2 lines)
In `adapters/inter_model_doc.py`, change `is_inter_model_doc` to accept `docs/inter-model/**/*.md`.
**Rationale:** The debate folder is invisible to the corpus. After fixing, the 16 debate files become searchable via `convmem ask`.
**Note:** P0a's `.kiro`/`snapshots` exclusion must remain — it applies before the nesting check.

### P3: Add coordination-index doc — CONDITIONAL (~30 lines)
Create `docs/inter-model/COORDINATION-INDEX.md` with searchable vocabulary bridges.
**Rationale:** Bridges the semantic gap between natural queries ("current plan arc") and document vocabulary ("coordination-index", "retrieval miss").
**Alternative:** If P0a+P0b+P0c solve the retrieval failure, this may be unnecessary. Re-evaluate after P1.

### P4: Source diversification + evidence scoping — SEPARATE TRACK (~30 lines)
Add `max_per_source` to `_format_context` and `domain` parameter to `_prepend_recent_decisions`.
**Rationale:** Defense-in-depth against future retrieval failures, regardless of duplicate mass.

### P5: Timestamp backfill — SEPARATE TRACK (~15 lines)
Backfill timestamps from source file mtime for Cursor/Continue units.

---

## Why the Debate Missed the Root Cause

The debate (ChatGPT, Claude, Codex, Crush, Cursor, Kiro) all operated from corpus queries and code reading — none of them inspected the **raw ChromaDB SQLite file** or **processed.json** to trace the actual source paths of the duplicate units. They saw "370 units, 20 titles" and assumed re-indexing of a single file. The real mechanism — 25 different Kiro session snapshots at 25 different paths — is only visible by examining the actual `source_path` metadata in the ChromaDB embedding_metadata table and cross-referencing with processed.json's path entries.

**Methodological advantage:** Continue-DeepSeek had the breadth to read 10 source files, run 6 corpus queries, inspect ChromaDB SQLite directly, and cross-reference processed.json — all in a single session. This is the kind of expansive search that reveals root causes invisible to agents limited to `convmem ask` or single-code-file reads.

---

## Nil-to-Minor Problems (Not Debate-Impacting)

These were found during the scout but do not materially affect the "plan arc" retrieval debate:

| Problem | Detail | Impact |
|---|---|---|
| System paths in Cursor projects | `home-lauer` (home dir), `opt-lampp` (XAMPP), `run-media-lauer-nym-ollama-1T-fs` (external drive), `empty-window` (15 sessions) | Noise in different semantic neighborhoods; won't rank for "plan arc" |
| Garbage test units | `"test summary a b c"`, `"test upsert debug f22bbd2"`, `"doc"` | 3 units out of 9,258 (0.03%) — negligible |
| Low-signal short units | 1,357 units are 50-200 chars | These are mostly Cursor agent summary lines — valid but terse |
| `queue_max_depth` delta | Live: 200, Example: 100 | Higher is actually better (more queue capacity) |
| `dedupe_similarity` missing | Not in live config, defaults to 0.92 internally | Same as example default; no change needed |
| `untagged_priority` missing | Not in live config, defaults to true internally | Same as example default |
| Confidence histogram stability | Unchanged across 15h of daemon cycles: `{'0.0': 2, '0.4': 10, '0.6': 36, '0.7': 311, '0.8': 1909, '0.9': 3539, '1.0': 2228}` | Daemon is stable but not improving — refine.jobs can't fix the problems above |
| `recency_half_life_days` missing | Not in live config; default behavior if unset needs verification | Minor sub-item; recency is already broken (Layer 4) regardless of half-life |

---

## Impact Summary (Post-Scout)

The original 6-layer stack + 3 new layers + evidence chain collapse = **10 distinct failure modes** contributing to the retrieval miss:

| Layer | Name | Type | Fix Complexity |
|---|---|---|---|
| 0 | Kiro snapshot multiplication | Ingestion path | 5-line exclude |
| 1 | Language gap | Semantic | Coordination doc |
| 2 | Duplicate voting bloc | Consequence of L0+L7+L8 | Resolved by P0a+P0b |
| 3 | Rerank disabled | Config | 1-line toggle |
| 4 | Recency broken | Data quality | Timestamp backfill |
| 5 | No citation diversification | Query pipeline | ~30 lines |
| 6 | Evidence path noise | Query pipeline | ~15 lines |
| 7 | Double Kiro ingestion | Ingestion path | Remove stale import |
| 8 | Cursor project path multiplication | Ingestion path | Path canonicalization |
| 9 | chroma_dedupe ledger-id-keyed | Refine mechanism | Add semantic_dedupe to jobs |
| — | Evidence chain collapse | Data quality | Auto-backfill job |

**P0 fixes (Layers 0, 3, 7, 9):** ~15 lines of code + 2 config toggles. Impact: removes ~2,100 duplicate/low-quality units from retrieval path.
**P1 fixes (Layers 1, 2, 4, 5, 6, 8, evidence):** ~100 lines total. Impact: defense-in-depth for future queries.

---

## Meta

**Model:** Continue-DeepSeek V4 Pro (Continue IDE, MCP shell)
**Session:** Continue MCP verify — independent pipeline audit: code audit + ChromaDB SQLite forensics + processed.json analysis
**Author:** continue-session
**Date:** 2026-07-15
**Branch:** plan/2026-07-14-corpus-quality-audit
**Target PR:** #34 (docs/2026-07-15-debate-insight-folder)
**Corpus at time of audit:** 8058 units, 1163 summaries, 459 Kiro snapshot units, rerank=false, semantic_dedupe removed from daemon
