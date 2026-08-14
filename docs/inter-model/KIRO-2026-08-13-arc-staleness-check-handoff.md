# Implementation Handoff: `arc_staleness` Doctor Check

**Date:** 2026-08-13  
**Author:** Kiro (design/review lane)  
**For:** Cursor or Codex (implementation lane)  
**Authorization:** Ryan, 2026-08-13 (verbal, this session)

---

## What to build

A new `_check_arc_staleness()` function in `doctor.py` that warns when STATUS-tracked
arcs have incomplete milestones but no progress in the Update Log for >14 days.

**Product goal:** Surface "authorized but forgotten" work before it silently stalls for
weeks. Advisory only — never blocks, never fails doctor.

**Why this exists:** Ryan runs multiple arcs in parallel across different models. When a
handoff is made but the receiving model never starts (or a branch sits without a PR),
nothing in the system surfaces the gap. P1.3 source-trust went 22 days after approval
with no sign of execution; R2b's replacement T4 packet has been needed for 23 days with
no action. This check makes invisible staleness visible.

---

## Integration point

Add `_check_arc_staleness()` to the v0 check list in `run_doctor()` (around line 1318),
after `_check_standing_register(cfg)`:

```python
checks: list[DoctorCheck] = [
    ...
    _check_standing_register(cfg),
    _check_arc_staleness(),          # <-- new
    _check_planning_guide_contract(),
    ...
]
```

---

## Specification

### Inputs

- Glob: `docs/plans/STATUS-*.md` relative to repository root (`Path(__file__).resolve().parent`)
- No config dependency; no external service

### Algorithm

```
for each STATUS-*.md file:
    1. Extract the arc slug from filename (e.g. STATUS-r2b-capture-auth.md → "r2b-capture-auth")

    2. Parse Section 10 "Update Log" table:
       - Find all lines matching: ^\| (\d{4}-\d{2}-\d{2}) \|
       - Take the most recent (maximum) date as `last_updated`
       - If no date found, treat as stale from epoch (always warn)

    3. Parse Section 4 "Completion State" table:
       - Look for cells containing any of (case-insensitive):
         "NOT STARTED", "NOT DONE", "BLOCKED", "HOLD", "NOT READY"
       - If ALL milestones are "DONE" (no incomplete markers found), SKIP this arc
         (it's finished, just awaiting merge — not stale)

    4. Compare:
       - days_stale = (today - last_updated).days
       - If days_stale > STALENESS_THRESHOLD_DAYS (default 14):
           → mark this arc as stale

    5. Count incomplete milestones (for the detail message):
       - Count rows in Section 4 containing the incomplete markers
```

### Output

- **No stale arcs:** `DoctorCheck("arc_staleness", True, "{n} arcs tracked, 0 stale")`
- **Stale arcs found:** `DoctorCheck("arc_staleness", True, "{n} arc(s) stale (>14d): {slug} (last: {date}, {k} incomplete); ...", status="warn")`
- **No STATUS files found:** `DoctorCheck("arc_staleness", True, "no STATUS files in docs/plans/", status="skip")`
- **Parse error on a file:** Skip that file silently (log if needed), don't fail the check

### Constants

```python
STALENESS_THRESHOLD_DAYS = 14
_STATUS_GLOB = "docs/plans/STATUS-*.md"
_INCOMPLETE_MARKERS = {"not started", "not done", "blocked", "hold", "not ready"}
_UPDATE_LOG_DATE_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", re.MULTILINE)
```

---

## Standing register entry

Add to `docs/standing-checks-register.json` in the `checks` array:

```json
{
  "id": "arc-staleness",
  "check": "STATUS-tracked arcs with incomplete milestones progressing within 14 days",
  "role": "Platform",
  "trigger": {
    "type": "probe",
    "probe": "arc_staleness"
  },
  "status": "open",
  "last_verified": "2026-08-13",
  "notes": "Probe reads docs/plans/STATUS-*.md Update Log dates and Section 4 completion markers. Advisory warn only. Catches the 'authorized but forgotten' pattern where work is handed to a model but never picked up. Added after Kiro audit identified P1.3 source-trust (22 days stale) and R2b T4 (23 days stale) as unnoticed gaps."
}
```

---

## Section parsing guidance

STATUS files follow a consistent 10-section template. Key parsing landmarks:

### Update Log (Section 10)

Appears near end of file. Structure:
```markdown
## Update Log

| Date | Who | Change |
|------|-----|--------|
| 2026-08-09 | Crush | Initial arc brief; ... |
```

Regex target: lines starting with `| YYYY-MM-DD |` after the `## Update Log` heading.
Take the **maximum date** found (not the last physical row — entries could be out of
order, though they typically aren't).

### Completion State (Section 4)

Appears mid-file. Structure:
```markdown
## 4. Completion State

| # | Milestone | Status | Blocking on |
|---|-----------|--------|-------------|
| T1 | Architecture docs | **DONE** | — |
| T5 | Ryan ACCEPT | **NOT STARTED** | Ryan ... |
```

Look for table rows containing any of the incomplete markers (bold-wrapped or plain):
`NOT STARTED`, `NOT DONE`, `BLOCKED`, `HOLD`, `NOT READY`.

---

## Test expectations

Focused tests in `tests/test_doctor_arc_staleness.py`:

1. **Stale arc detected:** STATUS file with Update Log date >14 days ago and incomplete
   milestones → warn with arc slug in detail
2. **Completed arc skipped:** STATUS file with all DONE milestones → not reported even
   if Update Log is old
3. **Fresh arc not flagged:** STATUS file with recent date (<14 days) and incomplete
   milestones → pass
4. **No STATUS files:** → skip status
5. **Malformed Update Log:** Missing dates → treated as stale from epoch (always warn)
6. **Multiple arcs, mixed:** One stale + one fresh → only stale one reported in detail

Use `tmp_path` fixtures with synthetic STATUS markdown content; do not depend on real
STATUS files (they change).

---

## What NOT to build

- No config knob for the threshold (hardcode 14 days; reconfigurable is premature)
- No ledger decision lookup (the "arcs without STATUS files" idea is separate/future)
- No LATEST.md parsing (STATUS files are the canonical source)
- No network calls, no model invocations
- No modification of existing checks

---

## Acceptance criteria

- [ ] `convmem doctor` reports `arc_staleness` check (pass or warn)
- [ ] Advisory only: `ok=True` always; `status="warn"` when stale arcs exist
- [ ] Register entry added to `docs/standing-checks-register.json`
- [ ] Existing 4 STATUS files correctly parsed (verified by running doctor locally)
- [ ] No regression in existing doctor checks (full suite passes)
- [ ] Ruff clean
- [ ] Tests in `tests/test_doctor_arc_staleness.py` pass

---

## Branch convention

```
feat/2026-08-13-arc-staleness-doctor-check
```

Push immediately after each commit. Open PR when tests pass. Ryan squash-merges.

---

## Related files

| What | Path |
|------|------|
| Doctor infrastructure | `doctor.py` lines 22–35 (`DoctorCheck`), 1294–1330 (`run_doctor`) |
| Standing register | `docs/standing-checks-register.json` |
| STATUS files (test against) | `docs/plans/STATUS-judgebench.md`, `STATUS-r2b-capture-auth.md`, `STATUS-shadow-ledger-phase0.md`, `STATUS-chroma-reconcile-tier-l.md` |
| Problem diagnosis (Ryan) | `~/Desktop/concurrent-work-loss-pattern-2026-08-13.md` |
| Dependability audit | `~/Desktop/dependability-tracking-audit-2026-08-13.md` |
