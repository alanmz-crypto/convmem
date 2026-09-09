# ConvMem Scratch Prototype — Claude Final Check

> Status: **PASS WITH CONDITIONS** — Claude has approved a narrowly bounded Cursor Execute grant after the conditions in this document are incorporated. Disposition remains B: bounded scratch prototype first.

## My current decision

I accept Disposition B. We should not enable incremental indexing in production yet, resume broad watcher activity, process `.crush/crush.db` incrementally, use paid providers, or modify the live corpus.

The next step should be a small, isolated scratch prototype that proves the safety-critical behavior the audit could not establish statically.

## Proposed scratch prototype

### Scope

- One append-only JSONL adapter only.
- Prefer `jsonl_kiro_session` or `jsonl_cursor` because their format detection is path-pattern-relative and can be exercised with a correctly named scratch fixture.
- Do not include SQLite, `.crush`, Codex home-anchored detection, production routing, or real-source indexing.
- Extend the existing `tests/test_safe_file_reindex.py` and `tests/purge_test_util.py` hermetic harness rather than creating new isolation plumbing.

### Safety boundary

- Fresh temporary root for source fixtures, Chroma, checkpoints, exports, inventory, and locks.
- A pre-import isolation bootstrap establishes the scratch-only environment before importing any ConvMem module that could resolve configuration or initialise infrastructure.
- Dedicated subprocess for crash tests with a sanitised scratch-only environment, no inherited production paths or provider credentials, and independent child-tree/lock containment.
- Deterministic fake summarisation, embeddings, and deduplication.
- No paid provider, no nonlocal endpoint, and no network for the ordinary suite.
- Production paths and locks rejected before client/resource construction.
- Mutable resources and fixtures use canonical resolved-path containment beneath the fresh temporary root; no symlinks, aliases, `..` paths, or production-default fallbacks are permitted.
- The first executable prototype substep mechanically proves all mutable resources resolve beneath the fresh temporary root, production configuration cannot override them, paid/nonlocal provider construction fails, and ordinary execution cannot make outbound network connections.
- Existing production services remain untouched and are not used by the prototype.

### Required prototype evidence

1. Initial full scratch ingest.
2. Single and multiple appends.
3. Partial trailing record and completion on the next run.
4. Exact chunk-boundary append.
5. Prefix mutation, truncation, and source replacement fallback.
6. Transform-fingerprint change fallback.
7. Crash before output, during output, after output but before checkpoint, and immediately after checkpoint.
8. Replay after every crash.
9. Incremental/full scratch equivalence for source coverage, authoritative IDs, provenance, boundaries, duplicates, and checkpoint meaning.
10. Call counters proving unchanged historical work is reused and work scales with the affected dependency frontier.
11. §3B units-in-flight memory profiling in scratch only.
12. Crash after some upserts but before all outputs.
13. Crash immediately before prune, during/after prune, and before completion/checkpoint.
14. Interruption or torn state while persisting checkpoint/processed state.
15. Crash during full-rebuild fallback before authoritative completion.
16. Append after the selected high-water point and mutation inside the validated prefix while the run is active.
17. Abrupt failure immediately before and after every durable authority transition introduced or discovered by the prototype, including activation/publication, prune epochs, fallback markers, cleanup, locks, and checkpoints.
18. Stale-lock recovery and retry after the crash subprocess dies while holding a scratch lock.

### Success condition

For every valid fixture state and crash/retry history, incremental processing must converge to the same authoritative scratch result as a clean full rebuild, without lost records, duplicate authoritative units, mixed generations, or falsely advanced completion state.

No live or paid canary is part of this prototype.

## What I believe Claude’s audit established

- The current `main` branch contains no implementation of the proposed append cursor, tail fingerprint, or append capability.
- The current watcher still performs full-source work on a changed source.
- Existing unit IDs are deterministic enough to justify testing reuse, but compatibility with incremental provenance and pruning still needs execution evidence.
- Existing scratch integration tests provide reusable Chroma, lock, configuration-patching, and fake-model patterns.
- The existing full-rebuild sequence performs live upserts, pruning, and processed-state completion separately; crash atomicity is not established.
- JSONL can validate the incremental state machine without touching the currently watched SQLite source.
- The active `.crush` source remains a separate cost problem and must not be silently treated as fixed by JSONL success.
- The prototype should take roughly 1–3 focused sessions, but this is a provisional estimate with medium confidence.

## Claims I want Claude to challenge again

| ID | Claim | What would change the decision |
|---|---|---|
| F1 | The existing scratch harness is safe to extend without opening production resources. | Any indirect config, lock, Chroma, export, or provider initialization path that escapes the temporary root. Isolation must be mechanically verified before the first incremental test. |
| F2 | A dedicated subprocess is sufficient for crash testing. | Any shared process, lock, environment, or child resource that could still affect production after the test subprocess is killed. The environment, file descriptors, process group, descendants, and scratch locks must be sanitised and contained. |
| F3 | Deterministic fakes are enough for the required correctness gate. | A correctness property that depends on real model semantics rather than deterministic inputs, identity, storage, or state transitions. |
| F4 | Kiro or Cursor JSONL is the correct first adapter. | No real supported adapter/fixture path, or evidence that the shared contract cannot be tested without Codex or SQLite-specific behavior. The fixture must traverse normal format detection and adapter dispatch end-to-end. |
| F5 | The prototype can use the existing full-rebuild path as a scratch oracle. | Any helper construction that can resolve production config, acquire production locks, open production Chroma, or call providers. The oracle must use the same mechanical isolation boundary and identical source, adapter, transform, dedupe, and storage inputs as the incremental path. |
| F6 | The expanded crash matrix plus transition-derived cases is sufficient to reach a meaningful readiness decision. | A durable authority transition or failure window is omitted and could still lose, duplicate, mix, prune, or falsely complete authoritative state. |
| F7 | Call counters plus synthetic scaling are enough for the zero-cost incrementality gate. | Evidence that the algorithmic work cannot be measured without real provider calls or production data. |
| F8 | `.crush` can remain paused/full-rebuild-only while JSONL is developed. | Evidence that this creates unrecoverable source loss or that the active SQLite path must be included to make the first slice meaningful. Resume/reconciliation safety remains a separate gate. |
| F9 | The 1–3-session estimate is a reasonable prototype estimate. | Any missing existing infrastructure or fault-injection work that materially expands the prototype; re-estimate if prune/publication or subprocess isolation requires new infrastructure. |
| F10 | Passing the prototype should lead to another independent review, not a canary. | Any evidence that synthetic scratch results establish production isolation, economics, semantic quality, SQLite safety, or watcher-resume safety. |

## Questions for Claude

1. Is this prototype boundary genuinely zero-production-indexing and zero-paid-provider?
2. Is the existing test harness a trustworthy foundation, or should isolation guards be added before any incremental code?
3. Is the adapter choice sound, given the active `.crush` SQLite source?
4. Is the crash/fault matrix complete enough for the first scratch gate?
5. Does the success condition correctly capture convergence, replay, identity, pruning, and completion safety?
6. What must be added before Cursor receives an Execute grant?
7. Is any claim above too strong and should be downgraded to `inferred` or `unknown`?
8. Is the 1–3-session estimate defensible for this bounded prototype?

## Required verdict format

### Overall verdict

`PASS`, `PASS WITH CONDITIONS`, or `FAIL`

State whether this proposal is safe to carry into a Cursor Execute grant for the isolated scratch prototype.

### Claim verdicts

| ID | Verdict (`agree` / `refute` / `restate`) | Reasoning | Corrected formulation if needed |
|---|---|---|---|
| F1 |  |  |  |
| F2 |  |  |  |
| F3 |  |  |  |
| F4 |  |  |  |
| F5 |  |  |  |
| F6 |  |  |  |
| F7 |  |  |  |
| F8 |  |  |  |
| F9 |  |  |  |
| F10 |  |  |  |

### Required corrections or blockers

List only changes required before the Execute grant or before interpreting prototype results.

### Execute-grant boundary

State exactly what Cursor may implement and what remains prohibited.

### Confidence

State `high`, `medium`, or `low`, with the dominant remaining uncertainty.

## Review boundary

This is a final design check only. Do not modify ConvMem, run tests, index sources, call providers, change services, access production data, mutate the corpus, or issue an Execute grant.

## Claude-approved Execute boundary

After the isolation-first conditions are verified, Cursor may work only in an
isolated ConvMem worktree/branch and may:

- extend the existing hermetic scratch-test infrastructure;
- add production-path, provider, network, and lock guards for the prototype;
- select one supported append-only JSONL adapter through normal scratch format detection;
- implement only source/generation identity, complete-record boundary, continuity validation, transform fingerprint, checkpoint/commit state, deterministic replay-safe identity, calculated invalidation frontier, fallback reason, scratch continuation, and scratch full-rebuild fallback;
- add the expanded crash/replay matrix;
- derive additional abrupt-failure points from every durable authority transition discovered during implementation, not only from the named matrix;
- verify canonical path containment, pre-import isolation, sanitised process-tree behavior, and stale-lock recovery;
- compare incremental output with clean scratch rebuild output;
- collect scratch-only call counters and memory evidence;
- produce an evidence handoff for independent review.

Cursor remains prohibited from production Chroma, corpus, processed state,
inventory, exports, locks, watched sources, `.crush` or SQLite incremental work,
watcher resume/reconfiguration, paid or nonlocal providers, ordinary network
access, live/real-source canaries, production pruning/migration, and treating
prototype success as production authorization.

## GPT conditions incorporated

The Execute grant must state explicitly that:

- isolation begins before ConvMem imports or application initialization;
- containment uses canonical resolved filesystem paths and fresh resources, not lexical prefixes or symlinked fixtures;
- crash subprocesses contain inherited file descriptors, working directory/config discovery, descendants, process groups, and stale scratch locks;
- the mandatory fault matrix is extended around every durable authority transition introduced or discovered;
- incremental and full-rebuild oracle inputs are frozen and authoritative comparison fields are not normalised away;
- prototype PASS authorises independent evidence review only, never a live/paid canary or production routing.
