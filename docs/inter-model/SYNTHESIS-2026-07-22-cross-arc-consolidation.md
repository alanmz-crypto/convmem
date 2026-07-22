# Synthesis: Cross-arc consolidation (2026-07-22)

```text
Consolidator: Cursor (designated this turn)
Sources:      docs/inter-model/STANCE-2026-07-22-*.md (8 files, Cursor lane)
              docs/inter-model/LATEST.md (Active handoff)
              Protocol: doctor PASS; brief; unresolved (11 — staging2 + old retrieval obs)
Not found:    No crush/kiro/codex/other STANCE-2026-07-22-*.md on origin
              No SOLO-CONTINUE class in filed stances
```

**Purpose:** One shared-bus picture of what to park, what to combine, and what Ryan
must authorize — **not** new implementation, merges, or ledger records.

**Stance fidelity:** Stances below are cited, not rewritten. Product claims prefer
`LATEST.md` + merged PR tips when a stance header is older than GATE close.

---

## 1. Roster

| Lane / agent | Class | Arc (one line) | Stance path |
|--------------|-------|----------------|-------------|
| Cursor | DONE | BugBot PR-native external review gate shipped | [`STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md`](STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md) |
| Cursor | **COMBINE** | Copilot CLI session ingest + always-on still unmerged | [`STANCE-2026-07-22-cursor-copilot-cli-wiring.md`](STANCE-2026-07-22-cursor-copilot-cli-wiring.md) |
| Cursor | DONE | Model-quality eval harness (detection only) | [`STANCE-2026-07-22-cursor-eval-harness-done.md`](STANCE-2026-07-22-cursor-eval-harness-done.md) |
| Cursor | DONE | MCP Roots shell brief boundary (#87) | [`STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md`](STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md) |
| Cursor | DONE | P1.3 live soak + semantic-dedupe default GATE | [`STANCE-2026-07-22-cursor-p13-dedupe-closed.md`](STANCE-2026-07-22-cursor-p13-dedupe-closed.md) |
| Cursor | DONE | R2b capture auth parked after T4 (impl on main; live capture unauthorized) | [`STANCE-2026-07-22-cursor-r2b-capture-parked.md`](STANCE-2026-07-22-cursor-r2b-capture-parked.md) |
| Cursor | DONE | Session arcs: dedupe GATE + debate archive + Steward VERIFY 2→3 | [`STANCE-2026-07-22-cursor-session-arcs-done.md`](STANCE-2026-07-22-cursor-session-arcs-done.md) |
| Cursor | DONE | Stage 4 closed; tool-output residual draft only | [`STANCE-2026-07-22-cursor-stage4-residual-closed.md`](STANCE-2026-07-22-cursor-stage4-residual-closed.md) |
| Crush / Kiro / Codex / other | — | **No stance file filed this wave** | — |

---

## 2. COMBINE clusters

### Cluster A — Copilot CLI Tier-A wiring (only active COMBINE)

**Merge thesis:** One land path for Copilot session ingest + watch + doctor +
always-on instructions; fold Kiro generate/deploy naming into the feat tip;
do **not** ship generate/deploy alone without the adapter.

| Piece | Evidence |
|-------|----------|
| Feat tip (adapter + MCP env load) | `feat/2026-07-19-copilot-cli-integration` @ `eb6f89d` — **no PR** |
| Parallel instruction pipeline | `docs/2026-07-19-response-tldr` @ `d0dbda6` (Kiro) — different example filename |
| Already settled (do not re-litigate) | HITL Copilot lifecycle [#54](https://github.com/alanmz-crypto/convmem/pull/54); R2a/DeepSeek *substitute* role ≠ session plumbing |
| Ryan pick needed | Which example name wins; authorize PR vs abandon adapter / keep local-only overlays |

Cite: `STANCE-2026-07-22-cursor-copilot-cli-wiring.md`.

### Cluster B — Shared-bus hygiene (DONE arcs that share a LATEST refresh)

**Merge thesis:** Not code merge — one **docs-only LATEST Active-handoff refresh**
so brief stops flagging STALE and so closed gaps are not re-opened from stale
bullets.

| Closed item | Tip / PR | Stale risk if LATEST lags |
|-------------|----------|---------------------------|
| BugBot gate | [#91](https://github.com/alanmz-crypto/convmem/pull/91) `db3e5e0` | Missing from Active handoff |
| Debate archive | [#94](https://github.com/alanmz-crypto/convmem/pull/94) `5a378b3` | Revive [#34](https://github.com/alanmz-crypto/convmem/pull/34) |
| Steward VERIFY 2→3 | [#96](https://github.com/alanmz-crypto/convmem/pull/96) `7a0c344` | Already noted on LATEST tip line |
| MCP Roots / #19 caveat | [#87](https://github.com/alanmz-crypto/convmem/pull/87) `eb84472` | Stage 3 still says Cursor `$HOME` open caveat |
| R2b implementation | [#67](https://github.com/alanmz-crypto/convmem/pull/67) `c0f06f5` | LATEST still reads like “no implementation” |
| P1.3 soak + dedupe GATE | [#86](https://github.com/alanmz-crypto/convmem/pull/86) `dba9795` | Already on LATEST; keep Phase D / lower bands unauthorized |

Cite: bugbot, session-arcs, mcp-roots, r2b, p13-dedupe stances.

---

## 3. DONE park list (stop; residual only if Ryan reopens)

| Arc | Stop because | Residual (Ryan-only reopen) |
|-----|--------------|------------------------------|
| P1.3 soak + dedupe default GATE | LATEST GATE ACCEPTED; soak CLOSED | Next similarity band; Phase D snapshot steering |
| Session arcs (debate + Steward residual) | `#94`/`#95`/`#96` merged | Stale PR cleanup day (`#33`/`#32`/`#31`/`#6`/`#37`) if asked |
| BugBot PR gate | `#91` merged `db3e5e0` | Org branch-protection BugBot settings; soft-close record if Ryan says closing |
| MCP Roots brief boundary | `#87` merged `eb84472` | Panel/live `CallMcpTool` bridge debug; delete old worktree when MCP stays on prod |
| R2b capture | Code on main; Cursor lane parked pre–B-Accept | Fresh T4 → T5 ACCEPT AND GRANT → T6–T8; or abandon draft `2026-07-21-r2b-capture-01` |
| Eval harness (detection) | On main; ledger already records ship | H-H judge excerpt fix; remediation options (ROADMAP) |
| Stage 4 + tool-output residual | Stage 4 CLOSED; residual is draft direction only | HITL for Crush tool-hygiene arc |

---

## 4. SOLO-CONTINUE list

**None** in filed `STANCE-2026-07-22-*.md`.

If a silent lane believes it is SOLO-CONTINUE: file a stance or stop — consolidator
has no durable Class line to protect.

---

## 5. Conflicts / double-work to kill

| Kill this | Why |
|-----------|-----|
| Blind `--approve-dedupe all` / lower-band drain | Default GATE closed; ~1055 pending **not authorized** |
| Re-open P1.3 ranking / source_trust / Crush `ksweep-routing` | Soak PASS; stopgap retired |
| Revive debate PR [#34](https://github.com/alanmz-crypto/convmem/pull/34) | Superseded by [#94](https://github.com/alanmz-crypto/convmem/pull/94) |
| Treat R2b T4 draft as ACCEPTed / run live capture | Snapshot stale; needs ACCEPT AND GRANT |
| Merge only Kiro Copilot generate/deploy without adapter | Leaves `main` blind to Copilot sessions |
| Dual Copilot example filenames both “winning” | Overwrite risk on `~/.copilot/copilot-instructions.md` |
| Fold BugBot into Copilot audit or Steward “someone looked” | Collapses scarce audit vs routine gate |
| Fold Stage-4 residual into P1.3/dedupe | Ranking ≠ Crush tool-dump tokens |
| Treat advisory eval judge scores as CI gates | Shipped policy: non-independent scores informational only |
| Read pre-GATE hygiene handoff header as current | Prefer LATEST + `#86` tip |
| Re-assert LATEST “R2b implementation unauthorized” | Implementation shipped (#67); **live capture** still unauthorized |
| Re-open Stage 3 Cursor `$HOME` caveat without citing #87 | Product gap closed; residual is agent↔MCP bridge |

---

## 6. Proposed next actions for Ryan only

Authorize / park / assign — **no merges by consolidator; no record blocks; no new code**.

| # | Decision | Options |
|---|----------|---------|
| 1 | **LATEST refresh** | Authorize a docs-only PR updating Active handoff for `#91`, `#87`/#19 caveat, R2b impl-vs-capture wording, `#94` — or leave brief STALE until you do it |
| 2 | **Copilot CLI land** | Authorize one PR from rebased `feat/2026-07-19-copilot-cli-integration` (fold Kiro naming) **vs** abandon adapter / keep local overlays; pick example filename |
| 3 | **Dedupe backlog** | GATE next band (name threshold) **vs** leave ~1055 pending parked; Phase D separate |
| 4 | **R2b resume** | Fresh T4 + T5 ACCEPT AND GRANT **vs** quarantine/abandon `2026-07-21-r2b-capture-01` |
| 5 | **Park everything else** | BugBot, eval harness, Stage 4 residual, MCP Roots product — stop unless you open an explicit residual (bridge debug / H-H / tool-output HITL) |

---

## 7. Coverage caveat

Only **Cursor** filed stances this wave (~8 agents claimed in Ryan prompt; Crush/Kiro/Codex silent on disk). Consolidation is complete for **filed** residue; silent lanes should not invent work from chat memory — file a stance or stand down.
