# Crush → Cursor: organization runbook handoff

**To:** Cursor (composer-2.5-fast) — execute `KIRO-2026-06-30-redrafted-plan-v4.md`  
**From:** Crush (deepseek-v4-pro)  
**Date:** 2026-06-30  

The runbook is ready. Option A, 5 commits, no ambiguity. Here's what to watch for.

## Execution notes

### Pre-flight
Run `convmem doctor && pytest` before Commit 1. If either fails, stop — baseline is dirty.

### Commit 1 — trivial
Delete two files. The `rmdir review-bundles` may fail if it's already gone; `|| true` handles it.

### Commit 2 — residue move list is exact
Kiro listed 12 explicit files in a comment block. The glob approach was abandoned because not all residue files match `*2026-06-22*` (e.g., `CONVERSATION_COMPACT.md`, `README-FOR-CHATGPT.md`, `KIRO-TO-ALL-MODELS.md` have no date). The manual `git mv` list is the source of truth — verify `ls docs/archive/residue/` before and after to confirm `HANDOFF-CURSOR-AUTO-COMPOSER-2026-06-25-soak.md` and `README.md` stayed.

The `BUILT-PLANS` patch (`../../LATEST.md` → `../../SYNTHESIS-STATUS.md`) is at roughly line 1311. Use `grep -n '../../LATEST.md' docs/inter-model/BUILT-PLANS*` to find the exact line.

### Commit 3 — grep gate
The loop will echo `KEEP` for any file with a live back-ref. You expect zero keeps (all June-22 files should be unreferenced). If one fires, investigate before committing — don't silence it with `2>/dev/null` on the echo.

The `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` move is outside the loop. It was confirmed unreferenced by Kiro's grep of all scripts/Python/config.

**Hard gate after Commit 3:** `convmem doctor` must exit 0, `pytest` must pass, `brief --stdout-only` must show no false stale alarm. If any fail, revert and investigate — most likely cause is `git mv` mtime interaction with `brief.py` staleness check.

### Commit 4 — docs/README.md
Keep it flat. Mention `SYNTHESIS-STATUS.md` at root explicitly (Option A record). Don't over-engineer — this is a navigation aid, not a manifesto.

### Commit 5 — archival
The file list is exhaustive. After the moves, `ls docs/inter-model/*.md | wc -l` should be ~30–35. Update `LATEST.md` with the one bullet exactly as written.

## Post-execution record block

After all 5 commits land, output a record for Ryan. Use the same anchor: `--relates-to dec_prop_20260630_221036_6e74`. Include commit SHAs, before/after counts, and any surprises.

## What not to do

- Don't skip Commit 3 verification gate even if it "looks fine"
- Don't move `docs/ROADMAP-DRAFT.md` — frozen
- Don't touch `docs/inter-model/LATEST.md` — SPOF
- Don't create docs subfolders — deferred
- Don't amend commits — each is independently revertible
