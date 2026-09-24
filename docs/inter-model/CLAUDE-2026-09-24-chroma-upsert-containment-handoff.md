# Implementation Handoff: Chroma native-write containment (Arc Poison Pill — Part B, Part C findings)

**Date:** 2026-09-24
**Author:** Claude (Opus 5.5), implementation lane
**For:** Ryan (review-lane choice, merge, deploy)
**Authorization:** Ryan, 2026-09-24. Brief reassigned the refreshed Kiro handoff from Cursor to Claude:
Part B (containment) and Part C (investigation only). No chromadb bump, no corpus re-index, no Switchboard,
no hardware.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `READY_FOR_PR` |
| **Branch** | `fix/2026-09-24-chroma-upsert-containment` (worktree `~/.local/share/convmem/worktrees/fix-2026-09-24-chroma-upsert-containment`) |
| **Tip SHA** | see `git log -1 origin/fix/2026-09-24-chroma-upsert-containment` (implementation commit `bca3d12`) |
| **Push status** | pushed to origin |
| **PR** | not opened (Ryan opens and owns the merge) |
| **Ryan GATE** | 1) choose a review lane (recommend Kiro design review and/or Copilot safety audit: this guards the shared writer path); 2) merge; 3) deploy = fast-forward `.worktrees/runtime-main`, then restart `convmem-watch` |
| **Production impact today** | none. The watcher runs from `.worktrees/runtime-main` (`main`), and nothing here was deployed |

---

## What was built

Every production Chroma write (every `ChromaStore` that `open_chroma_for_write(purpose="production")` creates)
now runs each native mutation (`upsert`/`update`/`delete`) inside `ChromaWriteGuard.native_write`
(`chroma_write_guard.py`). The guard keeps these invariants:

1. **One native write at a time across processes.** An exclusive `flock` on
   `<chroma_dir>.write-guard/native-write.lock`, held per call rather than per session, so long refine jobs don't
   block the watcher. It sits inside the existing shared writer lease, so backup captures behave as before.
2. **No saves from a stale in-process index.** If another process saved since this process's Chroma
   system loaded, the client is reloaded before writing. If another client in the same process pins the stale
   system, the write is refused (`ChromaStaleSystemError`) rather than silently losing data.
3. **A validated copy of each segment's last save** (`<chroma_dir>.write-guard/snapshots/<segment>/`). It is refreshed
   after every save through an atomic generation plus a `CURRENT` pointer.
4. **Restore only when torn.** Before any write, a live segment whose files changed since the restore point is
   validated: PASS → adopt it as the new restore point; FAIL → restore the copy, then run a census that confirms no record
   lost its vector. Restoring over a *valid* segment is never done, because that is the lossy case.
5. **Fail closed.** A torn segment with no restore point, a failed copy, a lossy restore, or this process's own
   save failing validation all write `QUARANTINE.json` and stop guarded writes. Reads are unaffected.

Also added:
- `watch.py`: after any abrupt index-child exit (signal death, including OOM `-9`, or a timeout kill), the watcher
  runs recovery right away. That narrows the window in which readers could load torn files. It never raises into the loop.
- `doctor`: a `chroma_write_guard` check. FAIL while quarantined, WARN when a torn save was restored in 7 days or
  the guard is switched off, PASS otherwise.
- `scripts/chroma_guard.py status|validate|census|clear-quarantine`. Read-only except `clear-quarantine`. It also
  closes hardening-backlog item §7.4: the §4.2 validator now lives in the repo, and a numpy port runs in 0.2 s
  on the live 97.5k-element segment.
- Off switch: `[index] chroma_write_guard = false`.

---

## Why these invariants (reproduced on scratch stores; chromadb 1.5.9)

| # | Experiment (synthetic store, never the live one) | Result |
|---|---|---|
| E1 | When are HNSW files written? | In place (same inode), from inside ordinary write calls, about every `sync_threshold` records. The log is then purged (`automatically_purge: true`). The vector segment's applied position lives in SQLite `max_seq_id` (the pickle's is `None`) |
| E3 | SIGSEGV a writer 0–10 ms into a save (6 trials) | 6/6 live segments **torn** (validator FAIL). After restoring the last save and letting Chroma replay its log: validator PASS and every vector present |
| E3b | SIGKILL across the save window, 0–450 ms (12 trials) | ≤20 ms: torn → restored → census **0 lost**. ≥40 ms: complete save kept → **0 lost** |
| E2 | Restore an *older* save after a newer save | **1,000 records silently lost**, validator PASS |
| E4 | Writer A loads the index, B saves, then A saves | **1,000 of 6,000 vectors silently lost**, validator PASS. Chroma's `get(include=["embeddings"])` then raises `Error finding id` |
| E5 | Long-lived reader, 10,898 queries after another process saved | No file writes: synced segments are written only by writers |
| — | New client's first load of a never-synced segment (header count 0) | Files rewritten with identical bytes. The guard identifies such segments by size so this doesn't look like a save |

E2 and E4 pass structural validation. That is why the guard *prevents* them (invariants 2 and 4) instead of
trying to detect them afterwards. `vector_census()` / `chroma_guard.py census` is the detector for the loss the
validator cannot see.

---

## Part C — investigation findings (for the root-cause decision)

**Premise check (per `DECISION-REVIEW-GUARDRAILS.md`).** The brief's premise ("root cause reproduced and
grounded" as a Chroma 1.5.9 `_upsert` bug, with a poison transcript) comes from the 2026-09-20 handoff body. The Arc
Poison Pill record superseded it on 2026-09-21: a matrix of 300k upserts on the crashing index came back clean, and the payload
hypothesis was refuted. I did not re-run those experiments. The cheap decisive evidence was this:

- **Today's crash population is not the upsert path.** Convmem-related native crashes this boot:
  `convmem unresolved` (a read-only CLI, 09-21), `index --file LATEST.md` (09-23), `file_generation_validate` on a
  pytest scratch store (09-24, Python 3.12), `pytest --collect-only` (09-24), `index --file TEAM-CHARTER` (09-24 15:21,
  the brief's recurrence), and **my own test worker writing 120 sixteen-dimension vectors to a tiny scratch store**
  (09-24 16:44). The faults land at wild addresses inside the Python interpreters (`ip 0`, `0x100000007`), not at a
  stable Chroma frame.
- **CPU concentration.** Across the last six boots, 6 of 12 kernel-recorded segfault CPUs are **CPU 8**. CPU 4 has 3,
  CPU 17 has 2, CPU 3 has 1. CPUs 8–11 are the two **5.4 GHz favoured cores**. Microcode is `0x137` (BIOS 06/12/2026),
  past Intel's Vmin-shift fixes. Those fixes stop further degradation but don't repair an already degraded core.
- **The live index is clean right now** (read-only; no Chroma client opened): structural PASS on both segments, and the
  census shows **0 records without a vector** (knowledge_units 87,175 rows / 86,290 HNSW ids / 933 pending).
  Today's 15:21 crash happened while the HNSW files were not being written (last write 14:13).
- **No newer Chroma exists.** 1.5.9 (2026-05-05) is the latest release on PyPI, so there is no version bump to propose.
  The two software hazards found (E2, E4) are Chroma local-mode design assumptions, not a crash bug, and the guard handles them.

**Recommendation.** Treat the recurrence as platform, pointing at the CPU (a favoured core) more than the DIMMs.
The arc's own tripwire routes that to Ryan's platform path: two-DIMM test, then an Intel RMA under the extended warranty.
The CPU concentration suggests going straight to the CPU question. **Stop rule met:** the #337 bounded stop
rule fired (second native-fault recurrence in the window). This investigation is that reopening, and its answer is
"still platform". Further Chroma-internals work has no decision value until a crash reproduces off CPU 8.

**Optional confirmation (not run; needs Ryan's go, and it produces real crash reports):** run the same
deterministic writer loop pinned with `taskset -c 8` and then `taskset -c 2`, and compare crash counts.

---

## Verification

| Check | Result |
|---|---|
| Simulated native crash mid-write (`test_native_crash_mid_write_leaves_the_shared_index_clean`, SIGKILL: same on-disk effect as a segfault, no core dump) | recovery → structural PASS, census 0 lost, writes resume |
| Deterministic torn save → next guarded write restores (`test_torn_save_is_restored_…`) | restored, 251/251 vectors present |
| Stale writer regression (`test_stale_writer_and_a_newer_save_…`) | guarded: 0 lost. Unguarded control: loss reproduced |
| New guard suite (17 tests) | 20 consecutive full-file runs: 19 green. The one failure was the 16:44 platform segfault of the test worker process, not a guard defect |
| Gate suites (R2b coverage/authority, shadow-writer scans, read-path inventory, canary pins, watch, doctor, circuit breaker) | 387 passed, 2 skipped |
| Normal small transcript, end to end, local models only, isolated `HOME` (no live paths, no provider calls) | `files_processed=1 chunks_indexed=1 units_indexed=1` in 23 s. Restore points created, validator PASS, census 0 lost |
| Full hermetic suite (`GITHUB_ACTIONS=true`, CI-style config) | see the PR description and the Track A transcript for the final count |
| Ruff | clean on new files; no new findings in modified files versus `main` |
| Pylint regression gate (`scripts/pylint_regression_gate.py compare`) | PASS: no new or increased findings |

Pins refreshed by line shift only, with identical snippets verified: three `SHADOW-WRITER-COVERAGE-INVENTORY.json` constructor
sites (`chroma_store.py:81/106`, `chroma_write_store.py:666`), the `watch.py` T0 canary hash, and the R2b inventory
regenerated with `write_v2_inventory_file()` (hash fields only). The read-path inventory classifies the moved
`PersistentClient` constructor (`_new_client`) and the census's read-only SQLite connection as `core-storage`.

---

## Deploying (Ryan)

- It takes effect only after merge, a `.worktrees/runtime-main` fast-forward, and a `convmem-watch` restart.
- The first guarded write copies a restore point of about **342 MB** (knowledge_units ≈ 327 MB, summaries ≈ 15 MB) into
  `~/.local/share/convmem/chroma.write-guard/`. After that, one copy follows each Chroma save, roughly every 1,000
  records, taking about a second. Whether restic should include that directory is left for you; backups were not changed.
- Watch with `python scripts/chroma_guard.py status` and `convmem doctor` (`chroma_write_guard`).
- If it misbehaves: set `[index] chroma_write_guard = false` in the live config (no code revert needed).

---

## What was NOT built (deliberately)

- No poison-transcript replay through the real indexer. It would need DeepSeek calls, the arc already refuted the
  payload hypothesis, and a tiny-store crash makes it moot.
- No reader-side guard (§7.4 reader discipline). Readers never write synced segments (E5).
- No write-ahead journal of our own. Recovery relies on Chroma's log, which E3/E3b showed is lossless for torn saves.
- No doctor silent-loss census. The script has it; wiring it into doctor is an easy follow-up if wanted.
- No chromadb bump (none exists), no re-index, no systemd, backup, hardware or Switchboard changes.
- `tests/test_chroma_write_guard.py` is not added to `tests/ci-critical-invariants.txt`. That is Ryan's call.

---

## Related files

| What | Path |
|------|------|
| Guard, validator, census | `chroma_write_guard.py` |
| Write choke point, stale-client reload | `chroma_store.py` (`_native`, `_reload_client`, `_new_client`) |
| Production wiring and off switch | `chroma_write_store.py` (`open_chroma_for_write`) |
| Watcher recovery | `watch.py` (`recover_chroma_after_abrupt_exit`, `_record_ready_path_failure`) |
| Doctor check | `doctor.py` (`_check_chroma_write_guard`) |
| Operator CLI | `scripts/chroma_guard.py` |
| Tests | `tests/test_chroma_write_guard.py`, `tests/_chroma_write_guard_worker.py` |
| Prior arc record | `docs/inter-model/CLAUDE-2026-09-23-poison-pill-circuit-breaker-handoff.md` (bounded stop rule); arc brief `STATUS-chroma-upsert-crash.md` is only on branch `fix/2026-09-20-chroma-upsert-poison-pill` |
| Superseded brief | `docs/inter-model/KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md`. Its 2026-09-24 refresh exists only as an untracked file in `~/Projects/convmem` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on the pushed branch
- [x] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-chroma-upsert-crash.md` Update Log: that brief is not on `main` (it lives on the unmerged docs branch), so it was not touched
- [x] Branch pushed

**Reviewer (picking up):** start with the "Why these invariants" table, then `ChromaWriteGuard.native_write` and
`reconcile`. The riskiest judgement calls are restoring only on validator FAIL, and quarantining (not restoring)
when this process's own save fails validation.
