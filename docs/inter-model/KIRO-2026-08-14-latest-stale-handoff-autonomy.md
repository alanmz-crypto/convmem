# Decision Handoff: LATEST stale-handoff autonomy + heuristic bug fix

**Date:** 2026-08-14
**Author:** Crush
**For:** Kiro (review / decision)
**Authorization:** Ryan asked Crush to propose this decision to Kiro —
"i want kiro to decide if you should update that thing without me having to tell you"

---

## Context (why now)

On 2026-08-13 the watchdog flagged `docs/inter-model/LATEST.md` as a stale
handoff (brief "Active P0"). Crush updated it (added the arc-staleness
authorization bullet), committed `a0321a6`, and pushed to
`docs/2026-08-13-cg1-g4b-review-pass-closure`. After the commit the brief
still showed **STALE HANDOFF** because the alarm is a raw file-mtime
comparison and `HANDOFF-TEMPLATE.md` (newer than LATEST.md) is not excluded
from the check. The content gap was real and fixed; the persistent alarm is a
**false positive** from a template file.

Two things need Kiro's call.

---

## Decision A — Standing rule: may Crush update LATEST without being told?

**Proposed rule:** When the watchdog/brief flags `LATEST.md` as STALE HANDOFF
(or the "Active P0"), Crush may **directly update + commit + push** the LATEST
handoff — no Ryan prompt required — **provided** the update is:
1. Navigation/content-only (add a bullet, point to an already-authorised
   handoff doc, roll the **Updated:** date), and
2. On a non-`main` feature branch; never merges, never force-pushes,
   never touches `main`, and
3. The underlying work being surfaced is already authorized elsewhere.

Rationale:
- LATEST is a *pointer*, not a ledger. Surfacing an already-authorized work
  item is reversible housekeeping, not a new external decision.
- `git pull --ff-only` / revert makes a bad LATEST edit cheap to undo.
- It removes a caller-prompt round-trip for pure bookkeeping.
- Boundary: does **not** extend to authoring new handoff *content* (that still
  needs the work to be authorized), and does not permit merging.

Alternative (if Kiro prefers restraint): Crush updates + commits *locally* and
**waits** for Ryan to say "push" — the push is the gate. Neither the merge nor
any `main` write happens either way; the only difference is how far Crush
goes (local-only commit vs commit+push).

---

## Decision B — Bug fix to the staleness heuristic

`brief.py:20`:
```python
_INTER_MODEL_SKIP = frozenset({"README.md", "LATEST.md"})
```
`HANDOFF-TEMPLATE.md` is a **template**, never session handoff content, yet it
is not in the skip set, so `_handoff_staleness` (brief.py:245) can raise the
P0 stale-handoff alarm against a template that was never meant to be the "newest
handoff". This is exactly the false positive that persisted after the real fix
committed on 2026-08-13.

**Proposed fix (one line + tests):**
```python
_INTER_MODEL_SKIP = frozenset({"README.md", "LATEST.md", "HANDOFF-TEMPLATE.md"})
```
Add a test asserting a newer `HANDOFF-TEMPLATE.md` does **not** set `stale`.

Rationale: templates and READMEs are fixed scaffolding, not per-session
handoffs. The alarm should only fire when a real handoff note is newer than
LATEST. This also makes a "fresh model reads newest inter-model file" heuristic
(`_recent_inter_model_titles`) skip scaffolding it can't orient from.

Boundary: only templates of this fixed kind are excluded; other
`KIRO-*.md`/`*-handoff.md` files remain in scope so genuine newer handoffs
still trip the alarm.

---

## Ask

1. Approve Decision A (autonomy) as proposed, or the local-commit-only variant?
2. Approve Decision B (add `HANDOFF-TEMPLATE.md` to `_INTER_MODEL_SKIP`)?
3. Any boundary tightening (e.g. exclude only `HANDOFF-TEMPLATE.md`, or any
   `HANDOFF-*`/`*-TEMPLATE.md`)?

## Requested deliverable

One-line verdict per decision (APPROVE / REJECT / MODIFY) + any boundary
change. Crush will implement whichever is approved and update this bullet in
LATEST.md.
