# Verify Plan — CG-2 production activation

```text
Planning Status

Phase:        Verify (historical gateway evidence retained; D1 reference-v2 globally closed)
Characters:   Independent Reviewer, Test-First Reviewer
Functions:    Reviewer
Lanes:        Cursor mechanical; Kiro independent integrated sign-off; Ryan GATE
Authority:    D1 integrated closure recorded at one tip; no production grant
```

**Status:** Historical gateway/Design A mechanical evidence is preserved below.
D1 reference-v2 corrective is **globally closed** at integrated review tip
`9cfb085836ca92c308d1a8f966aced9bbb48546e` (Kiro integrated PASS, 2026-08-30;
Ryan-delegated ledger write). The copied-`G_rb` V6c drill remains historical
only. This document authorizes no production D1 publication, owner cutover,
V8c grant, cleanup, or GC.

**Subject / tip:** `2a20209` (T5 complete — CG-2 Execute T1–T5 on branch)

**Architecture baseline (prior lock text):** `e680ce837653698a5be8b78ba02db2f880c40c63`

**Design A architecture lock (`main` base):** `cd9554e4c3006f7e0695d5d17a69696cc913c566`
(amendments papered 2026-08-21; docs branch — not yet merged)

**Execution plan (Ryan grant):** `6a808f1543f2c93270d9f0ed1ae88cad27f6556b`

**EXECUTION / ARCHITECTURE:**
[`EXECUTION-cg2-design-a.md`](EXECUTION-cg2-design-a.md) /
[`ARCHITECTURE-cg2-production-activation.md`](ARCHITECTURE-cg2-production-activation.md)

**Goal:** Preserve valid gateway evidence and define the prospective proof that
reference-v2 qualification, retained evidence, serving, rollback, and recovery
all bind the same original D0-covered physical state.

## Human consequence

Passing the new corrective rows at one independently reviewed implementation and
formal-model tip would let Ryan decide whether to grant a separate production
D1 reference publication. It would not activate an owner or enable GC.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor will supply corrective evidence only after grant; Kiro independently reviews one exact implementation/model tip; Ryan gates production separately. |
| **What** | Retained-reference-v2 manifest, same-reader qualification/serving, recovery binding, property map v3, and formal model. |
| **When** | After independent plan review and Ryan implementation grant; before any D1 retry. |
| **Why** | The failed copied generation drifted under cosine Chroma, and sidecar proof would not govern rollback serving. |
| **How** | Exact-ID target reader + D0 root reproduction + recovery restore + negative controls + TLC invariants. |

**TL;DR:** Historical V8a/V8b/soak evidence remains valid. D1R0–D1R12 are
**SATISFIED / PASS together** at `9cfb085836ca92c308d1a8f966aced9bbb48546e`.
V8c and production D1 remain unauthorized. No owner activation granted.

### Merge reading

- [CG-2 architecture](ARCHITECTURE-cg2-production-activation.md)
- [CG-2 D1 corrective execution plan](EXECUTION-cg2-design-a.md)
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

## Design A Execute closure (D7 — mechanical evidence)

**Status:** Mechanical bundle collected at closure tip `b64860b` (branch
`feat/2026-08-27-2026-08-27-cg2-d5-rehearsal`). **Does not** authorize
production D0, production `G_rb`/`G_canary`, V8c, cutover, PR merge/landing,
or any production operation.

| Field | Value |
|---|---|
| D6 accepted starting tip | `9a042fbc0d18500b91e056f47f60a00e20ccdb75` |
| D7 closure tip | `b64860b05575c62b4563c02ed6f05bb39910b4dc` |
| Design A architecture SHA | `3d8b151907f02c8b8ead89585fb43904840b210b` |
| Superseding execution plan SHA | `9a171bdf03d501ff891d991bbdad6acc1abda56c` |
| D6 TLC model tip (historical) | `ca1298e2c5741e2fca99dbd670d0775a398064f8` |
| Property map schema | `convmem/cg2-design-a-property-map-v2` |
| Evidence collector schema | `convmem/cg2-design-a-execute-evidence-v2` |

**Provenance distinction (§12.6 reconciliation):**

| Generation | Proof profile | Meaning |
|---|---|---|
| `G_rb` | `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` | Historical exact-vector state under ratified D0 chain; `historical_embedding_model.status=UNKNOWN`, identifier `null` |
| `G_canary` | `KNOWN_MODEL_AND_VECTOR_V1` | Writer-produced model and vector provenance under known-model profile |

**Production-negative confirmations:** no production D0 capture/validation,
no Ryan production D0 ratification, no production `G_rb`/`G_canary` build,
no fence/pointer publication, no owner activation, no V8c grant, no GC/Shadow/R2b.

## D1 reference-v2 corrective gate — integrated closure

These rows supersede the copied-generation interpretation of historical V6c.
**Global D1 closure:** all rows **SATISFIED / PASS** together at integrated
review tip `9cfb085836ca92c308d1a8f966aced9bbb48546e` (Kiro integrated
independent review, 2026-08-30). Closure does not authorize production D1.

| ID | Prospective check | Current result | Required evidence |
|---|---|---|---|
| D1R0 | Reviewed planning and implementation identity | **SATISFIED / PASS** | Kiro integrated independent PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e` (2026-08-30, fresh seed). Ryan-accepted planning SHA `8b5b53e2a460753711392379535b127cefa244b8`; formal corrective `7a8fd76350b7076f5d75e3ad53c7392647b2eac0` is ancestor; runtime delta `8897d1358f985e38a1070816189460d980824d75..9cfb085836ca92c308d1a8f966aced9bbb48546e` limited to reference-v2 implementation surfaces; commits after tip on branch are docs-only (`d9f1c8b`, `2b16ead`). |
| D1R1 | Existing D0 chain is consumed unchanged | **SATISFIED / PASS** | Kiro integrated independent PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e` (2026-08-30, fresh seed). Re-bound at final tip: reference-v2 consume prefix loads ratified production D0 unchanged — candidate `d4be814abc59e77a2d1420b6d7db8859f5a5fe6f449f107fbdd23eb9aecaa0be`, validation `4af9388454e80dedeb6988500647d2766333e22d4e5fecacadf055d14b667793`, ratification `ryan-d0-webui-2026-08-29`, vector root `28df88466daaf16c270b1112d2a160fecc9d47c1014bc5bf91e94ae70e83a24e`, snapshot root `8ee62dfd434e092b6c9d5367dbd53fa9e4402078dfa30aad2277f417ce1ebd49`, query context `df95af20d1774bb225d77fe2408450ee69ff3e7a9fee383ffa79e72febb370be`, owner `6daf07d443fbd1c4559f4c6516d7f1f585db25106f1aca3437b2ca7ecf0e39b3`; 37 LEGACY rows; roots reproduced; `ChromaStore(create_collections=False)` structurally non-creating; D0 artifacts unchanged. Prior per-row PASS at `8897d135…` subsumed by integrated closure. |
| D1R2 | Correct protocol identity | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Fingerprint `convmem/cg2-rollback-baseline-reference-v2`; deterministic reference-v2 target ID; `RETAINED_LEGACY_REFERENCE_V2` / `convmem/retained-legacy-reference-manifest-v2`; evidence v2; `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` unchanged. Primary: `tests/test_cg2_reference_v2.py::test_deterministic_reference_v2_target_id`. |
| D1R3 | Exact original physical membership | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Hermetic adversarial membership oracles refuse duplicate/additional/wrong-owner/missing/substituted physical IDs. Primary tests: `test_adversarial_{duplicate,additional,wrong_owner,missing,substituted}_physical_id_refuses`. |
| D1R4 | Exact row/readback state | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Serving-reader documents, immutable metadata/provenance, and canonical float32 hashes reproduce all D0 roots; one-ULP mutation refuses (`test_adversarial_one_ulp_vector_drift_refuses`). |
| D1R5 | One qualification/serving authority | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Spy/integration evidence: cold qualification, first-cutover rebind, and rollback scoring call the same target-aware reader (`test_same_reader_spy_qualification_and_serving`, `test_reference_v2_first_cutover_rollback_same_reader_rehearsal`). |
| D1R6 | No copied or sidecar vector authority | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Static inventory + write/lookup spies prove no Chroma add/upsert, `.f32le`/sidecar, re-embedding, or reconstruction participates (`test_zero_copied_vector_rows`, `test_reference_v2_static_inventory_no_sidecar_or_copied_vector_authority`, `test_reference_v2_lookup_spy_no_sidecar_or_generation_get_rows`). |
| D1R7 | Fresh-process production-shape qualification | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Child process reopens actual-layout Chroma and governed generation root, reloads D0, verifies context and selector, rejects stale/forged evidence (`test_reference_v2_fresh_process_failure_refuses_retained_evidence`). |
| D1R8 | Retention lifecycle truthful | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. `RETAINED_ROLLBACK_BASELINE` only after D1R1–D1R7 and D1R9; no `G_RB_CONVERT_COLD_VALIDATED` literal (`test_retention_lifecycle_uses_retained_rollback_baseline_only`). |
| D1R9 | Recovery covers one complete target | **SATISFIED / PASS** | Kiro integrated independent PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e` (2026-08-30, fresh seed). Re-bound restored reader with tip code: restic snapshot `7d9ea1465c129e778ce4787008ac06820bf6f9abc28fd76a9f47fcdd55d2d0e1`; target `2740ec5b5f01f2f293d07bbf0677c4e26f8daadefab8192682410e6685af2364`; manifest SHA-256 `8ca18854215d6c100aa11ca686f88b590609bfcac7f21dec44fcbc9f70b8ab0c`; evidence `/tmp/d1r9-ra-drill-20260830/evidence/`. Restored state preserves D0 chain, 37 LEGACY rows, exact snapshot/vector/query-context roots; recovery eligibility/membership/cold validation PASS; path isolation. **Non-blocking caveats (carry forward):** (1) production lacked retained reference-v2 at drill time — complete target materialized on isolated scratch only (`production_has_retained_reference_v2 = false`); (2) restore-inventory reported BLOCKED exit 31 on out-of-scope `decisions-approved.jsonl`. Prior per-row PASS at `8897d135…` subsumed by integrated closure. |
| D1R10 | Failed convert-v1 remains terminal | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. `2d01dfca08ac388e7ac74d145e789a8a35d8b97c4bf2ee6d971a95a8a74c4b3c` cannot be reused, activated, selected as previous, or cleaned; no `abandoned_d1` schema (`test_failed_convert_v1_target_id_refuses`, `test_reference_v2_id_differs_from_convert_v1`). |
| D1R11 | D0 exception contract preserved | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Non-finite D0 vector raises `D0AttestationError`; full pre-existing suite has no regression — Kiro independently reproduced **51/51 PASS** (`test_malformed_embedding_raises_d0_attestation_error`, `test_vector_float32_encoding_and_nonfinite_refusal`, `tests/test_cg2_rollback_baseline.py`). |
| D1R12 | Property map and formal model close the same contract | **SATISFIED / PASS** | Kiro integrated PASS at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Formal corrective `7a8fd76350b7076f5d75e3ad53c7392647b2eac0` is ancestor; `convmem/cg2-design-a-property-map-v3` at tip; eight substantive `GRb*` invariants in four positive TLC configs; negative controls on `GRbReferenceMembershipExact` and `GRbServingReadsReferencedRows`. Prior TLC v1.7.4 empirical PASS at corrective tip retained. **Non-blocking caveat (carry forward):** jar SHA-attestation wrapper (`run-d1r12-tlc.sh`) still unattested — separate supply-chain control, not the empirical model-checking result. |

**D1 integrated closure record (2026-08-30, Ryan-delegated ledger write):** All
D1 reference-v2 corrective obligations **D1R0–D1R12** are **SATISFIED / PASS
together** at integrated review tip `9cfb085836ca92c308d1a8f966aced9bbb48546e`
on branch `fix/2026-08-30-cg2-d1r0-d1r11-closure-evidence`. Kiro performed one
integrated independent review (fresh seed) and returned **ALL 13 rows PASS**.
Kiro independently reproduced **20/20** reference-v2 pytest and **51/51**
regression checks. Ryan delegated the global D1 ledger write to Cursor on
2026-08-30 after Kiro integrated PASS. **Three non-blocking caveats (carry
forward verbatim):** (1) D1R9 scratch materialization —
`production_has_retained_reference_v2 = false` (complete target materialized
on isolated scratch only; production not cut over); (2) D1R9 restore-inventory
BLOCKED exit 31 on out-of-scope `decisions-approved.jsonl`; (3) D1R12 jar
SHA-attestation wrapper (`run-d1r12-tlc.sh`) still unattested — separate
supply-chain control, not the empirical TLC model-checking result. **Does not
authorize production D1 publication, V8c, owner cutover, activation, or GC.**

**D1R12 formal closure record (2026-08-30):** Subsumed by integrated closure
at `9cfb085836ca92c308d1a8f966aced9bbb48546e`. Prior per-row PASS at formal
corrective `7a8fd76350b7076f5d75e3ad53c7392647b2eac0` retained in evidence chain.

**D1R12 ledger reconciliation (2026-08-30, Ryan):** Documentation commit
`d2d6f41` prematurely recorded expected PASS before independent review; superseded
by later Kiro independent review + TLC run and now by integrated closure at
`9cfb085836ca92c308d1a8f966aced9bbb48546e`. Formal model at `d2d6f41` byte-identical
to `7a8fd76`; no history repair required.

**D1R1 closure record (2026-08-30):** Subsumed by integrated closure at
`9cfb085836ca92c308d1a8f966aced9bbb48546e`. Prior per-row PASS at `8897d135…`
re-bound at final tip.

**D1R9 closure record (2026-08-30):** Subsumed by integrated closure at
`9cfb085836ca92c308d1a8f966aced9bbb48546e`. Prior per-row PASS at `8897d135…`
re-bound at final tip with tip code on restored reader.

**Corrective rollback drill:** after hermetic first cutover, resolve
`previous_generation_id` as the reference-v2 target, run fresh qualification,
switch the pointer, issue a real serving query, and prove scoring consumed the
exact D0-bound target-reader vectors. Then prove same-pointer recovery does not
switch targets and source advance leaves durable reconciliation-required.

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
| V3a | Source mutation refuses forward promotion | PASS | `tests/test_source_freshness_promotion.py` |
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
| V6c | Rollback uses retained target, not legacy resurrection | **HISTORICAL PASS / REFERENCE-V2 PENDING** | Copied-generation drill passed at `b64860b` but does not prove the corrected physical authority. D1R0–D1R12 globally closed at `9cfb085836ca92c308d1a8f966aced9bbb48546e` (D1R5 same-reader rollback rehearsal PASS); this VERIFY row not re-marked separately. |
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
| V8c | First-owner packet + one-shot activation grant | **PENDING** (not PASS) | **Definition:** Ryan accepts the complete packet and issues the exact one-shot grant. Before grant, packet binds reference-v2 `G_rb` target ID/manifest/evidence-v2/selector/recovery coverage and exact `G_canary` generation ID/manifest, source/pipeline/profile/qualification evidence, and one reviewed implementation/model SHA. **D1R0–D1R12: SATISFIED / PASS** at integrated tip `9cfb085836ca92c308d1a8f966aced9bbb48546e`; corrective V6c row not re-marked. Grant remains one-shot/self-invalidating. **Current state:** not authorized — Ryan GATE separate. |

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

Historical evidence uses `convmem/cg2-design-a-property-map-v2`. Corrective
closure uses `convmem/cg2-design-a-property-map-v3` (`cg2_property_map.py`) at
integrated review tip `9cfb085836ca92c308d1a8f966aced9bbb48546e`. **D1 globally
closed:** D1R0–D1R12 **SATISFIED / PASS** together (Kiro integrated independent
PASS, 2026-08-30). Non-blocking carry-forward: D1R9 scratch materialization
(`production_has_retained_reference_v2 = false`); D1R9 restore-inventory BLOCKED
exit 31 on out-of-scope `decisions-approved.jsonl`; D1R12 jar SHA-attestation
wrapper unattested.

## Evidence log

```text
Design A Execute closure (D7) — mechanical update at b64860b
Design A architecture: 3d8b151907f02c8b8ead89585fb43904840b210b
Superseding execution plan: 9a171bdf03d501ff891d991bbdad6acc1abda56c
D6 accepted tip: 9a042fbc0d18500b91e056f47f60a00e20ccdb75
D7 closure tip: b64860b05575c62b4563c02ed6f05bb39910b4dc
V6c copied-generation drill: HISTORICAL PASS only; reference-v2 D1 globally closed at 9cfb085836ca92c308d1a8f966aced9bbb48546e
D1 integrated closure: ALL D1R0-D1R12 SATISFIED / PASS at 9cfb085836ca92c308d1a8f966aced9bbb48546e (Kiro integrated independent PASS, 2026-08-30; Ryan-delegated ledger write)
D1 integrated evidence: 20/20 reference-v2 pytest; 51/51 regression; manifest /tmp/d1-integrated-evidence-20260830/integrated_d1_evidence_manifest.json
D1 non-blocking caveats: (1) D1R9 production_has_retained_reference_v2=false scratch materialization; (2) D1R9 restore-inventory BLOCKED exit 31 on out-of-scope decisions-approved.jsonl; (3) D1R12 jar SHA-attestation wrapper unattested
D1R12 formal obligation: subsumed by integrated closure; prior PASS at 7a8fd76350b7076f5d75e3ad53c7392647b2eac0 retained in chain
D1R12 ledger reconciliation: d2d6f41 premature record superseded by integrated closure
D1R1 consume-unchanged: subsumed by integrated closure; re-bound at 9cfb085836ca92c308d1a8f966aced9bbb48546e
D1R9 recovery drill: subsumed by integrated closure; re-bound at 9cfb085836ca92c308d1a8f966aced9bbb48546e; restic snapshot 7d9ea1465c129e778ce4787008ac06820bf6f9abc28fd76a9f47fcdd55d2d0e1; target 2740ec5b5f01f2f293d07bbf0677c4e26f8daadefab8192682410e6685af2364; evidence /tmp/d1r9-ra-drill-20260830/evidence/
First-owner packet (V8c): PENDING — provenance reconciled; not PASS
Production activation: NOT PERFORMED
Automatic GC: NOT PERFORMED
```
