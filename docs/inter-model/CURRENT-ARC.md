# Current Plan Arc — 2026-07-15

**Active arc:** Corpus quality audit — systematic deep analysis of the convmem
knowledge corpus to identify junk, gems, structural ingestion problems, and
concrete signal-to-noise improvements.

**Canonical handoff (what we're doing):**
[HANDOFF-DEEPSEEK-2026-07-14-corpus-quality-audit.md](HANDOFF-DEEPSEEK-2026-07-14-corpus-quality-audit.md)

**Active diagnosis (what we found):**
[CONTINUE-DEEPSEEK-2026-07-15-retrieval-diagnosis.md](CONTINUE-DEEPSEEK-2026-07-15-retrieval-diagnosis.md)
— 11-layer failure stack documented, P0 fix sequence in progress.

**Latest model-to-model coordination:**
[LATEST.md](LATEST.md) (note: may be stale mid-session; the corpus-quality-audit
arc is in progress and LATEST.md updates at session close.)

## Keywords for Search
plan, arc, current, active, now, today, latest, state, what are we doing,
corpus quality audit, retrieval diagnosis, junk detection, tombstone,
deduplication, semantic dedupe, ChromaDB cleanup, plan-arc-2026-07

## P0 Fix Status (2026-07-15)
- [x] P0a — Exclude Kiro snapshots from `is_inter_model_doc` (adapters/inter_model_doc.py)
- [x] P0b — Purge 646 Kiro snapshot units from ChromaDB
- [x] P0c — Re-enable `semantic_dedupe` + `rerank` in config
- [x] P0d — Create CURRENT-ARC.md vocabulary bridge (this file)
- [x] P0e — Add mid-session arc pointer to LATEST.md
