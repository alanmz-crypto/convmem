# Architecture — Arc Codex Kiro JSONL Production Canary

> **Arc: Codex. Planning artifact only.** This document does not authorize
> implementation, bootstrap, indexing, provider use, watcher operation, a PR,
> or activation.

## 1. Decision and product consequence

ConvMem can now incrementally process Kiro `messages.jsonl` files, but the
merged route remains disabled and deliberately refuses live production paths.
The next safe step is a two-part canary:

1. land and review a one-shot production-canary boundary that can name exactly
   one read-only Kiro source and exactly the existing production followers; and
2. under a later Ryan grant, use that boundary once to prove initial adoption,
   append-only frontier reuse, crash replay, source-scoped rollback, and the
   duration of cross-collection mixed visibility.

The canary will use a genuinely new Kiro source. It therefore needs an initial
full generation, but no migration or rebuild of legacy rows. It will not
change the production chunk size merely to manufacture an incremental result.

The canary stops at evidence. A successful run does not enable the feature,
start the watcher, adopt other sources, or authorize a second run.

## 2. Current facts and authority

The following are planning observations, not an executable grant. They must be
re-proved immediately before any live mutation.

| Item | Planning observation on 2026-09-10 |
|---|---|
| Dedicated source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Session metadata | sibling `session.json`; session id `sess_2628159e-d039-4646-a208-0a10a1b3e450`, workspace `/home/lauer/Projects/convmem`, status `idle` |
| Source identity | device `66306`, inode `23609783`, size `116047`, SHA-256 `b5b8e4b1f2d746b5457ddc324518f062cccf16f1f06a12ac1f0a1c93b8b89b6a` |
| Metadata identity | device `66306`, inode `23609784`, size `1272`, SHA-256 `79ddda24ab1574d1350cc036ea090a012f92adc896eef54d25da5f38894c15da` |
| Complete-prefix parse | 16 accepted messages, 16 ranges, complete boundary `116047` |
| Existing production adoption | zero `processed.json` entries and zero source rows in both Chroma collections |
| Feature state | `enabled = false`; `allow_full_rebuild = false` |
| Production chunking | size `60`, overlap `10`, step `50` |
| Watcher observation | no matching process in process census; user-systemd status was unavailable, so this is not sufficient for Gate 0 |

The source may grow while this plan is reviewed. Its identity, byte boundary,
and digest above are historical observations only. The later run grant must
bind a fresh complete-prefix snapshot.

Authority remains:

```text
Kiro JSONL complete prefix          source authority (read only)
             |
             v
checkpoint.json                    processing/recovery authority
             |
             +----> Chroma summaries and units
             +----> export and dedupe followers
             `----> processed.json (published last)
```

Chroma does not provide an atomic transaction spanning its two collections.
The checkpoint and rollback journal therefore remain the authority for
roll-forward or source-scoped restoration. The canary measures the visible
seam; it does not claim to remove it.

## 3. Why a new boundary is required

`IncrementalJsonlCoordinator` currently receives an `IsolationBoundary`. That
boundary correctly rejects production paths and requires deterministic fake
providers. `maybe_route_incremental()` also skips live activation when the
scratch-root environment is absent. Those are deliberate safety properties.

Three approaches were considered:

| Approach | Decision | Reason |
|---|---|---|
| Repeat against a copied source and temporary Chroma | Rejected as the next gate | Already proven; cannot measure the production writer, sidecars, locks, or serving visibility. |
| Widen or bypass `IsolationBoundary` | Rejected | Turns a strong general prohibition into ambient production authority. |
| Add a separate one-shot capability boundary and runner | **Chosen** | Makes every live read/write resource explicit, leaves the normal route default-off, and can be removed without changing the coordinator protocol. |

The new boundary is a deep module: the coordinator sees the same narrow path
and layout operations, while all grant parsing, path containment, process
gates, provider policy, call budgets, and evidence capture stay behind the
canary interface.

## 4. Two grants, never one inferred grant

### Grant P1 — harness implementation

After Kiro reviews this plan, Ryan may authorize Cursor to implement and test
the one-shot boundary and runner. P1 is hermetic:

- no production source or data path may be opened;
- no real provider or service may be called;
- no live config may be read or edited as operational authority;
- no `convmem index`, watcher command, bootstrap, or canary run may occur; and
- work stops at pushed evidence for Kiro review and a later Ryan PR decision.

### Grant P2 — one live canary

P2 does not exist merely because P1 merges. It must name the exact source,
fresh baseline source and metadata identities, the permitted pure-append
envelope, code revision, production resources, local model identities,
maximum calls, selected faults, rollback action, expiry, and one-shot nonce.
Ryan must authorize the final grant digest.

Changing any material field produces a different grant and requires a new
decision. A run may consume the nonce once. Failure does not imply permission
to retry.

## 5. Canary capability boundary

The P1 implementation should add a canary-only module and script, not a normal
`convmem` subcommand and not a new watcher route. Names are illustrative; the
reviewed implementation may improve them without changing the contract:

- `incremental_jsonl_canary.py`: grant model, validation, preflight, evidence,
  rollback capsule, and one-shot coordinator invocation;
- `scripts/run-jsonl-production-canary.py`: thin explicit launcher; and
- focused tests under `tests/`.

The runner must require both an absolute grant path and its expected SHA-256.
The grant is a local mode-0600 artifact, not committed to Git. It includes:

- repository revision and an allowed clean/known-diff state;
- exact canonical source and metadata paths;
- baseline device, inode, size, complete-boundary digest, and metadata digest;
- maximum final byte boundary and accepted-record count, maximum append
  epochs, and immutable-prefix rule for later controlled appends;
- exact mutable resources: Chroma root, incremental state root, export,
  dedupe, processed log, writer/source/export/processed locks, attestations,
  and census;
- a fresh temporary config overlay path and digest;
- watcher and competing-writer gate requirements;
- allowed loopback host and exact local model names/digests;
- per-stage transform-call ceilings;
- fault selector and expected pre-run checkpoint/generation;
- rollback capsule path and digest;
- expiration time, nonce, and `run_once = true`; and
- evidence directory, which must be new and mode 0700.

The boundary rejects unresolved paths, symlink components, aliases, duplicate
resources, unexpected ownership/modes, or any mutable path not named by the
grant. The source and metadata are opened read-only with `O_NOFOLLOW` and are
revalidated before and after capture. No operation may write, rename, unlink,
chmod, or lock either source file.

The production configuration file remains unchanged. The runner creates a
temporary overlay that copies the relevant production paths and chunking but
sets incremental mode only for this explicit process. The persistent config
continues to report `enabled = false` and `allow_full_rebuild = false` before
and after every stage.

## 6. Writer and recovery protocol

The canary reuses the existing production writer and source-scoped store
operations. It does not open Chroma directly through an ungoverned client.

The lock and publication sequence remains:

```text
outer production writer boundary
  -> incremental state advisory lock
     -> source lock
        -> governed Chroma session (safe re-entry)
        -> summary write
        -> unit write
        -> source-scoped prune
        -> checkpoint publication
        -> export lock and export reconciliation
        -> dedupe reconciliation
     -> release source lock
-> processed.json standalone writer-boundary + sidecar-lock transaction
```

The implementation must match the already-reviewed coordinator ordering, even
if the schematic groups follower work for readability. The executable tests
must assert the actual transition order rather than relying on this diagram.

Before the first live write, the runner captures a source-scoped rollback
capsule containing:

- exact rows and documents for this source in both Chroma collections;
- source-scoped export and dedupe entries;
- the processed entry, if any;
- incremental state/checkpoint bytes, if any;
- configuration and lock-path identities; and
- hashes plus an independently readable manifest.

For the selected new source the expected before-image is empty, but emptiness
must be proven, not assumed. Restore may delete or replace only candidate IDs
for the granted `source_path`. Cross-source counts and digests are captured
before and after every stage. A broad Chroma or restic restore is never an
automatic canary action.

If a transaction has not committed its checkpoint, the existing journal
chooses roll-forward from durable prepared outputs or exact before-image
restore. Once the checkpoint is authoritative, the canary reconciles
followers with zero transform calls. Any state not covered by those rules is
`recovery_unproven`: stop, retain evidence, and perform only the separately
authorized source-scoped rollback.

## 7. Provider and network boundary

The currently configured `deepseek-v4-flash` name can select a paid external
API when credentials are present. The canary must never inherit that choice.

P2 therefore requires:

- all external-provider credentials scrubbed from the child environment;
- an explicit local Ollama fallback model, initially proposed as
  `llama3.1:8b`, and local embedding model `nomic-embed-text:latest`;
- installed model manifests/digests captured before execution;
- only the pinned loopback Ollama endpoint allowed;
- non-loopback DNS and outbound connections denied in the canary process and
  descendants; and
- a hard call-budget guard inside the transform functions, not merely a
  post-run counter.

If the installed local model or digest differs from the reviewed grant, Gate 0
fails. Installing or pulling a model is outside both P1 and P2.

## 8. Real chunking and economic claim

Production uses chunk size 60, overlap 10, and step 50. With only 16 accepted
messages, the chosen session can prove correctness but not stable-history
reuse. Live execution is therefore blocked until the frozen complete prefix
contains **61 through 109 accepted messages**.

That range yields exactly two baseline chunks, beginning at 0 and 50. After a
small append that stays below 110 accepted messages:

- chunk 0 must be loaded from the durable prepared cache;
- only the frontier chunk beginning at 50 may be transformed;
- an unchanged replay must perform zero transforms; and
- projection reconstruction from the same prepared artifacts must match the
  committed source-scoped rows exactly.

The canary does not promise a dollar figure because all calls are local. It
proves the mechanism that avoids repeatedly re-summarizing stable history.
Baseline and append stages carry strict separate ceilings. Proposed ceilings
for Kiro review are:

| Stage | summarize | distill | summary embed | unit embed |
|---|---:|---:|---:|---:|
| Initial two-chunk generation | 2 | 2 | 2 | 16 |
| One frontier append generation | 1 | 1 | 1 | 8 |
| Replay/reconcile of the same generation | 0 | 0 | 0 | 0 |
| Whole canary: initial + control append + five fault appends | 8 | 8 | 8 | 64 |

Exceeding a ceiling stops before the next provider call and invokes the
authorized recovery path. Counts are evidence, not estimates inferred from
logs.

## 9. Fault and serving-visibility canary

Hermetic tests already cover every durable transition. Repeating all 44
transition sides against live production would add risk and local compute
without new information. P2 instead selects these load-bearing live faults:

1. summary committed, unit not committed;
2. unit committed, prune incomplete;
3. prune complete, checkpoint not published;
4. checkpoint published, export/dedupe follower incomplete; and
5. followers published, processed entry not committed.

Each fault is a contained child-process exit. Descendants must be killed or
proven absent before replay. A stage cannot proceed while a prior transaction,
attestation, census entry, or lock owner remains unexplained.

A concurrent read-only probe uses the real serving repository boundary and
records source-scoped summary/unit IDs, generation metadata, errors, and
monotonic timestamps. The canary does not assert nonexistent Chroma atomicity.
Its pass condition is:

- no row belonging to another source changes;
- every observed source row belongs to either the prior or candidate
  generation named by the transaction;
- mixed state appears only inside the measured apply/fault/recovery interval;
- replay or rollback converges within a 30-second hard stop; and
- after recovery authority settles, three consecutive reads over at least
  two seconds return one complete generation with no error or mixed state.

The maximum mixed-visibility and recovery durations are reported separately.
A duration within 30 seconds proves bounded recovery for this canary; it does
not establish an activation SLO. Kiro and Ryan decide whether the measurement
is acceptable before any activation plan.

## 10. Gate 0 and stop conditions

P2 Gate 0 must pass all of the following in a single preflight:

1. exact grant digest, revision, expiry, nonce, and clean allowed worktree;
2. 61–109 accepted messages and an exact baseline complete-prefix binding;
3. source and metadata canonical, regular, read-only opened, and unchanged;
4. no processed entry, no checkpoint/state, and zero Chroma rows for this new
   source before initial adoption;
5. persistent feature flag false and full rebuild false;
6. watcher inactive by service probe, process census, and denied service
   launcher; unknown/error is a failure;
7. no competing indexer/writer and all production locks either free or held by
   the attested canary process as appropriate;
8. all production paths exactly match the grant; no symlink escape;
9. named local models already installed with exact digests;
10. external credentials absent and non-loopback network denied;
11. fresh source-scoped rollback capsule verified readable; and
12. fresh restic backup identifier recorded as last-resort evidence, without
    authorizing a broad restore.

Immediate stop conditions include source drift, unexpected writer/read error,
call-cap breach, cross-source change, unproven recovery, timeout, nonlocal
network attempt, paid-provider selection, or failure to contain descendants.
The runner preserves evidence and consumes the one-shot grant. It must not
silently retry.

## 11. Evidence and decision boundary

P1 evidence must show hermetic rejection and fault behavior. P2 evidence must
contain the grant digest, fresh source binding, model identities, environment
scrub report, process/lock census, before-image manifest, per-transition event
log, provider counters, source digests before/after, source-scoped projection
manifests, read-probe timeline, rollback/replay result, and persistent-config
false/false confirmation.

Evidence must distinguish:

- previously reviewed scratch and hermetic implementation claims;
- P1 harness test results; and
- the single live P2 observation.

The runner stops after writing evidence. Kiro independently reviews the exact
P1 code revision and, later, the P2 evidence. Ryan then chooses one of:

- authorize a separately planned default-off activation slice;
- require a corrective canary or harness pass; or
- stop.

No canary outcome itself edits config, starts the watcher, indexes another
source, changes retrieval, or authorizes production rollout.

## 12. Review questions for Kiro

1. Does the separate canary boundary preserve rather than weaken the existing
   scratch isolation contract?
2. Is a dedicated runner outside normal `convmem index` the right way to keep
   watcher activation impossible during the canary?
3. Are the exact-resource grant, source-scoped rollback capsule, and one-shot
   nonce sufficient operational authority boundaries?
4. Is 61–109 accepted messages the correct minimal real-chunking window for a
   60/10 configuration?
5. Do the selected five live fault points add useful storage-seam evidence
   without repeating the exhaustive hermetic matrix?
6. Are the call ceilings conservative enough and fail-closed before spend?
7. Is the mixed-visibility pass condition honest and sufficient for a first
   canary, while correctly deferring activation SLOs?

## TL;DR

- Build a separate, one-shot, exact-resource canary boundary; do not weaken
  the existing scratch isolation guard or normal default-off route.
- The dedicated source is new but currently too short. Live execution remains
  blocked until it has 61–109 accepted messages, enabling a real two-chunk
  baseline and one-frontier-chunk append proof at production chunking.
- The later live grant permits local-only bounded transforms and five selected
  crash/replay observations, with source-scoped rollback and read visibility
  measurement; it stops at independently reviewed evidence.
