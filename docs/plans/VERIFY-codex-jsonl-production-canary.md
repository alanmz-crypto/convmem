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

## T0 baseline hashes (unchanged)

| File | SHA-256 |
|---|---|
| `watch.py` | `b72fd6380d48bf4256371f4b3f4f8eda03f2ca7f1dd9c107f4d6db60c05da2e2` |
| `ingest.py` | `03246a6c104ad9bb6d9c4df9ab9d34bac165080c725ed1545b64aef8f76f6d23` |
| `incremental_jsonl.py` | `e51509c2423db2f2ef5ca414457332aa37d945747b9f7ef8e73a9eb6705db12d` |
| `incremental_jsonl_isolation.py` | `818325221d46b1501795895b82d2465151b12ab76f0f11f21f42d8438c0a6df1` |

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

## TL;DR

P1 hermetic canary harness is on `main` via PR #296 (`907c828`). The P2 transfer
seam is on `main` via PR #299 (`8beda7d`). The P2 runtime-readiness corrective
is on `feat/2026-09-12-codex-jsonl-p2-runtime-readiness` and awaits exact-tip
Kiro review. Live P2 run, grant digest issuance, PR, and activation remain
Ryan-gated.

