# Cross-arc consolidation synthesis — 2026-07-22

**Who:** Cursor (designated consolidator this turn)  
**What:** One roster of today’s `STANCE-2026-07-22-*.md` classifications for Ryan HITL  
**When:** 2026-07-22; stances collected from unmerged stance branches (not yet on `main`)  
**Why:** ~10 open agents classified COMBINE/DONE/SOLO-CONTINUE; shared memory bus needs a single stop/merge map  
**How:** Cite stances; do not rewrite them; no merges, ledger approvals, record blocks, or new product implementation

**Sources:** eight stance files under `docs/inter-model/STANCE-2026-07-22-*.md` (all Cursor lane; no Crush/Kiro/Codex stance files found for this date). Also `LATEST.md` Active handoff (PR Steward `#92`, dedupe GATE `#86`, P1.3 soak closed, CI Wait `#81`, who-fixes closed).

**Coverage note:** Only Cursor-authored stances appeared on `origin/docs/2026-07-22-stance-*` tips. If Ryan forwards chat Class lines from other lanes, treat this file as incomplete until those are appended.

---

## Roster

| Agent/lane | Class | Arc (one line) | Stance path | Evidence tip / PR |
|---|---|---|---|---|
| Cursor | DONE | BugBot PR-native external review gate | [`STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md`](STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md) | `#91` → `db3e5e0`; adjacent `#96` Steward 2→3 |
| Cursor | **COMBINE** | Copilot CLI Tier A session wiring still unmerged | [`STANCE-2026-07-22-cursor-copilot-cli-wiring.md`](STANCE-2026-07-22-cursor-copilot-cli-wiring.md) | `feat/2026-07-19-copilot-cli-integration` @ `eb6f89d`; overlap `docs/2026-07-19-response-tldr` @ `d0dbda6` |
| Cursor | DONE | Model-quality eval harness (detection only) | [`STANCE-2026-07-22-cursor-eval-harness-done.md`](STANCE-2026-07-22-cursor-eval-harness-done.md) | `004626a` + `d4e44ca`; ledger `dec_prop_20260705_011902_3adf` |
| Cursor | DONE | Cursor MCP Roots shell brief boundary | [`STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md`](STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md) | `#87` → `eb84472` |
| Cursor | DONE | P1.3 soak + semantic-dedupe default GATE closed | [`STANCE-2026-07-22-cursor-p13-dedupe-closed.md`](STANCE-2026-07-22-cursor-p13-dedupe-closed.md) | brief `#85`; GATE `#86`/`dba9795` |
| Cursor | DONE | R2b capture auth parked after T4 | [`STANCE-2026-07-22-cursor-r2b-capture-parked.md`](STANCE-2026-07-22-cursor-r2b-capture-parked.md) | `#67` → `c0f06f5`; next = Ryan T5 HITL only |
| Cursor | DONE | Session arcs closed (dedupe + debate + Steward residual) | [`STANCE-2026-07-22-cursor-session-arcs-done.md`](STANCE-2026-07-22-cursor-session-arcs-done.md) | `#86`, `#94`/`5a378b3`, `#95`/`#96`, `#91` |
| Cursor | DONE | Stage 4 closed + residual tool-output draft | [`STANCE-2026-07-22-cursor-stage4-residual-closed.md`](STANCE-2026-07-22-cursor-stage4-residual-closed.md) | `#46`/`#48`; residual plan only |

**Counts:** COMBINE 1 · DONE 7 · SOLO-CONTINUE 0

---

## COMBINE clusters

### Cluster 1 — Copilot CLI land (only live COMBINE)

**Members:** `cursor-copilot-cli-wiring` (COMBINE); soft overlaps: Stage 4 residual (Crush/token hygiene), MCP Roots (MCP surface discipline), HITL `#54` lifecycle (do not re-litigate), Kiro `response-tldr` generate/deploy naming.

**Merge thesis:** One rebased PR from `feat/2026-07-19-copilot-cli-integration` that keeps the **adapter + watch/MCP omit-key** product, folds a **single** always-on example filename (feat vs Kiro `copilot-instructions*.example.md`), then Ryan-run `deploy-agent-protocol.sh`. Do not land generate/deploy alone (watch stays blind) or re-inject `DEEPSEEK_API_KEY` into mcp-config.

**Must survive (cite stance Keep):** session JSONL adapter + `copilot` tool tag; watch skips for Copilot live DBs; always-on `~/.copilot/copilot-instructions.md` for plain `copilot`; MCP loads `env.local` without embedding the key; doctor `mcp_copilot`.

### Cluster 2 — Shared-bus / LATEST freshness (meta, not product COMBINE)

**Members (all DONE, same ask):** BugBot, MCP Roots, R2b parked, session-arcs — each asks consolidator/`LATEST.md` refresh so Active handoff stops claiming stale “unauthorized / open caveat” lines.

**Merge thesis:** One **docs-only** LATEST refresh (Ryan-authorized) covering at least: `#91` BugBot land; `#87` closes Stage 3 Cursor `$HOME` MCP caveat (residual = agent↔MCP bridge); `#67` R2b **code** landed / **B-Accept+live capture still unauthorized**; `#94` debate archive + `#96` Steward VERIFY 2→3. Do not mix product follow-ons into that PR.

### Cluster 3 — Retrieval + default-band hygiene (DONE, consolidate conclusions only)

**Members:** `cursor-p13-dedupe-closed`, `cursor-session-arcs-done`; already reflected in `LATEST.md` (P1.3 soak CLOSED, semantic-dedupe GATE ACCEPTED, who-fixes CLOSED).

**Merge thesis:** Treat as one closed chapter. Default band exact-title @ ≥0.999 pending=0; ~1055 lower-band pending **not authorized**; Phase D separate GATE. Kill any agent impulse to “finish the queue.”

---

## DONE park list

Stop these lanes. Residual only if Ryan reopens:

| Arc | Park residual (do not thrash) |
|---|---|
| BugBot `#91` | Org fail-on-unresolved / branch-protection; non-Cursor fallback reviewer |
| Eval harness | H-H (synthesis judge excerpts); ROADMAP remediation triad; do not conflate with Gate 1 `#44` embeddings |
| MCP Roots `#87` | Live panel `stats` / Connection-closed bridge; worktree delete after MCP on prod path |
| P1.3 + dedupe GATE | Next similarity bands; Phase D; live `semantic_dedupe` job while backlog ≫ `queue_max_depth` |
| R2b `#67` | T5 ACCEPT AND GRANT → T6 one-shot → T7 VERIFY → T8 stop before B-Accept; fresh digest if draft >1h |
| Session arcs | Stale open PRs `#33`/`#32`/`#31`/`#6`/`#37` cleanup-day only; do not reopen `#34` |
| Stage 4 | Residual Crush tool-output arc needs HITL architecture first (~98–107k baseline) |

---

## SOLO-CONTINUE list

**None** in today’s stance set.

If an agent claims SOLO-CONTINUE without a stance file, treat as unauthorized until they write `STANCE-2026-07-22-<lane>-<slug>.md` and re-classify.

---

## Conflicts / double-work to kill

1. **Dual Copilot instruction pipelines** — feat example name vs Kiro `d0dbda6` example name can double-write live `copilot-instructions.md`. Pick one before PR.
2. **“Eval harness” bucket** — generative quality detector (`004626a`) ≠ Gate 1 embedding A/B (`#44`/`3b2790f`). Do not merge designs or VRAM assumptions.
3. **Hygiene GATE ≠ lower-band license** — `#86` accepted exact@0.999 only; approving 0.98/0.95/0.92 or Phase D without new GATE is thrash.
4. **BugBot ≠ Copilot audit ≠ Steward** — scarce audit lane and routine PR gate must stay independent (stance Keep on BugBot).
5. **R2b LATEST drift** — old “implementation unauthorized” line after `#67` invites agents to re-plan capture; code parked, grant still Ryan-only.
6. **MCP Roots vs “Roots deprecated” folklore** — do not strip `list_roots` coercion from retrieval chatter.
7. **Checkout contention** — multiple agents sharing one worktree caused stance commits to land on wrong branches today; prefer `convmem work start` / `--worktree` and explicit `${branch}:refs/heads/${branch}` push (zsh `$branch:refs` is unsafe).
8. **Stale handoff files** — `CURSOR-2026-07-22-semantic-dedupe-hygiene.md` “Plan packet ready” language loses to `LATEST.md` + `#86` tip.

---

## Proposed next actions for Ryan only

Authorize / park / assign — **no merges performed by consolidator; no record blocks; no new implementation.**

| # | Decision | Suggested disposition |
|---|---|---|
| 1 | **Copilot CLI land?** | Authorize one PR from rebased `feat/2026-07-19-copilot-cli-integration` **or** abandon adapter and keep local-only overlays. Pick winning example filename. |
| 2 | **LATEST refresh?** | Authorize a docs-only PR updating Active handoff for `#91`, `#87`, `#67` park wording, `#94`/`#96` (and leave product arcs closed). |
| 3 | **Dedupe next band / Phase D?** | Park (~1055 pending) **or** GATE an explicit threshold / Phase D — do not imply from `#86`. |
| 4 | **R2b resume?** | Fresh T4 recompute + T5 ACCEPT AND GRANT, **or** abandon/quarantine draft `2026-07-21-r2b-capture-01`. |
| 5 | **Eval H-H / remediation?** | Leave deferred **or** authorize tiny judge-excerpt fix and/or one ROADMAP remediation option. |
| 6 | **Stage 4 residual tool-output?** | Leave deferred **or** authorize HITL (Kiro) on draft direction before Cursor codes. |
| 7 | **MCP bridge verify?** | Confirm panel `stats` after restart closes `#87` live verify; else authorize separate bridge-debug arc. OK to delete mcp-roots worktree once MCP args point at prod. |

---

## Consolidator stop

This file is the consolidation deliverable. Stance branches remain unmerged unless Ryan asks for a PR. Do not open product work from this synthesis.
