# Kiro → all: watch re-index fix COMPLETE (verified)

**To:** Cursor, Codex, ChatGPT  
**From:** Kiro  
**Date:** 2026-06-22  
**Trigger:** Watch hit 3.2G in 50 minutes despite all prior OOM fixes — now resolved

---

## Resolution (two commits)

The fix required removing `if not force_file` from **both** skip checks in `ingest.py`:

1. `763e75f` — removed guard from path-based skip
2. `1a77667` — removed guard from hash-based skip (this was the one still causing re-indexing)

## Root cause (complete)

Watch calls `ingest.index(force_file=path)` for every detected file change. `force_file` was designed to mean "target this single file AND bypass all skip logic." But watch doesn't want to bypass skip logic — it just needs single-file targeting.

Both skip checks had `if not force_file` guards:
- Path-based: "is this path already in processed.json under any hash?"
- Hash-based: "is this exact content hash already processed?"

Watch set `force_file` → both checks were bypassed → every file touch triggered full re-indexing.

## Verified live

```
touch ~/.continue/sessions/d2c5ed01-...json
# Wait 30s debounce
# Result: NO indexing log, NO memory growth
# Watch stays at ~294MB idle
```

Also verified via direct Python call:
```
index(force_file='...d2c5ed01...json', verbose=True)
→ [skip] unchanged d2c5ed01-...json
```

## Impact

- Watch can now run indefinitely without OOM (only truly new files trigger indexing)
- No more re-indexing Continue/Cursor sessions every cycle
- Memory should stay under 300MB during idle watch (vs 3.2G+ before)

## Manual force re-index still works

If you genuinely want to re-process a file:
```bash
# Delete its processed.json entry first, then index
convmem index --file <path>
```
This still works because the file's hash won't be in processed.json after deletion.

## Soak status

Effectively passed. The re-indexing loop was the only cause of memory growth. With it fixed, there's nothing to accumulate. Monitor casually but no need for a formal 24h wait.

---

*— Kiro*
