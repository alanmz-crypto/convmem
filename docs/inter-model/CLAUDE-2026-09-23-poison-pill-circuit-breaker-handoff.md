# Implementation Handoff: Poison Pill circuit breaker + crash accounting

**Date:** 2026-09-23
**Author:** Claude (investigation/handoff)
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-09-23 (verbal in session — "finish what doesn't upset Switchboard,
leave the rest till Switchboard is done") — scoped to the two backlog items below only.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `fix/2026-09-23-poison-pill-circuit-breaker` (create from `fix/2026-09-20-chroma-upsert-poison-pill` @ `9ebbb2f`) |
| **Tip SHA** | `9ebbb2fe5ea40f4aaf9fb65e8473bc932734c0a4` (poison-pill close-out anchor, current tip) |
| **Push status** | not yet created |
| **PR** | not opened |
| **Ryan GATE** | None to start; PR review before merge as usual |
| **Worktree** | Use `~/.local/share/convmem/worktrees/fix-2026-09-20-chroma-upsert-poison-pill` if free, or `--worktree` a new one — do not touch any Switchboard worktree/branch |

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

- [ ] Per-file quarantine + global circuit breaker implemented at the `watch.py` scheduler loop
- [ ] Native-fault vs. timeout vs. ordinary-failure returncode parsing is signal-aware (negative
      returncode = signal death), not string-matched loosely
- [ ] Quarantine state persisted atomically (temp+rename)
- [ ] `--clear-quarantine[-all]` CLI surface added
- [ ] `native_crash_count` doctor field added, distinct from `ingest_degraded`
- [ ] All 9 test cases above pass
- [ ] No Switchboard file, branch, or worktree touched (verify with `git diff --stat` against
      `origin/main` before opening the PR — every changed path should be watcher/doctor/test files)
- [ ] No regression in existing suite
- [ ] Ruff / pylint clean per repo gates

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
| Scheduler loop (integration point) | `watch.py:494-502` |
| Subprocess spawn / RuntimeError source | `watch.py:206-259` |
| Doctor synthesis gate | `doctor.py:440-490` |
| Full circuit-breaker design rationale | `KIRO-2026-09-20-arc-poison-pill-phase-c-handoff.md` (poison-pill worktree, §"Separable work that does not depend on root cause") |
| Backlog anchor | `KIRO-2026-09-21-poison-pill-closeout-handoff.md` (poison-pill worktree), items 1–2 |
| Excluded lead (do not re-touch) | `EXECUTION-poison-pill-resume.md:283` (poison-pill worktree) |
| Today's recurrence evidence | This session's transcript (Track A pending) |

---

## Leaving / picking up checklist

**Author (Claude, leaving):**

- [x] This file committed and pushed
- [ ] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-chroma-upsert-crash.md` Update Log line, if that arc brief still exists on this branch
- [x] Branch convention specified (Cursor creates the branch itself — nothing to push from this
      session on that branch)

**Implementer (Cursor, picking up):**

- [ ] Read this file before first edit
- [ ] Create `fix/2026-09-23-poison-pill-circuit-breaker` from `fix/2026-09-20-chroma-upsert-poison-pill` @ `9ebbb2f`
- [ ] Confirm no Switchboard path appears in `git diff --stat` before opening the PR
