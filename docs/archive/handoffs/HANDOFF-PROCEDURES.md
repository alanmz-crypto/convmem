# Handoff: Procedure Extraction from Crush (Kiro, 2026-06-18)

## What was implemented

`extract_procedures.py` — standalone extractor that reads Crush DBs,
pairs `bash` tool_call/tool_result entries, groups by session, and uses
one LLM call per procedure for a human-readable title + summary.

## How it works

1. Scans all `**/.crush/crush.db` files (or one via `--db`)
2. Extracts `tool_call` (name=bash) + matching `tool_result` pairs by `tool_call_id`
3. Groups consecutive bash pairs by session_id
4. For each session with ≥2 bash steps:
   - Renders commands + outputs as text
   - Sends to LLM (distill_model from config) for title/summary/domain/keywords
   - Falls back to deterministic title if LLM fails
5. Outputs JSONL for `convmem add --file --upsert`

## Schema

```json
{
  "id": "proc_<session_id_short>",
  "kind": "observation",
  "domain": "coding.devops",
  "author_model": "crush-session",
  "title": "Free GPU VRAM by killing stale processes",
  "summary": "Used nvidia-smi to identify VRAM consumers, killed stale python processes, verified memory freed",
  "keywords": ["nvidia-smi", "kill", "VRAM", "GPU", "python"],
  "tool": "crush",
  "source_path": "/home/lauer/.config/crush/.crush/crush.db",
  "confidence": 0.75,
  "evidence": {
    "session_id": "ad0c3056-...",
    "workspace": "/home/lauer/.config/crush",
    "step_count": 8,
    "steps_json": "[{\"cmd\":\"nvidia-smi\",\"outcome\":\"...\"},...]"
  }
}
```

## Usage

```bash
# Extract from all Crush DBs (uses LLM — needs Ollama or DEEPSEEK_API_KEY)
source ~/.config/convmem/env.local
python extract_procedures.py

# Single DB
python extract_procedures.py --db ~/.config/crush/.crush/crush.db

# Preview
python extract_procedures.py --print | head -5

# Ingest
convmem add --file procedures.jsonl --upsert
```

## Validation for Cursor

```bash
cd ~/Projects/convmem

# 1. Syntax check
python -c "import extract_procedures; print('OK')"

# 2. Extract pairs (no LLM) — confirm data exists
python -c "
from extract_procedures import extract_pairs
pairs = extract_pairs('/home/lauer/.config/crush/.crush/crush.db')
for sid, steps in list(pairs.items())[:2]:
    print(f'{sid[:8]}: {len(steps)} bash steps')
    for s in steps[:2]:
        print(f'  \$ {s[\"cmd\"][:60]}')
"

# 3. Full extraction (one DB, uses LLM)
python extract_procedures.py --db ~/.config/crush/.crush/crush.db --print

# 4. Ingest + verify retrieval
python extract_procedures.py --db ~/.config/crush/.crush/crush.db
convmem add --file procedures.jsonl --upsert
convmem "free GPU VRAM"

# 5. Tests still pass
python -m unittest discover -s tests -q
```

## Design notes

- Uses `kind: "observation"` not a new kind — procedures are facts about what happened
- `steps_json` in evidence field preserves raw command/output for future structured retrieval
- LLM fallback: if generation fails, deterministic title from first command is used
- Stable IDs: `proc_<session_id[:12]>` — rerunning produces same IDs, upsert-safe
- Only `bash` tool_calls extracted (skip `view`, `edit`, `grep` — those are context, not procedure steps)
- `min_steps=2` default — single-command sessions aren't procedures

## Not in scope

- Procedure type in `UNIT_TYPES` / distill.py (kept as observation for now)
- Auto-linking procedures to decisions via `relates_to` (future: match workspace + timestamps)
- Non-bash tool extraction (edit, write — could be v2)
