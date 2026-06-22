# convmem — Multi-Agent Handoff (2026-06-22)

## Who I am (Kiro)

I'm the design reviewer and sanity checker for this project. I don't write the bulk of implementation code — I watch for mistakes, block bad assumptions, sign off on milestones, and write decision records. I have shell access to the dev machine and can verify anything on disk.

**My authority:** No adapter merges without `parse(real_file)[:2]` gate output. No scope creep without explicit approval. Decisions require human confirmation before ingestion. I sign off on milestones before the next one starts.

**What I've done this session:** Reviewed and signed off all milestones through F2c, wrote the Decision schema extension, implemented the exclude feature, fixed the re-index duplication root cause (deterministic IDs + upsert), diagnosed and fixed OOM crashes, built the MCP server, and wrote procedure extraction from Crush.

---

## Current state (2026-06-22)

### Corpus
- **1,028 knowledge units** (clean rebuild completed 2026-06-19)
- **263 conversation summaries**
- **121 source files processed** across Cursor JSONL (54), Continue (29), Crush (24), Cursor store.db (6), Aider (7), Open WebUI (1), Kiro (1)
- Domains fully tagged (0 untagged)
- 72 unit tests passing

### Services
| Service | Status | Notes |
|---------|--------|-------|
| `convmem-watch` | **disabled** | Re-enable after confirming stability: `systemctl --user enable --now convmem-watch` |
| `convmem-refine` | active | Jobs: chroma_dedupe, ledger_link, confidence_audit, stale_source_flag |
| `convmem-monitor.timer` | active | Hourly probes on staging2.willowyhollow.com |

### MCP Server
- **File:** `mcp_server.py` (FastMCP, Python MCP SDK 1.28.0, stdio)
- **Tools:** `search_fast` (retrieval only), `ask` (RAG + graceful degradation), `related`, `stats`
- **Registered:** Cursor (`~/.cursor/mcp.json`), Crush (`~/.config/crush/crush.json`), Continue (`~/.continue/mcpServers/convmem.json`)
- **Crush timeout:** 120s; DeepSeek internal timeout: 45s
- **Status:** Configured but Crush connection **unverified post-rebuild**

---

## Agent roles

| Agent | Role | Scope |
|-------|------|-------|
| **Kiro** | Design reviewer, decision signer | Reviews all PRs; blocks bad assumptions; writes decision records |
| **Cursor (Opus Auto)** | Primary implementer | Writes CLI, adapters, ingest, refine code |
| **Sonnet** | MCP expert | Owns Crush/Cursor/Continue MCP integration, tool contracts, stdio debugging |
| **Claude** | Architecture strategist | W5H direction, ecosystem design, inter-agent workflow patterns |
| **DeepSeek** | Runtime synthesis | `convmem ask` answers, distillation API |

---

## What each agent needs to know

### For Cursor (implementer)

**Build order discipline is enforced.** No Step N+1 until Step N is gate-tested. No adapters without `parse(real_file)[:2]` on terminal output.

**Key recent fixes:**
- `make_unit_id` uses `(source_path, start_offset, unit_index)` — no title (LLM non-deterministic)
- `add_unit` uses Chroma `upsert` not `add`
- Watch skips live DBs (Kiro sqlite, webui.db) via `is_live_watch_db()`
- `force_file` deletes old units for that source before re-ingesting
- `MemoryMax=4G` + `OOMPolicy=stop` + `RestartSec=300` on watch service
- `rerank=false` in config (GPU contention; re-enable when needed)

**Tests:** 72 tests in `tests/`. Run with: `python -m unittest discover -s tests -q`

**Next implementation items (priority order):**
1. Verify watch stability after re-enable (24h clean run)
2. `cause_unverified` monitor queue
3. `propose_decision` MCP write tool (agent proposes, human confirms)
4. `recency_weight` implementation

### For Sonnet (MCP expert)

**Your P0:** Verify Crush actually connects to convmem MCP server and calls tools.

**Ground truth on disk:**
```json
// ~/.config/crush/crush.json → mcp.convmem
{
  "type": "stdio",
  "command": "/home/lauer/miniforge3/envs/convmem/bin/python",
  "args": ["/home/lauer/Projects/convmem/mcp_server.py"],
  "timeout": 120,
  "env": {"HOME": "/home/lauer", "DEEPSEEK_API_KEY": "..."}
}
```

**Tool names in server code:** `search_fast`, `ask`, `related`, `stats` (no prefix). Crush may add `mcp_convmem_` prefix client-side.

**Protocol:** Server negotiates to client's requested version. SDK `LATEST_PROTOCOL_VERSION = "2025-11-25"`.

**Timeout stack:** Crush 120s → DeepSeek 45s → graceful fallback to raw retrieval on any failure.

**Test manually:**
```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"crush","version":"1.0"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{}}\n' | /home/lauer/miniforge3/envs/convmem/bin/python /home/lauer/Projects/convmem/mcp_server.py 2>/dev/null
```

### For Claude (strategist)

**Completed since last session:**
- Decision schema: `rationale`, `alternatives_rejected`, `constraints` fields on decisions
- Procedure extraction from Crush `tool_call`/`tool_result` pairs (36 procedures, LLM-titled)
- MCP server live (4 read-only tools)
- Clean rebuild done (1,028 units, no duplication)
- OOM root causes fixed (deterministic IDs, upsert, memory caps, live-DB skip)

**Open strategic questions:**
- `propose_decision` MCP write tool — how to gate human confirmation from within an agent session?
- Per-client decision logs (site-tagged rationale for web clients)
- Web retrieval + local context hybrid (convmem first, web fallback)
- Procedure-to-decision linking (Crush sessions → which decision was implemented?)

**Corpus profile:** coding.ml 336, coding.tooling 266, coding.devops 223, general 215, web_stack.* 248. First site: staging2.willowyhollow.com.

---

## Architecture (quick reference)

```
Source files → adapters/detect.py → parser → ingest.py
  → chunk → summarize (Ollama/DeepSeek) → embed (nomic-embed-text) → Chroma
  → distill → knowledge_units (deterministic IDs, upsert)

Ledger path (tools/scanners):
  JSONL → observe.py → normalize_ledger_record → embed → Chroma (upsert)
  Evidence chain: observation → decision (with rationale) → verification

Query:
  convmem "query" → embed → Chroma cosine → [rerank if enabled] → Rich display
  convmem ask → retrieve → DeepSeek synthesis → cited answer
  convmem related → build_ledger_index() → graph traversal

MCP:
  mcp_server.py → FastMCP stdio → search_fast | ask | related | stats
  ask degrades to raw retrieval on timeout/error

Always-on:
  watch (inotify → incremental index, disabled pending stability check)
  refine (dedupe, audit, link — 5-min cycle)
  monitor (hourly HTTP header probes → verifications)
```

---

## Files changed since initial commit

| Commit | What |
|--------|------|
| `9a226f7` | Handoff MCP detail for Sonnet |
| `d2b17d7` | Refine MCP tools + parameterize timeouts |
| `ae104b4` | MCP ask graceful degradation |
| `0c8ed9b` | **Root cause fix:** deterministic IDs + upsert |
| `30efb20` | Rerank CUDA→CPU fallback + count_units fix |
| `fb0ce33` | Path-based skip + OOMPolicy |
| `85c5f88` | MCP server + agent rules + memory cap |
| `17ee28f` | Cursor store.db adapter + procedures |
| `c176336` | Procedure extraction from Crush |
| `305013b` | Initial commit (everything through F2c) |

---

## How to use convmem (for any agent with shell access)

```bash
source ~/.config/convmem/env.local
convmem "nginx csp staging2"                    # search
convmem ask "why nginx not WPCode for CSP?"     # RAG
convmem ask "unresolved issues?" --evidence     # evidence-aware
convmem related obs_staging2_wpsec_csp-missing  # graph
convmem stats                                   # overview
convmem exclude PATH --reason "noise"           # skip file
```

**Rule:** Read tools are free. Write tools (`add`, `index`, `verify`, `exclude`) require user direction.
