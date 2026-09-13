# VERIFY — Arc Codex Kiro JSONL Production Canary (P1)

**Arc:** Codex

**Date:** 2026-09-10

**Lane:** Cursor Execute P1-T0–T8 / P1-A1–A14

**Current location:** `main` via squash-merged PR #296

**Baseline merge:** `b23cabad3a040bb6fef94cc8db8d9f5714b12a46` (PR #295)

**Handoff tip reviewed:** `66235b5b26194f9ee74c19e19863ba00737b8ba4`

**Kiro-reviewed tip:** `7412ce344f5997a454aaab321e7efc6acc5ef1ae`

**Final Kiro-reviewed PR head:** `40b8c119f9fde04cc3b0fcefacc87c802875d9e0`

**P1 merge:** `907c828e738f90db8f7f292ab46db040fec20c70` (PR #296)

---

## Disposition

Hermetic P1 canary-harness evidence is complete and is now on `main`. During
PR CI, the Steward corrected the scoped pylint regression and a sandbox-caught
hermeticity defect: the worker had omitted the architecture's outer,
grant-listed writer lease, so replay's final processed-state transaction tried
the default production writer lock. The correction keeps the outer lease on
the temporary writer lock for the whole coordinator run and binds the grant's
four named lock roles to the actual derived lock paths. Production coordinator,
ingest, watcher, and isolation modules remain unchanged.

The first corrected-tip repo-wide CI run then found that the P1 network test
installed denial in the parent pytest process before launching its already
contained worker. Removing that redundant parent mutation keeps denial inside
the worker and prevents test-order leakage into unrelated JudgeBench tests.
The harness is canary-only, uses synthetic sources and temporary roots only,
and does not touch live production paths, providers, watchers, or the dedicated
Kiro session. Kiro independently rechecked the final PR delta at `40b8c11` and
closed P1 as PASS; all six GitHub checks were green before Ryan squash-merged
PR #296 as `907c828`. P2 and activation remain separately Ryan-gated.

## What this evidence is

| Class | Status |
|---|---|
| P1 grant/boundary/fault/serving/chunking harness | PASS (hermetic) |
| Existing Arc Codex isolation/config/state regressions | PASS |
| C3/R2b writer inventory and census entrypoint binding | PASS (updated) |
| Live source / production corpus / providers / watcher / P2 | **Not run** |
| Repo-wide pytest | **Not run** (explicitly out of grant) |

## T0 baseline hashes (ingest.py intentionally refreshed)

| File | SHA-256 |
|---|---|
| `watch.py` | `b72fd6380d48bf4256371f4b3f4f8eda03f2ca7f1dd9c107f4d6db60c05da2e2` |
| `ingest.py` | `36049bc2cae1b9979fa4becb9e83fcca8cbf0c52a91dd78644f215c2a2742cac` |
| `incremental_jsonl.py` | `e51509c2423db2f2ef5ca414457332aa37d945747b9f7ef8e73a9eb6705db12d` |
| `incremental_jsonl_isolation.py` | `818325221d46b1501795895b82d2465151b12ab76f0f11f21f42d8438c0a6df1` |

`ingest.py` was intentionally rebaselined by the issue #268 bounded export-compaction
implementation. `watch.py` and isolation hashes are unchanged. Default-off and live-denial
behavior is unchanged.

Default-off branches verified: missing/false incremental table, no watcher import
of `incremental_jsonl`, canary launcher not registered in `convmem.py`.

## Exact commands and counts

Working directory: repository root. Interpreter: `/usr/bin/python3` 3.12.
Chroma/pytest from host user site; workers use `python -I` plus
`CONVMEM_INCREMENTAL_SITE`.

### Focused P1 and regression matrix

```bash
python3 -m pytest \
  tests/test_incremental_jsonl_canary_baseline.py \
  tests/test_incremental_jsonl_canary_grant.py \
  tests/test_incremental_jsonl_canary_operations.py \
  tests/test_incremental_jsonl_canary_serving.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_state.py \
  tests/test_shadow_writer_coverage_scan.py \
  tests/test_shadow_writer_gate_c3.py \
  -q
```

Result after the Steward correction: **128 passed** (24 new canary + 104
existing focused regressions).

Out of scope but attempted once for inventory cross-check:
`tests/test_serving_index_repository.py` — 3 cases skipped here because this VM
 lacks optional `sentence_transformers`; not P1 PASS evidence.

### Gates

```bash
python3 -m compileall incremental_jsonl_canary.py scripts/run-jsonl-production-canary.py \
  tests/incremental_jsonl_canary_worker.py tests/incremental_jsonl_canary_helpers.py \
  tests/test_incremental_jsonl_canary_*.py -q
git diff --check
python3 -m pylint incremental_jsonl_canary.py scripts/run-jsonl-production-canary.py \
  tests/incremental_jsonl_canary_worker.py tests/incremental_jsonl_canary_helpers.py \
  tests/test_incremental_jsonl_canary_*.py
```

`compileall`: PASS. `git diff --check`: clean. Scoped pylint on the changed P1
surfaces: **10.00/10**.

## P1 acceptance mapping

| ID | Result | Evidence |
|---|---|---|
| P1-A1 | PASS | `test_p1_a1_isolation_boundary_still_production_denying` |
| P1-A2 | PASS | grant decoder + no-default tests |
| P1-A3 | PASS | digest/expiry/revision/nonce fail-closed tests |
| P1-A4 | PASS | read-only source identity revalidation |
| P1-A5 | PASS | persistent false/false overlay checks |
| P1-A6 | PASS | network denial + credential scrub worker probe |
| P1-A7 | PASS | in-process call-budget guard |
| P1-A8 | PASS | capsule round-trip with unrelated sentinels |
| P1-A9 | PASS | five fault selectors + 44-transition inventory |
| P1-A10 | PASS | process-group termination containment |
| P1-A11 | PASS | serving probe mixed-state + stable reads |
| P1-A12 | PASS | 60/10 frontier reuse + zero-call replay |
| P1-A13 | PASS | CLI/watcher/canary launcher unreachable |
| P1-A14 | PASS | this VERIFY + reproducible commands |

The P1-A2 boundary evidence now also rejects any grant whose writer, source,
export, or processed lock role does not resolve to the lock path the reused
coordinator protocol actually opens.

## Hermetic proof highlights

- Five fault selectors map to `after_summary_upsert`, `after_unit_upsert`,
  `after_units_prune`, `after_checkpoint_publish`, `after_dedupe_reconcile`.
- 61–109 baseline and ≤110 append profiles enforced; 111 rejected.
- Gate 0 treats `systemctl --user is-active` stdout `inactive` as PASS even
  when exit is nonzero.
- No live `.kiro`, production Chroma, config, provider, DNS, or watcher access.

## Governance updates

- Added `incremental_jsonl.apply` to `writer_census.KNOWN_ENTRYPOINTS`.
- Regenerated `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` with route
  `jsonl_production_canary` → `incremental_jsonl_canary.py:canary_coordinator`.

## Independent recheck and merge disposition

Kiro reviewed the full delta from the earlier PASS tip `7412ce3` through final
PR head `40b8c11`, reproduced 128 focused passing tests, compileall,
`git diff --check`, and scoped pylint 10.00/10, and confirmed the writer-lease
and network-denial corrections strengthen isolation without changing the P1
contract. GitHub reported all six required checks green. Ryan then
squash-merged PR #296 as `907c828`.


## P2 corrective (hermetic Execute)

**Arc:** Codex JSONL production canary P2 corrective slice (Execute C0–C4 + Kiro recheck + lint corrections).
**Reviewed handoff:** [`docs/inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-corrective-execute.md`](../inter-model/CODEX-2026-09-11-jsonl-production-canary-p2-corrective-execute.md) at `b83d2a8`.
**Base revision:** `8741774273e968824e4c09f1a7d6bb57729c0d43` (`origin/main` after PR #298).
**Branch:** `feat/2026-09-11-codex-jsonl-p2-corrective`.
**Tip SHA:** `54efdbc99eb1c8fc698dd950d7e682a7e75be896`.

### Scope lock (observed)

- Synthetic Kiro JSONL sources and production-shaped temp paths only.
- P1 production denial, default-off routing, `IsolationBoundary`, normal CLI, and watcher behavior preserved.
- No live frozen source, production Chroma/data, providers/network, config mutation, indexing, watchers, activation, grant digest issuance, live P2, or PR opened.

### Kiro lint/evidence corrections (narrow delta)

| Item | Correction |
|---|---|
| Unused/reimported names | Removed unused imports; dropped lazy `Gate0ProbeHooks` reimport and inner `subprocess` reimport |
| R1714 | Gate 0 capsule digest check uses `not in` membership test |
| Long line / import order | Wrapped launcher subprocess call; moved helper imports above module constants |
| Protected access | Inline `# pylint: disable=protected-access` on intentional ingest/coordinator hooks only |
| Duplicate code | Shared `build_p2_fixture` / `grant_payload_with_resource_path` helpers; import `BASELINE_HASHES` from baseline tests |

### Kiro evidence-gap corrections

| Gap | Correction |
|---|---|
| Twelve Gate 0 checks fail closed individually | `test_p2_gate0_checks_fail_closed_individually` parametrizes all twelve checks |
| Five fault selectors on 61-message two-chunk source | `test_p2_c8_fault_selectors_restore_on_two_chunk_source` parametrizes all `FAULT_SELECTORS` |
| `p2-all` runs T3→T4→T5→T6 in order | `run_p2_orchestration()` executes append + fault battery + evidence freeze; launcher `p2-all` uses `include_faults=True` |
| Disposition derived from outcomes | `derive_p2_disposition()` returns `restored` when all fault observations restore; `converged` when T3+T4 succeed without faults |

### P2 acceptance mapping

| ID | Result | Evidence |
|---|---|---|
| P2-C1 | PASS | `test_p2_c1_p1_still_denies_production_paths` |
| P2-C2 | PASS | `test_p2_c2_positive_mode_binds_exact_resources` |
| P2-C3 | PASS | `test_p2_c3_empty_override_cannot_disable_p1_denial` |
| P2-C4 | PASS | `test_p2_c4_full_gate0_passes_with_stubs` + twelve fail-closed parametrized cases |
| P2-C5 | PASS | `test_p2_c5_launcher_refuses_p1_mutation` |
| P2-C6 | PASS | `test_p2_c6_initial_adoption_two_chunk_replay` |
| P2-C7 | PASS | `test_p2_c7_append_reuses_chunk_zero` |
| P2-C8 | PASS | five-selector parametrized fault restore on 61-message source |
| P2-C9 | PASS | `test_p2_c9_evidence_freeze` + orchestration evidence bundle |
| P2-C10 | PASS | `test_p2_c10_baseline_hashes_and_routes_unchanged` |
| P2-C11 | PASS | `test_p2_c11_unrelated_sentinels_unchanged` |
| P2-C12 | PASS | `test_p2_c12_nonce_receipt_one_run` |
| P2-C13 | PASS | focused P1 matrix still green (158 passed with P2 suite) |

### Exact commands and counts

```bash
python3 -m pytest \
  tests/test_incremental_jsonl_canary_baseline.py \
  tests/test_incremental_jsonl_canary_grant.py \
  tests/test_incremental_jsonl_canary_operations.py \
  tests/test_incremental_jsonl_canary_serving.py \
  tests/test_incremental_jsonl_canary_p2_corrective.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_state.py \
  tests/test_shadow_writer_coverage_scan.py \
  tests/test_shadow_writer_gate_c3.py \
  -q
```

Result: **158 passed** (128 focused P1/regression + 30 P2 corrective).

```bash
python3 -m compileall incremental_jsonl_canary.py scripts/run-jsonl-production-canary.py \
  tests/incremental_jsonl_canary_worker.py tests/incremental_jsonl_canary_helpers.py \
  tests/test_incremental_jsonl_canary_*.py -q
git diff --check
python3 -m pylint incremental_jsonl_canary.py scripts/run-jsonl-production-canary.py \
  tests/incremental_jsonl_canary_worker.py tests/incremental_jsonl_canary_helpers.py \
  tests/test_incremental_jsonl_canary_*.py
set +e
pylint $(git ls-files "*.py") --output-format=json > pylint-report.json
pylint_status=$?
set -e
python3 scripts/pylint_regression_gate.py ci \
  --report pylint-report.json \
  --pylint-status "$pylint_status" \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref origin/main
```

`compileall`: PASS. `git diff --check`: clean. Scoped pylint (`pylint==4.0.6`) on touched surfaces: **10.00/10**. `pylint_regression_gate.py ci`: **PASS** (459 findings, 243 fingerprints; no new/increased vs baseline).

### Stop state

Pushed feature tip `54efdbc99eb1c8fc698dd950d7e682a7e75be896` ready for Kiro narrow delta recheck. Live P2 run, grant digest issuance, PR, and activation remain Ryan-gated separately.

## P2 runtime-readiness corrective (C0–C7)

**Who:** Cursor Execute on `feat/2026-09-12-codex-jsonl-p2-runtime-readiness`, implementing the packet Kiro PASSed at `a2560b4db0faebe136b62ce9a8b874e70c74f86a`.

**What:** A live-safe exact-resource P2 runtime: versioned `p2-exact-resource-v2` grants, side-effect-free Gate 0, separately authorized preparation, a production-owned worker, one-stage transitions, and distinct live evidence.

**When:** 2026-09-12, branched from `origin/main` `7360a04e1e8154eca76eddf72c492251ae830c0f`.

**Why:** Merged P2 at `7360a04` could mutate during nominal preflight, treat stubbed backup/model checks as PASS, import test fakes on the live path, rewrite the source, and restore a post-fault image.

**How:** C0–C7 landed in implementation commit `ca88d540819b8d91684d397426511a0028bbcc10`. This evidence commit is the exact tip for Kiro review.

### Negative confirmation

No live source, production Chroma, processed/export/locks, provider/network call, watcher start/stop, config edit, indexing, Gate 0 against live resources, live P2 run, replacement grant/digest, PR, or activation occurred.

### Commands and counts

```bash
python3 -m pytest \
  tests/test_incremental_jsonl_canary_baseline.py \
  tests/test_incremental_jsonl_canary_grant.py \
  tests/test_incremental_jsonl_canary_operations.py \
  tests/test_incremental_jsonl_canary_serving.py \
  tests/test_incremental_jsonl_canary_p2_corrective.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_state.py \
  -q
```

Result: **165 passed** (128 focused P1/P2-corrective + 37 runtime-readiness).

```bash
python3 -m compileall -q incremental_jsonl_canary.py incremental_jsonl_canary_p2.py \
  incremental_jsonl_canary_live_worker.py chroma_readonly.py \
  scripts/run-jsonl-production-canary.py \
  tests/incremental_jsonl_canary_helpers.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py
git diff --check
python3 -m pylint --score=n incremental_jsonl_canary.py incremental_jsonl_canary_p2.py \
  incremental_jsonl_canary_live_worker.py chroma_readonly.py \
  scripts/run-jsonl-production-canary.py \
  tests/incremental_jsonl_canary_helpers.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py
```

`compileall`: PASS. `git diff --check`: clean. Scoped pylint: **10.00/10**.

### C0 baseline

Unchanged hashes from `7360a04`:

| File | SHA-256 |
|---|---|
| `watch.py` | `b72fd6380d48bf4256371f4b3f4f8eda03f2ca7f1dd9c107f4d6db60c05da2e2` |
| `ingest.py` | `03246a6c104ad9bb6d9c4df9ab9d34bac165080c725ed1545b64aef8f76f6d23` |
| `incremental_jsonl.py` | `e51509c2423db2f2ef5ca414457332aa37d945747b9f7ef8e73a9eb6705db12d` |
| `incremental_jsonl_isolation.py` | `818325221d46b1501795895b82d2465151b12ab76f0f11f21f42d8438c0a6df1` |

### Mapping

| ID | Result | Evidence |
|---|---|---|
| C0 | PASS | Baseline hashes unchanged; focused P1/P2 matrix green after the launcher P1-mutation check no longer depends on a live watcher |
| C1 | PASS | `p2-exact-resource-v2` binds persistent config, full model manifests, restic, and identities; v1 is not live-capable |
| C2 | PASS | Gate 0 writes nothing; twelve checks fail closed; restic stubs cannot PASS; no `systemctl start`; SQLite `mode=ro` |
| C3 | PASS | `prepare_live_p2` captures a non-zero capsule before T3 |
| C4 | PASS | Live module/worker/launcher AST has no `tests`/`pytest`/`install_fakes`; hermetic mode cannot select real providers |
| C5 | PASS | `p2-all` refused; 68-message case does not append 49; live helpers refuse source writes; stage-order/tamper/cap+1/descendant cases |
| C6 | PASS | Live evidence uses `p2-exact-resource-live-evidence.json` and `hermetic: false` |
| C7 | PASS | This section; stop for exact-tip Kiro review |

Candidate digest `c002385ee2e72e319ddcce2ab5d024c29abbe0031b86cbb26468cb604ee8c621` remains unauthorized and must not be reused after this runtime change.

## P2 live-safety corrective (Claude FAIL follow-up)

**Who:** Cursor Execute on `feat/2026-09-12-codex-jsonl-p2-runtime-readiness`, addressing local Claude Opus 5 FAIL at preserved `5bdc132950969c9f4473b182f47816d68ccde8e8`.

**What:** Make the exact-resource P2 canary live-safe and incapable of emitting false recovery or convergence evidence.

**When:** 2026-09-12, additive commits on the same branch. Failed reviewed revision `5bdc132` was not amended, rebased, or rewritten.

**Why:** Claude blocked B1–B8 (evidence authority, hardcoded restore, crash-self faults, incomplete rollback, source chmod, capsule-after-mutation, missing serving visibility, out-of-order faults) plus safety-relevant N1, N3–N7, N9, and N13.

**How:** Implementation commit `9969a38c485736e26cd1bcb27ee33ef8d2505aae`. This evidence commit is the exact tip for local Claude re-review. Do not route to Kiro.

### Negative confirmation

No live source, production Chroma, processed/export/locks, provider/network call, watcher start/stop, config edit, indexing, Gate 0 against live resources, live P2 run, replacement grant/digest, PR, merge, or activation occurred. No systemd operation. Worktree remained hermetic.

### Commands and counts

```bash
python3 -m pytest \
  tests/test_incremental_jsonl_canary_baseline.py \
  tests/test_incremental_jsonl_canary_grant.py \
  tests/test_incremental_jsonl_canary_operations.py \
  tests/test_incremental_jsonl_canary_serving.py \
  tests/test_incremental_jsonl_canary_p2_corrective.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_state.py \
  -q
```

Result: **184 passed** (165 prior focused suite + 19 live-safety regressions). Runtime-readiness file: 54 collected.

```bash
python3 -m compileall -q incremental_jsonl.py incremental_jsonl_canary.py \
  incremental_jsonl_canary_p2.py incremental_jsonl_canary_live_worker.py \
  incremental_jsonl_canary_network.py chroma_readonly.py \
  scripts/run-jsonl-production-canary.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py \
  tests/test_incremental_jsonl_state.py
git diff --check
python3 -m pylint incremental_jsonl.py incremental_jsonl_canary.py \
  incremental_jsonl_canary_p2.py incremental_jsonl_canary_live_worker.py \
  incremental_jsonl_canary_network.py scripts/run-jsonl-production-canary.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py \
  tests/test_incremental_jsonl_state.py
python3 -m pylint $(git ls-files "*.py") --output-format=json > pylint-report.json
python3 scripts/pylint_regression_gate.py ci \
  --report pylint-report.json \
  --pylint-status 30 \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref origin/main
```

`compileall`: PASS. `git diff --check`: clean. Scoped pylint: **10.00/10**. `pylint_regression_gate.py ci`: **PASS** (457 findings, 243 fingerprints; no new/increased vs `origin/main` `7360a04`).

### C0 baseline

Watch, ingest, and isolation hashes are unchanged from `7360a04`. `incremental_jsonl.py` changed **rollback capture/restore only** (processed preimage, checkpoint/transaction/state, prepared, and dedupe files) with normal-path regression `test_restore_rewinds_processed_checkpoint_and_state`.

| File | SHA-256 |
|---|---|
| `watch.py` | `b72fd6380d48bf4256371f4b3f4f8eda03f2ca7f1dd9c107f4d6db60c05da2e2` |
| `ingest.py` | `03246a6c104ad9bb6d9c4df9ab9d34bac165080c725ed1545b64aef8f76f6d23` |
| `incremental_jsonl.py` | `805c4f5d3871a42e8f4894263462b15181541a6c1be775c2935c7698187da1d0` |
| `incremental_jsonl_isolation.py` | `818325221d46b1501795895b82d2465151b12ab76f0f11f21f42d8438c0a6df1` |

### Claude blocker mapping

| ID | Result | Evidence |
|---|---|---|
| B1 | PASS | `test_b1_freeze_requires_t6_and_five_faults`, `test_b1_freeze_derives_disposition` — T6 stage, five distinct faults, append receipts, derived disposition |
| B2 | PASS | `test_b2_mismatch_is_recovery_unproven`, `test_b2_caller_disposition_cannot_override` — post-restore capsule compare; caller cannot select `restored` |
| B3 | PASS | `test_b3_crash_self_is_not_fault_evidence`, `test_c5_pre_fault_capsule_and_descendants` — child runs `t5-fault` with `CONVMEM_CANARY_FAULT`; `crash-self` refused; exit 86 |
| B4 | PASS | `test_b4_restore_rewinds_checkpoint_after_tamper`, `test_restore_rewinds_processed_checkpoint_and_state` — processed/checkpoint/state/dedupe restore |
| B5 | PASS | `test_b5_prepare_does_not_chmod_source` — source JSONL and `session.json` keep mode 0o644, inode, and timestamps |
| B6 | PASS | `test_b6_capsule_exists_before_overlay_mutation` — capsule persisted before overlay/census writes |
| B7 | PASS | `test_c3_prepare_and_t3_two_chunk` (≥3 samples), `test_b7_serving_visibility_fails_closed_without_probe` — concurrent probe; missing visibility fails closed |
| B8 | PASS | `test_b8_out_of_order_fault_is_refused` — exact `next_stage == FAULT_STAGE[selector]` |

### Safety-relevant N-finding mapping

| ID | Result | Evidence |
|---|---|---|
| N1 | PASS | `test_n1_network_denial_is_policy_specific` — loopback allowed; TEST-NET denied before socket via `install_p2_network_policy` |
| N3 | PASS | `test_n3_grant_bound_identities_are_validated` — overlay/evidence/capsule/persistent_config identities |
| N4 | PASS | `test_n4_writer_census_is_non_creating` — `LOCK_SH\|LOCK_NB`; no create/mtime change |
| N5 | PASS | `test_n5_grandchild_is_absent_after_exit` — `/proc` pgid scan; process group absent after exit |
| N6 | PASS | `test_n6_non_crash_exit_is_refused` — exact `CRASH_EXIT` (86) required |
| N7 | PASS | `test_n7_unrelated_manifest_is_derived` — derived unrelated-source manifest; empty default is not proof |
| N9 | PASS | `test_n9_production_probes_run_real_code` — production defaults exercised; not replaced by `live_gate0_hooks_pass()` |
| N13 | PASS | `test_n13_directory_role_does_not_grant_subtree` — directory roles do not grant uncontrolled subtrees |

### Stop state

Pushed feature tip `a47f32b8a80f5b8c612078835cff23db3da7e897` was the live-safety
evidence commit. Local Claude re-review returned FAIL (R1–R4). That SHA is
preserved.

## P2 R1–R4 sequence-completeness corrective

**Who:** Cursor Execute on `feat/2026-09-12-codex-jsonl-p2-runtime-readiness`, addressing local Claude FAIL at preserved `a47f32b8a80f5b8c612078835cff23db3da7e897`.

**What:** Make the documented live sequence completable with genuine `restored` evidence: bounded embedding fidelity, no invalid zero-call replay, stage-aware Gate 0, and an explicit T5 append-bind stage.

**When:** 2026-09-12, additive commits on the same branch. Failed reviewed revision `a47f32b` was not amended, rebased, or rewritten.

**Why:** Chroma restore changes embeddings by one float32 ULP so exact capsule equality could never pass; the `restored` branch then raised; Gate 0 still required pre-prepare absence; T5 had no shipped append-binding caller.

**How:** Implementation commit `f7bcdffb167696f4124dc844b99d4781919da6b1`. This evidence commit is the exact tip for local Claude re-review. Do not route to Kiro.

Bit-exact Chroma restore was not possible: writing a captured float32 embedding through `restore_source_rows` still lands one ULP away. Recovery therefore compares IDs, documents, metadata, state digests, and unrelated manifests exactly, and embeddings within **1 float32 ULP**. Adversarial 2-ULP / id / document / metadata / digest mismatches remain `recovery_unproven`.

Tightly coupled R3 extras (required for later-stage Gate 0 to be applicable at all): previously-absent resource roles may exist after prepare; source size/prefix checks allow a verified append after T3; zero-adoption is skipped after prepare. R5–R8 were not expanded.

### Negative confirmation

No live source, production Chroma, processed/export/locks, provider/network call, watcher start/stop, config edit, indexing, Gate 0 against live resources, live P2 run, replacement grant/digest, PR, merge, or activation occurred. No systemd operation. Worktree remained hermetic.

### Commands and counts

```bash
python3 -m pytest \
  tests/test_incremental_jsonl_canary_baseline.py \
  tests/test_incremental_jsonl_canary_grant.py \
  tests/test_incremental_jsonl_canary_operations.py \
  tests/test_incremental_jsonl_canary_serving.py \
  tests/test_incremental_jsonl_canary_p2_corrective.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_state.py \
  -q
```

Result: **190 passed** (184 prior focused suite + 6 R1–R4 regressions). Runtime-readiness file: 60 collected.

```bash
python3 -m compileall -q incremental_jsonl_canary_p2.py \
  incremental_jsonl_canary_live_worker.py \
  scripts/run-jsonl-production-canary.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py
git diff --check
python3 -m pylint incremental_jsonl_canary_p2.py \
  incremental_jsonl_canary_live_worker.py \
  scripts/run-jsonl-production-canary.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py
python3 -m pylint $(git ls-files "*.py") --output-format=json > pylint-report.json
python3 scripts/pylint_regression_gate.py ci \
  --report pylint-report.json \
  --pylint-status 30 \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref origin/main
```

`compileall`: PASS. `git diff --check`: clean. Scoped pylint: **10.00/10**. `pylint_regression_gate.py ci`: **PASS** (459 findings, 243 fingerprints; no new/increased vs `origin/main` `7360a04`).

### Mapping

| ID | Result | Evidence |
|---|---|---|
| R1 | PASS | `test_r1_one_ulp_embedding_is_restored`, `test_r1_adversarial_mismatches_stay_unproven`, `test_r2_restored_path_does_not_claim_zero_replay` — genuine `restored`; 2-ULP/id/document/metadata/digest mismatches stay `recovery_unproven` |
| R2 | PASS | `test_r2_restored_path_does_not_claim_zero_replay` — restored path does not call `_replay_zero`; `replay_outcome` is None |
| R3 | PASS | `test_r3_gate0_passes_after_prepare_and_fails_on_mutation` — Gate 0 passes after prepare; capsule digest and overlay identity mutations fail closed |
| R4 | PASS | `test_r4_launcher_bind_stage_is_separately_invoked`, `test_r4_documented_sequence_prepare_through_t6` — `t5-bind-append` / `t5-bind`; full prepare→T3→append→T4→bind→five T5 faults→T6 freeze without hand-edited receipts; proves **at least one** `restored`, not all five; `p2-all` still refused |

### Stop state

Pushed feature tip `4acb4c54fe0b332a73cc6c5dea343d6391527806` was the R1–R4
evidence commit. Kiro returned CONDITIONAL PASS (C1–C4). That SHA is preserved.

## P2 C1–C4 Kiro-condition corrective

**Who:** Cursor Execute on `feat/2026-09-12-codex-jsonl-p2-runtime-readiness`, addressing Kiro CONDITIONAL PASS at preserved `4acb4c54fe0b332a73cc6c5dea343d6391527806`.

**What:** Close four review conditions so the exact-resource P2 runtime can receive an unconditional exact-tip PASS: honest restoration claims, eliminate `converged`, freeze serving timeline/durations, and route dedupe restore through the granted role.

**When:** 2026-09-12, additive commits on the same branch. Conditional-PASS revision `4acb4c5` was not amended, rebased, or rewritten.

**Why:** The suite does not prove all five faults restore; freeze still had an unreachable `converged` branch; frozen evidence omitted the serving-read timeline required by Architecture §11 and EXECUTION P2-T6; dedupe capture/restore used `chroma_dir.parent` without an exact-role check.

**How:** Implementation commit `bd02a4f81da6076fd64c465e4a874a5174429e39`. This evidence commit is the exact tip for Kiro recheck. No Claude re-review.

Honest restoration contract: the hermetic documented sequence proves **at least one** of the five faults yields `restored`. Other faults may yield fail-closed `recovery_unproven`. Freeze derives `restored` only when every observed fault restored; mixed or all-unproven observations derive `recovery_unproven`. This VERIFY does **not** claim all five restore.

Implemented live disposition contract is `restored | recovery_unproven`. The unreachable `converged` freeze branch is removed; recording `converged` as an observed disposition fails closed.

Serving evidence: T3, T4, and each T5 fault record a bounded serving-read timeline (≤32 samples/stage) plus mixed/recovery durations derived from those samples. Freeze refuses missing or malformed timelines.

Dedupe C4: capture/restore resolve the granted `dedupe` role through `boundary.resolve_mutable` and refuse a chroma-derived location that is not that exact role **before** any write or chmod. Watch/ingest/isolation hashes are unchanged. `incremental_jsonl.py` hash is `048a895394629f55fa2c2b0af2f00c9844a9038268899a85eadd97c7d4d88cfe` because C4 changed only that rollback path.

### Negative confirmation

No live source, production Chroma, processed/export/locks, provider/network call, watcher start/stop, config edit, indexing, Gate 0 against live resources, live P2 run, replacement grant/digest, PR, merge, or activation occurred. No systemd operation. Worktree remained hermetic.

### Commands and counts

```bash
python3 -m pytest \
  tests/test_incremental_jsonl_canary_baseline.py \
  tests/test_incremental_jsonl_canary_grant.py \
  tests/test_incremental_jsonl_canary_operations.py \
  tests/test_incremental_jsonl_canary_serving.py \
  tests/test_incremental_jsonl_canary_p2_corrective.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py \
  tests/test_incremental_jsonl_config.py \
  tests/test_incremental_jsonl_isolation.py \
  tests/test_incremental_jsonl_state.py \
  -q
```

Result: **196 passed** (190 prior focused suite + 6 C1–C4 regressions).

```bash
python3 -m compileall -q incremental_jsonl.py incremental_jsonl_canary_p2.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py \
  tests/test_incremental_jsonl_state.py \
  tests/test_incremental_jsonl_canary_baseline.py
git diff --check
python3 -m pylint incremental_jsonl.py incremental_jsonl_canary_p2.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py \
  tests/test_incremental_jsonl_state.py \
  tests/test_incremental_jsonl_canary_baseline.py
python3 -m pylint $(git ls-files "*.py") --output-format=json > pylint-report.json
python3 scripts/pylint_regression_gate.py ci \
  --report pylint-report.json \
  --pylint-status 30 \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref origin/main
```

`compileall`: PASS. `git diff --check`: clean. Scoped pylint: **10.00/10**. `pylint_regression_gate.py ci`: **PASS** (459 findings, 243 fingerprints; no new/increased vs `origin/main` `7360a04`).

### Mapping

| ID | Result | Evidence |
|---|---|---|
| C1 | PASS | VERIFY/STATUS state at least one fault `restored`; other faults may be `recovery_unproven`; `test_r4_documented_sequence_prepare_through_t6` asserts `"restored" in dispositions` and does not require all five |
| C2 | PASS | `test_c2_converged_disposition_is_refused` — live freeze contract is `restored \| recovery_unproven`; `converged` is refused |
| C3 | PASS | `test_r4_documented_sequence_prepare_through_t6`, `test_b1_freeze_derives_disposition`, `test_c3_missing_timeline_fails_closed`, `test_c3_malformed_timeline_fails_closed` — frozen evidence carries bounded serving timeline and derived mixed/recovery durations; missing/malformed fail closed |
| C4 | PASS | `test_c4_dedupe_outside_granted_role_refused_before_mutation`, `test_c4_isolation_dedupe_outside_role_refused_before_chmod`, `test_c4_valid_exact_role_restore_still_succeeds`, `test_restore_rewinds_processed_checkpoint_and_state` — out-of-role refused before write/chmod; granted-role restore still succeeds |

### Stop state

Pushed feature tip after this evidence commit was ready for Kiro targeted
exact-tip recheck. Repo-wide CI then failed on overlay-inode reuse and stale
writer inventory. That CI corrective is recorded below.

## P2 CI overlay-digest and writer-inventory corrective

**Who:** Cursor Execute on `feat/2026-09-12-codex-jsonl-p2-runtime-readiness`
and existing PR #301.

**What:** Close the two root causes from GitHub pytest job `103563853581`
(run `34697675401`): Gate 0 overlay content was not bound, and the governed
writer inventory drifted.

**When:** 2026-09-12, additive commits after Kiro PASS at preserved
`6cb01076a3c57420d07c2b89bb6df9d4ba1659c8`. That revision was not amended,
rebased, or rewritten.

**Why:** `_identity_matches` checked type/uid/mode/device/inode only. CI reused
the inode after unlink/rewrite, so changed overlay bytes passed Gate 0.
`jsonl_production_canary` still listed `incremental_jsonl_canary.py:1001` after
the constructor moved to `:1234`, and the shadow session site still listed
`incremental_jsonl.py:500` after the call moved to `:501`. Committed R2b
implementation identity `0ad658b…` no longer matched regenerated `ba7cba8…`.

**How:** Gate 0 now hashes overlay bytes against `grant.config_overlay_digest`
before prepare and against a durable `overlay_digest` on the stage receipt
after prepare, while keeping owner/mode/device/inode and symlink checks.
Source-owned route/shadow sink declarations were updated, then
`docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` was regenerated with
`write_v2_inventory_file()` (implementation identity
`e9a4fca8c2d18eb166e7e3d65a201d26611a0b2a`). No generated revision was
hand-edited.

Implementation commits:
`bce855c81a183d1758fb822b4381c2706a035944` (overlay digest) and
`3582060765b0dde79cb09018d6fd6cca800c7556` (inventory). This evidence commit
is the exact tip for Kiro recheck. No Claude re-review. No new PR.

### Negative confirmation

No live source, production Chroma, processed/export/locks, provider/network
call, watcher start/stop, config edit, indexing, Gate 0 against live
resources, live P2 run, replacement grant/digest, new PR, merge, or
activation occurred. No systemd operation. Worktree remained hermetic.

### Commands and counts

```bash
python3 -m pytest \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py::test_n3_grant_bound_identities_are_validated \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py::test_n3_in_place_same_size_overlay_mutation_fails_closed \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py::test_n3_overlay_replacement_fails_closed_without_inode \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py::test_r3_gate0_passes_after_prepare_and_fails_on_mutation \
  tests/test_r2b_v2_coverage.py \
  tests/test_r2b_v2_implementation_revision.py \
  tests/test_r2b_v2_corrective_viii.py \
  tests/test_shadow_writer_coverage_scan.py \
  tests/test_r2b_v2_authority_boundary.py \
  tests/test_r2b_v2_authority_boundary_ii.py \
  tests/test_r2b_v2_authority_boundary_iii.py \
  tests/test_r2b_v2_authority_boundary_iv.py \
  tests/test_r2b_v2_authority_boundary_v.py \
  tests/test_r2b_v2_lease.py \
  -q
```

Focused Gate 0 + R2b/authority/inventory result: **PASS** (124 tests in the
combined focused run; the two original Gate 0 failures plus two new
inode-independent overlay tests).

CI-equivalent repo-wide suite (same as `.github/workflows/pylint.yml`):

```bash
export CONVMEM_CONFIG=/tmp/convmem-ci/config.toml
export GITHUB_ACTIONS=true
python -m pytest -q
```

Local result: **2362 passed, 64 skipped, 0 failed**, 228 subtests passed in
1196.50s.

GitHub pytest on implementation tip `35820607…` (run `34700444152`, job
`103571135172`): **2362 passed, 64 skipped, 8 warnings, 228 subtests passed**
in 1583.21s. `pylint (3.12)` **PASS**. Prior failing job `103563853581` was
50 failed / 2310 passed / 64 skipped.

```bash
python3 -m compileall -q incremental_jsonl_canary_p2.py \
  eval_corpus/r2b_v2/coverage/inventory.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py
git diff --check
python3 -m pylint incremental_jsonl_canary_p2.py \
  eval_corpus/r2b_v2/coverage/inventory.py \
  tests/test_incremental_jsonl_canary_p2_runtime_readiness.py
python3 -m pylint $(git ls-files "*.py") --output-format=json > pylint-report.json
python3 scripts/pylint_regression_gate.py ci \
  --report pylint-report.json \
  --pylint-status 30 \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref origin/main
```

`compileall`: PASS. `git diff --check`: clean. Scoped pylint: **10.00/10**.
`pylint_regression_gate.py ci`: **PASS** (460 findings, 243 fingerprints; no
new/increased vs `origin/main` `7360a04`).

### Mapping

| ID | Result | Evidence |
|---|---|---|
| Gate 0 overlay integrity | PASS | Pre-prepare checks `grant.config_overlay_digest`; post-prepare records and checks receipt `overlay_digest`; owner/mode/device/inode/symlink checks remain. `test_n3_in_place_same_size_overlay_mutation_fails_closed` and `test_n3_overlay_replacement_fails_closed_without_inode` do not depend on inode allocation. `test_r3_gate0_passes_after_prepare_and_fails_on_mutation` covers in-place and replacement after prepare. Mode mismatch still refuses `canary_gate0_paths`. |
| Writer inventory | PASS | Source-owned `jsonl_production_canary` sink is `incremental_jsonl_canary.py:1234`; shadow session site is `incremental_jsonl.py:501`. Regenerated inventory identity `e9a4fca8c2d18eb166e7e3d65a201d26611a0b2a`. R2b coverage, authority, implementation-revision, and Shadow scan tests PASS. |
| Repo-wide pytest | PASS | Local CI-equivalent **2362 passed, 64 skipped, 0 failed**. GitHub job `103571135172` **2362 passed, 64 skipped**. |

### Hashes

| File | SHA-256 |
|---|---|
| `incremental_jsonl_canary_p2.py` | `8125ee0c43df0a928ca01189d149ff333bac10127a2692882da5ec841ae09aee` |
| `incremental_jsonl.py` | `048a895394629f55fa2c2b0af2f00c9844a9038268899a85eadd97c7d4d88cfe` |
| `eval_corpus/r2b_v2/coverage/inventory.py` | `cbe95692850c2ddac7e4b459f006a06a5074b0f81800a67f42ab178e7533685a` |

`incremental_jsonl.py` hash is unchanged from the C4 tip. Overlay integrity
changed only `incremental_jsonl_canary_p2.py`.

Compare from preserved ancestor:
https://github.com/alanmz-crypto/convmem/compare/6cb01076a3c57420d07c2b89bb6df9d4ba1659c8...feat/2026-09-12-codex-jsonl-p2-runtime-readiness

### Stop state

Pushed feature tip after this evidence commit is ready for **Kiro targeted
exact-tip recheck**. No Claude re-review. Existing PR #301; no new PR. Live
P2 run, grant digest issuance, merge, and activation remain Ryan-gated
separately.

## TL;DR

P1 hermetic canary harness is on `main` via PR #296 (`907c828`). The P2 transfer
seam is on `main` via PR #299 (`8beda7d`). Preserved Claude FAILs: runtime-readiness
`5bdc132` and live-safety `a47f32b`. Kiro CONDITIONAL PASS at preserved `4acb4c5`.
C1–C4 Kiro PASS at preserved `6cb0107`. Repo-wide CI then failed; the overlay-
digest and writer-inventory corrective is on
`feat/2026-09-12-codex-jsonl-p2-runtime-readiness` / PR #301 and awaits Kiro
exact-tip recheck. Repo-wide pytest is **2362 passed, 64 skipped, 0 failed**.
Live P2 run, grant digest issuance, merge, and activation remain Ryan-gated.

