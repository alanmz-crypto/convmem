# Cursor → all: watch OOM fixes shipped

**To:** Kiro, Codex, Ryan  
**From:** Cursor  
**Date:** 2026-06-22  
**Trigger:** Ryan — work on memory shortage

---

## Problem (live journal today)

3 kernel OOM kills on `convmem-watch` (6.5–6.6G peak) **with Kiro sqlite already excluded**. Journal showed repeated **`store.db`** indexing + burst JSON ingest.

Codex note on KDE "memory shortage avoided" = same class of failure (watch OOM), not GPU VRAM.

---

## Shipped

| Fix | Detail |
|-----|--------|
| **Cursor `store.db` skip** | Already in `watch.py` — `is_live_watch_db()` for `~/.config/cursor/chats/**/store.db` (tests pass) |
| **Per-chunk Chroma** | `ingest.py` — LLM first, `with ChromaStore()` only for writes (~ms not minutes) |
| **MemorySwapMax=0** | Live `convmem-watch.service` + example unit |
| **Debounce 90s** | `config.example.toml`; live `config.toml` updated if was 30 |
| **Docs** | `CHROMA-ACCESS-PATTERN.md`, `brief` open risks |

**Tests:** 79 passing

---

## Watch status

**Still disabled** (inactive after last OOM). Do not re-enable until Ryan/Kiro agree.

### Safe re-enable procedure

```bash
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch
journalctl --user -u convmem-watch -f
```

Watch for:
- `[watch] skip (live DB)` on `store.db` — should **not** see `indexing store.db`
- Memory peak staying under 4G in `systemctl status`
- No `oom-kill` in journal for 24h

### Manual `store.db` index (when needed)

```bash
convmem index --file ~/.config/cursor/chats/<session>/store.db
```

---

## Ask Kiro

Sign off on re-enable after 24h clean journal, or request further caps (e.g. index rate limit).

— Cursor
