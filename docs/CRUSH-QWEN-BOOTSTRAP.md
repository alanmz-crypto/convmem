# Crush + Qwen3.7-Max — session bootstrap

**For Ryan:** Prefer this over DeepSeek for ConvMem architecture, planning, and
document synthesis. Paste as the **first message** in a new Crush session with
**Alibaba (Singapore) → Qwen3.7-Max** selected (large model).

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
| Code generation | Kimi K2.7 Code |

Runtime defaults live in `~/.local/share/crush/crush.json` (`large` /
`small`). Ritual copy: `~/.config/crush/CONVMEM-RITUAL.md` (from
`config/crush-global-convmem-ritual.example.md`).

**Crush MCP:** `mcp.convmem.disabled = true` until a timed soak proves
`search_fast` returns (see [`inter-model/CRUSH-VERIFY.md`](inter-model/CRUSH-VERIFY.md)).

## Related

- DeepSeek paste (legacy): [`CRUSH-DEEPSEEK-BOOTSTRAP.md`](CRUSH-DEEPSEEK-BOOTSTRAP.md)
- Soak / verify: [`inter-model/CRUSH-VERIFY.md`](inter-model/CRUSH-VERIFY.md)
