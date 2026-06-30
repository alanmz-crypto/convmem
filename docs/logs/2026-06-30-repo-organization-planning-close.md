# Repo organization planning close (2026-06-30)

**Author:** composer-2.5-fast (Cursor)  
**Chains to:** `dec_prop_20260630_220459_1e3f`  
**Trigger:** Ryan — multi-model audit of `~/Projects/convmem` layout; agree on a single runbook before execution (after backup).

---

## Summary

Planning-only session: Cursor, Codex, Kiro, and Crush reviewed repo organization without moving production paths or running the five cleanup commits. Consensus runbook is **Kiro v4** with Cursor and Codex patch notes merged. **Option A** (root `LATEST.md` → `SYNTHESIS-STATUS.md`) is decided and written in. **Execution deferred** until Ryan completes a backup, then **`execute v4`**.

---

## Done — planning and agreement

| Item | Outcome |
|------|---------|
| Path audit | Mapped ~35 root `.py` files, ~160 inter-model `.md` files; identified frozen paths (`brief.py` → `docs/inter-model/LATEST.md`, flat library imports, MCP entrypoints) |
| Stop list | Do not move `convmem.py`, `mcp_server.py`, flat `*.py`, `docs/inter-model/` path, `docs/inter-model/LATEST.md`, `docs/ROADMAP-DRAFT.md` |
| Deferred | `src/convmem/`, taxonomy subfolders, log splits, path configurability, watch-indexing archived prose |
| Canonical runbook | [`docs/inter-model/KIRO-2026-06-30-redrafted-plan-v4.md`](../inter-model/KIRO-2026-06-30-redrafted-plan-v4.md) — five commits, strict order, grep-gated archive |
| Option A | Root synthesis lane renamed to `SYNTHESIS-STATUS.md`; protocol SPOF stays `docs/inter-model/LATEST.md` |
| Serious flags closed | `ROADMAP-DRAFT` removed from move list; residue manual move (not blind glob); expanded grep gate; Commit 5 explicit file list (25 org docs) |
| Cursor additions | [`CURSOR-2026-06-30-v4-final-additions.md`](../inter-model/CURSOR-2026-06-30-v4-final-additions.md) — residue do-not-move list, BUILT-PLANS line ~1311 link patch, verify greps — merged into v4 |
| Codex additions | [`CODEX-2026-06-30-final-additions-for-kiro.md`](../inter-model/CODEX-2026-06-30-final-additions.md) — minimum grep set, ordering, runbook self-archive — merged into v4 |
| Final review | All models sign-off; grep simulation: 0 June-22 keeps among 102 candidates; Commit 5 list matches disk 25/25 |
| Advisory nit | Post-ship inbox ~33 operational files (not 20–25); counts are advisory only |

---

## Runbook outline (not executed)

1. **Commit 1** — delete `procedures.jsonl`, `sonnet-mcp-verify-full.tar.gz`, empty `review-bundles/`
2. **Commit 2** — consolidate residue (~12 files; exclude HANDOFF-2026-06-25 + residue `README.md`); rename root LATEST; patch BUILT-PLANS `../../SYNTHESIS-STATUS.md`
3. **Commit 3** — grep-gated bulk archive of 102 `*2026-06-22*` files; move `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md`; **hard stop** if `doctor` / `pytest` / `brief` fail
4. **Commit 4** — add flat `docs/README.md` with synthesis lane link
5. **Commit 5** — archive all 2026-06-30 org-planning meta-docs (including v4 runbook); update `docs/inter-model/LATEST.md` pointer

---

## Not done (explicit)

- No git commits from v4 runbook (dead artifacts still on disk)
- Ryan backup before execution
- Post-ship optional: run record block below after Ryan approves

---

## Record block

Ryan runs:

```bash
convmem record \
  --relates-to dec_prop_20260630_220459_1e3f \
  --summary "convmem repo: closed multi-model repo organization planning — Kiro v4 runbook approved, Option A, execution after backup" \
  --rationale "Planning-only session (no v4 commits): Cursor/Codex/Kiro/Crush aligned on frozen paths, grep-gated June-22 archive (~102 files), residue manual move, ROADMAP-DRAFT kept, GLOBAL-CONVMEM archive without stub. Canonical runbook: docs/inter-model/KIRO-2026-06-30-redrafted-plan-v4.md with Cursor and Codex final additions merged. Option A decided — root LATEST.md becomes SYNTHESIS-STATUS.md; docs/inter-model/LATEST.md unchanged. All models signed off; Commit 5 explicit list covers 25 org docs. Execution deferred until Ryan backup then execute v4. Log: docs/logs/2026-06-30-repo-organization-planning-close.md." \
  --author composer-2.5-fast

convmem record --approve-last
```
