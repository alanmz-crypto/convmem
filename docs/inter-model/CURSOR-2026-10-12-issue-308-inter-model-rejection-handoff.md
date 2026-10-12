# Implementation Handoff: stop the #308 inter-model rejection retry loop

**Arc: Codex (#286), Stage 2 prerequisite.** (Issue #308.)
**Date:** 2026-10-12
**Author:** Claude (Opus 5.5), from Codex's read-only design analysis
(2026-10-12)
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-10-12. Ryan granted "#308 fix: turn Codex's
design into a Cursor handoff" as a Stage 2 prerequisite of the Codex burn
work.

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `fix/2026-10-12-issue-308-inter-model-rejection` (create from `origin/main`) |
| **Tip SHA** | base `origin/main` `05aa2c8` |
| **Push status** | handoff pushed on `docs/2026-10-12-issue-308-inter-model-rejection-handoff` |
| **PR** | not opened |
| **Ryan GATE** | none for hermetic implementation; Ryan alone merges |
| **Track A ingest** | your Cursor transcript, at handoff |

## What to build

**Why this exists:** some `docs/inter-model/*.md` files fail the inter-model
provenance-supersession guard. Each one is then re-attempted on every
watcher cycle, all day, with no content change. One doc had 282 spawn
attempts on 2026-09-18, and inter-model docs caused 3,315 spawns from
Sep 26 to Oct 5. There are no paid calls, but every attempt spawns a child
and repeats local embedding work before the guard rejects again.

This has to be fixed before the 24 h watcher canary (Stage 2), the step
that brings back automatic capture without the Codex burn.

**The defect** (confirmed by Codex and Claude at `05aa2c8`):

- The provenance guard raises `InterModelIndexError`
  (`inter_model_index.py:95–121`, message at `:119`).
- `_index_inter_model_file` (`ingest.py:716–756`) catches every exception
  and returns a failure.
- At `ingest.py:~1415–1433`, that failure becomes `"skipped"` before
  `commit_processed_index_entry` (`:1447`). `processed.json` therefore never
  records the file, and the next event retries the same bytes.
- A correction from Codex: on `main`, the watcher doesn't consume the
  reconciler's queued work. Retries come from filesystem events through
  `flush_path` (`watch.py:~438–508`). The reconciler still reports these
  docs as `new_eligible_source` (`source_reconciler.py:146–155`).

**The fix:** record a terminal rejection for that exact content. Skip that
`(canonical path, full-file SHA-256)` pair in the watcher and the reconciler
until the bytes change.

## Integration points

1. `inter_model_index.py:~118`: give the provenance-supersession guard a
   distinct typed outcome, for example a subclass
   `InterModelSupersessionRequired(InterModelIndexError)`. Every other
   failure keeps its current type.
2. `ingest.py:716–756` (`_index_inter_model_file`) and `:~1415–1433`: carry
   that typed outcome through. Record the rejection with the full
   `file_hash` the caller already computes (`ingest.py:~1331–1346`). Return
   `"skipped"` exactly as today.
3. `ingest.py:509` (`watch_skip_reason`, called at `watch.py:476`): skip with
   a distinct reason, such as `inter_model_rejected`, when the current path
   and hash match a recorded rejection. Do this before any child is spawned.
4. `source_reconciler.py:121` (`discover_legacy_source_drift`): don't report
   a path whose current hash matches its recorded rejection. Report it again
   as soon as the hash differs.

## Specification

- **Storage:** a dedicated sidecar next to `processed.json` (for example
  `inter_model_rejections.json`). **Not** in `processed.json`, and **not**
  in the watcher circuit breaker or refusal quarantine.
  - That quarantine is path-wide and terminal by design (Codex D3), whereas
    this record must release when the content changes.
  - Each record holds the canonical path, the full-file SHA-256, the
    rejection kind (`provenance_supersession_required`), a UTC timestamp,
    and the guard's section id.
  - Writes are atomic (temp file plus rename, under the existing writer
    lock if one applies).
- **Writer:** only the typed provenance-supersession outcome writes a
  record. Embedding failures, I/O errors, parse failures and any other
  exception must stay retryable, and must write nothing.
- **Readers:** `watch_skip_reason` and `discover_legacy_source_drift`. A
  match requires the same canonical path and the same current hash.
  - The same bytes at a different path are not suppressed.
  - A changed hash is eligible at once.
- **Failure mode:** a corrupt or unreadable sidecar **fails open**. It
  suppresses nothing, so retries resume, and it prints one visible
  diagnostic. It never crashes the watcher or the reconciler.
- **Clearing:** a record clears itself when the content changes. Also add a
  small explicit clear path for the case where an operator resolves
  supersession without changing the bytes, such as
  `convmem exclude --undo`-style tooling, or a documented one-line
  procedure. Keep it minimal.
- **Constants:** none new. Use the existing hash function and path
  canonicalization.

## What NOT to build

- No change to the provenance guard's policy, to supersession semantics, or
  to the Chroma and export projection.
- No change to watcher scheduling or debounce, to the native-crash and
  timeout thresholds, or to the Codex refusal quarantine
  (`watch_circuit_breaker.py`). Don't count this skip as a crash.
- No `processed.json` schema change, and no new config keys.
- No live index runs, watcher start, provider calls, or edits to live data.
  Tests are hermetic only.

## Test expectations

All hermetic. Each of the first four must fail on `main` `05aa2c8`:

1. A provenance-guard rejection records the exact path and hash, returns
   `skipped`, and leaves both `processed.json` and the existing Chroma
   projection unchanged.
2. `watch_skip_reason` skips the rejected path and hash before a child
   spawns. After the file changes, it allows the new hash.
3. Reconciliation no longer reports the rejected path and hash, and reports
   it again after the content changes.
4. Repeated events on unchanged bytes produce zero further index attempts.
5. An embedding error, or any other non-guard exception, records nothing
   and stays retryable.
6. The same bytes at a different path aren't suppressed, and one path's
   rejection doesn't suppress another path.
7. A corrupt sidecar fails open with one diagnostic. Concurrent writes and
   reads don't lose records.

## Acceptance criteria

- [ ] Integration points 1–4 are implemented, and each test above is mapped
      to its name in the handoff-back.
- [ ] From a clean, disk-backed checkout with a fresh CI config:
  - the full-suite summary line (only the known #320 golden-eval failure
    allowed);
  - the exact Pylint regression-gate command, with `--base-ref` set to the
    merge base, plus its final line.
- [ ] No committed reports and no leftover worktrees. Pushed with an
      explicit refspec; no force-push, no rebase. If `main` moves, merge it.
- [ ] The handoff-back covers the tip SHA, `git show --stat` for each
      commit, and the test mapping.

## Branch convention

Run `convmem work start fix issue-308-inter-model-rejection --worktree`.
Then push every commit with `git push origin "${B}:refs/heads/${B}"`.

## Next after implementation

Claude verifies the tip. Then the Copilot audit (targeted:
isolation/fail-open) and the Kiro review run on the exact tip, and Ryan makes
the PR decision. Only after that is merged does the Stage 2 watcher canary
get its grant.
