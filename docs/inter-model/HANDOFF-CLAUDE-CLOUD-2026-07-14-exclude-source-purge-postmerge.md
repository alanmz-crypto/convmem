# Handoff: Exclude `--purge` post-merge idea review

**Date:** 2026-07-14
**From:** Ryan + Codex
**To:** Claude Cloud
**Purpose:** Update Claude on the exclude-source-purge plan he helped inform, then solicit genuinely new post-merge ideas. This is a strategy review only: **no code edits, live corpus mutation, merges, records, or external writes.**

## Read order

1. `docs/plans/ARCHITECTURE-exclude-source-purge.md`
2. `docs/plans/EXECUTION-exclude-source-purge.md`
3. `docs/plans/VERIFY-exclude-source-purge.md`
4. Only if needed to test a concrete claim: `source_purge.py`, `purge_locks.py`, and `exclude_cli.py`

The merged plan is the source of truth. Shared memory currently does not surface a Claude-labeled excerpt for the original review, so do not reconstruct prior advice from memory alone.

## Final state

- Ryan accepted gates 1–12, Design A, the three-lock hierarchy, and logical-not-forensic scope.
- PR #29, `feat: exclude --purge (logical source deletion)`, merged as `9e01f58`.
- PR #30 reconciled all Architecture, Execution, and Verification status markers and merged as `fb43050`.
- Cursor implemented the plan; Codex independently audited several revisions before approval.
- Final independent gate: focused purge/limit semantics passed; full suite **476/476**; unchanged Pylint regression gate and GitHub CI passed.

## What shipped

- `convmem exclude PATH --purge`, with default-No confirmation and `--yes` automation.
- Logical removal from Chroma knowledge units, Chroma summaries, and `knowledge_units.jsonl`.
- Marker-first exclusion plus a per-source fence so an in-flight writer cannot repopulate a successfully purged source.
- Ordered source, export, and processed-state locking; all six JSONL writers share the export lock.
- Read-only preview separated from mutation; preview does not create Chroma collections, lock files, WAL/SHM files, or directories.
- One shared exact-path candidate contract across preview, both purge sinks, and postcondition counts.
- Synthetic `purged:<sha256(path)>` markers for missing files; undo clears all same-path markers but does not resurrect deleted rows.
- Fail-closed malformed JSONL handling, atomic rewrites, cache invalidation, retry convergence, and zero-count postconditions.
- Production-event concurrency tests for ingest/purge, undo/purge, inter-model ingest, and the JSONL postcondition window.
- The ingest refactor was corrected to preserve pre-refactor `limit_files` and `files_skipped` behavior.

## Accepted limits — do not report these as newly discovered

- Purge is logical, not forensic. Chroma free pages, filesystem blocks, and existing Restic snapshots may retain bytes.
- Query-side exclusion filtering during the brief purge window is out of scope.
- Multi-machine coordination, Chroma compaction timing, and performance benchmarking are out of scope.
- Plain `exclude` remains a soft fence; destructive removal requires explicit `--purge`.

## What changed after the initial design

The plan absorbed 12 review amendments and three HOLD corrections. Implementation audit then fixed configured lock identity for inter-model ingest, undo/purge serialization, canonical missing-file markers, rejection of non-filesystem targets, real production-event race tests, restoration of the exact PR #28 Pylint gate, and the ingest skip/limit regression.

Do not re-open those settled points without a concrete counterexample against the merged behavior.

## Questions for Claude

1. **Defense in depth:** Is query-time filtering of actively excluded paths worth a follow-up, or would it create a second policy path and hide purge failures? If useful, identify the narrowest design that keeps postcondition failure observable.
2. **Replay and restore:** Could restoring `processed.json`, Chroma, or an older snapshot silently revive a logically purged source? Propose the smallest durable fence or recovery check that fits convmem's single-host leader/follower model without claiming forensic erasure.
3. **Drift detection:** Should `convmem doctor` detect rows whose source is actively excluded, or would that be too expensive/noisy? Define a bounded probe if you recommend one.
4. **Safe observability:** Is a content-free purge receipt useful—source-path hash, sink counts, timestamps, result only—or is the current exclusion marker enough? Avoid designs that copy sensitive payloads into a new audit artifact.
5. **Module depth:** After seeing the shipped boundaries, is the source/export/processed lock hierarchy hidden deeply enough, or is there a simpler unit-of-work/repository boundary that reduces coupling without weakening the race proof?
6. **Next risk:** Name any material failure mode not already covered by N1–N21, V1–V24, B1–B7, and the accepted limits. Include a deterministic reproduction or invariant, not a generic concern.

## Expected output

Return concise Markdown only:

1. **Post-merge verdict:** no follow-up needed, or follow-up warranted.
2. **New ideas:** at most five, ranked `now`, `next`, `later`, or `decline`.
3. For each recommended idea: the concrete failure/invariant, smallest safe change, and one deterministic verification.
4. **Best single follow-up:** one bounded task suitable for a new plan, or `none`.

Do not summarize the existing architecture, propose a rewrite, or turn accepted logical purge into forensic deletion.

## Claude prompt

> Review the merged exclude `--purge` architecture as a post-implementation strategist. Read Architecture, Execution, and Verification in that order. Treat gates 1–12, Design A, the three-lock hierarchy, and logical-not-forensic scope as accepted. Identify only genuinely new ideas or concrete residual failure modes, especially around defense-in-depth, restore/replay, drift detection, content-free observability, and module depth. Rank at most five ideas and give the smallest safe change plus one deterministic verification for each. End with the best single follow-up or `none`. Markdown only; no code, live corpus mutation, merge, record, or external writes.
