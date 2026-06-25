# Chroma access pattern (Cursor + Kiro, 2026-06-22)

**Status:** Implemented  
**Signed by:** Kiro (recommendation), Cursor (implementation)

---

## Problem

Single-writer Chroma (`dec_convmem_single_writer_chroma`) with multiple processes opening `PersistentClient` on the same path:

- **brief/stats** — metadata only → fixed via `chroma_readonly.py` (sqlite read)
- **search/ask/MCP** — needs HNSW vector query → must use `PersistentClient`
- **watch/refine/ingest** — writers hold sqlite lock during index bursts

Symptom: intermittent `readonly database` / lock errors when search collides with watch.

---

## Best practice (three layers)

### Layer 1 — Metadata reads (no PersistentClient)

Use `chroma_readonly.collection_count()` / `collection_metadata_rows()` / `ReadonlyUnitStore` for:

- `convmem brief`
- `convmem stats` (counts + breakdown tables)
- `convmem unresolved` (ledger graph over metadata rows)
- `convmem related --ledger-id …` (metadata-only related lookup)

### Layer 2 — Writers: short-lived client

**Rule:** Open `ChromaStore` only for the write burst; call `store.close()` before sleeping.

| Process | Pattern |
|---------|---------|
| `ingest.index` | **Per chunk:** LLM work first, then `with ChromaStore()` for summary + units only |
| `ingest.index` | `force_file` delete uses one short `with ChromaStore()` |
| `refine.run_job` | `try/finally: store.close()` after each job |
| `watch` | Skips live DBs (`kiro sqlite`, `cursor .../chats/.../store.db`); delegates to ingest |

Also: **atomic `save_processed()`** (write temp + rename).

**Watch memory:** `MemoryMax=4G`, `MemoryHigh=3G`, `MemorySwapMax=0`, `OOMPolicy=stop`. Debounce default **90s**.

### Layer 3 — Readers: short-lived client + retry

**Rule:** `open_chroma_for_read()` opens client, probes, retries on contention, closes in `finally`.

Used by:

- `query_units` / `query_raw`
- MCP `search` / `search_fast` / `ask` (via query layer)

Retries: 5 attempts, 150ms backoff steps.

---

## Not chosen (documented for later)

| Option | Why deferred |
|--------|----------------|
| Chroma HTTP server | More moving parts; revisit if contention persists |
| Python cosine over sqlite embeddings | No HNSW; too slow at scale |
| Second Chroma copy for reads | Violates single-writer decision |

---

## Verification

```bash
# While watch is active:
convmem search "wordpress staging2 security" --domain web_stack.security --top 5
convmem brief --stdout-only
python -m unittest discover -s tests -q
```

---

## For models

- **Kiro:** Search is reliable when writers release clients — sign off after soak test
- **Codex:** Use `convmem search` normally; no sqlite fallback needed unless errors persist
- **Sonnet:** MCP unchanged; benefits from query retry automatically

---

*Maintained in repo; point inter-model messages here instead of re-explaining.*
