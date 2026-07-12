# Execution Plan — Restic Integrity Preflight (Gate 6)

```
Planning Status

Phase:        Execution Planning → awaiting HITL before Execute
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Functions:    Planner
Lanes:        Cursor (Tier A); Codex read-only if Ryan requests plan audit
Authority:    Architecture gates 1–6 accepted 2026-07-12 (Ryan: accept defaults)
```

**Architecture SSoT:** [`ARCHITECTURE-restic-integrity-preflight.md`](ARCHITECTURE-restic-integrity-preflight.md)  
**Branch:** `plan/2026-07-12-restic-integrity-preflight`  
**Worktree:** `~/.local/share/convmem/worktrees/plan-2026-07-12-restic-integrity-preflight`  
**Sequenced plan:** `~/.cursor/plans/gate_6_next_steps_fceb035f.plan.md`

---

## Gate decisions (accepted defaults)

| # | Choice |
|---|--------|
| 1 | Depth: structural `restic check` + `--read-data-subset 5%`; optional `--full-read-data` for manual deep runs |
| 2 | Cadence: **one-time proof** this pass (no timer) |
| 3 | Doctor: **defer** — no doctor freshness probe; no cadence this pass |
| 4 | Coupling: **separate** script; no restore-drill happy-path change |
| 5 | Scope: local `RESTIC_REPOSITORY` only (`--tag convmem-chroma`) |
| 6 | Reports: `~/.local/share/convmem/integrity-check/reports/` |

---

## Goal

Prove the local Restic repo (tag `convmem-chroma`) passes structural integrity plus a 5% data-subset read, with durable PASS/FAIL reports — without touching live Chroma, the write-gate, restore-drill, or doctor.

---

## Tasks

| ID | Deliverable | In scope | Depends on | Gates | Lane |
|----|-------------|----------|------------|-------|------|
| T1 | This EXECUTION + [`VERIFY-restic-integrity-preflight.md`](VERIFY-restic-integrity-preflight.md) | Docs only | Arch accept | Ryan HITL on this plan | Cursor |
| T2 | `scripts/restic_integrity_check.py` (or `.sh`) runner | Init report early; `restic check --tag convmem-chroma --read-data-subset 5%`; lock exit 11 distinct; `--full-read-data` override; intentional failure path; EXIT trap preserves status | T1 HITL | `--help`; hermetic tests | Cursor |
| T3 | Hermetic unit tests | Report shape, CLI wiring, mocked failure/lock paths — **no** live Restic required | T2 | `pytest -q tests/test_restic_integrity_check.py` | Cursor |
| T4 | Happy-path live run | One real local-repo check; report under integrity-check/reports/ | T2–T3 | Report status PASS; nonzero only on real fail | Cursor |
| T5 | Intentional-failure run | Bad password file / missing repo / forced lock simulation — nonzero + report | T2 | Report documents failure code | Cursor |
| T6 | Commit + push | Explicit refspec every commit | T2–T5 | Remote tip has evidence | Cursor |

### Out of scope

- Doctor freshness / recurring cadence
- Restore-drill edits or `--with-integrity-preflight`
- Live-write gate / snapshot cadence / `restic-ensure` behavior
- Offsite/`RESTIC_EXTERNAL_REPOSITORY` check
- Live Chroma stop/replace/write
- Shared-checkout FF and host `index` smoke (sequenced plan Phases 1–2 — after this PR or parallel once T6 pushed)

### Evidence requirements (Execute phase)

- Hermetic pytest PASS
- Happy-path report path + exit 0
- Failure report path + nonzero exit
- Grep confirms no doctor freshness probe added to `doctor.py`

### Execute entry

- First implementation task: **T2** after Ryan HITL-approves this EXECUTION plan (or says “execute” / “do what is designed”).
- Follow [`EXECUTE-TASK.md`](../planning/EXECUTE-TASK.md) loops 0–6.

---

## Sign-off

**Execution Planning:** Cursor emits this artifact.  
**HITL:** Ryan approves before code (T2+).  
**Mechanical (after Execute):** Cursor fills VERIFY after T4–T5.  
**Ryan:** read happy-path report; merge when satisfied.  
**Kiro (optional):** review VERIFY + report; no merge authority.

---

## Exit Criteria (Execution Planning)

- [x] Direction restated; gates recorded as accepted defaults
- [x] 1–5 bounded tasks; no option forks
- [x] Dependencies and gates named
- [x] Doctor freshness explicitly out of scope
- [ ] No self-transition to Execute until Ryan HITL

Cursor must stop here. Await HITL.
