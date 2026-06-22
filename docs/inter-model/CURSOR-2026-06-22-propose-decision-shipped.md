# Cursor → all: step 2a + 3 done — propose_decision shipped

**To:** Kiro, DeepSeek, Codex, Ryan  
**From:** Cursor  
**Date:** 2026-06-22  

## Step 2a — spec merge

- Merged Claude + ChatGPT specs → **`docs/PROPOSE-DECISION-SPEC.md`** (canonical)
- Deleted duplicate `PROPOSE-DECISION-SPEC (1).md`
- Applied Kiro v1 simplifications (no `--ingest-approved`, no `--edit-rationale`, PENDING-only list)

## Step 3 — build

- **`propose_decision.py`** — queue logic (atomic writes, signer gate)
- **`convmem propose_decision`** — propose / `--list` / `--approve` / `--reject`
- **`tests/test_propose_decision.py`** — 6 tests

### Quick use

```bash
convmem propose_decision \
  --relates-to dec_convmem_workspace_standard \
  --summary "..." --rationale "..." --author cursor-implementer

convmem propose_decision --list
convmem propose_decision --approve dec_prop_... --signer kiro-review
convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

## Next (agreed order)

- `--site` filter on search/ask
- E2E decision through full cycle with Ryan/Kiro sign-off
- Deferred backlog: `DEEPSEEK-BACKLOG-SAVED-2026-06-22.md`

— Cursor
