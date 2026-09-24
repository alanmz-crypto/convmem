# Review Request: Decision and Review Guardrails (opt-in doc)

**Date:** 2026-09-24
**Author:** Claude (Sonnet 5)
**For:** Kiro (design / sign-off review)
**Authorization:** Ryan, 2026-09-24 (verbal — "route it to kiro")

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` — pending Kiro review only; no implementation blocked |
| **Branch** | `docs/2026-09-24-decision-review-guardrails-opt-in` |
| **Tip SHA** | `15cc101` |
| **Push status** | pushed to origin |
| **PR** | not opened — do not open until Ryan asks |
| **Ryan GATE** | none to start review; Ryan decides after Kiro's verdict whether to merge as-is, amend, or drop |
| **Track A ingest** | pending at session close |

---

## What this is (not an implementation task)

This is a **review request**, not a build handoff — there is nothing to implement. Ryan asked to add a decision/review-discipline framework (originating from a pasted design-philosophy doc, previously reviewed favorably by Kiro in this same conversation thread) as an **opt-in, request-only** reference, explicitly *not* wired into any always-loaded surface. Claude drafted it, self-identified that shipping a charter-adjacent doc without independent review was itself a gap, and Ryan then said to route it to Kiro.

**File under review:** [`DECISION-REVIEW-GUARDRAILS.md`](DECISION-REVIEW-GUARDRAILS.md)
**Charter touch-point (one line added):** [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md) — Related section only, no other charter content changed.

---

## Why Kiro specifically

Per the HITL charter's role table, "Design / sign-off" is Kiro's phase. This doc is charter-adjacent (linked from `TEAM-CHARTER-2026-07-06.md`'s Related section) and could shape how other lanes reason about escalation and review depth if treated as settled. Applying the new doc's own escalation ladder to itself: this is at least interface-level (other lanes' behavior may depend on it), not purely local drafting — so it shouldn't be treated as adopted team practice on Claude's self-assessment alone.

---

## What to check

1. **Scope creep vs. the earlier Kiro review.** Kiro's prior review (this conversation) recommended one precedence line — "safety invariants are never over-investigation." This doc adds a second control beyond that: a **tiebreaker** routing disputed local/interface/architectural classifications between a reviewer and the coordinating model to Ryan, rather than letting either side resolve it. Confirm whether that addition is warranted or is itself scope expansion beyond what was asked.
2. **Placement.** Is a standalone `docs/inter-model/` file with a single Related-section pointer the right level of visibility for "opt-in, not automatic" — or should it live somewhere less charter-adjacent (e.g. under `docs/plans/` or with no charter link at all) to avoid it drifting into de facto default use?
3. **Whether the non-negotiable floor is actually load-bearing.** The doc states these guardrails rank below system/tool guards, lane must-nots, and DB/secrets/external safety, and that a reviewer's own escalation can't be waved off via "stop rule" reasoning without Ryan's arbitration. Confirm this reads as binding, not decorative.
4. **General design review** — anything else in the doc that reads as ambiguous, redundant with existing charter language, or likely to be misapplied.

---

## What NOT to do

- No implementation edits — this is docs-only.
- Do not merge or open a PR — Ryan decides after your verdict.
- Do not treat this as authorization to revise the doc yourself; per the charter, Kiro edits architecture/plan/review documents only when Ryan explicitly requests that specific documentation task. If you find issues, issue a verdict/findings list; Ryan or Claude will apply changes.

---

## Acceptance criteria

- [ ] Kiro issues a written verdict (PASS / PASS with amendments / FAIL) on the two files above at tip `15cc101`
- [ ] Verdict identifies whether any finding is a blocker vs. an improvement
- [ ] Ryan decides merge/amend/drop based on the verdict

---

## Related files

| What | Path |
|------|------|
| Doc under review | [`DECISION-REVIEW-GUARDRAILS.md`](DECISION-REVIEW-GUARDRAILS.md) |
| Charter (one-line touch) | [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md) |
| Governing charter for this routing | [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md) §4 role table (Design / sign-off → Kiro) |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on pushed branch
- [x] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-*.md` Update Log line — not applicable, no active arc tracks this doc
- [x] Branch pushed

**Kiro (picking up):**

- [ ] Read this file before reviewing
- [ ] Review `DECISION-REVIEW-GUARDRAILS.md` at tip `15cc101` on `docs/2026-09-24-decision-review-guardrails-opt-in`
- [ ] Issue written verdict; do not edit the file directly unless Ryan separately requests it
