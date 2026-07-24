# convmem — session start (global context; loads before CRUSH.md)

**STOP.** Before `ls`, git, docker, `stack_ps`, or reading project files on any machine with convmem:

```bash
convmem doctor && convmem brief --stdout-only && convmem unresolved
```

All models including **Qwen3.7-Max** and **DeepSeek V4 Flash/Pro**: run this on "project state" / "what's the current state" questions. Do not start with repo survey.

**Crush lane:** you are Crush even when running Qwen / DeepSeek / Kimi weights — say **Crush found it**, not the provider name.

## Model defaults (billing-cycle coverage)

When Cursor (or other IDE) tokens are exhausted, **stay on Crush** — do not wait
for a refresh. Prefer Qwen headroom; also use DeepSeek V4 so that quota covers
ConvMem work through the month.

| Task | Best model |
|------|------------|
| Architecture, planning, cross-doc, large markdown | **Qwen3.7-Max** (default large, Alibaba Singapore) |
| Max busy / slower | Qwen3.7-Plus |
| Daily drafting | Qwen3.6-Plus |
| Quick brainstorming | Qwen3.6-Flash (default small) |
| Cursor dry + need another cloud budget | **DeepSeek V4 Pro** (or V4 Flash) via Crush |
| Intensive code generation | Kimi K2.7 Code |
| Git-heavy implementation | Kimi K2.7 Code or Qwen3.7-Max |

If you can only use one: **Qwen3.7-Max**. Second seat: **DeepSeek V4 Pro**.

## Crush + ConvMem tools (2026-07-24)

**Prefer shell `convmem` for reads.** Keep tools under Crush’s ~60s bash budget.

1. After ritual: `convmem "query"` / `convmem ask "…"` (or MCP if enabled).
2. **Do not** run `convmem index` / `add` / `verify` inside Crush bash — those exceed
   ~60s, freeze the UI on “waiting for tool”, and leave a child running. Track A
   handoff: run the index command in an **external** shell, or rely on watch
   auto-index. The PreToolUse hook denies in-Crush index/add/verify.
3. If UI says “waiting for tool” >30s: cancel (Esc), prune extra TTYs
   (`bash ~/Projects/convmem/scripts/prune-stale-crush.sh`), retry with one Crush.
4. Only **one** Crush TTY at a time.

Full protocol: `~/.config/crush/rules/convmem.md`
