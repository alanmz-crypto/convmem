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
