# F2c — Crush adapter (Builder brief)

**Status:** Implemented (F2c)

---

## Why Crush is missing today

[Charm Crush](https://github.com/charmbracelet/crush) stores chats in **per-project** SQLite files (`crush.db`), not in any `[sources].paths` root. convmem’s SQLite detector only recognizes Kiro, Open WebUI, and Cursor `store.db` table signatures — Crush’s `sessions` + `messages` schema is unknown, so files are never inventoried or parsed.

`~/.local/share/crush/crush.json` is **ephemeral app state** (models, OAuth) — **not** conversation history.

---

## Where Crush data lives

| Location | Contents |
|----------|----------|
| `<project>/.crush/crush.db` | Session + message history (primary) |
| `~/.config/crush/.crush/crush.db` | Global/adjacent copy (same schema) |
| `CRUSH_GLOBAL_DATA` / `crush -D <dir>` | User-overridden data dir |

On this machine, many `crush.db` files exist under `GitClones/`, `Documents/`, etc. — a **glob** (like Aider’s `**/.aider.chat.history.md`) is required; a single config path is not enough.

### Schema (detect + parse)

Tables: `sessions`, `messages` (also `files`, `read_files`, `goose_db_version`).

`messages` columns of interest:

- `session_id`, `role`, `parts` (JSON), `model`, `provider`, `created_at`, `finished_at`

Parser must decode `parts` JSON into canonical `{role, content, timestamp}` messages (same shape as other adapters).

**Detection rule:** SQLite with `goose_db_version`, `sessions`, and `messages` where `messages` has a `parts` column → `sqlite_crush`. Must not match Kiro (`conversations_v2`) or Open WebUI (`chat_message`).

**Parser v1:** extract `type: text` → `data.text`; skip `finish` and `reasoning`. Timestamps: `created_at` → ISO UTC (divide by 1000 when value ≥ 1e10; observed local DBs use seconds despite schema ms comment).

---

## Goals

1. Discover all `crush.db` files under configured roots (or home glob)
2. Parse sessions/messages into the ingest pipeline
3. Metadata `tool: crush`, preserve `source_path`, session id, model/provider when present
4. Idempotent index via existing `processed.json` content-hash flow

---

## Tasks

### Task 1 — Format detection

**Files:** `adapters/detect.py`, `inventory.py` (keep in sync)

```python
# After existing sqlite checks:
if "sessions" in tables and "messages" in tables:
    return "sqlite_crush"
```

Add to `TOOL_BY_FORMAT`: `"sqlite_crush": "crush"`.

### Task 2 — Parser

**File:** `adapters/sqlite_chat.py` (or `crush_chat.py` if cleaner)

- `parse_crush(path) -> list[dict]` — walk messages ordered by `created_at`
- Extract text from `parts` JSON (handle Crush part types; text-only v1 is OK)
- Unit test with a minimal fixture `tests/fixtures/crush_minimal.db` (copy or synthesize)

Wire in `_PARSERS["sqlite_crush"] = parse_crush`.

### Task 3 — Inventory discovery

**Options (pick one for v1):**

| Approach | Pros | Cons |
|----------|------|------|
| **A. Home rglob** `**/.crush/crush.db` (mirror Aider) | Finds all projects | Slower inventory scan |
| **B. Explicit paths** in `[sources].paths` | Fast | User must list roots |
| **C. Both** — glob + optional extra paths | Flexible | Slightly more config |

**Recommended v1:** **A** — add `Path.home()` crush glob to `inventory.py` / `walk_sources`, same pattern as Aider.

Document in `config.example.toml`:

```toml
# Crush: discovered via **/.crush/crush.db under $HOME (see F2c)
# Optional extra roots if using CRUSH_GLOBAL_DATA outside home layout:
# crush_paths = ["~/GitClones", "~/Documents/Computing/AI/ChatData"]
```

### Task 4 — Docs + stats

- README “Search layers” / setup: list Crush as indexed source
- `convmem stats` coverage: `sqlite_crush` in inventory breakdown (automatic once inventoried)

---

## Acceptance

```bash
python inventory.py                    # shows sqlite_crush N file(s)
convmem index --file <path>/crush.db   # chunks + units distilled
convmem "crush terminal" --top 3       # surfaces Crush sessions
python -m unittest discover -s tests   # includes crush parser test
```

---

## Out of scope (F2c v1)

- Cursor `store.db` adapter (separate backlog)
- Merging duplicate Crush sessions across machines
- `CRUSH_GLOBAL_DATA` env auto-discovery (manual paths OK for v1.1)
- Ledger / wp-sec integration for Crush chats

---

## Priority relative to other backlog

| Order | Item |
|-------|------|
| Now | Backfill drain → F2b monitor |
| **Next** | **F2c Crush adapter** |
| Later | Cursor `store.db`, `recency_weight`, LLM dedupe verdict |

---

## Schema sample (Step 3 gate — before adapter code)

**Source:** `~/.config/crush/.crush/crush.db` (sampled 2026-06-18)

```bash
sqlite3 ~/.config/crush/.crush/crush.db ".schema"
sqlite3 ~/.config/crush/.crush/crush.db "SELECT * FROM messages LIMIT 2"
```

**Tables:** `sessions`, `messages`, `files`, `read_files`, `goose_db_version`

**`messages.parts`:** JSON array of typed parts. Observed `type` values in sample:

| type | `data` keys | Parser v1 |
|------|-------------|-----------|
| `text` | `text` | ✅ extract |
| `reasoning` | `thinking`, `signature`, timestamps | optional / strip or fold into content |
| `finish` | `reason`, `time` | skip |

**Sample roles:** `user`, `assistant` — `model` and `provider` on assistant rows (e.g. `qwen3.5:latest`, `ollama-research`).

**Timestamps:** `created_at` / `updated_at` / `finished_at` — Unix **milliseconds** on messages.

Builder must re-run `.schema` + sample SELECT on a second `crush.db` (e.g. under `GitClones/`) before locking parser field assumptions.

---

*Scoped 2026-06 — user request: begin after original priorities finished.*
