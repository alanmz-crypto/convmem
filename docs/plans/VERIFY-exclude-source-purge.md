# Verification Matrix — Exclude Source Purge

**Architecture:** [`ARCHITECTURE-exclude-source-purge.md`](ARCHITECTURE-exclude-source-purge.md)
**Execution:** [`EXECUTION-exclude-source-purge.md`](EXECUTION-exclude-source-purge.md)
**Branch:** `plan/2026-07-14-exclude-source-purge`
**Status:** Awaiting architecture HITL; verification criteria defined

---

## Mechanical Verification (automated — Cursor fills after T9)

| ID | Assertion | How verified | Pass/Fail |
|----|-----------|-------------|-----------|
| V1 | All three sinks reach zero for purged source | N8: Chroma query + JSONL grep after purge | |
| V2 | Race closure: purge-then-ingest | N1: threading barrier test — ingest batch aborts when exclusion found | |
| V3 | Race closure: ingest-then-purge | N2: threading barrier test — purge deletes just-written rows | |
| V4 | Unrelated data preserved | N3: source B lines intact after source A purge | |
| V5 | Exact path matching | N4: similar paths not confused; N13: legacy variants found | |
| V6 | Crash idempotency | N5: simulated crash mid-purge + retry → all sinks zero | |
| V7 | Dry-run safety | N6: preview mode → zero mutations in Chroma + JSONL | |
| V8 | Malformed JSONL fail-closed | N10: abort rewrite, original intact, nonzero exit | |
| V9 | Lock ordering enforced | N9: reverse acquisition raises/asserts | |
| V10 | Inter-model path covered | N7: inter_model_doc units deleted by purge | |
| V11 | --yes automation path | N11: no prompt, purge proceeds | |
| V12 | --undo after purge | N12: exclusion cleared, sinks still empty, re-index required | |
| V13 | Concurrent same-source purge | N14: second purge idempotent (zero rows, exit 0) | |
| V14 | Existing test suite unbroken | `test_processed_exclude_race.py` PASS; `test_chroma_superseded.py` PASS | |
| V15 | No purged content in artifacts | Grep lock dir + tmp dir for source content after purge → zero matches | |

---

## Behavioral Verification (Ryan — manual or observed)

| ID | Claim | How verified | Pass/Fail |
|----|-------|-------------|-----------|
| B1 | Preview shows counts, not content | Run `convmem exclude PATH --purge` on seeded source; inspect output | |
| B2 | Default-No confirmation works | Decline at prompt → no mutation; re-run search → data still present | |
| B3 | --yes bypasses prompt | `convmem exclude PATH --purge --yes` completes without interaction | |
| B4 | Exit codes correct | Exit 0 on success; exit 1 on partial failure; exit 0 on dry-run/decline | |
| B5 | --undo after purge enables re-index | `convmem exclude --undo PATH` then `convmem index --file PATH --force` → data restored | |
| B6 | Search returns zero after purge | `convmem search "content from purged source"` → no hits from that source | |

---

## Regression Guard

| Existing test file | Must still pass | Notes |
|-------------------|-----------------|-------|
| `tests/test_processed_exclude_race.py` | Yes | Core exclusion race tests; new lock layer must not break them |
| `tests/test_chroma_superseded.py` | Yes | Tombstone/forget semantics unchanged |
| `tests/test_record_review_cli.py` | Yes | Record pipeline unaffected |
| `tests/test_write_gate_effect.py` | Yes | Write guard behavior unchanged |
| Full pytest suite | Yes | No regressions introduced |

---

## Security Properties

| Property | Verification |
|----------|-------------|
| Purged payloads not written to any file | V15 + code review: no temp/undo file contains document text |
| Exclusion marker survives concurrent ingest | V2 (existing behavior) + N1 |
| Lock files do not contain sensitive data | Code review: lock files are empty (flock advisory only) |
| No path traversal in lock filename | SHA-256 of canonical path → safe filename; test with adversarial paths |

---

## HITL Sign-off Criteria

Before marking this plan as accepted:

1. Ryan reviews and accepts Architecture gates 1–10
2. Ryan confirms Design A (per-source flock) as the chosen approach
3. Ryan acknowledges accepted downside (export lock adds one lock to hierarchy)
4. Ryan confirms implementation lane (Cursor) and review lane (Kiro)

After execution completes:

5. All V1–V15 cells filled PASS
6. All B1–B6 cells filled PASS (Ryan observes or delegates)
7. Full pytest suite green
8. Branch pushed; PR ready for Ryan merge

---

## Out of scope for verification

- Restic snapshot purge (operational, not code)
- Performance benchmarks (corpus too small to matter)
- Multi-machine scenarios (single-host by design)
- Chroma internal compaction timing (Chroma's responsibility)
