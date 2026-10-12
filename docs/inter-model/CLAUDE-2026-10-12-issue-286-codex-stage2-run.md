# Stage 2 run log: 24 h watcher canary

**Arc: Codex (#286).**
**Grant:** Ryan, 2026-10-12, "grant with ceiling". This grants the Stage 2
packet in `CLAUDE-2026-10-11-issue-286-codex-stage1-packet.md`, with the
proposed 24 h ceiling of **200 paid calls**.
**Runner:** Claude.

## Steps (done 2026-10-12, CDT)

1. **Backup gate.** `convmem-restic-local.service` reported "OK: current —
   snapshot covers today (id=b9a8977a…)". It was a no-op: 1.7 s of CPU and a
   79 MiB peak.
2. **Doctor preview** on `8a7cdab` with the live config, from a scratch
   worktree: exit 0, 0 FAIL, and no status differences from `05aa2c8`. The
   five WARNs are all known: `embed_collection_identity`, `restic_external`,
   `chroma_audit`, `standing_register` and `arc_staleness`.
3. **Promote.** `runtime-main` was fast-forwarded from `05aa2c8` to
   `8a7cdab`. Doctor exits 0, with the same statuses as the preview.
4. **Start.** `systemctl --user enable --now convmem-watch.service` at **T0
   = 06:57:25**. The service is active and enabled, with debounce 90 s and
   subprocess indexing on.

**Startup note.** The repository-knowledge startup sync failed:
"manifest_invalid: 63 unclassified tracked path(s);
first=bootstrap_safety.py". The watcher caught the exception and kept
running. That indexing is documentary, local embeddings only, so no paid
calls are involved. The manifest belongs to OpenClaw Watch Coverage, and it
isn't changed here.

## Measurement

The measurement script reads the service journal since T0, `systemctl
show`, the cgroup `memory.events`, the sidecar record count and
`processed.json` chunk counts. Every check reports paid calls first.

| Check | Time | Paid (admitted / legacy est.) | Spawns | Memory peak | Stop |
|---|---|---|---|---|---|
| T0 + 1 min | 06:58 | 0 / 0 | 0 | 0.46 GiB, no OOM events | none |
| T0 + 15 min | 07:12 | 0 / 0 | 0 | 4.10 GiB, no OOM events | none (window clean) |

## Stopped at T0 + 16 min (07:13:42): watcher memory growth

**Burn:** 0 paid calls. Nothing was indexed: there were no spawns, and the
sidecar was never written.

**Why Claude stopped it before any stop condition fired:**

- **The memory is the watcher's own heap.** The main process held
  **4.07 GiB anonymous** memory (only 0.09 GiB file cache) without running
  a single index child.
- **It was still growing.** RSS went 4.38 → 4.42 → 4.47 GB in about 20 s,
  roughly 2.4 MB/s.
- **The OOM would come quickly.** The service limit is `MemoryMax=8G`
  shared with the index children, and each child peaked at 6.3–6.7 GiB in
  Stage 1. So the first index run, or about 25 more idle minutes, would
  have meant an OOM kill. Under an OOM, a child can be killed mid-write.
- **Rollback:** `systemctl --user disable --now` gave a clean stop. Over its
  16 min 16 s, the service had used 4 min 19 s of CPU, with a 4.4G peak.
  Snapshot at 07:13:37: 43 threads, 12,086 inotify watches, 42 fds.

**This is a regression since Oct 5.** These are the service's own
`Consumed …` journal lines:

| Run ended | Wall clock | Memory peak |
|---|---|---|
| Oct 5, 12:55 | 30 min | 467.5M |
| Oct 5, 13:05 | 5 min | 462.3M |
| Oct 12, 07:13 | 16 min | **4.4G** |

Since Oct 5, the runtime moved from `a92a74e` to `8a7cdab` (46 commits).
`watch.py`, `ingest.py`, `incremental_jsonl.py`, `source_reconciler.py`,
`watch_circuit_breaker.py` and the new `live_diagnosis.py` all changed. The
live config also gained `[index.incremental_jsonl] enabled = true`.

**Ruled out so far (read-only):**

- `live_diagnosis.mark` is inert unless its env vars are set.
- `ManifestPoller` keeps a one-entry dict.
- Startup reconciliation runs before the observers start, and it had
  finished within the first minute. The growth happened in the idle loop,
  with no file events.

**Unchanged:** `runtime-main` stays at `8a7cdab`, because #308 adds only a
skip path. The live config is untouched. The watcher is inactive and
disabled.

**Next:** a hermetic diagnosis of the idle-loop growth: compare `a92a74e`
with `8a7cdab` against a scratch config and scratch roots, with no provider
access. A Stage 2 restart needs the fix and a new Ryan grant.

## Hermetic diagnosis, round 1 (Claude, 2026-10-12, no grant needed)

**Harness.** The watcher ran from a scratch checkout under `env -i` (no
provider keys), with `HOME` set to a scratch dir, so every `~` path
resolved inside scratch. Each run had a fresh data root, a scratch config
and a 90 s debounce, and nothing was indexed (0 spawns in every run). RSS
was sampled every 5 s.

| Run (runtime `8a7cdab`, incremental on) | What it reproduces | RSS |
|---|---|---|
| A 54 MiB pre-activation rollout appended every 0.28 s | The busiest live source (≈ 3.6 events/s) | 95 MB flat for 3 min |
| `kiro-cli` churn | Inserts into `data.sqlite3` with journal events, plus `.refresh.lock`, `publish.cursor`, `run-receipts/*.json` and heartbeat writes | 95 MB flat for 3 min |
| The invalid repository-knowledge manifest, polled every 30 s | The same `manifest_invalid: 63 unclassified` failure as live | 95 MB flat for 4 min (8 polls) |

**Also established:**

- **Startup was fast.** It finished in 3 s (06:57:25 → :28), so the growth
  and almost all of the 4 min 19 s of CPU came from the idle loop.
- **The per-event code didn't change.** Between `a92a74e` and `8a7cdab`,
  the drain, `is_watchable` and `scheduler` code is the same. The circuit
  breaker moved to its own module, and #308 only passes `processed_log`.
- **What the live roots produce** (read-only watchdog probe, 60 s): 782
  events across 17 paths. Most are `opened` and `closed_no_write`. The two
  busiest paths are both **pre-activation Codex rollouts in active use**:
  `2026-10-10T23-16-55-…` and `2026-10-11T21-30-12-…`, at 213 and 283
  events/min.

**Conclusion so far:** the leak depends on the real environment and didn't
reproduce on synthetic data. Next would be a production-faithful run that
indexes nothing: real watch roots (read-only), a scratch data root, an
effectively infinite debounce (no spawns), no provider keys, and
`tracemalloc` snapshots, comparing `a92a74e` with `8a7cdab`. Because it
reads live source trees, it waits for Ryan's go.

**Burn note:** the two active pre-activation Codex sessions above would
each get a full legacy re-index once the watcher runs and they go quiet.

## Root cause found (Claude, 2026-10-12, round 2 under Ryan's go)

**Live-faithful run.** Runtime `8a7cdab`, the real watch roots observed
read-only, a scratch `HOME` and data root, a 1e9 s debounce, `env -i`, and
provider hosts pointing at `127.0.0.1:9`, with `tracemalloc` on. Result:
**+279 MB/min, 0 spawns.** The live `processed.json` was written once
during the run, at 07:47:22, by a separate `convmem index --file
~/.crush/crush.db` that the interactive Crush session started (Crush's own
Track A). That wasn't the harness.

**The top growing allocations at minute 3** all come from
`repository_knowledge_scope._cached_manifest` (line 759), through
`load_and_validate_manifest`:

| What | Growth by minute 3 |
|---|---|
| Parsed manifest JSON | +103 MiB |
| Raw manifest text (137 copies of 299 KiB) | +40 MiB |
| `git ls-files` path lists | +22 MiB |
| Classification rows | +19 MiB |

**Mechanism.**

- `decide_path()` runs on every filesystem event and calls
  `_cached_manifest()` for each configured manifest.
- A **valid** manifest is cached, and each call only re-checks its sha256
  and git HEAD.
- An **invalid** manifest is "cached" as the last exception. So every event
  triggers a full `load_and_validate_manifest`: it reads the 306 KB file,
  parses the JSON, runs `git ls-files` and the cleanliness check, and builds
  the classification table. That explains the CPU.
- The stored exception's traceback references the frame holding that data,
  and the frame references the exception. Only a full GC frees that cycle,
  so memory grows with the event rate.

**Why it began with the promotion.** `repository_knowledge_scope.py` is
unchanged between `a92a74e` and `8a7cdab`. `a92a74e` is itself "Classify new
tracked files so repository indexing runs again", so its manifest was valid.
On `8a7cdab` the manifest
(`config/repository-knowledge/openclaw-watch-scope-v1.json`, read from
`runtime-main`) has **63 unclassified tracked paths**, from files added since
then. Nothing in CI caught the drift.

**Hermetic confirmation** (synthetic rollout appended 3.6 times a second):

| Runtime | Manifest | RSS |
|---|---|---|
| `8a7cdab` | its own, invalid | **+84 MB/min** |
| `a92a74e` | its own, valid (startup sync OK) | **flat at 96 MB** |
| `8a7cdab` | none configured | flat at 95 MB (round 1) |

**Fix options. All are cross-arc: OpenClaw Watch Coverage owns repository
knowledge.**

1. **Fast unblock (Ryan config grant).** Remove
   `watch.repository_knowledge_manifests` from the live config, and keep a
   backup.
   - Repository-knowledge capture is already broken (`startup sync failed:
     manifest_invalid`), so nothing that works today is lost.
   - With no manifest, `decide_path` returns `outside_unconfigured` at once.
   - Stage 2 can then restart.
2. **Durable code fix (Cursor).**
   - `_cached_manifest` caches failures keyed by the manifest sha256 and
     git HEAD, the same way it caches success, so an invalid manifest
     re-validates only when one of those changes.
   - It stores the exception without its traceback, which breaks the
     cycle.
   - Test: many `decide_path` calls on an invalid manifest run exactly one
     validation, and traced memory stays flat.
3. **Data and CI guard.** Classify the 63 paths, and add a CI test that
   fails when a tracked path is unclassified, so the manifest can't drift
   silently again.

## Fast unblock and restart (Ryan grant 2026-10-12: option 1; options 2–3 to Cursor)

**Config.**
- **Backup:**
  `~/.config/convmem/backups/config.toml.pre-manifest-removal-2026-10-12`,
  mode 600 and byte-identical to the original.
- **Change:** removed only `watch.repository_knowledge_manifests` (three
  lines). Every other key parses identically, as verified with `tomllib`,
  and the file mode is unchanged.
- **Doctor** exits 0, with no status differences.

**Pre-check before the restart** (live-faithful and read-only, the same
harness as above, 13 live roots, 0 spawns, no tracing):

| Manifest | RSS |
|---|---|
| none configured | **99 → 100 MB over 4 min (+0.6 MB/min)** |
| the invalid one (control) | **+140.6 MB/min**, matching production's 144 |

**Restart.**
- The backup gate is still current (`b9a8977a…`).
- `systemctl --user enable --now convmem-watch.service` at **T0′ =
  08:31:18**.
- There's no startup-sync failure now that no manifest is configured.
- The monitor gained a stop condition: the watcher's main RSS above
  2048 MB.

**Durable fix:** `CURSOR-2026-10-12-repository-manifest-failure-cache-handoff.md`
on `docs/2026-10-12-repository-manifest-failure-cache-handoff`. It covers
failure caching, the 63 classifications, the 14 stale include hashes and a
CI guard.

| Check | Time | Paid (admitted / legacy est.) | Spawns | Watcher RSS | Stop |
|---|---|---|---|---|---|
| T0′ + 1 min | 08:32 | 0 / 0 | 0 | 101 MB | none |
| T0′ + 15 min | 08:46 | 0 / 0 | 0 | 101–102 MB, flat for all 15 samples; service peak 0.45 GiB; no OOM events | none (window clean) |
| T0′ + 2 h | 10:31 | 0 / 0 | 1 (inter-model `LATEST.md`, 0 chunks, rejected) | 108–109 MB, flat for all 60 samples; service peak 0.45 GiB; no OOM events | none (window clean) |

**T0′ + 2 h notes.**
- **#308 works live.** At 09:08 the watcher spawned one index of
  `docs/inter-model/LATEST.md`. The child skipped it ("inter-model
  provenance supersession required"), indexed 0 chunks and made no
  provider calls. The sidecar recorded it. The next 52 re-checks were
  `skip (inter_model_rejected)` with no spawn: before #308, each would
  have been a spawn.
- **Correction to the burn note above.** The two pre-activation Codex
  rollouts stopped being written at 08:15–08:16, before the restart.
  The watcher indexes only on file events and does no catch-up scan, so
  they were not re-indexed. They cost a full legacy re-index only if
  those sessions are resumed. The fix is to retire them rather than
  resume them.
- 3,710 `skip (unchanged)`, 0 refusals, 0 errors and 0 restarts.
