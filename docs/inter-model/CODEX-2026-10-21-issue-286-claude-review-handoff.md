# [Arc Codex #286] Claude review request — forward processed-publication fence

**Requested reviewer:** Claude Code, independent review lane
**Requesting lane:** OpenAI Codex
**Date:** 2026-10-21 UTC
**Purpose:** review the exact implementation tip before Ryan decides whether to open and merge a PR.

## Review-confidence warning

During this work I inadvertently switched models and lost the prior model's cache and
working context. That means this implementation and the preceding reasoning may be
weaker than intended. Please treat that as a real uncertainty signal: independently
verify the exact code, call-site census, lock reasoning, test claims, and conclusions.
Do not accept the existing Codex or Kiro summaries as a substitute for your own review.

## Exact target

- **Implementation branch:** `fix/2026-10-21-issue-286-forward-publication-cas`
- **Exact tip:** `e6ce3c46aaa250d69129f519eba97bc2be874265`
- **Previous audited tip:** `ec7b8a55bb6a21c61089d69c025f1116e5b17239`
- **Previous audit result:** FAIL, Finding 1 — the incremental path released
  `source_flock` before `_publish_processed` and `_cleanup`, allowing a same-source
  legacy/manual/Track A writer to race and then be purged.

Review the exact tip, not the current `main` checkout. The requested comparison is:

```text
ec7b8a55bb6a21c61089d69c025f1116e5b17239..e6ce3c46aaa250d69129f519eba97bc2be874265
```

## Claimed correction to verify

The correction claims to:

1. Keep the existing per-source `source_flock` held through `_publish_processed` and
   `_cleanup` in `incremental_jsonl.py`.
2. Add `commit_processed_index_entry_fenced` in `ingest.py`, wrapping the low-level
   processed-sidecar mutation in the same source fence.
3. Route all three generic `_index_one_file` processed-publication branches through the
   fenced helper.
4. Add a deterministic late same-source writer regression proving exclusion during
   final publication and survival of a later publication.
5. Refresh the production canary hashes for the changed implementation files.

Relevant regions at the claimed tip are approximately:

- `incremental_jsonl.py:2608` — low-level processed publication;
- `incremental_jsonl.py:2707` and `2855-2866` — source fence, publication, cleanup;
- `ingest.py:432-459` — fenced helper;
- `ingest.py:1547`, `1592`, and `1651` — generic publication branches;
- `tests/test_issue_286_rollback_fresh_before_image.py:844-908` — late-writer regression;
- `tests/test_incremental_jsonl_canary_baseline.py` — refreshed implementation pins.

## Review questions

Please answer each question from the exact tree:

1. Is every processed forward-publication route covered, including recovery,
   legacy/manual calls, Track A, generic indexing, and any less-obvious caller?
   Identify every bypass or state explicitly that the census is exhaustive.
2. Is the lock order safe across `source_flock`, `index_write_flock`, processed-sidecar
   locks, and any other relevant lock? Check non-reentrancy, nested calls, and
   cross-source deadlock possibilities.
3. Does the fence accidentally enclose provider, network, Chroma-write, or other
   unbounded work? Does it change rollback authority, refusal behavior, or cleanup
   semantics?
4. Does the new regression genuinely fail on the old tip and prove both properties:
   a same-source writer cannot publish during recovery finalization, and a later writer
   survives after the fence is released? Assess timing/flakiness.
5. Are rollback, refusal, cleanup, production-inertness, canary pins, and existing
   guarded-route behavior preserved?
6. Are the reported test results and prior conclusions accurate? Identify missing tests,
   overclaims, or scope limits.

## Review constraints

- Review exact tip `e6ce3c46aaa250d69129f519eba97bc2be874265`.
- Do not modify production code, tests, scripts, configuration, generated files, or
  runtime state.
- Do not call paid providers, external networks, live Chroma, or production stores.
- Run only safe local deterministic checks if available; record exactly what ran.
- Do not open, merge, force-push, or otherwise change a PR.

## Existing evidence — verify independently

- Codex independently ran the focused issue-286 rollback/state/canary and stage-2
  corrective matrix: **116 passed** at the exact tip.
- The exact-tip Codex audit reported PASS after the earlier Finding 1 correction.
- Kiro performed a separate read-only static review and reported PASS, but could not run
  shell-based tests or recompute the canary hashes in its non-interactive session.

## Required deliverable

Return an explicit verdict: **PASS**, **PASS-WITH-CHANGES**, or **FAIL**.

Include numbered findings with severity and precise file/line references, tests actually
run, limitations, and whether the model-switch/cache-loss warning changes confidence.
If the verdict is not PASS, identify the smallest safe next action and lane. End with:

```text
I finished: [phase]
Next step:  [specific action]
Next lane:  [owner]
See my work: [single easiest path]
```

<!-- src: /home/lauer/.local/share/convmem/worktrees/docs-2026-10-20-issue-286-forward-publication-cas-audit/docs/inter-model/CODEX-2026-10-21-issue-286-forward-publication-cas-audit.md — exact-tip Codex audit evidence -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex status and review routing -->
