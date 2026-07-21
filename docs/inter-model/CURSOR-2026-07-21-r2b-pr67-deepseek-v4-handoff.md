# Cursor → DeepSeek V4: check Bugbot findings on R2b impl PR #67

**To:** DeepSeek V4 (Crush lane if shell; Continue+Bash OK) — **independent check**, not implementer  
**From:** Cursor  
**Date:** 2026-07-21  
**PR:** https://github.com/alanmz-crypto/convmem/pull/67  
**Branch:** `feat/2026-07-21-r2b-capture-auth`  
**Exact tip to review:** `38df0deb4c6fc371035ace746e8548d9e950a03d`  
**Architecture (binding):** [`docs/plans/ARCHITECTURE-r2b-capture-auth.md`](../plans/ARCHITECTURE-r2b-capture-auth.md) (on `main` via #65)

**Live ops:** Read-only. Do **not** merge, grant, run live capture, write eval-root, or `convmem record` / `--approve-last`.

---

## TL;DR

Ryan needs an independent verdict on **seven open Bugbot review threads** on PR #67 before merge. Say for each finding: **real / false-positive / defer**, with one sentence why, against the architecture doc. Prefer evidence from tip `38df0de…` (Bugs were filed against an earlier tip `4970eef…` — re-check current code).

---

## Context (plain language)

PR #67 implements R2b capture authorization in code (locked permission, source checks, one attempt, completion marker last). Pylint is green. Merge is blocked on open review threads. Cursor is the implementer; you are the checker.

**Naming:** If you run in Crush with DeepSeek V4 weights, you are still **Crush lane** for shell — say “Crush found …” when reporting. The job title is DeepSeek V4 check because Ryan asked for that reviewer.

---

## How to work

1. `convmem doctor` then `git fetch` and checkout tip `38df0deb4c6fc371035ace746e8548d9e950a03d` (or `gh pr checkout 67` and confirm tip).
2. Read architecture sections on write path, `source_snapshot`, completion marker, processed absence.
3. For each finding below: open the cited file/lines on **current tip**, not only Bugbot’s old SHA.
4. Return a verdict table (format at bottom). No code fixes unless Ryan separately asks.

---

## Findings to check (open threads)

### F1 — High — Caller paths never bound

- **On PR Find:** `Caller paths never bound`
- **Claim:** `_run_r2b_capture` copies from caller `export_src` / `processed_src` / `capture_dir` / `chroma_dir` without re-binding those args to `R2bBindings` from the approved manifest, so a valid capability could capture wrong sources or write wrong dirs.
- **Look at:** `eval_corpus/capture.py` — `_run_r2b_capture`, `materialize_r2b_write_authorization`, and how CLI passes paths.
- **Architecture ask:** Must runtime paths match approved bindings at write time?

### F2 — High — Approved snapshot not verified

- **Find:** `Approved snapshot not verified`
- **Claim:** Before writing the completion marker, R2b does not fully re-verify captured export / processed / Chroma against approved `source_snapshot`, so marker digests can disagree with on-disk capture if sources drift mid-run.
- **Look at:** post-copy drift checks, final live source-drift check, marker assembly (`source_snapshot_sha256`, `processed_state`).
- **Architecture ask:** Pre- and post-capture trusted recompute; marker only after checks pass.

### F3 — Medium — Processed state ignores manifest

- **Find:** `Processed state ignores manifest`
- **Claim:** `processed_state` is taken from “is `processed_src` a file?” instead of approved `source_snapshot.processed_state`, so absence/presence can disagree with the grant.
- **Look at:** copy branch and marker `processed_state` field vs `bindings.source_snapshot`.
- **Architecture ask:** When `processed_state == "absent"`, named path must stay absent; key still present in `paths`.

### F4 — Medium — Chroma extract sort diverges

- **Find:** `Chroma extract sort diverges`
- **Claim:** Identity uses UTF-8 byte sort in `compute_chroma_capture_identity`, but `extract_chroma_capture_slice` still uses plain `sorted(seen_ids)`, so extract and snapshot can diverge.
- **Look at:** both helpers; whether extract was refactored to share the canonical helper.
- **Architecture ask:** One shared canonicalization for snapshot, extract, and post-capture compare.

### F5 — Medium — Early drift skips report

- **Find:** `Early drift skips report`
- **Claim:** After `capture_dir` is created, early hash/drift failures return an in-memory FAILED report and never write `capture_report.json`, leaving a partial dir with no on-disk failure record.
- **Look at:** `_failed_r2b_result` / early return paths vs architecture “early FAILED report may remain.”
- **Architecture ask:** Incomplete dirs quarantined; report required when marker is written — clarify whether early FAILED must write report to disk.

### F6 — Low — Whitespace collection fields pass

- **Find:** `Whitespace collection fields pass`
- **Claim:** `chroma_collection_name` / `chroma_collection_id` accept whitespace-only strings (truthiness vs `.strip()`).
- **Look at:** `_validate_source_snapshot` / `validate_r2b_manifest_schema` in `eval_corpus/run_manifest.py`.

### F7 — Low — collection_id accepts non-string types

- **Find:** `collection_id accepts non-string types`
- **Claim:** Non-string JSON values (e.g. number) can pass as `chroma_collection_id`.
- **Look at:** same validator; type check for string.

---

## Out of scope

- Merging #67  
- Implementing fixes (Cursor does that after your verdict)  
- Live capture, packet ACCEPT/GRANT, B-Accept  
- Ledger `record` / `--approve-last`  
- Re-litigating Option A / architecture direction  

---

## Return format (paste back to Ryan)

```text
DEEPSEEK V4 / Crush — PR #67 Bugbot check
Tip reviewed: <sha>
Architecture: ARCHITECTURE-r2b-capture-auth.md

| ID | Title | Verdict (real / false-positive / defer) | One-sentence why | Blocking for merge? (Y/N) |
|----|-------|-----------------------------------------|------------------|---------------------------|
| F1 | Caller paths never bound | | | |
| F2 | Approved snapshot not verified | | | |
| F3 | Processed state ignores manifest | | | |
| F4 | Chroma extract sort diverges | | | |
| F5 | Early drift skips report | | | |
| F6 | Whitespace collection fields | | | |
| F7 | collection_id non-string types | | | |

Merge recommendation: HOLD | MERGE after F… | MERGE as-is
Largest risk if merged now: <one sentence>
```

---

## Status

| Item | State |
|------|--------|
| Handoff authored | 2026-07-21 |
| PR #67 pylint | PASS on tip `38df0de…` |
| Ryan HITL | Waiting on this check + merge decision |
