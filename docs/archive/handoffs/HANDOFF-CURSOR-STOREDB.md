# Handoff: Cursor store.db Adapter — Discovery + Implementation Spec

## Discovery Results (Kiro, 2026-06-18)

### Structure

Cursor store.db is a **content-addressed blob store** with a DAG (not a flat table):

- `meta` table: single row, key=0, value=hex-encoded JSON:
  ```json
  {"agentId": "...", "latestRootBlobId": "cca9...", "name": "Arch Diagnostics",
   "mode": "default", "createdAt": 1774924886662, "lastUsedModel": "claude-4.6-opus-high-thinking"}
  ```
- `blobs` table: `(id TEXT, data BLOB)` — id is SHA256 hex, data is raw bytes

### Blob types

| Type | How to identify | Contains |
|------|----------------|----------|
| Root blob | ID from `meta.latestRootBlobId` | Protobuf list of message blob IDs |
| Old root blobs | Unreferenced, contain many `0x0a 0x20` patterns | Previous conversation snapshots (history) |
| Message blobs | Referenced by root, data starts with `{` | JSON: `{"role": "...", "content": ...}` |

### Root blob format

Protobuf-encoded flat list of 32-byte SHA256 references:
```
0x0a 0x20 <32 bytes = blob SHA256> → repeated
```

Parsing: scan for `\x0a\x20` + 32 bytes, extract hex IDs. Each ID references a message blob.

### Message blob format

Pure JSON (data starts with `{`):
```json
{"role": "system"|"user"|"assistant"|"tool", "content": "..." | [...blocks...]}
```

- `user` content can be a string or `[{"type":"text","text":"..."}]` block list
- `assistant` content is usually a string
- `tool` messages contain tool results

### Counts (richest DB: 5d3e6fdf)

- 309 total blobs
- Latest root references 106 message blobs (1 system, 4 user, 32 assistant, 69 tool)
- 202 unreferenced blobs = old conversation snapshots (6/20 sampled are sub-trees)
- Only the `latestRootBlobId` tree matters for current conversation state

### All 6 store.db files

All under `~/.config/cursor/chats/1427524c79cf9b6f124866b167841e16/`:
- `5d3e6fdf...` — 309 blobs (Arch Diagnostics)
- `f71179c0...` — 159 blobs
- `80241f09...` — 70 blobs
- `26d7cd70...` — 46 blobs
- `816b5528...` — 1 blob
- `4c5e418a...` — 1 blob

## Implementation Spec

### Parser: `_parse_cursor_store` in `sqlite_chat.py`

```python
def _parse_cursor_store(conn: sqlite3.Connection, filepath: str) -> list[dict]:
    # 1. Read meta → get latestRootBlobId
    # 2. Read root blob → extract message refs (0x0a 0x20 + 32 bytes)
    # 3. For each ref, read blob data:
    #    - Skip if not JSON (data[0] != ord('{'))
    #    - Parse JSON → extract role + content
    #    - Skip system and tool roles
    #    - Normalize content (string or block list → plain text)
    # 4. Return list[dict] in order
```

### Detection

Already handled: `is_sqlite_crush_schema` rejects blobs+meta tables, and `_detect_sqlite`
returns `"sqlite_cursor_store"` when blobs+meta are present. Just need to wire `_PARSERS["sqlite_cursor_store"]` from `None` to the parser.

### Content normalization

User content can be:
- Plain string: `"content": "How do I..."`
- Block list: `"content": [{"type":"text","text":"..."},{"type":"tool_use",...}]`

Same extraction as jsonl_chat: take `type=text` blocks, skip tool_use.

### What to skip

- `role: system` — Cursor system prompt, huge, no retrieval value
- `role: tool` — tool results, noisy, already captured in assistant responses
- Old root blobs / unreferenced sub-trees — only parse `latestRootBlobId`

### Timestamp

`meta.createdAt` is unix ms → use as conversation-level timestamp.
Per-message timestamps don't exist in this format → `None`.

### Stable session_id

Use the directory name (UUID) from the file path: `5d3e6fdf-9bbd-4f90-aca7-6c21f9c8af18`

## Validation commands

```bash
# After implementation:
cd ~/Projects/convmem
python -c "
from adapters.sqlite_chat import parse
import json
msgs = parse('/home/lauer/.config/cursor/chats/1427524c79cf9b6f124866b167841e16/5d3e6fdf-9bbd-4f90-aca7-6c21f9c8af18/store.db')
print(f'messages: {len(msgs)}')
print(json.dumps(msgs[:2], indent=2))
"

# Expected: ~36 messages (4 user + 32 assistant from the 106-ref root)
# Shape: {"role": "user"|"assistant", "content": str, "timestamp": str|None}
```

## Risks

- Protobuf format might vary across Cursor versions — test all 6 DBs
- 1-blob DBs may have empty/null root → return `[]`
- Don't accidentally ingest the 202 old snapshots — only follow `latestRootBlobId`
