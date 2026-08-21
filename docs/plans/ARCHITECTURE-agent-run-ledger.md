# Architecture Direction — Agent Run Ledger

> **Arc: Runway Ledger** — ConvMem Agent Run identity tracking.
>
> This is an architecture plan, not an implementation authorization. Kiro
> reviews the architecture and execution package; Ryan owns the architecture
> and execution gates; Cursor owns any later implementation.

| Field | Value |
|---|---|
| **Status** | Architecture planning; implementation, hook installation, and live capture are not authorized by this document |
| **Arc codename** | **Runway Ledger** |
| **Owner** | Ryan owns HITL decisions and external hook installation; Codex authors the plan; Kiro reviews; Cursor implements after authorization |
| **Base** | `origin/main` at `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481` when this package was prepared |
| **Primary storage** | `~/.local/share/convmem/agent_runs.jsonl` with a sibling lock and private permissions |
| **First capture client** | Kiro `SessionStart` + `Stop` hooks; the schema and API remain client-neutral |

## Product goal

ConvMem should be able to answer **which agent and native session produced or
observed a piece of work** using durable, inspectable evidence. The answer must
remain honest when a client did not expose an identifier, when a hook failed, or
when several concurrent runs could match the same repository. Existing
`session_id`, ledger provenance, Chroma authority, and `author`/`signer`
controls must continue to mean what they mean today.

The Agent Run Ledger supplies a missing correlation layer:

```text
client lifecycle          existing ingest              durable work evidence
SessionStart/Stop  --->   session_id + optional   ---> commits, files,
Codex/Cursor/etc.         agent_run_id metadata       ledger record ids
        |                         |                         |
        +-------------------------+-------------------------+
                                  v
                     agent_runs.jsonl event log
                                  |
                         deterministic reducer
                                  |
                  run query / provenance explanation
```

The ledger is a **correlation record**, not a replacement for the ConvMem
decision/observation ledger and not a new authority for Chroma. It records
what was directly observed or explicitly linked. It does not claim causation
from temporal coincidence.

## Current baseline

ConvMem already has useful, non-unified identity facts:

- `adapters/detect.py` maps supported formats to client names through
  `TOOL_BY_FORMAT` (`kiro`, `codex`, `cursor`, `crush`, `copilot`, and other
  recognized clients).
- `ingest._chunk_session_meta()` carries the first available `session_id` and
  `workspace_directory` into the unit metadata path. Existing indexed units
  therefore retain native session evidence, but not a ConvMem-owned run ID.
- `adapters/kiro_session_jsonl.py` reads the Kiro `session.json` `id` and
  workspace path, falling back to the `sess_*` directory name only when the
  sidecar ID is absent. This is an existing deterministic parser, not an
  inference model.
- `pending_decisions.jsonl`, `pending_decision_events.jsonl`,
  `inventory.jsonl`, and the Shadow Ledger establish local JSONL sidecar
  patterns. `shadow_sink.py` demonstrates lock, sequence, `fsync`, tail
  validation, idempotency, and visible degradation patterns that the new
  writer should reuse rather than copy casually.
- `propose_decision.py` keeps proposal authoring separate from approval
  signing. `chroma_write_store.WriterAttestation` records process, executable,
  entrypoint, and code revision evidence. Neither surface is a run ledger.
- No `agent_runs.jsonl`, run reducer, `agent_run_id` metadata field, or
  `.kiro/hooks/` capture implementation exists in the repository today.

## Scope

### In scope for the first implementation slice

1. A versioned append-only event envelope and deterministic reducer.
2. A private local JSONL writer safe for concurrent client processes.
3. ConvMem-owned `run_id` generation and exact native-session correlation.
4. Kiro `SessionStart` and `Stop` capture, subject to a hook-contract fixture
   and Ryan's external installation grant.
5. A read/query path that distinguishes known, missing, ambiguous, conflicting,
   observed, and explicitly linked facts.
6. Progressive enrichment for repository, branch, commit, file, and ConvMem
   ledger-record evidence.
7. An additive, unambiguous `agent_run_id` association for newly ingested
   units, while retaining the existing `session_id` unchanged.
8. Tests for replay, duplicate delivery, concurrent appends, missing data,
   conflict handling, hook behavior, and ingest compatibility.

### Out of scope

- Replacing `session_id`, `author_model`, `--author`, `--signer`, or any
  existing provenance field.
- Making the Agent Run Ledger authoritative for observations, decisions,
  verification records, or Chroma.
- Rewriting or backfilling all historical Chroma units.
- Inferring client/session identity from prompt text, model names, branch names,
  timestamps, or “most recent” filesystem activity.
- Claiming that every commit or changed file in a time range was authored by a
  run. Temporal observation and explicit linkage are separate relations.
- Calling an LLM from hooks, the event writer, the reducer, or ingest identity
  resolution.
- Automatic semantic reconciliation of ambiguous runs. That is a later,
  evidence-constrained proposal surface, not deterministic capture.
- Cross-machine synchronization, cloud storage, or public identity telemetry.
- Production Chroma mutation, bulk indexing, database mutation, or changes to
  existing backup/restore authority.

## Definitions and evidence policy

| Term | Meaning |
|---|---|
| **run** | One ConvMem-correlated lifecycle observed from a client. A run may be incomplete if the process crashes or a stop hook is not delivered. |
| **run_id** | An opaque ID generated by ConvMem at capture time. It identifies the ledger record, not the client session and not a person. |
| **native_session_id** | An opaque identifier supplied by a client or its durable session metadata. It is never synthesized from a timestamp, path, or model. |
| **client** | A bounded label such as `kiro`, `codex`, `cursor`, `crush`, or `copilot`; the capture source supplies it. Unknown is allowed. |
| **observed** | A fact directly returned by a deterministic source during or around the run, such as a Git SHA or repository path. It is not a causal claim. |
| **explicit** | A fact deliberately linked by a caller that already knows the run, such as a ledger ID returned by `convmem record` and passed to enrichment. |
| **missing** | The source did not provide a fact. The reducer preserves null/missing rather than inventing a value. |
| **ambiguous** | More than one run satisfies an exact lookup. The resolver returns no run ID and exposes the candidates. |

The evidence ladder is deliberately narrow:

1. The hook or client adapter supplies `client` and, when available,
   `native_session_id`.
2. Git supplies repository root, branch, and exact revisions from the hook's
   working directory. Detached HEAD is represented as detached/unknown branch,
   not relabeled.
3. The capture API generates only `run_id` and `event_id`; those are ConvMem
   identifiers, not claims about external identity.
4. Enrichment accepts exact commit SHAs, repository-relative file paths, and
   validated ConvMem ledger IDs. It labels each relation as `observed` or
   `explicit`.
5. Any missing or conflicting value stays missing/conflicting in the query
   result. No LLM is allowed to fill the gap during capture.

## Chosen storage and event model

The authoritative run state is reconstructed from an append-only JSONL event
log. The log is the source of truth for run lifecycle and evidence; a reducer
may materialize a read-only view in memory or a disposable report, but no
mutable summary file is required for correctness.

### Event envelope

Every lifecycle or enrichment event has this shape. `facts` is event-specific,
but its keys and value types are validated by the writer.

```json
{
  "schema_version": 1,
  "event_id": "arevt_01J...",
  "sequence": 42,
  "event_type": "run_enriched",
  "run_id": "run_01J...",
  "event_time": "2026-08-20T20:15:11Z",
  "recorded_at": "2026-08-20T20:15:11.231Z",
  "client": "kiro",
  "native_session_id": "sess_opaque-client-id",
  "repository": "/home/lauer/Projects/convmem",
  "branch": "plan/2026-08-20-agent-run-ledger",
  "status": "active",
  "source": {
    "kind": "kiro_hook",
    "ref": "SessionStart"
  },
  "facts": {
    "head_revision": "0123456789abcdef0123456789abcdef01234567",
    "commits": [],
    "files": [],
    "ledger_records": []
  }
}
```

Field rules:

| Field | Rule |
|---|---|
| `schema_version` | Integer; readers reject unsupported major versions. |
| `event_id` | ConvMem-generated or deterministically supplied by a hook delivery; retrying the same delivery must reuse it. Same ID with different bytes is corruption. |
| `sequence` | Assigned while holding the append lock; strictly increasing in one log. Event-time clocks do not determine replay order. |
| `event_type` | `run_started`, `run_enriched`, `run_stopped`, or `capture_diagnostic`. |
| `run_id` | Required for lifecycle/enrichment events; null only for an unmatched `capture_diagnostic`. |
| `event_time` | Time observed by the source; nullable only for a diagnostic that lacks it. |
| `recorded_at` | UTC time ConvMem appended the event. |
| `client` | Source label; never inferred from `author_model` or executable text. |
| `native_session_id` | Opaque string or null. Preserve exact source bytes after bounded validation. |
| `repository` | Canonical Git top-level path or null. Never use the current checkout path when Git did not confirm it. |
| `branch` | Git symbolic branch name or null/`detached`; never convert a SHA into a branch name. |
| `status` | `active`, `completed`, `aborted`, or `unknown` for lifecycle events; `active` for enrichment; `diagnostic` for unmatched capture. |
| `source` | Machine-readable capture source and stable reference, with no prompt/content payload. |
| `facts` | Additive, validated evidence. It must not contain chat text, secrets, tokens, or arbitrary shell output. |

`facts` uses these bounded shapes:

```json
{
  "head_revision": "<40-hex SHA or null>",
  "commits": [
    {"sha": "<40-hex SHA>", "relation": "observed|explicit", "source": "git|caller"}
  ],
  "files": [
    {"path": "repo/relative/path.py", "relation": "observed|explicit", "source": "git|caller", "change": "added|modified|deleted|unknown"}
  ],
  "ledger_records": [
    {"ledger_id": "obs_...|dec_...|ver_...", "relation": "explicit", "source": "record|caller"}
  ]
}
```

The reducer unions duplicate evidence by canonical key while preserving all
source references. It never turns an `observed` fact into `explicit` without a
new explicit event.

### Lifecycle and replay

| Event | Required state before append | Resulting state |
|---|---|---|
| `run_started` | No active run for the exact idempotency key, or an exact retry | `active` |
| `run_enriched` | Existing run; terminal runs may receive later evidence but status does not reopen | unchanged |
| `run_stopped` | Existing active run; exact duplicate is idempotent | supplied terminal status |
| `capture_diagnostic` | No run lookup required | no run state change; diagnostic is queryable |

The reducer replays append order, skips an exact duplicate `event_id`, and
reports (rather than repairs) these conditions:

- an event has invalid schema or unsupported version;
- an event ID is reused with different content;
- a lifecycle transition is impossible;
- two immutable identity observations conflict;
- the file has malformed interior JSON or a truncated final line; or
- a stop request has zero or multiple exact candidates.

A run with no stop event remains `active`/`incomplete`. The query surface must
say “no terminal evidence recorded”; it must not infer `aborted` from age.

### Append durability and concurrency

The writer follows the existing Shadow Ledger durability direction:

1. Resolve the default path under `~/.local/share/convmem` and reject unsafe
   symlink/path conditions.
2. Create the parent directory privately on first use and the log with mode
   `0600`; fsync the directory after first publication.
3. Open the log in append mode and acquire a bounded `flock` on a sibling lock
   file.
4. Validate the current tail and compute the next sequence while holding the
   lock.
5. Write exactly one JSON line, flush, `fsync` the file, release the lock, and
   return the event ID.
6. Refuse to append to a corrupt log. A separate, explicitly authorized repair
   procedure may be designed later; the capture path never truncates or
   rewrites evidence.

Hook failure must be fail-open for the client lifecycle: a missing run event
   is preferable to blocking or altering an agent session. The failure is
   visible on stderr/diagnostics, and the query/doctor integration reports that
   capture was unavailable. “Fail-open” must not mean reporting a successful
   capture when no durable event was written.

## Correlation with existing ConvMem surfaces

### Ingest and Chroma metadata

Keep `session_id` exactly as it is. During a later ingest call, a resolver may
look up the message's native session ID and add `agent_run_id` only when one
and only one run is an exact match for the client/session and relevant
repository context. If zero or multiple runs match, ingest preserves the
existing metadata and omits `agent_run_id`; it does not guess.

This association is additive and forward-only in the first slice:

- no historical reindex or bulk mutation;
- no removal or rewriting of `session_id`;
- no Chroma read-path dependency on the Agent Run Ledger for existing units;
- no change to ledger IDs, `author_model`, `--author`, or `--signer`;
- tests prove that an unavailable run log leaves current ingest behavior
  unchanged.

The run query can still join historical units by their existing `session_id`
when the native session ID is exact, even when those units predate
`agent_run_id`.

### Ledger records and signatures

`convmem record` remains the authority for decision/observation/verification
records and `--signer` remains approval evidence. The first run implementation
does not add a required run argument to that command. Instead, a caller can
append an explicit `ledger_records` enrichment event after receiving the
ledger ID. A later architecture may add an optional run context to record
creation, but it must preserve author/signature semantics and cannot be
inferred from the current model name.

### Client neutrality

The storage/reducer API accepts a client label and opaque native ID; it does
not import Kiro-specific types. Kiro hooks are one adapter at the edge. Codex,
Cursor, Crush, and Copilot can later call the same `start`, `enrich`, and
`stop` operations with their own deterministic native-session source. The
existing `TOOL_BY_FORMAT` mapping remains the vocabulary bridge for ingest,
not the run ledger's source of truth.

## Kiro capture boundary

The first deterministic mechanism is a pair of repository-deployed Kiro hook
entries under `.kiro/hooks/`, using the client's `SessionStart` and `Stop`
lifecycle contracts. Exact filenames, stdin shape, environment variables, and
exit behavior are an execution-phase contract test, not an architectural
assumption.

The Kiro adapter must:

- use the hook-provided native session ID when present;
- otherwise read an explicitly supplied `session.json` path and apply the
  existing `kiro_session_jsonl.read_session_meta()` rules;
- capture Git facts only from the hook working directory and confirmed Git
  commands;
- call the shared writer with `client="kiro"`;
- never include conversation contents or model output; and
- return success to Kiro after a capture error, while emitting a diagnostic.

If Kiro supplies no stable native ID in either lifecycle hook, the start event
may still record a ConvMem `run_id` with `native_session_id: null`, but Stop
must produce an unmatched diagnostic rather than close an arbitrary active
run. The execution plan must test this degraded path before installation.

## Semantic interpretation boundary

Deterministic capture owns identity, timestamps, Git facts, exact IDs, event
validation, and lifecycle reduction. An LLM may be introduced only in a later
reconciliation stage that proposes a relationship among already captured
evidence, for example deciding whether two explicitly named work items refer
to the same user goal. Such a proposal must cite event IDs and remain separate
from the raw event log and existing ledger approval. The MVP has no LLM
dependency and no semantic auto-linking.

## Options considered

| Option | Decision | Reason |
|---|---|---|
| Mutable `agent_runs.json` summary | Rejected | Crash windows and concurrent writers can lose or overwrite lifecycle evidence. |
| Chroma-only run metadata | Rejected | It cannot capture a run before ingest, would couple identity to a projection, and would invite a backfill/authority change. |
| New fields only on existing ledger records | Rejected | It misses sessions with no record and changes a governed provenance surface before identity capture is stable. |
| LLM post-processing of transcripts | Rejected for capture | It fabricates or hides missing identity and is not deterministic enough for lifecycle evidence. |
| **Append-only event log + reducer** | **Chosen** | One narrow local source supports crash recovery, concurrent append, replay, client-neutral adapters, and explicit degraded states. |

## Locked invariants

1. Every run lifecycle event has a ConvMem-owned `run_id`; only diagnostics may
   omit it.
2. A native session ID is copied only from a deterministic client source.
3. Missing identity stays missing; ambiguous identity never resolves by
   recency, branch, timestamp, model, or prompt similarity.
4. `session_id`, Chroma authority, ledger authority, author, and signer keep
   their existing meanings.
5. The event log is append-only; no capture path rewrites, compacts, truncates,
   or silently skips corruption.
6. Sequence assignment and one-line append occur under a lock with durable
   `fsync`.
7. Reducer replay is deterministic and idempotent for exact duplicate events.
8. Observed Git facts are not causal authorship claims; explicit linkage is
   separately labeled.
9. Hooks and capture failure cannot block or mutate the client workflow.
10. No LLM runs in hooks, writing, reduction, or identity association.
11. New clients implement an edge adapter against the same envelope and do not
   create client-specific storage schemas.
12. No production hook installation, bulk ingest, Chroma mutation, or ledger
   write is authorized by this architecture document.

## Architecture acceptance

Kiro/Ryan architecture review should be able to answer “yes” to all of these
before Execution is treated as locked:

- Can a reviewer reconstruct a run from only `agent_runs.jsonl` and identify
  the source of each fact?
- Does every missing/ambiguous case remain visibly unresolved?
- Can two concurrent hooks append without interleaving or sequence collision?
- Does a crash or malformed tail fail closed without destroying prior events?
- Can the ingest path retain `session_id` and continue when the run log is
  absent or ambiguous?
- Can a future client use the same API without importing Kiro code?
- Is there a clear line between observed work and explicitly linked work?
- Is the implementation free of LLM and existing provenance/authority changes?

**Next artifact:** [`EXECUTION-agent-run-ledger.md`](EXECUTION-agent-run-ledger.md).
