# convmem — Handoff from Claude
**Author:** Claude (Anthropic) — architecture/brainstorm/coordination role  
**Date:** 2026-06-22  
**Based on:** HANDOFF-FOR-CLAUDE.md (original), HANDOFF-MULTI-AGENT.md (Kiro), HANDOFF-GREENFIELD-Second.md (Sonnet)

---

## Who I am and what I do here

Claude is the architecture and strategy layer in this multi-agent stack. I don't write implementation code, I don't own MCP wire-up, and I don't sign milestones. What I do: identify structural gaps before they become debt, define schemas and thresholds, pressure-test decisions against long-term consequences, and produce handoffs that give other models what they need without making them read everything.

In this session I reviewed three overlapping handoff documents and reconciled them. My assessments are below. Trust Sonnet on MCP source-level verification. Trust Kiro on milestone sign-off authority. Trust the rebuild log over any summary doc on unit counts.

---

## IMMEDIATE ACTION REQUIRED (before anything else)

### 1. Rotate the DeepSeek API key
A live unredacted key (`sk-5740...a511c`) left the dev machine inside a tar that was shared externally. The redaction in the global config copy did not cover `~/.local/share/crush/crush.json`. **This key is compromised. Rotate it at DeepSeek's dashboard now.** This takes two minutes and blocks nothing downstream.

### 2. Re-add the Kiro sqlite exclude before re-enabling watch
The `processed.json` wipe during rebuild lost this exclude. If watch is re-enabled without it, the live Kiro DB gets re-ingested and pollutes the corpus.

```bash
convmem exclude ~/.local/share/kiro-cli/data.sqlite3 --reason "live db, manual index only"
```

Do this **before** `systemctl --user enable --now convmem-watch`.

---

## Reconciled facts (source of truth calls)

| Item | Correct value | Why the other number is wrong |
|------|--------------|-------------------------------|
| Knowledge units | **1,018** | Rebuild log `units_indexed=1018` is authoritative. Chat summaries and Kiro's handoff both say 1,028 — they repeated each other, not the log. |
| Tests passing | **69** | Greenfield doc (closer to source). Kiro's handoff says 72. |
| Tool names in mcp_server.py | **search_fast, search, ask, related, stats** (5 tools) | Confirmed by Sonnet via AST parse — not eyeballed. Any doc showing 4 tools is stale. |
| Crush config key | **`mcp`** (not `mcpServers`) | `mcpServers` is a legacy key in old docs. The actual `crush.json.global` uses `mcp.convmem`. |
| Crush timeout | **120s** | Confirmed in actual config file. Old stale section said 60s. |
| `~/.local/share/crush/crush.json` | **Ephemeral app state only** | Does not participate in config merge chain. No `mcp` key present. Not a shadow risk — but it did contain the unredacted DeepSeek key. |

---

## State of the system (2026-06-22)

### What's running
| Service | Status | Note |
|---------|--------|------|
| `convmem-watch` | **Disabled** | Re-enable only after Kiro sqlite exclude is re-added |
| `convmem-refine` | Active | dedupe, ledger_link, confidence_audit, stale_source_flag |
| `convmem-monitor.timer` | Active | Hourly probes on staging2.willowyhollow.com |

### Corpus
- 1,018 knowledge units (clean rebuild, no duplicates)
- 263 conversation summaries
- 121/122 source files processed (1 skipped: empty agent-transcript JSONL)
- 0 untagged domains
- 69 tests passing

### Source breakdown
| Source | Units |
|--------|-------|
| Cursor JSONL | ~1,215 (pre-rebuild estimate) |
| Kiro | ~590 |
| Crush | ~228 (tool_call extraction pending) |
| Continue | ~221 |
| Open WebUI | ~181 |
| wp-sec / monitor / Lighthouse | ~20+ |

### Domain profile
`coding.ml` 336 · `coding.tooling` 266 · `coding.devops` 223 · `general` 215 · `web_stack.*` 248

---

## MCP status (Sonnet's domain — summary for other agents)

**Source-level confidence is high.** Sonnet did AST-level verification of tool names, traced the 45s timeout through `ask.py → llm.py → requests.post`, confirmed CWD-independence, confirmed read-only structural integrity, and resolved two conflicting doc sections in favor of the correct one.

**Live confidence is zero.** No one has run an actual Crush → MCP → `search_fast` call and received a response. Everything is code-level correct; the live handshake is P0 outstanding.

### What Sonnet needs to do next (on the dev machine)

**Step 1 — Check for shadowing project-local config:**
```bash
find / -maxdepth 6 \( -name '.crush.json' -o -name 'crush.json' \) 2>/dev/null
```
A project-local file in the Crush launch directory would silently override the global `mcp.convmem` block. Not yet checked against actual launch cwd.

**Step 2 — Run the stdio handshake:**
```bash
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n' \
| ~/miniforge3/envs/convmem/bin/python ~/Projects/convmem/mcp_server.py 2>/dev/null \
| tail -1 | python -m json.tool
```
Expect 5 tools: `search_fast`, `search`, `ask`, `related`, `stats`.

**Step 3 — Kill stale MCP processes before Crush retest:**
```bash
pkill -f 'mcp_server.py'
```
Cursor and Crush will respawn on next session.

**Step 4 — Live Crush agent test:** Restart Crush, call `search_fast` then `ask` from an actual agent session. Confirm `ask` returns within 120s and degrades gracefully on synthesis failure.

### MCP open work (priority order)
| Task | Priority |
|------|----------|
| Live stdio handshake on dev machine | **P0** |
| Confirm `search_fast` callable from live Crush session | **P0** |
| Check for project-local `.crush.json` shadowing | **P1** |
| Rotate DeepSeek key in `~/.local/share/crush/crush.json` | **P1 security** |
| Confirm `ask` degrades gracefully under API slowness | **P1** |
| Update `docs/HANDOFF-CRUSH-MCP-DEBUG.md` (still shows `mcpServers`) | P2 |
| Continue MCP connection — unverified by anyone | P2 |
| Future: `convmem_ingest` write tool with human confirmation gate | Backlog |

---

## Decisions in corpus (signed by Kiro)

All confirmed in prior session. Ready to query via `convmem ask "why..."`.

| Decision | Constraint / Risk | Rejected alternative |
|----------|-------------------|----------------------|
| Single-writer Chroma | Concurrent writes corrupt HNSW index silently | rsync Chroma between hosts |
| Dev machine as canonical host | Transcript sync adds fragile complexity, zero benefit | miniPC canonical via rsync |
| No auto-merge semantic duplicates | Auto-merge is irreversible; false positives delete real knowledge | Auto-merge above similarity threshold |
| Monitor never supersedes Kiro verification | Automated probe overwrites human-signed finding | Monitor emits verification regardless |
| Rationale in Chroma document text | Metadata-only is invisible to retrieval/generation path | Store rationale in metadata only |
| Deterministic unit IDs: hash(source_path + start_offset + unit_index) | Title is LLM non-deterministic; can't use as stable key | Title-based IDs |
| `add_unit` uses upsert | Re-index would create duplicates | Chroma `add` (errors on existing ID) |
| Watch skips live DBs | Live sqlite causes corruption/partial reads | Index all files indiscriminately |
| Kiro DB excluded from watch | Manual `index --file` only; live DB state is unpredictable | Watch-managed like other sources |
| Exclude state in processed.json | Excluding a session is a decision; flat path list has no context in 6 months | excluded.txt flat file |

---

## Schema changes approved this session

### Decision record — new fields (Builder: extend `ledger.py`)
```python
Decision(
    id="dec_...",
    relates_to="obs_...",
    summary="...",
    # Extended fields — approved this session:
    rationale="...",                        # prose, load-bearing reason
    alternatives_rejected=["...", "..."],   # list, queryable by ask
    constraints=["...", "..."],             # hard limits that shaped the choice
    confidence=0.9,
    author_model="kiro-review"
)
```

### Procedure type — new (Builder: add to `ledger.py`, new `extract_procedures.py` pass)
```python
Procedure(
    id="proc_...",
    relates_to="dec_...",       # must anchor to a decision
    steps=[
        {"cmd": "...", "outcome": "..."},
    ],
    author_model="crush-session",
    session_id="crush_..."
)
```
Crush schema confirmed by Sonnet: `tool_call` parts (name + input) + `tool_result` parts (tool_call_id + content). Current v1 adapter is text-only — correct behavior. Procedure extraction is a clean additive pass, no refactor.

---

## Build sequence (what comes next)

| Step | Owner | Status |
|------|-------|--------|
| Rotate DeepSeek key | Ryan | **Do now** |
| Re-add Kiro sqlite exclude | Ryan / Kiro | **Before watch re-enable** |
| Extend Decision schema (`rationale`, `alternatives_rejected`, `constraints`) | Builder | Ready — schema approved |
| Ingest 5 confirmed decision records from this session | Kiro | Ready after schema extension |
| Validate: `convmem ask "why single writer"` surfaces correct record | Kiro | W→H→Y proof |
| Live MCP stdio handshake | Sonnet | P0 outstanding |
| Live Crush agent session test | Sonnet | Follows handshake |
| Re-enable watch | Ryan | After exclude re-added |
| Crush procedure extractor (additive pass) | Builder | After decision schema validated |
| `cause_unverified` monitor queue → Kiro review cycle | Builder | Future cycle |
| MCP `propose_decision` write tool with confirmation gate | Builder / Sonnet | Backlog |
| `recency_weight` implementation | Builder | Config stub exists |
| `semantic_dedupe` LLM verdict (re-evaluate now rebuild is done) | Builder | Was blocked on rebuild |

---

## Claude's strategic perspective (for any agent reading this)

### What's working well
The multi-agent division of labor is genuinely effective. Kiro's sign-off authority prevents scope creep. Sonnet's source-level MCP verification caught real discrepancies that docs alone missed. Builder's implementation discipline (gate tests before next step) has kept the corpus clean. The decision record pattern with `rationale` + `alternatives_rejected` is the right answer — it's not overengineered and it's directly queryable.

### The gap that matters most right now
The MCP live handshake being unverified is the biggest single risk. Everything downstream — agents querying the corpus, `propose_decision` write tools, per-client decision logs — depends on that plumbing actually working. It should work. But "should work" and "works" are different things, and this system is specifically built to distinguish between them.

### The gap after that
`convmem ask "why did we..."` currently works for the five signed decisions from this session. At ~1,018 units the corpus is still small enough that retrieval quality is good. Around 5,000 units, the semantic dedupe and domain taxonomy investments become load-bearing — not a today problem but worth keeping in view.

### One thing no one has said explicitly
The per-client decision log idea (site-tagged rationale for pavlomassage.com, willowyhollow.com) is a natural extension that would make convmem directly useful for Ryan's web work, not just dev infrastructure. A `site:pavlomassage` filter on decisions would let any agent answer "why did we structure the booking flow this way" without digging through chat history. Low-lift, high-value for the actual client work.

---

## Architecture quick reference

```
Source files → adapters/detect.py → parser → ingest.py
  → chunk → summarize (Ollama/DeepSeek) → embed (nomic-embed-text) → Chroma
  → distill → knowledge_units (deterministic IDs, upsert)

Ledger path:
  JSONL → observe.py → normalize_ledger_record → embed → Chroma (upsert)
  Evidence chain: observation → decision (rationale + alternatives) → verification
                                          ↓
                               procedure (Crush tool_calls)

Query:
  convmem "query"           → semantic search
  convmem ask "question"    → RAG + DeepSeek synthesis + citations
  convmem related <id>      → graph traversal (relates_to links)
  convmem ask --evidence    → prefer unresolved findings

MCP (read-only):
  mcp_server.py → FastMCP stdio → search_fast | search | ask | related | stats
  ask degrades to raw retrieval on timeout/error (synthesis_failed: true)

Always-on:
  watch    → inotify → incremental index (disabled pending stability + exclude fix)
  refine   → dedupe, audit, link (5-min cycle, active)
  monitor  → hourly HTTP probes → verifications (active)
```

---

## CLI quick reference

```bash
source ~/.config/convmem/env.local

convmem "nginx csp staging2"                    # semantic search
convmem "query" --domain web_stack.security     # scoped search
convmem ask "why single writer?"                # RAG answer
convmem ask "unresolved issues?" --evidence     # evidence-aware
convmem related obs_staging2_wpsec_csp-missing  # graph traversal
convmem exclude PATH --reason "noise"           # skip from index
convmem stats                                   # corpus overview
convmem refine --once --job confidence_audit    # single refine job
```

**Rule:** Read tools are free. Write tools (`add`, `index`, `verify`, `exclude`) require Ryan's direction. Agents never write decisions autonomously.

---

## Constraints (unchanged, non-negotiable)

- Local-first; DeepSeek API only external dependency
- Single writer to Chroma — one host, one process
- Kiro verifications are authoritative — monitor never supersedes
- Distillation is lossy — never rely on it alone for audit trail
- No auto-merge without Kiro review
- No GPU-intensive operations while ComfyUI is active
- `~/.local/share/convmem/` is sensitive — contains real conversations
- 69 tests must pass before any merge

---

*Handoff produced by Claude after reviewing all three prior handoff documents. Not a spec. Corrections welcome via Kiro.*
