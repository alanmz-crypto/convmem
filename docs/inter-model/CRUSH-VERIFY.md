# Crush + convmem verification

**Updated:** 2026-07-23

## Alien-workspace soak

Dir: `~/WordPress/willowyhollow-practice/` or `~/WordPress/pavlomassage-practice/`

Prompt (unprompted): *What's the current state of this project?*

**Pass:** `convmem doctor` → `brief` → `unresolved` (shell) before `stack_ps` / git / docker / repo reads.

**Config:** `~/.config/crush/CONVMEM-RITUAL.md` (**first** in `global_context_paths`, before ponytail `CRUSH.md`) + `rules/convmem.md` + MCP + permissions hook.

## Model matrix (Crush)

| Model | Role | Notes |
|-------|------|-------|
| **Qwen3.7-Max** (Alibaba Singapore) | **Default large / lead architect** | Best for ConvMem architecture, planning, cross-doc, long reasoning. Prefer this. |
| **Qwen3.7-Plus** | Fallback large | When Max is busy or slower |
| **Qwen3.6-Plus** | Daily drafting | Balanced |
| **Qwen3.6-Flash** | Default small | Fast brainstorm / light turns |
| **Kimi K2.7 Code** | Coding specialist | Intensive implementation; not default for governance |
| **qwen3-coder:30b** (local Ollama) | Offline soak | Best local tool + rule following when cloud unavailable |
| **DeepSeek V4 Flash** | Legacy | Mixed soak; prefer Qwen3.7-Max |
| **DeepSeek V4 Pro** | Legacy | PASS with hook + restart historically; prefer Qwen3.7-Max |

Bootstrap paste: [`docs/CRUSH-QWEN-BOOTSTRAP.md`](../CRUSH-QWEN-BOOTSTRAP.md).

### Freeze / MCP hang checklist (2026-07-23)

Symptoms: UI stuck on `mcp_convmem_*`; `crush.log` shows `MCP client failed to initialize` / `context canceled`.

Likely causes:

1. **Many Crush TTYs** — each spawns `mcp_server.py`; prune to one Crush.
2. **Swap pressure** — full swap + heavy refine/Kiro MCP on GPU makes search feel frozen.
3. **MCP timeout** — `~/.config/crush/crush.json` `mcp.convmem.timeout` should be ≥180s.

Mitigation for the model: cancel hung MCP → use shell `convmem` / `convmem ask`.

## If DeepSeek V4 Pro skips convmem

1. Deploy: `bash ~/Projects/convmem/scripts/deploy-agent-protocol.sh`
2. **Reload hooks:** `bash ~/Projects/convmem/scripts/restart-crush-if-stale.sh` then start Crush (hooks load at process start only)
3. Confirm hooks in `crush.json`: 8 matchers → `hooks/convmem-allow.sh`
4. Optional clean slate: `rm -rf ~/.cache/convmem-crush-ritual/`
5. After soak: `grep 'decision.*deny' ~/…/.crush/logs/crush.log` or check first tools in `crush.db` for `convmem doctor`

## Session evidence (crush.db)

```bash
sqlite3 ~/WordPress/willowyhollow-practice/.crush/crush.db \
  "SELECT model, substr(parts,1,200) FROM messages WHERE role='assistant' ORDER BY created_at DESC LIMIT 3;"
```

Look for `convmem doctor` / `brief` in first tool calls vs `git`/`ls`/`stack_ps`.
