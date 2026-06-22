# Handoff: Conversation Exclude Feature

## What was implemented (Kiro, 2026-06-18)

Mark conversations as excluded from indexing. Exclusion state lives in
`processed.json` alongside existing hash-skip entries — queryable, reversible,
with optional reason.

## Files changed

| File | Change |
|------|--------|
| `ingest.py` | Exclude check fires before indexing, even with `force_file` (watch uses force_file) |
| `convmem.py` | New `exclude` command: `PATH --reason`, `--list`, `--undo PATH` |

## CLI

```bash
# Exclude a conversation (end-of-session decision)
convmem exclude ~/.cursor/projects/.../transcript.jsonl --reason "dead end debugging"

# List excluded
convmem exclude --list

# Re-include
convmem exclude --undo ~/.cursor/projects/.../transcript.jsonl
```

## processed.json entry shape

```json
{
  "a1b2c3...sha256...": {
    "path": "/home/lauer/.cursor/projects/.../transcript.jsonl",
    "excluded": true,
    "exclude_reason": "dead end debugging"
  }
}
```

- `excluded: true` — ingest skips this file hash, even with `--force`
- `exclude_reason` — optional prose, for auditability
- Removing `excluded` key (via `--undo`) re-enables indexing on next run

## Behavior

- `convmem exclude PATH` computes the file's SHA256, writes/updates the processed.json entry
- `convmem index` skips files where `processed[hash].excluded == true`
- `convmem watch` → calls `index(force_file=...)` → same exclude check fires
- Files not yet in processed.json get a new entry with just `path` + `excluded` + reason
- Files already indexed still get the `excluded` flag (won't be re-indexed if content changes)

## Validation commands for Cursor

```bash
# 1. Run tests (62/62 should pass)
cd ~/Projects/convmem
python -m unittest discover -s tests -q

# 2. Exclude a test file
convmem exclude ~/.cursor/projects/empty-window/agent-transcripts/992d7a06-2be3-4261-b2f3-83625d8e0529/992d7a06-2be3-4261-b2f3-83625d8e0529.jsonl --reason "empty window stub"

# 3. Confirm it shows in list
convmem exclude --list

# 4. Confirm index skips it
convmem index --file ~/.cursor/projects/empty-window/agent-transcripts/992d7a06-2be3-4261-b2f3-83625d8e0529/992d7a06-2be3-4261-b2f3-83625d8e0529.jsonl
# Should print: [skip] excluded ...

# 5. Undo
convmem exclude --undo ~/.cursor/projects/empty-window/agent-transcripts/992d7a06-2be3-4261-b2f3-83625d8e0529/992d7a06-2be3-4261-b2f3-83625d8e0529.jsonl

# 6. Confirm removed from list
convmem exclude --list
# Should print: No excluded conversations.
```

## Design decisions

- Exclusion lives in `processed.json`, not a sidecar file or flat list
- Reason is optional but encouraged (auditability for future review)
- `--undo` is a clean reversal — removes both `excluded` and `exclude_reason` keys
- Excluded files are skipped even with `force_file` (prevents watch from re-indexing)
- No schema changes to Chroma — this is ingest-layer only
