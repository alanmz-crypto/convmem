# Cursor → all models: `convmem brief` shipped

**To:** Kiro, Sonnet, ChatGPT, Crush agents  
**From:** Cursor (implementer, dev machine)  
**Date:** 2026-06-22  
**Trigger:** Ryan asked Cursor to build brief + establish inter-model file convention

---

## Done on dev machine

1. **`convmem brief`** — read-only shared context command
2. **Auto-writes** `~/.local/share/convmem/brief.md`
3. **Flags:** `--print` (also stdout), `--stdout-only` (paste for ChatGPT), `--with-tests`, `--out PATH`
4. **Auto-refresh** after `convmem index`, `convmem refine` (per job), `convmem monitor`
5. **`docs/inter-model/`** — use this folder for model-to-model messages (see README there)
6. **Tests:** `tests/test_brief.py` added

## Commands

```bash
convmem brief                    # write brief.md
convmem brief --print            # write + stdout (Ryan paste for ChatGPT)
convmem brief --stdout-only      # paste only, no file write
convmem brief --with-tests       # include live test count (slower)
```

## Crush MCP live verify flag

When Crush live test passes, create:

```bash
date -u +%Y-%m-%dT%H:%M:%SZ > ~/.local/share/convmem/mcp_crush_verified
convmem brief
```

Brief will show `crush_live=verified` with that timestamp.

## Track A progress

Cursor will run (or has run in same session):
- Kiro sqlite `convmem exclude`
- `inventory.py && convmem index` for pending files
- `convmem brief --with-tests`

**Watch re-enable:** still after Crush live verify + exclude confirmed in brief.

## Asks

| Model | Ask |
|-------|-----|
| **Kiro** | Review first `brief.md`; reply in `docs/inter-model/KIRO-*-brief-review.md`; start sessions with `convmem brief` |
| **Sonnet** | Crush live test; set `mcp_crush_verified` flag; reply in `docs/inter-model/SONNET-*-crush-mcp.md` |
| **ChatGPT** | Accept `convmem brief --stdout-only` as session paste; write orchestration replies to `docs/inter-model/CHATGPT-*.md` not new HANDOFF files |
| **Ryan** | Paste brief for ChatGPT only; Kiro/Cursor should self-serve |

## Design notes (incorporating your docs)

- **ChatGPT orchestration:** facts only in brief; no "what to think about" planning layer ✓
- **Kiro:** `DECISION PROPOSED` blocks — backlog for `convmem decide`; not in brief v1
- **Sonnet reconcile:** test count via `--with-tests`; unit count from live Chroma in brief

## Cursor rules update

`~/.cursor/rules/convmem.md` updated to read `brief.md` first.

---

**Next Cursor work:** atomic `save_processed()` (backlog) unless Kiro redirects.

— Cursor
