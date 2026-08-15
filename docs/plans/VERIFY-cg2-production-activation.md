# Verify Plan — CG-2 production activation

```text
Planning Status

Phase:        Verify (Execute mechanical evidence filled)
Characters:   Independent Reviewer, Test-First Reviewer
Functions:    Reviewer
Lanes:        Cursor mechanical; Kiro or named independent lane sign-off; Ryan GATE
Authority:    Post-Execute HITL — mechanical evidence from isolated rehearsal
```

**Status:** Mechanical Execute evidence filled on `feat/2026-08-15-cg2-production-activation`.
Does **not** authorize production soak, owner cutover, or GC.

**Subject / tip:** `f8419e3` (T5 complete — CG-2 Execute T1–T5 on branch)

**Architecture baseline:** `e680ce837653698a5be8b78ba02db2f880c40c63`

**Execution plan (Ryan grant):** `6a808f1543f2c93270d9f0ed1ae88cad27f6556b`

**EXECUTION / ARCHITECTURE:**
[`EXECUTION-cg2-production-activation.md`](EXECUTION-cg2-production-activation.md) /
[`ARCHITECTURE-cg2-production-activation.md`](ARCHITECTURE-cg2-production-activation.md)

**Goal:** Prove implementation preserves one serving authority, rejects stale work,
handles lost source notifications, accounts for logical identity, and remains safe
through isolated rehearsal — before any separately granted gateway soak.

## Human consequence

Passing mechanical VERIFY lets Ryan decide whether to open a PR and later grant
**legacy-only gateway soak**. It does **not** activate a generational owner or
enable GC.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor supplied mechanical evidence; Kiro or Ryan-named reviewer signs at PR; Ryan gates soak and activation separately. |
| **What** | CG-2 authority migration T1–T5 on feature branch. |
| **When** | After Execute on branch; before gateway soak grant. |
| **Why** | Race-sensitive authority, reconciliation, and mixed-mode paths need mechanical oracles beyond ordinary green tests. |
| **How** | Static inventories, hermetic pytest, isolated copied-corpus rehearsal, Chroma 1.5.9 mixed-mode proof. |

**TL;DR:** Mechanical checks PASS on isolated fixtures at pinned Chroma 1.5.9;
human sign-off and Ryan soak grant remain pending.

### Merge reading

- [CG-2 architecture](ARCHITECTURE-cg2-production-activation.md)
- [CG-2 execution plan](EXECUTION-cg2-production-activation.md)
- [Operator runbook](RUNBOOK-cg2-production-activation.md)
- [Formal model](formal/cg2/README.md)
- [Property map](../cg2_property_map.py) (`cg2_property_map.py`)

## Scope lock

| In scope | Out of scope |
|---|---|
| Global serving boundary; all owners legacy in rehearsal | Production owner activation |
| Authority resolution, typed fallback, retry budget | Corpus-wide snapshot claims |
| Source-hash guard and bounded reconciliation | Post-check source mutation guarantee |
| Logical accounting and serving vs physical stats | Physical ID as semantic identity |
| Chroma 1.5.9 mixed-mode control comparison | Exact kNN; queue surgery |
| Isolated rehearsal and failure-matrix pytest map | Automatic GC; legacy retirement |

## Verification design

| Field | Answer |
|---|---|
| **Independent oracle** | Active-manifest logical sets + authority-clean Chroma 1.5.9 control; formal TLA+ is transition oracle only. |
| **Failure-injection method** | Hermetic pytest: source drift, fence/pointer churn, lost notification, mixed inactive rows, cardinality underfill, authority refusal. |
| **Negative control** | Inventory tests fail on unclassified reads; cardinality error on forced underfill (`test_mixed_mode_proof`). |
| **Dual-path coverage** | Serving repository, query layer, MCP stats labeling, doctor checks, mixed-mode proof. |

## V0 — Preconditions and evidence identity

| Field | Value |
|---|---|
| `subject_tip_sha` | `f8419e3` |
| `architecture_sha` | `e680ce837653698a5be8b78ba02db2f880c40c63` |
| `execution_plan_sha` | `6a808f1543f2c93270d9f0ed1ae88cad27f6556b` |
| `gate_applicability` | `pending_pr_open` — BugBot when PR opened |
| `bugbot_reviewed_sha` | Pending |
| `chroma_version` | `1.5.9` (matches `requirements.txt`) |

| ID | Check | Result | Evidence |
|---|---|---|---|
| V0a | Subject tip resolves to implementation branch | PASS | `feat/2026-08-15-cg2-production-activation` |
| V0b | Execute recorded applicability decision | PASS | `cg2_rehearsal.external_review_record()` |
| V0c | BugBot SHA equals subject tip when required | PENDING | Awaiting PR review |
| V0d | Required findings fixed or Ryan-accepted | PENDING | PR lifecycle |
| V0e | Exemption recorded if applicable | SKIP | No exemption claimed |

## V1 — Serving-boundary completeness

| ID | Check | Result | Evidence |
|---|---|---|---|
| V1a | Static inventory classifies reads; empty fails | PASS | `tests/test_file_generation_read_path_inventory.py` |
| V1b | Serving paths use gateway or explicit non-serving class | PASS | `tests/test_serving_index_repository.py`, inventory EXPECTED |
| V1c | Legacy gateway matches direct Chroma on isolated corpus | PASS | `tests/test_cg2_rehearsal.py`, `test_legacy_gateway_matches_direct_chroma_query_units` |
| V1d | Authority failures do not reach legacy fallback | PASS | `test_authority_failure_never_triggers_query_fallback` |

## V2 — Authority resolution and fallback safety

| ID | Check | Result | Evidence |
|---|---|---|---|
| V2a | Fence/pointer/retirement evidence read without torn serving | PASS | `tests/test_serving_authority.py` |
| V2b | Post-fence cannot serve; legacy-global equivalence preserved | PASS | `test_fenced_owner_blocks_serving_open`, V1c |
| V2c | Qualification/integrity/mixed-mode failures fail closed | PASS | `test_serving_authority_error_is_not_transient`, mixed-mode gates |
| V2d | Only typed transient enters mediated fallback | PASS | `test_transient_backend_uses_mediated_fallback_only` |
| V2e | Retry budget → `AUTHORITY_UNSTABLE`, no fallback | PASS | `test_retry_budget_exhaustion_raises_authority_unstable` |

## V3 — Source freshness and reconciliation

| ID | Check | Result | Evidence |
|---|---|---|---|
| V3a | Source mutation refuses promotion | PASS | `tests/test_source_freshness_promotion.py` |
| V3b | Startup/sweep/overflow paths run | PASS | `tests/test_source_reconciler.py` |
| V3c | Lost notification found and queued | PASS | `test_discover_legacy_drift_when_source_changes`, sweep tests |
| V3d | Dirty state cleared only by successful sweep | PASS | `test_sweep_queues_owner_work_and_clears_dirty` |
| V3e | Bounded queue and coalescing | PASS | `test_owner_queue_coalesces_to_latest_desired_state`, admission test |
| V3f | Path policy tests | PASS | `tests/test_source_observation.py` (existing path policy) |

## V4 — Logical accounting and provenance

| ID | Check | Result | Evidence |
|---|---|---|---|
| V4a | Empty-set completeness/purity convention | PASS | `tests/test_logical_accounting.py::test_empty_set_membership_convention` |
| V4b | Distinct drift classes | PASS | `tests/test_logical_accounting.py` classification fixtures |
| V4c | Retained inactive not active drift | PASS | `test_retained_inactive_is_not_wrong_generation` |
| V4d | Namespaced logical identity | PASS | `logical_accounting.namespaced_logical_key` |
| V4e | Serving vs physical counts separated | PASS | MCP `stats` view field; `test_logical_projection` doctor |
| V4f | Embedding/alias blockers in doctor | PASS | `embed_collection_identity` WARN path unchanged |

## V5 — Mixed-mode backend correctness

| ID | Check | Result | Evidence |
|---|---|---|---|
| V5a | Authority-clean control matches embeddings/HNSW metadata | PASS | `mixed_mode_control.build_authority_clean_control` |
| V5b | Zero unauthorized rows in mixed result | PASS | `test_proof_gates_pass_against_control` authority_safety |
| V5c | No silent underfill vs control at representative k | PASS | `authorized_cardinality` gate in mixed-mode proof |
| V5d | Quality reported separately from safety/cardinality | PASS | `measure_retrieval_quality` in `mixed_mode_proof.py` |
| V5e | Unbounded expansion blocked; no raw fallback | PASS | `MixedModeCardinalityError`, `test_underfill_raises_cardinality_error` |

## V6 — Crash, rollback, retention, and recovery

| ID | Check | Result | Evidence |
|---|---|---|---|
| V6a | Kill/corruption paths fail closed or recover | PASS | `tests/test_file_generation_validate.py`, pointer recovery tests |
| V6b | Active/previous retention survives restart | PASS | `test_mixed_mode_proof.py::test_retention_survives_restart` |
| V6c | Rollback uses retained generation, not legacy resurrection | PASS | `tests/test_file_generation_store.py` previous retention |
| V6d | Recovery follows durable pointer | PASS | `tests/test_file_generation_pointer.py` recovery paths |
| V6e | GC disabled; protected generations not deleted | PASS | `PHYSICAL_DELETION_DISABLED`; no delete in proof path |

## V7 — Operational budgets and soak readiness

| ID | Check | Result | Evidence |
|---|---|---|---|
| V7a | Ratified budget constants recorded | PASS | `cg2_rehearsal.measured_budgets()` — retry 5/2.0s, reconciliation 300s |
| V7b | Chroma 1.5.9 storage/queue characterized locally | PASS | `characterize_chroma_storage` in mixed-mode proof tests |
| V7c | Legacy-only gateway rehearsal isolated | PASS | `run_legacy_gateway_rehearsal` — equivalence PASS |
| V7d | Shadow comparison | SKIP | Shadow ledger disabled; deferred to granted soak |
| V7e | Runbook names grants and pause conditions | PASS | `RUNBOOK-cg2-production-activation.md` |

## V8 — Independent sign-off and Ryan GATE

| ID | Check | Result | Evidence |
|---|---|---|---|
| V8a | Independent reviewer signs exact tip | PENDING | Kiro at PR |
| V8b | Ryan accepts package / grants soak separately | PENDING RYAN GATE | |
| V8c | First-owner packet (future) | PENDING | Not in Execute scope |

## Formal property → test map

See `cg2_property_map.py` and `collect_execute_evidence()["property_map"]`.
Fifteen architecture properties mapped to pytest modules (12 core + fallback pair).

## Evidence log

```text
VERIFY-cg2-production-activation — Execute mechanical fill
Architecture baseline: e680ce837653698a5be8b78ba02db2f880c40c63
Execution grant plan: 6a808f1543f2c93270d9f0ed1ae88cad27f6556b
Subject tip (branch): feat/2026-08-15-cg2-production-activation @ f8419e3
Mechanical run: pytest isolated CG-2 bundle + full suite (see PR)
Independent sign-off: pending PR
Ryan GATE (soak): pending
Production activation: NOT PERFORMED
Automatic GC: NOT PERFORMED
```
