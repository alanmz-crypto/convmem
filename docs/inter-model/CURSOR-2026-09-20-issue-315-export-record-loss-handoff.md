# Implementation Handoff: Issue #315 — zero-filled export row became silent unit loss

**Date:** 2026-09-20
**Author:** Crush (read-only diagnosis + code corrective)
**For:** Cursor (PR open / any follow-up implementation); Ryan (decisions below)
**Arc:** none (ad-hoc) — issue [#315](https://github.com/alanmz-crypto/convmem/issues/315)
**Authorization:** Ryan routed #315 to Crush for read-only diagnosis; the code
corrective was a scoped follow-up on the same branch. No production export
mutation was performed or authorized.

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `READY_FOR_PR` — work complete; open items are decisions, not implementation |
| **Branch** | `docs/2026-09-20-315-invalid-export-record-diagnosis` |
| **Tip SHA** | `cf9f19bff3fca0d55e44361cdad1371cdd6c98b8` |
| **Push status** | pushed to origin (verified via `git ls-remote`) |
| **PR** | **not opened** — branch is push-ready |
| **Ryan GATE** | Three decisions in §Open decisions below |
| **Track A ingest** | `~/Projects/convmem/.crush/crush.db` (indexed) |
| **Ledger** | `obs_68435fbdab34` (RTX 3060 Xid, related), `obs_a09dbfa9e237` (Chroma two-problem separation) |

---

## TL;DR

A production export row was reported as invalid UTF-8. It was actually a valid
record preceded by **1661 NUL bytes** — a torn append. The row has since
disappeared entirely and took **one active unit** with it. The export now scans
clean and `logical_projection` PASSes, which means the failure mode converted
from "loud" to "silent". The code corrective landed; the open items are a
recovery decision and a prevention decision.

---

## What changed

| Commit | Change |
|--------|--------|
| `459f995` | Diagnosis doc + `LATEST.md` routing bullet |
| `2f4c6d0` | Zero-fill gets its own error class; every invalid row reports nonblank record number, byte offset, length, and SHA-256 |
| `d03467c` | Append round-trip tests: valid JSON, newline-terminated, no NUL bytes, ids intact |
| `0f3c089` | Store-parity test: a dropped or duplicated export row now fails |
| `cf9f19b` | `LATEST.md` corrected from "pending repair" to "one unit lost" |

**Integration points:**

- `export_compaction.py` — `ZeroFilledExportRecordError` added beside
  `InvalidExportRecordError`; `_validate_record` detects a leading NUL run;
  `_scan_into_index` wraps the call to attach position and digest.
- `tests/test_export_compaction.py` — 4 new tests.
- `tests/test_ingest_dedupe.py` — 2 new tests.

**Message contract.** Errors raised from the scan now read:

```
export record is zero-filled (leading_zero_bytes=1661) at nonblank_record=147814 byte_offset=3712694659 length=11583 sha256=30b21251…
export record is not valid JSON at nonblank_record=2 byte_offset=8 length=8 sha256=…
```

Only integers, a hex digest, and fixed strings — no record content.

---

## Evidence summary

| Fact | Value |
|---|---|
| Export path | `~/.local/share/convmem/knowledge_units.jsonl` |
| Corrupt record offset / length | `3712694659` / `11583` |
| Corrupt record SHA-256 | `30b21251e972dcb66bc8c5452da363cea55e91e170d0335125a067586fe5740e` |
| Leading NUL run | 1661 contiguous bytes, verified all-zero |
| Payload after stripping NULs | exactly `json.dumps(unit)`, len 9921 |
| NUL bytes inside the JSON body | 0 |
| Producer | `ingest.py:674-677` — `open(export, "a")` with no `flush`/`fsync` |
| Why compaction can't heal it | `export_compaction.py:255` returns early when `retained >= nonblank` |
| Introduced | between 2026-09-20 00:18 and 04:03 CDT |
| Clean bounding snapshots | restic `e51f849a`, `48fde3d7` (both fully scanned clean) |
| Export after rewrite | dev `66306`, ino `20884043`, size `3771679862`, 149,601 records |
| Anomalies now | **zero** |

**The lost unit:** export rows for its `source_path` went **8 → 7**; Chroma still
holds **8**. Missing id `ca9e3739736068c7…`, `type=pattern`,
`content_hash=349edcd651731bb7…`. Its Chroma doc SHA-256 equals that
`content_hash`, so the bytes are recoverable from Chroma.

**Cause of the rewrite:** the Chroma HNSW SIGSEGV / rebuild loop documented in
[`KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md`](KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md).
Three distinct export inodes were observed during the session. The export
corruption and the Chroma crashes are **one incident, not two**.

---

## Open decisions (Ryan)

1. **The one lost unit.** Restore `ca9e3739736068c7…` into the export from Chroma,
   or accept the divergence as derived-state. If restoring: Chroma is the source,
   the doc hash matches, and no re-distill is needed.
2. **Append durability.** `ingest.py:674-677` still has no `flush`/`fsync`.
   Deliberately not changed — it costs an fsync per appended unit and is a
   performance tradeoff that deserves its own decision. Without it, this class of
   damage can recur on the next interrupted append.
3. **PR.** Branch is pushed and ready. No PR opened.

**Note:** the upstream Chroma crash loop is the real prevention. Until the Kiro
poison-pill / upsert-isolation fix lands, further export rewrites and further
silent unit loss are expected.

---

## Test expectations and what was verified

132 tests pass on the related suite; pylint 10.00/10. Both new test groups were
**verified to fail on the real defect** before being accepted:

- Injecting a NUL-prefixed append → both `tests/test_ingest_dedupe.py` tests fail.
- Dropping one export row → the parity test fails.
- `pylint export_compaction.py tests/test_export_compaction.py tests/test_ingest_dedupe.py` → 10.00/10.

`ingest.py` was restored and confirmed clean after each fault injection.

**Known coverage limit:** the parity test covers newly committed batches only. It
does not detect pre-existing corpus-wide divergence — Chroma currently holds
81,029 units against an export of 149,601 historical ids, so a unit can still be
silently lost outside the test's scope.

---

## Acceptance criteria

- [x] Zero-fill reported distinctly from corrupt rows
- [x] Invalid rows report record number, offset, length, digest — no content
- [x] Tests catch a zero-prefixed append
- [x] Tests catch a dropped export row
- [x] No production export mutation
- [x] No regression in related suite; pylint clean
- [ ] PR opened (awaiting Ryan)
- [ ] Ryan decides the three open items

---

## Branch convention

```
docs/2026-09-20-315-invalid-export-record-diagnosis
```

Pushed. Squash-merge is fine — no history preservation needed.

---

## Related files

| What | Path |
|------|------|
| Full diagnosis + confidence table | `docs/inter-model/CRUSH-2026-09-20-issue-315-invalid-export-record-diagnosis.md` |
| Failing validator | `export_compaction.py:148`, `:212` |
| No-op early return | `export_compaction.py:255` |
| **Append writer (root cause site)** | `ingest.py:674-677` |
| Export lock | `purge_locks.py:54`, `:79`, `:93` |
| Atomic publication | `atomic_files.py:40` |
| Compaction tests | `tests/test_export_compaction.py`, `tests/test_export_compaction_golden.py` |
| Append/parity tests | `tests/test_ingest_dedupe.py` |
| Upstream Chroma fix | `docs/inter-model/KIRO-2026-09-20-chroma-upsert-heap-corruption-handoff.md` |
| Issue thread | [#315 comment](https://github.com/alanmz-crypto/convmem/issues/315) |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed
- [x] `LATEST.md` bullet at top with link and resume state
- [x] Branch pushed
- [x] Issue #315 updated with status and open items
- [x] Track A session ingest

**Implementer (picking up):**

- [ ] Read this file before first edit
- [ ] `git fetch && git switch docs/2026-09-20-315-invalid-export-record-diagnosis`
- [ ] Open the PR if Ryan authorizes; otherwise wait on the three decisions
- [ ] Re-verify the live export inode/size before touching anything — it changed
      three times during the original session
