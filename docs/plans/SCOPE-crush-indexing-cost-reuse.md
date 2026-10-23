# [Arc Codex] Scope — stop paying again for unchanged Crush history

**Date:** 2026-10-23

**Owner:** Codex, planning and future implementation; Claude, independent review.

**Issue:** #393, changed Crush databases repeat historical summary/distill calls.

**Baseline:** `origin/main` at `3d24c753a4b46132d349c34a2cd37b0fbba464c2`.

**State:** scope proposal; no architecture approval or implementation grant.

## Outcome and authority

Ryan authorized parking doctor acknowledgment and scoping #393 on 2026-10-23.
This document defines the next design task, its boundaries, and the evidence
needed to approve implementation. It is not an ARCHITECTURE/EXECUTION packet.
It stays within Arc Codex's ingestion-cost follow-up; it creates no new arc.

The product outcome is that adding or updating messages in one Crush session
does not require summary/distill calls for unchanged chunks in other sessions.
Once a successful provider result is durably saved, a retry should reuse it.
The first capture and genuinely changed provider inputs can still cost money.
This is a paid-transform guarantee, not a promise of incremental SQLite reads,
zero embedding work, or exactly-once remote billing.

The earlier acknowledgment work is **PARKED**, not completed or approved.
Its original Timeshift event is absent from the new current boot. Ryan waived
the separate known CPU-7 doctor failure for session progress. No tripwire
policy or deployment acceptance criterion changed. The acknowledgment design
would still need its malformed-read and post-revocation defects corrected if
Ryan later resumes it.

## Evidence already available

Claude filed #393 on 2026-10-14 with a fake-provider probe against `41561ef`:
the first 12-message index called summarize/distill 3/3 times, an unchanged
repeat called them 0/0 times, and appending one message called them 4/4 times.
Those are recorded prior results, not measurements rerun in this scoping task.
No paid canary is needed to establish that reported symptom again.

The following mechanisms were inspected at the baseline above:

- `ingest.py:_index_one_file` hashes the whole file, skips an already processed
  hash, then attempts the incremental route. A changed Crush file reaches
  `_process_file_chunks`, which calls `build_chunk_artifact` for every chunk.
- `incremental_jsonl.py:decide_eligibility` and the format registry admit
  selected JSONL formats, not `sqlite_crush`. Their continuity proof uses
  unchanged raw-byte prefixes, device/inode identity, and complete-line
  coverage. Adding Crush to an allowlist would not supply a SQLite proof.
- `adapters/sqlite_chat.py:_parse_crush` sorts by `session_id, created_at, id`,
  extracts accepted user/assistant text, and flattens all sessions into one
  list. The query uses `id` as a tie-breaker but does not retain it in the
  canonical message. `chunk_messages` then windows across that entire list.
- `build_chunk_artifact` calls summarize and distill before the downstream
  exact-duplicate/export suppression. It also creates embeddings, IDs,
  locators and provenance. A complete artifact is not a reusable provider
  result independent of its source and projection location.
- `parse` opens SQLite with `mode=ro`; that does not make a main-file hash a
  logical snapshot identity or cover changes committed only in a WAL.

The saved probe proves repeated calls. Source inspection exposes an additional
scope constraint: appending to an earlier-sorting session shifts subsequent
global chunk windows. No new measured cache-hit rate is claimed here.

## Approaches and proposed direction

1. **Cache the existing global chunks.** Smallest possible mitigation and
   useful for exact repeated prompts. It cannot guarantee reuse for unchanged
   sessions when another session shifts their chunk windows. Do not call this
   alone a complete fix or close #393 on its evidence.
2. **Admit SQLite directly to the JSONL coordinator.** Reuses substantial
   transaction machinery but assumes byte-prefix continuity that SQLite does
   not provide. Reject this shortcut; a different source contract would be
   required before any coordinator generalization.
3. **A Crush-specific logical capture with session-local chunks and durable
   provider-result reuse.** Proposed direction for the binding design. Keep
   the current CLI and governed writer boundaries; reuse proven helpers only
   where their contracts actually fit. Its larger first-change cost buys a
   testable cross-session cost bound rather than a cache-hit assumption.

This is a recommendation for design review, not an approval to build option 3.
If Ryan chooses the smaller cache-only mitigation, label it partial and leave
the cross-session part of #393 open.

## Minimum complete scope

The next architecture must specify all of the following before Execute:

1. **Consistent source capture.** A read-only, bounded SQLite snapshot includes
   committed WAL data, never checkpoints or changes source database/WAL
   contents, and records a verifiable logical identity. Define the permitted
   shared-memory (`-shm`) interaction instead of assuming `mode=ro` has no
   filesystem effects. Define behavior for a busy/corrupt database,
   concurrent commits, replacement, rollback, and unsupported schema. A
   selected source must not silently fall through to a paid legacy rebuild.
   Place selected-Crush admission before, or explicitly replace, the unchanged
   main-file-hash skip in `_index_one_file`; otherwise a WAL-only change never
   reaches this capture.
2. **Stable session and message identity.** Retain the native session/message
   IDs and content fingerprints. Specify deterministic order for equal times,
   edits, late inserts, deletions, filtered parts, mixed timestamp units and
   session compaction. Retaining native IDs changes the adapter contract;
   define how null/invalid session IDs are refused or grouped. An ID alone is
   not evidence that content is unchanged.
3. **Session-local work selection.** Chunks do not cross session boundaries.
   A new or changed session cannot shift another session's input windows.
   Changes near a boundary revisit the necessary overlap/tail. Hash the actual
   provider-consumed input; the previous last message is not assumed immutable.
4. **Durable provider results.** Treat summary and distill as separate stages.
   Key reuse by the approved source scope, exact request/prompt, resolved
   provider/model/endpoint, generation parameters, and versioned cache/parser
   contract. Keep credentials out of keys and evidence. A same-named mutable
   model or changed fallback binding needs an explicit reuse policy. Save a
   successful stage before embedding or downstream writes, so those failures
   do not cause a successful generation to be purchased again.
5. **Fresh projection and provenance.** Do not cache and transplant complete
   `ChunkArtifact` objects. Bind reused responses to the captured records,
   current locators, and correct generation evidence, then normalize/embed and
   write through the existing governed paths. Specify how cache hits are
   reported without counting them as fresh provider HTTP attempts. A valid
   empty distillation is reusable; exceptions, malformed output and degraded
   partial artifacts are not successful cache entries.
6. **Recovery and concurrency.** Define cache atomicity, integrity checks,
   bounded storage, lock scope/order and same-source races. No provider call
   under a production write lease. A corrupt/missing entry must not silently
   count as a hit; whether a miss may spend requires a reviewed budget/refusal
   rule. Preserve the source-to-processed publication fence. Define a private
   cache location, permissions and retention; purge/exclusion must delete or
   invalidate affected cache entries themselves, not just serving rows. Use
   digests instead of storing full prompts unless reconstruction needs them.
   The crash-safe paid-attempt budget introduced for the opt-in Kiro route
   through PR #406 is a reference, not an inherited Crush spending grant.
7. **Adoption and read compatibility.** Session-local chunk addresses differ
   from today's global offsets. Specify summary/unit IDs, before-images,
   replacement/pruning, transcript expansion, and provenance locators before
   changing them. Two sessions both have offset zero; include session identity
   in addresses rather than colliding on a global-offset ID. The existing
   `bootstrap_required` outcome is the adoption precedent. Existing stores
   and `processed.json` are not proof of a
   populated new cache. Any warm-up/backfill cost, migration or rebuild needs
   its own exact-source proposal and Ryan decision.
8. **Explicit admission.** Decide the disabled default, exact source selection,
   feature setting, rollback and refusal behavior. Explicit `index --file`
   requests for Crush databases outside watch roots are the initial target.
   Specify interactions with CLI watch deferral and the watcher's own hash-based
   skip/trigger gates. No automatic WAL-only watch-trigger guarantee is claimed
   by this scope; such support needs an explicit design rather than assuming
   the later SQLite capture creates an event. Keep unselected formats and
   current Codex/Kiro settings unchanged. Do not reuse their live grants.

Capture hardening and cost reuse may be phased, but capture-only work cannot
be reported as closing #393.

There is an unavoidable gap between a provider completing a billable request
and the local result becoming durable. The design must state that crash window
honestly; local caching cannot promise exactly-once provider billing.

## Implementation boundary to estimate in the next plan

Candidate owners are a dedicated Crush capture/coordinator/cache module,
the Crush adapter, the narrow routing and artifact-building seams in
`ingest.py`, disabled configuration/admission, isolated tests, and manifest
classification. This is a candidate surface, not an approved edit allowlist.

The next design must name any changes needed for transcript expansion and
governed writer inventories. Do not smuggle them into a supposedly cache-only
patch. Reuse the existing JSONL transform contract as a reference; do not
change its epochs, checkpoint migration, prompt templates or recovery protocol
merely to add a Crush route. If shared code must change semantics, inventory
the effect and require explicit review before implementation.

No doctor-acknowledgment implementation, host repair, watcher restart, watch
root addition, live configuration, Chroma operation, quarantine clearing,
bootstrap, provider canary, retrieval-ranking change, or protocol deployment
is part of this scope. In particular, scoping #393 does not authorize the
separate #286 measurement reconciliation or retrieval #320/#263 work.

## Acceptance evidence the implementation must eventually supply

Use fake providers and synthetic SQLite databases only, with HOME/config,
Chroma, exports, logs and state redirected before imports. Deny network and
production path access. Real host databases are not test fixtures.

- Reproduce first index, unchanged repeat and one appended message. Report
  actual summarize and distill HTTP-attempt counters separately, plus cache
  hits and embeddings. Historical paid calls remain zero for unchanged inputs.
  Pin concrete chunk sizes, overlap and expected per-stage attempt counts for
  the affected session's tail/new windows; also assert the appended content is
  present so a skipped capture cannot satisfy the zero-call claim vacuously.
- Use two sessions; append to the earlier-sorting one. The other session's
  chunks remain unchanged and require zero historical summary/distill calls.
- Edit an existing message without changing its ID, add a late message, remove
  one, and cross overlap/tail boundaries. Recompute affected inputs without
  reusing stale content or disturbing the unaffected session.
- Commit into WAL without relying on a changed main-file hash. New committed
  content is captured; a concurrent transaction cannot produce a mixed view.
- Change prompt/model/endpoint/effort/parser versions and exercise fallback.
  A request from another transform contract is never treated as a hit.
- Fail after a durable summary but before embedding/distill; then after
  durable distill but before apply. Retry reuses each saved successful stage.
  Also test interrupted/corrupt writes, lock contention and duplicate workers.
- Verify valid empty distill, malformed output, exclusions, purge, stale rows,
  migration refusal, same-source publication fencing, and legacy rollback.
- Prove old/new IDs and transcript expansion remain correct, and run existing
  Codex/Kiro contract and fault/replay regressions. Full store rebuilds or
  already-successful paid canaries are not routine verification steps.

These are required future checks, not passing test results from this scope.

## Next deliverable and review gate

The recommended next planning task is for Codex to draft a binding
architecture and execution plan for option 3 after Claude scope review.
This scope proposes the direction; it does not approve that future design.
No additional direction-choice hard gate is created here: Ryan can steer the
proposal, and design review plus his separate Execute decision still apply.
Resolve the capture identity, chunk/address compatibility, cache contract,
corruption/spending policy, and adoption questions in those documents; do not
leave them for the implementer to guess. Continue using this Arc Codex STATUS
unless Ryan explicitly creates a new arc.

Then Claude reviews the exact design revision. Ryan's bounded Execute grant,
implementation review, PR/merge decision, exact-SHA runtime promotion and any
live-source/model-cost grants remain separate. Codex is Ryan's chosen
implementation lane for this follow-up; this does not rewrite other arcs'
team ownership.

**TL;DR:** [Arc Codex] Doctor acknowledgment is parked. Scope #393 as a
Crush-specific, session-aware path with durable provider-result reuse. A cache
of today's global chunks alone is partial. Capture, identity, compatibility,
spending and adoption rules must be designed and reviewed before Execute.

<!-- ref: ./STATUS-codex-jsonl-production-integration.md, ../inter-model/LATEST.md — current priority, ownership and gates -->
<!-- src: ../../adapters/sqlite_chat.py, ../../ingest.py, ../../incremental_jsonl.py, ../../incremental_jsonl_formats.py, ../../incremental_transform_contract.py, ../../distill.py, ../../llm.py — source, chunk, transform and commit boundaries inspected at the baseline -->
<!-- src: ../inter-model/CODEX-2026-10-22-doctor-ack-next-model-handoff.md — previously recorded #393 probe and separate work queue -->
<!-- src: ../builder-reference/ousterhout-builder-digest.md, ../builder-reference/hard-parts-builder-digest.md, ../builder-reference/ddia-builder-digest.md, ../builder-reference/arch-patterns-python-builder-digest.md, ../builder-reference/zeller-builder-digest.md — module boundaries, alternatives, ownership and verification discipline -->
