# Agreed best practices — Kiro sign-off + conversation conclusion

**Status:** Signed by Kiro (`KIRO-2026-06-22-memory-signoff.md`)  
**Date:** 2026-06-22  
**Audience:** Ryan, Cursor, Codex, Kiro, Sonnet, ChatGPT  

This is the **single conclusion doc** after reading the full inter-model thread on memory, search, brief, and parallel edits.

---

## 1. Three failure classes — never conflate

| Class | Symptom | Fix layer |
|-------|---------|-----------|
| **Watch OOM** | Kernel oom-kill, KDE "memory shortage avoided", 6G+ RSS | Live DB skip, per-chunk ingest, cgroup limits |
| **Chroma search lock** | Intermittent `readonly database` on `convmem search` | Short-lived writers + `open_chroma_for_read()` retry |
| **GPU VRAM** | nvidia-smi / ComfyUI | **Unrelated** to convmem watch |

Codex clarification + Kiro diagnosis + today's journal all agree on this split.

---

## 2. Watch / memory (Kiro approved)

### Live DBs — never watch-index

| Path | Rule |
|------|------|
| `~/.local/share/kiro-cli/data.sqlite3` | `convmem exclude` + `is_live_watch_db()` |
| `~/.config/cursor/chats/**/store.db` | `is_live_watch_db()` — manual `convmem index --file` only |
| `~/.local/share/convmem/imports/webui.db` | `is_live_watch_db()` |

### Ingest memory pattern (Kiro + Cursor)

1. **LLM work first** (summarize, distill, embed) — no Chroma open  
2. **`with ChromaStore()` per chunk** — write summary + units, then close  
3. **Atomic `save_processed()`** — temp file + rename  

### Systemd limits (Kiro approved)

```
MemoryMax=4G
MemoryHigh=3G
MemorySwapMax=0
OOMPolicy=stop
RestartSec=300
StartLimitBurst=3
```

### Watch timing

- **Debounce: 90s** (reduce indexing storms while Cursor/Continue active)  
- **Pass criteria:** 24h journal with **no `oom-kill`**, memory peak **under 3G**  
- **P0-complete withdrawn** until that soak passes  

### Re-enable (Ryan only, when ready)

```bash
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch
journalctl --user -u convmem-watch -f
# After 30 min:
systemctl --user show convmem-watch | grep Memory
```

**Watch is inactive now.** Kiro signed off the *fixes*, not re-enable yet.

---

## 3. Chroma access (Kiro + Cursor)

See `docs/CHROMA-ACCESS-PATTERN.md`.

| Operation | Mechanism |
|-----------|-----------|
| `brief`, `stats` | `chroma_readonly.py` — no PersistentClient |
| `search`, `ask`, MCP | `open_chroma_for_read()` + retry + close |
| ingest, refine | Short-lived `ChromaStore` writers only |

**Deferred:** Chroma HTTP server — only if contention/OOM persists at scale.

---

## 4. Multi-agent coordination (Kiro habits)

1. **Session start:** `convmem brief` (or read `~/.local/share/convmem/brief.md`)  
2. **Cross-model messages:** `docs/inter-model/<MODEL>-<date>-<topic>.md`  
3. **Deep questions:** `convmem ask` — not chat memory  
4. **ChatGPT:** paste `convmem brief --stdout-only` only  
5. **Decisions:** ingest to corpus or `DECISION PROPOSED` block — human/Kiro signs  

**Kiro role:** reviewer/signer — not implementer.  
**Cursor role:** implementer on dev machine.  
**Codex:** shell + readonly reporting path.  

---

## 5. What's done vs what's next

### Done (Kiro signed off)

- [x] `store.db` live-watch skip  
- [x] Per-chunk Chroma open/close  
- [x] `MemorySwapMax=0`, debounce 90s  
- [x] `convmem brief` + `chroma_readonly`  
- [x] Search retry + writer close  
- [x] Kiro sqlite exclude  

### Not done — Kiro gates

- [ ] **24h clean watch journal** before declaring stable  
- [ ] **Git commit** of all uncommitted work (Kiro recommends now)  
- [ ] `propose_decision` workflow — after brief adoption proven  
- [ ] Handoff doc consolidation → `STATUS.md` + archive  

---

## 6. One-line conclusion (Kiro + thread)

**Memory shortage = watch OOM from live DBs and indexing storms — not GPU, not search locks. Fixes are approved; watch stays off until 24h clean journal; then Ryan re-enables and Kiro signs stability.**

---

*Point new models here instead of re-reading the full inter-model chain.*
