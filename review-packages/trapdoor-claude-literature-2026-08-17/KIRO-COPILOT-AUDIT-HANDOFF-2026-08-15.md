# Copilot Audit Handoff — Dependability and Provenance Integrity

**Date:** 2026-08-15
**From:** Kiro (design review lane)
**To:** Cursor Composer 2.5 → spawn Copilot audit lane
**Branch:** `plan/2026-08-15-dependability-provenance`
**Review SHA:** `8f037a50c4cdce170320bbfd6160c932f7661798` (tip of `origin/plan/2026-08-15-dependability-provenance`)
**Repo:** `/home/lauer/Projects/convmem`

## What to build

Nothing. This is a **read-only audit request** — no code, no file changes, no runtime modifications.

## Task for Copilot audit lane

Perform a **targeted safety/isolation and continuity audit** of the dependability-provenance planning package at the exact SHA above. This is the second required review gate before Ryan's architecture lock (Section 14 of the architecture).

### Audit scope (do / do not)

| Do | Do not |
|----|--------|
| Verify no safety regression introduced by the planning package | Implement any code |
| Verify isolation: no live corpus/Chroma/Shadow/R2b/CG-2 mutation authorized | Re-audit the full codebase |
| Verify continuity: existing standing checks, backup, restore surfaces are not regressed | Modify any file on the branch |
| Check that no silent implementation authorization exists in the docs | Expand scope beyond this SHA |
| Record exact SHA and PASS/FAIL with findings | Run tests or change runtime config |

### Required output

1. `git rev-parse HEAD` — must match `8f037a50c4cdce170320bbfd6160c932f7661798`
2. Verdict: **PASS**, **CONDITIONAL PASS**, or **FAIL**
3. Blocking findings (if any) — each with file/section reference
4. Nonblocking findings (if any)
5. Safety confirmation: "No runtime, live-data, or operational authorization found in this planning package" (or identify what was found)

## Prior review dispositions (same SHA)

| Lane | Verdict | Summary |
|------|---------|---------|
| **Kiro design review** | PASS at parent `36c4df2` | Prior architecture PASS; exact-revision recheck is required after the V4m correction. |
| **Claude independent literature review** | Conditional Pass at parent `36c4df2` | Identified the capture/sealing gap; V4m is included in the current target. |
| **Codex Sol-High** | Planning correction pushed | Four authorized corrections plus V4m are present at the current target; implementation remains unauthorized. |

## Files to read (in order)

All paths are relative to repo root. Checkout `origin/plan/2026-08-15-dependability-provenance` or use `git show 8f037a5:<path>`.

1. `docs/inter-model/CLAUDE-2026-08-15-ARC-TRAPDOOR-HUNT-HANDOFF.md` — context for why this review exists and what Claude found
2. `docs/plans/ARCHITECTURE-dependability-provenance.md` — the normative architecture (802 lines); focus on:
   - Section 2 "Scope and assurance boundary" (what is and isn't owned)
   - Section 5 "Normative integrity rules" R1–R10
   - Section 11 "Implementation stages" (confirm: planning only, no runtime)
   - Section 12 "Explicit non-goals" (confirm: no live migration/activation/enforcement)
   - Section 13 "Required assurance wording" (confirm: no overclaim)
   - Section 14 "Review gates" (your role definition)
3. `docs/plans/EXECUTION-dependability-provenance.md` — Stage 1 decomposition; confirm header says "NOT AUTHORIZED FOR IMPLEMENTATION"
4. `docs/plans/VERIFY-dependability-provenance.md` — predeclared evidence rows; confirm all are PENDING
5. `docs/plans/STATUS-dependability-provenance.md` — arc brief; confirm Section 4 shows "Not authorized" for all P1/P2/P3
6. `docs/plans/CONVMEM-FIVE-PRIORITY-ARCS.md` — frozen parent roadmap; confirm no silent scope addition

## Safety/isolation checklist (minimum coverage)

- [ ] No `convmem record`, `convmem add`, `convmem index`, or any write command authorized
- [ ] No Chroma mutation, Shadow activation, R2b capture, or CG-2 operational action authorized
- [ ] No external configuration (GitHub rulesets, systemd timers, Restic profiles) changed
- [ ] No live migration or backfill authorized
- [ ] `EXECUTION` header explicitly says NOT AUTHORIZED
- [ ] `STATUS` Section 4 shows all implementation slices as "Not authorized"
- [ ] `VERIFY` rows are all PENDING — no evidence claimed
- [ ] No new or unauthorized non-document change is introduced by this planning package. The
      stale baseline makes the diff include CI-merge-gate file deletions outside `docs/`;
      those deletions are the explicit exception below, not evidence that this package
      modified runtime code.
- [ ] The CI-merge-gate deletions are already closed on current `main` by `#189`; confirm
      they are a stale-baseline artifact rather than a regression. Do not treat the raw
      `git diff --stat origin/main..8f037a5` path list as proof that every changed path
      belongs to this arc.

## Continuity checklist (minimum coverage)

- [ ] Existing `complete_data_restore.py` is not modified (future integration is planned, not enacted)
- [ ] Existing `backup_workflows.py` is not modified
- [ ] Existing CG-1 (`file_generation_*.py`) and CG-2 (`serving_*.py`) are not modified
- [ ] Existing `ingest.py`, `distill.py`, `refine.py`, `ingest_dedupe.py` are not modified
- [ ] No standing check in `docs/standing-checks-register.json` is removed or weakened
- [ ] `convmem doctor` checks are not altered

## Branch state

```
Remote:   origin/plan/2026-08-15-dependability-provenance
Tip SHA:  8f037a50c4cdce170320bbfd6160c932f7661798
Baseline: origin/main @ 2f427fcfb8818dd665310bae7e8cd5ffa066bdcc
Current main: bc83c85 (ahead of baseline — branch needs rebase before merge, nonblocking for this exact-SHA review)
```

## Review and rebase sequencing

The Copilot verdict requested here is bound only to
`8f037a50c4cdce170320bbfd6160c932f7661798`. After this audit, Ryan or the
authorized branch steward must rebase the planning branch onto the then-current
`main`. The rebase produces a new review SHA. Before architecture lock or merge,
run a targeted recheck at that new SHA covering at least: planning-only status,
absence of live/runtime authorization, `LATEST.md` additive reconciliation, and
preservation of the V4k/V4l/V4m, V4a, V5g, and normalized VERIFY table corrections. The PASS at the old SHA
must not be treated as a verdict on the rebased commit.

After rebase, `LATEST.md` changes must be additive relative to current `main`:
retain existing CG-2 soak and CI-merge-gate entries and add only the
dependability-provenance update required by the merge.

## After the audit

Return the verdict to Ryan. With Kiro PASS + Copilot PASS (or CONDITIONAL PASS with nonblocking findings), Ryan can proceed to architecture lock. If Copilot issues FAIL on material grounds that conflict with Kiro's PASS, the Sol-High gate applies per team charter.

## Spawn instructions for Cursor

Cursor Composer 2.5 should:
1. Switch to (or read from) `origin/plan/2026-08-15-dependability-provenance`
2. Spawn a Copilot audit session with this handoff as context
3. Copilot performs the read-only audit at the exact SHA
4. Copilot returns its verdict
5. Cursor relays the verdict back (or Copilot writes it directly)

No implementation. No file modification. Read-only audit only.

---

I finished: Copilot audit handoff preparation
Next step: Cursor spawns Copilot audit session with this handoff
Next lane: Cursor Composer 2.5 → Copilot audit lane
See my work: `/home/lauer/Projects/convmem/docs/inter-model/KIRO-2026-08-15-copilot-audit-handoff.md`

**TL;DR:** Read-only safety/isolation/continuity audit at `8f037a50`. Prior Kiro/Claude reviews were at earlier revisions; Copilot must review this exact target before Ryan locks.
