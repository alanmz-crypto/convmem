# EXECUTION — Bound the standing exposure-window probe

**Arc:** Trapdoor Hunt (issue #268 operational follow-up; does not reopen the
closed provenance T3 gate)

**Status:** IMPLEMENTED (corrective) — Cursor Execute C0–C7 on branch
`fix/2026-09-16-watch-oom-bound-exposure-probe-corrective`; awaiting GitHub
Copilot targeted safety/evidence re-audit (no PR opened; not yet Kiro-ready).

**Date:** 2026-09-14

## 1. Consequence for Ryan

PR #303 made the main brief aggregation memory-bounded, but the same brief
still asks the standing-register exposure-window probe to construct a full
`ReadonlyUnitStore`. That hidden call reads every metadata value, including
duplicated `provenance_envelope` strings, before a small watched transcript can
finish indexing.

The narrow correction makes only that probe consume the projected streaming
iterator already merged by PR #303. It retains the small ledger relation graph
needed to preserve exposure-window semantics, but it never requests documents,
provenance payloads, or non-ledger metadata. It does not change the standing
register, evidence-status rules, brief schema, ingestion, watcher policy, or
Arc Codex P2.

## 2. Evidence and diagnosis

PR #303 squash-merged as
`5c103aa2f11f54de74be3a7eab90c433c0c019cd`. Its tree exactly matches the
Copilot- and Kiro-PASSed implementation tip
`814e2d680360b67c03c805feb0e8c9c739d873d7`, and all required CI checks passed.

A post-merge hermetic comparison used the real `ingest.index(force_file=...)`
control flow with synthetic transcripts, temporary Chroma/config/export/state,
fake providers, network denial, production-path denial, an 8 GiB address-space
ceiling, and a 4 GiB RSS watchdog. All 32 runs completed without a denial or
watchdog kill. At 58,825 synthetic units, PR #303 reduced the measured combined
peak from about 2,682 MiB to 1,275 MiB, proving that the projected brief reader
works but that another corpus-sized reader remains.

The residual was isolated at 20,000 units:

| Path | 2 KiB envelopes | 32 KiB envelopes |
|---|---:|---:|
| Exposure probe alone | 100.1 MiB over import | 423.4 MiB over import |
| Brief with probe disabled | 20.9 MiB over import | 20.6 MiB over import |
| Full brief | 100.8 MiB over import | 423.8 MiB over import |

The exposure probe accounts for 423 of 424 MiB of the remaining envelope-size
sensitivity. The exact active call chain is:

```text
brief.write_brief
  -> brief.gather_brief_data
  -> doctor.standing_register_status
  -> doctor._evaluate_standing_rows
  -> doctor._standing_row_due
  -> doctor._exposure_window_probe
  -> chroma_readonly.open_readonly_unit_store
  -> ReadonlyUnitStore.__init__
  -> collection_metadata_rows   # unprojected full-list read
```

The merged projected iterator itself changed by only about 0.6 MiB when the
synthetic envelope grew from 2 KiB to 32 KiB. The remaining allocation is
therefore not a defect in the iterator or the PR #303 brief aggregate; it is a
separate caller left outside that slice.

The hermetic harness peaked near 1.6 GiB rather than reproducing the observed
flat 12.5 GiB watcher OOM. This correction removes the last demonstrated
envelope-sized reader on the measured brief path. It does not claim to explain
or close the entire live OOM.

## 3. Scope lock

### In scope

- Replace `_exposure_window_probe()`'s `ReadonlyUnitStore` construction with
  `iter_collection_metadata_rows()` using one exact scalar projection.
- Preserve the current `build_ledger_index()` relation semantics by using the
  already-merged non-caching `build_ledger_index_from_metadata()` helper.
- Preserve the current scalar `superseded is True` exclusion and do not add a
  `deleted` rule.
- Preserve every current exposure-window due/not-due decision and detail
  string, including duplicate-ledger and timestamp fallback behavior.
- Prove iterator cleanup, read-only behavior, standing-register fail-soft
  behavior, projection closure, and bounded memory hermetically.
- Refresh only code-derived inventories or baseline hashes that actually drift.

### Out of scope

- Changes to the PR #303 brief aggregate or its 19-field projection.
- Changes to `evidence_boost()`, `OPEN_STATUSES`, ledger relation semantics, or
  standing-register policy/data.
- Provenance storage normalization, envelope migration, commitments, or source
  authority.
- Changes to the public `collection_metadata_rows()` compatibility API or
  `ReadonlyUnitStore` behavior for other callers.
- Changes to ingestion, export compaction, Chroma/HNSW construction, providers,
  OpenBLAS/thread settings, memory caps, watcher timeout/debounce/cooldown, or
  exclusions.
- Production profiling, live Chroma/brief/indexing, source re-inclusion,
  watcher/systemd operation, or configuration changes.
- Arc Codex Gate 0, P2 packet/grant/digest work, live P2, or activation.

## 4. Existing observable contract

On the same stable corpus snapshot and standing-register row, the candidate
must preserve:

1. An invalid `last_verified` date is due with the same parse-error detail.
2. Only critical/high observations participate; medium/lower observations do
   not affect the result.
3. `evidence_boost()` and `OPEN_STATUSES` remain the authority for whether an
   observation is closed.
4. A passing verification child supplies the close date. An observation-level
   `verification_result: pass` is the second choice. Otherwise the latest
   observation/child timestamp remains the fallback.
5. A later non-verification note does not replace an existing passing
   verification close date.
6. Duplicate `ledger_id` and `relates_to` handling remains last-value with the
   current first-position ordering inherited from the embedding-id scan.
7. Rows with `superseded is True` are excluded exactly as
   `ReadonlyUnitStore.units_metadata()` excludes them today. `deleted` is not a
   new exclusion rule.
8. The returned boolean and detail strings remain byte-identical for stable
   inputs, including `closed_count` and the selected latest ledger id.
9. A broken probe continues to become a due standing row with
   `probe error: <ExceptionType>` rather than crashing `convmem doctor` or brief
   generation.

This slice changes the read shape only; it does not redefine an exposure window
or its operational consequence.

## 5. Chosen design

### 5.1 One exact projected iterator

Add a private constant in `doctor.py` for this closed projection:

```text
id, ledger_id, ledger_kind, type, relates_to, timestamp, result,
verification_result, severity, superseded
```

`id` is supplied by the iterator from `embedding_id`; the remaining nine names
are the SQL metadata-key allowlist. Call:

```python
iter_collection_metadata_rows(
    chroma_dir,
    "knowledge_units",
    metadata_keys=EXPOSURE_WINDOW_METADATA_KEYS,
    include_document=False,
)
```

The projection is the exact union read by `_kind()`, `evidence_boost()`,
`_dedupe_by_ledger_id()`, and `_exposure_window_probe()`. It must not include
`document`, `chroma:document`, `provenance_envelope`,
`provenance_commitment`, `provenance_assertion_id`, title, summary, source
fields, or any other metadata.

A test must compare the requested and returned field sets to this closed union.
Adding a field requires returning the plan to Kiro unless it is necessary to
preserve a newly demonstrated existing consumer contract.

### 5.2 Preserve lifecycle and ledger semantics

Feed the iterator through a small filtering generator that drops a row only
when `row.get("superseded") is True`. Do not use provenance identity,
assertion-level supersession, or `deleted` as an exclusion rule.

Pass the filtered iterable to `build_ledger_index_from_metadata()`. That helper
already preserves the current relationships while avoiding
`_LEDGER_INDEX_CACHE`. `_exposure_window_probe()` then runs its existing
decision loop unchanged over the returned `by_ledger_id` and `by_relates_to`
maps.

The retained memory is explicitly **O(L)** in the number of ledger rows and
their small projected scalar fields. It is not constant-space, but it is
independent of document size, provenance-envelope size, and non-ledger payload
size. The probe must not retain id-only or non-ledger rows after the helper has
skipped them.

### 5.3 Authority and resource boundary

Remove the exposure probe's dependency on `open_readonly_unit_store`; do not
change that API for other consumers. The candidate must:

- use the merged iterator's SQLite URI `mode=ro` connection;
- create no Chroma client, database, WAL, SHM, lock, or cache entry;
- leave `_LEDGER_INDEX_CACHE` unchanged;
- close cursor and connection on exhaustion and on every injected iteration
  failure;
- perform no retry, fallback full scan, or compatibility-wrapper call;
- let iterator/query errors reach `_evaluate_standing_rows()`, whose existing
  fail-soft boundary converts them into an advisory due row.

One projected scan occurs per evaluated exposure-window row, matching the
current per-row evaluation model. Deduplicating probe evaluation across
multiple register rows is not part of this correction.

### 5.4 Hermetic measurement boundary

All tests and measurement workers use temporary Chroma, register, config, and
brief paths. To exercise the real brief-to-doctor chain, patch only the standing
register path to a temporary register containing the exposure-window row; do
not patch `standing_register_status`, `_exposure_window_probe`, the projected
iterator, or ledger/evidence functions.

Install production-path and network denial before importing target modules.
Pass an explicit temporary brief output path. Build large Chroma fixtures
outside measured subprocesses. Every before/after canary must prove that the
production Chroma, brief, config, export, watcher, and service paths were not
opened or modified.

## 6. Alternatives considered

### A. Disable the exposure-window standing check — rejected

That would hide a dependability warning rather than bound its read and would
change a closed T3 operational safeguard.

### B. Patch `standing_register_status()` out of brief generation — rejected

The diagnostic used that ablation to locate the allocator, not as a product
design. Removing the standing section changes brief meaning and leaves doctor
invocations exposed.

### C. Use `collection_metadata_rows()` and delete large keys afterward — rejected

The full list and envelope strings have already been materialized before the
caller can delete them. Post-read filtering cannot bound peak memory.

### D. Add a bespoke SQL exposure-window algorithm — rejected for this slice

SQL-side aggregation could reduce even the small ledger graph, but it would
duplicate `evidence_boost()` and ledger relation semantics in SQL. Reusing the
projected iterator and metadata-index helper is the smaller semantic surface.

### E. Cache the projected ledger graph — rejected

The probe is small after projection, while a process-lifetime cache adds stale
snapshot and invalidation authority. The existing non-caching helper is the
correct boundary for brief/doctor orientation.

### F. Normalize provenance-envelope storage — deferred

That removes the underlying storage duplication but changes provenance,
recovery, rebuild, and migration contracts. It remains a separate architecture
decision and is unnecessary to close this read-side allocator.

## 7. Cursor implementation sequence

Implementation requires a separate Ryan Execute authorization after Kiro PASS.

### C0 — Freeze exposure-window semantics

Before changing production code, extend the deterministic doctor fixture to
cover: invalid dates; no eligible observations; critical/high/medium severity;
open, failed, and passed verifications; observation-level pass; timestamp
fallback; later notes; duplicate ledger ids; duplicate relations; equal close
dates; superseded rows; `deleted` rows; malformed optional scalar values; and
empty/missing collections. Capture exact `(due, detail)` outputs and the
standing-register/brief representation as the golden oracle.

### C1 — Route the probe through the closed projection

Replace only the exposure probe's store construction with the exact projected
iterator and `build_ledger_index_from_metadata()`. Keep the decision loop and
public function signatures unchanged. Remove the now-unused doctor import of
`open_readonly_unit_store` only if no other doctor path uses it.

### C2 — Prove semantic parity

Run the C0 oracle against baseline and candidate behavior. Prove duplicate
handling, close-date precedence, equal-date winner, exact detail strings, and
`superseded is True` parity. Prove that `deleted` alone remains non-exclusionary.

### C3 — Prove projection closure and non-retention

Trap the actual iterator call and assert the exact ten-field output union, the
nine SQL metadata keys, and `include_document=False`. Fail if any document,
provenance, or unapproved field is requested or returned. Trap and fail any
call to `open_readonly_unit_store()`, `collection_metadata_rows()`,
`provenance_identity()`, or `_LEDGER_INDEX_CACHE` mutation from this probe.

### C4 — Prove cleanup and fail-soft behavior

Inject connection failure and iterator failure before the first row, between
ledger rows, and after the final row. Assert cursor/connection cleanup and no
WAL/SHM/database creation. Through real `standing_register_status()`, assert
the error remains an advisory due row with the current exception-type detail;
through brief generation, assert the complete brief is published with that
advisory due row and never as a partial file. Separately inject a failure beyond
the standing-register fail-soft boundary and prove the prior brief remains
byte-identical.

### C5 — Prove the hermetic boundary

Exercise `_exposure_window_probe()`, `standing_register_status()`, and the real
brief-to-doctor call chain using only temporary resources. Install path/network
denial before imports, redirect the standing register and brief output
explicitly, and assert all production canaries remain byte-, identity-, mode-,
and mtime-identical.

### C6 — Prove bounded memory

Use fresh subprocesses over 5,000, 20,000, and 58,825-unit synthetic Chroma
fixtures with the diagnostic metadata shape and 32 KiB
`provenance_envelope` values. Build fixtures outside the measured worker. Run
both the exposure probe alone and the full brief path with the real temporary
standing row under a 2 GiB address-space ceiling.

Record import baseline, peak RSS, elapsed time, projected row count, retained
ledger count, due/detail digest, and opened paths. Acceptance requires:

- every 58,825-unit candidate run completes below **384 MiB peak RSS** on the
  implementation host;
- the 58,825-unit full brief is no more than **160 MiB above import baseline**;
- changing envelope size from 2 KiB to 32 KiB at 20,000 units changes peak RSS
  by no more than **16 MiB**;
- probe outcome and detail digest match C0;
- no returned or retained row contains a forbidden field;
- the production-path denial count is zero because no production access is
  attempted.

Large host-specific RSS evidence belongs in the verification record, not as a
hard CI threshold. CI runs semantic/resource tests and a smaller memory smoke
with a generous ceiling.

### C7 — Verify governed surfaces and stop

Run focused doctor, brief, Chroma-readonly, ledger, unresolved, standing-check,
Arc Codex default-off/baseline, writer-inventory, and directly affected tests.
Run repository-wide pytest, `compileall`, `git diff --check`, scoped pylint, and
the pylint regression gate. Refresh only mechanically derived evidence that
actually changed. Update the execution plan verification section and current
routing, commit, push an exact tip, and stop for GitHub Copilot's targeted
safety/evidence audit. No PR or operational action.

## 8. Verification matrix

| Risk | Required proof |
|---|---|
| Exposure semantics drift | C0 baseline/candidate golden parity, including exact detail strings |
| Envelope is still fetched | Exact projection trap plus 2 KiB/32 KiB RSS comparison |
| Full-row store survives | Trap store/list helper and assert ledger cache unchanged |
| Superseded/deleted behavior changes | Explicit scalar lifecycle parity cases |
| Duplicate/equal-date ordering changes | Duplicate ledger/relation and equal-date golden cases |
| Iterator leaks on failure | First/middle/final failure injection plus fd/connection checks |
| Read-only helper mutates Chroma | URI `mode=ro`, no WAL/SHM, identity/mtime checks |
| Fail-soft becomes fail-open or crash | Real standing-register and brief-chain error tests |
| Hermetic test touches production | Pre-import path/network denial and before/after canaries |
| Memory still follows envelope bytes | 5k/20k/58,825 curve and envelope-size delta |
| Default-off or P2 regresses | Arc Codex baseline/live-denial tests |
| Issue #268 falsely declared closed | Verification and PR text retain the residual 12.5 GiB caveat |

## 9. Delivery and gate order

1. Kiro reviews this plan and returns PASS, CONDITIONAL PASS, or FAIL.
2. Ryan separately authorizes Cursor Execute C0–C7.
3. Cursor implements in a fresh worktree from the authorization tip, verifies
   hermetically, pushes an exact tip, and stops without opening a PR.
4. GitHub Copilot audit lane performs a targeted safety/evidence audit.
5. Kiro reviews the exact implementation tip after Copilot PASS.
6. Ryan decides PR and squash-merge disposition.
7. After merge, a fresh hermetic end-to-end `ingest.index(force_file=...)`
   comparison against `5c103aa…` determines the remaining memory floor.
8. Only that evidence may support a separate Ryan decision about watcher
   exclusions/operation or resuming the Arc Codex P2 packet.

No plan, review, merge, or memory PASS in this sequence authorizes production
access, watcher operation, configuration change, source re-inclusion, Gate 0,
P2, grant issuance, or activation.

## 10. Implementation evidence (corrective tip)

**Authorization ancestor:** `1be3a987472790222e4cc4985796ddced221a865` (Ryan Execute
handoff routing commit; plan tip `5672ee9…` remains in ancestry).

**Prior audit FAIL tip (preserved, not rewritten):**
`c9359ae645be10c0469b94e5df2f166b6328e8d9` on
`impl/2026-09-14-watch-oom-bound-exposure-probe`.

**Corrective branch:** `fix/2026-09-16-watch-oom-bound-exposure-probe-corrective`

**Worktree:** `~/Projects/convmem-watch-oom-exposure-probe-corrective`

**Change:** `_exposure_window_probe()` reads via `iter_collection_metadata_rows()`
with `EXPOSURE_WINDOW_METADATA_KEYS` (derived from `BRIEF_METADATA_KEYS`),
filters `superseded is True`, and builds the ledger graph through
`build_ledger_index_from_metadata()`. Hermetic workers install production-path
and network denial before target imports.

**Corrective audit fixes (vs `c9359ae…` FAIL):**

| Finding | Fix |
|---|---|
| Pylint `E0611` on `build_ledger_index_from_metadata` | Match `unresolved.py` import style; deduplicate worker/hermetic helpers |
| +16 duplicate-code regressions | Shared `watch_oom_hermetic_isolation.py`, `watch_oom_memory_worker_shared.py`, `watch_oom_memory_test_support.py` |
| R2b writer inventory drift at failed tip | Regenerated `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` for `doctor.py` + `brief.py` identity |
| Missing network denial / negative control | `install_network_denial()` before imports; `c5-negative-network` worker mode + test |
| Incorrect VERIFY routing (false “pre-existing R2b”) | This section records observed gates only |

**Hermetic proof (2026-09-17, corrective host):**

| Slice | Evidence |
|---|---|
| C0 | `tests/golden/watch-oom-bound-exposure/c0-oracle.json` — 15 scenarios, exact `(due, detail)` |
| C2–C5 | `tests/test_watch_oom_bound_exposure_probe.py` — projection trap, fail-soft, cleanup, ledger parity |
| C5 path | `tests/test_watch_oom_bound_exposure_memory.py::test_c5_probe_worker_denies_production_default_brief` |
| C5 network | `tests/test_watch_oom_bound_exposure_memory.py::test_c5_probe_worker_denies_outbound_network` |
| C6 smoke | 5k probe + brief chain under 384 MiB peak; 2 KiB/32 KiB envelope delta ≤ 16 MiB |
| C6 full | `CONVMEM_C6_FULL=1` — host evidence only (not CI-gated) |
| C7 | `compileall` PASS; `git diff --check` PASS; pylint regression PASS vs `1be3a98` and `origin/main`; focused pytest 166 passed / 1 skipped; R2b inventory suite 88 passed |

**Residual caveat (unchanged):** this slice removes the last demonstrated
envelope-sized reader on the measured brief path; it does **not** claim to close
the live 12.5 GiB watcher OOM.

**Next lane:** GitHub Copilot targeted safety/evidence re-audit on the pushed
corrective tip. No production access, watcher operation, config change, Kiro, or
Arc Codex Gate 0/P2.

### §9.7 post-merge ingest.index measurement (2026-09-18, archlinux)

**Branch:** `fix/2026-09-17-exposure-probe-postmerge-measurement` (pushed; no PR)

**Candidate SHA:** frozen at Execute start on `main` (see evidence JSON).

**Baseline SHA:** `5c103aa2f11f54de74be3a7eab90c433c0c019cd`

**Harness:** `tests/watch_oom_exposure_index_e2e_worker.py`,
`tests/test_watch_oom_exposure_index_e2e.py`,
`tests/watch_oom_exposure_index_e2e_support.py`

**Host:** `archlinux` (Ryan-authorized Execute lane)

**Mandated worker ceiling:** 2 GiB `RLIMIT_AS` + path/network denial before
target imports (per handoff).

**Outcome:** Under the mandated 2 GiB ceiling and **90s** worker timeout, paired arms
record distinct outcomes (`timed_out` with `returncode: null`, `exited`,
`invalid_output`, `succeeded`). On archlinux with the production watch active,
the first baseline arm **timed out** at 90s and production export-canary drift
stopped the run (`measurement_blocked: true` in evidence). **No paired
peak/floor delta is claimed.**

**Wiring proof:** `test_e2e_5k_harness_wiring_without_as_ceiling` passes
(in-process, no `RLIMIT_AS`).

**Evidence file:** `docs/plans/EVIDENCE-watch-oom-exposure-index-e2e.json`

**Verdict (unchanged):** the live **12.5 GiB** watcher OOM remains unexplained;
issue **#268** is **not** closed. No watcher exclusion or Arc Codex P2
progression is authorized from this result alone (§9.8, Ryan only).

**Next lane:** GitHub Copilot targeted safety/evidence audit on the pushed §9.7
tip; then Kiro honesty review.

## 11. Jargon glossary

- **Exposure window:** the standing check requiring a corpus-clean scan after a
  critical/high observation closes.
- **Projected iterator:** the PR #303 read API that asks SQLite only for named
  scalar metadata fields and yields one grouped row at a time.
- **Ledger relation graph:** maps from ledger ids and parent ids to small
  observation/verification metadata used by `evidence_boost()`.
- **O(L):** memory proportional to ledger rows, not all knowledge-unit payload
  bytes or provenance-envelope bytes.
- **Fail-soft:** a broken standing probe becomes an advisory due item rather
  than crashing doctor or completed ingestion.
- **Golden oracle:** frozen baseline outputs used to prove that the read-shape
  refactor does not change behavior.
- **Exact-tip review:** review of one immutable commit in a clean detached
  worktree.

## TL;DR

- PR #303 cut the measured brief floor roughly in half, but the standing
  exposure-window probe still constructs an unprojected full-row store.
- Reuse the merged projected iterator with ten exact scalar output fields,
  preserve the current ledger/evidence and `superseded is True` semantics, and
  avoid every full-row store/cache path.
- Prove semantic parity, fail-soft cleanup, hermeticity, and a flat
  envelope-size memory curve before delivery.
- Kiro reviews first; this plan authorizes no implementation, production
  operation, watcher change, or Arc Codex P2 work.
