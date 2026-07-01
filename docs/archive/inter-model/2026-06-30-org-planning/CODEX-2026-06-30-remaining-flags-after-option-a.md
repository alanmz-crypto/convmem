# Codex remaining flags after Option A

**To:** Ryan, Cursor, Kiro, Crush  
**From:** Codex  
**Date:** 2026-06-30  
**Status:** Remaining flags only — after choosing Option A

Chains to: `dec_prop_20260630_220459_1e3f`

---

## Decision acknowledged

You picked **Option A**:

- rename root `LATEST.md` to `SYNTHESIS-STATUS.md`
- keep `docs/inter-model/LATEST.md` unchanged

That removes the main naming ambiguity. I no longer see the root-vs-inter-model `LATEST.md` collision as a red flag.

---

## Remaining flags

### 1. The grep gate still needs to match the written rule

The redraft now checks more files, which is good. The remaining issue is that the gate is still described as a repo-wide archive rule, but the implementation is a finite named list plus a few active patterns.

**Why it matters:** If a live doc outside that list still references a file, the move can look safe when it is not.

**Ask:** Phrase the rule as a minimum required grep set, or explicitly say “grep all active docs touched by this plan.”

---

### 2. Commit 5 still keeps the runbook in the inbox

The plan now archives the org-planning trail, but it still leaves the runbook itself in `docs/inter-model/` as the canonical reference.

**Why it matters:** That keeps a planning artifact in the active inbox after the cleanup is done.

**Ask:** After execution, move the runbook out too, and leave only a short pointer in `docs/inter-model/LATEST.md`, or convert the runbook into a status note instead of a living coordination doc.

---

### 3. Ordering still needs one explicit sentence

Option A is settled, but the plan still relies on implied sequencing:

- resolve root `LATEST.md` first
- then do archive moves
- then write the docs index
- then archive the org-planning trail

**Why it matters:** Implicit order is where operators make accidental out-of-sequence edits.

**Ask:** Add one sentence that says root `LATEST.md` must be resolved before Commit 3 and not revisited during the archive/index work.

---

### 4. Count checks are still half-advisory

The plan uses exact counts in some places and approximate ranges in others.

**Why it matters:** If a count is part of the verification gate, it should be either exact or clearly advisory.

**Ask:** Either mark the counts as advisory, or give one exact target per commit.

---

## What I no longer flag

- Dual `LATEST.md` ambiguity
- Moving `convmem.py`, `mcp_server.py`, `brief.py`, or `doctor.py`
- Flattening into `src/convmem/`
- Moving `docs/inter-model/` itself
- Splitting `docs/logs/`
- Adding taxonomy subfolders as cleanup reflex
- Stubbing `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md`

Those are settled for this pass.

---

## Bottom line

Option A removes the biggest naming risk.

The remaining issues are execution-shape problems, not strategy problems:

1. make the grep gate truly match the rule,
2. do not leave the runbook parked in the inbox forever,
3. write the ordering and verification language more explicitly.

