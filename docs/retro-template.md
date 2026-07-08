# Engineering-Team Retrospective — Template

Copy this to `docs/engineering-team-retro-<YYYY-MM-DD>.md` and fill it in.

**Framing:** a retro is not a fifth, separate stage and not a lesson-learned doc
nobody rereads. It is the coverage-ledger discipline applied to the *process*
instead of the code. Every finding must land in a real bucket — a register row,
a charter rule, or code — exactly as a code gap does. Prose-only is not a valid
destination.

This template is itself enforced by two register rows:
`retro-loop-closure` (someone runs step 0 within 90 days) and
`mechanized-claims-audit` (the claims a retro verifies get re-verified as code
moves).

---

## 0. Audit the previous retro (do this FIRST)

Open the most recent `docs/engineering-team-retro-*.md`. For each countermeasure
it recorded, cite where it landed and mark it:

| Previous action item | Destination (row / charter / code) | Done? |
|---|---|---|
| ... | ... | yes / no / partial |

A "no" or "partial" is this retro's first finding — carry it into section 1.
This step is what `retro-loop-closure` nags for; bump that row's
`last_verified` only after this table is filled honestly.

## 1. Process leaks

Not "did it work" but "where did the process itself leak." For each leak, give
the root cause (missing verification step vs. conversational pace) and a
**destination** — prose alone is not allowed.

| Leak | Root cause | Countermeasure | Destination |
|---|---|---|---|
| ... | ... | ... | register row `<id>` / charter rule on Role N / code |

## 2. Ledger-vs-reality sweep

Re-verify every (a)-classified claim and each closed-row mechanization against
**current** code with file:line citations. Use the citation table in
`docs/engineering-team-retro-2026-07-07.md` section 2 as the template. Record
drift found (ideally none). This sweep legitimately seeds
`mechanized-claims-audit`'s `last_verified`.

## 3. UNVERIFIED sweep

Enumerate every item ever marked unverified; confirm each reached a terminal
bucket (a / b / c / closed). A live mark is written with the uppercase
owner-tagged marker (`UNVERIFIED(owner)`) that the `unverified-resting-state`
probe greps for in `role-mapping.md` and `role-charters.md`; historical
lowercase prose is fine. Conclusion: did all of them resolve, or did some
quietly stay unverified because nobody circled back?

## 4. Explicit non-goals re-check

For everything intentionally excluded (Role 7's judgment calls, probe
exemptions, `trigger: none` manual-by-design rows, documented manual halves):
have the conditions behind the exclusion changed since decided? Verdict:
stands / revisit, one line each.

## 5. Ledger changes made by this retro

List the register rows added/closed, charter rules added, and code shipped —
the concrete conversions from section 1. Update the count snapshot in
`standing-checks-register.md` if row totals changed.

---

## Standing agenda (every increment, not just retros)

- Run an adversarial debug / "check for bugs" pass after each increment before
  calling it done — this was the single most effective step historically
  (it caught the suffix-match bug, the probe flagging its own docs, and template
  placeholders parsed as refs).
- Don't restate derived counts/lists a source of truth already holds; point at
  the source. Where a restatement is useful, date-stamp it as a snapshot.
