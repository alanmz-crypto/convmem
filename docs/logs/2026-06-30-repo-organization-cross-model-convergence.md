# Session log: repo organization cross-model convergence

**Date:** 2026-06-30  
**Duration:** ~1.5h  
**Models:** Cursor, Codex, Kiro, Crush  
**Chains to:** `dec_prop_20260630_221036_6e74`

## Flow

1. **Assessment round** — all 4 models posted individual repo org assessments, flagging agreements (freeze entrypoints, archive June-22, defer taxonomy/logs) and disagreements (docs subfolders, log split timing).

2. **Cross-assessment** — Crush found 6 red-flags across the assessments: Cursor misread Codex on logs, two archive homes, premature taxonomy, GLOBAL-CONVMEM stub risk, unresolved procedures.jsonl, dual LATEST.md.

3. **Red-flags convergence** — Cursor redrafted consolidated do-not-do list endorsed by all 4 models. Kiro's review resolved 4 open items (taxonomy defer, log defer, procedures.jsonl delete, sonnet tarball delete).

4. **Honesty sections** — Kiro and Crush independently wrote "what I missed" sections, converging on 5 shared gaps (PR discipline, meta-clutter, grep enforcement, shell-script consumers, producer-script coupling).

5. **Execution plans** — Crush, Kiro, and Codex each posted execution plans. Cursor synthesized v3 ALL-MODELS plan. Crush + Kiro critiqued it (6+8 flags). Cursor absorbed all flags into v3 final.

6. **Kiro redraft** — Kiro produced best-practices redraft with invariants, ordering rationale, anti-scope. Three rounds of feedback (Cursor v4 additions, Codex remaining flags) → v4 final runbook.

7. **Decision:** Option A (rename root `LATEST.md` → `SYNTHESIS-STATUS.md`).

## Outcome

**Kiro v4 runbook** at `docs/inter-model/KIRO-2026-06-30-redrafted-plan-v4.md` — 5 commits, frozen paths, grep-gated archive, per-commit verification, unconditional meta-close. Awaiting execution.

## Key decisions

- No docs taxonomy subfolders (4/4 defer)
- No log split (4/4 defer)
- No Python moves (4/4 freeze)
- ROADMAP-DRAFT.md frozen (confirmed live refs)
- GLOBAL-CONVMEM-PROTOCOL-PLANNER.md → archive, no stub
- ~102 June-22 files → `docs/archive/inter-model/2026-06-22/`
- 12 residue files consolidated into date bucket
- All ~25 org-planning meta-docs self-archive in Commit 5
