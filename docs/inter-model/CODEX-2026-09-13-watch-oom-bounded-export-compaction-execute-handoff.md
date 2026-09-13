# Implementation handoff — issue #268 bounded export compaction

**Arc:** Trapdoor Hunt (issue #268 operational follow-up)

**Date:** 2026-09-13
**Author:** Codex planning lane
**For:** Cursor implementation lane
**Authorization:** Ryan, 2026-09-13, explicit chat authorization: “authorize
Cursor Execute C0–C7”

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` |
| **Implementation branch** | create `fix/2026-09-13-watch-oom-bounded-export-compaction` in a fresh worktree |
| **Reviewed plan tip** | `36f9069fa16a842daf877add4388ed07583c4e5c` |
| **Runtime base** | `8983a6fc909344239e6e3051d85c50c5508c1a16` (`origin/main` when reviewed) |
| **Plan push status** | pushed to `origin/plan/2026-09-13-watch-oom-bounded-export-compaction` |
| **PR** | not opened; implementation does not authorize one |
| **Ryan GATE** | none for C0–C7; all live/PR/P2 actions remain gated |

## Goal / role / system / next

**Goal:** remove the demonstrated corpus-sized RSS accumulator from global
JSONL export compaction while preserving valid-row results and honest
original-or-complete-new crash behavior.

**Cursor's role:** implement exactly C0–C7 from the Kiro-PASSed plan, verify it
hermetically, commit and push, then stop at an exact tip.

**The system currently:** merged runtime `8983a6fc…` still materializes the
complete export through `read_text().splitlines()`, a retained-line dictionary,
and sometimes a joined replacement. Kiro PASSed the plan at `36f9069…`,
including the explicit incremental 16 MiB record-ceiling correction. Existing
watch exclusions remain containment; Arc Codex P2 is paused.

**Next action:** create the fresh implementation worktree, bring in the two
reviewed plan commits, execute C0–C7, and stop. Do not operate on the shared
checkout.

## Branch setup

From the repository root:

```text
convmem work start fix watch-oom-bounded-export-compaction --worktree
git cherry-pick 90beef57e1e4dd1bbe749215513d5c2478263298
git cherry-pick 36f9069fa16a842daf877add4388ed07583c4e5c
```

The first command creates and pushes the branch from `origin/main`. Push
immediately after each cherry-pick and every later commit using the explicit
branch refspec. If `origin/main` no longer equals `8983a6fc…`, stop and report
the new base before implementation; do not silently rebase the reviewed plan
onto changed runtime code.

## Authoritative specification

Read and implement:

- `docs/plans/EXECUTION-watch-oom-bounded-export-compaction.md` at reviewed
  plan tip `36f9069…`;
- C0–C7 in order;
- the 16 MiB ceiling incrementally while scanning, with each read bounded by
  remaining budget plus one detection byte—never an unbounded `readline()`
  followed by measurement.

The main integration points are:

- `ingest.py::_deduplicate_units_export_impl()` — retain the existing
  `production_writer_boundary(entrypoint="ingest.export")` wrapper and export
  flock, but delegate compaction to the new deep module;
- new `export_compaction.py` — bounded scanner, strict validation, SQLite
  offset index, streaming output, identity validation, and owned-scratch
  cleanup;
- `atomic_files.py` — callback-based `atomic_write_stream` with a validator
  after temp fsync and immediately before replacement.

## Required behavior

1. Preserve valid-row semantics: blank lines ignored, last value retained per
   non-empty string ID, IDs emitted in first-occurrence order, exact no-op when
   every nonblank row is uniquely valid.
2. Fail before publication on invalid UTF-8/JSON, non-object JSON, missing,
   empty, or non-string IDs, or records exceeding 16 MiB. Original bytes remain
   unchanged.
3. Store only ID, first sequence, and latest byte offset/length in a private
   same-directory SQLite scratch database; do not retain document lines in the
   database or Python collections.
4. Keep the export lock across scan, scratch indexing, output, validation, and
   publication.
5. Stream retained records from the still-open original descriptor into an
   atomic temp; revalidate path identity immediately before `os.replace`.
6. Preserve honest pre-publication versus post-publication durability errors.
7. Remove only invocation-owned artifacts on handled failures; do not add broad
   stale-temp deletion.

## Verification required before stopping

- Golden semantic parity and malformed/oversized fail-closed tests.
- Atomic callback, partial-write, fsync, replace, directory-fsync, cleanup, and
  descriptor-stability fault tests.
- Concurrent replacement/in-place mutation and export-lock contention tests.
- SQLite/ENOSPC failures leaving the original byte-identical.
- Fresh-process duplicate-heavy and unique-heavy 16/64/128 MiB measurements:
  all below 512 MiB peak RSS; the 128 MiB case no more than 96 MiB above import
  baseline; report throughput and output hashes/counts.
- Governed-writer inventory regeneration, `ingest.export` census continuity,
  intentional Arc Codex `ingest.py` baseline/VERIFY refresh, and proof that
  default-off/live denial did not change.
- Focused suites, repo-wide pytest, compileall, `git diff --check`, scoped
  pylint, and the repository pylint regression gate.

## What not to build or do

- No append-aware watcher ingestion, Chroma/brief optimization, timeout,
  cooldown, retry, debounce, exclusion, systemd, or memory-cap changes.
- No production export/source/config/provider access or compaction.
- No watcher operation, source re-inclusion, purge, Gate 0, Arc Codex P2,
  grant/digest, activation, PR, or merge.
- Do not claim this slice alone closes the flat 12.5 GiB OOM; it removes one
  proven corpus-sized accumulator. Remaining stacking must be evaluated later.
- Do not invoke Claude. Stop after the pushed exact-tip handoff.

## Return

Report branch, exact implementation/evidence SHAs, push status, tests and
memory measurements, changed governed surfaces, and negative confirmation.
Route next to the GitHub Copilot audit lane for the targeted safety review
specified in plan §9—not directly to Kiro or PR.

I finished: [Arc Trapdoor Hunt / issue #268] bounded Cursor Execute authorization
Next step: Cursor implements C0–C7 in a fresh worktree and stops at a pushed tip
Next lane: Cursor — implementation only
See my work: `docs/plans/EXECUTION-watch-oom-bounded-export-compaction.md`

**TL;DR:** Ryan authorized Cursor C0–C7 against Kiro-PASSed plan `36f9069…`;
implement hermetically, push the exact tip, and stop without PR or live action.
