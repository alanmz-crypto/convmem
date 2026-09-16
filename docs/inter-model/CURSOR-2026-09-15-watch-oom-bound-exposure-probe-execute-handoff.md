# Cursor Execute Handoff — Bound the exposure-window probe

**Arc:** Trapdoor Hunt (issue #268 operational follow-up; closed provenance T3
remains closed)

**State:** `BLOCKED_ON_RYAN`. Kiro PASSed the plan, but Ryan has not yet issued
the separate Cursor Execute grant. This document is routing, not authority.

**Goal:** Stop the standing exposure-window probe from loading unused
provenance envelopes during brief refresh while preserving every current
due/not-due result and detail string.

**Cursor role:** After Ryan explicitly authorizes Execute, implement only C0–C7
from the reviewed plan, verify hermetically, push an immutable tip, and stop for
GitHub Copilot audit. Do not open a PR.

**System currently:** PR #303 is merged on `main` as
`5c103aa2f11f54de74be3a7eab90c433c0c019cd`. It made the main brief aggregate
projected and memory-bounded. The post-merge diagnostic isolated the remaining
envelope-sized reader in `doctor._exposure_window_probe()`, which still creates
a full `ReadonlyUnitStore`.

**Next action:** Ryan issues the exact Execute authorization below. Cursor then
starts from this handoff's authorization descendant, not from an older plan tip.

## Reviewed authority basis

- Kiro-PASSed plan tip:
  `5672ee98b93b6d71db5d80bc34f189f1c13460eb`
- Plan:
  [`docs/plans/EXECUTION-watch-oom-bound-exposure-probe.md`](../plans/EXECUTION-watch-oom-bound-exposure-probe.md)
- Runtime baseline: `origin/main` at
  `5c103aa2f11f54de74be3a7eab90c433c0c019cd`
- Kiro verdict: unconditional PASS on the exact plan tip in a clean detached
  worktree.

## Required Ryan authorization

The following or an unambiguous equivalent must appear after this handoff:

```text
Authorize Cursor Execute C0–C7 for the bounded exposure-window probe against
Kiro-PASSed plan tip 5672ee98b93b6d71db5d80bc34f189f1c13460eb.
Hermetic implementation only; push exact evidence and stop for Copilot. No PR,
production access, watcher/config operation, or Arc Codex Gate 0/P2.
```

Until that grant exists, do not create the implementation branch or edit code.

## Implementation workspace after authorization

Use a fresh Cursor Composer chat and a fresh worktree. The authorization commit
must descend from plan tip `5672ee9` and contain this handoff on disk.

Planned branch:

```text
impl/2026-09-15-watch-oom-bound-exposure-probe
```

Planned worktree:

```text
~/Projects/convmem-watch-oom-exposure-probe
```

Create it from the pushed authorization branch/tip named by Ryan's grant, not
from bare `origin/main`, so the reviewed plan and handoff are present.

## Binding implementation contract

### Exact projected output union

```text
id, ledger_id, ledger_kind, type, relates_to, timestamp, result,
verification_result, severity, superseded
```

`id` comes from `embedding_id`. The other nine fields are the SQLite metadata
allowlist. Use `include_document=False`.

Forbidden on this path:

- `document` / `chroma:document`;
- `provenance_envelope`;
- `provenance_commitment`;
- `provenance_assertion_id`;
- every other metadata key not listed above;
- `open_readonly_unit_store()`;
- `collection_metadata_rows()`;
- provenance-identity filtering;
- mutation of `_LEDGER_INDEX_CACHE`.

### Required semantics

- Drop a row only when `row.get("superseded") is True`.
- Do not add `deleted` as an exclusion rule.
- Use `build_ledger_index_from_metadata()` without the process cache.
- Preserve last-value/first-position duplicate-ledger behavior and current
  embedding-id ordering.
- Preserve `evidence_boost()`, `OPEN_STATUSES`, close-date precedence, exact
  boolean results, and exact detail strings.
- Let read/query errors reach the existing standing-register fail-soft boundary
  as `probe error: <ExceptionType>`.
- No retry or fallback to a full-row read.

## Execute sequence

- **C0:** Freeze exact exposure-window and standing/brief outputs before code
  changes.
- **C1:** Route only `_exposure_window_probe()` through the closed projected
  iterator and non-caching metadata index.
- **C2:** Prove semantic parity, including duplicate/equal-date and lifecycle
  cases.
- **C3:** Prove projection closure and trap every forbidden store/list/cache
  path.
- **C4:** Prove iterator cleanup and existing fail-soft behavior under injected
  failures.
- **C5:** Prove pre-import production-path/network denial and unchanged
  canaries using only temporary resources.
- **C6:** Run 5k/20k/58,825-unit memory evidence and the 2 KiB/32 KiB envelope
  comparison under the plan's thresholds.
- **C7:** Run affected/full verification, refresh only derived evidence that
  genuinely drifts, commit, push, and stop for Copilot.

## Scope lock

Do not change:

- the PR #303 brief aggregate or its 19-field projection;
- `evidence_boost()`, `OPEN_STATUSES`, standing-register policy/data, or public
  ledger semantics;
- provenance storage/authority, ingestion, export compaction, Chroma/HNSW,
  providers, thread settings, memory caps, watcher policy, or exclusions;
- production config/data/brief, watcher/systemd state, Arc Codex Gate 0/P2,
  grants, digests, or activation.

No live profiling or production read is authorized. The prior diagnostic's
temporary harness may inform fixture shape but is not production authority.

## Required return

Return:

- implementation branch and exact pushed tip;
- preserved authorization ancestor;
- C0–C7 change/test mapping;
- focused, full-suite, compile, diff, and Pylint results;
- 5k/20k/58,825 memory table and envelope-size delta;
- explicit negative confirmation;
- easiest exact diff;
- stop statement: **Copilot next, no PR and no Kiro yet**.

## Copy/paste prompt after Ryan authorization

```text
Resume Arc Trapdoor Hunt bounded exposure-window probe Execute (C0–C7).

Read:
- docs/inter-model/CURSOR-2026-09-15-watch-oom-bound-exposure-probe-execute-handoff.md
- docs/plans/EXECUTION-watch-oom-bound-exposure-probe.md

Use a fresh Cursor Composer chat and create
impl/2026-09-15-watch-oom-bound-exposure-probe in
~/Projects/convmem-watch-oom-exposure-probe from the exact pushed
authorization tip named by Ryan.

Implement C0–C7 hermetically. Push an exact tip and stop for GitHub Copilot's
targeted audit. No PR, production access, watcher/config change, or Arc Codex
Gate 0/P2.
```

## TL;DR

- Kiro PASSed plan tip `5672ee9`; implementation still requires Ryan's separate
  grant.
- After authorization, Cursor replaces only the exposure probe's full store
  with the exact ten-field projected iterator and preserves all current
  evidence/lifecycle/fail-soft semantics.
- Hermetic semantic and full-corpus memory proof are mandatory.
- Push and stop for Copilot; no PR or operational action.
