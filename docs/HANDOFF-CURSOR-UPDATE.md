# Cursor implementer update — for all models (2026-06-22)

**Written by:** Cursor (Opus Auto) on the **canonical dev machine** (`/home/lauer`, Arch Linux).  
**Purpose:** My perspective after reading the latest handoffs — what to trust, what's stale, who does what next.  
**Not a replacement** for the detailed docs; a routing layer on top of them.

---

## Who I am in this stack

I'm the **primary implementer** on the machine where convmem actually runs: ingest, adapters, watch/refine, MCP server code, systemd units, rebuilds, and the MCP/Crush audit (items 1–10). I have shell access here; I wrote or landed most of the crisis fixes in Jun 18–19.

I am **not** the MCP live-verification seed (that's **Sonnet**, static tar review in `HANDOFF-GREENFIELD-Second.md`). I am **not** the architecture brainstorm session (**Claude**, `HANDOFF-FOR-MODELS.md`).

**Companion repo:** `~/Projects/wp-sec-agent` — scanner → convmem ledger; site `staging2.willowyhollow.com`.

---

## Which handoff to read (read this table first)

| Doc | Who it's for | Trust for… |
|-----|--------------|------------|
| **`HANDOFF-GREENFIELD-Second.md`** | **Sonnet**, Cursor, Kiro ops | **Current ops + MCP** — rebuild, watch, § MCP, Sonnet static audit at top |
| **`HANDOFF-FOR-MODELS.md`** | **Claude** (strategy) | Decision/Procedure schema, W5H, exclude rationale, agent-access *design* |
| `HANDOFF-FOR-CLAUDE.md` | Claude (deep W5H) | Product direction — corpus counts **stale** |
| `HANDOFF-MULTI-AGENT.md` | Kiro coordination | Kiro voice snapshot — partial overlap with Second |
| `HANDOFF-GREENFIELD.md` | Fallback | Older greenfield; prefer **Second** |
| `HANDOFF-CRUSH-MCP-DEBUG.md` | Nobody | **Stale** (`mcpServers` era) |

**Rule:** Operational truth → **GREENFIELD-Second**. Strategy/schema → **FOR-MODELS**. If they disagree on corpus size or MCP status, believe **this file's live snapshot** + Second, not FOR-MODELS.

---

## Live snapshot (Cursor verified 2026-06-22)

| Item | Value |
|------|--------|
| **Units in Chroma** | **1028** |
| **Summaries** | **263** |
| **processed.json** | **121/122** inventory files |
| **Rebuild log `units_indexed`** | **1018** (ingest-only; +10 units since = monitor/refine/other ingest) |
| **Tests** | **72** passing |
| **`rerank`** | **false** |
| **Kiro exclude** | **Not applied** — `convmem exclude --list` empty |
| **watch** | **disabled**, inactive |
| **refine** | active |
| **monitor.timer** | active |
| **Crush MCP live verify** | **Still outstanding** (Sonnet static review done; no one has run Crush → `search_fast` on machine) |
| **Git** | `main` ahead 11; untracked: `HANDOFF-*-Second`, `HANDOFF-FOR-MODELS`, verify tar |

### Unit count note (reconciling Sonnet vs summaries)

- Rebuild log: `units_indexed=1018` — **correct for that index run**.
- Chroma **now: 1028** — trust **`convmem stats` / `count_units()`** for “how big is the index today”.
- Early chat summaries that said “1028 right after rebuild” were slightly ahead of the log line; both are explainable. **Do not use FOR-MODELS “~1,710 units”.**

---

## What I did (Jun 18–19 crisis → rebuild → MCP hardening)

1. **Diagnosed watch OOM loop** — 7 kernel OOM kills; ~8,666 inflated units from `force_file` re-index + random UUIDs + live Kiro sqlite under watch.
2. **Shipped duplication/OOM fixes** — deterministic IDs (`source_path + start_offset + unit_index`, no title), Chroma `upsert`, delete-before-reindex, `is_live_watch_db()`, systemd `MemoryMax=4G`, conditional notify.
3. **Clean rebuild** — wiped `chroma/` + `processed.json`; full `convmem index` completed.
4. **MCP audit (1–10)** + Claude recommendations — `search_fast`, ask fallback (`synthesis_failed`), 45s synthesis cap, line-buffered stdout, fail-loud corrupt `processed.json`, Crush `timeout: 120`.
5. **Packaged** `sonnet-mcp-verify-full.tar.gz` for Sonnet seeds without filesystem (API key redacted in global crush copy only — see security below).

**Sonnet's GREENFIELD-Second top section** is an accurate static review of that work. I agree with their disputed-values table and their “live handshake still outstanding” conclusion.

---

## My perspective on the other handoffs

### Sonnet (`HANDOFF-GREENFIELD-Second` top)

**Agree:** Top § MCP is authoritative; stale duplicate section was correctly removed; no server-side `mcp_convmem_` prefix; `~/.local/share/crush/crush.json` is not config merge; P0 is live Crush verify.

**Add from dev machine:** Step 5 verification commands in Second are right — **someone with shell still needs to run them**. I have not seen a Crush MCP connection log in `~/.local/share/convmem/logs/` (only index logs).

**Tar:** `~/Projects/convmem/sonnet-mcp-verify-full.tar.gz` — use this, not `sonnet-mcp-verify-bundle.tar.gz` (partial).

### Kiro (`HANDOFF-MULTI-AGENT.md`)

Good Kiro-voice coordination; overlaps Second. **Watch enable checklist must include Kiro exclude first** — Multi-Agent doesn't stress this enough; Second does.

### Claude (`HANDOFF-FOR-MODELS.md`)

**Still valuable for:** Decision `rationale` / `alternatives_rejected` / `constraints`, Procedure from Crush tool_calls, exclude-in-`processed.json` design, three agent-access paths, five signed decisions table.

**Stale in FOR-MODELS:** corpus ~1,710 units, “MCP server later” (it's **shipped**), prototype step 5 “Later: MCP server”, watch/refine always-on picture (watch **off**), test count, rebuild status.

**Use FOR-MODELS for *why*; use Second for *what's running now*.**

---

## Agent routing (updated)

| Agent | Read | Your job now |
|-------|------|----------------|
| **Sonnet** | `HANDOFF-GREENFIELD-Second.md` (top + § MCP) + tar if no FS | **P0:** live stdio + Crush `search_fast` / `ask`; check project-local `.crush.json` shadowing |
| **Claude** | `HANDOFF-FOR-MODELS.md` + `HANDOFF-FOR-CLAUDE.md` | Strategy, `propose_decision` gating, per-client logs — **not** Crush debugging |
| **Kiro** | This file § Kiro + Second § Decisions | Sign off before watch re-enable; confirm exclude + MCP P0 |
| **Cursor** | This file + Second | Exclude Kiro, MCP live verify support, atomic `save_processed`, doc hygiene |
| **DeepSeek** | — | Runtime only (`ask` / distill API) |

---

## P0 before watch goes back on (human or Cursor on dev)

```bash
mamba activate convmem

# 1. Re-apply exclude lost on processed.json wipe
convmem exclude ~/.local/share/kiro-cli/data.sqlite3 \
  --reason "live DB — watch OOM; manual index only"

# 2. MCP live verify (Sonnet P0 — can be Cursor on machine)
pkill -f 'mcp_server.py' 2>/dev/null || true
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}\n' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}\n' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n' \
| python ~/Projects/convmem/mcp_server.py 2>/dev/null | tail -1 | python -m json.tool
# expect 5 tools — then restart Crush and call search_fast

# 3. No project-local crush config shadowing global mcp.convmem
find ~/Projects ~/GitClones -maxdepth 5 \( -name '.crush.json' -o -name 'crush.json' \) 2>/dev/null

# 4. Then re-enable watch
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch
journalctl --user -u convmem-watch -n 20
```

---

## Security (action required)

Sonnet correctly flagged: **unredacted `DEEPSEEK_API_KEY` in `~/.local/share/crush/crush.json`** may have left the machine in a tar. **Rotate the key** and prefer shell expansion in global config only:

```json
"DEEPSEEK_API_KEY": "$(grep DEEPSEEK_API_KEY ~/.config/convmem/env.systemd | cut -d= -f2-)"
```

Do not commit crush.json or tars with keys.

---

## MCP ground truth (Cursor confirms — matches Second)

| Setting | Value |
|---------|--------|
| Server tools | `search_fast`, `search`, `ask`, `related`, `stats` |
| Crush config key | `mcp.convmem` in `~/.config/crush/crush.json` |
| Crush `timeout` | **120** s |
| Protocol (Crush client) | **2025-11-25** (server negotiates) |
| `ask` synthesis cap | **45** s + retrieval fallback |
| `search_fast` | ~**3** s (Ollama embed — not sub-second) |
| Server-side tool prefix | **None** — Crush may display `mcp_convmem_*` client-side |

---

## Open work (Cursor priority view)

| P | Task | Owner |
|---|------|--------|
| P0 | Kiro sqlite `convmem exclude` | Cursor / human |
| P0 | Live Crush MCP verify | Sonnet or Cursor on dev |
| P0 | Rotate exposed DeepSeek key | human |
| P1 | Re-enable watch + 24h clean journal | after P0 |
| P1 | `get(embeddings)` probe → re-evaluate `semantic_dedupe` in refine jobs | Cursor |
| P1 | Atomic `save_processed()` | Cursor |
| P2 | Update `HANDOFF-CRUSH-MCP-DEBUG.md` or archive | anyone |
| P2 | `propose_decision` MCP write tool + human gate | Claude design → Cursor build |
| backlog | `recency_weight`, `cause_unverified` queue, OpenClaw D | per FOR-MODELS / F docs |

---

## Artifacts on dev machine

| Path | Notes |
|------|--------|
| `docs/HANDOFF-GREENFIELD-Second.md` | **Primary ops + MCP** |
| `docs/HANDOFF-FOR-MODELS.md` | **Primary strategy** |
| `docs/HANDOFF-CURSOR-UPDATE.md` | **This file** — routing + live state |
| `sonnet-mcp-verify-full.tar.gz` | Sonnet static review bundle |
| `handoff-tar/README-SONNET-SEED.md` | Tar manifest |

---

## Seed prompts (copy-paste)

**Sonnet:**  
> Read `docs/HANDOFF-CURSOR-UPDATE.md` then `docs/HANDOFF-GREENFIELD-Second.md` (top + § MCP). P0: live Crush MCP verify on dev machine. Tar: `sonnet-mcp-verify-full.tar.gz` if no FS.

**Claude:**  
> Read `docs/HANDOFF-FOR-MODELS.md` for your lane. Read `docs/HANDOFF-CURSOR-UPDATE.md` for current ops — ignore FOR-MODELS corpus/MCP status. Do not own Crush wire-up.

**Kiro:**  
> Read `docs/HANDOFF-CURSOR-UPDATE.md` P0 checklist before signing watch re-enable. Cross-check `HANDOFF-GREENFIELD-Second.md` § Decisions.

**New Cursor seed:**  
> Read `docs/HANDOFF-CURSOR-UPDATE.md` first, then `HANDOFF-GREENFIELD-Second.md`. Implement from P0/open work; 72 tests must pass.

---

## One line

**Clean index is back; watch stays off until Kiro is excluded and Crush MCP is proven live — strategy docs are ahead of ops docs on schema, behind on corpus and MCP status.**
