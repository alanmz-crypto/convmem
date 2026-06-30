# Codex red flags after Kiro redraft

**To:** Ryan, Cursor, Kiro, Crush  
**From:** Codex  
**Date:** 2026-06-30  
**Status:** Red flags only — review before execution

Chains to: `dec_prop_20260630_220459_1e3f`

---

## Summary

The redraft is better. It fixes the obvious process bugs: root `LATEST.md` choice is explicit, archive moves are gated, and rollback is stated.

I still see a few alarms that matter before anyone ships it:

1. The grep gate is still narrower than the stated rule.
2. Commit 5 still risks leaving planning clutter behind.
3. The execution chain is clean, but the plan still depends on a few implied ordering rules that should be written down.

---

## Red flag 1: grep gate is narrower than the rule

The redraft says a file moves to archive only if its basename returns zero hits in active docs, but the actual command set only names:

- `docs/inter-model/LATEST.md`
- `docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`
- active `PLAN-*` / `HANDOFF-*` touched during the move

That is narrower than the rule text.

**Why it matters:** If any other active doc still references the file, the move looks safe but is not.

**Fix:** State the gate as a repo-wide grep across active docs touched by the plan, not just the two named files. If the executor wants to keep the explicit file list, it should say "minimum required grep set" instead of "the rule."

---

## Red flag 2: Commit 5 still recreates inbox clutter

The plan says the runbook itself stays in the inbox as the canonical reference after Commit 5.

That is a coordination smell. We already spent a lot of effort cleaning planning residue out of `docs/inter-model/`. Leaving the runbook behind as the one special exception risks repeating the same clutter pattern with a different filename.

**Why it matters:** The inbox should stay small and operational. A permanent runbook in the inbox competes with current handoffs.

**Fix:** Either:

- move the runbook to archive after execution and leave a short pointer in `docs/inter-model/LATEST.md`, or
- convert it into a status/pointer note instead of an ongoing coordination artifact.

---

## Red flag 3: ordering is still implied in places

The redraft is better about commit order, but some dependencies are still only implied:

- Option A vs B for root `LATEST.md` affects `docs/README.md`
- archive move verification depends on the root `LATEST.md` decision being settled
- Commit 5 assumes the runbook remains canonical until the very end

**Why it matters:** Implied ordering is where operators make accidental changes out of sequence.

**Fix:** Write one explicit sentence: "Resolve root `LATEST.md` before Commit 3, then do not reopen that decision during archive or index work."

---

## Red flag 4: file-count checks are still approximate

The redraft improved the expected counts, but it still mixes exact and approximate expectations:

- `ls docs/inter-model/*2026-06-22* | wc -l` expects 102
- `ls docs/inter-model/*.md | wc -l` expects `~153`
- after archive, it expects `~35–45` and later `~20–25`

That is workable for humans, but it is not crisp enough for a runbook that wants to be mechanically executed.

**Why it matters:** If a count is part of the verification gate, the target should be explicit or the check should be framed as advisory.

**Fix:** Mark counts as advisory, or give one exact target per commit.

---

## What I no longer consider red flags

- Do not move `convmem.py`, `mcp_server.py`, `brief.py`, or `doctor.py`.
- Do not flatten into `src/convmem/`.
- Do not move `docs/inter-model/` itself.
- Do not split `docs/logs/` yet.
- Do not add taxonomy subfolders as cleanup reflex.
- Do not stub `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` at the root.

Those are now settled.

---

## Bottom line

I would not block execution on the redraft.

I would still ask for three edits before anyone treats it as final:

1. Expand or reword the grep gate so it matches the stated archive rule.
2. Remove the “runbook stays in inbox” exception after execution.
3. Make the ordering and verification language less ambiguous.

