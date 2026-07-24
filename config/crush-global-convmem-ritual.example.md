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

## Crush + ConvMem tools (2026-07-23)

**Use shell `convmem`, not MCP.** Crush’s MCP client has hung 10–15+ minutes on
`mcp_convmem_search_fast` while the stdio server sat idle — so `mcp.convmem` is
**disabled** in `~/.config/crush/crush.json` until that client path is fixed.

1. After ritual: `convmem "query"` / `convmem ask "…"`.
2. If UI says “waiting for tool” >30s: cancel (Esc) and retry via bash.
3. Only **one** Crush TTY; prune with `bash ~/Projects/convmem/scripts/prune-stale-crush.sh`.

Full protocol: `~/.config/crush/rules/convmem.md`
