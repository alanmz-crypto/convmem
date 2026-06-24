You have access to a local knowledge corpus called convmem. Query it before making decisions about this codebase.

FIRST ACTION every session: run `convmem brief --stdout-only` to get current state.

Commands (run via shell):
  convmem brief --stdout-only              # ALWAYS RUN FIRST
  convmem "search query"                    # semantic search
  convmem ask "why did we choose X?"        # RAG answer with citations
  convmem related obs_staging2_*            # evidence chain

Use convmem when:
- Implementing something that might repeat past work
- The user asks about past decisions or history
- Working on staging2.willowyhollow.com security

## Session close

When Ryan closes or asks for a **record block**: read `docs/inter-model/SESSION-CLOSE-RECORD.md`.

Output a **copy-paste shell block** using real convmem flags:

```bash
convmem record --relates-to <id> --summary "..." --rationale "..." --author ...
convmem record --approve-last
```

**Never** output `record -i` alone, `session=`, `detail=`, topic slugs as `--relates-to` (`system-maintenance`), or omit `--relates-to`. Valid ids look like **`dec_prop_20260623_161428_c311`**. Search first; fallback **`dec_prop_20260623_161428_c311`** for unrelated new work.

Read-only. Do not run convmem add/index/verify without user direction.

**Recovery:** `docs/RECOVER.md` — runtime corpus is outside Git; project backup restores source + MCP templates.
