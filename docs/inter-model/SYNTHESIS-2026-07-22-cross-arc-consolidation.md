# Cross-arc consolidation synthesis — 2026-07-22

**Consolidator:** Cursor (designated this turn)  
**Branch:** `docs/2026-07-22-cross-arc-consolidation-synthesis`  
**Sources:** all eight `docs/inter-model/STANCE-2026-07-22-*.md` (copied onto this branch for citation; bodies not rewritten) + chat Class lines from agent transcripts + `docs/inter-model/LATEST.md` as of consolidation.  
**Scope:** classify / park / assign only — no merges, no ledger `record`, no product implementation.  
**Consolidator pass:** 2026-07-22T21:05Z — roster re-verified (COMBINE 1 / DONE 9 / SOLO-CONTINUE 0); no new stances found.

Stance files currently live on **unmerged docs branches** (one stance each). Cite them; do not treat absence from `main` as “stance missing.”

| Stance file | Holding branch (local/origin) |
|---|---|
| `STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md` | `docs/2026-07-22-2026-07-22-stance-mcp-roots-boundary` |
| `STANCE-2026-07-22-cursor-r2b-capture-parked.md` | `docs/2026-07-22-2026-07-22-stance-r2b-capture-parked` |
| `STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md` | `docs/2026-07-22-stance-bugbot-gate-done` |
| `STANCE-2026-07-22-cursor-copilot-cli-wiring.md` | `docs/2026-07-22-stance-copilot-cli-wiring` |
| `STANCE-2026-07-22-cursor-session-arcs-done.md` | `docs/2026-07-22-stance-cursor-session-arcs-done` |
| `STANCE-2026-07-22-cursor-eval-harness-done.md` | `docs/2026-07-22-stance-eval-harness-done` |
| `STANCE-2026-07-22-cursor-p13-dedupe-closed.md` | `docs/2026-07-22-stance-p13-dedupe-closed` |
| `STANCE-2026-07-22-cursor-stage4-residual-closed.md` | `docs/2026-07-22-stance-stage4-residual` |

---

## Roster

| Agent / lane | Class | Arc (one line) | Stance path |
|---|---|---|---|
| Cursor — MCP Roots | DONE | Close `$HOME` cwd re-brief via Roots omit; [#87](https://github.com/alanmz-crypto/convmem/pull/87) `eb84472` | [`STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md`](STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md) |
| Cursor — R2b capture | DONE | Phase-scoped R2b auth landed [#67](https://github.com/alanmz-crypto/convmem/pull/67) `c0f06f5`; live capture parked pre–T5 | [`STANCE-2026-07-22-cursor-r2b-capture-parked.md`](STANCE-2026-07-22-cursor-r2b-capture-parked.md) |
| Cursor — BugBot gate | DONE | PR-native BugBot External Review gate [#91](https://github.com/alanmz-crypto/convmem/pull/91) `db3e5e0` | [`STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md`](STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md) |
| Cursor — Copilot CLI wiring | COMBINE | Session adapter + watch + always-on for plain `copilot`; **not on `main`** | [`STANCE-2026-07-22-cursor-copilot-cli-wiring.md`](STANCE-2026-07-22-cursor-copilot-cli-wiring.md) |
| Cursor — session arcs (dedupe/debate/Steward residual) | DONE | Default-band hygiene + `#94` debate archive + Steward VERIFY 2→3 (`#95`/`#96`) | [`STANCE-2026-07-22-cursor-session-arcs-done.md`](STANCE-2026-07-22-cursor-session-arcs-done.md) |
| Cursor — eval harness | DONE | Local-first quality detector shipped; remediation + H-H deferred | [`STANCE-2026-07-22-cursor-eval-harness-done.md`](STANCE-2026-07-22-cursor-eval-harness-done.md) |
| Cursor — P1.3 soak + dedupe GATE | DONE | P1.3 soak CLOSED; semantic-dedupe GATE ACCEPTED `#86` `dba9795` | [`STANCE-2026-07-22-cursor-p13-dedupe-closed.md`](STANCE-2026-07-22-cursor-p13-dedupe-closed.md) |
| Cursor — Stage 4 + residual | DONE | Stage 4 digest demotion CLOSED `#46`/`#48`; Crush tool-output residual deferred | [`STANCE-2026-07-22-cursor-stage4-residual-closed.md`](STANCE-2026-07-22-cursor-stage4-residual-closed.md) |
| Cursor — LATEST after PR #19 (Jul 13 chat) | DONE | Propose-only LATEST reconcile; Ryan declined apply; Track A only | **none** (no unique residue) |
| Cursor — Gate 1 / R2a rescue chat | DONE | Hermetic auth + VERIFY on `main`; no unique off-main residue | **none** |

**Class counts (written stances + chat-only):** COMBINE **1** · DONE **9** · SOLO-CONTINUE **0**.

---

## COMBINE clusters

### C1 — Copilot CLI surface wiring (only true COMBINE Class)

**Merge thesis:** One land path for Copilot as a Tier A surface: session ingest/watch/MCP + always-on instructions — fold Cursor feat tip with Kiro generate/deploy naming, do not ship either alone.

- Stance: [`STANCE-2026-07-22-cursor-copilot-cli-wiring.md`](STANCE-2026-07-22-cursor-copilot-cli-wiring.md) (Class COMBINE).
- Overlap: Kiro tip `d0dbda6` on `docs/2026-07-19-response-tldr` (generate/deploy only; different example filename).
- Settled elsewhere (do not re-litigate): [#54](https://github.com/alanmz-crypto/convmem/pull/54) Copilot lifecycle / Sol-High; DeepSeek V4-Pro *substitute* audit ≠ session adapter.
- Keep: `adapters/copilot_session_jsonl.py`, watch skips, `~/.copilot/copilot-instructions.md` for plain `copilot`, no `DEEPSEEK_API_KEY` in mcp-config.
- Ryan pick: which example name wins; authorize PR from rebased `feat/2026-07-19-copilot-cli-integration` vs abandon-to-local-overlays.

### C2 — LATEST.md truth refresh (DONE agents; consolidator cluster)

**Merge thesis:** Single LATEST Active-handoff edit that cites landed SHAs without reopening product arcs — Stage 3 `$HOME` caveat → `#87`; R2b “no implementation” → “implementation landed, live capture unauthorized”; add BugBot `#91` if missing; do not imply lower-band dedupe or Stage 4 residual are open.

- Drivers: mcp-roots, r2b-parked, bugbot, session-arcs-done (all recommend LATEST touch).
- **Do not** re-apply Jul 13 propose-only LATEST draft (chat DONE, no stance).
- Conservative: docs-only PR; no protocol churn; no deploy unless Ryan asks.

### C3 — Retrieval / ranking / hygiene park (DONE overlap)

**Merge thesis:** P1.3 + who-fixes + default-band semantic dedupe are one closed story; remaining ~1055 pending + Phase D need a **new** Ryan GATE — not implied by `#86`.

- Stances: p13-dedupe-closed + session-arcs-done (dedupe/debate/Steward slice).
- Kill: reading stale `CURSOR-2026-07-22-semantic-dedupe-hygiene.md` “awaiting GATE” header; re-enabling live `semantic_dedupe` while backlog ≫ `queue_max_depth`; reopening `#34` (superseded by `#94`).

### C4 — Review / Delivery gates adjacency (DONE; keep distinct)

**Merge thesis:** BugBot, PR Steward, and CI Wait are adjacent HITL surfaces — cite together in LATEST if refreshing, but do not collapse scarce Copilot audit or Steward into BugBot “someone looked.”

- Stances: bugbot-pr-gate-done; session-arcs Steward residual; LATEST already has Steward + CI Wait.
- Kill: treating Steward comment authority as BugBot evidence; treating CI Wait playbook as BugBot policy.

### C5 — R2 eval path park (DONE; Ryan HITL only)

**Merge thesis:** R2b code lane closed at T4 draft; next steps are Ryan T5–T8 only. R2a further work / Gate 2 / promotion remain unauthorized without new grant.

- Stance: r2b-capture-parked; chat-only Gate 1/R2a DONE.
- Kill: accepting stale T4 snapshot (>1h); inventing sidecar/grant from agents; marking VERIFY PASS from chat.

---

## DONE park list

Stop these agents; residual only if Ryan reopens:

| Arc | Evidence | Residual (reopen only if Ryan says so) |
|---|---|---|
| MCP Roots `#87` | `eb84472` on `main` | Panel/`stats` live Roots proof; agent `CallMcpTool` “Connection closed” bridge-debug; delete worktree when MCP on prod path |
| R2b `#67` | `c0f06f5`; draft under `authorizations/r2b/2026-07-21-r2b-capture-01/` | Fresh T4 → T5 ACCEPT AND GRANT → T6–T8; abandon/quarantine draft |
| BugBot `#91` | `db3e5e0` | Org branch-protection settings; non-Cursor fallback reviewer |
| Session arcs (dedupe/debate/Steward residual) | `#86` GATE; `#94`; `#95`/`#96` | Next dedupe band / Phase D GATE; optional LATEST refresh |
| P1.3 + dedupe GATE | LATEST soak CLOSED + `#86` | Same band/Phase D GATE; no Day+N soak thrash |
| Eval harness | on `main`; ledger `dec_prop_20260705_011902_3adf` | H-H judge excerpts; ROADMAP remediation option pick |
| Stage 4 | `#46`/`#48` CLOSED | Residual Crush tool-output HITL (draft plan only) |
| LATEST-after-#19 Jul 13 | Track A; no apply | none — MCP caveat owned by `#87` stance |
| Gate 1 / R2a chat | on `main` | further R2a / Gate 2 / promotion (already unauthorized on LATEST) |

---

## SOLO-CONTINUE list

**None.** No stance or chat Class reported SOLO-CONTINUE.

If Ryan later authorizes work, preferred owners (not auto-continue):

| Possible reopen | Keep doing | Must ignore |
|---|---|---|
| Copilot CLI land (after Ryan pick) | One rebased PR + deploy | Lifecycle `#54` re-litigation; dual example filenames |
| LATEST docs-only refresh | Cite `#87` / `#67` / `#91` accurately | Reopening product arcs; lower-band dedupe |
| R2b T5+ | Ryan HITL grant path only | Cursor coding / Bugbot thrash / live capture without grant |
| Stage 4 residual tool-output | New HITL architecture first | Folding into P1.3 / dedupe |
| Eval H-H or remediation | Tiny scoped follow-up | Treating advisory judges as CI gates |

---

## Conflicts / double-work to kill

1. **Two Copilot instruction pipelines** (`copilot-instructions-convmem.example.md` vs `copilot-instructions.example.md`) — pick one before any PR.
2. **LATEST Stage 3 `$HOME` caveat** without citing `#87` — re-opens a closed product gap.
3. **LATEST R2b “no implementation authorized”** after `#67` — false; live capture still unauthorized.
4. **Stale dedupe handoff header** vs LATEST GATE ACCEPTED — prefer LATEST + `#86`.
5. **Hygiene GATE ⇒ lower bands / Phase D** — not authorized.
6. **BugBot ⇄ Copilot audit ⇄ Steward** collapse — independent roles.
7. **Eval harness ⇄ Gate 1 embedding A/B** — different eval kinds; don’t merge into one VRAM/dependency story.
8. **Stage 4 residual ⇄ MCP `[:500]` clip** — residual is Crush bash/view dumps, not MCP-only.
9. **Shared checkout thrash** — many stance branches on one tree; use `--worktree` / don’t switch under peers.
10. **Jul 13 unused LATEST proposal** — do not resurrect; superseded.

---

## Proposed next actions for Ryan only

Authorize / park / assign — consolidator does **not** merge or implement:

1. **Park (default):** all DONE Cursor agents above — no further coding this cycle.
2. **Assign COMBINE:** Copilot CLI — pick land path (rebase `feat/2026-07-19-copilot-cli-integration` + fold Kiro naming **or** abandon adapter / keep local overlays) and which example filename wins.
3. **Authorize docs-only (optional):** one LATEST Active-handoff refresh PR covering `#87` caveat close, `#67` implementation-vs-live-capture wording, `#91` BugBot land line; optionally land the eight stance files + this synthesis onto `main` via squash/docs PR.
4. **Authorize or abandon:** R2b draft `2026-07-21-r2b-capture-01` (fresh T4→T5 ACCEPT AND GRANT vs quarantine).
5. **Defer unless asked:** next dedupe band / Phase D; Stage 4 tool-output HITL; eval H-H; MCP panel bridge-debug; soft-close `record` for any of these arcs.

---

## Consolidator notes

- Brief flagged LATEST stale vs newer inter-model files (stances) — expected until a LATEST refresh or stance land.
- This synthesis cites stances by path; it does **not** copy or edit stance bodies.
- Path-sensitive: `~/.cursor/mcp.json` must stay on **prod** `mcp_server.py` (not deleted worktrees); Copilot always-on path is `~/.copilot/copilot-instructions.md`.
