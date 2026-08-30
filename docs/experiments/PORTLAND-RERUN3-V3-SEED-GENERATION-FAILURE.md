# Portland Rerun3 Protocol v3 — Seed Generation Failure

**Verdict: `RERUN3 SEED-GENERATION FAILURE`**

Protocol-v3 execution completed with a single semantic candidate. No retry authorized.
Agent B remains unauthorized.

## Supersession

The pre-v3 candidate (thread `01a05042-8c04-7302-8baa-b7fa0039b228`, 27,603 units) is
classified **`PRE-V3 SEED — NON-ADMISSIBLE UNDER FINAL PROTOCOL`**. See
[`PORTLAND-RERUN3-SEED-READY.md`](PORTLAND-RERUN3-SEED-READY.md) (supersession banner added).

Rerun2 remains **`RERUN2 BLOCKED`** — unchanged.

## Protocol v3 lane

| Field | Value |
|-------|-------|
| Branch | `experiment/2026-08-30-portland-rerun3-v3` |
| Run ID | `portland-baseline-2026-08-30-rerun3-v3` |
| Harness | `scripts/experiments/portland-baseline/run_controller_v3.py` |
| Mechanical corrective SHA | `4b8ff94` |
| Background snapshot | Restic `d3908f4e` (27,601 units) |
| Manifest SHA256 | `9947836cc70e871474a4f96837a928e8cd26b16a12f56e885e4ebfa0f4395d6a` |
| Manifest path | `~/.local/share/convmem/experiments/portland-baseline-2026-08-30-rerun3-v3/frozen/protocol_v3_manifest.json` |
| Execution revision | tip of `experiment/2026-08-30-portland-rerun3-v3` at freeze time |
| Blindness verification | **PASS** |

## Phase-4 scope map (frozen before Agent A)

| Phase-4a subject | Locked scope |
|------------------|--------------|
| finance | `general` |
| employment | `coding.backend` |
| transportation | `web_stack.hosting` |
| logistics | `coding.devops` |

Agent A selected **employment** → locked scope **`coding.backend`** before Phase 4b.

## Agent A (Protocol-v3 single candidate)

| Field | Value |
|-------|-------|
| Thread ID | `01a0506f-55b9-7e61-a692-fe4795760e0f` |
| Attempts | 1 (hard single-candidate rule) |
| Rollout | `~/.codex/sessions/2026/08/29/rollout-2026-08-29T21-11-08-01a0506f-55b9-7e61-a692-fe4795760e0f.jsonl` |
| Index exit | `0` |
| Workspace | `~/.local/share/convmem/experiments/portland-baseline-2026-08-30-rerun3-v3/agent-a-workspace/` |

## K admissibility (status only)

| K | Role | Status |
|---|------|--------|
| K1 | housing/lifestyle preference | `present_captured` |
| K2 | explicit concrete monthly housing ceiling | `present_captured` |
| K3 | focal neighborhood observation | `present_captured` |
| K4 | concrete household/workspace need(s) | `present_captured` |
| K5 | rejected option | `present_captured` |
| K6 | causally linked rejection reason | `present_captured` |
| K7 | genuinely unresolved question | `present_captured` |
| K8 | supported provisional neighborhood decision | `present_captured` |
| K9 | later decision superseding K8 | `wrong_property` |
| K10 | move-relevant fact from adjacent scoped source | `wrong_property` |

## Failure causes

1. **K8→K9 relational rule:** Phase 3b retained the earlier provisional priority (`retained_k8: true`).
   Protocol v3 requires a genuine supersession; retention triggers seed-generation failure with no retry.

2. **K10 provenance:** Phase 4b did not produce a distinct ordinary source artifact on disk
   (`phase4_artifact_path: null`). Transcript contained adjacent-subject content, but qualifying
   capture under the locked non-relocation scope requires a separate indexed artifact.

## Not performed

- C1 freeze (seed not ready)
- Agent B (0/16 trials)
- Luna independent review

## Evidence root (local only)

`~/.local/share/convmem/experiments/portland-baseline-2026-08-30-rerun3-v3/`

Private inventory: `results/k_inventory.private.json` (local only).
