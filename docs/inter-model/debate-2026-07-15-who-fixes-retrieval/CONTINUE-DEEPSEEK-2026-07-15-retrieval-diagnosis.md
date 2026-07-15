# CONTINUE-DEEPSEEK Retrieval Diagnosis — 2026-07-15

**Topic:** Why `convmem ask "current plan arc"` returns stale June 30 material instead of July 14-15 facts.

**Method:** Full pipeline code audit + live corpus queries. No inference from prior debate files — all findings verified against running corpus.

---

## Five-Layer Failure Stack

### Layer 1: LANGUAGE GAP
"current plan arc" semantically matches arc *definitions* (what an arc IS), not current coordination facts ("Arc 2 retrieval miss"). The HANDOFF-DEEPSEEK file's "Arc 2" section uses vocabulary (`coordination-index`, `convmem plan arc audit`) that doesn't bridge to natural query vocabulary (`current plan arc`).

**Evidence:** Top-5 vector results for "current plan arc" return PLAN-2026-06-25-surface-coverage (arc definition doc) and SOAK-REPORT (arc mention in unrelated context). The July 14 HANDOFF-DEEPSEEK file ranks outside top-10.

### Layer 2: DUPLICATE MASS (the silent killer)
- 370 units × 20 titles from Kiro v4 run
- 102 units from BUILT-PLANS
- **`semantic_dedupe` is NOT in the daemon config** — `refine.jobs` in config.toml lists: `chroma_dedupe, ledger_link, confidence_audit, stale_source_flag` — missing `semantic_dedupe`
- Hasn't run since July 1 manual F1 drain
- The entire debate about Claude's positional window bug is moot: the job never runs

**Live-data finding that contradicts Claude's claim:** Kiro v4 units ARE clustered (positions 3728–4195, max gap 31), not "thousands apart" as claimed. BUILT-PLANS has one outlier at position 1912 (gap 5,252 from main cluster at 7164+).

### Layer 3: NO CITATION DIVERSIFICATION
`_format_context` in `query.py` is a pure formatter — no collapse, no source cap, no diversity logic. If top-20 results are all Kiro v4 duplicates, all 20 citations go to Kiro v4.

### Layer 4: RECENCY CAN'T HELP
`recency_weight=0.1` is active in `query.py` but **59% of corpus has no timestamp** — all Cursor/Continue inter-model doc units. These get 0.000 recency boost, making recency useless for the exact documents that contain July 14-15 facts.

### Layer 5: EVIDENCE PATH NOISE
`_prepend_recent_decisions` in `ask.py` has no domain scoping. WordPress decisions (`dec_prop_*` with site=willowyhollow) bleed into convmem queries, injecting irrelevant context.

---

## Additional Live-Data Findings

### Confirmed
- HANDOFF-DEEPSEEK ingested **twice**: direct path + Kiro session snapshot → 2 ChromaDB units with same content
- `is_inter_model_doc` rejects nested paths — debate folder files in `docs/inter-model/debate-*/` **can't be read from corpus**
- Recency boost gives 0.000 to all Cursor/Continue units (no timestamp → no boost)

### Contradicts Prior Debate Claims
| Claim | Reality |
|-------|---------|
| "Kiro units thousands apart" (Claude) | Clustered at positions 3728–4195, max gap 31 |
| "Positional window fix needed" (Claude) | Window is fine; the problem is duplicates, not positions |
| "Ask-time diversification" (ChatGPT) | Only helps if duplicates are collapsed first; diversifying 20 Kiro titles is still 20 Kiro titles |

---

## Recommended Sequence

| Priority | Action | Lines of Code |
|----------|--------|---------------|
| **P0** | Add `"semantic_dedupe"` to `refine.jobs` in `config.toml` | 1 line |
| **P1** | Fix nested ingest: remove `os.sep` check from `is_inter_model_doc` | 2 lines |
| **P2** | Add coordination-index doc with searchable vocabulary bridge | ~30 lines |
| **P3** | Diagnose first, patch second — run dedupe, then re-evaluate ask quality | 0 lines |
| **P4** | Citation source diversification (conditional on P0 results) | ~20 lines |
| **P5** | Evidence domain scoping in `_prepend_recent_decisions` | ~10 lines |
| **P6** | Timestamp backfill for Cursor/Continue units | ~15 lines |

**P0 is the single highest-leverage fix.** Everything else is optimization on top of a broken foundation.

---

## Meta

**Model:** Continue-DeepSeek V4 Pro
**Session:** Continue MCP verify — independent pipeline audit
**Author:** continue-session
**Date:** 2026-07-15
**Branch:** plan/2026-07-14-corpus-quality-audit
**Target PR:** #34 (docs/2026-07-15-debate-insight-folder)
