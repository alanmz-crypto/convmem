# VERIFY — Claude Watch Parity Gate 2

**Arc:** Claude Watch Parity
**Code revision:** local safety corrective — private Gate 0 probes, O_TMPFILE/linkat
publication, closed evidence only, no caller bypass surfaces
**Review tip:** exact HEAD of `fix/2026-09-20-claude-gate2-local-safety-corrective` (after
push; predecessor Copilot FAIL at `10322a6…`)
**Predecessor tip (FAIL):** `10322a6bc23a9ca38da310520f28395eaddda219`
**Base:** `e6a0634c214cf07c89b551d13410bb276a93b38d` (`origin/main` after Gate 1 #311)
**Plan:** `a811f58` — `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md`
**Live-source canary:** `NOT_RUN` (Ryan grant required; hermetic harness only)

## Scope delivered (this corrective)

Corrects Security Review findings **#1, #3, #4, #5, #6** on the capability-bound
redesign at `10322a6…`:

| Finding | Corrective |
|---|---|
| **#1** Gate 0 bypass / production hook surfaces | Removed public `gate0`, `gate0_watcher_probe`, `require_gate0_authority`, `Gate0ProbeHooks`, `_hermetic_gate0_hooks`, and `_gate0` bypass; internal `_enforce_gate0_for_mutable` only |
| **#3** Injectable hook indirection | Private `_probe_watcher_status` / `_probe_network_isolation`; tests monkeypatch those functions |
| **#4** Dictionary evidence coercion | `_build_gate0_evidence` returns closed `Gate0Evidence` only; coordinator outcome parsing rejects free-form strings |
| **#5** Named temp publication | Dynamic `_probe_tmpfile_available`; stage via `O_TMPFILE`; publish via capability-relative `linkat` |
| **#6** Descriptor / artifact cleanup | Probe fd closed on every path; anonymous fd ownership handoff prevents double-close; `durability` on capture evidence |

**Not attempted (finding #2):** `OPEN_SHARED_BOUNDARY_BLOCKER` — coordinator/root
authority still routes through shared `IncrementalJsonlCoordinator` and production
config surfaces; requires Codex architecture decision (mount namespace vs shared-code
authority vs `NO_GATE2_ROUTE`).

## Changed files (this corrective)

- `claude_incremental_canary.py`
- `tests/claude_incremental_canary_worker.py`
- `tests/test_claude_incremental_canary.py`
- `docs/inter-model/VERIFY-claude-watch-parity-gate2.md`

## Commands and results

```bash
/home/lauer/Projects/convmem/.venv/bin/python -m pytest \
  tests/test_claude_incremental_canary.py -q
# 43 passed (38 prior + 5 local-safety regressions)

/home/lauer/Projects/convmem/.venv/bin/python -m compileall -q \
  claude_incremental_canary.py tests/claude_incremental_canary_worker.py \
  tests/test_claude_incremental_canary.py
# exit 0
```

## Static diff checks

| Surface | Status |
|---|---|
| `incremental_jsonl.py` | unchanged |
| `KIRO_ROUTE_FORMATS` | unchanged |
| Watcher / sources / services / activation | unchanged |
| Gate 2 PASS claimed | **no** — finding #2 open; Copilot re-audit not requested |
| PR opened | no |

## Known limits

- **OPEN_SHARED_BOUNDARY_BLOCKER:** finding #2 deferred to Codex architecture lane.
- Live-source canary **NOT_RUN**.
- Successful publication is final; directory `fsync` failure yields
  `durability=unconfirmed` (not rolled back).

**TL;DR [Arc Claude Watch Parity]:** Five local Security Review defects corrected on
branch `fix/2026-09-20-claude-gate2-local-safety-corrective`; finding #2 recorded as
`OPEN_SHARED_BOUNDARY_BLOCKER`; 43 focused tests PASS; Gate 2 PASS not claimed.
