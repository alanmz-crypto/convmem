# DeepSeek v4 Pro — session context (convmem project)

**Prepared:** 2026-06-22 by Cursor for Ryan  
**Purpose:** Large-context briefing for DeepSeek running **locally via Crush**.  
**Repo:** `~/Projects/convmem` on Ryan's Arch Linux dev machine  

---

## Running via Crush (read this first)

DeepSeek runs **inside Crush**, not as a cloud paste. Use this workflow:

### Session bootstrap (shell — run in Crush before reasoning)

```bash
# 1. Ops snapshot (always first)
/home/lauer/miniforge3/envs/convmem/bin/python ~/Projects/convmem/convmem.py brief --stdout-only

# 2. Full project context (this document — ~15 min read at 1M context)
cat ~/.local/share/convmem/deepseek-session-context.md
# or: cat ~/Projects/convmem/docs/DEEPSEEK-SESSION-CONTEXT.md
```

### MCP tools (convmem server — prefer over guessing)

If Crush loaded the `convmem` MCP server (`mcp_server.py` via `~/.config/crush/crush.json`):

| Tool | Use |
|------|-----|
| `stats` | Corpus counts — use instead of citing stale numbers |
| `search_fast` | Low-latency retrieval, no LLM |
| `search` | Same as search_fast (scored units) |
| `ask` | RAG with citations — "why did we decide X?" |
| `related` | Evidence chain for a ledger id |

**If MCP shows "not connected":** use shell `convmem` commands from `AGENTS.md` instead; ask Ryan to restart Crush or check `crush.json` mcpServers block.

### Crush project root

- **Best cwd:** `~/Projects/convmem` (this file + `AGENTS.md` on disk)
- **Also fine:** `~/Projects/wp-sec-agent` — still run brief + read context path above
- Crush history ingests from `<project>/.crush/crush.db` — tool state, not source

### What DeepSeek should NOT do in Crush

- Do not `convmem index` / `convmem watch` / `convmem add` without Ryan's explicit OK
- Do not restart `convmem-watch` during soak
- Do not bulk-read `.venv/` or `~/.local/share/convmem/chroma/`

---

## Instructions for DeepSeek

### Your role

You are **DeepSeek** in the multi-agent setup. Per `docs/AGENT-ROLES.md`:

- **Lane:** Runtime synthesis — `convmem ask`, distill API, strategic reasoning on retrieved context
- **You are NOT:** the implementer (Cursor), signer (Kiro), or shell operator (Codex)
- **You do NOT:** claim code was shipped, restart services, or invent corpus stats

### How to use this document

1. Read this file **in full** first — it is curated for 1M-context synthesis passes (per Codex `deepseek-context-assessment`).
2. Treat **§ Live snapshot** as point-in-time; if Ryan gives a newer `convmem brief` block, prefer that for numbers.
3. For **implementation questions**, say "Cursor builds on dev machine after gates" — do not write production patches unless Ryan explicitly asks for design-only output.
4. For **"why did we decide X?"** — reason from § Signed decisions + § Thread chronology; suggest `convmem ask "…"` for citation-backed answers when Ryan has shell access.
5. **Separate three failure classes** (§ Architecture) — never conflate watch OOM, Chroma lock, and GPU VRAM.

### What Ryan may ask you to do

| Good fit | Poor fit |
|----------|----------|
| Synthesize inter-model thread into one narrative | Re-implement `ingest.py` from scratch |
| Prioritize backlog after soak | Restart `convmem-watch` |
| Review `PROPOSE-DECISION-SPEC` for gaps | Bulk-ingest the whole repo into context |
| Compare Claude vs ChatGPT spec merge | Load `.venv/` or Chroma data dirs |
| Strategy for wp-sec-agent + convmem together | Declare P0 complete before Kiro soak sign-off |
| Draft inter-model message for Kiro/ChatGPT | Auto-approve decisions (only Ryan/Kiro sign) |

### Output format Ryan prefers

- Complete sentences, structured sections
- Explicit **recommendations** with **why**
- Flag **blockers** vs **optional**
- If uncertain, say what evidence would resolve it (`brief`, journal line, test run)

---

## What convmem is

**convmem** is a local knowledge system for AI-assisted development:

1. **Ingest** chat transcripts (Cursor, Continue, Kiro, Crush, etc.) and tool observations
2. **Index** into Chroma (embeddings + metadata) with a **ledger** model: observation → decision → verification
3. **Query** via CLI (`search`, `ask`, `related`) and MCP (Cursor, Crush)
4. **Coordinate** multiple AI models via `convmem brief` + `docs/inter-model/` instead of Ryan as middleman

**Paying work context:** `~/Projects/wp-sec-agent` (WordPress security scans per client/site). convmem holds cross-project memory; client work stays in that repo.

**Machine workspace:** See § Workspace standard below.

---

## Architecture (stable — do not redesign without Kiro)

### Data flow

```text
Sources (cursor chats, continue sessions, kiro sqlite, crush.db, …)
    → ingest.py (parse, chunk, summarize, distill, embed)
    → Chroma (~/.local/share/convmem/chroma/)
    → query.py / ask.py / MCP read tools
    → brief.md (ops snapshot, no LLM)
```

### Ledger kinds (`ledger.py`)

| kind | Purpose | requires `relates_to` |
|------|---------|-------------------------|
| observation | Fact discovered | no |
| decision | Signed choice | yes |
| verification | Check outcome | yes |

Decision fields that matter for retrieval: `summary`, `rationale`, `alternatives_rejected`, `constraints`, `site`, `domain`, `author_model`.

**Critical:** `rationale` is appended to Chroma **document text** in `observe.py` so `convmem ask` can answer "why" questions.

### Chroma access (three layers)

| Layer | Use | Mechanism |
|-------|-----|-----------|
| 1 | brief, stats | `chroma_readonly.py` — sqlite only, no PersistentClient |
| 2 | ingest, refine, watch | Short-lived `ChromaStore` writers; per-chunk open/close |
| 3 | search, ask, MCP | `open_chroma_for_read()` + retry + close |

**Single-writer rule:** One workstation owns Chroma; do not rsync chroma/ to another machine (`dec_convmem_single_writer_chroma`).

### Watch (`watch.py` + systemd)

- Filesystem inotify on configured paths (cursor chats, continue, cursor projects, imports, kiro-cli dir)
- Debounce (config: 90s target; live unit may still show 30s until config updated)
- **Live DB skip:** `is_live_watch_db()` — Kiro sqlite, Cursor `store.db`, webui.db
- **Path skip (fix 763e75f):** If path already in `processed.json`, skip even when `force_file` set — prevents re-indexing Continue sessions on every hash change
- **Cgroup:** MemoryMax=4G, MemoryHigh=3G, MemorySwapMax=0

### Three failure classes — NEVER conflate

| Class | Symptom | Layer |
|-------|---------|-------|
| Watch OOM | KDE memory shortage, kernel oom-kill, 3–6G RSS on watch | live DB skip, path skip, per-chunk ingest, cgroup |
| Chroma lock | `readonly database` on search | short writers + read retry |
| GPU VRAM | ComfyUI / nvidia-smi | unrelated to convmem |

---

## Live snapshot (2026-06-22 ~20:02 UTC)

```
Corpus: 957 units, 258 summaries
Inventory: 127 indexed, 0 pending
Services: watch=active, refine=active, monitor.timer=active
Kiro DB excluded: yes
MCP: cursor + crush registered; crush_live verified 2026-06-22T15:35:23Z
Tests: 79 passing (run unittest on dev machine; brief --with-tests has auto-refresh bug)
Watch memory: ~500MB–2G after 763e75f fix (was 3.5G+ before path-skip fix)
P0: maintain watch journal 24h — no oom-kill, peak under 3G
```

**Recent commits (newest first):**

- `763e75f` — Fix watch re-indexing already-processed files (path skip + force_file)
- `b155a9a` — Ryan workspace standard confirmed
- `23c2f17` / `9d4845b` — Workspace docs, handoff archive, inter-model batch
- `036de85` — Watch OOM fixes, brief CLI, chroma_readonly, MCP configs

**Watch soak:** Restarted multiple times on 2026-06-22 for fixes. **Trust soak from last stable restart (~14:59)** with commit `763e75f` on tree. Codex monitors journal; Ryan does not restart unless emergency.

---

## Signed decisions (in corpus — queryable)

| ledger_id | summary (short) |
|-----------|-----------------|
| dec_convmem_workspace_standard | Workspace = convention-only doc, no enforcer |
| dec_convmem_single_writer_chroma | One machine owns Chroma; no dual-writer rsync |
| dec_convmem_dev_machine_canonical | watch/refine/monitor on dev machine |
| dec_convmem_no_auto_merge | Dedupe queue for human review; no auto-merge |
| dec_convmem_rationale_in_document | Rationale in embedded doc text for ask |
| dec_convmem_monitor_never_supersede_kiro | Monitor won't overwrite kiro-review verifications |
| dec_staging2_csp_nginx | CSP via nginx, not WP plugin layer (site-specific) |

**Ryan confirmed** workspace convention 2026-06-22 (`RYAN-2026-06-22-workspace-confirmed.md`).

---

## Thread chronology (2026-06-22 — what happened)

### Morning: crisis and fixes

1. **Watch OOM loop** — 7+ kernel kills; peaks ~6.5G; causes included Kiro live sqlite, Cursor `store.db` burst indexing, indexing storms
2. **Fixes shipped:** `store.db` skip, per-chunk Chroma, `MemorySwapMax=0`, debounce 90s in config example, `chroma_readonly` for brief/stats, search read retry
3. **Kiro withdrew P0-complete** — stability needs 24h clean journal
4. **Search diagnosis** — intermittent lock, not dead search (Codex + Cursor)

### Midday: coordination layer

5. **`convmem brief`** built — shared ops snapshot; inter-model convention in `docs/inter-model/`
6. **Workspace standard** proposed (Codex) → Kiro convention-only → Cursor inventory → **Ryan confirmed**
7. **Handoffs archived** to `docs/archive/handoffs/`; `docs/STATUS.md` points to brief + inter-model
8. **Soak work order** — policy/docs during soak; wp-sec-agent for Ryan; propose_decision design for ChatGPT

### Afternoon: decision specs + watch root cause

9. **Claude + ChatGPT** both wrote `PROPOSE-DECISION-SPEC.md` — merge brainstorm by Cursor
10. **Kiro approved** ChatGPT spec for post-soak build (with minor simplifications)
11. **Watch still climbed to ~3.5G** despite live-DB skips → Kiro found **path-skip bug**: `force_file` bypassed "already seen path" check
12. **Fix `763e75f`** — path skip applies even with `force_file`; memory dropped to ~500MB–2G idle
13. **Codex** acknowledged: soak pass = live DB exclusions **plus** known paths stay skipped
14. **Semantic dedupe** unblocked — `refine --once --job semantic_dedupe` queued 10 candidates (not auto-merge)

### Meta: DeepSeek 1M context

15. Codex assessed: use large context for **history synthesis**, not everyday code nav or loading `.venv`

---

## Workspace standard (confirmed)

> One root per project, one brief per project, explicit live-state exclusions, tool state isolated; convmem = cross-project bus only.

| Project root | Role |
|--------------|------|
| `~/Projects/convmem` | Memory bus, tooling |
| `~/Projects/wp-sec-agent` | Client security (`.crush/` excluded from watch) |
| `~/Projects/web-control` | Ops checklists |
| `~/Projects/ComfyUIimprov` | Noisy — never watch |

**Rejected:** workspace enforcer, manifest system, auto-discovery index.

---

## Agent roster

| Agent | Lane |
|-------|------|
| **Kiro** | Review, sign-off, milestone gates |
| **Cursor** | Implement on dev machine |
| **Codex** | Shell, journal monitoring, readonly reporting |
| **ChatGPT** | Orchestration, strategy, paste-only brief |
| **Sonnet** | MCP verification |
| **Crush** | Runtime agent, MCP read tools |
| **DeepSeek** | **You** — synthesis, ask, distill, large-context reasoning |

**Coordination:** `docs/inter-model/<MODEL>-<date>-<topic>.md` — newest first after `brief.md`.

---

## `propose_decision` — next build (POST-SOAK)

**Status:** Spec approved by Kiro; **do not implement during soak.**

### Problem it solves

Decisions live in chat and inter-model prose until someone manually writes JSONL and runs `convmem add`. That caused unit-count drift and "was P0 done?" confusion across models.

### Approved design (ChatGPT spec + Kiro review)

```text
propose → pending_decisions.jsonl (kind: decision_proposal, NOT in LEDGER_KINDS)
list    → PENDING only (default)
approve → signer allow-list: ryan | kiro-review → decisions-approved.jsonl
reject  → REJECTED, preserved, requires --reason
ingest  → existing: convmem add --file decisions-approved.jsonl --upsert
```

**Hard rules:** Never write Chroma on propose/approve. No MCP approve. No agent self-sign.

**Kiro simplifications (optional):** skip `--ingest-approved` wrapper; skip `--edit-rationale` on approve.

**Cursor merge note:** Use ChatGPT's `decision_proposal` kind + hard signer list; stub `--parse-doc` for v2.

Full specs on disk: `docs/PROPOSE-DECISION-SPEC.md`, `docs/PROPOSE-DECISION-SPEC (1).md` (dedupe to one after soak).

---

## Open work (priority order)

| Priority | Item | Owner | Gate |
|----------|------|-------|------|
| 1 | 24h watch soak | Codex monitor / Ryan | no oom-kill, peak <3G, known paths skip |
| 2 | Kiro stability sign-off | Kiro | after soak |
| 3 | Build `convmem propose_decision` | Cursor | after Kiro spec + soak |
| 4 | One decision E2E test | Cursor + Kiro | after build |
| 5 | `--site` filter on search/ask | Cursor | v1.1, cheap |
| 6 | Pending count in `brief` | Cursor | soak-safe |
| 7 | Fix `brief --with-tests` overwrite bug | Cursor | soak-safe |
| 8 | Review semantic dedupe queue (10 items) | Kiro | optional now |
| 9 | MCP propose tool | Cursor | v2 |

**Ryan productive lane during soak:** `wp-sec-agent` client work.

---

## Key files (for targeted follow-up — do not bulk-load)

| Path | Contents |
|------|----------|
| `convmem.py` | CLI entry |
| `ingest.py` | Pipeline + path skip fix |
| `watch.py` | Live DB skip, debounce |
| `ledger.py` | Decision schema |
| `brief.py` | Ops snapshot generator |
| `chroma_readonly.py` | Metadata without PersistentClient |
| `docs/CHROMA-ACCESS-PATTERN.md` | Reader/writer rules |
| `docs/WORKSPACE-STANDARD.md` | Machine project boundaries |
| `docs/PROPOSE-DECISION-SPEC.md` | Decision workflow spec |
| `docs/inter-model/KIRO-2026-06-22-watch-reindex-fix.md` | Latest watch fix |
| `docs/inter-model/KIRO-2026-06-22-propose-decision-review.md` | Kiro spec approval |
| `docs/inter-model/KIRO-CURSOR-BEST-PRACTICES-2026-06-22.md` | Single conclusion doc |
| `docs/archive/handoffs/` | Historical only |

**50 inter-model files** exist — use this document for narrative; drill into specific `docs/inter-model/*` only when needed.

---

## Suggested prompts for Ryan to give DeepSeek

Copy one of these after uploading this file:

**Synthesis:**
> Read the full session context. Summarize the convmem project's current state, top 3 risks, and recommended order of work for the next 48 hours. Flag anything contradictory in the chronology.

**Decision workflow:**
> Review the propose_decision design in § propose_decision. List any gaps, edge cases, or conflicts with single-writer Chroma before Cursor implements.

**Strategy:**
> Given convmem + wp-sec-agent + workspace standard, how should Ryan split time between client security work and tooling during the watch soak?

**Priority review:**
> The Claude/ChatGPT brainstorm listed 5 leverage items. Given § Open work and the watch fix, re-rank them and say what DeepSeek should help with vs what Cursor/Kiro own.

---

## Do NOT load into context

- `~/.local/share/convmem/chroma/` (large binary index)
- `.venv/` (thousands of dependency files)
- `~/Projects/ComfyUIimprov/` (9G+ noise)
- Full `docs/inter-model/` paste (50 files — use this doc instead)
- Stale `docs/archive/handoffs/` unless researching history

---

*End of DeepSeek session context. Regenerate after major milestones (soak pass, propose_decision ship) by asking Cursor to refresh this file.*
