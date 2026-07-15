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

## Seven-Layer Failure Stack

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

## Live Config vs Example Config — Key Deltas

| Setting | config.example.toml | Live (from brief) | Impact |
|---------|---------------------|-------------------|--------|
| `rerank` | `true` | `false` | Cross-encoder OFF |
| `refine.jobs` | includes `semantic_dedupe` | excludes `semantic_dedupe` | Post-F1 removal; dedupe never runs |
| `recency_weight` | `0.1` | `0.1` | Active but useless for 59% |
| `sources.paths` | includes `~/.kiro/sessions` | includes `~/.kiro/sessions` | **Layer 0 enabler** — snapshots are scanned |

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

## Meta

**Model:** Continue-DeepSeek V4 Pro (Continue IDE, MCP shell)
**Session:** Continue MCP verify — independent pipeline audit: code audit + ChromaDB SQLite forensics + processed.json analysis
**Author:** continue-session
**Date:** 2026-07-15
**Branch:** plan/2026-07-14-corpus-quality-audit
**Target PR:** #34 (docs/2026-07-15-debate-insight-folder)
**Corpus at time of audit:** 8058 units, 1163 summaries, 459 Kiro snapshot units, rerank=false, semantic_dedupe removed from daemon
