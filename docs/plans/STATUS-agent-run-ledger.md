# Arc Brief — Runway Ledger

> Every model working on this arc must read this file before acting.
>
> **Subject:** ConvMem Agent Run identity tracking.

## 1. What This Is For (product goal)

ConvMem currently preserves native `session_id` values inside indexed units,
but it cannot consistently answer which client/session lifecycle produced or
observed a unit of work. Runway Ledger adds a client-neutral, ConvMem-owned run
identity and durable event evidence without changing existing provenance or
storage authority.

**Done means:** a reviewer can reconstruct a run from the private append-only
event log, see the exact client/native session evidence and lifecycle status,
distinguish observed work from explicitly linked work, and receive an honest
unknown/ambiguous result when identity is missing. Kiro is the first capture
client; the same envelope supports Codex, Cursor, Crush, and Copilot later.

## 2. System Design (how the pieces connect)

```text
Kiro SessionStart/Stop             existing adapters/ingest
          |                                  |
          v                                  v
  shared capture API  ---- exact session lookup ----> optional agent_run_id
          |                                  |          (future units only)
          v                                  v
 ~/.local/share/convmem/agent_runs.jsonl  Chroma metadata keeps session_id
          |
          v
  deterministic reducer/query
          |
  lifecycle + identity + observed/explicit evidence
```

The log is append-only and event-sourced. A sibling lock serializes sequence
assignment and durable line appends. Reducer replay uses append sequence, not
wall-clock order. Capture does not call an LLM, mutate Chroma, or alter the
decision/observation ledger. Semantic reconciliation, if ever authorized, is a
separate evidence-citing proposal stage.

## 3. What Exists Right Now

| Surface | State |
|---|---|
| `main` | Core Runway Ledger implementation is merged via [PR #215](https://github.com/alanmz-crypto/convmem/pull/215) |
| `adapters/detect.py` | Existing client vocabulary in `TOOL_BY_FORMAT`; run association is additive and unique-match-only |
| `ingest.py` | `_chunk_session_meta()` carries existing `session_id`, workspace, and forward-only `agent_run_id` when uniquely resolved |
| `adapters/kiro_session_jsonl.py` | Deterministic Kiro session ID/workspace parser exists |
| `propose_decision.py` / `conflict_events.py` | Existing JSONL proposal/event patterns; not run identity authority |
| `shadow_sink.py` | Existing lock/sequence/fsync/tail-validation pattern to reuse conceptually |
| `chroma_write_store.py` | Existing `WriterAttestation`; run linkage remains outside Chroma mutation authority |
| `~/.local/share/convmem/agent_runs.jsonl` | Private runtime event log; its presence and contents depend on host hook/CLI use and are not repository state |
| `.kiro/hooks/` | Kiro start/stop hook definitions are present on `main`; enablement landed via [PR #216](https://github.com/alanmz-crypto/convmem/pull/216) |
| Architecture plan | [`ARCHITECTURE-agent-run-ledger.md`](ARCHITECTURE-agent-run-ledger.md) — locked design for the merged implementation |
| Execution plan | [`EXECUTION-agent-run-ledger.md`](EXECUTION-agent-run-ledger.md) — completed execution contract |
| Implementation/tests | **Merged** via [PR #215](https://github.com/alanmz-crypto/convmem/pull/215); V0–V13 PASS |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Arc codename and scope | Complete — **Runway Ledger** | — |
| Kiro architecture investigation | Complete; findings incorporated from the user-provided Kiro handoff | Kiro review of this package may add conditions |
| Architecture plan | **DONE / LOCKED** | Reviewed and carried by the merged implementation |
| Execution plan | **DONE / ACCEPTED** | T0–T8 execution and focused evidence complete |
| STATUS brief and registrations | **ON `main`** | This brief is the current-state pointer; generated surfaces follow the protocol source |
| Core implementation | **DONE / MERGED** via PR #215 | V0–V13 focused evidence PASS |
| Kiro hook enablement/live capture | **DONE for the shipped Kiro slice** via PR #216 | Host-specific runtime state should be checked with `doctor`/`brief`; other clients are future slices |

## 5. Your Role

This arc is closed for the shipped implementation. If you are checking the
personal deployment, use `convmem doctor` and `convmem brief --stdout-only` to
confirm host-specific hook and run-log state. If you are adding another client
or changing run association, treat that as a new bounded slice with its own
review and authorization; do not infer authorization from PR #215 or PR #216.

## 6. What Remains Before “Live”

No uncompleted repository milestone remains for the Kiro-first slice:

1. Architecture and Execution were reviewed and locked.
2. T0–T8 implementation, V0–V13 focused tests, and independent review passed.
3. The implementation merged via PR #215; Kiro hook enablement and soak merged via PR #216.
4. Forward-only `agent_run_id` association is active for unique matches.

Host deployment state is operational context, not a claim that every machine
has hooks installed. Codex, Cursor, Crush, and Copilot integrations remain
future slices and are not required to reopen or extend this arc.

## 7. Hard Stops

| Stop | Owner | Effect |
|---|---|---|
| Architecture or Execution review not PASS | Kiro/Ryan | No implementation or hook deployment |
| Kiro hook contract lacks stable native ID | Cursor/Kiro | Capture start-only evidence; unmatched Stop stays diagnostic; no fabricated identity |
| Multiple exact active run candidates | Reducer | Return ambiguity; never close by recency |
| Corrupt/truncated event log | Writer/validator | Refuse append and surface corruption; no automatic truncation |
| Missing repository/branch/Git facts | Capture | Preserve null/detached/unknown; no inference |
| Capture writer failure | Hook | Fail open for the client, but do not report durable capture success |
| Chroma/ledger mutation request | All lanes | Out of scope; separate arc and authorization required |
| Semantic or LLM reconciliation | All lanes | Later proposal-only design; absent from MVP |
| External hook installation | Ryan | Requires exact resource, operation, and reviewed bytes |

## 8. Relationship to ConvMem

Runway Ledger is an additive correlation layer. Existing indexed units retain
their `session_id`; existing ledger records retain their IDs, authors,
signers, and authority; Chroma remains a rebuildable search projection as
defined by current arcs. New units may receive `agent_run_id` only after an
exact unique native-session match. Existing units are not reindexed or
rewritten. Run evidence can point at a ledger ID, but it cannot approve,
supersede, or replace that ledger record.

## 9. Key Design Files

| Purpose | Path |
|---|---|
| Architecture authority | [`docs/plans/ARCHITECTURE-agent-run-ledger.md`](ARCHITECTURE-agent-run-ledger.md) |
| Execution order and tests | [`docs/plans/EXECUTION-agent-run-ledger.md`](EXECUTION-agent-run-ledger.md) |
| This current-state brief | [`docs/plans/STATUS-agent-run-ledger.md`](STATUS-agent-run-ledger.md) |
| Client vocabulary | [`adapters/detect.py`](../../adapters/detect.py) |
| Existing session metadata path | [`ingest.py`](../../ingest.py) |
| Kiro session parser | [`adapters/kiro_session_jsonl.py`](../../adapters/kiro_session_jsonl.py) |
| JSONL proposal/event patterns | [`propose_decision.py`](../../propose_decision.py), [`conflict_events.py`](../../conflict_events.py) |
| Durable mutation-event pattern | [`shadow_sink.py`](../../shadow_sink.py) |
| Existing writer evidence | [`chroma_write_store.py`](../../chroma_write_store.py) |
| Cross-arc rollup | [`docs/inter-model/STATUS.md`](../inter-model/STATUS.md) |

## 10. How to Update This Brief

Keep this file a current-state snapshot. When a milestone changes state,
rewrite sections 3–6, move branch work to `main` only after merge, remove
completed checklist items, and add one milestone-level line below. Do not add
session narrative here; session details belong in Track A ingest.

## Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-20 | Cursor | Execute started on feat branch; T0 Kiro hook contract fixtures landed |
| 2026-08-20 | Cursor | T1/T2 schema, reducer, and durable writer landed with focused tests |
| 2026-08-20 | Cursor | T3–T7 CLI, Kiro edge (disabled hooks), git facts, ingest resolver |
| 2026-08-20 | Cursor | V13 green; opened PR #215 at tip `a2a2865` |
| 2026-08-20 | Cursor | Claude Q4/Q7 pre-soak fixes on PR #215 (no-ID collision + stderr) |
| 2026-08-20 | Kiro | Soak passed; hooks enabled; PR #216 opened; arc closing |
| 2026-09-01 | Codex | Reconciled this brief with merged PRs #215/#216; Kiro-first implementation is closed and other clients remain future slices |
