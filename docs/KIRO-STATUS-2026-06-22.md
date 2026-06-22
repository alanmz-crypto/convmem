# convmem — Kiro Status & Perspective (2026-06-22)

## Who I am

I'm Kiro — the design reviewer, sanity checker, and decision signer for convmem. I have persistent shell access to the dev machine. I don't write the bulk of implementation but I do write critical fixes, decision records, and handoff docs. Nothing merges without my gate test. Decisions require human confirmation before I ingest them.

This file is my perspective after reading the handoffs that Claude and Sonnet produced independently. It reconciles discrepancies, confirms what's actually true on disk right now, and lists what needs to happen next.

---

## Corrections after reading other models' handoffs

### Unit count
- Claude's `HANDOFF-FOR-MODELS.md` says ~1,710 units — **stale** (pre-rebuild, inflated by 25× duplication)
- Sonnet's `HANDOFF-GREENFIELD-Second.md` says 1,018 from the rebuild log — **close**
- **Actual on disk right now: 1,028 units, 263 summaries** (verified live just now)
- The 10-unit difference is likely from monitor/refine writes after the rebuild finished

### Kiro exclude
- Sonnet correctly flagged that the Kiro DB exclude was lost when `processed.json` was wiped
- **Fixed just now** — re-added: `convmem exclude ~/.local/share/kiro-cli/data.sqlite3`

### DeepSeek API key exposure
- Sonnet flagged an unredacted key in `~/.local/share/crush/crush.json` that went into the tar
- **Action required by human: rotate this key on DeepSeek dashboard**

### MCP tool names
- Sonnet confirmed by AST parse: server-side names are `search_fast`, `search`, `ask`, `related`, `stats`
- No `mcp_convmem_` prefix in server code — if Crush adds one client-side, that's Crush's convention
- This is settled; no code change needed

### Crush MCP connection
- Config is correct (key: `mcp`, type: `stdio`, timeout: 120)
- **Still unverified live** — no one has run a Crush session that actually called a convmem tool yet
- This is Sonnet's P0 next time they have machine access

---

## What's actually running right now

| Component | State | Healthy |
|-----------|-------|---------|
| Chroma index | 1,028 units, clean, no duplicates | ✅ |
| `convmem-watch` | disabled (intentional) | ✅ |
| `convmem-refine` | active | ✅ |
| `convmem-monitor.timer` | active, hourly | ✅ |
| MCP server | spawns on-demand by Cursor/Crush | ✅ (untested from Crush) |
| Ollama | running, nomic-embed-text available | ✅ |
| Tests | 72/72 passing | ✅ |
| Kiro DB excluded | re-added today | ✅ |
| `rerank` | false (GPU safety) | ✅ |

---

## What each model got right

**Claude (`HANDOFF-FOR-MODELS.md`):**
- W5H gap analysis is sound and remains the strategic direction
- Decision schema extension (rationale + alternatives_rejected + constraints) — implemented and working
- "Would someone reasonably redo this wrong?" — locked as the decision capture filter
- Procedure extraction from Crush — implemented, 36 procedures ingested
- MCP as the right inter-agent path — confirmed and built

**Sonnet (`HANDOFF-GREENFIELD-Second.md`):**
- AST-verified tool catalog — correct, thorough
- Config priority chain for Crush — confirmed correct (project → global, data-dir is separate state)
- Identified the stale/duplicate MCP section problem — real issue, now resolved
- Security finding (exposed key) — real, needs rotation
- "Live handshake still outstanding" — correct, still true

---

## What each model should do next

### Sonnet (MCP expert)
1. Get on the dev machine and run the live Crush→convmem stdio handshake
2. Confirm `search_fast` returns results from a real Crush agent session
3. Test `ask` with DeepSeek unavailable — verify graceful degradation
4. Check for project-local `.crush.json` files that might shadow global config

### Claude (strategist)
- `propose_decision` MCP write tool design — how does the human confirm from within an agent session?
- Procedure-to-decision linking — how to connect a Crush command session to the decision it implemented?
- Per-client decision logs — schema for site-tagged rationale across multiple web clients

### Cursor (implementer)
1. Re-enable watch and monitor for 24h stability: `systemctl --user enable --now convmem-watch`
2. `cause_unverified` monitor queue (when monitor sees a state change, queue for Kiro to link to decision)
3. `propose_decision` MCP tool (after Claude scopes the UX)
4. `recency_weight` implementation (low priority)

### Human
1. **Rotate the DeepSeek API key** — exposed in tar sent to Sonnet
2. Open ComfyUI only when not indexing (GPU contention)
3. Decide when to re-enable watch (I'd say now — fixes are in, Kiro exclude is back)

---

## Doc hierarchy (which file to trust)

| File | Status | Use for |
|------|--------|---------|
| **This file** (`KIRO-STATUS-2026-06-22.md`) | Current | Ground truth, corrections, next actions |
| `HANDOFF-GREENFIELD-Second.md` | Current | MCP detail (Sonnet's area), architecture deep-dive |
| `HANDOFF-FOR-MODELS.md` | Current | Claude's W5H strategy, decision schema, ecosystem direction |
| `HANDOFF-MULTI-AGENT.md` | Superseded by this file | Was my earlier attempt before reading Claude/Sonnet output |
| `HANDOFF-GREENFIELD.md` | Superseded | Original greenfield, conflicting MCP sections |
| `HANDOFF-FOR-CLAUDE.md` | Still valid | Product strategy context for Claude sessions |

---

## Architecture (unchanged, confirmed)

```
Sources → adapters → ingest → chunk → summarize → distill → embed → Chroma (upsert)
Ledger → observe.py → normalize_ledger_record → embed → Chroma (upsert)
Query → embed → Chroma cosine → [rerank if on] → display / ask synthesis
MCP → FastMCP stdio → search_fast | ask | related | stats (read-only)
Watch → inotify → debounce → index --file (skips live DBs + excluded)
Refine → chroma_dedupe, ledger_link, confidence_audit, stale_source_flag (5-min cycle)
Monitor → hourly HTTP probes → verifications against existing observations
```

---

## My standing rules (unchanged)

- No adapter without `parse(real_file)[:2]` gate output
- No scope creep without explicit approval
- No auto-merge, no auto-delete without Kiro review
- Decision records require human confirm (10-second three-line format)
- Build order enforced: current step validated before next starts
- Monitor never supersedes Kiro verification
- Single writer to Chroma at all times
