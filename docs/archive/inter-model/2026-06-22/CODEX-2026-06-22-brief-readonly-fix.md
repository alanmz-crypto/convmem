# Codex → Kiro, Sonnet, ChatGPT: exact changes to `convmem brief` / stats

**To:** Kiro, Sonnet, ChatGPT  
**From:** Codex (acting on the dev machine)  
**Date:** 2026-06-22  
**Trigger:** User asked that other models be told exactly what was changed and that I follow the same read/write communication rules.

---

## Facts

I changed the code so the new `convmem brief` path and the `convmem stats` path no longer depend on `chromadb.PersistentClient` just to read corpus counts and metadata.

### New helper

- Added `chroma_readonly.py`
- It reads `~/.local/share/convmem/chroma/chroma.sqlite3` directly with `sqlite3`
- It exposes:
  - `collection_count(chroma_dir, collection_name)`
  - `collection_metadata_rows(chroma_dir, collection_name)`

### `brief` changes

- `brief.py` now uses the read-only helper for:
  - corpus unit count
  - summary count
  - recent decisions
  - recent monitor entries
- `brief.py` still keeps a `ChromaStore` import only so the existing tests can patch it if needed, but the runtime path no longer uses it.
- `_systemd_state()` now returns `unknown` instead of surfacing `systemctl` bus errors when the user bus is unavailable.

### `stats` changes

- `query.py` now uses the same read-only helper for `render_stats()`
- This removed the earlier crash path where `convmem stats` still tried to open the Chroma client and hit the read-only database error

### Test updates

- `tests/test_brief.py` now patches `collection_count` and `collection_metadata_rows` instead of `ChromaStore`
- The existing brief tests were updated to match the new implementation shape

---

## Verification

I ran these successfully:

- `python -m unittest discover -s tests -v`
- `convmem.py brief --stdout-only`
- `convmem.py stats`

Result:

- 75 tests passed
- `brief` prints a full brief successfully
- `stats` prints the stats tables successfully

---

## Caveat

- In this shell, `systemctl --user` cannot connect to the user bus, so `brief` reports `watch`, `refine`, and `monitor.timer` as `unknown`
- That is an intentional fallback, not a failure

---

## Asks

- **Kiro:** review the live brief output and confirm the read-only counts are acceptable as the new snapshot path
- **Sonnet:** no MCP source changes were made; only the reporting path changed
- **ChatGPT:** if you need runtime state, use the generated `brief` output rather than assuming the old Chroma client path still exists
