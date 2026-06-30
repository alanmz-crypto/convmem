# Searchable CLI chats — sharpened handoff (Plan 7)

**Date:** 2026-06-29  
**Parent:** Plan 7 in [`BUILT-PLANS-2026-06-24-to-2026-06-29.md`](BUILT-PLANS-2026-06-24-to-2026-06-29.md) (revised `searchable_cli_chats_ffb9fcf6`)  
**Supersedes:** vague “exclude /snapshots/ and /cli/” wording in the original Cursor plan

---

## What’s right (keep as-is)

- **Core diagnosis:** Recent kiro-cli work lives in `~/.kiro/sessions/.../messages.jsonl`; legacy sqlite is historical only. The “Kiro IDE” label was wrong — document explicitly so future agents don’t hunt a product that doesn’t exist.
- **Phase ordering:** jsonl sessions = today’s gap; sqlite snapshot = April-and-earlier backfill. Separate phases prevent conflating two problems into one adapter.
- **“What we are not building”:** Keep explicit to prevent scope creep during implementation.

---

## Phase 1 — kiro-cli session jsonl (detect + adapter)

### On-disk topology (authoritative)

```
~/.kiro/sessions/
  <hash>/
    sess_<uuid>/
      messages.jsonl    ← WANT THIS
      session.json
    snapshots/          ← EXCLUDE (nested under hash)
  cli/
    *.history           ← EXCLUDE (top-level thin sidecars)
```

`cli/` is at the **top level** of `~/.kiro/sessions/`. `snapshots/` is **nested under** `<hash>/`. Do not rely on a single path-string exclusion.

### detect.py match condition (required spec)

Use `path.parts` — not brittle substring matching on full paths:

```python
# Pseudocode — implemented in adapters/kiro_session_jsonl.is_kiro_session_jsonl
path.name == "messages.jsonl"
and path.parent.name.startswith("sess_")   # cleanest discriminator
and "snapshots" not in path.parts
```

The **`sess_` parent-directory check** excludes `cli/*.history` sidecars without needing `cli` in every exclusion rule. `cli/` files are not named `messages.jsonl` under a `sess_*` parent anyway — the `sess_` check is the primary gate.

**Repo status:** ✅ Shipped — [`adapters/kiro_session_jsonl.py`](../adapters/kiro_session_jsonl.py), [`tests/test_kiro_session_jsonl.py`](../tests/test_kiro_session_jsonl.py), [`docs/KIRO-SESSION-ADAPTER.md`](../KIRO-SESSION-ADAPTER.md)

### Backfill gate (Ryan — count before bulk)

Do not run bulk `index --file` until Ryan sees the count. Some sessions contain sensitive client conversation context (corpus is sensitive generally).

```bash
find ~/.kiro/sessions -name messages.jsonl \
  -not -path '*/snapshots/*' -not -path '*/cli/*' | wc -l
```

Review count (was 49+ at plan time). Only then:

```bash
find ~/.kiro/sessions -name messages.jsonl \
  -not -path '*/snapshots/*' -not -path '*/cli/*' \
  -exec convmem index --file {} \;
```

**Repo status:** ✅ Documented in [`docs/KIRO-SESSION-ADAPTER.md`](../KIRO-SESSION-ADAPTER.md)

### Ryan sign-off — Phase 1 end-to-end

Single test that confirms the full pipeline:

```bash
convmem search "convmem doctor"
```

**PASS:** A hit with `source_path` under `~/.kiro/sessions/` (not only legacy sqlite).

---

## Phase 2 — kiro-cli sqlite snapshot (historical)

Legacy `~/.local/share/kiro-cli/data.sqlite3` only. Live DB stays on `is_live_watch_db` deny list. Use [`scripts/index-kiro-cli-snapshot.sh`](../scripts/index-kiro-cli-snapshot.sh).

**Repo status:** ✅ Script shipped; Ryan runs once for pre-April history.

---

## Phase 3 — Continue + Crush (verify only)

Lighter than it looks — one terminal session. Adapters exist; confirm watch + stats.

### Standard verify

```bash
convmem stats                    # continue + crush row counts sane
convmem search "<recent cn marker>"   # Continue spot-check
convmem search "crush terminal"       # Crush spot-check (or known marker)
```

### Crush live-DB risk check (add to verify pass)

The real risk is watch re-indexing a **live** `crush.db` that should be snapshot-only (OOM class). `is_live_watch_db` today blocks kiro-cli sqlite and Cursor `store.db` — **not** crush.db. Confirm config is not wiring a live Crush path into watch sources incorrectly:

```bash
convmem doctor
grep -r "crush.db" ~/.config/convmem/config.toml || true
```

If watch is touching a live Crush DB it shouldn’t, that surfaces **before** OOM. Crush is normally discovered via `**/.crush/crush.db` home glob in inventory — verify behavior matches intent ([`docs/F2c-CRUSH-ADAPTER.md`](../F2c-CRUSH-ADAPTER.md)).

**Repo status:** 🔄 Verify pass documented here; run Ryan/manual once.

---

## Phase 4 — Codex `history.jsonl` (user prompts only)

### Caveat (preserve in adapter, not just checklist)

`~/.codex/history.jsonl` stores **user prompts only** — no assistant text. Future `convmem ask` queries against Codex-sourced units get context with no assistant replies, which can skew synthesis.

### Required metadata (day one)

Tag units with `source_type: prompt_only` in the adapter module docstring **and** on each parsed message / indexed unit metadata. v1: metadata only; ask-path handling deferred — but the hook must exist from day one so ask can branch later.

**Repo status:** ✅ Shipped — [`adapters/codex_history_jsonl.py`](../adapters/codex_history_jsonl.py) (module docstring + `source_type` on messages), [`tests/test_codex_history_jsonl.py`](../tests/test_codex_history_jsonl.py), note in [`config.example.toml`](../config.example.toml) and [`docs/WORKSPACE-STANDARD.md`](../WORKSPACE-STANDARD.md)

---

## What we are not building

- Separate “Kiro IDE” product — same kiro-cli, two on-disk formats
- Watch on live sqlite (kiro-cli `data.sqlite3`, Cursor `store.db`) — OOM risk
- Indexing `cli/*.history` alone (too thin)
- ChatGPT local ingest
- `ask` special-casing for `prompt_only` in v1 (metadata only)

---

## Ryan deploy checklist (ordered)

1. Merge `~/.kiro/sessions` into live `~/.config/convmem/config.toml` (see [`config.example.toml`](../config.example.toml))
2. **Count** jsonl files (`find … | wc -l`) — approve before bulk
3. Run jsonl backfill (`find … -exec convmem index --file {} \;`)
4. Run `scripts/index-kiro-cli-snapshot.sh` once (historical sqlite)
5. `convmem doctor` → exit 0
6. Phase 3 verify (stats + Crush config grep above)
7. Spot-checks:
   - `convmem search "convmem doctor"` → path under `~/.kiro/sessions/` (**Phase 1 sign-off**)
   - `convmem search "<april kiro title>"` → sqlite snapshot
   - Continue / Crush markers as before
   - Optional: `convmem search "<known codex prompt>"` → `history.jsonl`

---

## Implementation status summary

| Item | Status |
|------|--------|
| `jsonl_kiro_session` adapter + `sess_` detect | ✅ |
| KIRO-SESSION-ADAPTER.md + topology diagram | ✅ |
| Backfill count gate | ✅ documented |
| kiro-cli snapshot script | ✅ |
| Codex adapter + `source_type: prompt_only` | ✅ |
| Phase 3 Crush verify grep | 📋 this handoff |
| Ryan backfill + sign-off search | ⏳ Ryan |
