# Implementation Handoff: Codex rollout admission, corrective 4 (gate-3 FAIL fixes)

**Arc: Codex (#286).**
**Date:** 2026-10-11
**Author:** Claude (Opus 5.5), design author
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-10-10. This is the same hermetic implementation
grant as the
[Execute handoff](CURSOR-2026-10-10-issue-286-codex-rollout-admission-execute-handoff.md).
It fixes review findings only and adds no new scope.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `feat/2026-10-10-issue-286-codex-rollout-admission` |
| **Tip SHA** | `905ad40` (failed gate 3; see below) |
| **Push status** | pushed to origin |
| **PR** | not opened; Ryan opens it after both reviews PASS |
| **Ryan GATE** | none to start. After this corrective: Copilot audit and Kiro recheck on the new exact tip, then Ryan's PR/merge decision. |

### Gate-3 result at `905ad40` (2026-10-11)

Both reviews failed the same tip. They don't conflict, so Sol-High does not
apply.

- **Kiro:** FAIL, on the Pylint regression gate only. All six §13 conditions
  pass their named tests. Kiro ruled on three items the design didn't cover:
  - **(a)** the D8 lineage fields are accepted;
  - **(b)** the terminal quarantine stays generic, covering every
    `live_route_refused` including Kiro exact-path sources;
  - **(c)** the D8 prose should name the lineage mechanism. That edit is
    done in this commit.
- **Copilot audit:** FAIL, with six findings, all reproduced hermetically.
  Claude confirmed each against the code at `905ad40`.

---

## What to build

Close every gate-3 finding so that both reviewers can pass the next exact
tip. Behavior stays as designed: admitted Codex rollouts use the guarded
incremental route, and a refused source is quarantined terminally by path
and never respawns. The findings show four paths that escape those
guarantees: crash recovery, verbose mode, source growth during a run, and
the marker parser.

**Why this exists:** the guards protect paid-call spend and watcher memory.
If one path can bypass them, the protection doesn't hold.

---

## Sync with `main` first (added 2026-10-11)

`main` moved to `6a23aa9` (PR #384, the Kiro bootstrap test-isolation fix)
after this branch was cut. That PR rewrote §4–§6, the Update Log and the
TL;DR of `docs/plans/STATUS-codex-jsonl-production-integration.md` for the
Kiro bootstrap track, so the branch now conflicts with `main` in that one
file. Code doesn't conflict.

- Bring `main` in with `git merge origin/main`. Don't rebase: that would
  need a force-push, which agents never do.
- Resolve the STATUS file by taking `main`'s version, then re-adding only
  the Codex-rollout parts from this branch:
  - the "Codex rollout admission design" row in §4;
  - the Codex-rollouts sentences in the §5 role text;
  - the "Codex rollouts" list in §6;
  - this arc's 2026-10-10/11 Update Log lines.
- Don't edit `main`'s Kiro bootstrap text, even where it's out of date.
  Report anything you think is stale instead.

---

## Findings and required fixes

| # | Sev | Finding (reviewer) | Location at `905ad40` | Required fix |
|---|---|---|---|---|
| C1 | High | A pending transaction rolls forward before any admission guard or the D8 lineage check. A replay transformed above the chunk cap, and a rollback→re-enable replay committed instead of refusing (Copilot). | `incremental_jsonl.py:2221` (`return self._roll_forward(existing_tx)`), ahead of `:2277`/`:2332` | Recovery must refuse wherever a fresh run would, with zero provider calls. That covers identity, size, chunk cap, frontier subset and D8 lineage, for Codex-admitted sources. Either run the same guards on the roll-forward path before any replay transform, or refuse roll-forward for an admitted source whose guards fail. |
| C2 | High | In verbose mode stderr is inherited, so the marker is never captured. Exit 91 becomes `index subprocess exit 91` and is not quarantined; 3 events spawned 3 children (Copilot). | `watch.py:243–267` | Always capture stderr (and stdout), echoing them when verbose, so refusal handling never depends on verbose mode. |
| C3 | High | The parent's fallback hash keeps an unbounded `incomplete` buffer. An 8 MiB line with no newline retained 8 MiB despite 64 KiB reads (Copilot). | `adapters/jsonl_prefix.py` `streaming_complete_prefix_digest_for_path`; parent fallback in `watch.py` `_record_ready_path_failure` | Now that the digest is evidence only (§13 c3), the **parent never hashes**. The child always emits the digest in its marker; for `source_too_large`, the child computes it with an O(1)-memory hash. The parent records whatever the marker carries (an empty digest is allowed). Also make the helper O(1) memory: update one hasher with every byte, and take `hasher.copy()` just after each newline, rather than holding the tail. |
| C4 | High | Source growth bypasses the size ceiling. `_revalidate_live_prefix` reads the new full size unchecked (1,234 → 2,258 bytes against a 1,334-byte ceiling, then committed) (Copilot). | `incremental_jsonl.py:808–813` | For admitted sources, check `st_size` against `max_source_bytes` before the read and refuse `source_too_large`. Bound the read to what revalidation needs. |
| C5 | Medium | Any error text containing the marker quarantines the path. The regex is unanchored and the exit status isn't checked; an exit-1 child quarantined a non-Codex path (Copilot). | `watch.py:296–304` and the failure path at `:659` | Treat a failure as a refusal only when the child exits with the dedicated code 91 **and** stderr has a line matching the whole pattern `^live_route_refused:<outcome>(:<64-hex>)?$`. Carry the return code structurally (a typed exception or attribute), not by re-parsing message text. |
| C6 | Medium | A noncanonical admission root (`/../sessions`, `/./`, `/missing/..`) is silently normalized and accepted, not rejected (Copilot). | `config.py:106` → `_canonical_config_path` (`abspath`) | Reject any root whose raw value isn't already canonical: it must be absolute, contain no `.` or `..` component, and contain no symlink component. Accepting a root after normalizing it is the defect. |
| K1 | Gate | The Pylint regression gate fails (Kiro). This contradicts the PASS in the corrective-3 handoff-back. | gate output vs `ci/pylint-baseline.json` | Fix `convmem.py` C0207 (`rsplit(':', maxsplit=1)`). Break the three new cyclic pairs (`doctor↔watch`, `ingest↔watch`, `source_reconciler↔watch`), for example by moving refusal-state reads into a small module that both sides import. Only allowlist a cycle if breaking it isn't feasible, and say why. Clear the test-file findings (unused imports, line length, W0212, C1803, W0613). |

---

## What NOT to build

- No change to the §13 rulings: the quarantine stays terminal by path, and
  it stays generic across all `live_route_refused` (Kiro ruling (b)).
- No new admission rules, config keys or outcomes beyond what these fixes
  need.
- Everything in the Execute handoff's "What NOT to build" still applies: no
  live config, systemd, runtime worktree, watcher start, live index or
  provider call, and no PR.

---

## Test expectations

Hermetic only, as before. Each finding needs a test that fails at `905ad40`
and passes after the fix:

1. **C1:**
   - a `PREPARING` transaction replayed with a lower chunk cap refuses with
     zero provider calls;
   - a rollback→re-enable with a pending transaction refuses
     `projection_checkpoint_mismatch` with zero provider calls;
   - a pending transaction that passes all guards still rolls forward (no
     recovery regression).
2. **C2:** in verbose mode, a refusal quarantines on the first event, and 3
   later events spawn zero children.
3. **C3:**
   - the parent computes no digest on any refusal path;
   - the helper's memory stays bounded for a single 8 MiB unterminated line
     (assert the retained buffer is ≤ the read size, or use `tracemalloc`);
   - the property test against `prefix_sha256(data[:prefix_boundary(data)])`
     still passes.
4. **C4:** a source that grows past the ceiling between capture and
   revalidation refuses `source_too_large` with zero provider calls.
5. **C5:**
   - an exit-1 child whose error text quotes a marker does not quarantine;
   - exit 91 without a whole-line marker does not quarantine;
   - exit 91 with a whole-line marker does.
6. **C6:** `/../`, `/./`, `/x/..` and a symlink component each fail config
   validation, and an already-canonical root passes.
7. **K1:** the exact CI Pylint gate command passes (see Acceptance).

---

## Acceptance criteria

- [ ] C1–C6 and K1 are each fixed, and each is mapped to its test name in the
      handoff-back.
- [ ] The full CI-equivalent suite is green, apart from the known #320
      golden-eval test that depends on the live corpus.
- [ ] The Pylint regression gate passes when run exactly the way CI runs it.
      Paste the command and its final line, not just "PASS":
      `python scripts/pylint_regression_gate.py ci --report <pylint.json> --pylint-status <st> --branch-baseline ci/pylint-baseline.json`
      (mirror `.github/workflows` for how the report is produced).
- [ ] The secret scan, critical invariants, writer inventories and canary
      baselines pass; refresh any of them that drift.
- [ ] `origin/main` (at least `6a23aa9`) is merged in, and the branch merges
      cleanly with `main`.
- [ ] No live resource is touched.

---

## Branch convention

Same branch: `feat/2026-10-10-issue-286-codex-rollout-admission`. First
cherry-pick, in order, every commit on
`origin/docs/2026-10-10-issue-286-codex-rollout-admission-design` after
`cf74166`: the one that adds this file and the one that adds the sync step.
Then merge `origin/main` (see Sync with `main`). It carries the D8 prose
update and the §13 record of Kiro's rulings, and both are normative. Push
after every commit with an explicit refspec. Ryan squash-merges.

---

## Related files

| What | Path |
|------|------|
| Normative design, §13 as amended | `docs/plans/DESIGN-issue-286-codex-rollout-admission.md` |
| Original Execute handoff | `docs/inter-model/CURSOR-2026-10-10-issue-286-codex-rollout-admission-execute-handoff.md` |
| Arc brief | `docs/plans/STATUS-codex-jsonl-production-integration.md` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on the pushed design branch
- [x] `LATEST.md` bullet updated with resume state
- [x] STATUS Update Log line
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Cherry-pick the docs commit; read §13 and this file
- [ ] State Goal / role / system state / next action; Arc: Codex

---

## Verification of `fc8ea2a` (Claude, 2026-10-11) — not ready for review

Cursor's corrective-4 tip fixes C1–C6 in code, and the branch merges
cleanly with `main`. Two mechanical blockers remain, checked in clean
scratch worktrees with a fresh CI-style config:

1. **The Pylint regression gate fails** with 3 new findings in
   `tests/test_incremental_jsonl_codex_corrective_4.py`: an unused `mock`
   import (line 10) and unused arguments `path` and `kwargs` (line 152).
   This happens with the exact CI command, against either `905ad40` or
   `main`'s merge base (`6a23aa9`). The baseline file is identical on both,
   so the base ref is not the cause.
2. **51 tests fail on the tip; `main` passes the same 70-file set (665
   passed, 0 failed).**
   - The `convmem.py` C0207 fix shifted that file's lines by one, so the
     shadow and R2B writer inventories are stale (`convmem.py:416/520/694/
     710/1772` → `+1`). That cascades through the R2B v2 authority and
     revision tests.
   - The `watch.py` canary baseline hash was not refreshed; three baseline
     tests fail.

Notes for the reviewers, which don't block review:

- **Native-fault detection now uses the real exit code.** Before, a
  crashing child that printed anything to stderr was never counted as a
  native fault. This is a behavior change for every watched path, and Kiro
  should rule on it.
- **C3:** the parent no longer hashes (good). But `streaming_byte_digest_for_path`
  is used only by its test, and the old `streaming_complete_prefix_digest_for_path`
  still has the unbounded buffer. Remove both, or fix and use them. Refusals
  for `source_too_large` carry no digest, which is allowed.
- **Verbose mode now hides child stderr when the child succeeds.**
- **C1 recovery:** an `OSError` on `fstat` is reported as
  `source_too_large`. It fails closed, but the label is wrong.
- **STATUS merge:** the resolution condensed `main`'s Kiro-bootstrap §5
  paragraph instead of keeping it verbatim.

---

## Verification of `86597d8` (Claude, 2026-10-11) — clean; merge `main` before review

Corrective 4b clears both `fc8ea2a` blockers, checked in a clean scratch
worktree with a fresh CI-style config:

- Pylint regression gate: PASS against `main`'s merge base.
- The 70-file Codex, watcher, breaker, doctor, config and inventory set: 705
  passed, 0 failed.
- `streaming_complete_prefix_digest_for_path` matches the reference digest
  on 4,000 random files with buffer sizes 1–16, and peaks at about 136 KB on
  a 16 MiB unterminated line. The unused byte-digest helper is gone.

**Remaining step before review:** `main` moved to `db8aebb` (PR #385, the
#268 watch-memory diagnosis harness). The branch now conflicts with `main` in
four generated files: the shadow and R2B writer inventories,
`eval_corpus/r2b_v2/coverage/inventory.py`, and the canary baseline test.
`convmem.py`, `ingest.py` and `watch.py` auto-merge, but #385 adds
diagnostic markers to `ingest.py` and `convmem.py`, and it changes
`scripts/pylint_regression_gate.py`.

- Merge `origin/main`. Don't rebase.
- Resolve the four files by regenerating them, not by hand-editing.
- Rerun the full suite and the Pylint gate from a clean checkout.
- Remove the leftover `.worktrees/ci-verify-286-4b-clean`.

## Verification of `97a2951` (Claude, 2026-10-11) — clean; remove one stray file before review

Corrective 4c merges `main` at `db8aebb` (PR #385) without rebasing. I
checked it in a clean scratch worktree with a fresh CI-style config:

- Pylint regression gate: PASS against base `db8aebb` (465 findings, 240
  fingerprints, nothing new or increased).
- The 70-file Codex, watcher, breaker, doctor, config and inventory set,
  which now also picks up #385's diagnosis tests: 759 tests, 753 passed,
  6 skipped (opt-in tests), 0 failed. The first run, from a checkout on
  tmpfs, gave 1 failure and 27 errors in two #385 diagnosis files, because
  that harness refuses tmpfs scratch (`scratch_not_disk_backed`). Rerun
  from a disk-backed checkout, those two files pass: 46 passed, 2 skipped.
- The merge keeps both sides:
  - `watch.py` has #385's hermetic inner scope and diagnosis marks, plus
    this branch's exit-91 refusal path, piped stderr and
    `IndexSubprocessError`.
  - #385's inner supervisor returns the child's exit code and inherits its
    stderr, so refusals still reach the watcher during diagnosis runs.
  - The R2B sink pin `convmem.py:699` is the dry-run `ChromaStore`
    constructor, and the canary hashes match the merged files.

**Remaining step before review:** the merge commit adds a stray
`pylint-report.json` (212 KB of generated Pylint output) at the repo root.
Neither parent has this file. Remove it with `git rm`, then push. Also
remove the new leftover `.worktrees/ci-verify-286-4c-clean`.

**Reviewer notes (not blocking):**

- `production_chroma_write_session_call_sites` in the regenerated shadow
  inventory is now ordered as strings (`convmem.py:1777` before
  `convmem.py:421`); both parents ordered it by line number. Tests compare
  it as a set, so this is cosmetic.
- The earlier notes still stand for Kiro and Copilot:
  - Native-fault detection now uses the real exit code.
  - Verbose mode hides child stderr when the child succeeds.
  - In recovery, an `OSError` is labelled `source_too_large`.
  - The STATUS merge condensed `main`'s Kiro-bootstrap paragraph.

**Corrective 4d (`a5f1756`):** removes the stray `pylint-report.json` and
changes nothing else. The tree equals `97a2951` minus that file, and `main` at
`db8aebb` is an ancestor. Cursor removed both leftover test checkouts. Resume
state: ready for Copilot audit and Kiro recheck of exact tip `a5f1756`.

## Kiro recheck of `a5f1756` (2026-10-11) — PASS

Kiro reran the Pylint gate (PASS against base `db8aebb`) and 74 focused
tests, and confirmed that C1–C6, K1 and all six §13 conditions hold. Its
rulings on the reviewer notes:

- (a) Native-fault detection on the real exit code: accepted.
- (b) Verbose mode hiding a successful child's stderr: accepted.
- (c) Recovery labels an `OSError` as `source_too_large`: accepted. It still
  fails closed. A follow-up could map it to a distinct code such as
  `source_unavailable`; not required for this PR.
- (d) The branch STATUS condensed `main`'s Kiro-bootstrap paragraph: accepted,
  but flagged because the sync instruction said not to edit that text. Claude
  confirmed the dropped text includes `main`'s opening line, "The Kiro
  bootstrap remains stopped before grant materialization or paid calls."
  Restore `main`'s paragraph verbatim in a docs-only commit before the PR.
- (e) Shadow inventory in string order: accepted (cosmetic).

The Copilot audit of the same tip is next.

## Copilot re-audit of `a5f1756` (2026-10-11) — FAIL; corrective 5

Copilot closed C2, C3 and C4, and found the #385 merge grants no new
live-route authority. It FAILed the tip on three residual blockers. Claude
confirmed all three in the code at `a5f1756`:

- **C5b** was confirmed by a probe of the parser itself.
- **C1b** and **C6b** were confirmed by reading the code.
- Claude's earlier verifications missed C5b. So did the C5 pattern in this
  handoff: it didn't say that outcomes can contain a colon.

Kiro PASSed the same tip, so this is a same-revision PASS/FAIL conflict. The
findings are reproducible, so a new tip replaces both verdicts. Ryan decides
whether Sol-High adjudicates `a5f1756` anyway.

### Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `feat/2026-10-10-issue-286-codex-rollout-admission` |
| **Tip SHA** | `a5f1756` (Kiro PASS, Copilot FAIL) |
| **Authorization** | Ryan's 2026-10-10 hermetic grant (unchanged) |

### Findings and required fixes

| # | Sev | Finding at `a5f1756` | Location | Required fix |
|---|---|---|---|---|
| C5b | High | The refusal parser accepts only a colon-free outcome (`[^:\s]+`). Every `rebuild_required:<reason>` refusal is emitted with exit 91, but parses as `None`. That includes D8's `rebuild_required:projection_checkpoint_mismatch`, and the continuity refusals Kiro exact-path sources also emit. Those refusals are never quarantined, and each later append respawns a child. This breaks D3, §13 conditions 3–4 and Kiro ruling (b). | `watch_circuit_breaker.py:16–27` | Accept an outcome of one or more `:`-separated lowercase tokens (`[a-z0-9_]+`), followed by an optional final `:<64 hex>` digest. Strip the trailing digest before matching the outcome; a single greedy regex would swallow the digest into the outcome. Keep the exit-91 and whole-line requirements. The parsed outcome and digest must equal what `format_live_route_refused` was given. |
| C1b | High | When no checkpoint exists, recovery skips fresh-run eligibility. `_codex_projection_checkpoint_mismatch` returns `None`, and `_codex_roll_forward_refusal` never applies the fresh path's `bootstrap_required` rule (a processed entry or Chroma rows with no checkpoint). Scenario: the first admitted run crashes in `PREPARING`. Legacy indexing then indexes the source, and admission is restored after another append. Recovery then transforms and commits over the legacy projection. | `incremental_jsonl.py:1068–1071`, `:1112–1163`; the fresh rule at `:427–430` | In `_codex_roll_forward_refusal`, with no checkpoint, refuse `bootstrap_required` whenever the fresh path would. That means a processed entry for the path, or Chroma rows that this transaction did not write. Use the existing refusal flow: clean up, or restore the before-images and return `rolled_back`. Add no new outcome code. |
| C6b | Medium | `expanduser()` runs before the absolute-path check, so a raw `root = "~/.codex/sessions"` is accepted. C6 requires the raw value to be absolute already. | `config.py:64–70` | Check `Path(raw).is_absolute()` on the stripped raw text before any expansion. Reject `~` and `~user` forms as `noncanonical_path`. Any config example or doc for this root uses the absolute form. |
| D1 | Docs | Kiro note (d): the branch STATUS dropped `main`'s Kiro-bootstrap paragraph, including its opening line "The Kiro bootstrap remains stopped before grant materialization or paid calls." | `docs/plans/STATUS-codex-jsonl-production-integration.md` §5–§6 | Restore `main`'s Kiro-bootstrap text in §5 and §6 word for word from `origin/main`. Keep the Codex track as separate added text. Also replace the branch copy of this handoff with the docs-branch version: `git checkout origin/docs/2026-10-10-issue-286-codex-rollout-admission-design -- docs/inter-model/CURSOR-2026-10-11-issue-286-codex-rollout-admission-corrective-4-handoff.md`. |

**Report, don't fix:** say whether recovery for Kiro exact-path sources has the
same no-checkpoint gap as C1b.

### What NOT to build

- No new outcome codes, config keys or admission rules. `OSError` →
  `source_too_large` stays as it is (Kiro ruling (c)).
- No change to C2, C3, C4 or the #385 diagnosis code.
- Everything in this handoff's and the Execute handoff's "What NOT to build"
  still applies. In particular: no live config, watcher, provider call or PR.

### Test expectations

Each test must fail at `a5f1756` and pass after the fix.

1. **C5b:** every refusal outcome the route can emit round-trips through
   `format_live_route_refused` → CLI stderr → `parse_live_route_refused`, with
   and without a digest. That includes `rebuild_required:projection_checkpoint_mismatch`
   and each `rebuild_required:<continuity>` reason. Also:
   - a watcher test where the child exits 91 with the D8 marker quarantines on
     the first event, and later appends spawn zero children, in both verbose
     and quiet mode;
   - the C5 negative tests (exit 1 with a quoted marker; exit 91 without a
     whole-line marker) still don't quarantine.
2. **C1b:** Copilot's scenario refuses `bootstrap_required` with zero provider
   calls and no Chroma or processed change. The scenario: a crashed first
   admitted run in `PREPARING`, then a legacy index, then admission restored
   after an append. A first-run `PREPARING` recovery and a first-run `APPLYING`
   recovery with no legacy run still commit (no regression).
3. **C6b:** `~/.codex/sessions` and `~user/.codex/sessions` fail validation as
   `noncanonical_path`; an absolute canonical root passes.
4. **D1:** `git diff origin/main -- docs/plans/STATUS-codex-jsonl-production-integration.md`
   shows only added Codex text, with no removed or reworded `main` lines.

### Acceptance

- [ ] C5b, C1b, C6b and D1 are fixed, and each is mapped to its test name in
      the handoff-back.
- [ ] From a clean checkout of the pushed tip on disk-backed storage (not
      tmpfs), with a fresh CI config: the full-suite summary line (only the
      known #320 golden-eval failure allowed) and the exact Pylint gate
      command with `--base-ref` set to the merge base, plus its final line.
- [ ] No leftover worktrees, no generated reports committed, and
      `git show --stat` for each new commit.
- [ ] Pushed with an explicit refspec. No force-push, and no rebase; if `main`
      moves, merge it.

## Verification of `78b9295` (Claude, 2026-10-11) — clean; ready for exact-tip review

Corrective 5 is three commits:

- `d1534b0`: the fixes.
- `bbe5bb8`: the corrective-4 recovery tests now crash for real.
- `78b9295`: restores the STATUS text.

I checked it from disk-backed scratch worktrees with a fresh CI-style config:

- **Pylint regression gate:** PASS against base `db8aebb` (463 findings, 240
  fingerprints, nothing new or increased).
- **Focused test set** (Codex, watcher, breaker, doctor, config, inventory,
  and the #385 diagnosis tests): 787 passed, 6 skipped, 2 failed. The two
  failures are `tests/test_watch.py` debounce-timer tests:
  - they allow 10 ms of slack and ran while Pylint loaded the CPU;
  - neither the tests nor `watch.py` changed in corrective 5;
  - rerun on an idle machine, they pass 3 of 3 times.
- **The new tests do test the fixes.** With only `config.py`,
  `incremental_jsonl.py` and `watch_circuit_breaker.py` restored to
  `a5f1756`, the corrective-5 file gives 17 failed, 19 passed, which matches
  Cursor's figure. The failures cover all 12 `rebuild_required:*` round
  trips, both D8 watcher cases, the C1b scenario and both `~` roots.
- **C5b:** the parser strips a trailing 64-hex digest, then requires a
  `:`-separated `[a-z0-9_]+` outcome, keeping the exit-91 and whole-line
  rules.
- **C1b:** recovery with no checkpoint refuses `bootstrap_required` when the
  source has a processed entry or has Chroma rows this transaction didn't
  write.
  - A crashed transaction can't trip this check with its own processed
    entry: `_commit_generation` writes the checkpoint before it publishes
    the processed entry.
  - The test is end to end: a real crash, a real legacy reindex, and then
    recovery.
- **C6b:** the absolute-path check now runs on the raw text, before any
  expansion. `_canonical_config_path` is used only for the admission root,
  so no other config path loses `~` support.
- **D1:** `git diff origin/main` on the STATUS file removes 0 lines.
- **`bbe5bb8` is sound.** The old helper raised a route error, and cleanup
  deleted the transaction, so the corrective-4 "roll-forward" tests had been
  exercising the fresh path. Neither Claude, Kiro nor Copilot had caught
  this.

**Reported gap, outside this fix:** Cursor reports, from reading the code,
that recovery for Kiro exact-path sources has the same gap.
`_codex_roll_forward_refusal` returns at once for a source that isn't
Codex-admitted, and the D8 lineage check is Codex-only. Claude confirmed both
early returns. The gap can't be reached today, because no Kiro exact-path
live source is granted. It needs its own fix before any Kiro exact-path live
incremental run. For Kiro sources the fix isn't a one-liner: they carry no
D8 lineage, so the checkpointed rollback-then-re-enable case needs a design
decision too. Ryan decides whether it's a separate follow-up (recommended)
or part of this PR.

## PR draft (use once Copilot and Kiro both PASS `78b9295`)

**Before merge:** add one docs-only commit to the branch, after the PR is
opened, so the number exists. It does three things:

- states the post-merge reality in the Codex STATUS and LATEST lines: on
  `main`, default off, with Stage 1 as the next gate;
- adds the PR number;
- links the follow-up
  [exact-path recovery parity design](https://github.com/alanmz-crypto/convmem/blob/docs/2026-10-11-issue-286-exact-path-recovery-parity/docs/plans/DESIGN-issue-286-exact-path-recovery-parity.md).

Claude confirms `git diff <reviewed tip>..HEAD -- ':!docs'` is empty, so both
verdicts carry.

**Title:** Admit new Codex rollouts to the guarded incremental index route (off by default)

**Body:**

```markdown
## What changes for Ryan

After this merges, the guarded incremental route can index **new** Codex
rollout transcripts incrementally from their first index, instead of
re-indexing the whole file on every append. Whole-file re-indexing is the
main source of repeated paid re-indexing and of the largest watcher index
children. Nothing turns on by itself. The route stays off until you add an
explicit `codex_rollout_admission` config and grant Stage 1. Rollouts that
existed before activation stay on the legacy route exactly as today.

## Who / What / When / Why / How

- **Who:** Claude designed it (Kiro PASS at `9e91973`; §13 amended
  2026-10-11). Cursor implemented it through five correctives. Copilot
  audited and Kiro reviewed each exact tip, and Claude verified each tip
  before review.
- **What:**
  - time-bounded, identity-checked admission of new rollouts under
    `/home/<user>/.codex/sessions` (D1);
  - a terminal refusal quarantine, keyed by path (D3, §13);
  - a per-run transform cap and frontier-subset rule (D4);
  - a 256 MiB source ceiling (D5);
  - one-way route rollback, detected by lineage (D8);
  - the same guards on crash recovery;
  - watcher refusal handling (exit 91 plus a whole-line marker);
  - strict validation of the admission root path.
- **When:** Copilot audit and Kiro recheck PASSed exact tip `78b9295`.
  `main` is merged in at `db8aebb` (#385).
- **Why:** from Sep 26 to Oct 5 the watcher spawned 133 Codex rollout index
  children. One rollout was re-indexed 44 times, and all three children that
  hit the 12 GiB cap were Codex rollouts.
- **How:** a new admission module, plus coordinator guards on both fresh
  runs and recovery. The watcher circuit breaker moves into its own module.
  This PR changes no live config, systemd unit, runtime worktree or
  watcher.

## Not in this PR

- **Activation.** Stage 1 (manual, watcher stopped) and Stage 2 (a 24 h
  watcher canary, which also needs #308 and the watch-memory drop-in
  reconciliation) are separate Ryan grants.
- **Kiro exact-path sources.** They keep two recovery gaps that this PR
  closes only for Codex. Neither is reachable while the route is off. They
  are tracked in `DESIGN-issue-286-exact-path-recovery-parity.md` (follow-up
  branch).

## Verification

- Pylint regression gate PASS against the `main` merge base.
- Full suite (Cursor, clean clone): 3015 passed, plus the 1 known #320
  golden-eval failure, which depends on the live corpus.
- Focused set (Claude): 787 passed. Two debounce-timer tests failed only
  under CPU load and pass on rerun.
- Copilot audit PASS and Kiro PASS at `78b9295`.

## Merge reading

- [Design](docs/plans/DESIGN-issue-286-codex-rollout-admission.md)
- [Execute handoff](docs/inter-model/CURSOR-2026-10-10-issue-286-codex-rollout-admission-execute-handoff.md)
- [Corrective-4 handoff and verification record](docs/inter-model/CURSOR-2026-10-11-issue-286-codex-rollout-admission-corrective-4-handoff.md)
- [Arc Codex status brief](docs/plans/STATUS-codex-jsonl-production-integration.md)
- [LATEST](docs/inter-model/LATEST.md)

Refs #286. Squash merge is fine.

## TL;DR

New Codex rollouts can use the guarded incremental route, off by default,
with the same fail-closed guards on fresh runs and crash recovery. Nothing
activates until Ryan grants Stage 1.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```
