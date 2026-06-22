# Sonnet MCP verification bundle

Generated on dev machine after rebuild completed.

## Rebuild status

- **PID 1128957:** finished (no longer running)
- **Corpus:** 1028 units, 263 summaries
- **processed.json:** 121/122 inventory files (1 skipped: empty-window agent-transcript jsonl)
- **Log:** `rebuild-20260619-0629.log` — ends with `Done. files_processed=121 files_skipped=1`

## Authoritative MCP facts (use these, not stale sections)

| Setting | Value |
|---------|--------|
| Crush timeout | **120** s |
| Protocol (Crush client) | **2025-11-25** |
| Crush tool prefix | `mcp_convmem_<tool>` |
| ask synthesis timeout | **45** s internal |
| MCP tools | search_fast, search, ask, related, stats |

Duplicate bottom section "MCP Server (Sonnet's area)" was **removed** from HANDOFF-GREENFIELD.md.

## Files in tar

| File | Notes |
|------|--------|
| `mcp_server.py` | FastMCP stdio server |
| `ask.py`, `llm.py`, `query.py` | ask fallback + timeouts |
| `chroma_store.py`, `config.py` | Chroma + config load |
| `crush.json.global` | `~/.config/crush/crush.json` — API key **redacted** |
| `crush.json.local-share` | `~/.local/share/crush/crush.json` (secondary) |
| `config.toml` | live convmem config |
| `continue-mcp-convmem.json` | Continue MCP registration |
| `docs/HANDOFF-GREENFIELD.md` | greenfield handoff |

## P0 verification (on dev machine with Ollama up)

1. stdio `tools/list` → 5 tools
2. Crush restart → call `mcp_convmem_search_fast`
3. `ask` → confirm `synthesis_failed` path if DeepSeek slow
4. `pkill -f mcp_server.py` if stale Cursor MCP process

## Not in tar (on dev machine only)

- Live Chroma at `~/.local/share/convmem/chroma/`
- `~/.cursor/mcp.json`
- No Crush MCP connection logs in `~/.local/share/convmem/logs/` (only index logs)
