# Read-only diagnosis: issue #315 invalid export record at line 147814

**Date:** 2026-09-20
**Author:** Crush (read-only diagnosis)
**For:** Ryan (authorization), then Cursor if a code corrective is required
**Arc:** none (ad-hoc) — issue #315
**Issue:** [#315](https://github.com/alanmz-crypto/convmem/issues/315) — "Repair invalid UTF-8 export record blocking indexing"

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `BLOCKED_ON_RYAN` — diagnosis complete, no mutation performed |
| **Branch** | `docs/2026-09-20-315-invalid-export-record-diagnosis` |
| **Push status** | pushed to origin |
| **PR** | not opened (diagnosis only) |
| **Ryan GATE** | Approve Repair Option A or B below before any export mutation |
| **Track A ingest** | `~/Projects/convmem/.crush/crush.db` |

---

## Headline

**The record is not invalid UTF-8.** It is valid UTF-8, valid JSON, and
byte-identical to the clean writer output — preceded by **1661 NUL bytes**
(`0x00`). The issue title and the existing failure message both mislabel the
defect, which is why the search space so far has looked like an encoding bug
when it is a **write-completion** bug.

The corruption is a **sparse-file hole / zero-fill of a partial append**, not a
content defect. It is isolated: **exactly one anomalous record in 148,324
nonblank records**, and no other record in the file has a leading NUL or an
embedded NUL.

---

## 1. Exact reproduction (read-only, no content printed)

Structural re-derivation against the live export:

| Fact | Value |
|------|-------|
| Export path | `~/.local/share/convmem/knowledge_units.jsonl` |
| Device / inode | `66306` / `20883997` (unchanged by all scans) |
| Live size at diagnosis | `3728831447` bytes |
| Record start offset | `3712694659` |
| Raw record length | `11583` bytes (terminated) |
| Record SHA-256 | `30b21251e972dcb66bc8c5452da363cea55e91e170d0335125a067586fe5740e` |
| Records before it | 147,813 nonblank; it is nonblank #147814 |
| **Decodes as UTF-8** | **yes** — `UnicodeDecodeError` **not** reproduced |
| Fails as JSON | yes — `JSONDecodeError`, `pos=0`, `lineno=1`, `colno=1` |
| Leading NUL run | **1661 contiguous `0x00` bytes** (all-zero, verified) |
| Bytes after the NUL run | `7b 22 69 64` = `{"id` |
| Final byte of record | `7d` = `}` then `0a` (newline-terminated) |
| NULs inside the JSON body | **0** |
| Preceding record | ends `...63316166227d0a` — i.e. `c1af"}\n`, properly terminated, SHA `82dd6e46949950e1…` |
| Payload after stripping NULs | len `9921`, **byte-identical** to `json.dumps(unit)` (no newline); `+ "\n"` = the writer's exact output |

The issue's `UnicodeDecodeError` claim is reproducible only if the scan decoded
**raw bytes as strict UTF-8 including the NULs** — NUL is itself a valid UTF-8
code point (`U+0000`), so a correct scan reports a JSON error, not a decode
error. The issue's "Record length: 11583" matches the raw *with* the NUL prefix,
which is why the two observations were attributed to one cause.

### Failure path

`convmem index --file <runtime>` → `ingest._deduplicate_units_export_impl`
(`ingest.py:560`) → `export_compaction.compact_units_export`
(`export_compaction.py:52`) → `_scan_into_index` (`:212`) →
`_validate_record` (`:148`) → `json.loads` raises at `export_compaction.py:156`:

```
InvalidExportRecordError: export record is not valid JSON
```

Live re-run of `_scan_into_index` against the unmodified export reproduced the
failure in **6.5 s** with **no** size, mtime, or inode change. The scan is
read-only by construction (`os.open` with `O_RDONLY|O_NOFOLLOW`, `_pread_exact`,
SQLite `connect("")` scratch).

---

## 2. Which writer or recovery path produced it

### The writer

`ingest.py:674-677`:

```python
if units_export and write_export:
    units_export.parent.mkdir(parents=True, exist_ok=True)
    with export_flock(cfg):
        with open(units_export, "a", encoding="utf-8") as uf:
            uf.write(json.dumps(projection_unit) + "\n")
```

This matches the payload byte-for-byte: `json.dumps` default separators, no
`ensure_ascii=False`, `+ "\n"`, opened `"a"` with `encoding="utf-8"`.

### Why a valid payload could be hole-prefixed

Two structural facts narrow the mechanism to a **loss of append durability**,
not a bug in the payload:

1. **No `flush`/`fsync` at the append site.** The `with open(...)` block closes,
   which flushes Python buffers to the kernel, but nothing forces data to
   stable storage — while the Chroma `add_unit` for the same unit was already
   durably committed. A hard power loss inside that window leaves the four
   consumers disagreeing: Chroma has the unit; the export has a torn tail.
2. **`_deduplicate_units_export_impl` is a no-op when there are no duplicates.**
   `_compact_locked` (`export_compaction.py:255`) returns `0` early when
   `nonblank == 0 or retained >= nonblank`. A duplicate-free export is therefore
   **never rewritten** — there is no compaction pass that would heal a torn
   region. The damage survives indefinitely, and because compaction runs *before*
   indexing, the torn region blocks every later index.

The NUL prefix is consistent with a **stale block-sized zero tail from a
previous longer version of this file** being exposed: the region
`3712694659..3712696319` (1661 bytes) is entirely zeros, unaligned
(`offset % 4096 == 2435`), which is what a sparse hole reveals when a later
shorter write is appended over a region the file system had zero-filled.

### Time window (evidence-backed)

| Time (CDT) | Snapshot / evidence | Export size | Records | State |
|---|---|---|---|---|
| 2026-09-19 04:17 | restic `48fde3d7` | 3,416,557,577 | 138,050 | **clean** — full scan, zero anomalies |
| 2026-09-20 00:18 | restic `e51f849a` | 3,678,081,338 | 146,738 | **clean** — full scan, zero anomalies |
| 2026-09-20 04:03 | live mtime | 3,724,452,738 | (not rescanned) | defect present |
| 2026-09-20 04:10 | live mtime (now) | 3,728,831,447 | 148,324 | defect present |

**The corruption was introduced between 2026-09-20 00:18 and 04:03 CDT.**
The 00:18 snapshot is fully clean, so this is *not* an old latent defect that
was merely discovered late — it is a fresh, same-night event.

### Candidate trigger

`journalctl` shows repeated RTX 3060 `Xid 13/43` SM faults on 2026-09-19
(`16:09`, `16:45`, `23:46` …), and the standing open observation
`obs_68435fbdab34` already localizes them to `GPC2/TPC0/SM1`. Each fault aborts
an in-flight CUDA operation with `pid=..., name=python`. The `[FAIL]
logical_projection` doctor check (`'str' object has no attribute 'get'`, seeded
by this same malformed row) and the ingest failures share this window.

**Confidence: medium.** Correlation, not proof — no OOM-kill, kernel I/O error,
or ext4 error appears in the window. The mechanism (lost append durability) is
high confidence; the specific trigger is medium.

---

## 3. Does Chroma still contain the unit?

**Yes — confirmed present and consistent.**

| Field | Export record (NULs stripped) | Chroma metadata | Match |
|---|---|---|---|
| `id` | present, 64 chars, `id_sha16=ecaffe9bb9a1fd8c` | same id retrievable | ✅ |
| `type` | `pattern` | `pattern` | ✅ |
| `tool` | `cursor` | `cursor` | ✅ |
| `domain` | `web_stack.security` | `web_stack.security` | ✅ |
| `source_path` | `…/tmp-willowyhollow-contract-pilot-harness/agent-transcripts/1e5abc4a-…/1e5abc4a-….jsonl` | identical | ✅ |
| `author_model` | `deepseek-v4-flash` | `deepseek-v4-flash` | ✅ |
| `content_hash` | `349edcd651731bb7…` | `349edcd651731bb7…` | ✅ |
| **document/`summary`** | `summary` len 225 | doc len 334, **SHA-256 == `content_hash`** | ✅ |
| `provenance_envelope` | dict, 23 keys | same 23 keys (Chromadb `dict`; export serializes as dict) | ✅ |
| `provenance_commitment` / `assertion_id` | 64-char each | identical | ✅ |
| embedding | — | present, 768-dim | ✅ |

All 8 Chroma units for that `source_path` are present, each `start_offset=0`,
`workspace_directory=''`, `source_type=None` — **identical to the other seven
sibling units from the same transcript**, which is strong evidence the record is
a genuine writer output, not a fabricated row.

### Recovery-relevant observation (important)

All 8 units from this transcript are re-derivable **offline from the source
transcript**, which is still on disk unmodified:

- `workspace_directory` is `''` in Chroma, and the adapter
  (`adapters/jsonl_chat.py`) never emits `workspace_directory` — so the empty
  value is what a fresh ingest produces, not a lossy fallback.
- `session_id` `1e5abc4a-4a5c-4427-a4a8-32f5cfb4970e` is derivable from the path
  (`_session_id_from_path`), and `processed.json` already records
  `chunks: 1, units: 8`.

**Not yet established:** whether the record's `keywords`, `summary`, `title`, and
`provenance_envelope` are byte-reproducible from the source transcript. Those
fields come from the **distill/summarize LLM response**, which is not stored —
so byte-reproduction requires either the original provider response or the
already-persisted export/Chroma copy. **This is the single most important open
question for choosing Option B below.**

---

## 4. Can the export be reconstructed from authoritative data?

**Partially.** Field-level coverage:

| Export field | Authoritative source | Reproducible? |
|---|---|---|
| `id`, `type`, `title`, `source_path`, `confidence`, `timestamp`, `tool`, `domain`, `author_model`, `verifier_model`, `start_offset` | Chroma metadata | ✅ exact |
| `assertion_id`, `effective_integrity`, `provenance_commitment`, `provenance_envelope`, `provenance_status` | Chroma metadata | ✅ exact |
| `summary`, `keywords`, `source_type`, `content_hash` | **Not in Chroma metadata** — only the doc/embedding | ⚠️ `content_hash` = SHA-256 of Chroma doc; `summary`/`keywords` require re-distill or the existing bytes |
| key **order** | `ingest.py:940-952` insertion order | ✅ known |

Two distinct reconstruction scopes exist and they cost very different amounts:

- **Record-scope reconstruction** (repair one row): needs `summary`, `keywords`,
  `source_type`, `title` for exactly this unit. Available from the corrupted
  record itself (the payload is intact after the NULs) or from a backup.
- **Full-export reconstruction** (rebuild all 148,324 rows): requires
  `raw_units` for every chunk, i.e. re-running distill against every source —
  network calls, cost, and **non-determinism** (temperature 0.2) that would
  change `summary`/`keywords` and therefore `content_hash`. **This would not
  reproduce the current export byte-for-byte and should not be the first move.**

**Recommendation:** do not attempt full reconstruction. The defect is one row of
one file; the file is otherwise intact.

---

## 5. Existing tests: how invalid bytes could enter or survive compaction

The compaction hardening from PR #302 (`a91bb28`) is **sound and already correct**
for this class of input, and no test proves otherwise:

| Test | File:line | What it proves |
|---|---|---|
| `test_invalid_utf8_fails_closed` | `tests/test_export_compaction.py:211` | `\xff` row → `InvalidExportRecordError`, original untouched |
| `test_invalid_utf8_fails_closed` | `tests/test_export_compaction_golden.py:146` | same, golden parity |
| `test_malformed_json_fails_closed` | `:188` / `:111` | `NOTJSON` → fail closed |
| `test_non_object_missing_empty_and_nonstring_ids_fail_closed` | `:195` | structural rejects |
| `test_oversized_record_fails_closed_without_unbounded_readline` | `:228` | 16 MiB ceiling; bounded `os.read` |
| `test_noop_validates_identity_before_return` | `:469` | no-op still verifies identity |
| `test_lock_contention_blocks_append_writer` | `:437` | flock serializes compaction vs append |
| `test_sigkill_after_batches_leaves_export_dir_untouched` | `:561` | SIGKILL mid-scan leaves export dir clean |
| `test_path_replacement_during_output_refuses_publication` / `test_same_inode_mutation_during_output_refuses_publication` | `:384` / `:409` | publication identity checks |

**Gaps the suite does not cover — and the reason this defect reached production:**

1. **`ingest.py`'s append site has no test.** Every hardening test targets
   compaction. Nothing tests that an append is durable, validated, or
   atomic, so there is no test that would fail when an append is torn.
2. **No test asserts export/Chroma unit-set parity after a write.** A torn
   append that loses a record is invisible to compaction (the file stays
   "valid") and to the existing suite.
3. **No test covers a NUL-prefixed or zero-filled row.** The suite tests
   `\xff` (invalid UTF-8) and `NOTJSON`, but not the actual defect class:
   valid JSON behind a zero run. `_validate_record` correctly rejects it —
   as "not valid JSON", which is a *misleading* diagnosis, not a wrong
   decision.
4. **No fsync/durability assertion on the append path.** `test_sigkill_*`
   covers compaction; nothing covers append.

---

## 6. Safe line/offset/digest error reporting (proposed)

`_validate_record` (`export_compaction.py:148`) receives only `raw: bytes`, so it
cannot report position. The caller `_scan_into_index` (`:212`) holds
`offset`, `start`, and `nonblank`. Proposed change — **strictly additive to the
message, no behavior change**:

```python
# _scan_into_index, at the _validate_record call site
try:
    uid = _validate_record(record)
except InvalidExportRecordError as exc:
    raise InvalidExportRecordError(
        f"{exc} at nonblank_record={nonblank} "
        f"byte_offset={start} length={length} "
        f"sha256={hashlib.sha256(record).hexdigest()}"
    ) from exc
```

Reporting rules, all of which are satisfied by this shape:

- **Safe:** emits only integers, a hex digest, and the existing fixed error
  strings. No record content, no field values, no source paths.
- **Actionable:** `byte_offset` + `length` let a repair tool seek directly
  (exactly what this diagnosis did) without rescanning 3.7 GB.
- **Correct label:** split the message so the real class is named — for example
  `export record has a leading zero-fill prefix (byte_offset=…, run=1661)`
  when `raw.strip(b"\x00") != raw.strip()`, distinct from a genuine
  `not valid UTF-8`. This is what would have routed #315 correctly on day one.
- **Digest:** SHA-256 of the raw record, so a repair can be verified against the
  reported digest.

---

## Proposed repair authorization packet

### Option A — exact single-record repair (recommended)

**Scope:** rewrite one row in place, preserving every other byte.

1. **Preconditions**
   - `convmem doctor` fully green except the known #315-driven checks.
   - Fresh restic snapshot taken **after** this diagnosis (the 00:18 `e51f849a`
     snapshot is already a clean pre-corruption reference and remains the
     rollback target).
   - Acquire the export flock (`export_flock_path`, i.e.
     `knowledge_units.jsonl.lock`) for the entire operation.
   - **`convmem-watch` and `convmem-refine` stopped** for the duration, so no
     append can interleave.
2. **Verification before write**
   - Confirm live `dev`/`ino`/`size` equal the values in this document.
   - Confirm the raw record at `byte_offset=3712694659`, `length=11583` still
     hashes to `30b21251e972dcb66bc8c5452da363cea55e91e170d0335125a067586fe5740e`.
   - Confirm `raw.lstrip(b"\x00")` is exactly 9,921 bytes and equals
     `json.dumps(parsed_unit)` byte-for-byte; confirm the NUL run is exactly
     1,661 contiguous bytes.
3. **Write**
   - Publish via `atomic_files.atomic_write_stream` (temp → fsync → mode
     preserve → fsync → validate → `os.replace` → parent fsync), writing the
     record with the 1,661 NUL bytes removed and every other byte unchanged.
   - Abort and leave the original untouched on any validation failure.
4. **Postconditions**
   - `compact_units_export` scan completes; record count unchanged at 148,324.
   - `convmem index --file <Codex rollout>` completes.
   - Chroma/export parity for the affected `source_path` still 8/8.
   - `convmem doctor` → `logical_projection` PASS.
   - Rollback: restore `knowledge_units.jsonl` from `e51f849a`, or from the
     fresh pre-write snapshot.

**Risk:** low. One contiguous span of NULs removed; payload provably intact.

**Cost:** minutes. No network, no LLM calls, no re-embed.

### Option B — reconstruct the record from Chroma + transcript

Same as Option A for steps 1-4, but rebuild the record rather than strip NULs.
Use this only if step 2's payload verification fails (i.e. the JSON behind the
NULs turns out to be damaged too — it is not, per this diagnosis).

**Open question that must be answered first:** whether `summary` and `keywords`
are byte-reproducible. They come from an unarchived distill response, so
Option B is only safe if Chroma's stored doc plus a deterministic re-distill
reproduces `content_hash = 349edcd651731bb7…`. If it does not, Option B
**changes the record** and must be authorized as a content change, not a repair.

**Risk:** medium-high (content drift, non-determinism).
**Cost:** requires a distill invocation against the source transcript.

### Explicitly out of scope

- Reconstructing the whole export (148,324 rows) — unnecessary, and it cannot
  reproduce current bytes.
- Re-running `convmem verify` or any bulk index as part of the repair.
- Any change to `main`, the restic repos, or Chroma.

---

## Recommended next steps

| # | Action | Lane | Gate |
|---|---|---|---|
| 1 | Approve Option A; confirm the repair window (watch/refine stopped) | Ryan | **required** |
| 2 | Land the safe error-reporting change (§6 | Cursor | after 1, code PR |
| 3 | Add the missing append-durability + export/Chroma parity tests (§5 gaps 1-2) | Cursor | with 2 |
| 4 | Consider `flush` + `fsync` at `ingest.py:677` append site | Cursor | separate decision |
| 5 | Execute Option A under the approved packet | Cursor | after 1 |
| 6 | Verify postconditions (§Option A step 4) | Kiro | after 5 |

Item 4 is the durable fix: without it, the same class of damage can recur on the
next interrupted append. It is **not** required to close #315, and should be
decided on its own merits (it adds an fsync per appended unit).

---

## Confidence summary

| Finding | Confidence | Basis |
|---|---|---|
| Defect is 1661 leading NUL bytes, not invalid UTF-8 | **high** | direct byte inspection, digest matches issue |
| Payload is byte-exact clean writer output | **high** | equals `json.dumps(unit)` exactly |
| Exactly one anomalous record in 148,324 | **high** | full-file read-only scan |
| Defect introduced between 2026-09-20 00:18 and 04:03 | **high** | both bounding snapshots fully scanned clean |
| Chroma has the unit; fields and doc hash consistent | **high** | direct retrieval + hash comparison |
| Mechanism is lost append durability / sparse zero-fill | **medium-high** | structural + absence of fsync at append site |
| Trigger is the RTX 3060 Xid fault series | **medium** | correlation only; no OOM/I/O error in window |
| Option A repair fully resolves #315 | **high** | payload intact, single contiguous span |
| `keywords`/`summary` byte-reproducible offline | **low** | distill response not archived; unverified |

---

## Constraints observed

Read-only throughout. No record content printed. No export mutation. No bulk
`convmem index`, no `convmem verify`, no production data repair, no GitHub state
change. All snapshots were restored to `~/.cache/convmem-315/` (scratch) and the
live export's `size`, `mtime`, inode, and device were re-verified unchanged after
every scan.

---

## Related files

| What | Path |
|------|------|
| Failing validator | `export_compaction.py:148` (`_validate_record`), `:212` (`_scan_into_index`) |
| Compaction entry | `export_compaction.py:52` (`compact_units_export`) |
| No-op early return (why damage persists) | `export_compaction.py:255` (`_compact_locked`) |
| **Append writer (root cause site)** | `ingest.py:674-677` |
| Dedupe wrapper | `ingest.py:553-568` |
| Export lock | `purge_locks.py:54`, `:79`, `:93` |
| Atomic publication | `atomic_files.py:40` (`atomic_write_stream`) |
| Compaction tests | `tests/test_export_compaction.py`, `tests/test_export_compaction_golden.py` |
| Backup restore tooling | `complete_data_restore.py:156` (`_read_jsonl`, raises on malformed) |
| Recovery authority projection | `recovery_authority.py:255` |
| Reproduced first bad record | restic `e51f849a` (clean), `48fde3d7` (clean) |
| Scratch restores (not committed) | `~/.cache/convmem-315/` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed
- [x] `LATEST.md` bullet at top with link and resume state
- [x] Branch pushed
- [x] Track A session ingest

**Implementer (picking up):**

- [ ] Read this file before first edit
- [ ] Wait for Ryan's Option A / Option B decision — do **not** touch the export first
- [ ] `convmem work resume docs/2026-09-20-315-invalid-export-record-diagnosis`
