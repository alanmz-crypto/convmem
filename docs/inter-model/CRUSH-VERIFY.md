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

Symptoms: UI stuck on “waiting for tool” 10–15+ min; last log line often
`PreToolUse` `mcp_convmem_search_fast` with no tool result; MCP child ~60 MB
RSS idle on stdin (`anon_pipe_read`) — Crush never completes `tools/call`.

**Mitigation (applied):** `mcp.convmem.disabled = true` in
`~/.config/crush/crush.json`. Crush uses shell `convmem` only. Hook
`search_first` message steers to bash, not MCP.

Also:

1. **Many Crush TTYs** — prune with `scripts/prune-stale-crush.sh`.
2. **Swap pressure** — full swap + Kiro MCP on GPU (~2.8 GB) worsens hangs.
3. Re-enable MCP only after a timed Crush soak proves `search_fast` returns.

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
