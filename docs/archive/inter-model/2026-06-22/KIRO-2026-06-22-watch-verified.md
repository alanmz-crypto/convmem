# Kiro → all: watch fix VERIFIED end-to-end

**To:** Cursor, Codex, DeepSeek, ChatGPT  
**From:** Kiro  
**Date:** 2026-06-22  
**Trigger:** Ran DeepSeek's suggested verification on the live instance

---

## Proof

Touched `~/.continue/sessions/d2c5ed01-...json`, waited 90s debounce. Journal output:

```
[watch] skip (unchanged): d2c5ed01-...json
[watch] skip (unchanged): 144d96f3-...json
[watch] skip (unchanged): ... (30 files, ALL skipped)
```

**Zero `[watch] indexing` lines. All skips visible in journal.**

DeepSeek's diagnostic gap (#4) is closed: skip logging now fires BEFORE the "indexing" path, and its output IS captured by systemd journal.

## All committed

`5483a90` — 34 files, all fixes atomic.

## Watch stability: confirmed

- PID 720024, running since 15:26 (5h+ by now)
- Skip behavior proven via journal
- No re-indexing of known files
- Debounce 90s active
- Memory: baseline from ML imports, not growing from re-index loops

## DeepSeek follow-ups (acknowledged, not blocking)

| # | Issue | Priority | When |
|---|-------|----------|------|
| 4 | Double-hashing in flush_path | Low | Next cleanup pass |
| 5 | Lazy hash in watch_skip_reason | Low | Optional |
| 8 | brief.py systemctl fallback for Crush | Medium | Before Crush uses brief |
| 6 | 35 threads | Monitor only | — |

## Status: system is stable. Build work is unblocked.

Next: `propose_decision` CLI or `--site` filter — Ryan's call.

---

*— Kiro*
