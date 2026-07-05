# Percival/Gregory — builder digest (convmem)

**Source:** *Architecture Patterns with Python* · Part I (Domain, Repository, Unit of Work, Aggregates) and Part II (Events, Message Bus, CQRS)

**Read when:** designing ingest adapters, the service layer in `pipeline.py`, event handling in the watch daemon, aggregate boundaries in the ledger, or any question about domain-driven design patterns in Python.

## Principles

- **The domain model is the heart of the system.** All infrastructure (databases, APIs, file systems) exists to serve the domain logic. The domain should be pure Python with no framework dependencies — this is the Dependency Inversion Principle in practice.
- **The Repository pattern abstracts persistence.** The domain model should never touch SQL, files, or Chroma directly. A repository interface sits between them, making the domain testable without real infrastructure.
- **The Unit of Work pattern manages atomicity.** It wraps a set of repository operations into a single transaction that either commits entirely or rolls back. Convmem's `record --approve-last` is a unit of work: the approve either succeeds (indexes) or doesn't.
- **Aggregates define consistency boundaries.** An aggregate is a cluster of domain objects that must be updated atomically. Changes outside the aggregate are eventually consistent. For convmem, a single decision (`dec_prop_*`) with its observations (`obs_*` linked via `relates_to`) is an aggregate.
- **Domain Events decouple side effects.** When the domain does something important (e.g., a decision is approved), it emits an event. Other parts of the system react (e.g., index the decision, update the brief). This avoids coupling the domain logic to side-effect handling.
- **The Message Bus connects events to handlers.** A simple publish/subscribe mechanism routes events to their handlers. Convmem doesn't need a formal message bus today, but the watch → index and record → index flows are exactly this pattern.
- **Commands and Events are both messages, but different.** A command expresses intent ("approve this decision"). An event expresses fact ("decision was approved"). Commands are named with imperative verbs; events with past-tense verbs.

## What this means for convmem

### Repository pattern in convmem

The `ChromaStore` class is already a repository: it abstracts Chroma persistence behind `add()` and `search()` methods. The domain (`query.py`, `ask.py`) never touches Chroma directly. If Chroma's API changes or you switch to a different vector store, only `ChromaStore` changes.

The ledger (file-based JSONL) is its own repository. It doesn't have a formal repository interface yet — `ingest.py` writes to the ledger directly. Adding a `LedgerRepository` class would make the write path testable without touching real files.

### Unit of Work in the decision pipeline

The `record --approve-last` flow:

1. Open the pending queue (start unit of work)
2. Read the latest proposed decision
3. Write the approved decision to the approved JSONL (commit)
4. Index into Chroma (side effect)

Currently steps 3 and 4 are not atomic — if indexing fails, the decision is approved in the ledger but not searchable. A proper Unit of Work would make steps 3 and 4 a single transaction, or at minimum add a compensating action for step 3 if step 4 fails.

### Aggregates in the ledger

Each decision aggregate consists of:
- The decision itself (`dec_prop_*`)
- Its linked observations (`obs_*` via `relates_to`)
- Its verification records (`ver_*`)

The aggregate boundary means: when you update a decision's status (e.g., via `--approve-last`), all linked observations and verifications should be consistent. Currently the link is by ID only — there's no aggregate-level validation.

### Events in the watch/refine daemon

The watch daemon reacts to file-system events (new or modified inbox files). The refine daemon reacts to time events (periodic tick). Both are event-driven architectures at a small scale. Using the book's vocabulary:

- `FileChanged` → `ReIndex(source)` → `Indexer.handle()`
- `Tick(30min)` → `SynthesizeRecent()` → `Refiner.handle()`

The message bus is implicit (polling, file watches). Making it explicit would improve testability and observability.

## F1 refine job queue — commands, events, and handlers

Milestone F's F1 refine daemon runs jobs in **strict dependency order**
(`chroma_dedupe` → `backfill_domain` → `ledger_link` → `semantic_dedupe` →
`confidence_audit` → `redistill`). Map this queue onto the book's message
vocabulary:

| F1 job | Message type | Name (book style) | Handler responsibility |
|--------|--------------|-------------------|----------------------|
| Operator enables refine | **Command** | `RunRefineCycle` | Refine daemon accepts intent to process queue |
| `chroma_dedupe` | **Command** | `DeduplicateChromaRows` | Find twin UUIDs per `ledger_id`; tombstone orphans |
| Tombstone write | **Event** | `UnitSuperseded` | Chroma metadata `superseded: true`, `superseded_by: <uuid>` |
| `backfill_domain` | **Command** | `BackfillDomainMetadata` | LLM cheap pass; metadata-only |
| `ledger_link` | **Command** | `LinkLedgerClusters` | Cluster by site + summary after domains exist |
| `semantic_dedupe` | **Command** | `QueueSemanticPairs` | Pairs → `dedupe_queue.jsonl`; no auto-merge |
| `confidence_audit` | **Command** | `AuditConfidenceHistogram` | Stats to `refine_stats.json`; gates `redistill` |
| `redistill` | **Command** | `RedistillExpensive` | Last; only after audit reviewed |

**Rule:** commands express *what should happen next in the queue*; events express
*what already happened* (tombstone applied, domain written). Handlers must not
confuse a tombstone event with a dedupe command — the command runs the job; the
event is the durable fact other jobs may react to.

### Repository filter as single handler surface

`chroma_store.units_metadata(include_superseded=False)` is the **single filter
point** for tombstoned rows (MILESTONE-F locked). Every read path inherits via
this method — that is Repository pattern discipline: persistence filtering lives
in one adapter, not duplicated in `query.py` / `ask.py` / `ledger.py`.

Anti-pattern: adding `if not superseded` in each caller. One missed caller
re-surfaces orphan twins in `ask` citations.

## Unit of Work rollback — `refine_undo/`

F1 specifies undo artifacts under `refine_undo/<job>/<timestamp>.jsonl` when a
job must be reversed. This is textbook Unit of Work rollback:

1. **Begin** — job starts; optional snapshot of affected UUIDs / metadata
2. **Mutate** — job applies tombstones, domain tags, or queue entries
3. **Commit** — job marks complete in refine stats
4. **Compensate** — on failure or operator undo, append compensating records to
   `refine_undo/` and replay inverse operations (e.g. clear `superseded` metadata)

The ledger remains authoritative: undo files are **operational audit**, not a
second source of truth. Rebuild path is still `convmem index` from ledger if
Chroma state is suspect.

Agents implementing F1 should make rollback **visible** in orchestration
(`refine.py`), not hidden inside a single job function.

## Message bus — formalize before P2?

Today:

- `watch` → `index --file` (filesystem event → command)
- `record --approve-last` → index pass (approve event → derived index update)

These are choreographed workflows (Hard Parts digest), not a formal bus. **P2
gate question:** if MCP `unresolved` or background linker adds cross-surface
reactions, should convmem introduce an explicit in-process event registry
(`on_decision_approved` → `[index_handler, brief_invalidate_handler]`) or keep
implicit chains?

**Default (monolith):** stay implicit until a second handler needs the same
event and duplication appears. **Revisit trigger:** F1 job emits events that
`brief` or MCP must react to without polling Chroma.

## convmem Hooks

- **Domain purity:** `models.py` (PageText, ChunkRecord, SearchHit) should be pure dataclasses with no Chroma or file I/O dependencies. Currently they are — maintain this.
- **Repository abstraction:** ChromaStore is a good repository. The ledger write path should get one too — extract ledger write logic from `convmem.py` into a `LedgerRepository` so the CLI is just a thin delegate.
- **Aggregate consistency:** Before approving a decision, validate that all linked observations exist and are in a consistent state. The aggregate boundary should enforce this, not the CLI handler.
- **Event handlers as explicit wiring:** Replace implicit side-effect chains (record → auto-index) with explicit event → handler wiring. This makes the flow testable and the failure modes obvious.
- **Commands vs Events:** `convmem record` is a command (intent to create). `decision_proposed` is an event (fact that it was created). The CLI should issue commands; the event bus should handle reactions.

## Anti-patterns for Agents

- Do not put Chroma or file I/O logic in the domain models. That's infrastructure leaking into the domain — the book's primary anti-pattern.
- Do not skip repository abstractions because "it's just one machine." The abstraction enables testability. Test without Chroma by mocking `ChromaStore`.
- Do not let aggregates span multiple consistency boundaries. If a decision and its verification are in different aggregates, they can't be updated atomically. Either merge the aggregates or accept eventual consistency between them.
- Do not use events for commands. Calling a message "DecisionApproved" when it actually means "please approve this decision" confuses intent with fact. Commands are requests; events are notifications.
- Do not let side effects hide inside domain code. If `record` also triggers indexing, that should be visible at the orchestration level (pipeline.py), not hidden inside the domain logic.

## Related digests

- **DDIA** — the data system architecture that hosts the domain patterns. Repository and Unit of Work are implementation patterns; DDIA provides the data system theory.
- **Ousterhout** — the Service Layer pattern (ch. 4 in Architecture Patterns) is a deep module: narrow interface (orchestration commands), broad behavior (hides domain + infrastructure coordination).
- **Hard Parts** — event-driven architecture is one of the integration styles analyzed in the saga patterns. The watch daemon's event flow is a choreographed workflow.
