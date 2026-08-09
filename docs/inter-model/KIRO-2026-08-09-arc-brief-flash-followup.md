# Flash Follow-Up — Write Arc Briefs for Stalled Arcs

> **Status: COMPLETE (2026-08-09)** — Slices 1–2 landed #157; Active STATUS list updated #159/#161. Do not re-run unless Ryan opens a new stalled arc.

**Who/What:** Kiro handing off mechanical arc-brief authoring to Crush/DeepSeek V4 Flash.
**When:** After PR #156 merges (adds the arc brief pattern + `STATUS-judgebench.md` as template).
**Why:** Two other arcs are stalled at ~90% — code on `main` but not live. Arc briefs will make the gap visible to any model that touches them next.
**How:** Read each arc's ARCHITECTURE/EXECUTION/VERIFY triad + LATEST.md entry, then write a `docs/plans/STATUS-<slug>.md` following the JudgeBench template exactly.

---

## Prereqs

- PR #156 is merged (so `docs/plans/STATUS-judgebench.md` is the canonical template on `main`)
- `convmem work start docs <slug>` before editing

---

## Slice 1: `STATUS-r2b-capture-auth.md`

**Arc:** R2b capture authorization — the system that lets convmem capture and index authorization evidence from external sources.

**Read these first:**
- `docs/plans/ARCHITECTURE-r2b-capture-auth.md`
- `docs/plans/EXECUTION-2026-07-20-r2b-capture.md`
- `docs/plans/VERIFY-r2b-capture.md`
- LATEST.md entry: "R2b capture: code on main; draft packet QUARANTINED"

**Key facts for the brief:**
- Code is on `main` via #67 (`c0f06f5`)
- Live capture is **unauthorized**
- Draft disk packet `~/.local/share/convmem/authorizations/r2b/2026-07-21-r2b-capture-01/` is QUARANTINED/abandoned
- Next step: new T4 packet + Ryan ACCEPT AND GRANT
- No model can advance this without Ryan's explicit grant
- The gap is not code — it's authorization

**Done-when for this slice:** `docs/plans/STATUS-r2b-capture-auth.md` exists, follows the 10-section template from `STATUS-judgebench.md`, file map shows what's on `main` and what's missing (authorization packet), "Your Role" section is forward-looking, "What Remains" is a short checklist ending at "live capture enabled."

---

## Slice 2: `STATUS-shadow-ledger-phase0.md`

**Arc:** Shadow Ledger Phase 0 — a disabled-by-default delta capture system that shadows Chroma writes for future ledger integration.

**Read these first:**
- `docs/plans/ARCHITECTURE-shadow-ledger-phase0.md`
- `docs/plans/EXECUTION-shadow-ledger-phase0.md`
- `docs/plans/VERIFY-shadow-ledger-phase0.md`
- `docs/plans/PHASE0-SHADOW-CONTRACT.md`
- `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.md`
- LATEST.md entry: "Shadow Ledger Phase 0 Execute MERGED — soft close"

**Key facts for the brief:**
- Code is on `main` via #122 (`4535107`)
- Phase 0 is **disabled by default** — `shadow_ledger: disabled` in doctor
- Activation requires: separate Ryan grant + activation runbook (neither exists)
- V0–V7 mechanical PASS; V8 PASS (DeepSeek + Kiro)
- The gap is not code or verification — it's an activation decision + ops runbook
- `embed_collection_identity` WARN is related but non-blocking

**Done-when for this slice:** `docs/plans/STATUS-shadow-ledger-phase0.md` exists, follows the 10-section template, diagram shows write-store factory → sink injection → temp-Chroma replay flow, file map shows what's on `main` (all implementation) vs. what doesn't exist (activation manifest, runbook), "Your Role" section says "this arc is waiting for Ryan's activation grant — you're probably here to write the runbook or answer Ryan's questions about readiness."

---

## Execution rules

- One branch: `convmem work start docs 2026-08-09-stalled-arc-briefs`
- One commit per slice (two commits total)
- Push after each commit
- Do NOT read `ask.py`, do NOT modify any Python, do NOT touch the JudgeBench brief
- Follow the 10-section structure exactly — do not invent new sections
- The departure protocol (section 10) can be identical across all briefs (copy from template)
- Update AGENTS.md "Active STATUS files" list to include the two new briefs
- After both are done, offer a PR title/body but do not create the PR

---

## Tier / complexity

**Tier 1 (Flash).** This is purely reading existing docs and writing markdown in a known template. No code, no tests, no ambiguity. If any section requires understanding that isn't in the linked docs, write "Unknown — needs investigation" rather than guessing.

---

## Acceptance

- Both files parse as valid markdown
- Both follow all 10 sections from the JudgeBench template
- File maps are accurate (cross-check with `git ls-tree -r HEAD --name-only | grep <pattern>`)
- "What Remains" lists are sequential and end at "live/enabled"
- No session narrative, no implementation details beyond what's in the linked docs
- AGENTS.md updated with the new entries
