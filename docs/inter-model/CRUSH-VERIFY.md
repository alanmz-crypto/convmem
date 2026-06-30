# Crush + convmem verification

**Updated:** 2026-06-25

## Alien-workspace soak

Dir: `~/WordPress/willowyhollow-practice/` or `~/WordPress/pavlomassage-practice/`

Prompt (unprompted): *What's the current state of this project?*

**Pass:** `convmem doctor` → `brief` → `unresolved` (shell) before `stack_ps` / git / docker / repo reads.

**Config:** `~/.config/crush/CONVMEM-RITUAL.md` (**first** in `global_context_paths`, before ponytail `CRUSH.md`) + `rules/convmem.md` + MCP + permissions hook.

## Model matrix (Crush)

| Model | Alien soak | Notes |
|-------|------------|-------|
| **qwen3-coder:30b** (local) | Recommended | Best tool + rule following for protocol soak |
| **DeepSeek V4 Flash** | Mixed | PASS when rules salient (#9, willowyhollow 2026-06-28); FAIL bash-only (#6, #8) |
| **DeepSeek V4 Pro** | **PASS (hook + restart)** | Pre-restart FAIL: ComfyUI 21:35:33 `git`/`ls` first, `crush.log` `decision:none`. Post-restart PASS: 23:02:28 session `b8f40eaa` — first tool `convmem doctor && brief && unresolved`, debug log `ritual complete` build `v3-20260628` |
| DeepSeek R1 | untested | |

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
