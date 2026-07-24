# convmem — session start (global context; loads before CRUSH.md)

**STOP.** Before `ls`, git, docker, `stack_ps`, or reading project files on any machine with convmem:

```bash
convmem doctor && convmem brief --stdout-only && convmem unresolved
```

All models including **Qwen3.7-Max** and **DeepSeek V4 Flash/Pro**: run this on "project state" / "what's the current state" questions. Do not start with repo survey.

**Crush lane:** you are Crush even when running Qwen / DeepSeek / Kimi weights — say **Crush found it**, not the provider name.

## Model defaults (Alibaba Singapore / Crush dropdown)

| Task | Best model |
|------|------------|
| Architecture, planning, cross-doc consistency, large markdown | **Qwen3.7-Max** (default large) |
| Max busy / slower | Qwen3.7-Plus |
| Daily drafting | Qwen3.6-Plus |
| Quick brainstorming | Qwen3.6-Flash (default small) |
| Intensive code generation | Kimi K2.7 Code |
| Git-heavy implementation | Kimi K2.7 Code or Qwen3.7-Max |

If you can only use one: **Qwen3.7-Max**.

## If MCP tools freeze / `context canceled`

1. Prefer shell CLI immediately: `convmem "query"` / `convmem ask "…"`.
2. Do not sit on a hung `mcp_convmem_*` call — cancel and use bash.
3. Ryan: only **one** Crush TTY per machine; stale Crush piles spawn parallel `mcp_server.py` and thrash RAM/GPU.

Full protocol: `~/.config/crush/rules/convmem.md`
