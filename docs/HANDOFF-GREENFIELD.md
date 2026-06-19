# convmem — Greenfield Handoff for New Agent

## What this is

Local-first CLI that turns AI chat history into a searchable, citeable knowledge corpus with an evidence ledger for security findings. No cloud database, no web app. ChromaDB on disk + DeepSeek API for synthesis.

**Repo:** `~/Projects/convmem`  
**Config:** `~/.config/convmem/config.toml`  
**Data:** `~/.local/share/convmem/` (chroma/, processed.json, logs/)  
**Env:** `mamba activate convmem` (Python 3.11, all deps installed)

## Current state (2026-06-19)

- **Rebuild in progress** — `convmem index` running (PID 1128957), wiped old corrupted/duplicated Chroma, rebuilding clean from 122 source files. ~926 units so far, will finish at ~1,500–2,500.
- **Watch disabled** — re-enable after rebuild: `systemctl --user enable --now convmem-watch`
- **Refine active** — `convmem-refine.service` running (dedupe, link, audit jobs)
- **Monitor active** — `convmem-monitor.timer` probes staging2.willowyhollow.com hourly
- **69 tests passing**
- **MCP server** registered for Cursor, Crush, Continue (stdio transport)
- **rerank = false** in config (GPU contention mitigation; re-enable after rebuild)

## Architecture

```
Chat logs (Cursor, Kiro, Crush, Continue, Aider, Open WebUI)
    → adapters (format-based detection)
    → ingest.py (chunk → summarize → distill → embed → Chroma)

Security tools (wp-sec, Lighthouse, monitor probes)
    → observe.py / ledger.py (structured JSONL → Chroma)
    → evidence chain: observation → decision → verification

Query paths:
    convmem "query"           → semantic search (knowledge_units)
    convmem "query" --raw     → conversation_summaries fallback
    convmem ask "question"    → RAG (retrieve + DeepSeek synthesis + citations)
    convmem related <id>      → graph traversal (relates_to links)
    convmem ask --evidence    → prefer unresolved findings

MCP server (mcp_server.py):
    search, ask, related, stats → any MCP-capable agent
```

## Key files

| File | Role |
|------|------|
| `convmem.py` | CLI entry (typer) |
| `config.py` | Load TOML config |
| `adapters/` | Format detection + parsers (jsonl, sqlite, json, markdown) |
| `ingest.py` | Chunk → summarize → distill → embed → store |
| `distill.py` | LLM extraction → knowledge units (deterministic IDs) |
| `chroma_store.py` | ChromaDB wrapper (upsert, query, tombstone) |
| `llm.py` | Ollama embed + DeepSeek/Ollama generate |
| `ask.py` | RAG: retrieve → synthesize → cite |
| `query.py` | Retrieval + Rich display |
| `ledger.py` | Evidence ledger (observation/decision/verification) |
| `observe.py` | Direct ingest for tool-sourced findings |
| `evidence.py` | Evidence-aware re-ranking (unresolved > resolved) |
| `monitor.py` | HTTP security header probes |
| `refine.py` | Background jobs (dedupe, backfill, audit) |
| `watch.py` | Filesystem watch → incremental index |
| `mcp_server.py` | FastMCP stdio server |
| `extract_procedures.py` | Crush bash tool_call → procedure records |
| `domains.py` | Domain taxonomy |
| `rerank.py` | CrossEncoder reranker (CUDA→CPU fallback) |

## Milestones completed

Steps 0–8, Milestones A (ledger), B (graph), C (scanner auto-ingest + upsert), E (evidence-aware ask), F0 (watch), F1 (refine), F2a (store API), F2b (monitor), F2c (Crush adapter), Decision schema extension, Procedure extraction, Cursor store.db adapter, MCP server, Exclude feature.

## Decisions in the corpus (signed by Kiro)

- Single-writer Chroma (one machine owns the index)
- Dev machine is canonical host (not miniPC)
- No auto-merge semantic duplicates (queue for human review)
- Monitor never supersedes Kiro verification
- Rationale stored in Chroma document text (not metadata-only)
- Deterministic unit IDs: hash(source_path + start_offset + unit_index)
- add_unit uses upsert (idempotent re-index)
- Watch skips live DBs (Kiro sqlite, webui.db)
- Kiro DB excluded from watch (manual `index --file` only)

## Known debt

| Item | Status |
|------|--------|
| Rebuild in progress | Running now; re-enable watch after |
| `recency_weight` | Config key exists, not implemented |
| `semantic_dedupe` | Removed from refine jobs; blocked until rebuild completes and `get(embeddings)` works |
| Crush MCP connection | Config correct, untested post-fix |
| `cause_unverified` monitor queue | Not built |
| OpenClaw probes (Milestone D) | Deferred |

## After rebuild completes

```bash
# Check it finished
convmem stats

# Re-enable watch
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch

# Verify watch is healthy after 30 min
journalctl --user -u convmem-watch -n 20

# Re-run confidence audit
convmem refine --once --job confidence_audit
```

## Agent roles

| Agent | Role |
|-------|------|
| **Kiro** | Design reviewer, sanity checker, decision signer |
| **Cursor (Opus Auto)** | Primary implementer |
| **Claude** | Architecture brainstorming, ecosystem strategy |
| **DeepSeek** | `convmem ask` synthesis, distillation |

## CLI quick reference

```bash
source ~/.config/convmem/env.local

convmem "search query"                          # semantic search
convmem "query" --domain web_stack.security     # scoped
convmem ask "question"                          # RAG answer
convmem ask "question" --evidence               # prefer unresolved
convmem ask -i                                  # interactive
convmem related obs_staging2_wpsec_csp-missing  # evidence chain
convmem add --file observations.jsonl --upsert  # ingest findings
convmem verify UNIT_ID --model kiro-review      # cross-model check
convmem exclude PATH --reason "noise"           # exclude from indexing
convmem stats                                   # corpus overview
convmem refine --once --job confidence_audit    # run one refine job
convmem monitor --site staging2.willowyhollow.com --dry-run
```

## Constraints

- Local first; cloud only for DeepSeek API
- Kiro authority: decisions require human confirmation
- No GPU contention: don't index while ComfyUI is active
- Single writer: only one host writes to Chroma at a time
- 69 tests must pass before any merge
