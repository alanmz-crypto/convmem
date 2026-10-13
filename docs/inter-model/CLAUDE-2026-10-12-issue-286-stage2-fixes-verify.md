# Verify: Stage 2 wedge fixes, round 8 at `e1914f5`: FAIL; the real index entrypoint now pays and then fails, so deploying this tip would burn; corrective 7

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

## Burn status

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

## Verdict (round 8)

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

## Findings (round 8)

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

## Test results (round 8)

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

## Corrective 7 for Cursor

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
