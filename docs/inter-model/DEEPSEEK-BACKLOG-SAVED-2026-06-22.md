# DeepSeek backlog — saved for later (2026-06-22)

**Status:** Deferred per Ryan — revisit after `propose_decision` / current build lane  
**Sources:**  
- `DEEPSEEK-2026-06-22-third-pass.md` (7 open ops items)  
- `DEEPSEEK-2026-06-22-final-needles.md` (4 needles + confirmed non-problems)

**Snapshot when saved:** Watch PID 729522, commit `e8170ab`, 84 tests, corpus 957/258, skip logging verified.

---

## Already fixed (do not reopen)

| Item | Commit / evidence |
|------|-------------------|
| Re-index loop (path + hash skip) | `763e75f`, `1a77667` |
| Stale process missing hash fix | Restart 15:26 / 15:35 |
| Uncommitted agreed fixes | `5483a90`, `e8170ab` |
| Double-hash in flush_path | `e8170ab` |
| Journal skip gap | `[watch] skip (unchanged)` in journal |
| brief systemctl-only | pgrep fallback in `e8170ab` |
| Debounce 90s | config + unit restart |
| Cgroup limits in unit file | `MemoryMax=4G`, `MemoryHigh=3G`, `MemorySwapMax=0` in `convmem-watch.service` |

---

## Third pass — open (ops / cleanup)

| # | Item | Severity | Owner | When |
|---|------|----------|-------|------|
| T1 | **processed.json orphans** — 5× `d7afdd30…jsonl`, 2× kiro sqlite; no GC of old hashes per path | DATA | Cursor | Post-`propose_decision` |
| T2 | **Two MCP servers** — PIDs 22851 (09:48) + 702321 (15:04); kill stale | SERVICE | Codex/Ryan | ~30s when resumed |
| T3 | **Refine 11h+ unverified** — cycling vs stuck? Chroma write lock? | RESOURCE | Codex | Next check |
| T4 | **8 non-OOM watch restarts** — document why (deploy races, manual restarts) | STABILITY | Cursor | Inter-model note |
| T5 | ~~Cgroup fragility~~ | OPS | — | **Closed:** limits in unit file |
| T6 | **Idle RSS ~770MB–1.9G** after first scan loads ML stack; not 64MB pre-scan | MONITORING | All | Track VmPeak/VmRSS in brief |
| T7 | **35 threads invariant** — watchdog pool; risk if watch roots explode | ARCH | Cursor | v1.1 |

---

## Final pass — needles (design / latent / noise)

| # | Item | Severity | Notes |
|---|------|----------|-------|
| N1 | **path_known → "unchanged" without hash** | BY DESIGN | Active Cursor sessions never re-index on append; users need `convmem index --file --force`. Consider throttled hash-change reindex (e.g. 1/h/file). |
| N2 | **Main watch loop no exception handling** | LATENT | One bad `index()` crash kills watch. Wrap `flush_path` in try/except, log, forget path, continue. |
| N3 | **30+ files touched every 2–5 min** | NOISE | Cursor `store.db-shm` + chat store activity; skips are O(1); journal noise only. |
| N4 | **Kiro DB dual processed entries** | KNOWN | 127 units frozen snapshot + exclusion marker; 1826+ msgs not in corpus by design. |

---

## Confirmed NOT problems (DeepSeek final pass)

- Stale `.pyc` shadowing code  
- Chroma corruption from re-ingestion burst  
- `--force` flag logic (parser-dependent)  
- Watch+refine deadlock (refine ~5 FDs, WAL)  
- New Cursor session subdirs need watch restart (by design)  
- 35 threads = not a leak  

---

## Recommended resume order (when Ryan returns)

1. Kill stale MCP **22851** (T2)  
2. Wrap `flush_path` exception handling (N2) — small, soak-safe  
3. Document restart timeline (T4)  
4. Verify refine cycling (T3)  
5. `processed.json` GC for same-path old hashes (T1)  
6. Design throttled reindex for active sessions (N1) — needs spec  
7. Lazy ML imports (Kiro #2, from earlier consensus) — larger refactor  

---

## Build lane (unblocked per DeepSeek)

Proceed: **`propose_decision` CLI**, merge decision specs, **`--site`** on search/ask.

---

*Saved by Cursor on Ryan's request — "we'll come back to this."*
