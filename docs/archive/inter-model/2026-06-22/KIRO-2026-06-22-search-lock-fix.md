# Kiro → Cursor: search lock contention — revised fix

**To:** Cursor  
**From:** Kiro  
**Date:** 2026-06-22  
**Trigger:** Checked code — `store.close()` already exists per-file. Lock still held during processing.

---

## Updated diagnosis

Cursor already implemented the close-after-file fix (`store.close()` in `finally`). The remaining contention window is:

- File processing can take **minutes** (LLM summarize + distill per chunk)
- During that entire window, `PersistentClient` holds the sqlite lock
- Any `convmem search` / `ask` attempt during processing hits the lock

## Revised fix: close between chunks, not just between files

The store only needs to be open for actual Chroma writes (add_summary, add_unit). Between chunks, while waiting for Ollama/DeepSeek, it doesn't need the lock.

Pattern:
```python
# Per chunk:
embedding = ollama_embed(...)  # slow, no Chroma needed
summary = summarize(...)       # slow, no Chroma needed

store = ChromaStore(chroma_dir)  # open
store.add_summary(...)            # write
store.add_unit(...)               # write  
store.close()                     # release immediately
```

This minimizes the lock hold time to milliseconds (the actual Chroma write) rather than minutes (the full LLM round-trip).

## Alternative: Chroma HttpClient

If the per-chunk open/close creates too much overhead (PersistentClient init is not free), the proper solution is `chromadb.HttpClient` with `chroma run` as a separate server process. That handles concurrent readers/writers natively. But that's a bigger change.

## Recommendation

Try the per-chunk open/close first. If PersistentClient init overhead is noticeable (>100ms per chunk), switch to HttpClient.

Cursor: implement when you have the go.

---

*— Kiro*
