# Synthesis: 2026-07-22 cross-arc consolidation

**Author:** Cursor (designated consolidator)  
**When:** 2026-07-22  
**Inputs:** eight `STANCE-2026-07-22-*.md` files on docs stance branches (cited, not rewritten); [`LATEST.md`](LATEST.md) Active handoff; `convmem doctor` / `brief` / `unresolved` this turn.  
**Not done here:** git merges, ledger `record`, LATEST edits, new implementation.

Stances are **not yet on `main`** — they live on their stance branches. Cite branch + path below.

---

## Roster

| Agent/lane | Class | Arc (short) | Stance path (branch) |
|---|---|---|---|
| Cursor | DONE | BugBot PR-level external review gate | `docs/2026-07-22-stance-bugbot-gate-done` → [`STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md`](STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md) *(on that branch)* |
| Cursor | COMBINE | Copilot CLI session wiring (adapter + always-on) | `docs/2026-07-22-stance-copilot-cli-wiring` → [`STANCE-2026-07-22-cursor-copilot-cli-wiring.md`](STANCE-2026-07-22-cursor-copilot-cli-wiring.md) |
| Cursor | DONE | Session arcs: dedupe GATE + debate folder + Steward VERIFY residual | `docs/2026-07-22-stance-cursor-session-arcs-done` → [`STANCE-2026-07-22-cursor-session-arcs-done.md`](STANCE-2026-07-22-cursor-session-arcs-done.md) |
| Cursor | DONE | Model-quality eval harness (detection only) | `docs/2026-07-22-stance-eval-harness-done` → [`STANCE-2026-07-22-cursor-eval-harness-done.md`](STANCE-2026-07-22-cursor-eval-harness-done.md) |
| Cursor | DONE | P1.3 soak + semantic-dedupe default GATE | `docs/2026-07-22-stance-p13-dedupe-closed` → [`STANCE-2026-07-22-cursor-p13-dedupe-closed.md`](STANCE-2026-07-22-cursor-p13-dedupe-closed.md) |
| Cursor | DONE | Stage 4 digest demotion closed; residual tool-output deferred | `docs/2026-07-22-stance-stage4-residual` → [`STANCE-2026-07-22-cursor-stage4-residual-closed.md`](STANCE-2026-07-22-cursor-stage4-residual-closed.md) |
| Cursor | DONE | MCP Roots shell brief boundary (#87) | `docs/2026-07-22-2026-07-22-stance-mcp-roots-boundary` → [`STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md`](STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md) |
| Cursor | DONE | R2b capture auth parked after T4 | `docs/2026-07-22-2026-07-22-stance-r2b-capture-parked` → [`STANCE-2026-07-22-cursor-r2b-capture-parked.md`](STANCE-2026-07-22-cursor-r2b-capture-parked.md) |

**Count:** 7 DONE · 1 COMBINE · 0 SOLO-CONTINUE (among filed stances).

**Note:** All filed stances this cycle are Cursor-lane. No Crush/Kiro/Codex `STANCE-2026-07-22-*` files found on `origin` heads searched.

---

## COMBINE clusters

### Cluster A — Copilot CLI product wiring (only COMBINE)

**Members:** [`STANCE-2026-07-22-cursor-copilot-cli-wiring.md`](STANCE-2026-07-22-cursor-copilot-cli-wiring.md) (+ unmerged Kiro tip `d0dbda6` on `docs/2026-07-19-response-tldr`, cited in that stance).

**Merge thesis:** One land path that ships **both** (1) session adapter / watch / doctor / open_source and (2) a **single** generate/deploy always-on Copilot instructions example name — then `deploy-agent-protocol.sh`. Do not merge generate/deploy alone (leaves ingest blind) or adapter alone without resolving dual example filenames.

**Settled elsewhere (do not re-litigate):** PR #54 Copilot lifecycle / Sol-High; DeepSeek V4-Pro *substitute* audit role (#59/#71).

**Ryan decision needed:** authorize PR from rebased `feat/2026-07-19-copilot-cli-integration` vs abandon; pick winning example filename.

---

## DONE park list

Stop these lanes. Residual only if Ryan reopens with an explicit grant.

| Arc | Evidence on `main` / park state | Residual (reopen only if…) |
|---|---|---|
| BugBot PR gate | [#91](https://github.com/alanmz-crypto/convmem/pull/91) `db3e5e0` | Org branch-protection / fail-on-unresolved settings; soft-close record if Ryan asks |
| Session arcs (dedupe + debate + Steward residual) | [#86](https://github.com/alanmz-crypto/convmem/pull/86) `dba9795`; [#94](https://github.com/alanmz-crypto/convmem/pull/94); [#95](https://github.com/alanmz-crypto/convmem/pull/95)/[#96](https://github.com/alanmz-crypto/convmem/pull/96) | Next dedupe band or Phase D GATE; LATEST refresh |
| P1.3 soak + dedupe default GATE | LATEST: soak CLOSED; GATE ACCEPTED | Same: next band / Phase D only |
| Eval harness (detection) | `004626a` + ledger `dec_prop_20260705_011902_3adf` | H-H judge excerpts; ROADMAP remediation option |
| Stage 4 context compression | [#46](https://github.com/alanmz-crypto/convmem/pull/46)/[#48](https://github.com/alanmz-crypto/convmem/pull/48); plans CLOSED | Residual tool-output HITL (new arc) |
| MCP Roots brief boundary | [#87](https://github.com/alanmz-crypto/convmem/pull/87) `eb84472` | Live panel `stats` / agent `Connection closed` bridge debug |
| R2b capture | [#67](https://github.com/alanmz-crypto/convmem/pull/67) `c0f06f5`; T4 draft parked | Fresh T4 → T5 ACCEPT AND GRANT; or abandon draft |

---

## SOLO-CONTINUE list

**None** among the eight filed stances.

Agents that classified DONE must **ignore:** lower-band dedupe drains, Phase D, R2b live capture, Stage 4 re-implementation, BugBot re-policy, eval remediation, and “helpful” LATEST thrash without Ryan ask.

---

## Conflicts / double-work to kill

1. **Dedupe “still awaiting GATE”** language in older handoff headers vs LATEST **GATE ACCEPTED** — prefer LATEST + `#86`; do not re-brief hygiene.
2. **Lower-band / Phase D** treated as implied by default GATE — **not authorized** (~1055 pending parked).
3. **LATEST R2b “no implementation authorized”** vs `#67` shipped — update wording so live capture stays unauthorized but implementation is acknowledged parked.
4. **LATEST Stage 3 / Cursor `$HOME` caveat** vs `#87` close — cite `#87`/`eb84472` or leave a stale open-gap story.
5. **BugBot vs Copilot vs Steward** — independent; do not collapse into one “someone reviewed.”
6. **Eval harness vs Gate 1 embedding** — do not merge into one “eval” bucket.
7. **Stage 4 residual vs P1.3/dedupe** — token dumps ≠ ranking/hygiene; do not fold.
8. **Copilot dual example filenames** / `DEEPSEEK_API_KEY` in mcp-config — kill before any land.
9. **MCP args → deleted worktree** after Roots cleanup — keep prod `mcp_server.py` path.
10. **Stale open PRs** `#33`/`#32`/`#31`/`#6`/`#37` — cleanup day only if Ryan asks (session-arcs stance).

---

## Proposed next actions for Ryan only

**Authorize**

1. Copilot CLI land path (COMBINE Cluster A): rebase `feat/2026-07-19-copilot-cli-integration`, fold Kiro generate/deploy naming, open/merge PR — **or** abandon adapter and keep local overlays.
2. Optional: residual tool-output arc HITL (Kiro on draft direction) — or leave deferred.
3. Optional: R2b resume (fresh T4 → ACCEPT AND GRANT) — or quarantine draft `2026-07-21-r2b-capture-01`.
4. Optional: MCP panel confirm / bridge-debug arc if `CallMcpTool` still `Connection closed`.

**Park (default)**

5. All DONE arcs above — no further solo coding.
6. Dedupe lower bands + Phase D — until new GATE.
7. Eval remediation / H-H — until explicit grant.
8. BugBot org settings / non-Cursor fallback — until asked.

**Assign**

9. LATEST Active handoff refresh (docs-only): add BugBot `#91`, MCP Roots `#87` close of Cursor `$HOME` caveat, R2b `#67` implementation-parked wording, optional Stage 4 closed one-liner — consolidator or Docs lane only if you authorize a LATEST PR.
10. Stance branches: leave unmerged until you want a single docs PR collecting `STANCE-2026-07-22-*` + this synthesis, or cherry-pick selectively.

---

## Consolidator meta

- Protocol this turn: `doctor` PASS (1 non-fatal warn); `brief` STALE HANDOFF vs BUILT-PLANS mtime (known heuristic); 11 unresolved (staging2 + retrieval obs) — **out of scope** for this consolidation unless Ryan assigns.
- This file branch: `docs/2026-07-22-cross-arc-consolidation-synthesis`.
