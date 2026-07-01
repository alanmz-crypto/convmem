# Cursor → all: memory shortage — notes read + live status

**To:** Kiro, Codex, Ryan  
**From:** Cursor  
**Date:** 2026-06-22  
**Trigger:** Ryan asked to read notes on memory shortage

---

## Notes read

| Source | Claim |
|--------|--------|
| `CODEX-2026-06-22-memory-shortage-clarification.md` | KDE "memory shortage avoided" = **watch OOM loop** from live **Kiro sqlite**, not GPU VRAM or Chroma search locks |
| Handoffs / `watch.py` | Guards: exclude Kiro DB, `is_live_watch_db()`, deterministic IDs, upsert, `MemoryMax=4G` |
| `KIRO-2026-06-22-p0-complete.md` | Declared all P0 closed including watch re-enable |

## Implementation update

- **Codex landed `store.db` skip** in `watch.py` and added tests for Cursor Composer chat DBs on 2026-06-22.
- This closes the remaining live-watch OOM class called out in the notes below.

## Live machine contradicts "stable"

**Today (Jun 22) journal — 3 kernel OOM kills on `convmem-watch`:**

| Time | Peak RAM | Swap peak | Result |
|------|----------|-----------|--------|
| 11:50 | **6.5G** | 4.4G | oom-kill |
| 12:35 | **6.6G** | 4.3G | oom-kill |
| 13:26 | **6.6G** | 4.4G | oom-kill |

- `MemoryMax=4G` is set in unit file but peaks exceeded 4G → cgroup did not cap before kernel OOM
- **Kiro exclude is applied** — OOM is **not** the old Kiro-sqlite-only path
- Pre-OOM log pattern: heavy **`store.db`** re-indexing + burst Continue/Cursor JSON + duplicate jsonl (`dfc67b08` / `992d7a06`)
- **Watch now: inactive** (stopped after OOM cycle)

Codex clarification is **historically correct** but **incomplete for today**: memory shortage is still an active watch problem.

---

## Separate issues (do not conflate)

| Issue | Symptom | Fix class |
|-------|---------|-----------|
| **Watch OOM** | Kernel kills, KDE memory warnings, 6G+ RSS | Skip live DBs, rate-limit watch, per-chunk memory release |
| **Chroma search lock** | Intermittent `readonly database` on search | Per-chunk/`close()` on writers, `open_chroma_for_read` retry |
| **GPU VRAM** | ComfyUI / nvidia-smi | Unrelated to convmem watch |

---

## Likely current OOM drivers (Kiro exclude already on)

1. **`store.db` watch loop** — Cursor Composer DBs change while IDE runs; each touch → full ingest + distill + embed (journal: many `indexing store.db` lines)
2. **Indexing storm** — dozens of files per hour while Cursor/Continue active
3. **MemoryMax ineffective** — need `OOMPolicy=stop` + lower cap or `MemorySwapMax=0` to fail fast inside cgroup
4. **Chroma + LLM peak** — per-file store still holds client through all chunks (Kiro per-chunk fix not done)

---

## Recommended work (priority)

### P0 — stop the bleeding
- [ ] **Keep watch disabled** until below shipped and the journal is clean
- [x] **Skip `store.db` in watch** — treat like live DB (`is_live_watch_db` or path `**/store.db` under `~/.config/cursor/chats`)
- [ ] **Verify `OOMPolicy=stop`** in live `~/.config/systemd/user/convmem-watch.service`

### P1 — reduce memory per index
- [ ] **Per-chunk Chroma open/close** during ingest (Kiro `search-lock-fix` — also lowers peak RSS)
- [ ] **Watch debounce** increase (e.g. 30s → 120s) while Cursor active
- [ ] **StartLimitBurst** — already 3/hour; consider longer `RestartSec` after oom-kill

### P2 — manual paths
- [ ] `store.db` → manual `convmem index --file` on schedule, not watch
- [ ] Document in `CHROMA-ACCESS-PATTERN.md` or brief Open Risks

---

## Ask Kiro

Sign-off on **`store.db` = live-watch skip** (same class as Kiro sqlite). P0-complete should be **withdrawn or amended** until 24h clean journal with watch on.

---

## Ask Ryan

Confirm: disable watch until `store.db` skip lands? I can implement `is_live_watch_db` for `store.db` + tests in next pass.

— Cursor
