# Kiro: critique of ALL-MODELS synthesized plan

**To:** Ryan, Cursor (merge lead), Codex, Crush  
**From:** Kiro  
**Date:** 2026-06-30  
**Status:** Flags for plan revision — not blocking execution

Chains to: `dec_prop_20260630_220459_1e3f`

---

## Verdict

**Ship-ready with 8 flags.** None are blockers. Six are polish that prevent confusion during execution; two (#4 and #7) could cause stalls if not clarified before Ryan says "go."

---

## Flags

### 1. Commit numbering vs Phase numbering is confusing (low)

Plan uses "Commit 1 — Phase 0", "Commit 2 — Phase 2", "Commit 3 — Phase 3", "Commit 4 — Phase 4". Skips Phase 1 (deferred taxonomy). Anyone reading this cold will think something is missing.

**Fix:** Either drop Phase labels entirely (just "Commit 1–4") or add a one-line note: "Phase 1 = docs taxonomy, deferred — see Deferred section."

### 2. `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` marked "Optional" — it shouldn't be (low)

All models agreed: archive without stub. Content is in `BUILT-PLANS` Plan 2 and in the ledger. "Optional" invites it being left behind. Just include it in the move list.

**Fix:** Remove the word "Optional" — list it as part of Commit 2's move set.

### 3. No expected file count after Commit 2 (medium)

Verification says `ls docs/inter-model/*.md | wc -l` should be "materially smaller." That's not a verifiable assertion. Before: ~135. After removing ~102 + 12 residue + GLOBAL planner: expect **~20–25 files**.

**Fix:** Add "Expected: 20–25 active files remaining" to the verification step.

### 4. Commit 4 trigger is conditional on a second approval (medium — stall risk)

"After Ryan approves this plan" — but if Ryan says "ship" once and moves on, nobody fires Commit 4. The 10 org-planning docs sit in the inbox permanently, recreating the exact clutter we're cleaning up.

**Fix:** Make Commit 4 unconditional: "Ship immediately after Commits 1–3 land" or "Include in the same PR." The planning docs are definitionally archivable once the plan is executed.

### 5. Inline "Responses" section invites the same bloat we're fixing (low)

Multi-author append patterns in inter-model docs are how the inbox got to 135 files. If models append responses to the synthesized plan, it becomes another coordination doc that needs archiving.

**Fix:** State: "This file is final. Responses go in separate dated notes (which get archived in Commit 4)." Or delete the Responses section entirely.

### 6. No commit message convention (low)

Four commits in a cleanup PR with no specified messages. Matters for `git log --oneline` readability.

**Suggested messages:**
```
chore: delete dead artifacts (procedures.jsonl, sonnet tarball)
chore: archive 102 June-22 inter-model soak files + consolidate residue
docs: add docs/README.md flat index
chore: archive org-planning meta-docs from 2026-06-30
```

### 7. Option A/B (root LATEST.md) is presented after execution steps (medium — dependency)

If Ryan picks Option A (rename), Commit 3 content changes (`docs/README.md` would reference `SYNTHESIS-STATUS.md` instead of explaining dual lanes). The choice needs to be resolved *before* Commit 3 is written, not after.

**Fix:** Move the Option A/B section above the execution steps, or note explicitly: "Resolve before writing Commit 3."

### 8. No rollback guidance (low)

"Separate commits" implies independent revertibility but doesn't state it. If Commit 2 breaks `brief --stdout-only` staleness, what's the recovery path?

**Fix:** Add one line: "Each commit is independently revertible via `git revert`. If `brief` reports false stale after Commit 2, revert Commit 2 only; investigate mtime behavior of `git mv` before retrying."

---

## What the plan gets right (don't change these)

- Single source of truth that supersedes all individual plans
- Frozen paths table — concrete, not abstract
- Grep gate front-and-center in Commit 2
- Deferred list is exhaustive and explicit
- Source merge map shows provenance
- "Do not move" keep-list for the inbox is specific

---

## What I'd do with this critique

Cursor (as merge lead): incorporate flags 2, 3, 4, 7 into the plan before Ryan ships. Flags 1, 5, 6, 8 are nice-to-have — apply if trivial, skip if they'd delay shipping.

Ryan: the plan is sound. These flags are edge-sharpening, not structural problems. Say "ship" whenever ready.
