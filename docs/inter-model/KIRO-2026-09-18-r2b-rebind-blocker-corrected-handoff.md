# Handoff: R2b rebind is bigger than one coordinate — corrected diagnosis + next steps

**Date:** 2026-09-18
**Author:** Kiro (review lane — corrects the prior rebind handoff)
**For:** Ryan (scope decision) → then Cursor / R2b lane (implementation)
**Supersedes the premise of:** [`CURSOR-2026-09-17-r2b-inventory-rebind-handoff.md`](CURSOR-2026-09-17-r2b-inventory-rebind-handoff.md)
**Related:** [`KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md`](KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md) (the downstream work this branch blocks)

---

## What we're doing (one paragraph)

Branch `fix/2026-09-17-watch-skip-hash-parity` carries three verified,
production-confirmed correctives (watch re-spawn loop, `index --file` silent
success, provider fail-fast). It is **red on the R2b writer-coverage gate**, and
we need it green so it can go to PR — which in turn unblocks the Claude
transcript adapter (Gate 1 approved 2026-09-18). We attempted the rebind the
prior handoff described. **It does not work, because that handoff's premise is
wrong.** This document records the corrected diagnosis so the next lane scopes
the fix correctly instead of repeating a one-line change that cannot succeed.

---

## What we tried, and the result

Executed the authorized single-coordinate rebind exactly as specified, verified
in a **clean worktree** (never the polluted shared checkout):

- Applied `inventory.py:90` `("convmem.py:640",) → ("convmem.py:655",)`. Sink
  line re-derived, not trusted: confirmed at `convmem.py:655`.
- Regenerated `R2B-V2-WRITER-COVERAGE-INVENTORY.json`; digests **converged**
  (`0380b8d6…` on both sides), pylint 10/10.
- Nine-file R2b suite in clean worktree: **19 failed** — expected `0`.
- **Pristine branch tip, before any edit: 24 failed / 86 passed.** The branch
  was already red on R2b before we touched anything.

**Nothing was committed or pushed.** Branch is untouched at `3967360`.

---

## Corrected diagnosis (why the one-coordinate story is false)

1. **Sink coordinates are stale across MANY sites, not one.** Consistent
   per-file offsets between recorded and actual `production_chroma_write_session`
   sites:
   - `convmem.py` recorded `387/491/656/1718` → actual `402/506/671/1733`
   - `ingest.py` recorded `612/1092/1130` → actual `637/1138/1176`

2. **A SECOND committed artifact the prior handoff never mentions is stale:**
   `SHADOW-WRITER-COVERAGE-INVENTORY.json` (not the `R2B-V2` file). Its drift
   spans `convmem.py`, `ingest.py`, **and `incremental_jsonl.py` — Arc Codex,
   explicitly off-limits.** This is the boundary collision that makes the fix a
   scope decision rather than routine maintenance.

3. **The prior handoff's tip is stale:** it says `a544493`; live tip is
   `3967360` (three `docs(inter-model)`-only commits since — no code moved). So
   the 24-red state predates the handoff and was present when it was written.

4. **Regeneration must happen in a clean worktree too** — not just verification.
   Regenerating inside the shared checkout embedded **338 phantom
   `.claude/worktrees/…` sites** into the JSON. The prior handoff only warned
   about verification.

**The digest machinery itself works** — regeneration converges cleanly. The
problem is stale *content*, not a broken gate.

---

## The open question that must be answered first

**Was this branch ever actually green on R2b at `a544493` in a clean worktree?**
Our clean-worktree measurement says no (24-red at pristine tip). The earlier
"green" may have been measured on the polluted shared checkout — the same
pollution that produces phantom sites. If so, the "one coordinate" diagnosis was
an artifact of a bad measurement environment from the start.

---

## Next steps (in order)

1. **Ryan — scope decision.** Choose one:
   - **(a) Authorize a full inventory refresh:** rebind *all* stale governed
     coordinates and regenerate *both* inventory artifacts. This **necessarily
     touches Arc-Codex-adjacent coordinates** (`incremental_jsonl.py` in the
     shadow inventory), so it needs explicit cross-arc authorization.
   - **(b) Investigate first:** confirm the clean-worktree R2b baseline at
     `a544493`/`3967360` and decide whether the branch was mis-certified before
     committing to a fix scope.
2. **Implementation lane (Cursor or R2b lane), after (a) or (b):** perform the
   refresh in a **clean worktree** (both regeneration and verification), one
   commit, push with explicit refspec, do not weaken any test.
3. **Kiro:** review the pushed tip; certify green against the true clean-worktree
   baseline (`main`: 1 failed, 2527 passed — the single expected failure is
   `test_eval_golden.py::…::test_golden_questions`, unrelated).
4. **Then** the Claude transcript adapter (Gate 1 = Yes, Option 2) can be built
   off a green base per its handoff.

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `BLOCKED_ON_RYAN` (scope decision) |
| **Branch** | `fix/2026-09-17-watch-skip-hash-parity` |
| **Live tip** | `3967360` (handoff's `a544493` is stale) |
| **Push status** | untouched — nothing committed this session |
| **R2b state** | 24 failed / 86 passed at pristine tip (clean worktree) |
| **Ryan GATE** | Yes — scope decision (a) or (b) above |

---

## Hard boundaries (unchanged, carry forward)

- One commit, in a clean worktree; no test suppressed / skipped / xfail'd.
- No `git config`, force-push, reset --hard, or `--no-verify`.
- Any change touching Arc Codex `incremental_jsonl*.py` coordinates requires
  explicit cross-arc authorization — do not self-authorize.
- The change's author must not self-attest the regenerated digest; a different
  lane reviews.

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| R2b writer-coverage gate | A test suite that binds an authority-content digest over governed writer/proof/lease modules; goes red when recorded code coordinates drift from actual. |
| Governed sink / `production_chroma_write_session` | A code site that writes to the live Chroma store; R2b tracks their exact file:line coordinates. |
| Inventory artifact | Committed JSON recording governed coordinates — two exist: `R2B-V2-WRITER-COVERAGE-INVENTORY.json` and `SHADOW-WRITER-COVERAGE-INVENTORY.json`. |
| Rebind | Updating a recorded coordinate in the inventory to match where the code actually is now. |
| Clean worktree | A fresh `git worktree` checkout; required because the shared checkout's nested `.claude/worktrees` copy pollutes the R2b static scan with phantom sites. |
| Self-attestation | The author of a code change also regenerating the authority digest that certifies it — disallowed; a separate lane must do/review it. |
| Arc Codex | The gated arc owning `incremental_jsonl.py`; off-limits to unrelated work without explicit authorization. |
| Gate 1 (Claude adapter) | The approved decision (2026-09-18) to build a Claude transcript adapter (on-demand only); the downstream work this branch blocks. |
| Lane (Kiro / Cursor / R2b) | Role per `TEAM-CHARTER-2026-07-06.md`; Kiro reviews/plans, Cursor/R2b lane implement. |
