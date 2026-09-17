# Implementation Handoff: Watch-OOM bounded exposure-probe — post-Kiro-review disposition

**Date:** 2026-09-17
**Author:** Kiro (design review lane)
**For:** Ryan (PR/merge decision), then whichever lane runs the post-merge memory measurement
**Authorization:** Read-only exact-tip review authorized by Ryan, 2026-09-17 (verbal)

**Arc:** Watch OOM Bound Exposure Probe (Trapdoor Hunt operational follow-up; issue #268; does **not** reopen the closed provenance T3 gate)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `READY_FOR_PR` |
| **Branch** | `fix/2026-09-16-watch-oom-bound-exposure-probe-corrective` |
| **Tip SHA** | `ee979112ab8096b3b0b6bd818f758f26dfd691d0` |
| **Push status** | `pushed to origin` (remote branch tip == `ee97911`) |
| **PR** | `not opened` |
| **Baseline** | `origin/main` at `5c103aa` (PR #303); tip is **not** merged |
| **Ryan GATE** | Ryan decides PR creation + squash-merge disposition. No agent opens the PR, merges, or takes operational action. |

---

## Where this stands (consequence first)

Both required AI reviewers now **PASS** on the exact corrective tip `ee97911`:

- **GitHub Copilot** audit lane: PASS (targeted safety/evidence re-audit).
- **Claude** narrow advisory review: PASS.
- **Kiro** implementation review (this session, 2026-09-17): **PASS, PR-ready** — see verdict below.

Nothing is merged. The tip sits on a pushed branch awaiting Ryan's PR/squash-merge
decision. This handoff exists so the next session resumes from reviewed-PASS
state without re-deriving it from chat.

---

## Kiro review verdict (2026-09-17)

**PASS — PR-ready.** Read-only exact-tip review of `ee97911` against baseline
`1be3a98` and PASSed plan `5672ee9`. Detached-HEAD + clean tree confirmed in a
hermetic worktree. Independently verified all six requested focus areas:

1. **Ten-field projection** — `EXPOSURE_WINDOW_METADATA_KEYS` (9 SQL keys) + `id`
   from `embedding_id`, `include_document=False`. Matches plan §5.1. C3 trap test
   asserts requested keys and forbidden-field absence against a fixture that
   deliberately populates forbidden fields.
2. **`getattr(ledger, "build_ledger_index_from_metadata")`** — no default, so a
   missing attribute raises `AttributeError` identically to direct access; the
   name exists (`ledger.py:365`). Chosen to eliminate the pylint `no-name-in-module`
   suppression that `unresolved.py` still carries; `pylint doctor.py brief.py`
   scores **10.00/10** with E0611 enabled. Improvement, not defect.
3. **Iterator cleanup + standing-register fail-soft** — `iter_collection_metadata_rows`
   closes cursor/connection in `finally` (exhaustion, exception, GeneratorExit).
   `_evaluate_standing_rows` converts any probe exception to an advisory due row
   (`probe error: <Type>`); brief still publishes, never partial. `build_ledger_index_from_metadata`
   streams lazily, retains only ledger-bearing rows, never touches `_LEDGER_INDEX_CACHE`.
4. **Hermetic isolation** — path+network denial installed in `prepare_worker()`
   before lazy target imports; guards cover `open`/`os.open`/`io.open`/`Path.open`/
   `sqlite3.connect` (incl. `file:…?mode=ro` URI) + sockets; `denied_exit_code()`
   self-fails on breach; negative-control modes prove guards fire.
5. **Evidence honesty** — `c0-oracle.json` (15 scenarios) generated from the real
   probe; `deleted_not_excluded` proves `deleted` is not an exclusion rule while
   `superseded is True` is (byte-identical to `is_superseded`). `ExposureLedgerParityTests`
   anchors iterator-path == store-path parity.
6. **Superseded/semantic parity** — decision loop byte-identical to baseline
   (diff touches only store-construction lines); `test_doctor.py` rewired to real
   temp Chroma (strengthened).

**Targeted runs at tip:** C0+probe suite 12 passed · `pylint` 10.00/10 (E0611 on) ·
R2b/writer-coverage suite 211 passed · `git diff --check` clean · `compileall`
clean · `open_readonly_unit_store` fully removed from `doctor.py`.
**Not run** (correctly): broad pytest, C6 full-memory host evidence (CI-exempt per plan §6).

---

## What remains for future sessions

Per the plan's gate order (`docs/plans/EXECUTION-watch-oom-bound-exposure-probe.md` §9)
and its residual caveat:

1. **Ryan PR + squash-merge decision** (this gate) — tip reviewed, unmerged.
2. **Post-merge hermetic end-to-end measurement** (§9.7) — a fresh
   `ingest.index(force_file=...)` comparison against `5c103aa…` to determine the
   remaining memory floor. **Not yet run.** Only this evidence may inform step 4.
3. **Live 12.5 GiB watcher OOM is still OPEN.** This slice removed the last
   *demonstrated envelope-sized reader on the measured brief path*; the hermetic
   harness peaked ~1.6 GiB and never reproduced the flat 12.5 GiB production OOM.
   Root cause remains unexplained. Do not declare issue #268 closed.
4. **Downstream, Ryan-gated** (§9.8) — watcher exclusions/operation and resuming
   the Arc Codex P2 packet. Blocked on step 2 evidence + separate Ryan decision.

---

## What NOT to build / do

- No PR, merge, or squash without Ryan's decision.
- No production access, watcher/systemd operation, config change, source
  re-inclusion, Chroma/brief/indexing on live data.
- No Arc Codex Gate 0, P2 packet/grant/digest, or activation.
- Do not change the PR #303 brief aggregate, `evidence_boost()`, ledger relation
  semantics, standing-register policy, or the public `collection_metadata_rows()`
  / `ReadonlyUnitStore` API for other callers.
- Do not add a `deleted` exclusion rule or extend the ten-field projection.

---

## Related files

| What | Path |
|------|------|
| Execution plan (acceptance criteria, gate order, §10 evidence) | `docs/plans/EXECUTION-watch-oom-bound-exposure-probe.md` |
| Production change | `doctor.py` (`_iter_exposure_window_rows`, `_exposure_window_probe`), `brief.py` (`EXPOSURE_WINDOW_METADATA_KEYS`) |
| C0 golden oracle | `tests/golden/watch-oom-bound-exposure/c0-oracle.json` |
| Probe/projection/fail-soft/cleanup tests | `tests/test_watch_oom_bound_exposure_probe.py`, `tests/test_watch_oom_bound_exposure_c0.py` |
| Hermetic isolation helpers | `tests/watch_oom_hermetic_isolation.py`, `tests/watch_oom_exposure_hermetic.py` |
| Prior audit FAIL tip (preserved) | `c9359ae…` on `impl/2026-09-14-watch-oom-bound-exposure-probe` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file on pushed docs branch `docs/2026-09-17-exposure-probe-kiro-review-handoff`
- [x] `LATEST.md` bullet at top with link and resume state
- [x] Arc STATUS: this arc has no `STATUS-*.md`; state captured here + in LATEST
- [x] Corrective branch already pushed (`ee97911` on origin)

**Implementer / next session (picking up):**

- [ ] Read this file and plan §9 before any action
- [ ] Confirm `origin/main` tip and whether `ee97911` has since merged
- [ ] If merged: run the §9.7 post-merge memory measurement; keep the 12.5 GiB caveat
- [ ] Do not progress watcher/P2 without step-2 evidence + Ryan gate

<!-- Reviewed-PASS disposition handoff; authorizes no implementation or operational action. -->
