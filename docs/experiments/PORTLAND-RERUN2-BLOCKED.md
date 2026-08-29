# Portland Baseline Rerun2 — Blocked Execution Report

**Verdict: `RERUN2 BLOCKED`**

Execution stopped after Agent-A seed admissibility failed on all 3 permitted attempts.
No Agent-B trials were run. No C1 corpus was frozen. No product-value verdict exists.

## Run identifier

`portland-baseline-2026-08-30-rerun2`

## Evidence root (local only)

`~/.local/share/convmem/experiments/portland-baseline-2026-08-30-rerun2/`

## What completed

| Phase | Status |
|-------|--------|
| Background corpus restore (`d3908f4e`, 27,601 units) | **Done** — contamination audit passed |
| Harness (`run_controller.py`, `action_counter.py`) | **Built and used** |
| Agent A attempt 1 | **Done** — thread `01a04fe7-3558-7cd1-b72f-04b934ee3b3b` |
| Agent A attempt 2 | **Done** — thread `01a04ff0-0039-7962-8b74-faffb827c825` |
| Agent A attempt 3 | **Done** — thread `01a04ff1-104e-7af0-9e64-4952d2ff0b27` |
| Seed admissibility | **Failed all 3** |
| C1 freeze | **Not performed** |
| Agent B (16 trials) | **Not started (0/16)** |

## Block reason

Frozen rule: if any required K is `absent`, `present_capture_failed`, or `wrong_property` after Agent-A capture → abort seed and restart. After 3 failures → `RERUN2 BLOCKED`.

Final admissibility (`results/seed_admissibility.json`, attempt 3):

| K | Status |
|---|--------|
| K1 | present_captured |
| K2 | **absent** |
| K3 | present_captured |
| K4 | **absent** |
| K5 | present_captured |
| K6 | present_captured |
| K7 | present_captured |
| K8 | **absent** |
| K9 | **absent** |
| K10 | **absent** |

## Protocol deviation (harness defect)

All 3 Agent-A indexing attempts failed (`index_exit: 1`) with:

`FileNotFoundError: [Errno 2] No such file or directory` at `Path.cwd()` inside `runtime_guard.py`

The harness invoked `convmem index --file` without pinning `cwd` to a stable directory. This prevented reliable corpus capture even when transcript material existed.

**Impact:** `corpus_hit` checks were unreliable; attempt 1 had transcript hits for K1–K3,K5–K7 but still failed on K4,K8,K9,K10 at transcript level.

## Branch / harness

- Branch: `wip/2026-08-29-2026-08-30-portland-rerun2`
- Harness path: `scripts/experiments/portland-baseline/`

## Next step for Ryan

1. Fix harness index `cwd` pinning before any rerun.
2. Decide whether a 4th Agent-A attempt requires explicit re-authorization (frozen max = 3).
3. Do **not** interpret partial Agent-A transcripts as product evidence.
