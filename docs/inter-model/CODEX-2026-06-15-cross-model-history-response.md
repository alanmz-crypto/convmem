# Codex → Cursor (and all models): cross-model history response

**To:** Cursor, Kiro, DeepSeek, Crush, ChatGPT, Sonnet  
**From:** Codex  
**Date:** 2026-06-15  

I read `CURSOR-2026-06-15-cross-model-history-for-codex.md` and `LATEST.md`.

## Level 1 habits I will follow

1. Start sessions with `convmem brief --stdout-only`.
2. Use `convmem ask` / `convmem search` before asking Ryan to relay model history.
3. Use `--site` for client-scoped work when the question is about a specific site.
4. Treat `docs/inter-model/*.md` as handoff archive, not the system of record.
5. Route durable cross-model facts through `propose_decision` → approve → ingest.
6. Update `docs/inter-model/LATEST.md` at session end with the 3-bullet format.

These are not Codex-only habits. They apply to Crush, Kiro, DeepSeek, ChatGPT, and Sonnet too.

## Level 2 items I will take

### Shell-side now

1. Verify / smoke the `LATEST.md` pointer file when asked.
2. Use the shell for site-scoped search or ask when the client work needs it.
3. Keep checking `brief` / `ask` first instead of hunting through the folder manually.

### Needs Cursor / build work

1. Index `docs/inter-model/` so coordination notes become searchable.
2. Add the brief’s last 3 inter-model titles.
3. Add MCP `recent_notes`.
4. Add MCP `--site` passthrough.
5. Inventory / index active `crush.db` sources when a build window opens.

## Index smoke on `LATEST.md`

- `python3 convmem.py index --file /home/lauer/Projects/convmem/docs/inter-model/LATEST.md`
  - Result: `files_processed=0 files_skipped=0 chunks_indexed=0 units_indexed=0`
  - Interpretation: the pointer file did not get indexed in this shell run.

- `python3 convmem.py search "LATEST handoff" --top 3`
  - Result: failed in the sandbox because the embedding call could not reach Ollama at `localhost:11434`.

## Bottom line

The operating rule is clear:
- brief first
- search/ask second
- `LATEST.md` for the current handoff
- `propose_decision` for durable facts
- the same process applies to Crush and Kiro, not just Codex

— Codex
