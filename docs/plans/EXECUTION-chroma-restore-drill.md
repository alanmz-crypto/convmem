# Execution Plan — Chroma Restore Drill

```
Planning Status

Phase:        Execute
Characters:   Cursor
Lanes:        Cursor → Ryan (verify report) → optional Kiro
Authority:    Architecture gates 1–6 accepted 2026-07-12; Ryan authorized execution ("do what is designed")
```

**Architecture SSoT:** [`ARCHITECTURE-chroma-restore-drill.md`](ARCHITECTURE-chroma-restore-drill.md)  
**Branch:** `plan/2026-07-12-chroma-restore-drill`  
**Worktree:** `~/.local/share/convmem/worktrees/plan-2026-07-12-chroma-restore-drill`

---

## Gate decisions (accepted defaults)

| # | Choice |
|---|--------|
| 1 | Run dir: `mktemp -d` under `~/.local/share/convmem/restore-drill/runs/`; reports under `…/restore-drill/reports/` |
| 2 | Optional semantic: reuse `scripts/eval-retrieval.py` after adding `--chroma-dir` |
| 3 | Cadence: one-time this pass (no doctor freshness check) |
| 4 | Intentional failure: nonexistent snapshot ID |
| 5 | Counts: `knowledge_units` count > 0; other collections exist only |
| 6 | `restic check` deferred |

---

## Deliverables (this branch)

1. **Verification-only open** — `ChromaStore(..., create_collections=False)` + `open_chroma_for_verify()` using `get_collection` only (never `get_or_create_collection` on the drill path).
2. **`--chroma-dir` injection** — `query_units(..., chroma_dir=)` + `scripts/eval-retrieval.py --chroma-dir` for optional semantic checks against a restored root.
3. **Pinned fixture** — `tests/fixtures/chroma_restore_drill.json` (ledger id + chroma id + document sha256 + `created_at` for eligibility gate).
4. **Drill runner** — `scripts/chroma_restore_drill.py`: list/select → init report → restore → discover root → fingerprint → verify (missing collection, structural, pinned content, vector round-trip) → optional semantic → fingerprint assert → finalize report → trap cleanup of run dir only.
5. **Intentional failure path** — `--intentional-missing-snapshot` (or explicit bad `--snapshot`) exits nonzero, still writes a report.
6. **Hermetic tests** — verify-mode open, discover-root, fingerprint stability, fixture gate, missing-snapshot report path (no live Restic required for unit tests).
7. **One happy-path run + one missing-snapshot run** against a real tagged snapshot; reports under the reports dir.

---

## Implementation note (fingerprint)

PersistentClient read-opens rewrite `chroma.sqlite3` bookkeeping and HNSW segment bytes. The drill’s asserted fingerprint is **logical** (collection names + embedding ids via readonly SQLite), which stays stable across verify opens and still fails if units/collections are added or removed. Vector round-trip covers index queryability.

## Out of scope this PR

- Changing Restic gate / snapshot cadence / write-gate
- `restic check` integrity preflight (gate 6)
- Manifest-at-snapshot recording (gate 5 future)
- Bad-credentials failure exercise
- Recurring doctor check for drill freshness
- Stopping or mutating live Chroma

---

## Task order

| ID | Work | Done when |
|----|------|-----------|
| T1 | EXECUTION + VERIFY checklist | this file + `VERIFY-chroma-restore-drill.md` |
| T2 | `chroma_store` verify-only open + unit get w/ embedding | tests PASS |
| T3 | `query_units` / `eval-retrieval --chroma-dir` | tests PASS |
| T4 | Fixture + drill script | `--help` works; hermetic tests PASS |
| T5 | Happy-path drill on explicit snapshot ID | report PASS; run dir gone |
| T6 | Missing-snapshot intentional failure | nonzero exit; report documents failure |
| T7 | Commit + push | remote branch has tip |

---

## Sign-off

**Mechanical:** Cursor fills VERIFY after T5–T6.  
**Ryan:** read happy-path report; merge when satisfied.  
**Kiro (optional):** review VERIFY + report; no merge authority.
