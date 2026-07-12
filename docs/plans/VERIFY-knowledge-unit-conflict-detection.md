# VERIFY — Knowledge-Unit Conflict Detection

**Branch:** `plan/2026-07-12-knowledge-unit-conflict-detection`  
**Architecture:** [`ARCHITECTURE-knowledge-unit-conflict-detection.md`](ARCHITECTURE-knowledge-unit-conflict-detection.md)  
**Execution:** [`EXECUTION-knowledge-unit-conflict-detection.md`](EXECUTION-knowledge-unit-conflict-detection.md)

## Mechanical checks (fill after Execute)

| Check | PASS |
|-------|------|
| Hash schema v1 canonicalization (tests 1–4) | pytest |
| Lifecycle ≠ conflicts; unresolved definition | unit test |
| flock derived from data root / same store → same lock | unit or smoke |
| Targeted propose + approve under lock | integration |
| Create-if-absent / pending create collision | pytest |
| Rebase → new id + SUPERSEDED | pytest |
| Crash recovery matrix (test 11) | pytest |
| Barrier race (test 12) | pytest |
| Writer bypass closed (test 14) | inventory + test |
| Legacy import idempotent; Gate 5 warn→block | pytest |
| Uncertain upsert leaves APPROVAL_STARTED | pytest |
| Ordinary index non-governed path unlocked | smoke |
| Event append order / fsync path documented | code review |

## Evidence (fill after runs)

- Tip SHA: _(sha)_
- Test command / counts: _
- Writer inventory: _
- Schema deploy timestamp path: _

```text
Mechanical PASS: YYYY-MM-DD — tip <sha>
```
