# Implementation Handoff: §9.7 post-merge memory-floor measurement (exposure probe)

**Date:** 2026-09-17
**Author:** Kiro (design review lane)
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
| **Candidate** | current `main` tip containing `ef4a7dd` |
| **Branch to create** | `fix/2026-09-17-exposure-probe-postmerge-measurement` (fresh worktree from the authorization tip) |
| **PR** | `not opened` — push exact tip and stop |
| **Ryan GATE** | Ryan must authorize Cursor Execute for this measurement AND name the host/lane. No production access, watcher op, config change, or P2 progression. |

---

## What to build (consequence first)

Produce the **one number that unblocks the §9.8 decision**: the remaining
brief-path memory floor on merged `main`, measured through the **real
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
| `tests/watch_oom_exposure_hermetic.py::write_exposure_memory_fixture` | Build 5k / 20k / 58,825 synthetic Chroma with 32 KiB envelopes |
| `tests/watch_oom_memory_worker_shared.py::prepare_worker` | Path+network denial + 2 GiB `RLIMIT_AS` before target imports |
| `tests/watch_oom_hermetic_isolation.py` | Production-path/network denial guards + canaries |
| `tests/watch_oom_memory_test_support.py` | `MIB`, `MAX_PEAK_BYTES=384 MiB`, `MAX_FULL_OVER_BASELINE=160 MiB` |
| `tests/watch_oom_exposure_memory_worker.py` | Pattern for a subprocess measurement worker |

**New work:** add an `ingest`-driven worker mode (e.g. `--mode index-e2e`) and a
gated test (e.g. `tests/test_watch_oom_exposure_index_e2e.py`) that:

1. Builds the large Chroma fixture **outside** the measured subprocess.
2. In a fresh subprocess with denial + `RLIMIT_AS` installed before imports,
   runs the real `ingest.index(force_file=<synthetic transcript>)` control flow
   against a temporary Chroma/config/export/state (the same shape PR #303's
   post-merge diagnostic used).
3. Records import baseline RSS, peak RSS, elapsed, and opened paths.
4. Repeats the run against a `5c103aa` checkout to produce the baseline vs
   candidate delta.

The baseline arm requires a second worktree at `5c103aa`; measure both with the
identical worker and fixture builder so the delta is apples-to-apples.

---

## Specification

### Inputs
- Synthetic transcript(s) for `ingest.index(force_file=...)` (reuse the PR #303
  diagnostic transcript shape if recoverable; otherwise synthesize equivalent).
- Fixture sizes: 5,000 / 20,000 / 58,825 units, 32 KiB `provenance_envelope`.
- Temporary Chroma, config, export, state, brief output — no production paths.

### Behavior
```
for tip in (5c103aa_baseline, main_candidate):
    for n in (5_000, 20_000, 58_825):
        build fixture(n, 32KiB) OUTSIDE measured subprocess
        subprocess:
            install path+network denial; setrlimit(AS, 2 GiB)   # before imports
            baseline_rss = rss()
            ingest.index(force_file=synthetic_transcript, <temp everything>)
            emit {import_baseline, peak_rss, elapsed, opened_paths, denied_paths}
compute delta(candidate vs baseline) at each n; report remaining floor
```

### Output / contract
- Per (tip, n): import baseline RSS, peak RSS, elapsed, opened/denied paths.
- The **remaining floor** = candidate peak-over-import at 58,825 units, and the
  candidate-vs-`5c103aa` delta at each size.
- `denied_paths == []` (no production access attempted) — else the run fails.
- A written verdict paragraph that explicitly states the live 12.5 GiB OOM
  remains unexplained/open regardless of the measured floor.

### Hermetic rules (non-negotiable — mirror the merged C6 workers)
- Install path + network denial and `RLIMIT_AS` **before** importing `ingest`,
  `brief`, `doctor`, or Chroma modules.
- Temporary paths only; before/after canaries prove production Chroma/brief/
  config/export/watcher/service paths are byte-, identity-, mode-, and
  mtime-identical.
- Build large fixtures outside the measured subprocess.
- Negative controls prove the denial guards actually fire.

---

## What NOT to build / do
- **No** production access, live Chroma/brief/indexing, source re-inclusion.
- **No** watcher/systemd operation, config change, memory-cap/timeout/debounce
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

1. **e2e index candidate 5k/20k/58,825:** completes below the 2 GiB ceiling;
   `denied_paths == []`; records peak RSS.
2. **e2e index baseline `5c103aa` same sizes:** same, for delta.
3. **canary integrity:** all production canaries unchanged after every run.
4. **negative control:** denial guard fires when a production path is attempted.

CI keeps the existing smaller smoke; the full end-to-end curve is host evidence
recorded in the plan §10 verification section, not a hard CI threshold.

---

## Acceptance criteria
- [ ] Real `ingest.index(force_file=...)` runs hermetically at 5k/20k/58,825 on
      both `5c103aa` and merged `main`, under the 2 GiB ceiling.
- [ ] Remaining floor and candidate-vs-baseline delta reported per size.
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
Fresh worktree from the Ryan-authorized tip. Commit often; push each commit with
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
- [ ] Confirm `main` still contains `ef4a7dd`; create baseline worktree at `5c103aa`
- [ ] Build fixtures outside measured subprocess; denial+RLIMIT before imports
- [ ] Report floor + delta + honesty caveat; push exact tip; **no PR**

<!-- §9.7 measurement Execute spec. Authorizes no production/watcher/P2 action; requires Ryan Execute grant to start. -->
