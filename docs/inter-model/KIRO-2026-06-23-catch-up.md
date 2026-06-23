# Cursor → Kiro: catch-up (everything after yesterday)

**To:** Kiro  
**From:** Cursor  
**Date:** 2026-06-23  
**Trigger:** Ryan asked to update Kiro; Kiro has no context past yesterday.

**Live ops:** `~/.local/share/convmem/brief.md` — read first. Do not duplicate numbers here.

---

## Session start (your lane)

```bash
convmem brief --stdout-only
convmem ask "<your question>"
# client work:
convmem ask "..." --site staging2.willowyhollow.com
```

Then `docs/inter-model/LATEST.md` only if ask misses.

**Sign-off rule:** use `propose_decision --approve` + ingest — never write "approved" in markdown alone.

---

## What changed since yesterday

### Shipped (Cursor, 2026-06-23)

| Item | Detail |
|------|--------|
| **brief** | Shows `LATEST.md` age/author + last 3 inter-model filenames; live VmPeak/VmRSS unchanged |
| **MCP** | `site` parameter on `search_fast`, `search`, `ask` (Crush parity with CLI `--site`) |
| **Protocol** | `brief` + `LATEST.md` + `convmem propose_decision -i` — no separate protocol doc |
| **Tests** | brief + MCP site unit tests passing |

### Watch (verified live)

- PID running **16h+** since 2026-06-22 15:35 CDT restart
- Journal: skip-only, no OOM/errors on this run
- **brief now:** VmPeak ~5.56G, VmRSS ~3.85G (from `/proc`, not `ps`)
- Soak: operational sign-off stands; memory high but flat under 4G cap

### Cross-model coordination (group consensus)

Four ideas judged (Cursor, Codex, DeepSeek, Sonnet). **Agreed direction:**

- **HANDOVER** = `brief` measurements + approved ledger  
- **SYNC** = `LATEST.md` pointer (3 bullets)  
- **Thread** = `docs/inter-model/*.md` archive only — **not** in Chroma  
- **Killed:** notification bus, full-text inter-model embed, AutoGen consensus, `soak --check` auto-gate  

**Interaction test (2026-06-23):**

| Works | Fails |
|-------|-------|
| `ask --site` on staging2 CSP | `ask` on Codex coordination prose |
| Approved decisions in corpus | Inter-model essays searchable |

### Decisions already accepted (you may have done these)

All **accepted** in `decisions-approved.jsonl` (7 total), including:

- `dec_prop_20260623_020946_0b91` — status claims via pipeline, not prose  
- `dec_prop_20260622_234011_d1ba` — CSP via nginx on staging2  
- `dec_prop_20260623_004023_44a1` — watch OOM fix / conditional soak passed  

If not yet ingested to Chroma: `convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert`

### Pending your sign-off (new)

**`convmem propose_decision --list`** — should show:

- **Coordination protocol v1 shipped** (proposed by cursor-session 2026-06-23, relates to discipline rule)

```bash
convmem propose_decision --approve <id> --signer kiro-review
convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

### Ryan decision pending (not Kiro build)

Two **plans** brainstormed for Ryan to choose:

- **Plan A — Ledger-first:** discipline + pipeline, minimal new code, 30-day habit proof  
- **Plan B — Substrate-first:** brief-history snapshots + metadata-only coord index + MCP `recent_notes`  

You do not need to pick — assess if Ryan asks.

---

## Asks

1. **Approve** the new coordination-protocol proposal via CLI (see above).  
2. **Confirm ingest** if approved decisions are not yet in Chroma (`convmem ask "status claims inter-model"` should hit `dec_prop_20260623_020946`).  
3. **Do not** re-litigate soak in prose — cite `brief` VmRSS/VmPeak or `dec_prop_20260623_004023_44a1`.  
4. **Seed prompt:** add one line to your session start — *approve via `propose_decision --approve`, not markdown.*

---

## Read order

1. `~/.local/share/convmem/brief.md`  
2. `docs/inter-model/LATEST.md`  
3. `docs/inter-model/CURSOR-2026-06-23-coord-direction.md`  
4. This file (routing only)

— Cursor
