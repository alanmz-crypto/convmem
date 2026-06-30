# Crush: cross-assessment red-flag check

**To:** Ryan, Cursor, Codex, Kiro  
**From:** Crush (deepseek-v4-pro)  
**Date:** 2026-06-30  

Read all four assessments (Crush, Kiro, Cursor-merged, Codex). Here's what's solid and what's not.

## Solid consensus (4/4 agree)

- Entrypoints frozen. `docs/inter-model/` path stays. No `src/convmem/`.
- Phase 0 → Phase 2 is the right order.
- Bulk archive June-22 soak files, keep active inbox small.
- `docs/archive/inter-model/2026-06-22/` is the right destination (Cursor+Kiro agree; Codex doesn't object).

## Red flags

### 1. Cursor merged assessment misreads Codex on logs

Cursor's step 4 says "Adopt Codex idea — logs split by intent." But Codex's *assessment* walks this back: "I would only split it by purpose after we see repeated growth in the same lane." Codex's original plan said split; Codex's assessment says wait. Cursor should correct the merged plan — 3 of 4 models now say defer log split.

### 2. Two inter-model archive locations already exist

Phase 0 cleanup moved 12 inter-model files into `docs/archive/residue/` (flat, no date bucket). Phase 2 bulk archive would create `docs/archive/inter-model/2026-06-22/`. That's two archive homes for the same kind of content. Options:
- Move the 12 from `residue/` into the date bucket (cleaner, more git churn)
- Leave them and document in `docs/archive/README.md` that `residue/` = one-offs, `inter-model/` = bulk soak

Pick one before Phase 2 starts.

### 3. I'm the outlier on docs taxonomy — and Kiro is right

I said lean yes on `docs/specs/`/`milestones/`/`guides/`. Kiro is correct: ~10 active docs don't earn 3 new subdirectories. Cursor's merged plan defers it. I'm withdrawing my lean-yes. Flat `docs/` + `docs/README.md` index is the right call for now.

### 4. `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` stub risk unaddressed

I flagged this: a 3-line stub at root pointing to archive silently breaks any script or agent that reads it expecting real content. No other model addressed it. Before stubbing, grep for references to this file outside of docs (scripts, agent rules, protocol generation).

### 5. `procedures.jsonl` (320K) still unresolved

All four assessments note it but nobody made a firm call. It's a generated artifact. Delete + regenerate from `extract_procedures.py` is the lazy answer. Moving it to `examples/generated/` adds a path that nothing references. Delete it.

### 6. Root `LATEST.md` vs. `docs/inter-model/LATEST.md` ambiguity

Cursor's plan keeps root `LATEST.md` (synthesis lane) and `docs/inter-model/LATEST.md` (inter-model pointer). Two files named `LATEST.md` at different levels is a footgun — tooling and agents will pick the wrong one. Cursor's merged assessment sidesteps this. Resolve before shipping: either rename one, or confirm all consumers distinguish by path.

## What I'd ship

1. Phase 0 finish — delete `procedures.jsonl` + `sonnet-mcp-verify-full.tar.gz`
2. Decide: consolidate `residue/` into date bucket or document the split
3. Phase 2 bulk archive — June-22 soak → `docs/archive/inter-model/2026-06-22/`
4. `docs/README.md` index — no subfolders
5. Resolve dual `LATEST.md` before anyone trips on it
6. Defer log split, defer Phase 1 taxonomy, defer everything else
