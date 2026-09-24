# Implementation Handoff: Poison Pill circuit breaker + crash accounting

**Date:** 2026-09-23
**Author:** Claude (investigation + implementation, at Ryan's explicit direction — see Update below)
**For:** Ryan review / PR
**Authorization:** Ryan, 2026-09-23 (verbal in session — "finish what doesn't upset Switchboard,
leave the rest till Switchboard is done") — scoped to the two backlog items below only.

---

## Update — implemented, not by Cursor

Ryan asked Claude directly to build this rather than hand off to Cursor ("can you do the work for
Cursor"). Implemented and pushed. This is a deviation from the project's normal
implementation-lane convention (Cursor), done at explicit user direction — noted here so a future
reader isn't confused about why a "handoff to Cursor" doc has a finished implementation attached.

## Update — CI green after three fix-forward commits

The first push (`2ee4c12`) failed CI on two real, unrelated-looking gates that both trace to one
cause: the `--clear-quarantine` CLI flags added ~25 lines above `convmem.py`'s existing production
`ChromaStore` call site, shifting every line-number pin below it, plus pushing `watch.py`'s
control-flow complexity over the pylint regression gate. Fixed across three commits:

- `3a93271` — extracted `_process_ready_path`/`_record_ready_path_failure` to fix the
  too-many-branches/too-many-nested-blocks regression; refreshed `watch.py`'s T0 canary SHA-256;
  refreshed the convmem.py:655→680/671→696/1733→1758 line pins in
  `eval_corpus/r2b_v2/coverage/inventory.py` and `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json`.
- `604ff4c` — the full local suite (2691 passed) surfaced a fourth stale pin: the committed
  `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` binds a `code_revision` that's a content hash
  over R2b's governed-route dependency closure (`convmem.py` included), so it went stale too.
  Regenerated via the module's own `write_v2_inventory_file()` rather than hand-editing — every
  changed line was mechanically `code_revision`/`inventory_digest`, verified.
- `1615928` — CI's pylint gate caught two `watch.py` imports (`reconcile_manifest`,
  `token_manifest_path`) orphaned by the `3a93271` refactor; removed.
- `554781a` — that two-line removal changed `watch.py`'s content again, re-invalidating the same
  two content-identity pins a second time (same mechanism, not a new cause); refreshed both again.

All fixes verified snippet-by-snippet or via the artifact's own sanctioned regeneration path before
committing — none were blind edits to security/provenance-adjacent files. Final tip `554781a`
passes all 6 CI checks (pylint, pytest, CodeQL ×2, Analyze ×2, secret-scan).

## Update — merged

PR #328 was squash-merged by Ryan as `81efa35` on `main` (2026-09-24). This doc is kept for
provenance/history; no further action is pending on this fix. Root-cause reopening (see below)
remains a separate, deliberately deferred decision.

## Update — root-cause reopening: bounded stop rule (2026-09-24)

The open question left after this merge is whether the 2026-09-21 acceptance ("root cause =
platform, not software") still holds, given the 2026-09-23 recurrence had clean hardware telemetry.
Applying [`DECISION-REVIEW-GUARDRAILS.md`](DECISION-REVIEW-GUARDRAILS.md) at Ryan's direction:

- **Pattern:** not recursive review — the risk was the opposite: an open-ended "defer until
  Switchboard is done" gate with no size or date, which could quietly become permanent avoidance of
  a possibly-wrong architectural conclusion rather than a deliberate schedule.
- **Evidence:** identical crash signature recurred with the BIOS fix still in effect and zero
  MCE/thermal events; the arc's own closeout doc states this recurrence condition revokes the
  acceptance; the software-cause exclusion test (300k-upsert matrix) predates this recurrence.
- **Level:** at least interface/contract (`convmem-watch` is shared infrastructure every arc
  depends on, Switchboard included) — arguably architectural, since the accepted root-cause
  diagnosis itself may be wrong, not just an implementation detail under it.
- **Decision value:** real. Confirmed-still-platform → current containment (PR #328) is sufficient,
  acceptance stands. Confirmed-still-software → the R2b/Chroma dependency needs a fix beyond
  containment before Switchboard goes live on a read-heavy connector to this same corpus.
- **Stop rule (accepted, replaces open-ended Switchboard-gating):** whichever comes first —
  **7 days of clean `convmem-watch` operation** (`doctor`'s `native_crash_gate` reports 0 native
  crashes in its rolling 7-day window with no active quarantine entries), **or a second native-fault
  recurrence within that window** — triggers the root-cause investigation, independent of
  Switchboard's state. No new automation was built for this: `native_crash_gate` (landed in this
  same PR) already reports exactly the count and latest-crash data needed to evaluate it by hand;
  adding a bespoke trigger would be the "one-off procedure becoming unnecessary infrastructure"
  pattern the guardrails doc itself warns against.
- **Recommendation applied:** narrow, not stop — investigation isn't reopened now, but the
  deferral is bounded instead of indefinite.

**For whoever checks this next:** run `convmem doctor` (or `doctor --v1`) and read the
`native_crash_gate` line. If it reports 0 crashes and the merge date above is 7+ days past, or if
it reports 2+ crashes in the window, the stop rule has fired — open the root-cause investigation
regardless of what Switchboard's status is at that moment.

## Resume state

| Field | Value |
|-------|--------|
| **State** | `MERGED` |
| **Branch** | `fix/2026-09-23-poison-pill-circuit-breaker` (created from `origin/main` @ `9193f5e`, not the stale poison-pill worktree — see rationale below); merged and safe to delete |
| **Tip SHA (pre-merge)** | `554781a` |
| **Merge commit** | `81efa35` on `main` |
| **PR** | [#328](https://github.com/alanmz-crypto/convmem/pull/328) — MERGED |
| **Ryan GATE** | None — closed |

---

## Why this exists

Arc Poison Pill was accepted 2026-09-21 (root cause: unstable RAM under XMP; fix: BIOS defaults
restored) and downgraded to a non-blocking hardening backlog. Today, 2026-09-23 08:58:04 CDT, the
exact same crash signature recurred: `convmem-watch` spawned `convmem index --file LATEST.md`,
which took a native fault (`index subprocess exit -11`) during a Chroma upsert. Hardware/BIOS
telemetry for this recurrence is clean (PL1/PL2 still 253W/253W, zero MCE/thermal events in the
window) — see `docs/inter-model/CLAUDE-2026-09-23-...` session record. **This does not reopen root
cause in this handoff.** It only authorizes the two already-scoped, already-safe hardening items
that exist specifically to contain this class of crash regardless of cause:

1. No mechanism currently stops the watcher from repeatedly re-attempting a path that native-faults.
2. Native crashes are currently invisible in `doctor` — they'd either go uncounted or get silently
   folded into `ingest_degraded`, which conflates a crash with an ordinary provider drop.

Full background/forensics: `KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` (this worktree),
`KIRO-2026-09-21-poison-pill-closeout-handoff.md` §"Open future work" items 1–2.

---

## Integration points

### 1. Per-file quarantine + global circuit breaker

`watch.py:494-502` — the scheduler's ready-loop:

```python
for path in scheduler.ready():
    try:
        if is_reconcile_token(path):
            reconcile_manifest(token_manifest_path(path), cfg)
        else:
            flush_path(path, verbose=verbose, use_subprocess=True)
    except Exception as e:
        print(f"[watch] error processing {path}: {e}", file=sys.stderr)
    scheduler.forget(path)
```

`flush_path` → `_flush_path_subprocess` (`watch.py:206-259`) raises `RuntimeError` two ways:

- `f"index subprocess exit {proc.returncode}"` — `proc.returncode` is negative for a signal death
  (e.g. `-11` = SIGSEGV, `-6` = SIGABRT, `-7` = SIGBUS). **These are native faults.**
- `f"index subprocess timed out after {timeout:g} seconds"` — not a native fault; own threshold.

Neither case currently distinguishes a native fault from any other failure, and neither is counted
per-path.

### 2. Crash-vs-provider-drop accounting

`doctor.py:440` — `_check_synthesis_gate()`, `ingest_degraded` counter at `doctor.py:461-473`. Add a
sibling counter; do not fold native crashes into `ingest_degraded`.

---

## Specification

### Per-file quarantine + circuit breaker

```
on RuntimeError from flush_path(path):
    parse the returncode (or "timed out") from the exception message
    if returncode in {-11, -6, -7}:              # native fault
        native_crash_count[path] += 1
        global_native_crash_count += 1
        if native_crash_count[path] >= N:
            quarantine[path] = now()             # skip on future scheduler.ready() until cleared
            log + append an observation-shaped record (do not call convmem add directly —
              see "What NOT to build")
    elif "timed out" in message:
        timeout_count[path] += 1
        if timeout_count[path] >= M:
            quarantine[path] = now()
    else:
        # ordinary failure (parse error, provider drop, etc.) — existing behavior, uncounted here
        pass

    if global_native_crash_count within the last <window minutes> >= <global threshold>:
        stop spawning new index children entirely; log; raise/record an observation
        (this is the global circuit breaker — protects against a crash storm regardless of
        which file triggers it, per phase-C handoff's point that the failure is not
        file-scoped)

on success for path:
    reset native_crash_count[path] and timeout_count[path] to 0
```

Key correctness points from the phase-C handoff (do not relitigate these, just honor them):

- **Key by path, not by content hash.** A crash counter must survive the file changing.
- **Reset on success.** A path that recovers should not stay quarantined.
- **Append-safe / byte-prefix rule.** Persistence of quarantine state must not itself be a new
  crash surface — atomic write (temp file + rename), not an in-place mutation that can be caught
  mid-write by the exact class of process death this feature exists to survive.
- **A signal death is not a non-zero exit in the ordinary sense** — make sure the returncode
  parsing actually distinguishes negative (signal) from positive (normal nonzero exit) values;
  don't just string-match on "exit" without checking sign.

### CLI

`convmem watch --clear-quarantine <path>` and `--clear-quarantine-all` — implementer's call where
this attaches in the existing `convmem.py` subcommand structure (watch.py itself has no argparse;
find the actual CLI entry point before designing the flag surface — do not assume its shape from
this doc).

### Doctor field

```
DoctorCheck field: native_crash_count  (distinct from ingest_degraded)
```

Window: match whatever window `_check_synthesis_gate` already uses (7d) unless there's a reason to
diverge — state the reason if you do.

---

## What NOT to build

- **Do not reopen or re-litigate root cause.** The platform-vs-software question stays parked. This
  handoff is scoped to containment (stop a crash loop, count crashes accurately), not diagnosis.
- **Do not touch `hnsw:num_threads` or any `chroma_store.py` collection-creation metadata.** That
  lead was already tested (300,000-upsert matrix, default threads + `num_threads=1` + concurrent
  readers, 15/15 clean) and excluded — see `EXECUTION-poison-pill-resume.md:283` in this worktree.
  Re-touching it is out of scope here.
- **Do not touch BIOS, hardware, or anything requiring a physical reboot/settings change.** Ryan's
  gate, not an agent's, per the phase-C handoff's own "What NOT to build."
- **Do not touch any Switchboard branch, worktree, or file** (`feat/2026-09-21-openclaw-convmem-t0-t5`,
  `docs/2026-09-23-switchboard-naming-lock`, `docs/plans/*openclaw-convmem-integration*`,
  `docs/plans/*openclaw-watch-coverage*`). This work must be independently mergeable without
  touching anything in that arc's scope.
- **Do not call `convmem add` or otherwise write the ledger directly.** If the circuit breaker needs
  to "raise/record an observation," write it to a log or a structured file the way the codebase
  already does for other watcher events — durable ledger writes stay Ryan/CLI-owned per the
  read-only-guard convention already in force project-wide.
- **Do not restart or reconfigure the live `convmem-watch`/`convmem-reconcile` services as part of
  building this** — build and test against the code/tests only. Deploying to the live service (which
  requires a restart from `.worktrees/runtime-main`) is a separate, later step Ryan should sign off
  on once the PR is reviewed.
- **No corpus-wide reindex, no live Chroma writes during development** — test against fixtures/mocks
  per the existing test suite's conventions (see e.g. `tests/test_shadow_writer_gate_c3.py` for the
  house style on gated-writer tests).

---

## Test expectations

Focused tests, new file `tests/test_watch_circuit_breaker.py`:

1. **Native fault increments per-path counter:** simulate `flush_path` raising
   `RuntimeError("index subprocess exit -11")`; assert `native_crash_count[path] == 1`.
2. **Quarantine after N:** N consecutive native faults on the same path → path is skipped by
   `scheduler.ready()` (or equivalent) until cleared.
3. **Reset on success:** a path with a prior fault that then succeeds has its counter reset to 0.
4. **Non-signal failure is not counted as a native crash:** an ordinary parse/provider-drop
   exception does not increment `native_crash_count` or trigger quarantine.
5. **Timeout has its own independent threshold M**, not conflated with the signal-death threshold N.
6. **Global circuit breaker:** N-plus native faults across *different* paths within the window
   trips the global breaker (spawning stops) even though no single path hit its own per-path
   threshold.
7. **Quarantine state persists atomically:** simulate a process death mid-write of quarantine state;
   assert the on-disk file is never left partially written (temp+rename, or equivalent).
8. **`--clear-quarantine` / `--clear-quarantine-all`** clear the intended scope only.
9. **Doctor `native_crash_count` is distinct from `ingest_degraded`:** a synthetic native crash does
   not change the `ingest_degraded` count, and vice versa.

Use fixtures/mocks; no dependency on live corpus, live Chroma, or the actual `convmem-watch` service.

---

## Acceptance criteria

- [x] Per-file quarantine + global circuit breaker implemented at the `watch.py` scheduler loop
- [x] Native-fault vs. timeout vs. ordinary-failure returncode parsing is signal-aware (negative
      returncode = signal death), not string-matched loosely
- [x] Quarantine state persisted atomically (temp+rename via `os.replace`)
- [x] `--clear-quarantine[-all]` CLI surface added (`convmem watch --clear-quarantine <path>` /
      `--clear-quarantine-all`)
- [x] `native_crash_count`-equivalent doctor field added as `native_crash_gate`, distinct from
      `ingest_degraded` and `index_gate`
- [x] 22 circuit-breaker tests (`tests/test_watch_circuit_breaker.py`) + 5 doctor-gate tests
      (`tests/test_native_crash_gate.py`) — all pass, covering the 9 cases the spec called for
- [x] No Switchboard file, branch, or worktree touched — `git diff --stat origin/main` shows only
      `config.example.toml`, `convmem.py`, `doctor.py`, `watch.py`, and the two new test files
- [x] No regression: `test_watch*.py` (36), `test_doctor.py` (68), plus all watch/doctor-tagged
      tests project-wide (190 passed, 2 pre-existing skips) — all green
- [x] Pylint: new code adds zero new pylint findings beyond the file's pre-existing baseline
      (verified by comparing `pylint doctor.py watch.py convmem.py` before/after; new test files
      score clean). Ruff was not used as the gate — this repo's CI gate is the pylint regression
      gate (`.github/workflows/pylint.yml`), not ruff.

**Deviation from spec:** built directly on `origin/main` (`9193f5e`, current tip, already includes
the Switchboard T0–T5 merge) rather than the stale poison-pill branch tip named in the original
spec — that tip pre-dates the Switchboard merge and its `watch.py` changes, so branching from it
would have created the exact merge-collision risk this handoff was written to avoid. See the new
worktree note in "Related files" below.

---

## Branch convention

```
fix/2026-09-23-poison-pill-circuit-breaker
```

Push immediately after each commit. Open PR when acceptance criteria pass. Ryan squash-merges
unless PR says **Do not squash**. PR body should note this is containment-only, root cause remains
open, per the "What NOT to build" section above.

---

## Related files

| What | Path |
|------|------|
| New worktree (built here, not the stale poison-pill one) | `~/.local/share/convmem/worktrees/fix-2026-09-23-poison-pill-circuit-breaker` |
| Circuit breaker implementation | `watch.py` (`CircuitBreakerState`, `parse_native_fault_returncode`, `is_native_fault_returncode`, `is_timeout_message`, `log_native_crash`) |
| Scheduler loop (integration point) | `watch.py` `run_watch()` main loop |
| Subprocess spawn / RuntimeError source | `watch.py` `_flush_path_subprocess` |
| Doctor gate | `doctor.py` `_check_native_crash_gate()` |
| CLI | `convmem.py` `watch()` command, `--clear-quarantine[-all]` |
| Tests | `tests/test_watch_circuit_breaker.py`, `tests/test_native_crash_gate.py` |
| Config docs | `config.example.toml` `[watch]` section |
| Full circuit-breaker design rationale | `KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` (old poison-pill worktree, §"Separable work that does not depend on root cause") |
| Backlog anchor | `KIRO-2026-09-21-poison-pill-closeout-handoff.md` (old poison-pill worktree), items 1–2 |
| Excluded lead (do not re-touch) | `EXECUTION-poison-pill-resume.md:283` (old poison-pill worktree) |
| Today's recurrence evidence | This session's transcript (Track A pending) |

---

## PR — opened as [#328](https://github.com/alanmz-crypto/convmem/pull/328) (PR Steward grant, 2026-09-23; not merged)

**Title:** Contain native-fault index crashes with a watch circuit breaker

**Branch:** `fix/2026-09-23-poison-pill-circuit-breaker` → `main`

**Body:**

> **What changes for you:** `convmem-watch` no longer retries a file that keeps crashing the index
> subprocess forever, and `convmem doctor` now shows native crashes as their own number instead of
> hiding them inside provider-drop counts.
>
> **Who/What/When/Why/How:** Claude (at Ryan's direction) built a per-file quarantine and a global
> circuit breaker into the watcher, plus a `native_crash_count`-equivalent doctor gate
> (`native_crash_gate`), after a native-fault crash (SIGSEGV) recurred 2026-09-23 in
> `convmem-watch` — the same signature Arc Poison Pill's 2026-09-21 acceptance was meant to close.
> Rather than reopen that root-cause question mid-Switchboard, this lands only the two
> already-authorized, non-blocking hardening backlog items (per-file/global circuit breaker,
> crash-vs-provider-drop accounting) so a repeat crash quarantines itself instead of looping.
>
> **Scope:** containment only. Does not touch Chroma HNSW threading (already tested and excluded
> as a cause), BIOS/hardware, or any Switchboard file/branch — confirmed via `git diff --stat`
> against `origin/main`.
>
> **TL;DR:** Adds a watch-side circuit breaker + doctor visibility for native-fault index crashes;
> root cause of the underlying crash stays open and deferred until the Switchboard arc is done.
>
> Refs: `docs/inter-model/CLAUDE-2026-09-23-poison-pill-circuit-breaker-handoff.md`,
> `docs/inter-model/CLAUDE-2026-09-23-switchboard-transition-readiness-review.md`

**Merge reading:** none — this is drive-by containment work, not an arc close or Execute landing.

**Test plan:**
- `pytest tests/test_watch_circuit_breaker.py tests/test_native_crash_gate.py -q` → 27 passed
- `pytest -k "watch or doctor or native_crash" -q` → 190 passed, 2 pre-existing skips
- `pylint watch.py convmem.py doctor.py tests/test_watch_circuit_breaker.py tests/test_native_crash_gate.py` → no new findings vs. pre-change baseline

---

## Leaving / picking up checklist

**Author (Claude, leaving):**

- [x] This file committed and pushed (updated with implementation results)
- [x] `LATEST.md` bullet updated with resume state
- [ ] `STATUS-chroma-upsert-crash.md` Update Log line — not touched; that arc brief lives only in
      the old poison-pill worktree/branch, out of scope for this containment-only PR
- [x] Branch pushed: `fix/2026-09-23-poison-pill-circuit-breaker` @ `554781a` (CI green)

**Reviewer (Ryan, picking up):**

- [x] PR opened: [#328](https://github.com/alanmz-crypto/convmem/pull/328)
- [ ] Review the diff and merge when ready (squash-merge default applies unless you say otherwise)
- [ ] Root-cause reopening (today's recurrence vs. 2026-09-21 acceptance) stays a separate,
      later decision — not part of this PR
