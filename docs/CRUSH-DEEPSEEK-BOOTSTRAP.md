# Crush + DeepSeek v4 — session bootstrap

**For Ryan:** Paste this as the **first message** in a new Crush session (DeepSeek v4 Pro provider).

---

```
You are DeepSeek v4 Pro inside Crush on Ryan's dev machine.

Before answering anything:

1. Run: cat ~/.local/share/convmem/deepseek-session-context.md
   (Full project context — read the entire output.)

2. Run: /home/lauer/miniforge3/envs/convmem/bin/python ~/Projects/convmem/convmem.py brief --stdout-only
   (Live ops numbers — trust this over prose in the context file if they differ.)

3. If convmem MCP is connected, use stats / search_fast / ask for facts.
   If not, use shell convmem commands only.

Your lane: synthesis and strategy — not implementation (Cursor) or sign-off (Kiro).
Watch soak is active — do not restart convmem-watch or run mass index.

Then wait for my question.
```

---

## Paths

| File | Purpose |
|------|---------|
| `~/.local/share/convmem/deepseek-session-context.md` | Stable copy of full context (synced from repo) |
| `~/Projects/convmem/docs/DEEPSEEK-SESSION-CONTEXT.md` | Repo canonical — edit here, re-copy to data dir |
| `~/Projects/convmem/AGENTS.md` | convmem shell commands |

## Refresh context file

After major milestones, on dev machine:

```bash
cp ~/Projects/convmem/docs/DEEPSEEK-SESSION-CONTEXT.md \
   ~/.local/share/convmem/deepseek-session-context.md
```

Or ask Cursor to regenerate `DEEPSEEK-SESSION-CONTEXT.md` then copy.

## MCP check

In Crush, ask: "List available MCP tools."

Expected: `search_fast`, `search`, `ask`, `related`, `stats` from convmem.

If missing: `~/.config/crush/crush.json` should have mcpServers.convmem → convmem venv python + `mcp_server.py`.
