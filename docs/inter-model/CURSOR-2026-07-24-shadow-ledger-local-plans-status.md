# Local Cursor plans status (Shadow Ledger Phase 0) — not committed plan bodies

**Updated:** 2026-07-24  
**Purpose:** Preserve status of local `~/.cursor/plans/` files so a takeover
workspace knows they are superseded by draft Architecture PR #115. Plan file
bodies stay local (optional); do not treat pending todos as authorized work.

| Local path | Role | Status vs #115 |
|---|---|---|
| `~/.cursor/plans/shadow_ledger_phase_0_cadca832.plan.md` | Cursor revised Phase 0 implementation-oriented plan after Codex YELLOW | **Superseded for Architecture** by [#115](https://github.com/alanmz-crypto/convmem/pull/115). Todos (contract, audit corrections, shadow writer, hooks, tests, replay, inventory, report) remain pending and **unauthorized** until HITL + Execution |
| `~/.cursor/plans/codex_phase_0_work_order_940805a0.plan.md` | Package ChatGPT work order into Cursor→Codex handoff file + LATEST “requested not authored” | **Packaging execute skipped** — Ryan forwarded work order to Codex directly. Codex handoff file was never written. LATEST “requested” state superseded by Architecture **authored** on #115 |

## Related committed provenance

- ChatGPT advice handoff: `CURSOR-2026-07-24-shadow-ledger-phase0-chatgpt-handoff.md` (supersession banner added)
- Takeover brief: `CURSOR-2026-07-24-shadow-ledger-phase0-recon-takeover.md`
- Audit baseline: `docs/audit-ledger-first/` (+ README listing #115 correction debt)

## TL;DR

Local plans are historical input; GitHub draft #115 is the Architecture source of truth; no plan todo authorizes hooks.
