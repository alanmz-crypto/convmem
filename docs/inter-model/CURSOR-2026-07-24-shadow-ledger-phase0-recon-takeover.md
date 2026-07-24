# Cursor recon → one-workspace takeover (Shadow Ledger Phase 0)

**Updated:** 2026-07-24  
**From:** Cursor recon chat `f15c9bb9-bcbb-4252-9fe1-426f559b281d` (WS-cursor-recon)  
**Why:** Multi-chat residue + Codex Architecture closeout were split across
workspaces. This document + the salvage PR put everything a single takeover
workspace needs on GitHub.

## Consequence for Ryan / next workspace

You can close sibling Cursor chats after this salvage lands. Review draft
Architecture [#115](https://github.com/alanmz-crypto/convmem/pull/115). Do
**not** implement hooks until HITL + later Execution plan.

## Already on GitHub (do not redo)

| Artifact | Location |
|---|---|
| Research pack (backup + Neutral) | [#114](https://github.com/alanmz-crypto/convmem/pull/114) **MERGED** @ `8725813` on `main` (pack tip was `64d714b` on branch) |
| Shadow Ledger Phase 0 Architecture | Draft [#115](https://github.com/alanmz-crypto/convmem/pull/115) @ `c9a5c70` — Option B, eleven decisions locked, Chroma still Tier-1, HITL stop |
| Architecture branch | `docs/2026-07-24-shadow-ledger-phase0-architecture` |
| Optional local Codex worktree | `/tmp/convmem-shadow-ledger-phase0-architecture` (matches remote; **no open Codex workspace required**) |

## Salvaged in this PR (was local-only)

**Salvage PR:** [#116](https://github.com/alanmz-crypto/convmem/pull/116) @ `05c5567`  
**Branch:** `docs/2026-07-24-shadow-ledger-phase0-salvage`

| Artifact | Path |
|---|---|
| Qwen audit baseline (8 files) + status README | `docs/audit-ledger-first/` |
| ChatGPT→Codex advice handoff | `docs/inter-model/CURSOR-2026-07-24-shadow-ledger-phase0-chatgpt-handoff.md` |
| Local plans status (paths only) | `docs/inter-model/CURSOR-2026-07-24-shadow-ledger-local-plans-status.md` |
| Workspace coordination board snapshot | `docs/inter-model/COORD-2026-07-24-shadow-ledger-workspaces-BOARD.md` |
| Coord Round 1–3 prompts | `docs/inter-model/PROMPT-ROUND-*.md` |
| This takeover brief | this file |
| LATEST Active pointer | `docs/inter-model/LATEST.md` |

## Architecture summary (#115) — what was decided

Codex authored Architecture only (no Execution/VERIFY, no runtime):

- **Option B:** opt-in `ChromaStore` mutation observer / sink
- Observes confirmed `knowledge_units` mutations only (not `conversation_summaries`)
- Chroma commits first; shadow append is synchronous/durable and **visible on failure**; never rolls back Chroma
- Phase 0 proves **post-activation delta** only (not full corpus rebuild)
- Crash window Chroma-success / shadow-miss is **detectable**, not auto-healed
- Disposable replay must force-disable shadow recording
- Shadow is **not** a backup/restore source in Phase 0
- Ends with: `Active phase lane must stop here. Await HITL.`

Largest trade-off named by Codex: post-Chroma `fsync` latency vs honesty about the crash gap.

## Planning chain (do not re-litigate)

1. ChatGPT ledger-first audit brief → Qwen eight-file audit → **YELLOW**
2. Claude: accept YELLOW; approve **shadow only**
3. ChatGPT §10: ledger→Chroma restore is **end-state**, not Phase 0
4. Cursor revised plan (local): `~/.cursor/plans/shadow_ledger_phase_0_cadca832.plan.md`
5. ChatGPT Codex work order → Option B + 11 decisions → Architecture-only output
6. Cursor packaging plan (local, **not executed**): `~/.cursor/plans/codex_phase_0_work_order_940805a0.plan.md` — would have written a Codex handoff file; Ryan sent Codex the work order directly instead
7. Codex → draft PR #115 @ `c9a5c70`

## Local Cursor plans (not committed — paths only)

| Plan | Status |
|---|---|
| `~/.cursor/plans/shadow_ledger_phase_0_cadca832.plan.md` | Revised Cursor Phase 0 plan; todos still pending; **superseded as final Architecture by #115** |
| `~/.cursor/plans/codex_phase_0_work_order_940805a0.plan.md` | Packaging plan; Codex handoff file **never written**; LATEST “requested not authored” step **superseded** by #115 authored |

## Workspace coordination outcome

| WS | Chat id | Role | Disposition |
|---|---|---|---|
| WS-main-cursor | `ac56bcaf-…` | Research-pack #114 + backup/Neutral memo thread | Prefer as live takeover on shared checkout **or** any single chat after this salvage |
| WS-cursor-shadow-handoff | `0b7f1390-…` | Authored ChatGPT handoff + packaging plan | Close after salvage |
| WS-cursor-recon | `f15c9bb9-…` | Verified #115; wrote coord prompts; this salvage | Close after salvage PR |
| Codex | _(none open)_ | Authored #115 in `/tmp` worktree | No open workspace; GitHub is enough |

Ryan ruled: Codex does **not** need to file coordination Round 1.

## Shared checkout residue (may still be dirty locally)

Even after this PR, `/home/lauer/Projects/convmem` on
`docs/2026-07-24-research-pack-backup-neutral` may still show untracked/dirty
copies of audit/handoff/LATEST. Those are **duplicates of this salvage** —
safe to discard from that working tree after this PR is on GitHub, without
committing them onto the research-pack branch.

## Hard stops (unchanged)

- No production shadow hooks without Ryan HITL on #115 + later Execution
- No cutover, Neutral extraction, restore-order flip, schema freeze
- No committing audit onto the research-pack branch
- Squash OK on salvage PR

## Suggested next steps for the one live workspace

1. Ryan HITL on [#115](https://github.com/alanmz-crypto/convmem/pull/115)
2. Optional: docs-only correction pass on `docs/audit-ledger-first/` per #115 table
3. Only after Architecture approval: Codex may author `EXECUTION-shadow-ledger-phase0.md`
4. Cursor Execute only after Execution HITL — activation still separate

## TL;DR

Architecture is on draft #115; this salvage PR parks the audit baseline,
ChatGPT handoff, coordination board, and takeover brief so one Cursor
workspace can continue without the sibling chats.
