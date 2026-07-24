# Crush + DeepSeek V4 — session bootstrap

**When to use:** Cursor tokens are exhausted, Qwen is busy/slow, or you want to
**burn DeepSeek V4 quota** on ConvMem work this billing cycle. Still **Crush
lane** — not a separate DeepSeek lane.

Default lead remains Qwen3.7-Max:
[`CRUSH-QWEN-BOOTSTRAP.md`](CRUSH-QWEN-BOOTSTRAP.md).

**For Ryan:** Paste as the **first message** with Crush model
**DeepSeek → deepseek-v4-pro** (or **deepseek-v4-flash** for cheaper/faster).

---

```
You are DeepSeek V4 Pro inside Crush (Crush lane) on Ryan's dev machine.

Before answering anything:

1. Run: convmem doctor && convmem brief --stdout-only && convmem unresolved
2. For ledger facts use shell only (Crush MCP is disabled):
   convmem "query" / convmem ask "…"
   Do not call mcp_convmem_* or wait on MCP tools.
3. You are covering ground while Cursor/other IDE quotas are thin.
   Say "Crush found it" — not "DeepSeek found it."

Your lane: Crush — bug discovery / investigation and ConvMem synthesis.
Watch soak is active — do not restart convmem-watch or run mass index.

Then wait for my question.
```

---

## Paths

| File | Purpose |
|------|---------|
| `~/.local/share/convmem/deepseek-session-context.md` | Optional stable context copy |
| `~/Projects/convmem/docs/DEEPSEEK-SESSION-CONTEXT.md` | Repo canonical — edit here, re-copy to data dir |
| [`docs/MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md) | Billing-cycle routing (Qwen + DeepSeek) |

## Refresh context file (optional)

```bash
cp ~/Projects/convmem/docs/DEEPSEEK-SESSION-CONTEXT.md \
   ~/.local/share/convmem/deepseek-session-context.md
```

## Note on MCP

Crush ConvMem MCP is **disabled** until tools/call no longer hangs. Use shell
`convmem` only. See [`inter-model/CRUSH-VERIFY.md`](inter-model/CRUSH-VERIFY.md).
Re-probe: `bash scripts/probe-crush-mcp-tools-call.sh` (always restores disabled).

## Note on raw API smokes

DeepSeek V4 chat completions may return empty `message.content` with the answer
in `reasoning_content`. Crush tool turns still work; do not treat empty `content`
alone as a failed API key when HTTP 200 and reasoning text are present.
