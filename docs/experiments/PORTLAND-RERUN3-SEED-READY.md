# Portland Rerun3 — Seed Ready Report

> **SUPERSEDED — PRE-V3 SEED NON-ADMISSIBLE (2026-08-30)**
>
> This report documents the **pre-Protocol-v3** candidate generated before Codex
> Sol Extra-High adjudication was available. It is preserved as **protocol-development
> evidence only**.
>
> **Classification:** `PRE-V3 SEED — NON-ADMISSIBLE UNDER FINAL PROTOCOL`
>
> - Do **not** run Agent B from this candidate.
> - Do **not** use thread `01a05042-8c04-7302-8baa-b7fa0039b228`, its K1–K10 inventory,
>   answer values, 27,603-unit C1 snapshot, or semantic admissibility result for
>   Protocol-v3 evidence.
> - **Authorized Protocol-v3 lane:** branch `experiment/2026-08-30-portland-rerun3-v3`,
>   harness `run_controller_v3.py`, run ID `portland-baseline-2026-08-30-rerun3-v3`.
>
> History below is **unchanged** for audit trail.

---

**Historical status (pre-v3): `RERUN3 SEED READY`** (attempt 1 of 3 — **non-admissible under v3**)

Agent-B execution was **never authorized** from this candidate. Await Ryan seed review
before any Agent-B work; Protocol-v3 supersedes this gate entirely.

## Prior runs (preserved)

| Run | Status |
|-----|--------|
| Rerun1 / Run1 | INVALID — do not use |
| Rerun2 | `BLOCKED AT SEED ADMISSIBILITY` — preserved unchanged |
| Rerun3 false-positive | First automated SEED READY retracted (empty corpus + admissibility bug) |

## Harness corrective commits

| Commit | Purpose |
|--------|---------|
| `7e2f0da` | Pin `convmem index` cwd to `~/Projects/convmem` + regression test (2/2 PASS) |
| `a12581c` | Rerun3 controller + role-based admissibility |
| `e23d4a0` | Fix Restic repo path; separate transcript vs corpus hits |
| `4b8ff94` | Writable `units_export` path (fixes `/dev/null.lock` index failure) |

Branch: `wip/2026-08-29-2026-08-30-portland-rerun2` (pushed)

## Agent A (valid candidate)

| Field | Value |
|-------|-------|
| Run ID | `portland-baseline-2026-08-30-rerun3` |
| Attempt | 1 (admissible; attempts 2–3 not needed) |
| Thread ID | `01a05042-8c04-7302-8baa-b7fa0039b228` |
| Rollout | `~/.codex/sessions/2026/08/29/rollout-2026-08-29T20-22-13-01a05042-8c04-7302-8baa-b7fa0039b228.jsonl` |
| Index exit | `0` |
| Units indexed | `2` |
| Index cwd | `/home/lauer/Projects/convmem` |

Frozen multi-phase prompt: `results/frozen_protocol.json` (local evidence root only).

## K admissibility (status only — no public answer values)

| K | Role | Status |
|---|------|--------|
| K1 | housing/lifestyle preference | `present_captured` |
| K2 | concrete monthly budget ceiling | `present_captured` |
| K3 | neighborhood observation | `present_captured` |
| K4 | housing/household must-have(s) | `present_captured` |
| K5 | rejected option | `present_captured` |
| K6 | rejection reason | `present_captured` |
| K7 | unresolved question | `present_captured` |
| K8 | earlier decision | `present_captured` |
| K9 | later superseding decision | `present_captured` |
| K10 | fact outside relocation scope | `present_captured` |

Private inventory: `results/k_inventory.private.json` (local only).

## Background + C1 freeze

| Field | Value |
|-------|-------|
| Background snapshot | Restic `d3908f4e` (2026-08-28 00:15:38 CDT) |
| Background units | 27,601 |
| Frozen units | **27,603** (+2 Agent-A units) |
| Store digest | `edebc04accdbc773dc463fcf1af6de2c74fd743fcd3a3a1d8609f69be387c215` |
| Frozen at | `2026-08-30T01:25:50Z` |
| Contamination audit | **PASS** — no prior invalid-run artifacts |
| Agent-B material in freeze | **Absent** |

Evidence root: `~/.local/share/convmem/experiments/portland-baseline-2026-08-30-rerun3/`

## Not performed

- Agent B (0/16 trials)
- Luna independent results review
- ConvMem product verdict
