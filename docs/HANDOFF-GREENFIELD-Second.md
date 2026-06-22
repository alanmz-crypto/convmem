# convmem — Greenfield Handoff for New Agent

## 🔵 Sonnet MCP verification — 2026-06-22 (READ THIS FIRST)

**Identity note:** This session is "Sonnet" — a new seed, not a continuation of whoever wrote the original § MCP integration section below. Verified against actual source code in `sonnet-mcp-verify-full.tar.gz`, not just docs. No live access to the dev machine (no network, no process control) — everything below is static/source verification, not a live Crush run.

### Resolved: the two conflicting MCP sections

The doc used to have two MCP sections that disagreed (top one Cursor wrote, bottom one — now removed — was an earlier/stale pass). **Source code confirms the top § MCP integration section is correct on every point that was in dispute:**

| Disputed value | Bottom (stale, removed) said | **Confirmed correct (top section)** |
|---|---|---|
| Crush timeout | 60s | **120s** — verified in `crush.json.global`, key `mcp.convmem.timeout` |
| Protocol | tested 2024-11-05 / 2025-03-26 | **2025-11-25** — server negotiates to whatever client sends (MCP SDK behavior); not hardcoded either way |
| Tool name prefix | implied none | Confirmed: **no `mcp_convmem_` prefix exists in server code.** AST-parsed `mcp_server.py` — the 5 `@mcp.tool()` names are exactly `search_fast`, `search`, `ask`, `related`, `stats`. If Crush displays/calls them with a prefix, that's a Crush-side display convention, not anything the server does or that needs fixing here. |
| Continue config path | not mentioned | `~/.continue/mcpServers/convmem.json`, key `mcpServers.convmem` — per seed doc, unverified by me (no Continue test available) |

### Resolved: `~/.local/share/crush/crush.json` is not a config-merge layer

Question raised: does the data-dir copy of `crush.json` shadow or merge with `~/.config/crush/crush.json` for the `mcp` key? **No.** Per Crush's own README, config precedence is exactly three sources, highest to lowest: `.crush.json` (project) → `crush.json` (project) → `~/.config/crush/crush.json` (global). The data-dir file (`~/.local/share/crush/crush.json`) is documented separately as **ephemeral app state only** (recent models, provider key cache) — it has no `mcp` key in the copy I inspected, confirming it's not part of the merge chain. The global config's `mcp.convmem` block is the only thing Crush reads for this server, *provided* no stray project-local `.crush.json`/`crush.json` exists in the actual cwd Crush launches from or any parent up to the git root — that's worth one `find` pass on the dev machine since I can't check it remotely.

### Confirmed by reading source (not just trusting docs)

- **5 tools, exact names** — AST-parsed, not eyeballed.
- **`synthesis_failed` fallback is real and robust.** `ask.py` builds citations before calling `generate()`; broad `except Exception` catches timeout/auth/anything; returns retrieval-only answer with `synthesis_failed: true` rather than crashing the MCP call.
- **45s synthesis cap is enforced**, not just documented — traced `ask.py` → `llm.py` → `requests.post(timeout=45.0)`.
- **CWD-independence is real.** `config.py`'s `CONFIG_PATH` is hardcoded + `expanduser()`'d, no cwd dependency, only needs `HOME` — matches the "works under `env -i HOME=... python mcp_server.py`" claim.
- **Read-only confirmed structurally**, not just by docstring — traced every import reachable from all 5 tools, no write/ingest path exists.
- **`rerank=false` honored** — `query.py` only invokes the reranker if config says so.

### Gaps I could not close (sandbox limits, not code problems)

- **No `mcp` package, no network access here** — couldn't run the actual stdio `initialize`/`tools/list` handshake. The AST-confirmed tool list is solid, but the literal "restart Crush, call `search_fast` live" P0 step has to happen on the dev machine. Nobody has run that yet — there's no actual Crush↔MCP connection log anywhere in the tar I received, only per-project Crush *indexing* logs (different thing).
- **`meta_format.py`, `domains.py`, `open_source.py`, `ledger.py`, `evidence.py`** weren't in my tar (imported by `ask.py`/`query.py`/`related()`), so I can't statically confirm those import cleanly. Likely fine — they're in the Key Files table below — just outside what I personally checked.

### Two things to fix, unrelated to the MCP merge question

1. **Live unredacted DeepSeek key** sitting in `~/.local/share/crush/crush.json` (`sk-5740...a511c`) made it into the tar that left the dev machine, even though the handoff said keys were redacted — that redaction only covered the global config copy. **Rotate this key.**
2. **Unit count discrepancy:** Cursor's chat summary and the seed README both say "1028 units," but the actual rebuild log's only `Done.` line says `units_indexed=1018`. Off by 10, doesn't change the "rebuild succeeded" conclusion, but the log is the source of truth, not the two summaries that repeated each other.

### Recommended next action (for whichever model has the dev machine)

```bash
# Confirm no stray project-local config is shadowing global mcp.convmem
find / -maxdepth 6 \( -name '.crush.json' -o -name 'crush.json' \) 2>/dev/null

# Then run the actual P0 from § MCP integration below:
# tools/list over stdio, restart Crush, call search_fast then ask live.
```

That live verification is still **outstanding** — everything above is code-level confidence, not a confirmed live handshake.

---

## What this is

Local-first CLI that turns AI chat history into a searchable, citeable knowledge corpus with an evidence ledger for security findings. No cloud database, no web app. ChromaDB on disk + DeepSeek API for synthesis.

**Repo:** `~/Projects/convmem`
**Config:** `~/.config/convmem/config.toml`
**Data:** `~/.local/share/convmem/` (chroma/, processed.json, logs/)
**Env:** `mamba activate convmem` (Python 3.11, all deps installed)

## Current state (2026-06-22)

- **Rebuild complete** — clean index: 1,018 units, 263 summaries, 121/122 files processed (1 skipped: empty agent-transcript jsonl). No duplicates.
- **Watch disabled** — re-enable after excluding the Kiro sqlite DB (see below): `systemctl --user enable --now convmem-watch`
- **Refine active** — `convmem-refine.service` running (dedupe, link, audit jobs)
- **Monitor active** — `convmem-monitor.timer` probes staging2.willowyhollow.com hourly
- **69 tests passing**
- **MCP server** registered for Cursor, Crush, Continue (stdio transport) — **Crush live connection still unverified** (see Sonnet section above)
- **rerank = false** in config (GPU contention mitigation; re-enable after rebuild)
- **Before re-enabling watch:** `convmem exclude ~/.local/share/kiro-cli/data.sqlite3` — this exclude was lost when `processed.json` was wiped during rebuild

## Architecture

```
Chat logs (Cursor, Kiro, Crush, Continue, Aider, Open WebUI)
    → adapters (format-based detection)
    → ingest.py (chunk → summarize → distill → embed → Chroma)

Security tools (wp-sec, Lighthouse, monitor probes)
    → observe.py / ledger.py (structured JSONL → Chroma)
    → evidence chain: observation → decision → verification

Query paths:
    convmem "query"           → semantic search (knowledge_units)
    convmem "query" --raw     → conversation_summaries fallback
    convmem ask "question"    → RAG (retrieve + DeepSeek synthesis + citations)
    convmem related <id>      → graph traversal (relates_to links)
    convmem ask --evidence    → prefer unresolved findings

MCP server (mcp_server.py):
    search_fast, search, ask, related, stats → MCP-capable agents (Crush, Cursor)
    search_fast = retrieval only (~3s); ask = retrieve + synthesis (45s cap)
```

## Key files

| File | Role |
|------|------|
| `convmem.py` | CLI entry (typer) |
| `config.py` | Load TOML config |
| `adapters/` | Format detection + parsers (jsonl, sqlite, json, markdown) |
| `ingest.py` | Chunk → summarize → distill → embed → store |
| `distill.py` | LLM extraction → knowledge units (deterministic IDs) |
| `chroma_store.py` | ChromaDB wrapper (upsert, query, tombstone) |
| `llm.py` | Ollama embed + DeepSeek/Ollama generate |
| `ask.py` | RAG: retrieve → synthesize → cite |
| `query.py` | Retrieval + Rich display |
| `ledger.py` | Evidence ledger (observation/decision/verification) |
| `observe.py` | Direct ingest for tool-sourced findings |
| `evidence.py` | Evidence-aware re-ranking (unresolved > resolved) |
| `monitor.py` | HTTP security header probes |
| `refine.py` | Background jobs (dedupe, backfill, audit) |
| `watch.py` | Filesystem watch → incremental index |
| `mcp_server.py` | FastMCP stdio server |
| `extract_procedures.py` | Crush bash tool_call → procedure records |
| `domains.py` | Domain taxonomy |
| `rerank.py` | CrossEncoder reranker (CUDA→CPU fallback) |

## Milestones completed

Steps 0–8, Milestones A (ledger), B (graph), C (scanner auto-ingest + upsert), E (evidence-aware ask), F0 (watch), F1 (refine), F2a (store API), F2b (monitor), F2c (Crush adapter), Decision schema extension, Procedure extraction, Cursor store.db adapter, MCP server, Exclude feature.

## Decisions in the corpus (signed by Kiro)

- Single-writer Chroma (one machine owns the index)
- Dev machine is canonical host (not miniPC)
- No auto-merge semantic duplicates (queue for human review)
- Monitor never supersedes Kiro verification
- Rationale stored in Chroma document text (not metadata-only)
- Deterministic unit IDs: hash(source_path + start_offset + unit_index)
- add_unit uses upsert (idempotent re-index)
- Watch skips live DBs (Kiro sqlite, webui.db)
- Kiro DB excluded from watch (manual `index --file` only)

## Known debt

| Item | Status |
|------|--------|
| Crush MCP live connection | Config verified correct in source (timeout 120, no tool prefix server-side); **live stdio handshake still not run by anyone** — P0, see Sonnet section |
| `recency_weight` | Config key exists, not implemented |
| `semantic_dedupe` | Removed from refine jobs; blocked until rebuild completes and `get(embeddings)` works — rebuild is now done, re-evaluate |
| Kiro sqlite exclude | Lost on `processed.json` wipe; must re-add before re-enabling watch |
| `cause_unverified` monitor queue | Not built |
| OpenClaw probes (Milestone D) | Deferred |
| Live DeepSeek key in `~/.local/share/crush/crush.json` | **Rotate** — left the dev machine unredacted in a tar |
| Unit count doc mismatch | Chat/README summaries say 1028; rebuild log says 1018 — trust the log |

## After rebuild completes

```bash
# Check it finished
convmem stats

# Re-add the Kiro sqlite exclude (lost on processed.json wipe)
convmem exclude ~/.local/share/kiro-cli/data.sqlite3 --reason "live db, manual index only"

# Re-enable watch
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch

# Verify watch is healthy after 30 min
journalctl --user -u convmem-watch -n 20

# Re-run confidence audit
convmem refine --once --job confidence_audit
```

## Agent roles

| Agent | Role |
|-------|------|
| **Sonnet (you)** | **MCP expert** — Crush/Cursor MCP integration, tool contracts, stdio/protocol debugging, post-rebuild MCP verification. Own everything in § MCP below. Each new Sonnet session is a fresh seed — no memory of prior sessions; rely on this doc, not assumed continuity. |
| **Kiro** | Design reviewer, sanity checker, decision signer |
| **Cursor (Opus Auto)** | Primary implementer (CLI, ingest, adapters) |
| **Claude** | Architecture brainstorming, ecosystem strategy (not MCP wire-up) |
| **DeepSeek** | `convmem ask` synthesis + distillation API |

**Sonnet seed prompt:** Read this file, then **§ MCP integration** end-to-end. Your job is to get Crush reliably calling convmem tools after rebuild — not to re-audit ingest/watch unless MCP depends on it. The rebuild is done; your P0 is the live stdio verification, not re-confirming the index.

---

## MCP integration (Sonnet owns this)

### What the MCP server is

- **File:** `~/Projects/convmem/mcp_server.py`
- **Stack:** Python MCP SDK **1.28.0**, **FastMCP**, **stdio** transport only
- **Entry:** `asyncio.run(mcp.run_stdio_async())` — only `asyncio.run` in the codebase
- **Tools are sync** `def` (not `async def`); FastMCP runs them in a thread pool — no nested event loops
- **Read-only:** no ingest/write tools exposed (no `processed.json` race via MCP)
- **Stdout:** `sys.stdout.reconfigure(line_buffering=True)` at startup (subprocess block-buffering guard)
- **Import path:** `sys.path.insert(0, Path(__file__).parent)` — CWD-independent

### Tool catalog (current) — confirmed by AST parse 2026-06-22

| Tool | Latency (typical) | Use when |
|------|-------------------|----------|
| **`search_fast`** | ~3 s | Agent needs retrieval only; Crush default fast path |
| `search` | ~3 s | Same as `search_fast` (alias payload); prefer `search_fast` in Crush |
| `ask` | ~3 s retrieve + up to **45 s** synthesis | Need synthesized answer + citations |
| `related` | ~1 s | Traverse ledger graph by `ledger_id` |
| `stats` | ~0.5–2 s | Corpus counts by tool/domain |

**No `mcp_convmem_` prefix exists server-side** — confirmed by AST parse of `@mcp.tool()` decorators. If a client shows that prefix, it's added client-side.

**`ask` response JSON fields:** `answer`, `citations[]`, `confidence`, `warning`, `synthesis_failed` (bool).

**Synthesis failure behavior:** citations built **before** LLM call; on timeout/error → retrieval-only answer + `synthesis_failed: true` (does not hard-fail the MCP call). Confirmed by reading `ask.py`/`llm.py` source — `requests.post(timeout=45.0)` raises into a broad `except Exception`.

**Not exposed via MCP:** rerank (config `rerank=false`), ingest, exclude, monitor, refine.

### Client registration

#### Crush (primary target)

**Config:** `~/.config/crush/crush.json` — top-level key **`mcp`** (NOT `mcpServers`; that key is **legacy/stale** in old docs).

```json
"mcp": {
  "convmem": {
    "type": "stdio",
    "command": "/home/lauer/miniforge3/envs/convmem/bin/python",
    "args": ["/home/lauer/Projects/convmem/mcp_server.py"],
    "timeout": 120,
    "env": {
      "HOME": "/home/lauer",
      "DEEPSEEK_API_KEY": "$(grep DEEPSEEK_API_KEY ~/.config/convmem/env.systemd | cut -d= -f2-)"
    }
  }
}
```

- Crush default MCP timeout was **15 s** — too tight for `ask` (~14 s before fixes). **`timeout: 120`** is set and confirmed present in the actual config file.
- Crush client negotiates **`2025-11-25`** (`LATEST_PROTOCOL_VERSION` in Crush Go MCP client). Server accepts and returns same — server doesn't hardcode a version, it echoes whatever the client sends.
- Crush connects MCP servers **at startup** (parallel init per server). No `/mcp connect` CLI command.
- **Config priority, confirmed against Crush's own docs:** `.crush.json` (project) → `crush.json` (project) → `~/.config/crush/crush.json` (global). Highest wins. The data-dir file `~/.local/share/crush/crush.json` is a **separate, fourth thing** — ephemeral app state only, not part of this merge chain, confirmed to have no `mcp` key.
- **Action item:** confirm no stray project-local `.crush.json`/`crush.json` exists in whatever directory Crush is actually launched from, up to the git root — this would silently override the global `mcp.convmem` block if present. Not yet checked against the real launch cwd.
- **Tool names in Crush:** displayed/called with a `mcp_convmem_<tool>` prefix in some docs — this is Crush-side, not present in server code. Treat as Crush's naming convention, not a contract to match in `mcp_server.py`.

#### Cursor

- Config: `~/.cursor/mcp.json` (separate from Crush)
- Same command/args; Cursor spawn may leave **stale long-lived** `mcp_server.py` — restart if tools behave like pre-fix code

#### Continue

- Config: `~/.continue/mcpServers/convmem.json`, key `mcpServers.convmem`
- Unverified by Sonnet — no Continue test run yet

### Spawn environment (what works without shell activation)

Crush spawns with **minimal env** (not full conda `PATH`). Verified with `env -i HOME=...`:

| Need | Source |
|------|--------|
| Config | `~/.config/convmem/config.toml` via `load_config()` |
| Chroma path | Absolute after expanduser — **CWD-safe** (`/tmp` spawn OK) |
| Ollama embed/search | `http://localhost:11434` must be reachable |
| DeepSeek synthesis | `DEEPSEEK_API_KEY` in Crush `env` block; without key → falls back to `llama3.1:8b` |

No `CONVMEM_*` env vars required for basic operation.

### MCP audit results (items 1–10) — pre-fix baseline

| # | Area | Status |
|---|------|--------|
| 1 | `crush.json` key conflict | ✅ Only `mcp.convmem`; no duplicate `mcpServers` |
| 2 | Stdio framing | ✅ No stdout on import/initialize; stderr only for rerank fallback |
| 3 | Env at spawn | ✅ Works; `timeout` + `env` added |
| 4 | `processed.json` race | ✅ N/A — MCP has no ingest tool |
| 5 | Reranker blocking | ✅ `rerank=false` |
| 6 | Chroma relative paths | ✅ All absolute via `load_config()` |
| 7 | asyncio nesting | ✅ Safe |
| 8 | Protocol version | ✅ negotiated, not hardcoded — server echoes client's version |
| 9 | processed.json corruption | ⚠️ MCP ignores file; ingest fails loud on corrupt JSON now |
| 10 | Ask timeout / hang | ✅ Fixed: 45 s cap + retrieval fallback |

**Symptom map:** `search_fast` works but `ask` fails → was Crush 15 s timeout; should be fixed. If still broken → stdout pollution, project-local crush.json, or stale MCP process.

### Verification commands (run these — still outstanding as of 2026-06-22)

```bash
# 1. Protocol + tool list
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}\n' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}\n' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n' \
| ~/miniforge3/envs/convmem/bin/python ~/Projects/convmem/mcp_server.py 2>/dev/null \
| tail -1 | python -m json.tool

# Expect 5 tools: search_fast, search, ask, related, stats

# 2. Minimal-env search (simulates Crush spawn)
env -i HOME=$HOME USER=$USER \
  ~/miniforge3/envs/convmem/bin/python -c "
import sys; sys.path.insert(0,'$HOME/Projects/convmem')
from query import query_units
print(len(query_units('wordpress', top_k=1)))
"

# 3. Ask fallback (synthesis failure should not crash)
cd ~/Projects/convmem && python -c "
from unittest.mock import patch
from ask import ask
with patch('ask.generate', side_effect=TimeoutError('test')):
    r = ask('test', top_k=2)
print('synthesis_failed', r.get('synthesis_failed'), 'cites', len(r.get('citations',[])))
"

# 4. Kill stale MCP before Crush retest
pkill -f 'mcp_server.py'   # Cursor/Crush will respawn on next session

# 5. Check for shadowing project-local config (new — added by Sonnet 2026-06-22)
find / -maxdepth 6 \( -name '.crush.json' -o -name 'crush.json' \) 2>/dev/null
```

### Open MCP work for Sonnet

| Task | Priority |
|------|----------|
| **Run the live stdio handshake on the dev machine** | P0 — no one has done this yet; everything to date is source-level confidence |
| Confirm `search_fast` callable from a live Crush agent session | P0 |
| Confirm `ask` returns within 120 s with `synthesis_failed` on API slowness | P1 |
| Check for project-local `.crush.json`/`crush.json` shadowing global config at actual launch cwd | P1 — new, raised 2026-06-22 |
| Rotate the DeepSeek key exposed in `~/.local/share/crush/crush.json` | P1 security |
| Update `docs/HANDOFF-CRUSH-MCP-DEBUG.md` (still shows `mcpServers`) | P2 |
| Future: ingest MCP tool would need `processed.json` file lock | backlog |

### What MCP does NOT depend on

- `processed.json` state (never read by MCP)
- Watch/refine daemons running
- Reranker loaded
- `semantic_dedupe` / embedding bulk `get()`

MCP **does** depend on: finished or partial Chroma index, Ollama up, optional DeepSeek for full `ask` synthesis.

---

## Related docs

| Doc | Notes |
|-----|-------|
| `docs/HANDOFF-CRUSH-MCP-DEBUG.md` | **Stale** — shows `mcpServers`; use § MCP integration above |
| `docs/HANDOFF-FOR-CLAUDE.md` | Product/W5H direction (pre-rebuild counts) |
| `docs/HANDOFF-EXCLUDE.md` | Exclude feature |
| `docs/HANDOFF-CURSOR-STOREDB.md` | Cursor store.db adapter |

## CLI quick reference

```bash
source ~/.config/convmem/env.local

convmem "search query"                          # semantic search
convmem "query" --domain web_stack.security     # scoped
convmem ask "question"                          # RAG answer
convmem ask "question" --evidence               # prefer unresolved
convmem ask -i                                  # interactive
convmem related obs_staging2_wpsec_csp-missing  # evidence chain
convmem add --file observations.jsonl --upsert  # ingest findings
convmem verify UNIT_ID --model kiro-review      # cross-model check
convmem exclude PATH --reason "noise"           # exclude from indexing
convmem stats                                   # corpus overview
convmem refine --once --job confidence_audit    # run one refine job
convmem monitor --site staging2.willowyhollow.com --dry-run
```

## Constraints

- Local first; cloud only for DeepSeek API
- Kiro authority: decisions require human confirmation
- No GPU contention: don't index while ComfyUI is active
- Single writer: only one host writes to Chroma at a time
- 69 tests must pass before any merge
