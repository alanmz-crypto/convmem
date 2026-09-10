# VERIFY — Arc Codex Kiro JSONL Production Canary (P1)

**Arc:** Codex

**Date:** 2026-09-10

**Lane:** Cursor Execute P1-T0–T8 / P1-A1–A14

**Branch:** `feat/2026-09-10-codex-jsonl-production-canary-p1`

**Baseline merge:** `b23cabad3a040bb6fef94cc8db8d9f5714b12a46` (PR #295)

**Handoff tip reviewed:** `66235b5b26194f9ee74c19e19863ba00737b8ba4`

**Kiro correction:** import `Iterable` in `incremental_jsonl_canary.py` (required
typing fix for `assert_transition_coverage`).

**Corrected tip:** `a70101f28f567e05b3ee4fc3735ad21d97868014`

**PR:** not opened; Ryan/Kiro exact-tip review is next

---

## Disposition

Hermetic P1 canary-harness evidence is complete on the feature branch.
The harness is canary-only, uses synthetic sources and temporary roots only,
and does not touch live production paths, providers, watchers, or the dedicated
Kiro session. P2, PR creation, and activation remain separately Ryan-gated.

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

Result: **127 passed** (23 new canary + 104 existing focused regressions).

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

`compileall`: PASS. `git diff --check`: clean. Scoped pylint on new surfaces:
**9.69/10** (post-`Iterable` import correction).

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

## Kiro rerun

```bash
git fetch origin feat/2026-09-10-codex-jsonl-production-canary-p1
git rev-parse origin/feat/2026-09-10-codex-jsonl-production-canary-p1
```

Re-run the focused pytest command above from the exact tip. Do not run bare
`pytest -q` or perform P2/live operations.

## TL;DR

P1 hermetic canary harness evidence is pushed on
`feat/2026-09-10-codex-jsonl-production-canary-p1` for exact-tip Kiro review.
P2, PR creation, and activation remain unauthorized.
