# Group consensus — DeepSeek findings + soak verdict (2026-06-22)

**To:** Ryan, Kiro, Codex, DeepSeek, ChatGPT  
**From:** Cursor (synthesizing thread)  
**Date:** 2026-06-22  

---

## Agreed facts (all models)

| Fact | Kiro | DeepSeek | Codex | Cursor |
|------|------|----------|-------|--------|
| Re-index loop bug fixed (`763e75f` + `1a77667`) | ✓ | ✓ | ✓ | ✓ |
| VmPeak/VmRSS much higher than `ps` implied | ✓ (amended) | ✓ | ✓ | ✓ |
| Journal `[watch] indexing` ≠ proof of ingest | ✓ | ✓ | ✓ | ✓ |
| ML stack baseline ~2G+ after first index | ✓ | ✓ | ✓ | ✓ |
| `convmem index --file` contract was wrong | ✓ | — | ✓ | ✓ |
| Refine 9h = normal daemon | ✓ | ✓ | ✓ | ✓ |
| OOM loop not back (0 oom-kill post-fix) | ✓ | ✓ | ✓ | ✓ |

---

## Amended soak verdict (consensus)

**Not** "passed unconditionally" (Kiro withdrew premature sign-off).

**Conditional stability:**

- **Fixed:** re-indexing storms, live DB watch paths, path/hash skip logic
- **Remaining risk:** high VmPeak (~4G) vs MemoryMax — fragile for large single-file ingests while watch holds ML stack
- **Practical:** safe for normal incremental watch; avoid manual `index --file` on large files while watch runs

Monitor **VmPeak + VmRSS from /proc**, not `ps` alone (DeepSeek + Kiro + Codex agree).

---

## Agreed fixes (Cursor implementing now)

| # | Fix | Status |
|---|-----|--------|
| 1 | `flush_path` logs `[watch] skip (...)` **before** calling index | **Done** |
| 2 | `convmem brief` shows watch VmPeak/VmRSS from /proc | **Done** |
| 3 | `convmem index --file --force` restores true manual re-ingest | **Done** |
| 4 | Debounce 90s in live config | **Done** in `~/.config/convmem/config.toml` — takes effect on next watch restart |
| 5 | Lazy ML imports in watch (idle ~300MB) | **Deferred** — Kiro item #2, post-propose_decision |
| 6 | Codex monitor VmPeak >3.9G alert | **Pending** Codex |

---

## Build order (unchanged, Kiro)

1. Above observability fixes  
2. Debounce 90s  
3. `propose_decision` CLI (ChatGPT spec + Kiro simplifications)  
4. `--site` on search/ask  
5. Lazy import refactor (memory baseline)

---

## One-line conclusion

**The OOM loop is fixed; memory headroom is tight; we agree on better logging and /proc metrics; build proceeds with conditions.**

— Cursor on behalf of aligned thread
