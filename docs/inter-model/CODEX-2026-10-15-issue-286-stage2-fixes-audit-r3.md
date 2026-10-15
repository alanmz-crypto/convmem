# [Arc Codex #286] Stage 2 safety audit — round 3

**Verdict: FAIL at `7d46e6ed36db4c6103b3a7faf265d31ad5843ea7`.**

**Auditor:** Codex, performing Ryan's explicitly requested independent safety audit.
**Date:** 2026-10-15 UTC. **Implementation owner:** Cursor; verification evidence supplied by Claude.

The sequential retry and ordinary ingest corrections pass, but three reproducible blockers remain: concurrent routes lose retry reservations and exceed the attempt cap; repair crashes when its prepared target drifts; and monitor retries an initially unchanged row with an empty embedding. Two lower-severity observations concern cache invalidation after export failure and the new artifact-directory scan exclusion.

This report is evidence for Ryan's disposition, not an implementation, merge, deployment, provider, or canary grant.

## Revision and scope

- **Audited implementation:** `origin/fix/2026-10-12-issue-286-stage2-wedge-fixes`, exactly `7d46e6ed36db4c6103b3a7faf265d31ad5843ea7`, confirmed after fetching origin. The requested delta is `8d6ee76..7d46e6e`; callers and existing retry machinery were also inspected where necessary to evaluate the fixes.
- **Prior independent audit:** `docs/2026-10-14-issue-286-stage2-fixes-audit-r2`, `bd440dc`; report `docs/inter-model/CODEX-2026-10-14-issue-286-stage2-fixes-audit-r2.md`. Its R2-F1–F4 and eight executable probes are the recheck baseline.
- **Claude's evidence:** `origin/docs/2026-10-12-issue-286-stage2-fixes-handoff`, exactly `7911704e99f228d1888cbf7d89d51660815b7a6f`; rounds 15–18 in `docs/inter-model/CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md`. Claude's round-18 PASS is a supplied claim, independently checked below.
- **Report branch:** `docs/2026-10-15-issue-286-stage2-fixes-audit-r3`, based on fetched main `c6f07241ccf1a71d9d874fee963a37b04091b3ce`. Only this report is changed. All implementation line numbers below refer to the audited implementation, not the report branch.

The Arc Codex STATUS brief was read for orientation. Its older operational narrative is not used as evidence of current deployment. Known #393, Z1, and X2–X5 are not re-audited or used as blockers. There is no new same-revision opposing Kiro verdict in this audit and no conflict-adjudication invocation.

## Blocking findings

### R3-F1 — High: concurrent retry admission loses reservations and exceeds the paid-work bound

**Locations:** `incremental_retry_state.py:216–232, 251–287`; `incremental_jsonl.py:2800–2807`; the coordinator acquires its per-source advisory lock only at `incremental_jsonl.py:2483–2487`.

The retry gate and durable reservation execute before `coordinator.run()` acquires the source lock. Their read-modify-write operations have no common lock. Atomic replacement makes each individual JSON publication whole; it does not make the gate check and counter increment atomic across callers. Multiple callers can all read an empty state, publish `attempts_on_prefix=1`, and enter the coordinator. The coordinator serializes transformation, but does not recheck admission after waiting for that lock.

**Reproduction:** four threads invoked the real scratch production route for the same unchanged source. Two barriers in a wrapper around retry `_write` forced all four reservation payloads to be prepared before publication, then all four publications to finish before proceeding. The wrapper still called the real atomic writer. Source locking and coordinator execution were real; providers were fake, and `_write_prepared` raised a synthetic filesystem error before any completed prepared artifact existed.

**Observed:** four fake summary calls, four reservation values `[1, 1, 1, 1]`, and persisted `attempts_on_prefix=1`. The configured prefix cap is three. Later `live_route_refused` results do not undo work already performed. Individual returned error-code ordering varies with scheduling; the four calls and lost reservations reproduced on every executed run of this probe.

This is a remaining R2-F1 gap in corrective 12's reservation mechanism, already present at the requested delta's starting revision `8d6ee76`, not a claim that the small retry-state delta alone introduced it. It is within the requested paid-call-bounds recheck. Sequential tests do not establish concurrent bounds.

**Required correction:** serialize admission, reservation, and subsequent state accounting against the same source's competing operations, and revalidate a queued attempt before it can perform transform work. Preserve the provider-outside-C1 requirement. Add a real-route concurrent admission test that cannot admit more work than the bound. No fix was made here.

### R3-F2 — Medium: repair crashes instead of retrying after target drift

**Locations:** `observe.py:772–773, 841–857`, especially line 848.

The repair path now initially constructs `_DocumentAccurateReadonlyStore`, but its retry branch still calls `open_readonly_unit_store` without importing or defining that name. The local import was removed when the initial reader changed in `700b6ba`. The retry branch was introduced in `2ffaf79` and is reachable through normal cooperating-writer drift.

**Reproduction:** seed a real scratch decision, make its document empty, then call the actual `repair_empty_ledger_documents`. During the fake embedding callback, a cooperating writer fills that document through the real C1/production-store session. Commit correctly detects the stale prepared digest and releases its write scope. The retry handler then raises `NameError: name 'open_readonly_unit_store' is not defined`.

The embedding callback ran at `(index_write_lock_depth, production_chroma_store_session_depth) == (0, 0)`. Thus the lock-placement correction works, but the promised bounded repair retry does not. The job aborts rather than returning a repaired/skipped result or processing its remaining pending records. This finding concerns mutating repair; doctor's dry-run does not enter this branch.

**Required correction:** make the fresh-reader path executable and preserve document-accurate validation through its retry. Test real drift during repair, not only the ordinary repair and dry-run scan. No fix was made here.

### R3-F3 — Medium: monitor's drift retry passes an empty embedding to Chroma

**Locations:** `observe.py:292–309, 365`; `monitor.py:619–626`.

An unchanged prepared row intentionally has `embedding=[]`, because no embedding was needed. If that row changes before commit, monitor refreshes the reader and reparses the record, but unconditionally passes `precomputed_embedding=current.embedding`. The now-needed update treats the empty list as an available embedding and sends it to `update_unit`.

**Reproduction:** run the real `run_monitor` twice against scratch Chroma with fake HTTP probes and fake embeddings, creating its observation and verification rows. On the third run, let the first unchanged verification prepare normally, then change its document through a cooperating C1 writer. The first commit detects drift; the second commit uses the empty embedding.

**Observed:** Chroma receives `embeddings=[[]]` and raises `IndexError: list index out of range in update.` The third monitor invocation makes zero embedding calls. It aborts instead of completing or recording a bounded drift refusal. The earlier reader-refresh correction in `2ffaf79` exposes this transition from a skipped row to an update; the unchanged-row and already-embedded-update tests do not exercise it.

**Required correction:** distinguish a reusable computed embedding from the absence of one. When drift turns a skip into an update, compute the missing embedding outside C1 or refuse cleanly before mutation. Exercise the real monitor orchestration with this interleaving. No fix was made here.

## Lower-severity observations

### R3-O1 — Low: export failure bypasses post-write cache invalidation

**Locations:** `observe.py:365–388`.

Successful observation writes now invalidate the ledger cache, and the existing sequential upsert/repair regressions pass. However, invalidation occurs after export publication. If Chroma succeeds and `_upsert_jsonl_line` raises, that invalidation is skipped.

**Scratch reproduction:** prepare a missing ledger ID, thereby caching an empty ledger index; commit the insert through the real write session while injecting an export `OSError`. The durable Chroma row exists, but `build_ledger_index` still omits it, even when the next prepare uses a newly opened readonly reader. That prepare incorrectly describes the target as missing. A subsequent targeted commit check correctly refuses the duplicate insert.

This is not evidence of duplicate persistence or a successful false update. It limits the claim that every write clears the cache and can produce stale reads or unnecessary drift retries within the same process. Invalidate after a successful store mutation even when its later export fails. The new probe verifies both the stale cache and the protective refusal.

### R3-O2 — Low: the new artifacts exclusion also hides tracked writers

**Location:** `eval_corpus/r2b_v2/coverage/inventory.py:306–331`; related exclusion in `tests/test_shadow_writer_coverage_scan.py`.

The delta adds an unconditional `artifacts/` skip. Unlike `review-bundles/`, it does not check whether a file is tracked. In a real temporary Git repository containing identical tracked constructors under both directories, the actual R2b scanner reports `review-bundles/tracked_writer.py:2` but omits `artifacts/tracked_writer.py:2`.

No tracked implementation file exists under `artifacts/` at the audited tip, so this is a coverage-hardening observation rather than a demonstrated current production bypass. Preserve the tracked-file distinction when excluding scratch snapshots. The existing tracked-review-bundle test still passes and does not cover this newly excluded directory.

## Disposition of round 2 and requested focus areas

- **R2-F1:** the original unwritable-state and alternating-error counterexamples are corrected sequentially. An additional post-admission failure-recording probe makes three fake summary calls, then refuses the next three attempts; failed counter publication no longer permits indefinite sequential work. **Not closed overall:** R3-F1 demonstrates lost concurrent reservations.
- **R2-F2:** **closed for the exercised paths.** Refine appends now take C1, and approved-dedupe reads its queue after taking C1. An independent thread started at rollback's read/replace seam waits for C1, then appends successfully after rollback; its row and the earlier foreign row survive while the transaction-owned row is removed. The limiter regression also passes.
- **R2-F3:** the old embedding-under-C1 paths no longer reproduce. Single-approved ingest embeds at `(0, 0)`; commit detects drift without invoking a provider; retained tests verify reprepare outside C1 and provider-entry rejection under C1. **Recovery behavior still has blockers:** R3-F2 and R3-F3. No new executed provider call under C1 was found.
- **R2-F4:** the original direct commit of a deleted monitor target now raises drift before export/update. **The broader monitor retry path is not approved:** R3-F3.
- **Targeted reads under C1:** unchanged and changed readonly preparations commit without representation-induced drift; updates/skips re-read the target by ID; inserts check current active rows by ledger ID; the batch validates all prepared rows before its write loop. The retained `s1` test finds no full metadata scans in batch commit. This audit did not independently repeat Claude's 109k-unit timing measurements.
- **Insert races and duplicate input IDs:** retained tests reject a newly appeared insert target and confirm last-line coalescing before embedding, including all four duplicate-ID variants. The real add-command drift retry passes.
- **Ledger cache:** normal post-write invalidation and sequential upserts pass. Exception-path limitation: R3-O1.
- **Side files:** exercised dedupe appends/read-modify-write operations respect C1; exports also retain their export-file lock. Retry-state publication is not protected by C1, nor should paid work be moved inside C1 to fix it; its own source-level accounting needs serialization (R3-F1).

## Independent execution and limits

Implementation worktree: `/home/lauer/.kiro/audit-286-r3/code`, detached at the exact target. Documentation worktree: `/home/lauer/.kiro/audit-286-r3/docs`. Both are disk-backed ext4. The shared checkout was not switched or edited. New probes exist only in scratch, outside both worktrees.

The harness uses `/home/lauer/miniforge3/envs/convmem/bin/python`, `env -i`, a private HOME/TMPDIR, disabled pytest plugin autoload/bytecode/cache, endpoint overrides to a closed port, fake providers, and the reused pre-import audit hook denying Python network connections and production-path opens. Repository fixtures redirect live config and writer defaults to scratch. These controls are the same scoped test boundary used in round 2; they are not a certification of every native library or every repository test.

Results, recorded independently at `7d46e6e`:

- **Focused suite:** 127 passed, 5 subtests passed, 20.63 s. Includes round-2 focused files, corrective 12, Claude rounds 15–17, upsert, ledger-document, monitor, add-severity, and propose-decision tests.
- **Original eight round-2 probes, unchanged:** 1 passed and 7 failed, 4.02 s. Six failures are expected because their assertions describe the old unsafe behavior: unwritable state now refuses; alternating failures stop at three summaries; the refine worker blocks on C1; single-approved embedding runs at `(0, 0)`; both missing-target monitor probes raise drift. The seventh probe stops at its obsolete `rows[0][2]` tuple access. Its intended drift case is covered by corrective-12 and retained round-15 tests. These expected old-probe failures are not presented as repository regressions or as eight passing safety tests.
- **New independent scratch probes:** 7 passed, 2.28 s. Five assert the counterexamples in R3-F1–F3/O1–O2; two assert safe behavior for post-admission persistence failure and concurrent queue preservation. A passing counterexample test supports a finding, not an implementation PASS.
- **Selected inventory/baseline tests:** 36 passed, 2.84 s (`test_shadow_writer_coverage_scan.py`, `test_shadow_writer_gate_c3.py`, `test_incremental_jsonl_canary_baseline.py`). This is not a claim that the entire R2b suite was rerun.
- **Round-2 D1 sequence followed by retry probes:** 47 passed, 2 skipped, 3 failed, 5.94 s. The failures remain `test_prefix_route_isolation_hermetic`, `test_injected_kill_blocked_with_phase_evidence`, and `test_phase_order_subset` in `test_watch_oom_live_diagnosis_d1.py`. Their subprocesses report `bwrap: Can't mkdir parents for .../harness/home/.local/share/convmem: Read-only file system`. The same three names/error were observed in round 2. No independent main rerun was performed here, so no new baseline-equivalence claim is made.
- `git diff --check 8d6ee76..7d46e6e` passed. The implementation worktree remained clean. No full-suite rerun, live canary, or live data mutation was performed.

An initial monitor probe expected `ValueError`; the actual Chroma validation exception is `IndexError`. Only that scratch assertion was corrected before the final seven-probe run. No implementation changes were made. Earlier probe runs and their outputs remain alongside the final evidence.

The required startup `convmem doctor`, `brief --stdout-only`, and `unresolved` ran for read-only orientation; doctor exited 0 with nonfatal warnings. They are not canary evidence. No paid provider calls, indexing, corpus writes, service/config/runtime changes, fixes, PR creation, merge, or force-push were performed. Track A indexing is intentionally withheld under Ryan's task-specific no-production-state/no-paid-call restriction; invoking ingestion at handoff would exceed that restriction.

## Reproduction and evidence locations

Scratch root: `/home/lauer/.kiro/audit-286-r3/harness/`.

- New probes: `test_audit_r3.py`, SHA-256 `3d8cab2077ee58a298dd599ce882a1f9cbfe195d33b9f6d7a3d6ba8db19718c5`.
- Original round-2 probes: `test_audit_r2.py`, SHA-256 `12aa72f9ee22a12c9097bfc71d1ada21d31000c0ddf028e173fae39880aa0e2d`.
- Runner: `run-tests.sh`, SHA-256 `b516d0c51eee45b279c98b0c30e6a99f5a28a80c0d2c68367450f138cfb348a1`.
- Isolation hook: `sitecustomize.py`, SHA-256 `9d99fc9ea48691a8eeba75c52082ae4a3c263975fcfb1ee37c932674f0ec0dab`.
- Final outputs: `report-results.txt`, `r2-results.txt`, `focused-results.txt`, `inventory-results.txt`, `d1-results.txt`.

Run the new probes with a **new, unused** scratch basetemp:

```bash
bash /home/lauer/.kiro/audit-286-r3/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r3/harness/base-reproduce \
  -q -s /home/lauer/.kiro/audit-286-r3/harness/test_audit_r3.py
```

The scenario descriptions above explain the interleavings without requiring the scratch files. Probe source remains scratch-only as requested; it is not added as production tests or copied into this documentation branch.

## [Arc Codex #286] Handoff

I finished: round-3 safety audit of exact implementation `7d46e6e` — **FAIL**.
Next step: Ryan routes the three blockers for authorized correction, then requests an exact-revision recheck; O1–O2 remain lower-severity follow-ups.
Next lane: Ryan for disposition; Cursor for implementation if authorized.
See my work: this report's three blocking findings and independent execution evidence.

Branch: `docs/2026-10-15-issue-286-stage2-fixes-audit-r3`. The final documentation SHA and explicit-refspec push result are supplied in the chat handoff. This report is the only tracked change; no PR was requested or created.

### Optional PR text for Ryan

**Title:** Document remaining retry and drift-recovery safety failures

**Description:**

This publishes the round-3 FAIL verdict so Ryan can route the remaining Stage 2 corrections before approval. Codex audited Cursor's issue #286 implementation at exact revision `7d46e6e` on 2026-10-15, checking Claude's rounds 15–18 and rerunning the prior probes. Concurrent retry admission exceeds the attempt cap; repair and monitor each fail on a real prepare-to-commit drift path. Two lower-severity observations cover cache invalidation on export failure and tracked artifacts omitted from coverage scans. No implementation or production change is included.

Validation: 127 focused tests and 5 subtests passed; 36 selected inventory/baseline tests passed; seven scratch probes reproduced five findings and two safe controls. The D1 sequence retains three documented scratch-HOME bwrap failures. Original round-2 counterexample assertions were rerun and their changed outcomes are explained in the report.

**TL;DR:** [Arc Codex #286] Documentation only; safety verdict **FAIL**, with three blockers and two lower-severity observations.

## TL;DR

- [Arc Codex #286] **FAIL at `7d46e6e`:** concurrent admission loses retry counts; repair crashes on drift; monitor reuses an empty embedding after drift.
- Sequential retry bounds, C1 provider separation, targeted validation, duplicate-input coalescing, and concurrent queue preservation pass the exercised checks. Cache invalidation still has an export-failure gap.
- Evidence is isolated and provider-free. Only this audit report is committed; no fixes or production changes.

<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc orientation; this audit does not authorize activation -->
<!-- src: /home/lauer/.kiro/audit-286-r2/docs/docs/inter-model/CODEX-2026-10-14-issue-286-stage2-fixes-audit-r2.md, /home/lauer/.kiro/audit-286-r3/harness/test_audit_r3.py, /home/lauer/.kiro/audit-286-r3/harness/report-results.txt — prior findings and independent scratch evidence -->
