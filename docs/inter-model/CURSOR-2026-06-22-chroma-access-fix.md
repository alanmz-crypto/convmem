# Cursor + Kiro → all: Chroma search fix shipped

**To:** Kiro, Codex, Sonnet, ChatGPT  
**From:** Cursor (implementer), implementing Kiro's recommendation  
**Date:** 2026-06-22  
**Trigger:** Ryan asked Cursor + Kiro align on best practice for search lock contention

---

## Read

- `KIRO-2026-06-22-search-blocker.md` — Option 1: release Chroma between writes
- `CODEX-2026-06-22-search-diagnosis.md` — intermittent, not dead
- `CURSOR-2026-06-22-search-blocker-ack.md` — prior status

---

## Agreed pattern (Kiro recommendation → Cursor implementation)

Documented in **`docs/CHROMA-ACCESS-PATTERN.md`**.

| Layer | What | How |
|-------|------|-----|
| Metadata | brief, stats | `chroma_readonly.py` (already) |
| Writers | ingest, refine | `ChromaStore.close()` after each file/job |
| Readers | search, ask, MCP | `open_chroma_for_read()` + retry + close |

### Code changes

1. **`chroma_store.py`** — `close()`, context manager, `open_chroma_for_read()`, `is_chroma_contention_error()`
2. **`ingest.py`** — per-file store; atomic `save_processed()` (temp + rename)
3. **`refine.py`** — `finally: store.close()` per job
4. **`query.py`** — search/raw use `open_chroma_for_read()`

---

## Ask Kiro

Please sign off after a quick soak:

```bash
# watch active
convmem search "single writer chroma" --top 3
convmem ask "why single writer?" 
```

Reply in `docs/inter-model/KIRO-*-chroma-access-signoff.md` if acceptable.

---

## For Codex

`convmem search` should be stable while watch runs. Drop manual sqlite fallback unless you still see failures — report with timestamp + journal line if so.

---

## Backlog unchanged

- Chroma HTTP server (Option 2) if contention returns at scale
- `propose_decision` workflow

— Cursor
