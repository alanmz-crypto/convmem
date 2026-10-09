# PR Steward reminder: Ryan chose Option B

**Date:** 2026-09-27 (decided 2026-09-28)
**Author:** Claude (Sonnet 5)
**For:** Ryan and future PR lifecycle lanes
**Decision:** Ryan chose Option B on 2026-09-28; individual Steward assignments still require Ryan's explicit grant

---

## DECIDED — Option B (2026-09-28)

Ryan chose **Option B: start assigning PR Steward for future bounded
PR-lifecycle work.** This activates an already-built, already-reviewed role
(design doc `CODEX-2026-07-21-pr-steward-role.md`, Copilot audit + Kiro
sign-off, landed `main` 2026-07-22 as `0e2b396` via PR #92) — nothing new is
being designed or built here, just actually used going forward.

**What changes going forward:** when a task is bounded and well-defined
enough to need the full PR lifecycle (branch → commits → push → PR open →
CI monitoring → review-finding resolution), Ryan will explicitly assign PR
Steward (default: Codex) with a bounded brief, per the existing charter
activation rule — rather than leaving it to whichever lane is already
in-session doing the work directly. The bounded-brief criteria themselves
are not new: they already live in `TEAM-CHARTER-2026-07-06.md`'s PR Steward
section (brief-bound; no merge/grant/ledger authority; Ryan grant only,
never inferred or self-assigned). This doc doesn't redefine them.

`docs/standing-checks-register.json`'s `pr-steward-reminder` row has been
updated: `last_verified` bumped to 2026-09-28, and its notes field records
the decision so the next 30-day cycle starts from a real answer, not a
default.

---

## Current state

The standing-check decision is complete. The next bounded PR lifecycle task
may use PR Steward only when Ryan explicitly assigns that role and supplies
the brief required by the team charter. This decision does not grant Steward
authority over any particular PR.

---

## Decision context (historical)

`pr-steward-reminder` is a standing check (`docs/standing-checks-register.json`)
whose own definition is: *"Manual reminder: when describing a bounded,
well-defined task that needs full PR lifecycle (branch, commits, push, PR
open, CI monitoring, review-finding resolution), consider assigning PR
Steward (default: Codex). Activation: explicit Ryan assignment with bounded
brief."*

Per the team charter, PR Steward activation is **"a separate Ryan grant and
is never inferred from planning or implementation handoff."** No review
lane, subagent, or delegate could satisfy that — Ryan had to decide and state
it. Claude asked four times across a 2026-09-24 → 2026-09-27 session and
created this durable handoff when no direct answer had arrived. Ryan then
chose Option B on 2026-09-28.

---

## Options Ryan considered

At the time of the decision, `doctor` reported the reminder at **67 days
since verified (limit 30)**. The check posed this question:

**Should PR Steward (default: Codex) be assigned for bounded PR-lifecycle
tasks (branch → commits → push → PR open → CI monitoring → review-finding
resolution) going forward — or keep deferring?**

Context that makes this concrete: the 2026-09-24 → 2026-09-27 session this
handoff comes from did a fair amount of exactly that pattern directly
in-session (branches, commits, pushes, PR #334's open/CI-watch/audit/merge
cycle) without PR Steward. That's not wrong — Steward was never assigned —
but it's the kind of bounded, well-defined work the check is asking you to
consider handing to Steward instead.

**Option A — Keep deferring.** No process change. Someone (with your
confirmation) bumps `last_verified` in
`docs/standing-checks-register.json` to today's date, and the 30-day clock
restarts.

**Option B — Start assigning PR Steward** for future bounded PR-lifecycle
work. This is a real workflow change: bounded briefs would name Steward
explicitly (default Codex) per the charter's activation rule, rather than
whichever lane is already in-session doing the work directly.

---

## Authority boundary

- The 2026-09-28 `last_verified` update records Ryan's actual answer. Future
  updates must likewise reflect a real Ryan decision, not self-certification.
- No agent should infer a PR Steward assignment from this document alone.
  Each task needs Ryan's explicit grant and bounded brief, per the charter.

---

## Acceptance criteria

- [x] Ryan states Option A or Option B (or a third option not listed here) — **B, 2026-09-28**
- [x] If B: a follow-up note describes what "bounded brief" criteria trigger
      Steward assignment going forward — see "DECIDED" section above; criteria
      are the existing charter clause, not newly defined here
- [x] `docs/standing-checks-register.json`'s `pr-steward-reminder` row records
      the decision date and Option B

---

## Related files

| What | Path |
|------|------|
| Standing check definition | `docs/standing-checks-register.json` (id: `pr-steward-reminder`) |
| Governing charter | `docs/inter-model/TEAM-CHARTER-2026-07-06.md` — PR Steward role + activation rule |
| Where this originated | `docs/role-charters.md:70,74` |
