# Cursor → Ryan, DeepSeek: large-context session file ready

**To:** Ryan, DeepSeek  
**From:** Cursor  
**Date:** 2026-06-22  

## File to give DeepSeek v4 Pro

**Crush (local):** paste `docs/CRUSH-DEEPSEEK-BOOTSTRAP.md` as first message — it tells DeepSeek to `cat ~/.local/share/convmem/deepseek-session-context.md` + `convmem brief`.

**Cloud paste (optional):** `docs/DEEPSEEK-SESSION-CONTEXT.md`

Stable path on disk: `~/.local/share/convmem/deepseek-session-context.md` (copy of repo file).

Context file includes: role instructions, architecture, chronology, live snapshot, propose_decision summary, suggested prompts.

Per Codex `deepseek-context-assessment`: use 1M context for **history synthesis**, not repo bulk-load.

## Optional tar (if upload size matters)

```bash
tar -czf ~/Projects/convmem-deepseek-context.tar.gz \
  -C ~/Projects/convmem/docs \
  DEEPSEEK-SESSION-CONTEXT.md \
  PROPOSE-DECISION-SPEC.md \
  WORKSPACE-STANDARD.md \
  CHROMA-ACCESS-PATTERN.md \
  AGENT-ROLES.md
```

## Refresh

Ask Cursor to regenerate after soak pass or major ship.

— Cursor
