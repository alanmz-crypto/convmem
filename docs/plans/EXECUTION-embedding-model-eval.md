# EXECUTION — Embedding-Model A/B Evaluation (operator runbook)

**Status:** R1 Phase A harness shipped on `feat/YYYY-MM-DD-embed-eval-harness`.  
**Authority:** Architecture Rev 1 + Kiro sign-off + Execution Plan Rev 2 (+ R2a/R2b split).

## What R1 delivered

Tracked library/CLI surfaces and hermetic tests only:

- `eval_corpus/` — classify, dedup, reconstruct, fingerprint, exclusions, validate, shadow_build, config_audit, metrics, capture helpers
- `scripts/eval_corpus_capture.py` — refuses without `--authorize-r2b`
- `scripts/eval_shadow_embed.py` — refuses without `--authorize-r4` / `--authorize-r5`
- `scripts/eval_config_diff_allowlist.py`
- `query.py` — optional eval-scoped `retrieval_view` / `eval_view` (production default unchanged)
- `doctor.py` — read-only `embed_collection_identity` check

## Authorization remaining

| Checkpoint | Meaning |
|------------|---------|
| **R2a** | Create isolated external dirs + shadow config files only |
| **R2b** | Run immutable capture + construct corpus package |
| **B-Accept** | Human acceptance before either shadow build |
| **C0** | Freeze evaluation contract (Kiro+Ryan) before challenger eval |
| **R3** | Probe both models (ask whether `ollama stop` unload is allowed) |
| **R4** | Nomic shadow build |
| **R5** | Challenger shadow build |
| **R6** | Service stop (default: do not) |
| **R7** | All evaluation including 8-query smoke |
| **R8** | Destructive cleanup of experimental artifacts |

## Explicitly not in this arc

Live promotion, live-config migration, production dual writes.

## Notes

- `pending_decisions.jsonl` is not in `query_units` closure — no freeze required (documented in `eval_corpus.config_audit`).
- Crash-safe writes: `eval_corpus.io_atomic` (temp + fsync + rename).
- Cold-load unload (`ollama stop`) is model-management, not R6 — request at R3/R7.
