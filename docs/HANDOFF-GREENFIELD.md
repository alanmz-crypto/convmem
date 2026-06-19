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
    search_fast, search, ask, related, stats → MCP-capable agents (Crush, Cursor)
    search_fast = retrieval only (~3s); ask = retrieve + synthesis (45s cap)
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
| Crush MCP connection | Config updated (timeout 120, env); **Sonnet to verify post-rebuild** |
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
| **Sonnet (you)** | **MCP expert** — Crush/Cursor MCP integration, tool contracts, stdio/protocol debugging, post-rebuild MCP verification. Own everything in § MCP below. |
| **Kiro** | Design reviewer, sanity checker, decision signer |
| **Cursor (Opus Auto)** | Primary implementer (CLI, ingest, adapters) |
| **Claude** | Architecture brainstorming, ecosystem strategy (not MCP wire-up) |
| **DeepSeek** | `convmem ask` synthesis + distillation API |

**Sonnet seed prompt:** Read this file, then **§ MCP integration** end-to-end. Your job is to get Crush reliably calling convmem tools after rebuild — not to re-audit ingest/watch unless MCP depends on it.

---

## MCP integration (Sonnet owns this)

### What the MCP server is

- **File:** `~/Projects/convmem/mcp_server.py`
- **Stack:** Python MCP SDK **1.28.0**, **FastMCP**, **stdio** transport only
- **Entry:** `asyncio.run(mcp.run_stdio_async())` — only `asyncio.run` in the codebase
- **Tools are sync** `def` (not `async def`); FastMCP runs them in a thread pool — no nested event loops
- **Read-only:** no ingest/write tools exposed (no `processed.json` race via MCP)
- **Stdout:** `sys.stdout.reconfigure(line_buffering=True)` at startup (subprocess block-buffering guard)
- **Import path:** `sys.path.insert(0, Path(__file__).parent)` — CWD-independent

### Tool catalog (current)

| Tool | Latency (typical) | Use when |
|------|-------------------|----------|
| **`search_fast`** | ~3 s | Agent needs retrieval only; Crush default fast path |
| `search` | ~3 s | Same as `search_fast` (alias payload); prefer `search_fast` in Crush |
| `ask` | ~3 s retrieve + up to **45 s** synthesis | Need synthesized answer + citations |
| `related` | ~1 s | Traverse ledger graph by `ledger_id` |
| `stats` | ~0.5–2 s | Corpus counts by tool/domain |

**`ask` response JSON fields:** `answer`, `citations[]`, `confidence`, `warning`, `synthesis_failed` (bool).

**Synthesis failure behavior:** citations built **before** LLM call; on timeout/error → retrieval-only answer + `synthesis_failed: true` (does not hard-fail the MCP call).

**Not exposed via MCP:** rerank (config `rerank=false`), ingest, exclude, monitor, refine.

### Client registration

#### Crush (primary target)

**Config:** `~/.config/crush/crush.json` — top-level key **`mcp`** (NOT `mcpServers`; that key is **legacy/stale** in old docs).

```json
"mcp": {
  "convmem": {
    "type": "stdio",
    "command": "/home/lauer/miniforge3/envs/convmem/bin/python",
    "args": ["/home/lauer/Projects/convmem/mcp_server.py"],
    "timeout": 120,
    "env": {
      "HOME": "/home/lauer",
      "DEEPSEEK_API_KEY": "$(grep DEEPSEEK_API_KEY ~/.config/convmem/env.systemd | cut -d= -f2-)"
    }
  }
}
```

- Crush default MCP timeout was **15 s** — too tight for `ask` (~14 s before fixes). **`timeout: 120`** is set.
- Crush client negotiates **`2025-11-25`** (`LATEST_PROTOCOL_VERSION` in Crush Go MCP client). Server accepts and returns same.
- Crush connects MCP servers **at startup** (parallel init per server). No `/mcp connect` CLI command.
- **Config priority:** project `.crush.json` / `crush.json` overrides global — check workspace for missing `convmem` block.
- **Logs:** `journalctl --user` won't show MCP; use Crush session / `crush server` socket `unix:///run/user/1000/crush-1000.sock` for debugging.
- **Tool names in Crush:** prefixed `mcp_convmem_<tool>` (e.g. `mcp_convmem_search_fast`).

#### Cursor

- Config: `~/.cursor/mcp.json` (separate from Crush)
- Same command/args; Cursor spawn may leave **stale long-lived** `mcp_server.py` — restart if tools behave like pre-fix code

### Spawn environment (what works without shell activation)

Crush spawns with **minimal env** (not full conda `PATH`). Verified with `env -i HOME=...`:

| Need | Source |
|------|--------|
| Config | `~/.config/convmem/config.toml` via `load_config()` |
| Chroma path | Absolute after expanduser — **CWD-safe** (`/tmp` spawn OK) |
| Ollama embed/search | `http://localhost:11434` must be reachable |
| DeepSeek synthesis | `DEEPSEEK_API_KEY` in Crush `env` block; without key → falls back to `llama3.1:8b` |

No `CONVMEM_*` env vars required for basic operation.

### MCP audit results (items 1–10) — pre-fix baseline

| # | Area | Status |
|---|------|--------|
| 1 | `crush.json` key conflict | ✅ Only `mcp.convmem`; no duplicate `mcpServers` |
| 2 | Stdio framing | ✅ No stdout on import/initialize; stderr only for rerank fallback |
| 3 | Env at spawn | ✅ Works; `timeout` + `env` added |
| 4 | `processed.json` race | ✅ N/A — MCP has no ingest tool |
| 5 | Reranker blocking | ✅ `rerank=false` |
| 6 | Chroma relative paths | ✅ All absolute via `load_config()` |
| 7 | asyncio nesting | ✅ Safe |
| 8 | Protocol version | ✅ `2025-11-25` negotiated |
| 9 | processed.json corruption | ⚠️ MCP ignores file; ingest fails loud on corrupt JSON now |
| 10 | Ask timeout / hang | ✅ Fixed: 45 s cap + retrieval fallback |

**Symptom map:** `search_fast` works but `ask` fails → was Crush 15 s timeout; should be fixed. If still broken → stdout pollution, project-local crush.json, or stale MCP process.

### Verification commands (run these post-rebuild)

```bash
# 1. Protocol + tool list
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}\n' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}\n' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n' \
| ~/miniforge3/envs/convmem/bin/python ~/Projects/convmem/mcp_server.py 2>/dev/null \
| tail -1 | python -m json.tool

# Expect 5 tools: search_fast, search, ask, related, stats

# 2. Minimal-env search (simulates Crush spawn)
env -i HOME=$HOME USER=$USER \
  ~/miniforge3/envs/convmem/bin/python -c "
import sys; sys.path.insert(0,'$HOME/Projects/convmem')
from query import query_units
print(len(query_units('wordpress', top_k=1)))
"

# 3. Ask fallback (synthesis failure should not crash)
cd ~/Projects/convmem && python -c "
from unittest.mock import patch
from ask import ask
with patch('ask.generate', side_effect=TimeoutError('test')):
    r = ask('test', top_k=2)
print('synthesis_failed', r.get('synthesis_failed'), 'cites', len(r.get('citations',[])))
"

# 4. Kill stale MCP before Crush retest
pkill -f 'mcp_server.py'   # Cursor/Crush will respawn on next session
```

### Open MCP work for Sonnet

| Task | Priority |
|------|----------|
| **Verify Crush connects post-rebuild** | P0 — listed as untested in known debt |
| Confirm `mcp_convmem_search_fast` callable from Crush agent | P0 |
| Confirm `ask` returns within 120 s with `synthesis_failed` on API slowness | P1 |
| Update `docs/HANDOFF-CRUSH-MCP-DEBUG.md` (still shows `mcpServers`) | P2 |
| Consider hardcoded API key in crush.json → shell expansion only | P2 security |
| Future: ingest MCP tool would need `processed.json` file lock | backlog |

### What MCP does NOT depend on

- `processed.json` state (never read by MCP)
- Watch/refine daemons running
- Reranker loaded
- `semantic_dedupe` / embedding bulk `get()`

MCP **does** depend on: finished or partial Chroma index, Ollama up, optional DeepSeek for full `ask` synthesis.

---

## Related docs

| Doc | Notes |
|-----|-------|
| `docs/HANDOFF-CRUSH-MCP-DEBUG.md` | **Stale** — shows `mcpServers`; use § MCP integration above |
| `docs/HANDOFF-FOR-CLAUDE.md` | Product/W5H direction (pre-rebuild counts) |
| `docs/HANDOFF-EXCLUDE.md` | Exclude feature |
| `docs/HANDOFF-CURSOR-STOREDB.md` | Cursor store.db adapter |

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

## MCP Server (Sonnet's area)

**File:** `mcp_server.py` — FastMCP (Python `mcp` SDK v1.28.0), stdio transport.

**Tools exposed:**
| Tool | Latency | LLM call | Notes |
|------|---------|----------|-------|
| `search_fast` | ~50ms | No | Retrieval only, no synthesis |
| `ask` | 2–45s | Yes (DeepSeek) | Degrades to raw results on timeout/failure |
| `related` | ~100ms | No | Graph traversal via ledger_id |
| `stats` | ~200ms | No | Corpus counts |

**Registered in:**
| Client | Config file | Key format |
|--------|-------------|-----------|
| Cursor | `~/.cursor/mcp.json` | `mcpServers.convmem` |
| Crush | `~/.config/crush/crush.json` | `mcp.convmem` + `type: stdio` |
| Continue | `~/.continue/mcpServers/convmem.json` | `mcpServers.convmem` |

**Timeout architecture:**
- Crush client timeout: 60s (set in crush.json `timeout` field)
- DeepSeek API timeout: 45s (in `llm.py`)
- `ask` catches all exceptions → returns raw retrieval results on failure
- `search_fast` never calls LLM → always responds in <1s

**Env vars passed to subprocess (in config `env` blocks):**
- `HOME` (for config.toml path expansion)
- `DEEPSEEK_API_KEY` (for `ask` synthesis)

**Protocol:** Server negotiates to client's requested version (tested 2024-11-05 and 2025-03-26). No stdout pollution in tool paths — all print goes to stderr or is absent.

**Current status:**
- Cursor: should work (untested since latest refactor)
- Crush: config fixed (`mcp` key, `type: stdio`, `timeout: 60`), needs restart to verify connection
- Continue: config dropped in `~/.continue/mcpServers/`, untested

**Known issues:**
- Crush wasn't connecting pre-fix (wrong config keys). Post-fix untested.
- No write tools exposed (search/ask/related/stats are all read-only)
- Future: `propose_decision` tool (agent proposes, human confirms, then ingest)

**Testing the server manually:**
```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}}\n' | /home/lauer/miniforge3/envs/convmem/bin/python /home/lauer/Projects/convmem/mcp_server.py 2>/dev/null
```

**Next MCP work:**
1. Verify Crush connects after config fix (restart Crush, ask agent to call `search_fast`)
2. Add `propose_decision` write tool with human-confirm gate
3. Consider streaming for `ask` if 45s feels too slow for interactive use

## Constraints

- Local first; cloud only for DeepSeek API
- Kiro authority: decisions require human confirmation
- No GPU contention: don't index while ComfyUI is active
- Single writer: only one host writes to Chroma at a time
- 69 tests must pass before any merge
