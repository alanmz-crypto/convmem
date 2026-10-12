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
