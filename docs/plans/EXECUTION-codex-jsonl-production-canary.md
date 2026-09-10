# Execution Plan — Arc Codex Kiro JSONL Production Canary

> **Status: proposed, not authorized.** This plan separates a hermetic Cursor
> implementation grant (P1) from a one-shot live canary grant (P2). Kiro must
> review the architecture and this plan before Ryan may authorize either.

## 1. Scope lock

This plan may prepare and test a canary-only boundary around the already
merged incremental coordinator. It may later run one exact-source canary only
under a new Ryan grant.

Neither phase may:

- enable incremental JSONL in persistent production config;
- start or install `convmem-watch`;
- add the canary to normal `convmem index` routing;
- use a paid or nonlocal provider;
- pull/install models or access non-loopback network;
- index any source other than the granted Kiro JSONL;
- migrate or rebuild a previously indexed source;
- change chunking, retrieval, ranking, or other adapters;
- perform a broad Chroma/restic restore automatically; or
- continue from evidence to activation.

## 2. Phase P1 — hermetic canary harness

P1 is the next possible Execute phase, but it is not authorized by this plan.
Cursor starts only after Kiro PASS and Ryan's explicit bounded Execute grant.

### P1-T0 — re-establish the disabled baseline

1. Start a new `feat/2026-09-10-...` worktree from current `origin/main`.
2. Confirm the incremental feature is absent/false and
   `allow_full_rebuild = false` in examples and default loading.
3. Confirm `watch.py` and unrelated adapters are byte-identical before and
   after the implementation.
4. Run the existing Arc Codex isolation/config/state matrix before edits.
5. Install service, subprocess, provider, and network denials before importing
   the new runner in every test worker.

**Gate:** any baseline mismatch or attempted live access stops P1.

### P1-T1 — exact grant model and one-shot consumption

Implement a strict `CanaryGrant` decoder with a closed field set and explicit
schema version. Validate:

- absolute canonical paths and exact allowed resource roles;
- baseline source/metadata identity, boundary, and digests, plus a bounded
  pure-append envelope for later manual stages;
- code revision, expiry, nonce, and expected pre-state;
- model names/digests, loopback endpoint, call ceilings, and fault selector;
- rollback/evidence paths and digests; and
- external credential and watcher/process-denial policy.

Reject unknown fields, duplicate paths, path aliases, symlink components,
world/group-writable authority artifacts, stale grants, reused nonces, and
digest mismatch before opening Chroma or any provider.

The launcher accepts `--grant PATH --grant-sha256 DIGEST`. It has no defaults
for source or mutable resources. A nonce receipt is fsynced before the first
live-capable mutation. The receipt identifies one resumable run state machine:
it may advance only through grant-listed stages, append epochs, and faults, and
may not start a second run. Hermetic tests prove the same grant cannot create a
second run, including after a child crash.

### P1-T2 — production-canary boundary

Add a separate boundary implementing only the coordinator capabilities needed
for the exact granted source and layout. Do not modify `IsolationBoundary` to
accept production paths.

Tests must prove:

- only the exact source and sibling metadata can be opened read-only;
- every mutable path must match its named grant role;
- resolved aliases, symlink escapes, production-root substitution, config
  substitution, and unexpected locks fail before construction;
- source write/rename/unlink/chmod/lock attempts are impossible;
- `maybe_route_incremental()` stays default-off and does not discover the
  canary runner; and
- the runner cannot be reached through watcher or normal CLI dispatch.

### P1-T3 — config, provider, and network guard

Build the run configuration as a fresh temporary overlay. It may copy only
reviewed production path and chunking values, then set the feature for the
one runner process. It must re-read the persistent config before and after and
prove `enabled = false` and `allow_full_rebuild = false` there.

Before any transform:

- construct an allowlisted child environment rather than deleting selected
  variables from the parent;
- require all known external-provider keys absent;
- pin local model manifest digests;
- restrict the endpoint to the granted loopback address;
- deny DNS and non-loopback sockets in runner and descendants; and
- install an in-process counter guard that raises before a call exceeding its
  stage ceiling.

Tests use fake local provider endpoints and must demonstrate denial of paid
selection, external DNS/IP access, model mismatch, cap+1 calls, and a child
attempting to escape the denial.

### P1-T4 — rollback capsule and source isolation

Implement a source-scoped pre-run capsule and restore operation using the
existing governed writer and source-scoped Chroma primitives. The capsule must
round-trip:

- summaries and units including IDs, documents, embeddings where exposed, and
  metadata;
- source-matching export and dedupe entries;
- processed entry;
- checkpoint/transaction/rollback/prepared state; and
- a manifest of unrelated-source counts and content digests.

Restoration is candidate-ID and `source_path` constrained. Tests place
sentinels from at least two unrelated sources in both collections and all
sidecars. Crash before and after each restore publication must converge to the
exact before-image while all sentinels remain byte/logically identical.

Do not implement or invoke a whole-database/restic restore.

### P1-T5 — selected fault runner and descendant containment

Expose only the five reviewed P2 fault scenarios:

1. between summary and unit writes;
2. between unit write and prune completion;
3. between prune and checkpoint publication;
4. between checkpoint and export/dedupe completion; and
5. between followers and processed publication.

The worker exits distinctly at the named point. The supervisor records PID,
process group, transition log, and durable state, then proves the child and
descendants absent before replay. Unknown fault names fail before mutation.

Retain the exhaustive hermetic 44-transition matrix as regression evidence;
the five-scenario runner is an operational selector, not a reduction of test
coverage.

### P1-T6 — serving-visibility probe

Add a read-only concurrent probe through `ServingIndexRepository`, backed by a
temporary real Chroma store. It records monotonic timestamps, errors, and the
source-scoped summary/unit generation view while a fault worker applies and
recovers.

Tests must cover:

- prior complete → candidate mixed → candidate complete;
- fault → mixed state → roll-forward;
- fault → exact before-image restore;
- no observations after authority settles that contain mixed generations;
- three stable consecutive reads spanning at least two seconds; and
- hard stop when recovery exceeds 30 seconds.

The test may observe mixed state. It must never normalize it away or describe
the two collections as atomic.

### P1-T7 — real chunking and call-accounting rehearsal

Using synthetic Kiro transcripts and production chunking 60/10:

1. freeze 61 accepted messages and prove exactly two chunk starts, 0 and 50;
2. run the first generation within call ceilings;
3. append without reaching 110 accepted messages;
4. prove start 0 is reused and only start 50 is transformed;
5. replay unchanged and prove zero transforms; and
6. rebuild an isolated projection from the same durable prepared artifacts and
   compare exact source-scoped authority without re-running the LLM.

The harness must reject fewer than 61 or 110-or-more accepted messages for the
live canary profile. It must not alter chunk size or overlap.

### P1-T8 — governance and evidence

Run and update, as required:

- writer-route inventories and revision binding;
- shadow-writer coverage;
- source/exclusion and safe-reindex regressions that do not require a live
  production lock;
- focused Arc Codex tests;
- compileall, pylint, and `git diff --check`.

Create `docs/plans/VERIFY-codex-jsonl-production-canary.md` containing exact
commands, revisions, environment versions, transition coverage, call counts,
and explicit confirmation that no live source, production path, watcher,
provider, or network was touched.

Stop at a pushed exact tip for Kiro review. PR creation remains Ryan-gated.

## 3. P1 acceptance matrix

| ID | Acceptance condition | Evidence owner |
|---|---|---|
| P1-A1 | Existing isolation guard remains production-denying | focused boundary tests |
| P1-A2 | Canary has no default source/resource authority | grant decoder tests |
| P1-A3 | Grant digest, expiry, revision, nonce, and mode are fail-closed | grant tests |
| P1-A4 | Source is read-only and identity-bound before/after capture | file-boundary tests |
| P1-A5 | Persistent feature and rebuild flags remain false | config parity tests |
| P1-A6 | Paid/nonlocal provider and outbound network are impossible | child/network tests |
| P1-A7 | Call ceilings stop before cap+1 | provider-counter tests |
| P1-A8 | Source-scoped capsule restores exact state without sentinel change | rollback crash matrix |
| P1-A9 | Five operational faults map to reviewed durable transitions | coverage assertion |
| P1-A10 | Descendants and stale locks are contained or fail closed | subprocess tests |
| P1-A11 | Serving probe reports rather than hides mixed visibility | concurrent read tests |
| P1-A12 | 60/10 frontier reuse and zero-call replay are exact | 61-message rehearsal |
| P1-A13 | Normal ingest/watcher route remains default-off and unchanged | route/diff tests |
| P1-A14 | All evidence is hermetic and reproducible | VERIFY + Kiro rerun |

## 4. Phase P2 — one live canary

P2 is a separate operational plan section, not current authorization. It may
run only after the P1 code has merged, Kiro has passed the exact merged
revision or a reviewed tip preserved by merge, and Ryan has approved the final
grant digest.

### P2-T0 — source preparation by Ryan/Kiro usage

The dedicated session currently has 16 accepted messages. Before grant freeze,
Ryan continues ordinary benign interaction with that same Kiro session until
`parse_complete_prefix()` reports 61–109 accepted messages. The canary tooling
must not synthesize, append, or edit the live transcript.

Once the desired range is reached, stop using that Kiro session. Freeze fresh
source and metadata device/inode/size/digests and the complete boundary into
the proposed grant.

### P2-T1 — review and authorize the exact grant

Produce a human-readable preflight packet containing:

- the exact source and why it is dedicated;
- proof of zero existing adoption;
- all mutable resources and rollback scope;
- production config false/false state;
- repository revision;
- installed local model identities;
- per-stage and whole-run call ceilings, five fault selectors, maximum append
  epochs, maximum final byte/record bounds, and immutable-prefix rule;
- watcher/writer gate strategy;
- expected initial and append generation counts; and
- the complete grant JSON plus SHA-256.

Kiro reviews the packet. Ryan authorizes the exact digest and a one-shot run or
declines it. No agent may substitute a newer source digest after approval.

### P2-T2 — Gate 0

In one non-mutating preflight, prove every Architecture §10 requirement. In
particular:

- watcher inactive using service query, process census, and launcher denial;
- errors or unavailable status are not silently treated as inactive;
- no writer/indexer process or unexplained lock/attestation exists;
- exact source is regular, canonical, unchanged, and 61–109 messages;
- no rows, processed entry, or incremental state exist for this source;
- production config remains false/false;
- external credentials are absent from the allowlisted child environment;
- local models are already present with reviewed digests;
- non-loopback network denial is installed and self-tested;
- rollback capsule is readable and expected-empty for the source; and
- a fresh restic backup identifier is recorded, without invoking restore.

Gate 0 emits a digested evidence event. Any failure consumes no model
calls and performs no data mutation. Whether a failed preflight may receive a
new grant is a new Ryan decision.

### P2-T3 — initial two-chunk adoption

Run one initial generation against the exact frozen prefix. This is permitted
only because the source has no prior processed/checkpoint/Chroma authority.
It is not a legacy-source rebuild.

Assert:

- two chunk starts, 0 and 50;
- call counts within initial ceilings;
- prepared outputs durable before Chroma;
- checkpoint authoritative before processed publication;
- exact source-scoped rows and followers match the generation manifest;
- unrelated-source census/digests unchanged;
- persistent config remains false/false; and
- source and metadata digests remain unchanged.

Run an unchanged replay and require zero transform calls.

### P2-T4 — controlled append and frontier proof

Pause the runner at its explicit append gate. Ryan adds one benign prompt to
the dedicated Kiro session and waits for the response. No canary code writes
the source. The runner binds a new stage receipt only if device/inode are
unchanged, the prior granted prefix is byte-identical, the change is a pure
append, and the new complete prefix remains within the grant's byte, record,
epoch, and total-call ceilings.

Run the incremental generation and require:

- stable chunk 0 loaded from durable cache;
- only frontier start 50 transformed;
- append-stage call counts within 1/1/1/8 ceilings;
- source-scoped projection equals reconstruction from the same prepared
  artifacts; and
- unchanged replay performs zero calls.

If the append crosses 110 messages, the two-chunk proof profile no longer
applies and P2 stops for a revised plan; it does not silently accept a third
chunk.

### P2-T5 — five selected fault/replay observations

For each fault, pause at the explicit append gate and have Ryan create a benign
append generation. Bind a new stage receipt under the same approved
pure-append envelope, then use the fault selector already named in the grant.
Do not create source content programmatically.

For every case:

1. start the read-only serving probe;
2. launch the contained fault worker;
3. capture durable state at the distinct child exit;
4. prove descendants absent;
5. replay with the same prepared output and zero transform calls;
6. require convergence or perform the source-scoped authorized restore;
7. require three stable serving reads after authority settles; and
8. re-prove source digest and unrelated-source census/digests.

One grant may authorize the control append plus all five selectors, with at
most six post-baseline append epochs and whole-run ceilings of 8 summarize, 8
distill, 8 summary-embed, and 64 unit-embed calls. Prepared-cache replay calls
are always zero. Any need to change source, append envelope, model, call cap,
fault list, or rollback scope ends P2.

### P2-T6 — evidence freeze and stop

Write a self-contained, append-only evidence bundle with:

- exact approved grant and digest;
- consumed nonce receipt;
- code/config/model/source identities;
- Gate 0 result;
- rollback and unrelated-source manifests;
- transition/fault/process/lock timelines;
- initial, frontier, and replay call counts;
- source-scoped Chroma/follower manifests;
- serving-read timeline and mixed/recovery durations;
- source and persistent-config postconditions; and
- final disposition: `converged`, `restored`, or `recovery_unproven`.

Stop all canary processes, retain the watcher inactive, and do not invoke
normal indexing. Commit only redacted evidence suitable for review; retain any
machine-local absolute grant/capsule under the agreed protected evidence path.
Push a docs/evidence tip and stop for exact-tip Kiro review. PR, retry,
activation, watcher work, and adoption of another source remain Ryan-gated.

## 5. P2 acceptance matrix

| ID | Acceptance condition |
|---|---|
| P2-A1 | Exact approved grant is current, consumed once, and unchanged |
| P2-A2 | Gate 0 passes with watcher/writers absent and local-only execution |
| P2-A3 | Initial adoption is exactly two chunks and stays within call caps |
| P2-A4 | Unchanged initial replay has zero transform calls |
| P2-A5 | Controlled append reuses chunk 0 and transforms only frontier 50 |
| P2-A6 | Append replay has zero transform calls |
| P2-A7 | All five fault cases converge or exact-restore within 30 seconds |
| P2-A8 | No unrelated source changes in Chroma or followers |
| P2-A9 | No mixed state remains after recovery authority settles |
| P2-A10 | Mixed-visibility and recovery durations are reported honestly |
| P2-A11 | Source/metadata remain unchanged by the runner |
| P2-A12 | Persistent feature/rebuild flags remain false and watcher inactive |
| P2-A13 | No paid/nonlocal calls or call-cap breach occurs |
| P2-A14 | Run stops at evidence for independent Kiro review |

## 6. Stop and rollback rules

On any unexpected result:

1. stop the worker and descendants;
2. do not start the watcher or normal indexer;
3. preserve transaction, checkpoint, prepared output, process, and read-probe
   evidence;
4. if the existing recovery state is proven, replay once with zero calls;
5. otherwise perform only the grant-named source-scoped restore;
6. verify unrelated-source and persistent-config postconditions; and
7. stop for review.

Do not retry with fresh transforms, increase a call cap, edit the source,
delete evidence, clear unexplained locks, or restore the whole database without
a new Ryan grant.

## 7. Review handoff

Kiro should review this plan and the paired architecture before any P1 grant.
A PASS means Ryan may choose whether to authorize hermetic harness work. It
does not authorize P1 automatically and cannot authorize P2.

Kiro's P1 implementation review must verify the exact pushed tip and rerun the
hermetic matrix. Kiro's later P2 review must verify the evidence against the
approved grant digest and distinguish recorded live observations from
repeatable tests.

## TL;DR

- P1 builds and proves a one-shot canary boundary entirely under temporary
  roots; it stops for Kiro review and cannot touch live data.
- P2 is a later, separately digested Ryan grant for one new Kiro source using
  real 60/10 chunking, local-only bounded calls, five selected live faults,
  source-scoped recovery, and serving-visibility measurement.
- Both phases stop at evidence. Neither enables persistent config, normal
  indexing, another source, or the watcher.
