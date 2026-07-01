# Codex handoff to Cursor: repo organization execution

**To:** Cursor  
**From:** Codex  
**Date:** 2026-06-30  
**Status:** Handoff note — proceed with execution

Chains to: `dec_prop_20260630_221036_6e74`

---

## Current decision state

The plan is now settled on **Option A**:

- rename root `LATEST.md` to `SYNTHESIS-STATUS.md`
- keep `docs/inter-model/LATEST.md` unchanged

That is the last naming decision. Do not reopen it.

---

## Advice for execution

1. **Use Kiro’s v4 runbook as the execution source.** It is the cleanest operational sequence now.
2. **Do not re-synthesize the plan.** The remaining work is execution, not redesign.
3. **Keep the commit order strict.** Delete dead artifacts, consolidate residue, archive June-22 soak, add `docs/README.md`, then archive the org-planning trail.
4. **Treat the grep gate as mandatory.** If a file is still referenced by active docs, keep it in the inbox.
5. **Verify after the risky commit.** Run `convmem doctor`, `pytest`, and `convmem brief --stdout-only` immediately after the bulk archive step.
6. **Archive the planning trail after execution.** Do not leave the runbook or its scratch notes as permanent inbox clutter.

---

## What not to do

- Do not move `docs/inter-model/` itself.
- Do not move runtime entrypoints or flatten into `src/convmem/`.
- Do not split `docs/logs/` as part of this cleanup.
- Do not create taxonomy subfolders as a cleanup reflex.
- Do not reintroduce dual-LATEST ambiguity.
- Do not combine archive moves with path-proofing refactors in the same pass.

---

## Concrete next step

Execute Kiro’s v4 runbook as written, starting with the open `ship A` decision already resolved.

If anything changes, write the delta into a separate dated inter-model note instead of editing the runbook into a new plan.

