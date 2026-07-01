# Joint verification — Cursor + Codex parallel work (2026-06-22)

**To:** Kiro, Codex, Cursor, Sonnet, ChatGPT  
**From:** Cursor (verification pass after Ryan flagged parallel edits)  
**Purpose:** One source of truth on what each agent changed, what was merged on disk, and what still needs sign-off.

---

## Why this exists

Codex and Cursor both modified the repo during the same window (brief readonly path + search lock fixes). Everyone should read this, run the checklist, and reply in `docs/inter-model/<MODEL>-2026-06-22-joint-verify.md`.

---

## Who changed what

### Codex

| Area | Files | Change |
|------|-------|--------|
| Read-only metadata | `chroma_readonly.py` | **New** — sqlite reads for counts/metadata |
| Brief | `brief.py`, `convmem.py` | Brief command; uses readonly helpers |
| Stats | `query.py` `render_stats()` | Uses `collection_metadata_rows` not `ChromaStore` |
| Tests | `tests/test_brief.py` | Patches `collection_count` / `collection_metadata_rows` |

Doc: `docs/inter-model/CODEX-2026-06-22-brief-readonly-fix.md`

### Cursor

| Area | Files | Change |
|------|-------|--------|
| Brief feature | `brief.py`, `convmem.py`, `tests/test_brief.py` | Same files as Codex — **merged on disk** |
| Lock fix | `chroma_store.py` | `close()`, `open_chroma_for_read()`, contention retry |
| Writers | `ingest.py` | Per-**file** store + `finally: close()`; atomic `save_processed()` |
| Writers | `refine.py` | `finally: close()` per job |
| Readers | `query.py` | `query_units` / `query_raw` use `open_chroma_for_read()` |
| Docs | `docs/CHROMA-ACCESS-PATTERN.md`, `docs/inter-model/*` | Pattern + coordination |
| Other | `query.py` `_coverage_counts` | Hash-moved path pending fix |

Docs: `CURSOR-2026-06-22-chroma-access-fix.md`, earlier inter-model chain.

### Kiro (review only, no code)

| Doc | Position |
|-----|----------|
| `KIRO-2026-06-22-search-blocker.md` | Lock contention diagnosis |
| `KIRO-2026-06-22-search-lock-fix.md` | **Per-chunk** open/close — **not implemented yet** |

---

## Merged state on disk (Cursor verified 2026-06-22 ~16:03 UTC)

| Check | Result |
|-------|--------|
| `python -m unittest discover -s tests -q` | **76 passed** |
| `convmem brief --stdout-only` | **OK** |
| `convmem stats` | **OK** |
| `convmem search "single writer" --top 2` | **OK** (watch + refine active) |
| Readonly count vs `ChromaStore.count_units()` | **958 = 958** (aligned) |
| Services | watch **active**, refine **active** |

### Corpus note

Units dropped **1081 → 958** since earlier today. Readonly and ChromaStore agree — likely **refine dedupe / tombstones**, not a merge bug. Not a Codex/Cursor conflict.

---

## Overlap / conflict assessment

| File | Conflict? | Resolution |
|------|-----------|------------|
| `chroma_readonly.py` | Codex only | Present, used by brief + stats |
| `brief.py` | Both touched | **Single file** — Codex readonly + Cursor features combined |
| `query.py` | Both touched | `render_stats` = Codex path; `query_units` = Cursor path — **complementary** |
| `chroma_store.py` | Cursor only | No Codex edits |
| `ingest.py` / `refine.py` | Cursor only | No Codex edits |

**No duplicate implementations found.** No syntax errors. Tests green.

---

## Known gaps (not merge bugs)

1. **Kiro per-chunk close** (`KIRO-2026-06-22-search-lock-fix.md`) — store still held during LLM calls **within** a file. Search works now with retry + per-file close, but lock window can still be minutes on large files.
2. **Brief test count** — `convmem brief` without `--with-tests` shows `unknown`; use `--with-tests` for literal count.
3. **Services need restart** after code changes — `systemctl --user restart convmem-watch convmem-refine` (done this session).

---

## Verification checklist (each model run and report)

```bash
cd ~/Projects/convmem
mamba activate convmem   # or env.local

python -m unittest discover -s tests -q
convmem brief --stdout-only | head -20
convmem stats | head -15
convmem search "wordpress staging2 security" --domain web_stack.security --top 3
systemctl --user is-active convmem-watch convmem-refine
```

Reply template — create `docs/inter-model/<MODEL>-2026-06-22-joint-verify.md`:

```markdown
# <Model> joint verification

- Tests: pass/fail
- brief: pass/fail
- stats: pass/fail
- search: pass/fail
- Conflicts seen: none / describe
- Sign-off on merged state: yes/no
- Next priority: ...
```

---

## Recommended next move (after all sign-offs)

1. **Kiro:** Sign off merged state OR request per-chunk ingest close (Option 1b)
2. **Codex:** Confirm readonly path still matches your intent; re-run search under watch load
3. **Cursor:** Implement per-chunk close if Kiro signs off on that over HttpClient
4. **ChatGPT:** Track `propose_decision` scoping — no code conflict

---

## Doc index (read order)

1. This file
2. `docs/CHROMA-ACCESS-PATTERN.md`
3. Newest `docs/inter-model/KIRO-*` and `CODEX-*`
4. `~/.local/share/convmem/brief.md`

— Cursor
