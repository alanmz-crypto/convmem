# Cursor → Codex: Shadow Ledger Phase 0 Architecture work order (verbatim)

**Who:** ChatGPT authored this work order; Cursor packages it for provenance.  
**What:** Exact Codex Architecture Planning brief for Shadow Ledger Phase 0.  
**When:** Work order used to author [#115](https://github.com/alanmz-crypto/convmem/pull/115);
salvaged to Git 2026-07-24 after Architecture HITL lock (tip carried
`ARCHITECTURE-shadow-ledger-phase0.md`).  
**Why:** The packaging step was superseded when #115 appeared; the verbatim
text lived only in chat until this file.  
**How:** Treat Section “Exact ChatGPT/Codex work order” as immutable intake.
Architecture Direction is already **HITL approved** on #115 — do **not**
re-open Architecture authorship from this file. Next planning step remains
Gate 1b, then Codex `EXECUTION-shadow-ledger-phase0.md` under a **separate**
Ryan grant. Cursor Execute still forbidden.

## Provenance and authority

| Item | Value |
|---|---|
| Work-order author | ChatGPT Cloud (strategy) |
| Planning lane | OpenAI Codex |
| Implementation lane | Cursor — **not authorized** by this document |
| Architecture artifact | [`docs/plans/ARCHITECTURE-shadow-ledger-phase0.md`](../plans/ARCHITECTURE-shadow-ledger-phase0.md) |
| Architecture HITL | **APPROVED** Ryan 2026-07-24 (Kiro Gate 1b + lock-timeout revisions applied) |
| Related intake | [`CURSOR-2026-07-24-shadow-ledger-phase0-chatgpt-handoff.md`](CURSOR-2026-07-24-shadow-ledger-phase0-chatgpt-handoff.md) |
| Implementation Handoff (local draft input) | `~/.cursor/plans/shadow_ledger_phase_0_cadca832.plan.md` |
| Audit baseline | `docs/audit-ledger-first/` on `main` via [#117](https://github.com/alanmz-crypto/convmem/pull/117) |

## Working-tree audit-document status (historical)

When Codex first ran this work order, `docs/audit-ledger-first/` was often
untracked / missing from the Codex worktree. That blocker is **resolved for
location**: the eight-file pack is on `main` via #117 with Architecture-required
correction banners. Further factual corrections still need Ryan Gate 1b
confirmation before Execution Planning is authorized.

## Exact ChatGPT/Codex work order — verbatim

The following block is the work order as supplied by Ryan (2026-07-24). Do not
summarize or rewrite the eleven decisions when citing this intake.

````markdown
# Codex Work Order — Plan Shadow Ledger Phase 0
You are the **planning lane**, not the implementation lane.
Follow the repository Planning OS exactly:
1. Read:
   * `AGENTS.md`
   * `docs/PLANNING-PROTOCOL.md`
   * `docs/planning/ARCHITECTURE-PLANNING.md`
   * `docs/reasoning-modes.md`
   * `docs/MODEL-WORKFLOW.md`
   * `docs/builder-reference.md`
   * the supplied `Shadow Ledger Phase 0 Implementation Handoff`
2. Inspect the actual repository and establish:
   * current branch
   * current tip SHA
   * worktree status
   * whether `docs/audit-ledger-first/` exists on another branch, worktree, or supplied source
   * every production mutation route for the `knowledge_units` Chroma collection
3. Begin in **Architecture Planning**. Do not enter Execution Planning and do not modify runtime code.
## Source authority
Treat these points as already decided and do not reopen them:
* Chroma remains Tier-1 truth during Phase 0.
* The new ledger is shadow/candidate evidence only.
* No production read-path change.
* No restore-order change.
* No production migration or live Chroma rewrite.
* No canonical-schema freeze.
* No Neutral Core or Office Team work.
* No unification of observation and governed-decision authority.
* Shadow append failure must be visible but must not roll back or block a successful Chroma write.
* Disposable replay must never target production Chroma.
* Ryan approval is required before write-path hooks land and again before any later cutover work.
## Architecture question
Choose one architecture for recording every successful production mutation of Chroma knowledge units into a durable, append-only, non-authoritative shadow ledger without causing recursive writes, changing Chroma authority, or silently omitting mutation routes.
## Required system boundary
### In scope
* Append-only shadow event writer.
* Serialized append, flush, and fsync.
* Tail validation and corruption classification.
* Complete production mutation coverage.
* Creation, full update, metadata update, supersede, restore, and hard-delete events.
* Structured failure visibility and audit-gap reporting.
* Disposable replay into a temporary Chroma root.
* Final-state comparison against production.
* Chroma-only inventory.
* Candidate-only legacy-decision classification.
* Phase-0 readiness report.
* Documentation of the unchanged backup and restore doctrine.
### Out of scope
* Production reads from shadow.
* Production rebuild from shadow.
* Live migration.
* Rewriting `knowledge_units.jsonl`.
* Changing Restic restore selection or recovery authority.
* Final canonical schema declaration.
* Decisions-ledger authority changes.
* Neutral or Office Team implementation.
* Automatic repair or classification of historical production records.
## Repository findings that the architecture must address
The originally named mutation routes are not the entire writer inventory. Inspect and account for at least:
* `observe.ingest_observation`
* `observe.repair_empty_ledger_documents`
* `verify.verify_unit`
* `ingest._commit_chunk_to_stores`
* forced reindex supersede and delete paths
* `inter_model_index.index_inter_model_messages`
* governed-decision ingestion in `propose_decision.py`
* `refine.py` metadata and tombstone jobs
* `convmem forget`, including undo/restore
* `source_purge.py`
* write-capable MCP routes
* every caller of:
  * `ChromaStore.add_unit`
  * `ChromaStore.update_unit`
  * `ChromaStore.update_unit_metadata`
  * `ChromaStore.supersede_units_for_source`
  * `ChromaStore.delete_units_for_source`
Do not treat a grep list alone as proof of coverage. Establish whether any code mutates the Chroma collection directly.
## Architecture options to compare
Compare no more than these three approaches:
### Option A — Scattered domain hooks
Each business operation explicitly appends its shadow event after its Chroma mutation.
Assess drift risk, repeated record construction, and missed future writers.
### Option B — ChromaStore mutation sink
Add an optional mutation observer/sink to `ChromaStore`. It is disabled by default. A production write-store factory installs the shadow sink when Phase 0 is enabled. Direct read stores, tests, restore verification, and disposable replay do not install the sink.
Assess whether this captures all mutation semantics, including bulk supersede and hard deletion.
### Option C — Higher-level write service
Place all unit mutations behind a new service and migrate existing callers to it.
Assess migration size, bypass risk, and whether it is too large for Phase 0.
Unless repository evidence contradicts it, prefer **Option B** because it centralizes coverage while remaining opt-in and avoids recursive shadowing during replay.
## Decisions the Architecture Direction must make
Do not leave these as later implementation choices.
### 1. Activation and dependency boundary
Specify:
* exact configuration shape
* behavior when the configuration section is absent
* how production writers receive the sink
* how tests explicitly enable it
* how temporary replay explicitly disables it
* whether the shadow path defaults to the configured Chroma data root’s parent
Recommended default:
* feature absent or disabled means no shadow writes
* Ryan enables it explicitly for Phase 0
* once enabled, every production knowledge-unit mutation is observed
### 2. Mutation envelope
Define a provisional Phase-0 envelope containing at least:
* `shadow_schema_version`
* `event_id`
* deterministic `mutation_fingerprint`
* `event_type`
* `recorded_at`
* `chroma_id`
* `ledger_id`, when present
* resulting document, when the unit still exists
* resulting replay-relevant metadata
* pre-delete identity/state for a hard delete
* `state_hash`
* embedding-model tag
* operation provenance or writer route
* explicit `candidate` or `shadow` authority marker
The schema must remain labeled provisional and non-canonical.
### 3. Event vocabulary
Cover final-state semantics for at least:
* `unit_created`
* `unit_replaced`
* `unit_metadata_updated`
* `unit_superseded`
* `unit_restored`
* `unit_deleted`
Do not force governed-decision lifecycle events into this vocabulary. The shadow records the resulting Chroma projection mutation; it does not replace `decisions-approved.jsonl` or proposal lifecycle logs.
### 4. Hash boundary
Do not rely exclusively on `ledger_content_hash()`.
Define a separate deterministic projection-state hash over:
* stable unit identity
* document
* replay-relevant metadata
Exclude:
* raw embedding vectors
* Chroma-generated/backend-only fields
* transient process information
State whether timestamps are included and why. Ensure metadata-only changes can produce a different state hash.
### 5. Duplicate and uncertain-ack behavior
Specify:
* unique event identity
* deterministic mutation fingerprint
* replay behavior for repeated event IDs
* replay behavior for different event IDs that produce the same final state
* reporting of exact duplicate lines
* reporting of conflicting events with the same mutation identity
The replay must be idempotent. Duplicate final-state application may be a no-op, but conflicting duplicates must fail visibly.
### 6. Append and lock protocol
Specify the exact order:
1. Chroma mutation succeeds.
2. Build the resulting shadow event.
3. Acquire the shadow lock.
4. Validate the append boundary.
5. append exactly one complete UTF-8 JSON line
6. flush
7. fsync the file
8. release the lock
Define the global lock-order relationship with existing governed, source, and export locks. The shadow writer must never acquire a source, export, or governed lock while holding its own lock.
### 7. Corruption handling
Define behavior for:
* empty file
* clean newline-terminated file
* truncated final record
* invalid middle record
* valid duplicate record
* non-object JSON record
Recommended direction:
* truncated final bytes may be copied to a quarantine artifact and the file safely truncated to the previous complete newline while holding the lock
* invalid middle content fails closed for replay and append
* corruption is never silently skipped
* recovery actions affect only shadow artifacts, never Chroma
### 8. Failure visibility
A post-Chroma shadow failure cannot be rolled back.
Specify:
* structured logger/error event
* best-effort failure journal that contains identifiers but not sensitive payloads
* a counter or reportable gap condition
* how later reconciliation marks the run unready
* behavior when both the shadow file and failure journal are unwritable
The caller’s successful Chroma mutation must still return successfully.
### 9. Disposable replay
Specify:
* mandatory temporary output root
* path checks preventing equality with, parenthood of, or child relationship to production Chroma
* no shadow sink on the temporary store
* checkpoint scoped only to the temporary replay root
* deterministic event reduction
* content comparison categories:
  * missing in shadow
  * missing in Chroma
  * state-hash mismatch
  * duplicate event
  * conflicting mutation
  * extra final state
Define two embedding modes:
* deterministic stub embeddings for hermetic automated tests
* configured model re-embedding for live disposable validation
Raw embeddings are not part of equality.
### 10. Inventory and classification boundary
The inventory tools must calculate current counts rather than hardcode 192 or 3,448.
Define:
* active Chroma IDs absent from `knowledge_units.jsonl`
* safe category hints
* machine-readable report output
* no document or secret payload printed by default
* legacy candidate classes:
  * matched governed decision
  * likely observation
  * ambiguous
* no automatic rewrite, ingestion, deletion, or authority transfer
### 11. Backup doctrine
Document only:
* Chroma remains the restore truth.
* Existing Chroma backup and restore behavior remains unchanged.
* The shadow file may receive a separate lightweight backup for validation continuity.
* No restore script may select or project from shadow in Phase 0.
Do not modify the Restic live-write gate or restore drill to make shadow authoritative.
## Required Architecture Direction output
Create:
`docs/plans/ARCHITECTURE-shadow-ledger-phase0.md`
It must follow the repository Architecture Planning artifact format and contain:
* Planning Status
* source and authority
* system boundary
* current writer inventory
* constraints and invariants
* the three options
* one chosen direction
* rejected alternatives
* lock-order decision
* activation decision
* event and hash boundaries
* replay and corruption policy
* risks and reversibility
* missing-input/blocker section
* downstream handoff
The missing `docs/audit-ledger-first/` documents must be handled explicitly:
* locate and cite their actual branch/source, or
* record them as a blocker to the documentation-landing task
Do not reconstruct unseen audit documents from the handoff.
## Expected downstream artifacts after HITL approval
Name, but do not create or execute yet:
* `docs/plans/EXECUTION-shadow-ledger-phase0.md`
* `docs/plans/VERIFY-shadow-ledger-phase0.md`
The later Execution Plan should be bounded to five deliverables:
1. Baseline documents and Phase-0 configuration contract.
2. Shadow writer, mutation sink, and complete writer coverage.
3. Durability, corruption, concurrency, and failure tests.
4. Disposable replay and final-state comparison.
5. Inventory tools and Phase-0 readiness report.
## Stop condition
Emit the Architecture Direction only.
Do not:
* modify Python runtime code
* add the shadow writer
* hook Chroma
* create migration tools
* alter backup or restore behavior
* write a ledger decision
* self-transition to Execution Planning
End with:
`Active phase lane must stop here. Await HITL.`
````

## Cursor stop condition

Packaging complete. No Architecture rewrite, no Execution Planning, no Python,
no hooks, no backup/restore changes from this file alone.
