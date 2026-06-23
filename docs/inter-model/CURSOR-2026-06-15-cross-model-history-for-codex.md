# Cursor → Codex (and all models): cross-model history without Ryan hunting

**To:** Codex (primary), Kiro, DeepSeek, Crush, ChatGPT, Sonnet  
**From:** Cursor  
**Date:** 2026-06-15  
**Trigger:** Ryan asked: *“Models simply need to be able to utilize other models' history without me hunting. We can do that better?”*

**Live ops:** `~/.local/share/convmem/brief.md` — do not duplicate here.

---

## Problem (why Ryan is still the bus)

Ryan should **not** relay facts between five agents. He should **approve decisions** and do **client work** (`wp-sec-agent`).

Today, models share history through **three buckets**, but only **two are searchable without Ryan**:

| Source | In Chroma / searchable? | How the next model finds it |
|--------|------------------------|-----------------------------|
| Cursor / Continue chat transcripts | ✅ Yes (watch) | `convmem search` / `convmem ask` |
| Crush `crush.db` sessions | ✅ Yes (if indexed) | same |
| Approved decisions (ledger) | ✅ Yes (after approve + ingest) | `search` / `related` |
| `brief.md` | ✅ Yes (regenerated) | `convmem brief` |
| **`docs/inter-model/*.md` prose** | ❌ **Not indexed** | Ryan or manual `ls -lt docs/inter-model/` |
| Pending `propose_decision` queue | ❌ Queue file only | Ryan or Kiro approve flow |
| “Read the newest inter-model files” | ❌ Manual | **That is Ryan hunting** |

**Verified gap:** `convmem search "session close Ryan routing"` does **not** surface inter-model coordination notes — only old unrelated transcripts. Inter-model markdown lives **outside** the corpus unless someone manually ingests it.

So when DeepSeek says “step 8 done,” Cursor only knows if Ryan pasted it, or the fact landed in a **Cursor transcript** that watch picked up. The inter-model thread itself is **invisible to search**.

---

## What “good” looks like

**Ryan should not route facts.** Models get each other's history via:

```
convmem brief  →  convmem search / ask  →  related(ledger_id)
```

Inter-model markdown is **human-readable archive**, not the **system of record**. Durable cross-model facts go through **`propose_decision` → Kiro/Ryan `--approve` → `convmem add --file decisions-approved.jsonl --upsert`**.

**Success metric Ryan cares about:** one weekly line — *“convmem saved time on: ___”* — from a **real client question** (e.g. staging2 CSP), not infra churn.

**Time box:** primary work = client / job search; convmem infra ≤ ~30% unless Ryan explicitly opens a build window.

---

## Do better — three levels

### Level 1 — Now (no code, ~10 minutes)

Every model, **every session start:**

1. `convmem brief --stdout-only` (or read `~/.local/share/convmem/brief.md`)
2. `convmem ask "<topic in plain language>"` — site-scoped when client work: `--site staging2.willowyhollow.com`
3. Only if search misses: read files

**Decisions → pipeline, not prose.** Anything that must cross models:

```bash
convmem propose_decision --author <model>-session --title "..." --body "..." --tags convmem,decision
# Kiro or Ryan:
convmem propose_decision --approve <id> --author kiro-review
convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

**One pointer file (convention until indexed):** at session end, update **`docs/inter-model/LATEST.md`** with exactly three bullets:

- **State** — verified facts only  
- **Decision** — what was decided (or “none”)  
- **Next** — one named owner + one action  

Next model reads **one file** first, not twenty.

**Crush note:** MCP `search`/`ask` may return empty for site-scoped client queries. Use shell:

```bash
convmem search "..." --site staging2.willowyhollow.com
convmem ask "..." --site staging2.willowyhollow.com
```

MCP today: `search_fast`, `search`, `ask`, `related`, `stats` — **no `--site`**, **no `propose_decision`**.

**Alias (Ryan machine):**

```bash
convmem='/home/lauer/miniforge3/envs/convmem/bin/python /home/lauer/Projects/convmem/convmem.py'
```

---

### Level 2 — Soon (small convmem changes, high leverage)

| # | Change | Owner | Why |
|---|--------|-------|-----|
| 1 | **Index `docs/inter-model/`** — add to watch roots or post-session `convmem index --file docs/inter-model/LATEST.md` | Cursor implement / Codex run | Makes coordination notes searchable |
| 2 | **Brief: last 3 inter-model titles** (mtime + one-line summary) | Cursor implement | “What changed since yesterday” without folder hunt |
| 3 | **MCP `recent_notes`** — return newest N inter-model files | Cursor implement | Crush/Cursor get history without Ryan |
| 4 | **MCP `--site` passthrough** on search/ask | Cursor implement | Client work from Crush without shell |
| 5 | **Scheduled / on-demand Crush index** — ensure `**/crush.db` under active projects is in corpus | Codex shell | Symmetric Crush ↔ Cursor history |

**Fastest win bundle (~1–2h implement):** (1) watch or index inter-model + (2) brief shows last 3 notes + (3) `LATEST.md` convention documented in README.

---

### Level 3 — Later (v2 backlog)

From `docs/inter-model/DEEPSEEK-BACKLOG-SAVED-2026-06-22.md` and this plan:

- `--parse-doc` on inter-model → auto-extract `propose_decision` candidates  
- MCP read-only expose of pending proposal queue  
- Kill duplicate MCP PIDs; document watch restarts  
- processed.json GC, lazy ML imports, throttled session reindex  

---

## What already shipped (context for Codex)

Do not re-litigate; use search if you need detail:

| Item | Status |
|------|--------|
| `convmem brief` | Shipped |
| `propose_decision` CLI | Shipped |
| `--site` on search/ask (CLI) | Shipped + boundary bugs fixed |
| Watch: skip logging, debounce, try/except flush | Shipped |
| E2E decisions in corpus | Approved + ingested (~959 units) |
| Inter-model prose in Chroma | **Not done** — this doc's main ask |

---

## Asks by role

### Codex

1. **Adopt session start:** `brief` → `search`/`ask` before asking Ryan “what did the other models say?”  
2. **End session:** update `docs/inter-model/LATEST.md` (3 bullets) when you have cross-model facts.  
3. **Run index smoke** after inter-model updates (until watch ships):
   ```bash
   convmem index --file /home/lauer/Projects/convmem/docs/inter-model/LATEST.md
   convmem search "LATEST handoff" --top 3
   ```
4. **Implement or verify Level 2 item 5** if Ryan opens a build window: inventory/index active `crush.db` for `wp-sec-agent` and `convmem`.  
5. **Payoff test:** one real staging2 question end-to-end; report one line for Ryan's weekly metric.

### Kiro

- Approve decisions from queue; don't require Ryan to paste inter-model essays.  
- Sign off on watch/index inter-model before broad rollout.

### Cursor

- Implement Level 2 items 1–4 when Ryan triggers build.  
- Keep inter-model files short; point to ledger IDs when decisions are ingested.

### DeepSeek / ChatGPT / Sonnet

- Synthesis passes: read this file + `LATEST.md` + `brief` — not full `docs/inter-model/` grep by Ryan.  
- Put durable facts through `propose_decision`, not only prose.

### Ryan

- Only approve decisions + client work.  
- If a model asks “what did X say?”, reply: *“Run `convmem ask` and read `LATEST.md`.”*

---

## Reading order (any new session)

1. `~/.local/share/convmem/brief.md`  
2. `docs/inter-model/LATEST.md`  
3. **This file** (policy — until indexed, Codex should read explicitly)  
4. `convmem ask "<your task>"` (+ `--site` for client repos)  
5. Newest `docs/inter-model/*` only if steps 1–4 miss  

Full convention: `docs/inter-model/README.md`.

---

## Reply format

Codex: reply in `docs/inter-model/CODEX-2026-06-15-cross-model-history-response.md` with:

- Which Level 1 habits you'll follow  
- Which Level 2 items you'll take (shell vs needs Cursor)  
- Result of index smoke on `LATEST.md` if you run it  
