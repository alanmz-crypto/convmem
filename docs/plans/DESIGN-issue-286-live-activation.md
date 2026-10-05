# Issue #286 — guarded live incremental indexing design

**Arc: Trapdoor Hunt (#286), using the Arc Codex incremental engine.**
**State:** Kiro design PASS at `e4fa954`; RC-1 through RC-3 bind the branch
implementation. Copilot safety audit and exact-tip documentation recheck remain
open. No live grant.
**Base:** `origin/main` `ff5ce7b` on 2026-10-05.

## Product result and boundary

Stop repeated paid transforms of unchanged transcript chunks while preserving
complete source coverage and crash recovery. The first release keeps full-prefix
reads and hashes; it reduces model calls, not source I/O. The default-off
engine and the current `a92a74e` runtime pin remain unchanged until Ryan
separately grants a promotion and live test. Ryan requested temporary cost
containment on 2026-10-05: `convmem-watch.service` is stopped and disabled.

The reviewed S0–S3 branch `19d34a5` is 42 commits behind and 14 ahead of
current `origin/main`. Its Copilot documentation-acceptance FAIL at `e99856e`
still needs an exact-tip recheck; the later `19d34a5` docs correction is not
treated as a PASS. Bring only reviewed behavior needed for this route onto the
fresh branch; do not switch the shared checkout or rewrite either reviewed ref.

## Current failure modes

1. With no `[index.incremental_jsonl]` table, `maybe_route_incremental` returns
   `None` and legacy indexing runs. With the table enabled, a detected Kiro
   source reaches a hard `"skipped"` result when `CONVMEM_INCREMENTAL_ROOT` is
   absent. `ingest.py` treats the tuple as handled, so legacy indexing does not
   run. The config-only toggle is therefore neither a cost fix nor a coverage
   preserving rollout.
2. `CONVMEM_INCREMENTAL_ROOT` is a hermetic-test authority, not a production
   enable switch. `IsolationBoundary.from_environment` requires a fresh marker
   and token, rejects production overrides and inherited credentials, contains
   every mutable role under its root, and requires fake providers. Giving the
   live watcher this variable would misuse the test contract and cannot safely
   operate on the live corpus.
3. Without a checkpoint, a processed entry or Chroma source rows yields
   `bootstrap_required`; the coordinator returns `"skipped"`. Thus merely
   unblocking the live branch would silently stop updates for existing files.
4. The format registry covers Kiro and isolated Codex JSONL. Cursor
   `jsonl_cursor` has a legacy parser but no complete-prefix spec. Crush is
   `sqlite_crush`, not JSONL; its live DB is currently skipped by watch. This
   JSONL engine cannot claim to solve Crush SQLite reprocessing.

## Chosen design

### Two distinct boundaries

Keep `IsolationBoundary` unchanged for hermetic workers. Add a separate
production boundary that grants only these configured roles: the one selected
read-only source, the incremental state tree, the configured Chroma directory,
processed log, export file, dedupe sidecars, writer lock, attestation directory,
and census directory. Resolve paths canonically, reject symlink components and
role overlap, validate a regular owned source opened with `O_NOFOLLOW`, and
validate all roles before creating a directory or provider object. The
coordinator's transaction/replay machinery remains shared. The production
boundary does not relocate HOME, install network denial, or require a fake
provider. A production flag must never make the hermetic boundary permissive.

### Exact source selection and fail-closed routing

Keep the existing `enabled = false` default. Production routing requires an
additional explicit exact-path source grant in configuration (no wildcard or
directory-only grant for the first live slice). `enabled = true` without a
source grant remains inert and observable, not `"skipped"` for a changed file.
Selected live sources also require an explicit positive embedding dimension;
the coordinator's historical default of 8 is a hermetic fake-provider value
and must never be assumed for the live model. A wrong dimension fails before
publication and requires a corrected reviewed grant.
Hermetic routing still uses the tokenized root. A selected source must have a
supported format and an existing valid checkpoint before automatic watcher
routing. Missing/corrupt checkpoint, incompatible fingerprint, unexpected
source mutation, or unauthorized rebuild produces a visible nonzero failure
and no processed/checkpoint advance. An unselected source continues through
legacy indexing; exclusions and force/supersede semantics remain governed by
the existing call site. Never silently turn a selected source's refusal into
legacy full reprocessing, because that hides both cost and coverage failure.

### One-source bootstrap before watcher enable

Existing sources require a separate, one-shot exact-resource operation to
create a checkpoint. Before any live bootstrap, inventory processed entries,
both Chroma collections, export/dedupe rows, source identity and complete
prefix digest; take the existing complete-data backup gate. The operator pins
the exact source path and digest and accepts a measured one-time full-transform
budget. The coordinator prepares outputs durably before writes, snapshots
source-scoped before-images, applies and prunes a complete physical keep set,
publishes checkpoint first, then followers and `processed.json`. A mismatch or
ambiguous preimage refuses with no publish. This work does not infer a cursor
from `processed.json` or Chroma rows alone. Source bootstrap is never triggered
by ordinary watcher events. The candidate branch must prove rollback and
replay with fake providers and real temporary Chroma before any live grant.

The branch provides `scripts/bootstrap-incremental-jsonl.py` as a one-shot
candidate. It is not called by `watch.py` or `ingest.py`. Invocation requires
`--execute` and a mode-0600 JSON grant containing exactly the source path,
complete-prefix SHA-256, complete byte boundary, maximum transform chunks,
embedding dimension, and verified backup snapshot ID. The script checks that
watch is inactive and disabled, then checks the source digest and chunk cap
before calling the coordinator. It selects the source only in its in-memory
config; it does not edit the live TOML or start a service. The backup ID is a
reviewed operator assertion, so Ryan must verify the snapshot separately
before execution. A failed bootstrap can be resumed only through the same
one-shot path with the same grant; a generic watcher event refuses a marked
bootstrap transaction.

An alternative, zero-call adoption from legacy rows was considered. It would
need an exact mapping from every source chunk to summary/unit physical IDs,
prepared provider output, provenance, dedupe suppression, and recovery state.
The current legacy data does not establish that proof. The one-time rebuild
cost is explicit and bounded to a reviewed source, while later appends reuse
prepared historical transforms. If Ryan does not accept that bootstrap cost,
the source stays on the legacy route or watch stays paused; no zero-call claim.

### Coverage decision

The first live candidate is one Kiro JSONL source with an exact grant. Carry
the reviewed Codex history/rollout S0–S3 contracts onto current main, then
prove production boundary parity for one Codex source before its own grant.
Cursor JSONL needs its own versioned complete-prefix adapter, raw-line outcome
parity, rotation/rewrite tests, and review before routing. Crush SQLite needs
a separate SQLite snapshot/cursor design; do not insert it into a JSONL format
registry or claim this issue removes its cost. Report paid-call counts by
source format before claiming overall DeepSeek reduction. Markdown and other
watched files remain legacy; their cost is outside the JSONL claim.

## Verification and release order

Kiro's exact-tip design PASS at `e4fa954` binds three implementation checks:
RC-1 distinguishes unselected legacy routing, selected success, and selected
visible nonzero refusal; RC-2 forbids using the hermetic root or other
isolation environment variables as live authority; RC-3 proves generic
watcher/ingest events cannot invoke the one-shot bootstrap. These are not
production grants. Copilot's independent safety audit and the older
documentation-acceptance recheck remain outstanding.

1. Copilot audits isolation, fail-closed behavior, first-source bootstrap,
   and the prior docs acceptance failure. Kiro's design PASS at `e4fa954`
   does not transfer to later implementation tips; Kiro rechecks the final
   exact tip. A review is not a live grant.
2. Implement boundary and exact-source gate with no service/config edits. Test
   off/invalid config, unselected/selected sources, old processed data, symlink
   and role-alias attacks, provider denial, crash points, both Chroma
   collections, sidecars, and unrelated sources. Use network-denied fake
   providers and temporary real Chroma. Compare complete generations with the
   legacy clean-rebuild oracle and record transform-call counts.
3. Implement and review a one-shot bootstrap separately. It must be impossible
   for a generic watcher event to request it. Run focused and repo CI gates,
   then request fresh exact-tip Copilot PASS and Kiro PASS. Prior verdicts do
   not transfer to a new tip.
4. Only after Ryan's explicit source/digest/budget grant, perform the one-source
   bootstrap and measure it. Only after a separate watcher/config/restart grant,
   promote a reviewed runtime revision and test one appended message. Compare
   paid calls, coverage, projection IDs, rollback evidence, and health before
   expanding the exact source list. Ryan alone merges and grants activation.

The watcher remains disabled until a separately authorized restart. The
runtime pin, OpenClaw manifest, monitor timer, shadow ledger, and model
selection remain untouched by this branch.
