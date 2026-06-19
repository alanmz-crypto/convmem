# Handoff for Claude: Crush MCP Server Not Connecting

## Problem

We built a convmem MCP server (`mcp_server.py`) using Python's `mcp` SDK (v1.28.0, FastMCP, stdio transport). It works correctly when tested from the command line and connects fine with Cursor. However, Crush sees the config but reports "not connected/loaded in this session."

## What works

- Server responds correctly to MCP protocol over stdio (initialize, tools/list)
- Cursor picks it up from `~/.cursor/mcp.json`
- Python env path is valid: `/home/lauer/miniforge3/envs/convmem/bin/python`
- Server file: `/home/lauer/Projects/convmem/mcp_server.py`

## What doesn't work

Crush (installed via `/usr/bin/crush` on Arch Linux) sees the server in config but won't connect to it. Deepseek running in Crush reported: "Yes, one MCP server is configured — convmem (stdio transport, mcp_server.py). It's not currently connected/loaded in this session though."

## Current Crush MCP config

In `~/.config/crush/crush.json`:

```json
{
  "$schema": "https://charm.land/crush.json",
  "providers": { ... },
  "mcpServers": {
    "convmem": {
      "command": "/home/lauer/miniforge3/envs/convmem/bin/python",
      "args": ["/home/lauer/Projects/convmem/mcp_server.py"],
      "transport": "stdio"
    }
  }
}
```

## What we tried

- Full Crush restart (exit terminal, reopen)
- `/mcp connect convmem` — Crush says "Unknown command mcp"
- `crush mcp --help` — "Unknown command mcp for crush"
- `crush dirs` shows config at `~/.config/crush` (correct location)
- The config file is definitely being read (Crush knows the server name)

## Questions for Claude

1. What's the correct Crush MCP config format for stdio servers? Is `mcpServers` the right top-level key, or does Crush use a different key name?
2. Does Crush auto-connect MCP servers on startup, or does the model/session need to explicitly request it?
3. Is there a Crush version requirement for MCP support? (`/usr/bin/crush` on Arch, installed via pacman or AUR)
4. Does Crush need `"enabled": true` or some activation flag in the server config?
5. Is there a log we can check for MCP connection errors? (`crush server` runs a unix socket at `/run/user/1000/crush-1000.sock`)

## Environment

- OS: Arch Linux
- Crush: `/usr/bin/crush` (version unknown — `crush --version` not available)
- Python: 3.11.15 in mamba env
- MCP SDK: 1.28.0 (Python `mcp` package, FastMCP)
- Server transport: stdio
- Crush server socket: `unix:///run/user/1000/crush-1000.sock`

## The server itself (for reference)

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("convmem", instructions="Local knowledge corpus...")

@mcp.tool()
def search(query: str, top_k: int = 5, domain: str = "") -> str: ...

@mcp.tool()
def ask(question: str, ...) -> str: ...

@mcp.tool()
def related(ledger_id: str) -> str: ...

@mcp.tool()
def stats() -> str: ...

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())
```

Verified working via manual stdio test:
```
printf '{"jsonrpc":"2.0","id":1,"method":"initialize",...}\n' | python mcp_server.py
→ responds with server capabilities + 4 tools
```
