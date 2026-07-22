# Cross-arc consolidation synthesis — 2026-07-22

**Consolidator:** Cursor (designated)  
**Generated:** 2026-07-22  
**Inputs:** eight `STANCE-2026-07-22-*.md` files collected from stance branches onto this consolidation branch (verbatim; not rewritten). Chat Class lines matched those stances. **No Crush / Kiro / Codex stance files found** on remote branches at consolidate time — treat non-Cursor lanes as **unreported** unless Ryan forwards Class lines later.  
**Baseline handoff:** `docs/inter-model/LATEST.md` (Updated: PR Steward VERIFY `2`→`3` closed). Brief flagged STALE HANDOFF vs newer inter-model files.  
**`main` tip at collect:** `7a0c344` (`#96`).

---

## Roster

| Agent/lane | Class | Arc (one line) | Stance path | Stance branch tip |
|---|---|---|---|---|
| Cursor | COMBINE | Copilot CLI session wiring still unmerged (adapter + always-on vs Kiro generate/deploy naming) | [`STANCE-2026-07-22-cursor-copilot-cli-wiring.md`](STANCE-2026-07-22-cursor-copilot-cli-wiring.md) | `4a56dfd` |
| Cursor | DONE | BugBot PR-level external review gate landed | [`STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md`](STANCE-2026-07-22-cursor-bugbot-pr-gate-done.md) | `8141316` |
| Cursor | DONE | Model-quality eval harness (detection only) | [`STANCE-2026-07-22-cursor-eval-harness-done.md`](STANCE-2026-07-22-cursor-eval-harness-done.md) | `78c52c0` |
| Cursor | DONE | Cursor MCP Roots shell brief boundary (`#87`) | [`STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md`](STANCE-2026-07-22-cursor-mcp-roots-brief-boundary.md) | `85d4213` |
| Cursor | DONE | P1.3 soak + semantic-dedupe default GATE closed | [`STANCE-2026-07-22-cursor-p13-dedupe-closed.md`](STANCE-2026-07-22-cursor-p13-dedupe-closed.md) | `fa75e86` |
| Cursor | DONE | R2b capture auth parked after T4 | [`STANCE-2026-07-22-cursor-r2b-capture-parked.md`](STANCE-2026-07-22-cursor-r2b-capture-parked.md) | `9b59f37` |
| Cursor | DONE | Session arcs closed (dedupe default band + debate `#94` + Steward `#95`/`#96`) | [`STANCE-2026-07-22-cursor-session-arcs-done.md`](STANCE-2026-07-22-cursor-session-arcs-done.md) | `b6a6b36` |
| Cursor | DONE | Stage 4 closed + residual tool-output draft (HITL not accepted) | [`STANCE-2026-07-22-cursor-stage4-residual-closed.md`](STANCE-2026-07-22-cursor-stage4-residual-closed.md) | `6f80df9` |
| Crush / Kiro / Codex / other | *(unreported)* | — | none found | — |

**Class counts (reported):** COMBINE **1** · DONE **7** · SOLO-CONTINUE **0**.

---

## COMBINE clusters

### Cluster A — Copilot CLI surface land (only open COMBINE)

**Members:** [`STANCE-2026-07-22-cursor-copilot-cli-wiring.md`](STANCE-2026-07-22-cursor-copilot-cli-wiring.md) (+ cited overlap: Kiro tip `d0dbda6` on `docs/2026-07-19-response-tldr`, no separate Kiro stance file).

**Merge thesis:** One land path for Copilot CLI as a Tier A surface — session adapter + watch/doctor + always-on instructions — after Ryan picks which example/deploy naming wins (`copilot-instructions-convmem.example.md` on feat tip `eb6f89d` vs `copilot-instructions.example.md` on Kiro `d0dbda6`), then rebase `feat/2026-07-19-copilot-cli-integration` onto current `main` and deploy once.

**Do not merge carelessly with:** BugBot gate / Copilot *audit lane* lifecycle (`#54`), R2a substitute-audit docs (`#59`/`#71`), or “someone looked” Steward comments.

---

### Cluster B — Shared-bus LATEST refresh (meta-COMBINE; no coding)

**Members (DONE stances requesting consolidator LATEST touch):** BugBot `#91`, MCP Roots `#87`, R2b `#67` wording, session-arcs (`#94`/`#96`), brief STALE HANDOFF.

**Merge thesis:** Single docs-only LATEST Active-handoff update so the bus matches `main` — not eight parallel LATEST PRs.

**Proposed content (for Ryan authorize later; not applied in this synthesis turn):**
- BugBot `#91` / `db3e5e0` landed (policy bootstrap; PR-native SHA gate).
- MCP Roots `#87` / `eb84472` closes PR `#19` Cursor `$HOME` caveat (residual = agent↔MCP bridge, not product reopen).
- Debate folder `#94` / Steward residual `#96` closed.
- R2b: implementation on `main` (`#67` / `c0f06f5`); **live capture still unauthorized**; T4 draft stale for ACCEPT.
- Prefer LATEST + `#86` over stale header on `CURSOR-2026-07-22-semantic-dedupe-hygiene.md`.

---

## DONE park list

Stop these lanes. Residual only if Ryan reopens with an explicit GATE / HITL.

| Park | Evidence | Residual only if Ryan… |
|---|---|---|
| P1.3 soak + dedupe default band | LATEST GATE ACCEPTED; `#86`/`dba9795`; exact@≥0.999 pending=0 | GATEs next band (name threshold) or Phase D |
| who-fixes debate archive | `#94`/`5a378b3`; `#34` superseded | — |
| Steward VERIFY `2`→`3` | `#95`/`#96`/`7a0c344` | — |
| BugBot PR gate policy | `#91`/`db3e5e0`; Kiro V6 carried by content identity | branch-protection / fallback reviewer / record block |
| MCP Roots brief boundary | `#87`/`eb84472` | confirms panel `stats` / authorizes bridge-debug |
| R2b Cursor code lane | `#67`/`c0f06f5`; T4 draft parked | fresh T4 → T5 ACCEPT AND GRANT (or abandon draft) |
| Eval harness (detection) | on `main`; ledger `dec_prop_20260705_011902_3adf` / `…082050_98bb` | H-H judge excerpts or remediation option |
| Stage 4 compression | `#46`/`#48` closed; residual draft unaccepted | authorizes tool-output residual HITL |

---

## SOLO-CONTINUE list

**None reported.** No stance Class=SOLO-CONTINUE. Non-Cursor agents did not file stances — do **not** invent solo work for them.

If a Crush/Kiro/Codex agent is still mid-task in chat without a stance, Ryan should demand a Class line or park that chat.

---

## Conflicts / double-work to kill

1. **Stale hygiene handoff header** — `CURSOR-2026-07-22-semantic-dedupe-hygiene.md` still reads pre-GATE; agents re-planning Phase A = thrash. **Truth:** LATEST + `#86`.
2. **Dual Copilot instruction pipelines** — feat tip vs Kiro `d0dbda6` filenames/deploy targets can double-write `~/.copilot/copilot-instructions.md`. Kill solo “just land my tip.”
3. **BugBot ≠ Copilot audit ≠ Steward** — folding “review happened” across these collapses scarce audit vs routine PR gate.
4. **R2b LATEST wording** — “no implementation authorized” is false after `#67`; “no live capture” remains true. Do not ACCEPT from stale T4 snapshot (>1h).
5. **MCP Roots vs “Roots deprecated” notes** — do not strip `#87` `list_roots` coercion from old Codex notes.
6. **Eval harness vs Gate 1 embedding eval** — keep judge-independence / VRAM separation; do not unify into one “eval” bucket.
7. **Stage 4 residual vs ranking/hygiene** — tool-dump token waste ≠ retrieval quality; do not reopen under P1.3/dedupe labels.
8. **Parallel LATEST edits** — one refresh only (Cluster B).
9. **Docs-only pylint R0401 flake** — rerun/update-branch; do not “fix” Python for markdown PRs (session-arcs Keep).
10. **Stale open PRs** `#33`/`#32`/`#31`/`#6`/`#37` — cleanup day only; not today’s arc thrash.

---

## Proposed next actions for Ryan only

Authorize / park / assign — **no merges, no record blocks, no implementation in this turn.**

1. **Authorize or park — LATEST refresh (Cluster B):** one docs PR naming `#87`/`#91`/`#94`/`#96` + R2b implementation-vs-capture wording + prefer LATEST over stale hygiene handoff header.
2. **Authorize or abandon — Copilot CLI land (Cluster A):** pick example name + whether to open PR from rebased `feat/2026-07-19-copilot-cli-integration` (or keep local-only overlays).
3. **Park or GATE — dedupe lower bands / Phase D:** ~1055 pending; default is park unless you name a band.
4. **Park or HITL — R2b T5:** fresh T4 recompute → ACCEPT AND GRANT, or quarantine draft `2026-07-21-r2b-capture-01`.
5. **Optional parks (no urgency):** eval H-H; Stage 4 tool-output residual HITL; MCP panel `stats` confirm; BugBot soft-close record only if you say closing; stale-PR cleanup day.
6. **Coverage gap:** request Crush/Kiro/Codex Class lines if those chats are still open — consolidation below is Cursor-only.

---

## Coverage note

| Expected ~10 agents | Reported durable stance |
|---|---|
| Cursor (multiple chats) | 8 stances (7 DONE, 1 COMBINE) |
| Crush / Kiro / Codex / other | 0 stance files at consolidate time |

Consolidation is **complete for reported Cursor residue**; incomplete for multi-lane bus until other lanes file or Ryan forwards Class lines.
