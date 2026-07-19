# EXECUTION — Embedding-Model A/B Evaluation (operator runbook)

**Status:** R1 Phase A harness complete on `feat/2026-07-19-embed-eval-harness`.  
**Authority:** Architecture Rev 1 + Kiro sign-off + Execution Plan Rev 2 (+ R2a/R2b split).

## What R1 / Phase A delivered (tracked code + hermetic tests)

Library/CLI surfaces exercised only with temp fixtures — **no live capture, shadow
build, model ops, or evaluation against live/shadow stores** under R1:

| Surface | Capability shipped in-repo |
|---------|----------------------------|
| `eval_corpus/` | classify, dedup, reconstruct, fingerprint, exclusions, validate, capture (atomic copy + one-txn SQLite extract + package), shadow_build (injectable embed_fn + temp Chroma lifecycle/resume), config_audit, metrics, runner (dual views + latency harness) |
| `scripts/eval_corpus_capture.py` | Full capture CLI; refuses without `--authorize-r2b`; hermetic smoke uses temp paths |
| `scripts/eval_shadow_embed.py` | Embed-only builder CLI; refuses without `--authorize-r4`/`--authorize-r5`; `--embed-mode=fake` for hermetic; refuses `ollama` under R1 default |
| `scripts/eval_config_diff_allowlist.py` | Allowlist proof helper |
| `query.py` | Optional eval-scoped `retrieval_view` / `eval_view` (production default unchanged) |
| `doctor.py` | `embed_collection_identity` via **SQLite `mode=ro`** (`chroma_readonly.collection_config_metadata`) — no PersistentClient |

## Not shipped / not authorized under R1

- R2a external eval dirs + shadow config files
- R2b live immutable capture against production export/processed/chroma
- Real Ollama embedding / model pull / cold-load unload
- R4/R5 live shadow builds, R7 evaluation, R6 service stop, R8 cleanup
- Promotion, live-config migration, production dual writes

## Authorization remaining

| Checkpoint | Meaning |
|------------|---------|
| **R2a** | Create isolated external dirs + shadow config files only |
| **R2b** | Run immutable capture + construct corpus package against freeze paths |
| **B-Accept** | Human acceptance before either shadow build |
| **C0** | Freeze evaluation contract (Kiro+Ryan) before challenger eval |
| **R3** | Probe both models (ask whether `ollama stop` unload is allowed) |
| **R4** | Nomic shadow build |
| **R5** | Challenger shadow build |
| **R6** | Service stop (default: do not) |
| **R7** | All evaluation including 8-query smoke |
| **R8** | Destructive cleanup of experimental artifacts |

## Notes

- `pending_decisions.jsonl` is not in `query_units` closure — no freeze required (documented in `eval_corpus.config_audit`).
- Crash-safe writes: `eval_corpus.io_atomic` (temp + fsync + rename) for capture/package/manifest/result.
- Capture chroma extract is one readonly SQLite transaction (`mode=ro`), not PersistentClient.
- Cold-load unload (`ollama stop`) is model-management, not R6 — request at R3/R7.
