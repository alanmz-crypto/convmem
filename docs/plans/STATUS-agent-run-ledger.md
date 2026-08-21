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
| `origin/main` | `d10e1d5` — current planning base when this brief was authored |
| `adapters/detect.py` | Existing client vocabulary in `TOOL_BY_FORMAT`; no run abstraction |
| `ingest.py` | `_chunk_session_meta()` carries existing `session_id` and workspace; no `agent_run_id` |
| `adapters/kiro_session_jsonl.py` | Deterministic Kiro session ID/workspace parser exists |
| `propose_decision.py` / `conflict_events.py` | Existing JSONL proposal/event patterns; not run identity authority |
| `shadow_sink.py` | Existing lock/sequence/fsync/tail-validation pattern to reuse conceptually |
| `chroma_write_store.py` | Existing `WriterAttestation`; no run linkage |
| `~/.local/share/convmem/agent_runs.jsonl` | **Missing**; no production run log has been created by this plan |
| `.kiro/hooks/` | **Missing** in the repository; Kiro capture is planned, not installed |
| Architecture plan | [`ARCHITECTURE-agent-run-ledger.md`](ARCHITECTURE-agent-run-ledger.md) — authored on this planning branch |
| Execution plan | [`EXECUTION-agent-run-ledger.md`](EXECUTION-agent-run-ledger.md) — authored on this planning branch |
| Implementation/tests | **In progress** — T0–T7 on feat branch; V0–V12 focused PASS; V13 full suite pending |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Arc codename and scope | Complete — **Runway Ledger** | — |
| Kiro architecture investigation | Complete; findings incorporated from the user-provided Kiro handoff | Kiro review of this package may add conditions |
| Architecture plan | Drafted on `plan/2026-08-20-agent-run-ledger` | Kiro review, then Ryan Architecture HITL |
| Execution plan | Drafted on `plan/2026-08-20-agent-run-ledger` | Kiro review, then Ryan Execution HITL |
| STATUS brief and registrations | Included in this planning package | Ryan merge; generated surfaces may need propagation |
| Core implementation | In progress — Cursor Execute authorized 2026-08-20 | T0 done → T1–T8 |
| Kiro hook installation/live capture | Not started and not authorized | T0/T4 fixture evidence plus exact Ryan external grant |

## 5. Your Role

The current lane is **Cursor Execute** on `feat/2026-08-20-agent-run-ledger`
(worktree under `~/.local/share/convmem/worktrees/feat-2026-08-20-agent-run-ledger`).
Architecture and Execution are Ryan-locked after Kiro PASS. Implement T0–T8 per
`EXECUTION-agent-run-ledger.md`. Do not install live hooks or enable forward
ingest association without Ryan's exact grants. Kiro reviews the exact
revision after implementation; Ryan owns merges.

## 6. What Remains Before “Live”

1. ~~Kiro reviews the architecture and execution package~~ — PASS.
2. ~~Ryan locks Architecture and Execution~~ — granted 2026-08-20.
3. ~~Cursor proves the Kiro hook contract (T0)~~ — fixtures + contract tests.
4. ~~Cursor implements T1–T7~~ — on feat branch; hooks disabled pending Ryan grant.
5. Run V13 full suite; open PR; Kiro reviews exact tip.
6. Ryan grants the exact local hook installation/disposable soak if the gate is
   green. Verify private file permissions and fail-open behavior.
7. Ryan separately decides whether to enable forward-only `agent_run_id`
   association. No historical backfill is implied.
8. Add other clients only as separately reviewed edge adapters.

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
signers, and authority; Chroma remains a projection/authority surface exactly
as defined by current arcs. New units may receive `agent_run_id` only after an
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
| 2026-08-20 | Codex | Created Runway Ledger architecture, execution, and STATUS package from Kiro's identity-tracking investigation; implementation remains unauthorized |
