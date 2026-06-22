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

Read-only. Do not run convmem add/index/verify without user direction.
