# Conversation Compact — convmem (June 17–18, 2026)

Last compacted: 2026-06-18

## Project Overview

`convmem` is a local-first memory bus for AI coding assistants. It ingests chat logs (Cursor, Kiro, Continue, Aider, Open WebUI), distills them into typed knowledge units, and provides search/ask against a ChromaDB index. It also ingests structured observations from tools (wp-sec-agent, Lighthouse CI) as an inter-agent evidence ledger.

**Live index:** ~1,486 units visible (plus 20 tombstoned), ~1,470 untagged (no domain).

## Build Steps (chronological)

| Step | What shipped |
|------|-------------|
| 1–3 | Adapters (Cursor jsonl, Kiro sqlite, Continue JSON, Aider markdown, Open WebUI sqlite) |
| 4 | Ingest → conversation_summaries + `convmem index` + `--raw` search |
| 5 | Distillation → knowledge_units (solution/pattern/explanation/decision) |
| 6 | Cross-encoder rerank (top-20 → top-5) |
| 7 | Rich TUI, `convmem ask`, `convmem open` |
| **8** | **Domains, observations, verify** — `domains.py`, `observe.py`, `verify.py`, `--domain` flag |
| **A** | **Ledger contract** — `ledger.py` (Observation/Decision/Verification dataclasses), `observe.py` rewritten for ledger schema |
| **B** | **Evidence chain** — `convmem related`, `build_ledger_index()`, `related_chain()` |
| **C** | **Stable IDs, upsert** — `add --upsert`, `export_report_to_observations.py` |
| **E** | **Evidence rerank** — `evidence.py`, `ask --evidence` |
| **F0** | **Filesystem watch** — `watch.py` (inotify + watchdog), `convmem watch`, `systemd/convmem-watch.service.example` |
| **F1** | **Index refinement** — `refine.py`, `process_lock.py`, 7 jobs (chroma_dedupe, backfill_domain, ledger_link, semantic_dedupe, confidence_audit, redistill, stale_source_flag), `convmem refine` |
| **F2a** | **Store API + dedupe hardening** — `get_units_with_embeddings()`, `_dedupe_results_by_ledger_id()` in ask.py |

## Key Design Decisions (locked)

- **Tombstones are metadata-only** (`superseded: true` + `superseded_by: <uuid>`) — no physical deletes in v1
- **`units_metadata(include_superseded=False)`** is the default — all existing call sites unchanged
- **Rollback snapshots** at `refine_undo/<job>/<timestamp>.jsonl` before every mutating write
- **`redistill` is hard-gated** — `sys.exit(1)` without prior `confidence_audit` in `refine_stats.json`
- **No `--force` or `--prune` in F1**
- **No auto-merge** of semantic deduplicates — queue-only, Kiro approves
- **No job touches `processed.json` except `redistill`**
- Single writer for Chroma DB — miniPC is canonical, `refine.lock` on daemon start
- Observations are the lingua franca between agents; raw chats go through `convmem index` only

## Current Files

| File | Purpose |
|------|---------|
| `convmem.py` | Typer CLI — search, ask, index, stats, add, verify, related, watch, refine |
| `chroma_store.py` | ChromaDB wrapper — `get_units_with_embeddings()`, tombstone filter, all CRUD |
| `ledger.py` | Observation/Decision/Verification dataclasses + `normalize_ledger_record()` + graph traversal |
| `observe.py` | Direct JSONL ingestion → knowledge_units (delegates to `ledger.py`) |
| `distill.py` | LLM distillation from conversation chunks → knowledge units |
| `ingest.py` | Full ingest pipeline (summarize + distill) |
| `query.py` | Semantic search + Rich display (panels, citations, stats table) |
| `ask.py` | RAG answer with citations, `--evidence` flag, `_dedupe_results_by_ledger_id()` |
| `evidence.py` | Evidence-aware rerank (unresolved +0.18, failed +0.12, resolved -0.10, etc.) |
| `domains.py` | Dotted-path domain taxonomy + hierarchical matching |
| `verify.py` | Cross-model verification (metadata update + optional ledger record) |
| `watch.py` | Inotify-based filesystem watch (30s debounce, PID lock) |
| `refine.py` | 7 refinement jobs; daemon + `--once` mode; `CostLimiter`; undo snapshots |
| `process_lock.py` | Shared PID lock for watch + refine daemons |
| `related.py` | Evidence-chain display for `convmem related` |
| `export_report_to_observations.py` | Wp-sec-agent report → observations JSONL |
| `llm.py`, `meta_format.py`, `rerank.py`, `config.py`, `open_source.py` | Supporting |
| `docs/MILESTONE-F.md` | Locked F1 plan |
| `docs/F2a-SCOPING.md` | F2a tasks (Tasks 1 & 2 done, Task 3 skipped) |
| `docs/F2b-MONITOR-POLICY.md` | Kiro-locked monitor policy |

## Test Suite

**53/53 tests passing.** Files:
- `tests/test_chroma_superseded.py` (6 tests — tombstone filter, `get_units_with_embeddings`)
- `tests/test_refine.py` (6 tests — chroma_dedupe, confidence_audit, redistill gate, semantic_dedupe API)
- `tests/test_watch.py` (9 tests — debounce, flush, is_indexable, roots)
- Plus tests for ledger, upsert, milestone C, domain, evidence, ask, etc.

## CLI Commands

```
convmem "query" [--raw] [--top N] [--domain D] [--open N]
convmem ask "question" [--domain D] [--evidence] [-i] [--open N]
convmem index [--file PATH] [--limit N]
convmem stats
convmem add --file observations.jsonl [--upsert]
convmem add --title ... --summary ... --author ... [--keyword ...]
convmem verify <ledger_id> --model M [--confidence F] [--result pass|fail] [--notes ...]
convmem related <ledger_id>
convmem watch [--debounce N] [--path P] [--no-lock]
convmem refine [--once --job JOB] [--limit N] [--stats] [--no-lock]
```

## F2a Status (Tasks 1 & 2 complete, Task 3 skipped)

- **Task 1:** `get_units_with_embeddings()` added to `chroma_store.py` — returns `[{id, metadata, embedding}]` with `.tolist()` for numpy arrays, respects `include_superseded`. `semantic_dedupe` in `refine.py` now uses the public API — no `_collection` calls outside `chroma_store.py`.
- **Task 2:** `_dedupe_results_by_ledger_id()` already existed in `ask.py` (lines 100–111), wired after `apply_evidence_rerank()` when `--evidence` is set. Covered by existing tests.
- **Task 3 (LLM verdict on dedupe queue):** Skipped per instruction — stretch only after Tasks 1 & 2 clean.

## Current State

Backfill drain was started:
```
convmem refine --once --job backfill_domain --limit 60
```
Result: 60 processed / 60 updated / 0 errors, ~3.3 min runtime. Domains assigned: mostly `coding.tooling`, `coding.devops`, `general`. ~1,410 untagged remaining (of ~1,470). At 60/hr that's ~23.5 hours to drain on miniPC.

## What's Blocked / Deferred

- **F2b (monitor):** Blocked — Kiro policy locked in `docs/F2b-MONITOR-POLICY.md` (5 probes v1, observation vs verification rules, never-supersede-kiro check, confidence 0.4 always). Needs backfill drain to progress significantly (well below 1,400 untagged) before monitor probes are useful. Also needs Kiro sign-off on F2a first.
- **F2b probe set (v1):** CSP, HSTS, X-Content-Type-Options, Referrer-Policy, TLS redirect. Deferred v1.1: Permissions-Policy, cookie flags.
- **miniPC deployment:** Not yet — no SSH credentials needed until then.
- **Cursor store.db:** Detected but not indexed (deferred adapter).

## Next Action

F2a is verified. The next action is Kiro sign-off on F2a, then starting F2b (monitor) after the backfill drain makes meaningful progress or after Kiro gives the go. The miniPC backfill can also be set up as a systemd timer or cron job if that's preferred over running on this machine.
