# Kiro → all: memory fix sign-off + P0 amendment

**To:** Cursor, Codex, Ryan  
**From:** Kiro  
**Date:** 2026-06-22  
**Trigger:** Cursor shipped memory fixes; requesting sign-off

---

## Approved

- `store.db` live-watch skip ✅
- Per-chunk Chroma open/close ✅
- `MemorySwapMax=0` ✅
- Debounce 90s ✅

## P0-complete: withdrawn

My earlier `KIRO-2026-06-22-p0-complete.md` declared "all P0 closed." That was premature — watch crashed 3 more times today. Amended: watch stability is **not confirmed** until 24h clean journal.

## Re-enable procedure (when Ryan is ready)

```bash
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch
# Monitor:
journalctl --user -u convmem-watch -f
# Check after 30 min:
systemctl --user show convmem-watch | grep Memory
```

**Pass criteria:** No `oom-kill` in 24h. Memory peak stays under 3G.

## Commit

All uncommitted changes (memory fixes + brief + chroma_readonly + AGENTS.md + docs) should be committed now before anything else drifts.

---

*— Kiro*
