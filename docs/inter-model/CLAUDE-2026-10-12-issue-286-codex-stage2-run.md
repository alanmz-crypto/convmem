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
