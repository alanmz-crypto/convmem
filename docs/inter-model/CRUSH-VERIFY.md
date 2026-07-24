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
| **DeepSeek V4 Pro** | **Second cloud budget** | Use when Cursor is dry or Qwen busy — burn DeepSeek quota; still Crush lane |
| **DeepSeek V4 Flash** | Cheap/fast Crush seat | Same coverage role as Pro; historically mixed soak |
| **Kimi K2.7 Code** | Coding specialist | Intensive implementation; not default for governance |
| **qwen3-coder:30b** (local Ollama) | Offline soak | Best local tool + rule following when cloud unavailable |

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
3. Re-enable MCP only after a timed Crush soak proves `search_fast` / `stats` returns.
4. Repeatable probe: `bash scripts/probe-crush-mcp-tools-call.sh` (always restores
   `disabled=true`; do not treat a green run as auto-enable).

### Post-#106 optional soaks (2026-07-23 ~22:20 local)

| Check | Result | Evidence |
|-------|--------|----------|
| DashScope `qwen3.7-max` API smoke | **PASS** | ~4.4 s → `DASHSCOPE_OK` |
| DeepSeek V4 Flash/Pro API smoke | **PASS*** | HTTP OK; `content` often empty — answer in `reasoning_content` |
| Crush `deepseek-v4-flash` shell ritual | **PASS** | `crush run` → bash `convmem doctor` → `SOAK_OK` ~8 s |
| Crush MCP `tools/call` (hook-allow + enabled) | **FAIL** | PreToolUse **allow** on `mcp_convmem_stats`, then **50 s watchdog** — no `tool_result` in `crush.db` |
| False-positive trap | noted | Ritual-incomplete deny → model prints `MCP_PROBE_OK` without a real call — require DB `tool_result` not blocked |

**Keep `mcp.convmem.disabled=true`.** Crush permissions now also allow `bash` + `view` (runtime).

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
