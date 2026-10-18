# Arc Codex — Kiro session incremental indexing

**Issue:** #286. **Author:** Codex, 2026-10-18. **State:** design proposed;
Kiro review next. **Baseline:** fetched `origin/main` at `07117ed` (PR #404).
**Source:** Ryan's request to deliver the arc's original Kiro indexing goal.
**Authority:** design document only; no implementation, production operation,
configuration change, paid bootstrap, or PR is authorized by this document.

Planning status: Architecture Planning; Architect / Systems Thinker / Risk
Reviewer; function Planner; Codex authors, Kiro reviews, Ryan approves.
Standards: the architecture planning guide, team charter, and Ousterhout,
DDIA, Hard Parts, and Zeller builder digests. Stop: await design review/HITL.

## 1. Direction and consequence

Admit a bounded list of **exact Kiro transcript paths**, use the existing v2
semantic transform descriptor for all selected Kiro work, and bootstrap only
selected, non-excluded sessions through the governed one-shot route. Retain
the existing incremental coordinator, prepared cache, writer gates, and
recovery machinery. Do not introduce a second indexing engine.

The first rollout targets active sessions. A read-only inventory found ten
indexed, non-excluded Kiro sessions modified in the preceding 24 hours,
requiring approximately **36 paid calls** to bootstrap without retries. All
18 indexed, non-excluded sessions would require about **84 calls**. These are
estimates of initial transformation work, not spending grants. Later appends
transform the changing overlap frontier and new chunks; unchanged complete
prefixes make zero transform calls.

Exact-source admission has an operational cost: each new session needs an
explicit source-list update. Sessions outside the list continue on legacy.
This slice therefore reduces repeated work for its cohort, not all future
Kiro traffic automatically. Time-based discovery is deferred until there is
a trustworthy Kiro birth-identity contract. Cursor can reuse the architecture
after gaining a complete-prefix adapter and separate admission/recovery tests.

## 2. Current evidence and scope

### Repository facts at the baseline

- Codex time-based admission is merged through PR #388. Its predicate uses
  UUIDv7 time, filename time, and in-file session identity; it is not an mtime
  cutoff. See `incremental_jsonl_codex_admission.py:90` and the
  [Codex admission design](DESIGN-issue-286-codex-rollout-admission.md).
- Kiro exact-path recovery parity is merged through PR #396 (`9ef4ecd`).
  Production-boundary recovery must remain shared across Kiro and Codex.
- Semantic transform compatibility is merged through PR #399 (`9be0a4f`),
  but `incremental_jsonl.py:638` selects v2 only for `codex_admitted_live`.
  Kiro still hashes implementation identity into its v1 fingerprint.
- Full-rebuild handling is merged through PR #402 (`483373f`). Its Codex
  admission guard counts the whole transform when rebuilding, not merely
  the append frontier. Kiro does not yet inherit those resource caps.
- The bootstrap command independently computes the v1 fingerprint in
  `scripts/bootstrap-incremental-jsonl.py:157`. Changing only the coordinator
  would make grant preflight and actual transformation disagree.
- Kiro already has complete-prefix parsing, raw-line coverage, and byte
  ranges. Cursor's `adapters/jsonl_chat.py` only has whole-file parsing and
  is absent from `incremental_jsonl_formats.py`.
- The checkpoint converter in `incremental_checkpoint_migration.py` is
  explicitly **hermetic-only**. Its presence is not a live migration tool.

### Live observations, read-only on 2026-10-18

The configured chunk size/overlap are 60/10; embedding dimension is 768.
Incremental indexing is enabled for Codex, `live_sources` is empty, and the
shared `allow_full_rebuild` is **true**. Thus no Kiro source is selected today.
The watcher was active in the session brief. The older
[arc STATUS](STATUS-codex-jsonl-production-integration.md) and LATEST entry
still describe an earlier default-off stage; they are not current activation
evidence. This proposal does not claim a new live grant from these readings.

Ryan supplied the Canary 2 observation: approximately 186 legacy paid calls
across Cursor's 29 runs and Kiro's 23 runs in approximately 24 hours. This
document uses it as supplied evidence, not an independently reproduced count.
Runs are not unique sources or paid calls. The per-class paid split and exact
counter definition are unavailable here, so no Kiro savings percentage or
payback date can be inferred from 186.

In scope: Kiro selection, semantic compatibility, existing-source bootstrap,
metadata continuity, watcher interaction, safety/recovery, proof obligations,
rollout gates, and Cursor applicability. Out of scope: Kiro SQLite, Cursor
`store.db`, other transcript adapters, retrieval/chunking redesign, broad
automatic source discovery, repairing existing Codex incidents, and live
checkpoint conversion. Cursor implementation is a later Ryan-owned scope
decision. This is a continuation of Arc Codex, not a new arc.

## 3. Admission options and decision

**A — Exact-source selection (chosen).** Reuse canonical `live_sources`.
The grant identifies actual files and the existing production boundary checks
ownership, regular-file identity, symlink components, role overlap, and source
locks. It handles both newly created files and already indexed sessions.
Reversible by holding selected paths; migration costs are explicit. Main
trade-off: repeated operator work when new sessions are created.

**B — Kiro creation-time cutoff (deferred).** Observed Kiro transcript parent
identifiers are UUIDv4 (678/678 in the transcript inventory), not UUIDv7.
Sibling `session.json` has `createdAt`, but copying/restoring it can preserve
or change that value independently of the transcript. Filesystem mtime,
ctime, watcher first-seen time, and `lastModifiedAt` are not session birth
proof. A cutoff would need a specified, validated identity/creation contract,
copy handling, and durable enrollment before any legacy index. It provides
better unattended coverage but adds authority and race-handling machinery
that the first Kiro cohort does not need.

**C — Route all Kiro files and rebuild on demand (rejected).** This removes
enrollment work but turns ordinary watcher events into migration/spending
authority. It risks historical backfill and exclusion violations, and the
current global rebuild switch is already true for Codex. It is not a bounded
first rollout.

### Selected-source contract

1. Exclusion and purge rules win, including any same-path exclusion entry.
   Enrollment never removes exclusions.
2. Only an exact canonical path in `live_sources`, with normal detection
   `jsonl_kiro_session`, can select this Kiro route. No glob, basename-only,
   UUID-only, directory-wide, or copied-path inheritance. Constrain the first
   cohort to `~/.kiro/sessions/<workspace-hash>/sess_<uuid>/messages.jsonl`.
3. An unselected source retains legacy behavior. A selected source either
   commits, is unchanged, or refuses visibly; it never falls back to legacy.
4. A new source must have neither processed lineage nor source-owned Chroma
   rows nor contradictory incremental state. Any existing lineage without a
   checkpoint requires bootstrap, even if the source is newly enrolled.
5. Enroll a new path before its first indexing attempt. If legacy indexing
   wins that race, refuse `bootstrap_required`; do not relabel it as new.
   Pause the watcher and other index writers for an enrollment/bootstrap
   window, install the exact reviewed configuration, then probe routing.
6. Preserve `source_state_id(format, canonical_path)`. Moving/copying a file
   does not transfer checkpoint, paid budget, or recovery authority.

Selected Kiro must reach this decision before generic content-hash no-op
shortcuts. Currently `watch.flush_path` calls `watch_skip_reason`, and
`ingest._index_one_file` returns on an existing file hash before calling
`maybe_route_incremental` (`ingest.py:1391`). Bypass only the unchanged-hash
shortcut for selected Kiro, retaining exclusion and other policy checks.
The coordinator must check pending transactions, semantic metadata, policy,
and follower reconciliation before returning unchanged. Do not use
`force_reindex` to bypass these shortcuts; the live route forbids it.

## 4. Route policy and v2 compatibility

Keep **source selection**, **transform compatibility**, **resource policy**,
and **recovery authority** separate. Replace the Codex-only condition for v2
with an explicit selected-format capability: admitted Codex and selected Kiro
use v2. Do not set `codex_admitted_live` for Kiro or run Codex identity checks
against it. Isolated tests must be able to exercise this exact Kiro-v2 path.

Use `build_transform_descriptor` with Kiro's format/adapter contract, resolved
models, dimension, prompts, normalization, confidence, chunk size/overlap,
and epoch. Reuse v2 checkpoint/transaction fields, prepared-key derivation,
and generation scheme. Implementation revision remains provenance and current
writer authority, not a semantic cache key. Prompt/parser/output changes
invalidate reuse; instrumentation-only deploys do not. Extend the existing
[epoch checklist](incremental_transform_epoch_bump_checklist.md) and inventory
tests to cover Kiro, including the metadata contract below.
Use the Kiro adapter-contract version for Kiro-only semantic changes; do not
bump a shared epoch merely to enroll Kiro and invalidate healthy Codex caches.
Changes to shared semantics still require the shared epoch discipline.

Introduce a typed **Kiro policy** under the existing incremental settings
(proposed name `index.incremental_jsonl.kiro_session`). This is policy, not
additional selection. Require it for selected Kiro paths on the new runtime;
absence/malformed values refuse visibly before providers, while unselected
Kiro and existing Codex routing remain unchanged. Its first rollout has:

- `max_source_bytes = 268435456`, checked before allocation, capture, replay,
  and unchanged returns; this is a ceiling, not permission to allocate it.
- `max_transform_chunks_per_run = 20`, applied to the actual planned set
  before providers. Initial ingest/bootstrap counts all chunks; appends count
  the permitted frontier; any later authorized rebuild counts all chunks.
- `allow_full_rebuild = false`, mandatory in this first slice. It overrides,
  and never inherits, the shared true setting used by current Codex traffic.
  Reject true for this initial Kiro policy rather than silently enabling it.

Normal Kiro indexing cannot rebuild old checkpoints implicitly. This keeps
bootstrap a distinct one-shot operation and prevents code deployment or a
metadata change from spending on full history. Sharing guard helpers is
desirable; changing Codex policy or recovery outcomes is not part of this
direction. Pin regression tests for current Codex full-rebuild behavior.

### Kiro sidecar semantics

The current capture/revalidation code hashes **all bytes** of `session.json`
(`incremental_jsonl.py:803–915`). Kiro stores mutable UI fields such as
`lastModifiedAt`, title, and status there. An unrelated sidecar change during
paid work can therefore refuse the run. Conversely, cross-checkpoint
continuity does not explicitly compare the prior sidecar digest, so merely
retaining that raw digest is not a complete metadata contract.

Define `kiro-complete-prefix-v2` before live canary:

- Selected Kiro sources require a bounded, owned, regular, non-symlink
  `session.json`, read safely as part of capture. Use a 1 MiB metadata cap.
  Its `id` must equal the full `sess_<uuid>` parent name (the observed schema,
  not the bare UUID); require a valid workspacePaths representation.
  Missing/malformed or identity-mismatched metadata refuses, with no snapshot
  directory-name fallback and no provider calls.
- Compute a versioned semantic metadata digest from the **effective fields
  consumed by canonical messages/provenance**: session ID and selected
  workspace directory. Preserve raw sidecar bytes/digest in the snapshot for
  evidence. Creation time is provenance only, not admission authority.
- Compare the semantic digest during capture, before apply, on replay, and
  against the checkpoint even for an unchanged JSONL prefix. Changes to
  session identity or workspace refuse; they cannot leave reused historical
  rows carrying obsolete provenance. The digest is per-source state, not a
  reason to invalidate every Kiro source's transform descriptor.
- Title/status/lastModifiedAt-only updates may proceed when the effective
  fields are identical. Verify that these fields do not affect any transform,
  metadata, or provenance consumer; a new consumer expands the contract and
  forces the appropriate version change. Preserve raw-line selection and
  rendered-message behavior; do not opportunistically change Kiro parsing.
- Source bytes before the selected boundary must still match exactly.
  Only pure append after that boundary is allowed. Semantic sidecar handling
  does not relax transcript continuity or the writer authority checks.

This small Kiro adapter contract change is part of the design, not a claim
that existing v1 checkpoints can be relabeled. It also avoids solving noisy
metadata changes by allowing expensive automatic rebuilds.

## 5. Existing sessions: one-time bootstrap and checkpoint cases

Classify every exact candidate under locks before spending:

- **Never indexed, no checkpoint or pending state:** ordinary initial v2
  transform, under resource and canary budgets.
- **Legacy indexed, no checkpoint:** use the existing exact-source bootstrap
  command, updated to bind v2. Do not manufacture a checkpoint from
  `processed.json`, import arbitrary Chroma rows as prepared artifacts, or
  delete lineage to bypass admission. Existing summaries/units remain the
  serving state until the governed replacement commits.
- **Healthy v2 checkpoint:** normal frontier reuse; no bootstrap.
- **v1 checkpoint:** refuse `migration_required` in normal indexing. Leave
  it and its paid cache intact. The surveyed non-excluded cohort has none,
  so live v1 conversion is not a rollout dependency. If a later inventory
  finds one, exclude it from this cohort and prepare a separate exact-source
  migration/rebuild proposal. A live converter needs exact v1 preimage and
  semantic-equivalence proof, source/writer locks, quiescence, staged cache,
  atomic checkpoint publication, and recovery review; the hermetic helper
  alone is insufficient. A paid rebuild needs separate exact authority too.
- **Any pending transaction, rollback authority, corrupt state, quarantine,
  or retry hold:** classify and recover through its existing authorized
  operation. Do not bootstrap over it, clear it for convenience, or reset a
  budget. v1 pending transactions cannot replay on the v2 path; preserve them
  until an approved compatible-runtime recovery is available.

### Bootstrap binding and publication

The bootstrap script, grant validator, supersession checks, and coordinator
must use the same descriptor builder and effective policy. Version the grant
format explicitly: new Kiro-v2 grants bind fingerprint scheme, descriptor
digest, Kiro adapter contract, semantic sidecar digest, prefix boundary/hash,
canonical source, exact runtime/config/provider identities, resolved dimension,
backup authority, chunk cap, paid HTTP-attempt cap, and recovery allowance.
Do not silently reinterpret old v1 grants or regenerate their operation IDs.
Already-consumed and failed operations retain their receipts and lineage.

Require fresh complete-data backup authority, validated local/offsite coverage,
exact before-images, and the no-other-writer window already required by the
bootstrap safety protocol. Revalidate the proposal immediately before grant
consumption and again at publication. Pure append may remain outside the
selected prefix for a later index; mutation of the bound prefix or semantic
metadata invalidates the operation. No provider calls while holding the
global Chroma write scope. Preserve source → global writer → export lock order.

Publish durable prepared artifacts before Chroma mutation. Keep rollback
authority through both collection writes and verification. Commit checkpoint
authority before processed/export/dedupe followers. Replay repairs followers
from the committed generation without re-transforming completed cached work.
Retries and superseding grants retain all predecessor paid-attempt charges.

## 6. Paid-call estimate and proposed spending bounds

The estimate used a read-only scan of
`~/.kiro/sessions/*/sess_*/messages.jsonl` and the configured processed index
on 2026-10-18. It counted complete newline-terminated records accepted by the
current Kiro rule: user/assistant payload with nonblank string content.
Tool/status records and incomplete tails do not count as messages. It read
no Chroma collection and invoked no embedding or LLM provider.

For N accepted messages, size S=60, overlap O=10:

`C(N) = 0 if N=0, otherwise 1 + ceil(max(0, N-S)/(S-O))`.

Nominal successful paid work is **2 × C**: one summary plus one distillation
per chunk. Ollama embeddings are separately observed and cap-exempt under the
existing DeepSeek-only paid accounting; units per chunk affect embedding work.
Transport retries and failed requests can raise actual paid HTTP attempts.
The hard cap must therefore count actual provider HTTP attempts durably before
dispatch, not just successful summaries/distillations or watcher invocations.

Observed populations:

- 678 existing transcript files, 33,643 accepted messages, 959 chunks:
  1,918 nominal paid calls if all were transformed. **Not a migration target.**
- 513 transcript paths referenced in processed state, 830 chunks:
  1,660 nominal calls before applying exclusions. **Not an eligible cohort.**
- 495 of those paths have explicit exclusion entries. Preserve all of them.
- The remaining 18 indexed paths have 1,794 messages and 42 chunks:
  **84 nominal calls**, maximum six chunks per source. No checkpoint or
  transaction file was observed for these source IDs in the default
  configured incremental state root.
- Ten of those 18 were modified within 24 hours: 705 messages and 18 chunks,
  **36 nominal calls**, maximum three chunks per source.

All transcript sizes/mtimes were stable across the initial scan. This is an
estimate, not an atomic production inventory or proof of absent Chroma-only
lineage. Refresh canonical exclusions, source identity, exact prefix counts,
both-collection ownership, state, and backups for the actual grant. The first
processed snapshot digest was
`9c0ac4ad75a82613b5ba04a4a254af6d39b5830fbbd94e23c406fce4c53aef7f`;
subsequent reads confirmed the exclusion-filtered counts above. Active writes
and historical hash entries can change the inventory.

Recommend bootstrapping the ten recently modified eligible sources only after
the one-source canary succeeds. A proposed retry allowance of **6 × C actual
paid HTTP attempts** gives a hard aggregate bootstrap ceiling of **108** for
that snapshot, versus 36 nominal calls; all 18 would be 252 versus 84.
Six is an operator budget choice, not a guarantee that nested provider retries
will finish within it. Stop at the limit. The exact packet sets per-source
and aggregate limits and accounts for predecessor attempts. No blanket archive
backfill, unexclusion, or automatic grant renewal.

For subsequent appends, estimate `2 × changed_or_uncached_frontier_chunks`.
A one-chunk conversation may save no paid calls while it grows; savings rise
when stable historical chunks can be reused. Measure actual marginal savings
instead of promising that incremental means zero paid calls on every append.
Use a provider-free full-file chunk count as the counterfactual; never run a
second paid legacy transform merely to measure the baseline. No dollar figure
is claimed without current token usage, cache-hit mix, and pricing evidence.

## 7. Watcher interaction and visibility

Keep the existing debounce, watch roots, per-source serialization, and child
process resource controls. The watcher schedules work; ingest chooses the
route. Preserve the PR #397 child `index --file ... --now` behavior so a watcher
child cannot defer back to its own parent. Manual indexing keeps normal
watcher deferral unless the operator explicitly invokes the one-shot workflow.

Map a `session.json` create/modify/move/delete event to its sibling
`messages.jsonl` **only for selected Kiro paths**. Do not index the sidecar as
a transcript or broaden watch roots. Coalesce these events with transcript
events. Semantically irrelevant sidecar churn must reach an unchanged,
zero-provider outcome; identity changes must be visible even without a
transcript append. On initial activation explicitly enqueue the reviewed
cohort so enrollment does not depend on a later filesystem write.

Selected-source refusals use the existing parseable refusal exit/marker,
path quarantine, retry-state hold, and doctor reporting. Prefix changes do
not forgive a terminal refusal or recovery authority failure. The current
breaker can wake a wedged path when its prefix changes; preserve that
distinction from terminal refusal, but the woken Kiro operation must still
pass durable retry/recovery gates and must never discard its journal. Generic watch
events never bootstrap, migrate a fingerprint, rebuild a selected Kiro source,
or clear a hold. Preserve the distinction between watchdog quarantine and
Chroma write-guard containment. `watch --clear-quarantine <path>` currently
clears both watcher state and incremental retry holds; use it only under an
exact recovery decision after reviewing both, never `--clear-quarantine-all`.
Selected transcript deletion or missing metadata must produce a visible
coverage hold rather than disappear into the watcher's ordinary missing-file
skip. Reappearance alone does not erase a terminal hold.

The current allowlisted child telemetry is Codex-named. Add a Kiro-specific
or versioned shared event with explicit `adapter_format` and selection reason;
preserve existing Codex consumers. Forward it through the allowlist into the
watch journal and retain per-run outcomes from PR #400. Report source ID,
route, outcome, generation, prefix boundary, record/frontier counts, reused
and transformed chunks, actual paid HTTP attempts, local embeddings, elapsed
time, RSS, commit phase timings, and quarantine reason. Do not log chat text.

Incremental transformation still reads/validates the complete source prefix;
it is not constant-memory tail streaming. Neither v2 fingerprints nor the
paid-call reduction solves whole-file scan cost. The byte cap and measured
watcher child RSS remain necessary; PR #404's commit-digest reuse is preserved.

## 8. Safety, recovery, and rollback

The source transcript remains input authority; the checkpoint is processing
authority. Preserve exclusions, production write guard, R2b authority,
source-specific before-images, non-source row/vector equality checks, and
rollback tamper checks from the current Kiro production boundary.

Replay requires supported transaction and recovery-protocol versions,
validated semantic descriptor, source/prefix/metadata continuity, current
writer authority, and unchanged grant binding for bootstrap work. A semantic
fingerprint match alone never authorizes replay. Refuse unknown protocols,
missing prepared artifacts, inconsistent projection evidence, or unproven
rollback authority before provider calls or writes.

Crash expectations: before prepared publication, only durably recorded work
is reusable; after prepared publication, replay makes no additional calls for
that artifact. After partial Chroma apply, exact before-images permit governed
restore/replay; after checkpoint commit, follower repair is idempotent. A crash
after provider response but before durable caching can still cause a repeated
request. Charge the attempted request and do not promise exactly-once billing.
Chroma still lacks an atomic two-collection commit: the canary must measure
the reader-visible mixed-state interval and recovery duration.

Rollback means **hold affected paths and preserve evidence**, not remove them
from `live_sources` or switch incremental indexing off while writers continue.
Those changes would send paths back to legacy. Stop the relevant writers,
retain checkpoint/cache/journals/budgets, diagnose, then resume a compatible
runtime under a separate decision. Old runtimes must not open v2 state.
Returning a migrated source to legacy requires an explicit lineage and paid
rebuild decision; reverting config is not sufficient. Existing corpus entries
remain searchable during a hold, with the coverage lag reported explicitly.

Startup doctor also reported an unrelated Codex `recovery_unproven` pending
transaction. This design neither clears nor repairs it. Before a shared-runtime
deploy or bootstrap window, the operator must establish that no unresolved
writer/recovery state can race the operation; otherwise that stage is NO-GO.
Any separate incident remediation stays with its existing owner and authority.

## 9. Required verification before live use

These are acceptance obligations for later implementation, not tests run by
this design session. Use temporary sources/config/HOME/data roots, fake
providers, network denial, and temporary real Chroma where recovery needs it.
Redirect synthesis-failure logs and all sidecars before imports; do not repeat
the earlier test leak into live `synthesis_failures.jsonl`.

1. **Routing and authority:** exact selected/unselected paths, exclusions,
   copy/rename, wrong adapter, path aliases, symlinks and ownership failures,
   concurrent enrollment/legacy-index race, orphan Chroma lineage, missing
   policy, and shared `allow_full_rebuild=true` with Kiro rebuild disabled.
   Assert zero provider calls and zero unintended mutations on refusals.
2. **Semantic compatibility:** bookkeeping-only revision keeps Kiro-v2 cache
   keys; prompts, models, dimension, adapter contract, metadata interpretation,
   and chunk parameters invalidate appropriately. Grant/coordinator descriptors
   agree exactly. Unknown scheme or unresolved inputs fail closed. Codex's
   current v2 and full-rebuild behavior remain unchanged.
3. **Prefix/sidecar behavior:** multi-chunk append, empty/metadata-only prefix,
   partial final line and split UTF-8, malformed complete lines under the
   existing rejection contract, tool-only records, truncation/replacement,
   same-byte inode replacement, and mutation before/after the selected boundary.
   Title/status/lastModifiedAt changes remain zero-transform when otherwise
   unchanged; session/workspace changes refuse even on the fast unchanged path.
   Exercise sidecar-only events and changes during paid work and replay.
4. **Budget boundaries:** exact N=0/1/60/61/110/111 chunk counts, 20/21 planned
   chunks, maximum file/sidecar bytes, retries, crash after HTTP reservation,
   exhausted aggregate/source budgets, and successor accounting. No wrapper
   retry or new prefix can reset a bootstrap operation's lifetime cap.
5. **Bootstrap/recovery:** old grant rejection, selected-prefix drift, stale
   backup/config/provider binding, one-shot consumption, duplicate invocation,
   no implicit bootstrap, and existing v1 checkpoint/journal refusal. Inject
   crashes before/after prepared fsync, both collection writes, rollback
   publication, checkpoint publication, and each follower update. Verify exact
   restored vectors and untouched non-source rows; preserve failed evidence.
6. **Concurrency/watcher:** source lock spans retry admission and transform;
   global writer scope excludes provider calls; two children cannot double-pay
   one source. Test child `--now`, event coalescing, restart persistence,
   terminal quarantine on later appends, explicit hold release, event forwarding,
   and identity-change events without transcript writes.
7. **Coverage and value:** compare canonical accepted-message/range coverage
   and deterministic fake-provider outputs against full parsing, not only row
   counts. Verify stable chunk reuse, source retrieval of older and appended
   turns, no obsolete provenance, and cold/warm commit behavior. Use real paid
   canary output for retrieval spot-checks, not byte-equality expectations for
   nondeterministic model responses.

## 10. Staged rollout and canary gates

Each stage needs its own reviewed evidence and Ryan authority. These are
rollout conditions, not an Execute task breakdown or a runnable grant packet.

**Stage 0 — Review and hermetic proof.** Kiro reviews this direction. After
Ryan approves it, execution planning specifies the exact implementation and
tests above. Cursor implements only after the later Execute grant; targeted
independent safety review and Kiro review precede Ryan's merge decision.
Merge alone does not change live selection or spending authority.

**Stage 1 — One existing source plus one new source.** Prepare a fresh exact
packet with stopped watcher/other writers, compatible runtime, source and
sidecar identities, backups, configuration values, and budgets. Choose an
existing active source with at most three chunks and bootstrap it to v2:
at most six nominal calls, proposed hard cap 18 actual paid attempts. Enroll
a dedicated new Kiro session before first index to prove initial admission.
The packet pins separate initial/append caps and a durable cohort cap of
**120 actual paid attempts for the entire canary**, including bootstrap,
retries, and recovery, with no automatic replenishment. Implement shared
pre-dispatch accounting before this stage; an operator spreadsheet is not a
hard cap. Budget exhaustion holds sources without destroying their state.

The cohort budget is new shared accounting, not a capability already supplied
by the per-bootstrap journal. Reuse its paid-provider classification and
pre-dispatch reservation semantics. Give the canary ledger an explicit
operation identity and registered mutation path; serialize and fsync each
reservation under a short budget lock while holding the source lock, release
that budget lock before the request, and never acquire it from inside a
Chroma write scope. Reconcile source journals with the cohort ledger, count
crash-ambiguous reservations conservatively, and retain them across child
restarts. Failure to read/lock/persist the budget refuses before dispatch.
This needs concurrent-source and crash tests, not just a sum of success events.

Prove an unchanged rerun uses zero calls and an append spanning a chunk
boundary reuses stable history. Replay faults are proved hermetically first;
live crash injection is not implied. Once baseline indexing/retrieval is
healthy, the separately granted watcher stage runs at least 24 hours and
includes at least ten completed append runs, one mature multi-chunk session,
one watcher restart, and one compatible non-transform runtime transition
with no pending transaction. If workload is insufficient, mark INCONCLUSIVE;
extend only within a renewed duration/budget decision.

Canary PASS requires all of the following:

- Selected-source runs never use legacy. No bootstrap/rebuild occurs from
  watcher events. Excluded and unselected sources retain their prior policy.
- Every selected complete prefix is committed or has an explained visible
  hold; no silent missing turns, unexplained holds, or quarantines remain at
  acceptance. Both pre-existing and appended content are retrievable.
- Unchanged runs and prepared-artifact replay make zero additional transform
  calls. Incremental runs transform only the allowed frontier/new chunks.
- For a mature source, at least one append demonstrates actual historical
  reuse and lower planned paid work than the provider-free full-file
  counterfactual. Report total savings separately from migration cost and
  one-chunk cases; do not impose an invented percentage from Canary 2.
- Actual HTTP-attempt totals reconcile with the durable budget; no uncharged
  retry, cap overrun, or mistaken inclusion of Ollama in paid totals.
- Non-source rows/vectors and recovery evidence satisfy the reviewed
  invariants. No native fault, OOM, deadlock, or unsupported recovery occurs.
  Record maximum RSS, index lag, mixed-collection visibility interval, and
  restart/recovery duration against numeric limits fixed in the later packet.

Any safety failure, unexplained coverage gap, budget violation, or repeated
sidecar refusal stops expansion and holds the affected paths. A passing cost
chart cannot override these gates.

**Stage 2 — Small active cohort.** After accepted Stage 1 evidence, refresh the
ten-source inventory rather than reuse today's filenames/counts. Bootstrap
each authorized source sequentially in the no-other-writer window; proposed
snapshot total is 36 nominal / 108 maximum paid attempts. Give ongoing
watcher operation its own explicit budget and duration, observe another
24-hour window, and compare per-adapter outcomes with the initial canary.
Count the Stage 1 source once if it overlaps the cohort; do not bootstrap it
again. Any additional session is separately enrolled and classified.

**Stage 3 — Steady exact-source operation.** Ryan may approve further active
sessions and operational limits after evidence review. Keep cold historical
sessions excluded or legacy according to their existing policy. Report
residual legacy Kiro and Cursor paid work so partial enrollment is visible.
Automatic future-session admission and Cursor rollout require later direction
approval; neither is quietly enabled by this canary.

## 11. Can Cursor follow the same pattern?

**Yes, with adapter work; not by adding `jsonl_cursor` to an allowlist.**
Reuse exact-source admission, v2 descriptors, resource budgets, transaction
protocol, prepared cache, source/write locks, refusal containment, and staged
bootstrap. Namespace state by Cursor format plus canonical path, never share
Kiro artifacts merely because messages render similarly.

Cursor needs a complete-prefix adapter returning accepted-message byte ranges,
raw-line dispositions, boundary/hash, and identity. Preserve its current
extraction exactly: user/assistant role, text blocks joined with newlines,
tool-only/status lines omitted, and timestamp None. Prove whole-parse/prefix
parity, including multiple text blocks, malformed input and UTF-8 behavior;
any intended parser change must be separately named and versioned. Inspect
whether real Cursor files append, rewrite, compact, or replace during normal
use; continuity refusal is safe but a high refusal rate would defeat value.

Cursor filenames and parser output presently offer no reviewed creation-time
proof comparable to Codex UUIDv7 admission. Start with exact paths. It has no
Kiro-style sidecar dependency, so do not impose Kiro metadata checks. Extend
the governed bootstrap format/provider binding and production recovery tests
explicitly for Cursor. Existing Cursor legacy rows still require a one-time
bootstrap; the current command rejects non-Kiro formats. Capture separate
Cursor inventory and costs: 29 canary runs do not determine unique files or
bootstrap chunks. Kiro evidence cannot sign off Cursor automatically.

## 12. Review disposition and remaining trade-offs

Kiro should review five load-bearing decisions: exact-path enrollment rather
than inferred birth time; v2 plus versioned bootstrap binding as one change;
semantic sidecar continuity; Kiro-specific refusal of automatic rebuild even
when the shared flag is true; and bounded active-cohort bootstrap/canary.

The largest trade-off is incomplete unattended coverage: new sessions stay
legacy until enrolled. The second is paying once to regenerate legacy output
whose prepared-work provenance is unavailable. Avoiding that payment by
inventing cache compatibility is not acceptable. Remaining resource costs
include full-prefix reads, embeddings, and governed Chroma commit work.
Prepared caching limits repeated paid transformations but cannot remove the
provider-response/durable-cache crash window.

The existing STATUS/LATEST need reconciliation when this direction is accepted
or the next milestone lands; this single-document proposal does not rewrite
historical grants or claim the arc is finished. Kiro review comes next, then
Ryan's direction decision and separate execution planning. No PR was opened.

I finished: [Arc Codex] Kiro incremental-indexing design proposal.
Next step: Kiro reviews the five decisions and the safety/canary obligations.
Next lane: Kiro.
See my work: `docs/plans/DESIGN-issue-286-kiro-incremental-indexing.md`.

**TL;DR:** [Arc Codex] Use exact-source Kiro admission, shared v2 semantics,
versioned metadata/bootstrap contracts, and a small paid bootstrap: about 36
calls for the recent ten-source cohort, or 84 for all 18 non-excluded indexed
sessions. Keep normal Kiro rebuilds off; prove coverage, recovery, and savings
in a bounded canary before expanding. Cursor needs its own prefix adapter and
reviewed rollout.

<!-- ref: ./STATUS-codex-jsonl-production-integration.md, ./DESIGN-issue-286-codex-rollout-admission.md, ./incremental_transform_epoch_bump_checklist.md — existing arc and compatibility contracts -->
<!-- src: ../../incremental_jsonl.py, ../../incremental_jsonl_formats.py, ../../incremental_transform_contract.py, ../../incremental_checkpoint_migration.py, ../../scripts/bootstrap-incremental-jsonl.py, ../../bootstrap_safety.py, ../../config.py, ../../watch.py, ../../ingest.py, ../../adapters/kiro_session_jsonl.py, ../../adapters/jsonl_chat.py — baseline routing, transform, recovery, and parser behavior -->
<!-- src: /home/lauer/.config/convmem/config.toml, /home/lauer/.local/share/convmem/processed.json, /home/lauer/.kiro/sessions — read-only aggregate estimates on 2026-10-18; live data changes -->
