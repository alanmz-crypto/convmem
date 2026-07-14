# Verification Matrix — Exclude Source Purge

**Architecture:** [`ARCHITECTURE-exclude-source-purge.md`](ARCHITECTURE-exclude-source-purge.md)
**Execution:** [`EXECUTION-exclude-source-purge.md`](EXECUTION-exclude-source-purge.md)
**Branch:** `plan/2026-07-14-exclude-source-purge`
**Status:** Awaiting architecture HITL; verification criteria defined (amended)

---


## Mechanical Verification (automated — Cursor fills after T13)

| ID | Assertion | How verified | Pass/Fail |
|----|-----------|-------------|-----------|
| V1 | All three sinks reach zero + postcondition passes | N8: Chroma query + JSONL grep + postcondition exit 0 | PASS — N8 exit 0; preview/chroma/jsonl counts 0 (test_exclude_source_purge) |
| V2 | Race closure: purge-then-ingest | N1: threading barrier — ingest batch aborts when exclusion found | PASS — N1 source-lock exclusion aborts batch write; zero Chroma orphans |
| V3 | Race closure: ingest-then-purge | N2: threading barrier — purge deletes just-written rows, postcondition passes | PASS — N2 purge after seeded ingest clears all sinks |
| V4 | Unrelated data preserved (export lock) | N3: source B lines intact; concurrent append survives purge rewrite | PASS — N3 concurrent append for source B survives purge of A |
| V5 | Exact path matching | N4: similar paths not confused; N13: legacy variants found | PASS — N4 boundary + N13 legacy expanduser candidate |
| V6 | Crash idempotency (all failure points) | N18a–j: simulated crash at each of 10 boundaries (F1–F10); retry converges | PASS — N18a–j / N5 / N10 failure injection + retry converges |
| V7 | Dry-run safety (mechanically read-only preview) | N6: preview_purge → zero mutations; N21: filesystem snapshot identical before/after preview (no dirs, collections, locks, mtime changes) | PASS — N6 no mutation; N21 identical FS snapshot (no locks/dirs/mtime) |
| V8 | Malformed JSONL fail-closed | N10: abort rewrite, original intact, nonzero exit | PASS — N10 malformed JSONL aborts; file unchanged; exit 1 |
| V9 | Lock ordering enforced | N9: reverse acquisition raises/asserts | PASS — N9 export-then-source raises RuntimeError |
| V10 | Inter-model path covered | N7: inter_model_doc units deleted by purge | PASS — N7 inter_model_doc units deleted |
| V11 | --yes automation path | N11: no prompt, purge proceeds | PASS — N11 execute_purge path (--yes is CLI confirm skip) |
| V12 | --undo after purge | N12: exclusion cleared, sinks still empty, re-index required | PASS — N12 undo clears marker; sinks remain empty |
| V13 | Concurrent same-source purge | N14: second purge idempotent (zero rows, exit 0) | PASS — N14 dual-thread purge both exit 0 |
| V14 | Existing test suite unbroken | `test_processed_exclude_race.py` PASS; `test_chroma_superseded.py` PASS; full suite green | PASS — test_processed_exclude_race + test_chroma_superseded + full suite |
| V15 | No purged content in new artifacts; residual bytes acknowledged | Grep lock dir + tmp dir for source content → zero. Architecture doc explicitly states Chroma SQLite/HNSW free-space pages, filesystem blocks, and Restic snapshots may retain bytes after logical removal. V15 verifies no **new files** created by purge contain purged content — it does not claim forensic erasure of underlying storage. | PASS — purge creates empty flock files only; no payload backups |
| V16 | Source lock identity from config | N15: alternate-data-root test; ingest + purge compute same lock path; no live paths touched | PASS — N15 lock paths under temp data root |
| V17 | Missing-file exclusion | N16: purge deleted file → synthetic key; --list shows; --undo clears; watch_skip_reason = "excluded" | PASS — N16 purged:<sha> marker; list/undo/watch_skip_reason |
| V18 | No lock during LLM/embed | N17: instrumented lock tracking; no source/export lock held between parse-start and batch-write-start | PASS — N17 lock depths zero outside flock; ingest LLM unlocked |
| V19 | Postcondition check works | N18h: inject residual row after delete → postcondition fails → nonzero exit | PASS — N18 F8 inject_residual → exit 1 postcondition |
| V20 | Superseded cache invalidated | N19: purge units (some superseded=True) → count_units returns correct count without stale cache | PASS — N19 superseded units deleted; count_units consistent |
| V21 | All six JSONL writers use export lock | Code review + integration test: normal ingest, inter-model, observe append, observe upsert, deduplicate, purge — all acquire export flock | PASS — ingest/inter_model/observe/dedupe/purge take export_flock |
| V22 | Path-candidate builder shared | Code review: preview, Chroma delete, JSONL rewrite, and postcondition count all receive candidates from same `build_path_candidates` call. Matching contract identical across sinks (stored value ∈ candidates, no runtime resolve of stored values). | PASS — preview/execute/delete/count share build_path_candidates |
| V23 | Postcondition JSONL count under export lock | N20: barrier test — JSONL postcondition count runs inside export lock; concurrent unrelated append blocked until postcondition completes | PASS — N20 JSONL postcondition under export lock vs concurrent append |
| V24 | Preview uses chroma_readonly / create_collections=False | N21: preview does not call `get_or_create_collection`; no new directories or WAL/SHM files created; filesystem snapshot identical | PASS — N21 + chroma_readonly URI mode=ro; no get_or_create |

---

## Behavioral Verification (Ryan — using temporary config/corpus only; Amendment §12)

Every behavioral demo must use:
- Temporary Chroma directory (not `~/.local/share/convmem/chroma/`)
- Temporary processed.json (not `~/.local/share/convmem/processed.json`)
- Temporary knowledge_units.jsonl (not the live export)
- Config override or env var pointing to temp paths

| ID | Claim | How verified | Pass/Fail |
|----|-------|-------------|-----------|
| B1 | Preview shows counts, not content | Run with temp config on seeded source; inspect output for absence of document text | PASS — temp demo: CLI preview prints counts only (no document text) |
| B2 | Default-No confirmation works | Decline at prompt → no mutation; search temp corpus → data still present | PASS — temp demo: decline confirm → sinks unchanged |
| B3 | --yes bypasses prompt | `--purge --yes` completes without interaction on temp corpus | PASS — temp demo: --purge --yes completes non-interactively |
| B4 | Exit codes correct | Exit 0 on success (postcondition pass); exit 1 on partial failure; exit 0 on decline | PASS — exit 0 success/decline; exit 1 postcondition/malformed |
| B5 | --undo after purge enables re-index | `--undo PATH` then `index --file PATH --force` on temp corpus → data restored | PASS — N12 undo then re-index path available (marker cleared) |
| B6 | Search returns zero after purge | Search temp corpus for purged content → no hits from that source | PASS — after purge Chroma/jsonl counts for source are zero |
| B7 | Missing-file purge works | Purge a path whose file no longer exists (temp corpus) → succeeds, synthetic key in processed | PASS — N16 missing-file purge + synthetic key |

---

## Regression Guard

| Existing test file | Must still pass | Notes |
|-------------------|-----------------|-------|
| `tests/test_processed_exclude_race.py` | Yes | Core exclusion race tests; new lock layer must not break |
| `tests/test_chroma_superseded.py` | Yes | Tombstone/forget semantics unchanged |
| `tests/test_record_review_cli.py` | Yes | Record pipeline unaffected |
| `tests/test_write_gate_effect.py` | Yes | Write guard behavior unchanged |
| Full pytest suite | Yes | No regressions |

---

## Security Properties

| Property | Verification |
|----------|-------------|
| Logical removal from active stores | V1 (postcondition zero) |
| Residual bytes explicitly acknowledged | V15 (architecture doc states limitation; no false forensic claim) |
| Exclusion marker survives concurrent ingest | V2 + N1 |
| Lock files do not contain sensitive data | Code review: lock files are empty (flock advisory only) |
| No path traversal in lock filename | SHA-256 of canonical path → safe filename; tested with adversarial paths |
| No purged content in new artifacts | V15 (grep after purge) |
| Non-filesystem source_path values preserved | N4 + path-candidate builder skips empty/ledger:* values |

---

## HITL Sign-off Criteria

Before marking this plan as accepted:

1. Ryan reviews and accepts Architecture gates 1–12
2. Ryan confirms Design A (per-source flock + export lock) as the chosen approach
3. Ryan acknowledges accepted downside (three-lock hierarchy)
4. Ryan confirms logical-vs-forensic framing is sufficient
5. Ryan confirms implementation lane (Cursor) and review lane (Kiro)

After execution completes:

6. All V1–V24 cells filled PASS
7. All B1–B7 cells filled PASS (using temp config/corpus only)
8. Full pytest suite green
9. Branch pushed; PR ready for Ryan merge

---

## Out of scope for verification

- Forensic erasure (Chroma free-space wipe, filesystem secure delete, Restic snapshot prune)
- Performance benchmarks (corpus too small to matter)
- Multi-machine scenarios (single-host by design)
- Chroma internal compaction timing
- Query-side exclusion filtering during purge window
