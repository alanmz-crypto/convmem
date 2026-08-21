# Execution Plan — Agent Run Ledger

> **Arc: Runway Ledger** — ConvMem Agent Run identity tracking.

| Field | Value |
|---|---|
| **Architecture authority** | [`ARCHITECTURE-agent-run-ledger.md`](ARCHITECTURE-agent-run-ledger.md); implementation must satisfy its locked invariants |
| **Status** | Execution planning; no implementation or live hook installation is authorized by this document alone |
| **Planning lane** | Codex authors; Kiro reviews; Ryan gates; Cursor implements after Execute authorization |
| **Base** | `origin/main` at `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481` |
| **Primary artifact** | `~/.local/share/convmem/agent_runs.jsonl` |
| **First client** | Kiro `SessionStart` + `Stop`; Codex/Cursor/Crush/Copilot adapters are follow-on slices |

## Consequence for the next human

After this plan is approved and executed, ConvMem will have a private,
replayable run record that can answer which client/native session was associated
with captured work, while honestly returning unknown or ambiguous when the
client did not provide enough evidence. The implementation adds a new
correlation surface; it does not reclassify existing Chroma, ingest, ledger,
author, or signer provenance.

## Scope lock

### Execute only these outcomes

- A shared event envelope and reducer for `run_started`, `run_enriched`,
  `run_stopped`, and unmatched-capture diagnostics.
- Durable append with private permissions, lock/sequence discipline, tail
  validation, and exact duplicate idempotency.
- Kiro hook capture after the hook contract is proven by a fixture.
- Read/query/validate surfaces sufficient to inspect a run and its evidence.
- Optional forward-only `agent_run_id` attachment to newly ingested units when
  the native-session lookup is unique.
- Explicit enrichment for Git commits, repository-relative files, and ConvMem
  ledger IDs, with `observed` versus `explicit` relation labels.
- Tests and a verification package covering all locked invariants.

### Do not execute

- No prompt/content/model capture, LLM reconciliation, or semantic grouping.
- No historical reindex, Chroma migration, direct database mutation, or
  changes to existing ledger authority.
- No required `--run-id` change to `convmem record`; no automatic author/signer
  association.
- No non-Kiro hook deployment or external client configuration.
- No production hook installation or enabling of capture without Ryan's exact
  external-change grant.
- No repair/truncation/compaction of an event log from the normal capture path.

## Work order

The slices are intentionally ordered so the deterministic core is testable
before any client hook can write live data.

| Slice | Owner/lane | Deliverable | Depends on | Gate |
|---|---|---|---|---|
| T0 — contract reconnaissance | Cursor implementation lane, Kiro review | Kiro hook fixture documenting stdin, env, native ID, cwd, retry, and exit semantics; Git command fixture; explicit stop/fallback behavior | Architecture PASS | No hook file is installed until the fixture is reproducible |
| T1 — schema and reducer | Cursor | `agent_run_ledger` deep module, envelope validation, lifecycle reducer, evidence union/conflict report, typed query view | T0 schema inputs | Unit tests pass without filesystem or client tools |
| T2 — durable writer | Cursor | Private path resolution, sibling lock, sequence assignment, append/fsync, corruption refusal, exact event-id idempotency | T1 | Concurrent and fault-injection tests pass |
| T3 — read/CLI surface | Cursor | Narrow `agent-run` commands: start, stop, enrich, show/list, validate; machine-readable output for hooks and diagnostics | T1–T2 | Commands never expose raw prompt content or silently resolve ambiguity |
| T4 — Kiro edge adapter | Cursor | Repository `.kiro/hooks/` entries plus adapter wrapper using T3; fail-open client behavior; no LLM | T0, T3 | Hook fixture and missing-ID tests pass; Ryan external install still pending |
| T5 — deterministic Git enrichment | Cursor | Start/stop head facts and explicit/observed commit/file enrichment from confirmed Git output | T3, T4 | Detached HEAD, dirty tree, non-Git cwd, and concurrent-commit cases are truthful |
| T6 — ingest association | Cursor | Optional resolver in the existing session metadata path; additive `agent_run_id` only for a unique exact match | T1, T3 | Existing ingest/session tests pass unchanged; no backfill |
| T7 — explicit ledger links | Cursor | Enrichment path accepting validated `obs_`, `dec_`, and `ver_` IDs; no modification to record or signer semantics | T3 | Explicit link round-trip test passes |
| T8 — verification and handoff | Codex/Copilot audit lane as assigned; Kiro review; Ryan | VERIFY-style table, focused/full tests, docs/STATUS reconciliation, pushed branch | T1–T7 | Kiro PASS and Ryan Execute/installation decision |

T0 is a hard prerequisite. If the Kiro contract cannot provide a stable native
session ID, T4 must retain start-only evidence and unmatched-stop diagnostics;
it may not invent a replacement identity from path or time.

## Proposed implementation boundaries

The implementation should keep the event ledger deep and its callers thin:

| Module/surface | Responsibility | Must not own |
|---|---|---|
| `agent_run_ledger.py` (name may be refined by Cursor) | Envelope validation, path/lock, append, replay, resolution, evidence merge, query view | Chroma, embeddings, prompt parsing, LLM calls |
| `convmem.py` `agent-run` command group | Parse CLI options and delegate to the deep module | Reducer policy or JSONL formatting duplicated in handlers |
| Kiro hook wrapper | Extract hook facts, call shared API, fail-open on capture failure | Client-specific schema or semantic inference |
| `ingest.py` / resolver | Preserve existing session metadata and add a unique optional run ID | Guessing a run or requiring the run log |
| Git fact collector | Run bounded `git` commands and label outputs | Claiming causation or parsing arbitrary shell output |
| Existing `ledger.py` / `propose_decision.py` | Remain authoritative for their current records/signatures | Owning run lifecycle |
| Existing Chroma writer | Remain authoritative for Chroma | Importing run capture into mutation authority |

The exact module name can change only if the same boundary and public contract
remain intact. Do not create per-client copies of the reducer.

## Event and CLI contracts to implement

### Start

`agent-run start` accepts a client, optional native session ID, optional
repository/cwd, and a source reference. It obtains confirmed Git facts when
available, generates one opaque `run_id`, and appends `run_started`. It returns
the run ID and event ID only after durable append. A retry with the same
delivery idempotency key returns the existing run rather than starting a
second run.

If native identity is absent, the result explicitly reports
`native_session_id: null` and `identity_completeness: partial`.

### Stop

`agent-run stop` accepts an explicit run ID when a caller has one; otherwise it
requires an exact client/native-session/repository lookup. Zero candidates
produce a diagnostic; multiple candidates produce an ambiguity result. The
command never closes “the newest” run. Stop status is one of `completed`,
`aborted`, or `unknown`, supplied by the client/adapter rather than inferred
from elapsed time.

### Enrich

`agent-run enrich` accepts an explicit run ID and bounded fact lists. Git
collection may add observed facts from a confirmed repository; a caller may
add explicit facts. Duplicate facts are idempotent. A fact conflict is
preserved and reported; it does not overwrite the original source.

### Query and validation

`agent-run show/list` returns the reduced run state plus event IDs/source refs,
identity completeness, terminal evidence, conflicts, and observed/explicit
evidence. `agent-run validate` reports malformed events, sequence problems,
duplicate-ID byte mismatches, illegal transitions, and truncated tails without
repairing the file.

CLI output for hooks must have a stable compact machine-readable mode. Human
output may summarize it, but it must not be the only parseable contract.

## Test and verification matrix

| ID | Proof | Expected result |
|---|---|---|
| V0 | Envelope fixtures for each client and all nullable identity fields | Valid records round-trip; unknown client and missing native ID are accepted explicitly |
| V1 | Reducer replay in shuffled event-time order | Append sequence, not wall-clock text, determines state; duplicate exact event IDs are idempotent |
| V2 | Invalid schema, unsupported version, illegal transition, interior JSON corruption, truncated tail | Validation fails closed and never rewrites evidence |
| V3 | Two or more concurrent writers with barriers | Lines do not interleave; sequences are unique and increasing; every successful return has durable bytes |
| V4 | Same hook delivery retried; same event ID with changed payload | Exact retry is idempotent; changed bytes are a corruption/error |
| V5 | Start with no native ID; stop with no/ambiguous ID | Run remains incomplete and a diagnostic is exposed; no arbitrary close occurs |
| V6 | Repository, branch, detached HEAD, dirty tree, non-Git cwd | Only confirmed facts are recorded; missing facts stay null/detached/unknown |
| V7 | Commits/files observed versus explicitly linked | Relations remain distinct; temporal presence is not called authored work |
| V8 | Kiro hook fixture with successful, missing-ID, duplicate, and writer-failure cases | Hook is deterministic and fail-open; it never sends prompts or blocks the client |
| V9 | Existing ingest fixture with no run log, unique match, and ambiguous match | `session_id` and current metadata remain; optional `agent_run_id` appears only for a unique match |
| V10 | Explicit `obs_`, `dec_`, and `ver_` enrichment | IDs round-trip without changing ledger content, author, or signer behavior |
| V11 | Permission and path safety | Parent/file permissions are private; symlink/path refusal is visible |
| V12 | Cross-client envelope fixtures for Kiro/Codex/Cursor/Crush/Copilot | Same reducer and schema; only edge source extraction varies |
| V13 | Focused + full project suite | No regressions in ingest, ledger, Chroma, protocol, or existing JSONL writers |

## Rollout and rollback

1. Merge the core/reducer and tests only after Architecture and Execution HITL.
2. Land Kiro hook files behind the repository/client deployment boundary, but
   keep live installation disabled until T0/T4 evidence and Ryan's exact
   external grant exist.
3. Enable capture for a disposable/local Kiro session first. Verify the event
   file, permissions, reducer output, and fail-open behavior.
4. Enable the optional ingest association for forward-only units after V9;
   do not backfill or reindex existing data.
5. Add other clients only as separate edge slices using V12.

Rollback is additive: disable/remove the client hook, leave the append-only
event file for inspection, and the existing ingest path continues without
`agent_run_id` when capture is unavailable. No rollback may delete run events,
rewrite Chroma metadata, or alter existing ledger records.

## External changes and stop points

No external change is authorized by this plan. A later grant must name the
exact resource and operation, for example:

| Resource | Operation | Required owner |
|---|---|---|
| Repository `.kiro/hooks/SessionStart` and `.kiro/hooks/Stop` deployment | Install/enable the reviewed hook bytes for Kiro capture | Ryan |
| `~/.local/share/convmem/agent_runs.jsonl` | Create/write the local run ledger during a disposable soak | Ryan or explicitly delegated operator |
| Forward-only ingest association | Enable optional `agent_run_id` metadata after V9 | Ryan execution gate |

The path and final bytes must be reviewed at the grant. No hook may change
existing Kiro session storage, Chroma, or ConvMem ledger authority.

## Handoff and exit criteria

Execution is ready for Kiro review when:

- T0 defines the Kiro contract with a reproducible fixture;
- the architecture invariants are mapped to tests V0–V13;
- exact missing/ambiguous behavior is written into the CLI contract;
- the ingest association is explicitly additive and forward-only;
- external installation and live soak are separate Ryan gates; and
- the plan names no semantic or LLM dependency in the capture path.

The implementation phase is complete only when T1–T8 are committed, focused
and full tests pass, the verification table is filled with evidence, the
STATUS brief reflects the actual branch/main state, and the branch is pushed.
This plan assumes Ryan's default squash-merge policy; no `Do not squash` line
is required.

**Merge reading:** [`ARCHITECTURE-agent-run-ledger.md`](ARCHITECTURE-agent-run-ledger.md) · [`STATUS-agent-run-ledger.md`](STATUS-agent-run-ledger.md)
