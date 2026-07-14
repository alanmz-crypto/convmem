# Verification Matrix — Exclude Source Purge

**Architecture:** [`ARCHITECTURE-exclude-source-purge.md`](ARCHITECTURE-exclude-source-purge.md)
**Execution:** [`EXECUTION-exclude-source-purge.md`](EXECUTION-exclude-source-purge.md)
**Branch:** `plan/2026-07-14-exclude-source-purge`
**Status:** Awaiting architecture HITL; verification criteria defined (amended)

---


## Mechanical Verification (automated — Cursor fills after T13)

| ID | Assertion | How verified | Pass/Fail |
|----|-----------|-------------|-----------|
| V1 | All three sinks reach zero + postcondition passes | N8: Chroma query + JSONL grep + postcondition exit 0 | |
| V2 | Race closure: purge-then-ingest | N1: threading barrier — ingest batch aborts when exclusion found | |
| V3 | Race closure: ingest-then-purge | N2: threading barrier — purge deletes just-written rows, postcondition passes | |
| V4 | Unrelated data preserved (export lock) | N3: source B lines intact; concurrent append survives purge rewrite | |
| V5 | Exact path matching | N4: similar paths not confused; N13: legacy variants found | |
| V6 | Crash idempotency (all failure points) | N18a–h: simulated crash at each of 8 boundaries; retry converges | |
| V7 | Dry-run safety (separate preview function) | N6: preview_purge → zero mutations; CLI decline → no mutation | |
| V8 | Malformed JSONL fail-closed | N10: abort rewrite, original intact, nonzero exit | |
| V9 | Lock ordering enforced | N9: reverse acquisition raises/asserts | |
| V10 | Inter-model path covered | N7: inter_model_doc units deleted by purge | |
| V11 | --yes automation path | N11: no prompt, purge proceeds | |
| V12 | --undo after purge | N12: exclusion cleared, sinks still empty, re-index required | |
| V13 | Concurrent same-source purge | N14: second purge idempotent (zero rows, exit 0) | |
| V14 | Existing test suite unbroken | `test_processed_exclude_race.py` PASS; `test_chroma_superseded.py` PASS; full suite green | |
| V15 | No purged content in new artifacts; residual bytes acknowledged | Grep lock dir + tmp dir for source content → zero. Architecture doc explicitly states Chroma free-space/FS blocks/Restic may retain bytes. No false forensic claim. | |
| V16 | Source lock identity from config | N15: alternate-data-root test; ingest + purge compute same lock path; no live paths touched | |
| V17 | Missing-file exclusion | N16: purge deleted file → synthetic key; --list shows; --undo clears; watch_skip_reason = "excluded" | |
| V18 | No lock during LLM/embed | N17: instrumented lock tracking; no source/export lock held between parse-start and batch-write-start | |
| V19 | Postcondition check works | N18h: inject residual row after delete → postcondition fails → nonzero exit | |
| V20 | Superseded cache invalidated | N19: purge units (some superseded=True) → count_units returns correct count without stale cache | |
| V21 | All six JSONL writers use export lock | Code review + integration test: normal ingest, inter-model, observe append, observe upsert, deduplicate, purge — all acquire export flock | |
| V22 | Path-candidate builder shared | Code review: preview, Chroma delete, JSONL rewrite all receive candidates from same `build_path_candidates` call | |

---

## Behavioral Verification (Ryan — using temporary config/corpus only; Amendment §12)

Every behavioral demo must use:
- Temporary Chroma directory (not `~/.local/share/convmem/chroma/`)
- Temporary processed.json (not `~/.local/share/convmem/processed.json`)
- Temporary knowledge_units.jsonl (not the live export)
- Config override or env var pointing to temp paths

| ID | Claim | How verified | Pass/Fail |
|----|-------|-------------|-----------|
| B1 | Preview shows counts, not content | Run with temp config on seeded source; inspect output for absence of document text | |
| B2 | Default-No confirmation works | Decline at prompt → no mutation; search temp corpus → data still present | |
| B3 | --yes bypasses prompt | `--purge --yes` completes without interaction on temp corpus | |
| B4 | Exit codes correct | Exit 0 on success (postcondition pass); exit 1 on partial failure; exit 0 on decline | |
| B5 | --undo after purge enables re-index | `--undo PATH` then `index --file PATH --force` on temp corpus → data restored | |
| B6 | Search returns zero after purge | Search temp corpus for purged content → no hits from that source | |
| B7 | Missing-file purge works | Purge a path whose file no longer exists (temp corpus) → succeeds, synthetic key in processed | |

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

6. All V1–V22 cells filled PASS
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
