# Implementation Handoff: §9.7 post-merge memory-floor measurement (exposure probe)

**Date:** 2026-09-17
**Author:** Kiro (design review lane); readiness corrections by Codex (2026-09-17)
**For:** Cursor (implementation / measurement lane)
**Authorization:** Ryan Execute grant REQUIRED before starting — see Ryan GATE. This handoff is a spec, not an authorization.

**Arc:** Watch OOM Bound Exposure Probe (Trapdoor Hunt operational follow-up; issue #268; does **not** reopen the closed provenance T3 gate)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` (BLOCKED_ON_RYAN) |
| **Depends on** | PR **#305** merged (`ef4a7dd972435de1fbb684cd3aba43076b8232f6` on `main`) — the exposure-probe corrective is live |
| **Baseline for comparison** | `5c103aa2f11f54de74be3a7eab90c433c0c019cd` (PR #303) |
| **Candidate** | Freeze and record the exact `origin/main` tip at Execute start; verify `ef4a7dd` is its ancestor. Do not advance the candidate during the paired run. |
| **Branch to create** | `fix/2026-09-17-exposure-probe-postmerge-measurement` (fresh dedicated worktree from that frozen tip) |
| **PR** | `not opened` — push exact tip and stop |
| **Ryan GATE** | After this self-contained documentation branch lands, Ryan must authorize Cursor Execute for this measurement AND name the host/lane. Use a quiet or isolated host for the full curve; defer it if shared work would face resource pressure. No measured-worker production access, watcher op, production config change, or P2 progression. |

---

## What to build (consequence first)

Produce the **remaining-floor measurement and paired deltas for the §9.8
decision**: the brief-path memory floor on merged `main`, measured through the **real
`ingest.index(force_file=...)` end-to-end control flow**, compared against
baseline `5c103aa`.

**Why this exists:** The merged corrective (PR #305) bounded the exposure-window
probe's read. The already-merged C6 tests prove the *probe alone* and the
*patched brief chain* are bounded — but they do **not** run the real end-to-end
indexing path. Plan §9.7 requires a fresh hermetic `ingest.index(force_file=...)`
comparison to establish the *remaining* floor after the fix. Only that evidence
may inform Ryan's watcher-exclusion / Arc Codex P2 decision (§9.8).

**Critical honesty constraint:** The hermetic harness historically peaked
~1.6 GiB and has **never** reproduced the live 12.5 GiB watcher OOM. This
measurement quantifies the measured brief-path floor; it does **not** explain or
close the live OOM. The verification record and any summary MUST retain that
caveat. **Do not declare issue #268 closed.**

---

## Integration point

Reuse the merged C6 scaffolding; do **not** reinvent fixtures or workers.

| Existing asset (on `main`) | Reuse for |
|---|---|
| `tests/watch_oom_exposure_hermetic.py::write_exposure_memory_fixture` | Reuse its 5k / 20k / 58,825 row schema and 32 KiB envelopes; its minimal SQLite database serves read-only C6 tests and is **not** the final writable end-to-end fixture |
| `tests/watch_oom_memory_worker_shared.py::prepare_worker` | Path+network denial + 2 GiB `RLIMIT_AS` before target imports |
| `tests/watch_oom_hermetic_isolation.py` | Production-path/network denial guards; take read-only canary snapshots in the harness parent |
| `tests/watch_oom_memory_test_support.py` | `MIB` and the existing C6 probe/brief thresholds (`MAX_PEAK_BYTES=384 MiB`, `MAX_FULL_OVER_BASELINE=160 MiB`); these are not end-to-end index thresholds |
| `tests/watch_oom_exposure_memory_worker.py` | Pattern for a subprocess measurement worker |

**New work:** add an `ingest`-driven worker mode (e.g. `--mode index-e2e`) and a
gated test (e.g. `tests/test_watch_oom_exposure_index_e2e.py`) that:

1. Builds a **writable Chroma** fixture with the same synthetic rows outside
   the measured subprocess. Prove at 5k that both `ChromaStore` writes and
   `chroma_readonly` reads work before building the full curve.
2. In a fresh subprocess with denial + `RLIMIT_AS` installed before imports,
   runs the real `ingest.index(force_file=<synthetic transcript>)` control flow
   against a temporary Chroma/config/export/state.
3. Records post-import baseline RSS, peak RSS, elapsed, opened paths, and the
   target production-module paths.
4. Repeats the run against a `5c103aa` checkout to produce the baseline vs
   candidate delta.

The baseline arm requires a second, detached worktree at `5c103aa`. That tree
predates the C6 helpers above: **do not expect the worker or fixtures to exist
there**. Run one test-only harness from the candidate worktree for both arms,
with an explicit target-root argument. Before importing `ingest`, put only the
selected target's production modules on the import path. Fail if a production
module was already imported from the harness/candidate tree or if the recorded
`ingest`, `brief`, `doctor`, `config`, or Chroma-read module path is outside
the selected target tree. Record the harness file hash for both arms.

---

## Specification

### Inputs
- One deterministic synthetic transcript for `ingest.index(force_file=...)`,
  used unchanged in both arms; record its hash and indexing result.
- Fixture sizes: 5,000 / 20,000 / 58,825 units, 32 KiB `provenance_envelope`.
  Refactor/reuse the C6 row generator as test-only code, preserving existing C6
  behavior. Populate a real temporary Chroma store for each seed; copying the
  minimal `write_chroma_sqlite()` database into an ingest writer path is invalid.
  Use the same deterministic vector dimension for fixture rows and stubbed
  indexing embeddings; prove a write/read round trip at 5k first.
- Temporary Chroma, config, export, state, brief output — no production paths.
- Use `write_exposure_register` from the C6 fixture module to place the
  exposure-window standing row under the temporary root. Point the standing
  register lookup there and prove the probe was called; record its due/detail
  digest and require the same semantic result in both arms.
- After fixture creation, close its Chroma client before cloning. Hash a
  manifest of every regular file (relative path, size, SHA-256) in the seed;
  verify each arm's clone against that manifest immediately before its worker.
- Set `CONVMEM_CONFIG` to each arm's temporary config **before** importing
  `config` or `ingest`; the config module captures its default path at import.
  Stub provider/model calls identically to keep the transcript deterministic
  and offline. Do not stub `ingest.index`, its Chroma write session, brief
  refresh/gather, the standing exposure probe, or their Chroma read path.
  Assert one file was processed, at least one unit was durably written to the
  temporary Chroma, and the real brief/exposure path executed; a skipped or
  failed-soft brief is not a successful measurement.
- Keep `HOME` unchanged so denial guards still identify the real production
  roots. Before calling `ingest.index`, redirect the writer lock, attestation,
  census, and other writer-state defaults to the arm's temporary paths without
  disabling the writer gate. In particular, inspect `chroma_write_store`'s
  `DEFAULT_WRITER_LOCK`/`DEFAULT_ATTEST_DIR` and `writer_census`'s
  `DEFAULT_CENSUS_DIR`. Assert no writer path resolves into production.

### Behavior
```
for n in (5_000, 20_000, 58_825):
    build one writable, immutable fixture seed(n, 32KiB) OUTSIDE measured subprocess
    for tip in (5c103aa_baseline, frozen_main_candidate):   # serial; no overlap
        clone seed into a fresh per-arm temporary Chroma; verify seed/clone hash
        subprocess using the SAME harness:
            set temporary config before target imports
            install path+network denial; setrlimit(AS, 2 GiB)
            import target modules from tip; assert their paths
            import_baseline_rss = rss()
            ingest.index(force_file=synthetic_transcript)
            emit {import_baseline, peak_rss, elapsed, opened_paths,
                  denied_paths, target_module_paths, index_stats}
        remove this arm's Chroma clone before starting the next
    remove fixture seed before building the next size
compute per-size candidate-vs-baseline delta; report remaining floor
```

### Output / contract
- Per (tip, n): exact target SHA, harness hash, fixture/transcript hashes,
  target module paths, post-import baseline RSS, peak RSS, elapsed, index
  result, brief/exposure execution proof, and opened/denied paths.
- The **measured remaining floor** = candidate peak minus its post-import RSS at
  58,825 units. Report candidate-vs-`5c103aa` differences in both raw peak
  and peak-over-import at every size; require equal brief/probe semantic digests
  for a paired row. Do not label a single run the live floor.
- `denied_paths == []` (no production access attempted) — else the run fails.
- A written verdict paragraph that explicitly states the live 12.5 GiB OOM
  remains unexplained/open regardless of the measured floor.

### Hermetic rules (non-negotiable — mirror the merged C6 workers)
- Install path + network denial and `RLIMIT_AS` **before** importing `ingest`,
  `brief`, `doctor`, or Chroma modules.
- Temporary paths only inside each worker. The harness parent takes read-only
  before/after canary snapshots proving production Chroma/brief/config/export/
  watcher/service paths are byte-, identity-, mode-, and mtime-identical;
  workers cannot open those paths.
- Build large fixtures outside the measured subprocess.
- Negative controls prove the denial guards actually fire.
- The writable fixture seed is read-only evidence during measurement. Index
  into separate per-arm clones so the baseline and candidate start from
  identical Chroma files.

### Host resource boundary

The 2 GiB `RLIMIT_AS` applies only to each measured worker. Fixture creation,
SQLite copies, filesystem cache, and pytest itself remain outside that limit.
The 58,825 × 32 KiB envelopes contain about 1.8 GiB of raw data before SQLite
overhead. A dedicated Git worktree isolates source edits, **not** shared host
RAM, CPU, disk, or services.

- Use a named quiet/isolated host and a disk-backed temporary scratch directory
  outside production ConvMem data/config roots; do not put the full fixture on
  tmpfs by default. Check at least 8 GiB available RAM and 8 GiB free scratch
  before the full curve. If unavailable, defer and report rather than compete
  with other work.
- Build one size at a time, run one worker at a time, and delete each arm clone
  and seed when its comparison is complete. Do not run the full curve with
  parallel pytest workers or another large memory test.
- Monitor available RAM and scratch during the run. Stop before the next arm
  if available RAM falls below 4 GiB, scratch becomes insufficient, or another
  active workload is affected. Report the completed rows without extrapolating.

---

## What NOT to build / do
- **No** measured-worker production access, live Chroma/brief/indexing, source
  re-inclusion, or production mutation. The harness parent may read only the
  named production canaries before/after each arm.
- **No** watcher/systemd operation, production config change, memory-cap/timeout/debounce
  change, exclusion change.
- **No** Arc Codex Gate 0, P2 packet/grant/digest, or activation.
- **No** change to merged production code (`doctor.py`, `brief.py`,
  `chroma_readonly.py`, `ledger.py`) — this is measurement only. If measurement
  reveals a *new* allocator, STOP and return a finding; do not fix it under this
  handoff.
- **No** claim that this closes issue #268 or the live OOM.
- **No** PR — push the exact tip and stop for review.

---

## Test expectations
Gated test `tests/test_watch_oom_exposure_index_e2e.py` (host evidence, not a CI
RSS gate — mark `skipif` on an env flag like the existing `CONVMEM_C6_FULL`):

1. **e2e index candidate 5k/20k/58,825:** completes below the 2 GiB worker
   ceiling; `denied_paths == []`; records peak RSS and real brief execution.
2. **e2e index baseline `5c103aa` same sizes:** identical harness, transcript,
   and fixture seed; target production-module paths prove the correct checkout.
3. **canary integrity:** all production canaries unchanged after every run.
4. **negative control:** denial guard fires when a production path is attempted.

CI keeps the existing smaller smoke; the full end-to-end curve is host evidence
recorded in the plan §10 verification section, not a hard CI threshold.

---

## Acceptance criteria
- [ ] Real `ingest.index(force_file=...)` runs hermetically at 5k/20k/58,825 on
      both `5c103aa` and merged `main`, under the 2 GiB ceiling.
- [ ] Both arms use one hashed harness and identical pre-run writable fixture
      bytes; all target production modules resolve to the intended checkout.
- [ ] Temporary writer gate/attestation/census paths are exercised; no live
      writer path is opened, and a unit is written to temporary Chroma.
- [ ] Remaining floor and candidate-vs-baseline delta reported per size.
- [ ] Full curve runs serially on the named host within the scratch/RAM budget;
      stop conditions are checked between arms.
- [ ] `denied_paths == []`; all production canaries byte/identity/mode/mtime-identical.
- [ ] Written verdict retains the "12.5 GiB live OOM still open; #268 not closed" caveat.
- [ ] No production code changed; no regression in existing suite; ruff/pylint clean.
- [ ] Exact tip pushed with explicit refspec; **no PR opened**.
- [ ] Plan §10 verification section updated with the measured floor; `LATEST.md`
      bullet + this handoff's resume state advanced.

---

## Branch convention
```
fix/2026-09-17-exposure-probe-postmerge-measurement
```
Fresh worktree from the frozen `origin/main` tip at Execute start, after this
documentation is available to Cursor. Commit often; push each commit with
an explicit refspec (`git push -u origin "<branch>:refs/heads/<branch>"`). Stop
after pushing the exact tip — GitHub Copilot targeted audit and Kiro review
follow before any §9.8 decision.

---

## Gate order after this task (plan §9.7 → §9.8)
1. Cursor runs the measurement, pushes exact tip, stops (this handoff).
2. GitHub Copilot targeted safety/evidence audit on the pushed tip.
3. Kiro reviews the measurement evidence for honesty (floor claim vs live OOM).
4. **Ryan only:** decide watcher exclusions/operation or Arc Codex P2 resumption
   — only on the strength of this evidence.

---

## Related files
| What | Path |
|------|------|
| Execution plan (§6 measurement rules, §9 gate order, §10 evidence) | `docs/plans/EXECUTION-watch-oom-bound-exposure-probe.md` |
| Post-merge routing handoff (parent) | `docs/inter-model/KIRO-2026-09-17-exposure-probe-postmerge-handoff.md` |
| Merged production change | `doctor.py`, `brief.py` |
| Reuse: fixtures/workers/thresholds | `tests/watch_oom_exposure_hermetic.py`, `tests/watch_oom_memory_worker_shared.py`, `tests/watch_oom_hermetic_isolation.py`, `tests/watch_oom_memory_test_support.py`, `tests/watch_oom_exposure_memory_worker.py` |

---

## Picking up checklist (Cursor)
- [ ] Confirm Ryan Execute authorization + named host/lane before any edit
- [ ] Read this file + plan §6 and §9 first
- [ ] Freeze the exact candidate tip containing `ef4a7dd`; create detached
      baseline worktree at `5c103aa`
- [ ] Use one harness for both arms; verify target imports and fixture hashes
- [ ] Confirm quiet host + disk-backed scratch budget; build/run serially
- [ ] Build fixtures outside measured subprocess; denial+RLIMIT before imports
- [ ] Report floor + delta + honesty caveat; push exact tip; **no PR**

<!-- §9.7 measurement Execute spec. Authorizes no production/watcher/P2 action; requires Ryan Execute grant to start. -->
