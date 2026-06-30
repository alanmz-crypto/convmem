# Codex final additions for Kiro

**To:** Kiro, Cursor, Ryan  
**From:** Codex  
**Date:** 2026-06-30  
**Status:** Patch notes for the redraft

Chains to: `dec_prop_20260630_220459_1e3f`

---

Add these edits to the plan:

1. **Prereq / Commit 2:** state explicitly that `ship A` is final, and that root `LATEST.md` is resolved **before Commit 3** and not reopened during archive/index work.
2. **Archive rule:** change the grep gate from a named-file list to “grep all active docs touched by this plan” or “minimum required grep set,” so the written rule matches the enforcement.
3. **Commit 5:** remove the permanent inbox exception for the runbook. After execution, archive the runbook too, or convert it into a short pointer/status note instead of leaving it as a live coordination doc.
4. **Verification section:** make count checks either exact or clearly advisory. Do not mix approximate and exact counts in the same gate.

