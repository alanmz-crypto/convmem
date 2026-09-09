# ConvMem Scratch Prototype — GPT Independent Final Check

> Status: **independent review requested** — Claude returned `PASS WITH CONDITIONS` for a bounded scratch prototype, Disposition B. Please provide an independent adversarial check before a Cursor Execute grant is issued.

## Review question

Is the proposed scratch prototype sufficiently isolated, bounded, and testable to proceed with **zero production indexing, zero paid-provider calls, and no live corpus mutation**?

Challenge the proposal independently. Do not edit ConvMem, run tests, index sources, access production resources, change services, call providers, or issue an Execute grant.

## My current position

I accept the following constrained next step:

- implement only a scratch prototype for one append-only JSONL adapter;
- prefer `jsonl_kiro_session` or `jsonl_cursor` if normal scratch format detection can be exercised end-to-end;
- exclude SQLite and `.crush/crush.db` entirely;
- extend the existing hermetic scratch harness only after mechanically proving its isolation;
- use deterministic fake summarisation, embeddings, and deduplication;
- use a fresh temporary root for source, Chroma, checkpoints, exports, inventory, and locks;
- run crash tests in a dedicated subprocess with a sanitised environment and contained child tree;
- deny paid/nonlocal providers and ordinary outbound network access;
- retain full-rebuild fallback only inside the scratch isolation boundary;
- do not route production traffic, resume the watcher, alter services, migrate data, or run a real-source canary.

This is a provisional implementation hypothesis, not production authorization. The provisional estimate is **1–3 focused sessions**, with medium confidence.

## Required first executable step

Before any incremental or oracle test runs, the prototype must mechanically demonstrate that:

- every mutable path resolves below the fresh temporary root;
- production Chroma, checkpoints, inventory, exports, locks, watched sources, and `.crush` are rejected before client/resource construction;
- production configuration/default discovery cannot override scratch paths;
- paid or nonlocal provider construction fails;
- ordinary prototype execution cannot make outbound network connections;
- the test subprocess and any descendants cannot affect production state.

If this step cannot be proven, stop before implementing incremental logic.

## Required prototype scope

The scratch implementation may include only:

1. source/generation identity;
2. complete committed record boundary;
3. prefix/continuity validation;
4. transform fingerprint;
5. checkpoint/commit state;
6. deterministic replay-safe derived identity;
7. calculated dependency invalidation frontier;
8. explicit fallback reason;
9. scratch incremental continuation;
10. scratch full-rebuild fallback;
11. deterministic fake transforms and observable call counters;
12. fault/replay tests and scratch-only memory profiling.

## Required evidence

The prototype must cover:

- initial full scratch ingest;
- one and multiple appends;
- partial trailing record;
- exact chunk-boundary append;
- prefix mutation;
- truncation;
- source replacement/rotation;
- transform-fingerprint change;
- append after selected high-water point;
- mutation inside the validated prefix during a run;
- crash before output;
- crash after some but not all upserts;
- crash immediately before prune;
- crash during/after prune but before completion/checkpoint;
- interruption while persisting checkpoint/processed state;
- crash during fallback before authoritative completion;
- crash immediately after checkpoint commit;
- replay after every crash.

For every valid fixture state and crash/retry history, compare incremental processing with a clean scratch full rebuild for:

- source-record coverage;
- authoritative unit IDs;
- provenance;
- chunk/summary boundaries;
- duplicate count;
- checkpoint meaning;
- mixed-generation or premature-completion exposure;
- parser/transform/reuse/fallback counters.

The success condition is convergence without lost records, duplicate authoritative units, mixed authoritative generations, or falsely advanced completion state. Work for a small append must scale with the calculated invalidation frontier, not total historical source size.

## Claims for independent challenge

| ID | Claim | Failure condition |
|---|---|---|
| G1 | The existing scratch harness can be safely extended. | Any runtime path can escape the temporary root or construct a production resource before guards run. |
| G2 | Dedicated subprocess plus sanitized environment is sufficient for crash tests. | Descendants, locks, inherited state, or cleanup can affect production after termination. |
| G3 | Deterministic fakes are sufficient for the scratch correctness gate. | A required safety property depends on real model semantics rather than state, identity, or storage behavior. |
| G4 | Kiro/Cursor JSONL is a valid first target. | Normal detection cannot be exercised, no supported fixture exists, or source-neutral contracts cannot be tested there. |
| G5 | The full-rebuild path can serve as a safe scratch oracle. | It can resolve production defaults, open production resources, call providers, or expose a non-equivalent comparison. |
| G6 | The expanded fault matrix is sufficient. | Any untested window can lose, duplicate, mix, prune, or falsely complete authoritative state. |
| G7 | Synthetic counters and scaling provide useful zero-cost incrementality evidence. | They fail to show frontier-bounded work or cannot distinguish reuse from accidental full processing. |
| G8 | `.crush` can remain excluded and paused/full-rebuild-only. | Pause creates unrecoverable loss or JSONL work is meaningless without SQLite. |
| G9 | 1–3 sessions is a reasonable prototype estimate. | Isolation, publication, prune, or fault testing requires materially new infrastructure. |
| G10 | Prototype PASS should lead to another review, not a canary. | Any evidence that synthetic scratch results establish production isolation, economics, semantic quality, or SQLite safety. |

## Questions for GPT

1. Is this genuinely zero-production-indexing and zero-paid-provider under the stated first-step guard?
2. Is any prohibited resource still reachable through configuration import, helper construction, locks, exports, model setup, or fallback paths?
3. Is the subprocess/network boundary strong enough for crash and provider tests?
4. Is the adapter-selection requirement correctly scoped and testable?
5. Is the fault matrix complete enough for the first scratch gate?
6. Does the convergence criterion adequately protect identities, provenance, pruning, and completion state?
7. What must be added before Cursor receives Execute authorization?
8. Is the estimate defensible, or should the scope be narrowed further?

## Required verdict format

### Overall verdict

`PASS`, `PASS WITH CONDITIONS`, or `FAIL`

State whether this proposal is safe to carry into a Cursor Execute grant for the isolated scratch prototype.

### Claim verdicts

| ID | Verdict (`agree` / `refute` / `restate`) | Reasoning | Corrected formulation if needed |
|---|---|---|---|
| G1 |  |  |  |
| G2 |  |  |  |
| G3 |  |  |  |
| G4 |  |  |  |
| G5 |  |  |  |
| G6 |  |  |  |
| G7 |  |  |  |
| G8 |  |  |  |
| G9 |  |  |  |
| G10 |  |  |  |

### Required corrections or blockers

List only changes required before the Execute grant or before interpreting prototype results.

### Execute-grant boundary

State exactly what Cursor may implement and what remains prohibited.

### Confidence

State `high`, `medium`, or `low`, with the dominant remaining uncertainty.

## Review boundary

This is an independent design check only. Do not modify ConvMem, run tests, index sources, call providers, change services, access production data, mutate the corpus, migrate storage, or issue an Execute grant.
