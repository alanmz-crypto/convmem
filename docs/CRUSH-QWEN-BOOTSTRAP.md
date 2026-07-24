# Crush + Qwen3.7-Max — session bootstrap

**For Ryan:** Prefer this over Cursor when IDE tokens are low or exhausted.
Paste as the **first message** in a new Crush session with
**Alibaba (Singapore) → Qwen3.7-Max** selected (large model).

Also keep **DeepSeek V4 Pro/Flash** in the Crush dropdown — when Qwen is busy or
you want to burn DeepSeek quota, use
[`CRUSH-DEEPSEEK-BOOTSTRAP.md`](CRUSH-DEEPSEEK-BOOTSTRAP.md) (still Crush lane).

---

```
You are Qwen3.7-Max inside Crush (Crush lane) on Ryan's dev machine.

Before answering anything:

1. Run: convmem doctor && convmem brief --stdout-only && convmem unresolved
2. For ledger facts use shell only (Crush MCP is disabled — it hung on tools/call):
   convmem "query" / convmem ask "…"
   Do not call mcp_convmem_* or wait on MCP tools.
3. Stay on Qwen3.7-Max for architecture / planning / cross-doc work.
   Switch to Kimi K2.7 Code only for intensive code generation.
   If Qwen is busy or Ryan wants DeepSeek budget used: switch Crush model to
   DeepSeek V4 Pro (or Flash) — still Crush lane ("Crush found it").

Your lane: Crush — bug discovery / investigation and ConvMem synthesis.
Say "Crush found it" — not "Qwen found it."

Then wait for my question.
```

---

## Model matrix (same machine)

| Task | Model |
|------|--------|
| Architecture / planning OS / cross-doc / large markdown | Qwen3.7-Max |
| Max busy | Qwen3.7-Plus |
| Daily drafting | Qwen3.6-Plus |
| Quick brainstorm | Qwen3.6-Flash |
| Cursor dry / second cloud budget | DeepSeek V4 Pro (or Flash) |
| Code generation | Kimi K2.7 Code |

Runtime defaults live in `~/.local/share/crush/crush.json` (`large` /
`small`). Ritual copy: `~/.config/crush/CONVMEM-RITUAL.md` (from
`config/crush-global-convmem-ritual.example.md`).

Billing-cycle cheat sheet: [`docs/MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md) §
*Billing-cycle model routing*.

**Crush MCP:** keep `mcp.convmem.disabled = true` (2026-07-23 timed probe
**FAIL** — shell only). Re-check: `bash scripts/probe-crush-mcp-tools-call.sh`
(see [`inter-model/CRUSH-VERIFY.md`](inter-model/CRUSH-VERIFY.md)).

## Related

- DeepSeek paste (coverage / second budget): [`CRUSH-DEEPSEEK-BOOTSTRAP.md`](CRUSH-DEEPSEEK-BOOTSTRAP.md)
- Soak / verify: [`inter-model/CRUSH-VERIFY.md`](inter-model/CRUSH-VERIFY.md)
