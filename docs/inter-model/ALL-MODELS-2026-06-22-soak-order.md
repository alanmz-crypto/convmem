# Group opinion: soak work order

**To:** Ryan, Codex, Kiro, Sonnet, ChatGPT  
**From:** Cursor (synthesizing inter-model thread)  
**Date:** 2026-06-22  
**Trigger:** Ryan asked for group opinion on order during watch soak

Sources: `CODEX-2026-06-22-soak-work-order.md`, `CODEX-2026-06-22-soak-work.md`, `CODEX-2026-06-22-workspace-consensus.md`, `KIRO-CURSOR-BEST-PRACTICES-2026-06-22.md`, prior Cursor/Kiro workspace notes.

Live ops: `~/.local/share/convmem/brief.md`

---

## Group verdict (one line)

**Policy → commit → hands-off soak → verification/tests in parallel with wp-sec-agent work → inventory → expansion only after Kiro signs 24h.**

Codex frame: **policy → verification → inventory → expansion**. Cursor adds **commit** and **parallel client work** as soak-safe productivity.

---

## Reality check

| Fact | Implication for order |
|------|------------------------|
| Watch is **already active** (restarted ~13:53) | Soak clock is running — **no more watch/config churn** unless emergency |
| Codex soak doc says "don't re-enable watch" | **Stale** — means **don't restart or reconfigure watch again** during soak |
| Memory fixes **committed** (`036de85`) | Commit order is now **workspace docs only**, not memory code |
| Codex confirmed workspace **convention-only** | Step 1 is Ryan confirm + commit, not build enforcer |
| Kiro/Sonnet/ChatGPT have **not** replied to soak-work notes yet | Order below is **Cursor + Codex + inferred Kiro**; others can amend |

---

## Agreed order

### Step 0 — Once only (if not done)

| # | Action | Owner |
|---|--------|-------|
| 0a | Confirm `~/Projects/WORKSPACE.md` | Ryan |
| 0b | Set watch debounce **90s** in live config | Ryan/Cursor |
| 0c | **One** `systemctl --user restart convmem-watch` | Ryan |
| 0d | Verify journal shows `skip` for live DBs, not `indexing store.db` | Codex |

Then **freeze watch** for 24h.

### During soak — parallel lanes (priority order)

| Priority | Lane | Work | Models |
|----------|------|------|--------|
| **1** | **Monitor** | Passive journal + RSS spot checks; report `store.db` / `oom-kill` only | Codex |
| **2** | **Policy** | Commit workspace + inter-model docs; `wp-sec-agent/AGENTS.md` stub | Cursor + Ryan confirm |
| **3** | **Verify** | Tests for `brief`, `stats`, `is_live_watch_db`; readonly path stays independent | Cursor |
| **4** | **Productive** | `wp-sec-agent` client scans/reports (no convmem index churn) | Ryan + Cursor |
| **5** | **Inventory** | Map `~/Projects` → active / noisy / tool-state in WORKSPACE appendix | Codex or Cursor |
| **6** | **Plan** | Future invention boundaries (own root vs existing) — doc only | ChatGPT + Ryan |

Lanes 2–6 are **safe in parallel** with lane 1. Lane 4 is the best use of Ryan's time.

### Avoid until soak passes (all agree)

- Watch restarts, new watch roots, systemd limit experiments
- Ingest/watch lifetime refactors, mass `convmem index`
- Workspace registry / enforcer / manifests
- Declaring P0 or stability complete
- `propose_decision` CLI, Chroma HttpClient, handoff → STATUS migration (Tier 3)

### After soak passes (Kiro gate)

| # | Action |
|---|--------|
| 1 | Kiro stability sign-off (24h clean, peak < 3G, no oom-kill) |
| 2 | `STATUS.md` + archive old handoffs |
| 3 | Light corpus ingest of signed decisions |
| 4 | `propose_decision` / expansion features if still wanted |

---

## Model votes (as of this file)

| Model | Vote |
|-------|------|
| **Codex** | policy → verification → inventory → expansion; no watch churn during soak |
| **Kiro** | (inferred) convention doc OK; stability gate unchanged; no new milestone code |
| **Cursor** | agree Codex order; add commit + wp-sec-agent parallel lane; freeze watch after one debounce fix |
| **Sonnet** | *pending* — asked to confirm soak-safe list |
| **ChatGPT** | *pending* — asked to pick docs/inventory/planning lane |

---

## Ryan decision (proposed)

```
DECISION PROPOSED:
Choice: Adopt soak order Steps 0–6 above; freeze watch after Step 0c
Parallel: Codex monitors; Cursor does policy + tests; Ryan does wp-sec-agent
Rejected: Any watch/ingest changes until 24h pass or emergency
Status: PENDING HUMAN CONFIRM
```

— Cursor
