# DeepSeek Corpus Quality Audit — Handoff

**From:** Kiro (design/sign-off lane)  
**To:** DeepSeek (synthesis API — `convmem ask`)  
**Date:** 2026-07-14  
**Branch:** `plan/2026-07-14-corpus-quality-audit`

---

## Objective

Perform a deep analysis of the convmem knowledge corpus to identify:
1. **Junk** — redundant, low-value, or noise units polluting search results
2. **Gems** — high-signal units that represent durable knowledge worth protecting
3. **Structural problems** — patterns in ingestion/indexing that create junk systematically
4. **Recommendations** — concrete changes to improve signal-to-noise ratio

---

## Corpus State (as of 2026-07-14)

| Metric | Value |
|--------|-------|
| JSONL total lines | 17,626 (unique IDs) |
| Chroma indexed | 7,831 (44% of JSONL) |
| Superseded/tombstoned | 0 |
| Summaries | 1,140 |
| Confidence mean | 0.91 |
| Low confidence (<0.5) | 11 units |

### By tool (JSONL, all)
| Tool | Units | Has timestamp? |
|------|-------|----------------|
| cursor | 9,413 | **No** |
| kiro | 2,864 | Yes |
| codex | 1,447 | Yes |
| inter-model | 1,358 | Yes |
| continue | 1,056 | **No** |
| crush | 641 | Yes |
| openwebui | 541 | Yes |
| ryan | 138 | Yes |
| kiro-review | 72 | Yes |
| aider | 47 | Yes |

### By domain (Chroma, top 10)
| Domain | Units |
|--------|-------|
| coding.tooling | 1,738 |
| general | 291 |
| web_stack.security | 227 |
| coding.backend | 150 |
| web_stack.wordpress.deployment | 126 |
| web_stack.wordpress.plugins | 124 |
| web_stack.hosting | 75 |
| coding.tools.convmem | 63 |
| web_stack.wordpress.development | 36 |
| web_stack.wordpress.hosting | 34 |

---

## Known Junk Patterns (Kiro's initial triage)

### 1. Massive heading-level duplication from inter-model docs

**Worst offender:** `KIRO-2026-06-30-redrafted-plan-v4.md` → **370 units**, but only **20 unique titles**, each repeated 17–25x.

The indexer is chunking the same document multiple times (likely re-indexed on each watch trigger or manual `convmem index` call), and each chunk gets a new UUID instead of deduplicating by content hash.

Other high-repeat inter-model files:
- `BUILT-PLANS-2026-06-24-to-2026-06-29.md` → 102 units
- `WILLOWYHOLLOW-BUG-TRIAGE-2026-07-06.md` → 92 units
- `WILLOWYHOLLOW-CODE-REVIEW-FINDINGS.md` → 90 units (all unique titles — this is legitimate)

**Question for analysis:** Are the 370-unit files genuinely re-indexed 20+ times, or is the chunker splitting at headings and generating near-identical summaries for adjacent chunks of the same section?

### 2. Cursor and Continue units have no timestamps

10,469 of 17,626 units (59%) lack a timestamp. All cursor (9,413) and continue (1,056) units are affected. This means:
- Recency scoring is broken for the majority of units
- Cross-project digest can't filter stale cursor knowledge
- Deduplication across time windows is impossible

**Question:** Can we backfill timestamps from the source file mtime or from the JSONL's position (append-only implies ordering)?

### 3. The kiro-cli sqlite source produces generic "how-to" noise

1,892 units from `~/.local/share/kiro-cli/data.sqlite3`. Sample titles:
- "Enable Ollama systemd service for auto-start"
- "Install jq to fix zsh-ai JSON parsing"  
- "Install nvidia-settings GUI on Arch Linux"
- "Enable soft wrap in nano by default"

These are one-shot Q&A solutions from early Kiro usage. They're individually correct but collectively they drown out project-specific knowledge in search results. Many are trivially googleable — not the kind of thing that needs to persist in a project memory corpus.

**Question:** Should these be quarantined to a separate low-priority collection, or tombstoned outright? What's the retrieval hit rate on them?

### 4. Zero tombstones despite refine running

The `chroma_dedupe` job runs every 5 minutes but has tombstoned 0 units total. The dedupe queue has only 10 items. Either:
- The similarity threshold is too conservative
- The dedupe queue isn't being populated (no near-duplicate detection feeding it)
- The approval workflow is blocking progress (Ryan must approve)

### 5. JSONL-to-Chroma gap (56% not indexed)

17,626 JSONL entries but only 7,831 in Chroma. Doctor says "44% indexed" which it considers acceptable. But this means over half the corpus is searchable only via JSONL grep, not vector search. 

**Question:** Is this by design (Chroma holds only high-quality subset)? Or is it a pipeline failure where cursor/continue units never get embedded?

---

## Specific Audit Tasks for DeepSeek

### A. Duplicate cluster detection

Sample 100 random units from the `coding.tooling` domain (largest at 1,738 units). For each, query Chroma for top-5 nearest neighbors. Report:
- How many clusters have cosine similarity > 0.92 (near-duplicate threshold)?
- What's the distribution of cluster sizes?
- Are duplicates from the same source file or cross-source?

Approach:
```bash
convmem ask "In the coding.tooling domain, find examples of near-duplicate knowledge units that say essentially the same thing in different words. Give 5 concrete pairs with their titles."
```

### B. Signal-to-noise ratio by source type

For each tool (cursor, kiro, codex, inter-model, continue, crush), sample 10 units and rate each 1–5 on:
- **Specificity** — Does it contain project-specific knowledge, or is it generic?
- **Durability** — Will this still be relevant in 3 months?
- **Actionability** — Could an agent use this to make a concrete decision?

Approach:
```bash
convmem ask "Rate these 5 random cursor-sourced units on specificity, durability, and actionability (1-5 each). Give a brief rationale for each rating." 
```

### C. Domain taxonomy coherence

The domain tree has overlap and inconsistency:
- `coding.tooling` (1,738) vs `coding.tools.convmem` (63) — why the split?
- `coding.git` (24) vs `coding.git.workflow` (23) vs `coding.git_workflow` (19) — three domains for the same topic
- `web_stack.wordpress.hosting` (34) vs `web_stack.hosting` (75) — overlapping hierarchy
- `general` (291) — is this a dumping ground?

**Task:** Propose a normalized domain taxonomy that collapses redundant categories and routes the `general` bucket into specific homes.

### D. Inter-model document re-indexing problem

The `KIRO-2026-06-30-redrafted-plan-v4.md` file has 370 units with only 20 unique titles (each repeated ~20x). Determine:
- Is this from watch re-triggering on the same file?
- Is the processed.json filter failing to prevent re-indexing?
- Should inter-model docs use content-hash deduplication at ingest time?

### E. Retrieval quality spot-check

Run 10 realistic queries that an agent would ask during a session:
1. "How do I restore a WordPress backup on practice?"
2. "What's the convmem branching protocol?"
3. "Which security headers are missing on staging2?"
4. "How does the view transitions CSS work?"
5. "What was decided about the Chroma dedupe threshold?"
6. "Where are the Codex session logs stored?"
7. "What's the difference between Track A and Track B?"
8. "How do I run the cross-project digest?"
9. "What bugs were found in the July sprint?"
10. "What's the watch service memory limit?"

For each query, evaluate whether the top-3 results are:
- **Relevant** (actually answers the question)
- **Fresh** (not superseded by newer information)
- **Authoritative** (from a decision/verification, not a stale chat excerpt)

---

## Desired Output

A structured report (can go in this same inter-model directory or delivered via `convmem ask` session) covering:

1. **Junk inventory** — Estimated % of corpus that's noise, by category
2. **Gem patterns** — What makes the best units good? Common traits.
3. **Pipeline fixes** — Concrete changes to ingestion/indexing to prevent future junk:
   - Content-hash dedup at ingest?
   - Timestamp backfill strategy?
   - Source-level quarantine rules?
   - Domain normalization map?
4. **Cleanup plan** — Priority-ordered list of tombstoning actions (what to supersede and why)
5. **Metrics** — Proposed quality gates for `convmem doctor` to catch drift

---

## Constraints

- **Read-only analysis.** Do not tombstone, modify, or approve anything. This is an audit.
- DeepSeek operates via `convmem ask` — it can search and reason but not write to the ledger.
- Ryan approves any cleanup actions proposed by this audit.
- The JSONL at `~/.local/share/convmem/knowledge_units.jsonl` is the canonical data source for this analysis.

---

## How to Run This

Ryan or Crush can drive this audit by running targeted `convmem ask` queries based on the tasks above. The DeepSeek synthesis layer will ground its answers in the actual corpus via Chroma search. For tasks requiring raw JSONL analysis (duplicate counting, timestamp gaps), use Python one-liners against the ledger file directly.

Relevant code paths:
- `refine.py` — dedupe logic, tombstoning, queue management
- `chroma_store.py` — ChromaStore wrapper, superseded cache
- `adapters/` — per-source ingestion (cursor, codex, kiro, inter-model, etc.)
- `config/agent-protocol.md` — how agents interact with convmem
- `~/.config/convmem/config.toml` — sources, index paths, model config

---

## Success Criteria

After this audit, we should know:
1. What % of the corpus is junk and what kind
2. Whether the current dedupe pipeline is effective or broken
3. A prioritized cleanup roadmap that Ryan can approve
4. Whether the JSONL→Chroma gap is by design or a bug
5. Specific ingestion changes to stop creating junk going forward
