# Implementation Handoff: Watch-OOM exposure-probe — POST-MERGE next gate

**Date:** 2026-09-17
**Author:** Kiro (design review lane)
**For:** Ryan (gate decision), then the lane that runs the post-merge memory measurement
**Authorization:** Kiro read-only review authorized by Ryan 2026-09-17; this routing handoff authorizes no new action.

**Arc:** Watch OOM Bound Exposure Probe (Trapdoor Hunt operational follow-up; issue #268; does **not** reopen the closed provenance T3 gate)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `MERGED — awaiting post-merge measurement gate` |
| **PR** | **#305 — MERGED** (squash) 2026-09-17T13:19:09Z |
| **Merge commit** | `ef4a7dd972435de1fbb684cd3aba43076b8232f6` on `main` |
| **Reviewed tip** | `ee979112…` (branch `fix/2026-09-16-watch-oom-bound-exposure-probe-corrective`) — squash source, correctly not an ancestor of `main` |
| **Baseline for §9.7 comparison** | `5c103aa` (PR #303) |
| **Ryan GATE** | Decide whether/when the §9.7 post-merge hermetic memory measurement runs, and by which lane. No watcher/P2 progression without that evidence. |

---

## Consequence first

The corrective is **merged**. The standing exposure-window probe now reads the
projected ten-field metadata iterator on `main` instead of constructing a
full-row `ReadonlyUnitStore`. All three required checks passed before merge:
GitHub Copilot audit PASS, Kiro implementation review PASS (2026-09-17), Claude
advisory PASS. Verified on `main`: `origin/main:doctor.py` contains
`_iter_exposure_window_rows`, `EXPOSURE_WINDOW_METADATA_KEYS`, and the
`getattr(ledger, "build_ledger_index_from_metadata")` call.

**There is no PR left to open.** An earlier handoff described a `READY_FOR_PR`
state; that is now stale and superseded by this file.

---

## What remains (the actual next gate)

Per plan §9.7–§9.8:

1. **Post-merge hermetic end-to-end measurement** — a fresh
   `ingest.index(force_file=...)` comparison of the merged `main` against
   `5c103aa` to determine the remaining memory floor. **Not yet run.** This is
   the immediate next action and it is Ryan-gated (which lane, when).
2. **Live 12.5 GiB watcher OOM remains OPEN.** The merged slice removed the last
   *demonstrated envelope-sized reader on the measured brief path*; the hermetic
   harness peaked ~1.6 GiB and never reproduced the production OOM. Root cause
   unexplained. **Do not declare issue #268 closed on the strength of this merge.**
3. **Watcher exclusions/operation + Arc Codex P2 resumption** (§9.8) — blocked on
   the step-1 evidence plus a separate Ryan decision.

---

## What NOT to do

- Do not treat the merge as closing issue #268 or the live OOM.
- No production access, watcher/systemd operation, config change, source
  re-inclusion, or Arc Codex Gate 0/P2/grant/activation.
- No further code change to the exposure probe, PR #303 brief aggregate,
  `evidence_boost()`, ledger semantics, or the public `collection_metadata_rows()`
  / `ReadonlyUnitStore` API without a new plan.

---

## Related files

| What | Path |
|------|------|
| Execution plan (gate order §9, acceptance criteria) | `docs/plans/EXECUTION-watch-oom-bound-exposure-probe.md` |
| Merged production change | `doctor.py` (`_iter_exposure_window_rows`, `_exposure_window_probe`), `brief.py` (`EXPOSURE_WINDOW_METADATA_KEYS`) |
| C0 golden oracle | `tests/golden/watch-oom-bound-exposure/c0-oracle.json` |
| Probe/projection/fail-soft/cleanup tests | `tests/test_watch_oom_bound_exposure_probe.py`, `tests/test_watch_oom_bound_exposure_c0.py` |
| Superseded prior handoff (READY_FOR_PR — now stale) | `docs/inter-model/KIRO-2026-09-17-watch-oom-exposure-probe-review-handoff.md` |

---

## Picking up checklist (next session)

- [ ] Read this file and plan §9 first
- [ ] Confirm `main` still contains the merged change (`ef4a7dd` ancestry) before acting
- [ ] If running §9.7: build large Chroma fixtures outside the measured subprocess; hermetic temp paths only; keep the 12.5 GiB caveat in the verification record
- [ ] Do not progress watcher/P2 without step-1 evidence + Ryan gate

<!-- Post-merge routing handoff; supersedes the READY_FOR_PR handoff. Authorizes no implementation or operational action. -->
