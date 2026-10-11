# EXECUTION — Diagnose the live watch-child memory spike

**Arc:** Trapdoor Hunt · **Issue:** [#268](https://github.com/alanmz-crypto/convmem/issues/268)
**State:** DRAFT for Kiro design review; no harness implementation or host-run grant
**Date:** 2026-10-10

## 1. Consequence for Ryan

The successful bounded comparison in [PR #382](https://github.com/alanmz-crypto/convmem/pull/382) measures the merged ingestion path with synthetic transcripts and fake providers. It does not reproduce or explain the historical watch child's roughly 12.5 GiB memory peak. Keep issue #268 open and the watcher inactive while one *actual-source-shaped*, scratch-only investigation separates source-rebuild work from corpus-wide post-index work. The output is a phase-attributed memory record and a specific next decision, not automatic permission to restart the watcher or advance issue #286.

## 2. Evidence and competing explanations

- The September 12 recurrence reached the watch child's 12 GiB cgroup ceiling while indexing 5.8–9.7 MiB Codex JSONL triggers. The source files were small relative to the observed peak; [the bounded export plan](EXECUTION-watch-oom-bounded-export-compaction.md) and [the streamed brief plan](EXECUTION-watch-oom-stream-brief-metadata.md) identified and corrected separate corpus-sized allocators. Neither claimed full OOM closure.
- `watch.py:flush_path()` still dispatches `index --file` after a whole-file skip check. `ingest.py:_index_one_file()` hashes the file again, tries the guarded incremental route, and otherwise snapshots existing source rows, parses the complete source, processes every chunk, prunes completed replacements, and refreshes global outputs. The current 900-second child timeout limits duration, not peak memory.
- The earlier design at `92395e9:docs/plans/DESIGN-watch-incremental-index.md` correctly identified repeated full-file work but incorrectly described `evaluate_ingest_batch().accepted_rows` as retained for the whole source. The current code calls that function per chunk. Do not choose a units-in-flight limit `K` from that historical claim.
- The [PR #382](https://github.com/alanmz-crypto/convmem/pull/382) 58,825-row candidate arm peaked at 323.8 MiB process RSS under a 6 GiB/zero-swap cgroup; its baseline peaked at 2,244.5 MiB RSS and 4.04 GiB cgroup charge. Those are descriptive cross-version synthetic results. They do not measure the live source, live corpus state, or the production provider path.
- On 2026-10-10, a read-only `systemctl --user show` reported `convmem-watch.service` inactive and disabled. A bounded current `journalctl --user -u convmem-watch.service` query for September 12–13 returned no lines. The preserved [September 12 incident handoff](https://github.com/alanmz-crypto/convmem/blob/3eea055/docs/inter-model/KIRO-2026-09-12-arc-codex-watch-oom-recurrence-handoff.md) records the historical journal excerpts; absence from the current journal does not erase that evidence.

The investigation must distinguish at least these explanations: repeated source parsing/transforms; Chroma source-row snapshot and per-chunk writes; corpus-wide export or brief work; provider wait/retry and object lifetime; and cgroup charges that exceed sampled process RSS. A low synthetic RSS figure cannot eliminate any of these for the live workload.

## 3. Decision sequence and scope

### D0 — read-only source packet (feasibility checked; no run grant)

The archived September 12 handoff records four kernel cgroup OOM kills at 18:05:38 (`run-p816799-i780746.scope`), 19:51:02 (`run-p880132-i785397.scope`), 20:12:37 (`run-p895258-i882128.scope`), and 20:30:48 (`run-p905242-i871930.scope`), all at about 12.5 GiB anonymous RSS under the configured 12 GiB child cap. Its watch excerpts identify two OOM-exit rollouts: `01a09438…` at 19:51 (9.7 MB then) and `01a0948f…` at 20:30 (7.8 MB then). The handoff does not identify the source for the other two kills. `history.jsonl` was 5.8 MB and **timed out** after 900 seconds at 19:43; do not count that timeout as an OOM kill.

Read-only `stat` and hashing on 2026-10-10 found the two named rollout files still present. `01a09438…` is now 15,195,057 bytes (2,019 lines), last modified September 16, SHA-256 `101fd572cc06d4a33cfad843520e878c74734e47dae4494e44b70c2166fe25c7`. `01a0948f…` is now 58,019,647 bytes (9,096 lines), last modified September 18, SHA-256 `ad4fa97981892fb8dcc37d586ded2e09d50309c8216c1b6d01e5c1aa0684eb0c`. Both grew after the incident. These **current** bytes are available for a representative replay; no exact incident-time source snapshot was located in the checked surfaces. The third September-12-named rollout (0.94 MiB now) is not identified in the handoff as an OOM trigger. `history.jsonl` is still excluded from watch indexing; no exclusion was changed.

A read-only Restic inventory found complete-data-v2 snapshot `ac1087c8` from 2026-10-10 at 00:10 CDT, reported size 38.427 GiB. It covers ConvMem's data root, not the raw Codex transcript source. Its consistency and suitability for a scratch replay have **not** been validated. The proposed ext4 scratch mount had 305,700,995,072 bytes free at this check; D1 must remeasure and set a grant-specific reserve. The watcher remains inactive/disabled. No source was copied, no backup restored, and no indexing run occurred.

D0 therefore selects `01a09438…` as the smaller **representative** source candidate, subject to a fresh source hash at copy time and D1 backup validation. If the current backup cannot yield a consistent local scratch corpus within the approved resource budget, stop and return a revised design; never substitute live Chroma. Do not copy raw transcript text into git, a model prompt, or a log, and do not describe a replay of current bytes as the September 12 failure's exact reproduction.

### D1 — design and hermetic harness (separate Ryan Execute decision)

Cursor proposes a test-only harness on a separate branch, derived from the D0 packet. Its subject is one frozen copy of an actual affected JSONL source and a consistent, local scratch corpus restored from a verified backup if available. If a consistent backup cannot be obtained within the approved resource budget, stop and return a revised design; do not use live Chroma as a shortcut. The harness must launch the *current-main legacy watch-child command path* in a transient user cgroup, with all mutable roots redirected to disk-backed scratch, zero swap, network and production-path denial, fake providers, and canaries on production Chroma, export, brief, processed state, failure log, locks, and source files. Compute a content-and-mtime canary manifest before and after replay; any changed entry blocks the result. The frozen source copy must be opened read-only by the worker, with write-open denial and a matching hash before and after. The source copy and scratch data remain local, private, and untracked. No watcher service is started.

The harness first proves its routing and isolation with a small source prefix. Only after Copilot audits the isolation boundary and Kiro reviews the exact harness tip may Ryan consider one named-host, named-lane, one-shot replay grant. A grant must bind the exact target/harness revision, source snapshot hash, scratch path, cgroup `memory.max`/zero swap, a maximum 250 ms sampling period, a quiet writer window, and numeric minimum available-RAM and free-disk thresholds. D0 must estimate the restored corpus footprint; the proposed thresholds must cover the cgroup cap plus host reserve and the full scratch copy plus output reserve, respectively. Ryan fixes the numbers in the grant before execution, and the parent checks them before the run and during it. The 12 GiB historical cap is a candidate diagnostic bound, **not** an approved value; D0 and review must justify the final cap and host stop thresholds before Ryan grants execution. No cap increase or retry is implicit.

### D2 — one bounded replay (fresh, exact one-shot grant only)

Run one full-file replay of that frozen source under the reviewed limit. An out-of-worker-cgroup parent samples the worker's cgroup `memory.current`, `memory.peak`, and `memory.events` (`max`, `oom`, `oom_kill`) plus worker RSS at no more than 250 ms intervals and on each phase marker. The parent writes a private, bounded telemetry file in scratch and captures final cgroup counters **before** transient-unit removal; a worker SIGKILL must not erase the record. D1 must demonstrate this channel in a small injected-kill control and account for sampler memory and I/O. Mark whole-file skip hash, index hash, source-row snapshot, parse/chunk construction, per-chunk build and Chroma write, processed commit, brief refresh, and export compaction in the actual call order. Record counts and durations without transcript text or provider payloads. An optional second append arm needs its own explicit bound in the grant; it is not part of the default one-shot.

Stop and mark the replay **blocked** on source/corpus identity mismatch, production-path or network attempt, canary drift, missing phase/cgroup telemetry, writer collision, host headroom breach, or any undeclared model call. A cgroup OOM with intact telemetry is a diagnostic observation, not a successful indexing result. Do not retry, change the cap, or reinclude excluded sources during the grant.

## 4. Evidence and decision rule

The report must identify the exact source and corpus snapshot by hash and date; current-main and harness SHA; applied cgroup and swap limits; stage counts/durations; cgroup events; result and denial/canary status; and the differences from the historical watcher setup. For every phase and for the whole run, report **peak process RSS beside peak cgroup charge** in separate columns, with their sampling/peak methods stated. Keep raw source and copied corpus outside the repository.

- If the isolated replay reproduces a comparable spike, use the first phase that grows and its surrounding retained objects to propose a *narrow* code correction. Verify that correction against the same replay and ordinary hermetic tests before any watcher decision.
- If the replay stays low, record the non-reproduction. The fake-provider path, source/corpus time gap, or missing historic source may matter; do not declare the live OOM fixed or raise a memory cap to make the result look conclusive.
- If the replay is blocked, preserve the partial telemetry and return to design review. No operational conclusion follows.

Only Ryan decides a later watcher operation, exclusions, cap change, production profiling, or issue #286 progression. This plan grants none of them. It also leaves `summarize_model`, the OpenClaw manifest, monitor timer, shadow ledger, and the four protected ConvMem Switchboard planning files untouched.

## 5. Review request

Kiro should PASS or FAIL this exact plan tip on whether D0 can bind a meaningful source/corpus snapshot, the scratch/production denial boundary, cgroup telemetry after worker death, phase attribution, one-shot stop rules, and the honesty of the non-reproduction outcome. Review does not authorize D1 implementation or D2 execution. A future Cursor harness requires targeted Copilot isolation audit and Kiro exact-tip review before Ryan considers a separate host grant.

**TL;DR:** [Arc Trapdoor Hunt] Preserve the reviewed §9.7 result in PR #382, then collect a metadata-only source packet and design one scratch-only replay of the real watch-child path. Keep the watcher off and issue #268 open until a separately granted run identifies the live memory phase.
