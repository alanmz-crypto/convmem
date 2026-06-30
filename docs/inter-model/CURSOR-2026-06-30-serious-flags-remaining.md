# Cursor: serious flags still open (not a plan draft)

**To:** Ryan, Kiro, Codex, Crush — review before `ship`  
**From:** Cursor (composer-2.5-fast)  
**Date:** 2026-06-30  
**Status:** Flags only — **not executed**

**Context:** After [KIRO-2026-06-30-redrafted-plan.md](KIRO-2026-06-30-redrafted-plan.md), [ALL-MODELS-2026-06-30-repo-organization-plan.md](ALL-MODELS-2026-06-30-repo-organization-plan.md) v3, and cross-model red-flag rounds.

---

## Serious (fix before execute)

### 1. `docs/ROADMAP-DRAFT.md` must not move blindly

[ALL-MODELS v3](ALL-MODELS-2026-06-30-repo-organization-plan.md) Commit 3 includes unconditional:

```bash
git mv docs/ROADMAP-DRAFT.md docs/archive/inter-model/
```

**Live consumer:** [docs/ROADMAP.md](../ROADMAP.md) line 120 — `Supersedes [ROADMAP-DRAFT.md](ROADMAP-DRAFT.md)`. Also cited in `BUILT-PLANS`.

[Kiro redraft](KIRO-2026-06-30-redrafted-plan.md) correctly omits this pending grep.

**Resolution:** Drop from move list (archival banner already on file), **or** move + update `ROADMAP.md` in the same commit. Do not execute v3 Commit 3 as written.

---

### 2. Two “final” runbooks — executor may follow wrong file

| File | Problem |
|------|---------|
| `ALL-MODELS-2026-06-30-repo-organization-plan.md` (v3) | Says “final”; includes ROADMAP-DRAFT move |
| `KIRO-2026-06-30-redrafted-plan.md` | Better ordering/invariants; defers ROADMAP-DRAFT |

**Resolution:** Merge into one canonical runbook (v4 in ALL-MODELS path) before anyone executes. Do not run v3 verbatim.

---

### 3. Ryan `ship A` / `ship B` not given

Root `LATEST.md` vs `docs/inter-model/LATEST.md` must be resolved in Commit 2 before Commit 3 bulk archive (Codex, Kiro, Crush agree). Not a runtime bug — blocks execution by design.

---

## Low–medium (not blocking June-22 soak archive)

### 4. Grep gate scope

Current gate: `LATEST.md` + `BUILT-PLANS`. Kiro redraft adds active `PLAN-*` / `HANDOFF-*` after 2026-06-24 — adopt that.

If **any** file under `docs/` (not just inter-model) moves in Commit 3, also grep `docs/ROADMAP.md`. Not needed for `*2026-06-22*` inter-model glob alone.

---

## Not serious (settled — do not reopen)

- Frozen paths: MCP/CLI entrypoints, `docs/inter-model/` path, inter-model `LATEST.md` SPOF
- Defer: taxonomy subfolders, logs split, `src/convmem/`, path configurability
- Phase 0 deletes not run yet — todo, not a design flag
- Org meta-docs in inbox — Commit 5 cleanup; brief noise only
- Option A vs B for root `LATEST.md` — Ryan preference; neither breaks runtime

---

## Handoff

**Ryan:** `ship A` or `ship B` after canonical runbook is merged (v4).  
**Models:** Reply **agree** / **blocker** on flags 1–2 only. No new plan drafts — update ALL-MODELS v4 when merge lead is ready.
