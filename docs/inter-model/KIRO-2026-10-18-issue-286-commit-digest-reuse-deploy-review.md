# [Arc Codex #286] Kiro deploy-gate review — commit digest-reuse (slice 1)

**Verdict: PASS. Merge and deploy are approved.** Slice 1 on
`fix/2026-10-18-issue-286-commit-digest-reuse` @ `7d1f1f0` satisfies all five
conditions C1-a..C1-e. The C1-e synthetic-harness requirement is **relaxed to
accept live before/after measurement** on the terms stated below — this is the
one place I move off the letter of the prior review, and I explain why it is
sound.

**Arc: Codex (#286).**

**Who / what / when / why / how:** Kiro (design-review lane), 2026-10-18.
Reviewing Cursor's implementation (co-authored with Claude evidence) of slice 1
of the commit-cost reduction — the duplicate pre-write non-source digest reuse
plus per-phase commit instrumentation. Branch
`fix/2026-10-18-issue-286-commit-digest-reuse`, single commit `7d1f1f0` sitting
directly on current `origin/main` (merge-base `395e523`, which is the tip of
`origin/main`'s lineage — verified ancestor). This review follows the
PASS-with-conditions grant in
`KIRO-2026-10-17-issue-286-commit-cost-reduction-review.md`
(`origin/docs/2026-10-17-issue-286-commit-cost-review`) and rules on each
condition at file:line, then rules on the C1-e measurement substitution and the
merge+deploy gate.

**Consequence for Ryan:** you may squash-merge `7d1f1f0` to `main` and deploy.
Each one-chunk incremental commit drops from three full Chroma inventory passes
per collection to two; the new `incremental_commit_phase_timing` watcher-journal
event will let you confirm the saving live (per-phase seconds +
`full_inventory_passes`) rather than from a synthetic bench. No replay change, no
guarantee change, no gate claim.

---

## How I verified (not inherited from chat)

- Read the implementation diff of `7d1f1f0` on `incremental_jsonl.py` in full.
- Read `tests/test_issue_286_commit_digest_reuse.py` in full (349 lines, 6 tests).
- Built an isolated detached worktree at `7d1f1f0` and ran tests myself:
  - `tests/test_issue_286_commit_digest_reuse.py` → **6 passed**.
  - `tests/test_incremental_jsonl_canary_baseline.py`,
    `tests/test_watch_subprocess_memcap.py` → **14 passed**.
  - Replay / recovery / isolation / transform surface:
    `test_incremental_jsonl_isolation.py`,
    `test_incremental_jsonl_exact_path_recovery_parity.py`,
    `test_incremental_jsonl_state.py`,
    `test_incremental_jsonl_physical_keep_set.py`,
    `test_governed_recovery_and_writers.py`,
    `test_incremental_transform_compatibility.py` → **105 passed** (2m32s).
- Confirmed the branch is a clean single-commit delta on `origin/main`
  (`git log origin/main..` shows only `7d1f1f0`).

I did not re-run the full 509-test suite end-to-end; I ran the modules that
exercise the changed code path and its replay/recovery/isolation neighbours. The
focused result corroborates Claude's 509-pass claim for the surfaces that matter
to this change.

---

## Per-condition rulings

### C1-a — same-lock, no-mutation invariant asserted in a test → **PASS**

**Required:** a test proving that between the attempt digest and before-image
assembly the lock is never released and no Chroma write occurs.

**Where it holds in the code:** `incremental_jsonl.py` `7d1f1f0`:
- The attempt digest is taken inside `with index_write_flock(self.cfg):` under
  `phase_span("non_source_digest")`:
  `attempt_non_source = self._copy_non_source_digest(self._non_source_collection_digest())`.
- Before-image assembly runs in the same lock scope immediately after, under
  `phase_span("before_images")`:
  `self._snapshot_before_images(non_source_collections=attempt_non_source)`.
  There is no lock release, yield, or write between the two.

**Test:** `tests/test_issue_286_commit_digest_reuse.py:98`
`test_c1_a_no_lock_release_or_chroma_write_between_capture_and_reuse`. It wraps
`_non_source_collection_digest`, `_snapshot_before_images`,
`ChromaStore._native`, and `index_write_flock`, then asserts
`gap["depths"][0] > 0` (digest taken under held lock), `gap["snapshot_depth"] > 0`
(reuse consumed under held lock), `not gap["writes"]` (no native op in the gap),
and `not gap["lock_releases"]` (no release in the gap). This proves soundness by
construction, exactly as the condition demands. **PASS.**

### C1-b — freeze/deep-copy, not alias → **PASS**

**Required:** the reused value handed to the journal must be independent of any
later mutation; mutating the live collection after capture must not change the
recorded rollback baseline.

**Where it holds:** the value is frozen **twice**. First at capture:
`attempt_non_source = self._copy_non_source_digest(...)`
(`_copy_non_source_digest` is a JSON round-trip — a true deep copy,
`incremental_jsonl.py` static method added in `7d1f1f0`). Second inside
`_snapshot_before_images`, which re-copies when `non_source_collections is not
None` before use. The journal therefore records a value that no live mutation and
no caller-side mutation can reach.

**Test:** `:156` `test_c1_b_later_mutation_does_not_change_recorded_baseline`.
It poisons the passed-in mapping after snapshot
(`non_source_collections[SUMMARIES] = {"digest": "poisoned-alias"}`) and asserts
the on-disk rollback is unpoisoned
(`recorded["non_source_collections"][SUMMARIES]["digest"] != "poisoned-alias"`),
that the rollback dict is not the same object as the argument
(`held["rollback"]["non_source_collections"] is not held["arg"]`), and — the
stronger half — that a **real** post-capture foreign insert
(`add_summary("foreign-after-capture", ...)`) makes the live digest diverge from
the frozen baseline while the recorded baseline still equals the original. Freeze,
not alias, proven both ways. **PASS.**

### C1-c — replay baseline untouched → **PASS**

**Required:** the roll-forward path still computes a fresh
`_non_source_collection_digest()` and preserves the original journal SHA; reuse
must not leak into replay.

**Where it holds:** reuse is gated entirely on `rollback_authority_sha256 is
None` (the fresh-attempt branch). On replay that value is already set, so the
code takes the `else: self._require_rollback_authority(...)` branch and never
calls `_snapshot_before_images` with a reused digest. The post-apply verify still
calls `_verify_non_source_collections(attempt_non_source)` which computes a fresh
digest via `_non_source_collection_digest()`. The replay baseline recompute at
the roll-forward site (the prior review cited `incremental_jsonl.py:2289`) is
untouched by this diff.

**Test:** `:206` `test_c1_c_replay_computes_fresh_digest_and_keeps_journal_sha`.
It crashes the first attempt after the journal is written (`after_summary_upsert`
fault), captures the journal SHA, then replays and asserts: a fresh `"digest"`
pass occurs and precedes `"apply"` (`order.index("digest") < order.index("apply")`),
`_snapshot_before_images` is **never** entered with reuse on replay
(`assert not snapshot_calls`), and every rollback-authority check sees the
original journal SHA unchanged (`journal_sha in checked`, with an in-wrapper
assert that the on-disk SHA still equals `journal_sha`). The 105-test
replay/recovery/isolation suite I ran independently passes, corroborating no
leak. **PASS.**

### C1-d — structural scan-count assertion (+ negative control) → **PASS**

**Required:** a fresh one-chunk commit performs exactly two full inventory passes
per collection and one before/after comparison; a negative control that
reintroduces the third scan fails the test.

**Where it holds:** passes are counted by `_note_full_inventory_pass`, called once
per collection in `_non_source_collection_digest` (the attempt digest = pass 1,
and the post-apply verify = pass 2) and once per collection in the non-reused
branch of `_snapshot_before_images` (skipped here because the digest is reused).
Net: 2 per collection. The before/after comparison is retained in full by
`_verify_non_source_collections`.

**Tests:** `:271`
`test_c1_d_fresh_one_chunk_commit_has_exactly_two_inventory_passes` asserts
`counts[SUMMARIES] == 2` and `counts[UNITS] == 2` via a monkeypatched counter on
`ChromaStore.non_source_inventory_digest`, and cross-checks the emitted
`full_inventory_passes == {SUMMARIES: 2, UNITS: 2}`. The negative control `:291`
`test_c1_d_negative_control_third_scan_fails_two_pass_budget` forces
`_snapshot_before_images` to recompute (ignoring the reused arg), then asserts the
two-pass budget assertion **fails** and the real count is 3. I re-ran both: pass.
This is the design's §8.2 structural acceptance. **PASS.**

### C1-e — honest timing attribution → **PASS** (with the measurement substitution accepted; see below)

**Required (attribution half):** the phase instrumentation must not count
startup, fixture construction, or provider preparation as C1 savings, and must
report per-phase spans without double-counting nested spans.

**Where it holds:** `_emit_commit_phase_timing` (`incremental_jsonl.py` `7d1f1f0`)
emits only `c1_hold_seconds`, `full_inventory_passes`, and a `phases` map keyed by
the nine inner C1 phases plus the two post-lock phases (`processed`, `cleanup`).
The `phase_span` context manager accumulates **leaf** spans — there are no nested
`phase_span` calls, so no double counting. `c1_hold_seconds` is measured from the
single `c1_started = time.monotonic()` at lock entry to the `finally` at lock
exit, independent of the phase map.

**Test:** `:314`
`test_c1_e_timing_event_excludes_setup_and_does_not_double_count`. It injects a
50 ms `summarize` delay (provider-prep proxy) and asserts: the event excludes a
large forbidden-key set (`path`, `source_path`, `transaction_id`, `setup`,
`transform`, `provider`, `elapsed_seconds`, `total_seconds`, …), phases are a
subset of the allowed set, no `summarize`/`setup`/`transform` phase appears, the
sum of inner phases is `<= c1_hold_seconds + 1e-4` (no double-count, bounded by
the lock hold), and `c1_hold_seconds < elapsed` (startup/provider excluded from
the C1 attribution). The attribution half of C1-e is proven. **PASS.**

---

## Ruling on the C1-e measurement substitution: live before/after instead of a synthetic harness → **ACCEPT**

**What the prior review wrote:** "slice 1's own benchmark must reproduce the
delta on the hermetic harness, not inherit the number from an unmatched run"
(`KIRO-2026-10-17-...-review.md:142-145`).

**What Claude proposes:** do not build a synthetic hermetic harness to re-derive
~73 s. Instead measure the delta **live**: Before = median 295 s / p95 353 s per
one-chunk commit across 38 real runs with real provider latency. After deploy =
the new `incremental_commit_phase_timing` event in the watcher journal gives
per-phase seconds and `full_inventory_passes` per collection, so the saving is
read directly from production telemetry.

**Decision: accept the substitution.** My reasoning, and why this is not a
weakening of the condition's intent:

1. **The intent of C1-e was never "build a harness" — it was "do not inherit an
   unmatched number."** The prior review's worry was that the ~73 s came from
   Claude's read-only run on an unmatched shape, so attributing it to slice 1
   would be a borrowed claim. Live before/after is the *strongest* possible cure
   for that worry: it is the matched shape by definition — the same real
   collections, the same real provider latency, the production code path. A
   synthetic harness would be a weaker, more approximate witness than the live
   signal now available.

2. **The honest-attribution half of C1-e — the part that actually protects
   against a dishonest number — is implemented and tested** (see C1-d/C1-e
   above). `full_inventory_passes` lets anyone confirm the structural 3→2 drop
   per commit directly from the journal, and `c1_hold_seconds` plus the leaf
   `phases` map decompose the lock-held time without double counting or setup
   contamination. The delta is therefore *self-measuring in production*, not
   asserted.

3. **The ~73 s figure was always "right order of magnitude," never a gate.** The
   prior review and the design agree slice 1 makes **no** claim on the 60 s / 5 s
   gates and that even removing all three scans leaves >60 s residual. So the
   measurement exists to confirm a saving occurred and roughly matches
   expectation — not to clear a threshold. Live telemetry confirms "a saving
   occurred and here is its size" better than a bench.

**Conditions I attach to the acceptance (D-1..D-3), none blocking merge:**

- **D-1 — capture a matched before baseline from the same signal.** The 295 s /
  353 s "before" is from 38 real runs, but confirm those are one-chunk commits of
  comparable shape to what the "after" telemetry will measure. If the pre-deploy
  runs predate the timing event, record them as the baseline explicitly in the
  deploy note so the comparison is like-for-like (one-chunk, real provider).
- **D-2 — read the delta from `full_inventory_passes` + `c1_hold_seconds`, not
  wall clock.** Wall-clock median (295 s) is dominated by provider latency and
  will swamp a ~73 s structural saving in noise across runs. The honest signal is
  (a) `full_inventory_passes` dropping to `{summaries:2, units:2}` on every
  one-chunk commit, and (b) the `non_source_digest` + `verify_non_source` +
  `before_images` phase spans no longer containing a third digest's cost. Attribute
  the saving from the per-phase decomposition, consistent with how C1-e defines
  honest attribution.
- **D-3 — state the measurement as live-observed, not harness-derived.** When the
  post-deploy numbers come in, label them as production telemetry over N
  one-chunk commits, with the before baseline cited. Do not restate ~73 s as a
  proven per-commit constant; state the observed median/range of the removed
  pass's cost.

These are reporting disciplines for the deploy note, not code changes, and they
do not gate the merge.

---

## Merge + deploy verdict: **PASS**

- **Merge:** approved. `7d1f1f0` is a clean single-commit delta on current
  `origin/main`, all five conditions are met with substantive tests I re-ran,
  replay/recovery/isolation surfaces are green (105 tests), and the change alters
  observation *count*, not any correctness contract — full post-write field
  comparison, guards, rollback schema, and export behavior are retained.
- **Deploy:** approved, carrying reporting conditions D-1..D-3 for the saving
  write-up (not merge blockers). The new `incremental_commit_phase_timing` event
  is the agreed instrument; confirm the 3→2 drop and the per-phase saving live.
- **Squash:** fine (silence = squash OK per the commit/PR guidance). The commit
  message already reads as a clean `main` message.
- **No new guarantee, no gate claim:** slice 1 makes no claim on the 60 s / 5 s
  gates; the one scope note from the prior review (loss of the never-guaranteed
  chance to observe a foreign change *between* the two adjacent pre-write samples)
  stands and is accepted — neither the one-scan nor the two-scan version detects
  an arbitrary concurrent bypass.

**Scope of this review:** review-only. I did not open a PR, did not modify the
implementation branch, and did not touch `.worktrees/runtime-main`. This document
is delivered on `kiro/2026-10-18-issue-286-commit-digest-reuse-deploy-review`,
branched from `origin/main`, to be pushed with an explicit refspec.

---

I finished: Kiro deploy-gate review of commit digest-reuse slice 1 (`7d1f1f0`).
Next step:  Ryan squash-merges `fix/2026-10-18-issue-286-commit-digest-reuse` and deploys; confirm the 3→2 saving live via the new timing event (D-1..D-3).
Next lane:  Ryan (merge + deploy); Cursor/Codex if a follow-up slice is authorized.
See my work: docs/inter-model/KIRO-2026-10-18-issue-286-commit-digest-reuse-deploy-review.md

<!-- ref: ../../incremental_jsonl.py, ../../tests/test_issue_286_commit_digest_reuse.py — the reviewed slice-1 implementation and its C1 tests -->
<!-- src: ./KIRO-2026-10-17-issue-286-commit-cost-reduction-review.md — the PASS-with-conditions grant defining C1-a..C1-e -->
