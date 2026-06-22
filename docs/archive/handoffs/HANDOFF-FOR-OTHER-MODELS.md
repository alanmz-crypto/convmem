# Cursor → other models (upload this)

**From:** Cursor (Opus Auto), canonical dev machine implementer  
**To:** Kiro, Sonnet, ChatGPT (strategy), Crush agents, any new seed  
**Not for Ryan** — this is coordination between us.  
**Date:** 2026-06-22

---

## Why this exists

Ryan asked us to stop making him the middleman. This file states what I believe we should agree on, what's actually usable today, and who owns what next. Paste or upload it at the start of your session.

**DeepSeek key rotation:** Ryan said forget it for now. Do not block other work on it. Do not keep raising it unless he asks.

---

## Role map (settled — stop re-litigating)

| Agent | Lane |
|-------|------|
| **Cursor** | Implementation on dev machine — ingest, MCP server, systemd, rebuilds, `convmem brief` if we build it |
| **Kiro** | Design review, milestone sign-off, proactive corpus queries before answering Ryan |
| **Sonnet** | MCP verification — static source review + live Crush handshake |
| **ChatGPT** | Strategy/architecture (replaced Claude in that seat) — schema, decisions, build sequence; **no shell, no MCP** |
| **Crush** | Runtime agent with MCP read tools once live-tested |

"Builder" in older Claude handoffs = **Cursor**. Kiro's MULTI-AGENT doc describing implementation as done is consistent with that; Claude's FOR-MODELS "builder not engaged" was an earlier snapshot.

---

## Live facts (Cursor verified on machine — trust these over stale handoffs)

| Item | Value |
|------|--------|
| Chroma units | **1028** (rebuild logged **1018**; +10 from monitor/refine post-rebuild) |
| Summaries | **263** |
| Inventory | **121 indexed**, **1 pending** ingest |
| Tests | **72** passing (docs saying 69 are stale) |
| `rerank` | **false** |
| Kiro sqlite exclude | **Not applied yet** — `convmem exclude --list` empty |
| `convmem-watch` | **disabled** |
| `convmem-refine` | active |
| `convmem-monitor.timer` | active |
| MCP stdio | **Proven** — `initialize` + `tools/list` → 5 tools; `search_fast` returns real hits |
| Crush UI → MCP | **Still unverified** — needs one live agent call after Crush restart |
| Shadow `.crush.json` | None under `~/Projects` or `~/GitClones` |
| `brief.md` | **Does not exist yet** |
| `~/.cursor/rules/convmem.md` | Exists; tells Cursor to query convmem; corpus count in it is **stale** |

**Unit count rule:** Rebuild log = snapshot at index time. `convmem stats` / Chroma count = live truth today. Do not cite FOR-MODELS "~1,710 units."

---

## What each of you can use *right now*

### Kiro
You have shell. You should already be doing this; Ryan wants you to start proactively:

```bash
mamba activate convmem   # or source env.local
convmem stats
convmem ask "what did we decide about X?"
convmem ask "unresolved security on staging2?" --evidence
```

Before answering Ryan on architecture, decisions, or "didn't we already…", query first. You don't need new code for that.

### Cursor (me)
Two paths on dev machine:
1. **MCP** — `search_fast`, `search`, `ask`, `related`, `stats` (registered in `~/.cursor/mcp.json`)
2. **CLI** — same surface via `convmem` / `convmem ask`

I will use these before implementing anything that might duplicate past work. Rules file exists; I will treat MCP `search_fast` as the default low-latency check.

### Sonnet
Your static MCP audit in `HANDOFF-GREENFIELD-Second.md` matches what I see in code and what stdio just proved. Your remaining P0 is **Crush live session**, not more source review. If you have shell on dev machine, run Crush restart → one `search_fast` → optional `ask`. Report literal output back into handoff docs.

### ChatGPT (strategy)
You have **no shell and no MCP**. You only see what Ryan pastes. Your lane is still valid — schema, decision records, build sequence in `HANDOFF-FOR-MODELS.md` / `HANDOFF-FROM-CLAUDE.md` — but you cannot verify ops state yourself. Trust this file's live table and ask Ryan to paste `convmem brief` output once it exists.

### Crush
After live verify: use `search_fast` for lookups, `ask` when synthesis + citations are needed. `ask` degrades to retrieval-only on timeout (`synthesis_failed: true`).

---

## Agreed next moves (two tracks)

Ryan accepted this ordering. Do not fork into more handoff docs until Track A steps are done or explicitly reprioritized.

### Track A — index stability (P0)

| Step | Owner | Action |
|------|-------|--------|
| A1 | Cursor | `convmem exclude ~/.local/share/kiro-cli/data.sqlite3 --reason "live DB — watch OOM; manual index only"` |
| A2 | Cursor | `python inventory.py && convmem index` (clear 1 pending file) |
| A3 | Sonnet or Ryan | Restart Crush → live `search_fast` (then `ask` if clean) |
| A4 | Cursor / Ryan | `systemctl --user enable --now convmem-watch`; watch journal 30 min |

**Do not re-enable watch before A1.** That is the OOM regression path.

### Track B — less middleman (P1, can start in parallel with A)

Kiro proposed `convmem brief`. **Cursor agrees — build it.**

**Purpose:** One deterministic command → one compact context block Ryan pastes into ChatGPT (and any model without shell). Same ground truth for everyone.

**Proposed behavior:**
```bash
convmem brief              # stdout — paste into any model session
# also writes:
~/.local/share/convmem/brief.md
```

**Brief should include (no LLM required):**
- Corpus stats (units, summaries, by-source breakdown)
- Signed decisions from ledger (ids + one-line summary + rationale snippet)
- Last monitor verifications / open evidence
- Pending inventory count
- Service state (watch/refine/monitor)
- One-line "active priority" from latest handoff or config
- Timestamp + optional diff vs previous brief

**Auto-regenerate `brief.md` after:** `convmem index`, `convmem refine`, `convmem monitor` (hook in those code paths or a small post-hook script).

**Cursor rules update:** Add line to `~/.cursor/rules/convmem.md` — read `~/.local/share/convmem/brief.md` at session start if present. Fix stale unit count.

**Kiro habit:** Run `convmem brief` at conversation start until auto-regen exists; paste nothing to Ryan — use it yourself.

**ChatGPT habit:** Ryan pastes one `convmem brief` block at session start. You reason on that; do not invent corpus state.

Track B does **not** replace `convmem ask` for deep "why" questions. Brief = ground truth snapshot. Ask = RAG + synthesis.

### Track C — backlog (not now)

- Decision schema extension (`rationale`, `alternatives_rejected`, `constraints`)
- Ingest 5 signed Kiro decisions
- `propose_decision` MCP write tool with human gate
- HTTP MCP bridge for remote models
- `semantic_dedupe` re-eval after watch stable 24h
- Archive/update `HANDOFF-CRUSH-MCP-DEBUG.md`

---

## Handoff doc routing (don't read everything)

| Read for… | Doc |
|-----------|-----|
| Ops + MCP source truth | `HANDOFF-GREENFIELD-Second.md` |
| Strategy + schema | `HANDOFF-FOR-MODELS.md`, `HANDOFF-FROM-CLAUDE.md` |
| Cross-doc number disputes | `HANDOFF-SONNET-RECONCILE.md` |
| Cursor implementer layer | `HANDOFF-CURSOR-UPDATE.md` |
| This coordination message | `HANDOFF-FOR-OTHER-MODELS.md` (this file) |
| Ignore | `HANDOFF-CRUSH-MCP-DEBUG.md` (stale `mcpServers`) |

If docs disagree on counts or MCP status, **this file's live table wins** until someone re-runs the commands and updates it.

---

## What I need from each of you

**Kiro:** Confirm Track A + B ordering. Start querying convmem proactively today. If you want `convmem brief` spec tweaks, reply in your next handoff — Cursor will implement on dev machine.

**Sonnet:** Close A3 only. Post literal Crush `search_fast` output. Stop re-auditing source unless Crush fails live.

**ChatGPT:** Accept paste-based ops context until `convmem brief` exists. Keep strategy/schema work in your lane; defer implementation claims to Cursor/Kiro sign-off.

**Ryan (if he reads this anyway):** You only paste `convmem brief` for ChatGPT. For Kiro and Cursor, the tools should do the work.

---

## One line

**Index is clean; watch stays off until Kiro exclude is applied; MCP stdio works; Crush live is the last P0; `convmem brief` is how we stop making Ryan repeat himself.**

— Cursor
