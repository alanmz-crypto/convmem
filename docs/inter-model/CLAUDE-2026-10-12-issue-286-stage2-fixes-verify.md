# Verify: Stage 2 wedge fixes, round 26 at `d5d10b5`: FAIL; corrective 19 closes R5-F1 and R5-F2, but its capture-error code change weakens the retry hold (Astra's R6-F1, reproduced) and the R2b inventory is stale; corrective 20 (a one-line accounting fix, merge main, regenerate)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `d5d10b5`, Cursor's corrective
19: `8da61de` (read-only retry check before the unchanged shortcut; shortcut revalidates
the live source), `c252b22` (R2b inventory and baseline hash), `d5d10b5` (the read-only
check refuses a non-file state path).
**Input:** Astra's round-6 safety re-audit, **FAIL** (`docs/2026-10-15-issue-286-stage2-fixes-audit-r6`,
`5240cd6`, `docs/inter-model/CODEX-2026-10-15-issue-286-stage2-fixes-audit-r6.md`). My first
draft of this round accepted the change behind R6-F1; Astra's probe showed why that was wrong.
**Method:**
- I read the diff `a89f573..d5d10b5`.
- I ran Astra's round-4 harness (hash `fb7726ec…`) and round-5 harness (hash `80123bdf…`)
  unchanged. I also ran Cursor's copies, Astra's round-3 tests, my retained probes
  (rounds 15–17, 20, 21, 23, 24), the stage-2 wedge tests and the core suites.
- New probes (`tests/test_zz_claude_verify26.py`, appendix), run at the tip and at
  `a89f573`:
  - `z1` calls the read-only check directly for eight retry-state kinds and compares the
    state directory (files, bytes, timestamps) before and after.
  - `z2` runs the shortcut and the full path from fresh fixtures for the same eight kinds:
    three unchanged calls, then one valid append.
  - `z3` rotates the source during capture and checks the refusal and the retry record.
- The full hermetic suite under coverage, the leak census, diff coverage and the static
  check, all at `d5d10b5`, compared with main `458b9f6`.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units are inactive.
Live writes are still only on-demand Track A indexes of Codex session files (new chunks
only).

## Verdict (round 26)

**FAIL.** R5-F1 and R5-F2 are closed, but one change outside the spec weakens the retry
hold (R6-F1, Medium), and the R2b inventory is stale (R6-F2, Low). `main` also moved and now
conflicts. Corrective 20 below fixes R6-F1 with a one-line accounting change I've already
tested, and handles the rest mechanically.

**Closed and verified:**
- **R5-F2:** Astra's four `test_unchanged_preserves_gate_refusal` cases and her natural
  source-hold case pass unchanged.
  - Probe `z2`: for all eight kinds (absent, empty, corrupt, unavailable, prefix cap,
    same-error hold, source-wide hold, hold on another prefix), the shortcut and the full
    path give the same outcome, paid calls, snapshots and retry state on every call.
  - At `a89f573` the same probe diverges for five kinds (corrupt, unavailable, cap,
    same-error, source-wide): the shortcut reports "skipped" and the evidence is erased.
- **R5-F1:** Astra's three `test_shortcut_revalidates_source_after_read` cases (truncate,
  in-place rewrite, replacement) pass unchanged.
- **The check is read-only** (`z1`):
  - It raises `retry_state_unavailable` for corrupt state and for a directory in the
    state file's place.
  - It raises `live_route_refused` for a prefix cap, a same-error hold and a source-wide
    hold.
  - It passes for absent state, empty state and a hold on another prefix.
  - In every case the state directory is unchanged (same files, bytes and timestamps),
    and an absent state directory is never created.
- **Astra's round-4 harness passes unchanged, 7 of 7**, including the original lock
  sequence. Cursor restored `tests/test_zz_codex_audit_r4.py` to it.
- **Astra's round-5 harness: 13 of 14 pass unchanged.** The one failure is
  `test_adapted_lock_sequence_has_correct_reservation_semantics`, which spies the removed
  `reserve=False` gate call (expected; corrective 19 replaced it).
  - Cursor's replacement spies the coordinator's `_check_live_retry_admission_if_needed`
    rather than the module's `check_incremental_retry_gates`. The gate now calls that
    function internally, so spying it would add an event per gate call.
  - The expected sequence, the bytes-unchanged assertion and `summaries ==
    attempts_on_prefix == 2` are as specified. Astra rules on the copy in round 6.
- **Retained checks:** 223 passed (plus the planned failure above) across Astra's rounds
  3–5, my probes from rounds 15–17, 20, 21, 23 and 24, Cursor's copies, the stage-2 wedge
  tests and the core suites.
- **Lock order unchanged:** the check runs inside `run()` under the per-source lock, after
  the pending-transaction branch, with no C1 and no provider call. Kiro's round-4 verdict
  carries.
- **Static check:** clean (undefined-name family) on all 26 changed production files.
- **Diff coverage, corrective 19 (`a89f573..d5d10b5`):** 45 changed executable lines, 2
  never run (`incremental_retry_state.py:281` and `310`). Both are the `return` taken when
  a call has no state paths; no live route reaches them.
- **Leak census:** 0 leaks.

**One change outside the spec, rejected (R6-F1).** `run()` now catches `SourceCaptureError`
from capture, refuses with its own code, and accounts the failure under that code.
- My probe `z3` rotated the source on every call, so the code never changed and the hold
  built normally. I accepted the change on that evidence. That was wrong: the same-error
  and source-wide counters compare codes exactly, so **different** capture errors reset
  them.
- Astra's probe alternates the faults. I reproduced it with her file unchanged (hash
  `4fe4ea54…`):
  - At `d5d10b5`: six calls alternate `source_truncated` and `validated_prefix_mutated`,
    the counters stay at 1, and the seventh, quiet call processes the source and pays 2
    summaries.
  - At `a89f573`: both faults share `unexpected_SourceCaptureError`, the hold sets after 2
    captures, and the quiet call is refused with 0 paid.
- **Removing the catch isn't the fix:** without it, Astra's three round-5 race cases fail.
  The full path lets the error escape as `unexpected_SourceCaptureError`, while the shortcut
  arm refuses with `live_route_refused`.
- **Tested fix:** keep the catch and the specific code as the refusal's diagnostic, but
  account under the old key with `self.last_failure_code =
  classify_incremental_escape(exc)`. In my scratch worktree:
  - Astra's alternating probe matches `a89f573`: 2 captures, held, 0 paid, state kept.
  - Her round-5 race cases pass.
  - 161 tests pass across Astra's rounds 3–6, my probes and the route suites; only the
    obsolete round-5 control fails.
  - `z3` records `unexpected_SourceCaptureError` again.

**Full suite under coverage** (disk-backed worktree, private `--basetemp`, against main
`458b9f6` run the same way, ids without parameters): 98 failed, 3031 passed, 66 skipped, 52
errors. **Five tip-only failures, all from N15.** Leak census: 97 failed, 3030 passed, the
same five tip-only.

## Findings (round 26)

- **R6-F1 (Medium, merge-blocking; Astra's finding, reproduced):** specific capture-error
  codes reset the retry counters, so alternating capture faults never set the hold, and a
  later quiet call does paid work that `a89f573` refuses. Details and the tested fix above.
- **R6-F2 (Low, merge-blocking; found independently by Astra and me): the R2b inventory is
  stale at the tip.**
  - `d5d10b5` changed `incremental_retry_state.py` after the inventory refresh in
    `c252b22`, breaking "inventories after the last code commit".
  - Five R2b identity tests fail at `d5d10b5` (`test_r2b_v2_implementation_revision.py`
    ×3, `test_r2b_v2_corrective_viii.py` ×2); all 18 pass at `c252b22`.
  - Cursor's report missed it: its hermetic run was at `c252b22`, and it reran only one
    probe at `d5d10b5`.
- **Main moved (merge-blocking, not a finding against the branch).** `main` is now
  `c6f0724`: Safe Harbor PRs #391, #392 and #394. Merging it into the branch conflicts in
  four files:
  - `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` and
    `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json`: generated; regenerate them.
  - `tests/test_incremental_jsonl_canary_baseline.py`: recompute the baseline hash.
  - `propose_decision.py`: one import block. Keep the branch's imports (`prepare_` and
    `commit_observation_ingest`, the drift errors, `index_write_flock`) and add main's
    `# pylint: disable=no-name-in-module` comment on the `ledger` import.
  - Main also runs its full suite only through the Safe Harbor launcher
    (`python -I -S -B tests/_safe_harbor_t3_worker.py run-ci`, with the pinned upstream
    restic 0.19.0 in `SAFE_HARBOR_CI_RESTIC_EXECUTABLE`). A plain `pytest tests` stops at
    collection on main.

## Corrective 20 for Cursor

- **R6-F1:** in `run()`, keep the `except SourceCaptureError` branch and its refusal code,
  but set `self.last_failure_code = classify_incremental_escape(exc)` (imported from
  `incremental_retry_state`) instead of `exc.code`. Add Astra's
  `/home/lauer/.kiro/audit-286-r6/harness/test_audit_r6.py` unchanged as
  `tests/test_zz_codex_audit_r6.py`; all 10 must pass. This is the only logic change.
- **Merge, don't rebase:** `git merge origin/main` into the branch (no force-push). Resolve
  the four conflicts as above. Take main's side for everything else.
- Add my round-26 probes (appendix) as
  `tests/test_zz_claude_verify26.py`; all 17 must pass.
- **Inventories last, after the merge commit:** regenerate the R2b and Shadow inventories
  with their generators and refresh the `incremental_jsonl.py` baseline hash. Run the
  inventory tests at that final tip, including `test_r2b_v2_implementation_revision.py`
  and `test_r2b_v2_corrective_viii.py`.
- **Full suite at the final tip through main's launcher**, compared with main `c6f0724`
  run the same way. Take failure ids from the full summary; tip-only target is Z1 at most.
- Push with an explicit refspec; no PR, no merge.

## Next

1. Cursor: corrective 20.
2. Claude round 27 and Astra round 7 on Cursor's final tip, in parallel. Round 27 covers
   the merge resolution, the inventories, Astra's harnesses and my probes, and the full
   suite against main `c6f0724`.
3. If both pass: the PR draft with Kiro's CO-2 and CO-3; Ryan opens and merges.

**Note on Astra's round 6:** her report discloses one out-of-scope `convmem` corpus search
during orientation. It used the local embedding path, not a paid provider; no indexing
followed. Her test runs were isolated.

## Appendix (round 26): probes `tests/test_zz_claude_verify26.py`

```python
"""Claude verify probes, round 26 (corrective 19): the read-only retry check and the revalidating shortcut.

Scratch only: tmp_path HOME, fake providers, no network.
"""

# pylint: disable=protected-access

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import pytest

from tests.test_zz_claude_verify23 import _call, _metrics, _root


def _tree(root: Path):
    if not root.exists():
        return None
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            st = p.lstat()
            out[str(p.relative_to(root))] = (p.is_dir(), st.st_mtime_ns, None if p.is_dir() else p.read_bytes())
    return out


def _seed(state: Path, kind: str, prefix: str, source) -> None:
    state.parent.mkdir(parents=True, exist_ok=True)
    if kind == "absent":
        return
    if kind == "empty":
        state.write_text("{}\n")
    elif kind == "corrupt":
        state.write_text("{truncated\n")
    elif kind == "unavailable":
        state.mkdir()
    else:
        state.write_text(json.dumps({
            "source_path": str(source),
            "prefix_digest": "0" * 64 if kind == "other_prefix" else prefix,
            "error_code": "artifact_write_failed",
            "attempts_on_prefix": 3 if kind == "cap" else 0,
            "consecutive": 2 if kind in {"same_error", "other_prefix"} else 0,
            "source_consecutive": 3 if kind == "source_hold" else 0,
        }))


KINDS = ["absent", "empty", "corrupt", "unavailable", "cap", "same_error", "source_hold", "other_prefix"]
EXPECT = {"corrupt": "retry_state_unavailable", "unavailable": "retry_state_unavailable",
          "cap": "live_route_refused", "same_error": "live_route_refused", "source_hold": "live_route_refused"}


@pytest.mark.parametrize("kind", KINDS)
def test_z1_check_is_read_only(tmp_path, monkeypatch, kind) -> None:
    """The check refuses exactly like the gate and never creates, writes or touches anything."""
    import incremental_jsonl as inc
    from incremental_retry_state import check_incremental_retry_gates
    from watch import source_prefix_digest_for_watch
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    root = _root(source, cfg)
    state = root / "retry_state.json"
    prefix = source_prefix_digest_for_watch(str(source))
    if kind == "absent":
        assert not root.exists()
    else:
        _seed(state, kind, prefix, source)
    before = _tree(root)
    paths = {"transaction": root / "transaction.json", "lock": root / "lock.flock", "retry_state": state}
    from incremental_retry_state import _state_path
    assert _state_path(paths) == state, "probe must hit the real state path"
    try:
        check_incremental_retry_gates(paths, path_key=str(source), prefix_digest=prefix)
        got = None
    except inc.IncrementalJsonlError as exc:
        got = exc.code
    print(f"\nZ1 {kind}", got)
    assert got == EXPECT.get(kind)
    assert _tree(root) == before


@pytest.mark.parametrize("kind", KINDS)
def test_z2_shortcut_matches_full_path_for_every_retry_kind(tmp_path, monkeypatch, kind) -> None:
    """Seeded retry state, unchanged source: three calls, then a valid append and one more call."""
    import incremental_jsonl as inc
    from watch import source_prefix_digest_for_watch
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    original = inc.IncrementalJsonlCoordinator._unchanged_short_circuit_if_applicable
    arms = []
    for shortcut in (True, False):
        with monkeypatch.context() as mp:
            source, cfg, route = _route_fixture(tmp_path / str(shortcut), mp)
            calls = _count_summaries(mp)
            route()
            state = _root(source, cfg) / "retry_state.json"
            assert not state.exists()
            _seed(state, kind, source_prefix_digest_for_watch(str(source)), source)
            mp.setattr(inc.IncrementalJsonlCoordinator, "_unchanged_short_circuit_if_applicable",
                       original if shortcut else (lambda self: None))
            paid = len(calls)
            rows = []
            for i in range(4):
                if i == 3:
                    with source.open("ab") as fh:
                        fh.write(source.read_bytes().splitlines(keepends=True)[-1])
                r = _call(route)
                m = _metrics(source, cfg, calls)
                st = m["state"]
                if isinstance(st, bytes):
                    try:
                        st = {k: v for k, v in json.loads(st).items() if k != "source_path"}
                    except ValueError:
                        pass
                rows.append((r[:2], m["paid"] - paid, m["snapshots"], st))
            arms.append(rows)
    print(f"\nZ2 {kind}\n  shortcut: {[r[:3] for r in arms[0]]}\n  full:     {[r[:3] for r in arms[1]]}")
    assert arms[0] == arms[1]


def test_z3_capture_time_source_error_is_held(tmp_path, monkeypatch) -> None:
    """A source that rotates during every capture is refused, never paid, and held once its errors repeat."""
    import incremental_jsonl as inc
    from incremental_jsonl_formats import FORMAT_SPECS
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    route()
    with source.open("ab") as fh:
        fh.write(source.read_bytes().splitlines(keepends=True)[-1])
    spec = FORMAT_SPECS["jsonl_codex_rollout"]

    def parse(filepath, *, raw=None):
        view = spec.parse_complete_prefix(filepath, raw=raw)
        data = source.read_bytes()
        repl = source.with_suffix(".replacement")
        repl.write_bytes(data)
        repl.replace(source)  # rotate on every parse
        return view

    monkeypatch.setitem(FORMAT_SPECS, "jsonl_codex_rollout", dataclasses.replace(spec, parse_complete_prefix=parse))
    paid = len(calls)
    rows = []
    for _ in range(5):
        r = _call(route)
        m = _metrics(source, cfg, calls)
        st = json.loads(m["state"]) if isinstance(m["state"], bytes) else None
        rows.append((r[:2], m["paid"] - paid, m["snapshots"],
                     st and (st.get("error_code"), st.get("consecutive"), st.get("attempts_on_prefix"))))
    print("\nZ3", rows)
    assert all(r[0][0] == "raised" for r in rows)
    assert rows[-1][1] == 0
    assert rows[-1][2] == rows[2][2], "snapshots must stop growing once held"
```

---

# Round 25: `a89f573`, FAIL (R5-F1, R5-F2), corrective 19 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `a89f573` (unchanged since
round 24).
**Input:** Astra's round-5 safety re-audit, **FAIL** (`docs/2026-10-15-issue-286-stage2-fixes-audit-r5`,
`80e8008`, `docs/inter-model/CODEX-2026-10-15-issue-286-stage2-fixes-audit-r5.md`).
**Method:** I ran Astra's round-5 probes unchanged (`test_audit_r5.py`, hash `80123bdf…`)
in my worktree at `a89f573`, and at `74c8ee7` as the baseline.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units are inactive.
Live writes are still only on-demand Track A indexes of Codex session files (new chunks
only).

## Verdict (round 25)

**Round 24's PASS is withdrawn. Both findings reproduce at `a89f573`:** 8 failed, 6
passed, matching Astra's run. At `74c8ee7` the eight two-arm cases pass (no shortcut
exists there; the six controls that call the new method can't run there).

- **R5-F1 (Medium, new in corrective 17): the shortcut accepts a source that changed after
  its read.** It reads the bytes, checks them, and returns "unchanged" without
  `_revalidate_live_prefix`, which the full path runs after capture. If the file is
  truncated, rewritten in place or replaced between the read and the return, the shortcut
  reports success (`skipped`, no retry record); the full path refuses
  (`SourceCaptureError`) and keeps accounting. No paid call in the raced run.
- **R5-F2 (Medium, inherited): a matching checkpoint bypasses the retry gate and erases
  its evidence.** The shortcut returns before the refuse-only gate, and the router clears
  `retry_state.json` on "unchanged". Corrupt state, a prefix cap, a same-error hold or a
  source-wide hold all disappear when the source matches its checkpoint; with the
  shortcut disabled, the current full path refuses and keeps the bytes. Astra's natural
  case shows real re-admission: three invalid appends set a source-wide hold; restoring
  the committed bytes and calling once clears it; one valid append then pays one fake
  summary. At `74c8ee7` the old unchanged path cleared holds the same way, so this is
  inherited, but corrective 17's own rule (refuse before any work when state demands it)
  now applies to the full path only.

**Why round 24 missed them:** my equivalence probe (`y1`) compared the two arms only with
clean retry state and a quiet source. New rule: equivalence probes for a fast path must
also seed every retry-state kind and race the source between read and return.

**Also from Astra:** Cursor's adapted lock control is valid (one refuse-only event, not a
second reservation); R4-F1 and R4-F2 stay closed; the round-24 shared-helper cases pass.

## Corrective 19 for Cursor

- **Split the gate.** Add a read-only check in `incremental_retry_state.py`
  (`check_incremental_retry_gates(paths, *, path_key, prefix_digest)`): it raises
  `retry_state_unavailable` or `live_route_refused` exactly as the gate does today and never
  writes. `enforce_incremental_retry_gates` becomes check plus reservation; drop the
  `reserve` parameter.
- **R5-F2:** in `run()`, after the pending-transaction branch, call the read-only check
  **before** the unchanged shortcut (replacing today's `reserve=False` call before capture).
  A clean unchanged source still takes no reservation; corrupt or unavailable state and
  every hold refuse with the bytes untouched. The router's clear on "unchanged" then only
  clears state that holds nothing.
- **R5-F1:** the shortcut calls `self._revalidate_live_prefix(snapshot)` as its last step
  before returning "unchanged"; on `IncrementalJsonlError` or `SourceCaptureError` it
  returns `None`, so the full path runs and refuses as today.
- **Tests:** add Astra's `test_audit_r5.py` as `tests/test_zz_codex_audit_r5.py`; 13 of its
  14 tests pass unchanged. The split supersedes
  `test_adapted_lock_sequence_has_correct_reservation_semantics` (it spies the
  `reserve=False` gate call, which no longer exists, and conflicts with Astra's original
  round-4 sequence). Replace only that test with the same check against the split: spy
  `check_incremental_retry_gates` as `check` and the gate as `gate`; expect `check, capture,
  gate, work, account, gate, work, account, gate, gate`; the check never changes the state
  bytes; summaries equal `attempts_on_prefix` equal 2. Astra rules on it in round 6. With the split, Astra's round-4 harness should pass **unchanged**,
  including the original lock-sequence assertion (the read-only check isn't the spied
  gate, and replays go through the pending-transaction branch); restore
  `test_lock_covers_admission_run_accounting_and_release` in
  `tests/test_zz_codex_audit_r4.py` to Astra's original sequence. Keep my round-23 and
  round-24 probes, Astra's round-3 tests, the corrective 12–18 tests and the core suites
  passing. Keep the lock order; no provider call under C1.
- **Inventories last,** then the hermetic full suite against main `458b9f6` (main's failure
  ids from the full `-rfE` summary); tip-only target: Z1 at most.

## Next

1. Ryan: R5-F2 is inherited; corrective 19 fixes it now (fail closed: an unchanged source
   with corrupt retry state refuses instead of deleting the file). Pasting corrective 19
   accepts that disposition.
2. Cursor: corrective 19.
3. Claude round 26 and Astra round 6 on the same tip, in parallel.

---

# Round 24: `a89f573`, PASS withdrawn in round 25 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `a89f573`, Cursor's
corrective 18: `7f8daab` (the unchanged shortcut and the full path share one guard
helper; the shortcut never raises and skips itself for bootstrap grants) and `a89f573`
(R2b inventory and `incremental_jsonl.py` baseline hash, after the last code commit).
**Method:**
- I read the diff `d45ada4..a89f573`. Cursor's `tests/test_zz_claude_verify23.py` differs
  from my round-23 appendix only in line wrapping; I also ran my original copy.
- I ran Astra's round-4 harness unchanged (hash `fb7726ec…`), Astra's round-3 probes, my
  retained probes (rounds 15–17, 20, 21, 23), Cursor's round-4 tests and the core suites
  (`test_upsert`, `test_ledger_document`, `test_monitor`, `test_doctor`,
  `test_incremental_jsonl_live_boundary`).
- New probes (`tests/test_zz_claude_verify24.py`, appendix): `y1` runs five scenarios twice
  from fresh fixtures, once with the shortcut and once with it disabled, and compares the
  outcome, paid calls, snapshot count and retry state after each of four calls; `y2`
  drives the session-identity refusal, which the suite never runs.
- The full hermetic suite under coverage, the leak census, diff coverage and the static
  check, all at `a89f573`, compared with main `458b9f6`.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units are inactive.
Live writes during this round came from on-demand Track A indexes of today's Codex session
files through the incremental route on main (the last one, `rollout-2026-10-15T11-20-29-…`,
started 11:35). Each one only charges for its new chunks. Each commit also rewrites the
5.5 GB `knowledge_units.jsonl` through a temp file (a 4.3 GB `.tmp` was mid-write at
11:39). That's I/O, not a paid call; it belongs with the X-series follow-ups after merge.

## Verdict (round 24)

**PASS.**
- **N13 closed.** Probe `x1` passes: after a legacy re-index replaces the lineage, the
  unchanged source is refused (`rebuild_required:projection_checkpoint_mismatch`), 0 paid
  calls, the retry state is kept.
- **N14 closed.** Probe `x3`: the shortcut no longer raises; the gate decides, and the
  state bytes are stable from the third call. Capture still publishes a snapshot before
  it finds the invalid line; the hold bounds that to 2 (observation below).
- **Shortcut equals full path** (`y1`), call for call over four calls, in all five
  scenarios: plain unchanged ("skipped" four times, no retry state), legacy lineage,
  processed entry dropped, processed entry excluded (each refused as
  `rebuild_required:projection_checkpoint_mismatch`), and transform fingerprint changed
  (`rebuild_required:transform_fingerprint_changed`). 0 paid calls and 0 snapshots
  everywhere.
- **Session identity** (`y2`, the path the suite never runs): a mismatched session-meta
  id is refused on the first run and after a commit, with 0 paid calls and 0 snapshots,
  and the admitted-route log still records `codex_session_identity_mismatch`.
- **Bonus:** the shared helper deletes the call's snapshot before every refusal that
  precedes the unchanged check. A mutated validated prefix (`x2`) now leaves 0 snapshots
  (round 23: 2; before corrective 17: one more per call).
- **Retained checks:** 167 passed across Astra's round-3 and round-4 probes, my retained
  probes, Cursor's round-4 tests and the core suites. The only failure is Astra's lock
  control on sequence shape (two admission checks per attempt since corrective 17;
  unchanged from round 23, every lock assertion holds). Astra should confirm Cursor's
  adapted copy.
- **Lock order unchanged:** the helper reads `processed.json` and the checkpoint under
  the per-source lock, as the full path already did; no C1, no provider call. Kiro's
  round-4 verdict carries.
- **Full suite under coverage** (disk-backed worktree, private `--basetemp`, against main
  `458b9f6` run the same way, ids without parameters): 93 failed, 3015 passed, 66
  skipped, 52 errors. **No tip-only failure** (Z1 didn't flake). Cursor's corrective-18
  comparison agrees (0 tip-only, with 152 main failure ids collected this time).
- **Leak census** (fake live config in a scratch HOME): **0 leaks**; 92 failed, 3014
  passed, 66 skipped, 52 errors; no tip-only failure.
- **Static check:** clean (undefined-name family) on all 14 changed production files.
- **Diff coverage, corrective 18 (`d45ada4..a89f573`):** 62 changed executable lines,
  5 never run in the suite: the identity refusal and its log (`incremental_jsonl.py:2520`,
  `2689`, both run by `y2`), `bootstrap_not_required` (`2540`) and the shortcut's skip for
  bootstrap grants (`2579`), both moved unchanged and only reachable with Ryan's one-shot
  bootstrap grant, and the shortcut's oversized-source `return None` (`2590`, falls
  through to capture's existing refusal). Whole series: 694 lines, 130 never run.
- **Inventories** were regenerated after the last code commit (`a89f573`); the R2b,
  Shadow and baseline tests pass in both suites.

**Observations (not blocking; for the post-merge list):**
- A refusal raised inside capture (`invalid_prefix_encoding`) still leaves the snapshot
  it published; the retry hold bounds it to 2 per source (`x3`). Follow-up: capture should
  delete its own snapshot when it raises.
- Bootstrap refusals now report the captured boundary and record count instead of 0. No
  caller or test depends on the zero (the suite has no tip-only failure).
- Refusals with `rebuild_required:…` codes go through failure accounting on every call
  (`consecutive` 1, 2, 3…) rather than a gate hold; this was already so before corrective
  17, with no paid calls and now no snapshots.

## Next

1. Astra re-audits the exact tip `a89f573` (if not already running), including the
   adapted lock-control copy.
2. If Astra passes: the PR draft, carrying Kiro's CO-2 (R2b owner acknowledgement of the
   `review-bundles/` and `artifacts/` skip prefixes) and CO-3 (verdict "PASS with
   conditions"; cite this round's suite numbers, Z1 as a pre-existing flake). Ryan opens
   and merges.
3. After merge, separate Ryan grants: runtime-main promotion, protocol-surface deploy,
   canary 2 (CO-5, CO-6).

## Appendix (round 24): probes `tests/test_zz_claude_verify24.py`

```python
"""Claude verify probes, round 24 (corrective 18): the pre-capture shortcut must agree with the full path.

Scratch only: tmp_path HOME, fake providers, no network. Each scenario runs twice from a fresh fixture, once with
the shortcut and once with it disabled, and the observable results must match call for call.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_zz_claude_verify23 import _call, _metrics


def _lineage(cfg, value):
    plog = Path(cfg["index"]["processed_log"])
    data = json.loads(plog.read_text())
    for entry in data.values():
        if isinstance(entry, dict) and entry.get("incremental_jsonl_lineage"):
            entry["incremental_jsonl_lineage"] = value
    plog.write_text(json.dumps(data))


def _drop_processed(cfg):
    plog = Path(cfg["index"]["processed_log"])
    plog.write_text(json.dumps({k: v for k, v in json.loads(plog.read_text()).items()
                                if not (isinstance(v, dict) and v.get("incremental_jsonl_lineage"))}))


def _exclude_processed(cfg):
    plog = Path(cfg["index"]["processed_log"])
    data = json.loads(plog.read_text())
    for entry in data.values():
        if isinstance(entry, dict) and entry.get("incremental_jsonl_lineage"):
            entry["excluded"] = True
    plog.write_text(json.dumps(data))


def _fingerprint(cfg, source):
    from tests.test_zz_claude_verify23 import _root

    cp = _root(source, cfg) / "checkpoint.json"
    data = json.loads(cp.read_text())
    data["transform_fingerprint"] = "older-transform"
    cp.write_text(json.dumps(data))


SCENARIOS = {
    "plain": lambda cfg, source: None,
    "lineage": lambda cfg, source: _lineage(cfg, "legacy-reindex-lineage"),
    "processed_dropped": lambda cfg, source: _drop_processed(cfg),
    "processed_excluded": lambda cfg, source: _exclude_processed(cfg),
    "fingerprint": _fingerprint,
}


def _run(tmp_path, monkeypatch, scenario, shortcut):
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    route()
    SCENARIOS[scenario](cfg, source)
    if not shortcut:
        monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_unchanged_short_circuit_if_applicable",
                            lambda self: None)
    rows = []
    for _ in range(4):
        result = _call(route)
        m = _metrics(source, cfg, calls)
        state = None
        if isinstance(m["state"], bytes):
            state = {k: v for k, v in json.loads(m["state"]).items()
                     if k in ("attempts_on_prefix", "consecutive", "error_code")}
        rows.append((result[:2], m["paid"], m["snapshots"], state))
    return rows


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_y1_shortcut_matches_full_path(tmp_path, monkeypatch, scenario) -> None:
    with_shortcut = _run(tmp_path / "a", monkeypatch, scenario, True)
    without = _run(tmp_path / "b", monkeypatch, scenario, False)
    print(f"\nY1 {scenario}\n  shortcut: {with_shortcut}\n  full:     {without}")
    assert with_shortcut == without


@pytest.mark.parametrize("when", ["first_run", "after_commit"])
def test_y2_session_identity_mismatch_refuses_and_logs(tmp_path, monkeypatch, when) -> None:
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    if when == "after_commit":
        route()
    raw = bytearray(source.read_bytes())
    meta_end = raw.index(b"\n")
    uid = source.name.split("-", 6)[-1].removesuffix(".jsonl")[-12:].encode()
    pos = raw.index(uid, 0, meta_end) + len(uid) - 1
    raw[pos] = ord("0") if raw[pos] != ord("0") else ord("1")
    with open(source, "r+b") as fh:
        fh.write(bytes(raw))
    logged = []
    real = inc.IncrementalJsonlCoordinator._emit_codex_admitted_log
    def spy(self, result, **kw):
        logged.append(result.outcome)
        return real(self, result, **kw)
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_emit_codex_admitted_log", spy)
    paid = len(calls)
    rows = [(_call(route), _metrics(source, cfg, calls)) for _ in range(3)]
    print(f"\nY2 {when}", [(r[:3], m["paid"], m["snapshots"]) for r, m in rows], "logged", logged)
    assert len(calls) == paid
    assert all(r[0] == "raised" for r, _ in rows)
    assert "codex_session_identity_mismatch" in rows[0][0][2]
    assert all(m["snapshots"] == 0 for _, m in rows)
    assert "codex_session_identity_mismatch" in logged
```

---

# Round 23: `881c804`, FAIL on N13 (shortcut bypassed the lineage guard), corrective 18 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes`, Cursor's corrective 17:
code `e73d88d`, inventory and canary baseline `881c804`. The pushed tip `d45ada4`
adds only Kiro's round-4 review document on top (no code).
**Method:**
- I read the diff `74c8ee7..881c804` (`incremental_jsonl.py`, `incremental_retry_state.py`,
  the baseline hash, the new `tests/test_zz_codex_audit_r4.py`).
- I ran Astra's seven round-4 checks **unchanged** (hash `fb7726ec…`), Cursor's adapted copy,
  Astra's round-3 probes and my retained probes (rounds 15, 16, 17, 20, 21) at the tip.
- New probes (`tests/test_zz_claude_verify23.py`, appendix): repeated calls after each
  refusal kind, checking paid calls, snapshot count and bytes, and the retry-state bytes
  after every call; run at the tip and at `74c8ee7` as a differential.
- The full hermetic suite under coverage at `d45ada4`, compared with main `458b9f6`;
  diff coverage; the static undefined-name check.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units are inactive.
The live corpus did change since round 22, by design: four of today's Codex session
transcripts (Astra's audit sessions, 02:04 to 06:28) were indexed on demand through the
incremental route on main (Track A), a few chunks each (export +4.7 MB). One of them
(`rollout-2026-10-15T04-16-58-…`) stopped mid-run at 04:46 and left a `PREPARING`
transaction with one prepared artifact and one snapshot; its next index rolls forward and
reuses the artifact. I did not touch it. No further Mirror Crush indexing.

## Verdict (round 23)

**FAIL, on one new finding (Medium). Astra's two round-4 regressions are closed.**

**Closed and verified:**
- **R4-F1:** Astra's `test_corrupt_retry_admission_differential` passes unchanged. Probe
  `x4[corrupt]`: six calls on a corrupt state make 0 paid calls and 0 snapshots, and the
  corrupt bytes stay exactly as written (at `74c8ee7`: the state is rewritten and 2 paid
  calls follow). `x4[unavailable]` (a directory where the state file belongs): 0 paid,
  0 snapshots on every call (at `74c8ee7`: one snapshot per call, growing to 6).
- **R4-F2:** Astra's `test_refusal_snapshot_growth_differential` passes unchanged. Probe
  `x4[same_code]`: 2 paid, 0 snapshots across six calls (at `74c8ee7`: snapshots grow
  by one per held call). `x4[cap]`: 2 paid and one snapshot, the pending transaction's
  own, unchanged across six calls (same at `74c8ee7`).
- Bonus: two refusals outside the gate also stop leaking. A mutated validated prefix
  (`x2`) now stops at 2 snapshots (at `74c8ee7`: one more per call, 6 after six calls);
  invalid UTF-8 appended after a commit (`x3`) leaves none (at `74c8ee7`: 5 after five).
- Astra's five controls: four pass unchanged. The lock control
  (`test_lock_covers_admission_run_accounting_and_release`) fails unchanged only on the
  sequence shape: it expects one admission check per attempt, and corrective 17 now
  checks twice (refuse-only before capture, then the reservation). Cursor's copy updates
  the expected sequence; every lock assertion and the paid-call bound (2) still hold.
  Astra should confirm the adapted copy.
- Astra's round-3 probes, my round 15–17, 20 and 21 probes, and Cursor's ten round-4
  tests: 45 passed (plus the one shape-only failure above).
- **Kiro's lock order is unchanged:** the shortcut and the refuse-only gate run inside
  `run()` under the per-source lock, take no C1, and make no provider call. Kiro's
  round-4 verdict carries to this tip.
- Static check: clean on all 14 changed production files.
- **Full suite under coverage** (disk-backed worktree at `d45ada4`, private `--basetemp`,
  compared with main `458b9f6` run the same way, ids without parameters): 93 failed, 3008
  passed, 66 skipped, 52 errors. **No tip-only failure** (Z1 didn't flake). All 117 of
  Cursor's "tip-only" entries fail on main in this harness too; its main-side id list held
  26 of main's 150 failures.
- **Diff coverage, corrective 17 (`74c8ee7..881c804`):** 39 changed executable lines, 1
  never run (`incremental_jsonl.py:2530`, the shortcut's oversized-source `return None`,
  which then falls through to capture's existing `source_too_large` refusal). Whole series
  since corrective 12: 644 lines, 126 never run (round 21 classified those).
- **Concurrency:** round 20's probe (8 threads, 6 forked processes) still gives 2 paid / 2
  attempts.
- **Live state:** one live write during the run (09:43–09:46): the incremental route on main
  committed one new chunk of the live Codex session `rollout-2026-10-15T06-28-45-…`. That's
  on-demand Track A of a real `~/.codex/sessions` file, not this suite (scratch HOME). The
  leak census moves to round 24 (this round already fails).

## Findings (round 23)

- **N13 (Medium, merge-blocking): the pre-capture "unchanged" shortcut skips guards the
  full path runs, so a refused source reports success and its retry hold is wiped.**
  `_unchanged_short_circuit_if_applicable` (new in `e73d88d`) returns "unchanged" when the
  checkpoint's continuity, boundary and record count match. The full path checks more
  before it may return "unchanged": the D8 lineage guard
  (`_codex_projection_checkpoint_mismatch`: a legacy re-index replaced the path's
  processed lineage), the one-shot bootstrap refusals, eligibility and the session-meta
  identity. The router treats "unchanged" as success and calls
  `clear_incremental_retry_state`.
  - Probe `x1`: commit a source, then replace its processed lineage (as a legacy
    re-index does), then call three times with the source unchanged.
    - At `74c8ee7`: refused (`rebuild_required:projection_checkpoint_mismatch`), then
      held (`wedged_incremental_transaction_…`); the retry state is kept.
    - At the tip: three times "skipped" (success), and the retry state file is deleted.
  - No paid calls either way, and the mismatch surfaces again once the source grows. But
    a safety refusal becomes a silent success and its evidence is erased; this is the same
    class of bug as R4-F1 (an ordering change that weakens a guard).
- **N14 (Low): the shortcut can raise before the gate.** Its prefix parse raises
  `invalid_prefix_encoding` (invalid UTF-8 appended after a commit, probe `x3`) before
  the refuse-only gate, so each call goes through failure accounting and rewrites the
  state (`consecutive` 1, 2, 3, 4, 5) instead of being refused by the gate. No paid
  calls, no snapshots. Cost: one full parse and one state write per call.
- **Observation (not blocking):** a snapshot is still left by refusals that happen after
  capture but before the transaction is written (`rebuild_required:…`, `invalid_state`).
  The refuse-only gate now bounds them to the attempts admitted before the hold (2 in
  `x2`); before corrective 17 they grew on every call. Follow-up: every return before
  `_write_transaction` should delete the snapshot this call captured.
- **Note:** Kiro's round-4 review document (`d45ada4`) was committed on the fix branch
  rather than its own docs branch, so it will ride in the PR. Harmless; no history rewrite
  needed.

## Corrective 18 for Cursor

- **N13:** the shortcut may return "unchanged" only where the full path would. Put the
  post-capture checks that precede the full path's "unchanged" return (bootstrap refusals,
  eligibility, `_codex_projection_checkpoint_mismatch`, the session-meta identity) in one
  helper that both paths call, or have the shortcut return `None` (fall through to the
  full path) whenever `self.bootstrap_existing` is set, the projection check reports a
  mismatch, or the identity check refuses. Accept: probe `x1` passes (refused, retry
  state kept, 0 paid calls).
- **N14:** the shortcut never raises: on any `IncrementalJsonlError` or parse error it
  returns `None`, so the refuse-only gate decides first. Accept: probe `x3` passes (state
  bytes stable from the third call; 0 paid calls; no snapshots).
- **Tests:** add `tests/test_zz_claude_verify23.py` unchanged (all seven pass); keep Astra's
  round-3 and round-4 tests, all retained probes, the corrective 12–17 tests and the core
  suites passing. Keep every provider call outside C1; don't change the lock order.
- **Inventories last:** after the last code commit, refresh the R2b inventory and the
  `incremental_jsonl.py` baseline hash; run the inventory tests; then the hermetic full
  suite. For the comparison, collect main's failure ids from the full `-rfE` summary
  (corrective 17's harness kept only 26 of main's 150 failure ids, which produced the 117
  false "tip-only" entries; all 117 fail on main too); tip-only target: Z1 at most.

## Next

1. Cursor: corrective 18 (small: one helper plus one guard).
2. Claude round 24 and Astra's re-audit on the same new tip, in parallel. Kiro only if the
   lock order changes.

## Appendix (round 23): probes `tests/test_zz_claude_verify23.py`

```python
"""Claude verify probes, round 23 (corrective 17): the new pre-capture unchanged shortcut and repeated refusals.

Scratch only: tmp_path HOME, fake providers, no network. Each probe prints a row so the same file can run at
74c8ee7 (before corrective 17) and at the tip for a differential.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _root(source, cfg):
    import incremental_jsonl as inc

    return Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / inc.source_state_id(
        str(source.resolve()), format_id="jsonl_codex_rollout")


def _metrics(source, cfg, calls):
    root = _root(source, cfg)
    snaps = list((root / "snapshots").glob("*/*")) if (root / "snapshots").exists() else []
    state = root / "retry_state.json"
    return {"paid": len(calls), "snapshots": len(snaps), "snap_bytes": sum(p.stat().st_size for p in snaps),
            "state": state.read_bytes() if state.is_file() else ("dir" if state.is_dir() else None)}


def _call(route):
    import incremental_jsonl as inc

    try:
        result = route()
        return ("ok", result[0] if isinstance(result, tuple) else result)
    except inc.IncrementalJsonlError as exc:
        return ("raised", exc.code, str(exc).splitlines()[0][:90])


def _commit(tmp_path, monkeypatch):
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    route()
    assert (_root(source, cfg) / "checkpoint.json").is_file()
    return source, cfg, route, calls


def test_x1_unchanged_source_after_legacy_reindex_lineage(tmp_path, monkeypatch) -> None:
    """D8 guard: the full path refuses an unchanged source whose processed lineage no longer matches."""
    source, cfg, route, calls = _commit(tmp_path, monkeypatch)
    plog = Path(cfg["index"]["processed_log"])
    data = json.loads(plog.read_text())
    hits = 0
    for entry in data.values():
        if isinstance(entry, dict) and entry.get("incremental_jsonl_lineage"):
            entry["incremental_jsonl_lineage"] = "legacy-reindex-lineage"
            hits += 1
    assert hits == 1, hits
    plog.write_text(json.dumps(data))
    paid = len(calls)
    rows = [(_call(route), _metrics(source, cfg, calls)) for _ in range(3)]
    print("\nX1", [(r, {k: v for k, v in m.items() if k != "state"}, m["state"] is not None) for r, m in rows])
    print("X1 lineage after:", [e.get("incremental_jsonl_lineage") for e in json.loads(plog.read_text()).values() if isinstance(e, dict)])
    assert len(calls) == paid
    assert all(r[0] == "raised" for r, _ in rows), rows


def test_x2_mutated_prefix_repeated_calls_bound_snapshots(tmp_path, monkeypatch) -> None:
    source, cfg, route, calls = _commit(tmp_path, monkeypatch)
    raw = bytearray(source.read_bytes())
    second = raw.index(b"\n") + 1
    end = raw.index(b"\n", second)
    pos = max(i for i in range(second, end) if chr(raw[i]).isdigit())
    raw[pos] = ord("1") if raw[pos] != ord("1") else ord("2")
    with open(source, "r+b") as fh:  # same inode, same length
        fh.write(bytes(raw))
    paid = len(calls)
    rows = []
    for _ in range(6):
        rows.append((_call(route), _metrics(source, cfg, calls)))
    print("\nX2", [(r[:2], m["paid"], m["snapshots"], m["snap_bytes"]) for r, m in rows])
    for _, m in rows:
        print("X2state", m["state"][:200] if m["state"] else None)
    assert len(calls) == paid
    assert rows[-1][1]["snapshots"] == rows[2][1]["snapshots"], "snapshots must stop growing once held"
    assert rows[-1][1]["state"] == rows[3][1]["state"]


def test_x3_invalid_utf8_appended_after_commit(tmp_path, monkeypatch) -> None:
    source, cfg, route, calls = _commit(tmp_path, monkeypatch)
    with open(source, "ab") as fh:
        fh.write(b'{"type":"response_item","payload":"\xff\xfe"}\n')
    paid = len(calls)
    rows = [(_call(route), _metrics(source, cfg, calls)) for _ in range(5)]
    print("\nX3", [(r[:2], m["paid"], m["snapshots"]) for r, m in rows])
    assert len(calls) == paid
    assert rows[-1][1]["snapshots"] == rows[2][1]["snapshots"]
    assert rows[-1][1]["state"] == rows[3][1]["state"]


@pytest.mark.parametrize("kind", ["corrupt", "unavailable", "cap", "same_code"])
def test_x4_repeated_refusal_kinds(tmp_path, monkeypatch, kind) -> None:
    import incremental_jsonl as inc
    import ingest
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    state = _root(source, cfg) / "retry_state.json"
    if kind == "same_code":
        def fail_distill(*_a, **_k):
            raise RuntimeError("scratch distill unavailable")
        monkeypatch.setattr(ingest, "distill", fail_distill)
        monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    else:
        def fail(*_a, **_k):
            raise OSError("scratch prepared failure")
        monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    if kind == "corrupt":
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text("{truncated\n")
    if kind == "unavailable":
        state.parent.mkdir(parents=True, exist_ok=True)
        state.mkdir()  # a directory where the state file belongs
    rows = [(_call(route), _metrics(source, cfg, calls)) for _ in range(6)]
    print(f"\nX4 {kind}", [(r[:2], m["paid"], m["snapshots"], m["snap_bytes"]) for r, m in rows])
    paid = [m["paid"] for _, m in rows]
    assert paid[-1] == paid[2] and paid[-1] <= 4, paid
    assert rows[-1][1]["snapshots"] == rows[2][1]["snapshots"]
    assert rows[-1][1]["state"] == rows[2][1]["state"]
    if kind == "corrupt":
        assert state.read_text() == "{truncated\n"
```

---

# Round 22: `74c8ee7`, round 21 withdrawn, Astra round-4 FAIL reproduced, corrective 17 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `74c8ee7` (unchanged since
round 21).
**Input:** Astra's round-4 safety audit, **FAIL** (`docs/2026-10-15-issue-286-stage2-fixes-audit-r4`,
`d6b93ff`, `docs/inter-model/CODEX-2026-10-15-issue-286-stage2-fixes-audit-r4.md`).
Kiro's round-4 check is pending.
**Method:** I ran Astra's seven round-4 checks unchanged (hash `fb7726ec…`) in my
worktree at `74c8ee7`, and the two failing ones at `7d46e6e` as a control.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units are
inactive and disabled; no further Mirror Crush indexing. R4-F1 is a paid-attempt
bound gap after state corruption, so it matters once the watcher is back on.

## Verdict (round 22)

**Round 21's PASS is withdrawn. Both regressions reproduce at `74c8ee7` and are
absent at `7d46e6e`** (2 failed there vs 2 passed at the control). Astra's five
other checks pass at the tip: the source lock covers admission, run and
accounting; a competitor can't enter during accounting; 8 concurrent callers
with failing accounting still cap at three; success and unchanged runs take no
reservation; export failures clear the cache. All five round-3 findings stay
closed.

- **R4-F1 (High): corrupt retry state is overwritten, and paid work resumes.**
  Corrective 16 moved admission into `run()`, inside the wrapper's error
  handler. A corrupt `retry_state.json` correctly raises
  `retry_state_unavailable`, but the handler then records a failure through
  the permissive `_read`, which treats the corrupt file as empty and writes a
  fresh state with `attempts_on_prefix=0`. The next calls pay again: 2 extra
  fake summaries after one corruption (4 total on one prefix, past the cap).
  At `7d46e6e` the corrupt bytes stay and every call refuses.
- **R4-F2 (Medium): each refused attempt leaves a full source snapshot.** With
  no pending transaction, `run()` now captures and publishes a source snapshot
  before the admission gate; a refusal leaves it with no owner. Four refused
  calls leave 4 snapshots (1,234 bytes each, one full copy of the source per
  refusal). At `7d46e6e`: none.

**Why round 21 missed them:** diff coverage finds changed lines that never run;
these lines run, but in a new order on error paths. The retained corrupt-state
test (`test_q2c_corrupt_retry_state_fails_closed`) checks only the first
refusal, not the bytes afterwards or the next call. New rule for my rounds: for
any reordering of admission, accounting or snapshot steps, probe repeated calls
after each refusal kind and check the state files and disk between calls.

## Corrective 17 for Cursor

- **R4-F1:** separate an admission refusal from a failed admitted attempt. A
  refusal raised by the gate (`retry_state_unavailable`, `live_route_refused`)
  goes straight out, with no failure recording. And
  `record_incremental_retry_failure` must read the state strictly
  (`_read_or_raise_unavailable`): if it's unreadable, leave the bytes untouched
  and raise `retry_state_unavailable`; never replace corrupt evidence with a new
  zero-count state. Recovery stays explicit. Keep the source lock across
  admission and accounting.
- **R4-F2:** keep the unchanged-prefix short-circuit, but run the admission gate
  before the snapshot is captured and published; if the gate needs data from
  the capture, delete only the snapshot this call just captured (never one a
  transaction owns) when admission refuses.
- **Tests:** add Astra's seven round-4 checks as `tests/test_zz_codex_audit_r4.py`
  (the two safety assertions must pass; the five controls unchanged), plus a
  repeated-call test per refusal kind (corrupt state, unavailable state, cap
  reached, same-code hold) that checks the state bytes, the snapshot count and
  the summary count after every call. Keep Astra's round-3 tests, every retained
  probe (rounds 15–21), the corrective-12 to -16 tests, and the upsert,
  ledger-document, monitor, doctor and live-boundary suites passing.
- **Process:** after your **last** code commit, regenerate the R2b and Shadow
  inventories and the baseline hashes, then run the inventory tests and the
  hermetic full suite at that final tip vs main `458b9f6`; tip-only target is
  Z1 alone.

## Next

1. Kiro's round-4 check (pending) is on `74c8ee7`; it stands for the lock order
   unless corrective 17 changes it.
2. Cursor: corrective 17.
3. Claude, round 23, and Astra's re-audit on the same new tip, in parallel.

# Round 21: `74c8ee7`, PASS withdrawn in round 22 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `74c8ee7`, Cursor's
R2b inventory regeneration on top of `928700b` (round 20's condition).
**Method (two additions, after round 19's lesson):**
- **Diff coverage.** The full hermetic suite ran under `coverage` (installed in
  a scratch folder, not the shared environment), tracing the 13 production
  files changed since corrective 12. `diffcov.py` (appendix) lists every
  changed executable line (`0ee6994..74c8ee7`) that no test executes.
- **Static undefined-name check.** pylint's `undefined-variable`,
  `used-before-assignment` and related checks on the same 13 files. Run
  against `7d46e6e`'s `observe.py`, it flags Astra's R3-F2 `NameError` at line
  848, so it would have caught that bug before the audit.
- Plus: the commit is inventory-only; the R2b, Shadow and baseline tests; the
  full-suite comparison against main `458b9f6`.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units are
inactive and disabled; no further Mirror Crush indexing (735 lines).

## Verdict (round 21)

**PASS.**
- `928700b..74c8ee7` changes only `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json`.
  The R2b, Shadow and canary-baseline tests: 66 passed.
- Full suite under coverage: 93 failed, 2998 passed, 66 skipped, 52 errors;
  **no tip-only failure** against main (Z1 didn't flake this run). Cursor's
  report calls a live-boundary test "Z1"; Z1 is
  `tests/test_shadow_activation.py::test_recovery_refuses_replaced_artifact_inode`.
- **Static check: clean** on all 13 files.
- **Diff coverage:** 609 changed executable lines; 125 (20%) never executed.
  Most are guards, early returns, verbose prints and counters. Three groups
  carried real risk, and I ran each with a new probe (appendix,
  `tests/test_zz_claude_verify21.py`):
  - `propose_decision.py:639–653`, `ingest_approved_ledger`'s drift retry:
    `v1` recovers in round 2 (`updated=1`), both embeddings at depth (0, 0);
    `v2` refuses persistent drift cleanly.
  - `refine.py:323–346`, `convmem refine --approve-dedupe` (queue load and
    tombstone under C1): `v3` applies line 1, then `all`; the right units are
    superseded, queue rows are marked applied, no errors. `v4` refuses an
    out-of-range line.
  - `propose_decision.py:556–573`, `ingest_approved_file`: no caller in the
    repository (dead code); left as a note.
  - The rest (repair's second-drift skip, monitor's `drift_refused` and
    `errors` branches, drift-refused raises in the file wrapper, retry-state
    unwritable-directory errors) are short, simple branches; the static check
    covers the name-error class.

## Follow-ups (not merge-blocking)

- `ingest_approved_file` has no caller: delete it or wire it, later.
- X5 (doctor query plan), the cosmetic `skipped` count, X2–X4, #393, Z1, the
  test-double lock branch.

## Next

1. Astra re-audits the exact tip `74c8ee7`; Kiro confirms the lock-order change
   (in parallel).
2. Then the PR draft (CO-2 and CO-3 in its body); Ryan merges.

# Round 20: `928700b`, PASS on safety with one mechanical condition (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `928700b`, Cursor
Composer's corrective 16 (`9324d03`, `928700b`). It answers round 19 (below) and
Astra's round-3 audit (`3af90a3`).
**Method:**
- I read the diff `7d46e6e..928700b` (8 files).
- I ran Astra's seven round-3 probes in both directions: the originals (which
  assert the unsafe behavior) and Cursor's safe-direction rewrite
  (`tests/test_zz_codex_audit_r3.py`).
- I wrote a concurrency probe of my own (appendix): the real route, slowed fake
  summaries so callers pile up on the source lock, a failing prepared write,
  8 threads and 6 forked processes (the real collision is the watcher process
  against a CLI process). Each paid summary is counted in a shared file.
- I ran every retained probe (rounds 15–17), the corrective-6 and -12 tests,
  and the upsert, ledger-document, monitor, doctor, live-boundary,
  add-severity and propose-decision suites.
- I ran the hermetic full suite and the leak census in disk-backed worktrees
  and compared against main `458b9f6`, run the same way.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units are
inactive and disabled; no further Mirror Crush indexing (735 lines). R3-F1, the
paid-cap gap, is closed at this tip (below).

## Verdict (round 20)

**PASS on safety, with one mechanical condition:** regenerate the R2b inventory (below) before the re-audit.
- **R3-F1 (closed):** `maybe_route_incremental` takes the coordinator's
  per-source lock before anything else and holds it through the run and the
  failure accounting. Inside `run()`, the retry gate and reservation run after
  the unchanged-prefix short-circuit, right before the paid transform and
  before a roll-forward; every earlier return is a refusal with no paid work.
  - My probe: 8 threads, 2 paid, persisted attempts 2; 6 processes, 2 paid,
    persisted attempts 2 (the same-code gate refuses after 2; the cap is 3).
  - Astra's original probe now fails for the safe reason: only one reservation
    gets through before the lock serializes the rest.
  - The lock is skipped only when the coordinator's class lacks the lock
    helpers. The one real class (`IncrementalJsonlCoordinator`, constructed at
    `incremental_jsonl.py:2806`) has them, so production always locks; the
    branch exists for a test double (low; a test-side fix would be cleaner).
- **R3-F2 (closed):** repair's drift retry builds a fresh
  `_DocumentAccurateReadonlyStore`; Astra's original probe no longer raises
  `NameError`.
- **R3-F3 (closed):** monitor's re-prepare passes `current.embedding or None`,
  so a skip that drifted into an update embeds outside C1; no `IndexError`.
- **R3-O1 (closed):** the cache clear runs in a `finally` after the store write;
  the stale-cache probe now sees the row.
- **R3-O2 (closed):** `artifacts/` gets the tracked-file rule; the tracked
  writer is reported.
- Astra's two safe controls pass; every retained probe and the named suites
  pass (183 passed with my probe).

**Full suite and leak census** (ids compared without parameters):
- Tip: 99 failed, 2990 passed, 66 skipped, 52 errors. **6 tip-only:**
  - **5 R2b inventory tests** (`tests/test_r2b_v2_corrective_viii.py` ×2,
    `tests/test_r2b_v2_implementation_revision.py` ×3), deterministic (they
    fail the same way alone). The committed inventory records implementation
    identity `3a45709…`; the tip's is `f53ad1b…`. Cause: `928700b` edited
    `incremental_jsonl.py` after `9324d03` regenerated the inventory, and the
    full suite wasn't rerun after `928700b` (Cursor's report says so). The
    rule is still "inventories last".
  - **Z1**, the known ext4 inode flake.
- **Leak census: 0.** Its failures match the tip run.

**Condition (mechanical, Cursor):** regenerate the R2b inventory at `928700b`
(nothing else), run `tests/test_r2b_v2_corrective_viii.py`,
`tests/test_r2b_v2_implementation_revision.py`, the Shadow and baseline tests,
then the full suite at the new tip; tip-only target is Z1 alone.

## Follow-ups (not merge-blocking)

- X5 (doctor query plan), the cosmetic `skipped` count, X2–X4, #393, Z1, and the
  test-double lock branch above.

## Next

1. Cursor: the inventory commit above. Claude confirms the R2b tests and the tip-only list on the new tip.
2. Astra re-audits the new exact tip.
3. Kiro confirms the lock-order change (the source lock now wraps admission;
   C1 placement is unchanged).
4. Then the PR draft (CO-2 and CO-3 in its body); Ryan merges.

# Round 19: `7d46e6e`, Astra's FAIL reproduced; corrective 16 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `7d46e6e` (unchanged
since round 18).
**Inputs:**
- Astra's round-3 safety audit, **FAIL** (`docs/2026-10-15-issue-286-stage2-fixes-audit-r3`,
  `3af90a3`, `docs/inter-model/CODEX-2026-10-15-issue-286-stage2-fixes-audit-r3.md`).
- Kiro's round-3 design review, **PASS with conditions**
  (`docs/2026-10-15-issue-286-stage2-fixes-design-review-r3`, `607102f`): Q3 confirmed;
  CO-1 (revised) and CO-7 resolved; CO-2 and CO-3 for the PR body; CO-5 and CO-6
  for canary 2.
**Method:** I ran Astra's seven round-3 probes unchanged (hash `3d8cab20…`) in my
own disk-backed worktree at `7d46e6e` with my hermetic environment, twice, and
read the code at each finding.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units are
inactive and disabled; no further Mirror Crush indexing. But R3-F1 is a paid-work
bound gap, so it matters to the burn once the watcher is back on.

## Verdict (round 19)

**Round 18's PASS is withdrawn. Astra's three blockers reproduce at `7d46e6e`,
on both runs:**
- **R3-F1 (High): concurrent entrants on one source bypass the attempt cap.** The
  retry gate and reservation (`incremental_jsonl.py:2800`) run before
  `coordinator.run()` takes the per-source lock (`:2483`). Probe: 4 fake summary
  calls, reservations `[1, 1, 1, 1]`, persisted attempts 1, against a cap of 3.
  This is a real pattern: the watcher indexes a session file after its debounce
  while an agent's Track A `convmem index --file` targets the same file. Each
  concurrent entrant pays.
- **R3-F2 (Medium): repair crashes on drift.** The retry branch
  (`observe.py:848`) calls `open_readonly_unit_store`, which isn't imported in
  that function (the local import went with `700b6ba`'s reader change).
  `NameError`; the job aborts.
- **R3-F3 (Medium): monitor turns a drifted skip into an update with an empty
  embedding.** `monitor.py:626` passes `precomputed_embedding=current.embedding`,
  which is `[]` for a row first prepared as unchanged. Chroma raises
  `IndexError` in `update`; the monitor run aborts.
- **R3-O1, R3-O2 (Low)** also reproduce: an export failure after a successful
  store write skips the cache clear; the `artifacts/` skip hides tracked files
  from the R2b scan.
- Astra's two safe controls (post-admission failure recording bounds work;
  refine append survives a real rollback) pass.

**Why rounds 15–18 missed them:** my probes never ran two routes on one source
at once, and never drove repair's retry branch or monitor's skip-to-update
transition through real drift. Kiro's PASS doesn't conflict on any fact: it
confirmed the Q3 design, and these are implementation defects outside it. So no
Sol-High; reproduction settles it.

## Corrective 16 for Cursor

- **R3-F1:** serialize admission per source. Take the coordinator's per-source
  lock (not C1; it already serializes transform work, and provider calls under
  it are fine) before the retry gate and reservation, and run gate, reservation,
  transform and failure accounting inside it. A caller that waited re-checks
  admission after it gets the lock: if the prefix is already processed, it does
  no work; if the cap is reached, it refuses. Accept: Astra's
  `test_concurrent_real_routes_lose_reservations_and_exceed_prefix_cap`,
  inverted into a safe-direction test (same interleaving, real route): at most 3
  fake summaries for one prefix across 4 concurrent callers, and persisted
  attempts equal to the paid attempts.
- **R3-F2:** make repair's retry branch executable (a fresh document-accurate
  reader, as at prepare). Accept: Astra's repair-drift scenario as a safe-direction
  test: the job completes, the drifted row is skipped or repaired once, and the
  remaining pending rows are processed; embedding at depth (0, 0).
- **R3-F3:** a re-prepared row that now needs an embedding must not reuse an
  empty one: pass `current.embedding or None` (or compute it outside C1), or
  refuse cleanly before mutation. Accept: Astra's monitor scenario as a
  safe-direction test: the third run completes or records `drift_refused`; no
  `IndexError`; any embedding at (0, 0).
- **R3-O1:** clear the ledger cache once the store write succeeds, even if the
  export then fails (`finally`). **R3-O2:** apply the tracked-file check to
  `artifacts/` as for `review-bundles/`, with a test.
- **Tests:** add Astra's seven probes as `tests/test_zz_codex_audit_r3.py`,
  rewritten so each asserts the safe behavior (the two controls unchanged).
  Keep every retained probe (rounds 15–17), the corrective-12 to -15 tests,
  and the upsert, ledger-document, monitor and doctor suites passing.
- **Optional:** X5, the indexed document query from round 18.
- **Inventories last;** then the inventory, R2b and baseline tests; then the
  disk-backed full suites at main `458b9f6` and the tip; tip-only list, target
  zero (Z1 is a known flake).

## Next

1. Cursor: corrective 16.
2. Claude, round 20: Astra's scenarios in both directions, a concurrency probe of
   my own, the retained probes, the full suite and the leak census.
3. Astra re-audits the exact tip; Kiro's PASS with conditions carries unless the
   design changes (R3-F1's lock order does touch the route, so Kiro should
   confirm it).

# Round 18: `7d46e6e`, PASS withdrawn in round 19 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-15
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `7d46e6e`, Cursor
Composer's corrective 15 (`5a78e1e`, `7d46e6e`). It answers round 17 (below).
**Method:**
- I read the diff `700b6ba..7d46e6e` (3 files: `chroma_readonly.py`, the R2b
  inventory, and my round-17 probe, added unchanged).
- I ran every retained probe (rounds 15–17), Cursor's corrective-6 and -12
  tests, the upsert, ledger-document, monitor, doctor, add-severity and
  propose-decision suites, and Astra's round-2 probes at the tip.
- I timed the dry-run repair (what `convmem doctor` runs) on round 11's
  synthetic 109,000-unit store with 20 and with 213 decisions, the live
  corpus's count.
- I ran the hermetic full suite and the leak census in disk-backed worktrees
  and compared against main `458b9f6`, run the same way.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units
are inactive and disabled. No further Mirror Crush indexing (the export still
holds 735 Mirror lines). The only live write during this round was Cursor's
own Track A index of its session transcript (6 units). The retry bounds still
hold: Astra's probes show 3 paid attempts, not 6.

## Verdict (round 18)

**PASS.** `unit_document_text` now reads one unit's document with a SQL
lookup instead of iterating the collection in Python.
- Probe `r1`: 1 pass over the units collection for 20 decisions (21 at
  `700b6ba`).
- Dry-run repair on the 109k store: 7.5 s with 20 decisions; 35.3 s with
  213. At `700b6ba` that was about 13 minutes; on main about 10 s.
- Every retained probe passes: `c0`, `d1`–`d3`, `i1`, `l1`, `g1` (round 15);
  `u1` ×4, `n4`, `s1` (round 16); `r1` (round 17). The upsert,
  ledger-document, monitor and doctor suites pass.
- Astra's round-2 probes fail for the same safe reasons as in round 17.

**Full suite and leak census** (ids compared without parameters):
- Tip: 94 failed, 2988 passed, 66 skipped, 52 errors. **1 tip-only: Z1**
  (`tests/test_shadow_activation.py::test_recovery_refuses_replaced_artifact_inode`,
  the ext4 inode-reuse flake; not this branch). Cursor's "0 tip-only"
  matches.
- **Leak census: 0.** Its failures match the tip run.

## Follow-ups (not merge-blocking)

- **X5 (low, performance): doctor's dry-run repair is still about 3.5× main
  on a large corpus.** SQLite plans the new query as a scan of
  `embedding_metadata` (`SCAN em`), so each lookup costs about 150 ms warm
  (8 s once, cold) and grows with the store: 35 s for 213 decisions against
  main's 10 s. Starting from the indexed id fixes it: 213 lookups in 1.05 s.
  ```sql
  SELECT em.string_value FROM embedding_metadata em
  WHERE em.key = 'chroma:document' AND em.id = (
    SELECT e.id FROM embeddings e
    JOIN segments sg ON e.segment_id = sg.id
    JOIN collections c ON sg.collection = c.id
    WHERE c.name = ? AND sg.scope = 'METADATA' AND e.embedding_id = ? LIMIT 1)
  ```
  Can ride on this PR if Ryan wants (one function; `r1` still covers it), or
  follow with X2–X4.
- **Cosmetic:** coalesced duplicate lines aren't reported in the result's
  `skipped` count.
- **Still open from earlier rounds:** X2–X4, #393 (Crush re-pay), Z1 (Ryan's
  call whether its fix rides on this PR).

## Next

1. Astra (audit lane) re-audits and Kiro re-reviews the exact tip `7d46e6e`
   (Kiro rechecks Q3: rows are re-read fresh under the lock, now by targeted
   reads).
2. Then the PR draft (CO-2 and CO-3 in its body); Ryan merges.
3. Separate grants after merge: `runtime-main` promotion, protocol-surface
   deploy, canary 2 (CO-5, CO-6).

# Round 17: `700b6ba`, FAIL; corrective 15 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-14
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `700b6ba`, Cursor
Composer's corrective 14 (`d1a63d4`, `700b6ba`). It answers round 16 (below).
**Method:**
- I read the diff `2ffaf79..700b6ba` (11 files).
- I ran the round-15 and round-16 probes (Cursor added both unchanged),
  Cursor's tests, the upsert, ledger-document and monitor suites, and Astra's
  round-2 probes at the tip.
- I timed the batch commit and the dry-run repair on round 11's synthetic
  109,000-unit store, at the tip and at main `458b9f6`.
- I ran the hermetic full suite and the leak census in disk-backed worktrees
  and compared against main `458b9f6`, run the same way.

## Burn status

**No burn.** The branch isn't deployed; the watcher, refine and monitor units
are inactive and disabled. No further Mirror Crush indexing since round 16
(the export still holds 735 Mirror lines). The retry bounds still hold:
Astra's probes show 3 paid attempts, not 6.

## Verdict (round 17)

**FAIL, on one finding. Every round-16 finding is closed and verified, and
C1 holds are short again: 3 rows commit in under 0.1 s and 20 rows in 0.3 s
on the 109k store (40.7 s for 3 rows at `2ffaf79`).** The one new problem is
outside C1: the fix for the repair test reads each ledger decision's document
with a full scan of the store. `convmem doctor` runs that repair as a dry
run, so on the live corpus (about 213 decisions) doctor would take about 13
minutes instead of about 10 seconds. Every agent session starts with
`convmem doctor`. No paid calls, no lock.

**Closed and verified:**
- **N11:** the cache is cleared after every write and once after a batch;
  validation no longer fills it. `tests/test_upsert.py` and
  `tests/test_ledger_document.py` pass.
- **N9:** validation under C1 uses `get_unit(existing_chroma_id)` for updates
  and skips, and a targeted `active_units_for_ledger_id` (a `where` query, on
  the guarded store's read allow-list) for inserts; the write loop doesn't
  re-validate. Probe `s1`: 0 full scans. `perf16_commit_scans.py` on the 109k
  store: `scans=0`, 3 rows in 0.0 s, 20 rows in 0.3 s.
- **N10:** repeated ledger ids coalesce at prepare, before embedding; the last
  line wins in one round (probe `u1`, all four cases). Earlier lines aren't
  reported as skipped in the result (cosmetic; main counted them as updated).
- **N4:** probe `n4` (the real `convmem add --file --upsert` through a drift
  round) passes.
- **Mocks:** the corrective-6 add test and `test_run_monitor_skips_kiro`
  pass; the drift message `str()`s its ids.
- **Round-15 probes** (`c0`, `d1`–`d3`, `i1`, `l1`, `g1`) and the
  corrective-12 tests pass.
- **Astra's round-2 probes:** six of seven fail for the safe reason (the
  monitor missing-target probe now raises drift); the drift-embed probe still
  breaks on the prepared-row shape, covered by `c0` and `d1`–`d3`.

**Full suite** (disk-backed worktree, private `--basetemp`, compared with
main `458b9f6` run the same way, ids without parameters):
- Tip: 94 failed, 2987 passed, 66 skipped, 52 errors. **1 tip-only: Z1**
  (`tests/test_shadow_activation.py::test_recovery_refuses_replaced_artifact_inode`,
  the ext4 inode-reuse flake from round 13; not this branch). Cursor's
  "0 tip-only" matches once Z1 is set aside.
- No inventory, R2b, Shadow or baseline-hash failures.
- **Leak census: 0** (no test wrote under the fake live roots). Its failures match the tip run, less Z1 and one D1 bwrap test that failed only in the plain run.
- Live state during the runs: no indexing writes (export and `processed.json` unchanged; only the reconcile timer's files moved).

## Findings (round 17)

- **N12 (Medium, merge-blocking): the repair scan reads each document with a
  full-store scan, so `convmem doctor` takes minutes.**
  `chroma_readonly.unit_document_text(chroma_dir, chroma_id)` iterates every
  row of the units collection, documents included, until it finds the id.
  `repair_empty_ledger_documents` calls it once per scanned decision or
  verification, and `_DocumentAccurateReadonlyStore.get_unit` calls it again
  for every lookup through that reader. `doctor.py:1591`
  (`_check_empty_ledger_documents`) runs the repair as a dry run on every
  `convmem doctor`.
  - One lookup on the 109k store: 1.9 s (an early id) to 3.6 s (a late or
    missing id).
  - Dry-run repair with 20 decisions on the same store: 75.6 s at the tip,
    3.8 s per decision, against 10.3 s at main `458b9f6` (one fixed scan).
    Both measured alongside two full suites, so rough.
  - The live export holds about 213 distinct decision ledger ids, so doctor's
    check would take about 13 minutes at the tip and about 10 s on main.
  - Not a burn and not under C1; it's outside the lock. But every agent
    session starts with `convmem doctor` and waits for it.

## Corrective 15 for Cursor

- **N12:** read the documents of all candidate units in one pass, or look one
  up by id with a targeted query (the embedding id, not a full iteration).
  `unit_document_text` must not scan the collection per call, and
  `_DocumentAccurateReadonlyStore.get_unit` must not either. Accept: probe
  `r1` (appendix) passes: on a store with 2,000 units and 20 decisions, the
  dry-run repair reads the documents with at most 2 full iterations of the
  units collection. On the 109k store, a dry-run repair with 20 decisions
  takes about as long as on main (about 10 s).
- **Optional (cosmetic):** report coalesced duplicate lines in the result's
  `skipped` count.
- **Tests:** add probe `r1` unchanged; keep every round-15 and round-16 probe,
  the corrective-12 to -14 tests, and the upsert, ledger-document and monitor
  suites passing.
- **Inventories last,** as before; then the inventory, R2b and baseline
  tests; then the disk-backed full suites at main `458b9f6` and the tip;
  tip-only list, target zero.

## Next

1. Cursor: corrective 15 (small).
2. Claude, round 18: probe `r1`, the dry-run timing, the probes, the full
   suite and the leak census.
3. Then Astra re-audits and Kiro re-reviews the exact tip (Kiro rechecks Q3).

# Round 16: `2ffaf79`, FAIL; corrective 14 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-14
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `2ffaf79`, Cursor
Composer's corrective 13. It answers round 15 (below).
**Method:**
- I read the diff `8d6ee76..2ffaf79` (17 files).
- I ran the round-15 probes (Cursor added them unchanged), Cursor's tests,
  and Astra's round-2 probes at the tip.
- I wrote round-16 probes (appendix), all through real production sessions
  against a scratch config with fake providers:
  - the real `convmem add --file --upsert` command through a drift round;
  - one ledger id on several lines of one file;
  - a count of full-store scans inside the batch commit.
- I timed the batch commit on a synthetic 109,000-unit store (round 11's).
- I ran the hermetic full suite and the leak census in disk-backed worktrees
  and compared against main `458b9f6`, run the same way.

## Burn status

**Not from this branch, but a second Mirror Crush index ran this evening.**
The branch isn't deployed, and the watcher, refine and monitor units are
inactive and disabled. Nothing in this round touches the paid route, and the
retry bounds (R2-F1) still hold: Astra's probes show 3 paid attempts, not 6.
But the live export gained a second block of 263 units from
`~/Projects/SubProjects/Mirror/.crush/crush.db` (after the 472 from the
02:00 first index), the last written at 19:26:16, 159 of them during this
round's suite runs. By the first run's ratio that's about 19 chunks, about
38 DeepSeek calls (an estimate). `processed.json` gained no Mirror entry, so
the run didn't record completion and a repeat pays again (#393). No index
process is running now. The watcher is off and the reconcile timer only
queues work, so it was a manual or agent `convmem index --file`, most likely
from one of the two Mirror Crush sessions (one since 10-11, one since 10-13
21:17); the Track A hold may have reached only one of them. Ryan to check.

## Verdict (round 16)

**FAIL. Every round-15 finding is closed and verified, but the new
validation has two problems.** First, a commit fills the shared ledger-index
cache with the index from *before* its own write, so the next prepare in the
same process sees an existing ledger id as missing and the commit refuses it
as drift: 7 existing upsert and repair tests fail (N11). Second, cost: under
the index write lock (C1), every commit now rebuilds the ledger index from a
full scan of the store, once per row (N9). On the live
store's size (about 110,000 units) that's about 10 s per row. While C1 is
held the watcher waits, so a 3-row file stalls it for about 40 s, and a
100-row file for about 17 minutes. It doesn't pay anything (C1 is a blocking
lock with no timeout, and provider calls are refused under C1), but this PR
exists to remove wedges, so it shouldn't add a long C1 hold. A targeted
lookup takes about 8 ms on the same store.

**Closed and verified:**
- **N1:** the target digest drops the reader-only `document` key. Probe `c0`
  passes: prepared from the real readonly reader, committed to the real write
  store, the skip and the update both succeed.
- **N2:** every prepared row is validated under C1 before any is written, and
  round 2 re-prepares with a newly opened readonly reader. Probes `d1` (the
  caller's real reader), `d2` and `d3` pass.
- **N3:** an insert whose ledger id appeared since prepare raises drift
  (probe `i1`).
- **N4:** the admission context is built once per round. My probe runs the
  real `convmem add --file --upsert` through a drift: two admission rounds,
  exit 0, `updated=1`. With `8d6ee76`'s `convmem.py` and the rest at the tip,
  the same probe fails (exit 1; the single-use context can't be re-entered).
  Cursor's own N4 test builds its own `open_write_commit` and admission
  context, so it would pass against the old code too; my probe should replace
  it.
- **N5:** the hourly cap now breaks out of the loop and the collected
  candidates are appended (probe `l1`).
- **N6:** repair re-prepares outside C1 with a fresh reader and counts a
  drift skip once.
- **N8:** the failure prefix has its own field; the reservation keeps it.
- **g1:** the provider guard refuses `ollama_embed`, `summarize` and
  `distill_with_response` under C1 before any HTTP.
- **Astra's round-2 probes:** five of the seven fail for the safe reason (retry
  state unavailable; 3 paid, not 6; the append waits for the rollback; embed
  at depth (0, 0); a deleted target raises drift). The other two break on the
  new prepared-row format (a `Mock` store can't be scanned; a tuple shape);
  `c0`, `d1`–`d3` and Cursor's tests cover what they tested.

**Full suite and leak census** (disk-backed worktrees, private
`--basetemp`, compared with main `458b9f6` run the same way; ids compared
without parameters, since the main baseline was recorded without them):
- Tip: 102 failed, 2973 passed, 66 skipped, 52 errors. **9 tip-only**, all
  deterministic (they fail the same way run alone, in about a second):
  - **N11, 7:** `tests/test_upsert.py` (`test_upsert_keeps_unit_count`,
    `test_upsert_updates_document_and_embedding`,
    `test_upsert_skips_unchanged_reembed`, `test_file_ingest_twice_stats`,
    `test_upsert_export_uses_atomic_publication`) and
    `tests/test_ledger_document.py` (`test_repair_empty_ledger_documents`,
    `test_upsert_repairs_empty_document_when_metadata_unchanged`).
  - **Mocks, 2:** `test_issue_286_stage2_corrective6_audit.py::test_add_embeds_before_index_lock`
    (the new scan iterates a `Mock` store) and
    `test_monitor.py::MonitorProbeTests::test_run_monitor_skips_kiro` (a
    `MagicMock` ledger id reaches the drift message's `join`).
- **N7 is closed:** no inventory, R2b, Shadow or baseline-hash failures.
- **Leak census: 0.** Its one extra failure is the Z1 inode flake.

## Findings (round 16)

- **N11 (High, merge-blocking): a commit leaves the ledger cache stale.**
  `commit_observation_ingest` clears the process-wide ledger-index cache and
  rebuilds it *before* it writes, then writes and doesn't clear it again. The
  cache is keyed by `chroma_dir`, which the readonly reader shares, so any
  later prepare in the same process reads the pre-write index. Insert then
  upsert the same ledger id in one process: the prepare sees the id as missing
  (`target_digest == "missing"`), and the commit, which rescans, finds it and
  raises drift. Traced on `test_upsert_keeps_unit_count`: after the insert,
  the cache holds an empty index. At `8d6ee76` the insert path never filled
  the cache, which is why these tests passed then. The drift-retry wrappers
  recover in round 2 (re-embedding); a plain `ingest_observation`, repair and
  `ingest_approved_ledger` refuse.
- **N9 (Medium, merge-blocking): every commit rescans the whole store under
  C1.** `commit_observation_ingest` and `commit_prepared_observation_file_rows`
  now clear the ledger-index cache and rebuild it from `units_metadata()`, a
  full metadata scan. A batch scans once up front and again inside each row's
  commit: N+1 scans for N rows, all inside one C1 hold. Monitor, repair and
  approved ingest scan once per observation, each in its own C1 session.
  - Measured on the synthetic 109,000-unit store, run alongside two full
    suites: one scan takes 10.7 s. A 1-row batch held C1 for 20.5 s (2
    scans); 3 rows for 40.7 s (4 scans). At `8d6ee76` the same batch did 0
    scans (it used the stale cache, which was N3).
  - The live corpus was 109.9k units on 10-10. So `add --file --upsert` or an
    approved-file ingest of 100 rows holds C1 for about 17 minutes, and
    monitor adds about 11 s of C1 per observation.
  - C1 (`index_write_flock`) is a blocking `LOCK_EX` with no timeout, and the
    watch path has no lease TTL or watchdog, so the watcher waits; it doesn't
    fail or retry. A stall, not a burn.
  - Probe `s1` counts the scans: 5 for a 4-row batch at the tip; it should
    be 0.
- **N10 (Low): one ledger id on several lines of one file.** Validation passes
  for all of them; the write loop then re-checks each row against the
  batch's own earlier writes. Two copies need a second round (and re-embed);
  three copies are refused after round 2, with the row left at the second
  line's text. Main applies them in one pass and the last line wins (probe
  `u1`; main: `updated=2`, final text "Version 2.").

## Corrective 14 for Cursor

- **N11:** clear the ledger-index cache after every write (each
  `add_unit` or `update_unit` in the commit path, and once after a batch), and
  don't fill the shared cache from validation under C1 (N9's targeted reads
  remove that). Accept: the 7 tests above pass unchanged.
- **Mocks:** update the two tests to the new commit contract (give the mock
  store real `units_metadata`/lookup returns), and make the drift message
  `str()` its ids.
- **N9: validate with targeted reads, once per batch, and don't rescan
  inside the write loop.**
  - For an update or a skip, the prepared target is a chroma id:
    `get_unit(existing_chroma_id)` must still exist, carry the same ledger
    id, not be superseded, and match the prepared digest. No index needed.
  - For an insert, a targeted lookup of active rows with that ledger id
    (`where={"ledger_id": lid}` on the units collection, skipping
    superseded rows the way `units_metadata()` does) must return nothing.
    Add it as a read method on `ChromaStore` and to the guarded store's read
    allow-list (the CO-1 allow-list test will check).
  - Validate every row this way under C1, then write. The write loop
    doesn't re-validate (nothing else can write while C1 is held) and doesn't
    clear or rebuild the ledger-index cache; clear it once after the
    commit.
  - Same function for monitor, repair and `ingest_approved_ledger`.
  - Accept: probe `s1` passes (0 full scans); `perf16_commit_scans.py` on the
    109k store shows `scans=0` for 3 rows.
- **N10:** coalesce repeated ledger ids at prepare, before embedding: the last
  line wins, as on main, and earlier lines are counted (for example as
  skipped). Accept: probe `u1`, all four cases, in one round.
- **Tests:** add `tests/test_zz_claude_verify16.py` (appendix) unchanged;
  `u1` ×4, `n4` and `s1` must pass. Replace Cursor's N4 test with `n4`, or
  make it call the real command. Keep `c0`, `d1`–`d3`, `i1`, `l1`, `g1` and
  the corrective-12 and -13 tests passing.
- **Inventories last,** as before: regenerate after the last edit; run the
  inventory, R2b and baseline tests before the full suite; disk-backed full
  suites at main `458b9f6` and the tip; tip-only list, target zero. Run
  `tests/test_upsert.py`, `tests/test_ledger_document.py` and
  `tests/test_monitor.py` before the full suite too.

## Next

1. Ryan: send the Track A hold to both Mirror Crush sessions (or close the
   older one); then paste corrective 14 into Cursor.
2. Cursor: corrective 14.
3. Claude, round 17: the round-15 and round-16 probes as acceptance, the perf
   probe, the full suite and leak census.
4. Then Astra re-audits and Kiro re-reviews the exact tip (Kiro rechecks Q3).

# Round 15: `8d6ee76`, FAIL; corrective 13 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-14
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `8d6ee76`, Cursor
Composer's corrective 12. It answers round 14 (below).
**Method:**
- I read the diff `0ee6994..8d6ee76` (26 files).
- I ran Astra's eight round-2 probes unchanged at the tip, and Cursor's new
  `tests/test_issue_286_stage2_corrective12.py`.
- I wrote 9 round-15 probes (appendix) for the three classes round 13 missed:
  prepare-to-commit drift, retry-state persistence, and side-file writers. All
  go through real production sessions against a scratch config, with fake
  providers.
- I ran the full suite hermetically in a disk-backed worktree (`env -i`, a
  scratch `HOME`, a private `--basetemp`) and diffed it against round 13's main
  run at `458b9f6`, same method; and the leak census.

## Burn status

**No burn.** The branch isn't deployed, and the watcher, refine and monitor
units are inactive and disabled. **R2-F1, the burn path in the retry bounds, is
closed at this tip** (below).

## Verdict (round 15)

**FAIL. Astra's four blockers are closed, but D's new drift check has a
representation bug that refuses every update or skip of an existing ledger
row, and three smaller gaps remain.** It fails closed: nothing wrong is
written. But monitor, `add --file --upsert` and approved-file ingest stop
working for existing rows.

**Closed and verified:**
- **R2-F1 (A):** the attempt is reserved durably before `coordinator.run()`. A
  failed reservation or failure record raises `retry_state_unavailable`, which
  the CLI maps to the live-route-refused exit, so the watcher holds the file. A
  code-independent bound of 3 attempts per prefix applies. Astra's probes now
  fail for the safe reason: `retry_state_unavailable` instead of
  `artifact_write_failed`, and 3 paid instead of 6. The prefix digest is empty
  only when the file can't be read, before any payment.
- **R2-F2 (B):** approval loads the queue inside C1; `save_dedupe_queue`
  requires C1; semantic dedupe appends under C1 (Astra's probe: the append now
  waits for the rollback). Cursor's writer list covers both dedupe side files.
- **R2-F3 (C):** the runtime guard is in `llm.ollama_embed`, `llm.summarize` and
  `distill.distill_with_response`. My probe calls the real functions under C1;
  all three refuse before any HTTP. Single-record approval now embeds at depth
  (0, 0).
- **R2-F4 (D), for deletes and edits:** commit re-reads the target by ledger id
  and compares digests; a deleted target raises drift instead of exporting.
- **E:** the CO-7 text is scoped to watch roots and cites #393; the CO-1
  allow-list is documented and tested.
- **Astra's probes:** 6 of the 7 unsafe-behavior probes fail for the safe
  reason, and the store-binding probe passes. The seventh, drift-embed, breaks
  on the new prepared-row format instead, so my D probes stand in for it.

## Findings (round 15)

- **N1 (High, merge-blocking): every readonly-prepared commit of an existing
  row is a false drift.** The readonly reader's `get_unit` carries the stored
  document inside `metadata` (a `document` key); the write store's doesn't. The
  documents are equal and every other metadata value matches, but
  `_observation_target_digest` hashes the whole metadata dict, so the two
  digests never match. So:
  - an unchanged row (skip) and a changed row (update), prepared from the
    readonly reader and committed with nothing in between, both raise
    `ObservationIngestDriftError` (probe `c0`);
  - the retry re-prepares through the same kind of reader, so it drifts again:
    monitor counts every existing observation as `drift_refused`;
    `add --file --upsert`, approved-file ingest and `ingest_approved_ledger`
    refuse for any existing ledger id.
  - Cursor's tests didn't catch it: none prepares from the real readonly reader
    and commits to the real write store without a foreign change in between.
- **N2 (Medium): a batch commits row by row, so a later drift leaves a partial
  commit and a second round that trips on the batch's own writes.**
  `commit_prepared_observation_file_rows` writes each row as it validates it.
  If row 2 drifts, row 1 is already written; the retry re-commits row 1 against
  its pre-commit digest (drift again, refused), or adds an inserted row twice.
  Probe `d3` (it currently stops at N1 first). The re-prepare also reuses the
  caller's readonly reader, which is a snapshot taken when it opened, so it
  can't see the change it's retrying for (probe `d1` against `d2`).
- **N3 (Medium): the insert path isn't revalidated.** A row prepared against
  "no target" commits even when a row with that ledger id appeared since: probe
  `i1` ends with two rows for one ledger id. The lookup also goes through the
  process-lifetime ledger-index cache, which can't see a new row.
- **N4 (Medium): `add --file --upsert` can't do a second round.**
  `open_write_commit` re-enters one `admission_file` object, a single-use
  generator context manager (`contextmanager(_admission_steps)(...)`), so round
  2 fails with `RuntimeError` instead of retrying or refusing. With N1, every
  upsert of an existing row reaches round 2. Found by reading `convmem.py`; not
  probed (the admission step needs the restic preflight).
- **N5 (Low): the semantic-dedupe batch drops candidates at the hourly cap.**
  The cap's `return stats` still sits inside the loop, before the new batched
  append, so candidates already counted are lost (probe `l1`: queued 1, file
  empty). Before corrective 12 each was appended at once.
- **N6 (Medium): the empty-document repair re-prepares inside C1 on drift.**
  `observe.repair_empty_ledger_documents` catches drift inside its
  `index_write_flock` block and calls `prepare_observation_ingest` there,
  without a precomputed embedding and with the snapshot reader. So it embeds
  under the lock, or, with the real runtime guard, raises `RuntimeError`; and a
  row skipped for drift is counted as both `skipped` and `missing_source`.
  Monitor and `ingest_approved_ledger` do re-prepare outside C1, but with their
  snapshot readers (N2).
- **N7 (blocks CI, mechanical): line-pinned inventories and pins are stale
  again.** CO-1's new docstring moved `chroma_write_store.py` by about 10 lines
  after the inventories were made: the R2b scan finds unlisted direct
  `ChromaStore` constructor sites `chroma_write_store.py:1133` and `:1198`, so no
  trusted coverage proof can be minted and about 43 R2b authority tests fail;
  the Shadow inventory misses session site `chroma_write_store.py:1095`; the C3
  gate counts 22 writer-session sites against 19 inventoried. Three
  baseline-hash tests still pin the old `incremental_jsonl.py`.
- **N8 (Low): tests on the old API, and one changed meaning.**
  - Four tests mock functions the new paths no longer call
    (`test_add_severity.py` ×2, `test_monitor.py::test_run_monitor_skips_kiro`,
    `test_propose_decision.py::test_ingest_approved_ledger_indexes_one`). Not
    regressions: a spy shows `add --severity critical` still reaches prepare
    with `severity: critical`. Move them to the new API, keeping what they
    assert.
  - `consecutive` changed meaning. The reservation writes the current prefix
    before the failure is recorded, so `record_incremental_retry_failure` now
    counts same-code failures across prefix changes: after a hold, a new prefix
    gets one attempt, not two. That is more conservative, but undocumented, and
    `test_p3_real_wedge_marker_through_cli_parses` now fails (its fake run
    reports a prefix that differs from the file's). Keep the failure's prefix
    in its own field so `consecutive` keeps its meaning, or document the
    change; fix p3's fake digest either way.

**The full suite at `8d6ee76`:** 148 failed, 2917 passed, 66 skipped, 52 errors
(23 min). **54 ids fail only at the tip** (round 13: 1), 1 only at main (the
MCP test, fixed by X1). By cause: 48 are N7 (R2b 43, Shadow 2, baseline
pins 3), 4 are N8's old-API tests, 1 is N8's p3, 1 is
`test_ledger_document.py::test_repair_empty_ledger_documents` (repairs 0: N1,
the false drift, counted as a skip), and Z1 didn't appear. **The leak census:
0 tests.**

## Corrective 13 for Cursor

- **N1:** one canonical form for the target, used at prepare and at commit:
  the document text, plus metadata without reader-only keys (at least
  `document`; compare `ReadonlyUnitStore.get_unit` with `ChromaStore.get_unit`
  for the same rows to find the full set). Test: prepare from the real readonly
  reader, commit to the real write store, nothing between: the skip and the
  update both succeed.
- **N2 and N3, validate first, then write:** under C1, rebuild the ledger index
  fresh (invalidate the process cache first), revalidate **every** prepared row
  before writing any (an insert's target must still be missing), and raise
  drift listing all drifted ledger ids. Round 2 re-prepares the drifted rows
  outside C1 with a **newly opened** readonly reader. Apply the same to
  monitor's commit and `ingest_approved_ledger`.
- **N4:** build the admission context inside `open_write_commit`, once per
  round. Test `add --file --upsert` through a drift: two rounds, no
  `RuntimeError`.
- **N5:** append whatever was collected when the cap stops the job, or count
  only what was appended.
- **N6:** the repair prepares and re-prepares outside C1, like the others, and
  counts a drift skip once.
- **N8:** move the four old-API tests to the new API; keep the failure prefix
  in its own field (or document the new meaning); fix p3's fake digest.
- **N7, last of all:** after every other edit, regenerate the R2b and Shadow
  inventories, update the R2b constructor-site and mutation-sink allow-lists
  and the C3 session-site count, and re-pin the three baseline hashes. Then run
  the inventory, R2b and baseline tests before the full suite.
- **Tests:** add my round-15 probes (appendix) as tests: `c0`, `d1`, `d2`, `d3`,
  `i1`, `l1` must pass as written, `g1` too. Keep Cursor's corrective-12 tests.
- **Suites:** disk-backed full suites at main `458b9f6` and the tip; tip-only
  list, target zero.

## Next

1. Cursor: corrective 13.
2. Claude, round 16; then Astra re-audits and Kiro re-reviews the exact tip
   (Kiro rechecks Q3 with N1 in mind).

# Round 14: `0ee6994`, FAIL (Astra's audit confirmed); corrective 12 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-14
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `0ee6994`, unchanged
since round 13.
**Inputs:**
- Codex (Astra, high), round-2 safety audit, standing in for the Copilot audit
  lane: **FAIL**, four blockers.
  `docs/inter-model/CODEX-2026-10-14-issue-286-stage2-fixes-audit-r2.md` on
  `docs/2026-10-14-issue-286-stage2-fixes-audit-r2` (`bd440dc`).
- Kiro, round-2 design review: **PASS with conditions** (CO-1 revised, CO-2,
  CO-3, CO-7; CO-5 and CO-6 for canary 2).
  `docs/inter-model/KIRO-2026-10-14-issue-286-stage2-fixes-design-review-r2.md`
  on `docs/2026-10-14-issue-286-stage2-fixes-design-review-r2` (`b07f044`).
**Method:** I ran Astra's eight probes unchanged in my own harness (a
disk-backed worktree at `0ee6994`, `env -i`, a scratch `HOME`, a private
`--basetemp`), and read every cited location at `0ee6994`.

### Burn status

**No burn now.** Nothing changed since round 13: the branch isn't deployed, and
the watcher, refine and monitor units are inactive and disabled. But R2-F1 is a
burn path in the branch's own retry bounds, so the watcher must not run this
code until it's fixed.

### Verdict (round 14)

**FAIL at `0ee6994`. Astra's four blockers are real; round 13's PASS is
withdrawn.**
- All 8 of Astra's probes pass in my harness (8 passed, 1.9 s). Seven assert
  the unsafe behavior; the eighth checks the store binding. Each reproduces.
- Every cited location reads as Astra describes (below).
- **Why round 13 missed them:** my probes checked each corrective's own items
  and the suite diffs. I didn't probe the gap between preparing a write and
  committing it, a retry-state write that fails, or a sidecar writer outside
  C1. Round 15 runs Astra's probes, flipped, plus those three classes.
- **Kiro's PASS is design-level and stands for the C1/C2 mechanism.** One
  factual statement in it doesn't hold at this revision: Q3 says observe's
  commit "re-read[s] rows fresh under the lock". R2-F3 and R2-F4 show it
  doesn't, by executable probes. I recommend no Sol-High: the facts are
  settled by reproduction, not opinion, and both reviewers re-review the
  corrected tip. Ryan decides.

### Findings confirmed (Astra's numbering)

- **R2-F1 (High, burn): retry accounting fails open.**
  - `incremental_retry_state.record_incremental_retry_failure` catches
    `OSError` from the state write and returns `False`. The caller treats that
    as an ordinary first failure. So when the state can't be written (a
    read-only file, a full disk), every attempt pays again and nothing counts.
    Admission (`_ensure_retry_state_available`) only checks that an existing
    file is readable.
  - Both `consecutive` and `source_consecutive` reset when the error code
    changes, so alternating failures never reach a hold (Astra: 6 paid in 6).
  - Probes: `test_readonly_retry_file_allows_unbounded_paid_retries` (5 paid,
    state bytes unchanged), `test_alternating_failures_reset_both_paid_retry_counters`.
- **R2-F2 (High): foreign dedupe work can still be lost.**
  - `refine.job_semantic_dedupe` appends to `dedupe_queue.jsonl` without C1
    (`refine.py:663`). A locked rollback that reads the queue, then replaces
    it, erases an append that lands in between.
  - `_apply_approved_dedupe_impl` loads the queue (`refine.py:318`) before
    taking C1 (`:338`) and saves that snapshot (`:363`), dropping any append
    made in between, by refine or by ingest.
  - Probe: `test_refine_queue_append_is_lost_by_locked_rollback`.
- **R2-F3 (Medium): embedding still runs under C1 and a write session.**
  - The batch commit (`observe.ingest_observation_file` with `prepared_rows`)
    calls `ingest_observation` again. For a row prepared as unchanged
    (embedding `None`) that changed before commit, that call embeds under the
    lock. Reached from `add --file --upsert` (`convmem.py:510-529`) and
    approved-file ingest (`propose_decision.py:569-586`).
  - `propose_decision.ingest_approved_ledger` (`:611-626`) prepares and embeds
    inside C1 and the session; the empty-document repair (`observe.repair_empty_ledger_documents`, `observe.py:410-466`)
    has the same shape.
  - Probes: `test_unchanged_preparation_then_drift_embeds_inside_real_c1_session`,
    `test_approved_single_ledger_embeds_under_c1` (both record depths (1, 1)).
- **R2-F4 (Medium): monitor commits a stale decision.**
  - `observe.commit_observation_ingest` trusts the prepared `existing_chroma_id`
    and the `skipped_unchanged` flag from the readonly snapshot. It doesn't
    re-read the target under C1. If the row was deleted, `update_unit` changes
    nothing, yet the result says `_upserted` and the export gets the line. A
    skipped row may have changed or gone.
  - Probes: `test_monitor_prepared_update_exports_a_row_deleted_before_commit`,
    `test_prepared_monitor_update_never_rechecks_missing_target`.

### Corrective 12 for Cursor

Production code changes this time. Keep every provider call (summarize,
distill, embed, LLM) outside C1 and outside any Chroma write session.

- **A. Retry accounting that fails closed (R2-F1).**
  1. **Reserve before paying.** In `enforce_incremental_retry_gates`, after the
     gates pass and before any transform work, durably record the attempt
     (atomic write, as `_write` does): a code-independent
     `attempts_on_prefix` (+1 for the same `prefix_digest`, reset to 1 when it
     changes) and the pending transaction id. If that write fails, raise
     `retry_state_unavailable` before any paid work.
  2. **Bound attempts whatever the error.** Refuse (`live_route_refused`, a
     hold) when `attempts_on_prefix` reaches 3 without a success on that
     prefix, whatever the codes. Keep the same-code gates.
  3. **No silent write failures.** `record_incremental_retry_failure` must raise
     `retry_state_unavailable` on `OSError`, never return `False`. On success,
     a failed clear warns; it must not turn a committed success into a failure.
  4. The watcher holds the file on `retry_state_unavailable`, as it does for a
     corrupt state. Confirm it and test it.
- **B. Every dedupe sidecar write under C1 (R2-F2).**
  1. `job_semantic_dedupe`: collect candidates with no lock (the vector reader
     closed as now; the limiter decision before), then take C1 from the live
     config once and append them all.
  2. `_apply_approved_dedupe_impl`: load the queue, and resolve the target,
     inside the C1 block.
  3. List every writer of `dedupe_queue.jsonl` and
     `ingest_duplicate_suppressions.jsonl` (file:line) and show each holds C1.
- **C. No embedding under the lock (R2-F3).**
  1. Commits never embed. The batch path commits prepared rows through
     `commit_observation_ingest`; it never calls `ingest_observation` with
     `embedding=None` under the lock.
  2. On drift (D below), callers release C1 and the session, re-prepare the
     drifted rows outside (embedding there), and commit again: at most 2
     rounds, then refuse with a clear error. Applies to `add --file --upsert`,
     approved-file ingest, `ingest_approved_ledger` and the empty-document
     repair; the last two must prepare before taking C1.
  3. **Runtime guard:** `llm.ollama_embed`, `llm.summarize` and `distill.distill_with_response` (the distill entry
     point) raise if `index_write_lock_depth() > 0` or
     `production_chroma_store_session_depth() > 0`. If any production path
     trips it in the full suite, stop and report it; don't weaken the guard.
- **D. Commits revalidate under C1 (R2-F4).**
  1. A prepared observation records what it decided against: the target id and
     a digest of the target's document and metadata (or "no target").
  2. `commit_observation_ingest` re-reads the current target by ledger id from
     the write store under C1. If it's missing, or its digest differs, or a
     `skipped_unchanged` row changed or vanished, raise a drift error (handled
     as in C2). Never update a missing row; never resurrect a purged one.
  3. Set `_upserted` and write the export line only after the store mutation is
     confirmed.
  4. Monitor (`monitor.py:394`, `:594-598`): on drift, release, re-prepare
     outside, retry once, then count the observation as `drift_refused` in its
     result. The monitor run itself doesn't crash.
- **E. Kiro's low-effort conditions.**
  1. **CO-7:** scope the Track A text's auto-capture claim to transcripts
     **under the watch roots**, and say Crush databases outside a watch root
     aren't deferred (#393). Edit the same protocol sources `15663db` changed;
     no deploy.
  2. **CO-1 (revised):** list `_IndexWriteGuardedChromaStore`'s read allow-list
     with a one-line reason each method is read-only, and add a test that fails
     when a public `ChromaStore` method is neither on the list nor guarded.
- **Tests:** turn Astra's seven unsafe probes (the audit's appendix) into tests
  of the safe behavior; keep the store-binding probe. Add the A3 crash case:
  an exit after paying and before recording still counts the reservation.
- **Inventories last:** this changes production code, so re-pin baseline hashes
  and regenerate the R2b and Shadow inventories after every other edit, as in
  corrective 10.
- **Suites:** full hermetic suite in disk-backed worktrees (`git worktree add
  --detach` on a non-tmpfs path) with a private `--basetemp`, at main
  `458b9f6` and at your tip. List every tip-only failure id; target zero (flag
  Z1, the inode flake, if it appears).

### Next

1. Cursor: corrective 12.
2. Claude, round 15: Astra's probes flipped, drift, persistence-failure and
   sidecar-writer probes of my own, the disk-backed suite diff and the census.
3. Astra re-audits and Kiro re-reviews the exact corrected tip. Kiro rechecks
   Q3.
4. Then the PR draft (Kiro's CO-2 and CO-3 go in its body), and Ryan's grants.

# Round 13: `0ee6994`, PASS withdrawn in round 14 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-14
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `0ee6994`, Cursor
Composer's corrective 11. It answers round 12 (below).
**Method:**
- I read the diff `41561ef..0ee6994`: one test file, 7 lines.
- I ran corrective 11's acceptance in a disk-backed scratch worktree: the D1
  file followed by `verify8b` and `verify8d`.
- **New this round:** every full-suite run used a disk-backed worktree (ext4,
  under `~/.cache`) with a private `--basetemp`, so the D1 live-diagnosis
  tests run as they do in Cursor's checkout and in CI. Earlier rounds used
  tmpfs worktrees, where 27 of the 41 D1 tests error at setup.
- I ran the full suite hermetically (`env -i`, a scratch `HOME`, no API keys,
  `tests/test_index_loud_failures.py` skipped) at `0ee6994` **and at main
  `458b9f6`, fresh, same method**, so the comparison is like for like.
- I ran the leak census at `0ee6994` the same way.
- I ran every probe round, Codex's round-7 probes and Cursor's #286 files.
- I compared mtimes and sizes across the live data root before and after.

### Burn status

**No burn. This branch isn't deployed, and the watcher, refine and monitor
units are all inactive and disabled.**
- **My runs:** none can reach a paid provider. Providers are faked and the
  environment has no keys. Everything ran in scratch `HOME`s.
- **Live data root during round 13:** only the reconcile timer (`chroma/`,
  `source_reconciliation.json`, `writer_attestations/`). The export didn't
  grow; no index ran. The Crush session behind #393 is on hold.
- **The watcher burn path, at this tip:** unchanged from round 11 and still
  holding.
- **Canary 2 and #393:** of the 47 Crush databases ConvMem knows, 1 lies under
  a live watch root and is watchable (3 chunks). So a re-enabled watcher would
  re-pay at most that one database on each change. Small, but known.

### Verdict (round 13)

**PASS. Ready for the Astra audit and the Kiro review on `0ee6994`.**
- **Y0 is fixed.** `0ee6994` is byte-identical to the round-12 diff (same blob,
  `b0db98a..105ebb9`). In a disk-backed checkout, the D1 file followed by the
  three probes passes. The only D1 failures are 3 `bwrap` tests that fail the
  same way at main in my scratch `HOME`.
- **The full suite, disk-backed, tip against main:** 142 failure ids each.
  **No failure comes from this branch.** One id fails only at the tip, and it
  is a pre-existing filesystem flake in a test the branch doesn't touch (Z1);
  one fails only at main (the MCP test, fixed by X1).
- **The leak census:** **0 tests** change a file under the fake user's data
  root or default data dir, now with the D1 tests running.
- **Probes:** 90 passed (the 89 of round 12 plus the #393 Crush probe), and
  the same 11 expected failures.

### Findings (round 13)

- **Z1 (low, older than the branch, another arc's test): an inode-reuse flake.**
  `tests/test_shadow_activation.py::test_recovery_refuses_replaced_artifact_inode`
  unlinks a file, writes a replacement and asserts the replacement has a new
  `(st_dev, st_ino)`. ext4 can hand the freed inode number straight back, so
  the precondition fails: `assert (66306, 37364686) != (66306, 37364686)`. It
  failed at the tip in both disk-backed full runs (hermetic and census) and not
  at main; alone it passes 10/10 at both, and the files before it don't
  reproduce it. The branch changes neither the test nor
  `shadow_activation.py`. CI's runner is ext4 too, so it can flake there at
  main or at the tip. **Fix (proved in scratch, 5 lines):** keep the original
  open across the unlink, so its inode can't be reused:
  ```diff
  -    fixture["ledger"].unlink()
  -    _write_private(fixture["ledger"], "replacement\n")
  -    replacement_inode = fixture["ledger"].stat().st_ino
  +    # Hold the original open so its inode can't be freed and reused by the replacement.
  +    with fixture["ledger"].open("rb"):
  +        fixture["ledger"].unlink()
  +        _write_private(fixture["ledger"], "replacement\n")
  +        replacement_inode = fixture["ledger"].stat().st_ino
  ```
  Patched, it passes 10/10 alone and its file passes 32/32. It belongs to the
  Shadow Ledger arc's tests, so it's Ryan's call whether it rides on this PR
  (if CI trips) or lands separately.
- **Z2 (low, for Kiro): the Track A protocol text overstates the watcher's
  Crush coverage.** `15663db` tells agents that while the watcher runs it
  "captures Codex, Kiro, Cursor, Copilot, and Crush transcripts automatically",
  so `index --file` on those paths is deferred. For Crush, 1 of 47 databases
  is under a watch root; the rest are never deferred, and each `index --file`
  on them re-pays the whole database (#393). The behavior is safe (it indexes
  rather than silently skipping), but the text should say "under the watch
  roots".
- **Follow-ups after the merge, unchanged:** X2 (the readonly reader loads
  everything when it opens: plain `add` 0.7 s → 4.8 s on a 109k-unit store),
  X3 (`chroma_dedupe` undo snapshots carry document text), X4 (two `pass`
  bodies), #393 (Crush re-pay).

### Test results (round 13)

| Run (disk-backed worktrees, private `--basetemp`) | Result |
|---|---|
| Hermetic full suite, `0ee6994` | 95 failed, 2961 passed, 66 skipped, 52 errors (23 min) |
| Hermetic full suite, main `458b9f6`, same method | 95 failed, 2900 passed, 66 skipped, 52 errors (22 min) |
| Failure ids, tip only / main only | 1 (Z1, pre-existing flake) / 1 (MCP test, fixed by X1) |
| Leak census, `0ee6994` | **0** tests |
| D1 file + `verify8b` + `verify8d` | the 3 probes pass; 3 `bwrap` D1 tests fail, as at main |
| Z1 test alone, ×10 | tip 0/10, main 0/10 failed; patched 0/10 |
| All probe rounds + Cursor's #286 files | 90 passed, 11 failed (all expected) |

### Review focus (round 13)

The Codex audit (round 7) and the Kiro review (round 6) looked at `c7072fc`.
Correctives 6 to 11 changed a lot since. Both reviews should look at
`git diff origin/main...0ee6994`, weighted toward what changed after `c7072fc`
(`git diff c7072fc 0ee6994`).

**For the Astra audit (safety and isolation):**
1. **C1 is bound to its store.** `purge_locks.index_write_flock` records the
   `chroma_dir` it was taken for; the guarded store's
   `require_index_write_lock_held(chroma_dir=...)` compares canonical paths.
   `_refine_write_scope`, monitor's commit and `_apply_retirements` take C1
   from the live config. Can any production writer of summaries, units or the
   export write without C1, or under a C1 taken for another `chroma_dir`?
2. **The readonly reader.** Refine, monitor and its dry run, `add`,
   `add --file` and `ingest_approved_file` read through
   `chroma_readonly.open_readonly_unit_store` (SQLite `mode=ro`, no Chroma
   system). Can a write be built from a readonly row (stale metadata, the
   `document` key) instead of a fresh write-store read?
3. **Paid work outside locks.** Is any provider call (summarize, distill,
   embed, LLM) made while C1 or a Chroma write session is held? Check refine,
   monitor, `observe.prepare_observation_ingest` / `commit_observation_ingest`
   and `semantic_dedupe`.
4. **Burn safety.** Your round-7 findings F1 to F5 and O1, O2: confirm each
   stays fixed at this tip. Can any failure path re-run paid transform work in
   a loop?
5. **Hermeticity.** The `tests/conftest.py` autouse fixture and the D1 test fix:
   can any test reach the live `HOME`, live data paths or the network, or leave
   process-wide patches behind?
6. Out of scope, already known: #393, Z1, X2 to X4.

**For the Kiro review (design):**
1. Is binding C1 to its store (the lock remembers `chroma_dir`; the guard
   compares canonical paths; a symlinked `chroma_dir` is accepted) the right
   design?
2. The readonly reader trades open-time cost for not holding a Chroma system
   across writes (X2: plain `add` 0.7 s → 4.8 s, 151 → 617 MB on a 109k-unit
   store). Accept as is with X2 as a follow-up, or must X2 land before the
   merge?
3. Is `observe`'s prepare/commit split the right boundary for monitor?
4. Z2: should the Track A protocol text be corrected in this PR?
5. Is anything in the round-6 design (C1 window, C2 recovery, relaxed
   invariants) contradicted by correctives 6 to 11?

### Next

1. A fresh Codex (Astra, high) audit and a fresh Kiro review on `0ee6994`, in
   parallel.
2. If both pass: a PR draft with the census and the round history. Main has
   moved to `fdc8da7`; bringing it in is Ryan's call at PR time. Ryan decides
   whether Z1's 5-line fix rides on this PR.
3. Ryan's PR and merge; the docs branch gets its own PR.
4. Separate Ryan grants: the `runtime-main` promotion, the protocol-surface
   deploy, and canary 2.
5. Follow-ups after the merge: X2 to X4, #393, and Z1 if it didn't ride along.

# Round 12: `41561ef`, FAIL; corrective 11 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-14
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `41561ef`, Cursor
Composer's corrective 10. It answers round 11 (below).
**Method:**
- I read the diff `d2abcbe..41561ef`: three files, no production code.
- I compared both committed writer inventories with my own scratch
  regeneration from round 11.
- I ran every earlier probe round, Codex's round-7 probes, Cursor's #286
  test files, and the inventory and MCP tests.
- I ran the full suite hermetically at `41561ef` (`env -i`, a scratch `HOME`,
  no API keys, `tests/test_index_loud_failures.py` skipped) and compared it
  with round 8's main run at `458b9f6`, same method.
- I ran the leak census again: the full suite with a fake live config in a
  scratch `HOME`, logging every test that changes a file under that config's
  data root or the default data dir.
- I read Cursor's own junit results for its three tip-only failures, ran the
  full suite in a Cursor-like environment (`~/.local/bin` on `PATH`,
  `TMPDIR=/tmp`) with a scratch plugin that logs the per-thread writer-lease
  and index-lock state after each test, then reproduced and bisected the
  failures in a disk-backed scratch worktree.
- I wrote one scratch probe (appendix) for a burn path outside #286: Crush
  databases. It is now issue #393.
- I compared mtimes and sizes across the live data root before and after my
  runs, and checked running index processes from metadata only.

### Burn status

**No burn loop. This branch isn't deployed, and the watcher, refine and
monitor units are all inactive and disabled.**
- **My runs:** none can reach a paid provider. Providers are faked and the
  environment has no keys. Everything ran in scratch `HOME`s.
- **Live data root since round 11:** agents' own Track A runs from
  `runtime-main` (main's code, not this branch). By the export's
  `source_path`, the growth is: a Crush session's first index of its
  project's database (02:00 to 02:28 CDT; 34 chunks, 472 units, about 68 paid
  calls; it held a connection to the DeepSeek API while it ran), two Codex
  rollouts from 01:56 and 01:58 through the incremental route, and two Claude
  sessions from another project. Also the reconcile timer and the 00:16
  restic backup. Nothing from my runs.
- **A burn path outside #286, now issue #393:** indexing a changed Crush
  database pays for every chunk again. Crush databases go through the legacy
  single-file route. Any new message changes the file hash, and the next
  `index --file` re-chunks the whole database and calls summarize and
  distill for every chunk; duplicates are dropped only after the payment. My
  probe `test_changed_crush_db_repays_every_chunk` (appendix; real
  `ingest.index`, counting fakes) gives 3 paid on the first index, 0 when
  unchanged, and 4 after one appended message: all 3 old chunks again plus
  the new one. This branch doesn't change it: its deferral only applies to
  watched paths while the watcher runs. Ryan is holding that Crush session's
  Track A; #286 links to #393.
- **The watcher burn path, at this tip:** unchanged from round 11 and still
  holding.
- **Outside this arc:** the external restic backup has failed every run since
  2026-10-12 (exit 10, which usually means the repository isn't reachable).
  The local backup runs.

### Verdict (round 12)

**FAIL, on one test-only item (Y0). It is older than this branch. Everything
else passes.**
- **Corrective 10 is done:** X0 (the inventories) and X1 (the MCP test's
  environment) are fixed exactly as asked.
- **My hermetic suite meets both targets:** 0 tip-only failure ids against
  main, and 0 tests in the leak census.
- **Cursor's three "suite-order flakes" are real, and CI would see them.**
  Cursor reported `test_zz_claude_verify8b.py` ×2 and
  `test_zz_claude_verify8d.py` ×1 failing in its full runs only. Round 11 said
  they didn't reproduce for me. The reason: my worktrees live on tmpfs, so 27 of
  the 41 D1 live-diagnosis tests error at setup in my runs
  (`scratch_not_disk_backed:tmpfs`), the bootstrap test among them. In a disk-backed checkout, Cursor's and
  GitHub's, they run, and one of them leaves process-wide patches behind (Y0).
  The three probes then fail deterministically. Main's CI is green and runs
  on pull requests, so the PR would go red on exactly these three ids.
- **Corrective 11** is 7 lines in one test, with no production code. I proved
  it in scratch (appendix): with it, the D1 file followed by the three probes
  passes.

**Fixed and verified:**
- **X0, the inventories:** the Shadow pin now reads
  `repository_knowledge_sync.py:276`, and the R2b inventory is regenerated.
  Both files are byte-for-byte identical to my round-11 scratch
  regeneration: only `code_revision`, `inventory_digest` and that route's
  line fields changed. All 6 round-11 tip-only ids pass.
- **X1, the MCP test's environment:** `tests/test_mcp_crush_stdio_sequence.py`
  starts the server with a scratch `HOME` and `CONVMEM_CONFIG` (a minimal
  config and an empty Chroma dir under a temp tree). Of the caller's
  environment it passes only `PATH` and `USER`. The test passes hermetically;
  it failed at main.
- **The full suite:** 92 failed, 2958 passed, 66 skipped, 58 errors. 145
  failure ids against main's 146: **0 fail only at the tip**, and 1 fails only
  at main (the MCP test, fixed by X1).
- **The leak census:** **0 tests** change a file under the fake user's data
  root or default data dir (86 at main, 1 at `d2abcbe`). Both stay empty
  after the full suite.
- **Writer leases:** across the Cursor-like full run, no test leaves a writer
  lease held or an index-lock depth above 0. Y0 is not a lease leak.
- **Earlier probes:** 89 passed, 11 failed, the same 11 expected as round 11.

### Findings (round 12)

- **Y0 (blocks CI, test-only, older than the branch): a D1 test leaves the
  live-diagnosis bootstrap's patches active for the rest of the run.**
  - `tests/test_watch_oom_live_diagnosis_d1.py::test_network_denied_under_hermetic`
    calls `live_diagnosis.bootstrap_index_child()` inside the pytest process.
    That function is the entry hook for a disposable D1 index child. It
    installs its patches with `unittest.mock.patch(...).start()` and never
    stops them:
    - `ingest.production_chroma_write_session` and
      `ingest.production_writer_boundary`, rerouted to the test's scratch
      writer lock (`writer_root/writer.lock`);
    - `ingest.summarize`, `ingest._distill_with_provenance`,
      `ingest.ollama_embed`, `llm.summarize`, `llm.ollama_embed`,
      `distill.distill_with_response` and `ingest.time.sleep`, stubbed;
    - `brief.DEFAULT_BRIEF_PATH`, redirected; `ingest._LIVE_DIAG_PATCHED`,
      set.
  - The test's `finally` calls only `teardown_hermetic_guards()`, which
    restores the open guards. Everything above stays patched.
  - Every later index in the same process then takes its write session on
    the dead scratch lock, while the caller's lease is on another lock:
    `WriterBoundaryError: nested shared writer lease must reuse the outer
    lock path`, after 2 paid summaries (`verify8d`). And the stubbed distill
    never refuses, so the F2 retry and refusal-quarantine probes fail
    (`verify8b`: "DID NOT RAISE", `has_refusal_quarantine_for_path` False).
  - **Bisect:** that test alone, followed by `verify8d`, fails; the other 40
    D1 tests don't. The other in-process `bootstrap_index_child()` call
    (`test_index_child_source_contract_fail_closed`) refuses before installing
    anything.
  - **Age:** main `458b9f6` has the same test and the same bootstrap; this
    branch changes neither. On main nothing after D1 is sensitive to the
    leftover patches. On this branch the adopted probes are.
  - **Production:** not affected. `bootstrap_index_child()` returns at once
    unless `CONVMEM_LIVE_DIAG_HERMETIC=1`, which only the D1 harness sets, in
    a child.
  - **Fix (corrective 11):** in that test, save `brief.DEFAULT_BRIEF_PATH` and
    `ingest._LIVE_DIAG_PATCHED` with `monkeypatch` before the call, and call
    `unittest.mock.patch.stopall()` in the `finally` after
    `teardown_hermetic_guards()`. The diff is in the appendix. Not a global
    `stopall()` in `conftest.py`: tests that start patches in `setUpClass`
    would break.
- **My method gap, closed for round 13:** my hermetic runs used tmpfs
  worktrees, so the D1 file never ran for me. Round 13 adds a disk-backed
  worktree run.
- **Still open from round 11, follow-ups after the merge:** X2 (the readonly
  reader loads everything when it opens: plain `add` 0.7 s → 4.8 s on a
  109k-unit store), X3 (`chroma_dedupe` undo snapshots carry document text),
  X4 (two `pass` bodies).

### Test results (round 12)

| Run | Result |
|---|---|
| Hermetic full suite, `41561ef` (tmpfs worktree) | 92 failed, 2958 passed, 66 skipped, 58 errors (22 min) |
| Main `458b9f6` (round 8, same method) | 93 failed, 2896 passed, 66 skipped, 58 errors |
| Failure ids, tip only / main only | **0** / 1 |
| Leak census, `41561ef` | **0** tests (round 11: 1; main: 86) |
| Cursor-like full suite with lease watch (tmpfs worktree) | 93 failed, 3014 passed, 9 skipped, 58 errors; no leaked lease; the three probes pass |
| D1 file + `verify8b` + `verify8d`, disk-backed worktree | the 3 probes fail (Y0), as in Cursor's runs |
| Same, with the corrective-11 diff | the 3 probes pass; 3 D1 tests fail on `bwrap` in my scratch `HOME`, as in Cursor's runs at tip and main |
| All probe rounds + Cursor's #286 files | 89 passed, 11 failed (all expected) |
| Inventory + MCP tests | 34 passed |
| Crush re-pay probe (#393) | 3 paid, then 0 (unchanged), then 4 (one message appended) |

### Corrective 11 for Cursor

Test-only. No production code, no inventory changes.
- **Y0:** in
  `tests/test_watch_oom_live_diagnosis_d1.py::test_network_denied_under_hermetic`,
  undo everything `bootstrap_index_child()` installs in the pytest process:
  - save `brief.DEFAULT_BRIEF_PATH` and `ingest._LIVE_DIAG_PATCHED` with
    `monkeypatch` before the call;
  - call `unittest.mock.patch.stopall()` in the `finally`, after
    `teardown_hermetic_guards()`.
  - The appendix has the 7-line diff I proved in scratch.
- **Acceptance, in a disk-backed checkout** (yours is):
  `pytest tests/test_watch_oom_live_diagnosis_d1.py tests/test_zz_claude_verify8b.py tests/test_zz_claude_verify8d.py`
  shows no `verify8b` or `verify8d` failure.
- **Then** the hermetic full suite at your tip, with the tip-only list
  against main `458b9f6`. Target: zero, the three probes included.
- If any inventory test fails after the edit, regenerate the inventories
  last, as in corrective 10. A test-only edit shouldn't need it.

### Next

1. Cursor: corrective 11.
2. Claude, round 13: the D1 file plus probes in a disk-backed worktree, the
   hermetic diff against `458b9f6` (target zero) and the probes.
3. A fresh Codex (Astra, high) audit and a fresh Kiro review on that exact tip.
4. A PR draft with the census. Main has moved to `fdc8da7`; bringing it in is
   Ryan's call at PR time.
5. Separate Ryan grants: the `runtime-main` promotion, the protocol-surface
   deploy, and canary 2.
6. Follow-ups after the merge: X2–X4, and #393 (Crush re-pay).

# Round 11: `d2abcbe`, FAIL; corrective 10 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-14
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `d2abcbe`, Cursor
Composer's corrective 9. It answers round 10 (below).
**Method:**
- I read the diff `61307d7..d2abcbe`.
- I ran my canonical copy of the round-10 probes. Cursor adopted them as
  `tests/test_zz_claude_verify10.py`, reformatted, with one helper inlined
  and the assertions unchanged.
- I wrote 4 round-11 probes (appendix), all through the real production
  store session against a scratch config. Controls at `61307d7`.
- I ran every earlier probe round, Codex's round-7 probes and Cursor's #286
  test files.
- I timed the new readonly reader against the old readers on a synthetic
  109,000-unit scratch store, the size of the live corpus.
- I ran the full suite hermetically at `d2abcbe` (`env -i`, a scratch `HOME`,
  no API keys, `tests/test_index_loud_failures.py` skipped) and compared it
  with round 8's main run at `458b9f6`, same method.
- I ran the leak census again: the full suite at `d2abcbe` with a fake live
  config in a scratch `HOME`, logging every test that changes a file under
  that config's data root or the default data dir. Compared with round 10's
  census of main `458b9f6`.
- I regenerated both writer inventories in a scratch worktree, to confirm
  what the tip-only failures are.
- I compared mtimes and sizes across the live data root before and after my
  runs.

### Burn status

**No burn now. This branch isn't deployed, and the watcher, refine and
monitor units are all inactive and disabled.**
- **My runs:** none can reach a paid provider. Providers are faked and the
  environment has no keys. Everything ran in scratch `HOME`s.
- **Live data root since round 10:** three `convmem index --file` runs from
  `runtime-main` (main's code, not this branch): 23:55 CDT on 2026-10-13
  (`knowledge_units.jsonl` +1.1 MB, at the end of Cursor's corrective-9
  session), and 00:35 and 00:41 CDT on 2026-10-14 (+171 KB; Codex and Kiro
  sessions were active). That's agents indexing their own sessions, not a
  loop. Also the reconcile timer (`chroma/`, `source_reconciliation.json`,
  `writer_attestations/`) and the 00:16 restic backup. Nothing from my runs.
- **The watcher burn path, at this tip:** unchanged from round 10 and still
  holding. The index route commits when another process saves while it pays
  for a summary. The F2 retry bounds hold. A corrupt retry state makes the
  watcher hold the file.
- **Refine (W0), at this tip:** closed. A refine job now reads through the
  SQLite readonly reader, which holds no Chroma system. So a foreign save
  during a paid call no longer makes the job's writes fail. The round-10
  probe (3 units, a foreign save during the first paid call) now gives 3
  paid, 3 updated, 0 errors. At `61307d7` it gave 3 paid, 0 updated, 3
  errors.

### Verdict (round 11)

**FAIL, on one mechanical item. Everything substantive passes.**
- **All of round 10 is fixed:** W0 (readers held across writes), W1 (tests
  reaching the user's config), W2 (monitor's stub), W3 (the non-counting
  fake) and the bulk of W4.
- **The full suite:** 6 failure ids fail only at the tip, and none only at
  main (152 against 146). All 6 are the writer inventories being one edit
  behind the code (X0): a call in `repository_knowledge_sync.py` moved from
  line 275 to 276 after Cursor regenerated them. With the pin corrected and
  the R2b inventory regenerated in scratch, all 164 R2b and Shadow inventory
  tests pass. No behavior is involved. But CI runs these tests, so the PR
  would go red, and the audit and the review should see the final tip.
- **The leak census:** 1 test, down from 86 at main. The one left is older
  than this branch: it starts the MCP server in a subprocess with the
  caller's `HOME`, which the new fixture can't reach (X1). It's a two-line
  fix, and corrective 10 is open anyway, so I've put it in.
- **Cursor's three suite-order flakes** (`test_zz_claude_verify8b.py` ×2,
  `test_zz_claude_verify8d.py` ×1) didn't reproduce in my full run. All
  three passed.
- **Corrective 10** is the inventory regeneration and the MCP test's
  environment. Nothing in it touches production code. After it, I re-run
  the inventory tests, the census and the hermetic diff. Then the Astra
  audit and the Kiro review.

**Fixed and verified:**
- **W1 (T0), tests reaching the user's config:**
  - `tests/conftest.py` has a new autouse fixture. It points
    `config.CONFIG_PATH`, the default writer-gate lock, the attestation and
    census dirs, and the incremental state dir at a path that doesn't exist.
    `load_config()` reads `CONFIG_PATH` at call time, so the fixture covers
    it.
  - The refine tests run inside a scratch config
    (`tests/refine_scratch_env.py`).
  - `_refine_write_scope` takes C1 from the live config, the one the session
    loads, and refuses a caller config that names a different `chroma_dir`.
    Monitor's commit and retirement take C1 from the live config too.
  - The guard now checks that C1 belongs to the store it guards. C1
    remembers the `chroma_dir` it was taken for, and the guarded store
    compares canonical (symlink-resolved) paths on every mutation.
  - My probe `test_guard_refuses_a_lock_for_another_chroma_dir` passes at
    `d2abcbe` and fails at `61307d7` ("DID NOT RAISE"). A symlinked
    `chroma_dir` still writes (`test_guard_accepts_a_symlinked_chroma_dir`).
  - **The census:** 86 tests at main changed files under the fake user's
    data root or default data dir. At `d2abcbe`, 1 does (X1). Gone: the 84
    attestation writers, the writer-gate lock, `test_doctor.py` and the
    golden eval. Round 10's 7 tip-only writers (5 in `test_refine.py`,
    Cursor's corrective-6 refine test, `test_file_generation_dedupe.py`) are
    gone too.
- **W0 (T1), readers held across writes:**
  - Refine, monitor and monitor's dry run, `add`, `add --file` and
    `ingest_approved_file` now read through
    `chroma_readonly.open_readonly_unit_store`. It reads SQLite in `mode=ro`
    and holds no Chroma system.
  - `semantic_dedupe` needs vectors. It opens a `ChromaStore`, reads them,
    and closes it before anything else. It writes no rows, only the queue
    file.
  - `chroma_dedupe` and `stale_source_flag` now re-read each row from the
    write store before writing, as `backfill_domain` already did.
  - All 5 round-10 probes pass, among them refine (3 updated) and monitor
    (exit 0, observations stored) with a foreign save in the middle.
  - **No `document` key leaks into metadata.** The readonly rows carry the
    stored document under `document`. Every refine write builds its metadata
    from a fresh write-store read, never from those rows. My probe
    `test_readonly_rows_do_not_leak_documents_into_metadata` checks this
    through a real refine job.
  - The readonly reader returns real stored documents (`chroma:document`),
    so monitor's and `add --upsert`'s unchanged-row skip still compares the
    right text.
- **W2 (T2):** `observe.ingest_observation` is now `prepare_observation_ingest`
  plus `commit_observation_ingest`, and `ingest_observation` composes the
  two. Monitor prepares (validate, unchanged check, embed) with no session
  open and queues only prepared rows. A rejected record returns `None` and
  isn't counted. The commit runs under C1, then the session.
- **W3 (T3):** `test_inter_model_doc.py` uses the counting fake.
- **W4 (T4):** 50 of round 10's 52 tip-only ids now pass, among them the
  6 W1 tests, the 2 monitor tests (no longer reaching Ollama), the
  read-path inventory (it classifies the new `semantic_dedupe` reader) and
  41 of the 43 R2b ones. The other 2 are R2b identity tests, now failing
  for X0's reason. X0 adds 4 more ids.
- **Approved dedupe, which no earlier round covered:** `--approve-dedupe all`
  takes C1 and opens the store, and each row then opens a nested write scope
  (C1 again, re-entrant, and a second session). Nesting is allowed. My probe
  `test_approve_dedupe_all_tombstones_every_row` (2 approved rows, real
  sessions) tombstones both with 0 errors, at `d2abcbe` and at `61307d7`.
  Nothing to fix.
- **Earlier probes:** my rounds 2 to 11 plus Cursor's #286 test files give
  89 passed, 11 failed. The 11 are expected: round 4's two s2 probes
  (obsolete since corrective 4) and 9 of Codex's 10 round-7 probes, which
  fail because those holes stay fixed. Round 10's W1 probe now passes.

### Findings (round 11)

**X0 (blocks the PR's CI, mechanical): the writer inventories are one edit
behind the code.**
- `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` pins
  `repository_knowledge_sync.py:275`. The retirement session call is now
  on line 276, after `_apply_retirements` gained its config fallback.
- The R2b inventory's `code_revision` is `39ca8e4c…` and the code resolves
  to another identity.
- **The 6 tip-only ids:**
  - `tests/test_shadow_writer_coverage_scan.py::test_static_scan_matches_inventory_routing`
    ("missing={'repository_knowledge_sync.py:275'} extra={'repository_knowledge_sync.py:276'}")
  - `tests/test_r2b_v2_implementation_revision.py`:
    `test_committed_inventory_matches_resolved_implementation_identity`,
    `test_production_coverage_uses_committed_inventory_without_dual_mock`,
    `test_regenerated_inventory_matches_on_disk_artifact`
  - `tests/test_r2b_v2_corrective_viii.py`:
    `test_committed_inventory_matches_authority_content_identity`,
    `test_inventory_artifact_exists_on_disk`
- **Confirmed in scratch:**
  - I corrected the one pin.
  - I regenerated R2b with `write_v2_inventory_file()` under an isolated
    `HOME`, XDG dirs and `CONVMEM_CONFIG`.
  - The diff is only the derived `code_revision` and `inventory_digest`
    values, plus that route's `entrypoint`, `route_id` and
    `shadow_inventory_ref` moving from 275 to 276.
  - All 164 tests in the R2b and Shadow inventory files pass.

**X1 (low; T0's last leak, older than this branch): the MCP stdio test
starts the server with the caller's `HOME`.**
- `tests/test_mcp_crush_stdio_sequence.py` ~42–44 copies `os.environ`, and
  sets `HOME` only when it's missing. The server subprocess loads the user's
  config and opens the configured Chroma directory. The autouse fixture
  can't reach a subprocess.
- In the census it created `live/chroma/chroma.sqlite3` under the fake
  user's data root. With a real `HOME` it opens the live store, as any
  running MCP server does. There are about ten of those on this machine
  right now, so the risk is low. But it's the one test left against the T0
  bar.
- In the hermetic run it fails at both main and the tip (no config).

**X2 (low, performance; follow-up, not corrective 10): the readonly reader
loads the whole corpus when it opens.**
- `ReadonlyUnitStore.__init__` reads every active unit's metadata and
  document. On a synthetic 109,000-unit store (about 2 KB documents, run
  alongside two full suites, so the times are rough):

  | Path | Before corrective 9 | `d2abcbe` |
  |---|---|---|
  | plain `convmem add` (the old reader opened lazily and read nothing) | 0.7 s, 151 MB | 4.8 s, 617 MB |
  | upsert paths: monitor, `add --upsert`, `ingest_approved_file`, refine (old: `ChromaStore.units_metadata()`) | 12.3 s, 459 MB | 4.8 s, 617 MB |

- So the upsert paths got faster. A plain `add` now pays about 4 s and
  470 MB for a scan it doesn't use. Not paid calls, and not the burn.
  Later: load lazily, or open the reader only when `upsert` is set.

**X3 (low; follow-up): `chroma_dedupe`'s undo snapshots now carry document
text.**
- `write_undo_snapshot(wcfg, "chroma_dedupe", to_tombstone)` writes the
  readonly rows, which include `document`. The snapshots get bigger, and a
  hand restore through `update_unit_metadata` would put the document into
  metadata. Nothing restores them automatically. Later: drop `document`
  before the snapshot, or snapshot the fresh write-store rows, as
  `stale_source_flag` does.

**X4 (cosmetic; follow-up):** `refine._run_job_impl` ends in
`finally: pass`, and `run_monitor` in `if owned_store: pass`, leftovers from
the old `close()`.

**Not findings:**
- The fixture doesn't patch the import-time copies of these defaults:
  `ProductionBoundary`'s `config_path=CONFIG_PATH` default, `doctor.CONFIG_PATH`,
  and `DEFAULT_WRITER_LOCK` in `shadow_canary` and
  `eval_corpus/r2b_v2/gate_policy.py`. All four only read or record the
  path, and the census shows no test writing through them.
- The C1 file is still found from the config's data root
  (`processed_log`'s parent), while the new binding is to `chroma_dir`. Two
  configs that share a store but not a data root would take different
  lock files. Production loads one config, and this is older than the
  branch.

### Test results (round 11)

| What | Result |
|---|---|
| Round-10 probes (my canonical copy) at `d2abcbe` | 5 of 5 pass |
| Round-11 probes at `d2abcbe` | 4 of 4 pass |
| Round-11 probes at `61307d7` (control) | 3 pass; the C1 binding probe fails ("DID NOT RAISE"), as it should |
| My rounds 2–11, Codex's round 7, Cursor's #286 files | 89 passed, 11 failed, all expected (round 4's s2 ×2; Codex round 7 ×9, holes fixed) |
| Hermetic full suite at `d2abcbe` | 99 failed, 2951 passed, 66 skipped, 58 errors (23 min) |
| Hermetic full suite at main `458b9f6` (round 8's run) | 93 failed, 2896 passed, 66 skipped, 58 errors |
| Failure ids, tip vs main | 152 vs 146; **6 tip-only (X0), 0 main-only** |
| R2b and Shadow inventory tests, inventories regenerated in scratch | 164 passed |
| Leak census at `d2abcbe` (fake live config) | 1 test changes files under the fake user dirs (X1), against 86 at main |
| Full suite with the fake live config | 98 failed: the hermetic 99 less X1's test, which passes when a config exists |

### Corrective 10 for Cursor

Small. No production code changes. Do X1 first, then X0 last, after every
other edit.

**X1:** in `tests/test_mcp_crush_stdio_sequence.py`, start the server with a
scratch `HOME` and `CONVMEM_CONFIG` pointing at a nonexistent path (or a
temp config pointing at a temp data root), not the caller's. If the test
needs a store to answer `stats`, build one in its temp dir.

**X0:**
1. Correct the Shadow inventory pin `repository_knowledge_sync.py:275` to
   wherever the retirement session call is after your last edit (276 at
   `d2abcbe`).
2. Regenerate the R2b inventory with `write_v2_inventory_file()` under an
   isolated `HOME`, XDG dirs and `CONVMEM_CONFIG`.
3. The diff should be only `code_revision`, `inventory_digest` and that one
   route's line fields.

**Then:**
- Run the hermetic full suite at your tip and list every tip-only failure id
  against main `458b9f6`. The target is zero.
- Push with an explicit refspec. Don't open a PR or merge.
- X2–X4 are follow-ups for after the merge. Leave them out, so nothing else
  moves.

**After corrective 10:**
1. I re-verify: the inventory tests, the census and the hermetic diff.
2. A fresh Codex (Astra, high effort) audit and a fresh Kiro review on the
   exact new tip.
3. Ryan opens the PR and merges.

# Round 10: `61307d7`, FAIL; corrective 9 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `61307d7`, Cursor
Composer's corrective 8. It answers round 9 (below).
**Method:**
- I read the diff `905e602..61307d7`.
- I ran the round-9 probes, now in the tree as `tests/test_zz_claude_verify9.py`.
  They open the real production store session.
- I wrote 5 round-10 probes (appendix). Two of them make a real second process
  save to the store, through the write guard, while the code under test waits
  on a paid call or an HTTP probe. That's what the watcher does when it
  commits during a refine job. Each of those probes asserts that the foreign
  save really synced, so a pass can't be vacuous. Controls at `c7072fc`.
- I ran `tests/test_refine.py` against a fake "live" config in a scratch
  `HOME`, and listed every file it wrote outside its temp dir.
- I ran the full suite hermetically at `61307d7` (`env -i`, a scratch `HOME`,
  no API keys, `tests/test_index_loud_failures.py` skipped) and compared it
  with round 8's main run at `458b9f6`, same method.
- I ran a leak census: the full suite at `61307d7` and at main `458b9f6`,
  each with a fake live config in a scratch `HOME`, with a small plugin that
  logs every test that changes a file under that config's data root or the
  default data dir (appendix).
- I compared mtimes and sizes across the live data root before and after my
  runs.

### Burn status

**No burn now. This branch isn't deployed, and the watcher, refine and
monitor units are all inactive and disabled.**
- **My runs:** none can reach a paid provider. Providers are faked and the
  environment has no keys.
- **Live data root:** two `convmem index --file` runs, at 20:19 and 20:44 CDT
  (`knowledge_units.jsonl` +87 KB and +40 KB, `processed.json`, `brief.md`),
  both from `runtime-main`, which is main's code, not this branch. They're 25
  minutes apart, so this is session indexing (most likely Cursor's Track A
  and another agent starting up; a `convmem doctor` was running at 20:51),
  not a loop. Also the reconcile timer (`chroma/`,
  `source_reconciliation.json`, `writer_attestations/`). Nothing from my
  runs.
- **The watcher burn path, at this tip:** fixed, and it holds up in the new
  probe. The index route still commits when another process saves while it
  pays for a summary. The F2 retry bounds hold. A corrupt retry state now
  makes the watcher hold the file, checked end to end through the real CLI.
- **Refine's restart loop (V0), at this tip:** closed. The lock-order failure
  is fixed. The daemon now survives a failed job and keeps one hourly limiter
  for its whole life, so the old ~120 calls an hour can't happen.
- **What's left for refine (W0):** if another process saves while a refine
  job runs, every later write in that job fails after paying for its call.
  The units stay untagged and are retried next interval. That's bounded by
  the hourly caps (60 + 20 calls an hour at the defaults), and it only
  happens when a foreign save lands mid-job. It's still payment without
  progress. The unit is disabled today.

### Verdict (round 10)

**FAIL. Not ready for the audit and the review.**
- **What's fixed:** V0's lock order in refine, monitor and retirement. All
  three round-9 probes pass through the real session. Also V1 (the watcher
  holds a corrupt retry state), V2 (`--clear-quarantine <path>` releases a
  corrupt state), V3 (`add --file` and `ingest_approved_file` embed before
  C1), V4 (the guard denies `client`), the refine daemon's per-job catch and
  single limiter, and round 9's B, E, F and G suite items.
- **What corrective 8 broke:**
  - **W0:** refine and monitor open a read-only store, keep it open, and
    then open write sessions while it's still open. Both share one in-process
    Chroma system, so when another process saves in between, the write guard
    refuses the write: "another client in this process still holds a Chroma
    system that predates the latest save". That's the guard doing its job
    (no corruption). But refine has already paid by then.
  - **W1:** `tests/test_refine.py` now opens the production store session
    from the default config path. With a real `HOME` on this machine, the
    suite would write a refine undo snapshot into the live data root and
    open the live store for write. It hasn't happened: the live
    `refine_undo/` is untouched since 2026-07-22.
- **Smaller:** monitor's deferred ingest counts rejected records as
  observations (W2). One fake session still doesn't count, and the refine
  tests bypass session fakes entirely (W3).
- **The full suite:** 145 failed at `61307d7` against 93 at main `458b9f6`: 52
  failure ids fail only at the tip, and none only at main. 43 are the R2b
  inventory not knowing the new readers. 6 are W1. 2 are monitor tests
  that still reach a local Ollama. 1 is the read-path inventory (W4).
- **My share:** round 9's T0 said refine could read through "a read-only
  store, or a session closed before the write phase" without saying the
  reader must be closed before a write session opens. `add` gets this right
  because it closes its reader first. Refine and monitor followed the looser
  wording. I should have stated it.

**Fixed and verified:**
- **V0 (T0):** refine, monitor and retirement now take C1, then open the
  session. The round-9 probes `test_refine_backfill_domain_pays_then_writes`,
  `test_monitor_cli_ingests_through_real_session` and
  `test_repository_knowledge_retirement_through_real_session` pass at
  `61307d7`, unchanged except for formatting.
- **Refine daemon:** `run_refine_daemon` catches a job's exception and goes
  on. One `CostLimiter` lives for the daemon's life. My probe
  `test_refine_daemon_survives_a_failing_job_with_one_limiter` passes. It
  fails at `c7072fc`.
- **V1 (T2):** the CLI's exit-91 refusal now starts with
  `live_route_refused:retry_state_unavailable`. My end-to-end probe runs
  the real `convmem index --file` CLI over a corrupt retry state, then feeds
  its output to the watcher's failure handler, and the watcher holds the
  file. No paid summary after the corruption. It fails at `c7072fc`.
- **V2 (T3):** the per-source clear finds the state file by its computed
  path. Cursor's test covers clearing a corrupt state and the route running
  again.
- **V3, V4 (T4):** `add`, `add --file` and `ingest_approved_file` embed with
  a reader that is closed before C1. The guard raises on `client`.
- **T1, partly:** the round-9 probes are in the tree. A counting fake
  (`tests/fake_production_write_session.py`) now backs the fakes in seven
  test files.
- **Earlier probes:** my rounds 2 to 9 plus Cursor's wedge, corrective-6,
  corrective-7 and wedge-probe tests give 73 passed, 3 failed: round 4's two
  s2 probes (obsolete since corrective 4, as in rounds 8 and 9) and Cursor's
  `test_refine_tombstone_waits_for_index_lock` (W1). Codex's 10 round-7
  probes: 9 still fail, so those holes stay fixed. The 10th is the non-git
  scan artifact, as in round 9.

### Findings (round 10)

**W0 (medium; payment without progress in refine, a monitor outage): a
reader held open across write sessions in refine and monitor.**
- **Where:**
  - refine: `_run_job_impl` (`refine.py` ~815) opens `_open_read_store` and
    closes it only when the job ends. Each write opens
    `_refine_write_scope` (~36) while it's still open.
  - monitor: `run_monitor` (`monitor.py` ~381) opens its own `ChromaStore`,
    runs the HTTP probes, then opens the write session at ~584 while that
    store is still open.
- **Why it fails:** Chroma keeps one system per path per process. The
  write session's store reuses the system the reader loaded before C1. The
  write guard sees that another process saved since then and tries to
  reload. It can't while the reader still holds the old system, so it raises
  `ChromaStaleSystemError`. That refusal is correct: it's what stops a stale
  view from overwriting another writer's save.
- **Probes** (another process saves 150 guarded rows, and the HNSW syncs):
  - refine `backfill_domain`, 3 untagged units, a foreign save during the
    first paid call: 3 calls paid, 0 updated, 3 errors at `61307d7`. At
    `c7072fc`: 3 updated.
  - monitor CLI, a foreign save during the HTTP probe: exit 1 with
    `ChromaStaleSystemError` at `61307d7`. Passes at `c7072fc`.
  - the index route, a foreign save during the paid summary: commits at
    both. The main burn path doesn't have this problem.
- **Impact:** fail-closed, no corruption. Refine pays for every unit left in
  the job and writes none. The units are retried next interval. A new job
  opens a fresh reader, so it isn't sticky, and the hourly caps bound it.
  Monitor exits 1 (local embeds only, no payment).

**W1 (high; production safety, not a burn): refine's tests write through
the user's config.**
- `_refine_write_scope(cfg)` takes C1 from the caller's `cfg`, but opens
  `production_chroma_write_session()` from `config.CONFIG_PATH`. In
  production those are the same. In `tests/test_refine.py` they aren't: the
  tests pass a temp store and a temp `cfg`, and never point
  `CONFIG_PATH` anywhere.
- **Shown with a fake live config** in a scratch `HOME`
  (`~/.config/convmem/config.toml` pointing at `~/live/`):
  - at `61307d7`, `tests/test_refine.py` wrote
    `live/refine_undo/chroma_dedupe/<ts>.jsonl`, `live/chroma/chroma.sqlite3`,
    `live/chroma.write-guard/native-write.lock` and the writer-gate lock.
    5 of its 10 tests fail.
  - at `c7072fc`: nothing outside the temp dirs, and 10 of 10 pass.
- **On this machine:** a plain `pytest tests/test_refine.py` with the real
  `HOME` would open the live 5 GB store for write, put test rows in a live
  undo snapshot, and run the guard's reconcile on the live segments. The C1
  check (`require_index_write_lock_held`) doesn't stop the write, because it
  only asks whether *some* C1 is held, and the test holds its temp one.
- **It hasn't happened:** the newest file in the live `refine_undo/` is from
  2026-07-22.
- **The leak census (the full suite, main `458b9f6` vs `61307d7`):**
  - **New at the tip, writing into the configured data root (7 tests):**
    the 5 in `test_refine.py`, Cursor's
    `test_issue_286_stage2_corrective6_audit.py::test_refine_tombstone_waits_for_index_lock`,
    and `test_file_generation_dedupe.py::test_persisted_semantic_record_resolves_real_approval_path`.
    All touch `chroma/`. 3 also write `refine_undo/` snapshots, and 1
    creates the write-guard lock.
  - **Older than this branch (also at main):**
    - `test_doctor.py::test_run_doctor_all_pass`,
      `test_eval_golden.py::test_golden_questions` and
      `test_mcp_crush_stdio_sequence.py::test_shell_profile_stats_after_crush_handshake`
      open the configured Chroma directory.
    - 84 tests at main (92 at the tip) write attestation files under the
      default `~/.local/share/convmem/writer_attestations/`. One also takes
      the default writer-gate lock.
  - The other tip-only entries are my round-8 probes in
    `test_zz_claude_verify8c.py`. They write attestations only, and they
    don't exist at main.
  - With a real `HOME`, all of these are the live store, the live writer
    lock and the live attestation directory. T0's suite-wide fixture covers
    every one.

**W2 (low): monitor's deferred ingest returns a stub.**
- `_ingest_locked` (`monitor.py` ~409) queues the record and returns
  `{"id", "ledger_id"}`. The real `ingest_observation` runs later, and its
  result is dropped.
- So a record `ingest_observation` would reject (it returns `None`) counts
  as an observation, not an error. The run's ledger map (`by_ledger_id_after`)
  holds stub rows whose `id` is the ledger id, not the stored unit id.

**W3 (low): T1 is not done.**
- `tests/test_inter_model_doc.py:143` still patches the session with a
  `MagicMock` that doesn't count.
- The refine job tests reach the real session instead of a fake (W1), so
  they can't see a lock-order change either.
- The two monitor tests from round 9's E row still reach a local Ollama (W4).

**W4 (the full suite): 52 tests fail only at the tip, from four causes.**
- **Counts:**
  - main `458b9f6` (round 8's run, same method): 93 failed, 2896 passed,
    66 skipped, 58 errors.
  - `61307d7`: 145 failed, 2900 passed, 66 skipped, 58 errors.
  - Collapsing parameters: 146 failure ids at main, 198 at the tip, 52
    tip-only, 0 main-only.
- **Re-run with tracebacks:**

| Cause | Count | What it is |
|---|---|---|
| R2b static coverage | 43 | `incomplete_static_coverage`: "route refine_job: undocumented mutation sinks ['refine.py:45']", "route convmem_cli_index: undocumented mutation sinks ['convmem.py:482', 'convmem.py:500', 'convmem.py:791']", "route convmem_cli_index: stale governed sinks ['convmem.py:757']", "route propose_decision: undocumented mutation sinks ['propose_decision.py:559']". The new readers are raw `ChromaStore`s, which can mutate, and the inventory wasn't regenerated after they were added. 7 tests fail on that directly. In the other 36 the coverage proof can't mint ("diagnostic coverage did not pass"). A reader built on `chroma_readonly.open_readonly_unit_store` isn't a mutation sink (T1). |
| W1: refine tests reach the default config | 6 | `test_refine.py` ×5 and `test_issue_286_stage2_corrective6_audit.py::test_refine_tombstone_waits_for_index_lock`: "Config not found" under the scratch `HOME`. With a real `HOME` they'd write live. |
| E, still open: monitor tests reach a local Ollama | 2 | `test_monitor.py::MonitorProbeTests::test_run_monitor_emits_verification` and `::test_run_monitor_skips_kiro`: a 404 from `localhost:11434/api/embeddings`. Round 9 named these; corrective 8 mocked `test_add_severity` only. |
| Read-path inventory | 1 | `test_file_generation_read_path_inventory.py::test_all_direct_chroma_read_boundaries_are_explicitly_classified`: the new direct `ChromaStore` reads aren't classified. |

Round 9's other 13 tip-only failures (B, E for `add`, F, G) now pass.

**Not findings:**
- **Per-unit sessions in refine:** a session open is cheap here (the sink
  decision, the guard, and a client on the cached system). That's fine.
- **`main` moved** to `a7f7200` (Safe Harbor PR #391). I verified against
  `458b9f6` so the numbers compare with rounds 8 and 9. Bringing main in is
  for the PR step: a merge commit or GitHub's update button, Ryan's call.

### Test results (round 10)

| Run | Result |
|---|---|
| Full suite, main `458b9f6` (round 8) | 93 failed, 2896 passed, 66 skipped, 58 errors |
| Full suite, `61307d7` | 145 failed, 2900 passed, 66 skipped, 58 errors; 52 tip-only, 0 main-only (W4) |
| Round-9 probes (now in the tree), `61307d7` | 4 passed |
| Round-10 probes, `61307d7` | 3 passed (the index route, the watcher hold, the daemon); 2 failed (refine and monitor after a foreign save, W0) |
| Round-10 probes, `c7072fc` (control) | 3 passed (refine, monitor, the index route); 2 failed (the watcher hold and the daemon, fixed at the tip) |
| `tests/test_refine.py` with a fake live config | `61307d7`: 5 failed, 5 passed, 4 files written under the fake live root and default dir. `c7072fc`: 10 passed, nothing written |
| Rounds 2–9 probes plus Cursor's #286 tests, `61307d7` | 73 passed, 3 failed (round 4's obsolete s2 ×2; W1 ×1) |
| Codex's round-7 probes, `61307d7` | 9 failed (holes fixed), 1 passed (the non-git scan artifact) |
| Leak census, `61307d7` vs `458b9f6` | 94 tests vs 86 touch the fake live root or default dir; 7 tests write into the configured data root only at the tip (W1); 3 older Chroma openers and 84 older attestation writers at both |
| Live data root, before vs after | two `runtime-main` index runs and the reconcile timer; nothing from my runs |

### Corrective 9 for Cursor

All items are hermetic; none involve paid calls. Do T0 first.

**T0 (W1): no test can reach the user's config.**
- Add `tests/conftest.py` with an autouse fixture that points
  `config.CONFIG_PATH` at a path that doesn't exist under `tmp_path`. Do the
  same for every other default live path a session can reach:
  `chroma_write_store.DEFAULT_WRITER_LOCK`, the attestation and census
  defaults. A test that forgets its own config then fails instead of
  touching live data. Tests that need a config keep setting their own.
- Fix `tests/test_refine.py`, and every other test the leak census names,
  to use a scratch config.
- Take C1 from the same config the session will load, in
  `_refine_write_scope` and in `_apply_retirements` (it uses the caller's
  `_cfg` now). Load the live config, take C1 from it, then open the session.
- Make the guard's C1 check name the lock: refuse a write unless the held C1
  belongs to the session's data root.
- Acceptance: with a fake live config in a scratch `HOME`, the full suite
  writes nothing under that config's data root or the default data dir.
  (My plugin for this is in the appendix.)

**T1 (W0, and most of W4's R2b rows): close the reader before any write
session opens, and prefer one that holds no Chroma client.**
- `chroma_readonly.open_readonly_unit_store` reads `units_metadata()` and
  `get_unit()` straight from SQLite in read-only mode. It loads no Chroma
  system, so it can't pin a stale view, and it isn't a mutation sink. Use it
  for the metadata reads in refine, in monitor's and `add`'s embedding
  checks, and in `ingest_approved_file`. Check that each caller gets the
  fields it uses.
- Where a job needs vectors (`semantic_dedupe`'s
  `get_units_with_embeddings`), read them with a client and close it before
  the write phase.
- **refine:** read the batch's candidates (ids and metadata) into memory,
  close the reader, then make the LLM calls. Then per write: C1 → session →
  re-read the row → write → close. Where a job writes metadata it read
  earlier (`chroma_dedupe`, `stale_source_flag`, the tombstone path),
  re-read inside the session and write from the fresh row.
- **monitor:** open the reader only for the embedding checks, and close it
  before the write phase.
- Adopt the round-10 probes (appendix).

**T2 (W2):** don't return a stub. Split `ingest_observation` into a prepare
step (validate, build the unit and its embedding; no write) and a commit
step. Count rejections at prepare time, and fill the run's ledger map from
prepared units.

**T3 (W3):** move `test_inter_model_doc.py:143` onto the counting fake.

**T4: the full suite.**
- Fix or explain every tip-only failure (W4). Regenerate the R2b inventory
  and re-pin the route sinks after T1, classify any direct read that's left
  in the read-path inventory, and mock `llm.ollama_embed` in the two
  `test_monitor.py` tests.
- Then re-pin, regenerate the writer inventories after the last code edit,
  run the full suite hermetically at main `458b9f6` and at your tip, and list
  every tip-only failure with its cause. Your corrective-8 run reported 200
  failures without that comparison. I need the diff, not the total.

**After corrective 9:**
1. I re-verify.
2. A fresh Codex (Astra, high effort) audit and a fresh Kiro review on the
   exact new tip.
3. Ryan opens the PR and merges.

# Round 9: `905e602`, FAIL; corrective 8 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `905e602`, Cursor
Composer's corrective 7 (`3dbddae`) plus its census-test refresh (`905e602`).
It answers round 8 (below).
**Method:**
- I read the diff `e1914f5..905e602`.
- I took a census of every production store-session opener and checked, for
  each one, whether C1 is taken before the session opens.
- I wrote 4 round-9 probes that open the **real** production store session
  against a scratch config (appendix). No fake session. Controls at
  `c7072fc`.
- I ran Codex's 10 round-7 probes, my round-2 to round-8 probes, and Cursor's
  wedge, corrective-6 and corrective-7 tests.
- I ran the full suite hermetically at `905e602` (`env -i`, a scratch
  `HOME`, no API keys, `tests/test_index_loud_failures.py` skipped) and
  compared it with round 8's main run at `458b9f6`, same SHA and same
  method.
- I compared mtimes and sizes across the live data root before and after my
  runs.

### Burn status

**No burn now. This branch isn't deployed, and the watcher, refine and
monitor units are all disabled.**
- **My runs:** none can reach a paid provider. Providers are faked and the
  environment has no keys.
- **Deploying `905e602` would not burn through the watcher.** The index
  route is fixed: the real `index --file` entrypoint commits, and the F2
  retry bounds hold through it.
- **It would burn through refine, if `convmem-refine.service` is enabled.**
  See V0. Each restart pays one DeepSeek call and then crashes, about 120
  calls an hour with no writes. The unit is disabled today.
- **Live data root:** between my before and after snapshots, only `chroma/`,
  `source_reconciliation.json` and `writer_attestations/` changed. That's the
  2-minute `convmem-reconcile` timer's footprint. The export and the
  processed log didn't change. My runs used a scratch `HOME`, and can't reach
  the live config.

### Verdict (round 9)

**FAIL. Not ready for the audit and the review. Not deployable while the
refine unit can be enabled.**
- **What's fixed:** S0's real target. The incremental route through the real
  `ingest.index(force_file=...)` commits. So do bulk `index` and legacy
  `index --file`, purge, export compaction and the ledger approvals. R0 and
  R1 are closed.
- **What corrective 7 broke:** S3 and S2 moved C1 *inside* an already-open
  store session in three writers: refine, monitor and repository-knowledge
  retirement. That's exactly the order S0's check refuses, so all three now
  fail on every write. Refine pays for its LLM call first (V0).
- **Why nobody saw it:** every test of those three replaces the store
  session with a fake that never counts as a store session. That includes my
  own round-8 monitor and retirement probes. The round-9 probes open the
  real session: all three fail at `905e602` and pass at `c7072fc`.
- **Smaller:** S6's refusal can't be parsed by the watcher (V1). S5 can't
  release a corrupt retry state (V2). S3 is not done for `add --file` (V3).
- **The full suite:** 15 tests fail only at the tip (down from 122), and every
  one is explained (V5). None is a burn or a production break; 7 are the
  scratch prototype, refused by the guard as it should be.
- **My share:** round 8's S2 said "take C1 around `_apply_retirements`'
  mutation" without saying the session must open inside C1. S0's order list
  implied it, but I should have said it. My round-8 monitor and retirement
  probes used fake sessions, the same blind spot as the suite.

**Fixed and verified:**
- **S0 (R0):** the lock-order check now counts opened store sessions, not the
  boundary lease.
  - `test_index_file_routes_codex_rollout_and_commits` (real `index()`,
    production's single writer-lock path) passes.
  - Bulk `index` and legacy `index --file` (8c) pass.
  - Cursor's three F2 variants go through `ingest.index(force_file=...)` and
    pass: at most 2 paid summaries per prefix, then refusal.
- **S1 (R1):** C1 before the store session in `ingest_approved_file`,
  `ingest_approved_ledger`, `convmem verify` and
  `repair_empty_ledger_documents`. `governed_lock` is still taken before C1;
  `verify_unit` writes through `ingest_observation` and never takes
  `governed_lock`, so nothing takes them in the reverse order.
- **Census:** 18 store-session openers in production code, not counting the
  scratch prototype.
  - **14 take C1 first:** `add`, `verify`, `forget`'s write, ingest ×3,
    inter-model, the two ledger approvals, ledger repair, refine's
    approved-dedupe, repository-knowledge index, purge and the coordinator.
  - **1 needs no C1:** `forget`'s first session only reads, which the guard
    allows.
  - **3 take C1 inside the session:** V0.
- **S2:** the guard denies by default, with an explicit read list.
  `supersede_units_for_source` and `_collection()` now need C1.
- **S4 (R4):** monitor embeds the normalized stored document
  (`embed_ledger_record_for_storage`) and skips unchanged rows. My round-8
  probe passes.
- **S5 (R5):** `--clear-quarantine <path>` clears that source's retry
  state and releases the hold (8b passes). Doctor names the command.
- **S6 (R6), refusal:** a corrupt or unreadable retry state refuses with
  `retry_state_unavailable` before any transform, and the CLI exits 91.
- **S7:** the round-8 appendix probes are in the tree unchanged, plus
  Codex's `_route_fixture` (formatting changes only) and Q8 tests.
- **Inventories:** both regenerated; the census test passes.
- **Codex's 10 round-7 probes:** 9 now fail, so those holes are fixed. The
  10th passes only because it scans a temp directory that isn't a git repo
  (8b's Q7 probe covers the real case).
- **Earlier probes:** my rounds 2 to 8 plus Cursor's wedge, corrective-6 and
  corrective-7 tests give 69 passed. The 2 that fail are round 4's s2 probe,
  obsolete since corrective 4, as in round 8.

### Findings (round 9)

**V0 (high; a burn if the refine unit is enabled, plus three writer
outages): refine, monitor and retirement take C1 inside an open store
session.**
- **The rule (S0):** admission → writer boundary → `source_flock` → C1 →
  store session → `export_flock`. `assert_lock_ordering_ok` refuses C1 while
  this thread has an opened store session. That check is right: it's what
  keeps a Chroma client from being opened before another writer's commit and
  then writing from that stale view.
- **refine** (`refine.py` ~792 `_run_job_impl`, ~27 `_index_write_lock`):
  the job runner opens the store, then each job takes C1 per write.
  - **Real session:** `backfill_domain` pays one DeepSeek call
    (`llm.generate`, `distill_model`), then raises "lock ordering violation".
    The `with` is outside the job's `try`, so the whole job aborts. Every
    other job fails at its first write.
  - **The burn path:** `run_refine_daemon` doesn't catch a job's exception,
    so the daemon exits. `convmem-refine.service` has `Restart=on-failure`
    and `RestartSec=30`, and at 30-second spacing the default start limit
    never trips. `CostLimiter` lives in memory and is rebuilt on every job
    run. So each restart pays one more call: about 120 an hour, no writes,
    no end. Today the unit is disabled and the tip isn't deployed. The
    missing per-job catch and the per-run limiter are both on main already;
    this tip is what makes every run pay and fail.
  - A manual `convmem refine --job backfill_domain` pays one call and fails.
- **monitor** (`monitor.py` ~399 `_ingest_locked`; `convmem.py` ~774): the
  CLI opens the store session, runs the HTTP probes, then takes C1 per
  record. Real session: one local embed, then the lock-order error; exit 1;
  nothing stored. `convmem-monitor.timer` is disabled.
- **retirement** (`repository_knowledge_sync.py` ~249 and ~283):
  `_apply_retirements` opens the session, then takes C1 inside the loop.
  Every retirement raises. The repository-knowledge manifests are out of the
  live config for now (the parked manifest fix), so the watcher doesn't
  reach it today.
- **Why the suite passes:** the tests for all three patch in a fake session
  (`fake_session`, `_FakeProductionWrite`, `SimpleNamespace` stores) that
  never increments the store-session counter. There are about 35 such
  patches across 13 test files; none counts. Cursor's corrective-7 tests
  for the index route do use the real session, which is why R0's fix holds.

**V1 (medium): S6's exit 91 prints a line the watcher can't parse.**
- `convmem.py` ~343 prints the detail, "incremental retry state could not be
  read or written". `parse_live_route_refused` returns `None` for it, so
  `watch.py` ~711 records no hold.
- Effect: for an active session with a corrupt retry state, every new event
  spawns another index child that refuses before the transform. No payment,
  but churn, and the path never shows as held.
- Round 8's S6 asked for "a refusal head the watcher can parse". Use
  `format_live_route_refused("retry_state_unavailable", digest)`.

**V2 (medium): `--clear-quarantine <path>` can't release a corrupt retry
state.**
- `clear_incremental_retry_states_for_source` finds state files by reading
  their `source_path`. A corrupt file reads as `None` and is skipped.
- So the S6 fail-closed state is cleared only by `--clear-quarantine-all`,
  while doctor's remedy names the per-source command. Find the file by the
  source's computed state path, not by its contents.

**V3 (low): S3 isn't done for `add --file`.**
- `add --file` and `ingest_approved_file` still embed every record inside C1
  and the store session (local Ollama; not paid). C1 stays held for N
  embeds.
- Single-record `add` embeds before C1, but embeds the raw record, not the
  normalized stored text. In my samples the two were identical; use
  `embed_ledger_record_for_storage` anyway, as monitor does.

**V4 (low): the guard passes non-callable attributes straight through.**
- `session.store.client` returns the raw Chroma client, unguarded. No
  production caller uses it through a guarded store today. Deny it, or
  return a guarded proxy.

**V5 (the full suite): 15 tests fail only at the tip, and every one is explained.**
- **Counts:**
  - main `458b9f6` (round 8's run, same method): 93 failed, 2896 passed,
    66 skipped, 58 errors.
  - `905e602`: 108 failed, 2931 passed, 66 skipped, 58 errors.
  - Collapsing parameters: 146 failure ids at main, 161 at the tip, 15
    tip-only, 0 main-only. That matches Cursor's report after `905e602`.
- **Re-run with tracebacks:**

| Cause | Count | What it is |
|---|---|---|
| B: the scratch prototype writes without C1 | 7 | `test_scratch_jsonl_chroma.py` ×6, `test_scratch_jsonl_live_source_canary.py` ×1: "production Chroma mutation requires the store-wide index write lock". The guard is right; production never imports the prototype. Give the prototype's `_session()` C1 the way the coordinator's does. |
| E: tests reach a local Ollama | 5 | `test_add_severity.py` ×3 (exit 1 after a 404 from `localhost:11434`), `test_monitor.py` ×2 (404). `add` and monitor embed before the session now, and the mocks don't cover `llm.ollama_embed`. T0 changes monitor again, so update these after it. |
| G: expectations made obsolete by Q1 | 2 | `test_c4_valid_exact_role_restore_still_succeeds`, `test_c4_isolation_dedupe_outside_role_refused_before_chmod`: they expect the old whole-file dedupe restore (`'tampered' != 'keep-me'`). Update to the per-transaction contract. |
| F: a test double lacks `last_evidence` | 1 | `test_selected_refusal_is_visible_without_legacy_fallback`: the router writes `coordinator.last_evidence` before `run()`. Give `RefusingCoordinator` `last_evidence = {}` and `paths = None`. |

Categories A, C, D and H from round 8 are gone.

**Not findings:**
- **`main` moved** to `a7f7200` (Safe Harbor's recovery-evidence PR #391)
  since this branch forked at `458b9f6`. I verified against `458b9f6` so the
  numbers compare with round 8. Bringing main in is for the PR step, and
  agents don't force-push, so that's a merge commit or GitHub's update
  button, Ryan's call.

### Test results (round 9)

| Run | Result |
|---|---|
| Full suite, main `458b9f6` (round 8) | 93 failed, 2896 passed, 66 skipped, 58 errors |
| Full suite, `905e602` | 108 failed, 2931 passed, 66 skipped, 58 errors; 15 tip-only, 0 main-only (V5) |
| Round-9 probes, real store session: refine, monitor, retirement (V0) | all 3 fail at `905e602` (refine after 1 paid call, monitor after 1 local embed); all 3 pass at `c7072fc` |
| Round-9 control: the real session counts as one store session | passes at `905e602` |
| Round-8 probes (8, 8b, 8c, 8d), now in the tree | all pass: real `index --file` commits; bulk and legacy index commit; F2a/b/c ≤ 2 paid; Q2(d) hold and release; Q2(c) unreadable and corrupt; Q7; Q1 |
| Cursor's corrective-7 tests (F2 through `ingest.index`, Q8) and corrective-6 audit tests | all pass |
| Codex's 10 round-7 probes (they assert the unsafe behavior) | 9 now fail, so those holes are fixed; 1 passes because it scans a non-git directory |
| My rounds 2–5, plus Cursor's wedge-probe and wedge-fix tests | pass, except round 4's obsolete s2 probe (×2) |

### Corrective 8 for Cursor

All items are hermetic; none involve paid calls. Do T0 first.

**T0 (V0): C1 before the store session, in all three.**
- **The order doesn't change:** admission → writer boundary →
  `source_flock` → C1 → store session → `export_flock`. Never take C1 inside
  an open session; open the session inside C1.
- **refine:**
  - Do the reads and the LLM calls with no production store session open
    (a read-only store, or a session closed before the write phase).
  - Then, per batch: C1 → store session → re-read each row → write → close.
  - In `run_refine_daemon`, catch a job's exception, log it, and go on to
    the next job and the next interval, so one failure can't become a
    restart loop.
  - Keep one `CostLimiter` for the daemon's life, so the hourly cap is an
    hourly cap.
- **monitor:** run the HTTP probes and the embeddings with no store session
  open. Then C1 → store session → ingest with the precomputed embeddings →
  close.
- **retirement:** `index_write_flock` around `production_chroma_write_session`
  in `_apply_retirements`, not inside it.

**T1: tests that can see the lock order.**
- Adopt the round-9 probes (appendix).
- Give the tests one shared fake-session helper that counts as a store
  session (it calls `_enter_chroma_store_session()` and
  `_exit_chroma_store_session()`), and move every fake production session in
  `tests/` onto it. Then the suite sees this class of bug.

**T2 (V1):** print the `retry_state_unavailable` refusal with
`format_live_route_refused`, and add a watcher test: a corrupt state gives a
hold, not a retry on every event.

**T3 (V2):** clear a source's retry state by its computed state path,
corrupt or not. Add a test: corrupt state, `--clear-quarantine <path>`, then
the route runs again.

**T4 (V3, V4):** embed before C1 in `add --file` and `ingest_approved_file`,
using `embed_ledger_record_for_storage`; use it for single-record `add` too.
Deny `client` in the guard.

**T5: the full suite.**
- Fix or explain every tip-only failure: B (give the scratch prototype's `_session()` C1),
  E (mock `llm.ollama_embed` in `test_add_severity.py` and `test_monitor.py`,
  after T0), G (update both tests to the per-transaction dedupe contract) and
  F (`last_evidence = {}` on the double).
- Then re-pin, regenerate the writer inventories after the last code edit,
  run the full suite hermetically at main `458b9f6` and at your tip, and list
  every tip-only failure with its cause.

**After corrective 8:**
1. I re-verify.
2. A fresh Codex (Astra, high effort) audit and a fresh Kiro review on the
   exact new tip.
3. Ryan opens the PR and merges.

# Round 8: `e1914f5`, FAIL; corrective 7 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `e1914f5`, Cursor
Composer's corrective 6. It answers round 7 (below).
**Method:**
- I read the diff `c7072fc..e1914f5`.
- I took a census of every production write session in non-test code and
  checked each one for C1.
- I ran Codex's 10 audit probes, my round-2 to round-5 probes, Cursor's
  probe, wedge-fix and corrective-6 tests, and 15 new round-8 probes (in the
  appendix). I ran control runs at `c7072fc` for the probes that test new
  behavior.
- I re-ran every test that fails only at the tip, with full tracebacks, and
  sorted each one by cause.
- I ran the full suite hermetically at main `458b9f6` and at `e1914f5`, at
  the same time and on the same disk: `env -i`, a scratch `HOME`, no API
  keys, and `tests/test_index_loud_failures.py` skipped.
- I compared mtimes and sizes across the live data root before and after my
  runs.

### Burn status

**No burn from this branch now: it isn't deployed, and the watcher stayed
inactive and disabled throughout.**
- **My runs:** none of them can reach a paid provider. Providers are faked,
  and the environment has no keys.
  - Six tip-only tests did reach a local Ollama at `localhost:11434`. It's
    local and unpaid, and it answered 404. See category E below.
- **Deploying `e1914f5` would burn.** See R0.
- **Live writes during my window weren't mine:**
  - the 2-minute `convmem-reconcile` timer;
  - an index at 16:34 that grew the export by about 805 KB. It's most
    likely Codex's own Track A on its two active rollouts, through
    `runtime-main`.

  That is the out-of-band self-indexing already seen at 12:05. The branch's
  C4 deferral stops it once deployed. My runs ran with a scratch `HOME`;
  the tests that tried to read the live config got "Config not found".

### Verdict (round 8)

**FAIL. Not ready for the audit and the review, and not deployable.**
- **What's fixed:** corrective 6 closes every burn hole Codex found, when its
  probes call the router directly.
- **What its own checks broke:**
  - **R0:** the new lock-order check makes the real `convmem index --file`
    entrypoint pay for the transform and then fail at commit, on every
    Codex and Kiro source. It also breaks purge, export compaction and
    legacy `index --file`.
  - **R1:** the new write guard breaks ledger approvals, which never took
    C1.
- **What's still open:**
  - C1 misses one watcher writer (R2);
  - slow and paid work moved under C1 (R3).
- **The full suite:** 122 tests fail only at the tip. Each one is explained
  below.
- **My share of R0:** round 7's Q4 asked to "refuse C1 while a Chroma writer
  session is held", and I didn't separate the outer writer-boundary lease
  from an opened store session. My F2 probes also called the router
  directly, so they couldn't see it.

**Fixed and verified:**
- **Q2(a)(b), paid retries are bounded.** This holds on all three paths
  Codex probed:
  - an `OSError` writing the prepared artifact;
  - a 402 after a successful summary;
  - a failed distill through manual `index --file`.

  Each pays at most 2 summaries per prefix, then refuses before any
  transform, and the watcher holds the path. Codex's three F2 probes,
  flipped, pass. These probes call `maybe_route_incremental` directly. R0
  covers the real entrypoint.
- **Q2(d), the hold.** Three failures across three prefixes give 3 paid
  attempts, then refusal with 0 further calls. Releasing the hold is broken;
  see R5.
- **Q2(c):** an unreadable retry state refuses before any transform work.
- **Q1:**
  - the rollback removes exactly this transaction's dedupe lines;
  - foreign, legacy and malformed lines stay byte-identical and in order;
  - it runs under C1.
- **Q5, Q6, Q7 and Q8 do what they say.** Q7 checked against a real git
  repo: a tracked `review-bundles/` writer is scanned and an untracked one is
  skipped.
- **Codex's 10 probes:** 8 flip. The other 2 still "reproduce" only because
  of how the probes are built, so they aren't findings:
  - **the refine probe** calls the tombstone helper directly, with a mock
    store. Its real callers now hold C1, and the real store raises without
    it.
  - **the scan probe** scans a temp directory that isn't a git repo.
- **Earlier probes:** my rounds 2 to 5 plus Cursor's tests give 47 passed.
  - **2 obsolete:** the round-4 s2 probe stubs a helper that corrective 4
    removed. It fails the same way at `c7072fc`.
  - **1 Cursor test:** see R7.

### Findings (round 8)

**R0 (critical; a burn once deployed, plus an indexing outage): the new
lock-order check fires inside the normal index path, after the paid
transform.**
- **Where:** `assert_lock_ordering_ok` (`purge_locks.py` ~78–84) now refuses
  C1 whenever this thread holds any shared writer lease. It reads that from
  `production_write_session_depth()`.
- **Why it fires:** several callers take the outer
  `production_writer_boundary` lease first, then C1:
  - `ingest.index()` holds it around the whole run (`ingest.py` ~1638);
  - `execute_purge` (`source_purge.py` ~296);
  - `_deduplicate_units_export` (`ingest.py` ~580);
  - `approve_and_ingest`.
- **What breaks:**
  - **Codex and Kiro sources (the incremental route):** `convmem index
    --file` on a Codex rollout runs the transform and pays for it. Then
    `_commit_generation`'s fresh C1 raises "lock ordering violation: cannot
    acquire index write lock while holding a Chroma writer session".
    - My probe through the real `ingest.index(force_file=...)`, with
      production's single writer-lock path, paid 2 summaries and failed.
    - The same probe commits at `c7072fc`.
    - The error is counted as `unexpected_RuntimeError`, so Q2 caps it:
      2 paid attempts per prefix, or 3 across prefixes for an active
      session. Then R5's hold applies, and that hold never releases.
    - So once deployed, each Codex or Kiro source would pay for up to 3
      transforms and index nothing. Every new session would do the same.
      That covers the watcher's `index --file` children and agents' Track A.
  - **Legacy sources:** `index --file` fails at `_snapshot_reindex_rows`
    (`ingest.py` ~1243) before any paid call. So no burn, but every
    watcher child for Cursor, Crush, markdown and similar sources fails.
  - **Bulk `convmem index`:** chunks commit, then the final export
    compaction raises. Files are already marked processed, so nothing is
    paid twice. But every run ends in an error.
  - **Purge:** `convmem exclude-source` fails for every real candidate.
  - **The canary-2 runner:** `incremental_jsonl_canary.py` fails at the
    coordinator's `_chroma_row_count`.
- **Evidence:**
  - the tip-only failures in category A (54);
  - `test_index_file_routes_codex_rollout_and_commits`, in the appendix.
  Cursor's report saw this class and called it likely test-harness
  breakage.

**R1 (high, blocks the merge; not a burn issue): the write guard breaks
ledger writes, because they never took C1.**
- **What breaks:** `convmem record --approve-last` reaches
  `ingest_approved_ledger` (`propose_decision.py` ~568–600), which opens a
  production store without C1. `add_unit` then raises "production Chroma
  mutation requires the store-wide index write lock".
- **What the user sees:**
  - the approval saga leaves `APPROVAL_STARTED` behind;
  - recovery calls the same function, and it fails again;
  - so after the merge, every approval would stick.
- **The same shape elsewhere:**
  - `convmem verify` (`convmem.py` ~560, via `update_unit_metadata`);
  - `ingest_approved_file` (`propose_decision.py` ~549);
  - `observe.repair_empty_ledger_documents` when not a dry run
    (`scripts/repair-ledger-documents.py`).
- **Evidence:**
  `tests/test_chroma_approve_index.py::ChromaApproveIndexTests::test_ingest_approved_ledger_upsert_nonempty_corpus`
  fails at `e1914f5` with that error. It passes at main `458b9f6` and at `c7072fc`.
- **The guard did its job here:** it found writers missing from Cursor's
  list. The fix is to give them C1, not to exempt them.

**R2 (high; latent until the repository-knowledge manifests return): one
watcher writer still mutates units without C1, and the guard can't see it.**
- **The writer:** `repository_knowledge_sync._apply_retirements`
  (~247–315).
  - It opens a production session without C1, then calls
    `supersede_units_for_source` on `knowledge_units`.
  - The watcher runs it in-process, from the startup `reconcile_all` and
    from reconcile tokens, at the same time as index children.
  - That's the Stage 2 shape: a foreign write in the middle of an apply
    trips `non_source_isolation_changed`.
- **Why the guard misses it:**
  - its `_MUTATORS` list leaves out `supersede_units_for_source`;
  - it passes `_collection()` straight through, and that returns raw
    collection handles that can write unguarded.
- **Why it's latent:** `watch.repository_knowledge_manifests` has been out
  of the live config since 2026-10-12. It comes back when the manifest fix
  lands.
- **Probes:**
  - `test_guard_refuses_unlocked_supersede` gives no raise;
  - `test_repository_knowledge_retirement_holds_index_write_lock` gives a
    lock depth of `[0]`.

**R3 (medium; liveness; contradicts the PR's "no lock is held across paid
provider calls"): corrective 6 moved slow work under C1.**
- **refine:** `_run_job_impl` (`refine.py` ~769–775) now holds C1 for the
  whole job.
  - That includes `backfill_domain`'s DeepSeek `generate` calls (~424–462),
    which are paid.
  - At `c7072fc`, the refine job held no C1 at all; its tombstone writes
    were the F3 gap.
- **monitor:** `convmem monitor` holds C1 across all of `run_monitor`,
  including:
  - both HTTP probes, which have 20 s timeouts;
  - every embedding.

  My probe sees both fetches at lock depth 1; at `c7072fc` it sees 0.
  Round 1's C5 had already asked to narrow monitor's lock to the writes.
- **`add --file`:** this path still embeds each record under C1, through
  `ingest_observation_file`.
- **Effect:**
  - C1 is a blocking flock, so watcher applies wait.
  - An index child that waits past the watcher's 15-minute subprocess
    timeout is killed after its summaries were paid for.
  - Those summaries are cached and reused, so this doesn't re-burn. But the
    path's failure count climbs.

**R4 (medium; correctness; corrective 6 introduced it): monitor stores an
embedding of different text than the document it stores.**
- **The mismatch:**
  - `_ingest_locked` embeds `ledger_unit_document(record)`, on the raw
    record;
  - `ingest_observation` stores
    `ledger_unit_document(normalize_ledger_record(record))`.
- **Why the texts differ:** monitor records carry no keywords, so
  normalization derives them. The stored document includes the keywords;
  the embedding doesn't.
- **Effect:** retrieval drifts silently for every monitor unit.
- **It also embeds unchanged records:** monitor now embeds records that the
  upsert path then skips as unchanged.
- **`add` isn't affected:** it matches only because it requires 3 or more
  keywords and passes them through.
- **Probe:** `test_monitor_embeds_the_document_it_stores` fails at
  `e1914f5` and passes at `c7072fc`.

**R5 (medium; Q2(d) incomplete): nothing releases the 3-strikes hold.**
- **What `--clear-quarantine` does:** `convmem watch --clear-quarantine
  <path>` clears only the breaker state.
- **What stays:** `retry_state.json` keeps `source_consecutive` at 3 or
  more. So every later attempt refuses before any transform, from the
  watcher or from `index --file`.
- **Why it never clears itself:** only a success resets the count, and none
  can happen.
- **Effect:**
  - it's burn-safe;
  - but the session silently never indexes again;
  - doctor WARNs, with no remedy that works.
- **Probe:** `test_q2d_source_hold_across_prefixes_and_clear_quarantine_releases`.
  It sees 3 calls, then the source is still refused after the clear.

**R6 (low): Q2(c) is partial.**
- **A corrupt retry state is read as "no state",** so the next attempt pays:
  - a `retry_state.json` that doesn't parse is treated as missing;
  - doctor calls the same file `retry_state_unavailable`.
  - The failure then overwrites the file, so the cost is one extra paid
    attempt.
- **`retry_state_unavailable` exits 1, not 91:**
  - the spec and Cursor's report both say 91;
  - but only `live_route_refused` maps to 91 (`convmem.py` ~339–356).
  - The watcher treats it as an ordinary failure. Each child still refuses
    before transform, so there's no burn.

**R7 (low; tests and the census):**
- **One of Cursor's tests reads the live config.**
  `test_add_embeds_before_index_lock` reads the real
  `~/.config/convmem/config.toml`, because `add` now calls `load_config()`
  before the session.
  - Outside a hermetic environment, it also takes the live C1 lock file.
  - It fails in a hermetic run ("Config not found"), and it would fail in
    CI.
- **Tests the spec asked for are missing:**
  - Q2(c) and Q2(d);
  - Q8 (the tamper record and the doctor WARN);
  - an unlocked mutation raising (Q3);
  - concurrent runs through real entrypoints;
  - the three flipped F2 probes.
- **Test too weak:** `test_rollback_preserves_foreign_dedupe` only checks
  that the files aren't empty.
- **The writer list was incomplete:** it named 12 routes and missed the 5
  writers in R1 and R2.

**R8 (the full suite): 122 tests fail only at the tip, and every one is
explained.**
- **Counts:**
  - main `458b9f6`: 93 failed, 2896 passed, 66 skipped, 58 errors. That's
    the same 151 known failure ids as round 6.
  - `e1914f5`: 223 failed, 2804 passed, 66 skipped, 58 errors, giving 273
    failure ids.
  - No failure is main-only.
- **Re-run:** re-running the 122 with full tracebacks gives 130 failures,
  because parameters expand. They sort as follows.

| Cause | Count | What it is |
|---|---|---|
| A: the lock-order check counts the outer writer boundary (R0) | 54 | purge, the purge contract tests and concurrent purge; export compaction; legacy `index --file`; the incremental commit through `index()`; the canary runner (`test_incremental_jsonl_canary_p2_*`); `test_b4_*` |
| B: the write guard, on writers without C1 (R1) | 15 | ledger approve and recover (`test_safe_harbor_t2.py` CLI approve and recover, `test_chroma_approve_index.py`); ledger-document repair; the scratch prototype's projection |
| C: stale writer inventories (R2b and shadow) | 45 | the R2b coverage proof can't mint ("diagnostic coverage did not pass"); "undocumented mutation sinks", "stale governed sinks", "production session inventory drift" (`convmem.py:545`, `:1801`, `incremental_jsonl.py:676`, …). Only `R2B-V2-WRITER-COVERAGE-INVENTORY.json` was regenerated, and before the last code edits. |
| D: a test reads the live config (R7) | 1 | `test_add_embeds_before_index_lock` |
| E: tests reach a local Ollama | 6 | `add` and `monitor` now embed before the session, through `llm.ollama_embed`, and the tests' mocks don't cover that (`test_add_severity.py` ×3, `test_monitor.py` ×2, +1). Update the mocks; this is also how R4 slipped by. |
| F: a test double lacks `last_evidence` | 1 | `maybe_route_incremental` now writes `coordinator.last_evidence` before `run()`. Update the double. |
| G: expectations made obsolete by Q1 | 2 | `test_c4_valid_exact_role_restore_still_succeeds` and `test_c4_isolation_dedupe_outside_role_refused_before_chmod` expect a whole-file dedupe restore, and the second uses the old signature. Q1's own code still runs the outside-role check, through `_dedupe_restore_paths()`. Update the tests to the new contract. |
| H: CLI subprocess failures with no captured error | 6 | purge CLI ×4, Safe Harbor's event-only recovery, and the OpenClaw watch end-to-end (its index child left no Chroma behind). These are most likely A or B. Confirm after S0 and S1. |


**Not findings:**
- **`forget`:** it reads and prompts inside a writer session; the spec said
  before one. The writer lease is shared (`LOCK_SH`), so it blocks only C5
  activation, not other writers.
- **CG-2 tooling:** `cg2_first_cutover` and `cg2_rehearsal` write raw
  collections through `FileGenerationStore`, outside the production session.
  That's Recovery Authority's Ryan-gated cutover tooling, not part of this
  arc's census.

### Test results (round 8)

| Run | Result |
|---|---|
| Full suite, main `458b9f6` | 93 failed, 2896 passed, 66 skipped, 58 errors (the same 151 ids as round 6) |
| Full suite, `e1914f5` | 223 failed, 2804 passed, 66 skipped, 58 errors; 122 tip-only, 0 main-only (R8) |
| Round-8 probe, the real `index --file` entrypoint (R0) | fails at `e1914f5` (2 summaries paid, then a lock-order error); passes at `c7072fc` |
| Round-8 probe, bulk `index` and legacy `index --file` (R0) | both fail at `e1914f5` (bulk at the final compaction, after commit; `--file` before any paid call); pass at main |
| Codex's 10 audit probes (they assert the unsafe behavior) | 8 now fail, so those holes are fixed; 2 pass because of how they're built (explained above) |
| My rounds 2–5, plus Cursor's probe, wedge-fix and corrective-6 tests | 47 passed; 2 obsolete (also fail at `c7072fc`); 1 non-hermetic (R7) |
| Round-8 probes, burn bounds: F2a, F2b, F2c, Q2(c) unreadable, Q1, Q7 | 6 passed |
| Round-8 probes, findings | R2 ×2, R3, R4, R5 and R6 fail, as expected; controls at `c7072fc` pass for R3 and R4 |
| Approve-index test (R1) | fails at `e1914f5`; passes at main and at `c7072fc` |

### Corrective 7 for Cursor

All items are hermetic; none involve paid calls. Do S0 first.

**S0 (R0): keep the lock-order rule, but count the right thing.**
- **What the check counts:** it refuses C1 only while this thread has an
  opened production *store session*, from `production_chroma_write_session`
  or `open_production_write_store`. Track that depth separately.
- **What it doesn't count:** the outer `production_writer_boundary` lease.
  - It's the shared census and attestation lease (`LOCK_SH`), so it doesn't
    block other writers.
  - It belongs to the admission layer.
- **The full order:** Safe Harbor's admission check, then the writer
  boundary, then `source_flock`, then C1, then the store session, then
  `export_flock`.
- **Check every caller that opens a store and then takes C1:**
  - ingest's `_snapshot_reindex_rows` and `_commit_chunk_to_stores`;
  - export compaction;
  - purge;
  - the coordinator's `_session()`;
  - the canary runner.
- **Tests:**
  - adopt `test_index_file_routes_codex_rollout_and_commits` and the
    bulk-index probe;
  - add a variant of the three F2 probes that goes through
    `ingest.index(force_file=...)` instead of the router.

  Every burn probe must use the real entrypoint from now on.

**S1 (R1): C1 for every ledger writer, then a real census.**
- **Give C1 to:**
  - `ingest_approved_ledger` and `ingest_approved_file`;
  - `convmem verify`;
  - `observe.repair_empty_ledger_documents`.
- **Take the census:** list every call to `production_chroma_write_session`
  and `open_production_write_store` in production code, each with how it's
  covered, for the PR body.
- **Check the lock order:** `approve_and_ingest` holds `governed_lock`
  before it would take C1. Confirm that nothing takes C1 and then
  `governed_lock`.

**S2 (R2): C1 around the retirement, and a guard that denies by default.**
- Take C1 around `_apply_retirements`' mutation.
- Make the guard deny by default: expose an explicit list of read methods,
  and require C1 for everything else, including `supersede_units_for_source`.
- Handle `_collection()`: either block it, or return a collection whose
  add, upsert, update and delete require C1.

**S3 (R3): nothing slow under C1.**
- **refine:** make the LLM calls outside C1. Take C1 per write, and re-read
  the row under C1 before writing it.
- **monitor:** run the HTTP probes and the embeddings before C1. C1 and the
  writer session cover only the writes.
- **`add --file`:** compute the embeddings before C1.
- **The lock order doesn't change:** admission, then `source_flock`, then
  C1, then the Chroma session, then `export_flock`.

**S4 (R4): embed exactly the document that gets stored.**
- Embed the normalized document text, by exporting a prepare step from
  `observe`.
- Skip the embed when the record is unchanged.

**S5 (R5): `convmem watch --clear-quarantine <path>` releases the
retry-state hold.**
- It also clears that source's retry state, and `--clear-quarantine-all`
  clears every source's.
- Doctor's WARN names the command.

**S6 (R6): a corrupt retry state fails closed.**
- An unparseable retry state refuses with `retry_state_unavailable`, before
  any transform.
- Map it to exit 91, with a refusal head the watcher can parse.

**S7 (R7): tests.**
- Patch `load_config` in `test_add_embeds_before_index_lock`.
- Adopt the round-8 probes in the appendix as tests. They need Codex's
  `_route_fixture`, from the audit appendix.
- Add Q8 tests: the tamper record is written, and doctor WARNs within 7
  days and not after.

**Then:**
- re-pin the baseline hashes and regenerate the writer inventories;
- run the full suite hermetically in clean detached worktrees at main and
  at your final tip;
- **list every tip-only failure with its cause,** and fix it or explain
  it. "Likely the C1 guard" isn't enough: R0 and R1 were both in that list.
  R8's table is the starting point. After S0 to S7, the only tip-only
  failures left should be tests updated on purpose (E, F and G), each
  named.

**After corrective 7:**
1. I re-verify.
2. A fresh Codex (Astra, high effort) audit and a fresh Kiro review on the
   exact new tip.
3. Ryan opens the PR and merges.

---

# Round 7: `c7072fc`, Codex's FAIL held; corrective 6 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `c7072fc`. This
round is my disposition of two reviews of that tip:
- **Codex (Astra, high effort), standing in for the Copilot audit lane:**
  FAIL, with five blockers and two observations. The report is
  `docs/inter-model/CODEX-2026-10-13-issue-286-stage2-fixes-audit.md`, on
  branch `docs/2026-10-13-issue-286-stage2-fixes-audit` (`e1cec55`).
- **Kiro, design review:** PASS with conditions CO-1 to CO-5. The report is
  `docs/inter-model/KIRO-2026-10-13-issue-286-stage2-fixes-design-review.md`,
  on branch `docs/2026-10-13-issue-286-stage2-fixes-design-review`
  (`b96fbb8`).

**Method:**
- I extracted Codex's 10 probes and its network and live-path guard from the
  audit appendix, then ran them hermetically at `c7072fc`.
- I read each probe to confirm it doesn't stub out the mechanism it says it
  defeats.
- I read the code each finding cites.
- I checked three live config facts, printing booleans only.

### Verdict (round 7)

**The round-6 "ready" is withdrawn. Codex's FAIL holds, and corrective 6 is
needed.**
- **The probes:** all 10 reproduce at `c7072fc`, and each asserts the unsafe
  behavior. They use the real coordinator, rollback, lock, breaker,
  detection and scan code; only providers, stores or the subprocess transport
  are faked.
- **Sol-High isn't needed.** The two reviews don't contradict each other on
  a fact:
  - Kiro's PASS is explicitly conditional on C1 covering every writer (CO-1,
    "the guarantee is only as strong as the census").
  - Codex's F3 shows, with a reproduced probe, that it doesn't.
  - Reproducible evidence settles the remaining propositions: F4 shows that
    `add` embeds under the lock.
  - Codex also declined to infer a conflict.
- **My misses:** I missed all five blockers over six rounds.
  - My rounds tested the paths I had specified: the wedge, rollback and the
    export.
  - I never took a census of writers, checked the dedupe files under C2's
    relaxation, or followed errors other than `IncrementalJsonlError` out of
    a run after paid work.
  - My round-2 statement that raised provider refusals "don't make a billed
    call" is wrong when the summary succeeded first.

### Findings, confirmed

| Codex | Severity | Confirmed? | What it means here |
|---|---|---|---|
| F1 | high | yes, in code and by probe | The rollback restores `dedupe_queue.jsonl` and `ingest_duplicate_suppressions.jsonl` *whole* from their before-images (`_restore_dedupe_files` → `_restore_file_preimage`, `incremental_jsonl.py` ~1632–1639). **Concrete for canary 2:** if the 3 stale `APPLYING` Stage 2 transactions roll back, both files go back to their 2026-10-12 contents, deleting every dedupe record other sources wrote since. |
| F2 | high, burn | yes | Two holes. (a) Only `IncrementalJsonlError` is counted, so an `OSError` writing the prepared artifact (a full disk, say) or a `ProviderUnavailableError` after a successful summary makes the watcher re-run, and re-pay, on every event. (b) Retry state is checked only *after* `run()`, so each `index --file` on an unchanged prefix pays again before it refuses. The live summarize and distill models are the same (boolean check), so the 402-after-summary case is unlikely; the disk-error and post-summary failure paths don't depend on the provider. |
| F3 | high | yes | Semantic-dedupe tombstones in `refine` write while another thread holds C1. Inter-model ingest writes a unit before its export lock pulls in C1. Repository-knowledge ingest and source purge have the same late-acquire shape. A cooperating writer can still trip `non_source_isolation_changed` mid-apply, which was the Stage 2 cause. |
| F4 | medium | yes | `add` and `monitor` embed while holding C1. `forget` holds C1 through its interactive confirmation prompt, so a forgotten prompt stalls every writer, including the watcher. All three take the Chroma writer session *before* C1, against the spec's order. `assert_lock_ordering_ok` accepts C1 followed by `source_flock`. No production deadlock was shown. |
| F5 | medium | yes; can't fire in production today | `should_defer_index_file` has no Claude exception. None of the 13 live watch roots covers `~/.claude/projects` (boolean check), so it's a spec violation rather than a live gap. |
| O1 | low to medium | yes | The `review-bundles/` skip is an unconditional prefix, so a tracked writer there would be invisible. Nothing is tracked there today. This matches Kiro's CO-2. |
| O2 | low | yes | An empty digest (the source can't be read) releases a wedge hold. |

**Kiro's conditions:**
- CO-1 is now F3; it is a code item, not only a list.
- CO-2 is O1.
- CO-3 is mine: the PR draft's suite line and its review wording. I've
  corrected them below.
- CO-4 (make the tamper record durable) goes into corrective 6, so canary 2
  doesn't wait on another loop.
- CO-5 (release a clean `rolled_back` on a prefix change) stays a canary-2
  decision, as Kiro recommends.

### Corrective 6 for Cursor

All items are hermetic; none involve paid calls.

**Q1 (F1): roll back dedupe records by transaction, not by file.**
- Rollback removes only the lines this transaction wrote, identified by the
  `transaction_id` that `_reconcile_dedupe` stamps on each event.
- Every other line stays byte-identical and in order: foreign appends,
  foreign edits, and anything written after the before-image.
- If the file didn't exist before and nothing remains, remove it.
- **Test:** flip Codex's F1 probe. Foreign records survive and this
  transaction's records are gone. Add a case where the file already held
  older records.

**Q2 (F2): bound every failure that can follow paid work.**
- **(a) Count every exception that escapes `coordinator.run()`,** not just
  `IncrementalJsonlError`. Leave out `KeyboardInterrupt` and `SystemExit`.
  - Codes: `provider_unavailable` for `ProviderUnavailableError`,
    `artifact_write_failed` for `OSError`, `unexpected_<ClassName>` for
    anything else.
  - A second identical failure on the same prefix gives
    `live_route_refused` (exit 91), the same as today.
- **(b) Check before paying.** Before any transform work, compute the
  source's prefix digest and read its retry state. If this exact prefix is
  already refused, refuse at once with the same wedge refusal and do no
  transform work. This covers `index --file`, `--now` and watcher children,
  since all of them go through `maybe_route_incremental`.
- **(c) Fail closed on retry state.** If the retry state can't be read or
  written, refuse before any transform work with `retry_state_unavailable`
  (exit 91). Doctor WARNs about it.
- **(d) A bound across prefixes (my addition, beyond Codex's ask).** Three
  consecutive failures with the same code for one source, whatever the
  prefix, hold the path until `convmem watch --clear-quarantine`, and doctor
  WARNs.
  - **Why:** without this, an active session hitting a persistent
    post-summary failure, such as a full disk, pays one or two summaries on
    every append.
  - **When the count resets:** a success.
- **Tests:** flip Codex's three F2 probes. The third and later attempts make
  0 summary calls, and the watcher holds the path. Add tests for (c) and (d).

**Q3 (F3, Kiro CO-1): C1 covers every production writer of summaries, units
and the export.**
- **Wrap the mutation windows:**
  - `refine`: `_tombstone_semantic_duplicate` and the `chroma_dedupe`
    mutations;
  - inter-model ingest (`inter_model_index.py` ~323): take C1 before
    `add_unit`, and hold it through the export append;
  - repository-knowledge ingest (`repository_knowledge_index.py` ~280);
  - source purge (`source_purge.py` ~357 and ~386): take C1 before the
    collection deletes.
- **Enforce it at runtime.** In the production Chroma write session, every
  mutating call on summaries and units must raise unless this thread holds
  C1: add, upsert, metadata update and delete. That makes the census
  permanent and catches writers nobody listed. If some writer can't take C1,
  stop and report why; don't exempt it silently.
- **Report the full writer list** (route, file:line, how it's covered). It
  goes into the PR body.
- **Tests:**
  - flip Codex's refine probe, so the tombstone write waits until C1 is
    released;
  - add concurrent tests on real entrypoints;
  - test that an unlocked mutation raises.

**Q4 (F4): nothing slow or interactive under C1, and the specified lock
order.**
- `add` and `monitor` compute embeddings before taking C1. C1 covers only
  the store and export writes.
- `forget` asks for confirmation before it takes C1 or opens the writer
  session.
- **The order:** Safe Harbor's admission check stays outermost, then
  `source_flock`, then C1, then the Chroma writer session, then
  `export_flock`.
- Extend `assert_lock_ordering_ok`:
  - it refuses `source_flock` while C1 is held;
  - it refuses C1 while a Chroma writer session is held. Track the session
    depth to do this.
- **Tests:** flip Codex's `add` probe (no embed at lock depth 1) and its
  reversed-order probe (it now raises).

**Q5 (F5): never defer a Claude transcript.**
- `should_defer_index_file` returns False for `jsonl_claude_session`.
- Test it with a real Claude transcript under a broad root, which is Codex's
  probe flipped.

**Q6 (O2): unknown isn't a change.** When the prefix digest can't be computed,
keep a wedge hold.

**Q7 (O1, Kiro CO-2): narrow the R2b skip.**
- Skip `review-bundles/` only for files git doesn't track. Tracked files
  there are still scanned.
- Flip Codex's scan probe for a tracked file.
- Ryan acknowledges this for the R2b arc.

**Q8 (Kiro CO-4): make the tamper report durable.**
- When a rollback drops unexpected export lines, also append a structured
  record to the source's incremental state directory: time, source,
  transaction id and count.
- `convmem doctor` WARNs on records from the last 7 days.

**Not in corrective 6:** CO-5 (G5: whether a clean `rolled_back` releases on
a prefix change). Kiro recommends deciding it during canary 2.

**Then:**
- re-pin the baseline hashes and regenerate the writer inventories;
- run the full suite hermetically in clean detached worktrees at main and at
  your final tip;
- list every tip-only failure with its cause.

**After corrective 6:**
1. I re-verify, including Codex's probes flipped and my round-2 to round-5
   probes.
2. A fresh Codex audit and a fresh Kiro review on the exact new tip.
3. Ryan's PR and merge.

---

# Round 6: `c7072fc`, "ready" withdrawn in round 7 (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `c7072fc`, Cursor
Composer's corrective 5. It answers round 5 (below).
**Method:**
- I read the diff `62fe3a2..c7072fc`.
- I ran every probe from rounds 2 to 5, plus Cursor's probe and wedge-fix
  tests.
- I ran the full suite hermetically at main `458b9f6` and at `c7072fc`, at the
  same time and on the same disk: `env -i`, a scratch `HOME`, no API keys, and
  `tests/test_index_loud_failures.py` skipped.
- My runs touched nothing live. I compared mtimes and sizes across the live
  data root before and after.

### Verdict (round 6)

**Ready for the Copilot safety and isolation audit and for Kiro's design
review. I have no open findings.**

- **O1, fixed:** a line whose id is in the before-image is now compared by
  its parsed content, not its bytes. Cursor's code matches the fix I tested
  in round 5.
  - s3: a clean rollback of a grown session restores the export exactly and
    prints nothing, at both crash points.
  - s5: one line edited while the transaction is wedged is reported as
    exactly 1.
  - s1, s2, s4, r2 and the direct tamper test still pass.
- **All probes pass:** 41 tests, covering rounds 2 to 5 and Cursor's probe
  and wedge-fix files.
- **Full suite:** main `458b9f6` fails the same 151 known tests as in rounds
  3 and 5, and so does the tip. The tip passes 22 more tests: the branch's
  own. One test failed once, only at the tip:
  `test_chroma_write_guard.py::test_native_crash_mid_write_leaves_the_shared_index_clean`.
  It's a timing flake, not a regression:
  - it passed 5 of 5 at both main and the tip when re-run alone;
  - this branch doesn't touch `chroma_write_guard.py` or its test;
  - no core dumps were recorded during the run;
  - the cause: `vector_census` opens SQLite read-only (`chroma_write_guard.py`
    ~397–410). When the test's SIGKILL lands mid-write, it leaves a journal
    that a read-only connection can't recover, so the census raises
    `attempt to write a readonly database`. That robustness gap belongs to
    the write-guard work, not this arc.
- **Code left behind:** none. Nothing references the removed byte-matching
  helpers any more.

### Review focus: the decisions reviewers must judge

These are the places where the branch relaxes a reviewed invariant or makes a
judgment call. Copilot audits them for safety and isolation. Kiro reviews them
as design.

1. **C2, foreign state between attempts.**
   - **What changed:** replay and rollback no longer require foreign store
     rows or foreign export lines to equal their state at transaction start.
   - **What isolation now means:** it is checked against a digest taken
     under the C1 index write lock at the start of *this* attempt.
   - **What still holds:** foreign export lines pass through byte-identical
     and in order.
   - **The argument:** C1 makes foreign writes impossible during an apply,
     so foreign changes *between* attempts are legitimate.
2. **Source-owned export tamper is dropped, not refused (G3).**
   - **What the rollback does:** it always rewrites this source's lines back
     to the before-image.
   - **What the message counts** (`[incremental] rollback dropped N
     unexpected export lines for <source>`):
     - source-owned lines whose id is neither in the before-image nor in
       this source's store rows;
     - before-image lines whose parsed content changed.
   - **Not counted, but still removed:** a line whose id the store also
     holds.
   - **Why drop:** refusing in the export, after the store is already
     restored, would leave a half-rolled-back transaction that never
     recovers. The store rollback already deletes this source's unknown rows
     without a tamper check.
3. **G5: a clean rollback holds the session until someone clears it.**
   - **What happens:** after `rolled_back`, the watcher holds the path until
     `convmem watch --clear-quarantine`. Doctor lists it under
     `incremental_refusals`.
   - **Why it's acceptable for now:** it's burn-safe.
   - **Decision deferred:** decide after canary 2 whether a prefix change
     should release it.
4. **G7: another arc's guard changed.** `review-bundles/` was added to the
   R2b writer-scan skip list (`eval_corpus/r2b_v2/coverage/inventory.py`).
   It's an untracked folder in Ryan's checkout.
5. **K1 edge (a note):**
   - a raised error with no prefix digest records an empty digest, and the
     watcher never holds it, so it re-spawns on each event;
   - these errors fire before any paid work, and the CLI exits 91.
6. **Not in this branch:** `_reconcile_export` writes metadata keys in
   Chroma's read order, which varies from read to read. So the export file
   changes byte by byte on every commit. That's a separate issue.

### Test results (round 6)

| Run | Result |
|---|---|
| Full suite, main `458b9f6` (hermetic) | 93 failed, 2896 passed, 66 skipped, 58 errors |
| Full suite, `c7072fc` (hermetic) | 94 failed, 2918 passed, 66 skipped, 58 errors; the extra failure is the write-guard crash-test flake above |
| That crash test re-run alone, 5 times each at main and `c7072fc` | 10 of 10 pass |
| Probes from rounds 2–5, Cursor's probe and wedge-fix tests | 41 passed |

### Next

1. **Copilot audit lane:** a targeted safety and isolation audit of the
   branch, focused on the list above.
2. **Kiro:** a design review of C1, C2 and the relaxed invariants above.
   Copilot and Kiro can run in parallel on `c7072fc`.
3. **Ryan:** opens the PR (draft below) and merges. The docs branch
   `docs/2026-10-12-issue-286-stage2-fixes-handoff` lands in its own small
   PR.
4. **Separate Ryan grants after the merge:**
   - promote `runtime-main`;
   - deploy the protocol surfaces;
   - run canary 2. Doctor's new WARN will list the 3 stale `APPLYING` Stage
     2 transactions, and canary 2 should watch them clear.

### PR draft (for Ryan; refresh after corrective 6 and the re-reviews)

**Title:** Unwedge incremental indexing after concurrent writes and stop agent
self-indexing

**Body:**

> **What changes for you:**
> - Codex and Kiro sessions stuck in a wedged incremental transaction recover
>   on their next run, by replaying forward or rolling back cleanly.
> - A repeated failure now stops after two tries instead of retrying, and paying,
>   on every file event.
> - Agents stop paying to index their own transcripts while the watcher runs.
> - Opening an old session no longer queues a paid catch-up index.
>
> **Who:** Cursor Composer implemented it; Claude verified it; Codex, standing
> in for the Copilot audit lane, audited it; Kiro reviewed it (PASS with
> conditions). Ryan merges.
> **What:**
> - one store-wide index write lock (C1);
> - source-scoped replay and rollback (C2);
> - bounded retries surfaced to the watcher and doctor (C3);
> - a watcher that ignores opens, and `index --file` deferring to a running
>   watcher (C4).
>
> **When:** follows the Stage 2 canary stop on 2026-10-12. Deploying it is a
> separate grant.
> **Why:** issue #286 Stage 2.
> - Another writer indexing during an apply wedged two sessions for good.
>   Every retry failed, because recovery demanded that foreign state match
>   the transaction start.
> - Agents' Track A self-indexing caused the second wedge.
> - Plain file opens queued paid index waves.
>
> **How:**
> - **Lock order:** `source_flock` → index write lock → Chroma writer →
>   `export_flock`. No lock is held across paid provider calls.
> - **C2:** recovery proves only what this source owns.
> - **C3:** a second identical failure on the same prefix exits with
>   `live_route_refused` (exit 91). The watcher then holds the path until its
>   prefix changes.
>
> **Relaxed invariants (Kiro accepted both; see its design review):**
> 1. Foreign export bytes and store rows no longer have to match the
>    transaction start between attempts.
> 2. Source-owned export tamper is dropped with a stderr diagnostic instead
>    of refused.
>
> **Notes:**
> - G5: a clean rollback holds the session until `convmem watch
>   --clear-quarantine`; decide after canary 2.
> - G7: `review-bundles/` was added to the R2b writer-scan skip list.
>
> **Tests:**
> - The hermetic full suite at main `458b9f6` and at the tip fails the same
>   151 known local tests. One unrelated write-guard crash test flaked once
>   at the tip, and it passes when run alone at both SHAs.
> - The new wedge-fix and probe tests are in
>   `tests/test_issue_286_stage2_wedge_fixes.py` and
>   `tests/test_issue_286_stage2_wedge_probes.py`.
>
> **Merge reading:**
> - [Handoff (spec)](https://github.com/alanmz-crypto/convmem/blob/docs/2026-10-12-issue-286-stage2-fixes-handoff/docs/inter-model/CURSOR-2026-10-12-issue-286-stage2-fixes-handoff.md)
> - [Verify, rounds 1–6](https://github.com/alanmz-crypto/convmem/blob/docs/2026-10-12-issue-286-stage2-fixes-handoff/docs/inter-model/CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md)
> - [Arc STATUS](https://github.com/alanmz-crypto/convmem/blob/docs/2026-10-12-issue-286-stage2-fixes-handoff/docs/plans/STATUS-codex-jsonl-production-integration.md)
>
> These are on branch `docs/2026-10-12-issue-286-stage2-fixes-handoff`,
> which lands in its own docs PR.
>
> **After merge, separate grants:** the `runtime-main` promotion, the
> protocol-surface deploy and canary 2.
>
> Refs #286.
>
> **TL;DR:** the fixes for the Stage 2 wedge, retry loop, self-indexing and
> open storm, verified hermetically with no paid calls. Deploying stays
> Ryan-gated.

---

# Round 5: `62fe3a2`, not ready yet (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `62fe3a2`, Cursor
Composer's corrective 4. It answers round 4 (below).
**Method:**
- I read the diff `8a8c03a..62fe3a2`.
- I ran my round-2 to round-5 probes along with Cursor's probe and wedge-fix
  tests. The appendix has the round-5 source.
- I tested the fix proposed below in a scratch copy, then reverted it.
- I ran the full suite hermetically at main `458b9f6` and at `62fe3a2`, at the
  same time and on the same disk: `env -i`, a scratch `HOME`, no API keys, and
  `tests/test_index_loud_failures.py` skipped.
- My runs touched nothing live. I compared mtimes and sizes across the live
  data root before and after.
  - The root did change between 12:03 and 12:06, from a running Codex
    session's own Track A `convmem index --file` on deployed main (writer
    attestation `ingest.write`, parent the Codex app-server).
  - It appended 5 units for one of that session's rollouts.
  - The watcher stayed inactive and disabled.

### Verdict (round 5)

**Not ready for review yet. One small fix remains, and none of it involves
paid calls.**

**Good:**
- **N1's shape is right.** The rollback now checks unit ids. The on-disk
  read, the extra store snapshot and the Chroma `InternalError` swallow are
  gone.
- **Real tamper is reported.** A tampered line with an unknown id is counted
  on the real rollback path (s1).
- **Earlier false alarms are gone.** A clean rollback of a fresh session
  prints nothing at either fault point (s2, r2). So does the Kiro bootstrap
  shape, where the export already holds legacy-writer lines (s4).
- **Rollback is correct in every probe.** The export comes back
  byte-for-byte.
- **Full suite:** main `458b9f6` and `62fe3a2` fail the same 151 tests (93
  failures, 58 errors), so 0 fail only at the tip. The tip passes 20 more
  tests: the branch's own. This matches Cursor's report and my round-3 run.

**Still open:** the message fires on a clean rollback of a session that was
already committed and then grew. That's the most common real shape (P1).

### Findings (round 5)

**P1 (medium): a clean rollback of a grown session reports "dropped N".**
- **Where:** `_restore_export` (`incremental_jsonl.py` ~1752–1760). For a
  line whose id is in the preimage, it also requires the bytes to match the
  preimage.
- **Why the bytes differ:**
  - `_reconcile_export` rewrites all of this source's lines from store rows
    with `json.dumps(payload)`, without sorted keys.
  - Chroma returns metadata keys in a different order on each read, so the
    content is identical and the bytes are new.
  - I confirmed this directly: both old lines parse to equal objects, and
    their key order differs.
- **Repro, s3:**
  - commit a Codex rollout, then append records;
  - crash the next transaction after it rewrites the export
    (`after_export_reconcile` or `before_dedupe_reconcile`);
  - the replay rolls back and restores the export exactly, but prints
    `rollback dropped 2 unexpected export lines`.
- **It also skews real counts (s5):** one line edited in place while the
  transaction is wedged is reported as 2.
- **Effect:**
  - diagnostic only;
  - the rollback is correct;
  - no burn impact.
  - But this is the shape canary 2 will hit when a growing session rolls
    back. A false tamper report there would send the next investigation the
    wrong way.
- **Whose error:** mine. N1 asked for ids only, and also for the direct
  tamper test to still report 1. That test edits a line whose id is in the
  preimage, so the two asks conflict. Cursor reconciled them with a byte
  check, which reintroduced the key-order problem.
- **Fix (about 7 lines; I tested it in a scratch copy):**
  - for an id in the preimage, compare the parsed JSON object with the
    preimage line or lines for that id, not the bytes;
  - with that change, all 38 probe and wedge-fix tests pass, including s1,
    s3, s4, s5, r2 and the direct tamper test.

**A note for Kiro, no change asked:** an unexpected line whose id the store
also holds (for example, one added while the transaction is wedged) is
removed without being counted. The rollback removes it either way. The PR
body should say the message counts lines the rollback can't account for by
id, plus in-place edits of before-image lines.

**A note, no change asked (it predates this branch):** each commit rewrites a
source's export lines in a new key order. The export file then changes byte
by byte even when its content doesn't, which only affects backup diffs.
Sorting keys in `_reconcile_export` would fix it, but it would also rewrite
every source's export lines on their next commit. That belongs in a separate
issue.

### Test results (round 5)

| Run | Result |
|---|---|
| Full suite, main `458b9f6` (hermetic) | 93 failed, 2896 passed, 66 skipped, 58 errors |
| Full suite, `62fe3a2` (hermetic) | 93 failed, 2916 passed, 66 skipped, 58 errors; same 151 ids, 0 only at the tip |
| Round-2 and round-3 probes, round-4 s1, Cursor's probe and wedge-fix tests | pass |
| s3 control: a grown session commits | pass |
| s4: Kiro bootstrap shape with a legacy-writer line, clean rollback | pass, silent |
| s3: grown session, crash after the export rewrite, clean rollback | export restored; fail, "dropped 2" at both crash points (P1) |
| s5: one preimage-id line edited while wedged | export restored; fail, reports 2 instead of 1 (P1) |
| Same probe set with the proposed fix (scratch, reverted) | 38 passed |

### Corrective 5 for Cursor

- **O1 (P1):** in `_restore_export`, compare a preimage-id line by its
  parsed JSON object, not its bytes. Add s3 (both crash points) and s5 from
  the appendix. s1, s2, s4, r2 and the direct tamper test must still pass.
- **Then:** re-pin the baseline hash and regenerate the inventories if they
  change. Run the full suite in clean detached worktrees with the convmem
  environment's python, at main and at your final tip.

**After corrective 5:** a short re-verify from me (probes, plus a suite run
if more than `incremental_jsonl.py` and its tests change). Then come the
Copilot safety and isolation audit, Kiro's design review of C1 and C2, and
Ryan's PR and merge.

---

# Round 4: `8a8c03a`, not ready yet (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `8a8c03a`, Cursor
Composer's corrective 3. It answers round 3 (below).
**Method:** I read the diff `c8436b1..8a8c03a`, then ran my round-2, round-3
and round-4 probes along with Cursor's probe and wedge-fix tests; the appendix
has the round-4 source. I read Cursor's own suite logs rather than rerunning
the full suite; I'll run it myself on the final tip.

### Verdict (round 4)

**Not ready for review yet. One item remains, and none of it involves paid
calls.**

- **L1, fixed:** doctor formats `source_path` and reads every field with
  `.get`. r1 and r1b pass. A wedge recorded by the real writer now shows as a
  WARN instead of crashing doctor.
- **L3, done:** Cursor's final run fails 94 tests at main `458b9f6` and the
  same 94 at `8a8c03a`, so 0 fail only at the tip. This matches my round-3
  result.
- **L2, not fixed:** see M1.

### Findings (round 4)

**M1 (medium): the tamper message can no longer fire on the real rollback
path.**
- **Where:** `_restore_before_images` (`incremental_jsonl.py` ~1641–1695)
  adds every source-owned line now in the export file
  (`_source_owned_export_bytes_on_disk`) to the expected set. A tampered line
  is in that file, so it counts as expected.
- **Repro:**
  - s1: append a tampered source line, then replay a transaction that fails
    at `after_summary_upsert`. The rollback prints nothing.
  - The renamed tamper test still passes, but only because it calls
    `_restore_export` directly, without the expected set.
- **Why the disk read is there:** s2. Without it, a clean rollback at
  `before_dedupe_reconcile` still reports 2 dropped lines. The bytes rebuilt
  from store rows don't match the bytes the export writer wrote. Matching on
  bytes was the wrong design, and both my G3 and L2 specs asked for it.
- **Also:** `be1d34d` swallows a Chroma `InternalError` while taking the
  extra store snapshot.
- **Fix:** compare by unit id instead of bytes.
  - **Expected ids:** the ids in the preimage source lines, plus
    `current_units`. That's this source's store unit ids, which
    `_restore_before_images` already reads before it deletes extras.
  - **Unexpected:** a source-owned line whose `id` isn't in that set counts
    as unexpected.
  - **Remove:** `_source_owned_export_bytes_on_disk`, the extra
    `snapshot_source_rows` and the `InternalError` swallow.
  - **Direct callers:** when `_restore_export` is called without ids, it
    uses the preimage ids plus `ids_for_source(UNITS)`.
  - **PR body:** say that the message counts lines whose id the rollback
    can't account for. It doesn't compare content.

### Test results (round 4)

| Run | Result |
|---|---|
| Round-2 probes, round-3 probes r1, r1b and r2 (both points), Cursor's probe and wedge-fix tests | pass |
| s1: tampered line on the real rollback path is reported | fail, nothing printed (M1) |
| s2: clean rollback without the disk read prints nothing | `after_summary_upsert` pass; `before_dedupe_reconcile` fail, "dropped 2" (M1) |
| Cursor's full suite, main `458b9f6` against `8a8c03a` | 94 and 94 failed, same ids; 0 only at the tip |

### Corrective 4 for Cursor

- **N1 (M1):** apply the id-based fix above. s1 passes: the real path
  reports 1 and the line is gone. r2 prints nothing at either point. The
  direct tamper test still reports 1.
- **Then:** re-pin the baseline hashes and regenerate the inventories if they
  change. Run the full suite in clean detached worktrees with the convmem
  environment's python, at main and at your final tip.

**After corrective 4:** I run the full suite on the final tip and do a short
re-verify. Then come the Copilot safety and isolation audit, Kiro's design
review of C1 and C2, and Ryan's PR and merge.

---

# Round 3: `c8436b1`, not ready yet (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `c8436b1`, Cursor
Composer's corrective 2. It answers round 2 (below).
**Method:**
- I read the corrective-2 diff `cb0fbfe..c8436b1` and the hand-resolved parts
  of the merge `cb0fbfe` (`git show --remerge-diff`).
- I ran my round-2 probes, Cursor's probe file and new round-3 probes; the
  appendix has the round-3 source.
- I ran the full suite hermetically at main `458b9f6` and at `c8436b1`, at the
  same time and on the same disk: `env -i`, a scratch `HOME`, no API keys, and
  `tests/test_index_loud_failures.py` skipped.
- My runs touched nothing live. I compared mtimes and sizes across the live
  data root before and after, and I read the live incremental state
  directory for counts and phases only.
- Live did change in the window, from another agent's work:
  - A Codex session that started at 03:03 indexed its own rollout (Track A)
    from 03:26:54 to 03:31:04. That was one committed incremental run with a
    transform, so probably one paid summarization pass. It ran on the
    deployed main code, which doesn't have this branch's `index --file`
    deferral for active sessions.
  - A short write session at 03:37 touched chroma and the attestations, with
    no export or processed-log growth.

### Verdict (round 3)

**Not ready for review yet. Corrective 3 is small, and none of it involves
paid calls.**

**Good since round 2:**
- **K1:** errors raised out of `run()` are now counted. A second identical
  failure on the same prefix becomes `live_route_refused` (p4 passes).
- **K4:** the watcher computes the prefix digest only when a wedge hold
  exists for that path, and Cursor's test checks it.
- **K5:** p1–p7 are in the suite as `tests/test_issue_286_stage2_wedge_probes.py`.
- **K6, the merge:** Git needed a hand resolution in only one code file,
  `convmem.py`.
  - In `add`, it keeps main's admission wrapper and the branch's index lock.
  - In `monitor`, Cursor's hand edit fixed a `NameError` the automatic merge
    would have left.
  - The other hand resolutions are the two writer inventories.
- **Full suite:** the same 151 tests fail at main `458b9f6` and at `c8436b1`,
  so 0 fail only at the tip.

**Still open:**
- the doctor wedge WARN crashes `convmem doctor` on real data (H1);
- the new rollback diagnostic fires on ordinary rollbacks (H2);
- Cursor's suite report doesn't hold up (H3).

### Findings (round 3), most severe first

**H1 (high): doctor crashes as soon as a real wedge is recorded.**
- **Where:** `_check_wedged_incremental_transactions` (`doctor.py` ~609–645)
  formats each row with `source={source}`. The writer,
  `record_incremental_retry_failure`, stores the key `source_path`.
- **Effect:** `KeyError: 'source'`. Doctor builds its checks as one list with
  no per-check guard, so the whole `convmem doctor` fails. Every agent runs
  doctor first in every session, and it would fail at exactly the moment it
  should report a wedge.
- **Why the tests missed it:**
  - Before K2, doctor never found the state directory (G2), so the bad key
    was never reached.
  - My round-2 probe p5 hand-wrote `retry_state.json` using doctor's key, not
    the writer's. Cursor copied it in as K5. That one is my mistake.
- **Live exposure today:** none. The live state directory holds no
  `retry_state.json` yet. The first one would appear after this code
  deploys.
- **Repro:**
  - r1: two calls to the real writer, then the doctor check, gives `KeyError`;
  - r1b: two raised failures through `maybe_route_incremental`, then the
    doctor check, gives the same.
- **Fix:**
  - format `source_path`;
  - read every row field with `.get`, so a malformed file can't crash doctor;
  - make p5 write through `record_incremental_retry_failure`, assert the
    check is a WARN, and add r1b.

**H2 (medium): the "dropped unexpected export lines" message fires on
ordinary rollbacks.**
- **Where:** `_restore_before_images` (`incremental_jsonl.py` ~1630–1665)
  restores the store first. It deletes this source's extra rows and writes
  back the before-image. Only then does it call `_restore_export`.
  `_restore_export` builds its "expected" set from the store as it is now,
  which is the before-image again. So every export line the failed
  transaction wrote counts as unexpected.
- **Repro:** r2. A replay that fails at `before_dedupe_reconcile`, after
  `_reconcile_export` has written the transaction's lines, rolls back
  cleanly and prints `rollback dropped 2 unexpected export lines`. Nothing
  was tampered with. At `after_summary_upsert`, before any export write, it
  prints nothing.
- **Effect:** a cosmetic message, but the wrong one. It reports tamper on a
  healthy rollback, which is exactly the misleading signal G3 was meant to
  remove. I specified "current store rows" in G3 without checking the
  restore order; that's my error.
- **Fix:**
  - in `_restore_before_images`, before the store restore, capture the
    export payloads of this source's current store rows;
  - pass that set to `_restore_export` as expected lines, alongside the
    preimage lines;
  - r2 then passes at both fault points, and the tamper test still reports
    exactly 1.

**H3 (low, evidence): Cursor's suite report doesn't hold up.**
- **No result at the real tip:** the newest row is `697df9f`, not
  `c8436b1`.
- **The 42 aren't expected:** the report calls 42 tip-only failures against
  main "expected". Round 2 had 0, and my run at `c8436b1` has 0 too.
- **Likely cause:**
  - The branch run used `~/Projects/convmem`, whose untracked `artifacts/`
    and docs files feed the R2b writer scans. Main ran in a separate
    checkout.
  - The worker processes the run spawned used `~/miniforge3/bin/python`, not
    the convmem environment's interpreter.
- **Fix:** run both SHAs in clean detached worktrees, with the convmem
  environment's python.

**A note, no change asked (K1 edge):** a raised error that leaves no prefix
digest records an empty digest. The watcher never holds a digest-less wedge,
so it re-spawns on each event. That costs nothing: these errors fire before
any paid work, and the CLI exits 91 each time.

**A note for canary 2:** the live state directory holds 3 transactions in
`APPLYING` and 1 in `transform_failed`, all older than 15 minutes. These are
the Stage 2 wedges. Once this code deploys, doctor's new stale-transaction
WARN will list the 3 `APPLYING` ones. That's correct and expected. Canary 2
should watch them clear, by rollback or by commit.

### Test results (round 3)

| Run | Result |
|---|---|
| Full suite, main `458b9f6` | 93 failed, 2896 passed, 66 skipped, 58 errors (21:49) |
| Full suite, tip `c8436b1` | 93 failed, 2912 passed, 66 skipped, 58 errors (21:57) |
| Failing test ids compared | the same 151 at both; 0 only at the tip |
| Round-2 probes p1–p7, p4b, p6 at `c8436b1` | pass (p4 and p5 now pass) |
| Cursor's probe file and wedge-fix tests | pass |
| r1, r1b: doctor fed by the real writer | fail, `KeyError: 'source'` (H1) |
| r2 at `after_summary_upsert` | pass |
| r2 at `before_dedupe_reconcile` | fail, `rollback dropped 2 unexpected export lines` (H2) |

### Corrective 3 for Cursor

- **L1 (H1):** doctor formats `source_path` and reads row fields with `.get`.
  p5 writes through the real writer and asserts a WARN; add r1b.
- **L2 (H2):** capture this source's store-row export payloads before the
  store restore and pass them to `_restore_export` as expected lines. Add r2
  for both fault points; the tamper test still reports exactly 1.
- **L3 (H3):** run both suites in clean detached worktrees
  (`git worktree add --detach`) with the convmem environment's python: one
  at main, one at your final tip. List every test that fails only at the
  tip, with its cause.
- **Then:** rerun the full suite hermetically at main and at your final tip.
  Report the tip SHA, both results, and every test that fails only at your
  tip.

**After corrective 3:** a short re-verify from me, then the Copilot safety and
isolation audit, then Kiro's design review of C1 and C2, then Ryan opens the
PR and merges.

---

# Round 2: `117d698`, not ready yet (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-13
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `117d698`, Cursor
Composer's corrective 1. It answers round 1 (below) and the handoff
`docs/inter-model/CURSOR-2026-10-12-issue-286-stage2-fixes-handoff.md`.
**Method:**
- I read the diff `da7f9a0..117d698` and ran probe tests of my own; the
  appendix has their source.
- I ran the full suite hermetically at `8a7cdab` and at `117d698`, at the same
  time and on the same disk: `env -i`, a scratch `HOME`, no API keys, and
  `tests/test_index_loud_failures.py` skipped.
- Nothing live was touched. I compared mtimes and sizes across the live data
  root before and after, and no `index_write.lock` exists there.

### Verdict (round 2)

**Not ready for review yet. Corrective 2 is small, and none of it involves
paid calls.**

**Fixed since round 1:**
- **F1:** a replay that fails after foreign growth now rolls back
  (`rolled_back`) instead of wedging. This holds both before and after
  `_reconcile_export` has rewritten the export (probes p1 and p2).
- **F2:** the real wedge marker parses all the way through the CLI and the
  watcher (p3). The hold lifts when the prefix changes. On a committed Codex
  route, the watcher's prefix digest equals the coordinator's (p7).
- **F4:** two reviewed rollback tests pass again.
- **F3 and F3b:** test 5 is hermetic. The event filter is a module-level
  function, and its test fails at `8a7cdab`.
- **F5:** `monitor` takes the index lock only around each ingest write.
- **F5a–F5d:** fixed. The retry state now lives in the source's own
  incremental state directory.
- **F6:** delete events are queued again.
- **F8:** the removed comments and the journal-hash re-check are restored.
- **Full suite:** 0 tests fail only at the tip. The same 151 tests fail or error at
  both SHAs; all are pre-existing in the hermetic environment.

**Still open:**
- two gaps in C3's safety net (G1, G2);
- a C2 deviation hidden behind a test whose name says the opposite (G3);
- a per-event cost added to the watcher (G4).

### Findings (round 2), most severe first

**G1 (medium): C3 counts only failures that `run()` returns, not errors it
raises.**
- **Where:** `maybe_route_incremental` (`incremental_jsonl.py` ~2640–2672)
  records retry state only after `coordinator.run()` returns a result that
  isn't committed. An `IncrementalJsonlError` raised out of `run()`
  propagates instead. Examples are raises from the rollback in
  `_restore_replay_before_images`:
  - the journal changed;
  - a version or source mismatch;
  - a failed file restore.

  The CLI then exits 1, and the watcher retries on every write, with no
  limit and no doctor signal. That is exactly the shape of the production
  wedge. Its two known causes are fixed now, but C3 is the backstop for
  unknown ones. I missed this in round 1.
- **Repro:**
  - p4: a run that raises `recovery_unproven` three times stays
    `recovery_unproven` and never becomes `live_route_refused`;
  - p4b: the watcher spawns once per event, 5 for 5.
- **Cost:** no paid calls in practice.
  - Most transform failures already come back as counted
    `transform_failed` refusals.
  - The only transform errors that are raised are the attempt-budget stop
    and provider refusals with HTTP 401, 402 or 403. Neither makes a billed
    call.
  - The other raises happen during replay or rollback, after the paid work
    is cached.
- **Fix:** in `maybe_route_incremental`:
  - wrap `coordinator.run()`;
  - catch an `IncrementalJsonlError` whose code is not `live_route_refused`;
  - record it with `exc.code`, using the coordinator's prefix digest or,
    failing that, the transaction's `prefix_sha256`;
  - on a repeat, raise the wedge refusal; otherwise re-raise the original
    error.

**G2 (medium): doctor's wedge WARN can never fire in production.**
- **Where:** `iter_wedged_incremental_states` reads
  `cfg["index"]["incremental_jsonl"]["state_dir"]`. The live config has the
  `incremental_jsonl` table but no `state_dir` key (I checked as booleans).
  So the coordinator uses the default
  `~/.local/share/convmem/incremental-jsonl`, and doctor finds 0 rows. The
  tests pass only because their configs set `state_dir`.
- **Repro:** p5.
- **Fix:**
  - resolve the directory with `incremental_jsonl_settings(cfg).state_dir`,
    as the coordinator does;
  - also WARN on any `transaction.json` in `APPLYING` or `PREPARING` older
    than 15 minutes. That surfaces G1-type wedges even when no retry state
    exists.

**G3 (medium, a C2 deviation): export tamper is dropped instead of refused,
and the test name says the opposite.**
- **What the code does:** `_restore_export` now `continue`s for every line
  owned by this source, whether it's allowed or not. That makes
  `_allowed_source_export_bytes` dead code: it opens a store session and the
  result is never used.
- **What the test asserts:** `test_export_tamper_still_refused` asserts that
  the tampered line is silently replaced. The handoff's C2 and test 6 said
  "refuse", and both were binding.
- **My call: accept dropping, and revise the spec.**
  - The store rollback already deletes this source's unknown rows with no
    tamper check, and the export is derived data.
  - Refusing in the export, after the store is already restored, leaves a
    half-rolled-back transaction that never recovers.
- **It must be honest and visible:**
  - delete `_allowed_source_export_bytes` and the dead branch;
  - count the source lines that are neither before-image lines nor current
    store rows. When there are any, print one line:
    `[incremental] rollback dropped N unexpected export lines for <source>`;
  - rename the test to what it checks, and assert that line;
  - the PR body names both relaxed invariants (foreign export bytes and
    tamper refusal) for Kiro's design review.

**G4 (low to medium): the watcher digests every file that's ready, even when
nothing is quarantined.**
- **Where:** `_process_ready_path` calls `source_prefix_digest_for_watch` on
  every path before it checks whether a refusal exists. Non-JSONL files are
  read whole.
- **Measured:** one parse of a synthetic 60 MiB Codex rollout took 0.26 s,
  with a 195 MiB RSS peak. The canary watcher ran at about 110 MB.
- **Fix:** compute the digest only when the breaker holds a quarantined
  `wedged_incremental_transaction_*` entry for that path.

**G5 (low; a decision, no code asked): a clean rollback quarantines the
session for good.**
- **Why:** after `rolled_back`, `maybe_route_incremental` raises
  `live_route_refused:rolled_back:…`. That isn't a wedge outcome, so the
  watcher holds the path permanently, whatever its prefix.
- **Effect:** the rollback branch of the C2 acceptance case ("roll back
  cleanly and then commit") needs `convmem watch --clear-quarantine`.
- **Recommendation:** it's burn-safe, and doctor lists it under
  `incremental_refusals`. Keep it for canary 2 and decide afterwards.

**G6 (low): the tests still don't cover the real paths.**
- Test 3 still builds the marker by hand and mocks the watcher's digest.
- **Fix:** add probes p3 and p7 from the appendix. After K1 and K2, add p4
  and p5 as passing tests.

**G7 (low): another arc's guard changed.**
- `review-bundles/` was added to the R2b writer-scan skip list. It's an
  untracked folder in Ryan's checkout.
- Fine in substance, but it changes another arc's guard, so name it in the
  PR body.

**G8 (housekeeping): main has moved.**
- `origin/main` is now `458b9f6` (#389, Safe Harbor backup binding), which
  also regenerates both writer inventories.
- Merge `origin/main` (no rebase), regenerate the inventories, and re-pin.

**A note, no change asked:** both lock paths now go through one function.
`index_write_flock_for_export` passes only the export path, so the two would
diverge only if `processed_log` and `units_export` lived in different
directories. In production they share a parent (I checked as a boolean).

### Test results (round 2)

| Run | Result |
|---|---|
| Full suite at `8a7cdab` | 2835 passed, 93 failed, 58 errors, 66 skipped |
| Full suite at `117d698` | 2842 passed, 93 failed, 58 errors, 66 skipped |
| **Failing only at the tip** | **0**; the same 151 failing test ids at both SHAs |
| Note | My runs used tmpfs, so the D1 OOM tests error at both SHAs; Cursor's on-disk runs show fewer errors. Like for like, the result is the same. |
| Live state | unchanged by my runs. The one mtime change, `source_reconciliation.json` at 01:42:07, came from the scheduled `convmem-reconcile.timer` run at 01:42:06 |
| Probes p1, p2, p3, p7 | pass |
| Probes p4, p5 | fail (G1, G2) |
| Probes p4b, p6 | pass; they document current behavior (G1, G5) |
| Digest cost, synthetic 60 MiB Codex rollout | 0.26 s, 195 MiB RSS peak per parse (G4) |

### Corrective 2 for Cursor

- **K1 (G1):** count raised `IncrementalJsonlError`s in
  `maybe_route_incremental` as described. Then p4 passes.
- **K2 (G2):** doctor resolves `state_dir` the way the coordinator does, and
  WARNs on stale `APPLYING` or `PREPARING` transactions. Then p5 passes.
- **K3 (G3):** remove the dead allow-set, add the dropped-lines diagnostic,
  and rename and fix the test.
- **K4 (G4):** digest lazily, only for paths with a wedge hold, and test that
  no digest is computed when nothing is held.
- **K5 (G6):** add p3, p4, p5 and p7 from the appendix.
- **K6 (G8):** merge `origin/main`, regenerate and re-pin, and rerun the full
  suite hermetically at the merged main tip and at your tip. Report every
  test that fails only at your tip; the target is 0.
- **PR body:** the two relaxed invariants (G3 and the foreign-export
  relaxation), the G5 note and G7.

**After corrective 2:** I do a short re-verify, then Copilot audits safety
and isolation, then Kiro does the design review of C1 and C2, then Ryan
opens the PR and merges.

---

# Round 1: `da7f9a0`, FAIL (kept for the record)

**Arc: Codex (#286), after Stage 2.**
**Date:** 2026-10-12
**Verifier:** Claude (Opus 5.5)
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes` at `da7f9a0` (Cursor
Composer), against the handoff
`docs/inter-model/CURSOR-2026-10-12-issue-286-stage2-fixes-handoff.md`.
**Method:** I read the diff and ran tests hermetically: `env -i`, a scratch
`HOME` and no API keys. Nothing live was touched. Live
`processed.json`, `knowledge_units.jsonl` and `synthesis_failures.jsonl`
were unchanged by these runs, and no `index_write.lock` exists in the live
locks directory.

### Verdict

**FAIL. Return to Cursor for corrective 1 (C1–C6 below).**
- **What's right:** the lock design (C1), the watcher's intake filter (C4a)
  and the deferral logic (C4b) are sound. The replay-forward case from the
  canary now commits.
- **What blocks it, two defects:**
  1. A wedged transaction that has to *roll back* is still wedged.
  2. The bounded-retry refusal never reaches the watcher in production.

### Findings, most severe first

**F1 (high): the rollback path still pins isolation to the
transaction-start state.**
- **Where:** `incremental_jsonl.py:2109–2122`
  `_restore_replay_before_images`. It still calls
  `_verify_non_source_collections(rollback["non_source_collections"])`, the
  digest saved when the transaction began. It also runs outside
  `index_write_flock`: the rollback's store writes happen in `_roll_forward`,
  not inside `_commit_generation`.
- **Repro (hermetic, my test):**
  1. Take Cursor's test 1.
  2. Make the replay raise an `IncrementalJsonlError` after the foreign
     growth.
  3. The rollback raises `non_source_isolation_changed` at
     `incremental_jsonl.py:1499`, called from `:2119`, instead of returning
     `rolled_back`.
- **Effect:** any wedged transaction whose replay has to roll back stays
  wedged. That covers a roll-forward refusal, a rewritten source, or any
  replay error.

**F2 (high): the C3 refusal never parses in the watcher, and would never
release if it did.**
- **The parse:** `maybe_route_incremental` builds the detail
  `wedged_incremental_transaction:<code>:transaction=<id>:source=<path>:wedged
  incremental transaction; see doctor`. The CLI keeps it whole, because its
  last field isn't a 64-hex digest, and prints
  `live_route_refused:<that>`. `_parse_refusal_line` requires the outcome
  to match `[a-z0-9_]+(:[a-z0-9_]+)*`. The `=`, `/`, `.`, `-`, the spaces
  and the `;` fail that pattern, so `parse_live_route_refused` returns
  `None`. I checked this with the real format. The watcher therefore treats
  the refusal as a plain error and keeps retrying.
- **Why the test passes:** test 3 builds a synthetic marker
  (`format_live_route_refused("wedged_incremental_transaction:rollback_export_foreign_changed",
  prefix)`), so it never exercises the production string.
- **The release:** even with parsing fixed,
  `CircuitBreakerState.has_refusal_quarantine_for_path` matches any
  quarantined entry for that path, whatever its digest. Only `clear()`
  releases it. The spec says hold the path "until its prefix changes". As
  written, an active session would stay quarantined forever.

**F3 (medium): test 5 is not hermetic.**
- **Why:** `config.CONFIG_PATH` is fixed at import time, so the test's
  `monkeypatch.setenv("HOME", ...)` doesn't redirect `load_config()`.
- **Hermetically:** the test fails with "Config not found".
- **In a normal shell:** it reads the live config. The temp rollout is not
  under the live watch roots (I checked, printing booleans only), so
  nothing is deferred. The first `index --file` then calls the real
  `run_index` against the live config, before `ingest.index` is faked.
- I could not reproduce Cursor's "5/5". I found no trace of a live write.
  Set `CONVMEM_CONFIG`, or patch `config.CONFIG_PATH`, and fake
  `ingest.index` before the first invoke.

**F3b (medium): test 4 tests a copy of the handler, not the watcher.**
- `test_watcher_intake_event_types` defines its own `Handler` class inside
  the test and asserts against that copy. It never touches `watch.py`, so
  it passes at `8a7cdab`; the handoff required it to fail there.
- From reading it, the C4a code in `run_watch` looks right, but nothing
  tests it. Move the filter into a module-level function in `watch.py`
  and test that function.

**F4 (high, confirmed by existing tests): `_restore_export` refuses this
transaction's own lines, and the tamper test is missing.**
- The new check allows only *before-image* source lines. The spec also
  allows lines this transaction wrote. If `_reconcile_export` ran before the
  failure (for example, a failure in `_reconcile_dedupe`), a later rollback
  sees after-image lines and refuses them. That is a new wedge path the
  base code didn't have.
- Handoff test 6 ("tamper still refused") was not written.
- **Confirmed regression:** two reviewed rollback tests now fail with
  `rollback_export_foreign_changed: source export line is not rollback
  authority`:
  - `test_incremental_jsonl_bootstrap_safety.py::test_export_rollback_streams_foreign_bytes_and_restores_exact_order`;
  - `test_incremental_jsonl_canary_p2_runtime_readiness.py::test_r4_documented_sequence_prepare_through_t6`.

**F5 (medium): `convmem monitor` holds the store-wide lock during network
and embedding work.**
- `monitor_command` wraps all of `run_monitor`, including the HTTPS header
  fetches and the Ollama embeddings, in `index_write_flock`. Every writer,
  including the watcher, waits for the whole monitor run.
- Take the lock only around the store and export writes.

**F5a (medium): the new `load_config()` calls tie the CLI to the default
config file.**
- `index --file` (for the deferral check), `add`, `forget` and `monitor` now
  call `load_config()` with the path fixed at import.
- **Hermetically**, 31 tests fail with exit 1 ("Config not found"):
  - 26 in `test_incremental_jsonl_codex_corrective_5.py::test_c5b_every_route_outcome_round_trips_through_cli`;
  - 4 in `test_add_severity.py`;
  - test 5.
- **In a normal shell**, those tests read the live config instead.
- **Fix:** the deferral check should not hard-fail (no config means no
  deferral). Use the same config the command already uses.

**F5b (medium): dedupe persistence now needs `index.processed_log`.**
- The lock path is derived from `processed_log`, so a `cfg` without it
  raises `KeyError` at `purge_locks.py:73`.
- This breaks 4 tests in `test_ingest_dedupe.py` and
  `test_incremental_jsonl_bootstrap_safety.py::test_transaction_bound_dedupe_is_deterministic_and_idempotent`.

**F5c (medium): a refusal now writes state.**
- `maybe_route_incremental` writes `incremental_retry/<hash>.json` under the
  data root on every non-committed outcome.
- This breaks the reviewed invariant that a refusal leaves no data behind:
  `test_incremental_jsonl_live_boundary.py::test_selected_refusal_is_visible_without_legacy_fallback`
  asserts `not (tmp_path / "data").exists()`.
- Keep the retry state out of the data root, or skip it for refusals, and
  get the invariant change reviewed.

**F5d (low): the reviewed-file hash pins were not updated.**
- `test_incremental_jsonl_canary_baseline.py`,
  `test_incremental_jsonl_canary_p2_corrective.py` and
  `test_incremental_jsonl_canary_p2_runtime_readiness.py::test_c0_baseline_hashes_unchanged`
  pin `watch.py` and other files, and they now fail.
- Re-pin them on purpose and name the files in the report, so the
  reviewers see which reviewed files changed.

**F6 (low): deleted events are no longer queued.**
- The C4a filter drops `FileDeletedEvent`. My spec omitted it, so the gap is
  mine. Repository-knowledge reconcile no longer hears tracked-file
  deletions.
- Queue `deleted` events as before.

**F7 (low): the lock's identity comes from two places.**
- `index_write_lock_path(cfg)` uses the parent of `processed_log`;
  `index_write_lock_path_for_export` uses the parent of `units_export`. They
  are the same in production, but a config that splits them gets two locks,
  while the thread-local depth counter treats them as one.
- `index_write_flock` asserts lock order even when the lock is already held
  (the `_for_export` variant doesn't).

**F8 (low): unrelated removals.**
- Three explanatory comments were deleted in `ingest.py` and `convmem.py`.
- The post-apply re-check of the rollback-journal hash in
  `_commit_generation` was removed. The handoff said to keep the other
  authority checks unchanged.

### Test results

All runs are hermetic: `env -i`, a scratch `HOME` and no API keys. The
regression set is 54 test files covering add, doctor, export, incremental,
ingest, dedupe, locks, watch and the protocol, plus the new file.
`test_index_loud_failures.py` is excluded: it writes live state until
`eaae6e9` lands.

| Run | Result |
|---|---|
| Cursor's 5 new tests at `8a7cdab` | 3 fail as expected; test 5 errors on the missing config; **test 4 passes** (F3b) |
| Cursor's 5 new tests at `da7f9a0` | 4 pass; **test 5 fails** (F3) |
| Regression set at `8a7cdab` | 657 passed, 12 failed, 27 errors (all pre-existing in the hermetic environment) |
| Regression set at `da7f9a0` | 620 passed, 54 failed, 27 errors |
| **Failing only at the tip** | **42**: F4 (2), F5a (31, with test 5), F5b (5), F5c (1), F5d (3) |
| Failing only at main | 0 |
| My F1 repro (a replay error after foreign growth) | fails at the tip with `non_source_isolation_changed` |
| My F2 check (the real refusal line put through the watcher's parser) | `None` |
| Protocol tests (`test_bounded_autonomy_protocol.py`, `test_team_charter_protocol.py`) | pass |


### Corrective 1 for Cursor

- **C1:** `_restore_replay_before_images` and every rollback path run under
  `index_write_flock`. They verify isolation against a digest taken at the
  start of *this* rollback, under the lock, not the journal's digest. Add
  my repro as a test: a replay error after foreign growth must give
  `rolled_back`.
- **C2:** emit the wedge refusal as a parseable marker, for example
  `live_route_refused:wedged_incremental_transaction_<code>:<prefix_sha256>`,
  and put the transaction id and source on a separate diagnostic line.
  Release the refusal quarantine when the path's prefix digest changes.
  Test this end to end with the real CLI output, and test the release on a
  prefix change.
- **C3:** make test 5 hermetic (`CONVMEM_CONFIG` or `config.CONFIG_PATH`),
  with `ingest.index` faked before any invoke.
- **C3b:** move the C4a event filter into a module-level `watch.py` function
  that `run_watch`'s handler calls, and test it, so the test fails at
  `8a7cdab`.
- **C4:** `_restore_export` accepts before-image lines plus this source's
  current store rows as `_reconcile_export` would write them. Add test 6
  (tamper still refused) and an after-image rollback test.
- **C5:** narrow `monitor`'s lock to the store and export writes.
- **C5a:** fix F5a, F5b and F5c, and re-pin F5d on purpose. **Run the full
  suite hermetically** (`env -i`, scratch `HOME`, `CONVMEM_CONFIG` unset)
  and report every test that fails at the tip but not at `8a7cdab`. The
  target is 0.
- **C6:** queue deleted events again. Use one lock-path function. Make
  re-entry skip the order assert. Restore the removed comments and the
  journal-hash re-check.

## Appendix: round-21 probes and diff-coverage script

<details><summary>tests/test_zz_claude_verify21.py</summary>

```python
"""Claude verify probes, round 21 (74c8ee7): run the changed paths no test executed (diff coverage).

Scratch only: real production store sessions against a scratch config; fake providers; no network.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json

from tests.test_zz_claude_verify15 import _depth_embed, _foreign_update, _obs, _seed
from tests.test_zz_claude_verify9 import _real_session_env


def test_v1_approved_ledger_recovers_from_one_drift(tmp_path, monkeypatch) -> None:
    """propose_decision.py:639-653: first commit drifts, the retry re-prepares outside C1 and commits."""
    import propose_decision
    import purge_locks

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_v21_appr", "Old text.")
    unit, = _seed(cfg, rec)
    depths = []
    _depth_embed(monkeypatch, depths)
    real_flock, calls = purge_locks.index_write_flock, {"n": 0}

    def flock(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            _foreign_update(cfg, unit["id"], "foreign change")  # its own flock call is n == 2
        return real_flock(*a, **k)

    monkeypatch.setattr(purge_locks, "index_write_flock", flock)
    stats = propose_decision.ingest_approved_ledger(cfg, {**rec, "summary": "New approved text."})
    print(f"\nV1 stats={stats} flock_calls={calls['n']} depths={depths}")
    assert stats["updated"] == 1, stats
    assert depths and all(d == (0, 0) for d in depths), depths


def test_v2_approved_ledger_refuses_persistent_drift(tmp_path, monkeypatch) -> None:
    """Drift on both rounds: a clean refusal, not a crash or a write."""
    import pytest

    import propose_decision
    import purge_locks
    from observe import ObservationIngestDriftRefusedError

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_v21_appr2", "Old text.")
    unit, = _seed(cfg, rec)
    _depth_embed(monkeypatch, [])
    real_flock, state = purge_locks.index_write_flock, {"n": 0, "busy": False}

    def flock(*a, **k):
        if not state["busy"]:
            state["n"] += 1
            state["busy"] = True
            try:
                _foreign_update(cfg, unit["id"], f"foreign change {state['n']}")
            finally:
                state["busy"] = False
        return real_flock(*a, **k)

    monkeypatch.setattr(purge_locks, "index_write_flock", flock)
    with pytest.raises(ObservationIngestDriftRefusedError):
        propose_decision.ingest_approved_ledger(cfg, {**rec, "summary": "New approved text."})


def _dedupe_setup(tmp_path, monkeypatch):
    import refine
    from chroma_store import UNITS, ChromaStore

    cfg = _real_session_env(tmp_path, monkeypatch)
    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        col = store._collection(UNITS)
        ids = [f"u_dd_{i}" for i in range(4)]
        col.add(ids=ids, documents=[f"near-duplicate text {i}" for i in range(4)],
                metadatas=[{"title": f"dup {i}", "source_path": f"/scratch/d{i}.jsonl", "domain": "general"}
                           for i in range(4)],
                embeddings=[[1.0, 0.0, 0.0] for _ in range(4)])
    finally:
        store.close()
    rows = [{"event_id": f"e{i}", "id_a": ids[2 * i], "id_b": ids[2 * i + 1], "similarity": 0.99,
             "status": "approved_merge_a_canonical", "canonical_id": ids[2 * i], "tombstone_id": ids[2 * i + 1]}
            for i in range(2)]
    queue = refine.dedupe_queue_path(cfg)
    queue.parent.mkdir(parents=True, exist_ok=True)
    queue.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return cfg, queue, ids


def _superseded(cfg, unit_id):
    from chroma_store import ChromaStore, is_superseded

    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        unit = store.get_unit(unit_id)
        return bool(unit and is_superseded(unit.get("metadata") or {}))
    finally:
        store.close()


def test_v3_approve_dedupe_one_line_then_all(tmp_path, monkeypatch) -> None:
    """refine.py:323-346: `--approve-dedupe 1`, then `all`; tombstones land, the queue records it, no error."""
    import refine

    cfg, queue, ids = _dedupe_setup(tmp_path, monkeypatch)
    one = refine.apply_approved_dedupe("1", verbose=False)
    after_one = [json.loads(x) for x in queue.read_text().splitlines()]
    rest = refine.apply_approved_dedupe("all", verbose=False)
    after_all = [json.loads(x) for x in queue.read_text().splitlines()]
    print(f"\nV3 one={one} all={rest} applied={[r.get('chroma_applied') for r in after_all]} "
          f"superseded={[_superseded(cfg, i) for i in ids]}")
    assert one["tombstoned"] == 1 and one["errors"] == 0, one
    assert after_one[0].get("chroma_applied") is True and not after_one[1].get("chroma_applied"), after_one
    assert rest["errors"] == 0 and rest["tombstoned"] == 1, rest
    assert [_superseded(cfg, i) for i in ids] == [False, True, False, True]
    assert all(r.get("chroma_applied") is True for r in after_all), after_all


def test_v4_approve_dedupe_out_of_range_refuses_cleanly(tmp_path, monkeypatch) -> None:
    import pytest

    import refine

    _dedupe_setup(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="out of range"):
        refine.apply_approved_dedupe("9", verbose=False)
```

</details>

<details><summary>diffcov.py (scratch; run after `coverage json`)</summary>

```python
"""Changed-but-never-executed lines: git diff BASE..HEAD (added/modified lines) x coverage JSON missing lines.

Usage: python diffcov.py <worktree> <base> <coverage.json>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

wt, base, cov_json = sys.argv[1], sys.argv[2], sys.argv[3]
cov = json.load(open(cov_json))
files = {Path(k).name: v for k, v in cov["files"].items()}
diff = subprocess.run(["git", "-C", wt, "diff", "-U0", f"{base}..HEAD", "--", *files], capture_output=True,
                      text=True, check=True).stdout
changed: dict[str, set[int]] = {}
cur = None
for line in diff.splitlines():
    if line.startswith("+++ b/"):
        cur = Path(line[6:]).name
        changed.setdefault(cur, set())
    m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
    if m and cur:
        start, count = int(m.group(1)), int(m.group(2) or 1)
        changed[cur].update(range(start, start + count))
tot_exec = tot_miss = 0
report = []
for name, lines in sorted(changed.items()):
    f = files.get(name)
    if not f:
        continue
    executable = set(f["executed_lines"]) | set(f["missing_lines"])
    ch_exec = lines & executable
    miss = sorted(lines & set(f["missing_lines"]))
    tot_exec += len(ch_exec)
    tot_miss += len(miss)
    report.append((name, len(ch_exec), miss))
print(f"changed executable lines: {tot_exec}; never executed: {tot_miss} "
      f"({100 * (1 - tot_miss / max(1, tot_exec)):.1f}% covered)")
for name, n, miss in report:
    runs, start, prev = [], None, None
    for ln in miss:
        if start is None:
            start = prev = ln
        elif ln == prev + 1:
            prev = ln
        else:
            runs.append((start, prev)); start = prev = ln
    if start is not None:
        runs.append((start, prev))
    shown = ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in runs)
    print(f"{name}: {n} changed executable, {len(miss)} never run: {shown}")
```

</details>

## Appendix: round-20 probe test

Runs from `tests/` with helpers already on the branch. Real route against a scratch config; fake
providers; slowed fake summaries; 8 threads and 6 forked processes on one source.

<details><summary>tests/test_zz_claude_verify20.py</summary>

```python
"""Claude verify probes, round 20 (928700b): concurrent entrants on one source stay within the paid-attempt cap.

Scratch only: the real route against a scratch config; fake providers; no network. Summaries are slowed so
callers pile up on the source lock; each paid summary appends one line to a scratch file (shared across processes).
"""

from __future__ import annotations

import json
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


def _setup(tmp_path, monkeypatch, ledger: Path):
    import time

    import incremental_jsonl as inc
    import ingest
    from tests.incremental_jsonl_helpers import fake_summarize
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)

    def summarize(*args, **kwargs):
        with open(ledger, "a", encoding="utf-8") as fh:
            fh.write(f"{os.getpid()}\n")
        time.sleep(0.2)
        return fake_summarize(*args, **kwargs)

    monkeypatch.setattr(ingest, "summarize", summarize)

    def fail(*_a, **_k):
        raise OSError("scratch prepared artifact failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    state = (Path(cfg["index"]["incremental_jsonl"]["state_dir"])
             / inc.source_state_id(str(source.resolve()), format_id="jsonl_codex_rollout") / "retry_state.json")
    return route, state


def _invoke(route):
    import incremental_jsonl as inc

    try:
        route()
        return "ok"
    except inc.IncrementalJsonlError as exc:
        return exc.code


def _child(route, out):
    out.put(_invoke(route))


@pytest.mark.parametrize("mode,callers", [("threads", 8), ("processes", 6)])
def test_c20_concurrent_entrants_stay_within_the_cap(tmp_path, monkeypatch, mode, callers) -> None:
    ledger = tmp_path / "paid.log"
    route, state = _setup(tmp_path, monkeypatch, ledger)
    if mode == "threads":
        with ThreadPoolExecutor(max_workers=callers) as pool:
            results = list(pool.map(lambda _: _invoke(route), range(callers)))
    else:
        ctx = multiprocessing.get_context("fork")
        out = ctx.Queue()
        procs = [ctx.Process(target=_child, args=(route, out)) for _ in range(callers)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=120)
        results = [out.get(timeout=5) for _ in procs]
    paid = ledger.read_text().splitlines() if ledger.exists() else []
    saved = json.loads(state.read_text()) if state.exists() else {}
    print(f"\nC20 {mode} callers={callers} paid={len(paid)} attempts={saved.get('attempts_on_prefix')} "
          f"results={sorted(results)}")
    assert len(paid) <= 3, len(paid)
    assert int(saved.get("attempts_on_prefix") or 0) == len(paid), (saved.get("attempts_on_prefix"), len(paid))
```

</details>

## Appendix: round-17 probe test

It runs from `tests/` and imports `_real_session_env` from `tests/test_zz_claude_verify9.py`,
on the branch. Scratch config and store; no providers. At `700b6ba` it counts 21 passes over
the units collection for 20 decisions.

<details><summary>tests/test_zz_claude_verify17.py</summary>

```python
"""Claude verify probes, round 17 (700b6ba): the dry-run repair (run by `convmem doctor`) must not scan per decision.

Scratch only: a scratch config and store; no providers; no network.
"""

# pylint: disable=protected-access

from __future__ import annotations

from tests.test_zz_claude_verify9 import _real_session_env


def test_r1_dry_run_repair_reads_documents_without_a_scan_per_decision(tmp_path, monkeypatch) -> None:
    import chroma_readonly
    from chroma_store import UNITS, ChromaStore
    from ledger import invalidate_ledger_index_cache
    from observe import repair_empty_ledger_documents

    cfg = _real_session_env(tmp_path, monkeypatch)
    chroma_dir = cfg["index"]["chroma_dir"]
    store = ChromaStore(chroma_dir)
    try:
        col = store._collection(UNITS)
        n_fill, n_dec = 200, 20
        col.add(ids=[f"u_fill_{i}" for i in range(n_fill)], documents=[f"filler {i}" for i in range(n_fill)],
                metadatas=[{"title": f"filler {i}", "source_path": f"/scratch/f{i}.jsonl"} for i in range(n_fill)],
                embeddings=[[0.1, 0.2, 0.3] for _ in range(n_fill)])
        col.add(ids=[f"u_dec_{i}" for i in range(n_dec)], documents=[f"Decision text {i}" for i in range(n_dec)],
                metadatas=[{"ledger_id": f"dec_v17_{i}", "ledger_kind": "decision", "title": f"Decision {i}"}
                           for i in range(n_dec)],
                embeddings=[[0.1, 0.2, 0.3] for _ in range(n_dec)])
    finally:
        store.close()
    invalidate_ledger_index_cache(chroma_dir)
    passes = []
    real = chroma_readonly.iter_collection_metadata_rows

    def counting(chroma, collection, *a, **k):
        if collection == UNITS:
            passes.append(1)
        return real(chroma, collection, *a, **k)

    monkeypatch.setattr(chroma_readonly, "iter_collection_metadata_rows", counting)
    stats = repair_empty_ledger_documents(cfg, dry_run=True, verbose=False)
    print(f"\nR1 unit-collection passes={len(passes)} stats={stats}")
    assert stats["scanned"] == n_dec and stats["empty"] == 0, stats
    assert len(passes) <= 2, len(passes)
```

</details>

## Appendix: round-16 probe tests

They run from `tests/` and import helpers from `tests/test_zz_claude_verify15.py` and
`tests/test_zz_claude_verify9.py`, both on the branch. Real production store sessions against
a scratch config; fake providers; no network. `perf16_commit_scans.py` is not a test: it runs
against round 11's synthetic 109,000-unit store (built by a script in that round) and prints
the full scans and seconds inside one batch commit.

<details><summary>tests/test_zz_claude_verify16.py</summary>

```python
"""Claude verify probes, round 16 (2ffaf79): one ledger id on several lines of one file.

Scratch only: real production store sessions against a scratch config; fake providers; no network.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json

import pytest

from tests.test_zz_claude_verify15 import _commit_fn, _depth_embed, _FreshReader, _obs, _seed
from tests.test_zz_claude_verify9 import _real_session_env


def _rows(cfg, lid):
    from chroma_store import ChromaStore

    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        return [m for m in store.units_metadata() if m.get("ledger_id") == lid]
    finally:
        store.close()


@pytest.mark.parametrize("copies,seeded", [(2, False), (3, False), (2, True), (3, True)])
def test_u1_repeated_ledger_id_in_one_file(tmp_path, monkeypatch, copies, seeded) -> None:
    from observe import ingest_observation_file_with_drift_retry

    cfg = _real_session_env(tmp_path, monkeypatch)
    lid = f"obs_v16_dup_{copies}_{int(seeded)}"
    if seeded:
        _seed(cfg, _obs(lid, "Seeded text."))
    path = tmp_path / "obs.jsonl"
    path.write_text("".join(json.dumps(_obs(lid, f"Version {i}.")) + "\n" for i in range(copies)))
    _depth_embed(monkeypatch, [])
    owc, calls = _commit_fn(cfg)
    try:
        result, err = ingest_observation_file_with_drift_retry(
            str(path), embed_store=_FreshReader(cfg["index"]["chroma_dir"]), open_write_commit=owc,
            embed_model="fake", ollama_host="offline", upsert=True, verbose=False), None
    except Exception as exc:  # noqa: BLE001
        result, err = None, repr(exc)[:160]
    rows = _rows(cfg, lid)
    summary = (rows[0].get("summary") or rows[0].get("title")) if rows else None
    print(f"\nU1 copies={copies} seeded={seeded} rounds={calls['n']} err={err} result={result} "
          f"rows={len(rows)} summary={summary!r}")
    assert err is None and len(rows) == 1 and calls["n"] == 1, (calls["n"], err, len(rows))
    assert summary == f"Version {copies - 1}.", summary  # last line wins, as on main


def test_n4_real_add_file_upsert_survives_a_drift_round(tmp_path, monkeypatch) -> None:
    """The real `convmem add --file --upsert` command; only the Restic admission body is stubbed (still single-use)."""
    from typer.testing import CliRunner

    import convmem
    import purge_locks

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_v16_n4", "Old text.")
    unit, = _seed(cfg, rec)
    path = tmp_path / "upsert.jsonl"
    path.write_text(json.dumps({**rec, "summary": "New text from the file."}) + "\n")
    _depth_embed(monkeypatch, [])
    opens, flocks = [], {"n": 0}

    def admission_steps(_entrypoint, _governed, _expected_cfg):
        opens.append(1)
        yield

    real_flock = purge_locks.index_write_flock

    def flock(*a, **k):
        flocks["n"] += 1
        if flocks["n"] == 1:
            from tests.test_zz_claude_verify15 import _foreign_update
            _foreign_update(cfg, unit["id"], "foreign change")
        return real_flock(*a, **k)

    monkeypatch.setattr(convmem, "_admission_steps", admission_steps)
    monkeypatch.setattr(purge_locks, "index_write_flock", flock)
    res = CliRunner().invoke(convmem.app, ["add", "--file", str(path), "--upsert"])
    print(f"\nN4 exit={res.exit_code} opens={len(opens)} exc={res.exception!r} out={res.output[-160:]!r}")
    assert res.exit_code == 0 and len(opens) == 2 and "updated=1" in res.output, res.output


def test_s1_batch_commit_does_no_full_store_scan_under_c1(tmp_path, monkeypatch) -> None:
    """Validation under C1 must not rescan the whole store (one 10 s scan per row at 109k units)."""
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from observe import commit_prepared_observation_file_rows, prepare_observation_file_rows
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    recs = [_obs(f"obs_v16_s{i}", "Old text.") for i in range(3)]
    _seed(cfg, *recs)
    path = tmp_path / "obs.jsonl"
    path.write_text("".join(json.dumps({**r, "summary": "New text."}) + "\n" for r in recs)
                    + json.dumps(_obs("obs_v16_s_new", "Brand new.")) + "\n")
    _depth_embed(monkeypatch, [])
    rows, _ = prepare_observation_file_rows(str(path), embed_store=open_readonly_unit_store(cfg["index"]["chroma_dir"]),
                                            embed_model="fake", ollama_host="offline", upsert=True)
    scans = []
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify16.s1") as session:
            inner = session.store
            real = inner.units_metadata
            monkeypatch.setattr(inner, "units_metadata", lambda *a, **k: scans.append(1) or real(*a, **k),
                                raising=False)
            stats = commit_prepared_observation_file_rows(rows, store=inner, upsert=True, verbose=False)
    print(f"\nS1 full_scans={len(scans)} stats={stats}")
    assert stats["updated"] == 3 and stats["accepted"] == 1, stats
    assert scans == [], len(scans)
```

</details>

<details><summary>perf16_commit_scans.py (scratch; run with PYTHONPATH at the checkout)</summary>

```python
"""Round 16 perf probe: full-store scans and time inside the batch commit (the C1 critical section).

Usage: python perf16_commit_scans.py <chroma_dir> <n_rows>
Scratch store only (synthetic 109k units); fake embeddings; no network.
"""
import sys
import time

from chroma_store import ChromaStore
from ledger import invalidate_ledger_index_cache
from observe import (commit_prepared_observation_file_rows, ingest_observation,
                     prepare_observation_ingest)

path, n = sys.argv[1], int(sys.argv[2])
EMB = [0.5] * 16


class Counting:
    """Delegates to the store; counts and times full metadata scans."""

    def __init__(self, inner):
        self._inner = inner
        self.scans = 0
        self.scan_secs = 0.0

    def units_metadata(self, *a, **k):
        t = time.perf_counter()
        try:
            return self._inner.units_metadata(*a, **k)
        finally:
            self.scans += 1
            self.scan_secs += time.perf_counter() - t

    def __getattr__(self, name):
        return getattr(self._inner, name)


def obs(i, summary):
    return {"id": f"obs_perf16_{i}", "title": f"Perf {i}", "summary": summary,
            "keywords": ["perf", "scratch", "verify"], "author_model": "claude-verify",
            "type": "observation", "domain": "coding.tooling", "confidence": 0.9}


store = ChromaStore(path, mutation_sink=None)
try:
    tag = str(time.time_ns())
    for i in range(n):
        ingest_observation(obs(i, f"old {tag}"), store=store, embed_model="fake", ollama_host="offline",
                           upsert=True, precomputed_embedding=EMB)
    invalidate_ledger_index_cache(path)
    rows = []
    for i in range(n):
        p = prepare_observation_ingest(obs(i, f"new {tag}"), store=store, embed_model="fake",
                                       ollama_host="offline", upsert=True, precomputed_embedding=EMB)
        assert p is not None and p.upsert_update, p
        rows.append((i + 1, p))
    counting = Counting(store)
    t = time.perf_counter()
    stats = commit_prepared_observation_file_rows(rows, store=counting, upsert=True, verbose=False)
    total = time.perf_counter() - t
    print(f"rows={n}\tscans={counting.scans}\tscan_secs={counting.scan_secs:.1f}\tcommit_secs={total:.1f}\tstats={stats}")
finally:
    store.close()
```

</details>

## Appendix: round-15 probe tests

They run from `tests/` and import `_real_session_env` from `tests/test_zz_claude_verify9.py`,
already on the branch. Real production store sessions against a scratch config; fake
providers; provider hosts point at a closed port.

<details><summary>tests/test_zz_claude_verify15.py</summary>

```python
"""Claude verify probes, round 15 (8d6ee76): corrective 12's drift retry, insert race, limiter, guard.

Scratch only: real production store sessions against a scratch config; fake providers; no network.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tests.test_zz_claude_verify9 import _real_session_env


def _obs(lid: str, summary: str) -> dict:
    return {"id": lid, "title": f"Probe {lid}", "summary": summary,
            "keywords": ["probe", "scratch", "verify"], "author_model": "claude-verify",
            "type": "observation", "domain": "coding.tooling", "confidence": 0.9}


def _seed(cfg, *records):
    from chroma_store import ChromaStore
    from ledger import invalidate_ledger_index_cache
    from observe import ingest_observation

    seed = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        units = [ingest_observation(r, store=seed, embed_model="fake", ollama_host="offline",
                                    upsert=True, precomputed_embedding=[0.1, 0.2, 0.3]) for r in records]
    finally:
        seed.close()
    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    return units


def _foreign_update(cfg, unit_id: str, text: str) -> None:
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock

    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify15.foreign") as session:
            fresh = session.store.get_unit(unit_id)
            session.store.update_unit(unit_id, text, [0.1, 0.2, 0.3], fresh["metadata"])


def _depth_embed(monkeypatch, depths):
    import llm
    from chroma_write_store import production_chroma_store_session_depth
    from purge_locks import index_write_lock_depth

    def embed(*_a, **_k):
        depths.append((index_write_lock_depth(), production_chroma_store_session_depth()))
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(llm, "ollama_embed", embed)


def _commit_fn(cfg, foreign=None):
    """Like convmem.add's open_write_commit; runs `foreign` once, before the first commit."""
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock

    calls = {"n": 0}

    def open_write_commit(commit):
        calls["n"] += 1
        if foreign and calls["n"] == 1:
            foreign()
        with index_write_flock(cfg):
            with production_chroma_write_session(entrypoint="claude_verify15.commit") as session:
                return commit(session.store, None)

    return open_write_commit, calls


class _FreshReader:
    """A readonly reader reopened on every call, to separate snapshot staleness from other effects."""

    def __init__(self, chroma_dir):
        self.chroma_dir = str(chroma_dir)

    def __getattr__(self, name):
        from chroma_readonly import open_readonly_unit_store
        from ledger import invalidate_ledger_index_cache

        invalidate_ledger_index_cache(self.chroma_dir)
        return getattr(open_readonly_unit_store(self.chroma_dir), name)


def test_c0_unchanged_and_changed_rows_commit_without_false_drift(tmp_path, monkeypatch) -> None:
    """Control: prepared from the readonly reader, committed to the write store, nothing foreign in between."""
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from observe import commit_observation_ingest, prepare_observation_ingest
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    same, changed = _obs("obs_v15_same", "Stays the same."), _obs("obs_v15_chg", "Old text.")
    _seed(cfg, same, changed)
    _depth_embed(monkeypatch, [])
    reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    p_same = prepare_observation_ingest(same, store=reader, embed_model="fake", ollama_host="offline", upsert=True)
    p_chg = prepare_observation_ingest({**changed, "summary": "New text."}, store=reader, embed_model="fake",
                                       ollama_host="offline", upsert=True)
    assert p_same.skipped_unchanged and p_chg.upsert_update
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify15.c0") as session:
            a = commit_observation_ingest(p_same, store=session.store)
            b = commit_observation_ingest(p_chg, store=session.store)
    assert a.get("_skipped") and b.get("_upserted")


def test_d1_single_row_drift_retry_recovers(tmp_path, monkeypatch) -> None:
    """Spec C2: on drift, release, re-prepare outside C1, commit again. Uses the caller's real reader."""
    from chroma_readonly import open_readonly_unit_store
    from observe import ingest_observation_file_with_drift_retry

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_v15_d1", "Old text.")
    unit, = _seed(cfg, rec)
    path = tmp_path / "obs.jsonl"
    path.write_text(json.dumps({**rec, "summary": "New text from the file."}) + "\n")
    depths = []
    _depth_embed(monkeypatch, depths)
    owc, calls = _commit_fn(cfg, lambda: _foreign_update(cfg, unit["id"], "foreign change"))
    try:
        result, err = ingest_observation_file_with_drift_retry(
            str(path), embed_store=open_readonly_unit_store(cfg["index"]["chroma_dir"]),
            open_write_commit=owc, embed_model="fake", ollama_host="offline", upsert=True, verbose=False), None
    except Exception as exc:  # noqa: BLE001
        result, err = None, repr(exc)[:160]
    assert all(d == (0, 0) for d in depths), depths
    assert err is None, ("commit rounds:", calls["n"], err)
    assert result["updated"] == 1, result


def test_d2_single_row_drift_retry_with_a_fresh_reader(tmp_path, monkeypatch) -> None:
    """Same as d1 but the reader is reopened on each call: isolates snapshot staleness."""
    from observe import ingest_observation_file_with_drift_retry

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_v15_d2", "Old text.")
    unit, = _seed(cfg, rec)
    path = tmp_path / "obs.jsonl"
    path.write_text(json.dumps({**rec, "summary": "New text from the file."}) + "\n")
    _depth_embed(monkeypatch, [])
    owc, calls = _commit_fn(cfg, lambda: _foreign_update(cfg, unit["id"], "foreign change"))
    result = ingest_observation_file_with_drift_retry(
        str(path), embed_store=_FreshReader(cfg["index"]["chroma_dir"]), open_write_commit=owc,
        embed_model="fake", ollama_host="offline", upsert=True, verbose=False)
    assert result["updated"] == 1 and calls["n"] == 2, (result, calls)


def test_d3_batch_drift_on_a_later_row_recovers(tmp_path, monkeypatch) -> None:
    """Two changed rows; only row 2 drifts. Row 1 is committed in round 1; round 2 must not trip on it."""
    from observe import ingest_observation_file_with_drift_retry

    cfg = _real_session_env(tmp_path, monkeypatch)
    r1, r2 = _obs("obs_v15_b1", "Old one."), _obs("obs_v15_b2", "Old two.")
    _u1, u2 = _seed(cfg, r1, r2)
    path = tmp_path / "obs.jsonl"
    path.write_text(json.dumps({**r1, "summary": "New one."}) + "\n" + json.dumps({**r2, "summary": "New two."}) + "\n")
    _depth_embed(monkeypatch, [])
    owc, calls = _commit_fn(cfg, lambda: _foreign_update(cfg, u2["id"], "foreign change"))
    try:
        result, err = ingest_observation_file_with_drift_retry(
            str(path), embed_store=_FreshReader(cfg["index"]["chroma_dir"]), open_write_commit=owc,
            embed_model="fake", ollama_host="offline", upsert=True, verbose=False), None
    except Exception as exc:  # noqa: BLE001
        result, err = None, repr(exc)[:160]
    assert err is None, ("commit rounds:", calls["n"], err)
    assert result["updated"] == 2, result


def test_i1_insert_race_is_revalidated(tmp_path, monkeypatch) -> None:
    """Spec D: a row prepared against 'no target' must not commit over a target that appeared since."""
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from ledger import invalidate_ledger_index_cache
    from observe import (ObservationIngestDriftError, commit_observation_ingest, ingest_observation,
                         prepare_observation_ingest)
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    _depth_embed(monkeypatch, [])
    rec = _obs("obs_v15_ins", "Mine, prepared first.")
    reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    prepared = prepare_observation_ingest(rec, store=reader, embed_model="fake", ollama_host="offline", upsert=True)
    assert not prepared.upsert_update and not prepared.skipped_unchanged
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify15.foreign") as session:
            ingest_observation({**rec, "summary": "Foreign, inserted after my prepare."}, store=session.store,
                               embed_model="fake", ollama_host="offline", upsert=True,
                               precomputed_embedding=[0.1, 0.2, 0.3])
    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    outcome = "committed"
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify15.commit") as session:
            try:
                commit_observation_ingest(prepared, store=session.store)
            except ObservationIngestDriftError:
                outcome = "drift"
            rows = [m for m in session.store.units_metadata() if m.get("ledger_id") == "obs_v15_ins"]
    assert outcome == "drift", (outcome, len(rows))


def test_l1_semantic_dedupe_limiter_keeps_what_it_counted(tmp_path, monkeypatch) -> None:
    """The batched append must not drop candidates found before the hourly cap stops the job."""
    import refine

    cfg = _real_session_env(tmp_path, monkeypatch)
    vectors = Mock()
    vectors.get_units_with_embeddings.return_value = [
        {"id": x, "metadata": {"domain": "general"}, "embedding": [1.0, 0.0]} for x in ("a", "b", "c")]
    monkeypatch.setattr(refine, "ChromaStore", lambda *a, **k: vectors)
    limiter = Mock()
    limiter.allow.side_effect = [True, False, False, False]
    stats = refine.job_semantic_dedupe(None, cfg, verbose=False, limiter=limiter)
    queue = refine.dedupe_queue_path(cfg)
    lines = queue.read_text().splitlines() if queue.exists() else []
    assert stats["queued"] == len(lines), (stats, len(lines))


@pytest.mark.parametrize("call", ["embed", "summarize", "distill"])
def test_g1_real_provider_entry_refuses_under_c1(tmp_path, monkeypatch, call) -> None:
    """The runtime guard fires before any HTTP (hosts point at a closed port)."""
    import distill
    import llm
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    fn = {"embed": lambda: llm.ollama_embed("x", model="fake", host="http://127.0.0.1:9"),
          "summarize": lambda: llm.summarize("x", model="fake", ollama_host="http://127.0.0.1:9",
                                             deepseek_base_url="http://127.0.0.1:9"),
          "distill": lambda: distill.distill_with_response("x", model="fake", ollama_host="http://127.0.0.1:9",
                                                           deepseek_base_url="http://127.0.0.1:9")}[call]
    with index_write_flock(cfg):
        with pytest.raises(RuntimeError, match="provider calls are forbidden"):
            fn()
```

</details>

## Appendix: round-12 probe and corrective-11 diff

The Crush probe runs from `tests/` and imports `_route_fixture` from
`tests/test_zz_codex_audit.py`, already on the branch. It uses counting fake
providers; nothing is paid. The diff is the Y0 fix I proved in a disk-backed
scratch worktree at `41561ef`.

<details><summary>tests/test_zz_claude_verify12.py (issue #393)</summary>

```python
"""Claude verify probe, round 12: does a changed Crush database re-pay every chunk? Scratch only, fake providers."""

from __future__ import annotations

import json
import sqlite3
import traceback
from pathlib import Path
from unittest import mock

from tests.test_zz_codex_audit import _route_fixture

_SCHEMA = """
CREATE TABLE goose_db_version (id INTEGER PRIMARY KEY AUTOINCREMENT, version_id INTEGER NOT NULL,
    is_applied INTEGER NOT NULL, tstamp TIMESTAMP DEFAULT (datetime('now')));
CREATE TABLE sessions (id TEXT PRIMARY KEY, title TEXT NOT NULL, message_count INTEGER NOT NULL DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0, completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0.0, updated_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE messages (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL,
    parts TEXT NOT NULL DEFAULT '[]', model TEXT, provider TEXT, created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL, finished_at INTEGER);
"""


def _add_messages(db: Path, start: int, count: int) -> None:
    con = sqlite3.connect(db)
    try:
        if start == 0:
            con.executescript(_SCHEMA)
            con.execute("INSERT INTO sessions VALUES ('s1', 'probe', 0, 0, 0, 0.0, 1700000000000, 1700000000000)")
        for n in range(start, start + count):
            words = " ".join(f"topic{n}-word{k}" for k in range(400))
            parts = json.dumps([{"type": "text", "data": {"text": f"message {n}: {words}"}}])
            ts = 1_700_000_000_000 + n * 1000
            con.execute("INSERT INTO messages VALUES (?, 's1', ?, ?, NULL, NULL, ?, ?, NULL)",
                        (f"m{n}", "user" if n % 2 == 0 else "assistant", parts, ts, ts))
        con.commit()
    finally:
        con.close()


def test_changed_crush_db_repays_every_chunk(tmp_path, monkeypatch) -> None:
    import chroma_write_store
    import incremental_jsonl as inc
    import ingest

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    layout = inc.ProductionBoundary(cfg, str(source)).layout
    monkeypatch.setattr(chroma_write_store, "DEFAULT_WRITER_LOCK", layout["locks"] / "chroma_writer_gate.lock")
    paid = {"summarize": 0, "distill": 0}
    real_summarize, real_distill = ingest.summarize, ingest.distill

    def summarize(*a, **k):
        paid["summarize"] += 1
        return real_summarize(*a, **k)

    def distill(*a, **k):
        paid["distill"] += 1
        return real_distill(*a, **k)

    monkeypatch.setattr(ingest, "summarize", summarize)
    monkeypatch.setattr(ingest, "distill", distill)
    db = tmp_path / "proj" / ".crush" / "crush.db"
    db.parent.mkdir(parents=True)
    _add_messages(db, 0, 12)

    runs = []

    def run(label):
        before = dict(paid)
        with mock.patch("ingest.load_config", return_value=cfg), mock.patch("config.load_config", return_value=cfg), \
                mock.patch("brief.refresh_brief_after_change", lambda *_a, **_k: None):
            try:
                stats = ingest.index(verbose=False, force_file=str(db))
            except Exception as exc:  # noqa: BLE001
                stats = (repr(exc)[:160], [f"{f.filename.split('/')[-1]}:{f.lineno}"
                                           for f in traceback.extract_tb(exc.__traceback__)][-6:])
        runs.append((label, {k: paid[k] - before[k] for k in paid}, stats))

    run("first index, 12 messages")
    run("unchanged")
    _add_messages(db, 12, 1)
    run("one message appended")
    print("\nCRUSH-REPAY", json.dumps(runs, default=str))
    first, unchanged, appended = (r[1]["summarize"] for r in runs)
    assert first > 1 and unchanged == 0, runs
    # The finding: the append re-pays every earlier chunk, not just the new one.
    assert appended >= first, runs
```

</details>

<details><summary>Corrective 11 (Y0), proved in scratch</summary>

```diff
diff --git a/tests/test_watch_oom_live_diagnosis_d1.py b/tests/test_watch_oom_live_diagnosis_d1.py
index b0db98a..105ebb9 100644
--- a/tests/test_watch_oom_live_diagnosis_d1.py
+++ b/tests/test_watch_oom_live_diagnosis_d1.py
@@ -437,12 +437,19 @@ def test_network_denied_under_hermetic(layout: dict, monkeypatch: pytest.MonkeyP
         "CONVMEM_LIVE_DIAG_INDEX_PID_PATH",
         str(layout["index_pid_path"]),
     )
+    import brief
+    import ingest
+
+    # bootstrap_index_child() is a child-process entry hook: its patches never stop.
+    monkeypatch.setattr(brief, "DEFAULT_BRIEF_PATH", brief.DEFAULT_BRIEF_PATH)
+    monkeypatch.setattr(ingest, "_LIVE_DIAG_PATCHED", False, raising=False)
     try:
         bootstrap_index_child()
         with pytest.raises(LiveDiagnosisRefused, match="network_denied"):
             socket.create_connection(("127.0.0.1", 9), timeout=0.2)
     finally:
         teardown_hermetic_guards()
+        patch.stopall()
 
 
 def test_canary_drift_fail_closed() -> None:
```

</details>

## Appendix: round-11 probe tests

They run from `tests/` and import from `tests/test_zz_claude_verify9.py`, already on the
branch. Each opens the real production store session against a scratch config.

<details><summary>tests/test_zz_claude_verify11.py</summary>

```python
"""Claude verify probes, round 11 (d2abcbe): the approved-dedupe nesting, C1 binding, readonly rows.

Scratch only: real production store sessions against a scratch config; no provider calls.
"""

# pylint: disable=protected-access

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_zz_claude_verify9 import _real_session_env, _where


def _seed_pairs(chroma: Path, pairs: int) -> list[dict]:
    from chroma_store import ChromaStore

    seed = ChromaStore(str(chroma))
    rows = []
    try:
        for n in range(pairs):
            for role in ("canon", "dup"):
                uid = f"{role}{n}"
                seed.add_unit(uid, f"{role} document {n}", [0.1, 0.2, 0.3 + n],
                              {"id": uid, "title": f"{role} {n}", "timestamp": "2026-01-01T00:00:00Z"})
            rows.append({"id_a": f"canon{n}", "id_b": f"dup{n}", "status": "approved_merge_a_canonical",
                         "canonical_id": f"canon{n}", "tombstone_id": f"dup{n}", "similarity": 0.99})
    finally:
        seed.close()
    return rows


def test_approve_dedupe_all_tombstones_every_row(tmp_path, monkeypatch) -> None:
    """`convmem refine --approve-dedupe all`: C1 + session, then a nested write scope per row."""
    import refine
    from chroma_store import ChromaStore

    cfg = _real_session_env(tmp_path, monkeypatch)
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    refine.save_dedupe_queue(cfg, _seed_pairs(chroma, 2))
    try:
        totals, err = refine.apply_approved_dedupe("all", verbose=False), None
    except Exception as exc:
        totals, err = None, _where(exc)
    assert err is None, err
    assert totals == {"processed": 2, "tombstoned": 2, "skipped": 0, "errors": 0}, totals
    check = ChromaStore(str(chroma), mutation_sink=None)
    try:
        for n in range(2):
            meta = check.get_unit(f"dup{n}")["metadata"]
            assert meta.get("superseded") and meta.get("superseded_by") == f"canon{n}", meta
    finally:
        check.close()


def test_guard_refuses_a_lock_for_another_chroma_dir(tmp_path, monkeypatch) -> None:
    """T0: C1 taken from another config cannot authorize writes to this store."""
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    other = {"index": {k: str(tmp_path / "other" / Path(v).name) for k, v in cfg["index"].items()
                       if k in ("chroma_dir", "processed_log", "units_export")}}
    with index_write_flock(other):
        with production_chroma_write_session(entrypoint="claude_verify11") as session:
            with pytest.raises(RuntimeError, match="index write lock belongs to Chroma dir"):
                session.store.add_unit("x", "doc", [0.1, 0.2, 0.3], {"id": "x"})


def test_guard_accepts_a_symlinked_chroma_dir(tmp_path, monkeypatch) -> None:
    """T0: the binding compares canonical paths, so a symlinked chroma_dir in the config still writes."""
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    real = Path(cfg["index"]["chroma_dir"]).expanduser()
    link = tmp_path / "chroma-link"
    link.symlink_to(real, target_is_directory=True)
    cfg["index"]["chroma_dir"] = str(link)
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify11") as session:
            session.store.add_unit("x", "doc", [0.1, 0.2, 0.3], {"id": "x"})


def test_readonly_rows_do_not_leak_documents_into_metadata(tmp_path, monkeypatch) -> None:
    """Refine writes metadata from a fresh write-store read, never from a readonly row (which carries 'document')."""
    import llm
    import refine
    from chroma_store import ChromaStore

    cfg = _real_session_env(tmp_path, monkeypatch)
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    seed = ChromaStore(str(chroma))
    try:
        seed.add_unit("u0", "notes about python packaging", [0.1, 0.2, 0.3],
                      {"id": "u0", "title": "Packaging", "source_path": "/scratch/0"})
    finally:
        seed.close()
    monkeypatch.setattr(llm, "generate", lambda *a, **k: "coding.tooling")
    result = refine.run_job("backfill_domain", limit=1, verbose=False)
    assert result["updated"] == 1, result
    check = ChromaStore(str(chroma), mutation_sink=None)
    try:
        meta = check.get_unit("u0")["metadata"]
    finally:
        check.close()
    assert meta.get("domain") == "coding.tooling" and "document" not in meta, meta
```

</details>

## Appendix: round-10 probe tests

They run from `tests/` and import from `tests/test_zz_claude_verify9.py` and
`tests/test_zz_claude_verify8b.py`, both already on the branch. The refine, monitor and
index-route probes open the real production store session against a scratch config, and a
second process saves to the same store through the write guard. Each test asserts the
corrective-8 spec.

<details><summary>tests/test_zz_claude_verify10.py</summary>

```python
"""Claude verify probes, round 10 (61307d7): stores held open across a write session, the S6 watcher hold, the refine daemon.

The refine and monitor probes open the real production store session against a scratch
config, and a real second process saves to the same store through the write guard, the way the watcher would while refine
waits on its LLM call or monitor on its HTTP probes. Scratch only.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_zz_claude_verify9 import _real_session_env, _where

ROOT = Path(__file__).resolve().parents[1]


def _small_sync_store(chroma: Path) -> None:
    """Create both collections with a small HNSW sync threshold, from another process."""
    code = (
        "import sys, chromadb\n"
        "from chroma_store import SUMMARIES, UNITS\n"
        "c = chromadb.PersistentClient(path=sys.argv[1])\n"
        "for n in (SUMMARIES, UNITS):\n"
        "    c.get_or_create_collection(n, configuration={'hnsw': {'space': 'cosine', 'sync_threshold': 100, 'batch_size': 10}})\n"
    )
    done = subprocess.run([sys.executable, "-c", code, str(chroma)], cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr[-1500:]


_FOREIGN = (
    "import random, sys\n"
    "from chroma_store import ChromaStore\n"
    "from chroma_write_guard import ChromaWriteGuard\n"
    "root, dim = sys.argv[1], int(sys.argv[2])\n"
    "store = ChromaStore(root, write_guard=ChromaWriteGuard(root))\n"
    "try:\n"
    "    for i in range(150):\n"
    "        rng = random.Random(i)\n"
    "        store.add_summary(f'foreign{i}', f'summary {i}', [rng.random() - 0.5 for _ in range(dim)],\n"
    "                          {'source_path': '/foreign', 'n': i})\n"
    "finally:\n"
    "    store.close()\n"
)


def _foreign_save(chroma: Path, dim: int = 16) -> None:
    """Another process saves: 150 guarded summaries, so the HNSW syncs at 100."""
    from chroma_write_guard import _synced_only, store_signature

    before = _synced_only(store_signature(chroma))
    done = subprocess.run([sys.executable, "-c", _FOREIGN, str(chroma), str(dim)],
                          cwd=ROOT, capture_output=True, text=True, timeout=300, check=False)
    assert done.returncode == 0, done.stderr[-1500:]
    assert _synced_only(store_signature(chroma)) != before, "the foreign save did not sync; the probe would be vacuous"


def _store_env(tmp_path, monkeypatch):
    from chroma_store import ChromaStore

    cfg = _real_session_env(tmp_path, monkeypatch)
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    _small_sync_store(chroma)
    seed = ChromaStore(str(chroma))
    for n in range(3):
        seed.add_unit(f"u-untagged-{n}", f"notes about python packaging {n}", [0.1, 0.2, 0.3 + n],
                      {"id": f"u-untagged-{n}", "title": f"Packaging {n}", "source_path": f"/scratch/{n}"})
    seed.close()
    return cfg, chroma


def test_refine_write_survives_a_foreign_save_during_the_llm_call(tmp_path, monkeypatch) -> None:
    import llm
    import refine

    _cfg, chroma = _store_env(tmp_path, monkeypatch)
    paid: list[int] = []

    def generate(*_a, **_k):
        paid.append(1)
        if len(paid) == 1:
            _foreign_save(chroma)  # the watcher commits while refine waits on DeepSeek
        return "coding.tooling"

    monkeypatch.setattr(llm, "generate", generate)
    try:
        result, err = refine.run_job("backfill_domain", limit=3, verbose=False), None
    except Exception as exc:  # report how much was paid before the failure
        result, err = None, _where(exc)
    assert err is None, ("paid calls:", len(paid), err)
    assert result["updated"] == 3 and not result.get("errors"), ("paid calls:", len(paid), result)


def test_monitor_write_survives_a_foreign_save_during_the_probes(tmp_path, monkeypatch) -> None:
    import convmem
    import llm
    import monitor
    from typer.testing import CliRunner

    _cfg, chroma = _store_env(tmp_path, monkeypatch)
    saved: list[int] = []

    def fetch(site, *, session=None, timeout=20.0):
        if not saved:
            saved.append(1)
            _foreign_save(chroma)  # the watcher commits while monitor waits on HTTP
        return {}, "offline"

    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    monkeypatch.setattr(monitor, "fetch_https_headers", fetch)
    monkeypatch.setattr(monitor, "check_tls_redirect", lambda site, *, session=None, timeout=20.0: False)
    monkeypatch.setattr(llm, "ollama_embed", lambda *a, **k: [0.1, 0.2, 0.3])
    out = CliRunner().invoke(convmem.app, ["monitor", "--site", "example.test"])
    err = _where(out.exception) if out.exception and not isinstance(out.exception, SystemExit) else None
    assert saved and out.exit_code == 0 and err is None, (out.exit_code, err, out.output[-300:])
    stats, _end = json.JSONDecoder().raw_decode(out.output[out.output.index("{"):])
    assert stats["observations"] > 0, stats


def test_corrupt_retry_state_cli_refusal_holds_the_watcher(tmp_path, monkeypatch) -> None:
    """S6/T2 end to end: the real CLI's exit-91 output makes the watcher hold the path."""
    import config
    import convmem
    import watch
    from typer.testing import CliRunner
    from watch_circuit_breaker import CircuitBreakerState

    import incremental_jsonl as inc
    import pytest

    from tests.test_zz_claude_verify8b import _count_summaries, _retry_state_path, _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    _retry_state_path(tmp_path).write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr("ingest.load_config", lambda *a, **k: cfg, raising=False)
    monkeypatch.setattr(convmem, "_guard_write", lambda: None, raising=False)
    out = CliRunner().invoke(convmem.app, ["index", "--file", str(source)])
    assert out.exit_code == 91, (out.exit_code, out.output[-400:], out.exception)
    assert len(calls) == 1, "no paid summary after the corrupt state"
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    exc = watch.IndexSubprocessError("index child failed", returncode=91, stderr=out.output)
    watch._record_ready_path_failure(str(source), exc, breaker=breaker, verbose=False)
    assert breaker.has_refusal_quarantine_for_path(str(source)), out.output[-400:]
    assert breaker.should_skip_refusal_quarantine(str(source), None)


def test_refine_daemon_survives_a_failing_job_with_one_limiter(tmp_path, monkeypatch) -> None:
    import config
    import refine

    cfg = {"refine": {"jobs": ["backfill_domain", "chroma_dedupe"], "interval_seconds": 1, "batch_size": 2}}
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(refine, "_lock_path", lambda _cfg: tmp_path / "refine.lock")
    seen: list[tuple[str, int]] = []

    def run_job(job, **kwargs):
        seen.append((job, id(kwargs.get("limiter"))))
        if job == "backfill_domain":
            raise RuntimeError("lock ordering violation (probe)")
        return {}

    sleeps: list[int] = []

    def sleep(_s):
        sleeps.append(1)
        if len(sleeps) == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(refine, "run_job", run_job)
    monkeypatch.setattr(refine.time, "sleep", sleep)
    refine.run_refine_daemon(verbose=False, use_lock=False)
    assert [j for j, _ in seen] == ["backfill_domain", "chroma_dedupe"] * 2, seen
    assert len({lid for _, lid in seen}) == 1 and seen[0][1] != id(None), seen


def test_index_route_commits_after_a_foreign_save_during_the_paid_summary(tmp_path, monkeypatch) -> None:
    """The main burn path, same interleaving: another process saves while the route pays for a summary."""
    import ingest
    from tests.incremental_jsonl_helpers import fake_summarize

    _source, cfg, route = _route_fixture_small_sync(tmp_path, monkeypatch)
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    paid: list[int] = []

    def summarize(*args, **kwargs):
        paid.append(1)
        if len(paid) == 1:
            _foreign_save(chroma, dim=8)
        return fake_summarize(*args, **kwargs)

    monkeypatch.setattr(ingest, "summarize", summarize)
    try:
        result, err = route(), None
    except Exception as exc:  # report how much was paid before the failure
        result, err = None, _where(exc)
    assert err is None, ("paid summaries:", len(paid), err)
    assert paid, result


def _route_fixture_small_sync(tmp_path, monkeypatch):
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    _small_sync_store(Path(cfg["index"]["chroma_dir"]).expanduser())
    return source, cfg, route
```

</details>

The leak census plugin (scratch; load it with `PYTHONPATH=<dir> pytest -p leakwatch`, with
`LEAKWATCH_ROOTS` set to the fake live data root and the default data dir under the scratch
`HOME`, and `LEAKWATCH_OUT` set to a log path):

<details><summary>leakwatch.py</summary>

```python
"""Scratch pytest plugin: log every test that changes files under the fake live roots."""
import json
import os
import pathlib

import pytest

ROOTS = [pathlib.Path(p) for p in os.environ["LEAKWATCH_ROOTS"].split(":")]
OUT = pathlib.Path(os.environ["LEAKWATCH_OUT"])


def _snap():
    seen = {}
    for root in ROOTS:
        if root.exists():
            for p in root.rglob("*"):
                try:
                    st = p.stat()
                except OSError:
                    continue
                seen[str(p)] = (st.st_mtime_ns, st.st_size)
    return seen


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    before = _snap()
    yield
    after = _snap()
    changed = sorted([k for k, v in after.items() if before.get(k) != v] + [k for k in before if k not in after])
    if changed:
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"test": item.nodeid, "n": len(changed), "changed": changed[:8]}) + "\n")
```

</details>

## Appendix: round-9 probe tests

They run from `tests/` and import `_route_fixture` from `tests/test_zz_codex_audit.py`, which is
already on the branch. Each probe opens the real production store session against a scratch
config. Each test asserts the corrective-7 spec.

<details><summary>tests/test_zz_claude_verify9.py</summary>

```python
"""Claude verify probes, round 9 (905e602): writers that take C1 inside an open store session.

Each probe opens the real production store session (no fake session), against a scratch
config. Scratch only.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
import traceback

from tests.test_zz_codex_audit import _route_fixture


def _real_session_env(tmp_path, monkeypatch):
    import chroma_write_store
    import config
    import incremental_jsonl as inc

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    layout = inc.ProductionBoundary(cfg, str(source)).layout
    monkeypatch.setattr(chroma_write_store, "DEFAULT_WRITER_LOCK", layout["locks"] / "chroma_writer_gate.lock")
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr("brief.refresh_brief_after_change", lambda *a, **k: None, raising=False)
    return cfg


def _where(exc):
    return repr(exc)[:160], [f"{f.filename.split('/')[-1]}:{f.lineno}" for f in traceback.extract_tb(exc.__traceback__)][-5:]


def test_real_session_counts_one_store_session(tmp_path, monkeypatch) -> None:
    """Control: the real session is what the lock-order check counts."""
    from chroma_write_store import production_chroma_store_session_depth, production_chroma_write_session

    _real_session_env(tmp_path, monkeypatch)
    with production_chroma_write_session(entrypoint="claude_verify9") as session:
        assert session.store is not None
        assert production_chroma_store_session_depth() == 1
    assert production_chroma_store_session_depth() == 0


def test_refine_backfill_domain_pays_then_writes(tmp_path, monkeypatch) -> None:
    import llm
    import refine
    from chroma_store import ChromaStore

    cfg = _real_session_env(tmp_path, monkeypatch)
    seed = ChromaStore(cfg["index"]["chroma_dir"])
    seed.add_unit("u-untagged", "notes about python packaging", [0.1, 0.2, 0.3],
                  {"id": "u-untagged", "title": "Packaging", "source_path": "/scratch/a"})
    seed.close()
    paid: list[int] = []
    monkeypatch.setattr(llm, "generate", lambda *a, **k: paid.append(1) or "coding.tooling")
    try:
        result, err = refine.run_job("backfill_domain", limit=1, verbose=False), None
    except Exception as exc:  # report how much was paid before the failure
        result, err = None, _where(exc)
    assert err is None, ("paid calls:", len(paid), err)
    assert result["updated"] == 1, result


def test_monitor_cli_ingests_through_real_session(tmp_path, monkeypatch) -> None:
    import convmem
    import llm
    import monitor
    from typer.testing import CliRunner

    _real_session_env(tmp_path, monkeypatch)
    embeds: list[int] = []
    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    monkeypatch.setattr(monitor, "fetch_https_headers", lambda site, *, session=None, timeout=20.0: ({}, "offline"))
    monkeypatch.setattr(monitor, "check_tls_redirect", lambda site, *, session=None, timeout=20.0: False)
    monkeypatch.setattr(llm, "ollama_embed", lambda *a, **k: embeds.append(1) or [0.1, 0.2, 0.3])
    out = CliRunner().invoke(convmem.app, ["monitor", "--site", "example.test"])
    err = _where(out.exception) if out.exception and not isinstance(out.exception, SystemExit) else None
    assert out.exit_code == 0 and err is None, ("embeds:", len(embeds), err, out.output[-300:])
    stats, _end = json.JSONDecoder().raw_decode(out.output[out.output.index("{"):])
    assert stats["observations"] > 0, stats


def test_repository_knowledge_retirement_through_real_session(tmp_path, monkeypatch) -> None:
    import repository_knowledge_scope as rks
    from chroma_store import ChromaStore
    from repository_knowledge_sync import reconcile_manifest
    from tests.test_repository_knowledge_scope import _commit_all, _init_repo, _write_manifest

    cfg = _real_session_env(tmp_path, monkeypatch)
    rks.reset_configuration()
    root = tmp_path / "repo"
    root.mkdir()
    _init_repo(root)
    man = _write_manifest(root, {"docs/plan.md": ("# Plan\n", "markdown")})
    _commit_all(root)
    rk_cfg = {"index": dict(cfg["index"]), "watch": {"repository_knowledge_manifests": [str(man)]}}
    reconcile_manifest(str(man), rk_cfg, dispatch=lambda *_: None)
    prior_manifest = rks.sha256_file(man)
    prior_file = rks.sha256_file(root / "docs/plan.md")
    source = str((root / "docs/plan.md").resolve())
    seed = ChromaStore(cfg["index"]["chroma_dir"])
    seed.add_unit("right-row", "right", [0.0, 0.1, 0.2],
                  {"id": "right-row", "source_path": source, "source_type": "repository_knowledge_v1",
                   "file_sha256": prior_file, "manifest_sha256": prior_manifest})
    seed.close()
    payload = json.loads(man.read_text(encoding="utf-8"))
    (root / "docs/plan.md").unlink()
    payload["entries"] = [e for e in payload["entries"] if e["path"] != "docs/plan.md"]
    payload["classifications"] = [r for r in payload["classifications"] if r["path"] != "docs/plan.md"]
    payload["retire"] = [{"path": "docs/plan.md", "prior_file_sha256": prior_file,
                          "prior_manifest_sha256": prior_manifest, "reason": "probe retire"}]
    man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _commit_all(root, "retire")
    try:
        result, err = reconcile_manifest(str(man), rk_cfg, dispatch=lambda *_: None), None
    except Exception as exc:
        result, err = None, _where(exc)
    assert err is None, err
    assert result["retired"]["superseded"] == 1, result
```

</details>

## Appendix: round-8 probe tests

They run from `tests/`. `test_zz_claude_verify8b.py` and `8d` import `_route_fixture` from Codex's
audit probes (`tests/test_zz_codex_audit.py`, from the appendix of
`CODEX-2026-10-13-issue-286-stage2-fixes-audit.md`). Each test asserts the round-7 spec.

<details><summary>tests/test_zz_claude_verify8.py</summary>

```python
"""Claude verify probes for issue #286 corrective 6 (e1914f5). Scratch only.

Each test asserts the round-7 spec; a failure at e1914f5 is a finding.
"""

# pylint: disable=protected-access

from __future__ import annotations

import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests


def test_guard_refuses_unlocked_supersede() -> None:
    """Q3: every production Chroma mutator raises without C1, including supersede."""
    from chroma_write_store import _IndexWriteGuardedChromaStore

    inner = Mock()
    guarded = _IndexWriteGuardedChromaStore(inner)
    with pytest.raises(RuntimeError, match="index write lock"):
        guarded.supersede_units_for_source("/audit/source", superseded_by="audit")
    inner.supersede_units_for_source.assert_not_called()


def test_repository_knowledge_retirement_holds_index_write_lock(monkeypatch) -> None:
    """Q3: the watcher's repository-knowledge retirement supersedes units under C1."""
    from chroma_store import ChromaStore
    from purge_locks import index_write_lock_depth
    from tests.test_repository_knowledge_sync import SyncRoutingTests

    depths: list[int] = []
    real = ChromaStore.supersede_units_for_source

    def spy(self, *args, **kwargs):
        depths.append(index_write_lock_depth())
        return real(self, *args, **kwargs)

    monkeypatch.setattr(ChromaStore, "supersede_units_for_source", spy)
    result = unittest.TestResult()
    SyncRoutingTests("test_retirement_requires_prior_state_and_row_manifest_identity").run(result)
    assert result.wasSuccessful(), result.errors + result.failures
    assert depths, "retirement never superseded"
    assert all(depth >= 1 for depth in depths), depths


class _Offline:
    def get(self, *args, **kwargs):
        raise requests.ConnectionError("offline")


def test_monitor_embeds_the_document_it_stores(tmp_path, monkeypatch) -> None:
    """Q4 side effect: the precomputed embedding must be of the stored document text."""
    import llm
    from chroma_store import ChromaStore
    from monitor import run_monitor

    embedded: list[str] = []

    def embed(text, model=None, host=None):
        embedded.append(text)
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(llm, "ollama_embed", embed)
    store = ChromaStore(str(tmp_path / "chroma"))
    try:
        stats = run_monitor(
            store, site="example.test", embed_model="fake", ollama_host="http://127.0.0.1:9",
            units_export=None, dry_run=False, verbose=False, session=_Offline(),
        )
        assert stats["observations"] > 0, stats
        docs = [store.get_unit(m["id"])["document"] for m in store.units_metadata()]
    finally:
        store.close()
    mismatched = [doc for doc in docs if doc not in embedded]
    assert not mismatched, {"stored": mismatched[:2], "embedded": embedded[:2]}


def test_monitor_http_probes_run_outside_index_write_lock(tmp_path, monkeypatch) -> None:
    """Q4: nothing slow under C1. The CLI must not hold C1 across monitor's HTTP probes."""
    import chroma_write_store as cs
    import config
    import convmem
    import llm
    import monitor
    from chroma_store import ChromaStore
    from purge_locks import index_write_lock_depth
    from tests.purge_test_util import purge_cfg
    from typer.testing import CliRunner

    cfg = purge_cfg(tmp_path)
    cfg["models"] = {"embed_model": "fake", "ollama_host": "http://127.0.0.1:9"}
    cfg["index"]["units_export"] = None
    depths: list[tuple[str, int]] = []

    def headers(site, *, session=None, timeout=20.0):
        depths.append(("https_fetch", index_write_lock_depth()))
        return {}, "offline"

    def tls(site, *, session=None, timeout=20.0):
        depths.append(("tls_fetch", index_write_lock_depth()))
        return False

    @contextmanager
    def session(**kwargs):
        store = ChromaStore(str(tmp_path / "chroma"))
        try:
            yield SimpleNamespace(store=store, live_cfg=cfg)
        finally:
            store.close()

    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(cs, "production_chroma_write_session", session)
    monkeypatch.setattr(monitor, "fetch_https_headers", headers)
    monkeypatch.setattr(monitor, "check_tls_redirect", tls)
    monkeypatch.setattr(llm, "ollama_embed", lambda *a, **k: [0.1, 0.2, 0.3])
    monkeypatch.setattr("brief.refresh_brief_after_change", lambda *a, **k: None, raising=False)
    result = CliRunner().invoke(convmem.app, ["monitor", "--site", "example.test"])
    assert depths, (result.output, result.exception)
    assert all(depth == 0 for _, depth in depths), depths
```

</details>

<details><summary>tests/test_zz_claude_verify8b.py</summary>

```python
"""Claude verify probes for issue #286 corrective 6 (e1914f5), burn bounds. Scratch only.

Codex's F2 probes flipped to the round-7 spec, plus Q2(c), Q2(d), Q7 and Q1 checks.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
import subprocess

import pytest
import requests

from tests.test_zz_codex_audit import _route_fixture


def _count_summaries(monkeypatch):
    import ingest
    from tests.incremental_jsonl_helpers import fake_summarize

    calls: list[int] = []

    def summarize(*args, **kwargs):
        calls.append(1)
        return fake_summarize(*args, **kwargs)

    monkeypatch.setattr(ingest, "summarize", summarize)
    return calls


def _cli_stderr(exc) -> tuple[int, str]:
    """Mirror convmem.py's index --file handling of a routed failure (exit code, stderr)."""
    from incremental_jsonl import format_live_route_refused

    if getattr(exc, "code", "") != "live_route_refused":
        return 1, str(exc)
    lines = str(exc.detail or "").splitlines()
    head = lines[0]
    tail = head.rsplit(":", maxsplit=1)[-1]
    outcome, digest = head.rsplit(":", maxsplit=1) if ":" in head and len(tail) == 64 else (head, "")
    return 91, "\n".join([format_live_route_refused(outcome, digest), *lines[1:2]])


def _watch_flush(monkeypatch, route, catch):
    import watch

    def flush(path, **kwargs):
        try:
            route()
        except catch as exc:
            code, stderr = _cli_stderr(exc)
            raise watch.IndexSubprocessError(str(exc), returncode=code, stderr=stderr) from exc

    monkeypatch.setattr(watch, "flush_path", flush)


def test_f2a_prepared_write_oserror_stops_paying(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc
    import watch

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("simulated prepared-artifact write failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    _watch_flush(monkeypatch, route, (OSError, inc.IncrementalJsonlError))
    breaker = watch.CircuitBreakerState(tmp_path / "breaker.json")
    for _ in range(4):
        watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert len(calls) == 2, len(calls)
    assert breaker.has_refusal_quarantine_for_path(str(source))


def test_f2b_manual_retry_refuses_before_transform(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc
    import ingest

    _source, _cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def failed_distill(*args, **kwargs):
        raise RuntimeError("simulated distill timeout")

    monkeypatch.setattr(ingest, "distill", failed_distill)
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    codes = []
    for _ in range(4):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        codes.append(caught.value.code)
    assert len(calls) == 2, (len(calls), codes)
    assert codes[2:] == ["live_route_refused", "live_route_refused"], codes


def test_f2c_provider_refusal_stops_paying(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc
    import ingest
    import watch

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def failed_distill(*args, **kwargs):
        response = requests.Response()
        response.status_code = 402
        raise requests.HTTPError("synthetic provider unavailable", response=response)

    monkeypatch.setattr(ingest, "distill", failed_distill)
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    _watch_flush(monkeypatch, route, (ingest.ProviderUnavailableError, inc.IncrementalJsonlError))
    breaker = watch.CircuitBreakerState(tmp_path / "breaker.json")
    for _ in range(4):
        watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert len(calls) == 2, len(calls)
    assert breaker.has_refusal_quarantine_for_path(str(source))


def test_q2d_source_hold_across_prefixes_and_clear_quarantine_releases(tmp_path, monkeypatch) -> None:
    import config
    import convmem
    import incremental_jsonl as inc
    from tests.incremental_jsonl_helpers import codex_rollout_record
    from typer.testing import CliRunner

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    codes = []
    for index in range(4):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        codes.append(caught.value.code)
        with source.open("ab") as handle:  # an active session: a new prefix every time
            handle.write(codex_rollout_record(100 + index))
    assert len(calls) == 3, (len(calls), codes)
    assert codes[3] == "live_route_refused", codes

    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    out = CliRunner().invoke(convmem.app, ["watch", "--clear-quarantine", str(source)])
    assert out.exit_code == 0, (out.output, out.exception)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    assert len(calls) == 4, "clear-quarantine did not release the source hold"


def _retry_state_path(tmp_path):
    found = list((tmp_path / "data").rglob("retry_state.json"))
    assert len(found) == 1, found
    return found[0]


def _one_failure(tmp_path, monkeypatch):
    import incremental_jsonl as inc

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    return route, calls, _retry_state_path(tmp_path)


def test_q2c_unreadable_retry_state_fails_closed(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc

    route, calls, state = _one_failure(tmp_path, monkeypatch)
    state.chmod(0)
    try:
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
    finally:
        state.chmod(0o600)
    assert caught.value.code == "retry_state_unavailable", caught.value.code
    assert len(calls) == 1


def test_q2c_corrupt_retry_state_fails_closed(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc

    route, calls, state = _one_failure(tmp_path, monkeypatch)
    state.write_text("{not json", encoding="utf-8")
    with pytest.raises(inc.IncrementalJsonlError) as caught:
        route()
    assert caught.value.code == "retry_state_unavailable", caught.value.code
    assert len(calls) == 1


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_q7_tracked_review_bundle_scanned_untracked_skipped(tmp_path, monkeypatch) -> None:
    from eval_corpus.r2b_v2.coverage import inventory

    ctor = 'from chroma_store import ChromaStore\nstore = ChromaStore("~/.local/share/convmem/chroma")\n'
    _git(tmp_path, "init", "-q")
    (tmp_path / "review-bundles").mkdir()
    (tmp_path / "review-bundles/tracked_writer.py").write_text(ctor)
    (tmp_path / "review-bundles/untracked_writer.py").write_text(ctor)
    _git(tmp_path, "add", "review-bundles/tracked_writer.py")
    manifest = tmp_path / "shadow.json"
    manifest.write_text('{"allowlisted_direct_sites": []}')
    monkeypatch.setattr(inventory, "ROOT", tmp_path)
    monkeypatch.setattr(inventory, "SHADOW_INVENTORY", manifest)
    assert inventory._scan_chroma_ctor_uncached() == ["review-bundles/tracked_writer.py:2"]


def test_q1_dedupe_rollback_removes_only_this_transaction(tmp_path, monkeypatch) -> None:
    from tests.test_issue_286_stage2_wedge_probes import _wedge_then_replay

    replay, _export, _foreign, _source = _wedge_then_replay(tmp_path, monkeypatch, "before_summary_upsert")
    paths = replay._dedupe_restore_paths()
    own, other = "tx-own", "tx-other"
    lines = [
        json.dumps({"event_id": "old", "transaction_id": other}, separators=(",", ":")) + "\n",
        json.dumps({"event_id": "mine-1", "transaction_id": own}) + "\n",
        '{"event_id": "legacy-no-tx"}\n',
        json.dumps({"event_id": "mine-2", "transaction_id": own}) + "\n",
        json.dumps({"z": 1, "event_id": "later-foreign", "a": 2}) + "\n",
    ]
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(lines), encoding="utf-8")
    replay._restore_dedupe_files(own)
    expected = "".join(lines[i] for i in (0, 2, 4))
    for path in paths.values():
        assert path.read_text(encoding="utf-8") == expected
```

</details>

<details><summary>tests/test_zz_claude_verify8c.py</summary>

```python
"""Claude verify probe, round 8: legacy index paths through the real index() entrypoint. Scratch only."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import tests.test_index_limit_skip_stats as limit_stats


def _run(force_file: bool):
    calls: list[int] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "chroma").mkdir()
        (root / "processed.json").write_text("{}", encoding="utf-8")
        (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
        src = root / "agent-transcripts" / "s" / "chat.jsonl"
        src.parent.mkdir(parents=True)
        src.write_text(limit_stats._cursor_line() + "\n", encoding="utf-8")
        inv = root / "inventory.jsonl"
        limit_stats._write_inventory(inv, [str(src)])
        cfg = limit_stats.IndexLimitSkipStatsTests()._cfg(root, inv)
        unit = {"type": "explanation", "title": "T", "summary": "S", "keywords": ["k"],
                "confidence": 0.9, "domain": "coding.tooling"}
        with mock.patch("ingest.load_config", return_value=cfg), \
                mock.patch("config.load_config", return_value=cfg), \
                mock.patch("ingest.summarize", side_effect=lambda *a, **k: calls.append(1) or "summary"), \
                mock.patch("ingest.distill", return_value=[unit]), \
                mock.patch("ingest.ollama_embed", return_value=[0.1, 0.2]), \
                mock.patch("brief.refresh_brief_after_change", lambda *_a, **_k: None):
            from ingest import index

            try:
                return len(calls), index(verbose=False, force_file=str(src) if force_file else None), None
            except Exception as exc:  # report how much was paid before the failure
                return len(calls), None, repr(exc)[:160]


def test_bulk_index_commits_without_lock_error() -> None:
    calls, stats, err = _run(False)
    assert err is None, (calls, err)
    assert stats["files_processed"] == 1, stats


def test_legacy_index_file_commits_without_lock_error() -> None:
    calls, stats, err = _run(True)
    assert err is None, (calls, err)
    assert stats["files_processed"] == 1, stats
```

</details>

<details><summary>tests/test_zz_claude_verify8d.py</summary>

```python
"""Claude verify probe, round 8: the incremental route through the real index() entrypoint. Scratch only."""

from __future__ import annotations

import traceback
from unittest import mock

from tests.test_zz_codex_audit import _route_fixture


def test_index_file_routes_codex_rollout_and_commits(tmp_path, monkeypatch) -> None:
    import ingest
    from tests.incremental_jsonl_helpers import fake_summarize

    import chroma_write_store
    import incremental_jsonl as inc

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    # Production shape: the outer index() lease and the coordinator use one writer lock.
    layout = inc.ProductionBoundary(cfg, str(source)).layout
    monkeypatch.setattr(chroma_write_store, "DEFAULT_WRITER_LOCK", layout["locks"] / "chroma_writer_gate.lock")
    calls = []

    def summarize(*args, **kwargs):
        calls.append(1)
        return fake_summarize(*args, **kwargs)

    monkeypatch.setattr(ingest, "summarize", summarize)
    err = None
    with mock.patch("ingest.load_config", return_value=cfg), mock.patch("config.load_config", return_value=cfg), \
            mock.patch("brief.refresh_brief_after_change", lambda *_a, **_k: None):
        try:
            stats = ingest.index(verbose=False, force_file=str(source))
        except Exception as exc:
            stats = None
            err = (repr(exc)[:200], [f"{f.filename.split('/')[-1]}:{f.lineno}" for f in traceback.extract_tb(exc.__traceback__)][-8:])
    assert err is None, ("summaries paid:", len(calls), err)
    assert stats["files_processed"] == 1, stats
```

</details>

## Appendix: round-5 probe tests

They run from `tests/` and import helpers from the round-2 probe file below.

<details><summary>tests/test_zz_claude_verify5.py</summary>

```python
"""Claude verify probes for issue #286 corrective 4 (62fe3a2). Scratch only."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json
from pathlib import Path

import pytest

import incremental_jsonl
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import codex_rollout_record, install_fakes
from tests.test_incremental_jsonl_codex_rollout_route import _write_user_config
from tests.test_zz_claude_verify2 import _codex_env, _wedge_then_replay


def _owned(export: Path, source: Path) -> list[bytes]:
    out = []
    for raw in export.read_bytes().splitlines(keepends=True):
        row = json.loads(raw)
        if row.get("source_path") == str(source):
            out.append(raw)
    return out


def _commit_then_grow(tmp_path, monkeypatch, crash_point: str | None):
    """Commit once, grow the rollout, then (optionally) crash the next transaction at crash_point."""
    source, cfg = _codex_env(tmp_path, monkeypatch)
    install_fakes(monkeypatch)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    common = dict(cfg=cfg, enabled=True, chunk_size=4, overlap=0,
                  min_confidence=0.6, embed_dimension=8)
    first = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, **common)
    assert first.run().outcome == "committed"
    export = Path(cfg["index"]["units_export"])
    before = export.read_bytes()
    assert _owned(export, source), "first commit wrote no export lines"
    with source.open("ab") as handle:
        for index in range(8, 16):
            handle.write(codex_rollout_record(index))
    if crash_point:
        def crash(point: str) -> None:
            if point == crash_point:
                raise RuntimeError("partial apply")
        second = incremental_jsonl.IncrementalJsonlCoordinator(
            boundary, source, fault=crash, **common)
        with pytest.raises(RuntimeError, match="partial apply"):
            second.run()
    replay = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, **common)
    return replay, export, before, source


def _fail_at(point_name: str):
    def fault(point: str) -> None:
        if point == point_name:
            raise incremental_jsonl.IncrementalJsonlError("synthetic_replay_fault", "forced")
    return fault


def test_s3_control_grown_session_commits(tmp_path, monkeypatch) -> None:
    replay, export, before, source = _commit_then_grow(tmp_path, monkeypatch, None)
    assert replay.run().outcome == "committed"
    assert len(_owned(export, source)) > len(before.splitlines())


@pytest.mark.parametrize("crash", ["after_export_reconcile", "before_dedupe_reconcile"])
def test_s3_grown_session_clean_rollback_is_silent(tmp_path, monkeypatch, capsys, crash) -> None:
    """Committed session grows; the next transaction dies after rewriting the export; replay rolls back."""
    replay, export, before, _source = _commit_then_grow(tmp_path, monkeypatch, crash)
    assert export.read_bytes() != before  # the crashed transaction rewrote the export
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert export.read_bytes() == before
    err = capsys.readouterr().err
    assert "rollback dropped" not in err, err


def test_s4_legacy_format_preimage_line_clean_rollback(tmp_path, monkeypatch, capsys) -> None:
    """Kiro bootstrap shape: the export already holds a legacy-writer line for this source."""
    from adapters.kiro_session_jsonl import parse_complete_prefix
    from tests.incremental_jsonl_helpers import apply_env, isolated_env, write_source
    from tests.test_incremental_jsonl_live_boundary import _bootstrap_binding
    from tests.test_zz_claude_verify2 import _enable

    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    source = write_source(isolated.root, 4)
    boundary, cfg = _enable(isolated, source)
    common = dict(cfg=cfg, bootstrap_existing=True,
                  expected_prefix_sha256=parse_complete_prefix(str(source)).prefix_sha256,
                  max_bootstrap_chunks=4, chunk_size=2, **_bootstrap_binding())
    export = Path(cfg["index"]["units_export"])
    export.parent.mkdir(parents=True, exist_ok=True)
    legacy = json.dumps({"id": "legacy-unit", "source_path": str(source), "text": "old"}) + "\n"
    export.write_text(legacy, encoding="utf-8")
    before = export.read_bytes()

    def crash(point: str) -> None:
        if point == "after_export_reconcile":
            raise RuntimeError("partial apply")

    first = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, processed={"old-hash": {"path": str(source)}}, fault=crash, **common)
    with first._session() as session:
        session.store.add_unit("legacy-unit", "old", [0.1] * 8, {"source_path": str(source)})
    with pytest.raises(RuntimeError, match="partial apply"):
        first.run()
    replay = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, fault=_fail_at("after_summary_upsert"), **common)
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert export.read_bytes() == before
    err = capsys.readouterr().err
    assert "rollback dropped" not in err, err


def test_s5_preimage_line_edited_while_wedged_is_reported(tmp_path, monkeypatch, capsys) -> None:
    """While the transaction is wedged, a line with a preimage id is edited; rollback counts exactly 1."""
    replay, export, before, source = _commit_then_grow(tmp_path, monkeypatch, "after_export_reconcile")
    target_id = json.loads(_owned(export, source)[0])["id"]
    data = export.read_bytes()
    target = [r for r in data.splitlines(keepends=True) if json.loads(r).get("id") == target_id][0]
    edited = dict(json.loads(target), text_tampered=True)
    export.write_bytes(data.replace(target, (json.dumps(edited) + "\n").encode()))
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert export.read_bytes() == before
    err = capsys.readouterr().err
    assert "rollback dropped 1 unexpected export lines" in err, err
```

</details>

## Appendix: round-4 probe tests

They run from `tests/` and import helpers from the round-2 probe file below.

<details><summary>tests/test_zz_claude_verify4.py</summary>

```python
"""Claude verify probes for issue #286 corrective 3 (8a8c03a). Scratch only."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json

import pytest

import incremental_jsonl
from tests.test_zz_claude_verify2 import _wedge_then_replay


def _tamper(export_path, source) -> None:
    line = json.dumps({"id": "tampered-unit", "source_path": str(source), "text": "x"}) + "\n"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def test_s1_real_rollback_path_reports_tamper(tmp_path, monkeypatch, capsys) -> None:
    """A tampered source line present at rollback must be reported on the real path."""
    replay, export_path, _foreign, source = _wedge_then_replay(
        tmp_path, monkeypatch, "after_summary_upsert"
    )
    _tamper(export_path, source)
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    err = capsys.readouterr().err
    assert "rollback dropped 1 unexpected export lines" in err, err
    assert b"tampered-unit" not in export_path.read_bytes()


@pytest.mark.parametrize("point", ["after_summary_upsert", "before_dedupe_reconcile"])
def test_s2_store_only_capture_is_enough(tmp_path, monkeypatch, capsys, point) -> None:
    """Without the on-disk capture, a clean rollback still prints nothing."""
    monkeypatch.setattr(
        incremental_jsonl.IncrementalJsonlCoordinator,
        "_source_owned_export_bytes_on_disk",
        lambda self, _p: set(),
    )
    replay, _export, _foreign, _src = _wedge_then_replay(tmp_path, monkeypatch, point)
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    err = capsys.readouterr().err
    assert "rollback dropped" not in err, err
```

</details>

## Appendix: round-3 probe tests

They run from `tests/` and import helpers from the round-2 probe file below.

<details><summary>tests/test_zz_claude_verify3.py</summary>

```python
"""Claude verify probes for issue #286 corrective 2 (c8436b1). Scratch only."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import os
from pathlib import Path

import pytest

import incremental_jsonl
from tests.test_zz_claude_verify2 import _codex_env, _route, _wedge_then_replay


def test_r1_doctor_with_real_retry_state(tmp_path, monkeypatch) -> None:
    """Doctor's wedge WARN, fed by the real retry-state writer (not a hand-made file)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    import doctor
    from config import DEFAULT_INCREMENTAL_JSONL_STATE_DIR
    from incremental_retry_state import record_incremental_retry_failure

    root = Path(os.path.expanduser(DEFAULT_INCREMENTAL_JSONL_STATE_DIR)) / "src1"
    paths = {"transaction": root / "transaction.json"}
    repeat = False
    for _ in range(2):
        repeat = record_incremental_retry_failure(
            paths, path_key="/s/rollout.jsonl", prefix_digest="d" * 64,
            error_code="recovery_unproven", transaction_id="t" * 32,
        )
    assert repeat
    cfg = {"index": {"incremental_jsonl": {"enabled": True, "embed_dimension": 8}}}
    check = doctor._check_wedged_incremental_transactions(cfg)
    assert check.status == "warn", check


def test_r1b_route_wedge_then_doctor(tmp_path, monkeypatch) -> None:
    """End to end: two raised failures through maybe_route_incremental, then doctor."""
    source, cfg = _codex_env(tmp_path, monkeypatch)

    def raising_run(self):
        self.last_evidence["prefix_sha256"] = "e" * 64
        raise incremental_jsonl.IncrementalJsonlError("recovery_unproven", "rollback failed")

    monkeypatch.setattr(incremental_jsonl.IncrementalJsonlCoordinator, "run", raising_run)
    for _ in range(2):
        with pytest.raises(incremental_jsonl.IncrementalJsonlError):
            _route(cfg, source)
    import doctor
    check = doctor._check_wedged_incremental_transactions(cfg)
    assert check.status == "warn", check


@pytest.mark.parametrize("point", ["after_summary_upsert", "before_dedupe_reconcile"])
def test_r2_clean_rollback_prints_no_tamper_line(tmp_path, monkeypatch, capsys, point) -> None:
    """A legitimate rollback must not report 'unexpected' (tampered) export lines."""
    replay, export_path, _foreign, source = _wedge_then_replay(tmp_path, monkeypatch, point)
    before = export_path.read_bytes() if export_path.exists() else b""
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    err = capsys.readouterr().err
    print("EXPORT_BEFORE_REPLAY_SOURCE_LINES",
          sum(1 for line in before.splitlines() if str(source).encode() in line))
    assert "rollback dropped" not in err, err
```

</details>

## Appendix: round-2 probe tests

Hermetic; they ran in a detached worktree at `117d698`. Copy the ones K5 names into the suite.

<details><summary><code>tests/test_zz_claude_verify2.py</code></summary>

```python
"""Claude verify probes for issue #286 corrective 1 (117d698). Scratch only."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

import convmem
import incremental_jsonl
import watch
from adapters.kiro_session_jsonl import parse_complete_prefix
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    write_source,
)
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
)
from tests.test_incremental_jsonl_live_boundary import _bootstrap_binding
from watch import CircuitBreakerState, IndexSubprocessError
from watch_circuit_breaker import parse_live_route_refused


def _enable(isolated, source: Path):
    enable_incremental(isolated)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(live_sources=[str(source)], embed_dimension=8)
    return ProductionBoundary(cfg, source, config_path=isolated.layout["user_config"]), cfg


def _wedge_then_replay(tmp_path, monkeypatch, replay_point: str):
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    source = write_source(isolated.root, 4)
    boundary, cfg = _enable(isolated, source)
    digest = parse_complete_prefix(str(source)).prefix_sha256
    common = dict(
        cfg=cfg,
        bootstrap_existing=True,
        expected_prefix_sha256=digest,
        max_bootstrap_chunks=4,
        chunk_size=2,
        **_bootstrap_binding(),
    )

    def first_crash(point: str) -> None:
        if point == "after_summary_upsert":
            raise RuntimeError("initial partial apply")

    first = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, processed={"old-hash": {"path": str(source)}},
        fault=first_crash, **common,
    )
    with first._session() as session:
        session.store.add_summary("legacy-summary", "old", [0.1] * 8, {"source_path": str(source)})
        session.store.add_unit("legacy-unit", "old", [0.1] * 8, {"source_path": str(source)})
    with pytest.raises(RuntimeError, match="initial partial apply"):
        first.run()
    # Another source indexes between attempts: store row and export line.
    with first._session() as session:
        session.store.add_summary("foreign-summary", "foreign", [0.1] * 8, {"source_path": "/other"})
    export_path = Path(cfg["index"]["units_export"])
    export_path.parent.mkdir(parents=True, exist_ok=True)
    foreign_line = json.dumps({"id": "foreign-unit", "source_path": "/other"}) + "\n"
    with export_path.open("a", encoding="utf-8") as handle:
        handle.write(foreign_line)

    def replay_fault(point: str) -> None:
        if point == replay_point:
            raise incremental_jsonl.IncrementalJsonlError("synthetic_replay_fault", "forced")

    replay = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, fault=replay_fault, **common
    )
    return replay, export_path, foreign_line, source


def test_p1_rollback_after_foreign_growth(tmp_path, monkeypatch) -> None:
    replay, export_path, foreign_line, _src = _wedge_then_replay(
        tmp_path, monkeypatch, "after_summary_upsert"
    )
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert not replay.paths["transaction"].exists()
    assert foreign_line.encode() in export_path.read_bytes()


def test_p2_rollback_after_export_already_rewritten(tmp_path, monkeypatch) -> None:
    # F4 scenario: _reconcile_export ran, then the replay fails before dedupe.
    replay, export_path, foreign_line, _src = _wedge_then_replay(
        tmp_path, monkeypatch, "before_dedupe_reconcile"
    )
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert foreign_line.encode() in export_path.read_bytes()


def _codex_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    return source, cfg


def _route(cfg, source):
    return incremental_jsonl.maybe_route_incremental(
        cfg=cfg, idx=cfg["index"], path=str(source), path_key=str(source),
        file_hash="h", processed={}, models=cfg["models"], tool="codex",
        units_export=Path(cfg["index"]["units_export"]), chunk_size=4, overlap=0,
        min_confidence=0.0, force_reindex=False, supersede_on_reindex=False,
        verbose=False, detected_format="jsonl_codex_rollout",
    )


def test_p3_real_wedge_marker_through_cli_parses(tmp_path, monkeypatch) -> None:
    source, cfg = _codex_env(tmp_path, monkeypatch)
    digest = "c" * 64

    def failing_run(self):
        self.last_failure_code = "rollback_export_foreign_changed"
        self.last_evidence["prefix_sha256"] = digest
        tx = self.paths["transaction"]
        tx.parent.mkdir(parents=True, exist_ok=True)
        tx.write_text(json.dumps({"transaction_id": "a" * 32}), encoding="utf-8")
        return self._refusal("rolled_back")

    monkeypatch.setattr(incremental_jsonl.IncrementalJsonlCoordinator, "run", failing_run)
    with pytest.raises(incremental_jsonl.IncrementalJsonlError):
        _route(cfg, source)
    with pytest.raises(incremental_jsonl.IncrementalJsonlError) as second:
        _route(cfg, source)
    assert second.value.code == "live_route_refused"

    def raising_index(**_kwargs):
        raise second.value

    import ingest
    monkeypatch.setattr(ingest, "index", raising_index)
    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    result = CliRunner().invoke(convmem.app, ["index", "--file", str(source), "--now"])
    stderr = getattr(result, "stderr", "") or result.output
    assert result.exit_code == 91, (result.exit_code, stderr)
    parsed = parse_live_route_refused(stderr)
    assert parsed == (
        "wedged_incremental_transaction_rollback_export_foreign_changed", digest
    ), stderr
    assert "a" * 32 in stderr and str(source) in stderr


def test_p4_raised_rollback_error_is_never_counted(tmp_path, monkeypatch) -> None:
    """C3 backstop: an error raised out of run() (e.g. by the rollback) repeats forever."""
    source, cfg = _codex_env(tmp_path, monkeypatch)

    def raising_run(self):
        raise incremental_jsonl.IncrementalJsonlError("recovery_unproven", "rollback failed")

    monkeypatch.setattr(incremental_jsonl.IncrementalJsonlCoordinator, "run", raising_run)
    codes = []
    for _ in range(3):
        with pytest.raises(incremental_jsonl.IncrementalJsonlError) as exc:
            _route(cfg, source)
        codes.append(exc.value.code)
    # Expected by C3: the second identical failure becomes live_route_refused (exit 91).
    assert codes[1] == "live_route_refused", codes


def test_p4b_watcher_retries_plain_errors_forever(tmp_path, monkeypatch) -> None:
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    spawns = 0

    def fake_flush(_path, **_kwargs):
        nonlocal spawns
        spawns += 1
        raise IndexSubprocessError("recovery_unproven", returncode=1, stderr="Error: recovery_unproven\n")

    monkeypatch.setattr(watch, "flush_path", fake_flush)
    monkeypatch.setattr(watch, "source_prefix_digest_for_watch", lambda _p: "f" * 64)
    for _ in range(5):
        watch._process_ready_path("/x/rollout.jsonl", cfg={}, breaker=breaker, verbose=False)
    assert spawns == 5  # never bounded


def test_p5_doctor_wedge_check_with_default_state_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    from config import DEFAULT_INCREMENTAL_JSONL_STATE_DIR
    from incremental_retry_state import iter_wedged_incremental_states

    state_root = Path(os.path.expanduser(DEFAULT_INCREMENTAL_JSONL_STATE_DIR))
    (state_root / "src1").mkdir(parents=True)
    (state_root / "src1" / "retry_state.json").write_text(
        json.dumps({"source": "/s", "transaction_id": "t", "error_code": "e",
                    "prefix_digest": "d", "consecutive": 2}),
        encoding="utf-8",
    )
    cfg = {"index": {"incremental_jsonl": {"enabled": True, "embed_dimension": 8}}}
    # Live config has an incremental_jsonl table and no state_dir key.
    assert iter_wedged_incremental_states(cfg), "doctor misses the default state dir"


def test_p6_rolled_back_refusal_holds_forever(tmp_path) -> None:
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    breaker.record_refusal("/x/r.jsonl", outcome="rolled_back", prefix_digest="a" * 64)
    assert breaker.should_skip_refusal_quarantine("/x/r.jsonl", "b" * 64)



def test_p7_watcher_digest_matches_coordinator_digest(tmp_path, monkeypatch) -> None:
    from tests.test_incremental_jsonl_codex_rollout_route import _write_user_config
    from adapters.detect import detect_format

    source, cfg = _codex_env(tmp_path, monkeypatch)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    install_fakes(monkeypatch)
    assert detect_format(str(source)) == "jsonl_codex_rollout"
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    coord = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, cfg=cfg, enabled=True, chunk_size=4, overlap=0,
        min_confidence=0.6, embed_dimension=8, processed={},
    )
    result = coord.run()
    assert result.outcome == "committed"
    coordinator_digest = coord.last_evidence.get("prefix_sha256")
    watcher_digest = watch.source_prefix_digest_for_watch(str(source))
    assert coordinator_digest and watcher_digest == coordinator_digest, (
        watcher_digest, coordinator_digest)
```

</details>
