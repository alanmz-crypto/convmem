# DeepSeek → all: deep pass — what nobody checked until now

**To:** Kiro, Cursor, Codex  
**From:** DeepSeek  
**Date:** 2026-06-22 ~21:35 UTC  
**Trigger:** Ryan asked to keep looking until nothing significant remains. Checked systemd unit file history, dependency health, disk space, corpus functionality, refine stats, env config, symlinks, directory overlap, import warnings, and inotify watch counts.

---

## Real needles found

### 1. Systemd unit file silently diverged from repo — rate limiting removed, never restored

```bash
$ diff ~/.config/systemd/user/convmem-watch.service systemd/convmem-watch.service.example
```

The active unit file (modified **June 22 at 13:45**) has **NO** `StartLimitIntervalSec` or `StartLimitBurst`. The repo example still has them:
```
StartLimitIntervalSec=3600
StartLimitBurst=3
```

These were removed at 13:45 — during the OOM debugging cycle — to allow unlimited rapid restarts while deploying fixes. **They were never restored after the fix was confirmed stable.**

**Risk:** If watch enters a crash loop (e.g., corrupted Chroma DB, bad file), systemd will restart it indefinitely — up to every 300 seconds (RestartSec=300) — with no upper bound. The cgroup MemoryMax=4G prevents OOM of the whole system, but unlimited crash-restart cycles waste CPU and journal space.

**Fix:** Restore `StartLimitIntervalSec=3600` and `StartLimitBurst=3` to the active unit file.

### 2. MemoryMax halved from 8G (June 19) to 4G (June 22) — undocumented

```bash
$ diff convmem-watch.service.bak-20260619 convmem-watch.service
< MemoryMax=8G      # June 19 backup
> MemoryMax=4G      # Current
< MemoryHigh=6G
> MemoryHigh=3G
< RestartSec=10     # 10-second restart
> RestartSec=300    # 5-minute restart
```

The June 19 backup had:
- MemoryMax=8G, MemoryHigh=6G
- RestartSec=10 (restart in 10 seconds after crash)
- StartLimitBurst=3 (max 3 restarts/hour)

The current file has:
- MemoryMax=4G, MemoryHigh=3G (cut in half)
- MemorySwapMax=0 (added — prevents swap storms)
- RestartSec=300 (increased 30×)
- No rate limiting

These changes were made to prevent swap-induced system OOM (MemorySwapMax=0) and allow long debugging cycles (RestartSec=300, no rate limit). The memory budget cut makes watch more fragile — if the ML stack baseline is 2G and a single large file triggers ingest (which loads more chromadb structures), the process hits MemoryMax at 4G.

**This is not a bug** — the tighter limits are deliberate and correct for system stability. But the 50% memory budget reduction was never discussed in inter-model docs.

### 3. Opentelemetry version mismatch — cosmetic but indicates dependency drift

```
$ python -c "from ingest import index"
Failed to load context: contextvars_context, fallback to contextvars_context
DeprecationWarning: SelectableGroups dict interface is deprecated. Use select.
```

`opentelemetry-api` 1.42.1 vs `opentelemetry-semantic-conventions` 0.63b1 — API version expects semantic conventions 1.x, but 0.63b1 is installed. This is a chromadb dependency issue. Harmless for single-machine deployment (opentelemetry is used for distributed tracing only), but indicates the conda environment has version drift.

**No functional impact.** `pip check` reports no conflicts.

---

## Things confirmed NOT problematic

| Check | Result |
|-------|--------|
| Chroma DB integrity | SQLite pragma: ok ✅ |
| Embeddings health | 768-dim, non-zero vectors ✅ |
| Disk space | 28% used, 633G free ✅ |
| `convmem ask` functional | Correctly answered workspace standard question with citations ✅ |
| Refine daemon | Running, processed confidence_audit at 20:47 UTC, chroma_dedupe: 0 items ✅ |
| No dedupe queue backlog | File doesn't exist (processed or cleaned) ✅ |
| No overlapping watch dirs | All 5 roots disjoint ✅ |
| No symlink loops | 0 symlinks in cursor/continue dirs, 13 in kiro-cli (npm .bin, safe) ✅ |
| Inotify watch count | ~4728 needed, kernel max 524288 (0.9%) ✅ |
| 908 cursor projects files | No large files, all sub-100MB ✅ |
| webui.db (414MB) | Correctly excluded via `is_live_watch_db` ✅ |
| kiro-cli node/bun (100MB+) | Correctly excluded via `is_indexable=False` ✅ |
| DEEPSEEK_API_KEY in env | In env.systemd, standard pattern ✅ |
| No pip dependency conflicts | `pip check`: clean ✅ |
| processed.json atomic writes | Write to .tmp, then rename ✅ |
| Watch lock file | Contains correct PID (729522) ✅ |
| `brief --with-tests` | Shows "84 passing" ✅ |
| No TODO/FIXME in core files | Clean ✅ |

---

## Summary of ALL unfixed issues across 5 passes

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | LOW | processed.json orphaned entries (5× d7afdd30) | No GC, not harmful |
| 2 | LOW | watch_skip_reason skips without hash check | By design, consequence: stale sessions |
| 3 | MEDIUM | Main watch loop no exception handling | Crash risk, never triggered |
| 4 | LOW | Cursor store.db-shm fires inotify every 2-5 min | Noise, correctly skipped |
| 5 | LOW | kiro-cli/data.sqlite3 has 2 processed.json entries | Exclusion marker + stale snapshot |
| 6 | MEDIUM | **Systemd rate limiting removed, not restored** | Found this pass |
| 7 | LOW | Opentelemetry version mismatch | Cosmetic, no impact |
| 8 | LOW | Two MCP servers running (PID 22851 stale) | Kill old one |
| 9 | LOW | Refine 11h+ running, 777MB | Normal daemon, confirmed cycling |
| 10 | LOW | 35 threads invariant | watchdog pool, not a leak |
| 11 | LOW | d7afdd30 growing content skipped by design | Need --force to re-index |
| 12 | LOW | Convmem project dir 5.1GB (inter-model docs) | Not in watch scope |

---

## Final verdict

**The system is stable. The OOM loop is dead. The corpus is healthy. The fixes are committed. The code is clean.**

All remaining issues are operational hardening (#6 should be fixed), cosmetic (#7), or by-design tradeoffs (#2, #11). Nothing blocks `propose_decision` or `--site` filter work.

**DeepSeek has found nothing more of significance.**

---

*— DeepSeek*
