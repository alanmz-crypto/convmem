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

**Subject / tip:** `2a20209` (T5 complete — CG-2 Execute T1–T5 on branch)

**Architecture baseline (prior lock text):** `e680ce837653698a5be8b78ba02db2f880c40c63`

**Design A architecture lock (`main` base):** `cd9554e4c3006f7e0695d5d17a69696cc913c566`
(amendments papered 2026-08-21; docs branch — not yet merged)

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
V8a independent sign-off is **PASS** (Kiro); V8b (soak grant) is **PASS**; soak
**completion** was separately Ryan-accepted 2026-08-21; V8c remains **PENDING**
(definition papered under Design A — not PASS). No owner activation granted.

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
| `subject_tip_sha` | `2a20209` |
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
| V8a | Independent reviewer signs exact tip | **PASS** — independent sign-off justified | Kiro independent review of CG-2 implementation tip `2f427fcfb8818dd665310bae7e8cd5ffa066bdcc` and preservation check on `main` `451f523b48c9fd998a050edfe6766d14249dcc6b` (CG-2 implementation surfaces unchanged between them). Focused CG-2 tests **43/43 PASS**; CG-2 + generation-core **76/76 PASS**; query/doctor/rerank **84/84 PASS**. Full suite timed out at 180s — **not** claimed PASS or FAIL. No material defects. Non-blocking carry-forward for V8c/canary prep: `FrozenGenerationStable` and `RetryBudgetTerminates` share one test; structural immutability supplements coverage (does **not** block V8a). |
| V8b | Ryan accepts package / grants soak separately | **PASS** — legacy-only gateway soak grant recorded | Grant recorded in `LATEST.md`. V8b covers the **grant only**, not soak-completion success (see Soak-completion evidence below). |
| V8c | First-owner packet + one-shot activation grant | **PENDING** (not PASS) | **Definition (Design A / HITL #3):** V8c PASS = Ryan accepted the complete first-owner packet **and** issued the exact one-shot first-owner activation grant. Packet **before grant** must already bind exact `G_rb` (id + manifest SHA) **and** exact `G_canary` (id + manifest SHA) plus source hashes, pipeline fingerprints, embedding provenance, qualification evidence, and implementation SHA. No “fill `G_canary` at cutover”; no post-grant packet amendment to discover the target. Grant is one-shot and self-invalidating: if source/current authority/preconditions change before publication, first-cutover refuses and a **new packet + new V8c grant** are required. **Canary completion** is a separate later evidence record and Ryan decision — not implied by V8c PASS. **Current state:** not authorized; do not mark PASS. Next governed docs step after Design A architecture papering: Design A **execution plan** (packet field anchoring), not premature full V8c packet papering. |

## Soak-completion evidence (separate from V8b)

**Status:** **ACCEPTED** — Ryan accepted completed CG-2 legacy-only gateway soak on **2026-08-21**.

This record does **not** redefine V8b. V8b remains the soak **grant**. Soak
**completion** is evidenced here only. First generational owner, activation,
activation manifest, GC, Shadow, and R2b remain unauthorized.

| Field | Evidence |
|---|---|
| Acceptance date | 2026-08-21 (Ryan GATE — soak completion) |
| Watch continuity | PID **955623**; started **2026-08-18 02:12:54 CDT**; `NRestarts=0`; continuous ≥72h through acceptance |
| Authority | `owners=0` (legacy-only); live `logical_projection` PASS; `source_reconciliation` fresh (staleness ≪ 300s) |
| RUNBOOK pauses | No demonstrated CG-2 RUNBOOK pause condition during the accepted window |
| Midnight observer samples | Six `RESET_REQUIRED` samples (~00:00 / 00:15 CDT Aug 19–21) adjudicated **non-blocking**. Timing is consistent with the daily restic freshness boundary; the exact failing doctor check was **not** captured (checker discards doctor JSON on nonzero exit). Checker is observer-only; these observer events do **not** reset the RUNBOOK soak clock. |
| Final retrieval eval | **2026-08-21T08:17Z** — `python scripts/eval-retrieval.py` exit **0**; 8/8 PASS; P@1 **87.5%**; P@k **100%**; MRR **0.9375**; Recall@k **100%**; **no regression vs baseline**; no watch restart; no production/repository mutation |
| Out of scope of this acceptance | First owner / activation / GC / Shadow / R2b **not** granted (V8c remains PENDING) |

## Formal property → test map

See `cg2_property_map.py` and `collect_execute_evidence()["property_map"]`.
Fifteen architecture properties mapped to pytest modules (12 core + fallback pair).

## Evidence log

```text
VERIFY-cg2-production-activation — Execute mechanical fill
Architecture baseline: e680ce837653698a5be8b78ba02db2f880c40c63
Execution grant plan: 6a808f1543f2c93270d9f0ed1ae88cad27f6556b
Subject tip (branch): feat/2026-08-15-cg2-production-activation @ 2a20209
Mechanical run: pytest isolated CG-2 bundle + full suite (see PR)
Independent sign-off (V8a): PASS — Kiro; subject 2f427fc; main preservation 451f523
Ryan GATE soak grant (V8b): PASS — grant recorded (not completion)
Soak completion: ACCEPTED 2026-08-21 (separate evidence section above)
First-owner packet (V8c): PENDING — definition papered (Design A); not PASS; not authorized
V8c PASS definition: complete packet accepted + exact one-shot activation grant
Canary completion: separate later evidence / Ryan decision
Production activation: NOT PERFORMED
Automatic GC: NOT PERFORMED
```
